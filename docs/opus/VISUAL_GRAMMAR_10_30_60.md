# Visual Grammar — 10 / 30 / 60 for Ink Chronicle

**Status:** Creator-set allocation; detailed Blender mappings are TODO until implemented.  
**Basis:** Research report sections C, D, F, I, J, M, Q, R and S; D-93 and D-95.

## 0. Invariants shared by all lanes

Every lane must read as the same Ink Chronicle universe:
- identical approved character proportions, facial language, costumes and silhouettes;
- shared NPR material family, ink contour rules and line-width behavior;
- controlled color roles and a fixed per-world palette derived from one visual bible;
- coherent motivated lighting, atmospheric density, texture scale and camera language;
- reusable assets with stable provenance and hashes;
- consistent image treatment at wide, medium and close shot scales.

**Monostyle does not mean every scene has the same composition.** It means different scenes are built from a common style system. Do not mix unrelated photo-real, low-poly, vector-flat and painterly assets without a normalization process.

## 1. 10% — HELPER: explain facts and structure

**Audience function:** understand.  
**Use when:** a spatial, numerical, chronological or mechanical claim cannot be explained as clearly by dramatic action alone.

### 10.1 Strategic / route / territory map
- Show geographic relationships, barriers, supply routes, fronts, retreat lines and territorial changes.
- Camera: top-down orthographic for strategic clarity; 3D oblique / terrain flyover only when elevation, pass, valley or visibility changes the outcome.
- Motion: route reveal, arrow growth, front-line draw, territory fill, markers appearing in narrative order.
- Keep map data, coordinates, borders and names deterministic. Do not ask an image/video model to invent cartography.
- Default density: no more than 3–4 place labels, two opposing factions and one active primary route arrow at once.
- Use the same Ink Chronicle palette, paper/material treatment, outline width and lighting as the other lanes.
- Decision rule: simple region/location map stays efficient 2D geometry rendered in the chosen style; terrain-critical explanation may use Blender 3D relief. Do not force every map into expensive 3D.

### 10.2 Timeline / chronological stepper
- Use for event sequences, time jumps, counterfactual divergence and cause/effect order.
- Motion: active date marker, timeline draw, branch split, milestone lock.
- Keep 3–5 date nodes visible at once; highlight only the current event.
- Narration may pause briefly or name the timeline/period on initial appearance.

### 10.3 Quantitative charts
- Bar, line, step, stacked comparison and proportional loss/resource diagrams.
- Use only sourced values and units. Preserve zero baselines where appropriate; explain any non-zero axis.
- Avoid simultaneous chart animation, complex labels and visible lip-sync competition.
- Keep one primary metric at a time; suggested ceiling from research: up to four bars or two line series.

### 10.4 Counter / ticker / ledger
- For days, distance, resources, people, casualties or cumulative change when the changing number itself matters.
- One dominant number and one unit label. Number formatting must be deterministic and frame-accurate.

### 10.5 Cutaway / mechanism / process flow
- Explain a fortress interior, machine, weapon mechanism, command hierarchy, supply system or construction process.
- Blender options: sectional cutaway, exploded view, staged assembly, highlighted moving part, connected flow.
- Avoid a 3D cutaway when a small clean 2D schematic can explain the same thing faster.

### 10.6 Factual proof / visual evidence
- Primary documents, maps, sourced illustrations, comparison panels, date/claim callouts.
- Display the actual evidence and provenance. Distinguish a historical source image from a stylized reconstruction.

### HELPER shot-design rules
- The visual should add information, not repeat the narration word-for-word.
- One primary information task per screen.
- Text must remain readable at 1440p and on a phone-sized preview.
- Include a short explanation-read interval; do not animate every label simultaneously.
- Python may calculate data, generate SVG/curves or prepare text, but the final style pass must be shared with the Ink Chronicle system. Opus must decide whether Blender owns final helper composition or whether a tightly bounded compatible overlay is necessary.

## 2. 30% — STILL: cinematic tableaux, inserts and held compositions

**Audience function:** feel, inspect, absorb.  
**Definition:** a carefully composed illustrated scene where full character-body animation is not necessary. It is not automatically a motionless image.

