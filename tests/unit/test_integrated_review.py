"""The integrated production-coherence review (D-60): editorial_review/2 on a production_script/3.

The gap this closes (audit 2026-10-20): every deterministic validator judges one layer against its own rules, and the
editorial_review/1 contract carried only 13 broad scores, so a /3 script could pass every check while its combined
dialogue, visual, performance and audio plan undermined the story it tells. The fixtures below each pass `check_script`
with 0 FAIL yet carry a deliberate cross-layer defect; the /2 review contract is what carries (and blocks on) the
finding. The gate stays deterministic: it validates the review's coverage, honesty labels and findings, and the
narrative judgement itself stays with the independent critic — so a clean review of an unusual but valid story passes.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from explainer_engine.production import compile as C
from explainer_engine.production import editorial_gate as EG
from explainer_engine.production import validate as V

ROOT = Path(__file__).resolve().parents[2]
WORLD = json.loads((ROOT / "examples" / "stone_age" / "day1_v6" / "world_spec.json").read_text())


def scene_mini() -> dict:
    """A compact, fully valid production_script/3: three segments, one played scene, invented heroes, drama layer.
    `test_the_fixture_passes_every_deterministic_validator` pins that it compiles to 0 FAIL."""
    return {
        "schema": "production_script/3",
        "episode": {
            "id": "coherence_fixture", "title": "The Frozen Valley", "fps": 30, "grade": "prehistory",
            "scenario": {"file": "scenario.md", "approved_by": "creator", "approved_at": "2026-10-20",
                         "sha256": "0" * 64},
            "distinct": {"premise": "an invented valley must cross a frozen pass before the food runs out",
                         "question": "Does the valley cross the pass in time?",
                         "outcome": "they cross by burning the carts for warmth",
                         "mechanism": "heat budget of a night march"},
        },
        "voice": {"provider": "elevenlabs", "model": "eleven_v4", "voice_id": "x", "name": "X",
                  "style": "soft, deep, calm and warm storyteller", "pace_wpm": [140, 158]},
        "world": WORLD,
        "look": {"default_engine": "gemini"},
        "drama": {
            "premise": "A starving valley must cross a frozen pass in one night.",
            "question": "Does the valley cross the pass before the cold wins?",
            "promise": "A night march where every degree of warmth is paid for.",
            "needs": ["curiosity", "stakes", "competence"],
            "arcs": {"mara": {"want": "get everyone across tonight", "flaw": "trusts her own count too much"},
                     "oren": {"want": "wait for a thaw", "flaw": "fears open ice more than hunger"}},
            "loops": [{"id": "L01", "question": "Does the valley cross in time?"},
                      {"id": "L02", "question": "Is Mara's count of the food right?"}],
            "setups": [],
            "ending": {"kind": "callback", "note": "template A"},
        },
        "cast": {
            "mara": {"names": ["mara"], "card": "an invented young scout, wind-burned, braided hair",
                     "voice": {"style": "quick, bright, clipped scout's voice", "voice_id": "v_mara",
                               "traits": {"gender": "female", "age": "young", "temperament": ["driven", "impatient"],
                                          "energy": "high", "origin": "the valley highlands", "role": "hero"}},
                     "speech": {"basis": "personality",
                                "style": "short clipped sentences, counts things out loud, no hedging",
                                "words": ["count it", "by first light", "the pass"], "avoid": ["perhaps"]},
                     "face_sheet": {"id": "mara_faces_v1", "ref": "pair",
                                    "set": ["neutral", "joyful", "sad", "scared", "angry", "surprised", "curious",
                                            "confused", "smug", "determined"]},
                     "reference": {"collage": "mara_collage.jpg", "tile": 2, "picture": "pair",
                                   "approved_by": "creator", "approved_at": "2026-10-20"}},
            "oren": {"names": ["oren"], "card": "an invented old elder, heavy coat, carved staff",
                     "voice": {"style": "slow, low, gravelled elder's voice", "voice_id": "v_oren",
                               "traits": {"gender": "male", "age": "old", "temperament": ["wary", "deliberate"],
                                          "energy": "low", "origin": "the valley floor", "role": "mentor"}},
                     "speech": {"basis": "personality",
                                "style": "slow weighed sentences, answers with questions, old sayings",
                                "words": ["the ice remembers", "slow is alive", "listen"], "avoid": ["hurry"]},
                     "face_sheet": {"id": "oren_faces_v1", "ref": "pair",
                                    "set": ["neutral", "joyful", "sad", "scared", "angry", "surprised", "curious",
                                            "confused", "doubtful", "determined"]},
                     "reference": {"collage": "oren_collage.jpg", "tile": 1, "picture": "pair",
                                   "approved_by": "creator", "approved_at": "2026-10-20"}},
        },
        "story": {"events": [{"thing": "lantern", "at": "At the top"}], "forbidden_props": []},
        "library": {
            "valley": {"file": "valley.png", "heroes": [], "shows": []},
            "pass": {"file": "pass.png", "heroes": [], "shows": []},
            "pass_lit": {"file": "pass_lit.png", "heroes": [], "shows": ["lantern"]},
            "pair": {"file": "pair.png", "heroes": ["mara", "oren"], "shows": [],
                     "speakers": {"mara": [0.3, 0.4], "oren": [0.7, 0.4]}},
        },
        "music": [{"track": "tone", "from": "<start>", "to": None, "gain_db": -20}],
        "editorial": {
            "version": 1,
            "sources": [{"id": "S1", "url": "https://example.com/heat", "title": "Cold-weather march physiology",
                         "publisher": "Example Press", "published_at": "2026-01-01", "accessed_at": "2026-10-20",
                         "grade": "A", "passage": "A loaded march in deep cold loses heat faster than rest."}],
            "claims": [{"id": "C1", "text": "A loaded night march in deep cold drains body heat faster than resting.",
                        "type": "fact", "source_ids": ["S1"], "confidence": "verified", "uncertainty": ""}],
        },
        "segments": [
            {"id": "S01", "beat": "dusk", "light_beat": 5,
             "drama": {"function": "hook", "turn": "start", "stakes": "the food ends before any thaw",
                       "shift": "fed -> starving", "opens": ["L01"], "need": "curiosity", "claim_share": "fact"},
             "lines": [
                 {"text": "Could the valley cross the pass tonight?", "kind": "speculation", "claims": ["C1"],
                  "visual_beats": [{"at": "the pass", "kind": "label", "why": "names the pass as the obstacle",
                                    "text": "THE PASS"}]},
                 {"text": "A night march in that cold drains a body faster than resting, and the food is already gone.",
                  "kind": "fact", "claims": ["C1"],
                  "visual_beats": [{"at": "already gone", "kind": "symbol", "why": "the food already gone lands",
                                    "symbol": "cross"}]},
             ],
             "shots": [
                 {"at": "Could the", "type": "A", "picture": "valley",
                  "motion": {"kind": "push", "z0": 1.0, "z1": 1.05}, "purpose": "open on the whole valley at dusk"},
                 {"at": "A night march", "type": "A", "picture": "pass",
                  "motion": {"kind": "push", "z0": 1.0, "z1": 1.04}, "purpose": "show the obstacle"},
             ],
             "audio": {"beds": [{"at": "Could the", "sound": "wind", "purpose": "the cold as a presence"}]}},
            {"id": "S02", "beat": "the argument", "light_beat": 6,
             "drama": {"function": "midpoint", "turn": "but", "stakes": "split the valley and both halves die",
                       "shift": "united -> split", "opens": ["L02"], "closes": [], "need": "stakes",
                       "claim_share": "invented"},
             "scene": {"place": "the elder's hut, night", "present": ["mara", "oren"], "pov": "mara",
                       "why_now": "the last store was counted at dusk",
                       "want": "march everyone out tonight",
                       "obstacle_want": "keep everyone off the ice until a thaw",
                       "value": "trust", "open_charge": "+", "close_charge": "-",
                       "turn": "Oren asks for the count and Mara's number is short",
                       "exit": "interrupted", "surface_topic": "the food count",
                       "real_subject": "whose judgement the valley follows"},
             "lines": [
                 {"text": "The store was counted at dusk, and the elder's door stayed open.", "kind": "transition",
                  "visual_beats": [{"at": "door stayed open", "kind": "prop",
                                    "why": "the door stayed open for the fight", "thing": "door"}]},
                 {"text": "Count it with me. By first light we march.", "kind": "transition", "speaker": "mara",
                  "to": "oren", "intent": "press",
                  "visual_beats": [{"at": "we march", "kind": "expression", "why": "Oren hears we march as an order",
                                    "expression": "doubtful", "who": "oren"}]},
                 {"text": "Slow is alive, girl. The ice remembers the hasty.", "kind": "transition", "speaker": "oren",
                  "to": "mara", "intent": "deflect",
                  "visual_beats": [{"at": "ice remembers", "kind": "expression",
                                    "why": "the ice remembers lands on Mara", "expression": "determined",
                                    "who": "mara"}]},
                 {"text": "Then count what is left.", "kind": "transition", "speaker": "mara", "to": "oren",
                  "intent": "press",
                  "visual_beats": [{"at": "count what", "kind": "expression",
                                    "why": "count what is left challenges Oren", "expression": "surprised",
                                    "who": "oren"}]},
                 {"text": "Four days. You counted five.", "kind": "transition", "speaker": "oren", "to": "mara",
                  "intent": "reveal",
                  "visual_beats": [{"at": "counted five", "kind": "expression", "why": "counted five breaks on Mara",
                                    "expression": "scared", "who": "mara"}]},
                 {"text": "She left without the lantern.", "kind": "transition",
                  "visual_beats": [{"at": "without the lantern", "kind": "prop",
                                    "why": "she left without the lantern", "thing": "lantern"}]},
             ],
             "shots": [
                 {"at": "The store", "type": "B", "picture": "pair",
                  "motion": {"kind": "push", "z0": 1.0, "z1": 1.03}, "purpose": "two-shot: the scene's ground"},
                 {"at": "Four days", "type": "B", "picture": "pair", "reuse": "reframe",
                  "motion": {"kind": "push", "z0": 1.03, "z1": 1.08}, "purpose": "the reveal lands on the faces"},
             ],
             "audio": {"beds": [{"at": "The store", "sound": "wind", "purpose": "the cold waits outside"}]}},
            {"id": "S03", "beat": "the march", "light_beat": 7,
             "drama": {"function": "resolution", "turn": "therefore", "stakes": "the last of the warmth",
                       "shift": "split -> crossing", "closes": ["L01", "L02"], "need": "competence",
                       "claim_share": "invented"},
             "lines": [
                 {"text": "Therefore they march, and burn the carts for warmth.", "kind": "analysis", "claims": ["C1"],
                  "visual_beats": [{"at": "burn the carts", "kind": "symbol", "why": "burn the carts is the price",
                                    "symbol": "exclaim"}]},
                 {"text": "At the top of the pass, Mara lifts the lantern.", "kind": "transition",
                  "visual_beats": [{"at": "lifts the lantern", "kind": "highlight",
                                    "why": "lifts the lantern pays the opening", "pos": [0.5, 0.4]}]},
             ],
             "shots": [
                 {"at": "Therefore they", "type": "A", "picture": "valley", "reuse": "reframe",
                  "motion": {"kind": "pull", "z0": 1.06, "z1": 1.0}, "purpose": "the valley empties"},
                 {"at": "At the top", "type": "A", "picture": "pass_lit",
                  "motion": {"kind": "push", "z0": 1.0, "z1": 1.05}, "reveal": "lantern",
                  "purpose": "the lantern answers the opening"},
             ],
             "audio": {"beds": [{"at": "Therefore they", "sound": "wind", "purpose": "the cold stays honest"}],
                       "sfx": [{"at": "lifts the lantern", "sound": "chime", "gain_db": -22, "max_s": 0.6,
                                "purpose": "the callback lands"}]}},
        ],
    }


STORY_PAGE = "# ისტორია\n\n" + "მარა ხეობაში ლამპარს ეძებს და პოულობს. " * 30 + "\n\n## რატომ მუშაობს\n\nმიზეზი და შედეგი.\n"


def no_fails(doc: dict) -> list[dict]:
    found = V.check_script(C.compile_doc(copy.deepcopy(doc)))
    return [f for f in found if f["severity"] == "FAIL"]


def review2(script: Path, findings=(), layers=None, notes=(), schema="editorial_review/2") -> dict:
    scores = {name: {"score": 4, "evidence": f"Concrete script evidence for {name} is recorded here."}
              for name in EG.CRITERIA}
    base_layers = {
        "story": {"status": "inspected", "basis": "data",
                  "evidence": "read S01..S03 against drama: question, loops L01/L02, callback ending"},
        "entrances": {"status": "inspected", "basis": "data",
                      "evidence": "mara and oren enter inside the S02 scene mid-action, grounded by the narrator"},
        "dialogue": {"status": "inspected", "basis": "data",
                     "evidence": "every S02 line against the speech bibles, wants and the preceding turn"},
        "visual": {"status": "inspected", "basis": "instructions",
                   "evidence": "shots of S01..S03 and the beats against each line; pictures exist only as prompts"},
        "performance": {"status": "inspected", "basis": "instructions",
                        "evidence": "intents and expression beats of S02 against the scene's charge"},
        "audio": {"status": "inspected", "basis": "instructions",
                  "evidence": "the wind bed and the S03 chime against the story events they claim"},
        "timing": {"status": "inspected", "basis": "estimate",
                   "evidence": "the estimated read: the S02 reveal and the S03 callback both get their beat"},
    }
    integ = {"layers": layers if layers is not None else base_layers,
             "findings": list(findings), "notes": list(notes)}
    return {"schema": schema, "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            "reviewer_role": "independent_critic", "independent": True, "scores": scores,
            "critical_blockers": [], "required_revisions": [], "integrated": integ,
            "story_page": "story_page.md"}


def ir_finding(**kw) -> dict:
    base = {"id": "IR-01", "layers": ["visual", "audio"], "severity": "FAIL",
            "refs": ["S02 line 5", "S02 shot 2"],
            "expected": "the short count breaks Mara on screen and the dread holds",
            "instructed": "the edit cuts to the wide valley and a bright chime stings the count",
            "conflict": "the picture and sound celebrate at the moment the story breaks its hero",
            "consequence": "the viewer reads the midpoint reveal as a gag and the turn is lost",
            "confidence": "high", "basis": "instructions",
            "fix": "hold the pair reframe through the reveal and drop the chime",
            "owner": "editor"}
    base.update(kw)
    return base


def write_pair(tmp_path: Path, doc: dict, review=None, **review_kw) -> tuple[Path, Path]:
    script = tmp_path / "production_script.json"
    script.write_text(json.dumps(doc), encoding="utf-8")
    rev = tmp_path / "editorial_review.json"
    rev.write_text(json.dumps(review if review is not None else review2(script, **review_kw)), encoding="utf-8")
    (tmp_path / "story_page.md").write_text(STORY_PAGE, encoding="utf-8")
    return script, rev


def gate_rules(script: Path, rev: Path, sev="FAIL") -> set[str]:
    return {f["rule"] for f in EG.check(script, rev) if f["severity"] == sev}


# --- the gap is real: these scripts pass every deterministic validator ------------------------------------------------

def test_the_fixture_passes_every_deterministic_validator():
    assert no_fails(scene_mini()) == []


def undermined_reveal() -> dict:
    """The S02 reveal: the edit cuts away to the wide valley and a bright chime stings the count. Every field is
    individually legal; only the combined plan contradicts the scene's turn."""
    d = scene_mini()
    seg = d["segments"][1]
    seg["shots"][1] = {"at": "Four days", "type": "A", "picture": "valley", "reuse": "reframe",
                       "motion": {"kind": "pull", "z0": 1.05, "z1": 1.0}, "purpose": "breathe before the march"}
    seg["audio"]["sfx"] = [{"at": "Four days", "sound": "chime", "gain_db": -20, "max_s": 0.6,
                            "purpose": "a bright sting on the count"}]
    return d


