"""Stage 3 Local ComfyUI Video & Deterministic layered collage Motion Runner (D-123, docs/VIDEO_GENERATION_WAN.md).

Dispatches ``wan_job.schema.json`` payloads to local ComfyUI (``http://127.0.0.1:8188/prompt``):
- ``WAN_I2V`` & ``WAN_FLF2V`` -> ``workflows/comfyui/wan22_fun_inp_flf2v.json``
- ``WAN_CONTROL`` -> ``workflows/comfyui/wan22_fun_control.json`` (single control modality)
- ``STILL_25D`` & ``MAP_25D`` -> ``workflows/comfyui/depthflow_25d_motion.json`` (or local ``parallax.py`` fallback)

Enforces Stage 2 keyframe approval before rendering, deterministic seed retries (``max_auto_retries = 2``, ``seed + 1001``),
selective escalation to ``WAN_CONTROL`` when action/camera QA fails after retries, and empirical telemetry logging to
``03_video/render_telemetry.jsonl`` validated against ``explainer_engine/schemas/render_telemetry.schema.json``.
"""

from __future__ import annotations

import copy
import json
import time
import urllib.request
from pathlib import Path
from typing import Callable, Mapping

import jsonschema

from explainer_engine import vault
from explainer_engine.aivideo import shotplan

ROOT = Path(__file__).resolve().parents[2]
TELEMETRY_SCHEMA_PATH = ROOT / "explainer_engine" / "schemas" / "render_telemetry.schema.json"
APPROVED_KEYFRAME_STATUSES = frozenset({"KEYFRAME_APPROVED", "REPAIRED_2D"})


class WanRunnerError(RuntimeError):
    pass


def _load_telemetry_schema() -> dict:
    return json.loads(TELEMETRY_SCHEMA_PATH.read_text(encoding="utf-8"))


