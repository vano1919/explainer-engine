"""blender_scene/1: the scene spec of a Blender layout clip, its geometry and the validators V1-V9 (pure Python).

One clip = one place, people with tracks, cameras and cuts, 241 frames at 24 fps (10.0 s of time, frames 0..240).
A cut spans the frames [frame_in, frame_out); the last cut also owns the final frame. Units are metres, a heading is a
compass angle (0 faces +y, 90 faces +x), a pitch above 0 looks up. Nothing here needs Blender: the per-view pixel numbers
come from a pinhole projection that ``scene_render`` cross-checks against Blender's own camera after the render.

Status of each validator: ``FAIL`` blocks (a hard format limit or the creator's rule), ``REVIEW`` marks a hypothesis
threshold taken from the blocking note (docs/BLENDER_SCENE.md): it asks the creator to look and never silently passes.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "blender_scene_1.schema.json"
FILM_STYLE_DIR = Path(__file__).resolve().parent / "film_styles"
PLACES = ("british_trench", "no_mans_land", "german_trench")
FPS = 24
CLIP_FRAMES = 241                     # 8k+1 (LTX frame rule), 10.04 s of playback, frames 0..240
LENSES_ALLOWED = (28, 35, 50, 85)     # plan v5 section 4 item 3
SENSOR_WIDTH_MM = 36.0
PERSON_HEIGHT = 1.75
HEAD_FRACTION = 0.24 / 1.75           # head marker height over body height (blender_blocking._person)
BODY_RADIUS = 0.18
VIEW_MAX_S, VIEW_MIN_S = 2.0, 0.8     # creator's rule: a view is at most 2 s; plan v5 section 3: at least 0.8 s
SIZE_MULTIPLE = 64                    # LTX size rule
MIN_FOCUS_HEIGHT_FRAC = 250 / 1080    # V1 hypothesis (REVIEW): a face reads when the person is ~250 px at 1080 p
MAX_OVERLAP = 0.25                    # V2 hypothesis (REVIEW): share of the smaller person's box that is covered
MAX_WALK_SPEED = 2.5                  # V4 hypothesis (REVIEW), m/s: a fast walk, anything more is a run
TAIL_SECONDS, TAIL_MAX_MOVE = 0.75, 0.05   # V9 (plan 3a): the last 0.75 s are calm; metres a person may move in them
LAST_VIEW_MIN_S = 1.0                 # V9
CHAIN_POS_TOL = 0.05                  # V8, metres
MOVING_SAMPLE_EVERY = 12              # V1/V2 look every half second while the camera moves


class SceneSpecError(ValueError):
    pass


def load_spec(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    check_schema(spec)
    return spec


def check_schema(spec: dict) -> None:
    import jsonschema  # noqa: PLC0415
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(spec), key=lambda e: list(e.path))
    if errors:
        raise SceneSpecError("; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors[:8]))


# ------------------------------------------------------------------------------------------------ geometry

def _lerp(a, b, t):
    return a + (b - a) * t


def person_state(person: dict, frame: float) -> dict:
    """Position/heading/height by linear interpolation between track keys; the pose is the latest key's pose."""
    keys = sorted(person["track"], key=lambda k: k["frame"])
    prev = keys[0]
    for k in keys:
        if k["frame"] <= frame:
            prev = k
    nxt = next((k for k in keys if k["frame"] > frame), None)
    if nxt is None or nxt["frame"] == prev["frame"] or frame <= prev["frame"]:
        base, t, other = prev, 0.0, prev
    else:
        base, other = prev, nxt
        t = (frame - prev["frame"]) / (nxt["frame"] - prev["frame"])
    return {
        "pos": [_lerp(base["pos"][i], other["pos"][i], t) for i in (0, 1)],
        "heading": _lerp(base["heading"], other["heading"], t),
        "z": _lerp(base.get("z", 0.0), other.get("z", 0.0), t),
        "pose": prev.get("pose", "stand"),
    }


