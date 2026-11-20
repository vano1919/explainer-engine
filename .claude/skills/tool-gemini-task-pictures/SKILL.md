---
name: tool-gemini-task-pictures
description: Operate the Gemini chat's built-in image tool in Task mode as this channel's only picture maker - the T0 gate, references before scenes, batches of six pasted by the owner's computer session, the batch report and intake by order, the daily limit and the next-day resume, the output size an attachment costs, the free local 2x upscale after intake, and the paid 2K re-make only for a failing close-up hero shot, priced and asked first. Use when a batch of start or end pictures is planned, sent, received, resumed or redone, when a picture comes back small, missing or out of order, and before anyone proposes paying for a picture.
---

# Gemini Task mode pictures, the tool (layer L9, stage G5)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) as the tool page for the picture
maker of a v4.3 episode (D-131). This page is about running the tool; what a prompt says (the film line, the place block,
the hero text) is skill `v-visual-skills-image`, holding faces across pictures is skill `v-scenario-consistency`, and
judging what came back is skill `tool-vision-qa`.

## When to use, when not

- Use for every picture of an episode: hero portraits and places (rounds R1 and R2), start frames, end frames of a
  chained video shot, inserts. All of it is free inside the owner's subscription.
- Not for maps, charts, labels or any lettering (Python draws them, GC-07), not for thumbnails (`publish thumbnail`, a
  paid premium paint behind its own gate), and never through the paid API by default.
- Retired for v4.3 and only to be named as legacy: the Qwen-Image + xworld LoRA route and the legacy paint plans.

## What the engine does and what the session does

The engine cannot press buttons in Gemini. It writes the messages and reads the answers; the owner's computer session
(Claude in Chrome on his Gemini account, GC-15) pastes, attaches, waits and downloads; manual pasting is the fallback.

| Half | Module | CLI |
|---|---|---|
| Task route: T0, queue, batches, intake, verdicts, redo, resume | `explainer_engine/gemini_task/batch.py`, `queue.py`, `gate.py`, `report.py`, `prompts.py` | `python -m explainer_engine.gemini_task --help` |
| Chat route (fallback) and the shared intake, promote, remake list | `explainer_engine/imagegen/turn_pack.py` | `python -m explainer_engine.imagegen.turn_pack --help` |
| Every accepted original and master, hashed, read-only | `explainer_engine/imagegen/vault.py` | `python -m explainer_engine.imagegen.vault --help` |
| Paid backup when the owner says so | `explainer_engine/gemini_task/api_backup.py` | `estimate` first, `submit` only with `EXPLAINER_GEMINI_API=on` and a cap |

The fixed message texts live in `explainer_engine/gemini_task/texts/messages/` (T0, P6 references, P7 and P8 scenes, P9
resume, P10 redo); the Drive rules pack in `texts/drive_pack/`.

## The procedure

1. **T0 once** (GC-20): `python -m explainer_engine.gemini_task t0 <episode>`, paste, then `t0-record` with the answer and
   the downloads. Six generated pictures in one answer, each 16:9 and at least the native width, is PASS at batch size
   six (owner rule 19; `config/gemini_task.json` `batch_size_default`). Four or five sets that size; three or fewer, or a
   forced model change, stops the route and becomes a card for the owner. Every other message refuses until T0 passed.
2. **Open the episode's chat** (P0). One episode, one chat, only that episode's anchors (GC-10). Flash image model, never
   Argon/Pro (GC-16).
3. **References first** (GC-23): `queue`, then `batch <episode> 1` for R1 portraits and places with the main style
   picture only; the owner approves by looking (`approve ... --by <his message id>`); R2 full bodies with their own
   portrait; only then scene batches. A picture whose reference is not approved stays `blocked`.
4. **Scene batches** after the read is timed (voice first, `gemini_task/timing.py`). Each picture block names the series
   film directly (rule 20, e.g. "frames from a video in the style of the film 1917 (2019)"), its references in the fixed
   order (style anchor, heroes in cast order, the place, props; an end frame takes its start frame as image 2, GC-09 as
   amended by GC-21), and its target file name. Start and end frames never share a batch.
5. **Paste word for word.** The answer must end in a `BATCH REPORT`: one `MADE` or `NOT MADE` line per picture and
   `prompt: AS GIVEN|CHANGED` (GC-24). Download in answer order.
