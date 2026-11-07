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
SH_C = {8: HERE / "p15c8.sh", 2: HERE / "p15c2.sh", 1: HERE / "p15c1.sh"}   # 24 pictures + N clips (the creator 2026-11-06 21:41 UTC): same bundle pin
SH_Q = HERE / "p15q.sh"   # the Qwen-only script (the creator 2026-11-06 17:34 UTC): same bundle pin, no LTX
HF_ROOT = "route_test_2026-11/pilot"
QUESTION = ("does LTX-2.5 distilled i2v hold one 7.7 s single-scene shot from a Blender-composed, Qwen-styled frame (a furnished "
            "room, many soldiers), and do places and props stay put across the room's angles once Qwen restyles each still?")
RESTYLE = ("room_establishing", "room_two_shot", "room_close_host", "room_close_guest", "room_reverse", "room_insert_table",
           "room_insert_clock", "battle_f000_colour")
FRAMES, SEED, SIZE = 185, 42, (1920, 1088)
# PR #155 (j5_limits, BP-184: crowd clash <= 5.04 s = 121 frames, dialogue = 0 s LTX): the battle clips are 121 frames, the rest stay 185.
CLIP_FRAMES = {"ltx_c4": 121, "ltx_c5": 121}


def clip_frames(stage: str) -> int:
    return CLIP_FRAMES.get(stage, FRAMES)
ROOM_AUDIO = "We hear a quiet room tone, a candle crackling and low voices."
# v4 (the creator 2026-11-06 16:42 UTC: one start-up buys 30 s and more answers, 2-3 prompt styles for video and audio, other
# settings; Fable's list 16:42 UTC). (stage, shot, video style, audio sentence, spoken line, question). The run order puts c5 and c8
# last: Fable's drop order when the worst case does not fit.
CLIPS = [
    ("ltx_c1", "room_two_shot", "S1", ROOM_AUDIO, None, "which style sentence keeps our look? S1, our film sentence"),
    ("ltx_c2", "room_two_shot", "S2", ROOM_AUDIO, None, "which style sentence keeps our look? S2, the xworld captions' look words"),
    ("ltx_c3", "room_two_shot", "S3", ROOM_AUDIO, None, "which style sentence keeps our look? S3, no style sentence"),
    ("ltx_c4", "battle_f000_colour", "S2", "We hear a roaring battle cry and thundering feet.", None,
     "do the crowd's direction and the camera hold? (S2; audio A: battle roar)"),
    ("ltx_c6", "room_establishing", "S2", ROOM_AUDIO, None, "do the wide room's props stay put over 7.7 s?"),
    ("ltx_c7", "room_close_host", "S2", "We hear his low voice and a candle crackling.", ("host", "We ride at first light."),
     "can LTX's native voice and lips carry a dialogue close-up, or does dialogue stay ElevenLabs + J5?"),
    ("ltx_c8", "room_insert_clock", "S2", "We hear a slow clock ticking.", None, "does a small object move without drift?"),
    ("ltx_c5", "battle_f000_colour", "S1", "We hear distant war drums and the wind.", None,
     "do the crowd's direction and the camera hold? (S1; audio B: distant drums)"),
]
DROP_ORDER = ("ltx_c5", "ltx_c8")   # Fable 16:42 UTC: if the worst case does not fit the cap, drop clip 5 first, then 8
CLIP_MAX_MIN = 12.0   # per clip on the H100: 2x the ~5.8 min estimate (193 frames ~6 min, scaled); see the plan for the 17.5 case
CLIP_EXPECTED_MIN = 5.8
CARDS = [{"name": "A100 80GB", "cloud": "SECURE", "price_h": 1.79, "gpu_speed": 0.6},
         {"name": "H100 NVL", "cloud": "COMMUNITY", "price_h": 2.59, "gpu_speed": 1.0}]   # what could place at 16:33 UTC (worker)
