"""Mix validators (final plan S13, W2): loudness, true peak, voice-over-music gap, effects per scene, one continuous bed, and the two
critic rows of the sound checklist (CRAFT-SND-09, CRAFT-SND-11).

Loudness and peak come from BP-50 (the registry's pass band; BP-208's tighter band is REVIEW), the gap from BP-208 (the binding
floor stays BP-52), density and the bed from BP-209. Measurements are dicts (``lufs``, ``true_peak``, ``voice_lufs``,
``music_lufs`` as ``qa/targets.parse_ebur128`` names them) or a file measured with ffmpeg (NOT_RUN when ffmpeg is absent).
"""
from __future__ import annotations

import shutil

from explainer_engine.qa import gates as G
from explainer_engine.validators import _common as C

RULE_IDS = ("CRAFT-SND-09", "CRAFT-SND-11", "VAL-MIX-01", "VAL-MIX-02", "VAL-MIX-03", "VAL-MIX-04", "VAL-MIX-05")


def loudness(meas: dict) -> dict:
    """VAL-MIX-01: integrated loudness inside BP-50's pass band (a miss is that rule's severity) and inside BP-208's tight band
    around the target (a miss is REVIEW)."""
    if meas.get("lufs") is None:
        return G.row("VAL-MIX-01", None, "NOT_RUN: no integrated loudness measured")
    target, band = C.T("BP-50", "lufs"), C.T("BP-50", "pass_band")
    tight = C.T("BP-208", "lufs_tight_band")
    if target is None or band is None or tight is None:
        return C.missing_threshold("VAL-MIX-01", "BP-50/BP-208", "lufs, pass_band, lufs_tight_band")
    x = float(meas["lufs"])
    if not band[0] <= x <= band[1]:
        return G.row("VAL-MIX-01", False, f"{x} LUFS is outside BP-50's pass band {band}", x, level=C.level("BP-50"))
    return G.row("VAL-MIX-01", abs(x - target) <= tight, f"{x} LUFS; target {target} +/- {tight} (BP-208 tight band)", x,
                 level=G.REVIEW)


def true_peak(meas: dict) -> dict:
    """VAL-MIX-02: true peak at or under BP-50's ceiling."""
    if meas.get("true_peak") is None:
        return G.row("VAL-MIX-02", None, "NOT_RUN: no true peak measured")
    cap = C.T("BP-50", "true_peak_max")
    if cap is None:
        return C.missing_threshold("VAL-MIX-02", "BP-50", "true_peak_max")
    x = float(meas["true_peak"])
    return C.check("VAL-MIX-02", x <= cap, "BP-50", f"true peak {x} dBTP; at most {cap}", x)


def voice_over_music(meas: dict) -> dict:
    """VAL-MIX-03: the narration stem is at least voice_over_music_min_lu above the music stem while the voice speaks."""
    if meas.get("voice_lufs") is None or meas.get("music_lufs") is None:
        return G.row("VAL-MIX-03", None, "NOT_RUN: the voice and music stem loudness were not measured")
    need = C.T("BP-208", "voice_over_music_min_lu")
    if need is None:
        return C.missing_threshold("VAL-MIX-03", "BP-208", "voice_over_music_min_lu")
    gap = float(meas["voice_lufs"]) - float(meas["music_lufs"])
    return C.check("VAL-MIX-03", gap >= need, "BP-208", f"voice is {gap:.1f} LU over the music; at least {need}", gap)


def effects_per_scene(scenes: list[dict]) -> list[dict]:
    """VAL-MIX-04: every scene carries at least effects_per_scene_min effects (``scenes[i]['effects']``, a list)."""
    need = C.T("BP-209", "effects_per_scene_min")
    if need is None:
        return [C.missing_threshold("VAL-MIX-04", "BP-209", "effects_per_scene_min")]
    rows = [C.check(f"VAL-MIX-04:{s.get('scene_id', i)}", len(s.get("effects") or []) >= need, "BP-209",
                    f"{len(s.get('effects') or [])} effects (at least {need})", len(s.get("effects") or []))
            for i, s in enumerate(scenes)]
    return rows or [G.row("VAL-MIX-04", None, "NOT_RUN: no scene listed")]


