# Shot continuity for generated keyframes: research notes (2026-10-25)

What a per-shot "continuity card" has to carry so that consecutive AI-generated keyframes (Qwen-Image-2.1 / Qwen-Image-Edit-2511 / Gemini image) and their LTX-2.5 animations cut together inside one scene.

Labels used on each claim:
- **[EST]** established practice, documented in a primary or standard source.
- **[VEND]** a vendor's own documentation or model card. It describes intended behaviour, not independently measured behaviour.
- **[HYP]** hypothesis or community practice: plausible, but not verified for our models.
- **[UNVERIFIED]** cited from general knowledge of a book whose text I could not open in this session.

Sources are numbered [S1]..[S22] and listed at the end.

---

## 1. Classic continuity: what is tracked per shot

### 1.1 Live action (script supervisor)
- **Physical match items.** The script supervisor tracks props, wardrobe, set dressing, hair and makeup so they match from shot to shot. They also record where the actors are, their screen direction, the key actions, the lens, the scene's axis (180-degree rule) and off-camera eyelines [S1, citing Miller, *Script Supervising and Film Continuity*, 3rd ed. 1999, pp. 7-9]. **[EST]**
- **Why the record is needed.** Scenes are shot out of order, so the supervisor has to make sure "the hair, makeup, costumes and even the lighting all match". The standard tool is a reference photo taken after the first take, kept together with written notes [S2]. This is exactly the role our reference images play. **[EST]**
- **Breakdown data per scene.** Scene number, location, a brief description of the action, time of day, INT/EXT, cast, extras, props and costumes [S2]. Pre-production also produces a one-line continuity synopsis per scene: time of day, story day and a summary [S1]. **[EST]**
- **Per-take technical data.** Take number, lens, f-stop, filter, running time, shot size (WA, MCU...) and screen-position abbreviations such as "CRBG" (camera right background). The author of [S2] adds a thumbnail sketch per slate. **[EST]**

### 1.2 Editing grammar (what makes a cut join)
- **The continuity system.** Continuity editing is built from four parts: the establishing shot, the 180-degree rule, the eyeline match and match on action [S3, S4]. **[EST]**
- **180-degree rule.** The camera stays on one side of the line between the subjects. To cross it on purpose, insert a neutral shot, cutaway or insert first [S3, S5]. **[EST]**
- **30-degree rule.** Between two shots of the same subject, change the camera angle by at least 30 degrees, or change shot size clearly. Otherwise the cut reads as a jump cut [S4, S6]. Sources differ on exact wording. **[EST]**
- **Eyeline match.** Character A looks off-screen, and the next shot shows what A looks at, placed where that look points [S3]. **[EST]**
- **Murch's "Rule of Six".** Murch ranks what a cut must preserve: emotion 51 %, story 23 %, rhythm 10 %, eye-trace 7 %, two-dimensional plane of the screen 5 %, three-dimensional space of the action 4 %. When something has to be sacrificed, start from the bottom of the list (*In the Blink of an Eye*, 2nd ed. 2001). I took this from secondary summaries [S7, S8]; I did not open the book. **[EST, figures via secondary sources]**
  - *Implication for us:* spatial continuity matters, but it is not sacred. A card should flag violations as REVIEW, not BLOCK, unless the story depends on the geography.
- **Dmytryk, *On Film Editing* (1984).** It teaches cutting on movement (match on action) and that a cut needs a reason. **[UNVERIFIED: from general knowledge, no page check this session.]**

### 1.3 2D animation specifically (layout, BG, model sheets)
The most useful primary source found is the Hanna-Barbera *Layout Notes* (H-B staff: Grosvenor, Takamoto, Singer et al., undated; PDF via animationmeat.com) [S9]. **[EST]** Its rules map almost one-to-one onto generated shots:

- **Continuity is everyone's job.** "CONTINUITY IS EXTREMELY IMPORTANT", and layout artists must catch storyboard errors "in screen direction, continuity, and bad cutting". Its example: cars that move right-to-left in Sc 28 seem to move left-to-right in Sc 29 because the camera crossed the "axis of action", and Sc 30 flips back. They call this "bad filmmaking" [S9, p. 7].
- **Hook-ups across a cut.** For a cut from one place to another, "the characters' positions in the car (e.g. who is driving) must be continuous between Sc 99 and Sc 100". The damage also has to match: "the hole in the barn door, if seen in both scenes, must match" [S9, p. 7]. Hook-ups are noted on the X-sheets and the storyboard [S9, p. 2].
  - *Implication:* position and state of anything that crosses a cut are explicit fields.
