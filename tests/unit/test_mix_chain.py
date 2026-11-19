"""W6: the mix chain (audio/mix_chain) and its validators: every mix rule passes on a good fixture and fails on a bad one."""
from __future__ import annotations

import shutil
import wave

import numpy as np
import pytest
from scipy import signal

from explainer_engine.audio import duck
from explainer_engine.audio import mix_chain as MC
from explainer_engine.qa import targets as T
from explainer_engine.validators import mix as VM

SR = MC.SR
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _noise(seconds, seed, lo=None, hi=None):
    x = np.random.default_rng(seed).standard_normal(int(seconds * SR)).astype(np.float32)
    if lo:
        x = signal.sosfilt(signal.butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x).astype(np.float32)
    return x / np.abs(x).max()


def _scene(seconds=12.0):
    n = int(seconds * SR)
    voice = np.zeros(n, np.float32)
    for a in (1.0, 5.0, 9.0):                     # three spoken stretches of 2.5 s
        i = int(a * SR)
        voice[i:i + int(2.5 * SR)] = 0.25 * _noise(2.5, int(a), 150, 3500)
    st = lambda x, g: (np.stack([x, x], axis=1) * g).astype(np.float32)
    nar = st(voice, 1.0)
    mus = st(_noise(seconds, 11, 100, 8000), 0.3)
    amb = st(_noise(seconds, 12, 200, 5000), 0.1)
    sfx = np.zeros((n, 2), np.float32)
    sfx[int(3 * SR):int(3.3 * SR)] = st(_noise(0.3, 13), 0.4)
    return voice, nar, amb, sfx, mus


def _chain(**kw):
    voice, nar, amb, sfx, mus = _scene()
    return voice, MC.mix_stems(nar, amb, sfx, mus, voice, bed_duck_db=6.0, music_duck_db=duck.DEPTH_DB, **kw)


def test_the_chain_settings_are_read_from_bp_214_a_review_only_hypothesis():
    from explainer_engine.standards import sourced_rules as SRR
    r = SRR.rule("BP-214")
    assert r["status"] == "hypothesis" and r["severity"] == "REVIEW"
    t = r["thresholds"]
    assert (MC.ATTACK_MS, MC.RELEASE_MS, MC.CARVE_DB, MC.TP_MARGIN_DB, MC.GAP_MARGIN_LU) == (
        t["attack_ms"], t["release_ms"], t["carve_db"], t["tp_margin_db"], t["gap_margin_lu"])
    assert list(MC.CARVE_BAND_HZ) == t["carve_band_hz"]


def test_the_numbers_come_from_the_registry_not_from_here():
    assert MC.LUFS_TARGET == T.PROFILES["long"]["lufs"]
    assert MC.TP_MAX == T.PROFILES["long"]["true_peak_max"]
    assert MC.GAP_MIN_LU == 11.0 and MC.TIGHT_BAND == 0.5


@needs_ffmpeg
def test_own_bs1770_matches_ffmpeg_ebur128(tmp_path):
    x = np.stack([_noise(8, 1, 100, 6000) * 0.1] * 2, axis=1)
    p = tmp_path / "x.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    ref = T.measure_file(p)
    assert abs(MC.integrated_lufs(x) - ref["lufs"]) < 0.1
    assert abs(MC.true_peak_dbtp(x) - ref["true_peak"]) < 0.3


def test_the_chain_lands_on_target_with_peak_and_gap_inside_the_rules():
    voice, (stems, rec) = _chain()
    m = rec["measured"]
    assert abs(m["lufs"] - MC.LUFS_TARGET) <= MC.TIGHT_BAND               # VAL-MIX-01 on the tight band
    assert m["true_peak"] <= MC.TP_MAX                                    # VAL-MIX-02
    assert m["voice_lufs"] - m["music_lufs"] >= MC.GAP_MIN_LU             # VAL-MIX-03
    rows = VM.check_measurements(m)
    by = {r["gate"]: r["status"] for r in rows}
    assert by["VAL-MIX-01"] == "PASS" and by["VAL-MIX-02"] == "PASS" and by["VAL-MIX-03"] == "PASS"
    assert np.allclose(stems["mix"], stems["narration"] + stems["music"] + stems["ambience"] + stems["sfx"], atol=1e-5)


