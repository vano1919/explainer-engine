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
| P-05 | humour budget | <= 1 verbal joke / 60 s | 0-2 | tone, taste | L/C | script QA | flag only (review, never auto-edit) |
| P-06 | editorial boundaries | no advice, no medical/legal claims, no real-person claims without a source | list | risk rules | H/F | claim map | claim reviewer + checklist |
| P-07 | cadence (cycle 1) | 1 long-form / 2 weeks + 2 Shorts / week | measured later | own hours, not competitors (D-06, SE-26) | L/P | time log | reviewed after 3 long-forms |

## 2. Video, render and export
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-10 | long duration | 7 min | 5-11 | depth without padding | L/P,T | word budget | outside range = REVIEW, not FAIL |
| P-11 | short duration | 45 s | 25-60 | standalone Shorts | L/P,T | script | > 60 s = FAIL (no longer Shorts at launch) |
| P-12 | resolution | 1920x1080 (16:9), 1080x1920 (9:16) | fixed pair | vector art needs no 4K (D-08) | H/F | renderer | ffprobe |
| P-13 | frame rate | 30, constant | 24, 30 | smooth motion at low cost | M/C | cache key | ffprobe CFR |
| P-14 | video codec | H.264 High, yuv420p, CRF 18, preset medium, +faststart | CRF 16-23 | quality vs size (D-08) | H/C | disk | ffprobe |
| P-15 | audio codec | AAC-LC 48 kHz stereo 384 kbps | 192-384 kbps | TMR measured pipeline; YouTube re-encodes | M/C | mix | ffprobe |
| P-16 | container, names | mp4; `<slug>_<yyyymmdd>_<kind>.mp4` | | traceability | H/F | manifest | regex |
| P-17 | thumbnail | 1280x720 PNG <= 2 MB (re-verify limit) | | packaging (TITLE_THUMBNAIL_SYSTEM) | M/F | thumbnail render | file check |
| P-18 | captions | sidecar SRT/VTT from word timings; Shorts burned in | | accessibility, silent viewing | M/C | timings | overlap, safe-area, timing +/- 100 ms |
| P-19 | chapters | >= 3, first at 0:00, each >= 10 s (re-verify) | | navigation | M/F | timeline | metadata check |
| P-20 | publish | manual only, approval record required | | policy, creator rule | H/F | none | no upload code path |

## 3. Story and script
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-30 | premise clear by | 10 s long, 3 s Short | | hook (D-07) | L/P | hook spec | editorial checklist |
| P-31 | first answer by | <= 40 % of runtime | 25-60 % | no withheld payoff | L/P | structure | marker in storyboard |
| P-32 | words (long) | duration x heard pace (about 1,050 for 7 min) | | budget | M/T | P-52 | +/- 12 % = REVIEW |
| P-33 | claim coverage | every factual sentence -> >= 1 claim -> >= 1 source | | honesty (SCRIPTING_SPEC) | H/F | dossier | traceability FAIL |
| P-34 | uncertainty labels | fact, estimate, interpretation, allegation, speculation | enum | accurate wording | H/F | claim map | enum + wording check |
| P-35 | sentence length | mostly 8-18 words, variety | | spoken naturalness | M/C | NARRATION guide | metric flag (review) |
| P-36 | rhetorical questions | <= 1 per section | 0-2 | avoid AI cadence | M/C | | flag |
| P-37 | filler / cliche list | see NARRATION guide | | review flags | M/C | | flag, never auto-delete |
| P-38 | CTA policy | none in the body; one line in the description | | trust, inauthentic-content risk (V-01) | M/C | | flag |
| P-39 | conclusion | one short payoff line, no recap | | | M/C | | flag |

