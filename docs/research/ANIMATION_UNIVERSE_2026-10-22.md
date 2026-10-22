# One animated universe for Cross Worlds: four candidate directions (research, 2026-10-22)

The creator's brief of 2026-10-22 ("Define the Original Animation Universe Before Production") asks for one original,
recognisable, reusable animated universe that can hold a modern street, Mars, a prehistoric camp and a drowned future city
without looking like four productions, and that is cheap and repeatable to produce: real character action, not a slideshow
with camera moves. This document is deliverables 1, 2, 4-8 of that brief; deliverable 3 (the four concept boards) is
code that waits for the creator's money card: `explainer_engine/imagegen/universe_boards.py` (`estimate`, `run`, `board`).
Nothing was generated or paid for while writing this. The direction is the creator's choice; section 5 gives a reasoned
recommendation and no more.

What this document is NOT: a new architecture, a World Bible, an asset library or an episode. It reuses the stage A-F work
of [ARCHITECTURE_PLAN_2026-10-22](../ARCHITECTURE_PLAN_2026-10-22.md) (PR #18: Guardian, World Bible v1.0 draft, asset library,
provider adapters, parallax) and the scene continuity of PR #17 ([D-69](../DECISIONS_AND_OPEN_QUESTIONS.md)); it changes none of them.

## 1. The production philosophy, restated

