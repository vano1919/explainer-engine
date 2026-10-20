"""The audio rules agree after the PR #9 / PR #10 merge (2026-10-20 rescan, reports A / B / C): every audio number a check
enforces is read from the sourced-rules registry, every severity is the registry's (so the creator's FAIL/REVIEW call is a
JSON switch), and the C findings are proven on small timed documents: the scorecard yields on BP-01 (C2) and on synced
effects (C5), AL-02 does not call a /3 script "silent" (C6), BP-57 does not flag cue runs the cue bus varies (C7)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from explainer_engine.audio import cues as CUES, duck, layers as L
from explainer_engine.finish import speed
from explainer_engine.production import assemble as ASM, beats as BEATS, shorts, timing as T
from explainer_engine.qa import scorecard
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def sev(rule_id: str) -> str:
    return SR.rule(rule_id).get("severity", "REVIEW")


def _timed(duration=120.0, schema=None, sfx=(), cues=(), music=(), shots=()):
    t = {"duration": duration, "shots": list(shots), "segments": [],
         "audio": {"sfx": list(sfx), "beds": [], "music": list(music), "cues": list(cues)}}
    if schema:
        t["script_schema"] = schema
    return t


def _cues(n, every=1.0, name="tick"):
    return [{"sound": name if k % 2 else "pop", "start": k * every, "end": k * every + 0.05} for k in range(n)]


# --- the new registry entries ------------------------------------------------------------------------------------------------

def test_new_audio_rules_are_registered_with_their_status():
    assert SR.rule("BP-49")["status"] == "hypothesis" and sev("BP-49") == "REVIEW"  # AL-02 band: REVIEWs today
    assert SR.rule("BP-64")["status"] == "house" and "D-58" in SR.rule("BP-64")["decided"]  # cue length: FAILs today
    assert SR.rule("BP-65")["status"] == "hypothesis"  # AL-04 gain caps: REVIEW today
    assert SR.rule("BP-66")["status"] == "house" and "2026-10-16" in SR.rule("BP-66")["decided"]
    assert SR.check() == []


def test_enforced_by_names_the_symbols_that_really_read_the_registry():
    assert "explainer_engine/production/timing.py:SFX_EARLY_MAX" in SR.rule("BP-54")["enforced_by"]
    assert "explainer_engine/production/timing.py:SFX_OFFSET" not in SR.rule("BP-54")["enforced_by"]
    assert "explainer_engine/audio/cues.py:VARIANTS" in SR.rule("BP-57")["enforced_by"]
    assert "explainer_engine/audio/layers.py:AL-04" not in SR.rule("BP-52")["enforced_by"]  # AL-04 is BP-65's proxy, not LU
    assert "explainer_engine/finish/speed.py:AUDIO_CODEC" in SR.rule("BP-63")["enforced_by"]


# --- R-03 / C6: AL-02 band from BP-49; /3 has no lower bound ----------------------------------------------------------------

def test_al02_band_is_read_from_bp49():
    assert L.SFX_PER_MIN == tuple(SR.T("BP-49", "events_per_min")) and L.DENSITY_MIN_S == SR.T("BP-49", "min_video_s")


def test_al02_never_calls_an_event_bound_scene_script_silent():
    few = _cues(4, every=30.0)  # 2 cues a minute, every one bound to its event
    assert any(f["rule"] == "AL-02" and "silent" in f["detail"] and f["severity"] == sev("BP-49")
               for f in L.check(_timed(cues=few, schema="production_script/2")))
    assert not [f for f in L.check(_timed(cues=few, schema=BEATS.SCENE_SCHEMA)) if f["rule"] == "AL-02"]
    clutter = _cues(int(SR.T("BP-49", "events_per_min")[1] * 2) + 4, every=0.5)  # over the band in 120 s
    assert any(f["rule"] == "AL-02" and "clutter" in f["detail"] for f in L.check(_timed(cues=clutter, schema=BEATS.SCENE_SCHEMA)))


def test_the_timed_doc_carries_its_script_schema():
    from test_visual_beats import beats_doc, words_for
    d = beats_doc()
    d["schema"] = BEATS.SCENE_SCHEMA
    assert L.silence_is_default(T.time_script(d, words_for(d, 0.12)))


# --- R-19: music fades from BP-62, and the fade check ------------------------------------------------------------------------

def test_music_fades_default_to_bp62_in_timing_mix_and_shorts():
    from test_visual_beats import beats_doc, words_for
    d = beats_doc()
    d["music"] = [{"track": "m1", "from": "<start>", "to": None}]
    m = T.time_script(d, words_for(d, 0.12))["audio"]["music"][0]
    assert (m["fade_in_s"], m["fade_out_s"]) == (SR.T("BP-62", "fade_in_s"), SR.T("BP-62", "fade_out_s"))
    assert ASM.music_fades(m) == (SR.T("BP-62", "fade_in_s"), SR.T("BP-62", "fade_out_s"))
    assert ASM.music_fades({"fade_s": 2.5}) == (2.5, 2.5)  # an older timed file keeps its one length
    seg = ASM.fade(np.ones(1000), 100, 300)
    assert abs(seg[50] - 50 / 99) < 1e-9
    assert seg[-150] < 0.6 and seg[-1] == 0.0 and seg[150] == 1.0  # asymmetric: a short fade in, a long fade out
    f = shorts.music_filter(30.0)
    assert f"afade=t=in:st=0:d={SR.T('BP-62', 'fade_in_s'):.2f}" in f
    assert f"afade=t=out:st={30.0 - SR.T('BP-62', 'fade_out_s'):.2f}:d={SR.T('BP-62', 'fade_out_s'):.2f}" in f


def test_a_music_fade_faster_than_bp62_is_reported():
    shots = [{"id": "T1", "start": 0.0, "end": 40.0, "accents": []}]
    ok = [{"track": "m", "start": 0.0, "end": 40.0, "fade_in_s": SR.T("BP-62", "fade_in_s"),
           "fade_out_s": SR.T("BP-62", "fade_out_s")}]
    assert L.music_findings(_timed(40.0, music=ok, shots=shots)) == []
    cut = [dict(ok[0], fade_in_s=0.2)]
    f = L.music_findings(_timed(40.0, music=cut, shots=shots))
    assert len(f) == 1 and "fades in" in f[0]["detail"] and f[0]["severity"] == sev("BP-62")
    sting = [{"track": "reveal_sting", "start": 0.0, "end": 3.0, "fade_in_s": 0.0, "fade_out_s": 0.0}]
    assert L.music_findings(_timed(40.0, music=sting, shots=shots + [{"id": "T2", "start": 3.0, "end": 40.0}])) == []


# --- R-20: every duck is BP-53's ---------------------------------------------------------------------------------------------

class _Snd:
    def __init__(self, n):
        self.n = n

    def load(self, name):
        return np.ones(self.n) * 0.5 if name == "m" else np.sin(np.arange(self.n) * 0.3)


def test_music_dips_under_the_voice_by_bp53_without_a_cut():
    sr = ASM.SR
    n = sr * 6
    voice = np.zeros(n)
    voice[2 * sr:4 * sr] = np.sin(np.arange(2 * sr) * 2 * np.pi * 220 / sr) * 0.8  # speech from 2 s to 4 s
    timed = {"duration": 6.0, "shots": [], "audio": {"beds": [], "sfx": [], "cues": [],
                                                      "music": [{"track": "m", "start": 0.0, "end": 6.0, "gain_db": -18}]}}
    stats: dict = {}
    music_only = ASM.build_audio(timed, np.zeros(n), _Snd(n), {})
    mixed = ASM.build_audio(timed, voice, _Snd(n), stats)
    music_part = mixed - ASM.level_voice(voice, sr) / (np.abs(ASM.level_voice(voice, sr)).max() + 1e-9) * 0.9 * ASM.db(-3)
    q = lambda a, s, e: np.sqrt(np.mean(a[int(s * sr):int(e * sr)] ** 2))  # noqa: E731
    dip_db = 20 * np.log10(q(music_only, 2.5, 3.5) / q(music_part, 2.5, 3.5))
    assert abs(dip_db - SR.T("BP-53", "house_depth_db")) < 1.0, dip_db
    assert stats["voice_duck_max_step_db_per_ms"] <= SR.T("BP-53", "max_step_db_per_ms")


def test_the_bed_dip_under_a_world_sound_sits_inside_bp53():
    src = (ROOT / "explainer_engine/production/assemble.py").read_text(encoding="utf-8")
    assert "0.55 * moving_mean" not in src and "depth_db=4.0" not in src and "attack_ms=20, release_ms=280" not in src
    lo, hi = SR.T("BP-53", "depth_db")
    assert lo <= float(SR.T("BP-53", "depth_db")[0]) <= hi
    fx = np.zeros(48000)
    fx[10000:20000] = 0.5
    g = duck.duck_gain(fx, 48000, depth_db=lo, threshold=0.01)
    assert abs(20 * np.log10(g.min()) + lo) < 0.5 and duck.step_finding(g, 48000) is None


# --- R-21 / R-23: AL-04 gain caps (BP-65) and the cue earcon (BP-64) ---------------------------------------------------------

def test_al04_is_a_registered_gain_proxy_not_an_lu_distance():
    assert L.MAX_SFX_DB == SR.T("BP-65", "sfx_gain_max_db") and L.MAX_BED_DB == SR.T("BP-65", "bed_gain_max_db")
    assert T.BED_DEFAULT_DB == L.MAX_BED_DB
    loud = _timed(sfx=[{"sound": "x", "start": 1.0, "end": 1.2, "gain_db": L.MAX_SFX_DB + 2}])
    f = [x for x in L.check(loud) if x["rule"] == "AL-04"]
    assert f and f[0]["severity"] == sev("BP-65") and "BP-52" in f[0]["detail"]


def test_cue_length_and_level_come_from_bp64_and_the_schema_agrees():
    assert (CUES.MIN_MS, CUES.MAX_MS) == tuple(SR.T("BP-64", "cue_ms"))
    assert (CUES.MIN_GAIN_DB, CUES.MAX_GAIN_DB) == tuple(SR.T("BP-64", "gain_db"))
    assert CUES.DEFAULT_GAIN_DB == SR.T("BP-64", "default_gain_db")
    schema = json.loads((ROOT / "explainer_engine/schemas/production_script.schema.json").read_text(encoding="utf-8"))
    text = json.dumps(schema)
    cue = re.search(r'"gain_db": \{"type": "number", "minimum": (-?[\d.]+), "maximum": (-?[\d.]+), "default": (-?[\d.]+)\}, '
                    r'"max_ms": \{"type": "number", "minimum": (\d+), "maximum": (\d+)\}', text)
    assert cue, "the cue block of the schema moved"
    assert [float(x) for x in cue.groups()] == [*SR.T("BP-64", "gain_db"), SR.T("BP-64", "default_gain_db"),
                                                *SR.T("BP-64", "cue_ms")]
    for name in CUES.BUILD:
        for v in range(len(CUES.VARIANTS)):
            assert CUES.MIN_MS <= len(CUES.render(name, v)) / CUES.SR * 1000 <= CUES.MAX_MS, (name, v)
    assert "BP-58" in SR.rule("BP-64")["statement"]  # the one-shot floor does not apply to an earcon, and says so


# --- B row 8 / C7: BP-57 pitch jitter and cue runs ---------------------------------------------------------------------------

def test_cue_variants_are_bp57s_pitch_jitter():
    j = SR.T("BP-57", "pitch_jitter")
    assert CUES.VARIANTS == (1.0, round(1 - j, 6), round(1 + j, 6))
    assert len(set(CUES.VARIANTS)) >= SR.T("BP-57", "variants_min")


def test_bp57_skips_cue_runs_the_bus_varies_but_keeps_effect_runs(monkeypatch):
    run = [{"sound": "tick", "start": t, "end": t + 0.03} for t in (1.0, 21.0)]
    assert L.repeat_findings(_timed(cues=run)) == []  # two 'tick' 20 s apart: two different pitches, not one sample
    fx = [{"sound": "pop_in__v1", "start": 1.0, "end": 1.2}, {"sound": "pop_in__v1", "start": 2.0, "end": 2.2}]
    f = L.repeat_findings(_timed(sfx=fx))
    assert len(f) == 1 and f[0]["severity"] == sev("BP-57")
    monkeypatch.setattr(L.CUES, "VARIANTS", (1.0,))
    assert [x["where"] for x in L.repeat_findings(_timed(cues=run))] == ["cues"]


# --- C2 / C5: the scorecard yields to the registry ---------------------------------------------------------------------------

def _words(n=40, step=0.4):
    return [{"w": f"w{i}" + ("." if i % 6 == 5 else ""), "s": i * step, "e": i * step + 0.3} for i in range(n)]


def _shot():
    return {"id": "s1", "type": "A", "start": 0.0, "end": 16.0, "transition": "cut", "emotion": "tension", "beat": "hook",
            "phase": "d", "sentences": [0], "motion": {"kind": "static", "z0": 1.0, "z1": 1.0}, "picture": "p", "palette": [],
            "face": "none", "stakes": "x y z w v u t"}


def test_scorecard_never_fails_a_hypothesis_pace():
    assert SR.rule("BP-01")["status"] == "hypothesis"
    assert scorecard.pace_verdict(SR.T("BP-01", "wpm_fail_below") - 20) == sev("BP-01") != "FAIL"
    assert scorecard.pace_verdict(SR.T("BP-01", "wpm_fail_above") + 20) == sev("BP-01")
    w = [{"w": f"w{i}", "s": i * 0.5, "e": i * 0.5 + 0.4} for i in range(60)]  # 120 wpm, the Syndicate Wars case
    row = scorecard.score([_shot()], w, "Is it? yes.", {"cast": [], "style_suffix": ""})[0]
    assert row["status"] != "FAIL" and "BP-01" in row["evidence"][0]


def test_scorecard_passes_an_effect_synced_to_its_word_and_fails_a_masking_one():
    w = _words()
    look = {"cast": [], "style_suffix": ""}
    synced = [{"id": "pop", "at": w[5]["s"], "dur": 0.4}, {"id": "hit", "at": w[9]["s"] + SR.T("BP-54", "late_max_ms") / 1000 - 0.01,
                                                           "dur": 1.0}]
    row = scorecard.score([_shot()], w, "Is it? yes.", look, sound_events=synced)[1]
    assert row["status"] == "PASS" and "2 synced" in row["evidence"][0]
    whoosh = [{"id": "whoosh", "at": w[12]["s"] + 0.2, "dur": 0.8}]  # starts inside a word: synced to nothing
    row = scorecard.score([_shot()], w, "Is it? yes.", look, sound_events=synced + whoosh)[1]
    assert row["status"] == sev("BP-66") and "whoosh" in row["evidence"][0]
    gap = [{"id": "whoosh", "at": w[5]["e"] + 0.02, "dur": 0.05}]  # in the pause between words: masks nothing
    assert scorecard.score([_shot()], w, "Is it? yes.", look, sound_events=gap)[1]["status"] == "PASS"


def test_a_d43_timed_script_with_one_effect_passes_row_2():
    """C5 on the D-43 flow: timing places every effect on its phrase's first word (BP-54), so the row no longer FAILs it."""
    from test_visual_beats import beats_doc, words_for
    d = beats_doc()
    seg = d["segments"][0]
    first = seg["lines"][0]["text"].split()[0].strip(".,?!")
    seg.setdefault("audio", {})["sfx"] = [{"at": first, "sound": "pop", "purpose": "a test hit"}]
    words = words_for(d, 0.12)
    timed = T.time_script(d, words)
    ev = [{"id": e["sound"], "at": e["start"], "dur": e["end"] - e["start"]} for e in timed["audio"]["sfx"]]
    assert ev and all(scorecard.synced(e, words["words"]) for e in ev)
    assert scorecard.masking(ev, words["words"]) == []