LIMITS = {"max_usd": 6.5, "max_hours": 2.5, "max_idle_gpu_share": 0.15}   # Fable 16:42 UTC: <= 6.5 with the $7.99 balance
DISK_GB = 200   # Qwen-Image-2.1 33.1 GB + LTX-2.5's used files 86.5 GB (+ the IC LoRA) + pip ~15 GB + outputs < 2 GB (HF, 2026-11-06)
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
    for stage, sid, style, audio, line, question in CLIPS:
        nf = clip_frames(stage)
        jid = f"pilot.{stage[4:]}.{sid}.{style}.ltx25.i2v.f{nf}.s{SEED}"
        ljobs.append({"id": jid, "question": question, "recipe": "ltx_i2v/1", "pipeline": "distilled", "shot_id": sid, "clip_id": sid,
                      "style": style, "audio_prompt": audio, "spoken_line": line[1] if line else None,
                      "base": "ltx25", "variant": "i2v", "model": copy.deepcopy(e1["model"]), "text_encoder": copy.deepcopy(e1["text_encoder"]),
                      "lora": None, "frames": nf, "fps": 24, "width": SIZE[0], "height": SIZE[1], "seed": SEED,
                      "first_frame": {"path": f"{HF_ROOT}/first_frames/{sid}.png", "sha256": None, "pose": "start"},
                      "conditioning": [], "attention_mask": None, "chain_from": None,
                      "prompt": PS.ltx_prompt(sid, style=style, audio=audio, line=line),
                      "stage2_ic": False, "output": f"{HF_ROOT}/ltx/{jid}.mp4"})
        clips[stage] = {"job": jid, "first_frame_of": sid}
    sch = schedule()
    ltx = {k: copy.deepcopy(ltx14[k]) for k in ("schema", "code", "hf", "controls", "upscale")}
    ltx.update(weights={"ltx25": copy.deepcopy(ltx14["weights"]["ltx25"])}, clip_timeout_s=int(CLIP_MAX_MIN * 60),
               end_reserve_min=sch["end_reserve_min"])
    ltx["upscale"]["enabled"] = False   # the question is the motion; no upscale on the pod (as p14)
    return {"schema": "p15_config/1", "question": QUESTION, "hf_root": HF_ROOT, "hf": copy.deepcopy(ltx14["hf"]),
            "stills_manifest": {"path": f"{stills['hf_prefix']}/pilot_stills.json"},
            "qwen": copy.deepcopy(p14["qwen"]), "heroes_refs": copy.deepcopy(p14["heroes_refs"]) + [H3],
            "first_frame_size": list(SIZE), "qwen_jobs": qjobs, "ltx": ltx, "ltx_jobs": ljobs, "clips": clips,
            "max_ltx_failures": 2, "audio": {"in_mp4": True, "wav_sidecar": True},
            "launch": launch()}


def schedule(clips=None) -> dict:
    """``p15_schedule.json`` (pod_schedule/1): the net lane's two downloads, the restyle, one stage per clip, F."""
    ids = [c[0] for c in (clips or CLIPS)]
    st = [{"id": "weights_qwen", "needs": [], "on": {"net": {"expected_min": 5, "max_min": 15}}, "measured": False,
           "note": "Qwen-Image-2.1 + xworld_v2 ck3000 (step-3 pod 1 had it before 14:40 UTC, not timed alone)"},
          {"id": "qwen_restyle", "needs": ["weights_qwen"], "on": {"gpu": {"expected_min": 5.8, "max_min": 17.5}}, "measured": True,
           "note": "8 edits at 33.5-38.5 s + 61 s load: pod 1's measured Qwen speed on the H100 NVL"},
          {"id": "weights_ltx25", "needs": ["weights_qwen"], "on": {"net": {"expected_min": 4, "max_min": 12}}, "measured": False,
           "note": "LTX-2.5 distilled (pod 1: both LTX bases in 5.5 min, measured)"}]
    for c in clips or CLIPS:
        st.append({"id": c[0], "needs": ["weights_ltx25", "qwen_restyle"],
                   "on": {"gpu": {"expected_min": round(CLIP_EXPECTED_MIN * clip_frames(c[0]) / FRAMES, 1),
                                  "max_min": round(CLIP_MAX_MIN * clip_frames(c[0]) / FRAMES, 1)}}, "measured": False,
                   "note": f"1 clip, {clip_frames(c[0])} frames, {SIZE[0]}x{SIZE[1]}, seed {SEED}, {c[1]} {c[2]}, native audio (unmeasured)"})
    st.append({"id": "F", "needs": ids, "on": {"gpu": {"expected_min": 0.1, "max_min": 1}}, "measured": False,
               "note": "speeds.json + the last uploads"})
    return {"schema": "pod_schedule/1", "setup_min": 8, "end_reserve_min": 10, "lanes": {"gpu": 1, "net": 1}, "cards": CARDS,
            "limits": LIMITS, "stages": st,
            "_doc": ("Pilot v4 (the creator 2026-11-06 16:42 UTC): Qwen restyles the 8 Blender stills, then 8 LTX-2.5 distilled i2v clips "
                     "with native audio, one per stage. Generated by build.py; no Blender on the pod.")}


