"""One registry and one gate row for the validators written since 2026-11-20 (group 4, G-05, G-07, group 1 continuity, the
two coverage gaps and the attempt ranking). Until now each ran only from its own command line.

    python -m explainer_engine.qa.validator_gate <episode folder>       # exit 1 on a FAIL, 2 when nothing ran

``run_all(day)`` calls every registered validator on the episode folder and returns one row each,
``{id, name, status, detail}`` with status PASS | REVIEW | FAIL | NOT_RUN. **NOT_RUN is never a pass**: a validator whose input
file is missing, whose tool is absent, or that raised, is NOT_RUN with the reason. ``gate_row(day)`` folds the rows into the
production gate's vocabulary (``production_gate.script_gates`` row ``V``): any FAIL is BLOCKED; no FAIL but a NOT_RUN or nothing
run is WAIT (naming the validators that did not run); PASS only when every validator ran without a FAIL.

Where each validator finds its input in the episode folder ``day``: only files the pipeline already writes, no new names.

    shift_line_id, stated_theme, claim_ledger   production_script.json (D-43 flow) or story/production_script.json (animated route);
                                                 claim_ledger also claim_map.md beside it, else the script's editorial claims
    camera_cards                                 the script's ``shots``, only when some shot declares ``camera_move`` (no producer
                                                 writes it yet, so today this is NOT_RUN: said, not skipped silently)
    camera_clips                                 every ``*.mp4`` named like a shot (``S06_SH009_seed7100.mp4``): its move comes from the
                                                 ``<clip>.camera.json`` sidecar or the script shot's ``camera_move``; none = NOT_RUN
    ltx_prompts                                  ``prompts.json`` (``film_shots compose --out``): the ``video`` prompts. That file names
                                                 neither a hero nor a film id, so LP-05 and LP-06 are not run and a clean result is
                                                 REVIEW, never PASS
    continuity_cards                             every JSON under the folder (3 levels, under 3 MB) whose ``schema`` is
                                                 continuity_card/1 or /2, checked with episode_film.json's film id (CT-17) when present
    language                                     the viewer-text files that exist of: narration.txt, narration_tts.txt, metadata.md, the viewer
                                                 fields of publish.json and the script's spoken text (not their approval records)
    master_size                                  video.mp4 (or render/video.mp4, what ``production/assemble`` writes) against the delivery size
    attempt_ranking                              ``attempts.json`` files (``core/ledger.Attempts``): ranked only when a row carries ``checks``;
                                                 the ledger does not write them yet, so today NOT_RUN
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

NOT_RUN = "NOT_RUN"


def _row(rid: str, name: str, status: str, detail: str) -> dict:
    return {"id": rid, "name": name, "status": status, "detail": detail}


def _from_findings(rid: str, name: str, findings: list[dict], what: str) -> dict:
    """PASS means 'ran, no findings'; FAIL beats REVIEW. Findings use ``severity`` (or ``level``)."""
    sev = [str(f.get("severity", f.get("level", "REVIEW"))) for f in findings]
    fails, reviews = sev.count("FAIL"), sev.count("REVIEW")
    if fails:
        first = next(f for f in findings if str(f.get("severity", f.get("level"))) == "FAIL")
        return _row(rid, name, "FAIL", f"{what}: {fails} FAIL, {reviews} REVIEW; first: {first.get('rule')} {first.get('detail', '')}"[:300])
    if reviews:
        return _row(rid, name, "REVIEW", f"{what}: {reviews} REVIEW, no FAIL")
    return _row(rid, name, "PASS", f"{what}: no findings")


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _missing(rid: str, name: str, what: str) -> dict:
    return _row(rid, name, NOT_RUN, f"not run: no {what}")


def _episode_film_id(day: Path) -> str | None:
    p = day / "episode_film.json"
    if not p.is_file():
        return None
    from explainer_engine import episode_film
    return episode_film.film_id(episode_film.load_episode_film(str(p)))


# --- runners: each takes the episode folder and returns one row -------------------------------------------------------------
def _script(day: Path):
    p = next((q for q in (day / "production_script.json", day / "story" / "production_script.json") if q.is_file()), None)
    return _json(p) if p else None


def _shots(doc: dict) -> list[dict]:
    """The script's shots: a flat ``shots`` list, else the ``shots`` of each segment (the D-43 script keeps them there)."""
    flat = doc.get("shots")
    if isinstance(flat, list):
        return [x for x in flat if isinstance(x, dict)]
    return [x for seg in doc.get("segments", []) if isinstance(seg, dict) for x in seg.get("shots", []) if isinstance(x, dict)]


