# P6: a reference batch, rounds R1 and R2 (operator notes; only the MESSAGE block is sent)

Kind: PICTURES. Spec: section 3 row P6; Q4, Q7, Q8. Sent in the episode's one chat (GC-10), on Flash in Task mode.

- **R1**: hero portraits (`portrait` clause) and places (`place` clause), reference 1 = `main_style_5709.png` for every
  picture, nothing else attached. The creator approves each portrait and place by looking.
- **R2**: hero full bodies (`keep_full_body` + `full_body` clauses), reference 1 = `main_style_5709.png`, reference 2 =
  that hero's own APPROVED portrait. R2 is also test T1 (Q8): every picture uses a different reference 2, and T1 passes
  when each full body matches its own portrait and no other. If it fails, later batches hold one hero set only.

Attach: the files of `{{attached_list}}` in that order (R1: the main style picture; R2: the main style picture, then
the portraits in the order of the blocks). `{{round_note}}` is the R1 or R2 sentence below, chosen by the exporter.

R1 round_note: `Round R1: portraits and places. Each picture uses only the main style picture.`
R2 round_note: `Round R2: full bodies. Each picture uses the main style picture and its own portrait only; it never sees the other portraits.`

Placeholders: `episode_id`, `sha8`, `round` (R1 or R2), `round_note`, `n`, `era_line`, `attached_list`,
`picture_blocks`, `drive_root`.

=====BEGIN MESSAGE=====
PICTURES | P6 reference batch | episode {{episode_id}} | sha {{sha8}} | round {{round}}

READ on Drive, if you can: {{drive_root}}/rules/06_PICTURE_RULES.md. Everything this batch needs is in this message.

INPUT: {{n}} picture blocks. {{round_note}} ATTACHED, in this order: {{attached_list}}
-----BEGIN PICTURES-----
{{picture_blocks}}
-----END PICTURES-----

DO:
1. Work only on Flash. If the chat shows another model, write MODEL: <name> and stop.
2. Make the {{n}} pictures now with your direct image generation tool, one prompt per picture, as {{n}} separate 16:9 pictures in the listed order. No grid, collage, sheet of views or extra variant.
3. Write the report below. In the note, say if a face looks like a different picture's person.

RULES:
- Use only your direct image generation tool. Never draw a picture, card, placeholder or grid with Python or any other code.
- Send each prompt to the image tool word for word: add, cut or rewrite nothing.
- Attach the references exactly as listed for each picture, in that order. Image 1 gives the look only, never its people, pose or place; image 2, where listed, is this hero's face, kept exactly.
- No text, letters, numbers or writing-like marks in any picture. Every object fits this era: {{era_line}}
- Never repair or substitute. A picture not made is written NOT MADE with its reason.
- If the daily limit comes, stop: write NOT MADE: limit for every picture left, and never switch model or fall back to code.

ANSWER exactly in this form, after the pictures:
BATCH REPORT {{round}}
1 | <picture id> | MADE | refs: <numbers> | prompt: AS GIVEN|CHANGED <how> | note: <one short line or ->
2 | <picture id> | NOT MADE | reason: <one short line>
MADE <n> of {{n}}
=====END MESSAGE=====
