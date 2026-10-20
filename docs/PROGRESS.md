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
