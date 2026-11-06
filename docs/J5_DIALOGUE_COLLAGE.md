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

## 7c. Step 4: voice, mouth, blinks, brows (creator 18:34 UTC: "1 and 2, go"; credit cap 5000)

Code: `explainer_engine/blender/j5_face.py` (+ hooks in `j5_background.idle`, `mix_voice`). Test: `tests/unit/test_j5_face.py`.

- **Voice** (paid, one take per line, `eleven_v4`, `generations_count` 1, estimate first): three lines written for the test, 155 credits in all
  (cap 5000). The commander is Tucker Thomas (`EI3BL0ECeQayX8N4doHx`, old, deep, American), the scout is Cam (`GJr7Bxt1U0WeEWxRk8n6`, young,
  American): both picked from `creative_list_voices` by description, not by listening (EL-01 asks for a listening test; this is a test
  clip). Lines: scout "[quietly] The scouts are back, sir. The pass is open." (2.8 s, 53 credits); commander "[calmly] Then we march
  before dawn. Tell the men to rest. Tomorrow will not be kind." (5.68 s, 84); scout "[softly] Yes, sir." (1.12 s, 18). Placed in the clip at
  0.35 s, 3.80 s and 10.05 s (`LINES`) so each starts after the dip into its shot and ends before the dip out.
- **Mouth shapes** from the audio by Rhubarb Lip Sync 1.14.0 (MIT, github.com/DanielSWolf/rhubarb-lip-sync, Linux release binary,
  `rhubarb -f json -d <line text> --extendedShapes GHX`): shapes A-H and X per 10-150 ms. `F.mouth_state` eases over 55 ms.
- **Where the face is** (`ShotAssets._mapper`): the exact projection of a sheet pixel into the frame, built from the same numbers the Blender
  job gets (`card_geometry` of the graded card, the card turned to face the camera, `j5_collage.project`). A first try that matched alpha boxes
  put the mouth on the nose (the box of a cut-off figure lies); the projection puts eyes and mouth on the drawing (checked with markers).
- **Features** (`FEATURES`, sheet pixels, measured on zoomed crops): eyes, brows, mouth centre and lip band for `B_H1_left34` and
  `B_H2_right34`. A face card without an entry (the back views) gets nothing.
- **Mouth**: the part of the face below the mouth line is displaced down by the jaw (6 sheet px for the commander, 4.5 for the scout, times the
  shape's opening), the beard goes with it; a dark opening (outline ring + inside, colour from the card's own brightness) is drawn between
  the lips, width by the shape (E 0.72, F 0.55). **Blink**: a skin-coloured lid (sampled from the graded card under the eye) slides down over
  an ellipse a little larger than the eye, with a lash line on its edge; 0.2 s, first blink 0.8-1.6 s into a shot, then every 1.5-2.6 s.
- **Emotion** (`EXPR`): a speaking commander has his brows lowered (-0.35, about 0.7 px at 2560 per unit of 2 px) and lifts them with open sounds
  (+0.55 x opening) and squints 14 %; a listener's brows rise (+0.40, slowly alive). Brows move by a Gaussian bump of the image.
- **Mix** (`mix_voice`): ambience x 0.55 lowered by 8 dB while anyone speaks, each line peak 0.85, the sum limited to 0.9. A review mix, not the
  audio spine's levelling.
- **Fixes after the creator's first look (18:56 UTC: half the body moved with the jaw; the mouth was a black hole; the clip felt slow):**
  the jaw weight now lives only between the lips and a chin's height below the chin (`chin_y` per sheet) and fades sideways within 1.25 mouth
  widths, so neck, collar and armour stay; the opening is shaded (roof `INTERIOR`, lighter `TONGUE` toward the bottom, a strip of upper teeth on
  wide openings for the scout, none for the bearded commander) and the commander's is smaller (40 px sheet width, jaw 5.5); for liveliness the head dips with every
  open sound (`EXPR["bob"]`, 0.45 % of the card, a third of that for a listener) and the camera pushes harder (plate 3.5-5 %, cards 6-10 %, foreground
  truck 110 px). Snappiness in the sense of cutting rhythm and exaggerated acting is not solved by this and stays open.