DEFECTS = {
    # dialogue disconnected from the event it follows (structurally valid turn-taking)
    "disconnected_dialogue": (
        lambda d: d["segments"][1]["lines"].__setitem__(2, dict(
            d["segments"][1]["lines"][2], text="The west ridge grows good barley, listen.", intent="banter",
            visual_beats=[{"at": "good barley", "kind": "expression", "why": "good barley puzzles Mara",
                           "expression": "confused", "who": "mara"}])),
        ir_finding(id="IR-D1", layers=["dialogue"], refs=["S02 line 3"],
                   expected="Oren answers the order to march, deflecting toward the ice",
                   instructed="Oren replies about barley on the west ridge",
                   conflict="the line follows from nothing Mara just said and drops the scene's want",
                   consequence="the exchange reads as two people in different conversations",
                   basis="data", fix="answer the march order sideways, staying on the ice and the count",
                   owner="writer")),
    # the introduction contradicts the scene context
    "entrance_contradiction": (
        lambda d: d["segments"][1].__setitem__("scene", dict(d["segments"][1]["scene"],
                                                             place="out on the open ice, noon")),
        ir_finding(id="IR-D2", layers=["entrances", "visual"], refs=["S02 line 1", "S02"],
                   expected="the narrator seats the scene at the elder's open door at night",
                   instructed="the scene header plays the same exchange on open ice at noon",
                   conflict="the spoken introduction and the scene header place the meeting in two places",
                   consequence="the viewer is told a door stayed open while watching open ice",
                   basis="data", fix="return scene.place to the elder's hut or reword the narrator's line",
                   owner="architect")),
    # the visual and sound plan undermines the dramatic reveal
    "undermined_reveal": (
        lambda d: d.update(undermined_reveal()),
        ir_finding()),
    # dialogue against the established speech bible (too few lines for speech.py's deterministic check)
    "speech_bible_mismatch": (
        lambda d: d["segments"][1]["lines"].__setitem__(2, dict(
            d["segments"][1]["lines"][2], text="Count it. March by first light. Go now.",
            visual_beats=[{"at": "Go now", "kind": "expression", "why": "go now startles Mara",
                           "expression": "surprised", "who": "mara"}])),
        ir_finding(id="IR-D4", layers=["dialogue"], refs=["S02 line 3", "oren"],
                   expected="oren speaks in slow weighed sentences and answers with questions",
                   instructed="oren fires clipped imperatives in Mara's own register",
                   conflict="the elder's line is written in the scout's voice, not his speech bible",
                   consequence="the two voices blur and the argument loses its sides",
                   basis="data", fix="reword the line in oren's register (slow, a question, an old saying)",
                   owner="writer")),
    # a sound instruction against the emotional event
    "sound_against_event": (
        lambda d: d["segments"][1].setdefault("audio", {}).__setitem__(
            "sfx", [{"at": "Four days", "sound": "chime", "gain_db": -20, "max_s": 0.6,
                     "purpose": "a bright sting on the count"}]),
        ir_finding(id="IR-D5", layers=["audio"], refs=["S02 line 5", "chime at Four days"],
                   expected="the short count lands as dread inside the quiet wind bed",
                   instructed="a bright chime stings the exact words that break Mara",
                   conflict="the planned sound scores the reveal as a win against its meaning",
                   consequence="the emotional reading of the midpoint flips for the viewer",
                   basis="instructions", fix="drop the chime or move it to the S03 callback it fits",
                   owner="editor")),
    # individually valid segments whose combined sequence is incoherent
    "incoherent_sequence": (
        lambda d: d["segments"][2]["lines"].__setitem__(0, dict(
            d["segments"][2]["lines"][0], text="Therefore they wait for the thaw, and spring is kind.",
            kind="transition", claims=[],
            visual_beats=[{"at": "wait for the thaw", "kind": "symbol", "why": "wait for the thaw is the choice",
                           "symbol": "check"}])),
        ir_finding(id="IR-D6", layers=["story"], refs=["S03 line 1", "S03 line 2", "S02"],
                   expected="the short count forces the night march the ending pays off",
                   instructed="S03 says they wait for a thaw yet Mara still lifts the lantern at the top",
                   conflict="the resolution contradicts the decision the midpoint forced",
                   consequence="the ending answers a story that was never told",
                   basis="data", fix="resolve the march the count forced, or replant the ending",
                   owner="architect")),
    # the edit cuts away before the reaction lands
    "cut_before_reaction": (
        lambda d: d["segments"][1]["shots"].__setitem__(1, {"at": "She left", "type": "A", "picture": "valley",
                                                            "reuse": "reframe",
                                                            "motion": {"kind": "pull", "z0": 1.05, "z1": 1.0},
                                                            "purpose": "the valley waits for the verdict"}),
        ir_finding(id="IR-D7", layers=["visual", "timing"], refs=["S02 line 5", "S02 line 6"],
                   expected="Mara's face carries the broken count before the scene releases",
                   instructed="the edit leaves the two-shot for the wide valley one word after the reveal",
                   conflict="the cut arrives before the scared beat on Mara has time to land",
                   consequence="the viewer never sees the reveal cost anyone anything",
                   basis="estimate", fix="hold the pair through line 5 and cut on the narrator's exit line",
                   owner="editor")),
}


