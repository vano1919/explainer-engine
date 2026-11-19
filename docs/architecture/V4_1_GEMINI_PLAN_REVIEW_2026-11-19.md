# Gemini (Neon, thinking High) review of FINAL_ACTION_PLAN_STEP0_STEP1.md

Date: 2026-11-19. New Gemini chat: https://gemini.google.com/app/08a413e929ae3edf (model Neon, thinking level High, owner's Mac Chrome).
Prompt: the plan text (sections 1-8 and 10) plus the questions A-G; the full prompt is visible at the top of that chat.
Gemini could NOT open Drive/GitHub/HF content in this chat, so it marked every code fact F1-F9 UNVERIFIED. Its answer below is copied from the chat unchanged (formatting only: headings and bullets).

---

## A. Overall Verdict

**APPROVE WITH CHANGES**

Right strategic direction: Killing procedural mix.py as a master path, stripping non-commercial BBC RemArc audio, and gating LTX jobs and Whisper cuts before paid runs are the right priorities.

No codebase verification possible in this session: I do not have read access to Drive snapshot eb80e443, GitHub vano1919/explainer-engine, or HF links in this chat, so every repo/line/CI claim (F1-F9) is UNVERIFIED here and must be treated as self-reported until independently checked.

Three blockers must be fixed before Step 1 starts: Step 0.4b's CI allowlist check is underspecified and self-bypassable; Step 1.2's "energy check" cannot separate gunshots/loud ambience from speech and runs ahead of G1 ground-truth listening; and Step 1.4's PC-10 only checks audio stems while ignoring video, photos, and native LTX clip audio.

Hidden execution risk in Decision 3.2 / Step 1.5: Declaring episode/run.py (G8+G9) the sole master path before confirming G8 handles full film mastering (VO, music, ducking, LUFS, Truce dips) and before porting build_segments's guards invites a late-stage stall.

Parallelism trap in Section 4: Running G2 schema authoring against the Step 0 base SHA while Claude adds new fields in Steps 1.1-1.4 guarantees immediate schema-to-code drift unless field contracts are frozen first.

## B. Review of the Three Recommendations

### 3.1 Accept P1.2; V4.1 continues PR #195's plan - PARTLY

Why not full AGREE: Accepting P1.2 conditionally on green CI and tree verification makes sense, but both the git verification and the precedence rule have holes.

- **Git provenance ambiguity (eb80e443 vs 0592114):** Step 0.2 asks for a bundle containing two commits (eb80e443 and 0592114) yet only compares eb80e443^{tree} against PR #196's tree 52e6feee432c1dfaaa23346f571c23b2ed521542 (UNVERIFIED). If 0592114 is a child of eb80e443, comparing eb80e443^{tree} skips 0592114; if 0592114 is the parent, PR #196's CI only tested the squashed tip, not commit-by-commit integrity or file deletions outside the 31 copied files.
- **Precedence conflict:** Putting DEC-2026-11-17-01 and PR #195's plan above V4.1 (as amended by MA-01..MA-18) means any place where MA-01..MA-18 corrects PR #195 is technically outranked until an ADR line is written. Precedence should state explicitly that newer accepted amendments (MA-01..MA-18) override earlier plans where they conflict, with an explicit conflict table written in Step 0.3, not deferred ad hoc.
- **Branch split-brain:** Pushing exact commits to argon/p1-2-timing-contract while draft PR #196 exists on another head needs an explicit close/supersede rule so CI and Drive mirrors never diverge.

### 3.2 episode/run.py (G8 + G9) is the only master path; mix.py never makes a master - PARTLY

