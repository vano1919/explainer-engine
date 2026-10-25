---
name: narration-script
description: Write or fix the spoken narration of a Crossworld Theories video so the AI narrator (ElevenLabs v4; the voice is chosen per episode in `production_script.json`, D-43) sounds curious, intriguing and lightly funny instead of slow, monotone and documentary. Use for every new script, every rewrite of a beat, and whenever a read comes back flat, slow, with stress or question intonation on the wrong word, or with no conversational colour.
---

# Narration script: write for the ear, then for the voice

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role script` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Crossworld Theories is entertainment first, real facts second (SCRIPTING_SPEC §8.1): a witty historian telling an
unbelievable true story over a campfire. The voice reads exactly what is written, so **the script is the
performance**. Every rule below fixes a defect the creator heard in a real read (2026-10-16) or a pattern measured in
successful videos. Facts never change to serve the read: every factual sentence still maps to its claim.

Files per episode beat: `narration_tts.txt` (what the voice gets: tags, capitals, interjections) and `narration.txt`
(the same words without tags and stress capitals: captions, claim map, `words.json` alignment;
`audio/scribe_words.strip_tags`). Run `python -m explainer_engine.scripting.narration_lint narration_tts.txt` before
any paid read: 0 FAIL, every REVIEW either fixed or answered in one line.

## What the creator heard wrong in the first reads

1. **The hook question did not sound like a question.** "What happens if you drop... into the STONE AGE?" is a
   wh-question; in English those *fall* at the end. Only yes/no questions rise.
2. **Stress on the wrong words** and a flat melody: nothing told the voice which word carries the surprise.
3. **Slow**: ellipses everywhere (each one is a held pause) and long sentences: 140 words a minute.
4. **No pull to the next beat**: sections ended on a closed fact, so nothing made the viewer wait for what came next.
5. **No conversational colour**: no "hmm", "oh", "well", no reactions; it sounded recited, like a documentary.

## What successful narrators do (vidIQ transcripts, 2026-10-16)

| Video (views) | Pattern worth copying |
|---|---|
| Bernard Films, "Could a Modern Scientist Survive in The Stone Age?" (8.5 M, 1 min) | yes/no hook question; "Day one." "Day three." as beat markers; one action per sentence; ironic aside ("The tribe watches you collect useless stones all day."); a twist character (Socrates) and an open ending ("And now they all have questions.") |
| Quantummysteries, "A Scientist Appears in the Stone Age" (2.4 M, outlier 417x) | short present-tense sentences; a reversal line after every win ("The laughter stops."); fragments for speed ("Shaman uses mud. Useless.") |
| What If (Underknown), "What If You Lived in the Stone Age?" | spoken openers ("Alright, grab your bone flute and gather around the fire."); question then answer with "Well," ("Why is this still a mystery? Well, that's because..."); one-line reactions ("Yeah, good luck with that."); ends on a tease for another episode |
| Bright Side, "What If You Had to Live a Day in the Stone Age" (2.5 M) | constant direct address; interjections at real moments ("Oh, finally there's an ember, good job!", "Oh no! It got away."); a question every few sentences ("Need a fork? Way too early for that thing.") |

Common to all four: short sentences, a question every 20-30 seconds (an observation; the checked floor is N-06, BP-17), a reaction after each reveal, and the
end of every section pointing at the next problem. None of them sounds like a lecture.

## The rules (N-01..N-14 are checked by `narration_lint`; the numbers live in the sourced rules at the end)

### Questions
- **N-01 The first spoken sentence is the hook, in one of the four forms of BP-03**: a question, a cold-open incident
  line, a claim with a number, or a preview of what the viewer will see; never a greeting, the channel name, "today we
  look at" or "subscribe" (FAIL). When the hook is a question, make it a yes/no question so the pitch rises: "Could the
  greatest minds in history survive the Stone Age?", not "What happens if...". A wh-question is allowed later, short,
  and usually answered at once ("Why? Well...").
- **N-11 The 30-second contract (BP-04)**: inside the opening words the script confirms the title's promise and opens
  one named gap (a question or a "but/until" turn); the central answer waits until the last tenth. **BP-05**: no pure
  background sentence (a date, a definition, a biography line) before that gap sentence; context comes after the tension.
- **The stressed word of a question goes last**, right before the "?", so the rise lands on it: "...survive the Stone
  AGE?" rather than "...SURVIVE the Stone Age?" when the age is the surprise. One capital at most (N-04).
- **N-10 No ellipsis inside a question**, and no wh-question over BP-18's word cap (12): both flatten the contour.
- **Answer a question with a reaction word first**: "Two hands go up. Two! Out of a hundred." / "Who takes charge?
  Oh, you already know who."
- **N-06 At least one question per 150 words** (BP-17; about one a minute at BP-01's pace); a rhetorical question is the cheapest
  way to wake a listener up.

### Stress and melody
- **N-04 One capitalised word per sentence, on the word that carries the surprise** ("That's the ONLY magic.",
  "It's KEEPING it."). Never two; never on a function word; never on a name just because it is a name.
- Put the important word at the **end of the sentence** (English stresses the end): "Fire was not the problem.
  Keeping it was." is stronger than "Keeping it was the real problem."
- **Contrast pairs carry melody**: "Not freezing. Damp." / "The hard part isn't making it. It's keeping it."

### Tone of the what-if episodes (creator 2026-10-16)
- Scientific what-if: mostly drama and curious telling with honest doubt, humour in small doses (SR-07); the density and
  placement of the jokes follow BP-09 (at most one verbal joke per 60 s, the first inside 45 s, beside the fact). Ground the story in what is established, but never hedge the story itself ("we can only reason", "we cannot know for sure", "this is hypothetical" are SC-11 FAILs, BP-88): the narrator tells it as if it is happening now, and doubt lives in the heroes. Show, don't tell (SC-12, BP-87): never name a hero's trait, rating or biography; narrate what they do. Each period ends on the question that opens the next (SR-03).

### Pace
- **N-03 At most one ellipsis per beat** (BP-16: two is a REVIEW, more a FAIL). Each `...` is a held pause; use it only before the one reveal of that beat.
  For speed use full stops, dashes and fragments. The ellipsis is the emphasis rule of BP-10: emphasis comes from the
  text (one stressed word, one ellipsis, a tag), never from a held silence, and never a pause before a punch line.
- **N-05 Sentence length follows BP-06** (a REVIEW cap, a FAIL cap and a median for the ear). Fragments are allowed and
  fast ("A convex lens. The afternoon sun. One bright point on the grass."); one idea per sentence.
- **N-12 Contractions always** ("what's", "isn't", "they're"): they speed the read and sound like talk; never the -'ve
  forms (BP-07: the ear hears "would of"). Active voice, subject first, present tense where it is true, and "you" to
  one listener regularly (BP-07).
- **N-13 Numbers for the ear (BP-08)**: one numeral per sentence, rounded unless the exact figure is the point, and
  every number that matters is also shown on screen (ED-10).
- **N-14 No press-release lines (BP-15)**: never "comes out on", "is now available", "launches on", "according to the
  official", "as reported by"; the fact lives in the claim map, the line in the story; sources are never spoken.
- Target pace for this channel: the heard pace of **BP-01** (the first read was 140; the v3 test 168; D-49: engagement
  rises with pace and recall peaks near the top of the band).

### Open loops
- **N-02 Every beat ends on an open loop**: the next question, danger or promise, never a closed fact. Patterns:
  "But a rule won't keep anyone warm." / "And the sun is already sinking." / "Then the wind changes." /
  "Which raises a problem nobody saw coming." / last beat: tease the next episode ("And tomorrow? Tomorrow they need a
  pot.").
- **Pay every loop off** within the next one or two beats; a loop that never pays off feels like a trick.
- Open a smaller loop at the start of a long beat ("Here's the strange part.") so the middle does not sag.

### Conversational colour (interjections and reactions)
- **N-07 Use interjections, but where they would really be said**: a reaction to a reveal ("Hmm."), surprise ("Oh."),
  a turn ("Well,"), moving on ("Right."), trouble ahead ("Uh-oh."), a realisation ("Ah."). About one per 60 words,
  never two in a row, never inside a factual sentence (N-08: they open a sentence or stand alone).
- Pair them with the matching tag when the sound matters: `[chuckles]`, `[sighs]`, `[gasps]`, `[clears throat]`.
- Reactions as short lines are often better than sounds: "Yeah. Good luck with that." / "Somebody write that down."
- Humour comes from the situation (geniuses as confused tourists), dry understatement after a big moment, and the
  characters' reactions; never from a false fact (SCRIPTING_SPEC §8.1).

### Audio tags (ElevenLabs v4)
- **N-09 Tags describe how the line is spoken**, never stage directions (`[standing]`, `[music]` are not performed).
  Known delivery tags: `[curious]`, `[excited]`, `[mischievously]`, `[dramatically]`, `[sarcastic]`, `[warmly]`,
  `[cautiously]`, `[whispers]`, `[softly]`, `[surprised]`, `[nervous]`, `[deadpan]`, `[pause]`, `[short pause]`,
  plus sounds `[chuckles]`, `[laughs softly]`, `[sighs]`, `[gasps]`, `[exhales]`.
- A tag holds until the next one: place one where the delivery changes (about one per 2-3 sentences), not on every
  sentence. Match tags to the episode's cast voice (EL-01, `cast.<id>.voice.traits`): a playful voice takes
  `[mischievously]`, `[sarcastic]`, `[dramatically]` well, a calm one does not.
- v4 has no speed or stability control through the connector; pace comes from the text.

### Named heroes and friction (D-40, UR-21)
- Name the real people. The narration says "Franklin", "Newton", "Nansen", never "one of the scientists"; the pictures show
  them (skill `shot-visuals`). Anonymous "someone" is for crowds only.
- Give each hero a line that sounds like their archetype (`look.archetypes`): Newton objects, Einstein improvises, Franklin
  organises, Nansen says what survival actually takes. Humour is their reaction to the situation, never a false fact.
- Say what is at stake in each beat in plain words (cold, no fire, bad water, hunger, dusk): the picture will show it, so the
  line must give it a reason.

### Cuts and timing (the edit depends on it)
- Every place the picture should change needs a written mark (full stop, comma, dash, question mark) (UR-12).
  ElevenLabs reads commas and dashes in 0.05-0.1 s, so `audio/pause_pad.py` widens punctuated gaps to 0.26 s after
  the read; never rely on a comma alone for a cut in the first 30 s.
- A long sentence with no marks (more than about 4 s) leaves the first 30 s with no legal shot layout (UR-02):
  split it.

## Voice direction lives in the production script (D-43)
Write each segment's lines in `production_script.json` (`docs/PRODUCTION_SCRIPT.md`), not in loose text files: per line the text, the
tags where delivery changes, the one capitalised `emphasis` word, `tone`, `emotion` and `pause_after`; `compile` derives `narration.txt`
and `narration_tts.txt`. The narrator is described in `voice.style` in words only (soft, deep, calm, warm, mature, quietly emotional);
never "like <a real person>": no imitation, no cloning (PV-10). The creator picks the voice from `voice.candidates` after a short test
read; with a soft deep voice, carry emotion with short lines, a held `pause_after`, `[softly]`, `[whispers]`, `[sighs]`, not with volume.

## Procedure

1. Write the beat plainly, facts first (claim ids next to each factual sentence in the working notes).
2. Rewrite for the ear: the hook in one of the four BP-03 forms (a yes/no question rises best); the gap opened inside
   the 30-second contract (BP-04) with no context before it (BP-05); short sentences; contractions; one stressed
   capital per sentence; one question per minute; an open loop at the end of every beat; interjections where a person
   would say them; the first laugh early and beside the fact (BP-09).
3. Add tags at delivery changes only; write `narration_tts.txt`; derive `narration.txt` (no tags, normal case).
4. `narration_lint` → 0 FAIL; fix or answer every REVIEW.
5. Read it aloud at the BP-01 pace; anything you stumble on, cut.
6. **Paid test read of the first 45-60 s only** (estimate first, log it); the creator listens; then the full read.
7. After the read: Scribe → `scribe_words` → `pause_pad` → `build_shots` (0 FAIL) → the creator listens again.

## Sources

ElevenLabs, "Prompting Eleven v3/v4" (capitalisation increases emphasis; ellipses add pauses and weight; dashes give
short pauses; tags describe delivery; text structure strongly influences v4): https://elevenlabs.io/docs/best-practices/prompting ·
Intonation of questions: yes/no questions rise, wh-questions fall (Hedberg et al., CLA 2010,
https://cla-acl.artsci.utoronto.ca/pdfs/actes-2010/CLA2010_Hedberg_et_al.pdf; https://pronuncian.com/yes-no-question-intonation) ·
Open loops and pattern interrupts in YouTube scripts: https://joyspace.ai/open-loop-technique-force-viewers-watch-end,
https://www.overseeros.com/blog/youtube-storytelling-techniques-6-ways-keep-viewers-watching-longer ·
vidIQ transcripts read 2026-10-16: aeKrIhktzqU, BTNUK1SCoo4, vS5BmHsuvvk, agRKo_sEb4I (patterns only; no text copied
into our scripts).

## Sourced rules (docs/SOURCED_RULES.md)

The numbers that bind this skill live only in the registry (`explainer_engine/standards/sourced_rules.json`);
`narration_lint` reads them from there (N-01, N-03, N-05, N-06, N-07, N-10..N-15). A number changes there, with its sources,
never here.

- BP-03: the first spoken sentence is the hook in one of four forms: a question, a cold-open line of at most 14 words, a claim
  with a number, or a preview of what the viewer will see; never a greeting, the channel name, "today we look at" or
  "subscribe" (N-01, FAIL).
- BP-04: within the first 85 words the script confirms the title's promise and opens one named gap (a question or a
  but/until turn); the central answer is held back until the last tenth (N-11).
- BP-05: no pure background sentence (a date, a definition, a biography line) inside the first 85 words before the gap sentence.
- BP-06: sentences at most 20 words (REVIEW) and never over 25 (FAIL); the median at most 12; fragments allowed (N-05).
- BP-07: contractions, never would've / could've / should've / might've / must've; passive sentences at most 10 %; "you" or
  "your" at least once per 100 words; present tense where it is true (N-12).
- BP-08: at most one numeral per sentence, rounded unless the exact figure is the point; every number that matters is also
  shown on screen (N-13).
- BP-09: humour sits beside the fact, never inside the example that explains it; the first laugh inside the first 45 s; at
  most one verbal joke per 60 s.
- BP-10: no pause before a punch line; emphasis from the text (one stressed word, an ellipsis, a tag), never a hold over
  its limit (N-04; N-15 checks each narration line's `pause_after`; a dialogue scene's scripted silence is a scene device;
  the last line before a change of place or time may breathe within BP-10's boundary band, D-65, the creator 2026-10-20 21:14/21:17).
- Reported speech (D-65, the creator 2026-10-20 21:14/21:17): the speaker's name before his words ("Musk says ...", BP-95), at most two speakers
  reported in one line (BP-96). The narrator need not repeat what is on screen; the listener must follow the story.
- BP-16: at most one ellipsis per beat; two is a REVIEW, more than two a FAIL (N-03).
- BP-17: at least one question per 150 words (N-06) and about one interjection per 60 words, at least one (N-07).
- BP-18: no ellipsis inside a question, and a wh-question of at most 12 words (N-10).
- BP-15: no press-release lines ("comes out on", "is coming out on", "will be released on", "is scheduled for release",
  "releases on", "is now available", "available now", "launches on", "launching on", "officially announced", "according to
  the official", "the company announced", "press release", "as reported by", "launches worldwide"): the fact lives in the claim map, the line in
  the story; sources are cited in the claim map and the description, never spoken (N-14, FAIL). The same lexicon also holds
  the announcement-register patterns of SC-07 ("X's page says", "announced", "release date", "launches worldwide"),
  checked on narrator lines only: a hero may name a date inside a scene.

## One narrator tells the dialogue (D-68, creator 2026-10-21)

In a narrated episode nobody speaks in a voice of their own: the narrator performs every character's words. The creator
wants them "not monotone, the way he would say it". Rules, each with its sources, in
`/mnt/project-files/explainer-engine/titans_from_zero/qa_loop/research_narrated_dialogue.md`:

1. Name the speaker before the quote ("Musk says, ...", or an action beat: "Musk grips the wheel. ..."): a listener
   cannot look back. A tag after the quote is fine only when the speaker is already plain.
2. Paraphrase the setup; quote only the strongest words, short ("Forty dollars. Ten percent. Forever.").
3. Tell characters apart by attitude, never pitch or accent; never imitate a real living person's voice.
4. Write the attitude into the words first; a v4 tag before the quote only sharpens it, and its colour carries
   forward, so go back to the narrator's own tone after the quote (the line's `tone` names each turn).
5. Keep one attitude per character for the whole video, and at most two speakers in one told exchange.

Story cards (`design/cards.py`): the intro asks the episode's question over the heroes' heads; a recap names where each
hero stands, then one NEXT line that opens the coming chapter (a hook, never a summary of the end).
