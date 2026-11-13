"""The final master of an episode measured as a file (VL-12, docs/VIDEO_LANE.md): what the viewer gets, not what the plan said.

The runner's acceptance report (``episode/acceptance``) checks the plan and the records; this module opens the assembled
master and its stems and measures:

* the container: the episode's frame rate, an audio stream, picture and sound of one length (one frame + 50 ms);
* the frame count against the shots' frames;
* black and frozen runs inside every ``video`` shot (BP-164: a run of ``frozen_run_frames`` frames under ``frozen_diff_max``,
  or under ``black_luma_max``): LTX stalls and fades to black are the lane's known failures;
* the shot order: every video shot's middle frame in the master matches its own trimmed clip better than any other video
  clip (a swapped or missing clip FAILs);
* the cuts by continuity mode on the real frames (``videolane/cuts``);
* the dialogue: every clip-spoken shot's line is heard in its window of the voice stem, and the voice track laid it once
  (``audio/voice_track.json``, ``videolane/voice``);
* the bed: every place's ambience (``audio/stems/ambience.wav``) never drops under BP-189's floor inside its span, across
  the cuts and under the dialogue (ducking, never muting, BP-52); a level jump at a cut inside one bed over BP-191's
  ``cut_jump_db_max`` is REVIEW (the duck can move it legitimately);
* the mix floor: no window of the master's own sound under BP-189's floor (dead air).

Every FAIL gets a repair line (``repairs``) with its class: A (free and automatic: re-cut, re-assemble, re-mix from the
records on disk), B (free, but a stage or a plan changes first: re-plan, sound plan, re-ingest), C (paid: a clip is made
again on the creator's approved plan). Nothing is repaired here; the line says what, from which inputs (sha256), and which
stage runs it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

AV_TOL_S = 0.05
ORDER_DIFF_MAX = 14.0        # engineering default (0..255 grey, 160 px): the master's frame and its clip's frame are one picture
BED_EDGE_S = 0.6             # the J/L bridge zone at a bed's edges is not judged (episode/sound_plan BRIDGE_S is shorter)
WIN_S = 0.25


def _sha(p: Path) -> str | None:
    import hashlib
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def _runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def windows(records: list[dict]) -> dict:
    """``{shot_id: (first frame, end frame)}`` in the master (the assembler joins the shots end to end)."""
    out, t = {}, 0
    for r in records:
        out[r["shot_id"]] = (t, t + int(r["total_frames"]))
        t += int(r["total_frames"])
    return out


def black_frozen(grey: np.ndarray, a: int, b: int) -> dict:
    run = int(SR.T("BP-164", "frozen_run_frames"))
    seg = grey[a:b].astype(np.float32)
    if len(seg) < 2:
        return {"black": [], "frozen": []}
    luma = seg.mean(axis=(1, 2))
    diff = np.abs(np.diff(seg, axis=0)).mean(axis=(1, 2))
    black = _runs(luma < float(SR.T("BP-164", "black_luma_max")), run)          # as training/video_qa CLIP-10/11 count
    frozen = _runs(diff < float(SR.T("BP-164", "frozen_diff_max")), run + 1)
    return {"black": [(a + i, a + j) for i, j in black], "frozen": [(a + i, a + j + 1) for i, j in frozen]}


def check(root: Path, script: dict, records: list[dict], master: Path, fps: int, *, timing: dict | None = None,
          stems_dir: Path | None = None, voice_report: dict | None = None, sound_plan: dict | None = None,
          write: bool = True) -> dict:
    from explainer_engine.qa import sound_realism as R
    from explainer_engine.training import video_qa as VQ
    from explainer_engine.videolane import cuts as CU
    from explainer_engine.videolane import ingest as IN
    from explainer_engine.videolane import plan as P
    root = Path(root)
    stems_dir = Path(stems_dir) if stems_dir else root / "audio" / "stems"
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    rows, repairs, metrics = [], [], {}
    win = windows(records)
    planned = sum(int(r["total_frames"]) for r in records)
    video_ids = [r["shot_id"] for r in records if P.is_video(by.get(r["shot_id"], {}))]
    spoken = P.clip_spoken(script)

    def fix(row_name, shot, cls, action, inputs=(), stage=None):
        repairs.append({"row": row_name, "shot_id": shot, "class": cls, "action": action, "stage": stage,
                        "inputs": {str(p): _sha(root / p if not Path(p).is_absolute() else Path(p)) for p in inputs}})

    # --- the container and the frames
    pr = IN.probe(master)
    grey = CU.decode(master)
    n = len(grey)
    av_gap = abs(pr["duration"] - pr["audio_duration"]) if pr["has_audio"] else None
    metrics["container"] = dict(pr, frames=n, planned_frames=planned, av_gap_s=av_gap)
    ok_c = abs(pr["fps"] - fps) < 0.01 and pr["has_audio"] and av_gap is not None and av_gap <= 1.0 / fps + AV_TOL_S
    rows.append(G.row("master_container", ok_c, f"{pr['fps']:.3f} fps (episode {fps}), audio {'yes' if pr['has_audio'] else 'NO'}"
                      + (f", picture/sound gap {av_gap:.3f} s" if av_gap is not None else ""), metrics["container"]))
    if not ok_c:
        fix("master_container", None, "A", "assemble again (G9) from the shot records", ["production/shot_records.json"],
            "assemble")
    rows.append(G.row("master_frames_match_the_plan", n == planned, f"master {n} frames, the shots {planned}", n))
    if n != planned:
        fix("master_frames_match_the_plan", None, "A", "assemble again (G9); a shot clip of the wrong length is cut again "
            "from its raw clip (videolane.ingest)", ["production/shot_records.json"], "assemble")

    # --- black / frozen inside video shots
    bad_bf = []
    for sid in video_ids:
        a, b = win[sid]
        bf = black_frozen(grey, a, min(b, n))
        metrics.setdefault("black_frozen", {})[sid] = bf
        for kind in ("black", "frozen"):
            for i, j in bf[kind]:
                bad_bf.append(f"{sid}: {kind} {i / fps:.2f}-{j / fps:.2f} s ({j - i} frames)")
                rec = json.loads((root / "production" / "video" / f"{sid}.json").read_text(encoding="utf-8")) \
                    if (root / "production" / "video" / f"{sid}.json").is_file() else {}
                handle = float(rec.get("raw_seconds") or 0) - float(rec.get("out_s") or 0)
                if kind == "frozen" and j == min(b, n) and handle > (j - i) / fps:
                    fix("video_shots_not_black_or_frozen", sid, "A", f"re-cut {sid} earlier: the stall is its last {j - i} "
                        f"frames and the raw clip has {handle:.2f} s more (move the out point, re-ingest)",
                        [rec.get("raw_path", "")], "videolane.ingest")
                else:
                    fix("video_shots_not_black_or_frozen", sid, "C", f"make {sid} again (LTX {kind} run inside the edit)",
                        [rec.get("raw_path", "")] if rec else [], "ltx")
    rows.append(G.row("video_shots_not_black_or_frozen", not bad_bf, f"{len(bad_bf)} black or frozen run(s) inside the "
                      f"{len(video_ids)} video shot(s) (BP-164)", bad_bf[:20]))

    # --- shot order: the master's middle frame of every video shot against every video clip's middle frame
    mids = {}
    for r in records:
        sid = r["shot_id"]
        if sid in video_ids and r.get("clip_path") and Path(r["clip_path"]).is_file():
            g = VQ.decode_gray(r["clip_path"], (grey.shape[2], grey.shape[1]))
            if len(g):
                mids[sid] = g[len(g) // 2].astype(np.float32)
    order_bad = []
    for sid, ref in mids.items():
        a, b = win[sid]
        m = (a + b) // 2
        if m >= n:
            order_bad.append(f"{sid}: not in the master (it ends at frame {n})")
            continue
        f = grey[m].astype(np.float32)
        d_own = float(np.abs(f - ref).mean())
        others = {o: float(np.abs(f - g).mean()) for o, g in mids.items() if o != sid}
        best = min(others, key=others.get) if others else None
        metrics.setdefault("order", {})[sid] = {"own": round(d_own, 3), "best_other": best,
                                                "best_other_diff": round(others[best], 3) if best else None}
        if d_own > ORDER_DIFF_MAX or (best and others[best] < d_own):
            order_bad.append(f"{sid}: its window shows {'clip ' + best if best and others[best] < d_own else 'another picture'} "
                             f"(own clip {d_own:.1f}, max {ORDER_DIFF_MAX})")
    for o in order_bad:
        fix("video_shots_in_order", o.split(":")[0], "A", "assemble again from the records (the clip at that place is not "
            "its shot's)", ["production/shot_records.json"], "assemble")
    rows.append(G.row("video_shots_in_order", not order_bad if mids else None,
                      f"{len(order_bad)} of {len(mids)} video shot(s) out of place" if mids else "no video clip to compare",
                      order_bad[:20]))

    # --- cuts on the real frames
    cut = CU.check_master(master, records, script, fps)
    rows += cut["rows"]
    # FA-14: the heroes again on the clips (last frame of a shot against the first of the next, per scene; switch Q3)
    from explainer_engine.videolane import identity as ID
    rec_by = {r["shot_id"]: r for r in records}
    id_rows = []
    for scene in P.scenes(script):
        ids = [s["shot_id"] for s in scene if P.is_video(s) and (rec_by.get(s["shot_id"]) or {}).get("clip_path")
               and Path(rec_by[s["shot_id"]]["clip_path"]).is_file()]
        if len(ids) < 2:
            continue
        frames = {}
        for sid in ids:
            fr = VQ.read_video(rec_by[sid]["clip_path"])[0]
            frames[sid] = (fr[0], fr[-1])
        id_rows += ID.costume_findings(script, ids, frames)
    if id_rows or any(P.is_video(s) for s in script.get("shots", [])):
        lv = ID.levels()
        rows.append(G.row("clips_hero_costume_holds", not id_rows, f"{len(id_rows)} hero box(es) whose colours move "
                          f"across a cut of the clips (BP-166; switch Q3 -> {lv['costume']})", id_rows[:20],
                          level=lv["costume"]))
    metrics["cuts"] = cut["cuts"]
    for c in cut["cuts"]:
        if c["status"] == G.FAIL:
            if c["mode"] == "continuation":
                fix("cuts_continuation_and_coverage", c["shot_in"], "C", f"make {c['shot_in']} again from the hand-over "
                    f"frame of {c['shot_out']} (best_tail, VL-05), or re-plan it as coverage", [], "ltx")
            else:
                fix("cuts_continuation_and_coverage", c["shot_in"], "B", f"re-plan {c['shot_in']}: a size step or 30 degrees "
                    "from the shot before (VL-04), new picture", [], "script")

    # --- dialogue heard once, in its window
    voice = stems_dir / "narration.wav"
    heard_bad, laid_bad = [], []
    clip_ids = [s for s in video_ids if s in spoken]
    if clip_ids and voice.is_file():
        x = R.read_audio(voice)
        spans = R.speech_spans(x)
        for sid in clip_ids:
            a, b = win[sid][0] / fps, win[sid][1] / fps
            rec_p = root / "production" / "video" / f"{sid}.json"
            sp = json.loads(rec_p.read_text(encoding="utf-8")).get("speech") if rec_p.is_file() else None
            want = [(a + s, a + e) for s, e in (sp or [(0.0, b - a)])]
            need = sum(e - s for s, e in want)
            got = sum(max(0.0, min(e, e2) - max(s, s2)) for s, e in want for s2, e2 in spans)
            metrics.setdefault("dialogue", {})[sid] = {"window_s": [round(a, 3), round(b, 3)],
                                                       "heard_s": round(got, 3), "line_s": round(need, 3)}
            if need <= 0 or got < 0.5 * need:
                heard_bad.append(f"{sid}: {got:.2f} of {need:.2f} s of its line heard in {a:.2f}-{b:.2f} s")
                fix("dialogue_heard_in_its_shot", sid, "B", f"ingest {sid} again and rebuild the voice track (videolane.voice);"
                    " if the raw clip has no line, make it again (C)", [str(rec_p.relative_to(root))], "voice")
    if voice_report and clip_ids:
        laid = voice_report.get("laid") or []
        for sid in clip_ids:
            k = sum(1 for e in laid if e.get("what") == "clip" and e.get("shot_id") == sid)
            if k != 1:
                laid_bad.append(f"{sid}: laid {k} time(s)")
        clip_win = [(win[s][0] / fps, win[s][1] / fps) for s in clip_ids]
        for e in laid:
            if e.get("what") == "read":
                s0 = e["at_s"]
                s1 = s0 + e["read_s"][1] - e["read_s"][0]
                for a, b in clip_win:
                    if min(s1, b) - max(s0, a) > 1.0 / fps:
                        laid_bad.append(f"the read {e['read_s']} is laid over a clip's window {a:.2f}-{b:.2f} s")
        for o in laid_bad:
            fix("dialogue_laid_once", None, "A", "rebuild the voice track from the clock (videolane.voice)",
                ["audio/timing.json"], "voice")
    rows.append(G.row("dialogue_heard_in_its_shot", not heard_bad if (clip_ids and voice.is_file()) else
                      (True if not clip_ids else None),
                      f"{len(heard_bad)} of {len(clip_ids)} clip line(s) not heard in their shot" if clip_ids and voice.is_file()
                      else ("no clip-spoken shot" if not clip_ids else "no voice stem to measure"), heard_bad[:20]))
    rows.append(G.row("dialogue_laid_once", not laid_bad if voice_report else (True if not clip_ids else None),
                      f"{len(laid_bad)} line(s) laid twice or under the read" if voice_report else
                      ("no clip-spoken shot" if not clip_ids else "no voice track report"), laid_bad[:20]))

    # --- the bed: never under the floor inside its place, no jump at a cut inside one bed
    amb = stems_dir / "ambience.wav"
    floor = float(SR.T("BP-189", "floor_dbfs"))
    jump_max = float(SR.T("BP-191", "cut_jump_db_max"))
    bed_bad, jump_rev = [], []
    if sound_plan is None and (root / "audio" / "sound_plan.json").is_file():
        sound_plan = json.loads((root / "audio" / "sound_plan.json").read_text(encoding="utf-8"))
    if amb.is_file() and sound_plan:
        y = R.read_audio(amb)
        rate = R.SR
        lv = R.window_db(y, WIN_S)
        metrics["bed"] = []
        for bed in sound_plan.get("beds") or []:
            a = float(bed["start_s"]) + (BED_EDGE_S if float(bed["start_s"]) > 0 else 0.0)
            b = float(bed["end_s"]) - BED_EDGE_S
            ia, ib = int(a / WIN_S), int(b / WIN_S)
            seg = lv[ia:ib]
            if not len(seg):
                continue
            low = float(seg.min())
            metrics["bed"].append({"bed_id": bed["bed_id"], "span_s": [round(a, 2), round(b, 2)], "min_db": round(low, 2),
                                   "median_db": round(float(np.median(seg)), 2)})
            if low < floor:
                k = int(np.argmin(seg))
                t = (ia + k) * WIN_S
                where = next((s for s in bed.get("shot_ids", []) if win.get(s) and win[s][0] / fps <= t < win[s][1] / fps),
                             None)
                bed_bad.append(f"{bed['bed_id']}: the bed drops to {low:.1f} dBFS at {t:.2f} s (shot {where}; floor "
                               f"{floor} dBFS, BP-189)")
                fix("bed_continuous_in_its_place", where, "B", f"the sound plan or the stems leave {bed['bed_id']} silent in "
                    f"{where}: render the stems again from the plan (G8)", ["audio/sound_plan.json"], "sound")
            for sid in bed.get("shot_ids", [])[1:]:
                t = win[sid][0] / fps if sid in win else None
                if t is None or not (a < t < b):
                    continue
                i = int(t * rate)
                w = int(0.1 * rate)
                g = int(0.02 * rate)
                before = R.db(float(np.sqrt(np.mean(y[max(0, i - g - w):i - g] ** 2)) + 1e-12))
                after = R.db(float(np.sqrt(np.mean(y[i + g:i + g + w] ** 2)) + 1e-12))
                if abs(after - before) > jump_max:
                    jump_rev.append(f"{sid} @ {t:.2f} s: the bed jumps {after - before:+.1f} dB at the cut (max {jump_max})")
    rows.append(G.row("bed_continuous_in_its_place", not bed_bad if (amb.is_file() and sound_plan) else None,
                      f"{len(bed_bad)} bed(s) drop under the floor inside their place" if amb.is_file() and sound_plan
                      else "no ambience stem or sound plan to measure", bed_bad[:20]))
    rows.append(G.row("bed_level_holds_at_cuts", not jump_rev if (amb.is_file() and sound_plan) else None,
                      f"{len(jump_rev)} cut(s) where the bed jumps over {jump_max} dB" if amb.is_file() and sound_plan
                      else "no ambience stem or sound plan to measure", jump_rev[:20], level=G.REVIEW))

    # --- the master's own sound: no dead air
    if pr["has_audio"]:
        z = R.read_audio(master)
        lv = R.window_db(z, 0.5)
        inner = lv[1:-1] if len(lv) > 2 else lv
        dead = [f"{(i + 1) * 0.5:.1f} s: {v:.1f} dBFS" for i, v in enumerate(inner) if v < floor]
        metrics["mix_min_db"] = round(float(inner.min()), 2) if len(inner) else None
        rows.append(G.row("master_has_no_dead_air", not dead, f"{len(dead)} half-second window(s) under {floor} dBFS "
                          "(BP-189)", dead[:20]))
        if dead:
            fix("master_has_no_dead_air", None, "B", "a place without a bed or a gap in the stems: sound plan, then G8",
                ["audio/sound_plan.json"], "sound")
    else:
        rows.append(G.row("master_has_no_dead_air", False, "the master has no sound"))

    out = {"schema": "video_master_qa/1", "master": str(master), "master_sha256": _sha(master), "fps": fps, "rows": rows,
           "verdict": G.verdict(rows)["status"], "metrics": metrics, "repairs": repairs,
           "repair_classes": {"A": "free, automatic from the records on disk", "B": "free, a stage or plan changes first",
                              "C": "paid: the clip is made again on the creator's approved plan"}}
    if write:
        write_json_atomic(root / "qa" / "video_master_qa.json", out)
        if cut["cuts"]:
            try:
                out["boundary_sheet"] = str(CU.boundary_sheet(master, cut["cuts"], root / "qa" / "cut_boundaries.jpg"))
                write_json_atomic(root / "qa" / "video_master_qa.json", out)
            except Exception as exc:   # the sheet is for the eye; its failure is reported, never hidden
                out["boundary_sheet_error"] = str(exc)
                write_json_atomic(root / "qa" / "video_master_qa.json", out)
    return out
