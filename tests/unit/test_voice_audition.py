"""The voice director (P4b): the eight-measure battery on synthetic voices (deterministic, no network, no media), the VC-04
margins of BP-138, the audition record, the channel registry with its veto line (VC-08) and EL-13 drift."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.audio import casting, voice_audition as VA, voice_check as VC
from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError

SR = 24000
ROOT = Path(__file__).resolve().parents[2]


def synth(f0=100.0, seconds=11.0, seed=0, syll=4.0, pauses=(4.0, 8.0), bright=0.5, vibrato=0.0) -> np.ndarray:
    """A voiced signal: harmonics of a pitch with a gentle contour, a syllable-rate envelope, silent pauses, a little noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    contour = f0 * (1 + 0.04 * np.sin(2 * np.pi * 0.3 * t + seed) + vibrato * np.sin(2 * np.pi * 5 * t))
    phase = 2 * np.pi * np.cumsum(contour) / SR
    x = sum((bright ** (k - 1)) * np.sin(k * phase) / k for k in range(1, 30) if k * f0 < SR / 2)
    env = 0.55 + 0.45 * np.sin(np.pi * syll * t) ** 2
    for p in pauses:
        env[(t >= p) & (t < p + 0.6)] = 0.0
    x = x * env + rng.normal(0, 0.002, len(t))
    return (0.3 * x / np.max(np.abs(x))).astype(np.float32)


def tilt(x: np.ndarray, slope: float) -> np.ndarray:
    """The same voice made brighter (slope > 0) or darker (< 0): the spectrum scaled by (1 + f/800)^slope."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    y = np.fft.irfft(spec * (1 + f / 800.0) ** slope, len(x))
    return (0.3 * y / np.max(np.abs(y))).astype(np.float32)


def test_the_battery_is_deterministic_and_reads_pitch_pauses_and_pace():
    x = synth(100.0)
    a, b = VA.measure(x, SR), VA.measure(x, SR)
    assert a == b
    assert a["reliable"] and abs(a["f0_median_hz"] - 100) < 4
    assert a["pauses"]["count"] == 2 and 0.5 < a["pauses"]["median_s"] < 0.7
    assert 3 <= a["syllable_rate"] <= 5.5
    for key in ("f0_range_st", "pitch_variation_st", "emphasis_db", "centroid_hz", "tilt_db", "sibilance_db"):
        assert key in a
    words = " ".join(["word"] * 40)
    w = VA.measure(x, SR, words)
    assert w["wpm_speaking"] == pytest.approx(40 / w["speech_s"] * 60, abs=0.1) and w["wpm_overall"] < w["wpm_speaking"]
    assert "wpm_speaking" not in a


def test_the_fast_pitch_track_agrees_with_the_loop_version_within_a_semitone():
    from explainer_engine.audio import voice_layer
    x = synth(130.0, seconds=4.0, pauses=())
    fast, slow = VA.f0_track(x, SR), voice_layer.f0_track(x, SR)
    assert len(fast) > 100
    assert abs(12 * np.log2(np.median(fast) / np.median(slow))) < 1.0


@pytest.mark.parametrize("f0", [90.0, 130.0, 180.0, 240.0])
def test_the_pitch_is_read_across_the_range_of_voices(f0):
    p = VA.measure(synth(f0, pauses=()), SR)
    assert abs(12 * np.log2(p["f0_median_hz"] / f0)) < 0.5
    assert 0 < p["pitch_variation_st"] < 2.0 and p["f0_range_st"] >= p["pitch_variation_st"]


def test_the_other_measures_move_with_the_signal():
    base = synth()
    dull, bright = VA.measure(tilt(base, -1.0), SR), VA.measure(tilt(base, 1.0), SR)
    assert bright["tilt_db"] > dull["tilt_db"] + 6 and bright["sibilance_db"] > dull["sibilance_db"] + 6
    flat = VA.measure(base, SR)["emphasis_db"]
    stressed = base.copy()
    for a in (1.0, 3.0, 6.0):
        stressed[int(a * SR):int((a + 0.8) * SR)] *= 2.5  # loud phrases on a quieter read
    assert VA.measure(np.clip(stressed, -1, 1), SR)["emphasis_db"] > flat + 1.0
    many = VA.measure(synth(pauses=(2.0, 4.0, 6.0, 8.0)), SR)["pauses"]
    assert many["count"] == 4 and many["per_min"] > VA.measure(base, SR)["pauses"]["per_min"] and many["ratio"] > 0.15
    assert VA.measure(synth(syll=6.0, pauses=()), SR)["syllable_rate"] > VA.measure(synth(syll=3.0, pauses=()), SR)["syllable_rate"] * 1.5


def test_the_committed_preview_measurements_hold():
    """docs/research/VOICE_PREVIEWS_2026-10-30.json: the five free previews behind the PR's numbers (no media committed)."""
    doc = json.loads((ROOT / "docs" / "research" / "VOICE_PREVIEWS_2026-10-30.json").read_text(encoding="utf-8"))
    recs = doc["records"]
    assert len(recs) == 5
    for r in recs:
        assert contracts.validate(r) == [] and r["source"]["kind"] == "library_preview" and len(r["source"]["sha256"]) == 64
    short = [r["name"] for r in recs if not r["profile"]["reliable"]]
    assert short == ["David Planet Earth"]
    pairs = sorted(f["where"] for f in VA.distinct({r["name"]: r["profile"] for r in recs}))
    assert pairs == sorted(["Grandpa Spuds Oxley / Michael Moody - Grandfatherly and warm",
                            "Adam - Classic English Narrator / David Planet Earth",
                            "Adam - Classic English Narrator / Wyatt- Wise Rustic Cowboy"])


