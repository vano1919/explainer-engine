"""Chunk reads are heard one by one and their words placed at the chunk's offset in the joined read."""

from pathlib import Path

from explainer_engine.audio import local_words as L


def test_words_of_each_chunk_move_to_its_offset(monkeypatch):
    heard = {"a.wav": [{"text": "Rivals", "start": 0.1, "end": 0.5}], "b.wav": [{"text": "Mostly?", "start": 0.0, "end": 0.4}]}
    monkeypatch.setattr(L, "transcribe", lambda p, model="small.en", prompt=None: {"words": heard[Path(p).name]})
    res = L.transcribe_chunks([Path("a.wav"), Path("b.wav")], [0.0, 2.3])
    assert [(w["text"], w["start"], w["end"]) for w in res["words"]] == [("Rivals", 0.1, 0.5), ("Mostly?", 2.3, 2.7)]
    assert "per chunk" in res["source"]
