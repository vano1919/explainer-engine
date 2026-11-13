"""An LTX scene file from an episode's script (VL-10, docs/VIDEO_LANE.md): the plan the creator says yes to before one paid
launch (``training/pods/ltx/scene_run``), written from the shots' edit plans instead of by hand.

The file (``ltx_scene_test/3``) carries, for every video shot of the scene in cut order:

* ``seconds`` from the line (``videolane.plan.clip_seconds``, VL-06), never a fixed 10 s;
* a coverage or insert shot: its own pinned start picture (the episode's pictures stage);
* a continuation shot: no picture, ``continue_frame`` from its edit plan (default ``best_tail``): the worker picks the
  sharpest, stillest frame of the clip before's tail, crops it when asked, and starts this clip from it (VL-05);
* the one line (speaker, text) and the motion prompt of the shot.

The prompt LTX receives is COMPOSED here, never copied (Fable audit FA-02, P3): the script's ``video_prompt.motion_prompt``
(which the lint ``KP-V4-DIALOGUE-LEAK`` keeps free of dialogue) + for a clip-spoken shot ``<Name> says in <voice
description>: "<line>"`` (the voice from ``world_bible.characters[].voice_description``, written by the voice-caster) + a
sound clause from the shot's authored ``sound_events`` + for a narrated or silent shot the fixed ``Nobody speaks.``. This
function is the one place a line meets a prompt; the parts are written into the row (``prompt_parts``) so the audit sees
what LTX was told. A clip-spoken shot whose speaker has no voice description is listed in ``voice_missing`` and the scene
is refused by ``storyboard_problems`` (no paid clip of an unknown voice). Not proven until the first paid sample: that LTX
speaks the composed line in the described voice.

A narrated video shot is sized from the read's measured length when ``audio/timing.json`` exists (FA-15; ``basis``), else
from the plan.

It is written only from a FRESH storyboard record whose verdict is not FAIL (``videolane/storyboard``), and pins that
record's sha256; ``scene_run.job_spec`` refuses a /3 scene whose pin no longer matches. ``budget`` and ``ledger`` are the
creator's numbers for this scene (OR-23): without them the file is written as a draft (``draft: true``) that ``job_spec``
refuses.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import gates as G

SCHEMA = "ltx_scene_test/3"
NOBODY_SPEAKS = "Nobody speaks."


def _cast(script: dict) -> dict:
    return {c.get("character_id"): c for c in (script.get("world_bible") or {}).get("characters", [])}


def compose_prompt(script: dict, shot: dict) -> dict:
    """FA-02: ``{"prompt", "parts", "spoken", "voice_missing"}`` for one video shot (see the module text)."""
    from explainer_engine.episode import sound_plan as SPL
    from explainer_engine.videolane import plan as P
    motion = str((shot.get("video_prompt") or {}).get("motion_prompt") or "").strip()
    lines = {ln["line_id"]: ln for ln in script.get("audio_lines", [])}
    cast = _cast(script)
    parts = {"motion": motion}
    spoken, missing = [], []
    for lid in shot.get("audio_line_ids") or []:
        ln = lines.get(lid) or {}
        if ln.get("speaker_type") != "character":
            continue
        c = cast.get(ln.get("speaker_id")) or {}
        name = c.get("name") or str(ln.get("speaker_id") or "Someone")
        voice = str(c.get("voice_description") or "").strip()
        if not voice:
            missing.append(str(ln.get("speaker_id")))
        text = str(ln.get("text") or "").strip().replace('"', "'")
        spoken.append(f'{name} says in {voice}: "{text}"' if voice else f'{name} says: "{text}"')
    if spoken:
        parts["speech"] = " ".join(spoken)
    sounds = []
    for e in shot.get("sound_events") or []:
        cls = e.get("class") or SPL._class_of(e.get("what", "")) or e.get("what")
        word = str(cls).replace("_", " ")
        if word not in sounds:
            sounds.append(word)
    if sounds:
        parts["sound"] = "Sound: " + ", ".join(sounds) + "."
    if not spoken:
        parts["no_speech"] = NOBODY_SPEAKS
    prompt = " ".join(p for p in (parts.get("motion"), parts.get("speech"), parts.get("sound"), parts.get("no_speech")) if p)
    return {"prompt": prompt, "parts": parts, "spoken": bool(spoken), "voice_missing": missing,
            "clip_spoken": shot.get("shot_id") in P.clip_spoken(script)}


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(root: Path, script: dict, scene_id: str, out: Path, *, budget: dict | None = None, ledger: dict | None = None,
          max_s: float = 10.0, seed_base: int = 7100, asked: str | None = None) -> dict:
    from explainer_engine.videolane import plan as P
    from explainer_engine.videolane import storyboard as SB
    root = Path(root)
    rec_p = root / "production" / "storyboard" / f"{scene_id}.json"
    if not rec_p.is_file():
        raise ContractError(f"no storyboard for {scene_id}: run videolane.storyboard first (VL-10)")
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    if rec["verdict"]["status"] == G.FAIL:
        raise ContractError(f"the storyboard of {scene_id} FAILs ({', '.join(rec['verdict']['failed'])}): no paid scene")
    pics = json.loads((root / "production" / "pictures.json").read_text(encoding="utf-8"))["pictures"]
    stale = SB.fresh(root, rec, script, pics)
    if stale:
        raise ContractError(f"the storyboard of {scene_id} is stale: {'; '.join(stale)}")
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    lines = {ln["line_id"]: ln for ln in script.get("audio_lines", [])}
    from explainer_engine.episode import timing as ETM
    timed = (ETM.load(root) or {}).get("shots", {})
    shots, manifest, voice_missing = [], {}, []
    for k, sid in enumerate(rec["shots"]):
        s = by[sid]
        if not P.is_video(s):
            continue
        ep = s.get("edit_plan") or {}
        t_ = timed.get(sid)
        measured = float(t_["seconds"]) if t_ and t_.get("seconds") is not None else None
        secs = P.clip_seconds(script, s, max_s, measured_s=measured)
        if secs["over"]:
            raise ContractError(f"{sid}: its line needs {secs['needed_s']} s, the model makes {max_s} s (VL-06): split it")
        comp = compose_prompt(script, s)
        voice_missing += [f"{sid}: {who}" for who in comp["voice_missing"]]
        row = {"shot_id": sid, "seconds": secs["seconds"], "seconds_basis": secs["basis"], "seed": seed_base + k,
               "motion_prompt": comp["prompt"], "prompt_parts": comp["parts"],
               "continuity_mode": ep.get("continuity_mode")}
        ids = s.get("audio_line_ids") or []
        if ids:
            ln = lines.get(ids[0]) or {}
            row["line"] = {"speaker": ln.get("speaker_id"), "text": ln.get("text")}
        if ep.get("continuity_mode") == "continuation" and shots:
            row["continue_frame"] = dict({"pick": "best_tail", "window_s": 0.75}, **(ep.get("continue_frame") or {}))
        else:
            key = f"{sid}_start"
            if key not in pics:
                raise ContractError(f"{sid}: no start picture {key} (G5)")
            p = root / pics[key]["file"]
            manifest[key] = {"path": str(p.resolve()), "sha256": _sha(p)}
            row["picture"] = key
        shots.append(row)
    if not shots:
        raise ContractError(f"{scene_id}: no video shot in the scene")
    out = Path(out)
    man_p = out.with_name(out.stem + ".pictures.json")
    write_json_atomic(man_p, {"shots": manifest})
    scene = {"schema": SCHEMA, "id": scene_id, "episode": str(root), "asked": asked,
             "method": "video lane VL-01..VL-13 (D-137): one line per clip, seconds from the line, continuations from the "
                       "best tail frame, coverage from its own picture",
             "storyboard": {"record": str(rec_p.resolve()), "sha256": _sha(rec_p), "verdict": rec["verdict"]["status"]},
             "pictures": {"manifest": str(man_p.resolve())}, "shots": shots, "draft": not (budget and ledger),
             "prompt_composer": "videolane.scene.compose_prompt (FA-02)", "voice_missing": voice_missing}
    if budget:
        scene["budget"] = budget
    if ledger:
        scene["ledger"] = ledger
    write_json_atomic(out, scene)
    return scene


def storyboard_problems(scene: dict) -> list[str]:
    """``scene_run.job_spec``'s check of a /3 scene: not a draft, the storyboard pin still the record on disk, not FAIL."""
    if scene.get("schema") != SCHEMA:
        return []
    why = []
    if scene.get("draft"):
        why.append("a draft scene (no budget or ledger from the creator, OR-23)")
    if scene.get("voice_missing"):
        why.append(f"spoken shot(s) whose speaker has no voice description (FA-02): {', '.join(scene['voice_missing'][:6])}")
    sb = scene.get("storyboard") or {}
    p = Path(sb.get("record") or "__none__")
    if not p.is_file():
        why.append("its storyboard record is missing")
    elif _sha(p) != sb.get("sha256"):
        why.append("its storyboard changed after the scene was written: write the scene again")
    elif json.loads(p.read_text(encoding="utf-8"))["verdict"]["status"] == G.FAIL:
        why.append("its storyboard FAILs")
    return why
