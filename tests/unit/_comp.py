"""A demo job for the visual compensator tests: a spine, twelve comp_spec files (one per archetype) and their manifest, built in a
folder. The content is a fixture, not research: the places are real coordinates, the numbers are made up and say so (invariant 5)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.core import contracts as C
from explainer_engine.maps import camera as CAM

FPS = 24
SIZE = (320, 180)
WORDS = 900   # half a second a word: 7.5 minutes of read


def spine() -> dict:
    words = [{"i": i, "text": "word", "start_s": i * 0.5, "end_s": i * 0.5 + 0.4, "start_frame": i * 12, "end_frame": i * 12 + 10,
              "segment": "s1", "line": 0} for i in range(WORDS)]
    return {"schema": "audio_spine/1", "derived_from": {}, "fps": FPS, "duration_s": WORDS * 0.5, "total_frames": WORDS * 12 + 10,
            "words": words, "segments": [{"id": "s1", "start_frame": 0, "end_frame": WORDS * 12 + 10}], "post_hoc_shots": []}


def w(seconds: float) -> int:
    """The word that starts ``seconds`` into an item (half a second a word)."""
    return int(round(seconds * 2))


def _ev(eid, sec, op, target, frames=12, **args):
    e = {"id": eid, "word_index": w(sec), "op": op, "target": target, "frames": frames}
    if args:
        e["args"] = args
    return e


def _map_camera() -> dict:
    return {"start": {"lon": 25.0, "lat": 54.3, "span_km": 2000},
            "moves": [{"from_word": w(4), "to_word": w(10), "lon": 24.4, "lat": 54.8, "span_km": 50},
                      {"from_word": w(16), "to_word": w(22), "lon": 24.4, "lat": 54.8, "span_km": 1.5}]}


def map_payload(extra: dict | None = None) -> dict:
    p = {"camera": _map_camera(), "base": {"kind": "vector"}, "focus": {"lon": 24.4, "lat": 54.8, "radius_km": 400},
         "routes": [{"id": "r1", "side": "a", "waypoints": [[23.5, 54.9], [24.4, 54.8], [25.3, 54.7]], "ease": "march"}],
         "units": [{"id": "u1", "side": "a", "route": "r1"}],
         "labels": [{"id": "l1", "text": "Crossing", "lon": 23.9, "lat": 54.9, "class": "city"},
                    {"id": "l2", "text": "Depot", "lon": 25.2, "lat": 54.7, "class": "city"}],
         "rings": [{"id": "k1", "lon": 24.4, "lat": 54.8, "radius_km": 300}, {"id": "k2", "lon": 24.4, "lat": 54.8, "radius_km": 40}]}
    p.update(extra or {})
    return p


MAP_EVENTS = [_ev("e0", 0, "date", None, 12, text="JUNE"), _ev("e1", 1, "show_label", "l1", 6), _ev("e2", 2, "show_ring", "k1", 48),
              _ev("e3", 10, "show_route", "r1", 96), _ev("e4", 14.5, "march", "u1", 72), _ev("e5", 23, "show_label", "l2", 12),
              _ev("e6", 26, "show_ring", "k2", 24)]
MAP_FRAMES = 28 * FPS


def spec(archetype: str, item_id: str) -> dict:
    base = {"schema": "comp_spec/1", "item_id": item_id, "archetype_id": archetype, "width": SIZE[0], "height": SIZE[1]}
    if archetype == "MAP_3D_TERRAIN_FLYOVER":
        p = map_payload({"transition": {"to_shot": "s9", "pitch_deg": 45, "zdepth_ref": "visual/zdepth.png", "prelap_frames": 24}})
        p["camera"]["moves"][-1]["pitch_deg"] = 45
        return {**base, "events": copy.deepcopy(MAP_EVENTS), "payload": p}
    if archetype == "TACTICAL_UNIT_MANEUVER":
        return {**base, "events": copy.deepcopy(MAP_EVENTS), "payload": map_payload()}
    if archetype == "FORMATION_MICRO_MECHANICS":
        p = map_payload({"formation": {"side": "a", "count": 120, "center": [24.4, 54.8], "spread_km": 0.4, "start": "scatter"}})
        ev = [e for e in copy.deepcopy(MAP_EVENTS) if e["op"] != "march"] + [_ev("e4", 14.5, "form", "formation", 72, kind="column")]
        p["units"] = []
        return {**base, "events": ev, "payload": p}
    if archetype == "LOGISTICS_TETHER_AND_ATTRITION":
        p = map_payload({"supply": {"route": "r1", "strength_max": 1000, "strength_start": 1000, "side": "a"}})
        ev = [e for e in copy.deepcopy(MAP_EVENTS) if e["op"] != "march"]
        ev += [_ev("e4", 14.5, "supply_state", "supply", 48, state="amber"), _ev("e7", 19, "supply_state", "supply", 24, state="red"),
               _ev("e8", 20, "snap", "supply", 24, at=0.5)]
        p["units"] = []
        return {**base, "events": sorted(ev, key=lambda e: e["word_index"]), "payload": p}
    if archetype == "BALLISTIC_RANGE_AND_ENERGY_HUD":
        return {**base, "events": [_ev("a", 0, "show_ring", "r1", 36), _ev("b", 3, "draw_arc", "arc1", 48), _ev("c", 6, "stamp", "s1", 18),
                                   _ev("d", 8, "draw_arc", "arc2", 48), _ev("f", 11, "stamp", "s2", 18)],
                "payload": {"origin": [0.08, 0.78], "scale_m": 600, "rings": [{"id": "r1", "range_m": 100}],
                            "arcs": [{"id": "arc1", "range_m": 400, "peak_m": 90, "tone": "coral"}, {"id": "arc2", "range_m": 150, "peak_m": 10, "tone": "teal"}],
                            "stamps": [{"id": "s1", "range_m": 400, "text": "400 m"}, {"id": "s2", "range_m": 150, "text": "150 m"}]}}
    if archetype == "SPLIT_SCREEN_SPEED_RACE":
        return {**base, "events": [_ev("a", 1, "start", "race", 288)],
                "payload": {"left": {"label": "Racer A", "seconds": 12.0}, "right": {"label": "Racer B", "seconds": 20.4}, "side_left": "a", "side_right": "b"}}
    if archetype == "TECH_TREE_DEPENDENCY_GRAPH":
        return {**base, "events": [_ev("a", 0, "light", "n1", 24), _ev("b", 3, "light", "n2", 24), _ev("c", 6, "light", "n3", 24), _ev("d", 9, "light", "n4", 24)],
                "payload": {"nodes": [{"id": "n1", "label": "Iron", "x": 0.15, "y": 0.5}, {"id": "n2", "label": "Steel", "x": 0.4, "y": 0.35},
                                      {"id": "n3", "label": "Blade", "x": 0.65, "y": 0.5}, {"id": "n4", "label": "Gun", "x": 0.88, "y": 0.5, "state": "blocked"}],
                            "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}}
    if archetype == "ORDER_OF_BATTLE_TELEMETRY_HUD":
        return {**base, "events": [_ev("a", 1, "set", "row1", 18, value=800), _ev("b", 4, "set", "row2", 18, value=600), _ev("c", 7, "set", "row1", 18, value=500),
                                   _ev("d", 10, "set", "row2", 18, value=450)],
                "payload": {"corner": "tl", "rows": [{"id": "row1", "label": "Army A", "side": "a", "value": 1000, "unit": ""},
                                                     {"id": "row2", "label": "Army B", "side": "b", "value": 900, "unit": ""}]}}
    if archetype == "MULTI_SCENARIO_VERDICT_MATRIX":
        return {**base, "events": [_ev("a", 0, "grow", "s1", 36), _ev("b", 3, "grow", "s2", 36), _ev("c", 6, "grow", "s3", 36), _ev("d", 9, "grow", "s4", 36)],
                "payload": {"scenarios": [{"id": "s1", "label": "One", "probability": 0.5, "tone": "teal"}, {"id": "s2", "label": "Two", "probability": 0.3, "tone": "coral"},
                                          {"id": "s3", "label": "Three", "probability": 0.2, "tone": "amber"},
                                          {"id": "s4", "label": "Four", "probability": 0.0, "tone": "blue"}]}}
    if archetype == "WEAPON_AND_MATERIAL_CUTAWAY":
        return {**base, "events": [_ev("a", 0, "heat", "h1", 36), _ev("b", 3, "peel", "outer", 36), _ev("c", 6, "crack", "c1", 36), _ev("d", 9, "particles", "p1", 36),
                                   _ev("e", 11, "peel", "core", 36)],
                "payload": {"layers": [{"id": "core", "points": [[0.25, 0.3], [0.75, 0.3], [0.75, 0.7], [0.25, 0.7]], "tone": "grey"},
                                       {"id": "outer", "points": [[0.2, 0.25], [0.8, 0.25], [0.8, 0.75], [0.2, 0.75]], "tone": "kit", "peel": [0.0, -0.4]}],
                            "overlays": [{"id": "h1", "kind": "heat", "at": [0.5, 0.5], "radius": 0.3}, {"id": "c1", "kind": "crack", "at": [0.3, 0.4], "to": [0.7, 0.6]},
                                         {"id": "p1", "kind": "particles", "at": [0.5, 0.5], "count": 20}]}}
    if archetype == "PARALLAX_25D_TABLEAU":
        return {**base, "events": [_ev("a", 0, "dolly", "tableau", 240)],
                "payload": {"picture": "visual/assets/pic.png", "depth": "visual/assets/depth.png", "dolly": {"scale": 1.08, "dx": 0.012},
                            "dust": {"count": 12, "seed": 3}}}
    if archetype == "PRIMARY_SOURCE_DOSSIER_CARD":
        return {**base, "events": [_ev("a", 0, "focus", "doc", 36), _ev("b", 3, "underline", "l2", 24), _ev("c", 6, "underline", "l1", 24)],
                "payload": {"lines": [{"id": "l1", "text": "To the commander of the left wing,"}, {"id": "l2", "text": "hold the ford until noon."}],
                            "source": "Fixture letter, not a source", "tilt_deg": 14}}
    raise KeyError(archetype)


def shift(s: dict, words: int) -> dict:
    """The spec's word indices are written from the item's first word; the manifest's trigger word makes them absolute."""
    s = copy.deepcopy(s)
    for e in s["events"]:
        e["word_index"] += words
    for m in (s["payload"].get("camera") or {}).get("moves", []):
        m["from_word"] += words
        m["to_word"] += words
    return s


