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
import sys
import time
from pathlib import Path

from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.core.store import write_json_atomic
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
    return rows, {"mix": R.mix_report(doc), "shots": len(shots), "audit_status": audit["status"]}


def stage_sound_plan(ep: Episode, rehearsal: bool):
    """G4: the sound plan on the planned clock (the sound stage rebuilds it on the measured one), era-checked, its sources
    resolved, the needs listed."""
    from explainer_engine.episode import sound_plan as SP
    plan = SP.build(ep.script, fps=ep.fps)
    sources = SP.resolve(plan, ep.sound_library)
    path = SP.write(plan, sources, ep.root)
    needs = SP.needs(sources)
    blocked = plan["blocked_era_events"]
    rows = [G.row("no_era_foreign_sound_asked", not blocked, f"{len(blocked)} sound event(s) the era never heard, asked "
                  "by the script", blocked[:20]),
            G.row("every_sound_class_has_a_take", not needs, f"{len(needs)} class(es) still need a real take (the needs "
                  "list; new takes are paid credits, the creator's word first)", [n["class"] for n in needs][:30],
                  level=G.REVIEW)]
    return rows, {"plan": str(path.relative_to(ep.root)), "classes": len(plan["classes"]), "needs": len(needs)}


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
    return rows, {"timing": "audio/timing.json", "read_s": round(read_s, 3), "planned_s": round(planned, 3),
                  "total_frames": timing["total_frames"]}


def _events_for_picture(plan_shot: dict) -> list[dict]:
    return [{"frame": int(e["at_frame"]), "kind": e["picture_event"]} for e in plan_shot.get("events", [])
            if e.get("picture_event")]


def _clip_key(shot: dict, files: list, ep: Episode, spine) -> str:
    return _digest({"shot": shot, "files": files, "size": list(ep.size), "fps": ep.fps, "spine": spine})


def _wan_clip(ep: Episode, sid: str) -> dict | None:
    """The QA'd Wan clip of a shot, if ``aivideo/wan_adapter.run_shot`` made one: its report beside the clip."""
    rep = ep.root / "production" / "wan" / f"{sid}.json"
    if not rep.is_file():
        return None
    doc = json.loads(rep.read_text(encoding="utf-8"))
    if doc.get("route") != "wan" or doc.get("status") == G.FAIL or not doc.get("clip_path"):
        return None
    p = ep.path(doc["clip_path"]) if not Path(doc["clip_path"]).is_absolute() else Path(doc["clip_path"])
    return dict(doc, clip_path=str(p)) if p.is_file() else None


def stage_clips(ep: Episode, rehearsal: bool):
    """G7: every shot's clip by its route. ``map_action``: the action map (P4) with its gates (a map shot without actions
    FAILs, final audit B1);
    ``still_25d``: the layered 2.5D renderer (P5) with the sound plan's picture events and the measured spine; ``wan``: the
    QA'd clip of the Wan adapter (P6), never generated here; without one the shot FAILs, and a rehearsal draws it with the
    adapter's 2.5D fallback. A clip whose shot, pictures, spine and size are unchanged is reused."""
    from explainer_engine.aivideo.wan_adapter import DEFAULT_FALLBACK
    from explainer_engine.episode import sound_plan as SP
    from explainer_engine.production import layers25d as L25
    from explainer_engine.production.map_clip import render_action_map_clip
    script = ep.timed_script()
    timing = ep.timing()
    spines = TM.spines_of(timing)
    pics = json.loads(ep.path("production/pictures.json").read_text(encoding="utf-8"))["pictures"] \
        if ep.path("production/pictures.json").is_file() else {}
    plan = SP.build(script, fps=ep.fps, spines=spines)
    plan_by = {s["shot_id"]: s for s in plan["shots"]}
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
        key = _clip_key(sh, [start, end], ep, spines.get(sid))
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
                wan = _wan_clip(ep, sid) if route == "wan" else None
                if route == "wan" and wan is None:   # counted before the picture check (final audit B2)
                    missing_wan.append(sid)
                if start is None:
                    missing_pic.append(sid)
                    raise ContractError(f"{sid}: no start picture (G5)")
                if wan is not None:
                    out.write_bytes(Path(wan["clip_path"]).read_bytes())
                    res = {"provider": wan.get("backend"), "status": wan["status"], "total_frames": frames}
                    rec.update(visual_type=sh.get("visual_type"), provider=f"wan:{wan.get('backend')}", status=wan["status"],
                               wan_attempts=len(wan.get("attempts") or []))
                else:
                    shot = sh
                    if route == "wan":
                        if not rehearsal:
                            raise ContractError(f"{sid}: no QA'd Wan clip (production/wan/{sid}.json); Wan clips are made "
                                                "by the adapter on the creator's approved plan, never by the runner")
                        shot = dict(sh, motion_imitation=sh.get("fallback_motion_imitation") or DEFAULT_FALLBACK)
                        fallback.append(sid)
                    res = L25.render_clip(shot, ep.root / start["file"], out, width=w, height=h, fps=ep.fps,
                                          end_picture=(ep.root / end["file"]) if end else None, script=script,
                                          events=_events_for_picture(plan_by.get(sid, {})), spine=spines.get(sid))
                    rec.update(visual_type=sh.get("visual_type", "cinematic_scene"), provider=res["provider"],
                               status=res["gates"]["status"], gates_25d=res["gates"]["status"], camera=res["camera"],
                               effects=res["effects"], families=res["families"],
                               fallback_for_wan=route == "wan")
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
    from explainer_engine.episode import router as R
    durations = {r["shot_id"]: r["duration_sec"] for r in records}
    return rows, {"records": "production/shot_records.json", "made": made, "reused": reused,
                  "mix": R.mix_report(script, durations if timing else None)}


