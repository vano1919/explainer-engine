# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/maps/paths.py`
# Target Module : explainer_engine/maps/paths.py
# Target Classes/Symbols : def spline(), def length_km(), def validate(), def march_progress()
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

"""Terrain-aware routes (map law 2): a smooth curve through waypoints that stay on land and out of the no-go areas.

A route is a list of (lon, lat) waypoints, the crossings it is allowed to make (a ford, a bridge: a waypoint on a river is
listed in ``crossings``), the areas it must not enter (mountains, straits: rings of lon/lat given by the spec, because the
extract has no relief) and its ease. The curve is a Catmull-Rom spline sampled in lon/lat; ``validate`` walks it. Straight arrows
at constant speed across a mountain or a strait are the thing the law forbids, so a ``linear`` ease and a sample in water or in a
no-go ring are findings.
"""

from __future__ import annotations

from explainer_engine.maps import geo

EASES = ("march", "ease_in_out")  # "linear" exists only to be refused


def spline(waypoints: list[list[float]], per_segment: int = 24) -> list[tuple[float, float]]:
    """Catmull-Rom through the waypoints (uniform), ``per_segment`` samples between two of them; two waypoints give a straight line."""
    pts = [tuple(p) for p in waypoints]
    if len(pts) < 3:
        return [(pts[0][0] + (pts[-1][0] - pts[0][0]) * k / per_segment, pts[0][1] + (pts[-1][1] - pts[0][1]) * k / per_segment)
                for k in range(per_segment + 1)]
    ext = [pts[0]] + pts + [pts[-1]]
    out: list[tuple[float, float]] = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(per_segment):
            t = k / per_segment
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))  # type: ignore[arg-type]
    out.append((pts[-1][0], pts[-1][1]))
    return out


def length_km(curve: list[tuple[float, float]]) -> float:
    return sum(geo.distance_km(a[0], a[1], b[0], b[1]) for a, b in zip(curve, curve[1:]))


def validate(route: dict, rid: str = "route") -> list[dict]:
    """Law 2 on one route: eased (never linear), every sample on land and outside every no-go ring (REVIEW, CMP-02)."""
    out: list[dict] = []

    def add(detail: str) -> None:
        out.append({"rule": "CMP-02", "severity": "REVIEW", "where": rid, "detail": detail})

    if route.get("ease", "march") not in EASES:
        add(f"ease {route.get('ease')!r}: a march starts slow, cruises and halts at the line (never a constant-speed arrow)")
    wp = route["waypoints"]
    curve = spline(wp)
    wet = [i for i, (lon, lat) in enumerate(curve) if geo.is_water(lon, lat)]
    if wet:
        lon, lat = curve[wet[0]]
        add(f"{len(wet)} of {len(curve)} samples are in the sea or a lake (first at {lon:.2f}, {lat:.2f}): a route follows the land")
    for k, ring in enumerate(route.get("no_go", [])):
        bad = [i for i, (lon, lat) in enumerate(curve) if geo.point_in_ring(ring, lon, lat)]
        if bad:
            add(f"{len(bad)} samples are inside no-go area {k} (a range or a strait the route may not cross)")
    return out


def march_progress(route: dict, u: float) -> float:
    from explainer_engine.maps import draw as D
    return D.march(u) if route.get("ease", "march") == "march" else D.ease_in_out(u)
