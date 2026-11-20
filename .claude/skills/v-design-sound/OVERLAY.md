# Overlay for `v-design-sound`: Sound design (layer L18, stages G4 and G8)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from codepawl/creator-generalist, page `design-sound` (MIT, commit `007290c354`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel whose sound is planned from an event contract and
played by one renderer. The upstream text is this folder's `SKILL.md`; its `references/` stay the craft
library this page points into (layering, distance maths, mix practice). Its `scripts/` are not run here (see the end).

## What this layer owns

A scene of ours is a place, a time and people doing something. The sound has to say **where we are** (the bed), **what
just happened** (effects on the frame) and **how it feels** (music, only when it helps). The design is written into the
script and the sound plan; the cue sheet and the renderer only play it (skill `v-audio-production-skill`).

## The four house rules

1. **One continuous bed per place.** Every `location_id` gets one bed that runs under every shot and every line of its run
   of shots and across every cut (BP-189, BP-191); at a place change the next bed leads in and the old one tails out
   (J/L bridge, SP-01, BP-117). One bed row, not two beds stacked: wind and crowd are summed into one bed take, or the
   crowd becomes a spot effect. The bed is a real recording of that kind of place (BP-193), a loop with a clean seam
   (BP-58), never generated noise. Room tone stays under an authored silence.
2. **At least three heard effects per scene** (the creator's floor in the final plan, 2026-11-19; its validator is W2
   work). Count effects with an `sfx` decision that land on a visible event, not beat cues or the bed. A scene that cannot
   reach three has too little happening on screen: give the director a visible action (a hand on a bolt, a door, boots in
   mud, a page torn), never a filler sound nobody makes. If the floor and BP-55's beat share pull apart, keep both
   reported and ask; do not drop an effect to quiet a REVIEW.
3. **Every visible event has exactly one audio decision** (AV contract, D-135, AV-01..AV-08). `episode/events.visual_events`
   resolves each map action and each 2.5D motion item into an id, a frame span and one decision: `sfx`, `ui_cue`,
   `ambience_only`, `music_only`, `silent_by_design` (with its why) or `review_required`. A locked script carries
   `av_contract: "av_events/1"` with an `event_id` and `audio` on every item; a missing one FAILs at G1.
4. **A word alone never earns a sound** (AV-07). "The army was fired up" makes no noise. A word naming a sound class goes to
   the shot's `candidates`; only an authored `sound_events` item or a visual event is placed. A sound only mentioned and
   not seen stays under `heard_not_seen` (SP-03).

## Procedure

1. **Read the scene as a list of visible events** with the director's shot list (skill `v-director-cinematic`): what moves,
   what touches what, what material, how far from camera. Write each as plain words (material, action, space, distance):
   "iron shovel into wet clay, close". The visual beats page (skill `visual-beats`) owns where a cue lands.
2. **Give each event its decision and class** from `episode/sound_plan.EVENT_CLASSES` (map classes such as `map_route_draw`
   and `map_line_snap` included; map and chart motion makes a sound, BP-192). Camera moves are silent by default.
3. **Name the place and its bed** for every shot, and the shot's coverage state (SP-04: `FULL_LAYERED_DESIGN` ...
   `INTENTIONAL_SILENCE`, silence with its sentence).
4. **Check the era.** `audio/sfx_planner.filter_sound_events_for_era` refuses classes the period never heard and takes
   tagged with a later world (traffic, an engine, a garage).
5. **Library first** (OR-18, D-76): search the catalog by facets, not file names:
   `python -m explainer_engine.audio.catalog search --category ambience --era <era> --mood <mood> --usage background_layer`,
   preview with `catalog preview`, then record the search:
   `python -m explainer_engine.assets_reuse <episode folder> --kind sfx --tags <tags> --decide reuse|generate_new`.
6. **Free and licence-checked next**: a pick list through `python -m explainer_engine.audio.free_import <picks.json> <raw folder>`
   (pages read one at a time, LIB-03; licence verdicts in `audio/sources.py`; the BBC RemArc list is refused). Effects are
   chosen by quality, music by licence (LIB-05).
7. **Only then a paid take**, priced and with the creator's word (skill `v-elevenlabs-sound-effects`); the hook refuses a
   paid call without step 5's record.
8. **Run G4**: `python -m explainer_engine.episode run episodes/<id> --stage G4`; read `audio/sound_plan.json` (`needs`,
   `candidates`, `heard_not_seen`) and `production/av_events.json`. Every class on `needs` is a gap to fill, not to fake.
9. **After G8** read `sound_coverage.md` and `qa/av_event_report.md`: each event's take, onset offset and whether it is heard
   over its bed. Every row says `human: not_listened` until a person has listened.

## Placement rules (numbers live in the registry)

On the frame, early worse than late (BP-54); at most two of a class at once and a cap on layers (BP-56); no identical
take twice in a row, variants or the cue sheet's pitch and gain jitter (BP-57); one-shots for events, loops for beds
(BP-58); distance as gain, low-pass and outdoor reflection (SP-06: close, medium, distant); music only where the segment's
mood asks for it (SP-05); beat cues are free earcons from `audio/cues.py` within BP-64 and BP-81, never a second effect.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| a scene sounds like a slideshow | fewer than three effects; events planned as `ambience_only` | add visible actions with the director; give them `sfx` |
| a "senseless hiss" under a scene | generated noise or a wrong bed class | a real bed of that place (BP-193), library then free source |
| silence drops in a dialogue scene | bed ends at a clip cut | one bed row over the place's run; `production/scene_join.py` keeps it under clip joins |
| a battle din under a map | a word placed a sound | map shots take only their action layer and authored events (SP-03) |
| a car under a 1914 trench | take tagged for a later world | era filter; re-tag the take in the catalog |
| the same thud three times | one take reused | BP-57 variants or jitter; add takes to the library |
| effect lands before the hand | onset of the take not at its start | `audio/stems.onset_of`; trim the take's head in the library |

## References: when to open which

| File | Open when |
|---|---|
| `references/foley.md` | layering one event from several takes, query words, size and distance maths |
| `references/mix.md` | why the voice leads the mix, ducking and carving practice, the evidence behind it |
| `references/library.md` | how text-to-audio search ranks and why short impacts need a look at the waveform |
| `references/sources.md` | prompt wording for a generated effect, the order of sources |
| `references/music.md` | fitting a real track to a cut, mood search |
| `references/video-foley.md` | only to know why we do not generate foley from the picture |
| `examples/score-example.json` | never for production; a sketch format |

Ideas kept from upstream: describe each event in plain words before searching; every visible event at its own frame; no
merged sound covering several actions; values only ears can set (duck hold, cue margin) are the creator's, settled by a
blind A/B he listens to, never argued from measurements.

## Not used from upstream

The scripts and their `uv`/torch/CLAP index and home-folder library (ours is `assets/audio/library` with its
`manifest.json` and catalog), "licences warned, never blocking" (our quarantine and refusal rules win), video-to-foley
and its hosted variant (GPU or paid, and it bypasses the AV contract), `score.py` sketches, its own mix and loudness
targets (ours come from the registry), and `house-defaults.json` as a source of values.