@pytest.mark.parametrize("name", sorted(DEFECTS))
def test_defective_scripts_pass_the_validators_and_the_integrated_finding_blocks(name, tmp_path):
    mutate, found = DEFECTS[name]
    d = scene_mini()
    mutate(d)
    assert no_fails(d) == [], f"{name}: the defect must be invisible to the deterministic validators"
    script, rev = write_pair(tmp_path, d, findings=[found])
    rows = EG.check(script, rev)
    blocked = [f for f in rows if f["rule"] == "EG-22" and f["severity"] == "FAIL"]
    assert blocked, rows
    assert found["owner"] in blocked[0]["detail"]  # the finding routes to the stage that owns the fix
    assert not [f for f in rows if f["rule"] == "EG-21"], "the finding itself must be well-formed"


# --- no false positives: valid creative choices pass -------------------------------------------------------------------

def test_a_clean_script_with_a_clean_integrated_review_passes(tmp_path):
    script, rev = write_pair(tmp_path, scene_mini())
    assert EG.check(script, rev) == []


def test_a_deliberate_rapid_entrance_is_not_rejected(tmp_path):
    d = scene_mini()
    d["cast"]["runner"] = {
        "names": ["runner"], "card": "an invented breathless young runner, snow on his coat",
        "voice": {"style": "breathless, cracking young voice", "voice_id": "v_runner",
                  "traits": {"gender": "male", "age": "young", "temperament": ["urgent"], "energy": "high",
                             "origin": "the south road", "role": "everyman"}},
        "speech": {"basis": "personality", "style": "gasped fragments, one fact at a time, no greetings",
                   "words": ["the south road", "broke", "now"], "avoid": ["calm"]}}
    seg = d["segments"][1]
    seg["scene"]["present"] = ["mara", "oren", "runner"]
    seg["lines"].insert(5, {"text": "The ice broke on the south road, now!", "kind": "transition",
                            "speaker": "runner", "to": "room", "intent": "reveal",
                            "visual_beats": [{"at": "ice broke", "kind": "expression",
                                              "why": "the ice broke lands on Oren", "expression": "scared",
                                              "who": "oren"}]})
    assert no_fails(d) == []
    script, rev = write_pair(tmp_path, d, notes=["The runner's abrupt entrance is deliberate and earns the interrupt."])
    assert EG.check(script, rev) == []  # a note never blocks; speed alone is not a finding


