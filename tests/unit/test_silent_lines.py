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
    seg = out[k:k + int(0.2 * sr)]
    rms_db = 20 * np.log10(np.sqrt(np.mean(seg.astype(np.float64) ** 2)) + 1e-12)
    assert rms_db < -46 and np.any(seg != 0)  # room tone where the bubble is read, never digital zero (ED-12)


def test_gap_opens_at_the_quiet_spot_not_the_measured_middle():
    """Word times are off by 0.1-0.2 s: the gap goes where the read is really quiet, not into a consonant (ED-12)."""
    d = doc()
    sr = 1000
    voiced = []
    t = 0.1
    for tk in S.tokens(SIL.voiced_doc(d)):
        voiced.append({"w": tk["w"], "s": round(t, 3), "e": round(t + 0.3, 3)})
        t += 0.4
    pcm = np.full(int((t + 0.5) * sr), 0.5, dtype=np.float32)
    e3, s4 = voiced[3]["e"], voiced[4]["s"]
    q = int(round((e3 + 0.02) * sr))  # the real pause sits early in the gap, the middle still rings
    pcm[q - 10:q + 10] = 0.0
    out, words = SIL.insert(d, voiced, pcm, sr)
    k = int(round((words[4]["s"] - SIL.LEAD_S) * sr))
    assert abs(k - q) <= 15


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


def test_a_missed_word_after_the_gap_never_lands_before_it():
    """Titans "Elon Musk. Musk signs.": the recogniser missed the second "Musk", its interpolated time fell before the
    insert point and the shot "Musk signs" was cut 40 s too early. A word of a line after the gap starts after the gap."""
    d = doc()
    sr = 1000
    voiced = []
    t = 0.1
    for tk in S.tokens(SIL.voiced_doc(d)):
        voiced.append({"w": tk["w"], "s": round(t, 3), "e": round(t + 0.3, 3)})
        t += 0.4
    voiced[4] = dict(voiced[4], s=voiced[3]["e"] - 0.01, e=voiced[3]["e"])  # "He" interpolated onto "cold."
    pcm = np.full(int((t + 0.5) * sr), 0.5, dtype=np.float32)
    out, words = SIL.insert(d, voiced, pcm, sr)
    silent = [w for w in words if w.get("silent")]
    after = words[words.index(silent[-1]) + 1:]
    assert after and all(w["s"] >= silent[-1]["e"] for w in after)
    assert [w["s"] for w in words] == sorted(w["s"] for w in words)


def test_the_narrator_reports_the_exchange_bubbles_are_only_an_accent():
    """D-63: the creator found bubble-only dialogue unread and boring; one accent bubble per scene is allowed, two FAIL."""
    d = doc()
    long = next(ln for ln in d["segments"][0]["lines"] if not SIL.voiced(ln))
    assert any("BP-84" in why for why in SIL.check_reported_dialogue(d))  # a 15-word bubble is a line read alone (D-64)
    long["text"] = " ".join(long["text"].split()[:SIL.max_words()])  # the accent: a key phrase of BP-38's words
    assert SIL.check_reported_dialogue(d) == []  # one silent line: an accent
    d["segments"][0]["lines"].append({"text": "Fine.", "speaker": "musk", "voiced": False})
    assert SIL.check_reported_dialogue(d) and "D-63" in SIL.check_reported_dialogue(d)[0]
    d["segments"][0]["lines"][-1] = {"text": "Musk shrugs and says fine."}
    assert SIL.check_reported_dialogue(d) == []

