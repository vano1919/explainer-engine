"""Migrate shot cards to ``film_shots/3`` (the Ink Chronicle Blender path, D-96/D-97; roadmap section 10.3, ICW-02).

Reads ``film_shots/2`` (and ``film_shots/1``, whose cards have no lane yet) and writes the /3 cards: lanes ``VIDEO_3D``,
``STILL_3D``, ``HELPER``; per shot ``render_profile``, ``still_mode``, ``lipsync``, ``dialogue_cover``, ``helper_archetype``;
the 2560x1440 master at 24 fps (BP-167) with exact frame counts; the Ink Chronicle style block (house look + world bible
version) in place of the LoRA trigger and the video-model sentence (D-100, D-105). A dry run prints the report and writes
nothing; ``--write`` rewrites each file in place (atomic), ``--report <md>`` saves the report.

    python scripts/migrate_film_shots_2_to_3.py <film_shots.json>... [--write] [--report <file.md>]

The mapping (roadmap 10.3; every /3 lane is the BP-109 lane the old card already counted as, so the 60/30/10 shares are
unchanged by the migration and the report proves it):

- KEYFRAME_LTX, ATMOS_BROLL, DIALOGUE_CU -> VIDEO_3D (DIALOGUE_CU, or any shot with a spoken line, sets ``lipsync``);
  a card of these lanes at ``tier: hold`` was already a still under BP-109 (D-93) and becomes STILL_3D;
- STILL_HOLD -> STILL_3D; the parallax tableau (catalogue PARALLAX_25D_TABLEAU) -> STILL_3D ``parallax_25d``;
- MAP, COMPENSATOR, GRAPHICS -> HELPER, the catalogue id kept as ``helper_archetype``;
- HOST_COMMENTARY and DRAMA_BLOCKED_3D are refused with their decision (D-89; D-75/D-77, D-106);
- a film_shots/1 card: tier hold -> STILL_3D, every other card -> VIDEO_3D (the /1 reading of BP-109).

Defaults the planner refines later (ICW-03), each counted in the report: ``still_mode`` hold on a static camera and
camera_move_3d on a moving one; ``render_profile`` eevee_fast for tier light and eevee_full otherwise (cycles_hero is never
chosen here: it needs a written why); ``archetype`` null (the Ink Chronicle archetypes 1-20 are the shot designer's,
roadmap 7.3); for /1 cards ``lens_tier`` from the shot size, ``focal_xy`` the centre and no continuity or blocking reference.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from explainer_engine.core import contracts  # noqa: E402
from explainer_engine.core.store import write_text_atomic  # noqa: E402
from explainer_engine.scripting import film_shots  # noqa: E402
from explainer_engine.standards import sourced_rules as SR  # noqa: E402
from explainer_engine.world import bible as world_bible  # noqa: E402

V3 = "film_shots/3"
REFUSED = {"HOST_COMMENTARY": "no permanent hosts (D-89, card A1 NO)",
           "DRAMA_BLOCKED_3D": "the refused 3D-blocking lane of /2 (D-75/D-77, D-106): its intent on /3 is VIDEO_3D + an archetype"}
HELPER_LANES = {"MAP", "COMPENSATOR", "GRAPHICS"}
VIDEO_LANES = {"KEYFRAME_LTX", "ATMOS_BROLL", "DIALOGUE_CU"}
LEGACY_STYLE = ("trigger", "video_sentence", "neg_keyframe", "body", "neg_video")
LEGACY_SHOT = ("lane", "archetype", "duration_frames", "width", "height")
LENS_BY_SIZE = {"EWS": "wide", "WS": "wide", "MWS": "normal", "MS": "normal", "OTS": "normal", "MCU": "long", "CU": "long",
                "ECU": "long", "INSERT": "long"}


class MigrationRefused(ValueError):
    """A card that cannot become film_shots/3 (a refused lane, or a document that is not /1 or /2)."""


def _lane_3(shot: dict, schema: str) -> str:
    lane = shot.get("lane")
    if lane in REFUSED:
        raise MigrationRefused(f"shot {shot['id']}: lane {lane} is refused, {REFUSED[lane]}")
    old = film_shots.visual_lane(shot, schema if schema == "film_shots/2" else None)
    return {"video": "VIDEO_3D", "still": "STILL_3D", "helper": "HELPER"}[old]


def _still_mode(shot: dict) -> str:
    if shot.get("archetype") in film_shots.STILL_CATALOGUE:
        return "parallax_25d"
    return "hold" if shot["frame"].get("camera", "static") == "static" else "camera_move_3d"


def migrate(doc: dict, *, bible_version: str | None = None) -> tuple[dict, dict]:
    """(the film_shots/3 document, the report). Nothing is guessed silently: every default is counted in the report, and the
    result is validated against the contract (a FAIL raises ``ContractError``)."""
    schema = doc.get("schema")
    if schema not in ("film_shots/1", "film_shots/2"):
        raise MigrationRefused(f"cannot migrate {schema!r}: only film_shots/1 and film_shots/2")
    for s in doc.get("shots", []):
        if s.get("lane") in REFUSED:
            raise MigrationRefused(f"shot {s['id']}: lane {s['lane']} is refused, {REFUSED[s['lane']]}")
    bad = [f for f in contracts.errors(doc) if f["severity"] == "FAIL"]
    if bad:
        raise MigrationRefused("the input does not validate, fix it first: " +
                               "; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad[:3]))
    fps = SR.T("BP-167", "fps")
    width, height = SR.T("BP-167", "width"), SR.T("BP-167", "height")
    bible_version = bible_version or world_bible.load()["version"]
    before = film_shots.lane_shares(doc["shots"], schema if schema == "film_shots/2" else None)
    report = {"source_schema": schema, "shots": len(doc["shots"]), "lanes": Counter(), "still_mode": Counter(),
              "render_profile": Counter(), "lipsync": 0, "dialogue_off_screen": 0, "defaults": Counter(),
              "style_dropped": [k for k in LEGACY_STYLE if k in doc.get("style", {})], "fps_from": doc.get("fps")}
    new = {k: v for k, v in doc.items() if k not in ("schema", "fps", "style", "shots")}
    style = {"house_look": "ink_chronicle", "bible_version": bible_version}
    if "look" in doc.get("style", {}):
        style["look"] = doc["style"]["look"]
    new = {"schema": V3, "fps": fps, **{k: v for k, v in new.items() if k != "scene_sets"}, "style": style,
           **({"scene_sets": doc["scene_sets"]} if "scene_sets" in doc else {})}
    shots = []
    for s in doc["shots"]:
        lane = _lane_3(s, schema)
        old_lane = s.get("lane") or "(none, /1)"
        report["lanes"][f"{old_lane} -> {lane}"] += 1
        out = {k: v for k, v in s.items() if k not in LEGACY_SHOT}
        out.update(lane=lane, archetype=None, duration_frames=round(s["seconds"] * fps), width=width, height=height)
        if schema == "film_shots/1":
            out.update(lens_tier=LENS_BY_SIZE[s["frame"]["size"]], focal_xy=[0.5, 0.5], continuity_ref=None, blocking_ref=None)
            report["defaults"]["lens_tier, focal_xy, refs (/1 card)"] += 1
        if lane == "HELPER":
            out["helper_archetype"] = s["archetype"]
        else:
            out["render_profile"] = "eevee_fast" if s.get("tier") == "light" else "eevee_full"
            report["render_profile"][out["render_profile"]] += 1
        if lane == "STILL_3D":
            out["still_mode"] = _still_mode(s)
            report["still_mode"][out["still_mode"]] += 1
        if lane == "VIDEO_3D":
            out["lipsync"] = bool(s.get("dialogue"))
            report["lipsync"] += out["lipsync"]
            if s.get("lane") == "DIALOGUE_CU" and not s.get("dialogue"):
                report["defaults"]["DIALOGUE_CU without a line: lipsync false"] += 1
        if s.get("dialogue"):
            out["dialogue_cover"] = "on_screen" if out.get("lipsync") else "off_screen"
            report["dialogue_off_screen"] += out["dialogue_cover"] == "off_screen"
        shots.append(out)
    new["shots"] = shots
    after = film_shots.lane_shares(shots, V3)
    report["shares_before"], report["shares_after"] = before, after
    report["shares_unchanged"] = all(abs(before[k] - after[k]) < 1e-9 for k in before)
    contracts.validate(new)
    return new, report


def report_md(path: str, report: dict) -> str:
    lines = [f"### `{path}`", "",
             f"- {report['source_schema']} -> {V3}, {report['shots']} shots; fps {report['fps_from'] or '(none, /1)'} -> "
             f"{SR.T('BP-167', 'fps')}; frame {SR.T('BP-167', 'width')}x{SR.T('BP-167', 'height')} (BP-167)",
             f"- style fields dropped (legacy prompt route, D-100/D-105): {', '.join(report['style_dropped']) or 'none'}; "
             "added house_look ink_chronicle + bible_version"]
    lines += [f"- lane {k}: {v}" for k, v in sorted(report["lanes"].items())]
    lines += [f"- still_mode {k}: {v}" for k, v in sorted(report["still_mode"].items())]
    lines += [f"- render_profile {k}: {v}" for k, v in sorted(report["render_profile"].items())]
    lines.append(f"- lipsync shots: {report['lipsync']}; spoken lines covered off screen: {report['dialogue_off_screen']}")
    lines += [f"- default: {k}: {v}" for k, v in sorted(report["defaults"].items())]
    b, a = report["shares_before"], report["shares_after"]
    lines.append("- BP-109 runtime shares before -> after: " + ", ".join(f"{k} {b[k]:.1%} -> {a[k]:.1%}" for k in b) +
                 (" (unchanged)" if report["shares_unchanged"] else " (CHANGED: stop and look)"))
    lines.append("- archetype: null on every shot (the shot designer assigns 1-20, ICW-03)")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    write = "--write" in argv
    argv = [a for a in argv if a != "--write"]
    out_report = None
    if "--report" in argv:
        i = argv.index("--report")
        out_report = Path(argv[i + 1])
        del argv[i:i + 2]
    if not argv:
        print(__doc__)
        return 2
    parts, status = [], 0
    for name in argv:
        path = Path(name)
        doc = json.loads(path.read_text(encoding="utf-8"))
        try:
            new, report = migrate(doc)
        except (MigrationRefused, ValueError) as exc:
            parts.append(f"### `{name}`\n\n- REFUSED: {exc}\n")
            status = 1
            continue
        parts.append(report_md(name, report))
        if write:
            write_text_atomic(path, json.dumps(new, ensure_ascii=False, indent=1) + "\n")
    text = "\n".join(parts)
    print(text)
    if out_report:
        write_text_atomic(out_report, report_header(argv) + text)
    return status


def report_header(paths: list[str]) -> str:
    """The head of a saved dry-run report: what was run, so the report can be regenerated and compared (ICW-02)."""
    return ("# film_shots/1 and /2 -> film_shots/3: migration dry run\n\n"
            "Roadmap 10.3 (ICW-02). Regenerate with\n\n"
            f"    python scripts/migrate_film_shots_2_to_3.py {' '.join(paths)} --report <this file>\n\n"
            "A dry run writes no card. The Napoleon example's own report is `examples/napoleon_vs_genghis/migration_report.md`.\n\n")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
