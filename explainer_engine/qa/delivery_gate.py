"""Delivery gate (P3): fail closed on a produced film."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from explainer_engine.core.camera_vocab import ALLOWED_CAMERA_MOVES


def check(episode_log_path, clips_dir=None):
    """Return PASS/FAIL verdict for an episode log and its per-render receipts."""
    log_path = Path(episode_log_path)
    problems = []
    shots_status = {}
    try:
        log = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "problems": [f"cannot read episode log {log_path}: {exc}"], "shots": {}}
    if not isinstance(log, dict):
        return {"status": "FAIL", "problems": [f"episode log is not a JSON object: {log_path}"], "shots": {}}
    if "paid_calls" not in log:
        problems.append("episode log missing paid_calls")
    elif log["paid_calls"] != 0:
        problems.append(f"paid calls need a cost card (paid_calls={log['paid_calls']!r})")
    shots = log.get("shots")
    if not isinstance(shots, list) or not shots:
        problems.append("episode log has no shots")
        shots = []
    if clips_dir is None:
        name = log_path.name
        stem_before = name.split(".episode_log", 1)[0] if ".episode_log" in name else log_path.stem
        clips_dir = log_path.parent / (stem_before + "_work") / "clips"
    clips_dir = Path(clips_dir)
    for sh in shots:
        if not isinstance(sh, dict) or "id" not in sh:
            problems.append("a shot entry is missing its id")
            continue
        sid = sh["id"]
        shot_ok = True
        if "clip" not in sh:
            problems.append(f"{sid}: shot has no clip filename")
            shots_status[sid] = "FAIL"
            continue
        clip_name = sh["clip"]
        clip_path = Path(clip_name) if Path(clip_name).is_absolute() else clips_dir / clip_name
        if not clip_path.exists():
            problems.append(f"{sid}: clip file missing: {clip_path}")
            shot_ok = False
        receipt_path = clip_path.with_suffix(".render_log.json")
        if not receipt_path.exists():
            problems.append(f"{sid}: missing receipt {receipt_path}")
            shots_status[sid] = "FAIL"
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{sid}: cannot read receipt {receipt_path}: {exc}")
            shots_status[sid] = "FAIL"
            continue
        if not isinstance(receipt, dict):
            problems.append(f"{sid}: receipt is not a JSON object")
            shots_status[sid] = "FAIL"
            continue
        kind = receipt.get("kind")
        if kind == "photo":
            cam = receipt.get("camera")
            if not isinstance(cam, dict) or cam.get("move") not in ALLOWED_CAMERA_MOVES:
                problems.append(f"{sid}: photo camera.move must be one of {sorted(ALLOWED_CAMERA_MOVES)}")
                shot_ok = False
            if not receipt.get("film_id"):
                problems.append(f"{sid}: photo receipt missing film_id")
                shot_ok = False
            if not receipt.get("font"):
                problems.append(f"{sid}: photo receipt missing font")
                shot_ok = False
            depth = receipt.get("depth")
            if not isinstance(depth, dict) or not depth:
                problems.append(f"{sid}: photo receipt missing depth")
                shot_ok = False
            plume_checks = receipt.get("plume_checks")
            if not isinstance(plume_checks, list):
                problems.append(f"{sid}: photo receipt missing plume_checks")
                shot_ok = False
            else:
                for i, item in enumerate(plume_checks):
                    if not isinstance(item, dict) or item.get("status") != "PASS":
                        problems.append(f"{sid}: plume_checks[{i}] status is not PASS")
                        shot_ok = False
        elif kind == "map":
            if not receipt.get("render"):
                problems.append(f"{sid}: map receipt missing render")
                shot_ok = False
            cam = receipt.get("camera")
            if not isinstance(cam, dict) or cam.get("move") not in ALLOWED_CAMERA_MOVES:
                problems.append(f"{sid}: map camera.move must be one of {sorted(ALLOWED_CAMERA_MOVES)}")
                shot_ok = False
            if not receipt.get("film_id"):
                problems.append(f"{sid}: map receipt missing film_id")
                shot_ok = False
            if not receipt.get("font"):
                problems.append(f"{sid}: map receipt missing font")
                shot_ok = False
        else:
            problems.append(f"{sid}: receipt kind must be 'photo' or 'map', got {kind!r}")
            shot_ok = False
        shots_status[sid] = "PASS" if shot_ok else "FAIL"
    return {"status": "PASS" if not problems else "FAIL", "problems": problems, "shots": shots_status}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.qa.delivery_gate")
    ap.add_argument("episode_log")
    a = ap.parse_args(argv)
    verdict = check(a.episode_log)
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
