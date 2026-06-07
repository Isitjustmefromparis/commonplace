"""Recupere les reels/posts ENREGISTRES sur Instagram via instaloader.

⚠️ Instagram n'a pas d'API officielle pour les Enregistres. Ce module utilise
ta SESSION connectee (pas ton mot de passe) via instaloader. Instagram peut
detecter l'automatisation et bloquer temporairement un compte. Precautions
prises : pacing entre requetes, arret des qu'on rattrape le deja-connu, plafond
par execution. A lancer avec PARCIMONIE (manuel ou faible frequence), pas en
boucle 15 min.

Setup une fois sur le Mini :
    pip3 install instaloader
    instaloader -l TON_USERNAME      # login (gere la 2FA), enregistre la session
    # puis dans .env : IG_USERNAME=TON_USERNAME
Usage :
    python3 -m commonplace.run sync-saved
"""
import time
from . import config, db


def sync_saved(conn, verbose=True):
    try:
        import instaloader
    except ImportError:
        print("  instaloader manquant. Sur le Mini : pip3 install instaloader")
        return 0
    user = config.get("IG_USERNAME", "")
    if not user:
        print("  IG_USERNAME manquant dans .env")
        return 0

    L = instaloader.Instaloader(
        download_pictures=False, download_videos=False, download_video_thumbnails=False,
        download_comments=False, save_metadata=False, compress_json=False, quiet=True)
    try:
        L.load_session_from_file(user)
    except FileNotFoundError:
        print(f"  Pas de session pour {user}. Lance d'abord : instaloader -l {user}")
        return 0

    max_new = int(config.get("SAVED_MAX_PER_RUN", "30"))
    stop_after_known = int(config.get("SAVED_STOP_AFTER_KNOWN", "10"))
    pause = float(config.get("SAVED_PAUSE", "2.0"))

    added = known_streak = 0
    try:
        for post in L.get_saved_posts():
            url = f"https://www.instagram.com/p/{post.shortcode}/"
            bid = db.add_bookmark(conn, url, source="saved")
            if bid:
                added += 1
                known_streak = 0
                if verbose:
                    print(f"  + saved: {url}")
            else:
                known_streak += 1
                # arret anticipe (mode incremental). SAVED_STOP_AFTER_KNOWN=0 =
                # mode "vidage du back-catalogue" : on saute le deja-connu sans s'arreter.
                if stop_after_known and known_streak >= stop_after_known:
                    break
            if added >= max_new:
                break
            time.sleep(pause)  # pacing pour limiter la detection
    except Exception as e:
        print(f"  ! Instagram a interrompu la recup ({type(e).__name__}). "
              f"Reessaie plus tard, plus doucement. {added} ajoute(s) avant l'arret.")
    return added
