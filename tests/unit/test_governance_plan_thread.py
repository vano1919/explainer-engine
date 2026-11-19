"""Step 0.4c (D-139): the plan thread's recorded approval of the file list and a few protected files. Limits that stay with the
creator are tested as hard as the new power: spend caps, model routing, governance code, quality.yml diffs that weaken CI."""
from __future__ import annotations

import json

import pytest

from _gov import make_repo
from explainer_engine.governance import hooks, records

DELEG = "cmsg_owner_delegation"
APPROVABLE = ["docs/architecture/v4_1_allowlists.json", "config/picture_route.json", "config/retired_era.json",
              ".github/workflows/quality.yml"]


@pytest.fixture
def repo(tmp_path):
    r = make_repo(tmp_path / "r", git=False)
    cfg = json.loads((r / "config" / "model_routing.json").read_text(encoding="utf-8"))
    cfg["plan_thread_approvable"] = APPROVABLE
    cfg["plan_thread_delegation"] = {"message_id": DELEG, "quote": "the plan thread approves the file list"}
    cfg["protected_files"] = dict(cfg["protected_files"], **{p: 60 for p in APPROVABLE})
    (r / "config" / "model_routing.json").write_text(json.dumps(cfg), encoding="utf-8")
    return r


def approve(repo, target, **kw):
    kw.setdefault("reason", "amendment needs it")
    kw.setdefault("delegation_ref", DELEG)
    return records.add("protected_config", target, "cmsg_plan", "plan thread: approved", by="plan_thread", root=repo, **kw)


def write(repo, rel, content=None, old=None, new=None):
    ti = {"file_path": str(repo / rel)}
    if content is not None:
        ti["content"] = content
    else:
        ti.update(old_string=old, new_string=new)
    return hooks.pre_write({"tool_name": "Write", "tool_input": ti}, repo)


def test_a_plan_thread_record_unlocks_an_approvable_file(repo):
    rel = "docs/architecture/v4_1_allowlists.json"
    assert write(repo, rel, "{}") == 2
    approve(repo, rel)
    assert write(repo, rel, "{}") == 0


def test_it_never_unlocks_spend_caps_model_routing_channel_voices_or_governance_code(repo):
    for rel in ("config/spend_caps.json", "config/model_routing.json", "config/channel_voices.json",
                "explainer_engine/cloud/cheapest.py", "explainer_engine/training/pods/ltx/launch.json"):
        with pytest.raises(ValueError):
            approve(repo, rel)
        assert write(repo, rel, "x") == 2
    for rel in ("explainer_engine/governance/records.py", "explainer_engine/governance/hooks.py",
                "explainer_engine/governance/__main__.py"):     # a plan-thread record can never widen its own powers
        with pytest.raises(ValueError):
            approve(repo, rel)


def test_listing_a_never_file_in_the_config_does_not_widen_it(repo):
    cfg = json.loads((repo / "config" / "model_routing.json").read_text(encoding="utf-8"))
    cfg["plan_thread_approvable"] += ["config/spend_caps.json", "explainer_engine/governance/records.py"]
    (repo / "config" / "model_routing.json").write_text(json.dumps(cfg), encoding="utf-8")
    for rel in ("config/spend_caps.json", "explainer_engine/governance/records.py"):
        with pytest.raises(ValueError):
            approve(repo, rel)
    # a hand-written plan_thread line for a spend caps edit is ignored by the hook too
    (repo / "jobs").mkdir(exist_ok=True)
    import time
    (repo / "jobs" / "creator_ok.jsonl").write_text(json.dumps({"action": "protected_config", "target": "config/spend_caps.json",
        "message_id": "m", "by": "plan_thread", "at": time.time()}) + "\n", encoding="utf-8")
    assert write(repo, "config/spend_caps.json", "x") == 2


