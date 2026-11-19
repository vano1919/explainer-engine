import json

import pytest

from explainer_engine.cloud import modal_run as MR


def _red(tmp_path, worker="a" * 64):
    p = tmp_path / "ladder.json"
    p.write_text(json.dumps({"done": ["L0", "L1", "L2"], "red": "L3", "measured": {},
                             "rungs": {"L3": {"ok": False, "worker_sha": worker, "launch_sha": "b" * 64}}}))
    return p


def test_reset_needs_a_changed_worker_and_archives_the_red_file(tmp_path):
    p = _red(tmp_path)
    with pytest.raises(SystemExit):
        MR.reset(p, "a" * 64)                      # the same bytes: a retry, refused
    fresh = MR.reset(p, "c" * 64, why="distilled pipeline takes no negative prompt", stamp="T")
    assert fresh["done"] == [] and fresh["red"] is None
    arch = tmp_path / "ladder.red-T.json"
    assert json.loads(arch.read_text())["red"] == "L3"            # nothing deleted
    assert json.loads(p.read_text())["reset_from"]["archive"] == "ladder.red-T.json"
    with pytest.raises(SystemExit):
        MR.reset(p, "d" * 64)                      # not red any more


def test_reset_refuses_a_ladder_that_is_not_red(tmp_path):
    p = tmp_path / "l.json"
    p.write_text(json.dumps({"done": ["L0"], "red": None, "rungs": {}}))
    with pytest.raises(SystemExit):
        MR.reset(p, "c" * 64)
