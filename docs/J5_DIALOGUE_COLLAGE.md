# J5 dialogue collage: the procedure, step by step

> **Route-scoped since D-116 (2026-11-06):** this page belongs to route J5 (Qwen assets + Blender 2.5D, no LTX); the route decision is in the
> [decision log](DECISIONS_AND_OPEN_QUESTIONS.md) (D-116).

Source: the J5 dialogue test of 2026-11-06 (creator 16:44, 16:55, 17:25 and 17:26 UTC; thread "Test J5 dialogue with existing photos",
PR #151). Everything here was done free (CPU Blender 5.2.3, BiRefNet on the CPU, numpy/OpenCV/ffmpeg) and every number below is the one
that was used. It is a record to be turned into a standard, not a finished rule set: nothing in it is a validator threshold, and the
parts the test could not settle are listed at the end. The route itself is [ROUTE_PLAN_2026-11-06](architecture/ROUTE_PLAN_2026-11-06.md);
the asset contract and the cut-out rules are [SCENE_ASSETS](SCENE_ASSETS.md).

Code: `explainer_engine/blender/j5_collage.py` (step 1: stills), `explainer_engine/blender/j5_background.py` (step 2: motion),
the `transparent` job flag of `blender/bpy/assemble_25d.py`, `edit/cutout.py`. Tests: `tests/unit/test_j5_collage.py`,
`tests/unit/test_j5_background.py`.

## 0. Inputs and environment

- Pictures (HF `vano1919/tmr-artifacts`, `route_test_2026-11/assets/`): the backdrop `A/A1_tent.png` (2048x1024), the hero sheets
  `B/B_H1_*` (commander) and `B/B_H2_*` (scout), flat-lit on a plain neutral background, 1280x720 each.
- A bare cloud container needs: `apt-get install libegl1 libegl-mesa0 libgl1-mesa-dri libgbm1 ffmpeg`, a venv with `bpy==5.2.3`
  (the pinned Blender), `numpy pillow opencv-python-headless scipy`, and for the cut-out `torch` (CPU wheel), `torchvision`,
  `transformers`, `timm`, `kornia`, `einops`. Blender runs through the bpy wheel (`--bpy-python`), no binary download.
- The BiRefNet dtype fix of `icw/16-lean-pod` (0fa738b) is in `edit/cutout.py`.

## 1. Cut-out (free, CPU)

1. `edit.cutout.birefnet_mask(image)` for every sheet used (about 20 s each on 4 cores, the model loads once per call).
2. `edit.cutout.finish(image, mask)`: 2 px soft edge, edge colour taken from the nearest opaque pixel (no halo). `check` flags
   AC-15 when the figure touches the bottom edge: that is expected for the commander's sheets (see "What the sheets cannot give").
3. In `j5_collage.clean_cut`: the alpha is eroded by 1 px (3x3) and feathered by sigma 0.7, and the card is mirrored only where a
   reverse shot needs the other facing (the commander's back view in the reverse shot).

## 2. Scale, eye-line and camera

- Card height in metres comes from the alpha box of the figure. The scout is a whole figure: 1.65 m, feet at z = 0. The commander's
  sheets end at the belt: the bust card is 0.85 m tall and its bottom stands 0.91 m above the ground (heads then measure 0.27 m and
  0.23 m as rendered; a four-head figure is about 1.9 m). Both pairs of eyes then sit within 0.06 m of the camera's height.
- Cards face the camera (the planner's `_facing`), so the angle image carries the apparent facing: the scout (screen left) uses his
  right-facing card, the commander (screen right) his left-facing card; they look at each other.
- Positions: the scout (-0.7, 3.8), the commander (0.55, 3.8), the fire at (0, 9, 0.6): behind and between them in the two-shot.
- Four shots, all on one side of the line between the two heroes (180-degree rule), camera height 1.6 m, level, 24 fps master
  2560x1440, sensor 36 mm horizontal:

| Shot | Lens | Camera | Looks at | What it shows |
|---|---|---|---|---|
| S1 medium two-shot | 60 mm | (0, 0, 1.6) | straight ahead | both, the fire between them |
| S2 over the scout's shoulder | 60 mm | (-2.8, 2.4, 1.6) | the commander's face | the scout's back blurred and dark in front |
| S3 reverse over the commander's shoulder | 60 mm | (2.7, 2.4, 1.6) | the scout's face | the commander's back (mirrored) in front |
| S4 close-up of the commander | 70 mm | (-0.2, 0.6, 1.62) | the commander's face | his eye-line goes left to the scout |

- The lens is chosen so that the frame's bottom edge is at or above the bottom of the commander's card: 0.91 m at the
  commander's distance. `tests/unit/test_j5_collage.py` checks it for every shot.

## 3. The backdrop

A 360 equirect of 2048 px gives about 250 px across a 44-degree frame (10 times soft), so each shot uses a flat crop of the painted A1
as a plate 40 m away (a card of the planner's kind): S1 `(220, 11, 1780, 889)`, S2 `(1100, 183, 2048, 717)`, S3 `(0, 183, 950, 717)`,
S4 `(1150, 253, 1850, 647)` (A1 pixels, 16:9, the horizon row 450 at the frame's middle). Lanczos enlargement, then an unsharp mask
(1.35 / -0.35, sigma 1.6). The crop follows the camera's real azimuth, so the fire's glow is on the side the fire is on in each shot.

## 4. Light and colour of the cards (`grade_card`, `face_shadow`)

One light: the fire. Per card `lateral` (-1 camera-left .. +1 camera-right) is the screen distance from the fire to the card's middle,
divided by half a frame, clipped. Then, in this order:

1. Ambient: the card colour times the dusk ambient (0.50, 0.45, 0.64) on the shade side; on the lit side the ambient times 0.95 plus the
   fire's colour (1.0, 0.58, 0.22) times 0.50. The lit weight is a smoothstep across the figure's width toward the fire.
2. Face (cards that show a face, measured once per sheet in `FACE`): the half of the head that turns from the fire falls into a cool shade
   (multiply toward (0.60, 0.56, 0.82), 0.72 strength, soft terminator); a shadow under the brow ridge (0.20); the chin throws a soft
   shadow down onto the collar or the fur, away from the fire (0.55). Back views get none (no face).
3. Ground bounce: the lower quarter takes a warm 0.10.
4. Rims, from the card's alpha edge normals: a warm rim on the contour that faces the fire (0.85), a cool sky rim on top (0.35).
5. Blacks lifted toward the backdrop's darkest tone (0.09, 0.065, 0.14) by 0.55 of what is missing.
6. A foreground shoulder is multiplied by 0.68 (`dark`).

## 5. Blender passes (free, EEVEE on CPU)

`blender_layers`: the plate and every card are rendered alone, one pass each, at 2560x1440 with 8 samples; the cards' passes use the
`transparent` flag (film transparent, RGBA). 3.4-5.8 s per pass, whole sheet of four shots about 95 s on 4 cores. The cards are emission
only (no light, no cast shadow in Blender): all lighting is the grade above.

## 6. Composite and finish (`compose`)

Back to front by distance from the camera. The plate is blurred by the shot's sigma (S1 3, S2/S3 9, S4 14 at 2560 px), a foreground
shoulder by 5, the middle hero by 0. Then the fire's bloom (threshold (0.62, 0.40, 0.18), sigma 30, strength 0.55), a vignette (0.32 at the
corners) and one shared grain layer: fine 0.017, mid mottling 0.045 (sigma 5), long unevenness 0.26 (sigma 40), weighted toward the mid
tones. The same chain on the plate alone gives `backdrop_only.png`; the comparison of both is the "does it read pasted" check.

## 7. Motion of the background (`j5_background`, step 2)

All of it a function of the time `t` only. The plate is built 12 % larger than the frame; the camera moves over it.

- **One flicker** `flicker(t)`: value noise at 9 Hz (0.50) and 17 Hz (0.30) plus a 2.1 Hz sine (0.20). The ground glow, the flame, the
  embers and the warm side of the cards all take it, so the light on the heroes and the fire agree.
- **Flame**: cut from A1 by colour (R > 190, G > 70, R - B > 110 inside the fire box), licked upward by a scrolling noise displacement
  (up to 9 px sideways, 8 px up, growing with height), brightness 1 + 0.16 f.
- **Smoke**: fractal noise scrolled up 35-60 px/s, a column that widens from 34 to 96 px, warm at the base and cool above, alpha at most 0.42.
- **Embers**: 70 particles, life 2.8 s, rising 55-130 px/s, a sine drift, a flicker of their own; **dust/bokeh**: 16 soft circles in front of
  everything at half resolution (alpha 0.10).
- **Banners**: five banners (boxes and poles in `BANNERS`), colour mask, a travelling sine displacement growing from the pole (up to 9 px).
- **Ground fog**: a noise band around the horizon row, alpha at most 0.14, drifting.
- **Camera**: per shot a push-in or a truck: plate zoom 1.0 to 1.02-1.03, cards 1.03-1.055, parallax plate : middle : foreground = 0.3 : 0.65 :
  1.0, the foreground shifts 70 px on the trucking shots; cards breathe 0.5 % at 0.25 Hz about the frame bottom.
- **Ambience** (synthesised, no voice, no paid call): Poisson crackle (16 clicks/s small, 1.4/s large) band-passed 0.9-7 kHz, a low roar
  below 260 Hz, a slow wind 120-520 Hz; stereo, 48 kHz, 0.25 s fades.
- Cut order of the 12.5 s clip: S1 3.5 s, S2 3.0 s, S4 3.0 s, S3 3.0 s. One mp4 segment per shot (a finished segment is skipped on a
  re-run, RULE-R1), joined with `ffmpeg -c:v copy` and AAC 192 kb/s. x264 crf 14, yuv420p.

## 7b. Step 3: figures that breathe, shots that dissolve (creator 17:53 UTC)

The creator's note on the step-2 clip: the cuts between shots are too abrupt, and the people stand stiff. Both are in `j5_background.py`.

- **Idle motion of a figure** (`idle`, constants `IDLE`): a displacement field on each card, a function of `t` only, in shares of the card's
  visible height `H` (so it scales with the shot): body sway about the card's bottom edge 0.50 % H at the top (weight `h^1.6`, `h` = height
  above the bottom), head turn 0.30 % H, nod 0.22 % H, chest breath 0.20 % H (a Gaussian band just below the head), cloth and fur ripple
  0.12 % H (a sine travelling up the body, strength 0.6 + 0.4 x the fire's flicker). Every movement is two sines of unrelated frequencies
  (0.11/0.19, 0.17/0.29, 0.23/0.41, 0.27 Hz), phase per figure from its id, so the two men never move together. The head's share of the card is
  `HEAD_M` (0.24 m) over the metres the frame shows of the card. A foreground shoulder moves at 0.55 of that. The old whole-card 0.5 %
  scale breath is gone (it stretched the figure). Measured: the alpha mass changes by under 1.5 % (nothing stretches) and the rows at the
  card's bottom move under 0.3 px.
- **Camera on an ease-in-out curve**: the shot's push and truck follow smoothstep, so each shot starts and ends slowly and the cut does
  not land in the middle of a move.
- **Dip to black** (`DIP` = `fadeblack`, the creator's pick over the cross-dissolve, 18:11 UTC; `--transition fade` gives the dissolve, which
  shows a ghost of the other shot's figure for a moment). `DISSOLVE` = 10 frames, 0.42 s: the earlier shot is drawn 10 frames longer with the camera at rest (its `tail`), and ffmpeg's
  `xfade` blends it into the first 10 frames of the next. The cuts stay on the nominal clock (3.5 / 3.0 / 3.0 / 3.0 s); the fire is in
  every shot at about the same screen height, so the light carries over the blend. The ambience is one continuous track and does not
  restart at a cut.
- **Next render (creator 18:11 UTC):** make the dip slower (try 16-18 frames, about 0.7 s); `DISSOLVE` and the bound in
  `test_dissolve_is_short_and_the_cut_order_stays_on_the_nominal_clock` change together. Not re-rendered yet.
- **Not done:** an L- or J-cut (the next shot's sound arriving before its picture) needs a voice; there is none until the creator's yes
  to a new take. The commander's proportions come from his belt-up sheets and are not fixed by motion.

## 8. Measured (cloud container, 4 CPU cores, no GPU)

Cut-out: about 20 s per sheet. Blender layer passes: 3.4-5.8 s each, 95 s for the four shots. Motion: 1.3 s per frame, 300 frames in about
2.5 minutes with the four segments in parallel. Files: the 12.5 s clip is 125 MB at crf 14 (grain makes it heavy; a crf 21 preview is 33 MB).
HF: `route_test_2026-11/j5_dialogue/step1/` (first stills) and `step2/` (clip, preview, ambience, stills v2 with the face shadow).

## 9. Commands

```
python -m explainer_engine.blender.j5_collage render --inputs IN --out OUT --bpy-python VENV/bin/python
python -m explainer_engine.blender.j5_background render --collage OUT --inputs IN --out OUT2 [--shots S1_two_shot]
```
`IN` holds `A1_tent.png` and the `<sheet>.cut.png` files of section 1. 1.3 s per frame at 2560x1440 on 4 cores for the motion step.

## 10. What the sheets could not give (to settle before this becomes a standard)

- The commander's sheets end at the belt: no standing wide shot, no feet, no contact shadow or ground occlusion in any frame. A full-body
  commander sheet is a Qwen edit (paid, the creator's call).
- The scout has no left-facing card (his right-facing one nearly looks at the camera, so his eye-line to the commander is weak);
  `assets/E/E_B_H2_left34` exists and was not tried.
- Mouth states and an eyes-closed patch do not exist for any card, so no lip-sync, blink or brow animation yet (SCENE_ASSETS SA-06 needs them).
  The voice step uses an existing take only; no ElevenLabs call without the creator's separate yes.
- The ambience is synthesised and unmixed against a narrator; level and mix belong to the audio spine.
- A one-pixel hairline in the painted A1 (row about 375, to the right of the middle) survives in the S2/S4 plates; it is in the source picture.
- Not measured: how this reads to the creator against a Blender 3D set, and whether the flat plates need parallax from a real depth map.
