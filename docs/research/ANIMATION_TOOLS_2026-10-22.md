# Simple, beautiful, emotional, physical: how the reference shows do it, and the free tools that do it for us (2026-10-22)

The creator's note of 2026-10-22 13:51: the muse is a world of simple, beautiful animation; complexity is not required,
but the **emotion and the physics must be good**; study how the three reference shows get their results and which AI tools
and Python libraries reproduce them. Companion of [ANIMATION_UNIVERSE_2026-10-22](ANIMATION_UNIVERSE_2026-10-22.md) (the
four directions) and the source of the `animated-universe` skill. Read on 2026-10-22; licences were read on the projects'
own LICENSE files where the row says so. Nothing here names a show in a prompt: the shows are studied for principles.

## 1. What the three reference shows actually do (principles, not designs)

| Principle | Where it comes from | What it means for us |
|---|---|---|
| **Shapes you can draw in three strokes** | the undersea show's creator reduced his hero to a square with big eyes, shorts and a tie, and gave the octopus six legs instead of eight because "it was really just simpler for animation" ([Wikipedia](https://en.wikipedia.org/wiki/SpongeBob_SquarePants_(character)), [oral history](https://www.hoganmag.com/blog/the-oral-history-of-spongebob-squarepants)) | every character is one silhouette of 3-5 primary shapes; a design that needs more strokes is redrawn until it does not |
| **On-model most of the time, off-model only for the punch** | the same creator "felt that overusing exaggerated animation made it lose its impact" ([oral history](https://www.hoganmag.com/blog/the-oral-history-of-spongebob-squarepants)) | squash, stretch and wild faces are rationed to the beat that earns them; the rig's `squash` is bounded (22 %) and tied to real speed |
| **No black line, background as a character, one light** | the samurai series drew its hero without black linework, wanted "longer establishing shots so viewers feel where Jack is", and its art director brought "cinematic lighting, with mood and depth"; palette rule "no green grass, no blue sky" ([Animation Obsessive](https://animationobsessive.substack.com/p/the-visual-world-of-samurai-jack)) | an establishing plate gets time; every scene has one key light and one palette decision written down; the colour of a thing carries meaning |
| **Silhouette and negative space** | action in that series "makes use of negative space just as much as the characters" ([Ulster blog](https://blogs.ulster.ac.uk/seangorman/?p=114)); the screen became "a canvas, in which the action can take place" with split screens and aspect changes ([The Post](https://thepostathens.com/r/42d4e02783)) | compose on silhouette first: if the pose does not read in black, redo the pose; let a frame be mostly empty |
| **Long holds, fast moves, each character its own timing** | "long holds and looping motions, with action that moves quickly and then pauses abruptly ... every character moves in its own unique way" ([Animation Obsessive](https://animationobsessive.substack.com/p/the-visual-world-of-samurai-jack)) | a cycle library with eased keys and holds; per-character timing scale (a heavy man's walk is slower and lower) |
| **Silence carries story** | 1:20 without a word, carried by a burning tree and a slow move ([same](https://animationobsessive.substack.com/p/the-visual-world-of-samurai-jack)) | the narrator may stop; a held frame with sound is a beat, not a hole |
| **Rigs of separated parts, many worlds** | the sci-fi comedy is cut-out animated in a node-based tool with characters "separated into distinct parts such as arms, hair, and facial features" ([Toon Boom](https://www.toonboom.com/?p=13065), [Animation Magazine](https://animationmagazine.net/2013/12/intergalactic-travels-grandpa)) | the same rig and the same part library across every planet and era; the world changes, the pieces do not |
| **Limited animation economy** | moving part drawn, the rest held; cycles reused; mouths as a few shapes (the six Hanna-Barbera shapes + rest) ([Pixune](https://pixune.com/blog/what-is-limited-animation/), [Rhubarb](https://github.com/DanielSWolf/rhubarb-lip-sync)) | `production/rig.py`: pieces, cycles, four mouths now (A-F + X later via Rhubarb) |
| **The twelve principles as code** | squash/stretch with preserved volume, anticipation before the action, follow-through and overlap after it, slow in / slow out, secondary action ranked under the primary ([Illusion of Life summary](https://www.skills.sh/raphaelsalaja/skill/12-principles-of-animation)) | each is a function in the rig, not a wish in a prompt: `ease`, `squash`, `Spring`, anticipation keys inside `point` and `react` |

What we do not try to copy: hand-animated facial acting, cloth and hair simulation of a feature film, a crew's per-shot
timing. Our emotion comes from posing (silhouette), timing (holds and snaps), the face set (8-12 + mouths) and the
physics that makes a body feel heavy or light.

## 2. The tools (licences read 2026-10-22)

| Need | Tool | Licence | Verdict |
|---|---|---|---|
| Cut-out rig, cycles, principles, props physics | **our `production/rig.py`** (numpy + PIL, ~450 lines) | ours | **built today**; frame = pure function of its number; fits `assemble.py` |
| Mouth shapes from the narration | **Rhubarb Lip Sync** (CLI, WAV in, JSON of A-H + X shapes out) | MIT; bundled PocketSphinx BSD ([LICENSE.md](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md)) | adopt for production; the rig's `mouth_at` (letters of Scribe words) stands in until the binary is in `tools/` |
| Auto-rig a drawn humanoid and retarget motion (BVH) | **Meta AnimatedDrawings** (archived read-only 2025-09, Python 3.8, MIT code + weights) ([repo](https://github.com/facebookresearch/AnimatedDrawings)) | MIT | useful as a *joint finder* on a generated character sheet (pose estimator gives the pivots); the archived Python 3.8 stack is a reason not to depend on its renderer |
| Cut a generated character into pieces | **SAM 2** (segment by clicks or boxes) | Apache-2.0 ([LICENSE](https://github.com/facebookresearch/sam2/blob/main/LICENSE)) | adopt for the piece cut when a sheet is painted on one canvas; a sheet painted on flat chroma needs only the face-sheet matting we have |
| Background removal of a painted piece | **rembg** (code MIT; default `bria-rmbg` model needs a paid agreement for commercial use, `u2net`/`isnet` without such a note) ([repo](https://github.com/danielgatis/rembg)) | MIT + per-model | use only with `isnet-general-use` / `u2net`; never the default model |
| Rigid-body physics (ropes, bridges, falling rocks, boats) | **pymunk** (Chipmunk2D) | MIT ([PyPI](https://pypi.org/project/pymunk/)) | adopt when a shot needs more than the closed-form `drop_y`; simulate once per shot, store the trajectory, keep frames pure |
| In-betweens between two drawn keys | **ToonCrafter** (16 frames, 512x320, Apache code, weights unlicensed on the page) ([repo](https://github.com/Doubiiu/ToonCrafter)) | Apache / unclear | not now: low resolution, 2024-era, weights' terms unread |
| External rig runtimes | Godot (MIT, `--write-movie`, `--headless`), Rive C++ runtime, Synfig (GPL) | MIT / Rive / GPL | fallback only if the home rig fails the creator's eye (section 8 of the universe document) |
| A model that animates a still into video | Wan 2.6, Kling 3.0 (hosted); Wan 2.2 on a pod | per vendor | a few hero shots at most ([TOOLING_RESEARCH](../TOOLING_RESEARCH.md)); never the figure's acting |

Excluded on licence: InsightFace-based face tools (non-commercial weights), NoobAI (no commercialisation), FLUX.2 dev
for production (non-commercial), the default rembg model.

## 3. What was built today (free) and what it proved

`explainer_engine/production/rig.py` + `tests/unit/test_rig.py` (10 tests) + the 20-second clip
`rig_poc.mp4` (1280x720, 24 fps, 12 s to render on the CPU, no paid picture): a code-drawn adult figure in the ink-and-cel
manner walks in from off screen over three parallax layers, stops, points at a sign that drops and bounces on the pavement
(closed-form ballistics), speaks two lines with four mouth shapes from word timings, jumps back in surprise with
anticipation, stretch in the air and squash on landing, and settles; the scarf lags the walk and settles after the stop
(damped spring). Every frame is a pure function of its number (tested), so the chunked assembler can draw it.

Measured: 450 lines; 13 pieces; 6 cycles; 4 mouths; render 1.7x real time at 720p in one process. Not yet: a second drawn
angle (turns are flips), Rhubarb mouths, pymunk, the `rig` beat kind in `assemble.finish_frame`, pieces cut from a painted
character (the creator has not chosen a direction).

## 4. The rules this adds (house rules until sourced per D-59; proposed, not yet in the registry)

1. A character design must read as a silhouette in black at 10 % of the frame height; else redesign.
2. Squash and stretch, the wild face and the big take are rationed: at most one off-model beat per scene, tied to the story's turn.
3. Every scene names one key light and one palette decision; a plate gets its hold before the figures act.
4. Motion is the rig's: cycles, eased keys, anticipation and follow-through from code; a prompt never asks a picture for motion.
5. Physics is real or absent: a falling, swinging, floating thing obeys `drop_y` / a spring / pymunk, never a hand-guessed curve.
