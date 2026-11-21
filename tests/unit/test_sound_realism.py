"""The sound-realism gate (W1, BP-189..BP-193): each defect the realism audit measured on 2026-11-12 fails on a synthetic file
that has it, and passes when the defect is gone. The real files (the battle scene, the love scene, the overlay demo) are measured
by ``test_the_audited_files_fail`` when they are on disk (``EE_W1_DATA``)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.qa import sound_realism as R
from explainer_engine.standards import sourced_rules as SR_RULES

SR = R.SR


def voice(seconds: float, f0: float = 140.0, seed: int = 0) -> np.ndarray:
    """A speech-like burst: harmonics up to 3 kHz, syllables at about 4 Hz."""
    t = np.arange(int(seconds * SR)) / SR
    x = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 20))
    syl = 0.55 + 0.45 * np.sin(2 * np.pi * 4.1 * t + seed) ** 2
    env = np.minimum(1, t / 0.03) * np.minimum(1, (seconds - t) / 0.05)
    return (x * syl * env).astype(np.float32)


def at_db(x: np.ndarray, dbfs: float) -> np.ndarray:
    return (x * 10 ** ((dbfs - R.db(float(np.sqrt(np.mean(x ** 2))))) / 20)).astype(np.float32)


def bed(seconds: float, seed: int, lo: float = 80.0, hi: float = 2000.0) -> np.ndarray:
    """A bed that is not one steady noise: band noise with slow swells and sparse ticks (a stand-in for a real take)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    x = np.fft.irfft(spec, n)
    t = np.arange(n) / SR
    x *= 0.6 + 0.4 * np.sin(2 * np.pi * (0.2 + 0.1 * seed) * t) ** 2
    for p in rng.integers(0, n - 800, int(seconds * 3)):
        x[p:p + 400] += rng.standard_normal(400) * np.exp(-np.arange(400) / 60) * 3 * np.std(x)
    return x.astype(np.float32)


def place(buf: np.ndarray, x: np.ndarray, t: float) -> None:
    i = int(t * SR)
    buf[i:i + len(x)] += x[: len(buf) - i]


def rows(rep: dict) -> dict:
    return {r["gate"]: r["status"] for r in rep["rows"]}


def dialogue(gap_s: float, with_bed: bool) -> tuple[np.ndarray, dict]:
    """Two lines and a cut between them, either over digital silence (the battle scene) or over a bed."""
    total = 8.0
    x = np.zeros(int(total * SR), np.float32)
    if with_bed:
        x += at_db(bed(total, 1), -36.0)
    a = at_db(voice(2.0), -19.0)
    place(x, a, 1.5)
    place(x, at_db(voice(2.0, 180.0, 1), -19.0), 3.5 + gap_s)
    cut = 3.5 + gap_s / 2
    tl = {"cuts": [cut], "dialogue": [[0.0, total]], "lines": [{"id": "a", "start_s": 1.4, "end_s": cut},
                                                                {"id": "b", "start_s": cut, "end_s": total}],
          "events": [], "places": [{"start_s": 0.0, "end_s": total, "place": "plain"}]}
    return x, tl


def test_dead_air_between_lines_fails_and_a_bed_passes():
    x, tl = dialogue(1.15, with_bed=False)
    x += np.float32(1e-4) * np.random.default_rng(3).standard_normal(len(x)).astype(np.float32)   # -80 dBFS: no bed
    rep = R.measure(Path("synthetic"), tl, x=x)
    r = rows(rep)
    assert r["no_dropout"] == "FAIL" and r["dialogue_never_dead"] == "FAIL" and r["bed_not_broken_at_cut"] == "FAIL"
    assert r["pause_line_to_line"] == "REVIEW"           # BP-190 is a hypothesis: REVIEW, never FAIL
    good, tl2 = dialogue(0.45, with_bed=True)
    r2 = rows(R.measure(Path("synthetic"), tl2, x=good))
    assert r2["no_dropout"] == "PASS" and r2["dialogue_never_dead"] == "PASS" and r2["bed_not_broken_at_cut"] == "PASS"
    assert r2["pause_line_to_line"] == "PASS" and r2["bed_across_cuts"] == "PASS"


def test_the_pause_is_measured_speech_to_speech():
    x, tl = dialogue(0.9, with_bed=True)
    rep = R.measure(Path("synthetic"), tl, x=x)
    [p] = rep["measured"]["line_pauses"]
    assert abs(p["pause_s"] - 0.9) < 0.08


