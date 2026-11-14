"""Picture understanding for the Scene Director (roadmap 2026-11-14 B.2 ``scene_layers/1``; phase P1, prototype round 2).

One picture is understood ONCE and the result is cached next to it (``<picture>.layers/``); every render reads these files:

- ``depth.png``: 16-bit relative disparity at the picture's full size (near = 65535), never blurred. Three free CPU models are
  compared (roadmap D.1): Depth Anything V2 Small (ONNX, the repo's model, here at 1848x1036 instead of 924x518 and without the
  576x324 / 3 px blur of ``production/depth.py``), MoGe-2 ViT-L (depth + normals + field of view) and Depth Anything 3 Mono-Large.
- ``normals.png`` (MoGe-2 only, optional): surface direction for local light.
- ``masks/<id>.png``: named object masks from the director's points (``seen.objects``): SAM 2.1 Hiera-L picks the instance,
  BiRefNet sharpens fine edges (wire, rifles, spade handles) inside a band round SAM's mask when the object asks for it.
- ``lights/<id>.png``: light-source masks (flames, candles) from the director's point and radius: the warm, bright pixels inside
  the disc (a flame has no clean outline for SAM; the colour rule inside the director's disc is exact and free).
- ``plate.png``: the clean plate behind every object (LaMa big-lama, ONNX, 512 px tiles round each hole, only the hole replaced).
- ``manifest.json`` (``scene_layers/1``): picture sha256, model names, files, parameters, times; it is the cache key.

Heavy models are optional imports (torch, transformers, moge, depth_anything_3, onnxruntime); the model folder is
``$EXPLAINER_MODELS_DIR`` (default ``tools/models``, gitignored) with one sub-folder per Hugging Face repo (``owner__name``).
Every model function takes an injectable runner so the tests work on synthetic pictures without any model.

Prototype only (P1): nothing in ``episode/run.py`` calls this module yet (P2 wires the ``direction`` stage).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_json_atomic

SCHEMA = "scene_layers/1"
ROOT = Path(__file__).resolve().parents[2]
DEPTH_MODELS = ("da_v2_small", "moge2_vitl", "da3_mono_large")
REPOS = {
    "da_v2_small": "onnx-community/depth-anything-v2-small",
    "moge2_vitl": "Ruicheng/moge-2-vitl-normal",
    "da3_mono_large": "depth-anything/DA3MONO-LARGE",
    "sam21": "facebook/sam2.1-hiera-large",
    "birefnet": "ZhengPeng7/BiRefNet",
    "lama": "Carve/LaMa-ONNX",
}
LICENCES = {"da_v2_small": "Apache-2.0", "moge2_vitl": "MIT (model card)", "da3_mono_large": "Apache-2.0",
            "sam21": "Apache-2.0", "birefnet": "MIT", "lama": "Apache-2.0 (model card of the ONNX copy)"}
DA2_INPUT = (1848, 1036)     # width, height: multiples of 14, 16:9; 4x the pixels of production/depth.INPUT_SIZE
MOGE_INPUT = (1376, 768)
DA3_RES = 1008
LAMA_SIZE = 512
HOLE_GROW = 0.004            # a hole is the object's mask grown by this share of the width (soft edges and halos go too)
FINE_BAND = 0.006            # BiRefNet refines only inside this band (share of the width) round SAM's edge
_cache: dict = {}


def models_dir() -> Path:
    return Path(os.environ.get("EXPLAINER_MODELS_DIR") or ROOT / "tools" / "models")


def repo_dir(key: str) -> Path:
    return models_dir() / REPOS[key].replace("/", "__")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def normalise(d: np.ndarray, valid: np.ndarray | None = None) -> np.ndarray:
    """A disparity-like map to 0..1 (1 = nearest) by its 1st and 99th percentile; invalid pixels (sky for MoGe) are 0."""
    d = np.asarray(d, dtype=np.float32)
    v = d[valid] if valid is not None and valid.any() else d.ravel()
    lo, hi = np.percentile(v, 1.0), np.percentile(v, 99.0)
    out = np.clip((d - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)
    if valid is not None:
        out = np.where(valid, out, 0.0)
    return out.astype(np.float32)


def _resize(a: np.ndarray, size: tuple[int, int], interp: str = "cubic") -> np.ndarray:
    import cv2
    flag = {"cubic": cv2.INTER_CUBIC, "linear": cv2.INTER_LINEAR, "area": cv2.INTER_AREA, "nearest": cv2.INTER_NEAREST}[interp]
    return cv2.resize(np.asarray(a, dtype=np.float32), size, interpolation=flag)


# --- depth: three models, one output form ----------------------------------------------------------------------------------

def _torch():
    import torch
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    return torch


def run_da_v2_small(rgb: np.ndarray) -> dict:
    import onnxruntime as ort
    from PIL import Image
    s = _cache.get("da2") or ort.InferenceSession(str(repo_dir("da_v2_small") / "onnx" / "model.onnx"),
                                                  providers=["CPUExecutionProvider"])
    _cache["da2"] = s
    mean, std = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)
    x = np.asarray(Image.fromarray(rgb).resize(DA2_INPUT, Image.BICUBIC), dtype=np.float32) / 255.0
    x = ((x - mean) / std).transpose(2, 0, 1)[None].astype(np.float32)
    d = np.asarray(s.run(None, {s.get_inputs()[0].name: x})[0], dtype=np.float32).reshape(DA2_INPUT[1], DA2_INPUT[0])
    return {"disparity": d}


def run_moge2(rgb: np.ndarray) -> dict:
    torch = _torch()
    from moge.model.v2 import MoGeModel
    m = _cache.get("moge") or MoGeModel.from_pretrained(str(repo_dir("moge2_vitl") / "model.pt")).eval()
    _cache["moge"] = m
    x = torch.tensor(_resize(rgb, MOGE_INPUT, "area") / 255.0, dtype=torch.float32).permute(2, 0, 1)
    with torch.inference_mode():
        o = m.infer(x, use_fp16=False)
    depth = o["depth"].numpy()
    valid = o["mask"].numpy().astype(bool) & np.isfinite(depth) & (depth > 0)
    disp = np.where(valid, 1.0 / np.where(valid, depth, 1.0), 0.0)
    k = o["intrinsics"].numpy()
    fov_x = float(2 * np.degrees(np.arctan(0.5 / max(1e-6, k[0, 0]))))
    return {"disparity": disp, "valid": valid, "normals": o["normal"].numpy(), "fov_x_deg": fov_x}


def run_da3_mono(rgb: np.ndarray) -> dict:
    """Depth Anything 3 Mono-Large: its output is a relative DEPTH (larger = farther, checked on the six Truce photos:
    the near foreground has the smallest values), so the disparity is its inverse."""
    torch = _torch()
    import sys
    import types
    if "depth_anything_3.utils.export" not in sys.modules:   # the mono path needs none of the 3D export extras
        import depth_anything_3.utils  # noqa: F401
        st = types.ModuleType("depth_anything_3.utils.export")
        st.export = lambda *a, **k: None
        pa = types.ModuleType("depth_anything_3.utils.pose_align")
        pa.align_poses_umeyama = lambda *a, **k: None
        sys.modules["depth_anything_3.utils.export"], sys.modules["depth_anything_3.utils.pose_align"] = st, pa
    from depth_anything_3.api import DepthAnything3
    m = _cache.get("da3") or DepthAnything3.from_pretrained(str(repo_dir("da3_mono_large"))).eval()
    _cache["da3"] = m
    with torch.inference_mode():
        pred = m.inference([rgb], process_res=DA3_RES)
    depth = np.asarray(pred.depth[0], dtype=np.float32)
    return {"disparity": 1.0 / np.maximum(depth, 1e-4)}


DEPTH_RUNNERS = {"da_v2_small": run_da_v2_small, "moge2_vitl": run_moge2, "da3_mono_large": run_da3_mono}


def estimate_depth(rgb: np.ndarray, model: str, runner=None) -> dict:
    """One picture -> {"depth": 0..1 float32 at the picture's size (near = 1), "seconds", optional "normals", "fov_x_deg"}."""
    if model not in DEPTH_MODELS:
        raise ValueError(f"unknown depth model {model!r} (known: {', '.join(DEPTH_MODELS)})")
    h, w = rgb.shape[:2]
    t0 = time.time()
    out = (runner or DEPTH_RUNNERS[model])(rgb)
    secs = time.time() - t0
    valid = out.get("valid")
    d = normalise(out["disparity"], valid)
    res = {"depth": np.clip(_resize(d, (w, h), "cubic"), 0.0, 1.0), "seconds": round(secs, 2),
           "model_input": list(np.asarray(out["disparity"]).shape[::-1])}
    if out.get("normals") is not None:
        n = np.stack([_resize(out["normals"][..., i], (w, h), "linear") for i in range(3)], axis=-1)
        res["normals"] = n / np.maximum(1e-6, np.linalg.norm(n, axis=-1, keepdims=True))
    if out.get("fov_x_deg") is not None:
        res["fov_x_deg"] = round(out["fov_x_deg"], 2)
    return res


def depth_checks(depth: np.ndarray, checks: list[dict]) -> dict:
    """The director's near/far pairs (``seen.depth_checks``: ``{"near": [x, y], "far": [x, y], "why": ...}``): how many the map
    orders right (median of a small patch at each point)."""
    h, w = depth.shape
    r = max(2, int(0.006 * w))
    ok, rows = 0, []
    for c in checks:
        vals = []
        for key in ("near", "far"):
            x, y = int(c[key][0] * w), int(c[key][1] * h)
            vals.append(float(np.median(depth[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1])))
        good = vals[0] > vals[1]
        ok += good
        rows.append({"near": c["near"], "far": c["far"], "values": [round(v, 3) for v in vals], "right": bool(good)})
    return {"right": ok, "of": len(checks), "rows": rows}


def edge_alignment(depth: np.ndarray, masks: dict[str, np.ndarray]) -> float | None:
    """How sharply the depth changes on the objects' outlines against everywhere else (mean gradient on the outline / mean
    gradient overall): a map whose steps sit on the real object edges scores high, a blurred or misplaced one low."""
    import cv2
    if not masks:
        return None
    g = np.hypot(cv2.Sobel(depth, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(depth, cv2.CV_32F, 0, 1, ksize=3))
    edge = np.zeros(depth.shape, bool)
    k = np.ones((3, 3), np.uint8)
    for m in masks.values():
        b = (m > 0.5).astype(np.uint8)
        edge |= (cv2.dilate(b, k, iterations=2) - cv2.erode(b, k, iterations=2)).astype(bool)
    if not edge.any():
        return None
    return round(float(g[edge].mean() / max(1e-9, g.mean())), 3)


# --- masks: SAM 2.1 from the director's points, BiRefNet on fine edges -----------------------------------------------------

def run_sam(rgb: np.ndarray, prompts: list[dict]) -> list[np.ndarray]:
    """SAM 2.1 Hiera-L (transformers): one mask per prompt (positive ``points`` and negative ``neg``, picture pixels); the image
    is embedded once. The best of SAM's three proposals by its own IoU estimate is kept."""
    torch = _torch()
    from PIL import Image
    from transformers import Sam2Model, Sam2Processor
    if "sam" not in _cache:
        _cache["sam"] = (Sam2Processor.from_pretrained(str(repo_dir("sam21"))),
                         Sam2Model.from_pretrained(str(repo_dir("sam21"))).eval())
    proc, sam = _cache["sam"]
    im = Image.fromarray(rgb)
    base = proc(images=im, return_tensors="pt")
    with torch.inference_mode():
        emb = sam.get_image_embeddings(base["pixel_values"])
    out = []
    for pr in prompts:
        pts = [list(map(float, p)) for p in pr["points"]] + [list(map(float, p)) for p in pr.get("neg", [])]
        labels = [1] * len(pr["points"]) + [0] * len(pr.get("neg", []))
        inp = proc(images=im, input_points=[[pts]], input_labels=[[labels]], return_tensors="pt")
        with torch.inference_mode():
            o = sam(image_embeddings=emb, input_points=inp["input_points"], input_labels=inp["input_labels"],
                    multimask_output=True)
        masks = proc.post_process_masks(o.pred_masks, inp["original_sizes"])[0][0]   # (3, H, W)
        scores = o.iou_scores[0, 0].numpy()
        pick = int(np.argmax(scores)) if pr.get("pick") is None else int(pr["pick"])
        out.append({"mask": masks[pick].numpy().astype(np.float32), "score": float(scores[pick])})
    return out


def run_birefnet(crop_rgb: np.ndarray) -> np.ndarray:
    """BiRefNet (general): a crop -> its foreground alpha 0..1 at the crop's size (1024 px input)."""
    torch = _torch()
    from transformers import AutoModelForImageSegmentation
    if "biref" not in _cache:
        _cache["biref"] = AutoModelForImageSegmentation.from_pretrained(str(repo_dir("birefnet")),
                                                                        trust_remote_code=True).eval().float()
    m = _cache["biref"]
    h, w = crop_rgb.shape[:2]
    x = (_resize(crop_rgb, (1024, 1024), "area") / 255.0 - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = torch.tensor(x, dtype=torch.float32).permute(2, 0, 1)[None]
    with torch.inference_mode():
        p = m(x)[-1].sigmoid()[0, 0].numpy()
    return np.clip(_resize(p, (w, h), "cubic"), 0, 1)


def refine_fine_edges(rgb: np.ndarray, coarse: np.ndarray, runner=None) -> np.ndarray:
    """SAM's mask with its outline re-drawn by BiRefNet: inside a thin band round SAM's edge the alpha comes from BiRefNet
    (wire barbs, rifle tips, spade handles); deep inside stays 1, far outside stays 0. SAM decides WHICH object, BiRefNet
    only WHERE its edge is, so BiRefNet never adds a second object."""
    import cv2
    h, w = coarse.shape
    b = (coarse > 0.5).astype(np.uint8)
    if not b.any():
        return coarse.astype(np.float32)
    band = max(2, int(FINE_BAND * w))
    ys, xs = np.nonzero(b)
    pad = 4 * band
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
    alpha = (runner or run_birefnet)(rgb[y0:y1, x0:x1])
    k = np.ones((3, 3), np.uint8)
    inner = cv2.erode(b, k, iterations=band)
    outer = cv2.dilate(b, k, iterations=band)
    out = b.astype(np.float32)
    sub = out[y0:y1, x0:x1]
    ring = (outer[y0:y1, x0:x1] > 0) & (inner[y0:y1, x0:x1] == 0)
    sub[ring] = alpha[ring]
    out[y0:y1, x0:x1] = sub
    return np.clip(out, 0, 1).astype(np.float32)


def clean_mask(mask: np.ndarray, points_px: list, keep_share: float = 0.05) -> np.ndarray:
    """SAM's stray islands out: keep the connected parts that hold a positive point or are at least ``keep_share`` of the
    largest part; holes smaller than 0.2 % of the object (or 25 px) are filled. The soft edge (BiRefNet) is kept on the parts kept."""
    import cv2
    b = (mask > 0.5).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    if n <= 2:
        keep = b
    else:
        areas = stats[1:, cv2.CC_STAT_AREA]
        big = areas.max()
        hit = {int(lab[int(min(max(y, 0), b.shape[0] - 1)), int(min(max(x, 0), b.shape[1] - 1))]) for x, y in points_px}
        ok = [i for i in range(1, n) if i in hit or stats[i, cv2.CC_STAT_AREA] >= keep_share * big]
        keep = np.isin(lab, ok).astype(np.uint8)
    inv = (1 - keep).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    small = [i for i in range(1, n2) if st2[i, cv2.CC_STAT_AREA] < max(25, 0.002 * keep.sum())
             and st2[i, cv2.CC_STAT_LEFT] > 0 and st2[i, cv2.CC_STAT_TOP] > 0]
    keep = np.maximum(keep, np.isin(lab2, small).astype(np.uint8))
    grown = cv2.dilate(keep, np.ones((3, 3), np.uint8), iterations=2)
    return np.where(grown > 0, np.maximum(mask, keep.astype(np.float32)) * grown, 0.0).astype(np.float32)


def light_mask(rgb: np.ndarray, point, radius: float, kind: str = "fire") -> np.ndarray:
    """A light source's mask: inside the director's disc (centre ``point``, ``radius`` as a share of the width) the warm,
    bright pixels (orange to yellow, a flame's core), grown and softened; the disc itself if no such pixel exists."""
    import cv2
    h, w = rgb.shape[:2]
    cx, cy, r = point[0] * w, point[1] * h, radius * w
    yy, xx = np.mgrid[0:h, 0:w]
    disc = ((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    warm = ((hsv[..., 0] <= 32) | (hsv[..., 0] >= 170)) & (hsv[..., 2] >= (200 if kind != "glow" else 150)) & \
        (hsv[..., 1] >= 40)
    core = disc & warm
    if core.sum() < 6:
        core = disc
    m = cv2.dilate(core.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(1, int(0.002 * w)))
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(1.0, 0.0015 * w))


# --- the clean plate: LaMa in 512 px tiles round each hole -------------------------------------------------------------------

def run_lama(img512: np.ndarray, mask512: np.ndarray) -> np.ndarray:
    import onnxruntime as ort
    s = _cache.get("lama") or ort.InferenceSession(str(repo_dir("lama") / "lama_fp32.onnx"),
                                                   providers=["CPUExecutionProvider"])
    _cache["lama"] = s
    x = img512.astype(np.float32).transpose(2, 0, 1)[None] / 255.0
    m = (mask512 > 0.5).astype(np.float32)[None, None]
    o = s.run(None, {"image": x, "mask": m})[0][0].transpose(1, 2, 0)
    return np.clip(o, 0, 255).astype(np.uint8)


def hole_of(masks: list[np.ndarray], w: int) -> np.ndarray:
    import cv2
    if not masks:
        return None
    m = np.max(np.stack([(x > 0.1).astype(np.uint8) for x in masks]), axis=0)
    grow = max(1, int(HOLE_GROW * w))
    return cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=grow)


def clean_plate(rgb: np.ndarray, hole: np.ndarray, runner=None, context: float = 1.8) -> tuple[np.ndarray, list[dict]]:
    """Fill ``hole`` (uint8 0/1, picture size) with LaMa: each connected hole (close ones merged) gets a square crop with
    ``context`` times its size round it, resized to 512, filled, resized back; only hole pixels are replaced (a soft 2 px seam).
    Returns the plate and one row per tile (box, scale) for the manifest."""
    import cv2
    run = runner or run_lama
    h, w = hole.shape
    plate = rgb.copy()
    if hole is None or not hole.any():
        return plate, []
    merged = cv2.dilate(hole, np.ones((3, 3), np.uint8), iterations=max(1, int(0.01 * w)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(merged, connectivity=8)
    tiles = []
    for i in sorted(range(1, n), key=lambda j: -stats[j, cv2.CC_STAT_AREA]):
        x, y, bw, bh = stats[i, :4]
        side = int(min(max(bw, bh) * context, min(h, w)))
        side = max(side, min(LAMA_SIZE, min(h, w)))
        cx, cy = x + bw / 2, y + bh / 2
        x0 = int(np.clip(cx - side / 2, 0, w - side))
        y0 = int(np.clip(cy - side / 2, 0, h - side))
        crop, hcrop = plate[y0:y0 + side, x0:x0 + side], (hole[y0:y0 + side, x0:x0 + side] * (lab[y0:y0 + side, x0:x0 + side] == i))
        if not hcrop.any():
            continue
        im512 = cv2.resize(crop, (LAMA_SIZE, LAMA_SIZE), interpolation=cv2.INTER_AREA)
        mk512 = cv2.resize(hcrop.astype(np.float32), (LAMA_SIZE, LAMA_SIZE), interpolation=cv2.INTER_LINEAR) > 0.01
        fill = cv2.resize(run(im512, mk512.astype(np.uint8)), (side, side), interpolation=cv2.INTER_CUBIC)
        a = cv2.GaussianBlur(hcrop.astype(np.float32), (0, 0), 2.0)
        a = np.maximum(a, hcrop.astype(np.float32))[..., None]
        plate[y0:y0 + side, x0:x0 + side] = (crop * (1 - a) + fill * a + 0.5).astype(np.uint8)
        tiles.append({"box": [int(x0), int(y0), int(side), int(side)], "scale": round(side / LAMA_SIZE, 3)})
    return plate, tiles


# --- the whole step ---------------------------------------------------------------------------------------------------------

def _save_u16(path: Path, a: np.ndarray) -> None:
    import cv2
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), (np.clip(a, 0, 1) * 65535 + 0.5).astype(np.uint16))


def _save_u8(path: Path, a: np.ndarray) -> None:
    import cv2
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def load_u16(path: Path) -> np.ndarray:
    import cv2
    return cv2.imread(str(path), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0


def load_u8(path: Path) -> np.ndarray:
    import cv2
    return cv2.imread(str(path), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0


def layers_dir(picture: Path) -> Path:
    picture = Path(picture)
    return picture.with_name(picture.stem + ".layers")


def understand(picture: Path, seen: dict, depth_model: str = "da_v2_small", out_dir: Path | None = None,
               runners: dict | None = None, force: bool = False) -> dict:
    """Make (or reuse) the ``scene_layers/1`` folder of one picture from the director's ``seen`` block:
    ``objects`` = ``[{"id", "points": [[x, y], ...] (0..1), "neg": [...], "fine_edges": bool}]``,
    ``lights`` = ``[{"id", "point": [x, y], "radius": share of width, "kind": "fire"|"candle"|"glow"|"sun"}]``.
    The manifest's key is the picture's sha256 + the model + the prompts; the same key reuses the cached files."""
    import cv2
    from PIL import Image
    runners = runners or {}
    picture = Path(picture)
    out = Path(out_dir) if out_dir else layers_dir(picture)
    rgb = np.asarray(Image.open(picture).convert("RGB"))
    h, w = rgb.shape[:2]
    key_src = json.dumps({"sha": sha256_file(picture), "depth": depth_model, "objects": seen.get("objects", []),
                          "lights": seen.get("lights", []), "plate": "lama/1"}, sort_keys=True)
    key = hashlib.sha256(key_src.encode()).hexdigest()
    man_path = out / "manifest.json"
    if man_path.exists() and not force:
        man = json.loads(man_path.read_text())
        if man.get("key") == key:
            return man
    out.mkdir(parents=True, exist_ok=True)
    times = {}
    d = estimate_depth(rgb, depth_model, runners.get(depth_model))
    _save_u16(out / "depth.png", d["depth"])
    times["depth_s"] = d["seconds"]
    if "normals" in d:
        cv2.imwrite(str(out / "normals.png"), ((d["normals"] * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)[..., ::-1])
    objects = seen.get("objects", [])
    masks: dict[str, np.ndarray] = {}
    obj_rows = []
    if objects:
        t0 = time.time()
        prompts = [{"points": [[p[0] * w, p[1] * h] for p in o["points"]],
                    "neg": [[p[0] * w, p[1] * h] for p in o.get("neg", [])], "pick": o.get("pick")} for o in objects]
        got = (runners.get("sam") or run_sam)(rgb, prompts)
        times["sam_s"] = round(time.time() - t0, 2)
        t0 = time.time()
        light_by_id = {li["id"]: li for li in seen.get("lights", [])}
        for o, g, pr in zip(objects, got, prompts):
            m = clean_mask(g["mask"], pr["points"])
            if o.get("fine_edges"):
                m = refine_fine_edges(rgb, m, runners.get("birefnet"))
            for lid in o.get("with_lights", []):   # a flame belongs to its brazier: it moves with it and leaves no copy
                li = light_by_id[lid]
                m = np.maximum(m, light_mask(rgb, li["point"], float(li.get("radius", 0.02)), li.get("kind", "fire")))
            masks[o["id"]] = m
            _save_u8(out / "masks" / f"{o['id']}.png", m)
            area = float((m > 0.5).mean())
            obj_rows.append({"id": o["id"], "file": f"masks/{o['id']}.png", "sam_score": round(g["score"], 3),
                             "fine_edges": bool(o.get("fine_edges")), "area_share": round(area, 4),
                             "depth_median": round(float(np.median(d["depth"][m > 0.5])) if area > 0 else 0.0, 4)})
        times["birefnet_s"] = round(time.time() - t0, 2)
    light_rows = []
    for li in seen.get("lights", []):
        if li.get("kind") == "sun":
            light_rows.append({"id": li["id"], "kind": "sun", "point": li["point"]})
            continue
        m = light_mask(rgb, li["point"], float(li.get("radius", 0.02)), li.get("kind", "fire"))
        _save_u8(out / "lights" / f"{li['id']}.png", m)
        light_rows.append({"id": li["id"], "kind": li.get("kind", "fire"), "point": li["point"],
                           "radius": li.get("radius", 0.02), "file": f"lights/{li['id']}.png",
                           "area_share": round(float((m > 0.5).mean()), 5)})
    t0 = time.time()
    hole = hole_of([masks[o["id"]] for o in objects if o.get("layer", True)], w)
    plate, tiles = clean_plate(rgb, hole, runners.get("lama")) if hole is not None else (rgb.copy(), [])
    cv2.imwrite(str(out / "plate.png"), plate[..., ::-1])
    if hole is not None:
        _save_u8(out / "hole.png", hole.astype(np.float32))
    times["lama_s"] = round(time.time() - t0, 2)
    man = {"schema": SCHEMA, "key": key, "picture": picture.name, "picture_sha256": sha256_file(picture),
           "size": [w, h], "depth": {"model": depth_model, "repo": REPOS[depth_model], "licence": LICENCES[depth_model],
                                     "file": "depth.png", "bits": 16, "blur_px": 0,
                                     "model_input": d["model_input"], "fov_x_deg": d.get("fov_x_deg")},
           "normals": "normals.png" if "normals" in d else None,
           "masks": {"model": REPOS["sam21"], "refine": REPOS["birefnet"], "objects": obj_rows},
           "lights": light_rows,
           "plate": {"model": REPOS["lama"], "file": "plate.png", "hole": "hole.png" if hole is not None else None,
                     "tiles": tiles, "hole_share": round(float(hole.mean()), 4) if hole is not None else 0.0},
           "seconds": times, "made": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json_atomic(man_path, man)
    return man


def load(layers: Path) -> dict:
    """A ``scene_layers/1`` folder -> arrays: depth, plate (RGB), hole, masks {id: 0..1}, lights {id: 0..1}, manifest."""
    import cv2
    layers = Path(layers)
    man = json.loads((layers / "manifest.json").read_text())
    if man.get("schema") != SCHEMA:
        raise ValueError(f"{layers}: not a {SCHEMA} folder")
    out = {"manifest": man, "depth": load_u16(layers / "depth.png"),
           "plate": cv2.imread(str(layers / "plate.png"))[..., ::-1].copy(),
           "hole": load_u8(layers / "hole.png") if man["plate"].get("hole") else None,
           "masks": {o["id"]: load_u8(layers / o["file"]) for o in man["masks"]["objects"]},
           "lights": {li["id"]: load_u8(layers / li["file"]) for li in man["lights"] if li.get("file")}}
    if man.get("normals"):
        n = cv2.imread(str(layers / man["normals"]))[..., ::-1].astype(np.float32) / 255.0 * 2 - 1
        out["normals"] = n
    return out
