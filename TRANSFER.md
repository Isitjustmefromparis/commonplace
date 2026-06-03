# Transfert CommonPlace : MacBook Air -> Mac mini

Le Mac mini (toujours allume) est l'hote definitif. On copie le dossier
complet (avec `.env` et les reels deja captures), on installe, on automatise,
et on **eteint l'agent de l'Air** (un seul consommateur Telegram a la fois).

Mac mini : `mac-mini-de-alysse.local` (192.168.1.23), user `alyssehallali`.

---

## 1. Copier le dossier (depuis le MacBook Air)

```bash
rsync -av --exclude __pycache__ \
  ~/Documents/CommonPlace \
  alyssehallali@mac-mini-de-alysse.local:~/Documents/
```
(Si SSH demande un mot de passe, c'est celui de session du Mac mini.)

> Pas de SSH ? Alternative : AirDrop le dossier `~/Documents/CommonPlace`
> vers le Mac mini, il se range dans Telechargements -> deplace-le dans
> `~/Documents/`.

## 2. Installer sur le Mac mini

En SSH (`ssh alyssehallali@mac-mini-de-alysse.local`) ou directement clavier :
```bash
cd ~/Documents/CommonPlace
./setup.sh            # verifie yt-dlp, ffmpeg, claude (installe si besoin)
python3 -m commonplace.run full   # test : doit capturer/ranger sans erreur
```

Si `setup.sh` signale un manque :
```bash
brew install yt-dlp ffmpeg
```
`claude` doit etre installe ET connecte sur le Mac mini (c'est deja le cas
si Esprit y tourne).

## 3. Automatiser sur le Mac mini

```bash
cd ~/Documents/CommonPlace
./install-automation.sh      # agent launchd toutes les 15 min
tail -f data/cron.log        # verifier que ca tourne (Ctrl-C pour sortir)
```

## 4. IMPORTANT : eteindre l'agent du MacBook Air

Telegram ne sert chaque message qu'une fois. Si les DEUX machines tournent,
elles se volent les messages. Sur le **MacBook Air** :
```bash
launchctl bootout gui/$UID/com.alysse.commonplace
rm ~/Library/LaunchAgents/com.alysse.commonplace.plist
```

## 5. Consulter la galerie

Sur le Mac mini : `open ~/Documents/CommonPlace/data/gallery/index.html`.
Depuis l'Air/le tel, plus tard, on pourra exposer la galerie sur le reseau
local (petit serveur) si tu veux la consulter a distance.

---

### Recap commandes (copier-coller dans l'ordre)
```bash
# --- sur le MacBook Air ---
rsync -av --exclude __pycache__ ~/Documents/CommonPlace alyssehallali@mac-mini-de-alysse.local:~/Documents/

# --- sur le Mac mini ---
cd ~/Documents/CommonPlace && ./setup.sh && python3 -m commonplace.run full && ./install-automation.sh

# --- de retour sur le MacBook Air (couper son agent) ---
launchctl bootout gui/$UID/com.alysse.commonplace 2>/dev/null
rm -f ~/Library/LaunchAgents/com.alysse.commonplace.plist
```
