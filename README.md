# CommonPlace

Carnet local de bookmarks Instagram / TikTok / YouTube. Tu partages un reel,
il telecharge la video, la range tout seul dans des listes intelligentes, et
tu consultes tout dans ton navigateur. Tout reste en local.

## Comment ca marche

```
Capture                     Inbox          Pipeline                  Galerie
─────────                   ─────          ────────                  ───────
Insta/TikTok → Telegram  ─┐
                          ├─→  SQLite  ─→  yt-dlp telecharge    ─→   index.html
YouTube → playlist NL    ─┘               claude range en listes     (navigateur)
```

- **Capture** : tu Partages un reel/TikTok vers ton bot Telegram. YouTube : tu
  enregistres dans ta playlist non listee, il la lit tout seul.
- **Telechargement** : `yt-dlp` recupere la video + titre + auteur + legende.
- **Classement** : le CLI `claude` (deja authentifie) range chaque contenu dans
  des listes qui se creent au fil de l'eau ("Activites Myriam", "Recettes"...).
- **Galerie** : une page HTML statique, dans ta charte, ouvrable au navigateur.

## Dependances (toutes deja la sur les Macs d'Alysse)

`python3`, `yt-dlp`, `ffmpeg`, `claude` (CLI). Aucune librairie pip.

## Installation

```bash
cd ~/Documents/CommonPlace
./setup.sh
# remplis TELEGRAM_BOT_TOKEN dans .env
```

### Creer le bot Telegram
1. Dans Telegram : ouvre @BotFather, envoie `/newbot`.
2. Nom : `CommonPlace`. Username : `commonplace_alysse_bot` (ou variante).
3. Copie le token dans `.env` -> `TELEGRAM_BOT_TOKEN=...`.
4. Ouvre une conversation avec ton bot et envoie-lui un message.
5. `python3 -m commonplace.run whoami` -> note ton `chat_id`, mets-le dans
   `TELEGRAM_ALLOWED_CHAT_ID` (optionnel mais conseille).

### YouTube (optionnel)
Active "YouTube Data API v3" sur console.cloud.google.com, cree une cle API,
mets-la dans `YOUTUBE_API_KEY`. La playlist est deja renseignee.

## Utilisation

```bash
python3 -m commonplace.run full       # capture + download + classe + galerie
python3 -m commonplace.run add <url>  # ajouter un lien a la main (test)
open data/gallery/index.html          # voir le resultat
```

## Automatisation (Mac mini)

Lancer le pipeline toutes les 15 min via cron :
```cron
*/15 * * * * cd ~/Documents/CommonPlace && /opt/homebrew/bin/python3 -m commonplace.run full >> data/cron.log 2>&1
```

## Passer du MacBook Air au Mac mini

Le dossier est autonome. Copie-le (ou `git clone`), puis :
```bash
cd ~/Documents/CommonPlace && ./setup.sh
```
Le `.env` n'est pas versionne : recree-le sur le Mac mini.

## Structure

```
commonplace/
  config.py          parametres + .env
  db.py              SQLite (bookmarks, lists, liens)
  telegram_ingest.py capture Telegram
  youtube_ingest.py  capture playlist YouTube
  download.py        yt-dlp (video + metadonnees)
  classify.py        classement en listes via claude
  gallery.py         generation index.html
  run.py             orchestrateur (CLI)
data/
  commonplace.db     base
  media/             videos + vignettes
  gallery/index.html la galerie
```

## A venir (phases suivantes)
- Conversion des videos en format plus leger (espace disque).
- Transcription Whisper pour un classement plus fin.
- Reorganisation auto des listes (fusion/decoupe).
- Recap Telegram du matin.
```
