"""Zoom continuity (ED-02): consecutive shots of the same picture continue one camera move instead of snapping back to the
default view. Each timed shot gets ``render_motion`` (what the assembler draws); the script's ``motion`` stays what the board
rules (UR-13) judge. State is (zoom, horizontal centre offset as a share of the picture width)."""
from __future__ import annotations

ZMAX = 1.25  # the camera never pushes past this on one picture
STEP = 0.04  # growth of a continued shot when the script gave none
TOL = 0.005


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
            if z >= zmax - 0.01 or grow < 0:
                z1 = 1.0 if grow >= 0 else max(1.0, z + grow)  # past the cap: ease all the way out, never jump
                x1 = x * (z1 - 1.0) / max(z - 1.0, 1e-6) if z > 1.0 else 0.0
            else:
                z1 = min(zmax, z + grow)
                x1 = x
            x1 = max(-_limit(z1), min(_limit(z1), x1))
            m = {"kind": "push" if z1 > z else "pull" if z1 < z else "static", "z0": round(z, 4), "z1": round(z1, 4),
                 "x0": round(max(-_limit(z), min(_limit(z), x)), 4), "x1": round(x1, 4), "chained": True}
        s["render_motion"] = m
        prev = s
    return shots


def findings(shots: list[dict]) -> list[dict]:
    """ZOOM-1: the camera state at a cut inside one picture must be the same on both sides."""
    out = []
    for a, b in zip(shots, shots[1:]):
        if a["picture"] != b["picture"] or "render_motion" not in a or "render_motion" not in b:
            continue
        za, xa = end_state(a["render_motion"])
        zb, xb = start_state(b["render_motion"])
        if abs(za - zb) > TOL or abs(xa - xb) > TOL:
            out.append({"rule": "ED-02 ZOOM-1", "severity": "FAIL", "where": b["id"],
                        "detail": f"zoom snaps from {za:.3f} to {zb:.3f} (offset {xa:.3f} to {xb:.3f}) on the same picture"})
    return out
