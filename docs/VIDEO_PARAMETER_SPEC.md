# Video production parameter specification

Canonical home of every parameter's default, range, evidence label, status and validation. Evidence labels follow
`explainer_engine/core/labels.py` (sourced, measured, engineering_default, hypothesis, playback_dependent). Status: **F**
fixed, **C** configurable, **T** topic-dependent, **P** provisional (a named test can change it). Confidence H/M/L.
Colour values are in `explainer_engine/design/palette.json`, not here. Decisions behind a row: see the D- reference.

**Invalid / missing values (all groups):** an out-of-range or wrongly typed value is a `ConfigError` before the job
starts (nothing is spent). A missing optional value takes the default and the job log records "default used". A missing
**required** value (marked req) is a `ConfigError`. Configuration is grouped by responsibility (channel, topic, script,
voice, visual, assets, storyboard/render, audio, shorts, qa, cost, retry, output, approval) with the precedence
CLI flag > episode file > channel profile > built-in default ([PIPELINE_ARCHITECTURE](PIPELINE_ARCHITECTURE.md)).

## 1. Channel
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-01 | language | en, US-neutral spelling | en | audience and TTS support (D-09) | M/P | TTS voice | enum |
| P-02 | audience_setting | not_made_for_kids | enum | official guidance (V-03, D-17) | H/F | packaging | upload checklist item |
| P-03 | collision types | you_in_era, past_meets_present, era_meets_era, world_what_if, how_it_worked, money_across_eras, myth_vs_record | subset | the "worlds collide" positioning (D-25) | M/P | topic intake | topic must name a type and only public-domain or factual worlds |
| P-04 | third-party fictional worlds | allowed only as analysis episodes under RR-01..RR-13 (D-26) | rights check PASS | IP rules (V-07..V-12) | M/F | rights manifest | `rights/ip_check.py`: any FAIL blocks the package |
| P-05 | humour budget | <= 1 verbal joke / 60 s | see BP-09 | tone, taste | L/C | script QA | flag only (review, never auto-edit) |
| P-06 | editorial boundaries | no advice, no medical/legal claims, no real-person claims without a source | list | risk rules | H/F | claim map | claim reviewer + checklist |
| P-07 | cadence (cycle 1) | 1 long-form / 2 weeks + 2 Shorts / week | measured later | own hours, not competitors (D-06, SE-26) | L/P | time log | reviewed after 3 long-forms |

## 2. Video, render and export
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-10 | long duration | 7 min | 5-11 | depth without padding | L/P,T | word budget | outside range = REVIEW, not FAIL |
| P-11 | short duration | the length bands of BP-12 | see BP-12 | standalone Shorts; YouTube counts square/vertical videos up to 3 minutes as Shorts (V-25) | L/P,T | script | PV-28 (BP-12 word budget); > 180 s FAIL (not a Short) |
| P-12 | resolution | 1920x1080 (16:9), 1080x1920 (9:16) | fixed pair | vector art needs no 4K (D-08) | H/F | renderer | ffprobe |
| P-13 | frame rate | 30, constant | 24, 30 | smooth motion at low cost | M/C | cache key | ffprobe CFR |
| P-14 | video codec | H.264 High, yuv420p, CRF 18, preset medium, +faststart | CRF 16-23 | quality vs size (D-08) | H/C | disk | ffprobe |
| P-15 | audio codec | AAC-LC stereo, bitrate and sample rate per BP-63 | see BP-63 | YouTube's recommended upload settings (V-26); `assemble.AUDIO_CODEC` is the one export line for the video and the Shorts | H/F | mix | ffprobe |
| P-16 | container, names | mp4; `<slug>_<yyyymmdd>_<kind>.mp4` | | traceability | H/F | manifest | regex |
| P-17 | thumbnail | 1280x720 PNG <= 2 MB (re-verify limit) | | packaging (TITLE_THUMBNAIL_SYSTEM) | M/F | thumbnail render | file check |
| P-18 | captions | sidecar SRT/VTT from word timings; Shorts burned in at the reading speed of BP-13 | see BP-13 | accessibility, silent viewing | M/C | timings | overlap, safe-area (BP-29), timing (BP-13) |
| P-19 | chapters | >= 3, first at 0:00, each >= 10 s (re-verify) | | navigation | M/F | timeline | metadata check |
| P-20 | publish | manual only, approval record required | | policy, creator rule | H/F | none | no upload code path |

