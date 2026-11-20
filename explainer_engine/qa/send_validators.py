"""Validators the send gate runs on a candidate before the owner sees it (``governance/send_gate``, spec section 4). Each one is named by a
registry entry of ``owner_requirements.json`` (``check.ref`` = ``module:function``) and has a test on a compliant and on a violating
fixture. Contract: ``fn(path) -> {"status": PASS | FAIL | NOT_RUN, "value": number | None, "detail": str}``; ``fn.kinds`` lists the file
suffixes it applies to. Numpy and ffmpeg only (no OpenCV), so it also runs in the cloud container.

``living_motion`` (R-LIVING, the owner 2026-11-20 08:33 UTC and 2026-11-14: "only the fire moves" is not alive): on a clip with a still camera
the world must move, not only the flame. Measured on the delivered frames (480x270 grey, 8 frames a second):
- the camera is still: the phase-correlation shift between the two ends of every one-second window stays under ``STILL_SHIFT_PX`` of 480
  (else NOT_RUN: with a moving camera the pixel change is the camera, the rule is about a still one; BP-194 says a camera move alone does not count);
- G-LIVE-1 (BP-194, ``standards/sourced_rules.json``; the 1 px and 25 % are BP-194 thresholds too): no one-second window changes less than ``frozen_change_pct`` of the frame (a pixel counts above
  12 grey levels) - ``value`` is the deadest window's share in %;
- G-LIVE-3 (LIVING_PHOTO_RULES_2026-11-14): when ``<clip>.zones.json`` names the zones of the effects (``{"zones": [{"name": "smoke", "mask": "smoke.png"}]}``,
  mask paths relative to the json, white = zone) at least ``ZONE_MIN_PCT`` % of every zone's pixels change in the median window; without the file the zone
  part is reported as not measured in ``detail`` (the whole-frame number still decides).
The numbers are BP-194's engineering defaults and the rules document's proposals until the owner confirms them (D-59)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

from explainer_engine.qa import liveliness as LV
from explainer_engine.standards import sourced_rules as SR

PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"
SIZE = LV.FROZEN_SIZE                 # (480, 270)
ANALYSIS_FPS = 8
STILL_SHIFT_PX = float(SR.T("BP-194", "still_shift_px"))   # of 480: a camera that moves more than this in a second is not still
ZONE_MIN_PCT = float(SR.T("BP-194", "zone_min_pct"))        # G-LIVE-3: a quarter of the zone's pixels change


def decode_grey(path: Path, fps: int = ANALYSIS_FPS) -> list[np.ndarray]:
    """The clip's frames as float32 grey 480x270 arrays at ``fps`` frames a second (ffmpeg through a pipe)."""
    w, h = SIZE
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg could not decode the file: " + r.stderr.decode("utf-8", "replace")[-200:])
    n = len(r.stdout) // (w * h)
    return list(np.frombuffer(r.stdout[: n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float32))


def phase_shift(a: np.ndarray, b: np.ndarray) -> float:
    """The translation between two grey frames in pixels (phase correlation; the length of the shift vector)."""
    fa, fb = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    cross = fa * np.conj(fb)
    cross /= np.maximum(np.abs(cross), 1e-9)
    corr = np.fft.ifft2(cross).real
    iy, ix = np.unravel_index(int(np.argmax(corr)), corr.shape)
    h, w = corr.shape
    dy, dx = (iy - h if iy > h // 2 else iy), (ix - w if ix > w // 2 else ix)
    return float(np.hypot(dx, dy))


def _zones(path: Path) -> list[tuple[str, np.ndarray]]:
    side = path.with_suffix(".zones.json")
    if not side.is_file():
        return []
    from PIL import Image
    out = []
    for z in json.loads(side.read_text(encoding="utf-8")).get("zones", []):
        m = Image.open(side.parent / z["mask"]).convert("L").resize(SIZE)
        out.append((z["name"], np.asarray(m) > 127))
    return out


def living_motion(path) -> dict:
    path = Path(path)
    g = decode_grey(path)
    step = max(1, int(round(ANALYSIS_FPS * LV.FROZEN_WINDOW_S)))
    if len(g) <= step:
        return {"status": NOT_RUN, "value": None, "detail": f"too short for a one-second window ({len(g)} frames at {ANALYSIS_FPS} fps)"}
    shift = max(phase_shift(g[i], g[i + step]) for i in range(0, len(g) - step, max(1, step // 2)))
    if shift > STILL_SHIFT_PX:
        return {"status": NOT_RUN, "value": round(shift, 2), "detail": f"the camera moves (up to {shift:.1f} px of 480 in one second): the "
                f"still-camera rule does not apply; the owner's eye judges this clip"}
    fw = LV.frozen_windows_grey(g, ANALYSIS_FPS)
    low = fw["min_share_pct"]
    if fw["frozen"]:
        return {"status": FAIL, "value": low, "detail": f"{fw['frozen']} of {fw['windows']} one-second windows change under {LV.FROZEN_CHANGE:g} % of the "
                f"frame with a still camera (deadest {low:.2f} % from {fw['frozen_from_s'][0]:.1f} s): only a small part moves (G-LIVE-1, BP-194)"}
    zones, notes = _zones(path), []
    for name, mask in zones:
        shares = [float((np.abs(g[i + step] - g[i])[mask] > LV.FROZEN_PIXEL).mean() * 100) for i in range(0, len(g) - step, max(1, step // 2))]
        med = float(np.median(shares))
        if med < ZONE_MIN_PCT:
            return {"status": FAIL, "value": round(med, 2), "detail": f"the {name} zone changes {med:.1f} % of its pixels in the median second "
                    f"(under {ZONE_MIN_PCT:g} %): the effect barely moves (G-LIVE-3)"}
        notes.append(f"{name} {med:.1f} %")
    zone_text = ("zones " + ", ".join(notes)) if zones else "zones not measured (no .zones.json beside the clip)"
    return {"status": PASS, "value": low, "detail": f"deadest second changes {low:.2f} % of the frame (floor {LV.FROZEN_CHANGE:g} %), camera still "
            f"({shift:.2f} px); {zone_text}"}


living_motion.kinds = (".mp4", ".mov", ".webm", ".mkv")


_OPERATOR_MODE = re.compile(r"^(?:MODE:\s*(\w+)|chat mode\s*\**\s*(\w+))", re.I)


def operator_mode(text: str) -> str | None:
    """The mode the OPERATOR (the person or thread that pasted the batch) recorded: a ``MODE: task`` line, or the REPORT.md form
    ``chat mode **Task**``. The chat cannot know its own mode, so the ``MODE:`` inside a ``T0 REPORT`` (``MODEL: x | MODE: y``, the
    chat's own words) is not an operator line."""
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip().lstrip(">*- ").replace("**", "").replace("`", "").strip()
        m = _OPERATOR_MODE.match(line)
        if m:
            return (m.group(1) or m.group(2)).lower()
    return None


def gemini_task_report(path) -> dict:
    """Rule 19 (OR-V35, the owner's memory rule: Gemini photos only in Task mode, 6 per batch) on the intake record of a Gemini turn: a text
    file holding the pasted answer (a ``T0 REPORT`` or a ``BATCH REPORT`` of ``gemini_task/report.py``; a structure that does not parse
    raises, so the send gate BLOCKs, it is never a pass) and the operator's mode line (``operator_mode``).

    - **Count**: more picture lines than ``imagegen.turn_pack.DEFAULT_TURN`` (6) is a FAIL; a shorter batch is fine (a queue's last
      batch or a limit stop is shorter and the report cannot say which).
    - **Mode** (lead 2026-11-20 09:06): an operator line naming Task and a count of 6 or less is PASS; no operator line is NOT_RUN
      "mode not measured"; an operator mode other than Task is FAIL. A chat's own T0 ``MODE:`` naming something else is a FAIL too, but
      never a pass by itself."""
    from explainer_engine.gemini_task import report as RP
    from explainer_engine.imagegen import turn_pack as TP
    text = Path(path).read_text(encoding="utf-8")
    t0 = "T0 REPORT" in text.upper()
    rep = RP.parse_t0_report(text) if t0 else {"batch": RP.parse_batch_report(text), "mode": None}
    n = len(rep["batch"]["items"])
    limit = int(TP.DEFAULT_TURN)
    mode = operator_mode(text)
    if mode is not None and mode != "task":
        return {"status": FAIL, "value": n, "detail": f"the operator recorded mode {mode!r}, rule 19 allows Gemini photos only in Task mode"}
    if t0 and rep["mode"] and "task" not in rep["mode"].lower():
        return {"status": FAIL, "value": n, "detail": f"the chat reports MODE {rep['mode']!r}, rule 19 allows Gemini photos only in Task mode"}
    if n > limit:
        return {"status": FAIL, "value": n, "detail": f"{n} pictures in one batch, rule 19 allows {limit}"}
    if mode is None:
        return {"status": NOT_RUN, "value": n, "detail": f"{n} of at most {limit} pictures (counted), but no operator MODE line "
                "(`MODE: task` or `chat mode **Task**`): the mode is not measured"}
    return {"status": PASS, "value": n, "detail": f"{n} of at most {limit} pictures; operator mode task"}


gemini_task_report.kinds = (".txt", ".md")


FACE_IOU_MIN = float(SR.T("BP-214", "face_iou_min"))   # REVIEW-level engineering default (hypothesis, not binding until the owner has seen it)


def yunet_boxes(path) -> list[tuple[float, float, float, float]]:
    """YuNet face boxes of one picture as ``(x0, y0, x1, y1)`` in shares of the picture, from ``qa.face_points.detect`` (the project's one
    YuNet call). Raises ``RuntimeError`` when OpenCV or the model is missing: the caller says NOT_RUN."""
    from explainer_engine.qa import face_points as FP
    from explainer_engine.qa import pixels as PX
    model = PX.yunet_path()
    if PX._cv2() is None or model is None:
        raise RuntimeError("OpenCV or the YuNet model (tools/yunet or $EXPLAINER_YUNET) is missing")
    return [(f["x"] - f["w"] / 2, f["y"] - f["h"] / 2, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2) for f in FP.detect(Path(path), model)]


def iou(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    inter = max(0.0, w) * max(0.0, h)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def faces_intact_pair(before, after, detect=None) -> dict:
    """BP-214 (OR-V36): the same number of faces before and after, and every face box of the result overlapping its original at IoU of at
    least ``FACE_IOU_MIN``. Each original face is matched to the unused result face with the best overlap, in left-to-right order of the
    originals. ``detect(path)`` returns boxes in shares (default ``yunet_boxes``); no OpenCV or model, or no face in the original, is
    NOT_RUN, never a pass. The value is the lowest IoU. A hypothesis rule: the FAIL text says so."""
    detect = detect or yunet_boxes
    try:
        b, a = detect(before), detect(after)
    except RuntimeError as exc:
        return {"status": NOT_RUN, "value": None, "detail": f"faces not measured: {exc}"}
    tag = f"(BP-214 REVIEW-level default, IoU at least {FACE_IOU_MIN}, not binding until the owner has seen it)"
    if not b and not a:
        return {"status": NOT_RUN, "value": None, "detail": "no face found in the original or the result: nothing to compare"}
    if len(b) != len(a):
        return {"status": FAIL, "value": None, "detail": f"{len(b)} face(s) before, {len(a)} after {tag}"}
    free = list(a)
    worst = 1.0
    for box in sorted(b, key=lambda x: x[0]):
        best = max(free, key=lambda c: iou(box, c))
        free.remove(best)
        worst = min(worst, iou(box, best))
    worst = round(worst, 4)
    if worst < FACE_IOU_MIN:
        return {"status": FAIL, "value": worst, "detail": f"a face moved or changed: lowest IoU {worst} of {len(b)} face(s) {tag}"}
    return {"status": PASS, "value": worst, "detail": f"{len(b)} face(s), lowest IoU {worst} {tag}"}


def faces_intact(path) -> dict:
    """The send-gate adapter of ``faces_intact_pair``: a ``<name>.faces.json`` pair file ``{"before": "a.png", "after": "b.png"}`` (paths
    relative to the pair file). A ``.json`` without those two keys is NOT_RUN (not a pair file); a missing picture raises (BLOCK)."""
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not {"before", "after"} <= set(doc):
        return {"status": NOT_RUN, "value": None, "detail": "not a faces pair file (needs keys before and after)"}
    before, after = p.parent / doc["before"], p.parent / doc["after"]
    for f in (before, after):
        if not f.is_file():
            raise FileNotFoundError(f"{f} is not a picture")
    return faces_intact_pair(before, after)


faces_intact.kinds = (".json",)


def main(argv=None) -> int:
    """``python -m explainer_engine.qa.send_validators living_motion|gemini_task_report|faces_intact <file>...``: one line per clip, exit 1 on any FAIL, 2 on an error."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.qa.send_validators")
    ap.add_argument("validator", choices=("living_motion", "gemini_task_report", "faces_intact"))
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    worst = 0
    for f in a.files:
        try:
            r = {"living_motion": living_motion, "gemini_task_report": gemini_task_report, "faces_intact": faces_intact}[a.validator](f)
        except Exception as exc:                       # an undecodable file is an error, never a pass
            print(f"BLOCK {f}: {type(exc).__name__}: {exc}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        print(f"{r['status']:8} {'' if r['value'] is None else r['value']!s:>7}  {f}  {r['detail']}")
        worst = max(worst, 1 if r["status"] == FAIL else 0)
    return worst


if __name__ == "__main__":
    import sys
    sys.exit(main())
