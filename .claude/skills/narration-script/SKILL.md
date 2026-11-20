---
name: narration-script
description: Write or fix the narrator of a docudrama history episode - the voice that carries about 70 % of the words, writes to the picture instead of describing it, opens on a hook in the first sentence, holds the question open, moves fast for the ear, and hands each scene over to the heroes. Use for every new script, every rewrite of a beat, and whenever an ElevenLabs read comes back flat, slow, lecturing, or stressed on the wrong word.
---

# Narration: the docudrama voice-over (layer L4, stage 2 and 3)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Hook craft comes from the
vendored `v-hook-writing` and `v-viral-hooks` (both rewritten for our long-form use); the delivery comes from
`elevenlabs-voice`. This page owns the N rules (N-01..N-17, checked by `scripting/narration_lint.py`), the register rules
(`scripting/register_lint.py`, RG), and the sourced numbers (BP ids in [SOURCED_RULES](../../../docs/SOURCED_RULES.md));
a number changes in the registry with its sources, never here.

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role script` and follow it; legal, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never in this skill.

## What the narrator is for in a docudrama

The voice-over is the spine that the reenactments, the living photographs and the maps hang on. It carries time, place,
numbers, the record and the stakes; the heroes carry the moments. Three consequences:

1. **Write to the picture, not about it.** The viewer already sees the candle on the parapet; the narrator says what the
   picture cannot: "It is the first light anyone has shown on this line in nine weeks." Describing what is on screen is
   double exposition (KP-20, ST-21) and the fastest way to sound like a slideshow.
2. **Hand over, do not compete.** The narrator sets up a scene on its pressure and comes back on its consequence; it never
   restates the scene's turn and never quotes a hero inside it (skill `dialogue-scenes`).
3. **The script is the performance.** ElevenLabs reads exactly what is written, so stress, speed and colour are written
   into the words (one stressed word, short sentences, punctuation, a few tags), never hoped for.

The tone: a gripping storyteller who knows the record, telling it as if it is happening now, in present tense where true.
Entertainment first, facts never bent (SCRIPTING_SPEC section 8.1): every factual sentence maps to its claim, and doubt
lives in the heroes, never in hedges on the story (SC-11, BP-88).

## The opening (first 30 seconds)

Load `v-hook-writing` (the cold-open hook for a long video) and `v-viral-hooks` (archetypes and critique) to draft three
hooks, then pick by our rules:
- **N-01**: the first spoken sentence is the hook in one of BP-03's four forms (a question, a cold-open incident line, a
  claim with a number, a preview of what the viewer will see); never a greeting, the channel name, "today we look at" or
  "subscribe" (FAIL). A question hook is yes/no so the pitch rises ("Could two armies stop a war for one night?"); a
  wh-question falls in English and sounds like a statement.
- **N-11**: inside BP-04's opening words the script confirms the title's promise and opens one named gap; the central answer
  waits until the last tenth. **BP-05**: no pure background sentence (a date, a definition, a biography) before the gap.
- The docudrama cold open is usually **the strangest true moment, in present tense, in one or two short sentences**, then the
  question: "Christmas Eve, 1914. A German soldier climbs out of his trench. He is unarmed. He is singing."

## The middle: keep the question open

- **N-02**: every beat ends on an open loop (the next danger, question or promise), never a closed fact; pay each loop
  within the next beat or two (ST-05). Open a smaller loop at the start of a long beat ("Here is the strange part.").
- **N-06**: a question at least every BP-17 words; a wh-question short and answered at once ("Why? Because...").
- **Joins**: so, but, then the problem; never "and then" (ST-02, ST-20).
- **Numbers for the ear (N-13, BP-08)**: one numeral per sentence, rounded unless the exact figure is the point, and every
  number that matters is also on screen (ED-10).
- **No press-release lines (N-14, BP-15)**; sources are never spoken, they live in the claim map and the description.

## Sentences for the ear

- **N-05**: sentence length within BP-06 (a REVIEW cap, a FAIL cap, a median for the ear); fragments are fast and allowed.
- **N-12**: contractions always, never the -'ve forms (BP-07: the ear hears "would of"); active voice; "you" to one listener
  where the format allows it.
- **N-04**: one capitalised word per sentence, on the word that carries the surprise, never on a function word; put that
  word at the end of the sentence, where English stresses it: "The order was not to fire. They didn't NEED one."
- **N-03**: at most one ellipsis per beat (BP-16); each is a held pause, used before the one reveal.
- **N-10**: no ellipsis inside a question, and a wh-question within BP-18's cap.
- **The twist lands short**: the sentence that turns the story fits BP-115's estimate (`scripting/syllables.py`); a long twist
  becomes two sentences with the turn in the second.
- **Pace**: the heard pace of BP-01; engagement rises with pace (D-49). Pace comes from the text, not from settings.

## Conversational colour, docudrama-sized

- **N-07**: interjections where a person would really say them, about BP-17's rate, never two in a row, never inside a
  factual sentence (N-08). A docudrama narrator uses fewer than a comedy narrator: "Well," "Then," "Still," a dry one-line
  reaction ("Nobody fires.").
- Humour comes from the situation and from understatement after a big moment (BP-09: beside the fact, the first early,
  never more than one verbal joke per BP-09 interval); never from a false fact, never at the expense of the dead.

## Audio tags (ElevenLabs v4)

- **N-09**: tags describe how the line is spoken (`[softly]`, `[curious]`, `[dramatically]`, `[whispers]`, `[sighs]`,
  `[short pause]`), never stage directions (`[standing]`, `[music]`).
- A tag holds until the next one: place one where the delivery changes (about one per two or three sentences). Match tags
  to the cast voice's traits (EL-01); a calm, deep voice carries emotion with short lines and `[softly]`, not volume.
- No SSML on v4 (BP-14). Edit marks (`[DELAY: +Ns]`, `[OVERLAP: ..]`, `[CUT: ..]`) go on the speaker label, left of the colon;
  the TTS builder strips them.

## Cuts and timing

Every place the picture should change needs a written mark (full stop, comma, dash, question mark; UR-12).
`audio/pause_pad.py` widens punctuated gaps after the read; never rely on a comma alone for a cut in the first 30 seconds.
A long sentence with no marks leaves the opening with no legal shot layout (UR-02): split it.

## Files and procedure

Lines live in `production_script.json` (D-43, [PRODUCTION_SCRIPT](../../../docs/PRODUCTION_SCRIPT.md)): per line the text,
tags where delivery changes, the one `emphasis` word, `tone`, `emotion`, `pause_after`; `compile` derives `narration.txt`
(no tags, normal case: captions, claim map, word alignment via `audio/scribe_words.strip_tags`) and `narration_tts.txt`
(what the voice gets). The narrator is described in `voice.style` in words only, never "like <a real person>" (PV-10).

1. Write the beat plainly, facts first, claim ids beside every factual sentence.
2. Rewrite for the ear: hook form, the gap inside the 30-second contract, short sentences, contractions, one stressed word,
   a question on the cadence, an open loop at the end of every beat.
3. Write to the picture: strike every sentence that describes what the shot already shows.
4. Add tags only at delivery changes.
5. `python -m explainer_engine.scripting.narration_lint narration_tts.txt` and `python -m explainer_engine.scripting.register_lint <script>`:
   0 FAIL, every REVIEW fixed or answered in one line.
6. Read it aloud at BP-01's pace; cut whatever you stumble on.
7. A paid test read of the first 45-60 s only, estimated and logged first; the creator listens; then the full read.
8. After the read: Scribe word timings, `pause_pad`, the clock (`episode/timing.py`), and the creator listens again.

## One narrator tells the dialogue (D-68)

In a narrated real-person episode the narrator performs every quoted word: name the speaker before the quote ("Haig
writes, ..."), paraphrase the setup and quote only the strongest words, tell characters apart by attitude never by pitch
or accent, write the attitude into the words first, and return to the narrator's own tone after the quote. Full-cast
episodes give each hero a fixed voice instead (D-90).

## AI register: write like a person (N-16, N-17)

**N-16** (BP-140, FAIL): no tier-1 AI-register word and no sentence-initial Additionally, Moreover or Furthermore in
anything the viewer hears or reads. **N-17** (BP-114, REVIEW): little soft register, few structural tells (stacked triplets,
"It's not X. It's Y." pivots, participial tails, em-dash chains, "rather than" chains; RG-02..RG-04). The lists live only in
the registry; the lint reads them. A literal use is allowed through `register_allow.json` beside the script, with a reason
(RG-05). Fix by saying the thing: "the general stares at the map", not "delves into"; the alliances by name, not "a
tapestry of alliances".

### CHECKLIST (screenwriting)

Rendered from `explainer_engine/standards/craft_checklists/screenwriting.json` (the one home of these ids; 
`python -m explainer_engine.standards.craft write` regenerates it, `tests/unit/test_craft_checklists.py` fails when they
differ). Every row is a hypothesis until a second source type is verified ([CRAFT_CURRICULUM](../../../docs/CRAFT_CURRICULUM.md)).

<!-- craft-checklist:screenwriting:begin -->
| ID | check | rule | artefact field | sourced rules | enforced by |
|---|---|---|---|---|---|
| CRAFT-SCR-01 | code | no AI-register word over the density limit (delve, tapestry, testament to, ...) | production_script narration[].text and hero lines | BP-114, BP-140 | `explainer_engine/scripting/register_lint.py` |
| CRAFT-SCR-02 | critic | no structural AI tells: stacked triplets, sentence-initial 'Imagine', a rhetorical-question opener in every segment, em-dash chains, 'not just X but Y' | narration[].text | BP-114 | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-SCR-03 | code | the twist sentence lands inside its estimated spoken length | segment twist sentence + syllable estimate | BP-115 | `explainer_engine/scripting/syllables.py` (planned, P3) |
| CRAFT-SCR-04 | code | causal chain: THEREFORE / BUT joins, no AND-THEN chain | story beats | ST-02 | `explainer_engine/scripting/story_lint.py` |
| CRAFT-SCR-05 | code | show, don't tell and full immersion (no trait statements, no meta disclaimers) | narration and hero lines | BP-87, BP-88 | `explainer_engine/scripting/scene_lint.py` |
| CRAFT-SCR-06 | critic | no double exposition: the narration never describes what the picture already shows | narration line vs its shot card | KP-20 | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-SCR-07 | code | sentences for the ear and spoken register | narration[].text | BP-06, BP-07 | `explainer_engine/scripting/narration_lint.py` |
<!-- craft-checklist:screenwriting:end -->

## Sourced rules (docs/SOURCED_RULES.md)

The numbers behind this page live only in `explainer_engine/standards/sourced_rules.json`, and `narration_lint` reads them
from there: BP-01 (pace), BP-03 (hook forms), BP-04 and BP-05 (the 30-second contract), BP-06 (sentence length), BP-07
(contractions, voice, "you"), BP-08 (numbers), BP-09 (humour), BP-10 (holds), BP-14 (no SSML), BP-15 (press-release
lexicon), BP-16 (ellipses), BP-17 (questions and interjections), BP-18 (questions), BP-95 and BP-96 (reported speech),
BP-105 (narrator share), BP-114 and BP-140 (AI register), BP-115 (the twist sentence).


## Speech registers (DW-11, creator 2026-11-07): few-shot for the writer
Rule: every speaking hero has one `speech` card (register, sentence length, habits, `avoid`). It decides the written words AND the delivery tags. Test every line: if another hero could say it unchanged, rewrite it. Put these pairs in the writer prompt; the pairs are style demonstrations, not lines to reuse.

Same idea ("I will not help you"), five heroes:
- Narrator (dry, short): "Nobody in the camp argues. The old man has already decided."
- Rustic elder (no contractions, concrete images, repeats a word, inverted order): "Help you, I will not. The river does not carry a stone uphill, and neither do I."
- City wiseguy (contractions, slang, jokes as armour, trails off): "Yeah, no. I'm not, uh... look, you guys are gonna have to do this one yourselves."
- Child (tiny words, literal, asks): "You don't want to? But why? Is it because of the dark?"
- Noble (long courteous sentences, titles, formal verbs): "I regret, sir, that my honour permits me no part in this, however much it grieves me to refuse."

Bad (all heroes sound alike, and sound like a model): "I understand your request, but I must respectfully decline, as it would not be right." Fails RG register and DW-11.
Delivery follows the card: elder = slow, rough, long pauses; wiseguy = fast, breathy, cracks under stress; child = high, curious; noble = measured, clear consonants. No disclaimers, no stepping outside the story (SC-11).

### Six revision rules learned from the stone-age pilot (creator 2026-11-07, v4.1 -> v4.2)
1. **No disguised "not X, but Y"** ("He didn't capture him. He called him here."): write the physical action. **Never spoil a later reveal** in the setup narration; plant only the visual mystery (an empty space on the wall).
2. **No anachronistic nouns** in a period hero's mouth (a stone-age shaman does not say "city"): use the hero's own images. **Never echo a character's line in narration**; the narrator adds a concrete fact or a scale jump instead.
3. **A visual noun the viewer cannot place yet is clarified in the same line** ("sticky little fingers on the screen", not "fingers on glass"). **No stock similes** ("like water in a desert"): use a concrete number. **An overlap must answer what was just said**: the interrupter reacts to the other hero's words, not to a whisper at a phone.
4. **Show the realisation, do not state the moral**: let a hero notice the object that carries it. A big-city hero speaks in whole conditionals ("If you keep me here, all you get is..."), not telegraphese.
5. **Show the physical cause, not what characters think** ("A dead black glass. A fake god. The hunters raise their spears."), and tactile words instead of trailer lines ("Wet red clay. His palm beside Ura's.").
6. **No SSML on v3/v4 (BP-14).** Silences before a line are `[DELAY: +Ns]`, `[OVERLAP: ..]`, `[CUT: ..]` on the speaker label, left of the colon; the TTS builder strips them so the model never reads them aloud. Inside a line only `...` and the model's audio tags (`[sighs]`) are allowed. A cut-off line is written the same way everywhere (`--`). The narrator uses no em dash (creator 2026-11-07, v4.3, synced 12:20 UTC).

### Few-shot test pairs (run by tests/unit/test_speech_registers_fewshot.py)
GOOD (register lint must pass):
    He does the one thing he can. Phone light. On.
    Mountains of light I saw, in my sleep. Out of them, you walked.
    Okay. Sticks. I rub sticks. Nothing's happening!
    Is light inside the stone-thing? Can I eat it?
BAD (register lint must flag):
    Moreover, it is crucial to delve into the tapestry of this pivotal moment.


### Register boxes per speaker (hypotheses, REVIEW only)

These came from `docs/research/SPOKEN_STORYTELLING_RESEARCH_2026-11-07.md` and a 2026-11-07 audit; until a second source
type confirms them (D-59) they guide the writer and never fail a script.

| Speaker | Words per line | Contractions | Shape |
|---|---|---|---|
| Narrator, opening | short (hook zone) | allowed | noun, present verb, physical object |
| Narrator, middle | medium | allowed | two physical actions joined by and, so, while |
| Narrator, finale | short | allowed | staccato subject, verb, object |
| Officer, educated | medium to long | few | full conditionals, titles, measured |
| Private, city | short | many | dropped subjects, slang, interruptions with `--` |
| Farmer, rural | medium | some | concrete images, repeated words, inverted order |
| Child | very short | allowed | a literal physical question |

Mechanical traps: a noun the narrator just named is not repeated by the next speaker; no "X, but no Y" pivot (write two
positive actions); before a reveal the narrator describes only what is visible; a line before an overlap ends with `--` and
the interrupter answers it; edit marks on the label, never SSML; no em dash in a markdown title. Pre-render audit: cover the
names and identify the speaker; turn lengths differ clearly between a fast and a slow speaker; not every question is
answered at once; a reversal every few lines; every narrator sentence matches what moves on screen.

## Sources

ElevenLabs, "Prompting Eleven v3/v4" (capitals raise emphasis, ellipses add weight, dashes give short pauses, tags describe
delivery, text structure drives v4): https://elevenlabs.io/docs/best-practices/prompting. Intonation of questions: yes/no
questions rise, wh-questions fall (Hedberg et al., CLA 2010,
https://cla-acl.artsci.utoronto.ca/pdfs/actes-2010/CLA2010_Hedberg_et_al.pdf). Open loops in YouTube scripts:
https://joyspace.ai/open-loop-technique-force-viewers-watch-end. AI-style word drift: arXiv 2404.01268, 2406.07016 (the
abstract pages prove the drift, not our list). Writing to picture and avoiding double exposition: our KP-20 and ST-21 with
the critic's CRAFT-SCR-06.
