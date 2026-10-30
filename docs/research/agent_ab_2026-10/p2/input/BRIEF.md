# Shared brief, P0c-2 (identical for arm A2 and arm B2) — 16-segment run, 2026-10-29

Same episode as the first A/B: "What if Napoleon marched into Genghis Khan?", a dialogue "what if" docudrama (narrator +
speaking heroes), ONE `production_script/3` by the writers' room (skill `story-engine`, docs/STORY_ENGINE.md, stage pages in
`.claude/agents/`). THIS RUN IS AT FULL SCALE: **template D, the 15-minute historical docudrama, 16 segments** (follow its
16-segment timeline and module for war/rivalry; ST-17..ST-19 apply), about 2,500 spoken words, 3 or 4 speaking heroes plus the
narrator, 3 Shorts. English for everything the viewer hears or sees.

Fixed inputs (stage 0 is given): `jobs/ab_agents_2026-10/p2/input/claim_map.md` — the only facts. Ids are `C-NN`
(scripting/claims.py needs that form); `C-91..C-94` are the INVENTED premise (label I): cite them only on invented story beats,
never on a fact. Every spoken fact carries a claim id.

Rules of the test:
- Do NOT open anything under `examples/napoleon_vs_genghis`, `docs/research/agent_ab_2026-10/`, `jobs/ab_agents_2026-10/arm_*`,
  `jobs/ab_agents_2026-10/blind`, or `/mnt/project-files/**/napoleon*` (earlier scripts of this episode; reading them would
  contaminate the test). Other `examples/*` may be read as format models.
- No paid call of any kind (no ElevenLabs/Gemini/vidIQ tool, no pod, no media). Stage 5 (voice-caster) uses only
  `audio/casting.query` / `casting.rank` on local data; unverifiable candidates are marked `unverified`.
- Stage 7 (script-critic) is not part of either arm.
- Stages in scope: 1 story-architect, 2 scene-writer (one segment per call), 2b beat-writer, 3 performance-director,
  4 edit-planner, 5 voice-caster, 6 shorts-writer.
- Gates after each stage (free): `python -m explainer_engine.scripting.stage_guard <stage> before.json after.json`
  (architect, writer, beats, performer, editor, caster, shorts; known tooling bug: it rejects a LATER correction of a segment
  `scene` header as "not the architect's field" — report such a line, it is not your error), `story_lint`, and the partial
  gates `PYTHONPATH=. python3 jobs/ab_agents_2026-10/p2/input/gate.py <script> [story|scene|narr|beats|claims]`
  (the individual lints that run before `voice`/`shots` exist). `python -m explainer_engine.production validate` is for stages 4-6
  (it stops at schema FAILs before that).
- Known unfixable noise in validate: PV-05 (sound files not in git), PV-45/PV-47 (creator approvals), PV-11 (prompts not compiled).
- After EVERY stage copy the script to `<arm folder>/sNN_<stage>.json` (s01_architect, s02_writer, s02b_beats, s03_performer,
  s04_editor, s05_caster, s06_shorts); the final file is `<arm folder>/production_script.json`.
- Keep `<arm folder>/LOG.md`: per stage one line: what, gates and counts, fixes and tries.
