"""The Blender render validator (roadmap section 13, ICW-08; BP-174, BP-173): synthetic shots, each defect triggers exactly its row."""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from explainer_engine.blender import render as R
from explainer_engine.blender import style as S
from explainer_engine.blender import validate as V
from explainer_engine.core import contracts as C
from explainer_engine.qa import retry_router as RR
from explainer_engine.qa import scorecard as SC
from explainer_engine.standards import sourced_rules as SR

CORE = ("RV-FRAMES", "RV-SIZE", "RV-FPS", "RV-BLACK", "RV-FROZEN", "RV-FLICKER", "RV-LINE")
PAL = S.palette()


def rgb(token: str) -> np.ndarray:
    h = PAL[token].lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)


def spec(frames: int, scale: float = 0.25, output: str = "png_seq", fps: int = 24) -> dict:
    s = R.smoke_spec(frames=frames)
    s["frame"]["render_scale"] = scale
    s["render"]["output"] = output
    s["clock"]["fps"] = fps
    return s


def scene(i: int, w: int = 640, h: int = 360, *, lines: int = 10, bg: str = "paper", line: str = "ink", width: int = 1) -> np.ndarray:
    """A frame: a flat backdrop with vertical strokes that move one pixel a frame (so no two frames are equal)."""
    img = np.empty((h, w, 3), dtype=np.uint8)
    img[:] = rgb(bg) if isinstance(bg, str) else bg
    for k in range(lines):
        x = (20 + k * (w // (lines + 1)) + i) % (w - width)
        img[h // 8: h - h // 8, x:x + width] = rgb(line)
    return img


def shot(tmp_path, imgs: list[np.ndarray], name: str = "shot") -> object:
    d = tmp_path / name
    (d / "frames").mkdir(parents=True)
    for i, img in enumerate(imgs):
        Image.fromarray(img).save(d / "frames" / R.FRAME_NAME.format(index=i))
    return d


def failed(rows: list[dict], only=CORE) -> set[str]:
    return {r["check_id"].split(":", 1)[1] for r in rows if not r["passed"] and r["check_id"].split(":", 1)[1] in only}


def test_thresholds_come_from_the_registry():
    assert V.BLACK_FRAMES_MAX == SR.T("BP-174", "black_frames_max")
    assert V.FROZEN_FRAMES_MAX == SR.T("BP-174", "frozen_frames_max")
    assert V.FLICKER_LUMA_DELTA == SR.T("BP-174", "flicker_luma_delta")
    assert V.LINE_EDGE_VARIANCE == SR.T("BP-174", "line_edge_variance")
    assert V.WEIGHT_PX_1440 == SR.T("BP-173", "weight_px_1440")
    for rid in ("BP-173", "BP-174"):
        assert "explainer_engine/blender/validate.py" in SR.rule(rid)["enforced_by"]


def test_a_clean_shot_passes_every_core_row(tmp_path):
    d = shot(tmp_path, [scene(i) for i in range(16)])
    rows = V.RenderValidator().check(d, spec(16))
    assert failed(rows) == set()
    assert {r["check_id"].split(":", 1)[1] for r in rows} >= set(CORE) | {"RV-LINE-WEIGHT", "RV-CAL-DARK", "RV-CAL-STILL"}
    for r in rows:
        assert set(r) == {"check_id", "rule", "severity", "measured", "threshold", "passed"}


def test_more_than_two_black_frames_fail_and_two_do_not(tmp_path):
    # a very dark backdrop is all ink and within 0.08 luma of black, like a black frame: so only RV-BLACK can move
    dark = np.array([10, 10, 14], dtype=np.uint8)
    base = [scene(i, bg=dark, line="grey_mid") for i in range(16)]
    two = [np.zeros_like(f) if i in (5, 6) else f for i, f in enumerate(base)]
    three = [np.zeros_like(f) if i in (5, 6, 7) else f for i, f in enumerate(base)]
    assert failed(V.RenderValidator().check(shot(tmp_path, two, "two"), spec(16))) == set()
    rows = V.RenderValidator().check(shot(tmp_path, three, "three"), spec(16))
    assert failed(rows) == {"RV-BLACK"}
    black = next(r for r in rows if r["check_id"].endswith("RV-BLACK"))
    assert black["severity"] == "FAIL" and black["measured"] == 3


def test_a_near_black_frame_is_not_black_but_is_reported(tmp_path):
    imgs = [scene(i) for i in range(8)]
    imgs[3] = np.full_like(imgs[3], 1)
    rows = V.RenderValidator().check(shot(tmp_path, imgs), spec(8))
    assert next(r for r in rows if r["check_id"].endswith("RV-BLACK"))["measured"] == 0
    assert next(r for r in rows if r["check_id"].endswith("RV-CAL-DARK"))["measured"] < 0.01


def test_a_frozen_run_longer_than_twelve_frames_fails(tmp_path):
    ok = [scene(min(i, 3) if i < 15 else i) for i in range(20)]       # frames 3..14 identical: a run of 12
    bad = [scene(min(i, 3) if i < 16 else i) for i in range(20)]      # frames 3..15 identical: a run of 13
    assert failed(V.RenderValidator().check(shot(tmp_path, ok, "ok"), spec(20))) == set()
    rows = V.RenderValidator().check(shot(tmp_path, bad, "bad"), spec(20))
    assert failed(rows) == {"RV-FROZEN"}
    assert "13 frames" in next(r for r in rows if r["check_id"].endswith("RV-FROZEN"))["measured"]


def test_still_mode_hold_exempts_the_frozen_row(tmp_path):
    rows = V.RenderValidator().check(shot(tmp_path, [scene(0)] * 20), spec(20), still_mode="hold")
    assert failed(rows) == set()
    row = next(r for r in rows if r["check_id"].endswith("RV-FROZEN"))
    assert row["severity"] == "INFO" and "exempt" in row["measured"]


def test_a_luma_jump_is_flicker_and_review_only(tmp_path):
    imgs = [scene(i) for i in range(16)]
    imgs[8] = scene(8, bg="grey_mid")    # paper -> grey: luma drops by far more than 0.08, the strokes stay the same ink
    rows = V.RenderValidator().check(shot(tmp_path, imgs), spec(16))
    assert failed(rows) == {"RV-FLICKER"}
    row = next(r for r in rows if r["check_id"].endswith("RV-FLICKER"))
    assert row["severity"] == "REVIEW" and row["measured"] > V.FLICKER_LUMA_DELTA
    assert RR.status_of(rows) == "WARN_REVIEW"


def test_an_edge_count_jump_is_unstable_line_art(tmp_path):
    imgs = [scene(i) for i in range(16)]
    imgs[8] = scene(8, lines=20)          # twice the strokes for one frame: +100 % edge pixels, luma moves under 0.08
    rows = V.RenderValidator().check(shot(tmp_path, imgs), spec(16))
    assert failed(rows) == {"RV-LINE"}
    assert next(r for r in rows if r["check_id"].endswith("RV-LINE"))["measured"] >= 0.9


def test_missing_frames_and_a_wrong_size_fail_their_rows(tmp_path):
    imgs = [scene(i) for i in range(8)]
    d = shot(tmp_path, imgs)
    (d / "frames" / R.FRAME_NAME.format(index=5)).unlink()
    rows = V.RenderValidator().check(d, spec(8))
    assert "RV-FRAMES" in failed(rows) and "RV-SIZE" not in failed(rows)
    d2 = shot(tmp_path, [scene(i, w=320, h=180) for i in range(8)], "small")
    assert failed(V.RenderValidator().check(d2, spec(8))) == {"RV-SIZE"}


def test_the_clip_rate_and_frame_count_are_checked(tmp_path):
    d = shot(tmp_path, [scene(i) for i in range(8)])
    (d / "shot.mkv").write_bytes(b"x")
    good = lambda p: {"width": 640, "height": 360, "fps": 24.0, "frames": 8}  # noqa: E731
    assert failed(V.RenderValidator(probe=good).check(d, spec(8, output="mkv_ffv1"))) == set()
    for bad in ({"fps": 25.0}, {"frames": 7}, {"width": 320}):
        probe = lambda p, b=bad: dict(good(p), **b)  # noqa: E731
        assert failed(V.RenderValidator(probe=probe).check(d, spec(8, output="mkv_ffv1"))) == {"RV-FPS"}
    (d / "shot.mkv").unlink()
    assert failed(V.RenderValidator(probe=good).check(d, spec(8, output="mkv_ffv1"))) == {"RV-FPS"}
    assert failed(V.RenderValidator().check(d, spec(8, fps=25))) == {"RV-FPS"}


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg + ffprobe")
def test_a_real_ffv1_clip_probes_at_24_fps(tmp_path):
    d = shot(tmp_path, [scene(i) for i in range(8)])
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-framerate", "24", "-start_number", "0", "-i",
                    str(d / "frames" / "frame_%06d.png"), "-frames:v", "8", "-c:v", "ffv1", "-pix_fmt", "yuv444p",
                    str(d / "shot.mkv")], check=True)
    assert V.probe(d / "shot.mkv") == {"width": 640, "height": 360, "fps": 24.0, "frames": 8}
    assert failed(V.RenderValidator().check(d, spec(8, output="mkv_ffv1"))) == set()


def test_the_stroke_width_is_measured_at_1440_rows(tmp_path):
    two = [scene(i, w=2560, h=1440, width=2) for i in range(3)]
    six = [scene(i, w=2560, h=1440, width=6) for i in range(3)]
    r2 = V.RenderValidator().check(shot(tmp_path, two, "two"), spec(3, scale=1.0))
    r6 = V.RenderValidator().check(shot(tmp_path, six, "six"), spec(3, scale=1.0))
    w2 = next(r for r in r2 if r["check_id"].endswith("RV-LINE-WEIGHT"))
    w6 = next(r for r in r6 if r["check_id"].endswith("RV-LINE-WEIGHT"))
    assert w2["measured"] == 2.0 and w2["passed"] and w2["severity"] == "REVIEW" and w2["rule"] == "BP-173"
    assert w6["measured"] == 6.0 and not w6["passed"]
    # half the resolution, one pixel: still 2 px at 1440 rows
    one = [scene(i, w=1280, h=720, width=1) for i in range(3)]
    r1 = V.RenderValidator().check(shot(tmp_path, one, "one"), spec(3, scale=0.5))
    assert next(r for r in r1 if r["check_id"].endswith("RV-LINE-WEIGHT"))["measured"] == 2.0


def test_ink_level_sits_between_ink_and_paper():
    lo, hi = V._hex_luma(PAL["ink"]), V._hex_luma(PAL["paper"])
    assert lo < V.ink_level() < hi
    assert V.runs(np.array([[0, 1, 1, 0, 1, 0, 1, 1, 1]], dtype=bool)).tolist() == [2, 1, 3]


def test_style_findings_are_info_with_a_measured_value(tmp_path):
    flat = np.empty((90, 160, 3), dtype=np.uint8)
    flat[:] = rgb("paper")
    p = tmp_path / "flat.png"
    Image.fromarray(flat).save(p)
    rows = V.style_findings([p], "s1")
    assert [r["check_id"] for r in rows] == ["s1:ST-PALETTE", "s1:ST-PAPER", "s1:ST-SPECULAR"]
    assert all(r["severity"] == "INFO" and r["passed"] and r["threshold"] is None for r in rows)
    assert rows[0]["measured"] < 0.5 and rows[1]["measured"] < 1e-6
    white = np.full((90, 160, 3), 255, dtype=np.uint8)
    q = tmp_path / "white.png"
    Image.fromarray(white).save(q)
    assert V.style_findings([q], "s2")[2]["measured"] == 1.0


def test_the_report_is_a_valid_qa_report_and_the_cli_writes_it(tmp_path):
    d = shot(tmp_path, [np.zeros((360, 640, 3), dtype=np.uint8)] * 4)
    (d / "spec.json").write_text(json.dumps(spec(4)), encoding="utf-8")
    rows = V.run(d)
    rep = V.RenderValidator.report("job-001", rows)
    C.validate(rep)
    assert rep["stage"] == "clip" and rep["status"] == "ESCALATE_TO_HUMAN" and rep["retry_directive"] is None
    job = tmp_path / "job"
    assert V.main([str(d), "--job-dir", str(job), "--job-id", "job-001"]) == 1
    doc = json.loads((job / "qa" / "clip.qa_report.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "qa_report/1" and any(c["check_id"] == "smoke_01:RV-BLACK" and not c["passed"] for c in doc["checks"])
    assert SC.render_report(job)["job_id"] == "job-001"


def test_the_scorecard_reads_the_render_report_into_check_5():
    words = [{"w": "a", "s": 0.0, "e": 0.5}, {"w": "b.", "s": 0.6, "e": 1.0}]
    shots = [{"id": "s1", "start": 0.0, "end": 1.0}]
    bad = {"stage": "clip", "checks": [V.check("s1:RV-BLACK", "BP-174", "FAIL", 3, 2, False)]}
    rev = {"stage": "clip", "checks": [V.check("s1:RV-FLICKER", "BP-174", "REVIEW", 0.2, 0.08, False)]}
    ok = {"stage": "clip", "checks": [V.check("s1:RV-BLACK", "BP-174", "FAIL", 0, 2, True)]}
    pics = {"p1": {"luma": 0.5, "sat": 0.3, "warm": 0.1}}
    row5 = lambda q: SC.score(shots, words, "a b.", {}, pic_stats=pics, timed_findings=[], render_qa=q)[4]  # noqa: E731
    assert row5(bad)["status"] == "FAIL" and any("s1:RV-BLACK" in e for e in row5(bad)["evidence"])
    assert row5(rev)["status"] == "REVIEW"
    assert row5(ok)["status"] == "PASS"
    assert row5(None)["status"] == "PASS"


def test_the_legacy_clip_report_is_not_read_as_a_render_report(tmp_path):
    rep = RR.build_report("job-001", "clip", [{"check_id": "CLIP-03", "rule": "CLIP-03", "severity": "REVIEW", "measured": "x",
                                               "threshold": None, "passed": False}])
    RR.write_report(tmp_path, rep)
    assert SC.render_report(tmp_path) is None


def test_only_shot_spec_2_is_checked(tmp_path):
    with pytest.raises(Exception):
        V.RenderValidator().check(tmp_path, {"schema": "shot_spec/1", "shot_id": "x"})
