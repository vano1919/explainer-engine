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
