
"""RETIRED by D-80 (2026-10-26): the night-run route of the wldnk era; kept as history, never run. Checks and plans for an AI-video test (shots.json + timeline.json), shared by the pod scripts and the montage.

shots.json: {"title", "trigger", "style_suffix", "characters": {id: description}, "plates": {id: description},
             "shots": [{"id", "chars": [ids], "plate": id|null, "first", "last", "motion"}]}
timeline.json: {"intro_end", "end", "segments": [{"id", "t0", "t1"}]}  (seconds on the narration's clock)

No permanent heroes (the creator, 2026-10-22): characters belong to one video's shots.json, never to a LoRA."""
import math

MAX_REFS = 3          # reference sheets per keyframe (klein multi-reference; the plate makes the fourth)
TOL = 0.02            # seconds of slack between neighbouring timeline segments


def check_shots(data):
    """Problems in a shots.json (empty list = usable)."""
    bad = []
    trig = (data.get("trigger") or "").strip()
    if not trig:
        bad.append("no trigger word: the style LoRA would not be called")
    chars, plates = data.get("characters") or {}, data.get("plates") or {}
    seen = set()
    for s in data.get("shots") or []:
        sid = s.get("id")
        if not sid or sid in seen:
            bad.append(f"shot id missing or repeated: {sid!r}")
        seen.add(sid)
        for k in ("first", "last", "motion"):
            if not (s.get(k) or "").strip():
                bad.append(f"{sid}: empty {k} prompt")
        for c in s.get("chars") or []:
            if c not in chars:
                bad.append(f"{sid}: unknown character {c!r}")
        if s.get("plate") is not None and s["plate"] not in plates:
            bad.append(f"{sid}: unknown plate {s['plate']!r}")
    if not seen:
        bad.append("no shots")
    return bad


def check_timeline(tl, data):
    """Problems in a timeline against its shots: contiguous segments from the opening to the end, one shot each."""
    bad = []
    segs = tl.get("segments") or []
    if not segs:
        return ["no segments"]
    ids = {s.get("id") for s in data.get("shots") or []}
    t = tl.get("intro_end", 0.0)
    for g in segs:
        if g["id"] not in ids:
            bad.append(f"{g['id']}: no shot for this segment")
        if abs(g["t0"] - t) > TOL:
            bad.append(f"{g['id']}: starts at {g['t0']} but the previous part ends at {t}")
        if g["t1"] <= g["t0"]:
            bad.append(f"{g['id']}: empty or negative length")
        t = g["t1"]
    if abs(t - tl.get("end", t)) > TOL:
        bad.append(f"segments end at {t} but the narration ends at {tl.get('end')}")
    return bad


def keyframe_refs(shot, sheets):
    """Reference images for a shot's first keyframe: up to MAX_REFS character sheets, then the plate's picture."""
    refs = [sheets[c] for c in shot.get("chars") or [] if c in sheets][:MAX_REFS]
    if shot.get("plate") and shot["plate"] in sheets:
        refs.append(sheets[shot["plate"]])
    return refs


def prompt(data, text):
    """A keyframe prompt: trigger first (as the LoRA was captioned), then the shot, then the house style."""
    return ", ".join(p for p in (data.get("trigger"), text, data.get("style_suffix")) if p)


def montage_plan(tl, clip_seconds, have_first):
    """What fills each segment. clip_seconds: {id: length of its clip} (missing = no clip); have_first: ids with a
    first keyframe. A segment longer than its clip holds the first keyframe first (the clip starts on that frame)."""
    plan = []
    for g in tl["segments"]:
        sid, d = g["id"], round(g["t1"] - g["t0"], 3)
        L = clip_seconds.get(sid)
        if L:
            hold = round(d - L, 3) if d > L + 0.05 and sid in have_first else 0.0
            plan.append({"id": sid, "seconds": d, "how": "hold+clip" if hold else "clip", "hold": hold})
        elif sid in have_first:
            plan.append({"id": sid, "seconds": d, "how": "still", "hold": d})
        else:
            plan.append({"id": sid, "seconds": d, "how": "MISSING", "hold": 0.0})
    return plan


def affordable_minutes(max_usd, price_per_hour):
    """Minutes a pod may run before its money ceiling stops it."""
    return math.floor(max_usd / price_per_hour * 60) if price_per_hour > 0 else 0


def schedule_fits(stage_ends_min, max_usd, price_per_hour, upload_margin_min=10):
    """True when every stage deadline (minutes after the pod starts) lands before the money ceiling, with time to upload."""
    limit = affordable_minutes(max_usd, price_per_hour) - upload_margin_min
    return all(m <= limit for m in stage_ends_min)


# --- Active Stage 3 Local Wan 2.2 & DepthFlow layered collage Job Planner (D-123, 2026-11-09) ---

import hashlib
import json
from pathlib import Path
from typing import Mapping
import jsonschema
from explainer_engine import vault

ROOT = Path(__file__).resolve().parents[2]
WAN_JOB_SCHEMA_PATH = ROOT / "explainer_engine" / "schemas" / "wan_job.schema.json"

WORKFLOW_BY_MODE = {
    "WAN_I2V": "workflows/comfyui/wan22_fun_inp_flf2v.json",
    "WAN_FLF2V": "workflows/comfyui/wan22_fun_inp_flf2v.json",
    "WAN_CONTROL": "workflows/comfyui/wan22_fun_control.json",
    "COLLAGE_STILL": "workflows/comfyui/depthflow_25d_motion.json",
    "TACTILE_MAP": "workflows/comfyui/depthflow_25d_motion.json",
    "STILL_25D": "workflows/comfyui/depthflow_25d_motion.json",
    "MAP_25D": "workflows/comfyui/depthflow_25d_motion.json",
}


