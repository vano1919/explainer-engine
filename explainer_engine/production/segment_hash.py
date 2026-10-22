"""Per-segment hashes (D-70 stage F): when a script changes, only what depends on the changed segments is made again.

A segment's voice depends on its spoken text (lines: text, tags, emphasis, pause_after, speaker); its pictures on their
prompts and references; its timing and edit on both plus the shots. ``stale(old, new)`` names, per changed segment, which
artifacts are out of date, so a fix to one line never re-voices or re-paints the rest. stdlib only.
"""

from __future__ import annotations

import hashlib
import json

VOICE_KEYS = ("text", "tags", "emphasis", "pause_after", "speaker")


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _pictures(seg: dict) -> dict:
    out = {}
    for s in seg.get("shots", []):
        p = s["picture"]
        if isinstance(p, dict):
            out[p["id"]] = _h({k: v for k, v in p.items() if k != "id"})
        else:
            out[p] = _h(p)
    return out


def hashes(doc: dict) -> dict:
    """{segment id: {voice, pictures: {picture id: hash}, edit}}."""
    out = {}
    for seg in doc["segments"]:
        voice = _h([{k: ln.get(k) for k in VOICE_KEYS} for ln in seg["lines"]])
        pics = _pictures(seg)
        edit = _h([voice, sorted(pics.items()), seg.get("shots"), [ln.get("visual_beats") for ln in seg["lines"]],
                   seg.get("audio"), seg.get("scene")])
        out[seg["id"]] = {"voice": voice, "pictures": pics, "edit": edit}
    return out


def stale(old: dict, new: dict) -> dict:
    """What to make again: {segment id: {"voice": bool, "pictures": [ids], "edit": bool, "removed"?: True}}.
    A segment with nothing out of date is left out. ``old`` and ``new`` are scripts or the output of ``hashes``."""
    a = old if all(isinstance(v, dict) and "voice" in v for v in old.values()) and "segments" not in old else hashes(old)
    b = new if all(isinstance(v, dict) and "voice" in v for v in new.values()) and "segments" not in new else hashes(new)
    out = {}
    for sid, h in b.items():
        was = a.get(sid)
        if was is None:
            out[sid] = {"voice": True, "pictures": sorted(h["pictures"]), "edit": True}
            continue
        pics = sorted(p for p, ph in h["pictures"].items() if was["pictures"].get(p) != ph)
        row = {"voice": was["voice"] != h["voice"], "pictures": pics, "edit": was["edit"] != h["edit"]}
        if row["voice"] or pics or row["edit"]:
            out[sid] = row
    for sid in a:
        if sid not in b:
            out[sid] = {"voice": False, "pictures": [], "edit": True, "removed": True}
    return out


def check(doc: dict, library: dict | None = None) -> list[dict]:
    """PV-59: a segment's ``asset_ids`` are records of the asset library and the script's ``bible`` version exists.
    PV-60: an approved segment review was given on the segment as it is now (its ``review.hash`` is the current edit hash)."""
    out = []
    used = [(seg["id"], a) for seg in doc["segments"] for a in seg.get("asset_ids", [])]
    if used:
        if library is None:
            from explainer_engine.assets import library as L
            library = L.load() if L.PATH.exists() else {"items": []}
        known = {r["id"] for r in library.get("items", [])}
        for sid, a in used:
            if a not in known:
                out.append({"rule": "PV-59", "severity": "FAIL", "where": sid, "detail": f"asset {a} is not in the asset library"})
    if doc.get("bible"):
        from explainer_engine.world import bible as B
        if doc["bible"]["version"] not in B.versions():
            out.append({"rule": "PV-59", "severity": "FAIL", "where": "bible",
                        "detail": f"world bible version {doc['bible']['version']} never existed (known: {B.versions()})"})
    now = hashes(doc)
    for seg in doc["segments"]:
        r = seg.get("review")
        if r and r["status"] == "approved":
            if not r.get("by"):
                out.append({"rule": "PV-60", "severity": "FAIL", "where": seg["id"], "detail": "an approved review needs a name (by)"})
            if r.get("hash") != now[seg["id"]]["edit"]:
                out.append({"rule": "PV-60", "severity": "REVIEW", "where": seg["id"],
                            "detail": "the segment changed after its review: show it again (python -m explainer_engine.production"
                                      ".segment_hash <script> prints the current hashes)"})
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.segment_hash",
                                 description="per-segment hashes of a production script, or what a new version makes stale")
    ap.add_argument("script")
    ap.add_argument("--against", help="an older version of the script: print what to make again")
    a = ap.parse_args(argv)
    new = json.loads(Path(a.script).read_text(encoding="utf-8"))
    if a.against:
        print(json.dumps(stale(json.loads(Path(a.against).read_text(encoding="utf-8")), new), indent=2))
    else:
        print(json.dumps(hashes(new), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
