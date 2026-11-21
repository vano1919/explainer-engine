# P10: a redo batch (operator notes; only the MESSAGE block is sent)

Kind: PICTURES. Spec: section 3 row P10; Q11. Sent at the end of the episode, after the last scene batch, from the redo
list (`redo_list.md`), at most `{{batch_size}}` pictures per message.

Each redo block = the ORIGINAL picture block, with `REPLACES: <the earlier file>` after its first line and a new target
name, and with ONE correction sentence appended after the prompt's `tail`. The failed picture is never attached
(attaching it anchors the error). The references are the original ones.

How Claude writes the correction sentence (Q11): one sentence, in positive words, naming what the picture must show,
never what went wrong. "The only light is a clay oil lamp on the floor." not "Remove the glass lantern." "Kael's cloak
is dark red wool, as in image 2." not "The cloak was the wrong colour." No never-word, no text-words (the engine's
prompt gates run on the whole redo prompt). A picture that fails its redo goes to the creator, not into a second redo.

Placeholders: `episode_id`, `sha8`, `redo_no`, `redo_total`, `n`, `era_line`, `attached_list`, `picture_blocks`,
`drive_root`.

=====BEGIN MESSAGE=====
PICTURES | P10 redo batch | episode {{episode_id}} | sha {{sha8}} | redo {{redo_no}} of {{redo_total}}

READ on Drive, if you can: {{drive_root}}/rules/06_PICTURE_RULES.md. Everything this batch needs is in this message.

INPUT: {{n}} redo blocks. Each replaces an earlier picture that failed Claude's check; its prompt is the original with one correction sentence at the end. The failed pictures are not attached on purpose: do not look for them or copy them. ATTACHED, in this order: {{attached_list}}
-----BEGIN PICTURES-----
{{picture_blocks}}
-----END PICTURES-----

DO:
1. Work only on Flash. If the chat shows another model, write MODEL: <name> and stop.
2. Make the {{n}} pictures now with your direct image generation tool, one prompt per picture, as {{n}} separate 16:9 pictures in the listed order. No grid, collage or extra variant.
3. Write the report below.

RULES:
- Use only your direct image generation tool. Never draw a picture, card, placeholder or grid with Python or any other code.
- Send each prompt to the image tool word for word, the correction sentence included: add, cut or rewrite nothing.
- Attach the references exactly as listed for each picture, in that order. Image 1 gives the look only, never its people, pose or place; the others are our heroes and our place, kept exactly.
- No text, letters, numbers or writing-like marks in any picture. Every object fits this era: {{era_line}}
- Never repair or substitute. A picture not made is written NOT MADE with its reason.
- If the daily limit comes, stop: write NOT MADE: limit for every picture left, and never switch model or fall back to code.

ANSWER exactly in this form, after the pictures:
BATCH REPORT redo {{redo_no}}
1 | <picture id> | MADE | refs: <numbers> | prompt: AS GIVEN|CHANGED <how> | note: <one short line or ->
2 | <picture id> | NOT MADE | reason: <one short line>
MADE <n> of {{n}}
=====END MESSAGE=====
