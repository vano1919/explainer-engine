"""CR-16: no unit test writes into the real ``tools/runpod/`` (session files, notify log, incidents)."""
import pytest

from explainer_engine.cloud import runpod as R


@pytest.fixture(autouse=True)
def _isolated_runpod_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path / "rp_default")
    yield


@pytest.fixture
def real_dryrun():
    """Ask for this fixture to run the real ``dryrun.passed``: every other unit test treats the dry run (P1b, CR-18) as done, so the
    older tests of the create flow stay about what they test."""


@pytest.fixture(autouse=True)
def _dryrun_isolated(request, tmp_path, monkeypatch):
    from explainer_engine.cloud import dryrun as D
    monkeypatch.setattr(D, "DIR", tmp_path / "dryrun_default")
    if "real_dryrun" not in request.fixturenames:
        monkeypatch.setattr(D, "passed", lambda text, **kw: [])
    yield


@pytest.fixture(autouse=True)
def _job_speeds_isolated(tmp_path, monkeypatch):
    """P1c: ``runpod cost`` writes measured speed rows; a unit test never writes the committed config/job_speeds.json."""
    import shutil

    from explainer_engine.cloud import speeds as S
    copy = tmp_path / "job_speeds.json"
    shutil.copy(S.FILE, copy)
    monkeypatch.setattr(S, "FILE", copy)
    yield


@pytest.fixture
def word(tmp_path, monkeypatch):
    """D-133: an isolated record file of the creator's word; ``word("CH-03", "cmsg_1", ago_s=0)`` records a cheapest-run waiver."""
    import time

    from explainer_engine import governance
    from explainer_engine.governance import records
    root = tmp_path / "gov_root"
    monkeypatch.setattr(governance, "ROOT", root)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    def add(rule, message_id, ago_s=0.0):
        return records.add("cheapest_waive", rule, message_id, "his words", root=root, now=time.time() - ago_s)
    return add


def make_offer(entry="smoke", gpu="H100", worker="explainer_engine/training/pods/ltx/modal_ltx_jobs.py", now=None):
    """CH-07: a passing ``paid_offer/1`` (free credit first, today's cards, two priced combinations, the cheapest chosen)."""
    import datetime as dt

    from explainer_engine.cloud import paid_offer as P
    now = now or dt.datetime.now(dt.timezone.utc)
    t = P._iso(now)
    setup = {"cpu": 8, "memory_gib": 96, "model_loads_per_container": 1, "containers": 1, "scenes": 1, "clips": 4,
             "clip_s": [5, 5, 5, 5], "generated_s": 20, "scaledown_s": 2}
    offer = {
        "schema": P.SCHEMA, "job": "test", "launch": {"worker": worker, "entry": entry},
        "credit": {"checked_at": t, "source": "ledger_sum", "ref": "test ledgers", "monthly_free_usd": 30.0,
                   "used_usd": 29.9, "free_left_usd": 0.1},
        "gpus": {"checked_at": t, "source": "modal_pricing_page", "ref": P.PRICING_URL, "status_source": P.STATUS_URL,
                 "functions_status": "operational", "notices": [], "cpu_core_usd_s": 0.0000131, "mem_gib_usd_s": 0.00000222,
                 "rows": [{"gpu": "H100", "usd_s": 0.001097, "vram_gb": 80}, {"gpu": "A100-80GB", "usd_s": 0.000694, "vram_gb": 80},
                          {"gpu": "L40S", "usd_s": 0.000542, "vram_gb": 48}]},
        "need": {"vram_gb": 80, "basis": "known", "ref": "LTX-2.5 22B ran on 80 GB (the battle run)"},
        "combos": [dict(setup, id="a", gpu=gpu, gpu_s=200, worst_gpu_s=300, speed_basis="measured", speed_ref="battle run"),
                   dict(setup, id="b", gpu="A100-80GB", gpu_s=400, worst_gpu_s=600, speed_basis="estimate",
                        speed_ref="modal_schedule.GPUS speed 0.6")],
        "chosen": "a", "cap_usd": 1.0, "watchdog": {"model": "haiku", "effort": "low", "every_min": 2},
    }
    return P.price(offer)


@pytest.fixture
def paid_offer(tmp_path):
    """``paid_offer("smoke")`` writes a passing CH-07 offer for that LTX rung and returns its path."""
    import json

    def write(entry="smoke", **kw):
        p = tmp_path / f"offer_{entry}.json"
        p.write_text(json.dumps(make_offer(entry, **kw)))
        return p
    return write
