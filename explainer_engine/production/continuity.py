# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/production/continuity.py`
# Target Module : explainer_engine/production/continuity.py
# Target Classes/Symbols : def start_state(), def end_state(), def _limit(), def chain(), def _direction(), def warp(), def findings()
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

"""Zoom continuity (ED-02): consecutive shots of the same picture continue one camera move instead of snapping back to the
default view. Each timed shot gets ``render_motion`` (what the assembler draws); the script's ``motion`` stays what the board
rules (UR-13) judge. State is (zoom, horizontal centre offset as a share of the picture width). ``findings`` also carries
BP-30 (docs/SOURCED_RULES.md): the same framing of the same picture twice in a row is a REVIEW; BP-92: a camera move never
resets (a run of shots on one picture never returns to its start framing, a turn comes to rest)."""
from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR

ZMAX = SR.T("BP-20", "scale_max")  # the camera never pushes past this on one picture (a punch accent stacks on top, exempt)
STEP = 0.04  # growth of a continued shot when the script gave none
TOL = 0.005
SAME_ZOOM = SR.T("BP-30", "same_framing_zoom_tol")  # BP-30: the same framing = zooms this close and crops within TOL


def start_state(m: dict) -> tuple[float, float]:
    x = m["x0"] if "x0" in m else -m.get("dx", 0.0) / 2
    return float(m["z0"]), float(x)


def end_state(m: dict) -> tuple[float, float]:
    x = m["x1"] if "x1" in m else m.get("dx", 0.0) / 2
    return float(m["z1"]), float(x)


def _limit(z: float) -> float:
    """Largest centre offset that keeps the crop inside the picture at zoom z."""
    return max(0.0, (1.0 - 1.0 / z) / 2)


def chain(shots: list[dict], zmax: float = ZMAX) -> list[dict]:
    """Set ``render_motion`` on every shot; a shot on the same picture as the one before starts where that one ended."""
    prev = None
    for s in shots:
        m = dict(s["motion"])
        if prev is not None and prev["picture"] == s["picture"]:
            z, x = end_state(prev["render_motion"])
            grow = max(STEP, float(m["z1"]) - float(m["z0"])) if m.get("kind") != "pull" else -abs(float(m["z1"]) - float(m["z0"]))
            if z >= zmax - 0.01 or grow < 0:  # past the cap: pull out by one step, never all the way back (BP-92)
                z1 = max(1.0, z - STEP) if grow >= 0 else max(1.0, z + max(grow, -STEP))
                x1 = x * (z1 - 1.0) / max(z - 1.0, 1e-6) if z > 1.0 else 0.0
            else:
                z1 = min(zmax, z + grow)
                x1 = x
            x1 = max(-_limit(z1), min(_limit(z1), x1))
            m = {"kind": "push" if z1 > z else "pull" if z1 < z else "static", "z0": round(z, 4), "z1": round(z1, 4),
                 "x0": round(max(-_limit(z), min(_limit(z), x)), 4), "x1": round(x1, 4), "chained": True}
        s["render_motion"] = m
        prev = s
    for a, b in zip(shots, shots[1:] + [None]):  # ED-08: the camera is at rest at every cut to another picture
        a["render_motion"]["ein"] = not a["render_motion"].get("chained", False)
        a["render_motion"]["eout"] = b is None or b["picture"] != a["picture"]
    for a, b in zip(shots, shots[1:]):  # BP-92: a move that turns back on one picture comes to rest at the turn
        if b["render_motion"].get("chained") and _direction(a["render_motion"]) * _direction(b["render_motion"]) < 0:
            a["render_motion"]["eout"] = b["render_motion"]["ein"] = True
    return shots


def _direction(m: dict) -> int:
    dz = float(m["z1"]) - float(m["z0"])
    return (dz > 1e-9) - (dz < -1e-9)


def warp(u: float, ein: bool, eout: bool) -> float:
    """Progress 0..1 of a move: eased (zero speed) at an end that meets a cut to another picture, linear where the move
    must carry on into the next shot of the same picture."""
    f = lambda v: v * v * (2 - v)  # noqa: E731  speed 0 at 0, speed 1 at 1
    if ein and eout:
        return u * u * (3 - 2 * u)
    if ein:
        return f(u)
    if eout:
        return 1 - f(1 - u)
    return u


def findings(shots: list[dict]) -> list[dict]:
    """ZOOM-1: the camera state at a cut inside one picture must be the same on both sides. BP-30: a shot that ends where the
    shot before it ended (same crop, zoom within SAME_ZOOM) shows the same framing of the same picture twice in a row."""
    out = []
    run_start = None
    for a, b in zip([None] + shots, shots):  # BP-92: a run of shots on one picture never comes back to where it started
        if "render_motion" not in b:
            run_start = None
            continue
        if a is None or a["picture"] != b["picture"] or "render_motion" not in a:
            run_start, moved = start_state(b["render_motion"]), False
        ze, xe = end_state(b["render_motion"])
        back = abs(ze - run_start[0]) < SAME_ZOOM and abs(xe - run_start[1]) <= TOL
        if moved and back:
            out.append({"rule": "BP-92", "severity": SR.rule("BP-92").get("severity", "REVIEW"), "where": b["id"],
                        "detail": f"the camera returns to the framing this picture's run started from (zoom {ze:.3f}): a "
                                  "reset; continue the move, or cut to another picture"})
        moved = moved or not back
    for a, b in zip(shots, shots[1:]):
        if a["picture"] != b["picture"] or "render_motion" not in a or "render_motion" not in b:
            continue
        za, xa = end_state(a["render_motion"])
        zb, xb = start_state(b["render_motion"])
        if abs(za - zb) > TOL or abs(xa - xb) > TOL:
            out.append({"rule": "ED-02 ZOOM-1", "severity": "FAIL", "where": b["id"],
                        "detail": f"zoom snaps from {za:.3f} to {zb:.3f} (offset {xa:.3f} to {xb:.3f}) on the same picture"})
            continue
        ze, xe = end_state(b["render_motion"])
        if abs(ze - za) < SAME_ZOOM and abs(xe - xa) <= TOL:
            out.append({"rule": "BP-30", "severity": SR.rule("BP-30").get("severity", "REVIEW"), "where": b["id"],
                        "detail": f"same framing twice in a row: {b['id']} ends at zoom {ze:.3f} where {a['id']} ended "
                                  f"({za:.3f}) on the same picture; a cut changes the shot size by a full step"})
    return out
