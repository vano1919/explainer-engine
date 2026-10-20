"""The audio rules read from the sourced registry (BP-50..BP-63, BP-47; D-59) and the gates that never ran on the D-43 path
(contradictions A1, A2, A4, G1, G6, G9): every number comes from ``sourced_rules.json``, every verdict stands next to its
measurement, a FAIL stops a final render, a Short or a staging."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from explainer_engine import production_gate as G
from explainer_engine.audio import duck, layers as L, pause_pad as PP, seams, sfx_library as LIB
from explainer_engine.production import assemble as A
from explainer_engine.production import timing as T
from explainer_engine.publish import plan as PLAN
from explainer_engine.qa import publish_check as PC
from explainer_engine.qa import scorecard as SC
from explainer_engine.qa import targets
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "examples/syndicate_wars_ep1"
RULES = ROOT / "tests/fixtures/episode_rules/episode_rules.json"
HAVE_FFMPEG = shutil.which("ffmpeg") is not None


# --- qa/targets: the verdicts ---------------------------------------------------------------------------------------------

def test_profiles_come_from_the_registry_and_the_short_profile_has_no_lra_gate():
    long, short = targets.PROFILES["long"], targets.PROFILES["short"]
    assert long["lufs"] == SR.T("BP-50", "lufs") and tuple(long["pass_band"]) == tuple(SR.T("BP-50", "pass_band"))
    assert long["true_peak_max"] == SR.T("BP-50", "true_peak_max") and long["limiter_tp"] == SR.T("BP-50", "limiter_tp")
    assert long["stem_lra_max"] == SR.T("BP-59", "stem_lra_max") and "voice_gap_min_db" not in long  # RMS dB is not the unit
    assert short["lufs"] == SR.T("BP-61", "lufs") and short["max_short_term_above_lu"] == SR.T("BP-61", "max_short_term_above_lu")
    assert "LRA" in targets.loudnorm("long") and "LRA" not in targets.loudnorm("short")


def test_loudness_and_true_peak_verdicts_follow_the_bands():
    lo, hi = SR.T("BP-50", "pass_band")
    alo, _ = SR.T("BP-50", "allowed")
    assert targets.loudness_verdict((lo + hi) / 2) == "PASS"
    assert targets.loudness_verdict((alo + lo) / 2) == "REVIEW"
    assert targets.loudness_verdict(alo - 1) == "FAIL" and targets.loudness_verdict(hi + 1) == "FAIL"
    tp = SR.T("BP-50", "true_peak_max")
    assert targets.true_peak_verdict(tp - 0.5) == "PASS" and targets.true_peak_verdict(tp + 0.5) == "FAIL"


def test_ldr_is_the_dialogue_anchor_and_never_fails_because_bp51_is_review():
    rev, mx = SR.T("BP-51", "ldr_review_lu"), SR.T("BP-51", "ldr_max_lu")
    assert targets.ldr_verdict(-14, -14 - rev + 0.5) == "PASS"
    assert targets.ldr_verdict(-14, -14 - (rev + mx) / 2) == "REVIEW"
    assert targets.ldr_verdict(-14, -14 - mx - 2) == "REVIEW"  # over the max, but the registry says REVIEW: never a FAIL
    assert SR.rule("BP-51")["severity"] == "REVIEW"


def test_gap_verdict_is_in_lu_with_music_bed_and_combined_floors():
    m, b, c = SR.T("BP-52", "music_under_lu"), SR.T("BP-52", "bed_under_lu"), SR.T("BP-52", "combined_under_lu")
    assert targets.gap_verdict(-20, music_lu=-20 - m + 1) == "FAIL"  # music too close
    assert targets.gap_verdict(-20, bed_lu=-20 - b + 1) == "FAIL"  # bed too close
    assert targets.gap_verdict(-20, music_lu=-20 - m - 6, bed_lu=-20 - b - 6) == "PASS"
    # each stem clears its own floor but their sum does not clear the combined floor
    assert targets.gaps(-20, -20 - c + 0.5, -20 - c + 0.5)["combined"] < c
    assert targets.gap_verdict(-20, -20 - c + 0.5, -20 - c + 0.5) == "FAIL"


def test_short_term_and_stem_lra_verdicts():
    cap = SR.T("BP-61", "max_short_term_above_lu")
    assert targets.short_term_verdict(-14 + cap - 0.1, -14) == "PASS" and targets.short_term_verdict(-14 + cap + 0.1, -14) == "FAIL"
    lra = SR.T("BP-59", "stem_lra_max")
    assert targets.stem_lra_verdict(lra) == "PASS" and targets.stem_lra_verdict(lra + 1) == "FAIL"


EBUR = """[Parsed_ebur128_0 @ 0x1] t: 0.4 TARGET:-23 LUFS M: -inf S: -inf I: -70.0 LUFS LRA: 0.0 LU FTPK: -inf dBFS TPK: -inf dBFS
[Parsed_ebur128_0 @ 0x1] t: 3.1 TARGET:-23 LUFS M: -12.3 S: -11.9 I: -13.8 LUFS LRA: 2.0 LU FTPK: -2.1 dBFS TPK: -1.2 dBFS
[Parsed_ebur128_0 @ 0x1] t: 6.2 TARGET:-23 LUFS M: -15.0 S: -14.2 I: -14.1 LUFS LRA: 3.0 LU FTPK: -4.0 dBFS TPK: -1.2 dBFS
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -14.1 LUFS
    Threshold: -24.5 LUFS

  Loudness range:
    LRA:         3.0 LU
    Threshold: -34.6 LUFS
    LRA low:   -16.0 LUFS
    LRA high:  -13.0 LUFS

  True peak:
    Peak:       -1.2 dBFS
