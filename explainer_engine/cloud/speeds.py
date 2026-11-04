# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M6 & BATCH-M8A/M8B (Cloud Worker, Pod Provisioning & Cost Guard Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/cloud/speeds.py`
# Target Module : explainer_engine/cloud/speeds.py
# Target Classes/Symbols : class SpeedError (methods: ), def load(), def row(), def lookup(), def estimate(), def setup_share(), def record(), def from_units_json()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this cloud execution module with the 4-tier hybrid visual pipeline (`Tier 1 parallax_25d`, `Tier 2 qwen_nextpose`, `Tier 3 ltx_1080p`, `Tier 4 ltx_portrait_720p`), locking `xworld_v2` LoRA weight at `0.7` (`CD-02`), enforcing `8k+1` LTX frame buckets with frame-exact tail trim metadata, enforcing `CD-06` (`living == False`) before dispatching Tier 4 audio-to-video jobs, and recording per-zone (`cold_open..coda`) GPU wall-clock telemetry (`CD-05`) under hard `try/finally` pod termination (`D-78` / `BP-148`).
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this cloud module targets the pre-Master-Mold v2/v3 worker contract and does not propagate `/4` `tension_zone`, `scene_type`, `character_id` voice-clearance tokens (`CD-06`), or per-zone timing telemetry (`CD-05`).
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Prevents wasted GPU spend on invalid payloads, guarantees pod teardown (`$0.00` idle storage leak), and aligns worker execution with `config/cloud_pins.json`.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] RunPod Pods Pricing & Per-Second Billing
#        URL: https://docs.runpod.io/pods/pricing
#        Rationale: Details per-second GPU billing for RTX PRO 6000 Blackwell ($1.89/hr Secure Cloud) and H200 SXM ($3.59/hr), requiring hard budget caps and empirical runtime measurement.
#    [2] RunPod Account Billing & Storage Costs
#        URL: https://docs.runpod.io/accounts-billing/billing
#        Rationale: Documents that stopped pods still incur container/volume storage charges until terminated (`runpodctl remove pod`), grounding D-78 / BP-148 auto-teardown.
#    [3] PyTorch torch.compile Tutorial & Cold-Start Behavior
#        URL: https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html
#        Rationale: Explains why compilation overhead is avoided (`compile_mode: none` for <=2 segments in cloud_pins.json) and why cold-start must be amortized.
#    [4] GitHub Docs — About Protected Branches
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
#        Rationale: Specifies required status checks (`quality`), PR-only merge enforcement, and branch protection rules required by GATE-EXT-MAIN-PROTECT.
#    [5] GitHub Docs — Managing Rulesets for a Repository
#        URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
#        Rationale: Specifies ruleset protections preventing force-pushes, accidental branch deletion, and unreviewed merges into main.
#    [6] Python 3.12 What's New — PEP 701 Syntactic Formalization of f-strings
#        URL: https://docs.python.org/3/whatsnew/3.12.html#pep-701-syntactic-formalization-of-f-strings
#        Rationale: Explains why nested double-quotes inside an f-string expression (`blind_check.py:36`) raise SyntaxError on Python 3.11 even though Python 3.12+ permits them.
# =============================================================================

"""``config/job_speeds.json``: seconds per unit of each job type on each card, measured by a pod and written by ``runpod cost``
from the pod's ``units.json`` (P1c, RP-08/RP-09). stdlib only. A row is evidence, so it is never typed by hand and never guessed;
no row means "not measured" and the picker says so (``basis``)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from explainer_engine.core import store
from explainer_engine.core.errors import ContractError

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "config" / "job_speeds.json"
FIELDS = ("job_type", "units", "work_s")  # what a pod's units.json must carry
UNITS_JSON = "units.json"  # in the pod's $EE_OUT, next to stages.txt and beat.txt


# TODO [CLAUDE-CLASS-SYNC: SpeedError] (BATCH-M6 & BATCH-M8A/M8B (Cloud Worker, Pod Provisioning & Cost Guard Synchronization)): Synchronize class `SpeedError` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class SpeedError(ContractError):
    """A speed table or a pod's units.json that is not what the contract says (permanent: fix the file or the pod script)."""