def cut_of(spec: dict, frame: int) -> dict:
    cuts = spec["cuts"]
    for c in cuts:
        if c["frame_in"] <= frame < c["frame_out"]:
            return c
    return cuts[-1]


def camera_by_id(spec: dict, cam_id: str) -> dict:
    return next(c for c in spec["cameras"] if c["id"] == cam_id)


def cam_start(cam: dict) -> dict:
    """The camera's first pose: its own fields, or the first key of its path (version 2)."""
    path = cam.get("path")
    return min(path, key=lambda k: k["frame"]) if path else cam


def _ease(t: float, kind: str) -> float:
    if kind == "in_out":
        return t * t * (3 - 2 * t)
    if kind == "out":                    # fast start, comes to rest at the key: the way a camera stops
        return 1 - (1 - t) ** 2
    if kind == "in":
        return t * t
    return t


def path_state(cam: dict, frame: float) -> dict:
    """Camera pose on its path (``cameras[].path``, version 2): linear between keys, or the ease named on the key
    the segment starts at (``in_out``, ``out``, ``in``); before the first key and after the last it holds."""
    keys = sorted(cam["path"], key=lambda k: k["frame"])
    if frame <= keys[0]["frame"]:
        a = b = keys[0]
        t = 0.0
    elif frame >= keys[-1]["frame"]:
        a = b = keys[-1]
        t = 0.0
    else:
        a = max((k for k in keys if k["frame"] <= frame), key=lambda k: k["frame"])
        b = next(k for k in keys if k["frame"] > a["frame"])
        t = _ease((frame - a["frame"]) / (b["frame"] - a["frame"]), a.get("ease", "linear"))
    return {"pos": [_lerp(a["pos"][i], b["pos"][i], t) for i in range(3)],
            "heading": _lerp(a["heading"], b["heading"], t), "pitch": _lerp(a["pitch"], b["pitch"], t),
            "lens": _lerp(a["lens"], b["lens"], t)}


def camera_state(spec: dict, cut: dict, frame: float) -> dict:
    cam = camera_by_id(spec, cut["camera"])
    if cam.get("path"):
        return path_state(cam, frame)
    move = cam.get("move")
    t = 0.0
    if move and cut["frame_out"] > cut["frame_in"]:
        t = min(1.0, max(0.0, (frame - cut["frame_in"]) / (cut["frame_out"] - cut["frame_in"])))
    tgt = move or {}
    return {
        "pos": [_lerp(cam["pos"][i], tgt.get("pos", cam["pos"])[i], t) for i in range(3)],
        "heading": _lerp(cam["heading"], tgt.get("heading", cam["heading"]), t),
        "pitch": _lerp(cam["pitch"], tgt.get("pitch", cam["pitch"]), t),
        "lens": cam["lens"],
    }


def project(cam: dict, size: tuple[int, int], point: tuple[float, float, float]):
    """Pinhole projection that matches Blender (sensor 36 mm horizontal fit). Returns (x_px, y_px, depth_m)."""
    h, p = math.radians(cam["heading"]), math.radians(cam["pitch"])
    f = (math.sin(h) * math.cos(p), math.cos(h) * math.cos(p), math.sin(p))
    r = (math.cos(h), -math.sin(h), 0.0)
    u = (-math.sin(h) * math.sin(p), -math.cos(h) * math.sin(p), math.cos(p))
    d = [point[i] - cam["pos"][i] for i in range(3)]
    depth = sum(d[i] * f[i] for i in range(3))
    if depth <= 0.01:
        return None
    focal = cam["lens"] / SENSOR_WIDTH_MM * size[0]
    x = size[0] / 2 + focal * sum(d[i] * r[i] for i in range(3)) / depth
    y = size[1] / 2 - focal * sum(d[i] * u[i] for i in range(3)) / depth
    return x, y, depth


