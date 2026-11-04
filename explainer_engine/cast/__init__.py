# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M1: Cast Registry Public Package Exports (`D-88`, `D-89`, `D-90`, `D-62`, `PV-55`)
# Target Module : explainer_engine/cast/__init__.py
# Target Classes/Symbols : CharacterCard, CastRegistry, CastValidationError, VoiceClearanceResult
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Export the complete Cast & Voice Clearance public API from `explainer_engine/cast/__init__.py`:
#    - From `.registry`: export `CharacterCard`, `CharacterTraits`, `CastRegistry`, `CastValidationError`, `load_cast_registry`, `validate_cast_against_script`.
#    - From `.voice_clearance`: export `VoiceClearanceStatus`, `VoiceClearanceResult`, `verify_voice_clearance`, `enforce_d62_d90_voice_policy`.
#    Ensure all downstream callers (`scripting/mold_contract.py`, `audio/tts.py`, `video/tier_router.py`, `video/scene_builder.py`, `pipeline.py`) can import directly from `explainer_engine.cast`.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently `explainer_engine/cast/__init__.py` only exports basic placeholder symbols without `CharacterTraits.living` or `D-62`/`D-90` voice-clearance helpers (`CD-06`), forcing downstream modules to reach into private submodules or skip living-person voice enforcement.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Provides a clean, strongly typed package boundary so script validation, TTS voice assignment, and Tier 4 audio-to-video routing enforce identical cast and voice-safety contracts.
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
"""Stub specification module for explainer_engine/cast/__init__.py (to be implemented by Claude per TODO above)."""
from __future__ import annotations
