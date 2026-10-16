# Scripting specification: research, claims, script, rubric

Every video starts with research on its central question and ends its writing stage at the creator's approval #1.
Drafting is done in Claude Code sessions (D-13): an LLM may assist but cannot establish factual truth by assertion.

## 1. Research dossier (per episode)
Fields: slug, working title, central question, audience and knowledge level, viewer promise, pillar, format, sources
(S-id, URL, title, publisher, publication date, access date, type, grade), passages (exact quote or close paraphrase with
location), claims (C-id), contradictions and uncertainty notes, "do not use" list, sensitive-topic flag.
Source grade A primary (paper, standard, inquiry report, filing), B authoritative secondary (textbook, institution,
established reference), C secondary (journalism, trade press), D unverified (never alone). An important claim needs one
grade-A or two independent grade-B/C sources. Distinguish fact, estimate, interpretation, allegation, speculation.
Political, historical, financial, health and legal topics get a second read and stricter wording; contested
interpretations are not stated as settled; nothing reads as personal financial advice.

## 2. Claim record (C-id)
`id, text (as narrated), type, sources [S-id], source passage, confidence (verified | corroborated | single-source |
unverified), uncertainty wording, used_in [script sentence ids], reviewer, status`. Rule: no script sentence with a
factual content survives without a claim; no claim is "verified" without a recorded passage.

## 3. Required script contents
The narration is written for the edit: the question by 5 s (UR-01), a comma or full stop wherever a cut must fall
(UR-12), see [UNIVERSAL_RULE_BASE](UNIVERSAL_RULE_BASE.md).
Working title, audience, promise, central question; hook spec; outline; full narration with sentence ids and section
boundaries; payoff and conclusion; visual notes; on-screen text; SFX/transition cues; claim references; uncertainty notes;
source list; disclosure notes; Shorts candidates; packaging direction.

## 4. Format structures (one per approved format; not a single formula)
| Format (D-25) | Beats |
|---|---|
| you_in_era | the drop-in (you wake up in year X) -> first problem (food, money, work, danger) -> how people really solved it (sourced) -> the surprising part -> how long you would last, with the evidence and its limits |
| past_meets_present | a person or object from era X arrives today -> what they recognise -> what baffles them -> the real history behind each reaction -> what today still owes to their time |
| era_meets_era | two eras side by side -> the dimension that matters (tools, food, money, medicine) -> sourced differences -> where the comparison breaks down; conflicts shown without gore |
| world_what_if | the premise (dinosaurs never died out) -> the science that bounds it -> step-by-step consequences -> where the model stops being reliable (amber) |
| how_it_worked | a familiar need (heat, light, cleaning, counting) -> how era X met it -> the mechanism -> what changed and why |
| money_across_eras | a price or wage in era X -> what it bought (primary sources) -> why a direct conversion is uncertain (ranges, amber) -> what it tells us about life then |
| myth_vs_record | the claim as people say it -> where it comes from -> what the record shows -> why it persists -> an honest "still unclear" |
Each section has a role (setup, context, mechanism, escalation, example, payoff); jokes sit where they relieve, not
interrupt, an explanation; no fixed cut rate; a revisit of the promise before the end. Fact density is flagged when a
section carries more than about five new claims per minute (REVIEW, topic-dependent).

## 5. Script rubric (anchored 1-5; each criterion scored with an evidence note)
| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Factual reliability | unsupported claims | claims mapped, a few single-source | every claim verified, uncertainty worded |
| Clarity | needs prior knowledge, undefined terms | mostly clear | a newcomer follows without pausing |
| Story coherence | sections could be reordered | logical but flat | each beat sets up the next |
| Hook | greeting or vague promise | clear premise by 20 s | concrete puzzle by ~10 s |
| Relevance | trivia | interesting, little use | changes how the viewer sees a familiar thing |
| Originality | restates a common page | some new framing | a distinct angle, own analogy |
| Spoken naturalness | reads like an article | readable aloud | sounds like a person |
| Visual potential | talking points | some visual ideas | every beat has a visible action |
| Humour fit | forced or absent | present, neutral | arises from the material |
| Pacing potential | uniform density | some variation | tension and rest alternate |
| Source coverage | key points unsourced | most sourced | all sourced, contradictions noted |
| Title/thumbnail alignment | promise not paid | promise paid late | promise paid early and fully |
| Shorts potential | no standalone idea | one idea | two or three distinct ideas |

