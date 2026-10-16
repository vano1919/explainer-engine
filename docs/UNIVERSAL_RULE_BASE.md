# Universal Rule Base

The channel-wide rules every Crossworld Theories video follows: history, science, fantasy crossovers alike. The creator
set them on 2026-10-16 (D-37). Rules marked **[code]** are checked by `explainer_engine/edit/shot_rules.py`
(`python -m explainer_engine.edit.shot_rules <shots.json> <words.json> <look.json>`; UR-16..UR-21 in `edit/stakes.json`); **[editorial]** rules are
checked by the editor and the creator. A FAIL blocks the edit; a REVIEW goes to the creator.

The look stays the painted style of D-27 (the creator rejected the hyper-realistic modifier on 2026-10-16). Pictures come
from the local pod (D-36); Gemini only for reusable assets (D-19, D-28). Narration is Kokoro (AUDIO_SYSTEM.md), which
also gives the word timings the cuts depend on.

## Primary rule: one universe (UR-22; overrides every other instruction, creator 2026-10-16)

Every visual, character, background and generated image exists inside the **same drawn universe**. Where any other rule, prompt
or tool instruction conflicts with this one, this one wins. It applies to every image prompt from now on (pod pictures, Gemini
cast sprites, props, thumbnails).

1. **Absolute cohesion.** Characters, props, buildings, rocks, plants and sky match down to the smallest detail: they look drawn
   by the same artist for the same scene. A realistic person next to a caricature hero, realistic hands, or a photographic
   background is a defect, never a style variation.
