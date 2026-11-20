"""2.5D living photo renderer with the 2D smoke plume (L14, 2026-11-20), moved into the repo from the HF script x6_smoke2d.py
(= x6_living5 / run2e + smoke2d: plume source on the brazier, lean away from the person, person silhouette hides the plume).
Only paths and inputs changed: the photo, the depth (metres, .npy) and the faces are arguments, the noise textures are built on first use.
Constants, inventory and look are exactly those of the HF script (the look is the owner's call). CPU only, nothing paid.

Every frame is a pure function of its number. Measure a plume with ``explainer_engine.qa.plume_zones`` on ``Shot.plume_a`` and ``Shot.pmask_f``.
usage: python -m explainer_engine.fx25d.living S07_SH008 out.mp4 --pic photo.png --depth depth_m.npy [--faces-json t.json] [--drift] [--seconds 5]"""
from __future__ import annotations

import sys, json, subprocess, argparse
import numpy as np, cv2
from explainer_engine.fx25d.masks import sky_mask

W, H, FPS = 1280, 720, 24
FOCAL = W / (2 * np.tan(np.radians(30)))      # 60 degree horizontal field of view assumed (nothing measured)
SX, SY = W / 1376, H / 768
CY0 = 0.04      # zoom pivot (share of the height, near the top edge): head room is never cropped
MARGIN = 2.0
LAT, PUSH = 0.026, 0.020          # run2e camera (run2d: 0.012 / 0.012)
K_LO, K_HI, K_EXP = 0.40, 2.4, 1.15   # run2d: 0.55, 1.9, 1.0
NB, BAND_BLUR, BAND_MIX = 6, 18.0, 0.35
SMOKE_LEAN = 60   # smoke2d: extra drift to the right (px of the 1376 picture at the plume top), away from the officer
# officer silhouette of S07_SH008 in 1376x768 picture coordinates, drawn by hand from the photo (green outline checked on the picture); BiRefNet matte is NOT_RUN
OFFICER = [(790, 150), (798, 114), (840, 106), (886, 138), (892, 160), (880, 178), (878, 190), (905, 212), (920, 255), (925, 330), (928, 420), (930, 500), (930, 598), (896, 602), (896, 700), (892, 722), (868, 744), (790, 744), (768, 732), (772, 720), (818, 700), (822, 602), (772, 598), (768, 520), (757, 455), (760, 330), (777, 255), (782, 215), (792, 198), (790, 170)]
YUNET = None   # optional YuNet onnx path (faces are normally passed in)


def fbm(h, w, octaves=5, seed=0):
    """periodic (tileable) 1/f noise: white noise filtered in the Fourier domain, so scrolling it never shows a seam"""
    r = np.random.RandomState(seed); f = np.fft.fft2(r.randn(h, w))
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]; rad = np.sqrt(fx ** 2 + fy ** 2); rad[0, 0] = 1.0
    amp = rad ** -(1.55 + 0.1 * octaves / 2.0); amp *= np.exp(-0.5 * (2 * np.pi * 2.5 * rad) ** 2); amp[0, 0] = 0.0   # smooth at texel scale, still periodic
    x = np.fft.ifft2(f * amp).real.astype(np.float32); x = (x - x.mean()) / (x.std() + 1e-9)
    return np.clip(0.5 + 0.26 * x, 0, 1).astype(np.float32)


NOISE = NOISE2 = NOISE3 = None


def _init_noise():
    global NOISE, NOISE2, NOISE3
    if NOISE is None: NOISE, NOISE2, NOISE3 = fbm(1024, 1024, 6, 3), fbm(1024, 1024, 5, 11), fbm(1024, 1024, 4, 23)


