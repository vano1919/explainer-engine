# One place, one picture: scene reuse, references, identity, dialogue, cut assembly (LV- / RF- / HI- / DL- / AS-)

> Route-scoped since D-116 (2026-11-06: J2 and J5 use Qwen and LTX), amended by D-120 (2026-11-07).


## 2D Anchor & Multi-Angle Keyframe Reuse (`reuse_location_anchor`, D-123)
> **Route-scoped since D-116 (2026-11-06); updated 2026-11-09 by D-123:** In the 4-stage Hybrid B -> C pipeline ([MAIN_METHOD](MAIN_METHOD.md) Stage 7), environment and character continuity is maintained in 2D image space by passing approved `loc_<id>_anchor.png` and `char_<id>_turnaround.png` sheets into local ComfyUI Qwen workflows (`workflows/comfyui/qwen_keyframe_multiangle.json` with `reuse_location_anchor: true` and `start_frame_source: "multiangle_from_anchor"`). The `LV-`, `RF-`, `HI-`, `DL-`, and `AS-` rules below remain the code-checked continuity baseline.

The creator's decision, 2026-11-07 18:08 UTC (cmsg_01Hnu5zB86sjUj5GtTgaUkPWWGFzRWxBehT3gJoao5ggGZ), recorded as
[D-120](DECISIONS_AND_OPEN_QUESTIONS.md). His words, translated: "One scene only when it renders with a blurred background, or when
those scenes do not follow each other and the viewer will not notice. Rewrite the script and visual rules for this approach; so we
no longer need the Blender frame as a reference. A more detailed prompt and control of the hero's description replace the
reference photo. I do not ban reference photos: they may be the way to keep the heroes' and the places' style. I ban rendered
photos as references. Research which scene's photo can serve as the reference of which scene." Two risks he named: heroes must not
change from shot to shot; the dialogue render rules must get richer (mouth, imitation of body movement, proportions kept when a
figure is cut out).

First version: the PC session, 2026-11-07 (commit 9dccfcb on `systemic/next-video`, prefixes SR/RF/ID/DL). This file is the merged
version: SR- was already taken by ORCHESTRATION's time-jump rules and ID- is too generic for the lint, so the families are LV- (location
view), RF- (references), HI- (hero identity) and DL- (dialogue). Research: [E0 audit](research/stoneage_pilot_2026-11-07/E0_AUDIT_2026-11-07.md),
[scene-reuse research](research/stoneage_pilot_2026-11-07/SCENE_REUSE_RESEARCH_2026-11-07.md).

## What the tests measured (2026-11-07, HF `route_test_2026-11/sa_test/`, Qwen-Image-2.1 + xworld_v2 LoRA)

- Qwen edit keeps the composition of Image 1 almost exactly and **does not turn the camera** of a painted place (asset test B: the
  "left/right/back" views were copies of the front; run 2: only the ice field followed a new angle).
- A shaded Blender render as Image 1 pulls the picture toward 3D and weakens the style (cave CC0: edge density 7.55 % -> 4.22 %);
  the LoRA itself is healthy (E0 audit: no zero adapters).
- A **fixed, verbatim appearance text** kept Marcus, Ura, the hunters and the mammoths recognisable across 9 independent pictures
  (v5/v6). It did **not** fix faces: the hunters grew or lost beards between run 5 and run 7, so faces need their own words (HI-05).
- Verbal positions plus a layout image restored the staging (v6, run 7: sitting on the log, gesturing, holding torches). **A whole
  scene drawn from words alone, with no layout image, has not been tested yet**: run 3 (empty place + character sheets as images)
  lost the characters in the cave and the camp. The first 10 pictures of this route test exactly that.
- The painted master as a second image (E4b) came back over-saturated and noisy.

## 1. Location views (LV-)

