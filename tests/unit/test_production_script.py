"""D-43: the production script (one JSON = narration, voice direction, pictures and prompts, sounds, edit) and its
pipeline: compile, validate, time, assemble; plus the Day 1 script itself."""
import copy
import json
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.audio.pause_pad import pad_pauses
from explainer_engine.production import __main__ as CLI
from explainer_engine.production import assemble as A
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.production import validate as V

ROOT = Path(__file__).resolve().parents[2]
WORLD = json.loads((ROOT / "examples" / "stone_age" / "day1_v6" / "world_spec.json").read_text())
DAY1 = ROOT / "examples" / "stone_age" / "day1_v7" / "production_script.json"


def mini() -> dict:
    return {
        "schema": "production_script/1",
        "episode": {"id": "mini", "title": "Mini test", "fps": 30, "grade": "prehistory"},
        "voice": {"provider": "elevenlabs", "model": "eleven_v4", "voice_id": "x", "name": "X",
                  "style": "soft, deep, calm and warm storyteller", "pace_wpm": [140, 158]},
        "world": WORLD,
        "look": {"default_engine": "gemini"},
        "cast": {"einstein": {"names": ["einstein"], "card": "young Albert Einstein, untidy hair, moustache",
                              "props": ["reading glasses"]},
                 "franklin": {"names": ["franklin"], "card": "Benjamin Franklin, balding, round spectacles"}},
        "story": {"events": [{"thing": "fire", "at": "and fire"}], "forbidden_props": ["magnifying glass"]},
        "library": {"camp": {"file": "camp.png", "heroes": [], "shows": ["fire"]},
                    "valley": {"file": "valley.png", "heroes": [], "shows": []},
                    "duo": {"file": "duo.png", "heroes": ["franklin", "einstein"], "shows": [],
                            "speakers": {"einstein": [0.7, 0.3]}}},
        "music": [{"track": "tone", "from": "<start>", "to": None, "gain_db": -20}],
        "segments": [
            {"id": "S01", "beat": "dusk", "light_beat": 5,
             "lines": [{"text": "Could they survive the night?", "tags": ["softly"], "emphasis": ["night"], "pause_after": 0.6},
                       {"text": "Nobody knows, not even the bravest of them, and the cold wind is rising."}],
             "shots": [{"at": "Could", "type": "A", "picture": "valley", "motion": {"kind": "push", "z0": 1.0, "z1": 1.05}},
                       {"at": "Nobody knows.", "type": "C", "insert": True, "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0},
                        "picture": {"id": "cold_hands", "subject": "cold trembling hands rubbing together in the rising wind at dusk"}}],
             "audio": {"beds": [{"at": "Could", "sound": "wind"}]}},
            {"id": "S02", "beat": "fire", "light_beat": 6,
             "lines": [{"text": "Then Einstein takes off his glasses."}, {"text": "Oh. A lens."},
                       {"text": "One careful breath, and fire! A small flame, and a hundred tired faces turn toward it."}],
             "shots": [{"at": "Then Einstein", "type": "B", "picture": "duo", "motion": {"kind": "push", "z0": 1.0, "z1": 1.03},
                        "bubbles": [{"at": "Oh.", "who": "einstein", "text": "Oh. A lens!"}]},
                       {"at": "and fire", "type": "A", "picture": "camp", "reveal": "fire",
                        "motion": {"kind": "pull", "z0": 1.06, "z1": 1.0}}],
             "audio": {"sfx": [{"at": "One careful", "sound": "pop", "gain_db": -20, "max_s": 0.5}],
                       "beds": [{"at": "and fire", "sound": "crackle"}]}},
        ],
    }


def compiled() -> dict:
    return C.compile_doc(mini())


def rules(found, sev="FAIL"):
    return {f["rule"] for f in found if f["severity"] == sev}


