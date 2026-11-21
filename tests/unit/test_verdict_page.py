"""Guide step 4 (D-116): the verdict page measures every card the same way (identity, dE, line share, motion, seconds and
dollars, upscale) from the pod's out folder and the J5 renders; it ranks nothing. Free, ffmpeg-made clips."""
import json
import shutil
import subprocess

import pytest
from PIL import Image

from explainer_engine.finish import upscale as U
from explainer_engine.qa import verdict_page as V

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")


def _clip(path, size="480x272", src="testsrc"):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{src}=size={size}:rate=24:duration=0.5",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@needs_ffmpeg
def test_a_pod_out_folder_and_j5_renders_become_cards_with_every_number(tmp_path):
    pod = tmp_path / "pod"
    jid = "S03-02.ltx25.clay.s42"
    _clip(pod / "ltx" / f"{jid}.mp4", "1920x1088")
    (pod / "ltx" / f"{jid}.json").write_text(json.dumps({"seconds": 360.0}))
    U.upscale(pod / "ltx" / f"{jid}.mp4", pod / "ltx_up" / f"{jid}.mp4", **U.ROUTE_TEST)
    ff = tmp_path / "ff"
    ff.mkdir()
    Image.new("RGB", (480, 272), (200, 180, 150)).save(ff / "S03-02.png")
    _clip(tmp_path / "j5" / "S01-01.mp4")
    jobs = {"jobs": [{"id": jid, "clip_id": "S03-02", "shot_id": "S03-02", "route": "J2", "base": "ltx25", "variant": "clay",
                      "seed": 42}]}
    rows = V.cards(pod, jobs=jobs, j5=tmp_path / "j5", first_frames=ff)
    assert [(r["route"], r["shot"]) for r in rows] == [("J2", "S03-02"), ("J5", "S01-01")]
    doc = V.build(tmp_path / "out", rows, usd_per_hour=0.89)
    j2 = doc["cards"][0]
    assert j2["usd"] == round(360 * 0.89 / 3600, 3) and j2["seconds_gen"] == 360.0
    m = j2["metrics"]
    assert {"palette_dist", "ink_ratio"} <= set(m["identity"]) and m["delta_e_last_vs_first_frame"] >= 0
    assert {"hold_share", "flicker_max", "speed_p90"} <= set(m["motion"]) and set(m["line_share"]) == {"first", "last"}
    assert j2["upscale"]["schema"] == "upscale_compare/1" and len(j2["thumbs"]) == 3
    page = (tmp_path / "out" / "VERDICT.html").read_text()
    assert "J2 · S03-02" in page and "J5 · S01-01" in page and "prefers-color-scheme" in page
    assert json.loads((tmp_path / "out" / "verdict.json").read_text())["cards"][1]["route"] == "J5"
    assert all((tmp_path / "out" / t).exists() for c in doc["cards"] for t in c["thumbs"])


@needs_ffmpeg
def test_a_still_background_frame_gets_a_card_without_motion(tmp_path):
    bg = tmp_path / "bg"
    bg.mkdir()
    Image.new("RGB", (640, 360), (90, 80, 70)).save(bg / "S02-02_overnight.png")
    doc = V.build(tmp_path / "o", V.cards(None, background=bg))
    c = doc["cards"][0]
    assert c["route"] == "background" and "motion" not in c["metrics"] and c["metrics"]["frames"] == 1


def test_the_upscale_chain_keeps_the_wp5b_default_and_adds_cas_and_grain_only_when_asked():
    plain = U.video_filter(1920, 1088)
    assert "cas" not in plain and "noise" not in plain
    rt = U.video_filter(1920, 1088, **U.ROUTE_TEST)
    assert rt.index("flags=lanczos") < rt.index("cas=0.4") < rt.index("noise=alls=6:allf=t") < rt.index("fps=")
    assert "unsharp=5:5:0.6" in U.video_filter(1920, 1088, sharpen="unsharp")
    with pytest.raises(Exception):
        U.video_filter(1920, 1088, sharpen="laplace")
