"""S3 R2 (DV-003, SF-005): the API-backup message of ep_truce_1914 for the three full-body references.

The queue's R2 prompts word for word, except SF-005 (creator, card cmsg_01Hnu5zB86sjUj5GtTgaUkPWSCj4Rso8shs2yad4KB6UsB answer A,
2026-11-13 17:11 UTC): the backdrop phrase is replaced so no lantern is drawn behind the hero (FL-021). Checked by
`gemini_task.prompts.check`; any FAIL stops. Usage: python build_api_r2_message.py <repo root>
"""
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo))
from explainer_engine.gemini_task import ep as EP  # noqa: E402
from explainer_engine.gemini_task import prompts as PR  # noqa: E402

OLD = "a quiet softly blurred backdrop of the same world"
NEW = "a plain softly blurred backdrop of frosty sandbags and a dim winter sky"
ROOT = repo / "episodes" / "ep_truce_1914"
GT = ROOT / "planning" / "gemini_task"
man, _ = EP.load(ROOT)
lk = EP.look(man)
era = EP.era_line(man, lk)
q = json.loads((GT / "shot_queue.json").read_text(encoding="utf-8"))
items = []
for r in q["references"]:
    if r["round"] != "R2":
        continue
    assert r["prompt"].count(OLD) == 1, r["id"]
    p = r["prompt"].replace(OLD, NEW)
    rows = PR.check(p, lk, era, r["kind"])
    if PR.fails(rows):
        sys.exit(f"{r['id']}: {rows}")
    items.append((r["id"], r["target"], [(x["file"].split("/")[-1], x["role"]) for x in r["references"]], p))
blocks = "\n\n".join(PR.block(k, len(items), i, t, refs, p) for k, (i, t, refs, p) in enumerate(items, 1))
out = GT / "messages" / "API_S3_R2.md"
out.write_text("# ep_truce_1914 S3 API message: R2 full bodies (DV-003, SF-005)\n\n-----BEGIN PICTURES-----\n" + blocks +
               "\n-----END PICTURES-----\n", encoding="utf-8")
print(json.dumps({"message": str(out), "ids": [i[0] for i in items]}))
