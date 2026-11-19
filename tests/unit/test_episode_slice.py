"""A slice of an episode (episode/slice.py): the shots cut out, the whole-episode gates NOT_APPLICABLE, the stamp, the read cut."""
import json
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from explainer_engine.core.errors import ConfigError
from explainer_engine.episode import run as RUN
from explainer_engine.episode import slice as SL
from explainer_engine.qa import gates as G

ROOT = Path(__file__).resolve().parents[2]
TRUCE = ROOT / "episodes" / "ep_truce_1914"
FIRST_60 = "S01_SH001..S02_SH005"


def test_parse_shots_range_list_and_errors():
    ids = ["A1", "A2", "A3", "B1"]
    assert SL.parse_shots("A2..B1", ids) == ["A2", "A3", "B1"]
    assert SL.parse_shots("B1,A1", ids) == ["A1", "B1"]
    with pytest.raises(ConfigError):
        SL.parse_shots("A3..A1", ids)
    with pytest.raises(ConfigError):
        SL.parse_shots("A1..Z9", ids)
    with pytest.raises(ConfigError):
        SL.parse_shots("Z9", ids)


def test_not_applicable_neither_passes_nor_blocks_and_is_listed():
    rows = [G.row("a", True, "ok"), G.not_applicable("whole", "about the full episode", {"x": 1})]
    v = G.verdict(rows)
    assert v["status"] == G.PASS and v["not_applicable"] == ["whole"]
    assert G.verdict([G.not_applicable("whole", "d")])["status"] == G.NOT_RUN     # only NA rows: nothing was measured
    assert G.verdict(rows + [G.row("b", False, "no")])["status"] == G.FAIL


def test_scoped_script_keeps_only_the_slice():
    full = json.loads((TRUCE / "story" / "production_script.json").read_text(encoding="utf-8"))
    keep = SL.parse_shots(FIRST_60, [s["shot_id"] for s in full["shots"]])
    sc = SL.scoped_script(full, keep)
    assert [s["shot_id"] for s in sc["shots"]] == keep and len(keep) == 10
    assert {l["line_id"] for l in sc["audio_lines"]} == {i for s in sc["shots"] for i in s["audio_line_ids"]}
    assert {s["segment_id"] for s in sc["segments"]} == {"S01", "S02"}
    assert len(full["shots"]) == 84      # the source is not changed


def test_a_slice_runs_g1_on_the_slice_and_shows_the_whole_episode_gates_as_not_applicable(tmp_path):
    out = tmp_path / "ep_truce_1914"
    sl = SL.build(TRUCE, out, FIRST_60)
    assert sl["shippable"] is False and sl["stamp"] == "slice, not shippable" and len(sl["shots"]) == 10
    assert (out / "SLICE_NOT_SHIPPABLE.txt").is_file() and (out / SL.FULL_SCRIPT_REL).is_file()
    ep = RUN.Episode(out)
    rec = RUN.run_stage(ep, "script")
    by = {r["gate"]: r for r in rec["rows"]}
    for gate in ("video_share_against_target", "route_mix_60_30_10", "speaker_shots_are_video"):
        assert by[gate]["status"] == G.NOT_APPLICABLE, gate
        assert "on the full episode" in by[gate]["detail"]
    assert by["video_share_against_target"]["measured"]["full_episode_status"] in ("FAIL", "REVIEW", "PASS")
    assert "script_lints_outside_the_slice" in by
    assert rec["slice"] == {"stamp": "slice, not shippable", "shippable": False, "first": "S01_SH001", "last": "S02_SH005",
                            "shots": 10}
    assert rec["verdict"]["status"] in ("PASS", "REVIEW") and rec["verdict"]["not_applicable"]
    assert not rec["verdict"]["failed"]


def test_a_full_episode_keeps_its_whole_episode_gates(tmp_path):
    ep = RUN.Episode(TRUCE)
    assert ep.slice is None
    rows = RUN._whole_episode_rows(ep, lambda d: [G.row("video_share_against_target", False, "d", 0.5)], ep.script)
    assert rows[0]["status"] == G.FAIL


def test_a_slice_cannot_be_written_into_its_source(tmp_path):
    with pytest.raises(ConfigError):
        SL.build(TRUCE, TRUCE / "slice_here", FIRST_60)


def _wav(path: Path, seconds: float, rate: int = 16000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_the_read_is_cut_to_the_slice_window_and_rebased(tmp_path):
    clock = tmp_path / "clock"
    clock.mkdir()
    _wav(clock / "narration.wav", 10.0)
    (clock / "timing.json").write_text(json.dumps({"fps": 24, "shots": {
        "A": {"start_frame": 0, "frames": 48}, "B": {"start_frame": 48, "frames": 72}, "C": {"start_frame": 120, "frames": 48}}}))
    (clock / "narration.scribe.json").write_text(json.dumps({"source": "t", "seconds": 7.0, "words": [
        {"text": "a", "start": 0.5, "end": 0.9}, {"text": "b", "start": 2.5, "end": 2.9}, {"text": "c", "start": 5.2, "end": 5.6}]}))
    (clock / "line_reads.json").write_text(json.dumps({"schema": "line_reads/1", "lines": {"L1": {"seconds": 1}, "L9": {}}}))
    out = tmp_path / "out"
    info = SL.cut_read(clock, out, ["B", "C"], ["L1"])
    assert info["window_s"] == [2.0, 7.0] and info["words"] == 2
    sc = json.loads((out / "audio" / "narration.scribe.json").read_text())
    assert [w["start"] for w in sc["words"]] == [0.5, 3.2]
    assert list(json.loads((out / "audio" / "line_reads.json").read_text())["lines"]) == ["L1"]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(out / "audio" / "narration.wav")], capture_output=True, text=True).stdout)
    assert abs(dur - 5.0) < 0.05
