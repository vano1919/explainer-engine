# T0: the gate test (operator notes; only the MESSAGE block is sent)

Kind: PICTURES. Spec: `A1_GEMINI_TEXTS_SPEC.md` section 3 row T0, section 6 "T0 passes when". Sent once, in a NEW
Gemini chat on Flash in Task mode, with the pack already on Drive under `{{drive_root}}/rules/`.
Attach: `main_style_5709.png` only (the repo copy, sha256 pinned in the preset), as the message's only image.
`{{picture_blocks}}` holds the six anchor candidates of `PROMPT_CLAUSES.md` (t0_B2, t0_C3, t0_D2, t0_E, t0_F, t0_G), in
that order, each with reference 1 = `main_style_5709.png` and nothing else.

What the record keeps (A3): the answer text; DRIVE READ and DRIVE WRITE; the number of real pictures and whether any was
drawn by code; each download's size; the time from send to the last picture; the limit state. Q3: `queue_on_drive` may
be switched on only if DRIVE READ is OK and every line says `prompt: AS GIVEN`.

Placeholders: `episode_id`, `sha8` (of the six assembled prompts), `drive_root`, `era_line`, `picture_blocks`.

=====BEGIN MESSAGE=====
PICTURES | T0 gate test | episode {{episode_id}} | sha {{sha8}} | batch 0

READ on Drive: {{drive_root}}/rules/00_START_HERE.md. Everything else is in this message.

INPUT: six picture blocks; the attached picture is reference 1 of each.
-----BEGIN PICTURES-----
{{picture_blocks}}
-----END PICTURES-----

DO, in this order:
1. Work only on Flash. Write MODEL and MODE as the chat shows them; if the model is not Flash, stop there.
2. Open 00_START_HERE.md and quote its "Pack version" line exactly, or write DRIVE READ: FAILED and why.
3. Create {{drive_root}}/episodes/{{episode_id}}/t0_probe.md holding one line: T0 probe {{sha8}}. Write DRIVE WRITE: OK with the path, or FAILED and why.
4. Make the six pictures now with your direct image generation tool, one prompt per picture, as six separate 16:9 pictures in the listed order. No grid, collage or extra variant.
5. Write the report below.

RULES:
- Use only your direct image generation tool. Never draw a picture, card, placeholder or grid with Python or any other code.
- Send each prompt to the image tool word for word: add, cut or rewrite nothing.
- Attach the references exactly as listed for each picture, in that order. Image 1 gives the look only, never its people, pose or place.
- No text, letters, numbers or writing-like marks in any picture. Every object fits this era: {{era_line}}
- Never repair or substitute. A picture not made is written NOT MADE with its reason.
- If the daily limit comes, stop: write NOT MADE: limit for every picture left, and never switch model or fall back to code.

ANSWER exactly in this form, after the pictures:
T0 REPORT {{sha8}}
MODEL: <name> | MODE: <name>
DRIVE READ: OK "<the quoted line>" | FAILED <reason>
DRIVE WRITE: OK <path> | FAILED <reason>
BATCH REPORT 0
1 | <picture id> | MADE | refs: <numbers> | prompt: AS GIVEN|CHANGED <how> | note: <one short line or ->
2 | <picture id> | NOT MADE | reason: <one short line>
MADE <n> of 6
LIMIT: not reached | reached after <n> pictures
=====END MESSAGE=====
