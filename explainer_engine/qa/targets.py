"""House audio targets, one definition for the mixer, the Shorts renderer, the scorecard and the docs: every number is read
from the sourced-rules registry (BP-50 long-form loudness and true peak, BP-51 dialogue anchor, BP-52 background under speech,
BP-59 narration-stem range, BP-61 Shorts loudness; ``explainer_engine/standards/sourced_rules.json``, D-59). Nothing here
copies a number: change the registry, never this file.

Units: integrated loudness in LUFS (ITU-R BS.1770 gating), true peak in dBTP, differences between stems in LU (loudness
units, measured with the same gating on each stem); the old RMS-dB gap is gone (BP-52 changed the unit). YouTube publishes no
loudness number (support.google.com/youtube/answer/1722171, V-26): the -14 LUFS target is inferred from measurement and the
registry's sources. ``measure_file`` runs ffmpeg's ebur128 on a delivered file so the verdict stands next to the number.
"""

from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR


def _cap(verdict: str, rule_id: str) -> str:
    """A rule whose registry severity is REVIEW never FAILs (a hypothesis or a binding REVIEW rule, D-59)."""
    sev = SR.rule(rule_id).get("severity", "REVIEW")
    return "REVIEW" if verdict == "FAIL" and sev != "FAIL" else verdict


def _profiles() -> dict:
    long_t, short_t = SR.rule("BP-50")["thresholds"], SR.rule("BP-61")["thresholds"]
    long = {"rule": "BP-50", "lufs": float(long_t["lufs"]), "pass_band": tuple(long_t["pass_band"]),
            "allowed": tuple(long_t["allowed"]), "true_peak_max": float(long_t["true_peak_max"]),
            "limiter_tp": float(long_t["limiter_tp"]),
            "stem_lra_max": float(SR.T("BP-59", "stem_lra_max")),  # BP-59: the narration stem's range is the gate; the mix's LRA is informative
            "lra_gate": True}
    # BP-61: the Shorts profile keeps BP-50's integrated target and bands (the short-form rule names the same -14 / -1 numbers),
    # adds the short-term cap and drops every loudness-range gate (EBU R 128 s1: no LRA under two minutes).
    short = {**long, "rule": "BP-61", "lufs": float(short_t["lufs"]), "true_peak_max": float(short_t["true_peak_max"]),
             "max_short_term_above_lu": float(short_t["max_short_term_above_lu"]),
             "phone_hpf_hz": int(short_t["phone_hpf_hz"]), "lra_gate": False}
    return {"long": long, "short": short}


PROFILES = _profiles()


def loudnorm(profile: str = "long") -> str:
    """The ffmpeg loudnorm filter for a profile (the limiter sits under the true-peak ceiling: codec headroom, BP-50).
    The long profile gives loudnorm the narration stem's range cap (BP-59) as its range target; the short profile passes no
    LRA term (BP-61: no loudness-range rule under two minutes)."""
    p = PROFILES[profile]
    f = f"loudnorm=I={p['lufs']:g}:TP={p['limiter_tp']:g}"
    return f + (f":LRA={p['stem_lra_max']:g}" if p["lra_gate"] else "")


def loudness_verdict(lufs: float, profile: str = "long") -> str:
    p = PROFILES[profile]
    if p["pass_band"][0] <= lufs <= p["pass_band"][1]:
        return "PASS"
    return _cap("REVIEW" if p["allowed"][0] <= lufs <= p["allowed"][1] else "FAIL", p["rule"])


def true_peak_verdict(dbtp: float, profile: str = "long") -> str:
    p = PROFILES[profile]
    return "PASS" if dbtp <= p["true_peak_max"] else _cap("FAIL", p["rule"])


def ldr_verdict(mix_lufs: float, voice_lufs: float) -> str:
    """BP-51 dialogue anchor: programme loudness minus the narration stem's loudness (LU)."""
    d = mix_lufs - voice_lufs
    if d > SR.T("BP-51", "ldr_max_lu"):
        return _cap("FAIL", "BP-51")
    return "REVIEW" if d > SR.T("BP-51", "ldr_review_lu") else "PASS"


def _power_sum_lufs(levels: list[float]) -> float:
    return 10 * math.log10(sum(10 ** (x / 10) for x in levels))


def gaps(voice_lu: float, music_lu: float | None = None, bed_lu: float | None = None) -> dict:
    """The distances (LU) the BP-52 floors are judged on: voice minus music, voice minus bed, voice minus their power sum."""
    out: dict = {}
    if music_lu is not None:
        out["music"] = voice_lu - music_lu
    if bed_lu is not None:
        out["bed"] = voice_lu - bed_lu
    both = [x for x in (music_lu, bed_lu) if x is not None]
    if both:
        out["combined"] = voice_lu - _power_sum_lufs(both)
    return out


def gap_verdict(voice_lu: float, music_lu: float | None = None, bed_lu: float | None = None) -> str:
    """BP-52: background under speech in LU on the stems while the narrator speaks (music, ambience bed, their sum)."""
    g = gaps(voice_lu, music_lu, bed_lu)
    bad = ("music" in g and g["music"] < SR.T("BP-52", "music_under_lu")) \
        or ("bed" in g and g["bed"] < SR.T("BP-52", "bed_under_lu")) \
        or ("combined" in g and g["combined"] < SR.T("BP-52", "combined_under_lu"))
    return _cap("FAIL", "BP-52") if bad else "PASS"


