# Storyboard schema (contract v1) and timing contract

Canonical home of the storyboard contract. The authoritative machine form is `explainer_engine/schemas/storyboard.schema.json`
(written in Phase 3 from this document; it then wins on any disagreement and this page is updated to match). The
renderer executes only what this schema lists; an unknown field, enum value, reference or time is a `ContractError`,
never a silent no-op, and no phase may relax the schema to make a render pass (invariant 7 in `CLAUDE.md`).

## Document shape
```json
{
  "schema": "explainer.storyboard", "version": 1,
  "episode_id": "onion", "kind": "long|short",
  "canvas": {"width": 1920, "height": 1080, "fps": 30},
  "timing_source": {"words": "audio.words.json", "audio": "narration.wav"},
  "sections": [{"id": "SEC1", "role": "hook|context|mechanism|escalation|example|payoff", "title": "..."}],
  "scenes": [ ...scene... ]
}
```
## Scene and shot
| Field | Meaning | Rule |
|---|---|---|
| `scene.id` | `S01`... stable | unique, ordered |
| `scene.section_id` | section it belongs to | must exist |
| `scene.purpose` | what the viewer should understand | non-empty |
| `scene.narration` | `{segment_ids: [...], audio_ref}` | segment ids exist in the script; audio_ref resolves |
| `scene.start`, `scene.end` | anchors (see below) | `end` after `start`; scenes do not overlap and leave no unplanned gap |
| `scene.background` | asset id | exists in the asset manifest |
| `scene.camera` | `{x, y, zoom}` start pose + `moves` (PanCamera, ZoomCamera) | inside canvas bounds |
| `scene.shots[]` | one or more shots | see below |
| `scene.music` | music state id or `none` | exists in the audio plan |
| `scene.transition_out` | `cut | wipe | lid_reveal` | max one per scene |
| `scene.fallback` | `{asset, instruction}` when an asset is missing | required for any non-reusable asset |
| `scene.accessibility` | alt description, reduced-motion note | alt description required |
| `scene.qa` | required checks (for example `contrast`, `label_hold`) | names exist in QA_SPECIFICATION |
| `scene.source_refs` | claim ids shown as facts (numbers, diagrams) | claims exist and are verified |
| `scene.renderer_notes` | free text for the renderer | never interpreted by code |

`shot`: `id`, `start`, `end` (anchors), `composition` (named layout: `centre`, `left_right`, `grid3`, `full_diagram`,
vertical variants for 9:16), `entities[]` (`{id, asset, x, y, scale, z}`), `actions[]`, `text[]`, `captions` (reference
to the caption track), `sfx[]` (audio-event ids), `reuse` (`reused|new`).

## Anchors: timing comes from narration
An anchor is `{"word": "w_0123", "offset_ms": -200}` (a word id from the words file), `{"scene_start": true, "offset_ms":
300}`, `{"prev_end": true, "offset_ms": 0}`, or `{"time_ms": 12000}` for narration-free passages only. Phase 5 resolves
anchors to frames from the real word times; a scene longer than its narration holds, a scene shorter than its narration
is a validation error (narration is never cut to fit). SFX inside the first 150 ms of a stressed word needs
`purpose: sync`. Vertical Shorts have their own storyboard with their own anchors.

## Animation vocabulary (v1, finite)
| Action | Parameters | Notes |
|---|---|---|
| Move | entity, to (x,y), duration, easing | |
| Scale | entity, to, duration, easing | |
| Rotate | entity, to (deg), pivot, duration | |
| Fade | entity, to (0-1), duration | |
| Reveal | entity, style `pop|wipe|draw` | draw requires a path asset |
| Draw | entity (path), duration | stroke-dash draw-on |
| Bounce | entity, height, count | |
| Shake | entity, amplitude, duration | seeded, deterministic |
| FollowPath | entity, path, duration | |
| ChangeExpression | entity (Kit), expression | one of the eight |
| ChangePose | entity (Kit), pose | from the pose set (Phase 4) |
| LipSync | entity (Kit), source `words|loudness` | mouth from phonemes (visemes.py) |
| LidOpen | entity (Kit), duration | the reveal action |
| SwapProp | entity, asset | same-size variants only |
| PanCamera / ZoomCamera | to, duration, easing | |
| Highlight | entity, token (palette), duration | outline pulse; never colour alone |
| Count | entity (text), from, to, duration | numbers narrated must match |
| Label | text, anchor point, hold | hold >= 1.5 s + 0.3 s per word (P-71) |

Easing enum: `linear, in_out_cubic, out_back, in_cubic, out_cubic`. Each action's `at` is an anchor; durations are in
frames or ms and converted at 30 fps. Idle motion (blinks, sway) is generated, seeded and not listed.

## Validation rules (all enforced before any render)
Types, required fields and enums; unique stable ids; every reference resolves (asset, claim, segment, audio event,
music state); times are monotonic and inside the audio duration; no overlapping shots within a scene; at most three
simultaneous movers and six labels (REVIEW above); label holds meet P-71; every on-screen number has a claim; fallback
present for non-reusable assets; Kit actions only from the vocabulary; vertical storyboards are re-composed (a check
rejects a storyboard that is only a crop: entity positions must differ from the 16:9 version).

## Minimal valid scene (fixture shape)
```json
{"id": "S03", "section_id": "SEC2", "purpose": "Cutting breaks the cell and two things meet",
 "narration": {"segment_ids": ["N-007", "N-008"], "audio_ref": "narration.wav"},
 "start": {"word": "w_0141", "offset_ms": -150}, "end": {"word": "w_0188", "offset_ms": 400},
 "background": "bg.kitchen", "music": "light_bed", "transition_out": "cut",
 "shots": [{"id": "S03a", "start": {"scene_start": true}, "end": {"word": "w_0188", "offset_ms": 400},
   "composition": "centre",
   "entities": [{"id": "e_knife", "asset": "prop.knife", "x": 420, "y": 300, "scale": 1.0, "z": 3},
                {"id": "e_cell", "asset": "diagram.onion_cell", "x": 960, "y": 540, "scale": 1.4, "z": 1}],
   "actions": [{"action": "Move", "entity": "e_knife", "to": {"x": 900, "y": 540}, "at": {"word": "w_0141"}, "duration_ms": 350, "easing": "in_cubic"},
               {"action": "Shake", "entity": "e_cell", "amplitude": 6, "at": {"word": "w_0143"}, "duration_ms": 300}],
   "text": [], "sfx": ["sfx.knife_chop@w_0143"], "reuse": "new"}],
 "fallback": {"asset": "bg.plain_paper", "instruction": "use the plain paper background and keep the actions"},
 "accessibility": {"alt": "A knife cuts into an onion cell", "reduced_motion": "hold final pose, no shake"},
 "qa": ["contrast", "label_hold"], "source_refs": ["C-003"]}
```
