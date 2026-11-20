"""HUD readability check for a rendered map clip: does the text the schedule says is on screen read back by OCR?

Per sampled frame the expected items come from `maplibre_spec.schedule` (counter value, counter label, date chip, visible towns).
RapidOCR (and most scene-text OCR) never reads an isolated single glyph such as the counter's opening "0" (measured: a plain black "0" or
"8" on white is not read either), so a one-character expected value is checked as INK instead: pixels of the preset's counter colour
must exist in the top-left quarter, as a glyph at least 2 % of the frame high. Every item says which method decided it.
CLI: python -m explainer_engine.maps.maplibre_lane.hud_ocr <spec.json> <frames_dir> [step]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from explainer_engine.maps.maplibre_lane.render import _hex_rgb, load_style_preset
from explainer_engine.maps.maplibre_spec import load_shot_spec, schedule

OcrFn = Callable[[Any], list[str]]  # image (numpy array) -> recognised text lines
MIN_GLYPH_HEIGHT_FRACTION = 0.02
MIN_INK_PIXELS = 150
INK_TOLERANCE = 48.0


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def expected_items(spec: dict[str, Any], frame: int) -> dict[str, str]:
    """Text the shot shows at `frame`, by item name."""
    state = schedule(spec, frame)
    items = {"counter": _norm(f"{state['counter']:,}"), "label": _norm(spec["counter"]["label"])}
    if state["date"]:
        items["date"] = _norm(state["date"])
    for town in state["towns_visible"]:
        items["town:" + town] = _norm(town)
    return items


def ink_glyph_present(frame_rgb: Any, colour: tuple[int, int, int], min_height_fraction: float = MIN_GLYPH_HEIGHT_FRACTION) -> bool:
    """True when pixels near `colour` in the top-left quarter form a glyph tall enough to read."""
    import numpy as np

    h, w = frame_rgb.shape[:2]
    quarter = frame_rgb[: h // 2, : w // 2].astype(np.int32)
    dist = np.sqrt(((quarter - np.array(colour, dtype=np.int32)) ** 2).sum(axis=2))
    ys, xs = np.nonzero(dist < INK_TOLERANCE)
    if ys.size < MIN_INK_PIXELS:
        return False
    return bool((ys.max() - ys.min() + 1) >= min_height_fraction * h)


def check_frame(frame_rgb: Any, spec: dict[str, Any], frame: int, ocr: OcrFn, counter_colour: tuple[int, int, int]) -> dict[str, Any]:
    """Check one frame; returns {item: {"expected", "found", "method"}}."""
    blob = " ".join(_norm(t) for t in ocr(frame_rgb))
    out: dict[str, Any] = {}
    for name, want in expected_items(spec, frame).items():
        if name == "counter" and len(want) == 1:
            out[name] = {"expected": want, "found": ink_glyph_present(frame_rgb, counter_colour), "method": "ink"}
        else:
            out[name] = {"expected": want, "found": want in blob, "method": "ocr"}
    return out


def check_clip(spec_path: str | Path, frames_dir: str | Path, step: int = 12, ocr: OcrFn | None = None) -> dict[str, Any]:
    """Run the check on every `step`-th frame of a rendered clip."""
    import numpy as np
    from PIL import Image

    spec = load_shot_spec(spec_path)
    preset = load_style_preset(str(spec.get("style_preset", "neutral")))
    colour = _hex_rgb(preset["hud"]["counter_value"])
    if ocr is None:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()
        ocr = lambda img: [r[1] for r in (engine(img)[0] or [])]  # noqa: E731
    rows = []
    for path in sorted(Path(frames_dir).glob("frame_*.png"))[::step]:
        idx = int(path.stem.split("_")[1])
        img = np.asarray(Image.open(path).convert("RGB"))
        rows.append({"frame": idx, "items": check_frame(img, spec, idx, ocr, colour)})
    total = sum(len(r["items"]) for r in rows)
    found = sum(1 for r in rows for v in r["items"].values() if v["found"])
    return {"frames": len(rows), "items": total, "found": found, "rows": rows}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    report = check_clip(args[0], args[1], int(args[2]) if len(args) > 2 else 12)
    print(json.dumps(report, indent=1))
    return 0 if report["found"] == report["items"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
