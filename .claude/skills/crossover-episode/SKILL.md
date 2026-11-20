---
name: crossover-episode
description: Research and write a "worlds collide" crossover episode (two fictional or historical worlds meeting) from what the fans of both worlds actually discuss, balanced for casual viewers and hardcore fans, inside the rights rules. Use when the creator names two worlds to cross ("what if Westeros met Middle-earth", "Romans in a fantasy kingdom", "two games in one world") or asks for a crossover script, scenario or topic.
---

# Two worlds meet: fans, premise, script, rights (layers L29 and L30, stages S1-S3)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for crossover episodes made
on the v4.3 routes (D-131). The rights rules are RR-01..RR-16 in `docs/RIGHTS_AND_FAIR_USE.md` (binding, D-26); the
crossover script rules are `docs/SCRIPTING_SPEC.md` section 7; the limits are P-120..P-125 in
`docs/VIDEO_PARAMETER_SPEC.md`, with the quote and recap numbers in BP-77. This page links them; it never restates them.

**Rulebook first (D-51, OR-11):** `python -m explainer_engine.standards brief <episode>/episode_rules.json --role script`.
Legal, licence, likeness and art direction are decided there (docs/EPISODE_STANDARDS.md); conflicts go to the orchestrator.

## What we are making, and what we refuse to make

The target: the meeting that fans of both worlds have argued about and never seen done well, reasoned from each
world's own rules so a newcomer enjoys it too. Refused: "who would win" as the frame, a recap with a twist, a fan
sequel, a template with the names swapped. An episode that only sends characters on a new adventure shares the
source's purpose and is the weak legal case (RR-14); ours tests the worlds, it does not continue them (RR-01, RR-06).

## Stage 1: fan research before any idea of ours

Raw research (thread excerpts, comment notes) stays in gitignored `jobs/<slug>/research/`, never in the repository.
For each world:
- **Where fans argue:** the main subreddits and forums, threads on crossover, what-if, theory, unpopular opinion;
  sort by top and by controversial and read the comments, not the titles.
- **Canon facts:** fan wikis with page links for dates, geography, magic or tech rules, power scaling, economics.
- **What exists already:** crossover videos, fan-fiction indexes (titles and summaries only), forum takes. Note each
  angle so ours differs (P-125). Read; never copy wording, structure or art.
- **What viewers missed:** comments under the biggest existing crossover videos. vidIQ comment insights cost credits:
  estimate and log them in `docs/COST_AND_TIME_MODEL.md` before the call (invariant 2).
- **Primary canon:** the books and author interviews, quoted little (RR-04).

Record it all in `fan_brief.json` against `explainer_engine/schemas/fan_brief.schema.json` (sources with access dates,
theories with who proposed them and their canon status, fan demands, existing crossovers, canon rules, on-ramps, deep
cuts), then run `python -m explainer_engine.research.fan_brief jobs/<slug>/research/fan_brief.json` and fix every
FAIL (P-124 depth, P-125 originality). Canon facts that the script states also get claim rows (skill
`science-grounding`): a canon rule is `E` with its wiki or book link; our extrapolation is `R`; a fan theory is
credited and labelled as a theory (RR-07).

## Stage 2: premises, wide before narrow

At least twelve candidates before choosing. The obvious army battle is usually the take that already exists. Lenses
that open better ones:
- systems instead of fights: money, food, logistics, travel time, messages, law, faith, medicine, weather;
- one rule of world A dropped into world B (a single magic law, an institution, a creature);
- a small person crossing over: a merchant, a cook, a courier;
- second-order effects a year or ten years on (skill `time-jump-episode` when time is the engine);
- a popular fan theory taken as true, and the other world exposing it;
- the reverse direction, and the case where the meeting changes nothing, and why.

