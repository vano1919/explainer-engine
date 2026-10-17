"""House audio targets, one definition for the mixer, the Shorts renderer, the scorecard and the docs (P-90, P-91, P-93, P-101).

These are the channel's own targets (D-08, measured on Episode 1), not YouTube requirements: YouTube's recommended upload
settings name codecs and bitrates but no loudness (support.google.com/youtube/answer/1722171, read 2026-10-17, V-26); the
"-14 LUFS" playback reference is reported by secondary sources only. Units: integrated loudness in LUFS (EBU R128 / ITU-R
BS.1770 gating), true peak in dBTP, the voice-over-background gap as a difference of RMS levels in dB. Never mix them up.

Where the older documents disagreed (P-90 allowed -16..-13, the scorecard -17.5..-11; P-93 and Q-T08 asked a 10 dB gap, the
scorecard 14 dB; the Shorts renderer used -15 LUFS), the stricter value was kept (invariant 10).
"""

from __future__ import annotations

PROFILES = {
    "long": {"lufs": -14.0, "pass_band": (-15.0, -13.0), "allowed": (-16.0, -13.0), "true_peak_max": -1.0,
             "limiter_tp": -1.5, "lra": 9, "voice_gap_min_db": 14.0},
    "short": {"lufs": -14.0, "pass_band": (-15.0, -13.0), "allowed": (-16.0, -13.0), "true_peak_max": -1.0,
              "limiter_tp": -1.5, "lra": 9, "voice_gap_min_db": 14.0},
}


def loudnorm(profile: str = "long") -> str:
    """The ffmpeg loudnorm filter for a profile (the limiter sits 0.5 dB under the true-peak ceiling: codec headroom)."""
    p = PROFILES[profile]
    return f"loudnorm=I={p['lufs']:g}:TP={p['limiter_tp']:g}:LRA={p['lra']}"


def loudness_verdict(lufs: float, profile: str = "long") -> str:
    p = PROFILES[profile]
    if p["pass_band"][0] <= lufs <= p["pass_band"][1]:
        return "PASS"
    return "REVIEW" if p["allowed"][0] <= lufs <= p["allowed"][1] else "FAIL"


def true_peak_verdict(dbtp: float, profile: str = "long") -> str:
    return "PASS" if dbtp <= PROFILES[profile]["true_peak_max"] else "FAIL"


def gap_verdict(voice_rms_db: float, background_rms_db: float, profile: str = "long") -> str:
    return "PASS" if voice_rms_db - background_rms_db >= PROFILES[profile]["voice_gap_min_db"] else "FAIL"
