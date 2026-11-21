# P8: next (operator notes; only the MESSAGE block is sent)

Kind: PICTURES. Spec: section 3 row P8; Q3, Q12. Used only in `queue_on_drive` mode, which the T0 record switches on
(DRIVE READ OK and every T0 line `prompt: AS GIVEN`). The prompts and references are in the saved
`shot_queue.json`; this short message names the batch and repeats the three critical rules so that nothing depends on
Gemini remembering them. If the T0 record says `self_contained`, send P7 instead and never this.

Placeholders: `episode_id`, `sha8` (of the queue, as in P5), `batch_no`, `batch_total`, `n`, `picture_ids` (the
batch's ids, comma separated, in queue order), `era_line`, `drive_root`.

=====BEGIN MESSAGE=====
PICTURES | P8 next | episode {{episode_id}} | sha {{sha8}} | batch {{batch_no}} of {{batch_total}}

READ on Drive: {{drive_root}}/episodes/{{episode_id}}/shot_queue.json, and {{drive_root}}/rules/06_PICTURE_RULES.md if you can.

INPUT: batch {{batch_no}}. Make these {{n}} pictures, in this order: {{picture_ids}}. For each id, take its prompt and its reference list from the queue file, and attach the references from {{drive_root}}/episodes/{{episode_id}}/refs/ exactly as that entry lists them.

DO:
1. Work only on Flash. If the chat shows another model, write MODEL: <name> and stop.
2. Make the {{n}} pictures now with your direct image generation tool, one prompt per picture, as {{n}} separate 16:9 pictures in the listed order. No grid, collage or extra variant.
3. Write the report below.

RULES:
- Use only your direct image generation tool. Never draw a picture, card, placeholder or grid with Python or any other code.
- Send each prompt to the image tool word for word: add, cut or rewrite nothing.
- Attach the references exactly as listed for each picture, in that order. Image 1 gives the look only, never its people, pose or place; the others are our heroes and our place, kept exactly.
- No text, letters, numbers or writing-like marks in any picture. Every object fits this era: {{era_line}}
- Never repair or substitute. A picture not made is written NOT MADE with its reason.
- If the daily limit comes, stop: write NOT MADE: limit for every picture left, and never switch model or fall back to code.

ANSWER exactly in this form, after the pictures:
BATCH REPORT {{batch_no}}
1 | <picture id> | MADE | refs: <numbers> | prompt: AS GIVEN|CHANGED <how> | note: <one short line or ->
2 | <picture id> | NOT MADE | reason: <one short line>
MADE <n> of {{n}}
=====END MESSAGE=====