## 3. Story and script
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-30 | premise clear by | the first spoken sentence is the hook (BP-03) and the title's promise is confirmed inside the 30-second contract (BP-04); a Short's hook by BP-11 | see BP-03, BP-04, BP-11 | hook (D-07) | L/P | hook spec | narration_lint, PV-28 |
| P-31 | first answer by | <= 40 % of runtime | 25-60 % | no withheld payoff | L/P | structure | marker in storyboard |
| P-32 | words (long) | duration x the heard pace of BP-01 | see BP-01 | budget | M/T | P-52 | +/- 12 % = REVIEW |
| P-33 | claim coverage | every factual sentence -> >= 1 claim -> >= 1 source | | honesty (SCRIPTING_SPEC) | H/F | dossier | traceability FAIL |
| P-34 | uncertainty labels | fact, estimate, interpretation, allegation, speculation | enum | accurate wording | H/F | claim map | enum + wording check |
| P-35 | sentence length | for the ear: the median and the caps of BP-06, variety | see BP-06 | spoken naturalness | M/C | NARRATION guide | narration_lint N-05 |
| P-36 | rhetorical questions | <= 1 per section (a house hypothesis: no sourced rule names a rate; the forward-pointing questions follow BP-42) | 0-2 | avoid AI cadence | M/C | | flag |
| P-37 | filler / cliche list | see NARRATION guide | | review flags | M/C | | flag, never auto-delete |
| P-38 | CTA policy | none in the body; one line in the description | | trust, inauthentic-content risk (V-01) | M/C | | flag |
| P-39 | conclusion | one short payoff line, no recap | | | M/C | | flag |

