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
| Q-E15 | Every episode: the rulebook gate `final_qa` passes ([EPISODE_STANDARDS](EPISODE_STANDARDS.md)): no open BLOCK/REVIEW/ADAPT, licences verified, no placeholder credit, the disclosure decision recorded, and the last stamp matches the final script. |
| Q-E14 | Franchise episodes: does it satisfy both a casual viewer (on-ramps, no unexplained names) and a fan (deep cuts, real theories credited, canon respected or bent on purpose)? |

## Policy checklist (answered for every video; sources V-01, V-02, V-03, re-checked V-13, V-14; recorded in the episode rulebook)
Inauthentic-content: does the video add its own explanation, structure and visuals rather than a template swap (a distinct
storyline and concept per video)? Disclosure: does it contain realistic content (a real person made to say or do something,
altered real footage, a realistic scene that did not occur) or AI music as its main focus? If yes, use the Studio altered
or synthetic content label; cartoon visuals, AI-assisted scripting and a synthetic narrator who is not a real person's
likeness do not by themselves require it (re-verify against the current page before each publishing batch). Audience: set
"not made for kids" in Studio. Copyright: every asset has a licence record. Sensitive topics: second read done.

## Review bundle
Contact sheet of mid-scene frames; scene preview clips; narration preview; audio peak and silence report; captions
preview; the high-risk-scene list; unresolved factual issues; thumbnail preview; the technical report; the editorial
checklist; the cost and time log. Built so a human can review one episode in about 30 minutes.

## Gates
The prototype and every video: no technical FAIL; editorial items answered; policy checklist complete; creator approval
recorded in `acceptance_report.md` / the package. Stop and report after 5 iterations on the same issue.
