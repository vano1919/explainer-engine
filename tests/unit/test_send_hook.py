"""Spec section 7.1: the send hooks refuse an upload or a turn end with trial outputs that no validator measured, and fail closed
when the hook itself breaks. Fixtures: a fake failing output blocked, a fake passing one allowed, a broken hook closed. $0."""
from __future__ import annotations

import io
import json
import os
import time
from datetime import datetime, timezone

import pytest

from explainer_engine.governance import layer_gate as LG
from explainer_engine.governance import send_gate as SG
from explainer_engine.governance import send_hook as H
from test_owner_requirements import entry, put, registry, root  # noqa: F401 (root is a fixture)
from test_send_gate import VALIDATOR

MSG = "cmsg_01Hnu5zB86sjUj5GtTgaUkPW1oFAyBSLLgTCU7KMSLutpZ"


@pytest.fixture
def env(root):
    (root / "explainer_engine" / "validators" / "living.py").write_text(VALIDATOR, encoding="utf-8")
    (root / "tests" / "unit" / "test_living.py").write_text("def test_living_motion():\n    assert True\n\ndef test_living_motion_fails():\n    assert True\n", encoding="utf-8")
    put(root, registry(entry(1)))
    d = root / "out" / "trials" / "L9"
    d.mkdir(parents=True)
    good, bad = d / "good.txt", d / "bad.txt"
    good.write_text("mmmm", encoding="utf-8")
    bad.write_text("m", encoding="utf-8")
    return root, good, bad


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def upload(f):
    return f'python -c "from huggingface_hub import HfApi; HfApi().upload_file(path_or_fileobj=\'{f}\', path_in_repo=\'x/y.txt\')"'


def refused(fn, *a, **kw):
    with pytest.raises(H.Refused) as e:
        fn(*a, **kw)
    return str(e.value)


# ---- pre-bash: uploads ---------------------------------------------------------------------------------------------------------

def test_a_failing_output_is_blocked_and_a_passing_one_is_allowed(env):
    root, good, bad = env
    assert "no passing send record" in refused(H.pre_bash, bash(upload(good)), root=root)    # not measured yet
    SG.run("L9", [good], root=root)
    SG.run("L9", [bad], root=root)
    H.pre_bash(bash(upload(good)), root=root)                                                  # measured and PASS: allowed
    assert "no passing send record" in refused(H.pre_bash, bash(upload(bad)), root=root)       # measured and FAIL: blocked
    SG.run("L9", [bad], root=root, owner_asked=MSG)
    H.pre_bash(bash(upload(bad)), root=root)                                                   # labelled with the owner's word: allowed


def test_a_changed_file_needs_a_new_record(env):
    root, good, _ = env
    SG.run("L9", [good], root=root)
    good.write_text("mmmmmm", encoding="utf-8")
    refused(H.pre_bash, bash(upload(good)), root=root)


def test_a_log_or_a_vault_file_is_not_in_scope(env):
    root, _, _ = env
    log = root / "logs" / "run.txt"
    log.parent.mkdir()
    log.write_text("no marks at all", encoding="utf-8")
    H.pre_bash(bash(upload(log)), root=root)
    H.pre_bash(bash("ls -la out/trials/L9"), root=root)                                         # not an upload
    H.pre_bash(bash("cat out/trials/L9/bad.txt"), root=root)


def test_a_trial_output_must_name_its_layer(env):
    root, good, _ = env
    odd = root / "out" / "trials" / "misc.txt"
    odd.write_text("mmmm", encoding="utf-8")
    assert "names its layer" in refused(H.pre_bash, bash(upload(odd)), root=root)


def test_an_upload_that_names_a_trial_path_that_does_not_resolve_is_refused(env):
    root, _, _ = env
    refused(H.pre_bash, bash("hf upload vano1919/tmr-artifacts $OUT/trials/L9/ghost.png x/ghost.png"), root=root)


def test_a_folder_upload_checks_every_file_under_it(env):
    root, good, bad = env
    SG.run("L9", [good], root=root)
    msg = refused(H.pre_bash, bash(upload(good.parent)), root=root)                            # bad.txt has no record
    assert "bad.txt" in msg and "good.txt" not in msg


# ---- pre-bash: trial commands --------------------------------------------------------------------------------------------------

@pytest.mark.usefixtures("real_layer_gate")
def test_a_trial_command_needs_its_layers(env, monkeypatch):
    root, _, _ = env
    assert "L12" in refused(H.pre_bash, bash("python -m explainer_engine.training.pods.ltx.scene_run job scene.json spec.json"), root=root)
    assert "L9" in refused(H.pre_bash, bash("python -m explainer_engine.episode run episodes/x --stage pictures"), root=root)
    H.pre_bash(bash("python -m explainer_engine.episode status episodes/x"), root=root)
    from explainer_engine.governance import records
    for layer in ("L9", "L10", "L11", "L16"):
        records.add("layer_waiver", layer, MSG, "go on", root=root)
    H.pre_bash(bash("python -m explainer_engine.episode run episodes/x --stage pictures"), root=root)


