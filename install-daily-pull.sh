#!/usr/bin/env bash
# Installe l'agent launchd qui fait un "git pull" + regenere la galerie une
# fois par jour (par defaut a 6h00). A lancer UNE SEULE FOIS sur le Mac mini.
# Apres ca, les mises a jour du code se deploient toutes seules chaque jour.
# Usage : ./install-daily-pull.sh [heure]   (heure = 0..23, defaut 6)
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"
LABEL="com.alysse.commonplace-pull"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
HOUR="${1:-6}"
GIT_BIN="$(dirname "$(command -v git || echo /usr/bin/git)")"
BREW_BIN="$(dirname "$(command -v python3 || echo /opt/homebrew/bin/python3)")"

chmod +x "$ROOT/daily-pull.sh"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT/daily-pull.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$GIT_BIN:$BREW_BIN:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$ROOT/data/pull.log</string>
  <key>StandardErrorPath</key><string>$ROOT/data/pull.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl enable "gui/$UID/$LABEL" 2>/dev/null || true

echo "Installe : git pull + galerie tous les jours a ${HOUR}h00."
echo "Logs         : tail -f $ROOT/data/pull.log"
echo "Desinstaller : launchctl bootout gui/$UID/$LABEL && rm $PLIST"
