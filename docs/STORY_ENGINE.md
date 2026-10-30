# Story engine: story, dialogue, motion, sound layers, voices, Shorts (D-48)

The creator's notes of 2026-10-19:
- The first video told a less interesting story than it could have and missed what viewers want. Facts and people's basic needs must be balanced.
- The edit was slow, not animated and boring. It needs frequent picture changes, not only photos joined by standard transitions.
- The sound layers must not turn into noise.
- ElevenLabs voices should be found automatically from a hero's character. For a real person, the voice should follow what that person was really like.
- All of this is planned while the script is written and comes together in the edit.
- A mid-size model (Claude Sonnet) does the work, so the framework has to hold it on course.
- The format is a mini-entertainment with dialogue that shows an alternative reality, on topics that change often.
- Each video gets 10 Shorts in different styles that promote it.

This document is the canonical home of the ST, DW, PF, MO, AL, VC and SS rules. The research behind them is in
[research/STORY_EDIT_VOICE_2026-10-19.md](research/STORY_EDIT_VOICE_2026-10-19.md); every parameter was then checked
against studies, standards and official pages in [research/PARAMETER_AUDIT_2026-10-19.md](research/PARAMETER_AUDIT_2026-10-19.md)
(D-49), which says per rule whether it holds, changed, or stays a hypothesis. The procedure is the skill
`story-engine`; each stage has a page in `.claude/agents/` that the main agent follows, and only the critic is spawned
(OR-20). The fields live in
[PRODUCTION_SCRIPT](PRODUCTION_SCRIPT.md) (`drama`, `accents`, Short `style` and `ending`, `cast.<id>.voice.traits`),
and the checks are PV-33..PV-36 there.

Two kinds of finding:
- **FAIL** is structural (a loop that does not exist, a pay-off before its plant, a fact without a claim, a voice that imitates a person). It blocks the script.
- **REVIEW** is craft. The number tells the writer and the creator where to look, and the creator judges.

## Episode 1, measured (2026-10-19)

All numbers below come from Episode 1's own production script:
- **Pictures:** 217 shots. 161 were pushes, 54 pans and 2 pulls. Zoom never went above 1.08.
- **Joins:** 211 cuts and 6 dissolves. 89 joins were a reframe of the same picture.
- **Story devices:** 8 speech bubbles, no voiced dialogue, 22 questions in 18 minutes.
- **Sound:** 1.2 effects a minute.
- **Pace:** a visual event every 4.4 s on average, but the largest gap was 10 s.
- **Motion:** only 4 % of shots had anything moving besides the camera.

The rate of change was acceptable. What made it read as a slideshow was that every change was the same kind, and almost nothing moved inside the frame.

## Story (ST)

The story layer is written before any line (stage 1). It is checked by `scripting/story_lint.py`, called from PV-33.

