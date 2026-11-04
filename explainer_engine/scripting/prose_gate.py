# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2: Spoken Prose Quality Gate Synchronization with `/4` Dialogue & Silence Rules (`D-80`, `D-90`)
# Target Module : explainer_engine/scripting/prose_gate.py
# Target Classes/Symbols : ProseViolation, ProseGateResult, ProseGate, check_prose_quality
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Update `ProseGate` in `explainer_engine/scripting/prose_gate.py`:
#    - Support `/4` multi-voice character segments (`scene_type == "character_scene"` with `character_id` and `D-90` spoken quote lines) alongside narrator prose.
#    - Enforce `on_screen_text` 4-word hard ceiling (`len(on_screen_text.split()) <= 4`) when `on_screen_text` is present on a `/4` segment.
#    - Enforce active-voice spoken rhythm and `[pause: Xs]` / `silence_duration_sec` alignment around climax reveals (`D-80` / `D-86`).
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `prose_gate.py` assumes a single narrator voice across all segments and does not validate `/4` `on_screen_text` word-count caps (`<=4` words) or distinguish acted `character_scene` quotes (`D-90`) from narrator exposition.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Prevents false-positive prose rejections on short dramatic historical quotes while strictly enforcing the 4-word title-card / on-screen-text readability rule.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] ElevenLabs Prohibited Use Policy
#        URL: https://elevenlabs.io/use-policy
#        Rationale: Prohibits non-consensual voice cloning and impersonation of living individuals/candidates (enforced by D-62 / PV-55), while permitting dramatic voice acting for centuries-deceased historical figures (D-90).
#    [2] ElevenLabs Terms of Use
#        URL: https://elevenlabs.io/terms-of-use
#        Rationale: Governs commercial synthetic voice generation rights, speaker consent rules for living people, and lawful dramatic characterization.
#    [3] YouTube Disclosing Use of Altered or Synthetic Content
#        URL: https://support.google.com/youtube/answer/14328491?hl=en
#        Rationale: Distinguishes realistic deceptive deepfakes of real living persons/events from stylized 2D animated counterfactual historical drama.
#    [4] YouTube Understanding 'How this content was made' Disclosures
#        URL: https://support.google.com/youtube/answer/15447836?hl=en
#        Rationale: Specifies creator disclosure metadata requirements for synthetic media vs stylized animation.
#    [5] YouTube Channel Monetization Policies (Reused & Inauthentic Content)
#        URL: https://support.google.com/youtube/answer/1311392?hl=en-GB
#        Rationale: Confirms that multi-character dramatic dialogue (BP-142 / D-90) and original narrative transformation protect against inauthentic/repetitive content flags.
#    [6] Hu et al. (2021) — LoRA: Low-Rank Adaptation of Large Language Models (arXiv:2106.09685)
#        URL: https://arxiv.org/abs/2106.09685
#        Rationale: Provides the mathematical foundation for scaling low-rank style weights (alpha/r = 0.7 for xworld_v2) to retain base model prompt adherence while preserving cast identity.
# =============================================================================
"""Stub specification module for explainer_engine/scripting/prose_gate.py (to be implemented by Claude per TODO above)."""
from __future__ import annotations
