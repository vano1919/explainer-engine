"""The seven-point test every video passes (PRODUCTION_RULES gate 9, creator 2026-10-16). numpy + stdlib.

1 narration tone and sync  2 sound effects and sync  3 pictures fit the topic  4 pictures fit the topic's clichés
5 pictures fit each other  6 editing against general standards  7 the whole video: fun, interesting, easy to follow, sticky.
``score(...)`` returns one row per check: {id, name, status PASS|REVIEW|FAIL, evidence[], human: bool}. A row with ``human`` is
decided by the creator's listening or viewing; the machine only gathers evidence. A FAIL starts the failure loop: find the
cause, fix the general rule (not only this video), run again.

    python -m explainer_engine.qa.scorecard <episode folder>    # the D-43 flow: writes scorecard.md + scorecard.json, exit 1 on a FAIL

The folder holds ``production_script.json``, ``words.json``, ``timed.json`` (else the script is timed on the words) and, after
the render, ``assemble_report.json`` (the mix's measured loudness and verdicts, BP-50 / BP-51) and the pictures. Check 6 then
counts the D-43 editing rules (``production/validate.check_timed``), not the legacy shot rules.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

from ..edit import shot_rules as R
from ..standards import sourced_rules as SR
from . import targets

# BP-01: the one heard-pace band (PASS inside, REVIEW between, the registry's severity outside the fail bounds: BP-01 is a
# hypothesis, so that is REVIEW until a second source type makes it binding; D-59 "hypothesis = REVIEW only")
WPM_TARGET, WPM_MIN, WPM_MAX = SR.T("BP-01", "wpm_target"), SR.T("BP-01", "wpm_min"), SR.T("BP-01", "wpm_max")
WPM_FAIL_BELOW, WPM_FAIL_ABOVE = SR.T("BP-01", "wpm_fail_below"), SR.T("BP-01", "wpm_fail_above")
# BP-54: a sound effect whose onset sits inside this window of a word's onset is synced to that word (it lands on its frame)
SYNC_EARLY_S, SYNC_LATE_S = SR.T("BP-54", "early_max_ms") / 1000, SR.T("BP-54", "late_max_ms") / 1000

LUMA = np.array([0.2126, 0.7152, 0.0722])


def picture_stats(img: np.ndarray) -> dict:
    """img float RGB [0,1]: mean luma, mean saturation, mean warmth (R-B). Used to find pictures that do not belong together."""
    x = np.asarray(img, dtype=np.float64)
    mx, mn = x.max(axis=2), x.min(axis=2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return {"luma": float((x @ LUMA).mean()), "sat": float(sat.mean()), "warm": float((x[..., 0] - x[..., 2]).mean())}


def outliers(stats: dict[str, dict], k: float = 2.5) -> list[str]:
    """Pictures whose luma/saturation/warmth sit more than k robust deviations from the episode median."""
    bad = []
    for key in ("luma", "sat", "warm"):
        vals = np.array([s[key] for s in stats.values()])
        med = np.median(vals)
        mad = np.median(np.abs(vals - med)) * 1.4826 + 1e-6
        bad += [n for n, s in stats.items() if abs(s[key] - med) / mad > k]
    return sorted(set(bad))


def row(i, name, status, evidence, human=False):
    return {"id": i, "name": name, "status": status, "evidence": evidence, "human": human}


def worst(statuses):
    return "FAIL" if "FAIL" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS"


def severity(rule_id: str) -> str:
    """A rule's severity as the registry holds it; a hypothesis never FAILs (D-59)."""
    r = SR.rule(rule_id)
    sev = r.get("severity", "REVIEW")
    return "REVIEW" if r["status"] == "hypothesis" and sev == "FAIL" else sev


def pace_verdict(wpm: float) -> str:
    """BP-01 on the measured heard pace."""
    if WPM_MIN <= wpm <= WPM_MAX:
        return "PASS"
    if wpm < WPM_FAIL_BELOW or wpm > WPM_FAIL_ABOVE:
        return severity("BP-01")
    return "REVIEW"


def synced(event: dict, words: list[dict]) -> bool:
    """BP-54: the effect starts on a word (inside the sync window of that word's onset): it lands with its event."""
    return any(-SYNC_EARLY_S <= event["at"] - w["s"] <= SYNC_LATE_S for w in words)