def test_the_voice_is_only_scaled_with_everything_else_by_the_master():
    voice, (stems, rec) = _chain()
    raw = _scene()[1]
    k = stems["narration"][int(1.5 * SR):int(3 * SR)] / np.where(np.abs(raw[int(1.5 * SR):int(3 * SR)]) > 1e-4,
                                                                   raw[int(1.5 * SR):int(3 * SR)], 1e-4)
    mask = np.abs(raw[int(1.5 * SR):int(3 * SR), 0]) > 1e-2
    spread = np.percentile(np.abs(k[mask, 0]), [10, 90])
    assert spread[1] / spread[0] < 1.3          # a gain (the limiter may dip it a little), never a filter or a duck


def test_music_gap_holds_even_when_the_music_starts_loud():
    voice, nar, amb, sfx, mus = _scene()
    stems, rec = MC.mix_stems(nar, amb, sfx, mus * 3.0, voice, bed_duck_db=6.0, music_duck_db=duck.DEPTH_DB)
    assert rec["measured"]["voice_lufs"] - rec["measured"]["music_lufs"] >= MC.GAP_MIN_LU


def test_the_carve_dips_1_to_4_khz_of_the_music_only_while_the_voice_speaks():
    voice, nar, amb, sfx, mus = _scene()
    out = MC.carve(mus, voice)
    sos = signal.butter(2, MC.CARVE_BAND_HZ, "bandpass", fs=SR, output="sos")

    def band(x, a, b):
        return float(np.sqrt(np.mean(signal.sosfilt(sos, x[int(a * SR):int(b * SR)], axis=0) ** 2)))
    speaking = 20 * np.log10(band(out, 1.6, 3.4) / band(mus, 1.6, 3.4))
    silent = 20 * np.log10(band(out, 7.9, 8.8) / band(mus, 7.9, 8.8))
    assert speaking < -MC.CARVE_DB * 0.7 and abs(silent) < 0.3


def test_the_sidechain_uses_the_named_attack_and_release():
    voice = _scene()[0]
    g = duck.duck_gain(voice, SR, len(voice), depth_db=9.0, attack_ms=MC.ATTACK_MS, release_ms=MC.RELEASE_MS)
    db = 20 * np.log10(g)
    assert db.min() < -6.0 and db[0] > -0.5          # the dip happens and starts from unity


def test_the_limiter_holds_the_true_peak_and_the_master_can_be_switched_off():
    voice, nar, amb, sfx, mus = _scene()
    sfx = sfx.copy()
    sfx[int(6 * SR):int(6.01 * SR)] = 1.0           # a full-scale click on top of the mix
    stems, rec = MC.mix_stems(nar, amb, sfx, mus, voice, bed_duck_db=6.0, music_duck_db=duck.DEPTH_DB)
    assert rec["measured"]["true_peak"] <= MC.TP_MAX - 0.2
    stems, rec = MC.mix_stems(nar, amb, sfx, mus, voice, bed_duck_db=6.0, music_duck_db=duck.DEPTH_DB, master=False)
    assert rec["master"]["gain_db"] == 0.0 and "master" in rec["master"].get("skipped", "master")


@needs_ffmpeg
def test_true_peak_stays_under_the_ceiling_after_an_aac_encode(tmp_path):
    voice, (stems, rec) = _chain()
    for name, s in stems.items():
        with wave.open(str(tmp_path / f"{name}.wav"), "wb") as w:
            w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
            w.writeframes(np.rint(np.clip(s, -1, 1) * 32767).astype("<i2").tobytes())
    rep = MC.verify(tmp_path)
    by = {r["gate"]: r["status"] for r in rep["rows"]}
    assert by["VAL-MIX-02"] == "PASS" and by["VAL-MIX-02:after_aac"] == "PASS"
    assert by["VAL-MIX-01"] == "PASS" and by["VAL-MIX-03"] == "PASS"


# ----- the rule rows, good and bad fixtures
def test_each_mix_rule_passes_on_a_good_fixture_and_fails_on_a_bad_one():
    ok = {"lufs": -14.1, "true_peak": -1.4, "voice_lufs": -20.0, "music_lufs": -32.0}
    bad = {"lufs": -20.0, "true_peak": -0.2, "voice_lufs": -20.0, "music_lufs": -24.0}
    g = {r["gate"]: r["status"] for r in VM.check_measurements(ok)}
    b = {r["gate"]: r["status"] for r in VM.check_measurements(bad)}
    for rule in ("VAL-MIX-01", "VAL-MIX-02", "VAL-MIX-03"):
        assert g[rule] == "PASS", rule
        assert b[rule] in ("FAIL", "REVIEW"), rule
    assert b["VAL-MIX-02"] == "FAIL"


