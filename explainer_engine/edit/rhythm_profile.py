# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/edit/rhythm_profile.py`
# Target Module : explainer_engine/edit/rhythm_profile.py
# Target Classes/Symbols : def _profiles(), def available_profiles(), def resolve_profile_name(), def get_profile(), def _scaled(), def zone_at_time(), def zone_for_window(), def zone_wpm(), def words_to_seconds()
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

"""The one reader of the rhythm profile (BP-169): which zone of the episode a second belongs to, and what the zone asks for.

Every number lives in ``standards/sourced_rules.json`` (BP-169); nothing here copies one. ``calm_docudrama`` is the older
profile: it has no zones, its numbers are the other BP rows (BP-01, BP-107 ...), so a script of that era keeps its checks.
stdlib only.

    available_profiles()                       -> ["mrbeast_animated", "calm_docudrama"]
    resolve_profile_name(doc)                  -> a name from the doc's ``rhythm_profile`` or its schema version
    zone_at_time(t_s, total_s=720.0)           -> the zone dict at second t_s (the last zone owns total_s itself)
    zone_for_window(start_s, end_s)            -> the zone that holds most of [start_s, end_s)
    zone_wpm(zone_id, kind="heard")            -> the pace target of a zone
    words_to_seconds(words, t_start_s)         -> seconds the words take when read at the zones' pace, zone by zone
"""

from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR

LEGACY = "calm_docudrama"


def _profiles() -> dict:
    return SR.T("BP-169", "profiles")


def available_profiles() -> list[str]:
    return list(_profiles())


def resolve_profile_name(doc: dict | None = None) -> str:
    """The profile a document asks for: its ``rhythm_profile`` key, else the version of its schema (``production_script/3``
    is the calm era, ``/4`` and later the zoned one), else the registry default."""
    doc = doc or {}
    name = doc.get("rhythm_profile")
    if name is None:
        schema = str(doc.get("schema", ""))
        tail = schema.rsplit("/", 1)[-1]
        if tail.isdigit():
            name = LEGACY if int(tail) <= 3 else SR.T("BP-169", "default_profile")
    name = name or SR.T("BP-169", "default_profile")
    if name not in _profiles():
        raise KeyError(f"unknown rhythm profile {name!r}; known: {available_profiles()}")
    return name


def get_profile(doc_or_name: dict | str | None = None) -> dict:
    name = doc_or_name if isinstance(doc_or_name, str) else resolve_profile_name(doc_or_name)
    if name not in _profiles():
        raise KeyError(f"unknown rhythm profile {name!r}; known: {available_profiles()}")
    prof = _profiles()[name]
    if not isinstance(prof, dict):
        raise KeyError(f"{name!r} has no zones: it is the legacy profile, read the other BP rows")
    return prof


def _scaled(prof: dict, total_s: float) -> list[tuple[float, float, dict]]:
    base = float(SR.T("BP-169", "episode_s"))
    k = total_s / base
    return [(z["window_s"][0] * k, z["window_s"][1] * k, z) for z in prof["zones"]]


def zone_at_time(t_s: float, *, total_s: float = 720.0, profile_name: str = "mrbeast_animated") -> dict:
    if t_s < 0:
        raise ValueError("time before the start of the episode")
    zones = _scaled(get_profile(profile_name), total_s)
    for lo, hi, z in zones:
        if lo <= t_s < hi:
            return z
    return zones[-1][2]  # the right boundary and anything after belong to the last zone


def zone_for_window(start_s: float, end_s: float, *, total_s: float = 720.0, profile_name: str = "mrbeast_animated") -> dict:
    if end_s <= start_s:
        raise ValueError("an empty window")
    best, best_len = None, -1.0
    for lo, hi, z in _scaled(get_profile(profile_name), total_s):
        overlap = min(end_s, hi) - max(start_s, lo)
        if overlap > best_len:
            best, best_len = z, overlap
    return best


def zone_wpm(zone_id: str | None = None, *, profile_name: str | None = None, kind: str = "heard") -> float:
    """The pace target of a zone; with no zone, the episode's time-weighted mean."""
    if kind not in ("heard", "speaking"):
        raise ValueError("kind is 'heard' or 'speaking'")
    prof = get_profile(profile_name or SR.T("BP-169", "default_profile"))
    key = f"{kind}_wpm_target"
    if zone_id is not None:
        for z in prof["zones"]:
            if z["id"] == zone_id:
                return float(z[key])
        raise KeyError(f"unknown zone {zone_id!r}")
    span = sum(z["window_s"][1] - z["window_s"][0] for z in prof["zones"])
    return sum(z[key] * (z["window_s"][1] - z["window_s"][0]) for z in prof["zones"]) / span


def words_to_seconds(words: int, *, t_start_s: float = 0.0, total_s: float = 720.0,
                     profile_name: str = "mrbeast_animated") -> float:
    """Seconds that ``words`` take when read at the heard pace of the zone they fall in, starting at t_start_s (a read that
    crosses a zone border changes pace at the border)."""
    if words < 0:
        raise ValueError("negative words")
    zones = _scaled(get_profile(profile_name), total_s)
    t, left = t_start_s, float(words)
    for lo, hi, z in zones:
        if t >= hi and z is not zones[-1][2]:
            continue
        wps = z["heard_wpm_target"] / 60.0
        room = (hi - max(t, lo)) * wps
        last = z is zones[-1][2]
        if left <= room or last:
            return t + left / wps - t_start_s
        t, left = hi, left - room
    return t - t_start_s
