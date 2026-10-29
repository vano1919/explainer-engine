# Creative style bible


**Since 2026-10-22** the current visual world is versioned in `explainer_engine/world/bible.json` ([WORLD_BIBLE](WORLD_BIBLE.md)); this document keeps tone, humour, typography and the hook framework.
**Status 2026-10-15: the Kit sections below are retired** (the creator rejected draft v0, D-04); the new direction is hand-drawn / doodle, explored in `assets/style_samples/`; on 2026-10-16 the creator chose the painted-illustration look of the two reference images (D-27). Tone, shape grammar, hooks and accessibility still apply; the mascot and palette sections are rewritten once the creator picks a doodle style. Colours live only in
`explainer_engine/design/palette.json` (D-22); the character parts only in `assets/characters/kit/kit_reference.svg`.

## Tone and humour
A knowledgeable friend showing you something neat: curious, warm, a little dry. Humour is situational and visual (Kit's
reactions, literal visual metaphors), at most one verbal joke per ~60 s, never at people's expense, never a false fact
for a laugh. No alarm, no false urgency, no fabricated stakes.

## Kit (original mascot, working name)
- A cardboard-box character: body 200 x 230 (1 : 1.15), corner radius 24 (12 % of the width); a lid whose opening is the
  signature **cutaway reveal** (the opening shows the thing being explained, never Kit's insides).
- Face: two oval eyes with pupils and eyebrows; the brows carry the emotion. Mouth: a resting mouth per expression or one
  of six speech mouths (rest, m-b-p, wide, mid, round, f-v) driven by phonemes (`explainer_engine/audio/visemes.py`).
- Limbs: thin round-capped lines, mitten hands (paper fill, ink stroke).
- Eight expressions (neutral, curious, surprised, smug, confused, delighted, worried, deadpan) are drawn on the sheet.
  Ten poses (stand, point left/right, shrug, lean-in, hold-prop, lid-open, peek-out, facepalm, wave-off) and the rig
  pivots are Phase 4 work; every pose is composed from the sheet's parts, never redrawn from scratch (D-04).
- Kit narrates: lip-synced when on screen, voice-over otherwise. Kit is never the answer object (that is coral).

## Shape grammar and drawing rules
Rounded rectangles = human-made things; circles and blobs = natural things; sharp triangles only for danger. Stroke 6 px
for characters and 4 px for props at 1080p, round caps and joins. Flat fills plus one shade; no gradients except a
background vignette. Every meaningful shape has an ink stroke and meaning never rests on colour alone (D-22): myth
checks pair green with a check icon and red with a cross icon; "evidence is mixed" is an amber badge with the words.

## Colour use (values: palette.json)
`ink` outlines and text; `paper` default background and label chips; `kit_card`/`kit_shadow` Kit; `answer_coral` the answer
or key object, one per shot; `mechanism_teal` arrows, flows and mechanism labels; `support_blue` secondary objects;
`true_green`/`false_red` myth checks; `uncertain_amber` uncertainty badge; `night` dark scenes and Short end cards;
`grey_mid` inactive or background props. Measured contrasts and the text rules are in the palette file and its test.

## Typography
Fredoka (titles, big labels) and Inter (labels, captions); both SIL Open Font License, recorded in the asset licence
register ([ASSET_SYSTEM](ASSET_SYSTEM.md)). Label text 40 px minimum at 1080p for long-form, 56 px for Shorts; at most
about 6 labels on screen; title cards at most 6 words.

## Backgrounds and scene continuity
A small set of recurring places (kitchen, shop, street, workshop, lab bench, night sky) built from reusable props.
Warm paper background by default; `night` for dark topics. One home place per scene; a cutaway to another place shows what the talk is about while it is said (KP-42,
[BP-112](SOURCED_RULES.md); the creator 2026-10-24). Props keep their size and colour across
scenes of an episode. Diagrams use `mechanism_teal` flows over simple shapes; real numbers are written, never implied.

## Hooks (D-07)
Since 2026-10-16 the hook, the shot grammar and the mood system (emotion, light, palette) are binding in
[UNIVERSAL_RULE_BASE](UNIVERSAL_RULE_BASE.md) (UR-01, UR-04 to UR-10); the notes below are the earlier spec.
First frame shows the object and Kit already acting; the first sentence is a concrete observation, not a greeting. Each
hook spec records: first frame, first visible action, first sentence, on-screen text, sound event, the question the viewer
perceives, time until subject and relevance are clear, the transition, the main failure risk, and where the promise is
paid. A fast first visual is a hypothesis to test, not a rule.

## Accessibility
Captions on every video; no flashing; colour is never the only carrier of meaning; reduced-motion variants are noted per
scene where practical ([STORYBOARD_SCHEMA](STORYBOARD_SCHEMA.md)).
