# The production script (D-43)

One JSON file per video is the script, the voice direction, the picture plan with its prompts, the sound plan and the edit.
Schema: [`explainer_engine/schemas/production_script.schema.json`](../explainer_engine/schemas/production_script.schema.json).
Day 1: `examples/stone_age/day1_v7/production_script.json`. Code: `explainer_engine/production/`.

## Why (root causes found in the v5/v6 review, 2026-10-16)

| Defect the creator saw | Root cause in the old flow | Fixed by |
|---|---|---|
| Pictures in the wrong order, fire shown before the fire beat | the shot list was a separate file planned for an earlier read; the story state was lifted per beat; ordering was never checked against the text | shots live inside the segment they illustrate and start on written phrases (PV-04); story events are checked at the word (PV-24, UR-29) |
| A picture that does not show its line (wrong hero, wrong prop) | prompts were written in a separate task, after the script | the picture's subject, heroes and props are written with the line (PV-07, PV-08, UR-30) |
| Duplicate and stale prompts | prompts were composed by a build script and pasted into several files | prompts are compiled from the subject by `prompt_v2.compose` and checked fresh (PV-11, PV-06) |
| Cuts and sounds off the words | times were guessed from beats and shifted when the read changed | no time is ever written by hand: `timing.py` derives every start, end and frame from the read |
| Missing assets found at render | nothing checked that a file, sound or reference existed | PV-05 before any paid call, PV-25 at the render |
| Too many picture changes | no rhythm rule on the whole video | PV-24 (UR-31) on an estimated read while writing |

## Structure

