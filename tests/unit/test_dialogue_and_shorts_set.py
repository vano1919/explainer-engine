"""D-45 voiced dialogue (a line's ``speaker`` reads in the hero's own voice: chunks, PV-32, per-speaker voice check) and
SH-05 (a set of Shorts: every Short its own question and its own scene; the last line points to the video)."""
import copy
import json
import shutil

import numpy as np
import pytest

from explainer_engine.audio import voice_check
from explainer_engine.production import __main__ as CLI
from explainer_engine.production import script as S
from explainer_engine.production import validate as V

from test_production_script import DAY1, ROOT, _wav, mini, words_for

EP1 = ROOT / "examples" / "stone_age" / "ep1_v1" / "production_script.json"


def dialogue() -> dict:
    d = mini()
    d["cast"]["einstein"]["voice"] = {"voice_id": "e1", "name": "E", "style": "bright, quick, amused tenor"}
    d["segments"][1]["lines"][1]["speaker"] = "einstein"  # "Oh. A lens."
    return d


def _rules(doc, rule, sev=None):
    return [f for f in V.check_script(doc, None) if f["rule"] == rule and (sev is None or f["severity"] == sev)]


# --- voiced dialogue -------------------------------------------------------------------------------------------------

def test_narrator_only_chunks_are_unchanged():
    chunks = S.tts_chunks(S.load(DAY1))
    assert all("speaker" not in c and "voice_id" not in c for c in chunks)
    assert [s for c in chunks for s in c["segments"]] == [seg["id"] for seg in S.load(DAY1)["segments"]]


def test_dialogue_chunks_never_mix_speakers_and_keep_the_order():
    d = dialogue()
    assert not S.schema_errors(d)
    chunks = S.tts_chunks(d, max_chars=900)
    assert [(c["speaker"], c["voice_id"]) for c in chunks] == [("narrator", "x"), ("einstein", "e1"), ("narrator", "x")]
    assert chunks[1]["text"] == "Oh. A lens." and chunks[1]["segments"] == ["S02"]
    said = " ".join(c["text"].replace("\n", " ") for c in chunks)
    assert said == S.tts_text(d).replace("\n", " ").strip()


def test_pv32_speaker_needs_a_cast_voice_described_not_imitated():
    d = dialogue()
    assert not _rules(d, "PV-32", "FAIL") and not _rules(d, "PV-10", "FAIL")
    bad = copy.deepcopy(d)
    bad["segments"][1]["lines"][1]["speaker"] = "newton"
    assert _rules(bad, "PV-32", "FAIL")
    bad = copy.deepcopy(d)
    del bad["cast"]["einstein"]["voice"]
    assert _rules(bad, "PV-32", "FAIL")
    bad = copy.deepcopy(d)
    bad["cast"]["einstein"]["voice"]["style"] = "sounds like a famous film actor"
    assert _rules(bad, "PV-10", "FAIL")
    bad = copy.deepcopy(d)
    bad["cast"]["einstein"]["voice"]["voice_id"] = "x"  # the narrator's voice
    assert _rules(bad, "PV-32", "REVIEW")
    bad["cast"]["einstein"]["voice"]["voice_id"] = None
    assert any("no voice chosen" in f["detail"] for f in _rules(bad, "PV-32", "REVIEW"))


def _voice(n, sr, bright, rng):
    t = np.arange(n) / sr
    x = sum(np.sin(2 * np.pi * 110 * k * t) / k ** (1.2 if bright else 2.4) for k in range(1, 40))
    return 0.1 * x / np.abs(x).max() + 0.001 * rng.standard_normal(n)


def test_voice_check_by_speaker_ignores_the_other_voice_and_finds_a_stray_turn():
    sr, rng = 16000, np.random.default_rng(2)
    parts, turns, t = [], [], 0.0
    for k in range(12):  # alternating 6 s turns: a bright narrator, a darker hero
        who = "narrator" if k % 2 == 0 else "einstein"
        parts.append(_voice(6 * sr, sr, who == "narrator", rng))
        turns.append((who, t, t + 6))
        t += 6
    x = np.concatenate(parts)
    _, found = voice_check.check_speakers(x, sr, turns)
    assert not found
    parts[5] = _voice(6 * sr, sr, True, rng)  # one hero turn read in another-sounding voice
    _, found = voice_check.check_speakers(np.concatenate(parts), sr, turns)
    assert [f["where"] for f in found] == ["30-36 s"] and found[0]["detail"].startswith("einstein:")


