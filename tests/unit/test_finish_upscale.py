"""WP-5b: the LTX clip size (1920x1088) becomes the delivery frame (BP-167, 2560x1440, 24 fps) without stretching."""
import shutil
import subprocess

import pytest

from explainer_engine.core import delivery
from explainer_engine.core.errors import ConfigError
from explainer_engine.finish import upscale as U

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")


def test_the_filter_crops_the_model_padding_then_scales_to_the_delivery_frame():
    f = U.video_filter(1920, 1088)
    assert f.startswith("crop=1920:1080:") and f"scale={delivery.size()[0]}:{delivery.size()[1]}:flags=lanczos" in f
    assert f.endswith(f"fps={delivery.fps()}")


def test_an_exact_16_9_source_is_not_cropped_and_an_odd_one_is_refused():
    assert U.video_filter(1920, 1080).startswith("crop=1920:1080:")
    with pytest.raises(ConfigError):
        U.video_filter(1024, 1024)  # a square would lose a third of the picture
    with pytest.raises(ConfigError):
        U.video_filter(0, 1080)


@needs_ffmpeg
def test_a_clip_comes_out_at_the_delivery_frame_and_rate(tmp_path):
    src, dst = tmp_path / "ltx.mp4", tmp_path / "out.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x1088:rate=24:duration=0.5",
                    "-pix_fmt", "yuv420p", str(src)], check=True)
    U.upscale(src, dst)
    assert U.probe_size(dst) == delivery.size() and not (tmp_path / "out.part.mp4").exists()
    rate = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                           "-of", "csv=p=0", str(dst)], capture_output=True, text=True).stdout.strip()
    assert rate == f"{delivery.fps()}/1"


@needs_ffmpeg
def test_a_broken_source_leaves_no_file(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(ConfigError):
        U.upscale(bad, tmp_path / "o.mp4")
    assert not list(tmp_path.glob("o*"))
