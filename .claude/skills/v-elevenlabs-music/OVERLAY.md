# Overlay for `v-elevenlabs-music`: Music (layer L19, stages G4 and G8)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from the official elevenlabs/skills, page `music` (MIT, commit `97478d1b23`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel that calls the music tool only through the ElevenLabs
connector, guarded by the PreToolUse hook, after the library has been searched.
The upstream text is this folder's `SKILL.md` (SDK examples); `references/api_reference.md` stays the parameter list to check names against.

## When music plays here

Music serves the story; it is never wallpaper. The sound plan decides per segment (SP-05, `episode/sound_plan.music_decision`):
the mood comes from the segment's own words, delivery, light and action; a peaceful or joyful segment carries its bed
without a score unless it says `music: true`; one music row per run of one mood, with a crossfade at a mood change; a
designed riser ends on the cut where the story turns. Under the voice it ducks as a dip (BP-53) and stays under it by the
registry's margin (BP-52); fades follow BP-62. A hero singing on screen is not music: it is his line in a video clip
(skill `v-director-cinematic`).

## Order of sources

1. **Our library.** `python -m explainer_engine.audio.catalog search --category music --era <era> --mood <mood>` (add
   `--playable` for verified takes with a working copy). The cue sheet picks by mood, era and intensity
   (`episode/cue_sheet.pick_music`, LIB-06).
2. **A free track with a checked licence.** For music the licence matters (LIB-05): `audio/sources.verdict` says
   `verified`, `quarantine` or `rejected` (NC, share-alike on synchronisation, GPL are refused); a CC BY track needs its
   credit line (`python -m explainer_engine.audio.catalog credits <cue_sheet.json>`).
3. **Record the search** before any paid call:
   `python -m explainer_engine.assets_reuse <episode folder> --kind music --tags <tags> --decide reuse|generate_new`;
   the hook refuses a paid music call without it, and while a free generator is admitted for music (BP-162) it also needs
   `--why` naming what the free take could not do.
4. **ElevenLabs**, last, on the creator's word.

## A paid music call

1. Estimate credits and record them in the ledger; ElevenLabs credits are counted there until `config/spend_caps.json` has
   their line; stop at 80 % of any cap (invariant 2). Ask the creator with the price; no word, no call.
2. Read the connector's music model schema with `creative_get_model_schema` first: which of length, instrumental flag,
   output format and composition plan it really exposes. Do not assume an upstream SDK parameter exists there.
3. One call, `generations_count: 1` (EL-10; the default four takes charge four times). Poll
   `creative_get_flow_run_status` at its interval; never re-submit to retry.
4. Download at once, write the file and its sha256 into the episode folder and the ledger (OR-33).
5. Register it so no episode pays for it again:
   `python -m explainer_engine.audio.register <file> --name <name> --category music --tags <tags> --loop --model <model id> --prompt "<prompt>" --cost-usd <cost>`.
   A machine check is not a listen: `review.human` stays false until a person has heard it.

## Writing the prompt

- **Instrumental, under speech.** Ask for no vocals; keep the busy register away from the voice band; a steady texture
  that can loop or be cut on a phrase.
- **Period by instruments, never by names.** Style rule 20 names the series film in picture prompts; music is different:
  the tool refuses artists, bands and copyrighted lyrics, and naming a film's score invites a copy. Write the era's
  instruments and the feeling: "low strings and a distant snare, cold and patient, no melody climax".
- **Length and shape** from the segment's measured span on the clock, with room for the crossfades.
- **One mood per take.** A change of mood is a second row, not a prompt that turns half-way.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| music fights the narrator | melody in the voice band, or too loud | duck and margin per BP-52/BP-53; choose a sparser take |
| it sounds like a famous score | prompt named a film or composer | rewrite by instruments and mood |
| a `bad_prompt` refusal | a named artist or lyrics | use the tool's suggested wording, minus any name |
| the loop clicks | seam not checked | `python -m explainer_engine.audio.sfx_library assets/audio/library` lint (BP-58) |
| the hook refuses | no library record, no `paid_assets` pass, or not one take | fix the cause; never work around the hook |
| a 429 or a timeout | rate limit | wait and poll the first call; do not send a second |

## References: when to open which

| File | Open when |
|---|---|
| `references/api_reference.md` | checking a parameter name, a composition-plan field or an output format against the schema |
| `references/installation.md` | not needed: we never install the SDK or hold an API key in a script |

## Not used from upstream

SDK, CLI and raw API calls with a key, streaming, finetunes, inpainting and uploads (enterprise features, and they would
store our audio with the vendor), video-to-music (it sends the cut out and adds its own effects, which would bypass the AV
contract), songs with lyrics, and the upstream default model choice (we read the connector's schema per call).
