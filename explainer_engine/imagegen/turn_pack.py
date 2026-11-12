"""Pictures through the Gemini chat (v4.3 plan sections 0.6, 0.7, P3; rules GC-01..GC-17 in docs/GEMINI_CONSISTENCY_RULES.md).

The creator makes the episode's pictures in the Gemini chat's built-in image tool, inside his subscription, free, 6-12 per
chat session at the tool's native 16:9 size, one prompt per picture (GC-17). The engine cannot call that tool, so this module does the two halves around it:

- ``export``: from the episode-first script (``story/production_script.json``, schema_version 4.0.0) and the episode's look
  (``episode.json`` -> ``look``), write **turn packs**: ``planning/turn_packs/pack_NN.json`` (machine) and ``pack_NN.md``
  (paste-ready: one block per picture with its exact prompt, the reference files to attach IN ORDER and the file name to
  save it as). Image 1 of every picture is the look's style picture (GC-01, the preset ``crossworld_main_style_v1``);
  anchors come first; a scene shot attaches only its people and its place (GC-02).
- ``intake``: read the files he drops (by name), gate each one (GC-12: decodes, 16:9, native size or more, no letterbox,
  no duplicate; GC-07 lettering and GC-13 identity where a measurement exists, else ``NOT_RUN``), append every file to the
  ledger (``planning/picture_ledger.jsonl``, sha256 + gates + pack), draw a contact sheet and list what must be re-made.
- ``promote``: an accepted chat picture is a ``draft``; the free local 2x upscale (Real-ESRGAN class, GC-14) writes its
  working master ``assets/generated/masters/<name>.png`` at ``image_min_long_side`` (2752) or more. Without an installed
  upscaler the row is ``NOT_RUN`` and the picture stays a draft; it is never resized by a plain filter and called a master.
- ``remake_list``: the GC-14 list of close-up and medium-close-up hero shots whose finished 1080p frame FAILed the
  sharpness/face-detail gate, priced at the 2K batch rate. It is a request to the creator, never a run.

Nothing here is paid. The paid API route (``imagegen/gemini.py``) is off by default and is not called from this module.

CLI::

    python -m explainer_engine.imagegen.turn_pack export episodes/ep_toba [--size 6] [--only anchors|shots|all]
    python -m explainer_engine.imagegen.turn_pack intake episodes/ep_toba [--drop <folder>]
    python -m explainer_engine.imagegen.turn_pack promote episodes/ep_toba
    python -m explainer_engine.imagegen.turn_pack status episodes/ep_toba
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic, write_text_atomic

SCHEMA = "turn_pack/1"
MAX_REFERENCES = 6            # references attached to one chat request (GC-02); the tool's limit is not published, 6 is ours
DEFAULT_TURN = 6              # pictures per chat turn (the creator: 6-12 per turn)
MAX_TURN = 12
NATIVE_CHAT_SIZE = (1376, 768)  # the chat tool's native 16:9 output (the creator, 2026-11-12 09:38 UTC)
REMAKE_MODEL, REMAKE_SIZE = "gemini-nano-banana-2.1", "2K"   # GC-14, plan 0.7: the only paid picture, batch tier
REMAKE_SHOT_SIZES = ("close_up", "medium_close_up", "extreme_close_up")
UPSCALER_ENV = "EE_UPSCALER"   # path to a realesrgan-ncnn-vulkan class binary (``-i in -o out -s 2``); none -> NOT_RUN
ASPECT = 16 / 9
ASPECT_TOL = 0.01             # GC-12: 16:9 within 1 %
MAX_COMMAS = 9                # GC-06: more commas than this reads as a tag list (REVIEW)
DUP_HASH_DIST = 4             # GC-12: perceptual-hash distance at or under which two pictures are the same picture
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
KEEP_CLAUSE = ("Keep the exact faces, hair, costumes, props and designs of the attached reference images; "
               "only the pose, the action, the camera and the light change.")
ANCHOR_CLAUSE_CHAR = ("Character reference sheet on a plain neutral grey background, no props except the ones named, even soft "
                      "light: three views side by side (front, three-quarter, profile), full body, the same person in each view.")
ANCHOR_CLAUSE_PLACE = "Establishing view of the place, no people, the light of its usual time of day."
TEXT_WORDS = re.compile(r"\b(text|caption|label(l?ed|s)?|lettering|letters|sign(post|board)?s?|plaque|inscription|"
                        r"writing|written|title card|logo|watermark|numbers? on)\b", re.I)
NEGATED_TEXT = re.compile(r"\bno (text|lettering|letters|labels|signs|writing|watermark|logos?)\b", re.I)
ROUND_FACE_WORDS = re.compile(r"\b(expressive eyes|big eyes|round face|chubby|cute|smooth 3d sculpted shading|"
                              r"smooth sculpted|pixar|disney|button nose|baby[- ]faced|3d animat\w*|3d cartoon|cartoon|animated character)\b", re.I)
SECOND_ACTION = re.compile(r"\b(then|after that|and then|while also)\b", re.I)
NEGATED = re.compile(r"\b(never|no|not|without)\b[^,.;]*", re.I)   # a refused word inside "never a cartoon nose" is not asked for
STYLE_REF_CLAUSE = "Use image 1 only as the visual style; do not copy its people, their pose or its place."   # GC-01
PRESETS = Path(__file__).resolve().parents[2] / "config" / "visual_style_presets.json"
REPO_ROOT = Path(__file__).resolve().parents[2]
PICTURES_PER_DAY = 25         # GC-19: Flash pictures a day in the creator's chat, measured in reference round 1 (2026-11-12)


def _affirmative(text: str) -> str:
    return NEGATED.sub("", text or "")


def preset(pid: str) -> dict:
    """One style preset of ``config/visual_style_presets.json`` (the one home of the channel's look)."""
    doc = json.loads(PRESETS.read_text(encoding="utf-8"))
    pre = (doc.get("presets") or {}).get(pid)
    if not pre:
        raise ContractError(f"no style preset {pid!r} in config/visual_style_presets.json")
    return pre


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# --- the episode's inputs ----------------------------------------------------------------------------------------------
def load(root: Path) -> tuple[dict, dict]:
    """(episode.json, script) of an episode folder; the script must be the episode-first format (4.0.0)."""
    root = Path(root)
    man = json.loads((root / "episode.json").read_text(encoding="utf-8"))
    script = json.loads((root / "story" / "production_script.json").read_text(encoding="utf-8"))
    if script.get("schema_version") != "4.0.0":
        raise ContractError(f"{root}: turn packs need the episode-first script (schema_version 4.0.0)")
    if script.get("episode_id") != man["episode_id"]:
        raise ContractError(f"{root}: the script's episode id {script.get('episode_id')!r} is not {man['episode_id']!r} (EP-01)")
    return man, script


def sizes_of(man: dict) -> tuple[tuple[int, int], int]:
    """(intake floor (w, h), working-master long side) from episode.json (EP-02): the chat tool's native size and the
    upscaled master's long side (never under 2048)."""
    native = int(man.get("image_native_min_long_side") or NATIVE_CHAT_SIZE[0])
    master = int(man.get("image_min_long_side") or 2 * native)
    if master < 2048:
        raise ContractError(f"episode.json image_min_long_side {master} is under 2048 (EP-02)")
    return (native, int(round(native * 9 / 16 / 2)) * 2 if native != NATIVE_CHAT_SIZE[0] else NATIVE_CHAT_SIZE[1]), master


def look_of(man: dict) -> dict:
    """The episode's look: ``style_sentence`` (environment + materials, GC-03), ``face_sentence`` (GC-11), and the style
    references attached as image 1 of every picture (GC-01) with the words the chat must never read (GC-18). ``look.preset``
    takes them from ``config/visual_style_presets.json``; a field written in the episode wins."""
    look = dict(man.get("look") or {})
    if look.get("preset"):
        pre = preset(look["preset"])
        for k in ("style_sentence", "face_sentence", "never_words", "negative", "style_references", "pictures_per_day"):
            if look.get(k) in (None, "", []):
                look[k] = pre.get(k)
    for k in ("style_sentence", "face_sentence"):
        if not str(look.get(k) or "").strip():
            raise ContractError(f"episode.json look.{k} is missing (GC-03, GC-11)")
    both = _affirmative(look["face_sentence"] + " " + look["style_sentence"])
    if ROUND_FACE_WORDS.search(both):
        raise ContractError(f"the look asks for round, modern-cartoon faces ({ROUND_FACE_WORDS.search(both).group(0)!r}), "
                            "rejected by the creator on 2026-11-12 (GC-11)")
    never = never_hits(look, look["style_sentence"] + " " + look["face_sentence"])
    if never:
        raise ContractError(f"the look itself uses the words the chat must never read: {never} (GC-18)")
    for r in look.get("style_references") or []:
        if not (isinstance(r, dict) and r.get("file") and isinstance(r.get("sha256"), str) and len(r["sha256"]) == 64):
            raise ContractError("a style reference needs its file and sha256 (GC-01)")
    return look


def never_hits(look: dict, text: str) -> list[str]:
    """The look's never-words that ``text`` asks for (outside a negation): Gemini redraws such a request as a photograph."""
    words = [w for w in (look.get("never_words") or []) if w]
    if not words:
        return []
    rx = re.compile(r"\b(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b", re.I)
    return sorted({m.group(0).lower() for m in rx.finditer(_affirmative(text))})


def style_ref_path(ref: dict) -> str:
    """Where a style reference sits inside the episode folder (copied there from the repo by ``export``)."""
    return f"assets/reference/style/{Path(ref['file']).name}"


def style_refs(look: dict) -> list[str]:
    return [style_ref_path(r) for r in look.get("style_references") or []]


def registry(script: dict) -> dict:
    """id -> the verbatim appearance text of every character, place and prop (GC-04, HI-01)."""
    wb = script.get("world_bible") or {}
    reg = {}
    for c in wb.get("characters", []):
        reg[c["character_id"]] = {"kind": "character", "name": c["name"], "text": c["fixed_appearance_prompt"]}
    for p in wb.get("locations", []):
        reg[p["location_id"]] = {"kind": "location", "name": p["name"], "text": p["fixed_environment_prompt"],
                                 "light": p.get("lighting_palette", "")}
    for p in wb.get("props", []):
        reg[p["prop_id"]] = {"kind": "prop", "name": p["name"], "text": p["fixed_prop_prompt"]}
    return reg


def anchor_path(kind: str, rid: str) -> str:
    folder = {"character": "characters", "location": "locations", "prop": "props"}[kind]
    return f"assets/reference/{folder}/{rid}.png"


def frame_path(shot_id: str, which: str) -> str:
    return f"assets/generated/images/{shot_id}_{which}.png"


# --- prompts -----------------------------------------------------------------------------------------------------------
def _style(look: dict) -> str:
    """The style sentence, and the style-reference clause when the look attaches its style picture as image 1 (GC-01)."""
    return f"{look['style_sentence']} {STYLE_REF_CLAUSE}" if look.get("style_references") else look["style_sentence"]


def anchor_prompt(look: dict, rid: str, entry: dict) -> str:
    """GC-01/03/11: style sentence (and the style-reference clause), face sentence (people only), the registry text
    verbatim, the anchor clause. An anchor attaches nothing but the look's style reference."""
    st = _style(look)
    if entry["kind"] == "character":
        return f"{st} {look['face_sentence']} {entry['name']}: {entry['text']}. {ANCHOR_CLAUSE_CHAR} No text."
    if entry["kind"] == "location":
        light = f" Light: {entry['light']}." if entry.get("light") else ""
        return f"{st} {entry['name']}: {entry['text']}.{light} {ANCHOR_CLAUSE_PLACE} No text."
    return f"{st} Object reference: {entry['name']}: {entry['text']}, on a plain neutral grey background. No text."


def shot_prompt(look: dict, shot: dict, reg: dict, which: str) -> str:
    """GC-03/04/06: style sentence, face sentence, keep clause, one moment in scene language, the heroes' verbatim texts."""
    state = shot["action_end_state"] if which == "end" else shot["action_start_state"]
    comp = shot.get("screen_composition") or {}
    cam = shot.get("camera_spec") or {}
    size = str(cam.get("shot_size", "")).replace("_", " ")
    people = [f"{reg[c]['name']}: {reg[c]['text']}" for c in shot.get("character_ids", []) if c in reg]
    place = reg.get(shot.get("location_id"), {})
    parts = [_style(look)]
    if people:
        parts.append(look["face_sentence"])
    parts.append(KEEP_CLAUSE)
    parts.append(f"A {size} shot. {state.rstrip('.')}.")
    if place:
        parts.append(f"The place is {place['name']}, as in its reference image.")
    if comp.get("background"):
        parts.append(f"Behind: {comp['background'].rstrip('.')}.")
    parts.append(f"Light: {shot.get('lighting_and_time', '').rstrip('.')}.")
    for p in people:
        parts.append(p.rstrip(".") + ".")
    parts.append("No text, no letters, no signs.")
    return " ".join(x for x in parts if x.strip(" ."))


def check_prompt(prompt: str, item: dict, reg: dict, look: dict) -> list[dict]:
    """GC rows for one prompt (empty = clean)."""
    out = []
    if not prompt.startswith(look["style_sentence"]):
        out.append({"rule": "GC-03", "severity": "FAIL", "detail": "the prompt does not open with the look's style sentence"})
    for cid in item.get("people", []):
        if cid in reg and reg[cid]["text"] not in prompt:
            out.append({"rule": "GC-04", "severity": "FAIL", "detail": f"{cid}'s registry text is not in the prompt verbatim"})
    if item["kind"] == "shot" and KEEP_CLAUSE not in prompt:
        out.append({"rule": "GC-03", "severity": "FAIL", "detail": "a scene prompt lacks the keep-the-references clause"})
    if item["kind"] != "shot" and KEEP_CLAUSE in prompt:
        out.append({"rule": "GC-03", "severity": "FAIL", "detail": "an anchor prompt carries the keep clause (it has no refs)"})
    asks_text = [m.group(0) for m in TEXT_WORDS.finditer(NEGATED_TEXT.sub("", prompt))]
    if asks_text:
        out.append({"rule": "GC-07", "severity": "FAIL", "detail": f"the prompt asks for lettering: {asks_text[:3]}"})
    if ROUND_FACE_WORDS.search(_affirmative(prompt)):
        out.append({"rule": "GC-11", "severity": "FAIL", "detail": f"round, modern-cartoon face words: {ROUND_FACE_WORDS.search(_affirmative(prompt)).group(0)!r}"})
    never = never_hits(look, prompt)
    if never:
        out.append({"rule": "GC-18", "severity": "FAIL", "detail": f"words the chat redraws as a photograph: {never}"})
    if look.get("style_references") and STYLE_REF_CLAUSE not in prompt:
        out.append({"rule": "GC-01", "severity": "FAIL", "detail": "the style reference is attached but the prompt lacks its clause"})
    moment = item.get("moment", "")
    if moment.count(",") > MAX_COMMAS or len(SECOND_ACTION.findall(moment)) >= 1:
        out.append({"rule": "GC-06", "severity": "REVIEW", "detail": "the moment reads as a list or as two actions"})
    return out


# --- the queue ---------------------------------------------------------------------------------------------------------
def build_queue(man: dict, script: dict, only: str = "all") -> list[dict]:
    """Every picture the episode needs, in making order: character anchors, place anchors, prop anchors, then each scene's
    start frames, then end frames (GC-01, GC-09). A shot routed to ``map_action`` gets no picture (Python draws it)."""
    look = look_of(man)
    reg = registry(script)
    srefs = style_refs(look)
    used = {"character": set(), "location": set(), "prop": set()}
    shots = [s for s in script.get("shots", []) if s.get("route") != "map_action"
             and s.get("visual_type") != "map_visualization"]
    for s in shots:
        used["character"].update(s.get("character_ids", []))
        if s.get("location_id"):
            used["location"].add(s["location_id"])
        used["prop"].update(s.get("prop_ids", []))
    q = []
    if only in ("all", "anchors"):
        for kind in ("character", "location", "prop"):
            for rid in sorted(used[kind]):
                if rid not in reg:
                    raise ContractError(f"{rid} is used by a shot but has no world_bible entry (GC-02)")
                q.append({"id": rid, "kind": kind, "group": f"anchors:{kind}", "people": [rid] if kind == "character" else [],
                          "target": anchor_path(kind, rid), "references": list(srefs), "prompt": anchor_prompt(look, rid, reg[rid]),
                          "moment": reg[rid]["text"]})
    if only in ("all", "shots"):
        ends = []
        for s in shots:
            kp = s.get("keyframe_plan") or {}
            refs = [anchor_path("character", c) for c in s.get("character_ids", [])]
            if s.get("location_id"):
                refs.append(anchor_path("location", s["location_id"]))
            refs += [anchor_path("prop", p) for p in s.get("prop_ids", [])]
            if len(refs) + len(srefs) > MAX_REFERENCES:
                raise ContractError(f"{s['shot_id']} needs {len(refs) + len(srefs)} references, more than {MAX_REFERENCES} "
                                    "(GC-02): split the shot")
            base = {"kind": "shot", "shot_id": s["shot_id"], "segment_id": s["segment_id"], "group": f"scene:{s['segment_id']}",
                    "people": list(s.get("character_ids", [])), "place": s.get("location_id")}
            if kp.get("needs_start_frame", True):
                q.append(dict(base, id=f"{s['shot_id']}_start", which="start", target=frame_path(s["shot_id"], "start"),
                              references=srefs + refs, prompt=shot_prompt(look, s, reg, "start"), moment=s["action_start_state"]))
            if kp.get("needs_end_frame"):
                start_ref = [frame_path(s["shot_id"], "start")] if kp.get("needs_start_frame", True) else []
                ends.append(dict(base, id=f"{s['shot_id']}_end", which="end", target=frame_path(s["shot_id"], "end"),
                                 references=srefs + start_ref + refs[:MAX_REFERENCES - len(start_ref) - len(srefs)],
                                 prompt=shot_prompt(look, s, reg, "end"), moment=s["action_end_state"],
                                 after=f"{s['shot_id']}_start"))
        q += ends
    for it in q:
        it["checks"] = check_prompt(it["prompt"], it, reg, look)
    return q


def scene_picture_ids(script: dict) -> list[str]:
    """The scene pictures a script needs (start frames, end frames), without the look: for counts in the gate audit."""
    out = []
    for s in script.get("shots", []):
        if s.get("route") == "map_action" or s.get("visual_type") == "map_visualization":
            continue
        kp = s.get("keyframe_plan") or {}
        if kp.get("needs_start_frame", True):
            out.append(f"{s['shot_id']}_start")
        if kp.get("needs_end_frame"):
            out.append(f"{s['shot_id']}_end")
    return out


def plan_turns(queue: list[dict], size: int = DEFAULT_TURN) -> list[list[dict]]:
    """Split the queue into chat turns of at most ``size`` (GC-08: one group per turn; an end frame never shares a turn with
    its own start frame, GC-09)."""
    if not 1 <= size <= MAX_TURN:
        raise ContractError(f"a turn holds 1..{MAX_TURN} pictures, not {size}")
    turns: list[list[dict]] = []
    cur: list[dict] = []
    for it in queue:
        clash = it.get("after") and any(x["id"] == it["after"] for x in cur)
        if cur and (len(cur) >= size or cur[-1]["group"] != it["group"] or clash):
            turns.append(cur)
            cur = []
        cur.append(it)
    if cur:
        turns.append(cur)
    return turns


def instruction_block(man: dict, pack_no: int, turn: list[dict], day: int | None = None, per_day: int | None = None) -> str:
    """The paste-ready text for one chat turn (GC-10: one episode, one chat; GC-02 attach order; GC-19 the day it fits in)."""
    when = f" — day {day} (about {per_day} pictures a day in the chat, GC-19)" if day else ""
    lines = [f"# Turn pack {pack_no:02d} — episode {man['episode_id']} ({len(turn)} pictures){when}", "",
             f"Make these in THE ONE Gemini chat of episode `{man['episode_id']}` (GC-10), with the Flash image model, never Argon/Pro (GC-16). Every picture 16:9.",
             "Send each prompt block below as its OWN message (one prompt draws one picture; never send these notes, GC-17).",
             "Attach the listed reference images IN THE ORDER given, and nothing else (image 1 is the look's style picture when it has one; GC-01/02).",
             "Save each result under the file name given and drop them into the episode's folder.", ""]
    for k, it in enumerate(turn, 1):
        lines.append(f"## {k}. `{it['id']}` -> save as `{it['target']}`")
        if it["references"]:
            lines.append("Attach, in this order: " + ", ".join(f"`{r}`" for r in it["references"]))
        else:
            lines.append("Attach: nothing (an anchor is made from text only, GC-01).")
        lines += ["", "```", it["prompt"], "```", ""]
    return "\n".join(lines)


def export(root: Path, size: int = DEFAULT_TURN, only: str = "all") -> dict:
    """Write the turn packs of everything not yet accepted (the ledger's ``accepted`` rows are skipped)."""
    root = Path(root)
    man, script = load(root)
    queue = build_queue(man, script, only)
    fails = [(it["id"], c) for it in queue for c in it["checks"] if c["severity"] == "FAIL"]
    if fails:
        raise ContractError(f"{len(fails)} prompt rule(s) FAIL, no pack written: {fails[:5]}")
    look = look_of(man)
    srefs = style_refs(look)
    for ref in look.get("style_references") or []:      # GC-01: the style picture, copied in from the repo, held to its sha256
        dst = root / style_ref_path(ref)
        if not dst.is_file():
            src = REPO_ROOT / ref["file"]
            if not src.is_file():
                raise ContractError(f"the style reference {ref['file']} is missing (GC-01)")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        if sha256(dst) != ref["sha256"]:
            raise ContractError(f"{style_ref_path(ref)} is not the approved style picture (sha256, GC-01)")
    for it in queue:   # GC-01: image 1 is the look's style picture (or nothing); then only the episode's anchors or own start
        own = {frame_path(it["shot_id"], "start")} if it.get("shot_id") else set()
        if it["references"][:len(srefs)] != srefs:
            raise ContractError(f"{it['id']}: image 1 must be the look's style reference (GC-01)")
        rest = it["references"][len(srefs):]
        if it["kind"] != "shot" and rest:
            raise ContractError(f"{it['id']}: an anchor attaches only the style reference, no other picture (GC-01)")
        foreign = [r for r in rest if not re.match(r"assets/reference/(characters|locations|props)/", r) and r not in own]
        if foreign:
            raise ContractError(f"{it['id']} attaches {foreign}: only the episode's anchors or its own start frame (GC-01)")
    accepted = {r["id"] for r in ledger_rows(root) if r.get("status") == "accepted"}
    todo = [it for it in queue if it["id"] not in accepted]
    have_refs = accepted | {it["id"] for it in todo}
    for it in todo:
        for r in it["references"][len(srefs):]:
            rid = Path(r).stem
            if rid not in have_refs:
                raise ContractError(f"{it['id']} attaches {r}, which no pack makes and the ledger lacks (GC-02)")
    turns = plan_turns(todo, size)
    per_day = int(man.get("chat_pictures_per_day") or look.get("pictures_per_day") or PICTURES_PER_DAY)
    out_dir = root / "planning" / "turn_packs"
    out_dir.mkdir(parents=True, exist_ok=True)
    start = 1 + max([int(p.stem.split("_")[1]) for p in out_dir.glob("pack_*.json")] or [0])
    written, today, day = [], 0, 1
    for n, turn in enumerate(turns, start):   # GC-19: a pack never runs past the chat's daily picture quota
        if today and today + len(turn) > per_day:
            day, today = day + 1, 0
        today += len(turn)
        doc = {"schema": SCHEMA, "episode_id": man["episode_id"], "pack": n, "made_at": now(), "route": "gemini_chat",
               "native_size": list(NATIVE_CHAT_SIZE), "day": day, "pictures_per_day": per_day, "items": turn}
        write_json_atomic(out_dir / f"pack_{n:02d}.json", doc)
        write_text_atomic(out_dir / f"pack_{n:02d}.md", instruction_block(man, n, turn, day, per_day))
        written.append(f"pack_{n:02d}")
    return {"episode_id": man["episode_id"], "items": len(todo), "packs": written, "days": day if turns else 0,
            "review": [(it["id"], c["detail"]) for it in todo for c in it["checks"] if c["severity"] == "REVIEW"]}


# --- intake ------------------------------------------------------------------------------------------------------------
def ledger_path(root: Path) -> Path:
    return Path(root) / "planning" / "picture_ledger.jsonl"


def ledger_rows(root: Path) -> list[dict]:
    p = ledger_path(root)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _append(root: Path, row: dict) -> None:
    p = ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:   # one line per file, written the moment it is checked (OR-33 spirit)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def letterbox(img) -> bool:
    """A flat band (near-constant rows or columns) along an edge: the tool padded the picture (GC-12)."""
    import numpy as np
    a = np.asarray(img.convert("L"), dtype=np.float32)
    h, w = a.shape
    band_h, band_w = max(2, h // 40), max(2, w // 40)
    for strip in (a[:band_h], a[-band_h:], a[:, :band_w], a[:, -band_w:]):
        if strip.std() < 2.0 and (strip.mean() < 16 or strip.mean() > 239):
            return True
    return False


def phash(img) -> int:
    import imagehash
    return int(str(imagehash.phash(img)), 16)


def gate_file(path: Path, item: dict, min_size=NATIVE_CHAT_SIZE, seen: dict | None = None,
              identity=None, lettering=None) -> list[dict]:
    """GC-12 (+ GC-07, GC-13 hooks) for one dropped file. Every row: {gate, status PASS/FAIL/NOT_RUN, detail}."""
    from PIL import Image
    rows = []
    try:
        with Image.open(path) as im:
            im.verify()
        im = Image.open(path)
        im.load()
    except Exception as e:  # noqa: BLE001 - any decode failure is the gate's answer
        return [{"gate": "decodes", "status": "FAIL", "detail": f"does not decode: {e}"}]
    rows.append({"gate": "decodes", "status": "PASS", "detail": f"{im.format} {im.size[0]}x{im.size[1]}"})
    w, h = im.size
    ar_ok = abs((w / h) / ASPECT - 1) <= ASPECT_TOL
    rows.append({"gate": "aspect_16_9", "status": "PASS" if ar_ok else "FAIL", "detail": f"{w / h:.4f} vs {ASPECT:.4f}"})
    big = w >= min_size[0] and h >= min_size[1]
    rows.append({"gate": "native_size", "status": "PASS" if big else "FAIL",
                 "detail": f"{w}x{h}, needs at least {min_size[0]}x{min_size[1]}"})
    rows.append({"gate": "no_letterbox", "status": "FAIL" if letterbox(im) else "PASS", "detail": "edge bands"})
    if seen is not None:
        hv = phash(im)
        dup = next((k for k, v in seen.items() if bin(v ^ hv).count("1") <= DUP_HASH_DIST and k != item["id"]), None)
        rows.append({"gate": "not_duplicate", "status": "FAIL" if dup else "PASS",
                     "detail": f"same picture as {dup}" if dup else "unique"})
        seen[item["id"]] = hv
    rows.append(lettering(im, item) if lettering else
                {"gate": "letter_free", "status": "NOT_RUN", "detail": "no lettering detector installed: the contact sheet is read"})
    if item.get("people") and item["kind"] == "shot":
        rows.append(identity(path, item) if identity else
                    {"gate": "identity", "status": "NOT_RUN",
                     "detail": "no face embedder installed (tools/yunet): the contact sheet goes to the creator (GC-13)"})
    return rows


def face_identity(root: Path):
    """GC-13 with the repo's free face tools (``qa/face_points``: YuNet + SFace) when both models are installed, else None
    (the identity row is then NOT_RUN and the contact sheet goes to the creator). Each named hero of a shot picture must have
    a face whose SFace cosine to the hero's anchor is at least ``face_points.ID_MIN``; the threshold is a hypothesis, so a
    miss is REVIEW (D-59), never FAIL."""
    from explainer_engine.qa import face_points as FP
    from explainer_engine.qa import pixels as PX
    rec = FP.recognizer()
    if rec is None or not Path(PX.YUNET).is_file():
        return None
    import cv2

    def check(path: Path, item: dict) -> dict:
        faces = FP.detect(path, PX.YUNET, rec)
        missing, scores = [], {}
        for hero in item.get("people", []):
            anchor = Path(root) / anchor_path("character", hero)
            ref = FP.detect(anchor, PX.YUNET, rec) if anchor.is_file() else []
            if not ref or not faces:
                missing.append(hero)
                continue
            best = max(float(rec.match(f["_emb"], ref[0]["_emb"], cv2.FaceRecognizerSF_FR_COSINE)) for f in faces)
            scores[hero] = round(best, 3)
            if best < FP.ID_MIN:
                missing.append(hero)
        return {"gate": "identity", "status": "REVIEW" if missing else "PASS",
                "detail": f"cosine to the anchors {scores}; not matched: {missing}" if missing else f"cosine {scores}"}
    return check


def find_drop(root: Path, item: dict, drop: Path | None) -> Path | None:
    """The dropped file of one item: its exact target, or a file with the item's id as stem in ``drop`` (any image type)."""
    target = Path(root) / item["target"]
    for ext in IMAGE_EXTS:
        cand = target.with_suffix(ext)
        if cand.exists():
            return cand
    if drop:
        for ext in IMAGE_EXTS:
            for cand in (Path(drop) / f"{item['id']}{ext}", Path(drop) / f"{Path(item['target']).stem}{ext}"):
                if cand.exists():
                    return cand
    return None


def intake(root: Path, drop: Path | None = None, min_size=None, identity=None, lettering=None) -> dict:
    """Gate every dropped file of every pack; accepted files are copied to their target (the suffix follows the file's
    type); every file is a ledger row. The size floor is the episode's ``image_native_min_long_side`` (EP-02).
    Returns {accepted, rejected, missing, sheet}."""
    root = Path(root)
    man, _ = load(root)
    if min_size is None:
        min_size = sizes_of(man)[0]
    if identity is None:
        identity = face_identity(root)
    packs = sorted((root / "planning" / "turn_packs").glob("pack_*.json"))
    done = {r["id"]: r for r in ledger_rows(root) if r.get("status") == "accepted"}
    seen: dict = {}
    acc, rej, missing, review, sheet_items = [], [], [], [], []
    for p in packs:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if doc.get("episode_id") != man["episode_id"]:
            raise ContractError(f"{p.name} belongs to episode {doc.get('episode_id')!r}, not {man['episode_id']!r} (GC-10)")
        for it in doc["items"]:
            if it["id"] in done:
                continue
            f = find_drop(root, it, drop)
            if f is None:
                missing.append(it["id"])
                continue
            gates = gate_file(f, it, min_size, seen, identity, lettering)
            ok = all(g["status"] != "FAIL" for g in gates)
            dest = (root / it["target"]).with_suffix(f.suffix.lower())
            if ok and f.resolve() != dest.resolve():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
            kept = dest if ok else f
            row = {"id": it["id"], "pack": doc["pack"], "file": str(kept.relative_to(root)) if kept.is_relative_to(root)
                   else str(f), "sha256": sha256(kept), "status": "accepted" if ok else "rejected", "grade": "draft",
                   "gates": gates, "at": now()}
            _append(root, row)
            (acc if ok else rej).append(it["id"])
            if ok and any(g["status"] == "REVIEW" for g in gates):
                review.append(it["id"])
            sheet_items.append((dest if ok else f, it["id"], ok))
    sheet = contact_sheet(root, sheet_items) if sheet_items else None
    return {"episode_id": man["episode_id"], "accepted": acc, "rejected": rej, "missing": missing, "review": review,
            "sheet": str(sheet.relative_to(root)) if sheet else None}


def contact_sheet(root: Path, items: list[tuple[Path, str, bool]], cols: int = 4, width: int = 480) -> Path:
    """One sheet of the taken-in pictures, labelled, rejected ones framed red (the creator's eyes for GC-07/GC-13)."""
    from PIL import Image, ImageDraw
    th = int(width * 9 / 16)
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * width, rows * (th + 24)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for k, (path, label, ok) in enumerate(items):
        x, y = (k % cols) * width, (k // cols) * (th + 24)
        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((width, th))
            sheet.paste(im, (x + (width - im.size[0]) // 2, y))
        except Exception:  # noqa: BLE001 - an undecodable file shows as an empty cell
            pass
        if not ok:
            d.rectangle([x, y, x + width - 1, y + th - 1], outline=(220, 40, 40), width=4)
        d.text((x + 6, y + th + 4), label, fill=(230, 230, 230))
    out = Path(root) / "qa" / "contact_sheets" / f"intake_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out


# --- working masters (GC-14) ---------------------------------------------------------------------------------------
def master_path(target: str) -> str:
    return "assets/generated/masters/" + Path(target).stem + ".png"


def find_upscaler():
    """The installed free upscaler as ``fn(src, dst)``, or None (then promotion is NOT_RUN, never a plain resize)."""
    exe = os.environ.get(UPSCALER_ENV)
    if not exe or not Path(exe).is_file():
        return None

    def run(src: Path, dst: Path) -> None:
        subprocess.run([exe, "-i", str(src), "-o", str(dst), "-s", "2"], check=True, capture_output=True, timeout=600)
    return run


def promote(root: Path, upscaler=None) -> dict:
    """Upscale every accepted draft to its working master and gate the result (decodes, 16:9, long side >= the episode's
    ``image_min_long_side``). Each result is a ledger row with ``grade`` ``master`` (or the draft stays, with the reason)."""
    from PIL import Image
    root = Path(root)
    man, _ = load(root)
    _, need = sizes_of(man)
    rows = ledger_rows(root)
    masters = {r["id"] for r in rows if r.get("grade") == "master" and r.get("status") == "accepted"}
    drafts = [r for r in rows if r.get("status") == "accepted" and r.get("grade") == "draft" and r["id"] not in masters]
    up = upscaler or find_upscaler()
    out = {"episode_id": man["episode_id"], "promoted": [], "failed": [], "not_run": []}
    if up is None:
        out["not_run"] = [r["id"] for r in drafts]
        out["detail"] = f"no upscaler installed (set {UPSCALER_ENV}); the pictures stay drafts and cannot enter G7"
        return out
    for r in drafts:
        src = root / r["file"]
        dst = root / master_path(r["file"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            up(src, dst)
            with Image.open(dst) as im:
                w, h = im.size
        except Exception as e:  # noqa: BLE001 - a failed upscale is the gate's answer
            out["failed"].append({"id": r["id"], "detail": f"upscale failed: {e}"})
            continue
        ok = max(w, h) >= need and abs((w / h) / ASPECT - 1) <= ASPECT_TOL
        gate = {"gate": "master_size", "status": "PASS" if ok else "FAIL",
                "detail": f"{w}x{h}, needs a 16:9 long side of at least {need}"}
        _append(root, {"id": r["id"], "file": str(dst.relative_to(root)), "sha256": sha256(dst), "from_sha256": r["sha256"],
                       "status": "accepted" if ok else "rejected", "grade": "master" if ok else "draft", "gates": [gate],
                       "at": now()})
        (out["promoted"] if ok else out["failed"]).append(r["id"] if ok else {"id": r["id"], "detail": gate["detail"]})
    return out


def remake_list(root: Path, sharpness: dict | None) -> dict:
    """GC-14: the paid 2K re-make request. ``sharpness`` maps shot_id -> a gate row measured on the finished 1080p frame
    (status PASS/FAIL/NOT_RUN). Only close-up and medium-close-up shots with a named hero and a FAIL row are listed, with the
    batch price; nothing is sent. No measurement -> NOT_RUN."""
    from explainer_engine.imagegen import gemini as G
    root = Path(root)
    man, script = load(root)
    if not sharpness:
        return {"status": "NOT_RUN", "detail": "no finished 1080p frame was measured yet", "items": []}
    items = []
    for s in script.get("shots", []):
        size = str((s.get("camera_spec") or {}).get("shot_size", "")).lower()
        row = sharpness.get(s["shot_id"]) or {}
        if size in REMAKE_SHOT_SIZES and s.get("character_ids") and row.get("status") == "FAIL":
            items.append({"shot_id": s["shot_id"], "shot_size": size, "source": frame_path(s["shot_id"], "start"),
                          "detail": row.get("detail", "")})
    unit = G.BATCH_PRICES[REMAKE_MODEL][REMAKE_SIZE] + G.REFERENCE_USD
    doc = {"schema": "remake_2k/1", "episode_id": man["episode_id"], "made_at": now(), "model": REMAKE_MODEL,
           "size": REMAKE_SIZE, "tier": "batch", "usd_per_picture": round(unit, 4), "usd_total": round(unit * len(items), 4),
           "status": "needs_creator_ok" if items else "nothing_to_remake", "items": items,
           "prompt": "The same picture at 2K: keep every face, costume, pose, object and the light exactly as in the attached image."}
    if items:
        write_json_atomic(root / "planning" / "remake_2k.json", doc)
    return doc


def status(root: Path) -> dict:
    man, script = load(Path(root))
    queue = build_queue(man, script)
    rows = ledger_rows(Path(root))
    acc = {r["id"] for r in rows if r.get("status") == "accepted"}
    return {"episode_id": man["episode_id"], "needed": len(queue), "accepted": len(acc & {q["id"] for q in queue}),
            "open": [q["id"] for q in queue if q["id"] not in acc]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("episode", type=Path)
    e.add_argument("--size", type=int, default=DEFAULT_TURN)
    e.add_argument("--only", choices=("all", "anchors", "shots"), default="all")
    i = sub.add_parser("intake")
    i.add_argument("episode", type=Path)
    i.add_argument("--drop", type=Path)
    s = sub.add_parser("status")
    s.add_argument("episode", type=Path)
    pr = sub.add_parser("promote")
    pr.add_argument("episode", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "export":
        res = export(a.episode, a.size, a.only)
    elif a.cmd == "intake":
        res = intake(a.episode, a.drop)
    elif a.cmd == "promote":
        res = promote(a.episode)
    else:
        res = status(a.episode)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return 1 if a.cmd == "intake" and res["rejected"] else 0


if __name__ == "__main__":
    sys.exit(main())
