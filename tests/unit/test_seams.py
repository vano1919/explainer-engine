import shutil
import subprocess

import pytest

from explainer_engine.audio import seams

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def tone(path, volume):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=2", "-af", f"volume={volume}", str(path)],
                   check=True)


def test_plan_levels_chunks_to_one_loudness(tmp_path):
    paths = []
    for k, v in enumerate(["0.2", "0.1", "0.3"]):
        p = tmp_path / f"c{k}.wav"
        tone(p, v)
        paths.append(p)
    rep = seams.plan(paths)
    assert rep["spread_before_db"] > 5
    assert rep["spread_after_db"] <= seams.MAX_SPREAD_DB


def test_chain_has_gain_and_edge_fades(tmp_path):
    p = tmp_path / "c.wav"
    tone(p, "0.2")
    f = seams.chain(0, p, -2.5, 0.3)
    assert "volume=-2.500dB" in f and "afade=t=in" in f and "afade=t=out" in f and "pad_dur=0.3" in f


def test_duration_of_an_mp3_is_its_decoded_length(tmp_path):
    """One definition: decoded samples, encoder delay and padding trimmed (gapless). The fixture's length is derived from
    what was generated (seconds x rate = samples), not from ffprobe, whose container duration depends on the ffmpeg version:
    older builds count the ~25 ms delay plus padding, newer ones honour the LAME header and report the gapless length."""
    seconds, rate = 2, 44100
    samples = seconds * rate
    p = tmp_path / "take.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=f=220:r={rate}:d={seconds}",
                    "-c:a", "libmp3lame", str(p)], check=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    probe = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                  "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True).stdout)
    got = seams.duration(p)
    assert abs(got - len(raw) / 2 / 48000) < 1e-6  # the helper is the decoded sample count
    assert abs(got - samples / rate) < 0.002  # and that count is the generated length: delay/padding not included
    assert got <= probe + 1e-6  # the container never reports less than the decoded length
