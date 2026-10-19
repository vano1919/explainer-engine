# Title, thumbnail and hook system

Packaging is its own system and must be honest: the title, thumbnail, first frame, first sentence and payoff make one
promise that the video keeps. Hook rules are in [CREATIVE_STYLE_BIBLE](CREATIVE_STYLE_BIBLE.md) (D-07). Nothing here is a
predicted-performance rule; every pattern is a hypothesis tested on the channel's own data
([PUBLISHING_AND_ANALYTICS](PUBLISHING_AND_ANALYTICS.md)).

## Title pattern library (original adaptations; no competitor titles copied)
| Mechanism | Shape (example for a different topic) | Promise and curiosity | Depends on existing fame? | Payoff the video must deliver | Exaggeration risk |
|---|---|---|---|---|---|
| Hidden reason | "Why airplane windows are round" | one concrete cause behind a familiar thing | no | the cause, with its documented origin | low |
| Consequence | "What happens inside a battery when it dies" | a visible chain of events | no | the chain, stated at the level the sources support | medium (do not dramatise) |
| Misconception | "The part of leap years everyone gets wrong" | a common belief corrected | no | the belief, the record, the reason it persists | medium (must name what is wrong) |
| Hidden incentive | "Why printer ink is priced like that" | who benefits and how | no | the business model, with sources | medium (no accusation beyond the record) |
| Unexpected comparison | "A spoon of honey vs a bee's lifetime" | surprising scale | no | the real numbers, sourced | medium (check arithmetic) |
| Documented turning point | "The mistake that changed window design" | one event and what followed | no | the event and its documented effect | medium (sensitive if harm occurred) |
| Question | "Why is ice slippery?" | an open puzzle | no | the current best explanation, uncertainty shown | low (honest "scientists still debate") |

Rules: sentence case; no ALL CAPS, no "%", no "boring", no false urgency or fabricated stakes; keyword early; under about
60 characters where possible; the lane appears in the description and the channel name, not necessarily the title.
Rankings only when the topic is naturally a list. A title is never written before the script's promise is fixed.

## Thumbnail specification
How hard a thumbnail may pull (curiosity without deception) and the paid generation step: [THUMBNAIL_RULES](THUMBNAIL_RULES.md).
- Output: 1280 x 720 PNG, <= 2 MB (re-verify the limit when building it, Phase 7), made by `renderStill` from the
  episode's own assets; the editable source is the composition plus its props JSON. A finished image, not a mockup.
- Layout templates: T1 object + Kit's reaction; T2 before/after split; T3 cutaway (object with Kit's lid open).
- One focal object plus at most Kit; at most 4 words of text, Fredoka, ink on paper or paper on night (the text pairs in
  palette.json); `answer_coral` marks the key object; safe margin 10 %; keep the lower-right corner clear of the
  duration stamp.
- Reuse: Kit expressions and props from the asset library; a template change is a versioned decision, not an edit.
- Anti-patterns: stock faces, arrows pointing at nothing, more than two colours of text, text over detail, red circles,
  a different Kit than the sheet, any image or wording that promises what the video does not show.
- QA checklist (human + automatic): readable at 168 x 94 px; the text is legible in greyscale; the focal object is
  identifiable in under one second; the claim in the text appears in the video; no third-party IP; palette tokens only.

## What a "score" may and may not mean
A pre-publication review (our checklist), a tool heuristic (for example a vidIQ thumbnail score), real post-publication
analytics, and a formal YouTube experiment (Test and Compare, only if the feature is verified on the channel) are four
different things. A tool score is used only after we have read what it measures and whether it was validated; until then
it is logged as "heuristic, unvalidated" and never treated as a CTR probability. Manual before/after comparisons are
confounded by age, topic and traffic source and are labelled as such.

## Description, chapters, metadata
Description: a plain first paragraph that states the promise and the answer's shape; the source list with URLs; a
short note on how the video was made (narration is synthetic; script drafted with AI assistance and fact-checked against
the listed sources); chapters from the real timeline; no keyword stuffing, no links to unrelated products. Disclosure
decided by the checklist in [QA_SPECIFICATION](QA_SPECIFICATION.md) (D-16).

## First video (the prototype topic: onions; reopened by D-20 and D-25, kept until the new prototype topic is approved)
Candidate titles: "Why onions make you cry"; "What an onion does when you cut it"; "The onion's chemical alarm,
explained"; "Why your eyes water when you chop onions". Recommended: **"Why onions make you cry"** (plain hidden
reason, matches the first sentence, no promise beyond what the narration pays). Thumbnail concept: template T3, an onion with Kit's lid-open reveal showing two
compartments, Kit in goggles; text "Onion alarm" (a bare "WHY?" is rejected as empty). The actual image is produced in
Phase 7 and checked against the list above.
