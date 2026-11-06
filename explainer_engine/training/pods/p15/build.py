"""Host side of the pilot pod (free, no pod, no upload): ``p15.json`` written from the stills manifest (``pilot_stills/1``, the HF
copy of ``route_test_2026-11/pilot/blender/pilot_stills.json``), the shot cards' prompts and the step-3 pod's pins, then the code
bundle and its sha256 line in ``p15.sh``.

    python -m explainer_engine.training.pods.p15.build config --stills <pilot_stills.json>    # p15.json only
    python -m explainer_engine.training.pods.p15.build bundle --out ee_src.tar.gz [--ref HEAD]  # the bundle; pins its sha256 in p15.sh

The bundle is ``p14/lean.bundle`` (every git-tracked file under explainer_engine/, config/, assets/ at ``--ref``, byte-stable)
without ``p15.sh``, which pins it. The worker uploads it to HF ``code/p15/ee_src.tar.gz`` from the OR-34-audited commit; this module
never uploads.

What goes on the pod (PILOT_1MIN_PLAN.md v3): the Qwen restyle of the 7 room stills and the battle colour frame 0 (frame 200 and the
depth pass are no clip's first frame, so they are not restyled), then two LTX-2.5 distilled i2v clips of 185 frames (7.71 s, BP-172):
the room two-shot and the battle frame 0, seed 42, 1920x1088, prompts from the same cards.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from explainer_engine.blender import pilot_stills as PS
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.training.pods.p14 import lean as LEAN

HERE = Path(__file__).resolve().parent
SH = HERE / "p15.sh"
HF_ROOT = "route_test_2026-11/pilot"
QUESTION = ("does LTX-2.5 distilled i2v hold one 7.7 s single-scene shot from a Blender-composed, Qwen-styled frame (a furnished "
            "room, many soldiers), and do places and props stay put across the room's angles once Qwen restyles each still?")
RESTYLE = ("room_establishing", "room_two_shot", "room_close_host", "room_close_guest", "room_reverse", "room_insert_table",
           "room_insert_clock", "battle_f000_colour")
CLIPS = {"ltx_room": "room_two_shot", "ltx_battle": "battle_f000_colour"}   # Fable 15:52 UTC: the room clip is the two-shot
FRAMES, SEED, SIZE = 185, 42, (1920, 1088)
# B_H1/B_H2 as the step-3 pod pins them; B_H3 read 2026-11-06 from HF route_test_2026-11/assets/B/B_H3_front.png
H3 = {"name": "B_H3_front", "path": "route_test_2026-11/assets/B/B_H3_front.png",
      "sha256": "bae26df7f2a27872e8bcf52c2d762da955c7259f7b5c3b624c535cbe04bd0001"}


def _p14(name: str) -> dict:
    return json.loads((HERE.parent / "p14" / name).read_text(encoding="utf-8"))


def config(stills: dict) -> dict:
    if stills.get("schema") != PS.SCHEMA:
        raise ContractError(f"not a {PS.SCHEMA} manifest")
    st, p14, ltx14 = stills["shots"], _p14("p14_stages.json"), _p14("p14.json")
    missing = [s for s in RESTYLE if s not in st]
    if missing:
        raise ContractError(f"the stills manifest lacks {missing}")
    qjobs = []
    for sid in RESTYLE:
        p = PS.prompts(sid)
        if st[sid].get("prompts") and st[sid]["prompts"]["qwen"] != p["qwen"]:
            raise ContractError(f"{sid}: the manifest's prompt is not the card's (re-run pilot_stills manifest)")
        qjobs.append({"shot": sid, "still": {"path": f"{stills['hf_prefix']}/{st[sid]['file']}", "sha256": st[sid]["sha256"]},
                      "qwen_prompt": p["qwen"], "hero_refs": p["hero_refs"], "ltx_prompt": p["ltx"]})
    e1 = next(j for j in _p14("ltx_jobs.json")["jobs"] if j["base"] == "ltx25")
    ljobs, clips = [], {}
    for stage, sid in CLIPS.items():
        jid = f"pilot.{sid}.ltx25.i2v.f{FRAMES}.s{SEED}"
        ljobs.append({"id": jid, "question": QUESTION, "recipe": "ltx_i2v/1", "pipeline": "distilled", "shot_id": sid, "clip_id": sid,
                      "base": "ltx25", "variant": "i2v", "model": copy.deepcopy(e1["model"]), "text_encoder": copy.deepcopy(e1["text_encoder"]),
                      "lora": None, "frames": FRAMES, "fps": 24, "width": SIZE[0], "height": SIZE[1], "seed": SEED,
                      "first_frame": {"path": f"{HF_ROOT}/first_frames/{sid}.png", "sha256": None, "pose": "start"},
                      "conditioning": [], "attention_mask": None, "chain_from": None, "prompt": PS.prompts(sid)["ltx"],
                      "stage2_ic": False, "output": f"{HF_ROOT}/ltx/{jid}.mp4"})
        clips[stage] = {"job": jid, "first_frame_of": sid}
    sch = json.loads((HERE / "p15_schedule.json").read_text(encoding="utf-8"))
    tmax = {s["id"]: next(iter(s["on"].values()))["max_min"] for s in sch["stages"]}
    ltx = {k: copy.deepcopy(ltx14[k]) for k in ("schema", "code", "hf", "controls", "upscale")}
    ltx.update(weights={"ltx25": copy.deepcopy(ltx14["weights"]["ltx25"])}, clip_timeout_s=int(max(tmax[s] for s in CLIPS) * 60),
               end_reserve_min=sch["end_reserve_min"])
    ltx["upscale"]["enabled"] = False   # the question is the motion; no upscale on the pod (as p14)
    return {"schema": "p15_config/1", "question": QUESTION, "hf_root": HF_ROOT, "hf": copy.deepcopy(ltx14["hf"]),
            "stills_manifest": {"path": f"{stills['hf_prefix']}/pilot_stills.json"},
            "qwen": copy.deepcopy(p14["qwen"]), "heroes_refs": copy.deepcopy(p14["heroes_refs"]) + [H3],
            "first_frame_size": list(SIZE), "qwen_jobs": qjobs, "ltx": ltx, "ltx_jobs": ljobs, "clips": clips,
            "max_ltx_failures": 2}


def bundle(out: Path, ref: str | None = None) -> str:
    excl = LEAN.EXCLUDE
    LEAN.EXCLUDE = (*excl, "explainer_engine/training/pods/p15/p15.sh")
    try:
        sha = LEAN.bundle(out, ref)
    finally:
        LEAN.EXCLUDE = excl
    LEAN.pin(sha, SH)
    return sha


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("config")
    c.add_argument("--stills", type=Path, required=True)
    b = sub.add_parser("bundle")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--ref")
    a = ap.parse_args(argv)
    if a.cmd == "config":
        doc = config(json.loads(a.stills.read_text(encoding="utf-8")))
        write_json_atomic(HERE / "p15.json", doc)
        print(json.dumps({"qwen": [j["shot"] for j in doc["qwen_jobs"]], "ltx": [j["id"] for j in doc["ltx_jobs"]]}, indent=1))
    else:
        print(bundle(a.out, a.ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