def masking(sound_events: list[dict], words: list[dict]) -> list[dict]:
    """BP-66: the effects that overlap a spoken word without being synced to a word (a cut whoosh, a sound starting inside
    speech). A synced effect is judged by BP-54 and its level by AL-04 / BP-52, not here."""
    return [e for e in sound_events if not synced(e, words)
            and any(w["s"] < e["at"] + e.get("dur", 0.0) and e["at"] < w["e"] for w in words)]


def score(shots, words, text, look, *, pic_stats=None, judge=None, audio=None, sound_events=None, timed_findings=None) -> list[dict]:
    """shots/words as in shot_rules; text = plain narration; pic_stats {picture: stats}; judge {picture: verdict};
    audio = ``assemble_report.json``'s ``audio`` (lufs, true_peak and their verdicts, voice_lufs / ldr_lu / ldr_verdict,
    voice_lu / music_lu / bed_lu when the stems were measured, the older *_rms_db); sound_events [{id, at}] on the video clock;
    timed_findings = ``validate.check_timed`` of a D-43 episode (check 6 counts them instead of the legacy shot rules)."""
    rows = []
    n_words = len(words)
    dur = words[-1]["e"] - words[0]["s"] if words else 0.0
    wpm = n_words / dur * 60 if dur else 0.0
    ev = [f"{n_words} words in {dur:.1f} s = {wpm:.0f} wpm (BP-01: target {WPM_TARGET}, accepted {WPM_MIN}-{WPM_MAX}, "
          f"{severity('BP-01')} below {WPM_FAIL_BELOW} or above {WPM_FAIL_ABOVE})"]
    st = pace_verdict(wpm) if dur else "REVIEW"
    cuts = [s["start"] for s in shots[1:]]
    bad_cuts = [c for c in cuts if not R.cut_ok(c, words)]
    ev.append(f"{len(cuts) - len(bad_cuts)} of {len(cuts)} cuts sit in punctuated pauses (UR-12)")
    if bad_cuts:
        st = "FAIL"
    qs = len(re.findall(r"\?", text))
    ev.append(f"{qs} questions in {dur / 60:.1f} min; tone, stress and question intonation: the creator listens")
    rows.append(row(1, "narration tone and sync", st, ev, human=True))

    ev, st = [], "PASS"
    if sound_events is None:
        ev.append("no sound events recorded")
        st = "REVIEW"
    else:
        n_sync = sum(1 for e in sound_events if synced(e, words))
        masked = masking(sound_events, words)
        ev.append(f"{len(sound_events)} sound events: {n_sync} synced to their word (BP-54), {len(masked)} mask a spoken word "
                  "(BP-66)" + (": " + ", ".join(f"{e.get('id', '?')} at {e['at']:.2f}s" for e in masked[:6]) if masked else ""))
        if masked:
            st = worst([st, severity("BP-66")])
    if audio:  # the measured mix is judged whether or not effects were placed (BP-50..BP-52, BP-61)
        ev, st = audio_rows(audio, ev, st)
    ev.append("does the sound feel natural and helpful: the creator listens")
    rows.append(row(2, "sound effects and sync", st, ev, human=True))

    if judge:
        fails = [p for p, v in judge.items() if v["status"] == "FAIL"]
        revs = [p for p, v in judge.items() if v["status"] == "REVIEW"]
        rows.append(row(3, "pictures fit the topic and its world", "FAIL" if fails else "REVIEW" if revs else "PASS",
                        [f"visual judge: {len(judge) - len(fails) - len(revs)} PASS, {len(revs)} REVIEW, {len(fails)} FAIL"]
                        + [f"{p}: {judge[p]['fails'] or judge[p]['review']}" for p in fails + revs][:12]))
    else:
        rows.append(row(3, "pictures fit the topic and its world", "REVIEW", ["visual judge not run"]))
    rows.append(row(4, "pictures fit the topic's cliché expectations", "REVIEW",
                    ["checked against the era codex `cliches` list in the prompts; whether it reads as the genre: the creator looks"],
                    human=True))
    if pic_stats:
        out = outliers(pic_stats)
        rows.append(row(5, "pictures fit each other", "REVIEW" if out else "PASS",
                        [f"{len(pic_stats)} pictures; luma/saturation/warmth outliers: {out or 'none'}",
                         "one engine, one look thread, one grade; side-by-side sheet: the creator looks"], human=True))
    else:
        rows.append(row(5, "pictures fit each other", "REVIEW", ["no picture statistics"]))

    ds = [s["end"] - s["start"] for s in shots]
    hard = sum(1 for s in shots if s.get("transition", "cut") == "cut") / max(1, len(shots))
    if timed_findings is not None:  # the D-43 flow: the editing rules that really run on a timed script (PV, MO, VB, AL, BP)
        fails = [f for f in timed_findings if f["severity"] == "FAIL"]
        rows.append(row(6, "editing against general standards", "FAIL" if fails else "PASS",
                        [f"check_timed: {len(fails)} FAIL, {len(timed_findings) - len(fails)} REVIEW", f"{len(shots)} shots, mean "
                         f"{np.mean(ds):.2f} s, {hard:.0%} hard cuts", *[f"{f['rule']} {f['where']}: {f['detail']}" for f in fails][:8]]))
    else:
        found = R.check_shots([{k: v for k, v in s.items() if k != "prompt"} for s in shots], words, look)
        fails = [f for f in found if f["severity"] == "FAIL"]
        rows.append(row(6, "editing against general standards", "FAIL" if fails else "PASS",
                        [f"UR-01..UR-15: {len(fails)} FAIL, {len(found) - len(fails)} REVIEW", f"{len(shots)} shots, mean {np.mean(ds):.2f} s, "
                         f"{hard:.0%} hard cuts", *[f"{f['rule']} {f['shot']}: {f['detail']}" for f in fails][:8]]))

    loops = sum(1 for s in re.split(r"(?<=[.?!])\s+", text) if s.strip().endswith("?"))
    ev = [f"speech starts at {words[0]['s']:.1f} s; the hook takes one of BP-03's forms: the creator watches" if words
          else "no words: the hook is not measured",
          f"{loops} questions, {len(shots) / (dur / 60):.0f} shots per minute",
          "fun, interesting, easy to follow, makes you stay: the creator watches the whole video once, no pausing"]
    rows.append(row(7, "the whole video: fun, interesting, easy to follow, sticky", "REVIEW", ev, human=True))
    return rows


