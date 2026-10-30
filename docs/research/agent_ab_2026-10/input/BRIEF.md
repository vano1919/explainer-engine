# Shared brief (identical for arm A and arm B) — P0c agent A/B, 2026-10-29

Episode: "What if Napoleon marched into Genghis Khan?" — a dialogue "what if" docudrama (narrator + speaking heroes) in
the channel's style, written as ONE `production_script/3` by the writers' room stages (skill `story-engine`,
docs/STORY_ENGINE.md, stage pages in `.claude/agents/`).

Fixed inputs (stage 0 is DONE and not part of the test):
- `jobs/ab_agents_2026-10/input/claim_map.md` — the only facts. I01..I04 are the invented premise (Napoleon's army of 1812
  falls through a fog into the steppe of 1223; Genghis Khan himself is there). Every spoken fact carries a claim id.
- Scale of this test: **8 segments, about 5 minutes, beat template A or B** (not D), 3 speaking heroes at most plus the
  narrator. English for everything the viewer hears or sees.
- Do NOT open anything under `examples/napoleon_vs_genghis/` or `docs/research/*NAPOLEON*` or `/mnt/project-files/**/napoleon*`
  (an earlier script of this episode exists there; reading it would contaminate the test). Other `examples/*` may be read as
  format models.
- No paid call of any kind (no ElevenLabs/Gemini/vidIQ tool, no pod). Stage 5 (voice-caster) therefore uses only
  `audio/casting.query` / `casting.rank` on local data; candidates that cannot be verified without the connector are marked
  `unverified`.
- Stage 7 (script-critic) is NOT part of either arm; the independent critic of this A/B reads both results afterwards.
- Stages in scope: 1 story-architect, 2 scene-writer (one segment per call), 2b beat-writer, 3 performance-director,
  4 edit-planner, 5 voice-caster, 6 shorts-writer (3 Shorts are enough in this test).
- Gates after each stage (free): `python -m explainer_engine.scripting.stage_guard <stage> before.json after.json`
  (stage names there: architect, writer, beats, performer, editor, caster, shorts), `python -m explainer_engine.scripting.story_lint`,
  `python -m explainer_engine.production validate <script>` (PV rules relevant to the stage; later-stage fields are legitimately
  missing before their stage runs).
- After EVERY stage copy the script to `<arm folder>/sNN_<stage>.json` (s01_architect, s02_writer, s02b_beats, s03_performer,
  s04_editor, s05_caster, s06_shorts) so the stages can be compared; the final file is `<arm folder>/production_script.json`.
- Keep a `<arm folder>/LOG.md`: per stage one line: what was done, which gates ran and their FAIL/REVIEW counts, what was
  fixed and how many tries.
