"""Image providers behind one interface (D-70 stage D) and the model pilot: priced before sending, the ledger reserves and
settles, a paid picture is never bought twice, a lost answer is never retried, nothing runs without the creator's recorded
approval. No network: every adapter gets a fake ``http``."""
import io
import json

import pytest
from PIL import Image

from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.imagegen import pilot, providers
from explainer_engine.imagegen import plan as P
from explainer_engine.imagegen.providers.base import ChargeUncertain, ProviderError, cache_key

PNG = io.BytesIO()
Image.new("RGB", (8, 8), (10, 200, 30)).save(PNG, "PNG")
PNG = PNG.getvalue()


class FakeBFL:
    """The BFL task flow: POST -> {id, polling_url, cost}; GET polling_url -> Pending, then Ready with result.sample."""
    def __init__(self, *, polls=1, final="Ready", status_on_post=200, cost=0.9, lose_answer=False):
        self.calls, self.polls, self.final, self.status_on_post, self.cost, self.lose = [], polls, final, status_on_post, cost, lose_answer
        self.seen = 0

    def __call__(self, method, url, body, headers):
        self.calls.append((method, url, body, dict(headers)))
        if method == "POST":
            if self.lose:
                raise ChargeUncertain("bfl: no answer")
            if self.status_on_post != 200:
                return self.status_on_post, b'{"detail": "no"}'
            return 200, json.dumps({"id": "task1", "polling_url": "https://api.us.bfl.ai/v1/get_result?id=task1", "cost": self.cost}).encode()
        if "get_result" in url:
            self.seen += 1
            if self.seen <= self.polls:
                return 200, b'{"status": "Pending"}'
            if self.final != "Ready":
                return 200, json.dumps({"status": self.final, "details": {"why": "blocked"}}).encode()
            return 200, json.dumps({"status": "Ready", "cost": self.cost, "result": {"sample": "https://cdn.example/x.png", "seed": 7}}).encode()
        return 200, PNG


class FakeFal:
    def __init__(self, *, fail=False):
        self.calls, self.fail, self.seen = [], fail, 0

    def __call__(self, method, url, body, headers):
        self.calls.append((method, url, body, dict(headers)))
        if method == "POST":
            return 200, json.dumps({"request_id": "r1", "status_url": "https://queue.fal.run/fal-ai/bytedance/requests/r1/status",
                                    "response_url": "https://queue.fal.run/fal-ai/bytedance/requests/r1"}).encode()
        if url.endswith("/status"):
            self.seen += 1
            if self.seen == 1:
                return 200, b'{"status": "IN_QUEUE", "queue_position": 2}'
            if self.fail:
                return 200, b'{"status": "COMPLETED", "error": "nsfw"}'
            return 200, b'{"status": "COMPLETED"}'
        if url.endswith("/r1"):
            return 200, json.dumps({"images": [{"url": "https://cdn.example/y.png"}], "seed": 11}).encode()
        return 200, PNG


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_IMAGE_CACHE", str(tmp_path / "cache"))
    return Run.open(tmp_path / "run.json", caps={"bfl_usd": 1.0, "fal_usd": 1.0})


def test_registry_and_prices_are_class_data():
    assert providers.cls("bfl").PRICES["flux-3-image-klein"]["1k"] == 0.009
    assert providers.cls("fal").PRICES["seedream-4.5"]["2K_wide"] == 0.04
    assert providers.cls("fal").PRICES["qwen-image-edit-2511"]["1K_wide"] == pytest.approx(1344 * 768 / 1e6 * 0.03, abs=1e-3)
    with pytest.raises(ValueError):
        providers.cls("midjourney")
    assert P.price("bfl", "flux-3-image-klein", "2k", 0) == 0.014
    with pytest.raises(ValueError):
        P.price("fal", "seedream-4.5", "1K", 0)


