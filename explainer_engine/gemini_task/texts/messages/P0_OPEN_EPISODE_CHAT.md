# P0: open the episode chat (operator notes; only the MESSAGE block is sent)

Kind: CHECK. Spec: section 3 row P0; GC-10 (one episode, one chat), Q13. The first message of an episode's one Gemini
chat, on Flash in Task mode, before the short story is checked. It makes no picture and holds no episode text.

Placeholders: `episode_id`, `episode_title` (from `episode.json`), `era_line`, `sha8` (of the era line and title),
`drive_root`.

=====BEGIN MESSAGE=====
CHECK | P0 open the episode chat | episode {{episode_id}} | sha {{sha8}}

Make no picture. This is a check: you read and answer in words, in three lines.

READ on Drive, and nothing else: {{drive_root}}/rules/00_START_HERE.md and {{drive_root}}/rules/01_CHANNEL.md.

INPUT: this chat is for one episode only: {{episode_id}}, "{{episode_title}}". The episode's era: {{era_line}}

DO:
1. Work only on Flash. Write the model and the mode the chat shows.
2. Read the two files. Write the pack version line of 00_START_HERE.md exactly, or say you could not open it.
3. Confirm you will use only this episode's files and messages in this chat.

DO NOT:
- make any picture, card or placeholder;
- read or change any other file on Drive.

ANSWER exactly in this form:
MODEL: <name> | MODE: <name>
PACK: "<the pack version line>" | NOT OPENED <reason>
READY: episode {{episode_id}}
=====END MESSAGE=====
