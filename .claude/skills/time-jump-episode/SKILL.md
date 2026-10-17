---
name: time-jump-episode
description: Structure a Crossworld Theories episode that follows a premise across time (a day, a week, a month, a year, ten years, a hundred years) and ends by comparing it with the real record. Use when planning periods, their length, hooks, tone mix, reuse of pictures and the Shorts block of a production script.
---

# Time-jump episodes

**Episode rulebook first (D-45, OR-10):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role script` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Rules live in `docs/ORCHESTRATION.md` (SR-01..SR-08); this page is how to apply them.

1. **List the periods and give each a job**: what is the one problem it answers, what is its real bottleneck, what changes in the
   world. Weight minutes by surprise, not equally (a quiet year can be 40 s, a dangerous first night 2 minutes).
2. **Write the hook that closes each period** as the question the next period opens ("A month later: do they have a village or a
   graveyard?"). The first period opens with a yes/no question in 5 s (N-01).
3. **Tone mix**: 40 % drama, 20 % humour, 40 % doubt and curious telling. Count it per period; no period is all one tone.
4. **Named heroes carry the story** (UR-16..UR-21): who does what in each period, which friction between them, who is wrong.
5. **After the heroes die** (100 years): show their effect, not them: written knowledge, schools, tools, trade routes, descendants,
   a world visibly ahead of the real one, with the cost. Name what the real timeline had at the same date.
6. **The comparison chapter**: the real record's milestones against the group's, each with a source; the verdict is argued, the
   doubts stated, and it ends on the question the audience will argue about.
7. **Reuse plan** (SR-08): beside each shot say `unique`, `reuse:<picture id>` (new crop, zoom or speech bubble) or `emotion variant`.
   Dialogue between two named heroes uses one picture with bubbles (UR-31). A reuse must be a different moment of the story.
8. **Shorts block**: pick the 4 most surprising scenes + 1 trailer; write each short's hook and script (skill `shorts-for-video`).
9. Run `python -m explainer_engine.production validate` (PV-27 periods and PV-28 shorts included) and fix to 0 FAIL.
