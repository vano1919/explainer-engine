# Shots composed from reusable assets

ვანო set the plan on 2026-10-25 (02:19 and 02:21 Tbilisi):
- the style LoRA draws only assets: empty backgrounds, every hero from the angles a scene needs, props, crowd units and
  effects;
- code composes every shot from those assets, from a dialogue between two people to a battle of hundreds, so assets are
  reused, money is saved and the style stays the same;
- a picture or a video model then animates the shots.

The scene LoRA is out of production. Its 499 pairs (plus 336 held-out) stay as data to measure with and to test this code.
No generation starts before this system and its style tests are ready.

Code: `explainer_engine/compose/`. Tested by `tests/unit/test_compose.py`. Layout and sizes: `scripting/layout.py`
([KEYFRAME_GATE](KEYFRAME_GATE.md), LY-). Picture checks: KG-. Prompt shape of every asset: LT-65
([LORA_TRAINING](LORA_TRAINING.md)).

## The flow

1. The script becomes a shot list: size, at most 5 s each, and per shot `compose` or `reuse` (AC-12). The planner rules come
   from the cartoons measured on 2026-10-25 (below).
2. `library needs` lists the assets those shots use. Only the missing ones are drawn (AC-04): that list is the paid part.
3. Each asset is drawn with Qwen-Image-2512 and the style LoRA in the LT-65 shape (bf16, 1280x720 or a tall plate),
   cut out (BiRefNet) and checked (AC-15, AC-14, KG-). It is shown to ვანო and approved (AC-02).
4. `frame` composes each shot on the CPU (AC-05..AC-09), with crowds from `crowd` (AC-10, AC-11). A light repaint with the
   style LoRA (img2img 0.30) evens the light (retired for keyframes by D-78, 2026-10-25 10:50 Tbilisi: no img2img pass). That repaint is the only paid step per shot, ≈$0.01.
5. A `reuse` shot is a crop of an earlier frame (AC-13). Nothing new is drawn for it.

## Rules

