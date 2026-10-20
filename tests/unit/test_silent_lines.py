"""D-62: silent lines are shown as bubbles, never voiced; bubbles stay off faces, stay still and never repeat."""
import numpy as np

from explainer_engine.finish import bubbles as BUB
from explainer_engine.production import script as S, silent as SIL


def doc():
    return {"schema": "production_script/3", "voice": {"voice_id": "nar", "pace_wpm": [160, 190]},
            "cast": {"musk": {"voice": {"voice_id": "m", "traits": {"real_person": True}}},
                     "vance": {"voice": {"voice_id": "v", "traits": {"real_person": False}}}},
            "segments": [{"id": "S01", "lines": [
                {"text": "The bench is cold."},
                {"text": "I can build it. Give me a week and three broken scooters from the lot.", "speaker": "musk",
                 "voiced": False},
                {"text": "He means it.", "speaker": "vance"}]}]}


def test_pieces_keep_bubbles_short():
    long = " ".join(f"w{i}" for i in range(30)) + "."
    for p in SIL.pieces(long):
        assert len(p.split()) <= SIL.max_words()
    assert SIL.pieces("Yes. No.") == ["Yes.", "No."]


def test_silent_lines_are_never_read():
    d = doc()
    assert "scooters" not in S.tts_text(d)
    chunks = S.tts_chunks(d)
    assert all("scooters" not in c["text"] for c in chunks)
    assert {c["speaker"] for c in chunks} == {"narrator", "vance"}


def test_insert_opens_a_gap_and_times_the_bubble_words():
    d = doc()
    sr = 1000
    vtoks = S.tokens(SIL.voiced_doc(d))
    voiced = []
    t = 0.1
    for tk in vtoks:
        voiced.append({"w": tk["w"], "s": round(t, 3), "e": round(t + 0.3, 3)})
        t += 0.4
    pcm = np.ones(int((t + 0.5) * sr), dtype=np.float32)
    out, words = SIL.insert(d, voiced, pcm, sr)
    toks = S.tokens(d)
    assert len(words) == len(toks)
    gap = SIL.seconds(d["segments"][0]["lines"][1])
    assert abs(len(out) / sr - (len(pcm) / sr + gap)) < 0.01
    silent = [w for w in words if w.get("silent")]
    assert len(silent) == len(S.tokens({"segments": [{"lines": [d["segments"][0]["lines"][1]]}]}))
    assert words.index(silent[0]) == 4  # after "The bench is cold."
    assert words[4]["s"] >= words[3]["e"]
    assert words[-1]["s"] >= silent[-1]["e"]  # the voice after the bubble moved on by the gap
    k = int(round((words[3]["e"] + 0.05) * sr))
    assert np.allclose(out[k:k + int(0.2 * sr)], 0.0)  # silence where the bubble is read


def test_real_person_never_voiced():
    d = doc()
    assert SIL.check_real_people(d) == []
    d["segments"][0]["lines"][1]["voiced"] = True
    assert SIL.check_real_people(d)
    d["cast"]["musk"]["voice"]["traits"]["living"] = False  # the dead: the provider's narrower rule, not PV-55
    assert SIL.check_real_people(d) == []


def test_same_text_never_twice():
    shots = [{"id": "SH001", "bubbles": [{"text": "I can build it.", "start": 1.0, "end": 3.0}]},
             {"id": "SH002", "bubbles": [{"text": "I can build it.", "start": 3.1, "end": 4.0}]}]
    assert SIL.check_duplicates(shots)
    shots[1]["bubbles"][0]["text"] = "Give me a week."
    assert SIL.check_duplicates(shots) == []


def test_bubble_on_one_shot_or_flagged():
    d = doc()
    toks = S.tokens(d)
    words = [{"w": t["w"], "s": i * 0.5, "e": i * 0.5 + 0.4} for i, t in enumerate(toks)]
    shots = [{"id": "SH001", "start": 0.0, "end": 3.0}, {"id": "SH002", "start": 3.0, "end": 30.0}]
    _, problems = SIL.bubbles_for(d, toks, words, lambda i: i, shots)
    assert any(p["rule"] == "BUBBLE-5" for p in problems)  # the cut at 3.0 s falls inside the first piece
    shots = [{"id": "SH001", "start": 0.0, "end": 30.0}]
    got, problems = SIL.bubbles_for(d, toks, words, lambda i: i, shots)
    assert problems == [] and [b["who"] for b in got[0]] == ["musk"] * len(got[0])


def test_bubble_avoids_every_face_and_stays_still():
    frame = (1920, 1080)
    speaker = (700.0, 600.0)
    other = BUB.head_box((1000.0, 600.0), frame)
    b = BUB.Bubble("Give me a week.", speaker, 1.0, 4.0, frame, faces=[other])
    assert not b.covers_face
    assert not BUB.overlaps(b.box, other) and not BUB.overlaps(b.box, BUB.head_box(speaker, frame))
    a1, a2 = b.frame_layer(2.0), b.frame_layer(3.5)
    assert a1[1] == a2[1]  # the same place on screen while it is up


def test_crowded_frame_reports_a_covered_face():
    frame = (1920, 1080)
    faces = [BUB.head_box((x, y), frame) for x in range(100, 1900, 150) for y in range(150, 1080, 200)]
    b = BUB.Bubble("Give me a week.", (960.0, 600.0), 1.0, 4.0, frame, faces=faces)
    assert b.covers_face
