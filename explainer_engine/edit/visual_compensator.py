"""The visual compensator: free, deterministic frames for the stretches where the narrator speaks and no character is on screen
(Blueprint plan v2, phase P5; docs/COMPENSATOR.md).

``visual_comp_manifest/1`` says which archetype fills which shot and which spoken word starts it; each item's ``comp_spec/1`` says what
it draws and which word starts every change. This module is the catalogue of the twelve archetypes, the checker of a manifest (the
eight map laws for the map archetypes, the word lock and the stimulus window for all), the planner checks across items (rotation,
map share, lane balance) and the renderer that turns an item and a frame number into a picture. A frame is a pure function of its
spec and its number, so a chunked render draws the same pixels (CMP-09).

    python -m explainer_engine.edit.visual_compensator check <visual_comp_manifest.json> [--base <job folder>]
    python -m explainer_engine.edit.visual_compensator render <manifest> <item_id> <out dir> [--frames A:B] [--ss N]
    python -m explainer_engine.edit.visual_compensator measure <manifest> [--base <job folder>] [--write]
"""

from __future__ import annotations

import json
import sys
import time
from functools import lru_cache
from pathlib import Path

from explainer_engine.core import contracts as C
from explainer_engine.edit import hud, tableau
from explainer_engine.maps import draw as D
from explainer_engine.maps import laws, render as maprender, timeline
from explainer_engine.standards import sourced_rules as SR

CATALOGUE = Path(__file__).with_name("archetypes.json")
CONTINUOUS = {"PARALLAX_25D_TABLEAU"}   # a dolly runs the whole item: something moves every frame
FAMILIES = ("map", "hud", "cutaway", "graph")


@lru_cache(maxsize=1)
def catalogue() -> dict:
    return json.loads(CATALOGUE.read_text(encoding="utf-8"))


def archetype(archetype_id: str) -> dict:
    for a in catalogue()["archetypes"]:
        if a["id"] == archetype_id:
            return a
    raise KeyError(archetype_id)


def ids() -> list[str]:
    return [a["id"] for a in catalogue()["archetypes"]]


def lane_of(archetype_id: str) -> str:
    return archetype(archetype_id)["lane"]


def availability() -> list[dict]:
    """The planner's table: per archetype the lane, the family, whether it is free and the measured CPU seconds per frame (null until
    ``measure --write`` has run on the machine that renders)."""
    measured = (catalogue().get("measured") or {}).get("s_per_frame", {})
    return [{"id": a["id"], "number": a["number"], "lane": a["lane"], "family": a["family"], "free": a["free"],
             "pure_map": a["pure_map"], "s_per_frame": measured.get(a["id"])} for a in catalogue()["archetypes"]]


# --- one item ----------------------------------------------------------------------------------------------------------------------

def _module(archetype_id: str):
    if archetype_id in maprender.ARCHETYPES:
        return "map"
    if archetype_id in hud.ARCHETYPES:
        return "hud"
    return "tableau"


def payload_findings(spec: dict, base_dir: Path | None = None) -> list[dict]:
    """The shape findings of one comp_spec (what ``contracts`` runs): the archetype is in the catalogue and its payload is drawable."""
    if spec["archetype_id"] not in ids():
        return [{"rule": "CN-15", "severity": "FAIL", "where": spec["item_id"], "detail": f"archetype {spec['archetype_id']!r} is not in the catalogue"}]
    kind = _module(spec["archetype_id"])
    if kind == "map":
        return maprender.validate_payload(spec)
    if kind == "hud":
        return hud.validate_payload(spec)
    return tableau.validate_payload(spec) + tableau.asset_findings(spec, base_dir)