def audio_rows(audio: dict, ev: list[str], st: str) -> tuple[list[str], str]:
    """Check 2's measured rows: background under the voice (BP-52), integrated loudness and true peak (BP-50), the dialogue
    anchor (BP-51) and, for a Short, the short-term cap (BP-61). Every number is judged by ``qa/targets``."""
    if "voice_lu" in audio and ("music_lu" in audio or "bed_lu" in audio):
        g = targets.gaps(audio["voice_lu"], audio.get("music_lu"), audio.get("bed_lu"))
        ev.append("background under the voice while speaking: " + ", ".join(f"{k} {v:.1f} LU" for k, v in g.items()) + " (BP-52)")
        st = worst([st, targets.gap_verdict(audio["voice_lu"], audio.get("music_lu"), audio.get("bed_lu"))])
    elif "voice_rms_db" in audio:
        ev.append(f"voice {audio['voice_rms_db']:.1f} dB, bed {audio.get('bed_rms_db', float('nan')):.1f} dB, music "
                  f"{audio.get('music_rms_db', float('nan')):.1f} dB RMS while speaking; BP-52 judges LU on the stems, which this "
                  "mix did not measure: the creator listens")
        st = worst([st, "REVIEW"])
    if "lufs" in audio:
        lo, hi = targets.PROFILES["long"]["pass_band"]
        ev.append(f"integrated loudness {audio['lufs']:.1f} LUFS (PASS {lo:g} to {hi:g}, BP-50)")
        st = worst([st, audio.get("loudness_verdict") or targets.loudness_verdict(audio["lufs"])])
    if "true_peak" in audio:
        ev.append(f"true peak {audio['true_peak']:.1f} dBTP (at most {targets.PROFILES['long']['true_peak_max']:g}, BP-50)")
        st = worst([st, audio.get("true_peak_verdict") or targets.true_peak_verdict(audio["true_peak"])])
    if "lufs" in audio and "voice_lufs" in audio:
        v = audio.get("ldr_verdict") or targets.ldr_verdict(audio["lufs"], audio["voice_lufs"])
        ev.append(f"mix minus narration stem {audio['lufs'] - audio['voice_lufs']:.1f} LU (dialogue is the anchor, BP-51): {v}")
        st = worst([st, v])
    if "max_short_term" in audio and "lufs" in audio:
        v = audio.get("short_term_verdict") or targets.short_term_verdict(audio["max_short_term"], audio["lufs"])
        ev.append(f"loudest short-term window {audio['max_short_term']:.1f} LUFS, {audio['max_short_term'] - audio['lufs']:.1f} LU "
                  f"over integrated (BP-61): {v}")
        st = worst([st, v])
    return ev, st