2. **Shape and tone synchronisation.** The environment and its inhabitants share one design language: if the hills and rocks
   are rounded and quirky, the characters have quirky, exaggerated shapes too; the same colour palette, shading, line work and
   texture everywhere (the episode's `universe_thread` in `look.json`).
3. **Time-travel continuity.** When a character travels to another era, place or dimension, the era changes the props, clothes,
   architecture and palette within UR-08, but the specific style (texture, line work, rendering rules) stays one continuous,
   unbroken thread. No phase, scene or shot may define its own style.
4. **Placement.** This is the primary rule for all asset and character creation; the thread text is appended to every image
   prompt, and the generators refuse a prompt without it.

| ID | Rule | Check |
|---|---|---|
| UR-22 | **One universe** (the thread is `world/look_v2.json` "thread" from D-41; the older storybook thread of look v1 is superseded).  Every pod prompt carries the look's `universe_thread` (exaggerated shapes everywhere, thick warm-brown ink outline, flat watercolour fill, simple cel shading, one limited warm palette); any person, crowd or hand painted by the pod also carries `figure_style`; plates carry no people (UR-20); no phase overrides the style; realistic, photographic and "natural proportions" words are banned (UR-07); cast sprites are made with `edit/universe.sprite_prompt` and graded to their plate. Before a batch is accepted, a style-bridge sheet (a sprite and a pod-painted person and hand in one frame) is approved once per episode (`look.style_bridge`). | [code] thread in every prompt, `figure_style` for bodies, no per-phase style, REVIEW without `style_bridge`; [editorial] the sheet |

## A. Narrative

| ID | Rule | Check |
|---|---|---|
| UR-01 | **Hook, 0–5 s.** The first shot is a C (extreme close-up) or a moving A. The first sentence asks the episode's concrete question and the question is asked by 5 s; no greeting, no channel name. A sound event in the first second. | [code] shot 1 type and motion, a "?" word ending by 5 s, greeting words, first word or `sound_at` ≤ 1 s |
| UR-02 | **First 30 s are fast.** At least 6 shots start in the first 30 s, and each of them stays within its type's minimum + 1 s (A ≤ 6, B ≤ 4.5, C ≤ 3.5). | [code] |
| UR-03 | **Logical arc.** Beats run in story order; each beat names its time and place. Every shot belongs to a beat and shows what the narration says over it; no unrelated mood picture. Answer early, deepen after (no withheld payoff, SE-21). Shots are contiguous. | [code] beat and sentence ids present, no gaps; [editorial] relevance |

## B. Shot grammar

| ID | Rule | Check |
|---|---|---|
| UR-04 | **Three shot types.** **A** wide/establishing: a huge world, figures tiny or absent. **B** medium/action: at most 1–2 characters doing one action. **C** extreme close-up: objects and hands only, no faces, no environment. | [code] type is A, B or C; [editorial] the picture matches its type |
| UR-05 | **ABC sequencing.** A beat runs A → B → C; B → C → B inside one action and C → A after a revelation are fine. Never three shots of one type in a row. A beat after the first 30 s should open on A (UR-02 keeps long A shots out of the opening). | [code] three in a row = FAIL; a later beat not opening on A = REVIEW |
| UR-06 | **Faces: recognisable first, else faceless.** If the character has a reusable caricature (`look.caricatures`), the face is shown in B as our sprite over a pod plate. Else (no caricature, or the pose, action or object breaks UR-04 or UR-07) the figure is faceless: from behind, in silhouette, in profile in shadow, or hands with a signature prop (Einstein's spectacles, Curie's glass vials, Tesla's coil sketch). A pod prompt never names a cast member and never asks for a face. | [code] every B has `caricature:<name>` (the name must be in the look) or `faceless`; cast names and face words in prompts (a negated "no faces" is allowed) |
| UR-07 | **Painted style, one suffix.** Every pod prompt ends with the episode's style suffix (`look.style_suffix`) after its mood clause. Banned: hyper-realistic, photo-realistic, photo/photography, Unreal Engine, Octane, 3D render. Every person or hand a pod prompt paints follows the look's `figure_style` (UR-22: one universe; the earlier "natural proportions for pod figures" made a realistic man and a caricature hero look like two different worlds, creator 2026-10-16); our cast sprites are graded to their plate (saturation, black level, warm/cool tint, contact shadow). | [code] suffix and banned words; [editorial] the sprite grade |

## C. Mood: emotion → light → colour

| ID | Rule | Check |
|---|---|---|
| UR-08 | **The topic sets the palette range.** Each episode's `look.json` lists 5–7 colour names per story phase, and every shot names 1–4 colours from its phase. The palette moves with the story, so the colour itself tells the arc (Stone Age: ochre, umber, charcoal, fire amber, river teal; copper green in Month 1; iron grey and furnace orange in Year 1; electric white in Years 2–10). | [code] |
| UR-09 | **Every shot has one emotion,** from a fixed list: discovery, fear, tension, joy, humour, calm, sorrow (`explainer_engine/edit/moods.json`). The emotion picks the key light, the colours inside the palette and the contrast; its mood clause goes into the pod prompt and its grade (lift, saturation, warmth, contrast, vignette) into the compositor. The drawn style must still create the mood. | [code] emotion in the list; the clause in every new prompt |
| UR-10 | **Mood continuity.** The emotion changes at a beat boundary or on a sound event; light direction stays the same within a beat. | [code] a change inside a beat without `sound` = REVIEW; [editorial] light direction |

The emotion table (the canonical values are in `moods.json`):

| Emotion | Key light | Colour inside the palette | Contrast |
|---|---|---|---|
| discovery | one warm source, rim light, light shafts | warm highlights against cool shadows | medium-high, one bright focus |
| fear | low and hard, from below or behind | cold, desaturated, one warm accent at most | low-key, deep blacks |
| tension | side light through dust or haze | dusty warm earth tones | high |
| joy | high warm light, golden hour | saturated warm, open sky | high-key |
| humour | bright even daylight | clean, light | medium |
| calm | blue hour or embers | cool with a small warm glow | low |
| sorrow | overcast, flat | grey-blue, desaturated | low |

## D. Editor and timeline

| ID | Rule | Check |
|---|---|---|
| UR-11 | **Duration ranges.** A 5.0–7.0 s, B 3.5–5.0 s, C 2.5–4.0 s (the last shot may hold longer as a tail). | [code] |
| UR-12 | **Cut only in a pause.** A cut falls inside a narration pause after a comma, period, colon, semicolon or question mark, at least 0.05 s after the word before and 0.05 s before the next word (Kokoro word timings). Never inside a word, never between two words without punctuation. `solve_cuts` places cuts by dynamic programming over the pauses; if no placement exists: hold a shot longer within its range, merge two shots, or add a 0.3–0.6 s pause at the nearest comma, in that order. | [code] |
| UR-13 | **Ken Burns.** Zoom stays within 1.00–1.15. A: a slow horizontal pan (≤ 6 % of the width per 5 s) at one zoom between 1.05 and 1.08. B: a slow push-in (1.00 → ≤ 1.10). C: static or a pull-out (≤ 1.08 → 1.00). No camera shake. | [code] |
| UR-14 | **Transitions.** Hard cuts by default, at least 90 % of all transitions. A 1.0 s cross-dissolve only where the shot marks `time_jump` or `place_change` (Day 1 → Week 1, a new valley). | [code] |
| UR-15 | **Sound at cuts.** A swish or foley on a cut comes from the sound library (D-34) and never masks a word; music sits under the narration with ducking (AUDIO_SYSTEM.md). | [code] the id is in the library manifest; [editorial] masking |

## E. Stakes, heroes and tone (rule base 2; creator, 2026-10-16, D-40)

The creator's review of the first Day 1 pictures: too generic, a "picnic" of meadows and hands, no recognisable heroes, no
fear or nervousness, nothing a viewer imagines when they think of the Stone Age. These rules apply to every topic (history,
science, fantasy crossovers); `look.json` switches them on with `"rule_base": 2`. The vocabulary lives in
`explainer_engine/edit/stakes.json`.

| ID | Rule | Check |
|---|---|---|
| UR-16 | **No passive scenery; stakes in every frame.** Every shot has a `stakes` line (at least 5 words: what is at risk in this frame) and its pod prompt shows it: at least one cue from the stakes vocabulary (weather, fire, danger, hunger, conflict, strain, darkness, crowd, scale). The passive words (peaceful, serene, idyllic, picturesque, lovely, scenic, sunny meadow, calm landscape...) are banned. A wide shot shows the hostility or scale of the world, a close-up the gritty detail (shaking hands, blisters, sparks, cracked skin), never a pretty view. | [code] |
| UR-17 | **Named heroes in every B shot (amends UR-06).** A B shot shows 1-2 real, named heroes of the episode as our caricature sprites over a plate, each with an emotional pose (panic, shock, argue, shiver, exhausted, triumph, dismay, scheme, struggle, point, lecture, amazed, think, smug, recoil, plead); the standing-idle pose is not allowed. A faceless B shot needs a written `faceless_reason` and at most 15 % of the B shots may be faceless: anonymous backs are not a default. A pose that is not in `look.pose_bank` is a reusable sprite to make (Gemini is allowed for reusable cast art, D-36). | [code]; [editorial] the likeness and the pose read at a glance |
| UR-18 | **Friction.** A beat with two or more B shots has at least one with friction: two heroes disagreeing, a hero failing at a basic task, a reaction to someone else's plan. The comedy is human friction, never invented science. | [code] REVIEW |
| UR-19 | **Archetypes.** Every hero has one archetype line in `look.archetypes` (Newton the proud critic, Einstein the dreamy improviser, Franklin the organiser...); the pose, the dialogue and the humour stay in character. | [code] REVIEW for a missing line; [editorial] |
| UR-20 | **Plates are empty ground.** A plate prompt (a picture that our sprites stand on) never contains a people word (person, man, figure, crowd...): the model paints people whatever "empty of people" says. Describe empty ground instead. | [code] |
| UR-21 | **Tone.** Entertainment first, facts second: dry wit, irony and situational humour about brilliant people failing at basic survival; the physics, history and constraints are told straight and never invented for a joke. Scripts follow the `narration-script` skill, pictures the `shot-visuals` skill. | [editorial]; narration_lint for the script |
| UR-23 | **World fidelity.** Every visible object, costume and building comes from the topic's `world.json` (the host era's material culture, the visitors' own costume) or the claim map; anything in the era's `absent` list FAILs in the prompt and in the picture (a visitor's own prop is REVIEW). The world resolver names host, visitors and the light owner before any prompt (D-41, VISUAL_WORLD_ARCHITECTURE). | [code] `world.resolver.check_text`; [editorial] visual judge |
| UR-24 | **Adults read as adults.** Look v2 (`world/look_v2.json`): adult proportions, caricature in faces, hands and posture; child cues (storybook, cute, oversized head, kids, tiny figures, pastel, quirky, wobbly) are banned in prompts; every person has a costume from the world. | [code] child-cue and costume lint; [editorial] judge question `adults` |
| UR-25 | **Anchored generation.** No picture is made from words alone: pod pictures use the channel style LoRA, Gemini pictures use the approved look-bible frames and hero sheets as references; each shot goes to one generator by the routing table (`VISUAL_WORLD_ARCHITECTURE` section 6). | [editorial]; `look.style_bridge` records the approval |
| UR-26 | **One light key, one grade, a visual QA gate.** A prompt names exactly one light key (from the beat's entry in `world.day_arc`); every picture passes the era grade (`finish/grade.py`) and the visual judge (`qa/visual_judge.py`) before the creator sees a contact sheet. | [code] light-key lint, grade, judge |
| UR-27 | **Story state.** The world's `day_arc` lists what the story has not made yet at each beat (`not_yet`, e.g. fire, campfire, flames before the fire beat): the prompt says "no X anywhere in the frame", never names it otherwise, and drops the atmosphere words that imply it (woodsmoke); the visual judge asks `too_early` on every picture. A picture that shows it is repainted. | [code] `world.resolver.check_text`; [editorial] visual judge |

Real people: the heroes are real historical figures drawn as caricatures in a commentary and parody format. The creator decided
this on 2026-10-16; it is a risk to manage, not a guarantee: RIGHTS_AND_FAIR_USE.md records what is and is not covered, and
a likeness the estate actively licenses (Einstein's is one) is checked before the episode is published.

## The shot record

```json
{"id": "d1-04", "beat": "rules", "phase": "day1", "type": "B", "emotion": "joy", "start": 10.611, "end": 14.899,
 "sentences": [6], "motion": {"kind": "push", "z0": 1.0, "z1": 1.06}, "transition": "cut",
 "picture": "d1_plate_riverbank", "source": "new", "face": "caricature:darwin", "palette": ["ochre", "river teal"],
 "prompt": "medium shot of a river bank ..., golden hour light, ..., painterly storybook illustration, ...",
 "sound": "pop_in__v1"}
```

Optional fields: `time_jump`, `place_change`, `transition_seconds`, `sound_at` (seconds into the shot), `tail`
(the last shot), `grade` (copied from the emotion). The first worked example is
`examples/stone_age/day1_v1/` (built by its `build_shots.py`, 39 shots, 0 FAIL).

## Where the numbers come from

The durations, the 1.15 zoom, the 90 % hard cuts and the cut-on-pause rule are the creator's channel style (D-37), not
research findings: the seed research rejected a universal cut rate (SE-20), so they are judged by the channel's own
retention curves (PUBLISHING_AND_ANALYTICS.md) and changed only on that evidence. The first-30-s slack (minimum + 1 s),
the pan speed and the 0.05 s cut margin are engineering defaults.