def load(path=None):
    p = Path(path or FILE)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data.get("jobs"), dict) or "margin_unmeasured" not in data or "setup_share_max" not in data:
        raise SpeedError(f"{p}: needs jobs, margin_unmeasured and setup_share_max")
    return data


def row(job, card, data=None):
    """The measured row of a job type on a card, or None (not measured, or an unknown job type)."""
    data = data or load()
    return ((data["jobs"].get(job) or {}).get("rows") or {}).get(card)


def lookup(data, job, card=None):
    """The measured row of ``job`` on ``card``; without a card, the only measured one (several cards: None, the caller must name one).
    Pure: ``data`` is a loaded table, nothing is read from disk."""
    rows = (((data or {}).get("jobs") or {}).get(job) or {}).get("rows") or {}
    if card:
        return rows.get(card)
    return next(iter(rows.values())) if len(rows) == 1 else None


def estimate(job, card, units, data=None):
    """``{work_h, setup_h, basis}`` from a measured row, or None. ``setup_h`` is the measured fixed setup (boot, download, install)
    when the row has one, else 0 and ``setup_known`` False."""
    r = row(job, card, data)
    if not r or not units:
        return None
    setup_min = r.get("setup_min")
    return {"work_h": r["s_per_unit"] * float(units) / 3600, "setup_h": (setup_min or 0) / 60, "setup_known": setup_min is not None,
            "basis": "measured"}


def setup_share(setup_h, work_h):
    """The share of the pod's wall time that is fixed setup (RP-09 refuses a card above ``setup_share_max``)."""
    total = float(setup_h) + float(work_h)
    return float(setup_h) / total if total > 0 else 0.0


def record(job, card, *, cloud, units, work_s, setup_s=None, mb=None, download_s=None, usd=None, source, now=None, path=None):
    """Write the measured row of ``job`` on ``card`` and return it. ``source`` names the pod/run it came from."""
    if not units or units <= 0 or work_s is None or work_s <= 0:
        raise SpeedError("a speed row needs units > 0 and work_s > 0")
    p = Path(path or FILE)
    data = load(p)
    if job not in data["jobs"]:
        raise SpeedError(f"unknown job type {job!r} (known: {', '.join(sorted(data['jobs']))}); add it to config/job_speeds.json in a PR")
    old = data["jobs"][job]["rows"].get(card, {})
    r = {"s_per_unit": round(work_s / units, 4), "setup_min": round(setup_s / 60, 2) if setup_s is not None else old.get("setup_min"),
         "mb_per_s": dict(old.get("mb_per_s") or {}), "usd_per_unit": round(usd / units, 5) if usd else old.get("usd_per_unit"),
         "units": units, "source": source, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if now is None else now))}
    if mb and download_s:
        r["mb_per_s"][cloud] = round(mb / download_s, 2)
    data["jobs"][job]["rows"][card] = r
    store.write_json_atomic(p, data)
    return r


def from_units_json(text):
    """Parse a pod's ``units.json`` (``{job_type, units, work_s, setup_s?, mb?, download_s?}``; the card and the cloud come from the pod's session); SpeedError when it
    is not what the speed table needs."""
    try:
        d = json.loads(text)
    except (TypeError, ValueError) as e:
        raise SpeedError(f"units.json is not JSON ({e})") from e
    if not isinstance(d, dict):
        raise SpeedError(f"units.json must be a JSON object, not {type(d).__name__}")
    missing = [k for k in FIELDS if d.get(k) in (None, "", 0)]
    if missing:
        raise SpeedError(f"units.json lacks {', '.join(missing)}")
    if not isinstance(d["job_type"], str):
        raise SpeedError("units.json: job_type must be a string")
    for k in ("units", "work_s", "setup_s", "mb", "download_s"):
        v = d.get(k)
        if v is None and k not in FIELDS:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")) or v < 0:
            raise SpeedError(f"units.json: {k} must be a non-negative number, not {v!r}")
    return d
