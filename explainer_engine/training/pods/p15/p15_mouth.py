"""The mouth-variant job for the J5 dialogue (the creator, 2026-11-06 19:40 UTC: "same pod"): Qwen-Image-Edit through the pilot pod's loader
(Qwen-Image-2.1 + xworld_v2 ck3000 at 0.7, ``p14_qwen.style_lora`` / ``draw``) redraws, on the two hero sheets of the dialogue
(``B_H2_right34`` scout, ``B_H1_left34`` commander), the six Rhubarb mouth shapes A-F and two blink frames, 16 pictures in all.
The edit is MASKED: a context crop around the feature goes to Qwen (upscaled x3), the answer is shrunk back and composited into the full sheet
through a soft ellipse mask, and every pixel outside the mask support is bit-identical to the input; the job checks this itself and fails the
picture when a single pixel differs (``check_outside``). Inputs (sheets, cut-outs, masks) are pinned by sha256 in ``p15_mouth.json`` and fetched
from HF ``route_test_2026-11/j5_dialogue/mouth_variants_input/``. Outputs: ``<out>/qwen/mouth/<hero>__<shape>.png`` (the full sheet, RGB) + sidecar
+ a line in ``<out>/qwen/mouth/manifest.jsonl`` (OR-33); one failed picture is logged and the next one runs.

Numbers for the schedule (an ESTIMATE, nothing measured yet): the step-3 pod measured 36 s per 1280x720 edit with two references on the H100 NVL
(p15q_schedule.json). One 960x672 crop with one reference is about 0.7 of those pixels and one reference fewer: ~20 s per edit on that card,
~5.5 min for 16, plus 61 s to load the model when it is not already loaded by the restyle stage (run in the same process to save it).
VRAM: the same model and offload mode as the restyle stage (``model_cpu_offload``), so the same cards fit. Jobs: 16.

    python3 -m explainer_engine.training.pods.p15.p15_mouth --out <EE_OUT> [--list]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from explainer_engine.training.pods.p14 import p14_qwen as Q

HERE = Path(__file__).resolve().parent
MAX_FAIL_STREAK = 3
CROP = {"mouth": (320, 224), "blink": (352, 192)}      # context window in sheet pixels around the feature (Qwen needs a face, not a lip)

# one clause per tag, every tag once (the shot-card rule); the whole prompt stays far under 90 words
SHAPE_TAGS = {
    "A": "lips closed in a relaxed straight line",
    "B": "lips slightly parted with a thin dark gap and the upper teeth just visible",
    "C": "mouth open to a medium oval with a dark inside and the tongue low",
    "D": "mouth wide open with the jaw dropped and the tongue showing",
    "E": "lips rounded into a small O",
    "F": "lips pursed forward as when saying oo",
    "blink_half": "eyelids half closed over both eyes",
    "blink_full": "eyes fully closed, each lid one curved lash line",
}
FRAME = ("Redraw only the {part} of the character in this crop: {tag}. Keep the same face, skin, beard, hair, ink line weight, colours and "
         "lighting, and change nothing else.")


def load_cfg() -> dict:
    return json.loads((HERE / "p15_mouth.json").read_text(encoding="utf-8"))


def prompt(kind_tag: str) -> str:
    part = "eyes" if kind_tag.startswith("blink") else "mouth"
    return FRAME.format(part=part, tag=SHAPE_TAGS[kind_tag])


def jobs(cfg: dict) -> list[dict]:
    out = []
    for hero in cfg["heroes"]:                                   # H2 (scout) first: his lines come first in the clip
        for tag in list(cfg["shapes"]) + list(cfg["blinks"]):
            kind = "blink" if tag.startswith("blink") else "mouth"
            out.append({"name": f"{hero}__{tag}", "hero": hero, "tag": tag, "kind": kind, "prompt": prompt(tag),
                        "seed": cfg["seed_base"] + len(out), "cfg": cfg["cfg"], "stage": "mouth"})
    return out


def feature_mask(hero: dict, kind: str, shape=(704, 1280)) -> np.ndarray:
    """Soft mask (0..1, float32) of the area Qwen may change, in sheet pixels; exactly 0 outside its support."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = np.zeros(shape, np.float32)
    if kind == "mouth":
        cx, cy, mw, line, jaw = hero["mouth"]
        ax, ay = mw * 0.85 + 6, max(14.0, jaw * 2.5)
        ellipses = [(cx, cy + jaw * 0.5, ax, ay)]
    else:
        ellipses = [(cx, cy, ew * 0.8 + 4, eh * 1.4 + 3) for cx, cy, ew, eh in hero["eyes"]]
    for cx, cy, ax, ay in ellipses:
        r = np.sqrt(((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2)
        m = np.maximum(m, np.clip((1.0 - r) * min(ax, ay) / 3.0, 0.0, 1.0))      # 3 px feather inside the ellipse edge
    return m


def crop_box(hero: dict, kind: str, shape=(704, 1280)) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) of the context window, centred on the feature and kept inside the sheet."""
    h, w = shape
    cw, ch = CROP[kind]
    if kind == "mouth":
        cx, cy = hero["mouth"][0], hero["mouth"][1] + hero["mouth"][4] * 0.5
    else:
        cx = sum(e[0] for e in hero["eyes"]) / len(hero["eyes"])
        cy = sum(e[1] for e in hero["eyes"]) / len(hero["eyes"])
    x0 = int(min(max(round(cx - cw / 2), 0), w - cw))
    y0 = int(min(max(round(cy - ch / 2), 0), h - ch))
    return x0, y0, x0 + cw, y0 + ch


def composite(sheet: np.ndarray, edited_crop: np.ndarray, box, mask: np.ndarray) -> np.ndarray:
    """The sheet with the edited crop mixed in through ``mask``; pixels where the mask is 0 are copied, never recomputed."""
    x0, y0, x1, y1 = box
    out = sheet.copy()
    m = mask[y0:y1, x0:x1]
    mixed = sheet[y0:y1, x0:x1].astype(np.float32) * (1 - m[..., None]) + edited_crop.astype(np.float32) * m[..., None]
    region = out[y0:y1, x0:x1]
    sel = m > 0
    region[sel] = np.clip(np.rint(mixed[sel]), 0, 255).astype(sheet.dtype)
    return out


def check_outside(before: np.ndarray, after: np.ndarray, mask: np.ndarray) -> int:
    """Number of pixels that differ outside the mask support; the job fails the picture unless it is 0."""
    diff = np.any(before != after, axis=-1)
    return int(np.count_nonzero(diff & (mask <= 0)))


def fetch(cfg: dict, hero: dict, work: Path) -> dict[str, Path]:
    from huggingface_hub import hf_hub_download
    got = {}
    for key, f in hero["files"].items():
        p = Path(hf_hub_download(cfg["hf"]["repo"], f["path"], repo_type=cfg["hf"]["repo_type"], local_dir=str(work)))
        sha = Q.sha256_file(p)
        if sha != f["sha256"]:
            raise ValueError(f"{f['path']}: sha256 {sha} is not the pinned {f['sha256']}")
        got[key] = p
    return got


def redraw(pipe, cfg: dict, j: dict, sheet_rgb, hero: dict):
    """One masked edit: returns (full sheet RGB array, mask, pixels changed outside)."""
    from PIL import Image
    arr = np.asarray(sheet_rgb.convert("RGB"))
    box = crop_box(hero, j["kind"], arr.shape[:2])
    x0, y0, x1, y1 = box
    k = cfg["scale"]
    crop = Image.fromarray(arr[y0:y1, x0:x1]).resize(((x1 - x0) * k, (y1 - y0) * k), Image.LANCZOS)
    jj = dict(j, size=[crop.size[0], crop.size[1]])
    ed = Q.draw(pipe, cfg_for_draw(cfg), jj, [crop]).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS)
    mask = feature_mask(hero, j["kind"], arr.shape[:2])
    out = composite(arr, np.asarray(ed), box, mask)
    return out, mask, check_outside(arr, out, mask)


def cfg_for_draw(cfg: dict) -> dict:
    """``p14_qwen.draw`` reads steps and the negative prompt from the pilot config's qwen block."""
    q = json.loads((HERE / "p15.json").read_text(encoding="utf-8"))["qwen"]
    return {"qwen": q}


def run(out: Path, work: Path = Path("/workspace/mouth_in")) -> int:
    cfg = load_cfg()
    pilot = json.loads((HERE / "p15.json").read_text(encoding="utf-8"))
    out = Path(out)
    qd = out / cfg["out_dir"]
    qd.mkdir(parents=True, exist_ok=True)
    log = open(qd / "mouth.log", "a")

    def say(*a):
        line = time.strftime("%H:%M:%S ") + " ".join(map(str, a))
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    os.environ.setdefault("XW_GPU_MODE", pilot["qwen"]["gpu_mode"])
    sys.path.insert(0, str(HERE.parent))
    import xworld_v1_test as t
    from PIL import Image
    t0 = time.time()
    pipe, tr = t.load_pipeline()
    pipe = Q.style_lora(t, pipe, tr, pilot, say)
    say("loaded in", round(time.time() - t0), "s")
    made = failed = streak = 0
    for j in jobs(cfg):
        p = qd / f"{j['name']}.png"
        if p.exists():
            continue
        t1 = time.time()
        try:
            hero = cfg["heroes"][j["hero"]]
            files = fetch(cfg, hero, work)
            res, mask, bad = redraw(pipe, cfg, j, Image.open(files["sheet"]), hero)
            if bad:
                raise ValueError(f"{bad} pixels changed outside the mask")
        except Exception as e:   # noqa: BLE001 - one failed picture must not end the stage
            failed += 1
            streak += 1
            say("FAIL", j["name"], repr(e)[:300])
            with open(qd / "manifest.jsonl", "a") as f:
                f.write(json.dumps({"name": j["name"], "status": "failed", "error": repr(e)[:300]}) + "\n")
            if streak >= MAX_FAIL_STREAK:
                say("STOP:", streak, "pictures failed in a row; ending the stage so the pod can stop")
                break
            continue
        streak = 0
        Image.fromarray(res).save(p)
        side = {k: j[k] for k in ("name", "hero", "tag", "kind", "prompt", "seed", "cfg")}
        side.update(question=cfg["question"], words=len(j["prompt"].split()), sheet=hero["files"]["sheet"],
                    outside_mask_changed=0, seconds=round(time.time() - t1, 1), sha256=Q.sha256_file(p), status="ok")
        p.with_suffix(".json").write_text(json.dumps(side, indent=1), encoding="utf-8")
        with open(qd / "manifest.jsonl", "a") as f:
            f.write(json.dumps(side) + "\n")
        made += 1
        say("made", j["name"], side["seconds"], "s")
    say("mouth done", made, "made", failed, "failed")
    return 0 if made else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="J5 dialogue: masked Qwen edits of the mouth shapes and blinks")
    ap.add_argument("--out", type=Path, default=Path(os.environ.get("EE_OUT", "/workspace/out")))
    ap.add_argument("--list", action="store_true", help="print the pictures, no GPU")
    a = ap.parse_args(argv)
    if a.list:
        for j in jobs(load_cfg()):
            print(j["name"], j["seed"], len(j["prompt"].split()), "words")
        return 0
    return run(a.out)


if __name__ == "__main__":
    sys.exit(main())
