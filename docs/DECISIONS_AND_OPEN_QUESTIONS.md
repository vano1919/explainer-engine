# Decisions and open questions

Canonical home of every decision (D-xx), its alternatives, evidence, confidence, validation and change trigger. Other
documents cite an ID and never restate the reasoning. Status: **fixed** (policy/safety/creator rule), **configurable**,
**provisional** (best current choice, a named test can overturn it), **hypothesis** (an untested idea), **approval gate**
(needs the creator), **decided by creator** (explicit approval).

Instruction precedence when things conflict (directive section 1): platform/security/legal/safety, then the creator's
explicit constraints, then approved decisions, then recorded evidence, then the approved specification, then existing
repository behaviour, then recommendations. A decision is reopened only by new evidence that directly conflicts with it,
a failing test, or an implementation proving it impractical; the smallest viable change is proposed first.

## Decision log

| ID | Decision | Alternatives | Evidence / counter | Conf. | Validation | Change trigger | Status |
|---|---|---|---|---|---|---|---|
| D-01 | Positioning "hidden machinery of everyday things", English, general audience | finance, history, geopolitics, psychology | SE-04/23, B.4 / crowded space | M | 3 long + 9 Shorts | Fallback trigger (A) | provisional |
| D-02 | Pillars P1–P3 | single pillar | breadth for topic supply / dilution risk | M | per-pillar analytics | a pillar < half the others after 6 videos | provisional |
| D-03 | Formats list; rankings only when natural | countdown-first | directive §2, SE-24 | H | editorial QA | — | fixed |
| D-04 | Original mascot Kit + cutaway motif | no mascot; duo | SE-05/06/07 | M | creator review, Shorts recognisability | creator rejects design | approval gate |
| D-05 | Long-form core + 2–3 standalone Shorts | Shorts-only | directive §9; SE-23 sample is Shorts | M | Shorts vs long metrics separately | Shorts drive > 80 % subs and long-forms stall → rebalance | provisional |
| D-06 | Cadence 1 long / 2 wks + 2 Shorts / wk | weekly long | own time log | L | hours log | measured hours | hypothesis |
| D-07 | Hook framework: first frame shows the object and Kit already acting; first sentence is a concrete observation, no greeting; premise clear within ~10 s long / ~3 s Short; the promise is answered at least briefly before 40 % of runtime | greeting intro; delayed payoff to the last seconds (SE-21) | SE-10, SE-13; no threshold is established, so all times are hypotheses | L | per-video hook spec + viewed-vs-swiped and first-30-s retention | 3 comparable videos show an early drop despite a clear hook | hypothesis |
| D-08 | Export targets: 1080p30 H.264 (CRF 18, yuv420p, +faststart), AAC-LC 48 kHz 384 kbps; integrated loudness -14 LUFS +/- 1, true peak <= -1.0 dBTP | 4K; -16 LUFS; no loudness gate | vector art gains nothing from 4K; the loudness target is common playback-normalisation practice, not an official YouTube rule (playback dependent) | M | ebur128 on every render; listening on phone speaker and headphones | a measured playback problem, or an official YouTube loudness statement | provisional |
| D-09 | English (US-neutral spelling), general audience (teens and adults) | multi-language launch; kids | SE-02 (weak), V-03 | M | audience geography and retention of the first 3 videos | analytics show a different core audience | provisional |
| D-10 | Remotion primary; skia-python fallback | Motion Canvas, Revideo, Manim | V-04/05 | M | Phase-4 benchmark | benchmark/licence fail | provisional |
| D-11 | Python orchestrates; Node renders muted video; Python mixes audio | all-in-Remotion audio | repo mix/loudness tested | H | Phase 5 tests | — | provisional |
| D-12 | Kokoro local TTS, livelier delivery | ElevenLabs, Gemini TTS | cost 0, timings / expressiveness unknown | M | blind listening test | test rejects Kokoro | provisional |
| D-13 | Research + script drafting by Claude Code sessions via project skills (sources recorded with URL, access date, quote); Python validates claim map + style checks; creator approves | local LLM writes (TMR model); paid API | quality of facts matters most; no per-token cost under the plan | M | editorial QA scores | session limits or quality issues | **decided by creator 2026-10-15** |
| D-21 | Separate new repository; TMR modules copied with provenance, no runtime import | same repo package; shared core | creator decision; isolates the two projects | H | copied tests pass | — | **decided by creator 2026-10-15** |
| D-14 | JSON Schema canonical + `jsonschema` | pydantic, hand checks | already a dependency, language-neutral, TS types | H | contract tests | — | provisional |
| D-15 | Editorial originality gate (distinct story per video, no templated filler) | — | V-01 | H | QA checklist | policy change | fixed |
| D-16 | Disclosure decided per video by checklist (realistic? real person? AI music as focus?) | always/never disclose | V-02 | H | upload checklist | policy change | fixed |
| D-17 | "Not made for kids", adult/teen tone | — | V-03 | H | packaging review | policy change | fixed |
| D-18 | Music: procedural (repo `music_synth`) or CC0/licensed with per-file record; no commercial tracks | Lyria (paid) | rights | M | licence register | — | provisional |
| D-19 | Gemini only for reusable channel-identity assets, never per-topic pictures | — | creator's rule 2026-10-11 (CLAUDE.md) | H | ledger | — | fixed |
| D-20 | Prototype = onions | leap years, round plane windows | B.4 low risk | M | F criteria | dossier fails verification → leap years | approval gate |
| D-22 | Accent colours are fills only: every meaningful shape carries an ink stroke; text sits on paper, night or an ink-compatible fill; small red text is forbidden (false_red = large text only) | accents carrying meaning by colour alone | measured: accents are 1.5-3.7:1 against paper, ink on paper 14.7:1 (explainer_engine/design/palette.py) | H | tests/unit/test_palette.py | a palette change that keeps the tests green | fixed |
| D-23 | One canonical home per ID and per specification; other documents link, never copy; enforced by a docs lint test | duplicated tables per document | directive sections 7 and 20; tests/unit/test_docs.py | H | docs lint | none | fixed |

## Fallback positioning
"Money and incentives, explained" (pillar P2 as the whole channel). Trigger: after at least 6 long-forms and 15 Shorts,
P2 episodes beat P1/P3 on both CTR and average percentage viewed in like-for-like comparisons (same length band, same
age, similar traffic source). Cost: higher editorial burden (the advice boundary, fast-dating figures).

## Open questions (only what cannot be decided responsibly)
- Q1 Repository placement: **decided** (D-21).
- Q2 Channel name and Kit's final name and look: creator gate; draft sheet `assets/characters/kit/kit_reference.svg`.
- Q3 Voice: decided by the Phase 5 blind listening test (D-12), not now.
- Q4 Installing Node.js LTS and Remotion on the Windows PC (one-time, free): assumed acceptable unless the creator objects.
- Q5 Which of the five candidate topics (`docs/PUBLISHING_AND_ANALYTICS.md`) is video 1 after the prototype: decided
  after the prototype passes.

## Creator approval gates
1. Strategy, identity and Kit's look (after the Phase 2 pack). 2. The prototype's acceptance criteria and its human
review (Phase 6). 3. Each script and claim map before storyboard/render spend (per video, "approval #1"). 4. Each final
package before any upload (per video, "approval #2"). Nothing is published automatically.