def test_an_unconventional_but_coherent_story_passes(tmp_path):
    d = scene_mini()  # ends on a twist instead of a resolution: valid, not the template default
    d["segments"][2]["drama"]["function"] = "twist"
    d["drama"]["ending"] = {"kind": "open_question", "note": "template C, reveal ladder"}
    assert no_fails(d) == []
    script, rev = write_pair(tmp_path, d)
    assert EG.check(script, rev) == []


def test_a_review_finding_for_the_creator_does_not_block(tmp_path):
    script, rev = write_pair(tmp_path, scene_mini(),
                             findings=[ir_finding(id="IR-R1", severity="REVIEW",
                                                  conflict="the chime on the callback may be one sting too sweet")])
    rows = EG.check(script, rev)
    assert not [f for f in rows if f["severity"] == "FAIL"]
    assert [f for f in rows if f["rule"] == "EG-22" and f["severity"] == "REVIEW"]


# --- the contract: coverage, honesty, concreteness, identity ----------------------------------------------------------

def test_a_v3_script_requires_the_integrated_review(tmp_path):
    d = scene_mini()
    script = tmp_path / "production_script.json"
    script.write_text(json.dumps(d), encoding="utf-8")
    rev = tmp_path / "editorial_review.json"
    v1 = review2(script, schema="editorial_review/1")
    del v1["integrated"]
    rev.write_text(json.dumps(v1), encoding="utf-8")
    assert "EG-19" in gate_rules(script, rev)


