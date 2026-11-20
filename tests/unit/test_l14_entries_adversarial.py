"""L14 (2.5D, the living picture) tester fixtures, one negative and one compliant fixture per registry entry that has a validator (tester, 2026-11-20).

Entries and the validator each one names (``explainer_engine/governance/owner_requirements.json``):
  OR-V19a fire and smoke move   -> qa.send_validators:living_motion
  OR-V19b wind moves cloth/hair -> qa.send_validators:living_motion  (same function and the same two registry tests as V19a)
  OR-V19c snow falls with depth -> qa.send_validators:living_motion  (same)
  OR-V19e a camera move alone is not alive -> qa.liveliness:liveliness_rows
  OR-V27b no stand-in sound / camera -> qa.sound_realism:measure (sound half only)
  OR-V30a no overlay in video scenes -> overlay.rules:ov01
Judge entries (V11b, V30d, V41) are NOT_RUN here: a judge is a person or a vision model reading a rubric, not a function.

A test without a marker is a guard (true today). ``xfail(strict=True)`` is a defect: the assertion states what the owner's words need and it fails
today for the stated reason; the marker comes off in the commit that fixes it. Synthetic clips, ffmpeg, numpy: no network, $0."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.qa import liveliness as LV
from explainer_engine.qa import send_validators as V

W, H, FPS = 480, 270, 24
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
cv2 = pytest.importorskip("cv2")


# ---------------------------------------------------------------------------------------------------------------- helpers
def photo(seed: int = 5) -> np.ndarray:
    """A photograph-like still: smooth low-frequency texture plus a hard-edged block (not a blocky mosaic)."""
    rng = np.random.default_rng(seed)
    a = cv2.GaussianBlur(rng.normal(128, 50, (H, W)).astype(np.float32), (0, 0), 6)
    a = (a - a.min()) / (a.max() - a.min()) * 200 + 25
    a[100:170, 150:330] = 230
    return a.astype(np.float32)


P = photo()
N = int(3 * FPS)


def write_clip(path: Path, frames) -> Path:
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(path)],
                       input=b"".join(np.clip(f, 0, 255).astype(np.uint8).tobytes() for f in frames), capture_output=True)
    assert p.returncode == 0, p.stderr.decode()[-300:]
    return path


def zoom_frames(z: float, n: int = N):
    """A camera that only zooms: the centred zoom of a still photograph, ``z`` = total zoom (0.05 = 5 %)."""
    return [cv2.warpAffine(P, cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + z * i / n), (W, H), flags=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_REFLECT) for i in range(n)]


def pan_frames(px_per_s: float, n: int = N):
    wide = np.tile(P, (1, 3))
    return [wide[:, int(px_per_s * i / FPS) % W:int(px_per_s * i / FPS) % W + W] for i in range(n)]


def grain_frames(n: int = N, sigma: float = 25.0):
    rng = np.random.default_rng(7)
    return [P + rng.normal(0, sigma, P.shape) for _ in range(n)]


def fade_frames(n: int = N):
    return [P * (0.4 + 0.6 * i / n) for i in range(n)]


def fire_frames(area_pct: float, n: int = N):
    rng = np.random.default_rng(3)
    side = int(np.sqrt(W * H * area_pct / 100))
    out = []
    for _ in range(n):
        f = P.copy()
        f[H - side - 10:H - 10, 200:200 + side] = rng.integers(120, 255, (side, side))
        out.append(f)
    return out


def snow_frames(flakes: int, n: int = N, depth: bool = True):
    """Falling flakes over the still photo. ``depth``: near flakes (large z) are bigger and faster; else all alike."""
    rng = np.random.default_rng(11)
    x, y, z = rng.uniform(0, W, flakes), rng.uniform(0, H, flakes), rng.uniform(0, 1, flakes)
    size = (1 + 3 * z).astype(int) if depth else np.full(flakes, 2)
    vy = (20 + 80 * z) if depth else np.full(flakes, 50.0)
    out = []
    for i in range(n):
        f = P.copy()
        yy = (y + vy * i / FPS) % (H - 5)
        for k in range(flakes):
            f[int(yy[k]):int(yy[k]) + size[k], int(x[k]):int(x[k]) + size[k]] = 250
        out.append(f)
    return out


def wind_frames(n: int = N):
    """Grass: the lower band sways sideways, a still camera."""
    out = []
    for i in range(n):
        f = P.copy()
        for r in range(180, H):
            f[r] = np.roll(P[r], int(4 * np.sin(2 * np.pi * (i / FPS * 1.5 + r / 20))))
        out.append(f)
    return out


def proper_frames(n: int = N):
    """A compliant living picture: smoke turbulence in a zone, wind in the grass band, snow with depth, a still camera."""
    rng = np.random.default_rng(2)
    snow = snow_frames(300, n, depth=True)
    wind = wind_frames(n)
    out = []
    for i in range(n):
        f = snow[i].copy()
        f[180:, :] = wind[i][180:, :]
        f[40:150, 60:300] = np.clip(f[40:150, 60:300] + rng.normal(0, 30, (110, 240)), 0, 255)
        out.append(f)
    return out


def living(tmp_path: Path, name: str, frames) -> dict:
    return V.living_motion(write_clip(tmp_path / f"{name}.mp4", frames))


def rows_of(frames) -> dict:
    fr3 = [np.repeat(np.clip(f, 0, 255).astype(np.uint8)[..., None], 3, 2) for f in frames]
    rs, m = LV.liveliness_rows(fr3, float(FPS))
    return {"rows": {r["gate"]: r["status"] for r in rs}, "m": m}


# ===================================================================================== OR-V19a / V19b / V19c: living_motion (v2, BP-215)
from PIL import Image  # noqa: E402

ZONE_SKY = ("sky", "sky", (0, 0, 480, 40))
ZONE_SMOKE = ("smoke", "smoke", (60, 60, 260, 200))
ZONE_FIRE = ("fire", "fire", (300, 200, 400, 260))
FULL = lambda kind: ("all", kind, (0, 0, W, H))      # noqa: E731  a zone mask covering the whole frame


def zones_for(clip_path: Path, zones, extra=None) -> None:
    """``<clip>.zones.json`` + masks beside the clip; ``zones`` = [(name, kind, (x0, y0, x1, y1))]."""
    rows = []
    for zn, kind, (x0, y0, x1, y1) in zones:
        m = np.zeros((H, W), np.uint8)
        m[y0:y1, x0:x1] = 255
        Image.fromarray(m).save(clip_path.parent / f"{clip_path.stem}_{zn}.png")
        rows.append({"name": zn, "kind": kind, "mask": f"{clip_path.stem}_{zn}.png"})
    clip_path.with_suffix(".zones.json").write_text(json.dumps(dict({"zones": rows}, **(extra or {}))), encoding="utf-8")


def with_zones(tmp_path: Path, name: str, frames, zones, extra=None) -> dict:
    p = write_clip(tmp_path / f"{name}.mp4", frames)
    zones_for(p, zones, extra)
    return V.living_motion(p)


def noise_patch_frames(box, sigma: float, n: int = N):
    """The lazy generator's trick: per-frame random noise inside the declared zone, nothing moves coherently."""
    rng = np.random.default_rng(21)
    x0, y0, x1, y1 = box
    out = []
    for _ in range(n):
        f = P.copy()
        f[y0:y1, x0:x1] = np.clip(f[y0:y1, x0:x1] + rng.normal(0, sigma, (y1 - y0, x1 - x0)), 0, 255)
        out.append(f)
    return out


