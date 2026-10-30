---
name: lora-dataset-auditor
description: Stage page (OR-20, D-79): the main agent runs this stage itself, following this page; it is not spawned as a separate agent. Audits the training set of the channel's one LoRA (xworld style on Qwen-Image-2.1, D-80) before any pod (gate G1 of docs/LORA_TRAINING.md) - captions, trigger, shared phrases, duplicates, resolution, the creator's share - and looks at every item. Use before every LoRA run and whenever a dataset version changes.
model: sonnet
effort: medium
tools: Bash, Read, Write, Grep, Glob
---

You audit one dataset for the `lora-coordinator`. Rules: `docs/LORA_TRAINING.md` LT-01..LT-08; skill `lora-training`.

1. Run the tool (free, local):
   - photos: `python -m explainer_engine.training audit-style <folder>... --repeats his=5,aux_k=2 --creator his`
   - (retired, see History) edit pairs: `python -m explainer_engine.training audit-edit <targets> <control>...`
   - (retired, see History) video: write `clips.json` (`path, frames, width, height, caption` from ffprobe) and `audit-video clips.json`
2. Look at every item yourself (a numbered contact sheet; Read the image): style match with the creator's pictures, text
   and logos, eyes on objects, collages, grey or muddy colour, (retired, see History: cuts or scene changes inside a clip, character names in a
   motion caption (the motion LoRA learns movement only)).
3. Report: the tool's findings, then one line per item that is not a plain keep (`file - keep low / drop - why`), the
   creator share, and the exact fix for each FAIL. Never edit or delete the data yourself; the data owner applies it.

## History (retired by D-80)
- The edit-pair (`audit-edit`) and video-clip (`audit-video`) steps served the next-pose and video-motion LoRAs, which D-78, D-80 and LT-69 retired; they are not planned. Old description: Stage page (OR-20, D-79): the main agent runs this stage itself, following this page; it is not spawned as a separate agent. Audits a LoRA training set before any pod (gate G1 of docs/LORA_TRAINING.md) - captions, trigger, shared phrases, duplicates, resolution, the creator's share, edit-pair matching, video clip frames - and looks at every item. Use before every LoRA run and whenever a dataset version changes.
