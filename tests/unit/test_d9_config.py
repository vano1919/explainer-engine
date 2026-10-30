"""The creator's D9 answers (2026-10-30 11:56 UTC, message cmsg_01Hnu5zB86sjUj5GtTgaUkPW5XNWqTbsYwYjr1qt3UyQhT, "ყველაფერზე კი" =
option a on questions 10-13 and the stale pod id): the lines in config/spend_caps.json, their readers, and the protected channel voices."""

import json
import time

import pytest

from _gov import make_repo
from explainer_engine.cloud import runpod as R
from explainer_engine.core import spend_caps
from explainer_engine.governance import hooks, records
from explainer_engine.llm import gemini_api as G


def _caps_file(tmp_path, monkeypatch, mutate):
    doc = json.loads(spend_caps.PATH.read_text(encoding="utf-8"))      # always from the real file, not from the last mutation
    mutate(doc)
    f = tmp_path / "caps.json"
    f.write_text(json.dumps(doc))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(f))


# -- 11: ElevenLabs casting credits --------------------------------------------------------------------------------------------

def test_casting_credits_max_is_the_creators_1500(tmp_path, monkeypatch):
    assert spend_caps.casting_credits_max() == 1500.0
    for bad in (None, 0, -5, True, "1500"):
        _caps_file(tmp_path, monkeypatch, lambda d, bad=bad: d["casting"].update(casting_credits_max=bad))
        with pytest.raises(spend_caps.OverCeiling):
            spend_caps.casting_credits_max()
    _caps_file(tmp_path, monkeypatch, lambda d: d.pop("casting"))
    with pytest.raises(spend_caps.OverCeiling):
        spend_caps.casting_credits_max()


# -- 10: the Gemini API line --------------------------------------------------------------------------------------------------

def test_gemini_api_is_ten_dollars_a_month_and_the_stub_refuses_past_80_percent():
    assert spend_caps.gemini_api()["max_usd"] == 10.0 and spend_caps.gemini_api()["period"] == "month"
    assert G.monthly_ceiling() == 10.0
    assert G.reserve(0.2, 7.0) == pytest.approx(7.2)
    assert G.reserve(1.0, 7.0) == pytest.approx(8.0)                      # exactly 80 % is allowed
    with pytest.raises(G.GeminiRefused, match="80%"):
        G.reserve(0.5, 7.7)
    with pytest.raises(G.GeminiRefused):
        G.reserve(-1, 0)


def test_gemini_api_without_its_line_refuses_everything(tmp_path, monkeypatch):
    for mutate in (lambda d: d.pop("gemini_api"), lambda d: d["gemini_api"].update(max_usd=0), lambda d: d["gemini_api"].update(max_usd=True)):
        _caps_file(tmp_path, monkeypatch, mutate)
        with pytest.raises(spend_caps.OverCeiling):
            G.reserve(0.01, 0)


def test_no_gemini_api_client_exists_yet():
    with pytest.raises(G.GeminiRefused, match="not built"):
        G.complete("hello")


# -- 13: the RunPod minimum balance -------------------------------------------------------------------------------------------

class _Api:
    def __init__(self, balance):
        self._balance = balance

    def billing_total(self, since):
        return 0.0, []

    def balance(self):
        return {"clientBalance": self._balance}


def test_min_balance_left_is_one_dollar_and_create_refuses_below_it(monkeypatch):
    assert spend_caps.runpod()["min_balance_left_usd"] == 1.0
    monkeypatch.setattr(R, "check", lambda api, now: {"problems": []})
    low = R.preflight_create(_Api(1.20), max_usd=0.30, max_hours=1.0, gpu="default", now=10**6)     # 0.90 left: the old 0.25 allowed it
    assert any("min_balance_left_usd 1.0" in w for w in low), low
    ok = R.preflight_create(_Api(1.40), max_usd=0.30, max_hours=1.0, gpu="default", now=10**6)      # exactly 1.10 left
    assert not any("min_balance_left_usd" in w for w in ok), ok


# -- the stale pod id ---------------------------------------------------------------------------------------------------------

def test_the_gone_pod_is_no_longer_kept():
    keep = spend_caps.runpod()["keep_stopped_pods"]
    assert "97vn2t443puxxl" not in keep and len(keep) == len(set(keep)) and len(keep) == 49


# -- 12: channel_voices.json is a protected file -------------------------------------------------------------------------------

def test_channel_voices_changes_only_on_the_creators_recorded_word(tmp_path):
    repo = make_repo(tmp_path / "r", git=True)
    p = str(repo / "config" / "channel_voices.json")
    assert hooks.load(repo)["protected_files"]["config/channel_voices.json"] == 60
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": p}}, repo) == 2
    assert hooks.pre_bash({"tool_input": {"command": "sed -i 's/a/b/' config/channel_voices.json"}}, repo) == 2
    assert hooks.pre_bash({"tool_input": {"command": "cat config/channel_voices.json"}}, repo) == 0       # reading stays free
    records.add("protected_config", "config/channel_voices.json", "cmsg_x", "ვანო: კი", root=repo, now=time.time() - 7200)
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": p}}, repo) == 2              # a stale word
    records.add("protected_config", "config/channel_voices.json", "cmsg_y", "ვანო: კი", root=repo)
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": p}}, repo) == 0
    # the word names one file: it does not unlock the money caps
    assert hooks.pre_write({"tool_name": "Edit", "tool_input": {"file_path": str(repo / "config" / "spend_caps.json")}}, repo) == 2