| ID | Rule | Severity |
|---|---|---|
| ST-00 | A `drama` block (premise, a yes/no dramatic question, a promise) exists, and every segment has `drama.function` and `drama.turn`. On a `production_script/3` a missing drama block is a FAIL: Syndicate Wars shipped without one and this single REVIEW was its only trace (D-58). | REVIEW; FAIL on /3 |
| ST-01 | **One dramatic question.** It is asked in the cold open or hook and answered at the end (a resolution, button, twist or climax). | REVIEW |
| ST-02 | **But / therefore, never "and then".** Every join after the first is BUT (an obstacle) or THEREFORE (a consequence). About one join in three or more is a BUT. No segment opens with "and then", "after that" or "next". | REVIEW |
| ST-03 | **Stakes and a value turn.** Every segment after the opening says what is lost if it goes wrong (`stakes`). Every segment except the button turns a value (`shift`, for example "safe -> hunted"). A segment where nothing changes is cut or merged. | REVIEW |
| ST-04 | **Heroes who want something.** Every speaking hero has an arc (want, flaw; the lead also need and change). An arc for someone outside the cast is a FAIL. | REVIEW / FAIL |
| ST-05 | **Open loops.** Loops are declared (`drama.loops`), opened and closed in order, and none is left hanging. At the end of every segment before the resolution at least one loop is still open. Opening or closing an unknown loop, or closing a loop before it opens, is a FAIL. | REVIEW / FAIL |
| ST-06 | **Set-up and pay-off.** A detail planted early decides the end. A pay-off at or before its plant is a FAIL. A script of 6 or more segments has at least one pair. | REVIEW / FAIL |
| ST-07 | **Turns spread out.** There are at least two turning points (reversal, midpoint, crisis, twist, climax), and one falls in the middle third. | REVIEW |
| ST-08 | **Human needs.** At least 3 needs are named and each is served by a segment. The needs are curiosity, stakes, humour, wonder, fear, identity, justice, belonging, competence and surprise. | REVIEW |
| ST-09 | **Objectivity is labelled.** Every segment is `fact`, `reasoned` or `invented` (`claim_share`). Invention is never the majority. A segment labelled fact must carry claim ids, or it is a FAIL. The invention is disclosed outside the story, by the title and the description; on /3 the story itself never says it (SC-08, SC-11, [BP-88](SOURCED_RULES.md); the creator, 2026-10-20). The old spoken honesty beat stacked into "Invented, remember" x7 on Syndicate Wars. | REVIEW / FAIL |
| ST-10 | **The ending pays the promise.** It has a named kind: twist, reversal, bookend, callback or open question. | REVIEW |
| ST-11 | **A question is answered within seconds unless it is a declared loop** (D-49). The curiosity a question opens boosts memory for what follows in the next 2-4 s and is gone by 6-8 s (Murphy 2020), so an undeclared question gets its answer at once; only `drama.loops` stay open. The hook names what the viewer already knows and what they do not: a partial gap pulls harder than a total mystery (Frede 2026). Three or more questions in a segment that opens no loop are stacked, not answered ([BP-74](SOURCED_RULES.md)). | REVIEW |
| ST-12 | **The midpoint sits mid-story** (D-58). On a script long enough, the midpoint/reversal segment's centre falls in the word-share band of [BP-75](SOURCED_RULES.md) (a write-time proxy for the clock; evidence: [research/STORYTELLING_EDITING_2026-10-19.md](research/STORYTELLING_EDITING_2026-10-19.md)). | REVIEW |
| ST-13 | **Turns arrive on a cadence** (D-58). Between the hook and the resolution, no stretch longer than [BP-76](SOURCED_RULES.md)'s gap (words turned into seconds at [BP-01](SOURCED_RULES.md)'s heard pace) passes without a turn: a segment whose function is a reversal, midpoint, crisis, twist or climax, or whose `drama.turn` is "but". | REVIEW |
| ST-14 | **Every exchange is framed** ([D-64](DECISIONS_AND_OPEN_QUESTIONS.md)). A segment's hero lines (voiced or bubble) are one exchange: before it the narrator's setup names each speaker before his first line (REVIEW: a description may stand for a name) and says what brings them there, after it the narrator's conclusion says what came of it; a segment never ends or opens on a hero line, so two exchanges never touch. Counts and severity: [BP-90](SOURCED_RULES.md). | FAIL |
| ST-15 | **The speaker comes first** ([D-65](DECISIONS_AND_OPEN_QUESTIONS.md)). A narrator line that reports speech names the speaker before his words ("Musk says it is how fires work"), never in a trailing tag ("..., says Musk"); a heuristic, [BP-95](SOURCED_RULES.md). | REVIEW |
| ST-16 | **Two voices per reported line** ([D-65](DECISIONS_AND_OPEN_QUESTIONS.md)). One narrator line reports at most [BP-96](SOURCED_RULES.md)'s number of named speakers; a third enters as an action or in the next exchange (a hypothesis). | REVIEW |
| ST-17 | **Short narration blocks** (template D). Narrator lines with no character line between them last at most [BP-104](SOURCED_RULES.md)'s block (words at [BP-01](SOURCED_RULES.md)'s heard pace); the narrator carries the jumps in time, place, cause or goal, the scenes carry the action. | REVIEW |
| ST-18 | **The central scene is the longest scene** (template D). One scene with dialogue is the climax, crisis or midpoint, and no other scene has more words; it holds 2-3 escalations and the plan meets the unexpected inside it. | REVIEW |
| ST-19 | **The narrator's share** (template D). The narrator has the share of the words [BP-105](SOURCED_RULES.md) gives; a political or personal rivalry sits low in it, a campaign high. | REVIEW |
| ST-20 | **No "and then" chain** (P3). Two or more joins that open with "and then", "after that" or "next," inside one segment's lines, or on two consecutive segment openers, are REVIEW ([BP-145](SOURCED_RULES.md): one article-type source). A declared connector other than BUT or THEREFORE is already a contract FAIL ([CN-01](CONTRACTS.md): `drama.turn` and the spine's `causal_connector` take nothing else). | REVIEW |
| ST-21 | **No double exposition** (P3). A narrator line and the adjacent character line share at least [BP-144](SOURCED_RULES.md)'s share of their content words: the narrator says again what the scene just played. The shot-card twin is KP-20. | REVIEW |
| ST-22 | **Ad-safety window** (P3). A graphic-violence word ([BP-143](SOURCED_RULES.md) lexicon) in a line that starts, by the estimate of `scripting/syllables.py`, inside the first seconds of the video (YouTube's "first seven seconds", policy baseline B-16: one source type); the creator decides. | REVIEW |
| ST-23 | **The twist lands** (P3). The first line of a `twist` or `reversal` segment lasts at most [BP-115](SOURCED_RULES.md)'s seconds by the syllable estimate. | REVIEW |
| ST-24 | **A turn is played** (P3, [BP-142](SOURCED_RULES.md), house). Every turn slot (template D rows 4, 6, 8, 10, 11, 13; any segment whose function is a turn) holds a block in which a cast member acts or speaks: a turn told over a map, a card or the narrator alone is a FAIL; a played share below the profile's minimum ([BP-141](SOURCED_RULES.md)) is REVIEW. The measure is `variant_plan.dynamics`, the one function that counts lane shares. | FAIL / REVIEW |

### Story templates for an 8-12 minute what-if (D-58)

The 2026-10-19 rewrite replaced the single beat grid with three templates (template D, added 2026-10-24, is for the 15-minute historical docudrama) over the same validator (ST-01..ST-13).
The story architect picks one per episode, records the choice in a one-line note on `drama.ending.note` or at the top
of the skeleton, and varies it across the channel. Times are for 10 minutes and scale with length.

**A. Three-act / 7-point (the default).** Hook 0:00-0:15 with the core tension inside the first 15 s; stakes by 0:45;
the inciting event ~1:00; the central question standing by 1:30; 3-5 escalating sequences with pinch points ~2:30 and
~7:30; the midpoint pivot at 45-55 % (ST-12); low point and the hero's decision 7:30-9:00; climax 9:00-9:30; a button
that mirrors the opening image, at most 30 s after the question is answered.

**B. Save-the-Cat compressed.** Snyder's beats mapped by percent of runtime: catalyst ~11 %, midpoint 50 %,
all-is-lost ~75 %, break-into-three ~80 %, finale to the end. Suits episodes whose hero visibly changes.

**C. Mystery reveal ladder.** A cold open on a contradiction, then a reveal that reframes everything about every
2:00; the chronology is written out straight before the suspense order is chosen. Suits analysis episodes (D-26).

**D. Historical docudrama, 15 minutes (2026-10-24).** An animated docudrama: a narrator plus characters who talk to each
other, shots of 3-5 s. Three acts at the macro level, narrator and scene taking turns at the micro level, and every scene
ending on the next question. Set `drama.template` to "D"; ST-17..ST-19 then apply. Times are for 15:00 and scale with
length; the borders are guides, not a stopwatch. Evidence and what was not verified:
[research/DOCUDRAMA_CONSTITUTION_2026-10-24.md](research/DOCUDRAMA_CONSTITUTION_2026-10-24.md).

| # | Time | Segment (`function`) | What happens |
|---|---|---|---|
| 1 | 0:00-0:12 | hook (`cold_open`) | an action, a paradox or an odd detail at once; sound from the first frame; the first sentence is the hook (BP-03); 2-3 teasers cut from the later fight (KP-41, BP-111) |
| 2 | 0:12-0:30 | information gap (`hook`) | the narrator states the surprising outcome or the paradox; no part of the answer |
| 3 | 0:30-1:15 | orientation (`setup`) | narrator: where, when, who against whom (maps, diagrams, no extra text) |
| 4 | 1:15-2:45 | scene 1 (`inciting`) | goals and stakes declared through conflict |
| 5 | 2:45-3:15 | bridge | narrator: the result and the next question |
| 6 | 3:15-5:00 | scene 2 (`escalation`) | the first plan fails; the hero must react |
| 7 | 5:00-6:00 | new complication | narrator: the factor that changes the game |
| 8 | 6:00-7:30 | scene 3 (`escalation`) | the other side acts; a new place marks the boundary; while a plan is told, its execution is shown (KP-42) |
| 9 | 7:30-8:15 | preparation | narrator: the full size of the crisis; pressure rises; no spoiler |
| 10 | 8:15-10:45 | central scene (`climax` or `crisis`) | the longest scene (ST-18), 2-3 escalations inside; the other side's line cross-cut with the hero's (KP-42) |
| 11 | 10:45-11:15 | turning point (`reversal`) | the choice, revelation or failure that changes the story; then silence or one still frame |
| 12 | 11:15-12:00 | fallout | narrator: who lost and who won, never what we just saw |
| 13 | 12:00-13:30 | scene 4, final choice | the hero's last act, slower, on dialogue; no new conflict; the power gap shown in a cutaway, the lines broken by silent reactions (KP-43) |
| 14 | 13:30-14:30 | the answer (`resolution`) | the opening question answered fully; an uncertain fact is said to be uncertain |
| 15 | 14:30-14:45 | callback (`button`) | the first image again with a new meaning |
| 16 | 14:45-15:00 | channel pointer | the worlds already on the channel and the worlds coming, subscribe so as not to miss them (BP-106, KP-40); never a dry "subscribe" or a goodbye (BP-43); the narration runs on under the end screen |

The turn slots 4, 6, 8, 10, 11 and 13 are played scenes ([BP-142](SOURCED_RULES.md), ST-24, VP-08).

Modules by subject: a war or campaign runs two storylines (each side in its own place, variant 6 of the study); a
political or personal rivalry keeps the narrator low and escalates by words, blackmail or betrayal, on faces; an
invention, a money war or a mystery runs on questions, every scene a failed attempt that raises the next question and the
turning point a eureka moment. The long video carries captions as a closed-caption track and burns no full narrator
subtitles into the picture (the redundancy principle; the Shorts keep theirs, BP-13).

Whichever template: stakes strictly escalate from sequence to sequence, the central question is answered only in the last
tenth ([BP-04](SOURCED_RULES.md); ENG-5 checks where the resolution starts), and the final image mirrors the opening image's subject. The timings are **product hypotheses**:
the web research refuted every published numeric retention rule as evidence (0-3 votes: blogs that cite no data), the
templates encode the craft books and competitor videos we studied (sources per rule:
[research/STORYTELLING_EDITING_2026-10-19.md](research/STORYTELLING_EDITING_2026-10-19.md)), and our own retention
data will adjust them.

The format blends three references:
- Infographics Show what-ifs: a named hero with a personal stake, three loops, a reversal at the real limits, and a twist.
- Kurzgesagt: claims grounded in sources, picture beats on the operative word, and a crisis reframed as hope.
- xkcd *What If?*: an absurd premise worked through with serious arithmetic, with humour layered on top of the facts.

## Scenes (SC)

New in the 2026-10-19 rewrite (D-58), after the Syndicate Wars review: "no dialogue — characters speak out of context,
never meet, no scene is set". On a `production_script/3` every segment with dialogue carries a `scene` object (place,
time, `present`, `why_now`, `pov`, `want`, `obstacle_want`, `value`, `open_charge`, `close_charge`, `turn`, `exit`,
`surface_topic`, `real_subject`) and every spoken line says who it is said `to`. Checked by `scripting/scene_lint.py`,
wired as PV-48; a `/1` or `/2` script gets no SC findings (its contract is unchanged). The craft behind the rules is in
the skill `dialogue-scenes`; the sources per rule in
[research/STORYTELLING_EDITING_2026-10-19.md](research/STORYTELLING_EDITING_2026-10-19.md).