# --- BP-63: the sped file is the delivered file ------------------------------------------------------------------------------

def test_speed_retime_exports_the_delivery_codec(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cmd, check):
        seen["cmd"] = cmd
        Path(cmd[-1]).write_bytes(b"x")

    monkeypatch.setattr(speed.subprocess, "run", fake_run)
    speed.retime(tmp_path / "in.mp4", tmp_path / "out.mp4", speed.MAX_RATE)
    cmd = " ".join(seen["cmd"])
    assert " ".join(ASM.AUDIO_CODEC) in cmd and "192k" not in cmd
    assert f"{SR.T('BP-63', 'aac_kbps')}k" in cmd and str(SR.T("BP-63", "sample_rate")) in cmd


# --- the documents and skills state no superseded audio number ---------------------------------------------------------------

def test_docs_and_skills_link_the_audio_rules_instead_of_old_numbers():
    se = (ROOT / "docs/STORY_ENGINE.md").read_text(encoding="utf-8")
    al = "\n".join(ln for ln in se.splitlines() if ln.startswith("| AL-0"))
    assert "4 layers" not in al and "0.25 s" not in al and "-15 dB" not in al and "4-20" not in al
    assert "at most 4 (AL-01)" not in se and "0.94 / 1.06" not in se and "20-250 ms" not in se
    ed = (ROOT / "docs/EDITING.md").read_text(encoding="utf-8")
    assert "two background layers" not in ed and "1.05, 1.10 and 1.15" not in ed
    vea = (ROOT / ".claude/skills/video-editing-architect/SKILL.md").read_text(encoding="utf-8")
    assert "14+ dB" not in vea and "bed 4 dB" not in vea and "-55 to -60 dB under" not in vea
    assert "attack 20-80 ms" in (ROOT / ".claude/skills/editing-style/SKILL.md").read_text(encoding="utf-8")
    assert "voice-to-music gap >= 10 dB" not in (ROOT / "docs/IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
