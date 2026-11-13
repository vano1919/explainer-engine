# The look of the channel

Sources: `config/visual_style_presets.json`, preset `crossworld_main_style_v1` (every quoted sentence below is copied from
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

> Painterly cinematic storybook illustration with rich detail: a warm golden-hour world, low sun or firelight as a glowing rim light on hair and skin, soft luminous haze, a sky of warm gold, peach and rose melting into soft violet, deep warm shadows, glowing points of warm light against cooler green and stone, tactile handmade materials, a cosy, romantic, adventurous mood.

**Face sentence**, in every prompt with people:

> People are attractive, believable adult humans with real skin texture and warm, gentle, expressive faces, slightly idealised and softly stylised like a high-end animated feature painting, never a plastic 3D-render face, never a cartoon nose or oversized eyes.

**Style-reference clause**, in every prompt that attaches a style picture:

> Use image 1 only as the visual style; do not copy its people, their pose or its place.

## Words that must never reach the image tool

- photograph
- photo
- natural
- naturalistic
- candid
- realistic
- 3D render

Why: in the test rounds of 2026-11-12 these words made the tool repaint the whole request as a camera picture, and the
painted look was lost. They are refused in every prompt outside a "never" phrase. Describe the painted look with the
sentences above instead. The reverse failure has its own words: nothing that asks for a cartoon, big eyes, a round or
cute face, or a 3D-animation character (GC-11).

## The episode's era line

The style sentence names no era, no light source and no material, so it fits any age. Each episode adds one sentence
that says which world this is. It is in every picture prompt after the scene, word for word (GC-22):

> The world is the Late Pleistocene of 74,000 BCE in Africa and Asia: the only light sources are hearth fires, torches, glowing embers, the low sun and the glow of the eruption, and everything is made of hide, wood, bone, stone and plant fibre.

Everything in a picture comes from that sentence: the light sources it lists are the only ones allowed, and an object
that does not fit the era is a finding (an oil lantern in Egypt, a glass pane in the Stone Age).

## Always in the picture

- golden hour or firelight
- warm rim light
- soft haze and depth
- one glowing warm light source in frame
- tactile handmade textures
- people interact with each other or the place

## Never in the picture

text, letters, logos, watermark, plastic 3D-render skin, cartoon proportions, oversized eyes, modern objects of another era, harsh flat daylight, documentary look

## The style anchors: one per kind of shot

The first reference of every picture is a style anchor. It gives the look and nothing else. Which anchor depends on the
kind of shot, because a wide landscape and a firelit face show the style differently:

| Type | Shot | Anchor file on Drive | sha256 | Status |
|---|---|---|---|---|
| main | style anchors, hero portraits and full bodies, places | `main_style_5709.png` | `db719b00bdfacc04` | approved |
| D | special moment: hands and objects, no face | `style_D.jpg` | - | candidate |
| C | action with people, medium-wide | `style_C.jpg` | - | candidate |
| F | night exterior: moon and one torch | `style_F.jpg` | - | candidate |
| A | wide view: tiny figures, the place carries the frame | `style_A.jpg` | - | candidate |
| B | firelit close-up of a face | `style_B.jpg` | - | candidate |
| G | a group of three or more, medium-wide at dusk | `style_G.jpg` | - | candidate |
| E | people talking or working, medium | `style_E.jpg` | - | candidate |

Only an anchor whose status is approved is ever attached; until then its shots wait.

A reference picture of a hero or a place uses the main style picture as its style anchor.

## Two rules that the anchors make necessary

**Identity (GC-01).** The reference's two people, their faces, pose and clothes are NEVER reused; each picture states: 'Use image 1 only as the visual style; do not copy its people, their pose or its place.' Our heroes' faces come from their own anchor portraits.
A style anchor may show people. They are never our heroes. If the people of an anchor appear in a new picture, that
picture is rejected, however good it looks.

**Era.** Every object must fit the episode's era (v17 put an oil lantern in Ancient Egypt): name the era's light source (hearth, oil lamp, torch) instead of 'lantern'.
Each episode names its era and its light sources in the batch message. A glass lantern in the Stone Age is the kind of
miss this rule exists for.

## How to judge a finished picture against the look

1. Light: a low sun or a fire, a warm rim on the figures, haze and depth. Flat midday light fails.
2. Paint: visible painterly handling and rich detail. A camera picture fails; a smooth plastic render fails.
3. Faces: believable adults with skin texture and a quiet, readable emotion. Round cartoon faces fail; so do the faces
   of the style anchor.
4. Materials: handmade and of the era.
5. No text, letters, numbers or marks that look like writing anywhere.
