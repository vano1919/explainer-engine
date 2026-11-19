"""OB-1: nothing generated moves on unseen (final plan P-5, 5.4; docs/OBSERVATION.md).

Every picture, clip and voice take gets observation records (``schemas/observation_record.schema.json``) bound to its sha256, kept as
JSONL in ``<episode>/qa/observations.jsonl``. The observers (``qa/observers/``) return records, never a bare bool. The stage gate
(``gate_rows``, called by ``episode/run.py`` at the start of ``clips`` and ``assemble``) refuses a picture or clip without a PASS
record for its CURRENT hash: a changed file has a different sha256, so its old records no longer count.

An automatic observer (ffmpeg, transcript, gemini_api) decides alone only after the creator accepted its calibration report
(``config/observer_calibration.json``); until then its PASS counts only after the session or the creator looked at its evidence
and wrote that into the record (``review``). Defects map to one action R1..R4 in ``qa/retry_router.py`` (OB-2).

    python -m explainer_engine.qa.observe status <episode folder>
    python -m explainer_engine.qa.observe gate <episode folder> --stage clips|assemble
    python -m explainer_engine.qa.observe review <episode folder> <record_id> --by session|owner [--note T] [--message-id M]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.store import write_text_atomic
from explainer_engine.episode import shot_state as SS
from explainer_engine.qa import gates as G
from explainer_engine.qa import retry_router as RR
from explainer_engine.qa import status as ST

SCHEMA = "observation_record/1"
REL = "qa/observations.jsonl"
KINDS = ("image", "clip", "voice")
OBSERVERS = ("claude", "gemini_chat", "gemini_api", "ffmpeg", "transcript")
# The observers whose PASS needs a look of the session or the creator until their calibration report is accepted.
AUTOMATIC = ("ffmpeg", "transcript", "gemini_api")
# What each kind needs before it may move on: every group must hold a PASS (one observer of the group is enough to be present;
# the worst record of the group decides).
REQUIRED = {"image": (("claude", "gemini_chat", "gemini_api"),),
            "clip": (("ffmpeg",), ("claude", "gemini_chat", "gemini_api")),
            "voice": (("transcript",),)}
STAGE_KIND = {"clips": ("image", "image"), "assemble": ("clip", "clip")}   # stage -> (kind, shot_state asset key)
ROOT = Path(__file__).resolve().parents[2]
CALIBRATION = ROOT / "config" / "observer_calibration.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def records_path(root: Path) -> Path:
    return Path(root) / REL


def load(root: Path) -> list[dict]:
    p = records_path(root)
    if not p.is_file():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _rewrite(root: Path, rows: list[dict]) -> None:
    write_text_atomic(records_path(root), "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def calibration_accepted(observer: str, path: Path | None = None) -> bool:
    """The creator accepted this observer's calibration report (config/observer_calibration.json, ``accepted.<observer>``)."""
    p = Path(path or CALIBRATION)
    if not p.is_file():
        return False
    return bool((json.loads(p.read_text(encoding="utf-8")).get("accepted") or {}).get(observer))


def record_id(ep: str, shot: str, kind: str, observer: str, sha: str) -> str:
    return f"obs:{ep}:{shot}:{kind}:{observer}:{sha[:12]}:{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}"


def verdict_of(defects: list[dict], *, generative_left: bool = True) -> str:
    """No defect or only info -> PASS; a minor defect -> REVIEW; a major one -> RETRY, or BLOCK when its action is generative
    and the two retries of OB-2 are spent."""
    if any(d["severity"] == "major" for d in defects):
        worst = RR.worst([d["code"] for d in defects if d["severity"] == "major"])
        return ST.BLOCK if (worst["generative"] and not generative_left) else ST.RETRY
    return ST.REVIEW if any(d["severity"] == "minor" for d in defects) else ST.PASS


def build(root: Path, shot: str, kind: str, observer: str, path: str, *, questions=None, answers=None, defects=None,
          verdict: str | None = None, evidence=None, note: str | None = None, reviewed: dict | None = None,
          generative_left: bool = True) -> dict:
    """A record for the file at ``path`` (relative to the episode folder or absolute), hashed now. A file that does not exist
    gives a NOT_RUN record with the sha256 of nothing refused: there is no hash to bind, so ``ValueError``."""
    root = Path(root)
    p = Path(path)
    sha = SS.sha256_of(p if p.is_absolute() else root / p)
    if sha is None:
        raise ValueError(f"{path}: no such file; an observation binds to the sha256 of a file")
    defects = list(defects or [])
    if verdict is None:
        verdict = verdict_of(defects, generative_left=generative_left)
    ep = root.name
    asset = next((a for a in _assets(root) if a["shot_id"] == shot and a["sha256"] == sha), None)
    rec = {"schema": SCHEMA, "record_id": record_id(ep, shot, kind, observer, sha), "episode_id": ep, "asset_sha256": sha,
           "asset_id": asset["asset_id"] if asset else None, "asset_path": str(path), "shot_id": shot, "kind": kind,
           "observer": observer, "questions": list(questions or []), "answers": dict(answers or {}), "defects": defects,
           "verdict": ST.canon(verdict), "action": RR.worst([d["code"] for d in defects])["action"] if defects else "none",
           "observed_at": _now(), "evidence": list(evidence or []), "reviewed": reviewed}
    if note:
        rec["note"] = note
    return rec


