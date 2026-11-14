"""A real upscale that adds detail, on CPU, free (the owner via Fable, 2026-11-14; upscale direction II).

``finish/upscale.py`` (ffmpeg Lanczos + cas) only resizes: measured against Gemini's own 2K pictures it keeps 18-25 % of the
detail. The free test of 2026-11-14 (``architecture_2026-11-14/upscale_research``, LPIPS against the real 2K picture) picked
``4xNomos2_realplksr_dysample`` (RealPLKSR, 0.045-0.052 on a clean photo, 0.092-0.143 on a video frame) with
``2xNomosUni_span_multijpg`` (SPAN, 9 s a frame) as the fallback; Real-ESRGAN x2plus (the GC-14 binary's class) lost to a
plain resize. Both models are CC-BY-4.0 by Phips (docs/PROVENANCE.md); the weights are never committed: ``fetch`` downloads
them at a pinned revision into ``$EXPLAINER_MODELS_DIR/<owner>__<name>/`` and checks their sha256.

- ``decide(shot, ctx)``: the U-1..U-8 table, from the script before any picture exists (pure, no image).
- ``run`` tiles the model over the picture (reflected padding); ``to_size`` only ever shrinks the model's output.
- ``qc(original, result, anchor)``: Q1..Q7 (BP-198), every threshold a hypothesis at REVIEW (D-59).
- ``upscale(image, ...)``: RealPLKSR -> QC -> on any miss SPAN -> QC -> on a miss the picture as it is, with the rows for the
  reviewer; results are cached by picture sha256 + model + crop + size and written as they finish (OR-33 style).
- ``turn_pack.find_upscaler`` uses this module when the weights are present and torch + spandrel import, so GC-14's promote
  is no longer NOT_RUN in the cloud; without them it stays NOT_RUN (never a silent resize).

    python -m explainer_engine.finish.superres fetch [realplksr4x span2x]
    python -m explainer_engine.finish.superres plan <production_script.json> [--picture-width 2752]
    python -m explainer_engine.finish.superres run <image> --out <dir> [--size WxH] [--anchor A.png] [--crop x0,y0,x1,y1]
    python -m explainer_engine.finish.superres qc <original> <result> [--anchor A.png]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ConfigError
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
MODELS = {
    "realplksr4x": {"repo": "Phips/4xNomos2_realplksr_dysample", "revision": "893bd79c7eccc29cc04fa0ac4ff08f72585c2605",
                    "file": "4xNomos2_realplksr_dysample.safetensors",
                    "sha256": "371c210e419fb9a4c3f7bf1b9a94dfae0e344232a81147d4c9f9c96b44b5702a", "scale": 4,
                    "license": "CC-BY-4.0", "colour_fix": True},   # its card: "affects / saturates colours" (wavelet fix)
    "span2x": {"repo": "Phips/2xNomosUni_span_multijpg", "revision": "ed6111c4cabdaf42b75e6535600d5370cce9e4e2",
               "file": "2xNomosUni_span_multijpg.safetensors",
               "sha256": "bee2a9c082f2b8f6e7f5db504b36593c24a1a959511f587114c399ca58b9c92c", "scale": 2,
               "license": "CC-BY-4.0", "colour_fix": True},   # measured 2026-11-14 on the rifle frame: mean shift 5.1/255 without it
}
CHAIN = ("realplksr4x", "span2x")
LTX_SIZE = (1280, 704)              # the LTX worker's start picture (training/pods/ltx/modal_ltx_jobs.py)
DELIVERY_W = 2560                   # BP-167
PSNR_MIN = float(SR.T("BP-198", "consistency_psnr_min_db"))
COLOUR_MAX = float(SR.T("BP-198", "colour_shift_max"))
DETAIL_MIN = float(SR.T("BP-198", "detail_gain_min"))
OVERSHARP_MAX = float(SR.T("BP-198", "oversharp_max"))
INVENT_MAX = float(SR.T("BP-198", "lpips_vs_plain_max"))
_LOADED: dict = {}


def _cv2():
    import cv2
    return cv2


def models_dir() -> Path:
    return Path(os.environ.get("EXPLAINER_MODELS_DIR") or ROOT / "tools" / "models")


def model_path(model_id: str) -> Path:
    m = MODELS[model_id]
    return models_dir() / m["repo"].replace("/", "__") / m["file"]


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(model_id: str) -> Path:
    """Download the weights at the pinned revision (free) and check the sha256; a mismatch deletes nothing and raises."""
    p = model_path(model_id)
    if not p.is_file():
        from huggingface_hub import hf_hub_download
        m = MODELS[model_id]
        p.parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(m["repo"], m["file"], revision=m["revision"], local_dir=str(p.parent))
    if _sha256(p) != MODELS[model_id]["sha256"]:
        raise ConfigError(f"{p}: sha256 does not match the pinned {model_id} weights")
    return p


def available(model_id: str = CHAIN[0]) -> bool:
    """torch + spandrel import and the weights are on disk (no download here)."""
    try:
        import spandrel  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        return False
    return model_path(model_id).is_file()


def load(model_id: str, loader=None):
    """The model as ``fn(rgb float32 HxWx3 in 0..1) -> rgb at scale``; ``loader`` (tests) replaces spandrel."""
    if loader is not None:
        return loader(model_id)
    if model_id in _LOADED:
        return _LOADED[model_id]
    try:
        import torch
        from spandrel import ModelLoader
    except ImportError as e:
        raise ConfigError(f"superres needs torch and spandrel ({e}); the row is NOT_RUN, never a plain resize") from e
    p = model_path(model_id)
    if not p.is_file():
        raise ConfigError(f"no weights at {p}: run python -m explainer_engine.finish.superres fetch {model_id}")
    net = ModelLoader(device="cpu").load_from_file(str(p))
    net.eval()
    torch.set_num_threads(max(1, os.cpu_count() or 1))

    def fn(rgb: np.ndarray) -> np.ndarray:
        with torch.inference_mode():
            t = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))[None]
            return net(t)[0].clamp(0, 1).numpy().transpose(1, 2, 0)
    fn.scale = int(net.scale)
    _LOADED[model_id] = fn
    return fn


def run(bgr: np.ndarray, model_id: str, tile: int = 384, pad: int = 24, loader=None) -> np.ndarray:
    """BGR uint8 -> BGR uint8 at the model's scale, in tiles with a reflected border (the seams fall in the padding)."""
    fn = load(model_id, loader)
    s = int(getattr(fn, "scale", MODELS[model_id]["scale"]))
    rgb = bgr[:, :, ::-1].astype(np.float32) / 255.0
    h, w = rgb.shape[:2]
    out = np.zeros((h * s, w * s, 3), np.float32)
    big = np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)), mode="reflect")
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            th, tw = min(tile, h - y), min(tile, w - x)
            o = fn(big[y:y + th + 2 * pad, x:x + tw + 2 * pad])
            out[y * s:(y + th) * s, x * s:(x + tw) * s] = o[pad * s:(pad + th) * s, pad * s:(pad + tw) * s]
    return (out[:, :, ::-1] * 255 + 0.5).clip(0, 255).astype(np.uint8)


