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


def person(p):
    role = ", ".join(x.strip() for x in (p.get("title"), p.get("company_name")) if x and x.strip())
    return f'<b>{html.escape(p["full_name"].strip())}</b>' + (f' <span class="r">{html.escape(role)}</span>' if role else "")


def row(s):
    t0 = datetime.fromisoformat(s["starts_at"].replace("Z", "+00:00")).astimezone(CEST)
    t1 = datetime.fromisoformat(s["ends_at"].replace("Z", "+00:00")).astimezone(CEST)
    mods = list({p["id"]: p for p in s["moderators"] + s.get("chairpersons", [])}.values())
    spk = {p["id"]: p for p in s["speakers"] + s.get("participants", []) if p["id"] not in {m["id"] for m in mods}}
    who = "<br>".join(person(p) for p in sorted(spk.values(), key=lambda p: p.get("order") or 0))
    if mods:
        who += ("<br>" if who else "") + "(" + "; ".join("mod. " + person(p) for p in mods) + ")"
    fmt = (s.get("format") or {}).get("name") or ""
    room = (s.get("room") or {}).get("name") or ""
    tags = (f'<span class="tag">{html.escape(room)}</span>' if section(s) in ("Masterclass", "Podcast") else "") \
        + ('<span class="tag pend">pending</span>' if s["status"] != "accepted" else "")
    return t0, f'''<tr><td class="t">{t0:%H:%M}<span>{t1:%H:%M}</span></td>
<td><div class="ti">{html.escape(s["title"].strip())}</div>{tags}</td><td class="f">{html.escape(fmt)}</td><td>{who}</td></tr>'''


def page(data):
    now = datetime.now(CEST)
    tabs, panes = [], []
    for i, (day, label) in enumerate(DAYS):
        tabs.append(f'<button data-d="{i}"{" class=on" if i == 0 else ""}>{label}</button>')
        secs = []
        for name in SECTIONS:
            rows = sorted((row(s) for s in data if s["starts_at"][:10] == day and section(s) == name and s["status"] != "accept_queue"), key=lambda x: x[0])
            if rows:
                secs.append(f'''<h2>{name} <small>{len(rows)}</small></h2><div class="w"><table>
<thead><tr><th>Ora</th><th>Titolo</th><th>Formato</th><th>Speaker (moderatore)</th></tr></thead>
<tbody>{"".join(r for _, r in rows)}</tbody></table></div>''')
        panes.append(f'<section data-d="{i}"{"" if i == 0 else " hidden"}>{"".join(secs)}</section>')
    return f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Wave 2026 Agenda</title>
<link href="https://fonts.googleapis.com/css2?family=Funnel+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fbfbfb;--fg:#111;--mut:#6b6b6b;--line:#e3e3e3;--acc:#7b2cff;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#fbfbfb;--mut:#a8a8a8;--line:#2a2a2a;--acc:#b38bff;--card:#181818}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 "Funnel Sans",system-ui,sans-serif}}
header{{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;z-index:2;display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
h1{{font-size:18px;margin:0 12px 0 0}}nav{{display:flex;gap:6px}}
nav button{{font:inherit;font-weight:600;padding:6px 14px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:999px;cursor:pointer}}
nav button.on{{background:var(--acc);border-color:var(--acc);color:#fff}}
input{{font:inherit;padding:6px 12px;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--fg);flex:1;min-width:160px;max-width:320px}}
.upd{{color:var(--mut);font-size:12px;margin-left:auto}}
main{{padding:0 16px 40px;max-width:1300px;margin:0 auto}}h2{{margin:28px 0 8px;font-size:20px}}h2 small{{color:var(--mut);font-weight:400;font-size:14px}}
.w{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;background:var(--card)}}
th{{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);padding:8px;border-bottom:1px solid var(--line)}}
td{{padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}}
td.t{{white-space:nowrap;font-weight:700}}td.t span{{display:block;font-weight:400;color:var(--mut);font-size:13px}}
td.f{{color:var(--mut);white-space:nowrap}}.ti{{font-weight:600}}.r{{color:var(--mut)}}
.tag{{display:inline-block;font-size:11px;padding:1px 8px;border-radius:999px;border:1px solid var(--line);color:var(--mut);margin:4px 4px 0 0}}.tag.pend{{border-color:#e0a000;color:#e0a000}}
tr.h{{display:none}}
@media (max-width:700px){{th:nth-child(3),td.f{{display:none}}td{{font-size:14px}}}}
</style></head><body>
<header><h1>Wave 2026 · Agenda</h1><nav>{"".join(tabs)}</nav><input id="q" placeholder="Cerca titolo o speaker"><span class="upd">Sessionboard, aggiornato {now:%d/%m %H:%M}</span></header>
<main>{"".join(panes)}</main>
<script>
const B=document.querySelectorAll("nav button"),S=document.querySelectorAll("main section");
function show(i){{B.forEach(b=>b.classList.toggle("on",b.dataset.d==i));S.forEach(s=>s.hidden=s.dataset.d!=i);try{{localStorage.setItem("wa-day",i)}}catch(e){{}}}}
B.forEach(b=>b.onclick=()=>show(b.dataset.d));
try{{const d=localStorage.getItem("wa-day");if(d)show(d)}}catch(e){{}}
document.getElementById("q").oninput=e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll("tbody tr").forEach(r=>r.classList.toggle("h",q&&!r.textContent.toLowerCase().includes(q)))}};
setTimeout(()=>location.reload(),15*60*1000);
</script></body></html>'''


if __name__ == "__main__":
    out = Path("site")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page(sessions()))
    (out / ".nojekyll").touch()
