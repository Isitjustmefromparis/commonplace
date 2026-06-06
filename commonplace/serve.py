"""Petit serveur web local pour consulter CommonPlace depuis l'Air / le tel.

Sert le dossier data/ (donc la galerie + les videos + miniatures). Accessible
sur le reseau local ET via Tailscale (depuis n'importe ou). Gere les requetes
"Range" HTTP, indispensables pour que les videos se lisent sur iPhone/Safari.

Lancer : python3 -m commonplace.serve   (port 8787 par defaut)
"""
import os
import re
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from . import config, db, ask


class RangeHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler + support des requetes Range (lecture video iOS)."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/add":
            self._handle_add(urllib.parse.parse_qs(parsed.query))
            return
        if parsed.path == "/ask":
            self._handle_ask(urllib.parse.parse_qs(parsed.query))
            return
        if self.path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", "/gallery/index.html")
            self.end_headers()
            return
        if self.headers.get("Range"):
            self._serve_range()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length).decode("utf-8", "ignore") if length else ""
        params = urllib.parse.parse_qs(body)
        params.update(urllib.parse.parse_qs(parsed.query))
        if parsed.path == "/add":
            self._handle_add(params)
        elif parsed.path == "/note":
            self._handle_note(params)
        elif parsed.path == "/ask":
            self._handle_ask(params)
        else:
            self.send_error(404)

    def _text(self, code, msg):
        data = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _handle_ask(self, params):
        q = (params.get("q") or params.get("question") or [""])[0].strip()
        if not q:
            self._text(400, "pose une question avec ?q=...")
            return
        try:
            self._text(200, ask.answer(q))
        except Exception as e:
            self._text(500, f"erreur : {e}")

    def _handle_note(self, params):
        bid = (params.get("id") or [""])[0]
        text = (params.get("text") or [""])[0]
        key = (params.get("key") or [""])[0]
        add_key = config.get("ADD_KEY", "")
        if add_key and key != add_key:
            self._text(403, "cle invalide")
            return
        if not bid.isdigit():
            self._text(400, "id invalide")
            return
        conn = db.connect()
        db.set_note(conn, int(bid), text.strip() or None)
        conn.close()
        self._text(200, "note enregistree")

    def _handle_add(self, params):
        """Ajoute un lien envoye par le raccourci iPhone (ou tout client HTTP)."""
        url = (params.get("url") or [""])[0].strip()
        key = (params.get("key") or [""])[0]
        add_key = config.get("ADD_KEY", "")
        if add_key and key != add_key:
            self._text(403, "cle invalide")
            return
        if not url.startswith("http"):
            self._text(400, "pas d'URL valide")
            return
        conn = db.connect()
        bid = db.add_bookmark(conn, url, source="shortcut")
        conn.close()
        self._text(200, "Ajoute a CommonPlace" if bid else "deja present")

    def _serve_range(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            self.send_error(404)
            return
        size = os.path.getsize(path)
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers["Range"])
        if not m:
            self.send_error(400)
            return
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_error(416)
            return
        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break
                remaining -= len(chunk)

    def log_message(self, *args):
        pass  # silencieux


def main():
    config.ensure_dirs()
    port = int(config.get("SERVE_PORT", "8787"))
    handler = partial(RangeHandler, directory=str(config.DATA))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)
    print(f"CommonPlace en ligne : http://0.0.0.0:{port}/  (racine={config.DATA})")
    print("Accessible via Tailscale : http://mac-mini-de-alysse:%d/" % port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
