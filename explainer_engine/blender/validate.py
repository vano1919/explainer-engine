"""The render validator of the Blender lanes (roadmap section 13, ICW-08; BP-174, BP-173). Free and local: numpy + PIL + ffprobe.

    python -m explainer_engine.blender.validate <shot dir> [--still-mode hold] [--job-dir J] [--job-id ID]

``RenderValidator().check(shot_dir, spec)`` reads a shot folder of ``blender/render.py`` (``frames/frame_%06d.png``, and the clip
``shot.mkv`` when the spec asks for ``mkv_ffv1``) against its ``shot_spec/2`` and returns ``qa_report/1`` check rows (check_id, rule,
severity, measured, threshold, passed). ``report(job_id, checks)`` turns the rows of all shots into one ``qa_report/1`` of stage
``clip`` (``qa/retry_router.build_report``); ``qa/retry_router.write_report`` writes it to ``<job>/qa/clip.qa_report.json``, which
the review bundle already copies and ``qa/scorecard`` row 5 reads. There is no retry directive: the OR-04 actions are the legacy
image route's (D-105), so a failed FAIL row is ESCALATE_TO_HUMAN.

    RV-FRAMES       FAIL    the frame files are exactly frame_000000 .. frame_<n-1> of ``spec.clock.frames``
    RV-SIZE         FAIL    every frame is the declared tier: ``spec.frame`` width x height x ``render_scale``
    RV-FPS          FAIL    the clock is 24 fps (CN-09) and, when there is a clip, it probes at that rate with every frame
    RV-BLACK        FAIL    more than BP-174 ``black_frames_max`` black frames
    RV-FROZEN       FAIL    a run of identical frames longer than BP-174 ``frozen_frames_max`` (exempt: ``still_mode`` hold)
    RV-FLICKER      REVIEW  a mean-luma change above BP-174 ``flicker_luma_delta`` between neighbouring frames
    RV-LINE         REVIEW  an edge-pixel count that changes by more than BP-174 ``line_edge_variance`` between neighbours
    RV-LINE-WEIGHT  REVIEW  the measured stroke width, scaled to 1440 rows, outside BP-173 ``weight_px_1440``
    RV-CAL-*        INFO    the calibration numbers ICW-09 needs (darkest frame, smallest neighbour change, the stroke spread)

Definitions (no number of their own, so nothing here needs a registry row the creator has not given):

- a black frame has no lit pixel: the same test as ``render.check_png`` (all colour channels 0). A near-black frame is not black;
  its luma is reported in RV-CAL-DARK so ICW-09 can propose a tolerance;
- a frozen run is a run of frames whose pixels are identical. Blender renders the same scene state to the same pixels (fixed
  seed), so a frame that does not change is exactly equal to its neighbour; the smallest non-zero change is RV-CAL-STILL;
- luma is Rec. 709 on the display sRGB values in 0..1 (the scale of BP-174's 0.08);
- an edge pixel is an ink pixel: its luma is nearer the palette's ``ink`` token than its ``paper`` token (``design/palette.json``,
  the line and the backdrop of ``style.StyleTokens``). Dark shade steps count too, the same in every frame, so the ratio between
  neighbours still measures the Line Art;
- the stroke width is the median length of the ink runs along rows and columns that are at most twice BP-173's upper bound long
  (a line crossed at right angles is one run of its width; longer runs are filled shapes, not strokes).

``style_findings(frames)`` is the style-conformance row of section 13: the mean CIE76 dE of the frame to its nearest palette token,
the paper grain (the high-frequency luma spread inside flat areas) and the specular-highlight share (near-white, unsaturated
pixels). No threshold is registered for them, so they are INFO rows with the measured value, as ``qa/identity`` does before a
calibrated number exists; ICW-07 / ICW-09 register their BP rows, and only then do they become REVIEW.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.blender import style as S
from explainer_engine.blender.render import FRAME_NAME
from explainer_engine.core.errors import ContractError
from explainer_engine.qa import retry_router as RR
from explainer_engine.standards import sourced_rules as SR

RULE, LINE_RULE = "BP-174", "BP-173"
BLACK_FRAMES_MAX = SR.T("BP-174", "black_frames_max")
FROZEN_FRAMES_MAX = SR.T("BP-174", "frozen_frames_max")
FLICKER_LUMA_DELTA = SR.T("BP-174", "flicker_luma_delta")
LINE_EDGE_VARIANCE = SR.T("BP-174", "line_edge_variance")
WEIGHT_PX_1440 = SR.T("BP-173", "weight_px_1440")
FPS = 24  # CN-09 and D-96: one clock for every shot (core/contracts refuses another rate before a render starts)
LUMA = np.array([0.2126, 0.7152, 0.0722])
NOT_A_LOOK_COLOUR = ("chroma_key",)  # a keying colour, never part of the drawn frame


def check(check_id: str, rule: str, severity: str, measured, threshold, passed: bool) -> dict:
    return {"check_id": check_id, "rule": rule, "severity": severity, "measured": measured, "threshold": threshold,
            "passed": bool(passed)}


# --- pixels ------------------------------------------------------------------------------------------------------------------

def load(path: Path | str) -> np.ndarray:
    """A frame as uint8 RGB (alpha dropped: the frame is judged as it is shown)."""
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.uint8)


def luma(img: np.ndarray) -> np.ndarray:
    return (np.asarray(img, dtype=np.float64) / 255.0) @ LUMA


def _hex_luma(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    return float(np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]) @ LUMA)


def ink_level(palette: dict[str, str] | None = None, ink: str = "ink", paper: str = "paper") -> float:
    """The luma half way between the ink token and the paper token: below it a pixel is ink."""
    p = palette or S.palette()
    return (_hex_luma(p[ink]) + _hex_luma(p[paper])) / 2


def runs(mask: np.ndarray) -> np.ndarray:
    """Lengths of the runs of True along every row of ``mask`` (2-D bool)."""
    m = np.asarray(mask, dtype=np.int8)
    pad = np.zeros((m.shape[0], 1), dtype=np.int8)
    d = np.diff(np.hstack([pad, m, pad]), axis=1)
    starts, ends = np.nonzero(d == 1), np.nonzero(d == -1)
    return ends[1] - starts[1]


def stroke_width(mask: np.ndarray, cap: float) -> float | None:
    """The median ink run (rows and columns) no longer than ``cap`` pixels; None when the frame has no such run."""
    r = np.concatenate([runs(mask), runs(mask.T)])
    r = r[r <= cap]
    return float(np.median(r)) if r.size else None


def frame_stats(img: np.ndarray, level: float, cap: float) -> dict:
    y = luma(img)
    ink = y < level
    return {"lit": bool(img.any()), "luma": float(y.mean()), "ink": int(ink.sum()), "stroke": stroke_width(ink, cap)}


# --- the clip ----------------------------------------------------------------------------------------------------------------

def probe(path: Path | str) -> dict | None:
    """ffprobe of the clip's video stream: width, height, fps (exact fraction as float), frames (counted)."""
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", str(path)], capture_output=True,
                       text=True)
    if p.returncode != 0:
        return None
    s = (json.loads(p.stdout).get("streams") or [{}])[0]
    rate = s.get("r_frame_rate") or "0/1"
    return {"width": s.get("width"), "height": s.get("height"), "fps": float(Fraction(rate)) if rate != "0/0" else 0.0,
            "frames": int(s.get("nb_read_frames") or 0)}


