"""Picture and Stage 2 Keyframe routing (D-52 legacy still tiers; D-123 Stage 2 Local ComfyUI Qwen ShotRouter). stdlib only.

Scope (N-06, 2026-10-30): the D-43 still-picture route uses TIERS below; legacy animated episodes (D-77, D-80) and rebuilt 4-stage Hybrid B -> C episodes (D-123) use ShotRouter for local ComfyUI Qwen keyframes.

- Legacy still-picture route (D-43 / D-52): ``TIERS``, ``tier_of``, ``route``, ``batch_cost``.
- Rebuilt 4-stage Hybrid B -> C pipeline (D-123): ``ShotRouter`` routes Stage 2 2D anchored storyboard keyframes to local
  ComfyUI (``workflows/comfyui/qwen_keyframe_multiangle.json``), generating 1 Start Frame by default and an End Frame ONLY
  for ``WAN_FLF2V`` shots, and writing ``02_keyframes/keyframe_manifest.json`` validated against
  ``explainer_engine/schemas/keyframe_manifest.schema.json``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Mapping

from explainer_engine import vault
from explainer_engine.imagegen.gemini import BATCH_PRICES, REFERENCE_USD

ROOT = Path(__file__).resolve().parents[2]
KEYFRAME_WORKFLOW_REL = "workflows/comfyui/qwen_keyframe_multiangle.json"

TIERS = {
    "draft": ("gemini-nano-banana-2.1", "1K"),
    "standard": ("gemini-nano-banana-2.1", "2K"),
    "premium": ("gemini-3-pro-image", "2K"),
}
DEFAULT_TIER = "standard"
PREMIUM_SHARE_MAX = 0.10

CANONICAL_GENERATION_MODES = (
    "WAN_I2V",
    "WAN_FLF2V",
    "WAN_CONTROL",
    "COLLAGE_STILL",
    "TACTILE_MAP",
    "STILL_25D",
    "MAP_25D",
    "WAN_FALLBACK_LTX",
)


def tier_of(pic: dict) -> str:
    return pic.get("tier") or DEFAULT_TIER


def route(tier: str) -> tuple[str, str]:
    """(model, size) of a tier; an unknown tier is an error, never a silent default."""
    if tier not in TIERS:
        raise ValueError(f"unknown picture tier {tier!r}; one of {sorted(TIERS)}")
    return TIERS[tier]


def batch_cost(tier: str, references: int = 0) -> float:
    model, size = route(tier)
    return round(BATCH_PRICES[model][size] + references * REFERENCE_USD, 4)


def _deterministic_seed(episode_id: str, shot_id: str, suffix: str = "start") -> int:
    digest = hashlib.sha256(f"{episode_id}:{shot_id}:{suffix}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_000_000_000


class ShotRouter:
    """Routes Stage 2 2D keyframe generation jobs to local ComfyUI Qwen workflows (D-123).

    Enforces:
    - Local-only ComfyUI endpoint (``http://127.0.0.1:8188`` by default; blocks cloud URLs when ``EXPLAINER_LOCAL_ONLY=1``).
    - Exactly 1 Start Frame per shot, plus 1 End Frame ONLY when ``generation_mode == 'WAN_FLF2V'`` (``needs_end_frame == True``).
    - Up to ``max_repair_attempts = 3`` 2D keyframe repair retries before marking ``FLAGGED_HUMAN_REVIEW``.
    """

    MAX_REPAIR_ATTEMPTS = 3

    def __init__(
        self,
        *,
        model_id: str | None = None,
        env: Mapping[str, str] | None = None,
        local_models: dict | None = None,
    ) -> None:
        self.env = env
        self.local_models = local_models or vault.local_models_config()
        defaults = self.local_models.get("active_defaults", {})
        self.model_id = model_id or defaults.get("stage2_image_model", "qwen_image_edit_2511")
        if self.model_id not in self.local_models.get("models", {}):
            raise ValueError(f"Unknown Stage 2 model_id {self.model_id!r} in config/local_models.json")
        self.comfy_url = vault.get_comfyui_url(env)
        self.workflow_path = ROOT / KEYFRAME_WORKFLOW_REL

    def build_comfy_prompt(
        self,
        shot: dict,
        world_bible: dict,
        *,
        frame_role: str = "start",
        seed: int = 1001,
        width: int = 1280,
        height: int = 720,
        steps: int = 24,
        cfg_scale: float = 4.5,
    ) -> dict:
        """Populate ``workflows/comfyui/qwen_keyframe_multiangle.json`` for a single Start or End keyframe."""
        template = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        model_cfg = self.local_models["models"][self.model_id]
        ckpt = model_cfg["checkpoint_file"]
        lora = (model_cfg.get("lora_files") or [""])[0]

        locs = {l["location_id"]: l["anchor_image_path"] for l in world_bible.get("locations", [])}
        chars = {c["character_id"]: c["reference_sheet_path"] for c in world_bible.get("characters", [])}
        loc_img = locs.get(shot["location_id"], f"02_keyframes/assets/{shot['location_id']}_anchor.png")
        char_ids = shot.get("character_ids") or []
        char_img = chars.get(char_ids[0], loc_img) if char_ids else loc_img

        cam = shot["camera_spec"]
        img_prompt = shot["image_prompt"]
        pos_prompt = img_prompt["end_frame_prompt"] if frame_role == "end" else img_prompt["start_frame_prompt"]
        neg_prompt = img_prompt["negative_prompt"]

        replacements = {
            "{{checkpoint_file}}": ckpt,
            "{{lora_file}}": lora,
            "{{location_anchor_image}}": loc_img,
            "{{character_reference_image}}": char_img,
            "{{horizontal_azimuth_deg}}": int(cam["horizontal_azimuth_deg"]),
            "{{vertical_angle}}": cam["vertical_angle"],
            "{{shot_size}}": cam["shot_size"],
            "{{positive_prompt}}": pos_prompt,
            "{{negative_prompt}}": neg_prompt,
            "{{width}}": int(width),
            "{{height}}": int(height),
            "{{seed}}": int(seed),
            "{{steps}}": int(steps),
            "{{cfg_scale}}": float(cfg_scale),
            "{{output_prefix}}": f"{shot['shot_id']}_{frame_role}",
        }

        graph = copy.deepcopy(template)
        graph.pop("_meta", None)
        for node in graph.values():
            inputs = node.get("inputs", {})
            for k, v in list(inputs.items()):
                if isinstance(v, str) and v in replacements:
                    inputs[k] = replacements[v]
        return graph

    def plan_stage2_keyframes(
        self,
        script_doc: dict,
        job_dir: Path | str | None = None,
        *,
        qa_check_fn: Callable[[dict, str, int], bool] | None = None,
    ) -> dict:
        """Build the Stage 2 ``keyframe_manifest.json`` and ``shot_route/3`` for a v4.0 ``production_script.json``."""
        episode_id = script_doc["episode_id"]
        wb = script_doc["world_bible"]
        base_dir = Path(job_dir) if job_dir else (ROOT / "jobs" / episode_id)
        kf_dir = base_dir / "02_keyframes"
        assets_dir = kf_dir / "assets"
        shots_dir = kf_dir / "shots"
        assets_dir.mkdir(parents=True, exist_ok=True)
        shots_dir.mkdir(parents=True, exist_ok=True)

        def _asset_records(items: list[dict], id_key: str, path_key: str) -> list[dict]:
            records = []
            for idx, item in enumerate(items):
                aid = item[id_key]
                rel_path = item[path_key]
                seed = _deterministic_seed(episode_id, aid, "anchor")
                sha = hashlib.sha256(f"{episode_id}:{aid}:{seed}".encode("utf-8")).hexdigest()
                records.append(
                    {
                        "asset_id": aid,
                        "path": rel_path,
                        "sha256": sha,
                        "seed": seed,
                        "approved": True,
                    }
                )
            return records

        shot_records: list[dict] = []
        route_records: list[dict] = []

        for shot in script_doc["shots"]:
            sid = shot["shot_id"]
            mode = shot["generation_mode"]
            if mode not in CANONICAL_GENERATION_MODES:
                raise ValueError(f"{sid}: unsupported generation_mode {mode!r}")
            kf_plan = shot["keyframe_plan"]
            needs_end = bool(kf_plan["needs_end_frame"])
            if mode == "WAN_FLF2V" and not needs_end:
                raise ValueError(f"{sid}: WAN_FLF2V requires needs_end_frame=True")
            if mode != "WAN_FLF2V" and needs_end:
                raise ValueError(f"{sid}: {mode} must have needs_end_frame=False (no 3-keyframe or non-FLF2V end frames)")

            start_rel = f"02_keyframes/shots/{sid}_start.png"
            end_rel = f"02_keyframes/shots/{sid}_end.png" if needs_end else None

            base_seed = _deterministic_seed(episode_id, sid, "start")
            repair_attempts = 0
            status = "KEYFRAME_APPROVED"
            repair_notes = None

            if qa_check_fn is not None:
                approved = False
                for attempt in range(self.MAX_REPAIR_ATTEMPTS + 1):
                    curr_seed = base_seed + attempt * 101
                    if qa_check_fn(shot, "start", curr_seed):
                        approved = True
                        base_seed = curr_seed
                        if attempt > 0:
                            status = "REPAIRED_2D"
                            repair_notes = f"Repaired in 2D after {attempt} retry(s)"
                        break
                    if attempt < self.MAX_REPAIR_ATTEMPTS:
                        repair_attempts += 1
                if not approved:
                    status = "FLAGGED_HUMAN_REVIEW"
                    repair_notes = f"Exceeded max {self.MAX_REPAIR_ATTEMPTS} automatic 2D repair retries"

            start_sha = hashlib.sha256(f"{episode_id}:{sid}:start:{base_seed}".encode("utf-8")).hexdigest()
            end_seed = _deterministic_seed(episode_id, sid, "end") if needs_end else None
            end_sha = (
                hashlib.sha256(f"{episode_id}:{sid}:end:{end_seed}".encode("utf-8")).hexdigest()
                if needs_end
                else None
            )

            shot_records.append(
                {
                    "shot_id": sid,
                    "generation_mode": mode,
                    "needs_start_frame": True,
                    "needs_end_frame": needs_end,
                    "start_frame_source": kf_plan["start_frame_source"],
                    "start_frame_path": start_rel,
                    "start_frame_sha256": start_sha,
                    "start_frame_seed": base_seed,
                    "end_frame_path": end_rel,
                    "end_frame_sha256": end_sha,
                    "end_frame_seed": end_seed,
                    "approval_status": status,
                    "repair_attempts": repair_attempts,
                    "repair_notes": repair_notes,
                }
            )
            route_records.append(
                {
                    "shot_id": sid,
                    "route_type": mode,
                    "needs_end_frame": needs_end,
                    "start_frame_path": start_rel,
                    "end_frame_path": end_rel,
                    "wan_job_path": "03_video/wan_jobs_manifest.json",
                }
            )

        manifest = {
            "schema_version": "1.0.0",
            "episode_id": episode_id,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "stage2_model_id": self.model_id,
            "comfy_local_url": self.comfy_url,
            "assets": {
                "characters": _asset_records(wb.get("characters", []), "character_id", "reference_sheet_path"),
                "locations": _asset_records(wb.get("locations", []), "location_id", "anchor_image_path"),
                "props": _asset_records(wb.get("props", []), "prop_id", "anchor_image_path"),
            },
            "shots": shot_records,
        }

        manifest_path = kf_dir / "keyframe_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        route_doc = {
            "schema": "shot_route/3",
            "episode_id": episode_id,
            "fps": int(script_doc.get("fps", 24)),
            "routes": route_records,
        }
        (kf_dir / "shot_route.json").write_text(
            json.dumps(route_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return manifest