def _element_locks(spec: dict, tl: timeline.Timeline) -> list[dict]:
    """Word lock (CMP-04) for the HUD, graph and cutaway archetypes: every element that appears has an event on a word."""
    kind = _module(spec["archetype_id"])
    if kind == "map":
        return []
    ops = (hud.OPS if kind == "hud" else tableau.OPS)[spec["archetype_id"]]
    out = []
    for key in sorted({v for v in ops.values() if v not in ("race", "tableau", "doc")}):
        for x in spec["payload"].get(key, []):
            if not any(e.target == x["id"] for e in tl.events):
                out.append({"rule": "CMP-04", "severity": SR.level("BP-147"), "where": spec["item_id"],
                            "detail": f"{key[:-1]} {x['id']!r} has no event: it would sit on frame 1, frozen"})
    return out


def check_item(spec: dict, spine: dict, trigger_word_index: int, duration_frames: int, base_dir: Path | None = None,
               scene_set: dict | None = None) -> list[dict]:
    """Every finding of one item: the payload shape, then the laws (the eight for a map, the word lock and the stimulus window for
    the rest)."""
    found = payload_findings(spec, base_dir)
    if any(f["severity"] == "FAIL" for f in found):
        return found
    if _module(spec["archetype_id"]) == "map":
        return laws.check_item(spec, spine, trigger_word_index, duration_frames, base_dir, scene_set)
    try:
        tl, clock = timeline.build(spec, spine, trigger_word_index, duration_frames)
    except ValueError as e:
        return found + [{"rule": "CN-01", "severity": "FAIL", "where": spec["item_id"], "detail": str(e)}]
    found += _element_locks(spec, tl) + laws.faction_colours(spec)
    if spec["archetype_id"] not in CONTINUOUS:
        found += laws.stimulus_window(spec, tl, clock)
    return found


def render_item_frame(spec: dict, spine: dict, trigger_word_index: int, duration_frames: int, f: int, ss: int = D.SS,
                      base_dir: Path | None = None):
    """The frame ``f`` (counted from the item's first frame) as a PIL image: RGB, or RGBA for the telemetry overlay."""
    tl, clock = timeline.build(spec, spine, trigger_word_index, duration_frames)
    kind = _module(spec["archetype_id"])
    if kind == "map":
        return maprender.render_frame(spec, tl, clock, f, ss, base_dir)
    if kind == "hud":
        return hud.render_frame(spec, tl, f, ss)
    return tableau.render_frame(spec, tl, f, ss, base_dir)


# --- the manifest ------------------------------------------------------------------------------------------------------------------

def _read(base: Path, ref: str) -> dict:
    return json.loads((Path(base) / ref).read_text(encoding="utf-8"))


def items_of(manifest: dict, base: Path) -> list[dict]:
    """Each item with its spec (the layer of kind ``spec``), its spine and its place in time."""
    spine = _read(base, manifest["audio_spine"]["path"])
    out = []
    for it in manifest["items"]:
        ref = next((ly["ref"] for ly in it["layers"] if ly["kind"] == "spec"), None)
        spec = _read(base, ref) if ref else None
        w = spine["words"][it["trigger_word_index"]] if it["trigger_word_index"] < len(spine["words"]) else None
        start = w["start_frame"] / spine["fps"] if w else None
        out.append({"item": it, "spec": spec, "spine": spine, "start_s": start,
                    "end_s": None if start is None else start + it["duration_frames"] / spine["fps"]})
    return out


def check(manifest: dict, base: Path | str, scene_sets: dict | None = None) -> list[dict]:
    """Every finding of a manifest: the contract, each item (its spec must name the item and the archetype), then the planner
    checks across items."""
    base = Path(base)
    found = C.errors(manifest, base)
    if any(f["severity"] == "FAIL" for f in found):
        return found
    rows = items_of(manifest, base)
    for r in rows:
        it, spec = r["item"], r["spec"]
        if spec is None:
            found.append({"rule": "CN-01", "severity": "FAIL", "where": it["item_id"], "detail": "the item has no layer of kind 'spec'"})
            continue
        if spec["item_id"] != it["item_id"] or spec["archetype_id"] != it["archetype_id"]:
            found.append({"rule": "CN-01", "severity": "FAIL", "where": it["item_id"], "detail": "the spec names another item or archetype"})
            continue
        found += check_item(spec, r["spine"], it["trigger_word_index"], it["duration_frames"], base, (scene_sets or {}).get(it["shot_id"]))
    timed = [{"archetype_id": r["item"]["archetype_id"], "start_s": r["start_s"], "end_s": r["end_s"]} for r in rows if r["start_s"] is not None]
    found += rotation(timed)
    return found


