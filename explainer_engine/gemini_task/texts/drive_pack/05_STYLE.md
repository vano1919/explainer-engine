# The look of the channel

Sources: `config/visual_style_presets.json`, preset `{{style_preset_id}}` (every quoted sentence below is copied from
it at export; the preset wins); `docs/GEMINI_CONSISTENCY_RULES.md` (GC-01, GC-03, GC-11, GC-18, GC-21, GC-22).
Decided by the creator on 2026-11-12: one picture, `main_style_5709.png`, is the main style of the whole system.

## In one paragraph

A painted, cinematic storybook world at golden hour or by firelight: a low sun or a fire puts a glowing rim of light on
hair and skin, the air has a soft haze, warm lights stand against cooler green and stone, and everything is made by
hand and can almost be touched. The people are attractive, believable adults with warm, gentle faces, a little
idealised, like a painting from a high-end animated feature. It is not a camera picture and it is not a plastic 3D
cartoon. It sits between the two, and that place is narrow: most failures fall off one side or the other.

## The sentences (always word for word)

**Style sentence**, the first words of every picture prompt:

> {{style_sentence}}

**Face sentence**, in every prompt with people:

> {{face_sentence}}

**Style-reference clause**, in every prompt that attaches a style picture:

> {{style_reference_clause}}

## Words that must never reach the image tool

{{never_words}}

Why: in the test rounds of 2026-11-12 these words made the tool repaint the whole request as a camera picture, and the
painted look was lost. They are refused in every prompt outside a "never" phrase. Describe the painted look with the
sentences above instead. The reverse failure has its own words: nothing that asks for a cartoon, big eyes, a round or
cute face, or a 3D-animation character (GC-11).

## The episode's era line

The style sentence names no era, no light source and no material, so it fits any age. Each episode adds one sentence
that says which world this is. It is in every picture prompt after the scene, word for word (GC-22):

> {{era_line}}

Everything in a picture comes from that sentence: the light sources it lists are the only ones allowed, and an object
that does not fit the era is a finding (an oil lantern in Egypt, a glass pane in the Stone Age).

## Always in the picture

{{always_list}}

## Never in the picture

{{negative}}

## The style anchors: one per kind of shot

The first reference of every picture is a style anchor. It gives the look and nothing else. Which anchor depends on the
kind of shot, because a wide landscape and a firelit face show the style differently:

{{style_pack_table}}

A reference picture of a hero or a place uses the main style picture as its style anchor.

## Two rules that the anchors make necessary

**Identity (GC-01).** {{identity_rule}}
A style anchor may show people. They are never our heroes. If the people of an anchor appear in a new picture, that
picture is rejected, however good it looks.

**Era.** {{era_rule}}
Each episode names its era and its light sources in the batch message. A glass lantern in the Stone Age is the kind of
miss this rule exists for.

## How to judge a finished picture against the look

1. Light: a low sun or a fire, a warm rim on the figures, haze and depth. Flat midday light fails.
2. Paint: visible painterly handling and rich detail. A camera picture fails; a smooth plastic render fails.
3. Faces: believable adults with skin texture and a quiet, readable emotion. Round cartoon faces fail; so do the faces
   of the style anchor.
4. Materials: handmade and of the era.
5. No text, letters, numbers or marks that look like writing anywhere.