def _json_docs(day: Path, schemas: tuple[str, ...], depth: int = 3, max_bytes: int = 3_000_000):
    """(path, doc) of every JSON file under ``day`` (to ``depth`` folder levels, below ``max_bytes``) whose ``schema`` is listed."""
    out = []
    for p in sorted(day.rglob("*.json")):
        if len(p.relative_to(day).parts) > depth + 1 or p.stat().st_size > max_bytes:
            continue
        try:
            d = _json(p)
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and d.get("schema") in schemas:
            out.append((p, d))
    return out


def run_shift_line_id(day: Path) -> dict:
    from explainer_engine.scripting import shift_line_id
    doc = _script(day)
    if doc is None:
        return _missing("shift_line_id", "value shift names its line", "production_script.json")
    return _from_findings("shift_line_id", "value shift names its line", shift_line_id.check(doc), "SL")


def run_stated_theme(day: Path) -> dict:
    from explainer_engine.scripting import stated_theme
    doc = _script(day)
    if doc is None:
        return _missing("stated_theme", "theme stated, obstacle opposed", "production_script.json")
    return _from_findings("stated_theme", "theme stated, obstacle opposed", stated_theme.check(doc), "STH")


def run_claim_ledger(day: Path) -> dict:
    from explainer_engine.scripting import claim_ledger, claims
    doc = _script(day)
    if doc is None:
        return _missing("claim_ledger", "claim map as evidence ledger", "production_script.json")
    mp = day / "claim_map.md"
    if mp.is_file():
        cmap = claim_ledger.parse_ledger(mp.read_text(encoding="utf-8"))
    else:
        raw = claims.from_editorial(doc)
        if raw is None:
            return _missing("claim_ledger", "claim map as evidence ledger", "claim_map.md and no editorial claims in the script")
        cmap = {k: dict(v, type=None, opened=None, verdict=None, confidence=None, checked=None, counter_source=None)
                for k, v in raw.items()}
    return _from_findings("claim_ledger", "claim map as evidence ledger", claim_ledger.ledger_check(doc, cmap), "CL")


def run_camera_cards(day: Path) -> dict:
    from explainer_engine.qa import camera_move
    doc = _script(day)
    if doc is None:
        return _missing("camera_cards", "camera move on every shot card", "production_script.json")
    shots = _shots(doc)
    if not any(isinstance(sh, dict) and "camera_move" in sh for sh in shots):
        return _row("camera_cards", "camera move on every shot card", NOT_RUN,
                    f"not run: none of the script's {len(shots)} shots declares camera_move (nothing writes it yet)")
    return _from_findings("camera_cards", "camera move on every shot card", camera_move.check_shot_cards(shots), "CM")


def run_camera_clips(day: Path) -> dict:
    from explainer_engine.qa import camera_move
    import re
    clips = [c for c in sorted(day.rglob("*.mp4")) if re.match(r"S\d+_SH\d+", c.name)]
    if not clips:
        return _missing("camera_clips", "camera move measured on the clips", "shot clip (S##_SH###*.mp4)")
    doc = _script(day) or {}
    moves = {sh["id"]: sh["camera_move"] for sh in _shots(doc) if sh.get("camera_move") and sh.get("id")}
    results = []
    for clip in clips:
        declared = moves.get(re.match(r"(S\d+_SH\d+)", clip.name).group(1))
        if declared is None and not Path(str(clip) + ".camera.json").is_file():
            results.append((clip.name, {"status": NOT_RUN, "detail": "no declared camera move"}))
            continue
        results.append((clip.name, camera_move.camera_move_clip(clip, declared)))
    statuses = [r["status"] for _, r in results]
    for status in ("FAIL", NOT_RUN, "REVIEW"):       # worst first; NOT_RUN outranks REVIEW and PASS
        if status in statuses:
            names = ", ".join(n for n, r in results if r["status"] == status)[:200]
            return _row("camera_clips", "camera move measured on the clips", status, f"{statuses.count(status)} of {len(results)} clips {status}: {names}")
    return _row("camera_clips", "camera move measured on the clips", "PASS", f"{len(results)} clips, all PASS")