MOUTH_SHEETS = 2        # J5 mouth variants (p15_mouth): ONE sheet picture per hero (6 shapes + 2 blinks in a grid), the same loaded pipeline; up to 2 more seeds per hero are retries inside the 3x worst case (ვანო 19:41 UTC)
QWEN_PICS = 24          # --only qwen: 8 stills x 3 look variants (S1/S2/S3, Fable 2026-11-06 18:00 UTC)
QWEN_LOAD_S, QWEN_EDIT_S = 61, 36   # pod 1, H100 NVL: 61 s load, 33.5-38.5 s per edit (middle 36)
DISK_QWEN_GB = 110   # Qwen-Image-2.1 33.1 GB + pip ~15 GB + outputs < 2 GB = ~50 GB, the same ~60 GB margin that DISK_GB has over its ~137 GB
LIMITS_QWEN = {"max_usd": 3.4, "max_hours": 2.0, "max_idle_gpu_share": 0.5}   # Fable 18:00 UTC: 24 pictures, usual 3x maxes, A100 only
# the cards that could place at 16:33 UTC plus the COMMUNITY A100 the first plan priced (it had no stock then)
# gpu_speed is relative to the H100 NVL (1.0). A100 0.6: the first plan. The 48 GB cards (SECURE rows of `runpod cards --vram 48`,
# 2026-11-06 19:40 UTC) are ESTIMATED from runpod.SPEED ratios (A40/A6000 0.5, L40S 0.9, H100 NVL 1.8), never measured: the asset pod's
# 33-41 s per 1280x720 picture came from an RTX PRO 6000 Blackwell (96 GB, $1.69/h), not from a 48 GB card.
# speeds of the cards below the A100 are ALL ESTIMATED: gpu_speed = runpod.SPEED / 1.8 (H100 NVL = 1.0); prices are the live catalog rows of
# 2026-11-06 20:15 UTC. Out on purpose: H100 (17 min of work) and RTX PRO 6000 Blackwell (21 min; measured ~1.0 on the asset pod) fail RP-01
# (work >= 3 x the 8 min setup); A100 80GB PCIe (worst $3.65 / 122 min) is over both caps; RTX PRO 4000/4500 Blackwell have no speed in runpod.SPEED. Qwen-Image-2.1 is a 13.3 GB transformer + 16.3 GB text
# encoder + 1.3 GB VAE, drawn with model_cpu_offload: one part on the GPU at a time, so 24 GB cards may fit; the fit at 1280x720 with 3 images is unknown.
CARDS_QWEN = [{"name": "RTX A5000", "cloud": "SECURE", "price_h": 0.27, "gpu_speed": 0.194},
              {"name": "A40", "cloud": "SECURE", "price_h": 0.59, "gpu_speed": 0.278},
              {"name": "RTX A6000", "cloud": "SECURE", "price_h": 0.59, "gpu_speed": 0.278},
              {"name": "L4", "cloud": "SECURE", "price_h": 0.59, "gpu_speed": 0.167},
              {"name": "RTX 5090", "cloud": "COMMUNITY", "price_h": 0.69, "gpu_speed": 0.611},
              {"name": "RTX 4090", "cloud": "SECURE", "price_h": 0.89, "gpu_speed": 0.444},
              {"name": "RTX 6000 Ada", "cloud": "SECURE", "price_h": 0.99, "gpu_speed": 0.472},
              {"name": "L40S", "cloud": "SECURE", "price_h": 1.09, "gpu_speed": 0.5},
              {"name": "RTX 5090", "cloud": "SECURE", "price_h": 1.19, "gpu_speed": 0.611},
              {"name": "A100 80GB", "cloud": "COMMUNITY", "price_h": 1.39, "gpu_speed": 0.6},
              {"name": "A100 80GB", "cloud": "SECURE", "price_h": 1.79, "gpu_speed": 0.6}]


