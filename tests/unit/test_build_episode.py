"""production/build_episode.py: shots as long as their lines, narration placed on the film's clock, text-matched shot plan, clip cache. build_shot is faked."""
from __future__ import annotations

import json
import subprocess

import pytest

from explainer_engine.production import build_episode as BE


def _tone(path, secs):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=300:duration={secs}", str(path)], check=True)


def _fake_build_shot(spec_path, out_mp4, cache_dir=None, workdir=None, tile_dir=None):
    spec = json.loads(open(spec_path).read())
    FAKE_CALLS.append((spec["id"], spec["seconds"], spec.get("line_t")))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=gray:s=320x180:r=24:d={spec['seconds']}", "-pix_fmt", "yuv420p", str(out_mp4)], check=True)
    return {}


FAKE_CALLS: list = []


def test_shot_length_is_rounded_up_to_whole_frames():
    s = BE.shot_seconds([3.08], 0.25, 0.3, 0.45)
    assert s * 24 == int(s * 24) and s >= 3.78 and s - 3.78 < 1 / 24
    assert BE.shot_seconds([1.0, 2.0], 0.25, 0.3, 0.45) == pytest.approx(round((0.25 + 3.0 + 0.3 + 0.45) * 24 + 0.4999) / 24, abs=1 / 24)


def test_schedule_places_each_line_on_the_film_clock():
    rows = BE.schedule([{"id": "A", "lines": ["l1", "l2"]}, {"id": "B", "lines": ["l3"]}], {"l1": 1.0, "l2": 2.0, "l3": 1.5}, 0.25, 0.3, 0.45)
    assert rows[0]["lines"] == [("l1", 0.25), ("l2", 1.55)]
    assert rows[1]["start"] == pytest.approx(rows[0]["seconds"]) and rows[1]["lines"][0][1] == pytest.approx(rows[1]["start"] + 0.25, abs=1e-3)


def test_plan_from_shot_plan_matches_text_exactly():
    plan = {"shots": [{"shot": "S01_SH001", "segment": "S01", "lines": [["narrator", "Hello  there."]]}, {"shot": "S09_SH001", "segment": "S09", "lines": []}]}
    lines = [{"line_id": "S01_L001", "text": "Hello there."}]
    assert BE.plan_from_shot_plan(plan, lines, ["S01"]) == [{"id": "S01_SH001", "spec": "shots/S01_SH001.json", "lines": ["S01_L001"]}]
    with pytest.raises(BE.BuildEpisodeError):
        BE.plan_from_shot_plan(plan, [{"line_id": "x", "text": "other"}], ["S01"])
    with pytest.raises(BE.BuildEpisodeError):
        BE.plan_from_shot_plan(plan, lines + [{"line_id": "dup", "text": "Hello there."}], ["S01"])


@pytest.fixture
def episode(tmp_path, monkeypatch):
    FAKE_CALLS.clear()
    monkeypatch.setattr(BE.BS, "build_shot", _fake_build_shot)
    (tmp_path / "reads").mkdir(); (tmp_path / "shots").mkdir()
    _tone(tmp_path / "reads" / "a.wav", 1.0); _tone(tmp_path / "reads" / "b.wav", 1.5)
    (tmp_path / "durations.json").write_text(json.dumps([{"line_id": "L1", "file": "a.wav", "measured_s": 1.0}, {"line_id": "L2", "file": "b.wav", "measured_s": 1.5}]))
    (tmp_path / "film.json").write_text("{}")
    (tmp_path / "p.jpeg").write_bytes(b"x")
    for i in ("S1", "S2"):
        (tmp_path / "shots" / f"{i}.json").write_text(json.dumps({"id": i, "photo": "../p.jpeg", "film_file": "x", "seconds": 1, "camera": {"move": "zoom_in"}}))
    (tmp_path / "shots" / "M.json").write_text(json.dumps({"kind": "map", "id": "M", "seconds": 1, "line_t": [0.4, 5.4], "film_file": "../film.json"}))
    ep = {"id": "t", "film_file": "film.json", "durations": "durations.json", "audio_dir": "reads",
          "shots": [{"id": "S1", "spec": "shots/S1.json", "lines": ["L1"]}, {"id": "M", "spec": "shots/M.json", "lines": ["L2"]}, {"id": "S2", "spec": "shots/S2.json", "lines": []}]}
    (tmp_path / "ep.json").write_text(json.dumps(ep))
    return tmp_path


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def test_builds_the_film_with_voice_and_reuses_clips(episode):
    log = BE.build_episode(episode / "ep.json", episode / "o.mp4")
    assert abs(_dur(episode / "o.mp4") - log["seconds"]) < 0.15 and log["paid_calls"] == 0
    assert [c[0] for c in FAKE_CALLS] == ["S1", "M", "S2"] and FAKE_CALLS[0][1] == log["shots"][0]["seconds"]
    assert FAKE_CALLS[1][2][1] <= FAKE_CALLS[1][1] - 0.09            # the map's front finishes inside the shot
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(episode / "o.mp4")], capture_output=True, text=True).stdout
    assert "audio" in out and "video" in out
    n = len(FAKE_CALLS)
    again = BE.build_episode(episode / "ep.json", episode / "o.mp4")
    assert len(FAKE_CALLS) == n and sorted(again["reused"]) == ["M", "S1", "S2"]


def test_missing_read_or_duration_is_an_error(episode):
    (episode / "reads" / "a.wav").unlink()
    with pytest.raises(BE.BuildEpisodeError):
        BE.build_episode(episode / "ep.json", episode / "o.mp4")
    ep = json.loads((episode / "ep.json").read_text()); ep["shots"][0]["lines"] = ["ZZ"]
    (episode / "ep.json").write_text(json.dumps(ep))
    with pytest.raises(BE.BuildEpisodeError):
        BE.build_episode(episode / "ep.json", episode / "o.mp4")
