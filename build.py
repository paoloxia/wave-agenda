#!/usr/bin/env python3
"""Wave 2026 agenda page (7-9 Oct), built from Sessionboard event 273.
Sections: Fucine, Binario 3, Masterclass (track Masterclass, Rooms A/B/C), Podcast (track Podcast).
Output: site/index.html (public, the agenda is public anyway). The token only lives in the GitHub Actions secret.
Runs every 15 min on GitHub Actions; locally: SESSIONBOARD_TOKEN=... python3 build.py"""
import html, json, os, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE, EVENT = "https://public-api-eu.sessionboard.com", 273
CEST = timezone(timedelta(hours=2))
DAYS = [("2026-10-07", "7 OTT"), ("2026-10-08", "8 OTT"), ("2026-10-09", "9 OTT")]
SECTIONS = ["Fucine", "Binario 3", "Masterclass", "Podcast"]


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


def person(p, mod=False):
    role = ", ".join(x.strip() for x in (p.get("title"), p.get("company_name")) if x and x.strip())
    lab = '<span class="ml">Moderatore</span>' if mod else ""
    return f'<li{" class=mod" if mod else ""}>{lab}<b>{html.escape(" ".join(p["full_name"].split()))}</b>' \
        + (f'<span class="r">{html.escape(role)}</span>' if role else "") + "</li>"


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
        secs, jump = [], []
        for k, name in enumerate(SECTIONS):
            rows = sorted((row(s) for s in data if s["starts_at"][:10] == day and section(s) == name and s["status"] != "accept_queue"), key=lambda x: x[0])
            if rows:
                sid = f"d{i}-{k}"
                jump.append(f'<a href="#{sid}">{name}</a>')
                secs.append(f'''<div class="room r{k}" id="{sid}"><h2>{name}<small>{len(rows)} sessioni</small></h2>
{"".join(r for _, r in rows)}</div>''')
        panes.append(f'<section data-d="{i}"{"" if i == 0 else " hidden"}><div class="jump">{"".join(jump)}</div>{"".join(secs)}</section>')
    return f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Wave 2026 Agenda</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Funnel+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#f6f6f4;--fg:#121212;--mut:#545454;--line:#e2e2de;--card:#fff;--acc:#6a1fe0;--live:#d4145a;
