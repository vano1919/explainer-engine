# Overlay for `v-scenario-consistency`: Holding identity across pictures and clips (layer L10, stage G5 and G7)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from scenario-labs/skills, page `scenario-consistency` (MIT, commit `a14d061fe5`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel that does not use the Scenario platform: only the
methods are kept, carried out with the Gemini Task route, the turn-pack gates, the continuity cards and the video lane.
The upstream text, which drives Scenario's MCP tools, is this folder's `SKILL.md`; no Scenario MCP or API call
is ever made from this page. The folder has no `references/`.

## The ladder of durability, in our tools

Upstream ranks what holds a look from weakest to strongest. Here is the same ladder, with what we actually use:

| Upstream technique | Ours | Status |
|---|---|---|
| Baseline-plus-delta prompt | the cast registry text verbatim (GC-04, CT-02) + the place block word for word + one change clause | always, the floor |
| Reference images | the approved anchors: hero portrait and full body (R1, R2), place anchor; fixed order, within the cap (GC-02, GC-23) | always |
| Style reference | image 1 is the style anchor of the shot type (GC-01, GC-21); the series film named in words (rule 20) | always |
| Control map | an optional grey Blender layout of a hard staging (a lab aid; an attached image halves Gemini's output size, so it costs an upscale) | rare |
| Reference to video | LTX starts from the shot's own approved picture at frame 0 (image-to-video); the picture carries the look | every `video` shot |
| Seed reuse | the chat tool has no seed; an LTX seed only steps on a retry (`seed + SEED_STEP`) | not a consistency tool |
| Trained model | retired: the xworld style LoRA and its training are legacy (D-116, D-131); references come first and stay | not used |

## Procedure

1. **Write the baselines once.** Each hero's registry entry (age, build, skin, hair, face, garment, prop; HI-01, HI-02)
   and each place's block (where and when, left wall, right wall, floor, sky, camera height). Look at the approved anchor
   before writing: a shade you have not seen cannot be enumerated.
2. **Make and approve the anchors first** (GC-23): R1 portraits and places with the main style picture only; R2 full bodies
   with their own portrait. The creator approves by looking. Nothing of a scene is drawn before.
3. **Every scene picture is a fresh draw** from the anchors, never an edit of the shot before (CT-09; P-6 allows a
   same-shot continuation at most two hops from a fresh picture, compared with the master each time). The scene's master
   frame is drawn and approved first; coverage and inserts are drawn from it (CT-03, VL-04).
4. **Restate everything every time.** There is no memory between prompts or chats; "same as before" means nothing to the
   tool. One episode stays in one chat with its own anchors only (GC-10).
5. **State each reference's role** in the prompt, in attachment order: "image 1 is the style only; image 2 is the
   private; image 3 is the trench". Do not exceed the reference cap; extras stay unnamed and unanchored (CT-04, CT-05).
6. **A lasting change is a new anchor.** A greatcoat taken off from scene 4 on, a wound, snow on the parapet: draw it once
   as that hero's or place's change, have it approved, update the registry text, and anchor every later shot to the new
   one. A per-shot clause against the old anchor loses to the picture.
7. **Write the continuity card** for each shot (`continuity_card/1`, CT-01..CT-14; stage page `shot-continuity-writer`):
   positions, facing, eyeline, props, landmarks, light, and every change with its cause. The keyframe prompt is assembled
   by code from it: `python -m explainer_engine.scripting.continuity prompts <cards.json>`.
8. **Into video.** The clip's prompt names the action, not the look (skill `v-visual-skills-video`); re-describing the hero
   in motion words invites a second person or a new face.
9. **Sweep the whole clip, not its ends.** Drift often fades in mid-shot. Check identity on frames through the clip and
   across each cut (`explainer_engine/videolane/identity.py`: costume palette between shots, faces by SFace against the
   references, the card questions for the contact sheet). A loose part moving with the action (a coat hem, a sling) is
   animation; a part gained, lost, recoloured or reshaped is drift.

## Mistakes we will not repeat

- Chaining output to output (the legacy era's drift and the 2026-11-12 helmet change across cut 1): every shot from the
  untouched master and anchors.
- Attaching an outside sample: its people leak into every era (the 2026-11-11 sample; GC-01).
- Passing a turnaround or expression sheet as a reference slot: sheets are for review and filing (invariant 6); slots take
  single approved views.
- Fixing drift with a longer adjective list: tighten the verbatim baseline and the place block, or redraw from the master.
- Several heroes co-generated past the cap: their faces merge. Reduce the named cast in frame, turn or shrink the extra
  face, or split the beat into two shots.
- Rebuilding a hero from scratch because one picture failed (invariant 6). Redraw the shot, keep the hero.

## Checks in code (SK-2)

`explainer_engine/imagegen/turn_pack.py` (`check_prompt`: registry text present, style clause, keep clause; intake and the
identity hook, GC-13), `explainer_engine/gemini_task/queue.py` (attachment order, cap, R1 before R2),
`explainer_engine/scripting/continuity.py` (cards, CT rules, `compose_prompt`, `vision_questions`),
`explainer_engine/videolane/storyboard.py` (coverage stays in the master's place and light, VL-10),
`explainer_engine/videolane/identity.py` and `explainer_engine/qa/face_points.py` (faces and costume; NOT MEASURED is a
REVIEW, never a pass), `explainer_engine/training/video_qa.py` (hero palette distance against BP-166).

## Upstream sections: when to open which

| Need | Open in this folder's `SKILL.md` |
|---|---|
| The baseline-plus-delta discipline in full | "The baseline-plus-delta prompt" |
| Why a style reference holds rendering but not a subject | "Locking a style without a subject" |
| When a layout or pose map helps and when it locks the very thing to change | "Locking structure with a control map" |
| Judging identity frame by frame through a clip | "Carrying identity into video" |
| When references stop scaling (background to D-131's no-training choice) | "When references stop scaling" |

## Not used from upstream

Every Scenario tool and id (`model_run`, `asset_detect`, `recommend`, the frame extractor, collections, style ids and
credit pricing), uploads to Scenario, control-strength numbers for a ControlNet we do not run, model training, and the
sprite-sheet lane.
