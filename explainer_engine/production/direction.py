"""The Scene Director's file for one shot (roadmap 2026-11-14 B.1 ``shot_direction/1``; phase P1 draft, human-in-the-loop).

The director (in P1 the thread's Claude, looking at the real picture and the rendered frames; L-11 a) writes one JSON per
shot. The script stays Stage A's approved intent; this file is Stage B's decision as a difference with a reason. P1 only
loads, checks and resolves it into a ``production/directed25d`` plan; P2 turns the draft into a versioned schema and a runner
stage (``direction``, after ``pictures``, before ``clips``).

The draft's fields: ``schema``, ``shot_id``, ``kind`` (photo|map), ``picture_sha256``, ``seen`` (what is REALLY in the frame:
``what`` in words, ``objects`` with points, ``lights``, ``depth_checks``), ``purpose``, ``emotion``, ``focus``, ``composition``,
``intent`` (intended|minimal|still_by_design), ``tracks`` (camera, character, object, environment, lighting, atmosphere,
audio; each with ``op``, ``target``, ``timing``, ``renderer``, ``validate``), ``sound``, ``transition_out``, ``route``,
``overrides`` (field, from, to, why: a change without a reason FAILs), ``rounds`` and ``expect`` (what QA measures).
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "shot_direction/1-draft"
INTENTS = ("intended", "minimal", "still_by_design")
TRACKS = ("camera", "character", "object", "environment", "lighting", "atmosphere", "audio")
CAMERA_OPS = ("hold", "push", "pull", "truck", "crane", "pan", "tilt", "orbit", "handheld", "rack_focus")
EFFECT_OPS = ("fire", "candle", "glow", "smoke", "mist", "sun_shaft", "cloud_drift", "heat_haze", "fire_box", "dust")
AUDIO_DECISIONS = ("sfx", "ui_cue", "ambience_only", "music_only", "silent_by_design", "review_required")
RENDERERS = ("directed25d", "layers25d", "map_action", "ltx", "blender", "none")
MINIMAL_MAX = 0.5          # a "minimal" shot moves its camera at no more than this strength (engineering default, REVIEW)
SEGMENTS_MAX = 3


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def _ids(d: dict) -> tuple[set, set]:
    seen = d.get("seen") or {}
    return {o["id"] for o in seen.get("objects", [])}, {li["id"] for li in seen.get("lights", [])}


def check(d: dict, picture_sha256: str | None = None) -> list[dict]:
    """Problems of one direction file: ``[{"level": "FAIL"|"REVIEW", "what": text}]``; an empty list passes."""
    out = []

    def bad(what, level="FAIL"):
        out.append({"level": level, "what": what})

    if d.get("schema") != SCHEMA:
        bad(f"schema is {d.get('schema')!r}, not {SCHEMA}")
    if d.get("intent") not in INTENTS:
        bad(f"intent {d.get('intent')!r} is not one of {', '.join(INTENTS)}")
    if picture_sha256 and d.get("picture_sha256") != picture_sha256:
        bad("picture_sha256 does not match the picture: the direction was written for another picture")
    if not (d.get("seen") or {}).get("what"):
        bad("seen.what is empty: the director must say in words what is really in the frame")
    for o in d.get("overrides", []):
        for k in ("field", "from", "to", "why"):
            if not str(o.get(k, "")).strip():
                bad(f"override {o.get('field', '?')}: no {k} (a change without a reason FAILs)")
    objs, lights = _ids(d)
    cams = []
    for i, t in enumerate(d.get("tracks", [])):
        name = f"track {i} ({t.get('track')}/{t.get('op')})"
        if t.get("track") not in TRACKS:
            bad(f"{name}: unknown track")
            continue
        if t["track"] == "audio":
            if t.get("decision") not in AUDIO_DECISIONS:
                bad(f"{name}: audio decision {t.get('decision')!r}")
            continue
        if t.get("renderer") not in RENDERERS:
            bad(f"{name}: renderer {t.get('renderer')!r}")
        if t["track"] == "camera":
            if t.get("op") not in CAMERA_OPS:
                bad(f"{name}: camera op unknown")
            if "validate" not in t:
                bad(f"{name}: no validate block (every camera track says what QA measures)")
            if t.get("op") not in ("hold", "handheld", "rack_focus"):
                cams.append(t)
        elif t.get("op") not in EFFECT_OPS:
            bad(f"{name}: effect op unknown")
        tg = t.get("target") or {}
        for key in ("mask", "from_mask", "to_mask"):
            if tg.get(key) and tg[key] not in objs:
                bad(f"{name}: target {key} {tg[key]!r} is not an object of seen.objects")
        for lid in tg.get("lights", []) + ([tg["light"]] if tg.get("light") else []):
            if lid not in lights:
                bad(f"{name}: light {lid!r} is not in seen.lights")
    if len(cams) > SEGMENTS_MAX:
        bad(f"{len(cams)} camera segments; at most {SEGMENTS_MAX}")
    if d.get("intent") == "still_by_design" and cams:
        bad(f"still_by_design but the camera moves ({', '.join(t['op'] for t in cams)})")
    if d.get("intent") == "minimal":
        for t in cams:
            if float(t.get("params", {}).get("strength", 1.0)) > MINIMAL_MAX:
                bad(f"minimal but {t['op']} strength {t['params']['strength']} > {MINIMAL_MAX}", "REVIEW")
    return out


def word_frame(spine: list[dict], word: str, nth: int = 1) -> int:
    """The frame of the ``nth`` spoken ``word`` in the shot's clock spine (``clock/timing.json``)."""
    k = 0
    for w in spine or []:
        if str(w.get("word", "")).lower().strip(".,!?;:'\"") == word.lower():
            k += 1
            if k == nth:
                return int(w.get("frame", w.get("start_frame", 0)))
    raise ValueError(f"the word {word!r} (#{nth}) is not spoken in this shot")