- **Honest limits**: the mouth is a shaded ellipse on a flat painting, not a drawn mouth; the lid on the scout's
  cartoon eyes hides their black outline; no head turn on a vowel; the two eyes of the commander share one skin sample. A real fix is
  drawn mouth/eye variants per sheet (SA-06), which would be a paid Qwen edit.

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
- Mouth states and an eyes-closed patch do not exist for any card (SCENE_ASSETS SA-06 needs them); step 4 draws them procedurally (7c), which
  is a stand-in, not the asset.
- The ambience is synthesised and unmixed against a narrator; level and mix belong to the audio spine.
- A one-pixel hairline in the painted A1 (row about 375, to the right of the middle) survives in the S2/S4 plates; it is in the source picture.
- Not measured: how this reads to the creator against a Blender 3D set, and whether the flat plates need parallax from a real depth map.

## 7d. Step 4c: straight cuts, young scout voice, one level (2026-11-06)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX.

- **Straight cuts (creator, 19:14 UTC).** The dip to black "does not suit it"; shots now cut directly, as in a film. `DIP = "cut"`: no
  dissolve tail frames are rendered and `join` concatenates the segments. `fadeblack`/`fade` stay selectable with `--transition`.
  The earlier "slower dip next time" note is void.
- **Voice (19:13).** The scout is a boy, so his two lines were re-made with a young male voice (Ben Young Man, 2 takes, 71 credits;
  ElevenLabs ledger total 226 of the 5000 cap). Rhubarb cues were regenerated for them.
- **Sound jumps.** Lines were peak-normalised, so a quiet take sat 14 dB under the commander. Every line is now scaled to one speech RMS
  with a soft limiter (measured: -18.8 to -21.5 dBFS RMS across the three lines), shared room reverb, 20 ms edge fades, 6 dB duck with 0.4 s ramps.
- **Head jumps (19:12).** `F.drive` envelopes (0.35 s in, 0.5 s out) and a 150 ms low-passed mouth opening replace on/off toggles;
  `test_j5_face` has a no-jump test.

## 7e. Step 4d: the jaw no longer slides (creator, 19:28 UTC)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX.