def short_term_verdict(max_short_term: float, integrated: float) -> str:
    """BP-61: the loudest 3 s window of a Short stays within ``max_short_term_above_lu`` of its integrated loudness."""
    over = max_short_term - integrated > PROFILES["short"]["max_short_term_above_lu"]
    return _cap("FAIL", "BP-61") if over else "PASS"


def stem_lra_verdict(lra: float) -> str:
    """BP-59: the narration stem's loudness range (LU)."""
    return "PASS" if lra <= PROFILES["long"]["stem_lra_max"] else _cap("FAIL", "BP-59")


_NUM = r"(-?\d+(?:\.\d+)?|-inf)"


def parse_ebur128(stderr: str) -> dict:
    """What ffmpeg's ``ebur128=peak=true`` printed: integrated (LUFS), loudness range (LU), true peak (dBTP) and the loudest
    short-term window (LUFS; the per-frame ``S:`` column, -inf lines ignored)."""
    out: dict = {}
    tail = stderr.rsplit("Summary:", 1)[-1]
    m = re.search(rf"I:\s+{_NUM}\s+LUFS", tail)
    if m:
        out["lufs"] = float(m.group(1))
    m = re.search(rf"LRA:\s+{_NUM}\s+LU", tail)
    if m:
        out["lra"] = float(m.group(1))
    m = re.search(rf"Peak:\s+{_NUM}\s+dBFS", tail)  # the true-peak block prints "Peak: -1.2 dBFS"
    if m:
        out["true_peak"] = float(m.group(1))
    shorts = [float(x) for x in re.findall(rf"\bS:\s+{_NUM}", stderr.split("Summary:", 1)[0]) if x != "-inf"]
    if shorts:
        out["max_short_term"] = max(shorts)
    return out


def measure_file(path: Path) -> dict:
    """ebur128 of a delivered file (any container ffmpeg reads): the numbers the verdicts are written next to (BP-50, BP-61)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    found = parse_ebur128(err)
    if "lufs" not in found:
        raise RuntimeError(f"no loudness measured for {path}")
    return found


def normalise_file(src: Path, dst: Path, profile: str = "long", sr: int = 48000, rounds: int = 2, channels: int = 1) -> dict:
    """Loudnorm, then trim to the target (BP-50). Single-pass loudnorm on a wide-range mix (narration over quiet beds) lands
    short of the target: the titans preview came out 2.5 LU low. Each round measures the file, shifts it by the gap with a
    static gain and holds the peak under the limiter ceiling (limited at 4x the rate, so intersample peaks are caught); the range is not touched further. Returns the last measurement."""
    p = PROFILES[profile]
    run = ["ffmpeg", "-v", "error", "-y", "-i"]
    subprocess.run(run + [str(src), "-af", loudnorm(profile), "-ar", str(sr), "-ac", str(channels), str(dst)], check=True)
    meas = measure_file(dst)
    for _ in range(rounds):
        gap = p["lufs"] - meas["lufs"]
        if abs(gap) <= 0.3:
            break
        tmp = dst.with_name(dst.stem + ".trim" + dst.suffix)
        lim = 10 ** (p["limiter_tp"] / 20)
        subprocess.run(run + [str(dst), "-af", f"volume={gap:.2f}dB,aresample=192000,alimiter=limit={lim:.4f}:level=disabled:attack=5:release=80,aresample={sr}",
                              "-ar", str(sr), "-ac", str(channels), str(tmp)], check=True)
        tmp.replace(dst)
        meas = measure_file(dst)
    return meas


def verdicts(meas: dict, profile: str = "long", voice_lufs: float | None = None) -> dict:
    """The verdicts a report records next to a measurement: loudness and true peak (BP-50 / BP-61), the Shorts' short-term cap
    (BP-61), the dialogue anchor (BP-51) when the narration stem's loudness is known."""
    out = {"loudness_verdict": loudness_verdict(meas["lufs"], profile)}
    if "true_peak" in meas:
        out["true_peak_verdict"] = true_peak_verdict(meas["true_peak"], profile)
    if profile == "short" and "max_short_term" in meas:
        out["short_term_verdict"] = short_term_verdict(meas["max_short_term"], meas["lufs"])
    if voice_lufs is not None:
        out["ldr_lu"] = round(meas["lufs"] - voice_lufs, 2)
        out["ldr_verdict"] = ldr_verdict(meas["lufs"], voice_lufs)
    return out


def failures(report: dict) -> list[str]:
    """The FAIL verdicts of a report, each with its number (what a final render or a Short stops on, never silently)."""
    names = {"loudness_verdict": ("lufs", "LUFS"), "true_peak_verdict": ("true_peak", "dBTP"),
             "short_term_verdict": ("max_short_term", "LUFS short-term"), "ldr_verdict": ("ldr_lu", "LU over the voice")}
    out = []
    for key, (num, unit) in names.items():
        if report.get(key) == "FAIL":
            out.append(f"{key.replace('_verdict', '')} {report.get(num)} {unit}")
    return out