### 30.1 Establishing tableau
- Establish era, location, scale, social class, weather and dramatic geography.
- Shot sizes: EWS / WS / architectural master.
- Techniques: layered foreground/midground/background, slow 2.5D parallax, controlled pan/tilt, light change, fog/dust/embers, distant movement.
- Use a full 3D scene where the camera must change viewpoint or perspective; use a projected multi-plane tableau for small camera moves.

### 30.2 Character tableau
- Character portrait communicates status, fear, isolation, authority, resolve or internal conflict.
- Shot sizes: MCU / CU, occasional MWS.
- Techniques: deliberate silhouette, asymmetric framing, shallow/deep focus chosen by intent, slow dolly-in, eye movement, breathing, candle/firelight flicker.
- Do not use lip-sync for a character who is not audibly speaking.

### 30.3 Group tableau
- Council, crowd, assembly, command group, army command tent or public gathering.
- Techniques: wide architectural master, controlled symmetry, layered rows, central power hierarchy, selective head turns or gestures, camera push.
- Keep secondary faces stable and visually subordinate.

### 30.4 Detail insert / macro evidence
- Ring, seal, letter, map detail, weapon edge, hand, mechanism, artifact.
- Shot sizes: ECU / insert / macro.
- Techniques: motivated rack focus, shadow reveal, tactile light, slow micro-dolly, cut on a real sound/action.
- Use this lane for visual proof or sensory punctuation, not decorative filler.

### 30.5 Atmospheric / aftermath tableau
- Empty battlefield, damaged hall, abandoned weapon, smoke after impact, ruins, rain, snowfall, quiet aftermath.
- Techniques: held frame, slow dolly-out, moving atmosphere, environmental sound and purposeful negative space.

### 30.6 Visual contrast / juxtaposition
- Before vs after, power vs poverty, plan vs reality, two territories or two political positions.
- Techniques: matched composition, hard contrast cut, split tableau or shape-based match cut.

### STILL rendering modes
- `STILL_HOLD`: one approved still with only legally/technically permitted hold treatment.
- `TABLEAU_2_5D`: static geometry or projected layers with low-amplitude camera and atmosphere movement.
- `TABLEAU_3D`: true scene and camera animation when the view changes enough that a 2.5D projection fails.
- `INSERT`: short, high-detail image / object view with controlled focus or light.
- These are proposed render modes, not current route IDs.

**Rules:** retain the current actual STILL hold/motion rules only after checking the live BP-109 and BP-170 definitions and their tests. D-95 explicitly says STILL rules remain separate from the 5-second visible lip-sync target and 10–15-second non-dialogue VIDEO target.

## 3. 60% — VIDEO: full animated scenes

**Audience function:** see the event unfold.  
**Definition:** continuous movement or character performance is essential to the scene's meaning.

### 60.1 Large-scale battle / army movement / siege
- Establish geography before close action.
- Sequence: overhead/high-angle EWS → telephoto MWS compression → ground-level contact/reaction → aftermath.
- Techniques: elevated crane, tracking path, orbit only when geography stays readable, instanced crowds/armies, terrain-aware formation movement, staged impact and debris.
- Keep faction screen direction consistent. Use color plus shape/line symbols so identity is not color-only.
- Continuous 10–15-second action is valid when the full maneuver is clearer as one shot.

### 60.2 Small-scale fight / duel / physical confrontation
- Sequence: two-shot / MWS → OTS or side profile → ECU weapon/contact insert → CU reaction.
- Animate action in four phases: First Pose → Anticipation → Action Peak/Contact → Settle/Follow-Through.
- Prefer motivated editorial impact cuts to impossible hand/weapon collisions.
- Validate foot contact, body weight, weapon continuity and silhouette readability.

### 60.3 Dialogue / negotiation / argument
- Sequence: Master Two-Shot → OTS A → OTS B → listener reaction → insert when motivated.
- Preserve the 180-degree axis, eyeline match, screen side and room geography.
- Visible lip-sync planning target: maximum 5 seconds per speaking coverage shot. Longer dialogue is covered by reaction, hands, prop inserts or OTS shots.
- Do not make mechanical ping-pong cuts on every line.
- Use 70/30 audible spoken-word target independently of shot/lane allocation.

### 60.4 Group dialogue / council / assembly
- Master architectural frame, leader isolation, faction reaction inserts, selective speaking CU.
- Do not animate all figures simultaneously. Identify the active speaker, listeners and power relationships.
- Mix STILL and VIDEO within the scene as needed.