def one_continuous_bed(beds: list[dict], duration_s: float | None) -> dict:
    """VAL-MIX-05: at most beds_max bed layers (``{start, end}`` seconds) covering 0..duration with no gap over bed_gap_max_s."""
    most, gap_max = C.T("BP-209", "beds_max"), C.T("BP-209", "bed_gap_max_s")
    if most is None or gap_max is None:
        return C.missing_threshold("VAL-MIX-05", "BP-209", "beds_max/bed_gap_max_s")
    if not beds or duration_s is None:
        return G.row("VAL-MIX-05", None, "NOT_RUN: no bed layer listed or no episode duration")
    iv = sorted((float(b["start"]), float(b["end"])) for b in beds)
    gaps = [iv[0][0]] + [b[0] - a[1] for a, b in zip(iv, iv[1:])] + [float(duration_s) - max(e for _, e in iv)]
    worst = max(gaps)
    ok = len(iv) <= most and worst <= gap_max + 1e-9
    return C.check("VAL-MIX-05", ok, "BP-209", f"{len(iv)} bed layer(s) (at most {most}); longest gap {worst:.2f} s (at most {gap_max})",
                   {"layers": len(iv), "longest_gap_s": worst})


def encoded_embodied(layers: list[dict]) -> dict:
    """CRAFT-SND-09 (critic): every layer says whether its sound is ``encoded`` (narration) or ``embodied``; whether two encoded
    streams ever play at once is judged."""
    miss = [str(l.get("id", i)) for i, l in enumerate(layers) if l.get("colour") not in ("encoded", "embodied")]
    return C.critic("CRAFT-SND-09", "BP-121", [f"colour of layer {m}" for m in miss[:10]],
                    "encoded and embodied sound are balanced: never two encoded streams at once")


def motifs(owners: list[dict]) -> dict:
    """CRAFT-SND-11 (critic): every faction, hero and the channel names a ``motif`` (BP-123)."""
    miss = [str(o.get("owner", i)) for i, o in enumerate(owners) if not o.get("motif")]
    return C.critic("CRAFT-SND-11", "BP-123", [f"motif of {m}" for m in miss[:10]],
                    "one motif per faction, hero and channel; it returns when its owner acts")


def check_measurements(meas: dict, *, scenes: list[dict] | None = None, beds: list[dict] | None = None,
                       duration_s: float | None = None, layers: list[dict] | None = None, owners: list[dict] | None = None) -> list[dict]:
    rows = [loudness(meas), true_peak(meas), voice_over_music(meas)]
    rows += effects_per_scene(scenes) if scenes is not None else [G.row("VAL-MIX-04", None, "NOT_RUN: no scene list given")]
    rows.append(one_continuous_bed(beds or [], duration_s))
    if layers is not None:
        rows.append(encoded_embodied(layers))
    if owners is not None:
        rows.append(motifs(owners))
    return rows


def check_file(path, **kw) -> list[dict]:
    """Measure a delivered file with ffmpeg's ebur128, then ``check_measurements``; NOT_RUN rows when ffmpeg is absent."""
    if shutil.which("ffmpeg") is None:
        return [G.row("VAL-MIX-01", None, "NOT_RUN: ffmpeg is not installed"), G.row("VAL-MIX-02", None, "NOT_RUN: ffmpeg is not installed")]
    from explainer_engine.qa import targets
    try:
        meas = targets.measure_file(path)
    except RuntimeError as exc:
        return [G.row("VAL-MIX-01", None, f"NOT_RUN: {exc}"), G.row("VAL-MIX-02", None, f"NOT_RUN: {exc}")]
    return check_measurements({**meas, **{k: kw.pop(k) for k in ("voice_lufs", "music_lufs") if k in kw}}, **kw)