def test_a_brighter_voice_has_a_higher_centroid_and_a_higher_voice_a_higher_pitch():
    base = synth()
    dull, bright = VA.measure(tilt(base, -1.0), SR), VA.measure(tilt(base, 1.0), SR)
    assert bright["centroid_hz"] > dull["centroid_hz"] * 1.5
    assert VA.measure(synth(160.0), SR)["f0_median_hz"] > 150


def test_a_short_read_is_marked_unreliable_not_refused():
    p = VA.measure(synth(seconds=3.0, pauses=()), SR)
    assert p["reliable"] is False and "alone" in p["note"]
    with pytest.raises(ValueError):
        VA.baseline_of(p, "preview", "x")
    assert VA.measure(np.zeros(100, np.float32), SR)["reliable"] is False
    assert VA.measure(np.zeros(SR, np.float32), SR)["reliable"] is False


def test_takes_of_one_voice_agree_more_than_takes_of_two_voices():
    same = VA.consistency([synth(100, seed=s) for s in (1, 2, 3)], SR)
    cross = VA.consistency([synth(100, seed=1), synth(100, seed=2, bright=0.9), synth(170, seed=3, bright=0.9)], SR)
    assert same["embedder"] == "numpy_mfcc13" and same["takes"] == 3
    assert same["min_cosine"] > cross["min_cosine"]
    assert VA.consistency([synth()], SR)["min_cosine"] is None
    custom = VA.consistency([synth(), synth(seed=1)], SR, embedder=lambda x, sr: np.array([1.0, 0.0]), name="stub")
    assert custom == {"embedder": "stub", "takes": 2, "min_cosine": 1.0, "mean_cosine": 1.0}


def test_two_voices_must_differ_by_a_bp138_margin_and_the_margins_come_from_the_registry():
    from explainer_engine.standards import sourced_rules as SR_
    low, near, high = (VA.measure(synth(f, syll=4.0), SR) for f in (100.0, 102.0, 150.0))
    assert not VA.distinct({"a": low, "c": high})  # 100 -> 150 Hz is about 7 st
    found = VA.distinct({"a": low, "b": near})
    assert found and found[0]["rule"] == "VC-04" and found[0]["severity"] == "REVIEW" and found[0]["where"] == "a / b"
    assert VA.difference(low, high)["f0_st"]["margin"] == SR_.T("BP-138", "f0_margin_st")
    assert VA.distinct({"a": {}, "b": {}})[0]["detail"].startswith("no measure to compare")


