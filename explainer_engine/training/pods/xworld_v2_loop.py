"""The xworld_v2 picture-strategy loop (the Opus plan /mnt/project-files/xworld_v2/STRATEGY_LOOP_PLAN_2026-10-26.md, OR-26).

The loop: draw -> measure -> attribute each failure to ONE cause -> change only that cause -> draw again. This module is the free part
(numpy and PIL; the depth estimator and the VLM answers are plugged in), so every round starts with a dry run before any pod:

  rows       the strategy registry (pure strategies S1, S2T, S2E, S3cA, S3cAB and mixes M2, M4, M5, M3): what each needs
  round      a round config (rows, scenes, seeds, shots, cfg) and its ``changes`` (ONE per row, refused otherwise, round_N/changes.json)
  3D code    ``s0_agreement`` (the set's s0 render against the master: depth Spearman and every landmark's screen x) stops the round
  canvases   ``control_canvas`` (the 2x2 depth for M2/M4), ``inpaint_canvas`` (M4: the master in panel 1, the mask over 2-4),
             ``reproject`` (M5: the master warped into a new camera, with its hole mask)
  measures   geometry Spearman, frozen-plate SSIM, landmark order, grain, pass/fail per shot, ``scores``, ``sheet``
  decisions  ``attribute`` (the first matching cause of the plan's section 4) and ``stop`` (the success and no-progress rules)

    python xworld_v2_loop.py dry <round.json> <out dir>     writes the job list (pictures, prompts, canvases) without a model
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PODS = Path(__file__).parent
PANEL = (1280, 704)  # w, h of one panel (both /64); a 2x2 canvas is 2560x1408
SCENES = ("tent", "rome")
SHOTS = ("s1", "s2", "s3", "s4")
SEEDS = (11, 23)
SMALL_MOVES = {"tent": ("s2",), "rome": ("s2",)}  # push-ins: the only shots M5 (master-warp) is tried on
CONTROL_BAR, OTHER_BAR = 0.75, 0.6  # geometry Spearman bars of the plan
PLATE_MAX = 0.6  # a real cut: SSIM of the background against the master is below this
LANDMARK_MIN = 0.8
GRAIN_MAX = 1.2  # of the master's value
S0_SPEARMAN_MIN, S0_X_TOL = 0.6, 0.08
PASS_SHOTS = 7  # of 8 shots on EACH seed
CAUSES = ("3d_code", "strategy_setting", "strategy_limit", "frozen_plate", "prompt", "reference", "identity_reference", "passes",
          "model_data")
MAX_ROUNDS, NO_PROGRESS_ROUNDS = 4, 3

ROWS = {
    "S1": {"kind": "pure", "control": False, "grid": False, "note": "edit from the master + sheets (P2S); control row of round 1 only"},
    "S2T": {"kind": "pure", "control": False, "grid": True, "note": "2x2 grid, text only, O1 prompt fixes"},
    "S2E": {"kind": "pure", "control": False, "grid": True, "note": "2x2 grid, edit with the wide panel as Image 1 (test A)"},
    "S3cA": {"kind": "pure", "control": True, "grid": False, "note": "depth ControlNet per shot (pass A)"},
    "S3cAB": {"kind": "pure", "control": True, "grid": False, "note": "S3cA + identity pass B (master + sheet)"},
    "M2": {"kind": "mix", "control": True, "grid": True, "note": "S2 grid canvas + one 2x2 depth control image"},
    "M4": {"kind": "mix", "control": True, "grid": True, "note": "grid in-painting: master in panel 1, mask panels 2-4, 2x2 depth control"},
    "M5": {"kind": "mix", "control": True, "grid": False, "note": "master-warp for small moves, the holes in-painted"},
    "M3": {"kind": "mix", "control": True, "grid": False, "note": "S3cA + pass B whose reference is the S2 panel (only if S3cAB loses identity)"},
}


# --- the round config ------------------------------------------------------------------------------------------------------------

def check_round(cfg):
    """Problems of a round config ([] = fine): known rows, and not more than ONE change per row (the plan's rule, enforced here)."""
    bad = []
    for r in cfg.get("rows", []):
        if r not in ROWS:
            bad.append(f"unknown row {r}")
    seen = set()
    for c in cfg.get("changes", []):
        if c.get("row") not in cfg.get("rows", []):
            bad.append(f"change for a row that is not in the round: {c.get('row')}")
        if c.get("row") in seen:
            bad.append(f"two changes on row {c.get('row')} in one round")
        seen.add(c.get("row"))
        if c.get("cause") not in CAUSES:
            bad.append(f"change on {c.get('row')} has no known cause ({c.get('cause')})")
        if not c.get("change") or not c.get("expected"):
            bad.append(f"change on {c.get('row')} needs 'change' and 'expected'")
    if cfg.get("round", 1) > 1:
        for r in cfg.get("rows", []):
            if r not in seen:
                bad.append(f"round {cfg['round']}: row {r} has no recorded change")
    if cfg.get("round", 1) > MAX_ROUNDS:
        bad.append(f"more than {MAX_ROUNDS} rounds")
    return bad


def jobs(cfg):
    """[{row, scene, seed, shot|None, kind}] the pictures a round draws: per-shot rows one per shot, grid rows one grid per scene and seed
    (its four panels are the shots), M5 only the small moves. Round 1 of the plan: 68 pictures."""
    out = []
    for row in cfg["rows"]:
        for scene in cfg.get("scenes", SCENES):
            for seed in cfg.get("seeds", SEEDS):
                if ROWS[row]["grid"]:
                    out.append({"row": row, "scene": scene, "seed": seed, "shot": None, "kind": "grid"})
                    continue
                shots = SMALL_MOVES[scene] if row == "M5" else cfg.get("shots", SHOTS)
                out += [{"row": row, "scene": scene, "seed": seed, "shot": s, "kind": "shot"} for s in shots]
    return out


def picture_name(row, scene, seed, shot):
    return f"{row}/{scene}_{seed}_{shot}.png"


# --- our 3D code (free, before any pod) -------------------------------------------------------------------------------------------

def _s3():
    if __package__:
        from . import xworld_v2_s3 as s3
    else:
        import xworld_v2_s3 as s3
    return s3


def load_marks(scene, sets_dir=None):
    """The master's landmarks marked once by eye: {"screen_x": {object or person id: share of the picture width}}."""
    p = Path(sets_dir or PODS / "stories" / "v2" / "sets") / f"{scene}.marks.json"
    return json.loads(p.read_text(encoding="utf-8"))


def screen_x(s, ident):
    """{item id: screen x (share of the width) of its visible pixel mass in the render}, objects and people alike."""
    names = [o["id"] for o in s["objects"]] + [p["id"] for p in s["people"]]
    xs = (np.arange(ident.shape[1]) + 0.5) / ident.shape[1]
    out = {}
    for i, nm in enumerate(names):
        m = ident == i
        if m.any():
            out[nm] = float((m.sum(axis=0) * xs).sum() / m.sum())
    return out


def s0_agreement(s, marks, master_depth=None, w=320, h=180):
    """The set's s0 render against the master: {x: {id: (render, master, ok)}, spearman, ok, problems}. ``master_depth`` is the master's
    estimated inverse depth (near = high); without it only the landmark positions are checked."""
    s3 = _s3()
    ident, tmap, _ = s3.render(s, s3.camera(s, s["shots"]["s0"]), w, h)
    got = screen_x(s, ident)
    x, bad = {}, []
    for k, want in marks["screen_x"].items():
        have = got.get(k)
        ok = have is not None and abs(have - want) <= S0_X_TOL
        x[k] = (None if have is None else round(have, 3), want, ok)
        if not ok:
            bad.append(f"{s['scene']}: {k} is at screen x {None if have is None else round(have, 2)} in the render, {want} in the master")
    res = {"x": x, "spearman": None, "ok": not bad, "problems": bad}
    if master_depth is not None:
        a = s3._resize(master_depth, tmap.shape)
        res["spearman"] = s3.spearman(a, 1.0 / tmap)
        if res["spearman"] < S0_SPEARMAN_MIN:
            res["ok"] = False
            bad.append(f"{s['scene']}: depth Spearman of the s0 render vs the master is {res['spearman']:.2f}, bar {S0_SPEARMAN_MIN}")
    return res


# --- canvases --------------------------------------------------------------------------------------------------------------------

def control_canvas(depths, panel=PANEL):
    """The 2x2 control image: panel i = depth image i resized to the panel (top-left, top-right, bottom-left, bottom-right), no gutter."""
    from PIL import Image
    assert len(depths) == 4
    pw, ph = panel
    img = Image.new("RGB", (2 * pw, 2 * ph), (0, 0, 0))
    for i, d in enumerate(depths):
        img.paste(d.convert("RGB").resize((pw, ph), Image.LANCZOS), ((i % 2) * pw, (i // 2) * ph))
    return img


def inpaint_canvas(master, panel=PANEL):
    """M4: (image, mask). The master fills panel 1 (top-left), the other three are grey; the mask is white (regenerate) over panels 2-4."""
    from PIL import Image
    pw, ph = panel
    img = Image.new("RGB", (2 * pw, 2 * ph), (128, 128, 128))
    img.paste(master.convert("RGB").resize((pw, ph), Image.LANCZOS), (0, 0))
    mask = Image.new("L", (2 * pw, 2 * ph), 255)
    mask.paste(0, (0, 0, pw, ph))
    return img, mask


def panel_of(canvas, i, panel=PANEL):
    pw, ph = panel
    return canvas.crop(((i % 2) * pw, (i // 2) * ph, (i % 2 + 1) * pw, (i // 2 + 1) * ph))


def reproject(rgb, inv_depth, cam0, cam1, truth_t0, w=None, h=None):
    """M5: the master (rgb, h x w x 3) seen from camera 1. ``inv_depth`` = the estimated inverse depth of the master (near = high); its scale
    is fitted to the ray-cast distance ``truth_t0`` of the s0 render (least squares on 1/t = a*d + b), the pixels are lifted to 3-D along
    camera 0's rays and splatted (nearest wins) into camera 1. Returns (warped rgb, hole mask: True where nothing landed)."""
    s3 = _s3()
    rgb = np.asarray(rgb)
    H, W = rgb.shape[:2]
    d = s3._resize(inv_depth, (H, W)); t = s3._resize(truth_t0, (H, W))
    ok = np.isfinite(t) & np.isfinite(d)
    A = np.stack([d[ok], np.ones(ok.sum())], axis=1)
    a, b = np.linalg.lstsq(A, 1.0 / t[ok], rcond=None)[0]
    inv = np.clip(a * d + b, 1e-3, None)
    t0 = 1.0 / inv
    rays0 = s3._rays(cam0, W, H)
    pts = np.asarray(cam0["pos"], float)[None, :] + t0.reshape(-1, 1) * rays0
    f = s3._unit(np.asarray(cam1["look_at"], float) - np.asarray(cam1["pos"], float))
    right = s3._unit(np.cross(f, [0, 0, 1.0])); up = np.cross(right, f)
    v = pts - np.asarray(cam1["pos"], float)[None, :]
    zc = v @ f
    tn = math.tan(math.radians(cam1["vfov"]) / 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        u = (v @ right) / zc / (tn * W / H)
        vv = (v @ up) / zc / tn
    px = np.floor((u + 1) / 2 * W).astype(int); py = np.floor((1 - vv) / 2 * H).astype(int)
    inside = (zc > 1e-6) & (px >= 0) & (px < W) & (py >= 0) & (py < H) & np.isfinite(u) & np.isfinite(vv)
    order = np.argsort(-zc[inside])  # far first, so the near one is written last
    idx = np.nonzero(inside)[0][order]
    out = np.zeros_like(rgb); filled = np.zeros((H, W), bool)
    out[py[idx], px[idx]] = rgb.reshape(-1, rgb.shape[-1])[idx]
    filled[py[idx], px[idx]] = True
    return out, ~filled


# --- measures --------------------------------------------------------------------------------------------------------------------

def ssim(a, b, win=7):
    """Mean SSIM of two equal-size 2-D arrays (0..255), uniform window; with a mask apply it via ``plate_ssim``."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2

    def box(x):
        k = np.ones(win) / win
        x = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, x)
        return np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 0, x)

    ma, mb = box(a), box(b)
    va, vb, cov = box(a * a) - ma * ma, box(b * b) - mb * mb, box(a * b) - ma * mb
    return ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2))


def plate_ssim(pic, master, people=None, side=256):
    """SSIM of the background of ``pic`` against the master (PIL images); ``people`` = bool mask (any size) of pixels to leave out.
    A frozen plate scores near 1, a real cut below PLATE_MAX."""
    from PIL import Image

    def grey(im):
        return np.asarray(im.convert("L").resize((side, round(side * 9 / 16)), Image.LANCZOS), float)

    m = ssim(grey(pic), grey(master))
    if people is not None:
        pm = np.asarray(Image.fromarray((np.asarray(people) * 255).astype(np.uint8)).resize(m.shape[::-1])) < 128
        m = m[pm]
    return float(np.mean(m))


def order_match(expected, seen):
    """Landmark order score: the longest common subsequence of ``expected`` (left to right, from the ray cast) and ``seen`` (the VLM's list,
    same vocabulary), over the length of ``expected``; a seen item that is not in the vocabulary is ignored."""
    seen = [x for x in seen if x in expected]
    n, m = len(expected), len(seen)
    if not n:
        return None
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            L[i + 1][j + 1] = L[i][j] + 1 if expected[i] == seen[j] else max(L[i][j + 1], L[i + 1][j])
    return L[n][m] / n


def grain_ok(stats, master_stats):
    """Grain of a picture against the master's: Laplacian variance, busy share and saturation p95 each at most GRAIN_MAX x the master's."""
    return all(stats[k] <= GRAIN_MAX * master_stats[k] for k in ("lap_var", "busy", "sat_p95"))


def shot_result(row, m):
    """m = {geometry, plate, order, grain_ok, people_ok, props_ok, artifacts_ok} (None = not measured). -> {fails: [...], passed: bool}.
    A shot passes when nothing measured fails and the geometry, the plate and the grain were measured."""
    bar = CONTROL_BAR if ROWS[row]["control"] else OTHER_BAR
    fails = []
    if m.get("geometry") is not None and m["geometry"] < bar:
        fails.append("geometry")
    if m.get("plate") is not None and m["plate"] >= PLATE_MAX:
        fails.append("plate")
    if m.get("order") is not None and m["order"] < LANDMARK_MIN:
        fails.append("landmarks")
    for k, name in (("props_ok", "props"), ("artifacts_ok", "artifacts"), ("people_ok", "people"), ("grain_ok", "grain")):
        if m.get(k) is False:
            fails.append(name)
    needed = all(m.get(k) is not None for k in ("geometry", "plate", "grain_ok"))
    return {"fails": fails, "passed": needed and not fails}


def attribute(row, fails, s0_ok=True, prompt_rounds_failed=0):
    """The first matching cause of the plan's section 4 for one failure ('geometry', 'plate', 'landmarks', 'props', 'artifacts', 'people',
    'grain'), in the plan's order."""
    if not s0_ok:
        return "3d_code"
    for f in ("geometry", "plate", "landmarks", "props", "artifacts", "people", "grain"):
        if f not in fails:
            continue
        if f == "geometry":
            return "strategy_setting" if ROWS[row]["control"] else "strategy_limit"
        if f == "plate":
            return "frozen_plate"
        if f in ("landmarks", "props", "artifacts"):
            return "reference" if prompt_rounds_failed >= 2 else "prompt"
        if f == "people":
            return "identity_reference"
        return "passes"
    return None


def stop(history):
    """history = [{round, rows: {row: {seed: passed shots (of 8)}}, eye_winner: bool}, ...]. -> (verdict, why): 'success' (a row passes >= 7 of 8 shots
    on EACH seed and won the eye), 'no_progress' (3 rounds without the best row's pass count rising), 'max_rounds' or 'go_on'."""
    for h in history:
        for row, per in h["rows"].items():
            if per and all(v >= PASS_SHOTS for v in per.values()) and h.get("eye_winner") == row:
                return "success", f"{row} passes {PASS_SHOTS}+ of 8 shots on both seeds and won the eye (round {h['round']})"
    best = [max((sum(per.values()) for per in h["rows"].values()), default=0) for h in history]
    if len(best) > NO_PROGRESS_ROUNDS and max(best[-NO_PROGRESS_ROUNDS:]) <= max(best[:-NO_PROGRESS_ROUNDS]):
        return "no_progress", f"no row rose by a shot in the last {NO_PROGRESS_ROUNDS} rounds: best counts {best}"
    if len(history) >= MAX_ROUNDS:
        return "max_rounds", f"{MAX_ROUNDS} rounds done"
    return "go_on", "no stop rule applies"


def attribution_md(rnd, rows):
    """attribution.md for the Opus thread: ``rows`` = [{row, scene, seed, shot, fails, cause}] one line per failure."""
    lines = [f"# Round {rnd}: failures and their causes (plan section 4; the first matching cause wins)", "",
             "| row | scene | seed | shot | failed measure | cause |", "|---|---|---|---|---|---|"]
    for r in rows:
        for f in r["fails"] or ["-"]:
            lines.append(f"| {r['row']} | {r['scene']} | {r['seed']} | {r['shot']} | {f} | {r['cause'] or '-'} |")
    return "\n".join(lines) + "\n"


def dry(cfg, outd):
    """Round 0 for a config: refuses a bad config, lists every picture and writes <out>/jobs.json; no model."""
    bad = check_round(cfg)
    if bad:
        raise ValueError("; ".join(bad))
    j = jobs(cfg)
    Path(outd).mkdir(parents=True, exist_ok=True)
    (Path(outd) / "jobs.json").write_text(json.dumps(j, indent=1), encoding="utf-8")
    return j


if __name__ == "__main__":
    if sys.argv[1:2] == ["dry"]:
        cfg = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        print(len(dry(cfg, sys.argv[3])), "pictures")
