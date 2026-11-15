"""Guard (Task 1 review, 2026-11-15): ``qa.gates.verdict`` keeps its per-gate rows under ``"gates"``; ``episode/run.py``
read a ``"rows"`` key that ``verdict`` never writes, so every layers25d and map clip record carried an EMPTY ``gate_rows``
list (Audit #33 looked fixed while the rows were still lost) and the director's own renderer rows were dropped too."""
from __future__ import annotations

import json

from explainer_engine.episode import run as RUN
from explainer_engine.qa import gates as G
from tests.unit.test_plan_step_3 import FPS, _make_episode, _shot


def test_verdict_rows_reads_the_key_verdict_writes():
    rows = [G.row("a", True, "ok"), G.row("b", False, "bad", level=G.REVIEW)]
    got = RUN._verdict_rows(G.verdict(rows))
    assert [r["gate"] for r in got] == ["a", "b"]
    assert RUN._verdict_rows(None) == [] and RUN._verdict_rows({"status": "PASS"}) == []


def test_layers25d_fallback_record_keeps_its_real_gate_rows(tmp_path):
    """A still shot without direction/layers falls back to layers25d (rehearsal); its record must carry the renderer's
    per-gate rows, not an empty list."""
    root = _make_episode(tmp_path, [_shot("S01_SH001", duration_s=1.0)])
    ep = RUN.Episode(root, size=(192, 108), fps=FPS, rehearsal=True, auto_direct=False)
    RUN.stage_clips(ep, rehearsal=True)
    recs = json.loads((root / "production" / "shot_records.json").read_text(encoding="utf-8"))["shots"]
    assert len(recs) == 1
    rows = recs[0].get("gate_rows")
    assert isinstance(rows, list) and len(rows) >= 1, recs[0]
    assert all("gate" in r and "status" in r for r in rows)


def test_soldiers_or_a_trench_in_frame_do_not_make_a_gunshot_seen():
    """Task 1 added ``soldier|soldiers|trench`` to the gunshot's seen-words, so every trench shot "saw" a shot and a
    gunshot passed the seen check anywhere in the film; only a weapon or a shot itself counts."""
    from explainer_engine.episode import sound_plan as SP
    assert not SP._SEEN["gunshot"].search("Two soldiers stand in the frozen trench")
    assert SP._SEEN["gunshot"].search("A rifle shot cracks across no man's land")
