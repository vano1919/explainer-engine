"""CLIP-01..12 (CP-09, CP-10): a clip with no or wrong audio, a wrong frame rate or size, black, blown or frozen frames, or a first
frame that is not its keyframe is a visible row; `production_gate` shows the keyframe and clip checks (or their absence).
Pure rows on hand-built dicts and arrays; the ffmpeg part skips when ffmpeg is absent. Every threshold is read from the registry."""
from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction

import numpy as np
import pytest

from explainer_engine import production_gate as G
from explainer_engine.qa import targets
from explainer_engine.standards import sourced_rules as SR
from explainer_engine.training import video_qa as V

T = lambda key: SR.T("BP-164", key)  # noqa: E731
FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe(**kw):
    p = {"fps": Fraction(24), "avg_fps": Fraction(24), "frames": 49, "width": 1920, "height": 1088, "pix_fmt": "yuv420p",
         "has_audio": True, "video_duration": 49 / 24, "audio_duration": 49 / 24}
    p.update(kw)
    return p


def rules(found):
    return {f["rule"]: f["status"] for f in found}


def test_container_rows_fps_frames_size_audio_presence_and_length():
    assert rules(V.container_findings(probe(), fps_expected=24)) == {}
    assert rules(V.container_findings(probe(fps=Fraction(30), avg_fps=Fraction(30)), fps_expected=24)) == {"CLIP-01": "FAIL"}
    assert rules(V.container_findings(probe(avg_fps=Fraction(2397, 100)), fps_expected=24)) == {"CLIP-01": "FAIL"}   # variable rate
    assert rules(V.container_findings(probe())) == {"CLIP-01": "REVIEW"}                                          # no manifest fps: visible
    assert rules(V.container_findings(probe(frames=48), fps_expected=24)) == {"CLIP-02": "REVIEW"}
    assert rules(V.container_findings(probe(width=1000, height=700), fps_expected=24)) == {"CLIP-03": "REVIEW"}
    assert rules(V.container_findings(probe(has_audio=False), fps_expected=24, has_dialogue=True)) == {"CLIP-04": "FAIL"}
    assert rules(V.container_findings(probe(has_audio=False), fps_expected=24, has_dialogue=False)) == {}
    tol = T("av_duration_tol_frames") / 24
    assert rules(V.container_findings(probe(audio_duration=49 / 24 + tol * 5), fps_expected=24)) == {"CLIP-05": "REVIEW"}
    assert rules(V.container_findings(probe(audio_duration=49 / 24 + tol / 2), fps_expected=24)) == {}


def test_audio_rows_peak_speech_coverage_and_silence():
    ceiling = targets.PROFILES["long"]["true_peak_max"]
    over = V.audio_findings({"true_peak": ceiling + 1.0}, expect_speech=True, transcript_words=[])
    assert rules(over) == {"CLIP-06": targets.true_peak_verdict(ceiling + 1.0)}                # the severity is BP-50's, not ours
    assert V.audio_findings({"true_peak": ceiling - 3.0}, expect_speech=True, transcript_words=[]) == []
    words = ["one"] * T("spoken_words_max_in_silent_shot")
    assert rules(V.audio_findings({}, expect_speech=False, transcript_words=words)) == {"CLIP-07": "REVIEW"}
    assert V.audio_findings({}, expect_speech=False, transcript_words=words[:-1]) == []
    assert rules(V.audio_findings({}, expect_speech=None)) == {"CLIP-07": "REVIEW"}            # expectation not given: visible
    assert "no transcript" in V.audio_findings({}, expect_speech=False, transcript_words=None)[0]["msg"]
    heard = "the king rode north".split()
    assert V.audio_findings({}, expect_speech=True, transcript_words=heard, dialogue_text="the king rode north at dawn") == []
    assert rules(V.audio_findings({}, expect_speech=True, transcript_words=["hello", "world"],
                                  dialogue_text="the king rode north at dawn")) == {"CLIP-08": "REVIEW"}
    assert rules(V.audio_findings({}, expect_speech=True, transcript_words=None, dialogue_text="the king")) == {"CLIP-08": "REVIEW"}
    silent = V.audio_findings({"silence_share": T("silence_share_max") + 0.1}, expect_speech=True, has_dialogue=True,
                              transcript_words=[])
    assert rules(silent) == {"CLIP-09": "REVIEW"}
    assert V.audio_findings({"silence_share": 0.9}, expect_speech=False, has_dialogue=False, transcript_words=[]) == []


