# Prompt clauses of the Gemini Task route (A1b, 2026-11-12; operator and code notes, nothing here is sent as written)

Spec: `A1_GEMINI_TEXTS_SPEC.md` (project files, `v4_3_plan_2026-11-12/`), decisions Q2, Q4-Q7, Q10, Q11.
The engine builds every picture prompt from these clauses (Q2: Gemini only passes the prompt on), runs the never-words
and text-words gates of `imagegen/turn_pack.check_prompt` on the assembled prompt, and puts it into a message's
`{{picture_blocks}}`. Each clause sits between `=====BEGIN CLAUSE <name>=====` and `=====END CLAUSE=====`; the exporter
reads them by name (A2 replaces `ANCHOR_CLAUSE_CHAR`, `ANCHOR_CLAUSE_PLACE` and `KEEP_CLAUSE` with them).

## Assembly order (one prompt, one paragraph, single spaces between parts)

1. the preset's `style_sentence` (GC-03);
2. the preset's `face_sentence`, when the picture has people (GC-11);
3. the preset's `style_reference_clause` (every picture: image 1 is always a style picture, Q4);
4. `keep_scene` for a scene picture, `keep_full_body` for a full-body reference (nothing for anchors, portraits, places);
5. the subject: an anchor clause (T0), `portrait`, `full_body` or `place` with the hero's or place's verbatim text
   (GC-04), or the shot's own description from the video script;
6. the episode's `era_line` (Q6), verbatim;
7. `tail`.

A redo prompt (P10) is the original prompt unchanged plus ONE correction sentence after `tail` (Q11).

## The picture block (how `{{picture_blocks}}` is rendered, one block per picture, a blank line between blocks)

```
PICTURE <k> of <n> | id <picture id> | save as <target file name>
REFERENCES, in this order: 1 = <file> (style), 2 = <file> (<hero id or place id>), ...
PROMPT: <the assembled prompt, one paragraph>
```

A redo block adds `REPLACES: <the earlier file name>` after the first line. "Image 1" inside a prompt always means
reference 1 of that block (Q10).

## Shared clauses

=====BEGIN CLAUSE keep_scene=====
Keep the exact faces, hair, costumes, props and designs of the reference images after image 1; only the pose, the action, the camera and the light change.
=====END CLAUSE=====

=====BEGIN CLAUSE keep_full_body=====
Image 2 is this person's approved portrait: keep exactly that face, hair, skin, age and costume.
=====END CLAUSE=====

=====BEGIN CLAUSE portrait=====
Chest-up portrait of {{hero_text}}, the face turned slightly toward us and clearly lit by soft warm light, a calm friendly expression, a quiet softly blurred backdrop of the same world.
=====END CLAUSE=====

=====BEGIN CLAUSE full_body=====
Full-length view of {{hero_text}}, standing at ease and facing us, the whole costume, footwear and props in view from head to feet, a quiet softly blurred backdrop of the same world.
=====END CLAUSE=====

=====BEGIN CLAUSE place=====
Establishing view of {{place_text}}, with no people in it, in the light of its usual time of day.
=====END CLAUSE=====

=====BEGIN CLAUSE tail=====
One single 16:9 picture. No text, letters, numbers or marks that look like writing anywhere in it.
=====END CLAUSE=====

## The T0 anchor candidates (spec section 3, row T0; Q5)

B2 replaces B (glass lantern), C3 replaces C/C2 (resembled the main style couple), D2 replaces D (map with writing-like
marks); E, F, G are new shot types. Each uses only the main style picture as reference 1. People are chosen to differ
from the main style couple (a young man and woman): other ages, builds and hair, so a leak is easy to see. The close
and action anchors (B2, C3, E) are compared with the main style couple before the creator's pick (Q5); A stays as it is.

=====BEGIN CLAUSE t0_B2=====
Firelit close-up of a grey-haired woman in her fifties with short cropped hair and a lined face, at night, one side of her face lit by a small fire just below the frame and the other side in deep warm shadow, her eyes fixed on something beyond us, quietly worried. A few embers drift past. The fire is the only light.
=====END CLAUSE=====

=====BEGIN CLAUSE t0_C3=====
Action shot, medium-wide: three young men haul a heavy wooden sled up a muddy slope at sunset, leaning hard into the ropes, mud flying from their feet. The low sun behind them puts a bright rim on their arms and hair, with dust hanging in the warm air.
=====END CLAUSE=====

=====BEGIN CLAUSE t0_D2=====
Extreme close-up of two weathered hands cupping a small glowing ember over a nest of dry grass, a thin curl of smoke rising, the rest of the frame in soft warm darkness. No map, no marks, no face.
=====END CLAUSE=====

=====BEGIN CLAUSE t0_E=====
Medium shot of an old woman with long white braids and a broad young man with a shaved head sitting across a small fire at night, mid-argument: she leans in and points at him, and he looks back unconvinced with his arms folded. The fire lights them from below and rims their hair, with deep blue night behind them.
=====END CLAUSE=====

=====BEGIN CLAUSE t0_F=====
Wide night view of a few dwellings at the edge of a forest under a full moon, cool blue moonlight on the roofs and the trees, thin mist between the trunks, and one tiny figure carrying a burning torch along the path, the torch the only warm light.
=====END CLAUSE=====

=====BEGIN CLAUSE t0_G=====
Medium-wide shot of a group of seven people walking in a line along a ridge at dusk, carrying bundles and long poles, seen from a little below, the last sunlight behind them turning their outlines gold and a soft haze filling the valley beneath.
=====END CLAUSE=====
