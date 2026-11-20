---
name: science-grounding
description: Ground a Crossworld Theories "what if" episode in real science, history and logic before any script is written - find sources by topic, build the claim map, label every statement established / reasoned / guess, and argue the counterfactual honestly. Use at the start of every episode and whenever a number or a "would X have happened" claim appears in a script.
---

# Grounding an episode in the record (layer L1, stage S1)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the v4.3 episode folder
(D-131): the claim map lives in `episodes/<id>/story/claim_map.md`, every factual sentence of the script points at one of
its rows, and the runner's G1 reads it. This page is the method; the rules it serves live in their own homes and are
linked, never copied.

## What this page owns, and what it does not

Owns: the episode's question, the research pass, the claim map and its labels, the honest counterfactual, and the
closing statement of what was and was not verified (invariant 5). Does not own: how the narrator says it (skill
`narration-script`), how heroes speak (skill `dialogue-scenes`), the story spine (skill `story-engine`), rights of
someone else's fiction (skill `crossover-episode`). The episode rulebook comes first (D-51, OR-11): run
`python -m explainer_engine.standards brief <episode>/episode_rules.json --role research` and follow it; a conflict with
this page goes back to the orchestrator, it is not settled here.

The creator's line (2026-10-16): real science and logic underneath, creativity in the telling. The jokes never touch a
fact (UR-21); that is why viewers trust a channel that also invents heroes.

## The labels (one per claim row)

| Label | Letter in the map | Means | What the script may do with it |
|---|---|---|---|
| established | `E` | sources agree; a link is in the row | state it plainly |
| model | `M` | one published model or one study; name it | state it as that model's or study's finding |
| reasoned | `R` | our inference from established rows; the steps are written | argue it, with the premises visible |
| guess | `G` | plausible, not supported | only with a hedge word the ear hears ("probably", "maybe") |
| invention | `I` | the episode's own creation: composite heroes, their lines, a prop | never presented as a quote or a record; the description says so |

`explainer_engine/scripting/claims.py` reads exactly these letters (PV-37): a line's claim id must resolve, an `E` or
`M` row without a link is REVIEW, a number in a line without a claim id is REVIEW. The SCRIPTING_SPEC confidence words
(verified, corroborated, single-source, unverified, section 2) sit beside the label in the dossier; the editorial gate
(`explainer_engine/production/editorial_gate.py`) maps its claim types onto the same letters.

## Procedure

1. **One question, then its deciders.** Write the episode's yes/no question and the three to six sub-questions that
   settle it (for a truce episode: where did it happen, who started it, how many took part, how did it end).
2. **Search by sub-question, best tier first:** primary records and papers, museum and university pages, established
   references for dates (Britannica-level), then good journalism. Several searches per sub-question; open the page,
   never trust a snippet for a number.
3. **Use the researchers we have.** Gemini and Argon research is about 90 % reliable (creator, 2026-11-07): apply it as
   guidance at once, distrust only claims that are absolute and unverified, and write down which claims you did not
   open yourself. Default suspicion of their work is the wrong habit.
4. **Write the claim map** as you read: `| C-01 | sentence as narrated | label | source URL(s) |`, invented rows as
   `I-01`. The header line of the file says the access date and who read what. `research_dossier.md` beside it records
   which pages were opened and which came from summaries (see `episodes/ep_truce_1914/story/` for a finished pair).
5. **Two source types make a number binding.** D-59's rule for the registry carries over to the map: an important
   number wants two independent sources, or one primary (grade A in SCRIPTING_SPEC section 1). A single source keeps
   the row honest but marks it single-source, and the narration rounds or hedges it.
6. **Counterfactuals are arguments.** For each "they would have...": premises as claim ids, the inference step, the
   limit. Name what breaks it (too few people, no ore, no fuel, disease, a bad winter, an order from above) and give the
   strongest case on both sides. Label the result `R`, or `G` when the chain has a gap.
7. **Numbers: round in speech, exact in the map.** A map shot that shows a number names its claim id (MA-04); G1
   checks it (`map_numbers_have_claims` in `explainer_engine/episode/run.py`).
8. **Test the myths.** The topic's famous version ("the whole front stopped", "a scientist rebuilds a rifle in a week")
   is named and tested against the rows, never repeated because it is famous.
9. **Packaging data is not evidence.** vidIQ answers hook, title and outlier questions inside its run cap; facts come
   from sources only.
10. **Close the phase in writing:** what was verified by opening the page, what came from summaries, what was not
    checked and what it affects (often only a picture prompt). This sentence goes to the creator with the script.

## Real people and invented people

- An invented composite hero is fine (owner policy for docudrama, 2026-11-16) when its row is `I` and the description
  and pinned comment say so; its letters, photos and lines are our text, never a "quote".
- A real living person never gets a synthetic voice (D-62, ES-08); their words are reported by the narrator (D-63).
- A real dead person may speak in a played scene only in lines the record supports; the line cites the row it rests on.
  A realistic depiction of a real person turns the disclosure checklist on (D-16, ES-08).
- No reenacted face "proves" a fact: the proof is the row, the picture only shows the action.

## Vendored methods: when to open which

| Moment | Open | For |
|---|---|---|
| a source, image or document you are unsure of | skill `v-source-verification` | SIFT, provenance, the evidence trail |
| before the script goes to the creator | skill `v-fact-check-workflow` | the pre-publication claim pass on our map |
| a claim that sounds too neat, or a stale "latest" | skill `v-newsjack-fact-check` | lateral reading, tier climbing, calibrated status |

Their rating scales map onto our five letters; they never replace them.

## Checks in code, and the gaps

- PV-37: `explainer_engine/scripting/claims.py`, run by `python -m explainer_engine.production validate <script>`.
  The v4.3 runner's G1 (`python -m explainer_engine.episode run <episode> --stage script`) loads the same map for the
  numbers shown on map shots (`map_numbers_have_claims`); it does not replace the PV-37 run.
- ST-09 objectivity per segment: `explainer_engine/scripting/story_lint.py` (invention never the majority; a segment
  labelled fact carries claim ids).
- The source/claim contract and the independent review: `python -m explainer_engine.production.editorial_gate
  <script> --review <review.json>` (EG rules).
- Story premises compared fairly before the treatment:
  `python -m explainer_engine.research.hypotheses jobs/<slug>/research/story_hypotheses.json`.
- Not in code yet: "a narrated sentence is never stronger than its row" and "a binding number has two sources". The
  critic checks both by hand (skill `story-engine`, critic page) and says that it did.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| a vivid line with no row | written from memory | find the row or cut the line |
| "historians agree" with one link | one source dressed as consensus | relabel `M`, name the source in the dossier |
| the narration states a `G` row flatly | hedge lost in a rewrite | restore the hedge or upgrade the evidence |
| the counter on a map has no claim | number typed into the shot | add `claim` on the action, G1 re-checks |
| a composite hero reads as a real man | missing `I` row or disclosure line | add both before approval |

## Candidate evidence for a "would a knowledge-rich group outpace history?" episode

Population and idea growth (Kremer 1993; Romer on ideas; Boserup on intensification), minimum viable population and
skills, the materials chain (fire, clay, copper, charcoal, iron, glass, lenses) and its energy, public-health limits,
the "Connecticut Yankee" argument, Leonard Read's "I, Pencil". Each one is opened and given a row before use.
