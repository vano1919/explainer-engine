"""Cut-outs of the scene assets for the J5 route (D-116, guide step 2.1 item 2; rules SA-04 in docs/SCENE_ASSETS.md).

    python -m explainer_engine.edit.cutout finish --image hero.png --mask mask.png --out hero.cut.png [--report r.json]
    python -m explainer_engine.edit.cutout check cut.png [cut2.png ...]
    python -m explainer_engine.edit.cutout birefnet --image hero.png --out mask.png      # needs torch + transformers (a pod)

A Qwen hero sheet (flat-lit, plain neutral background) becomes a card for ``blender/assemble_25d.py`` in three steps:

1. **mask**: BiRefNet (``ZhengPeng7/BiRefNet``, MIT, pinned in ``config/cloud_pins.json`` ``models.cutout_birefnet``) predicts the
   foreground matte. It is the model the 2026-10-25 composition test used (HF ``film_1min_2026-10-24/comp_test/``); it runs where
   torch runs (the asset pod), so this module only loads it lazily. Any other matte (a hand mask, an RGBA file) is accepted.
2. **finish** (here, numpy + Pillow, free): a hard matte is feathered to a soft edge of ``FEATHER_PX`` = 2 pixels (a Gaussian of
   sigma ``FEATHER_PX / 2``; a BiRefNet matte is already that soft and is kept, because a second blur loses hair strands), and the colour of every edge pixel is replaced by the colour of the opaque figure next to it
   (``defringe``: the nearest opaque pixel, so an ink outline lends its own colour), so the sheet's grey background does not ride along as a light rim (the halo of a straight alpha cut).
3. **check** (``check``): AC-15 of the asset library (the figure alone, not cut by the edge, no ground patch) and SA-04's halo
   score (``halo_score``): how much lighter or darker the semi-transparent rim is than the nearest opaque pixel, as a
   share of full scale. Above ``HALO_REVIEW`` it is a REVIEW: an engineering default measured on the 10-25 cut-outs, never a FAIL.

No model, no network, no money in ``finish`` and ``check``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from explainer_engine.compose.library import check_cutout

FEATHER_PX = 2            # guide step 2.1: "alpha PNG, 2 px feather, no halo"
RIM = (0.02, 0.98)        # alpha inside this range is the rim
INNER_PX = 4              # the rim is compared with the nearest core pixel up to INNER_PX + 4 pixels away
HALO_REVIEW = 0.06        # SA-04: a rim this much lighter/darker than the figure next to it (share of 255) is a REVIEW
BIREFNET_PIN = "cutout_birefnet"


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _sep(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    """``a`` filtered by the 1-D kernel ``k`` along both axes, edges extended."""
    r = len(k) // 2
    p = np.pad(a, r, mode="edge")
    rows = sum(k[i] * p[:, i:i + a.shape[1]] for i in range(len(k)))
    return sum(k[i] * rows[i:i + a.shape[0], :] for i in range(len(k)))


def _blur(a: np.ndarray, sigma: float) -> np.ndarray:
    r = max(1, int(round(3 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return _sep(a.astype(np.float64), k / k.sum())


def load_mask(path_or_image) -> np.ndarray:
    """A matte as floats 0..1: the alpha of an RGBA picture, else its grey level."""
    im = path_or_image if isinstance(path_or_image, Image.Image) else Image.open(path_or_image)
    if im.mode in ("RGBA", "LA"):
        a = np.asarray(im.getchannel("A"), dtype=np.float64)
    else:
        a = np.asarray(im.convert("L"), dtype=np.float64)
    return a / 255.0


def edge_width(mask: np.ndarray) -> float:
    """The mean width of the matte's soft edge in pixels: rim pixels (alpha in ``RIM``) per pixel of the solid figure's outline.
    A hard (binary) cut is about 0-1 px, a BiRefNet matte usually 2 px or more."""
    solid = mask >= RIM[1]
    rim = (mask > RIM[0]) & (mask < RIM[1])
    p = np.pad(solid, 1)
    inner = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    outline = solid & ~inner
    return float(rim.sum() / max(int(outline.sum()), 1))


def feather(mask: np.ndarray, *, px: int = FEATHER_PX) -> np.ndarray:
    """A soft edge of about ``px`` pixels: a matte whose edge is already that soft (BiRefNet) is kept as it is (blurring it again
    loses hair strands, measured on the 10-25 cut-outs); a harder one gets a Gaussian of sigma ``px / 2``, nothing eroded."""
    m = np.clip(mask, 0.0, 1.0)
    if not px or edge_width(m) >= px:
        return m
    return np.clip(_blur(m, px / 2.0), 0.0, 1.0)


def grow(rgb: np.ndarray, known: np.ndarray, *, steps: int = 64) -> np.ndarray:
    """Every pixel's colour taken from the NEAREST ``known`` pixel: the known colours grow outwards one ring per step (the mean
    of the known 8-neighbours). An ink outline therefore lends its own dark colour to the rim beyond it, not a blend of the
    figure's fill. Pixels further than ``steps`` from any known pixel keep their own colour."""
    out = rgb.astype(np.float64).copy()
    have = known.astype(bool).copy()
    h, w = have.shape
    for _ in range(steps):
        if have.all():
            break
        acc = np.zeros_like(out)
        n = np.zeros((h, w))
        p_c = np.pad(out * have[..., None], ((1, 1), (1, 1), (0, 0)))
        p_h = np.pad(have.astype(np.float64), 1)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == dx == 0:
                    continue
                acc += p_c[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                n += p_h[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        new = ~have & (n > 0)
        if not new.any():
            break
        out[new] = acc[new] / n[new][:, None]
        have |= new
    return out


def _solid_core(alpha: np.ndarray) -> np.ndarray:
    """The opaque pixels whose colour is the figure's own: alpha at or above the rim. On a hard matte (edge under one pixel) the
    outermost opaque ring is dropped too, because a straight cut's boundary pixel still blends the background in."""
    solid = alpha >= RIM[1]
    if edge_width(alpha) >= 1.0:
        return solid
    ring = Image.fromarray((solid * 255).astype(np.uint8), mode="L").filter(ImageFilter.MinFilter(3))
    return np.asarray(ring) > 127


def defringe(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """The colour of every pixel outside the opaque core (the rim, and the 1 px ring inside it) replaced by the colour of the
    nearest core pixel (``grow``); the core keeps its colour. Fully transparent pixels get it too (they are invisible, but a
    renderer's texture filter samples them)."""
    return np.clip(grow(rgb, _solid_core(alpha)), 0, 255)


def finish(image, mask=None) -> Image.Image:
    """The card PNG: RGB of ``image`` (defringed), alpha = the feathered matte. ``mask`` defaults to ``image``'s own alpha."""
    im = image if isinstance(image, Image.Image) else Image.open(image)
    rgb = np.asarray(im.convert("RGB"), dtype=np.float64)
    m = load_mask(mask if mask is not None else im)
    if m.shape != rgb.shape[:2]:
        raise ValueError(f"the mask is {m.shape[1]}x{m.shape[0]}, the picture {rgb.shape[1]}x{rgb.shape[0]}")
    a = feather(m)
    col = defringe(rgb, a)
    out = np.dstack([col, a * 255.0]).round().astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def halo_score(cut) -> float:
    """SA-04: the mean absolute luma difference between the rim (alpha in ``RIM``) and the nearest pixel of the opaque core,
    as a share of 255. 0 = the rim carries the figure's own edge colour; a grey-sheet halo on an inked figure scores high."""
    im = cut if isinstance(cut, Image.Image) else Image.open(cut)
    rgba = np.asarray(im.convert("RGBA"), dtype=np.float64)
    a = rgba[..., 3] / 255.0
    rim = (a > RIM[0]) & (a < RIM[1])
    core = _solid_core(a)
    if not rim.any() or not core.any():
        return 0.0
    near = grow(rgba[..., :3], core, steps=INNER_PX + 4)
    lum, ref = _luma(rgba[..., :3]), _luma(near)
    return float(np.mean(np.abs(lum[rim] - ref[rim])) / 255.0)


def check(cut) -> list[dict]:
    """AC-15 (the figure alone) + SA-04 (halo, REVIEW) of one card."""
    im = cut if isinstance(cut, Image.Image) else Image.open(cut)
    out = check_cutout(im)
    if im.mode != "RGBA":
        out.append({"rule": "SA-04", "severity": "FAIL", "detail": f"mode {im.mode}: a card is an RGBA PNG"})
        return out
    h = halo_score(im)
    if h > HALO_REVIEW:
        out.append({"rule": "SA-04", "severity": "REVIEW", "detail": f"halo {h:.3f} > {HALO_REVIEW}: the rim differs from the "
                    f"figure next to it (re-run finish, or a cleaner matte)", "halo": round(h, 4)})
    return out


def birefnet_mask(image, *, pins: dict | None = None, device: str = "cpu") -> Image.Image:  # pragma: no cover - needs torch
    """The BiRefNet matte of ``image`` (an L picture of its size), from the pinned revision. Runs where torch and transformers
    are installed (the asset pod); the 1024x1024 input and ImageNet normalisation are the model card's."""
    import torch
    from torchvision import transforms
    from transformers import AutoModelForImageSegmentation

    from explainer_engine.cloud import pins as P
    pin = (pins or P.load())["models"][BIREFNET_PIN]
    model = AutoModelForImageSegmentation.from_pretrained(pin["id"], revision=pin["revision"], trust_remote_code=True)
    model.to(device).eval()
    im = (image if isinstance(image, Image.Image) else Image.open(image)).convert("RGB")
    tf = transforms.Compose([transforms.Resize((1024, 1024)), transforms.ToTensor(),
                             transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    with torch.no_grad():
        pred = model(tf(im).unsqueeze(0).to(device))[-1].sigmoid().cpu()[0].squeeze()
    return transforms.ToPILImage()(pred).resize(im.size, Image.BILINEAR)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("finish")
    f.add_argument("--image", required=True)
    f.add_argument("--mask", default=None)
    f.add_argument("--out", required=True)
    f.add_argument("--report", default=None)
    c = sub.add_parser("check")
    c.add_argument("cuts", nargs="+")
    b = sub.add_parser("birefnet")
    b.add_argument("--image", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--device", default="cpu")
    a = ap.parse_args(argv)
    if a.cmd == "birefnet":
        birefnet_mask(a.image, device=a.device).save(a.out)
        return 0
    if a.cmd == "finish":
        out = finish(a.image, a.mask)
        out.save(a.out)
        found = check(out)
        rep = {"cut": a.out, "halo": round(halo_score(out), 4), "findings": found}
        if a.report:
            Path(a.report).write_text(json.dumps(rep, indent=1), encoding="utf-8")
        print(json.dumps(rep, indent=1))
        return 1 if any(x["severity"] == "FAIL" for x in found) else 0
    rows = {p: {"halo": round(halo_score(p), 4), "findings": check(p)} for p in a.cuts}
    print(json.dumps(rows, indent=1))
    return 1 if any(x["severity"] == "FAIL" for r in rows.values() for x in r["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