def _frame(spec: dict | None, frames: int, spine, default: int) -> int:
    if not spec:
        return default
    if "frame" in spec:
        return int(spec["frame"])
    if "frac" in spec:
        return int(round(float(spec["frac"]) * frames))
    if "word" in spec:
        return word_frame(spine, spec["word"], int(spec.get("nth", 1))) + int(spec.get("offset", 0))
    raise ValueError(f"timing {spec!r}: give frame, frac or word")


def _target(tg: dict | None) -> dict | None:
    if not tg:
        return None
    out = {}
    if tg.get("mask"):
        out["mask"] = tg["mask"]
    if tg.get("point"):
        out["point"] = tg["point"]
    if tg.get("light"):
        out["light"] = tg["light"]
    return out or None


def resolve(d: dict, frames: int, spine: list[dict] | None = None, variant: str | None = None) -> dict:
    """The direction -> a ``directed25d`` plan. ``variant`` picks a named alternative block (``variants.<name>``: its
    ``tracks`` replace the main ones) for the ablations and the comparisons the owner chooses from."""
    tracks = d.get("tracks", [])
    if variant:
        tracks = d["variants"][variant]["tracks"]
    plan = {"shot_id": d["shot_id"], "frames": int(frames), "cameras": [], "handheld": None, "rack": None, "effects": [],
            "far_share": float(d.get("far_share", 0.2)), "intent": d.get("intent")}
    if d.get("layers") is not None:
        plan["layers"] = list(d["layers"])
    for t in tracks:
        if t.get("track") == "audio" or t.get("renderer") not in (None, "directed25d"):
            continue
        prm = dict(t.get("params", {}))
        tm = t.get("timing", {})
        a = _frame(tm.get("start"), frames, spine, 0)
        b = _frame(tm.get("end"), frames, spine, frames)
        op = t["op"]
        if t["track"] == "camera":
            if op == "hold":
                continue
            if op == "handheld":
                plan["handheld"] = float(prm.get("strength", 0.3))
                continue
            if op == "rack_focus":
                tg = t.get("target", {})
                plan["rack"] = {"from": {"mask": tg["from_mask"]} if tg.get("from_mask") else {"light": tg.get("from_light")},
                                "to": {"mask": tg["to_mask"]} if tg.get("to_mask") else {"light": tg.get("to_light")},
                                "at": a, "frames": max(1, b - a), "strength": float(prm.get("strength", 1.0)),
                                **{k: prm[k] for k in ("sigma_px", "span") if k in prm}}
                continue
            plan["cameras"].append({"op": op, "strength": float(prm.get("strength", 1.0)), "direction": prm.get("direction"),
                                    "from": a, "to": max(a + 1, b), "easing": prm.get("ease", "ease_in_out"),
                                    "target": _target(t.get("target"))})
        else:
            tg = t.get("target") or {}
            e = {"op": op, "strength": float(prm.pop("strength", 1.0)), "params": prm}
            if tg.get("lights"):
                e["lights"] = list(tg["lights"])
            if tg.get("light"):
                e["light"] = tg["light"]
                e.setdefault("lights", [tg["light"]])
            if tg.get("box"):
                e["box"] = tg["box"]
            if tg.get("point"):
                e["point"] = tg["point"]
            if tg.get("origin"):
                e["origin"] = tg["origin"]
            plan["effects"].append(e)
    plan["cameras"].sort(key=lambda c: c["from"])
    return plan
