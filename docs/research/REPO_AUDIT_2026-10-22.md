# Repo audit: explainer-engine @ claude/project-thread-w8oxrk (= origin/systemic/next-video, HEAD 0520c68), 2026-10-22

## 0. Component summary table

| Component | Status | Where |
|---|---|---|
| RunPod pod manager (create/guard/stop/sweep/cost/check) | exists-and-tested (fake API) | `explainer_engine/cloud/runpod.py`, `tests/unit/test_runpod.py` (27) |
| Claude session money hooks (SessionStart / Stop / pre-Bash) | exists-and-tested | `cloud/hooks.py`, `.claude/settings.json` |
| Spend ceilings file + loader | exists-and-tested | `config/spend_caps.json`, `core/spend_caps.py` |
| Run ledger (caps, reserve/refund/settle, approvals, failures, phases) | exists-and-tested | `core/ledger.py` |
| Per-pod job state | exists, one mutable JSON, no history | `runpod.py:191-215` (`tools/runpod/sessions/<pod>.json`, gitignored, sandbox disk) |
| Job state history / event log for cloud jobs | absent (explainer). TMR conductor has `state.json` + `events.jsonl` on the pod | TMR `cloud/conductor.py` |
| Checkpointing / resumable cloud stages | absent in explainer; TMR conductor resume + `run_or_resume.sh` | TMR |
| Durable result upload (HF `vano1919/tmr-artifacts`) | absent in explainer; TMR `cloud/store.py` (push/verify sha256) runs on the pod | TMR `cloud/store.py` |
| Watchdog independent of pod and session | absent (guard = detached local process on the sandbox, dies with it); optional heartbeat ping + ntfy | `runpod.py:443-457` |
| Idle detection | explainer: boot deadline + "conductor DONE but pod on"; TMR: log-stall push only (15 min) | `runpod.py:335-354`; TMR `conductor.py:323-342` |
| Incident log (machine-readable) | absent (prose only: TMR `docs/INCIDENTS_RUNBOOK`, RUNBOOK). `channel/incidents.json` documented-only | |
| Webhooks / inbound events | absent; outbound ntfy only | `runpod.py:364-374` |
| Gemini image client (sync + batch, cache, spend log) | exists-and-tested | `imagegen/gemini.py` |
| Provider abstraction for images | absent (provider table only; Gemini hard-wired) | `imagegen/plan.py:24-32`, `production/paint.py:190-194` |
| Paint plans with hash-bound approval | exists-and-tested | `imagegen/plan.py`, `production/paint.py` |
| Tier routing (draft/standard/premium) | exists-and-tested (Gemini only) | `imagegen/routing.py` |
| Face/expression sheets + keying + composite | exists-and-tested | `production/faces.py` |
| Variant-collage reference approval (OR-16) | exists-and-tested | `scripting/reference_approval.py` |
| World resolver + era codex + look v2 | exists-and-tested | `world/resolver.py`, `eras.json`, `look_v2.json` |
| Asset library with IDs / provenance / licences | documented-only | `docs/ASSET_SYSTEM.md`, P-66 |
| Scene staging / continuity (`production/staging.py`) | absent (PRs #16/#17 not merged) | |
| Zoom continuity across shots of one picture | exists-and-tested | `production/continuity.py` |
| Image-to-video / generative motion | absent | Veo only mentioned (`docs/TOOL_STRATEGY.md:23`); blocked by `standards/hook.py:23-35` |
| Ken Burns + chunked ffmpeg assembler | exists-and-tested | `production/assemble.py` |
| Remotion renderer | documented-only | `docs/RENDERING_ARCHITECTURE.md:5-7` |
| Style-distance QA, world schema, LoRA gates | documented-only | `docs/VISUAL_WORLD_ARCHITECTURE.md:184,228,234` |
| JobStore / job dirs | exists-and-tested, unused by the pipeline (dead) | `core/store.py:65-129`, `core/jobs.py` |
| End-to-end `python -m explainer_engine run` | documented-only (doc admits it) | `docs/PIPELINE_ARCHITECTURE.md:3-7` |
| YouTube unlisted staging upload | exists-and-tested (fake transport) | `publish/youtube.py` |

## 1. Cloud / GPU

### 1.1 Commands (`runpod.py:646-749`)
balance, check (exit 1 on problems), list, sweep [--dry-run] [--delete --yes], create --yes --max-usd --max-hours --ledger [--gpu default|cheap|big] [--boot manifest] [--volume] [--min-ram] [--name] [--on-cap stop|delete] [--no-guard], adopt, status, wait-ready, guard, stop, start --yes, delete --yes, cost. GPU pools and $/h ceilings :49-52; BOOT_MINUTES=10 :57. Image `ghcr.io/vano1919/tmr-pod:latest` (:47); boot_cmd curls TMR `cloud/bootstrap.sh` (:618-625).

### 1.2 Safety mechanisms that exist
- HTTP: retries 429/5xx/OSError with min(60, 2**attempt) backoff, 4 times; 404 → NotFound; other 4xx fatal (:104-123).
- Create: POST once, re-POST only after 429; unclear answer → look up by unique name 6×10 s; >1 pod with that name → raise; card dearer than max_price deleted (:276-308). Names carry `-until-<epoch>` (:158-172).
- Stop/delete idempotent and verified (GET shows EXITED/GONE); REST then GraphQL podStop (:235-269).
- Money clock `spent_estimate` compute + running disk, errs high (:182-187); `cost` settles with billed amount (:488-501).
- Guard loop 30 s (:395-440); stops on money cap, time cap, name lifetime, boot deadline, conductor DONE/STOPPED/CAPPED + 120 s (:335-354). Blind guard assumes RUNNING, pushes after 4 and 20 failed polls.
- `end_pod` retries up to 999× (30 s). Latent NameError if all fail (:379-387).
- `guard_detached` start_new_session + PID lock `tools/runpod/sessions/<pod>.guard` (:443-457). `PodSession` context manager stops on exception/atexit/SIGTERM (:504-534).
- `check()` (:548-577) flags expired RUNNING pod, pod with session but no live guard, EXITED pods not in keep_stopped_pods. `preflight_create` (:580-599) enforces per_pod_usd, max_hours_per_pod, max_price_per_hour, per_24h_usd, min_balance_left_usd, and any check() problem.
- Ledger coupling: create reserves max_usd as runpod_usd before POST, refunds on failure (:690-701).
- Hooks (`cloud/hooks.py`): SessionStart prints check(); Stop exit 2 while problems; pre-Bash refuses `rp.py create|start|adopt`, raw POST /pods, GraphQL deploy. No key/no network → never block.

### 1.3 Ceilings (`config/spend_caps.json`)
per_episode runpod_usd 3.0, gemini_usd 10.0; runpod per_pod_usd 1.0, per_24h_usd 1.5, max_hours_per_pod 2.0, max_price_per_hour 0.95, min_balance_left_usd 0.25. Ledger stops at 80 % (`ledger.py:21,97-108`); LedgerConflict (:29-32); 3 failures stop an item (:146-155).

### 1.4 What does NOT exist (explainer side)
- Job state history: session JSON overwritten in place (:195-201). Ledger keeps phases (last status) + failures list.
- Checkpointing/upload of pod results: no HF/S3 client; only HF_TOKEN passed to the pod (:610-615). Durable storage = TMR `cloud/store.py` run by in-pod stages.
- Watchdog independent of the session: guard dies with sandbox; after a container recycle `check()` takes the `sess is None` path and reports a live unexpired pod as info, not a problem (:557-564). Pod then bounded only by name lifetime (2 h), next session's Stop hook, in-pod conductor caps, or HEARTBEAT_URL. TMR runbook mentions an "hourly sweep Routine" — no such scheduler exists in code.
- GPU-idle detection: none. Incident log: none machine-readable. Webhooks: none inbound. Whole-job retry: none by design.

### 1.5 Secrets
RUNPOD_API_KEY env else `tools/runpod/api_key.txt` (:75-81); pod env secrets via `secret(name, env)` env-then-file (:603-615): ntfy_topic, heartbeat_url, hf_token, github_token, id_ed25519.pub; STATUS_TOKEN per pod. GEMINI_API_KEY env (`gemini.py:105`). YouTube via YOUTUBE_*_B64. ElevenLabs only via MCP, gated by `standards/hook.py`.

### 1.6 Recorded RunPod failures and causes
- COST_AND_TIME_MODEL.md:11 — 35-picture v2 run $0.28, pictures LOST: stage hit its 15-min limit, fatal stop skipped the push. Balance drop larger than guard figures (account shared with TMR), never reconciled (also PROGRESS 182-184, 330, 398).
- PROGRESS 175-185 — first pod (RTX 4090 $0.89/h) 13 pictures 25-30 s each, ~$0.20; foreign TMR pod running simultaneously.
- PROGRESS 231-247 — approved batch never started: session permission check refused pod action twice.
- PROGRESS 249-272 — lost run cause: 35×26 s = 15.2 min vs 15-min limit copied from the 13-picture job; pod deleted itself. Fixes went to TMR lint (picture_budget, fatal_before_push — NOT in local TMR checkout; on remote branch claude/master-directive-prompt-5rmv2y @f0abe62), R-29.
- PROGRESS 371-372 — 48 GB card "no instances available" 5×; fell back to Gemini.
- PROGRESS 671-682 — stopped TMR preflight pod (60 GB volume) billed $0.40/day ~3 days: rules said sweep, nothing ran them; TMR sweep ignored stopped pods → D-56, runpod.py.
- PRODUCTION_RULES.md:100 — Week 1 pod stopped on a guessed model size (58.0 vs 57.7 GB on 60 GB volume).
- TMR RUNBOOK_pods.md rows 1-19: bad cheap card CUDA launch failure (needs early GPU smoke test); stage before setup; artifacts lost on stage overflow; pkill -f killing its own shell; 40-min stage limit killing a run; pod 5 never booted, deleted after 15 min ($0.22) → boot deadline 10 min; monitor buffered behind grep; conductor money clock 3× overstated. :66-82 CPU audio slow stage while GPU idles. :120-132 ONNX 48 threads on few cores.
- TMR INCIDENTS_RUNPOD.md: pod stayed on after DONE (in-pod REST stop 400; cap checked only between stages) → outside guard; stopped pod could not restart ("not enough free GPUs"), volume lost; 2 MB/s upload left pod idle 30 min; container disk wiped on stop/start; 15-30 min compiles → baked image; background guard killed by Bash 30-min limit (~$0.45) → detached guard; PID 1 exit restart loop → tail -f /dev/null; CUDA unspecified launch failure; artifacts lost (nothing pushed before stage 9); measured: 40 GB models ~100 s, torch venv ~5 min, Z-Image ~14 s/picture.

## 2. Image generation
- No provider interface. `plan.py:24-32` PROVIDERS gemini (paints_here) / pod / local; only gemini executes; pod/local print a hand-off note (`paint.py:190-193`). `paint.py:194,300` construct GeminiClient directly; `routing.py` tiers are Gemini-only. Schema engine enum existing|gemini|pod_ref|pod_text|canva; `pod_text` has no producer.
- GeminiClient: price tables :24-36 (checked 2026-10-16/17), MAX_REFERENCES 14, REFERENCE_USD 0.0011. Sync: cache → estimate → 80 % cap → ledger reserve → POST → cache+out → spend log. 429/5xx retried 3×; timeout → ChargeUncertain, reservation kept. Batch: reserve half, `submitting_<key>.json` before POST (never resent). `judge()` paid vision (used only by an example).
- Cache key: sha256([prompt, model, size, aspect]) + sha256 of each ref's bytes, 24 hex (:78-82). Sync refs thumbnailed to PNG, batch refs to JPEG q90 → same request hashes differently per mode. No seed/model-version field. Ledger item_hash = sha256(id, prompt, sorted ref names); plan_hash = provider, model, size, batch, item hashes.
- Reference mechanisms: `look.style_refs` on every picture; `picture.refs` (pod_ref); `cast.<id>.reference` + `look.environment` (OR-16 collage pick, PV-47); face sheets (`faces.py`: 8-12 expressions on chroma green, key/despill, BP-34 checks, dialogue composite, framing normalisation). Reuse lookup by file name only (`beats.find_file`, `library[ref].file`). Provenance: hand-kept `generation_ledger*.jsonl` under `assets/characters/*/` written by example scripts.
- World: `world/resolver.py` resolve(spec) → palette/costume/absent/light/grade; check_text UR-22..27; `eras.json` (717 lines), `look_v2.json`. No persisted world file or schema; resolved on the fly (`compile.py:29-30`).
- Asset library documented-only: ASSET_SYSTEM.md asset record, `assets/LICENSES.json`, `asset_manifest.json`, tag search — none exist. What exists: per-script `library` dict (`script.py:181-198`) and run.json items (file, plan, hash, usd). VISUAL_WORLD_ARCHITECTURE names `qa/style_distance.py`, `schemas/world.schema.json`, `shot_rules.route`, world/LoRA gates, TMR `train_lora` — none exist.

## 3. Video / motion
No image-to-video anywhere. `assemble.py` (630 lines, numpy/PIL/ffmpeg): audio build (beds, sfx, music, ducking, loudnorm), per-shot sub-pixel `motion_box` Ken Burns (:269-280), zoom chain via `continuity.py`, easing, grade/bubbles/accents/beats/face composite/graphics, rawvideo piped to libx264 in 60 s chunks, resumable with plan.json stamp + PID lock, concat mux (:371-438, 584-623). `shorts.py` 9:16 crops; `finish/speed.py` retime; `edit/motion_lint.py` MO rules.

## 4. Production unit and schemas
Schemas: `production_script.schema.json` (/1,/2,/3; 2203 lines), episode_rules v1, fan_brief v1, story_hypotheses v1, rights_manifest v1, publish/1. Validated in code only: paint_plan/1, visual_review/1, editorial_review/1|2.
Model: segments {id, beat, lines[], shots[], audio, period, scene, drama, job, feel, rules}; scene {place, present[], pov, want, obstacle_want, value, charges, exit}; line {text, tags, tone, emotion, emphasis, pause_after, claims, speaker, to, intent, kind, visual_beats}; shot {at, type A/B/C, picture, motion, transition, insert, reveal, bubbles, reuse, accents, purpose, cut}; picture {id, file, engine, subject, refs, edit, heroes, shows, props, speakers, people, costume, prompt, stand_in, tier}. Cast hero {names, card, props, voice, expressions, face_sheet, speech, reference}.
Approvals: paint plans `run.json.approvals[plan_id]={hash,by,ref,provider,usd,at}` (`ledger.py:74-86`); OR-15 scenario sha256 (`scripting/scenario.py`, PV-45); OR-16 picks; rulebook stamps; editorial review bound to script sha256 (OR-10); PC-08 publish approval; thumbnail_log; hook overrides `jobs/gate_overrides.jsonl`.

## 5. QA
Deterministic: scorecard, engagement, publish_check, targets, short_format, claims, narration/story/scene lint, stage_guard, validate, shot_rules, motion_lint, resolver.check_text, faces.lint, ip_check. Deterministic check of LLM/human judgement: editorial_gate. LLM-based: visual_judge (paid Gemini judge, example-only) and sheet_review (Claude in-session, default). No automatic repaint loop.

## 6. Status / CLI / state
~30 module CLIs; no `python -m explainer_engine run`. Persistent state used: `jobs/<run>/run.json`, `<pictures>/plans/*.json`, `_gemini/{spend_log.jsonl,cache,batches}`, `tools/runpod/sessions/*`, `chunks/plan.json`, `render_progress.json`, `publish/youtube_state.json`. `core/store.JobStore`, `core/jobs`, `core/errors` test-only (dead); `core/labels` unused.

## 7. Tests
pytest, 58 unit files, ~603 tests. RunPod faked by FakeRunPod transport with scripted faults; Gemini by injected post callables / urlopen monkeypatch; YouTube by transport callable. Cloud failure cases well covered (retries, lost POST, idempotent stop, blind guard, boot timeout, caps, hooks). Not covered: end_pod exhausting retries (NameError), guard across a real process restart. Only `audio/narrate.py`, `publish/auth.py` untested.

## 8. Doc/code mismatches, duplication, dead code
- Absent but documented: ASSET_SYSTEM asset record/LICENSES.json/asset_manifest; STORYBOARD_SCHEMA storyboard.schema.json, P-66; VISUAL_WORLD_ARCHITECTURE style_distance/world schema/shot_rules.route/LoRA gates/repaint loop; ORCHESTRATION OR-10 `paint --estimate` flag; RISK_REGISTER R-23 (upload code exists), R-14, R-26 (Kokoro retired); RIGHTS channel/incidents.json; COST time_log.json; PIPELINE/IMPLEMENTATION episode.yaml, Remotion, render_bridge; CLAUDE_EXECUTION_GUIDE recovery via JobStore; pyyaml/kokoro-onnx in requirements unused; TMR files cited but absent locally (gen_pictures.py, gen_ref_pictures.py, stages_pictures.json, job_speeds.json, picture_budget/fatal_before_push lint).
- TOOL_STRATEGY says all pictures Gemini (D-52) yet pod plumbing alive (compile.POD_SUFFIX, pod_job.json, PROVIDERS["pod"], runpod.py; D-56 after D-52) — unresolved tension.
- Duplication: legacy shots.json flow vs D-43 production_script; example scripts duplicate engine code (17 files); TMR rp.py vs explainer runpod.py; hero identity in cast.reference and face_sheet.ref.
- Latent bugs for the Guardian: end_pod NameError; check() blind to a live pod after sandbox restart; state in gitignored tools/ on an ephemeral machine; `wait-ready` CLI never passes a probe (:723-724); unreconciled balance drops ×3 (shared account).