# --- the validator -----------------------------------------------------------------------------------------------------------

class RenderValidator:
    """Section 13's render validator. ``palette`` (token -> hex) and ``probe`` are injectable for tests."""

    def __init__(self, *, palette: dict[str, str] | None = None, probe=probe) -> None:
        self.palette = palette or S.palette()
        self.probe = probe
        self.level = ink_level(self.palette)

    def check(self, shot_dir: Path | str, spec: dict, *, still_mode: str | None = None) -> list[dict]:
        """Every row for one rendered shot. ``still_mode`` is the film_shots/3 shot's (``hold`` exempts RV-FROZEN)."""
        if spec.get("schema") != "shot_spec/2":
            raise ContractError("the render validator checks shot_spec/2 renders only (Blender lanes, D-96)")
        shot_dir = Path(shot_dir)
        sid = spec["shot_id"]
        n, fps = spec["clock"]["frames"], spec["clock"]["fps"]
        w = round(spec["frame"]["width"] * spec["frame"]["render_scale"])
        h = round(spec["frame"]["height"] * spec["frame"]["render_scale"])
        rows: list[dict] = []

        want = [FRAME_NAME.format(index=i) for i in range(n)]
        have = sorted(p.name for p in (shot_dir / "frames").glob("*.png"))
        missing, extra = sorted(set(want) - set(have)), sorted(set(have) - set(want))
        rows.append(check(f"{sid}:RV-FRAMES", RULE, "FAIL", f"{len(have)} files, {len(missing)} missing, {len(extra)} extra"
                          + (f" (first missing {missing[0]})" if missing else "") + (f" (first extra {extra[0]})" if extra else ""),
                          n, not missing and not extra))

        cap = 2 * WEIGHT_PX_1440[1] * h / 1440
        stats, sizes, still, frozen, run = [], [], [], 0, 1
        prev = None
        for name in want:
            if name not in have:
                prev = None
                run = 1
                continue
            img = load(shot_dir / "frames" / name)
            sizes.append((img.shape[1], img.shape[0]))
            stats.append(frame_stats(img, self.level, cap))
            if prev is not None and prev.shape == img.shape:
                diff = float(np.abs(prev.astype(np.int16) - img.astype(np.int16)).mean())
                if diff == 0.0:
                    run += 1
                else:
                    still.append(diff)
                    run = 1
                frozen = max(frozen, run)
            prev = img
        frozen = max(frozen, 1 if stats else 0)

        wrong = [s for s in sizes if s != (w, h)]
        rows.append(check(f"{sid}:RV-SIZE", RULE, "FAIL", f"{len(wrong)} of {len(sizes)} frames not {w}x{h}"
                          + (f" (e.g. {wrong[0][0]}x{wrong[0][1]})" if wrong else ""), f"{w}x{h}", not wrong))
        rows += self._fps_rows(shot_dir, spec, sid, n, fps, w, h)

        black = sum(1 for s in stats if not s["lit"])
        rows.append(check(f"{sid}:RV-BLACK", RULE, SR.level(RULE, "FAIL"), black, BLACK_FRAMES_MAX, black <= BLACK_FRAMES_MAX))
        exempt = still_mode == "hold"
        rows.append(check(f"{sid}:RV-FROZEN", RULE, "INFO" if exempt else SR.level(RULE, "FAIL"),
                          f"longest identical run {frozen} frames" + (" (still_mode hold: exempt)" if exempt else ""),
                          FROZEN_FRAMES_MAX, exempt or frozen <= FROZEN_FRAMES_MAX))

        lum = [s["luma"] for s in stats]
        jump = max((abs(b - a) for a, b in zip(lum, lum[1:])), default=0.0)
        rows.append(check(f"{sid}:RV-FLICKER", RULE, "REVIEW", round(jump, 4), FLICKER_LUMA_DELTA, jump <= FLICKER_LUMA_DELTA))
        ink = [s["ink"] for s in stats]
        change = max((abs(b - a) / a if a else (0.0 if not b else 1.0) for a, b in zip(ink, ink[1:])), default=0.0)
        rows.append(check(f"{sid}:RV-LINE", RULE, "REVIEW", round(change, 4), LINE_EDGE_VARIANCE, change <= LINE_EDGE_VARIANCE))

        strokes = [s["stroke"] * 1440 / h for s in stats if s["stroke"] is not None]
        lo, hi = WEIGHT_PX_1440
        if strokes:
            med = float(np.median(strokes))
            rows.append(check(f"{sid}:RV-LINE-WEIGHT", LINE_RULE, "REVIEW", round(med, 3), [lo, hi], lo <= med <= hi))
            rows.append(check(f"{sid}:RV-CAL-STROKE", LINE_RULE, "INFO", f"min {min(strokes):.2f} max {max(strokes):.2f} px at "
                              f"1440 rows; declared {spec.get('look', {}).get('line_weight_px')}", None, True))
        else:
            rows.append(check(f"{sid}:RV-LINE-WEIGHT", LINE_RULE, "REVIEW", "no ink stroke found", [lo, hi], False))
        rows.append(check(f"{sid}:RV-CAL-DARK", RULE, "INFO", round(min(lum), 4) if lum else None, None, True))
        rows.append(check(f"{sid}:RV-CAL-STILL", RULE, "INFO", round(min(still), 4) if still else None, None, True))
        return rows

    def _fps_rows(self, shot_dir: Path, spec: dict, sid: str, n: int, fps: float, w: int, h: int) -> list[dict]:
        ok = fps == FPS
        detail = f"clock {fps} fps"
        if spec["render"]["output"] == "mkv_ffv1":
            clip = shot_dir / "shot.mkv"
            got = self.probe(clip) if clip.exists() else None
            if got is None:
                ok, detail = False, detail + "; shot.mkv missing or unreadable"
            else:
                ok = ok and abs(got["fps"] - fps) < 1e-6 and got["frames"] == n and (got["width"], got["height"]) == (w, h)
                detail += f"; shot.mkv {got['width']}x{got['height']} {got['fps']:g} fps {got['frames']} frames"
        return [check(f"{sid}:RV-FPS", RULE, "FAIL", detail, FPS, ok)]

    @staticmethod
    def report(job_id: str, checks: list[dict]) -> dict:
        """One ``qa_report/1`` (stage ``clip``) of all the shots' rows; write it with ``qa/retry_router.write_report``."""
        return RR.build_report(job_id, "clip", checks)


