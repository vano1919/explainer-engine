# How a batch of pictures is made

Sources: `docs/GEMINI_CONSISTENCY_RULES.md` (GC-01..GC-25); the creator's messages of 2026-11-12 (15:20 and 15:25 UTC);
the test rounds of 2026-11-12 (`reference_round_1/v9` on the project's Hugging Face store).

A batch is one message from Claude that lists six pictures, and one answer from you that holds those six pictures and a
short report. Claude downloads them, checks each one and sends the next batch. This repeats to the end of the list.

## The eight rules of a batch

1. **Actual generated pictures only.** Use your built-in image generation tool for every picture. Never draw a
   picture, a text card, a placeholder, a grid or a collage with Python (PIL, matplotlib) or any other code. Why: a
   run of 168 once came back as four pictures and 164 text cards, and nobody could use it.
2. **Send each prompt to the image tool word for word.** Do not rewrite, shorten, translate, merge or decorate it, and
   add no style words of your own. Why: the wording is tested; added words have changed the look of whole rounds.
3. **Separate 16:9 pictures, in the order listed**, six unless the message names another number. One prompt makes
   one picture. No grid, no collage, no extra
   variants, nothing that is not on the list.
4. **References exactly as listed for each picture, in the order listed.** The first one is the style anchor: take
   the look from it and nothing else. Do not copy its people, their pose or its place. The following ones are our
   heroes and our place: keep their faces, hair, costumes and props exactly.
5. **No text in any picture**: no letters, numbers, signs, labels, logos, watermark, and no marks that look like
   writing.
6. **Every object fits the era named in the message**, and the light comes from the light source named in the prompt.
7. **Never repair inside a batch.** If a picture comes out wrong, leave it. Claude collects the bad ones and sends
   them again at the end, six at a time (the creator, 2026-11-12).
8. **Tell the truth about what happened.** If a picture was not made (a limit, a refusal, an error), write
   `NOT MADE` for it in the report and go on. Never fill the gap with something else.

## The report after the pictures

After the last picture, write this and nothing more:

```
BATCH REPORT <batch number>
1 | <picture id> | MADE | refs: <numbers> | prompt: AS GIVEN|CHANGED <how> | note: <one short line, or ->
2 | <picture id> | NOT MADE | reason: <one short line>
...
MADE <n> of <total>
```

Use the note for anything Claude should look at: "a second lamp appeared", "the cloak is a different colour". If the
tool changed a prompt, write `prompt: CHANGED` and how. One line. No descriptions of the pictures, no praise.

## Order of the work

1. **Hero portraits and places first.** A portrait is chest-up, the face clear and evenly lit. The creator approves.
2. **Full-body pictures of the heroes**, each made with its own approved portrait attached, so it is the same person.
3. **Scene pictures**, batch after batch, each with its style anchor, its heroes and its place attached.
4. **The redo list**, at the end.

## The daily limit

The chat makes only so many pictures a day (about {{pictures_per_day}} were measured on 2026-11-12). When the limit
comes, stop: report what was made and write `NOT MADE: limit` for the rest. Do not switch to another model, and never
to code. Work continues the next day from the first picture that was not made (`08_FILES_AND_STATE.md`).

## The model

Pictures are made on **Flash**. Never on Pro, Argon or Carbon, and never through a paid API (GC-16). If the chat
shows another model, say so in one line before doing anything else.

## Keeping a hero the same across the whole episode

- The hero's portrait is attached to every picture the hero is in, and the hero's description in the prompt never
  changes by a word.
- You are not asked to remember faces from earlier answers. Each batch stands on its own references.
- If you notice that a face in a new picture has drifted from its portrait, say so in the report. That is help.
