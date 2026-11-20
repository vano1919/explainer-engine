# Observation pipeline (W4, OB-1, OB-2)

Nothing generated moves on unseen: every picture, clip and voice take gets an observation record bound to its sha256, and the stage
gate refuses an asset without one. Code: `explainer_engine/qa/observe.py`, observers in `explainer_engine/qa/observers/`, actions in
`explainer_engine/qa/retry_router.py`, schema `explainer_engine/schemas/observation_record.schema.json`, tests `tests/unit/test_observe.py`.
Plan: `final_plan_2026-11-19/FINAL_COMPOSITION_PLAN_2026-11-19.md` section 5.4 and W4 (project files).

## 1. The record

One JSON line of `episodes/<ep>/qa/observations.jsonl` (`observation_record/1`): `asset_sha256`, `asset_id` (the vault record, whose
`observation_record_id` is set when a record is written), `shot_id`, `kind` (image, clip, voice), `observer`, `questions`, `answers`,
`defects` (`code`, `where`, `severity`), `verdict` (`qa/status.py`: PASS, REVIEW, RETRY, BLOCK, NOT_RUN), `action` (none, R1..R4),
`observed_at`, `evidence` (sheet, frame strip, transcript diff, task file) and `reviewed` (who looked at the evidence).
Defect codes: F1..F19 of the failure taxonomy in `.claude/skills/v-director-cinematic/references/failure-modes.md` (that file owns
them), `TECH-*` (measured by ffmpeg), `TXT-*` (transcript against the script).
Verdict from defects: none or info only -> PASS; a minor defect -> REVIEW; a major defect -> RETRY, or BLOCK when its action is generative
and the two retries are spent.

## 2. Observers (each returns records, never a bare bool)

