"""J5 mouth variants on the p15 pod (ვანო 2026-11-06 19:36 UTC: attach to the running pod; plan
``/mnt/project-files/explainer-engine/j5_dialogue_mouth_variants/PLAN_mouth_variants.md``). 16 edits with the SAME loaded Qwen-Image-2.1 +
xworld_v2 pipeline as the 24 pictures: for each of the two hero sheets six Rhubarb mouth shapes (A-F) and two blink frames. Each edit draws
the whole sheet (1280x704, seed 11, edit cfg) and is composited back through a feathered box mask (mouth/chin box, eyes box for blinks), so
every pixel outside the box is the input sheet's own (checked: ``outside_diff_max`` = 0 in the sidecar). Every result lands as it is drawn
(OR-33): ``<out>/mouth_variants/<sheet>__<shape>.png`` + sidecar + a line in ``manifest.jsonl``.
The box rule is a reading of the J5 spec (``mouth_box_xy_w_line_jaw`` = x, y, width, line, jaw): ``edit_box`` in a sheet's entry overrides it.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEATHER = 3   # px of linear ramp inside the box edge; outside the box the mask is 0


def load_spec() -> dict:
    return json.loads((HERE / "mouth_spec.json").read_text(encoding="utf-8"))


def mouth_box(e: dict, size) -> tuple[int, int, int, int]:
    if e.get("edit_box"):
        x0, y0, x1, y1 = e["edit_box"]
    else:
        x, y, w = e["mouth_box_xy_w_line_jaw"][:3]
        x0, x1, y0, y1 = x - 0.4 * w, x + 1.4 * w, y - 0.5 * w, e["chin_y"] + 0.4 * w
    return clamp((x0, y0, x1, y1), size)


def eyes_box(e: dict, size, pad: int = 6) -> tuple[int, int, int, int]:
    xs, ys, xe, ye = [], [], [], []
    for x, y, w, h in e["eyes"]:
        xs.append(x - pad), ys.append(y - pad), xe.append(x + w + pad), ye.append(y + h + pad)
    return clamp((min(xs), min(ys), max(xe), max(ye)), size)


def clamp(b, size):
    w, h = size
    x0, y0, x1, y1 = b
    return max(0, int(x0)), max(0, int(y0)), min(w, int(round(x1))), min(h, int(round(y1)))


def mask(box, size):
    """float32 (h, w): 1 inside the box with a linear ramp over FEATHER px at its edge, exactly 0 outside."""
    import numpy as np
    w, h = size
    x0, y0, x1, y1 = box
    m = np.zeros((h, w), np.float32)
    ys, xs = np.mgrid[y0:y1, x0:x1]
    d = np.minimum.reduce([xs - x0 + 1, x1 - xs, ys - y0 + 1, y1 - ys]).astype(np.float32)
    m[y0:y1, x0:x1] = np.clip(d / FEATHER, 0.0, 1.0)
    return m


def composite(src, drawn, box):
    """``src`` where the mask is 0, ``drawn`` where it is 1, a blend on the ramp (PIL images, same size). Returns (image, outside_diff_max)."""
    import numpy as np
    from PIL import Image
    a, b = np.asarray(src.convert("RGB"), np.float32), np.asarray(drawn.convert("RGB").resize(src.size), np.float32)
    m = mask(box, src.size)[..., None]
    out = np.rint(a * (1 - m) + b * m).clip(0, 255).astype(np.uint8)
    outside = (m[..., 0] == 0)
    diff = int(np.abs(out.astype(np.int16) - np.asarray(src.convert("RGB"), np.int16))[outside].max()) if outside.any() else 0
    return Image.fromarray(out), diff


def jobs(spec: dict | None = None) -> list[dict]:
    spec = spec or load_spec()
    out = []
    for sheet, e in spec["sheets"].items():
        for k, d in spec["shapes"].items():
            out.append({"name": f"{sheet}__{k}", "sheet": sheet, "kind": "mouth", "change": d, "box": mouth_box(e, spec["size"]),
                        "prompt": f"{e['prompt']} Same person, same pose, same drawing; only the mouth changes: {d}. Everything else identical."})
        for k, d in spec["blinks"].items():
            out.append({"name": f"{sheet}__{k}", "sheet": sheet, "kind": "blink", "change": d, "box": eyes_box(e, spec["size"]),
                        "prompt": f"{e['prompt']} Same person, same pose, same drawing; only the eyes change: {d}. Everything else identical."})
    return out


def fetch_sheet(spec: dict, sheet: str, work: Path) -> Path:
    from huggingface_hub import hf_hub_download
    p = Path(hf_hub_download("vano1919/tmr-artifacts", f"{spec['hf']}/{sheet}.png", repo_type="dataset", local_dir=str(work)))
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != spec["sheets"][sheet]["png_sha256"]:
        raise ValueError(f"{sheet}: sha256 {got} is not the pinned {spec['sheets'][sheet]['png_sha256']}")
    return p


def run_all(pipe, cfg: dict, out: Path, work: Path, say, draw, max_streak: int = 3) -> tuple[int, int]:
    """Draws every variant with the loaded pipeline (``draw`` = p14_qwen.draw). Returns (made, failed); stops after ``max_streak`` failures in a row."""
    from PIL import Image
    spec = load_spec()
    md = Path(out) / "mouth_variants"
    md.mkdir(parents=True, exist_ok=True)
    made = failed = streak = 0
    for j in jobs(spec):
        p = md / f"{j['name']}.png"
        if p.exists():
            continue
        t1 = time.time()
        try:
            src = Image.open(fetch_sheet(spec, j["sheet"], work)).convert("RGB")
            dj = {"prompt": j["prompt"], "seed": spec["seed"], "cfg": spec["cfg"], "size": spec["size"]}
            im, diff = composite(src, draw(pipe, cfg, dj, [src]).convert("RGB"), j["box"])
            if diff:
                raise ValueError(f"pixels outside the box changed by {diff}")
        except Exception as e:   # noqa: BLE001 - one failed variant must not end the stage
            failed += 1
            streak += 1
            say("FAIL", j["name"], repr(e)[:300])
            with open(md / "manifest.jsonl", "a") as f:
                f.write(json.dumps({"name": j["name"], "status": "failed", "error": repr(e)[:300]}) + "\n")
            if streak >= max_streak:
                say("STOP:", streak, "mouth variants failed in a row")
                break
            continue
        streak = 0
        im.save(p)
        side = {"name": j["name"], "sheet": j["sheet"], "kind": j["kind"], "change": j["change"], "box": list(j["box"]), "prompt": j["prompt"],
                "seed": spec["seed"], "cfg": spec["cfg"], "size": spec["size"], "outside_diff_max": diff, "seconds": round(time.time() - t1, 1),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "status": "ok", "lora": cfg["qwen"]["style_lora"]}
        p.with_suffix(".json").write_text(json.dumps(side, indent=1, ensure_ascii=False), encoding="utf-8")
        with open(md / "manifest.jsonl", "a") as f:
            f.write(json.dumps(side, ensure_ascii=False) + "\n")
        made += 1
        say("made", j["name"], side["seconds"], "s")
    return made, failed