# --- across items (the planner's checks) -------------------------------------------------------------------------------------------

def rotation(blocks: list[dict]) -> list[dict]:
    """BP-149: never the same archetype twice in a row; at most family_max items of one family in any window_s window; a run of
    map archetypes lasts at most map_run_max_s. ``blocks`` are ``{archetype_id, start_s, end_s}``."""
    out, lvl = [], SR.level("BP-149")
    window, fam_max, run_max = SR.T("BP-149", "window_s"), SR.T("BP-149", "family_max"), SR.T("BP-149", "map_run_max_s")
    blocks = sorted(blocks, key=lambda b: b["start_s"])
    for a, b in zip(blocks, blocks[1:]):
        if a["archetype_id"] == b["archetype_id"]:
            out.append({"rule": "CMP-10", "severity": lvl, "where": a["archetype_id"], "detail": "the same archetype in two adjacent items"})
    for i, b in enumerate(blocks):
        fam = archetype(b["archetype_id"])["family"]
        inside = [x for x in blocks if archetype(x["archetype_id"])["family"] == fam and b["start_s"] <= x["start_s"] < b["start_s"] + window]
        if len(inside) > fam_max:
            out.append({"rule": "CMP-10", "severity": lvl, "where": b["archetype_id"],
                        "detail": f"{len(inside)} {fam} items in {window:g} s from {b['start_s']:.1f} s (at most {fam_max})"})
            break
    run_start, run_end = None, None
    for b in blocks:
        if archetype(b["archetype_id"])["pure_map"]:
            run_start = b["start_s"] if run_start is None or b["start_s"] > run_end + 0.5 else run_start
            run_end = b["end_s"]
            if run_end - run_start > run_max:
                out.append({"rule": "CMP-10", "severity": lvl, "where": b["archetype_id"],
                            "detail": f"a map run of {run_end - run_start:.0f} s (at most {run_max:g} s)"})
                break
        else:
            run_start = run_end = None
    return out


def map_share(blocks: list[dict], total_s: float) -> list[dict]:
    """BP-150: the pure cartography archetypes are at most map_pure_share_max of the runtime (REVIEW; flagged hard over the high mark)."""
    share = sum(b["end_s"] - b["start_s"] for b in blocks if archetype(b["archetype_id"])["pure_map"]) / total_s
    out = []
    if share > SR.T("BP-150", "map_pure_share_max"):
        hard = share > SR.T("BP-150", "map_pure_share_high")
        out.append({"rule": "CMP-11", "severity": SR.level("BP-150"), "where": "runtime",
                    "detail": f"maps are {100 * share:.0f} % of the runtime (at most {100 * SR.T('BP-150', 'map_pure_share_max'):.0f} %)"
                              + (", over the high mark: nobody wants 80 % maps" if hard else "")})
    return out