def test_legacy_scripts_keep_the_v1_contract(tmp_path):
    from test_editorial_gate import valid_doc, valid_review
    script = tmp_path / "production_script.json"
    script.write_text(json.dumps(valid_doc()), encoding="utf-8")
    rev = tmp_path / "editorial_review.json"
    rev.write_text(json.dumps(valid_review(script)), encoding="utf-8")
    assert EG.check(script, rev) == []  # a /1 review still passes on a legacy script
    rev.write_text(json.dumps(review2(script)), encoding="utf-8")
    assert EG.check(script, rev) == []  # and a /2 review is accepted there too


def test_missing_layers_evidence_or_basis_fail(tmp_path):
    d = scene_mini()
    script = tmp_path / "production_script.json"
    script.write_text(json.dumps(d), encoding="utf-8")
    rev = tmp_path / "editorial_review.json"
    r = review2(script)
    del r["integrated"]["layers"]["audio"]
    rev.write_text(json.dumps(r), encoding="utf-8")
    assert "EG-20" in gate_rules(script, rev)
    r = review2(script)
    r["integrated"]["layers"]["visual"]["evidence"] = "fine"
    rev.write_text(json.dumps(r), encoding="utf-8")
    assert "EG-20" in gate_rules(script, rev)
    r = review2(script)
    r["integrated"]["layers"]["timing"]["basis"] = "heard it"  # never claim media that does not exist
    rev.write_text(json.dumps(r), encoding="utf-8")
    assert "EG-20" in gate_rules(script, rev)
    r = review2(script)
    r["integrated"]["layers"]["story"] = {"status": "not_applicable", "reason": "there is always a story layer"}
    rev.write_text(json.dumps(r), encoding="utf-8")
    assert "EG-20" in gate_rules(script, rev)


