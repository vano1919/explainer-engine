"""The Universal Rule Base checks (docs/UNIVERSAL_RULE_BASE.md): one good edit, one broken edit per rule, the measured
fire animatic v3 as a regression, and the committed Day 1 edit."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from explainer_engine.edit import shot_rules as R

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "tests/fixtures/fire_v3"
DAY1 = ROOT / "examples/stone_age/day1_v1"
LOOK = {"style_suffix": ", painted", "cast": ["einstein", "john snow"], "caricatures": ["einstein"],
        "phases": {"day1": {"palette": ["ochre", "umber", "fire amber"]}}}


def _words() -> list[dict]:
    text = ("Could they make fire? No matches, no tools. The night is cold. They try a lens. "
            "Smoke rises, then a flame. Fire. Then they keep it alive, all night, in shifts. The end.")
    out, t = [], 0.1
    for w in text.split():
        out.append({"w": w, "s": round(t, 3), "e": round(t + 0.32, 3)})
        t += 0.32 + (0.5 if w[-1] in ".?!" else 0.3 if w[-1] == "," else 0.05)
    return out


def _cut(words: list[dict], word: str) -> float:
    i = next(k for k, w in enumerate(words) if w["w"] == word)
    return round((words[i]["e"] + words[i + 1]["s"]) / 2, 3)


def _good() -> tuple[list[dict], list[dict]]:
    w = _words()
    clause = R.mood_clause("tension")
    kinds = ["C", "C", "B", "C", "B"]
    end = w[-1]["e"] + 0.8
    plan = [{"type": k, "start": 0.0, "end": 0.0, "planned": R.DURATIONS[k][0] + 0.4} for k in kinds]
    b = [0.0] + R.solve_cuts(plan, w, end) + [end]
    motions = {"A": {"kind": "pan", "z0": 1.06, "z1": 1.06, "dx": 0.03}, "B": {"kind": "push", "z0": 1.0, "z1": 1.06},
               "C": {"kind": "static", "z0": 1.0, "z1": 1.0}}
    shots = []
    for i, k in enumerate(kinds):
        s = {"id": f"s{i}", "beat": "fire", "phase": "day1", "type": k, "emotion": "tension", "start": b[i],
             "end": b[i + 1], "sentences": [0], "motion": dict(motions[k]), "transition": "cut",
             "palette": ["ochre"], "prompt": f"extreme close-up of a lens, no faces, {clause}, painted"}
        if k == "B":
            s["face"] = "caricature:einstein"
        shots.append(s)
    shots[0]["sound_at"] = 0.0
    shots[-1]["tail"] = True
    return shots, w


def _fails(shots, words, look=LOOK):
    return [f for f in R.check_shots(shots, words, look) if f["severity"] == "FAIL"]


def test_the_good_edit_passes():
    shots, words = _good()
    for s in shots:
        assert R.DURATIONS[s["type"]][0] <= s["end"] - s["start"] <= R.DURATIONS[s["type"]][0] + 1.0, s
    assert _fails(shots, words) == []


@pytest.mark.parametrize("rule, mutate", [
    ("UR-01", lambda s, w: s[0].update(type="B", face="faceless")),
    ("UR-11", lambda s, w: s[1].update(end=s[1]["start"] + 2.0) or s[2].update(start=s[1]["start"] + 2.0)),
    ("UR-02", lambda s, w: s[2].update(end=s[3]["end"]) or s.pop(3)),
    ("UR-12", lambda s, w: s[0].update(end=w[1]["s"] + 0.05) or s[1].update(start=w[1]["s"] + 0.05)),
    ("UR-13", lambda s, w: s[2]["motion"].update(z1=1.2)),
    ("UR-13", lambda s, w: s[1].update(motion={"kind": "push", "z0": 1.0, "z1": 1.05})),
    ("UR-13", lambda s, w: s[2]["motion"].update(shake=2)),
    ("UR-14", lambda s, w: s[2].update(transition="dissolve", transition_seconds=1.0)),
    ("UR-09", lambda s, w: s[3].update(emotion="nostalgia")),
    ("UR-09", lambda s, w: s[3].update(prompt="a medium shot of a camp, painted")),
    ("UR-08", lambda s, w: s[3].update(palette=["neon pink"])),
    ("UR-06", lambda s, w: s[2].update(prompt=s[2]["prompt"].replace("a lens", "Einstein's smiling face"))),
    ("UR-06", lambda s, w: s[2].update(prompt=s[2]["prompt"].replace("a lens", "John Snow at a well"))),
    ("UR-06", lambda s, w: s[2].update(face="caricature:wallace")),
    ("UR-06", lambda s, w: s[2].pop("face")),
    ("UR-07", lambda s, w: s[2].update(prompt=s[2]["prompt"].replace(", painted", ", hyper-realistic photo, painted"))),
    ("UR-07", lambda s, w: s[2].update(prompt=s[2]["prompt"] + ", 8k")),
    ("UR-05", lambda s, w: [x.update(type="C", motion={"kind": "static", "z0": 1.0, "z1": 1.0}) for x in s[:3]]),
])
def test_each_rule_catches_its_break(rule, mutate):
    shots, words = _good()
    shots = copy.deepcopy(shots)
    mutate(shots, words)
    assert rule in {f["rule"] for f in _fails(shots, words)}


def test_the_hook_needs_a_question_in_five_seconds():
    shots, words = _good()
    words = [dict(w, w=w["w"].replace("?", ".")) for w in words]
    assert "UR-01" in {f["rule"] for f in _fails(shots, words)}


def test_a_negated_face_is_not_a_face():
    shots, words = _good()
    shots[2]["prompt"] = shots[2]["prompt"].replace("no faces", "faces hidden, no faces")
    assert not [f for f in _fails(shots, words) if f["rule"] == "UR-06"]


def test_pauses_and_cut_placement():
    words = _words()
    pauses = R.pauses_from_words(words)
    assert all(b - a >= 2 * R.EDGE for a, b, _ in pauses)
    assert R.cut_ok(_cut(words, "fire?"), words)
    assert not R.cut_ok(words[2]["s"] + 0.1, words)  # inside a word
    assert not R.cut_ok((words[0]["e"] + words[1]["s"]) / 2, words)  # between words with no punctuation


def test_solve_cuts_places_every_cut_in_a_pause_and_reports_impossible_edits():
    words = _words()
    end = words[-1]["e"] + 0.8
    plan = [{"type": t, "planned": p, "start": 0, "end": 0} for t, p in
            [("C", 3.0), ("C", 3.0), ("B", 4.0), ("C", 3.0), ("B", 4.0)]]
    cuts = R.solve_cuts(plan, words, end)
    assert cuts is not None and len(cuts) == len(plan) - 1
    assert all(R.cut_ok(c, words) for c in cuts)
    shots = R.apply_cuts(plan, cuts, end)
    for s in shots:
        lo = R.DURATIONS[s["type"]][0]
        assert lo - 1e-6 <= s["end"] - s["start"] <= lo + R.FIRST_SLACK + 1e-6  # all inside the first 30 s
    assert R.solve_cuts([{"type": "A", "start": 0, "end": 1}], words, end) is None  # one A cannot hold it all


def test_compose_prompt_and_moods_share_one_table():
    moods = R.load_moods()
    assert {"discovery", "fear", "tension", "joy", "humour", "calm", "sorrow"} == set(moods)
    p = R.compose_prompt("a lens on grass.", "fear", LOOK)
    assert p.endswith(LOOK["style_suffix"]) and moods["fear"]["clause"] in p
    assert set(R.grade_for("joy")) == {"lift", "saturation", "warmth", "contrast", "vignette"}


def _load(path: Path, key: str):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data[key] if isinstance(data, dict) and key in data else data


def test_fire_animatic_v3_regression():
    """The measured v3 edit (docs/UNIVERSAL_RULE_BASE.md, the review of the reference video)."""
    shots, words, look = _load(V3 / "shots.json", "shots"), _load(V3 / "words.json", "words"), _load(V3 / "look.json", "x")
    found = R.check_shots(shots, words, look)
    fails = [f for f in found if f["severity"] == "FAIL"]
    by = lambda rule: sorted({f["shot"] for f in fails if f["rule"] == rule})  # noqa: E731
    assert by("UR-01") == ["v3-01"]
    assert by("UR-11") == ["v3-01", "v3-03", "v3-06", "v3-07", "v3-08", "v3-09", "v3-10", "v3-11"]
    assert by("UR-12") == ["v3-02", "v3-03", "v3-04", "v3-05", "v3-06", "v3-07", "v3-08", "v3-09", "v3-11"]
    assert by("UR-13") == ["v3-01", "v3-03", "v3-05", "v3-06", "v3-07", "v3-08", "v3-10", "v3-11"]
    assert len(by("UR-14")) == 11  # ten 0.12 s dissolves without a time jump, plus the share
    assert len(by("UR-09")) == 11 and len(by("UR-08")) == 11  # no emotion, no palette declared
    assert not by("UR-06") and not by("UR-05") and not by("UR-03")


def test_the_committed_day1_edit_passes():
    shots = _load(DAY1 / "shots.json", "shots")
    words = _load(DAY1 / "words.json", "words")
    look = json.loads((ROOT / "examples/stone_age/look.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "assets/audio/library/manifest.json").read_text(encoding="utf-8"))
    found = R.check_shots(shots, words, look, sound_ids={x["id"] for x in manifest["items"]})
    assert [f for f in found if f["severity"] == "FAIL"] == []
    assert shots[0]["start"] == 0.0 and abs(shots[-1]["end"] - _load(DAY1 / "words.json", "duration")) < 1e-6
    cuts = [s["start"] for s in shots[1:]]
    assert all(R.cut_ok(c, words) for c in cuts)
    assert sum(s["transition"] == "dissolve" for s in shots) == 0
