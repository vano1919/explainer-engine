---
name: crossover-episode
description: Research and write a "worlds collide" crossover episode (two fictional or historical worlds meeting) from what the fans of both worlds actually discuss, balanced for casual viewers and hardcore fans, inside the rights rules. Use when the creator names two worlds to cross ("what if Westeros met Middle-earth", "Romans in a fantasy kingdom", "two games in one world") or asks for a crossover script, scenario or topic.
---

# Crossover episode: fan research -> scenario -> balanced script -> rights check

**Episode rulebook first (D-45, OR-10):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role script` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

The goal is the scenario fans of both worlds have argued about and never seen done properly, explained so a newcomer
enjoys it too. Not a generic "who would win", not a recap, not a template with names swapped.

Read first: `docs/RIGHTS_AND_FAIR_USE.md` (RR rules, binding), `docs/SCRIPTING_SPEC.md` section 7, P-120..P-125 in
`docs/VIDEO_PARAMETER_SPEC.md`. Output goes to `jobs/<slug>/research/` (gitignored), never into the repo.

## 1. Fan research (do this before any idea of your own)
Work from the sources fans use, for each world:
- Community discussion: the main subreddits and forums of each world, threads on "crossover", "what if", "who would win",
  "unpopular opinion", "theory"; sort by top and by controversial, read the comments, not only titles.
- Fan wikis for canon facts (dates, geography, magic rules, power scaling, economics), with page links.
- Existing crossovers: YouTube videos, fan fiction indexes (titles and summaries only), forum threads. Note each one's
  angle so ours is different. Read; never copy wording, structure or art.
- YouTube comments under the biggest existing crossover videos: what viewers say was missing or wrong. If vidIQ is used
  (comment insights, 5 credits per call), log the cost in `docs/COST_AND_TIME_MODEL.md` first.
- Primary sources where they exist (the books, author interviews) for canon rules; quote little (RR-04).
Record everything in `fan_brief.json` (`explainer_engine/schemas/fan_brief.schema.json`): sources with access dates,
theories (who proposed them, how popular, canon status), what fans ask for, existing crossovers and their angles, canon
rules per world, casual on-ramps, deep cuts. Then run:
`python -m explainer_engine.research.fan_brief jobs/<slug>/research/fan_brief.json` and fix every FAIL.

## 2. Scenarios with maximum imagination
Generate at least 12 candidate premises before choosing. Push past the obvious: the obvious one is usually the army
battle every existing video already did. Useful lenses:
- systems instead of fights: money, food, logistics, travel time, communication, law, religion, medicine, weather;
- a single rule of one world dropped into the other (one magic law, one political institution, one creature);
- a small person, not a hero: a merchant, a cook, a messenger crossing over;
- second-order effects: what changes a year later, ten years later;
- fan theories as engines: what if the popular theory is true, and the other world exposes it;
- the reverse direction, and the case where the meeting changes nothing (and why that is interesting).
Score each premise 1-5 on surprise, fan payoff (does it answer a demand from the brief?), casual clarity, visual drama,
honesty (can the reasoning be sourced from canon?) and rights safety (RR-01: is it analysis?). Keep the best; record why
the others lost. Reject a premise that the brief's existing crossovers already cover (P-125).

## 3. Script (follow SCRIPTING_SPEC section 7)
- Hook: the collision in one concrete image and one sentence, no greeting, no "who would win".
- On-ramps for casual viewers inside the story (who these people are, what the rule is) in one or two lines each,
  never a lecture; deep cuts for fans (named theories with credit, small canon details, a callback the fandom knows).
- Tag every beat `casual`, `fan` or `both` in `beats.json`; check with `fan_brief.check_balance` (P-123).
- Play the scenario forward step by step from the canon rules; show the reasoning; label speculation; include the best
  counter-argument a fan would raise, and answer it.
- Payoff: a clear, arguable conclusion and the open question fans will debate (that is the comment section, not a
  "like and subscribe" plea).
- Recap only what the analysis needs (P-120); quotes short and analysed (P-122).
- Run `fan_brief.template_flags` over the narration and remove stock phrases unless one is really the best wording.

## 4. Pictures: simple doodle + dramatic scenes
Doodle for explanation (the traveller mascot, diagrams, maps we draw, comic beats); a few dramatic establishing scenes for
the big moments (landscapes, light, scale). All our own drawings; characters are our interpretations from text, never
the productions' designs, costumes or actors; no generator prompt names a franchise or character (RR-03).

## 5. Rights manifest and check
Write `rights_manifest.json` (`explainer_engine/schemas/rights_manifest.schema.json`) and run
`python -m explainer_engine.rights.ip_check jobs/<slug>/rights_manifest.json`. Any FAIL blocks the package; answer each
REVIEW in writing. Name the manifest in the episode rulebook (`execution.rights_manifest`, ES-17): its gate merges these findings. The description gets the unofficial note (RR-08).

## 6. Stop for the creator (approval #1)
Hand over: the fan brief summary, the chosen premise and the rejected ones, the script with beat tags, the balance and
template reports, the rights report. Nothing goes to storyboard or render before the creator approves.

**Rights rules added 2026-10-17 (RR-14..RR-16):** state the commentary target first (what the episode says about the source work), never feed official images to a generator, keep parody brands as props only. See `docs/RIGHTS_AND_FAIR_USE.md`.