def test_a_vague_or_unanchored_finding_is_rejected(tmp_path):
    d = scene_mini()
    script, rev = write_pair(tmp_path, d, findings=[ir_finding(refs=["the pacing in general"])])
    assert "EG-21" in gate_rules(script, rev)  # refs name nothing of this script
    script, rev = write_pair(tmp_path, d, findings=[ir_finding(fix="improve")])
    assert "EG-21" in gate_rules(script, rev)  # generic advice is not a correction
    script, rev = write_pair(tmp_path, d, findings=[ir_finding(owner="somebody")])
    assert "EG-21" in gate_rules(script, rev)
    script, rev = write_pair(tmp_path, d, findings=[ir_finding(basis="viewed")])
    assert "EG-21" in gate_rules(script, rev)  # claimed evidence kinds are a closed set
    script, rev = write_pair(tmp_path, d, findings=[ir_finding(severity="NOTE")])
    assert "EG-21" in gate_rules(script, rev)


def test_a_changed_script_invalidates_the_integrated_review(tmp_path):
    d = scene_mini()
    script, rev = write_pair(tmp_path, d)
    assert EG.check(script, rev) == []
    d["segments"][2]["lines"][1]["text"] = "At the top of the pass, Mara drops the lantern."
    script.write_text(json.dumps(d), encoding="utf-8")
    assert "EG-13" in gate_rules(script, rev)  # stale review: re-review the exact bytes


