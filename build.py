#!/usr/bin/env python3
"""Wave 2026 agenda page (7-9 Oct), built from Sessionboard event 273.
Sections: Fucine, Binario 3, Masterclass (track Masterclass, Rooms A/B/C), Podcast (track Podcast).
Output: site/index.html (public, the agenda is public anyway). The token only lives in the GitHub Actions secret.
Runs every 15 min on GitHub Actions; locally: SESSIONBOARD_TOKEN=... python3 build.py"""
import base64, hashlib, html, io, json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE, EVENT = "https://public-api-eu.sessionboard.com", 273
CEST = timezone(timedelta(hours=2))
DAYS = [("2026-10-07", "7 OTT"), ("2026-10-08", "8 OTT"), ("2026-10-09", "9 OTT")]
SECTIONS = ["Fucine", "Binario 3", "Masterclass", "Podcast"]
# Desktop columns side by side: Masterclass + Podcast share the third column, split in two.
COLS = [["Fucine"], ["Binario 3"], ["Masterclass", "Podcast"]]


def sessions():
    out, page = [], 1
    while True:
        req = urllib.request.Request(
            f"{BASE}/v1/event/{EVENT}/sessions?page={page}&pageSize=100", method="POST",
            data=b'{"filters":{},"sort":{}}',
            headers={"X-Access-Token": os.environ["SESSIONBOARD_TOKEN"], "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=60))
        out += r["results"]
        if page >= r["pagination"]["totalPages"]:
            return out
        page += 1


def section(s):
    room, track = (s.get("room") or {}).get("name"), (s.get("track") or {}).get("name")
    if track in ("Masterclass", "Podcast"):
        return track
    return room if room in ("Fucine", "Binario 3") else None


THUMBS = {}
DISPLAY = json.load(open(Path(__file__).with_name("display.json")))
LOGO = "data:image/svg+xml;base64," + base64.b64encode(Path(__file__).with_name("logo-wave.svg").read_bytes()).decode()


def display(word, cls):
    """PP Rader Light as vector paths (the licensed TTF is never published)."""
    g = DISPLAY.get(word.upper())
    if not g:
        return f'<span class="{cls} fb">{html.escape(word)}</span>'
    return f'<svg class="{cls}" viewBox="{g["vb"]}" role="img" aria-label="{html.escape(word)}"><path d="{g["d"]}"/></svg>'


def thumb(url):
    """Headshot (already B/W on Sessionboard) -> 240px square jpg, face kept near the top."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(url, timeout=30).read())).convert("L")
    except Exception:
        return url, None
    name = "h/" + hashlib.sha1(url.encode()).hexdigest()[:16] + ".jpg"
    ImageOps.fit(im, (240, 240), centering=(0.5, 0.3)).save(Path("site") / name, quality=82)
    return url, name


def person(p, mod=False):
    role = ", ".join(x.strip() for x in (p.get("title"), p.get("company_name")) if x and x.strip())
    name = html.escape(" ".join(p["full_name"].split()))
    img = f'<img src="{THUMBS[p["photo_url"]]}" alt="" loading="lazy">' if THUMBS.get(p.get("photo_url")) \
        else f'<span class="ph">{name[:1]}</span>'
    lab = '<span class="ml">Moderatore</span>' if mod else ""
    return f'<li{" class=mod" if mod else ""}>{img}<div>{lab}<b>{name}</b>' \
        + (f'<span class="r">{html.escape(role)}</span>' if role else "") + "</div></li>"


def row(s):
    t0 = datetime.fromisoformat(s["starts_at"].replace("Z", "+00:00")).astimezone(CEST)
    t1 = datetime.fromisoformat(s["ends_at"].replace("Z", "+00:00")).astimezone(CEST)
    mods = list({p["id"]: p for p in s["moderators"] + s.get("chairpersons", [])}.values())
    spk = {p["id"]: p for p in s["speakers"] + s.get("participants", []) if p["id"] not in {m["id"] for m in mods}}
    who = "".join(person(p) for p in sorted(spk.values(), key=lambda p: p.get("order") or 0)) \
        + "".join(person(p, True) for p in mods)
    meta = [(s.get("format") or {}).get("name") or ""]
    if section(s) in ("Masterclass", "Podcast"):
        meta.append((s.get("room") or {}).get("name") or "")
    meta = " · ".join(html.escape(m) for m in meta if m)
    pend = '<span class="pend">Da confermare</span>' if s["status"] != "accepted" else ""
    return t0, f'''<article class="s" data-s="{int(t0.timestamp())}" data-e="{int(t1.timestamp())}">
<div class="t"><b>{t0:%H:%M}</b><span>{t1:%H:%M}</span></div>
<div class="c"><h3>{html.escape(" ".join(s["title"].split()))}</h3><p class="m">{meta}{pend}<span class="live">In corso</span></p>
{f'<ul>{who}</ul>' if who else ''}</div></article>'''


def page(data):
    now = datetime.now(CEST)
    tabs, panes = [], []
    for i, (day, label) in enumerate(DAYS):
        tabs.append(f'<button data-d="{i}" data-day="{day}"{" class=on" if i == 0 else ""}>{label}</button>')
        cols, jump = [], []
        for group in COLS:
            secs = []
            for name in group:
                k = SECTIONS.index(name)
                rows = sorted((row(s) for s in data if s["starts_at"][:10] == day and section(s) == name and s["status"] != "accept_queue"), key=lambda x: x[0])
                if rows:
                    sid = f"d{i}-{k}"
                    jump.append(f'<a href="#{sid}">{name}</a>')
                    secs.append(f'''<div class="room r{k}" id="{sid}"><h2>{display(name, "dt")}<small>{len(rows)} sessioni</small></h2>
{"".join(r for _, r in rows)}</div>''')
            if secs:
                cols.append(f'<div class="grp g{len(secs)}">{"".join(secs)}</div>' if len(group) > 1 else secs[0])
        panes.append(f'<section data-d="{i}"{"" if i == 0 else " hidden"}><div class="jump">{"".join(jump)}</div><div class="cols">{"".join(cols)}</div></section>')
    return f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Wave 2026 Agenda</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Funnel+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#111111;--fg:#FBFBFB;--mut:#A8A8A8;--line:rgba(251,251,251,.14);--card:#111111;--acc:#DA34FF;--live:#DA34FF;color-scheme:dark}}
*{{box-sizing:border-box}}html{{scroll-padding-top:130px}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 "Funnel Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
header{{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
.bar{{max-width:1440px;margin:0 auto;padding:12px 16px;display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center}}
h1{{display:flex;align-items:center;gap:14px;margin:0}}h1 .logo{{height:30px;width:auto}}h1 .at{{height:15px;width:auto;fill:var(--mut)}}
nav{{display:flex;border:1px solid var(--line);border-radius:4px;padding:3px}}
nav button{{font:inherit;font-weight:600;font-size:15px;min-height:40px;padding:0 16px;border:0;background:none;color:var(--fg);border-radius:2px;cursor:pointer;transition:background .15s}}
nav button.on{{background:var(--fg);color:var(--bg)}}nav button.on::after{{content:"";display:block;height:2px;background:var(--acc);margin:-3px 6px 0}}
input{{font:inherit;min-height:42px;padding:0 14px;border:1px solid var(--line);border-radius:4px;background:var(--card);color:var(--fg);flex:1 1 200px}}
.upd{{color:var(--mut);font-size:13px;margin:14px 0 0}}
:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
main{{max-width:1440px;margin:0 auto;padding:8px 16px 64px}}
.jump{{display:flex;gap:8px;overflow-x:auto;margin:12px 0 4px;scrollbar-width:none}}.jump::-webkit-scrollbar{{display:none}}
.jump a{{white-space:nowrap;font-size:14px;font-weight:600;color:var(--fg);text-decoration:none;padding:8px 14px;border:1px solid var(--line);border-radius:4px;background:transparent}}
.room{{margin-top:40px}}
h2{{display:flex;align-items:flex-end;gap:10px;margin:0 0 12px;font-size:24px;letter-spacing:-.01em;position:sticky;top:var(--hh,64px);z-index:2;background:var(--bg);padding:10px 0}}
h2 .dt{{height:26px;width:auto;fill:var(--fg)}}h2 .fb{{font-size:28px;font-weight:300;text-transform:uppercase}}
h2 small{{white-space:nowrap;font-size:14px;font-weight:500;color:var(--mut)}}
.s{{display:grid;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:4px;padding:14px;margin-bottom:10px}}
.t b{{display:inline;margin-right:6px;font-size:17px;font-weight:500;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}.t span{{color:var(--mut);font-size:14px;font-variant-numeric:tabular-nums}}
h3{{margin:0;font-size:17px;line-height:1.3;font-weight:650}}
.m{{margin:4px 0 0;color:var(--mut);font-size:14px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}}
.pend{{font-size:12px;font-weight:600;color:var(--fg);border:1px solid var(--mut);padding:1px 8px;border-radius:4px}}
.live{{display:none;font-size:12px;font-weight:700;color:var(--acc);border:1px solid var(--acc);padding:1px 8px;border-radius:4px}}
ul{{list-style:none;margin:8px 0 0;padding:12px 0 0;border-top:1px solid var(--line);display:grid;gap:10px}}
li{{display:flex;align-items:center;gap:10px;min-width:0}}li div{{display:flex;flex-direction:column;align-items:flex-start;gap:1px;min-width:0}}
li img,li .ph{{flex:none;width:48px;height:48px;border-radius:4px;object-fit:cover;object-position:50% 30%;background:var(--line);filter:grayscale(1)}}
li .ph{{display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:var(--mut)}}
li b{{font-weight:600;font-size:15px;line-height:1.25}}li .r{{color:var(--mut);font-size:13px;line-height:1.3}}
.ml{{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);border:1px solid var(--line);border-radius:4px;padding:0 6px;margin-bottom:2px}}
.s.now{{border-color:var(--live);box-shadow:0 0 0 1px var(--live)}}.s.now .live{{display:inline-block}}
.s.past{{opacity:.5}}.h{{display:none!important}}
.empty{{display:none;color:var(--mut);padding:24px 0}}
.fold{{font:inherit;font-size:13px;font-weight:600;width:100%;min-height:40px;margin:0 0 10px;border:1px dashed var(--line);border-radius:4px;background:none;color:var(--mut);cursor:pointer}}
body:not(.q) .room.shut .s.past{{display:none}}body.q .fold{{display:none}}
@media (min-width:1000px){{.jump{{display:none}}.cols{{display:grid;grid-template-columns:1fr 1fr 1.7fr;gap:20px;align-items:start;margin-top:12px}}
.cols>*+*{{border-left:1px solid var(--line);padding-left:20px}}.room{{margin-top:0}}
.grp{{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}}.grp.g1{{grid-template-columns:1fr}}.grp h2 .dt{{height:22px}}}}
@media (max-width:600px){{.bar{{padding:10px 16px;gap:8px}}h1{{width:100%}}h1 .logo{{height:24px}}h1 .at{{height:12px}}nav{{flex:1}}nav button{{flex:1}}}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style></head><body>
<header><div class="bar"><h1><img class="logo" src="{LOGO}" alt="Wave by Vento">{display("Agenda", "at")}</h1><nav>{"".join(tabs)}</nav>
<input id="q" type="search" aria-label="Cerca" placeholder="Cerca titolo o speaker"></div></header>
<main><p class="upd">Dati Sessionboard, aggiornati alle {now:%H:%M} del {now:%d/%m}. La pagina si ricarica da sola.</p>{"".join(panes)}<p class="empty" id="none">Nessun risultato.</p></main>
<script>
const B=[...document.querySelectorAll("nav button")],S=[...document.querySelectorAll("main section")];
function show(i){{B.forEach(b=>b.classList.toggle("on",b.dataset.d==i));S.forEach(s=>s.hidden=s.dataset.d!=i);try{{localStorage.setItem("wa-day",i)}}catch(e){{}}}}
B.forEach(b=>b.onclick=()=>show(b.dataset.d));
const today=new Date().toLocaleDateString("sv-SE",{{timeZone:"Europe/Rome"}}),td=B.find(b=>b.dataset.day==today);
if(td)show(td.dataset.d);else try{{const d=localStorage.getItem("wa-day");if(d)show(d)}}catch(e){{}}
const H=document.querySelector("header"),hh=()=>document.documentElement.style.setProperty("--hh",H.offsetHeight+"px");hh();addEventListener("resize",hh);
// Past sessions folded per column, so the page opens on what is live / next in every room.
document.querySelectorAll(".room").forEach(r=>{{const b=document.createElement("button");b.className="fold";b.hidden=true;r.querySelector("h2").after(b);r.classList.add("shut");
b.onclick=()=>{{r.classList.toggle("shut");lab(r)}}}});
function lab(r){{const k=r.querySelectorAll(".s.past").length,b=r.querySelector(".fold");b.hidden=!k;b.textContent=r.classList.contains("shut")?`Mostra ${{k}} ${{k==1?"sessione conclusa":"sessioni concluse"}}`:"Nascondi sessioni concluse"}}
function tick(){{const n=Date.now()/1000;document.querySelectorAll(".s").forEach(a=>{{a.classList.toggle("now",n>=a.dataset.s&&n<a.dataset.e);a.classList.toggle("past",n>=a.dataset.e)}});document.querySelectorAll(".room").forEach(lab)}}
tick();setInterval(tick,60000);
// Today already over (evening): open on the next day instead of a wall of folded rooms.
if(td&&!S[td.dataset.d].querySelector(".s:not(.past)")&&B[+td.dataset.d+1])show(+td.dataset.d+1);
document.getElementById("q").oninput=e=>{{const q=e.target.value.trim().toLowerCase();let any=false;document.body.classList.toggle("q",!!q);
document.querySelectorAll(".room").forEach(r=>{{let k=0;r.querySelectorAll(".s").forEach(a=>{{const h=q&&!a.textContent.toLowerCase().includes(q);a.classList.toggle("h",h);if(!h)k++}});r.classList.toggle("h",!k);if(k&&!r.closest("section").hidden)any=true}});
document.querySelectorAll(".jump").forEach(j=>j.classList.toggle("h",!!q));document.getElementById("none").style.display=any?"none":"block"}};
setTimeout(()=>location.reload(),15*60*1000);
</script></body></html>'''


if __name__ == "__main__":
    out = Path("site")
    out.mkdir(exist_ok=True)
    (out / "h").mkdir(exist_ok=True)
    data = sessions()
    urls = {p["photo_url"] for x in data for p in x["speakers"] + x["moderators"] + x.get("participants", []) if p.get("photo_url")}
    with ThreadPoolExecutor(16) as ex:
        THUMBS.update((u, n) for u, n in ex.map(thumb, urls) if n)
    (out / "index.html").write_text(page(data))
    (out / ".nojekyll").touch()
