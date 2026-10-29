---
name: voice-caster
description: Stage page (OR-20, D-79): the main agent runs this stage itself, following this page; it is not spawned as a separate agent. Writers' room stage 5. Casts an ElevenLabs voice for the narrator and every speaking character from their traits (and, for a real person or known character, from documented facts about them), without imitation. Use when a script has speaking heroes without a voice_id, or when the creator asks to find voices.
model: sonnet
tools: Read, Edit, Bash, Grep, ToolSearch
---

You fill `voice` and `cast.<id>.voice` only (stage guard `caster`). Read `docs/STORY_ENGINE.md` (VC rules) and
`.claude/skills/elevenlabs-voice/SKILL.md`.

For each speaking hero:
1. Write `voice.traits`: gender, age (at the story's time), 2-4 temperament words from the hero card and arc, energy,
   origin, role. For a real person set `real_person: true` and list in `documented` the sourced facts the traits rest on
   (claim ids or URLs: where they grew up, how contemporaries described their manner). Never a film or actor portrayal.
2. `python -c` with `explainer_engine.audio.casting.query(hero)` gives the connector arguments; call
   `creative_list_voices` (ElevenLabs connector, free) with them; on no result use `casting.relaxed(q)` in order.
3. `casting.rank(results, hero, taken=<voice ids already cast>)` -> write the top three as `candidates` with their `why`.
4. If nothing fits, write `casting.design_description(hero)` into the report as a proposal for `creative_design_voice`
   (paid; the creator supplies the preview line and approves the cost; never call it yourself).
5. `production validate`: no PV-10 FAIL, PV-32 REVIEWs listed for the creator (two similar speakers, no voice chosen).
Never search, design or describe a voice as a named person's voice, never use the "famous" category, never clone.
The creator picks from the candidates after the one-chunk test read (EL-02).
