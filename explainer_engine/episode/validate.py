"""One contract for an episode folder (v4.3 plan P1.1 and F12): the folder's ``episode.json`` names the ONE episode id, and
every JSON document inside the folder that carries an episode id must carry that same id.

Run: ``python -m explainer_engine.episode.validate episodes/<id>`` (exit 1 on any FAIL).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ID_KEYS = ("episode_id", "episode")
SKIP_PARTS = {"cache", "renders", "audio", "jobs"}


def _ids(doc, path=""):
    """Every (json path, value) of an episode-id key, at any depth; ``episode`` counts only when it is a plain string."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            p = f"{path}.{k}" if path else k
            if k in ID_KEYS and isinstance(v, str):
                yield p, v
            elif isinstance(v, (dict, list)):
                yield from _ids(v, p)
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from _ids(v, f"{path}[{i}]")


def check_episode_ids(root: Path) -> list[dict]:
    """FAIL rows for every document in ``root`` whose episode id differs from ``episode.json``'s."""
    root = Path(root)
    man = json.loads((root / "episode.json").read_text(encoding="utf-8"))
    want = man["episode_id"]
    out = []
    if root.name != want:
        out.append({"rule": "EP-01", "severity": "FAIL", "where": str(root),
                    "detail": f"the folder is named {root.name!r} but episode.json says {want!r}"})
    for p in sorted(root.rglob("*.json")):
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] in SKIP_PARTS:
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            out.append({"rule": "EP-01", "severity": "FAIL", "where": str(rel), "detail": f"not readable JSON: {e}"})
            continue
        for jp, v in _ids(doc):
            if v != want:
                out.append({"rule": "EP-01", "severity": "FAIL", "where": f"{rel}:{jp}",
                            "detail": f"episode id {v!r}, the folder's episode is {want!r} (one id per episode, F12)"})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("episode", type=Path)
    a = ap.parse_args(argv)
    rows = check_episode_ids(a.episode)
    for r in rows:
        print(f"{r['severity']} {r['rule']} {r['where']}: {r['detail']}")
    print(f"{len(rows)} finding(s)")
    return 1 if any(r["severity"] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
