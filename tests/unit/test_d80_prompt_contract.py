"""N-09 (D-80): every picture prompt is on the one stack, Qwen-Image-2.1 + the xworld LoRA. The trigger has one home
(``training/lora_rules.json``), the composer emits no ``wldnk``/``nextpose`` prefix and no scene LoRA, and every card's
inference passes the keyframe gate's stack check (KG-16)."""

import json
import re
from pathlib import Path

from explainer_engine.qa import keyframe_gate, style_prompt
from explainer_engine.scripting import film_shots as F
from explainer_engine.training import lora_rules

ROOT = Path(__file__).resolve().parents[2]
BUS = ROOT / "examples" / "film_shots" / "bus_in_the_ice_age.json"
NAPOLEON = ROOT / "examples" / "napoleon_vs_genghis"
PICTURES = ("keyframe", "nextpose", "cut")
# the live prompt writers; a retired word may stand only on a line that names it retired
LIVE = ("explainer_engine/scripting/film_shots.py", "explainer_engine/qa/style_prompt.py",
        "explainer_engine/compose/episode_look.py", "explainer_engine/compose/style_score.py",
        "examples/napoleon_vs_genghis/episode.py")


def _on_the_d80_stack(card: dict) -> None:
    trigger = lora_rules.trigger()
    assert card["prompt"].startswith(trigger + ", "), card["id"]
    assert not re.match(r"\s*(wldnk|nextpose)\b", card["prompt"]), card["id"]
    assert card.get("lora") != "scene", card["id"]
    inf = card["inference"]
    keyframe_gate.check_stack(inf["base"], {inf["lora"]: inf.get("lora_weight")} if inf.get("lora") else {})


def test_one_trigger_home():
    trigger = lora_rules.trigger()
    assert style_prompt.TRIGGER == trigger and not trigger.startswith("wldnk")
    # the pod scripts keep their own literal (their sha binds a budget approval, N-03): pinned to the home, never edited here
    from explainer_engine.training.pods import xworld_v1_build, xworld_v2_data
    assert xworld_v2_data.TRIGGER == xworld_v1_build.TRIGGER == trigger
    for rel in LIVE:
        for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if "wldnk style" in line or '"nextpose, ' in line:
                assert "RETIRED" in line, f"{rel}:{n} states a retired trigger: {line.strip()}"


def test_compose_emits_only_the_d80_stack():
    doc = json.loads(BUS.read_text(encoding="utf-8"))
    cards = [c for c in F.compose(doc) + F.sheet_prompts(doc) if c["kind"] in PICTURES]
    assert {c["kind"] for c in cards} == set(PICTURES)  # the fixture has every picture kind
    for card in cards:
        _on_the_d80_stack(card)
    assert not [f for f in F.style_check(doc) if f["severity"] == "FAIL"]


def test_style_check_fails_a_retired_trigger():
    doc = json.loads(BUS.read_text(encoding="utf-8"))
    doc["style"]["trigger"] = "wldnk style"
    assert any(f["rule"] == "LT-65" and f["severity"] == "FAIL" for f in F.style_check(doc))


def test_napoleon_fixture_is_on_the_d80_stack():
    doc = json.loads((NAPOLEON / "film_shots.json").read_text(encoding="utf-8"))
    assert doc["style"]["trigger"] == lora_rules.trigger()
    committed = json.loads((NAPOLEON / "prompts.json").read_text(encoding="utf-8"))
    cards = [c for c in committed["sheets"] + committed["shots"] if c["kind"] in PICTURES]
    assert len(cards) > 200
    for card in cards:
        _on_the_d80_stack(card)
    shotlist = (NAPOLEON / "shotlist.md").read_text(encoding="utf-8")
    assert "wldnk" not in shotlist and "nextpose," not in shotlist
