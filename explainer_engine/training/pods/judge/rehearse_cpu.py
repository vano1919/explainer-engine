"""Free CPU rehearsal of ``HFJudge`` with the REAL transformers code, the REAL processor and chat template of a Qwen3-VL repo, and a TINY
random model of the same architecture (dense or MoE): it proves the message building, the image pipeline, greedy generation and the
YES / NO probability path run end to end on the pinned library before a GPU is paid for. It proves nothing about answer quality.

    python -m explainer_engine.training.pods.judge.rehearse_cpu <dir with the repo's small files> <tiny model dir to write>

The first dir needs config.json, preprocessor_config.json, tokenizer files and chat_template.json (a Hub download of those small files)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def build_tiny(src: Path, dst: Path):
    import torch
    from transformers import AutoConfig, AutoModelForImageTextToText
    cfg = AutoConfig.from_pretrained(src)
    t, v = cfg.text_config, cfg.vision_config
    t.hidden_size, t.num_hidden_layers, t.num_attention_heads, t.num_key_value_heads, t.head_dim = 64, 2, 4, 2, 16
    t.intermediate_size = 128
    t.rope_scaling = dict(t.rope_scaling, mrope_section=[2, 3, 3]) if getattr(t, "rope_scaling", None) else t.rope_scaling
    if hasattr(t, "num_experts"):
        t.num_experts, t.num_experts_per_tok, t.moe_intermediate_size = 4, 2, 32
    v.depth, v.hidden_size, v.num_heads, v.intermediate_size, v.out_hidden_size = 2, 32, 2, 64, 64
    v.deepstack_visual_indexes = [0, 1]
    torch.manual_seed(0)
    model = AutoModelForImageTextToText.from_config(cfg, dtype=torch.float32)
    dst.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(dst)
    for f in ("preprocessor_config.json", "video_preprocessor_config.json", "tokenizer.json", "tokenizer_config.json", "vocab.json",
              "merges.txt", "chat_template.json", "generation_config.json"):
        if (src / f).is_file():
            shutil.copy(src / f, dst / f)
    return type(model).__name__


def main(argv=None) -> int:
    from PIL import Image
    from explainer_engine.training.pods.judge import judge_core as J
    src, dst = Path(argv[0]), Path(argv[1])
    name = build_tiny(src, dst)
    j = J.HFJudge(str(dst), dtype="float32", device="cpu", experts="eager" if "moe" in name.lower() else None)
    prompts = J.load_prompts()
    ex = [Image.new("RGB", (96, 64), c) for c in ((200, 30, 30), (30, 200, 30), (30, 30, 200))]
    frame, anchor = Image.new("RGB", (160, 96), (90, 90, 90)), Image.new("RGB", (96, 96), (10, 10, 10))
    rows = {}
    for d in J.DEFECTS:
        q = J.build_question(prompts, d, True, len(ex))
        text, p = j.ask(q, ex, anchor if d == "identity_mismatch" else None, frame)
        assert 0.0 <= p <= 1.0, p
        rows[d] = {"p_yes": round(p, 4), "text": text[:40]}
    again = j.ask(J.build_question(prompts, "deformed_hand", True, len(ex)), ex, None, frame)
    assert abs(again[1] - rows["deformed_hand"]["p_yes"]) < 1e-3, "greedy decoding is not repeatable"
    print(json.dumps({"model_class": name, "yes_ids": j.yes_ids, "no_ids": j.no_ids, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
