#!/usr/bin/env bash
# Tire la derniere version du code (git pull) puis regenere la galerie.
# Lance une fois par jour par l'agent launchd com.alysse.commonplace-pull.
# Objectif : Alysse ne fait plus jamais de git pull a la main pour deployer.
set -e
cd "$(dirname "$0")"
echo "=== $(date) : daily-pull ==="
git pull --ff-only
python3 -m commonplace.run gallery
echo "=== fin ==="
