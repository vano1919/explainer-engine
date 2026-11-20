"""G-07: ltx_prompt_lint (LP-00..LP-06), tolerances file, film id check."""

from __future__ import annotations

import copy
import json

import pytest

from explainer_engine.qa import ltx_prompt_lint as lp
from explainer_engine.qa.ltx_prompt_lint import check_prompt_film, lint_ltx_prompt

HERO = "Anna"


def _clean(n: int = 120) -> str:
    return "Anna runs across the bridge " + " ".join(["fast"] * (n - 5))


def lint(prompt, **kw):
    kw.setdefault("hero_name", HERO)
    kw.setdefault("film_id", "f1")
    kw.setdefault("pack_film_id", "f1")
    return lint_ltx_prompt(prompt, **kw)


def rules(findings):
    return [f["rule"] for f in findings]


def test_clean_prompt_has_no_findings():
    assert len(_clean().split()) == 120
    assert lint(_clean()) == []


@pytest.mark.parametrize("prompt", ["", "   ", "\n\t "])
def test_empty_prompt_lp00_only(prompt):
    out = lint(prompt)
    assert rules(out) == ["LP-00"] and out[0]["severity"] == "FAIL"


def test_newline_lp01_fail():
    out = lint("Anna runs.\n\nShe jumps.")
    assert rules(out) == ["LP-01"] and out[0]["severity"] == "FAIL"


def test_word_limit_boundary():
    assert lint(_clean(200)) == []
    out = lint(_clean(201))
    assert rules(out) == ["LP-02"] and out[0]["severity"] == "FAIL"
    assert out[0]["detail"].endswith("(hypothesis, not binding until the owner has seen it)")


def test_non_action_opener_lp03_review():
    out = lint("The bridge shakes as Anna runs.")
    assert rules(out) == ["LP-03"] and out[0]["severity"] == "REVIEW"
    assert "hypothesis" in out[0]["detail"]


def test_forbidden_phrase_offset_and_case():
    out = lint("Orbit around Anna as she runs.")
    assert rules(out) == ["LP-04"] and out[0]["where"] == 0 and out[0]["severity"] == "REVIEW"
    assert "orbit" in out[0]["detail"] and "offset 0" in out[0]["detail"]


def test_whole_word_matching():
    assert lint("Anna runs while the camera dollying is not a word we flag.") == []
    assert rules(lint("Anna runs, camera dolly in.")) == ["LP-04"]


@pytest.mark.parametrize("phrase", ["static camera", "locked-off camera", "locked camera", "camera does not move",
                                    "whip-pan", "whip pan", "crash zoom", "rack focus", "arc shot", "360"])
def test_each_phrase_triggers_once(phrase):
    out = lint(f"Anna runs with a {phrase} here.")
    assert rules(out) == ["LP-04"]


def test_hero_missing_lp05_review_and_case_insensitive():
    out = lint("Bob runs across the bridge.")
    assert rules(out) == ["LP-05"] and out[0]["severity"] == "REVIEW"
    assert lint("ANNA runs across the bridge.") == []


def test_film_mismatch_lp06_fail():
    out = lint(_clean(), film_id="f1", pack_film_id="f2")
    assert rules(out) == ["LP-06"] and out[0]["severity"] == "FAIL"


def test_missing_pack_film_is_not_a_finding():
    assert lint(_clean(), pack_film_id=None) == []
    assert lint(_clean(), film_id=None) == []


def test_check_prompt_film_statuses():
    assert check_prompt_film("a", "a")["status"] == "PASS"
    assert check_prompt_film("a", "b")["status"] == "FAIL"
    assert check_prompt_film("a", None)["status"] == "NOT_RUN"
    assert check_prompt_film("a", "")["status"] == "NOT_RUN"
    for r in (check_prompt_film("a", "a"), check_prompt_film("a", None)):
        assert set(r) == {"status", "value", "detail"}


def test_non_string_prompt_raises_type_error():
    for bad in (None, 5, ["x"], b"x"):
        with pytest.raises(TypeError):
            lint(bad)


def test_inputs_not_mutated():
    args = {"prompt": _clean(), "hero_name": HERO, "film_id": "f1", "pack_film_id": "f1"}
    before = copy.deepcopy(args)
    lint_ltx_prompt(**args)
    assert args == before


def _tol(tmp_path, **override):
    data = json.loads(lp.DEFAULT_TOLERANCES.read_text(encoding="utf-8"))
    data.update(override)
    data = {k: v for k, v in data.items() if v is not None}
    p = tmp_path / "tol.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_default_tolerances_are_hypothesis_open():
    data = json.loads(lp.DEFAULT_TOLERANCES.read_text(encoding="utf-8"))
    assert data["schema"] == "ltx_prompt_tolerances/1"
    assert data["max_words"]["kind"] == "hypothesis" and data["max_words"]["status"] == "OPEN"
    nums = [k for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    assert nums == []


def test_custom_tolerance_changes_limit(tmp_path):
    path = _tol(tmp_path, max_words={"value": 10, "kind": "hypothesis", "status": "OPEN"})
    assert rules(lint(_clean(20), tolerances_path=path)) == ["LP-02"]


@pytest.mark.parametrize("key,bad", [("max_words", None), ("non_action_openers", None),
                                     ("forbidden_camera_phrases", None), ("max_words", {"value": "x"}),
                                     ("non_action_openers", "the"), ("forbidden_camera_phrases", [])])
def test_bad_tolerances_raise_value_error_naming_key(tmp_path, key, bad):
    path = _tol(tmp_path, **{key: bad})
    with pytest.raises(ValueError, match=key):
        lint(_clean(), tolerances_path=path)
