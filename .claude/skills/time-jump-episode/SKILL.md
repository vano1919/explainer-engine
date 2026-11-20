---
name: time-jump-episode
description: Structure a Crossworld Theories episode that follows a premise across time (a day, a week, a month, a year, ten years, a hundred years) and ends by comparing it with the real record. Use when planning periods, their length, hooks, tone mix, reuse of pictures and the Shorts block of a production script.
---

# Episodes that jump through time (layer L30, stage S2)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the v4.3 episode folder
(D-131). The format rules are SR-01..SR-08 in `docs/ORCHESTRATION.md`; this page is how a writer applies them inside the
writers' room (skill `story-engine`), without restating them.

**Rulebook first (D-51, OR-11):** run `python -m explainer_engine.standards brief <episode>/episode_rules.json --role script`
and follow it. Law, licences, likeness and art direction are decided there (docs/EPISODE_STANDARDS.md); a conflict goes
back to the orchestrator.

## When this format fits, and when it does not

Fits: one premise whose interest grows with time ("a group with modern knowledge lands in the Stone Age: a night, a month,
a year, a century"), where every jump changes the problem. Does not fit: a single event told minute by minute (that is a
plain docudrama, skill `v-sw-story-structure`), or two worlds meeting (skill `crossover-episode`). A time-jump episode is
still one question with chapters (SR-01), not a list of eras.

## Procedure

1. **Name the one question and the final comparison first.** The last chapter sets the real record against the group's
   (SR-01); knowing that verdict's shape tells you which periods are worth showing.
2. **Give each period a job card:** the one problem it answers, its real bottleneck (people, materials, tools, food,
   disease, energy, trust, SR-05), and what in the world changes because of it. A period without a new problem is cut.
3. **Weight minutes by surprise (SR-02).** A dangerous first night can take two minutes, a quiet decade forty seconds.
   The length falls out of the surprises; it is never split evenly.
4. **Close every period on the next one's question (SR-03).** "A month later: a village, or a graveyard?" The opening
   asks its yes/no question inside the hook window (N-01, BP-03's forms).
5. **Ground each jump (SR-04).** Every "after a year they would have..." is an argued chain in the claim map:
   established rows, reasoned steps, labelled guesses (skill `science-grounding`). The comparison chapter cites dated
   rows for the real milestones (farming, bronze, iron, printing, steam, antibiotics, and the population at each).
6. **Tone per period (SR-07).** Mostly drama, doubt and curious telling, humour at BP-09's density and placement,
   never inside the explaining example, never on a fact (UR-21). Count the mix per period; none is all one tone.
7. **Named heroes carry each period (UR-16..UR-21).** Who acts, who argues, who is wrong. Their talk follows the scene
   contract (skill `dialogue-scenes`); in v4.3 each hero line is spoken inside its own video clip (D-131, D-137).
8. **After the heroes are gone (SR-06).** At a hundred years show their effect, not them: schools, written knowledge,
   tools, trade, descendants, and the cost. Say what the real timeline had at that same date.
9. **The comparison chapter.** Milestone against milestone, each with its row; the verdict argued, doubts stated, and
   the closing question the comments will fight over. The creator's next-episode question only if he set one.
10. **Reuse plan (SR-08).** Beside each shot write `unique`, `reuse:<picture id>` or `emotion variant`, and the reason in
    story terms: a reuse must be a different moment, never a saving against the story. See the route note below.
11. **Shorts block.** Pick the four most surprising scenes plus one trailer and write each one's hook and lines (skill
    `shorts-for-video`); PV-28 checks the block.
12. **Validate.** `python -m explainer_engine.production validate <script>` covers PV-27 (periods consecutive, each
    period's last line opens the next question, the tone mix) and PV-28 (the Shorts); fix to zero FAIL. Then the v4.3
    runner's G1: `python -m explainer_engine.episode run <episode> --stage script`.

## Reuse in the v4.3 routes

The three routes change what "reuse" costs (D-131, D-132):

| Route | What a reuse looks like | Watch |
|---|---|---|
| `still_25d` | the same approved picture with a new crop, push or layer move | a different story moment, not the same beat twice |
| `video` | a new clip from an approved start picture of the same place | continuity of the place and heroes (skill `v-director-cinematic`) |
| `map_action` | one base map, new arrows, dates and counters per period | each period's date on screen; every number has a claim (MA-04) |

The old rule that two heroes in dialogue share one picture with speech bubbles (UR-31) belongs to the legacy still
picture route. In v4.3 a dialogue scene cuts between clips where each hero speaks his own line; bubbles stay only for
a real living person's silent line (D-62, PV-56).

## Hard rules that bite here

- Periods are chapters of one question; never a museum walk (SR-01).
- A jump that changes nothing is cut, however good its pictures.
- The time on screen is always readable: a date or "a year later" chip at every jump.
- A century-scale claim is still a claim: row, label, hedge.
- Sound: each period keeps one continuous bed for its place; a jump is where the bed may change (skill `v-design-sound`).

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| the middle sags around year ten | equal minutes per period | re-weight by surprise, cut the flat period |
| the ending feels like a list | comparison not argued | one verdict, the strongest doubt, one open question |
| "they invent steam in year three" | knowledge treated as the only limit | name the bottleneck (SR-05) and argue it |
| the same picture shows up as filler | reuse chosen for cost | give the reuse a new moment or make it unique |
| PV-27 FAIL on period order | segments of one period split apart | make each period's segments consecutive |

## Not used here

Upstream story-structure templates with acts of fixed length (the time-jump spine is driven by period surprise), and
any picture plan from the legacy routes (Qwen-Image, the Blender J5 shots; legacy since D-131).
