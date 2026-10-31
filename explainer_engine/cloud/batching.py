"""RP-01..RP-10, the batching and card rules of a paid pod, as code (P1c; source: the p9 RunPod re-check, B1..B10, project files
``blueprint_2026-10-29/recheck/p9_runpod.json``). The one home of the text is ``docs/CLOUD_RUNBOOK.md``; this module is what
``runpod create`` asks. stdlib only. Rules that need a measurement refuse only on what the plan states or a row measured; an
unknown is asked for, never assumed (Rule one, OR-22)."""
from __future__ import annotations

SETUP_MULTIPLE = 3        # RP-01: planned GPU work >= 3 x the pod's fixed setup
MEASURE_MAX_USD = 0.30    # RP-01 exempts a measurement pod of a new job type (B5: 3 units, <= $0.30)
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
