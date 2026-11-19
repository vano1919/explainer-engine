"""S3b (DV-003, SF-009, FL-022): the API-backup messages of ep_truce_1914's scene start frames, in dependency waves.

From the queue's own prompts (rebuilt by `python -m explainer_engine.gemini_task queue` after SF-006..008), plus:
- SF-009: one costume sentence after the prompt's people for the shots after the button exchange (the queue ignores the
  heroes' costume_continuity_notes, FL-015);
- FL-022: a picture never attaches itself;
- waves: a picture that attaches another scene picture goes in a later wave than that picture.
Every prompt goes through `gemini_task.prompts.check`; any FAIL stops. Usage:
    python build_api_scene_waves.py <repo root>            -> messages/API_S3_scenes_wave<N>.md + waves.json
"""
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo))
from explainer_engine.gemini_task import ep as EP  # noqa: E402
from explainer_engine.gemini_task import prompts as PR  # noqa: E402

ROOT = repo / "episodes" / "ep_truce_1914"
GT = ROOT / "planning" / "gemini_task"
man, _ = EP.load(ROOT)
lk = EP.look(man)
era = EP.era_line(man, lk)
q = json.loads((GT / "shot_queue.json").read_text(encoding="utf-8"))
script = json.loads((ROOT / "story" / "production_script.json").read_text(encoding="utf-8"))
reg = {c["id"] if "id" in c else c["character_id"]: c for c in script["world_bible"]["characters"]}


def order(sid):
    return int(sid[1:3]), int(sid.split("SH")[1][:3])


BUTTONS = [("char_thomas_hale", (6, 10), "Thomas's tunic has its top right brass button cut off."),
           ("char_friedrich_brandt", (6, 12), "Friedrich's greatcoat has one button missing.")]
P = {p["id"]: p for p in q["pictures"]}
items, sf009 = {}, {}
for pid, p in P.items():
    prompt = p["prompt"]
    adds = [s for cid, frm, s in BUTTONS if cid in p["people"] and order(p["shot_id"]) >= frm]
    if adds:
        tail = era
        assert prompt.count(tail) == 1, pid
        prompt = prompt.replace(tail, " ".join(adds) + " " + tail)
        sf009[pid] = adds
    refs = [(r["file"].split("/")[-1], r["role"]) for r in p["references"] if r["file"][:-4] != pid]
    people = [reg[c]["fixed_appearance_prompt"] for c in p["people"] if c in reg]
    rows = PR.check(prompt, lk, era, "scene", people_texts=people)
    if PR.fails(rows):
        sys.exit(f"{pid}: {PR.fails(rows)}")
    items[pid] = {"target": p["target"], "refs": refs, "prompt": prompt, "review": [r for r in rows if r not in PR.fails(rows)]}
wave = {}


def w(k):
    if k not in wave:
        wave[k] = 1 + max([w(f[:-4]) for f, _ in items[k]["refs"] if f[:-4] in items] or [0])
    return wave[k]


for k in items:
    w(k)
LIMIT = 15_000_000   # imagegen/gemini.BATCH_MAX_BYTES is 18 MB inline (base64); keep a margin


def ref_bytes(name):
    hits = sorted(GT.rglob(name)) or sorted((repo / "assets" / "style").rglob(name))
    return hits[0].stat().st_size if hits else 1_600_000   # a scene picture of an earlier wave, not made yet


out = {"era_line": era, "sf009": sf009, "waves": {}}
for n in sorted(set(wave.values())):
    ids = [k for k in P if wave[k] == n]
    parts, cur, size = [], [], 0
    for k in ids:
        b = sum(ref_bytes(f) for f, _ in items[k]["refs"]) * 4 // 3 + len(items[k]["prompt"])
        if cur and size + b > LIMIT:
            parts.append(cur); cur, size = [], 0
        cur.append(k); size += b
    if cur:
        parts.append(cur)
    out["waves"][n] = []
    for m, part in enumerate(parts, 1):
        blocks = "\n\n".join(PR.block(i, len(part), k, items[k]["target"], items[k]["refs"], items[k]["prompt"])
                             for i, k in enumerate(part, 1))
        f = GT / "messages" / f"API_S3_scenes_w{n}_p{m:02d}.md"
        f.write_text(f"# ep_truce_1914 S3b API message: scene start frames, wave {n} part {m} (DV-003, SF-009, FL-022)\n\n"
                     "-----BEGIN PICTURES-----\n" + blocks + "\n-----END PICTURES-----\n", encoding="utf-8")
        out["waves"][n].append({"message": str(f.relative_to(repo)), "ids": part})
(GT / "messages" / "API_S3_scenes_waves.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({n: [len(x["ids"]) for x in v] for n, v in out["waves"].items()}), "sf009:", len(sf009),
      "review rows:", sum(len(v["review"]) for v in items.values()))