def lane_balance(blocks: list[dict]) -> list[dict]:
    """BP-127: no more than non_character_run_max_s of consecutive non-character visuals without a character beat or a host line,
    and no character scene longer than character_scene_max_s without a payoff. ``blocks`` are ``{kind, start_s, end_s}`` with kind
    character, host, map, hud, cutaway or graph."""
    out, lvl = [], SR.level("BP-127")
    run_max, scene_max = SR.T("BP-127", "non_character_run_max_s"), SR.T("BP-127", "character_scene_max_s")
    blocks = sorted(blocks, key=lambda b: b["start_s"])
    run0 = run1 = None
    char0 = char1 = None
    for b in blocks:
        if b["kind"] in ("character", "host"):
            run0 = run1 = None
        else:
            run0 = b["start_s"] if run0 is None else run0
            run1 = b["end_s"]
            if run1 - run0 > run_max:
                out.append({"rule": "CMP-12", "severity": lvl, "where": f"{run0:.0f} s",
                            "detail": f"{run1 - run0:.0f} s of non-character visuals in a row (at most {run_max:g} s)"})
                run0 = run1 = None
        if b["kind"] == "character":
            char0 = b["start_s"] if char0 is None else char0
            char1 = b["end_s"]
            if char1 - char0 > scene_max:
                out.append({"rule": "CMP-12", "severity": lvl, "where": f"{char0:.0f} s",
                            "detail": f"{char1 - char0:.0f} s of character scene without a tactical or visual payoff (at most {scene_max:g} s)"})
                char0 = char1 = None
        elif b["kind"] != "host":
            char0 = char1 = None
    return out


# --- measured times, render, command line ------------------------------------------------------------------------------------------

def measure(manifest: dict, base: Path, size=(1280, 720), frames: int = 3) -> dict:
    """Seconds of CPU per frame per archetype at ``size`` (the median of ``frames`` frames) over the items of a manifest, for the
    planner's table. The machine is named in the result: another machine measures again."""
    import os
    import platform
    out: dict[str, float] = {}
    for r in items_of(manifest, base):
        spec = {**r["spec"], "width": size[0], "height": size[1]}
        n = r["item"]["duration_frames"]
        times = []
        for k in range(frames):
            t = time.perf_counter()
            render_item_frame(spec, r["spine"], r["item"]["trigger_word_index"], n, int(n * (k + 1) / (frames + 1)), D.SS, base)
            times.append(time.perf_counter() - t)
        out[spec["archetype_id"]] = round(sorted(times)[len(times) // 2], 3)
    return {"machine": f"{platform.machine()} {os.cpu_count()} cpu, python {platform.python_version()}", "size": list(size), "ss": D.SS,
            "s_per_frame": out}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("check", "render", "measure"):
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]

    def opt(name: str, default=None):
        if name in rest:
            i = rest.index(name)
            v = rest[i + 1]
            del rest[i:i + 2]
            return v
        return default

    if cmd == "check":
        base = Path(opt("--base") or Path(rest[0]).parent)
        manifest = json.loads(Path(rest[0]).read_text(encoding="utf-8"))
        status = 0
        for f in check(manifest, base):
            print(f"{f['severity']} {f['rule']} {f['where']}: {f['detail']}")
            status |= f["severity"] == "FAIL"
        return status
    if cmd == "render":
        base = Path(opt("--base") or Path(rest[0]).parent)
        a, _, b = (opt("--frames") or "").partition(":")
        ss = int(opt("--ss", D.SS))
        manifest = json.loads(Path(rest[0]).read_text(encoding="utf-8"))
        row = next(r for r in items_of(manifest, base) if r["item"]["item_id"] == rest[1])
        out = Path(rest[2])
        out.mkdir(parents=True, exist_ok=True)
        n = row["item"]["duration_frames"]
        for f in range(int(a or 0), int(b or n)):
            im = render_item_frame(row["spec"], row["spine"], row["item"]["trigger_word_index"], n, f, ss, base)
            (out / f"{f:05d}.png").write_bytes(D.png_bytes(im))
        return 0
    base = Path(opt("--base") or Path(rest[0]).parent)
    result = measure(json.loads(Path(rest[0]).read_text(encoding="utf-8")), base)
    print(json.dumps(result, indent=1))
    if "--write" in rest:
        doc = catalogue()
        doc["measured"] = result
        CATALOGUE.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        catalogue.cache_clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
