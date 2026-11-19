# SK-1 report: the story layer (S1 research, S2 structure, S3 narration; dialogue)

Stream W8, phase A, 2026-11-19. Rule SK-1 (creator 18:50, plan P-3): read our skill in full, open at least three public
alternatives, run one trial task, record replace / enrich / keep with a one-line reason, and split every rule into
code (a number, a count, a yes/no) or skill (judgement). Cost: $0. Nothing here changes `.claude/skills/` (phase B does,
after W1's PR); nothing is vendored by this stream.

## 0. How the evidence was gathered (and its limits)

- Public repositories were cloned with `git clone --depth 1` into a scratch folder and their `SKILL.md` files were read in
  the session. GitHub's REST API for those repositories is closed to this session (403), so **star counts are from the
  public repository search on 2026-11-19** and the commit is the cloned `HEAD`.
- Not reachable, so not counted: `Jamie-BitFlight/claude_skills` and `szoloth/skills` (raw README 404, `git ls-remote`
  asks for credentials: private, renamed or removed). They are replaced below by `elvisun/newsjack` and `daymade/claude-code-skills`.
- "Read in full" applies to our four skills and to `DirectorSKILL/SKILL.md`. For public alternatives I read frontmatter, the
  workflow/rules sections and the files named in the table; a long reference file that I did not open is marked *not opened*.
- A trial is run by following the skill's method on the real 60 s (ep_truce_1914 S01_SH001..S02_SH005, narration lines
  S01_L001..S02_L005) or, where the 60 s has no such material, on the nearest real lines. It shows what the method finds;
  it is one run, not a benchmark.

| Repo | Licence | Stars (search of 2026-11-19) | Commit read |
|---|---|---|---|
| jtydhr88/screenwriting-skills | MIT + NOTICE (book quotations not relicensed) | 2121 | `51115f18d160` (2026-10-02) |
| danjdewhurst/story-skills | MIT | 434 | `33085ccc3ceb` (2026-11-14) |
| jeffreytse/grimoire-core | MIT | 8 | `7ff5861b0083` |
| SkillMedev/skills | MIT | 25 | `97a13607d669` |
| ur-grue/autopunk-media-skills | MIT | 47 | `39e119bfef25` |
| abengkris/scripthis | MIT | 2 | `21e5135648f3` |
| vyralcontent/content-skills | MIT | 257 | `349e495d9702` (2026-06-22) |
| TheCraigHewitt/skills | MIT | 175 | `fdbf39b61fbc` |
| mohitagw15856/pm-claude-skills | MIT | 1576 | `c4679f94f256` |
| jscraik/Agent-Skills | Apache-2.0 | 9 | `29201925e182` |
| elvisun/newsjack | MIT | 1702 | `be1368c38e4f` (2026-11-16) |
| jamditis/claude-skills-journalism | MIT | 457 | `a6383bd0c4cb` |
| daymade/claude-code-skills | MIT | 1539 | `2393e2e5a82e` |
| akitaonrails/my-skills | **none** (no licence file) | 310 | `1aba042a7775` |
| wuwangzhang1216/DirectorSKILL | MIT | 387 | `c65ae0d14457` (2026-08-31) |

## 1. story-engine (S2, with S1's stage 0 and S3's stage 1b)

**Our skill, 12.5 KB, read in full.** Rules it carries: seven gated stages (research, variants, skeleton, scene, beats,
performance, edit, casting, Shorts, critic) with each stage owning its fields (`stage_guard`); twelve premises scored then one
premise, a yes/no dramatic question, a promise; each hero has want and flaw, the lead also need and change (ST-04); one of
three beat templates A/B/C, midpoint inside BP-75's share (ST-12), a turn at least every BP-76 gap (ST-13); every join BUT or
THEREFORE (ST-02); open loops at least every BP-42 interval and a set-up in the first third (ST-05, ST-06); at least three needs
(ST-08); objectivity labelled (ST-09); show-don't-tell and full immersion on /3 (SC-11, SC-12); the re-read rule (OR-32); the
creator approves the script before anything is paid (OR-17). Most of that is **process and gates**, which no public skill has.

