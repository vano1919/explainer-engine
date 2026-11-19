# P7: a scene batch (operator notes; only the MESSAGE block is sent)

Kind: PICTURES. Spec: section 3 row P7; Q1, Q2, Q4, Q9-Q12. Sent in the episode's one chat (GC-10), on Flash in Task mode.
A batch is at most `{{batch_size}}` pictures (six until the T0 record sets another number), grouped by place and style
anchor (Q10), so that one small set of attachments serves every picture of it.

Attach: the files of `{{attached_list}}`, in that order (the union of the batch's references: its style anchor or
anchors, the heroes' approved portraits and full bodies, the place). If the chat cannot show file names, the order of
the ATTACHED line is the only key, so attach in exactly that order.
`{{picture_blocks}}`: one block per picture as in `PROMPT_CLAUSES.md`; reference 1 of every scene picture is the style
anchor of its shot type (Q4), then the heroes in cast order, then the place (GC-02). No failed picture is ever attached.
Intake (A2) maps the downloads by their order in the answer and refuses a count that differs from MADE (Q9).

Placeholders: `episode_id`, `sha8` (of the batch's blocks), `batch_no`, `batch_total`, `n` (pictures in this batch),
`era_line`, `attached_list`, `picture_blocks`, `drive_root`.

=====BEGIN MESSAGE=====
PICTURES | P7 scene batch | episode {{episode_id}} | sha {{sha8}} | batch {{batch_no}} of {{batch_total}}

READ on Drive, if you can: {{drive_root}}/rules/06_PICTURE_RULES.md. Everything this batch needs is in this message; nothing depends on earlier answers.

INPUT: {{n}} picture blocks. ATTACHED, in this order: {{attached_list}}
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
- Never repair or substitute. A wrong picture stays as it is; a picture not made is written NOT MADE with its reason.
- If the daily limit comes, stop: write NOT MADE: limit for every picture left, and never switch model or fall back to code.

ANSWER exactly in this form, after the pictures:
BATCH REPORT {{batch_no}}
1 | <picture id> | MADE | refs: <numbers> | prompt: AS GIVEN|CHANGED <how> | note: <one short line or ->
2 | <picture id> | NOT MADE | reason: <one short line>
MADE <n> of {{n}}
=====END MESSAGE=====
