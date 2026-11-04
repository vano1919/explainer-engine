# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M6 & BATCH-M8A/M8B (Cloud Worker, Pod Provisioning & Cost Guard Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/cloud/batching.py`
# Target Module : explainer_engine/cloud/batching.py
# Target Classes/Symbols : def rp01(), def rp02(), def rp03(), def rp09(), def rp10()
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

"""RP-01..RP-10, the batching and card rules of a paid pod, as code (P1c; source: the p9 RunPod re-check, B1..B10, project files
``blueprint_2026-10-29/recheck/p9_runpod.json``). The one home of the text is ``docs/CLOUD_RUNBOOK.md``; this module is what
``runpod create`` asks. stdlib only. Rules that need a measurement refuse only on what the plan states or a row measured; an
unknown is asked for, never assumed (Rule one, OR-22)."""
from __future__ import annotations

SETUP_MULTIPLE = 3        # RP-01: planned GPU work >= 3 x the pod's fixed setup
MEASURE_MAX_USD = 0.50    # RP-01 exempts a measurement pod of a new job type (B5: 3 units, <= $0.30)
HW_ATTEMPTS = 2           # RP-10: the first try and ONE retry on another card
EXEMPT_TESTS = ("p12a_smoke",)  # the smoke pods of the paid plan: tiny by design, they exist to measure setup itself


def rp01(work_min, setup_min, *, measure=False, max_usd=None, test=None):
    """RP-01: refusals when the planned work is under ``SETUP_MULTIPLE`` x the fixed setup, or either number is not stated."""
    if test in EXEMPT_TESTS:
        return []
    if measure:
        return [] if (max_usd is not None and max_usd <= MEASURE_MAX_USD + 1e-9) else \
            [f"RP-01: --measure is for a 3-unit measurement pod of at most ${MEASURE_MAX_USD}; this pod asks ${max_usd}"]
    if work_min is None or setup_min is None:
        return ["RP-01: state the job's planned GPU work and its fixed setup: --work-min M --setup-min S (or --measure for a "
                f"3-unit measurement pod <= ${MEASURE_MAX_USD}); the plan, not a guess"]
    if work_min < SETUP_MULTIPLE * setup_min - 1e-9:
        return [f"RP-01: planned work {work_min:g} min is under {SETUP_MULTIPLE} x the fixed setup {setup_min:g} min: merge this job "
                "with another on the same weights, or wait for the next batch"]
    return []


def rp02(weights, earlier, *, reason=""):
    """RP-02: one pod for the jobs on the same weights. ``earlier`` = the weight sets of the pods this ledger already paid for;
    a second pod with the same non-empty set needs a stated reason (kept in the ledger)."""
    w = sorted(set(weights or ()))
    if w and any(sorted(set(e)) == w for e in earlier or ()) and not reason.strip():
        return [f"RP-02: this ledger already has a pod on the same weights ({', '.join(w)}): run the jobs on ONE pod, or give "
                "--second-pod-reason with the reason"]
    return []


def rp03(body):
    """RP-03: no network volume (break-even in docs/COST_AND_TIME_MODEL.md)."""
    mounts = body.get("mounts") or {}
    return ["RP-03: a network volume is not used (docs/COST_AND_TIME_MODEL.md, break-even)"] if (
        "networkVolumeId" in body or "network" in mounts or any("network" in str(k).lower() for k in mounts)) else []


def rp09(rows, *, share_max, refused=None):
    """RP-09: drop the cards whose fixed setup is over ``share_max`` of the pod's wall time (rows carry ``setup_share``); the
    reasons go into ``refused`` when given."""
    kept = []
    for r in rows:
        if r.get("setup_share") is not None and r["setup_share"] > share_max + 1e-9:
            if refused is not None:
                refused.append(f"RP-09: {r['gpu']} ({r['cloud']}): setup is {r['setup_share']:.0%} of the job, over {share_max:.0%}")
        else:
            kept.append(r)
    return kept


HW_EXTRA_MAX = 2          # RP-10: at most this many creator-granted extra hardware tries per create command


def rp10(hw_failures, script_failed, *, key="", extra=0, extra_reason=""):
    """RP-10: a hardware failure (no capacity, BAD_HOST) gets one retry; a script failure gets no paid retry of the same text.
    ``extra`` = tries the creator granted in words (``--hw-extra-retries N --hw-extra-reason "<his message id>"``); a grant
    without a reason, or over ``HW_EXTRA_MAX``, is ignored, so the guard is never opened without his recorded word."""
    out = []
    if extra and not extra_reason.strip():
        out.append("RP-10: --hw-extra-retries needs --hw-extra-reason (the creator's message id); it is not granted without it")
        extra = 0
    extra = max(0, min(int(extra or 0), HW_EXTRA_MAX))
    if hw_failures >= HW_ATTEMPTS + extra:
        out.append(f"RP-10: {hw_failures} failed create or BAD_HOST pod(s) on {key or 'this job'}: the one retry is used; stop and ask the creator")
    if script_failed:
        out.append("RP-10: this exact script already failed on a pod (not hardware): fix it and pass `runpod dryrun` on the new text first")
    return out
