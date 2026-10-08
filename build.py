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
DAYS = [("2026-10-07", "Wed 7"), ("2026-10-08", "Thu 8"), ("2026-10-09", "Fri 9")]
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
    co, role = ((p.get(k) or "").strip() for k in ("company_name", "title"))
    name = html.escape(" ".join(p["full_name"].split()))
    img = f'<img src="{THUMBS[p["photo_url"]]}" alt="" loading="lazy">' if THUMBS.get(p.get("photo_url")) \
        else f'<span class="ph">{name[:1]}</span>'
    lab = '<span class="ml">Moderator</span>' if mod else ""
    return f'<li{" class=mod" if mod else ""}>{img}<div>{lab}<b>{name}</b>' \
        + (f'<span class="co">{html.escape(co)}</span>' if co else "") \
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
    pend = '<span class="pend">To be confirmed</span>' if s["status"] != "accepted" else ""
    return t0, f'''<article class="s" data-s="{int(t0.timestamp())}" data-e="{int(t1.timestamp())}">
<div class="t"><b>{t0:%H:%M}</b><span>– {t1:%H:%M}</span></div>
<div class="c"><h3>{html.escape(" ".join(s["title"].split()))}</h3><p class="m">{meta}{pend}<span class="live">Live now</span></p>
{f'<ul>{who}</ul>' if who else ''}</div></article>'''


