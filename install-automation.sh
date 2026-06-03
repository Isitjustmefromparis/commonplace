#!/usr/bin/env bash
# Installe (ou reinstalle) l'agent launchd qui lance CommonPlace toutes les
# 15 minutes. Marche sur n'importe quelle machine (MacBook Air, Mac mini).
# Usage : ./install-automation.sh [intervalle_secondes]
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"
LABEL="com.alysse.commonplace"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
INTERVAL="${1:-900}"   # 900s = 15 min par defaut
PY="$(command -v python3)"
BREW_BIN="$(dirname "$(command -v yt-dlp || echo /opt/homebrew/bin/yt-dlp)")"

echo "Projet     : $ROOT"
echo "Python     : $PY"
echo "Intervalle : ${INTERVAL}s"

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
    <string>commonplace.run</string>
    <string>full</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$BREW_BIN:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartInterval</key><integer>$INTERVAL</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$ROOT/data/cron.log</string>
  <key>StandardErrorPath</key><string>$ROOT/data/cron.log</string>
</dict>
</plist>
PLISTEOF

# (re)charger
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl enable "gui/$UID/$LABEL" 2>/dev/null || true

echo "Installe. Etat :"
launchctl print "gui/$UID/$LABEL" 2>/dev/null | grep -E "state|pid|program " | sed 's/^/  /' || true
echo ""
echo "Logs       : tail -f $ROOT/data/cron.log"
echo "Desinstaller : launchctl bootout gui/$UID/$LABEL && rm $PLIST"