Score each 1-5 on surprise, fan payoff (does it answer a demand in the brief), casual clarity, visual drama, honesty
(can canon carry the reasoning) and rights safety (RR-01, RR-14). Keep the best; write why each other one lost. State
the commentary target in one full sentence: what the episode says about the source works themselves (RR-14).
`python -m explainer_engine.research.hypotheses jobs/<slug>/research/story_hypotheses.json` holds the premise
comparison honest (evidence and entertainment scored apart).

## Stage 3: the script (SCRIPTING_SPEC section 7, on top of sections 1-6)

- **Hook:** the collision in one concrete image and one sentence; no greeting, no "who would win" (BP-03 forms).
- **Two audiences:** on-ramps for newcomers inside the story, one or two lines each, never a lecture; deep cuts for
  fans: credited theories, small canon details, a callback the fandom knows. Tag every beat `casual`, `fan` or `both`
  and check with `fan_brief.check_balance` (P-123).
- **Reasoned forward:** play the scenario step by step from the canon rules, label speculation, raise the best fan
  counter-argument and answer it.
- **Payoff:** an arguable conclusion and the open question fans will fight over in the comments; no subscribe plea.
- **Limits:** recap only what the analysis needs (P-120, RR-05); quotes short, attributed and analysed (P-122, RR-04).
- **Stock phrases:** run `fan_brief.template_flags` over the narration and keep a flagged phrase only if it truly is
  the best wording.

## Pictures and clips under the rights rules

Pictures come from the Gemini chat's image tool as turn packs (`explainer_engine/imagegen/turn_pack.py`, D-131); clips
follow the video lane (D-132, D-137). On top of the usual picture rules:
- Our own interpretations from text only: never a production's character designs, costumes, sets, props, actor
  likenesses or official maps (RR-03). No prompt names the franchise, a character or an actor.
- Official screenshots, trailer frames and key art are private study only, never an image input or reference upload
  to any generator (RR-15).
- Parody brands and the franchise name are narrative props only, never on anything sold (RR-16).
- Thumbnails: our art only, no actor faces, key art, logos or screenshots (RR-09).
- Music and effects: own, CC0 or licensed with a record; never a franchise theme or a sound-alike (RR-11).

**Conflict to report, not settle:** rule 20 names the series' era film in every picture prompt; RR-03 forbids naming
a franchise or "in the style of" one. In a crossover the named film can never be one of the crossed works or its
adaptations. Whether naming any other film is acceptable in a franchise episode is the creator's call (OR-22): ask
before the first turn pack, record his answer in the rulebook.

## Stage 4: rights manifest and check

Write `rights_manifest.json` against `explainer_engine/schemas/rights_manifest.schema.json` and run
`python -m explainer_engine.rights.ip_check jobs/<slug>/rights_manifest.json`. Any FAIL blocks the package; every
REVIEW gets a written answer. Name the manifest in the rulebook (`execution.rights_manifest`, ES-17) so the rulebook's
gate merges these findings. The description carries the unofficial note (RR-08). The check lowers risk and proves
nothing about fair use; the creator carries the decision.

## Stage 5: stop for the creator (approval #1, OR-15)

Hand over the fan brief summary, the chosen premise with the losers and why, the commentary target, the script with
beat tags, the balance and template reports, the claim map and the rights report. Nothing goes to pictures, reads or
clips before his approval (`explainer_engine/scripting/script_approval.py`, OR-17).

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| fans would call it "seen it" | premise picked before the brief | redo stage 2 from the brief's existing takes |
| newcomers lost in minute one | on-ramps missing or a lecture | one in-story line per new rule, beat tagged `casual` |
| ip_check FAIL on `art` | a prompt named a character or used a still | rewrite from text, drop the reference image |
| recap REVIEW | plot summary carrying the episode | cut to what the test needs |
| a theory stated as canon | label lost | credit the author, label it a theory |

## Real-world crossovers

When one world is real history (Romans in a fantasy kingdom), the historical side follows the claim map like any
docudrama (skill `science-grounding`), real living people stay unvoiced (D-62), and the RR rules still bind the
fictional side.
