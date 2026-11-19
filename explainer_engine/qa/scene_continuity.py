"""Scene-level soft gates for the song-structured docudrama (owner-approved Python item 1, 2026-11-16).

Pure functions over the production script dict (``scene_bibles`` + shots); no I/O. Every row follows ``qa/gates.row``.
A script without ``scene_bibles`` / the new shot fields (older episodes) yields NO rows, so old runs keep their verdict.

Bands are MEASURED soft bands from the 29-video scene study (scene 20-50 s, 6-12 shots, edited shot 3-4 s, return to an
earlier shot in about 75 % of scenes; proxy detector, axis/eyeline NOT measured), so they are REVIEW findings, never FAIL
(D-59). FAIL is kept for objective defects only: a broken scene-bible reference, a boilerplate (repeated or empty) meaning
link, and a document insert without a valid motivation.
"""
from __future__ import annotations

from collections import Counter
from statistics import median

from explainer_engine.qa.gates import FAIL, REVIEW, row

SCENE_SECONDS = (20.0, 50.0)          # MEASURED soft band (scene_study)
SCENE_SHOTS = (6, 12)                 # MEASURED soft band
EDITED_SHOT_SECONDS = (3.0, 4.0)      # MEASURED soft band; source LTX clips stay 4-6 s (a different thing)
RETURN_TO_MASTER_SHARE = (0.65, 0.85)  # DESIGN_RULE around the measured ~75 %
MAX_MEANING_LINK_REPEATS = 2          # one text for more shots than this is boilerplate
MIN_MEANING_LINK_CHARS = 20
BIBLE_KEYS = ("scene_id", "scene_master_ref", "axis_id", "camera_side", "lighting_ref", "sound_bed_id")
DOCUMENT_MOTIVATIONS = ("read_aloud", "character_reading", "narrative_evidence", "sonic_motif")


def _edited(s: dict) -> float | None:
    v = s.get("edited_shot_duration_seconds", s.get("target_duration_seconds"))
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _link_text(s: dict) -> str:
    m = s.get("meaning_link")
    if isinstance(m, dict):
        m = m.get("text")
    return str(m or "").strip()


def scene_rows(script: dict) -> list[dict]:
    bibles = script.get("scene_bibles")
    if not bibles:
        return []
    shots = script.get("shots") or []
    rows: list[dict] = []

    ids = {b.get("scene_id") for b in bibles}
    incomplete = [f"{b.get('scene_id')}:{k}" for b in bibles for k in BIBLE_KEYS if not b.get(k)]
    dangling = sorted({str(s.get("scene_bible_ref")) for s in shots if s.get("scene_bible_ref") and s["scene_bible_ref"] not in ids})
    rows.append(row("SCENE_BIBLE_COMPLETENESS", not incomplete and not dangling,
                    f"{len(incomplete)} missing bible field(s), {len(dangling)} shot reference(s) to a scene bible that does not exist",
                    {"missing": incomplete[:20], "dangling": dangling[:20]}))

    out = [b["scene_id"] for b in bibles if not SCENE_SECONDS[0] <= float(b.get("scene_duration_seconds") or 0) <= SCENE_SECONDS[1]]
    rows.append(row("SCENE_DURATION_BAND_REVIEW", not out, f"{len(out)} of {len(bibles)} scene(s) outside "
                    f"{SCENE_SECONDS[0]:g}-{SCENE_SECONDS[1]:g} s (measured soft band)", out, level=REVIEW))
    out = [b["scene_id"] for b in bibles if not SCENE_SHOTS[0] <= int(b.get("edited_shot_count") or 0) <= SCENE_SHOTS[1]]
    rows.append(row("SCENE_SHOT_COUNT_BAND_REVIEW", not out, f"{len(out)} of {len(bibles)} scene(s) outside "
                    f"{SCENE_SHOTS[0]}-{SCENE_SHOTS[1]} shots (measured soft band)", out, level=REVIEW))

    by_scene: dict[str, list[float]] = {}
    for s in shots:
        d = _edited(s)
        if d is not None and not s.get("benchmark_exception") and s.get("scene_bible_ref"):
            by_scene.setdefault(s["scene_bible_ref"], []).append(d)
    med_out = {k: round(median(v), 2) for k, v in by_scene.items()
               if not EDITED_SHOT_SECONDS[0] <= median(v) <= EDITED_SHOT_SECONDS[1]}
    rows.append(row("EDITED_SHOT_DURATION_BAND_REVIEW", not med_out, f"{len(med_out)} of {len(by_scene)} scene(s) whose median "
                    f"edited shot is outside {EDITED_SHOT_SECONDS[0]:g}-{EDITED_SHOT_SECONDS[1]:g} s (source clips are 4-6 s; "
                    "benchmark exceptions skipped)", med_out, level=REVIEW))

    share = sum(1 for b in bibles if b.get("return_to_master")) / len(bibles)
    rows.append(row("RETURN_TO_MASTER_RATE_REVIEW", RETURN_TO_MASTER_SHARE[0] <= share <= RETURN_TO_MASTER_SHARE[1],
                    f"{share:.0%} of scenes return to their master shot (measured about 75 %; band is a design rule)",
                    round(share, 2), level=REVIEW))

    links = [(s.get("shot_id"), _link_text(s)) for s in shots if "meaning_link" in s]
    if links:
        counts = Counter(t for _, t in links)
        short = [sid for sid, t in links if len(t) < MIN_MEANING_LINK_CHARS]
        repeated = sorted({t[:60] for t, n in counts.items() if n > MAX_MEANING_LINK_REPEATS and t})
        rows.append(row("MEANING_LINK_SPECIFICITY", not short and not repeated,
                        f"{len(short)} empty/short meaning link(s), {len(repeated)} text(s) used by more than "
                        f"{MAX_MEANING_LINK_REPEATS} shots (boilerplate)", {"short": short[:20], "repeated": repeated[:10]}))

    docs = [s for s in shots if "document_motivation" in s]
    if docs:
        bad = [s.get("shot_id") for s in docs if s.get("document_motivation") not in DOCUMENT_MOTIVATIONS]
        rows.append(row("DOCUMENT_INSERT_MOTIVATION", not bad, f"{len(bad)} of {len(docs)} document insert(s) without a valid "
                        "motivation (read aloud, read by a character, narrative evidence or a sound motif)", bad[:20]))
        short_hold = [s.get("shot_id") for s in docs
                      if _edited(s) is not None and float(s.get("minimum_hold_seconds") or 0) > _edited(s) + 1e-6]
        rows.append(row("DOCUMENT_INSERT_HOLD_REVIEW", not short_hold, f"{len(short_hold)} document insert(s) cut shorter than "
                        "their minimum hold (readable or voiced time)", short_hold[:20], level=REVIEW))
    return rows


__all__ = ["scene_rows", "FAIL", "REVIEW"]
