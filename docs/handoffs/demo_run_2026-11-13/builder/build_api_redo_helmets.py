"""S3b redos, round 3 (FL-026 steel helmets, GC-25): the original prompt plus ONE correction sentence after the tail, the same references.
Usage: python build_api_redo.py <repo root> <out message.md>
"""
import json
import sys
from pathlib import Path

repo, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo))
from explainer_engine.gemini_task import ep as EP  # noqa: E402
from explainer_engine.gemini_task import prompts as PR  # noqa: E402

GT = repo / "episodes/ep_truce_1914/planning/gemini_task"
man, _ = EP.load(repo / "episodes/ep_truce_1914")
lk = EP.look(man)
era = EP.era_line(man, lk)
REDO = {"S03_SH003_start": "Every Saxon soldier wears a field-grey round Feldmuetze cap with a red band.",
        "S05_SH018_start": "Only frozen earth and frost lie on the grave.",
        "S05_SH019_start": "Only frozen earth and frost lie on the grave."}
waves = json.loads((GT / "messages/API_S3_scenes_waves.json").read_text(encoding="utf-8"))
sent = {}
for f in sorted((GT / "messages").glob("API_S3_scenes_w2_p*.md")):
    from explainer_engine.gemini_task import api_backup as AB
    for b in AB.picture_blocks(f.read_text(encoding="utf-8")):
        sent[b["id"]] = b
blocks = []
for k, (pid, corr) in enumerate(REDO.items(), 1):
    b = sent[pid]
    prompt = b["prompt"] + " " + corr
    rows = PR.check(prompt, lk, era, "scene", correction=corr)
    if PR.fails(rows):
        sys.exit(f"{pid}: {PR.fails(rows)}")
    q = json.loads((GT / "shot_queue.json").read_text(encoding="utf-8"))
    roles = {r["file"].split("/")[-1]: r["role"] for p in q["pictures"] if p["id"] == pid for r in p["references"]}
    blocks.append(PR.block(k, len(REDO), pid + "_r2", pid + "_r2.jpg", [(r, roles.get(r, "ref")) for r in b["refs"]],
                           prompt, replaces=pid))
out.write_text("# ep_truce_1914 S3b redos (FL-026)\n\n-----BEGIN PICTURES-----\n" + "\n\n".join(blocks) +
               "\n-----END PICTURES-----\n", encoding="utf-8")
print(out)