def test_a_failed_or_malformed_review_never_silently_passes(tmp_path):
    d = scene_mini()
    script = tmp_path / "production_script.json"
    script.write_text(json.dumps(d), encoding="utf-8")
    missing = tmp_path / "editorial_review.json"
    assert "EG-12" in gate_rules(script, missing)  # no review at all
    missing.write_text("{ not json", encoding="utf-8")
    assert "EG-12" in gate_rules(script, missing)  # a crashed reviewer's half-written file
    r = review2(script)
    r["integrated"] = "all good"
    missing.write_text(json.dumps(r), encoding="utf-8")
    assert "EG-19" in gate_rules(script, missing)  # a /2 review without its integrated object


def test_a_correction_that_breaks_another_layer_is_caught_by_the_re_review(tmp_path):
    d = undermined_reveal()
    script, rev = write_pair(tmp_path, d, findings=[ir_finding()])
    assert "EG-22" in gate_rules(script, rev)  # round 1: blocked
    # the "fix" restores the reveal shot but moves the chime onto the S03 quiet callback's planned stillness
    d["segments"][1]["shots"][1] = scene_mini()["segments"][1]["shots"][1]
    d["segments"][1]["audio"].pop("sfx", None)
    d["segments"][2]["audio"]["sfx"].insert(0, {"at": "Therefore they", "sound": "chime", "gain_db": -18,
                                                "max_s": 0.6, "purpose": "carry the sting into the march"})
    assert no_fails(d) == []
    script.write_text(json.dumps(d), encoding="utf-8")
    assert "EG-13" in gate_rules(script, rev)  # the old approval is stale the moment the fix lands
    rev.write_text(json.dumps(review2(script, findings=[ir_finding(
        id="IR-02", layers=["audio"], refs=["S03 line 1", "chime at Therefore they"],
        expected="the march opens on the wind alone, the cost still hanging",
        instructed="the moved chime now stings the march's first words",
        conflict="the correction moved the celebration from one wrong moment to another",
        consequence="the march reads as triumphant before anything is earned",
        basis="instructions", fix="cut the chime entirely; S03's own callback chime already lands",
        owner="editor")])), encoding="utf-8")
    assert "EG-22" in gate_rules(script, rev)  # round 2: the re-review catches the new contradiction


