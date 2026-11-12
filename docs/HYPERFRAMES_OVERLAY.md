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