| Alternative (opened) | What it is | Fit for us |
|---|---|---|
| `jtydhr88` **sw-story-structure** (31 KB, `reference.md` 14 KB *not opened*) | Six structure systems merged (Field paradigm, Snyder 15 beats, McKee event/scene/sequence/act, Hoxter nine beats, Hicks three acts as attraction / anticipation / satisfaction, Lu Jun's Chinese short-play methods). Ends with a diagnosis checklist and a premise-to-script workflow. Body is **Chinese**; the skill says the output language follows the question language. | Best coverage, also a short-form chapter (起承转合, "入戏要快", eight openings). Reads fine for the model; our team cannot proofread it, so it is vendored whole and never edited. |
| `jtydhr88` **sw-premise-theme** (24 KB, headings and first lines read) | Premise as tyrant (Egri), controlling idea = value + cause (McKee), logline tests. | Feeds our "premise, question, promise" step. |
| `jtydhr88` **sw-writers-room** (40 KB, headings read) | How a staffed TV room breaks a story, pitch, step deals, notes. | **No fit**: it is about a human staff. Not vendored. |
| `danjdewhurst` **plot-structure** (+ **premise-workshop**, headings and first 80 lines read; `references/` *not opened*) | Novel-length arcs kept as files under `plot/`, needs `story.md`, the `story-init` skill and a `story` CLI; beats are recorded as chapter fields. | Methods are good (structure models, setup/payoff records, try/fail) but the skill **needs a novel project and a CLI we do not have**: copied whole it would not run. Only `references/try-fail.md` and `scene-sequel.md` are worth copying as plain reference text. |
| `jeffreytse` **design-story-structure** (4 KB) | Seven steps with percentage marks (inciting incident 10-12 %, break 25 %, midpoint 50 %, dark night 75 %). | Too thin; our ST-12 already has the midpoint band from a sourced rule. |
| `SkillMedev` **story-structure-architect** (9 KB) | Tension curve, causality audit ("therefore / but" not "and then"), setups and payoffs audit. | Same checks as our ST-02, ST-05, ST-06; adds the **tension-curve sketch** as a diagnostic. |
| `ur-grue` **beat-sheet-builder** (9 KB) | 15-beat map from a premise; output 600-900 words. | Feature-film scale. |

**Trial (the 60 s through sw-story-structure's value method vs story-engine's gates).** McKee's test: a scene or sequence is
only an event if a value flips charge. Written for the 10 shots (value: safety / hope):

| Shot | Narration (clock) | Charge change |
|---|---|---|
| S01_SH001 | "Christmas morning, 1914." (3.0 s) | calm (+) |
| S01_SH002 | "In a few seconds, this man will walk toward the German guns." | + to - (threat promised) |
| S01_SH003 | "Unarmed. Across the ground where men had been dying..." | - to a charged + (the act) |
| S01_SH004 | "...thousands of soldiers on both sides did the same." | scale jump, one man to thousands (+) |
| S01_SH005 | "This is the day the war stopped... How it began, with a song. And how it ended." | open loop, the promise |
| S02_SH001 | "The war had begun in August. Everyone said it would be over by Christmas." | + (hope) |
| S02_SH002 | "By December it had dug itself into the ground..." | - |
| S02_SH003 | "...close enough to hear each other cough." | - held tension |
| S02_SH004 | "Mud to the knee. Water in every boot. A sniper..." | - |
| S02_SH005 | "Private Thomas Hale had read the same line by the brazier all week." | irony: + hope read in a - place |

Finding: four of the five S02 shots move one way (down) with narrated exposition, and only S02_SH005 turns the value back;
the structure method flags it as "flat exposition, 25 s before the next charge flip". `story_lint` (our gates) reports
**0 FAIL, 0 REVIEW** on the same script because on a `4.0.0` script it only runs ST-02, ST-13, ST-14, ST-21 and the V4 chain
rules: it cannot see this. So the public method finds something our current code does not; our code finds the other kind of
fault (a broken `cause_from_segment_id` chain, which the public skills cannot know about).

**Verdict: ENRICH.** Reason: our stage order, gates and approval stay (nothing public has them); the structure knowledge
(value turns, setup/payoff, tension curve, openings) is replaced by the vendored text instead of our paraphrase.
**Vendor list for W1:** `sw-story-structure` (with `reference.md`), `sw-premise-theme`, `sw-workflow` (its `terms.md` is linked
from the others). **Not vendored:** `sw-writers-room`, danjdewhurst's two skills (reference files only if the plan thread wants
them). **`sw-truby-anatomy`** (21 KB, headings, sections 1-2 and the workflow interface read; plan S2 names it): Truby's 22 steps, middle-act machinery (ghost, fake ally, fake defeat), four-corner opposition, moral-argument chain. It says itself that it is used after or instead of the page-map skill for long forms. Wrong scale for a 6 minute explainer: **do not vendor now**; revisit if an episode needs a long middle act.
**To code (SK-2), listed for W2:** on a v4 script `story_lint` has no code for ST-01, ST-03..ST-12, ST-15..ST-20, ST-22..ST-24
(want and flaw, join words, midpoint band, turn gap, loops, needs, objectivity): they exist only on the pre-v4 path.
A new check "a value charge change at least every N seconds" has no number yet: it is a hypothesis until two source types
back it, not a rule.

