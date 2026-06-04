"""Orchestrateur CommonPlace.

Pipeline complet : capture (Telegram + YouTube) -> telechargement -> classement
-> regeneration de la galerie. C'est ce script que le cron lance.

Usage :
    python3 -m commonplace.run            # pipeline complet
    python3 -m commonplace.run ingest     # capture seule
    python3 -m commonplace.run download   # telechargement seul
    python3 -m commonplace.run classify   # classement seul
    python3 -m commonplace.run gallery    # regenere la galerie
    python3 -m commonplace.run whoami     # affiche les chat_id Telegram
    python3 -m commonplace.run add <url>  # ajoute un lien a la main (test)
"""
import sys
from datetime import datetime, timezone, timedelta
from . import config, db, telegram_ingest, youtube_ingest, download, classify, gallery, reorg


def step_ingest(conn):
    n = 0
    if config.TELEGRAM_BOT_TOKEN:
        try:
            n += telegram_ingest.ingest(conn)
        except Exception as e:
            print(f"  ! Telegram: {e}")
    try:
        n += youtube_ingest.ingest(conn)
    except Exception as e:
        print(f"  ! YouTube: {e}")
    print(f"Capture : {n} nouveau(x) lien(s)")
    return n


def step_download(conn):
    ok, err = download.process_new(conn)
    print(f"Telechargement : {ok} ok, {err} echec(s)")
    return ok


def step_classify(conn):
    n = classify.classify(conn)
    print(f"Classement : {n} bookmark(s) ranges")
    return n


def step_gallery(conn):
    out = gallery.build(conn)
    print(f"Galerie : {out}")
    return out


def step_reorg(conn):
    m, s = reorg.run_reorg(conn)
    print(f"Reorganisation : {m} fusion(s), {s} decoupe(s)")
    return m, s


def _reorg_due(conn):
    """Vrai si la derniere reorg date de plus de 24h (ou jamais)."""
    last = db.meta_get(conn, "last_reorg")
    if not last:
        return True
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(last) > timedelta(hours=24)
    except ValueError:
        return True


def full(conn):
    print("=== CommonPlace ===")
    step_ingest(conn)
    step_download(conn)
    step_classify(conn)
    if _reorg_due(conn):
        step_reorg(conn)
    step_gallery(conn)
    print("Termine. Ouvre la galerie dans ton navigateur.")


def main():
    config.ensure_dirs()
    conn = db.connect()
    arg = sys.argv[1] if len(sys.argv) > 1 else "full"
    if arg == "full":
        full(conn)
    elif arg == "ingest":
        step_ingest(conn)
    elif arg == "download":
        step_download(conn)
    elif arg == "classify":
        step_classify(conn)
    elif arg == "gallery":
        step_gallery(conn)
    elif arg == "reorg":
        step_reorg(conn)
        step_gallery(conn)
    elif arg == "whoami":
        for cid, name in telegram_ingest.whoami(conn).items():
            print(f"chat_id={cid}  ({name})")
    elif arg == "add" and len(sys.argv) > 2:
        bid = db.add_bookmark(conn, sys.argv[2], source="manual")
        print(f"Ajoute id={bid}" if bid else "Deja present")
    else:
        print(__doc__)
    conn.close()


if __name__ == "__main__":
    main()
