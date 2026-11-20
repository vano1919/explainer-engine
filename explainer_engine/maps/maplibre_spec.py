"""Shot specification validation, animation schedule, and label-free style utilities (G-04c)."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
from typing import Any
REQUIRED_SPEC_KEYS: tuple[str, ...] = (
    "size",
    "fps",
    "seconds",
    "center",
    "zoom",
    "line_geojson",
    "line_t",
    "counter",
    "date_chip",
    "towns",
    "footnote",
)
ALLOWED_CAMERA_MOVES: tuple[str, ...] = (
    "truck",
    "zoom_in",
    "zoom_out",
    "truck_zoom_in",
    "truck_zoom_out",
)
FORBIDDEN_CAMERA_KEYS: tuple[str, ...] = ("bearing", "pitch", "rotation", "roll", "orbit")


class ShotSpecError(Exception):
    """Raised when a shot specification file cannot be parsed or fails validation."""
def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
def _is_sequence_not_str(value: Any) -> bool:
    return isinstance(value, (list, tuple))
def _is_lonlat(value: Any) -> bool:
    return (
        _is_sequence_not_str(value)
        and len(value) == 2
        and _is_number(value[0])
        and _is_number(value[1])
    )
def _validate_camera_block(camera: Any, problems: list[str]) -> None:
    """Validate optional 'camera' configuration block and append problem strings."""
    if not isinstance(camera, dict):
        problems.append("camera must be a dict")
        return
    for forbidden in FORBIDDEN_CAMERA_KEYS:
        if forbidden in camera:
            problems.append(f"camera must not carry {forbidden!r} (no rotation, tilt or orbit, owner 2026-11-20)")
    move = camera.get("move")
    if not isinstance(move, str) or move not in ALLOWED_CAMERA_MOVES:
        problems.append(
            f"camera 'move' must be one of {', '.join(ALLOWED_CAMERA_MOVES)}; got {move!r}"
        )
        return
    if "ease" in camera and camera["ease"] != "smoothstep":
        problems.append("camera 'ease' must be 'smoothstep'")
    needs_center = move in ("truck", "truck_zoom_in", "truck_zoom_out")
    needs_zoom = move in ("zoom_in", "zoom_out", "truck_zoom_in", "truck_zoom_out")
    if needs_center:
        if "center_from" not in camera or not _is_lonlat(camera["center_from"]):
            problems.append("camera 'center_from' must be a 2-element sequence of numbers [lon, lat]")
        if "center_to" not in camera or not _is_lonlat(camera["center_to"]):
            problems.append("camera 'center_to' must be a 2-element sequence of numbers [lon, lat]")
        if (
            "center_from" in camera
            and "center_to" in camera
            and _is_lonlat(camera["center_from"])
            and _is_lonlat(camera["center_to"])
            and float(camera["center_from"][0]) == float(camera["center_to"][0])
            and float(camera["center_from"][1]) == float(camera["center_to"][1])
        ):
            problems.append("camera 'center_from' and 'center_to' must differ for truck moves")
    else:
        if "center_from" in camera and not _is_lonlat(camera["center_from"]):
            problems.append("camera 'center_from' must be a 2-element sequence of numbers [lon, lat]")
        if "center_to" in camera and not _is_lonlat(camera["center_to"]):
            problems.append("camera 'center_to' must be a 2-element sequence of numbers [lon, lat]")
    if needs_zoom:
        if "zoom_from" not in camera or not _is_number(camera["zoom_from"]):
            problems.append("camera 'zoom_from' must be a number")
        if "zoom_to" not in camera or not _is_number(camera["zoom_to"]):
            problems.append("camera 'zoom_to' must be a number")
        if (
            "zoom_from" in camera
            and "zoom_to" in camera
            and _is_number(camera["zoom_from"])
            and _is_number(camera["zoom_to"])
        ):
            z_from = float(camera["zoom_from"])
            z_to = float(camera["zoom_to"])
            if move in ("zoom_in", "truck_zoom_in") and not (z_to > z_from):
                problems.append("camera 'zoom_to' must be greater than 'zoom_from' for zoom_in moves")
            elif move in ("zoom_out", "truck_zoom_out") and not (z_to < z_from):
                problems.append("camera 'zoom_to' must be less than 'zoom_from' for zoom_out moves")
    else:
        if "zoom_from" in camera and not _is_number(camera["zoom_from"]):
            problems.append("camera 'zoom_from' must be a number")
        if "zoom_to" in camera and not _is_number(camera["zoom_to"]):
            problems.append("camera 'zoom_to' must be a number")
def validate_shot_spec(spec: Any) -> list[str]:
    """Validate a shot specification dict and return a list of human-readable problem strings."""
    if not isinstance(spec, dict):
        return ["spec must be a dict"]
    problems: list[str] = []
    for key in REQUIRED_SPEC_KEYS:
        if key not in spec:
            problems.append(f"missing required key: {key}")
    if "size" in spec:
        size = spec["size"]
        if (
            not _is_sequence_not_str(size)
            or len(size) != 2
            or not _is_positive_int(size[0])
            or not _is_positive_int(size[1])
        ):
            problems.append("size must be a 2-element sequence of positive integers [width, height]")
    if "fps" in spec:
        fps = spec["fps"]
        if not _is_number(fps) or fps <= 0:
            problems.append("fps must be a positive number")
    if "seconds" in spec:
        seconds = spec["seconds"]
        if not _is_number(seconds) or seconds <= 0:
            problems.append("seconds must be a positive number")
    if "center" in spec:
        if not _is_lonlat(spec["center"]):
            problems.append("center must be a 2-element sequence of numbers [lon, lat]")
    if "zoom" in spec:
        if not _is_number(spec["zoom"]):
            problems.append("zoom must be a number")
    if "camera" in spec and spec["camera"] is not None:
        _validate_camera_block(spec["camera"], problems)
    if "line_geojson" in spec:
        line_geojson = spec["line_geojson"]
        if not isinstance(line_geojson, str) or not line_geojson:
            problems.append("line_geojson must be a non-empty string")
    if "line_t" in spec:
        line_t = spec["line_t"]
        if (
            not _is_sequence_not_str(line_t)
            or len(line_t) != 2
            or not _is_number(line_t[0])
            or not _is_number(line_t[1])
            or not (line_t[0] < line_t[1])
        ):
            problems.append("line_t must be a 2-element sequence [t0, t1] of numbers with t0 < t1")
    if "counter" in spec:
        counter = spec["counter"]
        if not isinstance(counter, dict):
            problems.append("counter must be a dict")
        else:
            required_counter_keys = ("from", "to", "t0", "t1", "label")
            missing_counter = [k for k in required_counter_keys if k not in counter]
            if missing_counter:
                problems.append(f"counter missing required keys: {', '.join(missing_counter)}")
            else:
                c_from = counter["from"]
                c_to = counter["to"]
                c_t0 = counter["t0"]
                c_t1 = counter["t1"]
                c_label = counter["label"]
                if not _is_number(c_from) or not _is_number(c_to):
                    problems.append("counter 'from' and 'to' must be numbers")
                if not _is_number(c_t0) or not _is_number(c_t1) or not (c_t0 < c_t1):
                    problems.append("counter 't0' and 't1' must be numbers with t0 < t1")
                if not isinstance(c_label, str):
                    problems.append("counter 'label' must be a string")
    if "date_chip" in spec:
        date_chip = spec["date_chip"]
        if not isinstance(date_chip, list):
            problems.append("date_chip must be a list of {t, text} objects")
        else:
            for idx, item in enumerate(date_chip):
                if (
                    not isinstance(item, dict)
                    or "t" not in item
                    or "text" not in item
                    or not _is_number(item["t"])
                    or not isinstance(item["text"], str)
                ):
                    problems.append(f"date_chip[{idx}] must be a dict with numeric 't' and string 'text'")
    if "towns" in spec:
        towns = spec["towns"]
        if not isinstance(towns, list):
            problems.append("towns must be a list of {name, lonlat, t} objects")
        else:
            for idx, town in enumerate(towns):
                if (
                    not isinstance(town, dict)
                    or "name" not in town
                    or "lonlat" not in town
                    or "t" not in town
                    or not isinstance(town["name"], str)
                    or not _is_lonlat(town["lonlat"])
                    or not _is_number(town["t"])
                ):
                    problems.append(
                        f"towns[{idx}] must be a dict with string 'name', 2-number 'lonlat', and numeric 't'"
                    )
    if "style_preset" in spec and (not isinstance(spec["style_preset"], str) or not spec["style_preset"]):
        problems.append("style_preset must be a non-empty string (name of maplibre_lane/styles/<name>.json)")
    if "film_file" in spec and (not isinstance(spec["film_file"], str) or not spec["film_file"]):
        problems.append("film_file must be a non-empty string")
    if "font" in spec:
        font = spec["font"]
        if not isinstance(font, str) or not font:
            problems.append("font must be a non-empty string")
    if "footnote" in spec:
        if not isinstance(spec["footnote"], str):
            problems.append("footnote must be a string")
    return problems
def load_shot_spec(path: str | Path) -> dict[str, Any]:
    """Load a JSON shot specification from `path` and validate it, raising ShotSpecError on failure."""
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, ValueError) as exc:  # ValueError: JSONDecodeError and UnicodeDecodeError
        raise ShotSpecError(f"Failed to read or parse shot spec {path!s}: {exc}") from exc
    problems = validate_shot_spec(data)
    if problems:
        raise ShotSpecError(f"Invalid shot spec in {path!s}: {'; '.join(problems)}")
    return data
def ease_smoothstep(u: float) -> float:
    """Clamped cubic Hermite smoothstep interpolation over [0, 1]."""
    clamped = min(1.0, max(0.0, float(u)))
    return clamped * clamped * (3.0 - 2.0 * clamped)
def frame_count(spec: dict[str, Any]) -> int:
    """Return total integer frame count round(fps * seconds) for `spec`."""
    return int(round(float(spec["fps"]) * float(spec["seconds"])))
def camera_state(spec: dict[str, Any], frame: int) -> dict[str, Any]:
    """Compute camera center (lon, lat) and zoom at integer `frame` eased with ease_smoothstep."""
    base_center = (float(spec["center"][0]), float(spec["center"][1]))
    base_zoom = float(spec["zoom"])
    camera = spec.get("camera")
    if not isinstance(camera, dict):
        return {
            "center": base_center,
            "zoom": base_zoom,
        }
    total_frames = frame_count(spec)
    if total_frames <= 1:
        raw_u = 1.0
    else:
        raw_u = float(frame) / float(total_frames - 1)
    u = ease_smoothstep(raw_u)
    move = camera.get("move")
    has_truck = move in ("truck", "truck_zoom_in", "truck_zoom_out")
    has_zoom = move in ("zoom_in", "zoom_out", "truck_zoom_in", "truck_zoom_out")
    if has_truck and "center_from" in camera and "center_to" in camera:
        c0_lon, c0_lat = float(camera["center_from"][0]), float(camera["center_from"][1])
        c1_lon, c1_lat = float(camera["center_to"][0]), float(camera["center_to"][1])
        center = (
            c0_lon + (c1_lon - c0_lon) * u,
            c0_lat + (c1_lat - c0_lat) * u,
        )
    else:
        center = base_center
    if has_zoom and "zoom_from" in camera and "zoom_to" in camera:
        z0 = float(camera["zoom_from"])
        z1 = float(camera["zoom_to"])
        zoom = z0 + (z1 - z0) * u
    else:
        zoom = base_zoom
    return {
        "center": center,
        "zoom": zoom,
    }
def schedule(spec: dict[str, Any], frame: int) -> dict[str, Any]:
    """Compute animation state at integer `frame` without mutating `spec`."""
    fps = float(spec["fps"])
    t = float(frame) / fps
    line_t0, line_t1 = float(spec["line_t"][0]), float(spec["line_t"][1])
    raw_line_u = (t - line_t0) / (line_t1 - line_t0)
    line_u = ease_smoothstep(raw_line_u)
    counter_spec = spec["counter"]
    c_from = float(counter_spec["from"])
    c_to = float(counter_spec["to"])
    c_t0 = float(counter_spec["t0"])
    c_t1 = float(counter_spec["t1"])
    raw_counter_u = (t - c_t0) / (c_t1 - c_t0)
    eased_counter_u = ease_smoothstep(raw_counter_u)
    counter_val = int(round(c_from + (c_to - c_from) * eased_counter_u))
    current_date = ""
    for chip in sorted(spec["date_chip"], key=lambda c: float(c["t"])):
        if float(chip["t"]) <= t:
            current_date = chip["text"]
    towns_visible = [
        town["name"]
        for town in spec["towns"]
        if t >= float(town["t"])
    ]
    return {
        "t": t,
        "line_u": line_u,
        "counter": counter_val,
        "date": current_date,
        "towns_visible": towns_visible,
    }
def strip_labels(style: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of a MapLibre style dict with all 'symbol' layers removed."""
    cleaned = copy.deepcopy(style)
    if isinstance(cleaned.get("layers"), list):
        cleaned["layers"] = [
            layer
            for layer in cleaned["layers"]
            if not (isinstance(layer, dict) and layer.get("type") == "symbol")
        ]
    return cleaned
def offline_tile_url(tile_dir: str | Path, kind: str) -> str:
    """Return an offline file:// XYZ tile URL template for 'vector' (.pbf) or 'dem' (.png)."""
    extensions = {"vector": "pbf", "dem": "png"}
    if kind not in extensions:
        raise ValueError(f"Unsupported offline tile kind: {kind!r}; expected 'vector' or 'dem'")
    abs_dir = Path(tile_dir).resolve().as_posix().rstrip("/")
    return f"file://{abs_dir}/{{z}}/{{x}}/{{y}}.{extensions[kind]}"
