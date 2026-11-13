# GEMINI.md — pointer

> **Updated 2026-11-12 (D-131):** the 9-gate protocol (G0..G8, the Gemini batch image generator, Thread A / Thread B) that
> this file described came from the v4.3 archive and is superseded by D-131; it stays readable in git history only.

What the Gemini chat does in a v4.3 episode:

1. **Pictures, free:** the chat's built-in image tool draws the episode's pictures in turns of 6-12, exported as turn packs and
   gated at intake (`imagegen/turn_pack`, rules GC-01..GC-17 in [`docs/GEMINI_CONSISTENCY_RULES.md`](docs/GEMINI_CONSISTENCY_RULES.md)),
   then upscaled 2x locally. Only a failing close-up hero shot is re-made at 2K on the paid batch tier, priced and asked first.
2. **Research and reviews** where the creator asks for them (about 90 % reliable, the creator 2026-11-07: used as guidance at once,
   the registry grade still follows D-59).

Everything else (the script, the routes `map_action` / `still_25d` / `wan`, the runner's gates, money) lives in [`CLAUDE.md`](CLAUDE.md)
and [`docs/EPISODE_FIRST.md`](docs/EPISODE_FIRST.md). No paid Gemini API call without the creator's word (`config/spend_caps.json`
`gemini_api`).
