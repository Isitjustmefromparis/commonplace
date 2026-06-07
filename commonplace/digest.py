"""Digestion nocturne : transforme le carnet en fiches markdown par theme.

Pour chaque liste, ecrit une fiche .md propre et lisible (par un humain ET par
un agent) : titre, description, et chaque element avec son auteur, un resume de
la legende, la note d'Alysse et le lien. Plus une fiche index.

Cible : config.WIKI_DIGEST_DIR (ex: ~/wiki/resources/commonplace) si defini,
sinon data/digest/. Optionnellement, commit+push git si WIKI_DIGEST_GIT=1.
"""
import json
import subprocess
from pathlib import Path
from . import config, db


def _target_dir():
    d = config.get("WIKI_DIGEST_DIR", "")
    return Path(d).expanduser() if d else (config.DATA / "digest")


def _fiche_md(lst, items):
    lines = [f"# {lst['name']}", ""]
    if lst["description"]:
        lines += [lst["description"], ""]
    lines.append(f"{len(items)} element(s) sauvegarde(s) dans CommonPlace.")
    lines.append("")
    for b in items:
        title = b["title"] or b["author"] or "Sans titre"
        lines.append(f"## {title}")
        meta = " · ".join(filter(None, [b["author"], b["platform"]]))
        if meta:
            lines.append(f"*{meta}*")
        ent = {}
        if "entities" in b.keys() and b["entities"]:
            try:
                ent = json.loads(b["entities"])
            except (ValueError, TypeError):
                ent = {}
        if ent.get("resume"):
            lines += ["", ent["resume"]]
        for label, key in (("Marques", "marques"), ("Produits", "produits"),
                           ("Lieux", "lieux"), ("Livres", "livres")):
            vals = [v for v in ent.get(key, []) if v]
            if vals:
                lines.append(f"- **{label}** : {', '.join(vals)}")
        cap = (b["caption"] or "").strip().replace("\r", " ")
        if cap:
            lines += ["", cap[:600]]
        note = b["note"] if "note" in b.keys() else None
        if note:
            lines += ["", f"**Ma note :** {note}"]
        lines += ["", f"[Voir l'original]({b['url']})", ""]
    return "\n".join(lines) + "\n"


def _maybe_git(target, n):
    if config.get("WIKI_DIGEST_GIT", "") not in ("1", "true", "yes"):
        return
    try:
        root = subprocess.run(["git", "-C", str(target), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True).stdout.strip()
        if not root:
            return
        subprocess.run(["git", "-C", root, "pull", "--rebase", "--autostash"],
                       capture_output=True, text=True, timeout=60)
        subprocess.run(["git", "-C", root, "add", str(target)], capture_output=True, text=True)
        subprocess.run(["git", "-C", root, "commit", "-m",
                        f"CommonPlace digest : {n} fiche(s)"], capture_output=True, text=True)
        subprocess.run(["git", "-C", root, "push"], capture_output=True, text=True, timeout=60)
    except Exception:
        pass  # best-effort, ne casse jamais la digestion


def digest(conn, verbose=True):
    target = _target_dir()
    target.mkdir(parents=True, exist_ok=True)
    written = 0
    index = ["# CommonPlace : carnet digere par theme", "",
             "Fiches generees automatiquement chaque nuit a partir du carnet.", ""]
    for lst in db.all_lists(conn):
        items = db.bookmarks_in_list(conn, lst["id"])
        if not items:
            continue
        fname = f"commonplace-{lst['slug']}.md"
        (target / fname).write_text(_fiche_md(lst, items), encoding="utf-8")
        index.append(f"- [{lst['name']}]({fname}) : {len(items)} element(s)")
        written += 1
        if verbose:
            print(f"  📝 {fname} ({len(items)})")
    (target / "commonplace-index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    _maybe_git(target, written)
    if verbose:
        print(f"  fiches ecrites dans {target}")
    return written
