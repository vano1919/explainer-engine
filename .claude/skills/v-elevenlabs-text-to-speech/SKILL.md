---
name: v-elevenlabs-text-to-speech
description: The ElevenLabs text-to-speech tool as this channel uses it - eleven_v4 through the connector, voice ids only from the library listing, one take per call, what the model and the connector expose, text normalisation and pronunciation, stitching chunks, output formats, errors and cost tracking. Use when making any narration or hero-line read, when choosing a model, or when a read call fails.
---

# ElevenLabs text-to-speech, the tool (layer L5, stage G6)

Built from the official elevenlabs/skills, page `text-to-speech` (MIT, commit `97478d1b23`). Rewritten under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for how we call it: through the ElevenLabs connector, guarded by
the PreToolUse hook, never with a raw API key from a script. Upstream text with SDK examples is unloaded in
`UPSTREAM_SKILL.md`; details in `references/` (installation, streaming, voice settings, text-to-dialogue). The direction
and credit rules are in skill `elevenlabs-voice`; what the words say, in `narration-script`.

## How a read is made here

1. The words are frozen and tagged (performance stage), the episode's sample gate allows these segments (OR-19), the
   rulebook's `paid_assets` gate passed, and the estimate is in the ledger.
2. The voice id comes from `creative_list_voices` or the creator, never from memory (the connector's own rule); it must be
   the id cast in `production_script.json` (`voice`, `cast.<id>.voice`).
3. One call per chunk with `generations_count: 1` (the hook refuses anything else).
4. Poll `creative_get_flow_run_status` with the returned ids at its `poll_after_seconds` until done; never re-submit to
   retry: a second call is a second charge.
5. Download at once, write the file and its sha256 to the episode folder and the ledger (OR-33), check it (EL-12), then the
   next chunk.

## Models (what to pick)

| Model | Use here |
|---|---|
| `eleven_v4` | **the default** for narration and hero lines: widest emotional range, audio tags, best text understanding |
| `eleven_v3` | only for an episode already read on it, so a re-read matches |
| `eleven_multilingual_v2` | a fallback for very long, flat reads where v4 drifts; no tags |
| `eleven_flash_v2_5`, `eleven_flash_v2` | not for episodes (low latency for agents); never for a published read |

v4 facts from upstream: supports stability and similarity in the API but not style or speed, no SSML, audio tags in
square brackets direct delivery. Our connector exposes only voice and language for v4 (MARKET_RESEARCH V-29); re-check
`creative_get_model_schema` before assuming any other parameter.

## Text that reads right

- **Normalisation**: v4 reads numbers and dates from context; for anything ambiguous write it the way it should be said in
  the TTS text ("nineteen fourteen", "the twenty-fourth"), and keep the display form in `narration.txt`.
- **Pronunciation**: names and places the voice may miss get IPA between slashes and a one-sentence test (EL-07).
- **Language**: `language_code` "en" for the US narrator; a hero's foreign words stay inside an English line ("Frohe
  Weihnachten, Tommy"); test that sentence alone first.
- **Tags**: `[softly]`, `[whispers]`, `[curious]`, `[sighs]`, `[short pause]` and the like; they are spoken as direction, cost
  characters, and carry forward until the next tag.

## Stitching chunks

Upstream's request stitching (`previous_text` / `next_text` or previous request ids) smooths joins between chunks. The
connector does not expose it (V-29, BP-14), so we stand in with chunks of one size class cut at beat ends, the same tag
state at each chunk start, and levelling plus edge fades after the read (ED-01). Never cut mid-sentence.

## Output

Take the connector's highest-quality audio; store as delivered, then convert in our audio stage (skill
`v-audio-production-skill`) to the mix format; never re-encode lossy to lossy twice. Upstream's audio effects (reverb,
distance, filters) are not used for narration; a hero's distance or a radio colour is placed by the sound stage on the stem,
where it can be changed without a new read.

## Errors and what to do

| Symptom | Meaning | Do |
|---|---|---|
| `402 paid_plan_required` | a library voice on a plan that cannot use it | choose a voice the plan can use; ask the creator before any plan change |
| a 4xx about the voice | wrong or retired voice id | re-list voices; never guess an id |
| `429` or a timeout | rate limit or slow service | wait and poll; do not re-submit until the first call's state is known |
| the hook refuses | a rule (one take, sample gate, `paid_assets`) is not met | fix the cause; never work around the hook |
| the take's words differ from the script | the model skipped or added words | re-read only the affected sentence (EL-08) after the check |

## Cost

One credit per character including tags (re-check the account's rate in the usage page or `account_get_usage` before an
estimate). Estimate before every paid read, record it in the ledger, and stop at 80 % of the cap in
`config/spend_caps.json` (invariant 2). Upstream's cost-tracking headers are not visible through the connector: the ledger is
our record.

## Not used from upstream

Raw SDK and CLI calls with an API key in a script, the WebSocket and streaming paths, voice cloning of real people, and the
upstream default voice suggestion (we cast per episode).
