# HyperFrames overlay layer (v4.3 plan section 9.2, stage B5)

The overlay layer draws the animated parts of a map shot (a place label, a highlight ring, an ash plume, a route arrow, a pulse, a
counter, the date chip and the scale bar) as a **transparent video** and lays it over the picture. Python still draws the relief plate and
decides every coordinate and every frame; the layer only animates what the spec says. Free and local: Node 22, headless Chrome, ffmpeg.

| Part | File |
|---|---|
| the spec: a map shot's action plan resolved to card pixels and word frames | `explainer_engine/overlay/spec.py` (`overlay_spec/1`) |
| the HTML/GSAP composition (one template; GSAP 3.12.7 and Inter are vendored, no CDN) | `explainer_engine/overlay/hyperframes/` |
| the driver: write project, render (`hyperframes@0.9.39`, Apache-2.0, pinned in `package.json`), composite with ffmpeg | `explainer_engine/overlay/hyperframes.py` |
| the Toba sample and the timing check | `explainer_engine/overlay/sample.py` |
| the test | `tests/unit/test_overlay_hyperframes.py` |

## How a shot goes through it
1. `maps/actions.plan` resolves each action to a word (from the read's word spine) and lon/lat; `overlay/spec.build` turns that into the
   card's pixels. `spine_from_scribe` makes the spine from an ElevenLabs Scribe word list.
2. `write_project` inlines the spec into the template; `render_overlay` renders it to WebM (VP9 with alpha) or MOV (ProRes 4444).
3. `composite` lays the plate inset (Python's, fading in over the first six frames) and the overlay over the clip. The clip's audio is kept.

## What it covers and what it does not
- Covered: `route_arrow`, `front_line`, `spread`, `plume`, `pulse`, `highlight`, `label`, `counter`, a date chip and a scale bar.
- Refused by the spec builder: `zoom` and `split_compare` (they move the camera or the plate, which Python owns; a moving camera would need
  a spec per frame) and card shots (no place, no map).
- The plate in the sample is the vector plate (no relief raster in the container), so the sample shows the overlay, not the final relief.

## Measured on 2026-11-12 (container: 4 CPU, no GPU, system Chrome, ffmpeg 6.1)
Numbers and the clip links are in the stage's handoff in the project folder; the timing check renders every item alone and compares the
alpha of its box with the cubic ease the Python drawer uses (`sample.timing_report`).

## Licences checked
HyperFrames: Apache-2.0 (npm field and the repository's licence). GSAP 3.12.7: GreenSock "standard no charge" licence, commercial use
covered; forbidden are code-free animation builders competing with Webflow's and reverse engineering. Rendering a channel's video in a
headless browser is not named in the licence text, so this is read, not lawyer-checked. HyperFrames' own telemetry is switched off by
`HYPERFRAMES_NO_TELEMETRY=1` and `DO_NOT_TRACK=1` (the driver sets both). Its `publish`, `share`, `billing` and Pro `templates` commands
reach HeyGen's cloud and are never used here.

## Integration rules OV-01..OV-56 (the creator, 2026-11-12; written by the orchestrator thread, checked by `overlay/rules.py`)

The creator's words (19:43 UTC): the overlay is forbidden in video scenes; it lives in the 10 % lane (`full`) and the 30 % lane (`accent`, strict:
only where needed, never spoil the main frame); every motion makes a sound; picture first, then the overlay in the picture's style; transparent
styles in places, especially in the 30 % lane. Rules marked "house" are the creator's calls; rules marked "წ" carry a number the creator has not yet
confirmed (the table is `rules.HOUSE`, the one home of those numbers until he confirms them and they move to `sourced_rules.json`). BP numbers are read
from the registry. Status of each rule in the validator: PASS, FAIL, NOT_RUN (a measurement or a judge is missing; never PASS by default), n/a.

| ID | rule | how it is checked |
|---|---|---|
| OV-01 | an `ltx` shot (the video route of D-131, LTX since D-132) carries no overlay at all: no element, no date chip, no inset; `composite` refuses an ltx clip | validator: ltx and a non-empty overlay = FAIL |
| OV-02 | an overlay never crosses a cut: every element starts at frame >= 8 and ends >= 8 frames before the cut | spec |
| OV-03 | information a video scene needs goes into its own 10 % shot before or after it, or the narrator says it without an overlay | script lint: an ltx shot (D-131 video route) has no `overlay_reason` |
| OV-04 | `full` mode only on `map_action` shots, every kind allowed | spec |
| OV-05 | `still_25d` shots take `accent` only (OV-30..38) | spec |
| OV-06 | the overlay never changes a shot's route; shares are measured by duration | spec, mix report |
| OV-10 | the episode picture's style comes first; the overlay's colours, fonts and textures derive from it (`overlay_style` tokens: ink, paper, accent, second, dim) | `style.derive` from the picture |
| OV-11 | one visual language per episode: every colour in a composition is a style token; one style hash | scan of the composition, episode check |
| OV-12 | the overlay goes through the last pass (grade, grain) together with the photo: composite first, then grade | render order record |
| OV-13 | no pure white, pure black or neon: the overlay's most saturated colour is at most 10 % above the frame's most saturated | token measurement |
| OV-14 | at most two typefaces, tabular numbers, text at least 40 px at 2560x1440 (P-64) | spec, composition scan |
| OV-15 | text contrast at least 4.5:1, measured on the pixels under the text after glass or halo, on the composite | contrast measurement of the render |
| OV-16 | one motion set: enter and exit by BP-134, drawings 0.5-1.5 s, one easing (`power3.inOut`), one change at a time (a counter may run with a route) | spec |
| OV-17 | the unit on screen is the unit the narrator says: miles for a US audience, the scale bar too | spec, narration line |
| OV-18 | a label never sits on a line (CRAFT-CART-04): a constant offset, zero intersections of the label box with the path | measured label boxes against the path |
| OV-20 | `solid` is forbidden in the 30 % lane; only `glass` and `bare` | spec |
| OV-21 | `glass`: fill alpha 0.45-0.70, 12-24 px blur behind, a thin light edge, colour `paper` or `dim`; the rendered alpha at the centre is 115-179 of 255 | spec and rendered alpha |
| OV-22 | `bare`: line and sign without a panel; text has a halo or soft shadow; first choice for lines, pulses, rings and one- or two-word labels | spec, contrast |
| OV-23 | one number or one name = `bare`; three or more values together (mini map, small chart, timeline) = `glass` | element count |
| OV-24 | a `solid` background is never a flat colour: a relief map plate or a style card (episode photo darkened and blurred); insets inside a 10 % shot are `glass` | pixel spread of the background |
| OV-30 | need test: an accent overlay only if the line says (a) a number, (b) a place and where it is, (c) a date or time jump, (d) a comparison, (e) a new name; the shot has an `overlay_reason` and an `at_word` that is a word of the line | lint |
| OV-31 | removal test: if the line is just as clear without the overlay, the overlay goes | the script critic's question, one answer per shot (NOT_RUN here) |
| OV-32 | budget: one group per shot, at most 2 elements on screen at once; at most 40 % of the 30 % shots (by duration) carry an overlay; at most 2 such shots in a row | spec, mix report |
| OV-33 | area: all overlay boxes together at most 15 % of the frame, one glass panel at most 12 % | box area |
| OV-34 | protected zones: an overlay never touches a face (YuNet box + 10 %) or the main object on any frame of the 2.5D move (`still_25d`, D-131); 5 % safe margin from the edge; the place is chosen by Python (`place.choose`, calm zone), never by hand | intersections per frame must be 0 |
| OV-35 | timing: an element appears on its word (never earlier, BP-54), stays at least 1.5 s or words x 0.3 s (the larger); all overlays together at most 60 % of an accent shot | timing report |
| OV-36 | the overlay is anchored to the screen (does not follow the camera, does not sway); anchoring to a point of the photo is not in v1 | spec: `anchor == screen` |
| OV-37 | no impact effect (`shake`, `lightning`) while an overlay element enters or draws | camera events against overlay frames |
| OV-38 | a mini map in the 30 % lane is a `glass` inset in a corner, within OV-33's area, with at most one action and one label | spec |
| OV-40 | 10 % kinds: map with actions, chart, big counter, timeline, compare card, date or quote card | spec kind |
| OV-41 | all cartography rules on a map (CRAFT-CART-01..08, BP-124, BP-125): a simple frame, highlight first and then move, date chip when time moves, scale | validator (the dim of inactive terrain is not drawn yet: NOT_RUN) |
| OV-42 | one `full` shot 4-12 s; runs of non-character visuals within BP-127 | spec |
| OV-43 | a `full` shot moves for its whole length (an action or a slow plate camera); no frozen run over 2 s | frame differences |
| OV-44 | the episode ambience never breaks in a 10 % shot | sound plan (see OV-55) |
| OV-45 | no legend, direct labels, at most 3 grid lines, titles at most 6 words | spec |
| OV-46 | every chart has `claim_ids`; every number matches the claim map (invariant 5); the demo's data is flagged DEMO | spec |
| OV-47 | a value appears when the narrator says it (`at_word` on every bar or point) | timing |
| OV-48 | colour never carries meaning alone (D-22): the highlighted bar has a label too | spec |
| OV-49 | a 30 % chart is `glass`, at most 3 bars or one line, within OV-33 | spec |
| OV-50 | every overlay motion (enter, draw, grow, count, marker move) has a sound event at its start (BP-54 window); a calm fade is not a motion and is silent | spec |
| OV-51 | the sound follows the motion's shape: a long motion has a long sound of the same length (+-2 frames), a point motion one hit | spec |
| OV-52 | one sound family per episode, in the picture's style: soft, organic (paper, pencil, wood, a soft bell); no digital beeps; one kind = one sound class everywhere (BP-57 variants) | sound plan |
| OV-53 | overlay sounds go through the same sound plan and renderer, in the SFX stem (BP-52, BP-65), and sit at least 6 LU below the scene's real sounds | stem measurement |
| OV-54 | at most 2 sounds of one class at once (BP-56) | sound plan |
| OV-55 | the ambience never breaks (in the 30 % lane the overlay sound lies over the scene's ambience; in the 10 % lane the ambience carries over from the neighbouring scene or the shot has its own); 10 %, 30 % and 60 % sit at one level | level gate by route |
| OV-56 | source: the library first (OR-18); a new paid sound only on the creator's word; procedural numpy sound cannot go into an episode, only into the demo | existing hook |

BP-55 (at most half of the visual beats have a sound) is overridden for overlay motion sounds by the creator's newer word: their purpose is `sync`
and they do not count in BP-55's share.

## Common mistakes OV-57..OV-69 (the creator, 2026-11-12 21:06 UTC: "research the mistakes made often and write them into the rules")

Two sources: (a) what editors, chart makers, map makers and sound editors name as their usual mistakes (web, 2026-11-12; pages opened are marked
*opened*, the rest were read as search summaries only), and (b) the mistakes this thread itself made while building the first demo, each found by
a measurement or by the eye. Most of (a) was already a rule (faces and margins OV-34, contrast OV-15, time on screen OV-35, no legend and direct labels
OV-45/OV-48, one style OV-11, no sound without need OV-50..OV-54); the rows below are what was missing. Every number is a house number ("წ") until
the creator confirms it; none comes from two source types yet (D-59), so each is a hypothesis with its measured check.

| ID | rule | the mistake it stops | check |
|---|---|---|---|
| OV-57 | a chart title states the finding ("Toba was 19 times bigger"), not the topic ("Eruption sizes") | the viewer has seconds and must work the point out alone (Online Journalism Blog 2026-06-23, *opened*) | critic question, NOT_RUN in code |
| OV-58 | bars stand on zero and their heights are in proportion to their values; a value axis never rescales while it is animated | the truncated axis and the bar that lies (GraphPad series, search summary) | spec |
| OV-59 | a `full` chart shows at most 5 bars, 6 line points or 5 timeline marks (accent: OV-49) | "a top ten is too much for video" (Online Journalism Blog, *opened*) | spec |
| OV-60 | exactly one bar wears the focus colour, the others stay neutral | colour on everything: the eye has nowhere to go (same source: remove to improve) | spec |
| OV-61 | no text overlaps another text, and no text sits on a data point (6 px clear) | a label on its own dot or on the line (map and chart guides; found in this demo: "0 °C" on the first point of the line chart) | measured text boxes |
| OV-62 | a sound belongs to a motion and lies inside it; fades, still parts and titles are silent | a whoosh on everything flattens the mix and hides the payoff (Boom Box Post, Kate Finan, *opened*) | spec |
| OV-63 | every chunk has exactly its planned frames, the final file their sum, audio and picture within 1 frame | **this demo:** `overlay=shortest=1` dropped the last frame of each of 9 shots: 9 frames of drift against the sound by the end | frame counts of the files |
| OV-64 | the overlay's step with the picture is measured on the COMPOSITE: lag 0 and no repeated overlay frame | **this demo:** WebM stores milliseconds, 0.042 s is later than 1/24 s, so a third of the overlay frames landed one frame late; the timing check read only the overlay's own file and passed | `demo_measure.sync_check` |
| OV-65 | a rendered file is used only with the spec it was made from (picture: the spec without sound; mix: the sound plan) | **this demo:** the report ran on specs older than the code and showed sound errors that were already fixed | hashes |
| OV-66 | the last word of a line ends inside its audio | **this demo:** a 24 kHz read fed to a 16 kHz aligner stretched every word time by 1.5 | word times against the read's length |
| OV-67 | text is drawn in the ink token only (dim, accent and second are for lines and fills) | **this demo:** the zero label in the dim token measured 4.22:1, under OV-15 | the fills of the drawn texts, read from the composition |
| OV-68 | before a file is sent the thread looks at one settled frame of every shot cut from the FINAL file and records it (`eye_check.json`: file hash, findings fixed, findings open); a newer final file needs a new look | **this demo:** the validator said 0 FAIL while the frames showed a label on a point and the file was 9 frames short. A PASS is not a look | the record and its hash |
| OV-69 | a long chain is one tracked process whose log ends with DONE or FAIL; never a shell loop that waits on `pgrep` | **this demo:** a chained background command died without a line and 20 minutes passed before it was seen | `demo_build.main` writes the line |

How the two ffmpeg mistakes are avoided in code: the overlay input is read with `-r 24` (exact frame times instead of the stored milliseconds) and the
`overlay` filter runs with `eof_action=repeat`, the frame count comes from `-frames:v`. Checked on three shots rendered both ways: the old command gives
lag 0-1 and 3-7 stalled frames, the new one lag 0 and 0 stalls on all nine overlay shots.

Not opened by this thread (search summaries only, so guidance, not grade): the GraphPad chart series, the Splice and Maptive map guides, the Frame.io and
PremiumBeat title guides beyond the opened Frame.io page ("on screen long enough to read every word twice" is its only number; OV-35 already asks for more).

### `overlay_spec/2` (explainer_engine/overlay/spec2.py)

New against spec/1: `mode` (full / accent), `surface` (solid / glass / bare), `overlay_reason`, `style_ref` and the style tokens, `anchor`, `protected[]`
(face and object boxes in picture units, moved with the 2.5D camera (D-131) by `camera.cam`), panels with a place chosen by `place.choose`, per item a `sound` list
(class, frame, length), and the kinds `bar_chart` (bars), `line_chart` (segments), `compare_pair` (halves), `timeline`, `stat_callout`, `counter_big`.
Geometry, time and sound are decided in Python; `hyperframes/template2.html` only draws them. A tween begins one frame before the word frame so that
its first visible change lands ON the word frame (measured by `window.__timing` in the composition and by the rendered alpha).

### The free 2-minute demo (`overlay/demo_build.py`, report `overlay/demo_report.py`)

Twelve shots (10 % and 30 % lanes and one LTX clip of the D-131 video route), 2560x1440, 24 fps, 120 s, one chunk per shot; the narration is a free scratch read (Kokoro, word
times by faster-whisper at 16 kHz, `demo_words.json`), the sounds are procedural, the photos are the three existing ones (M1, M3, `start_c1.png`), the map
plates are the repo's relief plates tinted with the style tokens. All data on screen is DEMO data and the demo is never uploaded. Cost: 0.
