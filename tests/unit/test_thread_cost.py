"""CC-1 (docs/ORCHESTRATION.md OR-38): the thread-cost rule measures a transcript, checks the handover file and refuses to end an
expensive turn until the one-line request is posted and the handover is written. Fabricated transcripts, no network."""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from explainer_engine.governance import thread_cost as tc  # noqa: E402

PHRASE = "I am expensive now: compact me or hand me over"
SID = "sess-1"


def cfg_dict(**kw) -> dict:
    cfg = json.loads((ROOT / "config" / "thread_cost.json").read_text(encoding="utf-8"))
    cfg["handover_dirs"] = ["jobs/_handover"]                      # relative: the tmp repo, never the real project files
    cfg.update(kw)
    return cfg


@pytest.fixture()
def repo(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "thread_cost.json").write_text(json.dumps(cfg_dict(context_tokens=1000, steps=5)), encoding="utf-8")
    return tmp_path


def assistant(i, tokens=100, side=False, tool=None, ts="2026-11-20T10:00:00Z"):
    content = [{"type": "text", "text": "x"}]
    if tool:
        content.append({"type": "tool_use", "name": tool[0], "input": tool[1]})
    o = {"type": "assistant", "uuid": f"u{i}", "timestamp": ts, "message": {"id": f"m{i}", "model": "mod", "content": content,
         "usage": {"input_tokens": tokens, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}
    if side:
        o["isSidechain"] = True
    return o


def write_transcript(path: Path, rows: list) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json at all\n", encoding="utf-8")
    return path


def handover(repo, body=None, session=SID):
    p = repo / "jobs" / "_handover" / f"HANDOVER_{session}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    body = body or ("# Goal\nfinish the cost rule and the tests for it\n# State\nhooks written, tests written, docs left to do\n"
                    "# Paths\nexplainer_engine/governance/thread_cost.py and config/thread_cost.json\n# Open questions\nnone for now\n")
    p.write_text(body, encoding="utf-8")
    return p


def event(tp, sid=SID):
    return {"transcript_path": str(tp), "session_id": sid}


def over_rows(n=6, tokens=100):
    return [assistant(i, tokens) for i in range(n)]


# ---- measure -------------------------------------------------------------------------------------------------------------------------

def test_measure_counts_context_and_distinct_steps(tmp_path):
    rows = [assistant(1, 100), assistant(1, 100), assistant(2, 700)]       # a repeated message id is one step
    m = tc.measure(write_transcript(tmp_path / "t.jsonl", rows), cfg_dict())
    assert m["steps"] == 2 and m["context_tokens"] == 700 and m["compactions"] == 0 and m["model"] == "mod"


def test_context_sums_input_cache_read_and_cache_creation(tmp_path):
    row = assistant(1)
    row["message"]["usage"] = {"input_tokens": 10, "cache_read_input_tokens": 200, "cache_creation_input_tokens": 3}
    assert tc.measure(write_transcript(tmp_path / "t.jsonl", [row]), cfg_dict())["context_tokens"] == 213


def test_compact_boundary_resets_steps_and_tokens(tmp_path):
    rows = over_rows(4, 900) + [{"type": "system", "subtype": "compact_boundary", "timestamp": "2026-11-20T11:00:00Z"}] + [assistant(10, 50)]
    m = tc.measure(write_transcript(tmp_path / "t.jsonl", rows), cfg_dict())
    assert (m["steps"], m["context_tokens"], m["compactions"], m["boundary_ts"]) == (1, 50, 1, "2026-11-20T11:00:00Z")


def test_sidechain_messages_are_not_counted(tmp_path):
    rows = [assistant(1, 100), assistant(2, 99999, side=True), assistant(3, 300, side=True)]
    m = tc.measure(write_transcript(tmp_path / "t.jsonl", rows), cfg_dict())
    assert m["steps"] == 1 and m["context_tokens"] == 100


def test_request_phrase_found_only_in_a_posting_tool_and_resets_at_the_boundary(tmp_path):
    post = ("mcp__hearthbot__post_message", {"text": PHRASE.upper() + "!"})
    other = ("Bash", {"command": f"echo '{PHRASE}'"})
    assert tc.measure(write_transcript(tmp_path / "a.jsonl", [assistant(1, tool=post)]), cfg_dict())["request_posted"]
    assert not tc.measure(write_transcript(tmp_path / "b.jsonl", [assistant(1, tool=other)]), cfg_dict())["request_posted"]
    rows = [assistant(1, tool=post), {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-11-20T11:00:00Z"}, assistant(2)]
    assert not tc.measure(write_transcript(tmp_path / "c.jsonl", rows), cfg_dict())["request_posted"]


# ---- config ----------------------------------------------------------------------------------------------------------------------------

def test_real_config_loads_and_is_the_one_place_of_the_limits():
    cfg = tc.load_config(ROOT)
    assert cfg["context_tokens"] == 150000 and cfg["steps"] == 300 and cfg["request_phrase"] == PHRASE


@pytest.mark.parametrize("patch", [{"steps": 0}, {"context_tokens": "9"}, {"sections": []}, {"handover_dirs": []}, {"request_phrase": " "}])
def test_bad_config_is_rejected(tmp_path, patch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "thread_cost.json").write_text(json.dumps(cfg_dict(**patch)), encoding="utf-8")
    with pytest.raises(tc.CostConfigError):
        tc.load_config(tmp_path)


# ---- handover problems -----------------------------------------------------------------------------------------------------------------

def test_handover_missing_then_fine(repo):
    cfg = tc.load_config(repo)
    path = tc.handover_file(repo, SID, cfg)
    assert "not written" in tc.handover_problems(path, cfg)[0]
    handover(repo)
    assert tc.handover_problems(path, cfg) == []


def test_handover_stale_after_compaction(repo):
    cfg = tc.load_config(repo)
    p = handover(repo)
    os.utime(p, (1_700_000_000, 1_700_000_000))
    assert any("older than the last compaction" in x for x in tc.handover_problems(p, cfg, "2026-11-20T11:00:00Z"))
    assert tc.handover_problems(p, cfg, None) == []


def test_handover_too_small_too_big_and_empty_section(repo):
    cfg = tc.load_config(repo)
    assert any("bytes (at least" in x for x in tc.handover_problems(handover(repo, "# Goal\nx\n"), cfg))
    assert any("bytes (at most" in x for x in tc.handover_problems(handover(repo, "# Goal\n" + "recap " * 3000), cfg))
    empty = "# Goal\ngoal text long enough to count here\n# State\n\n# Paths\nsome paths listed in this section, several of them in fact\n# Open questions\nnone yet for now, nothing else to ask the lead\n"
    probs = tc.handover_problems(handover(repo, empty), cfg)
    assert probs == ["section 'state' is missing or empty"]


# ---- hooks -----------------------------------------------------------------------------------------------------------------------------

def test_prompt_hook_silent_when_under_limit(repo, tmp_path):
    tp = write_transcript(tmp_path / "t.jsonl", over_rows(2))
    assert tc.prompt_hook(event(tp), repo) == ""


def test_prompt_hook_speaks_when_over_and_unsatisfied_then_goes_quiet(repo, tmp_path):
    rows = over_rows(6)
    tp = write_transcript(tmp_path / "t.jsonl", rows)
    text = tc.prompt_hook(event(tp), repo)
    assert "CC-1" in text and PHRASE in text and "HANDOVER_sess-1.md" in text
    handover(repo)
    rows.append(assistant(7, tool=("mcp__hearthbot__post_message", {"text": PHRASE})))
    write_transcript(tp, rows)
    assert tc.prompt_hook(event(tp), repo) == ""


def test_long_request_line_is_a_problem(repo, tmp_path):
    handover(repo)
    rows = over_rows(6) + [assistant(7, tool=("mcp__hearthbot__post_message", {"text": PHRASE + " " + "recap " * 200}))]
    st = tc.status(event(write_transcript(tmp_path / "t.jsonl", rows)), repo)
    assert st["over"] and not st["satisfied"] and any("characters" in p for p in st["problems"])


def test_stop_hook_refuses_twice_lets_go_after_three_and_logs(repo, tmp_path, capsys):
    ev = event(write_transcript(tmp_path / "t.jsonl", over_rows(6)))
    assert [tc.stop_hook(ev, repo) for _ in range(3)] == [2, 2, 2]
    assert "CC-1" in capsys.readouterr().err
    assert tc.stop_hook(ev, repo) == 0                              # the 4th refusal would exceed max_stop_blocks=3: let go
    rows = [json.loads(x) for x in (repo / "jobs" / "_cost" / "incidents.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["session"] == SID and rows[0]["reasons"]


def test_stop_hook_passes_once_satisfied_and_clears_the_counter(repo, tmp_path):
    rows = over_rows(6)
    tp = write_transcript(tmp_path / "t.jsonl", rows)
    assert tc.stop_hook(event(tp), repo) == 2
    handover(repo)
    rows.append(assistant(7, tool=("mcp__hearthbot__message_coordinator", {"text": PHRASE})))
    write_transcript(tp, rows)
    assert tc.stop_hook(event(tp), repo) == 0
    assert json.loads((repo / "jobs" / "_cost" / "stop_blocks.json").read_text(encoding="utf-8")) == {}


def test_stop_hook_passes_under_the_limit(repo, tmp_path):
    assert tc.stop_hook(event(write_transcript(tmp_path / "t.jsonl", over_rows(2))), repo) == 0


def test_hooks_fail_open_on_unreadable_transcript_or_bad_session(repo, tmp_path):
    assert tc.stop_hook({"transcript_path": str(tmp_path / "nope.jsonl"), "session_id": SID}, repo) == 0
    assert tc.stop_hook({}, repo) == 0
    tp = write_transcript(tmp_path / "t.jsonl", over_rows(6))
    assert tc.stop_hook(event(tp, "../evil"), repo) == 0 and tc.prompt_hook(event(tp, "../evil"), repo) == ""


def test_main_fails_open_on_bad_config(repo, tmp_path, monkeypatch, capsys):
    (repo / "config" / "thread_cost.json").write_text("{broken", encoding="utf-8")
    tp = write_transcript(tmp_path / "t.jsonl", over_rows(6))
    monkeypatch.setattr(tc, "root_dir", lambda root=None: Path(root) if root else repo)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event(tp))))
    assert tc.main(["stop"]) == 0
    assert "skipped" in capsys.readouterr().err


def test_main_rejects_unknown_command():
    with pytest.raises(SystemExit):
        tc.main(["nonsense"])


# ---- the CLI tool ----------------------------------------------------------------------------------------------------------------------

def test_tool_reports_and_exit_code_follow_the_limits(tmp_path, capsys):
    import thread_cost as tool
    tp = write_transcript(tmp_path / "t.jsonl", [assistant(1, 100)])
    assert tool.main([str(tp)]) == 0
    assert json.loads(capsys.readouterr().out)["steps"] == 1
    big = write_transcript(tmp_path / "b.jsonl", [assistant(1, 200_000)])
    assert tool.main([str(big)]) == 1
    assert tool.main([str(tmp_path / "missing.jsonl")]) == 2


def test_tool_finds_newest_transcript(tmp_path):
    import thread_cost as tool
    a = write_transcript(tmp_path / "p" / "old.jsonl", []) if (tmp_path / "p").mkdir() is None else None
    os.utime(a, (1, 1))
    b = write_transcript(tmp_path / "p" / "new.jsonl", [])
    assert tool.find_transcript(None, tmp_path) == b and tool.find_transcript("old", tmp_path) == a
