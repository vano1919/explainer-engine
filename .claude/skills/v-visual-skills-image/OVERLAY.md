# Overlay for `v-visual-skills-image`: Gemini Task pictures in the series film's look (layer L9, stage G5)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from smixs/visual-skills, page `image` (CC-BY-4.0, credit Serge Shima, see `NOTICE`; commit `61a60d317f`).
Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the only picture maker of a v4.3
episode: Gemini's own image tool (Flash, Nano Banana family) inside the creator's subscription, driven by text the engine
writes. The upstream text is this folder's `SKILL.md`; its `references/` stay usable as a prompt-craft library,
mainly `nano-banana.md`, `golden-rules.md`, `characters.md`, `de-slop.md` and `vision-decomposer.md` (table below).

## Where this sits

The engine never calls the tool. It writes packs and reads back files: the Task route in `explainer_engine/gemini_task/`
(GC-20..GC-27, CLI `python -m explainer_engine.gemini_task --help`) and the chat route in
`explainer_engine/imagegen/turn_pack.py` (GC-01..GC-19, CLI `python -m explainer_engine.imagegen.turn_pack --help`). The PC
session pastes, attaches and downloads; manual pasting is the fallback (GC-15). Everything here is free. The paid Gemini
API client (`explainer_engine/imagegen/gemini.py`) is off by default and only re-makes failing close-up hero shots at 2K,
each batch priced and asked first (GC-14).

Not here: what the shot must show (skill `v-director-cinematic`), holding a face across many pictures (skill
`v-scenario-consistency`), laying start pictures out for a scene (skill `v-scenario-storyboards`), motion words (skill
`v-visual-skills-video`).

## The look: one era film per series (rule 20)

The creator gives the story; Claude offers two or three script variants, then two or three successful films of that era
with a recommendation; he picks. From then on every prompt says so plainly, for example "Frames from a video in the style
of the film 1917 (2019)". On 2026-11-19 (22:22 UTC) naming the film beat a long description of its look. Keep beside it
one era line in the preset's shape (GC-22: the light sources and materials of that world) and nothing else about style.
Never ask for a specific shot, character or scene of that film; the film lends its light, palette and lens habits only.