def to_size(img: np.ndarray, w: int, h: int) -> np.ndarray:
    """The model's output to the size needed: INTER_AREA, never an enlargement past what the model made."""
    if w > img.shape[1] or h > img.shape[0]:
        raise ConfigError(f"to_size {w}x{h} is larger than the model's {img.shape[1]}x{img.shape[0]}: pick a larger model scale")
    return _cv2().resize(img, (w, h), interpolation=_cv2().INTER_AREA)


def colour_fix(result: np.ndarray, original: np.ndarray, sigma: float = 6.0) -> np.ndarray:
    """The model card's counter for saturated colours (a 'wavelet colour fix'): keep the result's detail (result minus its
    low-pass) on the low-pass colour of a plain resize of the input."""
    cv2 = _cv2()
    H, W = result.shape[:2]
    plain = cv2.resize(original, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    r = result.astype(np.float32)
    s = sigma * W / max(1, original.shape[1])
    out = r - cv2.GaussianBlur(r, (0, 0), s) + cv2.GaussianBlur(plain, (0, 0), s)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def crop_box(img: np.ndarray, box) -> np.ndarray:
    """``box`` = [x0, y0, x1, y1] as shares of the frame."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    return img[int(round(y0 * h)):int(round(y1 * h)), int(round(x0 * w)):int(round(x1 * w))]


# --- QC: Q1..Q7 (BP-198) ----------------------------------------------------------------------------------------------------

def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(((a.astype(np.float32) - b.astype(np.float32)) ** 2).mean())
    return 99.0 if mse < 1e-9 else 10 * math.log10(255 ** 2 / mse)


def _lap(img: np.ndarray) -> float:
    cv2 = _cv2()
    return float(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), cv2.CV_32F).var())


def lpips_fn():
    """LPIPS (AlexNet) as ``fn(a, b)`` on BGR uint8, or None when the package is missing (Q5 is then NOT_RUN)."""
    try:
        import lpips
        import torch
    except ImportError:
        return None
    net = lpips.LPIPS(net="alex", verbose=False)

    def fn(a, b):
        with torch.inference_mode():
            t = [torch.from_numpy(np.ascontiguousarray(x[:, :, ::-1].transpose(2, 0, 1))).float()[None] / 127.5 - 1 for x in (a, b)]
            return float(net(*t))
    return fn


def qc(original: np.ndarray, result: np.ndarray, anchor: np.ndarray | None = None, lp=None, identity=None) -> list[dict]:
    """Original (the input, any size) against the model's result. ``anchor``: the 2K photo of the same frame when there is
    one. ``lp``: an LPIPS function (``lpips_fn()``); ``identity``: ``fn(a, b) -> cosine`` on the face box (Q6, info only)."""
    cv2 = _cv2()
    h, w = original.shape[:2]
    H, W = result.shape[:2]
    back = cv2.resize(result, (w, h), interpolation=cv2.INTER_AREA)
    plain = cv2.resize(original, (W, H), interpolation=cv2.INTER_LANCZOS4)
    rows = []
    p = _psnr(back, original)
    rows.append(G.row("Q1_structure", p >= PSNR_MIN, f"result shrunk back to the input: {p:.1f} dB (at least {PSNR_MIN}, BP-198)",
                      round(p, 2), level=G.REVIEW))
    shift = float(np.abs(back.reshape(-1, 3).mean(0) - original.reshape(-1, 3).mean(0)).max())
    rows.append(G.row("Q2_colour", shift <= COLOUR_MAX, f"largest channel mean shift {shift:.2f}/255 (at most {COLOUR_MAX})",
                      round(shift, 3), level=G.REVIEW))
    gain = _lap(result) / max(_lap(plain), 1e-6)
    rows.append(G.row("Q3_detail_added", gain >= DETAIL_MIN, f"Laplacian variance x{gain:.2f} of a plain resize (at least "
                      f"x{DETAIL_MIN})", round(gain, 3), level=G.REVIEW))
    if anchor is not None:
        a = cv2.resize(anchor, (W, H), interpolation=cv2.INTER_AREA if anchor.shape[1] > W else cv2.INTER_LANCZOS4)
        over = _lap(result) / max(_lap(a), 1e-6)
        rows.append(G.row("Q4_not_oversharp", over <= OVERSHARP_MAX, f"x{over:.2f} the anchor photo's sharpness (at most "
                          f"x{OVERSHARP_MAX})", round(over, 3), level=G.REVIEW))
    else:
        a = None
        rows.append(G.row("Q4_not_oversharp", None, "no anchor photo to compare with"))
    d_plain = None
    if lp is not None:
        d_plain = lp(result, plain)
        rows.append(G.row("Q5_nothing_invented", d_plain <= INVENT_MAX, f"LPIPS to a plain resize {d_plain:.3f} (at most "
                          f"{INVENT_MAX})", round(d_plain, 4), level=G.REVIEW))
    else:
        rows.append(G.row("Q5_nothing_invented", None, "lpips is not installed"))
    if identity is not None:
        rows.append(G.row("Q6_same_face", None, f"face cosine {identity(original, result):.3f} (information only until "
                          "calibrated, BP-133)"))
    else:
        rows.append(G.row("Q6_same_face", None, "no face measurement given"))
    core = [r for r in rows if r["gate"] in ("Q1_structure", "Q2_colour", "Q3_detail_added", "Q5_nothing_invented")]
    missed = [r["gate"] for r in core if r["status"] != G.PASS]
    if missed:
        ok, detail = False, "not every core row passed: " + ", ".join(missed)
    elif a is not None and lp is not None:
        ok = lp(result, a) < lp(plain, a)
        detail = ("Q1, Q2, Q3, Q5 pass and the result is nearer the anchor than a plain resize" if ok
                  else "Q1, Q2, Q3, Q5 pass, but a plain resize is as near the anchor")
    else:
        ok, detail = True, "Q1, Q2, Q3 and Q5 pass"
    rows.append(G.row("Q7_better", ok, detail, level=G.REVIEW))
    return rows


def accepted(rows: list[dict]) -> bool:
    return all(r["status"] == G.PASS for r in rows if r["gate"] in ("Q1_structure", "Q2_colour", "Q3_detail_added",
                                                                     "Q5_nothing_invented", "Q7_better"))


# --- one picture, with the fallback chain and the cache -----------------------------------------------------------------

def cache_key(image_bytes: bytes, model_id: str, crop=None, size=None) -> str:
    return hashlib.sha256(json.dumps({"img": hashlib.sha256(image_bytes).hexdigest(), "model": model_id,
                                      "rev": MODELS[model_id]["revision"], "crop": crop, "size": size,
                                      "colour_fix": bool(MODELS[model_id].get("colour_fix"))},
                                     sort_keys=True).encode()).hexdigest()[:24]


def upscale(bgr: np.ndarray, out_dir: Path, name: str, size=None, crop=None, anchor: np.ndarray | None = None,
            chain=CHAIN, loader=None, lp="auto", identity=None) -> dict:
    """``bgr`` -> (crop) -> model -> ``size`` (default: 2x the input) -> QC; the first model whose QC is accepted wins, else the
    picture as it is (plain resize) with the rows for the reviewer. Every result is written as soon as it exists and the
    report row says which file, model, revision and sha256; a cached result is reused."""
    cv2 = _cv2()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = crop_box(bgr, crop) if crop else bgr
    want = tuple(size) if size else (src.shape[1] * 2, src.shape[0] * 2)
    if lp == "auto":
        lp = lpips_fn()
    ok_png, buf = cv2.imencode(".png", src)
    tries = []
    for mid in chain:
        key = cache_key(buf.tobytes(), mid, crop, list(want))
        dst = out_dir / f"{name}.{mid}.{key}.png"
        t0 = time.time()
        try:
            if dst.is_file():
                res = cv2.imread(str(dst))
                cached = True
            else:
                big = run(src, mid, loader=loader)
                res = to_size(big, *want)
                if MODELS[mid].get("colour_fix"):
                    res = colour_fix(res, src)
                cv2.imwrite(str(dst), res)
                cached = False
        except ConfigError as e:
            tries.append({"model": mid, "status": G.NOT_RUN, "detail": str(e)})
            continue
        rows = qc(src, res, anchor, lp, identity)
        tries.append({"model": mid, "revision": MODELS[mid]["revision"], "file": str(dst), "sha256": _sha256(dst),
                      "seconds": round(time.time() - t0, 1), "cached": cached, "rows": rows, "accepted": accepted(rows)})
        if accepted(rows):
            return {"name": name, "result": str(dst), "model": mid, "status": G.PASS, "tries": tries,
                    "input_sha256": hashlib.sha256(buf.tobytes()).hexdigest(), "size": list(want)}
    plain = out_dir / f"{name}.as_is.png"
    cv2.imwrite(str(plain), cv2.resize(src, want, interpolation=cv2.INTER_LANCZOS4))
    status = G.NOT_RUN if all(t["status"] == G.NOT_RUN for t in tries if "status" in t) and not any("rows" in t for t in tries) \
        else G.REVIEW
    return {"name": name, "result": str(plain), "model": None, "status": status, "tries": tries,
            "input_sha256": hashlib.sha256(buf.tobytes()).hexdigest(), "size": list(want),
            "detail": "no model passed QC (or none could run): the picture as it is, for the reviewer's eye"}


def upscale_file(src: Path, dst: Path, factor: int = 2, loader=None) -> dict:
    """GC-14's promote: ``src`` x ``factor`` -> ``dst``; raises when no model passed QC (the draft then stays a draft)."""
    cv2 = _cv2()
    img = cv2.imread(str(src))
    if img is None:
        raise ConfigError(f"{src} is not a picture")
    r = upscale(img, Path(dst).parent / ".superres", Path(src).stem, size=(img.shape[1] * factor, img.shape[0] * factor),
                loader=loader)
    if r["status"] != G.PASS:
        raise ConfigError(f"superres: {r.get('detail')} ({[t.get('model') for t in r['tries']]})")
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), cv2.imread(r["result"]))
    return r