def markdown(rows: list[dict]) -> str:
    out = ["| # | check | status | evidence |", "|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['id']} | {r['name']}{' (creator decides)' if r['human'] else ''} | {r['status']} | "
                   + "<br>".join(r["evidence"]) + " |")
    return "\n".join(out) + "\n"


# --- the D-43 flow -----------------------------------------------------------------------------------------------------

def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _find(folder: Path, name: str) -> Path | None:
    for p in (folder / name, folder / "render" / name):
        if p.exists():
            return p
    return next(iter(sorted(folder.glob(f"**/{name}"))), None)


def episode_inputs(folder: Path) -> dict:
    """Everything ``score`` needs, read from the episode folder (production_script.json, words.json, timed.json or the script
    timed on the words, assemble_report.json, the pictures, visual_review.json)."""
    from ..production import script as S
    from ..production import timing as T
    from ..production import validate as V
    folder = Path(folder)
    doc = S.load(folder / "production_script.json")
    words_doc = _json(folder / "words.json")
    if not words_doc:
        raise SystemExit(f"{folder}: no words.json (the full read's word timings, `production words`)")
    timed = _json(folder / "timed.json") or T.time_script(doc, words_doc)
    pic_dirs = [folder / d for d in doc.get("picture_dirs", [])] + [folder / "pictures"]
    rep = _find(folder, "assemble_report.json")
    audio = (_json(rep) or {}).get("audio") if rep else None
    pic_stats = {}
    for pid in sorted({s["picture"] for s in timed["shots"]}):
        png = next((d / f"{pid}.png" for d in pic_dirs if (d / f"{pid}.png").exists()), None)
        if png is not None:
            from PIL import Image
            im = Image.open(png).convert("RGB")
            im.thumbnail((96, 96))
            pic_stats[pid] = picture_stats(np.asarray(im, dtype=np.float64) / 255.0)
    review = _json(folder / "visual_review.json")
    judge = None
    if review and isinstance(review.get("pictures"), dict):
        judge = {}
        for pid, ans in review["pictures"].items():
            if isinstance(ans, dict) and ans.get("status") in ("PASS", "REVIEW", "FAIL"):
                judge[pid] = {"status": ans["status"], "fails": ans.get("fails", []), "review": ans.get("review", [])}
    sfx = timed.get("audio", {}).get("sfx", [])
    return {"shots": timed["shots"], "words": words_doc["words"], "text": S.narration_text(doc), "look": doc.get("look", {}),
            "pic_stats": pic_stats or None, "judge": judge or None, "audio": audio,
            "sound_events": [{"id": e["sound"], "at": e["start"], "dur": e["end"] - e["start"]} for e in sfx] if sfx else None,
            "timed_findings": V.check_timed(timed, doc, picture_dirs=pic_dirs)}


def run(folder: Path) -> list[dict]:
    """Score an episode folder and write ``scorecard.md`` / ``scorecard.json`` next to the script."""
    from ..core.store import write_json_atomic, write_text_atomic
    folder = Path(folder)
    inp = episode_inputs(folder)
    rows = score(inp.pop("shots"), inp.pop("words"), inp.pop("text"), inp.pop("look"), **inp)
    verdict = worst([r["status"] for r in rows])
    write_text_atomic(folder / "scorecard.md", f"# Seven-point test: {verdict}\n\n" + markdown(rows))
    write_json_atomic(folder / "scorecard.json", {"schema": "scorecard/1", "episode": folder.name, "verdict": verdict, "rows": rows})
    return rows


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    rows = run(Path(argv[0]))
    for r in rows:
        print(f"{r['status']:6} {r['id']} {r['name']}" + (" (creator decides)" if r["human"] else ""))
        for e in r["evidence"][:4]:
            print(f"       {e}")
    return 1 if any(r["status"] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
