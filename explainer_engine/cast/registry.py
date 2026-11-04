# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M1: Cast Registry & Character Identity Contract (`D-88`, `D-89`, `D-90`, `CD-06`)
# Target Module : explainer_engine/cast/registry.py
# Target Classes/Symbols : CharacterCard, CastRegistry, CastValidationError
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    1. In `CharacterCard` (and nested/companion `CharacterTraits`):
#       - Add explicit boolean field `living: bool = False` (or `traits.living: bool`) plus `historical_era: str | None = None`, `reference_sheet_path: str | None = None`, `elevenlabs_voice_id: str | None = None`, `default_lora_id: str = "xworld_v2"`, and `default_lora_scale: float = 0.7` (`CD-02`).
#       - Add method `CharacterCard. allows_synthetic_voicing() -> bool`: returns `True` ONLY when `self.living is False` and `self.role != "living_real_person"` (`CD-06`: deceased historical figures like Napoleon / Genghis Khan are permitted under `D-90`, whereas any living real person `living=True` is strictly prohibited under `D-62` / `PV-55`).
#    2. In `CastRegistry`:
#       - Implement `from_script(cls, script: Mapping[str, Any]) -> CastRegistry`: parses top-level `cast[]` array from a `production_script/4` payload, enforces cast count bounds (`1 <= len(cast) <= 4` when `scene_type == "character_scene"` is used), and verifies unique `character_id` and distinct `elevenlabs_voice_id` per cast member (`D-88` / `D-90`).
#       - Implement `validate_segment_references(self, segments: Sequence[Mapping[str, Any]]) -> list[str]`: verifies every segment with `character_id` references a declared member in `cast[]`, and every `scene_type == "character_scene"` has a valid `character_id`.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `explainer_engine/cast/registry.py` currently holds minimal skeleton dataclasses (`CharacterCard`, `CastRegistry`) that do not parse `/4` `cast[]` dictionaries, do not track `living: bool` to reconcile `D-62` vs `D-90` (`CD-06`), do not lock `default_lora_scale = 0.7` (`CD-02`), and are never called by `scripting/validator.py` or `pipeline.py`.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Enforces referential integrity between top-level `cast[]` and per-segment `character_id`, prevents accidental voice synthesis of living individuals (`D-62` / `PV-55`), and guarantees consistent character sheet and voice routing across Tier 1–4.
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
"""Stub specification module for explainer_engine/cast/registry.py (to be implemented by Claude per TODO above)."""
from __future__ import annotations
