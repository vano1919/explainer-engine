"""One runner for an episode-first episode (v4.3 plan P8, RN-01..RN-06 in docs/EPISODE_FIRST.md).

    python -m explainer_engine.episode run episodes/<id> --stage <stage>     # one stage (also G1..G10)
    python -m explainer_engine.episode run episodes/<id> --to <stage>        # every stage up to it, fresh records skipped
    python -m explainer_engine.episode status episodes/<id>                  # the stages, their verdicts, what is stale

The stages of plan section 4, in order: ``script`` (G1-G3), ``sound_plan`` (G4), ``pictures`` (G5), ``voice`` (G6),
``clips`` (G7a maps, G7b 2.5D, G7c Wan), ``sound`` (G8), ``assemble`` (G9), ``qa`` (G10). Each stage writes its record
``production/stages/<stage>.json``: its gate rows (``qa/gates``), its verdict, what it made, and the fingerprint of what it
was made from (the episode, the script, its own inputs and the record of the stage before). A stage refuses to start while
the record before it is missing, stale (made from other inputs) or not PASS/REVIEW. ``--rehearsal`` lets a stage start
after a FAIL or an INCOMPLETE record, to rehearse the whole chain on what exists: every later record says ``rehearsal``,
and the QA stage of a rehearsal never passes.

Nothing here spends money: no stage calls a paid service. Pictures come in through the turn packs (P3), the read through
the voice stage's files, Wan clips through ``aivideo/wan_adapter`` outside the runner; a Wan shot without its QA'd clip is
a FAIL (in a rehearsal it is drawn by the 2.5D fallback and the record says so).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import time
from pathlib import Path

from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.core.store import write_json_atomic, write_text_atomic
from explainer_engine.episode import timing as TM
from explainer_engine.qa import gates as G

STAGES = ("script", "sound_plan", "pictures", "voice", "clips", "sound", "assemble", "qa")
GATES = {"script": "G1-G3", "sound_plan": "G4", "pictures": "G5", "voice": "G6", "clips": "G7", "sound": "G8",
         "assemble": "G9", "qa": "G10"}
ALIASES = {"G1": "script", "G2": "script", "G3": "script", "G4": "sound_plan", "G5": "pictures", "G6": "voice",
           "G7": "clips", "G7a": "clips", "G7b": "clips", "G7c": "clips", "G8": "sound", "G9": "assemble", "G10": "qa"}
RECORD_SCHEMA = "episode_stage/1"
SCRIPT_REL = "story/production_script.json"
READ_REL = "audio/narration.wav"            # the episode's real read (ElevenLabs), the lines in the shots' order
TRANSCRIPT_REL = "audio/narration.scribe.json"   # its Scribe transcript (words with times)
WAN_LEDGER_REL = "logs/wan_ledger.jsonl"
GO_ON = (G.PASS, G.REVIEW)
DEFAULT_SIZE = (1920, 1080)


class StageRefused(RuntimeError):
    """A stage may not start: the record before it is missing, stale or not good enough."""


# --- records ---------------------------------------------------------------------------------------------------------

def _sha(path: Path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def record_path(root: Path, stage: str) -> Path:
    return Path(root) / "production" / "stages" / f"{stage}.json"


def read_record(root: Path, stage: str) -> dict | None:
    p = record_path(root, stage)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def record_digest(rec: dict | None) -> str | None:
    """What a later stage chains on: the verdict, the rows and the outputs (not the clock, so a re-run that makes the same
    thing leaves the stages after it fresh)."""
    if rec is None:
        return None
    return _digest({k: rec.get(k) for k in ("stage", "verdict", "rows", "outputs", "rehearsal", "fingerprint")})


class Episode:
    """The folder, its manifest, its script and the run's settings."""

    def __init__(self, root: Path, *, size: tuple[int, int] | None = None, fps: int | None = None,
                 rehearsal: bool = False, force: bool = False, chunks: tuple[int, int] | None = None,
                 chunk_seconds: float | None = None, sound_library: Path | None = None):
        self.root = Path(root).resolve()
        man = self.root / "episode.json"
        if not man.is_file():
            raise ConfigError(f"{self.root} has no episode.json: not an episode folder")
        self.manifest = json.loads(man.read_text(encoding="utf-8"))
        sp = self.root / SCRIPT_REL
        if not sp.is_file():
            raise ConfigError(f"{self.root} has no {SCRIPT_REL}")
        self.script = json.loads(sp.read_text(encoding="utf-8"))
        self.fps = int(fps or self.script.get("fps") or self.manifest.get("fps") or 24)
        self.size = tuple(size or self.manifest.get("render_size") or DEFAULT_SIZE)
        self.rehearsal, self.force, self.chunks = rehearsal, force, chunks
        self.chunk_seconds = chunk_seconds
        if sound_library is None:
            from explainer_engine.assets_reuse import SOUND_LIB
            sound_library = SOUND_LIB
        self.sound_library = Path(sound_library)

    def path(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if not p.is_relative_to(self.root):
            raise ContractError(f"{rel} is outside the episode folder (R-F)")
        return p

    def timing(self) -> dict | None:
        return TM.load(self.root)

    def timed_script(self) -> dict:
        return TM.timed_script(self.script, self.timing())


def _stage_inputs(ep: Episode, stage: str) -> dict:
    """The files a stage reads besides the script and the record before it."""
    files = {"episode.json": _sha(ep.root / "episode.json"), SCRIPT_REL: _sha(ep.root / SCRIPT_REL)}
    if stage == "pictures":
        files["planning/picture_ledger.jsonl"] = _sha(_picture_ledger(ep.root))
    if stage == "voice":
        files[READ_REL] = _sha(ep.root / READ_REL)
        files[TRANSCRIPT_REL] = _sha(ep.root / TRANSCRIPT_REL)
    if stage in ("sound_plan", "sound"):
        files["sound_library/manifest.json"] = _sha(ep.sound_library / "manifest.json")
    if stage == "clips":
        files[WAN_LEDGER_REL] = _sha(ep.root / WAN_LEDGER_REL)
    if stage == "voice":   # VL-07: the clip records of the clip-spoken shots time them (G7 re-cuts only the others)
        from explainer_engine.videolane import plan as VP
        for sid in sorted(VP.clip_spoken(ep.script)):
            rel = f"production/video/{sid}.json"
            files[rel] = _sha(ep.root / rel)
    return files


def fingerprint(ep: Episode, stage: str) -> str:
    i = STAGES.index(stage)
    before = record_digest(read_record(ep.root, STAGES[i - 1])) if i else None
    return _digest({"stage": stage, "inputs": _stage_inputs(ep, stage), "before": before, "size": list(ep.size),
                    "fps": ep.fps})


def state(ep: Episode) -> list[dict]:
    """Every stage: its record's verdict, fresh or stale, rehearsal or not."""
    out = []
    for s in STAGES:
        rec = read_record(ep.root, s)
        out.append({"stage": s, "gate": GATES[s], "status": rec["verdict"]["status"] if rec else None,
                    "fresh": bool(rec) and rec.get("fingerprint") == fingerprint(ep, s),
                    "rehearsal": bool(rec and rec.get("rehearsal")), "at": rec.get("at") if rec else None})
    return out


def check_before(ep: Episode, stage: str) -> bool:
    """Raise StageRefused when ``stage`` may not start; return whether the run is a rehearsal from here on (a record
    before it is one, or did not pass; ``--rehearsal`` only lets the stage start, it does not make a passing chain one)."""
    i = STAGES.index(stage)
    if i == 0:
        return False
    prev = STAGES[i - 1]
    rec = read_record(ep.root, prev)
    if rec is None:
        raise StageRefused(f"{stage} ({GATES[stage]}) needs the record of {prev} ({GATES[prev]}); run that stage first")
    if rec.get("fingerprint") != fingerprint(ep, prev):
        raise StageRefused(f"the record of {prev} is stale (its inputs changed since it ran); run {prev} again first")
    status = rec["verdict"]["status"]
    if status not in GO_ON and not ep.rehearsal:
        raise StageRefused(f"{prev} ended {status} ({', '.join(rec['verdict'].get('failed') or rec['verdict'].get('not_run') or [])}); "
                           f"fix it, or pass --rehearsal to rehearse the chain (a rehearsal never ships)")
    return bool(rec.get("rehearsal")) or status not in GO_ON


def run_stage(ep: Episode, stage: str) -> dict:
    stage = ALIASES.get(stage, stage)
    if stage not in STAGES:
        raise ConfigError(f"unknown stage {stage!r}: one of {', '.join(STAGES)} or G1..G10")
    rehearsal = check_before(ep, stage)
    t0 = time.time()
    fp = fingerprint(ep, stage)
    try:
        rows, outputs = STAGE_FUNCS[stage](ep, rehearsal)
    except ContractError as exc:   # a contract the stage cannot get past is its FAIL row, recorded, never a silent stop
        rows, outputs = [G.row(f"{stage}_ran", False, f"{type(exc).__name__}: {exc}")], {}
    except ConfigError as exc:     # a missing free tool or setting: nothing measured, recorded as NOT_RUN (final audit B3)
        rows, outputs = [G.row(f"{stage}_ran", None, f"{type(exc).__name__}: {exc}")], {}
    if stage == "qa":   # a rehearsal is never a pass: an earlier stage did not pass, so nothing from this run ships
        rows = rows + [G.row("not_a_rehearsal", not rehearsal, "the chain passed every stage" if not rehearsal else
                             "a rehearsal: an earlier stage did not pass, so nothing from this run ships")]
    verdict = G.verdict(rows)
    verdict.pop("gates", None)
    rec = {"schema": RECORD_SCHEMA, "episode_id": ep.manifest.get("episode_id"), "stage": stage, "gate": GATES[stage],
           "verdict": verdict, "rows": rows, "outputs": outputs, "rehearsal": rehearsal, "fingerprint": fp,
           "elapsed_s": round(time.time() - t0, 2), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json_atomic(record_path(ep.root, stage), rec)
    return rec


def run_to(ep: Episode, last: str) -> list[dict]:
    """Every stage up to ``last``; a stage with a fresh record is kept (``--force`` runs it again). Stops at the first stage
    that is refused or whose verdict does not let the next one start."""
    last = ALIASES.get(last, last)
    done = []
    for s in STAGES[: STAGES.index(last) + 1]:
        rec = read_record(ep.root, s)
        if rec and not ep.force and rec.get("fingerprint") == fingerprint(ep, s):
            done.append(dict(rec, reused=True))
        else:
            done.append(run_stage(ep, s))
        if done[-1]["verdict"]["status"] not in GO_ON and not ep.rehearsal:
            break
    return done


# --- the stages ------------------------------------------------------------------------------------------------------

def stage_script(ep: Episode, rehearsal: bool):
    """G1-G3: one episode id, the v4 schema, the gate audit (story, scene, shot and cohesion lints), a route with its
    reason on every shot, the speakers on Wan, and the router's agreement with every unlocked route."""
    import jsonschema
    from explainer_engine.episode import router as R
    from explainer_engine.episode.validate import check_episode_ids
    from explainer_engine.orchestration.rule_enforcer import run_all_gate_audits
    doc = ep.script
    rows = []
    ids = check_episode_ids(ep.root)
    rows.append(G.row("isolation_one_episode_id", not ids, f"{len(ids)} EP-01 finding(s)", [r["where"] for r in ids][:20]))
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    rows.append(G.row("script_schema", not errs, f"{len(errs)} schema error(s)",
                      [f"{list(e.path)}: {e.message[:160]}" for e in errs[:10]]))
    audit = run_all_gate_audits(doc)
    fails = [i for i in audit["issues"] if i.get("severity", "FAIL") == "FAIL"]
    reviews = [i for i in audit["issues"] if i.get("severity") == "REVIEW"]
    short = lambda xs: [f"{i.get('rule')} {i.get('where')}: {str(i.get('detail'))[:140]}" for i in xs[:20]]  # noqa: E731
    rows.append(G.row("script_lints_fail", not fails, f"{len(fails)} FAIL finding(s) of the gate audit", short(fails)))
    rows.append(G.row("script_lints_review", not reviews, f"{len(reviews)} REVIEW finding(s) of the gate audit",
                      short(reviews), level=G.REVIEW))
    shots = doc.get("shots", [])
    bad = [s.get("shot_id") for s in shots if s.get("route") not in R.ROUTES or not str(s.get("route_reason") or "").strip()]
    rows.append(G.row("every_shot_routed", bool(shots) and not bad, f"{len(bad)} of {len(shots)} shot(s) without a route "
                      "and its reason (RT-01)", bad[:20]))
    from explainer_engine.episode import retired
    old = retired.retired_routes_in(doc)
    rows.append(G.row("no_retired_route", not old, f"{len(old)} shot field(s) name a retired route (Q10, D-131: "
                      "config/retired_era.json)", old[:20]))
    rows += R.talking_check(doc)
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as LJ
    from explainer_engine.videolane import plan as VP
    if LJ.native_problems(LJ.LAUNCH):
        rows.append(G.row("video_shots_fit_the_model", None, "NOT_RUN: the LTX model's native limits are not pinned in "
                          f"{LJ.LAUNCH_PATH.name}: {'; '.join(LJ.native_problems(LJ.LAUNCH))}"))
    else:   # FA-01: the video route is LTX (D-132); the Wan fit row stays only for the legacy adapter and its tests
        rows += VP.fit_rows(doc, LJ.max_seconds(LJ.LAUNCH), LJ.LAUNCH.get("model_repo"), LJ.LAUNCH["native"]["fps"])
    rows += VP.rows(doc, LJ.max_seconds(LJ.LAUNCH))   # VL-01..VL-09: every LTX shot's edit plan (D-137)
    speakers = R.speaking_heroes(doc)
    differ = []
    for s in shots:
        if s.get("route_locked") or s.get("route") not in R.ROUTES:
            continue
        route, _why = R.route_shot(s, speakers.get(s["shot_id"]))
        if route != s["route"]:
            differ.append(f"{s['shot_id']}: {s['route']} -> {route}")
    rows.append(G.row("router_agrees", not differ, f"{len(differ)} unlocked shot(s) whose route the router would change "
                      "(run route_script or lock the route with its reason)", differ[:20], level=G.REVIEW))
    from explainer_engine.episode import events as E
    from explainer_engine.episode import sound_plan as SP
    rows += E.contract_rows(doc, set(SP.EVENT_CLASSES), ep.fps)
    rows += E.absolute_anchor_rows(doc)   # FA-06: on a locked script an absolute anchor under a read line is REVIEW
    rows.append(_claims_row(ep, doc))
    rows.append(_video_share_row(doc, _scope(ep)))
    return rows, {"mix": R.mix_report(doc), "shots": len(shots), "audit_status": audit["status"]}


def _scope(ep: Episode) -> str:
    """The run's scope from the manifest (``run_scope``): ``sample`` or ``full``; a manifest that says nothing is a full
    episode (the strict side)."""
    v = str(ep.manifest.get("run_scope") or "full")
    if v not in ("sample", "full"):
        raise ConfigError(f"episode.json run_scope {v!r} is not sample or full")
    return v


def _video_share_row(doc: dict, scope: str = "full") -> dict:
    """Q7 (Fable audit; the creator 2026-11-13, answer c, D-138): the video share by duration against D-131's target (+-10
    points). ``sample_review_full_fail`` (his answer): REVIEW on a sample (Toba keeps its 35.6 %, no re-routing), FAIL on a
    full episode; ``frame`` REVIEW always; ``reroute`` FAIL always."""
    from explainer_engine.core import open_questions as OQ
    from explainer_engine.episode import router as R
    mix = R.mix_report(doc)
    share = float(mix["shares"].get("video", 0.0))
    target = float((doc.get("visual_mix_target") or {}).get("cinematic_video_target") or 0.6)
    ok = abs(share - target) <= 0.10
    q7 = OQ.value("Q7")
    fail = q7 == "reroute" or (q7 == "sample_review_full_fail" and scope != "sample")
    return G.row("video_share_against_target", ok, f"video {share:.1%} of the duration ({mix['basis']}), D-131's target "
                 f"{target:.0%} (+-10 points); switch Q7 = {q7}, run_scope {scope}", round(share, 4),
                 level=G.FAIL if fail else G.REVIEW)


def _claims_row(ep: Episode, doc: dict) -> dict:
    """Every number a map shows (counter, bar_grow, progress_bar, milestone) carries a claim id of the episode's claim map
    (``story/claim_map.md``, scripting/claims): values come from claims, never invented (W3)."""
    from explainer_engine.maps import actions as MA
    from explainer_engine.scripting import claims as CL
    shown = [(s["shot_id"], a) for s in doc.get("shots", []) for a in s.get("actions") or [] if a.get("kind") in MA.NUMBER_KINDS]
    if not shown:
        return G.row("map_numbers_have_claims", True, "no map shot shows a number", 0)
    cmap = CL.load_map(ep.root / SCRIPT_REL)
    no_claim = [f"{sid}:{a.get('kind')}" for sid, a in shown if not a.get("claim")]
    unknown = [f"{sid}:{a.get('claim')}" for sid, a in shown if a.get("claim") and cmap is not None and a["claim"] not in cmap]
    if cmap is None:   # nothing to resolve the ids against: a person checks them (REVIEW), a missing id still FAILs
        if no_claim:
            return G.row("map_numbers_have_claims", False, f"shown numbers without a claim id {no_claim[:10]}", no_claim[:10])
        return G.row("map_numbers_have_claims", False, f"{len(shown)} shown number(s) carry claim ids, but the episode has no "
                     "claim map (story/claim_map.md) to resolve them", len(shown), level=G.REVIEW)
    return G.row("map_numbers_have_claims", not no_claim and not unknown, f"{len(shown)} shown number(s): without a claim "
                 f"{no_claim[:10]}, claim not in the map {unknown[:10]}", no_claim[:10] + unknown[:10])


def _era(ep: Episode) -> str | None:
    """The manifest's era id (FA-09): the sound plan's era comes from here, never from a guess."""
    return str((ep.manifest.get("historical_period") or {}).get("era_id") or "") or None


def stage_sound_plan(ep: Episode, rehearsal: bool):
    """G4: the sound plan on the planned clock (the sound stage rebuilds it on the measured one), era-checked, its sources
    resolved, the needs listed."""
    from explainer_engine.episode import sound_plan as SP
    plan = SP.build(ep.script, fps=ep.fps, era=_era(ep))
    sources = SP.resolve(plan, ep.sound_library)
    path = SP.write(plan, sources, ep.root)
    needs = SP.needs(sources)
    blocked = plan["blocked_era_events"]
    guessed_beds = sorted({b["place"] for b in plan["beds"] if b.get("basis") != "authored"})
    rows = [G.row("era_from_the_manifest", plan["era_basis"] in SP.ERA_BASES, f"the era is {plan['era']!r} "
                  f"({plan['era_basis']}): it comes from episode.json historical_period.era_id, never a guess (FA-09)"),
            G.row("beds_authored_per_place", not guessed_beds, f"{len(guessed_beds)} place(s) without an authored "
                  "ambience_bed: their bed is a candidate read from the prose (FA-09, the story-architect writes it)",
                  guessed_beds[:20], level=G.REVIEW),
            G.row("no_era_foreign_sound_asked", not blocked, f"{len(blocked)} sound event(s) the era never heard, asked "
                  "by the script", blocked[:20]),
            G.row("every_sound_class_has_a_take", not needs, f"{len(needs)} class(es) still need a real take (the needs "
                  "list; new takes are paid credits, the creator's word first)", [n["class"] for n in needs][:30],
                  level=G.REVIEW)]
    from explainer_engine.episode import events as E
    write_json_atomic(ep.path("production/av_events.json"), E.events_report(ep.script, None, ep.fps))
    rv = plan["av"]["review_required"]
    rows.append(G.row("av_events_decided", not rv, f"{sum(plan['av']['decisions'].values())} visible event(s) "
                      f"{plan['av']['decisions']}; review_required {rv[:10]}; {plan['av']['candidates']} word candidate(s) "
                      "listed, none placed (AV-07)", rv[:30], level=G.REVIEW))
    return rows, {"plan": str(path.relative_to(ep.root)), "classes": len(plan["classes"]), "needs": len(needs),
                  "av_events": "production/av_events.json"}


def _picture_ledger(root: Path) -> Path:
    from explainer_engine.imagegen import turn_pack as TP
    return TP.ledger_path(Path(root))


def needed_pictures(script: dict) -> list[tuple[str, str]]:
    """``(shot_id, which)`` of every picture the clips need: a start frame for each shot that is not a map, and an end
    frame where the shot's keyframe plan asks for one (the turn packs' own rule, GC-09)."""
    out = []
    for s in script.get("shots", []):
        if s.get("route") == "map_action" or s.get("visual_type") == "map_visualization":
            continue
        kp = s.get("keyframe_plan") or {}
        if kp.get("needs_start_frame", True):
            out.append((s["shot_id"], "start"))
        if kp.get("needs_end_frame"):
            out.append((s["shot_id"], "end"))
    return out


def stage_pictures(ep: Episode, rehearsal: bool):
    """G5: every picture a clip needs, taken in through the turn packs' intake (P3: decodes, 16:9, the native floor, no
    letterbox, identity), upscaled to its working master (EP-02). A draft or a file the intake never saw does not enter G7
    (in a rehearsal it is used and the rows say so)."""
    from explainer_engine.imagegen import turn_pack as TP
    ledger = TP.ledger_rows(ep.root)
    best: dict[str, dict] = {}
    for r in ledger:
        if r.get("status") != "accepted":
            continue
        if r.get("grade") == "master" or r["id"] not in best:
            best[r["id"]] = r
    pictures, missing, drafts, unrecorded, changed = {}, [], [], [], []
    for sid, which in needed_pictures(ep.script):
        pid = f"{sid}_{which}"
        shot = next(s for s in ep.script["shots"] if s["shot_id"] == sid)
        r = best.get(pid)
        if r is not None:
            p = ep.root / r["file"]
            grade = r.get("grade", "draft")
            if not p.is_file():
                missing.append(pid)
                continue
            if _sha(p) != r.get("sha256"):
                changed.append(pid)
        else:   # a file on disk that the intake never saw: the hand-set path, then the turn pack's names, then the archive's
            cands = [shot.get(f"{which}_keyframe_rel")] if shot.get(f"{which}_keyframe_rel") else []
            cands += [TP.master_path(TP.frame_path(sid, which)), TP.frame_path(sid, which),
                      f"assets/generated/images/{sid}_{which}.jpg"]
            p = next((ep.root / c for c in cands if (ep.root / c).is_file()), None)
            if p is None:
                missing.append(pid)
                continue
            grade = "unrecorded"
            unrecorded.append(pid)
        if grade == "draft":
            drafts.append(pid)
        pictures[pid] = {"file": str(p.relative_to(ep.root)), "grade": grade, "sha256": _sha(p)}
    need = len(needed_pictures(ep.script))
    rows = [G.row("every_picture_present", need > 0 and not missing, f"{need - len(missing)} of {need} picture(s) on disk",
                  missing[:30]) if need else G.row("every_picture_present", None, "the script needs no picture (maps only)"),
            G.row("every_picture_taken_in", not unrecorded and not changed,
                  f"{len(unrecorded)} picture(s) the intake never saw, {len(changed)} changed since the intake",
                  (unrecorded + changed)[:30]),
            G.row("every_picture_a_master", not drafts, f"{len(drafts)} draft(s) not yet upscaled to the working master "
                  "(turn_pack promote)", drafts[:30])]
    out = ep.path("production/pictures.json")
    write_json_atomic(out, {"episode_id": ep.manifest.get("episode_id"), "pictures": pictures})
    return rows, {"pictures": str(out.relative_to(ep.root)), "count": len(pictures), "missing": len(missing)}


def stage_voice(ep: Episode, rehearsal: bool):
    """G6: the episode's real read and its transcript -> the measured shot lengths and word spines (``episode/timing``).
    No read: FAIL (the read is ElevenLabs credits, made outside the runner on the creator's word)."""
    read, tr = ep.root / READ_REL, ep.root / TRANSCRIPT_REL
    timing_path = ep.root / "audio" / "timing.json"
    from explainer_engine.videolane import plan as VP
    if VP.clip_spoken(ep.script):
        return _voice_with_clips(ep, read, tr, timing_path)
    if not read.is_file() or not tr.is_file():
        if timing_path.is_file():
            timing_path.unlink()   # a timing from an older read must not time this run
        what = [x for x, p in ((READ_REL, read), (TRANSCRIPT_REL, tr)) if not p.is_file()]
        return [G.row("the_read_exists", False, f"missing {', '.join(what)}: the episode has no read yet; later stages "
                      "use the planned lengths (a rehearsal only)", what)], {"timing": None}
    import wave
    from explainer_engine.audio.environmental_sound_design import validate_narration_source_file
    validate_narration_source_file(read)
    with wave.open(str(read)) as w:
        read_s = w.getnframes() / float(w.getframerate())
    aligned = TM.align_read(ep.script, json.loads(tr.read_text(encoding="utf-8")), read_s)
    timing = TM.retime(ep.script, aligned, ep.fps, read_s)
    write_json_atomic(timing_path, timing)
    planned = sum(float(s.get("target_duration_seconds") or 0) for s in ep.script["shots"])
    from explainer_engine.audio import scribe_words as SW
    rows = [G.row("the_read_exists", True, f"{READ_REL}: {read_s:.2f} s", read_s),
            G.row("read_aligned_to_the_lines", aligned["status"] == G.PASS,
                  f"{aligned['coverage']:.1%} of the written words heard (needs {SW.MIN_COVERAGE:.0%})",
                  aligned["unmatched"][:20], level=G.REVIEW)]
    rows += _anchor_rows(ep, timing)
    return rows, {"timing": "audio/timing.json", "read_s": round(read_s, 3), "planned_s": round(planned, 3),
                  "total_frames": timing["total_frames"]}


def _anchor_rows(ep: Episode, timing: dict) -> list[dict]:
    """FA-06: every anchor resolved on the retimed shots right after G6's retime (``events.anchor_rows``)."""
    from explainer_engine.episode import events as E
    return E.anchor_rows(TM.timed_script(ep.script, timing), TM.spines_of(timing), ep.fps)


def _events_for_picture(plan_shot: dict) -> list[dict]:
    """The picture answers only an AUTHORED sound event (AV-07): a word of the read never shakes or flashes a picture."""
    return [{"frame": int(e["at_frame"]), "kind": e["picture_event"]} for e in plan_shot.get("events", [])
            if e.get("picture_event") and e.get("basis") == "authored"]


def _clip_key(shot: dict, files: list, ep: Episode, spine, events: list | None = None, renderer: str = "") -> str:
    """The cache key of one clip (AV-08): the shot's data, its pictures (paths and SHA-256), size and fps, the spine's hash,
    the hash of its resolved events, its motion profile and settings, and the renderer and contract versions. Any of them
    changing renders the clip again."""
    from explainer_engine.episode import events as E
    return _digest({"shot": shot, "files": files, "size": list(ep.size), "fps": ep.fps, "spine_sha": E.spine_hash(spine),
                    "events_sha": E.events_hash(events or []), "motion_profile": shot.get("motion_profile"),
                    "renderer": renderer, "resolver": E.RESOLVER_VERSION, "contract": ep.script.get("av_contract") or "legacy"})


def _voice_with_clips(ep: Episode, read: Path, tr: Path, timing_path: Path):
    """G6 when LTX clips speak some lines (VL-07): the read times the narrator's shots, each clip-spoken shot is timed by its
    trimmed clip (``production/video/<shot>.json``) and inserted at its place. A clip-spoken shot without its clip keeps its
    planned length and FAILs ``clip_spoken_shots_timed_by_their_clips`` (a rehearsal goes on)."""
    import wave
    from explainer_engine.videolane import ingest as VI
    from explainer_engine.videolane import plan as VP
    spoken = VP.clip_spoken(ep.script)
    clips = VI.clip_timings(ep.root, ep.script)
    missing = sorted(spoken - set(clips))
    for sid in missing:
        sh = next(s for s in ep.script["shots"] if s["shot_id"] == sid)
        clips[sid] = {"frames": max(1, int(round(float(sh.get("target_duration_seconds") or 1.0) * ep.fps))), "speech": []}
    rows, aligned, read_s = [], None, 0.0
    needs_read = bool(TM.read_order(ep.script))
    if needs_read and (not read.is_file() or not tr.is_file()):
        what = [x for x, p in ((READ_REL, read), (TRANSCRIPT_REL, tr)) if not p.is_file()]
        rows.append(G.row("the_read_exists", False, f"missing {', '.join(what)}: the narrator's shots keep their planned "
                          "lengths (a rehearsal only)", what))
    elif needs_read:
        from explainer_engine.audio import scribe_words as SW
        from explainer_engine.audio.environmental_sound_design import validate_narration_source_file
        validate_narration_source_file(read)
        with wave.open(str(read)) as w:
            read_s = w.getnframes() / float(w.getframerate())
        aligned = TM.align_read(ep.script, json.loads(tr.read_text(encoding="utf-8")), read_s)
        rows += [G.row("the_read_exists", True, f"{READ_REL}: {read_s:.2f} s", read_s),
                 G.row("read_aligned_to_the_lines", aligned["status"] == G.PASS,
                       f"{aligned['coverage']:.1%} of the written words heard (needs {SW.MIN_COVERAGE:.0%})",
                       aligned["unmatched"][:20], level=G.REVIEW)]
    else:
        rows.append(G.row("the_read_exists", True, "no narrator line: the clips speak every line (VL-07)"))
    timing = TM.retime_with_clips(ep.script, aligned, ep.fps, read_s, clips)
    write_json_atomic(timing_path, timing)
    rows.append(G.row("clip_spoken_shots_timed_by_their_clips", not missing, f"{len(spoken) - len(missing)} of "
                      f"{len(spoken)} clip-spoken shot(s) timed by their trimmed LTX clip", missing[:20]))
    rows += _anchor_rows(ep, timing)
    planned = sum(float(s.get("target_duration_seconds") or 0) for s in ep.script["shots"])
    return rows, {"timing": "audio/timing.json", "read_s": round(read_s, 3), "planned_s": round(planned, 3),
                  "total_frames": timing["total_frames"], "clip_timed": timing["clip_timed"],
                  "inserts": len(timing["inserts"])}


def _wan_clip(ep: Episode, sid: str) -> dict | None:
    """The QA'd Wan clip of a shot, if ``aivideo/wan_adapter.run_shot`` made one: its report beside the clip."""
    rep = ep.root / "production" / "video" / f"{sid}.json"
    if not rep.is_file():
        return None
    doc = json.loads(rep.read_text(encoding="utf-8"))
    if doc.get("route") != "video" or doc.get("status") == G.FAIL or not doc.get("clip_path"):
        return None
    p = ep.path(doc["clip_path"]) if not Path(doc["clip_path"]).is_absolute() else Path(doc["clip_path"])
    return dict(doc, clip_path=str(p)) if p.is_file() else None


def stage_clips(ep: Episode, rehearsal: bool):
    """G7: every shot's clip by its route. ``map_action``: the action map (P4) with its gates (a map shot without actions
    FAILs, final audit B1);
    ``still_25d``: the layered 2.5D renderer (P5) with the sound plan's picture events and the measured spine; ``wan``: the
    QA'd clip of the Wan adapter (P6), never generated here; without one the shot FAILs, and a rehearsal draws it with the
    adapter's 2.5D fallback. A clip whose shot, pictures, spine and size are unchanged is reused."""
    from explainer_engine.episode import sound_plan as SP
    from explainer_engine.production import layers25d as L25
    from explainer_engine.production.map_clip import render_action_map_clip
    script = ep.timed_script()
    timing = ep.timing()
    spines = TM.spines_of(timing)
    pics = json.loads(ep.path("production/pictures.json").read_text(encoding="utf-8"))["pictures"] \
        if ep.path("production/pictures.json").is_file() else {}
    plan = SP.build(script, fps=ep.fps, spines=spines, era=_era(ep))
    plan_by = {s["shot_id"]: s for s in plan["shots"]}
    from explainer_engine.episode import events as E
    from explainer_engine.maps import actions as MA
    ev_doc = E.events_report(script, spines, ep.fps)    # the one resolver on the measured clock (AV-01)
    write_json_atomic(ep.path("production/av_events.json"), ev_doc)
    av_events = ev_doc["shots"]
    w, h = ep.size
    clips_dir = ep.path("production/shot_clips")
    clips_dir.mkdir(parents=True, exist_ok=True)
    records, made, reused, failed, missing_wan, fallback, missing_pic, no_tool = [], 0, 0, [], [], [], [], []
    t = 0
    for sh in script["shots"]:
        sid = sh["shot_id"]
        frames = max(1, int(round(float(sh["target_duration_seconds"]) * ep.fps)))
        route = sh.get("route")
        rec = {"shot_id": sid, "segment_id": sh.get("segment_id"), "route": route, "start_sec": round(t / ep.fps, 4),
               "end_sec": round((t + frames) / ep.fps, 4), "duration_sec": round(frames / ep.fps, 4),
               "total_frames": frames}
        t += frames
        out = clips_dir / f"{sid}.mp4"
        report = clips_dir / f"{sid}.clip.json"
        is_map = route == "map_action" or sh.get("visual_type") == "map_visualization"
        start = pics.get(f"{sid}_start")
        end = pics.get(f"{sid}_end")
        evs = av_events.get(sid, {}).get("events", [])
        renderer = MA.RENDERER_VERSION if is_map else L25.RENDERER_VERSION
        files = [start, end] + ([_sha(ep.root / "production" / "video" / f"{sid}.json")] if route == "video" else [])
        key = _clip_key(sh, files, ep, spines.get(sid), evs, renderer)   # a video shot's key holds its clip record
        old = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else None
        if old and old.get("key") == key and out.is_file() and _sha(out) == old.get("output_sha256") and not ep.force:
            records.append(dict(old["record"], start_sec=rec["start_sec"], end_sec=rec["end_sec"]))
            reused += 1
            if old["record"].get("status") == G.FAIL:
                failed.append(sid)
            continue
        try:
            if is_map:
                if not sh.get("actions"):   # final audit B1: the archive's hard-coded Toba maps are no fallback
                    raise ContractError(f"{sid}: a map_action shot without actions (RT-03): write its actions on their "
                                        "words; the archive's fixed relief map is not used in a v4.3 episode")
                res = render_action_map_clip(sh, script, ep.manifest, out, width=w, height=h, fps=ep.fps,
                                             spine=spines.get(sid), keyframes_out_dir=ep.path("assets/maps/renders"))
                rec.update(visual_type="map_visualization", provider=res["provider"], status=res["gates"]["status"],
                           gates_map=res["gates"]["status"], source_start_keyframe=res.get("start_keyframe_path"),
                           source_end_keyframe=res.get("end_keyframe_path"))
            else:
                wan = _wan_clip(ep, sid) if route == "video" else None
                if route == "video" and wan is None:   # counted before the picture check (final audit B2)
                    missing_wan.append(sid)
                if start is None:
                    missing_pic.append(sid)
                    raise ContractError(f"{sid}: no start picture (G5)")
                if wan is not None and wan.get("schema") == "video_clip_record/1" and int(wan.get("frames") or 0) != frames:
                    from explainer_engine.videolane import ingest as VI
                    rel = dict(wan, clip_path=str(Path(wan["clip_path"]).relative_to(ep.root)))
                    new = VI.recut(ep.root, rel, frames, ep.fps)     # VL-11: from the kept raw clip, never stretched
                    wan = dict(new, clip_path=str(ep.root / new["clip_path"]))
                forced_fallback = None
                if wan is not None and wan.get("status") == G.FAIL:   # RT-07 in one place (videolane/failure, FA-16)
                    from explainer_engine.videolane import failure as VF
                    d = VF.decide(wan.get("attempts") or [{"status": G.FAIL}])
                    rec["rt07"] = d
                    if d["action"] != "fallback_25d":
                        raise ContractError(f"{sid}: its clip FAILs the QA and {d['why']} (RT-07)")
                    forced_fallback, wan = d["why"], None
                if wan is not None:
                    out.write_bytes(Path(wan["clip_path"]).read_bytes())
                    res = {"provider": wan.get("backend"), "status": wan["status"], "total_frames": frames}
                    rec.update(visual_type=sh.get("visual_type"), provider=f"wan:{wan.get('backend')}", status=wan["status"],
                               wan_attempts=len(wan.get("attempts") or []))
                else:
                    shot = sh
                    if route == "video":
                        if not rehearsal and not forced_fallback:
                            raise ContractError(f"{sid}: no QA'd video clip (production/video/{sid}.json); clips are made "
                                                "by the scene run on the creator's approved plan, never by the runner")
                        from explainer_engine.videolane import failure as VF
                        shot = VF.fallback_shot(sh)
                        fallback.append(sid)
                        if forced_fallback:
                            rec["fallback_reason"] = forced_fallback
                    res = L25.render_clip(shot, ep.root / start["file"], out, width=w, height=h, fps=ep.fps,
                                          end_picture=(ep.root / end["file"]) if end else None, script=script,
                                          events=_events_for_picture(plan_by.get(sid, {})), spine=spines.get(sid))
                    rec.update(visual_type=sh.get("visual_type", "cinematic_scene"), provider=res["provider"],
                               status=res["gates"]["status"], gates_25d=res["gates"]["status"], camera=res["camera"],
                               effects=res["effects"], families=res["families"],
                               fallback_for_wan=route == "video")
                rec.update(source_start_keyframe=str(ep.root / start["file"]),
                           source_end_keyframe=str(ep.root / end["file"]) if end else None)
            if int(res.get("total_frames") or frames) != frames:
                raise ContractError(f"{sid}: the clip has {res.get('total_frames')} frames, the shot {frames}")
        except ContractError as exc:
            rec.update(status=G.FAIL, error=str(exc), clip_path=None)
            failed.append(sid)
            records.append(rec)
            continue
        except ConfigError as exc:   # a free tool is missing: nothing was measured for this shot (final audit B3)
            rec.update(status=G.NOT_RUN, error=str(exc), clip_path=None)
            no_tool.append(f"{sid}: {exc}")
            records.append(rec)
            continue
        rec.update(clip_path=str(out), output_sha256=_sha(out))
        if rec["status"] == G.FAIL:
            failed.append(sid)
        write_json_atomic(report, {"key": key, "output_sha256": rec["output_sha256"], "record": rec,
                                   "renderer": {k: v for k, v in res.items() if k not in ("path",)}})
        records.append(rec)
        made += 1
    write_json_atomic(ep.path("production/shot_records.json"), {"episode_id": ep.manifest.get("episode_id"),
                                                                 "fps": ep.fps, "size": list(ep.size), "shots": records})
    n = len(records)
    rows = [G.row("every_shot_has_a_clip", not [r for r in records if not r.get("clip_path")],
                  f"{sum(1 for r in records if r.get('clip_path'))} of {n} shot(s) have a clip", missing_pic[:20]),
            G.row("no_clip_fails_its_gates", not failed, f"{len(failed)} shot(s) FAIL their clip gates", failed[:30]),
            G.row("every_wan_shot_is_a_wan_clip", not missing_wan, f"{len(missing_wan)} Wan shot(s) without a QA'd Wan "
                  "clip" + (f" ({len(fallback)} drawn by the 2.5D fallback in this rehearsal)" if fallback else ""),
                  missing_wan[:30]),
            G.row("free_tools_present", None if no_tool else True,
                  f"{len(no_tool)} shot(s) not drawn: a free tool is missing (the message names its fetch command)"
                  if no_tool else "every free tool the clips need was found", no_tool[:10])]
    from explainer_engine.core import open_questions as OQ
    if OQ.value("Q4") == "forced":   # Q4 (D-138): the read before the LTX scenes, every video shot measured
        from explainer_engine.videolane import line_reads as LR
        from explainer_engine.videolane import plan as VP
        have = LR.seconds_by_line(ep.root)
        lines_by = {ln["line_id"]: ln for ln in script.get("audio_lines", [])}
        unread = [s["shot_id"] for s in script.get("shots", []) if VP.is_video(s) and s["shot_id"] in VP.clip_spoken(script)
                  and any((lines_by.get(l) or {}).get("speaker_type") == "character" and l not in have
                          for l in s.get("audio_line_ids") or [])]
        rows.append(G.row("read_before_video", timing is not None and not unread,
                          "switch Q4 = forced: the narration's read (audio/timing.json) and every clip line's read "
                          f"(audio/line_reads.json) come before any video clip; read {'yes' if timing else 'no'}, "
                          f"{len(unread)} clip-spoken shot(s) without a line read", unread[:20]))
    from explainer_engine.episode import router as R
    durations = {r["shot_id"]: r["duration_sec"] for r in records}
    return rows, {"records": "production/shot_records.json", "made": made, "reused": reused,
                  "mix": R.mix_report(script, durations if timing else None)}


def _records(ep: Episode) -> list[dict]:
    p = ep.path("production/shot_records.json")
    if not p.is_file():
        raise ContractError("no production/shot_records.json: run the clips stage (G7) first")
    return json.loads(p.read_text(encoding="utf-8"))["shots"]


SILENT_LUFS = -60.0
POLISHED_REL = "audio/narration_polished.wav"   # HF-3: the read through the narrator chain (RC-004); the read itself is never written
DELIVERED_MIX_REL = "audio/stems/mix_delivered.wav"   # HF-2: the mix at the delivered loudness (BP-50); G9 muxes this file


def _polish_read(ep: Episode) -> tuple[Path | None, dict | None]:
    """HF-3 (FL-402, RC-004, TD-303): the read through ``audio/narrator_polish.CHAIN`` into its own file. The read stays as
    it is (its sha is pinned and is an input of G6); a chain that moves the length by more than 1/30 s is refused, because
    the word timings were measured on the raw read. Returns ``(None, None)`` when there is no read."""
    from explainer_engine.audio import narrator_polish as NP
    read = ep.root / READ_REL
    if not read.is_file():
        return None, None
    dst = ep.path(POLISHED_REL)
    before = NP._seconds(read)
    NP.polish(read, dst)
    after = NP._seconds(dst)
    if abs(after - before) > 1 / 30:
        dst.unlink(missing_ok=True)
        raise ContractError(f"narrator polish moved the length by {after - before:+.3f} s: the word timings would be wrong")
    return dst, {"chain": NP.CHAIN, "seconds_before": round(before, 3), "seconds_after": round(after, 3),
                 "read_sha256": _sha(read), "polished_sha256": _sha(dst)}


def _loudness_rows(prefix: str, meas: dict, what: str) -> list[dict]:
    """The BP-50 verdicts of a measurement as two gate rows (a REVIEW verdict stays a REVIEW row)."""
    from explainer_engine.qa import targets as TG
    v = TG.verdicts(meas, "long")
    band, tp = TG.PROFILES["long"]["pass_band"], TG.PROFILES["long"]["true_peak_max"]
    rows = []
    for gate, key, ok_text in ((f"{prefix}_loudness", "loudness_verdict",
                                f"{what}: {meas['lufs']:.2f} LUFS (BP-50 band {band[0]:g}..{band[1]:g})"),
                               (f"{prefix}_true_peak", "true_peak_verdict",
                                f"{what}: true peak {meas.get('true_peak')} dBTP (BP-50 ceiling {tp:g})")):
        if key not in v:
            rows.append(G.row(gate, None, f"{what}: not measured"))
        else:
            rows.append(G.row(gate, v[key] == "PASS", ok_text, meas["lufs"] if "loud" in gate else meas.get("true_peak"),
                              level=G.REVIEW if v[key] == "REVIEW" else G.FAIL))
    return rows


def _deliver_mix(mix_raw: Path, delivered: Path) -> tuple[list[dict], dict, dict]:
    """HF-2 (FL-403, TD-302): the raw mix at the delivered loudness (``qa/targets.normalise_file``, BP-50) in its own file,
    with the BP-50 verdict rows of the result. Returns ``(rows, raw measurement, delivered measurement)``; a silent preview
    is copied as it is and its rows are NOT_RUN."""
    from explainer_engine.qa import targets as TG
    try:
        raw_meas = TG.measure_file(mix_raw)
    except RuntimeError:
        raw_meas = {}
    if raw_meas.get("lufs", float("-inf")) <= SILENT_LUFS:   # ebur128 reports its -70 gate for silence
        shutil.copyfile(mix_raw, delivered)
        why = "the mix has no measurable loudness (silent preview)"
        return [G.row("delivered_mix_loudness", None, why), G.row("delivered_mix_true_peak", None, why)], raw_meas, raw_meas
    meas = TG.normalise_file(mix_raw, delivered, "long", 48000, channels=2)
    return _loudness_rows("delivered_mix", meas, "the delivered mix"), raw_meas, meas


def _master_loudness_rows(master_mp4: Path) -> tuple[list[dict], dict]:
    """HF-2: BP-50 on the master file itself (no gate measured it before); the measurement and its two rows."""
    from explainer_engine.qa import targets as TG
    meas = TG.measure_file(Path(master_mp4))
    return _loudness_rows("master", meas, "the master file"), meas


def stage_sound(ep: Episode, rehearsal: bool):
    """G8: the sound plan again on the measured clock, then the one renderer (``audio/stems``) into the five stems. A full
    run renders shippable (no placeholder, no missing class, the real read); a rehearsal renders a preview."""
    from explainer_engine.audio import stems as STEMS
    from explainer_engine.episode import sound_plan as SP
    from explainer_engine.episode.production_runner import audit_rendered_audio_stems
    script = ep.timed_script()
    timing = ep.timing()
    routes = {r["shot_id"]: (r.get("route") if not r.get("fallback_for_wan") else "still_25d") for r in _records(ep)}
    plan = SP.build(script, fps=ep.fps, spines=TM.spines_of(timing), routes=routes, era=_era(ep))
    sources = SP.resolve(plan, ep.sound_library)
    SP.write(plan, sources, ep.root)
    read = ep.root / READ_REL
    stems_dir = ep.path("audio/stems")
    polished, polish_info = _polish_read(ep)      # HF-3: every use of the read as sound below takes the polished file
    narration = polished
    voice_rep = None
    if timing and timing.get("inserts"):   # VL-13: the LTX dialogue laid once on its shots, the read split around it
        from explainer_engine.videolane import ingest as VI
        from explainer_engine.videolane import voice as VV
        clip_audio = {}
        for ins in timing["inserts"]:
            rp = ep.root / "production" / "video" / f"{ins['shot_id']}.json"
            if rp.is_file():
                d = json.loads(rp.read_text(encoding="utf-8"))
                clip_audio[ins["shot_id"]] = {"path": str(ep.root / d["clip_path"]), "speech": d.get("speech") or []}
        missing = [i["shot_id"] for i in timing["inserts"] if i["shot_id"] not in clip_audio]
        if not missing:
            voice_rep = VV.compose(timing, narration, clip_audio, ep.path("audio/voice_track.wav"),
                                   read_speech=VI.speech(narration) if narration else None)
            write_json_atomic(ep.path("audio/voice_track.json"), voice_rep)
            narration = ep.path("audio/voice_track.wav")
    # FA-13 / Q2: the narrated video shots' own clip sound, offered to the renderer (it lays it only when the switch is on)
    from explainer_engine.videolane import plan as VP
    spoken = VP.clip_spoken(script)
    narrated_clips = {}
    for s in script.get("shots", []):
        rp = ep.root / "production" / "video" / f"{s['shot_id']}.json"
        if VP.is_video(s) and s["shot_id"] not in spoken and rp.is_file():
            narrated_clips[s["shot_id"]] = str(ep.root / json.loads(rp.read_text(encoding="utf-8"))["clip_path"])
    rep = STEMS.render(plan, sources, stems_dir, library_root=ep.sound_library,
                       narration=narration, shippable=not rehearsal, clip_audio=narrated_clips)
    write_json_atomic(ep.path("audio/stems_report.json"), rep)
    stem_audit = audit_rendered_audio_stems(stems_dir=stems_dir, script_doc=_with_line_times(script, timing), fps=ep.fps)
    write_json_atomic(ep.path("qa/audio_stem_audit.json"), stem_audit)
    bad = sorted(set(rep.get("placeholders") or []) | {w.split(":")[0] for w in rep.get("not_shippable_because") or []})
    rows = [G.row("sound_is_shippable", bool(rep.get("shippable")) and not bad,
                  "every sound a real take and the real read" if not bad else f"not shippable: {', '.join(bad[:10])}", bad[:30])]
    rows += list((rep.get("levels") or {}).get("rows") or [])
    if polish_info:
        rows.append(G.row("narrator_polished", True, f"{POLISHED_REL}: {polish_info['seconds_before']} s -> "
                          f"{polish_info['seconds_after']} s, the read untouched", polish_info))
    n_drop = int(stem_audit.get("mid_line_narration_dropouts", 0))
    rows.append(G.row("narration_has_no_dropouts", n_drop == 0 if read.is_file() else None,
                      f"{n_drop} mid-line dropout(s)" if read.is_file() else "no read to scan", n_drop))
    # P0-C (D-135): the cue sheet's AV rows (BP-54 on the rendered onsets, BP-55, BP-56, BP-81) and the stems' mix check
    # (BP-50/52 loudness and voice protection, BP-161 silence) join the stage's rows; machine QC, never a listening
    av = ("events_on_sync", "events_on_the_frame", "purpose_and_share", "overlap", "cue_density", "cue_rate_review",
          "one_emphasis_a_line", "review_required_events")
    rows += [dict(r, gate=f"cue_{r['gate']}") for r in rep.get("cue_rows", []) if r["gate"] in av]
    from explainer_engine.audio import mix_check as MC
    sheet = json.loads((stems_dir / "cue_sheet.json").read_text(encoding="utf-8"))
    mixq = MC.check(stems_dir, plan=plan, sheet=sheet)
    write_json_atomic(ep.path("qa/mix_check.json"), mixq)
    rows += [dict(r, gate=f"mix_{r['gate']}") for r in mixq["rows"]]
    from explainer_engine.episode import av_report as AVR
    from explainer_engine.episode import events as E
    ev_doc = E.events_report(script, TM.spines_of(timing), ep.fps)
    rep_av = AVR.event_report(ev_doc, plan, sheet, rep)
    write_json_atomic(ep.path("qa/av_event_report.json"), rep_av)
    delivered_rows, raw_meas, meas = _deliver_mix(stems_dir / "mix.wav", ep.path(DELIVERED_MIX_REL))   # HF-2
    rows += delivered_rows
    write_json_atomic(ep.path("qa/delivered_mix.json"), {"raw_mix": raw_meas, "delivered_mix": meas,
                                                         "delivered_sha256": _sha(ep.path(DELIVERED_MIX_REL))})
    return rows, {"stems": "audio/stems", "report": "audio/stems_report.json", "narration": rep.get("narration_source"),
                  "mix_check": "qa/mix_check.json", "av_event_report": "qa/av_event_report.json",
                  "voice_track": "audio/voice_track.json" if voice_rep else None,
                  "narrator_polish": polish_info, "delivered_mix": DELIVERED_MIX_REL,
                  "mix_raw_loudness": raw_meas, "mix_delivered_loudness": meas}


def _with_line_times(script: dict, timing: dict | None) -> dict:
    """The script with each line's measured start and end (the stem audit scans the voice inside them); planned lines get
    their shot's window."""
    doc = json.loads(json.dumps(script))
    t, at = 0.0, {}
    for s in doc.get("shots", []):
        d = float(s["target_duration_seconds"])
        for lid in s.get("audio_line_ids") or []:
            sp = (timing or {}).get("spines", {}).get(s["shot_id"]) or []
            if sp:
                a = t + sp[0]["start_frame"] / (timing["fps"])
                at[lid] = (a, t + d)
            else:
                at[lid] = (t, t + d)
        t += d
    for ln in doc.get("audio_lines", []):
        if ln.get("line_id") in at:
            ln["start_sec"], ln["end_sec"] = at[ln["line_id"]]
    return doc


def stage_assemble(ep: Episode, rehearsal: bool):
    """G9: the clips in order with the cut plan's transitions, written in chunks through ``production/assemble``
    (RULE-R1); ``--chunks A:B`` draws only those chunks and joins nothing until all exist."""
    from explainer_engine.edit.cinematic_transitions import plan_episode_cinematic_transitions
    from explainer_engine.production import assemble as ASM
    records = _records(ep)
    script = ep.timed_script()
    plans = plan_episode_cinematic_transitions(script, fps=ep.fps, allow_decorative_wipes=False, honour_authored=True)   # HF-1
    write_json_atomic(ep.path("editing/transition_plan.json"), plans)
    missing = [r["shot_id"] for r in records if not r.get("clip_path")]
    if missing:
        return [G.row("every_clip_to_assemble", False, f"{len(missing)} shot(s) without a clip", missing[:30])], {}
    mix = ep.path(DELIVERED_MIX_REL)   # HF-2: the delivered mix, never the raw one
    if not mix.is_file():
        return [G.row("the_delivered_mix_exists", False, f"no {DELIVERED_MIX_REL}: run the sound stage (G8) again")], {}
    master = ep.path(f"renders/final/{ep.manifest['episode_id']}_master.mp4")
    res = ASM.assemble_shot_clips(records, plans, mix, master, fps=ep.fps, size=ep.size, only=ep.chunks,
                                  chunk_seconds=ep.chunk_seconds if ep.chunk_seconds is not None else ASM.CHUNK_SECONDS)
    left = res["chunks"]["left"]
    planned = sum(int(r["total_frames"]) for r in records)
    rows = [G.row("every_chunk_drawn", not left, f"{res['chunks']['count'] - len(left)} of {res['chunks']['count']} "
                  f"chunk(s) on disk ({res['chunks']['reused']} reused)", left)]
    if not left:
        rows.append(G.row("master_frames_match_the_shots", res["total_frames"] == planned,
                          f"master {res['total_frames']} frames, the shots {planned}", res["total_frames"]))
    write_json_atomic(ep.path("production/master.json"), res)
    return rows, {"master": str(master.relative_to(ep.root)) if not left else None, "chunks": res["chunks"]["count"],
                  "left": left}


def paid_lines(root: Path) -> list[dict]:
    """Every ledger line of the episode that carries money (``estimate_usd`` or ``usd`` above zero)."""
    out = []
    for p in sorted((Path(root) / "logs").glob("*ledger*.jsonl")):
        for ln in p.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            d = json.loads(ln)
            if float(d.get("estimate_usd") or d.get("usd") or 0) > 0:
                out.append(dict(d, ledger=p.name))
    return out


def stage_qa(ep: Episode, rehearsal: bool):
    """G10: the measured acceptance report over what the run made (``episode/acceptance``), the contact sheet from the
    master, the manifest. The HF upload and the creator's approval follow outside the runner."""
    from explainer_engine.episode.acceptance import gates as acceptance_gates
    from explainer_engine.episode.context import load_episode_context
    from explainer_engine.episode.production_runner import generate_master_video_contact_sheet
    records = _records(ep)
    script = ep.timed_script()
    ctx = load_episode_context(ep.root)
    rd = lambda rel: json.loads(ep.path(rel).read_text(encoding="utf-8")) if ep.path(rel).is_file() else None  # noqa: E731
    audio, stem_audit, master = rd("audio/stems_report.json"), rd("qa/audio_stem_audit.json"), rd("production/master.json")
    plans = rd("editing/transition_plan.json")
    video = master if master and master.get("master_mp4_path") else None
    acc = acceptance_gates(root=ep.root, script=script, shot_records=records, transition_plans=plans, audio=audio,
                           stem_audit=stem_audit, video=video, fps=ep.fps,
                           forbidden_tokens=sorted(ctx.forbidden_semantic_tokens),
                           narration_source=_narration_source(ep, audio), paid=paid_lines(ep.root))
    from explainer_engine.videolane import plan as VP
    vm = None
    if video and any(VP.is_video(s) for s in script.get("shots", [])):   # VL-12: the master as the viewer gets it
        from explainer_engine.videolane import master_qa as VM
        vm = VM.check(ep.root, script, records, Path(video["master_mp4_path"]), ep.fps, timing=ep.timing(),
                      voice_report=rd("audio/voice_track.json"))
        acc = dict(acc, gates=acc["gates"] + vm["rows"])
        acc["status"] = G.verdict(acc["gates"])["status"]
    sheet = None
    if video:
        sheet = ep.path(f"qa/contact_sheets/{ep.manifest['episode_id']}_contact_sheet.jpg")
        generate_master_video_contact_sheet(master_mp4_path=Path(video["master_mp4_path"]), shot_records=records,
                                            out_jpg_path=sheet)
    realism_rows = []
    if video:   # P0-C (D-135): BP-189..BP-193 on the delivered file, measured, never a listening
        from explainer_engine.episode import av_report as AVR
        from explainer_engine.episode import events as E
        from explainer_engine.qa import sound_realism as RL
        plan = rd("audio/sound_plan.json") or {}
        lw = {ln["line_id"]: (ln["start_sec"], ln["end_sec"]) for ln in _with_line_times(script, ep.timing())["audio_lines"]
              if ln.get("start_sec") is not None and _narration_source(ep, audio) not in (None, "none")}
        tl = AVR.timeline(plan, records, audio, lw)
        write_json_atomic(ep.path("qa/scene_timeline.json"), tl)
        realism = RL.measure(Path(video["master_mp4_path"]), tl)
        write_json_atomic(ep.path("qa/sound_realism.json"), {k: v for k, v in realism.items() if k != "gates"})
        realism_rows = [dict(r, gate=f"realism_{r['gate']}") for r in realism["rows"]]
        sheet_doc = rd("audio/stems/cue_sheet.json")
        rep_av = AVR.event_report(E.events_report(script, TM.spines_of(ep.timing()), ep.fps), plan, sheet_doc, audio, realism)
        write_json_atomic(ep.path("qa/av_event_report.json"), rep_av)
        write_text_atomic(ep.path("qa/av_event_report.md"), AVR.markdown(rep_av))
    if video:   # HF-2: nothing measured the delivered file's loudness before; BP-50 on the master itself
        master_rows, master_meas = _master_loudness_rows(Path(video["master_mp4_path"]))
        write_json_atomic(ep.path("qa/master_loudness.json"), master_meas)
        realism_rows = realism_rows + master_rows
    acc = dict(acc, gates=list(acc["gates"]) + realism_rows)
    if realism_rows:
        acc["status"] = G.verdict(acc["gates"])["status"]
    manifest = {"schema": "episode_production_manifest/4.3", "episode_id": ctx.episode_id, "title": ctx.title,
                "historical_period": ctx.era_id, "rehearsal": rehearsal, "master_video": video,
                "contact_sheet_path": str(sheet.relative_to(ep.root)) if sheet else None,
                "stages": state(ep), "shots": records, "acceptance": acc, "all_gates_passed": acc["status"] == G.PASS and not rehearsal}
    write_json_atomic(ep.path("production/production_manifest.json"), manifest)
    write_json_atomic(ep.path("qa/acceptance_report.json"), manifest)
    return acc["gates"], {"manifest": "production/production_manifest.json", "acceptance": acc["status"],
                         "contact_sheet": manifest["contact_sheet_path"],
                         "video_master_qa": "qa/video_master_qa.json" if vm else None}


def _narration_source(ep: Episode, audio: dict | None) -> str | None:
    if audio is None:
        return None
    read = ep.root / READ_REL
    src = audio.get("narration_source") or ""
    heard = src.startswith("file:") or (src not in ("", "none") and Path(src).is_file())
    return str(read) if heard and read.is_file() else "none"


STAGE_FUNCS = {"script": stage_script, "sound_plan": stage_sound_plan, "pictures": stage_pictures, "voice": stage_voice,
               "clips": stage_clips, "sound": stage_sound, "assemble": stage_assemble, "qa": stage_qa}


# --- CLI ---------------------------------------------------------------------------------------------------------------

def _size(text: str) -> tuple[int, int]:
    w, h = text.lower().split("x")
    return int(w), int(h)


def _chunks(text: str) -> tuple[int, int]:
    a, b = text.split(":")
    return int(a), int(b)


def _print_state(ep: Episode) -> None:
    for s in state(ep):
        mark = "-" if s["status"] is None else ("fresh" if s["fresh"] else "STALE")
        print(f"{s['gate']:6} {s['stage']:11} {str(s['status'] or 'not run'):10} {mark:6}"
              f"{' rehearsal' if s['rehearsal'] else ''}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.episode", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run one stage (--stage) or every stage up to one (--to)")
    r.add_argument("episode", type=Path)
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--stage")
    g.add_argument("--to")
    r.add_argument("--rehearsal", action="store_true", help="go on after a FAIL to rehearse the chain (never ships)")
    r.add_argument("--force", action="store_true", help="run stages and clips again even when their records are fresh")
    r.add_argument("--size", type=_size, help="WxH of the clips and the master (default episode.json render_size or 1920x1080)")
    r.add_argument("--fps", type=int)
    r.add_argument("--chunks", type=_chunks, help="A:B, draw only those assembly chunks (RULE-R1)")
    r.add_argument("--chunk-seconds", type=float)
    r.add_argument("--sound-library", type=Path, help="HF-7: the sound library folder (a manifest.json and its categories); "
                   "default assets/audio/library. Its manifest is in the fingerprint of G4 and G8, so give it to every call")
    s = sub.add_parser("status", help="the stages and their records")
    s.add_argument("episode", type=Path)
    s.add_argument("--sound-library", type=Path, help="the same folder the runs used (HF-7)")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        _print_state(Episode(a.episode, sound_library=a.sound_library))
        return 0
    ep = Episode(a.episode, size=a.size, fps=a.fps, rehearsal=a.rehearsal, force=a.force, chunks=a.chunks,
                 chunk_seconds=a.chunk_seconds, sound_library=a.sound_library)
    try:
        recs = [run_stage(ep, a.stage)] if a.stage else run_to(ep, a.to)
    except StageRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    for rec in recs:
        v = rec["verdict"]
        print(f"{rec['gate']:6} {rec['stage']:11} {v['status']:10}{' (kept)' if rec.get('reused') else ''}"
              f"{' rehearsal' if rec.get('rehearsal') else ''}")
        for row in rec["rows"]:
            if row["status"] != G.PASS:
                print(f"         {row['status']:8} {row['gate']}: {row['detail']}")
    last = recs[-1]["verdict"]["status"]
    return 0 if last in GO_ON else 1


if __name__ == "__main__":
    sys.exit(main())