def moving(n=20, size=(90, 160)):
    rng = np.random.default_rng(1)
    return rng.integers(60, 200, (n, *size), dtype=np.uint8)


def test_frame_rows_black_frozen_and_keyframe():
    assert V.frame_findings(moving()) == []
    black = moving()
    black[3] = 0
    assert rules(V.frame_findings(black)) == {"CLIP-10": "REVIEW"}
    blown = moving()
    blown[5] = 255
    assert rules(V.frame_findings(blown)) == {"CLIP-10": "REVIEW"}
    frozen = moving()
    frozen[8:] = frozen[8]                                                   # the last 12 frames are one picture
    assert 12 - 1 > T("frozen_run_frames") and rules(V.frame_findings(frozen)) == {"CLIP-11": "REVIEW"}
    assert V.frame_findings(frozen, animated=False) == []                    # a hold is meant to stand still
    cv2 = pytest.importorskip("cv2")  # noqa: F841 - the shared perceptual hash (training/footage.py) is OpenCV's
    frames = moving()
    assert V.frame_findings(frames, keyframe=frames[0].copy()) == []
    shifted = np.clip(frames[0].astype(int) + 40, 0, 255).astype(np.uint8)
    assert rules(V.frame_findings(frames, keyframe=shifted)) == {"CLIP-12": "REVIEW"}
    assert rules(V.frame_findings(frames, keyframe=frames[7].copy())) == {"CLIP-12": "REVIEW"}      # another picture entirely


def test_every_threshold_is_in_the_registry_and_a_hypothesis():
    r = SR.rule("BP-164")
    assert r["status"] == "hypothesis" and r["severity"] == "REVIEW" and "explainer_engine/training/video_qa.py" in r["enforced_by"]
    assert {"av_duration_tol_frames", "spoken_words_max_in_silent_shot", "dialogue_coverage_min", "silence_share_max", "black_luma_max",
            "blown_luma_min", "flat_luma_std_max", "frozen_run_frames", "frozen_diff_max", "frame0_mean_abs_diff_max",
            "frame0_dhash_max", "analysis_size", "silence_noise_db", "silence_min_s"} <= set(r["thresholds"])


def test_transcript_comes_from_a_file_never_a_paid_read(tmp_path):
    words = tmp_path / "words.json"
    words.write_text(json.dumps({"words": [{"text": "the", "start": 0, "end": 0.2, "type": "word"},
                                           {"text": " ", "start": 0.2, "end": 0.3, "type": "spacing"},
                                           {"text": "king", "start": 0.3, "end": 0.6, "type": "word"}]}), encoding="utf-8")
    assert V.transcript_for("clip.mp4", words) == ["the", "king"]
    plain = tmp_path / "t.txt"
    plain.write_text("the king rode", encoding="utf-8")
    assert V.transcript_for("clip.mp4", plain) == ["the", "king", "rode"]
    assert V.transcript_for("clip.mp4", None) is None            # nothing asked for, nothing transcribed


def make(tmp_path, name, *, fps=24, frames=49, audio=True, size="320x192"):
    out = tmp_path / name
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
    cmd += ["-frames:v", str(frames), "-c:v", "mpeg4", "-pix_fmt", "yuv420p"] + (["-c:a", "aac", "-shortest"] if audio else ["-an"]) + [str(out)]
    subprocess.run(cmd, check=True)
    return out


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg absent")
def test_real_clips_probe_and_rows(tmp_path):
    ok = make(tmp_path, "ok.mp4")
    p = V.probe_container(ok)
    assert (p["fps"], p["frames"], p["width"], p["height"], p["has_audio"]) == (Fraction(24), 49, 320, 192, True)
    m, found = V.clip_findings(ok, fps="24", expect_speech=False, transcript=[])
    assert [f["rule"] for f in found] == [] and m["audio"]["true_peak"] < targets.PROFILES["long"]["true_peak_max"]
    assert rules(V.clip_findings(make(tmp_path, "slow.mp4", fps=30), fps="24", expect_speech=False, transcript=[])[1])["CLIP-01"] == "FAIL"
    mute = make(tmp_path, "mute.mp4", audio=False)
    assert V.probe_container(mute)["has_audio"] is False
    assert rules(V.clip_findings(mute, fps="24", dialogue="the king rode north", transcript=[])[1])["CLIP-04"] == "FAIL"
    assert rules(V.clip_findings(make(tmp_path, "f48.mp4", frames=48), fps="24", expect_speech=False, transcript=[])[1])["CLIP-02"] == "REVIEW"


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg absent")
def test_the_cli_prints_the_rows_and_writes_the_sidecar(tmp_path, capsys):
    from explainer_engine.training import __main__ as cli
    clip = make(tmp_path, "ok.mp4")
    code = cli.main(["video-qa", str(clip), "--fps", "24", "--expect-speech", "no", "--write"])
    out = json.loads(capsys.readouterr().out)
    side = json.loads((tmp_path / "ok.mp4.video_qa.json").read_text(encoding="utf-8"))
    assert code == 0 and side["findings"] == out["findings"] and side["verdict"] == out["verdict"]
    assert any(f["rule"] == "CLIP-07" and "no transcript" in f["msg"] for f in side["findings"])   # nobody transcribed: said, not silent