## 2. dialogue-scenes (S2)

**Our skill, 14 KB, read in full.** Scene header with 13 fields (place, time, present, why_now, pov, want, obstacle_want,
value, open/close charge, turn, exit, surface_topic, real_subject; SC-01), Johnston's 8 questions (SC-06), enter late and
leave early, narrator-to-scene hand-off unit, turn-taking numbers (line 5-15 words, cap 35, one 25-60-word speech; DW-06),
Stein's five deflection moves (DW-12), subtext (SC-10), exposition as ammunition with the K/U table (DW-13, SC-07), full
immersion and show-don't-tell (SC-08, SC-11, SC-12), conflict modes, voice bibles, the Syndicate Wars worked example. Its
v4.3 note: every hero line sits in a `video`-route shot.

| Alternative (opened) | Fit |
|---|---|
| `jtydhr88` **sw-dialogue** (24 KB, headings and intro read) | McKee on dialogue as action, said / unsaid / unsayable, exposition as ammunition, beat analysis, a diagnosis checklist. Same ideas as ours, deeper on sources. |
| `jtydhr88` **sw-scene-craft** (23 KB, headings read) | McKee's five-step scene design, enter late and leave early, "action beats dialogue", props and details; a "how to write a scene" workflow. |
| `danjdewhurst` **scene-craft** (10 KB, workflow read; its `references/dialogue-subtext.md`, `try-fail.md` *not opened*) | Tied to a story project (`scenes/` files, `story` CLI); outcome vocabulary yes / no / yes-but / no-and. |
| `jeffreytse` **design-dialogue-craft** (8 KB) | Ten steps: purpose, subtext, no tags, voices, cut first and last lines. All inside our skill. |
| `ur-grue` **dialogue-polisher** (9 KB) / `abengkris` **dialogue-doctor** (2 KB) | Rewrite helpers; no new rule. |

**Trial.** The 60 s has no spoken character line (the first clip-spoken line is S02_SH006, 61.25 s). I ran sw-dialogue's
on-the-nose test on the nearest real lines, outside the slice: Thomas: "Home by Christmas, she says. Didn't say which one."
then Harris: "Keep your head down, and you might see one." Method result: both lines are subtext-carrying (Thomas deflects
the letter into a joke, Harris answers a different question with a threat); nothing is on the nose; the pair has no
opposing wants named, so SC-03 would ask for them in a header. Our `scene_lint` has no `scene` header for these shots on the
v4 path either (it runs SC-01..06, SC-10 and V4 rules but not SC-07..SC-09, SC-11, SC-12).

