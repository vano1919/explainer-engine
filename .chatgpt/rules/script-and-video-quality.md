# ChatGPT script and final-video quality rules

## Script gate
- Separate narration lines into `fact`, `analysis`, `speculation`, `joke` or `transition`.
- A factual line must reference claim IDs. Each claim must link to source IDs, a recorded passage and an uncertainty/confidence label.
- A direct or important factual claim needs one grade-A primary source or at least two independent grade-B/C sources. Grade-D sources never establish a claim alone.
- Speculation must be labelled as reasoning or a guess; it cannot silently become a factual assertion.
- The independent review report must be bound to the exact production-script SHA-256. Stale reports fail.
- Required rubric thresholds: factual reliability >= 4/5; source coverage >= 4/5; title/thumbnail alignment >= 4/5; every other criterion >= 3/5; mean >= 3.8/5; zero unresolved critical blockers.

## Narration, audio and edit
- Verify the actual promise/payoff before asset spending. Hook, character stakes, cause/effect, reversals, open loops and ending must form one story, not adjacent jokes or a list of facts.
- Pictures must show the exact story state and action described at the anchor phrase. No future object/event may appear before narration reveals it.
- Narration timings control cuts. Never cut words to force a desired shot duration. If no legal pause exists, rewrite/re-read, merge or hold; do not cut inside speech.
- Audio is judged by measurement and listening: consistent voice identity, clear consonants, emotional range, music ducking, no masking, no destructive silence edits, no clipped words.
- Music and SFX need an explicit narrative function and timeline. Prefer fewer, well-timed sounds to a constant effect layer.
- QA examines the rendered result: representative frames, transitions, captions, shot-to-line alignment, loudness, true peak, sync and missing/frozen frames. File existence is not acceptance.
