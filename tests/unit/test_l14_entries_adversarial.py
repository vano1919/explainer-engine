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


# ===================================================================================== OR-V19a / V19b / V19c: living_motion
# ---- guards: what the validator does right today
@needs_ffmpeg
def test_V19_a_compliant_living_picture_passes(tmp_path):
    r = living(tmp_path, "proper", proper_frames())
    assert r["status"] == "PASS" and r["value"] >= LV.FROZEN_CHANGE, r


@needs_ffmpeg
@pytest.mark.parametrize("pct", [1, 4])
def test_V19a_only_the_fire_moves_fails_for_a_small_flame(tmp_path, pct):
    r = living(tmp_path, f"fire{pct}", fire_frames(pct))
    assert r["status"] == "FAIL" and "G-LIVE-1" in r["detail"], r


@needs_ffmpeg
def test_V19_a_still_photograph_fails(tmp_path):
    r = living(tmp_path, "static", [P.copy() for _ in range(N)])
    assert r["status"] == "FAIL" and r["value"] == 0.0, r


@needs_ffmpeg
@pytest.mark.parametrize("px_per_s", [4, 20, 60])
def test_V19e_a_pan_is_not_run_never_a_pass(tmp_path, px_per_s):
    r = living(tmp_path, f"pan{px_per_s}", pan_frames(px_per_s))
    assert r["status"] == "NOT_RUN" and "camera moves" in r["detail"], r


@needs_ffmpeg
@pytest.mark.parametrize("zoom", [0.10, 0.20])
def test_V19e_a_fast_zoom_is_not_run_never_a_pass(tmp_path, zoom):
    assert living(tmp_path, f"zoom{zoom}", zoom_frames(zoom))["status"] == "NOT_RUN"


@needs_ffmpeg
def test_V19a_a_named_smoke_zone_that_does_not_move_fails_even_when_the_rest_moves(tmp_path):
    from PIL import Image
    frames = wind_frames()
    frames = [f.copy() for f in frames]
    rng = np.random.default_rng(4)
    for f in frames:                                         # also churn the lower half so the whole-frame floor is met
        f[150:260, 20:460] = np.clip(f[150:260, 20:460] + rng.normal(0, 40, (110, 440)), 0, 255)
    p = write_clip(tmp_path / "zoned.mp4", frames)
    m = np.zeros((H, W), np.uint8)
    m[20:80, 100:300] = 255                                  # "smoke" over a region that never changes
    Image.fromarray(m).save(tmp_path / "smoke.png")
    (tmp_path / "zoned.zones.json").write_text(json.dumps({"zones": [{"name": "smoke", "mask": "smoke.png"}]}), encoding="utf-8")
    r = V.living_motion(p)
    assert r["status"] == "FAIL" and "G-LIVE-3" in r["detail"], r


def test_V19_the_registry_binds_all_three_to_the_one_function():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    by = {e["id"]: e for e in reg["requirements"]}
    assert {by[i]["check"]["ref"] for i in ("OR-V19a", "OR-V19b", "OR-V19c")} == {"explainer_engine.qa.send_validators:living_motion"}


# ---- defects: the validator passes, or does not judge, what the owner's words reject
@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19e/Z1: a slow CENTRED zoom has zero translation, so the still-camera test (phase correlation) calls the camera still, and "
                                       "the zoom itself is counted as the world moving: 5 % zoom over 3 s measures 13.7 % change and PASSes 'it is just a zoom' (the owner's own words)")
def test_Z1_a_slow_zoom_alone_is_not_a_pass(tmp_path):
    assert living(tmp_path, "zoom5", zoom_frames(0.05))["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="Z2: per-frame film grain changes 70 % of the pixels, nothing moves; whole-frame change cannot tell noise from motion "
                                       "(the validator's own 'smoke' fixture is gaussian noise)")