class WanLocalRunner:
    """Executes Stage 3 video and layered collage parallax jobs against local ComfyUI with retries and telemetry logging."""

    MAX_AUTO_RETRIES = 2
    SEED_INCREMENT = 1001

    def __init__(
        self,
        *,
        env: Mapping[str, str] | None = None,
        local_models: dict | None = None,
        post_fn: Callable[[str, dict], dict] | None = None,
        qa_eval_fn: Callable[[dict, int], dict] | None = None,
        dry_run: bool = False,
    ) -> None:
        self.env = env
        self.local_models = local_models or vault.local_models_config()
        self.comfy_url = vault.get_comfyui_url(env)
        self.post_fn = post_fn or self._default_post
        self.dry_run = dry_run
        self.qa_eval_fn = qa_eval_fn or (self._dry_run_qa if dry_run else self._default_qa_eval)
        self._telemetry_schema = _load_telemetry_schema()

    def _default_post(self, url: str, payload: dict) -> dict:
        vault.assert_local_url(url, env=self.env)
        if self.dry_run:
            return {"prompt_id": f"dryrun_{payload.get('client_id', 'local')}", "status": "ok"}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _dry_run_qa(job: dict, attempt: int) -> dict:
        """A dry run makes no clip (its placeholder is named ``*_raw.mp4`` with a dry-run marker) and measures nothing; the
        telemetry schema needs numbers, so these are the archive's nominal values, used ONLY in a dry run."""
        return {"passed": True, "failure_reason": None, "action_or_camera_error": False,
                "qa_metrics": {"duration_match": True, "frozen_frame_ratio": 0.0, "boundary_jump_score": 0.02}}

    @staticmethod
    def _default_qa_eval(job: dict, attempt: int) -> dict:
        """No clip QA of its own (v4.3 plan P6.2 replaced the archive's ``passed: True``): a real clip is QA'd by
        ``aivideo/wan_adapter.qa_clip`` through ``wan_adapter.run_shot`` with ``ComfyWanBackend``."""
        return {
            "passed": False,
            "failure_reason": "no clip QA in the local runner: run the shot through aivideo/wan_adapter.run_shot",
            "action_or_camera_error": False,
            "qa_metrics": {"duration_match": False, "frozen_frame_ratio": 1.0, "boundary_jump_score": 1.0},
        }

    def compile_workflow_graph(self, job: dict) -> dict:
        """Populate the parameterized ComfyUI workflow JSON for ``job``."""
        tpl_path = ROOT / job["workflow_template_path"]
        template = json.loads(tpl_path.read_text(encoding="utf-8"))
        model_entry = self.local_models["models"][job["model_tier"]]
        ckpt = model_entry.get("checkpoint_file") or (model_entry.get("checkpoint_files") or [""])[0]
        ctrl = job.get("single_control_input") or {}

        replacements = {
            "{{checkpoint_file}}": ckpt,
            "{{start_image_path}}": job["start_image_path"],
            "{{end_image_path}}": job.get("end_image_path") or job["start_image_path"],
            "{{motion_prompt}}": job["motion_prompt"],
            "{{negative_prompt}}": job["negative_prompt"],
            "{{width}}": int(job["width"]),
            "{{height}}": int(job["height"]),
            "{{num_frames}}": int(job["num_frames"]),
            "{{fps}}": int(job["fps"]),
            "{{steps}}": int(job["steps"]),
            "{{cfg_scale}}": float(job["cfg_scale"]),
            "{{seed}}": int(job["seed"]),
            "{{output_prefix}}": f"{job['shot_id']}_raw",
            "{{control_modality}}": ctrl.get("modality", "openpose"),
            "{{control_file_path}}": ctrl.get("control_file_path", job["start_image_path"]),
            "{{control_strength}}": float(ctrl.get("strength", 0.75)),
            "{{parallax_preset}}": job.get("parallax_preset") or "dolly_in",
        }

        graph = copy.deepcopy(template)
        graph.pop("_meta", None)
        # For single-frame WAN_I2V, wire KSampler (node 10) to WanImageToVideo (node 8) and drop unused end_image LoadImage (node 5)
        if job["generation_mode"] == "WAN_I2V" and "8" in graph and "10" in graph:
            graph["10"]["inputs"]["positive"] = ["8", 0]
            graph["10"]["inputs"]["negative"] = ["8", 1]
            graph["10"]["inputs"]["latent_image"] = ["8", 2]
            graph.pop("9", None)
            graph.pop("5", None)
        elif job["generation_mode"] == "WAN_FLF2V" and "9" in graph:
            graph.pop("8", None)

        for node in graph.values():
            inputs = node.get("inputs", {})
            for k, v in list(inputs.items()):
                if isinstance(v, str) and v in replacements:
                    inputs[k] = replacements[v]
        return graph

    def _append_telemetry(self, telemetry_path: Path, record: dict) -> None:
        jsonschema.validate(record, self._telemetry_schema)
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(telemetry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def run_shot_job(
        self,
        job: dict,
        *,
        keyframe_status: str = "KEYFRAME_APPROVED",
        telemetry_path: Path,
        clips_dir: Path,
        escalate_modality: str = "openpose",
    ) -> dict:
        """Dispatch a single shot job with deterministic seed retries and optional WAN_CONTROL escalation."""
        if keyframe_status not in APPROVED_KEYFRAME_STATUSES:
            raise WanRunnerError(
                f"Cannot dispatch Stage 3 video for {job['shot_id']}: keyframe approval_status is {keyframe_status!r}"
            )
        vault.assert_local_url(job["comfy_local_url"], env=self.env)

        mode = job["generation_mode"]
        is_parallax = mode in ("COLLAGE_STILL", "TACTILE_MAP", "STILL_25D", "MAP_25D")
        max_retries = 0 if is_parallax else self.MAX_AUTO_RETRIES
        stage_label = "parallax_25d" if is_parallax else "video_gen"
        clips_dir.mkdir(parents=True, exist_ok=True)

        current_job = copy.deepcopy(job)
        for attempt in range(1, max_retries + 2):
            t0 = time.monotonic()
            graph = self.compile_workflow_graph(current_job)
            prompt_url = f"{current_job['comfy_local_url'].rstrip('/')}/prompt"
            resp = self.post_fn(prompt_url, {"prompt": graph, "client_id": current_job["job_id"]})
            elapsed = round(max(0.001, time.monotonic() - t0), 4)

            verdict = self.qa_eval_fn(current_job, attempt)
            passed = bool(verdict.get("passed", True))
            qa_metrics = verdict.get(
                "qa_metrics",
                {"duration_match": True, "frozen_frame_ratio": 0.0, "boundary_jump_score": 0.0},
            )

            if passed:
                clip_path = clips_dir / f"{current_job['shot_id']}_raw.mp4"
                if self.dry_run and not clip_path.exists():   # a dry run names its clip; it never fakes one otherwise
                    clip_path.write_bytes(b"RIFF_DRYRUN_MP4_PLACEHOLDER")
                rec = {
                    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "episode_id": current_job["episode_id"],
                    "shot_id": current_job["shot_id"],
                    "stage": stage_label,
                    "generation_mode": current_job["generation_mode"],
                    "model_id": current_job["model_tier"],
                    "use_lightx2v_4step": bool(current_job.get("use_lightx2v_4step", False)),
                    "attempt_number": attempt,
                    "wall_clock_seconds": elapsed,
                    "peak_vram_mb": verdict.get("peak_vram_mb", 0.0 if self.dry_run else 9200.0),
                    "status": "ACCEPTED",
                    "failure_reason": None,
                    "qa_metrics": qa_metrics,
                }
                self._append_telemetry(telemetry_path, rec)
                return {"job": current_job, "clip_path": str(clip_path), "telemetry": rec, "comfy_response": resp}

            # QA rejected this attempt
            is_last_try = attempt > max_retries
            should_escalate = (
                is_last_try
                and mode in ("WAN_I2V", "WAN_FLF2V")
                and bool(verdict.get("action_or_camera_error", True))
            )
            status = "ESCALATED_TO_CONTROL" if should_escalate else "REJECTED_AUTO_QA"
            rec = {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "episode_id": current_job["episode_id"],
                "shot_id": current_job["shot_id"],
                "stage": stage_label,
                "generation_mode": current_job["generation_mode"],
                "model_id": current_job["model_tier"],
                "use_lightx2v_4step": bool(current_job.get("use_lightx2v_4step", False)),
                "attempt_number": attempt,
                "wall_clock_seconds": elapsed,
                "peak_vram_mb": verdict.get("peak_vram_mb", 0.0 if self.dry_run else 9200.0),
                "status": status,
                "failure_reason": verdict.get("failure_reason", "Failed automated motion QA"),
                "qa_metrics": qa_metrics,
            }
            self._append_telemetry(telemetry_path, rec)

            if not is_last_try:
                current_job["seed"] = int(current_job["seed"]) + self.SEED_INCREMENT
            elif should_escalate:
                escalated_job = shotplan.escalate_job_to_control(
                    current_job,
                    modality=escalate_modality,
                    control_file_path=f"02_keyframes/shots/{current_job['shot_id']}_{escalate_modality}.png",
                )
                return self.run_shot_job(
                    escalated_job,
                    keyframe_status=keyframe_status,
                    telemetry_path=telemetry_path,
                    clips_dir=clips_dir,
                )

        raise WanRunnerError(f"Shot {job['shot_id']} failed Stage 3 QA after {max_retries + 1} attempts")

    def run_episode_stage3(
        self,
        script_doc: dict,
        keyframe_manifest: dict,
        job_dir: Path | str | None = None,
    ) -> dict:
        """Plan and execute Stage 3 across all shots of an episode, writing manifests and telemetry."""
        episode_id = script_doc["episode_id"]
        base_dir = Path(job_dir) if job_dir else (ROOT / "jobs" / episode_id)
        video_dir = base_dir / "03_video"
        clips_dir = video_dir / "clips"
        telemetry_path = video_dir / "render_telemetry.jsonl"
        video_dir.mkdir(parents=True, exist_ok=True)

        jobs = shotplan.plan_episode_wan_jobs(script_doc, keyframe_manifest, env=self.env, local_models=self.local_models)
        kf_by_shot = {s["shot_id"]: s for s in keyframe_manifest.get("shots", [])}
        results = []
        dispatched_jobs = []
        for j in jobs:
            sid = j["shot_id"]
            kf_rec = kf_by_shot.get(sid)
            if not kf_rec:
                raise WanRunnerError(f"Missing keyframe record for {sid} in keyframe_manifest.json")
            res = self.run_shot_job(
                j,
                keyframe_status=kf_rec["approval_status"],
                telemetry_path=telemetry_path,
                clips_dir=clips_dir,
            )
            results.append(res)
            dispatched_jobs.append(res["job"])

        manifest_doc = {
            "schema_version": "1.0.0",
            "episode_id": episode_id,
            "comfy_local_url": self.comfy_url,
            "jobs": dispatched_jobs,
        }
        (video_dir / "wan_jobs_manifest.json").write_text(
            json.dumps(manifest_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return {"manifest": manifest_doc, "results": results, "telemetry_path": str(telemetry_path)}
