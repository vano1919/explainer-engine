"""Run the seven-point scorecard on the Day 1 v5 build. python qa_run.py <pictures dir> <out dir>"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from explainer_engine.qa import scorecard as S  # noqa: E402

HERE = Path(__file__).parent
pics, out = Path(sys.argv[1]), Path(sys.argv[2])
shots = json.loads((HERE / "shots.json").read_text())["shots"]
words = json.loads((HERE / "words.json").read_text())["words"]
text = (HERE / "narration.txt").read_text()
look = json.loads((HERE.parent / "look.json").read_text())
HEROES = ["franklin", "newton", "nansen", "einstein", "darwin", "wallace", "snow", "curie", "tesla"]
POSES = ["dismay", "shock", "think", "amazed", "argue", "point", "smug", "scheme", "struggle", "triumph", "plead", "recoil", "lecture", "exhausted"]
look = dict(look, caricatures=HEROES, pose_bank={h: POSES for h in HEROES})  # D-41: heroes are drawn from cards, not sprites
stats = {}
for s in shots:
    im = Image.open(pics / f"{s['picture']}.png").convert("RGB")
    im.thumbnail((480, 270))
    stats[s["picture"]] = S.picture_stats(np.asarray(im) / 255.0)
judge = json.loads((pics / "judge_full.json").read_text())
prompts = {p["id"]: p for p in json.loads((HERE / "prompts.json").read_text())}
for pid, verdict in judge.items():  # verdicts written before the rules settled: one_light is advisory, too_early only counts before the fire
    keep = [f for f in verdict["fails"] if not f.startswith("one_light") and not (f.startswith("too_early: expected") and not prompts[pid]["not_yet"])]
    verdict["fails"] = keep
    verdict["status"] = "FAIL" if keep else ("REVIEW" if verdict["review"] else "PASS")
astats = json.loads((out / "audio_stats.json").read_text())
rows = S.score(shots, words, text, look, pic_stats=stats, judge=judge, audio=astats, sound_events=astats["events"])
(out / "scorecard.md").write_text(S.markdown(rows))
(out / "scorecard.json").write_text(json.dumps(rows, indent=1))
print(S.markdown(rows))
