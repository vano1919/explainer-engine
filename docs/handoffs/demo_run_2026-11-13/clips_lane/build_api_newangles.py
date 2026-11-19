"""New camera positions for five start pictures of script A (clips lane, coordinator note 19:37 UTC, picture preflight rule).
The original prompt of each (S03_SH003: the helmet redo r2), its camera sentence replaced by the script's own composition
(screen_composition / camera_spec), image 2 (the previous shot, the source of the repeated framing) dropped, ONE correction
sentence after the tail: nothing else changes.  Usage: python build_api_newangles.py <repo root> <out message.md>
"""
import glob
import json
import sys
from pathlib import Path

repo, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo))
from explainer_engine.gemini_task import api_backup as AB  # noqa: E402
from explainer_engine.gemini_task import ep as EP  # noqa: E402
from explainer_engine.gemini_task import prompts as PR  # noqa: E402

GT = repo / "episodes/ep_truce_1914/planning/gemini_task"
man, _ = EP.load(repo / "episodes/ep_truce_1914")
lk = EP.look(man)
era = EP.era_line(man, lk)
CORR = ("This picture shows a new camera position, different from every other picture of the film, with only the soldiers, "
        "wool and leather clothing, timber, sandbags, frost and wire of the shot's own place, and from image 1 only its painting style.")
# id of the sent block -> (new id, old camera sentence start, new camera sentence(s))
NEW = {
    "S03_SH003_start_r2": ("S03_SH003_start_n1", "A medium wide shot. Friedrich and five Saxon soldiers stand in the trench by the candle tree.",
        "A medium shot, closer than a wide view of the trench. Friedrich stands in the centre of the frame, seen from the chest up, "
        "singing, looking a little to the left of the camera, with two Saxon soldiers singing at his shoulders and the candle tree small and soft on the parapet behind them."),
    "S04_SH010_start": ("S04_SH010_start_n1", "A medium shot. Thomas stands facing Friedrich.",
        "A medium over-the-shoulder shot from behind Friedrich: his grey shoulder, greatcoat collar and the back of his round cap fill the right edge of the frame, out of focus. "
        "Thomas stands facing him at the centre-left, seen from the chest up, his face turned three quarters toward the camera in a nervous grin."),
    "S04_SH012_start": ("S04_SH012_start_n1", "A medium shot. Friedrich faces Thomas.",
        "A medium over-the-shoulder shot from behind Thomas: his khaki shoulder, greatcoat collar and the back of his cap fill the left edge of the frame, out of focus. "
        "Friedrich faces him at the centre-right, seen from the chest up, smiling, his face turned three quarters toward the camera, his hand held out toward Thomas."),
    "S04_SH014_start": ("S04_SH014_start_n1", "A medium wide shot. Thomas and Friedrich face each other two paces apart.",
        "A wide shot from a distance, side-on: Thomas on the left and Friedrich on the right, two small full-length figures in the middle of the empty frozen field, clasping hands, with frost in the foreground and wire stakes and fog behind them."),
    "S05_SH009_start": ("S05_SH009_start_n1", "A medium shot. Friedrich takes the portrait card from his breast pocket.",
        "A medium over-the-shoulder shot from behind Thomas: his khaki shoulder, greatcoat collar and the back of his cap fill the left edge of the frame, out of focus. "
        "Friedrich stands at the centre-right, seen from the chest up, taking the small portrait card from his breast pocket and holding it out toward Thomas."),
}
sent = {}
for f in sorted(glob.glob(str(GT / "messages/API_S3_*.md"))):
    try:
        for b in AB.picture_blocks(Path(f).read_text(encoding="utf-8")):
            sent[b["id"]] = b
    except Exception:
        pass
q = json.loads((GT / "shot_queue.json").read_text(encoding="utf-8"))
blocks = []
for k, (pid, (nid, old, new)) in enumerate(NEW.items(), 1):
    b = sent[pid]
    assert b["prompt"].count(old) == 1, pid
    prompt = b["prompt"].replace(old, new) + " " + CORR
    rows = PR.check(prompt, lk, era, "scene", correction=CORR)
    if PR.fails(rows):
        sys.exit(f"{pid}: {PR.fails(rows)}")
    if rows:
        print(pid, "rows:", rows)
    base = pid.replace("_r2", "")
    roles = {r["file"].split("/")[-1]: r["role"] for p in q["pictures"] if p["id"] == base for r in p["references"]}
    refs = [r for r in b["refs"] if not (r.startswith("S0") and r.endswith("_start.jpg"))]   # image 2 (previous shot) dropped
    blocks.append(PR.block(k, len(NEW), nid, nid + ".jpg", [(r, roles.get(r, "ref")) for r in refs], prompt, replaces=base))
out.write_text("# ep_truce_1914 new camera positions (clips lane)\n\n-----BEGIN PICTURES-----\n" + "\n\n".join(blocks) +
               "\n-----END PICTURES-----\n", encoding="utf-8")
print(out)
