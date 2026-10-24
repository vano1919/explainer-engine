"""AC-01..AC-04: the asset library. Every reusable picture is one record; a shot list is turned into the list of assets it
needs, and only what the library lacks is drawn (the paid part). stdlib only.

Record: ``{"id": "<kind>.<name>[.<variant>]" (P-66), "kind", "path", "name", "angle"?, "facing"?, "expression"?, "light"?,
"size_kind"? (a row of layout.SIZES), "foot"? (share of the cut-out's height below the ground contact, default 0),
"source": {"model", "lora", "prompt", "seed", "sha256"?}, "style"?: {"score", "control", "verdict"}, "approved": bool,
"tags": [...]}``.

    python -m explainer_engine.compose.library <library.json> needs <shots.json>   # what must be drawn for these shots
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from explainer_engine.core.store import write_json_atomic

KINDS = ("background", "hero", "prop", "crowd", "fx")
ANGLES = ("front", "three_quarter", "side", "back")
# AC-03: a side or three-quarter view facing the other way is the same drawing mirrored (no new paid picture); a front or
# back view is not mirrored (a scarf, a bag, a parting would swap sides)
MIRRORABLE = ("three_quarter", "side")
ID = re.compile(r"^(background|hero|prop|crowd|fx)\.[a-z0-9_]+(\.[a-z0-9_]+)*$")
REQUIRED = {"background": ("light",), "hero": ("angle", "expression", "size_kind"), "prop": ("size_kind",),
            "crowd": ("angle", "size_kind"), "fx": ()}


def check_record(r: dict) -> list[dict]:
    """AC-01: a record says what it is, where it came from and how it was judged."""
    out = []
    if not ID.match(r.get("id", "")):
        out.append({"rule": "AC-01", "severity": "FAIL", "detail": f"id {r.get('id')!r} is not <kind>.<name>[.<variant>]"})
    kind = r.get("kind")
    if kind not in KINDS:
        out.append({"rule": "AC-01", "severity": "FAIL", "detail": f"kind {kind!r}"})
    for k in REQUIRED.get(kind, ()):
        if not r.get(k):
            out.append({"rule": "AC-01", "severity": "FAIL", "detail": f"{kind} without {k}"})
    if r.get("angle") and r["angle"] not in ANGLES:
        out.append({"rule": "AC-01", "severity": "FAIL", "detail": f"angle {r['angle']!r}"})
    src = r.get("source") or {}
    if not (src.get("prompt") and src.get("model")):
        out.append({"rule": "AC-01", "severity": "FAIL", "detail": "no source prompt/model"})
    if not r.get("approved"):
        out.append({"rule": "AC-02", "severity": "REVIEW", "detail": "not approved yet: usable in tests, not in a video"})
    return out


BASE_SHARE = 0.8         # AC-15: an opaque base this wide in the cut-out's bottom rows is a ground patch cut with the figure


def check_cutout(im) -> list[dict]:
    """AC-15: a cut-out is the figure alone: not cut by the picture's edge, no patch of ground under the feet (the
    2026-10-25 composition test's girl came with a block of snow and sat on it in every shot)."""
    import numpy as np
    a = np.asarray(im.convert("RGBA").getchannel("A")) > 128
    out = []
    if not a.any():
        return [{"rule": "AC-15", "severity": "FAIL", "detail": "empty cut-out"}]
    edges = [n for n, e in (("top", a[0]), ("bottom", a[-1]), ("left", a[:, 0]), ("right", a[:, -1])) if e.any()]
    if edges:
        out.append({"rule": "AC-15", "severity": "FAIL", "detail": f"the figure touches the {', '.join(edges)} edge: cut"})
    ys = np.nonzero(a.any(1))[0]
    widths = a[ys.min():ys.max() + 1].sum(1)
    base = widths[-max(1, int(len(widths) * 0.04)):].max() / widths.max()
    if base >= BASE_SHARE:
        out.append({"rule": "AC-15", "severity": "FAIL", "detail": f"the bottom rows are {base:.0%} of the figure's width: "
                    f"a ground patch was cut with it"})
    return out


