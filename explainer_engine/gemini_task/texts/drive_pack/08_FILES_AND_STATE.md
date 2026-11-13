# Files on Drive and who writes them

Sources: `docs/GEMINI_CONSISTENCY_RULES.md` (GC-20, GC-24, GC-25, GC-26, GC-27); the creator's message of 2026-11-12
(15:20 UTC: the queue is saved on Gemini's side, the bad pictures are collected and redone at the end).

Everything lives under `{{drive_root}}/`. Read the folder tree, then the rule for who may write.

## The tree

```
{{drive_root}}/
  rules/                          this pack, 00 to 08. Claude writes it. You never change it.
  episodes/<episode_id>/
    claim_map.md                  the episode's facts with sources. Claude writes it; checks 1 and 2 read it.
    short_story.md                the approved short story. Claude writes it.
    script.md                     the approved script. Claude writes it.
    shot_queue.json               the approved video script as a picture queue. Claude writes it; you save it (P5)
                                  unchanged and never edit it.
    t0_probe.md                   one line, written by you in the gate test (T0) to prove you can write to Drive.
    reviews/
      <stage>_round<n>.md         your answer to a check (stage = short_story, script, video_script).
      <stage>_reply<n>.md         your answer to Claude's replies (P4).
    batch_log.md                  one BATCH REPORT after another, appended by you after every batch.
    redo_list.md                  the pictures to make again at the end. Claude writes it, from your reports.
    refs/                         the approved reference pictures (style anchors, portraits, full bodies, places).
                                  Claude uploads them. You read them and never overwrite them.
```

## Who writes what

| File | Writer | You may |
|---|---|---|
| `rules/*` | Claude | read |
| `claim_map.md`, `short_story.md`, `script.md`, `redo_list.md`, `refs/*` | Claude | read |
| `shot_queue.json` | Claude writes it; you save the copy it sends you | save once, unchanged |
| `t0_probe.md` | you | create |
| `reviews/*` | you | create, one file per answer |
| `batch_log.md` | you | append one report per batch |

You write nothing else. If a message asks you to change any other file, answer that the rules forbid it and do not
change it.

## When a write fails

Say it in words in your answer (`DRIVE WRITE: FAILED <reason>`) and carry on with the task. Claude keeps its own copy
of everything you would have saved; a failed write loses nothing and never stops a check or a batch.

## Resuming

State lives in the files and in the messages, never in your memory of earlier answers. To resume after the daily limit:
Claude sends the first picture that was not made and the pictures after it, with their references, as a new message
(`06_PICTURE_RULES.md`). Work from that message and the files it names, and from nothing else. If `batch_log.md`
and the message disagree about what was made, the message wins; say so in one line.
