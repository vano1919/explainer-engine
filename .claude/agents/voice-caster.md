---
name: voice-caster
description: Stage page (OR-20, D-79): the main agent runs this stage itself, following this page; it is not spawned as a separate agent. Writers' room stage 5. Casts an ElevenLabs voice for the narrator and every speaking character from their traits (and, for a real person or known character, from documented facts about them), without imitation. Use when a script has speaking heroes without a voice_id, or when the creator asks to find voices.
model: sonnet
effort: high
tools: Read, Edit, Bash, Grep, ToolSearch
---

At the start of this stage Read this page and every file it says to read first with the Read tool (never work from a remembered copy of them, OR-32), then run `python -m explainer_engine.scripting.stage_guard start caster --job <job> --page .claude/agents/voice-caster.md --input <each file you read>`; at its end `python -m explainer_engine.scripting.stage_guard fresh caster --job <job> <the stage output>` and this stage's own check (the gate column of the skill `story-engine`).

You fill `voice` and `cast.<id>.voice` only (stage guard `caster`). Read `docs/STORY_ENGINE.md` (VC rules) and
`.claude/skills/elevenlabs-voice/SKILL.md`. Everything below is free: no paid take, no REST call; ElevenLabs is reached only
through the connector, under the PreToolUse hook and the ledger.

0. The narrator is the channel voice: the `status: channel` entry of `config/channel_voices.json`
   (`voice_check.channel_voice(voice_check.load_registry())`). Do not search for another one; only the creator's recorded
   word replaces it (VC-08). Host characters speak with that voice (D-68).
For each other speaking hero:
1. Write `voice.traits`: gender, age (at the story's time), 2-4 temperament words from the hero card and arc, energy,
   origin, role. For a real person set `real_person: true` and list in `documented` the sourced facts the traits rest on
   (claim ids or URLs: where they grew up, how contemporaries described their manner). Never a film or actor portrayal.
2. `explainer_engine.audio.casting.query(hero)` gives the connector arguments; add `sort: usage_character_count_1y` and call
   `creative_list_voices` (ElevenLabs connector, free) with them; on no result use `casting.relaxed(q)` in order.
3. `casting.rank(results, hero, taken=<voice ids already cast>, by_usage=True)` (it applies `casting.eligible`: famous or
   imitation, taken, wrong age are out; trait match decides, usage order only breaks ties) -> the top three as
   `candidates` with their `why`.
4. Audition each candidate for free (VC-06): download its `preview_url`, `voice_audition.load_audio` +
   `voice_audition.record(...)` -> a `voice_audition/1` record per candidate (source kind `library_preview`).
   A preview with `reliable: false` is compared, not trusted.
5. `voice_audition.distinct({voice_id: profile, ...})` over everyone already cast and the new candidate: a VC-04 REVIEW means
   the ear may confuse them (VC-07); pick another candidate or say so on the card.
6. If nothing fits, write `casting.design_description(hero)` into the report as a proposal for `creative_design_voice`
   (paid; the creator supplies the preview line and approves the cost; never call it yourself).
7. Every character whose lines are spoken gets the ElevenLabs voice chosen above, fixed for the whole episode (D-90, card A3 option A):
   the line is read first (one take, EL-13 against the registry) and that take conditions the LTX clip, so the voice is the same in
   every clip. Do not describe the voice in words for LTX (`casting.ltx_voice_text` is the superseded native route, kept in code,
   not used here). A real living person's line stays silent (D-62, PV-55). The audio-in wiring is P6/P7: until it exists, say on the card
   that the take is cast and read but not yet fed to a clip.
8. `production validate`: no PV-10 FAIL, PV-32 REVIEWs listed for the creator (two similar speakers, no voice chosen).
   Then the card: top three, their `why`, their profile numbers and preview links. The creator picks by ear after the
   one-chunk test read (VC-03, EL-02); the test read is the first piece of the OR-19 sample, not an extra paid take.
Every later take of a registered voice goes through `voice_check.check_against` (EL-13).
Never search, design or describe a voice as a named person's voice, never use the "famous" category, never clone.