def test_an_intended_pause_is_allowed_up_to_the_dramatic_cap():
    x, tl = dialogue(1.2, with_bed=True)
    tl["intended_pauses"] = [[3.5, 4.7]]
    assert rows(R.measure(Path("synthetic"), tl, x=x))["pause_line_to_line"] == "PASS"


def test_a_jump_of_the_bed_at_a_cut_is_review():
    x, tl = dialogue(0.45, with_bed=False)
    cut = tl["cuts"][0]
    i = int(cut * SR)
    x[:i] += at_db(bed(cut, 2), -32.0)
    x[i:] += at_db(bed(len(x) / SR - cut, 4), -44.0)
    assert rows(R.measure(Path("synthetic"), tl, x=x))["bed_across_cuts"] == "REVIEW"


def actions(above_db: float) -> tuple[np.ndarray, dict]:
    total = 6.0
    x = at_db(bed(total, 5, 80.0, 7900.0), -34.0)        # a bed over the tick's whole spectrum: under it, no band can carry it
    evs = []
    for k, t in enumerate((1.0, 2.5, 4.0)):
        tick = voice(0.12, 900.0 + 100 * k, k) * np.exp(-np.arange(int(0.12 * SR)) / (0.03 * SR)).astype(np.float32)
        place(x, at_db(tick, -34.0 + above_db - 6.0), t)          # a short tick's 100 ms RMS sits ~6 dB under its own RMS
        evs.append({"at_s": t, "dur_s": 0.12, "class": "tick"})
    return x, {"cuts": [], "events": evs, "places": [{"start_s": 0.0, "end_s": total, "place": "map"}]}


def test_an_action_sound_under_its_bed_is_not_heard():
    x, tl = actions(-12.0)
    assert rows(R.measure(Path("synthetic"), tl, x=x))["action_sounds_heard"] == "FAIL"
    x, tl = actions(+14.0)
    rep = R.measure(Path("synthetic"), tl, x=x)
    assert rows(rep)["action_sounds_heard"] == "PASS", rep["measured"]["events"]


def three_places(same: bool) -> tuple[np.ndarray, dict]:
    parts, places, t = [], [], 0.0
    bands = [(80, 2000), (300, 6000), (60, 400)]
    for k in range(3):
        lo, hi = bands[0] if same else bands[k]
        parts.append(at_db(bed(4.0, 7 if same else k + 10, lo, hi), -35.0))
        places.append({"start_s": t, "end_s": t + 4.0, "place": f"p{k}"})
        t += 4.0
    return np.concatenate(parts), {"cuts": [4.0, 8.0], "events": [], "places": places}


def test_one_noise_under_every_place_fails():
    x, tl = three_places(same=True)
    assert rows(R.measure(Path("synthetic"), tl, x=x))["not_one_noise_everywhere"] == "FAIL"
    x, tl = three_places(same=False)
    assert rows(R.measure(Path("synthetic"), tl, x=x))["not_one_noise_everywhere"] == "PASS"


def test_the_gate_reads_its_numbers_from_the_registry_and_obeys_d59():
    assert SR_RULES.level("BP-189") == "FAIL" and SR_RULES.level("BP-192") == "FAIL" and SR_RULES.level("BP-193") == "FAIL"
    assert SR_RULES.level("BP-190") == "REVIEW" and SR_RULES.level("BP-191") == "REVIEW"
    src = Path(R.__file__).read_text(encoding="utf-8")
    reads = {(rid, key) for rid, key, _ in SR_RULES.threshold_reads(src)}
    for rid in ("BP-189", "BP-190", "BP-191", "BP-192", "BP-193"):
        assert any(r == rid for r, _ in reads), rid


DATA = Path(os.environ.get("EE_W1_DATA", "/home/user/ee-data/w1"))
OLD = [("battle/joined/battle_scene_joined.mp4", "tl/battle_old.json", {"no_dropout", "dialogue_never_dead"}),
       ("love/joined/love_scene_joined.mp4", "tl/love_old.json", {"no_dropout", "dialogue_never_dead"}),
       ("demo/demo_overlay_2min.mp4", "tl/demo_old.json", {"action_sounds_heard", "not_one_noise_everywhere"})]


@pytest.mark.parametrize("video,timeline,failing", OLD)
def test_the_audited_files_fail(video, timeline, failing):
    v, t = DATA / video, DATA / timeline
    if not v.is_file() or not t.is_file():
        pytest.skip(f"{v} is not on disk (HF vano1919/tmr-artifacts explainer-engine/...; set EE_W1_DATA)")
    rep = R.measure(v, json.loads(t.read_text(encoding="utf-8")))
    got = {r["gate"] for r in rep["rows"] if r["status"] == "FAIL"}
    assert failing <= got, got