# --- wiring: the gate runs at the right stage and affects the production decision --------------------------------------

def test_production_gate_0_5_blocks_on_the_integrated_review(tmp_path):
    from explainer_engine import production_gate as PG
    d = C.compile_doc(scene_mini())
    (tmp_path / "production_script.json").write_text(json.dumps(d), encoding="utf-8")
    rows = {r["gate"]: r for r in PG.script_gates(tmp_path)}
    assert rows[0.5]["status"] == "BLOCKED"  # no review at all
    script = tmp_path / "production_script.json"
    (tmp_path / "editorial_review.json").write_text(json.dumps(review2(script, findings=[ir_finding()])),
                                                    encoding="utf-8")
    rows = {r["gate"]: r for r in PG.script_gates(tmp_path)}
    assert rows[0.5]["status"] == "BLOCKED"  # a blocking integrated finding stops production
    (tmp_path / "editorial_review.json").write_text(json.dumps(review2(script)), encoding="utf-8")
    rows = {r["gate"]: r for r in PG.script_gates(tmp_path)}
    assert rows[0.5]["status"] == "BLOCKED"  # the passing review still owes its Georgian story page (EG-23)
    (tmp_path / "story_page.md").write_text(STORY_PAGE, encoding="utf-8")
    rows = {r["gate"]: r for r in PG.script_gates(tmp_path)}
    assert rows[0.5]["status"] == "PASS"  # the clean review opens the gate