def test_a_pace_difference_alone_separates_two_voices():
    slow = VA.measure(synth(100, syll=3.0, pauses=()), SR, " ".join(["w"] * 20))
    fast = VA.measure(synth(100, syll=3.0, pauses=()), SR, " ".join(["w"] * 40))
    diff = VA.difference(slow, fast)
    assert diff["rate"]["measure"] == "wpm_speaking" and diff["rate"]["met"] is True


def test_the_record_is_a_valid_contract_and_keeps_the_free_source():
    x = synth()
    rec = VA.record("v1", "Voice One", x, SR, {"kind": "library_preview", "ref": "https://example.test/p.mp3"},
                    takes=[synth(seed=1), synth(seed=2)], fit=casting.fit({"voice_id": "v1", "labels": {"gender": "male"}},
                                                                          {"voice": {"traits": {"gender": "male"}}}, 0, 5))
    assert contracts.validate(rec) == []
    assert rec["consistency"]["takes"] == 2 and rec["fit"]["usage_rank"] == 0
    bad = copy.deepcopy(rec)
    bad["source"]["kind"] = "paid_take"
    with pytest.raises(ContractError):
        contracts.validate(bad)


# -- the channel registry ----------------------------------------------------------------------------------------------

def test_the_shipped_registry_is_valid_and_names_the_channel_narrator():
    reg = VC.load_registry()
    nar = VC.channel_voice(reg)
    assert nar["voice_id"] == "NOpBlnGInO9m6vDvFkFC" and nar["status"] == "channel" and nar["baseline"]["kind"] == "read"
    assert VC.registry_errors(reg) == []


OTHER = {"voice_id": "other", "name": "Other", "role": "narrator", "status": "channel", "model": "eleven_v4", "baseline": None}
SPUDS = "NOpBlnGInO9m6vDvFkFC"


def word(root, voice_id, ref="cmsg_ok", now=None):
    from explainer_engine.governance import records
    records.add("channel_voice", voice_id, ref, "ვანო: კი", root=root, now=now)
    return ref


def test_only_the_creators_recorded_word_replaces_the_channel_narrator(tmp_path):
    reg = VC.load_registry()
    with pytest.raises(ContractError, match="VC-08"):
        VC.register(reg, OTHER)
    with pytest.raises(ContractError, match="no recorded creator word"):
        VC.register(reg, OTHER, creator_ref="cmsg_invented", root=tmp_path)  # a ref nobody recorded
    ref = word(tmp_path, "other")
    new = VC.register(reg, OTHER, creator_ref=ref, root=tmp_path)
    assert VC.channel_voice(new)["voice_id"] == "other"
    assert [v["status"] for v in new["voices"] if v["voice_id"] == SPUDS] == ["retired"]
    assert VC.channel_voice(reg)["voice_id"] == SPUDS  # the input is not changed
    candidate = dict(OTHER, status="candidate")
    assert VC.register(reg, candidate)["voices"][-1]["status"] == "candidate"  # a candidate needs no word


def test_a_word_for_another_voice_or_another_action_does_not_count(tmp_path):
    from explainer_engine.governance import records
    reg = VC.load_registry()
    records.add("channel_voice", "someone_else", "cmsg_a", "ვანო: კი", root=tmp_path)
    records.add("model_switch", "other", "cmsg_b", "ვანო: კი", root=tmp_path)
    records.add("channel_voice", "*", "cmsg_c", "ვანო: კი", root=tmp_path)  # no wildcard for the channel voice
    for ref in ("cmsg_a", "cmsg_b", "cmsg_c"):
        with pytest.raises(ContractError, match="no recorded creator word"):
            VC.register(reg, OTHER, creator_ref=ref, root=tmp_path)


