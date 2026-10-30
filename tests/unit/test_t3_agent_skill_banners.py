"""T3-3 (CP-07, CP-08, CP-13): retired material is banded in place, never deleted; the live pages name the live stack."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(p):
    return (ROOT / p).read_text(encoding="utf-8")


def _head(p, n):
    return "\n".join(_text(p).splitlines()[:n])


def test_animated_universe_skill_is_retired_in_part():
    p = ".claude/skills/animated-universe/SKILL.md"
    txt = _text(p)
    assert "Retired in part" in _head(p, 15)
    assert "Use the rig's cycles" not in txt.split("#### History")[0]
    assert "docs/SHOT_PROMPTS.md" in txt and "docs/SHOT_CONTINUITY.md" in txt
    assert "cut-out rig with reusable cycles" not in re.search(r"^description:.*$", txt, re.M).group(0)
    assert "#### History (retired 2026-10-22)" in txt


def test_lora_agents_describe_one_lora_on_qwen_image_2_1():
    for a in ("lora-coordinator", "lora-dataset-auditor", "lora-checkpoint-judge"):
        txt = _text(f".claude/agents/{a}.md")
        desc = re.search(r"^description:\s*(.*)$", txt, re.M).group(1)
        for banned in ("Qwen-Image-Edit", "next pose", "video motion on LTX"):
            assert banned not in desc, (a, banned)
        assert "## History (retired by D-80)" in txt, a
        body = txt.split("## History (retired by D-80)")[0]
        assert "5.21 s/step" not in body, a


def test_lora_training_skill_history_precedes_the_2512_settings():
    txt = _text(".claude/skills/lora-training/SKILL.md")
    hist = txt.index("## History (retired by D-80, lessons only)")
    assert hist < txt.index("Settings that worked (2026-10-23, Qwen-Image-2512")
    assert hist < txt.index("## Video and edit LoRAs")
    assert "Current stack: one LoRA on Qwen-Image-2.1" in txt[:hist]


def test_orchestrator_is_scoped_to_the_still_picture_route():
    head = _head(".claude/agents/orchestrator.md", 20)
    assert "Scope (" in head and "P11" in head
    assert "D-43 still-picture route" in _text("docs/ORCHESTRATION.md")
