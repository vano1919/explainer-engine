"""The data contracts (docs/CONTRACTS.md, CN-): every file one stage hands to the next is checked against its versioned
JSON Schema (``explainer_engine/schemas/<name>.schema.json``) and then against the contract's semantic rules (frame
geometry, derived-file freshness, index ranges). jsonschema only (plan decision D1: no Pydantic).

    errors(doc, base) -> findings [{rule, severity, where, detail}]      validate(doc, base) raises ContractError on any FAIL

    python -m explainer_engine.core.contracts check <file>... [--base <job folder>]

A finding is FAIL for a schema or invariant breach, and takes its level from the registry (``sourced_rules.level``) when a
hypothesis rule drives it (BP-114: video-model clip geometry), so a hypothesis never FAILs (D-59, CN-11).
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
GEOMETRY = "BP-114"  # clip geometry (CN-08, CN-09): a hypothesis, so its findings are REVIEW


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
    lvl = SR.level(GEOMETRY)
    step, off = SR.T(GEOMETRY, "frames_step"), SR.T(GEOMETRY, "frames_offset")
    if frames is not None:
        if (frames - off) % step:
            out.append(_f("CN-08", where, f"{frames} frames is not {step}k+{off} ({GEOMETRY})", lvl))
        if frames > SR.T(GEOMETRY, "frames_max"):
            out.append(_f("CN-08", where, f"{frames} frames is over {SR.T(GEOMETRY, 'frames_max')} ({GEOMETRY})", lvl))
    for name, v in (("width", width), ("height", height)):
        if v % SR.T(GEOMETRY, "size_multiple"):
            out.append(_f("CN-08", where, f"{name} {v} is not divisible by {SR.T(GEOMETRY, 'size_multiple')} ({GEOMETRY})", lvl))
        elif v % SR.T(GEOMETRY, "two_stage_size_multiple"):
            out.append(_f("CN-08", where, f"{name} {v} is not a multiple of {SR.T(GEOMETRY, 'two_stage_size_multiple')}: "
                                          f"a two-stage render needs it", "REVIEW"))
    return out


def _film_shots(doc: dict, base) -> list[dict]:
    if doc.get("schema") != "film_shots/2":
        return []
    out = []
    fps = doc["fps"]
    if fps != SR.T(GEOMETRY, "native_fps"):
        out.append(_f("CN-09", "fps", f"fps {fps} is not the video model's native {SR.T(GEOMETRY, 'native_fps')} (D-85)", SR.level(GEOMETRY)))
    for s in doc["shots"]:
        if s["lane"] in VIDEO_LANES:
            out += _geometry(s["width"], s["height"], s["duration_frames"], s["id"])
        want = s["seconds"] * fps
        if abs(want - s["duration_frames"]) > SR.T(GEOMETRY, "frames_step"):
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
    return out


def _spine_indices(doc: dict, base, key: str, indices) -> list[dict]:
    if base is None:
        return []
    path = Path(base) / doc["audio_spine"]["path"]
    if not path.exists():
        return [_f("CN-02", "audio_spine", f"{path} does not exist")]
    n = len(json.loads(path.read_text(encoding="utf-8"))["words"])
    return [_f("CN-01", where, f"word_index {i} is past the spine's {n} words") for where, i in indices if i is not None and i >= n]


def _visual_comp(doc: dict, base) -> list[dict]:
    idx = [(f"items[{k}]", it["trigger_word_index"]) for k, it in enumerate(doc["items"])]
    idx += [(f"items[{k}].layers[{j}]", ly["reveal_word_index"]) for k, it in enumerate(doc["items"]) for j, ly in enumerate(it["layers"])]
    return _spine_indices(doc, base, "items", idx)


def _sound_mix(doc: dict, base) -> list[dict]:
    out = _spine_indices(doc, base, "spots", [(f"spots[{k}]", s["word_index"]) for k, s in enumerate(doc["spots"])])
    for k, s in enumerate(doc["spots"]):
        if (s["word_index"] is None) == (s["frame"] is None):
            out.append(_f("CN-01", f"spots[{k}]", "a spot sits on a word_index or on a frame, exactly one"))
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


def _distribution(doc: dict, base) -> list[dict]:
    if base is None:
        return []
    out = []
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


SEMANTIC = {"film_shots": _film_shots, "shot_spec": _shot_spec, "audio_spine": _audio_spine, "visual_comp_manifest": _visual_comp,
            "sound_mix_manifest": _sound_mix, "qa_report": _qa_report, "distribution_package": _distribution,
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
