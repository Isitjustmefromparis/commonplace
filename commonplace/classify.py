"""Classement automatique en listes intelligentes via le CLI `claude`.

C'est le coeur "magique" : on envoie a Claude le lot de nouveaux bookmarks
ET les listes qui existent deja. Claude range chaque item dans une liste
existante ou en propose une nouvelle. En traitant tout le lot d'un coup, les
clusters emergent (6 activites pour Myriam -> une liste "Activites Myriam").

On utilise le CLI `claude` (deja authentifie) plutot qu'une cle API.
"""
import json
import re
import subprocess
from . import config, db

PROMPT_TEMPLATE = """Tu es le bibliothecaire de CommonPlace, le carnet de \
bookmarks d'Alysse (reels Instagram, TikTok, videos YouTube qu'elle enregistre).

Ta tache : ranger chaque bookmark ci-dessous dans une ou plusieurs LISTES \
thematiques. Une liste regroupe des contenus de meme intention (ex: \
"Activites pour Myriam", "Recettes", "Idees deco", "Inspiration ecriture", \
"Sport maison"). Pense usage concret, pas categorie abstraite.

REGLES :
- Reutilise en priorite une liste EXISTANTE si elle convient (donne son slug).
- Sinon, cree une nouvelle liste : nom court et parlant en francais + slug \
(minuscules, tirets, sans accents) + courte description.
- Un bookmark peut etre dans 1 a 3 listes. Evite d'en mettre dans trop.
- Regroupe : si plusieurs bookmarks du lot vont ensemble, mets-les dans la \
MEME liste plutot que d'en creer une par item.

LISTES EXISTANTES :
{existing}

BOOKMARKS A RANGER :
{items}

Reponds UNIQUEMENT avec du JSON valide, sans texte autour, sans balises \
markdown, au format exact :
{{
  "new_lists": [
    {{"name": "Activites pour Myriam", "slug": "activites-pour-myriam", \
"description": "Activites a faire a la maison avec Myriam"}}
  ],
  "assignments": [
    {{"id": 12, "lists": ["activites-pour-myriam"]}}
  ]
}}"""


def _build_existing(conn):
    rows = db.all_lists(conn)
    if not rows:
        return "(aucune pour l'instant)"
    return "\n".join(
        f"- slug={r['slug']} | {r['name']} : {r['description'] or ''}" for r in rows
    )


def _build_items(items):
    out = []
    for b in items:
        cap = (b["caption"] or "").replace("\n", " ").strip()
        if len(cap) > 500:
            cap = cap[:500] + "..."
        out.append(
            f"- id={b['id']} | plateforme={b['platform']} | "
            f"auteur={b['author'] or '?'} | titre={b['title'] or '?'} | "
            f"legende: {cap or '(vide)'}"
        )
    return "\n".join(out)


def _call_claude(prompt):
    res = subprocess.run(
        [config.CLAUDE_BIN, "-p", prompt],
        capture_output=True, text=True, timeout=300,
    )
    if res.returncode != 0:
        raise RuntimeError(f"claude a echoue : {res.stderr[:400]}")
    return res.stdout.strip()


def _parse_json(text):
    # enleve d'eventuelles balises ```json ... ```
    text = re.sub(r"^```(?:json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    # isole le premier objet JSON
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Pas de JSON dans la reponse : {text[:200]}")
    return json.loads(text[start:end + 1])


def classify(conn, verbose=True):
    """Classe les bookmarks non encore classes. Renvoie le nb traite."""
    items = db.unclassified(conn, limit=config.MAX_PER_RUN)
    if not items:
        return 0
    prompt = PROMPT_TEMPLATE.format(
        existing=_build_existing(conn),
        items=_build_items(items),
    )
    if verbose:
        print(f"  ⊞ classement de {len(items)} bookmark(s) via claude...")
    data = _parse_json(_call_claude(prompt))

    # 1. creer les nouvelles listes
    for nl in data.get("new_lists", []):
        db.get_or_create_list(conn, nl.get("name", nl.get("slug", "Liste")),
                              nl.get("description", ""))

    # 2. mapper slug -> id (apres creation)
    slug_to_id = {r["slug"]: r["id"] for r in db.all_lists(conn)}

    # 3. appliquer les affectations
    by_id = {b["id"]: b for b in items}
    for a in data.get("assignments", []):
        bid = a.get("id")
        if bid not in by_id:
            continue
        for slug in a.get("lists", []):
            slug = db.slugify(slug)
            list_id = slug_to_id.get(slug)
            if not list_id:
                # slug inconnu : on cree une liste a la volee
                list_id = db.get_or_create_list(conn, slug)
                slug_to_id[slug] = list_id
            db.link(conn, bid, list_id)
        db.update_bookmark(conn, bid, classified_at=db.now())
        if verbose:
            print(f"    #{bid} -> {a.get('lists')}")
    return len(items)
