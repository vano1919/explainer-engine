# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/compose/style_score.py`
# Target Module : explainer_engine/compose/style_score.py
# Target Classes/Symbols : def crops(), def embed(), def score(), def verdict(), def main()
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

"""AC-14: the automatic style score. Six crops of a picture (line, texture, colour, little layout) are embedded with
DINOv2-small and compared with the creator's own style photos (HF lora_plan_2026-10-22/references_v3, 11 pictures): the mean
of the five nearest cosine similarities.

Measured on 2026-10-25 over 80 earlier pictures the creator had judged: AUC 0.96 between the approved look (eras, the v5
samples) and the pictures he called "the style is lost" (mean 0.63 against 0.42). Its weak side: snow. His photos have none,
so a correct snowy picture scores low (the v5 tundra sample: 0.33). Therefore the score is never read alone: a new picture
is compared with a CONTROL of the same place drawn with the approved prompt shape, and the verdict is REVIEW at most
(D-59: a measured hypothesis, one source type, not a binding threshold).

    python -m explainer_engine.compose.style_score <refs dir> <image> [--control <image>]

Needs torch + transformers (CPU is enough, ~1 s per picture); the pure scoring below is tested without them.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

MODEL = "facebook/dinov2-small"
K = 5
DROP_REVIEW = 0.10       # AC-14: more than this below the same-place control -> REVIEW (style probably drifting)
CROPS, SIDE = 6, 224


def crops(img, n: int = CROPS, seed: int = 1):
    im = img.convert("RGB").resize((1024, 576))
    r = random.Random(seed)
    return [im.crop((x, y, x + SIDE, y + SIDE)) for x, y in ((r.randint(0, 1024 - SIDE), r.randint(0, 576 - SIDE))
                                                             for _ in range(n))]


_model = None


def embed(img) -> np.ndarray:
    """Mean of the crops' normalised CLS embeddings (lazy import: the repo's tests never load torch)."""
    global _model
    import torch
    from transformers import AutoImageProcessor, AutoModel
    if _model is None:
        _model = (AutoModel.from_pretrained(MODEL).eval(), AutoImageProcessor.from_pretrained(MODEL))
    m, proc = _model
    with torch.no_grad():
        e = m(**proc(images=crops(img), return_tensors="pt")).last_hidden_state[:, 0]
        e = torch.nn.functional.normalize(e, dim=-1).mean(0).numpy()
    return e / np.linalg.norm(e)


def score(e: np.ndarray, refs: list[np.ndarray], k: int = K) -> float:
    e = e / np.linalg.norm(e)
    sims = sorted((float(e @ (r / np.linalg.norm(r))) for r in refs), reverse=True)
    return float(np.mean(sims[:k]))


def verdict(s: float, control: float | None) -> dict:
    """PASS or REVIEW, never FAIL (hypothesis tier). Without a control the score is only reported."""
    if control is None:
        return {"rule": "AC-14", "severity": "INFO", "score": round(s, 3), "detail": "no same-place control: score only"}
    drop = control - s
    sev = "REVIEW" if drop > DROP_REVIEW else "PASS"
    return {"rule": "AC-14", "severity": sev, "score": round(s, 3), "control": round(control, 3),
            "detail": f"{drop:+.2f} below the control" if drop > 0 else "at or above the control"}


def main(argv: list[str]) -> int:
    from PIL import Image
    refs = [embed(Image.open(p)) for p in sorted(Path(argv[0]).iterdir()) if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    s = score(embed(Image.open(argv[1])), refs)
    c = score(embed(Image.open(argv[argv.index("--control") + 1])), refs) if "--control" in argv else None
    print(verdict(s, c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
