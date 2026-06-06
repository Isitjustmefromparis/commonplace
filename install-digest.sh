#!/usr/bin/env bash
# Installe l'agent launchd qui lance la digestion nocturne (fiches md par theme)
# tous les jours a une heure fixe (defaut minuit).
# Usage : ./install-digest.sh [heure]   (ex: ./install-digest.sh 0  pour minuit)
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"
LABEL="com.alysse.commonplace-digest"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
HOUR="${1:-0}"   # 0 = minuit
PY="$(command -v python3)"
BREW_BIN="$(dirname "$(command -v python3)")"

echo "Projet : $ROOT"
echo "Heure  : ${HOUR}h00 chaque jour"

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
    <string>digest</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$BREW_BIN:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$HOUR</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$ROOT/data/digest.log</string>
  <key>StandardErrorPath</key><string>$ROOT/data/digest.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl enable "gui/$UID/$LABEL" 2>/dev/null || true

echo "Installe. La digestion tournera chaque jour a ${HOUR}h00."
echo "Tester maintenant : python3 -m commonplace.run digest"
echo "Logs : tail -f $ROOT/data/digest.log"
echo "Desinstaller : launchctl bootout gui/$UID/$LABEL && rm $PLIST"
