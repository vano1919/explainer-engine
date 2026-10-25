# Style learning and scene transitions: research and plan, 2026-10-25

ვანო asked (2026-10-25 22:55 Tbilisi) for one last, evidence-backed plan for teaching the style and for moving between
scenes, and proposed downloading successful series to learn both from them. Full write-up in Georgian:
https://claude.ai/artifact/MBSTqzFYrM1RRGrLhTYbfM. Nothing here is a rule yet; rules come after his word, each with two
source types (D-59). No pod, no paid call until he decides.

## 1. Why style learning went wrong (our records)

| Step | Result | Cause (research) |
|---|---|---|
| v2 trained on our own LoRA's pictures | 12/12 👎 | recursive self-training loses diversity and quality (model collapse, arXiv 2505.08803, 2509.16499) |
| one style tail on all 164 v5 captions | extra long-nosed people in 6/8 shots | words in the caption bind style and content (B-LoRA, arXiv 2403.14572) |
| switch to Qwen-Image-2.1 without a comparison | ≈$5.1, painterly drift at step 750 | no controlled test against v5 (LT-72) |
| scene LoRA | ≈$6.3, unused | D-75 keeps only the style LoRA |
| v5 trained mostly on eras-like frames | 13/70 👍 outside eras prompts | narrow content: the LoRA learns content, not style |

Our automatic measures (DINO, edge density, hue entropy) did not predict his votes; his rating is the only judge.

## 2. What the research says

- Style: 20-50 clean, varied images; no near-duplicates; neutral content captions without style words (B-LoRA);
  human-selected feedback rounds (StyleDrop, arXiv 2306.00983).
- YouTube: the largest history-animation channels (Oversimplified ≈9.6M subscribers, Simple History ≈5.1M, Extra History
  ≈4.6M; third-party trackers, approximate) use simple, consistent visuals; story, humour and one stable look carry them.
  vidIQ recommends ≥60 % retention at 30 s. YPP "inauthentic content" wording since 2025-07-15.
- Transitions: continuity-rule cuts go unnoticed about 1/4 of the time, about 1/3 on motion onset, and the effect needs
  continuous sound (Smith 2012; Smith & Henderson 2008). Event boundaries update memory (Zacks et al. 2010), so a scene
  change should be marked (narrator bridge, establishing wide, map, time card). Average shot length fell to 3-4 s by
  2005 (Cutting, DeLong & Nothelfer 2010); our 3312 measured shots: median 3.2 s, 81 % static camera.

## 3. On learning from downloaded videos

- Measuring grammar and transitions from them: yes (numbers only, frames not kept).
- Training the style LoRA on their frames: no. YouTube's Terms bar downloading outside YouTube's own features; the US
  Copyright Office (Part 3, 2025-05-09, pre-publication) treats building a training set as reproduction with a
  fact-specific fair-use test; a model trained on their frames reproduces their characters too; a look-alike invites the
  inauthentic-content risk. Style trains only on our own images that he approved.

## 4. Plan

Style: S0 free style spec + 30 fixed production prompts and seeds, his blind 4-level rating (pass ≈70 % 👍/👌) ->
S1 baseline without training: Gemini with his references vs v5 2512 with the eras formula vs qi21 step 500 (his call;
Gemini with references must be checked against D-78) -> S2 only if a LoRA is needed for cost: v6, 40-60 of his 👍
images, a content matrix, content-only captions, 20 % hold-out, one model, checkpoints every 250, ≈$3, stop if worse
than S1's winner -> S3 production with the winner, the eras formula and D-75 cards.

Transitions: T0 free measurement of the downloaded references (ASL by scene type, transition types, J/L audio, seconds to
the first conflict) -> T1 proposed rules with two source types and a test -> T2 the prepared D-75 four-shot test
(≈$2.5) on his word.

Reference series: Oversimplified Napoleonic Wars 1-2; Epic History TV Napoleon seasons; Kings and Generals Napoleonic
Wars; Simple History Napoleon episodes; Netflix Roman Empire and Rise of Empires: Ottoman (no statistics verified).