def test_a_word_to_retire_the_standing_voice_does_not_crown_another_one(tmp_path):
    """Review of #50: the word must be for the voice that BECOMES the channel voice."""
    reg = VC.load_registry()
    standing = next(v for v in reg["voices"] if v["voice_id"] == SPUDS)
    ref = word(tmp_path, SPUDS)
    VC.register(reg, dict(standing, status="retired"), creator_ref=ref, root=tmp_path)  # his word retires Spuds
    with pytest.raises(ContractError, match="no recorded creator word 'cmsg_ok' for other"):
        VC.register(reg, OTHER, creator_ref=ref, root=tmp_path)  # but crowns nobody
    with pytest.raises(ContractError, match="for fresh"):
        VC.register(reg, dict(OTHER, voice_id="fresh"), creator_ref=ref, root=tmp_path)


def test_a_word_expires_after_the_window(tmp_path):
    import time
    reg = VC.load_registry()
    ref = word(tmp_path, "other", now=time.time() - (VC.WORD_MINUTES + 1) * 60)
    with pytest.raises(ContractError, match="no recorded creator word"):
        VC.register(reg, OTHER, creator_ref=ref, root=tmp_path)
    fresh = word(tmp_path, "other", ref="cmsg_new", now=time.time() - (VC.WORD_MINUTES - 5) * 60)
    assert VC.channel_voice(VC.register(reg, OTHER, creator_ref=fresh, root=tmp_path))["voice_id"] == "other"
    assert VC.WORD_MINUTES == 60


def test_retiring_demoting_or_changing_the_standing_narrator_needs_the_word_too(tmp_path):
    """Review of #45: retiring the narrator and then adding a new one must not get round VC-08 in two calls; a new model or
    baseline of the standing voice changes what EL-13 measures, so it needs the word as well."""
    reg = VC.load_registry()
    standing = next(v for v in reg["voices"] if v["voice_id"] == SPUDS)
    ref = word(tmp_path, SPUDS)
    changes = ({"status": "retired"}, {"status": "candidate"}, {"role": "character"}, {"model": "eleven_v5"},
               {"baseline": dict(standing["baseline"], centroid_hz=1200.0)}, {"baseline": None})
    for change in changes:
        with pytest.raises(ContractError, match="VC-08"):
            VC.register(reg, dict(standing, **change))
        done = VC.register(reg, dict(standing, **change), creator_ref=ref, root=tmp_path)
        assert next(v for v in done["voices"] if v["voice_id"] == SPUDS) == dict(standing, **change)
    # the name and the note are free; the first channel voice of a role needs no word
    renamed = VC.register(reg, dict(standing, note="reworded"))
    assert VC.channel_voice(renamed)["note"] == "reworded"
    first_character = dict(OTHER, role="character")
    assert VC.channel_voice(VC.register(reg, first_character), "character")["voice_id"] == "other"


@pytest.mark.parametrize("ref", ["", " ", "\t\n"])
def test_a_blank_creator_word_is_refused_everywhere(ref):
    reg = VC.load_registry()
    with pytest.raises(ContractError, match="blank"):
        VC.register(reg, OTHER, creator_ref=ref)
    with pytest.raises(ContractError, match="blank"):
        VC.register(reg, dict(OTHER, status="candidate"), creator_ref=ref)
    assert "channel_voice" in __import__("explainer_engine.governance.records", fromlist=["x"]).ACTIONS


def test_a_registry_with_two_channel_narrators_or_a_repeated_id_is_refused():
    reg = VC.load_registry()
    two = copy.deepcopy(reg)
    two["voices"].append(dict(two["voices"][0], voice_id="b"))
    assert any(f["rule"] == "VC-08" for f in VC.registry_errors(two))
    dup = copy.deepcopy(reg)
    dup["voices"].append(dict(dup["voices"][0], status="retired"))
    assert any("listed twice" in f["detail"] for f in VC.registry_errors(dup))
    with pytest.raises(ContractError):
        VC.register(reg, {"voice_id": "z", "name": "Z", "role": "narrator", "status": "candidate", "model": "eleven_v4"})


def _registry_for(x):
    p = VA.measure(x, SR)
    base = VA.baseline_of(p, "read", "test")
    return {"schema": "channel_voices/1", "voices": [{"voice_id": "v", "name": "V", "role": "narrator", "status": "channel",
                                                      "model": "eleven_v4", "baseline": base}]}


