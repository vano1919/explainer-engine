# Overlay for `v-hook-writing`: The cold open of a long docudrama (layer L4, stage 2)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from TheCraigHewitt/skills `youtube/hook-writing` (MIT, commit `fdbf39b61f`), written for creator-led talking-head
videos. Rewritten for a narrated history docudrama under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)).
Upstream text is this folder's `SKILL.md`. The checked rules are ours: N-01, N-11 and BP-03..BP-05 in skill
`narration-script`, checked by `scripting/narration_lint.py`. Short-form hooks: skill `v-viral-hooks`.

## What the first 30 seconds must do

The viewer clicked a title and a thumbnail. The opening's job is not to win the click again; it is to give a reason to
watch to the end. For a history docudrama that means four things, in about the first 85 spoken words (BP-04):

1. **Keep the title's promise at once.** If the title says "The Night the War Stopped", the first image and line are that
   night, not 1914 Europe in general.
2. **Show the strangest true moment.** Lead with the detail nobody expects (an unarmed man walking toward machine guns,
   singing), in present tense.
3. **Open one named gap**: the yes/no question the episode answers at the end (ST-01), or a "but" that makes the moment
   impossible ("But in the morning, the orders are to shoot.").
4. **Promise the kind of payoff**: the viewer should sense whether this ends in a twist, a cost, or a reveal, without being
   told the answer.

No throat-clearing: no greeting, no channel name, no "today we look at", no "subscribe" (N-01 FAIL), no branded intro, no
background before the gap (BP-05: a date, a definition or a biography comes after the tension).

## The three-step cold open, docudrama version

Upstream's lean-in, interjection and snapback become:

| Step | Seconds (estimate at BP-01's pace) | Our version | Example |
|---|---|---|---|
| 1 Moment | about 0-8 | the striking true moment, concrete, present tense | "Christmas Eve, 1914. A German soldier climbs out of his trench. No rifle. He's singing." |
| 2 Turn | about 8-18 | why it should be impossible: the danger, the rule, the cost | "Fifty yards away, two hundred British rifles are pointed at him." |
| 3 Question and promise | about 18-30 | the yes/no question and the promise of the episode | "Will anyone fire? What happens next is something both armies will spend years trying to forget." |

The question is yes/no so the voice rises (skill `narration-script`); the stressed word goes last.

## Hook forms that fit our episodes (BP-03's four forms)

| Form | Docudrama use | Example shape |
|---|---|---|
| Cold-open incident | the default: the moment itself | "[Date]. [A named person] does [an impossible thing]." |
| Question | when the premise is a puzzle | "Could [a group] really [stop / survive / win] [the impossible]?" |
| Claim with a number | when a number carries the shock | "One night in 1914, [number] men stopped fighting. Nobody ordered it." |
| Preview | when the viewer must see the payoff to believe it | "By morning, they'll be playing football in no man's land." |

Pick by the episode's best moment, not by habit; vary across episodes.

## Picture, words and on-screen text in step

Upstream's "one hook, three channels" holds, with our tools:
- **Picture** (skill `v-director-cinematic`): the opening shots are the strongest of the episode, usually a reenactment of
  the moment plus one evocative insert; never a map, never a title card, never a slow establishing landscape.
- **Words**: the narrator's cold open; a hero's one line may land as step 2 or 3 if it is the record's strongest sentence.
- **On-screen text**: date and place as a small period-styled chip ("24 December 1914, Flanders"); at most a few words; no
  text that repeats the narration word for word.
- **Sound**: the scene's bed starts with the first frame, with one effect that belongs to the moment (a footstep in frost, a
  rifle bolt); music, if any, enters on the question.

## Re-hooks through the middle

Every chapter turn re-opens a gap: a new danger, a revelation, a question ("But one officer is already writing a report.").
Our cadence rules are N-02 (every beat ends open) and ST-13 (a turn every BP-76 gap); upstream's "every 2-3 minutes" is
looser than ours and is not used. Mid-video re-hook lines must be specific ("Here is the part the official history left
out.") and must pay off within a beat or two.

## Things that kill the first minute

- Starting with context (the war's causes, the year's politics) before the moment.
- A map or a montage as the first image.
- A hook that promises more than the episode gives (the satisfaction drop hurts more than the click helps).
- A wh-question hook that falls flat in the read.
- Two questions in the first 30 seconds; the viewer holds one.
- Narration that describes what the picture already shows.

## Process

1. From the approved story variant, name the one moment the episode is built to reach and the strangest true detail.
2. Draft three cold opens in different forms; label each with its form.
3. For each: the shots (picture), the words, the date chip, the first sound.
4. Estimate the time at BP-01's pace; the gap must be open inside BP-04's word count.
5. Run `python -m explainer_engine.scripting.narration_lint` on the drafts; keep the one with 0 FAIL that reads best aloud.
6. The test read (first 45-60 s, paid, estimated and approved first) is the real check: the creator listens.

Not used from upstream: the channel-context file `.agents/youtube-context.md`, sponsor placement, creator-to-camera
advice, screen-recording visuals, and the "re-hook every 2-3 minutes" number.
