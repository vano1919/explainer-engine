# Tool strategy (D-28)

Which tool makes which part of a video, what it costs, and what was measured versus assumed. Evidence comes from the
TMR repository (read-only, `vano1919/tmr-video-script-engine@d88ba8f`): `render/imagegen.py`, `render/owl_pair.py`,
`render/owl_camp.py`, `render/localimages.py`, `cloud/rp.py`, `cloud/models.json`, `docs/INCIDENTS_RUNPOD.md`.

## Who makes what

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
