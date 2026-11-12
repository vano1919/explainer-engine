"""Episode-First Context, Path Resolver, and Semantic/Era Asset Compatibility Gate.

Enforces strict per-episode isolation (`episodes/<episode_id>/`):
1. Every episode resolves its own directory tree (`research/`, `story/`, `assets/`,
   `planning/`, `production/`, `audio/`, `editing/`, `renders/`, `qa/`, `logs/`).
2. No pipeline stage may resolve an asset belonging to another episode (`episode_scope`)
   unless `shared_ok=True` AND its `historical_period` / `era_tags` / `domain_tags`
   are compatible with the active `EpisodeContext`.
3. Any anachronistic or cross-episode asset (e.g., 1815 Waterloo Napoleon, cavalry,
   or Rothschild in the 74,000 BCE Toba episode) is deterministically rejected and
   quarantined before rendering.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Sequence, Tuple

import jsonschema

_SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"


def validate_instance(instance: dict, schema_name: str) -> None:
    schema_path = _SCHEMAS_DIR / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance, schema)


class EpisodeIsolationError(ValueError):
    """Raised when a cross-episode or path-traversal violation is detected."""


class EpisodeAssetQuarantineError(ValueError):
    """Raised when an asset fails historical-era or semantic compatibility validation."""


CANONICAL_EPISODE_SUBDIRS: Tuple[str, ...] = (
    "research",
    "story",
    "assets/reference/characters",
    "assets/reference/locations",
    "assets/reference/props",
    "assets/reference/style",
    "assets/generated/images",
    "assets/generated/depth",
    "assets/generated/mattes",
    "assets/generated/video_clips",
    "assets/maps/dem",
    "assets/maps/vectors",
    "assets/maps/plates",
    "assets/maps/overlays",
    "assets/maps/renders",
    "assets/3d/scenes",
    "assets/3d/terrain",
    "assets/3d/cameras",
    "assets/3d/renders",
    "planning",
    "production/shot_clips",
    "production/map_clips",
    "production/parallax_clips",
    "production/blender_clips",
    "production/transitions",
    "audio/voice_lines",
    "audio/sfx",
    "audio/ambience",
    "audio/music",
    "audio/stems",
    "editing",
    "renders/chunks",
    "renders/previews",
    "renders/final",
    "qa/contact_sheets",
    "qa/frame_audits",
    "qa/audio_audits",
    "logs",
)

# Historical-era incompatibility rules: maps era_id -> set of forbidden era tags and semantic tokens
ERA_INCOMPATIBILITY_MAP: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "prehistoric_pleistocene": {
        "forbidden_eras": (
            "napoleonic_19th_century",
            "1815_waterloo",
            "modern_20th_century",
            "1946_postwar_british_empire",
            "early_modern",
            "medieval",
        ),
        "forbidden_tokens": (
            "napoleon",
            "wellington",
            "blucher",
            "grouchy",
            "rothschild",
            "waterloo",
            "imperial_guard",
            "french_cavalry",
            "cuirassier",
            "bicorne",
            "musket",
            "cannon",
            "artillery",
            "bayonet",
            "royal_exchange",
            "whitehall",
            "bank_of_england",
            "keynes",
            "attlee",
            "bevin",
            "sword_metal",
            "horse_cavalry",
            "locomotive",
            "steamship",
            "podcast_studio",
            "oppenheimer",
        ),
    },
    "napoleonic_19th_century": {
        "forbidden_eras": (
            "prehistoric_pleistocene",
            "74000_bce",
            "modern_20th_century",
            "contemporary_21st_century",
        ),
        "forbidden_tokens": (
            "pleistocene",
            "74000bce",
            "shinfa_metema",
            "homo_sapiens_bottleneck",
            "podcast_studio",
            "oppenheimer",
        ),
    },
    "ancient_classical": {
        "forbidden_eras": ("napoleonic_19th_century", "1815_waterloo", "modern_20th_century", "contemporary_21st_century"),
        "forbidden_tokens": ("musket", "cannon", "rifle", "locomotive", "steamship", "automobile", "podcast_studio"),
    },
    "medieval": {
        "forbidden_eras": ("prehistoric_pleistocene", "modern_20th_century", "contemporary_21st_century"),
        "forbidden_tokens": ("rifle", "locomotive", "steamship", "automobile", "aircraft", "podcast_studio"),
    },
    "modern_20th_century": {
        "forbidden_eras": ("prehistoric_pleistocene", "74000_bce", "1815_waterloo"),
        "forbidden_tokens": ("pleistocene", "74000bce", "shinfa_metema"),
    },
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.digest().hex()


@dataclass(frozen=True)
class EpisodeContext:
    """Immutable runtime context for a single self-contained episode."""

    episode_id: str
    root_dir: Path
    manifest: Dict[str, Any]
    strict_isolation: bool = True

    @property
    def slug(self) -> str:
        return str(self.manifest.get("slug") or self.episode_id)

    @property
    def title(self) -> str:
        return str(self.manifest.get("title") or self.episode_id)

    @property
    def era_id(self) -> str:
        hp = self.manifest.get("historical_period") or {}
        return str(hp.get("era_id") or "")

    @property
    def allowed_era_tags(self) -> Tuple[str, ...]:
        return tuple(str(x).lower() for x in (self.manifest.get("allowed_era_tags") or []))

    @property
    def forbidden_era_tags(self) -> Tuple[str, ...]:
        base = set(str(x).lower() for x in (self.manifest.get("forbidden_era_tags") or []))
        era_rules = ERA_INCOMPATIBILITY_MAP.get(self.era_id, {})
        base.update(x.lower() for x in era_rules.get("forbidden_eras", ()))
        return tuple(sorted(base))

    @property
    def forbidden_semantic_tokens(self) -> Tuple[str, ...]:
        base = set(str(x).lower() for x in (self.manifest.get("forbidden_semantic_tokens") or []))
        era_rules = ERA_INCOMPATIBILITY_MAP.get(self.era_id, {})
        base.update(x.lower() for x in era_rules.get("forbidden_tokens", ()))
        return tuple(sorted(base))

    @property
    def allow_shared_style_anchors(self) -> bool:
        src = self.manifest.get("asset_sources") or {}
        return bool(src.get("allow_shared_style_anchors", False))


class EpisodeResolver:
    """Deterministic path and asset resolver scoped strictly to an EpisodeContext."""

    def __init__(self, context: EpisodeContext) -> None:
        self.context = context
        self.root = context.root_dir.resolve()

    def subdir(self, relative_dir: str, create: bool = True) -> Path:
        clean = relative_dir.strip("/").replace("\\", "/")
        target = (self.root / clean).resolve()
        self.assert_within_episode(target)
        if create:
            target.mkdir(parents=True, exist_ok=True)
        return target

    def resolve_path(self, relative_or_abs: str | Path) -> Path:
        p = Path(relative_or_abs)
        target = p.resolve() if p.is_absolute() else (self.root / p).resolve()
        self.assert_within_episode(target)
        return target

    def assert_within_episode(self, path: Path) -> None:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise EpisodeIsolationError(
                f"EPISODE_ISOLATION_VIOLATION: Path '{resolved}' is outside episode root "
                f"'{self.root}' for episode '{self.context.episode_id}'."
            ) from exc

    def select_asset_for_shot(
        self,
        shot_id: str,
        shot_spec: Dict[str, Any],
        candidates: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Select a verified compatible asset for `shot_id` and emit a full selection audit log."""
        considered: List[str] = []
        rejected: List[Dict[str, str]] = []
        selected: Optional[Dict[str, Any]] = None

        for cand in candidates:
            aid = str(cand.get("asset_id") or cand.get("id") or cand.get("filename") or "unknown")
            considered.append(aid)
            ok, reason = validate_asset_compatibility(self.context, cand, shot_spec=shot_spec)
            if not ok:
                rejected.append({"asset_id": aid, "reason": reason})
                continue
            if selected is None:
                selected = cand

        if selected is None:
            raise EpisodeAssetQuarantineError(
                f"NO_COMPATIBLE_ASSET_FOR_SHOT ({self.context.episode_id} / {shot_id}): "
                f"Considered {len(considered)} candidate(s), all rejected: {rejected}"
            )

        selected_id = str(selected.get("asset_id") or selected.get("id") or selected.get("filename"))
        return {
            "shot_id": shot_id,
            "episode_id": self.context.episode_id,
            "candidate_assets_considered": considered,
            "rejected_candidates": rejected,
            "selected_asset_id": selected_id,
            "selected_asset": selected,
            "selection_reason": (
                f"Verified episode_scope={selected.get('episode_scope')!r}, "
                f"era={selected.get('historical_period')!r}, and local file existence."
            ),
        }


