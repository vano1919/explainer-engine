"""CH-07 (D-133 as amended; the creator 2026-11-13 14:37 UTC and his card 14:47 UTC): before a paid option is offered, the free
credit is checked first, then today's Modal cards, prices and status, at least two combinations are priced and the cheapest is
chosen with its free/paid split, cap and watchdog; the hook refuses a paid LTX rung without such an offer."""
from __future__ import annotations

import copy
import datetime as dt
import json

import pytest

from conftest import make_offer
from explainer_engine.cloud import cheapest as C
from explainer_engine.cloud import hooks as H
from explainer_engine.cloud import paid_offer as P

LTX = "explainer_engine/training/pods/ltx/modal_ltx_jobs.py"
GO = "cmsg_01AbC:a1b2c3d4e5f6"
NOW = dt.datetime(2026, 11, 13, 15, 0, tzinfo=dt.timezone.utc)

PAGE = """<div>Nvidia H100 SXM5</div><div>$ 0.001097</div><span>0 . 0 0 1 0 9 7</span> / sec
<div>Nvidia RTX PRO 6000 $ 0.000842 0 . 0 0 0 8 4 2 / sec</div><div>Nvidia A100, 80 GB $ 0.000694 0 . 0 0 0 6 9 4 / sec</div>
<div>Nvidia L4 $ 0.000222 0 . 0 0 0 2 2 2 / sec</div>
<div>CPU $ 0.0000131 0 . 0 0 0 0 1 3 1 / core / sec</div><div>Memory $ 0.00000222 0 . 0 0 0 0 0 2 2 2 / GiB / sec</div>"""
STATUS = json.dumps({"included": [
    {"type": "status_page_resource", "attributes": {"public_name": "Functions", "status": "operational"}},
    {"type": "status_report", "attributes": {"title": "Control Plane Maintenance", "aggregate_state": "maintenance",
                                             "starts_at": "2026-11-16T01:00:00Z", "ends_at": "2026-11-16T02:00:00Z"}},
    {"type": "status_report", "attributes": {"title": "old", "aggregate_state": "resolved"}}]})


def _offer(**kw):
    o = make_offer(now=NOW)
    o.update(kw)
    return P.price(o)


def _why(o):
    return " | ".join(P.problems(o, NOW))


def test_a_complete_offer_passes_and_reads_as_a_georgian_card():
    o = _offer()
    assert P.problems(o, NOW) == []
    text = P.offer_text(o)
    assert "H100" in text and "უფასო კრედიტიდან $0.1" in text and "ფასიანი $0.183" in text and "Haiku" in text


@pytest.mark.parametrize("drop, why", [("credit", "free-credit check is missing"),
                                       ("gpus", "GPU availability check is missing"),
                                       ("split", "free/paid split is missing"),
                                       ("watchdog", "watchdog")])
def test_an_offer_without_a_required_step_fails(drop, why):
    o = _offer()
    o.pop(drop)
    if drop == "split":
        assert why in _why(o)
    else:
        assert why in _why(P.price(o) if drop != "credit" else o)


def test_one_combination_is_not_a_comparison():
    o = _offer()
    o["combos"] = o["combos"][:1]
    assert "at least two combinations" in _why(o)


def test_stale_checks_and_a_degraded_modal_fail():
    o = _offer()
    o["credit"]["checked_at"] = P._iso(NOW - dt.timedelta(hours=P.CREDIT_HOURS + 1))
    o["gpus"]["checked_at"] = P._iso(NOW - dt.timedelta(hours=P.GPU_HOURS + 1))
    o["gpus"]["functions_status"] = "degraded"
    why = _why(o)
    assert "credit check is older" in why and "GPU check is older" in why and "not operational" in why


def test_a_guessed_vram_need_fails_and_a_card_that_does_not_fit_cannot_be_chosen():
    o = _offer()
    o["need"] = {"vram_gb": 80, "basis": "estimate", "ref": "looks big"}
    assert "measured or known" in _why(o)
    o = _offer()
    o["combos"][0]["gpu"] = "L40S"                     # 48 GB against the 80 GB the job needs
    assert "does not fit" in _why(P.price(o))


def test_a_cheaper_fitting_combination_must_be_taken_or_explained():
    o = _offer()
    o["combos"][1]["gpu_s"], o["combos"][1]["worst_gpu_s"] = 100, 150      # the A100 combo is now the cheaper one
    o = P.price(o)
    assert "is cheaper than the chosen one" in _why(o)
    o["combos"][1]["not_chosen_why"] = "speed not measured on LTX; measuring it is its own approved run"
    assert P.problems(o, NOW) == []


def test_the_chosen_setup_keeps_the_cheapest_rules():
    o = _offer()
    o["combos"][0].update(model_loads_per_container=2, scaledown_s=60, containers=4)
    why = _why(o)
    assert "CH-01" in why and "CH-04" in why and "CH-03" in why


def test_prices_must_be_the_seconds_at_todays_rate_and_the_split_spends_free_credit_first():
    o = _offer()
    o["combos"][0]["est_usd"] = 0.01
    assert "not its seconds x today's rate" in _why(o)
    o = _offer()
    o["split"] = {"free_usd": 0.0, "paid_usd": o["combos"][0]["est_usd"]}
    assert "free credit first" in _why(o)
    o = _offer(cap_usd=0.2)
    assert "cap is missing or below" in _why(o)