def _records(ep: Episode) -> list[dict]:
    p = ep.path("production/shot_records.json")
    if not p.is_file():
        raise ContractError("no production/shot_records.json: run the clips stage (G7) first")
    return json.loads(p.read_text(encoding="utf-8"))["shots"]


def stage_sound(ep: Episode, rehearsal: bool):
    """G8: the sound plan again on the measured clock, then the one renderer (``audio/stems``) into the five stems. A full
    run renders shippable (no placeholder, no missing class, the real read); a rehearsal renders a preview."""
    from explainer_engine.audio import stems as STEMS
    from explainer_engine.episode import sound_plan as SP
    from explainer_engine.episode.production_runner import audit_rendered_audio_stems
    script = ep.timed_script()
    timing = ep.timing()
    routes = {r["shot_id"]: (r.get("route") if not r.get("fallback_for_wan") else "still_25d") for r in _records(ep)}
    plan = SP.build(script, fps=ep.fps, spines=TM.spines_of(timing), routes=routes)
    sources = SP.resolve(plan, ep.sound_library)
    SP.write(plan, sources, ep.root)
    read = ep.root / READ_REL
    stems_dir = ep.path("audio/stems")
    rep = STEMS.render(plan, sources, stems_dir, library_root=ep.sound_library,
                       narration=read if read.is_file() else None, shippable=not rehearsal)
    write_json_atomic(ep.path("audio/stems_report.json"), rep)
    stem_audit = audit_rendered_audio_stems(stems_dir=stems_dir, script_doc=_with_line_times(script, timing), fps=ep.fps)
    write_json_atomic(ep.path("qa/audio_stem_audit.json"), stem_audit)
    bad = sorted(set(rep.get("placeholders") or []) | {w.split(":")[0] for w in rep.get("not_shippable_because") or []})
    rows = [G.row("sound_is_shippable", bool(rep.get("shippable")) and not bad,
                  "every sound a real take and the real read" if not bad else f"not shippable: {', '.join(bad[:10])}", bad[:30])]
    rows += list((rep.get("levels") or {}).get("rows") or [])
    n_drop = int(stem_audit.get("mid_line_narration_dropouts", 0))
    rows.append(G.row("narration_has_no_dropouts", n_drop == 0 if read.is_file() else None,
                      f"{n_drop} mid-line dropout(s)" if read.is_file() else "no read to scan", n_drop))
    return rows, {"stems": "audio/stems", "report": "audio/stems_report.json", "narration": rep.get("narration_source")}


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
    plans = plan_episode_cinematic_transitions(script, fps=ep.fps, allow_decorative_wipes=False)
    write_json_atomic(ep.path("editing/transition_plan.json"), plans)
    missing = [r["shot_id"] for r in records if not r.get("clip_path")]
    if missing:
        return [G.row("every_clip_to_assemble", False, f"{len(missing)} shot(s) without a clip", missing[:30])], {}
    mix = ep.path("audio/stems/mix.wav")
    if not mix.is_file():
        return [G.row("the_mix_exists", False, "no audio/stems/mix.wav: run the sound stage (G8)")], {}
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
    sheet = None
    if video:
        sheet = ep.path(f"qa/contact_sheets/{ep.manifest['episode_id']}_contact_sheet.jpg")
        generate_master_video_contact_sheet(master_mp4_path=Path(video["master_mp4_path"]), shot_records=records,
                                            out_jpg_path=sheet)
    manifest = {"schema": "episode_production_manifest/4.3", "episode_id": ctx.episode_id, "title": ctx.title,
                "historical_period": ctx.era_id, "rehearsal": rehearsal, "master_video": video,
                "contact_sheet_path": str(sheet.relative_to(ep.root)) if sheet else None,
                "stages": state(ep), "shots": records, "acceptance": acc, "all_gates_passed": acc["status"] == G.PASS and not rehearsal}
    write_json_atomic(ep.path("production/production_manifest.json"), manifest)
    write_json_atomic(ep.path("qa/acceptance_report.json"), manifest)
    return acc["gates"], {"manifest": "production/production_manifest.json", "acceptance": acc["status"],
                         "contact_sheet": manifest["contact_sheet_path"]}


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
    s = sub.add_parser("status", help="the stages and their records")
    s.add_argument("episode", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "status":
        _print_state(Episode(a.episode))
        return 0
    ep = Episode(a.episode, size=a.size, fps=a.fps, rehearsal=a.rehearsal, force=a.force, chunks=a.chunks,
                 chunk_seconds=a.chunk_seconds)
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