ORDER = ["MAP_3D_TERRAIN_FLYOVER", "BALLISTIC_RANGE_AND_ENERGY_HUD", "WEAPON_AND_MATERIAL_CUTAWAY", "TECH_TREE_DEPENDENCY_GRAPH",
         "TACTICAL_UNIT_MANEUVER", "SPLIT_SCREEN_SPEED_RACE", "PARALLAX_25D_TABLEAU", "MULTI_SCENARIO_VERDICT_MATRIX",
         "FORMATION_MICRO_MECHANICS", "ORDER_OF_BATTLE_TELEMETRY_HUD", "PRIMARY_SOURCE_DOSSIER_CARD", "LOGISTICS_TETHER_AND_ATTRITION"]
LENGTH = {a: 14 * FPS for a in ORDER}
LENGTH.update({a: MAP_FRAMES for a in ("MAP_3D_TERRAIN_FLYOVER", "TACTICAL_UNIT_MANEUVER", "FORMATION_MICRO_MECHANICS", "LOGISTICS_TETHER_AND_ATTRITION")})
LENGTH["PARALLAX_25D_TABLEAU"] = 10 * FPS
LENGTH["PRIMARY_SOURCE_DOSSIER_CARD"] = 10 * FPS


def build(base: Path) -> dict:
    """Write the demo job into ``base`` and return the manifest."""
    base = Path(base)
    (base / "audio").mkdir(parents=True, exist_ok=True)
    (base / "visual" / "specs").mkdir(parents=True, exist_ok=True)
    (base / "visual" / "assets").mkdir(parents=True, exist_ok=True)
    sp = spine()
    (base / "audio" / "audio_spine.json").write_text(json.dumps(sp), encoding="utf-8")
    yy, xx = np.mgrid[0:90, 0:160]
    pic = np.stack([(xx * 255 // 160), (yy * 255 // 90), np.full_like(xx, 140)], axis=2).astype(np.uint8)
    pic[30:60, 60:100] = (230, 200, 60)
    Image.fromarray(pic).save(base / "visual" / "assets" / "pic.png")
    depth = (np.hypot(xx - 80, yy - 45) < 30) * 200 + (yy * 255 // 90) // 3
    Image.fromarray(depth.astype(np.uint8), "L").save(base / "visual" / "assets" / "depth.png")
    CAM.zdepth(*SIZE, 45).save(base / "visual" / "zdepth.png")
    items, t = [], 20.0
    for k, arch in enumerate(ORDER):
        iid = f"it{k + 1:02d}"
        s = shift(spec(arch, iid), w(t))
        (base / "visual" / "specs" / f"{iid}.json").write_text(json.dumps(s), encoding="utf-8")
        items.append({"item_id": iid, "shot_id": f"s{k + 1}", "archetype_id": arch, "trigger_word_index": w(t), "duration_frames": LENGTH[arch],
                      "layers": [{"kind": "spec", "ref": f"visual/specs/{iid}.json", "reveal_word_index": None}], "on_screen_text": None})
        t += LENGTH[arch] / FPS + 12
    manifest = {"schema": "visual_comp_manifest/1", "audio_spine": {"path": "audio/audio_spine.json", "sha256": C.sha256_file(base / "audio" / "audio_spine.json")},
                "items": items}
    (base / "visual" / "visual_comp_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest
