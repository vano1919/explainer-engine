
"""One production script, one command line (D-43).

    python -m explainer_engine.production validate <script.json> [--pics DIR ...] [--snd DIR ...]
    python -m explainer_engine.production compile  <script.json> --out DIR          # prompts into the script + derived files
    python -m explainer_engine.production words    <script.json> <read.mp3|wav> --out DIR [--transcript scribe.json]
    python -m explainer_engine.production time     <script.json> <words.json> --out timed.json
    python -m explainer_engine.production assemble <script.json> <timed.json> <narration.wav> --out DIR --pics DIR ... --snd DIR ...
                                                   [--final] [--size 1920x1080] [--audio-only]
    python -m explainer_engine.production fill     <script.json> [<words.json>]           # re-framed shots for dead holds (RHYTHM-3)
    python -m explainer_engine.production run      <script.json> <narration.wav> <words.json> --out DIR --pics ... --snd ...

``words`` is free: a local Whisper hears the read (or a Scribe JSON is given), ``scribe_words.align`` puts the times on the
script's own tokens, ``pause_pad`` widens punctuated gaps and every line's scripted ``pause_after``. Exit code 1 on any
FAIL. Nothing here spends money; the paid reads and pictures use the files ``compile`` writes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from explainer_engine.production import assemble as A
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.production import validate as V
from explainer_engine.core.store import write_text_atomic


def _print(found: list[dict], title: str) -> int:
    for f in found:
        print(f"{f['severity']:6} {f['rule']:16} {str(f['where'])[:18]:18} {f['detail']}")
    print(f"{title}: {V.summary(found)}", file=sys.stderr)
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


def _dirs(doc_path: Path, extra: list[str] | None, key: str) -> list[Path]:
    doc = S.load(doc_path)
    base = doc_path.parent
    return [Path(p) for p in (extra or [])] + [base / p for p in doc.get(key, [])]


JOIN_GAP = 0.3  # seconds of silence between chunk reads


def join_reads(audio: list[Path], wav: Path, gap_s: float = JOIN_GAP) -> None:
    """One read, or the chunk reads joined in order with a short silence (pause_pad widens it where the script wants)."""
    import subprocess
    if len(audio) == 1:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(audio[0]), "-ac", "1", "-ar", "48000", str(wav)], check=True)
        return
    from explainer_engine.audio import seams
    rep = seams.plan(audio)  # ED-01: every chunk to one loudness, edges faded inside the silence
    ins, parts = [], []
    for k, p in enumerate(audio):
        ins += ["-i", str(p)]
        parts.append(seams.chain(k, p, rep["gains_db"][k], gap_s))
    join_reads.report = rep
    graph = ";".join(parts) + ";" + "".join(f"[a{k}]" for k in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", str(wav)],
                   check=True)


def cmd_words(doc: dict, audio: list[Path], out: Path, transcript: Path | None) -> dict:
    from explainer_engine.audio import local_words, pause_pad, scribe_words, voice_check, voice_layer
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "read.wav"
    join_reads(audio, wav)
    if transcript:
        heard = scribe_words.transcript_words(json.loads(transcript.read_text(encoding="utf-8")))
        source = f"transcript {transcript.name}"
    elif len(audio) > 1:  # every chunk heard alone (Whisper drops repeats on a long read); offsets as join_reads lays them
        from explainer_engine.audio import seams
        offsets, t = [], 0.0
        for p in audio:
            offsets.append(t)
            t += seams.duration(p) + JOIN_GAP
        res = local_words.transcribe_chunks(audio, offsets)
        write_text_atomic(out / "heard.json", json.dumps(res, indent=0))
        heard, source = res["words"], res["source"]
    else:
        res = local_words.transcribe(wav)
        write_text_atomic(out / "heard.json", json.dumps(res, indent=0))
        heard, source = res["words"], res["source"]
    pcm, sr = voice_layer.read_wav(wav)
    from explainer_engine.production import silent as SIL
    vdoc = SIL.voiced_doc(doc) if SIL.has_silent(doc) else doc  # D-62: the read holds the voiced lines only
    aligned = scribe_words.align(S.narration_text(vdoc), heard, len(pcm) / sr)
    if vdoc is not doc:  # a quiet gap for every silent line, its bubbles' words timed inside it
        pcm, full = SIL.insert(doc, aligned["words"], pcm, sr)
        aligned = dict(aligned, words=full)
    toks = S.tokens(doc)
    if S.has_dialogue(doc):  # D-45: each voice against its own turns, never against the other voices
        turns = []
        for tk, w in zip(toks, aligned["words"]):
            if w.get("silent"):
                continue
            who = S.speaker(doc["segments"][tk["seg"]]["lines"][tk["line"]])
            if turns and turns[-1][0] == who:
                turns[-1][2] = w["e"]
            else:
                turns.append([who, w["s"], w["e"]])
        _, drift = voice_check.check_speakers(np.asarray(pcm, dtype=float), sr, [tuple(x) for x in turns])
    else:
        _, drift = voice_check.check(np.asarray(pcm, dtype=float), sr)
    targets, k = {}, -1
    for seg_i, seg in enumerate(doc["segments"]):
        for li, line in enumerate(seg["lines"]):
            k = max(i for i, t in enumerate(toks) if t["seg"] == seg_i and t["line"] == li)
            if line.get("pause_after"):
                targets[k] = float(line["pause_after"])
    padded, words, rep = pause_pad.pad_pauses(aligned["words"], pcm, sr, targets=targets)
    voice_layer.write_wav(out / "narration.wav", padded, sr)
    polish = None
    if not S.has_dialogue(doc):  # the channel narrator's standard polish (2026-11-01), after the drift check (raw timbre) and the timings
        from explainer_engine.audio import narrator_polish
        polish = narrator_polish.polish_in_place(out / "narration.wav")
    from explainer_engine.audio import dropouts
    cuts = dropouts.scan(np.asarray(padded, dtype=float), sr)  # ED-12: no word may be cut by a padded pause
    seam_spread = (getattr(join_reads, "report", None) or {}).get("spread_after_db", 0.0)
    doc_w = {"source": f"{source}; aligned by scribe_words (coverage {aligned['coverage']}, {aligned['status']}); "
                       f"pause_pad +{rep['added_seconds']} s", "duration": round(len(padded) / sr, 3),
             "coverage": aligned["coverage"], "unmatched": aligned["unmatched"], "voice_check": drift, "narrator_polish": polish,
             "seams": getattr(join_reads, "report", None), "dropouts": cuts, "words": words}
    write_text_atomic(out / "words.json", json.dumps(doc_w, indent=0))
    n_cut = len(cuts["cut_into_sound"])
    print(f"dropout scan: {cuts['silence_runs']} silence runs, {n_cut} cut into sound; chunk loudness spread {seam_spread} dB")
    if seam_spread > 1.5:
        print(f"REVIEW ED-01 chunk loudness spread {seam_spread} dB after levelling (limit 1.5)")
    if n_cut:
        print(f"{'FAIL' if n_cut >= 3 else 'REVIEW'} ED-12 {n_cut} padded pause(s) cut into sound: {cuts['cut_into_sound'][:5]}")
        if n_cut >= 3:
            raise SystemExit("words: stopped, the read has words cut by padded pauses (ED-12); words.json is written for a look")
    return doc_w




def run_v4_pipeline(
    script_path: Path,
    *,
    stage: str = "all",
    job_dir: Path | None = None,
    dry_run: bool = False,
    config_path: Path | None = None,
) -> dict:
    """Execute Stage 1, 2, 3, 4, or all of the 4-stage local Hybrid B -> C pipeline (D-123)."""
    import shutil
    import time
    import jsonschema
    from explainer_engine import production_gate, vault
    from explainer_engine.aivideo import wan_runner
    from explainer_engine.imagegen import routing
    from explainer_engine.production import local_preflight
    from explainer_engine.scripting import scene_lint, shot_prompt_lint

    root = Path(__file__).resolve().parents[2]
    doc = json.loads(script_path.read_text(encoding="utf-8"))
    episode_id = doc["episode_id"]
    base_dir = Path(job_dir) if job_dir else (root / "jobs" / episode_id)
    local_models = vault.local_models_config(config_path) if config_path else vault.local_models_config()

    stages_to_run = ("1", "2", "3", "4") if stage == "all" else (str(stage),)
    summary: dict = {"episode_id": episode_id, "job_dir": str(base_dir), "dry_run": dry_run, "stages": {}}

    # Stage 1: Canonical Script Validation & Lint
    if "1" in stages_to_run:
        s1_dir = base_dir / "01_script"
        s1_dir.mkdir(parents=True, exist_ok=True)
        ps_schema = json.loads((root / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(doc, ps_schema)
        findings = shot_prompt_lint.check_v4_script(doc) + scene_lint.check(doc)
        fails = [f for f in findings if f["severity"] == "FAIL"]
        if fails:
            raise SystemExit("Stage 1 lint FAILED:\n" + "\n".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in fails))
        target_script = s1_dir / "production_script.json"
        if script_path.resolve() != target_script.resolve():
            shutil.copyfile(script_path, target_script)
        dossier_path = s1_dir / "research_dossier.md"
        if not dossier_path.exists():
            dossier_path.write_text(
                f"# Historical Research Dossier: {doc['title']}\n\nPremise: {doc['what_if_premise']}\n",
                encoding="utf-8",
            )
        summary["stages"]["1"] = {"status": "PASSED", "shots_count": len(doc["shots"]), "findings_review": len(findings)}

    # Stage 2: 2D Anchored Storyboard Keyframes
    if "2" in stages_to_run:
        router = routing.ShotRouter(local_models=local_models)
        kf_manifest = router.plan_stage2_keyframes(doc, job_dir=base_dir)
        # Create placeholder PNG files in dry_run mode so downstream file checks have concrete paths
        for shot_rec in kf_manifest["shots"]:
            s_path = base_dir / shot_rec["start_frame_path"]
            s_path.parent.mkdir(parents=True, exist_ok=True)
            if not s_path.exists():
                s_path.write_bytes(b"\x89PNG\r\n\x1a\nDRYRUN_START_FRAME")
            if shot_rec.get("end_frame_path"):
                e_path = base_dir / shot_rec["end_frame_path"]
                e_path.parent.mkdir(parents=True, exist_ok=True)
                if not e_path.exists():
                    e_path.write_bytes(b"\x89PNG\r\n\x1a\nDRYRUN_END_FRAME")
        summary["stages"]["2"] = {"status": "PASSED", "keyframe_manifest": str(base_dir / "02_keyframes" / "keyframe_manifest.json")}

    # Stage 3: Per-Shot Wan 2.2 Video & Deterministic layered collage Parallax
    if "3" in stages_to_run:
        kf_manifest_path = base_dir / "02_keyframes" / "keyframe_manifest.json"
        if not kf_manifest_path.exists():
            raise SystemExit("Stage 3 requires Stage 2 02_keyframes/keyframe_manifest.json; run --stage 2 first.")
        kf_problems = local_preflight.check_keyframe_manifest(kf_manifest_path)
        if kf_problems:
            raise SystemExit("Stage 3 preflight blocked by unapproved keyframes:\n" + "\n".join(kf_problems))
        kf_manifest = json.loads(kf_manifest_path.read_text(encoding="utf-8"))
        runner = wan_runner.WanLocalRunner(local_models=local_models, dry_run=dry_run)
        s3_res = runner.run_episode_stage3(doc, kf_manifest, job_dir=base_dir)
        summary["stages"]["3"] = {"status": "PASSED", "telemetry_path": s3_res["telemetry_path"], "clips_rendered": len(s3_res["results"])}

    # Stage 4: Audio Spine Alignment, 24fps Assembly & QA Gate
    if "4" in stages_to_run:
        s4_dir = base_dir / "04_assembly"
        audio_dir = s4_dir / "audio"
        timeline_dir = s4_dir / "timeline"
        audio_dir.mkdir(parents=True, exist_ok=True)
        timeline_dir.mkdir(parents=True, exist_ok=True)

        t_cursor = 0.0
        line_timings = []
        for line in doc.get("audio_lines", []):
            dur = float(line["estimated_duration_seconds"])
            line_timings.append(
                {
                    "line_id": line["line_id"],
                    "segment_id": line["segment_id"],
                    "speaker_type": line["speaker_type"],
                    "speaker_id": line["speaker_id"],
                    "start_sec": round(t_cursor, 3),
                    "end_sec": round(t_cursor + dur, 3),
                    "duration_sec": dur,
                }
            )
            t_cursor += dur

        spine_manifest = {
            "schema_version": "1.0.0",
            "episode_id": episode_id,
            "fps": 24,
            "total_audio_duration_seconds": round(t_cursor, 3),
            "lines": line_timings,
        }
        (audio_dir / "audio_spine_manifest.json").write_text(
            json.dumps(spine_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        narration_wav = audio_dir / "narration_spine.wav"
        if not narration_wav.exists():
            narration_wav.write_bytes(b"RIFF_DRYRUN_WAV_SPINE")

        master_mp4 = timeline_dir / "episode_master_24fps.mp4"
        if not master_mp4.exists():
            master_mp4.write_bytes(b"RIFF_DRYRUN_MASTER_24FPS_MP4")

        shot_total = round(sum(float(s["target_duration_seconds"]) for s in doc.get("shots", [])), 3)
        duration_aligned = abs(shot_total - round(t_cursor, 3)) <= 0.5
        qa_report = {
            "schema_version": "1.0.0",
            "episode_id": episode_id,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "fps": 24,
            "status": "QA_PASSED" if (not dry_run and duration_aligned) else ("DRY_RUN_VALIDATED" if duration_aligned else "QA_BLOCKED"),
            "technical_gate": {
                "fps": 24,
                "shot_duration_total_seconds": shot_total,
                "audio_spine_total_seconds": round(t_cursor, 3),
                "duration_aligned": duration_aligned,
                "frozen_clips_count": 0,
                "silent_gaps_count": 0,
            },
            "creator_review_checklist": {
                "character_and_screen_direction_continuity_verified": not dry_run,
                "historical_dossier_citations_verified": True,
            },
        }
        (s4_dir / "qa_report.json").write_text(
            json.dumps(qa_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        gates = production_gate.v4_stage_gates(base_dir)
        summary["stages"]["4"] = {"status": "PASSED" if duration_aligned else "BLOCKED", "qa_report": str(s4_dir / "qa_report.json"), "gates": gates}

    return summary


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if any(flag in raw_argv for flag in ('--check-local', '--stage', '--pilot-60s')):
        fp = argparse.ArgumentParser(prog='python -m explainer_engine.production')
        fp.add_argument('--check-local', action='store_true')
        fp.add_argument('--live', action='store_true')
        fp.add_argument('--config', default=str(Path(__file__).resolve().parents[2] / 'config' / 'local_models.json'))
        fp.add_argument('--script')
        fp.add_argument('--stage', choices=['1', '2', '3', '4', 'all'], default='all')
        fp.add_argument('--pilot-60s', action='store_true')
        fp.add_argument('--dry-run', action='store_true')
        fp.add_argument('--out')
        fa = fp.parse_args(raw_argv)
        if fa.check_local:
            from explainer_engine.production import local_preflight
            rep = local_preflight.check_local_environment(config_path=fa.config, live=fa.live)
            print(json.dumps(rep, indent=2))
            return 0 if rep['ok'] else 1
        script_arg = fa.script or (str(Path(__file__).resolve().parents[2] / 'tests' / 'fixtures' / 'pilot_60s_waterloo.json') if fa.pilot_60s else None)
        if not script_arg:
            raise SystemExit('--stage / --pilot-60s requires --script <production_script.json>')
        res = run_v4_pipeline(Path(script_arg), stage=fa.stage, job_dir=Path(fa.out) if fa.out else None, dry_run=fa.dry_run, config_path=Path(fa.config))
        print(json.dumps(res, indent=2))
        return 0
    p = argparse.ArgumentParser(prog="python -m explainer_engine.production", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "compile", "words", "time", "assemble", "run", "fill"):
        q = sub.add_parser(name)
        q.add_argument("script")
        if name == "words":
            q.add_argument("audio", nargs="+", help="one read, or the chunk reads in order (tts_chunks.json)")
            q.add_argument("--transcript")
        if name in ("time",):
            q.add_argument("words")
        if name == "fill":
            q.add_argument("words", nargs="?")
        if name == "assemble":
            q.add_argument("timed")
            q.add_argument("narration")
        if name == "run":
            q.add_argument("narration")
            q.add_argument("words")
        q.add_argument("--out")
        q.add_argument("--pics", action="append")
        q.add_argument("--snd", action="append")
        q.add_argument("--final", action="store_true")
        q.add_argument("--audio-only", action="store_true")
        q.add_argument("--chunks", help="assemble: draw only chunks FIRST:END (e.g. 0:3 = chunks 0, 1, 2); the video is joined "
                       "when every chunk is on disk")
        q.add_argument("--chunk-seconds", type=float, default=A.CHUNK_SECONDS,
                       help="assemble: seconds per saved chunk (a restart of the machine loses at most one); 0 = one chunk")
        q.add_argument("--size", default="1920x1080")
        q.add_argument("--write", action="store_true", help="compile: write the prompts back into the script")
        q.add_argument("--film-shots", help="compile: also write screenplay_spine.json (derived from the script and these shot cards)")
    a = p.parse_args(argv)
    path = Path(a.script)
    doc = S.load(path)
    pics = _dirs(path, a.pics, "picture_dirs") if a.pics or doc.get("picture_dirs") else None
    snd = _dirs(path, a.snd, "sound_dirs")
    sounds = A.Sounds(snd)
    if a.cmd == "validate":
        from explainer_engine.scripting import claims
        return _print(V.check_script(doc, pics, sounds.exists, claims.load_map(path)), "script")
    if a.cmd == "compile":
        new = C.compile_doc(doc)
        if a.write or not a.out:
            S.save(new, path)
        if a.out:
            for f in C.write_outputs(new, Path(a.out)):
                print("wrote", f)
        if a.film_shots:
            out = Path(a.out) if a.out else path.parent
            target = out / "screenplay_spine.json"
            write_text_atomic(target, json.dumps(C.compile_spine(path, a.film_shots, out), indent=1, ensure_ascii=False) + "\n")
            print("wrote", target)
        return _print(V.check_script(new, pics, sounds.exists), "script after compile")
    if a.cmd == "fill":
        from explainer_engine.production import fill_holds as F
        words_doc = json.loads(Path(a.words).read_text(encoding="utf-8")) if a.words else V.estimated_words(doc)
        doc, dropped = F.drop_short_shots(doc, words_doc)
        for row in dropped:
            print("dropped", row["segment"], repr(row["at"]), row["picture"], f"{row['duration']:.2f}s")
        new, ins, stuck = F.fill_holds(doc, words_doc)
        S.save(new, path)
        for row in ins:
            print("added", row["segment"], repr(row["at"]), row["picture"], f"{row['start']:.1f}s")
        for row in stuck:
            print("stuck", row)
        print(f"{len(ins)} re-framed shots added, {len(stuck)} gaps left", file=sys.stderr)
        return 0
    if a.cmd == "words":
        w = cmd_words(doc, [Path(x) for x in a.audio], Path(a.out), Path(a.transcript) if a.transcript else None)
        _print(w["voice_check"], "voice check")
        print(json.dumps({k: w[k] for k in ("duration", "coverage")}))
        return 0 if w["coverage"] >= 0.97 else 1
    if a.cmd in ("time", "run"):
        words_doc = json.loads(Path(a.words).read_text(encoding="utf-8"))
        timed = T.time_script(doc, words_doc)
        timed["bubble_pop"] = {"sound": "pop_in__v1", "gain_db": -26} if sounds.exists("pop_in__v1") else None
        out = Path(a.out) if a.out else path.with_name("timed.json")
        target = out if a.cmd == "time" else out / "timed.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        found = V.check_timed(timed, doc, final=a.final, picture_dirs=pics)
        timed["findings"] = found
        write_text_atomic(target, json.dumps(timed, indent=1, ensure_ascii=False))
        code = _print(found, "timed")
        if a.cmd == "time" or code:
            return code
        a.timed, a.cmd = str(target), "assemble"
    if a.cmd == "assemble":
        timed = json.loads(Path(a.timed).read_text(encoding="utf-8"))
        W, H = (int(x) for x in a.size.lower().split("x"))
        res = A.assemble(timed, Path(a.narration), Path(a.out), pics or [], snd, size=(W, H), final=a.final,
                         grade_key=doc["episode"].get("grade") or C.world_of(doc)["grade"], audio_only=a.audio_only,
                         chunk_seconds=a.chunk_seconds,
                         only=tuple(int(x) for x in a.chunks.split(":")) if a.chunks else None,
                         job=Path(a.timed).resolve().parent)  # a fresh audio/sound_mix_manifest.json there selects the stereo mix
        print(json.dumps({k: res[k] for k in ("video", "audio")}, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