def words_for(doc, gap=0.7):
    out, t = [], 0.2
    for tk in S.tokens(doc):
        out.append({"w": tk["w"], "s": round(t, 3), "e": round(t + 0.38, 3), "para": tk["para"]})
        t += 0.38 + (gap if tk["w"][-1] in ".,!?" else 0.08)
    return {"words": out, "duration": round(t + 0.6, 3)}


# --- script ----------------------------------------------------------------------------------------------------------

def test_mini_is_valid_after_compile():
    found = V.check_script(compiled())
    assert not rules(found), found


def test_tts_text_carries_tags_emphasis_and_pauses():
    tts = S.tts_text(mini())
    assert tts.startswith("[softly] Could they survive the NIGHT? [short pause] Nobody knows,")
    assert S.narration_text(mini()).splitlines()[0] .startswith("Could they survive the night? Nobody knows,")


def test_tokens_know_their_segment_and_line():
    toks = S.tokens(mini())
    assert [t["seg"] for t in toks].count(0) == 19 and toks[-1]["line"] == 2


def test_compile_writes_prompts_with_the_d41_slots():
    d = compiled()
    p = d["segments"][0]["shots"][1]["picture"]["prompt"]
    assert p.startswith("tight cinematic insert, cold trembling hands") and "frock coats" in p


def test_stale_prompt_and_missing_prompt_fail():
    d = compiled()
    d["segments"][0]["shots"][1]["picture"]["subject"] = "warm hands by a campfire"
    assert "PV-11" in rules(V.check_script(d))
    assert "PV-11" in rules(V.check_script(mini()))


def test_phrase_outside_its_segment_or_late_opening_fails():
    d = compiled()
    d["segments"][0]["shots"][1]["at"] = "Then Einstein"
    assert "PV-04" in rules(V.check_script(d))
    d = compiled()
    d["segments"][1]["shots"][0]["at"] = "Oh."
    found = V.check_script(d)
    assert any(f["rule"] == "PV-04" and "first picture waits" in f["detail"] for f in found)


def test_undefined_or_twice_defined_picture_fails():
    d = compiled()
    d["segments"][1]["shots"][1]["picture"] = "nowhere"
    assert "PV-03" in rules(V.check_script(d))
    d = compiled()
    d["segments"][1]["shots"][1]["picture"] = copy.deepcopy(d["segments"][0]["shots"][1]["picture"])
    assert "PV-03" in rules(V.check_script(d))


