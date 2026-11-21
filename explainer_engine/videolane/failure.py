"""RT-07 for the video route (Fable audit 2026-11-13, FA-16): what happens when a video shot's clip fails its QA, written in
ONE place. The rule (docs/EPISODE_FIRST.md RT-07): a clip is measured; a FAIL gets one retry with a new seed; a second FAIL
falls back to ``still_25d`` with the shot's ``fallback_motion_imitation`` (else the adapter's default), and the record says
so. A retry is a paid generation: it runs only inside the creator's approved scene plan (OR-23) and its cap, never from the
runner. The runner (``episode/run.stage_clips``) and the scene tools read ``decide`` and ``fallback_shot`` from here.

The worker side (P5, 2026-11-13): a clip the model fails to make (no file: the CLI's non-zero exit or an exception in the
session) is retried once in the same container with ``seed + SEED_STEP`` (``modal_ltx_jobs.body``, the row's ``attempts``),
under the same in-container deadline, so the run's timeout and its cap still bound the bill. ``decide`` here is the QA-side
rule for a clip that was made."""
from __future__ import annotations

from explainer_engine.aivideo.wan_adapter import DEFAULT_FALLBACK, MAX_ATTEMPTS, SEED_STEP
from explainer_engine.qa import gates as G


def decide(attempts: list[dict], *, allow_fallback: bool = True) -> dict:
    """The next step for one video shot from its attempts so far (each ``{"status", "seed"?}``, oldest first)."""
    if not attempts:
        return {"action": "generate", "why": "no attempt yet"}
    last = attempts[-1]
    if last.get("status") in (G.PASS, G.REVIEW):
        return {"action": "accept", "why": f"attempt {len(attempts)} is {last['status']}"}
    if len(attempts) < MAX_ATTEMPTS:
        seed = last.get("seed")
        return {"action": "retry", "seed": None if seed is None else int(seed) + SEED_STEP,
                "why": f"attempt {len(attempts)} FAILs: one retry with a new seed (paid, inside the approved plan)"}
    if allow_fallback:
        return {"action": "fallback_25d", "why": f"{len(attempts)} attempts FAIL: the shot falls back to still_25d"}
    return {"action": "fail", "why": f"{len(attempts)} attempts FAIL and the fallback is off"}


def fallback_shot(shot: dict) -> dict:
    """The shot as the 2.5D renderer draws its fallback: the shot with its ``fallback_motion_imitation`` as the motion (the
    record keeps the route ``video`` and says ``fallback_for_wan``, so the mix and the QA know it was replaced)."""
    return dict(shot, motion_imitation=shot.get("fallback_motion_imitation") or DEFAULT_FALLBACK)
