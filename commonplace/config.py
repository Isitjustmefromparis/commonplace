"""Configuration centrale de CommonPlace.

Tout est en stdlib. Les chemins sont relatifs a la racine du projet pour
que le dossier soit 100% portable (copie sur le Mac mini sans rien changer).
Les secrets viennent d'un fichier .env a la racine (ou de l'environnement).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MEDIA = DATA / "media"
GALLERY = DATA / "gallery"
DB_PATH = DATA / "commonplace.db"
ENV_PATH = ROOT / ".env"


def _load_env():
    """Charge .env dans os.environ sans dependance externe."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # ne pas ecraser une variable deja definie dans l'environnement
        os.environ.setdefault(key, val)


_load_env()


def get(name, default=None):
    return os.environ.get(name, default)


# --- Parametres ---
TELEGRAM_BOT_TOKEN = get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_CHAT_ID = get("TELEGRAM_ALLOWED_CHAT_ID", "")  # optionnel : filtre
YOUTUBE_API_KEY = get("YOUTUBE_API_KEY", "")
YOUTUBE_PLAYLIST_ID = get("YOUTUBE_PLAYLIST_ID", "")
CLAUDE_BIN = get("CLAUDE_BIN", "claude")
YTDLP_BIN = get("YTDLP_BIN", "yt-dlp")
MAX_PER_RUN = int(get("MAX_PER_RUN", "25"))
# cookies optionnels pour Instagram/TikTok (export navigateur, format Netscape)
COOKIES_FILE = get("COOKIES_FILE", "")
# plateformes ou on ne garde QUE le lien + la miniature (pas la video entiere).
# par defaut youtube (videos lourdes, qui ne disparaissent quasi jamais).
THUMBNAIL_ONLY = {p.strip() for p in get("THUMBNAIL_ONLY_PLATFORMS", "youtube").split(",") if p.strip()}


def ensure_dirs():
    for d in (DATA, MEDIA, GALLERY):
        d.mkdir(parents=True, exist_ok=True)
