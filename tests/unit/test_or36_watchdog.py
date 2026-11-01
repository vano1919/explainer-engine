"""OR-36: every paid run has a hard cap and a cheap read-only Haiku watchdog."""
import json
from pathlib import Path

from explainer_engine import governance

ROOT = Path(__file__).resolve().parents[2]


def _front(path):
    text = path.read_text(encoding="utf-8").split("---")[1]
    return {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in text.strip().splitlines() if ":" in l)}


def test_the_watchdog_agent_is_haiku_low_and_cannot_write_or_spawn():
    cfg = json.loads((ROOT / "config" / "model_routing.json").read_text(encoding="utf-8"))
    governance.validate(cfg)
    f = _front(ROOT / ".claude" / "agents" / "paid-run-watchdog.md")
    assert (f["model"], f["effort"]) == ("haiku", "low") == (cfg["agents"]["paid-run-watchdog"]["model"],
                                                                cfg["agents"]["paid-run-watchdog"]["effort"])
    tools = {t.strip() for t in f["tools"].split(",")}
    assert not {"Write", "Edit", "MultiEdit", "NotebookEdit", "Agent", "Task"} & tools


def test_the_watchdog_page_names_only_read_only_runpod_commands():
    page = (ROOT / ".claude" / "agents" / "paid-run-watchdog.md").read_text(encoding="utf-8")
    assert "`python -m explainer_engine.cloud.runpod check`" in page
    assert "You never run `runpod create`, `stop`, `delete`, `start` or `sweep`" in page
    assert "80 % of the cap" in page


def test_or36_is_in_orchestration_and_is_not_a_spawner():
    text = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    row = next(l for l in text.splitlines() if l.startswith("| OR-36 "))
    assert "paid-run-watchdog" in row and "80 %" in row and "separate Haiku watchdog thread" in row
    cfg = json.loads((ROOT / "config" / "model_routing.json").read_text(encoding="utf-8"))
    assert "paid-run-watchdog" not in cfg["spawners"]
