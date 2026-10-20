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
| Q-T06 | A/V sync | scene starts within +/- 1 frame of anchors; a picture-synced sound inside the window of BP-54 (never early) |
| Q-T07 | silence, clipping, loudness, true peak | P-90, P-91, P-95 |
| Q-T08 | voice-to-background gap while speaking | the LU floors of BP-52 on the stems (music, bed, their sum) |
| Q-T09 | captions | no overlap, <= 2 lines, timing +/- 100 ms, inside safe area |
| Q-T10 | text safe margins and label size | P-64, 10 % margins |
| Q-T11 | palette and font lint of every SVG and frame text | tokens only |
| Q-T12 | Shorts present for planned Shorts; duration <= 180 s (V-25), house length P-11 | P-11 |
| Q-T13 | thumbnail present, size, format | P-17 |
| Q-T14 | disk and memory log | peak RAM < 10 GB; disk reserve kept |
| Q-T15 | job completeness | no stage RUNNING or FAILED |
| Q-T16 | licence register covers every font, SFX and music file | no unknown |
| Q-T17 | the edit follows the [Universal Rule Base](UNIVERSAL_RULE_BASE.md) | `edit/shot_rules.check_shots`: 0 FAIL; REVIEWs answered |
| Q-T18 | retired with Kokoro (D-39 / D-52): no alteration layer runs on an ElevenLabs read, so no `voice_report.json` is expected | P-99 stays for old drafts only |
| Q-T19 | export matches YouTube's recommended upload settings (V-26) | MP4, H.264 High progressive, BT.709, frame rate as rendered; audio per BP-63 (`assemble.AUDIO_CODEC`) |

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
| Q-E16 | Every episode: the engagement gate (`python -m explainer_engine.qa.engagement <script>`, EPISODE_STANDARDS section 7) ran before script approval and before the final render; every weak beat it names has a revision or a written reason. |
| Q-E17 | Every episode: the story hypotheses (`research/hypotheses.py`, section 8) had at least three premises, the selected one scored evidence >= 3, and the beat sheet ends on a payoff. |
| Q-E14 | Franchise episodes: does it satisfy both a casual viewer (on-ramps, no unexplained names) and a fan (deep cuts, real theories credited, canon respected or bent on purpose)? |

## Policy checklist (answered for every video; sources V-01, V-02, V-03, re-checked V-13, V-14; recorded in the episode rulebook)
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
| PC-08 | approval #2 recorded (who, which message); without it nothing is uploaded (FAIL; invariant 4; `publish stage` blocks on it) |
| PC-09 | the episode's gates have run: the rulebook's `final_qa` stamp passes (`standards gate`) and `scorecard.json` (the seven-point test, `qa/scorecard <folder>`) has no FAIL; missing means not run and blocks (FAIL) |

**Packaging review (Claude, in the session, before approval #2):** read the title, the thumbnail and the transcript of the
first 30 s together and answer in writing: does the opening deliver what the title and thumbnail promise (Help 16559650), is
anything misleading (Help 2801973, thumbnails Help 9229980), and does the episode differ from the earlier ones in premise and
outcome (the inauthentic-content line "characters put in the same situation over and over again with the same outcome",
Help 1311392). A "no" is a finding for the owner stage.

## Final QA areas (master prompt 2026-10-17, section 12) and where each is checked
| Area | Checks |
|---|---|
| Story and evidence | Q-E02, Q-E04, Q-E17, claim map (invariant 5) |
| Rulebook compliance | Q-E15 (`standards gate --at final_qa`), Q-E13 |
| Narration | Q-E05, Q-T18, PV-20, `voice_check`, ED-01, ED-12 |
| Visuals | Q-E06, Q-E11, `visual_judge`, PV-24, PV-40 |
| Audio | Q-T07, Q-T08, PV-29, PV-41, `qa/targets.py` |
| Editing | Q-T17, Q-E07, ED-01..ED-12, captions Q-T09, Q-T10 |
| Assets and provenance | Q-T16, ES-09, the run ledger (`core/ledger.py`) |
| Originality and engagement | Q-E16, ES-13, ES-14 |
| Delivery | Q-T01..Q-T03, Q-T19, the rulebook's disclosure `upload_action` (ES-08), approval #2 |

A green check is not a watched video: the contact sheet, three joins, the loudest chunk seams and the whole final playback are
looked at and listened to before approval #2 (OR-07).

## Review bundle
Contact sheet of mid-scene frames; scene preview clips; narration preview; audio peak and silence report; captions
preview; the high-risk-scene list; unresolved factual issues; thumbnail preview; the technical report; the editorial
checklist; the cost and time log. Built so a human can review one episode in about 30 minutes.

## Gates
The prototype and every video: no technical FAIL; editorial items answered; policy checklist complete; creator approval
recorded in `acceptance_report.md` / the package. Stop and report after 5 iterations on the same issue.

## Picture review by Claude (audit 2026-10-19)

The visual judge's questions (`qa/visual_judge.QUESTIONS`) are answered by Claude in the session, not by a paid model:
`python -m explainer_engine.qa.sheet_review request <script> --pictures <dir>` writes the questions per picture, Claude opens every
file and writes `visual_review.json` (`visual_review/1`: a boolean per question, a `why_` for every true answer), and
`python -m explainer_engine.qa.sheet_review apply <script> <visual_review.json>` gives PASS / FAIL / REVIEW per picture. A FAIL means a
repaint in a new approved paint plan. `GeminiClient.judge` stays for the creator's explicit request only and reserves in the ledger.

Two camera limits differ on purpose until the creator decides: `production/continuity.ZMAX` 1.25 (the furthest push on one
picture in the D-43 script) and `edit/shot_rules.MAX_ZOOM` 1.15 (UR-13, the storyboard rule). Neither was changed by the audit.
