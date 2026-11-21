# P9: resume after the limit (operator notes; only the MESSAGE block is sent)

Kind: PICTURES. Spec: section 3 row P9; Q12; GC-27. Sent the next day (the chat's picture limit resets daily), in the
episode's one chat, for the pictures of a batch that were `NOT MADE: limit`. Same shape as P7 for the remainder: the
blocks are the original blocks of the missing pictures, unchanged, and the attachments are the union of their
references in the order of the ATTACHED line. The batch keeps its number; the report counts only the pictures sent now.
Claude takes the first missing id from the report, never from memory.

Placeholders: `episode_id`, `sha8` (of the remaining blocks), `batch_no`, `batch_total`, `n` (pictures left),
`first_missing_id`, `era_line`, `attached_list`, `picture_blocks`, `drive_root`.

=====BEGIN MESSAGE=====
PICTURES | P9 resume | episode {{episode_id}} | sha {{sha8}} | batch {{batch_no}} of {{batch_total}}, from {{first_missing_id}}

READ on Drive, if you can: {{drive_root}}/rules/06_PICTURE_RULES.md. Everything this batch needs is in this message; nothing depends on earlier answers.

INPUT: yesterday's limit stopped batch {{batch_no}}. These {{n}} pictures are the ones not yet made, starting with {{first_missing_id}}. ATTACHED, in this order: {{attached_list}}
-----BEGIN PICTURES-----
{{picture_blocks}}
-----END PICTURES-----

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