def test_the_stages_up_to_the_target_are_all_needed():
    sc = H.scope()
    assert set(LG.STAGE_LAYERS["script"]) <= set(H.trial_layers("python -m explainer_engine.episode run e --to clips", sc))
    assert set(H.trial_layers("python -m explainer_engine.episode run e --stage clips", sc)) == set(LG.STAGE_LAYERS["clips"])
    assert H.trial_layers("echo hello", sc) == ()
    for talk in ("grep -rn scene_run explainer_engine", "git commit -m 'scene_run and python -m explainer_engine.episode run'",
                 "cat explainer_engine/episode/run.py"):
        assert H.trial_layers(talk, sc) == (), talk                                              # a word in a command is not a run


# ---- stop and subagent-stop ---------------------------------------------------------------------------------------------------

def transcript(root, files, *, started=None):
    started = started if started is not None else time.time() - 60
    iso = lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat()                       # noqa: E731
    rows = [{"type": "user", "timestamp": iso(started), "message": {"role": "user", "content": "make the trial"}}]
    for f in files:
        rows.append({"type": "assistant", "timestamp": iso(started + 5), "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": str(f), "content": "x"}}]}})
        rows.append({"type": "user", "timestamp": iso(started + 6), "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "ok"}]}})
    p = root / "transcript.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return p


def test_a_turn_that_wrote_unchecked_trial_outputs_cannot_end(env):
    root, good, bad = env
    ev = {"transcript_path": str(transcript(root, [good, bad])), "session_id": "s1"}
    msg = refused(H.stop, ev, root=root)
    assert "good.txt" in msg and "bad.txt" in msg
    SG.run("L9", [good], root=root)
    SG.run("L9", [bad], root=root, owner_asked=MSG)
    H.stop(ev, root=root)                                                                      # every output has its record


def test_a_turn_without_trial_outputs_ends(env):
    root, _, _ = env
    other = root / "notes.txt"
    other.write_text("hello", encoding="utf-8")
    H.stop({"transcript_path": str(transcript(root, [other])), "session_id": "s2"}, root=root)
    H.stop({"transcript_path": str(transcript(root, [])), "session_id": "s2"}, root=root)


def test_a_file_older_than_the_turn_is_not_this_turns_output(env):
    root, good, _ = env
    old = time.time() - 3600
    os.utime(good, (old, old))
    H.stop({"transcript_path": str(transcript(root, [good])), "session_id": "s3"}, root=root)


def test_an_unreadable_transcript_is_a_refusal(env):
    root, _, _ = env
    refused(H.stop, {"transcript_path": str(root / "nope.jsonl")}, root=root)
    refused(H.stop, {}, root=root)


def test_a_subagent_stop_reads_the_agent_transcript(env):
    root, good, _ = env
    ev = {"agent_transcript_path": str(transcript(root, [good])), "transcript_path": str(root / "main.jsonl"), "session_id": "s4"}
    assert "good.txt" in refused(H.stop, ev, root=root, sub=True)


def test_the_stop_hook_lets_go_after_three_refusals_and_records_the_incident(env):
    root, good, _ = env
    ev = {"transcript_path": str(transcript(root, [good])), "session_id": "loop"}
    for _ in range(3):
        refused(H.stop, ev, root=root)
    H.stop(ev, root=root)                                                                      # the 4th: let go, but not silently
    rows = [json.loads(line) for line in (root / H.INCIDENTS).read_text().splitlines()]
    assert rows and "good.txt" in rows[0]["unchecked"][0]


def _let_go(root, f, sid="q"):
    ev = {"transcript_path": str(transcript(root, [f])), "session_id": sid}
    for _ in range(3):
        refused(H.stop, ev, root=root)
    H.stop(ev, root=root)
    return ev


def test_a_released_turn_quarantines_its_files_and_only_a_newer_pass_lifts_it(env):
    root, good, bad = env
    _let_go(root, bad)
    assert SG.quarantined(SG.sha256(bad), root=root)
    assert SG.passing_record(bad, root=root) is None
    SG.run("L9", [bad], root=root)                                                             # FAIL (too short): still quarantined
    assert SG.passing_record(bad, root=root) is None
    SG.run("L9", [bad], root=root, owner_asked=MSG)                                            # a labelled record does not lift it
    assert SG.passing_record(bad, root=root) is None
    assert "no passing send record" in refused(H.pre_bash, bash(upload(bad)), root=root)
    SG.run("L9", [good], root=root)                                                            # another file passing does nothing for it
    assert SG.passing_record(bad, root=root) is None


def test_an_older_pass_does_not_survive_a_quarantine_and_a_newer_pass_lifts_it(env):
    root, good, _ = env
    now = time.time()
    SG.run("L9", [good], root=root, now=now - 10)
    assert SG.passing_record(good, root=root) is not None
    SG.quarantine([good], "released by the stop hook", root=root, now=now - 5)
    assert SG.passing_record(good, root=root) is None                                          # the PASS is older than the quarantine
    SG.run("L9", [good], root=root, now=now)                                                   # measured again, newer
    assert SG.passing_record(good, root=root) is not None


def test_a_send_that_fails_reports_the_quarantine_next_to_the_failure(env):
    root, _, bad = env
    SG.quarantine([bad], "released by the stop hook", root=root)
    rep = SG.run("L9", [bad], root=root)
    assert rep["status"] == SG.BLOCK and any(r["status"] == SG.FAIL for r in rep["rows"])      # the failure stays visible
    assert any(r["id"] == "QUARANTINE" and r["status"] == SG.BLOCK for r in rep["rows"])


def test_the_prompt_hook_shows_each_incident_once_and_fails_open(env, monkeypatch, capsys):
    root, good, _ = env
    assert H.prompt({}, root=root) == ""
    _let_go(root, good, "q3")
    first = H.prompt({}, root=root)
    assert "SEND GATE INCIDENT" in first and "good.txt" in first
    assert H.prompt({}, root=root) == ""                                                       # shown once
    monkeypatch.setattr(H, "prompt", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert run_main(monkeypatch, "prompt", {}, root) == 0                                      # fails open: never erases the owner's prompt
    assert "could not read the incidents" in capsys.readouterr().err


# ---- fail closed ---------------------------------------------------------------------------------------------------------------

def run_main(monkeypatch, cmd, event, root):
    monkeypatch.setattr("sys.stdin", io.StringIO(event if isinstance(event, str) else json.dumps(event)))
    monkeypatch.setattr(H, "root_dir", lambda r=None: root)
    return H.main([cmd])


def test_main_allows_a_clean_command_and_refuses_with_exit_2(env, monkeypatch, capsys):
    root, good, _ = env
    assert run_main(monkeypatch, "pre-bash", bash("echo hi"), root) == 0
    assert run_main(monkeypatch, "pre-bash", bash(upload(good)), root) == 2
    assert "send gate" in capsys.readouterr().err


@pytest.mark.parametrize("how", ["broken scope file", "garbage on stdin", "unknown command"])
def test_a_broken_hook_fails_closed(env, monkeypatch, capsys, tmp_path, how):
    root, _, _ = env
    event, cmd = bash("echo hi"), "pre-bash"
    if how == "broken scope file":
        monkeypatch.setattr(H, "SCOPE", tmp_path / "gone.json")
    elif how == "garbage on stdin":
        event = "{not json"
    else:
        cmd = "launch"
    assert run_main(monkeypatch, cmd, event, root) == 2
    err = capsys.readouterr().err
    assert ("unknown hook command" if how == "unknown command" else "failed closed") in err


def test_the_committed_scope_file_is_valid():
    sc = H.scope()
    assert H.in_scope("episodes/x/trials/L14/a.mp4", sc) and H.in_scope("out/comparison_L9/a.png", sc)
    assert not H.in_scope("logs/run.txt", sc) and not H.in_scope("vault/pictures/a.png", sc)
    assert H.layer_of("a/trials/L14/clip.mp4", sc) == "L14" and H.layer_of("a/trials/L9_x.png", sc) == "L9"
    assert H.layer_of("a/trials/L99/x.png", sc) is None and H.layer_of("a/trials/x.png", sc) is None


# ---- the wiring in .claude/settings.json ---------------------------------------------------------------------------------------

def _send_hook_commands():
    from _gov import ROOT
    cfg = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
    out = {}
    for event, groups in cfg.items():
        for g in groups:
            for h in g["hooks"]:
                if "governance.send_hook" in h["command"]:
                    out.setdefault(event, []).append(h["command"])
    return out


def test_the_send_hooks_are_wired_on_bash_stop_and_subagent_stop_and_keep_the_d84_hooks():
    from _gov import ROOT
    wired = _send_hook_commands()
    assert set(wired) == {"PreToolUse", "Stop", "SubagentStop", "UserPromptSubmit"}
    assert "pre-bash" in wired["PreToolUse"][0] and "subagent-stop" in wired["SubagentStop"][0] and " stop " in wired["Stop"][0] + " "
    text = (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert "governance.hooks pre-bash" in text and "governance.hooks stop" in text      # extended, not replaced


def test_a_send_hook_command_that_cannot_start_exits_2(tmp_path):
    import subprocess
    for event, cmds in _send_hook_commands().items():
        for c in cmds:
            if event == "UserPromptSubmit":      # fails open on purpose: an exit 2 would erase the owner's prompt
                continue
            r = subprocess.run(["/bin/bash", "-c", c], env={"PATH": "/nonexistent", "CLAUDE_PROJECT_DIR": str(tmp_path)},
                               input="{}", capture_output=True, text=True)
            assert r.returncode == 2 and "closed" in r.stderr, (c, r.returncode, r.stderr)