* `episode`, `voice` (provider, model, style words, pace range, tags; **never a real person's name to imitate** (PV-10); candidates for the test read),
  `world` (D-41 world spec), `look`, `cast` (hero names, hero card, props), `story` (events with their phrase, forbidden props),
  `library` (pictures that already exist), `music`, `sound_dirs`, `picture_dirs`.
* `drama` (D-48): premise, dramatic question, promise, needs, arcs, loops (L01..), set-ups (P01..), ending kind; `cast.<id>.voice.traits` (gender, age, temperament, energy, origin, ethnicity, role, real_person, documented) for casting (VC-01).
* `schema`: `production_script/2` (2026-10-19, D-54) adds `lines[].visual_beats` (kind, `at` phrase, `offset`, `why`, the kind's fields, `cue`) and `cast.<id>.expressions` (expression -> cut-out); `/1` scripts stay valid without them (PV-44). `cast.<id>.face_sheet` (`id`, `ref`, `set`) is the hero's expression sheet (VB-09, D-55).
* `schema`: `production_script/3` (2026-10-19, D-58, the scene rewrite) adds the scene contract: a segment with dialogue carries `scene` (`place`, `present`, `pov`, `want`, `obstacle_want`, `value`, `open_charge`, `close_charge`, `exit`, and optional `time`, `why_now`, `turn`, `surface_topic`, `real_subject`, `mode`); every line (segments and Shorts) may say `to` (who it is said to) and `intent` (reveal, press, deflect, concede, question, banter, decide, aside); a beat's `cue` gains `event` (reveal, impact, transition, build, diegetic, take, place) — on `/3` a cue without an event FAILs and silence is the default (VB-08 inverted). SC-01..SC-10 ([STORY_ENGINE](STORY_ENGINE.md)) bind only `/3`; `/1` and `/2` keep their exact old behaviour.
* `segments[]` (S01..): `drama` (function, turn, stakes, shift, need, opens, closes, claim_share), `lines[]` (text, tags, tone, emotion, one emphasised word, `pause_after`, claims, optional `speaker` = a cast id read in that hero's own `cast.<id>.voice`, D-45), `shots[]` (phrase `at`, type A/B/C,
  `accents` (punch, shake, whip_in, flash_in, pop_text, slam_text, wobble on a phrase), picture id or inline picture with `subject`/`engine`/`refs`/`edit`/`heroes`/`shows`/`props`/`speakers`, motion, bubbles), `audio` (`beds`, `sfx` on phrases).
* Engines: `existing` (a file), `gemini` (D-41 prompt, channel style refs), `pod_ref` (a reference edit, painted by the provider the creator picks for the batch, D-50), `pod_text` (no longer made, D-52), `canva` (filler made by hand, D-53).
* Rulebook-era fields (D-51, D-52): `episode.rulebook`; segment `job`, `feel`, `rules`; shot `purpose`, `cut.why`; picture `tier`, `tier_reason`; bed and sound `purpose`, `yields_to`. Times are still never written by hand: anchors are phrases, durations come from the read.

## Flow (one command line: `python -m explainer_engine.production ...`)

1. **Write a segment** (lines, shots with picture subjects, sounds together) -> `validate` (free; also runs the whole board on an
   estimated read, so a rhythm or story-state problem shows while writing).
2. `compile --write --out DIR`: fills every painted picture's prompt, writes `narration.txt`, `narration_tts.txt`, `pictures_gemini.json`, `pod_job.json`.
3. Paid steps use those files (read, pictures); each needs its price and the creator's yes first. Pictures go in batches:
   `paint plan` (free: the batch priced at every provider, written with a hash) -> the creator chooses the provider ->
   `paint approve` (records the yes against that hash in the run ledger) -> `paint run` (refuses without it). See PP rules.
4. `words`: local Whisper (free) or a Scribe JSON -> `scribe_words.align` on the script's own tokens -> `pause_pad` (punctuated gaps and every `pause_after`).
5. `time`: `timed.json` = frames at the episode fps (shots tile the video exactly), bubbles, beds, sounds, music, events, picture list, findings.
6. `assemble` / `run` (`--final` refuses missing pictures): graded pictures with motion and bubbles, narration, ambience, sounds, music ducked under voice and world sounds, -14 LUFS.

## Rules (PV-xx; FAIL blocks the next step)

| Id | Rule |
|---|---|
| PV-01 | the file matches the schema (unknown fields refused) |
| PV-02 | segment ids S01.. in order |
| PV-03 | every shot's picture is defined once (inline or in the library) before it is used |
| PV-04 | every phrase (shot, bubble, sound, bed) exists in its own segment, in order; a segment's first picture starts on the segment's first word |
| PV-05 | assets: a file or an engine for every picture, references exist, sounds exist, heroes and speakers are in the cast |
| PV-06 | no two pictures with the same prompt (REVIEW: nearly the same subject) |
| PV-07 | forbidden props never shown; a prop is held by its owner |
| PV-08 | a painted picture's subject shares content with its segment (REVIEW) |
| PV-10 | voice style describes a sound, never a person; a voice must be chosen before the full read (REVIEW) |
| PV-11 | prompts are compiled from the subject (fresh) and **every painted prompt** passes the D-41 prompt lint, reference edits (`pod_ref`) too; on a reference edit a missing look thread (UR-22) or light key (UR-26) is one REVIEW per picture (the reference picture carries them), child cues, absent objects and "not yet" stay FAIL (audit 2026-10-19) |
| PV-12 | narration lint (N-01..N-15, `scripting/narration_lint.py`) on the text the voice gets; N-14 (press-release lines, [BP-15](SOURCED_RULES.md)) runs on the narrator's lines only, and on a `production_script/3` SC-07 (PV-48) carries it; N-15 flags a narration line's `pause_after` over [BP-10](SOURCED_RULES.md)'s hold (a dialogue scene's scripted silence is a scene device, not a narration hold) |
| PV-14 | if any bed is used, the first segment names one |
| PV-20 | the read matches the script text at least 97 % |
| PV-21 | shot numbers 1..N, frame 0 start, no gap or overlap, last shot ends on the final frame |
| PV-23 | bubbles inside their shot, sounds inside the video, beds cover the video |
| PV-24 | the board rules on the timed script: STATE-1/2 story state at the word, HERO-1/2 hero of the line, RHYTHM-1..3 ([BP-40](SOURCED_RULES.md): pictures a minute and the still limits by section, where a change is a cut, an accent, a bubble or a visual beat; no shot under [BP-84](SOURCED_RULES.md)'s floor), BUBBLE-1..3 (BP-84, BP-27), CUT-1 |
| PV-25 | picture file present (REVIEW in a draft, FAIL with `--final`) |
| PV-26 | likeness by reference: a picture painted by editing (`pod_ref`) that names a hero needs a reference picture whose library `heroes` lists that hero (the model copies the face from the reference) |
| PV-27 | time-jump `periods`: every segment names a known period, a period's segments are consecutive, tone shares sum to 1; REVIEW when a period does not end on the question that opens the next (SR-03) |
| PV-28 | `shorts`: the hook is one question (one statement for the `anti_intuition` and `pov_you` styles, SS-05) and the first line, inside [BP-11](SOURCED_RULES.md)'s word cap (FAIL) and complete by its hook time on the Short's estimated read (REVIEW here; the real read decides in `production/shorts.py` with BP-11's severity); the word budget of [BP-12](SOURCED_RULES.md)'s length bands (REVIEW); the open premise and the ending of [BP-44](SOURCED_RULES.md) and the readability of [BP-46](SOURCED_RULES.md); pictures are the video's own (SH-01..SH-03); the last line points to the video (REVIEW, SH-01); across the set no two hooks are the same (FAIL) and no two Shorts share a body line or half their pictures (REVIEW, SH-05) |
| PV-29 | one music at a time (ED-03): two tracks overlap at most for a crossfade; the tick stays at or under its level (both [BP-86](SOURCED_RULES.md)) |
| PV-30 | every period opens on a card with a title (ED-09, REVIEW) |
| PV-31 | data visuals (ED-10): each passes `graphics.check_visual` and sits in an existing segment; a period without one is a REVIEW |
| PV-32 | voiced dialogue (D-45): a line's `speaker` is in the cast and has `cast.<id>.voice` (FAIL); that voice is described, never imitated (PV-10); no voice id yet, or two speakers on one voice id (REVIEW); imitation words, the person's name in the voice text, or a real person without documented traits are PV-10 FAILs (`audio/casting.problems`, VC-02); two heroes who would cast alike are REVIEW (VC-04) |
| PV-33 | the story layer (D-48, ST rules in [STORY_ENGINE](STORY_ENGINE.md), `scripting/story_lint.py`): unknown or premature loops, a pay-off before its plant, a fact segment without claims, an arc outside the cast FAIL; craft findings REVIEW, including stacked questions outside a declared loop (ST-11, D-49) |
| PV-34 | the Shorts set's styles (SS-01..SS-08): enough different styles, no style twice in a row, a loop ending runs into the first line, a pointer ending points to the video, two length bands, the first cut inside the hook, and the Short's pace by [BP-45](SOURCED_RULES.md) (shots, accents, bubbles and visual beats all count as events; the longest still is measured on the timed Short) |
| PV-35 | motion and visual variety (MO-01..MO-06, `edit/motion_lint.py`) on the estimated read and on the real read (REVIEW) |
| PV-36 | sound layers (AL-01..AL-04, `audio/layers.py`) on the estimated read and on the real read (REVIEW) |
| PV-37 | claims resolve (invariant 5, `scripting/claims.py`): every claim id on a line or a Short is a row of the episode's `claim_map.md` (FAIL; ids with no map FAIL); an E or M claim names a link, a line with a number has a claim id, a map nobody cites is a REVIEW. Whether the source says what the line says is the critic's claim pass |
| PV-38 | the episode is its own (`scripting/distinct.py`, REVIEW): `episode.distinct` names the premise, question, outcome and what is new (mechanism), compared with every approved episode in `docs/episodes.json`; a premise and outcome much like an earlier one is the inauthentic-content case "characters put in the same situation over and over again with the same outcome" (YouTube Help 1311392) |
| PV-39 | (rulebook-era scripts, `episode.rulebook` set) every segment has a beat `job`; the first is a hook or question, the last a payoff (REVIEW) |
| PV-40 | (rulebook-era) the creator picks the provider per batch (D-50 supersedes D-52's "Gemini only"): a `pod_text` picture without a paint plan that names it is a REVIEW (`paint plan --provider pod` first); `premium` needs `tier_reason`; more than 10 % premium REVIEW |
| PV-41 | (rulebook-era) every bed and sound event has a `purpose` (REVIEW) |
| PV-42 | (rulebook-era) every shot has a `purpose` (REVIEW); a spoken number has a claim id (FAIL, invariant 5) |
| PV-43 | (always) a picture with engine `canva` must be filler by `imagegen/importance.py` (type A or C, no heroes or people, used once, beat job explanation / emotional_pause / humor / transition; never hook, question, evidence, complication, reveal or payoff, never premium); at most 30 % of an episode's pictures; FAIL while `channel.canva_terms_verified` is false; REVIEW above the free plan's about 20 AI uses. The 4-second shot limit is checked after timing, since a script has no shot lengths yet (D-53) |
| PV-44 | visual beats and their cues (VB-00..VB-11 in [STORY_ENGINE](STORY_ENGINE.md), `production/beats.py`): in a `production_script/2` every line carries `visual_beats` (the /2 metronome of [BP-36](SOURCED_RULES.md) for narration and [BP-37](SOURCED_RULES.md) for dialogue reactions, each beat with a reason on its own line's words, few words ([BP-38](SOURCED_RULES.md)), numbers with a claim, a face the render can change, a short cue or `none` with a reason that never doubles an effect or stacks past BP-56's layer cap); FAIL rules block a /2 script, a legacy /1 gets one VB-00 REVIEW; on a `/3` the cue grammar inverts (D-58): silence is the default, a cue requires its `event`, the same sound never repeats back to back (VB-10) and density is capped (VB-11, [BP-81](SOURCED_RULES.md); VB-10 is [BP-80](SOURCED_RULES.md)), while the pacing gates relax to dead-air checks (VB-01 [BP-36](SOURCED_RULES.md), nested inside [BP-40](SOURCED_RULES.md); VB-02 reactions [BP-37](SOURCED_RULES.md) with [BP-33](SOURCED_RULES.md)'s flicker floor); checked on the estimated read and on the real read; every Short is checked the same way on its own estimated read except VB-01's cadence, which BP-45 replaces on a Short (SS-09, `shorts[].lines[].visual_beats`, reported as "SH03 line 2") |
| PV-45 | the approved short scenario came first (`scripting/scenario.py`, OR-15): `episode.scenario` names the scenario file next to the script, `approved_by`, `approved_at` (YYYY-MM-DD) and its `sha256`; missing or a scenario changed after the approval is a FAIL on `production_script/2`, a REVIEW on `/1` |
| PV-46 | each speaking hero's manner of speech (`scripting/speech.py`, DW-11): `cast.<id>.speech` with `basis` (public with `sources`, or personality), `style`, at least 3 signature `words`; missing is a FAIL on `/2` and a REVIEW on `/1`; a hero saying a word of their own `avoid` list is a REVIEW; on `/3` a hero none of whose signature words appears in their lines is a REVIEW (the manner must be used, not just declared) |
| PV-47 | the creator picked a variant collage tile first (`scripting/reference_approval.py`, OR-16): every hero drawn in a painted picture (`gemini`/`pod_ref`) or with a face sheet has `cast.<id>.reference`, and a script with painted pictures has `look.environment` (collage, tile, picture in the library, approved_by, approved_at; the collage exists next to the script); missing is a FAIL on `/2` (paint refuses), a REVIEW on `/1` |
| PV-48 | scenes and dialogue (SC-01..SC-10 in [STORY_ENGINE](STORY_ENGINE.md), `scripting/scene_lint.py`): binds only a `production_script/3` — the scene header and its turn of value, opposing wants, every line addressed to someone present (a hero never answers the narrator), a real exchange, enter late / leave early, no press-release narration, one honesty beat, turn-taking lengths, subtext never spoken; an earlier schema gets no SC findings |
| PV-52 | the heard pace of the estimated read (words / estimated duration, pauses included: [BP-01](SOURCED_RULES.md)'s one definition) lies inside BP-01's band; `voice.pace_wpm` is the voice's speaking rate the estimate times the words at before it adds punctuation and held pauses, so a `pace_wpm` inside the band can still be heard slower. Outside it is a REVIEW that asks to change `pace_wpm` or the pauses, or why this voice is slower or faster. The Short budgets and ST-13 use the same heard pace (BP-12, BP-76) |

## Paint plans (PP-xx; audit 2026-10-19; `imagegen/plan.py`, `production/paint.py`)

The image provider is chosen for every batch, by the creator, and nothing is painted without that answer. Claude does not
generate images (Anthropic: "an image understanding model only"); it prepares the plan, asks, and runs the chosen provider.

| Id | Rule |
|---|---|
| PP-01 | a plan is a `paint_plan/1` file with a known provider (`gemini`, `pod`, `local`); there is no default provider |
| PP-02 | the plan's hash covers its pictures, prompts, references, provider, model, size and tier; `paint run` needs an approval of exactly that hash in the run ledger (`Run.approve`: who, and which message); an edited plan loses its approval |
| PP-03 | the provider can take the batch: a listed price for the model and size, no more references than the provider takes |
| PP-04 | every item has a compiled prompt (`production compile --write`) |
| PP-05 | Gemini on one episode's own pictures (a plan not marked `reusable` and without `episode.gemini_exception`) is a REVIEW note for the creator, never a refusal: the provider choice per batch is the decision (D-50 supersedes the 2026-10-11 "reusable only" rule) |
| PP-06 | every item is a picture of the script and its prompt is still the script's prompt |
| PP-07 | the plan says what the batch is for (REVIEW) |
| PP-08 | the picture library (OR-18, D-63) had matches for an item's prompt when the plan was made: the plan lists them on the item (`library`) and the creator's approval says why a stored picture is not used, or it is fetched instead of painted (REVIEW) |

`paint run` also refuses a script with any PV FAIL (it runs `validate` with the picture folders), reserves every picture in
the ledger before its call, records it with its prompt hash, repaints a picture only when its prompt changed (in a new plan),
never sends an item of an open or lost batch again (`imagegen/gemini.open_batches`), never retries a request that timed out
(`ChargeUncertain`: it may have been billed), and stops an item after three failures. The cache of paid pictures is shared by
every output folder (`EXPLAINER_IMAGE_CACHE`).

## Voice direction

The voice block states how the narrator sounds in descriptive words (soft, deep, calm, warm, mature; emotion carried quietly). It is
a description of a sound, never "like <person>": no imitation and no cloning (PV-10, rights layer). The creator picks the actual voice
from the candidates after a short test read; the full read follows only then.

The read is made in chunks (`tts_chunks.json`, written by `compile`): whole segments, at most 900 characters each, one generation
per chunk with the same voice, model and settings, each given the text before and after it. With voiced dialogue (D-45) a chunk never mixes speakers and names its `speaker` and `voice_id`; `words` then checks each voice against its own turns. One generation of a whole 3-minute
read drifted to another-sounding voice after about three minutes (Day 1, 2026-10-16). `production words <script> T01.mp3 T02.mp3 ...`
joins the chunks in order, and `audio/voice_check.py` lists every 15 s window whose timbre is far from the read's own median
(VOICE-1, REVIEW: listen there; a chunk that sounds like another voice is read again, only that chunk).
