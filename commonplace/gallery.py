"""Genere la galerie statique data/gallery/index.html.

Inspiration : Dewey (masonry de cartes, sidebar de listes, cartes riches) mais
dans la charte d'Alysse (vert foret / orange / creme, Fraunces + Manrope).

Page autonome ouvrable au navigateur (file://). Filtrage (liste active,
plateforme, recherche) en JS cote client. Videos locales jouees via <video>.
"""
import html
import hashlib
from datetime import datetime
from . import config, db

# petits logos inline (monochromes, prennent currentColor)
PLATFORM_SVG = {
    "instagram": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.2.06 1.8.25 2.2.42.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.17.4.36 1 .42 2.2.07 1.3.07 1.7.07 4.9s0 3.6-.07 4.9c-.06 1.2-.25 1.8-.42 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.17-1 .36-2.2.42-1.3.07-1.7.07-4.9.07s-3.6 0-4.9-.07c-1.2-.06-1.8-.25-2.2-.42-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.17-.4-.36-1-.42-2.2C2.2 15.6 2.2 15.2 2.2 12s0-3.6.07-4.9c.06-1.2.25-1.8.42-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.17 1-.36 2.2-.42C8.4 2.2 8.8 2.2 12 2.2Zm0 1.8c-3.1 0-3.5 0-4.7.06-1.1.05-1.7.24-2.1.4-.5.2-.9.43-1.3.83-.4.4-.63.8-.83 1.3-.16.4-.35 1-.4 2.1C2.6 9.9 2.6 10.3 2.6 12s0 2.1.06 3.3c.05 1.1.24 1.7.4 2.1.2.5.43.9.83 1.3.4.4.8.63 1.3.83.4.16 1 .35 2.1.4 1.2.06 1.6.06 4.7.06s3.5 0 4.7-.06c1.1-.05 1.7-.24 2.1-.4.5-.2.9-.43 1.3-.83.4-.4.63-.8.83-1.3.16-.4.35-1 .4-2.1.06-1.2.06-1.6.06-3.3s0-2.1-.06-3.3c-.05-1.1-.24-1.7-.4-2.1-.2-.5-.43-.9-.83-1.3-.4-.4-.8-.63-1.3-.83-.4-.16-1-.35-2.1-.4C15.5 4 15.1 4 12 4Zm0 3.05A4.95 4.95 0 1 1 7.05 12 4.95 4.95 0 0 1 12 7.05Zm0 8.16A3.21 3.21 0 1 0 8.79 12 3.21 3.21 0 0 0 12 15.21Zm6.3-8.36a1.16 1.16 0 1 1-1.16-1.15 1.16 1.16 0 0 1 1.16 1.15Z"/></svg>',
    "tiktok": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.6 5.8a4.3 4.3 0 0 1-1-2.8h-3v12.2a2.5 2.5 0 1 1-2.5-2.5c.26 0 .5.04.74.1V9.7a5.6 5.6 0 0 0-.74-.05A5.5 5.5 0 1 0 15.6 15V9.3a7.2 7.2 0 0 0 4.2 1.34V7.6a4.3 4.3 0 0 1-3.2-1.8Z"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M23 7.5a3 3 0 0 0-2.1-2.1C19 5 12 5 12 5s-7 0-8.9.4A3 3 0 0 0 1 7.5 31 31 0 0 0 .6 12 31 31 0 0 0 1 16.5a3 3 0 0 0 2.1 2.1C5 19 12 19 12 19s7 0 8.9-.4a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .4-4.5 31 31 0 0 0-.4-4.5ZM9.8 15.3V8.7l5.7 3.3Z"/></svg>',
    "twitter": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.66l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"/></svg>',
    "autre": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10.6 13.4a1 1 0 0 0 1.4 0l4-4a3 3 0 0 0-4.2-4.2l-1 1a1 1 0 1 0 1.4 1.4l1-1a1 1 0 0 1 1.4 1.4l-4 4a1 1 0 0 0 0 1.4Zm2.8-2.8a1 1 0 0 0-1.4 0l-4 4a3 3 0 0 0 4.2 4.2l1-1a1 1 0 1 0-1.4-1.4l-1 1a1 1 0 0 1-1.4-1.4l4-4a1 1 0 0 0 0-1.4Z"/></svg>',
}

