# Shot prompts for animated shots

How the prompts of an animated shot are written: the keyframe (Qwen-Image-2512 + the style LoRA), the next pose of the same
shot (Qwen-Image-Edit-2511 + the scene LoRA, from the master frame), a cut to a new angle of the same scene, and the video
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
| `keyframe` | Qwen-Image-2512 + style LoRA | `wldnk style, ` + who (by what they look like) + the one action + where + light |
| `nextpose` | Qwen-Image-Edit-2511 + scene LoRA (+ style LoRA), image = the MASTER | `nextpose, a later frame of the same continuous animated shot, same camera: ` + one actor's change, the others' small reaction + "Same characters, same camera ..." |
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
