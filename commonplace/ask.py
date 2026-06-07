"""« Demande à ton carnet » : question en langage naturel sur tous les bookmarks.

Charge les entrees (titre, auteur, legende, note, listes, lien) et laisse le
CLI claude repondre en s'appuyant dessus, avec les liens en reference.
"""
from . import config, db
from .classify import _call_claude

PROMPT = """Tu es l'assistant du carnet de bookmarks d'Alysse (reels Instagram, \
TikTok, videos YouTube, tweets qu'elle a sauvegardes). Reponds a sa question en \
t'appuyant UNIQUEMENT sur les entrees ci-dessous. Cite les elements pertinents \
avec leur titre/auteur et donne le lien. Si rien ne correspond vraiment, dis-le \
franchement plutot que d'inventer. Reponds en francais, concis et concret.

QUESTION : {q}

ENTREES DU CARNET :
{corpus}
"""


def _corpus(conn, limit=500):
    rows = conn.execute(
        "SELECT * FROM bookmarks WHERE status IN ('downloaded','metadata_only') "
        "ORDER BY captured_at DESC LIMIT ?", (limit,)
    ).fetchall()
    lists_by_bid = {}
    for lst in db.all_lists(conn):
        for b in db.bookmarks_in_list(conn, lst["id"]):
            lists_by_bid.setdefault(b["id"], []).append(lst["name"])
    lines = []
    for b in rows:
        cap = (b["caption"] or "").replace("\n", " ")[:300]
        note = (b["note"] or "").replace("\n", " ") if "note" in b.keys() else ""
        lst = ", ".join(lists_by_bid.get(b["id"], []))
        line = (f"[{b['id']}] {b['platform']} | {b['author'] or '?'} | "
                f"listes: {lst or '-'} | {b['title'] or ''} | {cap} | {b['url']}")
        ent = b["entities"] if "entities" in b.keys() else None
        if ent:
            line += f" | INFOS: {ent}"
        if note:
            line += f" | NOTE: {note}"
        lines.append(line)
    return "\n".join(lines), len(rows)


def answer(question, conn=None):
    close = False
    if conn is None:
        conn = db.connect()
        close = True
    corpus, n = _corpus(conn)
    if close:
        conn.close()
    if not n:
        return "Ton carnet est encore vide."
    return _call_claude(PROMPT.format(q=question, corpus=corpus))
