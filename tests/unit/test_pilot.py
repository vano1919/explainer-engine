"""Guide step 6 (D-116): the one-minute pilot puts every route's clip on the master clock and frame and assembles it with
build_video_v2; a missing clip stops it, or becomes a marked slate in a preview. Free: ffmpeg test clips."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.production import pilot as P

ROOT = Path(__file__).resolve().parents[2]
RS = json.loads((ROOT / "tests" / "fixtures" / "route_test" / "route_shots.json").read_text(encoding="utf-8"))
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")


def _clip(path, size, frames, src="testsrc"):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{src}=size={size}:rate=24", "-frames:v", str(frames),
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_the_default_window_is_one_minute_of_whole_shots_over_three_scenes_and_four_routes():
    ch = P.select(RS)
    assert sum(s["seconds"] for s in ch) == 59.5 and ch[-1]["id"] == "S03-03"
    assert {s["scene"] for s in ch} == {"S01", "S02", "S03"} and {s["route"] for s in ch} == {"J5", "H", "J4", "J2"}
    with pytest.raises(ContractError):
        P.select(RS, ids=["S99-01"])


def test_the_window_becomes_a_valid_film_shots_3_spine_and_edit_manifest():
    film = P.film_shots(RS, P.select(RS), 24)
    C.validate(film)
    lanes = {s["id"]: s["lane"] for s in film["shots"]}
    assert lanes["S01-01"] == "STILL_3D" and lanes["S02-01"] == "HELPER" and lanes["S02-02"] == "VIDEO_3D"
    j4 = next(s for s in film["shots"] if s["id"] == "S02-02")
    assert [c["frames"] for c in j4["ltx_clips"]] == [145, 145] and j4["ltx_clips"][1]["overlap_frames"] == 8
    spine = P.spine_of(film)
    assert spine["total_frames"] == sum(s["duration_frames"] for s in film["shots"]) == round(59.5 * 24)
    assert [g["id"] for g in spine["segments"]] == ["S01", "S02", "S03"]
    m = P.edit_manifest(film, {"path": "f", "sha256": "0" * 64}, {"path": "s", "sha256": "0" * 64})
    cuts = [c for sc in m["scenes"] for c in sc["cuts"]]
    assert len(cuts) == len(film["shots"]) - 1 and all(c["cut_type"] == "STRAIGHT_CUT" for c in cuts)


def test_the_ltx_take_is_the_upscaled_copy_of_a_job_that_ran_on_the_asked_base(tmp_path):
    pod = tmp_path / "pod"
    (pod / "ltx").mkdir(parents=True)
    (pod / "ltx_up").mkdir()
    jobs = {"jobs": [{"id": "c1.ltx23.line.s42", "clip_id": "c1", "base": "ltx23"}, {"id": "c1.ltx25.colour.s42", "clip_id": "c1",
                                                                                      "base": "ltx25"},
                     {"id": "c1.ltx25.colour.s1337", "clip_id": "c1", "base": "ltx25"}]}
    (pod / "ltx_jobs.json").write_text(json.dumps(jobs))
    for jid, rc in (("c1.ltx23.line.s42", 0), ("c1.ltx25.colour.s42", 1), ("c1.ltx25.colour.s1337", 0)):
        (pod / "ltx" / f"{jid}.mp4").write_bytes(b"x")
        (pod / "ltx" / f"{jid}.json").write_text(json.dumps({"rc": rc}))
    (pod / "ltx_up" / "c1.ltx25.colour.s1337.mp4").write_bytes(b"x")
    assert P.ltx_pick(pod, "c1", base="ltx25") == (pod / "ltx_up" / "c1.ltx25.colour.s1337.mp4", "c1.ltx25.colour.s1337")
    assert P.ltx_pick(pod, "c1", base="ltx23")[1] == "c1.ltx23.line.s42"
    assert P.ltx_pick(pod, "c1", pick={"c1": "c1.ltx23.line.s42"})[0] == pod / "ltx" / "c1.ltx23.line.s42.mp4"
    assert P.ltx_pick(pod, "c2") == (None, None)


@needs_ffmpeg
def test_a_chained_j4_take_drops_its_shared_frames_and_both_parts_reach_the_master_frame(tmp_path):
    a, b = _clip(tmp_path / "a.mp4", "1920x1088", 20), _clip(tmp_path / "b.mp4", "1920x1088", 20, "testsrc2")
    cmd = P.conform_cmd([{"path": a, "skip": 0}, {"path": b, "skip": 8}], tmp_path / "o.mp4", 24)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "trim=start_frame=8" in graph and "crop=1920:1080" in graph and "scale=2560:1440" in graph and "concat=n=2" in graph
    subprocess.run(cmd, check=True)
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames,width,height", "-of", "csv=p=0", str(tmp_path / "o.mp4")],
                       capture_output=True, text=True).stdout.strip()
    assert n == "2560,1440,32"


@needs_ffmpeg
def test_the_pilot_assembles_its_window_and_a_missing_clip_stops_it_or_becomes_a_marked_slate(tmp_path):
    j5 = tmp_path / "j5"
    _clip(j5 / "S01-06.mp4", "2560x1440", 60)
    with pytest.raises(ContractError, match="clips missing"):
        P.build(RS, tmp_path / "a", ids=["S01-06", "S02-01"], j5=j5)
    rep = P.build(RS, tmp_path / "b", ids=["S01-06", "S02-01"], j5=j5, slates=True)
    assert rep["preview"] and rep["slates"] == ["S02-01"] and rep["seconds"] == 5.5
    assert rep["lane_share"] == {"VIDEO_3D": round(2.5 / 5.5, 3), "HELPER": round(3 / 5.5, 3)}
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames,width,height,r_frame_rate", "-of", "csv=p=0", str(tmp_path / "b" / rep["video"])],
                         capture_output=True, text=True).stdout.strip()
    assert out == "2560,1440,24/1,132"
    for name in ("film_shots.json", "audio_spine.json", "edit_and_grade_manifest.json", "pilot.json"):
        assert (tmp_path / "b" / name).exists()


@needs_ffmpeg
def test_an_assemble_25d_frame_folder_is_a_j5_clip(tmp_path):
    from PIL import Image
    d = tmp_path / "j5" / "S01-06" / "frames"
    d.mkdir(parents=True)
    for i in range(3):
        Image.new("RGB", (1280, 720), (40 * i, 80, 120)).save(d / f"frame_{i:06d}.png")
    row = P.sources([next(s for s in RS["shots"] if s["id"] == "S01-06")], j5=tmp_path / "j5")[0]
    assert row["missing"] is None and row["parts"][0]["frames"]
    cmd = P.conform_cmd(row["parts"], tmp_path / "o.mp4", 24)
    assert "-framerate" in cmd and "scale=2560:1440" in cmd[cmd.index("-filter_complex") + 1]
    subprocess.run(cmd, check=True)
    assert subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                           "-of", "csv=p=0", str(tmp_path / "o.mp4")], capture_output=True, text=True).stdout.strip() == "3"
