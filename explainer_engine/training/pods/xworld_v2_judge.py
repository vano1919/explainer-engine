"""Measures the pictures of one xworld_v2 round test with Qwen3-VL-8B (DSG-style questions, arXiv 2310.18235): for every shot
its own yes/no checks (did the change happen, who is there, the shot's content), "same place as shot 0?", the shot size
(close / medium / wide) and "which era are the people from?" against the scene's era words (ვანო 13:26: a viewer must see
the era at once). Claude's look decides; these numbers compare rounds and prompt forms.

    python xworld_v2_judge.py <scene dir> <round out dir>   ->  judge.jsonl + summary.json in the round dir
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import jobs, load
else:
    from xworld_v2_scenes import jobs, load

MODEL = "Qwen/Qwen3-VL-8B-Instruct"
YES = " Answer only yes or no."
SAME = "Do these two pictures show the same place (the same room, landscape or street)?" + YES
SIZE = "Is this picture a close-up of a face, a medium shot or a wide shot? Answer with one word: close, medium or wide."
ERA = "From which historical era or culture are the people in this picture? Answer in a few words."


def questions(scenes, outd):
    """[{name, form, scene, key, images, text, want}] for every drawn picture; want = 'yes', a size word or era words."""
    sc = {s["name"]: s for s in scenes}
    out = []
    for j in jobs(scenes):
        img = str(Path(outd) / f"{j['name']}.png")
        shot = next(s for s in sc[j["scene"]]["shots"] if s["id"] == j["shot"])
        base = {"name": j["name"], "form": j["form"], "scene": j["scene"]}
        for k, q in enumerate(shot["checks"]):
            out.append(dict(base, key=f"check{k}", images=[img], text=q + YES, want="yes"))
        if j["shot"] != "s0":
            out.append(dict(base, key="same_place", images=[str(Path(outd) / f"{j['scene']}_s0.png"), img], text=SAME,
                            want="yes"))
        out.append(dict(base, key="size", images=[img], text=SIZE, want=shot["size"]))
        out.append(dict(base, key="era", images=[img], text=ERA, want=sc[j["scene"]]["era"]))
    return out


def ok(q, answer):
    a = answer.lower()
    if isinstance(q["want"], list):
        return any(w in a for w in q["want"])
    return a.strip(" .").startswith(q["want"])


def summary(rows):
    """Share of passed questions per form and per key, and per form x scene."""
    out = {}
    for r in rows:
        for k in (r["form"], f"{r['form']}/{r['key'].rstrip('0123456789')}", f"{r['form']}/{r['scene']}"):
            n, p = out.get(k, (0, 0))
            out[k] = (n + 1, p + r["ok"])
    return {k: round(p / n, 3) for k, (n, p) in sorted(out.items())}


def main(argv):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    scenes, outd = load(argv[0]), Path(argv[1])
    qs = [q for q in questions(scenes, outd) if all(Path(i).exists() for i in q["images"])]
    proc = AutoProcessor.from_pretrained(MODEL)
    proc.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda").eval()
    rows = []
    for k in range(0, len(qs), 8):
        group = qs[k:k + 8]
        msgs = [[{"role": "user", "content": [{"type": "image", "image": i} for i in q["images"]]
                  + [{"type": "text", "text": q["text"]}]}] for q in group]
        enc = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_dict=True,
                                       return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=16, do_sample=False)
        for q, t in zip(group, proc.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)):
            t = " ".join(t.split())
            rows.append({k2: q[k2] for k2 in ("name", "form", "scene", "key")} | {"answer": t, "ok": ok(q, t)})
    (outd / "judge.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    (outd / "summary.json").write_text(json.dumps(summary(rows), indent=1), encoding="utf-8")
    print("judged", len(rows), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
