"""Attach the visual beats of beats/*.json (keyed by the exact line text) to production_script.json after a build.

    python make_script_builder.py make_script_content.py production_script.json && python apply_beats.py
Lines whose text has no beats are listed: the beat-writer writes them (stage 2b) before validate.
"""
import json
import glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / "production_script.json"
doc = json.loads(path.read_text(encoding="utf-8"))
beats: dict = {}
for f in sorted(glob.glob(str(HERE / "beats" / "*.json"))):
    beats.update(json.loads(Path(f).read_text(encoding="utf-8"))["lines"])
missing = []
for seg in doc["segments"]:
    for i, ln in enumerate(seg["lines"]):
        if ln["text"] in beats:
            ln["visual_beats"] = beats[ln["text"]]
        else:
            missing.append(f"{seg['id']} line {i + 1}: {ln['text']}")
path.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"beats on {sum(1 for s in doc['segments'] for l in s['lines'] if l.get('visual_beats'))} lines; {len(missing)} without")
for m in missing:
    print("  ", m)
