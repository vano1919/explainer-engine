You are an independent principal engineer and film-production expert, and a hard critic. Answer in ONE reply; this chat has room for only this one exchange, so do not ask me questions first. Answer in English; documents in Georgian are fine to read.

ATTACHED (read only what you need, start with the READMEs):
- `repo_text_PR188_302c8dd.zip`: all text files of my repo "Explainer Engine" at its newest state (rulebook `CLAUDE.md`, index `docs/INDEX.md`, episode runner `explainer_engine/episode/run.py`, 2.5D code `explainer_engine/production/` (`layers25d.py` = current default, `directed25d.py`, `living*.py`, `understand.py`), LTX chain `finish/frame_pick`, `finish/superres`, `videolane/`, `training/pods/ltx/`).
- `notes_knowledge_plan_journal_PRs_v2.zip`: `README_PACKAGE.md`, knowledge base `project_knowledge/` (01 state, 03 decisions, 04 requirements, 12 problems, 14 contradictions), plan `plan/FINAL_SCENE_AWARE_CINEMATIC_PRODUCTION_ROADMAP_2026-11-14.md`, `plan/PRUNE_LOG_2026-11-14.md` (removed items are settled), living-photo rules, sound guide, incident journal, diffs of open PRs #184-#191, `history_argon/` (your earlier tasks).

THE PROJECT IN 5 LINES: a solo creator's YouTube channel of hand-drawn "worlds collide" history explainers for a US audience. Current episode: the "Truce 1914" demo film (~ several minutes). Visual mix is fixed: 60 % real video (LTX-2.5 on a rented H100, paid, clips already made), 30 % still pictures (Gemini, already made) brought to life in 2.5D by free Python (each <= 5 s, cut on narrator words), 10 % helper visuals (maps, counters, progress bars, chosen by what the narration says), plus narration (ElevenLabs) and sound. Assembly is paused because the 2.5D clips went from "just a zoom" to "static" to "seams, cropping, weak or blown-out effects", and gates passed clips the creator rejected by eye.

THE CREATOR'S OWN DIAGNOSIS (today): we cannot assemble the video start to finish because (1) the maps are poor; (2) text, narration, sound and theme do not line up with each other; (3) map-to-map transitions jump; (4) the photos are often static (a few are good). Your earlier output for this project was richer: it went photo to photo with logical transitions, scene by scene, driven by the script. That is the quality bar.

THIS IS SESSION 1 OF A LOOP: you now build the knowledge base and the plan; Claude Opus will check the plan (and ask you back, not dismiss your facts); later fresh sessions of you will write the code and review it. So make the knowledge base and plan self-contained enough to hand to a fresh session.

THE ONE QUESTION: How do we finally make this video in parts (60 % LTX / 30 % 2.5D / 10 % helpers / narration / sound) and assemble them into ONE good, watchable, story-first film, with a pipeline that repeats for the next episodes with little manual work?

Use your YouTube, web, Wikipedia and GitHub access: look for proven tutorials and open-source tools for (a) 2.5D/parallax "living photo" animation from a single still (depth layering, inpainting the reveal, subtle particles/weather, camera moves) that looks professional rather than a Ken Burns zoom; (b) mixing AI video clips with animated stills so the cuts feel like one film (matching grade, motion continuity, cut on words, J/L cuts); (c) how successful documentary/explainer channels (e.g. Kurzgesagt-style, history-doc channels, the "faceless" AI-history channels) structure, pace and sound-design such a mix; (d) automatic QA that catches what a human sees (seams, stretched edges, frozen frames, blown-out highlights). Name the sources you used (title + link).

GIVE ME, SHORT AND STRUCTURED (target under 2500 words):
1. 6-10 lines in Georgian for the creator: verdict and the first three steps.
2. Verdict on our current approach (3-5 sentences): what is fundamentally right or wrong, judged against the code, not only the plans.
3. The 2.5D lane: the concrete technique you recommend (tools/libraries, models, parameters), why ours fails today (quote file + line), and a minimal free CPU (or cheap) recipe per shot type: landscape, group of people, close face, object.
4. Assembly: the end-to-end recipe (order, grade matching, transitions, cut rules, sound layers, loudness target), and which of our existing modules to keep, fix or drop.
5. QA that matches the human eye: 5-8 checks with how to measure each and a starting threshold (say "hypothesis" when it is one).
6. An ordered plan of at most 8 steps: each = goal, files touched, free or paid (with an estimate), done-when.
7. Why your earlier work for this project was rated better than Claude's: what in the way you worked (inputs, scope, use of external sources, independence) should we copy into how we brief you and Claude.
8. NOT CHECKED: what you could not verify.

Sections 3-5 must also cover the maps (rich, readable, animated maps and smooth map-to-map transitions) and the alignment of narration, text on screen, sound and theme per scene.

If you can, also return files: `KNOWLEDGE_BASE.md` (the proven techniques and sources you found, organised by lane: 2.5D, LTX clips, maps/helpers, transitions, sound, story/pacing, QA, YouTube fit), `PLAN.md` (sections 2-6) and any short Python/pseudo-code sketches of the 2.5D recipe and the QA checks. Be direct and specific; no praise, no generic advice. Do not spend effort on budgets, merging PRs or team process beyond item 7.
