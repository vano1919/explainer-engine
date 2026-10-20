import base64
import json

import numpy as np
import pytest

from explainer_engine.edit import prompt_v2
from explainer_engine.finish.grade import grade, mean_luma
from explainer_engine.imagegen.gemini import GeminiClient, GeminiError, estimate
from explainer_engine.qa import visual_judge as vj
from explainer_engine.world import resolver

SPEC = {"topic": "100 greatest scientists in the Stone Age",
        "host": {"era": "prehistory", "place": "SE Anatolia", "when": "about 10,000 BCE"},
        "visitors": [{"era": "industrial_victorian", "people": ["darwin", "franklin"]}],
        "day_arc": [{"beat": 1, "light": "storm_dusk"}, {"beat": 3, "light": "night_fire"}]}


def world():
    return resolver.resolve(SPEC)


def test_codex_has_thirteen_eras_and_every_grade_exists():
    c = resolver.load_codex()
    assert len(c["eras"]) == 13  # the 12 history/science eras + modern_neon_florida (Syndicate Wars, 2026-10-17)
    assert all(e["grade"] in c["grades"] for e in c["eras"].values())


def test_resolver_rejects_unknown_era_and_light():
    with pytest.raises(ValueError):
        resolver.resolve({**SPEC, "host": {"era": "atlantis"}})
    bad = {**SPEC, "day_arc": [{"beat": 1, "light": "neon"}]}
    with pytest.raises(ValueError):
        resolver.resolve(bad)


def test_light_follows_beat():
    w = world()
    assert "storm" in resolver.clause_for_beat(w, 2)
    assert "campfire" in resolver.clause_for_beat(w, 3)


def test_composed_prompt_passes_lint():
    w = world()
    p = prompt_v2.compose("B", "Franklin shields a spark with both hands, fear", w, 3, people=True)
    assert prompt_v2.lint(p, w, people=True) == []


def test_lint_catches_absent_child_cue_second_light_and_missing_thread():
    w = world()
    base = prompt_v2.compose("A", "a ridge", w, 1)
    assert any(f["rule"] == "UR-23" for f in prompt_v2.lint(base + ", a pottery jar", w))
    assert any(f["rule"] == "UR-24" for f in prompt_v2.lint(base + ", cute storybook kids", w))
    second = base + ", " + w["light_keys"]["night_fire"]
    assert any(f["rule"] == "UR-26" for f in prompt_v2.lint(second, w))
    assert any(f["rule"] == "UR-22" for f in prompt_v2.lint("a ridge, " + w["light_keys"]["storm_dusk"], w))


def test_visitor_prop_is_review_not_fail():
    w = world()
    p = prompt_v2.compose("C", "a hand holds spectacles", w, 1) + ", a glass lens"
    f = prompt_v2.lint(p, w, visitors_named=["franklin"])
    assert f and all(x["severity"] == "REVIEW" for x in f if x["rule"] == "UR-23")


def test_grade_is_deterministic_and_bounded():
    img = np.random.default_rng(1).random((16, 16, 3))
    g = resolver.load_codex()["grades"]["prehistory"]
    a, b = grade(img, g, 7), grade(img, g, 7)
    assert np.array_equal(a, b) and 0.0 <= a.min() and a.max() <= 1.0
    assert abs(mean_luma(a) - mean_luma(img)) < 0.1


def test_judge_verdicts():
    meta = {"plate": True, "hero": None, "stakes": "storm"}
    ok = {"adults": True, "era_objects": False, "text": False, "one_light": True, "mood": True, "people_in_plate": False, "too_early": False}
    assert vj.verdict(ok, meta)["status"] == "PASS"
    assert vj.verdict({**ok, "adults": False}, meta)["status"] == "FAIL"
    assert vj.verdict({**ok, "people_in_plate": True}, meta)["status"] == "FAIL"
    assert vj.parse('noise {"adults": true} tail') == {"adults": True}
    assert "SE Anatolia" in vj.build_prompt(world(), meta)


def png_reply():
    return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png",
            "data": base64.b64encode(b"PNG").decode()}}]}}]}


def test_gemini_client_cache_cap_and_log(tmp_path):
    calls = []
    c = GeminiClient(tmp_path, key="k", cap_usd=1.0, post=lambda m, b: calls.append(m) or png_reply())
    c.generate("a", "p", model="gemini-3-pro-image", size="2K")
    c.generate("a2", "p", model="gemini-3-pro-image", size="2K")  # same request: cache, no second call
    assert len(calls) == 1 and abs(c.spent - 0.134) < 1e-9
    rows = [json.loads(x) for x in (tmp_path / "spend_log.jsonl").read_text().splitlines()]
    assert [r["cached"] for r in rows] == [False, True]
    small = GeminiClient(tmp_path / "s", key="k", cap_usd=0.10, post=lambda m, b: png_reply())
    with pytest.raises(GeminiError):
        small.generate("x", "q", model="gemini-3-pro-image", size="2K")  # 0.134 > 80 % of 0.10
    with pytest.raises(GeminiError):
        estimate("gemini-3-pro-image", "9K", 1)


def test_story_state_not_yet():
    spec = {**SPEC, "day_arc": [{"beat": 1, "light": "storm_dusk", "not_yet": ["fire", "campfire"]},
                                {"beat": 3, "light": "night_fire"}]}
    w = resolver.resolve(spec)
    p = prompt_v2.compose("A", "a cold ridge with a long shadow", w, 1)
    assert "nothing burning or glowing anywhere" in p and "woodsmoke" not in p and "fire" not in p.lower().split("one drawn universe")[0]
    assert prompt_v2.lint(p, w, beat=1) == []
    bad = prompt_v2.lint(p + ", a small campfire burns", w, beat=1)
    assert any(f["rule"] == "UR-27" for f in bad)
    assert prompt_v2.lint(prompt_v2.compose("A", "a camp", w, 3), w, beat=3) == []


def test_modern_neon_florida_era_resolves_and_keeps_franchise_names_out_of_prompts():
    c = resolver.load_codex()
    w = resolver.resolve({"topic": "t", "host": {"era": "modern_neon_florida", "place": "p", "when": "w"},
                          "visitors": [], "day_arc": [{"beat": 1, "light": "neon_dusk"}]})
    assert w["grade"] == "neon_dusk" and "neon_dusk" in c["grades"]
    assert resolver.words_in("a Rockstar skyline, GTA logo", w["absent"]) == ["gta", "rockstar"]