## 4. Narration and language
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-50 | TTS route | ElevenLabs (D-39, D-52; the voice is chosen per episode in `production_script.json`, D-43) | - | Kokoro-82M (D-12) was the free draft route and is retired; its timings code is a leftover | H/F | skill `elevenlabs-voice` | the PreToolUse hook (`standards/hook.py`) |
| P-51 | voice | an ElevenLabs library voice, never a clone, never a famous person (D-39); `voice_id` per episode (D-43, voice-caster) | library voices | rights (D-38, ES-11) | H/F | P-50 | rulebook ES-11 |
| P-52 | heard pace | target and band per BP-01 (a hypothesis: five studies agree on the norm, one source type) | see BP-01 | engagement rises with pace; Episode 1 read at 120-140 and felt slow (D-49) | M/P | voice | measured on the finished read (scorecard check 1, PV-12) |
| P-53 | pauses | sentence 0.35 s, paragraph 0.7 s (house, measured by `pause_pad`); no pause before a punch line or a reveal: BP-10 | see BP-10 | rhythm | L/C | | measured |
| P-54 | pronunciation | `pronunciations.json` (project) over speakable() defaults | | numbers, units, acronyms | M/C | TTS | ASR word error check |
| P-55 | numbers | spoken form decided in the script, never left to TTS; one numeral a sentence, rounded, and shown on screen when it matters (BP-08) | see BP-08 | accuracy | H/F | script | narration_lint N-13 |
| P-56 | sample rate | the read as ElevenLabs delivers it, resampled to the delivery rate of BP-63 | see BP-63 | the mix and the export run at one rate (the 24 kHz line was Kokoro's, retired by D-39) | H/F | | sample-rate check |

## 5. Visual and assets
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-60 | medium | painted pictures (pod) + keyed sprites; the SVG plan is superseded (D-27, D-36) | | the creator's look (D-27) | H/F | renderer | asset check |
| P-61 | stroke | 6 px characters, 4 px props at 1080p; round caps | | style (STYLE_BIBLE) | M/F | rig | SVG lint |
| P-62 | palette | palette.json tokens only | | identity, contrast (D-22) | H/F | all art | colour lint + palette test |
| P-63 | typography | Fredoka titles, Inter labels | OFL fonts | licence, legibility | H/F | renderer | font check |
| P-64 | label size | >= 40 px long-form, >= 56 px Shorts at native size | | mobile reading | M/C | | storyboard check |
| P-65 | on-screen labels | <= 6 at once | | density | M/C | | REVIEW above |
| P-66 | asset ids | `<kind>.<name>[.<variant>]` e.g. `char.kit`, `prop.onion`, `bg.kitchen` | | stable references | H/F | manifest | regex + uniqueness |
| P-67 | asset formats | SVG first; PNG only if SVG loses value | | editability | H/F | ASSET_SYSTEM | licence + viewBox present |

## 6. Animation
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-70 | shot length | superseded by UR-11 (the type ranges of BP-85), UR-12 (cuts in pauses) and BP-40 (pictures a minute, still limits) | see BP-85, BP-40 | creator's style, D-37 (SE-20 rejected a universal rate) | M/F | narration | `edit/shot_rules.py` |
| P-71 | label hold | >= 1.5 s + 0.3 s per word (satisfies the floor of BP-27, which adds the cap) | see BP-27 | reading | M/C | | validator (motion_lint) |
| P-72 | simultaneous movers | <= 3 | 1-5 | clutter ceiling | M/C | | REVIEW above |
| P-73 | easing | in-out cubic; entrances out-back, overshoot about 1.1, 12-18 frames; every camera move eased per BP-23 | enum, see BP-23 | natural motion | M/C | vocabulary | enum, motion_lint |
| P-74 | lip-sync lead | 1 frame (30 ms) | 0-2 | matches TMR viseme finding | M/C | timings | sync test |
| P-75 | idle motion | blink every 4-8 s in silence, slow sway | | life without distraction | M/C | visemes | seeded, deterministic |
| P-76 | transitions | hard cut by default; a dissolve only at a change of place or time (BP-31, D-64); wipe and lid-open reveal retired | see BP-31 | purposeful change | M/C | | motion_lint |
| P-77 | missing-asset fallback | named placeholder, job stops at QA | | never silent | H/F | | QA FAIL |
| P-78 | reduced motion | static hold variant noted per scene where practical | | accessibility | L/C | | note present |

## 7. Audio
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-90 | integrated loudness | target, PASS band and allowed band per BP-50 | see BP-50 | inferred (YouTube's upload settings page names no loudness, V-26); measured on the delivered file with the verdict next to the number | M/C | mix | `qa/targets.py` (`assemble`, `shorts`, scorecard) |
| P-91 | true peak | ceiling and limiter per BP-50 | see BP-50 | codec headroom | H/F | mix | `qa/targets.py` FAIL above the ceiling |
| P-92 | voice shaping | gentle low-cut, light de-ess inside the band and depth of BP-60, soft limit; pauses are room tone, never zeros (BP-60) | see BP-60 | clarity | M/C | | `audio/pause_pad`, level audit |
| P-93 | music | one state per scene group (BP-62); under speech the music, the bed and their sum keep the LU floors of BP-52; the duck is a dip with the depth, attack, release and hold of BP-53 | see BP-52, BP-53 | speech first (D-18) | M/C | | `qa/targets.gap_verdict`, `audio/duck.py` |
| P-94 | SFX | each event has a purpose from BP-55 (clarify, humour, transition, sync); at most one beat in two carries an effect; peak <= voice peak - 3 dB | see BP-55 | not on every movement | M/F | event contract | schema + `audio/layers.py` |
| P-95 | silence | no unintended silence > 1.5 s (long-form), > 0.8 s (Shorts): a house hypothesis with no scanner yet; an inserted pause is room tone (BP-60) | | pacing | M/C | | `audio/dropouts.py` (true zeros only) |
| P-96 | fades | 20 ms edge fades on clips; music fades per BP-62 | see BP-62 | no clicks | M/C | | click check |
| P-97 | missing audio | job stops at QA, never a silent video | | | H/F | | QA FAIL |
| P-98 | narrator voice | superseded by D-39 / D-52: an ElevenLabs library voice per episode (`voice_id` in `production_script.json`, D-43); the Kokoro blend spec (`voice_spec.schema.json`, `rvc: null`) is kept only for old drafts | - | no real person is imitated (D-38) | H/F | voice spec | rulebook ES-11 |
| P-99 | timing contract of the alteration | length change <= 1 frame (33 ms); word-onset lag <= 20 ms | | the cuts are placed on the base render's pauses (UR-12) | M/F | base render | `voice_layer.timing_preserved`; failing audio is not used |

## 8. Shorts, publishing and cost
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-100 | Shorts per long-form | 2-3, only if the material supports distinct ideas | 0-3 | D-05 | M/P | dossier | each passes standalone checklist |
| P-101 | Short loudness | integrated target, true peak and the short-term cap per BP-61; no loudness-range gate | see BP-61 | short-form rules (EBU R 128 s1); measured on the FINAL Short, after cues and music | M/C | | `qa/targets.py` profile `short`, `production/shorts.py` |
| P-102 | Short safe area | the ad safe zone of BP-29 | see BP-29 | platform UI overlays | M/C | | safe-area check |
| P-103 | Short captions | phrase captions in blocks, at the reading speed of BP-13 | see BP-13 | silent viewing | M/P | timings | check |
| P-104 | analytics snapshots | 48 h, 7 d, 28 d | | like-for-like comparison | M/C | | record present |
| P-110 | Gemini cap | ceiling: config/spend_caps.json (D-56); a per-call max_usd in code is a default, not a cap | | creator budget | H/F | cost ledger | estimate before call; refuse above |
| P-111 | vidIQ cap | 200 credits; ledger before each call | | creator budget | H/F | | ledger entry first |
| P-112 | retries | 2 for retryable failures, backoff 2 s, 4 s | | transient errors | M/C | | state.json counts |
| P-113 | disk reserve | job refuses to start with < 10 GB free or < 1.5 x estimate | | constrained storage | M/C | | pre-flight |

## 9. Crossover analysis episodes (fictional worlds, D-26)
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-120 | recap share | <= 20 % of narration words | REVIEW > 20 %, FAIL > 35 % | RR-05, V-12 | M/F | script | `ip_check` |
| P-121 | franchise share of channel | <= 50 % of uploads in a rolling 10 | 0-50 % | RR-12 (identity stays original) | L/C | publishing plan | review at each cycle |
| P-122 | quotes | <= 6 per episode, <= 2 sentences / 40 words each, analysed and attributed | | RR-04 | M/F | script | `ip_check` |
| P-123 | audience balance | >= 30 % of beats tagged casual on-ramp, >= 30 % fan depth, rest both | 25-50 % each | creator rule 2026-10-16: satisfy casual viewers and hardcore fans | L/P | script beat tags | `fan_brief.check_balance` |
| P-124 | fan research depth | >= 6 sources of >= 3 kinds, >= 5 sourced theories, >= 3 fan demands, >= 3 existing crossovers reviewed, >= 2 canon rules per world | | creator rule 2026-10-16 | M/F | fan brief | `fan_brief.check` |
| P-125 | premise originality | token overlap with any reviewed existing crossover title <= 0.6 | | no copying of other creators' takes | L/C | fan brief | `fan_brief.check` (REVIEW) |