# palette de monogrammes derivee de la charte
AVATAR_COLORS = ["#36592F", "#E48C3C", "#213B1C", "#9c6b3f", "#6b7a5c", "#b8662f"]


def _avatar(name):
    name = (name or "?").strip()
    letter = html.escape(name[0].upper()) if name else "?"
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(AVATAR_COLORS)
    return f'<span class="avatar" style="background:{AVATAR_COLORS[idx]}">{letter}</span>'


def _fmt_date(iso):
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except ValueError:
        return iso[:10]


def _card(b, slug_by_bid):
    rel = "../"
    video = rel + b["video_path"] if b["video_path"] else None
    thumb = rel + b["thumb_path"] if b["thumb_path"] else None
    plat = b["platform"] or "autre"
    title = html.escape(b["title"] or "")
    author = html.escape(b["author"] or "")
    handle = ""
    cap = html.escape((b["caption"] or "").strip())
    if len(cap) > 280:
        cap = cap[:280] + "…"
    url = html.escape(b["url"])
    date = _fmt_date(b["captured_at"])
    lists = " ".join(slug_by_bid.get(b["id"], [])) or "__unsorted__"
    blob = html.escape(" ".join(filter(None, [b["title"], b["author"], b["caption"], plat])).lower())

    if video:
        poster = f'poster="{html.escape(thumb)}"' if thumb else ""
        media = f'<div class="media"><video controls preload="none" {poster} src="{html.escape(video)}"></video></div>'
    elif thumb:
        # pas de video locale (youtube / tweet) : miniature cliquable vers l'original
        media = (f'<a class="media media-link" href="{url}" target="_blank" rel="noopener">'
                 f'<img loading="lazy" src="{html.escape(thumb)}" alt="">'
                 f'<span class="play">▶</span></a>')
    else:
        media = ""

    cap_html = f'<p class="cap">{cap}</p>' if cap else ""
    title_html = f'<p class="ttl">{title}</p>' if title and title != author else ""
    note_val = html.escape(b["note"] or "") if "note" in b.keys() else ""

    return f"""
  <article class="card" data-lists="{lists}" data-platform="{plat}" data-search="{blob}">
    <div class="head">
      {_avatar(b['author'])}
      <div class="who"><span class="name">{author or 'Inconnu'}</span></div>
      <span class="plat plat-{plat}" title="{plat}">{PLATFORM_SVG.get(plat, PLATFORM_SVG['autre'])}</span>
    </div>
    {title_html}
    {cap_html}
    {media}
    <div class="foot"><span class="date">{date}</span><a class="src" href="{url}" target="_blank" rel="noopener">original ↗</a></div>
    <textarea class="note" data-id="{b['id']}" rows="1" placeholder="Ajouter une note, une idée…">{note_val}</textarea>
  </article>"""


