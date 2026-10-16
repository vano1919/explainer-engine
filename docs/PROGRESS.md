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
