# Overlay for `v-elevenlabs-sound-effects`: Sound effects, the tool (layer L18, stage G4 gaps)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from the official elevenlabs/skills, page `sound-effects` (MIT, commit `97478d1b23`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for how we reach it: the ElevenLabs connector, guarded by
the PreToolUse hook in `.claude/settings.json`, never an SDK with a key in a script.
The upstream text is this folder's `SKILL.md`; `references/installation.md` is not needed here. What to design is skill `v-design-sound`; this page
is only how to buy one missing take well.

## When to use it, and when not

Use it only when all of this holds: the class is on `audio/sound_plan.json`'s `needs` list; the catalog search found no
take of good quality (LIB-05: effects are chosen by quality); no free licence-checked source has it; the search is
recorded with `python -m explainer_engine.assets_reuse <episode folder> --kind sfx --tags <tags> --decide generate_new`;
and the creator agreed to the price.

Do not use it for: beat cues (free earcons, `audio/cues.py`, BP-64); voices, breaths or crowds that speak words (a read,
skill `elevenlabs-voice`); a sound for a word nobody sees (AV-07); a filler effect to reach the per-scene floor (add a
visible action instead); a bed that a real recording could give (BP-193 prefers the real place).

## The call

1. Estimate the credits, write them in the ledger (counted there until `config/spend_caps.json` has an ElevenLabs line),
   and stop at 80 % of any cap.
2. Read the connector's effect model schema with `creative_get_model_schema`: which of duration, prompt adherence, loop and
   output format it exposes. Upstream lists a duration range, a prompt-influence knob and a loop flag on the API; trust only
   what the schema shows.
3. One call per take, `generations_count: 1` (EL-10). Poll `creative_get_flow_run_status`; a second submit is a second charge.
4. Download at once; file and sha256 to the episode folder and the ledger (OR-33).
5. Register: `python -m explainer_engine.audio.register <file> --name <class_variant> --category <category> --tags <tags> --one-shot|--loop --model <model id> --prompt "<prompt>" --cost-usd <cost>`.
   It converts to the library's 16-bit mono WAV and records source, cost and licence. Then the technical QC
   (`audio/asset_qc.py`, LIB-07) and, for a loop, the seam lint (`python -m explainer_engine.audio.sfx_library assets/audio/library`).
6. A person listens before it ships; until then the manifest says `review.human: false`.

## Prompts that work for a period piece

- **One event class per prompt**: material, action, space, distance. "Hobnailed boots on wet duckboards, a few steps,
  outdoor trench, close." Never several actions merged into one take: the cue sheet places each on its own frame.
- **Name the era by its objects**, not a film: wooden wheels on cobbles, a bolt-action rifle, a field telephone crank.
  Add what must be absent when the model drifts modern ("no engine, no traffic"); the era filter
  (`audio/sfx_planner.filter_sound_events_for_era`) checks the tags afterwards.
- **Distance is the mix's job.** Ask for a close, dry take; the cue sheet adds distance gain, low-pass and reflection
  (SP-06). A take with baked-in reverb cannot be brought close again.
- **Beds**: ask for a loop of the place without events in it (wind through wire, a far murmur), long enough for BP-58's
  loop length; the seam is verified after, never assumed.
- **Variants for repeats** (BP-57): the cue sheet's pitch and gain jitter is free; buy extra variants only for a class heard
  many times close to camera.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| a soft swell where a hit was wanted | prompt too descriptive of mood | name the material and the contact; ask for a short, sharp onset |
| modern sounds inside | the model's default world | name period objects, add what must be absent; re-check the tags |
| the loop jumps at the join | seam not clean | seam lint; trim and crossfade in the library, do not buy again |
| onset late against the picture | silence at the take's head | `audio/stems.onset_of` measures it; trim the head when registering |
| the hook refuses | no library record, no `paid_assets` pass, or not one take | fix the cause; never work around the hook |
| a 422 | a value out of the schema's range | re-read `creative_get_model_schema` and correct the value |

## Not used from upstream

SDK, CLI and raw API calls with an API key, the telephony and low-rate output formats (we take the highest quality the
connector offers and convert once), stylised game and interface sounds (our earcons are procedural), and the upstream
default model choice (read from the connector's schema at call time).
