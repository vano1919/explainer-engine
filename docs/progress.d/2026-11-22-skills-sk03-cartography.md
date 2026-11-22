## 2026-11-22 — Cartography font rule follows the owner's film-font row (SK-03)
- Cartography Skill rule 8 and checklist row CRAFT-CART-08 said map labels use the style bible's faces (Fredoka, Inter). Owner row OR-F04 (words_verbatim true, `explainer_engine/governance/owner_requirements.json`) says the font always comes from the episode film's preset. Both now say so; CRAFT-CART-05 (palette.json) and the other Skills were checked and have no conflict with an active verbatim row, so they are unchanged.
- Files: `.claude/skills/cartography/SKILL.md`, `explainer_engine/standards/craft_checklists/cartography.json` (regenerated with `craft write`).
- Test: `tests/unit/test_craft_checklists.py` and `tests/unit/test_agent_governance.py` pass (41 tests).
- Not changed, on purpose: shot-visuals (Qwen-Image-2.1 route, OR-I27) and lora-training (D-80) stay; OR-C05 is an open conflict about the photo engine, so no patch is written for it.
