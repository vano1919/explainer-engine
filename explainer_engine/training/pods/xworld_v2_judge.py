# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v2_judge.py`
# Target Module : explainer_engine/training/pods/xworld_v2_judge.py
# Target Classes/Symbols : def questions(), def ok(), def summary(), def main()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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
            out.append(dict(base, key="same_place", images=[str(Path(outd) / f"{j['scene']}_{j['seed']}_s0.png"), img], text=SAME,
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
