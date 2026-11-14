"""TD-339: (a) a bed row takes the best-correlating of a fixed list of widen seeds, so a pair that falls in anti-phase does not
lose its mono sum; (b) a library record may declare ``loop_window_s`` and the bed row loops only that window."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pytest

from explainer_engine.audio import acoustics, stems
from explainer_engine.episode import cue_sheet as CS
from explainer_engine.episode import sound_plan as SP
import test_av_events as AV

SR = stems.SR


def _lowpass_noise(n, seed=5, hz=120.0):
    from scipy import signal
    x = np.random.default_rng(seed).standard_normal(n).astype(np.float32)
    b, a = signal.butter(2, hz / (SR / 2))
    return signal.lfilter(b, a, x).astype(np.float32) * 5


def _corr(st):
    return float(np.corrcoef(st[:, 0], st[:, 1])[0, 1])


def _mono_db(st):
    return 20 * np.log10(float(np.sqrt(np.mean(st.mean(axis=1) ** 2))) + 1e-12)


def _chan_db(st):
    return 20 * np.log10(float(np.sqrt(np.mean(st[:, 0] ** 2))) + 1e-12)


def test_an_anti_phase_pair_picks_a_better_seed_and_the_mono_sum_holds():
    x = _lowpass_noise(SR * 4)
    bad = None
    for k in range(200):                                            # a row whose own seed puts the low band in anti-phase
        cue = f"AMB_t{k}"
        own = acoustics.widen(x, seed=acoustics.seed_of(cue))
        if _corr(own) < -0.3:
            bad = (cue, own)
            break
    assert bad, "no anti-phase example found"
    cue, own = bad
    best = stems.widen_best(x, cue)
    assert _corr(best) > _corr(own) + 0.3
    assert _mono_db(best) > _mono_db(own) + 3.0                      # the mono sum no longer collapses
    assert _chan_db(best) - _mono_db(best) < _chan_db(own) - _mono_db(own)
    assert np.array_equal(best, stems.widen_best(x, cue))             # deterministic
    # the own seed wins a tie / when it is already the best: a well-correlated row keeps its own image
    for k in range(200):
        c2 = f"AMB_u{k}"
        o2 = acoustics.widen(x, seed=acoustics.seed_of(c2))
        cands = [_corr(acoustics.widen(x, seed=acoustics.seed_of(c2 if j == 0 else f"{c2}#{j}"))) for j in range(stems.WIDEN_SEEDS)]
        if _corr(o2) == max(cands):
            assert np.array_equal(stems.widen_best(x, c2), o2)
            break


class _Take:
    def __init__(self, x):
        self.x = x

    def take(self, row, k):
        return self.x


def test_play_row_loops_only_the_declared_window():
    loud = (np.random.default_rng(1).standard_normal(SR * 2) * 0.2).astype(np.float32)
    lull = loud[: SR * 2] * 0.03
    take = np.concatenate([loud, lull])                               # 2 s of wind, then a 2 s lull
    row = {"cue_id": "AMB_w", "asset_id": "w", "layer": "ambience", "duration_s": 9.0, "gain_db": -30.0, "loop": True,
           "fade_in_s": 0.0, "fade_out_s": 0.0, "pitch": 1.0, "eq": {}, "reverb": "dry", "asset_offset_s": 0.0}
    plain = stems.play_row(row, _Take(take), 0).mean(axis=1)
    win = stems.play_row(dict(row, loop_window_s=[0.0, 2.0]), _Take(take), 0).mean(axis=1)

    def lv(y, a, b):
        s = y[int(a * SR):int(b * SR)]
        return 20 * np.log10(float(np.sqrt(np.mean(s ** 2))) + 1e-12)
    assert lv(plain, 2.3, 3.7) < lv(plain, 0.3, 1.7) - 15              # without the window the lull plays
    spread = [lv(win, a, a + 1.0) for a in (0.3, 1.2, 2.3, 3.4, 4.5, 5.6, 6.7, 7.5)]
    assert max(spread) - min(spread) < 4.0                            # with it the bed stays level
    seam = int(2.0 * SR - 0.12 * SR)                                  # the seam: no click (largest step against the bed's own)
    steps = np.abs(np.diff(win))
    assert steps[seam:seam + int(0.3 * SR)].max() < 4 * np.percentile(steps, 99)


def test_the_cue_sheet_carries_the_declared_loop_window(tmp_path):
    shot, script = AV._map(actions=[{"kind": "route_arrow", "at_word": "walks", "until_word": "coast", "from": "toba",
                                     "to": "shinfa"}])
    plan = SP.build(script, fps=AV.FPS)
    lib = AV._lib(tmp_path / "lib", plan["classes"])
    man = json.loads((lib / "manifest.json").read_text())
    for it in man["items"]:
        if it["id"].startswith("wind_"):
            it["loop_window_s"] = [0.0, 0.5]
    (lib / "manifest.json").write_text(json.dumps(man))
    src = SP.resolve(plan, lib)
    rows = CS.build(plan, src, lib)["rows"]
    wind = [r for r in rows if r["cue_id"].startswith("AMB_") and r["cue_id"].endswith("_wind")]
    assert wind and all(r["loop_window_s"] == [0.0, 0.5] for r in wind)
    other = [r for r in rows if r["layer"] == "ambience" and r not in wind]
    assert all("loop_window_s" not in r for r in other)