### 60.5 Solitary emotion / realisation / reaction
- MCU → CU or CU → EWS depending on whether the emotion needs intimacy or isolation.
- Motion may be tiny: breath, blink, eye-line change, hand tension, light movement.
- Do not confuse “full VIDEO lane” with exaggerated movement.

### 60.6 Crafting / building / repairing / manual work
- Establishing workshop shot → ECU hands/tools → action peak → result / reaction.
- Use cut-on-action, material-specific Foley and clear cause/effect.
- Rig only the hands, tool and mechanism that matter; avoid unnecessarily animating the entire workshop.

### 60.7 Travel / marching / riding / sailing / traversal
- Route map HELPER → EWS profile → lateral tracking → tail-away WS.
- Preserve travel direction and changing geography.
- Use a continuous 8–14-second move only when the progression is readable and worthwhile.

### 60.8 Discovery / reveal
- Character-first reaction, delayed compositional reveal, focus pull, silhouette reveal or dolly-out.
- Use a clear visual subject and a single revelation point.
- Align the reveal to the narrative beat and sound/music drop.

### 60.9 Environmental action / disaster / destruction
- Use physical rigid-body or pre-baked animation only for visible, meaningful destruction.
- Use particle/2D FX cards for distant or small-scale debris where they are visually sufficient.
- Bake simulations before frame rendering; avoid recomputing physics independently for every output chunk.

### 60.10 Aftermath / consequence
- Wide held shot, retreating camera, damaged environment, secondary movement and silence/low-density score.
- Let the audience understand the consequence; do not rush every result into a fast montage.

## 4. Shared camera, composition and editing grammar

These apply to all lanes.

### Shot sizes
- EWS: geography, scale, isolation and army formations.
- WS/FS: full-body action and spatial relationships.
- MWS/Cowboy: torso/hand/weapon visibility.
- MS: action/dialogue baseline.
- MCU/CU: emotion and speech.
- ECU/Insert: evidence, object detail and tactile accents.
- Two-Shot / OTS: interpersonal geography and dialogue coverage.

### Lens intent (not a rigid preset)
- 18–28mm: wide spatial context, dramatic foreground scale, proximity distortion when intentional.
- 35–50mm: neutral documentary view / master coverage.
- 85–200mm: compression, dense formations and selective isolation.
- Perspective is governed by camera distance as well as focal length. Choose lens and camera position together.

### Camera moves
- Locked-off; pan/tilt; physical dolly; lateral tracking/truck; crane/jib/pedestal; orbit/arc; dolly zoom; motivated handheld.
- A digital crop/zoom is not a physical dolly and does not create parallax.
- Use true 3D for large orbit, significant crane-up/overhead or changing occlusion. Use 2.5D only for small projection-safe moves.
- Do not move the camera without a narrative reason.

### Editing
- Hard cut, cut-on-action, match cut, J-cut, L-cut, reaction cut, insert cut, cross-cut, smash cut, motivated whip-pan, dissolve and held/freeze tableau.
- Do not use transitions as decoration. Preserve 180-degree axis, eyeline, screen direction, lighting direction, room tone and movement vector.
- A dissolve is more suitable for time/memory/soft transition than for action impact.
- Shot duration is decided by information comprehension and story beat, not a universal timer.

## 5. Required 10/30/60 validator behavior

The plan must specify:
- runtime share calculation from final shot intervals (not frame count alone if frames overlap);
- treatment of transitions, black/silence and unclassified shots;
- whether mixed scenes can contain lane-level sub-ranges;
- tolerance application independently for HELPER, STILL and VIDEO;
- no silent reclassification to make the percentages pass;
- an episode-level report showing seconds, percentages, target, tolerance and deviations;
- the spoken-word report displayed separately (70/30).

## 6. Research-to-template mapping

Opus must map the 20 scene archetypes in research section F.1 to:
- one or more eligible visual lanes;
- preferred shot sequences;
- camera and lens options;
- animation/motion recipe;
- lighting/palette recipe;
- editing / transition options;
- audio cues;
- QA failures and acceptance conditions;
- expected render tier and cost profile.

The mapping should be many-to-many. Do not force every battle, dialogue or travel beat into one fixed sequence.
