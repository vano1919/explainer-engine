# CLAUDE.md — explainer-engine

A solo creator's 2D hand-drawn explainer channel ("worlds collide": history, science and money meeting other
eras, D-25; analysis episodes of other people's fictional worlds under the RR rules, D-26) and its production
pipeline: topic → research dossier + claim map → short scenario → **creator approval** (OR-15) → script → **creator approval** → schema-validated storyboard →
paint plan + **creator's provider choice** → pictures and ElevenLabs narration for the **first two parts only**, stitched into
a sample the creator watches and approves before the rest is paid (OR-19, D-67; `production/sample.py`) → the rest's pictures +
narration + Scribe word timings → PIL/ffmpeg assembly
(`production/assemble.py`) → Shorts → thumbnail + metadata (`qa/publish_check.py`) →
technical + editorial QA → review bundle → **creator approval** → manual upload. Cloud-first (D-31). Start from `docs/INDEX.md`: every specification and every ID (D-, SE-, V-, P-, R-, Q-) has ONE canonical home —
link to it, never copy it (`python -m explainer_engine.docs_lint` enforces this). `docs/PLAN_2026-10-15.md` is history.

**Rule one (creator, 2026-10-26, OR-22):** never take a system decision on an assumption (base model, LoRA and checkpoint, data, settings, test design, rule wording, spend); every detail his words do not settle is put to the creator first, also in auto mode. **Before every pod (OR-23):** a detailed plan item by item (purpose, model and checkpoint, data, every setting, outputs and HF paths, GPU and price, time and money caps, stop condition, what he sees, what follows), agreed before `runpod create`; never a general summary.
**Higher thread decides (creator, 2026-10-26, OR-24):** before every important decision the working session (Sonnet) asks a separate thread on a higher model (Opus); that thread takes the main planning decisions and its confirmation of an OR-23 pod plan starts the pod. The coordinator passes it complete information (facts, numbers, files, open items) but no reasoning, so the answer is not biased.
**Direct evaluations, full-scale plans (creator, 2026-10-26, OR-25):** an evaluation is direct, with the evidence; a plan starts from the goal, lists every path to it and grounds each in known training methods and the project's goals, not only the next step.
**Opus plans, Sonnet works (creator, 2026-10-26, OR-26):** the working session does the work; the Opus thread writes the plans, and hard technical questions (code and test design of a new method) go to it before the work; the session implements the plan as written.

## Commands

```powershell
.\setup.ps1                                   # once: .venv (Python 3.12/3.13) + packages
.venv\Scripts\python -m pytest -q             # all tests
.venv\Scripts\python -m explainer_engine.docs_lint        # docs: one home per ID, links, fixtures
.venv\Scripts\python -m explainer_engine.design.palette   # palette contrast table + rule check
.venv\Scripts\python -m explainer_engine.cloud.runpod check  # what bills on RunPod now (also run by the session hooks)
```

## Invariants (do not violate; stop and ask if a task seems to require it)