| ID | Rule | Severity |
|---|---|---|
| LV-01 | **A place is drawn more than once only (a) with its background blurred** (a dialogue or reaction close-up where the place reads as colour and light, not as walls and objects; DL-02), **or (b) when the two drawings never sit in consecutive shots**: at least one shot of another place, an insert or a blurred close-up stands between them, so the viewer cannot compare them. Two different drawings of the same place in consecutive shots fail. | FAIL |
| LV-02 | Consecutive sharp shots of one place are **the same picture**: a crop, push-in or pan of it (AC-12, AC-13, ED-02), a light or weather change of it in post (LV-05), or an LTX clip that starts from it. Pixels that are the same never contradict each other. | FAIL |
| LV-03 | A part of a location with its own landmarks is its own place (the cave's fire hall and its handprint wall; the camp's fire ring and its bone gate). A beat that needs a new look moves to such a place instead of a second drawing of the same view. | REVIEW |
| LV-04 | An **insert** shows a thing, not a place: a hand, the phone, a bone, a mask, a painted palm, on a blurred or neutral ground with at most two landmark details. An insert is not a view of a place for LV-01. | REVIEW |
| LV-05 | Change inside one picture is carried by **light, weather, smoke and the actors** (the fire flares or dies, the white flash, snow thickens) as a post layer or an LTX motion, never by a new drawing. | REVIEW |
| LV-06 | An LTX clip's first frame obeys LV-01 like any shot: it is a place's picture (or a blurred close-up), and a clip never shows a second drawing of the place it cut from. | FAIL |
| LV-07 | **Place register.** Every visual script ends with a table: place -> each drawing of it (id), the shots that use each drawing sharp, the blurred shots, the inserts, and for every second drawing the shots that separate it from the first. A script that breaks LV-01 fails before any paid step. | FAIL |
| LV-08 | (proposal, the creator to decide) Two drawings of one place inside the **same scene** need at least two shots between them, not one. | REVIEW |

## 2. References (RF-)

| ID | Rule | Severity |
|---|---|---|
| RF-01 | **No rendered (Blender / 3D) picture is a reference** for a Qwen picture. Staging comes from the scene words (HI-04). Blender stays for J4's depth/line control and the J5 2.5D assembly of finished pictures, never as an input image of Qwen. | FAIL |
| RF-02 | References are **our own pictures in the house style**, approved by the creator (AC-02): a hero's first approved close-up or sheet, a place's picture, a prop picture. A photo, a render or an older look is never a reference. | FAIL |
| RF-03 | **Which picture serves which shot** (the reference map; measured rows are marked): (1) a place's picture is Image 1 **only** for a change of itself that keeps the composition (the wall with a second handprint, the fire lit or dead): Qwen edit keeps composition (test B, measured); (2) a place's picture is the **blurred background** of that place's dialogue close-ups by a free crop, never a Qwen input (no cost, no drift); (3) a hero's approved close-up is Image 1 for **that same drawing's** mouth, blink and expression variants (untested; picture 10 of the first batch tests it); (4) a hero's close-up or sheet as Image 2 for a new pose is **not used** until a test shows it helps (run 3: sheets in a full scene were lost); (5) a place's picture as Image 2 for a new view is **not used** (E4b over-saturated). | REVIEW until each row is measured |
| RF-04 | At most 3 images per picture (CT-05). Order: the drawing being changed first, then people in the order the prompt names them. | FAIL |
| RF-05 | A generated **scene** picture is never the base of the next scene picture (CT-09). RF-03 (1) and (3) are edits of one approved drawing into its own variants, one step deep, never chained. Code: a job that uses a generated picture (`out:X`) says `variant_of: X` (D-121). | FAIL |

## 3. Hero identity (HI-)