def _assets(root: Path) -> list[dict]:
    p = Path(root) / "assets" / "asset_records.jsonl"
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()] if p.is_file() else []


def _link_vault(root: Path, rec: dict) -> bool:
    """Write ``observation_record_id`` into the vault record of this asset (same shot and sha256). False when it has none."""
    p = Path(root) / "assets" / "asset_records.jsonl"
    rows = _assets(root)
    hit = False
    for r in rows:
        if r["shot_id"] == rec["shot_id"] and r["sha256"] == rec["asset_sha256"]:
            r["observation_record_id"] = rec["record_id"]
            hit = True
    if hit:
        write_text_atomic(p, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))
    return hit


def write(root: Path, rec: dict) -> dict:
    """Validate, append, link the vault record and move the shot state. Returns the record plus ``settled`` (what the shot
    state did). One record never accepts alone: ``settle`` rolls every required observer up."""
    contracts.validate(rec)
    root = Path(root)
    rows = load(root) + [rec]
    _rewrite(root, rows)
    _link_vault(root, rec)
    return {**rec, "settled": settle(root, rec["shot_id"], rec["kind"], rec["asset_path"], rec["asset_sha256"])}


def current(root: Path, shot: str, kind: str, sha: str) -> dict[str, dict]:
    """The latest record of each observer for this exact hash (a record of any other hash is not counted)."""
    out: dict[str, dict] = {}
    for r in load(root):
        if r["shot_id"] == shot and r["kind"] == kind and r["asset_sha256"] == sha:
            out[r["observer"]] = r
    return out


def counts(rec: dict) -> bool:
    """A PASS record counts when the observer is accepted, or a person looked (``reviewed``); claude/gemini_chat are looks."""
    if rec["verdict"] not in (ST.PASS, "PASS"):
        return False
    if rec["observer"] not in AUTOMATIC:
        return True
    return bool(rec.get("reviewed")) or calibration_accepted(rec["observer"])


def asset_status(root: Path, shot: str, kind: str, sha: str) -> tuple[str, str]:
    """(status, reason) of one asset: PASS, REVIEW, RETRY, BLOCK, NOT_RUN, MISSING (no record for this hash), UNREVIEWED
    (an automatic PASS nobody looked at)."""
    recs = current(root, shot, kind, sha)
    worst: list[str] = []
    for group in REQUIRED[kind]:
        got = [recs[o] for o in group if o in recs]
        if not got:
            return "MISSING", f"no {'/'.join(group)} record for sha256 {sha[:12]}"
        verdicts = [ST.canon(r["verdict"]) for r in got]
        worst.append(ST.rollup(verdicts))
        if worst[-1] == ST.PASS and not all(counts(r) for r in got):
            return "UNREVIEWED", f"{'/'.join(r['observer'] for r in got)}: PASS not looked at and not calibrated"
    s = ST.rollup(worst)
    return s, ", ".join(f"{o}={ST.canon(r['verdict'])}" for o, r in sorted(recs.items()))


def settle(root: Path, shot: str, kind: str, path: str, sha: str) -> dict:
    """Move the shot state from the records of this hash: any real observation -> *_OBSERVED, PASS (every required observer
    counted) -> IMAGE_ACCEPTED / CLIP_ACCEPTED. A state that is not where it must be is a note, never a crash."""
    root = Path(root)
    status, why = asset_status(root, shot, kind, sha)
    out = {"status": status, "why": why, "moves": [], "note": None}
    if kind == "voice" or status in ("MISSING", "NOT_RUN"):
        return out
    states = SS.ShotStates(root)
    steps = {"image": [("IMAGE_GENERATED", None), ("IMAGE_OBSERVED", "IMAGE_ACCEPTED")],
             "clip": [("IMAGE_ACCEPTED", "VIDEO_GENERATED"), ("VIDEO_GENERATED", "VIDEO_OBSERVED"), ("VIDEO_OBSERVED", "CLIP_ACCEPTED")]}[kind]
    try:
        if kind == "image":
            if states.state(shot) == "IMAGE_GENERATED":
                states.advance(shot, "IMAGE_OBSERVED", sha, path)
                out["moves"].append("IMAGE_OBSERVED")
            if status == ST.PASS and states.state(shot) == "IMAGE_OBSERVED":
                states.advance(shot, "IMAGE_ACCEPTED", sha, path)
                out["moves"].append("IMAGE_ACCEPTED")
        else:
            if states.state(shot) == "IMAGE_ACCEPTED":
                states.advance(shot, "VIDEO_GENERATED", sha, path)
                out["moves"].append("VIDEO_GENERATED")
            if states.state(shot) == "VIDEO_GENERATED":
                states.advance(shot, "VIDEO_OBSERVED", sha, path)
                out["moves"].append("VIDEO_OBSERVED")
            if status == ST.PASS and states.state(shot) == "VIDEO_OBSERVED":
                states.advance(shot, "CLIP_ACCEPTED", sha, path)
                out["moves"].append("CLIP_ACCEPTED")
        if out["moves"]:
            states.save()
        elif states.state(shot) not in ("IMAGE_OBSERVED", "VIDEO_OBSERVED", "IMAGE_ACCEPTED", "VIDEO_GENERATED", "CLIP_ACCEPTED"):
            out["note"] = f"shot state is {states.state(shot)}: no move made (the asset is not yet bound at the state this step needs)"
    except SS.ShotStateError as exc:
        out["note"] = f"shot state not moved: {exc}"
    return out


