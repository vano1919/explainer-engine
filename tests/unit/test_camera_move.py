"""Tests for VAL-CAMERA-MOVE from TASK_VAL_CAMERA_MOVE.md section 7.
Needs cv2 + ffmpeg for the clip tests (skipped otherwise). Synthetic clips: seeded texture + known affine per frame."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
from explainer_engine.qa import camera_move as M

TEST_TOL = HERE.parent / "fixtures" / "camera_move" / "tolerances_TESTONLY.json"  # placeholder floors, NOT repo numbers


@pytest.fixture(autouse=True)
def _test_floors(monkeypatch):
    monkeypatch.setenv("CAMERA_MOVE_TOLERANCES", str(TEST_TOL))

try:
    import cv2, numpy as np
    HAVE = shutil.which("ffmpeg") is not None
except Exception:  # pragma: no cover
    HAVE = False
clip_only = pytest.mark.skipif(not HAVE, reason="needs cv2 + ffmpeg")

W, H, FPS, N = 480, 270, 24, 48


def texture():
    rng = np.random.RandomState(7)
    base = cv2.GaussianBlur(rng.randint(0, 255, (H * 2, W * 2), dtype=np.uint8), (0, 0), 3)
    img = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
    for _ in range(60):
        x, y = rng.randint(0, W * 2 - 40), rng.randint(0, H * 2 - 40)
        cv2.rectangle(img, (x, y), (x + rng.randint(10, 40), y + rng.randint(10, 40)), tuple(int(v) for v in rng.randint(0, 255, 3)), -1)
    return img


def make_clip(tmp_path, name, tx_pct=0.0, zoom_pct=0.0, rot_deg=0.0, easing="linear"):
    tex = texture()
    d = tmp_path / name; d.mkdir()
    for i in range(N):
        p = i / (N - 1)
        if easing == "ease":
            p = p * p * (3 - 2 * p)
        s = 1.0 + zoom_pct / 100.0 * p
        M_ = cv2.getRotationMatrix2D((W, H), rot_deg * p, s)  # about the texture centre
        M_[0, 2] += tx_pct / 100.0 * W * p
        crop = cv2.warpAffine(tex, M_, (W * 2, H * 2), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        cv2.imwrite(str(d / f"f{i:03d}.png"), crop[H // 2: H // 2 + H, W // 2: W // 2 + W])
    out = tmp_path / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(d / "f%03d.png"),
                    "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def rules(f, r):
    return [x for x in f if x["rule"] == r]


# ---------------- card tests ----------------
NARR = "All along the line of men the snow fell, and he decided to stay."
WHY = '"all along the line" -> a line of men'


def card(move="truck_l", why=WHY, **kw):
    return dict({"id": "SH01", "camera_move": move, "camera_why": why}, **kw)


@pytest.mark.parametrize("move", list(M.CAMERA_MOVES))
def test_a_valid_card_passes(move):
    why = '"he decided to stay" -> a decision' if move.startswith("zoom_in") else WHY
    if move in ("zoom_out", "truck_zoom_out"):
        why = '"the snow fell" -> context'
    f = M.check_shot_cards([card(move, why)], {"SH01": NARR})
    assert [x for x in f if x["severity"] == "FAIL"] == [], f
    assert len(M.CAMERA_MOVES) == 6 and "static" not in M.CAMERA_MOVES and not any("orbit" in m for m in M.CAMERA_MOVES)


def test_missing_camera_move_fails_cm01():
    c = card(); del c["camera_move"]
    f = rules(M.check_shot_cards([c], {"SH01": NARR}), "CM-01")
    assert f and f[0]["severity"] == "FAIL" and f[0]["where"] == "SH01"
    assert rules(M.check_shot_cards([card("")], {"SH01": NARR}), "CM-01")


def test_other_value_fails_cm02():
    assert rules(M.check_shot_cards([card("dolly")], {"SH01": NARR}), "CM-02")


@pytest.mark.parametrize("val", ["orbit", "Orbit", "rotate", "roll", "spin", "arc", "orbit_left"])
def test_orbit_rotate_roll_are_forbidden_cm02(val):
    f = rules(M.check_shot_cards([card(val)], {"SH01": NARR}), "CM-02")
    assert f and "forbidden" in f[0]["detail"] and "16:25" in f[0]["detail"]


@pytest.mark.parametrize("val", ["static", "still", "none"])
def test_static_fails_cm02_with_the_owner_text(val):
    f = rules(M.check_shot_cards([card(val)], {"SH01": NARR}), "CM-02")
    assert f and "static is not allowed" in f[0]["detail"] and "18:10" in f[0]["detail"]


def test_nonzero_rotation_field_fails_cm02():
    assert rules(M.check_shot_cards([card(camera_rotation_deg=2)], {"SH01": NARR}), "CM-02")
    assert rules(M.check_shot_cards([card(rotation=5)], {"SH01": NARR}), "CM-02")
    assert not rules(M.check_shot_cards([card(camera_rotation_deg=0)], {"SH01": NARR}), "CM-02")


def test_missing_or_multiline_camera_why_fails_cm03():
    c = card(); del c["camera_why"]
    assert rules(M.check_shot_cards([c], {"SH01": NARR}), "CM-03")
    assert rules(M.check_shot_cards([card(why='"all along"\n"the line"')], {"SH01": NARR}), "CM-03")


def test_why_without_a_quote_fails_cm04():
    assert [x["severity"] for x in rules(M.check_shot_cards([card(why="because the line is long")], {"SH01": NARR}), "CM-04")] == ["FAIL"]
    assert rules(M.check_shot_cards([card(why="he didn't stop")], {"SH01": NARR}), "CM-04")  # an apostrophe is not a quote


def test_a_quote_not_in_the_narration_fails_cm04():
    f = rules(M.check_shot_cards([card(why='"dragons over the hill"')], {"SH01": NARR}), "CM-04")
    assert f and f[0]["severity"] == "FAIL"


def test_quote_matching_ignores_case_and_whitespace():
    assert not rules(M.check_shot_cards([card(why='"ALL   along\nTHE line"'.replace("\n", " "))], {"SH01": NARR}), "CM-04")
    assert not rules(M.check_shot_cards([card(why='“all along the line” curly')], {"SH01": NARR}), "CM-04")


def test_without_narration_a_quote_is_enough_plus_a_review():
    f = rules(M.check_shot_cards([card()]), "CM-04")
    assert [x["severity"] for x in f] == ["REVIEW"]


def test_table_mismatch_is_review_not_fail_cm05():
    f = M.check_shot_cards([card("zoom_in", '"all along the line" -> a line of men, advance')], {"SH01": NARR})
    r = rules(f, "CM-05")
    assert r and r[0]["severity"] == "REVIEW" and "truck" in r[0]["detail"] and not [x for x in f if x["severity"] == "FAIL"]


def test_same_move_run_is_review_cm06():
    cards = [dict(card("truck_l"), id=f"SH0{i}") for i in range(5)]
    narr = {c["id"]: NARR for c in cards}
    f = rules(M.check_shot_cards(cards, narr), "CM-06")
    assert f and f[0]["severity"] == "REVIEW"
    cards[2]["camera_move"] = "zoom_in"; cards[2]["camera_why"] = '"he decided to stay"'
    assert not rules(M.check_shot_cards(cards, narr), "CM-06")


# ---------------- clip tests ----------------
@clip_only
@pytest.mark.parametrize("move,kw", [
    ("zoom_in", dict(zoom_pct=10)), ("zoom_out", dict(zoom_pct=-10)),
    ("truck_l", dict(tx_pct=8)), ("truck_r", dict(tx_pct=-8)),
    ("truck_zoom_in", dict(tx_pct=8, zoom_pct=10)), ("truck_zoom_out", dict(tx_pct=8, zoom_pct=-10)),
])
def test_declared_move_matches_measured(tmp_path, move, kw):
    r = M.camera_move_clip(make_clip(tmp_path, move, **kw), move=move)
    assert r["status"] == "PASS", r


@clip_only
def test_wrong_direction_fails_with_both_numbers(tmp_path):
    r = M.camera_move_clip(make_clip(tmp_path, "zo", zoom_pct=-10), move="zoom_in")
    txt = json.dumps(r)
    assert r["status"] == "FAIL" and "declared zoom_in" in txt and "measured zoom=-" in txt
    r2 = M.camera_move_clip(make_clip(tmp_path, "tl", tx_pct=8), move="truck_r")
    assert r2["status"] == "FAIL" and "declared truck_r" in json.dumps(r2)


@clip_only
def test_a_rotating_clip_fails_cm10_even_when_it_also_zooms_right(tmp_path):
    r = M.camera_move_clip(make_clip(tmp_path, "rz", zoom_pct=10, rot_deg=6), move="zoom_in")
    assert r["status"] == "FAIL" and rules(r["findings"], "CM-10")


@clip_only
def test_orbit_like_arc_fails(tmp_path):
    r = M.camera_move_clip(make_clip(tmp_path, "arc", tx_pct=8, rot_deg=6), move="truck_l")
    assert r["status"] == "FAIL" and rules(r["findings"], "CM-10")


@clip_only
def test_a_pure_truck_declared_as_combined_fails_cm13(tmp_path):
    r = M.camera_move_clip(make_clip(tmp_path, "pt", tx_pct=8), move="truck_zoom_in")
    assert r["status"] == "FAIL" and rules(r["findings"], "CM-13")


@clip_only
def test_a_pure_zoom_declared_as_truck_fails_cm12(tmp_path):
    r = M.camera_move_clip(make_clip(tmp_path, "pz", zoom_pct=10), move="truck_l")
    assert r["status"] == "FAIL" and rules(r["findings"], "CM-12")


@clip_only
def test_combined_with_mismatched_easing_is_review_cm14(tmp_path):
    # pan eased, zoom linear -> progress differs
    tex_clip = make_clip_two_curves(tmp_path)
    r = M.camera_move_clip(tex_clip, move="truck_zoom_in")
    assert r["status"] == "REVIEW" and rules(r["findings"], "CM-14"), r


def make_clip_two_curves(tmp_path):
    tex = texture(); d = tmp_path / "two"; d.mkdir()
    for i in range(N):
        p = i / (N - 1); pe = p * p * (3 - 2 * p)
        M_ = cv2.getRotationMatrix2D((W, H), 0, 1.0 + 0.10 * p)
        M_[0, 2] += 0.12 * W * (pe ** 3)
        crop = cv2.warpAffine(tex, M_, (W * 2, H * 2), borderMode=cv2.BORDER_REFLECT)
        cv2.imwrite(str(d / f"f{i:03d}.png"), crop[H // 2: H // 2 + H, W // 2: W // 2 + W])
    out = tmp_path / "two.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(d / "f%03d.png"),
                    "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


@clip_only
def test_a_clip_with_no_camera_move_fails_cm15_and_static_card_fails_cm02(tmp_path):
    r = M.camera_move_clip(make_clip(tmp_path, "still"), move="zoom_in")
    assert r["status"] == "FAIL" and rules(r["findings"], "CM-15")
    assert rules(M.check_shot_cards([card("static")], {"SH01": NARR}), "CM-02")
    assert M.camera_move_clip(make_clip(tmp_path, "still2"), move="static")["status"] == "FAIL"


@clip_only
def test_not_run_cases(tmp_path, monkeypatch):
    clip = make_clip(tmp_path, "z", zoom_pct=10)
    assert M.camera_move_clip(clip)["status"] == "NOT_RUN"  # no declared move
    sc = Path(str(clip) + ".camera.json"); sc.write_text(json.dumps({"camera_move": "zoom_in"}))
    assert M.camera_move_clip(clip)["status"] == "PASS"  # sidecar
    monkeypatch.setattr(M, "_cv2", lambda: None)
    assert M.camera_move_clip(clip, move="zoom_in")["status"] == "NOT_RUN"
    monkeypatch.undo()
    one = tmp_path / "one.mp4"
    d = tmp_path / "one"; d.mkdir(); cv2.imwrite(str(d / "f000.png"), texture()[:H, :W])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(d / "f%03d.png"), "-frames:v", "1",
                    "-pix_fmt", "yuv420p", str(one)], check=True)
    assert M.camera_move_clip(one, move="zoom_in")["status"] == "NOT_RUN"


@clip_only
def test_open_floors_make_the_floor_checks_not_run_never_a_pass(tmp_path, monkeypatch):
    """zoom_min_pct and still_drift_min_pct are OPEN (null in the shipped tolerances): CM-15 and the zoom size are NOT_RUN."""
    monkeypatch.delenv("CAMERA_MOVE_TOLERANCES")
    good = M.camera_move_clip(make_clip(tmp_path, "z", zoom_pct=10), move="zoom_in")
    assert good["status"] == "NOT_RUN" and "CM-15" in good["detail"] and not good["findings"]
    assert M.camera_move_clip(make_clip(tmp_path, "z2", zoom_pct=-10), move="zoom_in")["status"] == "FAIL"  # direction still checked
    assert M.camera_move_clip(make_clip(tmp_path, "r", zoom_pct=10, rot_deg=6), move="zoom_in")["status"] == "FAIL"  # rotation too
    assert M.camera_move_clip(make_clip(tmp_path, "t", tx_pct=8), move="truck_l")["status"] == "NOT_RUN"


def test_shipped_tolerances_have_the_two_floors_open():
    d = json.loads((Path(M.__file__).with_name("camera_move_tolerances.json")).read_text(encoding="utf-8"))
    assert d["zoom_min_pct"]["value"] is None and d["still_drift_min_pct"]["value"] is None
    assert "BP-181" not in Path(M.__file__).read_text(encoding="utf-8")


@clip_only
def test_cli_exit_codes(tmp_path):
    good = make_clip(tmp_path, "g", zoom_pct=10)
    bad = make_clip(tmp_path, "b", zoom_pct=-10)
    junk = tmp_path / "junk.mp4"; junk.write_bytes(b"not a video")
    assert M.main(["clip", str(bad), "--move", "zoom_in"]) == 1
    assert M.main(["clip", str(good), "--move", "zoom_in"]) == 0
    assert M.main(["clip", str(good)]) == 0  # NOT_RUN
    assert M.main(["clip", str(junk), "--move", "zoom_in"]) == 2
    cards = tmp_path / "c.json"; cards.write_text(json.dumps([card("static")]))
    assert M.main(["cards", str(cards)]) == 1
    cards.write_text(json.dumps([card()])); assert M.main(["cards", str(cards)]) == 0


@clip_only
def test_sign_convention_is_one_constant(tmp_path, monkeypatch):
    clip = make_clip(tmp_path, "t", tx_pct=8)
    assert M.camera_move_clip(clip, move="truck_l")["status"] == "PASS"
    assert M.camera_move_clip(clip, move="truck_r")["status"] == "FAIL"
    monkeypatch.setattr(M, "TRUCK_L_PAN_SIGN", -1.0)
    assert M.camera_move_clip(clip, move="truck_l")["status"] == "FAIL"
    assert M.camera_move_clip(clip, move="truck_r")["status"] == "PASS"
