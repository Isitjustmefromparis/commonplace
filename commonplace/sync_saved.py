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


def login_with_sessionid(sessionid, csrftoken="", ds_user_id="", verbose=True):
    """Cree la session instaloader a partir des cookies du navigateur.

    Contourne le login par mot de passe (casse par Instagram) et reutilise ta
    vraie session connectee. Instagram exige sessionid ET csrftoken. Recupere-les
    via : navigateur -> instagram.com connecte -> Inspecter -> Application ->
    Cookies -> lignes sessionid et csrftoken.
    """
    try:
        import instaloader
    except ImportError:
        print("  instaloader manquant : pip3 install --user --break-system-packages instaloader")
        return False
    user = config.get("IG_USERNAME", "")
    if not user:
        print("  IG_USERNAME manquant dans .env")
        return False
    if not csrftoken.strip():
        print("  Il manque le csrftoken (Instagram l'exige). Relance et colle aussi le csrftoken.")
        return False
    cookies = {"sessionid": sessionid.strip(), "csrftoken": csrftoken.strip()}
    if ds_user_id.strip():
        cookies["ds_user_id"] = ds_user_id.strip()
    L = instaloader.Instaloader(quiet=True)
    L.load_session(user, cookies)
    try:
        who = L.test_login()
    except Exception as e:
        who = None
        if verbose:
            print(f"  test_login a echoue : {e}")
    if who:
        L.save_session_to_file()
        print(f"  session enregistree pour {who} ✓")
        return True
    print("  echec : le sessionid est invalide ou expire. Recopie-le bien depuis le navigateur connecte.")
    return False


def maybe_sync(conn, verbose=True):
    """Version bridee pour le pipeline 15 min : ne lance sync_saved que si
    IG_USERNAME est defini ET si le dernier passage date de plus de
    SAVED_EVERY_HOURS (defaut 8h). SAVED_EVERY_HOURS=0 desactive la synchro
    auto. Le timestamp est mis a jour meme en cas d'echec, pour ne pas marteler
    Instagram toutes les 15 min sur une session morte.
    """
    if not config.get("IG_USERNAME", ""):
        return 0
    hours = float(config.get("SAVED_EVERY_HOURS", "8"))
    if hours <= 0:
        return 0  # synchro auto desactivee
    stamp = config.DATA / ".last_saved_sync"
    try:
        if stamp.exists() and (time.time() - stamp.stat().st_mtime) < hours * 3600:
            return 0  # trop tot, on attend
    except OSError:
        pass
    n = sync_saved(conn, verbose=verbose)
    try:
        stamp.write_text(str(time.time()))
    except OSError:
        pass
    return n


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
