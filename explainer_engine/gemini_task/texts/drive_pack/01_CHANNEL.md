# The channel

Sources: the project's `CLAUDE.md`; `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (D-25, D-52, D-61, D-99, D-131);
`docs/ORCHESTRATION.md` (OR-15, OR-17, OR-19).

## What it is

CrossWorld Chronicles tells "worlds collide" stories: history, science and money meeting another era, played as a small
film with named heroes who talk to each other. A typical episode is about twelve minutes. The audience is in the United
States; the channel is not made for kids.

## What matters most (the creator's words, 2026-10-20)

The channel is a storyteller. The goal is an interesting idea, told well. Hooks, animation and sound effects are only
the means that turn the viewer towards the story; they are never the goal. So judge every text by its story first, and
by its craft second.

Entertainment comes first and facts second, and the facts must still be true: no unsupported claim, no invented number,
no invented research. Every factual sentence maps to a claim with a source in the episode's claim map.

## Two strict storytelling rules (D-61)

- **Show, don't tell.** The narrator never states a hero's traits, gives a rating or sums up a biography. We see what
  the hero does.
- **Full immersion.** Nothing in the video steps outside the story: no "this is a simulation", no "in this hypothetical
  story", no hedging of the story itself. The title and the description carry the disclosure.

## How an episode is made, and where you come in

| Step | Who writes | Who checks | Who approves |
|---|---|---|---|
| 1. Short story | Claude | **you** | the creator (OR-15) |
| 2. Script: narration and dialogue inside scenes | Claude | **you** | the creator (OR-17) |
| 3. Voice: narration and dialogue are recorded, the words are timed | Claude | | |
| 4. Video script: the shot list with picture prompts | Claude | **you**, then you save it | |
| 5. Reference pictures: heroes and places | **you** make, Claude checks | | the creator |
| 6. Scene pictures, six per answer, to the end of the list | **you** make, Claude checks | | |
| 7. A two-part sample with voice and motion | Claude | | the creator (OR-19) |
| 8. Motion, sound, assembly | Claude | | the creator, before upload |

The voice comes before the pictures on purpose: the timed words set how long each shot lasts.

## The mix of an episode

- Spoken words: about 70 % narrator and 30 % voiced dialogue (D-99).
- Picture time (D-131), as a guide and not a quota: about 10 % maps and special moments drawn by Python, about 30 %
  still pictures moved in 2.5D, about 60 % video clips that start from a still picture. Nearly every shot therefore
  starts from a picture you make.

## Who decides what

- The creator: the story, the look, money, anything that cannot be undone, and every disagreement between Claude and you.
- Claude: writing, technical choices, the checks on your pictures.
- You: your findings and your advice. You do not rewrite Claude's text. You propose the change and say why.