1. Production is cloud-first (D-31): the cloud session + RunPod pods. Money ceilings live only in
   `config/spend_caps.json` and are enforced by code (D-56): pods only via `python -m explainer_engine.cloud.runpod`
   (`check` at start and end, `create --ledger`, guard, `stop`; delete only on the creator's word; a stopped disk bills).
   The creator's PC only reviews and uploads.
2. Budget caps are ceilings, not targets; the numbers live only in `config/spend_caps.json` (invariant 1; vidIQ and ElevenLabs
   credits are counted in the ledger until they have a line there). Estimate and log before every paid call
   (`docs/COST_AND_TIME_MODEL.md` ledger); at 80 % of a cap stop and ask. Leave nothing paid running.
3. (retired 2026-10-19: two long videos have shipped) No new pipeline stage goes into a video before its gate runs on the
   D-43 flow and a focused test proves it (D-59).
4. No public upload, ever, without a recorded creator approval. The only upload code is the unlisted/private staging of
   D-57 (`publish/`), run after the creator's OK; going public is the creator's click in Studio.
5. No unsupported claims, fabricated research, invented metrics, or copied protected IP. Every factual sentence maps
   to a claim with a source; say exactly what was and was not verified.
6. The original character/visual identity stays stable (hero references and expression sheets, D-55; never redraw from
   scratch; a new character or environment style is one collage of variants for the creator's choice).
7. Versioned schema contracts are authoritative; never bypass or weaken validation to make a render pass.
8. No destructive command, broad deletion, credential exposure, or unrelated refactor without approval. Cleanup
   deletes only job directories via `core/jobs.clean_jobs`.
9. Do not change the approved strategy or architecture without new evidence and a minimal-change proposal.
10. Never remove or weaken a test or acceptance criterion to make a phase pass.
11. Every meaningful change: a focused test + an entry in `docs/PROGRESS.md` (and the decision log if a decision moved).
12. A material conflict found during implementation: stop at the boundary, report evidence and options, ask.

**Autonomous runs:** `docs/ORCHESTRATION.md` and the `orchestrator` agent (`.claude/agents/orchestrator.md`), with the
`episode-standards-director` page for the rulebook (OR-11, OR-12): gated phases, hard caps in `core/ledger.py`, nothing lost on a stop, nothing public. Dialogue what-if episodes (D-48): the writers' room, skill `story-engine` + `docs/STORY_ENGINE.md`, one main agent that runs the stages itself plus one spawned critic (OR-20, D-79; stage pages `story-architect`, `scene-writer`, `beat-writer` (visual beats and cues, skill `visual-beats`, D-54), `performance-director`, `edit-planner`, `voice-caster`, `shorts-writer`; critic `script-critic`), `scripting/story_lint.py`, `scripting/stage_guard.py`, `production/accents.py`, `edit/motion_lint.py`, `audio/layers.py`, `audio/casting.py`. Skills `science-grounding`, `time-jump-episode`, `shorts-for-video`, `editing-style` (rules `docs/EDITING.md`), `video-editing-architect` (general technique database and QA list), `elevenlabs-voice` (first-take reads, credit saving).

**How we work (creator, 2026-10-17):** a change request goes in this order: (1) study the process and the real output (open files, measure, find the cause); (2) research when the topic needs it and write the findings into a skill; (3) ask the creator the questions that are truly his to answer; (4) update rules, skills, agents and tests; (5) only then produce. Never produce before steps 1-4. Creator notes become rules with a test (OR-09).
**Reusable before fast (creator, 2026-10-25, OR-21):** between a quick one-off and a reusable tool in the repo, always the reusable one at the same money cost, even when slower (a cheaper one-off goes to the creator); pods start only through `cloud/runpod.py create` with their script and config committed under `explainer_engine/training/pods/`.

**Long renders (RULE-R1, 2026-10-17):** a render longer than ~10 minutes runs as a tracked background task of the session, never a detached process; it is written in chunks (ED-13) and each run draws only its chunk range (`assemble --chunks A:B`) until all chunks exist, then joins once. The session keeps a wake-up timer while it runs. Details: `docs/PRODUCTION_RULES.md` section 3.

**Production rules (binding for every video, creator 2026-10-16):** start from `docs/PRODUCTION_RULES.md` and run
`python -m explainer_engine.production_gate <episode folder>` to see the gates (script, test read, shot plan, style bridge,
sprites, pictures, full read, render, QA). Skills: `narration-script` (how the narrator sounds), `shot-visuals` (what the pictures
show). Entertainment first, facts second; stakes and named heroes in every frame; one drawn world; limits computed from
measured speeds; every paid step estimated and approved first; look at the output before reporting it; reply to the creator in Georgian.
**Strict storytelling (creator, 2026-10-20, D-61):** show, don't tell (no trait statements, ratings or biographies from the
narrator, SC-12) and full immersion (no meta disclaimers or hedges on the story, SC-11); the creator approves the finished
script before anything is paid (OR-17, `scripting/script_approval.py`).
**The channel is a storyteller (creator, 2026-10-20):** the goal is an interesting idea, told well; hooks, animation and
sound effects are only the means that turn the viewer towards it, never the goal. Judge every script by its story first.
**Language (creator, 2026-10-17):** Georgian is only for talking to the creator. Everything the viewer sees or hears (narration, on-screen text, picture prompts, titles, metadata, Shorts) is English for the US audience; never ask again.

**Sourced rules (D-59, creator 2026-10-19):** no production rule is law by itself. Every number a validator enforces comes from
`explainer_engine/standards/sourced_rules.json` (`docs/SOURCED_RULES.md`, BP-xx; binding = two of three source types, article /
book / video; hypothesis = REVIEW only; house = the creator's dated call). Code reads `sourced_rules.T("BP-06", "max_words")`,
documents link the BP id instead of restating a number, `tests/unit/test_sourced_rules.py` keeps the registry, the table and the
code together. A new rule needs its two source types before it changes a threshold.

**Episode rulebook (D-51):** every new episode gets `episode_rules.json` from the `episode-standards-director` agent
(`docs/EPISODE_STANDARDS.md`, ES-xx): rules with dated sources and their kind (law, platform policy, provider terms, invariant,
threshold, heuristic), risks as PASS/ADAPT/REVIEW/BLOCK, creative and anti-monotony rules, per-role instructions
(`python -m explainer_engine.standards brief <rules> --role image`). Gates `final`, `script_lock`, `paid_assets`, `final_qa`;
`production/paint.py` refuses a paid run without a passing `paid_assets` gate. Constrain specific risks, never creativity.

**Upload per piece (creator, 2026-10-19):** each video or Short goes up to YouTube unlisted as soon as it passes its own tests,
one at a time, never waiting for the batch (`docs/PRODUCTION_RULES.md` standing order 9); never public, the creator sets the
thumbnail, sign-in by a fresh link per upload session.

Also binding: crossover episodes of other people's fictional worlds follow docs/RIGHTS_AND_FAIR_USE.md (no third-party
media, our own art only, short analysed quotes, small recap, credited fan theories) and pass `rights/ip_check.py`.
Pictures: the creator picks the provider for every batch (D-50, paint plan -> approve -> run; supersedes D-52's "Gemini
batch tier only"); on Gemini the batch tier and the tiers draft/standard/premium pick the model (`imagegen/routing.py`, D-52); audio: ElevenLabs for narration and sound effects, music from ElevenLabs or a per-track verified free library (D-52), guarded by the `.claude/settings.json` PreToolUse hook.
Filler pictures (type A/C, no person, used once, low-stakes beat, at most 30 %) may come from Canva once its terms are verified (D-53, PV-43).
Main market: US (D-52). Disclosure is decided per video by the checklist (realistic content
only, YouTube Help 14328491); channel audience "not made for kids".

## Layout

```
explainer_engine/core/    store.py (JobStore, atomic writes, stage registry), jobs.py (job naming, cleanup),
                          errors.py (Contract/Config/Retryable/NeedsReview), labels.py (evidence labels)
explainer_engine/audio/   scribe_words.py / local_words.py (word timings of the read), voice_layer.py, level.py, seams.py,
                          pause_pad.py, duck.py, layers.py (AL + BP audio rules), sfx_library.py, cues.py; timings.py and
                          visemes.py are Kokoro-era leftovers (D-39 retired Kokoro)
explainer_engine/cloud/   runpod.py (the only pod manager: check, create, guard, stop, sweep, cost), hooks.py (session money hooks)
config/spend_caps.json    the creator's money ceilings (D-56), read by the ledger and the pod manager
explainer_engine/design/  palette.json (the only place hex colours live), palette.py (contrast + rules)
explainer_engine/docs_lint.py   documentation consistency (D-23)
explainer_engine/rights/  ip_check.py: rights check of an episode's rights manifest (RR rules, D-26); any FAIL blocks
explainer_engine/standards/ rulebook.py (episode_rules.json: check, gate, stamp, brief, render), policy_baseline.json
                          (verified law/policy/terms sources, MARKET_RESEARCH V-13..V-24); CLI python -m explainer_engine.standards
explainer_engine/research/ fan_brief.py (crossover fan brief), hypotheses.py (story premises compared, HY rules)
explainer_engine/qa/      scorecard.py, engagement.py (anti-boredom gate, ENG), targets.py (the one set of loudness numbers)
explainer_engine/imagegen/ gemini.py (client, batch tier), routing.py (tiers draft/standard/premium, D-52),
                          picture_library.py (reusable pictures: tags, add/find/fetch, D-76)
explainer_engine/assets_reuse.py  library first (OR-18, D-76): search + record before any new music/SFX/reusable picture;
                          the hook refuses a paid music/SFX call without the record; audio/register.py saves new takes
.claude/settings.json     PreToolUse hook on the ElevenLabs connector -> standards/hook.py (pictures refused, one take, rulebook gate)
explainer_engine/schemas/ versioned JSON Schemas (rights_manifest, fan_brief, episode_rules, production_script, ...)
.claude/skills/crossover-episode/   procedure for crossover episodes (fan research -> scenario -> script -> rights)
assets/characters/kit/    kit_reference.svg (character parts; poses and rig come in Phase 4)
tests/unit/               fast tests; test_repo_hygiene.py guards media/keys, tmr_engine imports, provenance
docs/                     INDEX.md and the canonical specifications; PROGRESS.md (read the last entry first)
explainer_engine/production/  the D-43 production script: compile, validate (PV-xx), timing, assemble, paint (paint plans:
                          provider per batch, creator approval bound to the plan hash, PP-xx), fill_holds, accents
explainer_engine/imagegen/  gemini.py (sync/batch, cache in $EXPLAINER_IMAGE_CACHE or <out>/cache, ChargeUncertain), plan.py
explainer_engine/scripting/ story_lint, stage_guard, claims.py (claim_map.md -> PV-37), distinct.py (docs/episodes.json -> PV-38)
explainer_engine/qa/      visual_judge (questions), sheet_review.py (Claude answers them, free), publish_check.py (PC-xx)
explainer_engine/publish/ YouTube staging (D-57): plan.py (insert bodies), stage.py (unlisted upload, state, quota),
                          youtube.py (stdlib API client, never public), thumbnail.py (Gemini premium, TN rules), auth.py
explainer_engine/training/ LoRA training control (D-72, docs/LORA_TRAINING.md LT-xx): audit, config check, cost, checkpoint
                          judge; agents lora-coordinator/-dataset-auditor/-run-operator/-checkpoint-judge, skill lora-training
explainer_engine/world/   resolver (UR-22..27 prompt lint), look_v2.json; edit/, finish/, research/, rights/ as named
jobs/                     job output (gitignored): jobs/<slug>/job-NNN_<date>/{state.json, artifacts/...}
```

## Conventions and gotchas

- Code copied from `vano1919/tmr-video-script-engine` carries a provenance header and a row in `docs/PROVENANCE.md`;
  never import `tmr_engine`.
- Write JSON/text through `core/store.write_json_atomic` / `write_text_atomic`: on Windows `os.replace` fails
  ("Access is denied") while another process reads the target; `replace_file` retries.
- Secrets live only in gitignored `tools/` or env vars; never log or commit them.
- No linter/formatter/CI: match the existing style by hand; line length ~120.
- Before an import, an adapter, a path or a Hugging Face URL: grep the symbol or open the file; never cite one you did not open
  (Blueprint Lock 5; `tests/unit/test_agent_governance.py` checks every module, path and skill the agents and skills name).
- Models and effort live only in `config/model_routing.json` (D6/D7, OR-29): agent frontmatter, hooks and tests read it, it changes
  only on the creator's word. A model switch asked for by a tool inside a thread (the creator's own `/model` passes), a `.py` edit at xhigh/max, `config/spend_caps.json`, a force push and
  `branch -D` are refused by hooks (`explainer_engine/governance`, D-84) unless his word is recorded
  (`python -m explainer_engine.governance ok ...`). The critics are read-only. The Blueprint phases, decision cards (`owner:
  creator|claude`) and routing log are in `docs/blueprint/` (`python -m explainer_engine.governance check`).
- Usage limits (creator 2026-10-29, OR-30): the orchestrator and every thread watch the 5-hour and the weekly limit; at 95 % the
  unfinished work is backed up (project files + a WIP commit on the work branch) before it can be lost.
- Paid runs save step by step (creator 2026-10-30, OR-33): every paid run writes its output to a file as it arrives (stream / partial /
  checkpoint); a paid path without that protection proven by a test does not start.
- Commit with `git -c user.name=vano1919 -c user.email=122537395+vano1919@users.noreply.github.com`.
- The Bash tool collapses `\\` inside heredocs: write Python edit scripts with backslashes to a file first.