| Observer | File | Looks at | Needs |
|---|---|---|---|
| `ffmpeg` | `observers/ffmpeg.py` | decode check, black / frozen / silent stretches (BP-211), audio offset (BP-54), loudness, PySceneDetect cut list | ffmpeg; NOT_RUN without it; a missing PySceneDetect leaves only the cut list NOT_RUN |
| `transcript` | `observers/transcript.py` | an existing Whisper per-clip or Scribe transcript against the script line, word by word (missing, extra, duplicated, words on a silent beat, last word at the file's end) | an existing transcript; NOT_RUN without one; no new transcription call |
| `claude` | `observers/claude_look.py` | `request` builds the contact sheet, a full frame and the question list (the shot card's `acceptance_questions` plus an F-code checklist); the session opens them, `record` writes its answers | free |
| `gemini_chat` | `observers/gemini.py` | `chat_task` writes the G1 task file for the creator's own Gemini chat; `ingest_chat` reads the returned JSON | free; the creator runs the chat |
| `gemini_api` | `observers/gemini.py` | File API with an `fps` setting; client supplied by the caller, none built in | code and mocked tests only; no call without the creator's word (section 6) |

## 3. The gate

`episode/run.py` calls `observe.gate_rows` in `run_stage` before `clips` (every bound picture) and before `assemble` (every bound clip).
An asset passes only with a counted PASS record for its **current** sha256; a changed file has another hash, so its records no longer
count (and `shot_state.check_all` has already reset its states). Required observers: a picture needs the `claude` look (the Gemini chat makes the pictures, so
`gemini_chat` / `gemini_api` are optional extra eyes: their miss counts, their PASS never accepts alone, MA-15); a clip needs `ffmpeg` and one look; a voice take needs `transcript`. MISSING, NOT_RUN, RETRY, BLOCK and an unlooked
automatic PASS give a BLOCK row listing the shots (the stage does not run, except in a rehearsal, which never ships; unreadable records are the same BLOCK, recorded as a FAIL row, never a crash); only REVIEW
records give a REVIEW row, which needs the creator's `approve` bound to his message id before the next stage. Nothing bound to any
shot is a NOT_RUN row (never a pass, P-6), and a shot whose state is past the asset (`IMAGE_OBSERVED`.. for pictures, `VIDEO_OBSERVED`..
for clips) with no bound asset is a BLOCK line.

`ShotStates` moves when a record is written: `IMAGE_OBSERVED` then `IMAGE_ACCEPTED` (a picture), `VIDEO_GENERATED`, `VIDEO_OBSERVED`,
`CLIP_ACCEPTED` (a clip); the accepted states only when every required observer has a counted PASS.

## 4. Trust: the calibration rule

An automatic observer (ffmpeg, transcript, gemini_api) decides alone only after the creator accepts its calibration report
(`python -m explainer_engine.qa.observe accept <observer> --message-id cmsg_... --words "<his words>"` writes an `observer_calibration`
record to `jobs/creator_ok.jsonl` and the entry `accepted.<observer>` = {message_id, words, at} in `config/observer_calibration.json`, which
starts empty; a hand-edited entry does not count, only one whose message id is recorded). Until then its PASS counts only after the session
or the creator looked at its evidence: `python -m explainer_engine.qa.observe review <episode> <record_id> --by session --note "<what was
looked at>" --evidence <file>`. A session review needs that note and an existing evidence file (sheet, frame, transcript diff) whose
sha256 is stored with the stamp (a changed file voids it); an owner review needs his chat message id recorded as `observation_review` of
`<episode>:<shot>:<sha256[:12]>` (`governance ok`); `gemini_chat` records carry the owner stamp only when it is recorded.
Report: [OBSERVATION_CALIBRATION_2026-11-20](OBSERVATION_CALIBRATION_2026-11-20.md).

## 5. Defect to action (OB-2)

R1 fix in place (trim, mute, reseed, inpaint), R2 prompt patch, R3 new keyframe or reference, R4 fallback 2.5D. `generative` = it spends (D-131)
a generation and counts against the two retries of `shot_state.RETRY_CAP`; a trim, a mute and the 2.5D fallback spend none. The third (D-131)
generative retry is refused (`retry_router.consume_retry` raises); `retry_router.decide` then answers R4 for a clip and ESCALATE for a
picture. An unknown code has no action and is refused. The table is `retry_router.R_ACTIONS` (a test keeps this page equal to it):

| Code | Action | Generative | Why |
|---|---|---|---|
| `F1` | R3 | yes | identity is restored from the untouched master, not by wording |
| `F2` | R2 | yes | motion is written as a body mechanic (failure-modes F2) |
| `F3` | R2 | yes | one motion source, a tighter shot size |
| `F4` | R2 | yes | the action is rewritten as a body mechanic |
| `F5` | R3 | yes | an end keyframe gives the clip an end state (D-131) |
| `F6` | R2 | yes | exactly one named camera move with a magnitude |
| `F7` | R3 | yes | the end state of shot N becomes the start of N+1 through a new keyframe (D-131) |
| `F8` | R2 | yes | the era's forbidden-object list goes into the prompt |
| `F9` | R2 | yes | the head count is declared in the prompt |
| `F10` | R1 | yes | reseed or inpaint the hands; an insert only if two seeds fail |
| `F11` | R1 | yes | reseed or inpaint the text or mark |
| `F12` | R2 | yes | the named key source and side go into the prompt |
| `F13` | R2 | yes | duration and pace are budgeted from the action |
| `F14` | R2 | yes | contact moments are scheduled on cuts |
| `F15` | R1 | no | trim or mute the take; a clip that cannot be trimmed goes to R4 |
| `F16` | R3 | yes | style is restored from the approved reference |
| `F17` | R2 | yes | the delivery aspect is fixed in the prompt |
| `F18` | R1 | no | cut the seam out; long beats are planned as cut sequences |
| `F19` | R3 | yes | the prop is held in frame or handed to a cut by a new keyframe (D-131) |
| `TECH-DECODE` | R1 | yes | the file does not decode: generate it again with a new seed |
| `TECH-BLACK` | R1 | no | trim the black stretch |
| `TECH-FREEZE` | R2 | yes | a frozen picture is F2: write the motion |
| `TECH-SILENCE` | R1 | no | mute or trim; a silent beat may be intended |
| `TECH-OFFSET` | R1 | no | re-align the audio start in the edit |
| `TECH-FPS` | R1 | no | re-time the clip in the edit |
| `TECH-FRAMES` | R1 | no | re-time or trim the clip in the edit |
| `TECH-CUT` | R1 | no | trim at the unexpected cut (F18) |
| `TXT-DUP` | R1 | no | trim the repeated word out of the take |
| `TXT-FALSE` | R1 | no | mute the clip audio: words on a silent beat |
| `TXT-EXTRA` | R1 | no | trim the extra words |
| `TXT-MISSING` | R2 | yes | a word is missing: the line is read again (ElevenLabs credits: the creator is asked first) |
| `TXT-CUT` | R1 | no | play the take to its end |

## 6. Gemini API arm: priced plan (not run)

Prepared only: nothing here calls the API. Run needs the OR-23 plan with the creator's word, the OR-34 audit, and `GeminiApiObserver`
with a client that saves each raw answer before parsing (OR-33; the class does).

Price page: `aistudio.google.com/docs/pricing` (redirect of `ai.google.dev/gemini-api/docs/pricing`), read 2026-11-19, no update date on
the page. Video: `aistudio.google.com/docs/video-understanding`, read 2026-11-19: default 1 fps, `fps` in (0, 24], 258 tokens per frame
(66 at low media resolution), audio 32 tokens per second, File API 20 GB per file on the paid tier. Output tokens are an assumption
of 1,500 per clip (answers, defect list, thinking); the measured figure replaces it after a first clip.

Files: calibration set = the 12 raw LTX clips of `episodes/ep_truce_1914/qa/observer_calibration_labels.json`, 51.8 s in total; full set = (D-131)
56 raw clips, about 242 s (12-clip mean x 56). Estimate = seconds x fps x 258 video tokens at the input price + seconds x 32 audio
tokens at the audio price + output tokens at the output price. Standard tier (not batch).

| Set | fps | gemini-3-flash-preview ($0.50 in, $1.00 audio, $3.00 out per 1M) | gemini-3.1-pro-preview ($2.00 in, $12.00 out) | gemini-2.5-flash ($0.30 in, $1.00 audio, $2.50 out) |
|---|---|---|---|---|
| 12 clips | 1 | $0.062 | $0.246 | $0.051 |
| 12 clips | 2 | $0.069 | $0.273 | $0.055 |
| 12 clips | 4 | $0.082 | $0.326 | $0.063 |
| 56 clips | 1 | $0.291 | $1.148 | $0.236 |
| 56 clips | 2 | $0.322 | $1.273 | $0.255 |
| 56 clips | 4 | $0.385 | $1.523 | $0.293 |

The page says Gemini 2.5 Flash and Pro are no longer selectable in AI Studio and route to newer models from 2026-12-01, so the 2.5
column is a reference only. The 1914 calibration needs the 12-clip row (under $0.10 on a Flash model); the cap rule for the plan is
`config/spend_caps.json` (spend so far $4.58 of $5.20, $0.62 left): the 12-clip run fits, the 56-clip Pro run does not. fps choice is the
creator's: the handshake break of S04_SH014 lasts under a second, so fps 1 may miss a short defect; fps 2 to 4 costs under $0.02 more on the 12-clip set.

## 7. Commands

```
python -m explainer_engine.qa.observe status <episode folder>
python -m explainer_engine.qa.observe gate <episode folder> --stage clips|assemble
python -m explainer_engine.qa.observe review <episode folder> <record_id> --by session|owner [--note T] [--evidence FILE] [--message-id M]
python -m explainer_engine.qa.observers.calibration <clips dir> <labels.json> <whisper.json> <shot_plan.json> [--claude answers.json]
```
