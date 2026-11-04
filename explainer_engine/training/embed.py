# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/embed.py`
# Target Module : explainer_engine/training/embed.py
# Target Classes/Symbols : def _model(), def images(), def texts()
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

"""Picture and text embeddings for the judge (CLIP ViT-B-32, CPU is enough for a few hundred pictures).

Needs ``torch`` + ``open_clip_torch`` (not in requirements.txt: install them where the judge runs, the pod or a cloud
session). Embeddings are cached per file hash in ``<cache>/<sha1>.npy`` so a re-judge costs nothing.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

MODEL = ("ViT-B-32", "laion2b_s34b_b79k")
_M = {}


def _model():
    if not _M:
        import open_clip
        import torch
        m, _, pre = open_clip.create_model_and_transforms(*MODEL)
        m.eval()
        _M.update(m=m, pre=pre, tok=open_clip.get_tokenizer(MODEL[0]), torch=torch)
    return _M


def images(paths, cache=None):
    out = []
    for p in map(Path, paths):
        key = hashlib.sha1(p.read_bytes()).hexdigest()
        cp = Path(cache) / f"{key}.npy" if cache else None
        if cp and cp.exists():
            out.append(np.load(cp))
            continue
        from PIL import Image
        M = _model()
        with Image.open(p) as im, M["torch"].no_grad():
            v = M["m"].encode_image(M["pre"](im.convert("RGB")).unsqueeze(0))[0].numpy()
        v = v / np.linalg.norm(v)
        if cp:
            cp.parent.mkdir(parents=True, exist_ok=True)
            np.save(cp, v)
        out.append(v)
    return np.array(out)


def texts(strings):
    M = _model()
    with M["torch"].no_grad():
        v = M["m"].encode_text(M["tok"](list(strings))).numpy()
    return v / np.linalg.norm(v, axis=-1, keepdims=True)
