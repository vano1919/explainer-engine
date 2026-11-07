"""KP-54: the free Blender gate before a paid Qwen edit (creator 2026-11-07 14:42 UTC, Argon's review of the 6-photo test).

BL-01 every named subject's window in the still is bright enough (mean luma >= MIN_LUMA), BL-02 the colour temperature agrees with
the prompt's light words (blue / night / dusk: the sky band blue over red; orange / fire: the fire's window red over blue), BL-03 the
layout's clutter clash list (KP-53) is empty. Any FAIL stops the paid run.

    python -m explainer_engine.qa.blender_gate <still.png> <layout id>      # exits 1 on a FAIL
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MIN_LUMA = 0.15
WIN = 0.04            # half window, share of the frame width
COLD = re.compile(r"\b(blue|night|dusk|moon|snowstorm)\b", re.I)
WARM = re.compile(r"\b(orange|firelight|fire|torch|hearth)\b", re.I)


def _window(arr, sx: float, sy: float):
    h, w = arr.shape[:2]
    x0, x1 = int(max(0, (sx - WIN) * w)), int(min(w, (sx + WIN) * w))
    y0, y1 = int(max(0, (sy - WIN * 16 / 9) * h)), int(min(h, (sy + WIN * 16 / 9) * h))
    return arr[y0:y1, x0:x1]


def luma(rgb) -> float:
    return float((0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).mean())


def check(arr, subjects: dict, prompt: str, fire: tuple | None, clashes: list[str]) -> list[dict]:
    """``arr`` float RGB 0..1 (H, W, 3); ``subjects`` name -> (sx, sy) screen position; ``fire`` the fire's (sx, sy) or None."""
    out = []
    for n, (sx, sy) in subjects.items():
        if not (0 <= sx <= 1 and 0 <= sy <= 1):
            out.append({"id": "BL-01", "severity": "FAIL", "msg": f"{n} is outside the frame ({sx:.2f}, {sy:.2f})"})
            continue
        lv = luma(_window(arr, sx, sy))
        if lv < MIN_LUMA:
            out.append({"id": "BL-01", "severity": "FAIL", "msg": f"{n} too dark: luma {lv:.3f} < {MIN_LUMA}"})
    if COLD.search(prompt):
        sky = arr[: arr.shape[0] // 3]
        r, b = float(sky[..., 0].mean()), float(sky[..., 2].mean())
        if not b > r:
            out.append({"id": "BL-02", "severity": "FAIL", "msg": f"the prompt says a cold light but the sky band is warm (R {r:.3f} >= B {b:.3f})"})
    if WARM.search(prompt) and fire is not None:
        w = _window(arr, *fire)
        r, b = float(w[..., 0].mean()), float(w[..., 2].mean())
        if not r > b:
            out.append({"id": "BL-02", "severity": "FAIL", "msg": f"the prompt says firelight but the fire's window is cold (R {r:.3f} <= B {b:.3f})"})
    for c in clashes:
        out.append({"id": "BL-03", "severity": "FAIL", "msg": c})
    return out


def gate(png: Path, layout_id: str, prompt: str) -> list[dict]:
    import numpy as np
    from PIL import Image
    from explainer_engine.blender import stoneage_test_layouts as S
    _sa, scene, way, *angle = layout_id.split("_")   # sa_<scene>_<way>[_<angle>] (test A angles, 15:04 UTC)
    blocks, cast, structure, cam = {"cave": S._cave, "ice": S._ice, "camp": S._camp}[scene](way)
    if angle:
        cam = S.ANGLES[scene][angle[0]]
    arr = np.asarray(Image.open(png).convert("RGB"), dtype=np.float32) / 255.0
    subj = {n: S.project(cam, S._subject_point(blocks, cast, n))[:2] for n in S.SUBJECTS[scene]}
    flame = next((b for b in blocks if b.get("name", "").endswith("_flame")), None)
    fire = S.project(cam, flame["pos"])[:2] if flame else None
    return check(arr, subj, prompt, fire, S.clutter_clashes(blocks + S.proxies(cast), cast, cam, scene, structure))


def main(argv: list[str] | None = None) -> int:
    a = argv or sys.argv[1:]
    png, lid = Path(a[0]), a[1]
    prompt = a[2] if len(a) > 2 else ""
    found = gate(png, lid, prompt)
    print(json.dumps(found, indent=1))
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