def episode(tmp_path, shots=("S01", "S02")):
    (tmp_path / "film_shots.json").write_text(json.dumps({"shots": [{"id": s} for s in shots]}), encoding="utf-8")
    return tmp_path


def log(tmp_path, *recs):
    (tmp_path / "qa_log.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")


def row(tmp_path, name):
    return next((r for r in G.gates(tmp_path) if r["gate"] == name), None)


def test_gate_row_keyframes_waits_blocks_and_passes(tmp_path):
    episode(tmp_path)
    assert row(tmp_path, "keyframes")["status"] == "WAIT"                                    # film_shots.json, no log
    log(tmp_path, {"shot": "S01", "status": "PASS"})
    assert row(tmp_path, "keyframes")["status"] == "WAIT" and "1 of 2" in row(tmp_path, "keyframes")["detail"]
    log(tmp_path, {"shot": "S01", "status": "PASS"}, {"shot": "S02", "status": "FAIL"})
    assert row(tmp_path, "keyframes")["status"] == "BLOCKED"
    log(tmp_path, {"shot": "S01", "status": "PASS"}, {"shot": "S02", "status": "REVIEW"})
    assert row(tmp_path, "keyframes")["status"] == "WAIT"                                    # a REVIEW is not a pass
    log(tmp_path, {"shot": "S01", "status": "PASS"}, {"shot": "S02", "status": "PASS"})
    assert row(tmp_path, "keyframes")["status"] == "PASS"
    assert row(tmp_path, "clips") is None


def test_gate_row_clips_waits_blocks_and_passes(tmp_path):
    clips = tmp_path / "clips"
    clips.mkdir()
    (clips / "a.mp4").write_bytes(b"")
    assert row(tmp_path, "clips")["status"] == "WAIT" and row(tmp_path, "keyframes") is None
    (clips / "a.mp4.video_qa.json").write_text(json.dumps({"findings": [{"rule": "CLIP-07", "status": "REVIEW", "msg": "x"}]}), encoding="utf-8")
    r = row(tmp_path, "clips")
    assert r["status"] == "PASS" and "1 REVIEW" in r["detail"]
    (clips / "a.mp4.video_qa.json").write_text(json.dumps({"findings": [{"rule": "CLIP-04", "status": "FAIL", "msg": "x"}]}), encoding="utf-8")
    assert row(tmp_path, "clips")["status"] == "BLOCKED"


def test_a_still_picture_episode_gets_neither_row(tmp_path):
    assert row(tmp_path, "keyframes") is None and row(tmp_path, "clips") is None


def test_check_fast_action_rhythm_flags_a_clip_that_holds_too_much():
    from explainer_engine.training import video_qa as V
    bad = V.check_fast_action_rhythm({"rhythm": {"hold_share": 0.48}, "frozen_run_frames": 20})
    assert [f["rule"] for f in bad] == ["LT-80", "LT-80"] and all(f["status"] == "REVIEW" for f in bad)
    assert V.check_fast_action_rhythm({"rhythm": {"hold_share": 0.30}, "frozen_run_frames": 6}) == []
    assert V.check_fast_action_rhythm({"rhythm": {"hold_share": 0.9}}, zone_mode="calm_story") == []
