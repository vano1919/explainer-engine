# S4 voice handoff: Truce 1914, script A (sha 25636aba)

Done 2026-11-13 ~17:50 UTC. 72 spoken lines recorded, one take each (eleven_v4, generations_count 1). 12 silent-beat
lines are not spoken and were not recorded.

| Speaker | Voice (id) | Lines | Credits | Seconds |
|---|---|---|---|---|
| narrator | Odom, CcSJ2r3qw0XU9gJpEPyk | 33 | 2777 | 206.2 |
| Thomas Hale | Toby - British Male, pYDLV125o4CgqP8i49Lg | 17 | 432 | 34.3 |
| Friedrich Brandt | Paul - English Barritone Narration, G4t3322LqgEAU2HEgGCv | 16 | 459 | 37.0 |
| Sgt Harris | Gideon - Rugged, Gravelly and Northern, q1h5HGdnfVxp4TXTJRNN | 6 | 147 | 12.0 |

Total 3814.6 credits (1 credit per character, no tags), cap 5000. About $0.69 by the connector's own price field.
Text is exactly the frozen script text, no audio tags added. No re-reads, no failures.

Files: `episodes/ep_truce_1914/audio/reads/<line_id>.mp3`, `ledger.jsonl` (also `calls.jsonl` in project files),
`durations.json` (measured seconds per line), `lines.json` (line id, speaker, voice, text).
Measured durations match the connector's duration for all 72 lines.

Not done (input for the next steps):
- No listening check by ear or `voice_check` yet (EL-12/EL-13: Odom has no baseline, character voices are not registered
  in `config/channel_voices.json`). The owner has not heard the character voices; they were picked from preview text.
- The reads are raw (no narrator polish, no levelling, no fades). Scribe word timings not made.
- S3 scene start frames need `durations.json` for RN-03. Each line is one file, so every LTX clip's line length is known.

Deviation to log in the journal: the OR-12 rulebook gate override (card cmsg_01Hnu5zB86sjUj5GtTgaUkPWWHTR3nFtPkMUhifyeVa14L,
17:49 UTC) reached this thread after the last read had been paid. No `active_episode.json` was set, so no hook step
ran and no override file was created or needs deleting. Nothing was bypassed by file; the reads ran before the override
text arrived, which is a gap against the by-hand hook step of HANDOFF section 3.1.
