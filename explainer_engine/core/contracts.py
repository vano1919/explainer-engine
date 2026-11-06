
"""The data contracts (docs/CONTRACTS.md, CN-): every file one stage hands to the next is checked against its versioned
JSON Schema (``explainer_engine/schemas/<name>.schema.json``) and then against the contract's semantic rules (frame
geometry, derived-file freshness, index ranges). jsonschema only (plan decision D1: no Pydantic).

    errors(doc, base) -> findings [{rule, severity, where, detail}]      validate(doc, base) raises ContractError on any FAIL

    python -m explainer_engine.core.contracts check <file>... [--base <job folder>]

A finding is FAIL for a schema or invariant breach, and takes its level from the registry (``sourced_rules.level``) when a
hypothesis rule drives it (BP-139: video-model clip geometry), so a hypothesis never FAILs (D-59, CN-11). BP-139 applies only to
the recipes it names (``applies_to_recipes``, D-105, D-116): the LTX clips (``ltx_i2v``, ``ltx_layout``, ``ltx_restyle``) of
film_shots/2, shot_spec/1 and the J2/J4 shots of film_shots/3, never a J5 or Blender-rendered shot.

The Ink Chronicle contracts (D-96, roadmap section 10; ICW-02): ``film_shots/3`` and ``shot_spec/2`` (CN-17: the 24 fps master
clock and the 2560x1440 frame of BP-167, lane and render-profile agreement), ``shot_route/2`` (the Blender pin of BP-175),
``blender_scene_manifest/1``, ``blender_render_manifest/1``, ``render_checkpoint/1`` (CN-18, the frame-recovery protocol of
roadmap 10.4), ``asset_library/2`` (CN-19) and ``speech_mix_report/1`` (CN-20).
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.standards import sourced_rules as SR

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
VIDEO_LANES = {"KEYFRAME_LTX", "DIALOGUE_CU", "HOST_COMMENTARY", "DRAMA_BLOCKED_3D", "ATMOS_BROLL"}  # film_shots/2: LTX clips
LANES_3 = ("VIDEO_3D", "STILL_3D", "HELPER")  # film_shots/3 (D-97)
BLENDER_LANES = {"VIDEO_3D", "STILL_3D"}  # rendered by Blender (shot_spec/2); HELPER stays with the Python renderers
BLENDER_RECIPES = {"eevee_fast": "blender_eevee/1", "eevee_full": "blender_eevee/1", "eevee_painterly": "blender_eevee/1",
                   "cycles_hero": "blender_cycles/1"}
BLENDER_SPECS = ("shot_spec/2", "shot_spec/3")  # /3 (WP-Q1): /2 plus the look's view transform, shade and line mode
BIBLE = Path(__file__).resolve().parents[1] / "world" / "bible.json"


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@lru_cache(maxsize=None)
def _validator(name: str):
    import jsonschema
    path = SCHEMAS / f"{name}.schema.json"
    if not path.exists():
        raise ContractError(f"unknown contract {name!r}: no schemas/{name}.schema.json")
    return jsonschema.Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def contract_name(doc: dict) -> str:
    """``"audio_spine/1"`` -> ``"audio_spine"``; the document must name its contract (CN-01)."""
    tag = doc.get("schema") if isinstance(doc, dict) else None
    if not isinstance(tag, str) or "/" not in tag:
        raise ContractError("the document does not name its contract in `schema` (<name>/<N>)")
    return tag.split("/")[0]


def _f(rule: str, where: str, detail: str, severity: str = "FAIL") -> dict:
    return {"rule": rule, "severity": severity, "where": where, "detail": detail}


def ltx_recipe(recipe: str | None) -> bool:
    """D-105, D-116: CN-08 / BP-139 bind only the recipes BP-139 names (``ltx_i2v/*``, ``ltx_layout/*``, ``ltx_restyle/*``); a
    Blender, 2.5D or keyframe recipe is outside them."""
    return recipe is not None and any(fnmatch.fnmatchcase(recipe, pat) for pat in SR.T("BP-139", "applies_to_recipes"))


def _geometry(width, height, frames, where: str) -> list[dict]:
    """CN-08 on one video clip: 8k+1 frames, sizes divisible by 32 (two-stage: 64), at most the registry's frame limit."""
    out = []
    lvl = SR.level("BP-139")
    step, off, limit = SR.T("BP-139", "frames_step"), SR.T("BP-139", "frames_offset"), SR.T("BP-139", "frames_max")
    size, two_stage = SR.T("BP-139", "size_multiple"), SR.T("BP-139", "two_stage_size_multiple")
    if frames is not None:
        if (frames - off) % step:
            out.append(_f("CN-08", where, f"{frames} frames is not {step}k+{off} (BP-139)", lvl))
        if frames > limit:
            out.append(_f("CN-08", where, f"{frames} frames is over {limit} (BP-139)", lvl))
    for name, v in (("width", width), ("height", height)):
        if v % size:
            out.append(_f("CN-08", where, f"{name} {v} is not divisible by {size} (BP-139)", lvl))
        elif v % two_stage:
            out.append(_f("CN-08", where, f"{name} {v} is not a multiple of {two_stage}: a two-stage render needs it", "REVIEW"))
    return out


REFUSED_LANES = {
    "HOST_COMMENTARY": "no permanent hosts: card A1 is NO (creator 2026-10-30, D-89); the lane stays in the enum for history only",
    "DRAMA_BLOCKED_3D": "card A2 is 'not now': 3D blocking and LivePortrait/MuseTalk are neither in code in v2 (D-75, D-77)",
}


def _refused_lane(lane: str, where: str) -> list[dict]:
    """A lane the creator rejected cannot reach a renderer (D-89, A2); the enum value stays so older documents still parse."""
    return [_f("CN-11", where, f"lane {lane} is refused: {REFUSED_LANES[lane]}")] if lane in REFUSED_LANES else []


def _film_shots(doc: dict, base) -> list[dict]:
    if doc.get("schema") == "film_shots/3":
        return _film_shots_3(doc)
    if doc.get("schema") != "film_shots/2":
        return []
    out = []
    fps = doc["fps"]
    native = SR.T("BP-139", "native_fps")
    if fps != native:
        out.append(_f("CN-09", "fps", f"fps {fps} is not the video model's native {native} (D-85)", SR.level("BP-139")))
    for s in doc["shots"]:
        out += _refused_lane(s["lane"], s["id"])
        if s["lane"] in VIDEO_LANES:
            out += _geometry(s["width"], s["height"], s["duration_frames"], s["id"])
        if s["lane"] in ("MAP", "COMPENSATOR"):
            out += _catalogue_findings(s["id"], s["archetype"], s["lane"])
        want = s["seconds"] * fps
        if abs(want - s["duration_frames"]) > SR.T("BP-139", "frames_step"):
            out.append(_f("CN-08", s["id"], f"{s['duration_frames']} frames is far from {s['seconds']:g} s at {fps} fps", "REVIEW"))
    return out


def _master(where: str, width, height, fps) -> list[dict]:
    """CN-17 on a Blender-path document: the master frame and clock of BP-167 (2560x1440 at 24 fps, D-104); never a pulldown."""
    out, lvl = [], SR.level("BP-167")
    want_w, want_h, want_fps = SR.T("BP-167", "width"), SR.T("BP-167", "height"), SR.T("BP-167", "fps")
    if fps is not None and fps != want_fps:
        out.append(_f("CN-09", where, f"fps {fps} is not the master's {want_fps} (BP-167, D-104)", lvl))
    if width is not None and (width, height) != (want_w, want_h):
        out.append(_f("CN-17", where, f"{width}x{height} is not the {want_w}x{want_h} master (BP-167)", lvl))
    return out


def _bible_version() -> str | None:
    try:
        return json.loads(BIBLE.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None


def _film_shots_3(doc: dict) -> list[dict]:
    """CN-17 on ``film_shots/3`` (D-97): the master clock and frame, exact frame counts (Blender renders the frames it is
    asked for: round(seconds x fps), no 8k+1 rounding), a HELPER shot names a catalogue archetype (CN-15), and the cards are
    planned under the current world bible (a stale version is REVIEW: the look may have moved). The LTX clips of a J2/J4
    shot (``ltx_clips``, D-116) take CN-08's 8k+1 frames and sizes in 32."""
    fps = doc["fps"]
    out = _master("fps", None, None, fps)
    have = _bible_version()
    if have is not None and doc["style"]["bible_version"] != have:
        out.append(_f("CN-17", "style.bible_version", f"planned under bible {doc['style']['bible_version']}, the bible is {have}",
                      "REVIEW"))
    for s in doc["shots"]:
        out += _master(s["id"], s["width"], s["height"], None)
        want = round(s["seconds"] * fps)
        if s["duration_frames"] != want:
            out.append(_f("CN-17", s["id"], f"{s['duration_frames']} frames is not {s['seconds']:g} s at {fps} fps ({want})"))
        if s["lane"] == "HELPER":
            out += _catalogue_findings(s["id"], s["helper_archetype"])
        # D-116: a J2/J4 shot's LTX clips are LTX generations, so CN-08 / BP-139 bind them (ltx_layout/1, ltx_restyle/1);
        # the shot itself stays on the Blender master clock and frame above
        if s.get("route") in ("J2", "J4"):
            for n, c in enumerate(s.get("ltx_clips") or [], 1):
                out += _geometry(c["width"], c["height"], c["frames"], f"{s['id']}.clip{n}")
    return out


def _shot_spec(doc: dict, base) -> list[dict]:
    if doc["schema"] in BLENDER_SPECS:
        return _shot_spec_2(doc)
    out = []
    out += _refused_lane(doc["lane"], doc["shot_id"])
    m = doc["model"]
    if not (m["sha256"] or m["revision"]):
        out.append(_f("CN-07", "model", "a model is named by its sha256 or revision: a name alone changes under the cache"))
    if doc["lane"] in VIDEO_LANES and doc["frames"] is not None and ltx_recipe(doc["recipe"]):
        out += _geometry(doc["width"], doc["height"], doc["frames"], doc["shot_id"])
    return out


def _shot_spec_2(doc: dict) -> list[dict]:
    """CN-17 on ``shot_spec/2``: BP-167's master at render_scale 1.0 (a lower scale is the declared tier of roadmap 9.5), the
    recipe matches the render profile (Cycles only for ``cycles_hero``), a lip-synced shot is a VIDEO_3D shot with its
    Rhubarb cues and an on-screen mouth, and the Line Art weight is inside BP-173's band."""
    sid, out = doc["shot_id"], []
    out += _master(sid, doc["frame"]["width"], doc["frame"]["height"], doc["clock"]["fps"])
    profile = doc["render"]["profile"]
    if BLENDER_RECIPES[profile] != doc["recipe"]:
        out.append(_f("CN-17", sid, f"recipe {doc['recipe']} does not render profile {profile} ({BLENDER_RECIPES[profile]})"))
    perf = doc["performance"]
    if perf["lipsync"]:
        if doc["lane"] != "VIDEO_3D":
            out.append(_f("CN-17", sid, f"a lip-synced shot is VIDEO_3D, not {doc['lane']}"))
        if perf["rhubarb"] is None:
            out.append(_f("CN-17", sid, "a lip-synced shot needs its Rhubarb mouth cues (performance.rhubarb)"))
        if perf["dialogue_cover"] != "on_screen":
            out.append(_f("CN-17", sid, "a lip-synced shot shows the mouth: dialogue_cover is on_screen"))
    elif perf["rhubarb"] is not None or perf["dialogue_cover"] == "on_screen":
        out.append(_f("CN-17", sid, "mouth cues or an on-screen mouth on a shot that is not lip-synced"))
    lo, hi = SR.T("BP-173", "weight_px_1440")
    if doc["schema"] == "shot_spec/3" and doc["look"]["line_mode"] == "none":
        return out   # /3: a look without a drawn line has no Line Art weight to hold to BP-173's band
    if not lo <= doc["look"]["line_weight_px"] <= hi:
        out.append(_f("CN-17", sid, f"Line Art weight {doc['look']['line_weight_px']:g} px is outside {lo:g}-{hi:g} px at 1440p (BP-173)",
                      SR.level("BP-173")))
    return out


def _shot_route(doc: dict, base) -> list[dict]:
    """CN-17 on ``shot_route/2``: the route was written against the Blender pin of BP-175; a HELPER shot is drawn by the Python
    renderers from compensator items (no spec), a VIDEO_3D/STILL_3D shot is one Blender spec of its role and no item."""
    if doc["schema"] != "shot_route/2":
        return []
    out, pin = [], doc["pins"]["blender"]
    want = SR.T("BP-175", "blender_version"), SR.T("BP-175", "series")
    if (pin["version"], pin["series"]) != want:
        out.append(_f("CN-17", "pins.blender", f"Blender {pin['version']} {pin['series']} is not the pinned {want[0]} {want[1]} (BP-175)",
                      SR.level("BP-175")))
    seen: set[str] = set()
    for r in doc["routes"]:
        sid = r["shot_id"]
        if sid in seen:
            out.append(_f("CN-17", sid, "the shot is routed twice"))
        seen.add(sid)
        if r["lane"] == "HELPER":
            if r["recipe"] != "python_helper/1" or r["specs"] or not r["comp_items"]:
                out.append(_f("CN-17", sid, "a HELPER shot is python_helper/1 with its compensator items and no Blender spec"))
        else:
            role = "video" if r["lane"] == "VIDEO_3D" else "still"
            if r["recipe"] == "python_helper/1" or r["comp_items"] or [s["role"] for s in r["specs"]] != [role]:
                out.append(_f("CN-17", sid, f"a {r['lane']} shot is one Blender spec of role {role} and no compensator item"))
    return out


def _blender_scene(doc: dict, base) -> list[dict]:
    out = []
    frames = [c["frame"] for c in doc["camera_path"]]
    if frames != sorted(set(frames)):
        out.append(_f("CN-01", "camera_path", "camera samples are in frame order, one per frame"))
    for k, b in enumerate(doc["bounds"]):
        if any(lo > hi for lo, hi in zip(b["min"], b["max"])):
            out.append(_f("CN-01", f"bounds[{k}]", f"{b['object']}: min is above max"))
    ids = [a["id"] for a in doc["assets"]]
    if len(ids) != len(set(ids)):
        out.append(_f("CN-01", "assets", "an asset is listed twice"))
    o = doc["objects"]
    if o["total"] < o["meshes"] + o["armatures"] + o["lights"] + o["cameras"]:
        out.append(_f("CN-01", "objects", "the total is below the sum of its kinds"))
    return out


def _blender_render(doc: dict, base) -> list[dict]:
    """CN-18 on ``blender_render_manifest/1``: a clip exists only when every frame was written (roadmap 10.4 rule 3), at the
    master's clock and size, and the measured seconds per frame is the total over the frames written (it feeds job_speeds)."""
    out, sid = [], doc["shot_id"]
    n, want = doc["frames_written"], doc["frames_expected"]
    if n > want:
        out.append(_f("CN-18", sid, f"{n} frames written of {want} expected"))
    if (doc["output"] is not None) != (n == want):
        out.append(_f("CN-18", sid, "the clip is built only when every frame is written, and then it must be recorded"))
    if doc["output"] is not None:
        o = doc["output"]
        out += _master(sid, o["width"], o["height"], o["fps"])
    spf = doc["seconds_per_frame"]
    if (spf is None) != (n == 0) or (spf is not None and abs(spf - doc["seconds_total"] / n) > max(0.01, 0.01 * spf)):
        out.append(_f("CN-18", sid, "seconds_per_frame is seconds_total / frames_written (null when nothing was written)"))
    return out


def _render_checkpoint(doc: dict, base) -> list[dict]:
    """CN-18 on ``render_checkpoint/1`` (roadmap 10.4): a frame index once, inside the shot; a RENDERED frame has no remote copy
    yet; a DURABLY_STORED or COMMITTED frame was verified remotely (the same sha256 as the local file) at a recorded time; the
    vault prefix is ``blender/<job_id>/<shot_key>/frames/``. Only COMMITTED frames count for a resume."""
    out = []
    want = f"blender/{doc['job_id']}/{doc['shot_key']}/frames/"
    if doc["vault_prefix"] != want:
        out.append(_f("CN-18", "vault_prefix", f"{doc['vault_prefix']} is not {want}"))
    seen: set[int] = set()
    for fr in doc["frames"]:
        where = f"frames[{fr['index']}]"
        if fr["index"] in seen or fr["index"] >= doc["frames_expected"]:
            out.append(_f("CN-18", where, f"index {fr['index']} is repeated or outside the shot's {doc['frames_expected']} frames"))
        seen.add(fr["index"])
        if fr["state"] == "RENDERED":
            if fr["remote_sha256"] is not None or fr["stored_at"] is not None:
                out.append(_f("CN-18", where, "a RENDERED frame has no verified remote copy yet"))
        elif fr["remote_sha256"] != fr["local_sha256"] or fr["stored_at"] is None:
            out.append(_f("CN-18", where, f"a {fr['state']} frame's remote sha256 equals the local one, with the time it was stored"))
    return out


THIRD_PARTY = {"licensed", "cc0", "cc-by-4.0", "mit-tool", "gpl-tool-only", "vendor-terms", "community-licence-revenue-capped",
               "restricted-territory"}


def _asset_library(doc: dict, base) -> list[dict]:
    """CN-19 on ``asset_library/2`` (D-110, roadmap 21.4-21.5): ids are unique; a dependency is a record of the library with
    the same sha256; external storage names its path and git storage none; a third-party licence records where and when it was
    read; ``commercial_use: unknown`` blocks approval; a costume derives from a model (the identity carrier, D-101); an
    animation names the skeleton it plays on. ``asset_library/1`` keeps its schema-only reading."""
    if doc["schema"] != "asset_library/2":
        return []
    out = []
    by_id: dict[str, dict] = {}
    for it in doc["items"]:
        if it["id"] in by_id:
            out.append(_f("CN-19", it["id"], "the id is used twice"))
        by_id[it["id"]] = it
    for it in doc["items"]:
        aid, lic = it["id"], it["licence"]
        for d in it["deps"]:
            dep = by_id.get(d["asset_id"])
            if dep is None:
                out.append(_f("CN-19", aid, f"depends on {d['asset_id']}, which is not in the library"))
            elif dep["sha256"] != d["sha256"]:
                out.append(_f("CN-19", aid, f"depends on {d['asset_id']} at another sha256: re-link it"))
        st = it["storage"]
        if (st["location"] == "external") != (st["external_path"] is not None):
            out.append(_f("CN-19", aid, "external storage names its vault path; git storage names none"))
        if lic["status"] in THIRD_PARTY:
            for k in ("source_url", "revision_or_version", "inspected_on"):
                if not lic.get(k):
                    out.append(_f("CN-19", aid, f"a third-party licence ({lic['status']}) records {k}"))
        if it["approval"]["status"] == "approved" and lic["commercial_use"] == "unknown":
            out.append(_f("CN-19", aid, "commercial use is unknown: the asset cannot be approved (roadmap 21.4)"))
        if it["kind"] == "costume":
            parent = by_id.get(it["lineage"]["parent"] or "")
            if parent is None or parent["kind"] != "model":
                out.append(_f("CN-19", aid, "a costume derives from its character's model (lineage.parent, D-101)"))
        if it["kind"] == "animation" and not (it.get("three_d") or {}).get("skeleton_id"):
            out.append(_f("CN-19", aid, "an animation names the skeleton it was authored for (three_d.skeleton_id)"))
    return out


def _speech_mix(doc: dict, base) -> list[dict]:
    """CN-20 on ``speech_mix_report/1``: the share is the narrator's words over the audible words (``voiced: false`` excluded,
    D-99); the band itself is BP-105's and is judged by its reader, never stored here."""
    n, d = doc["narrator_words"], doc["dialogue_words"]
    want = n / (n + d) if n + d else 0.0
    if abs(doc["narrator_share_words"] - want) > 0.0005:
        return [_f("CN-20", "narrator_share_words", f"{doc['narrator_share_words']} is not {n} / ({n} + {d}) = {want:.3f}")]
    return []


def _audio_spine(doc: dict, base) -> list[dict]:
    out, fps, total = [], doc["fps"], doc["total_frames"]
    prev_start = -1.0
    for w in doc["words"]:
        where = f"words[{w['i']}]"
        if w["end_s"] < w["start_s"] or w["start_s"] < prev_start:
            out.append(_f("CN-01", where, "words are in order and each ends after it starts"))
        prev_start = w["start_s"]
        if w["start_frame"] != round(w["start_s"] * fps) or w["end_frame"] != round(w["end_s"] * fps):
            out.append(_f("CN-01", where, f"frames do not match seconds at {fps} fps"))
        if w["end_frame"] > total:
            out.append(_f("CN-01", where, f"ends at frame {w['end_frame']}, past the {total} frames of the read"))
    if doc["schema"] == "audio_spine/2":
        out += _spine_windows(doc)
    return out


def _spine_windows(doc: dict) -> list[dict]:
    """CN-01 on the post-hoc windows of an ``audio_spine/2`` (D-88): in order, not overlapping, inside the read's frames, each
    after a real word it does not precede, and no word frame inside one (a word is inside a window when their frame ranges
    overlap). A /1 document keeps its older, looser reading: nothing in it changes."""
    out, words, total = [], doc["words"], doc["total_frames"]
    prev_end, prev_after = 0, -1
    for k, h in enumerate(doc["post_hoc_shots"]):
        where = f"post_hoc_shots[{k}]"
        s, e, after = h["start_frame"], h["end_frame"], h["after_word"]
        if e <= s:
            out.append(_f("CN-01", where, f"the window {s}..{e} is empty or reversed"))
        if s < prev_end:
            out.append(_f("CN-01", where, f"the window starts at frame {s}, before the previous one ends at {prev_end}: windows are in order and do not overlap"))
        if e > total:
            out.append(_f("CN-01", where, f"ends at frame {e}, past the {total} frames of the episode"))
        if after >= len(words):
            out.append(_f("CN-01", where, f"after_word {after} is past the spine's {len(words)} words"))
        else:
            if after < prev_after:
                out.append(_f("CN-01", where, f"after_word {after} is before the previous window's {prev_after}"))
            if after >= 0 and s < words[after]["end_frame"]:
                out.append(_f("CN-01", where, f"the window opens at frame {s}, before word {after} ends at {words[after]['end_frame']}"))
        for w in words:
            if w["start_frame"] < e and w["end_frame"] > s:
                out.append(_f("CN-01", where, f"word {w['i']} ({w['start_frame']}..{w['end_frame']}) falls inside the window {s}..{e}"))
                break
        prev_end, prev_after = max(prev_end, e), max(prev_after, after)
    return out


def _spine_ref(doc: dict) -> dict:
    """The file reference of the spine a document sits on: top level in the /1 contracts, ``derived_from`` in /2 (D-88)."""
    return doc["audio_spine"] if "audio_spine" in doc else doc["derived_from"]["audio_spine"]


def _spine_indices(doc: dict, base, key: str, indices) -> list[dict]:
    if base is None:
        return []
    path = Path(base) / _spine_ref(doc)["path"]
    if not path.exists():
        return [_f("CN-02", "audio_spine", f"{path} does not exist")]
    n = len(json.loads(path.read_text(encoding="utf-8"))["words"])
    return [_f("CN-01", where, f"word_index {i} is past the spine's {n} words") for where, i in indices if i is not None and i >= n]


def _catalogue_findings(where: str, archetype: str, lane: str | None = None) -> list[dict]:
    """CN-15: an archetype named by a shot, an item or a spec is one of the catalogue, and on the lane its family belongs to."""
    from explainer_engine.edit import visual_compensator as VC
    if archetype not in VC.ids():
        return [_f("CN-15", where, f"archetype {archetype!r} is not in the catalogue (explainer_engine/edit/archetypes.json)")]
    if lane is not None and VC.lane_of(archetype) != lane:
        return [_f("CN-15", where, f"{archetype} belongs on the {VC.lane_of(archetype)} lane, not {lane}")]
    return []


def _visual_comp(doc: dict, base) -> list[dict]:
    idx = [(f"items[{k}]", it["trigger_word_index"]) for k, it in enumerate(doc["items"])]
    idx += [(f"items[{k}].layers[{j}]", ly["reveal_word_index"]) for k, it in enumerate(doc["items"]) for j, ly in enumerate(it["layers"])]
    out = [f for k, it in enumerate(doc["items"]) for f in _catalogue_findings(f"items[{k}]", it["archetype_id"])]
    return out + _spine_indices(doc, base, "items", idx)


def _comp_spec(doc: dict, base) -> list[dict]:
    from explainer_engine.edit import visual_compensator as VC
    return VC.payload_findings(doc, Path(base) if base is not None else None)


def _sound_mix(doc: dict, base) -> list[dict]:
    out = _spine_indices(doc, base, "spots", [(f"spots[{k}]", s["word_index"]) for k, s in enumerate(doc["spots"])])
    for k, s in enumerate(doc["spots"]):
        if (s["word_index"] is None) == (s["frame"] is None):
            out.append(_f("CN-01", f"spots[{k}]", "a spot sits on a word_index or on a frame, exactly one"))
    if doc["schema"] == "sound_mix_manifest/2":
        out += _sound_mix_2(doc, base)
    return out


HIT_LAYERS = ("sub", "body", "air")


def _sound_mix_2(doc: dict, base) -> list[dict]:
    """CN-16 on a ``sound_mix_manifest/2``: every frame inside ``total_frames`` (which is the spine's), the scenes follow one
    another without a gap or an overlap, and each hit group holds exactly one sub, one body and one air layer."""
    out, total = [], doc["total_frames"]

    def inside(where: str, start: int, end: int | None = None) -> None:
        end = start if end is None else end
        if end < start:
            out.append(_f("CN-16", where, f"ends at frame {end}, before it starts at {start}"))
        if end > total:
            out.append(_f("CN-16", where, f"frame {end} is past the manifest's {total} frames"))

    for key in ("dialogue", "scenes", "beds", "music", "vacuums"):
        for k, row in enumerate(doc[key]):
            inside(f"{key}[{k}]", row["start_frame"], row["end_frame"])
    for k, v in enumerate(doc["vacuums"]):
        if not v["start_frame"] <= v["reveal_frame"] <= v["end_frame"]:
            out.append(_f("CN-16", f"vacuums[{k}]", f"reveal_frame {v['reveal_frame']} is outside the vacuum {v['start_frame']}..{v['end_frame']}"))
    for k, c in enumerate(doc["cues"]):
        inside(f"cues[{k}]", c["frame"])
    for k, s in enumerate(doc["spots"]):
        if s["frame"] is not None:
            inside(f"spots[{k}]", s["frame"])
    prev = None
    for k, sc in enumerate(sorted(doc["scenes"], key=lambda r: r["start_frame"])):
        if prev is not None and sc["start_frame"] != prev["end_frame"]:
            kind = "overlaps" if sc["start_frame"] < prev["end_frame"] else "leaves a gap after"
            out.append(_f("CN-16", f"scenes {sc['scene']}", f"starts at frame {sc['start_frame']} and {kind} {prev['scene']}, which ends at {prev['end_frame']}"))
        prev = sc
    groups: dict[str, list[str]] = {}
    for k, s in enumerate(doc["spots"]):
        if s["group"] is None and s["layer"] in HIT_LAYERS:
            out.append(_f("CN-16", f"spots[{k}]", f"layer {s['layer']} belongs to a hit group, and this spot names none"))
        elif s["group"] is not None:
            if s["layer"] not in HIT_LAYERS:
                out.append(_f("CN-16", f"spots[{k}]", f"a spot in group {s['group']!r} is a sub, body or air layer, not {s['layer']!r}"))
            groups.setdefault(s["group"], []).append(s["layer"])
    for name, layers in groups.items():
        if sorted(layers) != sorted(HIT_LAYERS):
            out.append(_f("CN-16", f"group {name}", f"a hit group has exactly one sub, one body and one air layer, this one has {sorted(layers)}"))
    if base is not None:
        path = Path(base) / _spine_ref(doc)["path"]
        if path.exists():
            spine = json.loads(path.read_text(encoding="utf-8"))
            for key in ("total_frames", "fps"):
                if spine.get(key) != doc[key]:
                    out.append(_f("CN-16", key, f"{doc[key]} differs from the spine's {spine.get(key)}"))
    return out


def _qa_report(doc: dict, base) -> list[dict]:
    from explainer_engine.core.ledger import MAX_FAILURES
    out = []
    failed = [c["check_id"] for c in doc["checks"] if c["severity"] == "FAIL" and not c["passed"]]
    if doc["status"] == "PASS" and failed:
        out.append(_f("CN-13", "status", f"PASS with failed FAIL checks: {failed}"))
    d = doc["retry_directive"]
    if d and d["attempt"] >= MAX_FAILURES + 1:
        out.append(_f("CN-13", "retry_directive", f"attempt {d['attempt']}: after {MAX_FAILURES} failures the item stops and asks (OR-04)"))
    return out


ASSEMBLED_KEY = "assembled_video"  # the job_manifest artifact key of the finished episode video


def _distribution(doc: dict, base) -> list[dict]:
    """CN-14: the listed files exist unchanged, and when the job folder holds its manifest the package was cut from the video
    the job assembled (a package from an older render is refused)."""
    if base is None:
        return []
    out = []
    manifest = Path(base) / "job_manifest.json"
    if manifest.exists():
        row = json.loads(manifest.read_text(encoding="utf-8")).get("artifacts", {}).get(ASSEMBLED_KEY)
        if row is None:
            out.append(_f("CN-14", "source_episode_sha256", f"the job records no {ASSEMBLED_KEY} artifact to cut a package from"))
        elif row["sha256"] != doc["source_episode_sha256"]:
            out.append(_f("CN-14", "source_episode_sha256", "the package was cut from another render than the job's assembled video"))
    for name, ref in doc["files"].items():
        if ref is None:
            continue
        path = Path(base) / ref["path"]
        if not path.exists():
            out.append(_f("CN-14", f"files.{name}", f"{ref['path']} does not exist"))
        elif sha256_file(path) != ref["sha256"]:
            out.append(_f("CN-14", f"files.{name}", f"{ref['path']} changed since it was recorded"))
    return out


def _job_manifest(doc: dict, base) -> list[dict]:
    out = []
    if doc["reopen_to"] is not None and not doc["state"].startswith(("FAILED", "ABORTED", "CANCELLED")):
        out.append(_f("CN-03", "reopen_to", "reopen_to belongs to a terminal state only"))
    if doc["history"] and doc["history"][-1]["to"] != doc["state"]:
        out.append(_f("CN-03", "history", "the last history row does not end in the current state"))
    return out


def variants_sha256(doc: dict) -> str:
    """What the creator saw and picked: the sha256 of the variants array, so a later edit makes the choice stale (CN-04)."""
    return hashlib.sha256(json.dumps(doc["variants"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def variant_sums(variant: dict) -> list[dict]:
    """VP-01 (invariant 7): the blocks of every segment add up to its window, and the stored shares add up to 1. A plan whose
    numbers do not add up cannot be scored, so it is refused here and not weighed."""
    out = []
    for seg in variant.get("segments", []):
        got = sum(b["seconds"] for b in seg["blocks"])
        if abs(got - seg["window_s"]) > 0.01:
            out.append(_f("VP-01", f"{variant['id']} {seg['id']}", f"the blocks add up to {got:g} s, the window is {seg['window_s']:g} s"))
    shares = [v for k, v in variant.get("dynamics", {}).items() if k.startswith("share_")]
    if shares and abs(sum(shares) - 1.0) > 0.006:
        out.append(_f("VP-01", f"{variant['id']} dynamics", f"the shares add up to {sum(shares):.3f}, not 1"))
    return out


def _script_variants(doc: dict, base) -> list[dict]:
    if doc["schema"] != "script_variants/2":
        return []
    return [f for v in doc["variants"] for f in variant_sums(v)]


SEMANTIC = {"film_shots": _film_shots, "script_variants": _script_variants, "shot_spec": _shot_spec, "audio_spine": _audio_spine, "visual_comp_manifest": _visual_comp,
            "comp_spec": _comp_spec, "sound_mix_manifest": _sound_mix, "qa_report": _qa_report, "distribution_package": _distribution,
            "job_manifest": _job_manifest, "shot_route": _shot_route, "blender_scene_manifest": _blender_scene,
            "blender_render_manifest": _blender_render, "render_checkpoint": _render_checkpoint, "asset_library": _asset_library,
            "speech_mix_report": _speech_mix}


def derived_findings(doc: dict, base) -> list[dict]:
    """CN-02: a derived file names every input with its sha256; an input that changed makes it stale."""
    out = []
    for name, ref in (doc.get("derived_from") or {}).items():
        path = Path(base) / ref["path"]
        if not path.exists():
            out.append(_f("CN-02", f"derived_from.{name}", f"{ref['path']} does not exist"))
        elif sha256_file(path) != ref["sha256"]:
            out.append(_f("CN-02", f"derived_from.{name}", f"{ref['path']} changed: this file is stale, re-derive it (never hand-edit)"))
    return out


def errors(doc: dict, base: Path | str | None = None) -> list[dict]:
    """Every finding of a document: the schema first (CN-01; nothing else is read past a schema error), then the contract's
    own rules, then the freshness of a derived file when ``base`` (the job folder its paths are relative to) is given."""
    name = contract_name(doc)
    found = []
    for e in sorted(_validator(name).iter_errors(doc), key=lambda e: list(map(str, e.path))):
        found.append(_f("CN-01", "/".join(map(str, e.path)) or "document", e.message[:300]))
    if found:
        return found
    if name in SEMANTIC:
        found += SEMANTIC[name](doc, base)
    if base is not None:
        found += derived_findings(doc, base)
    return found


def validate(doc: dict, base: Path | str | None = None) -> list[dict]:
    """Raise ContractError when any finding FAILs; return the REVIEW findings."""
    found = errors(doc, base)
    bad = [f for f in found if f["severity"] == "FAIL"]
    if bad:
        raise ContractError("; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad))
    return found


def spec_fps(spec: dict) -> int:
    """The frame rate of a shot spec: ``fps`` in /1, ``clock.fps`` in /2 and /3."""
    return spec["clock"]["fps"] if spec.get("schema") in BLENDER_SPECS else spec["fps"]


def cross_fps(manifest: dict, film_shots: dict | None = None, specs: list[dict] | None = None) -> list[dict]:
    """CN-09: one frame rate across the job manifest, the shot cards and every video lane's (or Blender lane's) shot spec."""
    fps = manifest["fps"]
    out = []
    if film_shots is not None and film_shots.get("fps") not in (None, fps):
        out.append(_f("CN-09", "film_shots.fps", f"{film_shots['fps']} differs from the job's {fps}"))
    for s in specs or []:
        if s["lane"] in VIDEO_LANES | BLENDER_LANES and spec_fps(s) != fps:
            out.append(_f("CN-09", s["shot_id"], f"shot spec fps {spec_fps(s)} differs from the job's {fps}"))
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "check":
        print(__doc__)
        return 2
    base = None
    if "--base" in argv:
        i = argv.index("--base")
        base = argv[i + 1]
        del argv[i:i + 2]
    status = 0
    for name in argv[1:]:
        for f in errors(json.loads(Path(name).read_text(encoding="utf-8")), base or Path(name).parent):
            print(f"{f['severity']} {f['rule']} {name} {f['where']}: {f['detail']}")
            status |= f["severity"] == "FAIL"
    return status


if __name__ == "__main__":
    raise SystemExit(main())