def schedule_qwen() -> dict:
    """``p15q_schedule.json``: the Qwen weights, the 8 restyle edits, F. Same numbers as ``schedule()``'s first, second and last stage."""
    full = schedule()
    st = [copy.deepcopy(s) for s in full["stages"] if s["id"] in ("weights_qwen", "qwen_restyle")]
    exp = round((QWEN_LOAD_S + (QWEN_PICS + MOUTH_SHEETS) * QWEN_EDIT_S) / 60, 1)   # on the H100 NVL (speed 1.0); the card's gpu_speed scales it
    for s in st:
        if s["id"] == "qwen_restyle":
            s["on"]["gpu"] = {"expected_min": exp, "max_min": round(exp * 3, 1)}   # the usual 3x
            s["note"] = f"{QWEN_PICS} edits (8 stills x S1/S2/S3) + {MOUTH_SHEETS} J5 mouth sheets at 36 s + 61 s load: pod 1's measured Qwen speed on the H100 NVL"
    st.append({"id": "F", "needs": ["qwen_restyle"], "on": {"gpu": {"expected_min": 0.1, "max_min": 1}}, "measured": False,
               "note": "speeds.json + the last uploads"})
    return {"schema": "pod_schedule/1", "setup_min": full["setup_min"], "end_reserve_min": full["end_reserve_min"],
            "lanes": full["lanes"], "cards": CARDS_QWEN, "limits": LIMITS_QWEN, "stages": st,
            "_doc": ("Pilot, Qwen only (the creator 2026-11-06 17:34 UTC): the 8 Blender stills restyled in 3 look variants by Qwen-Image-2.1 + xworld_v2; "
                     "no LTX weights, no clip. Generated by build.py; no Blender on the pod.")}


CLIP_SETS = {8: ["ltx_c1", "ltx_c2", "ltx_c3", "ltx_c4", "ltx_c6", "ltx_c7", "ltx_c8", "ltx_c5"],   # the v4 order, all eight jobs
             2: ["ltx_c2", "ltx_c4"],
             1: ["ltx_c4"]}   # PR #155 pilot (the creator 2026-11-07 07:46 UTC "yes"): the one battle clip at 121 frames, no dialogue clip   # one dialogue shot (room_two_shot, look S2) and one action shot (battle frame 0, look S2)
# 80 GB cards only (the creator's scope card 21:41 UTC). Speeds relative to the H100 NVL; ESTIMATED except the H100 NVL's Qwen part (pod 1).
# RTX PRO 6000 Blackwell is out: the LTX stack never ran on sm_120 (the asset pod ran Qwen only).
CARDS_CLIPS = [{"name": "A100 80GB", "cloud": "COMMUNITY", "price_h": 1.39, "gpu_speed": 0.6},
               {"name": "A100 80GB", "cloud": "SECURE", "price_h": 1.79, "gpu_speed": 0.6},
               {"name": "H100 NVL", "cloud": "COMMUNITY", "price_h": 2.59, "gpu_speed": 1.0},
               # window 2 (the creator's card 2026-11-07 06:04 UTC: 2.8 h): speed ESTIMATED = A100 0.6 x SPEED 0.95
               {"name": "A100 80GB PCIe", "cloud": "COMMUNITY", "price_h": 1.19, "gpu_speed": 0.57},
               # window 3 (the creator 2026-11-07 06:08 UTC "4.7 cap"): the other 80 GB LTX-safe cards that pass RP-11 at $4.71 / 2.8 h, speeds ESTIMATED = SPEED / 1.8-style
               {"name": "H100 PCIe", "cloud": "COMMUNITY", "price_h": 1.99, "gpu_speed": 0.89},
               {"name": "H100 80GB HBM3", "cloud": "COMMUNITY", "price_h": 2.69, "gpu_speed": 1.11}]