def build(conn):
    # mapping bookmark -> slugs de listes
    slug_by_bid = {}
    list_counts = {}
    for lst in db.all_lists(conn):
        items = db.bookmarks_in_list(conn, lst["id"])
        if items:
            list_counts[lst["slug"]] = (lst["name"], len(items))
        for b in items:
            slug_by_bid.setdefault(b["id"], []).append(lst["slug"])

    rows = conn.execute(
        "SELECT * FROM bookmarks WHERE status IN ('downloaded','metadata_only') "
        "ORDER BY captured_at DESC"
    ).fetchall()

    cards = "\n".join(_card(b, slug_by_bid) for b in rows)
    total = len(rows)
    n_unsorted = sum(1 for b in rows if b["id"] not in slug_by_bid)

    # sidebar : listes
    nav = [f'<button class="nav active" data-list="__all__"><span>Tout</span><b>{total}</b></button>']
    for slug, (name, n) in sorted(list_counts.items(), key=lambda x: -x[1][1]):
        nav.append(f'<button class="nav" data-list="{html.escape(slug)}"><span>{html.escape(name)}</span><b>{n}</b></button>')
    if n_unsorted:
        nav.append(f'<button class="nav" data-list="__unsorted__"><span>A trier</span><b>{n_unsorted}</b></button>')

    # plateformes presentes
    plats = sorted({b["platform"] for b in rows if b["platform"]})
    plat_chips = "".join(
        f'<button class="chip" data-platform="{p}">{PLATFORM_SVG.get(p, PLATFORM_SVG["autre"])}<span>{p}</span></button>'
        for p in plats
    )

    page = (_TEMPLATE
            .replace("{{NAV}}", "\n".join(nav))
            .replace("{{CHIPS}}", plat_chips)
            .replace("{{CARDS}}", cards or '<p class="empty">Rien encore. Partage un reel a ton bot Telegram !</p>')
            .replace("{{TOTAL}}", str(total)))
    out = config.GALLERY / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CommonPlace</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900&family=Manrope:wght@300..800&display=swap" rel="stylesheet">
<style>
:root{
  --green:#36592F; --green-d:#213B1C; --orange:#E48C3C; --cream:#EFE7D2;
  --cream-soft:#F6F1E2; --paper:#FBF8EF; --sage:#CDCD8A; --muted:#7c8a6b; --line:#e2dcc6;
  --heading:"Fraunces",Georgia,serif; --body:"Manrope",-apple-system,sans-serif;
  --radius:18px; --shadow:0 4px 18px rgba(33,59,28,.07); --shadow-h:0 14px 40px rgba(33,59,28,.16);
}
*{box-sizing:border-box}
html,body{margin:0}
body{font-family:var(--body);background:var(--cream);color:var(--green-d);line-height:1.5;
  display:grid;grid-template-columns:264px 1fr;min-height:100vh}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:var(--sage);border-radius:99px}

/* Sidebar */
aside{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--paper);
  border-right:1px solid var(--line);padding:1.4rem 1rem;display:flex;flex-direction:column;gap:.3rem}
.brand{font-family:var(--heading);font-weight:900;font-size:1.7rem;color:var(--green-d);
  letter-spacing:-.02em;padding:.2rem .4rem 1rem}
.brand .dot{color:var(--orange)}
.sec{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);padding:1rem .6rem .3rem}
.nav{display:flex;align-items:center;justify-content:space-between;gap:.5rem;width:100%;
  border:0;background:transparent;color:var(--green-d);font-family:var(--body);font-size:.92rem;
  font-weight:600;text-align:left;padding:.5rem .6rem;border-radius:10px;cursor:pointer}
.nav span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nav b{font-size:.72rem;font-weight:700;color:var(--muted);background:var(--cream);
  border-radius:99px;padding:.05rem .5rem;flex:none}
.nav:hover{background:var(--cream)}
.nav.active{background:var(--green);color:var(--cream)}
.nav.active b{background:rgba(255,255,255,.2);color:var(--cream)}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;padding:.3rem .4rem}
.chip{display:inline-flex;align-items:center;gap:.3rem;border:1px solid var(--line);
  background:transparent;color:var(--muted);border-radius:99px;padding:.25rem .6rem;
  font-size:.78rem;font-weight:600;cursor:pointer;font-family:var(--body);text-transform:capitalize}
.chip svg{width:14px;height:14px}
.chip:hover{border-color:var(--orange);color:var(--green-d)}
.chip.on{background:var(--green);color:var(--cream);border-color:var(--green)}

/* Main */
main{padding:1.6rem 1.8rem 4rem;min-width:0}
.topbar{display:flex;align-items:center;gap:1rem;margin-bottom:1.4rem;flex-wrap:wrap}
.topbar h1{font-family:var(--heading);font-weight:800;font-size:1.6rem;color:var(--green-d);margin:0;flex:none}
.search{flex:1;min-width:200px}
.search input{width:100%;max-width:480px;padding:.7rem 1.1rem;border:1px solid var(--line);
  border-radius:99px;background:var(--paper);font-family:var(--body);font-size:.95rem;color:var(--green-d);outline:none}