def test_bfl_flow_reserves_settles_and_caches(tmp_path, ledger, monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k-test")
    http = FakeBFL(polls=2, cost=0.9)
    prov = providers.get("bfl", root=tmp_path / "bfl", run=ledger, http=http, sleep=lambda s: None)
    res = prov.generate("p1", "a hero", model="flux-3-image-klein", size="1k", refs=[PNG], seed=3)
    assert res.data == PNG and res.seed == 7 and res.usd_estimated == 0.009 and res.usd_settled == 0.009 and not res.cached
    post = http.calls[0]
    assert post[3]["x-key"] == "k-test" and post[2]["seed"] == 3 and post[2]["resolution"] == "1k" and post[2]["images"][0].startswith("data:image/png;base64,")
    assert [c[1] for c in http.calls[1:4]] == ["https://api.us.bfl.ai/v1/get_result?id=task1"] * 3  # the returned polling_url, never a hand-built one
    assert ledger.spent("bfl_usd") == pytest.approx(0.009) and ledger.data["reserved"]["p1"]["settled"]
    again = prov.generate("p1b", "a hero", model="flux-3-image-klein", size="1k", refs=[PNG], seed=3)
    assert again.cached and len(http.calls) == 5 and ledger.spent("bfl_usd") == pytest.approx(0.009)
    assert (tmp_path / "bfl" / "spend_log.jsonl").read_text().count("\n") == 2
    with pytest.raises(ProviderError, match="at most 10"):
        prov.generate("p2", "x", model="flux-3-image-klein", size="1k", refs=[PNG] * 11)
    with pytest.raises(ProviderError, match="unknown model"):
        prov.generate("p3", "x", model="flux-9", size="1k")


def test_bfl_moderation_and_no_credits_refund_the_reservation(tmp_path, ledger, monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")
    prov = providers.get("bfl", root=tmp_path / "b", run=ledger, http=FakeBFL(final="Content Moderated"), sleep=lambda s: None)
    with pytest.raises(ProviderError, match="Content Moderated"):
        prov.generate("m1", "x", model="flux-3-image-klein", size="1k")
    assert ledger.spent("bfl_usd") == 0.0
    prov = providers.get("bfl", root=tmp_path / "b", run=ledger, http=FakeBFL(status_on_post=402), sleep=lambda s: None)
    with pytest.raises(ProviderError, match="402"):
        prov.generate("m2", "x", model="flux-3-image-klein", size="1k")
    assert ledger.spent("bfl_usd") == 0.0


def test_a_lost_answer_keeps_the_reservation_and_is_not_retried(tmp_path, ledger, monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")
    http = FakeBFL(lose_answer=True)
    prov = providers.get("bfl", root=tmp_path / "b", run=ledger, http=http)
    with pytest.raises(ChargeUncertain):
        prov.generate("u1", "x", model="flux-3-image-klein", size="1k")
    assert ledger.spent("bfl_usd") == pytest.approx(0.009) and len(http.calls) == 1


def test_bfl_times_out_waiting(tmp_path, ledger, monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")
    prov = providers.get("bfl", root=tmp_path / "b", run=ledger, http=FakeBFL(polls=99), sleep=lambda s: None, poll_s=1.0, max_wait_s=3.0)
    with pytest.raises(ProviderError, match="still Pending"):
        prov.generate("t1", "x", model="flux-3-image-klein", size="1k")
    assert ledger.spent("bfl_usd") == 0.0


def test_missing_key_is_a_clear_error_before_any_call(tmp_path, ledger, monkeypatch):
    monkeypatch.delenv("BFL_API_KEY", raising=False)
    http = FakeBFL()
    with pytest.raises(ProviderError, match="BFL_API_KEY is not set"):
        providers.get("bfl", root=tmp_path / "b", run=ledger, http=http).generate("k1", "x", model="flux-3-image-klein", size="1k")
    assert http.calls == [] and ledger.spent("bfl_usd") == 0.0


def test_fal_queue_flow_and_edit(tmp_path, ledger, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "fk")
    http = FakeFal()
    prov = providers.get("fal", root=tmp_path / "f", run=ledger, http=http, sleep=lambda s: None)
    res = prov.edit("e1", "reverse angle", model="qwen-image-edit-2511", size="1K_wide", refs=[PNG], seed=2)
    assert res.data == PNG and res.seed == 11 and res.usd_settled is None and res.usd_estimated == pytest.approx(0.031)
    post = http.calls[0]
    assert post[1] == "https://queue.fal.run/fal-ai/qwen-image-edit-2511" and post[3]["Authorization"] == "Key fk"
    assert post[2]["image_size"] == {"width": 1344, "height": 768} and post[2]["output_format"] == "png" and post[2]["seed"] == 2
    assert http.calls[1][1].endswith("/requests/r1/status") and http.calls[3][1].endswith("/requests/r1")
    assert ledger.spent("fal_usd") == pytest.approx(0.031)
    with pytest.raises(ProviderError, match="needs at least one input"):
        prov.generate("e2", "x", model="seedream-4.5", size="2K_wide")
    with pytest.raises(ProviderError, match="first reference"):
        prov.edit("e3", "x", model="seedream-4.5", size="2K_wide", refs=[])
    t2i = prov.generate("e4", "a sheet", model="seedream-4.5-t2i", size="2K_wide")
    assert "image_urls" not in http.calls[-4][2] and t2i.usd_estimated == 0.04
    with pytest.raises(ProviderError, match="failed"):
        providers.get("fal", root=tmp_path / "f2", run=ledger, http=FakeFal(fail=True), sleep=lambda s: None).generate(
            "e5", "x", model="seedream-4.5", size="2K_wide", refs=[PNG])


def test_cache_key_covers_refs_seed_and_params():
    a = cache_key("bfl", "m", "p", "1k", [PNG], 1, {})
    assert a != cache_key("bfl", "m", "p", "1k", [PNG], 2, {}) != cache_key("bfl", "m", "p", "1k", [], 1, {})
    assert a != cache_key("bfl", "m", "p", "1k", [PNG], 1, {"edit": True}) and a == cache_key("bfl", "m", "p", "1k", [PNG], 1, {})


def test_pilot_plan_prices_every_take_and_binds_a_hash():
    p = pilot.plan(takes=4)
    assert [c["id"] for c in p["candidates"]] == ["bfl_flux_3_image_klein_1k", "fal_seedream_4_5_2K_wide", "fal_qwen_image_edit_2511_1K_wide"]
    assert p["usd"] == pytest.approx(0.216 + 0.96 + 24 * 0.031, abs=1e-3) and p["by_service"]["bfl_usd"] == pytest.approx(0.216)
    seed = [s for s in p["candidates"][1]["shots"] if s["shot"] == "s1_sheet"][0]
    assert seed["model"] == "seedream-4.5-t2i" and not seed["from_blank_canvas"]
    qwen = [s for s in p["candidates"][2]["shots"] if s["shot"] == "s1_sheet"][0]
    assert qwen["from_blank_canvas"]
    assert pilot.plan(takes=2)["hash"] != p["hash"] and pilot.plan(takes=4)["hash"] == p["hash"]
    assert "15.00" in pilot.table(p)
    with pytest.raises(ValueError):
        pilot.plan(["bfl:klein"])


class FakeProvider:
    """Stands in for every adapter in the pilot run: paints a coloured square, charges the class price, refuses on demand."""
    made = []

    def __init__(self, name, root, run=None, refuse=(), **kw):
        self.name, self.root, self.run, self.refuse = name, root, run, refuse
        self.klass = providers.cls(name)

    def generate(self, key, prompt, *, model, size, refs=None, seed=None, extra=None):
        usd = self.klass.PRICES[model][size]
        if any(r in key for r in self.refuse):
            raise ProviderError(f"{self.name}: Content Moderated")
        if self.run is not None:
            self.run.reserve(self.klass.service, usd, item=f"{self.name}:{key}")
        FakeProvider.made.append((self.name, key, len(refs or [])))
        b = io.BytesIO()
        Image.new("RGB", (16, 9), (seed or 0, 50, 50)).save(b, "PNG")
        return providers.Result(b.getvalue(), model, "v", seed, usd, None, 0.1)

    edit = generate


def test_pilot_refuses_without_the_creators_approval_and_runs_with_it(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_IMAGE_CACHE", str(tmp_path / "cache"))
    p = pilot.plan(takes=2)
    ledger = Run.open(tmp_path / "run.json", caps={"bfl_usd": 1.0, "fal_usd": 3.0})
    with pytest.raises(PermissionError, match="no recorded approval"):
        pilot.run(p, tmp_path / "out", ledger, factory=lambda name, **kw: FakeProvider(name, **kw), log=lambda *a: None)
    ledger.approve("pilot", p["hash"], by="ვანო", ref="card 2026-10-22", provider="bfl,fal", usd=p["usd"])
    FakeProvider.made.clear()
    res = pilot.run(p, tmp_path / "out", ledger, factory=lambda name, **kw: FakeProvider(name, refuse=("s6_sign_t2",), **kw), log=lambda *a: None)
    assert res["stopped"] is None and res["embedding_scores"].startswith("not computed")
    bfl = res["candidates"]["bfl_flux_3_image_klein_1k"]
    assert len(bfl["takes"]) == 12 and bfl["refusals"] == 1 and bfl["usd"] == pytest.approx(11 * 0.009)
    assert bfl["takes"]["s3_reverse_t1"]["file"] == "s3_reverse_t1.png" and bfl["takes"]["s6_sign_t2"]["error"] == "refused"
    refs = {(n, k): r for n, k, r in FakeProvider.made}
    assert refs[("bfl", "s1_sheet_t1")] == 0 and refs[("bfl", "s2_room_t1")] == 1 and refs[("fal", "s1_sheet_t1")] == 1  # Qwen starts from a blank canvas
    assert res["candidates"]["fal_qwen_image_edit_2511_1K_wide"]["takes"]["s1_sheet_t1"]["from_blank_canvas"]
    assert ledger.spent("bfl_usd") == pytest.approx(11 * 0.009)
    sheet = pilot.collage(tmp_path / "out", "bfl_flux_3_image_klein_1k")
    assert sheet.exists() and Image.open(sheet).width == 160 + 320 * 2
    # a second run paints nothing again: every take is on file
    FakeProvider.made.clear()
    pilot.run(p, tmp_path / "out", ledger, factory=lambda name, **kw: FakeProvider(name, **kw), log=lambda *a: None)
    assert [k for n, k, r in FakeProvider.made] == ["s6_sign_t2"] * 3  # the one refused take per candidate, nothing else


def test_pilot_stops_at_the_cap_and_keeps_what_was_painted(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_IMAGE_CACHE", str(tmp_path / "cache"))
    p = pilot.plan(["bfl:flux-3-image-klein:1k"], takes=4)
    ledger = Run.open(tmp_path / "run.json", caps={"bfl_usd": 0.05})  # 80 % = 0.04 = four pictures
    ledger.approve("pilot", p["hash"], by="ვანო", ref="card", provider="bfl", usd=p["usd"])
    res = pilot.run(p, tmp_path / "out", ledger, factory=lambda name, **kw: FakeProvider(name, **kw), log=lambda *a: None)
    assert "80 %" in res["stopped"] and len([t for t in res["candidates"]["bfl_flux_3_image_klein_1k"]["takes"].values() if t.get("file")]) == 4
    assert (tmp_path / "out" / "results.json").exists()


def test_pilot_cli_estimate_sends_nothing(capsys):
    assert pilot.main(["estimate", "--takes", "1"]) == 0
    out = capsys.readouterr().out
    assert "nothing is sent" in out and "0.480" in out  # 6 shots x (0.009 + 0.04 + 0.031)


def test_an_account_error_stops_the_candidate_after_one_call(tmp_path, monkeypatch):
    """Live 2026-10-22: BFL answered 403 Not authenticated, fal 403 'User is locked: exhausted balance'. One call, not 24."""
    monkeypatch.setenv("EXPLAINER_IMAGE_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("BFL_API_KEY", "k")
    calls = []

    def locked(method, url, body, headers):
        calls.append(url)
        return 403, b'{"detail":"Not authenticated"}'
    p = pilot.plan(["bfl:flux-3-image-klein:1k"], takes=4)
    ledger = Run.open(tmp_path / "run.json", caps={"bfl_usd": 1.0})
    ledger.approve("pilot", p["hash"], by="x", ref="y", provider="bfl", usd=p["usd"])
    res = pilot.run(p, tmp_path / "out", ledger, factory=lambda name, **kw: providers.get(name, http=locked, sleep=lambda s: None, **kw),
                    log=lambda *a: None)
    rec = res["candidates"]["bfl_flux_3_image_klein_1k"]
    assert len(calls) == 1 and "403" in rec["account_error"] and rec["failures"] == 1 and ledger.spent("bfl_usd") == 0.0


def test_style_step_prices_six_looks_and_needs_its_own_approval(tmp_path, monkeypatch):
    """The creator, 2026-10-22: show style variants first. One scene, six looks, one take, on the two t2i candidates."""
    monkeypatch.setenv("EXPLAINER_IMAGE_CACHE", str(tmp_path / "cache"))
    sp = pilot.style_plan()
    assert [len(c["styles"]) for c in sp["candidates"]] == [6, 6] and sp["usd"] == pytest.approx(6 * 0.009 + 6 * 0.04)
    assert all(st["prompt"].endswith("no logo") and "Mira" in st["prompt"] for c in sp["candidates"] for st in c["styles"])
    assert not [n for c in sp["candidates"] for st in c["styles"] for n in pilot.BANNED_NAMES if n in st["prompt"].lower()]
    monkeypatch.setattr(pilot, "STYLES", pilot.STYLES + [("bad", "bad", "in the style of SpongeBob")])
    with pytest.raises(ValueError, match="no_names"):
        pilot.style_plan()
    monkeypatch.setattr(pilot, "STYLES", pilot.STYLES[:-1])
    with pytest.raises(ValueError, match="editor"):
        pilot.style_plan(["fal:qwen-image-edit-2511:1K_wide"])
    ledger = Run.open(tmp_path / "run.json", caps={"bfl_usd": 1.0, "fal_usd": 1.0})
    ledger.approve("pilot", pilot.plan()["hash"], by="x", ref="y", provider="bfl", usd=1)  # the model pilot's yes is not the style step's
    with pytest.raises(PermissionError):
        pilot.run_styles(sp, tmp_path / "out", ledger, factory=lambda name, **kw: FakeProvider(name, **kw), log=lambda *a: None)
    ledger.approve("styles", sp["hash"], by="ვანო", ref="card", provider="bfl,fal", usd=sp["usd"])
    FakeProvider.made.clear()
    res = pilot.run_styles(sp, tmp_path / "out", ledger, factory=lambda name, **kw: FakeProvider(name, **kw), log=lambda *a: None)
    assert len(FakeProvider.made) == 12 and res["stopped"] is None
    assert ledger.spent("bfl_usd") == pytest.approx(0.054) and ledger.spent("fal_usd") == pytest.approx(0.24)
    sheet = pilot.style_sheet(tmp_path / "out", "bfl_flux_3_image_klein_1k")
    assert Image.open(sheet).size == (480 * 3, 24 + (270 + 24) * 2)
    FakeProvider.made.clear()
    pilot.run_styles(sp, tmp_path / "out", ledger, factory=lambda name, **kw: FakeProvider(name, **kw), log=lambda *a: None)
    assert FakeProvider.made == []  # painted once, never again


def test_gemini_depleted_credits_are_an_account_error(tmp_path):
    """2026-10-22 14:19: a 402 "prepayment credits are depleted" was sent ten times (all refused, $0); now the first one stops."""
    from explainer_engine.imagegen import gemini as G
    from explainer_engine.imagegen.providers.base import AccountError
    from explainer_engine.imagegen.providers.gemini_adapter import Gemini

    class Client:
        spent = 0.0

        def __init__(self, msg):
            self.msg = msg

        def generate(self, *a, **k):
            raise G.GeminiError(self.msg)

    with pytest.raises(AccountError):
        Gemini(tmp_path, client=Client("gemini-nano-banana-2.1: HTTP 402: credits depleted")).generate("x", "p", model="gemini-nano-banana-2.1", size="2K")
    with pytest.raises(ProviderError) as e:
        Gemini(tmp_path, client=Client("gemini-nano-banana-2.1: HTTP 500: busy")).generate("x", "p", model="gemini-nano-banana-2.1", size="2K")
    assert not isinstance(e.value, AccountError)
