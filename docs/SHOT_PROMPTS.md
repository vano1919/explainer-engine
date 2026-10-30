# Shot prompts for animated shots

> **Retired in part by [D-80](DECISIONS_AND_OPEN_QUESTIONS.md) (2026-10-26):** Qwen-Image-2512, Edit-2511 and every `wldnk_*` LoRA are banned; keyframes come from Qwen-Image-2.1 (draws and edits with references) with the new LoRA learned from Rick and Morty. Since N-09 (2026-10-30) the kind table, the model rows and the prompt shape below are on Qwen-Image-2.1 and the xworld_v2 LoRA, the trigger is read from `training/lora_rules.json`; the retired rows stay as marked History, and their Helps and Hurts lists are not yet re-measured on 2.1.

How the prompts of an animated shot are written: the keyframe (Qwen-Image-2.1 + the xworld_v2 LoRA, D-80), the next pose of the same
shot (Qwen-Image-2.1 in its edit mode with the one LoRA, from the master frame), a cut to a new angle of the same scene, and the video
(LTX-2.5 with native audio). ვანო asked for it on 2026-10-24 (15:35 Tbilisi): "analyse the patterns and anti-patterns of the
frame prompts from all the iterations, single out the mistakes you caused, write rules and give them to the scenario agents".

Every rule below comes from a picture or a clip we made and measured (2026-10-22..24). It is a **house** rule when our own
tests show it, a **hypothesis** when one clip suggests it (REVIEW only, never a FAIL). The look itself (one universe, the
trigger word, `universe_thread`) stays in [UNIVERSAL_RULE_BASE](UNIVERSAL_RULE_BASE.md) (UR-22) and the LoRA training rules
in [LORA_TRAINING](LORA_TRAINING.md); this page covers only what a prompt says.

Who uses it: the `story-architect` writes the scenario's shot lines so they can be filmed (one actor, one action, the camera,
the length); the `edit-planner` and the skill `shot-visuals` write the prompts. The check:
`python -m explainer_engine.scripting.shot_prompt_lint <shots.json>` (0 FAIL before any paid render).

## The four prompt kinds

| Kind | Model | Shape |
|---|---|---|
| `keyframe` | Qwen-Image-2.1 + the xworld_v2 LoRA (D-80) | `<trigger>, ` (`lora_rules.trigger()`) + who (by what they look like) + the one action + where + light |
| `nextpose` | Qwen-Image-2.1 in its edit mode with references, the one LoRA, image = the MASTER (N-09; the scene LoRA and Edit-2511 are banned by D-80) | `<trigger>, a later frame of the same continuous animated shot, same camera: ` + one actor's change, the others' small reaction + "Same characters, same camera ..." |
| `cut` | the same edit model, images = master + hero sheet | a new shot size or angle of the SAME place and time, the heroes as on the sheet |
| `video` | LTX-2.5 (image = the keyframe) | one fixed style sentence; the actor and the action with a start, peak and settle; the others' reaction; "everyone stays in frame"; ONE camera sentence; at most three sounds |