| ID | Rule | Severity |
|---|---|---|
| HI-01 | **Cast registry, verbatim.** Every person, animal and recurring prop has one appearance text: age, height in metres, build, the face (HI-05), hair, skin, each garment with its colour, shoes, the one mark (HI-03). Every prompt copies it word for word, never rewritten per shot (CT-02). It lives in the episode's visual script, one block per entity. Every jobs entry carries its `in_shot` list (D-121); the code checks that each listed entity's block is in the prompt word for word, that no other entity is described, and fails a job without the list. | FAIL |
| HI-02 | Registry text names colours with plain words and sizes in metres, so two pictures can be compared (Marcus 1.75 m, Ura 1.80 m, hunters 1.70 m, child 1.10 m, mammoths 3.5 / 3 / 2 m). | REVIEW |
| HI-03 | Distinct silhouettes: no two cast members share hair, garment colour and headgear; every hero has one unmistakable mark (Ura's antlered half-mask, Marcus's grey hoodie and white sneakers, the grey / brown / spotted furs). | REVIEW |
| HI-04 | **The prompt has three parts in a fixed order:** the style line (the LoRA trigger first, then one sentence that describes THIS scene's style in plain words, e.g. "Style: an exciting adventure style, varied colourful environments, rich detailed backgrounds."; it is written per scene and must fit the channel's one drawn world; creator 2026-11-07 19:33, after the 3-photo comparison where the new sentence looked better), the **scene** (shot size and camera height in plain words, who stands where left to right and near to far, who sits, kneels, turns away, what each hand holds, the landmarks, the light and its direction), then the **appearance** blocks of HI-01 for exactly the people in the shot. Nobody who is not in the shot is described; a person seen only in part (feet, a hand, the mask) gets only the registry words for that part, verbatim. | FAIL |
| HI-05 | **Faces are written.** Every hero's text names face shape, nose, brows and beard (or clean-shaven); every extra gets two face words. A hero whose face, hair or beard changes on the contact sheet is redrawn with a new seed, never accepted. | REVIEW |
| HI-06 | **Identity check per batch:** every picture with a hero goes on one contact sheet next to that hero's approved reference; the creator sees it before any picture is used; `qa/identity.py` scores are written as INFO until calibrated on these sheets (BP-133). | REVIEW |
| HI-07 | One LoRA weight per episode, recorded: **1.0** (the creator, 2026-11-07 19:25 UTC, replacing D-116's 0.7; every first-minute picture v8-v13 was drawn at 1.0; 1.2 drew no extra style and worse staging, run 6). | REVIEW |
| HI-08 | **A route prompt holds at most 280 words** (the creator, 2026-11-07 22:23 UTC, answer 4a, D-121): the scene part needs positions and the appearance part is fixed, and the face words of HI-05 add about 15 words per hero (v6's best pictures were 139-215 words; the first batch's cave picture, 273 words with five people, tested the top). LT-65's 150-word ceiling and its no-camera, no-position REVIEW stay for the LoRA "moment" prompts. Code: `scene_reuse.check_prompts`. | FAIL above 280 words |

## 4. Dialogue shots (DL-) — extends ED-14, KP-43, AC-15, BP-113

| ID | Rule | Severity |
|---|---|---|
| DL-01 | **Dialogue coverage:** start with an LTX-generated establishing two-shot in the pilot, normally about 5-9 seconds as a test target; show both speakers and enough of the place to establish their positions and eye-lines. Then choose LTX close-ups, reactions, or an optional J5 close-up according to the scene. Do not force a fixed sequence. Use an approved MCU character drawing only when J5 is selected; avoid generating it when the LTX footage is sufficient. | FAIL |
| DL-02 | **J5 close-up background:** derive the blurred background from the same approved place image/panorama used by the establishing shot; do not generate another environment view. The J5 renderer blurs that source locally for close-up camera setups and records the source hash. The blur amount remains a visual review item; it must hide readable landmarks while retaining continuity. | FAIL |
| DL-03 | **Proportions on every cut-out:** scaled uniformly by the registry height and the shot size, never squashed or stretched; the head is the same size in every shot of the same size in a scene (2 % tolerance); the frame cuts at the chest or waist, never at a joint; no edge halo (matte feather 1-2 px, edge colour decontaminated); no piece of the drawn background stays on the figure (AC-15). | FAIL |
| DL-04 | **Mouth:** at least four states: rest with the lips closed (also used for M/B/P), half-open, wide and round (O/U), all from the same drawing (RF-03 (3)), switched on the read's word and phoneme timings (`audio/words_to_mouth_cues.py`, Scribe timings); the lips close on m/b/p; the mouth never moves on silence or on another speaker's line; the mouth patch keeps the face's position to the pixel (registered by the face box). A take whose lip-sync check fails twice uses a mouth-hidden fallback (KP-43). Code (D-121): `cut_plan.check_dialogue` fails a speaking cut-out without the four `mouth` states and a `mouth_cues` file; `blender/bpy/cut_render.py` switches them by `cut_plan.mouth_track`. **A talking figure without a moving mouth is never rendered.** | FAIL |
| DL-05 | **The body never freezes:** a breathing cycle of 3-5 s (1-2 % scale on the chest, anchored at the frame's bottom edge), a blink every 2-6 s placed in pauses, never in a stressed word, a head tilt or nod of 1-3 degrees on stressed words, at most one gesture variant per line, and a slow push of the camera that is at rest at the cut (ED-08). | REVIEW |
| DL-06 | **Eyelines:** the speaker looks off-frame toward the listener's side, and the two speakers of one exchange face opposite sides of the frame (180-degree rule, CT-06, CT-11). A mirrored drawing is allowed only for a three-quarter view (AC-03). | FAIL |
| DL-07 | **Listener reactions** on every 2nd-4th line and always on news, an insult or a reveal (ED-14); at most BP-113's run of spoken lines before a silent reaction, an insert or a cutaway. | REVIEW |
| DL-08 | **Two-shots** are a place picture (LV-02) or an over-the-shoulder: the near hero's back or shoulder from their own approved drawing, blurred, in the frame's foreground edge; never a new sharp drawing of the place. | FAIL |
| DL-09 | **Overlaps and interruptions** ([OVERLAP], [CUT] in the script) cut to the new speaker on the overlap's first frame, the first speaker's mouth stops at the cut; a [DELAY] holds on the listener, not on a frozen speaker. | REVIEW |
| DL-10 | **Benchmark before expanding J5:** compare a short LTX-only dialogue with LTX opening footage plus optional J5 close-ups, using the same scene, approved characters, actual dialogue audio, and place image. Record quality, generation and production effort, render time, and costs; do not assume Blender is cheaper because its renderer is free. | FAIL |

## 4b. Cut assembly (AS-) — the creator, 2026-11-07 22:23 UTC (D-121)

The Gemini review of the stone-age minute-1 test (v1, c1, c2, c3b; package `route_test_2026-11/gemini_review/`) and the creator's answers 1a-8a
(msg `cmsg_01Hnu5zB86sjUj5GtTgaUkPWH3yBwffdTpnyWVr339uFoN`): "the point of generating this video and of the review is to optimise the code; update the code with the advice and make
sure a test checks every rule." Rules of 21:01-21:03 (a lone talking hero and a conversation's start are LTX, then close-ups; actions are
LTX, never a blurred-background still; collage only for general narration; ambience per place; hard cuts; no mouth-less talking stills)
now have code. Every rule is checked by `production/cut_plan.py` (`CHECKS` names the function) before anything is rendered, and
`tests/unit/test_cut_plan.py` proves each one fails on a bad plan.

| ID | Rule | Severity |
|---|---|---|
| AS-01 | **An action is an LTX clip.** A line marked `action` (fire fails, a foot in the snow, the drum, spears at a throat) is carried by a V shot, never a still or a cut-out on a blurred plate. | FAIL |
| AS-02 | **No talking still.** A hero's line is carried by an LTX clip or by a cut-out with a moving mouth (DL-04); never by a graphic (H). | FAIL |
| AS-03 | **A conversation normally opens on an LTX two-shot** (a scene with two or more speakers: type V, `two_shot`), then uses coverage suited to the dialogue (ED-14, DL-08). The pilot's 5-9 s opening is a test target, not a universal duration or a fixed shot sequence. | FAIL |
| AS-04 | **Collage only for narration.** A collage still (C) carries narrator lines or none; a hero's line on a collage fails. | FAIL |
| AS-05 | **Ambience per place.** Every place on screen has its looping ambience bed in the plan; the assembly mixes it over that place's shots (about 18 dB under the voice, short fades). v1 had none. | FAIL |
| AS-06 | **Whoever speaks is shown.** A shot that carries a hero's line shows that hero (`shows`, or the cut-out's `who`). v1 put Ura's line at 00:46-00:50 on Marcus's face. | FAIL |
| AS-07 | **Cuts sit in pauses**, or within 100 ms of a line's start; a cut inside a line is marked `l_cut` on purpose. | REVIEW |
| AS-08 | **What the line names is on screen.** A line's `must_show` items ("spears", "hunters") are in the shot's `shows`. v1's "Spears. Right at his throat." showed no spear. | FAIL |
| AS-09 | **Subtitles carry words, not names** (no "MARCUS:" prefix): the face says who speaks. | FAIL |
| AS-10 | **An LTX clip keeps its own sound** (its native audio, under the voice) unless `mute_reason` is written. v1 dropped it (`-an`). | FAIL |
| AS-11 | **Clips are never squeezed:** cover the frame and crop centred (`cut_plan.fit_filter`); v1 scaled 1920x1088 to 1280x704 (3.5 % squash). | FAIL |
| AS-12 | **Graphics are drawn in the house style** by `production/cards.py` (paper, hand ink line, ComicNeue, palette tokens); a flat UI mock-up fails. | FAIL |
| AS-13 | **A place's state changes only on an event shot** (the fire burning -> embers -> out): a state that changes between shots with no `event` naming it is flagged. | REVIEW |
| AS-14 | **No paid LTX run on a prompt FAIL:** every Modal launcher runs `production/paid_preflight.py` before `.remote()` (KP-04, KP-11, KP-22, KP-55, KP-59..KP-62 for LTX; RF-/HI- for Qwen). The c3 prompt broke KP-04, KP-22, KP-55 and KP-59 and was paid anyway. | FAIL |

