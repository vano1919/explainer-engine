"""words_to_mouth_cues: Scribe word timings -> Rhubarb-shaped cues that blender.rigs.LipSync accepts."""
import json

from explainer_engine.audio import words_to_mouth_cues as W
from explainer_engine.blender import rigs

WORDS = [{"text": "Be", "type": "word", "start": 0.2, "end": 0.4},
         {"text": "on", "type": "word", "start": 0.5, "end": 0.7},
         {"text": "spacing", "type": "spacing", "start": 0.7, "end": 0.72},
         {"text": "bells", "type": "word", "start": 0.8, "end": 1.4}]


def test_word_cues_follow_the_spelling():
    cues = W.word_cues("Be", 0.0, 0.2)
    assert [c["value"] for c in cues] == ["A", "C"]  # b closes the lips, e opens
    assert cues[0]["start"] == 0.0 and cues[-1]["end"] == 0.2


def test_mouth_cues_rest_in_gaps_and_tail_and_merge_short_cues():
    cues = W.mouth_cues(WORDS, duration=2.0)
    assert cues[0] == {"start": 0.0, "end": 0.2, "value": "X"}
    assert cues[-1]["value"] == "X" and cues[-1]["end"] == 2.0
    for a, b in zip(cues, cues[1:]):
        assert a["end"] == b["start"]
        assert a["value"] != b["value"]
    assert all(c["end"] - c["start"] >= W.MIN_CUE - 1e-9 for c in cues[1:])
    assert all(c["value"] in rigs.SHAPES for c in cues)


def test_rhubarb_doc_is_accepted_by_lipsync(tmp_path):
    doc = W.rhubarb_doc(WORDS, "line.wav", 2.0)
    assert doc["metadata"]["estimated"] is True
    p = tmp_path / "line.rhubarb.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert rigs.LipSync(fps=24).frames(p, frames=48)  # the checked reader: known shapes, sorted, no overlap


def test_cli_reads_a_wav_and_writes_the_doc(tmp_path):
    import wave
    wav = tmp_path / "l.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b"\0\0" * 16000)
    words = tmp_path / "w.json"
    words.write_text(json.dumps({"words": WORDS}), encoding="utf-8")
    out = tmp_path / "o.json"
    assert W.main(["--words", str(words), "--wav", str(wav), "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["metadata"]["duration"] == 2.0 and doc["mouthCues"][-1]["end"] == 2.0