def validate_asset_compatibility(
    context: EpisodeContext,
    asset_meta: Dict[str, Any],
    shot_spec: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Validate whether `asset_meta` is legally permitted inside `context`."""
    aid = str(asset_meta.get("asset_id") or asset_meta.get("id") or asset_meta.get("filename") or "unknown")
    ep_scope = str(asset_meta.get("episode_scope") or asset_meta.get("episode_id") or "").strip()
    shared_ok = bool(asset_meta.get("shared_ok", False))
    verified = bool(asset_meta.get("verified", True))

    if not verified:
        return False, f"Asset '{aid}' is marked unverified (verified=False)."

    # 1. Episode ownership check
    if ep_scope != context.episode_id:
        if not (shared_ok and context.allow_shared_style_anchors and ep_scope in ("shared", "global_style")):
            return (
                False,
                f"Cross-episode contamination blocked: asset '{aid}' belongs to "
                f"episode_scope='{ep_scope}', active episode is '{context.episode_id}'.",
            )

    # 2. Historical period / era tags check
    asset_era = str(asset_meta.get("historical_period") or "").strip().lower()
    asset_era_tags = [str(t).strip().lower() for t in (asset_meta.get("era_tags") or [])]
    all_asset_eras = set(asset_era_tags + ([asset_era] if asset_era else []))

    for bad_era in context.forbidden_era_tags:
        if bad_era and bad_era in all_asset_eras:
            return (
                False,
                f"Anachronistic era tag '{bad_era}' on asset '{aid}' is forbidden in "
                f"episode '{context.episode_id}' (era='{context.era_id}').",
            )

    if context.allowed_era_tags and all_asset_eras:
        if not any(tag in context.allowed_era_tags for tag in all_asset_eras):
            return (
                False,
                f"Asset '{aid}' era tags {sorted(all_asset_eras)} do not intersect "
                f"allowed_era_tags {list(context.allowed_era_tags)} for '{context.episode_id}'.",
            )

    # 3. Semantic subject / token contamination check
    text_fields = [
        str(asset_meta.get("subject") or ""),
        str(asset_meta.get("description") or ""),
        str(asset_meta.get("prompt") or ""),
        " ".join(str(x) for x in (asset_meta.get("domain_tags") or [])),
        " ".join(str(x) for x in (asset_meta.get("subject_tags") or [])),
        " ".join(str(x) for x in (asset_meta.get("characters") or [])),
    ]
    blob = " ".join(text_fields).lower()
    for bad_tok in context.forbidden_semantic_tokens:
        if not bad_tok:
            continue
        pattern = r"\b" + re.escape(bad_tok.replace("_", " ")) + r"\b"
        if bad_tok in blob or re.search(pattern, blob):
            return (
                False,
                f"Semantic contamination blocked: forbidden token '{bad_tok}' found in "
                f"asset '{aid}' metadata for episode '{context.episode_id}'.",
            )

    # 4. File existence and non-zero size check if path provided
    file_path = asset_meta.get("file_path") or asset_meta.get("path")
    if file_path:
        p = Path(str(file_path))
        if not p.is_absolute():
            p = (context.root_dir / p).resolve()
        if not p.is_file() or p.stat().st_size == 0:
            return False, f"Asset file '{p}' does not exist or is empty."
        if context.strict_isolation and ep_scope == context.episode_id:
            try:
                p.resolve().relative_to(context.root_dir.resolve())
            except ValueError:
                return (
                    False,
                    f"Asset file '{p}' resides outside episode root '{context.root_dir}'.",
                )

    return True, "ok"


def build_episode_directory_tree(
    episodes_root: Path,
    manifest: Dict[str, Any],
    readme_text: Optional[str] = None,
) -> EpisodeContext:
    """Create the canonical `episodes/<episode_id>/` directory structure and write `episode.json`."""
    validate_instance(manifest, "episode_manifest.schema.json")
    episode_id = str(manifest["episode_id"])
    ep_root = (episodes_root / episode_id).resolve()
    ep_root.mkdir(parents=True, exist_ok=True)

    for rel in CANONICAL_EPISODE_SUBDIRS:
        (ep_root / rel).mkdir(parents=True, exist_ok=True)

    manifest_path = ep_root / "episode.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme_path = ep_root / "README.md"
    if readme_text is None:
        hp = manifest["historical_period"]
        readme_text = (
            f"# Episode Workspace: `{episode_id}` — {manifest['title']}\n\n"
            f"- **Slug**: `{manifest['slug']}`\n"
            f"- **Historical Period**: `{hp['era_id']}` ({hp['label']}, {hp['start_year']} to {hp['end_year']})\n"
            f"- **Target Duration**: `{manifest['target_duration_s']}s`\n"
            f"- **Visual Style Profile**: `{manifest['visual_style_profile']}`\n"
            f"- **Map Style Profile**: `{manifest['map_style_profile']}`\n"
            f"- **Strict Episode Isolation**: `{manifest['asset_sources']['strict_episode_isolation']}`\n"
        )
    readme_path.write_text(readme_text, encoding="utf-8")

    lock_path = ep_root / "episode_lock.json"
    if not lock_path.exists():
        lock_payload = {
            "schema": "episode_lock/1",
            "episode_id": episode_id,
            "locked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "manifest_sha256": _sha256_file(manifest_path),
            "verified_assets_count": 0,
            "quarantined_assets_count": 0,
        }
        lock_path.write_text(json.dumps(lock_payload, indent=2) + "\n", encoding="utf-8")

    return EpisodeContext(
        episode_id=episode_id,
        root_dir=ep_root,
        manifest=manifest,
        strict_isolation=bool(manifest["asset_sources"].get("strict_episode_isolation", True)),
    )


def load_episode_context(episode_root: Path) -> EpisodeContext:
    """Load and schema-validate `episode.json` from `episode_root`."""
    ep_root = episode_root.resolve()
    manifest_path = ep_root / "episode.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing episode.json in {ep_root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_instance(manifest, "episode_manifest.schema.json")
    return EpisodeContext(
        episode_id=str(manifest["episode_id"]),
        root_dir=ep_root,
        manifest=manifest,
        strict_isolation=bool(manifest["asset_sources"].get("strict_episode_isolation", True)),
    )


def import_episode_asset(
    context: EpisodeContext,
    source_file: Path,
    target_rel_path: str,
    asset_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate and copy an asset into the episode workspace with full SHA-256 provenance."""
    if not source_file.is_file() or source_file.stat().st_size == 0:
        raise FileNotFoundError(f"Source asset file missing or empty: {source_file}")

    resolver = EpisodeResolver(context)
    dest_path = resolver.resolve_path(target_rel_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    meta_check = dict(asset_metadata)
    meta_check.setdefault("episode_scope", context.episode_id)
    meta_check["file_path"] = str(source_file.resolve())

    # Validate era & semantic compatibility before copying
    temp_ctx = EpisodeContext(
        episode_id=context.episode_id,
        root_dir=context.root_dir,
        manifest=context.manifest,
        strict_isolation=False,
    )
    ok, reason = validate_asset_compatibility(temp_ctx, meta_check)
    if not ok:
        raise EpisodeAssetQuarantineError(reason)

    if source_file.resolve() != dest_path.resolve():
        shutil.copy2(source_file, dest_path)

    sha = _sha256_file(dest_path)
    rel_str = str(dest_path.relative_to(context.root_dir)).replace("\\", "/")
    record = dict(asset_metadata)
    record.update({
        "episode_scope": context.episode_id,
        "file_path": rel_str,
        "sha256": sha,
        "bytes": dest_path.stat().st_size,
        "verified": True,
        "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    return record
