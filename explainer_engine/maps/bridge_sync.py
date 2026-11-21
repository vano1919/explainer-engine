"""Provisional bridge sync checks behind an env flag (QUALITY_SPEC.md section 3 (B1–B5), provisional).

Pure numeric checks; no image libraries, no rendering, no network; the numbers await owner approval.
"""

from __future__ import annotations

from explainer_engine.maps.quality_provisional import ENV_VAR, enabled

# provisional, owner approves on rendered samples
BRIDGE_ONSET_TOL_FRAMES = 1
BRIDGE_CAP_HEIGHT_MIN_PCT = 8.0
BRIDGE_HOLD_MIN_S = 1.0

NOT_FOUND_PROBLEM = "bridge text not found in narration"
NO_TIMING_PROBLEM = "no word timing for bridge: rejected, never placed by estimate"


def normalize(token: str) -> str:
    """Lowercase the token and keep only letters and digits, so case and punctuation cannot break a match."""
    return "".join(ch for ch in str(token).lower() if ch.isalnum())


def _normalized_words(words: list[dict]) -> list[str]:
    return [normalize(item.get("word", "")) for item in words]


def _timing(value) -> float | None:
    """Coerce a timing value to float; a missing key or None means there is no timing (fail closed)."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def find_bridge(words: list[dict], bridge_text: str) -> tuple[int, int] | None:
    """Index range (inclusive start, inclusive end) of the first occurrence of the bridge word sequence; else None."""
    target = [part for part in (normalize(token) for token in str(bridge_text).split()) if part]
    if not target:
        return None
    tokens = _normalized_words(words)
    for start in range(0, len(tokens) - len(target) + 1):
        if tokens[start:start + len(target)] == target:
            return start, start + len(target) - 1
    return None


def bridge_window(words: list[dict], bridge_text: str) -> dict:
    """Onset of the first matched word and end of the last matched word; fail closed when timing is missing."""
    found = find_bridge(words, bridge_text)
    if found is None:
        return {"ok": False, "problems": [NOT_FOUND_PROBLEM]}
    start, end = found
    for index in range(start, end + 1):
        if _timing(words[index].get("start_s")) is None or _timing(words[index].get("end_s")) is None:
            return {"ok": False, "problems": [NO_TIMING_PROBLEM]}
    return {
        "ok": True,
        "onset_s": _timing(words[start].get("start_s")),
        "hold_end_s": _timing(words[end].get("end_s")),
        "problems": [],
    }


def check_onset(
    first_visible_s: float,
    first_word_start_s: float,
    fps: float,
    tol_frames: int = BRIDGE_ONSET_TOL_FRAMES,
) -> list[str]:
    """Onset check (T6): the bridge must appear within ``tol_frames`` of the first bridge word being spoken."""
    if fps <= 0:
        raise ValueError("fps must be greater than 0")
    tolerance_s = tol_frames / float(fps)
    delta_s = abs(float(first_visible_s) - float(first_word_start_s))
    if delta_s > tolerance_s:
        return [
            f"bridge onset is {delta_s:.3f}s from the first word of the bridge, above the provisional tolerance "
            f"of {tolerance_s:.3f}s ({tol_frames} frame(s) at {fps} fps)"
        ]
    return []


def check_hold(
    visible_end_s: float,
    hold_end_s: float,
    visible_start_s: float,
    min_hold_s: float = BRIDGE_HOLD_MIN_S,
) -> list[str]:
    """Hold checks (T8): the bridge must survive its last word and stay on screen for the minimum hold."""
    problems: list[str] = []
    if visible_end_s < hold_end_s:
        problems.append(
            f"bridge disappears at {visible_end_s:.2f}s before the last bridge word ends at {hold_end_s:.2f}s"
        )
    duration_s = float(visible_end_s) - float(visible_start_s)
    if duration_s < min_hold_s:
        problems.append(
            f"bridge visible for {duration_s:.2f}s, below the provisional minimum hold of {min_hold_s:.2f}s"
        )
    return problems


def check_cap_height(cap_height_pct: float, minimum: float = BRIDGE_CAP_HEIGHT_MIN_PCT) -> list[str]:
    """Cap height check (T7): bridge text below the provisional minimum percent of frame height."""
    if cap_height_pct < minimum:
        return [
            f"bridge cap height {cap_height_pct:.2f}% is below the provisional minimum "
            f"{minimum:.1f}% of frame height"
        ]
    return []


def bridge_problems(
    words: list[dict],
    bridge_text: str,
    first_visible_s: float,
    visible_end_s: float,
    fps: float,
    cap_height_pct: float,
) -> list[str]:
    """Run all provisional bridge checks. Returns [] when the flag is off."""
    if not enabled():
        return []
    window = bridge_window(words, bridge_text)
    if not window["ok"]:
        return list(window["problems"])
    problems: list[str] = []
    problems.extend(check_onset(first_visible_s, window["onset_s"], fps))
    problems.extend(check_hold(visible_end_s, window["hold_end_s"], first_visible_s))
    problems.extend(check_cap_height(cap_height_pct))
    return problems