def test_the_record_needs_reason_delegation_and_no_wildcard(repo):
    rel = "config/picture_route.json"
    with pytest.raises(ValueError):
        approve(repo, rel, reason="")
    with pytest.raises(ValueError):
        approve(repo, rel, delegation_ref="")
    with pytest.raises(ValueError):
        approve(repo, rel, delegation_ref="cmsg_made_up")
    with pytest.raises(ValueError):
        approve(repo, "*")
    with pytest.raises(ValueError):
        records.add("model_switch", "opus", "cmsg_plan", "q", by="plan_thread", root=repo, reason="r", delegation_ref=DELEG)
    with pytest.raises(ValueError):
        records.add("protected_config", rel, "cmsg_plan", "q", by="someone", root=repo)


def test_a_plan_thread_record_expires_like_the_creators(repo):
    rel = "config/retired_era.json"
    approve(repo, rel, now=__import__("time").time() - 7200)
    assert write(repo, rel, "{}") == 2


def test_a_plan_thread_record_never_stands_for_the_creators_word_elsewhere(repo):
    rel = "config/picture_route.json"
    approve(repo, rel)
    assert records.find("protected_config", rel, "cmsg_plan", minutes=60, root=repo) is None     # creator_ref checks ignore it
    assert not records.valid("protected_config", rel, 60, root=repo, wildcard=False, include_plan_thread=False)
    assert records.valid("effort_override", "*", 60, root=repo) is False


QY = ".github/workflows/quality.yml"
BASE = "steps:\n  - name: tests\n    run: pytest -q -m \"not system\"\n  - name: docs\n    run: python -m explainer_engine.docs_lint\n"


def test_quality_yml_changes_that_weaken_ci_still_need_the_creator(repo):
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / QY).write_text(BASE, encoding="utf-8")
    approve(repo, QY)
    harmless = BASE + "  - name: scope\n    run: python -m explainer_engine.scope_check\n"
    assert write(repo, QY, harmless) == 0
    assert write(repo, QY, old="  - name: docs\n    run: python -m explainer_engine.docs_lint\n", new="") == 2          # a step removed
    assert write(repo, QY, BASE.replace("pytest -q", "pytest -q --deselect tests/x.py::t")) == 2
    assert write(repo, QY, BASE.replace("pytest -q", "pytest -q -k fast")) == 2
    assert write(repo, QY, BASE + "    continue-on-error: true\n") == 2
    assert write(repo, QY, BASE.replace("pytest -q", "echo ok # pytest -q")) == 2                   # R2: a command swapped for a no-op
    assert write(repo, QY, BASE.replace('pytest -q -m "not system"', "echo ok")) == 2
    assert write(repo, QY, BASE.replace('"not system"', '"not system and not media"')) == 2         # R2: any changed run command, even an existing -m filter
    assert records.quality_yml_problems(BASE, BASE) == []
    assert records.quality_yml_problems(BASE, BASE + "  - name: x\n    run: |\n      echo added\n") == []   # only added steps/commands
    block = "  - name: b\n    run: |\n      pytest -q\n      python -m docs\n"
    assert records.quality_yml_problems(BASE + block, BASE + block.replace("python -m docs", "true"))                 # a line of a run block counts too


def test_a_shell_write_to_quality_yml_cannot_be_diffed_so_it_needs_the_creator(repo):
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / QY).write_text(BASE, encoding="utf-8")
    approve(repo, QY)
    assert hooks.pre_bash({"tool_input": {"command": f"sed -i 's/x/y/' {QY}"}}, repo) == 2
    approve(repo, "config/picture_route.json")
    assert hooks.pre_bash({"tool_input": {"command": "sed -i 's/x/y/' config/picture_route.json"}}, repo) == 0


def test_a_creator_record_still_unlocks_everything_it_did_before(repo):
    records.add("protected_config", "config/spend_caps.json", "cmsg_owner", "ვანო: კი", root=repo)
    assert write(repo, "config/spend_caps.json", "{}") == 0


def test_the_audit_lists_every_plan_thread_approval(repo, capsys):
    approve(repo, "config/picture_route.json", reason="slice 1.1 picture route")
    rows = records.plan_thread_audit(root=repo)
    assert len(rows) == 1 and rows[0]["reason"] == "slice 1.1 picture route" and rows[0]["delegation_ref"] == DELEG