- **AGREE on banning mix.py from masters (conditional on F2):** I cannot inspect tools/render_tools/mix.py in this chat (UNVERIFIED, no snapshot mounted), so I cannot confirm or contradict lines 547-598 / 720 / 782 / 795. Assuming F2 is accurate, a mixer that synthesizes white-noise beds and sine-chord music violates D-136/OV-56 and has zero business producing a master, regardless of whether its loudness check logs PASS.
- **DISAGREE with declaring G8 (audio/stems.py) sufficient without proving full-mix parity:** F3 only claims G8 plays library takes, refuses placeholders, and writes audio/stems_report.json (UNVERIFIED). It does not prove G8 handles voiceover/narration placement, music cues, dialogue ducking, crossfades, YouTube loudness targeting (-14 LUFS integrated / true-peak ceiling), native LTX clip audio integration, or the hard-coded Truce dip list mentioned in F4 (build_segments L28-31). "Plays real library takes" is necessary, not sufficient, for a shippable master sound path.
- **Unresolved G9 vs build_segments conflict:** F4 states G9 (production/assemble.py) enforces exact frame-count equality (L1503, UNVERIFIED), while build_segments allows +-1 frame and owns the single-trim contract, cache key, single-resize guard, overlay authority, and Truce dip list. Letting a single 60-second happy-path parity test "decide" whether to port guards into G9 is backwards: safety guards (single-resize, cache invalidation, overlay authority) only trigger on failure/re-run/edge conditions, not necessarily on one clean 60-second slice. And if existing clips vary by +-1 frame, G9's strictness will reject them with no defined remediation path in Step 1.5.

### 3.3 Replace the 6 BBC RemArc sounds with Mixkit/CC0 items - PARTLY

- **AGREE on removing BBC RemArc immediately:** BBC RemArc's licence is strictly non-commercial (personal/educational/research). Removing bbc_remarc from audio/sources.py SFX_EXCEPTIONS (with logged owner reversal of the 2026-11-13 card) and keeping BBC files out of monetised masters is mandatory.
- **DISAGREE that replacing these 6 sounds is sufficient for YouTube monetization safety:**
  - *Massive visual blind spot:* The owner's rule covers third-party video/photo/audio that YouTube may block on a monetised channel. Replacing 6 SFX items and adding an audio-only PC-10 does nothing for archival 1914 photos, historical footage, Wikimedia/museum claims (Getty, Alamy, IWM, British Pathe), or AI-generated image/video commercial rights.
  - *Other audio paths unchecked:* What about music tracks, TTS/narration models, and native audio retained from LTX video clips (Step 1.2)? If any of those bypass audio/stems_report.json, they bypass PC-10.
  - *Mixkit & CC0 Content ID caveats:* Mixkit's Free Sound Effects License permits commercial YouTube use, but free stock pools still occasionally suffer third-party Content ID false positives; unlisted test uploads on YouTube Studio (Content ID pre-check) before public release are still necessary.
  - *Pool exhaustion & listening gap:* Removing 2 of the crowd_murmur items (58 shots), 2 fire items (22 shots), and 1 wind item (84 shots) while stems.Sounds.get rotates deterministically via ids[k % len(ids)] (F5, UNVERIFIED) increases repetitive looping across 84 wind shots. Auditing only "one 30-second sample per pool" will miss bad takes sitting at other indices in a 3-4 item pool.

## C. Verification of Facts F1-F9

Because this is a stateless review chat with no mounted Drive snapshot (eb80e443), no GitHub access, and no HF artifact access, none of F1-F9 can be independently confirmed from code here. Each is marked UNVERIFIED below alongside its logical/technical red flags.

