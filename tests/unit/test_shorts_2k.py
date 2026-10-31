"""F6 / P9: a Short is 1440x2560 at the job fps (BP-167), its safe zone scales with the frame (BP-29, REVIEW), and a
caption-free master sits beside the captioned file (BP-13 keeps the burned captions on the delivered one; CN-14)."""
import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from explainer_engine.core import contracts, delivery
from explainer_engine.production import clip_shorts as CS
from explainer_engine.production import shorts as SH
from explainer_engine.qa import short_format as SF
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def test_planned_frame_is_the_master_rotated_in_both_renderers():
    assert delivery.shorts_frame() == (1440, 2560)
    assert (SH.W, SH.H) == (1440, 2560) and (CS.W, CS.H) == (1440, 2560)
    assert CS.FPS == delivery.fps() and CS.FG_Y == (CS.H - CS.FG_H) // 2
    for path in ("shorts.py", "clip_shorts.py"):
        assert "W, H = 1080, 1920" not in (ROOT / "explainer_engine/production" / path).read_text(encoding="utf-8")


def test_short_format_accepts_9_16_at_any_height_and_refuses_16_9():
    assert SF.check({"width": 1440, "height": 2560, "seconds": 58.0}) == []
    assert SF.check({"width": 1080, "height": 1920, "seconds": 58.0}) == []
    assert [f["rule"] for f in SF.check({"width": 2560, "height": 1440, "seconds": 30})] == ["SF-01"]
    assert [f["rule"] for f in SF.check({"width": 1440, "height": 2400, "seconds": 30})] == ["SF-02"]


def test_five_planned_shorts_all_pass_the_format_check():
    """Five Shorts of a script fixture go through the real planning steps (``beats.short_doc`` + ``validate.short_words``, the
    estimated read: no Whisper needed); each plan row takes the delivery frame and the Short's own estimated seconds."""
    from test_short_beats import short_doc_with_beats
    from explainer_engine.production import beats as BEATS
    from explainer_engine.production import validate as V
    doc = short_doc_with_beats()
    base = doc["shorts"][0]
    doc["shorts"] = [dict(copy.deepcopy(base), id=f"SH{i:02d}") for i in range(1, delivery.shorts() + 1)]
    w, h = delivery.shorts_frame()
    plan = [{"id": sh["id"], "width": w, "height": h, "seconds": V.short_words(BEATS.short_doc(doc, sh))["duration"]}
            for sh in doc["shorts"]]
    assert len(plan) == 5 and all(p["seconds"] > 0 for p in plan)
    assert all(SF.check(p) == [] for p in plan), [SF.check(p) for p in plan]


def test_safe_zone_bands_scale_four_thirds_from_bp29():
    assert SH.safe_bands((1080, 1920)) == (tuple(SR.T("BP-29", "safe_x_px")), tuple(SR.T("BP-29", "safe_y_px")))
    (x0, x1), (y0, y1) = SH.safe_bands((1440, 2560))
    sx, sy = SR.T("BP-29", "safe_x_px"), SR.T("BP-29", "safe_y_px")
    assert (x0, x1) == (round(sx[0] * 4 / 3), round(sx[1] * 4 / 3)) and (y0, y1) == (round(sy[0] * 4 / 3), round(sy[1] * 4 / 3))
    rep = SH.safe_zone_report()
    assert rep["frame"] == [1440, 2560] and rep["safe_x_px_frame"] == [x0, x1] and rep["safe_y_px_frame"] == [y0, y1]
    assert SR.severity("BP-29") == "REVIEW" and rep["severity"] in ("REVIEW", "PASS")  # never a FAIL until the phone screenshot
    cap = rep["caption_box_px"]  # the caption style scales with the frame, so it sits where it sat at 1080
    assert cap[0] == SH.CAP_MARGIN_LR == 120 and cap[3] == 2560 - SH.CAP_MARGIN_V


def _package(base: Path, final: Path, master: Path) -> dict:
    doc = json.loads((ROOT / "tests/fixtures/contracts/distribution_package/valid.json").read_text(encoding="utf-8"))
    doc = copy.deepcopy(doc)
    files = SH.package_files(final, master, base)
    cover = base / "c1.png"
    cover.write_bytes(b"png")
    doc["files"] = {"video": files["video"], "cover": {"path": "c1.png", "sha256": contracts.sha256_file(cover)}, "captions": None}
    doc["checks"] = [files["check"]]
    return doc


def test_package_lists_the_captioned_file_and_the_master_with_sha256(tmp_path):
    final, master = tmp_path / "SH01.mp4", tmp_path / "SH01_master.mp4"
    final.write_bytes(b"captioned")
    master.write_bytes(b"master")
    doc = _package(tmp_path, final, master)
    assert contracts.errors(doc, tmp_path) == []  # CN-14: both exist unchanged
    assert doc["checks"][0]["check_id"] == f"caption_free_master:SH01_master.mp4@{contracts.sha256_file(master)}"
    final.write_bytes(b"re-rendered")  # the listed file changed since it was recorded
    assert any(f["rule"] == "CN-14" for f in contracts.errors(doc, tmp_path))


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg/ffprobe missing")
def test_clip_graph_encodes_2k_with_and_without_captions(tmp_path):
    from PIL import Image
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=320x180:r=24:d=1", "-f", "lavfi", "-i",
                    "sine=d=1", "-shortest", "-pix_fmt", "yuv420p", str(src)], check=True)
    over = tmp_path / "band.png"
    Image.new("RGBA", (CS.W, CS.H), (0, 0, 0, 0)).save(over)
    cap = CS.ass([{"w": "hello", "s": 0.0, "e": 0.4}, {"w": "world", "s": 0.4, "e": 0.8}], tmp_path / "cap.ass")
    assert f"PlayResX: {CS.W}" in cap.read_text(encoding="utf-8") and f"PlayResY: {CS.H}" in cap.read_text(encoding="utf-8")
    sizes = {}
    for name, subs in (("final", str(cap)), ("master", None)):
        out = tmp_path / f"{name}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-i", str(over), "-filter_complex",
                        CS.filter_graph(1.0, 24, subs, CS.FONT.parent), "-map", "[v]", "-map", "[au]", "-c:v", "libx264",
                        "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", str(out)], check=True)
        info = SF.probe(out)
        sizes[name] = (info["width"], info["height"])
        assert SF.check(info) == []
    assert sizes == {"final": (1440, 2560), "master": (1440, 2560)}
    assert (tmp_path / "final.mp4").stat().st_size != (tmp_path / "master.mp4").stat().st_size  # captions are burned in only one


def test_the_master_is_re_encoded_with_the_same_video_settings_as_the_captioned_file_not_copied():
    from explainer_engine.production import shorts
    src = Path(shorts.__file__).read_text(encoding="utf-8")
    assert shorts.FINAL_VIDEO[:2] == ["-c:v", "libx264"] and src.count("*FINAL_VIDEO") == 2     # the final and the master share them
    assert '"-c:v", "copy"' not in src