## 4. Narration and language
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-50 | TTS route | Kokoro-82M local | (listening test) | zero cost, timings exist (D-12) | M/P | Phase 5 test | blind A/B vs one cloud voice |
| P-51 | voice | chosen in the Phase 5 test, male or female, warm/clear | Kokoro built-in voices only | rights layer (built-ins only) | L/P | P-50 | listening panel |
| P-52 | heard pace | 170 wpm | 155-185 | D-49: engagement rises with pace (Guo 2014), 180 wpm best for recall in Rodero 2020, comprehension holds to ~330 (Murphy 2022); Episode 1 read at 120-140 and felt slow | M/P | voice | measured post-TTS, +/- 10 % |
| P-53 | pauses | sentence 0.35 s, paragraph 0.7 s, before a reveal 0.9 s | 0.2-1.2 s | rhythm | L/C | | measured |
| P-54 | pronunciation | `pronunciations.json` (project) over speakable() defaults | | numbers, units, acronyms | M/C | TTS | ASR word error check |
| P-55 | numbers | spoken form decided in the script, never left to TTS | | accuracy | H/F | script | lint: digits in narration need a spoken form |
| P-56 | sample rate | 24 kHz native, resampled to 48 kHz | | Kokoro output | H/F | | sample-rate check |

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
| P-70 | shot length | superseded by UR-11 (A 5-7 s, B 3.5-5 s, C 2.5-4 s) and UR-12 (cuts in pauses) | | creator's style, D-37 (SE-20 rejected a universal rate) | M/F | narration | `edit/shot_rules.py` |
| P-71 | label hold | >= 1.5 s + 0.3 s per word | | reading | M/C | | validator |
| P-72 | simultaneous movers | <= 3 | 1-5 | clutter ceiling | M/C | | REVIEW above |
| P-73 | easing | in-out cubic; entrances out-back, overshoot about 1.1, 12-18 frames | enum | natural motion | M/C | vocabulary | enum |
| P-74 | lip-sync lead | 1 frame (30 ms) | 0-2 | matches TMR viseme finding | M/C | timings | sync test |
| P-75 | idle motion | blink every 4-8 s in silence, slow sway | | life without distraction | M/C | visemes | seeded, deterministic |
| P-76 | transitions | cut, wipe, lid-open reveal; max 1 per scene | enum | purposeful change | M/C | | enum |
| P-77 | missing-asset fallback | named placeholder, job stops at QA | | never silent | H/F | | QA FAIL |
| P-78 | reduced motion | static hold variant noted per scene where practical | | accessibility | L/C | | note present |

## 7. Audio
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-90 | integrated loudness | -14 LUFS +/- 1 | -16 to -13 | playback normalisation (D-08) | M/C | mix | ebur128 FAIL outside |
| P-91 | true peak | <= -1.0 dBTP | | codec headroom | H/F | mix | ebur128 |
| P-92 | voice shaping | de-ess, gentle low-cut, soft limit (TMR shape_voice) | | clarity | M/C | | level audit |
| P-93 | music | one state per scene group; speech gap >= 10 dB; attack 50 ms, release 400 ms | | speech first (D-18) | M/C | | measured gap |
| P-94 | SFX | each event has purpose clarify/humour/transition; peak <= voice peak - 3 dB | | not on every movement | M/F | event contract | schema + level audit |
| P-95 | silence | no unintended silence > 1.5 s (long-form), > 0.8 s (Shorts) | | pacing | M/C | | audio scan |
| P-96 | fades | 20 ms edge fades on clips; music 1 s in, 2 s out | | no clicks | M/C | | click check |
| P-97 | missing audio | job stops at QA, never a silent video | | | H/F | | QA FAIL |
| P-98 | narrator voice | a Kokoro base voice + up to 3 blended voices (together <= 0.5), pitch -2..+2 semitones, tone shelves, `rvc: null` | blend sum <= 0.5; pitch +/-2 st | one narrator sound for the channel; no real person is imitated (D-38) | M/P | voice spec (`explainer_engine/schemas/voice_spec.schema.json`) | schema + `voice_layer.validate_voice_spec` |
| P-99 | timing contract of the alteration | length change <= 1 frame (33 ms); word-onset lag <= 20 ms | | the cuts are placed on the base render's pauses (UR-12) | M/F | base render | `voice_layer.timing_preserved`; failing audio is not used |

## 8. Shorts, publishing and cost
| ID | Parameter | Default | Allowed | Purpose, evidence | Conf/Status | Depends on | Validation |
|---|---|---|---|---|---|---|---|
| P-100 | Shorts per long-form | 2-3, only if the material supports distinct ideas | 0-3 | D-05 | M/P | dossier | each passes standalone checklist |
| P-101 | Short loudness | -14 LUFS, TP <= -1.0 | | consistency | M/C | | ebur128 |
| P-102 | Short safe area | keep bottom 420 px and right 140 px clear of text | | platform UI overlays (TMR measured) | M/C | | safe-area check |
| P-103 | Short captions | phrase captions <= 2 lines x 32 chars, current word lit | | silent viewing | M/P | timings | check |
| P-104 | analytics snapshots | 48 h, 7 d, 28 d | | like-for-like comparison | M/C | | record present |
| P-110 | Gemini cap | $10 total; per-call-batch `max_usd` default $1 | | creator budget | H/F | cost ledger | estimate before call; refuse above |
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