| Fact | Status | Technical assessment and what must be checked |
|---|---|---|
| F1 (PR #196 CI: 4476 passed, 24 skipped, 3 deselected, 1 xfailed; run 44490235037) | UNVERIFIED | Skipped tests jumped from 20 (fc35615) to 24 (PR #196). Before trusting "green", inspect those 4 newly skipped tests and the 3 deselected tests to verify nothing important was silently skipped to get CI green. |
| F2 (mix.py since 0e299cd synthesizes noise/sine chords at L547-598/720/782/795; PASS is loudness-only) | UNVERIFIED | Internally plausible and explains why a loudness gate missed synthetic audio. Needs independent check of whether mix.py still holds any non-SFX mixing logic (e.g., VO/music/ducking/LUFS) that G8 lacks. |
| F3 (G8 audio/stems.py L110-141 refuses placeholders, logs sounds_used/credits to audio/stems_report.json, run.py L1444) | UNVERIFIED | Even if true, F3 does not verify that stems_report.json captures every audio source in the final master (e.g., narration, music cues, LTX clip audio). Verify full audio-graph coverage. |
| F4 (G9 production/assemble.py L1487+/1503 exact frame check; build_segments guards + hard-coded Mac paths L36-40 and Truce dip list L28-31) | UNVERIFIED | Exposes an unresolved migration gap: where does the Truce dip list live once build_segments is bypassed or refactored? Also verify why build_segments needed +-1 frame tolerance in the first place (e.g., VFR/CFR rounding from LTX clips). |
| F5 (6 BBC IDs in 4 pools; stems.Sounds.get uses ids[k % len(ids)] L132; safe items exist in same pools) | UNVERIFIED | Verify that the remaining Mixkit/CC0 items in all 4 pools actually have commercial_use: true in the library manifest, have verified licences on file, and match 1914 sonic context (not modern acoustics). |
| F6 (Whisper words on 6 clips hallucinate over silence/ambience and transcribe gunshots as "BANG! BANG!"; ingest_scene has speech_with_words) | UNVERIFIED | Technically very plausible; classic whisper-small.en failure modes. However, the claim that "S07_SH005 'BANG! BANG!' is the two gunshot onsets" directly undermines Step 1.2's proposed energy-only fix (see Section D). |
| F7 (scene.py L206/279-282 computes regeneration_required without refusing; L152-160 NO_PERCEPTION_INPUT silently passes) | UNVERIFIED | Classic fail-open bug. Verify how many of the 4,476 existing tests rely on NO_PERCEPTION_INPUT silently passing before flipping it to fail-closed. |
| F8 (worker_sha() hashes only modal_ltx_jobs.py L250-251; scene_run.py edit keeps ladder valid, read_job invalidates L1-L3) | UNVERIFIED | Plausible, but verify whether modal_ltx_jobs.py imports helpers from scene_run.py or scene.py at runtime; if worker_sha() only hashes one file while importing others, the ladder cache itself has a hidden drift risk. |
| F9 (Two Chrome browsers with Claude extension connected) | UNVERIFIED | Relevance red flag: appears as a "verified fact" and an approval item in Section 8 ("Chrome bridge"), yet plays zero documented role in Steps 0, 1, or 4. |

## D. Critique of Step 0 and Step 1 (slices 1.1-1.5)

### Step 0

- **0.2 (Bundle and exact branch):** Clarify parent-child order of eb80e443 and 0592114, compare the tip tree (not just eb80e443), and specify what happens to draft PR #196 once argon/p1-2-timing-contract is pushed.
- **0.4a (Protected files):** Adding config/picture_route.json and config/retired_era.json to protected_files is right, but you missed docs/architecture/v4_1_allowlists.json (otherwise any PR can expand its own allowlist). Also clarify whether protected_files is enforced in CI or only via a local git hook; local hooks are trivially bypassed on GitHub or with --no-verify.
- **0.4b (PR allowlist CI job in .github/workflows/quality.yml):** High risk of breaking CI. Three gaps:
  - No slice-to-PR binding: How does quality.yml know which slice allowlist applies to a given PR (branch prefix, PR label, commit trailer)? If it uses PR labels, pull_request workflows don't re-run on label edits unless types: [opened, synchronize, reopened, labeled] is set.
  - Non-slice PRs will break: What happens on Step 0 PRs, PR #195, docs fixes, or hotfixes that aren't V4.1 slices? Without an explicit rule (e.g., enforced only for v4.1/* branches or explicit slice:* label, plus a required check that V4.1 branches carry a valid slice ID), you either break normal development or leave a loophole.
  - Shallow clone bug: actions/checkout defaults to fetch-depth: 1, which breaks git diff origin/$BASE...HEAD. Ensure fetch-depth: 0 (or explicit base-ref fetch) is configured.
- **0.4c (Branch protection):** Make sure enabling required quality checks on PR #195's base doesn't deadlock PR #195 itself if PR #195 predates the new 0.4b scope job.
- **0.5 (Copy 6 clips + start pictures to Drive):** Good; include the exact sha256 manifest AND raw audio extraction / metadata (fps, duration, sample rate) so G1 and Step 1.2 reference identical byte-exact inputs.

### Step 1

**1.1 Fail-closed picture check (scene.py, scene_run.py).** Mostly solid, with three missing details:
- Stale-file / TOCTOU hole: Recording picture_sha256 in scene.py (build) is pointless unless scene_run.py (job_spec) re-hashes the image file on disk and refuses if the hash drifted since build.
- Continuation-shot loophole: Recording continuation shots "as such" must still verify that a valid prior shot exists in the scene and passed its own check; otherwise mislabeling a shot as a continuation silently bypasses fail-closed gating.
- CI breakage risk: Turning NO_PERCEPTION_INPUT from a silent pass into a hard refusal will likely break existing tests in other modules that build minimal mock scenes. Under 0.4b, touching those test files outside 1.1's allowlist will fail CI; pre-audit callers of scene.build before locking 1.1's allowlist.

**1.2 One trim rule from clip's own sound (videolane/ingest.py): F6 and fix assessment.**
- Is the Whisper-words claim (F6) sound? Yes, directionally. Rejecting words-only whisper_edit_points is the right call; Whisper hallucinates dialogue over silence/ambience and mis-anchors timestamps.
- Is the proposed "one trim function with energy check" fix sound? **NO, not as written.**
  - Energy cannot reject high-energy non-speech: F6 explicitly says S07_SH005 ("BANG! BANG!") is two gunshot onsets. Gunshots have high acoustic energy. A rule stating "a word counts only where measured energy supports it" will accept "BANG! BANG!" as speech, directly contradicting 1.2's own required CI test ("S07_SH005 is two non-speech events"). You need actual VAD / speech-probability gating (e.g., Silero VAD or spectral/harmonic speech classification), or if ingest_scene's "detector spans" already uses a true VAD rather than an RMS energy gate, the plan must specify that explicitly instead of calling it an "energy check".
  - Steady loud ambience defeats absolute energy thresholds: S04_SH014 ("You" over steady ambience) requires relative SNR / local noise-floor contrast or VAD, not a flat dBFS threshold.
  - Timestamp stretching (S03_SH007): When Whisper stretches "Oh, my God" across 0.00-2.8 s while the only sound event is at 2.4-2.8 s, simply checking overlap will still keep the 0.00 s start time unless the trim function clamps word boundaries to the intersecting acoustic/VAD span rather than using Whisper's raw start timestamp.
  - Premature ground-truth fixtures: Step 1.2 hard-codes expected outcomes for the 6 clips before Gemini G1 listens to them and before the owner audits S06_SH008 and S03_SH007. If listening reveals that S03_SH007 at 2.4-2.8 s is a non-speech sigh or S04_SH014 has faint speech, 1.2's tests are baked around wrong assumptions. G1 + owner quick listen must feed into 1.2, not trail behind it.
  - Overfitting risk: Designing heuristics around 6 clips and testing on pre-extracted JSON energy windows from those same 6 clips risks overfitting; add synthetic edge-case unit tests (quiet whisper over low floor, loud gunshot + word hallucination, overlapping speech + explosion, zero-speech clip).

**1.3 Start-frame checks recorded, routes only proposed (ingest.py, storyboard.py).**
- Order: Correct to run strictly after 1.2 (shared videolane/ingest.py).
- Risk/Gap: Turning missing inspection data into REVIEW instead of PASS is right, but nothing in Step 1 enforces REVIEW before publishing. Until QA severity gating lands in Step 7, REVIEW behaves like a logged warning that cannot block a bad master. Add an explicit manifest counter (unresolved_reviews) surfaced in publish_check.py (even if non-blocking until Step 7, or blocking unless acknowledged by owner sign-off).

**1.4 Third-party media gate (audio/sources.py, qa/publish_check.py, docs/QA_SPECIFICATION.md).**
- Ordering trap: Removing bbc_remarc from SFX_EXCEPTIONS reverses the 2026-11-13 owner decision. That reversal must be recorded in docs/DECISIONS_AND_OPEN_QUESTIONS.md in Step 0.3 before 1.4 merges.
- Scope mismatch: Writing qa/third_party_media.json from audio/stems_report.json alone creates a false sense of security. Visual assets (photos/footage/bridge stills), narration TTS, music outside stems, and native LTX clip audio are completely unverified.
- generated_terms_unverified = REVIEW: If REVIEW doesn't require an explicit owner sign-off record before publishing, non-commercial free-tier AI audio can still reach YouTube.

**1.5 One render path and 60-second parity slice (mix.py, assemble.py, MAC_RUNBOOK.md).**
- Allowlist collision guaranteed: Section 3.2 explicitly warns that episode/run.py has never assembled the 1914 film. Yet 1.5's allowlist only permits mix.py, MAC_RUNBOOK.md, tests, and "assemble.py (only if the parity test shows a missing guard)". The moment the 60-second parity slice exposes a real bug in episode/run.py or audio/stems.py, or needs the Truce dip list migrated from build_segments, 1.5 will violate its own allowlist and halt.
- Brittle parity criterion: Comparing "per-shot frame counts and hashes" against build_segments will fail on irrelevant pixel-level encoder/colorspace/filter differences, and will fail immediately if build_segments (+-1 frame) and G9 (0 frame tolerance) disagree on a single clip. Specify exact comparison rules (frame count exact; video parity via raw decoded frame hash only if identical ffmpeg filtergraphs, otherwise SSIM/PSNR threshold; audio parity via LUFS + peak + library-take log).
- mix.py refusal check: Ensure refusing writes to renders/final resolves symlinks and Path.resolve() (not a fragile substring match) so an accidental relative path doesn't slip through.

## E. Missing or Wrong Items (by severity)

### BLOCKER

1. **Allowlist CI check (0.4b) is bypassable and will break unrelated PRs.**
   Fix: Add docs/architecture/v4_1_allowlists.json and .github/workflows/quality.yml to protected_files (enforced in CI, not only local hooks); define the exact PR-to-slice binding (e.g., branch pattern v4.1/slice-<id>-* or required PR metadata checked with fetch-depth: 0); exempt non-V4.1 PRs cleanly or require explicit opt-in mapping.
2. **PC-10 (qa/third_party_media.json) ignores third-party photos, video, VO, and native LTX clip audio.**
   Fix: Either (a) rename Step 1.4's output to qa/third_party_audio.json and add an explicit Step 1.4b / Step 2 gate for visual asset provenance (image/video manifest + AI generation terms) before any master can pass publish_check.py, AND verify that audio/stems_report.json (or PC-10) covers music, VO/TTS, and retained LTX clip audio, not just SFX pools.
3. **Step 1.2's "energy check" cannot satisfy its own gunshot/ambience test cases and runs ahead of G1 ground truth.**
   Fix: Require a true speech/VAD signal (confirming whether ingest_scene's detector is VAD or energy; if energy-only, add SNR + spectral/VAD gating) plus onset/offset boundary clamping; run Gemini G1 (plus quick owner spot-check on contested clips) before freezing 1.2's test assertions.

### MAJOR

4. **G8 (audio/stems.py) mastering completeness is assumed, not verified.**
   Fix: Before Step 1.5, audit G8 against full broadcast/YouTube requirements (VO track, music cues, dialogue ducking, Truce dips, -14 LUFS / -1 dBTP normalization, native LTX clip audio mixing). If G8 lacks any of these, explicitly scope a follow-up slice instead of pretending G8 is master-ready today.
5. **G9 vs build_segments guard migration and Truce dip list are hand-waved.**
   Fix: Write a 1-page feature matrix comparing assemble.py and build_segments.py (single-trim, cache key, single-resize, overlay authority, Truce dips, +-1 vs 0 frame rule). Explicitly decide before 1.5 how each item moves; don't rely on a happy-path 60 s parity run to discover missing defensive guards.
6. **G2 schema work will drift against Step 1 record changes.**
   Fix: Freeze a tiny 1-page field-name contract (picture_check, mute_tail_from_s, start-frame REVIEW shape, route_proposals.json, third_party_media.json) in Step 0 before either Claude writes Step 1 code or Gemini writes G2 schemas, OR schedule G2 schema finalization after 1.1-1.4 merge.
7. **TOCTOU gap in Step 1.1 (picture_sha256 not re-verified) and toothless REVIEW states (1.3/1.4).**
   Fix: Have job_spec re-hash the on-disk image and fail on mismatch with picture_check.picture_sha256; require publish_check.py to list all open REVIEW items and block final publish unless an explicit owner-signed waiver file exists.
8. **P1.2 commit provenance ambiguity (0592114 vs eb80e443) and PR #195 precedence conflict.**
   Fix: Verify the exact commit graph of argon/p1-2-timing-contract, inspect the 4 newly skipped + 3 deselected CI tests in PR #196, and write an explicit conflict-resolution table for PR #195 vs MA-01..MA-18 in Step 0.3.
9. **Step 1.1 allowlist doesn't account for broken upstream test fixtures when NO_PERCEPTION_INPUT turns fail-closed.**
   Fix: Grep all callers/tests of videolane/scene.py::build first and include every legitimate fixture update file in 1.1's allowlist before opening the PR.

### MINOR

10. **Unexplained Chrome bridge (F9 and Section 8).** Fix: Either document exactly which step needs browser automation on macOS/Windows or strike it from the plan and approvals list.
11. **Missing Section 9.** Fix: Confirm whether a section (e.g., Rollback Matrix or Risk Register) was accidentally deleted between Section 8 and Section 10, or renumber cleanly. *(Note: Section 9 is the message for Gemini; it was left out of the pasted prompt on purpose.)*
12. **No automated quarantine on render/pass1.** Fix: Drop a DO_NOT_MONETIZE_CONTAINS_BBC_REMARC.txt marker (or metadata flag recognized by publish_check.py) inside render/pass1 so a prose warning isn't the only safeguard.
13. **Insufficient audio QA for replacement pools (Decision 3.3).** Fix: Owner should audition every replacement take (not 1 per pool) plus a 60-second concatenated sequence of wind/crowd_murmur shots to catch audible modulo-loop repetition.
14. **G4 free image tool commercial terms and provenance unlogged.** Fix: Verify commercial YouTube rights of the image tool used for G4 before using any outputs in the master, and log tool/model/prompt/licence into the visual asset manifest.

## F. Assessment of the Proposed Work Split (Option A)

Overall: Sensible base model, needs 4 concrete adjustments. Having one coding agent with direct git/CI/cloud-media execution (Claude) avoids slow Drive-zip merge loops and unrun media tests (so Option A clearly beats Option B). However, the four Gemini tasks have flaws as scoped:

- **G1 (Watch/listen to 6 raw clips): Good for triage, unsafe as sole millisecond ground truth.** Change: Multimodal models routinely drift +-0.3-0.8 s on timestamps and can mishear subtle audio. Use Gemini G1 to classify what happens (visible lip movement vs off-screen audio, speech vs gunshot/ambience, approximate spans), then have the owner do a 2-minute human spot-check on the 6 clips (they're ~5-10 seconds each, less than a minute of total audio!) to lock ground truth before Step 1.2 is coded.
- **G2 (Write 6 schemas + v4_1_schemas.json against base SHA): Bad timing.** Change: Do not write schemas in parallel against the Step 0 base while Claude adds new JSON fields in Steps 1.1-1.4. Either have G2 draft the exact JSON schemas for Step 1's new fields first (so Claude implements to G2's contract and validates against it in CI), or defer G2 until Step 1 freezes. Contract-first is cleaner.
- **G3 (Cross-vendor PR review from Drive snapshot): Under-contextualized as described.** Change: A raw diff without surrounding code produces shallow reviews. Require each G3 Drive review packet to bundle: (a) git diff, (b) full text of every touched file + its direct callers, (c) the slice's allowlist entry, and (d) full CI test output (including skipped/xfailed tests).
- **G4 (5 photo fixes + 5 bridge stills in free image tool): Licence and visual-consistency risk.** Change: Confirm commercial monetization terms for the free image tool first, record provenance metadata for every generated/edited asset, and treat all G4 outputs as REVIEW until human historical-accuracy inspection (1914 uniforms, equipment, lighting consistency) passes.

## G. Final Recommended Order of Work (9 steps)

1. **Audit and lock the baseline (Step 0.1-0.3):** Inspect the 4 newly skipped / 3 deselected tests in PR #196; verify the exact commit graph (0592114 vs eb80e443) from the Drive bundle and reconcile PR #196 vs argon/p1-2-timing-contract; record owner approvals (including reversing the 2026-11-13 BBC exception and settling PR #195 vs MA-01..MA-18 conflicts) in docs/DECISIONS_AND_OPEN_QUESTIONS.md; remove or explain the Chrome bridge (F9).
2. **Harden governance locks without breaking CI (Step 0.4):** Protect config/picture_route.json, config/retired_era.json, docs/architecture/v4_1_allowlists.json, and .github/workflows/quality.yml (CI-enforced, not just local hooks); build the 0.4b allowlist checker with fetch-depth: 0 and explicit PR-to-slice binding; prove one real red run; enable branch protection (0.4c).
3. **Ground-truth audio triage + contract freeze (Step 0.5 + G1 + mini-G2):** Copy the 6 raw clips and start pictures to Drive with SHA-256s; run Gemini G1 and a 2-minute owner listen to lock real speech/non-speech timestamps for all 6 clips; freeze exact field schemas for Steps 1.1-1.4 so G2 and Step 1 cannot drift.
4. **Pre-flight audits (parallel, $0):** (a) grep all scene.build test fixtures for NO_PERCEPTION_INPUT fallout; (b) audit G8 (audio/stems.py) for full mastering capabilities (VO, music, ducking, LUFS, Truce dips, LTX clip audio) and write a feature matrix for G9 vs build_segments; (c) verify commercial terms of all remaining Mixkit/CC0 pool items and the G4 image tool.
5. **Step 1.1 + Step 1.4 in parallel (with G3 full-context reviews):** 1.1: fail-closed picture check in scene.py + scene_run.py with on-disk SHA-256 re-verification and continuation-chain validation. 1.4: remove bbc_remarc from SFX_EXCEPTIONS; add PC-10 checking all audio sources (stems, music, VO, retained LTX audio) with explicit scope clarity (or add visual-asset provenance check alongside it); quarantine render/pass1; owner auditions every replacement sound take.
6. **Step 1.2 (unified speech/VAD trim function):** Implement one trim function in videolane/ingest.py using actual VAD/speech classification + SNR contrast + acoustic boundary clamping (not raw energy alone), tested against G1+owner ground truth plus synthetic adversarial cases (loud gunshots, steady loud ambience, quiet speech).
7. **Step 1.3 (start-frame checks and route proposals):** Wire ingest.py and storyboard.py checks with REVIEW on missing data, apply_routes=False, and an unresolved-REVIEW counter surfaced in publish_check.py.
8. **Step 1.5 (one render path and 60-second parity slice):** Lock mix.py to preview_only (resolved-path guard); port required build_segments guards and Truce dip handling into G9 (or wrap build_segments cleanly after stripping Mac hard-coding); run the 60-second G8+G9 parity slice with defined video/audio tolerances and verify the full audio log.
9. **Finalize G2 schemas and visual provenance before paid runs (transition to Step 2+):** Merge complete G2 schemas validated against actual Step 1 outputs, add visual-asset licence gating (covering archival photos + G4 stills) to publish_check.py, and only then proceed to Step 7's read_job worker change and paid L3 smoke (OR-23 / OR-34 / $0.50 cap).
