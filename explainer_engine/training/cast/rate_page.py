"""The rating page for the new-world pictures (ვანო 2026-10-26 12:50 Tbilisi): every picture with four grades (ideal, good,
similar but with problems, bad), the reasons (palette wrong, outline of the people or the world, scene logic) and a free
field for his own reason; Claude's check (cast.check) and Claude's look are shown beside each picture.

Writes <out>/index.html and <out>/img/<name>.jpg (768 px thumbnails); the page keeps the grades in the artifact's `db`
(collection "ratings", one doc per picture: {level, reasons, note, at}), so Claude reads them back with ArtifactData.

    python -m explainer_engine.training.cast.rate_page <world dir> <out dir> [--looks looks.json]
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

LEVELS = [("ideal", "იდეალურია"), ("good", "კარგია"), ("close", "ჰგავს, მაგრამ პრობლემებია"), ("bad", "ცუდია")]
REASONS = [("palette", "ფერთა გამა არ ვარგა"), ("outline", "გმირების ან სამყაროს მოხაზულობა"), ("logic", "სცენის ლოგიკა")]
KINDS = {"person": "ადამიანები", "place": "ადგილები", "object": "საგნები"}


def kept(world):
    """The picture kept per id (the last PASS or REVIEW; else the last drawn), with its check row."""
    best = {}
    for line in (Path(world) / "report.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("verdict") == "ERROR" or not (Path(world) / f"{r['name']}.png").exists():
            continue
        if r.get("id") not in best or r["verdict"] in ("PASS", "REVIEW") or best[r["id"]]["verdict"] == "FAIL":
            best[r.get("id", r["name"])] = r
    return best


def build(world, out, looks=None, descs=None):
    from PIL import Image
    world, out = Path(world), Path(out)
    (out / "img").mkdir(parents=True, exist_ok=True)
    rows = []
    for i, r in sorted(kept(world).items()):
        with Image.open(world / f"{r['name']}.png") as im:
            im = im.convert("RGB"); im.thumbnail((768, 768)); im.save(out / "img" / f"{r['name']}.jpg", quality=84)
        rows.append({"name": r["name"], "id": i, "kind": r["kind"], "check": r["verdict"], "why": r.get("why", []),
                     "look": (looks or {}).get(r["name"], ""), "desc": (descs or {}).get(i, "")})
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("@DATA@", data).replace("@LEVELS@", json.dumps(LEVELS, ensure_ascii=False)) \
        .replace("@REASONS@", json.dumps(REASONS, ensure_ascii=False)).replace("@KINDS@", json.dumps(KINDS, ensure_ascii=False))
    (out / "index.html").write_text(page, encoding="utf-8")
    return rows


TEMPLATE = r"""<title>ახალი სამყაროს შეფასება</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root{--bg:#f4efe6;--card:#fffaf1;--fg:#221c18;--mut:#6d6258;--line:#d9cfc0;--acc:#1f2d5c;--ideal:#2e6b3a;--good:#5d8a3a;--close:#c47a1c;--bad:#b0202e;--chip:#ece3d4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17140f;--card:#211d17;--fg:#f1e9dc;--mut:#a89c8c;--line:#3a3329;--acc:#9fb3ee;--ideal:#6fbf7d;--good:#a6cf6f;--close:#e7a64a;--bad:#ef6b75;--chip:#2c2620;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#17140f;--card:#211d17;--fg:#f1e9dc;--mut:#a89c8c;--line:#3a3329;--acc:#9fb3ee;--ideal:#6fbf7d;--good:#a6cf6f;--close:#e7a64a;--bad:#ef6b75;--chip:#2c2620;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,"Noto Sans Georgian",sans-serif;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:12px 40px}
header{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding-block:8px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
h1{font-size:18px;margin:0;text-wrap:balance}
.tabs,.filters{display:flex;flex-wrap:wrap;gap:6px}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:8px;padding:6px 10px;cursor:pointer}
button[aria-pressed="true"]{background:var(--acc);color:var(--bg);border-color:var(--acc)}
#count{color:var(--mut);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin-top:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column;min-width:0}
.card img{width:100%;max-width:100%;display:block;background:var(--chip);cursor:zoom-in}
.body{padding:10px;display:flex;flex-direction:column;gap:8px}
.meta{font-size:12px;color:var(--mut);display:flex;justify-content:space-between;gap:6px;flex-wrap:wrap}
.check{font-weight:600}.check.PASS{color:var(--ideal)}.check.REVIEW{color:var(--close)}.check.FAIL{color:var(--bad)}
.look{font-size:13px;background:var(--chip);border-radius:8px;padding:6px 8px}
.levels{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.levels button{font-size:13px;padding:7px 6px}
.levels button[data-l="ideal"][aria-pressed="true"]{background:var(--ideal);border-color:var(--ideal)}
.levels button[data-l="good"][aria-pressed="true"]{background:var(--good);border-color:var(--good)}
.levels button[data-l="close"][aria-pressed="true"]{background:var(--close);border-color:var(--close)}
.levels button[data-l="bad"][aria-pressed="true"]{background:var(--bad);border-color:var(--bad)}
.reasons{display:flex;flex-direction:column;gap:4px;font-size:13px}
.reasons label{display:flex;gap:6px;align-items:center}
textarea{font:inherit;font-size:13px;width:100%;box-sizing:border-box;min-height:38px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);padding:6px}
.saved{font-size:12px;color:var(--mut);min-height:1em}
details{font-size:12px;color:var(--mut)}
#zoom{position:fixed;inset:0;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;z-index:20;padding:16px}
#zoom img{max-width:100%;max-height:100%}
.note{color:var(--mut);font-size:13px;max-width:70ch}
</style>
<header>
  <h1>ახალი სამყაროს შეფასება</h1>
  <div class="tabs" id="tabs"></div>
  <div class="filters"><button id="only" aria-pressed="false">მხოლოდ შეუფასებელი</button></div>
  <span id="count"></span>
</header>
<p class="note">აირჩიე დონე. „ჰგავს, მაგრამ პრობლემებია“ ან „ცუდია“ არჩევისას მონიშნე მიზეზი ან ჩაწერე შენი. შენახვა ავტომატურია. ქვეშ ჩანს ჩემი ავტომატური შემოწმება და ჩემი შენიშვნა.</p>
<div class="grid" id="grid"></div>
<div id="zoom" hidden><img alt=""></div>
<script>
const ROWS=@DATA@, LEVELS=@LEVELS@, REASONS=@REASONS@, KINDS=@KINDS@;
let kind="person", onlyOpen=false, ratings={}, db=null;
const $=s=>document.querySelector(s);
function tabs(){const t=$("#tabs");t.textContent="";for(const[k,v]of Object.entries(KINDS)){const b=document.createElement("button");b.textContent=v+" ("+ROWS.filter(r=>r.kind===k).length+")";b.setAttribute("aria-pressed",k===kind);b.onclick=()=>{kind=k;tabs();render()};t.append(b)}}
function count(){const n=ROWS.filter(r=>ratings[r.name]&&ratings[r.name].level).length;$("#count").textContent=`შეფასებულია ${n} / ${ROWS.length}`+(db?"":" · შენახვა მიუწვდომელია")}
async function save(name,patch){ratings[name]={...(ratings[name]||{}),...patch,at:new Date().toISOString()};count();const el=document.getElementById("s-"+name);if(!db){if(el)el.textContent="ვერ შეინახა: ბაზა მიუწვდომელია";return}
  try{await db.doc("ratings/"+name).set(ratings[name]);if(el)el.textContent="შენახულია"}catch(e){if(el)el.textContent="ვერ შეინახა"}}
function card(r){const c=document.createElement("div");c.className="card";const R=ratings[r.name]||{};
  const img=document.createElement("img");img.loading="lazy";img.src="img/"+r.name+".jpg";img.alt=r.desc||r.name;img.onclick=()=>{$("#zoom img").src=img.src;$("#zoom").hidden=false};c.append(img);
  const b=document.createElement("div");b.className="body";c.append(b);
  const m=document.createElement("div");m.className="meta";const a=document.createElement("span");a.textContent=r.name;const ch=document.createElement("span");ch.className="check "+r.check;ch.textContent="შემოწმება: "+r.check+(r.why.length?" · "+r.why.join(", "):"");m.append(a,ch);b.append(m);
  if(r.look){const l=document.createElement("div");l.className="look";l.textContent="ჩემი შენიშვნა: "+r.look;b.append(l)}
  if(r.desc){const d=document.createElement("details");const s=document.createElement("summary");s.textContent="აღწერა";d.append(s,document.createTextNode(r.desc));b.append(d)}
  const lv=document.createElement("div");lv.className="levels";for(const[k,v]of LEVELS){const x=document.createElement("button");x.dataset.l=k;x.textContent=v;x.setAttribute("aria-pressed",R.level===k);x.onclick=()=>{save(r.name,{level:k});lv.querySelectorAll("button").forEach(y=>y.setAttribute("aria-pressed",y.dataset.l===k))};lv.append(x)}b.append(lv);
  const rs=document.createElement("div");rs.className="reasons";for(const[k,v]of REASONS){const lab=document.createElement("label");const cb=document.createElement("input");cb.type="checkbox";cb.checked=(R.reasons||[]).includes(k);cb.onchange=()=>{const cur=new Set((ratings[r.name]||{}).reasons||[]);cb.checked?cur.add(k):cur.delete(k);save(r.name,{reasons:[...cur]})};lab.append(cb,document.createTextNode(v));rs.append(lab)}b.append(rs);
  const ta=document.createElement("textarea");ta.placeholder="შენი მიზეზი…";ta.value=R.note||"";let t;ta.oninput=()=>{clearTimeout(t);t=setTimeout(()=>save(r.name,{note:ta.value}),700)};b.append(ta);
  const sv=document.createElement("div");sv.className="saved";sv.id="s-"+r.name;b.append(sv);return c}
function render(){const g=$("#grid");g.textContent="";for(const r of ROWS){if(r.kind!==kind)continue;if(onlyOpen&&ratings[r.name]&&ratings[r.name].level)continue;g.append(card(r))}count()}
$("#only").onclick=e=>{onlyOpen=!onlyOpen;e.target.setAttribute("aria-pressed",onlyOpen);render()};
$("#zoom").onclick=()=>{$("#zoom").hidden=true};
tabs();render();
(async()=>{try{db=await window.claude?.use?.("db")}catch(e){db=null}
  if(!db){count();return}
  try{const snap=await db.collection("ratings").get();for(const d of (snap.docs||snap)){const id=d.id;const v=typeof d.data==="function"?d.data():d.data;if(id&&v)ratings[id]=v}}catch(e){}
  render()})();
</script>
"""


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.training.cast.rate_page")
    ap.add_argument("world"); ap.add_argument("out"); ap.add_argument("--looks")
    a = ap.parse_args(argv)
    from explainer_engine.training.cast.sheet import items
    descs = {i: v["desc"] for i, v in items().items()}
    looks = json.loads(Path(a.looks).read_text(encoding="utf-8")) if a.looks else None
    rows = build(a.world, a.out, looks, descs)
    print(len(rows), "pictures ->", Path(a.out) / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