## 4c. LTX clips in the edit (LX-) — merged from `systemic/next-video` 217737d (2026-11-12, v4.3 P0.3); retired-era tool (LTX), the edit lessons stand; the creator 2026-11-07 19:17 UTC; extends KP-16, KP-36, BP-108, BP-164

| ID | Rule | Severity |
|---|---|---|
| LX-01 | **Handles:** every clip is generated about 0.5 s longer at the head and 0.5 s at the tail than its slot (frames rounded up to 8k+1), so the edit can choose its in and out points. | REVIEW |
| LX-02 | **The first frames are not used:** the head handle (the model's warm-up, where the picture can morph away from the first frame) is trimmed; the shot starts at the first frame after the warm-up that still matches the keyframe (BP-164 frame0 check on the kept first frame). | FAIL when the kept head morphs |
| LX-03 | **The last second lands in the cut:** the clip's settle (KP-16) sits on the out point; the cut is on the settle or on a motivated action beat, never mid-morph; a frozen tail (BP-164) is trimmed, not shown. | REVIEW |
| LX-04 | **Speed:** a clip may be retimed in the edit between 0.85x and 1.15x (frame blending / optical flow, pitch-free since clip audio is not used for speech) to fit its slot; outside that band it is regenerated with a length that fits. Never retime a shot with visible lip-sync. | REVIEW |
| LX-05 | **Joins:** a clip that follows or precedes a still of the same picture starts or ends on that picture's framing (ED-02), and the camera is at rest at the cut (ED-08). | REVIEW |

## 5. Conflicts with existing rules and how they are resolved (D-120)

| Existing rule | Conflict | Resolution |
|---|---|---|
| D-116 J2 "Blender clay layout -> Qwen first frame -> LTX" | RF-01 forbids a render as Qwen's input | **Amended:** J2's first frame is a Qwen picture from the scene words (t2i) or an RF-03 edit; Blender stays in J4 (LTX depth/canny) and J5 (2.5D assembly) |
| D-101 / invariant 6 "identity carrier: Qwen hero sheet and Blender card or rig" | no Blender card or rig on this route | **Amended:** the carrier is the HI-01 registry text plus the hero's approved reference picture; the principle (never redraw a hero from scratch) stays |
| KP-56 (flat silhouettes in a Blender still for Qwen), KP-57 (Image 1 = Blender of the new angle, Image 2 = master), KP-54 (Blender gate before Qwen) | no Blender still goes to Qwen | **Superseded** (rows kept as history) |
| KP-58 (fallback: one environment = one LTX view; dialogues as Blender close-ups) | the new rule allows a second drawing when not consecutive; close-ups are Qwen drawings, not Blender | **Superseded** by LV-01, LV-06, DL-01 |
| LT-65 (at most 150 words, camera and positions go to the layout) | there is no layout image; the scene words carry positions | **Scoped:** LT-65 keeps the LoRA "moment" prompts; the route's three-part prompt follows HI-04 and HI-08 (ceiling pending) |
| PRODUCTION_RULES standing order 14 ("every Blender still or Qwen frame is the first frame of a planned LTX shot", `in_shot` list) | "Blender still" no longer applies | **Amended:** "every Qwen frame"; the `in_shot` list stays and the scene part of the prompt is written from it |
| CT-03 "Image 1 of every shot except the master is the scene's master frame" | a new sharp view from the master is impossible (test B) and a second drawing is LV-01 | **Amended:** the master is Image 1 only for a change of itself (RF-03 (1)); crops of it are made in code |
| CT-07 "consecutive shots of the same people change size by a step or angle by >= 30 degrees" | a 30-degree change of angle on a sharp place is a second drawing | **Amended:** inside one place the change is a size step on the same picture or a cut to a blurred close-up or insert |
| ED-14 "a scene opens on an establishing or two-shot" | a two-shot must not be a new drawing | **Amended:** establishing = the place's picture; two-shot = DL-08 |
| The creator's 10:57 rule "Blender assembles all scenes first, then Qwen makes the photos" (project rule 15) | Blender is no longer Qwen's input | **Replaced** by his 18:08 word (D-120) |
| AC-12, AC-13, CT-05, CT-06, CT-09, CT-11, D-27/D-28 cut-outs, BP-84, BP-108, BP-172 | none | kept |

## 6. Open (the creator's)

1. LV-08: one shot or two between two drawings of a place in the same scene.
2. (decided 2026-11-07 22:23 UTC, D-121) HI-08: 280 words, FAIL.
3. RF-03 (3)-(4): measured by the first batch (pictures 4, 7, 8, 10 of the plan).

## 7. Who starts paid runs (creator, 2026-11-07 19:32 UTC)

The PC Remote Control session never starts a paid run (no `modal run`, no ElevenLabs or other paid call, no pod): it does the free
Blender assembly and runs only sha-checked handoffs. Every paid run is started by the cloud thread, with a price, a cap, the
creator's yes and one Modal app at a time (the app id goes to the watchdog). Why: the PC session started duplicate A100 apps four
times on 2026-11-07, doubling the spend and breaking the one-app rule.

**Links of finished material (creator, 2026-11-07 20:16):** every finished item (picture, voice, clip, sheet, video) is reported to the
creator with its exact Hugging Face link (`https://huggingface.co/datasets/vano1919/tmr-artifacts/blob/main/<path>`), always, in the same message; only NEW items, never links already sent (creator 20:18).

