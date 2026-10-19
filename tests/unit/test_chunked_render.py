"""2026-10-17: the 2K render died three times because the machine restarted (uptime reset, no error in any log); one big
video file cannot survive that. The assembler now writes chunks that are finished files and reuses them on the next run."""
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from test_production_script import _wav, compiled, words_for

from explainer_engine.production import __main__ as CLI
from explainer_engine.production import assemble as A

FPS = 30


def shots(n=20, seconds=5.0, **extra):
    n_frames = round(seconds * FPS)
    return [{"start_frame": k * n_frames, "end_frame": (k + 1) * n_frames, **extra} for k in range(n)]


def test_chunks_start_at_cuts_and_cover_every_shot_once():
    s = shots()
    b = A.chunk_bounds(s, FPS, 20 * 150, seconds=12)
    assert b[0][0] == 0 and b[-1][1] == len(s)
    assert all(x[1] == y[0] for x, y in zip(b, b[1:]))
    assert all((s[k1 - 1]["end_frame"] - s[k0]["start_frame"]) / FPS >= 12 for k0, k1 in b[:-1])


def test_the_last_chunk_keeps_room_for_the_closing_fade():
    s = shots(n=5, seconds=5.0)  # 25 s: a 20 s chunk would leave 5 s, and one more cut at 20 s would leave 5 s >= the minimum
    for seconds in (4, 10, 12, 20, 24):
        b = A.chunk_bounds(s, FPS, 25 * FPS, seconds=seconds)
        last = b[-1]
        assert (s[-1]["end_frame"] - s[last[0]]["start_frame"]) / FPS >= A.FADE_OUT + 1.5


def test_a_chunk_never_starts_right_after_a_dissolve_that_is_still_running():
    s = shots(n=6, seconds=5.0)
    s[2] = {**s[2], "end_frame": s[2]["start_frame"] + 15, "transition": "dissolve", "transition_seconds": 1.0}  # 0.5 s shot
    for k in range(3, 6):  # keep the frames contiguous
        s[k] = {**s[k], "start_frame": s[k - 1]["end_frame"], "end_frame": s[k - 1]["end_frame"] + 150}
    assert not A.clean_cut(s, 3, FPS)
    total = s[-1]["end_frame"]
    assert all(k0 != 3 for k0, _ in A.chunk_bounds(s, FPS, total, seconds=1))


def test_only_the_first_chunk_fades_in_and_only_the_last_fades_out():
    assert "fade=t=in" in A.chunk_look(True, False, 60) and "fade=t=out" not in A.chunk_look(True, False, 60)
    assert "fade=t=out:st=58.500" in A.chunk_look(False, True, 60) and "fade=t=in" not in A.chunk_look(False, True, 60)
    assert "fade" not in A.chunk_look(False, False, 60)
    assert A.look_filter(100.0) == A.chunk_look(True, True, 100.0)