def test_duplicate_prompts_fail():
    d = mini()
    pic = copy.deepcopy(d["segments"][0]["shots"][1]["picture"])
    pic["id"] = "cold_hands_2"
    d["segments"][1]["shots"].insert(1, {"at": "Oh.", "type": "C", "insert": True, "picture": pic,
                                         "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0}})
    d["segments"][0]["light_beat"] = d["segments"][1]["light_beat"]
    assert "PV-06" in rules(V.check_script(C.compile_doc(d)))


def test_forbidden_prop_and_wrong_owner_fail():
    d = mini()
    d["library"]["duo"]["props"] = [{"thing": "reading glasses", "held_by": "franklin"}]
    d["segments"][0]["shots"][1]["picture"]["subject"] = "a magnifying glass over dry grass"
    found = V.check_script(C.compile_doc(d))
    assert sum(f["rule"] == "PV-07" for f in found) == 2


def test_story_state_is_checked_at_the_word_before_any_read():
    d = mini()
    d["segments"][1]["shots"][0]["picture"] = "camp"  # fire on screen before "and fire"
    found = V.check_script(C.compile_doc(d))
    assert any("STATE-1" in f["rule"] for f in found if f["severity"] == "FAIL")


def test_wrong_hero_for_the_line_fails():
    d = mini()
    d["library"]["duo"]["heroes"] = ["franklin"]
    d["library"]["duo"]["speakers"] = {"franklin": [0.3, 0.3]}
    found = V.check_script(C.compile_doc(d))
    assert any("HERO-1" in f["rule"] for f in found if f["severity"] == "FAIL")


def test_voice_must_not_name_a_person_to_imitate():
    d = compiled()
    d["voice"]["style"] = "deep and calm, sounds like Famous Actor"
    assert "PV-10" in rules(V.check_script(d))


def test_schema_rejects_unknown_fields_and_bad_motion():
    d = compiled()
    d["segments"][0]["shots"][0]["motion"]["z1"] = 1.4
    d["segments"][0]["colour"] = "red"
    assert len(S.schema_errors(d)) == 2


# --- timing ----------------------------------------------------------------------------------------------------------

def test_timing_tiles_frames_exactly_and_lands_on_the_phrases():
    d = compiled()
    w = words_for(d)
    timed = T.time_script(d, w)
    shots = timed["shots"]
    assert shots[0]["start_frame"] == 0 and shots[-1]["end_frame"] == timed["frames"]
    assert all(a["end_frame"] == b["start_frame"] for a, b in zip(shots, shots[1:]))
    assert all(s["cut_legal"] for s in shots)
    fire = shots[3]
    assert fire["text"].startswith("and fire!") and fire["start"] < w["words"][fire["word"]]["s"]
    assert timed["events"]["fire"] == fire["start"]
    b = shots[2]["bubbles"][0]
    assert shots[2]["start"] <= b["start"] < b["end"] <= shots[2]["end"]
    beds = timed["audio"]["beds"]
    assert beds[0]["start"] == 0.0 and beds[-1]["end"] == timed["duration"]
    assert not rules(V.check_timed(timed, d))


def test_timed_check_catches_gaps_and_order():
    d = compiled()
    timed = T.time_script(d, words_for(d))
    timed["shots"][1]["end_frame"] -= 3
    timed["shots"][2]["start"] = timed["shots"][1]["start"] - 0.1
    found = V.check_timed(timed, d)
    assert sum(f["rule"] == "PV-21" for f in found) >= 2


def test_timing_on_another_reads_text_reports_the_match():
    d = compiled()
    w = words_for(d)
    w["words"] = w["words"][:5] + w["words"][9:]
    timed = T.time_script(d, w)
    assert timed["text_match"] < T.MIN_TEXT_MATCH
    assert "PV-20" in rules(V.check_timed(timed, d))


def test_final_render_needs_every_picture():
    d = compiled()
    timed = T.time_script(d, words_for(d))
    assert "PV-25" in rules(V.check_timed(timed, d, final=True))
    assert "PV-25" not in rules(V.check_timed(timed, d, final=False))


def test_pause_pad_honours_scripted_pauses():
    words = [{"w": "night?", "s": 0.0, "e": 0.4}, {"w": "Nobody", "s": 0.5, "e": 0.8}]
    audio = np.zeros(48000)
    out, shifted, rep = pad_pauses(words, audio, 48000, targets={0: 0.6})
    assert abs((shifted[1]["s"] - shifted[0]["e"]) - 0.6) < 1e-3 and len(out) > len(audio)


# --- the Day 1 script ------------------------------------------------------------------------------------------------

def test_day1_script_is_valid():
    doc = S.load(DAY1)
    found = V.check_script(doc)
    assert not rules(found), [f for f in found if f["severity"] == "FAIL"]
    assert len(S.shots(doc)) >= 30


# --- end to end ------------------------------------------------------------------------------------------------------

def _wav(path: Path, x: np.ndarray, sr: int = 48000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="needs ffmpeg")
def test_end_to_end_script_to_video(tmp_path):
    from PIL import Image
    d = compiled()
    rng = np.random.default_rng(0)
    pics, snd = tmp_path / "pictures", tmp_path / "sounds"
    pics.mkdir(), snd.mkdir()
    for k, name in enumerate(["valley", "camp", "duo", "cold_hands"]):
        Image.fromarray((rng.random((180, 320, 3)) * 80 + k * 40).astype(np.uint8)).save(pics / f"{name}.png")
    sr = 48000
    _wav(snd / "wind.wav", rng.normal(0, 0.1, sr * 2))
    _wav(snd / "crackle.wav", rng.normal(0, 0.1, sr))
    _wav(snd / "pop.wav", np.sin(np.arange(sr // 4) * 0.2) * 0.5)
    _wav(snd / "tone.wav", np.sin(np.arange(sr * 2) * 2 * np.pi * 220 / sr) * 0.3)
    w = words_for(d)
    voice = np.zeros(int(w["duration"] * sr))
    for x in w["words"]:
        a, b = int(x["s"] * sr), int(x["e"] * sr)
        voice[a:b] = np.sin(np.arange(b - a) * 2 * np.pi * 150 / sr) * 0.5
    _wav(tmp_path / "narration.wav", voice)
    script, wjson = tmp_path / "script.json", tmp_path / "words.json"
    d["picture_dirs"], d["sound_dirs"] = ["pictures"], ["sounds"]
    script.write_text(json.dumps(d))
    wjson.write_text(json.dumps(w))
    assert CLI.main(["validate", str(script)]) == 0
    out = tmp_path / "out"
    assert CLI.main(["run", str(script), str(tmp_path / "narration.wav"), str(wjson), "--out", str(out),
                     "--size", "320x180"]) == 0
    timed = json.loads((out / "timed.json").read_text())
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", str(out / "video.mp4")],
                           capture_output=True, text=True).stdout.strip()
    assert int(probe) == timed["frames"]
    rep = json.loads((out / "assemble_report.json").read_text())
    assert rep["frames_written"] == timed["frames"] and rep["audio"]["music_dip_max_step_db_per_ms"] < 1.0


# --- 2026-10-16 fixes: chunked reads, voice drift, render guards ------------------------------------------------------

def test_tts_chunks_cover_every_segment_once_and_stay_short():
    doc = S.load(DAY1)
    chunks = S.tts_chunks(doc, max_chars=900)
    assert [s for c in chunks for s in c["segments"]] == [seg["id"] for seg in doc["segments"]]
    assert all(c["chars"] <= 900 or len(c["segments"]) == 1 for c in chunks) and len(chunks) >= 3
    assert chunks[1]["previous_text"] and chunks[0]["next_text"]


def test_voice_check_flags_a_darker_stretch():
    from explainer_engine.audio import voice_check
    sr = 16000
    rng = np.random.default_rng(1)
    def voice(n, bright):
        t = np.arange(n) / sr
        x = sum(np.sin(2 * np.pi * 110 * k * t) / k ** (1.2 if bright else 2.4) for k in range(1, 40))
        return 0.1 * x / np.abs(x).max() + 0.001 * rng.standard_normal(n)
    x = np.concatenate([voice(60 * sr, True), voice(30 * sr, False)])
    _, found = voice_check.check(x, sr)
    assert found and all(f["severity"] == "REVIEW" for f in found)
    assert float(found[-1]["where"].split("-")[0]) >= 45


def test_assemble_refuses_a_timing_with_fail(tmp_path):
    with pytest.raises(SystemExit):
        A.assemble({"findings": [{"severity": "FAIL", "rule": "PV-25", "detail": "x"}]}, tmp_path / "n.wav", tmp_path, [], [])


def test_pv26_hero_needs_a_reference_with_their_face():
    """2026-10-16: two Snow pictures named a reference (d1-36) that shows Franklin and Einstein; the check now FAILs it."""
    import json
    from pathlib import Path
    from explainer_engine.production import validate as V
    path = Path(__file__).resolve().parents[2] / "examples" / "stone_age" / "week1_v1" / "production_script.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert not [f for f in V.check_script(doc) if f["rule"] == "PV-26"]
    bad = json.loads(json.dumps(doc))
    for seg in bad["segments"]:
        for sh in seg["shots"]:
            if isinstance(sh["picture"], dict) and sh["picture"]["id"] == "w1_snow_rule":
                sh["picture"]["refs"] = ["v5_d1-36"]
    found = [f for f in V.check_script(bad) if f["rule"] == "PV-26"]
    assert found and "snow" in found[0]["detail"] and found[0]["severity"] == "FAIL"
