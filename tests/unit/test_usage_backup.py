"""P0b, OR-30: at 95 % of the 5-hour or the weekly limit the unfinished work is saved once per limit window ($0)."""
from __future__ import annotations

import json
import tarfile

import pytest

from _gov import ROOT, git, make_repo
from explainer_engine.governance import hooks, usage


def status_json(five=None, seven=None):
    rl = {}
    if five is not None:
        rl["five_hour"] = {"used_percentage": five, "resets_at": 1000}
    if seven is not None:
        rl["seven_day"] = {"used_percentage": seven, "resets_at": 2000}
    return {"model": {"display_name": "Sonnet 5.5"}, "effort": {"level": "high"}, "rate_limits": rl}


@pytest.fixture
def repo(tmp_path):
    r = make_repo(tmp_path / "r", git=True)
    cfg = json.loads((r / "config/model_routing.json").read_text())
    cfg["usage"]["backup_dir"] = str(tmp_path / "pf" / "_backup")  # parent exists below
    (tmp_path / "pf").mkdir()
    (r / "config/model_routing.json").write_text(json.dumps(cfg))
    return r


def test_record_keeps_only_the_windows_that_are_present(repo):
    assert "five_hour" in usage.record(status_json(five=40), repo)
    assert usage.current(repo)["five_hour"]["pct"] == 40
    out = usage.record({"model": {}}, repo)  # no rate_limits (API key login, or before the first reply)
    assert list(out) == ["at"]


def test_usage_goes_stale(repo):
    usage.record(status_json(five=99), repo, now=1_000_000)
    assert usage.current(repo, now=1_000_000 + 5 * 60) is not None
    assert usage.current(repo, now=1_000_000 + 11 * 60) is None


def test_94_does_not_back_up_95_and_99_do(repo):
    assert usage.backup_if_over(usage.record(status_json(five=94, seven=10), repo), repo, push=False) is None
    r = usage.backup_if_over(usage.record(status_json(five=95), repo), repo, push=False)
    assert r and r["reason"] == "usage five_hour 95%"
    assert usage.over({"seven_day": {"pct": 99, "resets_at": 5}}, 95) == [("seven_day", 99, 5)]


def test_backup_saves_the_diff_the_untracked_files_and_the_state(repo, tmp_path):
    (repo / "docs/blueprint/STATUS.md").write_text("changed\n", encoding="utf-8")
    (repo / "new_work.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "jobs").mkdir(exist_ok=True)
    (repo / "jobs/active_phase.json").write_text('{"phase": "P0b"}', encoding="utf-8")
    (repo / "jobs/P0b").mkdir()
    (repo / "jobs/P0b/attempts.json").write_text("[]", encoding="utf-8")
    r = usage.backup("test", repo, push=False)
    dest = tmp_path / "pf/_backup/work" / r["dest"].split("/")[-1]
    assert str(dest) == r["dest"]
    assert "changed" in (dest / "changes.diff").read_text(encoding="utf-8")
    assert "new_work.py" in tarfile.open(dest / "untracked.tar.gz").getnames()
    assert (dest / "job_attempts.json").exists()
    state = json.loads((dest / "state.json").read_text())
    assert state["branch"] == "work" and state["phase"] == "P0b" and state["push"].startswith("skipped")


def test_backup_runs_once_per_limit_window(repo):
    a = usage.backup_if_over(usage.record(status_json(five=96), repo), repo, push=False)
    b = usage.backup_if_over(usage.record(status_json(five=97), repo), repo, push=False)
    assert a["reason"] and "already" in b["skipped"]
    c = usage.backup_if_over(usage.record(status_json(five=50, seven=96), repo), repo, push=False)
    assert c and "seven_day" in c["reason"]  # another window is another backup


def test_a_wip_commit_is_pushed_on_a_work_branch_never_on_main(repo, tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    (repo / "wip.txt").write_text("unfinished\n", encoding="utf-8")
    r = usage.backup("limit", repo)
    assert r["commit"] == "ok" and r["push"] == "ok"
    assert "WIP auto-backup: limit" in git(repo, "log", "-1", "--format=%B")
    assert "wip.txt" in git(remote, "ls-tree", "-r", "--name-only", "work")
    git(repo, "checkout", "-q", "-b", "main")
    (repo / "wip2.txt").write_text("x", encoding="utf-8")
    r2 = usage.backup("limit-main", repo)
    assert r2["push"].startswith("skipped") and "main" not in git(remote, "branch", "--list", "main")


def test_statusline_prints_usage_and_starts_the_backup_only_over_the_line(repo, capsys, monkeypatch):
    started = []
    monkeypatch.setattr(hooks.subprocess, "Popen", lambda *a, **k: started.append(a))
    assert hooks.statusline(status_json(five=40, seven=10), repo) == 0
    assert "5h 40% · 7d 10%" in capsys.readouterr().out and not started
    hooks.statusline(status_json(five=96), repo)
    assert "5h 96% · 7d n/a" in capsys.readouterr().out and started
    hooks.statusline({"model": {"display_name": "X"}}, repo)  # an API-key login has no rate_limits
    assert "5h n/a" in capsys.readouterr().out


def test_the_stop_failure_hook_backs_up_on_rate_limit(repo, monkeypatch):
    seen = []
    monkeypatch.setattr(usage, "backup", lambda reason, root=None, **k: seen.append(reason) or {"dest": "d"})
    assert hooks.stop_failure({"error": "rate_limit"}, repo) == 0 and "rate_limit" in seen[0]


def test_the_settings_wire_the_statusline_and_the_stop_failure_hook():
    s = json.loads((ROOT / ".claude/settings.json").read_text())
    assert "governance.hooks statusline" in s["statusLine"]["command"] and s["statusLine"]["refreshInterval"] <= 60
    assert s["hooks"]["StopFailure"][0]["matcher"] == "rate_limit"
