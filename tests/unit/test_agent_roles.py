"""One main agent and one critic (OR-20, D-79): stage pages are followed by the main agent, never spawned; only the two
main agents may spawn, and each spawns only its one independent critic."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / ".claude/agents"
MAIN = {"orchestrator", "lora-coordinator"}
CRITICS = {"script-critic", "lora-checkpoint-judge"}


def _front(name: str) -> dict:
    text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    head = text.split("---", 2)[1]
    out = {}
    for line in head.strip().splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip()
    return out


def _names() -> set[str]:
    return {p.stem for p in AGENTS.glob("*.md")}


def test_every_agent_file_is_a_main_agent_a_critic_or_a_stage_page():
    for name in _names() - MAIN - CRITICS:
        assert _front(name)["description"].startswith("Stage page (OR-20, D-79)"), name
    for name in CRITICS:
        assert _front(name)["description"].startswith("The one independent critic (OR-20, D-79)"), name


def test_only_the_main_agents_may_spawn():
    spawners = {n for n in _names() if "Agent" in [t.strip() for t in _front(n).get("tools", "").split(",")]}
    assert spawners <= MAIN, spawners - MAIN


def test_the_main_agents_name_their_one_critic_and_run_the_stages_themselves():
    orch = (AGENTS / "orchestrator.md").read_text(encoding="utf-8")
    assert "the only agent you spawn is the critic" in orch and "`script-critic` (spawned, fresh context)" in orch
    lora = (AGENTS / "lora-coordinator.md").read_text(encoding="utf-8")
    assert "only the judge is spawned" in lora and "your checklist" in lora
    assert "| OR-20 |" in (ROOT / "docs/ORCHESTRATION.md").read_text(encoding="utf-8")
    assert "| D-79 |" in (ROOT / "docs/DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8")
