"""Opus-medium picture review (journal part clips_G7, REVIEW_pictures_opus_medium.md): free local fixes, no model call.
 - glass lantern on the crate in the left trench of S04_SH013, S06_SH007, S06_SH008, S07_SH003 (banned object): inpainted away
 - portrait card of S05_SH011 and S05_SH012 shows a man: the woman of S05_SH010's card is warped into the card (own border, fingers in front)
 - S06_SH003: faint letter-like marks on a crate: smudged
 - S03_SH003: two big candles standing on nothing at the bottom edge: cropped away (16:9 crop, 1.25x Lanczos)
Usage: python fix_review_items.py <mirrored dir> <S05_SH010 picture> <S03_SH003 new picture> <out dir>"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

mir, sh010, sh003, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)


def load(p):
    return cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)


def save(a, name):
    Image.fromarray(a).save(out / name)
    print(name)


# 1. lanterns
for shot in ("S04_SH013", "S06_SH007", "S06_SH008", "S07_SH003"):
    im = load(mir / f"{shot}_start_mirror.png")
    m = np.zeros(im.shape[:2], np.uint8)
    cv2.rectangle(m, (440, 812), (474, 878), 255, -1)
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    im = cv2.inpaint(im, m, 4, cv2.INPAINT_TELEA)
    # the lantern becomes a candle stub on the crate (a candle is what the world allows): body, flame, a little glow
    fog = float(im[820:880, 400:520].mean()) / 255.0
    lay = np.zeros_like(im, np.float32)
    cv2.rectangle(lay, (452, 851), (459, 867), (236, 222, 190), -1)
    cv2.ellipse(lay, (455, 843), (3, 7), 0, 0, 360, (255, 170, 60), -1)
    cv2.circle(lay, (455, 845), 15, (120, 70, 20), -1)
    glow = cv2.GaussianBlur(lay, (0, 0), 6)
    out_im = np.clip(im.astype(np.float32) + glow * 0.5, 0, 255)
    body = (lay.sum(2) > 0) & (np.abs(lay - 0).sum(2) > 300)
    sharp = cv2.GaussianBlur(lay, (0, 0), 0.8)
    a = np.clip(sharp.sum(2, keepdims=True) / 500.0, 0, 1) * (1 - 0.4 * fog)
    flame = np.zeros_like(im, np.float32)
    cv2.ellipse(flame, (455, 843), (3, 7), 0, 0, 360, (255, 190, 80), -1)
    cv2.rectangle(flame, (452, 851), (459, 867), (236, 222, 190), -1)
    am = cv2.GaussianBlur((flame.sum(2) > 0).astype(np.float32), (0, 0), 1.1)[..., None] * (1 - 0.35 * fog)
    out_im = out_im * (1 - am) + flame * am
    save(np.clip(out_im, 0, 255).astype(np.uint8), f"{shot}_start_fix2.png")

# 2. cards
woman = load(sh010)[665:890, 1300:1490]          # the woman, head and shoulders (190x225)
CARDS = {"S05_SH011": [(1366, 1086), (1465, 1105), (1392, 1242), (1222, 1258)],
         "S05_SH012": [(1688, 780), (1737, 815), (1706, 942), (1641, 936)]}
for shot, quad in CARDS.items():
    im = load(mir / f"{shot}_start_mirror.png")
    h, w = im.shape[:2]
    src = np.float32([[0, 0], [woman.shape[1], 0], [woman.shape[1], woman.shape[0]], [0, woman.shape[0]]])
    M = cv2.getPerspectiveTransform(src, np.float32(quad))
    warp = cv2.warpPerspective(woman, M, (w, h), flags=cv2.INTER_CUBIC)
    poly = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(poly, np.int32(quad), 255)
    poly = cv2.erode(poly, np.ones((3, 3), np.uint8))
    px = im.astype(np.int32)
    skin = ((px[..., 0] - px[..., 2]) > 55) & (px[..., 0] > px[..., 1] + 15)       # fingers stay in front
    mask = (poly > 0) & ~skin
    mask = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.2)[..., None]
    old = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32)
    inside = poly > 0
    g = cv2.cvtColor(warp, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = (g - g[inside].mean()) / (g[inside].std() + 1e-6) * old[inside].std() + old[inside].mean()
    paper = im[inside & (old > np.percentile(old[inside], 55))].astype(np.float32)
    hue = np.median(paper, axis=0) / max(float(np.median(paper)), 1.0)
    new = np.clip(g[..., None] * hue[None, None, :], 0, 255)
    res = im.astype(np.float32) * (1 - mask) + new * mask
    save(res.astype(np.uint8), f"{shot}_start_fix2.png")

# 3. S06_SH003 crate marks
im = load(mir / "S06_SH003_start_mirror.png")
x0, y0, x1, y1 = 2370, 1450, 2570, 1510
reg = im[y0:y1, x0:x1].copy()
im[y0:y1, x0:x1] = cv2.GaussianBlur(cv2.GaussianBlur(reg, (0, 0), 5), (0, 0), 3)
save(im, "S06_SH003_start_fix2.png")

# 4. S03_SH003 crop
im = load(sh003)
ch = 1240
cw = int(round(ch * 16 / 9))
cx0 = (im.shape[1] - cw) // 2
crop = im[0:ch, cx0:cx0 + cw]
up = cv2.resize(crop, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_LANCZOS4)
save(up, "S03_SH003_start_fix2.png")
