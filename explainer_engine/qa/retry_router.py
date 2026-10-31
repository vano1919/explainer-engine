"""P8 retry router and the ``qa_report/1`` writer (docs/CONTRACTS.md, OR-04, CN-13, BP-165).

A failed shot is retried in one fixed order and never a fourth time:

    attempt 1 -> RESEED                      (a new seed; KG-14)
    attempt 2 -> REWEIGHT_REFERENCES         (other reference weights)
    attempt 3 -> FALLBACK_KEYFRAME_LTX       for DIALOGUE_CU (the approved keyframe animated by LTX)
                 FALLBACK_STILL_HOLD         for every other video lane (the approved starting keyframe held still)
    a failed fallback -> ESCALATE_TO_HUMAN   (status of the report, no directive)
    attempt 4 -> ContractError (CN-13)

FALLBACK_STILL_HOLD holds the approved starting keyframe; the old cut-out rig of ``compose/`` does not return (D-75, D-80).
The attempts are counted in ``jobs/<phase>/attempts.json`` (``core/ledger.Attempts``); the checks come from
``training/video_qa.py`` (LT-50..62, CLIP-xx) and ``qa/keyframe_gate.py`` (KG), mapped here and never repeated.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.core.ledger import Attempts
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import keyframe_gate as KG

MAX_ATTEMPTS = KG.MAX_TRIES   # BP-165 max_tries; CN-13 refuses a directive past the ledger's failure limit (the same 3)
RESEED, REWEIGHT = "RESEED", "REWEIGHT_REFERENCES"
FALLBACK_KEYFRAME_LTX, FALLBACK_STILL_HOLD = "FALLBACK_KEYFRAME_LTX", "FALLBACK_STILL_HOLD"
ESCALATE = "ESCALATE_TO_HUMAN"
STAGES = ("keyframe", "clip", "assembled")


def action_for(attempt: int, lane: str, *, fallback_failed: bool = False) -> str:
    """The OR-04 directive of the attempt that is about to run (1-based). ``fallback_failed``: the fallback already ran and
    the shot still fails -> ESCALATE_TO_HUMAN."""
    if lane in contracts.REFUSED_LANES:
        raise ContractError(f"CN-11: lane {lane} is refused: {contracts.REFUSED_LANES[lane]}")
    if attempt > MAX_ATTEMPTS or attempt < 1:
        raise ContractError(f"CN-13: attempt {attempt} of {lane}: after {MAX_ATTEMPTS} attempts the item stops and asks (OR-04)")
    if fallback_failed:
        return ESCALATE
    if attempt == 1:
        return RESEED
    if attempt == 2:
        return REWEIGHT
    return FALLBACK_KEYFRAME_LTX if lane == "DIALOGUE_CU" else FALLBACK_STILL_HOLD


def directive(shot_id: str, attempt: int, lane: str, *, fallback_failed: bool = False) -> dict | None:
    """The ``retry_directive`` of a qa_report/1 (None when the answer is ESCALATE_TO_HUMAN: that is the report's status)."""
    action = action_for(attempt, lane, fallback_failed=fallback_failed)
    return None if action == ESCALATE else {"shot_id": shot_id, "attempt": attempt, "action": action}


def next_attempt(attempts_path: Path | str, shot_id: str, lane: str, cause: str = "", *, fallback_failed: bool = False) -> dict | None:
    """Count one more attempt in ``attempts.json`` and return its directive. The fourth raises ContractError before anything
    is written. Retry k is ``edit.router`` attempt k + 1 (the first render is attempt 1); the row is tagged ``kind="render"`` for
    ``ledger.count_renders``. ``REWEIGHT_REFERENCES`` has no router input yet (reference weights come from the card), so it reseeds at best."""
    log = Attempts(attempts_path, at_level=MAX_ATTEMPTS, escalated=0)
    n = len(log.rows()) + 1
    d = directive(shot_id, n, lane, fallback_failed=fallback_failed)
    log.add(cause or f"{shot_id}: attempt {n}", kind="render")
    return d


def still_hold(keyframe: Path | str, frames: int, fps: float) -> dict:
    """The plan of FALLBACK_STILL_HOLD: the approved starting keyframe held for the shot's length."""
    keyframe = Path(keyframe)
    if not keyframe.exists():
        raise ContractError(f"FALLBACK_STILL_HOLD needs the approved starting keyframe: {keyframe} does not exist")
    return {"kind": "still_hold", "source": str(keyframe), "sha256": contracts.sha256_file(keyframe), "frames": int(frames),
            "fps": fps, "seconds": round(frames / fps, 4)}


def render_still_hold(plan: dict, out: Path | str) -> Path:
    """Render the plan with ffmpeg (a silent H.264 clip of exactly ``frames`` frames)."""
    out = Path(out)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(plan["fps"]), "-i", plan["source"],
                    "-frames:v", str(plan["frames"]), "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p", "-an",
                    str(out)], check=True)
    return out