# --- style conformance (INFO until its BP rows exist) --------------------------------------------------------------------------

def _lab(rgb: np.ndarray) -> np.ndarray:
    """CIE L*a*b* (D65) of display sRGB in 0..1, vectorised (the formula of ``blender/grade.lab``)."""
    c = np.clip(rgb, 0.0, 1.0)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def palette_de(img: np.ndarray, palette: dict[str, str]) -> float:
    """Mean CIE76 dE of every pixel to its nearest palette token (``chroma_key`` left out)."""
    toks = np.array([[int(v.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)] for k, v in palette.items()
                     if k not in NOT_A_LOOK_COLOUR])
    px = _lab(np.asarray(img, dtype=np.float64).reshape(-1, 3) / 255.0)
    tk = _lab(toks)
    d = np.sqrt(((px[:, None, :] - tk[None, :, :]) ** 2).sum(-1)).min(1)
    return float(d.mean())


def paper_grain(img: np.ndarray) -> float:
    """The luma spread left after a 3x3 box blur, inside flat areas (where the blur barely moves the luma's gradient):
    the paper texture's grain, in luma units 0..1."""
    y = luma(img)
    p = np.pad(y, 1, mode="edge")
    blur = sum(p[i:i + y.shape[0], j:j + y.shape[1]] for i in range(3) for j in range(3)) / 9
    hf = y - blur
    gy, gx = np.gradient(blur)
    flat = np.hypot(gx, gy)
    keep = flat <= np.median(flat)
    return float(hf[keep].std()) if keep.any() else 0.0


