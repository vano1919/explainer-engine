# Antigravity Operational Constitution — Super-Realistic Cinema Engine

These rules govern ALL autonomous Antigravity sessions on `vano1919/explainer-engine` and synchronize 100% with `.claude/settings.json`, `explainer_engine/governance/gateway_hook.py`, `explainer_engine/core/spend_ledger.py`, and `config/super_realistic_film_bible.json`.

## 1. Financial Ceiling, Upfront Pre-Authorization & Spend Ledger Law (NON-NEGOTIABLE)
- **Upfront Pre-Authorization Protocol (Owner Rule — Overnight-Safe):**
  - ALL paid spend approvals (Modal H100, ElevenLabs, optional Paid Gemini / SFX / Music APIs) MUST be requested **UPFRONT at the start of the session/plan** as a single unified budget envelope — **NEVER mid-run** when the owner may be asleep or away from the computer.
  - Once the owner pre-authorizes the upfront budget envelope (either in the initial prompt or via upfront confirmation), the agent executes autonomously without stopping mid-run as long as cumulative spend stays within the approved SQLite WAL cap.
  - At **100% of the approved cap**, `explainer_engine/core/spend_ledger.py` enforces an automatic hard `OVERRUN` block (zero exceptions). Always compute reservations with safe cold-start/retry headroom so valid jobs do not false-lock overnight.
  - Committed `config/owner_approvals.json` MUST remain empty (`"approvals": {}`); session-scoped runtime approvals live in a gitignored job file passed via `EE_OWNER_APPROVALS_PATH`.
- **Modal H100 (`MODAL1` / LTX-2.5):** Default **$15.00 TOTAL HARD CAP** (or the session's explicitly pre-authorized envelope, whichever is lower).
  - Every paid Modal launch MUST atomically `reserve()` in SQLite WAL (`explainer_engine/core/spend_ledger.py`) BEFORE calling Modal, and `settle()` actual USD IMMEDIATELY after completion.
  - Keep LTX-2.5 action clips tight at **4.0–6.0 seconds** (`97–145` frames @ 24fps, `8n+1`) so each clip costs ~$0.06–$0.12 on H100.
- **Local CPU Rendering & Built-In Photo Gen (`generate_image`):** **$0.00 unlimited** — iterate locally until maps, 2.5D, bridges, color grade, and audio mixes are spotless before spending paid dollars.
- **Other Paid APIs (ElevenLabs, Paid Gemini, SFX/Music APIs):** Only within the upfront pre-authorized envelope; **$0.00** if not included in the session's upfront approval.

## 2. Super-Realistic 35mm Film Style Purity (TOTAL PURGE)
- **Single Source of Truth:** `config/super_realistic_film_bible.json` + `explainer_engine/episode/style_bible.py` strictly supersede legacy cartoon/illustrated/flat presets (`crossworld_main_style_v1`, `main_style_5709.png`, `ComicNeue`, `Bangers`, `design/palette.json`).
- **Zero Legacy Tokens:** Every active prompt, config, and preset MUST pass `lint_super_realistic_prompt()` — rejecting `cartoon`, `comic`, `anime`, `cel-shaded`, `clay`, `3d render`, `pixar`, `flat vector`, `neon`, `glossy cgi`, `storybook`, `painted look`.
- **Unified Cinema Lens:** LTX-2.5 clips, 2.5D parallax scenes, Natural Earth shaded-relief maps, and visual bridges MUST ALL pass through `explainer_engine/finish/cinema_grade.py` (`assets/luts/historical_docudrama_35mm.cube` + 35mm grain + soft vignette).

## 3. Production & Continuity Laws (Fixing DEF-01..DEF-11)
1. **Anchor-First ImagePaths (`DEF-01`, `DEF-02`):** Generate and SHA-256-lock `character_anchors/` + `location_anchors/` FIRST. Pass those exact anchor `ImagePaths` into EVERY subsequent scene keyframe generation and verify via `explainer_engine/qa/identity_lock.py`.
2. **Before-State Keyframes (`DEF-04`):** Transformation/ignition/movement shots MUST start from the pre-action initial state (e.g., unlit beacon, closed gate), NEVER the post-action outcome.
3. **4–6s LTX Clip Cap & Prop Continuity (`DEF-05`):** Every LTX prompt MUST be a single flowing present-tense paragraph with an explicit prop end-state clause (where held objects remain at clip end). NEVER apply per-clip zoom/stretch before stitching chained LTX shots.
4. **Automatic BP-187 Tail Trimming (`DEF-03`):** Trim speech/action clips `0.35–0.50s` after the final spoken word or action beat via `explainer_engine/edit/trim.py`. NEVER ship 7-second dead pauses.
5. **Scene-First Routing (`DEF-07`):** No "video slideshows" — whenever `ltx_video` is used, it MUST belong to a coherent multi-shot scene (continuous last-frame chaining or Blender-blocked multi-angle set). General narration uses `still_25d`, `map_action`, or illustrated `drawing_explainer`.
6. **2K Broadcast Master (`DEF-08`):** Every final delivery master MUST be `2560x1440`, `24 fps`, `yuv420p`, `48000 Hz` 2-ch stereo, `-14.0 ± 0.5 LUFS`, `<= -1.2 dBTP` (mix target `-1.5 dBTP` for AAC headroom).
7. **Scene-Isolated Broadcast Audio (`DEF-06`, `DEF-11`):** Lock per-shot ambience and SFX strictly to their own scene boundaries (**0.0s bleed into unrelated scenes**), use non-periodic ambience extension, keep modern documentary underscore subtly tucked under voice (`-26..-32 dB` relative), and add `30–50ms` anti-pop fades.

## 4. Mandatory Governed Execution, Research-First & Adversarial QA (L0–L5)
- Route governed commands and spend accounting through `explainer_engine/governance/antigravity_runner.py` (logging every step to `jobs/antigravity_execution_ledger.jsonl` and enforcing `gateway_hook` + `ProductionStateMachine` + `spend_ledger`).
- **Research-First Law:** When solving a hard media/audio/continuity problem, NEVER blindly invent from scratch. First research >=5 real external references/open-source tools/industry workflows, adapt proven methods, and only invent when nothing suitable exists.
- **Adversarial Clean-Room Eyes-On & Ears-On Rule:** NEVER self-grade a full film from a single compressed 480p watch or logs alone. Spawn an independent clean-room critic subagent that inspects **15–30s HD segments** AND **isolated audio stems (Music-only, SFX-only, Voice+Bed)** without seeing build scripts, paired with objective CV/audio detectors.
- **No Attribution & No Secret Leaks:** Zero AI/assistant attribution in code/commits; zero API keys or tokens in logs, URLs, or git commits.
