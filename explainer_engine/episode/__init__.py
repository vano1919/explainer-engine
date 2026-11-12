"""Episode-First architecture package (`explainer_engine.episode`).

Provides strict per-episode workspace resolution, manifest validation,
historical-era and semantic asset compatibility gating, and provenance logging.
"""
from explainer_engine.episode.context import (
    CANONICAL_EPISODE_SUBDIRS,
    ERA_INCOMPATIBILITY_MAP,
    EpisodeAssetQuarantineError,
    EpisodeContext,
    EpisodeIsolationError,
    EpisodeResolver,
    build_episode_directory_tree,
    import_episode_asset,
    load_episode_context,
    validate_asset_compatibility,
)

__all__ = [
    "CANONICAL_EPISODE_SUBDIRS",
    "ERA_INCOMPATIBILITY_MAP",
    "EpisodeAssetQuarantineError",
    "EpisodeContext",
    "EpisodeIsolationError",
    "EpisodeResolver",
    "build_episode_directory_tree",
    "import_episode_asset",
    "load_episode_context",
    "validate_asset_compatibility",
]