# --- checks from the existing gates --------------------------------------------------------------------------------------
def from_findings(findings: list[dict], *, prefix: str = "") -> list[dict]:
    """``training/video_qa`` rows {rule, status, msg} (status FAIL / REVIEW / PASS / INFO) as qa_report/1 checks."""
    out, seen = [], {}
    for f in findings:
        n = seen[f["rule"]] = seen.get(f["rule"], 0) + 1
        sev = f["status"] if f["status"] in ("FAIL", "REVIEW") else "INFO"
        out.append({"check_id": f"{prefix}{f['rule']}" + (f"#{n}" if n > 1 else ""), "rule": f["rule"], "severity": sev,
                    "measured": f["msg"], "threshold": None, "passed": sev == "INFO"})
    return out


def from_keyframe_verdict(shot_id: str, verdict: dict) -> list[dict]:
    """``qa/keyframe_gate.verdict`` ({status, fails, reviews}) as checks: a hard miss is a FAIL row, a soft or unreadable
    answer a REVIEW row, and a PASS leaves one INFO row."""
    rows = [{"check_id": f"{shot_id}:{x['code']}", "rule": "KG", "severity": sev, "measured": str(x["got"]), "threshold": x["q"],
             "passed": False} for sev, key in (("FAIL", "fails"), ("REVIEW", "reviews")) for x in verdict[key]]
    return rows or [{"check_id": f"{shot_id}:KG", "rule": "KG", "severity": "INFO", "measured": verdict["status"],
                     "threshold": None, "passed": True}]


def status_of(checks: list[dict], directive_: dict | None = None, *, escalated: bool = False) -> str:
    """PASS when nothing failed; WARN_REVIEW when only REVIEW rows failed; a failed FAIL row is REPAIR_APPLIED while a retry
    directive is dispatched and ESCALATE_TO_HUMAN when there is none (or ``escalated``)."""
    if escalated:
        return "ESCALATE_TO_HUMAN"
    if any(c["severity"] == "FAIL" and not c["passed"] for c in checks):
        return "REPAIR_APPLIED" if directive_ else "ESCALATE_TO_HUMAN"
    return "WARN_REVIEW" if any(not c["passed"] for c in checks) else "PASS"


def build_report(job_id: str, stage: str, checks: list[dict], directive_: dict | None = None, *, escalated: bool = False) -> dict:
    if stage not in STAGES:
        raise ContractError(f"qa stage {stage!r} is not one of {STAGES}")
    return {"schema": "qa_report/1", "job_id": job_id, "stage": stage, "status": status_of(checks, directive_, escalated=escalated),
            "checks": checks, "retry_directive": directive_}


def write_report(job_dir: Path | str, report: dict) -> Path:
    """``<job_dir>/qa/<stage>.qa_report.json``, validated first (CN-13: PASS never carries a failed FAIL row)."""
    contracts.validate(report, job_dir)
    path = Path(job_dir) / "qa" / f"{report['stage']}.qa_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, report)
    return path