Upstream warns against "like brand X" comparisons and against lens numbers on Nano Banana. Here the creator's rule wins
for the film name. Lens and camera height may stay in the place block as position words (the batch-2 test kept "35 mm
lens" and the creator approved it); they are not quality boosters.

## Anatomy of one prompt

In this order, as plain sentences (GC-06: one moment, no tag lists, no second action):
1. The film line (the series look) and, where the preset uses one, the style-reference clause for image 1 (GC-01, GC-21).
2. **The place block**, the same words in every picture of that place: where and when, what is on the left and on the
   right, the floor and the sky, camera height and direction. Write it once per place and paste it unchanged; a re-worded
   place is a new place to the tool (GC-05, LV-01).
3. **The people**, each with the verbatim registry text from the cast (GC-04, HI-01): age, build, face, hair, garment,
   prop. Never re-describe a hero in your own words inside a shot.
4. **The moment**: who does what, which way they face, where they look, what is in their hands, the light direction.
5. For an end frame: "the same place, camera, people and light, two seconds later; only this changes: ..." with its start
   frame attached (GC-09).

Never ask for writing of any kind (GC-07); numbers, names and dates are drawn later by Python. Keep out the look's
`never_words` (GC-18; the list is per look in `config/visual_style_presets.json`, so a film-look series sets its own).

## Running a batch

1. **T0 once per route** (GC-20): `python -m explainer_engine.gemini_task t0` then `t0-record`; without a PASS every other
   message refuses. T0 sets the batch size (six by default, `config/gemini_task.json`).
2. **References first** (GC-23): round R1 hero portraits and places, round R2 full bodies with their own portrait; the
   creator approves them by looking (`approve`, `approve-anchor`). No scene batch before that.
3. `queue <episode>`, then `batch <episode> <no>`: six self-contained prompts, references listed per picture in the
   fixed order (style anchor, heroes in cast order, the place, props; at most the reference cap, GC-02).
4. The PC session pastes the batch word for word into one chat of this episode (GC-10) and downloads in order. The answer
   must end with a `BATCH REPORT`: one `MADE` or `NOT MADE` line per picture and `prompt: AS GIVEN|CHANGED` (GC-24).
5. `intake <episode> <no> --answer <report> --drop <folder>` maps files to ids by order; a count that differs from MADE is
   refused. Turn-pack intake checks size, 16:9, bars, watermark band, duplicates (GC-12).
6. **Look at every picture** and write the observation (P-5). `verdict <episode> <id> ok|redo --correction "..."`.
7. A daily limit ends the batch with `NOT MADE: limit`; `resume` continues from the first missing picture next day (GC-27).
8. Redo comes after the phase, in batches of the batch size: the original prompt plus ONE positive sentence of what the
   picture must show, without the failed picture attached (GC-25). A picture that fails its redo goes to the creator.
9. `turn_pack promote` makes the working master with the free 2x upscale (GC-14); without an installed upscaler the row is
   NOT_RUN, never a plain resize. `remake_list` lists only close-up hero shots with a failed sharpness row, priced.

## Failure modes and fixes

| What came back | Cause | Fix (P-5 rung) |
|---|---|---|
| Cartoon or 3D-animation faces | style anchor or old preset words pulling | R2: name the film first; check image 1 is the right anchor (GC-11, GC-21) |
| The style picture's people copied into the scene | style reference without its clause | R2: add the clause; never attach outside samples (GC-01) |
| The place moves between start and end | place block re-worded | R2: paste the block unchanged; attach the start as image 2 (GC-09) |
| Extra soldiers, wrong head count | crowd words without a number | R2: "Exactly N people", named ones listed (CT-04) |
| A wrong period object (rubber soles, steel helmet in 1914) | not named in the block | R2: name the right object positively; check the claim map |
| Square or illustrated picture | tool ignored the format | re-ask once, then the creator |
| One picture refused for violence | moderation on a weapon beat | R2: soften the clause, show the consequence or the hands |
| Two of six missing | daily limit | `resume`, never a model switch (GC-27) |

## Checks in code (SK-2)

`explainer_engine/gemini_task/gate.py` (T0), `queue.py` (shot type, image 1, reference cap, R1 before R2), `prompts.py`
(`check`: style clause, keep-scene), `report.py` and `batch.py` (report parse, intake by order, verdict, one correction
sentence, redo after the phase), `explainer_engine/imagegen/turn_pack.py` (`check_prompt`, intake, `promote`,
`remake_list`), `explainer_engine/imagegen/vault.py` (asset record, reuse before new, OR-18), and
`explainer_engine/episode/shot_state.py` (an observed picture whose hash changes is observed again).

## References: when to open which

| Need | Open |
|---|---|
| What the Gemini image model rewards and ignores | `references/nano-banana.md` |
| Positive framing, one change per iteration, edit before re-roll | `references/golden-rules.md` |
| A hero across many pictures | `references/characters.md` (then skill `v-scenario-consistency`) |
| A picture that "looks AI", too glossy, too clean for a war film | `references/de-slop.md` (located imperfections: mud, frost, stubble) |
| The creator attaches a still and says "like this" | `references/vision-decomposer.md` (decompose, then write our blocks) |
| Words for motivated light, lens and film stock | `references/creative-direction.md` |
| Hero portraits of round R1 | `references/patterns/portrait-cinema.md` |
| A full checklist for a crowded scene | `references/prompt-framework.md` |
| Sequences of frames | `references/storyboards.md`, as background to skill `v-scenario-storyboards` |
| The 2K re-make "same picture at 2K" | `references/editing.md` (preserve lists) |

## Not used from upstream

GPT Image and its five-slot template, quality and size levers we cannot set in the chat, text rendering, slides,
infographics, multi-panel grids in one image (GC-17: one prompt, one picture), e-commerce, fashion, food, UI and poster
patterns, 2D-to-3D, the Russian triggers, and the rule against naming a film (overridden by rule 20).
