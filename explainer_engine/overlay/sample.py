"""B5 sample: a Toba map overlay (inset card) on an LTX 2K clip, rendered by HyperFrames, with the timing check against the word spine.

    python -m explainer_engine.overlay.sample --shot S02_SH010 --clip action_2k.mp4 --out <dir>

The word times are a SYNTHETIC Scribe-shaped fixture (no narration has been generated yet): they prove the path from word times to
frames, not any real read. Replace ``--scribe`` with a real Scribe word list of the line when the narration exists.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.maps import geo, plate, relief
from explainer_engine.overlay import hyperframes as HF
from explainer_engine.overlay import spec as OS

REPO = Path(__file__).resolve().parents[2]
EP = REPO / "episodes" / "ep_toba" / "planning"
CARD = (1408, 96, 1056, 594)        # x, y, w, h in the 2560x1440 frame: top right, over the sky of the LTX clips (the heroes are left and low)
DATE = {"S02_SH010": "74,000 years ago", "S01_SH008": "74,000 years ago"}


def synthetic_scribe(text: str, fps: int, seed: str, fit_s: float, wpm: float = 170.0) -> list[dict]:
    """Scribe-shaped words (``text, start, end, type``) with uneven, seeded timing and a pause after punctuation. SYNTHETIC."""
    rng = random.Random(seed)
    t, out = 0.25, []
    for tok in text.split():
        n = len(re.findall(r"[A-Za-z0-9']+", tok)) or 1
        d = max(0.12, (60.0 / wpm) * n * rng.uniform(0.7, 1.3))
        out.append({"text": tok, "start": round(t, 3), "end": round(t + d, 3), "type": "word"})
        t += d + (0.28 if tok.endswith((",", ".", "—")) or "—" in tok else 0.02)
    k = fit_s / out[-1]["end"]       # the whole read fits the shot's window (88 % of it), as a real take would be cut to
    return [{**w, "start": round(w["start"] * k, 3), "end": round(w["end"] * k, 3)} for w in out]


def load_shot(shot_id: str) -> tuple[dict, dict, dict]:
    script = json.loads((EP / "production_script_2min.json").read_text(encoding="utf-8"))
    prop = json.loads((EP / "map_actions_proposal_p4.json").read_text(encoding="utf-8"))
    shot = dict(next(s for s in script["shots"] if s["shot_id"] == shot_id))
    shot["actions"] = prop["shots"][shot_id]["actions"]
    shot["map_view"] = prop["shots"][shot_id]["map_view"]
    return shot, script, prop["places"]


def draw_plate(spec: dict, out_png: Path) -> Path:
    c = spec["card"]
    v = spec["view"]
    view = geo.View(v["lon"], v["lat"], v["span_km"], c["w"], c["h"])
    relief_ok = relief.raster_path().exists()
    img = plate.render_plate(view, ss=2, shaded_relief=relief_ok).convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=c["radius"], fill=255)
    img.putalpha(mask)
    img.save(out_png)
    return out_png


def build(shot_id: str, scribe: list[dict] | None = None) -> tuple[dict, list[dict]]:
    shot, script, places = load_shot(shot_id)
    fps = 24
    text = next(l["text"] for l in script["audio_lines"] if l["line_id"] == shot["audio_line_ids"][0])
    scribe = scribe or synthetic_scribe(text, fps, shot_id, 0.88 * float(shot["target_duration_seconds"]))
    spine = OS.spine_from_scribe(scribe, fps)
    spec = OS.build(shot, script, places, fps, card=CARD, spine=spine, date_text=DATE.get(shot_id), hold_frames=240)
    return spec, scribe


def _alpha_frames(overlay: Path, tmp: Path, name: str) -> np.ndarray:
    raw = tmp / f"{name}.raw"
    dec = ["-c:v", "libvpx-vp9"] if str(overlay).endswith(".webm") else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", *dec, "-i", str(overlay), "-vf", "alphaextract,scale=640:360:flags=area", "-pix_fmt", "gray",
                    "-f", "rawvideo", str(raw)], check=True)
    return np.fromfile(raw, np.uint8).reshape(-1, 360, 640)


def _ease(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


MODEL = {   # the alpha inside the item's box, as a share of its final value, frame j after the plan's start
    "highlight": lambda j, n: _ease(j / n), "route_arrow": lambda j, n: _ease(j / n), "front_line": lambda j, n: _ease(j / n),
    "label": lambda j, n: min(1.0, j / 6.0), "plume": lambda j, n: _ease(j / n) ** 2, "spread": lambda j, n: _ease(j / n) ** 2,
}


def timing_report(spec: dict, tmp: Path, fmt: str = "webm") -> list[dict]:
    """Each item is rendered ALONE (a short, draft-quality HyperFrames render) and the alpha inside its own box is followed frame by
    frame. ``shift`` = the whole-frame offset (-3..3) at which the measured curve best matches the model curve of its kind (the same
    cubic ease the Python drawer uses); 0 = it moves exactly when the word says. ``err`` = the worst gap to the model at that shift
    (share of the final change). ``early`` = the alpha moved before the start (after the card chrome settled at frame 12).
    Pulses (cyclic) and counters (text) have no ramp: only ``early`` and the first change are reported."""
    out = []
    n_anim = spec["anim_frames"]
    for it, reg in zip(spec["items"], OS.active_regions(spec)):
        st = it["start"]
        one = {**spec, "items": [it], "frames": st + n_anim + 12, "date_chip": None}
        proj = HF.write_project(one, tmp / f"iso_{it['id']}")
        ov = tmp / f"iso_{it['id']}.{fmt}"
        HF.render_overlay(proj, ov, fmt=fmt, quality="draft")
        a = _alpha_frames(ov, tmp, f"iso_{it['id']}").astype(np.int16)
        sx, sy = 640 / spec["frame"]["w"], 360 / spec["frame"]["h"]
        x0, y0, x1, y1 = reg["box"]
        box = (slice(int(max(0, y0 * sy)), int(min(360, y1 * sy + 1))), slice(int(max(0, x0 * sx)), int(min(640, x1 * sx + 1))))
        base = a[st - 1][box]
        d = np.array([np.abs(f[box] - base).sum() for f in a], dtype=np.float64)
        final = d[min(len(d) - 1, st + n_anim + 8)]
        row = {"id": it["id"], "kind": it["kind"], "word": it["word"], "plan_start": st,
               "early": bool(d[12:st].max() > 255 * 3) if st > 12 else None,
               "first_change": next((i for i in range(st, len(d)) if d[i] > 255 * 3), None)}
        m = MODEL.get(it["kind"])
        if m and final > 0:
            best = None
            for shift in range(-3, 4):
                err = max(abs(d[min(len(d) - 1, max(0, st + j + shift))] / final - m(j, n_anim)) for j in range(0, n_anim + 1))
                if best is None or err < best[1]:
                    best = (shift, err)
            row.update(shift=best[0], err=round(float(best[1]), 3))
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default="S02_SH010")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fmt", default="webm")
    ap.add_argument("--scribe", help="a Scribe word list (json) of the line; default: the synthetic fixture")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scribe = json.loads(Path(a.scribe).read_text(encoding="utf-8")) if a.scribe else None
    spec, scribe = build(a.shot, scribe)
    spec["word_basis"] = "scribe" if a.scribe else "SYNTHETIC Scribe-shaped fixture (no narration exists yet)"
    (out / f"{a.shot}_scribe_{'real' if a.scribe else 'SYNTHETIC'}.json").write_text(json.dumps(scribe, indent=1), encoding="utf-8")
    proj = HF.write_project(spec, out / f"{a.shot}_project")
    png = draw_plate(spec, out / f"{a.shot}_plate.png")
    ov = out / f"{a.shot}_overlay.{a.fmt}"
    import time
    t0 = time.time()
    HF.render_overlay(proj, ov, fmt=a.fmt)
    t_render = time.time() - t0
    comp = out / f"{a.shot}_on_ltx_2k.mp4"
    t0 = time.time()
    HF.composite(a.clip, png, ov, comp, spec)
    t_comp = time.time() - t0
    rep = timing_report(spec, out / f"{a.shot}_iso", a.fmt)
    (out / f"{a.shot}_timing.json").write_text(json.dumps({"basis": spec["word_basis"], "render_s": round(t_render, 1), "composite_s": round(t_comp, 1),
                                                           "items": rep}, indent=1), encoding="utf-8")
    print(json.dumps({"render_s": t_render, "composite_s": t_comp, "timing": rep}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
