import json
import shutil
import subprocess

import pytest

from explainer_engine.research import reference_study as rs

HEAT = [{"start_time": float(i * 10), "end_time": float(i * 10 + 10), "value": v}
        for i, v in enumerate([1.0, 0.2, 0.3, 0.9, 0.1, 0.4, 0.5, 0.6, 0.2, 0.3])]


def _ref(tmp_path, name, views, channel="fern"):
    v = tmp_path / f"{name}.mp4"
    v.write_bytes(b"")
    v.with_suffix(".info.json").write_text(json.dumps(
        {"id": name, "title": name, "channel": channel, "view_count": views, "duration": 100.0, "heatmap": HEAT}))
    return v


def test_shot_stats_counts_the_opening_and_the_median():
    s = rs.shot_stats([5.0, 10.0, 40.0, 70.0], 100.0)
    assert s["shots"] == 5 and s["cuts_first_30s"] == 2
    assert s["median_shot_s"] == 30.0 and s["shots_per_min"] == 3.0


def test_cut_density_at_heatmap_peaks_and_lows(tmp_path):
    row = rs.study_video(_ref(tmp_path, "a", 10), cuts=[2.0, 5.0, 8.0, 31.0, 45.0])
    # peaks = 0..10 (1.0) and 30..40 (0.9): four cuts in 20 s; lows = 40..50 (0.1) and 10..20 (0.2): one cut in 20 s
    assert row["cuts_per_min_peaks"] == 12.0
    assert row["cuts_per_min_lows"] == 3.0
    assert row["peak_times_s"] == [0, 30]


def test_most_viewed_against_the_rest(tmp_path):
    rows = [rs.study_video(_ref(tmp_path, f"v{i}", views), cuts=cuts) for i, (views, cuts) in
            enumerate([(900, [3.0, 6.0, 9.0]), (800, [4.0, 8.0]), (700, [5.0, 10.0]), (50, [50.0]), (10, [])])]
    c = rs.compare(rows)["fern"]
    assert c["top"] == ["v0.mp4", "v1.mp4", "v2.mp4"] and c["rest"] == ["v3.mp4", "v4.mp4"]
    assert c["cuts_first_30s"] == {"top": 2, "rest": 0}


def test_a_video_without_metadata_still_measures(tmp_path):
    v = tmp_path / "x.mp4"
    v.write_bytes(b"")
    row = rs.study_video(v, cuts=[10.0, 20.0])
    assert row["channel"] == "unknown" and row["cuts_per_min_peaks"] is None


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg")
def test_real_cuts_from_a_video(tmp_path):
    pytest.importorskip("scenedetect")
    v = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=160x90:d=2", "-f", "lavfi", "-i",
                    "color=blue:s=160x90:d=2", "-f", "lavfi", "-i", "color=white:s=160x90:d=2", "-filter_complex",
                    "[0][1][2]concat=n=3:v=1", "-r", "24", str(v)], check=True)
    row = rs.study_video(v)
    assert row["shots"] == 3 and row["cuts_first_30s"] == 2