**Verdict: KEEP ours, enrich from sw-dialogue and sw-scene-craft.** Reason: our header, hand-off unit and numbers are
already richer than every public alternative; the public text adds source depth (McKee beat analysis, the unsayable), not
rules. **Vendor list for W1:** `sw-dialogue`, `sw-scene-craft`. **Not vendored:** the four small helpers (no new content).
**To code:** nothing new; the SC-07..SC-09, SC-11, SC-12 gap on the v4 path goes to W2.

## 3. narration-script (S3)

**Our skill, 30 KB, read in full.** Voice of the channel for ElevenLabs v4: the hook is the first spoken sentence in one of
four BP-03 forms (N-01), 30-second contract (N-11), one capitalised stressed word per sentence (N-04), at most one ellipsis per
beat (N-03), sentence cap and median (N-05), a question per 150 words (N-06), interjections (N-07), tags only for delivery
(N-09), no ellipsis in a question and wh-questions at most 12 words (N-10), contractions and numbers for the ear (N-12, N-13), no
press-release lines (N-14), no AI-register words (N-16, N-17), every beat ends on an open loop (N-02), reported speech rules, speech
registers, per-line audit. The numbers already live in `sourced_rules.json` and `narration_lint` reads them.

| Alternative (opened) | Fit |
|---|---|
| `vyralcontent` **viral-hooks** (10 KB, workflow and checklist read; `references/` *not opened*) | Short-form: hook = visual + verbal + on-screen text in the first 1-3 s; a batch of six to ten across at least three archetypes; checklist (specific noun, payoff visible, no throat-clearing, resolves by second 3, works with sound off); anti-patterns. |
| `TheCraigHewitt` **hook-writing** (YouTube long form, first 30 s, core principles and the three-step hook formula read) | Matches the title's promise in the first 5 s, hook is not an introduction, front-load the best material, spoken words, visuals and text say the same thing. |
| `mohitagw15856` **youtube-script-writer** (full structure read) | Packaging, cold open, chapters, "pattern interrupts every 4-8 s ... whoosh, ding, pop". **The interrupt rule contradicts our decisions** (one continuous bed, sound only where a story event earns it), so that part is rejected. |
| `jscraik` **youtube-hooks-scripts** (read in full, 70 lines) | A generic template with no concrete rules. No fit. |

**Trial.** `narration_lint` on the 10 narrator lines of the 60 s: **0 FAIL, 14 REVIEW** (N-02 on every beat: all ten end
closed; N-11: no question or turn in the first 85 words; N-12: no "you" in 139 words; N-06: 0 questions in 139 words; N-07:
no interjection). viral-hooks' checklist on the hook "Christmas morning, 1914." (3.0 s on the clock): specific noun and date
pass, no throat-clearing passes, **the visual layer fails**: the frame is an empty field with no on-screen element, which
the skill calls "a flat opening frame". hook-writing says the title promise ("The Day We Were Not Enemies") should be
previewed inside five seconds; the promise first appears in S01_L005 at about 24 s on the clock. Both public skills point to
the hook layer (visual and promise placement), our lint points to rhythm and loops; none overlaps.

**Verdict: ENRICH.** Reason: voice, pace, tags and the numbers are ours and not found elsewhere; the **three-layer hook** and
the long-form 30-second promise test are the public knowledge we lack. **Vendor list for W1:** `viral-hooks` (with its
references), `hook-writing`. **Not vendored:** `youtube-script-writer` (rule conflict), `youtube-hooks-scripts` (empty).
**To code:** the visual-layer check ("a hook frame shows an event or text at the first caption") needs a number nobody has
sourced: hypothesis. The title-promise check exists as N-11.

## 4. science-grounding (S1)

