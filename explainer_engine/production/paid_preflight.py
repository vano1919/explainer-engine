"""Free rule check of a paid jobs file, run on the local side of every Modal launcher BEFORE ``.remote()`` (the creator, 2026-11-07
22:23 UTC: the Gemini review found that the c3 LTX prompt broke KP-04, KP-22 and KP-55 and the minute-1 cut broke DL-04, and no code
had run those checks before money was spent). A FAIL stops the launcher; nothing is started.

- LTX jobs (``ltx_jobs.py`` shape: ``{"names": [...], "jobs": [{"id", "prompt", "frames", "fps", "held_props"?, "camera_end"?,
  "prop_change"?, "exit"?}]}``) -> ``scripting/shot_prompt_lint`` as route J2 video shots (KP-04, KP-11, KP-22, KP-55, KP-59..KP-62).
  A jobs file without ``names`` (the story names of the heroes) fails: KP-22 cannot be checked.
- Qwen jobs (``qwen_jobs.py`` shape) -> ``production/scene_reuse.check_all`` (RF-01, RF-04, RF-05, HI-01, HI-04, HI-08, ...).

    python -m explainer_engine.production.paid_preflight ltx|qwen <jobs.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.production import scene_reuse
from explainer_engine.scripting import shot_prompt_lint


def ltx_shots(doc: dict) -> list[dict]:
    shots = []
    for j in doc["jobs"]:
        fps = float(j.get("fps", 24) or 24)
        shots.append({"id": j["id"], "kind": "video", "route": "J2", "ltx": True, "prompt": j["prompt"],
                      "seconds": float(j.get("frames", 0)) / fps, "neg": j.get("negative_prompt", ""),
                      **{k: j[k] for k in ("held_props", "camera_end", "prop_change", "exit", "mode", "people") if k in j}})
    return shots


def ltx(doc: dict) -> list[str]:
    if not doc.get("names"):
        return ["FAIL KP-22 jobs file: no 'names' list (the heroes' story names), so story names in prompts cannot be found"]
    found = shot_prompt_lint.check(ltx_shots(doc), names=doc["names"])
    return [f"{f['severity']} {f['rule']} {f['where']}: {f['detail']}" for f in found if f["severity"] == "FAIL"]


def qwen(doc: dict) -> list[str]:
    return [f"{sev} {rule} {text}" for rule, sev, text in scene_reuse.check_all(doc) if sev == "FAIL"]


def refuse(kind: str, path) -> None:
    """Raise SystemExit with every FAIL of the jobs file at ``path``; return quietly when it passes."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = (ltx if kind == "ltx" else qwen)(doc)
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


def main(argv: list[str]) -> int:
    kind, path = argv
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = (ltx if kind == "ltx" else qwen)(doc)
    print("\n".join(bad) or "pass")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