def measure_person(cam: dict, size: tuple[int, int], st: dict) -> dict:
    """Where a person lands in the picture: box, height, head height, whether the head and the middle are in frame."""
    x, y = st["pos"]
    feet = project(cam, size, (x, y, st["z"]))
    top = project(cam, size, (x, y, st["z"] + PERSON_HEIGHT))
    if feet is None or top is None:
        return {"visible": False, "height_px": 0, "head_px": 0, "box": [0, 0, 0, 0], "in_frame": False}
    height = abs(feet[1] - top[1])
    half_w = BODY_RADIUS * cam["lens"] / SENSOR_WIDTH_MM * size[0] / feet[2]
    box = [feet[0] - half_w, top[1], feet[0] + half_w, feet[1]]
    in_frame = 0 <= feet[0] <= size[0] and 0 <= top[1] <= size[1] and 0 <= top[0] <= size[0]
    return {"visible": True, "height_px": round(height, 1), "head_px": round(height * HEAD_FRACTION, 1),
            "feet_px": [round(feet[0], 1), round(feet[1], 1)], "depth_m": round(feet[2], 2),
            "box": [round(v, 1) for v in box], "in_frame": bool(in_frame)}


def camera_moves(spec: dict, cut: dict) -> bool:
    a, b = cut["frame_in"], max(cut["frame_out"] - 1, cut["frame_in"])
    return camera_state(spec, cut, a) != camera_state(spec, cut, b)


