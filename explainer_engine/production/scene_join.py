"""The scene join (W1 of the realism plan, 2026-11-12): video clips that each carry their own speech (LTX dialogue clips) become
one scene whose sound is believable, and the delivered file is measured by the sound-realism gate (``qa/sound_realism``).

What the hand join of 2026-11-12 got wrong, and what this does instead:

* **Dead air** (the battle: 39 % of the dialogue under -40 dBFS, -63.5 dBFS before "Attack!"): the scene's bed
  (``episode/sound_plan`` classes, real library takes, rendered by ``audio/stems``) runs under every clip and across every cut;
  the clips' own track is the dialogue layer, so the bed ducks under it (BP-53) and never stops.
* **The illogical fast cut** (c1 -> c2 cut 0.3 s after the line, then 1.26 s of nothing): each clip is trimmed by its MEASURED
  speech (``trims``: a head lead before the first word, a tail after the last, BP-190); the pause from line to line is the
  variant's ``pause_s``, split into tail and head.
* **Clicks at the seam** (BP-188): each clip's own track gets a ``CLIP_FADE_S`` fade at both ends (BP-191); the bed crosses the
  cut, so the fade is never heard as a hole.

The card (``scene_join/1``) says what the picture shows and so what may sound (SD-02 "sound sources", here BP-192): the bed's
classes for the place, the spot sounds with their clip and time, which clips are chained (one continuous motion: never trimmed,
their pauses are the generator's), which pauses are intended, and an establishing ``lead_s``. A class with no real take stops
the join (``sound_plan.shippable``) and lands on the needs list; nothing is ever synthesised.

    python -m explainer_engine.production.scene_join <card.json> --out <dir> [--pause 0.3] [--bed-under 18] [--root <clips>]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

from explainer_engine.audio import stems as ST
from explainer_engine.audio.free_import import decode
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.episode import sound_plan as SP
from explainer_engine.qa import sound_realism as R
from explainer_engine.standards import sourced_rules as SR_RULES

SCHEMA = "scene_join/1"
RATE = 48000
FPS = 24
CLIP_FADE_S = float(np.mean(SR_RULES.T("BP-191", "clip_fade_s")))      # 0.1 s: each clip's own track, both ends
HEAD_LEAD_S = SR_RULES.T("BP-190", "head_lead_s")                     # [lo, hi] before a line's first word
TAIL_S = SR_RULES.T("BP-190", "tail_s")                               # [lo, hi] after its last word
DIALOGUE_RMS_DBFS = -20.0      # every clip's speech set to one level (the speakers of LTX clips differ by up to 9 dB)
BED_UNDER_MIN_LU = float(SR_RULES.T("BP-52", "bed_under_lu"))       # BP-52 (binding): the bed at least 15 LU under the voice
BED_UNDER_DEFAULT = BED_UNDER_MIN_LU


def frame_round(t: float) -> float:
    return round(round(t * FPS) / FPS, 4)


def split_pause(pause_s: float) -> tuple[float, float]:
    """(tail, head) of a pause between two clips' lines: 40 % before the cut as the head lead of the next line, inside
    BP-190's head range where the pause allows it; the rest is the tail after the last word."""
    head = min(HEAD_LEAD_S[1], max(0.08, 0.4 * pause_s))
    return round(pause_s - head, 3), round(head, 3)


def trims(spans: list[tuple[float, float]], dur: float, *, head: float, tail: float, lead_s: float | None = None,
          keep: tuple[float, float] | None = None) -> tuple[float, float]:
    """(in, out) of one clip from its measured speech: ``head`` before the first word (``lead_s`` instead for an establishing
    shot), ``tail`` after the last; ``keep`` overrides both (a clip without speech, or one the card keeps whole). Times snap to
    frames so the picture and the sound cut together."""
    if keep is not None:
        a, b = keep
    elif not spans:
        a, b = 0.0, dur
    else:
        a = max(0.0, spans[0][0] - (lead_s if lead_s is not None else head))
        b = min(dur, spans[-1][1] + tail)
    a, b = frame_round(a), frame_round(b)
    if b - a < 1.0 / FPS:
        raise ContractError(f"clip trims to nothing ({a}..{b} s)")
    return a, b