# set 1 (p15d): the three 80 GB LTX-safe cards that pass RP-11 at the ORIGINAL $3.7 / 2.7 h; speeds ESTIMATED.
CARDS_ONE = [{"name": "A100 80GB", "cloud": "COMMUNITY", "price_h": 1.39, "gpu_speed": 0.6},
             {"name": "A100 80GB PCIe", "cloud": "COMMUNITY", "price_h": 1.19, "gpu_speed": 0.57},
             {"name": "H100 PCIe", "cloud": "COMMUNITY", "price_h": 1.99, "gpu_speed": 0.89}]


def clip_first_frame(clip_id: str) -> str:
    """The restyle picture an LTX clip starts from when the pod draws the 24 look variants: ``<shot>__<look>`` with the look equal to the clip's
    own style tag (c1 room_two_shot S1 -> room_two_shot__S1). The tag was a prompt style in v4; here it also picks the look variant."""
    c = next(x for x in CLIPS if x[0] == clip_id)
    return f"{c[1]}__{c[2]}"


LIMITS_CLIPS = {8: {"max_usd": 6.5, "max_hours": 4.7, "max_idle_gpu_share": 0.15},   # PROPOSED, the creator's card decides: A100 COMMUNITY worst $6.43 / 278 min (with the 2 mouth sheets)
                2: {"max_usd": 4.71, "max_hours": 2.8, "max_idle_gpu_share": 0.15},
                1: {"max_usd": 3.7, "max_hours": 2.7, "max_idle_gpu_share": 0.15}}   # 2.8 h = the creator 2026-11-07 06:04 (A100 PCIe worst 2.74 h); PROPOSED: A100 COMMUNITY worst $3.65 / 158 min (24 + 2 mouth sheets + 2 clips); 4 sheets $3.79, 6 sheets $3.93


def schedule_qwen_clips(n: int, limits: dict | None = None) -> dict:
    """``p15qc<n>_schedule.json``: the 24 look-variant pictures, the LTX weights, ``n`` clips, F (80 GB cards)."""
    full, q = schedule(), schedule_qwen()
    ids = CLIP_SETS[n]
    st = [copy.deepcopy(s) for s in q["stages"] if s["id"] in ("weights_qwen", "qwen_restyle")]
    st.append(copy.deepcopy(next(s for s in full["stages"] if s["id"] == "weights_ltx25")))
    for s in full["stages"]:
        if s["id"] in ids:
            st.append(copy.deepcopy(s))
    st.sort(key=lambda s: (["weights_qwen", "qwen_restyle", "weights_ltx25"] + ids).index(s["id"]))
    st.append({"id": "F", "needs": ids, "on": {"gpu": {"expected_min": 0.1, "max_min": 1}}, "measured": False, "note": "speeds.json + the last uploads"})
    return {"schema": "pod_schedule/1", "setup_min": full["setup_min"], "end_reserve_min": full["end_reserve_min"], "lanes": full["lanes"],
            "cards": CARDS_ONE if n == 1 else CARDS_CLIPS, "limits": limits or LIMITS_CLIPS[n], "stages": st,
            "_doc": (f"Pilot: the 24 Qwen look-variant pictures + {n} LTX-2.5 i2v clips (the creator 2026-11-06 21:41 UTC: video too, because a pod is hard to get). "
                     "Clip first frames: " + ", ".join(f"{i} <- {clip_first_frame(i)}" for i in ids) + ". Generated by build.py.")}