**Simple to produce is not the same as poor to look at.** Television animation has lived on this since the 1950s: the
moving part (a mouth, an arm, a walking figure) is drawn and the rest is held; a walk, a run, a point and a fall are cycles
drawn once and reused; a dialogue scene is a held body with a handful of mouth shapes; a background is painted once and
panned ([Pixune, "What is limited animation"](https://pixune.com/blog/what-is-limited-animation/),
[GarageFarm, "Limited animation: what is it?"](https://garagefarm.net/blog/limited-animation-what-is-it)). The audience never
counted the drawings; it watched the staging, the silhouette, the light and the timing. Cut-out production (a figure as
layered pieces on hinges) is the same economy applied to the figure itself: assets are reused, in-betweens are tweened, and
the cost is controlled by the DESIGN of the figure, not by lowering the finish of the frame.

So the rule for Cross Worlds: **spend design effort once, where it is reused, and spend nothing per shot that a reusable
piece can carry.** Concretely:

| What the viewer sees | What the system does |
|---|---|
| a distinctive drawn world with cinematic frames | one shape language, one material treatment, one light philosophy, one composition grammar, written once in the World Bible and enforced in prompts and QA |
| expressive characters | a base figure per character: a fixed silhouette, 3 drawn angles, 8-12 expressions, 6 mouth shapes; everything else is a pose of those pieces |
| characters walking, running, pointing, falling, talking, reacting | 10-15 reusable cycles and poses on a cut-out rig, driven by the script's beats; the same cycle serves every character of the same build |
| rich environments in every era | modular plates: sky, far, mid, near layers; props and building parts as separate pieces, recoloured by palette, relit by the scene's key |
| continuity from shot to shot | the scene's master frame and staging (PR #17) plus the SAME pieces in every shot, so nothing can vanish or change |
| motion in the frame | layer parallax (PR #18) + rig motion + drawn text objects; generated video only for a few atmosphere hero shots, if ever |

The What-if stick-figure channels are the extreme end of this economy; their lesson is the constraint (few characters,
clean scenes, simple motion, narration doing the work), not their look, and the guides about them say the same: the
edge is the story and the pacing, not the art ([Satura, stickman workflow](https://saturaai.com/blog/how-to-make-stickman-animation-youtube-videos-with-free-ai-tools-qs3mdr)).
Cross Worlds wants the economy with a far better frame.

## 2. What the existing project can do today (stage A audit, re-read 2026-10-22)

Honest split between present and proposed capability (brief point 2 and 8):

| Capability | Today | Where |
|---|---|---|
| Stills with pan / push / hold, chunked ffmpeg, resumable | **yes** | `production/assemble.py` (`motion_box`), `edit/motion_lint.py` BP-22 |
| 2.5D parallax from a depth map (near parts drift more than far) | **yes, code only** (PR #18; the depth model download and a look at real frames are not done) | `production/parallax.py`, `production/depth.py` |
| A speaking hero's face changing ~once a second | **yes**: a keyed close-up from a 10-expression sheet over the blurred scene | `production/faces.py` (VB-09) |
| Speech bubbles, period cards, data visuals, drawn text objects | **yes** (free, PIL) | `finish/bubbles.py`, `production/graphics.py` |
| Word timings of the narration (for mouth flaps or beat timing) | **yes** (ElevenLabs Scribe) | `audio/scribe_words.py` |
| A pose bank per hero (a sprite per pose, walk contact / passing frames) | **partly**: files and a lint exist (`look.pose_bank`, UR-17); no rig, no interpolation, no cycle player | `assets/characters/crossworld_cast_v0/analyst/*.png`, `edit/shot_rules.py` |
| Sprite with a sound-driven mouth, blended mouth openings, premultiplied compositing | **yes, in TMR**, for the owl; portable with provenance | `tmr_engine/render/visemes.py`, `owl_assets.py`, `celestial.py` (GPU) |
| A 2D cut-out rig: layered body parts, hinges, keyframed cycles (walk, run, point, fall, turn) | **no** | proposed: `production/rig.py` (section 8) |
| Layer separation of a generated picture (character / mid / far) | **no** in our code (the Canva connector exposes one; its terms are unverified, D-53) | proposed: free matting on chroma backgrounds, as the face sheets already do |
| Scene continuity: one room, master frame, bounded repaints | **in PR #17** (awaits the creator's word) | `production/staging.py` |
| World Bible, asset library with provenance, provider adapters (bfl, fal, gemini) | **in PR #18** (draft) | `world/bible.py`, `assets/library.py`, `imagegen/providers/` |
| Generated video (image-to-video) | **no**; researched, priced ($2.5-10 per episode for a few hero shots) | [TOOLING_RESEARCH](../TOOLING_RESEARCH.md) |

What this means: every direction below is produced as **PNG pieces composited by PIL over layered plates**, which is what
the assembler already does with pictures, faces and bubbles. The missing piece for "real action" is one module: a cut-out
rig that places body parts by keyframes. It is style-agnostic, free, and is the proof of concept of section 8.

## 3. Four original directions

The four differ in shape language, line, material, dimensional feel and palette logic (brief point 6), not in colour
alone. Each is described in our own words; no show, studio, artist or character is named anywhere, and the code refuses a
prompt that does (`universe_boards.lint`). The references the creator listed were studied for principles only: simple
readable forms; exaggerated body language and silhouettes; appealing stylisation with coherent fantasy environments;
strong compositions and cinematic staging; flexibility across many imaginative settings.

### 3.1 Paper Stage
A layered cut-paper theatre. Every object is a hard-edged cut shape with no ink line, visible paper grain, and soft drop
shadows between the layers that give the scene real depth. Figures are adult, geometric, hinged; faces are a few cut pieces
(brows, eyes, one mouth) that read from far away. One key light per scene; each scene a limited palette of five colours and
one accent; wide theatrical staging with foreground, middle and far layers. Modern, Mars, prehistoric and the drowned city
are the same paper, cut into different shapes and lit differently.

### 3.2 Ink and Cel
A classic television cel look done well: one uniform bold ink outline, flat colour with exactly one shadow tone and one
highlight, adult proportions of about six and a half heads with slightly exaggerated hands, jaws and shoulders, backgrounds
in a looser softer line with gentle gradient skies, one key light with cast shadows, eye-level cinematic framing. This is the
nearest to look v2 (`world/look_v2.json`: ink-shadowed silhouettes, adult proportions, caricature in faces and hands); the
era codex applies unchanged.

### 3.3 Soft Volume
Rounded sculpted volumes with painted soft shading and no outlines: the feel of a big-screen feature in 2D. One warm key and
a cool fill, matte painted surfaces, exaggerated but believable adult body shapes, big expressive hands, faces shaded like
clay, environments of chunky simplified volumes with haze between planes, rich saturated colour with complementary shadows.
The most "premium" still; the most expensive to move (section 4).

### 3.4 Poster Graphic
Angular graphic design: hard-edged geometric shapes, no outlines, two or three colours plus one hot accent per scene, bold
silhouettes and large negative space, subtle grain and halftone, adult figures with long limbs and faces drawn with a few
shapes and strong brows, one dramatic key light with deep flat shadows, widescreen composition with a strong horizon. The
most cinematic and the most serious; comedy needs timing rather than rubber faces.

### The boards
`python -m explainer_engine.imagegen.universe_boards prompts` prints the twenty ready-to-use prompts: for each direction the
same four scenes (A a rain-wet downtown street at dusk with a woman crossing and a man waving from a diner door; B a Mars
outpost at sunrise with two suited figures, one pointing at a dust storm; C a prehistoric river camp at dawn with a hunter
pointing at mammoths; D a drowned city with an old man and a girl fishing from a tenth-floor window) plus one character
line-up (a modern woman, a prehistoric hunter, an astronaut, each calm and alarmed, on one ground line). The scene text is
identical across directions, so a board compares the direction and nothing else. `board` composes the five pictures into ONE
labelled image per direction (labels drawn by code: image models misspell them). Cost at the default candidate (FLUX 3 Image
Klein, 1k, $0.009): **$0.18 for all four boards**, one take; $0.36 with two takes; Seedream 4.5 $0.80 / $1.60; Gemini 3.1 Flash
Image $1.34 / $2.68 (prices read 2026-10-22 and 2026-10-16, `imagegen/providers`). Run only on the creator's card:
`run --approved-by --ref` records the yes against the plan's hash.

## 4. Comparative assessment (brief point 7)

Scores are my judgement from the design itself, 1 (poor) to 5 (strong); the boards and the proof of concept replace them
with evidence. "Pictures per episode" assumes a 10-minute episode of about 40 scenes.

| Criterion | Paper Stage | Ink and Cel | Soft Volume | Poster Graphic |
|---|---|---|---|---|
| Visual attractiveness of a still | 4 | 4 | **5** | 4 |
| Animation simplicity (rig, cycles) | **5**: 10-14 hinged pieces, turns are piece swaps | 4: standard cut-out rig, 3 drawn angles | **2**: shading baked in; each angle a new painting or 3D | **5**: 8-12 flat shapes, turns are swaps |
| Expressions and mouths needed | 6-8 brow/mouth combos | 8-10 faces x 3 angles + 6 mouths | 10-12 faces x angle, mouths need matching light | 6-8 brow/mouth shapes |
| Cycles that cover most scenes | ~10 (walk, run, point, fall, turn, sit, carry, react, talk, idle) | ~12 (+ toward-camera walk, gestures) | ~12, each in more angles | ~10 |
| Environment construction and reuse | **5**: layers are assets by construction | 4: line-and-flat pieces, shared skies | 3: volumes recolour, relighting repaints | **5**: shapes recolour to the scene palette |
| 2D / 2.5D / 3D | 2D pieces on a 2.5D stage (native) | 2D + layer parallax | looks 3D; honest only as many sprites or real 3D | 2D graphic + layer parallax |
| Camera angles and real movement | pans, pushes, layer parallax native; no orbit | angles from 3 drawn views | wide shots superb, new angles dear | low/high angles cheap; wide is home |
| Close-ups | 2: bold but coarse, need own pieces | **5** | 5 (with identity lock) | 3: striking, cool |
| Wide shots | 5 | 4 | 5 | **5** |
| Modern / historical / prehistoric / sci-fi | 5: one material everywhere | 5: proven on TV for decades | 5 | 4: comedy is the stretch |
| Fragile / expensive / hard to automate | grain and shadow direction drift between pictures | line weight drift (the known pain; needs a reference set or LoRA) | **most paid pictures, most drift, slowest** | restrained palette fights the model's habit |
| Fit with the existing project | **5**: PNG layers + PIL + parallax, no new runtime | 5: look v2 and the era codex apply unchanged | 2: needs stage E (LoRA) before anything moves | 4: palette.json rule and drawn text objects fit best |
| Paid pictures per episode (estimate) | ~60 plates + ~30 pieces first episode, then ~40 | ~70 then ~45 | ~120 then ~90 | ~55 then ~35 |

Honesty notes. (1) A single still of Soft Volume will look the best and is the trap the brief warns about: its figures
cannot be rigged without the shading breaking, so every pose and angle is a new paid painting; it is production-friendly
only with a 3D pipeline this project does not have. (2) Paper Stage and Poster Graphic are the cheapest to move but each
carries a tone risk (gentle; cool). (3) Ink and Cel is the safest all-rounder and the one most exposed to the drift problem
the project already fought (line weight across generated assets), which the World Bible anchors and a LoRA (stage E) are
meant to fix. (4) None of this is measured yet: the boards and the proof of concept are the evidence.

## 5. Recommendation (the choice is the creator's)

**Ink and Cel first, with Paper Stage as the close second to look at on the boards.** Reasons: it keeps the rules and code
already agreed (look v2's adult proportions and ink-shadowed silhouettes, the thirteen-era codex, the palette rule, the face
sheets); it is the one direction that is strong in close-ups AND cheap to rig, which a narrated dialogue channel needs (the
narrator's "as he would say it" lines live on faces); it has decades of television proof across every era the channel
wants; and its known weakness (line drift) is exactly what PR #18's World Bible anchors, the asset library and the stage E
LoRA comparison are built to measure and fix. Paper Stage is recommended as the alternative to compare on the boards
because it is the most automation-friendly and the most distinctive at a glance; if the creator finds its close-ups
acceptable, it would be the cheaper channel to run. Soft Volume is not recommended for production at this project's size.
Poster Graphic is recommended if the channel's tone settles on serious and adventure stories.

## 6. Preliminary asset-library plan (brief point 5; records go into `assets/library.json`, WB-06)

| Class | Shared across episodes (one asset, recoloured / relit) | Variant-based (one base, controlled variants) | Unique (per episode) |
|---|---|---|---|
| Sky and light | sky layers per light key of the era codex (dawn, dusk, storm, night, firelight, neon) | weather overlays (rain, snow, dust, embers, fog) | a one-off sky only for a story beat (an eclipse) |
| Terrain and vegetation | ground layers (grass, sand, rock, water, snow, ash); 3 tree bases (broad, conifer, dead), bush, rock, grass clumps | palette variants of the same tree (green modern, red alien, dark night), scale variants | a named landmark |
| Buildings | wall, window, door, roof, column, stair, balcony and sign pieces in 4 material sets (timber/hide, stone/brick, concrete/glass, metal/composite) | era variants of a piece (a Roman window, a 1950s window, a habitat port) | a specific famous building, drawn once from references |
| Props and vehicles | containers, tools, fire, lamp, table, chair, bed, boat, cart, car and rover bases | era dressings and palettes | a plot object (the telegram, the map) |
| Characters | 3-4 body builds (lean, average, broad, child) with the rig; a universal cycle set (idle, walk, run, turn, point, fall, sit, carry, react, talk) | per-character: silhouette, costume layer, 3 angles, 8-12 expressions, 6 mouths; costume variants per era for a visitor | a hero's face and costume (D-55 hero references; a returning hero reuses the library sheet, bible.json `characters`) |
| Effects and camera | smoke, dust, sparks, splash, breath, speed lines; the parallax profiles (hold, push, pan, drift); transition set | palette-tinted variants | none |
| Graphics | title card, recap card, sign/label/ledger/map templates in the palette fonts | per-era type treatment | the episode's own text |

Rule of thumb from the brief: share what is structural (geometry, cycles, templates), vary what is cultural (material,
costume, palette, type), make unique only what the story names. Nothing in this table is built now.

## 7. How the chosen direction is tested in the existing project (brief point 8)

Visual decisions and engineering decisions are kept apart:

1. **Visual (the creator decides)**: the four boards (section 3) -> one direction -> the World Bible's `look` part gets the
   direction's core as the new thread (a `bible bump --major`, WB-02); its first anchors are the board pictures the creator
   approves (WB-05); nothing else in the bible changes.
2. **Continuity in the direction (free review, then paid only on approval)**: PR #17's staging on one scene: a master frame
   and two shots painted with the direction's core and the same references; the continuity review says whether the
   direction holds a room (CS rules).
3. **Identity (stage D/E of PR #18, unchanged)**: the six-shot pilot runs in the chosen direction instead of the generic
   style line (`pilot.STYLE` is replaced by the direction's core; one line of code); the LoRA question is answered by the
   held-out comparison, never assumed.
4. **Motion (engineering, free)**: the rig proof of concept of section 8 on pieces cut from the approved line-up picture;
   no generated video.
5. **Gates that already exist and stay**: PV validation, motion lint (BP-22), editorial gate, `production_gate`, the paid
   assets gate of the rulebook, the ledger caps. The direction adds prompts and pieces, never a bypass.

## 8. Minimal proof of concept: style AND real animation before anything large (brief point 9.8)

Goal: one 20-second clip in the chosen direction in which a character walks into the A plate, stops, turns to the camera,
points at a sign, speaks two narrated lines with a moving mouth, and reacts, with layer parallax behind; produced by the
existing assembler, free except the pieces.

| Step | What | Cost | Done when |
|---|---|---|---|
| P1 | `production/rig.py`: a cut-out puppet = ordered PNG pieces (head, torso, upper/lower arm x2, hand x2, upper/lower leg x2, foot x2) with pivot points, placed by keyframes with easing; cycles (`walk`, `run`, `idle`, `turn`, `point`, `fall`, `react`) as JSON keyframes; `talk` = mouth piece swap from the Scribe word timings (`audio/scribe_words.py`) using the viseme logic of TMR `render/visemes.py` (ported with provenance) | $0 | a frame is a pure function of its number (chunked renders match); 15 unit tests (pivots, easing, cycle looping, mouth from words, determinism) |
| P2 | pieces: ONE paid picture of the hero on a flat chroma background in the chosen direction (front and side, arms and legs apart), cut into pieces by the same matting the face sheets use; the pivots marked by hand once | ~$0.01-0.04 | the puppet idles without seams at 1080p |
| P3 | plates: the A board picture split into far / mid / near by a depth threshold (PR #18 depth map) or by one extra paid "background only" picture | $0-0.04 | parallax runs with the hero on the near layer |
| P4 | a beat kind `rig` in the production script (`segments[].shots[].beats[]`), drawn in `assemble.finish_frame` after the picture and before faces and bubbles; motion lint counts rig motion as motion | $0 | the 20-second clip renders through `assemble --chunks`; the creator watches it |
| P5 | measure: pieces per character, minutes of hand work per character (pivots), render time per minute, seams and judder seen; write the numbers into this document and decide whether a second angle set and the full cycle set are worth it | $0 | the creator says go or stop |

What this does not test and says so: facial acting beyond mouth and brow swaps, a figure turning smoothly toward the
camera (a swap, not a turn), cloth and hair motion, crowds. Those are what a few generated hero shots would buy later, if
ever (TOOLING_RESEARCH: Wan 2.6 / Kling prices).

Sources read for this document: the two limited-animation overviews above; Godot's command-line movie mode
([docs](https://docs.godotengine.org/en/4.2/tutorials/editor/command_line_tutorial.html): `--write-movie`, `--fixed-fps`,
`--headless`) and the Rive C++ runtime ([docs](https://rive.app/docs/runtimes/cpp/overview)) as the two external 2D rig
runtimes considered and set aside for now: both would add a runtime and a file format to a pipeline whose assembler is
already PIL + ffmpeg, while the proof of concept needs about a thousand lines of numpy; they stay the fallback if P5 shows
the home-made rig is not enough.