def scroll(tex, ox, oy, out_w, out_h, scale=1.0):
    xs = ((np.arange(out_w, dtype=np.float32)[None, :] * scale + ox) % tex.shape[1]).astype(np.float32)
    ys = ((np.arange(out_h, dtype=np.float32)[:, None] * scale + oy) % tex.shape[0]).astype(np.float32)
    return remap(tex, np.ascontiguousarray(np.broadcast_to(xs, (out_h, out_w)), dtype=np.float32),
                     np.ascontiguousarray(np.broadcast_to(ys, (out_h, out_w)), dtype=np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)


_remap = cv2.remap


def remap(img, mx, my, interp=cv2.INTER_LINEAR, **kw):
    return _remap(img, np.ascontiguousarray(mx, dtype=np.float32), np.ascontiguousarray(my, dtype=np.float32), interp, **kw)


def box(b): return (int(b[0] * SX), int(b[1] * SY), int(b[2] * SX), int(b[3] * SY))


# the director's living-element inventory of each photo, in 1376x768 picture coordinates (LP-01..LP-12 style)
INV = {
    "S07_SH006": dict(
        fires=[dict(box=(300, 520, 440, 720), src=(360, 545), spread=28, embers=60, R=2.4)],
        smoke=[dict(src=(360, 520), spread=0.30, a=2.6, w=46, h=380, depth=7.0, soft=True, v2=True, peak=0.9, hole=0.10, lean=SMOKE_LEAN, avoid=True)],   # smoke2d: avoid needs a person mask (--person-mask): the brazier stands between soldiers, lean alone does not clear them
        sway_trees=[dict(box=(800, 40, 970, 290), base=285, amp=3.2)], sway_cloth=[dict(box=(940, 90, 1110, 470), amp=1.6, y0=260)],
        candles=[1], wind=(1.0, 0.0), snow=1.0, mist=0.22, sky_amp=1.2),
    "S04_SH008": dict(
        fires=[], smoke=[dict(src=(1150, 205), spread=0.35, a=3.2, dark=True, w=40, h=300, depth=50.0, soft=True, v2=True, peak=0.9, hole=0.85)],
        sway_trees=[dict(box=(1180, 140, 1376, 305), base=300, amp=3.0), dict(box=(790, 190, 1060, 300), base=295, amp=2.4)],
        sway_cloth=[dict(box=(620, 370, 790, 640), amp=1.8, y0=470)], candles=[], wind=(1.0, 0.0), snow=3.0, mist=0.85, sky_amp=0.22),
    "S07_SH008": dict(
        fires=[dict(box=(900, 430, 990, 520), src=(942, 460), spread=14, embers=26, R=2.0)],
        smoke=[dict(src=(952, 448), spread=0.22, a=3.0, w=40, h=380, depth=4.5, soft=True, v2=True, peak=0.6, hole=0.85, lean=SMOKE_LEAN, avoid=True)],   # smoke2d: source on the brazier (its fire is the visible origin, flame at ~(938,480)); lean and avoid are new keys, only this plume reads them
        sway_trees=[], sway_cloth=[dict(box=(755, 190, 935, 610), amp=1.6, y0=360)], candles=[], wind=(0.8, 0.0), snow=0.7, mist=0.18, sky_amp=0.85,
        persons=[OFFICER]),
    "S04_SH014": dict(     # held-out photo: inventory written once, no constant changed afterwards
        fires=[dict(box=(188, 322, 228, 366), src=(207, 340), spread=10, embers=22, R=6.0), dict(box=(1172, 328, 1208, 372), src=(1190, 345), spread=10, embers=22, R=6.0)],
        smoke=[dict(src=(222, 318), spread=0.35, a=3.2, w=34, h=300, soft=True, v2=True, peak=0.55, lift=0.04, bias=0.4, hole=0.85), dict(src=(1200, 318), spread=0.35, a=3.2, w=34, h=300, soft=True, v2=True, peak=0.55, lift=0.04, bias=0.4, hole=0.85)],   # run3 (no longer held-out)
        sway_trees=[], sway_cloth=[dict(box=(500, 250, 690, 610), amp=1.2, y0=320), dict(box=(700, 250, 890, 610), amp=1.2, y0=320)],
        candles=[], wind=(1.0, 0.0), snow=2.2, mist=0.7, sky_amp=0.20),
}


class Shot:
    def __init__(self, frame, seconds=5.0, drift=False, particles=True, pic=None, depth=None, faces=None, mouths=None, inventory=None, person_mask=None):
        """pic: BGR image array or path; depth: metres, array or .npy path (same picture); faces: [(x0, y0, x1, y1)] in 1280x720 pixels;
        mouths: [(x, y, score)]; person_mask: extra person zones for the measurement, an image array or path (non-zero = person; resized to 1280x720), unioned
        with the inventory silhouettes and the faces; it never changes the picture, only Shot.pmask / pmask_f; inventory: dict like INV[frame] (default INV[frame])."""
        _init_noise()
        self.frame, self.inv, self.drift, self.particles = frame, (inventory if inventory is not None else INV[frame]), drift, particles
        self.n = int(seconds * FPS); self.secs = seconds
        pic = cv2.imread(str(pic)) if isinstance(pic, (str, bytes)) or hasattr(pic, "__fspath__") else pic
        if pic is None: raise ValueError("pic: an image array or a readable path is required")
        im = cv2.resize(pic, (W, H), interpolation=cv2.INTER_AREA); self.im = im; self.imf = im.astype(np.float32) / 255
        if depth is None: raise ValueError("depth: metres, an array or an .npy path, is required")
        d = (np.load(depth) if isinstance(depth, (str, bytes)) or hasattr(depth, "__fspath__") else np.asarray(depth)).astype(np.float32); inv = ~np.isfinite(d)
        d = np.where(np.isfinite(d), d, np.nanmax(d[np.isfinite(d)])); d = np.clip(d, 0.3, 400.0)
        self.depth = cv2.resize(d, (W, H), interpolation=cv2.INTER_LINEAR)
        self.inv_sky = cv2.resize(inv.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
        self.dsmooth = cv2.GaussianBlur(np.minimum(self.depth, 60.0), (0, 0), 16)   # wide smoothing: a slope stretches, an edge never tears
        c = self.depth[int(0.25 * H):int(0.85 * H), int(0.3 * W):int(0.7 * W)]; self.d0 = float(np.median(c))
        kc = np.clip((self.d0 / self.dsmooth) ** K_EXP, K_LO, K_HI)
        if NB > 0:   # soft depth bands: quantile edges of log-depth, k of each band = its median, feathered so no seam tears
            ld = np.log(np.minimum(self.dsmooth, 60.0)); qs = np.percentile(ld, np.linspace(0, 100, NB + 1)); lab = np.clip(np.digitize(ld, qs[1:-1]), 0, NB - 1)
            kb = np.zeros_like(kc)
            for b in range(NB): kb[lab == b] = float(np.median(kc[lab == b]))
            kb = cv2.GaussianBlur(kb, (0, 0), BAND_BLUR); kc = (1 - BAND_MIX) * kc + BAND_MIX * kb
        self.kmap = kc.astype(np.float32)
        self.gx, self.gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        self.wx, self.wy = self.inv["wind"]
        self.sky = sky_mask(self.im, self.depth, self.inv_sky)
        self.gray_blur = cv2.GaussianBlur(cv2.cvtColor(self.im, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255, (0, 0), 6)
        # sky detail layer (what the real clouds look like) for the drift of the cloud structure
        foot = np.zeros((H, W), np.float32)        # the plumes' own footprint is not "sky": cloud drift must not carry the photo's own smoke away from its chimney
        for sm in self.inv["smoke"]:
            sx_, sy_ = sm["src"][0] * SX, sm["src"][1] * SY; hh_ = sm["h"] * SY; ww_ = sm["w"] * SX
            rise_ = (self.gy - sy_) / -hh_; rc_ = rise_.clip(0, 1)
            for g_ in (0.4, 1.0, 1.6):
                ec = sx_ + (rc_ ** 1.3) * 90 * SX * self.wx * g_ * 0.5; wd_ = ww_ * (0.35 + rc_ * (1.0 + sm["spread"] * 2))
                foot = np.maximum(foot, np.exp(-((self.gx - ec) ** 2) / (2 * wd_ ** 2)) * (rise_ > -0.08) * (rise_ < 1.2))
        foot = cv2.GaussianBlur(cv2.dilate((foot > 0.05).astype(np.uint8), np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 12)
        self.sky_full = self.sky.copy(); self.sky = self.sky * (1 - np.clip(foot * 1.6, 0, 1))
        nonsky = cv2.dilate((self.sky < 0.5).astype(np.uint8), np.ones((25, 25), np.uint8))   # everything that is not sky is filled from the sky around it
        small = cv2.resize(self.im, (W // 4, H // 4), interpolation=cv2.INTER_AREA); ns = cv2.resize(nonsky, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST)
        plate = cv2.resize(cv2.inpaint(small, ns, 5, cv2.INPAINT_TELEA), (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
        self.sky_hp = (plate - cv2.GaussianBlur(plate, (0, 0), 14)) * (1 - np.clip(cv2.GaussianBlur(cv2.dilate((foot > 0.2).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(np.float32), (0, 0), 14) * 1.5, 0, 1))[..., None]
        # fire: flame mask (colour inside the inventory box), position in space, light falloff
        self.fires = []
        for fr in self.inv["fires"]:
            x0, y0, x1, y1 = box(fr["box"]); m = np.zeros((H, W), np.float32)
            hsv = cv2.cvtColor(self.im[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
            m[y0:y1, x0:x1] = ((hsv[..., 2] > 185) & (hsv[..., 1] > 90) & (hsv[..., 0] >= 3) & (hsv[..., 0] <= 34)).astype(np.float32)
            m = cv2.GaussianBlur(m, (0, 0), 1.2); md = cv2.GaussianBlur(cv2.dilate((m > 0.2).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 3)
            sx, sy = fr["src"][0] * SX, fr["src"][1] * SY; dz = float(self.depth[int(np.clip(sy, 0, H - 1)), int(np.clip(sx, 0, W - 1))])
            X = (self.gx - W / 2) * self.depth / FOCAL; Y = (self.gy - H / 2) * self.depth / FOCAL
            fx, fy = (sx - W / 2) * dz / FOCAL, (sy - H / 2) * dz / FOCAL
            r2 = (X - fx) ** 2 + (Y - fy) ** 2 + (self.depth - dz) ** 2
            self.fires.append(dict(mask=m, mask_d=md, sx=sx, sy=sy, dz=dz, r2=r2.astype(np.float32), R=fr["R"], spread=fr["spread"] * SX,
                                   emb=np.random.RandomState(31 + len(self.fires)).rand(max(1, fr["embers"]), 6), n_emb=fr["embers"]))
        # faces: given by the caller (YuNet output of the photo), else YuNet if YUNET names a model, else none
        self.mouths = [tuple(map(float, m)) for m in (mouths or [])]; self.faces = [tuple(map(float, f)) for f in (faces or [])]
        if not self.faces and YUNET:
            try:
                det = cv2.FaceDetectorYN.create(YUNET, "", (W, H), 0.5, 0.3, 50); _, fs = det.detect(self.im)
                for r in (fs if fs is not None else []):
                    lm = r[4:14].reshape(5, 2); mouth = (lm[3] + lm[4]) / 2; self.mouths.append((float(mouth[0]), float(mouth[1]), float(r[14]))); self.faces.append((float(r[0]), float(r[1]), float(r[0] + r[2]), float(r[1] + r[3])))
            except Exception as e:
                print("yunet failed", e, file=sys.stderr)
        # snow flakes in three depth bands (+ a few crossing the lens); z in metres from the depth distribution of THIS photo
        q = lambda a: float(np.percentile(np.minimum(self.depth, 80.0), a))
        rs = np.random.RandomState(sum(map(ord, frame)))
        k = self.inv["snow"]; nb = dict(far=int(4200 * k), mid=int(900 * k), near=int(110 * k))
        zr = dict(far=(q(62), max(q(62) * 1.5, q(99))), mid=(q(22), q(62)), near=(max(0.45, q(3)), max(0.9, q(22))))
        fl = []
        for band, nn in nb.items():
            z = np.exp(rs.uniform(np.log(max(0.4, zr[band][0])), np.log(max(zr[band][1], zr[band][0] * 1.2)), nn))
            for i in range(nn): fl.append((band, z[i], rs.rand() * (W + 120), rs.rand() * (H + 120), rs.rand() * 6.28, 0.7 + 0.6 * rs.rand()))
        self.flakes = fl
        self.lens = [dict(x0=rs.rand() * W, y0=rs.rand() * H, vx=-40 + 80 * rs.rand(), vy=60 + 80 * rs.rand(), r=14 + 14 * rs.rand()) for _ in range(4)]
        self.tel = dict(far_drawn=0, far_hidden=0, mid_drawn=0, mid_hidden=0, near_drawn=0, near_hidden=0, violations=0, frames=0)
        self.last_env = np.zeros((H, W), np.float32)
        self.pmask = np.zeros((H, W), np.uint8)       # smoke2d: person zones (hard silhouette) in output pixels
        for poly in self.inv.get("persons", []):
            cv2.fillPoly(self.pmask, [np.array([(x * SX, y * SY) for x, y in poly], np.int32)], 1)
        for (fx0, fy0, fx1, fy1) in self.faces: self.pmask[int(fy0):int(fy1), int(fx0):int(fx1)] = 1
        if person_mask is not None:
            pm_in = cv2.imread(str(person_mask), cv2.IMREAD_GRAYSCALE) if isinstance(person_mask, (str, bytes)) or hasattr(person_mask, "__fspath__") else np.asarray(person_mask)
            if pm_in is None: raise ValueError("person_mask: not readable")
            if pm_in.ndim == 3: pm_in = pm_in.max(axis=2)
            self.pmask = np.maximum(self.pmask, (cv2.resize(pm_in.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8))
        self.pmask_f = self.pmask.astype(np.float32)
        if any(sm.get("avoid") for sm in self.inv["smoke"]) and not self.pmask.any():
            raise ValueError("a plume with avoid=True needs person zones (inventory 'persons', faces or person_mask): refusing to render it onto people unchecked")
        self.phide = np.clip(cv2.GaussianBlur(cv2.dilate(self.pmask, np.ones((7, 7), np.uint8)).astype(np.float32), (0, 0), 2.5) * 1.15, 0, 1)   # nearer person covers the plume (feathered, 3 px grown)
        self.plume_a = np.zeros((H, W), np.float32)
        self.z0 = 1.0; self.edge = None
        if self.drift: self.solve_zoom()

    def wind(self, t): return 1.0 + 0.55 * np.sin(t * 0.9 + 1.3) + 0.3 * np.sin(t * 2.3)     # ONE wind for snow, smoke, cloth, breath, mist, clouds

    # ---- camera drift with depth parallax (D-139: slow push + lateral over the shot)
    def cam(self, t):
        u = t / self.secs; e = u * u * (3 - 2 * u)
        return (LAT * W * (e - 0.5), PUSH * e) if self.drift else (0.0, 0.0)   # lateral px at the focus depth, push share at the focus depth

    def maps(self, t, z0):
        sxp, pz = self.cam(t); k = self.kmap; zf = z0 + pz * k; cy0 = CY0 * H
        return W / 2 + (self.gx - W / 2) / zf - sxp * k, cy0 + (self.gy - cy0) / zf

    def solve_zoom(self):
        """smallest base zoom (steps of 0.002) for which, at every frame of the move, every sample lies inside the picture by MARGIN px:
        no replicated, smeared or empty border at any frame; also records the visible rectangle and the worst top crop."""
        ts = [i / FPS for i in range(self.n)]
        z = 1.0
        while z < 1.3:
            lo = [1e9, 1e9]; hi = [-1e9, -1e9]
            for t in ts:
                u, v = self.maps(t, z); lo = [min(lo[0], float(u.min())), min(lo[1], float(v.min()))]; hi = [max(hi[0], float(u.max())), max(hi[1], float(v.max()))]
            if lo[0] >= MARGIN and lo[1] >= 0 and hi[0] <= W - 1 - MARGIN and hi[1] <= H - 1 - MARGIN: break
            z += 0.002
        self.z0 = z
        self.edge = dict(z0=round(z, 3), min_u=round(lo[0], 2), min_v=round(lo[1], 2), max_u=round(hi[0], 2), max_v=round(hi[1], 2),
                         top_crop_px=round(lo[1], 2), left_crop_px=round(lo[0], 2), right_crop_px=round(W - 1 - hi[0], 2), bottom_crop_px=round(H - 1 - hi[1], 2))

    def parallax(self, img, t, interp=cv2.INTER_LINEAR):
        sxp, pz = self.cam(t)
        if sxp == 0 and pz == 0: return img
        k = self.kmap
        zf = self.z0 + pz * k; cy0 = CY0 * H; u = W / 2 + (self.gx - W / 2) / zf - sxp * k; v = cy0 + (self.gy - cy0) / zf   # run3: zoom pivot near the top edge keeps head room (caps stay in frame)
        return remap(img, u.astype(np.float32), v.astype(np.float32), interp, borderMode=cv2.BORDER_REPLICATE)

    def render(self, f):
        t = f / FPS; g = self.wind(t); out = self.imf.copy(); inv = self.inv
        self.plume_a = np.zeros((H, W), np.float32)
        self.m_emb = np.zeros((H, W), np.float32); self.m_far = np.zeros((H, W), np.float32); self.m_all = np.zeros((H, W), np.float32)
        gx, gy = self.gx, self.gy
        dx = np.zeros((H, W), np.float32); dy = np.zeros((H, W), np.float32)
        for tr in inv["sway_trees"]:
            x0, y0, x1, y1 = box(tr["box"]); base = tr["base"] * SY; sub = np.zeros((H, W), np.float32); sub[y0:y1, x0:x1] = 1
            w = np.clip((base - gy) / max(1, base - y0), 0, 1) ** 1.5 * cv2.GaussianBlur(sub, (0, 0), 6)
            dx += tr["amp"] * w * g * (np.sin(t * 2.1 + gx * 0.02) * 0.7 + (scroll(NOISE, t * 40, 0, W, H) - 0.5) * 1.2) * self.wx
        for c in inv["sway_cloth"]:
            x0, y0, x1, y1 = box(c["box"]); sub = np.zeros((H, W), np.float32); sub[y0:y1, x0:x1] = 1; sub = cv2.GaussianBlur(sub, (0, 0), 10)
            w = np.clip((gy - c["y0"] * SY) / max(1, y1 - c["y0"] * SY), 0, 1) * sub
            dx += c["amp"] * w * g * (np.sin(t * 3.0 + gy * 0.03) + 0.6 * (scroll(NOISE2, t * 55, t * 20, W, H) - 0.5) * 2) * self.wx
            dy += 0.4 * c["amp"] * w * np.sin(t * 2.4 + gx * 0.02)
        for fr in self.fires:      # flame deformation and heat haze above it (haze only on surfaces behind the brazier)
            fd = cv2.GaussianBlur(fr["mask_d"], (0, 0), 2)
            nz = scroll(NOISE2, 30 * np.sin(t * 5.1), t * 520, W, H); nz2 = scroll(NOISE, t * 310, -t * 90, W, H)
            dy += -7.0 * fd * (nz - 0.5) * 2 - 3.0 * fd * (nz2 - 0.5); dx += 6.0 * fd * (nz2 - 0.5) * 2 + 1.5 * fd * self.wx
            hh = fr["spread"] * 7 + 90 * SX; up = np.clip((fr["sy"] - 6 - gy) / hh, 0, 1.4)
            col = np.exp(-((gx - fr["sx"] - up * 25 * self.wx) ** 2) / (2 * (fr["spread"] * 2.2 + 14 * SX + up * 22 * SX) ** 2))
            haze = col * np.clip(up * 3, 0, 1) * np.clip(1.5 - up, 0, 1) * (self.depth > fr["dz"] * 0.9)
            hn = scroll(NOISE3, t * 40, t * 260, W, H, 0.8); hn2 = scroll(NOISE2, -t * 30, t * 190, W, H, 1.2)
            dx += 3.4 * haze * (hn - 0.5) * 2; dy += 2.4 * haze * (hn2 - 0.5) * 2
        if np.any(dx) or np.any(dy):
            out = remap(out, gx - dx, gy - dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # ---- fire: flicker, light that falls on the world (faces, coats, sandbags) with distance, embers
        for i, fr in enumerate(self.fires):
            ph = i * 1.9; fl = 0.84 + 0.30 * (0.5 + 0.5 * np.sin(t * 17.0 + ph + 0.5 * np.sin(t * 7.0 + ph)))
            fm = remap(fr["mask"], gx - dx, gy - dy, cv2.INTER_LINEAR)[..., None]
            out = np.clip(out * (1 + (fl - 1.0) * fm * 1.6), 0, 1)
            inten = 0.55 + 0.40 * np.sin(t * 13.0 + ph + 1.0) * 0.5 + 0.12 * np.sin(t * 29.0 + ph) + 0.15 * np.sin(t * 5.3 + ph)
            lum = cv2.cvtColor((out * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255
            light = np.exp(-fr["r2"] / (2 * fr["R"] ** 2))[..., None] * (1 - fm)
            out = np.clip(out + light * inten * (0.12 + 0.88 * lum ** 0.6) * np.array([0.10, 0.36, 0.80], np.float32) * 0.62, 0, 1)
            if self.particles and fr["n_emb"]:
                layer = np.zeros((H, W, 3), np.float32)
                for j, e in enumerate(fr["emb"]):
                    life = 1.4 + 1.6 * e[0]; p = (t / life + e[1]) % 1.0
                    x = fr["sx"] + (e[2] - 0.5) * fr["spread"] * 2 + p * (30 + 55 * e[3]) * self.wx * g * 0.6 + 8 * np.sin(p * 9 + e[4] * 6) * SX
                    y = fr["sy"] - p * (90 + 160 * e[5]) * SY * (0.5 + 0.5 * min(1.5, fr["R"] / 2.4))
                    a = (1 - p) ** 1.3 * (0.6 + 0.4 * np.sin(t * 25 + j)); r = 1.2 + 1.2 * e[3]
                    cv2.circle(layer, (int(x), int(y)), int(max(1, r)), (0.15 * a, 0.55 * a, 1.0 * a), -1, cv2.LINE_AA)
                out = np.clip(out + cv2.GaussianBlur(layer, (0, 0), 0.9) * 1.4, 0, 1); self.m_emb = np.maximum(self.m_emb, np.clip(cv2.GaussianBlur(layer.max(axis=2), (0, 0), 0.9) * 4, 0, 1))
        # ---- smoke plumes (advected noise inside a widening, wind-bent envelope; nearer surfaces cover it)
        for s in inv["smoke"]:
            sx, sy = s["src"][0] * SX, s["src"][1] * SY; hh = s["h"] * SY; ww = s["w"] * SX
            dsrc = float(s.get("depth") or self.depth[int(np.clip(sy, 0, H - 1)), int(np.clip(sx, 0, W - 1))]); dsrc = max(dsrc, 1.0)
            rise = (gy - sy) / -hh; rc = rise.clip(0, 1)
            env_c = sx + (rc ** 1.3) * (90 * SX * self.wx * g * 0.5 + s.get("lean", 0.0) * SX)
            wd = ww * (0.35 + rc * (1.0 + s["spread"] * 2)); lat = np.exp(-((gx - env_c) ** 2) / (2 * wd ** 2))
            vert = np.clip(rise, 0, 1) ** 0.5 * np.clip(1 - rise, 0, 1) ** 1.2 * (rise > 0)
            self.last_env = np.maximum(self.last_env, lat * vert)
            wp = (scroll(NOISE2, t * 30, t * 50, W, H, 0.4) - 0.5) * 60
            n1 = scroll(NOISE, (t * 90 * self.wx * g) * 3.5 + wp, (t * 300) * 3.5 + wp, W, H, 3.5); n2 = scroll(NOISE2, (t * 140 * self.wx) * 2.5 - wp, (t * 520) * 2.5, W, H, 2.5)
            dens = cv2.GaussianBlur(np.clip((n1 * 0.6 + n2 * 0.4 - 0.43) * 3.2, 0, 1), (0, 0), 2.5) * np.clip(lat * 1.6, 0, 1) * np.clip(vert * 1.8, 0, 1)
            cover = np.maximum(np.clip((self.depth - dsrc * 0.92) / (dsrc * 0.08 + 0.05), 0, 1), np.clip(self.sky * 1.5, 0, 1))   # sky pixels never hide smoke
            if s.get("v2"):   # run2d: stronger soft steam. Smooth sigmoid of two advected noise octaves inside a smooth envelope (no clip thresholds, no plateau),
                # sheared by height (wind grows with height, ONE sign), rising; occlusion by nearer surfaces is a wide smooth ramp (no 0.5 floor); faces are protected.
                xs = (gx - t * 30 * self.wx * (0.35 + rc) - wp * 0.2) * 0.6; ys = (gy + t * 80) * 0.6
                n1v = remap(NOISE, xs % 1024, ys % 1024, cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
                xs2 = (gx - t * 30 * self.wx * (0.35 + rc) - wp * 0.2) * 1.6; ys2 = (gy + t * 80) * 1.6
                n2v = remap(NOISE3, xs2 % 1024, ys2 % 1024, cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
                z = (0.75 * (n1v - 0.5) + 0.25 * (n2v - 0.5)) / 0.2
                vs = np.clip(rc * 2.6, 0, 1); vs = vs * vs * (3 - 2 * vs); vf = np.clip((1.0 - rise) / 0.45, 0, 1); vf = vf * vf * (3 - 2 * vf)
                envv = np.exp(-((gx - env_c) ** 2) / (2 * (wd * 1.15) ** 2)) * vs * vf * (rise > 0)
                dv = envv / (1.0 + np.exp(-(s.get("slope", 2.0) * z + s.get("bias", 1.6))))
                nearer = cv2.GaussianBlur(np.clip((dsrc * 0.97 - self.depth) / (dsrc * 0.2 + 0.05), 0, 1), (0, 0), 6)
                guard = np.zeros((H, W), np.float32)
                for (fx0, fy0, fx1, fy1) in self.faces:
                    cx_, cy_, bw, bh = (fx0 + fx1) / 2, (fy0 + fy1) / 2, fx1 - fx0, fy1 - fy0
                    cv2.ellipse(guard, (int(cx_), int(cy_ + 0.25 * bh)), (int(bw * 1.1), int(bh * 1.5)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
                guard = 1 - 0.65 * np.clip(cv2.GaussianBlur(guard, (0, 0), 22) * 1.5, 0, 1)
                a = np.clip(s["peak"] * np.clip(dv * s["a"], 0, 1) * (1 - nearer) * guard, 0, 0.9)
                if s.get("avoid"): a = a * (1 - self.phide)
                self.plume_a = np.maximum(self.plume_a, a); self.last_env = np.maximum(self.last_env, 0) ; self.vis_env = np.maximum(getattr(self, 'vis_env', 0), lat * vert * (1 - nearer) * ((1 - self.phide) if s.get('avoid') else 1.0))
            elif s.get("soft"):   # run2c: soft noise-shaped plume: smooth saturation (no flat plateau), low peak, depth cover feathered (no straight occlusion edge)
                cover = cv2.GaussianBlur(np.maximum(np.clip((self.depth - dsrc * 0.7) / (dsrc * 0.5 + 0.05), 0, 1), np.clip(self.sky * 1.5, 0, 1)), (0, 0), 22); cover = 0.5 + 0.5 * cover
                n3 = scroll(NOISE3, (t * 60 * self.wx) * 1.8 + wp * 0.5, (t * 260) * 1.8, W, H, 1.8)    # a second, coarser turbulence breaks the interior up: wisps with holes, no plateau
                dens = dens * np.clip(s.get("hole", 0.5) + 1.7 * (n3 - 0.38), 0, 1) ** 1.3 * np.clip(rc * 6.0, 0, 1) ** 1.5
                a = s["peak"] * np.clip(dens * s["a"], 0, 1) ** 1.25 * cover * np.clip(lat * 2.0, 0, 1)
            else:
                a = np.clip(dens * s["a"] * 3.0, 0, 0.85) * cover
            self.dbg_a = a
            col = np.array([0.50, 0.50, 0.52], np.float32) * (0.6 + 0.4 * (np.mean(self.imf[max(0, int(sy - hh)):int(sy), :, :], axis=(0, 1)).mean() * 2))
            if s.get("dark"): col = np.array([0.30, 0.30, 0.32], np.float32)
            if s.get("v2"): colm = np.clip(cv2.GaussianBlur(out, (0, 0), 14) * (0.55 if s.get("dark") else 1.35) + (0.0 if s.get("dark") else s.get("lift", 0.30)), 0, 1); out = out * (1 - a[..., None]) + colm * a[..., None]
            elif s.get("soft"): colm = np.clip(cv2.GaussianBlur(out, (0, 0), 16) * (0.55 if s.get("dark") else 1.25) + (0.0 if s.get("dark") else 0.14), 0, 1); out = out * (1 - a[..., None]) + colm * a[..., None]
            else: out = out * (1 - a[..., None]) + col * a[..., None]
        # ---- mist between the depth planes: density follows depth (aerial perspective), drifts with the wind
        km = inv["mist"]
        if km > 0:
            far = 1 - np.exp(-np.minimum(self.depth, 80.0) / (0.6 * float(np.percentile(np.minimum(self.depth, 80), 90)) + 1e-3))
            nm = scroll(NOISE, t * 40 * self.wx * g, t * 4, W, H, 0.6) * 0.65 + scroll(NOISE2, t * 62 * self.wx * g, t * 6, W, H, 0.4) * 0.35
            a = np.clip(km * far * (0.35 + 1.3 * (nm - 0.25)), 0, 0.7) * (1 - 0.85 * self.sky)
            hz = self.imf[: int(0.55 * H)][self.sky[: int(0.55 * H)] > 0.5]; fogc = (np.percentile(hz, 85, axis=0) if hz.size else np.array([0.8, 0.82, 0.85])) * 0.92 + 0.05
            out = out * (1 - a[..., None]) + fogc[None, None, :] * a[..., None]
        # ---- sky: the real cloud structure drifts as a detail layer inside a feathered mask (no box, no replaced pixels, so no halo) + slow brightness flow
        sw = self.sky[..., None]
        if sw.max() > 0:
            vc = 20.0 * self.wx; sh = t * vc        # run2b: ONE constant cloud velocity (px/s, +x) for detail layer and brightness flow; never multiplied by the gust
            det = remap(self.sky_hp, gx - sh, gy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            out = out + (det - self.sky_hp) * sw * 1.15
            m1 = scroll(NOISE, -(t * vc) * 0.30, t * 1.0, W, H, 0.30) - 0.5; m2 = scroll(NOISE3, -(t * vc) * 0.6, t * 1.5, W, H, 0.6) - 0.5
            mod = m1 * 1.0 + m2 * 0.6; mod = np.tanh(3.2 * (mod - cv2.GaussianBlur(mod, (0, 0), 90))) * inv["sky_amp"] * 1.3     # zero-mean: clouds brighten and darken, the sky as a whole does not shift
            out = out * (1 + mod[..., None] * self.sky_full[..., None])
        # ---- candles (existing warm lights flicker), breath from YuNet mouths
        if inv["candles"]:
            x0, y0, x1, y1 = box((800, 100, 960, 260)); hsv = cv2.cvtColor((out[y0:y1, x0:x1] * 255).astype(np.uint8), cv2.COLOR_BGR2HSV)
            lm = cv2.GaussianBlur(((hsv[..., 2] > 170) & (hsv[..., 1] > 60) & (hsv[..., 0] < 40)).astype(np.float32), (0, 0), 1.5)
            ph = gx[y0:y1, x0:x1] * 0.37 + gy[y0:y1, x0:x1] * 0.21; fl2 = 1 + 0.30 * np.sin(t * 11 + ph) * np.sin(t * 6.3 + ph * 0.7)
            out[y0:y1, x0:x1] = np.clip(out[y0:y1, x0:x1] * (1 + (fl2 - 1)[..., None] * lm[..., None] * 1.5), 0, 1)
        for k, (mx, my, sc) in enumerate(self.mouths):
            per = 3.4 + 0.35 * (k % 3); ph = ((t + k * 1.1) % per) / per
            if ph < 0.75:
                r = (3 + ph * 15) * SX; x = mx + ph * 40 * self.wx * g - ph * 4; y = my - ph * 70 * SY
                m = np.exp(-(((gx - x) ** 2) * 1.6 + ((gy - y) ** 2) * 0.7) / (2 * r ** 2)) * np.clip(scroll(NOISE2, t * 90, t * 40, W, H, 0.6) * 1.4, 0, 1)
                a = cv2.GaussianBlur((np.sin(ph / 0.75 * np.pi) ** 1.5) * 0.16 * m, (0, 0), 2.0)
                out = out * (1 - a[..., None]) + np.clip(cv2.GaussianBlur(out, (0, 0), 14) * 1.5 + 0.12, 0, 1) * a[..., None]   # run3: vapour takes the surroundings' tone, lighter, softer
        out = np.clip(out, 0, 1)
        # ---- camera drift (parallax by depth) on everything above, then the snow with its own parallax
        out = self.parallax(out, t); self.m_emb = self.parallax(self.m_emb, t)
        if self.particles: out = self.snow(out, t, g)
        self.m_all = np.maximum(self.m_all, self.m_emb)
        return (np.clip(out, 0, 1) * 255).astype(np.uint8)

    def snow(self, out, t, g):
        sxp, pz = self.cam(t); depth_w = self.parallax(self.depth, t) if self.drift else self.depth
        layers = dict(far=np.zeros((H, W), np.float32), mid=np.zeros((H, W), np.float32), near=np.zeros((H, W), np.float32))
        cnt = self.tel; cnt["frames"] += 1
        for band, z, x0, y0, ph, sv in self.flakes:
            vf = 0.40 * sv; vw = 0.50 * self.wx * g * (1.0 if band != "far" else 0.9)
            px_s = FOCAL / z                                    # pixels per metre at this depth
            x = (x0 + t * vw * px_s + 14 * np.sin(t * 1.3 + ph) * (1 / (1 + z * 0.3)) - sxp * min(3.0, self.d0 / z) * 0.8) % (W + 120) - 60
            y = (y0 + t * vf * px_s) % (H + 120) - 60
            xi, yi = int(x), int(y)
            if xi < 0 or yi < 0 or xi >= W or yi >= H: continue
            hid = z > depth_w[yi, xi] * 1.02                    # a nearer surface at that pixel hides the flake
            cnt[band + "_hidden" if hid else band + "_drawn"] += 1
            if hid: continue
            if z > depth_w[yi, xi] * 1.02: cnt["violations"] += 1
            r = FOCAL * 0.0042 / z; a = {"far": 0.50, "mid": 0.78, "near": 0.92}[band] * min(1.0, 0.5 + r * 0.4)
            streak = min(22, int(0.5 * vf * px_s / FPS * 3))
            if band == "far" or r < 1.0:
                cv2.circle(layers[band], (xi, yi), 1, a, -1, cv2.LINE_AA)
            elif streak > 1:
                cv2.line(layers[band], (xi, yi), (int(x - self.wx * streak * 0.35), int(y - streak)), a, int(max(1, round(r))), cv2.LINE_AA)
            else:
                cv2.circle(layers[band], (xi, yi), int(max(1, round(r))), a, -1, cv2.LINE_AA)
        layers["far"] = cv2.GaussianBlur(layers["far"], (0, 0), 0.6); layers["mid"] = cv2.GaussianBlur(layers["mid"], (0, 0), 0.7)
        layers["near"] = cv2.GaussianBlur(layers["near"], (0, 0), 2.2)               # near flakes defocused
        # lens flakes: a few very near, big, soft, crossing the lens (not hidden by anything)
        lens = np.zeros((H, W), np.float32)
        for L in self.lens:
            x = (L["x0"] + t * (L["vx"] + 40 * self.wx * g)) % (W + 80) - 40; y = (L["y0"] + t * L["vy"]) % (H + 80) - 40
            cv2.circle(lens, (int(x), int(y)), int(L["r"]), 0.30, -1, cv2.LINE_AA)
        lens = cv2.GaussianBlur(lens, (0, 0), 7.0)
        # flake light from the surroundings: warm near the brazier, cool in shadow, darker than a bright sky
        amb = cv2.GaussianBlur(out, (0, 0), 22); bl = amb.mean(axis=2, keepdims=True)
        chroma = amb / np.maximum(amb.max(axis=2, keepdims=True), 1e-3)
        tone = np.where(bl > 0.55, bl * 0.86, np.clip(bl * 1.9 + 0.38, 0.42, 0.98))
        col = np.clip(chroma * tone * 1.0 + (1 - chroma) * 0.0, 0, 1)
        col = np.clip(col * 0.85 + tone * 0.15, 0, 1)
        for band, wgt in (("far", 1.0), ("mid", 1.0), ("near", 1.0)):
            a = np.clip(layers[band] * wgt, 0, 1)[..., None]; out = out * (1 - a) + col * a
        a = lens[..., None]; out = out * (1 - a) + np.clip(col * 1.05, 0, 1) * a
        self.m_far = np.clip(layers['far'] * 3, 0, 1)
        self.m_all = np.maximum.reduce([np.clip(layers['far'] * 3, 0, 1), np.clip(layers['mid'] * 3, 0, 1), np.clip(layers['near'] * 3, 0, 1), np.clip(lens * 3, 0, 1)])
        return out

    def zones(self):
        zs = {}
        f = np.zeros((H, W), np.float32)
        for fr in self.fires: f = np.maximum(f, fr["mask_d"])
        if f.max() > 0: zs["fire"] = (f > 0.3)
        if self.last_env.max() > 0: zs["smoke"] = ((self.vis_env if hasattr(self, "vis_env") else self.last_env) > 0.07)
        zs["sky"] = (self.sky > 0.5)
        return zs


def run(frame, out_mp4, seconds=5.0, drift=False, particles=True, tel=None, **shot_kw):
    s = Shot(frame, seconds, drift, particles, **shot_kw)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out_mp4], stdin=subprocess.PIPE)
    stem = out_mp4[:-4]; mw = {}
    if particles:
        for nm in ("matte", "far"):
            mw[nm] = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                       "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", f"{stem}_{nm}.mp4"], stdin=subprocess.PIPE)
    CHK = (1, 25, 49, 73, 97, 121); metrics = {}
    for f in range(max(s.n, 121)):
        fr_img = s.render(f)
        if f < s.n: p.stdin.write(fr_img.tobytes())
        if f + 1 in CHK:      # 1-based frame numbers, as in the X3 reports; measured on the frame as it is seen (after the camera move)
            t_ = f / FPS; a_ = s.parallax(s.plume_a, t_); pm_ = s.parallax(s.pmask_f, t_) > 0.5
            from explainer_engine.qa import plume_zones as PZ   # the shared measure: NOT_RUN (never PASS) without a person mask or without a plume
            ps = PZ.plume_in_person_share(a_, pm_ if s.pmask.any() else None); ts = PZ.plume_total_share(a_)
            metrics["f%d" % (f + 1)] = dict(person_share=ps["value"], person_share_status=ps["status"], plume_area_share=ts["value"], plume_area_share_status=ts["status"],
                                            plume_mean_alpha=round(float(a_.mean()), 5), in_clip=bool(f < s.n))
            cv2.imwrite(stem + "_f%03d.png" % (f + 1), cv2.resize(fr_img, (640, 360), interpolation=cv2.INTER_AREA))
            cv2.imwrite(stem + "_f%03d_alpha.png" % (f + 1), cv2.resize((np.clip(a_, 0, 1) * 255).astype(np.uint8), (640, 360), interpolation=cv2.INTER_AREA))
            if f + 1 == 1: cv2.imwrite(stem + "_person_zone.png", (pm_ * 255).astype(np.uint8))
        if particles and f < s.n:
            mw["matte"].stdin.write((np.clip(s.m_all, 0, 1) * 255).astype(np.uint8).tobytes()); mw["far"].stdin.write((np.clip(s.m_far, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    json.dump(metrics, open(f"{stem}.smoke_metrics.json", "w"), indent=1); print(metrics)
    for w in mw.values(): w.stdin.close(); w.wait()
    inv_d = 1.0 / np.minimum(s.depth, 80.0); inv_d = (inv_d - inv_d.min()) / (inv_d.max() - inv_d.min() + 1e-9)
    cv2.imwrite(f"{stem}_depth.png", (inv_d * 255).astype(np.uint8))
    zj = {"zones": []}
    for name, m in s.zones().items():
        cv2.imwrite(f"{stem}.{name}.png", (m * 255).astype(np.uint8)); zj["zones"].append({"name": name, "kind": name, "mask": f"{stem.split('/')[-1]}.{name}.png"})
    if particles:
        b = stem.split('/')[-1]; zj["particles"] = {"matte": f"{b}_matte.mp4", "far": f"{b}_far.mp4"}; zj["depth"] = f"{b}_depth.png"
    json.dump(zj, open(f"{stem}.zones.json", "w"))
    t = dict(s.tel); t["mouths"] = [(round(a), round(b), round(c, 2)) for a, b, c in s.mouths]; t["d0_m"] = round(s.d0, 2)
    if drift:
        dd = s.depth; lo_, hi_ = np.percentile(dd, 10), np.percentile(dd, 90); sx0, pz0 = s.cam(0.0); sx1, pz1 = s.cam(s.secs - 1.0 / FPS)
        def shift(m):
            k_ = float(np.median(s.kmap[m])); return abs((sx1 - sx0) * k_)
        t["parallax_px"] = dict(near=round(shift(dd <= lo_), 1), far=round(shift(dd >= hi_), 1), mid=round(shift((dd > lo_) & (dd < hi_)), 1),
                                near_far_ratio=round(shift(dd <= lo_) / max(1e-6, shift(dd >= hi_)), 2), lateral_px_at_focus=round(abs(sx1 - sx0), 1))
    t["edge"] = s.edge; t["faces"] = [[round(v) for v in fb] for fb in s.faces]; t["cloud_velocity_px_s"] = 20.0 * s.wx
    json.dump(t, open(f"{stem}.telemetry.json", "w")); print(frame, out_mp4, t)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("frame"); ap.add_argument("out"); ap.add_argument("--pic", required=True); ap.add_argument("--depth", required=True)
    ap.add_argument("--person-mask", help="image, non-zero = person (measurement only)"); ap.add_argument("--faces-json", help="json with 'faces' and 'mouths' (the telemetry of an earlier run)"); ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--drift", action="store_true"); ap.add_argument("--noparticles", action="store_true"); ap.add_argument("--baseline", action="store_true")
    a = ap.parse_args(argv)
    kw = {}
    if a.faces_json:
        tj = json.load(open(a.faces_json)); kw = dict(faces=tj.get("faces"), mouths=tj.get("mouths"))
    if a.baseline:   # the run2e smoke exactly as it was: source (945, 445), no lean, no person avoidance
        sm = INV["S07_SH008"]["smoke"][0]; sm.update(src=(945, 445), lean=0.0, avoid=False)
    run(a.frame, a.out, a.seconds, a.drift, not a.noparticles, pic=a.pic, depth=a.depth, person_mask=a.person_mask, **kw)


if __name__ == "__main__":
    main()