def _fade_ends(x: np.ndarray, s: float) -> np.ndarray:
    k = min(len(x) // 2, int(s * RATE))
    if k > 0:
        r = np.linspace(0, 1, k, dtype=np.float32)
        x[:k] *= r
        x[-k:] *= r[::-1]
    return x


BETWEEN_LINES_DB = -15.0     # a clip's own track between its lines: its hiss and room differ clip by clip (measured up to 10 dB
                             # at a cut, love scene 2026-11-12), so the scene's bed carries the background there (dialogue edit)
SPEECH_PAD_S = 0.08


def between_lines_gain(n: int, spans, rate: int = RATE, depth_db: float = BETWEEN_LINES_DB) -> np.ndarray:
    """Gain over one clip's track: 1 inside its speech (padded), ``depth_db`` between, with 30 ms ramps."""
    g = np.full(n, 10 ** (depth_db / 20), np.float32)
    for a, b in spans:
        g[max(0, int((a - SPEECH_PAD_S) * rate)):min(n, int((b + SPEECH_PAD_S) * rate))] = 1.0
    k = int(0.03 * rate)
    ker = np.ones(k, np.float32) / k
    return np.convolve(g, ker, mode="same").astype(np.float32)


def _rms_db(x: np.ndarray) -> float:
    return R.db(float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))) if len(x) else -120.0


def _speech_level(x: np.ndarray, spans) -> float:
    parts = [x[int(a * RATE):int(b * RATE)] for a, b in spans]
    return _rms_db(np.concatenate(parts)) if parts else _rms_db(x)