**Gates.** Factual reliability, source coverage and title alignment must each be >= 4; no other criterion below 3; mean
>= 3.8. A critical factual gap, weak story logic or a misleading promise stops the pipeline (NEEDS_REVIEW) before any
storyboard, TTS or render spend. Scores are the reviewer's, with notes, not a model's assertion.

## 6. Shorts selection
Per long-form: (a) adapt a strong section, (b) script a separate Short from the same verified research, or (c) use a
related standalone angle, chosen by creative and production value. A Short stands alone (independent hook, arc, payoff,
no need for the long video), is re-storyboarded for 9:16, and carries its own claims. No forced loop, runtime, caption on
every word, or number of Shorts.

## 7. Crossover episodes (two worlds meeting; D-26)
Procedure: the `crossover-episode` skill (`.claude/skills/crossover-episode/SKILL.md`). Rules that every crossover
script meets, on top of sections 1-6:
- **Fan research first.** A validated fan brief (`research/fan_brief.py`, P-124) exists before any premise is chosen:
  the fans' theories, what they ask for, the existing crossovers and their angles, each world's canon rules.
- **Original premise.** At least 12 candidates scored on surprise, fan payoff, casual clarity, visual drama, honesty
  and rights safety; the premise must not repeat an existing take (P-125). Systems, small people and second-order
  effects beat the default army battle.
- **Balance.** Every beat is tagged casual, fan or both; at least 30 % serve each audience (P-123). Casual viewers get
  on-ramps inside the story; fans get credited theories, canon details and deep cuts.
- **Analysis, not retelling.** The scenario is reasoned from canon rules, with speculation labelled and the best
  counter-argument answered (RR-01, RR-06); recap and quotes stay inside P-120 and P-122.
- **No templates.** Stock phrases (`fan_brief.TEMPLATE_PHRASES`) are flagged and removed unless they are truly the best
  words; "who would win" is never the frame.
- **Rights check passes** (`rights/ip_check.py`) before approval #1.

## 8. Writing for an expressive narrator (ElevenLabs, D-39)
The narrator reads the text as written, so the text carries the performance. Rules for the narration file:
- **Punctuation is the pacing.** `...` holds a pause before a reveal ("Both of them... are unsure."); `—` is a
  sudden turn ("And night — is coming."); commas make the voice breathe in long sentences; a full stop ends a beat.
  These marks are also the edit's cut points (UR-12), so a pause the picture needs must be written into the text.
- **Emotion lives in the sentences, not in labels.** Mystery: a question, then a short withheld answer. Suspense:
  short sentences, one fact each, the danger last. Triumph: a longer sentence that rises to the result. Humour: a flat
  understatement after a big moment. Each beat's emotion matches its shot's emotion (UR-14).
- **No stage directions in the displayed script.** Audio tags (`[whispers]`, `[curious]`) are allowed only in a
  separate `narration_tts.txt` and are removed before alignment; the captions and `words.json` use the plain text.
- **Write what must be heard.** Numbers and years as words when the reading matters ("twelve thousand years ago"),
  names spelled the way they are said; check unusual names in the first sample.
- **Light edits only.** Rewriting for the read changes rhythm and punctuation, never a fact: every factual sentence
  still maps to its claim (section 2).

### 8.1 Tone: entertainment first, facts second (creator, 2026-10-16; narrator Clyde, D-39)
The narrator is a witty historian telling an unbelievable true story over a campfire: curious, mysterious,
conversational. Never a dry documentary, never a comedy sketch.
- **Humour comes from the situation and the characters' reactions**, in small doses: dry understatement, an ironic
  aside, a flat line after a big moment (brilliant scientists as confused tourists). About one light touch per beat,
  never two in a row, none at moments of real danger or in the fire-making physics.
- **The facts stay serious.** A joke never changes, softens or invents a fact, a number or a mechanism; the science,
  physics and survival constraints are told straight. A joke that needs a false statement is cut.
- **Written for the shot, not only the ear.** A joke adds words, and every shot has a duration range (UR-11): after
  adding a line, re-check the beat's length against its shot before the read is paid for.
- **Checked by ear.** The creator judges whether it is funny and whether it stays credible; a model's opinion of its
  own humour is not evidence.