def _wan_schema() -> dict:
    return json.loads(WAN_JOB_SCHEMA_PATH.read_text(encoding="utf-8"))


def _shot_seed(episode_id: str, shot_id: str) -> int:
    digest = hashlib.sha256(f"{episode_id}:{shot_id}:wan".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_000_000_000


def build_wan_payload(
    shot: dict,
    *,
    episode_id: str,
    keyframe_record: dict | None = None,
    env: Mapping[str, str] | None = None,
    local_models: dict | None = None,
    model_tier_override: str | None = None,
    use_lightx2v_4step: bool = False,
    width: int = 1280,
    height: int = 720,
    num_frames: int = 81,
    steps: int | None = None,
    cfg_scale: float = 5.0,
    seed: int | None = None,
) -> dict:
    """Build and schema-validate a local Stage 3 Wan 2.2 / DepthFlow job payload (wan_job.schema.json)."""
    cfg = local_models or vault.local_models_config()
    defaults = cfg.get("active_defaults", {})
    comfy_url = vault.get_comfyui_url(env)

    sid = shot["shot_id"]
    mode = shot["generation_mode"]
    if mode not in WORKFLOW_BY_MODE:
        raise ValueError(f"{sid}: unsupported Stage 3 generation_mode {mode!r}")

    if model_tier_override:
        tier = model_tier_override
    elif mode in ("WAN_I2V", "WAN_FLF2V"):
        tier = defaults.get("stage3_video_inp_model", "wan22_fun_5b_inp")
    elif mode == "WAN_CONTROL":
        tier = defaults.get("stage3_video_control_model", "wan22_fun_5b_control")
    else:
        tier = defaults.get("stage3_parallax_engine", "depthflow_local_25d")

    start_path = (
        keyframe_record["start_frame_path"]
        if keyframe_record and keyframe_record.get("start_frame_path")
        else f"02_keyframes/shots/{sid}_start.png"
    )
    end_path = None
    if mode == "WAN_FLF2V":
        end_path = (
            keyframe_record["end_frame_path"]
            if keyframe_record and keyframe_record.get("end_frame_path")
            else f"02_keyframes/shots/{sid}_end.png"
        )

    ctrl_input = None
    if mode == "WAN_CONTROL":
        sc = shot.get("selective_control")
        if not isinstance(sc, dict):
            raise ValueError(f"{sid}: WAN_CONTROL requires selective_control object")
        ctrl_input = {
            "modality": sc["control_modality"],
            "control_file_path": sc["control_source_path"],
            "strength": float(sc.get("control_strength", 0.75)),
        }

    resolved_steps = int(steps) if steps is not None else (4 if use_lightx2v_4step else 20)
    resolved_seed = int(seed) if seed is not None else _shot_seed(episode_id, sid)

    job = {
        "job_id": f"wan_{episode_id}_{sid}",
        "episode_id": episode_id,
        "shot_id": sid,
        "generation_mode": mode,
        "model_tier": tier,
        "workflow_template_path": WORKFLOW_BY_MODE[mode],
        "comfy_local_url": comfy_url,
        "start_image_path": start_path,
        "end_image_path": end_path,
        "single_control_input": ctrl_input,
        "use_lightx2v_4step": bool(use_lightx2v_4step),
        "motion_prompt": shot["video_prompt"]["motion_prompt"],
        "negative_prompt": shot["image_prompt"]["negative_prompt"],
        "width": int(width),
        "height": int(height),
        "num_frames": int(num_frames),
        "fps": 24,
        "steps": resolved_steps,
        "cfg_scale": float(cfg_scale),
        "seed": resolved_seed,
    }
    jsonschema.validate(job, _wan_schema())
    return job


def escalate_job_to_control(
    job: dict,
    *,
    modality: str = "openpose",
    control_file_path: str | None = None,
    strength: float = 0.75,
    local_models: dict | None = None,
) -> dict:
    """Escalate a failing WAN_I2V / WAN_FLF2V job to selective secondary WAN_CONTROL with a single control modality."""
    cfg = local_models or vault.local_models_config()
    ctrl_tier = cfg.get("active_defaults", {}).get("stage3_video_control_model", "wan22_fun_5b_control")
    sid = job["shot_id"]
    escalated = dict(job)
    escalated["generation_mode"] = "WAN_CONTROL"
    escalated["model_tier"] = ctrl_tier
    escalated["workflow_template_path"] = WORKFLOW_BY_MODE["WAN_CONTROL"]
    escalated["end_image_path"] = None
    escalated["single_control_input"] = {
        "modality": modality,
        "control_file_path": control_file_path or f"02_keyframes/shots/{sid}_{modality}.png",
        "strength": float(strength),
    }
    jsonschema.validate(escalated, _wan_schema())
    return escalated


def plan_episode_wan_jobs(
    script_doc: dict,
    keyframe_manifest: dict | None = None,
    *,
    env: Mapping[str, str] | None = None,
    local_models: dict | None = None,
) -> list[dict]:
    """Build validated Stage 3 wan_job payloads for all shots in a v4.0 production_script.json."""
    episode_id = script_doc["episode_id"]
    kf_by_shot = {s["shot_id"]: s for s in (keyframe_manifest or {}).get("shots", [])}
    return [
        build_wan_payload(
            shot,
            episode_id=episode_id,
            keyframe_record=kf_by_shot.get(shot["shot_id"]),
            env=env,
            local_models=local_models,
        )
        for shot in script_doc.get("shots", [])
    ]
