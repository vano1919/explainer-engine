"""P0b, Blueprint Lock 6 + Lock 5 (D-84): every agent file declares model and effort from the one config; critics are read-only;
only the two main agents may spawn; every script, module, skill and hook an agent or skill names exists."""
from __future__ import annotations

import json
from pathlib import Path
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
    # a command may end in `|| { ...; exit 2; }` (the closed pre-* hooks, T2.7): the hook name is the word after `governance.hooks`
    names = {m.group(1) for c in commands for m in [re.search(r"governance\.hooks ([\w-]+)", c)] if m}
    assert names == set(hooks.HOOKS)  # every hook is wired


PLANNED = re.compile(r"`[^`\n]*`\s*\(planned, (?:P\d+[a-z]?|W\d+)\)")  # P = blueprint phase, W = final-plan stream (W1 overlays name W2 validators)


def _named(text: str):
    mods = set(re.findall(r"python -m (explainer_engine[\w.]*)", text))
    paths = set(re.findall(r"`(explainer_engine/[\w/]+\.py)`", text))
    skills = set(re.findall(r"skills? `([a-z][a-z-]+)`", text))
    return mods, paths, skills


def _module_exists(mod: str) -> bool:
    p = ROOT / mod.replace(".", "/")
    return p.with_suffix(".py").exists() or (p / "__init__.py").exists() or (p / "__main__.py").exists()


def _upstream_text(f) -> bool:
    parts = f.relative_to(ROOT / ".claude").parts
    vdir = next((i for i, part in enumerate(parts) if part.startswith("v-")), None)
    if vdir is None:
        return False
    folder = ROOT / ".claude" / Path(*parts[:vdir + 1])
    rel = Path(*parts[vdir + 1:]).as_posix()
    if rel == "OVERLAY.md":  # our rules on top of a vendored skill (team plan rule 4): scanned like any skill of ours
        return False
    src = folder / "SOURCE.md"
    return rel == "SOURCE.md" or (src.is_file() and f"  {rel}\n" in src.read_text(encoding="utf-8"))


def test_everything_an_agent_or_a_skill_names_exists():
    missing = []
    # vendored upstream text (`v-*` files pinned in SOURCE.md; our OVERLAY.md is scanned) is byte-pinned third-party text guarded by
    # tests/unit/test_vendored_skills.py, not this scan; our RW-50 rewrite of a v-* SKILL.md is ours and is scanned (2026-11-20)
    files = [f for f in (ROOT / ".claude").rglob("*.md") if not _upstream_text(f)]
    for f in files:
        # only a reference directly followed by the marker "(planned, P8)" may name a module a later phase builds; the marker is the
        # contract and exempts nothing else on the line
        text = PLANNED.sub("", f.read_text(encoding="utf-8"))
        mods, paths, skills = _named(text)
        missing += [f"{f.name}: module {m}" for m in mods if not _module_exists(m)]
        missing += [f"{f.name}: {p}" for p in paths if not (ROOT / p).exists()]
        missing += [f"{f.name}: skill {s}" for s in skills if not (ROOT / ".claude/skills" / s / "SKILL.md").exists() and not (ROOT / ".claude/skills/_archive" / s / "SKILL.md").exists() and s not in {n for n in NAMES}]
    assert not missing, missing


def test_the_planned_marker_exempts_only_the_reference_in_front_of_it():
    assert PLANNED.sub("", "`explainer_engine/qa/x.py` (planned, P8) and `explainer_engine/qa/y.py` exist") == " and `explainer_engine/qa/y.py` exist"
    assert PLANNED.sub("", "`a.py` (planned P8)") == "`a.py` (planned P8)"  # the exact marker, with a phase id
    assert PLANNED.sub("", "`a.py` (planned, soon)") == "`a.py` (planned, soon)"
    planned = re.findall(r"\(planned, (P\d+[a-z]?)\)", "".join(f.read_text(encoding="utf-8") for f in (ROOT / ".claude").rglob("*.md")))
    phases = {p["id"] for p in json.loads((ROOT / "docs/blueprint/phases.json").read_text(encoding="utf-8"))["phases"]}
    assert planned and set(planned) <= phases  # a marker names a phase of the plan


def test_the_blueprint_packages_that_must_not_exist_do_not():
    for name in ("storyboard", "validation", "telemetry", "style", "thumbnail"):
        assert not (ROOT / "explainer_engine" / name).is_dir(), name
    assert not (ROOT / "engine").exists()  # Blueprint Phase 1 item 14


# ---- T4 (plan_v2 wave 2): CP-12 route notes, N-06 docstring scope, the select_screen move ------------------------------------------

def test_cp12_edit_planner_and_shot_visuals_carry_a_route_note_and_no_live_2512():
    for rel in (".claude/agents/edit-planner.md", ".claude/skills/_archive/shot-visuals/SKILL.md"):
        lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        assert any("Route note" in l and "D-43" in l and "D-80" in l for l in lines[:12]), rel
        for l in lines:
            if "2512" in l or "Edit-2511" in l:
                assert "banned" in l, (rel, l)
    skill = (ROOT / ".claude/skills/_archive/shot-visuals/SKILL.md").read_text(encoding="utf-8")
    assert skill.index("## Still-picture route (D-43)") < skill.index("## Animated route (D-77/D-80)")
    assert skill.index("## Animated shots") > skill.index("## Animated route (D-77/D-80)")
    assert skill.index("## Procedure") < skill.index("## Animated route (D-77/D-80)")  # the sprite procedure stays in the still route


def test_n06_routing_hook_and_staging_docstrings_say_they_are_the_still_picture_route():
    for rel in ("imagegen/routing.py", "standards/hook.py", "production/staging.py"):
        head = "\n".join((ROOT / "explainer_engine" / rel).read_text(encoding="utf-8").splitlines()[:8])
        assert "Scope (N-06" in head and "D-43" in head and "D-80" in head, rel


def test_select_screen_lives_with_its_episode():
    assert not (ROOT / "explainer_engine/production/select_screen.py").exists()
    assert (ROOT / "examples/syndicate_wars_ep1/select_screen.py").exists()
    assert (ROOT / "examples/syndicate_wars_ep1/test_select_screen.py").exists()
    assert "examples/syndicate_wars_ep1/select_screen.py" in (ROOT / "explainer_engine/production/shorts.py").read_text(encoding="utf-8")
    assert "examples/syndicate_wars_ep1" in (ROOT / "pytest.ini").read_text(encoding="utf-8")
