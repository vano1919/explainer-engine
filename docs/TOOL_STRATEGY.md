# Tool strategy (D-28)

Which tool makes which part of a video, what it costs, and what was measured versus assumed. Evidence comes from the
TMR repository (read-only, `vano1919/tmr-video-script-engine@d88ba8f`): `render/imagegen.py`, `render/owl_pair.py`,
`render/owl_camp.py`, `render/localimages.py`, `cloud/rp.py`, `cloud/models.json`, `docs/INCIDENTS_RUNPOD.md`.

## Who makes what

**Current routing (D-46, 2026-10-17):** every picture is painted by Gemini on the batch tier (`production/paint.py`, tiers in
`imagegen/routing.py`); narration, music and sound effects come from ElevenLabs only. The pod and Z-Image rows below are kept as
history of D-19/D-36; they are no longer used.

| Part of the video | Tool | Why | Cost | Evidence |
|---|---|---|---|---|
| Mascot pose and expression kit (made once, kept in the library) | Gemini image (`gemini-3.1-flash-image`), on a flat green background, keyed to RGBA | identity asset (D-19); the creator's references were made with Gemini; Gemini can keep one character from a reference picture | list price $0.067 (1K) / $0.101 (2K) per picture, checked 2026-10-08 in TMR, re-check before the first call | TMR keyed Gemini owls from flat green (`owl_pair.key_green`: corner-measured green, despill, 0.8 px edge blur) |
| Mouth and eye states | Gemini edits of the base pose, but only the changed region is kept | Gemini repaints the whole picture on every edit (about 5 % of pixels differ everywhere); blending whole pictures makes the character shimmer on every word | inside the kit budget | measured in TMR (`owl_pair.patch_pose` docstring) |
| World backgrounds (one per world, reused) | Z-Image-Turbo on a RunPod GPU, painted against one Gemini style reference; Gemini only for a world that the library will reuse and Z-Image cannot match | cheap, offline-licence model; no per-topic Gemini pictures (D-19) | RTX A5000 about $0.27/h; one 1536x864 picture about 14 s, so roughly $0.001 per picture plus 10-20 min of pod start-up | measured in TMR (INCIDENTS_RUNPOD 2026-10-10, 2026-10-13); licence Apache-2.0 (official model page, checked 2026-10-16) |
| Topic props and scene pictures | Z-Image-Turbo (RunPod), or the RX 5700 at home (SDXL, about 6-7 min each, free but slow) | per-topic pictures may not use Gemini | as above | TMR `localimages.py`; 13 of 23 SDXL pictures were defective in TMR run-024, so `picture_check` gates every one |
| Motion | code (Remotion): layered parallax, camera, pose tweens, bobbing, squash, glow, particles, mouth swaps on phoneme timings | image models make stills; motion in code is free, deterministic and re-renderable | $0 | D-10, D-27 |
| Explaining parts (arrows, labels, notebook doodles) | code-drawn SVG on top of the painted layers | text must be exact and editable | $0 | D-27 |
| Research and scripts | Claude Code sessions (D-13); the 7B/27B on RunPod is not used for scripts | quality of facts and imagination matters most | $0 per token | D-13; TMR's 7B needed many repairs (INCIDENTS_RUNPOD) |
| Narration | Kokoro local (D-12) | — | $0 | D-12 |
| Optional signature motion (e.g. a walk loop) | Veo, only after the kit test, only for reusable loops | expensive | about $0.96 per 8 s loop in TMR, re-check | TMR `videogen.py` |

## Rules
- Image models make **poses**, not movements. "Every possible movement" means a pose library (stand, walk contact and
  passing, point, shrug, think, surprise, run, sit, hold-prop, look-back, wave, jump) plus mouth and eye states; code
  moves between them.
- The character never contains the key green; glows (the compass, the watch) are added in code, because soft glow keys
  badly on green.
- No franchise names, actors or key art in any prompt (RR-03); this holds for Gemini and Z-Image alike.
- Every generated picture is recorded with prompt, model, seed or reference, cost and date (ASSET_SYSTEM).
- Style match between Gemini identity assets and Z-Image backgrounds is a hypothesis: the kit test includes 3 Z-Image
  backgrounds next to the Gemini mascot. If they clash, the fallback is fewer, reused Gemini world backgrounds.

## Money control for RunPod (carried over from TMR, binding)
No pod without an approved price and time cap; every pod gets `rp.py guard` (with a 2 h tool timeout) and push
notifications; `rp.py sweep` at the start and end of every session; one pod per job, deleted at the end; at 80 % of a
cap stop and ask. This project has no RunPod budget yet: the creator sets one before the first pod.

