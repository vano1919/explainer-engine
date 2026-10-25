# Keyframe gate: check every picture, log the cause, fix only the weak part

ვანო asked for this on 2026-10-24 (18:53 Tbilisi). The system draws a picture for the video and checks its logic, the world's
physics, and whether a video can be made from it. A failing picture is drawn again. Only a passing master goes on to the
scene LoRA. Every session records what came out right and wrong and whose fault it was (the prompt, the style LoRA or the
scene LoRA). The data is sorted, and only the weak part is fixed: a prompt rule, or a LoRA's next version.

Code: `explainer_engine/qa/keyframe_gate.py`, tested by `tests/unit/test_keyframe_gate.py`. Prompt rules:
[SHOT_PROMPTS](SHOT_PROMPTS.md) (KP-). LoRA training: [LORA_TRAINING](LORA_TRAINING.md) (LT-).

## The flow

1. A shot card (film_shots) becomes a master. The master is drawn with Qwen-Image-2512 and the style LoRA, in 3 variants.
2. Each variant goes to the gate (KG-01..KG-13, KG-17..KG-21), then to Claude's table (KG-22).
3. A passing variant goes on. Next poses are drawn from it with Qwen-Image-Edit-2511 and the scene LoRA only, and every pose
   goes through the gate again.
4. A failing shot is drawn again with a new seed, at most 3 times (KG-14). After that the prompt is fixed.
5. Every picture writes one line to `qa_log.jsonl`. The session's `summary` turns those lines into actions (KG-15).

The questions go to Qwen2.5-VL-72B (AWQ) one at a time (`single_prompt`, KG-20); the 7B with one numbered list proved
unreliable on the film tests. Claude then fills the same questions for every picture (KG-22); where the two disagree, the
disagreement is itself logged.

## Rules

| ID | Check | Expected | Hard | Evidence |
|---|---|---|---|---|
| KG-01 | number of people and animals (cast members include animals, e.g. the mammoth), and then for each card figure how many times it appears; an animal seen only in part (a trunk at the frame edge) is still a card figure | the card's count; 1 each | yes | busy masters invented people (scene LoRA samples, 2026-10-24); film test v2: a second mammoth passed the total count (5 of 6) |
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
| KG-12 | the actor's arms and hands are fully inside a master, in a full shot or wider (MS, MCU, CU and ECU cut the arms by design) | yes | yes | IC layouts with cut limbs froze (KP-12); film test v2 failed a close-up for it |
| KG-13 | next pose or cut: the same drawing style as the first image | yes | yes | style LoRA inside Edit changed the look (2026-10-24) |
| KG-17 | no measurement lines, arrows, rulers, percentages or numbers drawn over the picture | no | yes | film test v2: a prompt with numbers drew them in 6 of 10 pictures, and the soft text check (KG-10) noticed only 2 |
| KG-18 | two figures are not look-alikes (same hair colour or same clothes), asked when the card has two or more | no | yes | the pink-haired girl drawn twice in all 10 bus pictures (2026-10-24); a per-figure count alone let it through |
| KG-19 | each figure has its sheet marks (`marks`: round glasses, a red scarf) | yes | yes | asset test: the old man lost his glasses and the gate said nothing |
| KG-21 | the world's absent things are absent (`absent`: a road, a car, a building in the ice age); objects are counted (`things`: one bus) | no / the count | yes | asset test: three buses; a mammoth in a car's trunk on asphalt |
| KG-20 | **The judge is Qwen2.5-VL-72B (AWQ) and every question is asked on its own** (`VLM_MODEL`, `single_prompt`) | - | - | the 7B with one numbered list missed a second mammoth, three buses and the twins, and failed correct clothes |
| KG-22 | **Claude's own table before the creator sees a picture** (`keyframe_gate table`): every gate question plus the style row against the approved eras sheet, filled with what the picture shows; a picture is never shown with "looks fine" | - | - | ვანო 2026-10-24 23:29 Tbilisi: "you think it's fine", while every bus picture had a twin |
| KG-23 | **The style spec (`blind_check.STYLE_SPEC`), the approved eras sheet put into six checkable items:** line (bold, uneven, hand-inked outlines), figures (lanky, angular, big heads and noses, bulging eyes), colour (earthy base, a few glowing accents), texture (chalky painterly background, flat-filled figures, no vector gradient, no 3D, no photo, no oil), detail (a busy world in the same ink line), light (one source, warm-cool). Each is answered yes / no / ? for every picture. A style PASS needs both halves: every item "yes" and the DINOv2 score against the 20 eras cells at or above the weakest eras cell (0.557, `STYLE_SCORE_MIN`). A "no" FAILs; a "?" is REVIEW | no | yes | 2026-10-25: the 2512 ControlNet frames scored 0.56-0.69 but were flat vector; the 2.1 LoRA at step 750 scored 0.19-0.45 |
| KG-24 | **The blind description.** The describer sees the picture and `DESCRIBE_RULES` only, never the prompt or the card. It counts every kind of thing corner to corner, places it with the card's place words, names it with a plain noun, reports text, overlays, floating things and anatomy, answers the style items, and writes "?" plus an `uncertain` line instead of guessing | - | - | ვანო 2026-10-25 16:27 Tbilisi: describe the picture, then compare it with the prompt's logic; a question list tells the judge what to find |
| KG-25 | **Code compares the description with the contract** (`compare`): exact counts of the card's `things`, its `absent` things (synonyms: a "skyline" is a building), the number of people, floating things and broken anatomy FAIL; text or overlays REVIEW. Relations stay with the question gate (KG-06) | yes | yes | the 2.1 LoRA sample of 2026-10-25: one bus asked, a second small bus and a city drawn |
| KG-26 | **A "?" gets a second look before anyone sees the picture** (`second_look`): one focused question about that item alone, on the whole picture, with a short reason. Still unsure: REVIEW for Claude's table (KG-22), never a PASS | - | - | ვანო 2026-10-25: "if there are question marks, check the description again" |
| KG-27 | **One vocabulary for prompt, card and description.** The prompt writer names a counted thing with the card's `things` noun and never puts an `absent` word in a picture prompt (film_shots `absent_check`, PR #24); the describer uses the same plain nouns and place words; the comparer maps synonyms (`SYNONYMS`). A word the comparer cannot map is a REVIEW, never a silent pass | - | - | "city bus" drew a city (2026-10-25); one vocabulary keeps the loop consistent (ვანო) |
| KG-14 | **At most 3 tries per shot.** Then the prompt is fixed, never an endless redraw | - | - | ვანო: regenerate only on a fail; spend nothing blind |
| KG-15 | **The cause is measured, not guessed.** The same prompt is drawn without the LoRA, and with the LoRA on another seed, on 2-3 pictures per new error type. If the base model also makes the error, the fix is the prompt: a lint rule and a test, which is free and always tried first. If only the LoRA makes it, on both seeds, the cause is the LoRA: such cases are collected, and at 15 of one type a retraining with passing pictures of that case is proposed to the creator (paid), followed by a re-run of the old test sheet. If the other seed is clean, it was chance | - | - | KP-14; a LoRA always retrains as a whole, so the added data aims at the weak part and the old sheet guards the rest |
| KG-16 | **A LoRA loads only into the base it was trained on.** The style LoRA goes only into Qwen-Image-2512 (masters, hero sheets); the scene LoRA only into Edit-2511 (poses, cuts); the Qwen-Image-2.1 style LoRA (`wldnk_qi21`, 2026-10-25) only into Qwen-Image-2.1, where one model both draws and edits (`check_stack`) | - | - | the style-weight test 2026-10-24: the style LoRA inside Edit swapped identities at every weight, and with the scene LoRA at 0.8 it gave junk; Edit with the scene LoRA alone kept a wldnk master's style in 4 of 4 poses |

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

