"""The data contracts (docs/CONTRACTS.md, CN-): every file one stage hands to the next is checked against its versioned
JSON Schema (``explainer_engine/schemas/<name>.schema.json``) and then against the contract's semantic rules (frame
geometry, derived-file freshness, index ranges). jsonschema only (plan decision D1: no Pydantic).

    errors(doc, base) -> findings [{rule, severity, where, detail}]      validate(doc, base) raises ContractError on any FAIL

    python -m explainer_engine.core.contracts check <file>... [--base <job folder>]

A finding is FAIL for a schema or invariant breach, and takes its level from the registry (``sourced_rules.level``) when a
hypothesis rule drives it (BP-139: video-model clip geometry), so a hypothesis never FAILs (D-59, CN-11).
"""

from __future__ import annotations

import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.standards import sourced_rules as SR

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
VIDEO_LANES = {"KEYFRAME_LTX", "DIALOGUE_CU", "HOST_COMMENTARY", "DRAMA_BLOCKED_3D", "ATMOS_BROLL"}


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


def _film_shots(doc: dict, base) -> list[dict]:
    if doc.get("schema") != "film_shots/2":
        return []
    out = []
    fps = doc["fps"]
    native = SR.T("BP-139", "native_fps")
    if fps != native:
        out.append(_f("CN-09", "fps", f"fps {fps} is not the video model's native {native} (D-85)", SR.level("BP-139")))
    for s in doc["shots"]:
        if s["lane"] in VIDEO_LANES:
            out += _geometry(s["width"], s["height"], s["duration_frames"], s["id"])
        if s["lane"] in ("MAP", "COMPENSATOR"):
            out += _catalogue_findings(s["id"], s["archetype"], s["lane"])
        want = s["seconds"] * fps
        if abs(want - s["duration_frames"]) > SR.T("BP-139", "frames_step"):
            out.append(_f("CN-08", s["id"], f"{s['duration_frames']} frames is far from {s['seconds']:g} s at {fps} fps", "REVIEW"))
    return out


def _shot_spec(doc: dict, base) -> list[dict]:
    out = []
    m = doc["model"]
    if not (m["sha256"] or m["revision"]):
        out.append(_f("CN-07", "model", "a model is named by its sha256 or revision: a name alone changes under the cache"))
    if doc["lane"] in VIDEO_LANES and doc["frames"] is not None:
        out += _geometry(doc["width"], doc["height"], doc["frames"], doc["shot_id"])
    return out


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
            "job_manifest": _job_manifest}


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


def cross_fps(manifest: dict, film_shots: dict | None = None, specs: list[dict] | None = None) -> list[dict]:
    """CN-09: one frame rate across the job manifest, the shot cards and every video lane's shot spec."""
    fps = manifest["fps"]
    out = []
    if film_shots is not None and film_shots.get("fps") not in (None, fps):
        out.append(_f("CN-09", "film_shots.fps", f"{film_shots['fps']} differs from the job's {fps}"))
    for s in specs or []:
        if s["lane"] in VIDEO_LANES and s["fps"] != fps:
            out.append(_f("CN-09", s["shot_id"], f"shot spec fps {s['fps']} differs from the job's {fps}"))
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
