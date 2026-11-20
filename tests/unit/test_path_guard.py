"""T2.7 path guard (tester S2, S3, W2, R7): the owner's word and the send records are never written by hand; the gate files are protected
by a mechanism that SHIPS SWITCHED OFF. Judged by the files a command touches, not by its words."""
from __future__ import annotations

import io
import json
import sys

import pytest

from _gov import ROOT, make_repo
from explainer_engine.governance import hooks, path_guard, records


@pytest.fixture
def repo(tmp_path):
    r = make_repo(tmp_path / "r")
    (r / "jobs" / "send_gate").mkdir(parents=True)
    (r / "jobs" / "creator_ok.jsonl").write_text("", encoding="utf-8")
    (r / ".claude").mkdir()
    (r / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (r / "explainer_engine" / "governance").mkdir(parents=True)
    (r / "explainer_engine" / "governance" / "send_gate.py").write_text("x = 1\n", encoding="utf-8")
    (r / "docs" / "layers").mkdir(parents=True)
    (r / "docs" / "layers" / "L9.json").write_text("{}", encoding="utf-8")
    return r


@pytest.fixture
def gate_on(tmp_path, monkeypatch):
    cfg = tmp_path / "gate_files.json"
    cfg.write_text(json.dumps({"schema": "gate_files/1", "enabled": True, "paths": [
        ".claude/settings.json", "explainer_engine/governance/**", "docs/layers/**", ".github/workflows/owner-requirements.yml"]}), encoding="utf-8")
    monkeypatch.setattr(path_guard, "GATE_CONFIG", cfg)


def bash(repo, cmd):
    return hooks.pre_bash({"tool_input": {"command": cmd}}, repo)


def write(repo, rel, tool="Write"):
    return hooks.pre_write({"tool_name": tool, "tool_input": {"file_path": str(repo / rel)}}, repo)


NEVER_PATHS = ["jobs/creator_ok.jsonl", "jobs/send_gate/records.jsonl", "jobs/send_gate/quarantine.jsonl", "jobs/send_gate/incidents.jsonl"]


# ---- the owner's word and the send records: never by hand (W2, S2, S3) ------------------------------------------------------------

@pytest.mark.parametrize("rel", NEVER_PATHS)
def test_W2_a_write_or_edit_of_the_owners_word_or_the_send_records_is_refused(repo, rel):
    assert write(repo, rel) == 2
    assert write(repo, rel, tool="Edit") == 2


def test_W2_no_recorded_word_unlocks_them(repo):
    records.add("protected_config", "jobs/creator_ok.jsonl", "cmsg_x", "ok", root=repo)
    assert write(repo, "jobs/creator_ok.jsonl") == 2
    assert bash(repo, "echo x >> jobs/creator_ok.jsonl") == 2


REFUSED = [
    "echo x >> jobs/creator_ok.jsonl",
    "cd jobs && echo x >> creator_ok.jsonl",
    "cd jobs/send_gate && echo x >> records.jsonl",
    "D=jobs/send_gate; echo x > $D/records.jsonl",
    "export D=jobs; echo x > ${D}/creator_ok.jsonl",
    "echo x > jobs/creator_*",
    "cat /dev/null > jobs/send_gate/rec*",
    "cat /dev/null > jobs/creator_o?.jsonl",
    "python3 -c \"from pathlib import Path; Path('jobs/creator_ok.jsonl').write_text('')\"",
    "python3 -c \"open('jobs/send_gate/records.jsonl','a').write('x')\"",
    "python3 - <<'EOF'\nfrom pathlib import Path\nPath('jobs/send_gate/records.jsonl').write_text('')\nEOF",
    "rm jobs/send_gate/quarantine.jsonl",
    "rm -rf jobs/send_gate",
    "mv jobs/send_gate /tmp/x",
    "ln -sf /tmp/x jobs/creator_ok.jsonl",
    "curl -o jobs/send_gate/records.jsonl http://example.invalid/x",
    "rsync -a /tmp/x/ jobs/send_gate/",
    "ex -sc 'wq' jobs/creator_ok.jsonl",
    "sed -i s/a/b/ jobs/creator_ok.jsonl",
    "truncate -s0 jobs/send_gate/records.jsonl",
    "tee jobs/creator_ok.jsonl",
    "cp /tmp/x jobs/creator_ok.jsonl",
    "bash -c 'echo x >> jobs/creator_ok.jsonl'",
    "echo ok && echo x >> jobs/creator_ok.jsonl",
    "sed -i 's/a/b/' .claude/settings.json && echo disableAllHooks",
    "python3 -c \"import json; d=json.load(open('.claude/settings.json')); d['disableAllHooks']=True; json.dump(d,open('.claude/settings.json','w'))\"",
]


@pytest.mark.parametrize("cmd", REFUSED, ids=[c[:60].replace("\n", " ") for c in REFUSED])
def test_a_command_that_writes_the_owners_word_or_the_send_records_is_refused(repo, cmd):
    assert bash(repo, cmd) == 2, cmd


ALLOWED = [
    "cat jobs/creator_ok.jsonl",
    "grep layer_waiver jobs/creator_ok.jsonl",
    "tail -3 jobs/send_gate/records.jsonl",
    "ls jobs/send_gate",
    "wc -l jobs/creator_ok.jsonl",
    "cat jobs/creator_ok.jsonl > /tmp/copy.jsonl",
    "python3 -c \"print(open('jobs/creator_ok.jsonl').read())\"",
    "python -m explainer_engine.governance.send_gate L9 out/trials/L9/x.txt",
    "python -m explainer_engine.governance ok layer_waiver L9 cmsg_abc \"he said ok\"",
    "echo hi > /tmp/x.txt",
    "git status",
    "git diff -- jobs",
    "mkdir -p jobs/sample-job-001",
    "ls jobs",
    "echo 'disableAllHooks is a setting' > /tmp/note.txt",
]


@pytest.mark.parametrize("cmd", ALLOWED)
def test_reads_and_the_own_code_of_the_logs_are_not_refused(repo, cmd):
    assert bash(repo, cmd) == 0, cmd


# ---- the gate files: SHIPPED SWITCHED OFF, the mechanism proven switched on (R7) ---------------------------------------------------

def test_R7_the_shipped_switch_is_off_and_says_so():
    cfg = json.loads(path_guard.GATE_CONFIG.read_text(encoding="utf-8"))
    assert cfg["enabled"] is False and "NOT ENFORCED" in cfg["note"]
    assert {".claude/settings.json", "explainer_engine/governance/**", "docs/layers/**"} <= set(cfg["paths"])
    assert not path_guard.gate_enabled()


GATE_FILES = [".claude/settings.json", "explainer_engine/governance/send_gate.py", "docs/layers/L9.json"]


@pytest.mark.parametrize("rel", GATE_FILES)
def test_R7_switched_off_an_edit_of_a_gate_file_is_not_enforced(repo, rel):
    assert write(repo, rel) == 0
    assert bash(repo, f"echo x >> {rel}") == 0


@pytest.mark.parametrize("rel", GATE_FILES)
def test_R7_switched_on_a_gate_file_changes_only_on_the_owners_recorded_word(repo, gate_on, rel):
    assert write(repo, rel) == 2
    assert write(repo, rel, tool="Edit") == 2
    assert bash(repo, f"echo x >> {rel}") == 2
    assert bash(repo, f"python3 -c \"open('{rel}','w').write('x')\"") == 2
    assert bash(repo, f"cat {rel}") == 0
    records.add("protected_config", rel, "cmsg_x", "ok", root=repo)
    assert write(repo, rel) == 0
    assert bash(repo, f"echo x >> {rel}") == 0


def test_R7_the_word_names_one_gate_file_only(repo, gate_on):
    records.add("protected_config", "docs/layers/L9.json", "cmsg_x", "ok", root=repo)
    assert write(repo, "docs/layers/L9.json") == 0
    assert write(repo, "explainer_engine/governance/send_gate.py") == 2
    assert write(repo, ".claude/settings.json") == 2


def test_R7_a_file_that_is_new_below_a_gate_directory_is_protected_too(repo, gate_on):
    assert write(repo, "explainer_engine/governance/brand_new.py") == 2
    assert write(repo, "docs/layers/L10.json") == 2
    assert write(repo, "docs/other.md") == 0


def test_R7_a_broken_or_missing_switch_file_counts_as_off(tmp_path, monkeypatch):
    for text in (None, "", "{", "[]", '{"enabled": "yes"}'):
        f = tmp_path / "g.json"
        f.unlink(missing_ok=True) if text is None else f.write_text(text, encoding="utf-8")
        monkeypatch.setattr(path_guard, "GATE_CONFIG", f)
        assert not path_guard.gate_enabled(), text


# ---- fail closed (the pre-* hooks of governance/hooks.py) ---------------------------------------------------------------------

@pytest.mark.parametrize("name", ["pre-bash", "pre-write", "pre-agent"])
def test_the_pre_hooks_fail_closed(name, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    monkeypatch.setitem(hooks.HOOKS, name, lambda event: 1 / 0)
    assert hooks.main([name]) == 2
    assert "failed closed" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["prompt", "statusline", "post-edit"])
def test_the_other_hooks_still_fail_open(name, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    monkeypatch.setitem(hooks.HOOKS, name, lambda event: 1 / 0)
    assert hooks.main([name]) == 0


def test_every_governance_pre_hook_command_in_settings_closes_when_it_cannot_start():
    d = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for g in d["hooks"]["PreToolUse"] for h in g["hooks"] if "governance.hooks pre-" in h["command"]]
    assert len(cmds) >= 3
    for c in cmds:
        assert "exit 2" in c, c
