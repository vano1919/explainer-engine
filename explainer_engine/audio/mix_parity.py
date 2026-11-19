"""Parity run of the mix chain on the old 1914 minute (W6, docs/MIX_CHAIN.md): the first ``--seconds`` of an episode's
``sound_plan.json`` rendered through ``audio/stems.render`` (so through ``audio/mix_chain``) with the episode's own read and the sound
library, then measured and judged by ``validators/mix`` (``mix_chain.verify``). This is a test of the chain, not a final mix: it is a
preview render (a take whose file is not in the library stays silent and is listed, D-136) and nothing here costs money.

    python -m explainer_engine.audio.mix_parity --plan sound_plan.json --narration narration.wav --library <root> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

from explainer_engine.audio import mix_chain as MC
from explainer_engine.audio import stems
from explainer_engine.core.store import write_json_atomic
from explainer_engine.episode import sound_plan as SP


def crop_plan(plan: dict, seconds: float) -> dict:
    """The plan limited to ``[0, seconds)``: whole shots that start before the cut, the beds and music clipped to it."""
    p = json.loads(json.dumps(plan))
    p["shots"] = [s for s in p["shots"] if s["start_s"] < seconds]
    for s in p["shots"]:
        s["dur_s"] = round(min(s["dur_s"], seconds - s["start_s"]), 3)
    ids = {s["shot_id"] for s in p["shots"]}
    for key in ("beds", "music"):
        p[key] = [dict(b, end_s=min(b["end_s"], seconds)) for b in p.get(key, []) if b["start_s"] < seconds]
    for b in p["beds"]:
        b["shot_ids"] = [i for i in b.get("shot_ids", []) if i in ids]
    p["bridges"] = [b for b in p.get("bridges", []) if all(b.get(k) in (None, *ids) for k in ("from_shot", "to_shot"))]
    p["duration_s"] = seconds
    return p


def crop_wav(src: Path, dst: Path, seconds: float) -> Path:
    with wave.open(str(src)) as w:
        ch, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(int(seconds * rate))
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(ch), o.setsampwidth(width), o.setframerate(rate)
        o.writeframes(raw)
    return dst


def run(plan_path: Path, narration: Path, library: Path, out: Path, seconds: float = 60.0) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    plan = crop_plan(json.loads(Path(plan_path).read_text(encoding="utf-8")), seconds)
    sources = SP.resolve(plan, library)
    nar = crop_wav(narration, out / "narration_input.wav", seconds)
    rep = stems.render(plan, sources, out / "stems", library_root=library, narration=nar, shippable=False)
    sheet = json.loads((out / "stems" / "cue_sheet.json").read_text(encoding="utf-8"))
    verdict = MC.verify(out / "stems", plan, rep["events_placed"], sheet["rows"])
    # a phone-playable file: the mix as AAC in an m4a (what the delivery codec makes of it)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out / "stems" / "mix.wav"), "-c:a", "aac", "-b:a", "192k",
                    str(out / "mix_parity_60s.m4a")], check=True)
    stem_lufs = {}
    for name in ("narration", "music", "ambience", "sfx"):
        with wave.open(str(out / "stems" / f"{name}.wav")) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32).reshape(-1, w.getnchannels()) / 32768
        v = MC.integrated_lufs(x)
        stem_lufs[name] = None if v == float("-inf") else round(v, 1)
    # effect loudness while an effect plays: the sfx stem over the windows of its placed events
    ev = []
    for e in rep["events_placed"]:
        if e.get("layer") in ("foley", "spot", "transition") and e["cue_id"] not in rep["silent_rows"]:
            ev.append((e["at_s"], min(e["end_s"], e["at_s"] + 3.0)))
    record_effects = {"events_played": len(ev), "events_silent": len(rep["silent_rows"])}
    record = {"stem_lufs": stem_lufs, "effects": record_effects, "schema": "mix_parity/1", "seconds": seconds, "plan": str(plan_path), "preview_not_final": True,
              "silent_rows": rep["silent_rows"], "placeholders": rep["placeholders"], "mix_chain": rep["mix_chain"],
              "verify": verdict, "levels": rep["levels"]["groups"], "sounds_used": len(rep["sounds_used"])}
    write_json_atomic(out / "mix_parity_report.json", record)
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True), ap.add_argument("--narration", required=True)
    ap.add_argument("--library", required=True), ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=60.0)
    a = ap.parse_args()
    r = run(Path(a.plan), Path(a.narration), Path(a.library), Path(a.out), a.seconds)
    print(json.dumps({"measured": r["verify"]["measured"], "after_aac": r["verify"]["after_aac"],
                      "verdict": r["verify"]["verdict"]["status"] if isinstance(r["verify"]["verdict"], dict) else r["verify"]["verdict"],
                      "silent_rows": len(r["silent_rows"])}, indent=1))
    for row in r["verify"]["rows"]:
        print(row["status"], row["gate"], "-", row["detail"][:140])


if __name__ == "__main__":
    main()
