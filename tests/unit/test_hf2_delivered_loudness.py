"""HF-2 (Truce 1914 assembly, FL-403, TD-302): G8 writes the delivered mix, G9 muxes it, G10 measures the master."""
from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

import numpy as np

from explainer_engine.episode import run as RUN
from explainer_engine.qa import gates as G
from explainer_engine.qa import targets as T


def _stereo_wav(path: Path, seconds: float, amp: float, rate: int = 48000) -> Path:
    n = int(seconds * rate)
    t = np.arange(n) / rate
    x = amp * (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 1330 * t) * (np.sin(2 * np.pi * 0.7 * t) > 0))
    s = (np.repeat(x[:, None], 2, axis=1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(s.tobytes())
    return path


def test_a_quiet_mix_is_delivered_inside_bp50s_band(tmp_path):
    stems = tmp_path / "stems"
    stems.mkdir()
    raw = _stereo_wav(stems / "mix.wav", 12.0, 0.01)          # about -45 LUFS: far under the band
    raw_sha = raw.read_bytes()
    assert T.measure_file(raw)["lufs"] < -35
    rows, meas = RUN.deliver_mix(stems)
    prof = T.PROFILES["long"]
    assert prof["pass_band"][0] <= meas["delivered"]["lufs"] <= prof["pass_band"][1]
    assert meas["delivered"]["true_peak"] <= prof["true_peak_max"]
    assert (stems / "mix_delivered.wav").is_file() and raw.read_bytes() == raw_sha   # the raw mix is kept
    by = {r["gate"]: r for r in rows}
    assert by["delivered_mix_loudness"]["status"] == G.PASS and by["delivered_mix_true_peak"]["status"] == G.PASS
    assert meas["raw"]["lufs"] < meas["delivered"]["lufs"]


def test_the_loudness_rows_fail_outside_the_band():
    low = RUN._loudness_rows("master", {"lufs": -26.0, "true_peak": -3.0}, "the master file")
    hot = RUN._loudness_rows("master", {"lufs": -14.0, "true_peak": 0.5}, "the master file")
    assert [r["status"] for r in low] == [G.FAIL, G.PASS]
    assert hot[1]["status"] == G.FAIL and hot[0]["status"] == G.PASS


def test_the_assembly_refuses_without_the_delivered_mix(tmp_path, monkeypatch):
    root = tmp_path / "ep"
    (root / "audio" / "stems").mkdir(parents=True)
    (root / "audio" / "stems" / "mix.wav").write_bytes(b"RIFF")        # the raw mix alone is not enough
    ep = RUN.Episode.__new__(RUN.Episode)
    ep.root, ep.fps, ep.size, ep.chunks, ep.chunk_seconds = root, 24, (64, 36), None, None
    ep.path = lambda rel: root / rel
    ep.manifest = {"episode_id": "ep"}
    ep.timed_script = lambda: {"shots": []}
    monkeypatch.setattr(RUN, "_records", lambda e: [{"shot_id": "S1", "clip_path": "x.mp4", "total_frames": 1}])
    rows, outs = RUN.stage_assemble(ep, False)
    assert rows[0]["gate"] == "the_delivered_mix_exists" and rows[0]["status"] == G.FAIL and outs == {}


def test_the_rehearsal_chain_muxes_the_delivered_mix_and_measures_the_master(tmp_path, monkeypatch):
    from tests.unit import test_v43_runner as base
    base.test_a_small_episode_rehearses_the_whole_chain(tmp_path, monkeypatch)
    root = tmp_path / "ep_toba"
    assert (root / "audio" / "stems" / "mix_delivered.wav").is_file()
    rows = {r["gate"] for r in json.loads((root / "qa" / "acceptance_report.json").read_text())["acceptance"]["gates"]}
    assert {"master_loudness", "master_true_peak"} <= rows
    sound = {r["gate"] for r in json.loads((root / "production" / "stages" / "sound.json").read_text())["rows"]}
    assert {"delivered_mix_loudness", "delivered_mix_true_peak"} <= sound
