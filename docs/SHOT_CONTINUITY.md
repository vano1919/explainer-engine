# Shot continuity cards (CC-)

How the shots of one scene are made to cut together. ვანო decided this on 2026-10-25 (20:11 and 20:17 Tbilisi). The base
picture models already know how shots join, so we do not train continuity. We train only the style
([LORA_TRAINING](LORA_TRAINING.md) LT-69). For continuity, we test which prompts and references work best. The agent that
writes the shots has an output format standardised on research.

- Decision: [D-75](DECISIONS_AND_OPEN_QUESTIONS.md).
- Research with 22 sources: [research/SHOT_CONTINUITY_2026-10-25.md](research/SHOT_CONTINUITY_2026-10-25.md).
- Code: `explainer_engine/scripting/continuity.py`; schema `explainer_engine/schemas/continuity_card.schema.json`
  (`continuity_card/1`).
- Example: `examples/continuity/napoleon_tent.json`. Test: `tests/unit/test_continuity.py`.
- Agent: `shot-continuity-writer` (`.claude/agents/`).

```powershell
.venv\Scripts\python -m explainer_engine.scripting.continuity check <cards.json>
.venv\Scripts\python -m explainer_engine.scripting.continuity prompts <cards.json> --out prompts.json
```

## Where the format comes from

The card is a script supervisor's continuity sheet and a Hanna-Barbera layout folder, written as data:
- **Every background carries where/when** ("Castle hallway / Night"), and a detail shot names its establishing BG
  ("Match to BG 19"). In the card, that is `where_when` and the master frame.
- **Hook-ups across a cut**: who is driving, and the hole in the barn door matches. In the card, that is the whole
  per-person state plus the `changes` list.
- **Editing grammar**: the 180° axis, the 30° rule, the eyeline match, match on action.
- **Vendor docs**:
  - Qwen-Edit works best with 1-3 input images.
  - Gemini has per-model reference limits, and recommends "keep everything the same, but change...".
  - FLUX: refer to images by position, and keep the subject description identical across shots.
- **Drift papers**: chained edits drift, so each shot is drawn fresh from the original references.

Card design rules:
1. A card holds the shot's full **state**, not only its delta.
2. Identity text comes **verbatim** from the cast registry.
3. Every field is machine-checkable: an enum, an id, a number, or a question a vision model answers about the finished
   picture.
4. Prompts are assembled by code, never written by hand.

## The card

One file per scene. The scene part:
- `location`: id, `where_when`, INT/EXT, time of day, weather, landmarks, `master_frame`.
- `light`: key light direction, source, colour key.
- `cast`: per person a cast-tag name, a verbatim description, a model sheet and costume variants.
- `style_line`.
- `model`: the picture model, which sets the reference cap.

One card per shot:
- `shot_size`, `angle`, `camera_side` (A/B of the axis), `axis`, `axis_cross_reason`, `angle_change_deg`.
- `hook_up`, `camera_move`, `end_framing`.
- `head_count` and `extras`.
- `characters`: position, depth, facing, eyeline, costume, flags, props, expression, action.
- `landmarks` with their screen side, and `set_state`.
- Overrides of time, weather or light.
- `changes`: entity, field, from, to, cause.
- `refs`, in order with roles, plus `derive_from` and `chain_depth`.

## Rules

| ID | Rule | Kind | Enforced by |
|---|---|---|---|
| CC-01 | The cards follow `continuity_card/1`. `where_when` has the BG-note shape "place / time", and shot ids are unique | house + H-B Layout Notes | `schema_findings` FAIL |
| CC-02 | Every person on screen is in the cast registry, and every costume is one of the person's registered variants. The prompt copies the description verbatim; there is no per-shot description field | source (FLUX "held identically across shots"; model sheets) | FAIL |
| CC-03 | Image 1 of every shot except the master is the scene's master frame (role `place`). The master is drawn and approved first | source (H-B "Match to BG 19"; anchor-shot practice) | FAIL |
| CC-04 | `head_count` = named people + `extras`; the prompt says "Exactly N people" | hypothesis (extra people were our most common failure, KG-27) | FAIL |
| CC-05 | References stay within the model's cap (`MODEL_REFS`). Every character reference is that person's model sheet. Every person on screen has a sheet among the references; a missing sheet is a REVIEW when the cap is full. The previous shot, when used, is the last reference | vendor (Qwen 1-3; Gemini 4-5 people) | FAIL / REVIEW |
| CC-06 | Two or more people on screen need an axis. The camera stays on its side unless a reason is given (neutral shot, cutaway, insert, on-screen move) | source (180° rule; H-B Sc 28-30) | FAIL / REVIEW |
| CC-07 | Two consecutive shots of the same people change size by at least one step or the angle by at least 30°, unless the cut is a time cut | source (30° rule; H-B "not so slightly different") | FAIL |
| CC-08 | Every state difference from the previous shot appears in `changes` with a cause. This covers time, weather, light, set state, and each person's costume, flags and props; position and facing are compared only on the same camera side and size. A listed change that did not happen is a REVIEW | source (hook-ups; script supervisor) | FAIL / REVIEW |
| CC-09 | A shot is drawn fresh from the original references, at most `MAX_CHAIN` (1) edit deep, and `derive_from` names an earlier shot | source (Banana100, FreqEdit, Agent Banana drift) | FAIL |
| CC-10 | A shot shows only landmarks from its location's list | source (H-B BG continuity) | FAIL |
| CC-11 | An eyeline points at a person in the cast or off-screen (left, right, down, up). A person who looks at someone on screen faces them | source (eyeline match; H-B eye direction) | FAIL / REVIEW |
| CC-12 | On a match-on-action cut on the same camera side, a moving person keeps their screen direction | source (H-B Sc 28-30; match on action) | FAIL |
| CC-13 | The keyframe prompt is assembled by `compose_prompt`, in a fixed order: style line, images by position with their role, size and angle, head count, each person (verbatim identity, costume, place, facing, eyeline, props, action), landmarks with sides, set state, time and light, changes, "Keep everything else the same" | source (research section 4 H) | code |
| CC-14 | Every finished keyframe is asked the card's questions: head count, each person's side, facing, props and sheet match, the landmarks, light direction, and a new framing versus the previous shot. The answers feed the blind check's second look ([KEYFRAME_GATE](KEYFRAME_GATE.md) KG-) | house | `vision_questions` |

Video clips keep the prompt rules of [SHOT_PROMPTS](SHOT_PROMPTS.md) (KP-). LTX takes first and last frames only from the
same setup.

## What we test (not train)

Continuity is tested on one scene of four shots, drawn with and without the style LoRA. The test also checks that the
style LoRA does not break what the base model already does. Variables, one at a time:

1. **Number of references:** master only; master plus sheets (default); plus the previous shot.
2. **Order of references:** place first (default) or people first.
3. **Identity text:** verbatim registry description (default) or a short cast tag only.
4. **Change wording:** the full state alone, or the full state plus "Change from the previous shot: ... Keep everything
   else the same."
5. **Drawing:** fresh from the references (default) or edited from the previous shot (chain depth 1).

ვანო rates every picture by eye on the four-level scale; the CC-14 questions are scored next to his vote. The winner
becomes the default of `compose_prompt`. No numeric tolerance (colour distance, position drift) is set before it is
measured on our own shots.
