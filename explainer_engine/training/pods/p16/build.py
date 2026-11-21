"""Host side of P1's pod (free, no pod, no upload): ``p16.json`` and ``p16_schedule.json`` for the rest of the 60 s pilot minute
(EXEC_QUEUE.md P1; the creator 2026-11-06 16:18 UTC), written from p15's committed config (its stills, prompts, pins), the new
battle stills' manifest (``pilot_stills_p16.json``) and, once the p15 pod has run, its measured first frames and LTX speed.

    python -m explainer_engine.training.pods.p16.build config --extra <pilot_stills_p16.json> --stills <pilot_stills.json> [--p15-out <dir>] [--ltx-s-per-frame X --on "A100 80GB"]
    python -m explainer_engine.training.pods.p16.build bundle --out ee_src.tar.gz [--ref HEAD]   # pins its sha256 in p16.sh

The minute (24 fps): the p15 pod's two clips (room two-shot, battle frame 0; 185 frames each) are reused as they are. This pod adds
eight clips: five room clips from p15's restyled stills (establishing, close host, close guest, reverse, insert table: 145, 145,
145, 145, 97 frames) and three battle clips (wide high 145, front mid 145, frame 200 121 frames), the last three from restyles this
pod draws. Every length is 8k+1 and at most 8 s (BP-172); the edit trims to the shot (the creator's Q4). The room clock insert has
no clip (J5 push-in on its still, free).
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

from explainer_engine.blender import pilot_stills as PS
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.training.pods.p14 import lean as LEAN

HERE = Path(__file__).resolve().parent
P15 = HERE.parent / "p15"
SH = HERE / "p16.sh"
P15_ROOT = "route_test_2026-11/pilot"
HF_ROOT = "route_test_2026-11/pilot/p16"
QUESTION = ("do Qwen-Image-2.1 + xworld_v2 restyles of our Blender stills hold the look, and does LTX-2.5 distilled i2v hold the "
            "motion, across ten clips that cut into one minute (identity across angles, props stay, no melting)?")
SEED, SIZE = 42, (1920, 1088)
# stage -> (shot, frames, where its first frame is drawn); camera names stand for their one picked frame
CLIPS = {"ltx_room_establishing": ("room_establishing", 145, "p15"), "ltx_room_close_host": ("room_close_host", 145, "p15"),
         "ltx_room_close_guest": ("room_close_guest", 145, "p15"), "ltx_room_reverse": ("room_reverse", 145, "p15"),
         "ltx_room_insert_table": ("room_insert_table", 97, "p15"),
         "ltx_battle_wide_high": ("wide_high", 145, "qwen_restyle"), "ltx_battle_front_mid": ("front_mid", 145, "qwen_restyle"),
         "ltx_battle_f200": ("battle_f200_colour", 121, "qwen_restyle")}
CARDS = [{"name": "A100 80GB", "cloud": "COMMUNITY", "price_h": 1.39, "gpu_speed": 0.6},
         {"name": "H100 NVL", "cloud": "COMMUNITY", "price_h": 2.59, "gpu_speed": 1.0}]
SPEED = {c["name"]: c["gpu_speed"] for c in CARDS}
LTX_MIN_PER_FRAME_EST = 6.0 / 193       # H100 NVL minutes per frame, unmeasured until the p15 pod's clips
QWEN_LOAD_S, QWEN_EDIT_S = 61.0, 36.0   # pod 1's H100 NVL, measured (p15 schedule)
LIMITS = {"max_usd": 5.0, "max_hours": 3.0, "max_idle_gpu_share": 0.15}


def _shot_ids(extra: dict) -> dict[str, str]:
    """camera name -> the picked still's id in the extra manifest (``battle_wide_high_f096_colour``)."""
    out = {}
    for sid, s in extra["shots"].items():
        out[s["camera_name"]] = sid
    return out


def _p15() -> dict:
    return json.loads((P15 / "p15.json").read_text(encoding="utf-8"))


def p15_first_frames(p15_out: Path | None) -> dict[str, dict]:
    """shot -> {"sha256"} of the first frames the p15 pod drew (its qwen/manifest.jsonl), when its output is at hand."""
    if p15_out is None:
        return {}
    rows = {}
    mf = Path(p15_out) / "qwen" / "manifest.jsonl"
    for ln in mf.read_text(encoding="utf-8").splitlines():
        r = json.loads(ln) if ln.strip() else {}
        if r.get("status") == "ok":
            rows[r["name"]] = {"sha256": r["first_frame"]["sha256"]}
    return rows


