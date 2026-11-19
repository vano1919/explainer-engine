"""W5 (the creator 2026-11-19 20:07 UTC): the Klein picture batch on Modal. No Modal, no money, no network, no GPU: the container body gets
fake downloads, a fake HF API and a fake generator; the ladder, the ledger and the clock are the real ones."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from test_klein_runpod import Api, Gen, Op, _batch

from explainer_engine.cloud import hooks as H
from explainer_engine.cloud import modal_run as MR
from explainer_engine.core import spend_caps
from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.training.pods.klein import klein_jobs as K
from explainer_engine.training.pods.klein import modal_klein_jobs as W

PLAN = "cd" * 32
KLEIN = "explainer_engine/training/pods/klein/modal_klein_jobs.py"
SECRET = "very-secret-token-value"
ENV = {"MODAL1_TOKEN_ID": "ak-1", "MODAL1_TOKEN_SECRET": SECRET, "MODAL1_PROFILE": "second",
       "MODAL_TOKEN_ID": "ak-1", "MODAL_TOKEN_SECRET": SECRET, "MODAL_PROFILE": "second"}


def test_the_modal_section_is_pinned_the_rate_is_the_price_table_and_every_timeout_fits_the_cap():
    L = W.LAUNCH
    assert W.modal_problems(L) == [] and W.gpus(L) == ["L40S", "A100-80GB"]
    assert W.stated_rate(L) == W.rate_usd_h(L) == 2.2373 and L["modal"]["prices_date"] and L["modal"]["prices_source"]   # source and date recorded
    assert L["cap_usd"] == 1.0 and L["modal"]["caps"]["run_usd"] == 0.65 and L["modal"]["startup_timeout_s"] == 120 and L["modal"]["scaledown_window_s"] <= 5
    for gpu in W.gpus(L):
        smoke_t, run_t = W.timeouts(L, gpu)
        h = W.stated_rate(L, gpu)
        c = L["modal"]
        assert run_t * h / 3600 + c["cold_start_s"] * h / 3600 <= c["caps"]["run_usd"] + 1e-9      # the hard bill, cold start included, stays in the cap
        assert smoke_t * h / 3600 + c["cold_start_s"] * h / 3600 <= c["caps"]["smoke_usd"] + 1e-9 and run_t > smoke_t > W.MARGIN_S
    bad = copy.deepcopy(L)
    bad["modal"]["usd_per_h"]["L40S"] = 1.0                                                     # a rate that is not the dated table's
    assert any("price table" in p for p in W.modal_problems(bad))
    bad = copy.deepcopy(L)
    bad["modal"]["caps"]["run_usd"] = 1.01                                                      # above the creator's recorded cap
    assert any("above the creator's recorded cap_usd" in p for p in W.modal_problems(bad))
    bad = copy.deepcopy(L)
    bad["modal"]["scaledown_window_s"] = 60                                                     # no warm container
    assert any("scaledown_window_s" in p for p in W.modal_problems(bad))
    assert W.timeouts(dict(L, modal={})) is None


def test_a_paid_preflight_refuses_with_no_modal_line_and_with_a_wrong_account(monkeypatch, tmp_path):
    monkeypatch.setattr(spend_caps, "load", lambda *a, **k: {"per_episode": {}})               # no `modal` line: a zero approved budget
    offer = tmp_path / "offer.json"
    offer.write_text("{}")
    with pytest.raises(SystemExit, match="no modal per_run_usd in config/spend_caps.json"):
        W.preflight(W.LAUNCH, env=dict(ENV, EE_PAID_OFFER=str(offer)))
    with pytest.raises(SystemExit, match="CH-07"):                                              # and no passing paid offer: still refused
        W.preflight(W.LAUNCH, env=dict(ENV))
    monkeypatch.setattr(spend_caps, "load", lambda *a, **k: {"modal": {"per_run_usd": 0.7}})   # a line under the cap's 80 % rule (0.56 < the 0.65 run cap)
    with pytest.raises(SystemExit, match="above 80 % of the creator's"):
        W.preflight(W.LAUNCH, env=dict(ENV, EE_PAID_OFFER=str(offer)))
    with pytest.raises(SystemExit, match="MODAL1"):
        W.preflight(W.LAUNCH, env=dict(ENV, MODAL_TOKEN_ID="ak-other"))


def test_the_second_account_must_be_the_active_one_and_its_values_are_never_printed():
    assert W.token_problems(ENV) == []
    assert any("MODAL1_TOKEN_ID is not set" in p for p in W.token_problems({}))
    bad = W.token_problems(dict(ENV, MODAL_TOKEN_SECRET="the-first-accounts-secret"))
    assert bad and not any(SECRET in p or "the-first-accounts-secret" in p for p in bad)
    assert any("MODAL_PROFILE" in p for p in W.token_problems(dict(ENV, MODAL_PROFILE="first")))


def test_the_ladder_order_is_enforced_and_bound_to_the_launch_and_worker_bytes(tmp_path):
    ladder = tmp_path / "ladder.json"
    pr = W.proof(W.LAUNCH)
    with pytest.raises(SystemExit, match="needs"):
        W.ladder_gate("L3", path=ladder)                                                        # L3 before L0..L2: refused
    MR.record_rung(ladder, "L0", True, commit="abc123")
    W.record("L1", True, path=ladder)
    with pytest.raises(SystemExit, match=r"rung L3 needs \['L2'\]"):
        W.ladder_gate("L3", path=ladder)
    W.record("L2", True, path=ladder)
    W.ladder_gate("L3", path=ladder)                                                            # in order: allowed
    lad = json.loads(ladder.read_text())
    assert lad["rungs"]["L1"]["launch_sha"] == pr["launch_sha"] and lad["rungs"]["L1"]["worker_sha"] == pr["worker_sha"]
    changed = dict(W.LAUNCH, cap_usd=0.9)                                                       # another launch file: the green rungs are stale
    with pytest.raises(SystemExit, match="another launch file or worker"):
        W.ladder_gate("L3", path=ladder, launch=changed)
    with pytest.raises(SystemExit, match="red"):
        W.record("L3", False, path=ladder, result={"state": "FAILED"})
    with pytest.raises(SystemExit, match="rung L3 is red"):
        W.ladder_gate("L4", path=ladder)


def test_the_container_fetches_only_sha_named_files_and_checks_each_hash(tmp_path):
    code, batch = b"code-bytes", b"batch-bytes"
    pins = {"code": hashlib.sha256(code).hexdigest(), "batch": hashlib.sha256(batch).hexdigest()}
    paths = W.hf_paths(pins)
    assert paths["code"] == f"code/klein/ee_src-{pins['code']}.tar.gz" and paths["batch"] == f"code/klein/batch-{pins['batch']}.tar.gz"
    real = W.pins_of_script()
    assert all(len(v) == 64 for v in real.values()) and all("main" not in v for v in W.hf_paths(real).values())
    asked = []

    def dl(name, dest):
        asked.append(name)
        p = Path(dest) / Path(name).name
        p.write_bytes(code if "ee_src" in name else batch)
        return str(p)
    got = W.fetch_pinned(paths, pins, tmp_path / "ok", download=dl)
    assert asked == [paths["code"], paths["batch"]] and got["code"].read_bytes() == code
    with pytest.raises(SystemExit, match="the pin says"):                                      # a replaced file under the same name: nothing runs
        W.fetch_pinned(paths, dict(pins, batch="00" * 32), tmp_path / "bad", download=dl)
    with pytest.raises(SystemExit, match="not a sha256-named file"):                           # a fixed name on main is never read
        W.fetch_pinned({"code": "code/klein/ee_src.tar.gz", "batch": paths["batch"]}, pins, tmp_path / "main", download=dl)


def test_the_ledger_reserves_before_the_call_refuses_a_repeat_and_settles_at_the_wall_clock(tmp_path):
    path = str(tmp_path / "ledger.json")
    run = W.reserve_launch(path, "klein_main_x", 1.0, 3.5)                                      # 1.0 <= 80 % of 3.5
    assert run.data["reserved"]["klein_main_x"]["amount"] == 1.0 and "klein_main_x" in run.data["items"]["launch"]
    with pytest.raises(SystemExit, match="launched already"):
        W.reserve_launch(path, "klein_main_x", 1.0, 3.5)                                        # a repeat would pay twice
    usd = W.settle_launch(run, "klein_main_x", 600, 2.2373)
    assert usd == round(600 * 2.2373 / 3600, 4) and Run.open(path).spent("modal_usd") == pytest.approx(usd)
    with pytest.raises(CapReached, match="80 %"):
        W.reserve_launch(str(tmp_path / "l2.json"), "klein_main_y", 1.0, 1.0)                  # a $1 line cannot carry a $1 reservation


def _bundle(tmp_path, batch):
    """The two sha-named files of a run: a code bundle (empty, the repo's own klein_jobs is already imported) and the real batch tarball."""
    def tar(name, files):
        p = tmp_path / name
        with tarfile.open(p, "w:gz") as tf:
            for fn, data in files.items():
                ti = tarfile.TarInfo(fn)
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
        return p
    code = tar("c.tar.gz", {"README": b"code"})
    bt = tar("b.tar.gz", {"batch.json": json.dumps(batch).encode()})
    pins = {"code": hashlib.sha256(code.read_bytes()).hexdigest(), "batch": hashlib.sha256(bt.read_bytes()).hexdigest()}
    paths = W.hf_paths(pins)
    return pins, paths, (lambda name, dest: str(code if "ee_src" in name else bt))


def _launch_with_files(tmp_path):
    L = copy.deepcopy(W.LAUNCH)
    m = L["models"][L["model"]]
    m["files"] = {"transformer/model.safetensors": hashlib.sha256(b"x").hexdigest(), "vae/config.json": "12" * 20}
    m["sizes"] = {k: 1 for k in m["files"]}
    root = K.weights_root(L, str(tmp_path / "vol"))
    for f in ("transformer/model.safetensors",):
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_bytes(b"x")
    cfg = root / "vae" / "config.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_bytes(b"x")
    m["files"]["vae/config.json"] = K.file_id(cfg, "12" * 20) if False else _blob(cfg)
    return L, str(tmp_path / "vol")


def _blob(p):
    data = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_the_body_sets_the_clock_and_cap_that_run_reads_and_calls_run_unchanged(tmp_path, monkeypatch):
    L, vol = _launch_with_files(tmp_path)
    pins, paths, dl = _bundle(tmp_path, _batch(2))
    seen = {}

    def fake_run(batch, out, **kw):
        import os
        seen.update(kw, price=os.environ["EE_PRICE"], cap=os.environ["EE_MAX_USD"], created=os.environ["EE_CREATED"], n=len(batch["jobs"]))
        return {"end": "DONE", "spent_usd": 0.2, "price_source": "EE_PRICE", "cap_source": "EE_MAX_USD", "steps": {}, "pictures": []}
    for k in ("EE_PRICE", "EE_MAX_USD", "EE_CREATED"):
        monkeypatch.setenv(k, "0")                                                              # restored by monkeypatch after the test
    res = W.body({"paths": paths, "pins": pins, "cap_usd": 1.0}, L, gpu="L40S", timeout_s=1340, vol_root=vol, work=tmp_path / "w",
                 download=dl, now=lambda: 5000.0, run_fn=fake_run, baked=tmp_path / "none")
    assert res["state"] == "DONE" and seen["price"] == "2.2373" and seen["cap"] == "1.0" and float(seen["created"]) == 5000.0 - 120
    assert res["clock"] == {"price_usd_per_h": 2.2373, "cap_usd": 1.0, "cold_start_s": 120} and seen["n"] == 2
    assert seen["launch"]["weights_dir"] == "/w/klein" and seen["launch"]["minutes"]["download"] == [0, 0, 0]   # the Volume holds the weights: no download minutes
    res = W.body({"paths": paths, "pins": pins, "cap_usd": 1.0}, L, gpu="A100-80GB", timeout_s=1055, vol_root=vol, work=tmp_path / "w2",
                 download=dl, now=lambda: 5000.0, run_fn=fake_run, baked=tmp_path / "none")
    assert seen["price"] == "2.7845"                                                            # the fallback card runs on its own rate
    res = W.body({"paths": paths, "pins": pins, "cap_usd": 1.0}, L, gpu="H100", timeout_s=1000, vol_root=vol, work=tmp_path / "w3",
                 download=dl, now=lambda: 5000.0, run_fn=fake_run, baked=tmp_path / "none")
    assert res["state"] == "FAILED" and "not one of the launch's cards" in res["error"]


def test_the_body_refuses_unstaged_weights_on_the_gpu_and_a_replaced_bundle(tmp_path):
    L, vol = _launch_with_files(tmp_path)
    pins, paths, dl = _bundle(tmp_path, _batch(2))
    res = W.body({"paths": paths, "pins": pins, "cap_usd": 1.0}, L, gpu="L40S", timeout_s=1340, vol_root=str(tmp_path / "empty"),
                 work=tmp_path / "w", download=dl, run_fn=lambda *a, **k: pytest.fail("run must not start"), baked=tmp_path / "none")
    assert res["state"] == "FAILED" and "not staged on the Volume" in res["error"]          # L2 runs on CPU, never on the paid card
    res = W.body({"paths": paths, "pins": dict(pins, code="00" * 32), "cap_usd": 1.0}, L, gpu="L40S", timeout_s=1340, vol_root=vol,
                 work=tmp_path / "w2", download=dl, run_fn=lambda *a, **k: pytest.fail("run must not start"), baked=tmp_path / "none")
    assert res["state"] == "FAILED" and "the pin says" in res["error"]
    other = dict(L, cap_usd=0.5)                                                                # the launch passed in must be the baked one's shape
    assert W.container_gate(other, baked=tmp_path / "none") and any("run_usd" in p for p in W.container_gate(other))


def test_each_picture_is_uploaded_and_verified_before_the_next_one_through_the_body(tmp_path, monkeypatch):
    L, vol = _launch_with_files(tmp_path)
    pins, paths, dl = _bundle(tmp_path, _batch(2))
    api, gen = Api(), Gen()

    def ordered_gen(job, launch, refs, png):
        api.order.append("gen:" + job["id"])
        gen(job, launch, refs, png)
    for k in ("EE_PRICE", "EE_MAX_USD", "EE_CREATED"):
        monkeypatch.setenv(k, "0")
    res = W.body({"paths": paths, "pins": pins, "cap_usd": 1.0}, L, gpu="L40S", timeout_s=1340, vol_root=vol, work=tmp_path / "w",
                 download=dl, now=lambda: 5000.0, api=api, baked=tmp_path / "none", generate=ordered_gen, clock=lambda: 5300.0, upload_op=Op,
                 fetch=lambda spec, dest: Path(dest), tmp=str(tmp_path / "in"))
    assert res["state"] == "DONE", res
    assert api.order[:6] == ["gen:L3_smoke", "upload", "gen:P0", "upload", "gen:P1", "upload"]   # OR-33: each one on HF before the next starts
    assert set(api.order[6:]) == {"upload"} and api.order[6:]                                  # E6: run_record.json and modal_record.json go up at the end
    assert (tmp_path / "w" / "out" / "modal_record.json").is_file()
    assert res["price_source"] == "EE_PRICE" and res["cap_source"] == "EE_MAX_USD"
    assert res["spent_usd"] == pytest.approx((300 + 120) / 3600 * 2.2373, abs=0.005)           # the clock includes the cold start at the card's rate


def test_the_hook_knows_the_klein_worker_and_lets_only_its_free_rung_through_without_a_go():
    assert H.modal_refusal(f"modal run {KLEIN}::check") is None                                # L1: the entrypoint's own ladder gate holds it
    for entry in ("weights", "smoke", "main"):
        assert "EE_MODAL_GO" in H.modal_refusal(f"modal run {KLEIN}::{entry} --plan p.json", env={})
    assert H.modal_refusal(f"EE_MODAL_GO=cmsg_1:abcdefabcdef modal run {KLEIN}::main --plan p.json") is None
    assert H.worker_api_refusal("python -c 'import modal_klein_jobs as m; m.GPU_FUNCS[0].remote()'")   # driven from python: refused
    assert H.paid_looking(f"python {KLEIN}")


def test_the_creators_modal_line_is_3_50_a_run_with_no_episode_line():
    m = spend_caps.modal()                                                                      # the creator's typed answer, 2026-11-19 20:18 UTC
    assert m["per_run_usd"] == 3.5 and "per_episode_usd" not in m and "cmsg_01Hnu5zB86sjUj5GtTgaUkPWS3PzAxqNtHbt57o5A2pUPb" in m["decided"]
    with pytest.raises(spend_caps.OverCeiling, match="per_episode_usd"):
        spend_caps.modal(episode=True)                                                          # an episode's Modal runs still wait for his episode line
    assert W.LAUNCH["modal"]["caps"]["run_usd"] <= 0.8 * m["per_run_usd"]                       # the Klein cap passes the ledger's 80 % rule


def test_the_caps_sum_to_the_creators_total_and_the_weights_check_on_the_gpu_is_size_only(tmp_path):
    L, vol = _launch_with_files(tmp_path)
    c = L["modal"]["caps"]
    assert c["smoke_usd"] + c["run_usd"] <= L["cap_usd"] + 1e-9                                 # E1: his Klein $1 is the total, smoke included
    over = json.loads(json.dumps(L)); over["modal"]["caps"]["run_usd"] = 0.7
    assert any("smoke_usd" in p and "total" in p for p in W.modal_problems(over, check_table=False))
    assert L["modal"]["torch_pin"] and "cu128" in L["modal"]["torch_cuda_index"]                # E3: torch is installed explicitly, L1 proves it
    from explainer_engine.training.pods.klein import klein_jobs as K
    f = sorted(K.model_of(L)["files"])[0]
    p = K.weights_root(L, vol) / f
    p.write_bytes(p.read_bytes() + b"x")                                                        # a wrong size is caught without hashing
    assert any(f in b for b in W.check_weights(L, vol, hash_files=False))