.search input:focus{border-color:var(--orange)}
.askbar{display:flex;gap:.6rem;margin:0 0 1rem;max-width:760px}
.askbar input{flex:1;padding:.7rem 1.1rem;border:1px solid var(--line);border-radius:99px;
  background:var(--paper);font-family:var(--body);font-size:.95rem;color:var(--green-d);outline:none}
.askbar input:focus{border-color:var(--orange)}
.askbar button{flex:none;border:0;background:var(--green);color:var(--cream);font-family:var(--body);
  font-weight:700;font-size:.9rem;padding:.7rem 1.3rem;border-radius:99px;cursor:pointer}
.askbar button:hover{background:var(--orange)}
.askbar button:disabled{opacity:.5;cursor:wait}
.answer{max-width:760px;background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--orange);
  border-radius:12px;padding:1rem 1.2rem;margin:0 0 1.4rem;white-space:pre-wrap;font-size:.92rem;line-height:1.55;box-shadow:var(--shadow)}

/* Masonry */
.masonry{column-count:4;column-gap:1.2rem}
@media(max-width:1500px){.masonry{column-count:3}}
@media(max-width:1100px){.masonry{column-count:2}}
@media(max-width:680px){body{grid-template-columns:1fr}aside{display:none}.masonry{column-count:1}}
.card{break-inside:avoid;background:var(--paper);border:1px solid var(--line);border-radius:var(--radius);
  margin:0 0 1.2rem;overflow:hidden;box-shadow:var(--shadow);transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-3px);box-shadow:var(--shadow-h)}
.head{display:flex;align-items:center;gap:.6rem;padding:.85rem .95rem .3rem}
.avatar{width:34px;height:34px;border-radius:99px;flex:none;color:#fff;font-weight:800;
  display:flex;align-items:center;justify-content:center;font-size:.95rem;font-family:var(--heading)}
