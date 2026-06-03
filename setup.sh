#!/usr/bin/env bash
# Setup CommonPlace — verifie les dependances et prepare le dossier.
# Zero dependance pip : tout est en stdlib Python. Seuls yt-dlp, ffmpeg
# et claude (CLI) sont requis.
set -e
cd "$(dirname "$0")"

echo "=== CommonPlace setup ==="

missing=0
check() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "  ok   $1 ($(command -v "$1"))"
  else
    echo "  MANQUE $1 — installe avec : $2"
    missing=1
  fi
}

check python3 "brew install python"
check yt-dlp  "brew install yt-dlp"
check ffmpeg  "brew install ffmpeg"
check claude  "voir https://claude.com/claude-code"

mkdir -p data/media data/gallery

if [ ! -f .env ]; then
  cp .env.example .env
  echo "  .env cree depuis .env.example — remplis TELEGRAM_BOT_TOKEN"
else
  echo "  .env deja present"
fi

if [ "$missing" = "1" ]; then
  echo ""
  echo "Installe les dependances manquantes puis relance ./setup.sh"
  exit 1
fi

echo ""
echo "Pret. Commandes utiles :"
echo "  python3 -m commonplace.run whoami     # trouver ton chat_id Telegram"
echo "  python3 -m commonplace.run full       # pipeline complet"
echo "  open data/gallery/index.html          # ouvrir la galerie"
