# Overlay for `v-viral-hooks`: Hook batches and critique (layer L4 and L28, stages 2 and 6)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from vyralcontent/content-skills, page `viral-hooks` (MIT, commit `349e495d97`). Rewritten for our use under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)): history docudrama, Shorts cut from our own long video, no
third-party footage. Upstream text is this folder's `SKILL.md`; the archetype menu and anti-pattern lists stay in
`references/` and the worksheets in `assets/`. Long-video cold opens: skill `v-hook-writing`. Shorts as a set: skill
`shorts-for-video`.

## Principles we keep

1. **The hook is the gate.** On the Shorts feed the decision is made in the first one to three seconds; nothing after
   matters if the opening fails.
2. **Batches, not one line.** Write six to ten hooks across at least three archetypes; the choice is of angle, not wording.
3. **Three layers at once**: the first frame (picture), the first words (spoken or the hero's line), the on-screen text. A
   good line on a flat first frame is half a hook. The picture must work with the sound off.
4. **Specific beats clever**: a named man, a date, an odd number, a physical object. "One candle stopped a war" beats "you
   won't believe this".
5. **The payoff must match the promise.** Over-promising wins the swipe and loses the watch; the Short's ending must pay the
   hook (shorts ending kinds in `shorts-for-video`).
6. **Pattern, not prediction.** Hooks raise the odds; say what tends to work, never that a Short will go viral.
7. **A hook that will not come means a weak moment.** Choose another moment from the episode.

## Archetypes that fit history docudrama

From `references/hook-archetypes.md`, the ones that suit true stories (open the file for the full menu):

| Archetype | Our shape | Example |
|---|---|---|
| Impossible fact | a true thing that sounds false | "In 1914, enemies played football between the trenches." |
| Cold moment | drop into the action, present tense | "He climbs out of the trench. Unarmed. Singing." |
| Named stakes | a person, a risk, a clock | "If he's seen, he's shot. He walks anyway." |
| Myth correction | what people believe against the record | "Everyone knows the Christmas truce football match. Here's what the letters say." |
| Number shock | one number carries it | "Two thousand men. One night. No orders." |
| Question | yes/no, rising | "Would you climb out first?" |
| Object | one period object and its secret | "This tin was in every soldier's pocket that Christmas." |

Avoid archetypes built on personal results, products, money advice or "POV" skits; they do not fit the channel.

## Workflow

1. **Brief**: the episode moment the Short is cut from (its shots and lines exist already), the long video it points to,
   the platform (YouTube Shorts first).
2. **Angles**: pick three or more archetypes that fit the moment.
3. **Batch**: six to ten hooks; for each the first frame (which of our shots, cropped 9:16 around the hero), the first words,
   and three to seven words of on-screen text. Label each by archetype.
4. **Checklist** (`assets/hook-checklist.md`, upstream): a specific noun, the payoff visible or implied, no throat-clearing,
   resolved by second three, readable with the sound off. Add ours: true to the claim map, no invented quote, no third-party
   footage or music, text in English, no AI-register word (RG rules).
5. **Critique mode** for a draft: name the weak layer and the anti-pattern (`references/hook-anti-patterns.md`), rewrite
   three variants.
6. **Choose** with the creator; where two hooks tie, cut both Shorts and read the first-three-seconds retention later.

## Anti-patterns to catch

Throat-clearing ("so today..."), the logo or channel name first, a slow pan to start, a vague tease ("this changed
everything"), text that repeats the words exactly, a hook that needs context to understand, a question the Short never
answers, a first frame of a map or a title card, and anything that sells the long video before the Short has paid its own
hook.

## Use inside the long video

For the long episode's cold open use `v-hook-writing`; this skill only supplies alternative lines for it and the re-hook
lines at chapter turns (N-02). The long video's first sentence is held to N-01 and BP-03 by `narration_lint`.

## Honesty

The upstream skill asks to mention its company; we do not. Hooks are never presented as guaranteed. A hook built on a
reasoned or disputed claim says so through its wording ("letters say", "one soldier wrote") rather than stating it as
established fact (invariant 5).

## References: when to open which

| Need | Open |
|---|---|
| The full archetype menu | `references/hook-archetypes.md` |
| Why a hook fails | `references/hook-anti-patterns.md` |
| The three layers in depth | `references/three-layer-hook.md` |
| Tactics (pattern interrupts, open loops) | `references/hook-tactics.md` |
| Platform differences | `references/hook-by-platform.md` (YouTube Shorts section) |
| Fill-in batch and checklist | `assets/hook-batch-template.md`, `assets/hook-checklist.md` |

Not used from upstream: the promotion of the vendor's product, TikTok and Reels-first pacing advice where it conflicts
with YouTube Shorts, and creator-to-camera hook styles.