def _plan():
    return {"shots": [{"shot_id": "A1", "segment_id": "S1", "start_s": 0.0, "dur_s": 5.0},
                      {"shot_id": "A2", "segment_id": "S1", "start_s": 5.0, "dur_s": 5.0},
                      {"shot_id": "B1", "segment_id": "S2", "start_s": 10.0, "dur_s": 5.0}]}


def _ev(shot, k):
    return {"shot_id": shot, "layer": "foley", "cue_id": f"EV_{shot}_{k}"}


def test_effects_per_scene_and_one_bed_per_scene_pass_and_fail():
    plan = _plan()
    placed = [_ev("A1", 1), _ev("A1", 2), _ev("A2", 3), _ev("B1", 1), _ev("B1", 2), _ev("B1", 3)]
    bed = lambda cid, a, b: {"layer": "ambience", "cue_id": cid, "start_s": a, "end_s": b}
    good_beds = [bed("BED1", 0.0, 10.0), bed("BED2", 10.0, 15.0)]
    rows = {r["gate"]: r["status"] for r in MC.scene_rows(plan, placed, good_beds)}
    assert rows["VAL-MIX-04:S1"] == "PASS" and rows["VAL-MIX-04:S2"] == "PASS"
    assert rows["VAL-MIX-05:S1"] == "PASS" and rows["VAL-MIX-05:S2"] == "PASS"
    # bad: a scene with two effects, a bed with a 1.5 s hole, a scene with two bed layers
    placed_bad = placed[:2] + placed[3:]
    gappy = [bed("BED1", 0.0, 4.0), bed("BED1b", 5.5, 10.0), bed("BED2", 10.0, 15.0)]
    rows = {r["gate"]: r["status"] for r in MC.scene_rows(plan, placed_bad, gappy)}
    assert rows["VAL-MIX-04:S1"] != "PASS" and rows["VAL-MIX-04:S2"] == "PASS"   # BP-209 is a REVIEW row
    assert rows["VAL-MIX-05:S1"] != "PASS"
    layered = [bed("BED1", 0.0, 10.0), bed("BED1x", 0.0, 10.0), bed("BED2", 10.0, 15.0)]
    rows = {r["gate"]: r["status"] for r in MC.scene_rows(plan, placed, layered)}
    assert rows["VAL-MIX-05:S1"] != "PASS" and rows["VAL-MIX-05:S2"] == "PASS"


def test_ev_ambience_rows_are_events_not_the_bed():
    plan = _plan()
    rows = [{"layer": "ambience", "cue_id": "EV_x", "start_s": 0.0, "end_s": 1.0}]
    scenes, bed_sets, _ = MC.scenes_of(plan, [], rows)
    assert all(not iv for _, iv, _, _ in bed_sets)


def test_the_delivery_bitrate_is_bp_63s_and_the_roundtrip_uses_it():
    from explainer_engine.production import assemble
    assert MC.AAC_KBPS == int(assemble._DELIVERY["aac_kbps"]) == 384


def test_a_very_quiet_input_is_not_lifted_by_tens_of_db_and_says_so():
    voice, nar, amb, sfx, mus = _scene()
    k = np.float32(10 ** (-40 / 20))
    stems, rec = MC.mix_stems(nar * k, amb * k, sfx * k, mus * k, voice, bed_duck_db=6.0, music_duck_db=duck.DEPTH_DB)
    assert rec["master"]["gain_db"] <= MC.MASTER_GAIN_MAX_DB + 1e-6 and rec["master"]["gain_capped"] is True
    assert rec["measured"]["lufs"] < MC.LUFS_TARGET - MC.TIGHT_BAND
    row = rec["rows"][0]
    assert row["gate"] == "master_gain_cap" and row["status"] == "REVIEW"
    # a normal input is not capped and has no such row
    _, ok = _chain()[1]
    assert ok["master"]["gain_capped"] is False and ok["rows"] == []
