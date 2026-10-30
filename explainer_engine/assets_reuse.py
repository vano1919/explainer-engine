"""Library first (OR-18, D-76, the creator 2026-10-20): before any new background music, sound effect or reusable
picture is generated, the libraries are searched and the search is recorded in the episode's ``asset_reuse.json``.
The ElevenLabs hook (``standards/hook.py``) refuses a paid music or sound-effect call for an episode without such a
record, and ``paint plan`` lists a prompt's library matches on the plan (PP-08). New is generated only when nothing
in the library fits, and the record says why.

Free generator (D8, BP-162): the order is library -> an admitted free generator -> the ElevenLabs connector.
``generate_free`` records that the episode takes a free take from the generator admitted for the kind
(``audio/generator_gate.py``; it needs that admission). While an admission exists for a kind, ``generate_new`` (paid)
needs ``--why`` naming what the free take could not do, with or without library matches, and the hook refuses a paid
call without it. With no admission (today) nothing changes.

CLI (search and record in one step):
    python -m explainer_engine.assets_reuse <episode folder> --kind music --tags tense,heist
        [--decide reuse|generate_free|generate_new] [--why "..."]

Without ``--decide`` it only prints the matches. ``generate_new`` with matches present (or with a generator admitted for
the kind) needs ``--why``.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from explainer_engine.core.store import write_json_atomic

REPO = Path(__file__).resolve().parents[1]
SOUND_LIB = REPO / "assets" / "audio" / "library"
KINDS = ("music", "sfx", "vocal", "picture")
_SOUND_CATEGORY = {"music": "music", "sfx": "foley", "vocal": "vocal"}
RECORD_NAME = "asset_reuse.json"
DECISIONS = ("reuse", "generate_free", "generate_new")


def free_generator(kind: str) -> dict | None:
    """The admission (``audio/generator_gate.py``) of a free generator for this kind, or None: today none is admitted. The
    library's ``foley`` is the gate's ``sfx``; pictures and vocals have no generator kind."""
    from explainer_engine.audio import generator_gate
    return generator_gate.admitted({"music": "music", "sfx": "sfx"}.get(kind, ""))


def lookup(kind: str, tags: list[str], *, sound_root: Path | None = None, picture_root: Path | None = None) -> list[dict]:
    """Usable library entries having ALL the tags: the sound library for music/sfx/vocal, the picture library for picture."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; known: {KINDS}")
    if kind == "picture":
        from explainer_engine.imagegen import picture_library
        return picture_library.find(picture_root or picture_library.ROOT, tags=tags)
    from explainer_engine.audio import sfx_library
    return sfx_library.find(sound_root or SOUND_LIB, tags=tags, category=_SOUND_CATEGORY[kind])


def load_record(episode_dir: Path) -> dict:
    path = Path(episode_dir) / RECORD_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 1, "lookups": []}


def record(episode_dir: Path, *, kind: str, tags: list[str], matches: list[dict], decision: str, why: str = "") -> dict:
    """Append one search to the episode's ``asset_reuse.json``. ``generate_new`` over existing matches needs a reason."""
    if decision not in DECISIONS:
        raise ValueError("decision is 'reuse', 'generate_free' or 'generate_new'")
    adm = free_generator(kind)
    if decision == "generate_free" and adm is None:
        raise ValueError(f"no free generator is admitted for {kind}: library first, then the connector (BP-162)")
    if decision == "generate_new" and matches and not why.strip():
        raise ValueError("the library has matches: say why none of them fits (--why)")
    if decision == "generate_new" and adm is not None and not why.strip():
        raise ValueError(f"{adm['generator']} is admitted for {kind} (BP-162): say what the free take could not do (--why)")
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "tags": sorted(set(tags)),
             "matches": [m["id"] for m in matches], "decision": decision, "why": why}
    if decision == "generate_free":
        entry["generator"] = adm["id"]
    doc = load_record(episode_dir)
    doc["lookups"].append(entry)
    write_json_atomic(Path(episode_dir) / RECORD_NAME, doc)
    return entry


def has_lookup(episode_dir: Path, kind: str) -> bool:
    """Whether the episode recorded at least one decided library search of this kind (what the hook checks, OR-18)."""
    return any(e.get("kind") == kind and e.get("decision") in DECISIONS for e in load_record(episode_dir).get("lookups", []))


def paid_justified(episode_dir: Path, kind: str) -> bool:
    """Whether a paid music/sfx call of this kind is justified (what the hook checks, BP-162): with no admission for the kind,
    always; with one, only when the episode recorded ``generate_new`` with a ``why`` for it."""
    if free_generator(kind) is None:
        return True
    return any(e.get("kind") == kind and e.get("decision") == "generate_new" and (e.get("why") or "").strip()
               for e in load_record(episode_dir).get("lookups", []))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("episode", help="the episode folder (asset_reuse.json is written next to its script)")
    p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--tags", required=True, help="comma-separated")
    p.add_argument("--decide", choices=list(DECISIONS))
    p.add_argument("--why", default="")
    a = p.parse_args(argv)
    tags = [t for t in a.tags.split(",") if t]
    matches = lookup(a.kind, tags)
    for m in matches:
        print(f"{m['id']:40} {m.get('category') or m.get('kind'):10} {','.join(m['tags'])}")
    print(f"{len(matches)} match(es) for {a.kind} {tags}")
    if a.decide:
        entry = record(Path(a.episode), kind=a.kind, tags=tags, matches=matches, decision=a.decide, why=a.why)
        print(f"recorded: {entry['decision']} ({Path(a.episode) / RECORD_NAME})")
    else:
        print("nothing recorded (pass --decide reuse|generate_free|generate_new); a paid music/sfx call needs the record (OR-18)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
