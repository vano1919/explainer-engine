"""Captions for the xworld_v1 material (D-80) with Qwen3-VL-8B-Instruct on a pod; started by caption_xworld_v1.sh (OR-21).

The material is HF ``lora_plan_2026-10-26/dataset_xworld_v1/`` (manifest.json). Every image gets one description; every
pair (shot -> next shot of a scene, start -> end of a shot) also gets one change line. The trigger word is NOT written here:
it is added when the training set is put together, so the creator's choice of trigger stays open (OR-22).
Output: captions.jsonl (one row per job, appended as it goes, so a stop loses nothing) under the same HF folder.

    python caption_xworld_v1.py <dataset dir> <out dir> [--limit N] [--batch B]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MODEL = "Qwen/Qwen3-VL-8B-Instruct"
MAX_NEW = {"describe": 180, "change": 60}

# No character names (decided 2026-10-26: captions describe what is seen, the LoRA learns the look, not a cast).
DESCRIBE = (
    "Describe this frame from a 2D animated cartoon for an image-generation training caption. One paragraph, 50 to 90 "
    "words, plain English. Order: first the place (where, time of day, the main objects of the set), then each person "
    "or creature (looks, clothing, pose, facing direction, expression, where in the frame), then what is happening, "
    "then the camera (shot size such as close-up / medium / wide, angle, what is in the foreground). Never use names of "
    "characters, shows, studios or brands; describe people by how they look (for example 'an old man with spiky "
    "light-blue hair in a white lab coat'). Do not describe the drawing style, line work or colours of the art itself. "
    "Do not mention text, subtitles or logos. No opinions, no guesses about the story.")
CHANGE = (
    "These are two consecutive frames of the same scene of a 2D animated cartoon: frame 1, then frame 2. In ONE "
    "sentence that starts with 'Change from the previous shot:' say only what is different in frame 2 (camera shot "
    "size or angle, who is visible, poses, expressions, positions, objects). Same rules: no names of characters or "
    "shows, people described by how they look, nothing about the drawing style, nothing about what stayed the same.")
BANNED = ("rick", "morty", "summer", "beth", "jerry", "smith", "sanchez", "meeseeks", "adult swim", "cartoon network")


def jobs(manifest: dict) -> list[dict]:
    """Every caption the material needs, in a fixed order: descriptions of each image once, then the change lines."""
    tr, out, seen = manifest["train"], [], set()

    def desc(img, part):
        if img not in seen:
            seen.add(img)
            out.append({"id": f"d:{img}", "kind": "describe", "images": [img], "part": part})
    for x in tr["single"]:
        desc(x["img"], "single")
    for p in tr["scene_pairs"]:
        desc(p["a"], "scene_pair"); desc(p["b"], "scene_pair")
    for p in tr["inshot_pairs"]:
        desc(p["a"], "inshot_pair"); desc(p["b"], "inshot_pair")
    for chain in manifest["hold_out"]["chains"]:
        for img in chain:
            desc(img, "hold_out")
    for p in tr["scene_pairs"]:
        out.append({"id": f"c:{p['a']}>{p['b']}", "kind": "change", "images": [p["a"], p["b"]], "part": "scene_pair"})
    for p in tr["inshot_pairs"]:
        out.append({"id": f"c:{p['a']}>{p['b']}", "kind": "change", "images": [p["a"], p["b"]], "part": "inshot_pair"})
    for chain in manifest["hold_out"]["chains"]:
        for a, b in zip(chain, chain[1:]):
            out.append({"id": f"c:{a}>{b}", "kind": "change", "images": [a, b], "part": "hold_out"})
    return out


def problems(text: str, kind: str) -> list[str]:
    """What the review flags at once (Claude still reads every caption, 2026-10-26)."""
    low, bad = text.lower(), []
    bad += [f"name:{w}" for w in BANNED if w in low]
    words = len(text.split())
    if kind == "describe" and not 35 <= words <= 120:
        bad.append(f"length:{words}")
    if kind == "change" and not low.startswith("change from the previous shot:"):
        bad.append("change_prefix")
    return bad


def main(argv):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    ds, outdir = Path(argv[0]), Path(argv[1])
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    batch = int(argv[argv.index("--batch") + 1]) if "--batch" in argv else 4
    outdir.mkdir(parents=True, exist_ok=True)
    todo = jobs(json.loads((ds / "manifest.json").read_text(encoding="utf-8")))[:limit]
    path = outdir / "captions.jsonl"
    done = {json.loads(line)["id"] for line in path.open(encoding="utf-8")} if path.exists() else set()
    todo = [j for j in todo if j["id"] not in done]
    print(f"jobs left {len(todo)} (done {len(done)})", flush=True)
    proc = AutoProcessor.from_pretrained(MODEL)
    proc.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda").eval()
    for kind in ("describe", "change"):
        part = [j for j in todo if j["kind"] == kind]
        for k in range(0, len(part), batch):
            group = part[k:k + batch]
            msgs = [[{"role": "user", "content": [{"type": "image", "image": str(ds / im)} for im in j["images"]]
                      + [{"type": "text", "text": DESCRIBE if kind == "describe" else CHANGE}]}] for j in group]
            enc = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_dict=True,
                                           return_tensors="pt", padding=True).to(model.device)
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=MAX_NEW[kind], do_sample=False)
            texts = proc.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
            with path.open("a", encoding="utf-8") as f:
                for j, t in zip(group, texts):
                    t = " ".join(t.split())
                    f.write(json.dumps(dict(j, text=t, flags=problems(t, kind)), ensure_ascii=False) + "\n")
            print(f"{kind} {k + len(group)}/{len(part)}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
