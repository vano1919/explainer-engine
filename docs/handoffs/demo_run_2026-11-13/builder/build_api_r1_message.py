"""S3 (DV-003, RC-002, RC-003): the API-backup message of ep_truce_1914 for the six new 1914 style anchors plus R1.

The Task package's `batch` refuses before T0 and the GC-26 review (both waived by the creator for this run, card
cmsg_01Hnu5zB86sjUj5GtTgaUkPWKfyQxUuUGhDtLX72PBMkfB answer A). This script writes the same picture blocks the package
would write, with the package's own functions: the anchors are assembled by `gemini_task.prompts.assemble` (kind
"anchor") from the subjects of `planning/gemini_task/anchors_1914_draft.md`; the R1 prompts are the queue's, word for word.
Every prompt goes through `prompts.check`; any FAIL stops. No repo code is changed.

Usage: python build_api_r1_message.py <repo root> [--out <message.md>]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("repo", type=Path)
ap.add_argument("--out", type=Path)
a = ap.parse_args()
sys.path.insert(0, str(a.repo))
from explainer_engine.gemini_task import ep as EP  # noqa: E402
from explainer_engine.gemini_task import prompts as PR  # noqa: E402

ROOT = a.repo / "episodes" / "ep_truce_1914"
GT = ROOT / "planning" / "gemini_task"
man, _ = EP.load(ROOT)
lk = EP.look(man)
era = EP.era_line(man, lk)
STYLE = ("main_style_5709.png", "style")

rows = re.findall(r"^\| ([A-F]) \| [^|]+ \| (.+?) \|$", (GT / "anchors_1914_draft.md").read_text(encoding="utf-8"), re.M)
PEOPLE = {"A": True, "B": True, "C": True, "D": False, "E": True, "F": True}
items = []
for t, subject in rows:
    prompt = PR.assemble(lk, era, "anchor", subject.strip(), people=PEOPLE[t])
    items.append({"id": f"anchor1914_{t}", "target": f"anchors/style_{t}.jpg", "refs": [STYLE], "prompt": prompt,
                  "checks": PR.check(prompt, lk, era, "anchor", subject=subject.strip())})
q = json.loads((GT / "shot_queue.json").read_text(encoding="utf-8"))
for r in q["references"]:
    if r["round"] != "R1":
        continue
    refs = [(x["file"], x["role"]) for x in r["references"]]
    people = r.get("people") or []
    reg_texts = []
    items.append({"id": r["id"], "target": r["target"], "refs": refs, "prompt": r["prompt"],
                  "checks": PR.check(r["prompt"], lk, era, r["kind"], subject="")})
bad = [(i["id"], c) for i in items for c in i["checks"] if c["severity"] == "FAIL"]
rev = [(i["id"], c) for i in items for c in i["checks"] if c["severity"] != "FAIL"]
if bad:
    print(json.dumps(bad, indent=1))
    sys.exit("prompt rule FAIL")
blocks = "\n\n".join(PR.block(k, len(items), i["id"], i["target"], i["refs"], i["prompt"])
                     for k, i in enumerate(items, 1))
text = ("# ep_truce_1914 S3 API message: 1914 style anchors A-F + R1 (DV-003, RC-002, RC-003)\n\n"
        "Built by build_api_r1_message.py; sent only through gemini_task.api_backup.\n\n"
        "-----BEGIN PICTURES-----\n" + blocks + "\n-----END PICTURES-----\n")
out = a.out or (GT / "messages" / "API_S3_anchors_R1.md")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(text, encoding="utf-8")
print(json.dumps({"message": str(out), "pictures": len(items), "ids": [i["id"] for i in items], "review": rev}, indent=1))
