"""The creator's picture route order (2026-11-13): Gemini chat, then Gemini API, then BFL; the config and the progress log say so."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_route_order_is_chat_api_bfl():
    cfg = json.loads((ROOT / "config" / "picture_route.json").read_text(encoding="utf-8"))
    assert [r["route"] for r in cfg["order"]] == ["gemini_chat_task", "gemini_api_batch", "bfl_api"]
    assert [r["level"] for r in cfg["order"]] == [1, 2, 3]
    assert cfg["order"][0]["price_usd_per_photo"] == 0.0


def test_progress_log_names_the_route():
    assert "config/picture_route.json" in (ROOT / "docs" / "PROGRESS.md").read_text(encoding="utf-8")
