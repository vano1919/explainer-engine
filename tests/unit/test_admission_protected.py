"""N-08 follow-up: ``assets/audio/generator_admission.json`` is a protected file, like ``config/channel_voices.json`` (D9 question
12). ``generator_gate.admit`` writes it only with the creator's ``generator_admit`` word; this keeps a hand edit (Edit, Write or a
shell writer) behind his ``protected_config`` word too, so the file cannot be filled without either."""

import time

from _gov import make_repo
from explainer_engine.audio import generator_gate
from explainer_engine.governance import hooks, records

REL = "assets/audio/generator_admission.json"


def test_the_admission_file_is_the_one_generator_gate_writes():
    assert generator_gate.ADMISSION.relative_to(generator_gate.REPO).as_posix() == REL


def test_a_generator_admission_changes_only_on_the_creators_recorded_word(tmp_path):
    repo = make_repo(tmp_path / "r", git=True)
    p = str(repo / "assets" / "audio" / "generator_admission.json")
    assert hooks.load(repo)["protected_files"][REL] == 60
    for tool in ("Edit", "Write"):
        assert hooks.pre_write({"tool_name": tool, "tool_input": {"file_path": p}}, repo) == 2
    assert hooks.pre_bash({"tool_input": {"command": f"echo '{{}}' > {REL}"}}, repo) == 2
    assert hooks.pre_bash({"tool_input": {"command": f"cat {REL}"}}, repo) == 0                 # reading stays free
    records.add("protected_config", REL, "cmsg_x", "ვანო: კი", root=repo, now=time.time() - 7200)
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": p}}, repo) == 2    # a stale word
    records.add("protected_config", REL, "cmsg_y", "ვანო: კი", root=repo)
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": p}}, repo) == 0
    # the word names one file: it unlocks neither the money caps nor the routing config
    for other in ("config/spend_caps.json", "config/model_routing.json"):
        assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": str(repo / other)}}, repo) == 2


def test_the_admit_command_keeps_its_own_gate_and_is_not_refused_by_the_shell_guard(tmp_path):
    """`admit` writes the file from Python behind the creator's `generator_admit` word (BP-162); the guard stops hand edits only."""
    repo = make_repo(tmp_path / "r", git=True)
    cmd = ("python -m explainer_engine.audio.generator_gate admit r.json --generator g --kind sfx --sheet s/sheet.md "
           "--creator-ref cmsg_1 --at 2026-10-31T10:00:00Z")
    assert hooks.pre_bash({"tool_input": {"command": cmd}}, repo) == 0