def run_ltx_prompts(day: Path) -> dict:
    from explainer_engine.qa import ltx_prompt_lint
    files = [p for p in sorted(day.rglob("prompts.json")) if len(p.relative_to(day).parts) <= 4]
    items = []
    for p in files:
        try:
            d = _json(p)
        except (OSError, ValueError):
            continue
        items += [x for x in (d.get("shots", []) if isinstance(d, dict) else []) if x.get("kind") == "video" and x.get("prompt")]
    if not items:
        return _missing("ltx_prompts", "video-model prompts", "prompts.json with video prompts")
    found: list[dict] = []
    for item in items:
        # the file names no hero and no film id: LP-05 and LP-06 cannot be judged, so they are left out, not guessed
        for f in ltx_prompt_lint.lint_ltx_prompt(item["prompt"], hero_name="x", film_id=None, pack_film_id=None):
            if f["rule"] != "LP-05":
                found.append(dict(f, detail=f"{item.get('id', '?')}: {f['detail']}"))
    row = _from_findings("ltx_prompts", "video-model prompts", found, f"LP-00..LP-04 on {len(items)} prompts")
    if row["status"] == "PASS":
        return _row("ltx_prompts", "video-model prompts", "REVIEW",
                    f"LP-00..LP-04 clean on {len(items)} prompts; LP-05 (hero) and LP-06 (film id) not run: the file carries neither")
    return row


def run_continuity_cards(day: Path) -> dict:
    from explainer_engine.scripting import continuity
    docs = _json_docs(day, ("continuity_card/1", "continuity_card/2"))
    if not docs:
        return _missing("continuity_cards", "scene continuity cards", "continuity_card JSON")
    film = _episode_film_id(day)
    found: list[dict] = []
    for _, doc in docs:
        found += continuity.check(doc, film_id=film)
    return _from_findings("continuity_cards", "scene continuity cards", found, "CT")


VIEWER_FILES = ("narration.txt", "narration_tts.txt", "metadata.md")   # not publish/*: youtube_state.json is the creator's own record


def _publish_text(doc: dict) -> str:
    """What a viewer sees of publish/1: title, description, chapters, tags, the Shorts' titles and descriptions, the thumbnail
    text. Not ``approval``, ``disclosure`` or ``files``: those are the creator's own records."""
    parts = [doc.get("title", ""), doc.get("description", ""), (doc.get("thumbnail") or {}).get("text", "")]
    parts += [c.get("title", "") for c in doc.get("chapters", []) if isinstance(c, dict)]
    parts += [t for t in doc.get("tags", []) if isinstance(t, str)]
    for sh in doc.get("shorts", []):
        parts += [str(sh.get("title", "")), str(sh.get("description", ""))] if isinstance(sh, dict) else []
    return "\n".join(x for x in parts if isinstance(x, str))


def run_language(day: Path) -> dict:
    from explainer_engine.production import script as production_script
    from explainer_engine.qa import language_check
    hits, errors, sources = [], [], 0
    for name in VIEWER_FILES:
        p = day / name
        if p.is_file():
            h, err = language_check.scan_file(p)
            hits += h
            errors += [err] if err else []
            sources += 1
    pub = day / "publish.json"
    if pub.is_file():
        try:
            hits += language_check.scan_text(_publish_text(_json(pub)), "publish.json")
            sources += 1
        except (OSError, ValueError, AttributeError):
            errors.append("publish.json: not readable as publish/1")
    doc = _script(day)
    if doc is not None:     # the spoken text only: the script also holds the creator's own approval records
        try:
            hits += language_check.scan_text(production_script.narration_text(doc), "production_script narration")
            sources += 1
        except (KeyError, TypeError, AttributeError):
            errors.append("production_script.json: segments have no readable lines")
    r = language_check.verdict(hits, errors, sources)
    return _row("language", "no Georgian script in viewer text", r["status"], r["detail"])


def run_master_size(day: Path, declared=None) -> dict:
    from explainer_engine.qa import master_size
    master = next((p for p in (day / "video.mp4", day / "render" / "video.mp4") if p.is_file()), None)
    if master is None:
        return _missing("master_size", "master pixel size", "video.mp4")
    r = master_size.check_master_size(master, declared)
    return _row("master_size", "master pixel size", r["status"], r["detail"])