def review(root: Path, rid: str, by: str, note: str = "", message_id: str | None = None) -> dict:
    """Stamp a record: the session or the creator looked at its evidence (never an automatic PASS without it)."""
    root = Path(root)
    rows = load(root)
    rec = next((r for r in rows if r["record_id"] == rid), None)
    if rec is None:
        raise KeyError(f"no observation record {rid!r}")
    rec["reviewed"] = {"by": by, "at": _now(), "note": note, "message_id": message_id}
    contracts.validate(rec)
    _rewrite(root, rows)
    return {**rec, "settled": settle(root, rec["shot_id"], rec["kind"], rec["asset_path"], rec["asset_sha256"])}


# --- the stage gate ---------------------------------------------------------------------------------------------------
def gate_rows(root: Path, stage: str) -> list[dict]:
    """The OB-1 row of ``run_stage`` (``[]`` for a stage that has no gate): every picture (before ``clips``) or clip (before
    ``assemble``) bound to a shot must have a counted PASS record for its current sha256. BLOCK lists the shots; REVIEW only
    when every record is a REVIEW (the stage's REVIEW verdict then needs the creator's ``approve``)."""
    if stage not in STAGE_KIND:
        return []
    kind, key = STAGE_KIND[stage]
    root = Path(root)
    states = SS.ShotStates(root)
    block, review_, ok = [], [], 0
    for shot in sorted(states.doc["shots"]):
        a = states.shot(shot)["assets"].get(key)
        if not a:
            continue
        sha = SS.sha256_of(root / a["path"])
        if sha is None:
            block.append(f"{shot}: {a['path']} is missing")
            continue
        status, why = asset_status(root, shot, kind, sha)
        if status == ST.PASS:
            ok += 1
        elif status == ST.REVIEW:
            review_.append(f"{shot} ({why})")
        else:
            block.append(f"{shot}: {status} ({why})")
    name = f"observation_{kind}s"
    if block:
        return [G.row(name, False, f"OB-1: {len(block)} {kind}(s) without a passing observation record for their current hash: "
                                   + "; ".join(block[:25]) + ("; ..." if len(block) > 25 else ""), {"blocked": block, "ok": ok})]
    if review_:
        return [G.row(name, False, f"OB-1: {len(review_)} {kind}(s) observed with REVIEW: " + "; ".join(review_[:25]),
                      {"review": review_, "ok": ok}, level=G.REVIEW)]
    return [G.row(name, True, f"OB-1: {ok} {kind}(s) have a passing observation record" if ok else
                  f"OB-1: no {kind} is bound to a shot yet; nothing to observe", {"ok": ok})]


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.qa.observe", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("episode")
    g = sub.add_parser("gate")
    g.add_argument("episode")
    g.add_argument("--stage", required=True, choices=sorted(STAGE_KIND))
    r = sub.add_parser("review")
    r.add_argument("episode")
    r.add_argument("record_id")
    r.add_argument("--by", required=True, choices=("session", "owner"))
    r.add_argument("--note", default="")
    r.add_argument("--message-id", default=None)
    a = ap.parse_args(argv)
    root = Path(a.episode)
    if a.cmd == "status":
        seen = {}
        for rec in load(root):
            seen[(rec["shot_id"], rec["kind"], rec["asset_sha256"])] = 1
        for shot, kind, sha in sorted(seen):
            st, why = asset_status(root, shot, kind, sha)
            print(f"{shot:12} {kind:6} {sha[:12]} {st:10} {why}")
        return 0
    if a.cmd == "gate":
        rows = gate_rows(root, a.stage)
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
        return 1 if any(x["status"] == G.FAIL for x in rows) else 0
    print(json.dumps(review(root, a.record_id, a.by, a.note, a.message_id)["reviewed"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