A worked video prompt (the video LoRA's validation set, written after the eras test):

```json
{"id": "disco_val", "kind": "video", "seconds": 10,
 "prompt": "Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. A man with a huge afro on roller skates loses his balance, flails both arms and tips backward, then catches himself with one hand on the floor; the three girls on skates gasp and cover their mouths and stay in frame. Static camera. Sounds: funky disco music, a loud thud, gasps.",
 "neg": "text, watermark, extra people, duplicated character, deformed face, extra fingers"}
```

## Rules

| ID | Rule | Evidence (our tests) | Kind | Check |
|---|---|---|---|---|
| KP-01 | **Name every acting person by what the picture shows**, never by a bare role word: "the nurse in the purple jacket", "the old man with round glasses", never "the woman", "a man", "one man", "someone". The model cannot find "the woman" among four people, so it paints a new one | scene LoRA v1 samples 2026-10-24: "the woman points ahead" invented a stranger at steps 0, 250, 500 and 1000; "one man shouts" picked nobody | house | [code] FAIL |
| KP-02 | **One main actor per shot, named first; the others react small and said so** ("the others only turn their heads"). The model hands the action to the figure whose pose is closest to it, whatever the prompt says, so pick a master where the actor's pose is not already someone else's | "the old man throws up his hands": the bearded man raised his hands at all five steps, step 0 included (the base model, not the LoRA) | house | [code] REVIEW over four action clauses; [editorial] the master |
| KP-03 | **Nobody leaves the frame unless the story wants it.** No verb that carries a hero to the edge ("runs after", "heading into", "walks away", "flees") in a video prompt without `exit: true`, and every video prompt says the heroes stay in frame | eras test 2026-10-24, farm: "runs after galloping cows heading into the barn" -> the farmer and both cows left, the shot ended on an empty barn | house | [code] FAIL; missing "in frame" REVIEW |
| KP-04 | **One camera sentence in every video prompt** ("Static camera." or one named move). Without it LTX moves the camera by itself | max-length test 2026-10-24: the camera never stayed still in 10, 15 or 20 s; the eras prompts named no camera | house | [code] FAIL none, REVIEW two or more moves |
| KP-05 | **A moving vehicle: the camera travels with it and the heroes are large**, or they smear | eras wildwest ("on the roof of the moving train"): heroes' sharpness fell to x0.35 in the last 3 s | hypothesis | [code] REVIEW |
| KP-06 | **A shot is at most 10 s** (REVIEW over 8 s); a longer action is two shots | max-length test: 10 s clean, 15 s a duplicated girl and a changed bus, 20 s translucent heroes | house | [code] FAIL / REVIEW |
| KP-07 | **A next-pose prompt has no camera or framing word** (close-up, wide, zoom, pan, angle, from behind, view): it changes only poses; a new framing is a `cut` | zero-shot next pose 2026-10-23: 3 of 7 failures re-framed the shot, caused by framing words ("close-up") in the prompts | house | [code] FAIL |
| KP-08 | **Every next pose is drawn from the master frame**, never from the previous pose (chained edits drift) | the scene-sequence review 2026-10-23: chained edits add up their drift, one master keeps the set | house | [code] FAIL when `source` is not `master` |
| KP-09 | **The negative prompt never names our own style.** Not cartoonish, exaggerated, stylized, flat colours, outlines, drawing, caricature, distorted proportions, motion blur (smears and squash are allowed, VQ criteria). LTX's stock negative contains "cartoonish rendering", "exaggerated expressions", "distorted proportions", "motion blur", "stylized filters": always replace it | every LTX test of 2026-10-23..24 (IC, max length, eras: 13 clips) ran with the stock negative because the test script set none | house | [code] FAIL |
| KP-10 | **The style is carried by the trigger and one fixed style sentence, the same in every shot**; no per-shot style adjectives | style LoRA v2: a long style string in every caption bound the style to the string, not the trigger (stopped at 572 steps) | house | [code] REVIEW when the first sentences differ |
| KP-11 | **At most three sounds in a video prompt, the loudest one named once** | eras test: 3 of 5 clips peaked at 0 dB; the prompts listed four or five sounds | hypothesis | [code] REVIEW |
| KP-12 | **Act big: the action has a start, a peak and a settle, with body parts** ("loses his balance, flails both arms, catches himself with one hand"). Small verbs alone (looks, glances, sways, huddles, smiles) give a frozen shot | eras: disco and school (big verbs) acted, ice age (huddles, sways) held still 85 % of the time; IC layouts with small moves froze the heroes (2026-10-23) | house | [code] REVIEW when no strong verb |
| KP-13 | **The acting heroes are large in the frame** (a medium shot, about a third of the frame's height or more); a wide shot with many small people carries only camera, weather and ambient motion | ice age tribe (small figures) froze; the scene LoRA's crowd master (prompt 3) stayed near-static at 750 and 1000; the IC crowd shot moved only the camera | house | [editorial] |
| KP-14 | **A test prompt tests the model, not the prompt.** Every test prompt passes this lint; a failure is first looked up at step 0 (the base model) before it is blamed on a LoRA | the scene LoRA's prompt 1 failed identically at step 0, so the LoRA did not cause it | house | [editorial]; LT-12 |

## The mistakes and who made them (2026-10-22..24)

| What went wrong | Cause | Made by | Rule |
|---|---|---|---|
| scene LoRA samples: a stranger woman, the wrong man acting | my sample prompts used bare role words ("the woman", "one man") | Claude | KP-01, KP-02 |
| scene LoRA prompt 3 barely moved | I chose a crowd master with small heroes for an acting prompt | Claude | KP-13 |
| farm clip ended on an empty barn | my prompt "runs after galloping cows heading into the barn" | Claude | KP-03 |
| the camera wandered in every clip | my video prompts named no camera | Claude | KP-04 |
| style fought in every LTX test | my test script kept LTX's stock negative ("cartoonish rendering", "exaggerated expressions") | Claude | KP-09 |
| IC shots frozen | my layouts moved arms by a few pixels | Claude | KP-12 |
| ice age clip frozen | many small figures + small verbs in my prompt | Claude | KP-12, KP-13 |
| wildwest heroes smeared | a moving train with small heroes; the camera was not told to follow | Claude | KP-05 |
| the wrong hero raises his hands | the base model gives an action to the figure already posed for it | the model | KP-02 |
| next pose re-framed 3 of 7 shots | "close-up" and framing words in next-pose prompts | the style thread's eval prompts | KP-07 |
| style bound to a string | a long style sentence in every training caption | Claude (style v2) | KP-10 |

## Patterns that worked

- An actor named by two visible traits and a prop, then one big action with a start, peak and settle (disco, school class).
- The others' reaction written as one small verb each, plus "everyone stays in frame" (the video LoRA's validation set).
- "Static camera." as its own sentence; a moving shot names the one move and what it follows.
- Next poses drawn from the master with "same camera" and "nobody new appears and nobody disappears".
- One fixed style sentence first, identical in every shot; sounds after the action, at most three.

## How our three models read a prompt (audit, 2026-10-24)

ვანო asked on 2026-10-24 (15:50 Tbilisi) to check these rules against what our models and our local LoRAs need, so that a
prompt helps the story instead of causing a bad frame, without boring or over-constrained shots. Sources are at the end of
this page; "ours" means our own tests of 2026-10-22..24.

| Model | How it reads | Helps | Hurts |
|---|---|---|---|
| Qwen-Image-2.1 + xworld_v2 LoRA (keyframe, next pose, cut): the Helps and Hurts lists of the two retired rows are kept under History below and are not yet re-measured on 2.1 | natural-language caption grammar with the trigger first | - | - |
| *(History, banned by D-80)* Qwen-Image-2512 + wldnk style LoRA (keyframe) | a 7B vision-language text encoder: long natural sentences, left/right/foreground placement, counts; true CFG 4, so the negative prompt acts; the LoRA learned captions `wldnk style, <what is visible>` | the trigger first, then plain visible content in caption grammar; shot size and angle words ("medium shot at eye level"); each person's screen side and gaze; "only these N people"; the FIRST pose of the action | style adjectives (the trigger carries the style, KP-10); bare role words (ours); the official negative's "oversaturated, over-smooth" against our bright flat colour; quality words (8k, masterpiece) |
| *(History, banned by D-80)* Qwen-Image-Edit-2511 + scene LoRA (next pose, cut) | an instruction on top of the image(s); 2511 keeps identity in group shots better; the scene LoRA learned `nextpose, a later frame of the same continuous animated shot, same camera: <what changed>` | the exact training prefix; only the change; the actor by tag AND screen side (the model sees the picture, the side tells it which figure); the end pose as a visible state; "nobody new appears" | framing words in a next pose (KP-07); chained edits (KP-08); describing the whole scene again |
| LTX-2.5 two-stage (video + native audio) | one present-tense paragraph; image-to-video: the picture already holds the place and the faces; stage 1 runs the dev model with CFG, so the negative acts there; the audio is generated with the picture from the same text | the action in time order (start, then peak, then settle); the face as visible cues; ONE camera sentence relative to the subject and how the frame ends; the spoken line in quotes with speaker, language and voice; a settle before and after the line; concrete sounds with a visible source, the sound sentence last; at most two faces close | re-describing the picture (identity drift); named emotions (neutral faces); labelled fields and shot lists; more than two faces in a close shot (merging); readable text; score music (the edit adds it); story names it cannot know; quality words |

### Audit of KP-01..KP-14

| Verdict | Rule | What changed |
|---|---|---|
| keep, sharpen | KP-01 | a person is named by two visible traits AND a screen side; each hero has ONE tag used word for word in every prompt (KP-15) |
| keep | KP-02 | the screen side answers part of "the model picks the closest pose"; the clause counter now skips the formula sentences (camera, in frame, a quoted line) and counts one actor's start-peak-settle chain once |
| keep | KP-03 | a shot with nobody in it (an establishing or insert shot) no longer asks for "stays in frame" |
| keep, extend | KP-04 | a move names how the frame ends (`camera_end`); LTX completes a move it can see the end of |
| keep | KP-05, KP-06, KP-08, KP-14 | |
| keep, scope | KP-07 | true for next poses only: keyframes and cuts NEED the shot size and angle words |
| keep, scope | KP-09 | the negative acts where CFG runs: Qwen-Image (true CFG 4) and LTX stage 1 (dev); a distilled-only LTX run (CFG 1) ignores it, so never rely on a negative there, write the wanted end state instead. House negatives: `film_shots.NEG_KEYFRAME`, `NEG_VIDEO` |
| keep, fix the sentence | KP-10 | the bake-off style sentence asked for "smooth natural character motion", the floaty motion LT-57 measures (KP-24) |
| keep | KP-11 | also counts a prose sound sentence ("We hear ..."), the form the LTX guides ask for |
| keep | KP-12 | it is anticipation, action and follow-through (Thomas and Johnston); the first frame shows the start (KP-16) |
| keep, now in code | KP-13 | KP-19 |

### Rules KP-15..KP-34, KP-44 and KP-45 (the shot card)

| ID | Rule | Evidence | Kind | Check |
|---|---|---|---|---|
| KP-15 | **One visible identity tag per hero**, at least two traits ("the old man with round glasses and a red scarf"), distinct from every other tag, the same words in every prompt of the episode | KP-01's failures; LTX multi-shot guides: a returning character keeps the same identifying words | house + source | [code] FAIL bare or twin tag, REVIEW short |
| KP-16 | **Start, peak, settle; the video's first frame shows the start.** The composed first frame (assets placed by the layout, docs/ASSET_COMPOSE.md) is at the anticipation, the video moves through the peak, the settle is the end pose (and the guided last frame). A first frame that already shows the peak leaves the clip nothing to do. The actor stands in the blocking. Under D-77 the style-LoRA moment prompt (LT-65) is not that frame: it tells the moment at its peak with a reaction, as the approved pictures did, and the start pose comes from the composition | eras and IC tests: shots that began at their peak froze; LTX image-to-video guides: give the action a clear end state; the LoRA thread 2026-10-24: the peak-and-reaction prompts drew the approved look | house + source | [code] FAIL actor absent, REVIEW peak = settle or no big verb |
| KP-17 | **Emotion as the lens sees it**: eyes, brows, mouth, shoulders, hands; never a bare feeling word | LTX-2 and LTX-2.5 guides: named emotions leave the face neutral | source | [code] REVIEW |
| KP-18 | **The spoken line**: in quotes, one speaker per shot who stands in the frame, said to someone present (or the room), with language and voice; at most BP-100's words for the clip length after a settle at each end; the speaker in a medium or closer shot; a verb of speech without quoted words is a REVIEW (the model invents gibberish) | LTX guides (quotes, words per second, let the face settle); our eras clips | source | [code] FAIL speaker/listener absent, REVIEW length and size |
| KP-19 | **Faces the model keeps apart**: at most BP-101's people in a medium or closer shot; nobody acts in a wide (KP-13) | LTX-2.5 guide: more than two faces merge; the creator's cartoons: 78 % of shots show two people or fewer, groups appear in wides | source + measured | [code] REVIEW |
| KP-20 | **A narrated shot is silent in frame**: the narrator never talks over a sync line, the clip's prompt says "Nobody speaks", and the narration gives what the heroes cannot know instead of describing what the picture shows | the creator's SHOW DON'T TELL (2026-10-20); LTX fills an unspecified track with chatter | house | [code] FAIL both on one shot, REVIEW narration repeating the action |
| KP-21 | **No score music in a clip**: music is the edit's (ED-03, one music at a time); a clip asks only for music with a visible source (`diegetic_music`) | ED-03; the eras clips peaked at 0 dB with music stacked on sounds | house | [code] REVIEW |
| KP-22 | **No story names in prompts**: the models do not know "Walter"; the tag names him. A name said aloud inside a quoted line is fine | the bake-off prompts named "Walter" and "Tom" | house | [code] FAIL |
| KP-23 | **No quality words, no readable text**: 8k, masterpiece, highly detailed do nothing; signs and captions are garbled and belong to the edit | LTX-2.5 guide; Qwen showcase (text works only as an exact quoted layout, which we never need) | source | [code] REVIEW |
| KP-24 | **The style sentence never asks for smooth, fluid or natural motion**: our cartoons hold most frames between quick moves; plain LTX holds 0.10-0.33 against the cartoons' p10 of 0.26 | LT-57 measurements; the bake-off style sentence | hypothesis | [code] REVIEW |
| KP-25 | **A video prompt describes the change only**, one paragraph within BP-102's words: no place description (the picture holds it), no shot lists or labels | LTX image-to-video guides: re-captioning drifts identity | source | [code] REVIEW |
| KP-26 | **Shot grammar of a scene**: a scene with two or more people opens on a shot that shows where everyone is (wide or full), unless the opening close-up is a declared hook; no more than BP-103's shots of one size in a row; each person keeps their screen side (the 180-degree line) unless the shot says `crosses_line`; an exchange gets at least one close shot (MCU, CU or over-the-shoulder) | the creator's cartoons (120 shots, below); the 180- and 30-degree rules | measured + source | [code] REVIEW |
| KP-27 | **Next poses and cuts come from the scene's keyframe master** (KP-08 for cards): `master` names a keyframe shot of the same scene | KP-08 | house | [code] FAIL |
| KP-28 | **Every shot says what it does for the story** (`beat`, one sentence) and its `mode`: scene, narrated, establish or insert. A shot without a beat is not drawn | the creator: the story is the goal, pictures are the means (2026-10-20) | house | [schema] FAIL |
| KP-29 | **Pin what the story needs, free what the model does well.** Pinned: who, where, gaze, the one action's three poses, the face, the line, the camera, the sounds. Free: secondary motion (hair, cloth, breath, blinks), the background's life, the exact timing inside the shot, the acting between the poses, the crowd. Never script a limb-by-limb path or more than one action chain per actor; never write "do not move" or "exactly" for acting | ice age and IC tests (over-constrained layouts froze); LTX guides (overloaded scenes break) | house + source | [editorial] |
| KP-30 | **Prompts are composed, not typed**: the keyframe, next pose, cut and video prompts of a shot come from its card (`film_shots compose`), so the same tag, side, pose and line appear in every model's grammar; a hand-written prompt passes the same lint | the eras and scene tests mixed hand-written variants of one shot | house | [code] `film_shots check` |
| KP-31 | **Everyone stands on something.** On a drawn first frame (keyframe, cut) every person in the blocking has `on`, a phrase that names the surface ("standing on the packed snow", "sitting on the bottom step of the bus door") | the creator 2026-10-24: composition in every picture prompt; floating and merged figures in the style-LoRA masters | house | [code] FAIL |
| KP-32 | **The lead figure has a size**: `height` (a quarter, a third, half, two thirds, most of the frame height) on the actor, or the first person when nobody acts. `height_pct` is kept for the keyframe gate only: the prompt says the nearest word, never a number (test v2 of the 1-minute film, 2026-10-24: numbers were drawn as rulers, arrows and percentages in 6 of 10 pictures and did not size the figure better, height error 0.18 against 0.19). A figure cut by the frame edge has `partial` ("the trunk"): written as "Only the trunk of ... reaches into the frame", counted by the gate, no support or height | the creator 2026-10-24; the keyframe gate measures it | house | [code] FAIL |
| KP-33 | **Relations the picture can draw one way only**: each `frame.relations` sentence says behind, in front of, on top of, under, to the left of...; "by", "near", "beside", "next to" or "with" alone FAIL ("a woolly mammoth by the boulder" drew a mammoth-shaped boulder); a relation names a figure already in the picture with its tag and "the", never "a" or "an" before a cast member's noun ("a living woolly mammoth stands behind the bus" drew two mammoths in 4 of 4 pictures, test v2 2026-10-24) | the LoRA thread's master test 2026-10-24 | house | [code] FAIL |
| KP-34 | **Free space for the action**: a drawn first frame with an action has `frame.lead_room` (left, right, above, below, or none when the action stays in place), so the video does not move a hand or a body out of the frame | the creator 2026-10-24; KP-03 (everyone stays in frame) | house | [code] FAIL |
| KP-44 | **Never name what must be absent.** No picture prompt of a frame (keyframe, next pose, cut, last frame, video) says a word of the world's `absent` or the frame's `frame.absent` (KG-21), not inside another name ("city bus") and not after "no" ("a plain with no road"); spoken lines in quotes are sound and are left out. Say it another way ("yellow bus", "an open snowy plain") | the LoRA thread 2026-10-25: the Qwen-Image-2.1 style LoRA drew a city behind "city bus" at steps 250 and 500, the base model at step 0 none | evidence (one test) | [code] REVIEW |
| KP-45 | **Everyone in the moment, and someone reacts.** A keyframe moment names every figure of its blocking (at least by the tag's head; the gate counts them, KG-01/KG-02), and with two or more figures one of the others has a reaction or a pose. Words are spent in rounds within LT-65's 40: the lead with the action, the light's head, everyone by head, the full light, the others' reactions, the lead's first costume trait, the others' traits, then the lead's body words and full tags. With three or more heroes not every costume fits: identity there comes from the hero sheets and the composition (ASSET_COMPOSE) | the LoRA thread 2026-10-25: S04-01, S08-01 and S13-01 dropped a hero; eight multi-hero moments named the others without a verb or costume; the eras formula wants the second hero's reaction | evidence (one review) | [code] REVIEW |
| KP-46 | **No AI register on the card.** The narration, dialogue, bubble and HUD text of a card passes `register_lint` for words and phrases (RG-01, RG-02; no densities on cards); prompt text is exempt. | the AI register rules RG-01, RG-02 (STORY_ENGINE.md); BP-140 | [code] FAIL / REVIEW |

### Rules KP-35..KP-43 (the episode, under the script engine v1)

They run when the cards say `"engine": "script_engine/1"` ([SCRIPT_ENGINE.md](SCRIPT_ENGINE.md)); the numbers are BP-104..BP-110
in [SOURCED_RULES.md](SOURCED_RULES.md), the evidence is
[research/SCRIPT_ENGINE_V1_2026-10-24.md](research/SCRIPT_ENGINE_V1_2026-10-24.md) and (KP-41..KP-43, BP-111..BP-113)
[research/SCRIPT_ENGINE_V2_2026-10-24.md](research/SCRIPT_ENGINE_V2_2026-10-24.md).

| ID | Rule | Why | Kind | Check |
|---|---|---|---|---|
| KP-35 | **Shot rhythm**: shots a minute and the median shot inside BP-107's band (episodes of a minute or more) | the creator's three reference cartoons, 3517 shots | hypothesis | [code] REVIEW |
| KP-36 | **Clip length**: one clip at most BP-108's maximum; a longer shot that changes pose draws its last frame (`last_frame`) so a key pose lands every few seconds | night tests 2026-10-24: duplicates at 15 s, translucent heroes at 20 s | hypothesis | [code] REVIEW |
| KP-37 | **Animation tiers**: every shot is `hold` (the keyframe with a camera move by our code), `light` (breath, glance, a turn of the head, on the fast model) or `full` (acting); holds at most BP-109's share; a spoken line on a hold or light shot FAILs (lips need the full model); an acted peak on a hold is REVIEW | the critic's 40 % still read as a slideshow; the cartoons hold a still on 5-10 % | hypothesis (the line rule: invariant) | [code] FAIL / REVIEW |
| KP-38 | **Camera moves** on at most BP-110's share of shots; the rest say `static` | the cartoons: static camera on 81 % | hypothesis | [code] REVIEW |
| KP-39 | **Narration blocks on the cards**: shots narrated with no line spoken between them last at most BP-104's block; the narrator's words fit the pictures under them (BP-01's top pace) and keep BP-105's share | template D (ST-17, ST-19) measured on the cards instead of the script | hypothesis | [code] REVIEW |
| KP-40 | **The outro points to the channel**: a subscribe line in the last six shots names a world already on the channel and a world coming (the `channel` block) and why (not to miss them); a BP-43 sign-off FAILs | the creator 2026-10-24 (BP-106) | house | [code] FAIL |
| KP-41 | **The cold open shows the fight to come**: in the first BP-111 seconds at least BP-111's count of shots are `teaser_of` a later action shot; a teaser is a piece of that shot's own clip (`compose` writes `kind: reuse`, nothing is drawn or rendered); a teaser that points at no later shot, or is longer than it, FAILs | the creator's forwarded review 2026-10-24: the first real clash came at 3:13; the cold open (an attention-grabbing scene from the middle, repeated when the story gets there) | hypothesis (the pointer rule: invariant) | [code] REVIEW / FAIL |
| KP-42 | **Strategy shown in action**: at most BP-112's seconds in one place before a cutaway to another place shows what the talk is about while it is said: the plan carried out, its cost, the other side moving (cross-cutting); action, reaction, consequence, not more battle | the review: 5:03-8:19 was talk about plans; cross-cutting builds suspense and simultaneity | hypothesis | [code] REVIEW |
| KP-43 | **AI acting is a risk**: at most BP-113's count of spoken lines in a row before a silent reaction, an insert or a cutaway; every full-tier line in a medium or closer shot carries an acting check (`qa: [acting]`: lips on the line, the peak, the face, no freeze) and a fallback that hides the mouth (over the speaker's shoulder onto the listener, or the speaker's hands); a take is redrawn only when the check fails, the fallback after a second failure | the creator 2026-10-24: 'the AI's acting is the critical vulnerability; if it fails the parley becomes a podcast' | house | [code] REVIEW; compose |
| (LT-65) | **Style-LoRA prompts in the moment shape**: a keyframe moment or hero sheet is `<trigger>, <a short story of the moment>` (place, the lead with caricature body words and the action at its peak, someone's reaction, a light source) in at most 40 words, with no caption tail and no camera, size or position words; each tag once (LY-09); sizes, sides, heights, supports and counts are the gate card's and the composition's (ASSET_COMPOSE). `film_shots check` runs `qa/style_prompt.check` on every such prompt | the LoRA thread 2026-10-24 (PR #22 c032f76): the 20-33-word eras prompts drew the approved look, the composed layout prompts a flat grey cartoon | evidence (one test) | [code] FAIL / REVIEW |

## The shot card (`film_shots/1`)

Schema: [`explainer_engine/schemas/film_shots.schema.json`](../explainer_engine/schemas/film_shots.schema.json); worked
example: [`examples/film_shots/bus_in_the_ice_age.json`](../examples/film_shots/bus_in_the_ice_age.json) (the scene LoRA's
bus test, rewritten as six cards: establish, master, cut, over-the-shoulder, insert, next pose; 0 FAIL, 0 REVIEW).
Every composed prompt names its LoRA (`lora`: `style`, the one xworld_v2 LoRA on Qwen-Image-2.1; the old `scene` LoRA on Edit-2511 is banned by D-80), and `compose` also writes
one `gate` card per drawn first frame (keyframe, cut: the people by tag, side, height and support with the lead marked
`actor`, the relations, the free space) for the keyframe gate of PR #22.

| Field | Says | Written by |
|---|---|---|
| `cast.<id>.tag`, `voice` | the visible identity tag (KP-15); how the voice sounds | story-architect (from the hero sheet), voice-caster |
| `places` | each place once, as visible words | story-architect |
| `beat`, `mode`, `scene` | what the shot does for the story; scene, narrated, establish or insert | story-architect |
| `frame` (`size`, `angle`, `camera`, `camera_end`, `over`, `place`, `light`, `crosses_line`) | the frame | edit-planner |
| `blocking[]` (`who`, `where`, `facing`, `pose`, `on`, `height`, `height_pct`, `partial`) | who stands where, looking where, on what, how big, in the first frame | edit-planner |
| `frame.relations[]`, `frame.lead_room` (`side`, `for`) | how things in the picture stand to each other; the free space the action moves into | edit-planner |
| `action` (`who`, `start`, `peak`, `settle`, `face`) | the one action, present-tense verb phrases; the face as cues | scene-writer, performance-director |
| `reactions[]` | the others' one small verb each | scene-writer |
| `dialogue` (`who`, `to`, `text`, `delivery`, `language`) | the line (from the script's line), how it is said | scene-writer, performance-director |
| `narration` | the narrator's words over a narrated shot | scene-writer |
| `sound` (`ambience`, `foley[]`, `loudest`, `diegetic_music`) | at most three sounds with a visible source | edit-planner |
| `source`, `master`, `last_frame`, `exit` | how the first frame is drawn; whether the settle pose guides the last frame | edit-planner |

```
python -m explainer_engine.scripting.film_shots check <film_shots.json>                   # 0 FAIL before any paid call
python -m explainer_engine.scripting.film_shots compose <film_shots.json> --out prompts.json  # keyframe / nextpose / cut / video prompts
python -m explainer_engine.scripting.shot_prompt_lint prompts.json                        # the same lint on any prompt file
```

## Shot grammar of the creator's cartoons (measured 2026-10-24)

120 shots (Rick and Morty, Solar Opposites, Inside Job; 4 runs of 10 consecutive shots each) labelled by hand, plus the
camera measure of all 3312 unique shots. Details and labels:
[research/SHOT_GRAMMAR_FOOTAGE_2026-10-24.md](research/SHOT_GRAMMAR_FOOTAGE_2026-10-24.md).

- Shot sizes: medium 30 %, wide 20 %, medium close-up 18 %, full 17 %, insert 8 %, establishing 4 %, close-up 3 %.
- People: 1 in 38 % of shots, 2 in 40 %, none in 8 %, 3 or more in 15 % (almost all of those are wides).
- Camera: static in 81 % of all shots; a move is an event (a reveal, a chase).
- Dialogue: wide to show who is where, then singles and two-shots, over-the-shoulder reverses (16 % of shots), eye level.
- Inserts (a phone, a prop, a hand) are 8 %: cheap shots with no face to keep, good for a beat of information.

## Waiting

The narrator-and-scene structure (a teaser, the narrator's set-up, scenes with dialogue, the narrator tying the meaning)
waits for the documentaries the creator will send (2026-10-24, 16:05 Tbilisi): their shots and the narrator's share will be
measured the same way before any rule is written.

## Sources (audit 2026-10-24)

- Lightricks, [Prompting guide for LTX-2](https://docs.ltx.video/api-documentation/prompting-guide) (official; six elements, one paragraph, quotes for dialogue)
- deAPI, [LTX-2.5 prompting guide: multi-shot, native audio](https://deapi.ai/blog/ltx-2-5-prompting-guide-multi-shot-scenes-native-audio-and-prompts-that-actually-cut)
- fal.ai, [How to use LTX-2.5](https://fal.ai/learn/tools/how-to-use-ltx-2-5)
- Qwen (retired models, kept as sources of the History rows), [Qwen-Image-2512 model card](https://huggingface.co/Qwen/Qwen-Image-2512) and [Qwen-Image-Edit-2511 model card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) (true CFG 4, placement by description)
- F. Thomas and O. Johnston, *The Illusion of Life: Disney Animation* (1981): anticipation, staging, follow-through
- [180-degree rule](https://en.wikipedia.org/wiki/180-degree_rule), [30-degree rule](https://en.wikipedia.org/wiki/30-degree_rule)
