"""P0b (OR-04): two attempts at the assigned level, the third only escalated, then the item stops."""
import json

import pytest

from explainer_engine.core.errors import NeedsReview
from explainer_engine.core.ledger import Attempts
from explainer_engine.governance import __main__ as cli


def test_two_plain_attempts_then_one_escalated_then_stop(tmp_path):
    a = Attempts(tmp_path / "P9" / "attempts.json")
    assert a.add("red test")["n"] == 1 and a.add("same cause")["n"] == 2
    with pytest.raises(NeedsReview, match="only escalated"):
        a.add("third try at the same level")
    assert a.add("on the reviewer's plan", escalated=True)["n"] == 3
    with pytest.raises(NeedsReview, match="ask the creator"):
        a.add("again", escalated=True)
    with pytest.raises(NeedsReview):
        a.add("plain again")
    rows = json.loads((tmp_path / "P9" / "attempts.json").read_text())
    assert [r["escalated"] for r in rows] == [False, False, True]


def test_the_numbers_come_from_the_config_file_defaults():
    from _gov import config
    e = config()["escalation"]
    assert (e["attempts_at_level"], e["escalated_attempts"]) == (2, 1)


def test_cli_exits_2_when_the_item_must_stop(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "root_dir", lambda *a: tmp_path)
    assert cli.main(["attempt", "P9"]) == 0 and cli.main(["attempt", "P9"]) == 0
    assert cli.main(["attempt", "P9"]) == 2
    assert cli.main(["attempt", "P9", "--escalated"]) == 0
    assert cli.main(["attempt", "P9", "--escalated"]) == 2
