"""Petit serveur web local pour consulter CommonPlace depuis l'Air / le tel.

Sert le dossier data/ (donc la galerie + les videos + miniatures). Accessible
sur le reseau local ET via Tailscale (depuis n'importe ou). Gere les requetes
"Range" HTTP, indispensables pour que les videos se lisent sur iPhone/Safari.

Lancer : python3 -m commonplace.serve   (port 8787 par defaut)
"""
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from . import config


class RangeHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler + support des requetes Range (lecture video iOS)."""

    def do_GET(self):
        if self.path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", "/gallery/index.html")
            self.end_headers()
            return
        if self.headers.get("Range"):
            self._serve_range()
        else:
            super().do_GET()

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