--r0:#6a1fe0;--r1:#0b7a6b;--r2:#c25a00;--r3:#c0177a}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0f0f10;--fg:#f4f4f4;--mut:#b0b0b0;--line:#2b2b2e;--card:#18181b;--acc:#b08cff;--live:#ff5c93;
--r0:#b08cff;--r1:#4fd1bd;--r2:#ffab5c;--r3:#ff7ac6}}}}
*{{box-sizing:border-box}}html{{scroll-padding-top:130px}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 "Funnel Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
header{{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
.bar{{max-width:960px;margin:0 auto;padding:12px 16px;display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center}}
h1{{font-size:20px;margin:0;font-weight:700;letter-spacing:-.01em}}h1 span{{color:var(--mut);font-weight:500}}
nav{{display:flex;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:3px}}
nav button{{font:inherit;font-weight:600;font-size:15px;min-height:40px;padding:0 16px;border:0;background:none;color:var(--fg);border-radius:9px;cursor:pointer;transition:background .15s}}
nav button.on{{background:var(--acc);color:#fff}}
input{{font:inherit;min-height:42px;padding:0 14px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--fg);flex:1 1 200px}}
.upd{{color:var(--mut);font-size:13px;margin:14px 0 0}}
:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
main{{max-width:960px;margin:0 auto;padding:8px 16px 64px}}
.jump{{display:flex;gap:8px;overflow-x:auto;margin:12px 0 4px;scrollbar-width:none}}.jump::-webkit-scrollbar{{display:none}}
.jump a{{white-space:nowrap;font-size:14px;font-weight:600;color:var(--fg);text-decoration:none;padding:8px 14px;border:1px solid var(--line);border-radius:999px;background:var(--card)}}
.room{{--rc:var(--r0);margin-top:28px}}.r1{{--rc:var(--r1)}}.r2{{--rc:var(--r2)}}.r3{{--rc:var(--r3)}}
h2{{display:flex;align-items:baseline;gap:10px;margin:0 0 12px;font-size:24px;letter-spacing:-.01em}}
h2::before{{content:"";width:10px;height:10px;border-radius:3px;background:var(--rc);align-self:center}}
h2 small{{font-size:14px;font-weight:500;color:var(--mut)}}
.s{{display:grid;grid-template-columns:76px 1fr;gap:16px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--rc);border-radius:12px;padding:16px;margin-bottom:10px}}
.t b{{display:block;font-size:20px;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}.t span{{color:var(--mut);font-size:14px;font-variant-numeric:tabular-nums}}
h3{{margin:0;font-size:18px;line-height:1.3;font-weight:650}}
.m{{margin:4px 0 0;color:var(--mut);font-size:14px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}}
.pend{{font-size:12px;font-weight:600;color:#8a5a00;background:#fff1cc;padding:2px 8px;border-radius:6px}}
.live{{display:none;font-size:12px;font-weight:700;color:#fff;background:var(--live);padding:2px 8px;border-radius:6px}}
ul{{list-style:none;margin:12px 0 0;padding:12px 0 0;border-top:1px solid var(--line);display:grid;gap:6px}}
li b{{font-weight:600;margin-right:8px}}li .r{{color:var(--mut);font-size:15px}}
li.mod{{margin-top:2px}}.ml{{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mut);border:1px solid var(--line);border-radius:5px;padding:0 6px;margin-right:8px;vertical-align:1px}}
.s.now{{border-color:var(--live);box-shadow:0 0 0 1px var(--live)}}.s.now .live{{display:inline-block}}
.s.past{{opacity:.5}}.h{{display:none!important}}
.empty{{display:none;color:var(--mut);padding:24px 0}}
@media (max-width:600px){{.s{{grid-template-columns:1fr;gap:6px;padding:14px}}.t b{{display:inline;font-size:17px;margin-right:6px}}h3{{font-size:17px}}.bar{{padding:10px 16px;gap:8px}}h1{{display:none}}nav{{flex:1}}nav button{{flex:1}}li .r{{display:block}}}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style></head><body>
<header><div class="bar"><h1>Wave 2026 <span>Agenda</span></h1><nav>{"".join(tabs)}</nav>
<input id="q" type="search" aria-label="Cerca" placeholder="Cerca titolo o speaker"></div></header>
<main><p class="upd">Dati Sessionboard, aggiornati alle {now:%H:%M} del {now:%d/%m}. La pagina si ricarica da sola.</p>{"".join(panes)}<p class="empty" id="none">Nessun risultato.</p></main>
<script>
const B=[...document.querySelectorAll("nav button")],S=[...document.querySelectorAll("main section")];
function show(i){{B.forEach(b=>b.classList.toggle("on",b.dataset.d==i));S.forEach(s=>s.hidden=s.dataset.d!=i);try{{localStorage.setItem("wa-day",i)}}catch(e){{}}}}
B.forEach(b=>b.onclick=()=>show(b.dataset.d));
const today=new Date().toLocaleDateString("sv-SE",{{timeZone:"Europe/Rome"}}),td=B.find(b=>b.dataset.day==today);
if(td)show(td.dataset.d);else try{{const d=localStorage.getItem("wa-day");if(d)show(d)}}catch(e){{}}
function tick(){{const n=Date.now()/1000;document.querySelectorAll(".s").forEach(a=>{{a.classList.toggle("now",n>=a.dataset.s&&n<a.dataset.e);a.classList.toggle("past",n>=a.dataset.e)}})}}
tick();setInterval(tick,60000);
document.getElementById("q").oninput=e=>{{const q=e.target.value.trim().toLowerCase();let any=false;
document.querySelectorAll(".room").forEach(r=>{{let k=0;r.querySelectorAll(".s").forEach(a=>{{const h=q&&!a.textContent.toLowerCase().includes(q);a.classList.toggle("h",h);if(!h)k++}});r.classList.toggle("h",!k);if(k&&!r.closest("section").hidden)any=true}});
document.querySelectorAll(".jump").forEach(j=>j.classList.toggle("h",!!q));document.getElementById("none").style.display=any?"none":"block"}};
setTimeout(()=>location.reload(),15*60*1000);
</script></body></html>'''


if __name__ == "__main__":
    out = Path("site")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page(sessions()))
    (out / ".nojekyll").touch()