| ID | Rule | Severity | Code |
|---|---|---|---|
| AC-01 | **Every asset is one record:** id `<kind>.<name>[.<variant>]` (P-66), kind (background, hero, prop, crowd, fx), file, the source (model, LoRA, prompt, seed). A hero also has its angle (front, three_quarter, side, back), expression and real-size row; a background has its light and horizon | FAIL | `library.check_record` |
| AC-02 | Only an asset the creator approved goes into a video; unapproved assets serve tests | REVIEW | `library.check_record` |
| AC-03 | A three-quarter or side view facing the other way is the same drawing mirrored (no new picture); a front or back view is never mirrored (a scarf, a bag, a parting would swap sides) | - | `Library.find` |
| AC-04 | Before any paid drawing, the shot list's needs are matched against the library; only the missing ones are drawn | FAIL when a shot's asset is missing | `Library.needs` |
| AC-05 | The background's recorded horizon lands on the shot's horizon (the plate slides vertically); if the plate is too short, the shot fails rather than letting figures float. Tolerance: EWS 4 % ... CU 30 % of the frame height | FAIL | `frame.compose` |
| AC-06 | A figure's drawn height (above the ground contact) fills its layout box (LY-02: perspective from real height and distance); its contact row stands on the box bottom | - | `frame.place` |
| AC-07 | A soft contact shadow lies under feet that are in the frame, offset away from the light | - | `frame.place` |
| AC-08 | Aerial perspective: figures farther than 3x the lead's distance take up to 28 % of the horizon's colour | - | `frame.haze_for` |
| AC-09 | Painting order is far to near | - | `frame.compose` |
| AC-10 | A crowd is scattered over a band of ground by perspective (uniform over the ground's area, so more people far away), with a real gap between people. No more than 15 % of figures stand next to the same unit facing the same way | FAIL | `crowd.scatter`, `crowd.check` |
| AC-11 | A crowd of 10 or more uses at least 3 different units | FAIL | `crowd.check` |
| AC-12 | A shot of the same setup (background, angle, cast) as an earlier one, at the same or a tighter size, reuses that frame through a crop. A teaser (`teaser_of`) reuses the later shot it shows | - | `reuse.plan` |
| AC-13 | A crop never enlarges a frame more than 1.6x of its render scale. Otherwise compose the shot, or render the source larger | FAIL | `reuse.check` |
| AC-14 | **Style score:** DINOv2-small on 6 crops against the creator's 11 style photos, compared with a same-place control drawn in the LT-65 shape. More than 0.10 below the control is REVIEW. It is a measured hypothesis (one source type, D-59) and never fails a picture alone | REVIEW | `style_score` |
| AC-15 | A cut-out is the figure alone: not cut by the picture's edge, and no patch of ground under the feet | FAIL | `library.check_cutout` |
| AC-16 | **Episode look:** each episode has one look file (`episode_look/1`), measured from its approved key frame (Lab mean and spread, hue histogram, 6 palette colours) with one colour-and-light phrase and named light variants (night, interior ...). It sits on top of the style LoRA and never replaces it: the LT-66 absolutes stay as they are | FAIL without a look file once an episode has a key frame | `episode_look.make` |
| AC-17 | The look phrase is at most 10 words of colour and light vocabulary only: no style or medium words (A8), no camera, size or number words (A6), not the trigger or the tail. It goes at the end of every style-LoRA prompt of the episode, and the whole prompt still passes LT-65/66 (40 words): scene words shrink, the absolutes never | FAIL | `episode_look.check_phrase`, `apply` |
| AC-18 | **Colour drift:** each new picture's colour distance to the look (Lab mean shift in units of the look's spread, plus hue-histogram distance) above 0.35 is REVIEW. A hypothesis with one source type (D-59): calibrate on the first episode | REVIEW | `episode_look.drift` |
| AC-19 | **Bounded grade:** a composed frame may be matched toward the look (Reinhard in Lab) at strength at most 0.35, lightness at half of it, so ink lines and drawing stay. The original file is kept; a grade never repaints | FAIL above 0.35 (the code caps it) | `episode_look.grade` |

## What the cartoons say (measured 2026-10-25, free)

Source: HF `footage_2026-10-23` (6 videos: Rick and Morty, Inside Job, Solar Opposites; 3312 shots without duplicates;
120 shots labelled by hand in `grammar_2026-10-24`).
- Shot length: median 3.2 s, half between 2.5 and 4.8 s, 23 % longer than 5 s. The shot list only holds shots of 2 s or
  more, so these numbers lean long.
- About 20 % of shots return to a setup seen within the last 8 shots. This is an estimate from thumbnail similarity, with
  36 pairs checked by eye. It is a lower bound: the videos are compilations.
- The camera is nearly still in 66-77 % of shots.
- Shot sizes: MS 30 %, WS 20 %, MCU 18 %, MWS 17 %, insert 8 %, EWS 4 %, CU 3 %. A shot shows 1-2 people in 79 % of cases,
  3 or more in 15 %, and 16 % are over the shoulder.

## What the first CPU test showed (2026-10-25, the composition test's 4 heroes and 2 backgrounds)

Sheet: project files `film_1min_2026-10-24/compose_demo/`.
- A WS of 4 heroes, a MWS of 2, a reuse crop and a crowd of 90 were composed in seconds, at $0.
- AC-05 failed the MWS. In an eye-level two-shot the horizon crosses the figures' heads (0.11 of the frame), while the plate's
  horizon is at 0.48. Close shots need their own plate: a tall plate, or one drawn at chest height.
- AC-15 failed the girl's cut-out: a block of snow was cut with her, and she sat on it in every shot.
- The crowd test used the four heroes as units. Real crowds need their own units: 6-8 soldiers per side, three-quarter view,
  3-4 poses each.