def specular_share(img: np.ndarray) -> float:
    """Share of near-white, unsaturated pixels (luma above 0.95, saturation under 0.1): a photoreal highlight cue."""
    x = np.asarray(img, dtype=np.float64) / 255.0
    mx, mn = x.max(-1), x.min(-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return float(((x @ LUMA > 0.95) & (sat < 0.1)).mean())


def style_findings(frames: list[Path | str], shot_id: str, *, palette: dict[str, str] | None = None, size: int = 320) -> list[dict]:
    """Section 13's style-conformance rows on the given frames (each downscaled to ``size`` px wide): INFO with the measured value."""
    pal = palette or S.palette()
    de, grain, spec = [], [], []
    for f in frames:
        with Image.open(f) as im:
            im = im.convert("RGB")
            im.thumbnail((size, size * 4))
            img = np.asarray(im, dtype=np.uint8)
        de.append(palette_de(img, pal))
        grain.append(paper_grain(img))
        spec.append(specular_share(img))
    m = lambda v: round(float(np.mean(v)), 4) if v else None  # noqa: E731
    return [check(f"{shot_id}:ST-PALETTE", "style", "INFO", m(de), None, True),
            check(f"{shot_id}:ST-PAPER", "style", "INFO", m(grain), None, True),
            check(f"{shot_id}:ST-SPECULAR", "style", "INFO", m(spec), None, True)]


# --- the command -------------------------------------------------------------------------------------------------------------

def run(shot_dir: Path | str, *, still_mode: str | None = None, style: bool = True) -> list[dict]:
    """All rows of a shot folder of ``blender/render.py`` (its ``spec.json``)."""
    shot_dir = Path(shot_dir)
    spec = json.loads((shot_dir / "spec.json").read_text(encoding="utf-8"))
    rows = RenderValidator().check(shot_dir, spec, still_mode=still_mode)
    if style:
        frames = sorted((shot_dir / "frames").glob("*.png"))
        pick = [frames[i] for i in sorted({0, len(frames) // 2, len(frames) - 1})] if frames else []
        rows += style_findings(pick, spec["shot_id"])
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.validate", description=__doc__.split("\n\n")[0])
    ap.add_argument("shot_dirs", nargs="+", type=Path)
    ap.add_argument("--still-mode", default=None)
    ap.add_argument("--job-dir", type=Path, default=None, help="write <job>/qa/clip.qa_report.json")
    ap.add_argument("--job-id", default=None)
    a = ap.parse_args(argv)
    rows = [r for d in a.shot_dirs for r in run(d, still_mode=a.still_mode)]
    for r in rows:
        mark = "ok " if r["passed"] else r["severity"]
        print(f"{mark:6} {r['check_id']:28} {r['measured']}  (threshold {r['threshold']})")
    if a.job_dir is not None:
        rep = RenderValidator.report(a.job_id or a.job_dir.name, rows)
        print(RR.write_report(a.job_dir, rep))
    return 1 if any(r["severity"] == "FAIL" and not r["passed"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