def clip_frames_ok(frames: int) -> bool:
    return (frames - 1) % 8 == 0 and frames / 24 <= 8.0


def config(extra: dict, stills: dict, p15_out: Path | None = None) -> dict:
    """``extra``: pilot_stills_p16.json (the new battle stills); ``stills``: the pinned pilot_stills.json (frame 200's colour pass)."""
    if extra.get("schema") != PS.EXTRA_SCHEMA or stills.get("schema") != PS.SCHEMA:
        raise ContractError(f"need a {PS.EXTRA_SCHEMA} and a {PS.SCHEMA} manifest")
    base = _p15()
    cams = _shot_ids(extra)
    for want in ("wide_high", "front_mid"):
        if want not in cams:
            raise ContractError(f"the extra manifest has no still of the {want} camera")
    ff15 = p15_first_frames(p15_out)
    p15_jobs = {j["shot"]: j for j in base["qwen_jobs"]}
    qjobs, shot_of = [], {}
    for stage, (shot, frames, src) in CLIPS.items():
        sid = cams.get(shot, shot)
        shot_of[stage] = sid
        if not clip_frames_ok(frames):
            raise ContractError(f"{stage}: {frames} frames is not 8k+1 and at most 8 s")
        if src == "p15" and sid not in p15_jobs:
            raise ContractError(f"{stage}: p15 has no restyle of {sid}")
    for stage in ("ltx_battle_f200", "ltx_battle_wide_high", "ltx_battle_front_mid"):
        sid = shot_of[stage]
        s, hf = (extra["shots"][sid], extra["hf_prefix"]) if sid in extra["shots"] else (stills["shots"].get(sid), stills["hf_prefix"])
        if s is None:
            raise ContractError(f"{sid}: no still in either manifest")
        p = PS.prompts(sid)
        if s.get("prompts") and s["prompts"]["qwen"] != p["qwen"]:
            raise ContractError(f"{sid}: the manifest's prompt is not the card's (re-run pilot_stills extra)")
        qjobs.append({"shot": sid, "still": {"path": f"{hf}/{s['file']}", "sha256": s["sha256"]},
                      "qwen_prompt": p["qwen"], "hero_refs": p["hero_refs"], "ltx_prompt": p["ltx"]})
    return _assemble(base, qjobs, shot_of, ff15, p15_jobs)


def _assemble(base: dict, qjobs: list[dict], shot_of: dict, ff15: dict, p15_jobs: dict) -> dict:
    ltx = copy.deepcopy(base["ltx"])
    e1 = copy.deepcopy(base["ltx_jobs"][0])
    ljobs, clips = [], {}
    for stage, (_, frames, src) in CLIPS.items():
        sid = shot_of[stage]
        jid = f"pilot.{sid}.ltx25.i2v.f{frames}.s{SEED}"
        if src == "p15":
            ff = {"path": f"{P15_ROOT}/first_frames/{sid}.png", "sha256": (ff15.get(sid) or {}).get("sha256"), "pose": "start"}
        else:
            ff = {"path": f"{HF_ROOT}/first_frames/{sid}.png", "sha256": None, "pose": "start"}
        job = dict(e1, id=jid, question=QUESTION, shot_id=sid, clip_id=sid, frames=frames, seed=SEED, first_frame=ff,
                   prompt=PS.prompts(sid)["ltx"], output=f"{HF_ROOT}/ltx/{jid}.mp4")
        ljobs.append(job)
        clips[stage] = {"job": jid, "first_frame_of": sid, "from": src, "frames": frames}
    sch = schedule()
    ltx["clip_timeout_s"] = int(max(next(iter(s["on"].values()))["max_min"] for s in sch["stages"] if s["id"] in CLIPS) * 60)
    ltx["end_reserve_min"] = sch["end_reserve_min"]
    return {"schema": "p16_config/1", "question": QUESTION, "hf_root": HF_ROOT, "hf": copy.deepcopy(base["hf"]),
            "stills_manifest": copy.deepcopy(base["stills_manifest"]), "qwen": copy.deepcopy(base["qwen"]),
            "heroes_refs": copy.deepcopy(base["heroes_refs"]), "first_frame_size": list(SIZE), "qwen_jobs": qjobs, "ltx": ltx,
            "ltx_jobs": ljobs, "clips": clips, "max_ltx_failures": 2}


