"""T2.7: the sealed send logs, the tool-level hook (post_message attachments, GitHub, Drive, merges), pushes that name no file."""
from __future__ import annotations

import json
import shutil

import pytest

from explainer_engine.governance import records
from explainer_engine.governance import send_gate as SG
from explainer_engine.governance import send_hook as H
from test_owner_requirements import entry, put, registry, root  # noqa: F401
from test_send_hook import MSG, bash, env, refused, upload  # noqa: F401


def tool(name, **inp):
    return {"tool_name": name, "tool_input": inp}


# ---- sealed logs -----------------------------------------------------------------------------------------------------------

def test_a_legitimate_row_after_a_hand_written_line_still_counts(env):
    root, good, bad = env
    SG.run("L9", [good], root=root)
    log = root / SG.RECORDS
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"layer": "L9", "status": "PASS", "files": [{"path": str(bad), "sha256": SG.sha256(bad)}], "at": 1}) + "\n")
    SG.run("L9", [bad], root=root, owner_asked=MSG)
    assert SG.passing_record(good, root=root) is not None
    assert SG.passing_record(bad, root=root)["label"]["owner_asked"] == MSG


def test_an_edited_row_and_every_row_after_a_deleted_one_are_ignored(env):
    root, good, bad = env
    SG.run("L9", [good], root=root)
    SG.run("L9", [bad], root=root, owner_asked=MSG)
    log = root / SG.RECORDS
    lines = log.read_text(encoding="utf-8").splitlines()
    log.write_text("\n".join([lines[0].replace('"PASS"', '"PASS" ') .replace("mmmm", "mmmm"), lines[1]]) + "\n", encoding="utf-8")
    # the first row is the same JSON with a space: its seal is of the canonical body, so it still fits; the second chains to it
    assert SG.passing_record(good, root=root) is not None
    row = json.loads(lines[0])
    row["files"][0]["sha256"] = "0" * 64
    log.write_text(json.dumps(row) + "\n" + lines[1] + "\n", encoding="utf-8")
    assert SG.passing_record(good, root=root) is None                                           # an edited row no longer fits
    assert SG.passing_record(bad, root=root) is None                                            # nor does anything chained after it
    log.write_text(lines[1] + "\n", encoding="utf-8")                                           # the first row deleted
    assert SG.passing_record(bad, root=root) is None


def test_the_quarantine_is_in_both_sealed_logs(env):
    root, _, bad = env
    SG.quarantine([bad], "let go", root=root)
    assert SG.quarantined(SG.sha256(bad), root=root)
    (root / SG.QUARANTINE).unlink()
    assert SG.quarantined(SG.sha256(bad), root=root)                                            # the records log still says so


# ---- the tool hook ---------------------------------------------------------------------------------------------------------

def test_attaching_an_unmeasured_trial_file_to_a_message_is_refused(env):
    root, good, bad = env
    ev = tool("mcp__hearthbot__post_message", text="here", attached_outputs=[{"kind": "file", "ref": str(good)}])
    assert "no passing send record" in refused(H.pre_tool, ev, root=root)
    SG.run("L9", [good], root=root)
    H.pre_tool(ev, root=root)
    refused(H.pre_tool, tool("mcp__hearthbot__post_message", text="x", attached_outputs=[{"kind": "file", "ref": str(bad)}]), root=root)


def test_a_message_without_files_and_a_log_attachment_pass(env):
    root, _, _ = env
    log = root / "logs" / "run.txt"
    log.parent.mkdir()
    log.write_text("log", encoding="utf-8")
    H.pre_tool(tool("mcp__hearthbot__post_message", text="done"), root=root)
    H.pre_tool(tool("mcp__hearthbot__post_message", text="done", attached_outputs=[{"kind": "file", "ref": str(log)}]), root=root)
    H.pre_tool(tool("mcp__hearthbot__post_message", text="done", attached_outputs=[{"kind": "link", "ref": "https://huggingface.co/x"}]), root=root)


def test_a_copy_of_a_trial_file_sent_by_another_route_is_refused(env):
    root, _, bad = env
    neutral = root / "logs" / "summary.txt"
    neutral.parent.mkdir()
    shutil.copy(bad, neutral)
    refused(H.pre_tool, tool("mcp__Google_Drive__create_file", title="x", file_path=str(neutral)), root=root)
    refused(H.pre_tool, tool("mcp__github__push_files", files=[{"path": str(bad), "content": "x"}]), root=root)


@pytest.mark.parametrize("name", ["mcp__github__merge_pull_request", "mcp__github__enable_pr_auto_merge"])
def test_a_merge_needs_the_owners_recorded_word_for_that_pull_request(env, name):
    root, _, _ = env
    assert "merge_approval" in refused(H.pre_tool, tool(name, owner="o", repo="r", pullNumber=219), root=root)
    records.add("merge_approval", "219", "cmsg_abc", "merge it", root=root)
    H.pre_tool(tool(name, owner="o", repo="r", pullNumber=219), root=root)
    refused(H.pre_tool, tool(name, owner="o", repo="r", pullNumber=220), root=root)             # the word names one pull request


@pytest.mark.parametrize("target", ["*", "all", "", "219,220", "PR-1"])
def test_a_merge_approval_names_one_pull_request(tmp_path, target):
    with pytest.raises(ValueError):
        records.add("merge_approval", target, "cmsg_abc", "ok", root=tmp_path)


def test_the_tool_hook_closes_on_a_broken_event(monkeypatch):
    import io
    import sys
    monkeypatch.setattr(sys, "stdin", io.StringIO("{nope"))
    assert H.main(["pre-tool"]) == 2


# ---- pushes and uploads that name no file ---------------------------------------------------------------------------------------

def test_a_push_is_judged_by_the_trial_outputs_it_would_send(env):
    root, good, bad = env
    refused(H.pre_bash, bash("git push origin main"), root=root)
    SG.run("L9", [good], root=root)
    SG.run("L9", [bad], root=root, owner_asked=MSG)
    H.pre_bash(bash("git push origin main"), root=root)


def test_a_push_with_no_layer_named_trial_file_passes(root):
    H.pre_bash(bash("git push origin main"), root=root)
