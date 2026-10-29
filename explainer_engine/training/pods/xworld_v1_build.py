"""Builds the xworld_v1 training folders and config on the pod from the material manifest and the reviewed captions (D-80).

One LoRA on Qwen-Image-2.1 learns the style and the scene sequence together (LT-69):
* ``style/``: every single frame, caption ``xworld style, <description>`` (plain text-to-image);
* ``pairs/target`` + ``pairs/control``: shot -> next shot of one scene and start -> end of one shot; the target's caption is
  ``xworld style, <description of the target>. <change line>`` and the control picture (same file name, LT-08) is the frame
  before it (2.1 edits when the dataset has a control path).
The trigger is written into every caption file because ai-toolkit cannot add it to cached text embeddings (LT-13).
Held-out scenes never reach a training folder (LT-76): ``build`` refuses when one does.
Sample prompts (LT-12, LT-75): 2 held-out descriptions, the first of them again without the trigger, 1 held-out edit
(real first frame + the change line to the next), 2 new subjects; fixed seed.

    python xworld_v1_build.py <dataset dir> <captions_reviewed.jsonl> <out ds dir> <cfg template> <cfg out>
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

TRIGGER = "xworld style"  # ვანო 2026-10-26 02:15 Tbilisi ("ყველა კი" to the night plan)
NEW_SUBJECTS = [
    "a crowded medieval market square at noon, a baker in an apron arguing with a knight in dented armour, "
    "stalls of bread and cabbages, wide shot from eye level",
    "inside a small spaceship cockpit at night, two astronauts in orange suits look out of the round window at a "
    "giant purple planet, medium shot from behind their seats",
]


def load_captions(path):
    """id -> text, from the reviewed jsonl (rows with ``drop: true`` are left out)."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if not r.get("drop"):
                out[r["id"]] = r["text"]
    return out


def plan(manifest, caps):
    """The training items: [(kind, name, image, control or None, caption)]. Pure; raises on a held-out leak (LT-76)."""
    hold = {img for chain in manifest["hold_out"]["chains"] for img in chain}
    guard = {f"frames/{i:04d}.png" for i in manifest["hold_out"].get("guard_shots", [])}
    tr, items = manifest["train"], []
    for x in tr["single"]:
        d = caps.get(f"d:{x['img']}")
        if d:
            items.append(("style", Path(x["img"]).stem, x["img"], None, f"{TRIGGER}, {d}"))
    for k, p in enumerate(tr["scene_pairs"] + tr["inshot_pairs"]):
        d, c = caps.get(f"d:{p['b']}"), caps.get(f"c:{p['a']}>{p['b']}")
        if d and c:
            items.append(("pair", f"p{k:04d}", p["b"], p["a"], f"{TRIGGER}, {d.rstrip('.')}. {c}"))
    leak = [i for i in items if i[2] in hold | guard or (i[3] and i[3] in hold | guard)]
    if leak:
        raise ValueError(f"LT-76: {len(leak)} held-out pictures in training, e.g. {leak[0][2]}")
    return items


def samples(manifest, caps, ds_dir):
    """Six fixed sample prompts (LT-12): held-out content, one without the trigger, one held-out edit, two new subjects."""
    chains = [c for c in manifest["hold_out"]["chains"] if len(c) >= 6]
    a, b = chains[0], chains[1]
    out = [{"prompt": f"{TRIGGER}, {caps[f'd:{a[0]}']}"}, {"prompt": f"{TRIGGER}, {caps[f'd:{b[0]}']}"},
           {"prompt": caps[f"d:{a[0]}"]},
           {"prompt": f"{TRIGGER}, {caps[f'd:{a[1]}'].rstrip('.')}. {caps[f'c:{a[0]}>{a[1]}']}",
            "ctrl_img": str(Path(ds_dir) / "ref" / Path(a[0]).name)}]
    out += [{"prompt": f"{TRIGGER}, {s}"} for s in NEW_SUBJECTS]
    return out


def build(dataset, captions, out, template, cfg_out):
    dataset, out = Path(dataset), Path(out)
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    caps = load_captions(captions)
    items = plan(manifest, caps)
    for sub in ("style", "pairs/target", "pairs/control", "ref"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    for kind, name, img, ctrl, text in items:
        dst = out / ("style" if kind == "style" else "pairs/target")
        shutil.copy(dataset / img, dst / f"{name}.png")
        (dst / f"{name}.txt").write_text(text, encoding="utf-8")
        if ctrl:
            shutil.copy(dataset / ctrl, out / "pairs/control" / f"{name}.png")
    smp = samples(manifest, caps, out)
    for s in smp:
        if "ctrl_img" in s:
            shutil.copy(dataset / "frames" / Path(s["ctrl_img"]).name, s["ctrl_img"])
    cfg = Path(template).read_text(encoding="utf-8").replace("\"@SAMPLES@\"", json.dumps(smp, ensure_ascii=False))
    Path(cfg_out).write_text(cfg, encoding="utf-8")
    n = {"style": sum(i[0] == "style" for i in items), "pairs": sum(i[0] == "pair" for i in items)}
    print("built", n, flush=True)
    return n


if __name__ == "__main__":
    build(*sys.argv[1:6])
