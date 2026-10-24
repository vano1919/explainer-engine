# Keyframe gate: check every picture, log the cause, fix only the weak part

ვანო asked for this on 2026-10-24 (18:53 Tbilisi). The system draws a picture for the video and checks its logic, the world's
physics, and whether a video can be made from it. A failing picture is drawn again. Only a passing master goes on to the
scene LoRA. Every session records what came out right and wrong and whose fault it was (the prompt, the style LoRA or the
scene LoRA). The data is sorted, and only the weak part is fixed: a prompt rule, or a LoRA's next version.

Code: `explainer_engine/qa/keyframe_gate.py`, tested by `tests/unit/test_keyframe_gate.py`. Prompt rules:
[SHOT_PROMPTS](SHOT_PROMPTS.md) (KP-). LoRA training: [LORA_TRAINING](LORA_TRAINING.md) (LT-).

## The flow

1. A shot card (film_shots) becomes a master. The master is drawn with Qwen-Image-2512 and the style LoRA, in 3 variants.
2. Each variant goes to the gate (KG-01..KG-13).
3. A passing variant goes on. Next poses are drawn from it with Qwen-Image-Edit-2511 and the scene LoRA only, and every pose
   goes through the gate again.
4. A failing shot is drawn again with a new seed, at most 3 times (KG-14). After that the prompt is fixed.
5. Every picture writes one line to `qa_log.jsonl`. The session's `summary` turns those lines into actions (KG-15).

The questions go to a vision model as one numbered list (`vlm_prompt`). Qwen2.5-VL-7B is already on the training pod, so
this is free. Claude reads a sample of the same pictures and answers the same questions; where the two disagree, the
disagreement is itself logged.

## Rules

| ID | Check | Expected | Hard | Evidence |
|---|---|---|---|---|
| KG-01 | number of people and animals (cast members include animals, e.g. the mammoth) | the card's count | yes | busy masters invented people (scene LoRA samples, 2026-10-24) |
| KG-02 | every card person is present | yes | yes | "the woman" painted a stranger (KP-01) |
| KG-03 | every person on the card's screen side | yes | yes | the action went to the wrong hero (KP-02) |
| KG-04 | the actor's height share of the frame | yes | no (REVIEW): how well a VLM judges this is unmeasured | small figures froze in video (KP-13) |
| KG-05 | everyone rests on what the card says (snow, a log, a seat) | yes | yes | ვანო 2026-10-24: logic and physics |
| KG-06 | every relation on the card holds ("a living mammoth stands behind the boulder") | yes | yes | ice-age master: the mammoth reads as a carving on the rock |
| KG-07 | nothing floats without a reason | no | yes | physics |
| KG-08 | anatomy: the right count of limbs and fingers, nothing stuck in a face or an eye | no | yes | glasses inside an eye (kf_v2 bus pictures) |
| KG-09 | no ambiguous animal or object (carving, painting or real) | no | yes | the mammoth; the fish inside the underwater dome |
| KG-10 | no text or lettering | no | no (REVIEW): lettering is added in editing | disco, jazz and USSR signs garbled (20-era sheet) |
| KG-11 | free space on the side the actor will move into | yes | yes | KP-03 (nobody leaves the frame) |
| KG-12 | the actor's arms and hands are fully inside a master | yes | yes | IC layouts with cut limbs froze (KP-12) |
| KG-13 | next pose or cut: the same drawing style as the first image | yes | yes | style LoRA inside Edit changed the look (2026-10-24) |
| KG-14 | **At most 3 tries per shot.** Then the prompt is fixed, never an endless redraw | - | - | ვანო: regenerate only on a fail; spend nothing blind |
| KG-15 | **The cause is measured, not guessed.** The same prompt is drawn without the LoRA, and with the LoRA on another seed, on 2-3 pictures per new error type. If the base model also makes the error, the fix is the prompt: a lint rule and a test, which is free and always tried first. If only the LoRA makes it, on both seeds, the cause is the LoRA: such cases are collected, and at 15 of one type a retraining with passing pictures of that case is proposed to the creator (paid), followed by a re-run of the old test sheet. If the other seed is clean, it was chance | - | - | KP-14; a LoRA always retrains as a whole, so the added data aims at the weak part and the old sheet guards the rest |
| KG-16 | **A LoRA loads only into the base it was trained on.** The style LoRA goes only into Qwen-Image-2512 (masters, hero sheets); the scene LoRA only into Edit-2511 (poses, cuts) (`check_stack`) | - | - | the style-weight test 2026-10-24: the style LoRA inside Edit swapped identities at every weight, and with the scene LoRA at 0.8 it gave junk; Edit with the scene LoRA alone kept a wldnk master's style in 4 of 4 poses |

## Measured on the approved 20-era sheet (2026-10-24, Claude's read)

| Result | Pictures |
|---|---|
| Logic errors | 1 of 20: underwater_city (a man without breathing gear in a water-filled dome with a giant fish, KG-07/KG-09; the prompt asked for "a fish-farmer feeding giant fish" in glass domes) |
| Drawn as asked, but reads ambiguously | 1: ice_age_tribe. The prompt asked for "a woman painting mammoths on a rock", and the model painted that, but without visible paint or brush the mammoth reads as a carving or a real animal (KG-09). Correction 2026-10-24 19:55: this was first counted as a logic error before the prompt was read |
| Weak but readable | 1: japan_dojo (unclear how many swords there are and who holds which) |
| Garbled text (REVIEW) | 3: disco_1970s, jazz_1920s, ussr_queue |
| Logical, but small crowded figures (limited motion, KP-13) | 3: ussr_queue, greek_agora, school_class |

Both problem pictures do what their prompts said; the prompts were ambiguous. That is why the composition fields on the card (relations, support, height,
free space) come first and a style LoRA retraining does not.
