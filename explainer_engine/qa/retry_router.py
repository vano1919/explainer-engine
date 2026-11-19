
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


# --- OB-2: a defect decides the action (final plan P-5, W4; table and reasons in docs/OBSERVATION.md) ------------------------
# code -> (action, generative, why). R1 fix in place (trim, mute, reseed, inpaint), R2 prompt patch, R3 new keyframe or
# reference, R4 fallback 2.5D from the approved keyframe. ``generative`` = it spends a generation, so it counts against the two
# retries of shot_state.RETRY_CAP; a trim, a mute and the 2.5D fallback spend none.
R_ACTIONS: dict[str, tuple[str, bool, str]] = {
    "F1": ("R3", True, "identity is restored from the untouched master, not by wording"),
    "F2": ("R2", True, "motion is written as a body mechanic (failure-modes F2)"),
    "F3": ("R2", True, "one motion source, a tighter shot size"),
    "F4": ("R2", True, "the action is rewritten as a body mechanic"),
    "F5": ("R3", True, "an end keyframe gives the clip an end state"),
    "F6": ("R2", True, "exactly one named camera move with a magnitude"),
    "F7": ("R3", True, "the end state of shot N becomes the start of N+1 through a new keyframe"),
    "F8": ("R2", True, "the era's forbidden-object list goes into the prompt"),
    "F9": ("R2", True, "the head count is declared in the prompt"),
    "F10": ("R1", True, "reseed or inpaint the hands; an insert only if two seeds fail"),
    "F11": ("R1", True, "reseed or inpaint the text or mark"),
    "F12": ("R2", True, "the named key source and side go into the prompt"),
    "F13": ("R2", True, "duration and pace are budgeted from the action"),
    "F14": ("R2", True, "contact moments are scheduled on cuts"),
    "F15": ("R1", False, "trim or mute the take; a clip that cannot be trimmed goes to R4"),
    "F16": ("R3", True, "style is restored from the approved reference"),
    "F17": ("R2", True, "the delivery aspect is fixed in the prompt"),
    "F18": ("R1", False, "cut the seam out; long beats are planned as cut sequences"),
    "F19": ("R3", True, "the prop is held in frame or handed to a cut by a new keyframe"),
    "TECH-DECODE": ("R1", True, "the file does not decode: generate it again with a new seed"),
    "TECH-BLACK": ("R1", False, "trim the black stretch"),
    "TECH-FREEZE": ("R2", True, "a frozen picture is F2: write the motion"),
    "TECH-SILENCE": ("R1", False, "mute or trim; a silent beat may be intended"),
    "TECH-OFFSET": ("R1", False, "re-align the audio start in the edit"),
    "TECH-FPS": ("R1", False, "re-time the clip in the edit"),
    "TECH-FRAMES": ("R1", False, "re-time or trim the clip in the edit"),
    "TECH-CUT": ("R1", False, "trim at the unexpected cut (F18)"),
    "TXT-DUP": ("R1", False, "trim the repeated word out of the take"),
    "TXT-FALSE": ("R1", False, "mute the clip audio: words on a silent beat"),
    "TXT-EXTRA": ("R1", False, "trim the extra words"),
    "TXT-MISSING": ("R2", True, "a word is missing: the line is read again (ElevenLabs credits: the creator is asked first)"),
    "TXT-CUT": ("R1", False, "play the take to its end"),
}
_RANK = {"R3": 3, "R2": 2, "R1": 1, "R4": 0}


def action_for_defect(code: str) -> dict:
    """``{"code", "action", "generative", "why"}`` of one defect code; an unknown code is refused (no guessed action)."""
    if code not in R_ACTIONS:
        raise ContractError(f"OB-2: defect code {code!r} has no R1..R4 action in qa/retry_router.R_ACTIONS")
    a, g, why = R_ACTIONS[code]
    return {"code": code, "action": a, "generative": g, "why": why}


def worst(codes: list[str]) -> dict:
    """The action of the most expensive defect (R3 over R2 over R1; a generative one over a free one)."""
    if not codes:
        return {"code": None, "action": "none", "generative": False, "why": "no defect"}
    return max((action_for_defect(c) for c in codes), key=lambda d: (d["generative"], _RANK[d["action"]]))


def consume_retry(states, shot: str, kind: str) -> str:
    """Spend one generative retry of ``shot`` (``kind`` "image" or "clip"): moves IMAGE_OBSERVED -> IMAGE_RETRY or
    VIDEO_OBSERVED -> VIDEO_RETRY. The third raises ``ShotStateError`` (shot_state.RETRY_CAP = 2): take the 2.5D fallback or stop."""
    state = "IMAGE_RETRY" if kind == "image" else "VIDEO_RETRY"
    states.advance(shot, state)
    return state


def decide(states, shot: str, kind: str, codes: list[str]) -> dict:
    """What happens next for a shot with these defects: the worst defect's action; a generative action with no retry left
    becomes R4 (FALLBACK_25D) for a clip and a stop (``ESCALATE``) for a picture. Nothing is advanced here."""
    w = worst(codes)
    left = RETRY_LEFT(states, shot, kind)
    if w["generative"] and left <= 0:
        return {**w, "action": "R4" if kind == "clip" else "ESCALATE", "retries_left": 0,
                "why": f"{w['why']}; the two retries are spent (OB-2)"}
    return {**w, "retries_left": left}


def RETRY_LEFT(states, shot: str, kind: str) -> int:
    from explainer_engine.episode.shot_state import RETRY_CAP
    return RETRY_CAP - states.shot(shot)["retries"]["image" if kind == "image" else "video"]