def test_el13_a_take_that_sounds_like_the_baseline_is_clean_and_a_darker_one_is_review():
    reg = _registry_for(synth(100, seed=1))
    _, clean = VC.check_against(synth(100, seed=2), SR, "v", reg)
    assert clean == []
    windows, dark = VC.check_against(tilt(synth(100, seed=3), -1.5), SR, "v", reg)
    assert windows and dark and all(f["rule"] == "EL-13" and f["severity"] == "REVIEW" for f in dark)
    assert "baseline (read)" in dark[0]["detail"]


def test_el13_says_so_when_it_cannot_compare():
    reg = _registry_for(synth())
    assert "not in config" in VC.check_against(synth(), SR, "ghost", reg)[1][0]["detail"]
    nobase = copy.deepcopy(reg)
    nobase["voices"][0]["baseline"] = None
    assert "no baseline" in VC.check_against(synth(), SR, "v", nobase)[1][0]["detail"]
    assert "too short" in VC.check_against(synth(seconds=0.5, pauses=()), SR, "v", reg)[1][0]["detail"]


# -- casting: eligible, fit, the popularity tie-break -------------------------------------------------------------------

OLD = {"names": ["x"], "voice": {"style": "warm", "traits": {"gender": "male", "age": "old", "origin": "USA"}}}


def v(vid, **kw):
    return {"voice_id": vid, "name": vid, **kw}


def test_library_age_words_are_read_as_our_bands():
    senior = v("s", labels={"Age": "Senior", "Gender": "Male", "Accent": "American"})
    young = v("y", labels={"age": "young", "gender": "male"})
    assert casting.eligible(senior, OLD) == []
    assert casting.eligible(young, OLD)[0].startswith("labelled 'young'")
    assert casting.score(senior, OLD) > 0.8


def test_eligible_refuses_famous_imitation_taken_and_wrong_age():
    assert any("famous" in r for r in casting.eligible(v("a", description="Similar to famous documentary voice"), OLD))
    assert any("famous" in r for r in casting.eligible(v("a", category="famous"), OLD))
    assert any("already" in r for r in casting.eligible(v("a"), OLD, taken={"a"}))
    assert casting.eligible(v("a"), OLD) == []


def test_equal_trait_scores_go_to_the_more_used_voice_and_the_label_says_so():
    lab = {"gender": "male", "age": "old", "accent": "american"}
    voices = [v("most", labels=lab), v("mid", labels=lab), v("least", labels=lab), v("bare")]
    r = casting.rank(voices, OLD, by_usage=True)
    assert [c["voice_id"] for c in r] == ["most", "mid", "least"]
    assert "most-used #1 of 4 listed" in r[0]["why"]
    flipped = casting.rank(list(reversed(voices)), OLD, by_usage=True)
    assert flipped[0]["voice_id"] == "least"  # list order is the usage order the caller asks the connector for
    f = casting.fit(v("bare"), OLD, 3, 4)
    assert f["unlabelled"] is True and f["usage_rank"] == 3
    assert "most-used" not in casting.rank(voices, OLD)[0]["why"]  # the old call is unchanged


def test_an_ltx_cast_card_voice_is_words_from_traits_and_never_a_person():
    text = casting.ltx_voice_text(OLD)
    assert "elderly" in text and "male" in text
    named = {"names": ["Napoleon"], "voice": {"style": "sounds like Napoleon", "traits": {"gender": "male"}}}
    with pytest.raises(ValueError):
        casting.ltx_voice_text(named)


def test_there_is_no_elevenlabs_rest_client_in_the_package():
    """The narrator goes through the connector's hook and ledger only (the creator's D8 answer, 2026-10-29)."""
    assert not (ROOT / "explainer_engine" / "audio" / "elevenlabs_rest.py").exists()
    for p in (ROOT / "explainer_engine").rglob("*.py"):
        assert not re.search(r"api\.elevenlabs\.io|xi-api-key", p.read_text(encoding="utf-8")), p
