# Overlay for `v-viral-youtube-shorts`: Shorts-feed craft (layer L28, stage S19, after G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from vyralcontent/content-skills, page `viral-youtube-shorts` (MIT, commit `349e495d97`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) as the feed knowledge behind our Shorts procedure, which lives
in skill `shorts-for-video`. The upstream text is this folder's `SKILL.md`; its `references/` and `assets/`
stay readable as background, and every number in them is a hypothesis until it reaches the BP registry.

## How this page and skill `shorts-for-video` split the work

- `shorts-for-video` owns the procedure: the `shorts` block, the 9:16 crop around the named heroes, reuse of the main
  read, the set of styles, the rules SH-01..SH-05 and SS-01..SS-09, the renderer and the checks.
- This page owns the feed reasoning: why the first frame matters, where a Short loses people, why it should loop, and how
  to read what YouTube shows afterwards. It never overrides a channel rule; where upstream disagrees with a BP number, the
  registry wins and the gap is noted for the research pass.
- Hooks as words: skill `v-viral-hooks`. The long video's opening: skill `v-hook-writing`.

## What the feed rewards (as we apply it)

1. **Each Short stands alone.** The Shorts feed ranks a Short on its own behaviour, not on the channel. So every Short of
   a set needs its own question and its own scene (SH-05); a Short that needs the episode to make sense fails in the feed.
2. **The first frame is the thumbnail.** Most Shorts views start in the feed, so the hook's key words are on screen from
   frame 0 and the first cut lands inside the hook line (SS-07); the hook is spoken from the first second (BP-11).
3. **Viewed versus swiped away is the opening's grade; the retention curve is the middle's.** A cliff in the first
   seconds is the hook; a slope after it is the middle. Our first Shorts held the opening and lost the middle, which is why
   the visual-beat layer and the event floor exist (SS-08, SS-09, BP-45).
4. **A loop is retention you do not have to earn twice.** When the last line runs into the first (SS-04 `loop`), a replay
   reads as one continuous watch. Design the last beat and the first frame together.
5. **The bridge to the long video is the point.** A Short exists to advertise the episode (SH-01): the ending points to
   the full story or loops, never begs for a subscribe or signs off (BP-44). The related-video link and the pinned comment
   are set by hand at upload (SS-03).
6. **Engaged views, not raw views.** Read the right number in Studio; a view counts on any start or loop.
7. **Patterns, not promises.** Say what tends to work and why; never predict that a Short will break out.

## Choosing the moment from our episode

- A visible reversal, a decision under pressure, or a fact that sounds wrong but is sourced: the moment must be clear
  without context and true (SH-04: the opener maps to a claim).
- Prefer reenactment moments where a hero speaks or acts (route `video`, D-131): faces and bodies hold the feed better
  than a map. A map moment works only when the motion itself is the surprise (a front collapsing in seconds).
- The heroes must fit a 9:16 window: if two speakers stand at opposite edges of the 16:9 frame, choose a moment with one,
  or cut between them.
- Reuse the main read and the clips' own lines: the Short adds only its hook and pointer lines (one shared pointer line is
  the only new voice cost when cutting from the master).

## Diagnosis after posting (read the curve, then edit)

| Studio shows | Likely cause | Change in the next Short |
|---|---|---|
| Many swipes in the first seconds | the hook is slow, abstract or starts on a still | a question on frame 0, a cut inside the hook, a face first |
| A steady slide in the middle | too few changes on screen, a long held frame | more events per 10 s (BP-45), an insert or a reaction |
| A drop right before the end | the answer came too early | keep the answer for the last stretch (BP-44) |
| Percentage viewed well under full on a loop design | the seam shows | match the last line and frame to the opening |
| Views but no long-video clicks | no pointer, or the link not set | the pointer line plus the related-video link (SS-03) |

The mapping of a curve onto segment ids belongs to the packaging checklist (CRAFT-PKG-03, CRAFT-PKG-04 in
`shorts-for-video`).

## Anti-patterns that demote a Short

A 16:9 file with bars (it is not a Short; `python -m explainer_engine.qa.short_format` catches it), captions or faces under
the feed's UI (BP-29 safe zone), a logo or welcome intro, a subscribe plea, a watermark from another platform, licensed
music (our music is ElevenLabs or a verified free library, library first, OR-18), third-party footage of any kind, and a set
that repeats one scene or one style twice in a row (SS-02, PV-28).

## Hard rules that bite here

- Every Short is English for the US audience, 9:16 in the BP-167 frame, within YouTube's length limit (BP-137).
- Nothing goes public; staging is unlisted after its own tests, the owner clicks public (invariant 4).
- Monetisation tactics never change a script; the story decides.

## References: when to open which

| File | Open when |
|---|---|
| `references/shorts-retention.md` | reading a curve, drop-off shapes, loop design |
| `references/shorts-algorithm.md` | why a Short is judged alone, the seeding window |
| `references/shorts-to-longform-funnel.md` | pointer line, pinned comment, related-video link |
| `references/shorts-anti-patterns.md` | the full demotion list with reasons |
| `references/shorts-search-and-shelf.md` | what is indexed (title, description, transcript, on-screen text) |
| `references/shorts-monetization.md` | only when the owner asks about Shorts revenue |
| `assets/shorts-vvsa-checklist.md` | a quick pass over a drafted Short |
| `assets/shorts-to-longform-bridge.md` | drafting the pointer and pinned comment |
| `assets/shorts-script-template.md` | background only; our template is the `shorts` block |

## Not used from upstream

The brief-gathering interview (our brief is the finished episode), the length sweet spot as a rule (our bands are
BP-12's), trending sounds, monetisation tuning by music choice, the channel-trailer audit, and every mention of the
upstream vendor's product.