def pulse_frames(amp: float, hz: float, n: int = N):
    return [np.clip(P * (1 + amp * np.sin(2 * np.pi * hz * i / FPS)), 0, 255) for i in range(n)]


def smooth_pan_frames(px_per_s: float, sigma: float, n: int = N):
    a = cv2.GaussianBlur(np.random.default_rng(5).normal(128, 50, (H, W * 3)).astype(np.float32), (0, 0), sigma)
    a = (a - a.min()) / (a.max() - a.min()) * 200 + 25
    return [a[:, int(px_per_s * i / FPS):int(px_per_s * i / FPS) + W] for i in range(n)]


def alive_world(tmp_path: Path, name: str = "alive", draw_over=None) -> Path:
    """The compliant world: a still camera, sky, smoke and fire textures drift by themselves (the developer's own compliant shape)."""
    rng = np.random.default_rng(2)
    base = np.tile(np.clip(np.kron(rng.integers(40, 200, (27, 48)), np.ones((10, 10))), 0, 255).astype(np.float32), (1, 2))
    tex = np.clip(np.kron(np.random.default_rng(8).integers(30, 220, (27, 96)), np.ones((10, 10))), 0, 255).astype(np.float32)
    areas = (((slice(0, 40), slice(0, W)), 0.5), ((slice(60, 200), slice(60, 260)), 0.7), ((slice(200, 260), slice(300, 400)), 1.5))
    frames = []
    for i in range(N):
        f = base[:, :W].copy()
        for (ys, xs), speed in areas:
            sh = int(round(speed * i)) % 300
            f[ys, xs] = tex[ys, xs.start + sh:xs.stop + sh]
        if draw_over is not None:
            f = np.where(draw_over[min(i, len(draw_over) - 1)] > 0, 255, f)
        frames.append(f)
    return write_clip(tmp_path / f"{name}.mp4", frames)


