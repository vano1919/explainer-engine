"""The four candidate universes and their concept boards (the creator's brief of 2026-10-22): the same scenes in every
direction, no other work named, no child cues, priced before sending, refused without the creator's approval, every picture
recorded, one labelled board image per direction. No network: a fake provider stands in."""
import io
import json

import pytest
from PIL import Image

from explainer_engine.core.ledger import Run
from explainer_engine.imagegen import universe_boards as UB
from explainer_engine.imagegen.providers.base import AccountError, ProviderError, Result

PNG = io.BytesIO()
Image.new("RGB", (64, 36), (120, 40, 200)).save(PNG, "PNG")
PNG = PNG.getvalue()


class FakeProvider:
    service = "bfl_usd"

    def __init__(self, root, *, run=None, fail_on=(), account_error=False, **kw):
        self.root, self.run, self.calls, self.fail_on, self.account_error = root, run, [], fail_on, account_error

    def generate(self, name, prompt, *, model, size, refs=None, seed=None, extra=None):
        self.calls.append((name, model, size, seed, extra))
        if self.account_error:
            raise AccountError("bfl: HTTP 403 (key or account)")
        if name in self.fail_on:
            raise ProviderError("bfl: Moderated")
        if self.run is not None:
            self.run.reserve(self.service, 0.009, item=name)
        return Result(PNG, model, "v", seed, 0.009, None, 0.5)


def test_same_scenes_in_every_direction_and_distinct_cores():
    for d in UB.DIRECTIONS:
        rows = UB.prompts(d)
        assert [r["slot"] for r in rows] == ["A", "B", "C", "D", "L"]
        for r, (slot, _title, scene) in zip(rows, UB.ENVIRONMENTS):
            assert r["prompt"].startswith(scene) and d["core"] in r["prompt"] and r["prompt"].endswith(UB.NO_TEXT)
    cores = [d["core"] for d in UB.DIRECTIONS]
    assert len(set(cores)) == 4 and len({d["id"] for d in UB.DIRECTIONS}) == 4
    for d in UB.DIRECTIONS:  # the brief's feasibility questions are answered for every direction
        assert set(d["production"]) == {"characters", "expressions", "environments", "dimension", "camera", "closeups", "settings", "fragile", "fit"}


def test_prompts_name_no_other_work_and_carry_no_child_cues():
    for d in UB.DIRECTIONS:
        for q in UB.prompts(d):
            assert UB.lint(q["prompt"]) == [], (d["id"], q["slot"])
    assert "spongebob" in UB.lint("square yellow hero like spongebob")
    assert "big head" in UB.lint("a big head figure") and "3d render" in UB.lint("a 3D render of a street")


def test_plan_prices_every_picture_and_binds_a_hash():
    p = UB.plan(takes=1)
    assert p["usd"] == pytest.approx(20 * 0.009) and p["by_service"] == {"bfl_usd": 0.18}
    assert len(p["candidates"][0]["boards"]) == 4 and all(len(b["pictures"]) == 5 for b in p["candidates"][0]["boards"])
    assert p["hash"] == UB.plan(takes=1)["hash"] and p["hash"] != UB.plan(takes=2)["hash"]
    two = UB.plan(["bfl:flux-3-image-klein:1k", "fal:seedream-4.5-t2i:2K_wide"], takes=2)
    assert two["by_service"] == {"bfl_usd": 0.36, "fal_usd": 1.6}
    assert "40" in UB.table(two) and two["hash"] in UB.table(two)
    with pytest.raises(ValueError):
        UB.plan(["bfl:flux-3-image-klein"])


def test_plan_refuses_a_prompt_that_names_a_work(monkeypatch):
    monkeypatch.setitem(UB.DIRECTIONS[0], "core", UB.DIRECTIONS[0]["core"] + ", in the manner of samurai jack")
    with pytest.raises(ValueError, match="samurai jack"):
        UB.plan()


def test_run_is_refused_without_the_creators_approval(tmp_path):
    p = UB.plan()
    ledger = Run.open(tmp_path / "run.json", caps={"bfl_usd": 1.0})
    with pytest.raises(PermissionError):
        UB.run(p, tmp_path, ledger, factory=lambda name, **kw: FakeProvider(**kw), log=lambda *a: None)
    assert not (tmp_path / "results.json").exists()


def test_run_paints_every_board_records_failures_and_composes_labelled_boards(tmp_path):
    p = UB.plan()
    ledger = Run.open(tmp_path / "run.json", caps={"bfl_usd": 1.0})
    ledger.approve("boards", p["hash"], by="ვანო", ref="card 2026-10-22", provider="bfl", usd=p["usd"])
    made = []

    def factory(name, **kw):
        prov = FakeProvider(fail_on=("ink_cel_C_t1",), **kw)
        made.append(prov)
        return prov

    res = UB.run(p, tmp_path, ledger, factory=factory, log=lambda *a: None)
    rec = res["candidates"]["bfl_flux_3_image_klein_1k"]
    assert len(rec["pictures"]) == 20 and rec["failures"] == 1 and rec["pictures"]["ink_cel_C_t1"]["error"] == "refused"
    assert rec["usd"] == pytest.approx(19 * 0.009) and ledger.spent("bfl_usd") == pytest.approx(19 * 0.009)
    assert all(c[4] == {"aspect_ratio": "16:9"} and c[3] == 1 for c in made[0].calls)
    assert (tmp_path / "bfl_flux_3_image_klein_1k" / "paper_stage_A_t1.png").exists()
    # the second run paints nothing that exists (the failed one is retried) and the results file keeps its records
    res2 = UB.run(p, tmp_path, ledger, factory=factory, log=lambda *a: None)
    assert [c[0] for c in made[1].calls] == ["ink_cel_C_t1"] and res2["candidates"]["bfl_flux_3_image_klein_1k"]["failures"] == 1
    for d in UB.DIRECTIONS:
        out = UB.board(tmp_path, "bfl_flux_3_image_klein_1k", d["id"], cell=(160, 90))
        im = Image.open(out)
        assert im.size == (320, 26 * 2 + 2 * (90 + 26) + 90 + 26)
    sheet = Image.open(tmp_path / "board_ink_cel_bfl_flux_3_image_klein_1k_t1.png").convert("RGB")
    assert sheet.getpixel((10, 26 * 2 + 10)) == (120, 40, 200)  # A is painted
    assert sheet.getpixel((10, 26 * 2 + 90 + 26 + 10)) != (120, 40, 200)  # C (ink_cel) is the refused one: no picture


def test_an_account_error_stops_that_candidate_after_one_call(tmp_path):
    p = UB.plan()
    ledger = Run.open(tmp_path / "run.json", caps={"bfl_usd": 1.0})
    ledger.approve("boards", p["hash"], by="ვანო", ref="card", provider="bfl", usd=p["usd"])
    made = []

    def factory(name, **kw):
        prov = FakeProvider(account_error=True, **kw)
        made.append(prov)
        return prov

    res = UB.run(p, tmp_path, ledger, factory=factory, log=lambda *a: None)
    assert len(made[0].calls) == 1 and "account_error" in res["candidates"]["bfl_flux_3_image_klein_1k"]
    assert ledger.spent("bfl_usd") == 0.0


def test_cli_estimate_and_prompts_send_nothing(capsys):
    assert UB.main(["estimate"]) == 0
    out = capsys.readouterr().out
    assert "nothing is sent" in out and "0.180" in out
    assert UB.main(["prompts"]) == 0
    out = capsys.readouterr().out
    assert out.count("[A] modern city") == 4 and "Paper Stage" in out