.who{flex:1;min-width:0}
.name{display:block;font-weight:700;font-size:.92rem;color:var(--green-d);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.plat{flex:none;color:var(--muted)}
.plat svg{width:20px;height:20px;display:block}
.plat-instagram{color:#c13584}.plat-tiktok{color:#010101}.plat-youtube{color:#c0392b}.plat-twitter{color:#0f1419}
.ttl{font-family:var(--heading);font-weight:700;font-size:1rem;line-height:1.25;
  margin:.4rem .95rem 0;color:var(--green-d)}
.cap{margin:.5rem .95rem .2rem;font-size:.9rem;color:var(--green-d);opacity:.9}
.media{margin-top:.6rem;background:var(--green-d);line-height:0;position:relative;display:block}
.media video,.media img{width:100%;height:auto;display:block;max-height:560px;object-fit:cover}
.media-link .play{position:absolute;inset:0;margin:auto;width:54px;height:54px;
  display:flex;align-items:center;justify-content:center;border-radius:99px;
  background:rgba(33,59,28,.75);color:#fff;font-size:1.3rem;padding-left:4px}
.media-link:hover .play{background:var(--orange)}
.foot{display:flex;align-items:center;justify-content:space-between;padding:.6rem .95rem .85rem}
.date{font-size:.78rem;color:var(--muted)}
.src{font-size:.8rem;font-weight:700;color:var(--green)}
.src:hover{color:var(--orange)}
.note{display:block;width:auto;margin:0 .95rem 1rem;padding:.5rem .6rem;border:1px dashed var(--line);
  border-radius:10px;background:var(--cream);font-family:var(--body);font-size:.85rem;color:var(--green-d);
  resize:none;outline:none;line-height:1.4;overflow:hidden}
.note:focus{border-style:solid;border-color:var(--orange);background:#fff}
.note.saved{border-color:var(--green);border-style:solid}
.note::placeholder{color:var(--muted);opacity:.75}
a{text-decoration:none;color:inherit}
.empty{color:var(--muted);font-size:1.05rem;margin-top:3rem}
.hidden{display:none!important}
</style>
</head>
<body>
<aside>
  <div class="brand">common<span class="dot">place.</span></div>
  <div class="sec">Listes</div>
  {{NAV}}
  <div class="sec">Plateformes</div>
  <div class="chips">{{CHIPS}}</div>
</aside>
<main>
  <div class="topbar">
    <h1 id="title">Tout</h1>
    <div class="search"><input id="q" type="search" placeholder="Rechercher (titre, auteur, mot-cle)…"></div>
  </div>
  <div class="askbar">
    <input id="ask" type="text" placeholder="Demande à ton carnet… (ex : qu'est-ce que j'ai sauvé pour Myriam ?)">
    <button id="askbtn">Demander</button>
  </div>
  <div id="answer" class="answer hidden"></div>
  <div class="masonry" id="grid">
{{CARDS}}
  </div>
</main>
<script>
const state={list:"__all__",plats:new Set(),q:""};
const cards=[...document.querySelectorAll(".card")];
function apply(){
  const t=state.q.trim().toLowerCase();
  cards.forEach(c=>{
    const inList = state.list==="__all__"
      || (state.list==="__unsorted__" ? c.dataset.lists==="__unsorted__"
          : c.dataset.lists.split(" ").includes(state.list));
    const inPlat = state.plats.size===0 || state.plats.has(c.dataset.platform);
    const inQ = !t || c.dataset.search.includes(t);
    c.classList.toggle("hidden", !(inList&&inPlat&&inQ));
  });
}
document.querySelectorAll(".nav").forEach(n=>n.addEventListener("click",()=>{
  document.querySelectorAll(".nav").forEach(x=>x.classList.remove("active"));
  n.classList.add("active");
  state.list=n.dataset.list;
  document.getElementById("title").textContent=n.querySelector("span").textContent;
  apply();
}));
document.querySelectorAll(".chip").forEach(ch=>ch.addEventListener("click",()=>{
  const p=ch.dataset.platform;
  ch.classList.toggle("on");
  if(state.plats.has(p))state.plats.delete(p);else state.plats.add(p);
  apply();
}));
const q=document.getElementById("q");
q.addEventListener("input",()=>{state.q=q.value;apply();});

// base des appels API : relatif si servi, absolu si ouvert en file://
const NBASE = location.protocol==="file:" ? "http://100.109.120.86:8787" : "";

// --- demande à ton carnet ---
const askIn=document.getElementById("ask"), askBtn=document.getElementById("askbtn"), ansBox=document.getElementById("answer");
async function doAsk(){
  const q=askIn.value.trim(); if(!q)return;
  ansBox.classList.remove("hidden"); ansBox.textContent="Je cherche dans ton carnet…"; askBtn.disabled=true;
  try{
    const b=new URLSearchParams(); b.set("q",q);
    const r=await fetch(NBASE+"/ask",{method:"POST",body:b});
    ansBox.textContent=await r.text();
  }catch(e){ ansBox.textContent="Oups, le carnet n'a pas répondu (serveur joignable ?)."; }
  askBtn.disabled=false;
}
askBtn&&askBtn.addEventListener("click",doAsk);
askIn&&askIn.addEventListener("keydown",e=>{if(e.key==="Enter")doAsk();});

// --- notes : sauvegarde auto + champ qui grandit ---
function grow(t){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,160)+"px";}
document.querySelectorAll("textarea.note").forEach(t=>{
  grow(t);
  t.addEventListener("input",()=>grow(t));
  t.addEventListener("change",()=>{
    const b=new URLSearchParams();b.set("id",t.dataset.id);b.set("text",t.value);
    fetch(NBASE+"/note",{method:"POST",body:b})
      .then(r=>{if(r.ok){t.classList.add("saved");setTimeout(()=>t.classList.remove("saved"),1000);}})
      .catch(()=>{});
  });
});
</script>
</body>
</html>"""
