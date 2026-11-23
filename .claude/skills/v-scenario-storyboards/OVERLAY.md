# Overlay for `v-scenario-storyboards`: Storyboards from our own pictures (layer L10, stage G5 to G7)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from scenario-labs/skills, page `scenario-storyboards` (MIT, commit `a14d061fe5`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel that makes its panels in the Gemini Task route and
checks them in the video lane; the Scenario platform is never called. The upstream text, written around Scenario's MCP
tools for comics and animatics, is this folder's `SKILL.md`; the folder has no `references/`.

## The idea we keep

The unit is the shot, never the sheet. A "page of six panels" from one prompt cannot be repaired one panel at a time and
its heroes change from cell to cell. So: the table first, the cast locked, one picture per shot from the same approved
anchors, words added afterwards by code, the sheet assembled last and looked at before any clip is bought. Image money is
free here (the chat tool) and video money is not, so the storyboard is the cheapest place to find a bad shot.

## Procedure for one scene

1. **The shot table** comes from the director (skill `v-director-cinematic`): per shot its id, route, story function,
   size, angle, camera move or locked, who is where facing what, the place, the light, and for a `video` shot its
   `edit_plan` mode (VL-01). Only what a camera can see goes in the action column: a thought or a smell becomes a visible
   sign, a line, or narration.
2. **Arrange it as coverage**, not a row of pictures: open on an establishing, place or time shot (VL-09); keep the camera
   on one side of the axis so screen direction holds (CT-06, VL-04); step the size or turn at least 30 degrees between two
   shots of the same people (CT-07); climb the size ladder as pressure rises; break more than three lines in a row with a
   reaction or an insert (VL-08); plan at least one evocative insert (hands, boots, a candle) per scene.
3. **Lock the cast and the place** before any scene picture: approved anchors (GC-23) and the place block written once
   (skill `v-scenario-consistency`).
4. **One prompt per picture**, in batches of six (skill `v-visual-skills-image`): the film line, the place block word for
   word, the verbatim hero text, then that shot's moment. Never chain a picture from its neighbour; a continuation shot gets
   no picture of its own (the clip before hands it over, VL-05) and shows its source on the sheet as "from <shot>".
5. **Letter-free art** (GC-07): no captions, signs, speech bubbles or dates in the pictures. A date and place chip, a name
   label or a map number is drawn by Python later (`explainer_engine/overlay/`, `explainer_engine/maps/`).
6. **The contact sheet**: `explainer_engine/videolane/storyboard.py` lays the start pictures in cut order into
   `production/storyboard/<scene>.jpg` and checks them (VL-10): every shot that needs a picture has one; no two pictures
   repeat a composition (perceptual hash a few bits apart: FAIL); every coverage and insert picture stays in the master's
   place and light (palette and top third against BP-166: REVIEW); the edit plan passes.
7. **Look at the sheet** (P-5): Claude opens it, writes one observation line per shot, and the creator looks. The card
   questions (`explainer_engine/scripting/continuity.py` `vision_questions`) go with it; `python -m
   explainer_engine.qa.sheet_review request` prepares Claude's free answers.
8. **Pin and hand on.** `explainer_engine/videolane/scene.py` writes the paid scene file only from a fresh, non-FAIL sheet
   and pins its sha256; a picture changed afterwards moves the pin and the launch refuses (skill `v-ltxv2-video`).

## When the movement must carry across the cut

Animating each panel on its own resets the performance at every cut. When an action runs on (he climbs the fire step,
then raises the rifle), use the `continuation` mode: the next clip starts from the chosen tail frame of the one before
(VL-05), the camera's end state is the next start (VL-03), and the chain is at most two hops from a fresh picture (P-6).
When the cut changes angle, use `coverage` with its own fresh picture from the master.

## Failure modes and fixes

| On the sheet | Fix |
|---|---|
| Two shots look the same (dHash FAIL) | change size or angle in the table, redraw one (CT-07) |
| A coverage picture has another sky or wall | redraw it from the master with the place block unchanged (VL-04) |
| A hero swaps sides between shots on one axis | fix positions on the card, redraw (CT-06) |
| A costume change appears mid-scene with no cause | either a new approved anchor, or redraw with the old one (CT-08) |
| A fight or weapon panel refused by the tool | soften the clause, show the consequence or the hands; keep the beat |
| Writing appears in a picture | redo with one positive sentence of what the surface shows instead (GC-25) |
| The sheet reads as a slideshow | the table lacks reactions and inserts; go back to step 2 |

## Checks in code (SK-2)

`explainer_engine/videolane/plan.py` (VL-01..VL-09), `explainer_engine/videolane/storyboard.py` (VL-10: presence,
duplicates, place and light, freshness against the plan digest), `explainer_engine/videolane/scene.py`
(`storyboard_problems`, the pin), `explainer_engine/scripting/continuity.py` (CT-01..CT-14),
`explainer_engine/videolane/identity.py` (hero rows on the sheet before money), `explainer_engine/imagegen/turn_pack.py`
(the lettering heuristic at intake).

## Upstream sections: when to open which

| Need | Open in this folder's `SKILL.md` |
|---|---|
| The stage order from script to assembled page | "Quick reference" |
| How a shot list labels panels and arranges coverage | the paragraph after the quick reference |
| The six-panel walk-through as a model for a six-picture batch | "Worked example: a six-panel comic page" |
| The classic storyboard mistakes in one list | "Common mistakes" |

## Not used from upstream

Scenario's search, style LoRAs, `model_run`, `jobs_wait`, text-overlay and assembly tools, comic-page layout and lettering
(we letter by code on the video, not on a page), the Seedance storyboard sibling, and unattended "take the first result"
choices: the creator picks the look (rule 20) and approves the anchors.
