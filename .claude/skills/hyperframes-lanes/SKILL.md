---
name: hyperframes-lanes
description: Use HyperFrames (our pinned HTML-to-video overlay tool) and its official skills and block registry inside the channel's rules - which registry blocks fit the 10 % map lane and the 30 % photo lane, what our own renderers already do better, and the free QA commands that catch audio/picture drift and frozen frames. Use before building any overlay, counter, map animation, film texture or transition, and before judging sync or liveliness of a rendered clip.
---

# HyperFrames in our lanes

HyperFrames renders HTML/GSAP to video frame by frame. We already use it for the overlay layer (`docs/HYPERFRAMES_OVERLAY.md`,
driver `explainer_engine/overlay/hyperframes.py`, pin in `explainer_engine/overlay/hyperframes/package.json`). HeyGen's official
agent skills are vendored, unchanged, in `vendor/hyperframes-skills/` (Apache-2.0, source commit in its `README.md`). They are
not loaded as skills on their own: this page is the entry point and it wins where they differ.

## Our rules first (where the vendored skills say otherwise)

1. **Lanes.** Overlays only in the 10 % map lane and the 30 % photo lane, never on the 60 % video shots (OV rules in
   `docs/HYPERFRAMES_OVERLAY.md`). The picture is made first, then the overlay in its style; in the photo lane it is transparent
   and never covers a face or the subject.
2. **Pin.** The CLI is `hyperframes@0.9.39`. The vendored skills were written for 0.9.46: check every flag with
   `npx hyperframes@0.9.39 <command> --help` before using it. A pin bump is its own change with a test.
3. **Nothing leaves the machine.** Set `HYPERFRAMES_NO_TELEMETRY=1` and `DO_NOT_TRACK=1`; skip the vendored "usage beacon".
   Never use `publish`, `share`, `billing`, `templates`, `reverse`, `audio --quality best` (it uploads to HeyGen and may bill)
   or `snapshot --describe` (it sends frames to Gemini). Media comes from our own lanes: voice and SFX from ElevenLabs and
   the sound library, pictures from our own pipeline, never HeyGen's `media-use`, avatars or generated video.
4. **Our art, our maps.** The vendored map advice (satellite tiles through `bake-basemap.mjs`, real imagery) does not apply:
   our maps are drawn by `maps/` on our relief, letter-free, under the `cartography` skill and `docs/RIGHTS_AND_FAIR_USE.md`.
   A registry map block is a technique reference (arc timing, marker pop, label after the camera holds), not a source of plates.
5. **No CDN in renders.** Registry blocks load GSAP from a CDN; for production, point them at the vendored GSAP in
   `explainer_engine/overlay/hyperframes/vendor/`, as our template does.
6. **Licence per item.** The registry is Apache-2.0 but some blocks carry third-party code (for example the WebGPU shader
   blocks: MIT, `lib/*THIRD-PARTY-LICENSES.txt`). Record the item and its licence in the shot's asset record before use.
7. **The director decides.** Which effect a shot gets is the director's choice by the written criteria
   (`living_director` in PR #188, LP rules); this page only says which tool can draw it.

## Which registry item for which need

Search: `npx hyperframes@0.9.39 catalog --query "<the beat, in English>" --json`; install into a scratch project:
`npx hyperframes@0.9.39 add <name> --json`. Checked on 2026-11-14 against the registry at the vendored commit.

| Need | Registry item | Lane | Our own renderer already has it? |
|---|---|---|---|
| film texture, warmth | `grain-overlay`, `grain-field` | 30 % | no: candidate |
| memory beat, motivated transition | `organic-light-leak-overlay`, `light-leak` | 30 %, seams | no: candidate |
| handheld or rig camera feel | `camera-shake` (nine measured profiles, seek-safe) | 30 % | partly (`handheld`, `shake`): compare |
| a key light travelling over a scene | `light-sweep-pass` | 30 % | partly (`sun_shaft_drift`, `sun_glint`) |
| falling snow, stars | `snow`, `starfield` | 30 % | yes (`snow` in three depth layers, `stars`, occluded by depth): keep ours |
| rack focus, dolly zoom, pull-back | `rack-focus`, `camera-dolly-zoom`, `pull-back-reveal` | 30 % accents | partly (`rack_focus`): compare |
| counter, number that lands | `count-up`, `number-wheel`, `number-pop-in` | 10 % | yes (overlay `counter`): borrow the landing |
| route with marker, landing pop | `nyc-paris-flight`, `us-map-flow` (arcs) | 10 % | partly (`route_arrow`): borrow arc and pop timing |
| chart built in reading order | `chart-story`, `data-chart`, `bar-chart-race` | 10 % | no: candidate for card shots |
| transitions with a cause | `catalog --tag transition` | seams | no: candidate |

Wind in trees, cloth, wire sway, fire, smoke, breath and water are not in the registry: they stay in our renderer.

## Free QA that catches our faults

These run locally on a finished mp4 or a HyperFrames project and cost nothing:

- **Sound against picture.** `hyperframes measure events <clip.mp4> --map --json` lists when things change on screen with the
  sound beside them; `hyperframes audio <clip.mp4> --only moments,onsets --json` gives where each hit lands. A visual event and
  its sound more than BP-54's window apart is a sync fault; report it with both times.
- **Lip sync on spoken video clips.** `hyperframes measure sync <clip.mp4> --json`: the lag between mouth motion and voice.
- **Liveliness.** `hyperframes measure energy` compares how much two clips move and when; use it next to the reference clip
  when a photo-lane shot is judged "frozen".
- **Cuts and seams.** `hyperframes measure cuts <reel.mp4> --json` finds hard cuts (and lists flashes and whips apart);
  `snapshot --review` on a project writes a strip around every cut.
- **Motion intent.** A `<name>.motion.json` next to a composition (`appearsBy`, `before`, `staysInFrame`, `keepsMoving`) makes
  `check` fail an overlay that arrives late, leaves the frame or freezes.

Every result is evidence for a gate, not a gate by itself: a number becomes a threshold only through
`explainer_engine/standards/sourced_rules.json` (D-59).

## Where to read more

- Composition contract, work loop: `vendor/hyperframes-skills/hyperframes/SKILL.md`, `references/format.md`.
- Motion craft and transitions (measured on HeyGen's films; one source type, so hypotheses for us): `references/motion.md`.
- Explainer structure: `references/types/explainer.md`. Sound placement: `references/sound.md`.
- CLI and recovery: `vendor/hyperframes-skills/hyperframes-cli/`. Registry wiring: `vendor/hyperframes-skills/hyperframes-registry/`.
- What we took into our own rules: the `editing-style`, `visual-beats` and `cartography` skills, sections marked "HyperFrames".