6. **Intake**: `intake <episode> <no> --answer a.txt --drop <folder>`. Files map to ids by position; a count different
   from MADE, or ids out of order, is refused (the intake never guesses). Each file is gated free (decodes, 16:9, width
   floor, no bars, no duplicate, not a flat card drawn by code) and written to the ledger the moment it is checked.
7. **Look at every picture** (P-5) and record `verdict <episode> <id> ok|redo --correction "<one positive sentence>"`.
8. **Daily limit** (GC-27, GC-19): the answer writes `NOT MADE: limit` for the rest and must not switch model or draw
   with code. Next day `resume <episode> <no>` (P9) restarts at the first missing picture with the original blocks. Plan
   packs by the look's `pictures_per_day`; `turn_pack export` reports how many days an episode needs.
9. **Redo after the phase** (GC-25, P10): batches of the batch size, original prompt plus ONE correction sentence, the
   failed picture never attached. A picture that fails its redo goes to the owner, not to a second redo.
10. **Promote** with the free local 2x upscale (`turn_pack promote <episode>`, GC-14; the upscaler is skill
    `tool-upscale`). Without an installed upscaler the row is NOT_RUN and the picture stays a draft.

## Output size: what an attachment costs

Measured on 2026-11-19 (overnight log, batch 2 against batch 3): a Task-mode answer with no attached image came back at
2752x1536; the same text with one attached layout image came back at 1376x768. "4K quality" in the prompt changed
nothing. Since nearly every real picture attaches its style anchor and heroes (GC-01, GC-02), expect the 1376x768 size
(the intake floor, GC-12) and plan the 2x upscale for every picture; do not drop references to win resolution, because
the references are what hold faces and places. Re-measure when Gemini changes; this is one night's finding.

## Money

The chat is free. Paid is only: (a) GC-14's 2K re-make by the batch tier, listed by `turn_pack.remake_list` for close-up
and medium-close-up hero shots whose finished 1080p frame FAILed sharpness, each batch priced in the ledger
(`explainer_engine/core/ledger.py`), under `config/spend_caps.json`, and asked of the owner first; (b) `api_backup` when
the owner orders it after a used-up limit. A working login or a passed T0 is not his word.

## Failure modes and fixes

| What happened | Cause | Fix |
|---|---|---|
| Five files for six MADE lines | a download missed | re-download in order; never rename to fit |
| `prompt: CHANGED` on a line | the tool rewrote the prompt | treat the picture as unproven; redo list |
| Picture at 1376x768 | an attachment (expected) | promote with the 2x upscale |
| Square or illustrated picture | format ignored | redo list once, then the owner |
| The style picture's couple in a scene | missing style clause or wrong image 1 | check GC-01/GC-21 order, redo |
| Model switched to Pro, or a code-drawn card | the tool fell back after the limit | refuse at intake; `resume` next day |
| A picture of another episode | a shared chat | new chat per episode (GC-10) |

## Checks in code

T0 record `config/gemini_t0_record.json`; prompt gates in `prompts.py` (`check`) and `turn_pack.check_prompt` (GC-03,
GC-04, GC-06, GC-07, GC-11, GC-18, GC-21, GC-22); intake by order in `batch.py` and `report.py`; size and duplicates in
`turn_pack.intake` (GC-12); masters in `turn_pack.promote`; the per-shot state machine in
`explainer_engine/episode/shot_state.py` (an observed picture whose hash changes must be observed again). Rules:
[docs/GEMINI_CONSISTENCY_RULES.md](../../../docs/GEMINI_CONSISTENCY_RULES.md) GC-01..GC-27.

## Known stale text

GC-18's never-words list in `config/visual_style_presets.json` refuses "realistic" and "photograph", and GC-11 names the
older adventure-film face look; a film-look series under rule 20 asks for realistic film frames. Until the owner rewrites
those lines, give the film-look series its own look entry with its own `never_words`, and report the conflict.

## Sources (what each taught; licence noted in one line)

- Google, "Prompting tips for Nano Banana Pro" (blog) and the AI Studio image-generation docs, fetched 2026-11-20 in the
  SK-1 research: name what each reference contributes; reference limits differ per model and the chat has its own.
- Emily2040/nano-banana-image-skill (Apache-2.0, commit `1f1360cc26`): label unofficial tricks as unproven.
- hosnye/directing-cinematic-storyboards, `references/nano-banana-prompting.md` (no licence file, commit `a09cf34b76`):
  read for the idea of a stable prompt architecture only.
