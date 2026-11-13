"""HF-3 (Truce 1914 assembly, FL-402, TD-303, RC-004): G8 polishes into its own file, the raw read stays."""
from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.audio import narrator_polish as NP
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import run as RUN


def _read(path: Path, seconds: float = 3.0, rate: int = 48000) -> Path:
    n = int(seconds * rate)
    t = np.arange(n) / rate
    x = (0.2 * np.sin(2 * np.pi * 180 * t) + 0.02 * np.sin(2 * np.pi * 40 * t)) * 32767
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(x.astype("<i2").tobytes())
    return path


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_the_raw_read_is_untouched_and_the_polished_copy_has_the_same_length(tmp_path):
    read = _read(tmp_path / "narration.wav")
    before = _sha(read)
    rep = RUN.polish_read(read, tmp_path / "narration_polished.wav")
    assert _sha(read) == before and rep["source_sha256"] == before
    assert rep["polished_sha256"] == _sha(tmp_path / "narration_polished.wav") != before
    assert rep["chain"] == NP.CHAIN and "highpass=f=60" in rep["chain"]
    assert abs(rep["seconds_after"] - rep["seconds_before"]) <= 1 / 30


def test_a_chain_that_moves_the_length_is_refused_and_leaves_nothing(tmp_path, monkeypatch):
    read = _read(tmp_path / "narration.wav")
    monkeypatch.setattr(NP, "CHAIN", "atempo=0.9")
    with pytest.raises(ContractError, match="1/30"):
        RUN.polish_read(read, tmp_path / "narration_polished.wav")
    assert not (tmp_path / "narration_polished.wav").exists()


def test_the_sound_stage_fingerprint_follows_the_polish_chain(tmp_path, monkeypatch):
    from tests.unit import test_v43_runner as base
    root = base._episode(tmp_path)
    ep = RUN.Episode(root)
    one = RUN.fingerprint(ep, "sound")
    monkeypatch.setattr(NP, "CHAIN", NP.CHAIN + ",volume=-1dB")
    assert RUN.fingerprint(ep, "sound") != one


def test_the_rehearsal_chain_lays_the_polished_read_and_never_writes_the_raw_one(tmp_path, monkeypatch):
    from tests.unit import test_v43_runner as base
    orig = base._wav
    shas = {}

    def _wav_and_note(path, seconds, rate=48000):
        out = orig(path, seconds, rate)
        if out.name == "narration.wav":
            shas["read"] = _sha(out)
        return out

    monkeypatch.setattr(base, "_wav", _wav_and_note)
    base.test_a_small_episode_rehearses_the_whole_chain(tmp_path, monkeypatch)
    root = tmp_path / "ep_toba"
    assert _sha(root / "audio" / "narration.wav") == shas["read"]
    assert (root / "audio" / "narration_polished.wav").is_file()
    rep = json.loads((root / "audio" / "stems_report.json").read_text())
    assert rep["narration_source"].endswith("narration_polished.wav")
    assert json.loads((root / "audio" / "narration_polished.json").read_text())["source_sha256"] == shas["read"]