"""


def test_ebur128_is_parsed_and_verdicts_are_written_next_to_the_numbers():
    m = targets.parse_ebur128(EBUR)
    assert m == {"lufs": -14.1, "lra": 3.0, "true_peak": -1.2, "max_short_term": -11.9}
    v = targets.verdicts(m, "short")
    assert v["loudness_verdict"] == "PASS" and v["true_peak_verdict"] == "PASS" and v["short_term_verdict"] == "PASS"
    v = targets.verdicts(m, "long", voice_lufs=-20.0)
    assert v["ldr_lu"] == pytest.approx(5.9) and v["ldr_verdict"] == "REVIEW"
    assert targets.failures({"loudness_verdict": "FAIL", "lufs": -11.0, "true_peak_verdict": "PASS"}) == ["loudness -11.0 LUFS"]


@pytest.mark.skipif(not HAVE_FFMPEG, reason="needs ffmpeg")
def test_measure_file_reads_a_real_file(tmp_path):
    wav = tmp_path / "t.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=4", "-af", "volume=0.3", str(wav)], check=True)
    m = targets.measure_file(wav)
    assert -40 < m["lufs"] < 0 and m["true_peak"] < 0 and "max_short_term" in m


# --- audio/duck, timing: the house numbers inside the sourced ranges --------------------------------------------------------

def test_duck_constants_sit_inside_bp53_and_the_step_check_reads_the_jnd():
    t = SR.rule("BP-53")["thresholds"]
    assert duck.DEPTH_DB == t["house_depth_db"] and t["depth_db"][0] <= duck.DEPTH_DB <= t["depth_db"][1]
    assert t["attack_ms"][0] <= duck.ATTACK_MS <= t["attack_ms"][1] and t["release_ms"][0] <= duck.RELEASE_MS <= t["release_ms"][1]
    assert duck.HOLD_MS >= t["hold_ms_min"] and duck.MAX_STEP_DB_PER_MS == t["max_step_db_per_ms"]
    sr = 8000
    side = np.zeros(sr)
    side[sr // 2:] = 0.5
    g = duck.duck_gain(side, sr)
    assert duck.step_finding(g, sr) is None
    hard = np.where(np.arange(sr) < sr // 2, 1.0, 10 ** (-20 / 20))  # a 20 dB cliff in one sample: a cut
    assert duck.step_finding(hard, sr)["rule"] == "BP-53"


def test_sfx_offset_never_leads_the_picture_and_a_scripted_lead_is_held_in_the_window():
    assert T.SFX_OFFSET == 0.0 and T.SFX_LATE_MAX == SR.T("BP-54", "late_max_ms") / 1000
    assert -T.SFX_EARLY_MAX == -SR.T("BP-54", "early_max_ms") / 1000


# --- audio/layers: BP-54, BP-55, BP-56, BP-57, BP-62 ---------------------------------------------------------------------

def _shot(i, a, b, accents=()):
    return {"id": f"S{i}", "start": a, "end": b, "accents": list(accents), "bubbles": []}


def _timed(sfx=(), cues=(), music=(), shots=None, beats=(), duration=200.0):
    return {"duration": duration, "shots": shots or [_shot(1, 0.0, duration)], "visual_beats": list(beats),
            "segments": [{"id": "S01", "start": 0.0, "end": duration}],
            "audio": {"sfx": list(sfx), "cues": list(cues), "music": list(music), "beds": []}}


def test_sync_window_is_asymmetric_early_fails_late_is_forgiven_until_its_own_limit():
    early, late = SR.T("BP-54", "early_max_ms") / 1000, SR.T("BP-54", "late_max_ms") / 1000
    assert L.SYNC_EARLY == early and L.SYNC_LATE == late and late > early

    def found(offset):
        t = _timed(sfx=[{"sound": "hit", "start": 10.0 + offset, "end": 10.5, "gain_db": -18}],
                   shots=[_shot(1, 0.0, 200.0, [{"kind": "punch", "start": 10.0}])])
        return [f for f in L.check(t) if f["rule"] == "AL-03"]

    assert found(-early + 0.005) == [] and found(late - 0.005) == []  # inside the window both ways
    assert found(-(early + 0.02))[0]["severity"] == "FAIL" and "early" in found(-(early + 0.02))[0]["detail"]
    assert found(late + 0.03)[0]["severity"] == "FAIL" and "late" in found(late + 0.03)[0]["detail"]
    assert found(0.9)[0]["severity"] == "REVIEW"  # nothing near the move at all: the old AL-03 "no effect"


def test_beat_share_cap_bp55():
    beats = [{"start": 5.0 * k, "kind": "symbol"} for k in range(10)]
    many = [{"sound": f"s{k}", "start": 5.0 * k, "end": 5.0 * k + 0.3, "gain_db": -18} for k in range(8)]
    few = many[:3]
    assert [f["rule"] for f in L.beat_share_findings(_timed(sfx=many, beats=beats))] == ["BP-55"]
    assert L.beat_share_findings(_timed(sfx=few, beats=beats)) == []
    assert L.beat_share_findings(_timed(sfx=many)) == []  # no beats: nothing to share


def test_same_sample_twice_in_a_row_bp57():
    sfx = [{"sound": "pop_in__v1", "start": 1.0, "end": 1.2}, {"sound": "pop_in__v1", "start": 2.0, "end": 2.2},
           {"sound": "whoosh", "start": 3.0, "end": 3.4}, {"sound": "pop_in__v1", "start": 4.0, "end": 4.2}]
    f = L.repeat_findings(_timed(sfx=sfx))
    assert len(f) == 1 and f[0]["rule"] == "BP-57" and "pop_in__v1" in f[0]["where"] and f[0]["severity"] == "REVIEW"
    cues = [{"sound": "blip", "start": 1.0, "end": 1.1}, {"sound": "blip", "start": 2.0, "end": 2.1}, {"sound": "pluck", "start": 3.0, "end": 3.1}]
    assert [x["where"] for x in L.repeat_findings(_timed(cues=cues))] == ["cues"]
    assert L.repeat_findings(_timed(sfx=sfx[2:3], cues=cues[1:])) == []


def test_music_is_spotted_on_boundaries_with_a_no_music_stretch_and_short_stings_bp62():
    shots = [_shot(1, 0.0, 30.0), _shot(2, 30.0, 150.0), _shot(3, 150.0, 200.0)]
    on_cuts = [{"track": "m1", "start": 0.0, "end": 30.0}, {"track": "m2", "start": 150.0, "end": 200.0}]
    assert L.music_findings(_timed(music=on_cuts, shots=shots)) == []
    off = [{"track": "m1", "start": 12.3, "end": 30.0}]
    f = L.music_findings(_timed(music=off, shots=shots))
    assert len(f) == 1 and "start at 12.30s" in f[0]["detail"] and f[0]["severity"] == "REVIEW"
    wall = [{"track": "m1", "start": 0.0, "end": 150.0}, {"track": "m2", "start": 150.0, "end": 200.0}]  # wallpaper
    assert any("without music" in x["detail"] for x in L.music_findings(_timed(music=wall, shots=shots)))
    sting = [{"track": "reveal_sting", "start": 30.0, "end": 30.0 + SR.T("BP-62", "sting_max_s") + 3}]
    assert any("sting" in x["detail"] for x in L.music_findings(_timed(music=sting, shots=shots)))
    assert L.music_findings(_timed(music=[{"track": "m", "start": 0.0, "end": 40.0}], duration=40.0,
                                   shots=[_shot(1, 0.0, 40.0)])) == []  # a Short needs no no-music stretch


def test_al01_counts_layers_from_bp56():
    assert L.MAX_SFX_AT_ONCE == SR.T("BP-56", "same_class_max") and L.MAX_LAYERS == SR.T("BP-56", "layers_max")
    assert L.MAX_BED_DB == -SR.T("BP-52", "bed_under_lu")


# --- audio/seams BP-59, pause_pad BP-60, sfx_library BP-58 -----------------------------------------------------------------

def test_seam_findings_gate_the_spread_and_the_join_steps():
    assert seams.MAX_SPREAD_DB == SR.T("BP-59", "chunk_spread_db_max") and seams.JOIN_STEP_LU_MAX == SR.T("BP-59", "join_step_lu_max")
    ok = {"target_lufs": -20.0, "before": [-20.5, -19.6, -20.0], "gains_db": [0.5, -0.4, 0.0], "spread_before_db": 0.9, "spread_after_db": 0.0}
    assert seams.findings(ok) == []
    wide = {"target_lufs": -20.0, "before": [-33.0, -20.0, -6.5], "gains_db": [6.0, 0.0, -6.0],
            "spread_before_db": 26.5, "spread_after_db": 14.5}  # Syndicate Wars: 26.5 dB spread, clamped at 6 dB
    f = seams.findings(wide)
    rules = {x["rule"] for x in f}
    assert rules == {"BP-59"} and all(x["severity"] == SR.rule("BP-59")["severity"] for x in f)
    assert any("spread" in x["detail"] for x in f) and any("join steps" in x["detail"] for x in f) and any("re-read" in x["detail"] for x in f)


def test_seams_cli_exits_one_on_a_fail(monkeypatch, tmp_path, capsys):
    levels = iter([-33.0, -20.0])
    monkeypatch.setattr(seams, "lufs", lambda p: next(levels))
    assert seams.main([str(tmp_path / "a.wav"), str(tmp_path / "b.wav")]) == 1
    assert "BP-59" in capsys.readouterr().out


def test_pauses_are_filled_with_room_tone_at_the_reads_floor_not_zeros():
    sr = 1000
    words = [{"w": "Hello,", "s": 0.0, "e": 0.4, "para": 0}, {"w": "there", "s": 0.45, "e": 0.8, "para": 0}]
    rng = np.random.default_rng(1)
    floor = 10 ** (-70 / 20)
    audio = (rng.standard_normal(int(1.0 * sr)) * floor).astype(np.float32)  # a -70 dBFS room
    for w in words:
        audio[int(w["s"] * sr):int(w["e"] * sr)] = 0.5
    out, new, rep = PP.pad_pauses(words, audio, sr, min_gap=0.26)
    assert rep["inserted"] == 1 and len(out) == len(audio) + int(round(0.21 * sr))
    assert rep["fill_dbfs"] is not None and rep["fill_dbfs"] <= SR.T("BP-60", "pause_fill_dbfs_max")
    gap = out[int(round(new[0]["e"] * sr)) + 15:int(round(new[1]["s"] * sr)) - 15]
    level = 20 * np.log10(np.sqrt(np.mean(gap.astype(np.float64) ** 2)) + 1e-12)
    assert np.any(gap != 0) and -80 < level <= SR.T("BP-60", "pause_fill_dbfs_max") + 1
    assert PP.noise_floor_db(np.zeros(sr, np.float32), sr) == PP.FILL_MIN_DB  # digital silence: a trace, never louder
    loud = (rng.standard_normal(sr) * 0.1).astype(np.float32)  # a noisy read: the fill is capped, not the floor
    assert min(PP.noise_floor_db(loud, sr), PP.FILL_MAX_DB) == PP.FILL_MAX_DB


def test_sfx_library_kinds_and_seam_checks_bp58():
    assert LIB.kind_of({"kind": "loop"}) == "loop" and LIB.kind_of({"loop": False, "category": "music"}) == "one_shot"
    assert LIB.kind_of({"loop": True}) == "loop" and LIB.kind_of({"category": "foley"}) == "one_shot"
    sr = 8000
    t = SR.rule("BP-58")["thresholds"]
    rng = np.random.default_rng(0)
    short_loop = (rng.standard_normal(sr * 5) * 0.1).astype(np.float32)
    f = LIB.check_seams({"id": "bed__v1", "kind": "loop"}, short_loop, sr)
    assert any("loop of" in x["detail"] for x in f) and all(x["rule"] == "BP-58" and x["severity"] == "REVIEW" for x in f)
    n = int(sr * (t["loop_min_s"] + 1))
    good = (np.sin(np.arange(n) * 2 * np.pi * 110 / sr) * 0.1).astype(np.float32)  # a steady bed: identical at both ends
    assert LIB.check_seams({"id": "bed__v2", "kind": "loop"}, good, sr) == []
    stepped = good.copy()
    stepped[-sr:] *= 0.1  # the tail is 20 dB down: the wrap steps
    assert any("seam steps" in x["detail"] for x in LIB.check_seams({"id": "bed__v3", "kind": "loop"}, stepped, sr))
    clicked = good.copy()
    clicked[sr // 2:sr // 2 + 40] = 0.9  # a transient half a second after the seam
    assert any("transient" in x["detail"] for x in LIB.check_seams({"id": "bed__v4", "kind": "loop"}, clicked, sr))
    long_hit = (rng.standard_normal(sr * 8) * 0.1).astype(np.float32)
    assert any("one-shot of" in x["detail"] for x in LIB.check_seams({"id": "hit__v1", "kind": "one_shot"}, long_hit, sr))
    assert LIB.check_seams({"id": "hit__v2"}, long_hit[: sr // 2], sr) == []


# --- the export: BP-63 and the measured verdicts (BP-50 / BP-51 / BP-61) ----------------------------------------------------

def test_delivery_codec_comes_from_bp63_and_is_what_the_mux_and_the_shorts_use(tmp_path, monkeypatch):
    t = SR.rule("BP-63")["thresholds"]
    assert A.AUDIO_CODEC == ["-c:a", "aac", "-b:a", f"{t['aac_kbps']}k", "-ar", str(t["sample_rate"]), "-ac", str(t["channels"])]
    out = tmp_path / "out"
    (out / "chunks").mkdir(parents=True)
    (out / "chunks" / "c_0000.mp4").write_bytes(b"x")
    (out / "audio.wav").write_bytes(b"x")
    seen = []

    def fake_run(cmd, **kw):
        seen.append(cmd)
        Path(cmd[-1]).write_bytes(b"mp4")

    monkeypatch.setattr(A.subprocess, "run", fake_run)
    A.mux(out, [(0, 1)])
    cmd = seen[0]
    assert (out / "video.mp4").exists() and cmd[cmd.index("-ac") + 1] == "2" and cmd[cmd.index("-b:a") + 1] == "384k"
    for path in ("explainer_engine/production/assemble.py", "explainer_engine/production/shorts.py"):
        assert '"192k"' not in (ROOT / path).read_text(encoding="utf-8"), path  # mono 192k is not a delivery (BP-63)
    shorts_src = (ROOT / "explainer_engine/production/shorts.py").read_text(encoding="utf-8")
    assert "*ASM.AUDIO_CODEC, str(final)" in shorts_src and "measure_final(final)" in shorts_src


def test_measure_delivery_records_verdicts_and_the_dialogue_anchor(monkeypatch, tmp_path):
    levels = {"mix.wav": {"lufs": -14.2, "true_peak": -1.4, "lra": 6.0, "max_short_term": -10.0},
              "voice.wav": {"lufs": -19.0, "true_peak": -3.0}}
    monkeypatch.setattr(targets, "measure_file", lambda p: levels[Path(p).name])
    rep = A.measure_delivery(tmp_path / "mix.wav", tmp_path / "voice.wav")
    assert rep["loudness_verdict"] == "PASS" and rep["true_peak_verdict"] == "PASS"
    assert rep["voice_lufs"] == -19.0 and rep["ldr_lu"] == pytest.approx(4.8) and rep["ldr_verdict"] == "REVIEW"
    assert targets.failures(rep) == []


def test_a_final_render_stops_on_a_loudness_fail_after_writing_the_report(monkeypatch, tmp_path):
    monkeypatch.setattr(A, "read_wav", lambda p: (np.zeros(48000), 48000))
    monkeypatch.setattr(A, "Sounds", lambda dirs: None)
    monkeypatch.setattr(A, "build_audio", lambda timed, nar, sounds, stats: np.zeros(len(nar)))
    monkeypatch.setattr(A.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(A, "measure_delivery", lambda *a, **k: {"lufs": -11.0, "loudness_verdict": "FAIL", "true_peak": -2.0,
                                                                "true_peak_verdict": "PASS"})
    timed = {"fps": 30, "frames": 30, "findings": [], "audio": {"beds": [], "sfx": [], "music": [], "cues": []}, "shots": [], "pictures": {}}
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as exc:
        A.assemble(timed, tmp_path / "n.wav", out, [], [], final=True, audio_only=True)
    assert "-11.0 LUFS" in str(exc.value) and "BP-50" in str(exc.value)
    assert json.loads((out / "assemble_report.json").read_text())["audio"]["loudness_verdict"] == "FAIL"
    rep = A.assemble(timed, tmp_path / "n.wav", out, [], [], final=False, audio_only=True)  # a draft reports, never stops
    assert rep["audio"]["loudness_verdict"] == "FAIL"


# --- the gates that never ran: scorecard CLI, PC-08 / PC-09, production_gate 8 and 9 ----------------------------------------

@pytest.mark.skipif(not (SW / "words.json").exists() or not (SW / "timed.json").exists(), reason="example files missing")
def test_scorecard_cli_runs_on_the_syndicate_wars_folder(tmp_path):
    folder = tmp_path / "sw"
    shutil.copytree(SW, folder, ignore=shutil.ignore_patterns("publish", "beats", "*.py", "*.md"))
    (folder / "render").mkdir()
    (folder / "render" / "assemble_report.json").write_text(json.dumps({"audio": {"lufs": -14.3, "true_peak": -1.6, "voice_lufs": -17.0,
                                                                                   "loudness_verdict": "PASS", "true_peak_verdict": "PASS",
                                                                                   "ldr_lu": 2.7, "ldr_verdict": "PASS"}}))
    rc = SC.main([str(folder)])
    card = json.loads((folder / "scorecard.json").read_text(encoding="utf-8"))
    assert card["schema"] == "scorecard/1" and [r["id"] for r in card["rows"]] == [1, 2, 3, 4, 5, 6, 7]
    assert rc == (1 if any(r["status"] == "FAIL" for r in card["rows"]) else 0)
    row2 = card["rows"][1]
    assert any("BP-51" in e for e in row2["evidence"]) and any("BP-50" in e for e in row2["evidence"])
    assert any("check_timed" in e for e in card["rows"][5]["evidence"])  # the D-43 editing rules, not the legacy shot rules
    assert (folder / "scorecard.md").read_text(encoding="utf-8").startswith("# Seven-point test:")


def test_check2_rows_carry_ldr_and_short_term_when_the_stats_do():
    ev, st = SC.audio_rows({"lufs": -14.0, "voice_lufs": -20.5, "max_short_term": -7.0}, [], "PASS")
    assert any("BP-51" in e for e in ev) and any("BP-61" in e for e in ev) and st == "FAIL"  # 6.5 LU anchor -> REVIEW; 7 LU short-term -> FAIL
    ev, st = SC.audio_rows({"lufs": -14.0, "voice_lufs": -17.0, "max_short_term": -11.0}, [], "PASS")
    assert st == "PASS"


PUB = {
    "schema": "publish/1", "title": "T", "description": "Sources: https://example.org", "duration_s": 600,
    "chapters": [{"t": "0:00", "title": "a"}, {"t": "2:20", "title": "b"}, {"t": "5:00", "title": "c"}],
    "audience": "not_made_for_kids",
    "disclosure": {"decision": "not_needed", "reason": "drawn", "photoreal_pictures": False, "real_person_realistic": False,
                   "real_event_altered": False, "ai_music_main": False},
    "mid_roll": "off", "self_certification_answered": True, "approval": {"by": "creator", "ref": "cmsg_x"},
}


def _episode(tmp_path: Path, *, stamped=True, card="PASS") -> Path:
    from explainer_engine.standards import rulebook as R
    ep = tmp_path / "ep"
    ep.mkdir(parents=True)
    (ep / "publish.json").write_text(json.dumps(PUB))
    (ep / "production_script.json").write_text("{}")
    (ep / "episode_rules.json").write_text(RULES.read_text(encoding="utf-8"))
    if stamped:
        R.stamp(ep / "episode_rules.json", "final_qa", by="t", scope="all", script=ep / "production_script.json")
    if card:
        (ep / "scorecard.json").write_text(json.dumps({"schema": "scorecard/1", "rows": [{"id": 2, "name": "sound", "status": card}]}))
    return ep


def test_pc08_fails_without_approval_and_pc09_needs_the_stamp_and_the_scorecard(tmp_path):
    ep = _episode(tmp_path)
    assert [f for f in PC.check(PUB, None, ep) if f["severity"] == "FAIL"] == []
    assert any(f["rule"] == "PC-08" and f["severity"] == "FAIL" for f in PC.check({**PUB, "approval": None}))
    assert any(f["rule"] == "PC-09" and "final_qa" in f["where"] for f in PC.check(PUB, None, _episode(tmp_path / "b", stamped=False)))
    assert any(f["rule"] == "PC-09" and "scorecard" in f["where"] for f in PC.check(PUB, None, _episode(tmp_path / "c", card=None)))
    assert any(f["rule"] == "PC-09" and "FAIL on" in f["detail"] for f in PC.check(PUB, None, _episode(tmp_path / "d", card="FAIL")))
    (tmp_path / "e").mkdir()
    assert any("no episode rulebook" in f["detail"] for f in PC.gate_findings(tmp_path / "e"))
    assert PC.main([str(ep / "publish.json")]) == 0 and PC.main([str(ep / "publish.json"), "--episode", str(tmp_path / "e")]) == 1


def test_production_gate_8_and_9_read_the_verdicts_and_the_approval(tmp_path):
    ep = _episode(tmp_path)
    assert G.approval_state(ep)[0] == "PASS"
    (ep / "publish.json").write_text(json.dumps({**PUB, "approval": None}))
    assert G.approval_state(ep)[0] == "WAIT"
    assert G.qa_state(ep)[0] == "WAIT"  # a scorecard but no assemble report yet
    (ep / "assemble_report.json").write_text(json.dumps({"audio": {"lufs": -14.0, "loudness_verdict": "PASS", "true_peak": -1.5,
                                                                   "true_peak_verdict": "PASS"}}))
    assert G.qa_state(ep)[0] == "PASS"
    (ep / "assemble_report.json").write_text(json.dumps({"audio": {"lufs": -11.0, "loudness_verdict": "FAIL"}}))
    st, _, nxt = G.qa_state(ep)
    assert st == "BLOCKED" and "loudness" in nxt


# --- governance: PV-40 / PP-05 (D-50), BP-47 ------------------------------------------------------------------------------

def test_pv40_allows_a_pod_engine_named_by_a_paint_plan():
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from test_production_script import compiled
    from explainer_engine.production import script as S
    from explainer_engine.production import validate as V
    doc = compiled()
    doc["episode"]["rulebook"] = "episode_rules.json"
    doc["look"]["default_engine"] = "pod_text"
    pics, _ = S.pictures(doc)
    painted = [p for p in pics.values() if p.get("uses") and not p.get("file")]
    if not painted:
        pytest.skip("the mini script has no unpainted pictures")
    found = [f for f in V.rulebook_era_findings(doc) if f["rule"] == "PV-40" and "pod" in f["detail"]]
    assert found and all(f["severity"] == "REVIEW" for f in found)  # D-50: a choice to make, never a refusal
    doc["_plans"] = [{"provider": "pod", "items": [{"id": p["id"]} for p in painted]}]
    assert not [f for f in V.rulebook_era_findings(doc) if f["rule"] == "PV-40" and "pod" in f["detail"]]


def test_posting_spread_bp47():
    t = SR.rule("BP-47")["thresholds"]
    none = PLAN.posting_findings({"shorts": [{"id": "SH01"}]})
    assert len(none) == 1 and "BP-47" in none[0]["detail"]
    pub = {"publish_date": "2026-11-01", "shorts": [{"id": f"SH{k:02d}", "publish_date": "2026-11-0" + str(1 + k // 2)} for k in range(1, 5)]}
    f = PLAN.posting_findings(pub)
    assert any("a day" in x["detail"] for x in f) and any("spans" in x["detail"] for x in f)
    late = {"publish_date": "2026-11-01", "shorts": [{"id": "SH01", "publish_date": "2026-11-20"}]}
    assert any("first Short" in x["detail"] for x in PLAN.posting_findings(late))
    good = {"publish_date": "2026-11-01", "shorts": [{"id": f"SH{k:02d}", "publish_date": f"2026-11-{2 + 2 * k:02d}"} for k in range(8)]}
    assert PLAN.posting_findings(good) == [] and (2 + 2 * 7) - 2 >= t["spread_days_min"]
