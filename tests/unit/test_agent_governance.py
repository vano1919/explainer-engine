"""P0b, Blueprint Lock 6 + Lock 5 (D-84): every agent file declares model and effort from the one config; critics are read-only;
only the two main agents may spawn; every script, module, skill and hook an agent or skill names exists."""
from __future__ import annotations

import json
import re

import pytest

from explainer_engine import governance
from explainer_engine.core.errors import ContractError
from explainer_engine.governance import hooks
from _gov import AGENTS, ROOT, config, front, tools

CFG = config()
NAMES = sorted(p.stem for p in AGENTS.glob("*.md"))


def test_config_validates_and_covers_every_agent_file():
    governance.validate(CFG)
    assert set(CFG["agents"]) == set(NAMES)
    assert len(CFG["classes"]) == 18


@pytest.mark.parametrize("name", NAMES)
def test_agent_frontmatter_matches_the_config(name):
    f, a = front(AGENTS / f"{name}.md"), CFG["agents"][name]
    for key in ("name", "description", "tools", "model", "effort"):
        assert f.get(key), f"{name}: {key}"
    assert f["name"] == name
    assert (f["model"], f["effort"]) == (a["model"], a["effort"]), name


def test_critics_are_opus_high_and_read_only():
    crit = CFG["critics"]
    for name in crit["names"]:
        f = front(AGENTS / f"{name}.md")
        assert (f["model"], f["effort"]) == (crit["model"], crit["effort"]), name
        assert set(tools(AGENTS / f"{name}.md")) <= set(crit["tools"]), name
        assert not {"Bash", "Write", "Edit", "Agent", "Task"} & set(tools(AGENTS / f"{name}.md"))


def test_only_the_two_main_agents_spawn_and_the_old_task_name_counts_too():
    spawners = {n for n in NAMES if {"Agent", "Task"} & set(tools(AGENTS / f"{n}.md"))}
    assert spawners <= set(CFG["spawners"]) == {"orchestrator", "lora-coordinator"}


def test_fable_only_on_the_story_stages_and_only_with_the_flag():
    story = set(CFG["fable_story_stages"]["stages"])
    for n in NAMES:
        model = front(AGENTS / f"{n}.md")["model"]
        if model == "fable":
            assert n in story and CFG["fable_story_stages"]["enabled"], n
        if CFG["agents"][n]["role"] == "main":
            assert model != "fable"
    assert CFG["fable_story_stages"]["enabled"] is False  # the creator turns it on, in his own words


def test_effort_never_above_the_code_ceiling_in_an_agent_file():
    order = CFG["efforts"]
    for n in NAMES:
        assert order.index(front(AGENTS / f"{n}.md")["effort"]) <= order.index(CFG["code"]["effort_ceiling"]), n


def test_the_config_validator_rejects_a_bad_pair():
    bad = json.loads(json.dumps(CFG))
    bad["agents"]["script-critic"]["model"] = "sonnet"
    with pytest.raises(ContractError):
        governance.validate(bad)
    bad = json.loads(json.dumps(CFG))
    bad["agents"]["orchestrator"]["model"] = "fable"
    with pytest.raises(ContractError):
        governance.validate(bad)
    bad = json.loads(json.dumps(CFG))
    bad["agents"]["beat-writer"]["effort"] = "max"
    with pytest.raises(ContractError):
        governance.validate(bad)


def test_every_hook_command_names_an_existing_module_and_hook():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = []
    for entries in settings["hooks"].values():
        for e in entries:
            commands += [h["command"] for h in e["hooks"]]
    commands.append(settings["statusLine"]["command"])
    for cmd in commands:
        m = re.search(r"-m (explainer_engine[\w.]*)\s*(\S*)", cmd)
        assert m, cmd
        path = ROOT / (m.group(1).replace(".", "/") + ".py")
        assert path.exists(), m.group(1)
        if m.group(1) == "explainer_engine.governance.hooks":
            assert m.group(2) in hooks.HOOKS, m.group(2)
    names = {re.search(r"hooks (\S+)$", c).group(1) for c in commands if c.endswith(tuple(hooks.HOOKS))}
    assert names == set(hooks.HOOKS)  # every hook is wired


def _named(text: str):
    mods = set(re.findall(r"python -m (explainer_engine[\w.]*)", text))
    paths = set(re.findall(r"`(explainer_engine/[\w/]+\.py)`", text))
    skills = set(re.findall(r"skills? `([a-z][a-z-]+)`", text))
    return mods, paths, skills


def _module_exists(mod: str) -> bool:
    p = ROOT / mod.replace(".", "/")
    return p.with_suffix(".py").exists() or (p / "__init__.py").exists() or (p / "__main__.py").exists()


def test_everything_an_agent_or_a_skill_names_exists():
    missing = []
    files = list((ROOT / ".claude").rglob("*.md"))
    for f in files:
        mods, paths, skills = _named(f.read_text(encoding="utf-8"))
        missing += [f"{f.name}: module {m}" for m in mods if not _module_exists(m)]
        missing += [f"{f.name}: {p}" for p in paths if not (ROOT / p).exists()]
        missing += [f"{f.name}: skill {s}" for s in skills if not (ROOT / ".claude/skills" / s / "SKILL.md").exists() and s not in {n for n in NAMES}]
    assert not missing, missing


def test_the_blueprint_packages_that_must_not_exist_do_not():
    for name in ("storyboard", "validation", "telemetry", "style", "thumbnail"):
        assert not (ROOT / "explainer_engine" / name).is_dir(), name
    assert not (ROOT / "engine").exists()  # Blueprint Phase 1 item 14