def test_Z2_film_grain_alone_is_not_a_pass(tmp_path):
    assert living(tmp_path, "grain", grain_frames())["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="Z3: a brightness fade changes 98 % of the pixels; a fade is a transition, not motion, yet it PASSes G-LIVE-1")
def test_Z3_a_brightness_fade_alone_is_not_a_pass(tmp_path):
    assert living(tmp_path, "fade", fade_frames())["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.parametrize("flakes", [1500, 3000])
@pytest.mark.xfail(strict=True, reason="V19c/Z4: dense snow on a still camera is read as 'the camera moves' (the falling flakes dominate the phase correlation, "
                                       "50-98 px/s) and the clip is NOT_RUN: snow, the very effect V19c is about, switches the check off; and it can never PASS "
                                       "(sparse snow is under the 5 % floor and FAILs), so V19c cannot be proven by snow at all")
def test_Z4_falling_snow_is_not_mistaken_for_a_moving_camera(tmp_path, flakes):
    r = living(tmp_path, f"snow{flakes}", snow_frames(flakes))
    assert "camera moves" not in r["detail"], r


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19c/Z5: snow depth ('near flakes larger and faster than far') is not measured anywhere; a snow clip whose flakes are all "
                                       "alike gets the same verdict as one with depth (here: both NOT_RUN)")
def test_Z5_snow_with_depth_and_snow_without_depth_are_told_apart(tmp_path):
    a = living(tmp_path, "snow_depth", snow_frames(1500, depth=True))
    b = living(tmp_path, "snow_flat", snow_frames(1500, depth=False))
    assert a["status"] == "PASS" and b["status"] == "FAIL", (a, b)


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="V19b: wind has no measure; the registry's compliant and negative tests for V19b are the smoke fixture and the small-flame "
                                       "fixture shared with V19a/V19c, so nothing in the registered proof is about wind (a wind-only clip passes only because "
                                       "a band of pixels changes)")
def test_Z6_each_of_v19a_v19b_v19c_has_its_own_compliant_and_negative_test():
    reg = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine/governance/owner_requirements.json").read_text(encoding="utf-8"))
    by = {e["id"]: e["check"] for e in reg["requirements"]}
    tests = [(by[i]["test"], by[i]["negative_test"]) for i in ("OR-V19a", "OR-V19b", "OR-V19c")]
    assert len(set(tests)) == 3, tests


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="Z7: without a .zones.json the zone rule (G-LIVE-3) is skipped and 'only the fire moves' is judged by area alone: a flame "
                                       "covering 8 % of the frame PASSes with no smoke, wind or snow anywhere")
def test_Z7_a_big_flame_alone_without_a_zones_file_is_not_a_pass(tmp_path):
    assert living(tmp_path, "bigfire", fire_frames(8))["status"] != "PASS"


@needs_ffmpeg
@pytest.mark.xfail(strict=True, reason="Z8: a one-second flicker (period of exactly the 1 s window) is invisible to a window that compares frames 1 s apart; "
                                       "an all-frame luminance pulse measures 0.0 % and FAILs: the right verdict for the wrong reason (nothing else moves), "
                                       "but the same pulse with a moving world inside would be measured as if it did not pulse; recorded as a window-aliasing limit")
def test_Z8_the_window_does_not_alias_with_a_one_second_period(tmp_path):
    pulse = [np.clip(P * (1 + 0.25 * np.sin(2 * np.pi * 1.0 * i / FPS)), 0, 255) for i in range(N)]
    r = living(tmp_path, "pulse", pulse)
    assert r["value"] is not None and r["value"] > 0.0, r


# ===================================================================================== OR-V19e: liveliness_rows
def test_V19e_a_camera_move_alone_is_not_alive_beyond_the_camera_at_every_amount():
    for z in (0.05, 0.12, 0.25):
        out = rows_of(zoom_frames(z))
        assert out["rows"]["alive_beyond_camera"] == "REVIEW", (z, out)
        assert out["m"]["local"]["pct_per_s"] < LV.LOCAL_FLOOR


def test_V19e_a_still_picture_is_review_on_all_three_rows():
    out = rows_of([P.copy() for _ in range(N)])
    assert set(out["rows"].values()) == {"REVIEW"}, out


def test_V19e_a_living_picture_passes_the_row():
    out = rows_of(proper_frames())
    assert out["rows"]["alive_beyond_camera"] in ("PASS", "REVIEW")           # recorded: see the numbers below
    assert out["rows"]["no_frozen_second"] == "PASS", out


def test_V19e_a_moving_blob_on_a_still_camera_passes_all_rows():
    frames = []
    for i in range(N):
        f = P.copy()
        cv2.circle(f, (int(60 + 120 * i / N * 3), 135), 45, 255, -1)
        frames.append(f)
    out = rows_of(frames)
    assert out["rows"]["no_frozen_second"] == "PASS" and out["rows"]["alive_beyond_camera"] == "PASS", out


def test_V19e_the_rows_are_review_not_fail_so_they_wait_for_the_director_never_block():
    from explainer_engine.governance import layer_gate  # noqa: F401  (imported: the row level is the registry's, G.REVIEW)
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