def page(data):
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
                    jump.append(f'<button data-r="{name}">{name}</button>')
                    secs.append(f'''<div class="room r{k}" id="{sid}" data-r="{name}"><h2>{display(name, "dt")}<small>{len(rows)} sessions</small></h2>
{"".join(r for _, r in rows)}</div>''')
            if secs:
                cols.append(f'<div class="grp g{len(secs)}">{"".join(secs)}</div>' if len(group) > 1 else secs[0])
        panes.append(f'<section data-d="{i}"{"" if i == 0 else " hidden"}><div class="now-box" hidden></div><div class="jump" role="tablist">{"".join(jump)}</div><div class="cols">{"".join(cols)}</div></section>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Wave 2026 Agenda</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Funnel+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#111111;--fg:#FBFBFB;--mut:#A8A8A8;--line:rgba(251,251,251,.14);--acc:#DA34FF;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 "Funnel Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%}}
header{{position:sticky;top:0;z-index:10;background:var(--bg);border-bottom:1px solid var(--line)}}
.bar{{max-width:1440px;margin:0 auto;padding:12px 16px;display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center}}
h1{{display:flex;align-items:center;gap:12px;margin:0;flex:1}}h1 .logo{{height:28px;width:auto}}h1 .at{{height:14px;width:auto;fill:var(--mut)}}
nav{{display:flex;border:1px solid var(--line);border-radius:4px;padding:3px}}
nav button{{font:inherit;font-weight:600;font-size:15px;min-height:42px;padding:0 18px;border:0;background:none;color:var(--fg);border-radius:2px;cursor:pointer}}
nav button.on{{background:var(--fg);color:var(--bg)}}nav button.on::after{{content:"";display:block;height:2px;background:var(--acc);margin:-4px 8px 0}}
:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
main{{max-width:1440px;margin:0 auto;padding:0 16px 64px}}
input{{display:block;width:100%;font:inherit;min-height:44px;margin:16px 0 0;padding:0 14px;border:1px solid var(--line);border-radius:4px;background:var(--bg);color:var(--fg)}}
.now-box{{margin:16px 0 0;border:1px solid var(--line);border-radius:4px;padding:4px 14px}}
.now-box h4{{margin:10px 0 2px;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}}
.now-box button{{display:grid;grid-template-columns:92px 1fr;gap:12px;width:100%;text-align:left;font:inherit;color:var(--fg);background:none;border:0;border-top:1px solid var(--line);padding:10px 0;cursor:pointer}}
.now-box h4+button{{border-top:0}}.now-box .rn{{font-weight:600;font-size:14px}}.now-box .tt{{font-size:14px;line-height:1.35}}
.now-box .tm{{display:block;color:var(--mut);font-size:12px;font-weight:600}}.now-box .tm.on{{color:var(--acc)}}
.jump{{position:sticky;top:var(--hh,110px);z-index:5;background:var(--bg);display:flex;gap:6px;overflow-x:auto;margin:12px -16px 0;padding:10px 16px;border-bottom:1px solid var(--line);scrollbar-width:none}}.jump::-webkit-scrollbar{{display:none}}
.jump button{{font:inherit;font-weight:600;font-size:15px;white-space:nowrap;min-height:40px;padding:0 14px;border:1px solid var(--line);border-radius:4px;background:none;color:var(--fg);cursor:pointer}}
.jump button.on{{background:var(--fg);color:var(--bg);border-color:var(--fg)}}
.room{{margin-top:20px}}
h2{{display:flex;align-items:flex-end;gap:10px;margin:0 0 12px;background:var(--bg);padding:6px 0}}
h2 .dt{{height:24px;width:auto;fill:var(--fg)}}h2 .fb{{font-size:28px;font-weight:300;text-transform:uppercase}}
h2 small{{white-space:nowrap;font-size:13px;font-weight:500;color:var(--mut)}}
.s{{display:grid;gap:4px;border:1px solid var(--line);border-radius:4px;padding:14px;margin-bottom:10px;scroll-margin-top:calc(var(--hh,110px) + 76px)}}
.t b{{margin-right:4px;font-size:18px;font-weight:600;font-variant-numeric:tabular-nums}}.t span{{color:var(--mut);font-size:15px;font-variant-numeric:tabular-nums}}
h3{{margin:0;font-size:17px;line-height:1.3;font-weight:650}}
.m{{margin:2px 0 0;color:var(--mut);font-size:14px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}}
.pend{{font-size:12px;font-weight:600;color:var(--fg);border:1px solid var(--mut);padding:1px 8px;border-radius:4px}}
.live{{display:none;font-size:12px;font-weight:700;color:var(--acc);border:1px solid var(--acc);padding:1px 8px;border-radius:4px}}
ul{{list-style:none;margin:10px 0 0;padding:12px 0 0;border-top:1px solid var(--line);display:grid;gap:12px}}
li{{display:flex;align-items:center;gap:12px;min-width:0}}li div{{display:flex;flex-direction:column;align-items:flex-start;min-width:0}}
li img,li .ph{{flex:none;width:52px;height:52px;border-radius:4px;object-fit:cover;object-position:50% 30%;background:var(--line)}}
li .ph{{display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:var(--mut)}}
li b{{font-weight:650;font-size:15px;line-height:1.25}}
li .co{{font-size:14px;font-weight:500;line-height:1.3;margin-top:2px}}li .r{{color:var(--mut);font-size:13px;line-height:1.3}}
.ml{{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);border:1px solid var(--line);border-radius:4px;padding:0 6px;margin-bottom:3px}}
.s.now{{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}}.s.now .live{{display:inline-block}}
.s.past{{opacity:.5}}.h{{display:none!important}}
.empty{{display:none;color:var(--mut);padding:24px 0}}
.fold{{font:inherit;font-size:13px;font-weight:600;width:100%;min-height:42px;margin:0 0 10px;border:1px dashed var(--line);border-radius:4px;background:none;color:var(--mut);cursor:pointer}}
body:not(.q) .room.shut .s.past{{display:none}}body.q .fold,body.q .now-box{{display:none}}
@media (max-width:999px){{body:not(.q) .room:not(.sel){{display:none}}}}
@media (min-width:1000px){{.jump{{display:none}}.cols{{display:grid;grid-template-columns:1fr 1fr 1.7fr;gap:20px;align-items:start;margin-top:16px}}
.now-box{{display:grid;grid-template-columns:repeat(4,1fr);gap:0 20px}}.now-box h4{{grid-column:1/-1}}.now-box h4+button{{border-top:1px solid var(--line)}}
.cols>*+*{{border-left:1px solid var(--line);padding-left:20px}}.room{{margin-top:0}}h2{{position:sticky;top:var(--hh,64px);z-index:2}}
.grp{{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}}.grp.g1{{grid-template-columns:1fr}}.grp h2 .dt{{height:22px}}}}
@media (max-width:600px){{.jump button{{flex:1 1 auto;padding:0 10px;font-size:14px}}nav{{flex:1 1 100%}}nav button{{flex:1;padding:0 8px}}h1 .logo{{height:24px}}h1 .at{{height:12px}}}}
</style></head><body>
<header><div class="bar"><h1><img class="logo" src="{LOGO}" alt="Wave by Vento">{display("Agenda", "at")}</h1><nav aria-label="Day">{"".join(tabs)}</nav></div></header>
<main><input id="q" type="search" aria-label="Search" placeholder="Search session, speaker or company">{"".join(panes)}<p class="empty" id="none">No results.</p></main>
<script>
const B=[...document.querySelectorAll("nav button")],S=[...document.querySelectorAll("main section")],H=document.querySelector("header");
const get=k=>{{try{{return localStorage.getItem(k)}}catch(e){{}}}},put=(k,v)=>{{try{{localStorage.setItem(k,v)}}catch(e){{}}}};
let room=get("wa-room");
// Mobile: one room at a time, chosen from the sticky room tabs (desktop shows all rooms as columns).
function pick(sec,name){{const R=[...sec.querySelectorAll(".room")];if(!R.some(r=>r.dataset.r==name))name=R[0]&&R[0].dataset.r;
R.forEach(r=>r.classList.toggle("sel",r.dataset.r==name));sec.querySelectorAll(".jump button").forEach(b=>{{b.classList.toggle("on",b.dataset.r==name);b.setAttribute("aria-selected",b.dataset.r==name)}})}}
function show(i){{B.forEach(b=>b.classList.toggle("on",b.dataset.d==i));S.forEach(s=>s.hidden=s.dataset.d!=i);pick(S[i],room);put("wa-day",i)}}
B.forEach(b=>b.onclick=()=>show(b.dataset.d));
document.querySelectorAll(".jump").forEach(j=>j.onclick=e=>{{const b=e.target.closest("button");if(!b)return;room=b.dataset.r;put("wa-room",room);pick(j.closest("section"),room);
const y=j.parentNode.querySelector(".cols").getBoundingClientRect().top+scrollY-H.offsetHeight-j.offsetHeight;if(scrollY>y)scrollTo(0,y)}});
const hh=()=>document.documentElement.style.setProperty("--hh",H.offsetHeight+"px");hh();addEventListener("resize",hh);
// Past sessions folded per room, so the page opens on what is live / next.
document.querySelectorAll(".room").forEach(r=>{{const b=document.createElement("button");b.className="fold";b.hidden=true;r.querySelector("h2").after(b);r.classList.add("shut");
b.onclick=()=>{{r.classList.toggle("shut");lab(r)}}}});
function lab(r){{const k=r.querySelectorAll(".s.past").length,b=r.querySelector(".fold");b.hidden=!k;b.textContent=r.classList.contains("shut")?`Show ${{k}} past ${{k==1?"session":"sessions"}}`:"Hide past sessions"}}
const today=new Date().toLocaleDateString("sv-SE",{{timeZone:"Europe/Rome"}}),td=B.find(b=>b.dataset.day==today);
const hm=t=>new Date(t*1000).toLocaleTimeString("en-GB",{{timeZone:"Europe/Rome",hour:"2-digit",minute:"2-digit"}});
const el=(t,c,x)=>{{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e}};
// "Now in the rooms": what is on (or next) in every room, today only.
function nowBox(){{if(!td)return;const sec=S[td.dataset.d],box=sec.querySelector(".now-box");const hd=el("h4","","Now in the rooms");box.replaceChildren(hd);
sec.querySelectorAll(".room").forEach(r=>{{const a=r.querySelector(".s.now")||r.querySelector(".s:not(.past)");if(!a)return;const on=a.classList.contains("now");
const b=el("button");b.append(el("span","rn",r.dataset.r));const d=el("span","tt");d.append(el("span","tm"+(on?" on":""),on?"Live now, until "+hm(a.dataset.e):"At "+hm(a.dataset.s)),a.querySelector("h3").textContent);b.append(d);
b.onclick=()=>{{room=r.dataset.r;pick(sec,room);a.scrollIntoView({{behavior:"smooth"}})}};box.append(b)}});if(!sec.querySelector(".s.now"))hd.textContent="Up next in the rooms";box.hidden=box.children.length<2}}
function tick(){{const n=Date.now()/1000;document.querySelectorAll(".s").forEach(a=>{{a.classList.toggle("now",n>=a.dataset.s&&n<a.dataset.e);a.classList.toggle("past",n>=a.dataset.e)}});document.querySelectorAll(".room").forEach(lab);nowBox()}}
tick();setInterval(tick,60000);
if(td)show(td.dataset.d);else show(get("wa-day")||0);
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
