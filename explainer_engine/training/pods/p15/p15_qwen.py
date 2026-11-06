"""The pilot pod (PILOT_1MIN_PLAN.md v3, the creator 2026-11-06 15:25 / 16:05 UTC): Qwen-Image-2.1 + xworld_v2 checkpoint 3000 at
0.7 restyles each Blender still of the pilot (HF ``route_test_2026-11/pilot/blender/``, pinned by sha256 in ``p15.json``) as a
multi-image edit: Image 1 the still (it carries places, sizes and poses), then the hero sheets the shot card names, with the prompt
``blender/pilot_stills.prompts`` generated from that card. 1280x720 out; the LTX first frame of every picture is written at 1920x1088
(``first_frames/<shot>.png``). The loader, the LoRA merge and the draw call are the step-3 pod's (``p14/p14_qwen.py``: ``style_lora``,
``draw``, ``first_frame``, ``resolve_ref``). Every picture lands as it is drawn: ``<out>/qwen/<shot>.png`` + its sidecar + a line in
``<out>/qwen/manifest.jsonl`` (OR-33). One failed picture is logged and the next one runs.

    python3 -m explainer_engine.training.pods.p15.p15_qwen --out <EE_OUT> --assets <dir> [--list]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from explainer_engine.training.pods.p14 import p14_qwen as Q

HERE = Path(__file__).resolve().parent


def load_cfg() -> dict:
    return json.loads((HERE / "p15.json").read_text(encoding="utf-8"))


MAX_FAIL_STREAK = 3   # pictures failing in a row before the stage ends (a card that cannot hold the model fails every one)
LOOKS = ("S1", "S2", "S3")   # the three look variants of --variants (pilot_stills.QWEN_LOOK), same seed and LoRA


def jobs(cfg: dict, variants: bool = False) -> list[dict]:
    """The pictures: one per still, or with ``variants`` three per still (``<shot>__S1`` .. ``__S3``, Fable 18:00 UTC), the prompt
    ``pilot_stills.qwen_variant`` (the card's words plus the look clauses that fit under 90 words), everything else identical."""
    q = cfg["qwen"]
    if not variants:
        return [{"name": j["shot"], "stage": "pilot", "prompt": j["qwen_prompt"], "seed": q["seed"], "cfg": q["cfg_edit"], "size": q["size"],
                 "kind": "edit", "clip": j["shot"], "still": j["still"], "refs": [("hero", h) for h in j["hero_refs"]]}
                for j in cfg["qwen_jobs"]]
    from explainer_engine.blender import pilot_stills as PS
    out = []
    for j in cfg["qwen_jobs"]:
        for s in LOOKS:
            prompt = PS.qwen_variant(j["shot"], s)
            if s == "S3" and prompt != j["qwen_prompt"]:
                raise ValueError(f"{j['shot']}: S3 must be the card's prompt")
            out.append({"name": f"{j['shot']}__{s}", "stage": "pilot", "prompt": prompt, "seed": q["seed"], "cfg": q["cfg_edit"],
                        "size": q["size"], "kind": "edit", "clip": f"{j['shot']}__{s}", "still": j["still"],
                        "refs": [("hero", h) for h in j["hero_refs"]], "look": s})
    return out


def fetch_still(cfg: dict, still: dict, work: Path) -> Path:
    """The Blender still from the vault, held to its pinned sha256."""
    from huggingface_hub import hf_hub_download
    p = Path(hf_hub_download(cfg["hf"]["repo"], still["path"], repo_type=cfg["hf"]["repo_type"], local_dir=str(work)))
    got = Q.sha256_file(p)
    if got != still["sha256"]:
        raise ValueError(f"{still['path']}: sha256 {got} is not the pinned {still['sha256']}")
    return p


def run(out: Path, assets: Path, work: Path = Path("/workspace/pilot_in"), variants: bool = False) -> int:
    cfg = load_cfg()
    out = Path(out)
    qd = out / "qwen"
    qd.mkdir(parents=True, exist_ok=True)
    log = open(qd / "qwen.log", "a")

    def say(*a):
        line = time.strftime("%H:%M:%S ") + " ".join(map(str, a))
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    os.environ.setdefault("XW_GPU_MODE", cfg["qwen"]["gpu_mode"])
    sys.path.insert(0, str(HERE.parent))
    import xworld_v1_test as t
    from PIL import Image
    t0 = time.time()
    pipe, tr = t.load_pipeline()
    pipe = Q.style_lora(t, pipe, tr, cfg, say)
    say("loaded in", round(time.time() - t0), "s")
    made = failed = streak = 0
    for j in jobs(cfg, variants):
        p = qd / f"{j['name']}.png"
        if p.exists():
            continue
        t1 = time.time()
        try:
            sp = fetch_still(cfg, j["still"], work)
            refs, rows = [Image.open(sp).convert("RGB")], [{"ref": "still", "path": j["still"]["path"], "sha256": j["still"]["sha256"]}]
            for label, key in j["refs"]:
                rp, sha = Q.resolve_ref(cfg, label, key, work, assets)
                refs.append(Image.open(rp).convert("RGB"))
                rows.append({"ref": key, "path": str(rp), "sha256": sha})
            im = Q.draw(pipe, cfg, j, refs).convert("RGB")
        except Exception as e:   # noqa: BLE001 - one failed picture must not end the stage
            failed += 1
            streak += 1
            say("FAIL", j["name"], repr(e)[:300])
            with open(qd / "manifest.jsonl", "a") as f:
                f.write(json.dumps({"name": j["name"], "status": "failed", "error": repr(e)[:300]}) + "\n")
            if streak >= MAX_FAIL_STREAK:   # e.g. 48 GB out of memory: every picture would fail, the card would only bill
                say("STOP: ", streak, "pictures failed in a row; ending the stage so the pod can stop")
                break
            continue
        streak = 0
        im.save(p)
        ff = out / "first_frames" / f"{j['clip']}.png"
        ff.parent.mkdir(parents=True, exist_ok=True)
        Q.first_frame(im, cfg["first_frame_size"]).save(ff)
        side = {k: j[k] for k in ("name", "stage", "prompt", "seed", "cfg", "size", "kind")}
        side.update(question=cfg["question"], words=len(j["prompt"].split()), refs=rows, steps=cfg["qwen"]["steps"],
                    negative=cfg["qwen"]["negative"], lora=cfg["qwen"]["style_lora"], seconds=round(time.time() - t1, 1),
                    sha256=Q.sha256_file(p), status="ok",
                    first_frame={"path": f"first_frames/{j['clip']}.png", "sha256": Q.sha256_file(ff), "size": cfg["first_frame_size"]})
        p.with_suffix(".json").write_text(json.dumps(side, indent=1, ensure_ascii=False), encoding="utf-8")
        with open(qd / "manifest.jsonl", "a") as f:
            f.write(json.dumps(side, ensure_ascii=False) + "\n")
        made += 1
        say("made", j["name"], side["seconds"], "s")
    say("qwen done", made, "made", failed, "failed")
    return 0 if made else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="pilot pod: the Qwen restyle of the Blender stills")
    ap.add_argument("--out", type=Path, default=Path(os.environ.get("EE_OUT", "/workspace/out")))
    ap.add_argument("--assets", type=Path, default=Path("/workspace/assets"))
    ap.add_argument("--list", action="store_true", help="print the pictures, no GPU")
    ap.add_argument("--variants", action="store_true", help="three look variants per still (S1, S2, S3), 24 pictures")
    a = ap.parse_args(argv)
    if a.list:
        for j in jobs(load_cfg(), a.variants):
            print(j["name"], j["size"], len(j["prompt"].split()), "words", j["still"]["path"], [r[1] for r in j["refs"]])
        return 0
    return run(a.out, a.assets, variants=a.variants)


if __name__ == "__main__":
    sys.exit(main())
