"""The J2/J4 spec writer (D-116, guide step 3): the route shots' LTX clips x the test matrix -> one ``ltx_job/1`` document, the
only input of the route-test pod (``training/pods/p14``). Free; no weights are touched here.

    python -m explainer_engine.edit.ltx_jobs <route_shots.json> <out ltx_jobs.json> [--layouts DIR] [--matrix M.json] [--job-id ID]

Every job is one ``ltx_pipelines.ic_lora`` generation (Lightricks/LTX-2 at the P12 code pin): a distilled checkpoint, one IC-LoRA,
the Blender layout clip(s) as ``--video-conditioning``, the Qwen first frame as ``--image`` at frame 0 (the START pose of the layout,
the creator's C1 by route, 2026-11-06 11:12 UTC), the clip's prompt. Two bases (the creator's card 11:11 UTC: J4 on both):

    ltx25  Lightricks/LTX-2.5 + the Layout-To-Render IC-LoRA (models.video_ltx_layout_lora): J2 on the clay pass, J4 on the colour pass
    ltx23  Lightricks/LTX-2.3 + the Union-Control IC-LoRA (models.video_ltx_control, reference at 0.5x): J4 on line (fore and mid
           planes only, inverted to white-on-black like the canny maps it was trained on) or a canny of the colour pass, and depth

``MATRIX`` is this writer's proposal from the guide's section 3 (battle clip A both bases x 2 seeds and both line variants, clip B
chained from A's last 8 frames, the duel x 2 seeds; 10 generations, LJ-07 caps 12); the pod's OR-23 plan (the Fable thread) decides
the real one and passes it with ``--matrix``. Prompts come from the route shots (``route_shots/draft0``, never hand-edited: their
builders write them); layout paths and hashes from ``blender/layout_passes`` manifests; a first frame is made on the pod (sha null).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from explainer_engine.blender import layout_passes as LP
from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.edit import router

SCHEMA = "ltx_job/1"
HF_ROOT = "route_test_2026-11"
SEEDS = router.SEEDS[:2]
CONTROL_STRENGTH = 0.7     # the guide's higher Union variant (0.5 / 0.7); the OR-23 plan may add 0.5
LAYOUT_STRENGTH = 1.0      # Layout-To-Render: conditioning 1.0 (guide section 3)
CHAIN_FRAMES = 8           # clip B starts from clip A's last 8 frames (the layout clips overlap by 8, layout_passes.SCENES)
BASE_LORA = {"ltx25": "video_ltx_layout_lora", "ltx23": "video_ltx_control"}
# route-shot clip -> (layout scene, layout clip) of blender/layout_passes; clips without one wait for their layout
LAYOUT_OF = {"S02-02.c1": ("battle", "battle_c1"), "S02-02.c2": ("battle", "battle_c2"), "S03-02": ("duel", "duel_c1")}
MATRIX = [
    {"clip": "S02-02.c1", "base": "ltx23", "variant": "line_foremid", "seeds": list(SEEDS)},
    {"clip": "S02-02.c1", "base": "ltx23", "variant": "canny_full", "seeds": list(SEEDS)},
    {"clip": "S02-02.c1", "base": "ltx25", "variant": "colour", "seeds": list(SEEDS)},
    {"clip": "S02-02.c2", "base": "ltx23", "variant": "line_foremid", "seeds": [SEEDS[0]], "chain": "S02-02.c1"},
    {"clip": "S02-02.c2", "base": "ltx25", "variant": "colour", "seeds": [SEEDS[0]], "chain": "S02-02.c1"},
    {"clip": "S03-02", "base": "ltx25", "variant": "clay", "seeds": list(SEEDS)},
]
# variant -> conditioning rows (pass, derive); depth rides with both Union variants
VARIANTS = {
    "clay": [("clay", None)],
    "colour": [("colour", None)],
    "line_foremid": [("line", "invert"), ("depth", None)],
    "canny_full": [("canny_full", "canny"), ("depth", None)],
}


def clips(route_shots: dict) -> dict[str, dict]:
    """clip id -> {shot_id, route, frames, fps, size, first_frame_prompt, prompt} of every J2/J4 clip of the route shots."""
    out = {}
    for s in route_shots["shots"]:
        if s.get("route") == "J4":
            for c in s["clips"]:
                out[c["clip"]] = {"shot_id": s["id"], "route": "J4", "frames": c["frames"], "fps": LP.FPS, "size": list(LP.SIZE),
                                  "first_frame_prompt": c["qwen_first_frame"], "prompt": c["ltx_restyle"]}
        elif s.get("route") == "J2":
            lt = s["ltx"]
            out[s["id"]] = {"shot_id": s["id"], "route": "J2", "frames": lt["frames"], "fps": lt["fps"], "size": list(lt["size"]),
                            "first_frame_prompt": s["prompts"]["qwen_frame"], "prompt": s["prompts"]["ltx_motion"]}
    return out


def _pin(pins: dict, key: str) -> dict:
    e = pins["models"].get(key)
    if e is None:
        raise ContractError(f"config/cloud_pins.json has no models.{key}")
    return e


def _layout(layouts: Path | None, scene: str, clip: str, kind: str) -> tuple[str, str | None]:
    path = f"{LP.HF_PREFIX}/{scene}/{kind}/{clip}_{kind}.mp4"
    if layouts is None or not (Path(layouts) / scene / "layout_manifest.json").exists():
        return path, None
    man = json.loads((Path(layouts) / scene / "layout_manifest.json").read_text(encoding="utf-8"))
    row = ((man.get("passes") or {}).get(kind) or {}).get("clips", {}).get(clip)
    return path, (row or {}).get("sha256")


def conditioning(variant: str, clip_id: str, layouts: Path | None) -> list[dict]:
    if clip_id not in LAYOUT_OF:
        raise ContractError(f"{clip_id}: no Blender layout is planned for it (layout_passes scenes: {', '.join(LP.SCENES)})")
    scene, lclip = LAYOUT_OF[clip_id]
    rows = []
    for kind, derive in VARIANTS[variant]:
        src = "colour" if kind == "canny_full" else kind     # a canny of the colour pass: every edge, background included
        path, sha = _layout(layouts, scene, lclip, src)
        strength = LAYOUT_STRENGTH if variant in ("clay", "colour") else CONTROL_STRENGTH
        row = {"pass": kind, "path": path, "sha256": sha, "strength": strength}
        if derive:
            row["derive"] = derive
        rows.append(row)
    return rows


def frames_of(clip_id: str, row: dict) -> int:
    """The layout clip's frames when the clip has a layout (the generation must match its control video), else the route shot's."""
    if clip_id in LAYOUT_OF:
        scene, lclip = LAYOUT_OF[clip_id]
        return next(c["frames"] for c in LP.plan(scene)["clips"] if c["id"] == lclip)
    return row["frames"]


def build(route_shots: dict, *, layouts: Path | str | None = None, matrix: list[dict] | None = None, pins: dict | None = None,
          job_id: str = "route_test_2026-11", code: dict | None = None) -> dict:
    from explainer_engine.cloud import pins as pins_mod
    pins = pins if pins is not None else pins_mod.load()
    code = code or _code_pin()
    rows = clips(route_shots)
    jobs, first_of = [], {}
    for m in matrix if matrix is not None else MATRIX:
        cid = m["clip"]
        if cid not in rows:
            raise ContractError(f"matrix names {cid!r}, which is no J2/J4 clip of the route shots ({', '.join(sorted(rows))})")
        r, base = rows[cid], m["base"]
        model_key, lora_key = C.LTX_BASES[base], BASE_LORA[base]
        mp, lp = _pin(pins, model_key), _pin(pins, lora_key)
        te_key = mp.get("text_encoder")
        te = _pin(pins, te_key) if te_key else None
        for seed in m["seeds"]:
            jid = f"{cid}.{base}.{m['variant']}.s{seed}"
            chain = None
            if m.get("chain"):
                prev = first_of.get((m["chain"], base, m["variant"]))
                if prev is None:
                    raise ContractError(f"{jid}: chain {m['chain']} has no earlier job on {base}/{m['variant']} in the matrix")
                chain = {"job": prev, "frames": CHAIN_FRAMES}
            jobs.append({
                "id": jid, "shot_id": r["shot_id"], "clip_id": cid, "route": r["route"], "recipe": router.ROUTE_RECIPE[r["route"]],
                "base": base, "variant": m["variant"],
                "model": {"key": model_key, "id": mp["id"], "revision": mp.get("revision"), "sha256": mp.get("sha256")},
                "text_encoder": ({"key": te_key, "id": te["id"], "revision": te.get("revision"), "sha256": te.get("sha256")}
                                 if te else None),
                "lora": {"key": lora_key, "id": lp["id"], "revision": lp.get("revision"), "file": lp["file"], "sha256": lp.get("sha256"),
                         "strength": 1.0},
                "frames": frames_of(cid, r), "fps": r["fps"], "width": r["size"][0], "height": r["size"][1], "seed": seed,
                "first_frame": {"path": f"{HF_ROOT}/first_frames/{cid}.png", "sha256": None, "pose": "start",
                                "prompt": r["first_frame_prompt"]},
                "conditioning": conditioning(m["variant"], cid, Path(layouts) if layouts else None),
                "attention_mask": None, "chain_from": chain, "prompt": r["prompt"], "stage2_ic": r["route"] == "J4",
                "output": f"{HF_ROOT}/ltx/{jid}.mp4"})
            first_of.setdefault((cid, base, m["variant"]), jid)
    doc = {"schema": SCHEMA, "job_id": job_id, "episode": route_shots.get("episode", ""), "code": code, "jobs": jobs}
    C.validate(doc)
    return doc


POD_DIR = Path(__file__).resolve().parents[1] / "training" / "pods" / "p14"
CANNY_VF = "edgedetect=low=0.1:high=0.3:mode=wires,format=gray"   # FFmpeg's Canny: white edges on black (the Union canny maps)


def pod_config(pins: dict | None = None) -> dict:
    """``training/pods/p14/p14.json``: the code pin, the vault, both bases' files with their pinned revisions and sha256 (from
    config/cloud_pins.json and the P12 file list, never typed here), the derived-control and upscale filters, the clip timeout."""
    from explainer_engine.cloud import pins as pins_mod
    from explainer_engine.finish import upscale
    pins = pins if pins is not None else pins_mod.load()
    m = pins["models"]
    p12 = json.loads((POD_DIR.parent / "p12" / "p12b.json").read_text(encoding="utf-8"))["ltx"]
    v25, v23 = m["video_ltx"], m["video_ltx_23"]
    up25 = next(f for f in p12["files"] if f.startswith("latent_upscale_models/"))
    lora = lambda k: {"repo": m[k]["id"], "revision": m[k]["revision"], "file": m[k]["file"], "sha256": m[k]["sha256"]}  # noqa: E731
    te = m[v23["text_encoder"]]
    return {
        "schema": "p14_config/1", "code": _code_pin(), "jobs_file": "ltx_jobs.json",
        "hf": {"repo": "vano1919/tmr-artifacts", "repo_type": "dataset"},
        "weights": {
            "ltx25": {"repo": v25["id"], "revision": v25["revision"],
                      "files": {f: v25["sha256_files"][f] for f in p12["files"] if f != up25},
                      "upsampler": {"file": up25, "sha256": v25["sha256_files"][up25]}, "lora": lora("video_ltx_layout_lora")},
            "ltx23": {"repo": v23["id"], "revision": v23["revision"],
                      "checkpoint": {"file": v23["file"], "sha256": v23["sha256"]},
                      "upsampler": {"file": v23["upsampler"]["file"], "sha256": v23["upsampler"]["sha256"]},
                      "lora": lora("video_ltx_control"),
                      "text_encoder": {"repo": te["id"], "revision": te["revision"], "files": te.get("sha256_files")}}},
        "controls": {"canny_vf": CANNY_VF},
        "upscale": {"vf": upscale.video_filter(1920, 1088, **upscale.ROUTE_TEST)},
        "clip_timeout_s": 1800, "end_reserve_min": 10,
    }


def _code_pin() -> dict:
    cfg = json.loads((Path(__file__).resolve().parents[1] / "training" / "pods" / "p12" / "p12b.json").read_text(encoding="utf-8"))
    return {"url": cfg["ltx"]["code"]["url"], "sha": cfg["ltx"]["code"]["sha"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("route_shots", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--layouts", type=Path)
    ap.add_argument("--matrix", type=Path)
    ap.add_argument("--job-id", default="route_test_2026-11")
    ap.add_argument("--pod", action="store_true", help="also write training/pods/p14/p14.json and the jobs copy beside it")
    a = ap.parse_args(argv)
    rs = json.loads(a.route_shots.read_text(encoding="utf-8"))
    matrix = json.loads(a.matrix.read_text(encoding="utf-8")) if a.matrix else None
    doc = build(rs, layouts=a.layouts, matrix=matrix, job_id=a.job_id)
    write_json_atomic(a.out, doc)
    if a.pod:
        write_json_atomic(POD_DIR / "p14.json", pod_config())
        write_json_atomic(POD_DIR / "ltx_jobs.json", doc)
    found = C.errors(doc)
    print(f"{len(doc['jobs'])} jobs -> {a.out}" + "".join(f"\n  {f['severity']} {f['rule']} {f['where']}: {f['detail']}" for f in found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
