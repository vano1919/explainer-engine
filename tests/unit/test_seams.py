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
    """Offsets of spliced takes come from duration(): an MP3's container length overstates it by the encoder padding."""
    p = tmp_path / "take.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=2", "-c:a", "libmp3lame", str(p)],
                   check=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    probe = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                  "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True).stdout)
    assert abs(seams.duration(p) - len(raw) / 2 / 48000) < 1e-6
    assert seams.duration(p) < probe
