"""Shot-card and map validators (final plan S4, W2): the lens, height, depth and angle rules of the shot-visuals and
cartography checklists. Input: shot cards (``continuity_card`` / the production script's shots) and map-step lists.

Card keys read: ``shot_id``, ``subject``, ``lens_tier`` (wide/normal/long or 24/50/85), ``lens_mm``, ``camera_height``
(low/eye/high), ``camera_spec.horizontal_azimuth_deg`` or ``azimuth_deg``, ``screen_composition`` {foreground, midground, background}.
"""
from __future__ import annotations

from explainer_engine.qa import gates as G
from explainer_engine.validators import _common as C

RULE_IDS = ("CRAFT-CART-02", "CRAFT-CART-06", "CRAFT-CIN-01", "CRAFT-CIN-02", "CRAFT-CIN-03", "CRAFT-CIN-06")
_TIER_NAMES = {"wide": 0, "normal": 1, "long": 2}
_HEIGHTS = ("low", "eye", "high")


def _tier_mm(card: dict):
    """The card's lens in mm: ``lens_mm``, a tier name mapped through BP-126's lens_tiers_mm, or a tier given as a number."""
    tiers = C.T("BP-126", "lens_tiers_mm")
    if card.get("lens_mm") is not None:
        return float(card["lens_mm"])
    t = card.get("lens_tier")
    if isinstance(t, (int, float)):
        return float(t)
    if isinstance(t, str) and t in _TIER_NAMES and tiers:
        return float(tiers[_TIER_NAMES[t]])
    return None


def lens_tier(cards: list[dict]) -> dict:
    """CRAFT-CIN-01 (critic): every card names a lens tier from BP-126's vocabulary; whether the beat motivates it is judged."""
    tiers = C.T("BP-126", "lens_tiers_mm") or []
    bad = [c.get("shot_id", "?") for c in cards
           if not (c.get("lens_tier") in _TIER_NAMES or (isinstance(c.get("lens_tier"), (int, float)) and c["lens_tier"] in tiers))]
    return C.critic("CRAFT-CIN-01", "BP-126", [f"lens_tier on {s}" for s in bad[:10]],
                    "the lens tier must be motivated by the beat (long = compression, wide = space)")


def camera_height(cards: list[dict]) -> dict:
    """CRAFT-CIN-02 (critic): camera height is low, eye or high on every card (BP-126); the motivation is judged."""
    bad = [c.get("shot_id", "?") for c in cards if c.get("camera_height") not in _HEIGHTS]
    return C.critic("CRAFT-CIN-02", "BP-126", [f"camera_height on {s}" for s in bad[:10]],
                    "low / eye / high must be motivated (low reads strong)")


def depth_staging(cards: list[dict]) -> dict:
    """CRAFT-CIN-06 (critic): foreground, midground and background are named on every card (KP-33)."""
    bad = []
    for c in cards:
        comp = c.get("screen_composition") or c.get("depth") or {}
        if not all(str(comp.get(k) or "").strip() for k in ("foreground", "midground", "background")):
            bad.append(c.get("shot_id", "?"))
    return C.critic("CRAFT-CIN-06", "KP-33", [f"foreground/midground/background on {s}" for s in bad[:10]],
                    "depth staging must be real, not named for the form")


def _azimuth(card: dict):
    v = (card.get("camera_spec") or {}).get("horizontal_azimuth_deg", card.get("azimuth_deg"))
    return None if v is None else float(v)


def angle_or_lens_change(cards: list[dict]) -> list[dict]:
    """CRAFT-CIN-03 (code, BP-126): two shots of one subject in a row change the angle by at least cut_angle_min_deg or the lens by
    at least lens_change_min_mm. One row per consecutive pair of one subject; a pair with no angle and no lens is NOT_RUN."""
    ang, mm = C.T("BP-126", "cut_angle_min_deg"), C.T("BP-126", "lens_change_min_mm")
    if ang is None or mm is None:
        return [C.missing_threshold("CRAFT-CIN-03", "BP-126", "cut_angle_min_deg/lens_change_min_mm")]
    rows = []
    for a, b in zip(cards, cards[1:]):
        subj = a.get("subject")
        if not subj or subj != b.get("subject"):
            continue
        gate = f"CRAFT-CIN-03:{a.get('shot_id', '?')}>{b.get('shot_id', '?')}"
        aa, ab, la, lb = _azimuth(a), _azimuth(b), _tier_mm(a), _tier_mm(b)
        d_ang = None if aa is None or ab is None else abs((ab - aa + 180) % 360 - 180)
        d_mm = None if la is None or lb is None else abs(lb - la)
        if d_ang is None and d_mm is None:
            rows.append(G.row(gate, None, "NOT_RUN: neither the angle nor the lens of both shots is on the cards"))
            continue
        ok = (d_ang is not None and d_ang >= ang) or (d_mm is not None and d_mm >= mm)
        rows.append(C.check(gate, ok, "BP-126", f"angle change {d_ang} deg (min {ang}), lens change {d_mm} mm (min {mm})",
                            {"angle_deg": d_ang, "lens_mm": d_mm}))
    return rows or [G.row("CRAFT-CIN-03", None, "NOT_RUN: no two consecutive shots of one subject")]


def map_steps(steps: list[dict]) -> dict:
    """CRAFT-CART-02 (critic): each map step lists what ``changed`` (at most BP-124's changes_at_once_max) and says
    ``highlight_before_move``."""
    most = C.T("BP-124", "changes_at_once_max")
    missing = [f"changed/highlight_before_move on step {i}" for i, s in enumerate(steps)
               if "changed" not in s or "highlight_before_move" not in s][:10]
    many = [i for i, s in enumerate(steps) if most is not None and len(s.get("changed") or []) > most]
    return C.critic("CRAFT-CART-02", "BP-124", missing,
                    f"one change at a time; the changed thing is highlighted before it moves"
                    + (f" (steps {many} change more than {most} thing at once)" if many else ""), {"too_many": many})


def map_plates(plates: dict) -> dict:
    """CRAFT-CART-06 (critic): ``projection`` and ``north_up`` are one per episode, a scale bar on every meso and micro plate, a legend
    only with more than two symbol classes."""
    miss = [k for k in ("projection", "north_up", "plates") if k not in plates]
    items = plates.get("plates") or []
    no_bar = [p.get("id", i) for i, p in enumerate(items) if p.get("scale") in ("meso", "micro") and not p.get("scale_bar")]
    bad_legend = [p.get("id", i) for i, p in enumerate(items) if p.get("legend") and int(p.get("symbol_classes") or 0) <= 2]
    note = "one projection and north-up per episode; a scale bar on every meso and micro map; a legend only above two symbol classes"
    if no_bar or bad_legend:
        note += f" (no scale bar: {no_bar}; legend without enough classes: {bad_legend})"
    return C.critic("CRAFT-CART-06", "-", miss, note, {"no_scale_bar": no_bar, "bad_legend": bad_legend})


def validate(cards: list[dict], *, map_step_list: list[dict] | None = None, map_plate_set: dict | None = None) -> list[dict]:
    rows = [lens_tier(cards), camera_height(cards), depth_staging(cards), *angle_or_lens_change(cards)]
    if map_step_list is not None:
        rows.append(map_steps(map_step_list))
    if map_plate_set is not None:
        rows.append(map_plates(map_plate_set))
    return rows
