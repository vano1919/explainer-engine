"""The acceptance report of an episode run (v4.3 plan P2, EP-03): each gate is a measurement on what the run made, or NOT_RUN.

Replaces the archive's AC-01..AC-10 of ``production_runner`` (four of them were the literal ``True``, one compared a constant
with itself, two were fixed to the 2-minute pilot: exactly 3 maps, 115-125 s; plan F2, F3). The numbers now come from the
episode's own script: the map count from its map shots, the duration from its shots' target seconds (or the timed spine).
"""
from __future__ import annotations

import re
from pathlib import Path

from explainer_engine.episode.validate import check_episode_ids
from explainer_engine.qa.gates import row, verdict

DURATION_TOL = 0.02          # the master may differ from the script's planned length by 2 % (frame rounding, J/L cuts)


def _inside(path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _map_shot(s: dict) -> bool:
    return s.get("route") == "map_action" or s.get("visual_type") == "map_visualization" \
        or s.get("generation_mode") in ("MAP_25D", "TACTILE_MAP")


def gates(*, root: Path, script: dict, shot_records: list[dict], transition_plans: list[dict] | None,
          audio: dict | None, stem_audit: dict | None, video: dict | None, fps: int,
          forbidden_tokens=(), narration_source: str | None = None, paid_calls: int | None = None) -> dict:
    root = Path(root)
    rows = []

    ids = check_episode_ids(root)
    rows.append(row("isolation_one_episode_id", not ids, f"{len(ids)} EP-01 finding(s)", [r["where"] for r in ids]))

    used = [p for r in shot_records for p in (r.get("source_start_keyframe"), r.get("source_end_keyframe"), r.get("clip_path")) if p]
    outside = [p for p in used if not _inside(p, root)]
    rows.append(row("assets_inside_the_episode", (not outside) if used else None,
                    f"{len(used)} file(s) used, {len(outside)} outside the episode folder" if used else "no shot file was recorded",
                    outside))

    if forbidden_tokens:
        pat = re.compile(r"\b(" + "|".join(re.escape(t) for t in forbidden_tokens) + r")\b", re.I)
        hits = []
        for s in script.get("shots", []):
            text = " ".join(str(s.get(k) or "") for k in ("image_prompt", "narrative_purpose", "action_start_state", "action_end_state"))
            hits += [f"{s.get('shot_id')}:{m.group(0)}" for m in pat.finditer(text)]
        rows.append(row("no_foreign_era_words_in_prompts", not hits, f"{len(hits)} forbidden word(s) in the shots' prompts", hits[:20]))
    else:
        rows.append(row("no_foreign_era_words_in_prompts", None, "the episode lists no forbidden era words"))

    if audio is None:
        rows.append(row("audio_era_gating", None, "no sound was rendered"))
    else:
        blocked = list(audio.get("blocked_era_events") or [])
        rows.append(row("audio_era_gating", not blocked, f"{len(blocked)} era-foreign sound event(s) blocked in the plan", blocked[:20]))

    if narration_source is None:
        rows.append(row("narration_is_a_real_read", None, "no narration in this run"))
    else:
        real = narration_source not in ("synthesized", "placeholder") and Path(narration_source).is_file()
        rows.append(row("narration_is_a_real_read", real,
                        "the narration is a read file" if real else
                        f"the narration is {narration_source!r}: a placeholder, never shippable (plan F4, P7)", narration_source))

    if stem_audit is None:
        rows.append(row("narration_has_no_dropouts", None, "no stem audit"))
    else:
        n_drop = int(stem_audit.get("mid_line_narration_dropouts", 0))
        n_sd = len(stem_audit.get("sound_director_stem_findings") or [])
        rows.append(row("narration_has_no_dropouts", n_drop == 0 and n_sd == 0,
                        f"{n_drop} mid-line dropout(s), {n_sd} sound-director finding(s)", {"dropouts": n_drop, "findings": n_sd}))

    want_maps = sorted(s["shot_id"] for s in script.get("shots", []) if _map_shot(s))
    made_maps = sorted(r["shot_id"] for r in shot_records if r.get("visual_type") == "map_visualization"
                       and r.get("clip_path") and Path(r["clip_path"]).is_file())
    if not shot_records:
        rows.append(row("every_map_shot_rendered", None, "no shot was rendered"))
    else:
        missing = sorted(set(want_maps) - set(made_maps))
        rows.append(row("every_map_shot_rendered", not missing, f"{len(made_maps)} of {len(want_maps)} map shot(s) of the script rendered",
                        missing))

    rows.append(row("camera_motion_measured", None, "no motion measurement on the clips yet (P5 adds it)"))

    if transition_plans is None:
        rows.append(row("transitions_ed04", None, "no transition plan"))
    else:
        bad = [p.get("from_shot_id") or p.get("shot_id") for p in transition_plans if not p.get("ed04_compliant")]
        rows.append(row("transitions_ed04", not bad, f"{len(bad)} of {len(transition_plans)} cut(s) break ED-04", bad[:20]))

    planned = round(sum(float(s.get("target_duration_seconds") or 0.0) for s in script.get("shots", [])), 3)
    if video is None or not video.get("duration_sec"):
        rows.append(row("master_length_matches_the_script", None, "no master video"))
    else:
        dur = float(video["duration_sec"])
        frames_ok = int(video.get("total_frames", -1)) == int(round(dur * fps))
        ok = planned > 0 and abs(dur - planned) <= DURATION_TOL * planned and frames_ok
        rows.append(row("master_length_matches_the_script", ok,
                        f"master {dur:.2f} s vs script {planned:.2f} s (tolerance {DURATION_TOL:.0%}), frames {'match' if frames_ok else 'differ'}",
                        {"master_s": dur, "script_s": planned, "frames": video.get("total_frames")}))

    if paid_calls is None:
        rows.append(row("no_paid_call", None, "this run does not read the ledger yet (P8)"))
    else:
        rows.append(row("no_paid_call", paid_calls == 0, f"{paid_calls} paid call(s) in the ledger for this run", paid_calls))
    return verdict(rows)
