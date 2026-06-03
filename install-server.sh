#!/usr/bin/env bash
# Installe l'agent launchd qui garde le serveur web CommonPlace allume en
# permanence (consultation depuis l'Air / le tel via Tailscale).
# Usage : ./install-server.sh [port]   (defaut 8787)
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"
LABEL="com.alysse.commonplace-serve"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PORT="${1:-8787}"
PY="$(command -v python3)"
BREW_BIN="$(dirname "$(command -v python3)")"

echo "Projet : $ROOT"
echo "Port   : $PORT"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>-m</string>
    <string>commonplace.serve</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$BREW_BIN:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>SERVE_PORT</key><string>$PORT</string>
  </dict>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$ROOT/data/serve.log</string>
  <key>StandardErrorPath</key><string>$ROOT/data/serve.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl enable "gui/$UID/$LABEL" 2>/dev/null || true

echo "Installe. Le serveur tourne en permanence."
echo ""
echo "Acces depuis CETTE machine : http://localhost:$PORT/"
echo "Acces via Tailscale (Air/tel) : http://mac-mini-de-alysse:$PORT/"
echo "Logs : tail -f $ROOT/data/serve.log"
echo "Desinstaller : launchctl bootout gui/$UID/$LABEL && rm $PLIST"
