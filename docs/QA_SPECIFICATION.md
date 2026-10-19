# QA specification

Technical QA and editorial QA are separate reports. Findings use the TMR tier idea (copied in Phase 6): **FAIL** for
objective defects and policy blockers, **REVIEW** for judgement, **INFO** for notes; an unanswered review item never
defaults to pass. A deterministic FAIL cannot be overridden by an assertion.

## Technical QA (automated where feasible)
| ID | Check | Threshold / rule |
|---|---|---|
| Q-T01 | required files present (video, Shorts, thumbnail, captions, metadata, sources, manifest) | all present |
| Q-T02 | container, codec, size, aspect, fps, duration | match P-12 to P-15; CFR |
| Q-T03 | corrupt or truncated output | ffprobe decodes whole file |
| Q-T04 | black, blank or frozen frames | none beyond declared holds |
| Q-T05 | missing scene, asset, transition | manifest equals render log |
| Q-T06 | A/V sync | scene starts within +/- 1 frame of anchors; SFX within 1 frame |
| Q-T07 | silence, clipping, loudness, true peak | P-90, P-91, P-95 |
| Q-T08 | voice-to-music gap while speaking | >= 10 dB |
| Q-T09 | captions | no overlap, <= 2 lines, timing +/- 100 ms, inside safe area |
| Q-T10 | text safe margins and label size | P-64, 10 % margins |
| Q-T11 | palette and font lint of every SVG and frame text | tokens only |
| Q-T12 | Shorts present for planned Shorts; duration <= 60 s | P-11 |
| Q-T13 | thumbnail present, size, format | P-17 |
| Q-T14 | disk and memory log | peak RAM < 10 GB; disk reserve kept |
| Q-T15 | job completeness | no stage RUNNING or FAILED |
| Q-T16 | licence register covers every font, SFX and music file | no unknown |
| Q-T17 | the edit follows the [Universal Rule Base](UNIVERSAL_RULE_BASE.md) | `edit/shot_rules.check_shots`: 0 FAIL; REVIEWs answered |
| Q-T18 | the narration WAV keeps the base render's timings (D-38) | P-99: length delta <= 33 ms, lag <= 20 ms; `voice_report.json` says `used: altered` |

## Editorial QA (a human or a reviewing Claude session; an LLM cannot establish truth by assertion)
| ID | Question |
|---|---|
| Q-E01 | Is the hook clear (premise, relevance, first frame)? |
| Q-E02 | Is every claim sourced, and is uncertainty worded honestly? |
| Q-E03 | Does the payoff keep the title and thumbnail promise? |
| Q-E04 | Is the story coherent, with sections doing distinct jobs? |
| Q-E05 | Does it sound spoken, without the flagged patterns (NARRATION guide)? |
| Q-E06 | Do visuals match what is said, at a pace a first-time viewer follows? |
| Q-E07 | Do animation timing and sound effects clarify rather than decorate? |
| Q-E08 | Does the humour suit the topic (no ridicule of people, no false facts)? |
| Q-E09 | Is the Short understandable alone with its own payoff? |
| Q-E10 | Are title, thumbnail and description honest and consistent with the style bible? |
| Q-E11 | Is Kit on model (the sheet) and the world consistent? |
| Q-E12 | Policy checklist (below) answered. |
| Q-E13 | Franchise episodes: rights check (`rights/ip_check.py`) has no FAIL and every REVIEW is answered; the analysis purpose (RR-01, RR-06) is visible in every scene. |
| Q-E14 | Franchise episodes: does it satisfy both a casual viewer (on-ramps, no unexplained names) and a fan (deep cuts, real theories credited, canon respected or bent on purpose)? |

## Policy checklist (answered for every video; sources V-01, V-02, V-03)
Inauthentic-content: does the video add its own explanation, structure and visuals rather than a template swap (a distinct
storyline and concept per video)? Disclosure: does it contain realistic content (a real person made to say or do something,
altered real footage, a realistic scene that did not occur) or AI music as its main focus? If yes, use the Studio altered
or synthetic content label; cartoon visuals, AI-assisted scripting and a synthetic narrator who is not a real person's
likeness do not by themselves require it (re-verify against the current page before each publishing batch). Audience: set
"not made for kids" in Studio. Copyright: every asset has a licence record. Sensitive topics: second read done.

## Publish checklist (PC-xx; `qa/publish_check.py` on the episode's `publish.json`, schema `publish/1`; audit 2026-10-19)

Free and deterministic; it says what is missing or contradicts a rule, the decisions stay the creator's. Pages opened
2026-10-19; re-open them before each publishing batch.

| Id | Rule |
|---|---|
| PC-01 | the file matches `publish/1`; chapters start at 0:00, at least three, ascending, each at least 10 s (Help 9884579) |
| PC-02 | audience "not made for kids" (D-17; Help 9528076) |
| PC-03 | GenAI disclosure (Help 14328491): photoreal pictures, a realistic real person saying or doing what they did not, an altered real event or place, or AI music as the main focus need "disclose"; each trigger is answered true or false (REVIEW); real people with invented lines are flagged from the script |
| PC-04 | a Short over 60 s uses only our own voice, library or procedural audio: any claim blocks a Short that long (Help 15424877) |
| PC-05 | a Short is at most 180 s |
| PC-06 | title at most 100 and description at most 5,000 characters |
| PC-07 | a source link in the description, the mid-roll decision and the advertiser self-certification recorded (REVIEW) |
| PC-08 | approval #2 recorded (who, which message); without it nothing is uploaded (REVIEW; invariant 4) |

**Packaging review (Claude, in the session, before approval #2):** read the title, the thumbnail and the transcript of the
first 30 s together and answer in writing: does the opening deliver what the title and thumbnail promise (Help 16559650), is
anything misleading (Help 2801973, thumbnails Help 9229980), and does the episode differ from the earlier ones in premise and
outcome (the inauthentic-content line "characters put in the same situation over and over again with the same outcome",
Help 1311392). A "no" is a finding for the owner stage.

## Review bundle
Contact sheet of mid-scene frames; scene preview clips; narration preview; audio peak and silence report; captions
preview; the high-risk-scene list; unresolved factual issues; thumbnail preview; the technical report; the editorial
checklist; the cost and time log. Built so a human can review one episode in about 30 minutes.

## Gates
The prototype and every video: no technical FAIL; editorial items answered; policy checklist complete; creator approval
recorded in `acceptance_report.md` / the package. Stop and report after 5 iterations on the same issue.
