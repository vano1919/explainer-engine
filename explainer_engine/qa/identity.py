# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/qa/identity.py`
# Target Module : explainer_engine/qa/identity.py
# Target Classes/Symbols : def check(), def cosine(), def clip_embedder(), def hero_identity(), def identity_check(), def style_check(), def mouth_box(), def mouth_openness(), def _grid(), def lipsync_offset(), def lipsync_check(), def lipsync_frames(), def lipsync_file()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""P8 identity and sync QA of a rendered shot (BP-133, CRAFT-ANI-15/16). Free, CPU, REVIEW only (BP-133 is a hypothesis).

- Identity: the cosine between a hero sheet and the frames of a shot, with the CLIP embedder of ``training/embed.py`` (no new
  weights). The identity threshold is "calibrate on our hero sheets" (BP-133): until a calibrated number is passed in, the row
  is INFO (score only), never a guess and never the Blueprint's 0.65. The embedder is injectable (``embedder(paths) -> (n, d)``):
  where torch and open_clip are not installed the default raises ConfigError and tests inject a deterministic fake.
- Style: ``compose/style_score.py`` is read through its pure ``score`` / ``verdict`` (read-only, AC-14); the embedding of a
  picture is injectable too.
- Lip sync: a free proxy, no SyncNet (not pinned). The mouth's openness per frame (the dark share of a mouth box, from the
  face box of ``qa/face_points.detect``) is cross-correlated with the loudness envelope of ``audio/envelope.py``; the lag of
  the best match is the offset in ms (positive = the mouth moves after the sound). Over ``lipsync_max_ms`` it is a REVIEW row.

Every function returns ``qa_report/1`` check dicts (check_id, rule, severity, measured, threshold, passed) that
``qa/retry_router.write_report`` collects.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from explainer_engine.audio import envelope as ENV
from explainer_engine.core.errors import ConfigError
from explainer_engine.standards import sourced_rules as SR

RULE = "BP-133"
GRID_S = 0.005   # analysis grid of the lag search (5 ms); an analysis constant, not a rule
MAX_LAG_MS = 500  # the search window around zero; an offset beyond it is "no match", not a measured offset


def check(check_id: str, severity: str, measured, threshold, passed: bool, rule: str = RULE) -> dict:
    return {"check_id": check_id, "rule": rule, "severity": severity, "measured": measured, "threshold": threshold,
            "passed": bool(passed)}