## Kit test (before any full kit)
1. Gemini, 1K: base traveller from the creator's reference 02 on flat green, then 8 poses and 4 expressions
   (13 pictures + about 30 % retries, about $1.20).
2. Key, measure identity drift (outline, scarf, satchel, face proportions) and edge quality; build one 10 s parallax
   test scene in code.
3. Z-Image: 3 world backgrounds against the same style reference (one pod session, under $0.50).
4. Creator judges; only then the full kit (about 40 pictures, about $3-4 at 1K).

## Kit test result (2026-10-16, model gemini-3.1-flash-image, 1K, list price $0.067 per picture)
Spend: 15 pictures, about $1.01 (estimate at list price; no retries were needed). Files: `assets/characters/traveller/test_v0/`
(keyed pictures, two world backgrounds, contact sheet, walk-test frames, generation ledger with every prompt).
- **Identity held** across 1 base + 8 poses + 4 expressions from one reference: face, cheeks, scarf, satchel, proportions
  and line style look the same on the contact sheet. This was judged by eye only; no numeric drift measure was made.
- **Keying works**: no green pixels left on the keyed edges (measured on 3 pictures); edges look clean on dark and light.
- **Defects found**: the scarf tail and the satchel differ per picture (the frontal expressions show the scarf hanging in
  front; the delighted picture has the satchel on the other side); a faint blue rim on shaded edges; one world
  background came with a painted paper border that must be cropped; mouth states for lip-sync are NOT tested yet (only
  four whole-face expressions).
- **Animation test** (8 s, 1080p30, built in code, 84 s to render on this sandbox, not the creator's PC): two backgrounds
  blended into one panorama, camera pan, two-frame walk cycle with bob, seam glow and particles, shadow, surprise pop,
  delighted finish. It reads as a living storybook scene; the walk is a two-pose swap, not smooth limb animation.
- **Not tested**: Z-Image backgrounds (no RunPod cap yet), so the style match between Gemini mascot and Z-Image worlds
  is still a hypothesis; mouth patches; a second world pair; consistency over many more poses.

## Cast bank result (2026-10-16): the analyst and the companion
Files: `assets/characters/crossworld_cast_v0/` (12 analyst poses and expressions, 8 companion poses, two 2K worlds, a contact
sheet, test frames, the generation ledger with all prompts).
- **Identity held** across 12 analyst and 8 companion pictures generated from one reference each, judged by eye: hat, monocle,
  neckerchief, satchel, proportions and line style repeat. Small variations: which hand holds the notebook, the monocle
  hanging in the startled pose. The companion is the easier design (no face, no limbs).
- **2K needs an explicit parameter**: asking for "2K" in the prompt text returned 1376x768; `imageConfig.imageSize: "2K"` returned
  2752x1536 (list price $0.101). Two 1K worlds ($0.13) were wasted.
- **Border defect persists**: the cold world still arrives with a painted paper edge on the top and left despite the prompt;
  crop 2-3 % of each edge in the asset step (a measured crop, to be built into the picture gate).
- **Test scene** (10 s, 2560x1440, 30 fps, code only, CPU in the cloud session: 152 s): analyst walks across the seam, startled
  pop, looks to the horizon, ends with a wry smile; the companion floats beside, changes eye state and opens its wings at the end.
  The walk is still a two-pose swap. Limbs do not move between poses; this is the ceiling of the pose-bank method.

## Sound result (2026-10-16): what Gemini can and cannot make
- Gemini has **no sound-effect model** (pricing page, 2026-10-16). Gemini TTS (`gemini-3.8-flash-tts`, $9 per 1M audio tokens
  until the end of 2026, 25 tokens per second) can make vocal reactions; Lyria (`lyria-3-clip-preview`, $0.04) makes 30 s
  music clips only (the request "about 4 seconds" returned 30.8 s, MP3 data in a .wav-named field).
- **Measured**: plain instructions ("Make only a short gasp") were read aloud by the voice (8 of 11 clips contained speech of the
  instruction, per a model listener). Bracketed tags worked: 15 of 24 tried sounds matched their intent, 5 were mislabelled by
  the listener (gasp heard as snicker, chuckle as gasp, sniff as groan, gulp as sigh), 4 failed on rate limits (HTTP 429 with 4 parallel
  calls). One uncapped call ran 458 s and cost about $0.10; every later call carries `maxOutputTokens`.
- **The model listener is weak** (it disagreed with itself between runs); only the creator's ears count (`review.human`).
- Result: 63 sounds in the library: 21 foley types x 1-3 takes (45 files, procedural, free), 15 vocal reactions, 3 music clips.
  Audio spend about $0.26 (estimate).

