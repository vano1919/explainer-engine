# Script engine v2: action shown, the cold open, AI acting (research, 2026-10-24)

**What this is.** ვანო (2026-10-24, after the first Napoleon package) asked three things: why the picture prompts were not
visible next to the script, whether the episode needs more action, and how to control the AI's acting, which he called
the script's critical vulnerability (the 91 s parley turns into "a podcast" if the faces fail). He forwarded another
model's review of the package to read, not to follow wholesale. This file keeps what was checked and the evidence behind
KP-41..KP-43 ([SHOT_PROMPTS.md](../SHOT_PROMPTS.md)) and BP-111..BP-113 ([SOURCED_RULES.md](../SOURCED_RULES.md)).

## 1. The review, checked against the cards

| Point of the review | Checked on the v1 cards | Taken |
|---|---|---|
| The first real clash comes at 3:13 | true: S06 (the arrows) started at 3:14; 0:00-0:30 was a drum, a reveal and narration | yes: three 2 s teasers cut from S10's own clips at 0:03-0:09 (KP-41) |
| S06 needs its cost shown | half true: spent French horses and fresh Mongol remounts were already on screen | one shot added: the riders form again out of range after the gun |
| 5:03-8:19 is the weakest stretch: plans told, not shown | true: the yurt was 95 s in one place with 9 lines in a row | cutaways while the plan is told: the scouts count the wagons, the French column pulls away from its wagons, riders slip out at night; in S09 a scout watches the guns being hidden and riders walk a dry gully (KP-42) |
| S10: two parallel lines, front and camp | true: the camp appeared only as smoke at the end | the camp line cross-cut with the battle: the drummer hears hooves, the guards' ragged volley, the torches right after Napoleon's "That is how Europe learned", the drummer drumming the alarm |
| Keep the envoy, the council, the parley; no third battle | agreed | kept; no battle added |
| The parley should show the asymmetry: guns, no food | partly there in words ("the men are eating grass") | the cutaway shows it (Brun chewing grass in the ash), and the price is paid on screen (two guns dragged off) |
| Judge action by action, reaction, consequence | agreed | written into [SCRIPT_ENGINE.md](../SCRIPT_ENGINE.md) section 4 |

The review's "more strategy shown through action, not more battle" is the rule KP-42 encodes.

## 2. Sources

- **Cold open.** Wikipedia, "Cold open": a teaser sequence jumps into the story before the titles; late-1950s dramas
  "opened with an attention-grabbing scene from the middle of the episode, which would repeat when the story arrived at
  that point" (https://en.wikipedia.org/wiki/Cold_open). Our teasers are exactly that: pieces of later shots, which
  also costs nothing (the clip is rendered once and cut twice).
- **Cross-cutting.** Wikipedia, "Cross-cutting": establishes action at the same time; "suspense may be added by
  cross-cutting" (https://en.wikipedia.org/wiki/Cross-cutting). How To Film School: parallel action "withholds
  resolution while increasing pressure", the audience links events "even before the characters do"
  (https://howtofilmschool.com/dictionary/parallel-action-cross-cutting/). That is the camp line of S10: the viewer
  sees the torches while Napoleon smiles.
- **The 90 s in one place** (BP-112) is the same ceiling as the narration block (BP-104) and the story-engine skill's
  "a scene every 60-90 s"; a hypothesis, REVIEW only.
- **Four lines in a row** (BP-113) is the creator's call on the acting risk turned into a number by us; house, REVIEW
  only, to be measured on the 1-minute film's acting takes.
- Not found: a source that measures how long a plan may be told before it is shown (the heist-writing article found
  speaks of complications, not intercutting:
  https://www.creativescreenwriting.com/cswcms/scene-stealers-writing-the-perfect-heist-part-2/).

## 3. AI acting: what the engine now does

1. **Fewer lines rest on a face.** No more than four spoken lines in a row; silent reactions (light tier, cheaper) and
   cutaways sit between them (KP-43). Two lines of the yurt became silent acted beats.
2. **Each acted line is checked.** `compose` puts `qa: ["acting"]` on every full-tier line in a medium shot or closer,
   with what to check: the line (lips move on it and only on it), the action's peak (the gesture is visible), the face
   when the card gives one. The video QA of PR #22 runs it; a take is redrawn only when it fails (the creator's rule).
3. **A fallback that hides the mouth.** After a second failure the shot becomes an over-the-shoulder from behind the
   speaker onto the listener (the line plays on the reaction), or the speaker's hands for a line said to the room.
4. **Not yet known**: how often LTX-2.5 passes the acting check on our style. The 1-minute film measures it; the parley
   of this episode is the first candidate to test, as a paid step with the creator's approval.

## 4. Where the new approach met older rules (ვანო 2026-10-24: the new approach wins)

| Older rule | Conflict with | Resolution (D-77) |
|---|---|---|
| BP-40: at most 10 pictures a minute; ED-14's image budget | BP-107: 11-17 shots a minute, measured on the creator's cartoons | BP-40 scoped to still-picture episodes; animated episodes use BP-107 (the 5 s rule of the first 30 s still holds) |
| BP-43: the last sentence points to one next video | BP-106 / KP-40: the outro names the worlds on the channel and coming | BP-106 replaces the "one next video" part under the engine; BP-43's sign-off lexicon still FAILs |
| Skill `dialogue-scenes`: ~40-60 % narration, a played scene every 60-90 s | BP-105 (25-45 %), template D's 2-4 minute scenes, BP-112 | the skill now points to BP-105, BP-112 and BP-113 |
| Style bible: one place per scene | KP-42 cutaways | one home place per scene, cutaways allowed and expected |
| Template D row 1: hook 0:00-0:03 | KP-41 teasers in the first 10 s | the hook runs 0:00-0:12 with 2-3 teasers; rows 8, 10, 13 name the cutaways and the silent beats |
| D-55: expression sheets because the face changes about once a second | LTX acting from the hero sheet, KP-43 | D-55 stays for still-picture episodes |
| BP-70: a real exchange has at least 4 unbroken lines | BP-113: at most 4 lines in a row | no conflict: the cap equals the minimum, said in both statements |

Checked and not in conflict: BP-31 (cutaways are hard cuts), BP-03 (the first sentence is still the hook: a claim with
a number, 14 words), ED-14's listener reaction every 2nd-4th line (KP-43 is the same idea in code), the critic's 40 %
stills (already replaced by BP-109 in v1).
