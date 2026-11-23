"""The owner's Modal video line ($10, 2026-11-21) is recorded in config/spend_caps.json with its decision and stop."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_modal_render_line_is_ten_dollars_with_owner_decision():
    d = json.loads((ROOT / "config" / "spend_caps.json").read_text(encoding="utf-8"))
    line = d["modal_render"]
    assert line["per_episode_usd"] == 10.0
    assert "cmsg_01Hnu5zB86sjUj5GtTgaUkPW4V6QpczZqhnb1GLWaouN1G" in line["decided"]
    assert round(line["per_episode_usd"] * 0.8, 2) == 8.0   # 80 % warning / stop point used by the ledger
