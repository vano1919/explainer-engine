"""The lean step-3 pod, stages B and C (STEP3_POD_PLAN_LEAN_ka.md section 1): Qwen-Image-2.1 + xworld_v2 checkpoint 3000 at 0.7 on
the pod's card, one process for both stages (the model loads once; the process ends before the cutouts and LTX, which frees the card).

- B: the first layout frame of the battle and of the duel, drawn as a line drawing by Blender (stage A), plus the hero sheet(s), as
  references of a Qwen edit with the scene's 40-90 word moment, 1280x720. Question: does Qwen keep Blender's proportions and placement?
  Each picture gets ``line_match`` (the share of the layout's line pixels that have an edge of the picture within ``line_match_px``)
  and is also written as the LTX first frame of its clip at 1920x1088 (``first_frames/<clip>.png``: B is the only source of them).
- C: two text-to-image pictures from ~150-word prompts (the asset pod's 90-word D4_rain and D2_duel extended with proportion and setting
  detail, no camera or size words). Question: does the style hold at 150 words, and do the crowd clones go or stay?

Provenance: ``draw`` and ``style_lora`` are the asset pod's ``draw`` and ``pod_loras`` (PR #140, branch claude/project-thread-4i756j
@af06ad9, ``training/pods/route/route_assets.py``) cut to the one style LoRA (no panorama LoRA here); the loader is
``training/pods/xworld_v1_test.py`` (``load_pipeline``, ``Loras.gate_up``) as there. Every picture: ``<out>/qwen/<name>.png`` + its sidecar
(prompt, seed, cfg, size, refs with sha256, seconds) and a line in ``<out>/qwen/manifest.jsonl`` as soon as it is drawn (OR-33: the
wrapper uploads the folder). One failed picture is logged and the next one runs.

- X6 (the creator's card 13:33 UTC): the travel shot S04-01's still (t2i), also written as its LTX first frame; X4: the fix edit
  "change nothing else; fix: ..." of one assembled J5 frame of stage G (references: that frame + the hero sheet), in a second session
  after the LTX stage (``--layouts`` is then the step3 folder that holds ``j5/``).

    python3 -m explainer_engine.training.pods.p14.p14_qwen --stages B,C,X6 --out <step3 dir> --layouts <dir> --assets <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cfg() -> dict:
    return json.loads((HERE / "p14_stages.json").read_text(encoding="utf-8"))


def layout_frame(layouts: Path, scene: str, kind: str, frame: int) -> Path:
    """The PNG of one layout frame as ``blender/layout_passes`` writes it (``<out>/<scene>/<pass>/frames/frame_NNNNNN.png``)."""
    from_name = f"frame_{frame:06d}.png"
    return Path(layouts) / scene / kind / "frames" / from_name


def jobs(cfg: dict, stages: list[str], scene: str | None = None) -> list[dict]:
    """The pictures of the asked stages as dicts: name, stage, prompt, seed, cfg, size, refs [(label, path key)], kind. ``scene``
    keeps only B's edits of that layout scene (the pod runs B per scene, as each scene's frame 0 lands)."""
    q, out = cfg["qwen"], []
    if "B" in stages:
        for j in cfg["B"]["jobs"]:
            if scene and j["layout"]["scene"] != scene:
                continue
            out.append({"name": j["name"], "stage": "B", "prompt": j["prompt"], "seed": q["seed"], "cfg": q["cfg_edit"],
                        "size": q["size"], "kind": "edit", "clip": j["clip"],
                        "refs": [("layout", j["layout"])] + [("hero", h) for h in j["heroes"]]})
    if "X6" in stages:   # the creator's card 13:33 UTC, X6: the travel shot's still (its camera move and its LTX i2v follow)
        x = cfg["X"]["X6"]
        out.append({"name": x["still"]["name"], "stage": "X6", "prompt": x["still"]["prompt"], "seed": x["still"]["seed"],
                    "cfg": q["cfg_text"], "size": q["size"], "kind": "t2i", "refs": [], "clip": x["shot"],
                    "question": x["question"]})
    if "X4" in stages:   # X4: the fix edit of one assembled J5 frame (stage G), after the LTX stage
        x = cfg["X"]["X4"]
        out.append({"name": f"X4_{x['frame_from_g']['shot']}_f{x['frame_from_g']['frame']}_fix", "stage": "X4", "prompt": x["prompt"],
                    "seed": x["seed"], "cfg": x["cfg"], "size": q["size"], "kind": "edit", "question": x["question"],
                    "refs": [("g_frame", x["frame_from_g"])] + [("hero", h) for h in x["heroes"]]})
    if "C" in stages:
        for j in cfg["C"]["jobs"]:
            out.append({"name": j["name"], "stage": "C", "prompt": j["prompt"], "seed": q["seed"], "cfg": q["cfg_text"],
                        "size": q["size"], "kind": "t2i", "refs": [], "from": j["from"]})
    return out


# --- pure picture helpers (numpy + PIL): tested off the pod -------------------------------------------------------------------

def edges(rgb, *, thresh: float = 40.0):
    """A boolean edge map: the gradient magnitude of the luma (Sobel-like 3x3 differences) above ``thresh`` (0..255 scale)."""
    import numpy as np
    a = np.asarray(rgb, dtype=np.float32)
    y = a[..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32) if a.ndim == 3 else a
    p = np.pad(y, 1, mode="edge")
    gx = (p[1:-1, 2:] - p[1:-1, :-2]) + 0.5 * (p[:-2, 2:] - p[:-2, :-2] + p[2:, 2:] - p[2:, :-2])
    gy = (p[2:, 1:-1] - p[:-2, 1:-1]) + 0.5 * (p[2:, :-2] - p[:-2, :-2] + p[2:, 2:] - p[:-2, 2:])
    return np.hypot(gx, gy) > thresh


def dilate(mask, px: int):
    import numpy as np
    m = mask.copy()
    for _ in range(px):
        p = np.pad(m, 1)
        m = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return m


def line_match(layout_line, picture, *, px: int = 3) -> dict:
    """How much of the layout's drawing the picture keeps: ``kept`` = the share of the layout's ink pixels (dark lines on white) that
    have an edge of the picture within ``px`` pixels; ``extra`` = the share of the picture's edges with no layout line within ``px``
    (new shapes Qwen added). Both pictures are compared at the picture's size. Numbers for the verdict page, no threshold here."""
    import numpy as np
    from PIL import Image
    pic = picture.convert("RGB")
    lay = layout_line.convert("L").resize(pic.size, Image.BILINEAR)
    ink = np.asarray(lay, dtype=np.float32) < 128
    e = edges(pic)
    if not ink.any():
        return {"kept": None, "extra": None, "px": px, "ink_pixels": 0}
    kept = float((ink & dilate(e, px)).sum() / ink.sum())
    extra = float((e & ~dilate(ink, px)).sum() / max(int(e.sum()), 1))
    return {"kept": round(kept, 4), "extra": round(extra, 4), "px": px, "ink_pixels": int(ink.sum()), "edge_pixels": int(e.sum())}


