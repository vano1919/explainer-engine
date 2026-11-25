# Workflow 01: Anchor-First Super-Realistic Keyframe Generation

## Prerequisites
- Read `config/super_realistic_film_bible.json`.
- Zero legacy cartoon/comic/storybook tokens allowed (`lint_super_realistic_prompt`).

## Steps
1. **Generate Master Character Anchors (`character_anchors/`):**
   - Use built-in `generate_image` (`$0.00`) in 16:9 with 35mm ARRI Alexa photorealistic historical cinema framing.
   - Lock exact clothing materials, hair/beard, age, scars, and props. Compute and record SHA-256 hashes.
2. **Generate Master Location Anchors (`location_anchors/`):**
   - Generate one establishing architectural/landscape plate per location set (16:9) with physically motivated light. Record SHA-256 hashes.
3. **Generate Anchor-Locked Scene Keyframes (`keyframes/`):**
   - Pass exact `[character_anchor, location_anchor]` via `ImagePaths` into EVERY scene keyframe generation (`DEF-01`, `DEF-02`).
   - For action/transformation shots ("ignites", "opens", "advances", "rises"), enforce **Before-State Keyframes** (`DEF-04`) — depict the pre-action initial state (plus optional post-action end frame for `flf2v`).
4. **Verify Identity & Style Purity:**
   - Run `explainer_engine/qa/identity_lock.py` (`mandatory=True`, non-self comparison) and `lint_super_realistic_prompt()`.
   - Visually inspect every generated keyframe before approving for 2.5D or Modal LTX rendering.
