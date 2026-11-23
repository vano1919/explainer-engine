"""The speech-mix report (roadmap 8.1-8.2, ICW-03; D-99, BP-105): narrator words against voiced character words over the
audible lines of one script, written as ``speech_mix_report/1`` (``schemas/speech_mix_report.schema.json``, CN-20).

    python -m explainer_engine.qa.speech_mix <script.json | film_shots.json> [--spine audio/audio_spine.json]
        [--film-shots film_shots.json] [--job-id JOB] [--out speech_mix_report.json]

- The share is measured over **audible words**: narrator words / (narrator words + voiced character words); a line marked
  ``voiced: false`` (a silent bubble, roadmap 8.1) is counted apart as ``unvoiced_words`` and never in the share.
- The script is a ``production_script`` (segments of lines: a line with a ``speaker`` is a character's) or the shot cards
  themselves (``film_shots``: ``narration`` is the narrator's, ``dialogue.text`` a character's), whichever the episode has.
- ``narrator_share_seconds`` is informational: the narrator's audible seconds over all audible seconds, from the
  ``audio_spine`` word windows (a spine word's ``line`` is the global index into the script's lines, as
  ``production/timing.py`` writes ``timed.lines``); ``null`` without a spine. It never replaces the word rule.
- Lip-sync coverage (BP-108): the number of ``lipsync`` shots of ``film_shots/3``, their seconds and the longest one.

The band and the nominal are BP-105's, read through ``scripting/film_shots`` (the module the registry lists); this file and
the report never store them (CN-20). ``findings`` returns the REVIEWs: a share outside the band (KP-39) and a seen voiced
shot over the dialogue cap (KP-36). The final-mix delivery check of roadmap section 13 (a missing, cut or duplicated word on
the mixed stem) is ICW-08's.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.store import write_json_atomic
from explainer_engine.scripting import film_shots as F

RULE = "BP-105"


def _words(text: str) -> int:
    return len((text or "").split())


def script_lines(script: dict) -> list[dict]:
    """``{"who": None | cast id, "voiced": bool, "words": int}`` per line, in the script's order (the spine's line index)."""
    out: list[dict] = []
    if str(script.get("schema", "")).startswith("film_shots/"):
        for s in script["shots"]:
            if s.get("narration"):
                out.append({"who": None, "voiced": True, "words": _words(s["narration"])})
            spoken = s.get("dialogue")
            for d in ([spoken] if isinstance(spoken, dict) else (spoken or [])):
                out.append({"who": d.get("who"), "voiced": d.get("voiced", True) is not False, "words": _words(d.get("text"))})
        return out
    for seg in script.get("segments", []):
        for ln in seg.get("lines", []):
            who = ln.get("speaker")
            out.append({"who": who, "voiced": ln.get("voiced", True) is not False, "words": _words(ln.get("text"))})
    return out


def seconds_share(script: dict, spine: dict | None) -> float | None:
    """The narrator's share of the audible seconds of the spine's words (informational, roadmap 8.1); None without a spine.
    A spine word on a line the script marks unvoiced is left out; a spine that names a line the script does not have is a
    contract fault (the two are not the same read)."""
    if spine is None:
        return None
    lines = script_lines(script)
    narr = total = 0.0
    for w in spine["words"]:
        k = w["line"]
        if not 0 <= k < len(lines):
            raise contracts.ContractError(f"spine word {w['i']} names line {k}; the script has {len(lines)} lines")
        if not lines[k]["voiced"]:
            continue
        secs = float(w["end_s"]) - float(w["start_s"])
        total += secs
        narr += secs if lines[k]["who"] is None else 0.0
    return round(narr / total, 4) if total else None


def report(script: dict, *, refs: dict[str, dict], job_id: str, spine: dict | None = None,
           film_shots: dict | None = None) -> dict:
    """``speech_mix_report/1`` of one script (+ the spine for seconds, + film_shots/3 for lip-sync coverage). ``refs`` names
    each input as ``{path, sha256}`` relative to the job folder (CN-02): ``script`` always, ``audio_spine`` / ``film_shots``
    when given."""
    lines = script_lines(script)
    narrator = sum(x["words"] for x in lines if x["who"] is None)
    dialogue = sum(x["words"] for x in lines if x["who"] is not None and x["voiced"])
    unvoiced = sum(x["words"] for x in lines if x["who"] is not None and not x["voiced"])
    cards = film_shots if film_shots is not None else (script if script.get("schema") == F.V3 else None)
    seen = [s for s in (cards or {}).get("shots", []) if s.get("lipsync")]
    derived = {"script": refs["script"]}
    if spine is not None:
        derived["audio_spine"] = refs["audio_spine"]
    if film_shots is not None:
        derived["film_shots"] = refs["film_shots"]
    doc = {"schema": "speech_mix_report/1", "job_id": job_id, "derived_from": derived, "rule": RULE,
           "narrator_words": narrator, "dialogue_words": dialogue, "unvoiced_words": unvoiced,
           "narrator_share_words": round(narrator / (narrator + dialogue), 4) if narrator + dialogue else 0.0,
           "narrator_share_seconds": seconds_share(script, spine),
           "lipsync_shots": len(seen), "lipsync_seconds": float(sum(float(s["seconds"]) for s in seen)),
           "longest_voiced_cu_s": float(max((float(s["seconds"]) for s in seen), default=0.0))}
    contracts.validate(doc)
    return doc


def findings(doc: dict) -> list[dict]:
    """REVIEW findings of a report: KP-39 (the narrator's word share outside BP-105's band; the nominal named) and KP-36 (a
    seen voiced shot longer than BP-108's dialogue cap). Never FAIL: the script goes back to the writers' room (D-99)."""
    out = []
    lo, hi = F.NARRATOR_SHARE
    share = doc["narrator_share_words"]
    if doc["narrator_words"] + doc["dialogue_words"] and not lo <= share <= hi:
        out.append({"rule": "KP-39", "severity": "REVIEW", "where": "speech_mix",
                    "detail": f"the narrator has {share:.1%} of the audible words (nominal {F.NARRATOR_NOMINAL:.0%}, band "
                              f"{lo:.0%}-{hi:.0%}, BP-105): back to the writers' room, never a silent rewrite"})
    if doc["longest_voiced_cu_s"] > F.DIALOGUE_SHOT_MAX_S:
        out.append({"rule": "KP-36", "severity": "REVIEW", "where": "speech_mix",
                    "detail": f"a seen voiced shot of {doc['longest_voiced_cu_s']:g} s: lip-sync coverage is at most "
                              f"{F.DIALOGUE_SHOT_MAX_S:g} s a shot (BP-108); split it onto an off-screen cover shot"})
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2

    def opt(name: str) -> str | None:
        if name in argv:
            i = argv.index(name)
            val = argv[i + 1]
            del argv[i:i + 2]
            return val
        return None

    spine_p, shots_p, job, out_p = opt("--spine"), opt("--film-shots"), opt("--job-id"), opt("--out")
    script_p = Path(argv[0])
    base = (Path(out_p).parent if out_p else script_p.parent).resolve()

    def ref(p: Path) -> dict:
        p = p.resolve()
        try:
            rel = p.relative_to(base).as_posix()
        except ValueError:
            rel = p.as_posix()
        return {"path": rel, "sha256": contracts.sha256_file(p)}

    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))  # noqa: E731
    refs = {"script": ref(script_p)}
    spine = film = None
    if spine_p:
        spine, refs["audio_spine"] = load(spine_p), ref(Path(spine_p))
    if shots_p:
        film, refs["film_shots"] = load(shots_p), ref(Path(shots_p))
    doc = report(load(script_p), refs=refs, job_id=job or script_p.parent.name, spine=spine, film_shots=film)
    for f in findings(doc):
        print(f"{f['severity']} {f['rule']} {f['where']}: {f['detail']}")
    print(f"narrator {doc['narrator_share_words']:.1%} of {doc['narrator_words'] + doc['dialogue_words']} audible words; "
          f"{doc['lipsync_shots']} lip-sync shots, longest {doc['longest_voiced_cu_s']:g} s")
    if out_p:
        write_json_atomic(Path(out_p), doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
