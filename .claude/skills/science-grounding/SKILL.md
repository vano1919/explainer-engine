---
name: science-grounding
description: Ground a Crossworld Theories "what if" episode in real science, history and logic before any script is written - find sources by topic, build the claim map, label every statement established / reasoned / guess, and argue the counterfactual honestly. Use at the start of every episode and whenever a number or a "would X have happened" claim appears in a script.
---

# Science grounding for "what if" episodes

## Vendored methods (W8 phase B): when to load which

Load these at step 2 and step 8 of the procedure below, read whole, paste nothing:
- `v-source-verification`: SIFT and the durable evidence trail for any source, image, document or video you are unsure of.
- `v-fact-check-workflow`: pre-publication claim rating and the checks before an episode goes to the creator.
- `v-newsjack-fact-check`: lateral reading, source-tier climbing and a calibrated rating for each extracted claim.

**What stays ours:** the claim map (SCRIPTING_SPEC section 2), our four labels (`established`, `model`, `reasoned`,
`guess`), counterfactuals as arguments with premises by claim id, round-in-speech and exact-in-map numbers, and the
rule "two independent sources for every number". Upstream rating scales map onto our labels, they do not replace them.
**Not used:** any upstream step that publishes, emails, posts, or calls an account service; the PR-copy framing of
`v-newsjack-fact-check` (we check our own script, not a pitch).
**Checked by:** `scripting/claims.py` (claim map to PV-37, one source type is not a binding grade, D-59), the episode
rulebook gates (`standards`), and `scripting/story_lint.py` ST-09 for the objectivity label per segment.
**Known gaps (W2):** "a narrated sentence is not stronger than its claim" and "a numeric claim has two sources" have no
validator yet; the critic checks them by hand and says so.

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role research` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

The creator's brief (2026-10-16): lean on real science and logic, be creative in the telling. The audience trusts the channel
because the jokes never touch the facts (UR-21).

## Procedure
1. **Question first.** Write the episode's one question and the 3-6 sub-questions that decide it (for the time-jump Stone Age
   episode: is knowledge the bottleneck, or people, materials, tools, energy, food, disease?).
2. **Find sources by theme, from the whole web, best first**: peer-reviewed papers and reviews (Google Scholar, PubMed, arXiv,
   Nature/Science/PNAS news), museum and university pages, the Smithsonian, encyclopaedias (Britannica) for dates, books named in
   papers, and the economic-history literature for growth. Run several searches per sub-question; read the pages, never rely
   on a snippet. Prefer two independent sources for every number.
3. **Claim map** (`claim_map.md`/JSON in the episode folder, SCRIPTING_SPEC §2): id, sentence, source URL, access date,
   label. Labels: `established` (sources agree), `model` (a published model, name the model), `reasoned` (our inference from
   established steps; state the steps), `guess` (marked as a guess in the script by words like "probably", never as fact).
4. **Counterfactuals are arguments.** For every "they would have..." write premises (each a claim id), the step, the limit.
   Always name what could break it (population too small, no ore, no fuel, disease, an unlucky winter) and give both sides.
5. **Numbers**: round them in speech, exact in the map; compare with the real record only with dated sources (when did humans
   really get farming, bronze, iron, steam, printing, antibiotics; at what population).
6. **Cliché check**: the topic's popular myths ("a scientist can rebuild a gun in a week") are named and tested, not repeated.
7. **vidIQ** only for packaging questions (hooks, titles, outliers), within the run cap; facts come from sources.
8. Say at the end of the phase what was and was not verified (invariant 5).

## Candidate lines of evidence for "would a knowledge-rich group outpace history?"
Population and idea growth models (Kremer 1993 on population and technology; Romer on ideas; Boserup on intensification),
the size of the "minimum viable population" and its skills, the materials-and-tools chain (fire, clay, copper, charcoal, iron,
steel, glass, lenses) and the energy it needs, public-health limits (clean water, childbirth, infection), fiction-versus-history
"Connecticut Yankee" argument, and Leonard Read's "I, Pencil" (no one knows how to make everything). Verify each before use.