def first_frame(picture, size):
    """The LTX first frame of a clip: the picture scaled to cover ``size`` and cut to it from the centre (1280x720 -> 1920x1088
    keeps the full width and drops 4 rows top and bottom)."""
    from PIL import Image
    w, h = size
    s = max(w / picture.width, h / picture.height)
    im = picture.convert("RGB").resize((round(picture.width * s), round(picture.height * s)), Image.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


# --- the pod side ---------------------------------------------------------------------------------------------------------------

def style_lora(t, pipe, tr, cfg, say):
    """Merges the style LoRA once (the asset pod's ``pod_loras`` with the style LoRA only), checked against its sha256."""
    import torch
    from huggingface_hub import hf_hub_download
    from videox_fun.utils import merge_lora
    s = cfg["qwen"]["style_lora"]
    path = hf_hub_download(s["hf"], s["path"], repo_type="dataset")
    if sha256_file(path) != s["sha256"]:
        raise SystemExit("style LoRA sha256 mismatch: not the checkpoint the creator approved")
    L = t.Loras(pipe, tr, {"style": path}, say)
    L.pipe = merge_lora(L.pipe, path, s["weight"], device="cuda", dtype=torch.bfloat16)
    say("lora style", s["weight"], "gate_up", L.gate_up(path, s["weight"]))
    return L.pipe


def draw(pipe, cfg, j, refs):
    import torch
    q = cfg["qwen"]
    g = torch.Generator(device="cuda").manual_seed(j["seed"])
    with torch.no_grad():
        return pipe(j["prompt"], image=refs or None, negative_prompt=q["negative"], height=j["size"][1], width=j["size"][0],
                    generator=g, num_inference_steps=q["steps"], true_cfg_scale=j["cfg"]).images[0]


def resolve_ref(cfg, label, key, layouts: Path, assets: Path):
    """(path, sha256) of one reference: a layout frame of stage A, or a hero sheet of the asset pod (held to its pinned sha256)."""
    if label == "g_frame":   # a frame of stage G: <out>/j5/<shot>/frames/frame_NNNNNN.png (``layouts`` is the step3 dir here)
        p = Path(layouts) / "j5" / key["shot"] / "frames" / f"frame_{key['frame']:06d}.png"
        if not p.exists():
            raise FileNotFoundError(f"stage G frame {p} is missing")
        return p, sha256_file(p)
    if label == "layout":
        p = layout_frame(layouts, key["scene"], key["pass"], key["frame"])
        if not p.exists():
            raise FileNotFoundError(f"layout frame {p} (stage A) is missing")
        return p, sha256_file(p)
    ref = next(r for r in cfg["heroes_refs"] if r["name"] == key)
    p = Path(assets) / ref["path"].split("/", 1)[1]
    if not p.exists():
        from huggingface_hub import hf_hub_download
        p = Path(hf_hub_download("vano1919/tmr-artifacts", ref["path"], repo_type="dataset", local_dir=str(assets)))
    got = sha256_file(p)
    if got != ref["sha256"]:
        raise ValueError(f"{key}: sha256 {got} is not the pinned {ref['sha256']}")
    return p, got


def run(stages, out: Path, layouts: Path, assets: Path, scene: str | None = None) -> int:
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
    pipe = style_lora(t, pipe, tr, cfg, say)
    say("loaded in", round(time.time() - t0), "s")
    made = failed = 0
    for j in jobs(cfg, stages, scene):
        p = qd / f"{j['name']}.png"
        if p.exists():
            continue
        t1 = time.time()
        try:
            refs, ref_rows = [], []
            for label, key in j["refs"]:
                rp, sha = resolve_ref(cfg, label, key, layouts, assets)
                refs.append(Image.open(rp).convert("RGB"))
                ref_rows.append({"ref": label, "path": str(rp), "sha256": sha})
            im = draw(pipe, cfg, j, refs).convert("RGB")
        except Exception as e:   # noqa: BLE001 - one failed picture must not end the stage
            failed += 1
            say("FAIL", j["name"], repr(e)[:300])
            with open(qd / "manifest.jsonl", "a") as f:
                f.write(json.dumps({"name": j["name"], "stage": j["stage"], "status": "failed", "error": repr(e)[:300]}) + "\n")
            continue
        im.save(p)
        side = {k: j[k] for k in ("name", "stage", "prompt", "seed", "cfg", "size", "kind")}
        side["question"] = j.get("question") or (cfg.get(j["stage"]) or {}).get("question")
        side.update(words=len(j["prompt"].split()), refs=ref_rows, steps=cfg["qwen"]["steps"], negative=cfg["qwen"]["negative"],
                    lora=cfg["qwen"]["style_lora"], seconds=round(time.time() - t1, 1), sha256=sha256_file(p), status="ok")
        if j["stage"] == "B":
            side["line_match"] = line_match(refs[0], im, px=cfg["B"]["line_match_px"])
        if j["stage"] in ("B", "X6"):   # B's pictures and X6's still are the only first frames of their LTX clips
            ff = out / "first_frames" / f"{j['clip']}.png"
            ff.parent.mkdir(parents=True, exist_ok=True)
            first_frame(im, cfg["B"]["first_frame_size"]).save(ff)
            side["first_frame"] = {"path": f"first_frames/{j['clip']}.png", "sha256": sha256_file(ff),
                                   "size": cfg["B"]["first_frame_size"]}
        p.with_suffix(".json").write_text(json.dumps(side, indent=1, ensure_ascii=False), encoding="utf-8")
        with open(qd / "manifest.jsonl", "a") as f:
            f.write(json.dumps(side, ensure_ascii=False) + "\n")
        made += 1
        say("made", j["name"], side["seconds"], "s", side.get("line_match", ""))
    say("qwen done", made, "made", failed, "failed")
    return 0 if made else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lean step-3 pod: Qwen stages B and C")
    ap.add_argument("--stages", default="B,C,X6")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--layouts", type=Path, required=True)
    ap.add_argument("--assets", type=Path, required=True)
    ap.add_argument("--list", action="store_true", help="print the pictures, no GPU")
    ap.add_argument("--scene", help="B: only the edits of this layout scene")
    a = ap.parse_args(argv)
    st = a.stages.split(",")
    if a.list:
        for j in jobs(load_cfg(), st, a.scene):
            print(j["stage"], j["name"], j["kind"], j["size"], len(j["prompt"].split()), "words", [r[1] for r in j["refs"]])
        return 0
    return run(st, a.out, a.layouts, a.assets, a.scene)


if __name__ == "__main__":
    sys.exit(main())
