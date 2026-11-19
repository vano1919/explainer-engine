# Observer calibration, free observers (W4, 2026-11-20)

Question: do the free observers find the known 1914 defects and keep quiet on clips with no recorded defect? Data: `episodes/ep_truce_1914/qa/observer_calibration_2026-11-20.json`
(full records), labels `episodes/ep_truce_1914/qa/observer_calibration_labels.json`, session answers `observer_calibration_claude_answers.json`, tool
`explainer_engine/qa/observers/calibration.py` (run: see [OBSERVATION](OBSERVATION.md) section 7). Cost $0.

## Set

12 raw LTX clips downloaded from the HF dataset (sha256 equal to the vault records of `asset_records.jsonl`, checked): 3 labelled
defect clips (`S06_SH008` the word "Maybe" twice; `S03_SH007` silent beat transcribed as "Oh my God" and a white fog bloom; `S04_SH014`
handshake breaks at the end; source `CORRECTIONS_LOG.md` part A), 8 labelled good, 1 not evaluable (`S03_SH003`: its defect, a cut word
"Nacht", was made by the old assembly, the raw clip is complete, so no label is claimed). Good means only: no defect recorded in the corrections log.
It is not a verified-good label (the 1914 film was rejected as a whole). Pictures are not calibrated: no picture defect is labelled in the sources, so a picture
FP/FN count cannot be made yet. Counts are per clip.

## Results

### ffmpeg observer (decode, black, frozen, silent, audio offset, loudness, PySceneDetect 0.7.3)

TP 0, FP 0, FN 0, TN 11. Recall on the defects of its own kind: no labelled defect of this kind. Known defect clips outside its reach: `S06_SH008`, `S03_SH007`, `S04_SH014`.

- TP: none
- FP: none
- FN: none
- TN: `S02_SH006`, `S02_SH007`, `S03_SH004`, `S03_SH005`, `S03_SH006`, `S03_SH007`, `S03_SH008`, `S04_SH003`, `S04_SH004`, `S04_SH014`, `S06_SH008`

### transcript observer (Whisper small word timings of 2026-11-15 against the shot plan's line)

TP 2, FP 2, FN 0, TN 7. Recall on the defects of its own kind: 2 of 2. Known defect clips outside its reach: `S04_SH014`.

- TP: `S03_SH007`, `S06_SH008`
- FP: `S03_SH006`, `S04_SH014`
- FN: none
- TN: `S02_SH006`, `S02_SH007`, `S03_SH004`, `S03_SH005`, `S03_SH008`, `S04_SH003`, `S04_SH004`

### claude look (the session, blind round, picture only, 2 fps sheets)

TP 2, FP 3, FN 0, TN 6. Recall on the defects of its own kind: 2 of 2. Known defect clips outside its reach: `S06_SH008`.

- TP: `S03_SH007`, `S04_SH014`
- FP: `S02_SH006`, `S03_SH008`, `S04_SH004`
- FN: none
- TN: `S02_SH007`, `S03_SH004`, `S03_SH005`, `S03_SH006`, `S04_SH003`, `S06_SH008`

## What the counts say and do not say

- ffmpeg found nothing in 11 clips (0 FP); none of the three known defects is a black, frozen or silent stretch, so it is blind to all of them by
  design. PySceneDetect's content detector found no cut in any clip, including the jump inside `S04_SH004` that the look found: it is not
  a sufficient detector for a jump between two similar generated frames. Its use is "decode and gross failure", not defects of the story.
- transcript caught both transcript defects (the duplicated "Maybe": `TXT-DUP`; the words on the silent beat: `TXT-FALSE`). Its two FPs: `S03_SH006`
  (Whisper heard "him" for the script's "'em": a spelling difference the 0.6 similarity cutoff does not forgive) and `S04_SH014`
  (a single heard "You" on a silent beat, a known Whisper habit on noise; the clip has a real, other defect). The cutoff was not tuned on this set.
  Words on a silent beat may be a real artefact: whether they matter is the creator's.
- claude look caught 2 of 2 visual defects (`S03_SH007` bloom, `S04_SH014` break) and did not see the audio-only defect of `S06_SH008` (picture-only
  sheets: the sound is not in them). Its 3 FPs are things the labels do not know: `S04_SH004` shows a jump inside the clip (officer climbs, then stands
  with arms wide in another spot) that PySceneDetect missed; `S03_SH008` shows two soldiers appearing behind; `S02_SH006` shows the letter changing
  shape. The first is probably a real defect in a clip labelled good, so "good" is a weak label and the FP count is an upper bound. The look was blind
  to the shot names but not to the task, and one reader judged the whole set (no second reader), so the numbers are indicative, not a measurement of an independent judge.
- Sample size: 11 clips, 3 labelled defects. No rate here is a statistic.

## Decision for the creator

Not made by the observers. Until he accepts a report in a message (his id is then entered in `config/observer_calibration.json`), every automatic PASS needs the
session's recorded look, and no observer decides alone. Open question for him, in his words: accept `transcript` as a decider for the sound of a clip (2 of 2, 2 FPs of
11), accept `ffmpeg` as a decider for decode/black/frozen only, and keep the look (claude, or Gemini chat/API once priced and calibrated) as the only judge of the story picture.
The Gemini arms are not calibrated: the `gemini_chat` and `gemini_api` rows of the table in OBSERVATION.md stay unaccepted; the priced plan for the API run is its section 6.