# --- identity ----------------------------------------------------------------------------------------------------------
def cosine(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def clip_embedder(paths, cache=None) -> np.ndarray:
    """The default embedder: CLIP ViT-B-32 of ``training/embed.py``. ConfigError when torch / open_clip are missing."""
    try:
        from explainer_engine.training import embed
        return embed.images(paths, cache)
    except ImportError as e:
        raise ConfigError(f"the CLIP embedder needs torch + open_clip_torch ({e}); install them where the QA runs or pass "
                          "embedder=") from e


def hero_identity(frames, sheets, embedder=None) -> dict:
    """Each frame's best cosine to the hero sheet pictures: {per_frame, mean, min}. ``frames`` / ``sheets`` are image paths."""
    embedder = embedder or clip_embedder
    f, s = np.asarray(embedder(list(frames)), dtype=float), np.asarray(embedder(list(sheets)), dtype=float)
    if not len(f) or not len(s):
        raise ValueError("identity needs at least one frame and one hero sheet picture")
    f = f / np.linalg.norm(f, axis=1, keepdims=True)
    s = s / np.linalg.norm(s, axis=1, keepdims=True)
    per = (f @ s.T).max(axis=1)
    return {"per_frame": [round(float(x), 4) for x in per], "mean": round(float(per.mean()), 4), "min": round(float(per.min()), 4)}


def identity_check(shot_id: str, scores: dict, threshold: float | None = None) -> dict:
    """CRAFT-ANI-16. Without a calibrated ``threshold`` the row is a REVIEW row that passes (the score is only reported; BP-133 is REVIEW)."""
    if threshold is None:
        return check(f"identity:{shot_id}", "REVIEW", scores["min"], "uncalibrated (BP-133: calibrate on our hero sheets)", True)
    return check(f"identity:{shot_id}", "REVIEW", scores["min"], threshold, scores["min"] >= threshold)


def style_check(shot_id: str, image_embedding, refs: list, control_embedding=None) -> dict:
    """AC-14 through ``compose/style_score`` (read-only): PASS / REVIEW against a same-place control, else score only."""
    from explainer_engine.compose import style_score as SS
    s = SS.score(np.asarray(image_embedding), [np.asarray(r) for r in refs])
    c = None if control_embedding is None else SS.score(np.asarray(control_embedding), [np.asarray(r) for r in refs])
    v = SS.verdict(s, c)
    return check(f"style:{shot_id}", "INFO" if v["severity"] == "INFO" else "REVIEW", v["score"],
                 f"control {v.get('control')} - {SS.DROP_REVIEW}" if c is not None else "no control", v["severity"] != "REVIEW",
                 rule="AC-14")


# --- lip sync ----------------------------------------------------------------------------------------------------------
def mouth_box(face: dict) -> tuple[float, float, float, float]:
    """The mouth's box (shares of the frame) from a ``face_points.detect`` face {x, y (centre), w, h}: the lower middle of it."""
    return (face["x"] - 0.25 * face["w"], face["y"] + 0.10 * face["h"], face["x"] + 0.25 * face["w"], face["y"] + 0.45 * face["h"])


def mouth_openness(frames, box) -> list[float]:
    """Per frame, the dark share of the mouth box (an open mouth shows its dark inside; the lines of a closed one are thin).
    ``frames`` are (h, w) or (h, w, 3) uint8 arrays, ``box`` shares (x0, y0, x1, y1)."""
    out = []
    for fr in frames:
        g = np.asarray(fr, dtype=float)
        g = g.mean(axis=2) if g.ndim == 3 else g
        h, w = g.shape
        x0, y0, x1, y1 = (int(box[0] * w), int(box[1] * h), max(int(box[2] * w), int(box[0] * w) + 1),
                          max(int(box[3] * h), int(box[1] * h) + 1))
        out.append(float(1.0 - g[y0:y1, x0:x1].mean() / 255.0))
    return out


def _grid(series, step_s: float, dt: float, end: float) -> np.ndarray:
    t = np.arange(0.0, end, dt)
    x = np.interp(t, np.arange(len(series)) * step_s, np.asarray(series, dtype=float))
    x = x - x.mean()
    sd = x.std()
    return x / sd if sd > 0 else x


def lipsync_offset(mouth: list[float], mouth_fps: float, env: list[float], env_step_s: float = ENV.STEP,
                   max_lag_ms: float = MAX_LAG_MS) -> dict:
    """The lag of the best match between the mouth series and the loudness envelope: {offset_ms, confidence}. Positive: the
    mouth follows the sound. ``confidence`` is the normalised correlation at the peak (0..1; low = nothing to measure)."""
    end = min(len(mouth) / mouth_fps, len(env) * env_step_s)
    if end < 1.0 or len(mouth) < 2 or len(env) < 2:
        raise ValueError("lip-sync needs at least one second of mouth frames and envelope")
    m, a = _grid(mouth, 1.0 / mouth_fps, GRID_S, end), _grid(env, env_step_s, GRID_S, end)
    n = len(m)
    c = np.correlate(m, a, "full") / n
    lags = np.arange(-(n - 1), n) * GRID_S * 1000.0
    ok = np.abs(lags) <= max_lag_ms
    k = int(np.argmax(np.where(ok, c, -np.inf)))
    return {"offset_ms": round(float(lags[k]), 1), "confidence": round(float(max(0.0, min(1.0, c[k]))), 3)}


def lipsync_check(shot_id: str, offset: dict) -> dict:
    """CRAFT-ANI-15 (BP-133, REVIEW): the offset beyond ``lipsync_max_ms`` (a REVIEW row, never a FAIL)."""
    limit = SR.T(RULE, "lipsync_max_ms")
    return check(f"lipsync:{shot_id}", "REVIEW", offset["offset_ms"], limit, abs(offset["offset_ms"]) <= limit)


def lipsync_frames(offset_ms: float, fps: float) -> float:
    return offset_ms * fps / 1000.0


def lipsync_file(frames, fps: float, box, wav: Path | str, shot_id: str) -> tuple[dict, dict]:
    """Frames of a clip (arrays) + the line's WAV -> (offset, check row)."""
    off = lipsync_offset(mouth_openness(frames, box), fps, ENV.envelope(Path(wav)))
    return off, lipsync_check(shot_id, off)
