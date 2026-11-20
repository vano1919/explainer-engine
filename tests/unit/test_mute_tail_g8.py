"""Step 1.5 (D-139): G8 applies the clip record's ``mute_tail_from_s`` (mix.py did; the runner did not)."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from explainer_engine.audio import stems as ST

SR = 48000


def test_mute_from_fades_then_silences_and_never_clicks():
    x = np.ones(SR, np.float32) * 0.5
    y = ST.mute_from(x, SR, 0.5, fade_ms=80)
    assert np.allclose(y[: int(0.5 * SR)], 0.5)                       # before the point: untouched
    assert y[int(0.5 * SR)] > 0.49 and y[int(0.5 * SR) + int(0.08 * SR) - 1] < 0.01   # a ramp, not a step
    assert np.all(y[int(0.5 * SR) + int(0.08 * SR):] == 0.0)
    assert np.abs(np.diff(y)).max() < 0.01                            # no sample-to-sample jump (no click)


def test_a_point_past_the_end_or_none_changes_nothing_and_zero_silences_all():
    x = np.ones(1000, np.float32)
    assert np.array_equal(ST.mute_from(x, SR, 5.0), x)
    assert np.array_equal(ST.mute_from(x, SR, None), x)
    assert not ST.mute_from(x, SR, 0.0, fade_ms=0).any()


def _clip(path: Path, seconds=2.0):
    t = np.arange(int(seconds * SR)) / SR
    pcm = (np.sin(2 * np.pi * 220 * t) * 0.4 * 32767).astype("<i2").tobytes()
    raw = path.with_suffix(".s16")
    raw.write_bytes(pcm)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", str(raw), str(path)], check=True)


def test_the_runner_mutes_the_tail_of_a_record_that_carries_the_field_and_names_the_shot(tmp_path):
    from explainer_engine.episode import run as RUN
    from explainer_engine.videolane import voice as VV
    clip = tmp_path / "S01_SH001.wav"
    _clip(clip)
    ep = SimpleNamespace(path=lambda rel: tmp_path / rel)
    ca = {"S01_SH001": {"path": str(clip), "speech": [], "speaker": None}}
    rec = {"mute_tail_from_s": 1.5, "in_s": 0.5}                       # raw-clip seconds: 1.0 s into the trimmed clip
    row = RUN._mute_clip_tail(ep, "S01_SH001", clip, rec, ca)
    assert row["shot_id"] == "S01_SH001" and abs(row["mute_from_s"] - 1.0) < 1e-6
    y = VV.read_mono(Path(ca["S01_SH001"]["path"]), SR)
    assert np.abs(y[: int(0.9 * SR)]).max() > 0.3                      # the speech before the point stays
    assert np.abs(y[int(1.15 * SR):]).max() < 1e-3                     # the tail is gone
    assert ca["S01_SH001"]["path"] != str(clip)                        # the raw clip is never overwritten


def test_the_runner_only_calls_it_when_the_record_has_the_field():
    src = (Path(__file__).resolve().parents[2] / "explainer_engine" / "episode" / "run.py").read_text(encoding="utf-8")
    assert 'if d.get("mute_tail_from_s") is not None' in src and 'rep["muted_tails"] = muted_tails' in src