Cause: the chin zone was displaced by the full jaw drop, so a bearded chin slid down like a mask. Drawn 2D characters do not move the
chin that way: the mouth shape changes in place and the head nods a little. `FEATURES[...]["move"]` now scales the chin displacement
(commander 0.12, scout 0.4); the painted mouth opening keeps its full size. Techniques searched: GitHub search is limited to this session's
repositories, so the rule is taken from 2D viseme practice (Rhubarb's own mouth-shape set: swap shapes, do not warp the face).
Open: a true shape swap needs drawn mouth variants per sheet (paid Qwen edit, the creator's call); the whole-head nod is the remaining motion.

## 7f. Variant sheets instead of a picture per mouth (creator, 19:41 UTC, D-119)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX.

One Qwen picture per hero holds the 8 variants of the moving part (A-F, two blinks) in a 4x2 grid of 512x512 cells, 32 px gutters and margins,
2208x1120 (`j5_variant_sheet.py`, the layout constant both the pod job and the cutter import). `build_input_sheet` makes the picture Qwen
is asked to vary (the neutral head, upscaled, in all cells); `cut_cells` cuts the answer; `align` finds translation and scale on the stable
upper face (template search over scales 0.94-1.06 and +-24 px, sub-pixel, no warp); `check_cell` reports registration error, score and an identity
score (gradient-orientation descriptor outside the moving parts, a proxy, not a face-embedding model); `variant_sheets` puts each cell's mouth or
eyes into the hero sheet through the feathered mask (pixels outside the mask stay the sheet's own); `blend_sheet` mixes them with the cue
weights (`j5_face.cue_weights`, 55 ms). Tested on a synthetic sheet only: no real Qwen sheet exists yet, so the real registration error and identity
numbers are still to be measured. Wiring `blend_sheet` into the card renderer waits for the real sheets.

Two layouts are comparable by one constant (2026-11-06 19:46 UTC): `LAYOUTS` holds "A" (4x2 cells of 512 px on 2208x1120, about 2.5 MP) and "B" (4x2 cells of
304 px on 1280x720), `LAYOUT` picks the default, every function takes `layout=`, and `cut_cells` finds the layout from the image size, so the cutter does not
depend on which one the pod drew. The first mouth pod draws one H1 sheet in each at the same seed; the winner is chosen by the per-cell identity score and the
registration error, then H2 is drawn in the winner.

## 7g. Cutting a multi-angle dialogue (creator, 19:52-19:57 UTC)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX.

Finding: step 4e cut S2 -> S4, the same commander from the same side, only closer: a jump, not a change of angle. The repository already has the rule
(BP-30: the shot size changes by a full step, never the same framing twice; a direction change over 90 degrees needs a neutral picture between; BP-103: two cuts of nearly the same
size and angle read as a jump, the 30-degree rule; ED-14 / BP-117: J and L cuts), but `dialogue-scenes` and the J5 shot table did not apply it to a hero's angle. The Blender and LTX rule
files hold no dialogue-coverage rule. Practice found on the web (a vendor glossary and one practitioner article, so a rule of thumb, not a study): shot / reverse shot with matching
eyelines, the camera stays on one side of the axis (180-degree rule), at least 30 degrees or a full size step when the same subject is cut to again, cut on action, and for generated video
"log each character's eyeline direction per shot" (HackerNoon, screen-direction workflow); a January 2026 paper (arXiv 2601.17737) plans shots from dialogue and carries identity with first and last frames.

The standard for J5 dialogue, as code in `explainer_engine/blender/j5_cuts.py` (`lint`, tested):
1. A cut changes the SUBJECT (the other hero, motivated by the speaker change or a reaction) or the ANGLE of the same hero by 30 degrees or more (another sheet: front, 3/4 left, 3/4 right, back) and also a full size step.
2. A size change on the same hero and the same sheet is a camera move INSIDE one shot (a slow push-in), never a cut.
3. The two heroes keep their sides of the frame in every shot (180-degree rule); eyelines point at each other.
4. Sound leads or trails the picture at the cut (J and L cuts); the line starts after the cut, not on it.
Available angles today: the commander has front, back, 3/4 left and 3/4 right sheets; the scout has front, back and 3/4 right (no 3/4 left). Step 4f cuts S1 (two-shot, scout speaking) -> S2 (commander, one 6 s shot with a push-in) -> S3 (scout's answer from the reverse side) and passes the lint.

## 7h. Final dialogue rules, from the first photo frame to the last cut (creator, 20:00 UTC; BP-176, BP-177)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX.

Sources re-checked on 2026-11-06 20:00-20:15 UTC, three types: article (Wikipedia, 30-degree rule, quoting Corrigan and White: "to emphasize the motivation for the cut by giving a substantially
different view of the action"; Wikipedia, Camera coverage: master shot first, all coverage obeys the 180-degree rule, call-and-answer shots keep the same lens and distance); books (Mascelli, *The Five C's of
Cinematography*: screen direction and eyeline; Murch, *In the Blink of an Eye*: the rule of six, cut by giving up the lowest first; both through secondary summaries, not the books themselves); a video
(*Most AI Filmmakers Ignore This Rule*, transcript read through vidIQ, 5 credits: establish the two-shot first, derive every coverage picture from it, keep each hero on one side looking one way, move the camera
at least 30 degrees, log the eyeline per shot before generating the performance). Not verified: a UChicago study on dialogue cut points (the PDF could not be read). Cost: 5 vidIQ credits.

**At the plan (before any picture, `j5_cuts.plan_check`, BP-177):** every shot names subject, sheet view, size, sides of the frame, each hero's eyeline and, after the first, the motivation of the cut; the first
picture is the WIDE two-shot of both heroes; the hero on the left looks right and the other looks left; no later shot changes sides or eyelines.
**At picture generation:** the master two-shot is generated first; every over-the-shoulder, single or reaction picture is derived from it (the master as the reference image), keeps the sides and eyelines, and shows
only what its clip needs (standing order 14). A picture needs a sheet whose view fits the angle (the scout has no 3/4-left sheet: a shot needing it is replanned or the sheet is drawn first).
**At the cut (`j5_cuts.lint`, BP-176):** the subject changes (speaker change, reaction) or the angle on the same hero changes by 30 degrees or more together with a full size step; the same hero closer from the same side is a push-in inside one shot.
**At the sound:** the line starts after the cut or the sound leads or trails it (J and L cuts, ED-14, BP-117).

## 7i. How well the rules are verified, and cheap cuts that reuse pictures (creator, 20:13 UTC; BP-178)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX.

**What is verified, what is not (2026-11-06).** Read in full: the 30-degree rule page and the camera coverage page (Wikipedia), the transcript of the AI-dialogue video, Murch's own words
in an interview ("Emotion, Story and Rhythm are the top three"; "let go from the bottom of the list up"; "2D is just the 180 degree rule"; among the top three sacrifice rhythm first), the limited-animation page (Wikipedia).
Seen only through search summaries: Mascelli's book (screen direction, eyeline, continuity cutting) and the book text of Murch. Not verified: the UChicago dialogue-cut study (unreadable PDF), the claims of a dialogue-editing guide that reads auto-generated, every retention number for
punch-ins (creator tutorials, anecdotal), and any animation-studio source (only an anecdotal comment that breaking the 180-degree rule is taboo in animated features). So BP-176 and BP-177 have article + book + video; BP-178 is a hypothesis (REVIEW only).
Nuance found: the camera coverage page lists the cut-in (a tighter shot from the master's angle) as ordinary coverage and the 30-degree page names the axial cut as an established classical exception (20 mm rule), so BP-176 is stricter than the books on purpose:
the creator's complaint stands and a same-angle cut is allowed only as a declared axial cut-in of two size steps (wide to close).

**Cheap cuts and reuse (all checked by `j5_cuts.lint` / `plan_check`):**
| Technique | What it is | Rule |
|---|---|---|
| Push-in inside one shot | the camera moves closer on the same hero, no cut | free, preferred for a speaking hero (BP-176) |
| Punch-in | cut to the same subject, same angle, frame scaled 1.06-1.15, declared `cut: punch_in`, one per 3 s at most | a deliberate jump (BP-178, REVIEW); hides a cut, adds rhythm; use rarely |
| Axial cut-in | same angle, wide to close | declared `cut: axial`, two size steps (BP-176) |
| Reuse of a picture | a later shot shows an earlier picture with another crop, zoom or slight angle | `reuse_of: <earlier shot>`, same subject and sheet view (BP-178; the creator, 2026-10-25: a new picture only when the shot needs one) |
| Hold / reaction | the picture stays while the other hero speaks; cut to the listener on the line's end | free; no new picture |
| Mouth-only movement | the body stays one drawing, only the mouth and blink change | the variant sheet (D-119) |
| Camera move over a still | a pan or push on one drawing | the J5 cards already do this |
Limits: a punch-in on a bad crop loses sharpness (scale stays modest); reuse that needs a cut-out or compositing is only done when it works simply (the creator, 2026-11-01).

## 7j. A minute of several scenes: non-dialogue editing, transitions and the still lane (creator, 20:17 UTC; BP-179, BP-180, BP-181)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX.

**What was read (2026-11-06, Wikipedia, full pages):** Film editing, Cut (filmmaking), Montage, Match cut, Continuity editing, Dissolve, Fade, Jump cut, Cross-cutting, Ken Burns effect, Multiplane camera, Twelve basic principles of animation,
Shot reverse shot, Kuleshov effect, Establishing shot, Cutaway, Split edit, Shot (filmmaking), Rule of thirds, Headroom, Animatic, Cutout animation, Parallax scrolling, Limited animation, Camera coverage, 30-degree rule. The Wipe and Pan pages and the
Soviet-montage pages gave nothing usable. This is about 25 pages, not "all of Wikipedia"; one source type (article), so BP-179..181 are hypotheses: REVIEW lines, never FAIL, until a book or a video backs them.

| Need | Rule (registry id) | What the lint checks (`j5_montage.lint_montage`) |
|---|---|---|
| Transition between photos | the straight cut is the default; a dissolve = another place or time (0.5-2.0 s); a fade to black only closes the film or a chapter; no wipes; a match cut needs a shared tag; a cutaway shows something related (BP-179) | dissolve inside one scene, dissolve length, fade spacing, match tag |
| New scene | opens with an establishing wide shot, then closer coverage (BP-180) | first shot of a scene is wide or declared establishing |
| Order and rhythm | cross-cut two lines of action with a reason; screen direction of a travelling subject stays; no undeclared jump cut; stills at most 5 s, video by BP-108 (BP-180) | direction flips, `j5_cuts.lint` per scene, durations, runtime minus dissolve overlaps |
| 30 % still lane keeping the animated look | a still always moves: Ken Burns push, pull or pan of scale 1.04-1.25, or parallax of 3 or more depth layers; limited animation moves only what must (BP-181) | still without motion, scale range, layer count |
| Style preservation | one plate brightness inside a scene (ratio at most 1.25); the subject on a third with headroom (BP-181) | luma ratio between neighbouring shots; thirds and headroom are a craft check at the picture, not yet code |

**The minute (plan, nothing rendered or billed):** `explainer_engine/blender/j5_minute.py`, five scenes, 14 shots, 60.0 s, three heroes (commander H1, scout H2, elder H3) plus the crowds of the existing D pictures.
1. Title map (helper, 3 s) then the rain march: D4 wide with a push-in, a close-up of the drummer boy cut from the same picture (declared axial cut-in, reuse), H1 from behind leading the column over the A3 field.
2. Dissolve (1 s) to the tent: A1 wide with parallax, then the dialogue as cut in 4f (two-shot, commander, scout), the elder H3 as a cutaway, and the D6 face close-up as the decision.
3. Straight cut to the ford (D1, parallax) and the courtyard duel (D2): the battle that follows the decision.
4. Dissolve (1.5 s) to D5 at dawn (pull-back), a fade to black (1 s) under a title card.
The plan passes `plan_check` for the dialogue slice and has no cut without a reason. **Open, reported by the lint:** the lane shares are 36 % video / 53 % still / 11 % helper against 60 / 30 / 10 +-5 (BP-109), because the J5 cards animate only the heroes; the crowd
pictures are stills with camera motion. Options for the creator: accept for a test minute, or animate the D pictures' crowds with Blender cut-out layers (more work and a new check), or shorten the stills.
**Steps to make it (all free, on the PC or CI):** (1) fetch the 11 pictures from HF; (2) per picture a plate or layer split for the parallax shots (depth map, 3 layers) and the Ken Burns paths; (3) the dialogue shots again from 4f with S2 cut to 5 s (BP-108); (4) H1 walking card and H3 card from their sheets;
(5) helper map and title card in Python; (6) FFmpeg cuts, two dissolves and the final fade, voice and ambience on the tracks (J and L cuts); (7) lint, look at the frames, then the creator watches. No paid step.

**First render of the minute (v1, 20:40 UTC, free, in the cloud container, CPU):** 1920x1080 at 24 fps (not yet the 2560x1440 master), 60.0 s, HF `route_test_2026-11/j5_minute/v1/minute_j5_v1.mp4`. Only pictures with lora "style" on Qwen 2.1 (the creator, 20:30 UTC: nothing else).
Built by `blender/j5_minute_render.py` (Python: Ken Burns, three-band parallax with sideways camera, fire flicker, rain streaks, a walking cut-out card, map and title helpers; the dialogue shots are cut from the 4f clip with S2 held to 5 s and the
commander's last second carried over the elder cutaway as a J cut) and `j5_minute_ambience.py` (synthesised rain, fire, battle, wind beds), joined with FFmpeg (two dissolves, fade out at the end). Blender itself was not used in v1: the parallax
here is a 2D band split, not a depth-based 2.5D camera. Not done: depth-map layers, drawn mouths (waiting for the variant sheets), proper music, loudness measurement, the 2560x1440 master.

**v2 of the minute (21:35 UTC; creator 20:55: illogical cuts, nothing animated; 21:09: study the existing render techniques, do not invent).**
*Order now follows time and place:* keep at noon (A2 courtyard wide, D2 duel) -> map "The road to the ford" -> rain march (D4, the drummer as a cut-in of the same picture) -> night camp (A1, dialogue, elder, D6 face) -> ford at sunset (D1) -> dawn after (D5) -> the commander
walks the field (A3). v1 had a dry field in the rain and a noon duel at the sunset ford.
*Animation (free):* `j5_minute_anim.py` moves what the picture shows, with colour and depth masks: a bob that travels down the marching column, waving flags, flowing water and smoke, a watching crowd, sword-clash flashes, fire and torch flames, breathing, drifting fog; embers and rain are screen-space overlays (`j5_minute_post.py`).
*Camera:* `j5_minute_depth.py` (Depth Anything V2 Small) gives a depth map per picture; `j5_minute_depthcam.py` builds a relief mesh in Blender (Workbench, the animated texture changes every frame) and moves a real perspective camera over it. About 1 s per 1080p frame on 4 CPU cores.
*Sound:* synthesised beds per place (`j5_minute_ambience.py`), the bed ducked under the dialogue, the mix normalised to BP-50: -14.0 LUFS, true peak -1.4 dBTP; voice against bed while speaking about 21 LU (13.8 raw, bed ducked by 7 dB; BP-52 asks 15).
*Existing techniques found (2026-11-06, web search, not yet tried unless noted):* DepthFlow (BrokenSource, depth map + ray-marching parallax shader, AGPL-3.0; our Blender relief camera does the same job under our own licence); 3D Ken Burns Effect from a Single Image
(Niklaus et al. 2019, `sniklaus/3d-ken-burns`: depth, point cloud, depth-aware inpainting of what the camera uncovers; the gap-fill we lack); Meta Animated Drawings (`facebookresearch/AnimatedDrawings`, MIT: detects, cuts and rigs a drawn figure and retargets BVH motion onto it:
the free way to make walking and gesturing cards, next to try on the hero sheets); frame-interpolation and image-to-video models (LTX, Wan) remain the paid motion route. Wikipedia: Cutout animation, Limited animation, Multiplane camera, Parallax scrolling (already in BP-181).
*Not good yet, honest:* the elder is a flat card on a blurred plate; the drummer cut-in is soft (a 2.4x crop of a 1280 px picture); the courtyard picture looks more 3D-render than the other xworld pictures (reported); the map is a plain Python drawing; no depth-aware inpainting, so a larger camera move
would show stretched edges; masters are 1080p; drawn mouths still wait for the sheets; the figures in the crowd shots do not walk or fight, only bob and sway.