- **Where and when, on every BG.** Every background layout carries a where/when note, such as "English countryside / Day" or "Castle Hallway / Night". A detail BG names its establishing BG: "Match to BG 19" [S9, p. ~23].
  - *Implication:* this is our "master frame reference" field, invented decades before AI.
- **Character sizes.** Use the model sheet's standard sizes (standard, waist shot, close-up, long shot) whenever possible [S9, p. 22].
- **Eye direction in dialogue.** Avoid staging dialogue in profile, and keep good eye direction: characters "should be looking at each other or at what they are talking about" [S9, p. 22].
- **BG reuse and variety.** Reuse BGs; overlays and underlays can disguise reuse. New BGs should not be "so slightly different" that the viewer can't tell them apart [S9].
  - *Implication:* when a new angle is meant, it must look clearly new (this echoes the 30-degree rule).
- **The H-B reading list.** The notes send layout artists to Mascelli's *The Five C's of Cinematography* (1965) for continuity [S9, p. 7]. **[EST; Mascelli's text not opened]**
- **Model sheets.** They exist to keep characters consistent "from scene to scene" when many artists draw them [S10]. **[EST]**
- **Background keys.** The background stylist sets colour, style and mood. Key BGs or the establishing shot are painted first, and production BGs follow them [S11]. That is the colour key / master BG pattern. **[EST]**
- **Layout's job.** It sets camera angles, camera paths, lighting and shading, plus the characters' key poses [S12]. **[EST]**
- **Books not opened this session.** Glebas, *Directing the Story* (2009); Paez and Jew, *Prepare to Board!* (2013); Williams, *The Animator's Survival Kit* (2001). From general knowledge, the board books cover screen direction, the line, shot progression (wide-medium-close) and staging for clarity. **[UNVERIFIED]**

**Ranking for 2D (my synthesis, [HYP]).** These matter most because the viewer sees them instantly in flat, stylised art:
1. Character model: silhouette, colours and costume.
2. Screen direction, axis and left/right placement.
3. The BG match: the same landmarks, plus a colour key that fixes light and time.
4. Relative size.

Lens and f-stop matter less because 2D has no real optics. They matter more if the style uses depth of field.

---

## 2. Field lists of the classic documents

**Script supervisor's editor log / continuity sheet [S1, S2, S13]** **[EST]**
- Scene, setup and take; print/hold/NG; timecode or roll.
- Lens, f-stop, filter; running time.
- Shot size and description; screen direction of the movement; actor positions; key actions.
- Dialogue on or off camera; wardrobe, prop and hair notes; reference photo.
- Director's notes.

The lined script adds where each setup starts and stops, and the daily production report adds counts and times.

**Scene breakdown [S2]** **[EST]**
- Scene number; INT/EXT; location; time of day; story day.
- Action summary; cast, extras, props, costumes.

**Animation scene folder / layout [S9, S12, S14]** **[EST]**
- Scene number with a boxed short description; hook-up notes; CUT marks.
- X-sheet (exposure sheet: timing and camera instructions).
- Field size and field guides; camera moves (truck, pan, tilt).
- BG layout with its where/when note and "Match to BG nn"; overlays and underlays; held cels.
- Character key poses at model-sheet sizes.

(Pan and field limits are not relevant for us.)

---

## 3. AI consistency practice (2024-2026)

### 3.1 What the vendors say

**Qwen-Image-Edit-2509** [S15] **[VEND]**
- "Optimal performance is currently achieved with 1 to 3 input images".
- Supported combinations include "person + person", "person + product" and "person + scene".
- Native ControlNet support (depth, edge, keypoint).

**Qwen-Image-Edit-2511** [S16] **[VEND]**
- Claims "mitigate image drift", "improved character consistency" and multi-person fusion of two separate portraits into one group shot.
- Has built-in LoRAs for lighting and new viewpoints.
- Its example prompt places characters explicitly: "The magician bear is on the left, the alchemist bear is on the right, facing each other in the central park square."
- No input limit is stated; the card has no limitations section and no metrics.

**Qwen-Image-2.1** **[UNVERIFIED]**
- I could not reach the official card. Secondary write-ups [S17] say: one checkpoint for generation plus multi-reference editing, up to 10 reference images, released 2026-09-20, and a non-commercial licence (unlike the Apache-2.0 2511).
- **Check the licence before production use.**

**Gemini image models** (Gemini API docs, fetched 2026-10-25) [S18] **[VEND]**
- Reference limits by model:

  | Model | Character refs | Object refs | Style refs |
  |---|---|---|---|
  | `gemini-nano-banana-2.1`, `gemini-3.1-flash-image` | up to 4 | up to 10 | – |
  | `gemini-3-pro-image` | up to 5 | up to 6 (14 total) | up to 3 |
  | `gemini-2.5-flash-image` | – | best with up to 3 inputs | – |
  | `gemini-3.1-flash-lite-image` | – | – | – |

  Flash Lite is "not optimized for multiple reference inputs or multi-turn sequential editing".
- Recommended practice:
  - Iterate in a multi-turn conversation.
  - Edit with "Keep everything the same, but change ...". The docs' own edit example uses "Do not change any other elements of the image".
  - Be hyper-specific.
  - Use step-by-step instructions for complex scenes.
  - Use "semantic negative prompts": describe what is there instead of writing "no X".
  - Use cinematic camera language.

**FLUX (Black Forest Labs)** [S19] **[VEND]**
- FLUX 3 / FLUX.2 take up to 10 reference images.
- Refer to them by position: "image 1 is the first entry", and say each image's purpose.
- There is no seed in FLUX 3, so the same prompt varies between runs.
- Their multi-shot video schema keeps a **"Subject description — a fixed description held identically across shots, so identity stays consistent"**. Scene, light and depth of field go per shot. One global style-and-colour line ties the shots together.
- Kontext claims consistency "even after multiple edits".
- The Kontext paper (arXiv 2506.15742, June 2025) names "degradation in character consistency and stability across multiple turns" as the weakness of competing editors [S20].

**LTX-2 / 2.5** (Diffusers docs) [S21] **[VEND]**
- `LTX2ImageToVideoPipeline(image=...)` uses the still as the first frame.
- `LTX2ConditionPipeline` takes `LTX2VideoCondition(frames, index, strength)`. Index 0 is the first frame, -1 the last. The index is a *latent* index: an image placed at an inner index tends to look static over the frames it covers.
- `image_crf` re-compresses the conditioning image (default 18 for 2.5).
- Default length 121 frames at 24 fps (about 5 s). 2.5 can predict the duration itself.

**LTX prompting guide** (LTX Team, 2025-12-11) [S22] **[VEND]**
- Write one flowing paragraph of 4-8 sentences in the present tense.
- Cover the shot, the scene (light, palette, texture, atmosphere), the action in order, the characters (age, hair, clothing, distinguishing details), the camera move, and how subjects look *after* the move.
- Match the detail to shot scale: close-ups need more.

**FLUX image-to-video guide** [S19] **[VEND]**
- For start + end frames: "Keep the two frames related — same subject, scene, or camera setup". A wider gap means more unpredictability.

### 3.2 Reported failure modes and mitigations

| Failure | Evidence | Mitigation reported | Status |
|---|---|---|---|
| Chained-edit drift: artifacts, colour shift, untouched areas re-rendered | Banana100 (arXiv 2604.03400): artifacts accumulate over iterative Nano Banana Pro edits, and quality metrics miss it. FreqEdit (2512.01755): global colour shifts across rounds. Agent Banana (2602.09084): "prior-induced editing drift" of non-edited regions. A manga-panel study (2604.28185): earlier panels drift with no instruction. | Generate each shot fresh from the *original* references, not from the last output. Limit chain depth. Check colour against a key frame. | [EST in research; mitigation HYP] |
| Identity drift between shots | Vendor claims of fixes [S16, S20]; practitioner reports (Coverr, Croma blogs) | Model sheets as references. A fixed, identical character description. A role stated for each image ("image 2 is the face of X"). | [VEND/HYP] |
| Background reinvention | H-B "Match to BG 19" principle [S9]. Practitioners: generate anchor/establishing shots first and pass them as references for dependent shots (MindStudio; invideo FAQ) | Master BG frame as reference, plus a named landmark list | [HYP for AI] |
| Copying the reference composition (new shot = old framing) | No primary study found. The H-B "not so slightly different" rule and the 30-degree rule explain why it fails at the cut. | State the new shot size and angle explicitly, and that the reference is "for the place only, new camera position" | [HYP, unverified] |
| Extra or missing people | No primary study found | State the head count ("exactly two people") and run a vision check after generation | [HYP] |
| Hard keyframe jumps in video | KeyFrame-Compass (arXiv 2607.14202, 2026-07-15): trade-off between keyframe fidelity and natural motion; denser keyframes are worse | Keep first and last frames close (same setup); one change per clip | [EST for the trade-off] |
| Too many references | Qwen 2509: 1-3 optimal. Gemini: 4-5 characters with high fidelity. | Cap references per call; drop the least important | [VEND] |

---

## 4. Proposed per-shot continuity card

Design rules (my proposal, [HYP]):
1. Every field must be machine-checkable: an enum, an id, a number, or a yes/no a vision model answers on the finished keyframe.
2. The card describes the shot's *state*, not only its delta. The prompt is assembled from fixed blocks plus a "changes" block.
3. Identity text is copied verbatim from a registry, never re-written per shot [S19 "held identically"].

### A. Scene state (one scene sheet; the shot inherits it)
| Field | Check | Source |
|---|---|---|
| `scene_id`, `shot_id`, `order` | schema | S1, S9 (scene/setup numbering) |
| `location_id` + one-line "where / when" ("Castle hallway / Night") | must exist in the location registry | S9 ("English countryside / Day"), S2 |
| `story_day`, `time_of_day` (enum), `int_ext` | the same in every shot of the scene unless `time_jump` is set | S1, S2 |
| `weather`/`atmosphere` (enum: clear, rain, fog, snow, dust...) | the same across the scene; vision yes/no | S2, S22 (atmosphere) |
| `master_frame_id` (the establishing BG of the scene) | must be generated and approved before dependent shots | S9 ("Match to BG 19"), S11, MindStudio |

### B. Camera and axis
| Field | Check | Source |
|---|---|---|
| `shot_size` (enum ELS/LS/MS/MCU/CU/insert), restricted to the model sheet's standard sizes | enum; compare head height in the output | S2, S9 (size system) |
| `angle` (eye/low/high), `camera_side` (A/B of the axis) | `camera_side` the same as the previous shot unless `axis_cross_reason` ∈ {neutral shot, cutaway, insert, on-screen move} | S1, S3, S5, S9 |
| `axis` = the two entities that define the line (e.g. `hero↔king`) | must be set when two or more entities talk or move | S1, S3 |
| `angle_change_vs_prev` ≥ 30° **or** `shot_size` changes by at least one step | computed from the previous card; FAIL → jump-cut risk | S4, S6, S9 |
| `camera_move` (static/pan L/R/push in/pull out...) + `end_framing` | text; used in the LTX prompt | S21, S22 |

### C. Characters (one row per entity on screen)
| Field | Check | Source |
|---|---|---|
| `character_id` → registry with a model sheet / turnaround and a **verbatim** description | id exists; description string equals the registry | S10, S19, S16 |
| `screen_pos` (left/centre/right + fg/mid/bg) | vision check; the same as the previous shot on the same side of the axis | S9 (who is driving), S16 example |
| `facing` / `screen_direction` (L→R, R→L, toward/away) | consistent across the cut for continuous motion | S1, S9 (cars Sc 28-30) |
| `eyeline_target` (entity id or off-screen side) | the next shot shows the target on that side | S3, S9 (eye direction) |
| `costume_state` (variant id + damage/dirt/wet flags) | variant id in the registry; flags carried forward until a shot changes them | S1, S2 |
| `props_in_hand` [{prop_id, hand L/R, state}] | carried forward; a change needs an action in this or the previous shot | S1, S9 (hole in the barn door) |
| `expression` / `pose` (sheet reference) | expression-sheet id | S10, CLAUDE.md D-55 |
| `head_count` on screen (exact) | vision count = the card | [HYP] extra-people failure |

### D. Place and landmarks
| Field | Check | Source |
|---|---|---|
| `landmarks_visible` [{landmark_id, screen side}] | a subset of the location's landmark list; positions consistent with `camera_side` | S9, S12 |
| `set_state` changes (door open, fire lit, hole in wall) | carried forward like props | S9, S1 (set dressing) |

### E. Light, colour, time
| Field | Check | Source |
|---|---|---|
| `key_light_dir` (screen L/R/top/back) + `light_source` (sun, fire, window) | the same across the scene unless motivated; vision yes/no | S2 ("lighting all match"), S12 |
| `colour_key_id` (palette and mood of the scene) | mean hue/luma within tolerance of the master frame | S11, Gemini colour-drift papers |

### F. Delta vs the previous shot
| Field | Check | Source |
|---|---|---|
| `changes` = a list of {entity, field, from, to, cause} | every difference between consecutive cards must appear here; anything else is an error | S9 (hook-ups), S18 ("keep everything the same, but change...") |
| `hook_up` = the cut type (match on action / eyeline / cutaway / time cut) | enum | S3, S4, S9 |

### G. References (in order, capped)
| Field | Check | Source |
|---|---|---|
| `refs` ordered list: 1 = master frame of the place, 2..n = the model sheet of each character on screen (the most important first), last = the previous shot *only* if continuity of the exact state matters | count ≤ the model limit (Qwen Edit: 3 optimal; Gemini Flash: 4 characters / 10 objects; Pro: 5 high fidelity) | S15, S16, S18, S19 |
| `ref_roles` = a text role per ref ("image 1: the place, new camera angle; image 2: the face and costume of X") | every ref named in the prompt by position | S19 ("refer by position"), Croma blog |
| `derive_from_original` = true (never chain an edit off an edit beyond depth N) | chain depth ≤ N | S20, Banana100, FreqEdit |

### H. Prompt template (assembled, never free-written)
```
[STYLE LINE, global, verbatim]
Image 1 is the place: {location one-liner}; show it from {camera_side}, {shot_size}, {angle}.
Image {k} is {character name}: {verbatim registry description}, wearing {costume variant}{state flags}.
Exactly {head_count} people. {name} is {screen_pos}, facing {facing}, looking at {eyeline_target}, holding {prop+state}.
Visible: {landmarks with sides}. {time_of_day}, {weather}; key light from {key_light_dir} ({light_source}).
Change from previous shot: {changes}. Keep everything else the same.
```
For the LTX-2.5 clip, use one present-tense paragraph of 4-8 sentences: shot, scene light, action in order, camera move, and how the frame ends [S22]. Use first+last frames only when both come from the same setup [S19, KeyFrame-Compass].

### Post-generation checks (free, vision-model questions)
- Head count.
- Each character's identity vs the sheet.
- Left/right positions and facing.
- Landmark presence and side.
- Light direction.
- Colour-key distance to the master frame.
- Not a near-duplicate of the previous shot's framing (30-degree/size rule).

---

## 5. What I could not verify
- The text of Glebas, Paez & Jew, Williams, Dmytryk, Mascelli and Murch. Murch's percentages come from secondary summaries; the others are general knowledge only.
- The official Qwen-Image-2.1 card (reference limit, licence): secondary sources only.
- An official Black Forest Labs Kontext prompting guide (the old URL returns 404; current FLUX 3 docs used instead).
- Any controlled study of "copying the reference composition" or "extra people". The mitigations listed for these are hypotheses.
- A cell in the Gemini table conflicts with the docs' own example: the example sends 5 people to a model listed at 4.
- No source gives numeric tolerances (colour distance, how far a position may move). They must be calibrated on our own shots.

## Sources
- S1 Wikipedia, "Script supervisor" (cites Miller, *Script Supervising and Film Continuity*, Focal 1999), https://en.wikipedia.org/wiki/Script_supervisor (accessed 2026-10-25)
- S2 Vassar film dept., "What IS a script supervisor" handout (2016), https://pages.vassar.edu/film-majors/files/2016/03/script-super-docs.pdf
- S3 Wikipedia, "Continuity editing", https://en.wikipedia.org/wiki/Continuity_editing
- S4 MasterClass, "Continuity editing in film explained", https://www.masterclass.com/articles/continuity-editing-in-film-explained
- S5 FilmDaft, "What is the 180-degree rule", https://filmdaft.com/understanding-the-180-degree-rule-in-media/
- S6 Indiana Univ. C229 lecture week 9 (2024-25), https://jkmedia.sitehost.iu.edu/C229/Lecture9_sp25.docx
- S7 No Film School, "6 rules for good cutting according to Walter Murch" (2016-11), https://nofilmschool.com/2016/11/6-rules-good-cutting-according-oscar-winning-editor-walter-murch
- S8 StudioBinder, "Walter Murch rule of six", https://studiobinder.com/blog/walter-murch-rule-of-six
- S9 Hanna-Barbera staff, *H&B Layout Notes: A Helpful Guide to Layout* (undated; animationmeat.com PDF), https://eclass.aegean.gr/modules/document/file.php/511154/Theory/HB_LayoutNotes.pdf
- S10 Wikipedia, "Model sheet", https://en.wikipedia.org/wiki/Model_sheet
- S11 Wikipedia, "Background artist", https://en.wikipedia.org/wiki/Background_artist
- S12 Wikipedia, "Traditional animation" (layout), https://en.wikipedia.org/wiki/Traditional_animation
- S13 RoleCatcher, "Prepare film continuity reports", https://rolecatcher.com/en/skills/hard-skills/information-skills/documenting-and-recording-information/prepare-film-continuity-reports/
- S14 Wikipedia, "Exposure sheet", https://en.wikipedia.org/wiki/Exposure_sheet
- S15 Qwen, Qwen-Image-Edit-2509 model card, https://huggingface.co/Qwen/Qwen-Image-Edit-2509
- S16 Qwen, Qwen-Image-Edit-2511 model card, https://huggingface.co/Qwen/Qwen-Image-Edit-2511 ; Replicate readme (1-3 inputs), https://replicate.com/qwen/qwen-image-edit-2511
- S17 Secondary, Qwen-Image-2.1: https://braindetox.kr/en/posts/qwen_image_2_1_unified_generation_2026.html ; https://codersera.com/blog/how-to-run-qwen-image-2-1-locally-2026/
- S18 Google, Gemini API "Image generation" (limitations, best practices), https://ai.google.dev/gemini-api/docs/image-generation (fetched 2026-10-25)
- S19 Black Forest Labs docs: https://docs.bfl.ml/guides/prompting_unified_basics.md ; https://docs.bfl.ml/guides/prompting_video_text_to_video.md ; https://docs.bfl.ml/guides/prompting_video_image_to_video.md ; https://docs.bfl.ml/kontext/kontext_image_editing.md
- S20 Labs et al., "FLUX.1 Kontext" arXiv 2506.15742 (2025-06), https://arxiv.org/abs/2506.15742
- S21 Hugging Face Diffusers, LTX-2 pipelines, https://huggingface.co/docs/diffusers/api/pipelines/ltx2
- S22 LTX Team, "Prompting guide for LTX-2" (2025-12-11), https://ltx.io/model/model-blog/prompting-guide-for-ltx-2
- Drift papers: Banana100 https://arxiv.org/pdf/2604.03400 ; FreqEdit https://arxiv.org/pdf/2512.01755 ; Agent Banana https://arxiv.org/pdf/2602.09084 ; multi-panel drift https://arxiv.org/pdf/2604.28185 ; KeyFrame-Compass (2026-07-15) https://arxiv.org/abs/2607.14202
- Practitioner (HYP-grade): MindStudio https://www.mindstudio.ai/blog/storyboards-character-sheets-ai-video-generation ; invideo FAQ https://invideo.io/faq/how-do-you-maintain-consistent-lighting-and-character/ ; Croma https://www.croma.com/unboxed/how-to-use-google-nano-banana-pro-ai ; Coverr https://coverr.co/blog/nano-banana-pro-ai-image-character-consistency-2026
