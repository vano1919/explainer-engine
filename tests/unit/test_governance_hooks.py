"""P0b: every hook on fake events, deny and allow cases ($0). Hooks act on a throw-away repo (``root``)."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time

import pytest

from _gov import ROOT, git, make_repo
from explainer_engine.governance import hooks, records, status


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path / "r", git=True)


def bash(repo, cmd):
    return hooks.pre_bash({"tool_input": {"command": cmd}}, repo)


def write(repo, path, effort=None, tool="Write"):
    ev = {"tool_name": tool, "tool_input": {"file_path": path}}
    if effort:
        ev["effort"] = {"level": effort}
    return hooks.pre_write(ev, repo)


# ---- Bash --------------------------------------------------------------------------------------------------------------------

def test_force_push_needs_a_backup_tag_on_the_remote_tip(repo, capsys):
    git(repo, "update-ref", "refs/remotes/origin/work", "HEAD")
    assert bash(repo, "git push --force origin work") == 2
    assert "backup" in capsys.readouterr().err
    git(repo, "tag", "backup/work-1", "HEAD")
    assert bash(repo, "git push --force origin work") == 0
    assert bash(repo, "git push --force-with-lease origin work") == 0
    assert bash(repo, "git push origin +work:work") == 0  # the tip is backed up


def test_force_push_of_a_branch_the_remote_does_not_have_is_harmless_but_a_delete_is_not(repo):
    assert bash(repo, "git push -f -u origin work") == 0  # no remote tip is known: nothing is overwritten
    assert bash(repo, "git push origin --delete work") == 2


def test_force_push_variants_are_all_seen(repo):
    git(repo, "update-ref", "refs/remotes/origin/work", "HEAD")
    for cmd in ("git push -f origin work", "git push --force-with-lease=work origin work", "git push origin +work",
                "git push origin --delete work", "git push origin :work", "git push --mirror origin",
                "cd x && git push -f"):
        assert bash(repo, cmd) == 2, cmd


def test_plain_push_and_other_git_commands_pass(repo):
    for cmd in ("git push -u origin work", "git status", "git branch -d old", "git log --oneline", "git commit -m 'git push --force'"):
        assert bash(repo, cmd) == 0, cmd


def test_branch_force_delete_needs_a_backup_tag(repo):
    git(repo, "branch", "old")
    assert bash(repo, "git branch -D old") == 2
    assert bash(repo, "git branch --delete --force old") == 2
    git(repo, "tag", "backup/old", "old")
    assert bash(repo, "git branch -D old") == 0


def test_shell_writes_to_protected_config_need_the_creators_word(repo):
    for cmd in ("echo '{}' > config/spend_caps.json", "sed -i 's/1/2/' config/spend_caps.json", "tee config/model_routing.json",
                "cp /tmp/x config/spend_caps.json", "python3 -c \"open('config/spend_caps.json','w').write('{}')\"",
                "git checkout config/spend_caps.json"):
        assert bash(repo, cmd) == 2, cmd
    for cmd in ("cat config/spend_caps.json", "jq .runpod_usd config/spend_caps.json", "cat config/spend_caps.json > /tmp/copy.json"):
        assert bash(repo, cmd) == 0, cmd
    records.add("protected_config", "config/spend_caps.json", "cmsg_x", "ვანო: დააყენე 31", root=repo)
    assert bash(repo, "sed -i 's/1/2/' config/spend_caps.json") == 0
    assert bash(repo, "sed -i 's/1/2/' config/model_routing.json") == 2  # the word names one file


# ---- Write / Edit ------------------------------------------------------------------------------------------------------------

def test_no_top_level_engine_folder(repo):
    assert write(repo, str(repo / "engine" / "x.py")) == 2
    assert write(repo, "engine/y.json") == 2
    assert write(repo, str(repo / "explainer_engine" / "engine.py")) == 0
    assert write(repo, str(repo / "docs" / "engine" / "a.md")) == 0


def test_protected_config_edit_needs_a_fresh_record(repo):
    p = str(repo / "config" / "spend_caps.json")
    assert write(repo, p, tool="Edit") == 2
    assert write(repo, str(repo / "config" / "model_routing.json")) == 2
    now = time.time()
    records.add("protected_config", "config/spend_caps.json", "cmsg_x", "ვანო: კი", root=repo, now=now - 7200)
    assert write(repo, p) == 2  # a stale word
    records.add("protected_config", "config/spend_caps.json", "cmsg_y", "ვანო: კი", root=repo)
    assert write(repo, p) == 0


def test_python_edits_refuse_xhigh_and_max_without_an_override(repo, monkeypatch):
    monkeypatch.delenv("CLAUDE_EFFORT", raising=False)
    f = str(repo / "explainer_engine" / "x.py")
    assert write(repo, f, "high") == 0 and write(repo, f, "medium") == 0 and write(repo, f) == 0
    assert write(repo, f, "xhigh") == 2 and write(repo, f, "max") == 2
    assert write(repo, str(repo / "docs" / "a.md"), "max") == 0  # only code
    monkeypatch.setenv("CLAUDE_EFFORT", "max")
    assert write(repo, f) == 2  # the environment variable is read when the event has no effort
    records.add("effort_override", "*", "cmsg_z", "ვანო: max კოდზე", root=repo)
    assert write(repo, f, "max") == 0


def test_a_path_outside_the_repo_is_not_ours(repo, tmp_path):
    assert write(repo, str(tmp_path / "elsewhere" / "engine" / "x.py")) == 0


# ---- Agent -------------------------------------------------------------------------------------------------------------------

def agent(repo, kind, model=None):
    ti = {"subagent_type": kind, "prompt": "x"}
    if model:
        ti["model"] = model
    return hooks.pre_agent({"tool_name": "Agent", "tool_input": ti}, repo)


def test_fable_is_refused_outside_the_story_stages(repo):
    assert agent(repo, "beat-writer", "fable") == 2
    assert agent(repo, "scene-writer", "fable") == 2  # the flag is off: only his word turns it on
    assert agent(repo, "general-purpose", "claude-fable-5-1") == 2
    assert agent(repo, "scene-writer", "sonnet") == 0 and agent(repo, "beat-writer") == 0
    cfg = json.loads((repo / "config" / "model_routing.json").read_text())
    cfg["fable_story_stages"]["enabled"] = True
    (repo / "config" / "model_routing.json").write_text(json.dumps(cfg))
    assert agent(repo, "scene-writer", "fable") == 0 and agent(repo, "story-architect", "fable") == 0
    assert agent(repo, "beat-writer", "fable") == 2


def test_a_critic_runs_only_on_opus(repo):
    assert agent(repo, "script-critic", "sonnet") == 2
    assert agent(repo, "lora-checkpoint-judge", "haiku") == 2
    assert agent(repo, "script-critic", "opus") == 0 and agent(repo, "script-critic", "claude-opus-5-5") == 0
    assert agent(repo, "script-critic") == 0  # the frontmatter decides (pinned by test_agent_governance)


# ---- model switch ------------------------------------------------------------------------------------------------------------

def test_model_switch_needs_the_creators_recorded_word(repo, capsys):
    ev = {"from_model": "claude-opus-5-5", "to_model": "claude-sonnet-5-5"}
    assert hooks.pre_switch(ev, repo) == 2
    assert "creator" in capsys.readouterr().err
    records.add("model_switch", "claude-opus-5-5", "cmsg_a", "ვანო: კი", root=repo)
    assert hooks.pre_switch(ev, repo) == 2  # the word was for another model
    records.add("model_switch", "sonnet", "cmsg_b", "ვანო: კი", root=repo)
    assert hooks.pre_switch(ev, repo) == 0
    old = make_repo(repo.parent / "old")
    records.add("model_switch", "*", "cmsg_c", "ვანო: კი", root=old, now=time.time() - 16 * 60)
    assert hooks.pre_switch(ev, old) == 2  # 16 minutes is too old


def test_a_record_needs_a_message_id_and_a_quote(repo):
    with pytest.raises(ValueError):
        records.add("model_switch", "*", "", "x", root=repo)
    with pytest.raises(ValueError):
        records.add("model_switch", "*", "cmsg_1", " ", root=repo)
    with pytest.raises(ValueError):
        records.add("anything", "*", "cmsg_1", "x", root=repo)


def test_the_creators_own_model_commands_pass_but_an_sdk_or_remote_switch_needs_his_word(repo):
    ev = {"from_model": "claude-opus-5-5", "to_model": "claude-sonnet-5-5"}
    assert hooks.pre_switch(ev | {"source": "command"}, repo) == 0  # /model typed at his keyboard
    assert hooks.pre_switch(ev | {"source": "picker"}, repo) == 0
    assert hooks.pre_switch(ev | {"source": "sdk"}, repo) == 2  # the hearth tool, Remote Control, an SDK host
    assert hooks.pre_switch(ev, repo) == 2  # no source: treated as not his
    records.add("model_switch", "sonnet", "cmsg_b", "ვანო: კი", root=repo)
    assert hooks.pre_switch(ev | {"source": "sdk"}, repo) == 0


def test_post_switch_logs_every_switch_untracked_with_the_message_id(repo):
    records.add("model_switch", "sonnet", "cmsg_77", "ვანო: კი", root=repo)
    hooks.post_switch({"from_model": "a", "to_model": "claude-sonnet-5-5", "source": "sdk"}, repo)
    hooks.post_switch({"from_model": "b", "to_model": "claude-opus-5-5", "source": "auto"}, repo)  # an automatic fallback
    rows = [json.loads(l) for l in (repo / "jobs" / "switch_log.jsonl").read_text().splitlines()]
    assert rows[0]["message_id"] == "cmsg_77" and rows[0]["source"] == "sdk" and rows[1]["message_id"] is None
    assert all(l.get("kind") != "switch" for l in status.log(repo))  # the tracked routing_log stays clean


def test_full_ref_names_do_not_bypass_the_force_push_guard(repo):
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/feat", "HEAD")
    for cmd in ("git push --force origin HEAD:refs/heads/main", "git push -f origin work:refs/heads/feat",
                "git push origin +refs/heads/feat:refs/heads/feat", "git push --force origin refs/heads/main",
                "git -C . push -f origin HEAD:main", "git push --force origin refs/heads/feat:feat"):
        assert bash(repo, cmd) == 2, cmd
    git(repo, "tag", "backup/main-1", "origin/main")
    assert bash(repo, "git push --force origin HEAD:refs/heads/main") == 0


def test_wrapper_commands_do_not_hide_a_force_push(repo):
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    for cmd in ("timeout 60 git push --force origin main", "env GIT_TRACE=1 git push -f origin main", "sudo git push -f origin main",
                "nice -n 5 git push -f origin main", "nohup git push --force origin main", "command git push -f origin main",
                "time git branch -D feat-none", "env -i FOO=1 timeout 30s git push -f origin main"):
        git(repo, "branch", "-f", "feat-none") if "feat-none" in cmd else None
        assert bash(repo, cmd) == 2, cmd
    for cmd in ("timeout -s KILL 60 git push -f origin main", "sudo -u root git push -f origin main", "bash -lc 'git push -f origin main'",
                "eval \"git push --force origin main\"", "eval git push -f origin main", "echo x | xargs git push -f origin main",
                "env -u FOO PATH=/bin git push -f origin main"):
        assert bash(repo, cmd) == 2, cmd
    assert bash(repo, "bash -c \"git push -f origin main\"") == 2  # a quoted script is read too
    assert bash(repo, "sh -c 'echo hi; sudo git push --force origin main'") == 2
    assert bash(repo, "bash -c 'git status'") == 0
    assert bash(repo, "timeout 60 git push -u origin work") == 0
    assert bash(repo, "echo timeout git push -f origin main") == 0  # an argument of echo, not a command


def test_text_inside_a_commit_message_is_not_a_command(repo):
    git(repo, "update-ref", "refs/remotes/origin/work", "HEAD")
    for cmd in ("git commit -m \"note: never git push -f here\"", "git commit -m 'explain branch -D usage'",
                "echo 'git push --force origin work'", "git log --grep='branch -D'"):
        assert bash(repo, cmd) == 0, cmd
    assert bash(repo, "git commit -m 'x'\ngit push --force origin work") == 2  # a real second line still counts
    assert bash(repo, "echo hi && git push -f origin work") == 2
    assert bash(repo, "FOO=1 git push -f origin work") == 2


def test_protected_shell_guard_reads_pass_and_more_writers_are_seen(repo):
    for cmd in ("cp config/spend_caps.json /tmp/x", "grep write_text config/spend_caps.json", "cat config/spend_caps.json | jq .",
                "python3 -c \"import json;print(json.load(open('config/spend_caps.json')))\""):
        assert bash(repo, cmd) == 0, cmd
    for cmd in ("perl -pi -e 's/1/2/' config/spend_caps.json", "jq .x=1 config/spend_caps.json | sponge config/spend_caps.json",
                "Set-Content config\\spend_caps.json '{}'", "cp /tmp/x config\\spend_caps.json", "Out-File -FilePath config/model_routing.json",
                "python3 -c \"from pathlib import Path; Path('config/spend_caps.json').write_text('{}')\""):
        assert bash(repo, cmd) == 2, cmd


def test_a_wildcard_word_never_unlocks_a_protected_file(repo):
    with pytest.raises(ValueError):
        records.add("protected_config", "*", "cmsg_1", "ვანო: კი", root=repo)
    (repo / "jobs").mkdir(exist_ok=True)
    (repo / "jobs" / "creator_ok.jsonl").write_text(json.dumps({"action": "protected_config", "target": "*", "message_id": "m", "at": time.time()}) + "\n")
    assert write(repo, str(repo / "config" / "spend_caps.json")) == 2  # a hand-written wildcard line does not count either


def test_a_critic_spawned_without_a_model_is_checked_against_its_agent_file(repo):
    page = repo / ".claude" / "agents"
    page.mkdir(parents=True)
    (page / "script-critic.md").write_text("---\nname: script-critic\nmodel: sonnet\n---\n", encoding="utf-8")
    assert agent(repo, "script-critic") == 2
    (page / "script-critic.md").write_text("---\nname: script-critic\nmodel: opus\n---\n", encoding="utf-8")
    assert agent(repo, "script-critic") == 0


# ---- post-edit ---------------------------------------------------------------------------------------------------------------

def edit_event(repo, rel):
    return {"tool_name": "Write", "tool_input": {"file_path": str(repo / rel)}}


def test_post_edit_feeds_back_findings(repo, capsys):
    (repo / "bad.py").write_text("def f(:\n", encoding="utf-8")
    assert hooks.post_edit(edit_event(repo, "bad.py"), repo) == 2 and "syntax error" in capsys.readouterr().err
    (repo / "ok.py").write_text("x = 1\n", encoding="utf-8")
    assert hooks.post_edit(edit_event(repo, "ok.py"), repo) == 0
    (repo / "bad.json").write_text("{", encoding="utf-8")
    assert hooks.post_edit(edit_event(repo, "bad.json"), repo) == 2
    cfg = json.loads((repo / "config" / "model_routing.json").read_text())
    cfg["agents"]["script-critic"]["model"] = "sonnet"
    (repo / "config" / "model_routing.json").write_text(json.dumps(cfg))
    assert hooks.post_edit(edit_event(repo, "config/model_routing.json"), repo) == 2
    assert hooks.post_edit(edit_event(repo, "missing.py"), repo) == 0


def test_post_edit_checks_the_blueprint_files(repo):
    p = repo / "docs/blueprint/decision_queue.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["cards"][0].pop("owner")
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    assert hooks.post_edit(edit_event(repo, "docs/blueprint/decision_queue.json"), repo) == 2


# ---- prompt / stop -----------------------------------------------------------------------------------------------------------

def test_prompt_prints_the_reminder(repo, capsys):
    assert hooks.prompt({}, repo) == 0
    out = capsys.readouterr().out
    assert "owner=creator" in out and "S0-S4" in out


def set_state(repo, phase, state):
    p = repo / "docs/blueprint/phases.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for r in d["phases"]:
        if r["id"] == phase:
            r["state"], r["pr"] = state, "#1"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def test_stop_refuses_a_done_phase_without_its_log_line(repo, capsys):
    assert hooks.stop({}, repo) == 0
    set_state(repo, "P0c", "done")
    assert hooks.stop({}, repo) == 2 and "P0c" in capsys.readouterr().err
    assert hooks.stop({"stop_hook_active": True}, repo) == 0
    status.append_log({"kind": "phase", "phase": "P0c", "level": "S2", "model": "claude-sonnet-5-5", "effort": "medium", "result": "x"}, repo)
    assert hooks.stop({}, repo) == 0


def test_stop_checks_the_active_phase_checklist(repo, capsys):
    p = repo / "docs/blueprint/phases.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for r in d["phases"]:
        if r["id"] == "P0c":
            r["state"], r["pr"] = "review", "#1"
            r["checklist"] = {"paths": ["docs/research/AGENT_AB_2026-10.md"], "tests": [], "progress": "P0c"}
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    status.append_log({"kind": "phase", "phase": "P0c", "level": "S2", "model": "m", "effort": "medium", "result": "x"}, repo)
    (repo / "jobs").mkdir()
    (repo / "jobs" / "active_phase.json").write_text('{"phase": "P0c"}', encoding="utf-8")
    assert hooks.stop({}, repo) == 2
    err = capsys.readouterr().err
    assert "required path missing" in err and "PROGRESS" in err
    (repo / "docs/research").mkdir()
    (repo / "docs/research/AGENT_AB_2026-10.md").write_text("x", encoding="utf-8")
    (repo / "docs/PROGRESS.md").write_text("## P0c done\n", encoding="utf-8")
    assert hooks.stop({}, repo) == 0


def test_stop_runs_the_listed_tests(repo, capsys):
    (repo / "t_ok.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (repo / "t_bad.py").write_text("def test_a():\n    assert False\n", encoding="utf-8")
    assert hooks._tests_pass(repo, ["t_ok.py"]) is None
    assert "failing" in hooks._tests_pass(repo, ["t_bad.py"])


# ---- fail open + the real process --------------------------------------------------------------------------------------------

def test_a_broken_hook_fails_open_and_garbage_stdin_is_ignored(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    monkeypatch.setitem(hooks.HOOKS, "pre-bash", lambda event: 1 / 0)
    assert hooks.main(["pre-bash"]) == 0
    assert "skipped" in capsys.readouterr().err


def test_the_real_process_denies_with_exit_2(tmp_path):
    repo = make_repo(tmp_path / "r", git=True)
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "CLAUDE_PROJECT_DIR": str(repo), "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "-m", "explainer_engine.governance.hooks", "pre-write"],
                       input=json.dumps({"tool_input": {"file_path": str(repo / "engine" / "x.py")}}), capture_output=True,
                       text=True, cwd=repo, env=env)
    assert r.returncode == 2 and "engine" in r.stderr
