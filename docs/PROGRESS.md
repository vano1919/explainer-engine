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
