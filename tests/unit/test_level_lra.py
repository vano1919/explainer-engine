"""BP-59 "after levelling": the narration stem's loudness range (EBU R 128 LRA) must come out of ``audio/level.py`` under ``stem_lra_max``.

Synthetic read: sentences at the RMS swing the leveler was built for (-35.5 .. -22.6 dB, ``audio/level.py`` docstring), syllable-like amplitude modulation,
fixed seed. Measured with ffmpeg ``ebur128`` and parsed by ``qa/targets.parse_ebur128`` (the same path the gates use). Real episode1 narration
(2026-11-20, measured by hand with the same filter): 7.8 LU raw -> 4.4 LU levelled; the read: 7.7 -> 4.3 (docs/PROGRESS.md).
"""
import shutil
import subprocess
import wave

import numpy as np
import pytest

from explainer_engine.audio.level import level_voice
from explainer_engine.qa import targets
from explainer_engine.standards import sourced_rules as SR

SR_HZ = 48000
SENTENCE_DB = [-35.5, -22.6, -30.0, -24.0, -33.0, -26.0, -31.0, -23.0]
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg absent")


def swinging_read(seed=7, sentences=48):
    rng = np.random.default_rng(seed)
    parts = []
    for i in range(sentences):
        n = int(rng.uniform(2.0, 3.5) * SR_HZ)
        t = np.arange(n) / SR_HZ
        x = rng.standard_normal(n) * (0.55 + 0.45 * np.sin(2 * np.pi * 4 * t + rng.uniform(0, 6)))
        parts += [x / np.sqrt(np.mean(x ** 2)) * 10 ** (SENTENCE_DB[i % len(SENTENCE_DB)] / 20), np.zeros(int(0.4 * SR_HZ))]
    return np.concatenate(parts)


def lra_of(signal, tmp_path, name):
    path = tmp_path / f"{name}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR_HZ)
        w.writeframes((np.clip(signal, -1, 1) * 32767).astype(np.int16).tobytes())
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    return targets.parse_ebur128(r.stderr)["lra"]


def test_levelling_brings_the_stem_range_under_the_bp59_limit(tmp_path):
    raw = swinging_read()
    limit = SR.T("BP-59", "stem_lra_max")
    raw_lra = lra_of(raw, tmp_path, "raw")
    levelled_lra = lra_of(level_voice(raw, SR_HZ), tmp_path, "levelled")
    assert raw_lra > limit and targets.stem_lra_verdict(raw_lra) == "FAIL"      # the test is meaningful: the raw read breaks the rule
    assert levelled_lra < raw_lra and targets.stem_lra_verdict(levelled_lra) == "PASS"