def test_the_credit_comes_from_modal_and_falls_back_to_the_ledgers(tmp_path):
    raw = json.dumps({"metered_cost": "22.49", "billed_cost": "0", "adjustments": {
        "credits": "-17.03", "free_storage": "-5.32", "network_egress_allowance": "-0.14"}})     # Modal's real shape
    c = P.fetch_credit(NOW, cli=lambda args: raw)
    assert (c["source"], c["used_usd"], c["free_left_usd"]) == ("modal_billing_summary", 17.03, 12.97)
    raw = json.dumps({"metered_cost": "12.5", "billed_cost": "0", "adjustments": {}})         # no credits line: fallback
    assert P.fetch_credit(NOW, cli=lambda args: raw)["free_left_usd"] == 17.5
    (tmp_path / "a.json").write_text(json.dumps({"created": "2026-11-12T18:22:04", "spent": {"modal": 2.5, "gemini_usd": 9}}))
    (tmp_path / "b.json").write_text(json.dumps({"created": "2026-11-12T21:10:25", "spent": {"modal_ltx": 0.5}}))
    (tmp_path / "old.json").write_text(json.dumps({"created": "2026-10-30T10:00:00", "spent": {"modal": 7}}))
    c = P.fetch_credit(NOW, ledgers=tmp_path, cli=lambda args: None)          # the gRPC API is not reachable
    assert (c["source"], c["used_usd"], c["free_left_usd"]) == ("ledger_sum", 3.0, 27.0)
    assert "a.json" in c["ref"] and "old.json" not in c["ref"]
    with pytest.raises(ValueError):
        P._modal_cli(["run", "x.py"])                                          # only read-only billing commands


def test_the_cards_come_from_todays_pricing_page_and_the_status_page():
    g = P.fetch_gpus(NOW, get=lambda url: PAGE if url == P.PRICING_URL else STATUS)
    rows = {r["gpu"]: (r["usd_s"], r["vram_gb"]) for r in g["rows"]}
    assert rows == {"H100": (0.001097, 80), "RTX-PRO-6000": (0.000842, 96), "A100-80GB": (0.000694, 80), "L4": (0.000222, 24)}
    assert g["functions_status"] == "operational" and len(g["notices"]) == 1 and "Maintenance" in g["notices"][0]
    with pytest.raises(ValueError):
        P.gpus_from_page("<html>nothing</html>")


def test_the_hook_refuses_a_paid_ltx_rung_without_a_passing_offer_for_it(tmp_path, paid_offer):
    cmd = f"EE_MODAL_GO={GO} modal run {LTX}::smoke"
    assert "CH-07" in H.modal_refusal(cmd, env={})
    ok = paid_offer("smoke")
    assert H.modal_refusal(f"EE_MODAL_GO={GO} EE_PAID_OFFER={ok} modal run {LTX}::smoke", env={}) is None
    assert H.modal_refusal(cmd, env={"EE_PAID_OFFER": str(ok)}) is None
    wrong_rung = paid_offer("main")
    assert "not " + LTX + "::smoke" in H.modal_refusal(f"EE_MODAL_GO={GO} EE_PAID_OFFER={wrong_rung} modal run {LTX}::smoke",
                                                     env={})
    bad = json.loads(ok.read_text())
    bad.pop("credit")
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    assert "free-credit check" in H.modal_refusal(f"EE_MODAL_GO={GO} EE_PAID_OFFER={tmp_path / 'bad.json'} modal run {LTX}::smoke",
                                                  env={})


def test_the_offer_must_choose_the_card_the_launch_runs_on(tmp_path):
    o = make_offer("smoke", gpu="A100-80GB")
    o["combos"][1]["gpu"] = "H100"
    o = P.price(o)
    launch = {"gpu": "H100!"}
    p = tmp_path / "o.json"
    p.write_text(json.dumps(o))
    found = C.offer_problems("smoke", f"EE_PAID_OFFER={p}", {}, launch, LTX)
    assert any("launch runs on H100" in why for _, why in found)


def test_the_creators_recorded_word_waives_ch07_for_one_run(word):
    cmd = f"EE_MODAL_GO={GO} EE_CHEAPEST_WAIVE=cmsg_9:CH-07 modal run {LTX}::smoke"
    assert "CH-07" in H.modal_refusal(cmd, env={})
    word("CH-07", "cmsg_9")
    assert H.modal_refusal(cmd, env={}) is None


def test_ch07_is_documented_where_the_cheapest_rules_live():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    runbook = (root / "docs" / "CLOUD_RUNBOOK.md").read_text(encoding="utf-8")
    assert "| CH-07 |" in runbook and "paid_offer" in runbook
    for page in (".claude/agents/paid-run-watchdog.md", ".claude/agents/orchestrator.md", ".claude/rules/cloud-platforms.md",
                 ".claude/skills/modal-operations/SKILL.md"):
        assert "CH-07" in (root / page).read_text(encoding="utf-8"), page
