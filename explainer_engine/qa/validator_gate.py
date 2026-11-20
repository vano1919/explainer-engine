"""One registry and one gate row for the validators written since 2026-11-20 (group 4, G-05, G-07, group 1 continuity, the
two coverage gaps and the attempt ranking). Until now each ran only from its own command line.

    python -m explainer_engine.qa.validator_gate <episode folder>       # exit 1 on a FAIL, 2 when nothing ran

``run_all(day)`` calls every registered validator on the episode folder and returns one row each,
``{id, name, status, detail}`` with status PASS | REVIEW | FAIL | NOT_RUN. **NOT_RUN is never a pass**: a validator whose input
file is missing, whose tool is absent, or that raised, is NOT_RUN with the reason. ``gate_row(day)`` folds the rows into the
production gate's vocabulary (``production_gate.script_gates`` row ``V``): any FAIL is BLOCKED; no FAIL but a NOT_RUN or nothing
run is WAIT (naming the validators that did not run); PASS only when every validator ran without a FAIL.

Where each validator finds its input in the episode folder ``day`` (file names are this module's proposal, to be confirmed by
the lead; a different name changes one line of ``REGISTRY``):

    shift_line_id, stated_theme, claim_ledger   production_script.json (claim_ledger also claim_map.md, or the script's editorial claims)
    camera_cards                                 shot_cards.json  (a list, or {"shots": [...]} / {"cards": [...]})
    camera_clips                                 every ``<clip>.camera.json`` sidecar under the folder, for the clip beside it
    ltx_prompts                                  ltx_prompts.json: [{shot_id, prompt, hero_name, film_id}], each film_id compared
                                                 with the folder's episode_film.json
    continuity_cards                             continuity_cards.json: one card document or a list of them, checked with the
                                                 episode film id (CT-17)
    language                                     the viewer-text files that exist of: narration.txt, narration_tts.txt, publish.json,
                                                 viewer_text/*.txt, viewer_text/*.json
    master_size                                  master.mp4 (or render/master.mp4) against the delivery size, or ``declared``
    attempt_ranking                              qa/attempts.json: {shot_id: [{attempt, checks}]}; a row only for shots with 2+ attempts
                                                 (REVIEW: a sort for the creator, never a pass; NOT_RUN when there is nothing to rank)
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
    p = day / "production_script.json"
    return _json(p) if p.is_file() else None


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
    p = day / "shot_cards.json"
    if not p.is_file():
        return _missing("camera_cards", "camera move on every shot card", "shot_cards.json")
    return _from_findings("camera_cards", "camera move on every shot card", camera_move.check_shot_cards(_json(p)), "CM")


def run_camera_clips(day: Path) -> dict:
    from explainer_engine.qa import camera_move
    sidecars = sorted(day.glob("**/*.camera.json"))
    if not sidecars:
        return _missing("camera_clips", "camera move measured on the clips", "<clip>.camera.json sidecar")
    results = []
    for sc in sidecars:
        clip = Path(str(sc)[: -len(".camera.json")])
        if not clip.is_file():
            results.append((clip.name, {"status": NOT_RUN, "detail": "clip file missing"}))
            continue
        results.append((clip.name, camera_move.camera_move_clip(clip)))
    statuses = [r["status"] for _, r in results]
    for status in ("FAIL", NOT_RUN, "REVIEW"):       # worst first; NOT_RUN outranks REVIEW and PASS
        if status in statuses:
            names = ", ".join(n for n, r in results if r["status"] == status)[:200]
            return _row("camera_clips", "camera move measured on the clips", status, f"{statuses.count(status)} of {len(results)} clips {status}: {names}")
    return _row("camera_clips", "camera move measured on the clips", "PASS", f"{len(results)} clips, all PASS")


def run_ltx_prompts(day: Path) -> dict:
    from explainer_engine.qa import ltx_prompt_lint
    p = day / "ltx_prompts.json"
    if not p.is_file():
        return _missing("ltx_prompts", "video-model prompts", "ltx_prompts.json")
    pack_film = _episode_film_id(day)
    found: list[dict] = []
    for item in _json(p):
        for f in ltx_prompt_lint.lint_ltx_prompt(item["prompt"], hero_name=item.get("hero_name", ""),
                                                 film_id=item.get("film_id"), pack_film_id=pack_film):
            found.append(dict(f, detail=f"{item.get('shot_id', '?')}: {f['detail']}"))
    row = _from_findings("ltx_prompts", "video-model prompts", found, "LP")
    if row["status"] == "PASS" and pack_film is None:
        return _row("ltx_prompts", "video-model prompts", NOT_RUN, "not run to the end: no episode_film.json, so LP-06 (film id) could not be checked")
    return row


def run_continuity_cards(day: Path) -> dict:
    from explainer_engine.scripting import continuity
    p = day / "continuity_cards.json"
    if not p.is_file():
        return _missing("continuity_cards", "scene continuity cards", "continuity_cards.json")
    data = _json(p)
    film = _episode_film_id(day)
    found: list[dict] = []
    for doc in data if isinstance(data, list) else [data]:
        found += continuity.check(doc, film_id=film)
    return _from_findings("continuity_cards", "scene continuity cards", found, "CT")


VIEWER_FILES = ("narration.txt", "narration_tts.txt", "publish.json")


def run_language(day: Path) -> dict:
    from explainer_engine.qa import language_check
    files = [day / n for n in VIEWER_FILES if (day / n).is_file()]
    vt = day / "viewer_text"
    if vt.is_dir():
        files += sorted(p for p in vt.iterdir() if p.suffix.lower() in (".txt", ".json"))
    if not files:
        return _missing("language", "no Georgian script in viewer text", "viewer-text file")
    r = language_check.check_files(files)
    return _row("language", "no Georgian script in viewer text", r["status"], r["detail"])


def run_master_size(day: Path, declared=None) -> dict:
    from explainer_engine.qa import master_size
    master = next((p for p in (day / "master.mp4", day / "render" / "master.mp4") if p.is_file()), None)
    if master is None:
        return _missing("master_size", "master pixel size", "master.mp4")
    r = master_size.check_master_size(master, declared)
    return _row("master_size", "master pixel size", r["status"], r["detail"])


def run_attempt_ranking(day: Path) -> dict:
    from explainer_engine.qa import attempt_ranking
    p = day / "qa" / "attempts.json"
    if not p.is_file():
        return _missing("attempt_ranking", "attempts at the retry cap", "qa/attempts.json")
    spent = {shot: v for shot, v in _json(p).items() if len(v) >= 2}
    if not spent:
        return _row("attempt_ranking", "attempts at the retry cap", NOT_RUN, "not run: no shot has two or more attempts to rank")
    text = "; ".join(attempt_ranking.format_for_creator(s, attempt_ranking.rank_attempts(v)).replace("\n", " ") for s, v in spent.items())
    return _row("attempt_ranking", "attempts at the retry cap", "REVIEW", "the creator chooses by eye: " + text[:260])


REGISTRY: list[tuple[str, Callable[[Path], dict]]] = [
    ("shift_line_id", run_shift_line_id), ("stated_theme", run_stated_theme), ("claim_ledger", run_claim_ledger),
    ("camera_cards", run_camera_cards), ("camera_clips", run_camera_clips), ("ltx_prompts", run_ltx_prompts),
    ("continuity_cards", run_continuity_cards), ("language", run_language), ("master_size", run_master_size),
    ("attempt_ranking", run_attempt_ranking),
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