| ID | Rule | Severity |
|---|---|---|
| SC-01 | **A scene is declared before it is played.** A segment with dialogue has a complete scene header; `present` names cast members and `pov` is one of them. | FAIL |
| SC-02 | **The scene turns.** `open_charge` != `close_charge` on the scene's `value` (an unchanged charge is a nonevent — cut it or give it a turn), and `turn` names the turning beat in one sentence. | FAIL |
| SC-03 | **Wants collide.** `want` != `obstacle_want`, both concrete: someone present wants something that collides with what the POV wants. Explaining at each other is a meeting, not a scene. | FAIL |
| SC-04 | **Every line is addressed.** Each spoken line's `to` is someone present (or `self` / `room`). A hero never talks to the narrator: the fourth wall stands between the cast and the narration. | FAIL |
| SC-05 | **A real exchange.** With 2+ present, at least one unbroken run of character lines of the length and speaker count of [BP-70](SOURCED_RULES.md) (no narrator inside), or a reported exchange ([D-65](DECISIONS_AND_OPEN_QUESTIONS.md)): the narrator lines report at least as many turns of as many named speakers ("Musk says", "he asks"). Everyone present speaks or reacts (REVIEW), and a `reveal` line gets a reaction: the next beat is another character's line or a listener's expression (REVIEW). | FAIL / REVIEW |
| SC-06 | **Enter late, leave early.** No greeting opener, no wrap-up closer: the scene starts mid-action and ends within a line or two of its turn. | REVIEW |
| SC-07 | **No press-release narration.** The press-release lexicon of [BP-15](SOURCED_RULES.md) ("X's page says", "announced", "release date", "is set to release", "comes out on", "launches worldwide"...; one list, shared with N-14) is banned from narrator lines (the creator, 2026-10-19: tell the story). A date or spec enters only inside a scene, as stakes or ammunition ("he had until November 19 — therefore..."). | FAIL |
| SC-08 | **No spoken honesty beat.** Narrator lines never stop the story to say it is invented: [BP-71](SOURCED_RULES.md) allows 0 segments since 2026-10-20 (the creator's immersion rule, SC-11). The title and the description carry the disclosure, the claim map labels each segment (ST-09). | FAIL |
| SC-09 | **Turn-taking.** A spoken turn over the cap of [BP-72](SOURCED_RULES.md) (35 words) is a FAIL (split it or give the summary to the narrator), and so is a second speech in one scene (one 25-60-word speech, at its peak); a turn over [BP-73](SOURCED_RULES.md)'s jab length (15 words) is a REVIEW, and so are more than 3 consecutive question-turns, which read as an interview (DW-12). | FAIL / REVIEW |
| SC-10 | **Subtext is never spoken.** The scene declares `surface_topic` and `real_subject` (REVIEW if absent); a line that states the real subject verbatim is a FAIL. | FAIL / REVIEW |
| SC-11 | **Full immersion, no meta disclaimers** (the creator's strict storytelling rule 2, 2026-10-20, D-61). No line, Short or on-screen text steps outside the story ("this is a simulation", "as an AI", "in this hypothetical story", "none of this happened"), and the narrator never hedges the story itself ("we cannot know for sure"); the episode plays as a tense documentary of events happening now. A hero may doubt inside a scene. The lexicon is [BP-88](SOURCED_RULES.md)'s. | FAIL |
| SC-12 | **Show, don't tell** (the creator's strict storytelling rule 1, 2026-10-20, D-61). The narrator never states a hero's traits ("he is charismatic", "she takes risks"), gives a rating ("9/10", stars) or summarises a biography ("was born in", "net worth"); no stat cards or star ratings on screen (`select_screen.py` is Syndicate Wars only). A trait shows only through what the hero does, says, gets wrong and decides. Heroes may judge each other inside a scene. The lexicons are [BP-87](SOURCED_RULES.md)'s. | FAIL |

## Dialogue (DW)

Stage 2 writes the dialogue one segment per call, with the skill `dialogue-scenes`. Where a DW rule has code, the code
is an SC rule of `scene_lint.py` (noted per row); the rest is editorial, held by the scene-writer and the critic.

| ID | Rule |
|---|---|
| DW-01 | **Dialogue is conflict.** Each speaking hero wants something in the scene, and their wants collide (encoded as SC-03 and SC-05). Two heroes never agree for more than two lines in a row (editorial, the critic watches it). |
| DW-02 | **Enter late, leave early.** A scene starts in the middle of the action and ends on its open loop (encoded as SC-06). |
| DW-03 | **Character voice.** Word choice follows the hero card and the arc (the theorist and the hands-on one, the optimist and the cynic). If you cover the speaker names, you can still tell who speaks, on about 80 % of lines (the cover-the-names test, skill `dialogue-scenes`). |
| DW-04 | **Subtext over statement.** Heroes do not announce their feelings, and the scene's real subject is never spoken (encoded as SC-10). The narrator explains only what the heroes cannot know. |
| DW-05 | **A reaction after every reveal.** A line marked `intent: reveal` is followed by another character's line or a listener's expression beat, before the next information (encoded in SC-05; Kuleshov: show the face the line affects). |
| DW-06 | **Short spoken turns.** Default 5-15 words, with contractions; a turn over 35 words is split or given to the narrator; one 25-60-word speech per scene, at its peak (encoded as SC-09; the numbers are [BP-72](SOURCED_RULES.md) and [BP-73](SOURCED_RULES.md)). |
| DW-07 | **Humour from situation and character, never from a false fact.** A joke never carries a claim, and a joke never carries the explanation either (D-49): the fact is said straight, the joke is the reaction to it. Humorous examples woven into the explanation cut recall by 13-17 % in Bolkan 2018; humour beside the content did not. |
| DW-09 | **The learner-corrected scene is one conflict mode among several** (softened 2026-10-19, D-58). The tutor-tutee evidence (Chi 2017 d = 1.08 on transfer; Qian 2024) is for explainers, so a scene where one hero guesses wrong and is corrected stays in the toolbox — but it is chosen per scene (`scene.mode: learner`) and varied with the other modes: balanced, asymmetric, indirect, comic, minimal. Every scene as a tutor-tutee lesson contradicted the ensemble drama D-48 asks for. |
| DW-10 | **The narrator talks to "you"** (D-49): second person, contractions, a direct question to the viewer about once a minute (N-06, [BP-17](SOURCED_RULES.md)). Conversational style: d = 0.79 in Mayer's tests, transfer d = 0.54 in the Ginns 2013 meta-analysis. |
| DW-11 | **Each hero talks like themselves** (creator 2026-10-19; PV-46, `scripting/speech.py`). Every speaking hero has `cast.<id>.speech`: `basis` `public` (a real person or a known character: the manner and vocabulary they are generally known for, with `sources`) or `personality` (an invented hero: from the card and arc), a one-sentence `style` (pace, register, sentence length, habits), at least three signature `words` or turns of phrase, and what they never say (`avoid`). The lines are always our own: the manner is borrowed, never a quote or catchphrase from a film or series, and the voice still never imitates anyone (VC-02). |
| DW-08 | **No info-dump in a mouth.** A number belongs to the narrator or a data visual (ED-10), unless the hero's want is to argue it. At most one number per turn. |
| DW-12 | **Answer sideways** (D-58). No more than 3 clean question-then-answer pairs in a row (SC-09 flags the chain, [BP-73](SOURCED_RULES.md)), and at least two non-direct responses per scene: deflect, answer with a question, silence plus an action, counterattack, partial truth. An interview is not a conversation. |
| DW-13 | **Exposition is ammunition** (D-58). A fact both speakers know is spoken only as a weapon or a stake, never as information for the audience ("would they say this with no audience watching?"); a fact neither knows belongs to the narrator; about one dialogue-borne fact per 2-3 beats. The knowledge-state notes live with the scene header (skill `dialogue-scenes`). |

## Performance (PF)

Stage 3 writes the delivery only. The words are frozen, and `stage_guard performer` checks that.

| ID | Rule |
|---|---|
| PF-01 | **Tags follow the speaker's temperament** (`cast.<id>.voice.traits.temperament`). There are at most 2 tags a line, and none on a line that reads well flat (rules EL in skill `elevenlabs-voice`). |
| PF-02 | **One stressed word a line,** usually the last content word or the operative word the picture lands on. |
| PF-03 | **Pauses carry the story:** about 0.5 s before a reveal (the one pause length with measured comprehension gain, Van Loon 2000), never inside a name or number. A pause after a punchline is a style choice: the one study of joke performances found no evidence that punchlines are preceded or followed by pauses (Attardo 2011). |
| PF-04 | **Interjections are reactions,** prepended only from the guard's list (oh, hmm, well, wait, huh, uh-oh...). There is at most one in five lines a speaker, and never on the narrator's factual lines. |
| PF-05 | **Emotion arcs with the story:** the crisis line is quieter, not louder. The climax is the most energetic segment. |

## Motion and visual change (MO)

Stage 4 plans the motion on the frozen words. `edit/motion_lint.py` checks it as PV-35, on the estimated read and again on the real read.

Rate alone does not cure a slideshow. Variety does: different kinds of event, and something moving inside the frame. An event is anything new the eye gets:
- a new picture or a reframe;
- an accent;
- a speech bubble;
- a data visual;
- a card.

| ID | Rule (all REVIEW) |
|---|---|
| MO-01 | **No dead air.** The still limits are BP-40's, section by section ([SOURCED_RULES](SOURCED_RULES.md): the hook window, then the body's REVIEW line); MO-01 counts the same events as the board's RHYTHM-3 (a cut, bubble, accent, data visual, card or visual beat) and reports at REVIEW, RHYTHM-3 is the gate. Background (D-49): cuts and motion do raise attention and memory (Lang 2000) and film shot lengths fell under 4 s after 2000 (Cutting 2011); the old flat "5 s everywhere" was superseded by BP-40 (D-59). |
| MO-02 | **Variety.** Every window holds a minimum number of kinds of event (BP-83, [SOURCED_RULES](SOURCED_RULES.md)). |
| MO-03 | **No plain runs.** Only a few shots in a row may be only a camera move (no accent, bubble or visual; BP-83). |
| MO-04 | **Hard entries are motivated.** `whip_in` and `flash_in` go only on a segment's first shot (a story turn), and at least BP-25's gap apart. This amends ED-04: they mark a turn, they are not a style. |
| MO-05 | **Words on screen are rare.** `pop_text` / `slam_text` keep BP-83's gap and BP-38's word cap (the beats' VB-04 cap). |
| MO-06 | **The frame lives.** The share of shots with something moving besides the camera (wobble, a bubble, an accent, a building visual) is reported only, with no target (BP-83, [D-64](DECISIONS_AND_OPEN_QUESTIONS.md): a target pushed accents onto plain shots). |
| MO-07 | **Rhythm is variance** (D-58). A run of consecutive shots holding almost the same time, or a segment whose hold lengths barely vary, reads as a metronome (BP-83's run, spread and CV): hold long on wonder, cut short on action (Bordwell on tempo contrast; Murch: cut on the thought, not the clock). It can always be met together with BP-40: in the hook window holds of about 2.6 s and 4.9 s alternated pass both. |

Every change should do one of five jobs: clarify, emphasise, reorient, compress or contrast. A change that does none of them is cut. Stillness is allowed when it is chosen: a held wonder shot (ED-05) is not a gap if a wobble or a building visual keeps the frame alive.

### Accent vocabulary

`production/accents.py` draws the accents into the render. It costs nothing and is deterministic: the same frame always renders the same.

| kind | What it does | Duration |
|---|---|---|
| `punch` | A quick zoom-in on the word | 0.12 s in, held through the shot |
| `shake` | A camera shake, decaying (an impact beat only) | the house shake inside BP-24 |
| `wobble` | A slow, continuous "living" drift of the whole frame | 2.4 s period |
| `whip_in` | A blurred sideways whip from the previous frame (segment openings only, MO-04) | 0.22 s |
| `flash_in` | A white flash that clears (segment openings only) | BP-26 (frames, white level) |
| `pop_text` | Up to BP-38's word cap pops in with overshoot | pop 0.25 s, hold P-71 (1.5 s + 0.3 s a word, within BP-27) |
| `slam_text` | Big words slam in from scale | 0.12 s, hold P-71 + 0.6 s (within BP-27) |

An accent is timed to a phrase of its shot's words (`at`), so the picture beat lands on the operative word.

## Sound layers (AL)

Stage 4 also plans the sound. `audio/layers.py` checks it as PV-36. ED-03 (one music at a time) still applies.

| ID | Rule (severity from the registry: REVIEW, except a sound outside BP-54's window) |
|---|---|
| AL-01 | **Few layers at once.** Effects of one class at once and the layers in all (voice, music and bed included) stay within [BP-56](SOURCED_RULES.md). |
| AL-02 | **Enough sound, not clutter.** Sound events a minute, effects and beat cues counted together, inside [BP-49](SOURCED_RULES.md)'s band (a hypothesis; changed 2026-10-19: the old count left cues out, so the rule never fired on the 33 cues/min it existed for). Below the band the motion is silent (Episode 1 had 1.2 a minute), above it is clutter. On `/3` silence is the default (VB-08), so only the upper bound applies. How the density rules nest: AL-02 counts everything the ear hears; VB-11 caps the cues alone, more strictly; BP-55 caps the share of visual beats that carry an effect. |
| AL-03 | **Every hard move is heard.** A whip, flash, slam, shake or punch has an effect inside [BP-54](SOURCED_RULES.md)'s sync window (a sound outside it, early or late, is BP-54's FAIL; no sound near the move at all is a REVIEW). |
| AL-04 | **Under the voice.** Before ducking, effects and beds stay under [BP-65](SOURCED_RULES.md)'s pre-mix gain caps (dBFS, a proxy). The measure itself is [BP-52](SOURCED_RULES.md): the background's loudness distance under the voice in LU on the stems (D-49: Torcoli 2019; foreground effects within 4-5 LU of dialogue, EBU Tech 3343, Netflix). Music and bed duck under speech by [BP-53](SOURCED_RULES.md) and rise in pauses. |

## Voice casting (VC)

Stage 5 casts the voices. `audio/casting.py` and PV-10 / PV-32 check them.

| ID | Rule | Severity |
|---|---|---|
| VC-01 | **Cast from traits.** Each speaking hero has `voice.traits`: gender, age, temperament (at most 4 words), energy, origin and role. `casting.query` turns the traits into a free library search (ElevenLabs `creative_list_voices`), and `casting.rank` scores the results and proposes three candidates. If no library voice fits, `casting.design_description` writes a description for a designed voice (paid, so it needs an estimate and the creator's yes). | REVIEW |
| VC-02 | **A real person: documented traits only.** For a real person (`real_person`), the traits come from sources (`documented`, claim ids): their age at the time of the story, region, station and recorded temperament. The voice is never searched, designed or described as that person's voice. It is never cloned, never taken from a "famous" category, and never prompted with the person's name. ElevenLabs' prohibited-use policy bans impersonation; its "no-go voices" filter restricts clones that approximate prominent public figures but is incomplete by its own description, so the policy, not the filter, is the line. This channel goes further: no soundalikes. | FAIL (PV-10) |
| VC-03 | **A test read before the cast is fixed.** The creator hears one chunk per candidate and picks (EL-02). | REVIEW |
| VC-04 | **Voices the ear can tell apart.** Two speakers never share a voice. Two heroes with the same gender, age and energy get different temperaments and voices. | REVIEW (PV-32) |
| VC-05 | **Age, ethnicity and region are hard.** Each speaking hero has `voice.traits.age` (young / middle_aged / old) and an `origin` or `ethnicity` (creator 2026-10-19: "ages matter most", "add the ethnicity to the rules"). Age is a filter: a voice labelled two bands off, or young for a middle-aged hero, is never ranked (`casting.age_of`, read from the style or card when the trait is missing). The accent is read from `origin`, then from `ethnicity` (a Japanese businessman speaks English with a Japanese accent, not an American one); a named region (Birmingham, Midlands, Brooklyn...) goes into the search text and the ranking because the library labels only carry "british" or "american". An unknown age or origin is a REVIEW before casting. | REVIEW (PV-32) |
| VC-06 | **Audition by measurement, free.** Each of the top candidates is heard for free (the library preview the connector returns, or a read the creator already holds) and gets one `voice_audition/1` record: median pitch and range, pitch variation, emphasis, pace, spectral centroid, pause rhythm, sibilance and, when several takes exist, their consistency (`audio/voice_audition.py`). The profile is measured, never judged; a preview under 5 s of speech is marked unreliable. No paid take is made to audition (V5: the paid test is the first piece of the OR-19 sample). | REVIEW |
| VC-07 | **Distinct is measurable.** Two cast voices differ by at least one of BP-138's margins (pitch, pace, centroid); a pair that reaches none is a VC-04 REVIEW (`voice_audition.distinct`). The creator still picks by ear (VC-03). | REVIEW (BP-138) |
| VC-08 | **The channel voice stays.** `config/channel_voices.json` (`channel_voices/1`) holds the voices the channel uses and the baseline of each; the narrator is the one `status: channel` entry, and only the creator's recorded word replaces, retires or demotes it, or changes its model or its baseline (the drift reference of EL-13): `voice_check.register` needs a `creator_ref` that names a `channel_voice` record younger than 60 minutes in `jobs/creator_ok.jsonl` for the voice that becomes the channel voice (or the standing one being changed) (`python -m explainer_engine.governance ok channel_voice <voice_id> <message id> "<his words>"`) and refuses otherwise, in one call or two (Blueprint veto line V1). Host characters speak with the narrator's voice (D-68, V2). | FAIL (register) |
| VC-09 | **Eligible, then fit, then use.** A voice is a candidate only if `casting.eligible` finds no reason against it (famous or imitation, taken, age two bands off, VC-02/05); candidates are ordered by `casting.fit`: the trait match first, the library's one-year usage order only as the tie-break (the connector is called with `sort: usage_character_count_1y`, `rank(..., by_usage=True)`). A voice an LTX cast card needs is written as words from the traits only (`casting.ltx_voice_text`, the same PV-10 guard). | REVIEW |

## Shorts styles (SS)

Stage 6 writes the Shorts, checked by PV-34 and, as before, PV-28 / SH rules.

| ID | Rule |
|---|---|
| SS-01 | **A set of 10 uses at least 6 styles.** A set of 5 or more uses at least min(6, max(3, 60 % of the set)). |
| SS-02 | **Alternate styles in posting order.** Two Shorts in a row never share a style. |
| SS-03 | **Every Short is a moment of the video, re-cut, not a summary.** The long video's exact title is said aloud or shown, and the related-video link (shown under the channel handle; a public or unlisted video of our own channel) is set in Studio by hand at upload. The set is posted within three days of the video (weak evidence, one channel's data; D-49). |
| SS-05 | **A statement hook for two styles** (creator, 2026-10-19): `anti_intuition` and `pov_you` may open with one statement inside [BP-11](SOURCED_RULES.md)'s word cap and hook time ("Don't go to the lifeboats.", "You wake up in 1347.") instead of a question; every other style keeps SH-01's question. Checked by PV-28. |
| SS-06 | **Two length bands** (D-49). A set of six or more has at least three Shorts of 15-30 s and three of 45-75 s. Views per Short peak at 11-30 s in a 108k-Short analysis, while interaction is about twice as high at 30-90 s and the animated what-if breakouts run 38-100 s; YouTube says no length is favoured. The channel's own viewed-vs-swiped numbers decide. Checked by PV-34 on the estimated read (a Short's words at [BP-12](SOURCED_RULES.md)'s heard pace, `validate.short_seconds`). |
| SS-07 | **The hook is on frame 0 and the first cut lands inside it** (D-49). The hook's key words are on screen from the first frame (99.9 % of Shorts views come from the feed, so the first frame is the thumbnail) and the second shot starts on a word of the hook line, about 2 s in; a still never holds through the hook. Episode 1's Shorts held one still 4-8 s and completed the hook at 2.5-3.5 s. Checked by PV-34. |
| SS-08 | **At least 3 visual events every 10 s** (cuts, reframes, accents, text pops, HUD ticks). A hypothesis from observation (D-49): the breakout Shorts watched showed 3-6, Episode 1's 1.4. Checked by PV-34 on the estimated read. |
| SS-09 | **A Short carries the same visual-beat layer as the long video** (creator, 2026-10-19). Every Short line has its `visual_beats` with their cues, and a Short line with a `speaker` its expression changes, under the script's schema VB rules (each beat with its reason and cue, VB-03 and VB-08; the faces as VB-02 asks on that schema), while the Short's pace is BP-45's (a change on screen at least every few seconds and enough events every 10 s, beats counted; the 1.5 s metronome of VB-01 is not a Shorts rule and does not run on a Short). Most Short lines are the video's own lines and take its beats; a Short's own lines (hook, pointer) get beats of their own; a `label` or `highlight` points at a spot inside the Short's 9:16 crop. Why: on 2026-10-19 Studio read about 80 % viewed vs 20 % swiped away, so the hook holds, while likes per view were 0.4-1.0 % (small-channel median 1.71 %) and vidIQ counted 1.4 changes every 10 s with stills held 4-8 s: the Shorts lose people in the middle ([PARAMETER_AUDIT](research/PARAMETER_AUDIT_2026-10-19.md) section 0). Checked by PV-44 on each Short's estimated read (170 wpm), reported as "SH03 line 2"; drawn and cued by `production/shorts.py` with the long video's own renderer. |
| SS-04 | **The ending has a kind:** cliffhanger, loop (the last line runs into the first), question, or pointer (the last line points to the video). |

### Style catalog

The stage-by-stage recipe of each style (frame 0, the hook, the body, text and HUD, sound, ending, length band) is in
[research/PARAMETER_AUDIT_2026-10-19.md](research/PARAMETER_AUDIT_2026-10-19.md) section 6 and in the skill `shorts-for-video`.

| style | Shape | Typical ending |
|---|---|---|
| `cold_open_cliffhanger` | The video's cold open, cut at the worst moment | cliffhanger ("Part 2 is the full video") |
| `anti_intuition` | "If X happens, don't do Y. Everyone else will." | pointer |
| `countdown_hud` | A counter at the top (DAY 1, YEAR 100) driving the steps | cliffhanger |
| `dialogue_clash` | Two heroes argue one point in 4-6 fast turns, ending on a punchline | question |
| `fact_bomb` | One astonishing number from the claim map, built on screen | pointer |
| `pov_you` | Second person: "You wake up in 1347..." | question |
| `myth_buster` | A common belief, then what really happened | pointer |
| `ranked_three` | Three outcomes, the best last | question |
| `loop` | The last line completes the first, so the Short replays seamlessly | loop |
| `would_you` | A choice for the viewer, then the consequence | question |

Shorts tricks, all checked or planned in the script:
- a hook line and on-screen text within the first 2-3 s;
- 3-6 changes every 10 s;
- word-highlight captions;
- a persistent HUD for counters;
- a sound on a text pop only when it has a purpose (BP-55: at most one beat in two carries an effect);
- the loop ending;
- the long title said aloud;
- the related-video link and a pinned comment at upload, which is manual (no upload code, invariant 4).

PV-28 asks that the hook be one question inside [BP-11](SOURCED_RULES.md)'s word cap, complete by its hook time on the estimated read (REVIEW there; the real read decides in `production/shorts.py`), except for the two statement-hook styles of SS-05.

## Visual beats (VB)

The creator's notes of 2026-10-19: a picture change every 3-6 s is fine (superseded by BP-40, D-59), but about every 1.5 s something must happen in the
picture (a chart, a word, an object, a sign), chosen by what the narrator says at that instant, and written while the script is
written, not added at the render. In dialogue the face is the focus, so the expression changes about once a second (anger, joy,
surprise, doubt...). Every addition also makes a very short, light sound so the change is noticed for a moment without tiring
the ear; whether expression changes should sound too was left to the evidence.

The beats are a field of each line, `lines[].visual_beats` ([PRODUCTION_SCRIPT](PRODUCTION_SCRIPT.md), `production_script/2`),
written by stage 2b (`beat-writer`, skill `visual-beats`) right after the scene-writer finishes the same segment, on frozen
words (`stage_guard beats`). A beat lands on a phrase of its own line (`at`) plus an optional `offset` (-0.3..1.5 s): never a
clock time. Kinds: `text`, `label`, `prop`, `chart`, `highlight`, `symbol`, `accent` (a punch or shake of `production/accents.py`),
`expression`. The render draws them for free (`production/beats.py`); the cues are made in code (`audio/cues.py`).
Checked by PV-44: on the estimated read while writing, again on the real read. In a `production_script/1` (legacy) they are one
VB-00 REVIEW; in `/2` the FAIL rules below block the script. **On a `production_script/3` (D-58) the metronomes are retired and
the cue logic inverts:** pacing follows new information, not a clock (the per-row "/3" notes below); silence is the default and
a cue exists only for a named story event (`cue.event`: reveal, impact, transition, build, diegetic, take or place). A `/2`
script keeps the old contract unchanged.

| ID | Rule | Severity |
|---|---|---|
| VB-00 | A legacy `production_script/1` without beats gets one notice: new episodes are written as `/2`. | REVIEW |
| VB-01 | On `/2`: **a beat about every 1.5 s while the narrator speaks** (the metronome). Any visual event counts (a new picture, a reframe, an accent, a bubble, a data visual, a card, a beat); a long gap is a REVIEW, a longer one a FAIL, and a segment's mean gap is checked too. On `/3`: **pacing follows new information, not a clock** — only real dead air while the narrator speaks is flagged (a REVIEW line and a FAIL line, no mean rule). Every number is [BP-36](SOURCED_RULES.md) (house, D-58). **How VB-01 and BP-40 relate:** both count the same events (a cut, a bubble, an accent, a data visual, a card, a visual beat tied to a narration word: VB-12, [BP-93](SOURCED_RULES.md)); BP-40 judges every still of the video by section (the hook window, the body), VB-01 only the stretches where the narrator speaks. In the hook window BP-40 is the stricter limit, in the body VB-01's FAIL is; both are met by the same beats. Guidance for the beat-writer: in the hook and climax keep within BP-40's hook limit, in the body let new information set the pace inside VB-01's limits, one pattern interrupt in BP-41's window. How often the picture itself changes is BP-40 (pictures a minute and still limits; PV-24 RHYTHM). Shorts follow BP-45 instead. | REVIEW / FAIL |
| VB-02 | On `/2`: **in dialogue the face changes about once a second** (a REVIEW line and a FAIL line for the longest stretch without a change). On `/3`: **reactions, not a metronome** — a reaction where a line lands is a choice, never a quota (no per-line minimum since [D-64](DECISIONS_AND_OPEN_QUESTIONS.md): a face swap on every line made every line a cut), and a long stretch without one is a REVIEW; every number is [BP-37](SOURCED_RULES.md) (house, all REVIEW). Two changes of one face closer than [BP-33](SOURCED_RULES.md)'s hold are flicker (REVIEW; BP-33 replaced the old 0.7 s). On a `reveal` line prefer the LISTENER's face (`who` != the speaker). The same expression twice in a row is not a change. | REVIEW / FAIL |
| VB-03 | **Every beat has a reason and belongs to its instant.** `why` (at least three words) says what in the line it shows; `at` is a phrase of its own line, in the order the beats land (FAIL). A beat whose words share nothing with its line or the lines next to it is a REVIEW. | FAIL / REVIEW |
| VB-04 | **Few words, no number without a source.** A beat shows at most [BP-38](SOURCED_RULES.md)'s words; a digit on screen or any chart needs a claim id on the beat or its line (invariant 5); a bars chart has BP-38's number of bars. | FAIL |
| VB-05 | **Variety.** Only a short run of beats of one kind in a row in a segment, and only a share of a segment's beats as words (show the thing instead): a hypothesis, [BP-82](SOURCED_RULES.md). | REVIEW |
| VB-06 | **The render can draw it.** An expression names a hero of the cast (`who`, default the line's speaker) and that face is in the shot's picture (`speakers` point) or the hero has a cut-out for that expression (`cast.<id>.expressions`). A prop without a cut-out is drawn as a word sticker (REVIEW). | FAIL / REVIEW |
| VB-07 | **Few beat overlays on screen at once** ([BP-82](SOURCED_RULES.md)). | REVIEW |
| VB-08 | On `/2`: **every beat names its cue** (`cue.sound` from `audio/cues.py`, or `none` with a reason); a narration beat with `none` and no effect at its moment is a FAIL. On `/3` this **inverts** (D-58): silence is the default and never a finding; a cue is opt-in and must name its story event (`cue.event`: reveal, impact, transition, build, diegetic, take, place) — a cue without an event is a FAIL. The mickey-mousing warning in the cue evidence below always said so; `/2` mandated the anti-pattern (414 cues on Syndicate Wars). On every schema: a cue keeps [BP-64](SOURCED_RULES.md)'s length and level (an earcon: BP-58's one-shot floor does not apply), starts on the beat's first frame, is never ducked, never doubles a sound effect and keeps [BP-39](SOURCED_RULES.md)'s distance from an effect (none under a playing one) and between two cues, and with a cue the layers stay within BP-56's cap (AL-01). Expression changes are silent, except one big take a line (surprised, scared, angry, joyful) that may carry a cue; a cue on a quiet expression is a REVIEW, two cued expressions on one line a FAIL. A cue counts as the sound AL-03 asks for on a hard accent. | FAIL / REVIEW |
| VB-10 | **A repeated sound stops meaning anything** (D-58, `/3`). The same cue sound on two consecutive cues is a REVIEW; the same sound too often inside a window is a FAIL ([BP-80](SOURCED_RULES.md)). The mixer also rotates three deterministic pitch variants per sound (1.0 and plus or minus [BP-57](SOURCED_RULES.md)'s pitch jitter, `audio/cues.VARIANTS`), so two presses of one trigger never play the identical waveform — the "one press plays many times" bug (the creator, 2026-10-19). | FAIL / REVIEW |
| VB-11 | **Cue density** (D-58, `/3`). Cues a minute across the video have a REVIEW and a FAIL line (Syndicate Wars shipped 33/min and nothing read as meaningful), a burst inside a few seconds is a REVIEW, and emphasis cues (thud, chime, rise, fall) are capped per line (FAIL); every number is [BP-81](SOURCED_RULES.md). Cues count toward AL-02's events. | FAIL / REVIEW |
| VB-12 | On `/3`: **a beat needs a word** ([D-64](DECISIONS_AND_OPEN_QUESTIONS.md)). A beat is new information only when it is tied to a narration word: on a narrator line, with a content word in its `at` (what it shows is VB-03's check). An untied beat is reported and does not count for VB-01 or BP-40's stills; no rule asks for a beat on a timer ([BP-93](SOURCED_RULES.md)). | REVIEW |
| VB-09 | **Expression sheets** (D-55, `production/faces.py`). A hero who changes expression in dialogue has one `cast.<id>.face_sheet`: 8-12 close-ups (about 10) on flat chroma green (palette token `chroma_key`), always including the base set neutral, joyful, sad, scared, angry, surprised; painted once from the hero's reference picture (`ref`, invariant 6: the same face, never redrawn) through `paint plan --faces` -> approve -> run, and reused in every scene and episode. Every expression beat names an expression of its hero's sheet. With the sheet painted, the dialogue frame is the scene's own picture zoomed in 1.3x on the face and blurred, with the keyed close-up of the current expression over it, swapped on every change; without it the face push and emotion mark stand in. A close-up whose edge does not key out cleanly (under 85 %) is a REVIEW. | FAIL / REVIEW |

**Defaults chosen (2026-10-19, the creator may change them):** target 1.5 s with the tolerances above; expression vocabulary
neutral, curious, surprised, joyful, amused, smug, confused, doubtful, worried, scared, angry, sad, determined, deadpan (the style
bible's eight plus the creator's anger, joy, doubt and four more). A painted picture cannot change its face, so an expression is
shown by a push in on the face (`speakers` point), a pop toward it on each change and a drawn emotion mark beside it (vein,
sparkles, sweat drop, ?, !, swirl...); when the hero has cut-outs (`cast.<id>.expressions`, for example the analyst's
`a_amused`, `a_startled`, `a_think`, `a_shrug`), a face inset swaps them on every change. When the narrator says something
abstract, the beat shows the operative word as a sign (question, cross for "no/not", arrows for more/less, check, clock for
time, equals/plus) or rings the thing in the picture; a number becomes a counter or bars only with a claim.

**Cue evidence.** A 60 ms tone in sync with a visual change pulls attention to it and speeds finding it ("pip and pop": Van der
Burg, Olivers, Bronkhorst and Theeuwes 2008, J Exp Psychol HPP 34(5); temporal-order study, Journal of Vision 8(5):2, 2008);
the Journal of Vision paper's introduction reports that search still gains when the tone also falls on a distractor in 80 % of
trials, but loses when it always falls on a distractor: a tone that marks the wrong things, or everything, stops helping.
Interface sounds should be "as brief as possible", used "in moderation, or they can quickly become overwhelming", "just a few
sounds that are easily distinguishable" ([Google conversation design: earcons](https://developers.google.com/assistant/conversation-design/earcons)).
Matching a sound to every movement ("mickey-mousing") "can lead to a very artificial experience" (Connor 2019,
[animationstudies 2.0](https://blog.animationstudies.org/synchronization-and-synchresis-avoiding-mickey-mousing-in-sound-design/)).
Hence: ten short, distinct cues, light and quiet, one per narration beat (the creator's ask; the `/2` rule: on `/3` cues are opt-in, VB-08), and **silent expression changes in
dialogue**, because there the voice is already sounding once a second, a cue per face change would sit on every word and mask
it (AL-04: the voice first), and a tone on every change is the case where the attention gain is no longer shown. One cue a line is kept for the
big take, the moment a cartoon would score anyway. The cue timings and levels are product hypotheses; the creator's ear and the
channel's retention decide.

## Register (RG)

The AI register: the vocabulary and the shapes a language model overuses, which a listener hears as machine writing. Checked by
`scripting/register_lint.py` on every text the viewer hears or reads (narrator and hero lines, bubbles, card and HUD text; the
Shorts, pinned comment and thumbnail text join with P9). Prompt text for image and video models is out of scope (KP rules). The
word lists live in the registry only: tier 1 in [BP-140](SOURCED_RULES.md) (house, FAIL), tier 2 and the densities in
[BP-114](SOURCED_RULES.md) (hypothesis, REVIEW). Matching is plain, not negation-aware: "never delve" is still the register.

| ID | Rule | Severity |
|---|---|---|
| RG-01 | **Tier 1** (N-16): a word of BP-140's `register_words`, or a sentence-initial "Additionally,", "Moreover," or "Furthermore,", outside the allow-list. Dialogue counts: the model writes the heroes too. | FAIL (house, the creator 2026-10-29) |
| RG-02 | **Tier 2** (N-17): soft words and phrases of BP-114 (`lexicon`, `phrases`): more than `review_hits_per_300_words` hits in one segment. | REVIEW |
| RG-03 | **Structure densities** (N-17), narration only, per 1,000 spoken words: triplets, "It's not X. It's Y." pivots, participial tails, em dashes, a "rather than" chain; the limits are BP-114's. Nominalisations are only reported. A text of under 1,000 words may carry one of each tell. Hero lines are never measured for structure. | REVIEW |
| RG-04 | **Summarising opener or closer**: "In conclusion", "Ultimately,", "Overall," and the like on a segment's first line or the script's last line (`openers` of BP-114). | REVIEW |
| RG-05 | **An allow-list entry has a reason and a note.** `register_allow.json` next to the script holds `{term, reason: literal | quote | name, note}`; the note names the segment or line it covers, or says `all`. An entry without a reason or a note is refused and the term still fires. | FAIL (invariant 7) |

Built-in exemptions: text inside a documented quotation (a line that cites a `quote` claim) and a capitalised proper noun in
the middle of a sentence ("the Renowned" as a ship). A sentence-initial capital is not exempt. The lexicon is dated: older than
BP-140's `recheck_days` since its `checked_on`, one REVIEW per run asks for a re-check.

## The writers' room

These are the stages and gates. How to run them is in the skill `story-engine`.

| # | Stage (page the main agent follows; stage 7 is spawned, OR-20) | Owns | Gate |
|---|---|---|---|
| 1b | variant planner (a step of `story-architect`, [OR-31](ORCHESTRATION.md)) | `script_variants.json`: two or three priced variants, the creator's pick | VP checks, the critic's score, `chosen` set |
| 1 | `story-architect` | `drama`, `cast`, segment skeleton, scene headers (`scene`, SC-01) | PV-33, PV-48 0 FAIL |
| 2 | `scene-writer` (skill `dialogue-scenes`) | segment `lines` with `to` / `intent` | `stage_guard writer`, PV-12, PV-33, PV-48 |
| 2b | `beat-writer` (same segment, right after the writer) | line `visual_beats`; on `/3` cues opt-in and event-bound | `stage_guard beats`, PV-44 (VB rules) |
| 3 | `performance-director` | line delivery | `stage_guard performer` (words frozen) |
| 4 | `edit-planner` | shots, accents, audio, visuals; a beat's `pos` only | `stage_guard editor`, PV-24, PV-35, PV-36, PV-44 |
| 4b | sound pass (a step of `edit-planner`, after the read is timed; [AUDIO_SYSTEM](AUDIO_SYSTEM.md) "Sound director") | nothing in the script; writes `audio/` only | `stage_guard sound` (script unchanged), SD checks 0 FAIL |
| 5 | `voice-caster` | `voice`, `cast.<id>.voice` | `stage_guard caster`, PV-10, PV-32 |
| 6 | `shorts-writer` | `shorts` | `stage_guard shorts`, PV-28, PV-34 |
| 7 | `script-critic` | findings only; on `/3` also the integrated production-coherence review `editorial_review/2` ([SCRIPTING_SPEC](SCRIPTING_SPEC.md) section 5.2, D-60) ; a passing review also writes `story_page.md`, the whole story on one page in Georgian and why it is well told ([BP-89](SOURCED_RULES.md), EG-23) | editorial gate (EG); at most 2 rounds, then creator approval #1 of the finished script, recorded in `episode.script_approval` ([OR-17](ORCHESTRATION.md)) |

Why this framing holds a mid-size model on course:
1. **Separate the story from its technical detail.** The narrative is written first, and the technical layers are added afterwards on frozen words. Hierarchical, staged generation (Dramatron; the two-stage screenplay study; DOC outlines) keeps long-range coherence and pacing better than writing everything in one pass.
2. **Give every call the map, and only its own territory.** The whole one-line skeleton goes with every call, so the agent always knows where the story is going. Only the segment being written is attached in full. Dramatron's participants found its dialogue inconsistent because a scene's dialogue never saw the earlier scenes' dialogue; the skeleton plus the last three lines fix that.
3. **Check with code between stages** (prompt chaining with programmatic gates). Each stage owns its fields, and the stage guard proves it.
4. **The critic gets a fresh context** (the evaluator-optimizer pattern). Each finding goes back to the stage that owns it, for at most two rounds.
5. **Strict, schema-shaped tools:** the JSON Schema and the validators make the common mistakes impossible rather than discouraged.