def launch_qwen(card: str = "A100", cloud: str = "COMMUNITY") -> dict:
    return {"cmd": (f"python -m explainer_engine.cloud.runpod create --yes --vram 80 --only \"{card}\" --cloud {cloud} "
                    f"--max-usd {LIMITS_QWEN['max_usd']} --max-hours {LIMITS_QWEN['max_hours']} --disk {DISK_QWEN_GB} --boot-minutes 25 "
                    "--setup-min 8 --work-min 26 --ref-hours 1.3 --script explainer_engine/training/pods/p15/p15q.sh --script-url <HF url of p15q.sh> "
                    "--schedule explainer_engine/training/pods/p15/p15q_schedule.json "
                    "--heartbeat datasets/vano1919/tmr-artifacts:route_test_2026-11/pilot/beat.txt --ledger <run.json>"),
            "upload_first": "HF code/p15/ee_src.tar.gz = python -m explainer_engine.training.pods.p15.build bundle --ref <the audited commit>; "
                            "HF code/p15/p15q.sh = explainer_engine/training/pods/p15/p15q.sh at that commit",
            "disk_gb": DISK_QWEN_GB,
            "rp01": ("--work-min 26 = the A100's expected GPU work (RP-11: 25.8 min), over 3 x the 8 min setup; the H100's 15.5 min "
                     "would fail RP-01, so the launch names the A100 only: COMMUNITY first, then SECURE")}


def launch() -> dict:
    """The worker's create line, in the CLI's own flags (runpod.py create)."""
    return {"cmd": ("python -m explainer_engine.cloud.runpod create --yes --vram 80 --only \"H100 NVL\" --cloud COMMUNITY "
                    f"--max-usd {LIMITS['max_usd']} --max-hours {LIMITS['max_hours']} --disk {DISK_GB} --boot-minutes 25 "
                    "--setup-min 8 --work-min 130 --script explainer_engine/training/pods/p15/p15.sh --script-url <HF url of p15.sh> "
                    "--schedule explainer_engine/training/pods/p15/p15_schedule.json "
                    "--heartbeat datasets/vano1919/tmr-artifacts:route_test_2026-11/pilot/beat.txt --ledger <run.json>"),
            "upload_first": "HF code/p15/ee_src.tar.gz = python -m explainer_engine.training.pods.p15.build bundle --ref <the audited commit>",
            "disk_gb": DISK_GB,
            "why_h100_only": ("worst case on the A100 SECURE $1.79/h is $6.68 (3.7 h at speed 0.6), over the $6.5 cap; the H100 NVL "
                              "$2.59/h worst is $6.37 in 2.46 h (expected $3.25)")}


def bundle(out: Path, ref: str | None = None) -> str:
    excl = LEAN.EXCLUDE
    # every pinned script is excluded (a script cannot carry the sha of a bundle that contains itself): derived, so a new variant cannot be forgotten
    LEAN.EXCLUDE = (*excl, "explainer_engine/training/pods/p15/p15.sh", "explainer_engine/training/pods/p15/p15q.sh",
                    *(f"explainer_engine/training/pods/p15/{p.name}" for p in SH_C.values()))
    try:
        sha = LEAN.bundle(out, ref)
    finally:
        LEAN.EXCLUDE = excl
    LEAN.pin(sha, SH)
    LEAN.pin(sha, SH_Q)
    for p in SH_C.values():
        if p.exists():
            LEAN.pin(sha, p)
    return sha


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("config")
    c.add_argument("--stills", type=Path, required=True)
    sub.add_parser("schedule-qwen")
    sub.add_parser("schedule-clips")
    sub.add_parser("launch-qwen")
    b = sub.add_parser("bundle")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--ref")
    a = ap.parse_args(argv)
    if a.cmd == "config":
        doc = config(json.loads(a.stills.read_text(encoding="utf-8")))
        write_json_atomic(HERE / "p15.json", doc)
        write_json_atomic(HERE / "p15_schedule.json", schedule())
        write_json_atomic(HERE / "p15q_schedule.json", schedule_qwen())
        print(json.dumps({"qwen": [j["shot"] for j in doc["qwen_jobs"]], "ltx": [j["id"] for j in doc["ltx_jobs"]]}, indent=1))
    elif a.cmd == "schedule-qwen":
        write_json_atomic(HERE / "p15q_schedule.json", schedule_qwen())
    elif a.cmd == "schedule-clips":
        for n in CLIP_SETS:
            write_json_atomic(HERE / f"p15qc{n}_schedule.json", schedule_qwen_clips(n))
    elif a.cmd == "launch-qwen":
        print(json.dumps(launch_qwen(), indent=1))
    else:
        print(bundle(a.out, a.ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