# --- a set of Shorts (SH-05) -----------------------------------------------------------------------------------------

def _short(sid, hook, body, pics, last="The full story is on the channel."):
    return {"id": sid, "hook": hook, "lines": [{"text": hook}] + [{"text": b} for b in body] + [{"text": last}],
            "shots": [{"at": hook.split()[0], "picture": p, "crop_x": 0.5} for p in pics]}


def test_shorts_set_each_short_its_own_question_and_scene():
    d = mini()
    a = _short("SH01", "Could they survive the night?", ["Nobody knows, not even the bravest of them."], ["valley"])
    b = _short("SH02", "Could a lens make fire?", ["Then Einstein takes off his glasses."], ["duo", "camp"])
    d["shorts"] = [a, b]
    assert not [f for f in _rules(d, "PV-28") if "SH-05" in f["detail"] or "SH-01)" in f["detail"]]
    d["shorts"] = [a, copy.deepcopy(a) | {"id": "SH02"}]
    found = _rules(d, "PV-28")
    assert any(f["severity"] == "FAIL" and "same hook" in f["detail"] for f in found)
    assert any(f["severity"] == "REVIEW" and "also told in SH01" in f["detail"] for f in found)
    assert any(f["severity"] == "REVIEW" and "pictures are also in SH01" in f["detail"] for f in found)
    d["shorts"] = [_short("SH01", a["hook"], ["Nobody knows."], ["valley"], last="So cold.")]
    assert any("does not point to the full video" in f["detail"] for f in _rules(d, "PV-28", "REVIEW"))


def test_episode1_shorts_pass_the_set_rules():
    found = [f for f in _rules(S.load(EP1), "PV-28") if "SH-05" in f["detail"] or "SH-01)" in f["detail"]]
    assert not found


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_words_checks_each_voice_on_its_own_turns(tmp_path, monkeypatch):
    d, sr, rng = dialogue(), 48000, np.random.default_rng(3)
    w = words_for(d)
    x = rng.normal(0, 3e-4, int(w["duration"] * sr))  # a room floor: exact-zero runs read as cut words (ED-12)
    seen, real = {}, voice_check.check_speakers

    def spy(pcm, rate, turns):
        seen["turns"] = turns
        return real(pcm, rate, turns)
    monkeypatch.setattr(voice_check, "check_speakers", spy)
    for tk, ww in zip(S.tokens(d), w["words"]):
        a, b = int(ww["s"] * sr), int(ww["e"] * sr)
        x[a:b] = _voice(b - a, sr, S.speaker(d["segments"][tk["seg"]]["lines"][tk["line"]]) == "narrator", rng)
    _wav(tmp_path / "read.wav", x)
    tr = tmp_path / "scribe.json"
    tr.write_text(json.dumps({"words": [{"text": ww["w"], "start": ww["s"], "end": ww["e"]} for ww in w["words"]]}))
    rep = CLI.cmd_words(d, [tmp_path / "read.wav"], tmp_path / "out", tr)
    assert [t[0] for t in seen["turns"]] == ["narrator", "einstein", "narrator"]
    lens = [w["words"][i]["s"] for i, tk in enumerate(S.tokens(d)) if tk["seg"] == 1 and tk["line"] == 1]
    assert abs(seen["turns"][1][1] - lens[0]) < 0.3 and rep["voice_check"] == []
    assert rep["narrator_polish"] is None  # a conversation is not the narrator's read: no polish


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_words_polishes_a_single_narrator_read(tmp_path):
    d, sr, rng = dialogue(), 48000, np.random.default_rng(4)
    for seg in d["segments"]:
        for line in seg["lines"]:
            line.pop("speaker", None)
    assert not S.has_dialogue(d)
    w = words_for(d)
    x = rng.normal(0, 3e-4, int(w["duration"] * sr))
    for ww in w["words"]:
        a, b = int(ww["s"] * sr), int(ww["e"] * sr)
        x[a:b] = _voice(b - a, sr, True, rng)
    _wav(tmp_path / "read.wav", x)
    tr = tmp_path / "scribe.json"
    tr.write_text(json.dumps({"words": [{"text": ww["w"], "start": ww["s"], "end": ww["e"]} for ww in w["words"]]}))
    rep = CLI.cmd_words(d, [tmp_path / "read.wav"], tmp_path / "out", tr)
    assert rep["narrator_polish"]["chain"].startswith("volume=-0.6dB") and not (tmp_path / "out" / "narration.polish.wav").exists()