def sample_frames(cut: dict, every: int | None = None) -> list[int]:
    a, b = cut["frame_in"], cut["frame_out"]
    base = {a, (a + b) // 2, b - 1 if b > a else a}
    if every:
        base |= set(range(a, b, every))
    return sorted(base)


def measure_cut(spec: dict, cut: dict) -> list[dict]:
    size = tuple(spec["size"])
    out = []
    for fr in sample_frames(cut, MOVING_SAMPLE_EVERY if camera_moves(spec, cut) else None):
        cam = camera_state(spec, cut, fr)
        people = {p["id"]: measure_person(cam, size, person_state(p, fr)) for p in spec["people"]}
        out.append({"frame": fr, "people": people})
    return out


def _overlap(a: list[float], b: list[float]) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return w * h / smaller if smaller > 0 else 0.0


# ------------------------------------------------------------------------------------------------ validators

def _res(vid: str, status: str, message: str, **extra) -> dict:
    return {"id": vid, "status": status, "message": message, **extra}


def _structure(spec: dict) -> list[dict]:
    """Cuts must tile the clip, ids must resolve; without these nothing else is meaningful."""
    out, ids = [], {p["id"] for p in spec["people"]}
    cams = {c["id"] for c in spec["cameras"]}
    cuts = spec["cuts"]
    if cuts[0]["frame_in"] != 0:
        out.append(_res("STRUCT", "FAIL", f"first cut starts at {cuts[0]['frame_in']}, not 0"))
    for a, b in zip(cuts, cuts[1:]):
        if a["frame_out"] != b["frame_in"]:
            out.append(_res("STRUCT", "FAIL", f"cuts do not touch: {a['frame_out']} then {b['frame_in']}"))
    if cuts[-1]["frame_out"] != spec["clip_frames"] - 1:
        out.append(_res("STRUCT", "FAIL", f"last cut ends at {cuts[-1]['frame_out']}, clip last frame is "
                                          f"{spec['clip_frames'] - 1}"))
    for c in cuts:
        if c["camera"] not in cams:
            out.append(_res("STRUCT", "FAIL", f"cut uses unknown camera {c['camera']}"))
        for pid in c["focus"]:
            if pid not in ids:
                out.append(_res("STRUCT", "FAIL", f"focus names unknown person {pid}"))
    for p in spec["people"]:
        if p["track"] and min(k["frame"] for k in p["track"]) != 0:
            out.append(_res("STRUCT", "FAIL", f"{p['id']}: track does not start at frame 0"))
    return out


def validate_spec(spec: dict) -> list[dict]:
    """V3-V6 (spec only) plus V4, V9 and the structure; the pixel validators V1/V2 run on the same spec."""
    res = _structure(spec)
    if res:
        return res
    size = tuple(spec["size"])
    fps = spec["fps"]
    # V3 view length
    def _secs(c):
        return (c["frame_out"] - c["frame_in"]) / fps
    takes = [(c["camera"], _secs(c)) for c in spec["cuts"] if c.get("long_take") and _secs(c) > VIEW_MAX_S + 1e-9]
    bad = [(c["camera"], _secs(c)) for c in spec["cuts"]
           if not VIEW_MIN_S - 1e-9 <= _secs(c) <= VIEW_MAX_S + 1e-9 and not (c.get("long_take") and _secs(c) > VIEW_MAX_S)]
    if bad:
        res.append(_res("V3", "FAIL", f"view length out of {VIEW_MIN_S}-{VIEW_MAX_S} s: {bad}"))
    elif takes:     # the creator's 2.0 s rule is broken on purpose: it must be seen, never silently passed
        res.append(_res("V3", "REVIEW", f"declared long take(s) longer than {VIEW_MAX_S} s (creator's rule, exception "
                                        f"needs his look): {takes}"))
    else:
        res.append(_res("V3", "PASS", f"{len(spec['cuts'])} views, each {VIEW_MIN_S}-{VIEW_MAX_S} s"))
    # V4 static people stay, speed limit
    problems, fast = [], []
    for p in spec["people"]:
        keys = sorted(p["track"], key=lambda k: k["frame"])
        if p.get("static") and any((k["pos"], k["heading"]) != (keys[0]["pos"], keys[0]["heading"]) for k in keys):
            problems.append(f"{p['id']} is static but its track moves")
        for a, b in zip(keys, keys[1:]):
            dist = math.dist(a["pos"], b["pos"])
            secs = (b["frame"] - a["frame"]) / fps
            if secs > 0 and dist / secs > MAX_WALK_SPEED:
                fast.append(f"{p['id']} {dist / secs:.1f} m/s")
    if problems:
        res.append(_res("V4", "FAIL", "; ".join(problems)))
    elif fast:
        res.append(_res("V4", "REVIEW", f"faster than a walk ({MAX_WALK_SPEED} m/s, hypothesis): {fast}"))
    else:
        res.append(_res("V4", "PASS", "static people stay, nobody moves faster than a walk"))
    # V5 lenses
    res.append(validate_camera(spec))
    # V6 frame count and size rules
    issues = []
    if (spec["clip_frames"] - 1) % 8:
        issues.append(f"clip_frames {spec['clip_frames']} is not 8k+1")
    if spec["clip_frames"] != CLIP_FRAMES:
        issues.append(f"clip_frames {spec['clip_frames']} is not {CLIP_FRAMES}")
    if size[0] % SIZE_MULTIPLE or size[1] % SIZE_MULTIPLE:
        issues.append(f"size {size} not divisible by {SIZE_MULTIPLE}")
    res.append(_res("V6", "FAIL", "; ".join(issues)) if issues else
               _res("V6", "PASS", f"{spec['clip_frames']} frames (8k+1), size {size[0]}x{size[1]} divisible by 64"))
    res += validate_pixels(spec)
    res.append(validate_tail(spec))
    res += validate_transitions(spec)
    return res


def validate_pixels(spec: dict) -> list[dict]:
    """V1 (focus people tall enough and in frame) and V2 (people do not hide each other), on first/middle/last frame."""
    size = tuple(spec["size"])
    v1, v2 = [], []
    for c in spec["cuts"]:
        for s in measure_cut(spec, c):
            for pid in c["focus"]:
                m = s["people"][pid]
                frac = m["height_px"] / size[1]
                if not m["visible"] or not m["in_frame"]:
                    v1.append(f"{c['camera']} f{s['frame']}: {pid} not in frame")
                elif frac < MIN_FOCUS_HEIGHT_FRAC:
                    v1.append(f"{c['camera']} f{s['frame']}: {pid} {m['height_px']:.0f} px "
                              f"({frac:.2f} of frame height < {MIN_FOCUS_HEIGHT_FRAC:.2f})")
            ids = [p for p, m in s["people"].items() if m["visible"]]
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    ov = _overlap(s["people"][a]["box"], s["people"][b]["box"])
                    if ov > MAX_OVERLAP:
                        v2.append(f"{c['camera']} f{s['frame']}: {a} and {b} overlap {ov:.0%}")
    return [
        _res("V1", "REVIEW", f"hypothesis threshold: {len(v1)} issue(s): {v1[:6]}") if v1 else
        _res("V1", "PASS", f"every focus person is in frame and >= {MIN_FOCUS_HEIGHT_FRAC:.2f} of frame height"),
        _res("V2", "REVIEW", f"hypothesis threshold: {len(v2)} issue(s): {v2[:6]}") if v2 else
        _res("V2", "PASS", f"no two people overlap more than {MAX_OVERLAP:.0%}"),
    ]


def validate_tail(spec: dict) -> dict:
    """V9: last view >= 1.0 s, camera still and people calm in the last 0.75 s (the frame the next clip starts from)."""
    last = spec["cuts"][-1]
    secs = (last["frame_out"] - last["frame_in"]) / spec["fps"]
    if secs < LAST_VIEW_MIN_S:
        return _res("V9", "FAIL", f"last view is {secs:.2f} s, needs >= {LAST_VIEW_MIN_S} s")
    start = spec["clip_frames"] - 1 - round(TAIL_SECONDS * spec["fps"])
    moved = []
    for p in spec["people"]:
        a, b = person_state(p, start), person_state(p, spec["clip_frames"] - 1)
        d = math.dist(a["pos"], b["pos"])
        if d > TAIL_MAX_MOVE or a["pose"] != b["pose"]:
            moved.append(f"{p['id']} moves {d:.2f} m / pose {a['pose']}->{b['pose']}")
    cam_a, cam_b = camera_state(spec, last, start), camera_state(spec, last, spec["clip_frames"] - 1)
    if cam_a != cam_b:
        moved.append("camera moves")
    return _res("V9", "REVIEW", f"tail not calm (hypothesis): {moved}") if moved else \
        _res("V9", "PASS", f"last view {secs:.2f} s, calm in the last {TAIL_SECONDS} s")


def validate_chain(prev: dict, nxt: dict) -> dict:
    """V8: the next clip's first view is the previous clip's last view (camera, lens, people), unless it declares a new photo."""
    if nxt.get("new_photo"):
        return _res("V8", "PASS", "next clip declares a new photo")
    last, first = prev["cuts"][-1], nxt["cuts"][0]
    a = camera_state(prev, last, prev["clip_frames"] - 1)
    b = camera_state(nxt, first, 0)
    problems = []
    if a["lens"] != b["lens"] or a["heading"] != b["heading"] or a["pitch"] != b["pitch"] or \
            math.dist(a["pos"], b["pos"]) > CHAIN_POS_TOL:
        problems.append("camera differs")
    prev_people = {p["id"]: person_state(p, prev["clip_frames"] - 1) for p in prev["people"]}
    for p in nxt["people"]:
        st, old = person_state(p, 0), prev_people.get(p["id"])
        if old is None or math.dist(st["pos"], old["pos"]) > CHAIN_POS_TOL or st["pose"] != old["pose"]:
            problems.append(f"{p['id']} not where the last clip left them")
    if prev["place"] != nxt["place"]:
        problems.append("place differs")
    return _res("V8", "FAIL", "; ".join(problems)) if problems else _res("V8", "PASS", "chain continues the last view")


def summarize(results: list[dict]) -> str:
    states = {r["status"] for r in results}
    return "FAIL" if "FAIL" in states else "REVIEW" if "REVIEW" in states else "PASS"


def validate_series(specs: list[dict]) -> list[dict]:
    """V8 over a run of clips of one scene (same place, each clip chained to the one before)."""
    out = []
    for prev, nxt in zip(specs, specs[1:]):
        res = validate_chain(prev, nxt)
        res["message"] = f"{prev['scene_id']} -> {nxt['scene_id']}: {res['message']}"
        out.append(res)
    return out


def load_series(directory: str | Path) -> dict[str, list[dict]]:
    """Specs of a folder grouped by scene letter: t0_a1, t0_a2, ... -> {"a": [clip1, clip2, ...]} in clip order."""
    groups: dict[str, list[tuple[str, dict]]] = {}
    for path in sorted(Path(directory).glob("*.json")):
        spec = load_spec(path)
        stem = spec["scene_id"]
        groups.setdefault(stem[:-1], []).append((stem, spec))
    return {k: [s for _, s in sorted(v)] for k, v in groups.items()}



# ------------------------------------------------------------------------------------------------ film style card

def load_film_style(name: str | Path) -> dict:
    """``film_styles/<name>.json`` (or a path). A card holds camera language only: no colour, no light."""
    path = Path(name)
    if not path.suffix:
        path = FILM_STYLE_DIR / f"{name}.json"
    card = json.loads(path.read_text(encoding="utf-8"))
    if any(k in card for k in ("light", "lighting", "colour", "color", "palette")):
        raise SceneSpecError(f"film style {path.name}: Blender's role is camera and angles only, no colour/light field")
    return card


def spec_card(spec: dict) -> dict | None:
    return load_film_style(spec["film_style"]) if spec.get("film_style") else None


def _card_status(card: dict | None) -> str:
    """A draft card is a hypothesis: a broken number asks the creator to look (REVIEW); a verified card blocks."""
    return "REVIEW" if card is None or card.get("draft", True) else "FAIL"


def validate_camera(spec: dict) -> dict:
    """V5: every lens on every camera (path keys included) is in the allowed list, from the film card when the spec names
    one, else the T0 list; with a card the camera height must also stay in the card's range."""
    card = spec_card(spec)
    lenses = tuple(card["lens_mm"]) if card else LENSES_ALLOWED
    bad = []
    heights = []
    for cam in spec["cameras"]:
        keys = cam.get("path") or [cam]
        if any(k["lens"] not in lenses for k in keys):
            bad.append(cam["id"])
        if card:
            lo, hi = card["camera_height_m"]["min"], card["camera_height_m"]["max"]
            if any(not lo - 1e-9 <= k["pos"][2] <= hi + 1e-9 for k in keys):
                heights.append(cam["id"])
    if bad:
        return _res("V5", "FAIL", f"lens not in {lenses}: {bad}")
    if heights:
        return _res("V5", _card_status(card), f"camera height outside the card's {card['camera_height_m']['min']}-"
                                              f"{card['camera_height_m']['max']} m (card draft={card.get('draft', True)}): {heights}")
    return _res("V5", "PASS", f"every lens in {lenses}" + (f" and every height inside the card ({card['film']})" if card else ""))


# ------------------------------------------------------------------------------------------------ V11 / V12

def _compass(dx: float, dy: float) -> float:
    return math.degrees(math.atan2(dx, dy)) % 360


def _angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d


def size_class(frac: float, card: dict | None) -> str:
    """close / medium / wide from the subject's height as a share of the frame height; the cut-offs come from the card."""
    t = (card or {}).get("size_classes", {"close_min_frac": 0.6, "medium_min_frac": 0.3})
    return "close" if frac >= t["close_min_frac"] else "medium" if frac >= t["medium_min_frac"] else "wide"


_SIZE_RANK = {"wide": 0, "medium": 1, "close": 2}


def _subject(spec: dict, a: dict, b: dict) -> str | None:
    shared = [p for p in b["focus"] if p in a["focus"]]
    if shared:
        return shared[0]
    return (b["focus"] or a["focus"] or [None])[0]


def _cam_velocity(spec: dict, cut: dict, frame: int, forward: bool) -> dict:
    """Camera velocity at a frame in the camera's own frame (forward, right), metres/second."""
    f0, f1 = (frame, frame + 1) if forward else (frame - 1, frame)
    s0, s1 = camera_state(spec, cut, f0), camera_state(spec, cut, f1)
    dx, dy = (s1["pos"][0] - s0["pos"][0]) * spec["fps"], (s1["pos"][1] - s0["pos"][1]) * spec["fps"]
    h = math.radians(s1["heading"])
    fwd, right = dx * math.sin(h) + dy * math.cos(h), dx * math.cos(h) - dy * math.sin(h)
    speed = math.hypot(fwd, right)
    return {"speed": round(speed, 3), "dir": round(math.degrees(math.atan2(right, fwd)), 1) if speed else None,
            "fwd": round(fwd, 3), "right": round(right, 3)}


def _axis_pair(spec: dict) -> list[str]:
    ids = spec.get("axis") or [p["id"] for p in spec["people"][:2]]
    return ids


def _side(spec: dict, cam_pos, frame: int, neutral_m: float) -> int:
    """Which side of the 180-degree line (person 1 -> person 2) the camera is on: +1 / -1, 0 on the line."""
    ids = _axis_pair(spec)
    if len(ids) < 2:
        return 0
    people = {p["id"]: p for p in spec["people"]}
    p1, p2 = person_state(people[ids[0]], frame)["pos"], person_state(people[ids[1]], frame)["pos"]
    ax, ay = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(ax, ay)
    if length < 1e-6:
        return 0
    cross = (ax * (cam_pos[1] - p1[1]) - ay * (cam_pos[0] - p1[0])) / length    # signed metres from the line
    return 0 if abs(cross) <= neutral_m else (1 if cross > 0 else -1)


def transitions(spec: dict) -> list[dict]:
    """One row per cut-to-cut transition: the camera's angle change around the subject, the size change, the side of
    the 180-degree line and the camera speed (direction in the camera's own frame) leaving and entering."""
    card = spec_card(spec)
    tr = (card or {}).get("transition", {})
    neutral = tr.get("axis_neutral_m", 0.3)
    size = tuple(spec["size"])
    people = {p["id"]: p for p in spec["people"]}
    rows = []
    for a, b in zip(spec["cuts"], spec["cuts"][1:]):
        fa, fb = a["frame_out"] - 1, b["frame_in"]
        row = {"from": a["camera"], "to": b["camera"], "frame": b["frame_in"], "axis_cross_ok": bool(b.get("axis_cross_ok"))}
        subj = _subject(spec, a, b)
        ca, cb = camera_state(spec, a, fa), camera_state(spec, b, fb)
        if subj:
            sa, sb = person_state(people[subj], fa), person_state(people[subj], fb)
            az_a = _compass(ca["pos"][0] - sa["pos"][0], ca["pos"][1] - sa["pos"][1])
            az_b = _compass(cb["pos"][0] - sb["pos"][0], cb["pos"][1] - sb["pos"][1])
            ma, mb = measure_person(ca, size, sa), measure_person(cb, size, sb)
            fra, frb = ma["height_px"] / size[1], mb["height_px"] / size[1]
            row.update(subject=subj, angle_deg=round(_angle_diff(az_a, az_b), 1),
                       size_from=size_class(fra, card), size_to=size_class(frb, card),
                       height_frac_from=round(fra, 3), height_frac_to=round(frb, 3))
            row["size_steps"] = abs(_SIZE_RANK[row["size_from"]] - _SIZE_RANK[row["size_to"]])
        else:
            row.update(subject=None, angle_deg=None, size_from=None, size_to=None, size_steps=None)
        row["side_from"], row["side_to"] = _side(spec, ca["pos"], fa, neutral), _side(spec, cb["pos"], fb, neutral)
        va, vb = _cam_velocity(spec, a, fa, False), _cam_velocity(spec, b, fb, True)
        row["speed_from_mps"], row["speed_to_mps"] = va["speed"], vb["speed"]
        row["dir_from_deg"], row["dir_to_deg"] = va["dir"], vb["dir"]
        rows.append(row)
    return rows


def validate_transitions(spec: dict) -> list[dict]:
    """V11 (angle/size jump) and V12 (a: 180-degree line, b: movement handoff). Only for version 2 specs: the T0 specs
    (version 1) were drawn without them and report N/A with what V11/V12 would have said."""
    rows = transitions(spec)
    v2 = spec.get("version", 1) >= 2
    out = []
    card = spec_card(spec)
    tr = (card or {}).get("transition", {})
    min_angle = tr.get("min_angle_deg", 30)
    min_steps = tr.get("min_size_steps", 1)
    still = tr.get("still_speed_mps", 0.1)
    max_dir = tr.get("handoff_max_direction_deg", 45)
    max_ratio = tr.get("handoff_max_speed_ratio", 2.0)
    status = _card_status(card)
    jumps, crossed, mism_dir, mism_speed = [], [], [], []
    for r in rows:
        tag = f"{r['from']}->{r['to']}"
        if r["angle_deg"] is not None and r["angle_deg"] < min_angle and r["size_steps"] < min_steps:
            jumps.append(f"{tag}: {r['angle_deg']}° and {r['size_from']}->{r['size_to']} (needs >= {min_angle}° or a size step)")
        if r["side_from"] and r["side_to"] and r["side_from"] != r["side_to"] and not r["axis_cross_ok"]:
            crossed.append(f"{tag}: side {r['side_from']:+d} -> {r['side_to']:+d}")
        sa, sb = r["speed_from_mps"], r["speed_to_mps"]
        if sa > still and sb > still:
            d = _angle_diff(r["dir_from_deg"], r["dir_to_deg"])
            if d > max_dir:
                mism_dir.append(f"{tag}: direction {r['dir_from_deg']}° -> {r['dir_to_deg']}° ({d:.0f}° apart > {max_dir}°)")
            ratio = max(sa, sb) / min(sa, sb)
            if ratio > max_ratio:
                mism_speed.append(f"{tag}: speed {sa} -> {sb} m/s (x{ratio:.1f} > x{max_ratio})")
    if not v2:
        def _would(items):
            return "would FAIL/REVIEW" if items else "would PASS"
        return [_res("V11", "N/A", f"version 1 spec, not checked ({_would(jumps)})"),
                _res("V12", "N/A", f"version 1 spec, not checked (180° line {_would(crossed)}, handoff "
                                   f"{_would(mism_dir + mism_speed)})")]
    out.append(_res("V11", status, f"jump cut(s), card draft={(card or {}).get('draft', True)}: {jumps}") if jumps else
               _res("V11", "PASS", f"{len(rows)} transition(s), each >= {min_angle}° around the subject or a size step"))
    if crossed:
        out.append(_res("V12", "FAIL", f"camera crosses the 180° line without axis_cross_ok: {crossed}"))
    elif mism_dir:
        out.append(_res("V12", status, f"movement does not hand over: {mism_dir}"))
    elif mism_speed:
        out.append(_res("V12", status, f"movement speed jumps at the cut: {mism_speed}"))
    else:
        out.append(_res("V12", "PASS", "same side of the 180° line, movement hands over (direction and speed)"))
    return out
