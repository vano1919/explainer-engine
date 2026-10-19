"""A Short is vertical 9:16 and at most three minutes, or YouTube makes it a video (qa/short_format.py, creator 2026-10-19)."""
import subprocess

import pytest

from explainer_engine.qa import short_format as SF


def test_only_a_vertical_9_16_file_of_at_most_three_minutes_passes():
    assert SF.check({"width": 1080, "height": 1920, "seconds": 58.9}) == []
    assert [f["rule"] for f in SF.check({"width": 1920, "height": 1080, "seconds": 30})] == ["SF-01"]
    assert [f["rule"] for f in SF.check({"width": 1080, "height": 1350, "seconds": 30})] == ["SF-02"]
    assert [f["rule"] for f in SF.check({"width": 1080, "height": 1920, "seconds": 181})] == ["SF-03"]
    assert SF.SHORTS_LINK.format(id="abc") == "https://www.youtube.com/shorts/abc"


@pytest.mark.parametrize("size,ok", [("108x192", True), ("192x108", False)])
def test_probe_reads_the_rendered_file(tmp_path, size, ok):
    f = tmp_path / "s.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={size}:d=1", "-pix_fmt", "yuv420p",
                    str(f)], check=True)
    info = SF.probe(f)
    assert (SF.check(info) == []) is ok and 0.9 < info["seconds"] < 1.2