**Our skill, 3.4 KB, read in full.** Question first plus sub-questions; sources by theme, best first, two independent sources
per number; claim map with id, sentence, URL, date, label (established / model / reasoned / guess); counterfactuals are
arguments with premises, step, limit; round numbers in speech; cliché check; vidIQ for packaging only; say what was and was
not verified. Thin on method: it has no primary-source rule, no quote check and no rating discipline.

| Alternative (opened) | Fit |
|---|---|
| `elvisun/newsjack` **fact-check** (22 KB, doctrine, methods and labels read) | "The burden of proof is on the speaker"; extract every claim, verify each alone, climb the source tier (primary > secondary > tertiary), lateral reading, two independent sources, four status labels (Verified, Missing source, Disputed, Unverifiable), age limits for facts, mandatory warning block. Aimed at PR copy but the method is general. |
| `jamditis` **fact-check-workflow** (11 KB) and **source-verification** (SIFT) | Claim log template, primary-first research, rating scale, evidence checklist. Both begin with an untrusted-content contract (useful for web retrieval). |
| `daymade` **fact-checker** (8.6 KB) | Edits a document and proposes corrections with approval; built for technical specifications. |
| `akitaonrails` **fact-check** (11 KB) | Adversarial two-pass design with cheap checkers; **no licence file: not vendorable**. |

**Trial (newsjack's method on our own claim map, offline).** Every sentence of the 10 narrator lines maps to a claim (all
10 have `basis_claim_ids`), which our PV-37 already requires. Run on the claims they cite:
- C-05 and C-06 (S02_L001, S02_L002) rest on a **single secondary source** (history.com). Under source-tier climbing and the
  two-source rule they stay "Missing source" until a second source is added.
- **Wording overstates its claim:** S02_L001 says "Everyone said it would be over by Christmas"; C-05 says "many expected".
- S02_L003 says the sides "sat close enough to hear each other cough" ("here, in Flanders"); C-07 only says "about fifty
  yards in places (elsewhere up to about 300)": the cough detail and the claim that this holds "in Flanders" have no row.
- All 23 C-rows are secondary or tertiary web pages; no primary document (war diary, letter) is cited for the 60 s.
These are findings for the plan thread; this stream does not rewrite words (OR-17 approved them, plan W8).

**Verdict: ENRICH.** Reason: our label scheme (what kind of statement) stays, and the vendored method adds the second axis
we lack (how well it was verified) and the wording-versus-claim check. **Vendor list for W1:** `newsjack/skills/fact-check`
(it mentions optional `ETHICS.md` / `WHY-NOT-SPAM.md`; W1 should copy the folder as is and note they are absent),
`source-verification`, `fact-check-workflow`. **Not vendored:** `daymade/fact-checker`, `akitaonrails/fact-check` (no licence).
**To code:** PV-37 exists (claim per sentence). New: "narrated sentence not stronger than its claim" has no deterministic
test (quantifier words: everyone, always, never, all) — a candidate lint listed for W2; "a numeric claim cites at least two
sources" is checkable from `claim_map.md` and has no code.

## 5. Summary and handoff to W1 (via the plan thread)

| Our skill | Verdict | Vendor (W1) | Stays ours |
|---|---|---|---|
| story-engine | enrich | sw-story-structure (+reference.md), sw-premise-theme, sw-workflow | stage order, gates, stage_guard, approvals |
| dialogue-scenes | keep, enrich | sw-dialogue, sw-scene-craft | scene header, hand-off unit, SC/DW numbers |
| narration-script | enrich | viral-hooks, hook-writing | voice, tags, pace, N-rules |
| science-grounding | enrich | newsjack fact-check, source-verification, fact-check-workflow | claim labels, counterfactual rule |

W2 candidates (no code yet): story_lint ST rules on v4 scripts; scene_lint SC-07..SC-09, SC-11, SC-12 on v4; "narrated sentence
not stronger than its claim"; "numeric claim has two sources". Each needs its source types before it becomes a threshold.

Phase B (after W1's PR) turns each overlay into "when to load which vendored skill, what stays ours, which validator checks
the result", without pasting upstream text.
