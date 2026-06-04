"""Reorganisation automatique des listes (passe quotidienne).

Deux operations, via le CLI claude :
1. FUSION : repere les listes qui font doublon ou se recouvrent et les fusionne
   (ex: "Activites enfants" + "Activites creatives enfants" -> une seule).
2. DECOUPE : une liste devenue trop grosse est scindee en sous-themes coherents.

Conservateur par construction : ne supprime jamais un bookmark, ne fait que
deplacer/regrouper les rattachements aux listes.
"""
import json
import re
from . import config, db
from .classify import _call_claude, _parse_json

SPLIT_THRESHOLD = int(config.get("SPLIT_THRESHOLD", "30"))

MERGE_PROMPT = """Tu es le bibliothecaire de CommonPlace (carnet de bookmarks).
Voici les listes actuelles. Repere celles qui FONT DOUBLON ou se recouvrent \
largement et qui gagneraient a etre fusionnees. Ne fusionne QUE des listes \
vraiment proches (meme sujet/intention). Dans le doute, ne fusionne pas.

LISTES (slug | nom | description | nb d'elements) :
{lists}

Reponds UNIQUEMENT en JSON valide, sans texte ni balises :
{{
  "merges": [
    {{"name": "Nom canonique", "description": "desc courte", \
"from": ["slug-a", "slug-b"]}}
  ]
}}
Si rien a fusionner : {{"merges": []}}"""

SPLIT_PROMPT = """Tu es le bibliothecaire de CommonPlace. La liste "{name}" est \
devenue trop grosse et heterogene. Scinde-la en 2 a 4 sous-listes COHERENTES \
selon les intentions reelles. Chaque element doit aller dans exactement une \
sous-liste. Si certains ne rentrent nulle part, laisse-les dans "garder".

ELEMENTS (id | titre | legende) :
{items}

Reponds UNIQUEMENT en JSON valide :
{{
  "sublists": [
    {{"name": "Sous-theme", "description": "desc", "ids": [12, 34]}}
  ],
  "garder": [56]
}}
Si la liste est en fait coherente et ne doit PAS etre scindee : \
{{"sublists": [], "garder": []}}"""


def _lists_block(conn):
    rows = db.all_lists(conn)
    lines = []
    for r in rows:
        n = db.list_count(conn, r["id"])
        lines.append(f"- {r['slug']} | {r['name']} | {r['description'] or ''} | {n}")
    return "\n".join(lines), rows


def merge_similar(conn, verbose=True):
    block, rows = _lists_block(conn)
    if len(rows) < 3:
        return 0
    data = _parse_json(_call_claude(MERGE_PROMPT.format(lists=block)))
    merged = 0
    for m in data.get("merges", []):
        from_slugs = [db.slugify(s) for s in m.get("from", [])]
        if len(from_slugs) < 2:
            continue
        slug_to_id = {r["slug"]: r["id"] for r in db.all_lists(conn)}
        src_ids = [slug_to_id[s] for s in from_slugs if s in slug_to_id]
        if len(src_ids) < 2:
            continue
        target_id = db.get_or_create_list(conn, m.get("name", from_slugs[0]),
                                          m.get("description", ""))
        db.merge_lists(conn, src_ids, target_id)
        merged += 1
        if verbose:
            print(f"  ⤺ fusion {from_slugs} -> {m.get('name')}")
    return merged


def split_large(conn, verbose=True):
    splits = 0
    for r in db.all_lists(conn):
        if db.list_count(conn, r["id"]) <= SPLIT_THRESHOLD:
            continue
        items = db.bookmarks_in_list(conn, r["id"])
        lines = []
        for b in items:
            cap = (b["caption"] or "").replace("\n", " ")[:160]
            lines.append(f"- id={b['id']} | {b['title'] or '?'} | {cap}")
        data = _parse_json(_call_claude(
            SPLIT_PROMPT.format(name=r["name"], items="\n".join(lines))))
        subs = data.get("sublists", [])
        if not subs:
            continue
        valid_ids = {b["id"] for b in items}
        for sub in subs:
            sub_id = db.get_or_create_list(conn, sub.get("name", "Sous-liste"),
                                           sub.get("description", ""))
            for bid in sub.get("ids", []):
                if bid in valid_ids and sub_id != r["id"]:
                    db.link(conn, bid, sub_id)
                    db.unlink(conn, bid, r["id"])
        db.delete_list_if_empty(conn, r["id"])
        splits += 1
        if verbose:
            print(f"  ✂ decoupe '{r['name']}' en {len(subs)} sous-listes")
    return splits


def run_reorg(conn, verbose=True):
    if verbose:
        print("  ⚙ reorganisation des listes...")
    m = merge_similar(conn, verbose)
    s = split_large(conn, verbose)
    db.meta_set(conn, "last_reorg", db.now())
    return m, s
