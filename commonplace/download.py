"""Telechargement video + metadonnees via yt-dlp (appele en sous-processus).

Strategie :
1. yt-dlp -J  -> recupere les metadonnees (titre, auteur, legende, duree)
   meme pour Instagram / TikTok / YouTube.
2. telechargement de la video dans data/media/<id>.<ext> + vignette.
Si le telechargement echoue mais que les metadonnees passent, on garde
quand meme l'entree en 'metadata_only' (le lien + la legende restent utiles).
"""
import json
import re
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from . import config, db


def fetch_tweet_oembed(url):
    """Recupere auteur + texte d'un tweet via l'oEmbed officiel (sans auth).

    Marche meme pour les tweets purement texte que yt-dlp ne sait pas traiter.
    Renvoie {'author':..., 'text':...} ou None.
    """
    api = ("https://publish.twitter.com/oembed?dnt=true&omit_script=true&url="
           + urllib.parse.quote(url, safe=""))
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return None
    import html as _html
    blob = data.get("html", "")
    blob = re.sub(r"<br\s*/?>", " ", blob)
    text = re.sub(r"<[^>]+>", " ", blob)          # enleve les balises
    text = _html.unescape(re.sub(r"\s+", " ", text)).strip()
    return {"author": data.get("author_name"), "text": text or None}


def _run(args, timeout=300):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _common_opts():
    opts = []
    if config.COOKIES_FILE:
        opts += ["--cookies", config.COOKIES_FILE]
    return opts


def fetch_metadata(url):
    """Renvoie le dict d'infos yt-dlp, ou None."""
    args = [config.YTDLP_BIN, "-J", "--no-warnings", *_common_opts(), url]
    res = _run(args)
    if res.returncode != 0 or not res.stdout.strip():
        return None
    try:
        info = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None
    # une playlist renvoie 'entries' : on prend la 1re entree
    if info.get("_type") == "playlist" and info.get("entries"):
        info = info["entries"][0]
    return info


def download_thumbnail(url, bid):
    """Recupere uniquement la miniature (pas la video). Renvoie thumb_rel ou None."""
    out_tmpl = str(config.MEDIA / f"{bid}.%(ext)s")
    args = [
        config.YTDLP_BIN, "--skip-download", "--write-thumbnail",
        "--convert-thumbnails", "jpg", "--no-warnings",
        "-o", out_tmpl, *_common_opts(), url,
    ]
    _run(args, timeout=120)
    for f in config.MEDIA.glob(f"{bid}.*"):
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            return f.relative_to(config.DATA).as_posix()
    return None


def download_video(url, bid):
    """Telecharge la video. Renvoie (video_rel, thumb_rel) ou (None, None)."""
    out_tmpl = str(config.MEDIA / f"{bid}.%(ext)s")
    args = [
        config.YTDLP_BIN,
        "-f", "mp4/best",
        "--no-warnings",
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "-o", out_tmpl,
        *_common_opts(),
        url,
    ]
    res = _run(args)
    video_rel = thumb_rel = None
    for f in config.MEDIA.glob(f"{bid}.*"):
        rel = f.relative_to(config.DATA).as_posix()
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            thumb_rel = rel
        elif f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov"):
            video_rel = rel
    if res.returncode != 0 and not video_rel:
        return None, thumb_rel
    return video_rel, thumb_rel


def process_new(conn, verbose=True):
    """Telecharge tous les bookmarks 'new'. Renvoie (ok, errors)."""
    items = db.bookmarks_by_status(conn, "new", limit=config.MAX_PER_RUN)
    ok = err = 0
    for b in items:
        bid, url = b["id"], b["url"]
        if verbose:
            print(f"  ↓ download #{bid} {url}")
        info = fetch_metadata(url)
        is_twitter = b["platform"] == "twitter"
        # repli oEmbed pour les tweets (surtout les tweets texte sans video)
        tweet = fetch_tweet_oembed(url) if is_twitter else None
        fields = {"downloaded_at": db.now()}
        if info:
            # le vrai auteur = le createur du contenu (uploader yt-dlp),
            # pas l'expediteur Telegram (toujours Alysse)
            creator = (info.get("uploader") or info.get("channel")
                       or info.get("uploader_id") or (tweet or {}).get("author") or b["author"])
            fields.update(
                title=info.get("title"),
                author=creator,
                caption=info.get("description") or (tweet or {}).get("text") or b["caption"],
                duration=int(info["duration"]) if info.get("duration") else None,
            )
        elif tweet:
            # tweet texte : pas de video, mais on garde auteur + contenu
            fields.update(author=tweet.get("author") or b["author"],
                          caption=tweet.get("text") or b["caption"])

        # plateformes "lien + miniature" (ex: youtube) : on ne telecharge pas la video
        if b["platform"] in config.THUMBNAIL_ONLY:
            thumb_rel = download_thumbnail(url, bid)
            if info or thumb_rel:
                fields.update(thumb_path=thumb_rel, video_path=None,
                              status="downloaded", error=None)
                ok += 1
                if verbose:
                    print(f"    ◐ lien+miniature pour #{bid}")
            else:
                fields.update(status="error",
                              error="metadonnees indisponibles (lien prive/mort ?)")
                err += 1
            db.update_bookmark(conn, bid, **fields)
            continue

        video_rel, thumb_rel = download_video(url, bid)
        if video_rel:
            fields.update(video_path=video_rel, thumb_path=thumb_rel,
                          status="downloaded", error=None)
            ok += 1
        elif info or tweet:
            fields.update(thumb_path=thumb_rel, status="metadata_only",
                          error=None if tweet and not info else "video non telechargeable (cookies/protection ?)")
            ok += 1
            if verbose:
                print(f"    ! sans video pour #{bid}" if tweet and not info
                      else f"    ! metadata seulement pour #{bid}")
        else:
            fields.update(status="error",
                          error="yt-dlp n'a rien pu recuperer (lien mort/prive ?)")
            err += 1
            if verbose:
                print(f"    x echec total pour #{bid}")
        db.update_bookmark(conn, bid, **fields)
    return ok, err
