"""The night's $20 is checked before a live Modal submission: the worst case (conservative_retry_total_usd) is booked first,
and a submission that would pass the night is refused before any credential is read."""
from types import SimpleNamespace

import pytest

from explainer_engine.cloud.providers import modal_provider as MP
from explainer_engine.core import spend_caps


class _Approved:
    def validate(self, provider):
        return None


def _adapter(monkeypatch, worst_usd):
    adapter = MP.ModalAdapter(token_id="md-test", token_secret="md-secret", clock=lambda: 1_760_000_000.0)
    monkeypatch.setattr(adapter, "estimate_cost", lambda *a, **k: SimpleNamespace(
        expected_total_usd=worst_usd, conservative_retry_total_usd=worst_usd, net_after_credits_usd=worst_usd))
    called = []
    monkeypatch.setattr(adapter, "verify_credentials", lambda: called.append(1))
    return adapter, called


def test_a_live_modal_submit_past_the_night_is_refused_before_credentials(real_overnight, tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_OVERNIGHT_DIR", str(tmp_path / "night"))
    spend_caps.overnight_reserve("claude_api", "booked", 19.0)
    adapter, called = _adapter(monkeypatch, 2.5)
    with pytest.raises(spend_caps.OverCeiling, match="modal"):
        adapter.submit_job(None, SimpleNamespace(gpu_type="H100"), function_name="f", idempotency_key="k1",
                           dry_run=False, approval=_Approved())
    assert called == []


def test_a_live_modal_submit_inside_the_night_books_its_worst_case(real_overnight, tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_OVERNIGHT_DIR", str(tmp_path / "night"))
    adapter, called = _adapter(monkeypatch, 2.0)
    out = adapter.submit_job(None, SimpleNamespace(gpu_type="H100"), function_name="f", idempotency_key="k2",
                             dry_run=False, approval=_Approved())
    assert out["mode"] == "created" and called == [1]
    assert round(spend_caps.overnight_spent(), 6) == 2.0