class Library:
    def __init__(self, path: str | Path | None = None, records: list[dict] | None = None):
        self.path = Path(path) if path else None
        if records is None and self.path and self.path.exists():
            records = json.loads(self.path.read_text(encoding="utf-8"))["assets"]
        self.records = {r["id"]: r for r in (records or [])}

    def add(self, record: dict) -> list[dict]:
        found = check_record(record)
        if not any(f["severity"] == "FAIL" for f in found):
            self.records[record["id"]] = record
        return found

    def save(self) -> Path:
        return write_json_atomic(self.path, {"schema": "asset_library/1", "assets": sorted(self.records.values(),
                                                                                            key=lambda r: r["id"])})

    def get(self, aid: str) -> dict:
        return self.records[aid]

    def find(self, kind: str, name: str | None = None, angle: str | None = None, facing: str | None = None,
             expression: str | None = None, approved_only: bool = False) -> dict | None:
        """AC-03: the record for a need, and whether to mirror it: ``{"id", "flip"}``; None when it must be drawn. An
        expression falls back to the hero's neutral one only when the need says ``expression: any``."""
        pool = [r for r in self.records.values() if r["kind"] == kind and (name is None or r.get("name") == name)
                and (not approved_only or r.get("approved"))]
        if expression and expression != "any":
            pool = [r for r in pool if r.get("expression") == expression]
        if angle:
            pool = [r for r in pool if r.get("angle") == angle]
        if not pool:
            return None
        if facing and angle in MIRRORABLE:
            same = [r for r in pool if r.get("facing") == facing]
            if same:
                return {"id": sorted(same, key=lambda r: r["id"])[0]["id"], "flip": False}
            return {"id": sorted(pool, key=lambda r: r["id"])[0]["id"], "flip": True}
        if facing and angle not in MIRRORABLE:
            pool = [r for r in pool if r.get("facing") in (None, facing)] or []
            if not pool:
                return None
        return {"id": sorted(pool, key=lambda r: r["id"])[0]["id"], "flip": False}

    def needs(self, shots: list[dict]) -> dict:
        """AC-04: every asset the shots use, deduplicated; ``missing`` is the paid list (one picture each)."""
        wanted, missing, found = {}, [], {}
        for s in shots:
            for need in shot_needs(s):
                key = json.dumps(need, sort_keys=True)
                wanted.setdefault(key, need)
        for key, need in wanted.items():
            hit = self.find(**need)
            if hit:
                found[key] = hit
            else:
                missing.append(need)
        return {"wanted": len(wanted), "reused": len(found), "missing": missing}


def shot_needs(shot: dict) -> list[dict]:
    """The assets one composed shot asks for (a reuse shot asks for none)."""
    if shot.get("reuse"):
        return []
    out = [{"kind": "background", "name": shot["background"]}]
    for it in shot.get("items", []):
        a = it.get("asset")
        if not a:
            continue
        need = {"kind": a.get("kind", "hero"), "name": a["name"]}
        for k in ("angle", "facing", "expression"):
            if a.get(k):
                need[k] = a[k]
        out.append(need)
    for c in shot.get("crowd", []):
        for unit in c["units"]:
            out.append({"kind": "crowd", "name": unit, "angle": c.get("angle", "three_quarter")})
    return out


def main(argv: list[str]) -> int:
    lib = Library(argv[0])
    if argv[1] == "needs":
        shots = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        res = lib.needs(shots["shots"] if isinstance(shots, dict) else shots)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if argv[1] == "check":
        bad = 0
        for r in lib.records.values():
            for f in check_record(r):
                bad += f["severity"] == "FAIL"
                print(r["id"], f["severity"], f["detail"])
        return 1 if bad else 0
    raise SystemExit("usage: library <library.json> needs <shots.json> | check")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
