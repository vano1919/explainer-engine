"""N-07: the visitors' costume and the judge's visitors premise come from the episode's world, never from one episode's
text kept as a code default (the Stone Age frock coats, the 1700s-1900s scientists)."""

import copy
import json
from pathlib import Path

from explainer_engine.production import compile as C
from explainer_engine.qa import sheet_review as R
from explainer_engine.qa import visual_judge as J

ROOT = Path(__file__).resolve().parents[2]
EP1 = ROOT / "examples" / "stone_age" / "ep1_v1" / "production_script.json"
TITANS = ROOT / "examples" / "titans_from_zero" / "production_script.json"
DAY1 = ("1700s", "frock coat", "spectacles", "scientists")


def _doc(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _prompts(doc: dict) -> str:
    c = C.compile_doc(doc)
    return json.dumps([sh["picture"].get("prompt") for s in c["segments"] for sh in s["shots"]
                       if isinstance(sh["picture"], dict)])


def test_no_visitors_no_costume_and_other_visitors_get_their_own_era():
    doc = _doc(EP1)
    assert C._visitor_costume(doc).startswith("muddy frock coats")      # the Stone Age world names its visitors' clothes
    bare = copy.deepcopy(doc)
    bare["world"]["visitors"] = []
    del bare["world"]["visitor_costume"]
    assert C._visitor_costume(bare) == ""
    sail = copy.deepcopy(doc)
    sail["world"]["visitors"] = [{"era": "age_of_sail", "people": ["cook"]}]
    del sail["world"]["visitor_costume"]
    costume = C._visitor_costume(sail)
    assert costume and not any(w in costume for w in DAY1)               # the codex costume of that era, not Day 1's
    assert "1700s to 1900s" not in _prompts(sail)


def test_the_judge_premise_comes_from_the_world():
    titans = C.world_of(_doc(TITANS))
    assert titans["visitors"] == []
    prompt = J.build_prompt(titans, {"stakes": "storm", "not_yet": ["fire"]})
    assert not any(w in prompt for w in DAY1) and "time-travelling" not in prompt
    assert "Must NOT appear yet" in prompt and prompt.index("Must NOT appear yet") < prompt.index("What the picture")
    stone = C.world_of(_doc(EP1))
    note = J.build_prompt(stone, {"stakes": "storm"})
    assert "industrial victorian" in note and "frock coats" in note and "time-travelling visitors" in note


def test_the_stone_age_episode_keeps_its_premise():
    doc = _doc(EP1)
    assert "muddy frock coats, waistcoats, long skirts and spectacles of the 1700s to 1900s" in _prompts(doc)
    md = R.request(C.compile_doc(doc), [])
    assert "industrial victorian" in md
    # one costume source: the judge is told exactly the clothes the pictures were painted with (T1's review)
    costume = C._visitor_costume(doc)
    assert costume in _prompts(doc) and costume in md and "top hats" not in md
    assert "pocket watch" in md and "pocket watch" not in J.build_prompt(C.world_of(_doc(TITANS)), {"stakes": "x"})