# --- U-1..U-8: what the script decides before a picture exists ----------------------------------------------------------

def decide(shot: dict, ctx: dict | None = None) -> dict:
    """The upscale decision of one shot's start image (pure). ``ctx``: ``picture_width`` (the anchor photo's real width,
    default 2752), ``delivery_width`` (2560), ``purpose`` (``promote`` for GC-14). Returns rule, action, why and ``delivery``
    (what the finished clip gets: U-8 Lanczos for video, nothing else for the rest)."""
    ctx = ctx or {}
    route = shot.get("route")
    ep = shot.get("edit_plan") or {}
    changed = ep.get("state_changed_since_anchor")
    next_use = ep.get("next_use")
    delivery = "lanczos" if route == "video" else "none"

    def out(rule, action, why, **kw):
        return {"shot_id": shot.get("shot_id"), "rule": rule, "action": action, "why": why, "delivery": delivery, **kw}
    if ctx.get("purpose") == "promote":
        return out("U-6", "model_x2", "a chat picture at its native size becomes the working master (GC-14)")
    if route == "map_action" or shot.get("kind") in ("map", "chart", "overlay", "graphic"):
        return out("U-7", "none", "maps, charts and overlays are drawn at the size they are shown")
    unknown = changed is None
    if route == "video":
        cf = ep.get("continue_frame")
        if ep.get("continuity_mode") == "continuation" and cf is not None:
            crop = cf.get("crop")
            if crop:
                if changed is False:
                    return out("U-3", "anchor_photo_crop", "a punch-in with nothing changed since the anchor: crop the 2K anchor "
                               "photo, not the softer frame", crop=crop)
                return out("U-3", "model_x4_crop", "a punch-in after the state changed: frame -> model x4 -> crop -> "
                           f"{LTX_SIZE[0]}x{LTX_SIZE[1]}" + (" (state_changed_since_anchor missing: assumed changed)"
                                                             if unknown else ""), crop=crop, review=unknown)
            return out("U-2", "as_is", "a continuation at the same framing takes the chosen frame as it is (a same-size model "
                       "pass waits for the paid test, upscale direction III)")
        return out("U-1", "none", f"starts from the anchor photo; the worker shrinks it to {LTX_SIZE[0]}x{LTX_SIZE[1]}")
    if next_use == "still" or shot.get("start_from") == "video_frame":
        if changed is False:
            return out("U-4", "anchor_photo", "a video frame becomes a still with nothing changed: use the anchor photo")
        return out("U-4", "model_x2", "a video frame becomes a still after the state changed: model x2 to the delivery size"
                   + (" (state_changed_since_anchor missing: assumed changed)" if unknown else ""), review=unknown)
    if route == "still_25d":
        pw = float(ctx.get("picture_width", 2752))
        dw = float(ctx.get("delivery_width", DELIVERY_W))
        zoom = float(shot.get("max_zoom") or (shot.get("motion_profile") or {}).get("zoom_max") or 1.1)
        crop = shot.get("crop") or [0, 0, 1, 1]
        need = dw * zoom / max(1e-6, crop[2] - crop[0])
        if need > pw:
            return out("U-5", "model_x2", f"the shot needs {need:.0f} px of picture width (delivery {dw:.0f} x zoom {zoom} / "
                       f"crop), the picture has {pw:.0f}")
        return out("U-5", "none", f"the picture's {pw:.0f} px cover the {need:.0f} px the shot needs")
    return out("U-1", "none", "no rule asks for an upscale")