@pytest.mark.skipif(not Path("/proc/1/cmdline").exists(), reason="needs /proc")
def test_a_lock_whose_pid_now_belongs_to_another_program_is_stale(tmp_path):
    lock = tmp_path / ".assemble.lock"
    lock.write_text("1")  # after a restart the old pid can be anything: pid 1 is alive but is not an assemble
    assert not A.lock_alive(lock)
    lock.write_text("not a pid")
    assert not A.lock_alive(lock)


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="needs ffmpeg")
def test_a_render_that_dies_before_the_join_resumes_from_its_chunks(tmp_path, monkeypatch):
    d = compiled()
    rng = np.random.default_rng(0)
    pics, snd = tmp_path / "pictures", tmp_path / "sounds"
    pics.mkdir(), snd.mkdir()
    for k, name in enumerate(["valley", "camp", "duo", "cold_hands"]):
        Image.fromarray((rng.random((180, 320, 3)) * 80 + k * 40).astype(np.uint8)).save(pics / f"{name}.png")
    sr = 48000
    _wav(snd / "wind.wav", rng.normal(0, 0.1, sr * 2))
    _wav(snd / "crackle.wav", rng.normal(0, 0.1, sr))
    _wav(snd / "pop.wav", np.sin(np.arange(sr // 4) * 0.2) * 0.5)
    _wav(snd / "tone.wav", np.sin(np.arange(sr * 2) * 2 * np.pi * 220 / sr) * 0.3)
    w = words_for(d)
    voice = np.zeros(int(w["duration"] * sr))
    for x in w["words"]:
        a, b = int(x["s"] * sr), int(x["e"] * sr)
        voice[a:b] = np.sin(np.arange(b - a) * 2 * np.pi * 150 / sr) * 0.5
    _wav(tmp_path / "narration.wav", voice)
    script, wjson, out = tmp_path / "script.json", tmp_path / "words.json", tmp_path / "out"
    d["picture_dirs"], d["sound_dirs"] = ["pictures"], ["sounds"]
    script.write_text(json.dumps(d))
    wjson.write_text(json.dumps(w))

    real_mux = A.mux
    def dies(*a, **k):
        raise RuntimeError("the machine restarted")
    monkeypatch.setattr(A, "mux", dies)
    with pytest.raises(RuntimeError):
        CLI.main(["run", str(script), str(tmp_path / "narration.wav"), str(wjson), "--out", str(out), "--size", "320x180",
                  "--chunk-seconds", "5"])
    left = sorted(p.name for p in (out / "chunks").glob("c_*.mp4"))
    assert len(left) >= 2 and not (out / "video.mp4").exists()  # the chunks are finished files; nothing half-done counts
    marks = {p.name: p.stat().st_mtime_ns for p in (out / "chunks").glob("c_*.mp4")}

    monkeypatch.setattr(A, "mux", real_mux)
    assert CLI.main(["assemble", str(script), str(out / "timed.json"), str(tmp_path / "narration.wav"), "--out", str(out),
                     "--size", "320x180", "--chunk-seconds", "5"]) == 0
    rep = json.loads((out / "assemble_report.json").read_text())
    timed = json.loads((out / "timed.json").read_text())
    assert rep["chunks"] == {"count": len(left), "reused": len(left), "left": []}  # nothing was drawn twice
    assert marks and not (out / "chunks").exists()
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(out / "video.mp4")], capture_output=True, text=True).stdout.strip()
    assert int(n) == timed["frames"] == rep["frames_written"]


def _tiny_episode(tmp_path):
    d = compiled()
    rng = np.random.default_rng(0)
    pics, snd = tmp_path / "pictures", tmp_path / "sounds"
    pics.mkdir(), snd.mkdir()
    for k, name in enumerate(["valley", "camp", "duo", "cold_hands"]):
        Image.fromarray((rng.random((180, 320, 3)) * 80 + k * 40).astype(np.uint8)).save(pics / f"{name}.png")
    sr = 48000
    _wav(snd / "wind.wav", rng.normal(0, 0.1, sr * 2))
    _wav(snd / "crackle.wav", rng.normal(0, 0.1, sr))
    _wav(snd / "pop.wav", np.sin(np.arange(sr // 4) * 0.2) * 0.5)
    _wav(snd / "tone.wav", np.sin(np.arange(sr * 2) * 2 * np.pi * 220 / sr) * 0.3)
    w = words_for(d)
    voice = np.zeros(int(w["duration"] * sr))
    for x in w["words"]:
        a, b = int(x["s"] * sr), int(x["e"] * sr)
        voice[a:b] = np.sin(np.arange(b - a) * 2 * np.pi * 150 / sr) * 0.5
    _wav(tmp_path / "narration.wav", voice)
    script, wjson = tmp_path / "script.json", tmp_path / "words.json"
    d["picture_dirs"], d["sound_dirs"] = ["pictures"], ["sounds"]
    script.write_text(json.dumps(d))
    wjson.write_text(json.dumps(w))
    return script, wjson


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="needs ffmpeg")
def test_part_by_part_draws_only_its_chunks_then_joins_when_all_are_there(tmp_path):
    from explainer_engine.production import __main__ as CLI
    script, wjson = _tiny_episode(tmp_path)
    out = tmp_path / "out"
    base = ["run", str(script), str(tmp_path / "narration.wav"), str(wjson), "--out", str(out), "--size", "320x180",
            "--chunk-seconds", "5"]
    assert CLI.main(base + ["--chunks", "0:1"]) == 0
    assert (out / "chunks" / "c_0000.mp4").exists() and not (out / "chunks" / "c_0001.mp4").exists()
    assert not (out / "video.mp4").exists()  # a part of the film is not a film
    rep = json.loads((out / "assemble_report.json").read_text())
    assert rep["chunks"]["left"] and rep["video"] is None
    assert CLI.main(base + ["--chunks", "1:99"]) == 0
    timed = json.loads((out / "timed.json").read_text())
    assert (out / "video.mp4").exists() and not (out / "chunks").exists()
    rep = json.loads((out / "assemble_report.json").read_text())
    assert rep["chunks"]["left"] == [] and rep["video"]
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(out / "video.mp4")], capture_output=True, text=True).stdout.strip()
    assert int(n) == timed["frames"]


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="needs ffmpeg")
def test_the_chunked_render_still_draws_the_accents(tmp_path, monkeypatch):
    """next-video merge (2026-10-19): the chunk loop of 10-17 and the accents of D-48 met in one draw()."""
    script, wjson = _tiny_episode(tmp_path)
    d = json.loads(script.read_text())
    d["segments"][1]["shots"][1]["accents"] = [{"kind": "slam_text", "at": "A small flame", "text": "FIRE"}]
    script.write_text(json.dumps(d))
    seen = []
    real = A.ACC.draw
    monkeypatch.setattr(A.ACC, "draw", lambda frame, acc, f, *a, **k: seen.append(f) or real(frame, acc, f, *a, **k))
    assert CLI.main(["run", str(script), str(tmp_path / "narration.wav"), str(wjson), "--out", str(tmp_path / "out"),
                     "--size", "320x180", "--chunk-seconds", "5"]) == 0
    assert seen and (tmp_path / "out" / "video.mp4").exists()


def test_a_pid_of_another_user_is_not_a_crash(tmp_path, monkeypatch):
    """CI 2026-10-19: on a non-root runner os.kill(1, 0) raises PermissionError; the pid exists but is not an assemble."""
    lock = tmp_path / ".assemble.lock"
    lock.write_text("1")

    def denied(pid, sig):
        raise PermissionError(1, "Operation not permitted")
    monkeypatch.setattr(A.os, "kill", denied)
    assert not A.lock_alive(lock)
