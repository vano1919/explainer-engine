# Progress log

Append one entry per phase boundary: completed work, state, files changed, test results, decisions, blockers,
cost (estimate/actual), next step, recovery instructions.

## 2026-10-15 — Plan approved (Mode A)
- Approved plan: `docs/PLAN_2026-10-15.md`. Creator decisions: D-13 (Claude Code sessions draft research and scripts),
  D-21 (separate repository), repo name `explainer-engine`.
- Spend: Gemini $0.00 of $10; vidIQ 0 of 200 credits (account balance read 2026-10-15: 395, call cost 0).

## 2026-10-15 — Phase 1: new repo, inventory & safeguards (in progress)
- Blocker: creating `vano1919/explainer-engine` through the GitHub integration returned 403 ("Resource not accessible
  by integration"). The scaffold was built and committed in a local repository; it is pushed once the creator creates
  the empty repository and it is attached to the session.
- Done: scaffold (`explainer_engine/core`, `explainer_engine/audio`, `tests/unit`, `docs/`), `.gitignore` (jobs, media,
  models, keys), `requirements.txt` (numpy, jsonschema, pyyaml, pytest), `pytest.ini`, `setup.ps1`, `CLAUDE.md`;
  copied modules with provenance (`docs/PROVENANCE.md`); `docs/REPO_REUSE_AUDIT.md`.
- Tests (Linux sandbox, Python 3.13, fresh venv): `python -m pytest -q` → 24 passed. The guard test was checked
  against a planted `from tmr_engine import x` (it failed as intended). Not tested: `setup.ps1` on Windows.
- Not done in Phase 1 by design: Kokoro, Node/Remotion, schemas (Phases 3–5).
- Next: Phase 2, the decision and specification pack (split the plan into the canonical docs), Kit reference sheet
  draft, palette contrast check.
- Recovery: the local clone is a plain git repository; `git push -u origin main` after `git remote add origin ...`.

## 2026-10-15 — Phase 1 pushed
- `vano1919/explainer-engine` created by the creator; commit `a41e47b` pushed to `main` (the repo was empty, so no PR).
  Remote clone checked: 25 files, 24 tests pass.

## 2026-10-15 — Phase 2: decision and specification pack (branch `phase-2-spec-pack`, draft PR)
- Done: 19 canonical documents + `docs/INDEX.md`; `explainer_engine/design/palette.json` + `palette.py` (contrast and
  rules); `assets/characters/kit/kit_reference.svg` (draft v0: body, limbs, two lid states, 8 expressions, 6 speech
  mouths); `explainer_engine/docs_lint.py` (one home per ID, links, JSON fixtures, no hex in docs).
- Measured (palette): ink on paper 14.7:1; every accent colour is 1.5-3.7:1 against paper, below the 3:1 graphics need,
  so accents are fills with an ink stroke and `false_red` text is large-only (D-22). The plan's colour table had not
  stated this; it is now a tested rule.
- Decisions added: D-07 (hook framework, was cited but undefined), D-08 (export targets), D-09 (language), D-22
  (accent rule), D-23 (canonical homes).
- Tests: `python -m pytest -q` -> 36 passed; `python -m explainer_engine.docs_lint` -> 0 findings (verified to fail on a
  planted dangling ID, duplicate definition and broken link). The Kit sheet was rendered with headless Chromium and
  inspected by eye; its first render had clipped labels and box-shaped eyelids, fixed before commit.
- Deviation from the plan (G.2): `.claude/rules/`, skills and hooks are not written in Phase 2. The path-scoping and
  hook syntax for the installed Claude Code version were not verified, and the directive says to verify first and add
  only what a workflow justifies. They are scheduled with Phases 3, 4 and 6 (`docs/CLAUDE_EXECUTION_GUIDE.md`).
- Not verified: the official YouTube thumbnail size limit and chapter minimum (marked "re-verify" in P-17, P-19; checked
  in Phase 7); Fredoka and Inter licence files (recorded in Phase 4).
- Awaiting the creator: review of strategy, identity and Kit's look (approval gate 1 in the decision log; Q2: final name).
- Next: Phase 3, contracts first (JSON Schemas for config, assets, storyboard, audio events, manifests, timing, job
  state, with valid and invalid fixtures).

## 2026-10-15 — Creator feedback on Phase 2 and niche research
- Creator feedback: Kit / the visual direction was disliked; asked why this topic and what it rested on.
- Honest finding written to docs/MARKET_RESEARCH.md B.7: the original topic pick was a reasoned guess under the
  creator's constraints, not measured demand; the supplied report covers Shorts, not 5-11 minute explainers.
- vidIQ research (creator approved ~60 credits): 60 spent (6 outlier searches, 6 keyword researches; 5 credits wasted on
  an unusable generic seed). Account 445 -> 385. Project cap 200: 60 used.
- Result: finance (SE-34) and what-if/space (SE-35) have the widest small-channel breakout evidence; everyday mechanisms
  (SE-29) has real breakouts at our length, mostly about vehicles; stories (SE-33) are kids / third-party IP.
- Decisions: D-01 reopened and then resolved for now by **D-24** (creator: test both arms before choosing); D-04 Kit
  draft v0 rejected, new direction hand-drawn / doodle style (creator, 2026-10-15).
- Next: doodle style samples for the creator's reaction (`assets/style_samples/`), then redesign of the mascot and
  palette (D-04) before Phase 4; Phase 3 (contracts) does not depend on the visual style.

## 2026-10-15 — "Worlds collide" (creator's idea) researched and adopted as D-25
- Creator proposed collisions of worlds and delegated the decision (100-credit limit). Spent 70 (385 -> 315; project 130
  of 200). Findings in docs/MARKET_RESEARCH.md B.8 (SE-37..SE-45).
- Decision D-25 (synthesis): keep the collision idea, restricted to public-domain or factual worlds (eras, prehistory,
  nature, science, myths, technology, money); reject film/game crossovers (third-party IP). The earlier arms live inside
  it. D-01, D-02, D-24 superseded; D-20 (prototype topic) reopened.
- Updated: PROJECT_BRIEF positioning, SCRIPTING_SPEC formats, VIDEO_PARAMETER_SPEC P-03/P-04, PUBLISHING candidates,
  CLAUDE.md summary; style bible marks the Kit sections retired.
- Waiting on the creator: doodle style choice (1/2/3), the prototype topic.

## 2026-10-16 — Crossover analysis episodes (D-26), rights rules, fan research in code
- Creator: analyse how two existing fictional worlds could meet (e.g. two fantasy franchises), simple doodle animation +
  a few dramatic scenes, no copying; find where YouTube and the law draw the line and build it into the rules; every
  crossover script starts from the fans' theories, demands and existing crossovers, balanced for casual viewers and
  hardcore fans, imaginative, not templated.
- Verified (official pages, 2026-10-16): YouTube fair use, copyright strikes, trademark policy; US Copyright Office fair
  use; Warhol v. Goldsmith and the Harry Potter Lexicon case via summaries (V-07..V-12).
- Added: docs/RIGHTS_AND_FAIR_USE.md (RR-01..RR-13); D-26 (amends D-25); P-120..P-125; Q-E13, Q-E14; R-28;
  `rights/ip_check.py` + schema; `research/fan_brief.py` + schema; skill `.claude/skills/crossover-episode`;
  SCRIPTING_SPEC section 7; docs lint knows the RR- prefix.
- Tests: 50 passed (14 new); docs lint 0 findings. Not legal advice: the rules lower risk, they do not prove fair use.
- Style sample `assets/style_samples/traveller_scene_v0.svg`: the traveller (marker line + pencil hatching) on the seam
  between two original worlds, painted-look layers built in code (free), plus three doodle explanation panels. First
  render hid fills (a CSS class overrode them); fixed and re-checked by eye. Waiting on the creator's reaction.

## 2026-10-16 — Creator's visual references (D-27)
- Creator reacted to `traveller_scene_v0` with two images and "I want visuals more like these": (1) our composition
  repainted as a rich painted scene (glowing aurora and sun, volumes, textured paper, three notebook doodle panels);
  (2) the same bean traveller (red scarf, brown satchel, pocket watch) with expressive eyes and hands, a time vortex
  with clock numerals and a shopping cart of Roman props. Saved as `assets/style_samples/creator_reference_01/02`.
- Finding: this quality cannot come from code-drawn SVG. D-27 records the look and a production proposal (reusable
  raster kit, animation and doodle explanations in code); the method is not locked until a consistency test passes.
- No paid call made (Gemini $0 of $10, vidIQ 130 of 200). Waiting on the creator: which tool made the references,
  who generates the kit, mascot/channel name.

## 2026-10-16 — Tool strategy (D-28), channel name proposal (D-29)
- Creator: references were made with Gemini; reuse the TMR project's tools (RunPod image model); generate the mascot's
  moves on green with Gemini once and keep them; other pictures from the cloud model; channel name "Crossword Theories".
- Read TMR evidence (key_green, patch_pose, Z-Image timings and incidents, prices). Z-Image-Turbo licence Apache-2.0
  (official model page). Wrote docs/TOOL_STRATEGY.md with a kit test before any full kit; D-28, D-29 (spelling
  Crossworld proposed). No paid call (Gemini $0, RunPod $0, vidIQ 130 of 200).
- Waiting on the creator: name spelling, RunPod cap, go for the kit test (about $1.20 Gemini + under $0.50 RunPod).

## 2026-10-16 — Kit test run (D-27, D-28)
- Creator approved the test. Gemini (key present in the session, list price re-checked on the pricing page: $0.067 per 1K
  picture): 1 base from the creator's reference, 8 poses, 4 expressions, 2 world backgrounds = 15 pictures, about $1.01.
- Result in docs/TOOL_STRATEGY.md ("Kit test result"): identity held by eye, keying clean, defects listed, 8 s code
  animation rendered. Assets in `assets/characters/traveller/test_v0/` (the mp4 is not committed: media stay out of git).
- Gemini $1.01 of $10 (estimate). RunPod $0 (no cap set). vidIQ 130 of 200. Name D-29 and the RunPod cap still open.

## 2026-10-16 — Resolution question (D-30)
- Creator doubts 1080p on big televisions. Proposed D-30: 1440p master, 2K backgrounds, 1080p fallback; decided after the Phase 4 benchmark. No spend.

## 2026-10-16 — Review of the TMR cloud chain; plan revision proposed (not yet adopted)
- Creator: production runs in the cloud, not on the i5-8400; review the other project's technical abilities and the plan;
  will the Gemini pictures be reused; does a child-faced mascot suit a serious analysing voice ("100 greatest scientists
  dropped into the Stone Age").
- Read (TMR@d88ba8f): cloud/rp.py, Dockerfile, models.json, stages_*.json, RUNBOOK_pods.md, INCIDENTS_RUNPOD.md, handoffs.
  Measured there: a 20-min 2560x1440 30 fps video rendered on a 4090 pod in ~8 min (GPU compositor, moderngl + EGL, NVENC);
  the whole 29-stage chain cost $1.00 / 67 min; Kokoro on the pod CPU is slow (~45 min per 20 min of speech) but ~7-8 min
  in this 4-vCPU cloud sandbox (free); Z-Image ~14 s per picture; a 27B text and vision model runs on the pod.
- Read now (free calls): RunPod balance $7.37, no pod running.
- Proposed, waiting on the creator: hardware baseline = this sandbox + RunPod (replaces invariant 1's PC); renderer = a GPU
  compositor ported from TMR instead of Remotion (D-10), since the art is now painted raster layers; D-30 1440p; mascot
  aged up and silent (a separate narrator voice), see the chat answer of this date.

## 2026-10-16 — Plan revised: cloud-first, GPU compositor, mature mascot (D-31, D-32, D-33)
- Creator approved: take what is needed from TMR (and solve problems found), mascot aged up with other options, RunPod cap $3.
- Docs: D-31/32/33; CLAUDE.md invariant 1; REPO_REUSE_AUDIT port list with problem -> solution; cost ledger (RunPod $3 cap,
  Gemini about $1.34 for 20 pictures).
- Mascot options generated (5 pictures, about $0.34): `assets/characters/mascot_options_v0/`. Waiting on the creator's pick.
- Next after the pick: pose bank for the chosen design (silent mascot: poses and reactions, no mouth states), 2K worlds,
  then Phase 3 contracts and the Phase 4 compositor benchmark on one approved pod.

## 2026-10-16 — Cast chosen (D-33): the analyst (A2) and the companion (B); first 1440p duo test
- Creator picked A2 and B together. Generated 12 analyst + 8 companion pictures and two true-2K worlds; keyed and stored;
  10 s 1440p test scene rendered in code (152 s on the cloud CPU). Spend: Gemini about $3.02 of $10 (estimate); RunPod $0.
- Findings in docs/TOOL_STRATEGY.md ("Cast bank result"): identity held, 2K needs `imageSize`, border defect persists.
- Next: names for the two characters and the channel spelling (D-29), the compositor port and Phase 3 contracts, then the
  one approved pod for the Phase 4 benchmark.

## 2026-10-16 — Names, first topic, reusable sound library (D-29, D-34, D-35)
- Creator: names Dirkus (analyst) and Tick (watch); channel name confirmed; first topic = "100 greatest scientists dropped
  into the Stone Age" (D-20 resolved); asked for Gemini-made movement/reaction sounds in a reusable library.
- Built `audio/foley.py`, `audio/sfx_library.py`, `audio/build_library.py`, schema `sfx_manifest`, tests (60 passed, lint 0).
  Library: 63 sounds (45 procedural foley, 15 Gemini TTS vocal reactions, 3 Lyria clips). Findings in TOOL_STRATEGY
  ("Sound result"). No sound has been heard by a person. Gemini about $3.28 of $10 (estimate), RunPod $0, vidIQ 130/200.
- Next: the creator listens to the audition packs; then the script for the Stone Age episode (research dossier, claim map,
  script) with approval gate #1.


## 2026-10-16 — Scientist caricature cast, test v0 (Stone Age episode)
Creator confirmed: Anatolia setting, "prime-age" arrival rule, start making instead of verifying first, fully animated snappy
video with scientist caricatures acting in parallel with the narration. Story draft: `examples/stone_age/story_draft_v0.md`
(claims still unverified; the creator chose to make first and verify later — the claim map is still required before approval #1).
Made 8 caricatures on flat green (Newton, Einstein, Curie, Darwin, Tesla, Archimedes, Franklin, Nansen) with the Gemini
image model, Dirkus' pose as the style guide only: 8 calls ≈ $0.54 at list price (Gemini total ≈ $3.82 / $10). Keyed with
`key_green`; sheet: `assets/characters/scientists_v0/contact_sheet.png`. Identity is recognisable from description alone
(no photos used). Open: 20th-century likenesses (Einstein, Curie, Tesla) need the rights note in RIGHTS_AND_FAIR_USE.md;
more poses per scientist are only made when a scene needs them.

## 2026-10-16 — Fire test stopped; rule D-36 (scenes only from the local pod)
First 28 s test (Nansen, Franklin, Einstein light a fire; narration by Gemini TTS ≈ $0.03; sound library SFX) was composed over
Gemini-made backgrounds and kept the characters ~30 % of the frame height. The creator rejected the look twice (first the
background, then characters too small) and then restated the binding rule: **Gemini is only for assets reused in future videos;
scene pictures are made on the pod**, and shots must alternate WIDE → MEDIUM → CLOSE-UP (one-frame mixes of epic scenery and
close characters give wrong scale). **My error:** I generated 7 episode-specific backgrounds with Gemini (≈ $0.70, two of them
unused variants) against the 2026-10-11 rule. The pictures stay only as *style targets* for the pod
(`assets/style_samples/stone_age_look_v0/`); they are not used in the episode. Gemini total ≈ $5.0 / $10 (list prices).
Kept as reusable: the 8 scientist caricatures + 6 poses (`assets/characters/scientists_v0/`), the sound library.
Next: shot plan `examples/stone_age/shot_plan_v0.md` for creator review; one pod preflight needs an explicit approved price and time cap.

## 2026-10-16 — First pod run (creator approved: card ≤ $0.95/h, ≤ 45 min, ≈ $0.72 max)
Pictures-only job added to TMR's cloud tooling (`cloud/stages_pictures.json`, `cloud/gen_pictures.py`,
`cloud/jobs/stone_age_day1.json`; branch claude/master-directive-prompt-5rmv2y, commit 84956dd). Pod `9r4woj5fmrq1xj`
(secure RTX 4090, $0.89/h, baked image) with `rp.py guard --max-usd 0.72`: stages podkey, gpu, disk, ntfy, link_env, cuda,
fetch_zimage (33 GB), pictures, store, push all PASSED. 13 pictures 1920×1088, **25–30 s each** (Z-Image-Turbo, 9 steps, CPU
offload; slower than TMR's earlier 14 s at 1536×864), no defective picture, attempts 1. Guard log: **spent ≈ $0.20 of $0.72**.
The pod is gone (guard: "pod is gone"; GET returns 404); pictures are in the HF store `pictures/stone_age_day1`, copies as
JPEG in `examples/stone_age/pictures_v0/`. Balance read before the run $6.61, after $6.07: the difference ($0.55) is larger than
my pod's $0.20 because **another pod, `xjbkftngkcqb7y` (tmr-lab-until-1792154663, created 07:44 UTC, $0.89/h, approved lifetime
to 12:44 UTC), was running and is not mine** — I did not touch it. Closeups (hands, lens, spark, flame) and plates came out
clean; wide shot 1 and the night shots read as the right scale. Next: animatic with the keyed caricatures on the plates.

## 2026-10-16 — Universal Rule Base (D-37), review of the fire animatic, Stone Age script v1, Day 1 timed
The creator sent a channel-wide rule base (hook, ABC shots, cuts on TTS pauses, durations, Ken Burns, transitions) with a
hyper-realistic style modifier. Asked first, because it overturned D-27: the creator **kept the painted look** and added
two rules: the topic sets the palette range, and every shot names an emotion delivered by light and colour. Faces: our
caricature when one exists, else faceless. New canonical doc `docs/UNIVERSAL_RULE_BASE.md` (ID family UR-, added to
docs_lint), D-37, P-60/P-70 superseded, Q-T17. Code: `explainer_engine/edit/shot_rules.py` (check_shots for every [code]
rule, cut placement in pauses by dynamic programming, mood clauses and grades from `edit/moods.json`), 26 tests, including
a regression on the measured fire_scene_v3 edit (`tests/fixtures/fire_v3`, pauses from silencedetect on its narration):
8 of 11 shots out of range, 9 of 10 cuts inside speech, 8 of 11 moves wrong for their type (I first wrote 6 in the plan:
the code count is right), 10 short dissolves without a time jump, no hook question, no emotion or palette.
Changed while building: the first-30-s rule became "every shot stays within its minimum + 1 s" (the plan's "no A over
5.0 s" plus the 5.0 s A minimum left no room for an A shot).
Narration moved to **Kokoro** (am_michael, speed 1.05, ≈ 150 wpm; free, local, with phoneme timings); the Gemini TTS
narration of v3 was topic content and broke D-19 (≈ $0.03, already logged). `examples/stone_age/day1_v1/`: narration
(384 words, 2:34), measured `words.json`, `build_shots.py` → `shots.json` (39 shots: 30 new pod pictures, 9 reused from
pictures_v0), `timing.md`, `check_report.md`: **0 FAIL**, 2 REVIEW (the water and fire beats open on B/C, not A, because
their first sentences are shorter than 5 s). `examples/stone_age/look.json` (palette per phase) and `script_v1.md` (whole
episode, ≈ 1,800 words ≈ 12 min, beats + shot outlines; claims still unverified). Pod job for the 30 new pictures:
TMR `cloud/jobs/stone_age_day1_v2.json` (not run: needs an approved pod cap). Money: $0 this step; RunPod balance $5.50
when read at 09:38 UTC, the foreign pod `xjbkftngkcqb7y` still running and untouched.

## 2026-10-16 — Voice alteration layer (D-38), 7-take voice panel
The creator found `am_michael` too generic but wants Kokoro's timings kept. Plan approved (plan mode), then built:
`audio/voice_layer.py` (style blend, ffmpeg rubberband pitch/formant at tempo 1, warmth/brightness/de-ess shaping copied from
TMR, `timing_preserved`: length ≤ 33 ms and envelope lag ≤ 20 ms, `alter` falls back to the base audio on failure,
`measure`), `audio/narrate.py` (the reproducible path that replaces the hand-run scratch script), schema
`voice_spec.schema.json`, `assets/audio/voices/baseline_michael.json`, 11 tests (suite 97 passed). RVC is specified in
AUDIO_SYSTEM.md but not built: no model with a commercial licence and a consenting speaker exists, and `narrate.py` refuses
an `rvc` spec. Docs: AUDIO_SYSTEM "Voice alteration layer", D-38 (voice choice pending), P-98, P-99, Q-T18, PROVENANCE row.
Measured on the first two paragraphs (33 s), `examples/stone_age/voice_panel/p*.json`: median pitch baseline 113.7 Hz;
michael+george 40 % 123.1; +onyx 40 % 100.0; +lewis 40 % 107.1; george 25 % + onyx 25 % 109.6. Blends change the length by
-3 % to -7.5 % (so `words.json` must be re-measured after the voice is chosen). Pitch −1 st gave 116.5 Hz, −2 st shifted
formants 110.1 Hz, length delta 0 ms, lag 2–3 ms. Sent the creator a 7-take MP3 (20 s each); the choice is theirs by ear.
Day 1 `words.json`/`shots.json` are regenerated once the voice is chosen. Money $0.

## 2026-10-16 — ElevenLabs narrator (D-39), 3 samples, writing for an expressive read
The creator rejected all 7 Kokoro takes ("too stable, flat") and moved the final narrator to ElevenLabs, keeping the
`words.json` contract. No API key in the session, so the creator chose the connector for speech and **Scribe** for word
times. Built `audio/scribe_words.py` (Scribe words + script → `words.json`: written words and punctuation kept, difflib
match on normalised words, numbers spelled both ways, a lone `—`/`...` joins the word before it, unheard words
interpolated and flagged `estimated`, coverage ≥ 97 % or REVIEW) and 5 tests (suite 102 passed, docs_lint 0). Docs: D-39
(D-38 superseded), SCRIPTING_SPEC §8 (punctuation is the pacing and the cut points; emotion in the sentences; tags only in
a separate TTS file; light edits, never a fact), ElevenLabs line in the cost ledger. `examples/stone_age/day1_v2/narration.txt`:
Day 1 retuned for the read (ellipses, dashes, shorter reveal sentences; same facts). Samples (eleven_v4, one 283-character
hook text, library voices): Kenneth 22.6 s, Clyde 24.1 s, Declan Sage 26.5 s; 849 credits ≈ $0.15. The 30-picture pod batch
was approved by the creator but not started: this session's auto-mode permission check refused the pod action; it waits for
the creator to allow it.

## 2026-10-16 — Clyde chosen; tone calibrated; Day 1 read, Scribe timings, new edit (46 shots)
The creator chose Clyde and set the tone: entertainment first, facts second, dry wit from the situation and the characters,
science and history told straight (SCRIPTING_SPEC §8.1). `day1_v2/narration.txt` rewritten with light touches (all, painfully,
real · halfway · naturally · Write that down · yes, that John Snow · Slower, and with more opinions); facts unchanged. Read with
Clyde (eleven_v4) in one call, 170.6 s, 2,337 credits ≈ $0.42; Scribe words: 402 of 402 script words heard (coverage 100 %).
Finding: with raw ElevenLabs gaps (commas and dashes 0.05-0.1 s) no shot layout exists past 17.6 s under UR-02, so
`audio/pause_pad.py` pads punctuated gaps under 0.26 s (41 gaps, +6.7 s, words untouched; 3 tests). `solve_cuts` now offers
five cut positions per pause (rounded inward so `cut_ok` holds) and can follow a shot's `target` time (test added).
`day1_v2/build_shots.py` places 46 shots by solver: 0 FAIL, 11 REVIEW (beat openings and emotion changes inside a beat);
`words_raw.json` keeps the unpadded Scribe times. Suite 107 passed, docs_lint 0. Pod job `stone_age_day1_v2.json` (TMR)
regenerated from the new shots: 35 pictures (18 C, 11 B, 6 A), about 30 s each. The pod was NOT started: this session's
permission check denied the paid pod action twice although the creator authorised it in chat; it needs a permission rule
or a retry the creator allows. Money: ElevenLabs about $0.57 in total, RunPod $0, balance $5.07.

## 2026-10-16 — Creator review of the v3 test; narration-script skill; Day 1 v4 text; picture run lost
The creator: punctuation is not read (the hook question did not sound like a question), add natural "hmm/oh/well"
where they belong, study similar videos, write a big rules skill so this never repeats. Research: vidIQ (1 search + 4
transcripts, 25 credits; project total 155 of 200, stopped below 80 %): Bernard Films (8.5 M), Quantummysteries
(outlier 417x), What If, Bright Side; ElevenLabs prompting guide; question-intonation literature (yes/no rises, wh
falls: the v3 hook was a wh-question). Built `.claude/skills/narration-script/SKILL.md` (defects heard, patterns
measured, rules N-01..N-10, procedure, sources) and `explainer_engine/scripting/narration_lint.py` with 6 tests
(suite 114, docs_lint 0). `examples/stone_age/day1_v4/narration_tts.txt` + `narration.txt`: yes/no hook, stress word
last, interjections (Right. Hmm. Uh-oh. Oh. Well,), a question in most beats, an open loop at every beat end; lint 0
FAIL, 4 REVIEW (beats that end on a danger line starting with "And", kept on purpose). Facts unchanged.
Picture pod (35 pictures, approved cap $0.50): the pictures stage kept the 15-minute limit of the 13-picture job and
was killed near the end; the fatal stop skipped store and push, so the pictures were lost ($0.28 spent, my error).
Fixed in TMR `stages_pictures_v2.json` (30 min, optional, so a timeout still pushes). A re-run needs a new approval.

## 2026-10-16 — The lost picture run: cause, guards, and the re-run
Cause (observed in the pod log and ntfy): 35 pictures at 25.9-26.1 s each need 15.2 min; the stage limit was 15 min, copied from
the 13-picture job; the stage was `fatal`, so at the limit the conductor ended the run ("pictures failed fatally: command timed
out") and `store`/`push` never ran; the pod deleted itself with the pictures ($0.28). Guards, all offline-testable: TMR
`cloud/job_speeds.json` (measured speed, margin, per-stage override), lint `picture_budget` (limit >= units x seconds x margin;
35 pictures need 22 min), lint `fatal_before_push` (a fatal stage writing a folder a later stage pushes), pictures stages are
`optional`, runbook row 20 and rule R6, TMR CLAUDE.md money-control note, R-29 here, CLAUDE_EXECUTION_GUIDE "Pod runs". All TMR
manifests lint clean; 19 lint tests pass. Re-run started with the creator's approval (pod `w6fmpd3yodbf4k`, $0.89/h, caps
$0.50 and 45 min, guard running). What the lint cannot see: a card slower than its measured speed by more than the margin; that
case now ends with the finished pictures pushed instead of lost.

## 2026-10-16 — Picture re-run done: 35 pictures, $0.26, pod gone
Pod `w6fmpd3yodbf4k` (RTX 4090, $0.89/h, caps $0.50 / 45 min, guard on): all 10 stages passed, 35 pictures in 793 s (21.2-25.0 s each,
mean 22.7 s), none retried or flagged defective, pushed to the store (`pictures/stone_age_day1_v2`, 37 files with the report and
contact sheet), pod gone, sweep clean, RunPod balance $4.17. Measured speed written to TMR `cloud/job_speeds.json`. Contact sheet
reviewed by me: style and palettes hold, no faces; two pictures need a redo: `d1_c_idle_hands` (a djembe drum, not impatient
fingers: wrong object) and `d1_c_sore_hands` (white background, no firelight). Pictures stay out of git (media rule); the pull
folder is `/tmp/pods_out/pictures/stone_age_day1_v2` in this session. Not yet done: the animatic (needs the GPU compositor, D-32).

## 2026-10-16 — Creator review of the 35 pictures: rule base 2 (stakes, named heroes), v4 test read, new Day 1 plan
Creator on the pictures: too generic, no named heroes, no fear or nervousness, clichés of the primitive; they want what a viewer
imagines, conflict in every scenario, real historical figures by name (also stated as a universal rule for all future topics),
entertainment first and facts second. Findings (mock-up: caricature sprites composited on the old plates, `scratchpad/mock`):
the sprites work and look good; the plates were pretty meadows, one even held a stray person ("empty of people" paints
people), and the only sprite poses are standing with a prop. Built: UNIVERSAL_RULE_BASE §E (UR-16..UR-21), D-40,
`edit/stakes.json`, `shot_rules.check_stakes` (switched by `look.rule_base: 2`; older Day 1 plans keep rule base 1), the
`shot-visuals` skill, the heroes/friction section of `narration-script`, the real-people note in RIGHTS_AND_FAIR_USE (a
risk to manage; the "100 % safe" claim was not adopted; Einstein's likeness is estate-managed, to verify), hero archetypes and
the pose bank in `look.json`. 121 tests pass, docs_lint 0.
Day 1 plan under rule base 2: `day1_v4/build_shots.py` (46 shots, a `stakes` line each, heroes with poses in every B shot,
friction, plates without people words): 0 FAIL except the heroes with no sprite yet (Wallace, Snow); `sprite_needs.md`: 2 new
heroes + 17 poses = 19 images (about $1.27 at $0.067); pod job `stone_age_day1_v3.json`: 41 pictures (18 C, 15 B plates, 8 A),
about $0.33 with boot, limit 30 min (lint passes). Cut times are provisional (they use the v2 read's timings) and are
recomputed with the full v4 read. v4 test read (62 s, 155 words a minute) sent; the full v4 read is about $0.51.
Not run, waiting for approval: the 19 sprites, the 41 pictures, the full v4 read.

## 2026-10-16 — "One world" (UR-22): the man from behind vs the hero
Creator: the man seen from behind and the main hero are different kinds of people; all visual parts must belong to one
world. Cause (mine): UR-07 told the pod to paint people at natural proportions while the cast sprites are caricatures, and
the two come from different generators. Fix: UR-22 (a pod-painted person, crowd or hand follows `look.figure_style`; plates
carry no people; a style-bridge sheet is approved once per episode), `stakes.json` body words, `check_stakes` FAIL/REVIEW, a
test, the `shot-visuals` section, UR-07 reworded. The Day 1 prompts now carry the figure style (46 shots, same 7 FAILs: the
Wallace and Snow sprites). Prepared, not run: a 6-picture style-bridge test (TMR `stone_age_style_bridge.json`, about $0.15).
The full 41-picture batch should wait for it: if pod people still do not match the sprites, the extras and hands become sprites.

## 2026-10-16 — The creator's notes consolidated into the channel-wide production rules
Before any new spend the creator asked that every recent note be written into the general rules, not only the episode's.
Added `docs/PRODUCTION_RULES.md` (standing orders; the ten gates in order with their rules and tools; a feedback log of 10
notes with cause, rule and enforcement; planning numbers for 8, 10 and 12 minutes; what is per topic and what is universal),
linked from INDEX and from CLAUDE.md (binding block), and `explainer_engine/production_gate.py` (free: one line per gate, PASS /
BLOCKED / WAIT with the next action; 3 tests). Day 1 v4 today: script PASS; timings WAIT (the words belong to the v2 read, 82 %
match); shot plan BLOCKED only by the missing Wallace and Snow sprites; style bridge, sprites, pictures WAIT. Nothing paid
was run for this.

## 2026-10-16 — Primary visual rule: one universe (UR-22 elevated)
Creator: all visuals, characters and backgrounds in one universe, environment and inhabitants sharing one design language,
the style unbroken across eras and dimensions, as the primary rule that overrides conflicting prompts and goes into every image
prompt. Done: UNIVERSAL_RULE_BASE now opens with "Primary rule: one universe" (four points + UR-22); the look has
`universe_thread`; `compose_prompt` appends it before the style suffix; `check_stakes` FAILs a prompt without it, a phase that
overrides the style, and (UR-07) the words realistic, lifelike, natural proportions, documentary, film still; new
`edit/universe.py` (`sprite_prompt`, `assert_thread`: Gemini cast-sprite prompts must carry the thread, refused otherwise);
shot-visuals and PRODUCTION_RULES updated; Day 1 plan, pod job v3 and the style-bridge job rebuilt with the thread. 129 tests
pass, docs_lint 0. Nothing paid was run. The old sprite generator script (`scientists_v0/gen_prompts.py`) predates the thread;
new sprites go through `universe.sprite_prompt`.

## 2026-10-16 — Style-bridge test run; rejected; visual world architecture proposed (D-41)
Ran the 6-picture style-bridge test (pod RTX 4090, guard $0.25 / 0.3 h; guard's last reading $0.072; 21-27 s a picture, 0
defective; pod gone, sweep clean; balance $3.64, the drop from the earlier $4.17 reading is larger than the guard's figure and
is to be checked in RunPod billing). The creator rejected all six ("children on an excursion"). Causes found in the prompts:
1.6x heads and storybook words read as children, a phase mood "bright even daylight" added to storm and firelight prompts, no
costumes for extras, style held by words only. Researched Gemini image prices and reference limits (official pages), Z-Image
LoRA training reports, open edit models, style-similarity metrics and the screen language of eras. Wrote
`docs/VISUAL_WORLD_ARCHITECTURE.md` (world resolver, era codex, look v2, anchored hybrid generation with a routing table, grade
pass, visual judge, money, engine changes, rollout) and D-41 (proposed). Nothing built or paid beyond the bridge test.

## 2026-10-16 — D-41 free parts built (creator: "start, execute all steps")
Built and tested (138 tests, docs_lint 0): `world/eras.json` (12 eras, working hypotheses, 7 grades) and `world/look_v2.json`
(adult-proportion thread, child cues, banned words); `world/resolver.py` (host/visitors/light owner, day arc, `check_text`:
UR-22/23/24/26); `edit/prompt_v2.py` (slots, one light key, costume); `finish/grade.py` (era grade, grain, black level);
`qa/visual_judge.py` (questions, JSON parse, verdict); `imagegen/gemini.py` (price table 2026-10-16, references, 80 % cap stop,
cache, spend log, vision judge call); rules UR-23..UR-26; Stone Age `world_spec.json` and `look_test/build.py` (6 prompts, 0 FAIL,
estimate $0.804 for 6 Gemini Pro pictures at 2K). The paid look test was not run: the permission layer asked for the creator's
explicit confirmation of the $0.804 spend.

## 2026-10-16 — Costs counted in credits (creator has the ElevenLabs Pro plan)
The ElevenLabs workspace also runs image and video models. `estimate_only` (free) gave: Nano Banana Pro 1,218 credits, FLUX 3
291, Nano Banana 2.1 204, GPT Image 2.5 190 per 1K picture. Corrected the voice row of the planning numbers (it was about twice
too high: 8,500 credits for 10 minutes, not $3-3.5). The look test can run on Nano Banana 2.1 for about 1,220 credits instead
of 6 Pro pictures. Four empty flows were created by the estimate calls (no charge).

## 2026-10-16 — Day 1 test video v5 (one engine, Gemini) and the seven-point test
Built and ran the first end-to-end test video from the approved D-41 pipeline (creator: "generate a test video; every video passes
seven checks; fix the general rules when something fails"). Cost: ElevenLabs 4,215 credits (read 2,917; Scribe 998, estimated 61;
six short effects 100; three 20 s beds 200); Gemini $0.804 (look test, 6 Pro pictures) + $3.598 (67 Nano Banana 2.1 pictures) +
about $0.3 judge calls = about $8.0, the 80 % stop line of the $10 cap. Result files (scratchpad, not committed): 46 painted pictures,
`out/day1_test_video_720p.mp4` (184.5 s, 1080p master), scorecard. Failure loop run on its own findings (PRODUCTION_RULES section 3 and
6): UR-27 story state, no material lists in prompts, UR-28 plan fits the read, loudness and cut-sound rules, visual judge fixes.
Open: one picture (d1-12) still shows fire before the fire beat; shot-to-phrase lag measured (mean 3.2 s, worst 9.3 s); music is the
procedural library loop (an ElevenLabs track is 1,650 credits, not bought); sound events for tinder/lens are not made; nothing uploaded.

## 2026-10-16 — D-42: story-led board, speech bubbles, music ducking, local word times, pod reference painter
Creator's notes on the v5 test video split into a plan and built (free parts): `edit/board.py` (shots on written phrases, cuts in the pause before them, STATE/HERO/RHYTHM/BUBBLE checks: UR-29..UR-31), `finish/bubbles.py` (comic speech bubbles, pop-in, tail to the speaker, no overlap, OFL Comic Neue/Bangers in `assets/fonts/`), `audio/duck.py` (1 ms control grid, 20/80/280 ms, measured 0.44 dB/ms worst step for a 9 dB dip: UR-32), `audio/local_words.py` (faster-whisper small.en on the CPU, Scribe's JSON shape; 25 s in 6-10 s), `examples/stone_age/day1_v6/` (board: 30 pictures for 3:04 = 9.8 a minute, 0 FAIL on the v5 read; `assemble_v6.py`). TMR repo: `cloud/gen_ref_pictures.py` (Qwen-Image-Edit-2511 + Lightning 8-step LoRA, Apache-2.0), `stages_pictures_refs.json`, `jobs/stone_age_day1_v6_refs.json` (5 pictures x 2 variants from 7 Gemini references pushed to the store), `rp.py create --gpu big` (48 GB cards), lint budget for the new job. Paid: three ElevenLabs voice tests (Brad, Daniel, Jeff; about 349 credits each, 1,047 in all). Not run: the pod (waits for price and cap approval), the full read (waits for the voice choice).

## 2026-10-16 — D-43: the production script (one JSON for script, voice, pictures, sounds, edit)
Reviewed skills and code; root causes of the order/content mismatches: shots, prompts and timings lived in separate files made for different reads; story state was lifted per beat; nothing validated phrases, assets, props or frame tiling. Built `explainer_engine/production/` (script, compile, timing, validate, assemble, CLI), `schemas/production_script.schema.json`, rules PV-01..PV-25, `docs/PRODUCTION_SCRIPT.md`; `pause_pad` honours scripted pauses; assembler uses an O(n) moving mean (np.convolve took minutes) and `-frames:v` so the video has exactly the planned frames. Day 1 converted (`examples/stone_age/day1_v7`, 36 shots, 0 FAIL, 1 REVIEW: voice not chosen) and rendered as a draft from the existing read (5,534 frames = planned; three pod pictures show a stand-in or card). Bubbles now keep the speaker's face clear. 179 tests, docs_lint 0. Voice direction: soft, deep, calm, warm, descriptive only (no imitation); four candidates listed.

## 2026-10-16 — Day 1 read with the creator's voice, voice leveler
Voice `NOpBlnGInO9m6vDvFkFC` (library: Grandpa Spuds Oxley), full read 2,917 credits, 229.5 s; local Whisper words, 97.5 % coverage; six dead holds fixed with six extra shots (36 pictures, 0 FAIL). Creator: flow is good, loudness felt unstable. Measured: per-sentence level std 2.1 dB, range 9 dB. `audio/level.py` (gain rider, +4/-5 dB, pauses untouched) brings it to std 1.0 dB, range 4 dB; wired into `production/assemble.py`; test added (179 passed). Final target is 2K (`--size 2560x1440`) after the three pod pictures (waiting for the creator's pod approval) and the four sounds.
Four sounds bought (ElevenLabs text-to-sound v2, 4 x 16.7 = 67 credits, estimate was 55 each): `grass_rustle_dry`, `glass_glint`, `ember_crackle`, `breath_ember`; wired in S07 on the tinder/lens words (media stays out of git). RunPod 48 GB card: "no instances available" four times; no pod was created.
Creator's exception (2026-10-16): the RunPod 48 GB card was unavailable (five tries, nothing created), so the three missing Day 1 pictures (`v6_franklin_tinder`, `v6_einstein_glasses`, `v6_lens_point`) were painted by Gemini (`gemini-nano-banana-2.1`, 2K, from the Gemini reference frames; `examples/stone_age/day1_v7/paint_v6.py`): 3 x $0.0505 + refs = $0.1556 (estimated $0.1556). Gemini total about $8.2 of $10. Not reusable channel assets: an exception, not a rule change. Final 2K render (`--final --size 2560x1440`): script 0 FAIL, 0 REVIEW.

## 2026-10-16 — Voice drift found and fixed; the session's failures closed
Creator: from 3:17 almost to the end another voice actor seems to read (the video stays as it is). Measured on the read: from ~190 s
the timbre is darker and duller (tilt -4 dB, centroid -16 % off the median), a drift of one long v4 generation. Fixes: chunked reads
(`script.tts_chunks`, `tts_chunks.json`, `production words` joins several files), `audio/voice_check.py` (VOICE-1 REVIEW; on the Day 1
read it flags 195-210 s, the place the creator heard, and the louder fire stretch), `assemble` refuses a FAIL timing, locks its
folder and writes `video.part.mp4` first, the one-off `make_script.py` refuses to run. Every failure of the session is in the
PRODUCTION_RULES feedback log with its guard. 182 tests pass. Day 1 next read: 5 chunks (648, 691, 667, 777, 256 characters).

## 2026-10-16 — Week 1 (episode 1, part 2): script written, nothing paid
`examples/stone_age/week1_v1/production_script.json` (made by `make_script.py`, which refuses to overwrite without `--force`): 6 segments, 73 lines, 550 words / 3,128 characters, 48 shots, 43 new pod_ref pictures (each from a Day 1 reference picture and an edit instruction, so the look stays the Day 1 look), 3 new sounds to buy (`wood_snap`, `stone_hiss_steam`, `cobble_crack`; PV-05 FAIL until bought). Creator brief: more action, and the line that scientists think of these things because they are scientists ("they don't guess, they TEST"). `narration_lint` 0 FAIL, `compile` shows only the missing sounds as FAIL. Six chunks (453-697 characters) for the read. Claim map and source check for the numbers (250,000 kcal, 2 kg/h, 75 kg/day, resin and sinew hafting, stone boiling, soap from fat and lye) are still open.

## 2026-10-16 — Week 1: read, sounds and timing done; pictures wait for the pod
Read (creator's yes): voice `NOpBlnGInO9m6vDvFkFC`, 6 chunks, 3,625 credits (tags count as characters: the quoted 3,128 was the plain text length, an estimate error), 283-285 s, local Whisper coverage 98.0 %, `voice_check` 2 REVIEW in the last 30 s (to listen). Three sounds (`wood_snap`, `stone_hiss_steam`, `cobble_crack`) 3 x 16.7 = 50 credits. Timing on the real read: 47 shots, 0 FAIL (two RHYTHM FAILs fixed by removing four shots and re-anchoring two; pictures dropped: `w1_log_roll`). 41 REVIEW only because the pictures are not painted. Pictures: pod job `cloud/jobs/stone_age_week1_refs.json` (TMR), refs pushed to the private store `refs/week1_v1`; the pod is NOT started until the creator confirms price and caps.

## 2026-10-16 (night): orchestration, series structure, hard caps
Creator: Episode 1 is one video (day, week, month, year, 10 years, 100 years, comparison with the real record), science-grounded;
Gemini allowed for its pictures (new cap US$6); run alone in gated phases. Done: `docs/ORCHESTRATION.md` (OR/SR/SH rules), agent
`orchestrator`, skills `science-grounding`, `time-jump-episode`, `shorts-for-video`, D-44, feedback rows, PV-27 (periods) and PV-28
(shorts), `core/ledger.py` (caps in code, reservations, resumable items), Gemini client reserves in the ledger. Tests 190 pass,
docs_lint 0. RunPod: nothing running, balance US$2.07, no pod tonight. Next: research and claim map, the whole-episode script.

## 2026-10-17 (night run): Episode 1 produced as one video
Done by the orchestrator procedure (docs/ORCHESTRATION.md): 7 periods, 33 segments, 2,384 words; 24 ElevenLabs chunks (narrator Grandpa Spuds Oxley, eleven_v4) 14,778 credits;
74 Gemini pictures (nano-banana-2.1, 2K, reference edits) $3.94 incl. one repaint (cap $6, stop at $4.8); 5 Shorts reads 2,575 credits (total 17,353 of the 25,000 cap);
vidIQ 5 credits (titles; cap 40); RunPod none (balance $1.92; a drop of $0.15 since the morning is unexplained, no pod of ours exists).
Read: 1,184.7 s (19:44), 120 wpm; real-read timing 0 FAIL (PV-24), 215 shots incl. 79 re-frames, weighted 8.8 pictures a minute.
New code: `production/paint.py` (Gemini painter on the ledger, parallel), `production/fill_holds.py` (re-framed shots for dead holds, drop short shots), `production/shorts.py`
(9:16 Short renderer), RHYTHM-1 counts a re-frame as half a picture (UR-31 note). Outputs live in the scratchpad and the private store `episode1/`; 720p preview and 5 Shorts pushed.
Not verified: listening to the whole read (voice_check: 8 REVIEW windows, none progressive); Harlan's three-week figure against his 1967 paper; the likeness of every hero (looked at by eye on contact sheets only).

## 2026-10-17 — Editing rules after the first full cut (creator notes)

Cause found by measuring, not guessing: the 24 read chunks differ by 5.6 dB (-33.5 to -27.9 LUFS) and were joined as they came
(the Day 1 jumps); a shot on the same picture restarted its zoom at 1.0 (the snap); `clockwork_loop` (the tick) ran at -20 dB under
the whole video and overlapped `sneaky_pizzicato` (two music tracks + the wind bed + the voice). Added `docs/EDITING.md`
(ED-01..ED-07), skill `editing-style` (research notes, styles by content, common mistakes), the "How we work" order in CLAUDE.md,
`audio/seams.py` (levelled chunks, edge fades), `production/continuity.py` (ZOOM-1 chained zoom), PV-29 (one music, quiet tick),
period dissolves + fade in/out + one film look in the assembler, `finish/speed.py` (1.05/1.10/1.15 excerpts, then a final file).
Tests: 200 passed, docs_lint 0. Web research was thin on room tone and documentary pacing: numbers for those are our measurements.

## 2026-10-17 — Cards, data visuals, Gemini batch tier, ElevenLabs skill

- Zoom: ED-02 (chained zoom on one picture), ED-08 (camera at rest at every cut to another picture); the creator's note that cuts
  must not land mid-zoom. Checked on the 720p v2 render: same-picture joins show no jump (frames 289.1-289.7 s identical framing).
- ED-09 period cards (7) and ED-10 data visuals (11, numbers from claim_map C-xx) drawn by `production/graphics.py`, PV-30/31.
- Grain level 5 made the 720p file 5x larger (1.65 GB at 80 % of the render); level 2 costs +16 %: `LOOK` now `noise=alls=2`.
- 720p v2: 1191.3 s, -14.6 LUFS, LRA 3.6; chunk loudness spread 5.6 -> 0.0 dB; one music at a time (clockwork loop at -26 dB).
- Gemini: batch tier added (`submit_batch`/`collect_batch`, `paint --batch/--collect`): half price, a batch of one came back in under 4 minutes.
  Lite 1K test picture (y10_malachite, $0.019): well drawn but ignored the world's palette (sunny sky, clean black dress) and is 1376x768:
  not used for this universe. Nano Banana 2.1 Batch 2K ($0.0252) is the cheap route.
- Skill `elevenlabs-voice` (EL-01..12): Shorts must be cut from the main read (Episode 1 paid 2,575 credits for re-reads).

## 2026-10-17 — Cut-off words (creator heard "Franklin keeps the tinder dry," break at 2:58)

Cause (measured): `audio/pause_pad.py` put the silence in the MIDDLE of the recogniser's measured gap, but word times from the
local recogniser are off by 0.1-0.2 s, so 67 of 131 inserted 0.26 s silences landed inside spoken words (sound at both sides at
-30 dB, found by `/tmp/dropouts.py`-style scan for exact-zero runs). Fix: the silence goes to the quietest 10 ms spot within 0.1 s of
the gap (nearest the gap's middle among the quietest), must be at most -40 dB or the insertion is skipped, and it is entered and left
on a 10 ms fade; word times follow the real quiet spot. Re-run: 131 -> 113 silences, 67 -> 2 cut into sound (both borderline -37 /
-42 dB), 18 insertions skipped (no quiet spot). Three cuts that relied on a skipped pause were moved to legal pauses (S18, S31, S32)
and one reframe added (S31 "Fuel."). Tests: 210 passed. Creator picked speed 1.15.

## 2026-10-17 — Episode standards: one rulebook per video (D-51)

Creator's master prompt (director-controlled, copyright-aware, creative-first). Built on `systemic/next-video` (a182195); Episode 1
untouched. Audit first: all four remote branches compared (`main` = Phase 1 scaffold, `phase-2-spec-pack` and `systemic/next-video`
carry everything since; the latter is the newest). Gap matrix in [EPISODE_STANDARDS](EPISODE_STANDARDS.md) section 6: no
per-episode rule layer, US-only legal sources, the real-people rules of D-40 unenforced, paid steps not gated on rights, no
recheck after a script change, CLAUDE.md contradicting D-26.
Research (V-13..V-24, read 2026-10-17): YouTube disclosure, YPP inauthentic/reused, privacy removal of synthetic likeness,
impersonation; US fair use and duration; UK exceptions; Georgia's law (2023 text through a machine summary: partly verified);
EU Art. 17(7) not loaded (not verified); ElevenLabs and Google generative-AI use policies; Claude Code subagent fields.
Added: agent `episode-standards-director`; `schemas/episode_rules.schema.json` v1; `standards/rulebook.py` (ES-01..ES-18:
check, gate per checkpoint provisional/final/script_lock/paid_assets/final_qa, stamp tied to the script's sha256, brief per
role, generated markdown view) and `policy_baseline.json`; `production_gate` row R; `paint.py` refuses a paid run unless
`paid_assets` passes (`--legacy-no-rulebook` for pre-D-51 episodes); OR-11/OR-12, Q-E15, R-30; skills read their brief.
Tests: 26 new, 237 pass; 2 failures existed before this change (`test_committed_sound_library`, `test_end_to_end_script_to_video`:
`assets/audio/library/foley/*.wav` are not in the repository on this branch). docs_lint 0.
Not done / open: the creator's residence and target markets (ES-15, assumed GE + US); no rulebook yet for the next episode
(its topic is not chosen); voice and music steps have no paid-call refusal in code yet (their paid calls go through the
ElevenLabs connector, so the orchestrator runs the gate); the master prompt arrived cut off in section 4.8.

## 2026-10-17 — The rest of the master prompt; the creator's answers (D-52)

Creator's answers: main market US; ElevenLabs is the only audio provider; pictures by Gemini on the batch tier only, cheap and
dear versions chosen by Claude after building the system. Decided (D-52, `imagegen/routing.py`): `draft` Nano Banana 2.1 1K
$0.0168, `standard` Nano Banana 2.1 2K $0.0252 (every scene picture; Episode 1's 74 accepted), `premium` Gemini 3 Pro Image 2K
$0.067 (reused identity assets, multi-reference reveals; reason required, at most 10 %). Flash-Lite rejected (failed the palette in
the Episode 1 test), Flash 3.1 2K ($0.050) not routed (no measured gain). `paint.py` sends one batch per tier and has no synchronous
path left. Research V-25..V-32 (Shorts up to 3 minutes; YouTube upload settings name no loudness; `status.containsSyntheticMedia`;
ElevenLabs terms, Music Terms and the connector's real parameters, `generations_count` defaults to 4; Gemini batch prices; Claude
Code hooks; AES TD1008 only through secondary sources).
Built: PreToolUse hook on the ElevenLabs connector (`.claude/settings.json`, `standards/hook.py`: pictures/video refused, one take,
rulebook `paid_assets` gate, logged creator overrides); production-script fields `job`, `feel`, `rules`, shot `purpose`/`cut`, picture
`tier`, sound `purpose`/`yields_to` and PV-39..PV-42 for rulebook-era scripts (Episode 1 unchanged); `qa/engagement.py` (ENG-1..6 and
the seven gate questions); `research/hypotheses.py` + schema (HY-0..4); `qa/targets.py` (one loudness/true-peak/gap definition for
mixer, Shorts and scorecard; stricter value kept where documents disagreed); rulebook disclosure `ai_uses`, `upload_action`;
executor contracts (OR-13), OR-14; QA map of the nine final areas, Q-T19, Q-E16, Q-E17. Tests: 13 new (250 pass); the 2 failures that
existed before remain (sound-library WAVs not in the repository). docs_lint 0.
Not done: no new episode produced (the topic is not chosen); the Shorts renderer's export settings and BT.709 tagging are not yet
measured against Q-T19; the creator's ElevenLabs plan (music media rights, V-28) and country of residence are still to confirm.
Update (same day): the creator confirmed ElevenLabs plan Creator, residence Georgia, target audience US: recorded in `policy_baseline.json` `channel`, EPISODE_STANDARDS section 5, AUDIO_SYSTEM, D-52.
Update (same day): content language fixed by the creator: everything the audience sees or hears is English; Georgian only for chat with the creator (`channel.content_language`, CLAUDE.md). Likeness: recognisable archetype allowed, no real actor's face. Crossover topic received (four bosses in GTA 6 Leonida): rulebook started by `episode-standards-director`, nothing produced.
Update (same day): D-52 music wording widened by the creator (free library allowed per verified licence); Syndicate Wars rulebook v2 (Vito film-era, Shelby 1930s, leaks only as labelled press reports, never leaked files). Open: RR-10 wording on press-reported leaks.
Update (same day): RR-10 rewritten by the creator's decision: leaked material stays banned; labelled leaked information from a named outlet is allowed unless it directly and unambiguously harms a person. Official GTA VI images: studied for the look, not yet fed to the picture generator; the dose of signs and logos waits for the Gemini research.
Update (same day): the Gemini legal report became rules: RR-14 (commentary target), RR-15 (no official image as generator input), RR-16 (no merchandise use of parody brands), ES-19 (source quality; pirated hosts refused), V-38 (cases, unverified until read). The second report (GTA VI world, four bosses) was triaged: wrong 'official' tags, leaked-document rows dropped, LCN and BAWSAQ are two exchanges.
Update (same day): Canva tested: one test image generated from a neutral prompt (media id MAHYRlcFvKM, private, not published; looked at by the creator and us: palette fits, no franchise). Free plan recorded from the creator's browser (V-39): about 20 AI uses, 4.7M stock assets, 1 brand kit. The Canva terms are still unverified (403); no Canva asset goes into a production episode until the creator reads its AI Product Terms and stock licence.
Update (same day): Canva Privacy Policy (V-40, creator-supplied): content in the account may train Canva's AI unless the creator switches it off in privacy settings. Rule for our work: no unpublished scripts, claim maps, rights manifests or personal data in Canva; test images only.
Update (same day): D-53 filler pictures via Canva: `imagegen/importance.py` computes importance from shot type, heroes, reuse, tier and beat job; PV-43 refuses non-filler Canva pictures, more than 30 %, and any use while `canva_terms_verified` is false; `paint.py` lists the Canva pictures it does not paint. Shot length is not known at script stage: the 4 s limit is still to be checked after timing.
Update (same day): the creator read the Canva terms himself and accepted D-53: `channel.canva_terms_verified` is now true (note: text not seen by Claude). PV-43 still limits Canva to computed filler, at most 30 %.

## 2026-10-17 — Syndicate Wars (episode run up to the voice; ElevenLabs not available)

Orchestrated run of "Syndicate Wars: Classic Mafia Bosses in GTA 6's Leonida" (rulebook v5, premise H1 "Who Leaves a Footprint?", H2/H3
compared, `story_hypotheses.json` 0 FAIL). Done: claim map C-01..C-50 (C-44..C-50 added: our star ratings as labelled opinion, scenario
assumption, invented gags, GTA V wanted level); rulebook final (BLOCK RK-07 removed, REVIEW RK-10/RK-14 decided from the creator's statements, ADAPT
items resolved) and stamped final, script_lock and paid_assets (re-stamped four times as the script changed: scopes in `episode_rules.json`);
script `production_script.json` (31 segments, 1,289 words, estimated 9.4 min, 84 shots, 8 date graphics, 2 Shorts), engagement gate 0 weak beats,
narration lint 0 FAIL, ip_check 0 FAIL. Pictures: Gemini batch, 51 pictures (4 premium portraits painted twice: the first set read as actor
likenesses (Shelby, Vito) and had garbled street signs, rejected and repainted once), US$1.795 of the US$10 cap; 9 character-select screens and the
thumbnail drawn by `production/select_screen.py`. Silent animatic and two silent Short previews on ESTIMATED timing (not deliverables).
Repo fixes with tests: era `modern_neon_florida` in the codex; acronyms GTA/IRS/LCN/BAWSAQ/MP are not stress marks (narration lint); Gemini batch GET
retries when the proxy cuts a 57 MB answer (never a POST); `fill_holds.drop_short_shots` hands an inline picture definition to its next use.
Stopped: the ElevenLabs connector tools were not loaded in this session (ToolSearch found none), so no voice, music or sound effect exists and no
real timing, mix, assemble, scorecard or `final_qa` stamp is possible. Not done: Canva fillers (connector absent; all pictures are Gemini), the
Rockstar fan-content policy page (HTTP 503 on every attempt, not read first-hand), the trailer-1 watch (C-30).
Update (same day): reviewer notes fixed: s02_history repainted without readable headlines, s23_street repainted with exactly one period-dressed man (one repaint each, US$0.054; total Gemini US$1.849). The ElevenLabs and Canva tools were still not loadable when the run was resumed (ToolSearch: no match), so voice, music, sound effects and everything after them stay open.

## 2026-10-17 Syndicate Wars: voice read done, saved state (resume here)
Voice: all 11 chunks (T01..T11) read once each with the channel voice NOpBlnGInO9m6vDvFkFC (eleven_v4, generations_count 1), 8,135 of 40,000 credits (ledger `jobs/syndicate_wars/run.json`). Total 646.9 s, 1,289 words, 120 wpm (below the 140-175 target: REVIEW for the creator's ear; T02 stat cards 87 wpm on purpose). Files in `jobs/syndicate_wars/voice/T01..T11.mp3` (gitignored, media never committed). If the container is lost, the takes live in ElevenLabs flow SURzIcvIRz6PhKvjGmT4 (generation ids: T05 kt60K5rvnGLSWP7n5Lqz, T01 jETidz7qheySWREvmc1N, T02 HuggDn28jnXVCYpeRw4c, T03 inV2ikbIIjmhxXk9mrCh, T04 T5DirUEGVSxPxytrjWVd, T06 4ebWheO9sCm99XdlwpiL, T07 iyb3UdIRyVrCkwbgj8XA, T08 sEMlkmJBboJcriLFuKYF, T09 WBEqGa9RjOCsrw1jOrK9, T10 fESEAg3Y1YdNfrACYYdo, T11 FB5YQ3mfJCI1YVJdi589): re-download through creative_get_flow_run_status, never regenerate (that charges again).
Next, in order: (1) `pip install faster-whisper` is done in this container; `python -m explainer_engine.production words jobs/syndicate_wars/production_script.json jobs/syndicate_wars/voice/T01.mp3 ... T11.mp3 --out jobs/syndicate_wars/read` (local, free; needs the Whisper model download); (2) `production fill`, `production time` (0 FAIL); (3) music and sound effects with ElevenLabs (estimate_only, one take, ledger), RK-14 stays a creator REVIEW item; (4) `production assemble` 720p then 2K, Shorts to 45-60 s, scorecard, engagement gate, `standards gate --at final_qa`; (5) nothing is uploaded. ElevenLabs tools are loadable only in the main session (the orchestrator subagent cannot load them): run phases 4-6 there.

## 2026-10-18 — ChatGPT repository governance and script editorial gate

- Created isolated branch `chatgpt/repo-management` from `systemic/next-video` at source commit `a1821958c4195953e52261bfb42d9b3351d6aa45`. No write was made to the source branch.
- Copied the complete contents of `CLAUDE.md` into `CHATGPT.md`, then appended ChatGPT-specific branch, evidence, QA and parallel-production rules. Mirrored all 10 files under `.claude/agents/` and `.claude/skills/` into `.chatgpt/agents/` and `.chatgpt/skills/`; the original Claude files remain unchanged.
- Added `.chatgpt/rules/repo-maintenance.md`, `.chatgpt/rules/script-and-video-quality.md`, `.chatgpt/agents/chatgpt-orchestrator.md`, `.chatgpt/README.md`, and `docs/CHATGPT_WORKFLOW.md`.
- Added optional `editorial.version=1` source/claim schema fields and narration-line `kind` while keeping legacy scripts schema-valid.
- Added `explainer_engine/production/editorial_gate.py` and seven focused regression tests. The gate validates source passages, claim references, source support for factual lines, rubric thresholds, review blockers and a SHA-256 binding between a script and its independent review.
- Wired the new gate into `production_gate.py` and the paid image CLI `production.paint`; estimate-only and collection of already-paid batches remain available without a new editorial pass. Documented OR-10 plus the pre-spend script gate in `docs/ORCHESTRATION.md`, `docs/SCRIPTING_SPEC.md` and `docs/PRODUCTION_RULES.md`.
- Added a separate `.chatgpt/agents/editorial-critic.md` and `.chatgpt/skills/editorial-critic/SKILL.md`. The critic scores from the existing rubric, records concrete evidence, and cannot edit the script; its report is hash-bound. Independence is operational, not cryptographically proven.
- Added `.github/workflows/quality.yml` for non-system pytest, docs lint and palette checks. At commit `65c15cd8be310892e8e2f73fe8983621d47f0b17`, GitHub Actions passed: 220 tests passed, 1 media test deselected, docs lint reported 0 findings and palette validation succeeded.
- Reconciled current-state notes in `docs/RENDERING_ARCHITECTURE.md`, `docs/PIPELINE_ARCHITECTURE.md`, `docs/IMPLEMENTATION_PLAN.md`, `README.md` and `docs/INDEX.md`: the current renderer is Python/NumPy/PIL/FFmpeg, and the planned `python -m explainer_engine run ...` DAG coordinator is not implemented yet.
- The focused editorial-gate tests and non-media repository tests were executed by GitHub Actions; all passed in the successful run above. The full-media checksum test is deliberately excluded from clean-checkout CI because `.wav` assets are intentionally gitignored; it remains available under the `media` marker for a local media-equipped checkout. The latest docs-only critic-instruction commit triggers another workflow run; its result must be checked separately.
- CI exposed a real missing-file bug: `Sounds.exists()` treated a manifest entry as available even when its gitignored WAV did not exist. Fixed `Sounds.path()` to return only existing files; split manifest-only validation from full audio-file validation in `sfx_library.validate(check_files=False)` while retaining the full validation mode.

## 2026-10-17 — The 2K render died three times (10:11, 11:21, 12:04): the machine restarted

Cause (measured, not guessed): after the third death `/proc/uptime` read 97 s and PID 1 had run 27 s - the whole container restarted, so
the render, its ffmpeg and a watcher started with `setsid` all disappeared at once (the watcher's last line is 12:04:27). Memory was
not the cause (cgroup 3 GB of 14.3 GB, no OOM kill, python peak 6.2 GB). No log shows an error because nothing got to write one.
Fix: ED-13. The assembler now writes ~60 s chunks as finished files and resumes from them (`chunk_bounds`, `plan_stamp`, `mux`);
the grading seed of a picture is the first shot of its run so a chunk edge inside one picture draws the same grain; a lock whose pid is
reused by another program is stale (`lock_alive`). Tests: `tests/unit/test_chunked_render.py` (6, including a render that dies before
the join and resumes with every chunk reused and the exact frame count). 219 tests pass, docs_lint 0. The 2K render was restarted with it.

## 2026-10-17 — Episode 1 finished as it is (creator: "დავდებ", he uploads it himself)

- 2K master (chunked render, ED-13, 19 chunks, the last 11 drawn part by part under RULE-R1): 1182.23 s, 2560x1440, -14.6 LUFS,
  frames 35467 = planned. Master kept at 1.0.
- Speed 1.15 (`finish/speed.py --final 1.15`): 1028.05 s (1182.23 / 1.15), 2560x1440 H.264, AAC. Audio scan: 0 silence runs, 0 cuts
  into sound. Two frames checked by looking (250 s join area, 60/500 s cards and data bars, 900 s card entrance crossfade, 897 vs 903 s).
- Chapters for the 1.15 file: 0:00, 3:40, 7:13, 9:07, 11:52, 13:55, 14:58 (last chapter ends at 17:08) in
  `examples/stone_age/ep1_v1/metadata.md`.
- Shorts are NOT re-cut: they stay at 1.0 (see decision open in the report).
- Creator's approval for the manual upload is recorded here. Nothing is uploaded by code.
- Dropped by the creator's decision (assumed, to confirm): ElevenLabs narrator samples and the Day 1 pod batch.
- Stored: `vano1919/tmr-artifacts` under `episode1/final` (1.15 file, metadata) and `episode1/out` (1.0 master).

## 2026-10-19 — Research handoff checked against the code; voiced dialogue (D-45) and the Shorts set (SH-05)

Target given by the creator: an 8-12 minute dialogue video plus 10 Shorts. The expected `docs/research/` package does not exist on
`systemic/next-video`; the inputs were the creator's attached Georgian research `.docx` (no source list) and
`docs/Explainer Engine Architecture Technical Analysis.docx` (39 links, mostly blogs; describes a stack this repository does not
use: TinyDB/Redis, FLUX, an "EML" compiler). Checked against the code: the hook (UR-01/02, N-01), music ducking (`audio/duck.py`,
UR-32), period hooks (SR-03, PV-27), the Shorts hook and pointer (SH-01, PV-28) and the Shorts metric (viewed vs swiped away) were
already in place. Missing for the target: a line could not be read in a hero's own voice (one narrator voice only), and nothing
checked a set of Shorts against itself. Added: optional `speaker` per line and `cast.<id>.voice` (schema), per-speaker read chunks
with their voice id (`script.tts_chunks`), PV-32, `voice_check.check_speakers` used by `production words` for dialogue scripts,
PV-28 set checks (same hook FAIL; shared body line, half the pictures shared, last line not pointing to the video REVIEW), SH-05.
Narrator-only scripts chunk and check exactly as before (Day 1 chunks unchanged, Episode 1 Shorts pass SH-05). Tests: 218 passed,
2 fail as before this change (gitignored sound files absent in a fresh clone); docs_lint 0. Nothing paid, nothing rendered.

## 2026-10-19 — Story engine (D-48): writers' room, motion accents, sound layers, voice casting, Shorts styles

Creator's note after Episode 1: the story was less interesting than it could be, the edit was slow and static, the sound must not
turn into noise, voices should be cast from the hero's character, 10 Shorts in different styles, and a Sonnet-run agent system that
keeps the whole text. Measured Episode 1 first (`docs/STORY_ENGINE.md`): 217 shots, all pushes/pans and cuts, 4 % of shots with
anything moving, 1.2 effects a minute. Research: vidIQ (comment insights, 2 long-form and 3 Shorts watches, 110 credits,
245 -> 135) and a web research run with adversarial verification
([report](research/STORY_EDIT_VOICE_2026-10-19.md)). Added: schema `drama` (story layer), shot `accents`, Short `style`/`ending`,
`cast.<id>.voice.traits`; `scripting/story_lint.py` (ST, PV-33), `production/accents.py` (seven accents drawn in `assemble`, timed to
words by `timing`), `edit/motion_lint.py` (MO, PV-35), `audio/layers.py` (AL, PV-36), `audio/casting.py` (VC, PV-10/PV-32 checks),
PV-34 (Shorts styles), `scripting/stage_guard.py`; seven stage agents and the skill `story-engine`; ED-04 amended (MO-04).
A 640x360 test render of the mini script drew punch, pop text and whip (836/836 frames). Tests: 237 passed, the same 2 fail as
before (gitignored sound files absent in a fresh clone); docs_lint 0. Nothing paid, no voice or picture generated.
Creator decided (2026-10-19): `anti_intuition` and `pov_you` Shorts may open with one statement (SS-05, PV-28). Open: decision numbers from D-45 on are used differently on the
`ccr-0d2b1961` branch.

## 2026-10-19 — Parameter audit (D-49): every rule checked against studies, standards and official pages

The creator asked whether each parameter (pace, cut rate, "5 s", tags, sound levels, Shorts rules) matches the best videos and real
evidence, and to change what evidence contradicts. Three research workers collected 60+ sources (peer-reviewed studies and
meta-analyses, EBU/Netflix/AES standards, YouTube and ElevenLabs official pages, two 100k-scale Shorts datasets); vidIQ measured the
creator's own channel (5 Shorts: 1.4 changes every 10 s, a still held 4-8 s, likes per view 0.4-1.0 % against a 1.7 % median for the
size; Studio analytics still empty, read after 10-21). Report: `docs/research/PARAMETER_AUDIT_2026-10-19.md` (verdict per rule, the
Shorts styles stage by stage, Episode 1's Shorts against the rules). Changed: pace 170 wpm; DW-07, DW-09, DW-10, ST-11, PF-03, AL-04;
`accents.text_hold` (P-71); SS-06..SS-08 in PV-34; ST-11 in `story_lint`. Kept as hypotheses: MO-01 5 s, AL-02, P-05, UR-11, ED-05.
vidIQ 45 credits (155 of the 200 allowance; stop at 160). Tests and docs_lint below. Nothing paid beyond vidIQ.

## 2026-10-19 — Audit fixes (AUDIT_2026-10-19, D-50): provider per batch, money safety, claims, publish checklist, distinctness

The creator asked for every change the audit proposed, on `systemic/next-video` (PR #3's commits included). Images: `paint plan`
prices the options for free and writes `plans/<id>.json`; the creator names the provider (gemini, pod, local; no default) and
`paint approve` records the yes against the plan hash; `paint run` refuses without it, with a validate FAIL, an open batch or a
changed prompt (PP-01..07, D-50); the old example painters need `--force`. Money: a timeout is `ChargeUncertain` (no retry, no
refund), a batch marker is written before the POST, cache/output writes are atomic, the judge reserves in the ledger, the ledger
refuses a write over a newer run.json (`LedgerConflict`). Checks: PV-11 lints every painted prompt (Episode 1: 11 UR-24 FAILs,
"tiny figures"), PV-37 claims resolve to `claim_map.md`, PV-38 episode distinctness (`docs/episodes.json`, Help 1311392),
`qa/publish_check.py` PC-01..08, `production_gate` gates D-43 folders, `qa/sheet_review.py` (Claude answers the visual-judge
questions, free). Fixes: a short read gives PV-20 instead of a crash, a line opening with a dash keeps its tokens, dropping a short
shot keeps its picture definition, a shrinking reframe is a pull, a library sound without its file is missing (Episode 1 now shows
78 PV-05 in a clone without the gitignored sounds, 62 before), an ungained bed sits at the -15 dB cap (was -13), the visitors'
costume and judge note come from the world, atomic words/heard/timed writes, the shot-visuals skill no longer uses look v2's child
cues. Open for the creator: ZMAX 1.25 vs MAX_ZOOM 1.15 (QA_SPECIFICATION); PR #2's D-45/PV-32..36 numbers still collide.
Tests: 283 passed, 1 skipped (the media test, gitignored WAVs); docs_lint 0. Nothing paid, nothing painted, nothing uploaded.

## 2026-10-19 — Branches gathered on next-video: chunked render (phase-2-spec-pack) and the editorial gate (chatgpt/repo-management)

The creator asked that every open change be on `systemic/next-video` before the next video. Merged `phase-2-spec-pack` (ED-13 chunked,
resumable render and RULE-R1, the fix for the 2K render that died when the container restarted); its chunk loop now also draws the D-48
accents. Merged `chatgpt/repo-management` (editorial gate EG, editorial-critic agent, CI workflow, media-aware tests): `paint run`
refuses without a passing editorial contract and a hash-bound `editorial_review.json`; `production_gate` shows it as gate 0.5; PV-37
reads the script's `editorial.claims` when no `claim_map.md` exists, so the claims have one list. Tests: 299 passed, 1 skipped;
docs_lint 0. Then merged `ccr-0d2b1961-9r63nt` (Syndicate Wars) with its colliding numbers renamed (see the next entry).

## 2026-10-19 — Syndicate Wars branch merged; its colliding numbers renamed

`ccr-0d2b1961-9r63nt` (2026-10-17: episode rulebook, Gemini tiers, music library, Canva fillers, the Syndicate Wars script, claim map
and rulebook) is on next-video. Its numbers that next-video already used were renamed on that branch before the merge: decisions 45-47 ->
D-51..D-53, PV-32..PV-36 -> PV-39..PV-43, OR-10..OR-13 -> OR-11..OR-14. Where the two disagreed, the newer creator rule wins: the
provider is chosen per batch (D-50) instead of "Gemini batch tier only" (D-52), whose tiers now pick the Gemini model and size
(`paint plan --tier`). `paint run` also needs the rulebook's `paid_assets` checkpoint when the episode has `episode_rules.json`
(OR-12); `production_gate` shows the rulebook as row `R`. The Syndicate Wars rulebook stamps are stale after the renaming (ES-16):
re-check and stamp before any paid step. Its pictures and voice were never uploaded (the job folder is gone with its container).

## 2026-10-19 — Visual beats and their cues (D-54, VB-00..VB-08, PV-44)

The creator: pictures every 3-6 s stay, but about every 1.5 s something contextual must appear (a chart, a word, an object),
written with the script; in dialogue the face changes about once a second; later the same day: every addition makes a very
short light sound, and whether face changes should sound is for the evidence to decide. Built: `production_script/2` with
`lines[].visual_beats` (text, label, prop, chart, highlight, symbol, accent, expression; `at` phrase + `offset`, `why`, `cue`) and
`cast.<id>.expressions`; stage 2b `beat-writer` + skill `visual-beats` (same segment, right after the scene-writer; `stage_guard
beats`, the editor may only move a beat's `pos`); `production/beats.py` (lint, timing, cadence checks, free deterministic render:
labels, rings, signs, counters, bars, props, a face push with an emotion mark and a cut-out face inset); `audio/cues.py` (ten
procedural cues of 25-180 ms, mixed undocked at -26 dB); beats count as MO events, a cue answers AL-03. Expression changes are
silent except one big take a line (Van der Burg 2008, Google earcon guidance, Connor 2019; STORY_ENGINE VB section). Legacy `/1`
scripts get one VB-00 REVIEW. Worked example: Episode 1's first three segments (`tests/fixtures/ep1_beats`, 49 beats, mean gap
1.23 s on the estimated read, 0 VB FAIL). Nothing paid, nothing painted, nothing read aloud.

## 2026-10-19 — Expression sheets for dialogue faces (D-55, VB-09, PV-44)

The creator: faces change about once a second in dialogue, so do not paint the hero again into every place; paint about ten
close-up expressions per speaking hero on green once, and in dialogue lay the keyed close-up over the scene's picture,
zoomed in and blurred. Built: `cast.<id>.face_sheet` (`id`, `ref`, `set`) in the schema; `production/faces.py` (VB-09 lint:
8-12 expressions, base set neutral/joyful/sad/scared/angry/surprised, every expression beat inside its hero's set, a reference
picture, a clean key edge once painted; the paint-plan items with prompts from the hero's card and the reference; the saving
against a full picture per face; chroma key with despill; the composite); `paint plan --faces` (a reusable plan behind the same
approve -> run gate, `faces_saving` in the plan, PP-06 knows the close-ups); palette token `chroma_key`; `assemble` composites
the dialogue frames. Tests: `tests/unit/test_face_sheets.py` (10). Nothing paid or painted.

## 2026-10-19 — A short scenario before every script; each hero talks like themselves (OR-15, PV-45, DW-11, PV-46)

The creator: always send a short scenario first, and write the script only once they like the final story; and every
character talks in the manner and vocabulary they are generally known for, or, when invented, from their personality.
Built: `episode.scenario` (file, approved_by, approved_at, sha256) and `scripting/scenario.py` (PV-45: missing or changed
after the approval is a FAIL on `/2`, a REVIEW on `/1`); `cast.<id>.speech` (basis public with sources or personality, style,
signature words, avoid) and `scripting/speech.py` (PV-46), written by the story-architect and used by the scene-writer; the
voice rule VC-02 (no imitation) is unchanged. Tests: `tests/unit/test_scenario_first.py` (3), `test_speech_manner.py` (3);
the /2 fixture of `test_visual_beats.py` records an approved scenario. Syndicate Wars: visual beats for all 31 segments in
`examples/syndicate_wars_ep1/beats/` (375 beats, written by the beat-writer procedure, 0 PV-44 FAIL per segment range), not yet
applied: the script waits for the creator's approval of `scenario_dialogue_v1`.

## 2026-10-19 — Syndicate Wars script v2: the approved story, boss dialogue, GTA VI world, 10 Shorts

The creator approved the short scenario (`examples/syndicate_wars_ep1/scenario.md`, bound by sha256 in `episode.scenario`)
with the GTA VI facts from Rockstar's own pages. Built: segment S03 (Leonida's six places and Rockstar's named characters,
named only, C-51..C-55, read first-hand 2026-10-19); 14 original boss lines (Capone, Vito, Mizuno, Shelby) with their own
cast voices by traits (ER-03), `speech` manners and face sheets; ten new Shorts SH01-SH10 (ten styles, each flags its invented
scenes); visual beats for all 136 narration lines (`beats/beats_by_line.json` + `beats_v2_new_lines.json`, `apply_beats.py`).
Editorial contract (`editorial_contract.json`: 27 graded sources, 32 claims; `line_kinds.json`) copied into the script by
the builder. An independent critic asked for 10 revisions (unsupported years on G03/G06, GTA V wanted-level wording, Vito's
death year, uninvented-looking Shorts, graphics one segment early); all applied; its re-review (`editorial_review.json`,
mean 3.92) leaves only EG-11 REVIEWs (C-03, C-05, C-17, C-29 unused). Rulebook v7 (RK-12 per-Short flags, new RK-19) and
the `script_lock` stamp pass; `paid_assets` is stale until re-checked. `production validate`: only PV-05 (pictures not yet
made). Tests: the full suite (397) including `test_syndicate_wars_example.py`.

## 2026-10-19 — RunPod money control in code (D-56)
Found (RunPod API, read-only): a stopped TMR preflight pod `etkpzxh16v1ksm` (60 GB volume) had billed $0.40/day since
2026-10-17 (billing API: $0.40, $0.40, $0.23 so far today) with the balance at $0.97; deleted on the creator's word, API shows
0 pods and $0/h after. Cause in the rules: they said "sweep and delete at the end" but nothing ran them, and TMR's sweep
ignored stopped pods unless `--delete`. Built (narrow; the in-pod side stays in TMR): `explainer_engine/cloud/runpod.py`
(port of TMR `rp.py` with retries, a create that is never POSTed twice, verified idempotent stop/delete, per-pod sessions,
guard with lifetime/boot/blind handling, `check`, `cost` from `GET /billing/pods`, `PodSession`), `config/spend_caps.json` +
`core/spend_caps.py` (the ledger refuses caps above the ceilings), `Run.settle`, and session hooks `cloud/hooks.py`
(SessionStart report, Stop refuses to end a turn while something bills unapproved, Bash refuses `rp.py create/start` and raw
`POST /pods`). Tests: `tests/unit/test_runpod.py` (27, fake RunPod API, no network); full suite 424 passed, docs_lint 0. No pod was started; $0 spent.
Not changed: TMR's conductor still deletes its pod at DONE by manifest (`end_action`), and its money clock restarts with a
container restart (`/proc/1` ctime); the outside guard here keeps the session clock, so it covers that case.

## 2026-10-19 — Syndicate Wars pictures: v1 recovered, one variant collage first (OR-16, PV-47), face sheets painted

The creator: before a hero or a world is painted for the first time, ONE collage of variants (colours, character, buildings),
approved, instead of many exploration pictures. Built: `scripting/reference_approval.py` (PV-47: every hero drawn in a painted
picture or with a face sheet has `cast.<id>.reference`, a script with painted pictures has `look.environment`: collage, tile,
library picture, approved_by, approved_at; FAIL on `/2` so paint refuses, REVIEW on `/1`; `collage_prompt` asks for 4-6 tiles in
one picture, `build_sheet` lays out existing pictures for free), schema fields, OR-16 in ORCHESTRATION. Syndicate Wars: the
v1 Gemini batch answers were still on the server, so 51 pictures came back for free (`runs/syndicate_wars/pictures_v1` on HF);
46 of the 48 the script needs plus the four portraits and s01_skyline. The creator approved the free collage of those
(`reference_collage_v1.jpg`, tiles 1-4 the bosses, 5 the world) and chose existing pictures for the two missing shots
(`It already has` -> s01_boardwalk, `And in the Keys` -> c12_palm); sc_* cards from `select_screen`. Four unused claims
(C-03, C-05, C-17, C-29) left the editorial contract; the independent delta review passes (EG gate PASS) and `paid_assets` is
stamped again. Face sheets: plan F1 (42 close-ups, Gemini batch, $1.105) approved and painted ($1.03 charged; three empty
answers repainted in the same plan). QA by eye: the painter framed about eight close-ups tighter, so a face change would jump
in size; `faces.same_framing` matches every close-up of a sheet to the tightest by the head silhouette (scaled up only, head
top and centre aligned); originals kept in `jobs/syndicate_wars/faces_raw`. Tests: `test_reference_collage.py` (6),
`test_face_sheets.py` (+1); `test_visual_beats.py` fixture records the pick. No pod was started.

## 2026-10-19 — Shorts carry the visual-beat layer and its cues (SS-09, PV-44)

Measured: the creator's Shorts keep about 80 % viewed vs 20 % swiped away (Studio, the creator, recorded in
PARAMETER_AUDIT section 0 in place of the open question), but likes per view are 0.4-1.0 % (small-channel median 1.71 %)
and vidIQ counted 1.4 changes every 10 s: people leave in the middle. The long video had beats (D-54/D-55); the Shorts did
not (no `visual_beats` on `shorts[].lines[]`, PV-44 over segments only, no beats or cues in `production/shorts.py`).
Built: the schema takes `visual_beats` on a Short line (the same `$defs/beat`); `beats.short_doc` turns a Short into a
one-segment script on the video's pictures so `beats.lint`, `timing.time_script` and `beats.check_timed` run on it
unchanged; `validate.short_beat_findings` (PV-44, every Short on its own estimated read at 170 wpm, reported as
"SH03 line 2"; FAIL on `/2`, nothing on a legacy `/1` without Short beats); `assemble.finish_frame`, `beats_for_shot`,
`hero_faces_of` and `cue_bus` lifted out of `assemble` unchanged so `shorts.py` draws every frame (9:16 crop + push, face
focus, accents, close-ups, beats) and mixes the cues with the long video's own code; a label or ring whose spot falls outside
the 9:16 crop is moved inside it (counted in the Short's report); the stage guard lets the beat-writer write Short beats
only. Rule SS-09 (STORY_ENGINE), PV-44 text, skills `visual-beats` and `shorts-for-video`, agents `beat-writer` and
`shorts-writer` updated. Syndicate Wars: `apply_beats.py` attaches beats to Short lines by exact text (47 lines share the
video's beats); the beat-writer procedure wrote 86 beats for the 22 Short-only lines (`beats/beats_shorts.json`, each with
its cue, no numbers on screen, no new pictures): 255 beats on the 69 Short lines, 0 PV-44 FAIL on the Shorts; `production
validate` after rebuild + compile: only the 14 PV-05 (pictures not made). Tests: `tests/unit/test_short_beats.py` (8).

## 2026-10-19 — Syndicate Wars: paid_assets stamped (rulebook v8)

Rockstar's fan-content policy page read first-hand (B-14 verified, RK-02 evidence); one franchise word removed from the
`w02_studio` prompt (RR-03); `script_lock` and `paid_assets` stamped on rulebook v8 with the condition that pictures recovered
from earlier Gemini batches are only ones painted from today's prompts, never the pre-v2 Vito/Shelby portraits, each face checked
for actor likeness. Editorial review rebound to the script (EG-11 REVIEWs only).

## 2026-10-19 — voice casting: age is a hard filter (creator: "ages matter most")

Three voice options offered for Vito and Mizuno sounded too young: they were picked by name and description, outside
`audio/casting.rank`. `casting.age_of` now reads `voice.traits.age`, or the age words of the style and card; `rank` never
offers a voice labelled two bands off or a young voice for a middle-aged hero; PV-32 REVIEWs a speaking hero whose age is
unknown. Tests: `tests/unit/test_casting_age.py`; `test_casting_ranks_returned_voices_and_never_reuses_one` now expects the
young voice to be dropped for the old hero.

## 2026-10-19 — voice casting: ethnicity, accent and region (VC-05); Syndicate Wars picks

Creator: Capone = Crazy Eddie, Vito = Mr Wellington; Mizuno must carry a Japanese accent and Shelby a Birmingham accent ("add the
ethnicity to the rules too"). `traits.ethnicity` is new in the schema; `casting.accent_of` reads `origin`, then `ethnicity`
(Japanese and Welsh among the accents); `casting.region_of` puts a named region (Birmingham, Midlands...) into the search text
and a +2 weight in `rank`, because library labels only say "british". PV-32 REVIEWs a hero with no accent source. Rule VC-05 in
`docs/STORY_ENGINE.md`; tests in `tests/unit/test_casting_age.py`. Cast styles of Mizuno and Shelby changed in the content file;
the script is rebuilt and the stamps re-bound once all four voice ids are fixed (ES-16). Library search found no West Midlands
male voice; Midlands candidates (Robert, Dan) and a Japanese-accent voice (Hideo) were sampled, 122 credits.

## 2026-10-19 — Syndicate Wars: full read, words and shot plan on the real read

Full read on ElevenLabs v4: 26 chunks paid (9,127 credits, settled in `run.json`), 7 reused from the test reads. The narrator
read 115-130 wpm (EL-12 asks 155-185): his chunks were sped up 8 % with atempo (the cap the creator allowed for Shorts) and the
creator is asked whether to keep it; the chunks are levelled to -29 LUFS before the join (26.5 dB spread; `seams` clamps at 6 dB).
`production words` now hears every chunk alone (`local_words.transcribe_chunks`: on the joined 12-minute read Whisper dropped
repeated words, coverage 96 %); `scribe_words.norm` reads British spellings, hyphenated words and dollar amounts as the recogniser
writes them; `pause_pad` searches 0.25 s round a gap and inserts only below -46 dB, under the dropout scan's -42 dB (6 cuts ->
0 FAIL); `validate` finds a painted picture by its id like `assemble.find_picture` (46 false PV-25). Coverage 97.1 %, 12:15.
`fill` added 50 re-framed shots (RHYTHM-3); two painted shots it dropped were restored by moving their anchors; four beats added,
one cue moved (VB-01/VB-08). Editorial review and rulebook stamps re-bound (shots and beats only). Tests:
`test_scribe_words.py`, `test_pause_pad.py`, `test_local_words_chunks.py`, `test_production_script.py`.

## 2026-10-19 — Syndicate Wars: render, 10 Shorts, publish checklist

Main video rendered in 12 chunks of about 60 s (RULE-R1) and joined: 12:14, 1920x1080 30 fps, -14.7 LUFS, true peak -1.1 dBTP,
no music or ambience bed (none was planned). The Shorts reuse 47 lines cut from the main read; 22 new lines were recorded on the
narrator's voice (1,739.83 credits, settled; credits = prompt characters), paced +8 % and levelled to the cut lines (-28.8 LUFS).
Looking at the first Shorts found two defects, both fixed with a test: a dialogue close-up (16:9) was pinned to the left edge of
the 9:16 frame, so the speaking hero fell off screen over a blurred background (`faces.composite` now centres it and caps it at
`PORTRAIT_W` frame widths in a portrait frame; the long video is unchanged); the stat cards (`sc_*`) were cropped to 9:16 and lost
their title and stars (`shorts.fit_screen` fits the whole card over a blurred fill and moves its spots with it). `publish.json`
written from the real segment times (10 chapters); `publish_check`: 0 FAIL, 3 REVIEW for the creator (mid-roll, self-certification,
approval #2). Tests: `test_face_sheets.py::test_composite_in_a_short_centres_the_hero_of_a_wide_close_up`,
`test_short_beats.py::test_a_stat_card_is_fitted_whole_in_the_short_and_its_spots_move_with_it`.

## 2026-10-19 — Syndicate Wars staged on YouTube; a Short is checked to be a Short

Long video and 10 Shorts staged unlisted (state in `examples/syndicate_wars_ep1/publish/youtube_state.json`), each item as it
passed (standing order 9). The creator saw the Shorts as videos: YouTube had made all ten Shorts (1080x1920, 0.5625, under
60 s; `youtube.com/shorts/<id>` answers 200, the long video redirects), but the links given were `youtu.be`, which opens the
ordinary player. `qa/short_format.py` now checks a Short file (SF-01 horizontal, SF-02 not 9:16, SF-03 over 180 s),
`production.shorts` refuses to hand on a file that fails, and links to Shorts are `youtube.com/shorts/<id>`. The upload tool
(PR #7) should run the same check before `videos.insert` once it is merged. Test: `tests/unit/test_short_format.py`.

## 2026-10-19 — YouTube staging upload (D-57): unlisted, everything filled in, the creator clicks Public

The creator: when the video and the Shorts are done, upload them unlisted with title, description, tags, thumbnail, US location,
not made for kids and no paid promotion; they only check and publish. Built `explainer_engine/publish/` (stdlib): `plan.py` (the
`videos.insert` bodies from `publish.json` + the script's Shorts; chapters into the description; tags fitted to 500 characters;
the Shorts link the long video), `youtube.py` (token refresh, resumable upload with resume after a drop, thumbnails.set, read-only
channel and duplicate checks; refuses public and `publishAt`; no `videos.update`), `stage.py` (PC gate, channel id check, ids
saved per file sha256 so nothing uploads twice, daily quota counter, the Studio review checklist), `thumbnail.py` (Gemini 3 Pro
Image behind the estimate -> creator OK gate, headline in our font, TN checks), `auth.py` (one-time sign-in on the creator's PC).
`publish.schema.json` gains optional `tags`, `youtube`, `thumbnail`, `files`, `pinned_comment` and per-Short `title`/`description`/
`tags`. New rules file `docs/THUMBNAIL_RULES.md` (TN-01..TN-11, sources V-49). API facts V-45..V-49: location is deprecated in
the API and paid promotion is not settable on insert, so both are Studio checklist items; an upload costs 1 unit of a 100/day
bucket now, not 1600 units. The old YouTube token in the cloud env (TMR's) has expired: the creator re-authorises once.
Tests: `tests/unit/test_youtube_publish.py` (13, fake API, no network). Nothing uploaded, nothing paid.

## 2026-10-19 - Thumbnail and package research, rules regraded (PR #7)
Five research passes (YouTube Help/policy, studies, curiosity/colour/AI, niche cases, title/tags/description) in
`docs/research/thumbnail_research_2026-10-19.md`; V-50. Finding: policy is solid, element rules are weak, so `docs/THUMBNAIL_RULES.md`
now grades every rule (P/S/H), adds the clothed noir-silhouette motif with the exact sexual-content line (TN-12, TN-13), package
rules for title, tags, description and Shorts (TN-14..TN-18), a review checklist and a Test & Compare plan (T-1..T-5, sample sizes).
`publish/plan.py` now flags titles over 70 characters, more than 3 hashtags in the long description, over 60 anywhere (FAIL) and
"18+"/"21+" wording; test `test_package_findings_follow_the_thumbnail_rules`. Not done: no thumbnail painted (needs the silhouette
collage approval, cost shown, creator's OK); vidIQ outlier pass not run (credits need approval). 411 tests pass, docs_lint 0.


2026-10-19 vidIQ thumbnail pass: 2 calls, 10 credits (balance 90 -> 80); no usable evidence (research file, Appendix F). Ledger about 165 of 200 by project memory, past the 160 stop line; no more vidIQ calls without the creator's word.

2026-10-19 thumbnail niche study (free): looked at 28 real thumbnails of the niche (research Appendix G, contact sheets in docs/research). Finding: bright, face-forward, versus layouts, fixed templates; no dark silhouette as a main subject. TN-12 changed to a small cameo, TN-19 (named heroes/versus) and TN-20 (one template) added. Gemini: one collage $0.134 (silhouette variants, creator OK), now not the main subject; no thumbnail painted yet.

2026-10-19 thumbnail drafts v2 (nano-banana 2K, $0.107; thumbnails today about $0.40 in all): Vito and Shelby seen only from behind, dressed in the films' look on the creator's order (tuxedo and slicked grey hair at a long table; undercut, flat cap, long coat by a canal). This overrides Syndicate Wars ER-04/RK-05/RK-06 ("no production costume combination") for back views; faces stay invented (RK-07). The episode rulebook on systemic/next-video must record the change (episode-standards-director) before the thumbnail is used. Files in project-files explainer-engine/thumbnail_motif.

2026-10-19 thumbnail is the creator's job (creator): `publish stage` no longer sends a thumbnail unless publish.json `thumbnail.upload` is true; the Studio checklist says "YOUR thumbnail set in Studio"; `publish thumbnail` stays as the paid draft maker. Test `test_thumbnail_is_sent_only_when_publish_json_allows_it`; THUMBNAIL_RULES.md and PUBLISHING_AND_ANALYTICS.md updated.

## 2026-10-19 — The scene rewrite: production_script/3, SC rules, inverted cues (D-58)

After the creator's Syndicate Wars review (senseless cues, no real dialogue, press-release narration, "rewrite the whole
system"), the storytelling and editing system was rewritten from research on a new schema; `/1`/`/2` keep their exact
behaviour and the finished video stays as it is. Research first (6 notes + a synthesized report, Georgian summary
approved by the creator), then rules: every new or changed rule carries at least two source types in
`docs/research/STORYTELLING_EDITING_2026-10-19.md` (the creator's sourcing rule).
- Schema `production_script/3`: `segments[].scene` (place, present, pov, want/obstacle_want, value, charges, turn,
  exit, surface/real subject, mode), `lines[].to` + `intent`, beat `cue.event`.
- Code: `scripting/scene_lint.py` (SC-01..SC-10, PV-48 in `production/validate.py`); `story_lint` ST-00 FAIL on /3 +
  ST-12/ST-13; `production/beats.py` VB-08 inverted on /3 (silence default, event-bound cues) + VB-10/VB-11 + /3
  pacing gates + de-stack of beats collapsed onto one instant; `audio/cues.py` 3 deterministic pitch variants and
  `assemble.cue_bus` rotates them; manifest `loop`/`intended_seconds` + `Sounds.loopable` so one-shots are never tiled
  (beds/music `play_once`, Shorts `-stream_loop` gated); `audio/layers.py` AL-02 counts cues; `edit/motion_lint.py`
  MO-07 hold variance; `scripting/speech.py` signature-words-used check on /3.
- Docs: STORY_ENGINE (SC section, DW-09 softened + DW-12/DW-13, three story templates replace the beat grid, ST/VB/MO
  rows), EDITING ED-14 (dialogue coverage grammar), PRODUCTION_SCRIPT (/3 + PV-48), INDEX, D-58 in the decision log.
- Skills/agents: new `dialogue-scenes` (scene header, hand-off unit, deflections, worked Capone/Enzo example);
  `visual-beats`, `story-engine` updated to /3; agents scene-writer, story-architect, beat-writer, edit-planner.
- Tests: `tests/unit/test_scene_system.py` (20); whole suite 425 passed, 1 skipped; docs_lint 0 findings. The
  Syndicate Wars example test is untouched and green (its /2 contract is frozen).
- Next: the next episode is written as `/3` by the writers' room; the parallel audit thread covers the rest of the
  system (its input: `/mnt/project-files/explainer-engine/storytelling_research/RULE_CONFLICTS_2026-10-19.md`).

## 2026-10-20 - System audit and the sourced rules (D-59; branch claude/system-audit-sourced-rules-3i81ai, draft PR to next-video)
The creator (2026-10-19): no production rule is law; find the contradictions between the rules first, then research best practice
with verifiable sources (two of three types per change), then put the rules into Python, the skills and the agents. Done in that order:
(1) four audit passes (narration, audio, editing/motion, governance) over CLAUDE.md, the docs, the validators, the skills and the agents
found 211 contradictions (`docs/research/SYSTEM_AUDIT_2026-10-19.md`; the shared folder `SYSTEM_AUDIT_2026-10-19/` has the four research
files too), the worst being gates that never ran on the D-43 flow (seven-point test, loudness/true peak, `check_shots`, PC-08) and numbers
restated in 3-7 places (pace 150-185, pictures per minute 10 vs 13-14, zoom 1.15 vs 1.25, bed "20 dB" vs 14 vs 10 vs -15, Shorts length
in four bands). (2) Research of 209 fetched sources (narration 40, audio 63, motion/text 51, retention/Shorts 55; every URL opened, nothing
from a snippet; books verified through quoting pages or Open Library search-inside; videos through oEmbed/transcript pages).
(3) The registry `explainer_engine/standards/sourced_rules.json` (BP-01..63, 54 rules: 43 binding, 8 hypotheses, 3 house) with
`standards/sourced_rules.py` (`T`, `check`, `render`, `write`), the generated `docs/SOURCED_RULES.md`, `docs_lint` home `BP`,
`tests/unit/test_sourced_rules.py` (registry ↔ table ↔ code). Validators now read `SR.T(...)`: `narration_lint` N-01 (four hook forms,
greeting FAILs), N-05 (median 12 / 20 / FAIL 25), new N-11..N-14 (30-s contract, register, numerals, press-release lines FAIL);
`validate` PV-12 forwards REVIEWs, PV-28 Shorts bands/hook/sign-off/readability, PV-34 from BP-45, new PV-52 pace band, PV-40 pod allowed
when the plan names it; `shorts.py` leading-silence trim, hook spoken within 1 s (BP-11 refusal), caption and safe-zone report rows,
tempo cap 1.08, stereo 384k export and a loudness check of the final file; `engagement` ENG-7 (microhook every 150 s), ENG-8 (abrupt
ending); `scorecard` pace band + a CLI on the episode folder (`python -m explainer_engine.qa.scorecard <episode>`) + LU/LDR rows;
`speed.py` rates 1.05/1.08; `motion_lint.check_sourced` BP-20..33 (scale range and rate, pan cap, easing, shake only on impact, flash
safety, text holds and safe area, dissolve only on a period boundary, expression lead and hold); `continuity.ZMAX` 1.15 + BP-30;
`board` section-aware RHYTHM-3 (5 s hook / 20 s REVIEW / 40 s FAIL) + BP-41 interrupt; `fill_holds` stops stacking on beats;
`faces.composite_match` (anti-sticker) and the expression lead; `accents` flash 2 frames at 80 %, text hold cap; `targets` profiles from
BP-50/61, `ldr_verdict`, LU `gap_verdict`, `measure_file`; `assemble` measures loudness + true peak + dialogue anchor and refuses a final
render on FAIL, stereo 384k mux; `duck`, `layers` (asymmetric sync 45/125 ms, BP-55/57/62), `seams` (1.5 dB gate), `pause_pad` (room
tone), `sfx_library` (one-shot vs loop); `publish_check` PC-08 FAIL + PC-09 (final_qa stamp, scorecard); `production_gate` gates 8/9 read
them; `plan.py` PP-05 is a REVIEW (D-50: the creator picks the provider); `hook.py` denies a paid call on an editorial FAIL (OR-10);
`publish/plan.py` posting spread (BP-47). Skills and agents carry a "Sourced rules" section (narration-script, shorts-for-video,
elevenlabs-voice, editing-style, video-editing-architect, shot-visuals; performance-director, script-critic, shorts-writer, edit-planner,
orchestrator, episode-standards-director); docs link BP ids instead of numbers (VIDEO_PARAMETER_SPEC, AUDIO_SYSTEM, UNIVERSAL_RULE_BASE,
QA_SPECIFICATION, ORCHESTRATION, PRODUCTION_RULES, NARRATION_AND_LANGUAGE_GUIDE, PUBLISHING_AND_ANALYTICS, RIGHTS, EPISODE_STANDARDS);
CLAUDE.md invariant 2 reworded, 3 retired, 6 reworded; Kokoro rows marked superseded.
Tests: 541 passed, 1 skipped (new: test_sourced_rules 7, test_sourced_narration 18, test_sourced_motion 21, test_sourced_audio 27);
docs_lint 0; registry check 0. Nothing paid, nothing uploaded.
Not done / for the next PR: BP-52 in LU on real mixes needs BS.1770 stem measurements in `build_audio` (PR #9's region; the scorecard
treats RMS stats as REVIEW until then); the Short's mono phone check (BP-61); payoff position (BP-04/BP-44) is a writer/critic rule, not
machine-checked; the `sfx_manifest` schema needs `kind` (PR #9 owns it); STORY_ENGINE AL-02/AL-03 wording is PR #9's file (PRODUCTION_SCRIPT's PV-40, PV-52 and
PP-05 rows were brought in line here after CI caught the missing PV-52 row); the Syndicate Wars example now scores FAIL on pace (122 wpm) and hook-window stills (it stays as is, the
creator's word). Overlaps with PR #9 listed in the PR description.

## 2026-10-20 - Rule consistency after the merge: audio
Rescan findings A R-01..R-03, R-19..R-23, R-29c/e/h, B audio rows and C 2/5/6/7 fixed. New registry entries: BP-49 (AL-02 band,
hypothesis), BP-64 (beat-cue length and level, house FAIL, D-58; BP-58's one-shot floor does not apply to an earcon), BP-65 (AL-04
pre-mix gain caps, hypothesis: a dBFS proxy, BP-52 stays LU on the stems), BP-66 (an effect over speech is synced or masking, house
FAIL, the creator's 2026-10-16 note). Code: every duck reads BP-53 (assemble's `vduck 0.55` gone; the bed under a world sound dips by
BP-53's floor, 6 dB, not the superseded 4); music fades 1 s in / 2 s out from BP-62 in timing, the mix and the Shorts, with a fade
check in `layers.music_findings`; cue pitch variants are 1 +/- BP-57's jitter and cue runs are no BP-57 finding while the bus varies
them; AL-02 has no lower bound on `/3` (the timed file now carries `script_schema`); the sped file (`finish/speed.py`) uses BP-63's
codec; the scorecard caps BP-01 at the registry's severity (REVIEW: a hypothesis never FAILs, so a slow read no longer blocks gate 8 /
PC-09 on its own) and FAILs only an effect that masks a word, not one synced to its word by BP-54. Every severity comes from the
registry. Defaults applied (the creator may overturn): BP-53 covers every music duck under the voice. STORY_ENGINE AL rows, EDITING
ED-03/ED-06, AUDIO_SYSTEM, IMPLEMENTATION_PLAN, QA_SPECIFICATION and three skills link the BP ids. Tests: tests/unit/test_rule_consistency_audio.py
(18); test_scorecard, test_sourced_audio and test_sourced_narration now expect the registry's value (masking event moved into the word,
cue runs varied, BP-01 severity). Nothing paid.

## 2026-10-20 - Rule consistency after the merge: picture / motion / visual beats

What changed (the D-59 audit's findings for pictures, motion and visual beats; one number, one home):
- Registry: new BP-36 (VB-01 cadence), BP-37 (VB-02 faces), BP-38 (VB-04 text words, bars), BP-39 (VB-08 cue spacing),
  BP-80 (VB-10 repeats), BP-81 (VB-11 cue density) as house FAIL rules (the creator, 2026-10-20: PR #9's scene-rewrite
  limits stop an episode, numbers from D-58); BP-82 (VB-05/07) and BP-83 (MO-02..07) as hypotheses (REVIEW only); BP-84
  (shot floors, bubble words: D-42/UR-31), BP-85 (UR-01..17 storyboard numbers: D-37) and BP-86 (PV-29 crossfade and tick:
  ED-03) as house rules. BP-20/24/27/28/30/33/40/41/45 amended (statements and `enforced_by`); SOURCED_RULES.md regenerated.
- Code reads every number and severity from the registry: `production/beats.py`, `edit/board.py`, `edit/motion_lint.py`,
  `edit/shot_rules.py`, `production/validate.py` (PV-24, PV-29, PV-34), `fill_holds.py`, `accents.py`, `continuity.py`,
  `finish/bubbles.py`, `design/palette.py`. No check carries a literal FAIL/REVIEW where a rule exists.
- `board.change_times` counts visual beats, data visuals and cards (C-1): a dialogue held on one picture with an
  expression change per line passes RHYTHM-3 and BP-41; the synthetic /3 script went from 1 FAIL (base) and 3 FAIL
  (hook by beats) to 0 FAIL on `production time` and `validate`. MO-01 is section-aware (hook / body of BP-40).
- Shorts: VB-01's cadence does not run on a Short; BP-45 owns its pace and PV-34 counts beats as events (C-11).
- UR-01 checks BP-03's hook forms instead of the superseded "question by 5 s"; BUBBLE-2 uses BP-27's hold (a hypothesis,
  so REVIEW; it supersedes UR-31's `max(1.4, 0.3 n)`).
- `python -m explainer_engine.edit.board` on a production script now exits 2 with "not a storyboard ... production time"
  instead of `KeyError: 'shots'`.
- Docs, skills and agents link the BP ids instead of restating 1.25 zoom, 3-6 s pictures, every 9 s, 3-frame flash,
  1.6 s pop hold, 8/15 s and 4/6/0.7 s cadences, "a sound on every accent", 14 framings, the 1.5 s Shorts metronome
  (SS-09), the J/L 0.4 s lead (a bed pre-lap, not ED-14's J/L cut) and the 40/20 tone mix (BP-09). MO-07's hold variance
  and BP-40's still limits are documented as satisfiable together.

Defaults applied: a visual beat is an on-screen change; a binding BP rule wins over a house or doc number; a hypothesis
never FAILs.

Tests: new `tests/unit/test_rule_consistency_motion.py` (registry pins, severity read from JSON, C-1, Shorts, bubbles,
PV-29, the board CLI error). Expectations moved to the registry: `test_short_beats` (VB-01 FAIL on a Short -> BP-45),
`test_shot_rules` (UR-01 question by 5 s -> BP-03 forms; the v3 cold open passes), severity reads in `test_visual_beats`,
`test_scene_system`, `test_shot_rules`. Full suite: 574 passed.

## 2026-10-20 - Rule consistency after the merge: narration, story, scenes, Shorts text

The D-59 rescan (A R-13..R-15, R-24..R-26, R-29 narration lines; B tables 1-3 narration rows; C-3, C-4, C-9, C-10, C-12) fixed for
narration, story, scene and Shorts-text rules. Every number now lives in `standards/sourced_rules.json` and every check of this group
takes its severity from the registry entry (`sev(...)`), so a FAIL/REVIEW decision is a JSON edit.

- New registry entries: BP-16 (N-03 ellipses, house FAIL), BP-17 (N-06/N-07 question and interjection density), BP-18 (N-10 wh-question
  length), BP-70 (SC-05 exchange), BP-71 (SC-08 disclaimers), BP-72 (SC-09 turn and speech caps), BP-73 (SC-09 jab review and DW-12 Q&A
  chain), BP-74..BP-76 (ST-11..ST-13), BP-77 (rights quote and recap limits of `rights/ip_check.py`). PR #9's scene limits (BP-70..72)
  are house FAIL as the creator confirmed on 2026-10-20. BP-01, BP-03, BP-04, BP-10, BP-11, BP-12, BP-15 and BP-43 got statements and
  `enforced_by` rows that match the code.
- C-3: one pace. ST-13, engagement, the Short length and PV-52 all use BP-01's heard pace; PV-52 now compares the heard pace of the
  estimated read (pace_wpm plus pauses), not the configured speaking rate.
- C-4: one press-release lexicon (BP-15 phrases + patterns, "launches worldwide" added) shared by N-14 and SC-07, on narrator lines only
  (`narration_lint.doc_findings`); a hero may name a date in a scene. Default applied: /1 and /2 scripts get the phrases only (D-58 keeps
  their contract); the patterns bind from /3.
- C-9: BP-11's hook word cap and its 3 s hook end are both checked (PV-28 on the estimated read as REVIEW, `shorts.hook_timing` on the
  real read at the registry severity); the registry states that at 170 wpm the time bound is the tighter one (about 8 words).
- C-10: one Short duration, `validate.short_seconds`; `short_words` scales the estimated read to it. BP-12's statement now quotes the
  bands its thresholds compute (38-93 and 115-234 words).
- C-12: ENG-3 counts a chart beat with values, or a text beat with the number, as shown. ENG-5 reads BP-04's `answer_after_share`;
  ENG-8 reads BP-43's `end_screen_narration_min_s`.
- Defaults applied: BP-10 governs narration holds (new N-15 on a narration line's `pause_after`); a silence beat inside a dialogue scene
  is a scene device. The EG-18 rubric numbers in `editorial_gate.py` are named process constants (SCRIPTING_SPEC section 5), outside the
  registry. Humour share (old 20 %) now points to BP-09's joke density in the docs and skills.
- Docs, skills and agents point at the BP ids instead of restating numbers (NARRATION_AND_LANGUAGE_GUIDE, PRODUCTION_RULES,
  UNIVERSAL_RULE_BASE UR-01, STORY_ENGINE ST/SC/DW/SS rows, PRODUCTION_SCRIPT PV-12/PV-28/PV-52, ORCHESTRATION, EPISODE_STANDARDS,
  VIDEO_PARAMETER_SPEC P-05; skills narration-script, shorts-for-video, story-engine, dialogue-scenes, elevenlabs-voice; agents
  scene-writer, story-architect, shorts-writer, orchestrator).
- Tests: `tests/unit/test_rule_consistency_narration.py` (26 tests; severities read from the registry, severity-switch tests flip the
  JSON). Two older tests changed only their expectations for the new definitions: `test_sourced_narration.py::test_pv52` (heard pace)
  and `test_eng8` (its pointer now sits more than BP-43's end-screen time before the end). The synthetic /3 script shows the effect: a
  date in a hero's mouth no longer FAILs, "launches worldwide" on a narrator line FAILs SC-07, the base script's estimate is heard at
  150 wpm (PV-52 REVIEW), a 10-word Short hook ends at 3.1 s (PV-28 REVIEW), and the three Short durations agree.

## 2026-10-20 - Rule consistency after the merge: integration
The three groups above were merged rule by rule (registry 54 -> 80 rules; `sourced_rules check` 0 findings) and their
cross-group handoffs applied: VB-08's cue-length check takes BP-64's severity (`beats.py`), PV-34 uses the one Short duration
(`validate.short_seconds`), edit-planner and the visual-beats skill cite BP-49 and BP-64, EDITING ED-03 links BP-86,
SCRIPTING_SPEC's "question by 5 s" follows BP-03, UR-03's "no withheld payoff" now reads with BP-04. `test_short_beats`' held
line was lengthened so it still outlasts BP-45's still limit at BP-01's heard pace (the Short read got faster; the check is
unchanged). The creator's decision (2026-10-20, decision card): PR #9's own gating numbers stay FAIL, as house rules. Re-run
of the free end-to-end probes on the merged result: the synthetic /3 base and hook-by-beats scripts validate and time with 0 FAIL
(before: 1 and 3 FAIL); the deliberately broken variants still FAIL on their own rule (VB-08, VB-10, RHYTHM-1/2). Syndicate
Wars' scorecard has no FAIL left from a hypothesis (pace 122 wpm is a REVIEW). Tests 618 passed; docs_lint 0. Nothing paid.

## 2026-10-20 - The integrated production-coherence review (D-60)

The audit this thread ran traced the one gap the scene rewrite (D-58) and the sourced rules (D-59) left open: every
deterministic validator judges one layer against its own rules, the script-critic's instructions sampled layers
(10 random beats, the narration read) without a contract proving the whole plan was read together, and the
`editorial_review/1` JSON carried only 13 broad scores — so a `/3` script could pass everything while its combined
dialogue, visual, performance, audio and timing plan undermined its own story. Proven with seven fixtures that pass
`check_script` with 0 FAIL yet carry a cross-layer defect (a reveal cut away from with a bright sting, a non-sequitur
answer, an entrance whose narration contradicts the scene header, an elder in the scout's register, a chime scoring
dread as a win, a resolution that contradicts the midpoint, a cut before the reaction lands).

- The smallest implementation: `editorial_review/2` extends the existing independent review (no new agent, gate or data
  model). `integrated.layers` — story, entrances, dialogue, visual, performance, audio, timing — each with evidence and
  an honest basis (`data` / `estimate` / `instructions`: unrendered media is never claimed as seen); `integrated.findings`
  machine-routable (exact refs that must name something of the script, expected vs instructed, conflict, consequence,
  confidence, smallest fix, owner stage). FAIL blocks gate 0.5, paid narration (OR-10 hook) and paint preflight through
  the existing `editorial_gate.check` call sites; REVIEW is the creator's call; taste lives in `notes` and never blocks.
  New checks EG-19..EG-22 in `production/editorial_gate.py`; a `/3` script with a `/1` review is EG-19. `/1`/`/2`
  scripts keep `editorial_review/1` byte-for-byte (their tests unchanged).
- The judgement stays with the script-critic (stage 7, fresh context): its agent file now walks the seven layers as one
  timeline and writes the `/2` review; the gate validates coverage, honesty and concreteness deterministically, so a
  deliberate rapid entrance or an unconventional structure is never auto-rejected (both pinned by tests).
- Docs: [SCRIPTING_SPEC](SCRIPTING_SPEC.md) section 5.2 (the contract), OR-10 row, STORY_ENGINE stage 7 row, the
  story-engine skill, CHATGPT_WORKFLOW; decision [D-60](DECISIONS_AND_OPEN_QUESTIONS.md).
- Tests: `tests/unit/test_integrated_review.py` (27: the gap fixtures, blocking and routing, stale-on-edit, fail-closed
  on a missing/malformed/half-written review, a correction that breaks another layer caught on re-review, legacy
  contract intact, gate 0.5 wiring, no-false-positive cases). Nothing paid; no renders claimed.

## 2026-10-23 - LoRA training control: protocol, tools and four agents (D-72)

ვანო asked for a coordinator / multi-agent system for the three LoRAs (photo style, image-edit next pose, video motion),
built on researched testing practice, and for step-by-step control of the running trainings.

- Research (sources in [LORA_TRAINING](LORA_TRAINING.md) section 3): judge checkpoints by fixed-seed samples, not loss;
  overfitting = same background/pose whatever the prompt, prompt words ignored, colour burn, unasked objects; held-out
  prompts and a no-trigger probe; video with vs without the LoRA, temporal metrics only together with motion amount.
- Code `explainer_engine/training/` (free, local): `audit.py` (LT-01..LT-15: captions, trigger, shared phrases and
  words, duplicates, resolution, the creator's weighted share, edit-pair matching, LTX clip frames/sizes; config check of
  ai-toolkit and ltx-trainer YAML; cost projection), `judge.py` (LT-20..LT-43: style progress per prompt from the base
  toward the creator's pictures, adherence, memorisation, sameness, trigger leakage, the CONTINUE/STOP decision; video
  motion/jitter/keyframe; edit drift/change; tqdm log parser), `embed.py` (CLIP ViT-B-32 on CPU, cached; needs torch +
  open_clip_torch, not in requirements). CLI `python -m explainer_engine.training`.
- Agents `lora-coordinator`, `lora-dataset-auditor`, `lora-run-operator`, `lora-checkpoint-judge`; skill
  `lora-training`; docs_lint home `LT` -> LORA_TRAINING.md.
- Applied to the live runs: dataset v7 audit FAILed on 12 pictures under 512 px (504x278 in the creator's folder) and
  22 crops reusing their full image's caption -> the photo thread dropped them before v4 (his share 54 %). v3 config:
  cached text embeddings made caption dropout a no-op, no no-trigger probe, samples ≈20 % of the run -> fixed in v4. v3
  judge: step 250 progress 0.55, step 500 0.42 (the close-up fell back to semi-photo, confirmed by eye) -> v3@250 is the
  best v3. v4 config PASS; projection ≈$1.8 vs its $1.65 cap (expect a stop near step 1300).
- Tests: `tests/unit/test_lora_training.py` (19). Nothing paid in this thread.
- 15:00 Footage plan (ვანო 14:51): `training/footage.py` (FS-00..FS-07: probe, shot split, camera/motion measure, show
  balance and held-out, master-frame pairs, 89-frame clips, motion-caption name ban) + 2 tests on a synthetic video;
  the plan with costs (first full cycle ≈$55-75) in project files `FOOTAGE_PLAN_2026-10-23_ka.md`; both threads briefed.

## 2026-10-23 - Video QA in code: morphing, melting, flicker, lost parts, layout fidelity, cartoon rhythm (LT-50..LT-59)

- ვანო 22:32 (Tbilisi 02:32): "write it in code, watch hands, faces and the usual AI mistakes, measure every parameter,
  use the hours of cartoons as the norm; B's IC video has no feet". `training/video_qa.py` + CLI `video-qa`,
  `footage-rhythm`; thresholds in `lora_rules.json` "video_qa" (house starting values).
- Measured on the first IC test (A/B, 5 s, 1920x1088): all four clips PASS flicker/morph/lines (morph p95 0.009-0.015);
  the B_ic defect is not visible in global numbers. Cause found by eye: our bend-rig layout smeared the scientist's legs
  into shadow and left a dark ghost where he stood; the IC render followed the layout and drew a second caveman there.
  LT-59 (layout fidelity per grid cell) flags exactly that area from 2.4 s. Lesson: an IC shot is only as good as its
  layout; layouts need a clean plate behind moving people and rigid legs.
- Weak spots stated in the module: hands and faces are judged by eye on `--sheet` (LT-58); the box tracker follows ink
  outlines but can still lose a fast character, so LT-55 is REVIEW only.
- Tests: 3 synthetic line-art clips (clean PASS; melting + brightness pop; lost legs + an invented figure vs its layout).
- 23:55 Hard multi-shot test (4 heroes, a 30-person crowd, 10 s) and max length from one photo (plain LTX-2.5 distilled,
  1920x1088, 10/15/20 s render in 5/8/11 min on an A40, no OOM). IC: identity and stability hold for 10 s, but motion
  follows our too-timid warp layouts (hold share 1.0); a stronger warp bends faces, so warps cannot carry acting. Plain
  I2V acts well; by length: 10 s clean (detail x0.75), 15 s a duplicated girl appears in the bus window and the bus
  changes, 20 s two heroes turn translucent (detail x0.57) and "Static camera" is ignored at every length. New LT-53
  REVIEW on detail loss catches the 20 s ghosting; cartoon norm (120 shots): hold share p50 0.77.
- 00:20 (2026-10-24) IC conditioning strength 0.6 and 0.4 (hoping the model adds acting): the render turns into the grey
  clay layout and still does not act; Layout-To-Render needs strength 1.0, and acting must come from the layout itself.
  LT-54 now FAILs a saturation loss over 0.2. Night video tests ≈$2.5 (4 pods, all stopped).

## 2026-10-24 - Continuity across a cut in code (LT-60..LT-62) and the eras clips

- ვანო 07:17 UTC: "does anything check consistency between the frames of the video, or is the scene LoRA drawing the
  stills right enough?" Answer: a scene is cut from several <= 10 s shots (max-length test), so the join between shots is
  where the look jumps; nothing measured that. `video_qa.shot_identity` + CLI `shot-identity <a.mp4> [<b.mp4>]
  [--heroes]`: A's last frame vs B's first (or one clip's first vs last): the set's palette distance (hue x saturation
  + brightness histograms, ink dropped), ink share ratio (line weight; edge density misses it, a 5 px line has the same
  edge count as a 2 px one), each named hero's box palette. REVIEW only (LT-60 palette > 0.08, LT-61 ink outside
  x0.7..1.4, LT-62 hero > 0.15); whether it is the same face stays with the eye (LT-58) or CLIP (LT-43).
  Measured: the two finished eras clips drift 0.002-0.006 inside 10 s; school vs wild west scenes measure 0.09 and
  ink x2.6 (flagged). Test: synthetic cut (same drawing PASS; recoloured set, thicker ink, new shirt each flagged).
- Guard lesson (07:12): pod scripts that never send a status ping are STOPPED by a live guard at the boot deadline
  (default 25 min); the first eras pod died after 2 of 5 clips (~$0.3 lost). New pods get `boot_minutes` >= the job.
- 08:27 UTC ვანო's full video report (50 criteria + advice; copy in project files
  `lora_plan_2026-10-22/VIDEO_LORA_REPORT_vano_2026-10-24_ka.md`) -> `training/video_criteria.json` (VQ-01..50: 22 code,
  27 eye, 1 n/a) + LORA_TRAINING section 7 with the taken / not-taken table (DLoRAL, flow/LPIPS losses and two-stage
  training not taken, with reasons; lower video LR + warm-up, RS-LoRA at rank >= 64, "a frame of a video" captions and
  the animate-the-pair gate taken). Linked shots need no training: LTX-2.5 start + end keyframes + video conditioning.
  Eras clips' root causes written there (farm = my prompt; wildwest = length; ice_age = anchor bias on a crowd).
- 08:55 UTC ვანო: "find what caused the $1.3 loss and teach the system". Causes: (1) I read the REST pod record's
  `runtime: null` / `machine: {}` as "no machine"; the working eras pod showed the same, so it is no signal; a training pod
  that was running was stopped after 72 min (≈$1.3); (2) the same record never satisfies `ready()` (no IP, no ports) for
  script pods, so the guard killed the eras pod at its 25-min boot deadline (≈$0.3); (3) the pod scripts uploaded nothing
  before their first long stage. Fix in code (LT-17): `runpod.lint_pod_script` (an upload loop <= 300 s before the first
  heavy step; `preflight_create(script=...)` refuses otherwise), `hf_heartbeat` + `heartbeat_step` in the guard (a fresh
  HF upload = the answer that lifts the boot deadline; silence = an alert, never a stop). 5 tests, one on the very script
  that lost the money.

## 2026-10-24 — LT-17 follow-up: the heartbeat file must change

The scene LoRA pod's heartbeat (`stages.txt`) froze for the whole training stage, because an HF upload skips unchanged files;
the guard pushed a false "silent" alert while the pod trained normally. `lint_pod_script` now also requires the upload loop to
rewrite a heartbeat file every pass (`date > out/beat.txt; up`); test `test_a_pod_script_must_upload_its_log_before_its_first_heavy_step`.
Video LoRA v1 dataset: 83 of 150 cartoon clips kept after the cut, live-action, credits and graphics filters and an eye check
of every clip; motion-only captions written off the pod (no paid captioner).

## 2026-10-24 — LT-18: test videos have no upscale; one take, a new one only on a failed check

ვანო's rules for the 1-minute test film: no upscale in test videos (they measure logic), each shot made once and checked, a new
take only when the check fails; release resolution 2K. The test film is made in three variants: 24 fps, 12 fps ("on twos") and
a third with ~20 % less-animated shots (still + camera). Docs: project files lora_plan_2026-10-24/.

## 2026-10-24 — KP: how animated-shot prompts are written (SHOT_PROMPTS.md, `scripting/shot_prompt_lint.py`)

ვანო (15:35 Tbilisi): analyse the frame prompts of all iterations, single out my own mistakes, write rules and give them to the
scenario agents. Corpus: the IC, max-length and eras LTX prompts, the scene LoRA samples, the zero-shot next poses, the video
LoRA validation set, the running chain test. Findings: bare role words painted strangers (KP-01), the base model hands an action
to the figure already posed for it (KP-02), exit verbs emptied the farm shot (KP-03), no camera sentence (KP-04), a moving train
smeared the heroes (KP-05), over 10 s breaks (KP-06), framing words re-frame next poses (KP-07), and every LTX test ran with the
stock negative prompt that names our style ("cartoonish rendering", "exaggerated expressions"; KP-09). Most mistakes were mine
(table in the doc). The lint FAILs/REVIEWs these on the real prompts (test `tests/unit/test_shot_prompt_lint.py`); the
story-architect, edit-planner and the skill `shot-visuals` now write shots to KP. The lint also found two vague prompts in the running chain test
("the woman by the rock", "the cave man on the left"); both rewritten on HF before the pod read its code.


## 2026-10-24 — KP-15..KP-30: shot cards and composed prompts (`scripting/film_shots.py`, `film_shots/1`)

ვანო (15:50 Tbilisi): check the new prompt rules against how our photo models and local LoRAs read a prompt, which technical
terms help and which are missing; describe the frame, its drama, the spoken text, the tone and the sound so the picture, video
and audio prompts help the storytelling; keep the balance so shots are not boring or over-constrained; study his cartoons.
Done: an audit of KP-01..KP-14 per model (Qwen-Image-2512 + style LoRA, Qwen-Image-Edit-2511 + scene LoRA, LTX-2.5 with audio;
official guides and our tests), 120 cartoon shots labelled by hand plus the camera measure of 3312
(`docs/research/SHOT_GRAMMAR_FOOTAGE_2026-10-24.md`), the shot card schema `film_shots/1`, a composer that writes the
keyframe, next pose, cut and video prompts from one card, rules KP-15..KP-30 in code (tags, start-peak-settle with the
first frame at the start, faces as cues, quoted lines that fit the clip, at most two faces close, narrated shots silent,
no score music, no story names, no quality words, no "smooth motion", the change only, scene grammar), BP-100..BP-103
(hypotheses, REVIEW; the registry's id pattern now takes three digits), the worked example
`examples/film_shots/bus_in_the_ice_age.json` (0 FAIL, 0 REVIEW) and `tests/unit/test_film_shots.py`. Agents story-architect,
scene-writer, performance-director, edit-planner and the skill shot-visuals write their fields of the card. The narrator-and-
scene structure waits for the documentaries ვანო will send (16:05).


## 2026-10-24 — KP-31..KP-34: composition in every picture prompt (shot cards)

ვანო (18:53 Tbilisi, LoRA thread): every picture prompt must state its composition, the sizes of the bodies and the space.
Done: the shot card gains `blocking[].on` (what each person stands or sits on), `blocking[].height` (a quarter .. most of the
frame height; `height_pct` as a number for the words-vs-numbers test), `frame.relations[]` and `frame.lead_room`; the
composer writes them into keyframe and cut prompts (never into a next pose, which keeps the master's layout); KP-31..KP-34
FAIL when they are missing or vague ("by the boulder"); every composed prompt names its LoRA (`style` / `scene`, never the
style LoRA on Edit-2511) and `compose` writes one gate card per drawn first frame for the keyframe gate (PR #22). The worked
example passes (0 FAIL, 0 REVIEW); tests in `tests/unit/test_film_shots.py`.


## 2026-10-24 — Template D: the 15-minute historical docudrama (STORY_ENGINE, ST-17..ST-19)

ვანო (20:22 Tbilisi) brought back another AI's report on the ten structure variants of one 15-minute animated docudrama
(narrator plus talking characters). Done: its 16-segment timeline is template D in `docs/STORY_ENGINE.md` (three acts,
narrator and scene in turns, a question at every scene's end, modules for war / rivalry / invention), with one change:
its "subscribe" outro breaks BP-43, so the last 10 s point to the next video. `drama.template` (A-D, optional) is new in
the schema; on D, `scripting/story_lint.py` checks ST-17 (no narration block over BP-104's 90 s), ST-18 (the central scene
is the longest scene) and ST-19 (the narrator's share in BP-105's 25-45 %), all hypotheses, REVIEW. The summary and what
was not verified (its 65-84 % and effect-size figures): `docs/research/DOCUDRAMA_CONSTITUTION_2026-10-24.md`. Agent
story-architect picks D for history episodes. Test: `tests/unit/test_story_engine.py::test_template_d_docudrama_rules`.



## 2026-10-24 — Script engine v1 and the first episode on it (Napoleon vs Genghis Khan)

ვანო (20:56 Tbilisi): one full 15-minute episode prompt (Napoleon's army falls through time onto the steppe of Genghis
Khan), with zero improvisation: where a rule was missing, research it and write it first. Done: `docs/SCRIPT_ENGINE.md`
(the pipeline topic -> claim map -> template D -> shot cards -> composed prompts; ZI-01..ZI-06; the variants in use while
tests run; the writer's brief). New episode rules on the cards under `"engine": "script_engine/1"`: KP-35 shot rhythm,
KP-36 clip length and key poses, KP-37 animation tiers (hold / light / full; a line on a hold or light shot FAILs), KP-38
camera moves, KP-39 narration blocks and share on the cards, KP-40 the outro as a channel pointer (the creator's call:
worlds on the channel, worlds coming, subscribe so as not to miss them), ZI-02 a claim behind every number, ZI-03 a tier
on every shot. Numbers BP-106..BP-110 (the creator's cartoons measured: 11-17 shots a minute, still pictures on 5-10 % of
the time, which replaces the critic's 40 %; night tests: clips of at most 10 s), evidence in
`docs/research/SCRIPT_ENGINE_V1_2026-10-24.md`. The composer now writes tier, model, fps and LTX's 8k+1 frame count on
every video prompt, hero-sheet prompts for named heroes, and draws a cut's last frame from the cut itself; `film_shots
script` writes the readable script with claim ids. Template D's last segment is now the 15 s channel pointer. The
episode: `examples/napoleon_vs_genghis/` (204 shots, 15:00, narrator 45 %, 0 FAIL, 0 REVIEW; PROMPT_PACKAGE.md for review).
Tests in `tests/unit/test_film_shots.py`.


## 2026-10-24 — Picture test v2 findings in the composer (KP-32, KP-33)

The LoRA thread's 1-minute film picture test v2 (Qwen-Image-2512 + style LoRA, 2 seeds, words against numbers). Done: the
prompt never carries a size as a number (numbers were drawn as rulers and percentages in 6 of 10 pictures and sized the
figure no better), `height_pct` becomes the nearest word and stays for the gate; KP-33 FAILs a relation that puts "a" or "an"
before a cast member's noun ("a living woolly mammoth ... behind the bus" drew two mammoths in 4 of 4); a figure cut by the
frame edge is `blocking[].partial` ("the trunk"), written as such, counted by the gate card, without support or height.
The repeated-tag hypothesis (one figure drawn twice) is a variant to test in `docs/SCRIPT_ENGINE.md`, not a rule. Tests in
`tests/unit/test_film_shots.py`.


## 2026-10-24 — Script engine v2: the cold open, strategy shown in action, AI acting (KP-41..KP-43)

ვანო asked where the picture prompts are, whether the episode needs more action, and how to control AI acting (the
parley fails as "a podcast" if the faces fail); he forwarded another model's review to read. Checked against the cards
(`docs/research/SCRIPT_ENGINE_V2_2026-10-24.md`): the first clash came at 3:13, the yurt was 95 s in one place with nine
lines in a row, the camp raid was only smoke. Done: KP-41 teasers in the first 10 s cut from later shots (`teaser_of`,
`compose` writes `kind: reuse`, nothing drawn), KP-42 at most 90 s in one place before a cutaway, KP-43 at most four
lines in a row and an acting check plus a mouth-hiding fallback on every full-tier line (`qa`, `acting`, `fallback`);
BP-111..BP-113. `film_shots shotlist` writes the script with every prompt under its shot. The episode: three teasers,
cutaways in S04, S06, S08, S09, S13, S10 cross-cut with the camp, still 15:00 (214 shots, narrator 44.9 %, 0 FAIL,
0 REVIEW). Composer: "Only this figure is in the picture" (was "Only these 1 person"). Tests in
`tests/unit/test_film_shots.py`.


## 2026-10-24 — Conflicts between the script engine and older rules resolved (D-77)

ვანო: this thread stabilises the script-writing system (no paid runs); where the new approach conflicts with old rules,
the new one wins and the rules change. Reviewed docs, the registry, skills and agents
(`docs/research/SCRIPT_ENGINE_V2_2026-10-24.md` section 4). Changed: BP-40 scoped to still-picture episodes (animated
ones take BP-107's shot rate; ED-14 likewise), BP-43's "one next video" replaced by BP-106 under the engine, the
`dialogue-scenes` skill's 40-60 % narration and "a scene every 60-90 s" replaced by BP-105/BP-112/BP-113, the style
bible's "one place per scene" now allows cutaways, template D's hook runs 0:00-0:12 with teasers (rows 8, 10, 13 name the
cutaways and silent beats), D-55 kept for still-picture episodes only; `supersedes` fields on BP-105/106/107/112;
agents story-architect, scene-writer and edit-planner told the episode rules. No conflict: BP-70's four-line exchange
equals BP-113's cap; BP-31, BP-03, ED-14's listener reactions. Decision D-77.


## 2026-10-24 — Keyframe and sheet prompts in the style LoRA's training shape (LT-65, LY-09)

The LoRA thread found the style faded in composed keyframes: same pod, LoRA and seeds, the approved 31-word eras prompt
drew the look and the 337-word composed bus prompt a flat grey generic cartoon; every v5 caption ends with one style tail
the composer never sent. Done: `keyframe_prompt` and `sheet_prompts` write `wldnk style, <scene>, <tail>` in at most 90
words (`STYLE_TAIL`, `KEYFRAME_WORDS_MAX`; a card may set `style.tail`); each tag once, a gaze as a direction, figures
past the budget placed by their tag's head phrase; heights, supports, relations and free space stay in the gate card
(for EliGen boxes or a blockout) and in cut prompts; `film_shots check` runs `style_check` (missing tail FAIL, over 90
words REVIEW, PR #22's `qa/style_prompt.check` when present). The bus example's "flat grey daylight" and "empty white"
plain words replaced. Tests in `tests/unit/test_film_shots.py`.

## 2026-10-24 — LT-19: a pod's GPU check has a timeout; a bad host stops itself through the guard

ვანო (16:20 Tbilisi): find why the chain-test pod hung and fix it if it was avoidable. Cause: my launchers dropped the
`allowedCudaVersions` filter (for stock), so RunPod gave a driver-550 host (native CUDA 12.4, compat 13.0) to the CUDA 13
aitoolkit image; the pod's `python -c "...torch.cuda.get_device_name(0)"` printed "cuda ok" and never returned. The background
upload loop kept the heartbeat fresh, so the guard saw a live pod for 12 min (≈$0.6) until I read the log. The relaunch got a
driver-595 host (CUDA 13.2) and ran normally. Fixes: `lint_pod_script` refuses a CUDA call without `timeout`; a failed probe
writes BAD_HOST to the heartbeat and the guard stops that pod (`hf_text`, `heartbeat_step` -> "bad_host"); `create` refuses a
body without the CUDA filter unless `any_cuda=True`. Tests: `test_a_cuda_check_without_a_timeout_is_refused`,
`test_a_pod_that_reports_a_bad_host_is_stopped_by_its_guard`, `test_create_refuses_a_body_without_the_cuda_filter`.


## 2026-10-24 — KG: keyframe gate, cause log, a LoRA only on its own base

ვანო (18:53 Tbilisi): check every picture's logic, physics and video use before the scene LoRA takes it; redraw on a fail;
record what was right and wrong and whose fault (prompt, style LoRA, scene LoRA); fix only the weak part. Cause of today's
wrong-style pictures: the chain-test masters and the hero sheet were BFL night-run pictures, and the style LoRA was loaded into
Edit-2511 (a different base); the one wldnk master (ice age) kept its style through Edit + the scene LoRA alone. New
[KEYFRAME_GATE](KEYFRAME_GATE.md) (KG-01..KG-16, new docs_lint family KG) and `qa/keyframe_gate.py`: questions from the shot
card for the pod's VLM, verdict (hard FAIL / soft REVIEW), at most 3 tries, `blame` (base without LoRA + another seed), the
`qa_log.jsonl` summary (prompt rule first; a LoRA retraining candidate at 15 cases of one type), and `check_stack` (style LoRA
only on Qwen-Image-2512, scene LoRA only on Edit-2511). The approved 20-era sheet read by Claude: 1 logic error of 20 (underwater dome) and the ice-age
mammoth, which the prompt asked for as a rock painting; both prompts were ambiguous. Test: `tests/unit/test_keyframe_gate.py` (7).

## 2026-10-24 — LY: shot layout from real sizes and the camera

ვანო (19:34 Tbilisi): give exact sizes with ± in one prompt variant and relative proportions in the other, make sure the system
writing the numbers makes no mistakes, and look at drawing simple figures first and our style after. New
`scripting/layout.py` (LY-01..LY-08 in [KEYFRAME_GATE](KEYFRAME_GATE.md), docs_lint family LY): a table of real heights with
references, the shot size sets the lead's frame share, perspective places every other figure (height = f·H/z, horizon by
angle, `elev` for a hill), checks FAIL a figure outside the frame or hidden behind a nearer one, and one layout writes the
technical prompt (± 5 %), the relative prompt (ratios and metres in words), EliGen boxes and a grey blockout for a ControlNet.
On its first run it caught the scenario's mammoth 100 % hidden behind the bus. Test: `tests/unit/test_layout.py` (5).

## 2026-10-24 21:40 Tbilisi: film picture test v2, and three gate fixes (KG-01, KG-12, KG-17)

ვანო said "run everything" at 19:50. Test v2 drew 60 pictures of the 1-minute film on one pod for $1.94 (≈$0.7 of it was the
pod idle after the end: I checked too late). The results are in [KEYFRAME_GATE](KEYFRAME_GATE.md), "Film test v2". The gate
made errors in both directions:
- It missed a second mammoth: the total count was 5 of 6.
- It noticed drawn rulers in only 2 of 6 pictures.
- It failed a close-up for cut-off arms.

Fixes in `qa/keyframe_gate.py`, tested in `test_film_test_v2_cases`:
- KG-01 now also asks per card figure how many times it appears.
- KG-17 (hard) asks for measurement lines and numbers.
- KG-12 is skipped in MS and closer shots.

The prompt-text fixes (name a figure once, then a short name; no numbers in the text) belong to the shot prompts (PR #24)
and were sent there.


## 2026-10-24 22:30 Tbilisi: LT-63 newest code and rules, LT-64 the creator's approved rules

ვანო noticed that the pod fixes (LT-17, LT-19) sit only in PR #22 and asked whether the other threads' newest rules are
in use. They were not all in use. Test v2 composed its prompts at PR #24 08f2bf6, before that thread's b991562 (sizes in
words, no "a/an" before a cast noun, partial figures). The asset test writes its prompts by hand. LT-63 makes every run start
from the newest heads, take its prompts from the composer, and record its commits. LT-64 lists the rules he approved, which
apply in every next iteration.

## 2026-10-24 23:45 Tbilisi: why the style faded, and a stricter picture check

ვანო saw the film pictures lose the approved style and repeat the same girl. The negative-prompt run already held the cause.
On one pod, with one LoRA file and seeds 7 and 8, the approved eras prompt drew the approved look. The film's bus prompt drew
a flat, round, grey cartoon. The two prompts differ in shape:
- the eras prompt is 31 words, has caricature words and a fire;
- the bus prompt is 337 words, has no caricature word, says "flat grey daylight", and repeats every full tag up to 9 times.

All 164 training captions end with one style tail, and the composer never sent it. The LoRA is not broken; the prompts left
the shape it was trained on. New rules:
- LT-65 (`qa/style_prompt.py`): the tail, at most 90 words, no grey light.
- LY-09 (`layout.short`, `repeated_tags`): a full tag is said once.
- KG-18..KG-22 (`keyframe_gate`):
  - look-alike twins;
  - sheet marks such as glasses;
  - objects counted, so one bus is one bus;
  - absent things (a road in the ice age);
  - the 72B judge, one question per call;
  - my own filled table for every picture before the creator sees it.


Follow-up: PR #22's head (5049711, `qa/style_prompt.py`) merged into this branch; the composer now takes `STYLE_TAIL` and
the 90-word limit from it and `film_shots check` runs its `check` (washed-out light words REVIEW); the Napoleon cards' grey
and flat lights recoloured (0 FAIL, 0 REVIEW).
Follow-up 2: the keyframe words are built by levels (bare tag head -> with side -> full), raised in order light, lead,
sides, others in full, the rest of the place, relations, so a crowded shot (the 1-minute film's six figures came to 101
words) stays at 90 and keeps its light; the 1-minute film card recoloured ("flat grey daylight", "empty white") and its
"a living woolly mammoth" relations named by tag (0 FAIL, 0 REVIEW).

## 2026-10-25 03:30 Tbilisi: shots composed from reusable assets (AC-01..AC-15), LT-65 without the tail

ვანო's plan (02:19): the style LoRA draws only assets, code composes the shots (micro scenes and battles), assets are reused.
He asked to make the system ready before any generation, starting with the free part.

What was done:
- A free analysis of why the style faded (https://claude.ai/artifact/BCfwRAUtF34g9xcS1bjk6D). The v5 training samples drew
  the film's own heroes in the approved look from short story prompts without the tail. LT-65 now asks for that shape
  (at most 40 words, no layout words). The tail is flagged.
- `explainer_engine/compose/`:
  - `library` (records, mirrored views, the list of what must be drawn, cut-out check);
  - `frame` (perspective placement, horizon match, contact shadow, haze, depth order);
  - `crowd` (scatter by ground area, clone check);
  - `reuse` (same setup → crop, zoom limit 1.6x, teasers);
  - `style_score` (DINOv2 against his photos and a same-place control, REVIEW only).
- The cartoon footage was measured for the planner: shot median 3.2 s, ≈20 % return to an earlier setup, camera still in
  ≈2/3 of shots.
- The first CPU test with the composition test's assets. It composed a WS, a MWS, a reuse crop and a 90-figure crowd. Two
  real defects were caught: a plate with the wrong horizon for close shots (AC-05), and a cut-out carrying a block of snow
  (AC-15).

## 2026-10-25 03:50 Tbilisi: the script engine's picture prompts follow the new LT-65 (moment shape, 40 words, no tail)

- `film_shots.keyframe_prompt` is now `wldnk style, <the moment>`: the place's head, the lead with caricature body words
  (`style.body`, default `BODY_WORDS`) and the action at its peak, one reaction, the light, then others briefly while words
  remain. It stays within `style_prompt.MAX_WORDS` (40) and has no tail and no camera, size or position words. Sizes, sides,
  heights, supports and counts stay on the gate card for the composition of assets (docs/ASSET_COMPOSE.md).
- KP-16 under D-77: the composed first frame of the video keeps the start pose, and the style-LoRA moment shows the peak
  with a reaction, as the approved eras pictures did.
- Hero sheets use the same shape (`_sheet_text`, ≤40 words). `style_check` runs `qa/style_prompt.check` on every
  style-LoRA prompt.
- Napoleon vs Genghis (214 shots), the bus example and film_1min all pass with 0 FAIL / 0 REVIEW. Tests
  `test_keyframe_tells_the_moment_at_its_peak_with_a_reaction_and_no_layout` and
  `test_keyframes_and_sheets_keep_the_moment_shape_and_name_each_figure_once`.

## 2026-10-25 03:20 Tbilisi: episode look (AC-16..AC-19) and the prompt absolutes (LT-66)
- ვანო asked for an episode-level colour layer that keeps colours consistent between the episode's pictures when places
  and countries change, without changing the style LoRA's look, and for the list of prompting absolutes.
- `qa/style_prompt.py`: `ABSOLUTES` (A1..A10), `NEGATIVE`, `INFERENCE`; other media or art styles in a prompt now FAIL
  (LT-66). `compose/episode_look.py`: the look file measured from the approved key frame, a 10-word colour-and-light
  phrase added to every prompt (the prompt still passes the 40-word rule), colour drift as REVIEW, and a bounded grade
  (at most 0.35, originals kept). Tests: `tests/unit/test_episode_look.py` (absolutes frozen, clash, phrase, apply,
  drift and grade). Nothing paid; the drift threshold is calibrated on the first episode.

## 2026-10-25 16:50 Tbilisi: blind description check (KG-23..KG-27) and generated style pictures (LT-67, LT-68)
- ვანო asked for a precise written style description that every picture is checked against, and for a describer agent
  with fixed rules. The describer describes each picture without its prompt; the description is compared with the
  scene's logic; a "?" gets a second look. The prompt writer gets matching rules, so the loop stays consistent.
- `qa/blind_check.py`:
  - `STYLE_SPEC` gives six items read off the approved eras sheet.
  - `DESCRIBE_RULES` shows the describer the picture only.
  - `compare` checks the description against the gate card: counted things, absent things with synonyms, people,
    floating things, anatomy and style.
  - `second_look` asks one question per doubtful item.
  - `style_verdict` needs the DINOv2 score (at least 0.557 against the 20 eras cells) and every style item.
  - Tests: `tests/unit/test_blind_check.py`, including the 2.1 LoRA's second small bus and the flat-vector frames that
    passed on the score alone.
- `keyframe_gate.LORA_BASE` adds the Qwen-Image-2.1 style LoRA (`wldnk_qi21`, one model that draws and edits).
- LT-67: pictures generated for training are drawn with the eras formula. LT-68: a picture joins a style set only with
  both gates passed, and generated pictures make up at most 40 % of the set.
- 104 eras-formula prompts are ready for the 2512 + approved-LoRA generation (all pass `style_prompt.check`, 19-32 words).

## 2026-10-25 18:30 Tbilisi - the 104-picture gate run
- 104 pictures (2512 + approved LoRA, eras-formula prompts): 78 PASS, 12 FAIL, 14 REVIEW after both gates and a second look.
  Failures: extra person or object (8), smooth vector (3), an ambiguous prompt word ("the cook ducks" drew a duck-billed cook) (1).
- `blind_check.compare` was calibrated on them (KG-27): cast counting, scene-named floating effects, zero count = REVIEW.
  The auto half of KG-23 is content-biased (buses, sea are not on the eras sheet): 9 in-style pictures scored <0.557 -> REVIEW by eye.
- 2.1 LoRA "failure" cause (records): the test sampled with cfg 1.0 (training samples used 4) and VideoX-Fun `merge_lora`
  skipped all 32 `img_mlp.gate_up` layers (ai-toolkit stores the fused [gate_layer; proj]). Fix tested in `infer21b.py`.

## 2026-10-25 20:40 Tbilisi: style-only training and continuity cards (D-75, CT-01..CT-14, LT-69, LT-70)
- ვანო: the base models already know how shots join, so all training goes to the style. For continuity, test which prompts
  and references work best, with an agent whose output format rests on research.
- The research covers 22 sources (`docs/research/SHOT_CONTINUITY_2026-10-25.md`):
  - script supervisor sheets and the Hanna-Barbera Layout Notes (where/when on every BG, "Match to BG 19", hook-ups);
  - the 180° and 30° rules, the eyeline match and match on action;
  - Qwen, Gemini, FLUX and LTX docs (reference caps, refer by position, identical identity text);
  - the drift papers (draw fresh from the originals).
- `scripting/continuity.py` + `schemas/continuity_card.schema.json`:
  - checks the cards (CT-01..CT-12);
  - assembles each keyframe prompt (CT-13);
  - writes the questions for the finished picture (CT-14).
  - Example `examples/continuity/napoleon_tent.json`, test `tests/unit/test_continuity.py`.
- New agent `shot-continuity-writer`.
- `docs/SHOT_CONTINUITY.md` lists the five things the continuity test varies.
- LT-69: only the style LoRA is trained.
- LT-70: a generated picture becomes training data only with ვანო's 👍. The automatic gates only pre-sort; 13 of 70
  DINO-passed frames got his 👍, and v2 got 12 of 12 👎.

## 2026-10-25 21:05 Tbilisi: report money events at once (LT-71)
- Job 0195 (2.1 with the creator's 7 pictures as references) hung on picture 9. The pod billed ~45 min ($1.1) with no work, and the
  creator was told only "stuck". New rule LT-71: every money event and main-work result is reported at once with $, options and a
  recommendation; worker jobs get time limits near their expected length.

## 2026-10-25 21:10 Tbilisi: be critical (LT-72)
- ვანო: ideas, his own included, are verified and answered with arguments, never agreed by default. The 2.1 move and the scene
  LoRA were followed without a comparison against the approved option. LT-72.

## 2026-10-24 - Money per job, one pod manager on REST v2, pods stop themselves (D-74)
- Why: the RunPod loss strategy (creator's "Ok", 2026-10-24): about $4-5 lost from 10-22 to 10-24, the largest share
  finished pods idling in `tail -f /dev/null`; the pod-management code was split across unmerged PRs (#18 Guardian and
  watchdog on REST v2, #22 LT-17/LT-19 on REST v1) and REST v1 retires 2026-11-15.
- Done (this PR is the watchdog slice for main: the Guardian and the pod manager, nothing else from the systemic branch): one `explainer_engine/cloud/runpod.py` on REST v2 with PR #18's Guardian (`jobs`, `store`, `incidents`,
  `watchdog`, `.github/workflows/watchdog.yml`) and #22's heartbeat (LT-17) and bad-host check (LT-19); new: pods stop
  themselves when their job ends and at a dead-man timer (`self_stop_sh`, `dead_man_sh`, `script_cmd`, `boot_cmd`), the
  heartbeat's DONE/FAILED stops the pod from the guard, `lint_pod_script` refuses an idle tail without a self-stop, cards
  are picked by the job's estimated cost from the live catalog (`pick_gpus`, `runpod cards --vram GB --ref-hours H`,
  `create --vram/--ref-hours/--script/--script-url/--heartbeat`), and the preflight checks the job against its approved
  money and time. `config/spend_caps.json`: `max_price_per_hour` 3.0 is only the runaway ceiling; the caps the creator
  approved on 2026-10-23 stay; `bfl_usd`/`fal_usd` lines from #18.
- Tests: `tests/unit/test_runpod.py` uses fixed test ceilings (the live file no longer moves the asserted limits) and
  adds the self-stop, DONE stop, card-picking and per-job preflight cases. Not yet verified: that the key a pod gets can
  stop that pod (one cheap guarded pod, ≈$0.01, before the next paid run relies on it).
- Next: the RUNPOD_API_KEY repository secret and a merge to main make the watchdog run (scheduled workflows run only on
  the default branch).

## 2026-10-20 - Strict storytelling rules 1 and 2, and approval #1 recorded in code (D-61)

The creator's brief for the next episode ("titans from zero") set two general rules and asked that the order scenario ->
yes -> full script -> yes -> paid is a rule. Check before the change: next-video (0520c68) holds every branch and PR of
the repo (no open PR, no branch with commits next-video lacks; main differs only by merge commits); OR-15 / PV-45 already
bound the scenario, but approval #1 of the finished script was prose only (PRODUCTION_RULES gate 0, EPISODE_STANDARDS
`script_lock`), never recorded or checked before a paid step.

- Show, don't tell: SC-12 in `scripting/scene_lint.py` (PV-48 on `/3`), lexicons in [BP-87](SOURCED_RULES.md): a narrator
  line linking a hero to a trait, a rating or a biography line is a FAIL; ratings or stat cards on screen too (`sc_`
  pictures of `select_screen.py`). Heroes judging each other inside a scene stay allowed.
- Full immersion: SC-11, [BP-88](SOURCED_RULES.md): a meta frame ("this is a simulation", "as an AI", "in this
  hypothetical story", "none of this happened") is a FAIL in any line, Short or on-screen text; a hedge on the story
  ("we cannot know for sure") in narration. [BP-71](SOURCED_RULES.md)'s spoken honesty beat goes from 2 segments to 0;
  SC-08's pattern no longer fires on the plain verb "invented". The disclosure lives in the title and the description.
- Approval #1: `scripting/script_approval.py` (PV-53, [OR-17](ORCHESTRATION.md)): `episode.script_approval` (who, date,
  sha256 of every word said, Shorts included) is required on `/3` by paint preflight, the ElevenLabs hook and gate 0.9 of
  `production_gate`; tags, pictures and files may change after the yes, words may not. Schema field added.
- Skills dialogue-scenes, story-engine, narration-script; agents scene-writer, story-architect, script-critic,
  shorts-writer. `/1` and `/2` scripts keep their contract (Syndicate Wars unchanged).
- Tests: `tests/unit/test_storytelling_rules.py` (10). Nothing paid.

## 2026-10-20 - The critic's passing review comes with a one-page story in Georgian (BP-89, EG-23)

The creator: when the critic's review passes, it also writes the whole story on one page in Georgian and shows why it is a
well-told story and not a string of phrases. House rule [BP-89](SOURCED_RULES.md) (thresholds: one page in words, share of
Georgian letters, a "why" heading); `production/editorial_gate.py` EG-23 refuses an `editorial_review/2` of a `/3` script
without `story_page` (file next to the review), which also keeps gate 0.5 of `production_gate` closed. Agent script-critic
step 9, skill story-engine, STORY_ENGINE stage 7 row, SCRIPTING_SPEC 5.2. `/1` and `/2` scripts unchanged. Tests:
`tests/unit/test_story_page.py` (4), the integrated-review fixtures write a page. First page: Titans from Zero.

## 2026-10-20 - Titans from Zero: stage 4 (edit and sound plan) and a present-day New York era

`edit-planner` pass over S01..S16 of `examples/titans_from_zero/production_script.json` (words, tags and beats untouched;
`stage_guard editor`: 0 violations). Shots, motion, accents, bubbles, beds, sfx and `music` are planned; `graphics` stay empty
(the only claim rows are C-01..C-05, the story's numbers are invented, so a data visual would break invariant 5).
`world` is now a resolvable spec (the string `host` could not be resolved once shots exist): this needed the codex era
`modern_new_york` (14 eras; light keys for the courthouse, street, lot, motel, garage, warehouse, burnt garage and factory
office) in `explainer_engine/world/eras.json`; `tests/unit/test_world_architecture.py` pins 14 eras and one light key per beat.
Nothing painted, nothing paid. Open owners: sound files (WAVs are gitignored; nine ambience beds are not in the manifest),
cast speech/voice/face sheets and the variant collages (PV-46, PV-32, VB-09, PV-47).

## 2026-10-20 - A time counter in the corner (ED-15, PV-54)

- The creator took one note from an outside review of the titans script: a persistent day/year counter on screen. New
  top-level `counter` (editor-owned in `stage_guard`): segment + label; `timing.py` turns it into `counters` (first shot
  of the segment to the next label), `assemble.overlays` draws `graphics.counter` (a top-left chip, 0.4 s flip, hidden
  under a period card). `validate` PV-54 runs `graphics.check_counter`. Docs: ED-15 in EDITING, PV-54 in PRODUCTION_SCRIPT.
- titans_from_zero: DAY 1 (S01), WEEK 1 (S04), MONTH 6, MONTH 9, YEAR 1, YEAR 2, YEAR 3, YEAR 5 (S14). S05's period
  stays day1 for the story, the counter keeps WEEK 1 so the clock never runs backwards on screen.
- Voices re-cast without samples (creator: samples cost credits): from free `creative_list_voices` searches sorted by
  last year's usage, the most used voice that fits each hero's documented type (VC-02, no soundalikes).
- Tests: `tests/unit/test_graphics.py` (+3). Nothing paid.

## 2026-10-20 - Titans from Zero: episode rulebook v1 (provisional); paid_assets does not pass

`examples/titans_from_zero/episode_rules.json` (+ generated `episode_rules.md`) by the episode-standards-director: 16 rules,
19 risks for ten living people in an invented what-if. Sources re-read today: ElevenLabs use policy (09 Oct 2026 version,
V-51: s.4 now names "impersonating ... elected officials"), YouTube 14328491, 2801947, 2802268 (V-52), Hustler v. Falwell
(V-53), NY Civil Rights Law s.51 (V-54), Georgia's Law on Freedom of Speech and Expression (V-55); NO FAKES Act status and
California 3344 not verified (V-56). Baseline: B-10 re-dated, B-22..B-26 added. Result: provisional check 0 FAIL; the
`paid_assets` gate FAILs on RK-01 BLOCK (Trump's lines voiced by ElevenLabs, provider s.4) and three creator decisions
(RK-02 the six other real people's synthesised voices, RK-12 the invented buyer's name "Vance", RK-17 Lyria music outside
D-52). No stamp, nothing paid. Tests: the existing `tests/unit/test_episode_rules.py` baseline test covers the new rows.

## 2026-10-20 - Real people speak in bubbles (D-62, PV-55, BUBBLE-4/5)

The creator's call after RK-01/RK-02: real living people keep their names but are never voiced. A line with
`"voiced": false` is shown as speech bubbles (`production/silent.py`): one sentence per bubble, BP-84 words, BP-27 hold;
`production words` aligns the read against the voiced lines only and opens a quiet gap for each silent run, so words.json,
beats and shots keep one entry per token. PV-55 FAILs a voiced line of a real living person (`production_script/3`;
`traits.living: false` exempts the dead). The creator also asked for stable bubbles: BUBBLE-4 FAILs a bubble over any face
(every speaker's face, at the bubble's start and end crop), BUBBLE-5 FAILs a cut inside a bubble and the same text shown
twice. Titans: 149 lines silent, edit plan re-cut (no BUBBLE/CUT FAIL left), Shorts re-balanced (narrator lines break
silent runs). Tests: `tests/unit/test_silent_lines.py` (8). Nothing paid; the script needs the creator's re-approval.

## 2026-10-20 - Titans: style and six hero references picked; collage waivable per hero (OR-16)

The creator picked a synthesis of tiles 1 and 3 of `examples/titans_from_zero/pictures/style_collage_v1.jpg` and OK'd the
six named caricatures of `hero_caricatures_v1.jpg` (Nano Banana 2, $0.05; style collage Gemini 3 Pro, $0.13), recorded as
`cast.<id>.reference` and `look.environment`. For the five other characters he declined a separate collage ("not worth
drawing just to show"): `reference.first_picture: true` (schema anyOf) makes PV-47 a REVIEW until the hero's first scene
picture, OK'd on the contact sheet, is recorded as `picture`. Test: `tests/unit/test_reference_collage.py` (+1).

## 2026-10-20 - Titans: hero references in every paint prompt, quiet bubble gaps, face sheets

`compile.hero_refs`: a Gemini picture of a named hero now carries that hero's approved reference picture (and the episode's
world when no hero is drawn), so no face is painted from the prompt alone (invariant 6, OR-16). `silent.insert` opened the
bubble gaps in the measured middle of a pause with digital zeros; word times are 0.1-0.2 s off, so 14 gaps cut into sound
(ED-12). The gap now opens at `pause_pad.quiet_point` (the quietest 10 ms within `SEARCH` of the pause) on a 10 ms fade and
is filled with the read's room tone (BP-60). Titans: face sheets (VB-09) for the nine heroes with expression beats; Belfort's
14 expressions cut to 12 (curious -> surprised, confused -> doubtful in S12, S13, S15 and the Shorts SH07, SH09), Cardone
+determined, O'Leary and Cuban +deadpan. Tests: `test_silent_lines.py` (+1, the gap is room tone), `test_reference_collage.py` (+1).

## 2026-10-20 - Pictures and audio approved together (standing order 10); paint preflight honours REVIEW

The creator: after the script's yes, approve the pictures and the audio together and start them together, since the Gemini batch
waits for nothing. `docs/PRODUCTION_RULES.md` standing order 10 + feedback row, the orchestrator's phase 3 asks one paid-assets
question and runs phases 4 and 5 in parallel. `paint.preflight` refused on the editorial review's REVIEW items (EG-22 "for the
creator"), against D-60 (FAIL blocks, REVIEW is the creator's call; the ElevenLabs hook already filtered); it now blocks on FAIL
only. Titans B1: 67 of 106 pictures submitted on Nano Banana batch, the rest wait for the creator at the run's 80 % cap line.
Test: `test_storytelling_rules.py::test_paid_pictures_block_on_editorial_fail_not_review`.

## 2026-10-20 - Face sheets painted only as needed (VB-09)

The creator: "paint the faces only as the script needs them". `faces.needed(doc)` = the expressions the film's and the
Shorts' expression beats show, plus `neutral` (the resting face between beats); `to_paint` and the VB-09 "not painted yet"
REVIEW cover only those. A sheet's `set` still defines the hero's range (D-55 unchanged); the faces nobody uses yet are painted
by the episode that first shows them. Titans: 93 template close-ups -> 65 needed ($2.45 -> $1.71). Tests: `test_face_sheets.py` (+1, 3 updated).

## 2026-10-20 - Dialogue frame chosen: blurred scene + big face, blur 0.024

Four dialogue-frame variants on S12 "What's the catch?" (`conversation_variants_v1.jpg`: blurred backdrop + big face, sharp scene
+ comic face panel, two faces, painted scene only). The creator chose the first "with a slightly more blurred background":
`faces.BLUR` 0.014 -> 0.024 (`conversation_blur_v2.jpg` compares 0.014 / 0.024 / 0.034). Test: `test_face_sheets.py` (+1).

## 2026-10-20 - Standing order 11: the first two parts are shown before the rest is rendered

The creator: render the first two parts, join them, show him, and only then the rest; his notes become rules first.
`docs/PRODUCTION_RULES.md` standing order 11 + feedback row; the orchestrator's render step follows it.

## 2026-10-20 - ElevenLabs takes in the sound library (Titans audio)

The manifest schema records an ElevenLabs take: source kind `elevenlabs`, `cost_credits`, `generation_id`, and the BP-58
`kind` (one_shot / loop). Titans added two music loops (`eleven_music_v2_5`, 899.8 credits each), `battery_hiss__v1` (5) and
nine 30 s ambience loops (`amb_*__v1`, 99.99 each, estimated 330); ten Shorts narrator takes (2,352 credits). WAVs stay out of git.
Test: `test_sfx_library.py::test_elevenlabs_take_with_kind_and_credits_validates`.

## 2026-10-20 - A word the recogniser missed never lands before a bubble gap (D-62)

Titans S02 "Elon Musk. Musk signs.": Whisper heard one "Musk", the aligner interpolated the second just before the silent run's
insert point, so the shot "Musk signs" started 40 s early and every S02 cut after it failed CUT-1/RHYTHM-2. `silent.insert` now
gives every voiced word of a line that follows a gap in script order at least that gap's shift, and never a start before the
insert point. Test: `test_silent_lines.py::test_a_missed_word_after_the_gap_never_lands_before_it`.

## 2026-10-20 - Titans timing: three short shots get a breath (PV-24)

After the real read three cuts failed: S12 "You know how this kind of paper works." (2.25 s shot), S15 "Oh, the bench is still
there." (cut with no pause) and S16 "Luck decided which envelope paid." (2.36 s). Fix on the timing only, no new words:
`pause_after` 0.5 on the S12 and S15 lines, and the S16 line split at its full stop with a 0.5 s pause (visual beats divided).

## 2026-10-20 - The narrator tells the dialogue (D-63, PV-56)

The creator on the first titans preview: bubble-only dialogue is unread and boring, and a bubble glitched across a cut into a
face close-up. D-63: the narrator reports each exchange, the speaker's face is held in its mood at its end, then a slow move on;
real people stay unvoiced (D-62). PV-56 FAILs a segment with more than one silent line. The titans script fails it until its
dialogue scenes are rewritten (S02 first, as a two-minute re-render for the creator).
Test: `test_silent_lines.py::test_the_narrator_reports_the_exchange_bubbles_are_only_an_accent`.

## 2026-10-20 - Claude watches every render first: qa/frame_review (standing order 12)

The creator, on the first Titans preview: a bubble stayed across a cut into a face close-up, one speaker's words sat on another
hero's face, faces swapped every 1-2 s, a ring sat on empty wall: "why can't you watch and evaluate it yourself?".
`python -m explainer_engine.qa.frame_review <timed.json> <video> [--from --to] --out DIR` (free: ffmpeg + PIL) lists the moments
that matter (cuts +-0.15 s, bubble start/middle/end, beat starts, face-frame changes, dissolve midpoints), pulls each frame at
480 px, writes labelled contact sheets (FAIL tiles red, REVIEW amber) and `review.json`, and checks the timeline as the renderer
draws it (`faces.composite`'s lead and ease): FR-BUBBLE-CUT / FR-BUBBLE-FACE / FR-BUBBLE-WHO / FR-RING-FACE / FR-RING-HERO FAIL;
FR-FACE-RATE, FR-FACE-HOLD (BP-33), FR-FACE-GHOST, FR-TEXT-CUT, FR-RING-LOOK, FR-BUBBLE-TAIL REVIEW; BP-50 loudness of the range
through `qa/targets`. Exit 1 on FAIL. `docs/PRODUCTION_RULES.md` standing order 12 + feedback row; the orchestrator's render step.
Titans 0-123 s (`jobs/titans_from_zero/render/review/frame_review_v1`): 17 FAIL, all in S02's dialogue and its rings.
Test: `tests/unit/test_frame_review.py` (7).

## 2026-10-20 — Splice the read around new narrator passages (D-63)

`production/splice_read.py`: `points` aligns the old script's voiced lines on the existing read and lists, for each run of
bubble lines, the second where its gap opened (`silent.insert_points`, pass 1 of `silent.insert` split out); `pieces` cuts
`read.wav` there on 10 ms fades and interleaves the new narrator takes in script order, for `production words`. Only the
new passages are paid for. Titans: 19 runs. Test: `tests/unit/test_splice_read.py`.

## 2026-10-20 — Loudness lands on the target (BP-50)

Single-pass loudnorm left the titans preview at -16.5 LUFS (FAIL; input range 19.9 LU). `qa/targets.normalise_file` runs
the loudnorm, measures, then trims by the gap with a static gain and an oversampled (4x) limiter at the limiter ceiling,
up to two rounds; `production/assemble.py` uses it. The same mix now measures -14.8 LUFS / -1.5 dBTP (PASS / PASS).
Test: `test_a_wide_range_mix_is_trimmed_onto_the_long_target`.

## 2026-10-20 — One view plan per shot: close-ups, bubbles and the camera follow what is on screen (CC-01, CC-03, CC-06)

Static analysis of the Titans 0-123 s preview (`/mnt/project-files/explainer-engine/titans_from_zero/qa_loop/static_analysis.md`).
Causes: `faces.composite` put a close-up in and out of the frame whenever an expression beat came (24 face-frame runs in
61.7-123 s, median 1.7 s, 14 under BP-84's 2.0 s insert floor), eased the blurred backdrop 1.0 -> 1.3 -> 1.0 at each edge (the
"zoom reset"), and let it run up to the cut; bubbles were laid out once on the scene and drawn over whatever the composite
showed (a speaker's words on another hero's close-up, a tail into blur); `assemble.beats_for_shot` keyed face points by
`id()` of a copy, so no expression ever had its face point; a held punch, a wobble and the face lean did not return to rest
at a cut inside one picture (SH069 -> SH070); the face lean switched pivot in one frame.
Fix: `faces.views` (the shot's view plan: scene or one hero's close-up; never past the cut; a bubble never crosses a view
change and only shows on the scene or its speaker's own close-up; views under BP-84's insert floor absorbed), written by
timing into `shots[].views` (`faces.plan_shots`); the composite cuts in and out with its view; `assemble.shot_bubbles` lays
each bubble out on its view (on a close-up at the mouth measured on the keyed silhouette, `faces.mouth_and_head`);
`assemble.rest_weight` eases accents and the face lean to rest at a same-picture cut; the face lean glides between speakers;
`beats.fit_to_views` centres a ring that names a hero on his face point, keeps rings and labels off close-ups and ends a word
with its shot when it stays readable (BP-27). The preview's plan: 13 views in 61.7-123 s, none under 2.2 s, 0 of the frame
review's 17 FAIL causes left (`jobs/titans_from_zero/render/review/static/timed_planned.json`). Test: `tests/unit/test_view_plan.py`.

## 2026-10-20 — The research becomes rules: D-64 (the creator's call of 21:14, RX-01..RX-14)

The titans QA loop's research (`titans_from_zero/qa_loop/research_editing_rules.md`, A + B sources per rule; the C videos
could not be watched) and static analysis, settled by the creator's dated call ([D-64](DECISIONS_AND_OPEN_QUESTIONS.md),
recorded as `house` next to the sources in `standards/sourced_rules.json`). Changed: BP-84's bubble cap now reads BP-38's
word cap (a bubble is an accent; the PV-56 accent line too; a shipped `/1` gets a REVIEW); BP-31 allows a dissolve at every
change of place or time (timing marks `place_change` where the segment's scene place or time changes) and gains a length
band; BP-37's per-line minimum is 0 and the rule REVIEW; BP-36 and BP-40 count a visual beat only when it is tied to a
narration word (`/3`); BP-83's MO-06 is reported only (INFO). New: BP-90 / ST-14 (setup, exchange, conclusion, never
chained; the speaker-naming part REVIEW), BP-91 / PV-57 (the establishing cast), BP-92 (moves never reset:
`continuity.chain` pulls out by one step at most and rests at a turn; a run that returns to its start framing FAILs),
BP-93 / VB-12 (a beat needs a word), BP-94 (the held mood after an exchange, a hypothesis). Skills editing-style,
visual-beats, dialogue-scenes, video-editing-architect and agents beat-writer, edit-planner, scene-writer, script-critic
link the BP ids. Tests: `tests/unit/test_d64_editing_rules.py`; updated to the new sourced values:
`test_rule_consistency_motion.py` (BP-83 without `alive_share_min`, the bubble cap from BP-38, the BUBBLE-1/2 test at 4
words), `test_silent_lines.py` (the 15-word accent now FAILs, its 4-word key phrase passes), `test_story_engine.py` (MO-06
INFO). On the titans script: 6 new FAIL (BUBBLE-1 on a Short bubble, PV-56 on S12's 14-word bubble, PV-57 on S03, S11,
S14, S16) and VB-12 REVIEWs on the beats of hero lines; the script is not changed here.

## 2026-10-20 — The QA loop: review after every two rendered chunks, data + pixels, classed for a fix (standing order 12)

`qa/frame_review.py` now follows the renderer: a shot's `views` (the view plan `production/faces.views` writes through timing)
decide which face fills each frame (`faces.view_at` / `faces.face_in_view`); FR-FACE-GHOST and the own-close-up FR-BUBBLE-WHO
REVIEW no longer apply to a planned shot; an old timed file keeps the old eased mirror. On the Titans preview's own timing:
17 FAIL (as frame_review_v1); on `timed_planned.json`: 0 FAIL. `--pixels` adds `qa/pixels.py`, free (PySceneDetect, OpenCV
ORB + YuNet, ImageHash, ffmpeg freezedetect / blackdetect): PX-CUT-EXTRA and PX-FROZEN FAIL (objective: a cut the plan does not
have, a still picture while the plan moves it), PX-CUT-MISSING, PX-CAM-JUMP (RX-11 (a)), PX-JUMP-CUT (BP-30's tolerance, RX-11
(b)), PX-BLACK, PX-BUBBLE-FACE REVIEW; every invented number sits in one HYPOTHESIS block. `qa/face_points.py` measures the
heroes' faces on the painted pictures (YuNet; who is who by OpenCV SFace against each hero's face sheet, else left-to-right
order) and writes `face_points.json`; FP-OFF REVIEW past 0.08 of the width (hypothesis); `--apply` rewrites only the matches
SFace named. On titans (report only, script unchanged): 143 declared points in 75 pictures, 113 matched to a painted face (95
named by SFace), 30 without a face (backs in over-the-shoulder shots, or missed), **70 more than 0.08 of the width off, 59 of
them confidently** (`jobs/titans_from_zero/render/review/face_points/`); s02_signing declares O'Leary left of Musk, he is drawn
in the middle. `qa/loop.py` (`python -m explainer_engine.qa.loop <script> --read DIR --out DIR --chunks A:B`) times, assembles
the chunk pair, joins it with its mix, runs the frame review with pixels and the face points, classes each finding systemic
(same rule on 2+ shots, range-wide, or pixels against clean plan data) or script with its owner file, counts iterations and
stops after 5 on one finding; it edits nothing. On the old chunks 0-1 (0-123.3 s): the 17 data FAIL of v1 (all systemic), and
the pixel checks found **no** pixel defect: all 18 planned cuts seen, 2 extra cuts both planned (the SH004 punch, a face-frame
change in SH015), 9 still stretches all at eased move ends the plan holds, no camera jump beyond the planned punches, no
same-picture jump cut, no bubble over a face (16 of 18 bubbles located). Limit: frames on a close-up are not measured for
camera jumps, so the old close-up backdrop zoom (CC-06 cause 1) is seen only by the data checks. Paid allowance (the creator):
`config/spend_caps.json` `allowances.qa_loop` = 2,000 ElevenLabs credits per run for re-reads of lines the loop changed,
enforced by `core/ledger.Run.reserve_allowance` (refuses above it, and the run's own cap with its 80 % stop still applies).
Tests: `tests/unit/test_pixels.py`, `test_qa_loop.py`, `test_face_points.py`, and new cases in `test_frame_review.py`,
`test_ledger.py`.

## 2026-10-20 — Narrated exchanges count, a scene change breathes: D-65 (the creator, 21:14, confirmed 21:17)

From the long storytelling research (`titans_from_zero/qa_loop/long_research_storytelling.md`, "Contradictions found",
NR-01..NR-12). BP-70 (SC-05) is met by an unbroken run of hero lines as before, or by narrator lines that report at least as
many turns from as many named present speakers (`story_lint.reported_turns`: a name or he/she with a reporting verb of
BP-70's `speech_verbs`). BP-10 (N-15) exempts the last narration line of a segment before a change of place or time: a breath
up to `boundary_breath_max_s`, REVIEW above (NR-07: the naming is sourced, the seconds a hypothesis). New REVIEW checks in
`scripting/story_lint.py`: ST-15 the speaker before his words (BP-95, NR-02) and ST-16 at most two reported speakers a line
(BP-96, NR-04, a hypothesis). Skills dialogue-scenes, narration-script and agents performance-director, scene-writer,
script-critic link the ids. Test: `tests/unit/test_d65_reported_exchange.py`.

## 2026-10-20 — Titans v2 narration; splice points take joined takes

The narrator passages follow the long research (speaker first, at most 2 speakers an exchange, every exchange ends on a
decision; `/mnt/project-files/explainer-engine/titans_from_zero/qa_loop/long_research_storytelling.md`), 3,794 new
characters. A new line written after a former run is read right after that run's take: `splice_read pieces` takes
`a.wav+b.wav` (`splice_read.join`, 0.6 s apart). The QA loop removed shots that broke BP-92 / CUT-1 / RHYTHM-2.
Test: `test_two_takes_at_one_point_are_read_back_to_back`.

## 2026-10-20 — The face lean glides (QA loop, PX-CUT-EXTRA)

The loop's pixel check found two cuts the plan does not have (titans 99.8 s and 125.9 s): an expression beat leaned the
crop 10 % plus a 4 % pop toward the face in a quarter second, which reads as a jump (CC-06). `beats.FACE_*`: 6 %, no pop,
over 1.2 s. Test: `test_the_face_lean_never_jumps_like_a_cut`.

## 2026-10-20 — A renderer fix redraws the chunks

`assemble.plan_stamp` now carries `render_code()`, a hash of the modules that draw a frame; before, a code fix kept the
chunks drawn by the old code (the loop's third pass re-reviewed the same jump). Test: `test_a_renderer_change_redraws_the_chunks`.

## 2026-10-21 — Prop rings and labels land on what the picture shows (CC-03)

The beat-writer writes a ring's or label's `pos` without seeing the picture; on titans most rings and labels whose phrase names
no hero were template guesses ([0.5, 0.72]) on empty wall or floor. `qa/prop_points.py` (free, local, CPU): OWLv2
(`google/owlv2-base-patch16-ensemble`, Apache-2.0, `transformers` + CPU `torch`) looks for each prop beat's phrase in the
picture its timed shot shows (a verb phrase first as its thing: "reads the screen" -> "screen"); a find at `SCORE_MIN` (0.23,
hypothesis, tuned by eye on the titans sheets) moves `pos` to the box centre, a pos already in a find stays, a label naming the
place the whole picture shows stays, a ring found nowhere (or only as the whole picture) is dropped (RX-12, BP-93: a ring on
nothing is worse than no ring). Writes `prop_points.json` and contact sheets (old pos -> found box); `--apply` rewrites the
script with 2-space JSON. `check` gives PB-OFF / PB-NONE REVIEW; `qa/loop.py` runs it beside the face points and classes it as
the script's. Without the model the tool skips and says so. `beats.fit_to_views` now snaps a label naming a hero (in its phrase
or only its tag) to his face point as rings snap (the S02 label "KEVIN O'LEARY" pointed at an empty wall; it now sits on him
in s02_wide). On titans: 82 rings and labels, 25 name a hero, 5 are not drawn (close-ups), 52 measured: 13 kept, 19 moved,
20 dropped (`jobs/titans_from_zero/render/review/prop_points/`). Validate after `--apply`: still 8 FAIL (PV-45, PV-47, known),
one new REVIEW (VB-05: four symbol beats in a row in S09 once its labels went). Tests: `tests/unit/test_prop_points.py`
(fake detector), `test_a_label_naming_a_hero_points_at_his_face_point`.

## 2026-10-21 — Told conversations keep bubbles; word slams; the COURTHOUSE tag holds still (D-66)

The creator's notes on sample v2. (1) The S01 label "COURTHOUSE" sat at x 0.5 and `beats.draw` picked its side from the
camera-moved point, so the tag flipped left and right every frame; the side now comes from the picture spot. Test:
`test_a_label_at_the_centre_keeps_its_side_while_the_camera_drifts`. (2) A told turn shows its key phrase in a bubble over the
speaker (shot `bubbles[].reported`, schema field added; 49 on titans, each at most four words, the speaker in the shot's
picture). Tests: `tests/unit/test_reported_bubbles.py`. (3) Word slams: `slam_text` dims and softens the picture behind the word
(BP-97, house, the creator's call), PV-58 keeps them to one a scene, three words and first tellings; titans gets PAPERWORK
(S01, with a 0.8 s pause after its line) and FOREVER (S02). Tests: `tests/unit/test_word_slam.py`. Research for the next
editing steps (dialogue, text and graphics, multi-variant editing):
`/mnt/project-files/explainer-engine/titans_from_zero/qa_loop/research_edit_{dialogue,text_graphics,variants}.md`.
Loop pass 1 on parts 1-2: 0 FAIL; the slams were cut by the next shot after ~0.8 s and seven bubbles near a shot end were
cut under BP-27's hold (BUBBLE-2). The slam lines now carry a 1.0 s `pause_after` (S02's line split after "Forever." so
the pause lands there) and the seven bubbles start on an earlier narration word. Note: `words` on the whole spliced read
padded +73 s against +26 s per piece (one long transcription measures shorter gaps, so pause_pad widens more): run `words`
on the pieces in order.
Loop pass 2: O'Leary's bubble (SH015) landed by Belfort's face and read as Belfort's line. `bubbles.layout` now prefers a
spot nearer its speaker than any other face and sweeps a finer grid (also below the face) after the old candidates. Test:
`test_a_bubble_sits_nearer_its_speaker_than_the_hero_beside_him`. The pixel check counted the slam's dim and blur as a
92 px camera step; a `slam_text` hold is now a planned change (`pixels.planned` pops). Test:
`test_a_word_slam_is_planned_so_its_dim_and_blur_are_no_camera_jump`.

## 2026-10-21 — Drawn props from the text: line-icon stickers

The creator on sample v3: the telling is fine, the picture needs drawn things that follow from the words (not new photos;
not only rings and arrows). `explainer_engine/design/icons.py` reads 50 vendored Tabler line icons (`assets/icons/tabler`,
MIT, licence kept) and draws each as a paper sticker in the house ink; a prop beat with `asset: "icon:a+b+c"` shows them
in a row, each drawn on in turn as the narrator names it, with an optional word caption (`beats.draw`; the beat holds
until the row is complete, `icon_hold`); a missing icon is a VB-06 FAIL. Titans S01-S03 get 14 of them (ten men, the
towers, the clerk's stamp, no dollar, the brain, five years, forty bucks, price tags, a piece of every future, the
envelope, the signature, the bankruptcy gavel, the last line, the loan and the dead card); numbers are written as words
(VB-04). Tests: `tests/unit/test_icons.py`.
Loop pass on the icons (parts 1-2): 0 FAIL. Moving the "Ten men" beat off "none" left 5.3 s without a change in the first
30 s (RHYTHM-3), so the cross on "none" is back after the sticker. The sheets showed FORTY BUCKS and the gavel riding into
the next scene: a drawn prop now ends with its shot, like a label (`beats.resolve`). Test:
`test_a_drawn_prop_ends_with_its_shot_and_a_symbol_may_cross_the_cut`.

## 2026-10-21 — One narrator for every voice, an intro card and four chapter recaps (D-68)

The creator on sample v4 (08:59): the direction is right, more drama; every voice must be the one narrator; the told
dialogue re-recorded in that voice, performed "the way he would say it"; the video opens on a dark card with the question;
a short recap after each chapter with signs and text; and meaningful signs where they were missing. Research (10 rules,
sources): `/mnt/project-files/explainer-engine/titans_from_zero/qa_loop/research_narrated_dialogue.md`, summarised in the
`narration-script` skill. Titans: 24 told lines rewritten as short performed quotes with the speaker named first, S12's
voiced lines (Vance, Belfort) become the narrator's, no line keeps a `speaker`; `design/cards.py` draws the intro card
(the ten heads cut from the approved `p_<hero>` references round the YuNet face) and four recap boards (week one, month
nine, year two, year three), each rung row by row as the narrator names it; schema `cards` and `lines[].card`; 56 more
drawn props across S04-S16. Validate: 0 FAIL. Tests: `tests/unit/test_story_cards.py`.

**2026-10-21: titans re-recorded with one narrator, full render.** 22 Brad takes (eleven_v4, one generation each, 6,625
of the creator's 7,000 credits) spliced into the old read (`jobs/.../read_v3/build.py`; S15's roll call re-read: the old
take named five of the eight). Two systemic fixes found on the full render: `audio/seams.duration` now measures an MP3 by
its decoded samples (ffprobe's container length counts the encoder padding, and 22 takes drifted the word timings 0.7 s
late by the end; `tests/unit/test_seams.py`); `qa/pixels.planned` counts every view change of a shot's view plan as a
planned cut (wide -> face close-up read as PX-CUT-EXTRA on six shots; `tests/unit/test_pixels.py`). Told-turn bubbles
re-anchored on the performed quotes and, where they restate one, carry its own words (BP-84 four words). Editorial
review rounds 12-14 (one FAIL fixed: the first recap gave away O'Leary's envelopes), ER-03/RK-20 rewritten for D-68 on
the creator's card (12:05).

## 2026-10-21 - Titans final_qa: provider terms read, licences verified, C-01/C-05 upgraded

The episode-standards-director read the current terms first-hand and recorded them (policy baseline B-27..B-29,
MARKET_RESEARCH V-58..V-60): Gemini API Additional Terms (Google won't claim ownership of generated content; no clause on
monetisation, music or preview models), ElevenLabs Terms of Service and ElevenCreative Exhibit 4 (sound effects in video on a
paid plan, never standalone or as a library), ElevenLabs Music Terms (Creator: online commercial use except film, TV, radio
and Studio Games). Titans rulebook v3: RK-15 and RK-18 licences verified (PASS); RK-17 corrected (the two music tracks in the
mix are ElevenLabs Music takes made 2026-10-20, not Lyria), licence verified, still REVIEW for Content ID with the creator's
2026-10-17 decision. Claim map C-01 (Kim Kiyosaki's own interviews, Honolulu Star-Bulletin 2000) and C-05 (Bloomberg via
Fortune 2018) upgraded with narrowed wording; the script is unchanged. Description: sources updated, "our own drawings"
corrected to "made with AI image tools". final_qa stamped (0 FAIL). No code changed, so no new test; docs_lint clean.

## 2026-10-21 — thumbnail draft tier

- `publish thumbnail --tier draft|standard|premium`: the creator asked for a cheap try before the premium thumbnail. A
  non-premium try is written as `thumbnail_<tier>.jpg` beside the final file and never replaces it; the tier is logged.
  Test: `tests/unit/test_youtube_publish.py::test_a_draft_thumbnail_is_cheap_and_never_replaces_the_final`.
- Titans `publish.json` got its `thumbnail` block (Trump, Musk, Zuckerberg broke on black, "SKILL OR LUCK?"). The draft
  was not painted: Gemini answered 429 RESOURCE_EXHAUSTED (prepaid credits depleted).

## 2026-10-21 — Shorts cut from the finished long video

- The creator dropped the ten scripted Shorts (their old reads lack the dialogue after D-68) and asked for five Shorts cut
  from the long video's best moments: the video's own opening, one moment, a shared outro line that points to the full
  video and leads back into the opening question, so the Short loops; 15 % faster; no new read besides that one line.
- `production/clip_shorts.py` (plan.json -> 1080x1920: blurred fill, the 16:9 frame with a 6 % side crop, title band,
  word captions, "full video" label; the last frame is the first). Test: `tests/unit/test_clip_shorts.py`.
- `publish/plan.py`: `"shorts_from": "publish"` stages the Shorts listed in publish.json instead of the script's.
  Test: `test_youtube_publish.py::test_shorts_cut_from_the_long_video_come_from_publish_json`.

## 2026-10-20 — Library first: reusable assets looked up before any new generation (D-76, OR-18)
- The creator's rule (2026-10-20): a local library of background music and reusable objects; new is generated only when
  nothing there fits; what this session's episodes created is kept.
- Built: `imagegen/picture_library.py` + `assets/pictures/library/manifest.json` + `schemas/picture_manifest.schema.json`
  (props, backgrounds, textures, character art, thumbnail parts; tags, source, prompt, cost, licence, the creator's look);
  `audio/register.py` (connector MP3/stereo → the sound library's mono WAV, source `elevenlabs`, loop/one-shot);
  `assets_reuse.py` (search both libraries + record the search in the episode's `asset_reuse.json`).
- Enforced: `standards/hook.py` refuses a paid ElevenLabs music/SFX call without a recorded search (OR-18); `paint plan`
  lists a prompt's picture-library matches on the plan and `imagegen/plan.py` reports them as PP-08 (REVIEW).
- Docs: D-76 (decision log), OR-18 (ORCHESTRATION), PP-08 (PRODUCTION_SCRIPT), AUDIO_SYSTEM and ASSET_SYSTEM library
  sections, PRODUCTION_RULES standing order 5, CLAUDE.md layout. Media backup home: HF `tmr-artifacts/library/`.
- Tests: `test_assets_reuse.py`, `test_picture_library.py`, `test_audio_register.py`; the hook test now records a
  search before reaching the rulebook gate. Full suite green locally.
- Next: the titans thread registers its generated music/ambience with `audio/register.py` when its paid run finishes.

## 2026-10-21 — The two-part sample gate (D-67, OR-19; branch `claude/project-thread-i9ftf6`)

- The creator (2026-10-21): after the script, stop generating the whole video's audio and pictures; make the first two
  parts, he watches, corrects, and only then is the rest generated. It stages the 2026-10-20 combined images-and-audio
  approval (one estimate, one provider choice stay) into sample first, rest on his recorded word.
- New `explainer_engine/production/sample.py`: the sample scope (first two segments, widenable in `sample_approval.json`),
  the sample's pictures and in-scope reads, and the approval record bound to the script's sha256 (`status` / `approve` CLI).
- Enforced in code: `paint.preflight` refuses a plan with pictures outside the sample before the approval (PP-09;
  `paint plan --sample` keeps a plan inside it; `reusable` plans and face sheets stay allowed), the ElevenLabs hook
  refuses a paid read whose text is not inside the sample segments (Shorts included), and `production_gate` shows
  gate 6.5 between the pictures and the render.
- Docs: PRODUCTION_RULES standing order 10 + gate 6.5 + feedback-log row, ORCHESTRATION OR-19, PRODUCTION_SCRIPT PP-09,
  CLAUDE.md pipeline line, the orchestrator agent and the elevenlabs-voice skill; decision
  [D-67](DECISIONS_AND_OPEN_QUESTIONS.md) (decision ids 61-66 are claimed by the open PR #14 / #15 branches).
- Tests: `tests/unit/test_sample_gate.py` (9: scope, shared pictures, in/out-of-scope reads, PP-09, sha binding,
  hook wiring, gate row and CLI, `paint plan --sample`). Nothing paid; no renders claimed.

## 2026-10-22 - Scene continuity of the painted pictures (D-69)

The titans episode showed five men on a bench of ten, then two other men in another room while the narration told one
conversation. Traced in the code: `compile.jobs` gave every Gemini picture only the style references and `compose` wrote
each prompt from its own subject; nothing carried the room, the seats or the roster from one picture to the next, and
nothing compared a painted picture with them. Fixed inside the existing flow (same provider, model, size and paint gate):

- Schema: optional segment `staging` (location, time, layout, fixed, roster, positions, master, scene_id, continues),
  picture `framing` / `visible` / `partial` / `change` / `cut_away`, `look.continuity: auto`. Scripts without them compile
  byte-for-byte as before (pinned by a test).
- `production/staging.py`: scene ids (only a new place or time starts a scene), shot kinds (master, continue, action,
  reframe, insert, cut_away, montage), references in priority order (master frame, previous shot for an edit, the visible
  heroes' approved faces, style), the prompt's continuity block (KEEP UNCHANGED / THIS SHOT / MAY CHANGE, one single frame),
  the script lint CS-01..CS-07 (in `validate`), the paint order and review gate CS-09, the review questions and verdicts
  CS-10/CS-11 (per framing: a close-up is never failed for the people outside it), bounded repaints CS-12 (2 corrections,
  then the creator), a free pixel hint for split screens.
- `paint`: `plan --masters`; `plan --run` carries each rejected picture's correction (part of the item hash, so a repaint
  needs a new approval); references trimmed to the model's slots (`gemini.REF_LIMITS`, Google's page read 2026-10-22: Nano
  Banana 2.1 keeps 4 faces and 10 objects) and named (CS-08); `run` paints masters before the shots that take them and
  holds a shot until its master PASSed. `GeminiClient.judge` takes extra images (the master), each priced.
- Review: Claude's look is the default and free (`staging request` -> `continuity_review.json` -> `staging apply`); the
  Gemini vision call (`staging judge`) needs the creator's `--yes` and a `--max-usd`.
- Rules CS-01..CS-12 in [PRODUCTION_SCRIPT](PRODUCTION_SCRIPT.md), decision [D-69](DECISIONS_AND_OPEN_QUESTIONS.md); the
  skill `shot-visuals` and the agent `edit-planner` write `staging`; the stage guard gives `staging` to the editor.
- Read on the titans script with `look.continuity: auto` (nothing painted): CS-02/CS-03 find the scenes whose master leaves
  people out or whose pictures draw people outside the room (SC09, SC11, SC13-SC15), CS-05 the "ten men" bench with five named.
- Tests: `tests/unit/test_scene_continuity.py` (27, mocked provider). Nothing paid.

## 2026-10-22 - Stage A of the master brief: repo audit and tooling research (D-70)

The creator's master brief (2026-10-22, thread "წარმოების არქიტექტურა და ვიზუალი") asks for a model- and provider-agnostic
production system with one visual world, an Infrastructure Guardian and continuous QA, in stages A-H. Stage A done, nothing
paid:

- Repo audit ([research/REPO_AUDIT_2026-10-22](research/REPO_AUDIT_2026-10-22.md)): what exists and is tested (pod manager,
  ledger, caps, paint plans, face sheets, chunked assembler, deterministic QA), what exists untested or unused (`core/store`,
  `core/jobs`), what is documented only (asset record, licence register, style distance, world schema, Remotion, `paint
  --estimate`) and the Guardian gaps: the guard dies with the sandbox and `check()` then treats a live pod as fine, no durable
  copy of pod outputs in this repo, no state history or incident log, Gemini hard-wired behind a provider table, a cache key
  that differs between sync and batch, a latent `end_pod` NameError, three unreconciled balance drops.
- Tooling research with dated sources ([TOOLING_RESEARCH](TOOLING_RESEARCH.md) + three appendices): RunPod REST v1 retires
  2026-11-15 (`cloud/runpod.py` uses it); Veo preview, Sora, Hume, PlayHT and OpenAI TTS are gone or ending; FLUX 3 Image
  Klein ($0.009 per image, 10 refs, open weights), Seedream 4.5 and Qwen-Image-Edit-2511 are the picture pilot candidates,
  Illustrious/Animagine the anime anchor; stills + 2.5D parallax stay the motion default, Wan 2.6 / Kling 3.0 only for hero
  shots; ElevenLabs stays, with `/with-timestamps` replacing Scribe on the narration track; hosted per-output APIs beat pods
  for bursts; Cloudflare Worker cron + R2 (free) for a watchdog that outlives the session; GitHub cron only as backup.
- Plan ([ARCHITECTURE_PLAN_2026-10-22](ARCHITECTURE_PLAN_2026-10-22.md)) and decision [D-70](DECISIONS_AND_OPEN_QUESTIONS.md)
  (approval gate). Stage B (Guardian: REST v2 port, job record with history and heartbeat, durable copy before any stop,
  incident log, external watchdog, phone status and kill-switch, 15 mocked recovery scenarios) is next and needs no paid call.
- Four questions for the creator are in the plan's section 4 (the pilot and its ceiling, the Cloudflare/Modal accounts, the
  motion default, characters between episodes). Tests 603 collected, `test_runpod.py` 27 passed; docs_lint 0.

## 2026-10-22 - Stage B, item 1: the pod manager speaks RunPod REST v2

RunPod retires REST v1 on 2026-11-15; `explainer_engine/cloud/runpod.py` used it. Ported to v2 (`api.runpod.io/v2`, facts in
[TOOL_STRATEGY](TOOL_STRATEGY.md) "Money control for RunPod"), nothing paid, no pod touched:

- `norm()` flattens a v2 pod (`status`, `cost`, `disk`, `mounts.persistent.size`, `runtime.ports`/`gpus`) into the record
  the module and the session files already used, so the guard, the money clock, `check`, `sweep` and `settle` keep their logic.
- `create()` tries the pool's cards one `gpu.id` per POST (v2 has no type list) and moves on only after a clear refusal;
  a lost answer is still never followed by a second POST. A pod born `PROVISIONING` reports `cost` 0: the session's price
  falls back to the card ceiling until the pod reports its price, so the money clock never runs on $0/h.
- `stop`/`start` use `POST /pods/{id}/action` (GraphQL fallback kept), `DELETE` accepts 204, `pods()` reads every page,
  `billing()` sums `records[].totalAmount` (v2 has no billed seconds: the ledger item records `billed_buckets`), new
  `logs()` reads the server-sent events (`runpod logs <pod>`); `status` shows uptime and GPU utilisation.
- `ERROR` is a state now: the guard stops such a pod, `check` and `sweep` list its disk like a stopped one.
- `end_pod` no longer has the latent `NameError` when every stop attempt fails: it records `close_status` UNSTOPPED and pushes
  "GUARD GAVE UP".
- `cloud/hooks.py` also refuses raw v2 pod starts (`POST /v2/pods`, `action` start/restart, the Python SDK's `create_pod`).
- Tests: `tests/unit/test_runpod.py` rewritten against a v2-shaped fake (36 tests: pagination, next card after a refusal,
  v2 body, ceiling price while PROVISIONING, ERROR handling, SSE logs, the UNSTOPPED path, v2 hook bypasses).

## 2026-10-22 - Stage B, items 2-8: the Infrastructure Guardian (no paid call)

Prompted twice: the master brief (stage B) and the creator's report at 09:13 that the RunPod balance fell from ~$8 to $0.95
while every thread said nothing paid was running (a separate thread audits the account). What now exists, all against a fake
RunPod, nothing spent: see [TOOL_STRATEGY](TOOL_STRATEGY.md) "The Guardian" for the design.

- `cloud/jobs.py`: the job record (state.json + events.jsonl + heartbeat.json), the brief's fifteen states with legal
  transitions, `observe` (pod status + conductor line -> job state; a heartbeat only on progress), `stall` (per-state limits
  from the measured incidents, or the stage's own budget), outputs with sha256 and `safe_to_release`, "same inputs, finished:
  not run again". `create` writes the record (`--job <slug>`), the guard follows it, `end_pod` closes it.
- `cloud/store.py` (from TMR, provenance row): push with damage checks and a sha256 sidecar, verify by size + hash, `store_job`.
- `cloud/incidents.py` + `incidents.json`: 22 known incidents with fingerprints; `classify`, `match`, `repeats`, `record`,
  `doctor`. The guard, the watchdog and a failed `create` record what they saw.
- `cloud/watchdog.py` + `.github/workflows/watchdog.yml`: session-independent rules (expired or unnamed live pod -> stop; ERROR,
  stopped disks, network volumes, idle serverless workers -> report; 24 h ceiling -> stop all; balance floor -> report; stalled
  job -> stop only with every output stored), cron every 30 min, `kill_all` button for GitHub Mobile. Needs the repository
  secret `RUNPOD_API_KEY` (the creator adds it; the workflow says so and exits 0 without it).
- `python -m explainer_engine.cloud status|logs|doctor|budget|incidents|stop-all`.
- `runpod.check` lists stand-alone network volumes ($0.07/GB/month) and serverless endpoints with min workers > 0: the two
  ways an account bills with no pod.
- Tests: `tests/unit/test_cloud_guardian.py` (22: the record, the mapping, stalls, store, incidents, scenarios 1-15 of the brief,
  the create CLI); `test_runpod.py` 37.
- Folded in the independent RunPod validation (another thread, 09:24) and the lost-money audit (09:25): the whole-account
  `GET /billing` for the 24 h ceiling; network volumes, global volumes and serverless endpoints in `check`, the watchdog and
  `delete-volume <id> --yes`; an unreadable listing is a PROBLEM, not silence; 402 stops the card loop; `Retry-After` is
  honoured; only a restricted key enters a pod; hooks refuse `runpodctl create|start` and `PATCH /v2/pods`; scenarios 16
  (stopped pod cannot restart) and 17 (balance hits $0 mid-job: RECOVERY_REQUIRED with the unstored outputs visible);
  GraphQL balance retirement (early 2027) noted with a revisit date. The audit's finding: the leak was 2026-10-15..19, before
  D-56; nothing billed since. The creator's two one-time actions: the `RUNPOD_API_KEY` repository secret (watchdog) and
  RunPod's low-balance e-mail alert. Overlaps PR #19 (the audit thread's `check` additions): whoever lands second rebases.

## 2026-10-22 — Stage C: World Bible and asset library (D-70; the master brief, thread "წარმოების არქიტექტურა და ვიზუალი")
- `explainer_engine/world/bible.py` + `bible.json` v1.0 (draft) + `schemas/world_bible.schema.json`: the look v2 thread, the era
  codex and the palette pinned by hash under one version; camera language, graphics style (the narrated-style black opening card
  and chapter recap cards), era-change rules, characters (none permanent, the creator 2026-10-22), motion default (stills +
  2.5D parallax), banned drift, anchors (empty until the pilot), changelog. `check` fails on a part edited without `bump`;
  `approve --by` is refused on drift and records who and when.
- `explainer_engine/assets/library.py` + `assets/library.json` + `schemas/asset_library.schema.json`: one record per reusable
  asset (id P-66, file + sha256, tags, bible version, provider/model/version/prompt/params/seed/refs/LoRA/cost, licence,
  approval, lineage, origin); `register` warns about duplicates (same bytes, same recipe, shared tags) and never vetoes;
  `find`, `approve`, `derive`, `children`, `verify` (reports, never deletes), `ids_for_files`, `record_painted`. Seeded with
  the eight scientists_v0 sprites and their analyst reference from the generation ledgers, all `superseded` by look v2.
- Wired in: `world.resolver.resolve` writes `bible`; `imagegen.plan.make` writes `bible` (outside the hash); `paint plan` records
  `assets` (which references are library assets); a reusable plan's painted pictures are registered (`paint.shelve`, sync and batch).
- Docs: [WORLD_BIBLE](WORLD_BIBLE.md) (WB-01..WB-10, `docs_lint` home), INDEX row; ASSET_SYSTEM, VISUAL_WORLD_ARCHITECTURE and
  CREATIVE_STYLE_BIBLE point at the code. Tests: `tests/unit/test_world_bible.py` (9), `tests/unit/test_asset_library.py` (9).
- Not built (said plainly): embedding search; the Cloudflare runner; PR #15's picture library is referenced by `origin.source`,
  not duplicated. Nothing paid; no pod.

## 2026-10-22 — Stage D code: image providers behind one interface, the model pilot (D-70; nothing paid)
- `imagegen/providers/` (`base.py`, `bfl.py`, `fal.py`, `gemini_adapter.py`): estimate before any call, ledger reserve / refund /
  settle, cache by request incl. reference bytes and seed, `ChargeUncertain` never retried, keys only from `BFL_API_KEY` /
  `FAL_KEY` / `GEMINI_API_KEY`. Endpoints, fields, states and prices read on 2026-10-22 from docs.bfl.ml and fal.ai (module docstrings).
- `imagegen/plan.py`: `bfl` and `fal` providers (adapter rows in `options`, prices from the adapters); `production/paint.py`
  `run` paints through the adapter (same ledger, same failure handling; batch stays Gemini's).
- `imagegen/pilot.py`: the six-shot pilot (sheet, two heroes in a room, reverse angle as an edit, expression change as an edit,
  era jump, legible sign) x 4 takes on Klein 1k, Seedream 4.5 2K and Qwen-Image-Edit 1344x768: estimate $1.92 (the card said
  ~$2.26 with Qwen at a larger size); `run` refused without `Run.approve("pilot", hash)`; results.json per take; collage per
  candidate. Editors start shots without a source from a blank canvas, recorded as such.
- `config/spend_caps.json`: `bfl_usd` 3.0, `fal_usd` 9.0 (the creator's card of 2026-10-22, ceiling $15 with RunPod's 3).
- Tests: `tests/unit/test_image_providers.py` (12: BFL and fal flows with fake HTTP, moderation and 402 refunds, lost answer,
  timeout, missing key, cache key, pilot plan/hash, refused without approval, cap stop, CLI estimate). PP-01 names the providers.
- Waiting on the creator: the decision card (run the pilot ~$2; with or without the Illustrious pod).
- 12:01 first live attempt: $0, every account refused (BFL 403 Not authenticated, fal 403 locked: exhausted balance); account
  errors now stop a candidate after one call. 12:26 the creator asked for style variants first: `pilot styles` (six looks, one
  scene, Klein + Seedream, $0.29, own approval) added with a test; waiting for his card and the account top-ups.
- 2026-10-22 12:35, stage D style step: the creator's mix replaces the six generic looks (`imagegen/pilot.py` QUALITIES +
  STYLES: volume, clean design, cinematic, comic faces in six blends, no work named in a prompt, `BANNED_NAMES` guard and test);
  estimate $0.294 unchanged, new hash 32fbe1f4c423fffc. Nothing paid.
- 2026-10-22 13:20, D-70 stage F code (free, while the pilot waits for the accounts): `production/parallax.py` +
  `production/depth.py` (2.5D parallax, `motion.parallax` up to 2 % of the width, depth map next to the picture), drawn in
  `assemble.finish_frame`, depth maps in the chunk stamp; Scene Package schema fields; `production/segment_hash.py` (per-segment
  hashes, stale list CLI, PV-59 / PV-60 wired into `validate.check_script`). Tests `tests/unit/test_scene_package.py` (9).

## 2026-10-22 — Four candidate animated universes (the creator's brief of 13:23; nothing paid)
- The creator asked for ONE original, reusable animated universe decided before production, compared on four concept boards
  (the same four environments per board), with feasibility, an asset-library plan and a proof of concept of real animation.
  Written as [research/ANIMATION_UNIVERSE_2026-10-22](research/ANIMATION_UNIVERSE_2026-10-22.md): philosophy, the honest
  present/proposed capability table (stills + Ken Burns, PR #18 parallax, face sheets and bubbles exist; a cut-out rig and
  cycles do not), four directions (Paper Stage, Ink and Cel, Soft Volume, Poster Graphic), the comparison, a recommendation
  (Ink and Cel first, Paper Stage second; the choice is the creator's), the shared / variant / unique asset table, the
  test path through the existing gates, and the five-step rig proof of concept (`production/rig.py`, ~$0.05).
- Code: `explainer_engine/imagegen/universe_boards.py` on PR #18's provider adapters: `prompts` (20 ready prompts, the same
  scenes in every direction, no other work named, no look-v2 child cues or banned words, `lint`), `estimate` ($0.18 for all
  four boards on FLUX 3 Image Klein 1k; Seedream $0.80; Gemini $1.34), `run` refused without the creator's approval of the
  plan hash, cached and recorded per picture, account errors stop a candidate after one call; `board` composes ONE labelled
  image per direction (2 x 2 environments + the line-up strip). Tests `tests/unit/test_universe_boards.py` (8).
- Not done, by the brief's own rule: no board generated (the creator paused paid work until he tops up), no architecture
  change, no asset library, no episode. Waiting on his card: which candidate and how many takes.

## 2026-10-22 — The muse: simple and beautiful, emotion and physics good (the creator, 13:51; nothing paid)
- Research [research/ANIMATION_TOOLS_2026-10-22](research/ANIMATION_TOOLS_2026-10-22.md): the three reference shows' principles
  (three-stroke shapes, on-model with rationed exaggeration, no black line and background as a character, silhouette and negative
  space, long holds and snaps, silence, part rigs across worlds), the twelve principles as functions, the tools with licences read
  on their LICENSE files (Rhubarb MIT, AnimatedDrawings MIT, SAM 2 Apache-2.0, pymunk MIT, rembg MIT with a paid default model,
  ToonCrafter unclear weights). Skill `.claude/skills/animated-universe/SKILL.md`.
- Built: `production/rig.py`, a cut-out rig in numpy + PIL: pieces with pivots and a parent tree, eased keyframe cycles (idle, walk,
  run, point, react, fall), follow-through springs for secondary pieces, area-preserving bounded squash and stretch from vertical
  speed, closed-form drop-and-bounce physics, four mouth shapes from word timings, flip, and a 20-second proof-of-concept clip from
  code-drawn pieces over three parallax layers (`rig demo`; 1280x720 in 12 s). Frames are a pure function of their number.
  Tests `tests/unit/test_rig.py` (10). Looked at: the walk, the point at the sign, the talk, the jump with stretch and squash.
- Not done: the `rig` beat kind in `assemble.finish_frame`, Rhubarb and pymunk in `tools/`, pieces cut from a painted character
  (waits for the creator's choice of direction), the five proposed house rules are not in the registry (D-59 needs sources).

## 2026-10-22 — Boards as one picture with four places; the creator's reference as a fifth direction (nothing paid yet)
- The creator (14:15): one reference picture per world with four places, then a 10-second test shot ("100 people end up in the
  ice age") in a less primitive look than the code-drawn rig figure; he attached his own reference picture.
- `imagegen/universe_boards.py`: `--mode grid` asks for ONE picture of a 2 x 2 grid (city, Mars, prehistoric, drowned future) per
  direction, labelled by `grid_board`; `--directions` picks a subset; a fifth direction `wild_ink` describes his reference's
  qualities in our own words (uneven heavy ink line, bulging eyes, rubbery mouths, painterly plates, neon accents for the strange)
  and is never given his picture as an input; the lint caught "wobbly" (a look v2 child cue) and it was replaced.
  Estimate on Gemini Nano Banana 2.1 2K, 5 directions x 2 takes: $0.50 (3.1 Flash $1.01). BFL still answers "Not authenticated",
  fal is locked. Tests `tests/unit/test_universe_boards.py` (10). Waiting on his card.
- 14:19 the approved run (card cmsg_01Hnu5zB86sjUj5GtTgaUkPWCTKFFQJ2XNiT2NW3zgjnPx, Nano Banana 2.1, $0.50): $0 spent, every request
  refused with Gemini HTTP 402 "prepayment credits are depleted". The adapter sent all ten because a Gemini 402 was a plain provider
  error; `providers/gemini_adapter.py` now raises `AccountError` on 401/402/403, so the first one stops the candidate (test added).
  The approval stays bound to plan hash 807c365090475447 in `jobs/universe/2026-10-22_grid/run.json`; a rerun after a top-up paints it.

## 2026-10-22 - Research: the hybrid visual model (AI world, rigged characters)

The creator asked whether AI should only paint and move the environment while characters (wounded ones and hard poses
included) are drawn and rigged with classic tools that AI drives. Answer and sources in
[HYBRID_VISUAL_MODEL_2026-10-22](research/HYBRID_VISUAL_MODEL_2026-10-22.md): yes, split by "must be exact and repeatable"
(body, joints, cycles, wounds, physics: code-driven rig) vs "may vary" (plates, one atmospheric shot: AI); ambient nature
motion by code on the plate; the ice test's leg defect comes from parts cut out of one painted pose, so parts must be made
as parts (SVG body + painted face set) and joints must bend. Synfig, Blender Grease Pencil, OpenToonz, Godot, Rive, Spine,
Live2D, Moho and Lottie compared for AI control, headless render, deformation and licence. Documents only; nothing paid;
no code or rule changed.

## 2026-10-22 - Hybrid model PoC: a bending rig on a painted plate

After the research above the creator said "კი" to the free PoC. `production/bend_rig.py` (numpy + PIL): two-bone limbs
drawn as one ink shape (no knee or elbow seam), inverse-kinematics feet planted by the distance travelled (no slide), hips
clamped by reach, a keyed fall/get-up, a squash-and-flip turn, a scrape decal and an antalgic limp as data, follow-through
on the scarf, code-made snowfall and tree sway over the ice test's plate (crowd painted out, no new spend), footsteps and
impacts read from the poses. `check` (BR-1..BR-7) passes on all 432 frames; `tests/unit/test_bend_rig.py` (10). Result and
what it does not solve (style seam, one view): [HYBRID_VISUAL_MODEL_2026-10-22](research/HYBRID_VISUAL_MODEL_2026-10-22.md)
section 8. Nothing paid.

## 2026-10-22 - Hybrid model PoC v2: painted faces on the rig, a real turn, a softer walk

The creator: faces from the image model, bodies from us; fix the turn; the walk is a bit robotic. `bend_rig --heads`
(painted head per expression, hands in its skin colour), the turn as side -> front -> side with the feet stepping to
their own sides, heel-to-toe roll in every gait (footfall sound at the heel strike), torso pitch wave, arms lagging the
legs, head nod spring. `check` 0 findings; `tests/unit/test_bend_rig.py` 12. Faces reused from the Wild Ink board,
nothing paid. Notes on what a real face sheet needs: [HYBRID_VISUAL_MODEL_2026-10-22](research/HYBRID_VISUAL_MODEL_2026-10-22.md) 8.1.

## 2026-10-22 - Hybrid model PoC v3: the body's paint from the picture (Sheet)

The creator's Wild Ink cave reference as the world's style; question answered (what is reachable in motion, which
tools are missing, 3/4 views). Free, his choice: `bend_rig.Sheet` carries painted parts (`parts.json`: picture, bone,
half-widths per part) onto the rig's bones by a similarity, outline stays the rig's; Einstein cut from the reference
with GrabCut walks, falls, turns and limps with his paint. 14 tests, `check` 0 findings. What a real parts sheet must
be: [HYBRID_VISUAL_MODEL_2026-10-22](research/HYBRID_VISUAL_MODEL_2026-10-22.md) 8.2.

## 2026-10-22 - Hybrid model: a 30-second Ice Age test cartoon in 2.5D

- The creator (19:35, 19:38): a spacious world, faces, clothes and expressions from the image model in the reference's
  style, a 30 s cartoon with heroes, our rig for the bodies; Klein approved with a $1.5 ceiling; assets reusable for the
  Ice Age episode. Eleven Klein pictures, $0.154 (ledger `jobs/ice_cartoon/job-001_2026-10-22/run.json`).
- `production/bend_rig.py`: `Sheet` mode `cut` (painted cut-outs carried whole on the bones), the `three_quarter` view,
  per-character `Build` (`use_build`, `load_build`), heads per expression and view (`head_picture`).
- `production/ice_short.py`: the 2.5D shot (layers, camera keys, depth scaling, sled physics, rope, snow, sounds from the
  poses, checks). Research doc section 8.3.
- Tests: `test_bend_rig.py` (3/4 view, build swap, cut part on its bone) and `test_ice_short.py` (camera ground line,
  depth scaling, captions).

## 2026-10-22 - Ice Age test cartoon v2: physics, mocap gait, operator camera (stages 0+1 + the paid stage 2 test)

- The creator (20:32): the physics and the montage are off; plan first (the Claude Doc), then his choice (card 20:47): stages
  0+1 free + the ≈$0.50 fal test.
- New `production/physics2d.py` (pymunk: terrain, lane, sled on a rope with a giving arm, ragdoll with muscle tone, follow-
  through, camera operator), `production/mocap.py` + `gaits.json` (CMU BVH -> measured gaits, retargeted by leg length;
  `bend_rig.measured`), `ice_short.py` rewritten on them (10 shots, events -> sounds, checks 0 findings).
- Tests: `test_physics2d.py` 7, `test_mocap.py` 3, `test_ice_short.py` 6; `python -m pytest -q` -> 671 passed, 1 skipped.
- Rendered: `hybrid_model_2026-10-22/ice_cartoon/v2/` (30 s with the earlier voice takes, the 5 s fall clip, old-vs-new
  sheet). Nothing new paid for pictures or voice.
- Paid (fal, approved on the card): Wan 2.2 Animate $0.20 on the walk clip (unusable: smeared, no pose from a small cartoon
  figure); refusals before generation cost $0. Kling 2.6 Motion Control $0.35 on the close-up clip: Dev re-animated on
  model from one reference picture, following the rig's gesture and acting with the face. Total $0.55; ledger
  `jobs/ice_cartoon/job-002_2026-10-22/run.json` (cap 0.75).
- Learned: motion-transfer models need a hero filling the frame; wide 2.5D shots give them nothing; Kling Motion Control
  is a candidate for close-up inserts driven by the rig. Research doc 8.4.
- Next: the creator's read of v2 (old vs new), then the remaining plan stages (secondary motion on soft parts, a 3/4 mesh
  warp, more mocap clips: jump, land, get-up).

## 2026-10-22 - AI-video route: night run (Wan 2.2 style LoRA + a 2-minute test video), rig cartoon retired

- The creator (22:19): the rig cartoon v2 is "so bad there is no hope"; new route (plan doc, 22:26): photo style LoRA
  keyframes -> Wan 2.2 14B first/last-frame clips with a style video LoRA -> SeedVR2 -> montage. 22:41: no permanent heroes
  and no character LoRAs ever. 22:45/22:54: yes to every stage and cost within the RunPod balance; full pod authority;
  audio at most 3,000 ElevenLabs credits; 22:50: by morning trained models, a new 2-minute test video, tests for the new
  production and the unneeded tests gone. Script approval (OR-15) waived by him for this test only.
- New `explainer_engine/aivideo/`: `shotplan.py` (shots.json and timeline checks, keyframe references, montage plan,
  money schedule) and `pod/` (launch.py through the one pod manager + ledger + guard, pod.sh stage clock with self-stop,
  kf.py FLUX.2 klein + photo LoRA keyframes, clips.py Wan 2.2 I2V FLF2V + lightx2v 4-step + style LoRA in fp8 layerwise
  casting, wan_lora.yaml ai-toolkit wan22_14b, watchdog.py, montage.py).
- No A40 was free; the pod runs on an L40S at $0.79/h, so the $2.7 ceiling ends it after 205 min: the watchdog stops
  training at 95 min (800 steps, a checkpoint every 100) and the clips stop at 170 min (`schedule_fits`). The first try
  (~8 min) died on two setup faults, now fixed: a body without `volumeInGb` got a 20 GB volume on /workspace, and
  removing the CUDA forward-compat libs breaks torch on a datacenter card with driver 550 (they stay unless torch fails).
  Try 2 (~22 min) ran every stage in 21 min without doing anything: pod.sh's `pip install -U huggingface_hub` pulled 2.2,
  which transformers refuses, and the smoke failures did not stop it. Now the hub is pinned below 2 (`fixhub.py` heals a
  running pod), a failed smoke is fatal, and the ceiling of the next try is $2.4 (training to 85 min, clips to 150).
- Narration: one ElevenLabs take, 1,522 credits, 113.7 s; word times by faster-whisper; 16 segments.
- Tests: `tests/unit/test_aivideo_shotplan.py` (9). Proposed for removal on the creator's word (not done): the rig cartoon
  route (production/bend_rig, ice_short, physics2d, mocap, gaits.json, pymunk) and its four test files.
- Try 3 (L40S, 2 h 32 min, ~$2.0): the Wan 2.2 style LoRA trained 800 steps in 32 min (`wldnk_wan22_v1`, HF
  `night_run_2026-10-22/train/`), 38 keyframes with the photo LoRA (`wldnk_style_v1`, 1250 steps, from the LoRA thread);
  every clip was drawn and lost: diffusers' mp4 writer needs imageio-ffmpeg. Frames now go to disk first; zero clips fails.
- Try 4 (A40, $0.06) died in setup (torch half-replaced by a pip that could not uninstall debian's numpy): install beside.
- Try 5 (clips only, `pod_clips.sh` + `launch_clips.py`, $0.69/h, ~$0.31): c01 at 720p (285 s), then 480p (97 s each)
  until the deadline: 9 of 16 clips. The night ledger stops at 80 % of $3.6; ~$2.85 billed in all.
- Seen in the clips: the style holds; motion is small; where first and last keyframes differ in layout, FLF2V cross-fades
  (ghosted faces in c03, c06). Next: last frame = a small edit of the first (same layout), or plain I2V with a motion prompt.

## 2026-10-24 - The vault: nothing we made is lost (D-73)

The creator asked for a thread that makes sure none of the work is ever lost and all of it stays in his hands. Inventory
(2026-10-24 09:30 UTC): the primary copy is the private HF dataset `vano1919/tmr-artifacts` (owned by vano1919; 9 290 files,
47.8 GB); the approved style LoRA `wldnk_style_v1.0` matches its sha256 `b384ad49…` (same bytes as `train_qwen_v5` step 1750),
the fallback matches step 1250; the Wan 2.2 LoRA (all checkpoints), every Qwen style run, datasets v1-v7, references and the
scene LoRA's redrawn pairs are there. RunPod holds no data: the 12 stopped pods have 0 GB disks and no network volume
exists; the one running pod is the scene LoRA training (not touched). Single point of failure: HF alone, and code only on
GitHub branches of 9 open PRs.

- `explainer_engine/vault.py` (stdlib): `snapshot` (HF tree API with sha256/blob ids -> `docs/VAULT_MANIFEST.json`, critical
  rows by `config/vault.json`), `verify` (exit 1 on MISSING/CHANGED), `pull` (the second copy on any disk, hash-checked,
  `.part` swapped in only after its hash matches, identical bytes copied instead of downloaded, re-runs download nothing),
  `check-uploaded` (a pod proves its outputs are on HF before it stops), `lint_pod_script` (VT-01/02).
- On HF: tag `vault-2026-10-24` pins today's state; `vault/code/` holds git bundles of both repositories, every branch.
- 636 project files (1 GB: night-run and ice-cartoon assets, Titans voice and narrator cuts, kf_v2, dataset_style_v7 extras,
  ic_test, the eras clips, eval sheets) and the creator's uploads (his reference photos) existed only in the project files:
  now on HF `project_files/` (tag `vault-2026-10-24b`); 147 HF download-cache stubs (`.cache/`) skipped. Totals: 9 979 files,
  49.3 GB; critical 4 197 files, 8.1 GB. The snapshot never lists its own manifest copies (`vault/VAULT_MANIFEST*`).
- Docs: [VAULT](VAULT.md) (VT-01..VT-05, restore), decision [D-73](DECISIONS_AND_OPEN_QUESTIONS.md), INDEX row; docs_lint knows VT-.
- Tests: `tests/unit/test_vault.py` (8: paging, critical marking, loss and change caught, upload check, empty output, pull
  re-check and twins, a corrupt download never overwrites, the lint). Nothing paid, nothing deleted.
- Open: the second copy's place is the creator's call (his PC: `vault pull --dest <folder>`, ~8.1 GB); the pod-script lint is
  wired into `runpod.lint_pod_script` when PR #22 (which adds that function) merges.

## 2026-10-25 03:20 Tbilisi: the script engine adds the episode look and keeps the LT-66 absolutes

- `style.look` in the shot cards names the episode's look file (`episode_look/1`, read next to the cards by `film_shots.load`)
  or gives its phrase and lights inline. A shot may name a light variant with `frame.look`. Every keyframe moment and hero
  sheet then ends with the phrase through `episode_look.apply` (AC-17). The moment's word budget shrinks by the phrase, so
  the whole prompt still passes `style_prompt.check` (40 words).
- `style_check` FAILs a look phrase or variant with non-colour words or style words (AC-17), a variant the look lacks, and
  any `neg_keyframe` other than `style_prompt.NEGATIVE` (LT-66 A3). Style-LoRA items now carry `neg` = NEGATIVE and
  `inference` = `style_prompt.INFERENCE`. A8 caught "to take a photo" in film_1min S02-02, which now reads "to snap a picture".
- Tests: `test_every_style_prompt_ends_with_the_episode_look_and_still_fits_lt65`,
  `test_a_look_with_style_words_or_a_negative_of_its_own_fails_lt66`.

## 2026-10-25 16:30 Tbilisi: gate cards for every drawn frame, with object counts and absent things

- The LoRA thread found a gap, confirmed in code: `qa/keyframe_gate.py` asks about `things` (KG-01) and `absent` (KG-21),
  but the shot cards had no such fields and `gate_cards` built cards for keyframes and cuts only. The Qwen-Image-2.1 style
  LoRA then drew a second bus and a city for "city bus".
- `film_shots/1` gains `frame.things` ({name: count}, or {name: {count, plural}}), `frame.absent` and a top-level `absent`
  (the world's). `gate_card` passes them as the gate's `things` ({plural, count}) and `absent` (deduplicated).
- `gate_cards` now covers every drawn frame: next-pose first frames and the guided last frames (`.last`, with `master`
  for KG-13). A lead who exits is not expected in the last frame.
- The bus example and film_1min count one yellow city bus on the plain and list a city, a building and a paved road
  as absent. Test: `test_every_drawn_frame_gets_a_gate_card_with_exact_counts_and_absent_things`.

## 2026-10-25 16:45 Tbilisi: KP-44, never name what must be absent

- The LoRA thread measured that the Qwen-Image-2.1 style LoRA draws a city behind "city bus": none at step 0, a city at
  steps 250 and 500. `film_shots.absent_check` (KP-44, REVIEW) now flags any picture prompt that says a word of the
  world's or the frame's `absent` things. It also catches "with no road", because models draw what is named after "no".
  Spoken lines in quotes are left out.
- The bus example and film_1min say "yellow bus" (tag, places, relations, things) and "an open snowy plain". "City"
  stays in `absent`. Test: `test_a_picture_word_that_names_an_absent_thing_is_flagged`.

## 2026-10-25 19:40 Tbilisi: every hero in the moment, with a reaction (KP-45)

- The LoRA thread checked the Napoleon prompts before round 2 of the 2.1 style-LoRA loop. Two issues: S04-01, S08-01
  and S13-01 dropped a hero, and the multi-hero moments named the others with a bare head phrase and no verb.
- `keyframe_prompt` now spends its 40 words in rounds, so every figure is named before any costume word.
  `_trait` (the tag's first trait) and `_light_head` (the light source) are the middle levels. Others with a card
  reaction come first.
- New REVIEW rule KP-45 (`moment_check`): a figure missing from the moment's words, or two or more figures where nobody
  but the lead does anything. It found five more Napoleon shots and film_1min S02-01. Those cards, and the eight
  multi-hero keyframes, got short reactions in `episode.py`.
- With three or four heroes, 40 words cannot hold every costume. Identity there comes from the hero sheets and the
  composition. Test: `test_a_four_hero_moment_names_everyone_and_gives_the_others_their_reactions`.

## 2026-10-25 22:10 Tbilisi: all open branches in one place; D-71 and D-78 written; CT-09 forbids the edit pass

ვანო: put the repository in order so the newest rules are in one place, and date every PR.
- PRs #14-#21 and #23-#25 are merged into PR #22's branch (#19 as superseded by main's `check`). Every PR's dates,
  the ID collisions (D-63 -> D-76, D-74 -> D-77, ST-14..16 -> ST-17..19; the first definer keeps the number) and the
  rule conflicts with the current winner: [research/BRANCH_INTEGRATION_2026-10-25.md](research/BRANCH_INTEGRATION_2026-10-25.md).
- Joins: OR-19's sample filter runs after D-69's staging plan; staged references build on `hero_refs`; both painters send
  `P.full_prompt`; World Bible v1.1 (the modern_new_york era) and its tests follow the committed version; BP-40 keeps
  ვანო's 2026-10-20 21:14 wording plus the 2026-10-24 scope; VT-01/02 run inside `runpod.lint_pod_script`.
- D-71 (Wild Ink) and D-78 (no edit model, no img2img pass; ვანო 10:50 Tbilisi) were only in project memory; now in the
  decision log. CT-09: `MAX_CHAIN` 0, a `derive_from` other than `original` FAILs; the continuity test loses its edit
  variant; the example card uses `qwen_image_21`. Test: `test_no_edit_pass_on_an_earlier_shot`.
- Open for ვანო: ASSET_COMPOSE (code composes) or D-75 (cards + references) as the production route; removal of the
  retired rig code; closing the merged PRs.

## 2026-10-25 22:20 Tbilisi: the retired rig route removed

ვანო ("მიდი გააკეთე", 22:18 Tbilisi, on the cleanup list of research/BRANCH_INTEGRATION_2026-10-25.md section 4): the
rig route he retired on 2026-10-22 22:19 goes. Removed `production/bend_rig.py`, `ice_short.py`, `physics2d.py`,
`mocap.py`, `gaits.json`, their four tests and the `pymunk` requirement; the history stays in git, PR #21 and
research/HYBRID_VISUAL_MODEL_2026-10-22.md. `production/rig.py` (PR #20's cut-out rig, not part of the retired cartoon)
stays. The merged PRs #14-#21 and #23-#25 are closed in favour of PR #22; their branches are kept.

## 2026-10-25 22:22 Tbilisi: D-75 is the production route

ვანო: "we are on D-75 now". Keyframes are drawn from continuity cards and references (SHOT_CONTINUITY); ASSET_COMPOSE
(code-composed shots) is marked superseded and kept as history. Recorded in D-75 and the integration audit.

## 2026-10-25 22:30 Tbilisi: one main agent and one critic (OR-20, D-79)

ვანო said yes (22:21 Tbilisi) to one point of an outside AI review: one strong main agent and at most one independent
critic. Review page of the three AI answers: https://claude.ai/artifact/4oP3AWRwrNJEj22WYXA2vd.
- OR-20 / D-79: the main agent (`orchestrator`, `lora-coordinator` or the session) runs every stage itself from the stage
  pages in `.claude/agents/`; the staged writing, `stage_guard` and every gate stay. Only `script-critic` and
  `lora-checkpoint-judge` are spawned, with a fresh context. The orchestrator gets the `Agent` tool for its critic.
- The eleven stage pages say so in their description; the story-engine skill, STORY_ENGINE, LORA_TRAINING and CLAUDE.md
  follow. Counter recorded in D-79: one context grows longer and the stages lose the cheaper Sonnet model.
- Test: `tests/unit/test_agent_roles.py`.

## 2026-10-25 23:30 Tbilisi: style learning and scene transitions, research and plan

ვანო asked for one last, evidence-backed plan for the style and for scene transitions. Written up in Georgian at
https://claude.ai/artifact/MBSTqzFYrM1RRGrLhTYbfM and in `docs/research/STYLE_AND_TRANSITIONS_PLAN_2026-10-25.md`:
why our style training failed (self-generated data, the caption tail, untested model switch), a free baseline before any
new LoRA, grammar and transitions measured from downloaded references but no training on their frames. Nothing paid;
no rule changed until he decides.
- 23:20 Tbilisi: plan v2 after ვანო's correction (the genre, any topic; no rights limits, his decision):
  https://claude.ai/artifact/Ajuy7VSeUuzLWDfU3Fyc4E, section 5 of the research file.
- 23:40 Tbilisi: `research/reference_study.py` (first stage of the v2 analysis pipeline, free): cuts per video, shots per
  minute, median shot, cuts in the first 30 s, cut density at the "Most replayed" peaks vs lows (from yt-dlp's
  `.info.json` heatmap), and each channel's most-viewed videos against the rest. Test: `tests/unit/test_reference_study.py`.
  Next stages (shot descriptions, Whisper speakers and J/L cuts, script structure) once the references are in.

## 2026-10-26 00:35 Tbilisi: reusable before fast (OR-21); xworld_style_v1 from the repo

ვანო (00:33-00:34): "reusable vs speed: reusable every time ... if the cost is the same". Rule OR-21 in ORCHESTRATION and
CLAUDE.md. A scratchpad pod launcher had been refused by the session's safety check; the xworld style LoRA (95 Rick and
Morty frames, rank 16, Qwen-Image-2512, ≈$3, cap $4) now starts through `cloud/runpod.py create` with its pod script and
config committed in `explainer_engine/training/pods/xworld_style_v1.{sh,yaml}`. `create --disk GB` sets the container disk
(the Qwen download needs more than 80 GB). The pod script returns at the end instead of sleeping, so the pod stops itself.
Tests: `tests/unit/test_reusable_first.py`, `test_runpod.py::test_create_cli_sets_the_container_disk`.
- 00:45 Tbilisi: ვანო chose to delete the unused global volume wasteful_fuchsia_fish; `runpod delete-volume <id> --global
  --yes` (new, verified by listing again; test `test_delete_volume_global_needs_the_word_and_verifies`) removed it. Pod
  hrdpkuwoh6iyuz (L40, $0.69/h, job cap $3.2 = 80 % of the run's $4) started through `runpod create`, guard on.

## 2026-10-26 01:06 Tbilisi: rule one (OR-22) and a detailed plan before every pod (OR-23)

ვანო (01:05): never take a system decision on an assumption, agree every detail with him, also in auto mode; (01:06) before
every pod a detailed plan, not a general one. Rows OR-22 and OR-23 in ORCHESTRATION; CLAUDE.md carries both above the
commands. Cause: the xworld style LoRA was started on Qwen-Image-2512 from an old rule against his newer 2.1 decision.
Test: `tests/unit/test_agree_every_detail.py`.

## 2026-10-26 01:20 Tbilisi: D-80, start from zero on Qwen-Image-2.1; old rules reconciled (LT-73)

ვანო (01:02-01:04): the engine moved to Qwen-Image-2.1, visuals included; review every rule and resolve conflicts for the
newest. His answers (01:15): every old LoRA banned everywhere, the new look is learned from Rick and Morty, style and scene
sequence are taught together on 2.1 with the prompt types of the continuity research tested; whether the sequences enter
training as sequences is decided in the process. Changed together:
- D-80 (new), D-71 superseded, D-78 amended; LT-64, LT-69 rewritten; LT-65..LT-68 and KG-22/KG-23 suspended (written for the
  banned look); KG-16, ZI-06, CT-09 for 2.1; LT-73 (a new decision rewrites every older rule it contradicts, same change).
- Code: `keyframe_gate.RETIRED` (2512, Edit-2511) and `RETIRED_LORAS` (`wldnk_*`) refused by `check_stack`; `LORA_BASE`
  holds only `xworld` on 2.1; `style_prompt.INFERENCE` has no LoRA until the creator rates the new one; the old flux/wan pod
  scripts are marked retired; SHOT_PROMPTS and the lora-training skill carry a D-80 banner.
- Tests: `test_keyframe_gate.py::test_only_the_2_1_stack`, `::test_old_loras_are_banned`, `test_episode_look`.
- Cost of the mistake that led here: the xworld pod on 2512 (≈$0.15), stopped at 00:59.
- 01:45 Tbilisi: the new D-80 material comes fresh from the video (ვანო: "we changed the training, are we using the same
  frames?"). Only Rick and Morty footage on hand: the 2 h S1-3 compilation (1142 shots). Choices he left to Claude (01:44):
  start with these 2 h; sequence material = shot -> next shot of the same scene plus start -> end of a shot where the pose
  really changes; captions by Qwen-VL on a pod (plan first, OR-23), every caption checked by Claude, no character names;
  10 % of scenes held out whole for the prompt-type test.
- 02:40 Tbilisi: the xworld_v1 material is ready (free, from the 2 h video, every image checked by eye): 766 style frames,
  357 shot -> next-shot pairs of one scene, 234 start -> end pairs inside a shot (a real pose change, still background),
  28 whole scene chains held out (102 shots; 4 chains of 6-13 shots for the 6-frame prompt-type test) with a guard band.
  Rejected: gore, readable text and credits, Nazi symbols, nudity, vomit, show-in-show art, split screens. HF:
  `lora_plan_2026-10-26/dataset_xworld_v1/` (manifest.json; 1337 files) and `..._code/` (scripts + review records).
  No captions yet: the Qwen-VL pod waits for the creator's OK of its plan (OR-23).
- 03:05 Tbilisi: caption pod script `training/pods/caption_xworld_v1.{py,sh}` + `tests/unit/test_caption_xworld_v1.py`
  (Qwen3-VL-8B-Instruct; 1336 descriptions + 665 change lines; no names, no trigger, resumable). Not started: the pod plan
  goes to the creator first (OR-23).
- 03:15 Tbilisi: ვანო "ყველა კი" (02:15) to the night plan and to the missing rules. Night ledger
  `jobs/xworld_v1/night_2026-10-26/run.json` (runpod $8.75, 80 % = the agreed $7). Caption pod d0sxf4ya1gajsb (RTX 3090,
  $0.22/h, cheaper than the A5000, none in stock with a volume; `--volume 0`) started 02:17. New rules LT-74 (VL captions read
  before training), LT-75 (prompt-type test: measured against the real next frame, then eye, creator decides), LT-76 (held-out
  never in training, refused by the build), LT-77 (six 2.1 training samples); LT-07 style size 20-1000. Training pod files
  `training/pods/xworld_v1.{sh,yaml}` + `xworld_v1_build.py` (style + pairs with control, trigger `xworld style` in every
  caption, rank 16, lr 1e-4, 2500 steps, 1024 px, every 250 steps); the 2512 `xworld_style_v1.{sh,yaml}` are deleted (D-80).
  `hrdpkuwoh6iyuz` (stopped, 0 GB, $0/day) is listed in keep_stopped_pods so `create` runs; deletion still waits for his word.
- 02:40 Tbilisi (10-26): caption pod d0sxf4ya1gajsb stopped by the guard at the 10-minute boot deadline (slow tmr-pod image
  pull); `runpod create --boot-minutes` added (test), second pod 682n7rxqdgqycp started 02:29 with 30 minutes. The first stays
  stopped (0 GB, $0/day, in keep_stopped_pods); deletion waits for his word.
- 02:45 Tbilisi: ვანო (02:37-02:38) raised the night limit to $9 (ledger `runpod_usd` cap 11.25, 80 % = 9), 15-minute checks,
  saving at every milestone, full autonomy inside the plan, strange questions to the coordinator for a separate research
  thread: LT-78.
- 02:45 Tbilisi: 682n7rxqdgqycp was still fetching ghcr.io/vano1919/tmr-pod after 15 min (RunPod logs "still fetching
  image"); stopped (kept, $0/day) and relaunched as 9iyvc4ute6ppwp on RTX A5000 community $0.16/h with the common
  runpod/pytorch 2.4 image (cached on most hosts; the script installs transformers itself). Lesson: the big tmr-pod image
  is not cached on community hosts; script pods that need only torch use runpod/pytorch.
- 04:15 Tbilisi: captions done (9iyvc4ute6ppwp, A5000 $0.16/h, download 32 min + 47 min of captioning, billed $0.07 so far,
  2001 rows: 1336 descriptions 49-108 words, 665 change lines 11-55 words, 1 name). LT-74 automatic review
  (`training/pods/caption_review.py` + test): 19 edited (names to roles, cut endings), 0 dropped; read samples of both kinds.
  HF `caption_xworld_v1/captions_reviewed.jsonl` + `review_report.json`. Local dry build: 766 style + 591 pairs, no
  held-out leak, 6 samples; the test plan has 280 jobs.
- 04:25 Tbilisi: training pod create: every 48 GB SECURE card (L40, 6000 Ada, A40, A6000, L40S) answers "no instances
  available" under the CUDA >= 12.8 filter (LT-19); one try got an H100 NVL community at $2.59/h (only ~1.5 h inside the
  $4 job cap, half of it boot): stopped at once (kept, $0/day). A retry loop asks every 2.5 min for the cheapest job card.
- 05:10 Tbilisi: training on vvgrnie44lxhp8 (RTX PRO 6000 Blackwell): boot 2 min, train from 00:32Z, 1.31 s/step (+ ~1.5 min
  of samples per 250), projected end ~02:15Z, ~$3.2 of the $4 cap. Samples 0/250/500 (HF `train_xworld_v1/review/
  sheet_0-500.jpg`): by 500 the two new subjects (medieval market, cockpit) are drawn flat in the R&M line look; the
  held-out frames come close to the real ones; the no-trigger sample also goes flat (trigger bleed, expected with no
  caption dropout; watch it).
- 06:20 Tbilisi: training done 02:16Z (TRAIN EXIT 0, 2500 steps, 1.3 s/step; billed $1.57 so far, guard estimate $3.24 of $4).
  Ten checkpoints on HF `train_xworld_v1/output/` (250..2250 + final). Choice (`training/pods/xworld_v1_pick.py` + test, CLIP
  held-out closeness, then eye): A = 2250 (held 0.901, best), B = 1500 (0.894, best at least 500 steps away); 2500 has
  overfit flags (close crops, a ghosted double face in the edit sample, held 0.842). `test_xworld_v1/code/picks.json`
  (with the reasons and all scores), sheets in `train_xworld_v1/review/`. Test pod ys4qcp04yp4nym (RTX PRO 6000
  community $1.69/h, ostris/aitoolkit image, $1.5 cap) started 02:19Z; D/T run first.
- 07:30 Tbilisi: test pod ys4qcp04yp4nym drew all 80 D/T frames (A = 2250, B = 1500; 35 s per 1280x720 picture with CPU
  offload); V3-V6, D0, T0 were not reached inside $1.5. LT-75 scores (`training/pods/xworld_v1_score.py` + test; HF
  `test_xworld_v1/review/score.json`, sheets chain0-3.jpg): D/2250 CLIP 0.843, palette 0.105, ink x1.84, composite 0.130 >
  D/1500 0.038 > T/2250 -0.178 > T/1500 -0.195. On the sheets D follows the change lines (close-ups, cuts, new people); T
  repeats the previous drawn frame and degrades step by step. Weak spot: who a person is comes only from the description.
  **Money incident:** the detached `runpod guard` processes die in this cloud container after 5-30 minutes (logs end
  00:28Z, 02:27Z, 23:14Z); the test pod ran unguarded to $1.6 (cap $1.5) until the 15-minute check stopped it. The
  training pod ended by its own script. Fix to propose: run the guard as a tracked background task of the session, or
  give pods a self-enforced money cap. Night total ~$5.0 of $9 (balance $10.42 -> $5.41); nothing running; six stopped
  0 GB pods kept for his word. Report: https://claude.ai/artifact/3xSDYTdC4bHJRqShLdGuCW
- 10:50 Tbilisi: ვანო's story test (10:32): "Napoleon in his tent, a general reports the enemy, he rushes out and sees a great
  Mongol army on the far meadow", drawn on the new style from frame 0 with the winning prompt form. New reusable
  `training/pods/xworld_v1_story.py` + `.sh` (any story file in `training/pods/stories/`; frame 0 from text, every other
  shot = D with its drawn master as the only reference; a run may also redraw a master from text as a second branch) +
  `tests/unit/test_xworld_v1_story.py`; `xworld_v1_test.py` now shares `load_pipeline`, `Loras`, `draw`, `logger`.
  Story `stories/napoleon_tent.json`: 9 shots (tent A0-A4, outside B0-B3), 17 pictures (LoRA 2250: 9 + B from text 4; base
  4). Code on HF `story_xworld_v1/napoleon_tent/code/`. Pod plan put to ვანო (OR-23); not started.
- 11:00 Tbilisi: story pod wnrcpyh9f2xl2c (RTX PRO 6000 community $1.69/h) drew all 17 pictures in 13 min and stopped
  itself (STORY EXIT 0; guard estimate ~$0.39 of $1.2; the session-tracked guard ran to the end this time). Sheets
  `story_xworld_v1/napoleon_tent/review/row0-3.jpg`. Result: frame 0 from text is in the new style with an invented hero
  (A0, t_B0); the D form with a DRAWN master mostly copies the master: A1 adds the officer, but A2-A4 stay the master (no
  close-ups, no exit); outside from the tent master stays inside the tent and gets colour noise; B1-B3 from the text
  master repeat it (no riders, no army). Base model = photoreal, no style. So D's success on R&M (real masters) does not
  carry to our drawn masters; next test (text-only shots with the same hero description, D without "Keep everything
  else the same.") put to ვანო.
- 11:25 Tbilisi: ვანო: the faces look like the Rick and Morty boy; he chose option 1 (no retraining: lower LoRA weight +
  faces described unlike the show's default face; "დაუწყე 1"). Story runs now carry a LoRA `weight` (`Loras.use(key,
  weight)` unmerges and merges again on a change); story `stories/napoleon_faces.json`: two close-ups (general, officer),
  each as before and with a face description, at weight 1.0 / 0.7 / 0.5 = 12 pictures from text. Pod udfnfnuo6eim89 (RTX
  PRO 6000 community $1.69/h, cap $0.8 / 1 h, session-tracked guard); the stopped story pod wnrcpyh9f2xl2c joins
  keep_stopped_pods (0 GB, delete on his word). Note: my "~$0.3" for option 1 was low; a pod's fixed setup is ~$0.35.
- 11:40 Tbilisi: faces pod udfnfnuo6eim89 drew the 12 close-ups in 10 min and stopped itself (guard ~$0.28 of $0.8).
  Sheets `story_xworld_v1/napoleon_faces/review/faces0-1.jpg`. Without a face description the general keeps the show's
  default face (round head, dot eyes) at 1.0 and 0.7, less so at 0.5. WITH the face description (square fleshy face, hooded
  eyes, hooked nose / long narrow face, cheekbones, almond eyes) both men become our own designs at every weight; 0.7
  keeps the flat cartoon line, 0.5 turns darker and more painterly; at 0.7/0.5 the officer drifts from close-up to medium
  shot. Proposal to ვანო: weight 0.7 + a written face for every person (a composer rule with a test).
- 11:55 Tbilisi: LT-79 (ვანო 11:49 "კი დაწერე" + "the detailed description must differ from the show's characters"):
  xworld story files need a `cast` with a written face per person (4+ of shape, eyes, nose, brows, jaw/chin, mouth), each
  shot's `faces` and the face text word for word in its description, no trait or name of the training show's people
  (`SHOW_FACE`), runs default to weight 0.7; `xworld_v1_story.face_problems` + 6 tests; the two earlier stories carry
  `before_lt79` (napoleon_tent keeps weight 1.0 explicitly).
- 12:10 Tbilisi: ვანო (12:01-12:02, with a reference picture of four labelled figures): new cast for xworld v2 = full-body
  people in full costume on a plain background, line close to the show's, costume, face style and palette different, palette
  and drawing = his reference, ONE shared style block + a separate description per person. New
  `training/cast/sheet.py` (100 people: 50 roles x 2, faces by LT-79, `check`, `list`, `draw` via the BFL Klein provider,
  1k 3:4, a seed per person) + `tests/unit/test_cast_sheet.py`; `xworld_v1_story.show_traits` now matches whole words
  ("Elizabethan" is not "beth"). BFL: the working key is env `BFL_API_kay` (247.2 credits); `BFL_API_KEY` answers 403.
  4-person test x (text only | + his picture as style reference) = 8 pictures, $0.072 (ledger
  `jobs/xworld_v1/cast_2026-10-26/ledger.json`; HF `cast_xworld_v2/test4/`): text only matches his palette and line with
  our own faces; with his picture as reference Klein copies his four figures (bicorne Napoleon instead of a grenadier,
  his Renaissance man instead of a woman painter), so no reference.
- 12:20 Tbilisi: ვანო 12:11: new world = places without people, objects without people, people without extra things, each
  kind alone; samples first, then the whole world on the BFL credit; and check how such training behaves. `cast/sheet.py`
  now has one style CORE + a fixed frame per kind (person / place / object; the person prompt is unchanged), 6 sample
  places + 6 objects: 12 pictures $0.108 (HF `cast_xworld_v2/world_samples/`): all in his palette and line, places empty,
  objects alone. Research + our records put to him: one trigger over R&M frames + new pictures would blend the two looks
  (R&M dominates by count); proposal = two triggers in one LoRA (R&M sequence data keeps its own style word, the new world
  takes `xworld style`), creator-picked synthetic pictures as the minority, caption dropout; weight back to 1.0 on v2 if
  faces come out our own (his 12:13 note).

## 2026-10-26 13:30 Tbilisi: new-world pictures done, rating page

- BFL (FLUX 3 Klein, 1k): 220 pictures kept (100 people, 80 places, 40 objects; 16 of them the approved samples), every
  one checked by `training/cast/check.py`: 208 PASS, 12 REVIEW (CLIP "maybe people in the place"), 0 FAIL kept. BFL credit
  247.2 -> 42.0 (~$2.05 spent today in total).
- Claude's look: places and objects hold the style and palette; 20 of 50 people written as women came out as men and 4 are
  unclear (Klein ignores "a woman" after the role); o001 (figurines on the map) and o008 (people painted on the vase) break
  "objects without people".
- `training/cast/rate_page.py` (+ test): the creator's rating page, four levels, three reasons and a free note, kept in the
  artifact db (collection `ratings`): https://claude.ai/artifact/6MKaVGbdzs4jv56b96QKmA.

## 2026-10-26 13:55 Tbilisi: xworld_v2 round plan prepared (no pod yet)

- ვანო 13:26: train the new world's style in rounds; after every round test style AND scene logic (three worlds: inside,
  outside, a city street; five shots each), compare prompt forms, people described the way their era is pictured. Plan doc
  https://claude.ai/artifact/4TZNBRNF6NAYWMPueHBccr (4 x 750 steps, tests at 0/750/1500/2250/3000, ~$7.3, cap $9); waits
  for his choice and a RunPod top-up (balance $4.67).
- Code (OR-21, tests `test_xworld_v2_data.py`, `test_xworld_v2_rounds.py`): `xworld_v2_data.py` (210 new pictures,
  as-drawn captions, 10 held out), `xworld_v2_build.py` (new x3 under `xworld style` + the 591 v1 pairs under `rm style`),
  `xworld_v2.yaml`, `xworld_v2.sh` (round 0 base test, then train -> checkpoint step check -> test per round),
  `xworld_v2_scenes.py` (P1 = LT-75 D, P2 = D + camera/layout, P3 = text only), `xworld_v2_judge.py` (Qwen3-VL questions:
  checks, same place, shot size, era), `xworld_v2_sheet.py`, scenes `stories/v2/{tent,tundra,rome}.json`. On HF:
  `dataset_xworld_v2/`, `train_xworld_v2/code/`.
- 14:05 Tbilisi: independent review (https://claude.ai/artifact/MVN9UQUnyQekPj2rRt24v2): the R&M pairs are not prior
  preservation, the 234 within-shot pairs teach a still camera, no multi-person style images, thin test. ვანო chose round 0
  first (base model, `xworld_v2_round0.sh`: P1/P2/P3/P2F x seeds 11, 23). `xworld_v2.sh`/`.yaml` are `.draft` until the
  revised training plan: they still lack the VT-01 vault check and a two-trigger answer to `test_reusable_first`
  (CI failed on them, run 40302908548). Round-0 pod: no 80 GB card free (8 tries 13:55-14:00); 48 GB / 1.5 h put to ვანო.
- 12:30 UTC 2026-10-26 (round 0 done, ≈$0.95, balance $3.73): base Qwen-Image-2.1, 102 pictures, VL judge P1 0.66, P2 0.65,
  P2F 0.75, P3 0.85 (same place P3 0.5, size P1/P2/P2F 0.29-0.38). Seen by eye, not by the judge: chained shots (P1/P2)
  turn noisy and oversaturated, P2F frames are near copies, two men drawn as the same Napoleon type. Auto-QA plan from the
  QA-methods thread: `/mnt/project-files/xworld_v2/AUTO_QA_PLAN_2026-10-26_ka.md` (one method per failure; FAIL power only
  for metrics with AUC >= 0.8 on ვანო's ratings; thresholds are a proposal until his OK, RULE #1). First free step done:
  `training/qa/image_stats.py` (Laplacian variance, busy 16 px blocks, Hasler-Suesstrunk colourfulness, saturation p95,
  clipped share; test `test_qa_image_stats.py`). On round 0 it separates the chain at once: Laplacian variance of shot 1..4
  P1 6.8k, 11.8k, 14.7k, 15.6k against 1.7k for shot 0 (P2 the same, P2F ~7k flat, P3 0.7-1.6k), busy blocks 0.81 -> 1.0,
  colourfulness 35 -> 66. P2F already starts 3.8x above shot 0 after one edit pass. Ratios against shot 0 and against the
  same round-0 frame are the metric, never a fixed threshold. Old archives removed from project files after an HF backup
  check (lora_plan_2026-10-22, hybrid_model_2026-10-22).
- 12:45 UTC 2026-10-26 (ვანო 12:33 "yes, rewrite"): the independent round-1 review (`/mnt/project-files/xworld_v2/ROUND1_REVIEW_2026-10-26.md`:
  base-model edits never cut, chained edits fall into noise by shot 3, the 357 cut pairs are the only cut teacher; keep R&M 36 %
  x3, reduced test P3 + P2F, rm-style control, 20-step smoke run) is the base of round 1. `xworld_v2_build.pairs` now keeps only
  the 357 cross-shot pairs and writes each caption in the P2F test form under `rm style` (master sentence, description,
  "Cut to the next shot: <change>", keep line; `cut_caption`, test `test_xworld_v2_rounds.py`). Seen in the real captions: some
  change sentences describe a new place ("the scene shifts to a doorway"), which fights the master sentence "keep its landmarks";
  the cut teaches framing, the place-keeping comes from the pairs where only the camera moves. Not yet decided by ვანო: R&M
  share (25 % x5 or 36 % x3, review prefers 36 %), test size, top-up; no pod before his approval.
- 12:55 UTC 2026-10-26 (ვანო 12:42 "both"): test and training now ask in one form. `xworld_v2_scenes`: P2F = master + description
  + change + keep line (no layout sentence), `P2R` = P2F under `rm style` (does the cut show only under the trigger it is
  trained with?), `ROUND_TESTS` = what a training round draws (P3 seed 11, P2F seeds 11 and 23, P2R tent seed 11 = 46
  pictures, `xworld_v2_scenes.py <scenes> <out> <lora> [weight] round`); `xworld_v2_sheet` shows per row "did the camera
  move? is it the same place?". `xworld_v2_build.pairs` drops the pairs whose change moves to another place (`new_place`):
  357 -> 342, so R&M is 35 % with the new pictures x3. Round-0's P2F text (with layout) was not the same prompt. Free checks
  of the review's question: 270 of 357 change sentences name a camera and 261 a size or angle word. Still open for ვანო: R&M
  share (x3 = 35 %, or x5 = 25 %), test size, seed 23 and the rm-style control (in ROUND_TESTS, +~$0.1 and +$0.1 per
  checkpoint), the top-up; smoke run of 20 steps goes first on the same pod.
- 13:20 UTC 2026-10-26 (OR-24 written; the Opus thread confirmed the round-1 plan 12:52 with three conditions): (1) money cap $5.5
  (80 % = $4.4; the $4.3 estimate would otherwise hit the guard in the last test), the top-up must cover it and is ვანო's;
  (2) `xworld_v2.sh` and `xworld_v2.yaml` are committed now (no longer `.draft`): 20-step smoke run, rounds of 750 steps to 3000,
  a checkpoint every 250, `ROUND_TESTS` after each round, the vault check VT-01 last; (3) P2F/P2R ask "Cut to the next shot: <change
  without its leading Cut to>", the same form as the pairs. Two-trigger answer found in ai-toolkit's source: a process-level
  `trigger_word` is injected into EVERY training prompt (`process_general_training_batch`) and copied onto datasets without their
  own, so `xworld style` would have been put in front of the `rm style` pairs; the config has no process-level one and each
  dataset names its own (`test_reusable_first` now accepts one trigger per dataset, `test_xworld_v2_rounds` pins it). The
  build ran locally on the real data: 210 new + 342 pairs, all captions carry their trigger. Opus thread's stop rule: if at 1500
  no P2F or P2R scene shows a camera move in either seed, stop and show ვანო instead of going on to 3000.
- 15:58 UTC 2026-10-26: OR-25 (ვანო to the planning thread, 15:57): evaluations are always direct; every plan is full scale (starts from the goal,
  lists every path, grounds each in known training methods and the project's goals). Row in docs/ORCHESTRATION.md, line in CLAUDE.md,
  test in `test_agree_every_detail.py`. Also: `runpod create --only <card id substring>` with `--vram` (the creator names the card when
  the cheapest is not his choice) and `per_pod_usd` 6.0 -> 6.9 in `config/spend_caps.json` (his +25 % for the xworld_v2 pod, 13:13-13:42).
- 16:35 UTC 2026-10-26: the P2S reference test is prepared, no spend (the Opus thread's plan 16:17, ვანო's panorama question 16:14):
  `training/pods/xworld_v2_p2s.py` (+ `_sheet.py`, `xworld_v2_p2s.sh`): tent and rome, seed 11, one checkpoint (2250), master only (P2F)
  vs master + one model sheet per person (P2S, three images at most, named by position in the prompt; a fallback to two images is
  logged) x cfg 4.0/2.5 x LoRA weight 1.0/0.7 = 64 cells + 2 masters + 4 sheets = 70 pictures; test `test_xworld_v2_p2s.py`.
  Facts given to the thread: ai-toolkit's `qwen_image_2` arch takes up to three control images (`ctrl_img_1..3`), our drawing script
  (VideoX-Fun `QwenImage21Pipeline`) has only ever been given one; the round tests run at true_cfg 4.0, 30 steps, LoRA weight 1.0.
- 16:50 UTC 2026-10-26 (ვანო 16:39: 3000 test on a separate pod, one scene standard + the methods; the Opus thread's scope): the
  separate pod (`xworld_v2_p2s.sh`, checkpoint 3000) now runs (1) a free look at the pipeline inputs (3 images, depth) ->
  `pipeline_inputs.txt`, (2) the short standard test `xworld_v2_scenes.py ... one` = tundra, P3 seed 11 + P2F seeds 11 and 23,
  (3) P2S on tent and rome at LoRA weight 1.0, cfg 4.0 vs 2.5 (the 0.7 axis dropped: the aim is the best way, not a comparison;
  32 cells), (4) S2 `xworld_v2_s2.py`: a 2x2 storyboard grid per scene, cut into panels (gutter search), each panel cleaned
  as an edit of itself; the first grid is logged GATE before the clean-ups. Tests: `test_xworld_v2_p2s.py`, `test_xworld_v2_s2.py`.
- 17:10 UTC 2026-10-26 (ვანო 17:06): OR-26 "Opus plans, Sonnet works" (ORCHESTRATION, CLAUDE.md, test). S3 (3D layout) code is
  written from the Opus thread's plan, not from the working session's own design; 2.1 pipeline checked free: `image` is a list of
  any length, no depth/control input (depth would be one more reference image).
- 17:45 UTC 2026-10-26 (OR-26): S3 layout test coded from the Opus plan (`xworld_v2_s3.py`, set files `stories/v2/sets/{tent,rome}.set.json`,
  numpy ray caster, depth S3d and coloured blockout S3b, prompt builder, `spearman`; `test_xworld_v2_s3.py`, 9 tests). Deviations
  from the plan, reported: shots whose camera is a place, not a person (s0, wides) use `cam` {pos, look_at}; a subject camera may
  use `from` (a direction point) next to `side`/`ots`; the pod run uses cfg 2.5 (the P2S winner is not known on an unattended pod);
  Depth-Anything scoring is run after the pod on the saved `*_t.npy` layouts. Pod order: standard -> P2S -> S2 -> S3.
- 17:35 UTC 2026-10-26 (ვანო 17:14 E7-E9, the Opus thread's fixes): P2S, S2 and S3 prompts (not the standard rows) now drop the
  parts the camera cannot see (`xworld_v2_scenes.frame_desc`: close = no footwear or legs, medium = no footwear), add the card's
  "behind" sentence and, in an over-the-shoulder shot, "exactly two people ... seen from behind" (`frame_extras`); collage titles carry
  three more questions (anatomy, background, duplicates). Test in `test_xworld_v2_p2s.py`.
- 18:55 UTC 2026-10-26 (OR-26, the Opus plan S3C_CONTROLNET_PLAN): S3c coded: `xworld_v2_s3c.py` (step 0 LoRA key match with a 100 % stop and a
  with/without-LoRA sample, pass A control pipeline + depth, pass B edit pipeline with master + sheet), pod script `xworld_v2_s3c.sh`
  (reads the P2S master and sheets and the S3 depth renders from HF; vault check at the end), sheets for S3 and S3c, `xworld_v2_s3.score`
  (Depth-Anything V2 Small vs the rendered layout, Spearman, free, CPU). Facts read free: the ControlNet file is 7.55 GB, control branch only
  (`control_img_in` + 16 `control_blocks`, strict=False on the base transformer, so the base LoRA keys should match), `config_path` must be
  qwenimage21_control.yaml. Deviation: the scale sweep (0.6/0.8) is only drawn on one shot per scene because an unattended pod cannot judge
  it; 20 pictures. The pod needs ვანო's OR-23 yes.
- 19:30 UTC 2026-10-26 (3000 test done on pod kohifcge91ujw9, $1.71): S2 wins (a real cut and one place and cast in all four panels, both scenes),
  P2S ≈ P2F (tent cuts, rome does not), S3 as a reference image fails (Spearman of the result equals S1's: rome 0.32-0.52, tent -0.21-0.34; pass bar 0.6);
  collages in project files `xworld_v2/round3000/`. S3c pods 1 and 2 stopped in under 2 minutes: (1) my own mistake, the install block of
  `xworld_v2_s3c.sh` was pasted twice (second `git clone` aborted); (2) step 0 counted the 32 fused `img_mlp.gate_up` layers as unmatched
  although `Loras.gate_up` fills them (the 10-25 lesson): `match_report` now counts a gate_up layer as matched when `gate_layer` and
  `proj` both exist. Tests added for both. Cost of the two failed boots ≈ $0.1.
- 19:40 UTC 2026-10-26 (OR-26, Opus relay 19:20 UTC: test A, eight shots as two grids): `xworld_v2_s2x.py` + `stories/v2/more/{tent,rome}.json`
  (shots s5-s8, text built from the card's cast), grids g1 (shots 0-3), g2t (4-7, text only) and g2e (4-7 as an edit of grid 1's wide
  panel), 2560x1408, seeds 11 and 23, 12 grids; free measures (`measure`: panels cut, grain ratio to g1, faces per panel and cross-grid identity when the
  YuNet/SFace models exist), sheet per scene and seed. Choices reported: grid 1 now also carries the place sentence and the `frame_extras` line
  (the winning S2 grid had neither), and `SHOULDER` accepts "over the X's shoulder" (before, only "over X's"), so rome s4 and the new s8 get the
  "exactly two people" line. Test `test_xworld_v2_s2x.py`. No pod until ვანო's OR-23 yes.
- 20:30 UTC 2026-10-26 (OR-26, the Opus plan STRATEGY_LOOP_PLAN): round 0 of the strategy loop, free part coded: `xworld_v2_loop.py` (row registry S1,
  S2T, S2E, S3cA, S3cAB, M2, M4, M5, M3; round config with ONE change per row refused in code; round 1 = 68 pictures; the 2x2 depth control canvas and
  the M4 in-paint canvas; M5 `reproject` of the master into a new camera; frozen-plate SSIM, landmark order match, grain bar, shot pass rule,
  attribution in the plan's order, the stop rule, attribution.md) and `test_xworld_v2_loop.py` (13 tests). The s0 agreement measure found the two
  set files off the masters (tent: general 0.11 and entrance 0.08 of the width too far right; rome: legionary 0.37, counter 0.1, baker not
  in the picture): the sets were moved to the masters' landmark positions (`sets/*.marks.json`, read by eye from the masters), both agree
  now. S3 depth maps already on HF (used by the running S3c pod) come from the OLD sets, so S3c answers for those; the loop's rounds use the new ones.
  Not yet written: the pod-side runner of the rows (needs the S3c numbers and the M4 in-paint call of the control pipeline `image` + `mask_image`).

## 2026-10-26 20:25 UTC (23:25 Tbilisi): S3c verdict, mannequins, loop round 1 prepared (no pod yet)

- S3c (depth ControlNet, 8 shots, scale 1.0): geometry follows the depth (Spearman rome 0.54-0.89, tent 0.35-0.65 against S1's -0.21..0.52), but each frame painted alone loses the xworld style and the faces, the sphere heads read as giant hats/bowls, and pass B restores no identity (tent s4 0.65 -> 0.22). ვანო: "meaningless, crumpled, not connected". Cost of the S3c pods about $0.96 with the two failed boots.
- Opus plan section 8 (`/mnt/project-files/xworld_v2/STRATEGY_LOOP_PLAN_2026-10-26.md`): depth control is tried only inside the grids (M2E50, M4E50 = control ended at 50 % of the steps; M4 full as one tent diagnostic), next to S2T and S2E; S1 = the existing P2S pictures; new FAIL rule "connected" (face similarity across the panels at least S2T's).
- 3D code (`xworld_v2_s3.py`): people are mannequins (torso to the shoulders, neck, head sphere 0.11 m), the near figure of an over-the-shoulder shot is cut at the shoulder (`cam["cut"]`), the Rome fountain is a stepped basin (`shape: basin`), close-ups are head and shoulders (0.7 m frame, was 0.45 m: the sphere filled the frame). The old close-up test (head 35-60 % of the frame) now pins 25-45 % for the new framing; new tests for the head share, the cut figure and the basin.
- Loop (`xworld_v2_loop.py`, `xworld_v2_loop_run.py`): rows `M2E50`, `M4E50` (`ControlEnd` zeroes `control_context_scale` in the transformer kwargs after half the calls and logs whether the kwarg was seen), `row_scenes`, `connectedness`, `connected_ok`, `style_ok` (compose/style_score stands in for CSD, bar S2T - 0.05); `load_control_pipeline` disables the VAE tiling (tear suspect, logs the previous state). Round 1 config `loop/round_1.json`: 9 grids + 2 M5 pictures, seed 11. Pod script `xworld_v2_loop.sh`.

## 2026-10-26 22:10 UTC (02:10 Tbilisi 10-27): loop round 2 running, factor cells, held-out places, round 3a code (OR-26, Opus plan sections 9-13)

- ვანო (21:58 UTC): every action must fit the general logic of places and people, not the few frames at hand; the whole remaining balance goes to the
  360-degree coordination goal; the Opus thread decides the spend. Held-out places: `stories/v2/heldout/ship.json` (cards, other kind of place than
  the tuned ones) and `sets/ship.set.json`, `sets/tundra.set.json`; `load_scenes` reads them, and a test bans every scene word from the method code
  (`xworld_v2_loop_run.py`, `xworld_v2_cells.py`, `xworld_v2_dirs.py`; the words come from the set and card files only).
- Round 2 (pod w4f1yaxxidnotl, H100 NVL $2.59/h, caps $1.95 / 1.2 h): rows M6, S2Tp, S2Ep, S2L on tent and rome, seeds 11 and 23. M6 `fill survived`
  0.003-0.013 (the noise fill did not leak the old fill). A detached guard was killed by its 30 min background limit and restarted with a 2 h limit.
- Factor cells (`xworld_v2_cells.py`): a row name `X_<canvas>_<reference>_<layout>_<prompt>` is a combination of factors; the L16 half fraction is
  orthogonal (test); S2Tp is the cell `X_g_n_0_0`. New optional factor E (`+dir`, `+sk`, `+dsk`): the direction views, the line sketch, both.
- Round 3a code (`xworld_v2_dirs.py`): the TURNAROUND row (the EMPTY place from four directions around the master camera, words from the set's ray cast),
  the line SKETCH canvas (outlines with names, stick figures with names, same 2x2 order), the shaded colour PLATE of the empty set; rows PO55/PO70
  (SDEdit paintover: the plate noised to the sigma of a shortened schedule and denoised with the LoRA, then the people added by the edit pipeline with the
  sheets and their ray-cast position in words); job `stages` (the money cap cuts the end), `last_scenes`, `ensure_assets` (master and sheets of a
  held-out place). Test `test_round_3a_extras_turnaround_sketch_paintover`. Deviation from the Opus plan 13: no VLM is on the pod, so the turnarounds
  are not checked or redrawn there (checked by eye afterwards), and both candidate cells are drawn on the held-out places (the pick is offline).

## 2026-10-26 23:15 UTC (03:15 Tbilisi 10-27): round 3a results, view-by-position bug, round 3b (OR-26)

- Round 3a (pod lmeb5qu5gdak0o, RTX PRO 6000 $1.69/h, stopped at about $1.0 of the $2.05 cap on Opus's word): TURN views are coherent in tent, rome, ship, tundra
  (landmarks keep their order around the circle). The `+dir`/`+dsk` grids COPY the turnaround picture panel by panel: the background is consistent across
  the four panels, but the view is chosen by the panel's position, not by the shot camera's yaw (code-class cause, `attribution.md`). Ship base and ship `+dsk` are coherent.
- Paintover PO55/PO70 failed on the pod: the 2.1 VAE takes RGBA, the plate was encoded as RGB. Fixed in `sdedit` (RGBA, latent channels from the encoder output).
- Round 3b (`loop/round_3b.json`, stages PO smoke, `+dpl` tent/rome, `+dpl` ship/tundra, PO tent/rome/ship, `+dpl` seed 23): new cell `X_g_n_0_0+dpl`;
  `xworld_v2_dirs.plate_grid` cuts the turnaround picture into one EMPTY backdrop per panel by the shot's view index, yaw offset, pitch and field of view
  (`_crop_box`); `plate_words` keeps the backdrop and adds the people. The turnaround pictures come from HF round_3a (no redraw). Test `test_round_3b_backdrop_per_panel_and_config`.
- 23:30 UTC: cap raised on the creator's delegation, ვანო 2026-10-26 21:58/21:59 UTC (all remaining balance for 360° coordination), decided by the Opus thread: `config/spend_caps.json` runpod_usd 29.0 -> 31.0 (the 80 % stop sat below ledger + round 3b's pod); no new money, the real limit stays the balance minus the 0.25 floor. Round 3b first try (pod 9twmhywjhuu5s4) cost $0.06: the pod refused a config with cause "bug"; fixed, `check_round` now in the test.

## 2026-10-27 01:10 UTC (05:10 Tbilisi): round 3b results (pod r4w729gcrlx4wv, H100 NVL $2.59/h, 23:36-23:56 UTC, ≈$0.85; balance $0.49)

- Out on HF `lora_plan_2026-10-26/train_xworld_v2/loop/round_3b/out/loop/{TURN,X_g_n_0_0+dpl,PO55,PO70}`; sheets (left the turnaround, right the +dpl grid) in `/mnt/project-files/xworld_v2/round_3b/`.
- `+dpl` (one empty backdrop per panel, cut from the turnaround by the shot's yaw): tent, ship, tundra keep their landmarks and the order of them in all four panels (tent: lantern pole, table, bed, door; ship: mast, crates, wheel, lighthouse; tundra: rock, river, mountains); rome keeps the street, balconies and Colosseum in 3 of 4, the wide panel shows a larger Colosseum than its plate. Seed 23 drawn on tent/rome/ship (not yet looked at one by one).
- Paintover PO55/PO70 ran, but the drawn picture does not follow the plate (new street, new tent), the people panel s4 comes out as the unpainted plate with mannequins. Paintover is rejected.

## 2026-10-27 03:30 UTC (07:30 Tbilisi): code work after round 3b (Opus list, no pod, no money)

- TURN views: `xworld_v2_dirs.view_prompt` (one prompt per yaw: landmarks left to right and what must NOT be visible, both from the ray cast), four draws composed by `compose_turn`, `view_checklist` json beside the grid; `prompts(sc, "TURN", view_index)`.
- Backdrop per panel: `reproject`/`plate_view`/`plate_grid` read the turnaround along the shot's own yaw, pitch and field of view; a shot between two views reads both with an 8 degree soft seam (`view_weight`). Limit: a pitch beyond the turnaround's 52 degree vertical view smears.
- People: `people_rule` (exactly N people, names, the person seen from behind appears once, from the set's `ots`) in `plate_words` and the paintover people prompt.
- SDEdit: `start_noise` pins the shifted start sigma to the scheduler's formula (strength 0.55 = noise 0.79); the unit test does not show the math wrong, PO stays "untested". Test `test_round_3c_view_prompts_reprojection_people_rule_and_sdedit_noise`; attribution in `/mnt/project-files/xworld_v2/round_3b/attribution.md`.

## 2026-10-29 07:40 UTC (11:40 Tbilisi): every branch and PR into main, OLD_HISTORY.md (no pod, no money)

- ვანო (2026-10-29 07:03 UTC): analyse every branch and PR, settle conflicts for the newest findings, keep only `main` with
  0 open PRs, save everything worth remembering in one file. Analysis: all 28 remote branches were already ancestors of
  `claude/project-thread-beg7xa` (PR #22, settled 2026-10-25 in `docs/research/BRANCH_INTEGRATION_2026-10-25.md`), and
  `main` (PR #26) was too, so PR #22's tip goes to `main` without a conflict.
- `OLD_HISTORY.md` (repository root): the merge record of both repositories, the rules in force (RULE #1-#6, D-73..D-80),
  the state of the strategy loop (3b +dpl best, gallery https://claude.ai/artifact/C5TMq1VZsAPF7FqvNXb6zA), the HF and
  project-files material by path, the old threads, the full project memory and the project-files listing. No binaries.
- tmr-video-script-engine: PR #9 and #10 merged into its main (PR #11; `cloud/rp.py` keeps both `--gpu a5000` and
  `--gpu big`); PR #4 and `three-hour-format-7ewyz0` closed as superseded (kept in the HF vault bundle).
- Tests: `pytest -m "not system and not media"` 1218 passed; `docs_lint` 0 findings; tmr `tests/unit` 709 passed.
- From now on new work starts from `main` (the `systemic/next-video` working branch is retired by this request).

## 2026-10-29 19:00 UTC (23:00 Tbilisi): P1a, RunPod stop paths that always fire and never kill a healthy pod (no pod, no money)

- Blueprint v2 phase P1a (PR #29). Design in [CLOUD_RUNBOOK](CLOUD_RUNBOOK.md) (CR-01..CR-16, new ID family `CR`); the evidence is
  `blueprint_2026-10-29/recheck/verify_runpod.json`: the EXIT trap of `self_stop_sh` was never installed (only its first line was
  used), the guard stopped healthy script pods through `jobs.stall` + a vacuous `safe_to_release`, the heartbeat was optional, upload
  failures were swallowed, the watchdog hid its own failures, the hooks failed open.
- `cloud/pod_wrapper.sh` is now the start command of every script pod (`runpod.script_cmd()`; the job's URL, money, lifetime and HF
  folder arrive as `EE_*` env, `wrapper_env`). It owns the GPU check (BAD_HOST), the key boot-probe (line 1 of beat.txt), the 5-minute
  upload loop with a failure counter, the money dead-man (`deadline_of`: created + min(lifetime, max_usd / (price + disk)) - grace),
  the end word (DONE / FAILED / FAILED_UPLOAD / CAPPED / BAD_HOST), the final upload + verify with a bounded retry and the stop (v2
  action, then GraphQL; no v1 route). `lint_pod_script` now refuses a script that writes beat.txt or an end word, idles, touches CUDA
  without `timeout` or sends weights into the output folder; the old own-loop rule survives as `lint_own_upload_loop`.
- `create` refuses a script pod without a heartbeat, and without a stop path outside the session (restricted in-pod key OR a watchdog
  run in the last 60 min), writes the live record `runpod/live/<pod>.json` to the vault dataset (`cloud/hf_live.py`) before the POST and
  drops it when no pod is made. The guard lives by the HF beat for script pods (REST view no longer drives a stall); progress frozen
  under fresh beats = STALLED, then stop at twice the limit (`# stall-minutes: N`); failing uploads push and never stop while files are
  unstored; FAILED_UPLOAD / BAD_HOST put the job into RECOVERY_REQUIRED.
- Watchdog: cron every 10 min, reads the live records and beats (DONE / FAILED / CAPPED / money estimate -> stop), writes
  `runpod/watchdog.json`, closes records of gone pods, writes the job summary; no masks (a missing key, a failed stop and a lost push
  are red). Hooks: the Stop hook refuses to end a turn when the check cannot run and a known pod is live; TMR `rp.py` is an allow-list.
  Pushes are recorded in `tools/runpod/notify.jsonl`; `check` reports a lost push or a missing topic while a pod is live.
- Tests: `test_pod_wrapper.py` (the real wrapper under bash with stubbed curl/nvidia-smi/uploader), `test_cloud_stop_paths.py` (criteria
  c, d, f, g and the create refusals), conftest isolation of `tools/runpod` (CR-16). Changed on purpose: the lint tests of the old rule
  now call `lint_own_upload_loop`; `test_a_pod_script_that_idles...` no longer expects `dead_man_sh` and the dead trap (replaced by the
  wrapper tests); the watchdog cron test expects */10. The old training scripts under `training/pods/` write their own DONE and are
  refused at the next `create` until P1b rewrites the ones that are reused.
- Open for the creator: GitHub secret `HF_TOKEN` (write on `vano1919/tmr-artifacts`) for the watchdog; balance is $0.40 so P12a waits for a
  top-up. Unproven until P12a: the wrapper as container command on RunPod, the real uploader in `ee_upload`, the in-pod key's stop right.
- P12a drills (CR-17): `runpod create --drill no_self_stop|drop_key|upload_fail` (refused unless the ledger meta says `test=p12a_smoke`),
  `--pass-s/--upload-grace-s/--cap-grace-s` into the pod env, `EE_DEADLINE` exported to the job script; `self_stop` says so and returns when
  the pod has no key. Tests in `test_pod_wrapper.py` and `test_cloud_stop_paths.py`.
- P1a cross-review fixes (PR #29): the watchdog ignores a beat that is not this pod's (BOOT `pod=`, or newer than the record) so a retry is
  not stopped by the last run's FAILED; a loop upload pass verifies only settled files and never `beat.txt` (the end sequence still verifies
  all) and the verified time is the pass start; the hook refuses TMR `rp.py` sub-commands outside the allow-list however it is launched;
  `EE_PRICE` is the card ceiling; `upload_fail >= 6` with unstored files moves the job to RECOVERY_REQUIRED; a guard stop with unstored
  files does the same (CR-11). Tests for each.

## 2026-10-29 22:30 UTC (02:30 Tbilisi): P0d Claude API client (no real call yet, no money)

- ვანო 2026-10-29 18:58 UTC: Claude API key in the env file, use the credit fast. Plan `CLAUDE_API_PLAN_2026-10-29.md`; OR-24 verdict
  with changes `CLAUDE_API_PLAN_OR24.md` (cache-write and web-search prices, no fallbacks on Batch, explicit effort, no 400 parameters,
  secret refusal, ledger as the only meter, read-only repo tool loop).
- New: `explainer_engine/llm/claude_api.py` (routing by class from `config/model_routing.json`, prices from `config/llm_prices.json`, response
  cache, job ledger plus `calls.jsonl` with start/done/void lines and gap stop, Batch API from 20 requests, `fallbacks: "default"` on direct
  calls, Fable 400 -> declared fallback route, overload wait 15 min, secret refusal, `list_dir`/`read_file`/`grep` tool loop), CLI
  `estimate | run | status | void`, `docs/LLM_API.md`. `config/spend_caps.json` got `claude_api` (95 total; J1 10, J1b 8, J2a 8, J2b 10, J3 12,
  J4 5, J5 3, J6 15, reserve 24; approval = the OR-24 verdict). `anthropic>=2.3` in requirements.
- Test: `tests/unit/test_claude_api.py` (fake client): 51 passed, 1 skipped until `config/model_routing.json` (PR #30) is on the branch.
  The key was ABSENT in the thread that built this (environment started before it was added): no real call was made.
- Next: J1 (`review/pr_review.py`) on PR #30, #31, #29 once the key is present in an environment.

## 2026-10-29 23:00 UTC (03:00 Tbilisi): P0d review fixes (PR #34, REQUEST_CHANGES by the P0a thread)

- F7: the repo tools resolve every path first and keep it inside the checkout; `grep` and `list_dir` skip symlinks (an `os.walk` without links), `.env*`, `id_rsa`,
  `.netrc`, `*.key`, `tools/`, `.git`, and `..` paths are refused; the key patterns now cover AWS, Bearer, `github_pat_`, `sk_`, `sk-proj-`, Slack, `*_KEY=`/`*_TOKEN=`/`*_B64=`
  assignments. The long-input regex backtracking was removed (a 30,000-character prompt took 21 s).
- F8: price lines for the fallback targets (Opus 4.8, Opus 5, Sonnet 5); every `usage.iterations` entry priced at its own model, the ledger books the larger of the sum and the
  top-level usage; a paid call whose model has no price gets a `done` line at the reserved amount. `void UID` defaults to the reserved amount; `run` refuses a job whose worst
  case passes the job's 80 % stop; a batch rerun that truncates no longer drops the other results; the first message of a tool loop (the diff) is cached across turns.
- Tests: 28 new cases in `tests/unit/test_claude_api.py` (79 passed, 1 skipped).

## 2026-10-29 22:50 Tbilisi: P0b, the code guards of the Blueprint plan (no pod, no money)

- ვანო 2026-10-29 18:19 UTC "დაიწყე", 18:25 (usage rule), 18:27 "კი" (Opus designed, Sonnet 5.5 high implemented, OR-26). Design: `blueprint_2026-10-29/P0b_DESIGN.md` in the project files.
- `config/model_routing.json` (D7): models, the 18 task classes of MODEL_ROUTING v2 part 4 (D6), the pair of every agent, critics, spawners, the Fable
  story-stage flag (off), escalation numbers, owner categories, protected files, usage line. `explainer_engine/governance/`: `hooks.py`
  (pre-bash, pre-write, pre-agent, post-edit, pre-switch/post-switch, prompt, stop, stop-failure, statusline), `records.py` (the creator's word
  in `jobs/creator_ok.jsonl`), `status.py` (phases, cards, routing log, generated STATUS), `usage.py` (OR-30 backup), CLI `python -m explainer_engine.governance`.
- Hooks wired in `.claude/settings.json` next to the money hooks (D-56): force push / `branch -D` without a `backup/*` tag, `engine/`, protected config,
  `*.py` at xhigh/max, Fable outside the story stages, critics off Opus, model switch without his word, findings after every edit, the Stop check of a
  done phase (routing_log line, files, PROGRESS entry, listed tests). All fail open on a broken check.
- All 15 agent files declare `model:` and `effort:` (6 had none; stage pages got `effort`); both critics are `Read, Grep, Glob` (D-84): `script-critic` lost
  Bash, `lora-checkpoint-judge` lost Bash and Write; the orchestrator and the coordinator run the tools and pass the output by path.
- `core/ledger.Attempts` (OR-04): attempts 1-2 at the assigned level, the 3rd only escalated, then NeedsReview. Docs: OR-28 (halt and ask), OR-29, OR-30; D-81, D-83,
  D-84; UD-01..UD-10 table; `UD` home in `docs_lint`; `docs/blueprint/` (phases.json, decision_queue.json with owner on every card, routing_log.jsonl,
  generated STATUS.md). The usage rule (95 %): the status line is the only source of percentages; cloud threads see `allowed_warning` in `get_session`.
- Tests: `test_agent_governance` (27), `test_governance_hooks` (23), `test_decision_queue`, `test_routing_log`, `test_attempts`, `test_usage_backup`,
  OR-28 in `test_agree_every_detail`; `pytest -m "not system and not media"` 1292 passed; `docs_lint` 0 findings.
- Not enforceable, stated: the halt itself and the S0-S4 classification (words only); run-folder scoping of critics; that the recorded word quotes
  a real message; that `PreModelSwitch` fires for the hearth switch tool and that `Agent` events carry `model` (unverified, the tools also refuse alone).

### P0b review round 1 (cross-review of PR #30, fixed in the same PR)

- Blocking 1: `PreModelSwitch` carries `source`; the creator's own `/model` and picker (`command`, `picker`) now pass, an `sdk` switch (the hearth tool, Remote Control) still needs his recorded word.
- Blocking 2: the force-push guard strips `refs/heads/` and resolves `HEAD`, so `HEAD:refs/heads/main` no longer slips past.
- Cheap items taken: commands are tokenised with `shlex` (commit-message text is no longer a command); protected-file guard sees `perl -pi`, `sponge`, `Set-Content`, Windows paths and a copy onto the file, and no longer refuses reads; a wildcard word never unlocks a protected file; the backup keys a window without `resets_at` by time bucket, never commits credential-like files, and writes a generic trailer; switches are logged to untracked `jobs/switch_log.jsonl` with the message id; a critic spawned without a model is checked against its agent file; `Attempts` numbers come from `config.escalation` in the CLI; `.claude/settings.local.json` is gitignored; limits stated in OR-29.
- Not built: the frontmatter re-check inside `pre-agent` (`test_agent_governance` already pins every agent file).
- Follow-up from the re-review (APPROVE): the git parser skips wrapper commands (`sudo`, `env`, `timeout 60`, `nice -n 5`, `nohup`, `command`, `time`...), so `timeout 60 git push --force origin main` is refused; tested. `bash -c "git push -f ..."` is read too (the quoted script is parsed as commands).

## 2026-10-29 19:00 UTC: P0a repo hygiene (blueprint v2, no pod, no money)

- D2 (ვანო, 2026-10-29): `.chatgpt/` deleted (16 files: a 2026-10-18 copy of `.claude/` plus ChatGPT rules; the
  editorial-critic agent/skill and rules stay readable in git history before this commit). The editorial gate code
  (`production/editorial_gate.py`, OR-10) is untouched.
- Superseded banners: `CHATGPT.md`, `docs/CHATGPT_WORKFLOW.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/PIPELINE_ARCHITECTURE.md`;
  `README.md` and `docs/INDEX.md` no longer point to `.chatgpt/`; `quality.yml` lost the `chatgpt/**` trigger;
  `requirements.txt` lost the kokoro-onnx line (D-39, narrate.py is a legacy path) and the Remotion comment;
  `docs/EDITING.md` ED-09 points to `production/graphics.py` (`production/cards.py` was never built).
- `audio/visemes.py` and `audio/timings.py` stay (provenance ports; `timings` is imported by `audio/narrate.py`).
- Test: `tests/unit/test_repo_hygiene.py` (no `.chatgpt/`, no CI trigger, visemes importable, retired deps absent).

## 2026-10-29 Tbilisi night: agent form A/B, one main agent vs one worker per stage (P0c, free)
- Same Napoleon-vs-Genghis brief (8 segments, 3 Shorts, stages 1-6 of the story engine) written two ways by Sonnet: arm A one
  agent in one context, arm B 22 fresh workers with a gate after each return. Both reach `story_lint` 0 FAIL / 0 REVIEW.
  Whole-script `production validate`: A 28 FAIL (all media and creator gates) / 60 REVIEW, B 27 FAIL (13 script defects) / 133 REVIEW.
  Cost equal within 1 %. Blind Opus critic, mean of its six criteria recomputed: one context 4.00, workers 3.83 (noise-level on one sample); workers better at line level.
- Findings: the workers' hand-off fields (hero face sheets, a dialogue scene header, delivery tags) surfaced only at the editor
  stage; `stage_guard` `SEG_STORY` lacks `scene` (architect corrections are rejected; not fixed here, no code in this phase);
  `production validate` cannot reach the beat checks before `voice`/`shots` exist; claim-id format `C-NN` vs the map's `C##`.
- Evidence (not a decision) recorded in `docs/research/AGENT_AB_2026-10.md`: the evidence does not support the per-stage worker form as the A5 answer; D-79 stays the
  default; the long-context argument (16 segments, cheaper model for mechanical stages) is untested. Data, snapshots and
  `measure.py` in `docs/research/agent_ab_2026-10/`. No paid call. Decision log unchanged (the decision is the creator's A5).

## 2026-10-29 22:45 UTC: P3b craft curriculum, sub-step 2 (blueprint v2, no pod, no money)

- The professional craft of nine departments in the repository's three layers: skill pages (extended `narration-script`
  AI register, `editing-style` sound design, `video-editing-architect` editing/colour and motion graphics with Mayer's
  principles, `shot-visuals` shot grammar and lanes, `elevenlabs-voice` casting and performance, `shorts-for-video`
  packaging; new `cartography` and `animation-principles`; a pointer in the `performance-director` stage page), one
  checklist per department `explainer_engine/standards/craft_checklists/<dept>.json` (102 CRAFT- rows in the shape of
  `training/video_criteria.json`, each with its kind, artefact field, sourced rules, source and enforcement; rendered into
  its skill's CHECKLIST table), and the index [CRAFT_CURRICULUM](CRAFT_CURRICULUM.md) with the 13 Blueprint conflicts
  (creator decision pending, the rule in force stays) and the 17 areas.
- Registry: BP-114..138 added, all **hypothesis, REVIEW** (no rule has two verified source types; sources only from
  `docs/research/CRAFT_SOURCES_2026-10.md`, numbers no opened source supports cite "Blueprint 2026-10 (unverified)");
  each names its checklist row in `enforced_by` and the validator still to be written in `planned` (P3-P10). The
  dramatisability caps (BP-127) are the Blueprint's house numbers, not McKee's or Katz's. No existing threshold changed;
  the conflicting Blueprint numbers (-16 LUFS, 135-145 wpm, 3-5 dB duck, 0.18 eye trace, 2.0-3.5 s window, 24 fps,
  250/480/240/60 safe zone) are conflict records only, not registry entries.
- Tooling: `explainer_engine/standards/craft.py` (`check`, `write`: integrity and the rendered copies; judges no video).
- Test: `tests/unit/test_craft_checklists.py` (shape, unique ids, sources and enforcement, BP ids exist, skill tables and
  the curriculum index equal the JSON, one home per CRAFT id, 13 conflicts and 17 areas listed, the conflicting rules keep
  their numbers).
- Merge of main with P3b (#36): the Lock 5 test of `test_agent_governance` exempts only a backticked reference directly followed by `(planned, Pn)` (regex, the phase must exist in `docs/blueprint/phases.json`); everything else on the line is still checked.
- P1a second review: the `rp.py` hook inverts its rule: any segment that does not start with a reader/editor and runs `rp.py` with a sub-command outside the allow-list is refused, whatever launches it (timeout, env, FOO=1, nice, stdbuf, watch ...); `diff a/rp.py b/rp.py` and `open('cloud/rp.py')` are no longer refused. Tests extended.

## 2026-10-29 19:20 UTC (23:20 Tbilisi): Blueprint P2, the data contracts (no pod, no money)

- ვანო (2026-10-29 18:19 and 18:30 UTC): start phase P2 of the Blueprint plan v2 and carry it through the night. Design by the Opus
  pass, code by the Sonnet pass from `blueprint_2026-10-29/P2/P2_IMPLEMENTATION_PLAN.md` (OR-26).
- `docs/CONTRACTS.md` (new home, prefix CN-): 15 contracts with writer, reader and hand-or-derived; CN-01..CN-14; the lifecycle
  with gates #1-#4 and eight named back paths. Schemas in `explainer_engine/schemas/`: job_manifest, script_variants,
  screenplay_spine, voice_casting, audio_spine, sound_mix_manifest, visual_comp_manifest, scene_set, shot_spec, pod_heartbeat,
  edit_and_grade_manifest, qa_report, editorial_review/3, distribution_package; `film_shots/2` added to film_shots.schema.json
  (`/1` documents validate unchanged).
- Code: `core/contracts.py` (schema + semantic checks + derived freshness, CLI `check`), `core/store.EpisodeJob`
  (`job_manifest/1`: only the next state, approvals per gate, dossier hash fixed once, no cross-job artifacts, abort/reopen,
  adopt), `core/shot_cache.py` (SHA-256 of the shot spec without paths). `core/ledger.py` unchanged: it already holds pod and API
  money in one run.json; `test_one_ledger` pins it. `training/cast/sheet.py` no longer writes the bfl cap as a number.
- Decisions: D-85 (episode fps = LTX native 24, measured on six clips; assemble and Shorts at 30 follow in P7/P9). BP-139 (8k+1,
  /32, two-stage /64, at most 257 frames; hypothesis, so REVIEW). AUDIO_TIMED comes after SAMPLE_APPROVED (the read is paid, OR-19).
  `sourced_rules.level()` caps a hypothesis at REVIEW; `enforced_by` of 9 rules completed (the sync test found them).
- Tests: `test_contracts`, `test_lifecycle`, `test_shot_cache`, `test_one_ledger`, `test_spend_caps_single_source`,
  `test_sourced_rules_sync`, `test_validator_severity_tiers` (0 FAIL-on-hypothesis found in the code today); fixtures in
  `tests/fixtures/contracts/`.
- Review fixes (cross-review of 2026-10-29 22:23 UTC): `EpisodeJob.adopt` now goes through the state's gate (CN-04/CN-06), refuses terminal
  states and names the dossier; creator and planner approvals of a gate must bind a non-null sha256; CN-14 compares
  `source_episode_sha256` with the job's `assembled_video`; `film_shots/1` refuses the /2 fields; a cached render and the repo's
  `assets/` may be recorded as artifacts but not any path that merely contains "assets"; the cache key treats `1` and `1.0` alike;
  BP-139 is read by literal id and listed only where it is read (`test_bp_139_is_listed_only_where_it_is_read`).
- Second review round (22:45 UTC): `adopt` takes `approvals` for EVERY gated state up to the target (a machine approval of STAGED_UNLISTED
  no longer skips the creator's REVIEW_APPROVED), hashes the dossier file, checks the reservation past BUDGET_RESERVED, never adopts into
  PUBLISHED_PUBLIC or a terminal state; `create` makes only CREATED.

## 2026-10-30 UTC: Blueprint P3, script spine, variant planner (stage 1b), register lint (no pod, no money)
Design: `blueprint_2026-10-29/P3/P3_DESIGN.md` (Opus thread); this entry grows one line per commit. A5 stays provisionally D-79: the D-79 branch is built.
- `stage_guard`: the architect owns the dialogue segment's `scene` header (P0c finding; `test_stage_guard_lets_the_architect_correct_a_scene_header_and_nobody_else`).
- Rules and docs first: BP-140 (house FAIL: the AI-register word tier, 75 listed forms of 32 words and the Additionally/Moreover/Furthermore openers, `checked_on` 2026-10-29, recheck 180 days; the creator's 09:28 wording is quoted from the plan card because his exact words are not in the repository), BP-114 becomes the soft tier (27 words, 68 phrases, the densities per 1,000 words), BP-141 (profiles A-D, hypothesis), BP-142 (every turn is a played scene, house FAIL), BP-143..146 (ad-safety window, double exposition, "and then" chain, drift; hypotheses). `revolutionary` and `boasts` are in the soft tier, not tier 1 (Napoleon's own period; a hero may boast). `sourced_rules` accepts a dict threshold. Docs: ST-20..ST-24, the RG rules (STORY_ENGINE), the VP checks and ZI-07..ZI-10 (SCRIPT_ENGINE), OR-31 and OR-32, PV-61, KP-46, D-86; `RG` and `VP` join the docs_lint homes.
- `scripting/syllables.py`: `count` (the one syllable counter; `production/validate.syllables` delegates) and `seconds(text)` = a read-time estimate at BP-01's pace with the shape (syllable weight, sentence and clause pauses) fitted on the two committed Scribe reads (stone_age day1_v2, day1_v5); the Kokoro (day1_v1) and local-Whisper (titans, syndicate) timings are skipped by their `source`. `syllables_calibration.json`; `test_syllables`. The committed reads were heard at 122-155 wpm against BP-01's 170: recorded, no change proposed (P4).
- `scripting/register_lint.py` (RG-01..RG-05) and its call sites: PV-61 (`validate.check_script`, hero lines words and phrases only, narrator lines also densities and openers; `register_allow.json` next to the script), N-16/N-17 in `narration_lint.lint` (the text path before any paid read; a production script passes `register=False` because PV-61 covers it), KP-46 in `film_shots.check`. BP-114 and BP-140 name the module in `enforced_by` and drop `planned`; `test_craft_checklists` now requires one checklist row plus existing readers for an implemented rule (no row removed). Baseline: 0 RG-01 on all 5 committed production scripts and the Napoleon draft; one REVIEW on stone_age week1_v1 (3 triplets in 557 words). `test_register_lint` (25 tests).
- `story_lint.script_checks`: ST-20 an and-then chain (BP-145), ST-21 double exposition (narrator line repeating the adjacent hero line, `story_lint.overlap` against BP-144, shared with KP-20 in `film_shots`), ST-22 graphic violence inside the first 7 s (BP-143), ST-23 a twist line over BP-115's estimate (`syllables.seconds`), and the BP-135 first-packaging-promise check under ST-01. All REVIEW (hypotheses, D-59). `tests/unit/test_story_lint_p3.py` (6 tests).
- `scripting/variant_plan.py` (stage 1b; VP-01..VP-18, ST-24), `script_variants/2`, `config`-free cost model. `dynamics` is the one function that counts lane shares, runs, rotation, turn coverage and the narrator share (words when the blocks carry them, else the unplayed seconds); `checks`, `lane_findings` (the `LANES` table, one VP-11 per missing lane naming its phase), `cost` (rows `pod`/`api`/`cpu`/`voice`; planned = base x 1.5, worst = base x 3; a row without a measurement is `unknown` and makes the totals the string `"unknown"`; VP-13 FAILs on the KNOWN part above 80 % of a cap, `ledger.STOP_FRACTION`), `drift` (VP-15: seconds and a 20 % cost drift REVIEW; cost above the approved `usd_worst` FAIL), `score` (100 - 10/REVIEW - 25/FAIL), `brief` (facts only for the Opus thread), CLI `brief|score [--write]|check|napoleon [--write]`. Contract: `script_variants/2` in the same schema file (enum + if/then), VP-01 sums in `contracts.variant_sums`, `contracts.variants_sha256`, `EpisodeJob.move("VARIANT_CHOSEN", variants=<file>)` binds the approval to it (CN-04); the existing `move` calls stay valid because `variants` is optional. ST-24 in `story_lint.turns_played` (template D's rows 4/6/8/10/11/13 only when the script has template D's 16 rows, else the turn functions; FAIL by BP-142, REVIEW by BP-141); BP-141/142/146/135 drop `planned`, BP-105/107/109/127 name `variant_plan.py`, CRAFT-PKG-01 drops `planned`. Napoleon: V1 (profile D) rebuilt from `film_shots.json` = shares scene 0.801 / compensator 0.153 / hold 0.046, narrator 0.449 by words, **0 FAIL, 1 REVIEW (VP-12), score 90**; V2 (profile B, `variant_v2.json`) = scene 0.362 / compensator 0.474 / map 0.158, **0 FAIL, 4 REVIEW (VP-11 MAP, VP-11 COMPENSATOR, VP-12, VP-16), score 60**; `examples/napoleon_vs_genghis/script_variants.json` is rebuilt by `variant_plan napoleon --write` and a test fails when it is stale. Deviations from the design, all minor: (1) the pod price is `MAX_PRICE["default"]` (the creator's ceiling) times hours = `seconds_per_unit` x `margin` / `runpod.SPEED[gpu]` / 3600 (the design divides the price, which is a typo for the time); (2) ElevenLabs credits are `unknown` until `config/job_speeds.json` carries `elevenlabs_usd_per_credit` (the single observed rate is not written into code); (3) the per-24-h pod cap is not part of VP-13 (an episode spans days); only the episode caps and the per-pod cap; (4) `dossier_sha256` of the Napoleon example is the sha256 of its `film_shots.json` (the example has no research dossier); (5) `film_shots.check` does not call `dynamics` yet: a map share needs film_shots/2 lanes (P5). The Napoleon tests pass `speeds={}` so a later `config/job_speeds.json` does not silently re-score the example. `tests/unit/test_variant_plan.py` (28 tests), 4 contract fixtures (`valid_v2`, `invalid__shares_not_one`, `invalid__chosen_without_sha`, `invalid__blocks_not_window`), 2 ST-24 tests.
- `production/compile.py:compile_spine` + `production compile --film-shots FS` (ZI-10): `screenplay_spine/1` derived from the script and its shot cards (segments matched by id, est seconds and clock windows from the shot seconds, the connector from `drama.turn`, claims from `claim_map.md` with E/M = FACT and R/G/I = ALTERNATE, `derived_from` hashes so a changed input is CN-02); ContractError on a missing segment, a stray scene, a claim not in the map, missing promises or profile. `production_script/3` gains the optional `drama.packaging_promises` (exactly 3) and `drama.profile_id` (A-D): additive, every /3 file stays valid, so no version bump (design risk R4). `script_approval` records `promises_sha256` when promises exist and PV-53 FAILs a changed promise. `claims.ROW` accepts `[A-Z]-?\d{2,3}` (the `C02` / `I01` ids of the Napoleon draft; P0c; none of the 3 committed claim maps changes, so the "how many are affected" risk R5 is 0). `tests/unit/test_screenplay_spine.py` (10 tests).
- `scripting/entity_align.py` (`key`, `same`, `heard`) and `audio/scribe_words.align(..., entities=None)`: a name of the script ("Ney") opposite a heard word of the same sound ("Nay") inside an equal-length replace span counts as heard, not estimated, so coverage rises and the times stay what they were; the default call is unchanged. A reduced in-repo key (not Double Metaphone: no phonetic library, design disagreement 3): "Ney"/"Nay" -> `N`, "Subutai"/"Subotai" -> `SBT`; the key is never used outside an aligned span, so the short key `N` cannot match a word the alignment did not already put opposite the name. Not claimed: "Genghis"/"Chengis" (the rules do not reach it). `tests/unit/test_entity_align.py` (5 tests).
- `stage_guard start` / `fresh` (OR-32, the re-read rule): `start` appends the stage, the time and the sha256 of the stage page and its inputs to `<job>/story/stage_log.jsonl`; `fresh` reports an output with no start record, a start older than the previous stage's, a page or input changed since the start, or no output (REVIEW until the creator's A5 card is final; `--strict` exits 1); the old `stage_guard <stage> before after` form is unchanged. First body line of the seven stage pages (architect, scene-writer, beat-writer, performance-director, edit-planner, voice-caster, shorts-writer); story-architect gets step 1b (the variants, OR-31) and step 3 takes the template and profile of the chosen variant; scene-writer runs `register_lint` and the ST-20..ST-23 check; edit-planner follows the chosen variant's lanes (VP-15); script-critic scores each variant's story (`scores.critic`, never summed with the code's) and reads the register report; story-engine skill: row 1b, the re-read rule and "Branch switch (A5)" (D-79 built, D-81 a documented `stage_mode` switch, absent = inline); orchestrator phase 2a; SCRIPT_ENGINE pipeline row 1b; INDEX prefixes RG- and VP-. No new agent page (a new agent needs a protected `config/model_routing.json` edit and the creator's word).
- Open for the creator (none blocks P3; each has the default that was built): (1) the exact 09:28 UTC wording for BP-140 and BP-142 `decided` (the registry quotes the plan card's summary and says so); (2) which words are in the FAIL tier (the 75 forms of BP-140; "revolutionary" and "boasts" are not in it); (3) whether an and-then chain in the text should FAIL (built: REVIEW, ST-20; the declared connector is already a contract FAIL); (4) whether ad-safety FAILs and whether the window is 7 s (YouTube's wording, built) or 8 s (the card); (5) style devices (contrast pairs, question-answer chains, fragments, em dashes: built as densities, REVIEW); (6) the score formula on the card (built: 100 - 10 per REVIEW - 25 per FAIL, next to the critic's, never summed); (7) a separate `variant-planner` page (built: none). Waits for the creator (V4 pilot, OR-15, OR-17): the rewritten Napoleon script and its approvals; the unattended subset (V1/V2 `script_variants.json`, lint baselines) is built and tested.
- Review follow-ups (P2 thread's verdict on #40): the register allow-list now reaches every call site, not only PV-61 (`narration_lint.lint(allow=)`, `film_shots.check(allow=)`, both CLIs load `register_allow.json` next to the file), so a literal "realm" is exemptable in N-16 and KP-46; `chosen.variant_id` must name an existing variant and one without a FAIL (`variant_plan.check_file`, CN-04), and `EpisodeJob.move(variants=)` refuses an id that is not a variant. Tests added in `test_register_lint` and `test_variant_plan`.

## 2026-10-30 03:50 UTC: Blueprint P4b, the voice director (free, no pod, no paid take)

- ვანო (2026-10-29 18:17 and 18:30 UTC): D8 conditional (a free generator only if a measured one is good and diverse enough; the
  narrator stays on the ElevenLabs connector, so the REST client of the plan card is dropped) and "assume yes up to paid".
  Phase P4b of Blueprint plan v2, after P2 (#31).
- `audio/voice_audition.py` (new, the one place a voice is measured; P8 and P12b import it): eight measures from one free listening
  (library preview or a held read): median pitch and range, pitch variation, emphasis, pace (wpm with the text, else syllable
  rate), spectral centroid and tilt, pause rhythm, sibilance, plus the consistency of several takes (cosine of a numpy MFCC
  embedding, `numpy_mfcc13`; the embedder is a parameter, the identity scorer is P12b's measurement). Pitch is a vectorised
  FFT autocorrelation (`f0_track`, within 1 semitone of `voice_layer.f0_track`, 100x faster). `difference`/`distinct` make VC-04
  measurable with BP-138's three margins (read by literal id, REVIEW). `record` is `voice_audition/1`; `baseline_of` and the CLI
  (`measure`, `compare`, `baseline`) feed the registry. The profile is measured, never judged: no new threshold was invented
  (consistency has no limit until real takes are measured).
- Measured on five real library previews fetched free (8.6 s, 9.7 s, 6.1 s, 2.7 s, 9.2 s of speech; the 2.7 s one is marked
  `reliable: false`): median pitch 95.6-127 Hz, centroid 914-1492 Hz, 3.7-4.4 syllables/s; three pairs fell under every margin
  (Spuds/Moody, Adam/David, Adam/Wyatt), so the battery separates voices a description cannot. A preview is not a baseline for
  centroid: the channel voice's preview measured 914 Hz against about 1250 Hz in its real read.
- `audio/casting.py`: `eligible` (famous/imitation, taken, age two bands off: the reasons), `fit` (trait match, usage rank, unlabelled)
  and `rank(..., by_usage=True)` (trait first, the library's one-year usage order only as the tie-break); library age words
  ("Senior", "middle aged") are read as our bands (the connector returns free-text labels); `ltx_voice_text` writes the voice of
  an LTX cast card as words from traits under the PV-10 guard. `rank` without `by_usage` is unchanged.
- `config/channel_voices.json` (`channel_voices/1`) and `voice_check`: `load_registry`, `registry_errors`, `register` (replacing the
  channel narrator needs the creator's recorded word, VC-08 / veto V1) and `check_against` = EL-13 (a take's timbre windows against
  the voice's baseline with the read-drift limits; unregistered, no baseline and too-short takes are REVIEW). The shipped baseline is
  Episode 1's measured Day 1 read (tilt -21.3 dB, centroid ~1250 Hz), kind `read`.
- Rules: VC-06..09 (STORY_ENGINE), EL-13 (skill), voice-caster page steps 0-8, CRAFT-VOX-02/03/08 and BP-138 no longer "planned"
  (BP-138 lists the module; `test_the_new_craft_rules_...` now accepts a built validator beside the checklist row).
  Schemas `voice_audition/1`, `channel_voices/1` with fixtures; CONTRACTS table rows.
- Not done, by design: no REST client (D8: connector only; `test_there_is_no_elevenlabs_rest_client_in_the_package`); no
  `casting_credits_max` line in `config/spend_caps.json` (a protected file, D9 "later": the creator's numbers, before P12a); no
  free voice generator was measured, so none replaces ElevenLabs for narration (Kokoro's retirement, D-39, stands).
- Tests: `tests/unit/test_voice_audition.py` (18, synthetic voices, no network or media), contract fixtures for both schemas.

## 2026-10-29 22:30 UTC (02:30 Tbilisi 10-30): paid-test caps and their ledgers (no pod, no money)

- ვანო (2026-10-29 18:40 UTC, relayed): a clear yes to the paid tests P12a, P12b and P12e within $5.90 in total, each
  started only after the coordinator's go after the final Fable xhigh static audit. The OR-23 plans and their OR-24
  confirmation are in project files `explainer-engine/blueprint_2026-10-29/paid/PAID_TESTS_PLAN.md` (Georgian summary
  `PAID_TESTS_PLAN_ka.md`).
- `config/spend_caps.json` `paid_tests`: total_usd 5.9; p12a_smoke runpod_usd 0.50, p12b_two_runs 3.00, p12e_hosts 2.40
  (pods hard at 80 %: 0.40 / 2.40 / 1.92). P12b and P12e sit above the first proposal (2.50 / 1.00) because the 80 % stop would
  leave their pods below their estimates; the total is his $5.90.
- `spend_caps.paid_test(name)` reads a test's lines and refuses an unknown test and a section over its total.
  `ledger.Run.open_test(path, name)` opens a test's ledger with its line as the cap, every other service at 0 and meta `test`,
  and refuses another run's ledger. Without it, `runpod create --ledger` on a new path got the episode ceiling
  (runpod_usd 31). CLI: `python -m explainer_engine.core.ledger open-test <run.json> <test>` and `report <run.json>`.
- D9's numbers (min_balance_left_usd 1.00, ElevenLabs casting_credits_max 1500) are ვანო's and are not in this change.
- Tests: `tests/unit/test_spend_caps.py` (5); `tests/unit` 1208 passed, 5 failed only because this container lacks `cv2`
  (the same 5 fail on main here); `docs_lint` 0 findings.
- Review fixes (PR #33 cross-review): `runpod create` refuses a ledger path that does not exist (a ledger made there got the
  episode ceilings); `Run.open` re-checks a paid test's ledger against its line on every open; the cap is per test, not per
  file: `open_test` needs `EXPLAINER_LEDGER_MIRROR` (a durable folder), restores a missing path from `<mirror>/<test>.json`,
  every save writes the mirror and a ledger that differs from its mirror stops with LedgerConflict; `ledger report` only
  reads; `decided` cites the creator's message id. Tests: tests/unit/test_spend_caps.py, tests/unit/test_runpod.py,
  tests/unit/test_cloud_stop_paths.py (P1a's drill tests now open their ledger with `open_test`, its line and its
  mirror, instead of a hand-made ledger above the line).

## 2026-10-30 03:50 UTC: P12d, the fake-HTTP drills (no pod, no money)

- `tests/unit/test_cloud_drills.py`: the five scenarios of the Blueprint card played once, each chaining the real `pod_wrapper.sh`
  (stubbed curl and uploader, `EE_DRILL` from CR-17) with the watchdog and the guard over the fake RunPod and fake registry: the
  session dies (no_self_stop), the cap is reached (and the silent pod is stopped by its record's money estimate), the folder upload
  fails (upload_fail), only the watchdog is left, the pod has no key (drop_key). `docs/CLOUD_RUNBOOK.md` "Drills" is the table
  (scenario, expected, received, live); the live column stays empty until P12a's pod runs `create --drill`.

## 2026-10-30 — P0c-2: agent form A/B at 16 segments (free, evidence only)
- `docs/research/AGENT_AB_P0C2_2026-10.md` + data in `docs/research/agent_ab_2026-10/p2/`: Napoleon-vs-Genghis at 16 segments (template D), one context (A2) vs 26 workers with Haiku on the mechanical
  stages (B2), blind Opus critic (A2 4.00 vs B2 3.17 on its table), cost 14.19 M vs 19.08 M input-price units, B2 ahead only if a Haiku unit costs under half a Sonnet unit.
  `measure.py` now reads the `s03r_writer` repair snapshot. The plan thread's recommendation, in force under the creator's 2026-10-29 18:17 UTC delegation: A5 = D-79; the card returns to him in the 2026-10-30 morning report for confirmation and he can overturn it. D-81 stays a hypothesis with reopen triggers (row in `docs/DECISIONS_AND_OPEN_QUESTIONS.md`). No paid call. Test: none (research data; `docs_lint` 0 findings).

## 2026-10-30 03:30 UTC: P1a follow-up, nested `rp.py` runs behind a reader (no pod, no money)

- Re-review of PR #29: ``echo `./rp.py create` `` and `find . -exec ./rp.py create {} \;` passed because the first word was a reader.
  Backticks now split a command segment like `(`, and a `find` with `-exec`/`-execdir`/`-ok`/`-okdir` is not a reader. Tests in
  `test_f_the_bash_hook_allows_only_read_only_and_stopping_tmr_commands`; `find . -name rp.py` and ``echo `./rp.py status` `` stay allowed.

## 2026-10-30 — P2 follow-up: review leftovers of PR #31
- `EpisodeJob.adopt`: a directory as the dossier path and approvals that are not a dict are `ContractError`, no longer `IsADirectoryError` / `AttributeError`.
- `shot_cache.key`: inf / NaN anywhere in a shot spec is a `ContractError` (no JSON form, no stable key).
- Tests: `test_adopt_refuses_a_directory_dossier_and_non_dict_approvals`, `test_a_non_finite_number_is_a_contract_error_not_a_crash`.
- Left open (design changes, for P3+ to take with the stage that uses them): approval `sha256` compared with the artifact it approves; CN-14 skipped when no `job_manifest.json` is present; `threshold_reads` does not see a rule id held in a constant.
- Review of #45 (P3b thread, CHANGES NEEDED, one blocker): `voice_check.register` now needs a non-blank `creator_ref` for ANY status or
  role change of the standing channel entry, not only for adding a different channel voice (retire-then-add no longer works in two
  calls), and a blank or whitespace ref is refused. Minors taken: pitch checked at 90-240 Hz, the other measures move with the signal
  (tilt, sibilance, emphasis, pauses, syllable rate), and the five preview measurements are committed
  (`docs/research/VOICE_PREVIEWS_2026-10-30.json`, no media) and pinned by a test.


## 2026-10-30 04:10 UTC: P1b, `runpod dryrun` + `config/cloud_pins.json` (no pod, no money)

- `cloud/dryrun.py` + `runpod dryrun --script`: `bash -n`, `lint_pod_script`, four static install rules (`pip install -U` only with `==`,
  `git+https` only with `@sha`, every `git clone` followed by a checkout of a sha from the pins file, no `|| true` on installs, a `DRY=1`
  gate after the last install) and a Hub existence check of every literal repo id. The record is keyed by the sha256 of the script text and
  by the pins file; `preflight_create` refuses a script pod without a passing one. `config/cloud_pins.json` (`cloud/pins.py`): image digests
  `tmr_pod`, `aitoolkit`, `smoke`, git shas of ai-toolkit / VideoX-Fun / diffusers / peft, `huggingface_hub` 1.33.0; all `smoke_verified:
  false`, every `pull_mb_per_s` null (not measured, not guessed). Script pods run by digest only (default `tmr_pod`); an unlisted digest, a
  tag or an undecided pin is refused; an image without a measured pull speed on COMMUNITY needs `--boot-minutes >= 25` (LT-15).
  `runpod pins <pins.txt>` compares a pod's own record. The wrapper installs `huggingface_hub==$EE_HF_PIN` when the image lacks it and ends
  the pod `BAD_HOST: no uploader` when that fails (paid plan §2.0 item 6, first option). CR-18 in `docs/CLOUD_RUNBOOK.md`;
  `tests/unit/test_cloud_pins_dryrun.py` (19 tests; the three old defects are read from the real `xworld_v2_loop.sh`).
- Values that came from lookups on 2026-10-30, not from this repo: the digests (registries), the git HEADs of that day (not necessarily
  the commits rounds 2-3b ran), the `smoke` tag (the only CUDA tag of `runpod/pytorch` 2.4; the plan says "a runpod/pytorch 2.4 digest")
  and `huggingface_hub` (latest 1.x; its API checked by import). They are pins to be proved by P12a, not facts about a working stack.
- Not done here, on purpose: the nine historic `training/pods/*.sh` (pre-P1a protocol: own upload loop, own DONE) are not rewritten. They are
  refused by `create` already; the P12 scripts under `training/pods/p12/` are the ones that must pass `dryrun`.

## 2026-10-30 04:30 UTC: P1b follow-up, review items 1-2 of PR #46 (no pod, no money)

- `runpod dryrun`: a `git+https://...@<ref>` or `pkg@git+...` pin counts only with a 40-hex sha after `@` (`@main` and tags move); a multi-line
  `if [ "${DRY:-0}" = 1 ]; then ... exit 0; fi` gate is recognised (the `exit` must be inside the block). Items 3 (a plain unpinned `pip install foo`
  without `-U`) and 4 (the record is not bound to the Hub) stay as the card wrote them. Test: `test_only_a_sha_pins_a_git_install_and_a_multi_line_dry_gate_counts`.

## 2026-10-30 06:30 UTC: P1b follow-up review round (PR #49, P3b thread)

- The sha pin is anchored: the FIRST `@` of a `git+https://...` url must be followed by a lowercase 40-hex sha and then the end, `#`, `&` or a quote
  (`@main#egg=b@<sha>`, 39/41 hex and uppercase no longer pass; same rule for `pkg@git+...` under `pip install -U`).
- The DRY gate is no longer a window of lines: it is `[ "${DRY:-0}" = 1 ] && exit 0` or an `if` over a DRY = 1 test whose THEN branch (not an
  else, not a nested `if`) runs `exit 0`; `DRY=0` tests, `echo "DRY=$DRY"` plus a later exit, an else-branch exit and `exit 1` do not count.
  This is also stricter than main's one-line check, which counted any line naming DRY and an exit. No script in the repo used either form.
  Test: `test_a_sha_pin_is_anchored_and_a_dry_gate_is_a_real_dry_is_1_test_whose_branch_exits_zero` (fails on the previous code).
- Round 3 (P3b): only `exit 0` ends a DRY gate; a top-level `return 0` is an error in bash, not an exit, and without `set -e` the script would
  run on into the paid stages (tested). Known limits, not fixed: heredoc bodies, function bodies and subshells are read as ordinary lines;
  `git+file://` and `git+git://` urls are not checked (`git+https?` only).

## 2026-10-30 04:45 UTC: P4b follow-up, the channel voice's word is checked, not just present (after #45)

- Optional findings of the #45 review: `creator_ref` was only checked for being non-blank, and the standing narrator's model and baseline
  could change without a word. Now `governance/records.py` has the action `channel_voice` (target = the voice id) and `find`;
  `voice_check.register` needs a `creator_ref` that names such a record for the voice (no wildcard, no other action) to make a
  different voice the channel voice, retire or demote the standing one, or change its `model` or `baseline`; the name, the note and
  the first channel voice of a role stay free.
- Choice to confirm (mine, not the creator's words): the baseline and the model count as "the channel voice" because loosening
  the baseline would hide drift (EL-13) and a new model changes how it sounds. If the creator wants the next episode's approved read
  to replace the baseline without a separate word, that is one line in `register`.
- Tests: `test_voice_audition.py` (a ref nobody recorded, a word for another voice/action/wildcard, each standing-voice change).
- Review of #50 (P0b thread): the word must be for the voice that BECOMES the channel voice (a word recorded to retire the standing
  voice no longer crowns another one), and it expires after 60 minutes (the window of a protected-config edit and an effort
  override; `records.find(..., minutes=)`). The records file is plain JSONL like the other actions': as strong as they are, not
  tamper-evident. For the creator: `config/channel_voices.json` is not a protected file, so a direct edit still bypasses `register`.


## 2026-10-30 05:00 UTC: P1c, measured speeds, batching rules RP-01..10, the bill into the ledger (no pod, no money)

- `config/job_speeds.json` + `cloud/speeds.py`: the table is committed EMPTY (job types and units only); `runpod cost <pod>` fills a row
  from the pod's `$EE_OUT/units.json` (new contract, RP-08: `{job_type, units, work_s, setup_s?, mb?, download_s?}`; the P12 scripts must
  write it). `pick_gpus` takes a measured row first, then the SPEED estimate, and a card nobody knows is NOT skipped any more: slowest known
  speed x `margin_unmeasured` 2.0. A card whose fixed setup is over 40 % of the pod's time is refused with its reason (RP-09). The old test
  that expected an unknown card to be skipped is changed on purpose (card text of P1c).
- RP-01..RP-10 (`cloud/batching.py`; the rule texts are the p9 re-check's B1..B10, home `docs/CLOUD_RUNBOOK.md`, docs_lint home `RP`):
  `create` now needs `--work-min` and `--setup-min` (RP-01; exempt: the P12a smoke ledger and `--measure` <= $0.30) and `--disk` for a
  script pod, records the weight set per pod (RP-02, `--second-pod-reason`), defaults a script pod to volume 0 and no ports, and counts
  hardware tries per job (RP-10). `--wait-stock 15m`, `cards --job T --units N`.
- Money: `cost` needs the pod id; `settle_due` (run by the session-start hook) settles a pod 90 min after its stop; `cost` prints a PROGRESS-ready
  line and keeps `usd_per_unit` in the ledger; `Run.report()` shows settled and open reservations apart; `check` prints the stopped disks on
  one line, names dead `keep_stopped_pods` ids and flags billing no pod explains; `start` is refused without `--allow-zero-gpu-risk`.
  `tests/unit/test_cloud_economy.py` (21 tests).
- Not done, on purpose: (1) `MAX_PRICE` pools from `config/spend_caps.json`: that file changes only on the creator's recorded word, and the
  numbers are the same; (2) the PROGRESS line is printed and kept in `tools/runpod/settled.jsonl`, not written into this file by the tool
  (every branch would conflict on it); (3) the watchdog does not settle (it has no ledger in CI): the session hook does; (4) RP-09's "never an
  80/96 GB card when 48 GB fits" needs a measured `min_vram` per job type: none exists yet.

## 2026-10-30 06:00 UTC: P1c review fixes (PR #48): a garbled units.json, a settled flag that was written away

- `units.json` is validated before it is used (`speeds.from_units_json`): an object with a string `job_type` and non-negative numbers, else
  `SpeedError` (now a `ContractError`). `cost_report` settles the real bill FIRST and parses the pod's files after, so a garbled file
  (`[]`, `null`, `5`, `units: "abc"`) costs only the speed row ("no speed row: units.json ..." in the settle line), never the ledger entry.
  The session-start hook shows a failed `settle_due` as an info line instead of dropping the whole RunPod check.
- `cost_report` re-reads the session before it records the pod's outcome, so `settled` is no longer written away and the next session does not
  settle the same pod again. Tests: `test_a_garbled_units_json_never_keeps_the_bill_out_of_the_ledger`, `test_the_session_hook_survives_...`,
  `test_a_settled_pod_stays_settled_...`.
- Wording: RP-10's message says "failed create or BAD_HOST pod(s)" (a failed `create` of any cause uses the one try). `check` only REPORTS
  unknown `keep_stopped_pods` ids; it does not clean them up (`config/spend_caps.json` changes only on the creator's word).

## 2026-10-30 09:00 UTC: Blueprint P4, the audio spine, the sound director and the free-generator gate (no pod, no paid take)

- ვანო (2026-10-29 18:17 UTC, D8): a free generator only with measured quality and variety, otherwise ElevenLabs; the narrator stays on the
  connector (no REST client). Plan: `blueprint_2026-10-29/P4/P4_DESIGN.md` (Opus 5.5 high, OR-26); built by Sonnet 5.5 high in eight commits
  on the plan's order (draft PR #51). Nothing paid was called, no pod, no network.
- **Spine** (`audio/spine.py`, `audio_spine/2`): one clock compiled from `words.json` + `timed.json` (+ `film_shots`), never written or
  repaired; D-88 post-hoc dialogue windows (a window of the planned length after the last read word, later words move, `read_time`
  inverts, `retime_post_hoc` swaps planned for clip). **Sound director** (`audio/sound_director.py`, `audio/acoustics.py`):
  `sound_mix_manifest/2` is derived (CN-02, CN-16, SD-15 stale = FAIL), the shot-to-audio matrix (BP-160) is rendered from code into
  AUDIO_SYSTEM, checks SD-01..SD-15 (every severity is the registry level of its rule; FAIL only SD-05's BP-54 onset, SD-13, SD-14,
  SD-15). **Render** (`assemble.build_audio_v2`): constant-power pan, widened music, one impulse response per scene, perspective,
  presence-band dip, vacuums, three-layer hits, stems; a job without a manifest takes the old `build_audio` unchanged.
- **Free-generator gate** (`audio/generator_gate.py`, BP-162/BP-163): `measure` (duration, silence share, clipped share, DC offset, a loop's
  seam; variety by `voice_audition.mfcc_embedding` against the library's ElevenLabs items; near-duplicate seeds), `sheet` (seeded,
  blind, levelled A/B), `admit` (refused without `creator_ref` + `at` + the answered sheet + a passing report), `admitted(kind)`.
  Order: library, then an admitted free generator, then the connector. Enforced in `assets_reuse` (`generate_free`; `generate_new`
  needs `--why` while a kind is admitted), the ElevenLabs hook (same refusal shape as OR-18), `register --source-kind open_model
  --admission` and `sfx_library.validate` (SD-13). **No generator is admitted**: `assets/audio/generator_admission.json` does not exist, so
  nothing changes today.
- **Stage 4b**: `stage_guard` stage `sound` owns no script field (a pass that changes the script is a violation); `edit-planner` step
  "4b Sound" (no new agent: `config/model_routing.json` is protected); ORCHESTRATION executor row, STORY_ENGINE row, `editing-style`
  "Sound director", AUDIO_SYSTEM (v1 event contract marked superseded, the gate documented), CONTRACTS (sfx_manifest additions).
- Deviations from the plan, with the reason:
  1. SD-04 dip depth is derived by `acoustics.dip_centre_for_gap`: the spec's 3.5 dB at the Q 1.2 bell moves the 1-4 kHz band by only
     1.4 dB, so the centre depth is solved for the gap BP-118 asks for (SD-04 measures the gap, never the filter).
  2. The mid perspective is the midpoint of BP-122's near and far ends (the spec names no value).
  3. `level_voice` peaks at 4.0 GB RSS on a 15-minute read; that is the pre-existing path (the old `build_audio` does the same);
     chunking it is a follow-up.
  4. `assemble(job=None)`: the signature keeps `job` optional so the old callers and tests stay as they were.
  5. The dialogue-window `total_frames` against the picture's length is P6's (it picks the native lines); until then the spine has no windows.
  6. BP-163 gained four threshold keys (`prompts_clean_min` 0.8 from spec 5.1 "80 % of prompts", `silence_floor_dbfs`, `window_ms`,
     `clip_level`) so no number is literal in `generator_gate.py`; its statement says so. DC offset is reported, not judged (BP-163
     has no limit for it).
  7. A prompt is clean only when all `takes_per_prompt` takes exist and pass; the variety is computed over technically clean takes only.
  8. `admit` takes `sheet` (its sha256 is recorded) and an optional `prefer_rate`, recorded as he states it and not gated: his recorded
     word is the gate (OPEN 1 below); `register --source-kind open_model` also needs the model's own licence note (the ElevenLabs default
     would be false) and refuses an admission for another model; the kind of a take is music, room_tone (tag) or sfx (other foley).
  9. SD-13 at plan time still checks only that an `open_model` item names an admission; the file check (kind, model) is `validate`'s and
     `register`'s. `stage_guard`'s `ORDER` does not list `sound` (it runs after the read, outside the script stages' chain).
- OPEN for the creator (none blocks; the default is what is built): (1) the admission bar: his blind A/B answer, a generator admitted
  for a kind if he prefers it or calls it "same" on at least half of the pairs (his number can replace "half"); (2) where the free
  measurement run happens: default the HF ZeroGPU Space through the connector, else CPU in a cloud session, never a pod; (3) music width
  from mono library files: default a fixed all-pass decorrelation; (4) room tone when the library has none: default procedural pink noise
  per scene (free, seeded).
- Cross-review fixes (plan thread, 2026-10-30): `assemble.v2_manifest` now runs `contracts.errors` (schema, CN-16, CN-02) and refuses a
  manifest that is not `sound_mix_manifest/2`, has an empty or missing `derived_from`, or was hand-edited into an invalid shape (SD-15);
  `test_assemble_v2` pins it (six forged cases, not-JSON, one fresh pass) and pins the old mono path by a golden int16 sha256 of
  `build_audio` (equal on main and on this head). SD-04's limit is written into BP-118 and AUDIO_SYSTEM.
- Follow-ups, not in this PR: (a) an admission gate before the first generator is admitted: `assets/audio/generator_admission.json` is
  not in the governance `protected_files`, `admit` trusts the report's numbers (it re-derives the verdict, but a hand-written file
  passes) and the mix-time SD-13 only looks for an id; (b) block-wise `level_voice`: 3.84 GB peak RSS on main alone for 15 minutes,
  4.01 GB old path, 4.07 GB v2, so the stereo mix adds almost nothing but the whole path wants chunking.
- Not done, on purpose: the measurement run of ACE-Step 1.5 and Stable Audio Open Small against the library (spec 5.3) is a separate free
  step after the merge; P6 (native-dialogue lane), P7 (cuts, OTIO) and P8 (CRAFT-SND-09/11 critic rows) are the handoffs of spec 6.4.
- Tests: `test_audio_spine`, `test_sound_director`, `test_acoustics`, `test_assemble_v2`, `test_generator_gate` (17), the sound stage in
  `test_story_engine`, contract fixtures /2. Full suite (not system, not media): 1906 passed; docs_lint 0 findings; governance check ok.

## 2026-10-30 08:30 UTC: the pre-pod secrets gate (CR-19; free, no pod, no money)

- `cloud/env_presence.py` + the manual workflow `.github/workflows/presence_check.yml` ("Run workflow"): prints `present` / `MISSING` for
  `HF_TOKEN`, `RUNPOD_API_KEY`, `NTFY_TOPIC` (the secrets `watchdog.yml` reads), never a value, a prefix or a length, red when one is missing
  or blank. Manual only, not in "quality" (a fork's pull request has no secrets). Limits, said in CR-19: it proves existence, not validity or
  scope, and a pod's own `HF_TOKEN` comes from the session that runs `create`, not from the GitHub secret. Test:
  `tests/unit/test_cloud_env_presence.py` (including that the workflow maps exactly the required names).
- Review round (P3b, PR #53): the files are named `env_presence.py` / `presence_check.yml` / `test_cloud_env_presence.py` because the repo-hygiene
  guard refuses tracked file names that look like secret files (`secret` in the name); the guard is unchanged. The leak test now uses a canary
  none of whose characters occurs in the legitimate output and checks stdout and stderr in set / blank / whitespace / newline / missing cases (it fails
  for a printed first character, a tail or a length); the secrets are mapped on the one step that needs them, not on the job.

## 2026-10-30 08:10 UTC — P0d: key alias `EE_ANTHROPIC_API_KEY`
The environment settings refuse the name `ANTHROPIC_API_KEY` (Claude Code account auth). `claude_api.api_key()` now takes the first non-empty of `ANTHROPIC_API_KEY`, `EE_ANTHROPIC_API_KEY`; used by `client()`, `status`, `estimate`. Test: `test_the_key_can_come_from_the_alias_name`.

## 2026-10-30 UTC (Tbilisi night): Blueprint P5, the visual compensator: maps, HUD, tableaux (no pod, no money)

- ვანო (2026-10-29 18:30 UTC): carry the Blueprint through the night, free steps only. P5 = the free, deterministic frames for the
  narrated stretches with no character: 12 archetypes, the map's 8 laws. Home: `docs/COMPENSATOR.md` (prefix CMP-).
- Code: `explainer_engine/maps/` (geo, plate, camera, paths, timeline, render for archetypes 1-4, laws CMP-01..08 and CMP-13, draw),
  `maps/data/` (Natural Earth 1:50m extract, 547 KB, pinned sources and a build script), `edit/hud.py` (5, 7, 10, 11, 12),
  `edit/tableau.py` (6, 8, 9), `edit/visual_compensator.py` (catalogue `edit/archetypes.json`, manifest check, CMP-10 rotation,
  CMP-11 map share, CMP-12 lane balance, render and measure CLI). A frame is a pure function of (spec, spine, frame): same bytes
  in a chunked render (CMP-09).
- Contracts: new `comp_spec/1`; `visual_comp_manifest/1` items reference it by a layer of kind `spec`; CN-15 (an archetype is one of the
  catalogue and on its family's lane, for shots, items and specs). Registry: BP-147..153 (hypotheses, so REVIEW), BP-124/125/127 now
  enforced by the new validators.
- Decisions: D-87 (ceiling = 2D vector map + 2.5D parallax, no height model; the faction pair is blue and vermilion: after Machado 2009
  the worst case over protan, deutan and tritan is 112.9 (CIE76) against 98.3 for the Blueprint's red and 87.5 for the first pick, a light
  orange, whose 118 claim was wrong for tritan, found in review; the sides are also told apart by a square or a triangle and a solid or a
  dashed route).
  Palette tokens `faction_a`, `faction_b` with `design/palette.py:faction_findings`. The dossier card has no stamp (CMP-15, D-61/SC-11).
- Measured (this container, 1280x720, ss 2): 0.09 s per frame for HUDs and graphs, 0.5 s for maps, 1.6 s for the formation, 2.4 s for the
  parallax tableau: a 30 s item at 24 fps is minutes of CPU, never a pod (`archetypes.json` `measured`).
- Tests: `test_maps` (one test per law, determinism, letterless plate by construction, the pinned extract; the OCR check skips when
  tesseract is absent), `test_compensator` (catalogue = doc table, all 12 archetypes render from the demo job in `tests/unit/_comp.py`,
  chunk-identical bytes, cross-item checks, CN-15, CMP-14 no client and no model imported).
- Not done (named in COMPENSATOR.md): BiRefNet is only an input slot for the matte, the depth model is not in this phase (tests use a
  synthetic depth map), painting the plates is P12e, the router is P6.
- Review round 1 (P0a): D-87's numbers corrected and the pair re-chosen by worst case (vermilion `faction_b`, world bible v1.3 draft);
  route lines and heads carry the side mark; `WordClock.frame_of` refuses a word before the trigger word (CN-01) instead of clamping;
  BP-127 keeps its `planned` note for the score; the known limits and the two open card criteria are listed in `docs/COMPENSATOR.md`.
- Review round 2 (P0a re-review and the Claude API review J1): `draw.Canvas.line` carries the dash phase across a curve's segments (side b's route
  really is dashed; the first fix could loop for ever on a float edge, now always moves on); `camera.tilt` narrows the far edge (code, docstring
  and doc agree); a `comp_spec/1` payload with a missing key is a CN-01 FAIL from every validator, never an exception (a guard in
  `visual_compensator` plus explicit checks, and a test that removes each key of every archetype's payload in turn); `check` now runs CMP-11 over the
  spine's runtime and CMP-12 when the planner passes its beats; the tableau reads its PNGs once per item and skips file checks without a job
  folder; catalogue, PNG and source pins are written atomically; a faction pair needs both marks; the doc names the fonts the code really uses.
  P5's rule ids moved to BP-147..153 and its decision to D-87 after main took BP-140..146 and D-86 (P3).

## 2026-10-30 08:50 UTC: G13 crash-drill test (audit pass 1, B3; free)

- `git grep` on main (874b498) found no test of a ledger one save ahead of its mirror reaching `create`: the audit was right. Added
  `test_drill_6_the_mirror_write_fails_once_...` to `tests/unit/test_cloud_drills.py` (runbook drill table row 6): the mirror write fails once during
  `reserve`; `Run.open_test` and `runpod create` both stop with `LedgerConflict`, the fake API gets 0 calls, the ledger keeps its 0.07. The table
  test now expects six rows. No code changed (the audit found the code correct); nothing else weakened.

## 2026-10-30 08:55 UTC — P0d: the tool loop's cache breakpoint, partial saves, loop estimate (J1b scope A lost $5.02)
J1b scope A ran 18 turns and hit the 80 % stop without saving anything: the ledger shows `cache_read` stuck at the 22,746-token system prefix while fresh `input` grew to 48k per turn ($0.50 a turn). Causes fixed in `llm/claude_api.py`: (1) `_with_breakpoint` puts the cache breakpoint on the last block every turn (the first message keeps its own; at most two message breakpoints); (2) `save_partial` writes `partial_<job>_<id>.json` (assistant text, tool calls, results cut to 400 characters, usd so far, the stopping error) before any error leaves the loop, and the error carries the path as a note; (3) `estimate` marks a tool loop's figures as first-turn only and adds a `loop` row (`--turns N`, `--new-tokens-per-turn`) priced with cached re-reads (`loop_usd`). The per-turn reservation (`worst_usd`) is unchanged and stays conservative (whole prompt as writes): it still trips the stop earlier than the real spend. Tests: breakpoint per turn, partial on max_turns and on a cap stop, estimate warning. No paid call.

## 2026-10-30 09:10 UTC: G15, `create --cloud`, flags that mean what they say (audit pass 1, B2; free)

- The paid thread found that `--only "GeForce RTX 3090"` kept the SECURE 3090 at $0.50 beside the COMMUNITY one and `EE_PRICE` was the dearest
  pick, which cut pod A's dead-man from 16.2 to 6.2 min. `create --cloud COMMUNITY|SECURE` now restricts the picks, the cards tried and
  `EE_PRICE` to one cloud; `--only` accepts a comma list and is searched among 50 cards, not the cheapest six. An unknown flag is refused
  before any API call, as are `--only`/`--cloud`/`--ref-hours`/`--wait-stock` without `--vram` (they were ignored: default pool, RTX 4090 SECURE).
  CR-20 in the runbook; tests in `tests/unit/test_cloud_economy.py`, including one that every flag the create branch reads is in the known list.
- Review-desk round on this PR (four gaps, all on the money path): `--vram` now REQUIRES `--cloud` (no committed caller or doc used `create --vram`
  without it, so nothing legitimate breaks); an empty or flag-like value (`--cloud ""`, `--only ""`) is refused, not read as "not given";
  every name in an `--only` list must match a card with stock, else refusal with a did-you-mean (a typo used to be dropped and the pod
  landed on the card left over; an out-of-stock name now refuses too, `--wait-stock` retries it); the 50-card search is pinned by a test
  where the wanted card is outside the cheapest six (mutated back to 6, it fails).
- For the P12a commands: pass `--vram 24 --ref-hours 0.05 --boot-minutes 25 --cloud COMMUNITY` (or SECURE) with `--only`; leave out
  `--setup-min` (a 10-minute setup against 3 minutes of work is refused by RP-09).

## 2026-10-30 09:40 UTC: the five P12a pod scripts (audit pass 1, B1 / G9; free, no pod, no money)

- `explainer_engine/training/pods/p12/p12a_A..E.sh`, written from the paid plan sections 2.2-2.6 and nothing else: A (boot facts, one shard download
  timed, the aitoolkit manifest by skopeo when present), B (3 steps, then `exit 1`), C (10 minutes of 1 KB parts), D (30 minutes of parts that the cap
  ends), E (2 minutes, `exit 0`). Each declares `# heartbeat: datasets/vano1919/tmr-artifacts:runs/p12a/<X>/beat.txt` and `# stall-minutes: 4`,
  writes `progress.txt` with a changing line and `t.jsonl` events (script_start with `EE_DEADLINE`, exit with rc), installs nothing, so no DRY gate is needed.
- A-2 downloads shard 00002 (4,261,951,904 bytes, measured on the Hub at revision d26bb61) as the plan thread decided; shard 00001 is 9.97 GB. The
  shard is found by its name prefix and checked by its size (4,261,951,904) before it is fetched, so the script names no weight file: VT-01 takes
  any script naming weight files for a training pod, and the plan thread decided (08:38) not to walk around it with an assembled name nor to loosen it
  without a precise rule. A downloads to /workspace/dl, deletes it and writes no weights to $EE_OUT (a test checks that no shard reaches the vault).
- A does not write the image digest the plan mentions: the pod has no such variable (nothing sets one); the session reads it from the create body.
  The boot facts list only chosen non-secret variables (the pod env holds keys; a test checks none is written).
- `runpod dryrun` passes for all five (Hub existence of Qwen/Qwen-Image-2.1 and the vault dataset checked with the network). sha256 of the scripts:
  A 25661e2e, B c193e702, C 64cc4734, D 8af25923, E 40ab6415 (full values in the PR). A dryrun record is keyed by that text: any edit means a new
  dryrun, and the copies on HF `code/p12/` must be made from the merged files, then compared by sha256 before each create (audit N3).
- Test: `tests/unit/test_p12a_scripts.py` runs B, C, D, E and A under the real `pod_wrapper.sh` with stubs and short steps (`P12_STEP_S`, `P12_DL` only
  for the test): end words, drills, parts uploaded before the cap, boot facts, speed record, shard deleted.

## 2026-10-30 09:55 UTC: CR-12 wording, the watchdog is an hours-scale backstop (audit pass 1, B4; docs only)

- Evidence (audit 08:35 UTC): the recorded scheduled runs were 4-7 h apart (29 runs in 6 days under `*/30`, none under `*/10` by 08:19 on 10-30). CR-12
  and the stop-path table now say so, and that the session dispatches the watchdog before every create and every 10 minutes while a pod relies
  on it, so the stop is the watchdog's code with the session's timing. Pod E's pass criterion is the OR-24 thread's call (2026-10-30 08:38): E passes when the watchdog's own code stops it at
  the first session-dispatched run after DONE, and its report states that the timing came from the session, not from cron. Nothing in code changed.

## 2026-10-30 09:20 UTC — P0d follow-up to the cache-fix review: loop bounds, previous output as a write, second breakpoint
The review of the cache fix left three points. (1) `loop_usd(mode=cached|uncached|miss)` and the estimate row now carry `usd_if_cached`, `usd_if_uncached` (no cache read at all: what the J1b scope A run billed) and `usd_if_miss` (everything rewritten every turn), and the model's output of the previous turn is billed as a cache write (about 4 % more than before). The default tool-result size is 2000 tokens a turn, rounded up from what the scope A ledger shows (~1.5k). (2) `worst_usd`, `worst_total_usd` and the pre-run refusal no longer price a loop at turn 1: the loop figure chosen by `--loop-bound cached|uncached|miss` counts, never less than turn 1. Default `cached` (the expected case after the breakpoint fix); `uncached` is the conservative choice and, on a 24-turn PR review (102k-token first turn) gives $12.95 against $1.70 cached, so with it every J1 review would be refused at the $8 line's $6.40 stop: the owner of the money lines picks the default. (3) `_with_breakpoint` also keeps the previous turn's breakpoint (four in all with the system prefix), so a turn with more than ~10 parallel tool results hits the cache. Tests: ordering and arithmetic of the three modes, the loop in worst_total, the refusal by bound, the second breakpoint on 14 parallel results. No paid call.

## 2026-10-30 09:45 UTC — P0d: runtime cache guard in the tool loop (default `--loop-bound cached` made self-checking)
Decision (Blueprint thread): `--loop-bound` stays `cached`. So the loop now checks that assumption itself: `cache_guard` from turn 3, on a turn that still wants tools, stops with `CacheCold` (naming the measured share) when under 60 % of the prompt tokens were cache reads or writes, or when the cache read did not grow while 1000 or more fresh input tokens were billed (the read stuck at the system prefix). The partial is saved by the #58 path. Prompts under 1024 tokens and final answers are not judged. Replaying the J1b scope A ledger rows through it stops at turn 3. Tests: warm history runs on; stuck-at-prefix stops at turn 3 with the partial on disk; the share message; the guard switched off fails the stuck test. Existing max_turns/cap tests now script warm usage (they test turns and caps, not the cache).

## 2026-10-30 UTC: P5 follow-up, Canvas.line's dashed walk always terminates (no pod, no money)

- The plan thread's review desk (after #47): the 1e-6 float floor of the dash walk was not pinned by a test, and `Canvas.line` still hung or
  divided by zero on degenerate input. Now: `draw.dash_runs` is a pure generator walking only the part of the line inside the canvas box (the
  phase still advances over the rest), so the work is bounded by the box, not by the line's length (a 1e12 px line is instant); a dash must be
  finite with on > 0 and off >= 0 and the coordinates finite, else ValueError; a pattern finer than a pixel is drawn solid.
- `tests/unit/test_draw_guards.py`: the refused dashes and coordinates, the 1e12 line, the 1e-9 dash, and the phase across the clipped part.
- Review of #60 (P1a): the absolute floor is not enough far from the origin (at 1e12 one float step is ~1.2e-4, so `pos + step == pos` and the
  walk never moved; `Canvas.line([(-1000000000003.8188, 10), (1e12, 10)], dash=(2.5077..., 5.1608...))` spun). `dash_runs` now advances one ulp
  (`math.nextafter`) when a step does not move `pos`; that input has its own test. The old floor test's premise (no floor = a stall) no longer
  holds, so it now pins what the floor still does (keeps ulp-sized sliver runs out). The phase advance over a segment wholly outside the box
  has a test that fails when the line is deleted (checked by mutation); so does removing the `nextafter` step.

## 2026-10-30 12:00 UTC — P0d: paid output saved step by step (audit F1-F11; OR-33)
The static audit (`blueprint_2026-10-29/paid/AUDIT_CLAUDE_API_2026-10-30.md`, ~$7.30 paid with no result) found ten paths where paid output is lost and four where cost balloons. Fixed in `llm/claude_api.py`: (F1) every call streams, each text delta is flushed to `<ledger>/stream/<uid>.txt` and the start line names the file; (F2) an error after text is not retried or voided but booked at the reservation, `StreamBroken` carries the path and text; (F3) `OutputTruncated` carries the paid text, `main` writes `<id>.truncated.md|json`, batch items too; (F4) the tool loop checkpoints its partial after every turn, saves on `BaseException`, and `run` turns SIGTERM into `KeyboardInterrupt`; (F5) the last turn, or a turn with less room than two worst-case turns, is a wrap-up turn (`WRAP_UP_TEXT`, tools list unchanged), one that still calls tools stops with the partial; (F6) the turn's content is in the transcript before `CacheCold`; (F7) `run_job(on_result=)` hands over each result at once, `main` writes files as they come, a failing request marks the rest `not_run`; (F8) a batch rerun skips items that have a `done`/`void` line; (F9) `cache_guard` stops a loop whose cache read is under 50 % of the previous turn's whole prompt (a full miss; measured against the previous prompt so one big tool result is not a miss); (F10) the loop estimate prices the last turn at `max_tokens`, tool results of one turn are capped at 60,000 characters; (F11) message calls use SDK `max_retries=0`. New rule OR-33 (ORCHESTRATION.md, CLAUDE.md). Tests: one or more per fix in `tests/unit/test_claude_api.py`; the fake client now always streams; `test_long_output_is_streamed` also checks a short call streams, and `test_a_cap_stop_in_the_middle_of_a_loop_keeps_the_turns_so_far` now makes the money disappear mid-loop (a wrap-up turn precedes a plain cap stop). Open (not changed): the TTL for slow tool loops, the default `--loop-bound`. No paid call.
- Follow-up (same day): the stream file is written one redacted line at a time (a split key never reaches it; truncated files are redacted too); a 1 h-TTL tool loop needs `measured_turn_gap_s` > 300 in the job file (the 1 h loop figure is tested never below the 5 m one); stream-proof gate: `stream_proof.json` is written once by the first direct call whose stream file equals its redacted answer, `run` refuses (exit 4) any job but a tiny proof job (<= 256 tokens, ~$0.0001 on Haiku 5.5) until it exists, `status` shows it. New rules OR-34 (Fable's full-repo audit before any paid test) and OR-35 (API instead of threads where quality holds) in ORCHESTRATION.md and CLAUDE.md, tested in `tests/unit/test_api_audit_rules.py`.

## 2026-10-30 — P0d: thinking is streamed and saved, a max_tokens floor per effort, max effort needs a reason (the $3.45 thinking-only loss)
A Fable 5.1 job at effort `max`, max_tokens 40000, stopped on `max_tokens` after $3.45 and saved nothing: thinking is always on, billed as output and counted toward max_tokens, it used all 40000 and no text delta ever came, so the stream file (opened at the first text) never existed. Fixed in `llm/claude_api.py`: (F12) every request sends `thinking: {adaptive, summarized}` (batches too; never `budget_tokens`); (F13) the stream file is created with a header at the start of every attempt and gets `[thinking]` and `[answer]` parts (thinking deltas redacted and line-buffered, `signature_delta` ignored), F2's "output arrived" counts thinking, the stream proof compares only the `[answer]` part, `OutputTruncated` carries `.thinking` and says plainly when thinking used all of max_tokens, `main` writes `<id>.thinking.md`, partial transcripts keep thinking blocks; (F15) `MIN_MAX_TOKENS_BY_EFFORT` (max 64000, xhigh 32000) refuses a request before anything is reserved, `estimate` shows `max_tokens_floor_ok`, `run` returns 3; (F16) a single-shot request at effort `max` needs `max_effort_reason` in the job file (`max_effort_reason_ok` in the estimate, `run` returns 3). `config/model_routing.json` untouched. Tests changed because of this: the body test now expects `thinking`; two Fable xhigh tests use max_tokens 32000; stream-file assertions read the `[answer]` part. No paid call.

## 2026-10-30 — Claude API money lines: plan v2 gets its own line ($28), a line may not be lower than its spend
ვანო chose option 0 ("max, 64k, about 6 calls") on the plan thread's decision card, 2026-10-30 11:23 UTC (cmsg_01Hnu5zB86sjUj5GtTgaUkPWYNYok241qwy43eZsfEZQe6); earlier at 10:01 UTC he allowed raising a ceiling by up to 30 % for the plan (cmsg_01Hnu5zB86sjUj5GtTgaUkPWNCYsuH3FgTVKXhhNQpbKyd). `config/spend_caps.json` `claude_api.jobs`: J1b 8 -> 5.02 (its $5.02 spent stays covered), J6 15 -> 0, J4 5 -> 2.98, reserve 24 -> 16, new `plan_v2` 28; the lines still add up to $95. `claude_api status` prints `lines_below_spent`, and a test pins the sum and J1b's cover.

## 2026-10-30 12:00 UTC: D9, the creator's answers in `config/` (no pod, no money)

- ვანო, 2026-10-30 11:56 UTC, message `cmsg_01Hnu5zB86sjUj5GtTgaUkPW5XNWqTbsYwYjr1qt3UyQhT`: "ყველაფერზე კი", that is option a on every question of
  `QUESTIONS_FOR_VANO_2026-10-30.md`. This change carries questions 10-13 and the stale pod; the merge of this PR is his recorded word for the
  protected files (`config/spend_caps.json`, `config/model_routing.json`).
- `config/spend_caps.json`: `runpod.min_balance_left_usd` 0.25 -> 1.00 (question 13; `create`'s preflight and the watchdog already read it);
  new `casting.casting_credits_max` 1500 ElevenLabs credits (question 11; reader `spend_caps.casting_credits_max()`); new `gemini_api`
  `max_usd` 10 per calendar month (question 10; reader `spend_caps.gemini_api()`); `97vn2t443puxxl` removed from `keep_stopped_pods`
  (`runpod check` reported it gone).
- `explainer_engine/llm/gemini_api.py`: no client yet; `reserve(estimate, spent_month)` refuses past 80 % of the ceiling, `complete` always
  refuses. The picture calls keep `per_episode.gemini_usd`.
- `config/model_routing.json` `protected_files` gets `config/channel_voices.json` (60 minutes; question 12): a tool edits it only on his
  recorded `protected_config` word, beside the `channel_voice` word that `voice_check.register` asks for. The docstring of `register` said the
  file was not protected; it now says it is.
- Tests: `tests/unit/test_d9_config.py` (7: the 1500, the 10 dollars and the 80 % stop, no line = refusal, create refuses at 0.90 left, the
  pod id gone, the channel-voices hook with a stale and a fresh word). Each was mutation-checked.
- The shared fake RunPod account of `tests/unit/test_runpod.py` held a balance of $1.00, which is now below `min_balance_left_usd` plus a
  test pod's `--max-usd`; 16 cloud tests were refused by the floor instead of testing what they name. The fake's balance is now a
  `balance` attribute defaulting to $20.00; no assertion changed (the refusal itself is `test_min_balance_left_is_one_dollar_...`).

## 2026-10-30 — T3-1 (CP-03): the Blueprint table says what main says; a merged phase without a routing-log row fails `governance check` (no pod, no money)
- `docs/blueprint/phases.json`: P0a #32, P0c #35, P1a #29, P1b #46 + #49, P1c #48, P2 #31, P3b #36, P4b #45 + #50, P5 #47, P3 #40, P4 #51 and
  P12d #44 are `done` with `#NN merged` (evidence: the first-parent merge commits of main up to `66d4529`, the phase entries of this file,
  the project STATUS mirror 13:55). P0b was already `done`. Unchanged: P5b, P6 (`todo`, ready to start), P7-P11 (`todo`), P12a/b/c/e (`blocked`).
  OPEN: `P0c-2` and `P0d` appear in the mirror and in PROGRESS but have no id in `phases.json` (24 phases, a test pins the count); not added.
  OPEN: PROGRESS names no PR number for #32, #35 and #44; the merge commits on main and the mirror agree, so they are set `done`.
- `routing_log.jsonl`: ten backfilled rows (P0a, P0c, P1a, P1b, P1c, P2, P3b, P5, P3, P12d). Only P1a and P2 have a stated run model (Opus
  high, mirror 13:55); the others carry `unrecorded` model/effort and the planned routing in the note, never an invented value.
- `governance/status.py`: no code change; `check_log` already returns an error for a `review`/`done` phase without its row. The new tests pin it.
- Tests (`tests/unit/test_routing_log.py`): `test_merged_phases_are_marked_done_with_their_pr` and
  `test_governance_check_fails_closed_on_merged_phase_without_log` were red on main; `test_every_merged_phase_has_a_routing_log_row` added.
  Three older tests used P0c as their "not yet done" fixture phase (`test_a_done_phase_without_a_log_line_fails`,
  `test_a_review_phase_needs_a_pr`, `test_stop_refuses_a_done_phase_without_its_log_line`); they now use P6, which is still `todo`; no assertion changed.
- `docs/blueprint/STATUS.md` regenerated by `governance status --write`. Closes Fable F-03; Argon-1 F-10.
## 2026-10-30 13:45 UTC — T2 (claude-sonnet-5-5 high) — CP-02 + N-04: honest lanes and the real speeds schema in `variant_plan` (PR #69)
- `scripting/variant_plan.py`: `KEYFRAME_LTX:light/full` are `available: False, phase: "P6"` (no LTX-2.5 / Wan 2.2 clip pod script under
  `training/pods/`; `grep -il "ltx\|wan2"` over every `*.sh` finds none, and `runpod dryrun --offline` refuses the nine pre-P1a scripts);
  `MAP` and `COMPENSATOR` are `available: True` with file evidence (`maps/render.py`, `edit/visual_compensator.py`, both opened);
  `_row_usd` reads the table `runpod cost --record-speed` writes (`jobs/<job>/rows/<card>`, priced from `usd_per_unit`, never from seconds
  alone) through the new pure `cloud/speeds.lookup(data, job, card=None)`; the flat `speeds[job]["seconds_per_unit"]` form stays as the
  legacy path (its tests are unchanged); VP-12 names why a pod row is unpriced (no measured row for the job / several cards measured and
  the row names none / no priced row for the card).
- `examples/napoleon_vs_genghis/script_variants.json` re-scored by `variant_plan napoleon --write` (`chosen` is `null` and no sha binds the
  file): v1 90 -> 70 (two KEYFRAME_LTX lanes wait for P6), v2 60 -> 70 (MAP and COMPENSATOR findings gone, one KEYFRAME_LTX added); the pick
  stays the creator's.
- Tests red on main -> green: `test_variant_plan.py::test_vp11_each_missing_lane_is_one_finding_naming_its_phase_and_the_table_is_honest`
  (evidence must be a file, KEYFRAME lanes `False/P6`, MAP and COMPENSATOR `True`), `::test_row_usd_reads_the_job_speeds_schema_written_by_runpod_cost`,
  `::test_vp12_names_why_a_pod_row_is_unpriced`, `test_cloud_economy.py::test_lookup_names_the_one_measured_card_or_nothing`. Five existing
  tests pinned the old scores/lane table (90/60, `lanes.MAP` missing); their expectations moved to the new facts, no assertion removed.
- OPEN: the scores of the two Napoleon variants now tie (70/70); needs ვანო only for the pick. No pod, no API call, nothing deleted.
- Decision log: none moved.
## 2026-10-30 UTC: plan_v2 T1 / CP-01, the retired launchers never run; the hook refuses them and a library create (no pod, no money)

- `explainer_engine/aivideo/pod/launch.py`, `launch_clips.py` (D-80, Fable F-01, Argon-1 F-19, Argon-2 F-06 fence half): the docstring
  opens with `RETIRED by D-80 ...`; `raise SystemExit("RETIRED by D-80: ...")` is the first statement after it, before every import (run as a
  script, the `explainer_engine` import fails without PYTHONPATH, so a guard placed just above `api = rp.Api()` would never print). Nothing
  else changed; nothing deleted (invariant 8, deletion is the creator's word). No other RunPod caller under `aivideo/pod/`.
- `explainer_engine/cloud/hooks.py` `BYPASS` += the launcher paths (`python ... aivideo/pod/launch(_clips)`, `/`, `\` or `.`) and a Python
  `rp.create(` / `runpod.create(` (`;` and newlines kept inside, so `python -c "...; rp.create(...)"` and a heredoc are caught). Readers
  (`cat`, `grep`) and the CLI (`python -m explainer_engine.cloud.runpod create|check`) stay allowed. The hook is the second net; the library
  guard is N-01.
- Tests: `tests/unit/test_money_path_fences.py` (CP-01 section: both launchers exit with `RETIRED by D-80` and no network, 7 refused
  commands, 6 allowed ones); `tests/unit/test_aivideo_shotplan.py::test_pod_code_follows_the_rules` += the guard sits before `rp.create(`
  (addition only). Red on main: 9 failed.

## 2026-10-30 — T3-2 (CP-04): the live xworld LoRA, datasets and code are vault-`critical` (no pod, no money)
- `config/vault.json` `critical` gains `lora_plan_2026-10-26/` `train_xworld_v2/output/**`, `train_xworld_v2/code/**`, `train_xworld_v1/**`,
  `dataset_xworld_v1/**`, `dataset_xworld_v2/**`, `caption_xworld_v1/**` (every prefix appears in `explainer_engine/training/pods/*.sh`). Nothing removed; the `wldnk_*` rows stay (deleting them is creator card 6).
- Not added, OPEN: `train_xworld_v2/train.log` (only v1's `train.log` is uploaded by a pod script; v1 is covered by `train_xworld_v1/**`) and
  `cast_xworld_v2` (Argon-1; no HF path for it in the repo).
- `docs/VAULT.md` VT-01..VT-04 only restrict deleting, so adding globs needed no creator word.
- `vault snapshot` ran (HF_TOKEN was in the session, read-only on HF): 16735 files, 60.97 GB; critical 8860 files, 13.87 GB. `docs/VAULT_MANIFEST.json` regenerated and trimmed to the 8860 critical rows plus `note` (VAULT.md: critical rows only); `vault verify` on it: PASS, every manifest file is on the primary copy.
- Test: `tests/unit/test_vault.py::test_the_live_xworld_lora_and_datasets_are_critical` (red before the globs, 1 failed; green after, 9 passed). Closes Argon-1 F-01; Argon-2 F-26 (the add half).
## 2026-10-30 — plan_v2 wave 1, T2 PR-B: CP-05, KG-22/KG-23 are a visible REVIEW while the style is suspended (D-80)
- `qa/blind_check.py`: the retired wldnk rubric is kept as `STYLE_SPEC_WLDNK_RETIRED` (mechanics only, tests still run it); the live `STYLE_SPEC` is empty
  and `STYLE_SUSPENDED = True` is the one flag. `describe_rules`, `compare(..., spec=None)` and `style_verdict(..., spec=None)` take the spec as an argument,
  so no verdict is computed from a spec nobody chose. `qa/keyframe_gate.py` imports the flag and writes KG-22 (and KG-23) as an explicit REVIEW row
  (`kg22_row`, `kg22_row_text`) naming D-80 instead of an empty PASS; `docs/KEYFRAME_GATE.md` carries the two rows.
- Tests red on main -> green: `test_keyframe_gate.py::test_kg22_is_review_while_the_style_set_is_suspended`; `test_blind_check.py` does not collect on main code
  (`STYLE_SPEC_WLDNK_RETIRED` missing). Focused set 30 passed, `docs_lint` 0 findings, `governance check` ok. No assertion removed.
- OPEN: when a new style set is chosen the creator's call, not this PR, fills `STYLE_SPEC` and clears the flag. No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 UTC: plan_v2 T1 / N-01, `runpod create` needs `--script`; the pin and the wrapper are checked on the body; `create()` sends only a stamped body (no pod, no money)

- `explainer_engine/cloud/runpod.py` (Argon-2 F-06 library half, F-19): `main create` refuses a missing `--script` before any other check
  (`refused: runpod create needs --script (... OR-21 ...)`). `preflight_create(..., body=None)`: with `body` (every creation passes it) a
  missing script is refused (OR-21), a body whose `cmd` is not `pod_wrapper.sh` is refused (so a TMR boot body or a `--script` without
  `--script-url` is never sent), and the body's own `image` must be a digest in `config/cloud_pins.json` (unconditional; before, only
  `if script`). With no refusal the body is stamped in place (`PREFLIGHT_KEY` = sha256 of the body, `preflight_stamp`). `create(api, body)`
  pops the stamp first and refuses a missing one or a body changed after the preflight, before any HTTP call. `main create` now builds the
  body (and `--disk`, RP-03) before the preflight and passes it. Without `body` (`start` of a stopped pod, the ceiling tests) nothing changes
  and nothing is stamped. `boot_cmd`/`create_body(boot=...)` stay text builders (their text is pinned by tests); a boot body can no longer
  be stamped, so it cannot be sent. `IMAGE`/`BOOT_REPO` stay, commented as history.
- Tests: `tests/unit/test_money_path_fences.py` (N-01 section, 7: unstamped body refused with no network, a body changed after the
  preflight refused, no script / unpinned image / boot body never stamped, three scriptless CLI lines refused with `OR-21` before any call,
  a script create POSTs exactly one body without the stamp, running the wrapper, on a digest). Red on main: 7 failed.
- Tests changed and why (setup only, or an allowed path that is now a refusal): `test_runpod.py` gets `stamped()`, `script_pod()`,
  `live_ok()`; 9 library tests of the card loop stamp their hand-made body; 6 CLI tests that used a scriptless/boot pod now run a script pod
  (two expected values follow the script pod: `status_token` empty, `pod_shape` 0/40 GB); `test_cloud_guardian.py` 2 CLI tests the same;
  `test_cloud_stop_paths.py:344` stamps its body (one line; T3 owns the file this wave and was told).
- Card B2 evidence (ვანო decides deletion; U9): `config/spend_caps.json` `runpod.keep_stopped_pods` has **49** ids (Argon-1 said 50,
  Argon-2 47). `runpod check` (read-only, 2026-10-30 ~13:45 UTC): 49 STOPPED pods, each 0 GB, $0.00/day in total; billed $0.00 in 24 h;
  balance $10.40; no PROBLEM line.
- OPEN for T3/CP-18: `docs/CLOUD_RUNBOOK.md:18` and `:54` (CR-01, "Boot (TMR manifest) pods keep `boot_cmd`") still describe boot pods.
## 2026-10-30 — plan_v2 wave 1, T2 PR-C: CP-09+CP-10, CLIP-01..12 in `video-qa` and the gate rows `keyframes` / `clips`
- `training/video_qa.py`: `probe_container`, `audio_measure`, `decode_gray`, `clip_findings`, `qa_file(..., clip=)` add CLIP-01..12 (frame rate against the
  manifest and variable-rate, 8k+1 frames and 32-divisible size per BP-139, a dialogue shot has an audio track, audio length against picture, true peak
  against BP-50 with BP-50's own severity, words heard in a shot that should be silent, share of the dialogue heard, silence share, black / blown / flat
  frames, a frozen tail, frame 0 against its keyframe). Every number is `BP-164` (new, hypothesis, REVIEW); only CLIP-01 (rate), CLIP-04 (no track in a dialogue
  shot) and CLIP-06 (BP-50 ceiling) can FAIL, none from a hypothesis number. `training video-qa` gets `--fps --dialogue --expect-speech --transcript
  --keyframe --write` (`<clip>.video_qa.json` beside the clip). The transcript comes from a given file, else the free local transcriber when installed, never a paid read.
- `production_gate.py`: new rows `keyframes` (from `qa_log.jsonl`) and `clips` (from the sidecars); WAIT / BLOCKED / PASS; a still-picture episode gets neither row.
  The gate reads JSON only (the log through `keyframe_gate`'s reader, the clip sidecars as files) and runs no check, so a skipped check shows as WAIT instead of leaving no trace.
- Unverified items from the card, opened here: U3 `made_with.lora` and `bible_version` exist (`assets/library.py:77-99`), not in `assets_reuse.py`; U4
  `audio/local_words.transcribe` exists (faster-whisper, imported inside `_model`); U5 `qa/face_points.py`, `qa/prop_points.py`, `training/qa/image_stats.py` exist,
  nothing here depends on them; U6 `video_qa` holds the LT thresholds as quoted literals (table in PR-D).
- Tests red on main -> green: new `tests/unit/test_video_qa_clip_rows.py` (10: container, audio, frame rows; registry hygiene; transcript source; real ffmpeg
  clips; CLI sidecar; gate rows keyframes and clips; still episodes). Focused set 71 passed with PR-B's, `docs_lint` and `governance check` clean.
- OPEN: where clips live under an episode folder (`clips/**/*.mp4` is read) is for P6/P7; the REVIEW-only follow-up cards are in the PR body. No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 — T3-3 (CP-07, CP-08, CP-13): agent and skill pages carry the retirement banners (no pod, no money)
- `animated-universe` skill: description and a "Retired in part" banner (cut-out rig retired 2026-10-22, D-77/D-78); "Move a character" now points to the clip prompt (SHOT_PROMPTS KP) and the continuity card (CT); the rig bullets sit under `#### History (retired 2026-10-22)`. Silhouette, proportions, key light, squash-and-stretch rationing and long holds stay.
- `lora-coordinator`, `lora-dataset-auditor`, `lora-checkpoint-judge`: descriptions name the one LoRA (xworld style on Qwen-Image-2.1, D-80); the three-LoRA / edit / video wording and the A40 5.21 s/step figure moved under `## History (retired by D-80)` (measured rows: `config/job_speeds.json`). `lora-training` skill: "Current stack" line; "Settings that worked (Qwen-Image-2512 ...)" and "Video and edit LoRAs" under `## History (retired by D-80, lessons only)`; money numbers kept.
- `orchestrator` page and `docs/ORCHESTRATION.md` head: scope line, the still-picture D-43 route only until P6/P7/P8/P11. No step removed, no `model:`/`effort:` line touched.
- Test `tests/unit/test_t3_agent_skill_banners.py` (4 tests, red before, green after); `test_agent_governance`, `test_agent_roles`, `test_rig`, `test_lora_training` pass. Test adaptation: the plan's "History before the first `2512`" cannot hold for the skill (its description and banner name 2512), so the test pins History before the "Settings that worked (... Qwen-Image-2512" heading.
- OPEN: `animated-universe` "Stage a scene" still says "Motion ladder: rig motion first" and its checks ask for a named cycle; the card did not cover them, left unchanged. `lora-run-operator` page not in scope.
- Closes Fable F-04 (doc half), F-07, F-09; Argon-1 F-04 (doc half), F-13.
- T3-3 review fix (T2, PR #77): `config/job_speeds.json` `jobs.lora_train.rows` is empty, so the agent pages no longer say "measured rows live in ...". `lora-coordinator` G3 says the table is empty until the first xworld run is measured (`runpod cost --record-speed`) and that the old 5.21 s/step is only an estimate for Qwen-Image-2.1 (ask the creator); its History line says the same; the sentence is dropped from `lora-checkpoint-judge` (no cost step). `lora-dataset-auditor` marks its edit/video steps and the motion-caption check "(retired, see History)". Test `test_no_agent_page_claims_measured_lora_speeds_that_do_not_exist`.

## 2026-10-30 — T3-4 (CP-06, CP-15, CP-10 link rows): PRODUCTION_RULES and the Kokoro modules (no pod, no money)
- `audio/narrate.py`, `timings.py`, `visemes.py`: first docstring line `RETIRED by D-39 ...`; `python -m explainer_engine.audio.narrate` now exits 1 with the same words (no model load); imports and functions untouched, `voice_layer.py` not edited.
  Adaptation: the guard sits directly after `from __future__ import annotations` (a statement before it is a SyntaxError) and before every other import.
- `docs/PRODUCTION_RULES.md`: "Kokoro only for drafts" -> "Kokoro retired (D-39), drafts are ElevenLabs first takes"; "voice (Clyde)" in the universal list -> `config/channel_voices.json` (card C10); both "Pro plan" -> the plan recorded in D-52 (Creator), linked; section 2 gate table gains rows 7.5 `keyframes` and 7.6 `clips` (links to KEYFRAME_GATE.md and training/video_qa, wording "wired as production_gate rows keyframes/clips ... run by hand until then"). The `1 credit about $0.00018` arithmetic is not in AUDIO_SYSTEM.md, so it stays. The history rows 105/126 that name Clyde stay (feedback log, dated).
- Test: `tests/unit/test_repo_hygiene.py::test_kokoro_modules_carry_the_d39_banner_and_narrate_cli_refuses` (red before, green after; hygiene, audio_timing, voice_layer, docs, production_gate pass). The plan's table-style assertion became a regex on `**keyframes**` / `**clips**` because the gate table uses bold names.
- OPEN: section 4a still states "cap $10 in total, stop at 80 %" for Gemini (a cap number outside `config/spend_caps.json`); the card did not list it.
- Closes Fable F-06, F-11 (doc rows); Argon-1 F-17, F-19 (Kokoro half), Q2 row 9; Argon-2 F-23 (banner half).
- T3-4 review fixes (T2, PR #79): "the the" typo in PRODUCTION_RULES; `docs/AUDIO_SYSTEM.md` narrate paragraph now opens with the D-39 retirement (the CLI refuses, the old path is history); banner line of the three Kokoro modules wrapped to repo width; row 7.6 says the video_qa JSON is kept beside the clip; the stale duplicate `CP-07/08/13` routing row dropped.

## 2026-10-30 — T3-5 (CP-14, CP-18): money documents link the caps; the watchdog is named a backstop (no pod, no money)
- `COST_AND_TIME_MODEL` ledger: the Gemini and RunPod cap cells -> "the ceiling in `config/spend_caps.json` (D-56)" (spent-so-far figures stay as history); `ORCHESTRATION` money-ledger paragraph: the 2026-10-16 night-run caps are history, ceilings in force live only in `config/spend_caps.json`; `VIDEO_PARAMETER_SPEC` P-110 cell; `PROJECT_BRIEF` budget sentence (Gemini `US$10` replaced by the link; the vidIQ 200 stays, it has no line in the caps file yet).
- `CLOUD_RUNBOOK` stop-path row 3 (watchdog): names `.github/workflows/watchdog.yml` and its cron `*/10 * * * *`, says GitHub may delay a schedule by hours (4-7 h observed), so it is the backstop and never the stop a plan relies on; the in-pod dead-man and the session guard are the primary stops.
- Tests (`tests/unit/test_spend_caps_single_source.py`, 2 new, red before, green after); `test_docs` and `docs_lint` pass.
- `CLOUD_RUNBOOK.md` line 18 is marked history and CR-01 says boot (TMR manifest) pods are retired by N-01 (`preflight_create` refuses a body whose `cmd` is not `pod_wrapper.sh`; `boot_cmd` stays a text builder). Test `test_runbook_no_longer_says_boot_pods_run`. `test_cloud_stop_paths.py:344` was already stamped by T1 in #70.
- Closes Fable F-12; Argon-1 F-16, Q2 row 7.
- T3-5 review fixes (T2, PR #80): the two stale "prepared locally" routing rows (CP-07/08/13, CP-06/15) are not in this PR; the Gemini cell names `per_episode.gemini_usd` and the RunPod cell the `runpod` lines of `config/spend_caps.json`; the spent cell says "of the then US$10 cap"; P-110 names the key. (T3-6's routing row is checked for the same duplicates before it opens.)

## 2026-10-30 — T3-6 (CP-16, CP-19) + evidence for cards A3 and the Shorts card (no pod, no money)
- `DECISIONS_AND_OPEN_QUESTIONS` Q2 (Kit rejected D-04; permanent hosts are card A1, open for ვანო), Q3 (D-39), Q4 (superseded by D-31/D-32) marked decided; `QA_SPECIFICATION` Q-E11 asks about every named character's approved reference sheet (D-55); Kit table rows and paragraphs of `STORYBOARD_SCHEMA` and `CREATIVE_STYLE_BIBLE` prefixed `(history, D-04 rejected 2026-10-15)`, nothing removed (`assets/characters/kit/`, `test_kit_sheet.py` untouched, deletion is card 6); `CRAFT_CURRICULUM`: "Exception: the fps row is decided by D-85 (24 fps, no pulldown)", every other row stays pending (card 7).
- Test `tests/unit/test_t3_decisions_docs.py` (3, red before, green after); `test_craft_checklists`, `test_docs`, `test_kit_sheet` pass, `docs_lint` 0. The Q-line locator matches the `- Q2 ` list markup.
- OPEN: `CREATIVE_STYLE_BIBLE` line 9 (tone: "Kit's reactions") is a mention, not a Kit paragraph, left as is.
- Evidence for the voices card (A3 vs D-62/63/68), no decision taken. `explainer_engine/production/silent.py:4-5` "PV-55 binds it: a cast member marked ``traits.real_person`` has no voiced line"; `:254` `real = {h for h, c in doc.get("cast", {}).items() if traits(c).get("real_person") and traits(c).get("living", True)}`; `:258` `if line.get("speaker") in real and voiced(line):` -> `:259-260` "is a real person and must not be voiced (voiced: false, shown as bubbles; D-62)"; `production/validate.py:418-423` reports PV-55 and PV-56 (`check_reported_dialogue`, D-63). The check keys on the cast member's `traits.real_person` (and `living`, default true) and the line's `voiced` flag, both in the production script.
- Evidence for the Shorts card. `production/validate.py:519-527` PV-34 with `len(shorts) >= 5`: Shorts without a style (SS-01) and fewer than `need = min(6, max(3, len(shorts) * 6 // 10))` distinct styles are REVIEW; `:530` same style right before another (SS-02); `:535-537` loop and pointer endings (SS-04); `:540-546` with `len(shorts) >= 6`: `short_band` (secs <= the first BP-12 band's top) and `long_band` (secs >= the second band's bottom) each need at least 3, else REVIEW (SS-06); `:552`, `:561` first cut inside the hook and visual events per 10 s. So PV-34 checks styles when there are 5 or more Shorts and the two length bands (3 each) when there are 6 or more.
## 2026-10-30 UTC: plan_v2 T1 / N-02, paid BFL calls of `training/cast/sheet.py` run only inside a ledger (one unplanned $0.018, see below)

- `explainer_engine/training/cast/sheet.py` (Argon-2 F-05): `draw()` and the real path of `world()` open the run ledger first
  (`_run`): no ledger = `ValueError("refused: paid BFL calls run only inside a ledger (D-56); pass --ledger")`; `world()` builds
  `BFL(out, run=run, key=k)` (it had no run), so every picture reserves on the ledger's `bfl_usd` (for a new ledger
  `config/spend_caps.json` `per_episode.bfl_usd`) with the ledger's 80 % stop; a `--budget` above that cap is refused (no number in the
  code). The local `spent` counter stays as the budget display. CLI: `draw|world --yes` without `--ledger` is an argparse error naming
  `--ledger`; the estimate without `--yes` stays free and unchanged. `world()` with an injected `generate` (its unit tests) needs no ledger.
- `explainer_engine/imagegen/providers/bfl.py` (C3; BFL already carries `run`): `_request` (the paid HTTP call) refuses `run is None`
  (`ProviderError`); a cache hit in `generate()` never reaches it. No other `BFL(` caller outside `sheet.py` (paint goes through
  `providers.get(..., run=run)`).
- Tests: `tests/unit/test_money_path_fences.py` N-02 section (5: CLI `draw/world --yes` without a ledger, no `BFL` built without a run
  and built with one, budget above the cap, `BFL._request` without a run). Red on main: 5 failed. No existing test changed.
- **Unplanned spend, 2026-10-30 13:45 UTC: $0.018 on BFL (2 x Klein 1k, $0.009 each).** The first red run of the CLI test ran the OLD
  `sheet.main(["draw", ..., "--yes"])`; this session had a BFL key in its environment (`BFL_API_kay`), and the old code drew without a
  ledger, which is the hole this card closes. The pictures (`c000.png`, `p001.png`, `spend_log.jsonl`) are kept in the project files
  `explainer-engine/blueprint_2026-10-29/paid/plan_v2/t1_bfl_incident/`. The test now removes every `KEY_ENV` variable and blocks
  `BFL._request` before it calls, so it fails without a paid call on code without the guard; the red run was repeated that way.

## 2026-10-30 UTC: plan_v2 T1 / N-03, VARIANT_CHOSEN needs the variants file its approval binds; the other gates' artifact binding is OPEN (no pod, no money)

- Verify (Lock 5) against Argon-2 F-04: `core/store.py` has no `APPROVAL_GATES` or `_HEX64`; the gates are `GATES` and
  `_check_approval(..., bind=True)` asks only for a non-null `sha256`; `job_manifest.schema.json` makes it 64 hex. So "any 64-hex string
  is accepted as a creator approval" is true. `move("VARIANT_CHOSEN")` ran the variants check only `if variants is not None`: true.
  The artifact half of the card is **not reproducible as written**: no production code calls `record_artifact`, the keys are free-form, and
  CN-04's table binds most gates in prose only ("the scenario file", "the words' sha256 (script_approval)", "the paint/pod plan hash",
  "`sample_approval.json`", "the review bundle", "his message"); no gate has a key that both CN-04 and the code name.
- `explainer_engine/core/store.py`: `move("VARIANT_CHOSEN")` without `variants=` is refused before any write (`ContractError`,
  "VARIANT_CHOSEN needs variants=... (CN-04, OR-31)"); the existing check (the picked id is a variant, the approval's sha256 is the
  `variants_sha256` of the unchanged file) now always runs. No gate→artifact map was added (D1: nothing to map without guessing).
- Tests: `tests/unit/test_money_path_fences.py` N-03 (a creator approval with the right hash but no file is refused and writes nothing;
  `"a" * 64` with the file is refused; the right pair passes). Red on main: 1 failed. `tests/unit/test_lifecycle.py`: new `variants_file()`
  helper; `step()`, the back-path walk and the adopt-chain walk pass the variants file and its hash when they enter VARIANT_CHOSEN (an
  allowed path, a pick without its file, is now a refusal); `test_a_creator_gate_binds_the_sha256...` expects the variants hash instead of
  the placeholder `"c" * 64`.
- OPEN (CN-04 wording is OR-22, for ვანო/coordinator): (1) which manifest artifact key each of SCENARIO_APPROVED, SCRIPT_APPROVED,
  BUDGET_RESERVED, SAMPLE_APPROVED, REVIEW_APPROVED binds, and who records it (`record_artifact` has no production caller); until then those
  approvals are checked for kind, `by`, `ref` and a 64-hex `sha256` only. (2) `adopt()` into VARIANT_CHOSEN or later checks the approvals but
  not the variants file (CN-04: "`adopt` is held to the same gates"); closing it adds a `variants=` argument to `adopt`.

## 2026-10-30 UTC: plan_v2 T1 / follow-up of T5's reviews: adopt binds the variants file, create() re-checks the body, the hook catches every create spelling (no pod, no money)

- `explainer_engine/core/store.py`: the VARIANT_CHOSEN check moved into `EpisodeJob._check_variants` (one home) and `adopt()` takes
  `variants=`: adopting into VARIANT_CHOSEN or later checks the file exactly as `move` does (CN-04: "`adopt` is held to the same gates";
  T5's review of N-03). Nothing is written when it fails.
- `explainer_engine/cloud/runpod.py`: `create()` checks again what the body alone decides, after the stamp: it runs `pod_wrapper.sh`
  (OR-21) and its image is pinned (`config/cloud_pins.json`). `preflight_stamp` is public, so a stamp can be forged with one call (T5's
  review of N-01); a forged stamp now sends neither a boot pod nor an unpinned image.
- `explainer_engine/cloud/hooks.py`: one more BYPASS pattern, a Python command that names `runpod` and calls `create(`: a bare imported
  name (`from ...runpod import create; create(`) and an alias (`runpod as R; R.create(`) were allowed (T5's review of CP-01).
- Tests: `tests/unit/test_money_path_fences.py` gains 3 hook cases, the forged-stamp test and the adopt test (red on the N-03 head:
  5 failed, 30 passed; green: 35 passed). Setup only: `tests/unit/test_runpod.py::stamped()` makes its hand-made body a script pod's
  body (wrapper command, pinned image) before stamping; `tests/unit/test_lifecycle.py` writes the Napoleon variants file in the `folder`
  fixture, `gates_up_to` carries its real hash, and the three adopts that pass the pick name the file. No assert removed.
- OPEN: none new. The gate→artifact binding of the other gates stays with ვანო (options sent to the coordinator).

## 2026-10-30 UTC: plan_v2 T1 / N-03 option A, every person's gate binds the hash its own tool records (ვანო's choice, no pod, no money)

- ვანო chose option A (2026-10-30 14:48 UTC, through the coordinator): SCENARIO_APPROVED, SCRIPT_APPROVED, BUDGET_RESERVED,
  SAMPLE_APPROVED and REVIEW_APPROVED are entered only with `artifact=` (what the person approved), and the approval's sha256 must equal
  `core/store.bound_sha256(gate, artifact)`: the scenario file's sha256 (PV-45); the script's words only,
  `script_approval.words_sha256` (OR-17, so delivery tags may still change); the approved plan file, refused when a paint plan no
  longer matches its own `plan_hash`; the `script_sha256` that `sample_approval.json` binds, for an unchanged script (OR-19); the
  review bundle folder as one hash (`store.bundle_sha256`: every file's relative path and sha256, sorted; owner=claude, no bundle
  manifest existed). `adopt()` takes `artifacts={gate: path}` and checks every bound gate on the way the same way. A refusal writes
  nothing. PUBLISHED_PUBLIC stays the creator's click with a ref (CN-06); VARIANT_CHOSEN keeps its variants file. These match the
  "binds" column of the CN-04 lifecycle table in docs/CONTRACTS.md, whose wording is unchanged.
- Tests: `tests/unit/test_money_path_fences.py` option-A section (5 gates: no artifact refused, `"a" * 64` refused, the tool's hash
  passes, nothing written on a refusal; words-only script hash, a changed paint plan, a sample for another script, a changed bundle).
  Red on the follow-up head: 6 failed. Setup only: `tests/unit/test_lifecycle.py` gains `artifact_for()` (the artifact and its tool's
  hash per gate); `step()`, the planner budget move, `gates_up_to`, the adopt calls that pass a bound gate and the adopt-chain walk
  name the artifact and carry its hash; the follow-up's adopt test names its scenario file. No assert removed.
- Amended after T5's review (ვანო's picks "ა ა ა", 2026-10-30 14:56 UTC): BUDGET_RESERVED for a pod binds the sha256 of its start
  script committed under `explainer_engine/training/pods/` (`cloud/dryrun.sha256_of`, the ledger's `pod_plans.script_sha`); any other
  non-plan file, or a copy of the script outside that folder, is refused. SAMPLE_APPROVED binds the sha256 of `sample_approval.json`
  itself (still only while its script is unchanged). REVIEW_APPROVED binds the sha256 of `<bundle>/bundle_manifest.json`, written by the
  new `explainer_engine/qa/review_bundle.py` (`write` / `check`, CLI `python -m explainer_engine.qa.review_bundle write|check <bundle>`:
  every file's relative path and sha256); the gate re-checks the bundle against it (a changed, missing or unlisted file is refused).
  `store.bundle_sha256` is gone (it was added in this same PR). Tests: a pod script passes and a markdown plan or a copy outside the
  folder is refused; the sample binds its file; changed, added and removed bundle files are refused; the CLI round trip.
## 2026-10-30 — plan_v2 wave 1, T2 PR-D: CP-17, numbers a validator reads go through the registry (BP-165, BP-166)
- `standards/sourced_rules.json`: `BP-165` (keyframe gate tries per shot `max_tries` 3 and `retrain_at` 15, KG-14/KG-15) and `BP-166` (the review-only LT-53/54/55/59..62
  numbers of `video-qa`), both hypothesis / REVIEW, `sources: []`, with a `next_step`. `qa/keyframe_gate.py` reads `MAX_TRIES` / `RETRAIN_AT` and
  `training/video_qa.py` reads its review-only numbers through `SR.T(...)`. The FAIL thresholds (`flicker_max`, `morph_second_max`, `edges_keep_min`, `sat_loss_fail`) stay in
  `lora_rules.json` `video_qa` (house, dated) and are not moved: a hypothesis registry row may not carry a FAIL. `docs/LORA_TRAINING.md` LT rows name the BP id; `docs/SOURCED_RULES.md` regenerated.
- Test red on main-era code -> green: `test_sourced_rules_sync.py::test_cp17_the_keyframe_gate_and_video_qa_numbers_come_from_the_registry`. Focused set 61 passed, `docs_lint` 0 findings,
  `governance check` ok. Defaults are unchanged (every moved number keeps its value), so no verdict moves.
- `docs/PRODUCTION_RULES.md` rows 7.5 and 7.6 (T3-4's wording "until they land the two CLIs are run by hand" was stale once CP-10 landed): they now name the `production_gate` rows `keyframes` and `clips` and the `<clip>.video_qa.json` sidecar. Coordinator's ask, 2026-10-30.
- T1's review (#82): the ten BP-166 numbers are no longer copied in `lora_rules.json` `video_qa` (it keeps `about` and the four FAIL keys); the pod scorer
  `training/pods/xworld_v1_score.py` reads `ink_max` through `SR.T("BP-166", ...)` and is listed in BP-166 `enforced_by` (a local scoring step run after the pod; no approval binds its sha);
  the test now pins the literal starting values and asserts no BP-166 key is in `RULES["video_qa"]`, so a copy cannot come back. LT-56/57 rows carry "(number: BP-166)".
- OPEN: BP-165/BP-166 need two source types or the creator's dated word before any of them can become FAIL. No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 — plan_v2 wave 1, T2 PR-E: N-08, a generator admission needs the creator's recorded word and a key for its report; SD-13 runs `item_problems`
- `governance/records.py`: `generator_admit` joins `ACTIONS` (target `<generator>:<kind>`); `governance ok generator_admit ...` records his word in `jobs/creator_ok.jsonl`.
  `audio/generator_gate.admit` refuses a `creator_ref` that does not resolve to such a record (`records.find`, the lookup the channel voice uses, VC-08), and refuses a
  sheet without `sheet_key.json` beside it or with a key made for another report (`report_sha256`). It stores `picks_for_generator` / `picks_total` for the eye; no minimum is
  invented (D8: his recorded word is the gate).
- `audio/sound_director.py` SD-13: a free-generator take (source kind `open_model`) now runs `generator_gate.item_problems` instead of a non-empty-admission check, so a missing
  admission, a wrong kind or a wrong model is a FAIL naming the problem.
- Tests red on main -> green: `test_generator_gate.py` (3: recorded word, key for this report, picks recorded without an invented minimum) and
  `test_sound_director.py::test_a_free_generator_take_without_an_admission_is_sd13_and_fails`. `docs/AUDIO_SYSTEM.md` names the record. Existing admit tests now record the word first (setup;
  assertions unchanged).
- OPEN (needs ვანო): `assets/audio/generator_admission.json` must be added to `protected_files` in `config/model_routing.json` so that editing it by hand is refused without his word (that file is protected config; not touched here).
  T1's review (#83): `admit` also refuses a sheet with any pair not answered A / B / same ("answer every pair of the sheet first"); the share stays for the eye. `records.add` refuses a wildcard `generator_admit` target. The lookup has no age window (an admission stands until replaced), said in the docstring.
  OPEN: whether a minimum share of picks for the generator is wanted is his call (none invented). No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 — plan_v2 wave 2, T4 PR-1: the creator's word on hosts (D-89), the dialogue voice (D-90) and the craft conflicts (D-91)
- `docs/DECISIONS_AND_OPEN_QUESTIONS.md`: D-89 (card A1 NO, his word of 2026-10-30 16:13 UTC; `p12e_hosts` stays unspent), D-90 (card A3 option A, "Fixed ElevenLabs voice +
  LTX audio-in", confirmed 16:16 UTC: a character has one fixed ElevenLabs voice, the line is read first and the take conditions the clip; supersedes the native-voice answer),
  D-91 (the 12 craft conflicts: the rule in force stays, decided on his delegation, approved by the coordinator 16:54 UTC; row 8 stays D-85). D-88 carries an amendment pointer; Q2 says A1 is answered.
- `docs/SCRIPT_ENGINE.md` "Dialogue audio" row and stage-7 row, `.claude/agents/voice-caster.md` step 7 (no `ltx_voice_text`; cast, read first, take conditions the clip), `docs/AUDIO_SYSTEM.md`
  (dialogue-route note under the SD-12 matrix), `docs/CRAFT_CURRICULUM.md` status line. `docs/blueprint/decision_queue.json` cards A1 and A3 carry his newer answers; `STATUS.md` regenerated.
- Test red on main -> green: `tests/unit/test_voice_route_docs.py` (3 tests). Docs say "Not built yet": the audio-in wiring and the lane decision are P6/P7; the code still reserves post-hoc windows.
- OPEN: whether a deceased historical figure may be voiced (PV-55 keys on `real_person`, D-62 bars only living people); the exact wording of D-91's rows is the "rule in force" column of the table. No pod, no API call, nothing deleted.
- Decision log: D-89, D-90, D-91 added; D-88 amended.
## 2026-10-30 — plan_v2 wave 1, T2 follow-up: `generator_gate._picks` counts distinct pairs (T1's note on #83)
- `_picks` kept a count of answered rows, so a pair repeated in the sheet could stand in for a blank one and `admit` would pass. It now keeps one answer per pair: the total is the number of
  distinct answered pairs, and a pair answered twice with different answers is refused ("answered twice"). No minimum share added (still his call).
- Test red on main -> green: `test_generator_gate.py::test_a_repeated_row_cannot_stand_in_for_a_blank_pair`. No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 — plan_v2 wave 2, T4 PR-2: CP-12 route notes, N-06 docstring scope, `select_screen` moves to its episode
- `.claude/agents/edit-planner.md` and `.claude/skills/shot-visuals/SKILL.md` open with the **Route note** (a still-picture episode D-43 vs an animated one D-77/D-80, never both). `shot-visuals`
  is sectioned, no rule text removed: `## Still-picture route (D-43)` (everything from "What went wrong" through "One scene, one room" and "Procedure"), `## Animated route (D-77/D-80)` ("Animated shots", moved
  after the Procedure), `## Both routes` (cinematography). Neither page carried a live 2512 or Edit-2511 line on current main.
- N-06, docstrings only, logic untouched: `imagegen/routing.py`, `standards/hook.py`, `production/staging.py` each open with a Scope line naming the D-43 still-picture route.
- `production/select_screen.py` and its test moved to `examples/syndicate_wars_ep1/` (git rename, content as before; run `python examples/syndicate_wars_ep1/select_screen.py <dir>`); `pytest.ini` `testpaths` adds that folder so
  the three tests still run; the one code comment (`production/shorts.py`) names the new path. No code imported the module.
- Tests red on main -> green: `test_agent_governance.py` (three T4 tests). The registry text `sourced_rules.json` BP-87 / SC-12 still say `select_screen.py` (name only, true).
- OPEN: none. No pod, no API call, nothing deleted (a move, not a deletion).
## 2026-10-30 — plan_v2 wave 2, T1: `assets/audio/generator_admission.json` is a protected file (N-08 follow-up)
- `config/model_routing.json` `protected_files` gets `assets/audio/generator_admission.json` (60 minutes), like `config/channel_voices.json`
  (D9 question 12). The creator's word: 2026-10-30 17:07 UTC, cmsg_01Hnu5zB86sjUj5GtTgaUkPW8msPdnCCDWn3ATgkWHUK4i ("კაერგი მაშ დაამატე",
  answering cmsg_01Hnu5zB86sjUj5GtTgaUkPWXzbqo24EyY822YqDJXSjAs), recorded as `protected_config config/model_routing.json` before the edit.
  An Edit, Write or shell writer on the admission file now needs his `protected_config` word; `generator_gate admit` keeps its own gate
  (the `generator_admit` word, BP-162) and is not refused by the shell guard. `generator_gate` docstring and `docs/AUDIO_SYSTEM.md` say so.
- Test red on main -> green: `tests/unit/test_admission_protected.py` (the path is the one `generator_gate` writes; Edit/Write/echo refused,
  cat free; a stale word refused, a fresh one unlocks only that file; the `admit` command passes the guard). No pod, no API call, nothing deleted.

## 2026-10-30 — plan_v2 wave 2, T5 N-09: D-80 prompt contract, one trigger home, no wldnk / nextpose / scene LoRA in composed cards
- `training/lora_rules.py` (new, stdlib): `load()` and `trigger()` read `training/lora_rules.json`, the one home of the trigger; its `dataset.trigger` is now `xworld style`
  (the word `training/pods/xworld_v2_data.py` captioned the dataset with, LT-79). `training/audit.py`, `qa/style_prompt.py` (so `compose/episode_look.py`) and
  `scripting/film_shots.py` read it; `examples/napoleon_vs_genghis/episode.py` takes its `style.trigger` from it.
- `scripting/film_shots.py`: next poses open with `<trigger>, a later frame of the same continuous animated shot, same camera:` (was `nextpose, `), cuts open with the trigger;
  every picture card carries `lora: "style"` and `style_prompt.INFERENCE` (no `scene` LoRA: one LoRA, next poses and cuts in its edit mode, D-80). `style_check` FAILs (LT-65)
  a `style.trigger` other than the home and any keyframe / next-pose / cut prompt that does not start with it or starts with a retired prefix. `shot_prompt_lint` strips the
  new edit opener instead of `nextpose,`.
- Fixtures regenerated with the repo CLIs: `examples/film_shots/bus_in_the_ice_age.json`, napoleon `film_shots.json`, `prompts.json` (the committed copy was stale: 2512 / wldnk
  inference), `shotlist.md`; `script_variants.json` only its `dossier_sha256` (the hash of the changed `film_shots.json`, `variant_plan napoleon --write`).
- Test red on main -> green: `test_d80_prompt_contract.py` (4: one trigger home, compose emits only the D-80 stack and every card passes `keyframe_gate.check_stack`,
  `style_check` FAILs a retired trigger, the napoleon fixture is on the stack). Existing tests changed only their expected trigger or the card selector (`kind == "keyframe"`
  instead of `lora == "style"`, the same set before this change). `docs/LORA_TRAINING.md` LT-01 links the home instead of stating the word.
- T1's review (#87): the pod scripts' own `TRIGGER` literals (`training/pods/xworld_v2_data.py`, `xworld_v1_build.py`, the words the LoRA was captioned
  with) are pinned to `lora_rules.trigger()` by `test_one_trigger_home`; the scripts themselves are not edited (their sha binds a pod BUDGET approval, N-03).
- OPEN: `style_prompt.INFERENCE["lora"]` is still `None` ("no LoRA until the creator rates the new one") while D-83 / LT-79 name xworld_v2 ck3000 at 0.7; the next-pose wording vs
  the xworld edit caption shape; wldnk-era `BODY_WORDS` / `STYLE_TAIL` / `video_sentence`; `examples/continuity/napoleon_tent.json` style_line; `PROMPT_PACKAGE.md`;
  `docs/SHOT_PROMPTS.md` rows 23/87 and `docs/SCRIPT_ENGINE.md` (T4); `qa/blind_check.py` (T2). No pod, no API call, nothing deleted, no schema change.
- Decision log: none moved.

## 2026-10-30 — plan_v2 wave 2, T4 PR-3: BP-167 delivery defaults of the animated route
- His word of 2026-10-30 16:13 UTC (item 3, yes to the delivery numbers), house D-59: `standards/sourced_rules.json` `BP-167` {long_minutes 15, width 2560, height 1440, fps 24, shorts 5}, status house, severity REVIEW,
  scoped by the coordinator (17:23 UTC) to the **animated route only**. One reader, `core/delivery.py`; `core/store.EpisodeJob.create(fps=None)` takes the delivery fps when a job names none (a named fps is kept).
  `docs/SOURCED_RULES.md` regenerated; `docs/VIDEO_PARAMETER_SPEC.md` P-10/P-12/P-13/P-100 point to BP-167 without restating a number (the older values stay as the still route's).
- Tests (all fail on main: no module/row): `tests/unit/test_delivery_defaults.py` (7: house + dated, 15 min, 2560x1440, 24 fps equal to BP-139's native and `film_shots.FPS`, five Shorts, job default and named fps, and that the
  still route and the schema default are unchanged).
- OPEN (not edited, TECH_QUESTIONS questions 29-31 (project files)): `production_script.schema.json` `episode.fps` `default: 30` inside `enum [24,25,30,60]` (a default change is a schema edit, a version bump to be reported before any edit, invariant 7);
  the still route (`timing.py`, `assemble.py`, `motion_lint.py`, `finish/speed.py`); the Shorts' frame rate (`clip_shorts.FPS` 30) and size; PV-34's count for five Shorts. Width, height, minutes and shorts have no consumer yet (P7/P8).
- Note on #88: the moved `select_screen` tests run through `pytest.ini` `testpaths` (CI and a bare `pytest -q` run them; `pytest tests` does not), TECH_QUESTIONS 32.
- No pod, no API call, nothing deleted.
- Decision log: none moved (a registry row).

## 2026-10-30 — plan_v2 wave 2, T4 PR-4: CP-11, the documents that described 2512 / Edit-2511 / wldnk as "in use" now say it is history (after N-09 #87)
- `docs/SCRIPT_ENGINE.md`: the stage 6 row and the "In use now" Keyframe and Next-pose cells name Qwen-Image-2.1 + the xworld_v2 LoRA (D-80, ZI-06, KG-16), continuity through continuity_card/1, weights/steps/sizes by link to LT-79;
  the trigger is `<trigger>` read through `lora_rules.trigger()` (N-09's one home); the next-pose opener is the one N-09 composes. The old cells moved to `### History (banned by D-80)` under the table.
  `docs/KEYFRAME_GATE.md` "The flow" (masters and next poses on 2.1 with references, the Edit-2511 step marked banned); `docs/TOOL_STRATEGY.md` current routing (D-50 provider choice for the still route, the pod route for animated);
  `docs/UNIVERSAL_RULE_BASE.md` UR-22 and UR-25 scoped to the D-43 still-picture route (no rule text removed; PV-11 and `world/resolver.py` untouched, the U2 grep stays an N-09 follow-up);
  `docs/SHOT_PROMPTS.md` kind table, model rows (the retired rows kept as History, their Helps/Hurts not yet re-measured on 2.1), intro and `lora` sentence (T5's note on rows 23/87);
  `docs/VIDEO_PARAMETER_SPEC.md` a scope line: the "Allowed" ranges are the still route's, the animated delivery defaults are BP-167 (T3's note on #89).
- Tests red on main -> green: `test_docs.py` (2 new: no live 2512/Edit-2511/wldnk/`nextpose,` outside a History block in SCRIPT_ENGINE, KEYFRAME_GATE and SHOT_PROMPTS; UR-22/UR-25/TOOL_STRATEGY/VIDEO_PARAMETER_SPEC scoped).
- OPEN: `qa/style_prompt.INFERENCE["lora"]` is still `None` (T5's open item), so SCRIPT_ENGINE says "see LT-79" and not a LoRA weight; `docs/PROMPT_PACKAGE.md` was not touched (T5's list). No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 — plan_v2 wave 2, T4 PR-5: follow-up to CP-11 (ASSET_COMPOSE step 3, the SHOT_PROMPTS banner)
- `docs/ASSET_COMPOSE.md` step 3 no longer says assets are drawn with Qwen-Image-2512 (now Qwen-Image-2.1 + the xworld_v2 LoRA, D-80, settings LT-79); the `docs/SHOT_PROMPTS.md` line-3 banner says the rows are on the new stack since N-09 and that the retired rows' Helps/Hurts are not re-measured (T3's notes on #90).
- Test red on main -> green: `test_docs.py` (1 new). The LoRA weight 0.7 (LT-79) vs 1.0 (code) is T5's open item, already in TECH_QUESTIONS. Other docs that still name 2512 (`LORA_TRAINING`, `PRODUCTION_RULES`, `ARCHITECTURE_PLAN_2026-10-22`, `TOOLING_RESEARCH`, `DECISIONS`) are history or decision text and were not touched. No pod, no API call, nothing deleted.

## 2026-10-30 — plan_v2 wave 2, T5 N-07: the visitors' costume and the judge's visitors premise come from the episode's world
- `production/compile.py`: the module default `VISITOR_COSTUME` (the Stone Age Day 1 frock coats) is gone. `_visitor_costume(doc, world)` returns the episode's
  `world.visitor_costume`, else the codex costume of its resolved visitors' eras (`world/resolver.resolve`), and `""` for a world without visitors.
  The Day 1 text now lives in the Stone Age worlds as `visitor_costume` (`examples/stone_age/world_spec.json`, `day1_v5`/`day1_v6` `world_spec.json`,
  `week1_v1`/`day1_v7`/`ep1_v1` `production_script.json`; the schema's `world` is an open object, no schema change). Compiled prompts of all five committed
  production scripts (three Stone Age, Titans, Syndicate Wars) are identical before and after (checked by compiling on main and on the branch).
- `qa/visual_judge.py`: the module default `VISITORS_NOTE` (the 1700s-1900s scientists, pasted into every episode's judge prompt) is gone. `visitors_note(world)`
  is the world's own `visitors_note`, else built from its resolved visitors (era, up to four people, codex costume), else empty; a world without visitors gets no
  visitors sentence. The `era_objects` question is built per world: the visitors' exemption only when the world has visitors, the "flag things like" examples from
  the world's own `absent` list (it was the Stone Age list for every episode). The not-yet line keeps its place before the stakes line.
- Test red on main -> green: `test_costume_from_world.py` (3: no visitors = no costume and other visitors get their own era's costume; the judge premise comes from
  the world, Titans has none; the Stone Age episode keeps its frock-coat costume and gets its visitors in the review request). `test_sheet_review.py` now expects the
  Day 1 text from the Stone Age world instead of `C.VISITOR_COSTUME` (expectation only).
- Facts that differed from the card (Argon-2): there is no `examples/*/world.json` (worlds live in `world_spec.json` and the production scripts' `world`);
  compile already gave no costume without visitors, the default leaked for visitors of any era; the judge's `visitors_note` override never reached a real episode
  (`sheet_review` passes the resolved world, which drops the key). `examples/stone_age/day1_v5/build_v5.py` and `look_test/build.py` keep their own copies (episode
  scripts, not engine code).
- T1's review (#92): one costume source. `compile.world_of` now carries `visitor_costume` (the episode's words, else the codex costume, else "") and
  `visitors_note` uses it, so the judge is told exactly the clothes the pictures were painted with (the first head told the judge the codex costume
  while the Stone Age pictures used the episode's words). The pocket-watch exemption of the `text` question is also visitors-only now.
  Deliberate judge-prompt change for the Stone Age episode: the note names the visitors' era, four of its people and their costume instead of
  "scientists from the 1700s to 1900s"; the `era_objects` exemption reads "their own clothes, tools and pocket items" and its examples come from the
  world's `absent` list (pottery, metal, iron, bronze, wheel) instead of the hard-coded Stone Age list.
- OPEN: none. No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 night run: Claude API lines raised for review, change plan, fix desk and result check
- The creator's card answer (2026-10-30 20:46 UTC, "yes, all"): `claude_api.jobs` gets `final_review` 8, `change_plan` 8, `fix_desk` 8, `result_check` 10 (34 in all).
  Paid from `plan_v2` 28 -> 18 (its work is done), `J3` 12 -> 4, `J4` 2.98 -> 0, `J5` 3 -> 0, `reserve` 16 -> 5.98; the total stays 95.0. Pod lines are unchanged
  (P12a 0.50, P12b 3.00, P12e deferred). Technical and rule questions go to Fable through the API in his place; only money needs his word.
- Test: `test_real_spend_caps_file_holds_the_or24_caps` pins the new lines and the unchanged total.
- OPEN: none. No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 — change plan T02: RETIRED banners on six old-era modules (D-80, D-39)

- `aivideo/pod/montage.py`, `fixhub.py`, `watchdog.py`, `aivideo/shotplan.py` carry the D-80 banner, `audio/voice_layer.py` the D-39 banner,
  `production/rig.py` the creator's 2026-10-22 banner (first docstring line). The three pod scripts raise `SystemExit("RETIRED ...")` before any
  import, `rig.py` in its `__main__` block; `shotplan.py` and `voice_layer.py` are banner only (their functions stay importable and tested).
  `kf.py`/`clips.py` (already RETIRED) import `fixhub` and start `watchdog.py`, so they now stop there if ever run. Nothing deleted.
- Test: `test_old_era_modules_carry_a_retired_banner_and_their_cli_refuses` (docstrings read with `ast`, no import).
- OPEN: none. No pod, no API call.
## 2026-10-30 change plan T03: the five P12a scripts pinned to their dryrun sha256
- `tests/unit/test_p12a_scripts.py::test_the_p12a_scripts_on_main_are_the_ones_the_plan_dryran` holds the sha256 of `p12a_A.sh` .. `p12a_E.sh` (plan §1.2); a changed script
  fails a free test before any pod and needs a new OR-24 confirmation and a new dryrun record first. All five match on `main` today.
## 2026-10-30 T05: `runpod create --test <name>` binds the ledger to its paid test
- `create` reads `--test`: a ledger with `meta.test` needs `--test <that test>`; a wrong name, or `--test` on a plain ledger, is refused before any RunPod call.
- Test: `test_create_requires_and_checks_the_test_name_of_a_paid_test_ledger` (cases: no flag, wrong name, plain ledger, right name reaches the fake).
  The helper `_create_p12a` in `test_cloud_stop_paths.py` now passes `--test` for a paid-test ledger (planner decision); no assertion changed.
## 2026-10-30 — change plan T07: the continuity example on the D-80 trigger home

- `examples/continuity/napoleon_tent.json` `style_line` is now the trigger alone (`xworld style`, `training/lora_rules.json` via `qa/style_prompt.py`); the
  wldnk-era look words are dropped (the planner's call). `examples/napoleon_vs_genghis/PROMPT_PACKAGE.md` starts with a history note (superseded by D-80).
- Test: `test_the_example_style_line_passes_the_d80_trigger_check` (trigger equality + `style_prompt.check` has no FAIL).
## 2026-10-30 night run T08: PRODUCTION_RULES gates 6 and 8 name real tools
- `docs/PRODUCTION_RULES.md` gate 6 now points at `python -m explainer_engine.cloud.runpod dryrun --script <pod.sh>` (`cloud/dryrun.py`, CR-18),
  `config/job_speeds.json` (`cloud/speeds.py`) and `docs/CLOUD_RUNBOOK.md` (was the TMR `cloud/lint_manifest.py`, `cloud/job_speeds.json`, runbook R6);
  gate 8 says the GPU compositor (D-32) is not built and the render is `production/assemble.py` in chunks (RULE-R1, ED-13). No gate name, number or order changed.
- Test: existing `test_production_rules_page_is_linked_and_names_every_gate` stays green.
- OPEN: none. No pod, no API call, nothing deleted.
- Decision log: none moved.
## 2026-10-30 — T09: boundary tests from T01 (tests only)
- T01 (`FREE_CHECKS_2026-10-30.md`): check 9 = NO, so `test_min_balance_refusal_at_the_exact_boundary` is added in
  `tests/unit/test_d9_config.py` (fake balance 20.00: `--max-usd 19.00` leaves exactly 1.00 and passes the balance
  preflight, 19.01 leaves 0.99 and is refused naming `min_balance_left_usd`). Check 8 = YES (`_picks` already counts
  distinct pair numbers, commit dd5009f), so no `generator_gate.py` change and no new generator-gate test.
- No production code changed, nothing paid. Tests: see the PR.
## 2026-10-30 T10: `p12b.json`, every pin of the Qwen-only P12b
- New `explainer_engine/training/pods/p12/p12b.json`: Qwen-Image-2.1 revision, `xworld_v2_000003000` (vault sha256), the Multiple-Angles LoRA
  (revision read from the Hub: 175b29b6eb41307473eebc363fca8fc198216b60), the 12 azimuths, the four hero sheets (HF dataset
  `vano1919/tmr-artifacts`, `p2s/out/p2s/`, paths given by the coordinator), the host pictures, stages Q1-Q4, drop order, prompts, outputs, heartbeat.
  LTX stages (L1, L2, L3, AV) are listed as `deferred_to_p12c`.
- Test: `tests/unit/test_p12b_config.py::test_p12b_json_is_pinned_complete_and_qwen_only`.
- OPEN: none. No pod, no API call, nothing deleted.
- Decision log: none moved.

## 2026-10-30 T06: `runpod create --rules` runs the `paid_assets` gate for episode pods
- `explainer_engine/cloud/runpod.py`: new `--rules <episode_rules.json>` flag; `create` calls `standards.rulebook.gate(rules, "paid_assets", <production_script.json next to it>)` (the call `production/paint.py` makes) and refuses before any API call on a FAIL (BLOCK or undecided REVIEW are FAIL at `paid_assets`), printing the rule ids; `--rules` with `--test` is refused (a paid test has no episode rulebook). `docs/ORCHESTRATION.md` OR-12 "Enforced by" cell names it.
- Test: `tests/unit/test_episode_rules.py::test_create_runs_the_paid_assets_gate_when_rules_are_given_and_refuses_a_block`.
- OPEN: `--rules` is optional until the ledger meta records an episode. No pod, no API call, nothing deleted.
## 2026-10-30 T13: OR-33 proof job and OR-34 audit job files (estimate only)
- New `explainer_engine/llm/jobs/p12_stream_proof.json` (job `result_check`, class `simple-question`, Haiku, low, `max_tokens` 200,
  prompt "Reply with the single word READY.") and `explainer_engine/llm/jobs/or34_full_repo_audit.json` (job `result_check`, class
  `whole-project-plan` on Fable xhigh, `max_tokens` 32000, read-only repo tools, the plan's three-question prompt).
- `claude_api estimate`: proof worst_usd 0.0001; audit worst_usd 3.2169 (cached bound; 9.66 uncached, 11.51 on a miss), both fit the
  job line. `run` was never called; nothing paid.
- Test: `tests/unit/test_claude_api.py::test_the_committed_p12_jobs_are_valid_and_the_proof_is_tiny`.
- OPEN: the `<main sha>` in the audit prompt is filled at the creator's go. No pod, no API call, nothing deleted.
## 2026-10-30 T11: the P12b pod script (Qwen run) and its dryrun record
- New `explainer_engine/training/pods/p12/p12b.sh` (pinned installs from `config/cloud_pins.json`, `timeout` CUDA check, `DRY=1` gate after the last
  install, `# heartbeat:` / `# stall-minutes: 15`, ends by returning) and `p12b.py` (reads `p12b.json`, `EE_DEADLINE`, `EE_OUT`; downloads base, style LoRA
  with sha256 check (exit 3), MVA LoRA outside `EE_OUT`; loads the pipeline once as `xworld_v1_test.load_pipeline`; `set_adapters` per stage; the plan 3.5
  projection before each optional stage; PNG + JSON sidecar per unit; `stages.txt`, `t.jsonl`, `progress.txt`). The wrapper downloads only `p12b.sh`, so
  it fetches `p12b.py` / `p12b.json` from HF `code/p12/` and checks their sha256 pinned in its text.
- `runpod dryrun --script` passes; sha256 of `p12b.sh` is in the PR body. Test: `tests/unit/test_p12b_pod_script.py`.
- OPEN: copy `p12b.py`, `p12b.json` and the two host pictures to HF before create (see PR); no pod, no API call, nothing deleted.
- Decision log: none moved.
## 2026-10-30 T11 fixes from the independent verifier (Fable): P12b LoRA calls, host paths, T06 REVIEW test
- `p12b.py`: the `load_lora_weights` / `set_adapters` calls (no LoRA mixin on `QwenImage21Pipeline`) are replaced by the call shape of
  `xworld_v1_test.py`: `from videox_fun.utils import merge_lora, unmerge_lora`, `pipe = merge_lora(pipe, path, weight, device="cuda", dtype=bf16)`;
  the xworld LoRA is merged once at 1.0, the MVA LoRA is unmerged and merged again per strength and unmerged for Q4.
- `p12b.json`: the hosts are `code/p12/hosts/a_idle.png` and `code/p12/hosts/b_hover.png` in the HF dataset; `p12b.sh` pins the new sha256 of `p12b.py` / `p12b.json`.
- `EE_DEADLINE` checked: `pod_wrapper.sh` exports epoch seconds, `p12b.py` reads `float(os.environ["EE_DEADLINE"])`; no change.
- Test: `tests/unit/test_episode_rules.py::test_create_refuses_an_undecided_review_at_the_paid_assets_gate_and_makes_no_pod` (zero fake pods).
- OPEN: the `gate_up` fix of `xworld_v1_test.py` (img_mlp.gate_up delta split) is not in `p12b.py`; the creator/Opus thread decides whether P12b needs it. No pod, no paid API call, nothing deleted.
## 2026-10-30 P12b: the gate_up correction of xworld_v1_test.py is now in p12b.py
- `p12b.py` gets `GateUp.gate_up` (copied exactly from `xworld_v1_test.Loras.gate_up`: same regex and maths, `mods = dict(pipe.transformer.named_modules())`,
  self-contained). It runs after the style `merge_lora` (sign +1.0), after each MVA `merge_lora` (+strength) and after each MVA `unmerge_lora` (-strength);
  `t.jsonl` records `lora_gate_up` with the layer count. Without it the ai-toolkit fused `img_mlp.gate_up` layer was skipped (10-25 finding).
- `p12b.sh` pins the new sha256 of `p12b.py`; `runpod dryrun --script` passes. Tests: static order test and a numeric test (skipped without torch) in
  `tests/unit/test_p12b_pod_script.py`. Closes the OPEN of the previous entry. No pod, nothing paid, nothing deleted.

## 2026-10-30 (night run) — OR-34 audit findings: banners made truthful
- The Fable OR-34 audit (main 5cfac9eb, $1.36, `result_check`) answered NOT READY: `audio/voice_layer.py` carried a "never run" banner while five live modules import its WAV helpers; `aivideo/__init__.py` described the banned route with no banner. Q2 grep over `training/pods`, `.claude/agents`, `.claude/skills` for `wldnk|2512|2511|Wild Ink|wan22|qi21`: only history sections and the bannered lora-training lessons. Q3: p12a/p12b script pin tests pass on main.
- The `voice_layer` banner now says what is retired (blend, alteration) and what stays live (`read_wav`, `write_wav`, `f0_track`); `aivideo/__init__.py` gets a RETIRED (D-80) banner. Docstrings only, no code change; nothing paid, nothing deleted.

## 2026-10-31 (night run) — P12a: stopped pods A and E listed in keep_stopped_pods
- Pod A (`ixuendp5qoiu1e`) and pod E (`onuaeup37xsmk5`) are stopped, 0 GB, $0.00/day. Not listed, the pod manager refused every new `create` ("clean up first") and the GitHub watchdog run failed on them (it writes `watchdog.json` only on success, so `create` also saw the watchdog as older than 60 min). Config-only change; no money line moved; nothing deleted.

## 2026-10-31 (night run) — P12a: pods C2, D2 and B2 listed in keep_stopped_pods
- Same reason as the entry above: stopped pods (0 GB, $0.00/day) must be listed or `create` and the GitHub watchdog refuse. P12a so far: A passed, E passed (the watchdog stopped it 41 s after DONE), C2 passed (`FAILED_UPLOAD`, `unstored=12`), D2 inconclusive (stopped by hand before its own deadline, re-run once at `--max-usd 0.06`), B2 `BAD_HOST` 9 s after create (one hardware retry left). Config and test count only; nothing deleted.

## 2026-10-31 (night run) — P12a finished: all five pods passed
- A (plain path, in-pod self stop, download 4.26 GB in 338 s = 12.6 MB/s), E (no key: the watchdog stopped it 41 s after DONE), C2 (`FAILED_UPLOAD`, `unstored=12`, stopped after the end sequence), B3 (`FAILED rc=1`, the session guard stopped it within about a minute, no in-pod stop), D3 (`CAPPED rc=143` at its own deadline, `unstored=0`, stopped). New names C2, D2, B2, B3, D3 because RP-10 counts capacity refusals per name. B2 was a `BAD_HOST` 9 s after create (hardware retry B3 worked). D2 was inconclusive (stopped by hand before its own deadline). Billed about $0.16 + B3 and D3.
- Stopped pods B3 and D3 added to `keep_stopped_pods` (test count 56). Nothing deleted.

## 2026-10-31 (night run) — P12b not started: RP-01 refused the pod (no pod, no money)
- All P12b preconditions held (sha256 of `p12b.sh/py/json` equal to the HF `code/p12/` copies, hero sheets, hosts and both LoRAs reachable, ledger `jobs/p12b/run.json` opened, watchdog fresh, balance $10.17). `runpod create` with `--setup-min 67 --work-min 108` (A40/A6000 SECURE, $0.59/h, estimate $1.72) was refused: `RP-01: planned work 108 min is under 3 x the fixed setup 67 min`. No pod was made.
- Fable (API, `fix_desk`): RP-01 and the pod line 2.40 cannot both hold at setup 67 (work >= 201 min needs a 268-min pod = $2.68 at $0.60/h; 2.40 buys at most 173 work minutes). No exemption for `p12b_two_runs` (that would delete the rule); P12e cannot be merged into the same pod (it needs the creator's host pick and A4's strength from P12b). The plan thread has to re-confirm or re-price P12b: lower the setup by a measured change (Qwen units start while the LTX download runs, or a faster download route) or move E6 (16 region plates, no P12b dependency) into P12b. The morning decides; money lines unchanged, nothing was spent, nothing deleted.
- B3 and D3 show $0.00 billed so far (billing lags up to ~90 min); they are settled later with `runpod cost`.

## 2026-10-31 (night run) — no permanent hosts, final: P12e host sheets dropped, P12b to be re-priced
- Creator 06:37 UTC: no permanent hosts (D-89 stands). The `p12e_hosts` line in `config/spend_caps.json` is re-labelled "dropped, money unassigned" (value and the 5.90 total unchanged); the plan (project files `PAID_TESTS_PLAN.md` R2 and the `_ka` twin) records the void parts (Q4 host collage, E1-E5) and Fable's route for RP-01: `hf_transfer`, 8 region plates (E6) into P12b, one measurement pod first. The measurement pod needs the creator's money word (card posted); `p12b.json/py/sh` are NOT changed yet. No pod, nothing paid, nothing deleted.

## 2026-10-31 — Research blueprint vs main (Fable API, job research_vs_main)
- Creator (cmsg_01Hnu5zB86sjUj5GtTgaUkPW7wdRsVrtLqHuGQPn7kTYof): "yes, $25 cap"; the 25 is taken from J2b (10 to 0), J2a (8 to 0), fix_desk (8 to 1) by his card tap cmsg_01Hnu5zB86sjUj5GtTgaUkPWWMoczMmiDtJ6L7CiexQMQ3, so the lines still sum to 95. `config/spend_caps.json` `claude_api.jobs.research_vs_main` = 25.0 (recorded word `protected_config`).
- Ran: the Master Research Blueprint (.docx, 153 topics) analysed by Fable xhigh, compared with main b81200d, overview + one-page Georgian audit. Three steps, each saved to a file as it arrived (OR-33).
- Cost (ledger): stream proof $0.00001, step 1 $3.73, step 2 $6.96, step 3 $1.73; total $12.42 of $25 (client stop $20).
- Result: 104 covered, 26 partial, 15 contradicted, 3 ignored, 5 rejected. Files: project folder `explainer-engine/research_vs_main_2026-10-31/` and HF dataset `vano1919/tmr-artifacts` `research_vs_main_2026-10-31/`.
- Next: the creator decides the listed contradictions; P6/P7/P8 gaps go to the planner.