def schedule(ltx_s_per_frame: float | None = None, on: str = "H100 NVL", qwen_edits: int = 3, limits: dict | None = None) -> dict:
    """The RP-11 stage graph. Minutes are for the H100 NVL (the schedule divides by the card's speed); a measured LTX speed
    (seconds per frame on card ``on``) turns the clip stages into ``measured`` with a 1.5x worst case, else the estimate with 3x."""
    per_frame = LTX_MIN_PER_FRAME_EST if ltx_s_per_frame is None else ltx_s_per_frame / 60 * SPEED[on]
    mult, measured = (3.0, False) if ltx_s_per_frame is None else (1.5, True)
    st = [{"id": "weights_ltx25", "needs": [], "on": {"net": {"expected_min": 4, "max_min": 12}}, "measured": False,
           "note": "LTX-2.5 distilled only (step-3 pod 1: both LTX bases in 5.5 min, measured)"},
          {"id": "weights_qwen", "needs": [], "on": {"net": {"expected_min": 5, "max_min": 15}}, "measured": False,
           "note": "Qwen-Image-2.1 + xworld_v2 ck3000 (step-3 pod 1 had it before 14:40 UTC, not timed alone)"}]
    for stage, (shot, frames, src) in CLIPS.items():
        exp = round(frames * per_frame, 2)
        needs = ["weights_ltx25"] + (["qwen_restyle"] if src == "qwen_restyle" else [])
        whose = "the p15 pod's restyle" if src == "p15" else "this pod's restyle"
        st.append({"id": stage, "needs": needs, "on": {"gpu": {"expected_min": exp, "max_min": round(exp * mult, 1)}},
                   "measured": measured, "note": f"{frames} frames ({frames / 24:.2f} s) at 1920x1088, seed 42, from {whose} of {shot}"})
    q = round((QWEN_LOAD_S + qwen_edits * QWEN_EDIT_S) / 60, 2)
    st.append({"id": "qwen_restyle", "needs": ["weights_qwen"], "on": {"gpu": {"expected_min": q, "max_min": round(q * 3, 1)}},
               "measured": True, "note": f"{qwen_edits} edits (battle frame 200 and the two new battle stills) at 36 s + 61 s load: "
                                         "pod 1's measured Qwen speed on the H100 NVL"})
    st.append({"id": "F", "needs": list(CLIPS), "on": {"gpu": {"expected_min": 0.1, "max_min": 1}}, "measured": False,
               "note": "speeds.json + the last uploads"})
    return {"schema": "pod_schedule/1", "setup_min": 8, "end_reserve_min": 10, "lanes": {"gpu": 1, "net": 1}, "cards": copy.deepcopy(CARDS), "stages": st,
            "limits": dict(limits or LIMITS),
            "_doc": "P1 (EXEC_QUEUE.md): the rest of the 60 s pilot minute after the p15 pod. The room clips start from p15's first frames "
                    "(on HF) as soon as the LTX weights are in; Qwen's weights come second on the net lane; the three battle clips follow "
                    "the restyle of their stills. No Blender on the pod."}


def bundle(out: Path, ref: str | None = None) -> str:
    excl = LEAN.EXCLUDE
    LEAN.EXCLUDE = (*excl, "explainer_engine/training/pods/p16/p16.sh")
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
    c.add_argument("--extra", type=Path, required=True)
    c.add_argument("--stills", type=Path, required=True, help="the pinned pilot_stills.json (HF copy)")
    c.add_argument("--p15-out", type=Path)
    c.add_argument("--ltx-s-per-frame", type=float)
    c.add_argument("--on", default="A100 80GB", choices=sorted(SPEED))
    b = sub.add_parser("bundle")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--ref")
    a = ap.parse_args(argv)
    if a.cmd == "config":
        doc = config(json.loads(a.extra.read_text(encoding="utf-8")), json.loads(a.stills.read_text(encoding="utf-8")), a.p15_out)
        write_json_atomic(HERE / "p16.json", doc)
        write_json_atomic(HERE / "p16_schedule.json", schedule(a.ltx_s_per_frame, a.on))
        print(json.dumps({"qwen": [j["shot"] for j in doc["qwen_jobs"]], "ltx": [j["id"] for j in doc["ltx_jobs"]]}, indent=1))
    else:
        print(bundle(a.out, a.ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
