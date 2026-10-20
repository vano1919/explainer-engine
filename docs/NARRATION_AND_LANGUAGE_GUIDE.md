# Narration and language guide

Voice route and parameters: P-50 to P-56 in [VIDEO_PARAMETER_SPEC](VIDEO_PARAMETER_SPEC.md); TTS decision D-12.

## The voice we want
A knowledgeable person explaining something interesting to a friend: warm, clear, confident without shouting, a little
dry. More conversational than a documentary, less hyped than a trailer. Language: American-neutral English. The voice is
chosen by a blind listening test (Phase 5) on a realistic passage that includes questions, numbers, technical terms, a
joke and a long explanatory sentence, not on a showcase sentence. ElevenLabs library voices only (D-39; no cloning, ever).

## How the script should read
- Contractions, active voice, direct address ("you"), concrete analogies, one idea per sentence.
- Define a technical term the first time it appears, in plain words, then use it consistently (one name per thing).
- Numbers: the script writes the spoken form ("one point two billion"), never raw digits (P-55). Units spoken out.
- Questions: at most one rhetorical question per section; a question is asked only if the next sentence answers it.
- Humour: set up in one sentence, pause (0.9 s), deliver flat; no explaining the joke.
- Transitions are varied and specific ("That's the cell. Now zoom in on what's inside it."); never the same connector
  twice in a row.

## Review flags (a detector flags; a human decides; nothing is rewritten automatically)
Generic openers and closers ("have you ever wondered", "in today's video", "let's dive in", "so there you have it");
overused devices ("imagine", "here's the thing", "but here's the twist", "buckle up"); empty intensifiers and unsupported
superlatives ("mind-blowing", "insane", "incredible", "the most important ever", "you won't believe"); more than two
rhetorical questions in a section; repeated sentence openings (three in a row); sentences over the caps of BP-06; stacked
clauses; a closing recap that restates the video; a begging call to action; keyword stuffing; phrases that appear in
a known competitor's script (checked by the creator's reference notes, never by copying). The detector reuses the
negation-aware approach of the TMR lexicons (copied in Phase 6, [PROVENANCE](PROVENANCE.md)) so "never insane" is not
flagged like "insane".

## Pronunciation and delivery
`speakable()` (copied in Phase 5) expands acronyms, numbers and years; project pronunciations live in a JSON file that
wins over defaults. After rendering, an ASR word-error check (optional faster-whisper) flags misread terms for a human
ear. Delivery is lively (the heard pace of BP-01, short pauses) rather than TMR's calm presets; the numbers are
P-52/P-53 and are verified by measurement on the finished read.

## Failure and fallback
If the chosen voice mispronounces a term the pronunciation file cannot fix, change the wording. If the chosen voice fails the
listening test, propose a paid voice with its cost and a monthly line item for approval; a cloud TTS is never adopted
silently. Voice consistency: one voice per channel, set once in the channel profile.