def run_attempt_ranking(day: Path) -> dict:
    from explainer_engine.qa import attempt_ranking
    files = sorted(p for p in day.rglob("attempts.json") if len(p.relative_to(day).parts) <= 4)
    if not files:
        return _missing("attempt_ranking", "attempts at the retry cap", "attempts.json")
    spent = {}
    for p in files:
        rows = _json(p)
        if len(rows) >= 2 and all(isinstance(r, dict) and isinstance(r.get("checks"), list) for r in rows):
            spent[p.parent.name] = [{"attempt": r.get("n", i), "checks": r["checks"]} for i, r in enumerate(rows, 1)]
    if not spent:
        return _row("attempt_ranking", "attempts at the retry cap", NOT_RUN,
                    f"not run: {len(files)} attempts.json found, but no shot has two or more attempts that carry their checks "
                    "(the ledger writes the cause only)")
    text = "; ".join(attempt_ranking.format_for_creator(s_, attempt_ranking.rank_attempts(v)).replace("\n", " ") for s_, v in spent.items())
    return _row("attempt_ranking", "attempts at the retry cap", "REVIEW", "the creator chooses by eye: " + text[:260])


def _timed(day: Path):
    """The timed production script of the episode (``timed.json``, assemble's own input), or None."""
    for p in sorted(day.rglob("timed.json"), key=lambda q: len(q.relative_to(day).parts)):
        if len(p.relative_to(day).parts) <= 3:
            doc = _json(p)
            if isinstance(doc, dict) and isinstance(doc.get("shots"), list):
                return doc
    return None


def _timed_row(day: Path, rid: str, name: str, check) -> dict:
    timed = _timed(day)
    if timed is None:
        return _missing(rid, name, "timed.json")
    r = check(timed)
    return _row(rid, name, r["status"], r["detail"])


def run_first_shot(day: Path) -> dict:
    from explainer_engine.qa import first_shot
    return _timed_row(day, "first_shot", "first shot is not a flash", first_shot.check_timed)


def run_opening_density(day: Path) -> dict:
    from explainer_engine.qa import opening_density
    return _timed_row(day, "opening_density", "opening (30 s) keeps changing", opening_density.check_timed)


REGISTRY: list[tuple[str, Callable[[Path], dict]]] = [
    ("shift_line_id", run_shift_line_id), ("stated_theme", run_stated_theme), ("claim_ledger", run_claim_ledger),
    ("camera_cards", run_camera_cards), ("camera_clips", run_camera_clips), ("ltx_prompts", run_ltx_prompts),
    ("continuity_cards", run_continuity_cards), ("language", run_language), ("master_size", run_master_size),
    ("attempt_ranking", run_attempt_ranking), ("first_shot", run_first_shot),
    ("opening_density", run_opening_density),
]


def run_all(day: Path | str) -> list[dict]:
    """One row per registered validator. An exception inside a validator is NOT_RUN with its type and message, never a pass."""
    day = Path(day)
    rows = []
    for rid, fn in REGISTRY:
        try:
            rows.append(fn(day))
        except Exception as exc:  # noqa: BLE001 - a crashing validator must show up as not run, not take the gate down
            rows.append(_row(rid, rid, NOT_RUN, f"not run: the validator raised {exc.__class__.__name__}: {str(exc)[:150]}"))
    return rows


def gate_row(day: Path | str) -> tuple[str, str, str]:
    """(status, detail, next) for ``production_gate``: BLOCKED on any FAIL, WAIT on any NOT_RUN, PASS only when all ran."""
    rows = run_all(day)
    fails = [r["id"] for r in rows if r["status"] == "FAIL"]
    not_run = [r["id"] for r in rows if r["status"] == NOT_RUN]
    reviews = [r["id"] for r in rows if r["status"] == "REVIEW"]
    ran = len(rows) - len(not_run)
    if fails:
        return "BLOCKED", f"{len(fails)} FAIL ({', '.join(fails)}), {ran} of {len(rows)} ran", "python -m explainer_engine.qa.validator_gate <folder>"
    if not_run:
        return "WAIT", f"{ran} of {len(rows)} ran, no FAIL; not run: {', '.join(not_run)}", "provide the inputs, then run validator_gate"
    return "PASS", f"all {len(rows)} ran, no FAIL" + (f"; REVIEW: {', '.join(reviews)}" if reviews else ""), ""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__)
        return 2
    rows = run_all(argv[0])
    for r in rows:
        print(f"{r['status']:8} {r['id']:16} {r['detail']}")
    if any(r["status"] == "FAIL" for r in rows):
        return 1
    return 2 if all(r["status"] == NOT_RUN for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