## Film test v2 (2026-10-24): what the pictures showed

60 pictures of the 1-minute film, $1.94. The report, the marked sheets and the logs are in the project files,
`film_1min_2026-10-24/test_v2/`. Most errors came from the prompt text, not the LoRAs:
- A figure named twice with a new article ("the mammoth ...", then "a living woolly mammoth ...") was drawn twice (4 of 4).
- A long tag repeated eight times in one prompt gave one figure twice (4 of 4; a hypothesis, still untested).
- Numbers in the prompt text were drawn as rulers (6 of 10) without making sizes more accurate. The mean height error was
  0.18 with numbers and 0.19 with relative words, both measured by the VLM's boxes, so LY-05 numbers stay out of the text.
- The blockout through ControlNet kept positions best (0.15) but mixed the figures' clothes.
- Edit without a LoRA kept the style as well as the scene LoRA v1 did and followed the action at least as well.
- The style refresh changed nothing visible.
- A cut drawn with Edit kept the master's framing.

## Layout: sizes computed, not guessed (LY-, `scripting/layout.py`)

ვანო asked for this on 2026-10-24 (19:34 Tbilisi). One prompt variant gives exact sizes with a ± tolerance, the other gives
relative proportions, and the system that writes the numbers must not make mistakes. A language model is weak at numbers
and space. The known fix works in two stages: first the layout, then the picture made from that layout. In LLM-grounded
Diffusion this raised spatial accuracy from 37 % to 77 % ([Lian et al. 2023](https://arxiv.org/pdf/2305.13655)). Here code
computes the layout from real sizes and the camera, and Claude only names the things and where they stand.

| ID | Rule | Check |
|---|---|---|
| LY-01 | **Real heights come from one table** (`SIZES`), each with its reference: adult ~1.7 m, city bus ~3.0-3.2 m, woolly mammoth 2.7-3.4 m at the shoulder. Cartoon figures keep real heights | [code] |
| LY-02 | **The shot size fixes the lead figure's share of the frame** (`LEAD_SHARE`: EWS 12 %, WS 35 %, MWS 82 %, MS ~1.9x cut by the frame ...). Every other figure follows by perspective: height = focal × real height / distance. The camera height and the horizon come from the angle; in a full shot or closer the camera is aimed at the lead (headroom `TOP`), so a full shot keeps the feet in the frame and a close-up is given by the head | [code] |
| LY-03 | **A figure outside the frame FAILs**; one cut by the frame edge in a wide shot is REVIEW | [code] |
| LY-04 | **A figure that cannot be seen or cannot act FAILs or is REVIEWed.** FAIL: more than 60 % hidden behind a nearer figure (the scenario's mammoth 6 m behind the bus was 100 % hidden until it was raised on the hill; the girl sitting on the bus step was hidden behind the nurse), or two figures at the same depth overlapping by more than half. REVIEW: smaller than 4 % of the frame height (KP-13) | [code] |
| LY-05 | **The technical prompt:** every figure's height share ± 5 %, its centre and its feet in % of the frame | [code] |
| LY-06 | **The relative prompt:** every figure compared with the lead in words ("about twice as tall as", "about 11 metres behind", "about 5 metres higher up") | [code] |
| LY-07 | **EliGen boxes** come from the same layout | [code] |
| LY-08 | **The blockout:** grey figures on a ground gradient, nearer = lighter. It is a depth-like control picture for a ControlNet (depth / soft edge), the "simple figures first, our style after" path | [code] |
| LY-09 | **Every figure's full tag is said once per prompt.** Later mentions use "the" + its noun (`short`); `repeated_tags` FAILs a prompt that repeats a full tag | [code] |
