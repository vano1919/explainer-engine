# J5 dialogue test brief (creator 2026-11-06 16:44 UTC, msg cmsg_01Hnu5zB86sjUj5GtTgaUkPWBgAsiH8wqy5vS2D2SXi7bH)

His words: "Can we test J5 now? With the existing pictures build a dialogue photo-collage, show me, I'll confirm; then add voice,
emotion, mouth movement and motion imitations in the background."

FREE ONLY. No pod, no paid call. Two steps with his approval between them. Report to the Fable thread
(cmsg_01Hnu5zB86sjUj5GtTgaUkPWSDJ6dN9sdcVPJPP6ZJszpc); questions as 4-option items there.

## Inputs (already paid for, on HF vano1919/tmr-artifacts, dataset)
- 360° / wide backdrops: route_test_2026-11/assets/A/ (A1_tent, A2_courtyard, A3_field, A4_ship).
- Hero sheets, flat-lit: route_test_2026-11/assets/B/ (B_H1 commander, B_H2 scout, B_H3; front, back, left34, right34).
- Same hero in environments: route_test_2026-11/assets/C/.
- Code: blender/assemble_25d.py (J5 2.5D: camera projection + cards), edit/cutout.py (BiRefNet; the dtype fix is on icw/16-lean-pod
  0fa738b; on CPU here, free), production rules for J5 (FINAL_HIGH_LEVEL_PLAN_ka.md §9: mouth = 3 states + 2-frame cross-blend,
  dialogue angles without a visible mouth where possible).

## Step 1 (now): the collage
- One dialogue scene, two heroes (H1 commander + H2 scout) in ONE backdrop (A1_tent recommended: an interior, dialogue-friendly).
- 3-4 frames of the scene as J5 would cut it: establishing two-shot, over-the-shoulder H1→H2, over-the-shoulder H2→H1, one close-up.
  Same backdrop, consistent screen direction (180° rule), heroes cut out (BiRefNet) and placed as cards in Blender 2.5D,
  contact shadow, a light harmonise if the code has one (no paid repaint).
- Render stills at 2560x1440 (EEVEE, this container or CI), one contact sheet, upload to HF route_test_2026-11/j5_dialogue/step1/.
- Send the sheet path to the Fable thread. STOP: wait for the creator's OK (Fable relays it).

## Step 2 (after his OK only)
- Voice: reuse an existing recorded take (project files voice/line_1.wav or earlier ElevenLabs takes in the ledger), no new
  ElevenLabs call without his separate yes (feedback rule 11-01).
- Mouth: 3 states + 2-frame cross-blend on the speaking card, from word timings (Scribe timings if the take has them, else local).
- Emotion: brow/eye state per line (the cards' expression variants if they exist; else say what is missing, do not invent).
- Background motion imitation: slow parallax/camera drift, firelight flicker, smoke/dust layer (cheap 2D, no LTX).
- 10-15 s clip at 24 fps, 2560x1440, sound in, upload to HF route_test_2026-11/j5_dialogue/step2/, seconds per frame recorded.

## Deliver
Step 1 sheet; then step 2 clip with HF links; a PROGRESS entry and any code on a branch off icw/05c-ink-round with a PR (never main).
