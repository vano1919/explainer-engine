"""The creator's strict storytelling rules 1 and 2 (2026-10-20, D-61): show, don't tell (SC-12, BP-87) and full immersion
with no meta disclaimers (SC-11, BP-88, BP-71 at 0); and the recorded approval of the finished script before any paid
step (OR-17, PV-53)."""
import copy
import json

from test_production_script import mini
from test_scene_system import sc_rules, scene_doc

from explainer_engine.production import paint as PA
from explainer_engine.scripting import scene_lint as SC
from explainer_engine.scripting import script_approval as SA
from explainer_engine.standards import hook
from explainer_engine.standards import sourced_rules as SR


def narr(text: str) -> dict:
    d = scene_doc()
    d["cast"]["trump"] = {"names": ["Donald Trump"]}
    d["segments"][0]["lines"][0]["text"] = text
    return d


def test_the_two_rules_are_dated_house_fails_and_the_honesty_beat_is_zero():
    for bp in ("BP-87", "BP-88"):
        r = SR.rule(bp)
        assert (r["status"], r["severity"]) == ("house", "FAIL") and "2026-10-20" in r["decided"]
    assert SR.T("BP-71", "disclaimer_segments_max") == 0
    assert SR.check() == []


def test_meta_disclaimers_fail_anywhere_and_hedges_fail_in_narration():
    for text in ("This is a simulation, of course.", "As an AI, I can only imagine the rest.",
                 "In this hypothetical story, nobody knows them.", "None of this happened, but watch."):
        assert "SC-11" in sc_rules(narr(text), "FAIL"), text
    assert "SC-11" in sc_rules(narr("We cannot know for sure what he did next."), "FAIL")
    d = scene_doc()
    d["segments"][0]["lines"][2]["text"] = "This is just a simulation, Al."  # a hero breaking the frame too
    assert "SC-11" in sc_rules(d, "FAIL")
    d = scene_doc()
    d["segments"][0]["lines"][2]["text"] = "You can't know for sure. Count it again."  # doubt inside a scene is drama
    assert "SC-11" not in sc_rules(d)


def test_shorts_and_on_screen_text_are_inside_the_story_too():
    d = scene_doc()
    d["shorts"] = [{"id": "SH01", "lines": [{"text": "Hypothetically speaking, he goes broke by noon."}]}]
    assert "SC-11" in sc_rules(d, "FAIL")
    d = scene_doc()
    d["segments"][0]["lines"][1]["visual_beats"] = [{"at": "twice", "kind": "label", "label": "Cunning: 9/10"}]
    assert "SC-12" in sc_rules(d, "FAIL")
    d = scene_doc()
    d["segments"][0]["shots"] = [{"picture": "sc_capone"}]
    assert "SC-12" in sc_rules(d, "FAIL")  # a select-screen stat card


def test_the_narrator_never_tells_traits_ratings_or_biography():
    for text in ("Trump is charismatic.", "He's reckless.", "Donald Trump was famously ruthless.",
                 "She is a natural salesman.", "Musk takes risks nobody else would.", "He was born in Queens.",
                 "Risk appetite: 9 out of 10."):
        assert "SC-12" in sc_rules(narr(text), "FAIL"), text


def test_showing_lines_pass():
    for text in ("He spends forty of his hundred dollars on a rented jacket before he buys food.",
                 "Trump's bold jacket buys him ten minutes in the lobby.", "The deal was bold, and the manager knew it.",
                 "She invented a new offer on the spot.", "The lobby of a 5-star hotel goes quiet.",
                 "The pawn shop is open 24/7."):
        found = {f["rule"] for f in SC.lint(narr(text))}
        assert not found & {"SC-08", "SC-11", "SC-12"}, (text, found)
    d = scene_doc()
    d["segments"][0]["lines"][2]["text"] = "You're reckless. That's my money."  # a hero judging a hero is action
    assert "SC-12" not in sc_rules(d)


def test_earlier_schemas_keep_their_contract():
    d = narr("This is a simulation. Trump is charismatic.")
    d["schema"] = "production_script/2"
    assert SC.lint(d) == []
    assert SA.check(d) == []


def test_one_spoken_invention_disclaimer_is_now_a_fail():
    assert "SC-08" in sc_rules(narr("We invented this part of the night."), "FAIL")


def test_the_finished_script_needs_the_creators_recorded_approval(tmp_path):
    d = scene_doc()
    d["episode"] = {"id": "titans"}
    assert [f["rule"] for f in SA.check(d)] == ["PV-53"]
    path = tmp_path / "production_script.json"
    path.write_text(json.dumps(d), encoding="utf-8")
    rec = SA.approve(path, "vano", "2026-10-20")
    d = json.loads(path.read_text(encoding="utf-8"))
    assert d["episode"]["script_approval"] == rec and SA.check(d) == []
    d2 = copy.deepcopy(d)
    d2["segments"][0]["lines"][0]["tags"] = ["tense"]  # delivery may change after the yes
    d2["segments"][0]["shots"] = [{"picture": "p_bar"}]
    assert SA.check(d2) == []
    d2["segments"][0]["lines"][2]["text"] = "Four times. It's short."  # the words may not
    assert "changed after" in SA.check(d2)[0]["detail"]
    d3 = copy.deepcopy(d)
    d3["shorts"] = [{"id": "SH01", "lines": [{"text": "A new Short line."}]}]
    assert SA.check(d3), "a Short added after the yes goes back to the creator"
    d4 = copy.deepcopy(d)
    d4["segments"][0]["lines"][2]["voiced"] = False  # a heard line turned into a bubble (D-62) goes back too
    assert SA.check(d4)
    d4["segments"][0]["lines"][2]["voiced"] = True  # an explicit true hashes like before
    assert SA.check(d4) == []


def test_paid_pictures_wait_for_the_script_approval():
    d = mini()
    d["schema"] = "production_script/3"

    class Run:
        path = "run"

        def approved(self, *_):
            return True

    why = PA.preflight({"id": "p1", "hash": "h", "items": [], "provider": "gemini"}, d, [], Run())
    assert any(w.startswith("PV-53") for w in why)


def test_paid_audio_waits_for_the_script_approval(tmp_path, monkeypatch):
    from explainer_engine.standards import rulebook as R
    monkeypatch.setattr(R, "gate", lambda *a, **k: [])
    (tmp_path / ".claude").mkdir()
    ep = tmp_path / "ep"
    ep.mkdir()
    (ep / "episode_rules.json").write_text("{}", encoding="utf-8")
    d = scene_doc()
    d["episode"] = {"id": "titans"}
    script = ep / "production_script.json"
    script.write_text(json.dumps(d), encoding="utf-8")
    (tmp_path / ".claude/active_episode.json").write_text(json.dumps({"episode": "ep"}), encoding="utf-8")
    call = {"generations_count": 1, "text": "x"}
    assert "OR-17" in hook.decide("mcp__ElevenLabs__creative_generate_speech", call, tmp_path)
    SA.approve(script, "vano", "2026-10-20")
    assert "OR-17" not in (hook.decide("mcp__ElevenLabs__creative_generate_speech", call, tmp_path) or "")
