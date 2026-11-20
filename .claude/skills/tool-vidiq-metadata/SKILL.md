---
name: tool-vidiq-metadata
description: Write the long video's title, description, tags and chapters for a US audience with the vidIQ connector as a research and drafting aid - balance read first, every credit-spending call priced in the ledger and asked of the owner, drafts that only promise what the episode pays, chapters taken from the measured read clock, everything landing in publish.json and passing the free publish checklist. Use when an episode reaches packaging, when a title or description is drafted or challenged, when chapters are made, and before any vidIQ call that might spend credits.
---

# vidIQ metadata, the tool (layer L27, packaging after G10)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the packaging step of a
v4.3 episode: the words that ship with the upload. vidIQ helps research and draft; our files and checks decide. The
thumbnail is skill `v-thumbnail-skill`; the upload itself is skill `tool-youtube-upload`; Shorts copy is skill
`shorts-for-video`; facts in the description go through skill `v-fact-check-workflow`.

## When to use, when not

- Use once the master passed G10 and the script's promise is frozen: a title is never written before that
  ([docs/TITLE_THUMBNAIL_SYSTEM.md](../../../docs/TITLE_THUMBNAIL_SYSTEM.md)).
- Use vidIQ only for a question whose answer would change a word: which of two phrasings people search, whether a title
  reads as a duplicate of a big video, what a chapter list of the measured read should be called.
- Not for uploading, editing a live video, thumbnails, music, voice-overs or social posts, even though the connector
  offers them (`vidiq_video_upload`, `vidiq_update_video`, `vidiq_generate_thumbnail`, `vidiq_social_post_publish` and the
  like): uploads go only through `publish/` (invariant 4, D-57); our pictures and sounds have their own tools.

## Credits: free versus paid

vidIQ credits are counted in the ledger of [docs/COST_AND_TIME_MODEL.md](../../../docs/COST_AND_TIME_MODEL.md) until they
get a line in `config/spend_caps.json` (invariant 2); the project cap there is 200 credits and most of it was spent in
October, so the remaining room is small.

1. Call `vidiq_balance` first. It cost 0 credits when measured (MARKET_RESEARCH V-06).
2. Treat every other call as credit-spending until a balance read before and after proves it free. Measured in this
   project: an outlier search, a keyword research, a transcript and an analytics call each cost 5 credits; video watches
   and comment insights cost more. Generation tools (`vidiq_generate_titles`, `vidiq_generate_video_chapters`,
   `vidiq_compose`, `vidiq_score_title`) are not yet measured here: do not assume they are free.
3. Before a spending batch: write the planned credits and the question it answers into the vidIQ spend log, show the owner
   the batch and its cost, wait for his word, then call; fill the actual from `vidiq_balance` after. Stop at 80 % of the
   cap. `vidiq_credit_usage_list` reconciles a surprise.

## The procedure

1. **Read the episode**: the approved script's promise and cold open, the claim map, the measured clock
   (`audio/timing.json` from G6), the Shorts plan. The title promises what the first 30 seconds confirm (BP-04).
2. **Draft three titles** of different mechanisms from the pattern library (hidden reason, turning point, question...):
   English for the US audience, sentence case, no all caps, no false urgency, the keyword early, short enough to read on a
   phone. Optional, if the owner allows the credits: score or search the phrasing with vidIQ.
3. **The description**: the first line restates the promise in plain words (it is what shows above the fold), then what
   the episode covers, the source line (PC-07), the disclosure wording when the checklist asks for it (PC-03). Every
   factual sentence maps to a claim-map row; no claim the episode does not support (invariant 5).
4. **Chapters from the clock, not from a model's guess**: boundaries at segment and scene turns on the measured read;
   each title is the promise of that section in a few words. `publish/plan.py` appends the chapter block to the
   description itself. A vidIQ chapter draft is a starting list only, re-timed to our clock.
5. **Tags**: the exact search phrase first, then the era, the event, the people, the format; `plan.fit_tags` keeps the
   ones that fit YouTube's count and reports the rest. Hashtags stay few.
6. **Write `<episode>/publish.json`** (schema `publish/1`, `explainer_engine/schemas/publish.schema.json`): title,
   description, chapters, audience, disclosure, tags, thumbnail.
7. **Check for free**: `python -m explainer_engine.qa.publish_check <episode>/publish.json --episode <episode>`. Fix every
   FAIL; show REVIEW rows to the owner. Then the owner picks the title.

## Hard rules at this layer

- The chapter rules are PC-01 (first at 0:00, at least three, ascending, each long enough; Help 9884579), enforced in
  `explainer_engine/qa/publish_check.py`; cite PC-01 instead of restating numbers. Field limits are PC-06 and the
  `videos.insert` rules in `explainer_engine/publish/plan.py`; `<` and `>` are refused.
- No clickbait the episode does not pay: no promise, number, "secret" or villain the video does not deliver; misleading
  metadata breaks YouTube policy (Help 2801973, read by `publish_check`) and the channel's own honesty rule.
- Audience is "not made for kids" (PC-02); the disclosure is decided per video by the checklist (PC-03).
- Everything the viewer reads is English; Georgian only in the talk with the owner.
- No competitor title is copied; patterns are adapted.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| Chapters do not show on YouTube | a PC-01 rule broken | run `publish_check`; re-time from the clock |
| A title the first minute does not pay | written before the promise froze | rewrite from the cold open (BP-04) |
| Credits gone after "just a check" | a spending call assumed free | balance before and after; log it; ask first |
| Description states a number the script hedges | words outran the evidence | match the claim row's label |
| vidIQ suggests trend words off topic | generic seed | drop them; our topic decides |

## Sources (what each taught; licence noted in one line)

- ericrisco/rsc-harness, page `youtube-packaging` (MIT, commit `28a51a9100`): read the channel and the video before
  writing; a small title set; an above-the-fold first line; the first tag as the exact phrase.
- Jakeschincariol/youtube-agent-skill, page `yt-chapters` (MIT, commit `a2feb21049`): chapter lists fail silently when
  a rule breaks; retitle every boundary as the section's promise.
- TheCraigHewitt/skills, pages `description-seo` and `title-craft` (MIT, commit `fdbf39b61f`): description structure.
