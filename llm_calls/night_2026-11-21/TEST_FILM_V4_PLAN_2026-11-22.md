# Test Film v4: plan (new, from zero; old test films are not used and not deleted)

Status: PLAN FOR OWNER APPROVAL. Nothing is paid. No paid run starts until ვანო approves this plan and gives a recorded card yes.

## 1. Purpose
One short film (about 60 s, 1920x1080, 24 fps) that tests the whole v4.3 chain end to end on a fresh set of shots: map shot, narration bridges, 2.5D still-motion shot, one video shot, sound, and the technical gates. It answers: do the new rules and tools work together on real output, and what does a full run cost.

## 2. Shot list (proposal, 3 shots, about 60 s)
| # | Lane | Length | What it tests | Where it runs | Paid? |
|---|---|---|---|---|---|
| S1 | map (maps/render.py, camera move from the five) | ~20 s | map rules M1–M7, a narration bridge (B1–B6), truck or zoom move (C1) | local CPU or PC | no |
| S2 | 2.5D still-motion (fx25d/living.py, 1920x1080 output) | ~20 s | no-melt on a person-free plume, output size, frozen and sharpness gates | local CPU | no |
| S3 | video (LTX-2.5 distilled on Modal, D-132) | ~20 s, 2 clips of about 10 s | one video clip with speech, video gate on real motion | Modal | yes, small |

Narration: one voice line per shot, ElevenLabs. Music and SFX: library first (no new paid SFX unless the library has none).

## 3. What is measured (gate set)
- Video: technical_gate.check_video on each rendered clip: size 1920x1080, fps 23.9–60.1, bitrate ≥ 4000 kbps, black ≤ 0.02, frozen ≤ 0.05, sharpness ≥ 0.02 (GUESS). Thresholds stay PROVISIONAL; the first run is measurement, not a pass/fail on taste.
- Audio: technical_gate.check_audio (LUFS −16.5..−13.5, true peak ≤ −1 dB, clipping, speech-to-noise ≥ 20 dB, silence ≤ 40 %).
- Map: QUALITY_SPEC M1–M7 and bridge rules B1–B6 (PROVISIONAL, T1–T10 owner approves on samples).
- Camera: only the five moves (delivery_gate.ALLOWED_CAMERA_MOVES), one per shot.
- No-melt: qa/still_region.py measure only (no limit yet, codec floor noted in the 2026-11-21 results).

Not in this film: taste judgements (story, look). Those stay with ვანო.

## 4. Cost (estimate, not spent)
- S1, S2: $0 (local CPU, free renders).
- ElevenLabs narration for 3 lines: small, credit-based; amount depends on the account's current rate; to be priced before the run (not priced tonight: no live account check).
- S3, Modal LTX: measured earlier at about $0.1 per clip (2026-11-21 notes), so 2 clips about $0.2 plus start-up. Stop line proposal: $2 for this film, far below the Modal $10 line.
- Claude API: none needed for the run itself.
Total paid estimate: under $2 for Modal plus the ElevenLabs credit. The Modal spend line in config/spend_caps.json is still absent, so the owner must approve that line first.

## 5. Preconditions (must hold before any paid step)
1. ვანო approves this plan (recorded message id).
2. config/spend_caps.json gets the modal line (owner's word, recorded through governance).
3. The LTX shot's prompt and camera move follow the five-move rule.
4. OR-34 audit of the changed repo runs before a paid test (the rule for paid tests). The night's Opus technical check covered the render diff only; the full-repo audit is still due.

## 6. Steps (free first)
1. Build the three shot specs (JSON) locally; validate against the five-move rule and the bridge timing rules (free).
2. Render S1 and S2 locally at 1920x1080 (free); run the video and technical gates; record the numbers.
3. Stop. Report the numbers to ვანო. Ask for the approval of the paid S3 and the ElevenLabs lines.
4. After approval: S3 through the video lane (Modal, with the watchdog and the ledger), then the audio, then assembly, then the gates again.

## 7. Open questions for ვანო
- Is the 60-second length right, or do you want the three-shot version only?
- Which narration words should the bridges show (the film text is not fixed yet)?
- Confirm the Modal line of $2 for this film (within the $10 total).