def flake_matte(left_too: bool, n: int = N):
    """Far flakes (200 of 3x3 px): over the right half only, or over the left half (the soldiers) too."""
    rng = np.random.default_rng(5)
    lo = 0 if left_too else W // 2
    x0, y0 = rng.integers(lo, W - 3, 200), rng.integers(0, H, 200)
    out = []
    for i in range(n):
        m = np.zeros((H, W), np.float32)
        for x, y in zip(x0, (y0 + 1.5 * i * 24 / FPS) % (H - 3)):
            m[int(y):int(y) + 3, x:x + 3] = 255
        out.append(m)
    return out


def occlusion(tmp_path: Path, drawn_left: bool, declared_left: bool, flat_depth: bool = False, declare: bool = True) -> dict:
    """The delivered clip has flakes drawn over the world (right half, or the soldiers' left half too); the sidecar declares a far-particle matte and a
    depth map (near half = left)."""
    p = alive_world(tmp_path, "occ", draw_over=flake_matte(drawn_left))
    write_clip(tmp_path / "far.mp4", flake_matte(declared_left))
    depth = np.zeros((H, W), np.uint8)
    depth[:, :W // 2], depth[:, W // 2:] = 230, 40
    if flat_depth:
        depth[:] = 40
    Image.fromarray(depth).save(tmp_path / "depth.png")
    zones_for(p, [ZONE_SKY, ZONE_SMOKE, ZONE_FIRE], {"particles": {"far": "far.mp4"}, "depth": "depth.png"} if declare else None)
    return V.living_motion(p)


# ---- guards: what living_motion v2 does right today
@needs_ffmpeg
def test_V19_a_compliant_world_with_its_zones_passes_with_its_numbers(tmp_path):
    p = alive_world(tmp_path)
    zones_for(p, [ZONE_SKY, ZONE_SMOKE, ZONE_FIRE])
    r = V.living_motion(p)
    assert r["status"] == "PASS" and r["value"] >= V.ZONE_COVER_MIN, r
    assert all(k in r["detail"] for k in ("sky ", "smoke ", "fire "))


@needs_ffmpeg
@pytest.mark.parametrize("pct", [1, 4, 8])
def test_V19a_only_the_fire_moves_fails_at_every_flame_size(tmp_path, pct):
    r = living(tmp_path, f"fire{pct}", fire_frames(pct))
    assert r["status"] == "FAIL", r


@needs_ffmpeg
def test_V19_a_still_photograph_fails_by_the_cheap_guard(tmp_path):
    r = living(tmp_path, "static", [P.copy() for _ in range(N)])
    assert r["status"] == "FAIL" and r["value"] == 0.0 and "G-LIVE-1" in r["detail"], r


@needs_ffmpeg
@pytest.mark.parametrize("zoom", [0.05, 0.12])
def test_V19e_a_zoom_alone_fails_with_the_camera_taken_out(tmp_path, zoom):
    r = living(tmp_path, f"zoom{zoom}", zoom_frames(zoom))
    assert r["status"] == "FAIL" and "camera" in r["detail"], r


@needs_ffmpeg
@pytest.mark.parametrize("px_per_s,sigma", [(6, 6), (10, 6), (20, 3), (40, 3), (20, 1.5), (40, 0.8)])
def test_V19e_a_pan_alone_fails_on_a_textured_picture(tmp_path, px_per_s, sigma):
    r = living(tmp_path, f"pan{px_per_s}_{sigma}", smooth_pan_frames(px_per_s, sigma))
    assert r["status"] == "FAIL", r


@needs_ffmpeg
def test_V19_a_brightness_fade_alone_fails(tmp_path):
    assert living(tmp_path, "fade", fade_frames())["status"] == "FAIL"


@needs_ffmpeg
@pytest.mark.parametrize("zoom", [0.05])
def test_V19e_a_zoom_alone_fails_even_with_a_whole_frame_zone(tmp_path, zoom):
    r = with_zones(tmp_path, "zoomzone", zoom_frames(zoom), [FULL("sky")])
    assert r["status"] == "FAIL" and "G-LIVE-3" in r["detail"], r


@needs_ffmpeg
def test_V19_a_dead_picture_fails_even_with_a_whole_frame_zone(tmp_path):
    assert with_zones(tmp_path, "deadzone", [P.copy() for _ in range(N)], [FULL("sky")])["status"] == "FAIL"


@needs_ffmpeg
def test_V19_a_fade_inside_a_declared_smoke_zone_fails(tmp_path):
    assert with_zones(tmp_path, "fadezone", fade_frames(), [ZONE_SMOKE])["status"] == "FAIL"


@needs_ffmpeg
def test_V19a_a_flat_patch_that_only_changes_brightness_fails_in_the_smoke_zone(tmp_path):
    rng = np.random.default_rng(1)
    frames = []
    for _ in range(N):
        f = P.copy()
        f[60:200, 60:260] = rng.integers(60, 255)
        frames.append(f)
    assert with_zones(tmp_path, "flatflicker", frames, [ZONE_SMOKE])["status"] == "FAIL"


@needs_ffmpeg
@pytest.mark.parametrize("name,frames", [("grain", grain_frames()), ("snow1500", snow_frames(1500)), ("snow1500_flat", snow_frames(1500, depth=False))])
def test_V19_noise_and_dense_snow_are_never_a_pass(tmp_path, name, frames):
    assert living(tmp_path, name, frames)["status"] != "PASS"


@needs_ffmpeg
def test_V19b_wind_swaying_a_band_of_grass_passes_without_zones(tmp_path):
    r = living(tmp_path, "wind", wind_frames())
    assert r["status"] == "PASS", r


@needs_ffmpeg
def test_V19c_far_flakes_hidden_behind_the_foreground_pass_and_drawn_over_it_fail(tmp_path):
    ok_dir, bad_dir = tmp_path / "ok", tmp_path / "bad"
    ok_dir.mkdir()
    bad_dir.mkdir()
    ok = occlusion(ok_dir, False, False)
    bad = occlusion(bad_dir, True, True)
    assert ok["status"] == "PASS" and "far particles over the foreground 0.00 %" in ok["detail"], ok
    assert bad["status"] == "FAIL" and "does not hide them" in bad["detail"], bad


def test_V19_the_registry_binds_all_three_to_the_one_function():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    by = {e["id"]: e for e in reg["requirements"]}
    assert {by[i]["check"]["ref"] for i in ("OR-V19a", "OR-V19b", "OR-V19c")} == {"explainer_engine.qa.send_validators:living_motion"}


# ---- defects: each is a way the check is passed (or skipped) by a clip the owner's words reject
@needs_ffmpeg
@pytest.mark.parametrize("zone,box,sigma", [(ZONE_SMOKE, (60, 60, 260, 200), 25), (ZONE_SMOKE, (60, 60, 260, 200), 15), (ZONE_SKY, (0, 0, 480, 40), 40)])
@pytest.mark.xfail(strict=True, reason="V19a/Z1 (gaming): per-frame random noise inside the declared zone is read by Farneback as 46-87 % of the zone 'moving' "
                                       "(BP-215 needs 25 %): a lazy generator declares a zone and flickers noise in it; nothing moves coherently")
def test_Z1_noise_flickering_inside_a_declared_zone_is_not_a_pass(tmp_path, zone, box, sigma):
    assert with_zones(tmp_path, "noisezone", noise_patch_frames(box, sigma), [zone])["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.parametrize("hz", [0.5, 1.3])
@pytest.mark.xfail(strict=True, reason="V19/Z2 (gaming): a global brightness pulse (25 % amplitude) PASSes with no zones and measures 32-68 % 'moving'; "
                                       "a pulse of the whole picture is not motion (a monotone fade fails, a sinusoid does not)")
def test_Z2_a_global_brightness_pulse_is_not_a_pass(tmp_path, hz):
    assert living(tmp_path, "pulse", pulse_frames(0.25, hz))["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19/Z2b (gaming): the same pulse with a smoke zone declared over it PASSes too (32 % of the zone 'moves')")
def test_Z2b_a_global_pulse_with_a_declared_zone_is_not_a_pass(tmp_path):
    assert with_zones(tmp_path, "pulsezone", pulse_frames(0.25, 1.3), [ZONE_SMOKE])["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19e/Z3: a 20 px/s pan of a very smooth (blur sigma 6, fog/sky-like) picture PASSes: the similarity fit leaves 28-37 % of "
                                       "the frame 'moving' once the camera is out; on any texture with sigma <= 3 the same pan FAILs correctly (guards above)")
def test_Z3_a_camera_pan_of_a_low_texture_picture_is_not_a_pass(tmp_path):
    assert living(tmp_path, "smoothpan", smooth_pan_frames(20, 6))["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.parametrize("flakes", [800, 1500])
@pytest.mark.xfail(strict=True, reason="V19c/Z4: a snow-only clip (still camera, dead picture) is NOT_RUN ('camera could not be separated', 5-11 % inliers), "
                                       "not FAIL; BP-215 says snow alone cannot pass, and NOT_RUN is what the send gate releases today (S1, lead's open decision)")
def test_Z4_a_snow_only_clip_is_a_fail_not_a_not_run(tmp_path, flakes):
    assert living(tmp_path, f"snow{flakes}", snow_frames(flakes))["status"] == "FAIL"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19c/Z5: the far-particle matte is declared by the sidecar, never compared with the delivered clip: flakes drawn over "
                                       "the soldiers while the matte lists only right-half flakes PASS ('far particles over the foreground 0.00 %')")
def test_Z5_flakes_drawn_over_the_soldiers_with_a_matte_that_says_otherwise_do_not_pass(tmp_path):
    assert occlusion(tmp_path, drawn_left=True, declared_left=False)["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19c/Z6: a flat depth map (nothing is foreground) makes 'over the foreground' 0 % for any flake; the check passes "
                                       "flakes drawn over the soldiers with an honest matte")
def test_Z6_a_flat_depth_map_does_not_prove_the_occlusion(tmp_path):
    assert occlusion(tmp_path, drawn_left=True, declared_left=True, flat_depth=True)["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19c/Z7: no `particles` block in the sidecar is 'no particle layer declared' = PASS; flakes drawn over the soldiers and not "
                                       "declared are never looked at (design question for the lead: undeclared snow should be NOT_RUN, not PASS)")
def test_Z7_snow_drawn_over_the_soldiers_without_a_declared_layer_is_not_a_pass(tmp_path):
    assert occlusion(tmp_path, drawn_left=True, declared_left=True, declare=False)["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19b: wind has no measure of its own: the registered compliant and negative tests of V19a, V19b and V19c are the same two "
                                       "nodes, so nothing in the registered proof is about wind (V19b) or snow depth (V19c)")
def test_Z8_each_of_v19a_v19b_v19c_has_its_own_compliant_and_negative_test():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    by = {e["id"]: e["check"] for e in reg["requirements"]}
    tests = [(by[i]["test"], by[i]["negative_test"]) for i in ("OR-V19a", "OR-V19b", "OR-V19c")]
    assert len(set(tests)) == 3, tests


# ===================================================================================== OR-V19e: liveliness_rows
def test_V19e_a_camera_move_alone_is_not_alive_beyond_the_camera_at_every_amount():
    for z in (0.05, 0.12, 0.25):
        out = rows_of(zoom_frames(z))
        assert out["rows"]["alive_beyond_camera"] == "REVIEW", (z, out)
        assert out["m"]["local"]["pct_per_s"] < LV.LOCAL_FLOOR


def test_V19e_a_still_picture_is_review_on_all_three_rows():
    out = rows_of([P.copy() for _ in range(N)])
    assert set(out["rows"].values()) == {"REVIEW"}, out


def test_V19e_a_moving_blob_on_a_still_camera_passes_all_rows():
    frames = []
    for i in range(N):
        f = P.copy()
        cv2.circle(f, (int(60 + 120 * i / N * 3), 135), 45, 255, -1)
        frames.append(f)
    out = rows_of(frames)
    assert out["rows"]["no_frozen_second"] == "PASS" and out["rows"]["alive_beyond_camera"] == "PASS", out


def test_V19e_the_rows_are_review_not_fail_so_they_wait_for_the_director_never_block():
    out = rows_of(zoom_frames(0.12))
    assert "FAIL" not in out["rows"].values()


@pytest.mark.xfail(strict=True, reason="V19e/Z9: the camera is taken out by a similarity warp, but a brightness fade is not a camera: a fade alone measures "
                                       "10 % local change and PASSes alive_beyond_camera")
def test_Z9_a_fade_is_not_alive_beyond_the_camera():
    assert rows_of(fade_frames())["rows"]["alive_beyond_camera"] != "PASS"


@pytest.mark.xfail(strict=True, reason="V19e/Z10: per-frame grain passes alive_beyond_camera (2.7 %/s local change)")
def test_Z10_grain_is_not_alive_beyond_the_camera():
    assert rows_of(grain_frames())["rows"]["alive_beyond_camera"] != "PASS"


@pytest.mark.xfail(strict=True, reason="V19e has no send_ref and liveliness_rows takes decoded frames, not a path: the send gate cannot run it, so a clip "
                                       "that is only a zoom reaches the owner with living_motion NOT_RUN and V19e never measured")
def test_Z11_the_camera_only_check_is_wired_to_the_send_gate():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    chk = {e["id"]: e["check"] for e in reg["requirements"]}["OR-V19e"]
    assert chk.get("send_ref"), chk


# ===================================================================================== OR-V27b: sound_realism.measure
from explainer_engine.qa import sound_realism as SRZ  # noqa: E402

SR_HZ = SRZ.SR


def db_to(x: np.ndarray, dbfs: float) -> np.ndarray:
    return (x * 10 ** ((dbfs - SRZ.db(float(np.sqrt(np.mean(x ** 2))))) / 20)).astype(np.float32)


def hiss_places(gains, seeds=(1, 2, 3)):
    """Three places, each a different seed of WHITE noise (numpy hiss), at the given levels: one stand-in noise under every place."""
    parts, places, t = [], [], 0.0
    for k, g in enumerate(gains):
        x = np.random.default_rng(seeds[k]).standard_normal(int(4 * SR_HZ)).astype(np.float32)
        parts.append(db_to(x, g))
        places.append({"start_s": t, "end_s": t + 4.0, "place": f"p{k}"})
        t += 4.0
    return np.concatenate(parts), {"cuts": [4.0, 8.0], "events": [], "places": places}


def real_places():
    from test_sound_realism import three_places
    return three_places(same=False)


def srow(rep, gate):
    return {r["gate"]: r["status"] for r in rep["rows"]}[gate]


def test_V27b_numpy_hiss_under_every_place_fails_and_distinct_beds_pass():
    x, tl = hiss_places((-35, -35, -35))
    assert srow(SRZ.measure(Path("synthetic"), tl, x=x), "not_one_noise_everywhere") == "FAIL"
    x, tl = real_places()
    assert srow(SRZ.measure(Path("synthetic"), tl, x=x), "not_one_noise_everywhere") == "PASS"


def test_V27b_one_place_or_no_timeline_is_not_run_never_a_pass():
    x, tl = hiss_places((-35,))
    assert srow(SRZ.measure(Path("synthetic"), tl, x=x), "not_one_noise_everywhere") == "NOT_RUN"
    x, tl = real_places()
    assert srow(SRZ.measure(Path("synthetic"), None, x=x), "not_one_noise_everywhere") == "NOT_RUN"


def test_V27b_digital_silence_between_lines_fails():
    from test_sound_realism import dialogue
    x, tl = dialogue(1.5, with_bed=False)
    rep = SRZ.measure(Path("synthetic"), tl, x=x)
    assert "FAIL" in {r["status"] for r in rep["rows"] if r["gate"] in ("no_dropout", "dialogue_never_dead")}


@pytest.mark.xfail(strict=True, reason="V27b/Z12: the same white hiss at three different levels under three places is still ONE stand-in noise, but the row says "
                                       "NOT_RUN (the level differences make other rows fail first) instead of FAIL")
def test_Z12_the_same_hiss_at_different_levels_is_still_one_noise():
    x, tl = hiss_places((-30, -38, -45))
    assert srow(SRZ.measure(Path("synthetic"), tl, x=x), "not_one_noise_everywhere") == "FAIL"


@pytest.mark.xfail(strict=True, reason="V27b/Z13: the registry text says no stand-in sound AND no stand-in camera move; only the sound half has a validator "
                                       "(the entry's own note: 'camera half stays unmapped'); there is no field for a second check, so the camera half is "
                                       "invisible to the registry and to CI")
def test_Z13_the_camera_half_of_v27b_has_a_check_of_its_own():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    e = {x["id"]: x for x in reg["requirements"]}["OR-V27b"]
    assert "camera half stays unmapped" not in json.dumps(e["check"]), e["check"]


@pytest.mark.xfail(strict=True, reason="V27b has no negative_test field (REQ-NONEGATIVE in ci_check, soft mode hides it) and no send_ref: measure() takes samples "
                                       "or a path plus a timeline the director supplies, so the send gate cannot run it on a candidate")
def test_Z14_v27b_names_a_negative_test():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    assert {x["id"]: x for x in reg["requirements"]}["OR-V27b"]["check"].get("negative_test")


# ===================================================================================== OR-V30a: overlay.rules.ov01
from explainer_engine.overlay import rules as OVR  # noqa: E402


def ov_ctx(route: str, items=(), panels=(), reason=None):
    spec = {"items": list(items), "panels": list(panels), "frames": 240, "words": [], "mode": "accent"}
    if reason:
        spec["overlay_reason"] = reason
    return OVR.Ctx(spec, {"route": route}, None, None, {}, None)


ITEM = {"id": "i1", "kind": "label", "start": 20, "end": 120}


def test_V30a_an_overlay_on_an_ltx_shot_fails_and_a_clean_ltx_shot_passes():
    assert OVR.ov01(ov_ctx("ltx", items=[ITEM]))["status"] == OVR.FAIL
    assert OVR.ov01(ov_ctx("ltx", panels=[{"id": "p1", "start": 20, "end": 120}]))["status"] == OVR.FAIL
    assert OVR.ov01(ov_ctx("ltx"))["status"] == OVR.PASS


@pytest.mark.parametrize("route", ["map_action", "still_25d"])
def test_V30a_other_routes_are_not_applicable(route):
    assert OVR.ov01(ov_ctx(route, items=[ITEM]))["status"] == OVR.NA


@pytest.mark.parametrize("route", ["video", "wan"])
@pytest.mark.xfail(strict=True, reason="V30a/Z15: ov01 and ov03 test `route != 'ltx'`; since D-132/D-137 a v4.3 shot's route is `video` (the D-131 name `wan` "
                                       "reads as `video`, `episode/router.LEGACY_ROUTES`), so an overlay on a v4.3 video shot is NOT_APPLICABLE and the owner's "
                                       "rule 'forbidden in video scenes' never fires on a shot the current router produces")
def test_Z15_an_overlay_on_a_v43_video_shot_fails(route):
    assert OVR.ov01(ov_ctx(route, items=[ITEM]))["status"] == OVR.FAIL


@pytest.mark.parametrize("route", ["video", "wan"])
@pytest.mark.xfail(strict=True, reason="V30a/Z15: the same blind spot in ov03 (overlay_reason on a video shot)")
def test_Z15_an_overlay_reason_on_a_v43_video_shot_fails(route):
    assert OVR.ov03(ov_ctx(route, reason="mood"))["status"] == OVR.FAIL


@pytest.mark.xfail(strict=True, reason="V30a: the registered test names no `ov01` (REQ-NOTEST in ci_check, hidden by the soft mode) and the entry has no negative_test")
def test_Z16_v30a_names_a_test_that_calls_ov01_and_a_negative_test():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    chk = {x["id"]: x for x in reg["requirements"]}["OR-V30a"]["check"]
    body = (Path(__file__).resolve().parents[2] / chk["test"].split("::")[0]).read_text(encoding="utf-8")
    assert "ov01" in body.split(chk["test"].split("::")[1])[1].split("\ndef ")[0] and chk.get("negative_test")


# ===================================================================================== judges and unmapped entries: NOT_RUN
@pytest.mark.parametrize("entry,anchor", [("OR-V11b", "j-seen-defects"), ("OR-V30d", "j-style-unity"), ("OR-V41", "j-25d-moves")])
def test_judge_entries_name_a_rubric_heading_that_exists_but_are_not_run_by_code(entry, anchor):
    root = Path(__file__).resolve().parents[2]
    reg = json.loads((root / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    chk = {e["id"]: e["check"] for e in reg["requirements"]}[entry]
    assert chk["kind"] == "judge" and chk["rubric"].endswith("#" + anchor), chk
    text = (root / chk["rubric"].split("#")[0]).read_text(encoding="utf-8").lower()
    assert anchor in text.replace(" ", "-") or anchor in text, f"{anchor} not found in the rubric file"
