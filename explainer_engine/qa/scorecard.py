"""The seven-point test every video passes (PRODUCTION_RULES gate 9, creator 2026-10-16). numpy + stdlib.

1 narration tone and sync  2 sound effects and sync  3 pictures fit the topic  4 pictures fit the topic's clichés
5 pictures fit each other  6 editing against general standards  7 the whole video: fun, interesting, easy to follow, sticky.
``score(...)`` returns one row per check: {id, name, status PASS|REVIEW|FAIL, evidence[], human: bool}. A row with ``human`` is
decided by the creator's listening or viewing; the machine only gathers evidence. A FAIL starts the failure loop: find the
cause, fix the general rule (not only this video), run again.
"""

from __future__ import annotations

import re

import numpy as np

from ..edit import shot_rules as R

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


def score(shots, words, text, look, *, pic_stats=None, judge=None, audio=None, sound_events=None) -> list[dict]:
    """shots/words as in shot_rules; text = plain narration; pic_stats {picture: stats}; judge {picture: verdict};
    audio {voice_rms_db, bed_rms_db, music_rms_db, lufs}; sound_events [{id, at}] on the video clock."""
    rows = []
    n_words = len(words)
    dur = words[-1]["e"] - words[0]["s"] if words else 0.0
    wpm = n_words / dur * 60 if dur else 0.0
    ev = [f"{n_words} words in {dur:.1f} s = {wpm:.0f} wpm (target 155-175)"]
    st = "PASS" if 150 <= wpm <= 180 else "REVIEW"
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
        rows.append(row(2, "sound effects and sync", "REVIEW", ["no sound events recorded"], human=True))
    else:
        masked = [e for e in sound_events if any(w["s"] - 0.02 < e["at"] < w["e"] + 0.02 for w in words)]
        ev.append(f"{len(sound_events)} sound events, {len(masked)} land on a spoken word")
        if masked:
            st = "FAIL"
        if audio:
            ev.append(f"voice {audio['voice_rms_db']:.1f} dB, bed {audio['bed_rms_db']:.1f} dB, music {audio['music_rms_db']:.1f} dB "
                      f"(voice at least 14 dB above bed+music)")
            if audio["voice_rms_db"] - max(audio["bed_rms_db"], audio["music_rms_db"]) < 14:
                st = "FAIL"
            if "lufs" in audio:
                ev.append(f"integrated loudness {audio['lufs']:.1f} LUFS (target -16 to -12)")
                if not -17.5 <= audio["lufs"] <= -11:
                    st = worst([st, "REVIEW"])
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

    found = R.check_shots([{k: v for k, v in s.items() if k != "prompt"} for s in shots], words, look)
    fails = [f for f in found if f["severity"] == "FAIL"]
    ds = [s["end"] - s["start"] for s in shots]
    hard = sum(1 for s in shots if s.get("transition", "cut") == "cut") / max(1, len(shots))
    rows.append(row(6, "editing against general standards", "FAIL" if fails else "PASS",
                    [f"UR-01..UR-15: {len(fails)} FAIL, {len(found) - len(fails)} REVIEW", f"{len(shots)} shots, mean {np.mean(ds):.2f} s, "
                     f"{hard:.0%} hard cuts", *[f"{f['rule']} {f['shot']}: {f['detail']}" for f in fails][:8]]))

    loops = sum(1 for s in re.split(r"(?<=[.?!])\s+", text) if s.strip().endswith("?"))
    ev = [f"hook is a question by 5 s: {'yes' if R.pauses_from_words(words) and words[0]['s'] < 1 else 'check'}",
          f"{loops} questions, {len(shots) / (dur / 60):.0f} shots per minute",
          "fun, interesting, easy to follow, makes you stay: the creator watches the whole video once, no pausing"]
    rows.append(row(7, "the whole video: fun, interesting, easy to follow, sticky", "REVIEW", ev, human=True))
    return rows


def markdown(rows: list[dict]) -> str:
    out = ["| # | check | status | evidence |", "|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['id']} | {r['name']}{' (creator decides)' if r['human'] else ''} | {r['status']} | "
                   + "<br>".join(r["evidence"]) + " |")
    return "\n".join(out) + "\n"
