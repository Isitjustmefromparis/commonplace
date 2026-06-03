"""Capture des liens depuis Telegram via l'API getUpdates (stdlib urllib).

Principe : on interroge le bot, on lit les nouveaux messages, on en extrait
les URLs et on les ajoute a la base. L'offset est memorise pour ne jamais
retraiter deux fois le meme message (idempotent).
"""
import json
import re
import urllib.request
import urllib.parse
from . import config, db

URL_RE = re.compile(r"https?://[^\s]+")


def _api(method, params=None):
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN manquant dans .env")
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params or {}).encode()
    with urllib.request.urlopen(url, data=data, timeout=30) as r:
        return json.loads(r.read().decode())


def _extract_urls(message):
    """Recupere les URLs d'un message (texte + legende + entities)."""
    urls = []
    for field in ("text", "caption"):
        txt = message.get(field) or ""
        urls += URL_RE.findall(txt)
        # entities de type text_link portent l'URL dans l'attribut 'url'
        for ent in message.get(field + "_entities", []) or message.get("entities", []) or []:
            if ent.get("type") == "text_link" and ent.get("url"):
                urls.append(ent["url"])
    # nettoyage : enlever ponctuation finale
    cleaned = []
    for u in urls:
        u = u.rstrip(").,;]")
        if u not in cleaned:
            cleaned.append(u)
    return cleaned


def ingest(conn, verbose=True):
    """Lit les nouveaux messages et ajoute les liens. Renvoie le nb ajoute."""
    offset = int(db.meta_get(conn, "telegram_offset", "0") or 0)
    added = 0
    resp = _api("getUpdates", {"offset": offset + 1, "timeout": 0, "limit": 100})
    if not resp.get("ok"):
        raise RuntimeError(f"Telegram getUpdates a echoue : {resp}")

    last_update_id = offset
    for upd in resp.get("result", []):
        last_update_id = max(last_update_id, upd["update_id"])
        msg = upd.get("message") or upd.get("channel_post")
        if not msg:
            continue
        chat_id = str(msg.get("chat", {}).get("id", ""))
        # filtre optionnel : n'accepter qu'un chat precis
        if config.TELEGRAM_ALLOWED_CHAT_ID and chat_id != config.TELEGRAM_ALLOWED_CHAT_ID:
            continue
        author = msg.get("from", {}).get("first_name") or msg.get("chat", {}).get("title")
        legende = msg.get("text") or msg.get("caption")
        for url in _extract_urls(msg):
            bid = db.add_bookmark(conn, url, source="telegram",
                                  author=author, caption=legende)
            if bid:
                added += 1
                if verbose:
                    print(f"  + Telegram: {url}")

    if last_update_id > offset:
        db.meta_set(conn, "telegram_offset", last_update_id)
    return added


def whoami(conn=None):
    """Outil de debug : affiche les chat_id qui ont ecrit au bot."""
    resp = _api("getUpdates", {"timeout": 0, "limit": 100})
    seen = {}
    for upd in resp.get("result", []):
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat", {})
        if chat:
            seen[str(chat.get("id"))] = chat.get("title") or chat.get("first_name") or chat.get("type")
    return seen


if __name__ == "__main__":
    print("Chats ayant ecrit au bot :")
    for cid, name in whoami().items():
        print(f"  chat_id={cid}  ({name})")