def _write_wav(path: Path, x: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def read_stereo(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    return x.reshape(-1, ch)


def _lufs_of(x: np.ndarray) -> float:
    """Integrated loudness (ffmpeg ebur128) of a mono array."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.wav"
        _write_wav(p, x.astype(np.float32))
        r = subprocess.run(["ffmpeg", "-nostats", "-i", str(p), "-af", "ebur128", "-f", "null", "-"], capture_output=True,
                           text=True)
    found = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", r.stderr)
    if not found or found[-1] == "-inf":
        raise ContractError("no loudness: the measured part is silent")
    return float(found[-1])


def plan_of(card: dict, clips: list[dict]) -> dict:
    """A sound_plan/1 of the scene: one shot per clip, one bed for the place (the scene is one place), the spots as authored
    events. No music: a dialogue scene's music is the episode's cue, not the join's."""
    shots, t = [], 0.0
    for c in clips:
        evs = []
        for sp in card.get("spots", []):
            if sp["clip"] != c["id"]:
                continue
            at = sp["at_s"] - c["in_s"]
            if 0 <= at <= c["dur_s"]:
                evs.append(SP._event(sp["class"], at, "authored", FPS, what=sp.get("what", sp["class"])))
        shots.append({"shot_id": c["id"], "segment_id": card["scene"], "start_s": round(t, 3), "dur_s": c["dur_s"],
                      "route": "ltx", "place": card["place"], "room": card.get("room", "outdoor"), "weather": "card",
                      "surface": "card", "audio_line_ids": [], "events": evs})
        t += c["dur_s"]
    bed = {"bed_id": f"BED_01_{card['place']}", "place": card["place"], "room": card.get("room", "outdoor"),
           "classes": list(card["bed"]), "start_s": 0.0, "end_s": round(t, 3), "shot_ids": [c["id"] for c in clips]}
    classes = sorted(set(card["bed"]) | {e["class"] for s in shots for e in s["events"]})
    for cls in classes:
        if cls not in SP.EVENT_CLASSES:
            raise ContractError(f"{cls}: not a class of sound_plan.EVENT_CLASSES")
    return {"schema": SP.SCHEMA, "episode_id": card["scene"], "era": card.get("era", "unknown"), "fps": FPS,
            "duration_s": round(t, 3), "shots": shots, "beds": [bed], "bridges": [], "music": [], "blocked_era_events": [],
            "classes": classes}


def join(card: dict, out_dir: Path, *, clip_root: Path, library_root: Path, pause_s: float, bed_under_lu: float,
         label: str) -> dict:
    if bed_under_lu < BED_UNDER_MIN_LU:
        raise ContractError(f"bed {bed_under_lu} LU under the voice: BP-52 asks at least {BED_UNDER_MIN_LU:g} LU")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tail, head = split_pause(pause_s)
    clips = []
    for c in card["clips"]:
        path = Path(clip_root) / c["file"]
        x = decode(path, RATE)
        x16 = decode(path, R.SR)
        spans = R.speech_spans(x16, R.SR) if c.get("speech", True) else []
        if c.get("line_window"):                     # the card's window of the line: what follows is a crowd, not the line
            w0, w1 = c["line_window"]
            spans = [(max(a, w0), min(b, w1)) for a, b in spans if b > w0 and a < w1]
        dur = len(x) / RATE
        keep = tuple(c["keep"]) if c.get("keep") else ((0.0, dur) if c.get("chained") else None)
        a, b = trims(spans, dur, head=head, tail=tail, lead_s=c.get("lead_s"), keep=keep)
        seg = x[int(a * RATE):int(b * RATE)].copy()
        sp = [(max(a, s0) - a, min(b, s1) - a) for s0, s1 in spans if s1 > a and s0 < b]
        gain_db = DIALOGUE_RMS_DBFS - _speech_level(seg, sp) if sp else float(c.get("gain_db", 0.0))
        seg = seg * np.float32(10 ** (gain_db / 20))
        if sp:
            seg = seg * between_lines_gain(len(seg), sp)
        seg = _fade_ends(seg, CLIP_FADE_S)
        clips.append({"id": c["id"], "file": c["file"], "in_s": a, "out_s": b, "dur_s": round(b - a, 4), "spans": sp,
                      "gain_db": round(gain_db, 2), "audio": seg, "line": c.get("line", c["id"]) if sp else None})
    plan = plan_of(card, clips)
    sources = SP.resolve(plan, library_root)
    ok, why = SP.shippable(sources, plan)
    if not ok:
        return {"schema": "scene_join_report/1", "label": label, "status": "NEEDS", "needs": SP.needs(sources), "why": why}
    n = int(round(plan["duration_s"] * RATE))
    dialogue = np.zeros(n, np.float32)
    t = 0.0
    for c in clips:
        i = int(round(t * RATE))
        m = min(len(c["audio"]), n - i)
        dialogue[i:i + m] += c["audio"][:m]
        t += c["dur_s"]
    peak = float(np.max(np.abs(dialogue)))
    if peak > 0.89:                                  # a war cry: keep the dialogue under full scale before the mix
        dialogue *= 0.89 / peak
    dpath = out_dir / f"dialogue_{card['scene']}.wav"
    _write_wav(dpath, dialogue)
    rep = ST.render(plan, sources, out_dir / "stems", library_root=library_root, narration=dpath, shippable=True)
    nar = read_stereo(out_dir / "stems" / "narration.wav")
    amb = read_stereo(out_dir / "stems" / "ambience.wav")
    sfx = read_stereo(out_dir / "stems" / "sfx.wav")
    # the variant's bed level: the bed (ambience + spots) under speech sits bed_under_lu under the speech (BP-52)
    tl = timeline(card, clips, plan)
    sp_mask = np.zeros(n, bool)
    for a, b in tl["speech_spans"]:
        sp_mask[int(a * RATE):int(b * RATE)] = True
    voice_l = _lufs_of(nar.mean(axis=1)[sp_mask])
    bg_l = _lufs_of((amb + sfx).mean(axis=1)[sp_mask])
    g = 10 ** ((voice_l - bed_under_lu - bg_l) / 20)
    mix = nar + (amb + sfx) * np.float32(g)
    pk = float(np.max(np.abs(mix)))
    if pk > 0.89:
        mix *= 0.89 / pk
    mpath = out_dir / "mix.wav"
    with wave.open(str(mpath), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    video = out_dir / f"{card['scene']}_{label}.mp4"
    _picture(clips, Path(clip_root), mpath, video, float(card.get("dissolve_s", 0.0)))
    write_json_atomic(out_dir / "timeline.json", {k: v for k, v in tl.items() if k != "speech_spans"})
    gate = R.measure(video, tl)
    write_json_atomic(out_dir / "sound_realism.json", gate)
    out = {"schema": "scene_join_report/1", "label": label, "status": "BUILT", "video": str(video),
           "pause_s": pause_s, "tail_s": tail, "head_s": head, "bed_under_voice_lu": bed_under_lu,
           "measured_bed_gain_db": round(R.db(g), 2), "voice_lufs_in_speech": voice_l, "bed_lufs_in_speech_before": bg_l,
           "clips": [{k: v for k, v in c.items() if k != "audio"} for c in clips], "sounds_used": rep["sounds_used"],
           "stems_gates": rep["gates"], "gate": {r["gate"]: r["status"] for r in gate["rows"]}, "verdict": gate["verdict"]}
    write_json_atomic(out_dir / "scene_join_report.json", out)
    return out


def timeline(card: dict, clips: list[dict], plan: dict) -> dict:
    cuts, lines, spans, pauses, t = [], [], [], [], 0.0
    for i, c in enumerate(clips):
        if i:
            cuts.append(round(t, 3))
        for a, b in c["spans"]:
            spans.append((round(t + a, 3), round(t + b, 3)))
        if c["spans"] and c["line"]:
            lines.append({"id": c["id"], "start_s": round(t + c["spans"][0][0] - 0.05, 3),
                          "end_s": round(t + c["spans"][-1][1] + 0.05, 3)})
        for p in card.get("intended_pauses", []):
            if p["clip"] == c["id"]:                     # a pause inside a clip the story wants (he sees the ridge, then orders)
                inner = [(b0, a1) for (_, b0), (a1, _) in zip(c["spans"], c["spans"][1:])]
                pauses += [[round(t + b0, 3), round(t + a1, 3)] for b0, a1 in inner if a1 - b0 > 0.6]
        t += c["dur_s"]
    talk = [l for l in lines]
    dlg = [[talk[0]["start_s"], talk[-1]["end_s"]]] if talk else []
    events = [{"at_s": round(s["start_s"] + e["at_s"], 3), "dur_s": 0.6, "class": e["class"]}
              for s in plan["shots"] for e in s["events"] if e["kind"] != "ambience"]
    return {"schema": "scene_timeline/1", "file": f"{card['scene']} (scene_join)", "cuts": cuts, "dialogue": dlg,
            "lines": lines, "intended_pauses": pauses, "events": events,
            "places": [{"start_s": 0.0, "end_s": plan["duration_s"], "place": card["place"]}], "speech_spans": spans}


def _picture(clips: list[dict], root: Path, audio: Path, out: Path, dissolve_s: float = 0.0) -> None:
    """Trim each clip's picture to its sound's frames, the new mix under it (AAC 48 kHz stereo). Hard cuts (BP-188), or with
    ``dissolve_s`` a picture dissolve centred on each cut, drawn from the frames just past the trims, so the sound's clock
    and every cut time stay where the timeline says (a chained close-up whose tail was trimmed: a cut would jump)."""
    h = dissolve_s / 2
    with tempfile.TemporaryDirectory() as d:
        parts = []
        for i, c in enumerate(clips):
            a = c["in_s"] - (h if i and dissolve_s else 0.0)
            b = c["out_s"] + (h if i + 1 < len(clips) and dissolve_s else 0.0)
            if a < 0:
                raise ContractError(f"{c['id']}: no frames before its trim for a {dissolve_s} s dissolve")
            p = Path(d) / f"p{i}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", str(root / c["file"]),
                            "-t", f"{b - a:.4f}", "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                            "-crf", "17", "-pix_fmt", "yuv420p", str(p)], check=True)
            parts.append(p)
        if dissolve_s and len(parts) > 1:
            inputs = [x for p in parts for x in ("-i", str(p))]
            chain, last, t = [], "[0:v]", 0.0
            for k in range(1, len(parts)):
                t += clips[k - 1]["dur_s"]
                tag = f"[v{k}]"
                chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={dissolve_s}:offset={t - h:.4f}{tag}")
                last = tag
            subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(audio), "-filter_complex", ";".join(chain),
                            "-map", last, "-map", f"{len(parts)}:a", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", str(RATE), "-shortest", str(out)],
                           check=True)
            return
        lst = Path(d) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", str(RATE),
                        "-shortest", str(out)], check=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scene_join")
    ap.add_argument("card")
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--library", default="assets/audio/library")
    ap.add_argument("--pause", type=float, default=0.5)
    ap.add_argument("--bed-under", type=float, default=BED_UNDER_DEFAULT)
    ap.add_argument("--label", default="")
    a = ap.parse_args(argv)
    card = json.loads(Path(a.card).read_text(encoding="utf-8"))
    if card.get("schema") != SCHEMA:
        raise ContractError(f"{a.card}: not a {SCHEMA} card")
    label = a.label or f"p{int(a.pause * 10):02d}_b{int(a.bed_under)}"
    rep = join(card, Path(a.out), clip_root=Path(a.root), library_root=Path(a.library), pause_s=a.pause,
               bed_under_lu=a.bed_under, label=label)
    print(json.dumps({k: rep[k] for k in rep if k not in ("clips", "sounds_used", "stems_gates")}, indent=1))
    return 0 if rep["status"] == "BUILT" and rep["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