def plan(script: dict, ctx: dict | None = None) -> list[dict]:
    return [decide(s, ctx) for s in script.get("shots", [])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.finish.superres")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("models", nargs="*", default=list(CHAIN))
    pl = sub.add_parser("plan")
    pl.add_argument("script")
    pl.add_argument("--picture-width", type=int, default=2752)
    r = sub.add_parser("run")
    r.add_argument("image")
    r.add_argument("--out", required=True)
    r.add_argument("--size")
    r.add_argument("--anchor")
    r.add_argument("--crop")
    q = sub.add_parser("qc")
    q.add_argument("original")
    q.add_argument("result")
    q.add_argument("--anchor")
    a = ap.parse_args(argv)
    cv2 = _cv2()
    if a.cmd == "fetch":
        for m in a.models:
            print(m, fetch(m))
        return 0
    if a.cmd == "plan":
        rows = plan(json.loads(Path(a.script).read_text(encoding="utf-8")), {"picture_width": a.picture_width})
        for x in rows:
            print(f"{x['shot_id']:12s} {x['rule']:4s} {x['action']:18s} {x['why']}")
        return 0
    if a.cmd == "run":
        img = cv2.imread(a.image)
        size = tuple(int(v) for v in a.size.split("x")) if a.size else None
        crop = [float(v) for v in a.crop.split(",")] if a.crop else None
        anchor = cv2.imread(a.anchor) if a.anchor else None
        res = upscale(img, Path(a.out), Path(a.image).stem, size=size, crop=crop, anchor=anchor)
        rep = Path(a.out) / "superres_report.json"
        old = json.loads(rep.read_text()) if rep.is_file() else []
        rep.write_text(json.dumps(old + [res], indent=1))
        print(json.dumps({k: res[k] for k in ("name", "result", "model", "status")}))
        return 0 if res["status"] == G.PASS else 1
    rows = qc(cv2.imread(a.original), cv2.imread(a.result), cv2.imread(a.anchor) if a.anchor else None, lpips_fn())
    for x in rows:
        print(f"{x['gate']:22s} {x['status']:7s} {x['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
