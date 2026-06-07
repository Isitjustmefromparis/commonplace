"""Enrichissement « field notes » : extrait les infos actionnables d'un contenu.

Pour chaque bookmark, Claude repere le type (shopping, lieu, livre, recette,
activite, idee) et extrait marques / produits / lieux / livres / personnes, plus
un resume d'une phrase. Stocke en JSON dans bookmarks.entities (+ kind).

v1 : pas de recherche web (rapide, fiable, local). Traite le lot en un appel.
"""
import json
from . import config, db
from .classify import _call_claude, _parse_json

PROMPT = """Tu es l'analyste de CommonPlace. Pour chaque contenu sauvegarde \
(reel, tiktok, video, tweet), extrais les infos ACTIONNABLES. Ne te base que \
sur ce qui est explicitement mentionne ou tres clairement deductible ; \
n'invente rien. Listes vides si rien.

CONTENUS :
{items}

Reponds UNIQUEMENT en JSON valide, sans texte ni balises :
{{
  "results": [
    {{
      "id": 12,
      "kind": "shopping|lieu|livre|recette|activite|idee|autre",
      "resume": "une phrase : ce que c'est et pourquoi c'est utile",
      "marques": [], "produits": [], "lieux": [], "livres": [], "personnes": []
    }}
  ]
}}"""


def _items_block(items):
    out = []
    for b in items:
        cap = (b["caption"] or "").replace("\n", " ")[:500]
        out.append(f"- id={b['id']} | {b['platform']} | {b['author'] or '?'} | "
                   f"{b['title'] or ''} | {cap}")
    return "\n".join(out)


def enrich(conn, verbose=True):
    items = conn.execute(
        "SELECT * FROM bookmarks WHERE entities IS NULL "
        "AND status IN ('downloaded','metadata_only') ORDER BY id LIMIT ?",
        (config.MAX_PER_RUN,)
    ).fetchall()
    if not items:
        return 0
    try:
        data = _parse_json(_call_claude(PROMPT.format(items=_items_block(items))))
    except Exception as e:
        if verbose:
            print(f"  ! enrichissement echoue : {e}")
        return 0
    by_id = {b["id"]: b for b in items}
    n = 0
    for r in data.get("results", []):
        bid = r.get("id")
        if bid not in by_id:
            continue
        ent = {k: r.get(k, []) for k in ("marques", "produits", "lieux", "livres", "personnes")}
        ent["resume"] = r.get("resume", "")
        db.update_bookmark(conn, bid, kind=r.get("kind"),
                           entities=json.dumps(ent, ensure_ascii=False))
        n += 1
        if verbose:
            print(f"  ✦ #{bid} [{r.get('kind')}]")
    return n
