---
name: video-editing-architect
description: Foundational guide, technique database and decision framework for audio-video editing - genre-to-style mapping, cut types, transitions, typography, B-roll, vocal chain, ducking levels, SFX pairing, patterns and anti-patterns, chapters and a pre-render QA checklist. Use before planning any cut, mix, caption or Short, and whenever a video feels flat, jumpy, noisy or over-edited.
---

# Video Editing Architect

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role edit` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

File requested as `video-editing-architect.md`; stored as `SKILL.md` so the skill loader finds it. Project-specific, binding rules
stay in `docs/EDITING.md` (ED-xx) and `docs/UNIVERSAL_RULE_BASE.md` (UR-xx); the `editing-style` skill is the Crossworld Theories
application of this page. **Where the two disagree, the project rules win.**

Numbers below are working defaults used by working editors and platform guidance, not laws. `[ours]` marks a value measured or fixed in
this project. Every value can be moved by evidence; when you move one, say why in `docs/PROGRESS.md`.

## How to decide (the framework)

1. **Name the genre** (section 1). The genre fixes pacing, sound density and how much editing is allowed.
2. **Name the job of each beat**: hook, explain, prove, reveal, rest. A beat has one job and one dominant change on screen.
3. **Choose the lightest tool that does the job**: hard cut before dissolve, dissolve before graphic transition, nothing before anything.
4. **Check against anti-patterns** (section 4) and the QA list (section 6) before rendering.
5. **Look and listen** (frames either side of three cuts, the loudest three joins) and write what you saw and heard.

---

## 1. Genre-to-style map

| Genre | Pacing (shot length) | Visual dynamics | Audio and sound design |
|---|---|---|---|
| **Talking head / educational / tech review** | 2-6 s on the face, a change (zoom, cut, B-roll, graphic) every 3-5 s; 12-25 cuts a minute is normal; jump cuts remove every breath and stumble | alternate 100% and 108-112% punch-ins on cuts, never a zoom drifting for more than 3 s; B-roll covers claims and product shots (2-4 s); lower thirds once at 0:02-0:08 for 4 s; key words highlighted (one colour) | voice first; music bed -26 to -22 dB under voice, -14 to -10 dB in gaps; short pops/whooshes only on graphics and product reveals; dense, crisp |
| **Faceless / voiceover / educational and sleep** (Night Owl Library style) | educational: 4-9 s a picture, 6-10 pictures a minute `[ours: <=10]`; sleep: 12-30 s a picture, no cut inside a sentence | slow push 100% to 105-108% over the whole shot (one direction), dissolve 1.5-3 s, dark low-contrast grade, no on-screen text except the title and chapter cards; sleep: nothing flashes, no sudden brightness | voice -20 to -16 LUFS short-term (sleep: lower and steady, 3-4 dB dynamic range), ambience bed (rain, room tone, fire) -34 to -28 dB, music optional and slow; no riser, no boom, no sting; SFX only if soft and rare |
| **Documentary / video essay / storytelling** | 4-10 s average, longer holds (10-20 s) for weight, faster (2-4 s) in montage; cut on the narration's pauses | Ken Burns push/pull on stills, match cuts between ideas, archive-style grade with constant grain/vignette, maps and timelines as motion graphics, lower thirds for names | layered but quiet: voice dominant, ambience -30 dB, music -24 to -20 dB ducked 6-9 dB under voice, J-cuts/L-cuts for scene changes, a deliberate silence (1-3 s) before a reveal |
| **Dynamic vlogs / action / off-road** | 1-3 s in action, 3-6 s in calm; cut on motion, 25-40 cuts a minute at peaks | speed ramps, whip pans, shake-cut-on-impact, POV and chase angles alternate, minimal text (speed, place) | engine/wind natural sound is the base, music -18 to -12 dB with a strong beat, hits on cuts: whoosh on whips, low boom on impact, riser 1-3 s before a jump |
| **Short-form (Shorts / Reels / TikTok)** | hook in 0-3 s, a visual change every 1-2.5 s, 20-45 s total (house up to 60, P-11; YouTube counts up to 3 minutes as a Short, V-25) | 9:16, subject in the centre 60% (the caption and UI zones cover the top 10% and bottom 20%), captions 2-4 words at a time, 6-8% zoom punches on key words | voice -14 LUFS integrated, music -22 to -18 dB, pop on every caption pulse, whoosh on every cut that moves, one sting max at the payoff; loopable last frame |
| **Ambient / relaxing / ASMR** | 20-60 s per scene or a single long take; transitions 3-6 s or none | almost still: slow drift under 3% a minute, no zoom punches, no text, soft fades only | no voice or a whisper at -28 to -24 LUFS; texture is the content; no sudden sound ever, peaks below -12 dBFS, noise floor clean (no hiss under -60 dB), loop seams crossfaded 4-8 s |

---

## 2. Visual techniques

### 2.1 Cut types

| Cut | What it is | Use when | Avoid when |
|---|---|---|---|
| **Jump cut** | same framing, a slice of time removed | talking head: remove breaths, stumbles, dead air; keeps energy | docu, ambient, sleep; a long take with a visible subject (the viewer sees the position jump) |
| **Dynamic zoom (punch-in)** | scale 100% to 108% or 112% on a cut, or a 0.3-0.6 s eased push | emphasis on a key word; hides a jump cut; adds rhythm to a static shot | more than one in 3 s; zooms that restart from 100% on the same picture (continue or ease out, ED-02) |
| **J-cut** | next scene's audio starts 0.3-1.0 s before its picture | scene change, reveals, to pull the viewer forward | when the sound would spoil a surprise |
| **L-cut** | previous audio continues 0.3-1.0 s over the new picture | reactions, showing what is being described | when the old sound no longer fits the new picture |
| **Cut on action** | cut during a movement, 2-4 frames after it begins | continuity of motion (a hand reaching, a door opening); invisible cut | static shots |
| **Match cut** | the next shot repeats shape, position or motion of the last | idea-to-idea links, time jumps (a fire becomes a sun) | when the pictures have different framing scale (it reads as a mistake) |
| **Smash cut** | abrupt cut from quiet to loud or calm to chaos, with sound jump | comedy, shock, "one second later" | any sleep/ambient piece; after more than one per 2 minutes |
| **Invisible cut** | cut hidden by a movement, whip, dark frame or object passing the lens | stitching takes, fake long takes | no motion to hide it |

Cut on the pause, not on the word `[ours: UR-12]`; leave 80-120 ms of room each side so no syllable is clipped. In narrated work the cut sits
0.0-0.15 s before the first word of the line it illustrates.

### 2.2 Transitions

| Transition | Parameters | Meaning | Use |
|---|---|---|---|
| **Hard cut** | 0 frames | same time, same place | default, 85-95% of all transitions |
| **Dissolve** | 12-24 frames (0.4-0.8 s) action; 1-2 s time jump `[ours: 1.0 s at period starts]`; 3-6 s ambient | time passes, mood shifts | at most 10% of transitions `[ours: UR-14]`; never across a spoken sentence |
| **Dip to black/white** | 0.5-1.5 s in, hold 0.2 s, out | chapter end, shock, silence | start and end of a piece `[ours: 1 s in, 1.5 s out]` |
| **Whip pan** | 6-10 frames of blur, matched by a whoosh | energy, place change in action | vlogs, shorts, tech reviews; never in docu/sleep |
| **Mask transition** | an object (door, hand, tree) wipes the frame 10-20 frames | clever place/time link | when a real foreground object exists; otherwise it looks fake |
| **Push / zoom transition** | 8-14 frames, 1.15x to 1.3x scale with blur | continues the zoom language across a cut | shorts, tutorials |
| **Match move** | next shot starts with the same motion direction and speed | smooth link between different pictures | the zoom/pan of the outgoing shot ends at the speed the next one starts |

Rule of three: at most three transition kinds in one video `[ours: cut, dissolve, black]`.

### 2.3 Typography and motion graphics

- **Lower third**: 4 s on screen, in at 0:02-0:08 of the first appearance, safe margin 5% from edges, sans-serif, 2 lines max.
- **Key highlights**: one accent colour for one word per sentence; 100-150 ms scale pop (100% to 108% to 100%); never highlight more than 3 words in 5 s.
- **Dynamic captions**: 1-4 words at a time (shorts), 2 lines x 38 characters (long form); on screen from 0.1 s before the word to 0.2 s after; reading speed 15-17 characters a second.
- **Kinetic text**: only when the words are the picture (a quote, a number, a rule); ease 6-10 frames in, hold at least 1.2 s, ease out 4-6 frames.
- **Contrast**: text luminance contrast of at least 4.5:1 against what is behind it; use drop shadow (offset 2-4 px, blur 6-12 px, 60-70% black) or a blurred box (30-50% black, 12-24 px blur, 8-12 px radius). Test on the brightest frame under the text.
- **Mobile size**: caption cap height at least 4% of frame height (about 43 px on 1080 tall); body text never below 36 px at 1080p.

### 2.3b Data visuals and period cards

- A period or chapter card: 3-4 s, big title (cap height 8-12% of the frame), one short line under it, a progress strip; the previous
  sentence's sound rings 0.3-0.5 s into the card; a soft whoosh or low tone, never a boom in calm genres.
- Charts/counters: build 0.6-1.0 s with a pop, hold 3-7 s, at most 6 marks, label height at least 4% of the frame, one idea each,
  numbers from a sourced list only. A counter that adds up a calculation on screen ("100 x 2,500 = 250,000") convinces more than a
  finished chart: let the viewer watch the sum happen.

### 2.4 B-roll and visual fillers

- Choose B-roll by **meaning, not decoration**: it must show the noun or the action in the sentence being said, within 0.3 s of the word.
- Length 2-5 s; start a B-roll shot on a movement or a clear subject, not an empty frame; never reuse a clip within 60 s.
- Overlays (grain, dust, light leak): one constant layer at 4-10% opacity across the video; switching them on and off draws attention to them.
- Screen balance: one focus per frame (rule of thirds, 40-60% of the frame is empty or quiet), leave caption zones free, keep faces out of the bottom 20% in vertical.
- Fillers for pauses: hold, then a very slow push (under 3% a second); never an unrelated clip.

---

## 3. Audio techniques

### 3.1 Vocal chain (in this order)

1. **Noise reduction**: 6-12 dB of broadband reduction at most; more makes the voice watery. Room tone from the take is kept at -55 to -60 dB under the words.
2. **EQ**: high-pass 80 Hz (female 100 Hz), cut 200-300 Hz by 2-3 dB if boxy, presence boost +2-3 dB at 3-5 kHz, air shelf +1-2 dB above 10 kHz only on clean voices.
3. **Compressor**: ratio 2:1 to 3:1, attack 10-30 ms, release 80-150 ms, 3-6 dB gain reduction on peaks; target 6-9 dB loudness range for spoken explainers, 3-4 dB for sleep.
4. **De-esser**: band 5-8 kHz, 3-6 dB of reduction on sibilants only.
5. **Limiter**: true peak ceiling **-1 dBTP** (shorts: -1.5 dBTP, because platform transcoding adds overshoot).
6. **Loudness**: integrated **-14 LUFS** for YouTube and shorts, -16 LUFS for podcast-style, -20 to -23 LUFS for sleep/ambient; short-term never above -9 LUFS.

**Chunk matching (project rule `ED-01`)**: before joining separately generated clips, bring each to the same gated loudness (spread under 1.5 dB) and fade the edges 20-30 ms inside the silence; Episode 1 chunks spread 5.6 dB before this and the joins were audible.

### 3.2 Ducking levels (voice vs music vs bed)

| Content | Voice | Music under voice | Music in gaps | Bed/ambience |
|---|---|---|---|---|
| Talking head | -16 LUFS reference | -26 to -22 dB below voice peaks | up to -14 dB | -35 dB or none |
| Documentary / essay | -16 | 18-24 dB under voice (duck 6-9 dB) | -16 | -30 |
| Faceless educational | -16 to -14 | 20-26 dB under | -18 | -32 |
| Sleep / ambient | -22 | 25 dB under, one track at a time | no gap swell | -34 to -28 |
| Vlog / action | -14, natural sound present | -18 | -10 | natural -20 |
| Shorts | -14 | -22 to -18 | -14 | -28 |

Ducking parameters: threshold at the voice level, reduction 6-9 dB, attack 20-30 ms, hold 80 ms, release 250-400 ms `[ours: music dips 9 dB, bed 4 dB under world sounds, 1 ms control grid]`.
**One music at a time** (a handover is a crossfade of at most 3 s); a tick/clock loop counts as music and sits at least 6 dB lower `[ours: ED-03, PV-29]`. At most two background layers plus the voice.

### 3.3 SFX and visual pairing

| Sound | Pairs with | Level (vs voice peaks) | Length |
|---|---|---|---|
| Pop / click | text and caption appearing, icon pops | -18 to -14 dB | 40-120 ms |
| Whoosh / swoosh | fast movement, whip, push transitions | -16 to -12 dB | 200-600 ms, peak on the middle of the move |
| Paper rip / texture | graphic or card change, sticker slap | -18 dB | 150-400 ms |
| Low boom / riser | dramatic or informational emphasis; riser ends exactly on the hit | boom -14 dB, riser -20 dB rising to -12 | boom 0.6-1.5 s, riser 1-3 s |
| Ambience / room tone | location, atmosphere, joining edits | -35 to -28 dB, constant | continuous, crossfade 1.5 s |

Rules: a sound starts with the picture event it belongs to (within one frame); SFX never sit on top of a spoken word, they use its gaps or dip the music; vary the sample for repeated events (three variants of a pop); never use the same whoosh twice in a row; leave 3-6 dB of headroom below the voice.

---

## 4. Patterns and anti-patterns

### Patterns (do)

- **Pattern interrupt every 3-7 s**: a cut, a punch-in, a new graphic, a sound, or a change of colour; in calmer genres 8-12 s.
- **Cold open / hook in the first 10-15 s**: the most surprising line or image first, a question or promise within 3 s, then the title; no logo sting, no "welcome back".
- **Audio lead-in**: the next sound begins 0.3-0.5 s before the picture (J-cut), so the cut feels motivated.
- **Pause and punch**: alternate dense and quiet beats; a 0.4-1.0 s silence before a key fact makes it land.
- **Hold the end of every period/chapter on a question** that the next one answers (open loop).
- **Consistency**: one grade, one grain, one type family, three transition kinds at most.

### Anti-patterns (do not)

| Anti-pattern | Why it hurts | Fix |
|---|---|---|
| Over-editing: an effect on every cut | viewer notices the editor, fatigue | effects only where a beat needs one; keep calm scenes calm |
| Jump cuts in ambient/docu | reads as a glitch in a continuous mood | dissolve or hold |
| Text or graphics appearing with no sound | feels dead | pop/click at the appearance, or deliberately silent |
| Music covering the voice; SFX painfully loud | viewers leave or mute | voice 14+ dB above music peaks `[ours: UR-32]`, SFX below voice |
| Two music tracks plus a tick plus a bed together | muddy mix | one music, tick 6 dB under, two layers max `[ours: ED-03]` |
| Zoom that snaps back to 100% on the same picture | looks like a rendering error | continue the move or ease out `[ours: ED-02]` |
| A cut in the middle of a zoom | jerk | rest at cuts `[ours: ED-08]` |
| Chunks of different loudness joined as they came | audible seam | level and fade `[ours: ED-01]` |
| Template 3D/glitch transitions on serious topics | cheapens the subject | cut or dissolve |
| Cutting inside a sentence on a half-word | clipped syllable | cut in the pause |
| Held picture with no change for over 9 s `[ours: UR-31]` | attention drops | bubble, re-frame or cut |

---

## 5. Chapters and structure

- **Architecture**: cold open (0:00-0:15) then the title/promise, chapters of 1-4 minutes each; a chapter starts at a clear change of topic or period and ends on its hook.
- **SEO and navigation**: YouTube requires the first chapter at 0:00, at least 3 chapters, each at least 10 s; titles of 2-6 words with the search keyword where it is natural ("Year 1: the first harvest"); chapters appear as a timeline on the player and in search results.
- **When not to give chapters**: when the title would spoil a reveal (use a neutral label), in sleep/ambient videos where seeking is not wanted, in Shorts, and when the chapters would be shorter than 30 s each.
- **Mapping to the cut**: place the chapter's first frame on a dissolve or a card, 0.5 s after the previous sentence ends.
- **Retention shape**: strongest claim in the first 15 s, second peak at 25-35% of the length, final payoff delivered before the last 10% (not after a long outro).

---

## 6. QA checklist before render

**Audio**
- [ ] Integrated loudness -14 LUFS (sleep -20 to -23), true peak at or below -1 dBTP, no clipped samples.
- [ ] Voice 14+ dB above music in the same moment; no music-over-voice in the three loudest sections.
- [ ] Chunk joins: loudness spread under 1.5 dB, no click (listen to the three loudest joins with headphones).
- [ ] Dropout scan (`audio/dropouts.py`): no silence run with speech level on either side; no word cut by a padded pause (ED-12).
- [ ] One music at a time; the tick at least 6 dB below; no more than two background layers.
- [ ] SFX never on a spoken word; each starts within one frame of its picture event.
- [ ] Fade in 0.5 s and out 1.5 s at the ends; no silence over 1.5 s unless designed.

**Picture and retention**
- [ ] Hook inside 3 s (question or promise), cold open at most 15 s.
- [ ] A visible change at least every 9 s, a pattern interrupt every 3-7 s (genre-dependent).
- [ ] Open loop at the end of every chapter or period.
- [ ] No zoom snap (same picture), no cut in the middle of a move.
- [ ] Transitions: at most three kinds; dissolves at most 10%.
- [ ] Grade, grain and vignette constant across the whole video; skin tones and the hero's colours stay in the same range.
- [ ] Brightest and darkest frames checked; no frame flashes (under 3 flashes in a second) for sleep/ambient or any viewer-safety concern.

**Legibility and platform**
- [ ] Captions and text readable on a phone held at arm's length: cap height at least 4% of frame, contrast at least 4.5:1, inside the safe area (5% margin; vertical: top 10% and bottom 20% free).
- [ ] 2 lines at most; no word on screen longer than needed to read it (15-17 characters a second).
- [ ] Chapters: first at 0:00, at least three, each 10 s or longer; titles do not spoil.
- [ ] Resolution and rate as specified (2560x1440 / 30 fps; Shorts 1080x1920); a 20-second excerpt exported at the final settings and watched on a phone.
- [ ] Disclosures, rights and the creator-approval record are present before anything is uploaded (`CLAUDE.md` invariant 4).

When an item fails, find the cause from evidence (the rule, the file, the timestamp), fix the **general** rule or tool, add a test, and re-render only what changed.
