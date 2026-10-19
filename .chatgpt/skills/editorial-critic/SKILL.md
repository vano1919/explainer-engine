---
name: editorial-critic
description: Independently score an exact Crossworld Theories production script against factual, narrative, visual, audio/edit and packaging requirements before paid TTS or asset generation. Re-run after every material script revision.
---

# Editorial critic: reject weak scripts before production cost

Read docs/SCRIPTING_SPEC.md, docs/PRODUCTION_RULES.md, docs/UNIVERSAL_RULE_BASE.md, docs/PRODUCTION_SCRIPT.md, and the rights document for any third-party fictional world.

## Independence

- Review the actual current script, not the author's summary.
- Do not inspect self-scores or prior review results before scoring.
- Do not rewrite the production script. Return findings for the author/orchestrator to resolve.
- Inspect source passages for material facts. A search snippet, URL, source title or authoritative-sounding publisher label alone is not enough.
- Bind the review to the exact script bytes with SHA-256. Any edit invalidates the prior report.
- The independent=true field is a workflow declaration, not cryptographic proof. Use a separate reviewer context with no access to the author's desired verdict.

## Assess every existing rubric criterion

Use the 1-5 anchors from docs/SCRIPTING_SPEC.md and produce evidence notes for all 13 exact keys:
factual_reliability, clarity, story_coherence, hook, relevance, originality, spoken_naturalness, visual_potential, humour_fit, pacing_potential, source_coverage, title_thumbnail_alignment and shorts_potential.

Keep the current gates: factual reliability, source coverage and title/thumbnail alignment at least 4/5; every other criterion at least 3/5; overall mean at least 3.8/5. No numerical score cancels a critical blocker.

### Fact and reasoning review

- Every narration line classified as fact, analysis or speculation maps to claim IDs.
- The narrated claim, source passage and scope agree on dates, people, numbers, units and certainty.
- Material factual claims use one grade-A primary source or at least two independent grade-B/C publishers. Grade-D sources only suggest leads.
- Distinguish fact, estimate, interpretation, allegation and speculation. Counterfactual reasoning may be creative but must state assumptions and limits.
- Look for outdated numbers, missing counterevidence, cherry-picked comparisons, false precision, causal claims supported only by correlation and jokes that change factual meaning.
- Rights problems are blockers, not something a high originality score can offset.

### Story review

- A new viewer understands the premise early.
- Named characters have goals, friction, consequential choices and distinct reactions.
- Each beat changes the story state or understanding. Flag filler, repeated facts, disconnected jokes, fake stakes and loops that never pay off.
- The title promise is answered clearly and on time.
- Narration sounds spoken and has usable moments for emphasis, reaction, pause, reveal and silence.
- Visual plans show the action and exact story state at the spoken anchor, not generic scenery or future events.
- Shorts have their own hook and payoff and use the same verified evidence.

## Finalization

Write editorial_review.json beside the exact script. Set truthful scores and evidence notes; populate critical_blockers and required_revisions honestly. Then run:

.venv\Scripts\python -m explainer_engine.production.editorial_gate <production_script.json> --review <editorial_review.json>

A gate pass checks structure, hash binding and rubric thresholds. It does not prove sources are true, prove independent identity, or replace listening to and inspecting the finished video.