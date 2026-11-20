
"""Voice identity consistency and inter-character separation validation (OR-A08, OR-A13)."""

from dataclasses import dataclass
from itertools import combinations
import numpy as np

@dataclass(frozen=True)
class Limits:
    """Threshold configuration for voice embedding validation (all defaults are hypotheses)."""

    self_floor: float = 0.75
    cross_ceiling: float = 0.90
    min_clips: int = 2
    severity: str = "REVIEW"

def _to_1d_float_vector(vec: np.ndarray | list[float], name: str = "vector") -> np.ndarray:
    """Convert input to a non-empty, finite, non-zero 1-D float64 numpy array."""
    arr = np.asarray(vec, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{name} must be a non-empty 1-D vector, got shape {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    norm = float(np.linalg.norm(arr))
    if norm == 0.0:
        raise ValueError(f"{name} must be non-zero")
    return arr

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity of two 1-D float vectors; ValueError on different length or a zero vector."""
    vec_a = _to_1d_float_vector(a, "a")
    vec_b = _to_1d_float_vector(b, "b")
    if vec_a.shape[0] != vec_b.shape[0]:
        raise ValueError(f"Vector length mismatch: {vec_a.shape[0]} vs {vec_b.shape[0]}")
    sim = float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))
    return float(np.clip(sim, -1.0, 1.0))

def centroid(vectors: list[list[float]]) -> np.ndarray:
    """Mean of the L2-normalised vectors (so a long vector does not dominate). Result is NOT re-normalised."""
    if not vectors:
        raise ValueError("vectors must not be empty")
    unit_vectors: list[np.ndarray] = []
    expected_dim: int | None = None
    for idx, vec in enumerate(vectors):
        arr = _to_1d_float_vector(vec, f"vectors[{idx}]")
        if expected_dim is None:
            expected_dim = arr.shape[0]
        elif arr.shape[0] != expected_dim:
            raise ValueError(f"Embedding length mismatch in centroid: expected {expected_dim}, got {arr.shape[0]}")
        unit_vectors.append(arr / np.linalg.norm(arr))
    return np.mean(np.stack(unit_vectors, axis=0), axis=0)

def check(clips: list[dict], limits: Limits = Limits()) -> list[dict]:
    """Validate per-character voice stability (OR-A08) and inter-character separation (OR-A13)."""
    if not isinstance(clips, list):
        raise ValueError("clips must be a list of clip dicts")
    if not clips:
        return []

    expected_dim: int | None = None
    by_character: dict[str, list[tuple[str, np.ndarray]]] = {}

    for idx, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise ValueError(f"clips[{idx}] must be a dict")
        if "id" not in clip or "character" not in clip or "embedding" not in clip:
            raise ValueError(f"clips[{idx}] missing required keys ('id', 'character', 'embedding')")
        clip_id = clip["id"]
        character = clip["character"]
        if not isinstance(clip_id, str) or not clip_id:
            raise ValueError(f"clips[{idx}]['id'] must be a non-empty string")
        if not isinstance(character, str) or not character:
            raise ValueError(f"clips[{idx}]['character'] must be a non-empty string")

        vec = _to_1d_float_vector(clip["embedding"], f"clips[{idx}]['embedding']")
        if expected_dim is None:
            expected_dim = vec.shape[0]
        elif vec.shape[0] != expected_dim:
            raise ValueError(
                f"Embedding length mismatch for clip '{clip_id}': expected {expected_dim}, got {vec.shape[0]}"
            )
        by_character.setdefault(character, []).append((clip_id, vec))

    findings: list[dict] = []
    centroids: dict[str, np.ndarray] = {}

    for character, char_clips in by_character.items():
        char_centroid = centroid([vec.tolist() for _, vec in char_clips])
        if np.linalg.norm(char_centroid) > 0.0:
            centroids[character] = char_centroid

        if len(char_clips) < limits.min_clips:
            findings.append(
                {
                    "rule": "VOICE-03",
                    "severity": limits.severity,
                    "where": character,
                    "detail": (
                        f"Character '{character}' has {len(char_clips)} clip(s), "
                        f"below the minimum of {limits.min_clips} required for drift checks."
                    ),
                }
            )
            continue

        for clip_id, vec in char_clips:
            if np.linalg.norm(char_centroid) == 0.0:
                sim = 0.0
            else:
                sim = cosine(vec, char_centroid)
            if round(sim, 6) < round(limits.self_floor, 6):
                findings.append(
                    {
                        "rule": "VOICE-01",
                        "severity": limits.severity,
                        "where": clip_id,
                        "detail": (
                            f"Clip '{clip_id}' for '{character}' has centroid cosine similarity "
                            f"{sim:.6f}, below floor {limits.self_floor:.6f}."
                        ),
                    }
                )

    for char_a, char_b in combinations(sorted(centroids.keys()), 2):
        sim = cosine(centroids[char_a], centroids[char_b])
        if round(sim, 6) >= round(limits.cross_ceiling, 6):
            pair_id = f"{char_a}|{char_b}"
            findings.append(
                {
                    "rule": "VOICE-02",
                    "severity": limits.severity,
                    "where": pair_id,
                    "detail": (
                        f"Characters '{char_a}' and '{char_b}' have centroid cosine similarity "
                        f"{sim:.6f}, at or above ceiling {limits.cross_ceiling:.6f}."
                    ),
                }
            )

    findings.sort(key=lambda item: (item["where"], item["rule"]))
    return findings
