"""FA-14 (Fable audit 2026-11-13): the hero identity rows before money (storyboard) and on the clips (G10). The audit's case:
two frames of one hero whose helmet changes colour across a cut must be flagged by the hero-box palette row."""
from __future__ import annotations

import numpy as np

from explainer_engine.core import open_questions as OQ
from explainer_engine.videolane import identity as ID


def _frame(helmet):
    f = np.full((180, 320, 3), (60, 70, 80), np.uint8)          # the set
    f[40:180, 20:140] = (150, 110, 80)                         # the hero on the left: body
    f[20:70, 40:120] = helmet                                  # ... and the helmet
    return f


def _script():
    shot = lambda sid: {"shot_id": sid, "segment_id": "S1", "location_id": "L", "route": "video",
                        "character_ids": ["hero"], "edit_plan": {"continuity_mode": "coverage",
                                                                "screen_positions": {"hero": "left"}}}
    return {"shots": [shot("A"), shot("B")], "world_bible": {"characters": [{"character_id": "hero", "name": "Hero"}]}}


def test_a_changed_helmet_colour_is_flagged():
    same = ID.costume_findings(_script(), ["A", "B"], {"A": (_frame((200, 40, 40)),) * 2, "B": (_frame((200, 40, 40)),) * 2})
    changed = ID.costume_findings(_script(), ["A", "B"], {"A": (_frame((200, 40, 40)),) * 2,
                                                          "B": (_frame((40, 60, 210)),) * 2})
    assert same == [] and len(changed) == 1 and "hero (head) A -> B" in changed[0]


def test_the_level_follows_switch_q3(monkeypatch):
    assert OQ.value("Q3") == "REVIEW" and ID.levels() == {"face": "REVIEW", "costume": "REVIEW"}
    monkeypatch.setattr(OQ, "value", lambda qid, path=OQ.PATH: "FAIL_FACE_REVIEW_COSTUME")
    assert ID.levels() == {"face": "FAIL", "costume": "REVIEW"}
    monkeypatch.setattr(OQ, "value", lambda qid, path=OQ.PATH: "FAIL")
    rows = ID.rows(_script(), ["A", "B"], {"A": (_frame((200, 40, 40)),) * 2, "B": (_frame((40, 60, 210)),) * 2}, {}, {},
                   "storyboard")
    cost = next(r for r in rows if r["gate"] == "storyboard_hero_costume_holds")
    face = next(r for r in rows if r["gate"] == "storyboard_hero_face_holds")
    assert cost["status"] == "FAIL"
    assert face["status"] == "REVIEW" and "NOT MEASURED" in face["detail"]     # no face tools: never a pass
