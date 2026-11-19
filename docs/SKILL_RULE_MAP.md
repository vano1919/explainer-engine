# Skill rule map (W1, P-4)

Where every rule id of the six archived skills (`.claude/skills/_archive/`: `video-editing-architect`, `shot-visuals`,
`animation-principles`, `animated-universe`, `editing-style`, `lora-training`) and of the nine craft checklists now lives, so no
rule disappears when a skill is archived. `tests/unit/test_vendored_skills.py` checks that every id in the archived skills
and every checklist id is a row start below exactly once.

Mapping targets (exactly one per id):

- **validator**: `explainer_engine/validators/<stage>.py` (W2 builds it; stage names fixed in the final plan). A W2 test checks the
  id is in that module's `RULE_IDS`.
- **existing**: a module or the canonical document that already holds the rule (opened, path exists).
- **judgement**: a `v-<skill>` (vendored) or kept skill carries it as judgement, checked by the critic or the eye, no number.
- **hypothesis**: no home beyond REVIEW; stays a hypothesis until a second source type exists (D-59).

## A. The 102 craft checklist rules (`standards/craft_checklists/*.json`, the one home of the text)

Counts: validator 11, existing 39, judgement 47, hypothesis 5 (total 102).

| Rule | Skill-table id | Skill | Check (planned cell) | Mapping | Target | Rule text |
|---|---|---|---|---|---|---|
| `CRAFT-ANI-01` | ANI-01 | animation-principles | eye | judgement | `v-animate-characters` | squash and stretch keep the volume |
| `CRAFT-ANI-02` | ANI-02 | animation-principles | eye | judgement | `v-animate-characters` | anticipation before every big action |
| `CRAFT-ANI-03` | ANI-03 | animation-principles | eye | judgement | `v-animate-characters` | staging: one idea read at a glance |
| `CRAFT-ANI-04` | ANI-04 | animation-principles | eye | judgement | `v-animate-characters` | pose to pose: keyframe and next pose carry the action, the model fills between |
| `CRAFT-ANI-05` | ANI-05 | animation-principles | eye | judgement | `v-animate-characters` | follow-through and overlapping action |
| `CRAFT-ANI-06` | ANI-06 | animation-principles | eye | judgement | `v-animate-characters` | slow in and slow out on limbs, not only on the camera |
| `CRAFT-ANI-07` | ANI-07 | animation-principles | eye | judgement | `v-animate-characters` | actions move on arcs |
| `CRAFT-ANI-08` | ANI-08 | animation-principles | eye | judgement | `v-animate-characters` | secondary action (hair, cloth, breath) is free |
| `CRAFT-ANI-09` | ANI-09 | animation-principles | code | existing | `explainer_engine/scripting/film_shots.py` | timing: shot rhythm and visual mix |
| `CRAFT-ANI-10` | ANI-10 | animation-principles | eye | judgement | `v-animate-characters` | exaggeration in the caricature, never in the facts |
| `CRAFT-ANI-11` | ANI-11 | animation-principles | eye | judgement | `v-animate-characters` | solid drawing: no duplicated or missing limbs |
| `CRAFT-ANI-12` | ANI-12 | animation-principles | eye | judgement | `v-animate-characters` | appeal: the hero stays on model (hero references, D-55) |
| `CRAFT-ANI-13` | ANI-13 | animation-principles | eye | judgement | `v-animate-characters` | a held character breathes: blink cadence and a moving hold on long holds |
| `CRAFT-ANI-14` | ANI-14 | animation-principles | eye | judgement | `v-animate-characters` | a planted foot does not slide |
| `CRAFT-ANI-15` | ANI-15 | animation-principles | code | existing | `explainer_engine/qa/identity.py` | lip-sync offset and confidence measured on every full-tier spoken shot |
| `CRAFT-ANI-16` | ANI-16 | animation-principles | code | existing | `explainer_engine/qa/identity.py` | identity score against the hero sheet, threshold calibrated on our own sheets |
| `CRAFT-CART-01` | CART-01 | cartography | code | existing | `explainer_engine/maps/laws.py` | an animated map frame stays simple: label and unit caps, inactive terrain dimmed |
| `CRAFT-CART-02` | CART-02 | cartography | critic (planned P8) | judgement | `cartography (kept skill, no vendored equivalent)` | one change at a time; the changed thing is highlighted before it moves |
| `CRAFT-CART-03` | CART-03 | cartography | code | existing | `explainer_engine/maps/laws.py` | a temporal legend or date chip whenever map time advances |
| `CRAFT-CART-04` | CART-04 | cartography | eye | judgement | `cartography (kept skill, no vendored equivalent)` | labels never cross a line feature, keep one offset and a halo, size by feature class |
| `CRAFT-CART-05` | CART-05 | cartography | code | existing | `explainer_engine/design/palette.py` | quantitative layers use sequential or diverging palettes; faction pairs are colour-blind safe and never colour-only |
| `CRAFT-CART-06` | CART-06 | cartography | critic (planned P8) | judgement | `cartography (kept skill, no vendored equivalent)` | one projection and north-up per episode; a scale bar on every meso and micro map; a legend only with more than two symbol classes |
| `CRAFT-CART-07` | CART-07 | cartography | code | existing | `explainer_engine/maps/laws.py` | a change of map altitude takes its eased duration |
| `CRAFT-CART-08` | CART-08 | cartography | eye | judgement | `cartography (kept skill, no vendored equivalent)` | map type is the style bible's (Fredoka, Inter), not the Blueprint's set |
| `CRAFT-CIN-01` | CIN-01 | shot-visuals | critic (planned P8) | judgement | `v-director-cinematic` | every shot card names a lens tier motivated by the beat (long = compression, wide = space) |
| `CRAFT-CIN-02` | CIN-02 | shot-visuals | critic (planned P8) | judgement | `v-director-cinematic` | camera height low / eye / high motivated (low reads strong) |
| `CRAFT-CIN-03` | CIN-03 | shot-visuals | code (planned P6) | validator | `explainer_engine/validators/shots.py` | two shots of one subject in a row change angle by 30 degrees or the lens by 20 mm |
| `CRAFT-CIN-04` | CIN-04 | shot-visuals | code | existing | `explainer_engine/scripting/continuity.py` | screen sides and the axis hold inside a scene |
| `CRAFT-CIN-05` | CIN-05 | shot-visuals | eye | judgement | `v-director-cinematic` | headroom and nose room: a facing figure has lead room toward its gaze |
| `CRAFT-CIN-06` | CIN-06 | shot-visuals | critic (planned P8) | judgement | `v-director-cinematic` | depth staging: foreground, midground and background named on the card |
| `CRAFT-CIN-07` | CIN-07 | shot-visuals | code | existing | `explainer_engine/production/continuity.py` | the focal point stays within BP-30's shift across a hard cut |
| `CRAFT-CIN-08` | CIN-08 | shot-visuals | code | existing | `explainer_engine/scripting/film_shots.py` | shot-size variety inside a scene |
| `CRAFT-CIN-09` | CIN-09 | shot-visuals | critic (planned P8) | judgement | `v-director-cinematic` | a per-segment visual intensity rises toward the climax and drops at the resolution, with contrast between neighbours |
| `CRAFT-CIN-10` | CIN-10 | shot-visuals | code | existing | `explainer_engine/edit/visual_compensator.py` | lane shares follow each beat's dramatisability score inside the run caps |
| `CRAFT-CIN-11` | CIN-11 | shot-visuals | eye | judgement | `v-director-cinematic` | stakes and named heroes in every frame |
| `CRAFT-EDC-01` | EDC-01 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | every cut decided by the Rule of Six in its order (emotion first, sacrifice from the bottom) |
| `CRAFT-EDC-02` | EDC-02 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | never cut without a reason |
| `CRAFT-EDC-03` | EDC-03 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/edit.py` | a cut inside an action lands 2-4 frames after the motion begins |
| `CRAFT-EDC-04` | EDC-04 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/edit.py` | every rendered shot keeps its handles at both ends |
| `CRAFT-EDC-05` | EDC-05 | video-editing-architect | code | existing | `explainer_engine/edit/motion_lint.py` | hard cut by default; a dissolve only at a change of place or time |
| `CRAFT-EDC-06` | EDC-06 | video-editing-architect | eye (planned P7) | judgement | `v-edit-video` | an occlusion wipe is used only as an invisible cut (a silhouette crosses the lens), never as a visible transition |
| `CRAFT-EDC-07` | EDC-07 | video-editing-architect | code | existing | `explainer_engine/edit/motion_lint.py` | whips and flashes are spaced and open a story turn |
| `CRAFT-EDC-08` | EDC-08 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/edit.py` | whip, speed ramp and rack focus keep their durations |
| `CRAFT-EDC-09` | EDC-09 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/edit.py` | every shot's boundary frames match the scene's master frame within a bounded transfer |
| `CRAFT-EDC-10` | EDC-10 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/color.py` | hero costume and skin swatches stay inside a delta-E band across the episode |
| `CRAFT-EDC-11` | EDC-11 | video-editing-architect | eye | judgement | `v-edit-video` | one constant film look over the whole episode |
| `CRAFT-EDC-12` | EDC-12 | video-editing-architect | eye | judgement | `v-edit-video` | delivery frame rate 24 fps, the video clips' native rate (D-85, creator-confirmed 2026-10-31); D-30's 30 fps is superseded |
| `CRAFT-MOG-01` | MOG-01 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/edit.py` | a graphic enters with an ease-out and leaves with an ease-in inside its durations |
| `CRAFT-MOG-02` | MOG-02 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/edit.py` | a counter ticks at a readable rate and lands on its spoken number |
| `CRAFT-MOG-03` | MOG-03 | video-editing-architect | code (planned P7) | validator | `explainer_engine/validators/edit.py` | at most one graphic element in motion besides the camera |
| `CRAFT-MOG-04` | MOG-04 | video-editing-architect | eye | judgement | `v-edit-video` | every HUD element keeps one slot per episode |
| `CRAFT-MOG-05` | MOG-05 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | coherence: no decorative beat |
| `CRAFT-MOG-06` | MOG-06 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | signaling: one focus, the rest dimmed |
| `CRAFT-MOG-07` | MOG-07 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | redundancy: no burned narrator subtitles on 16:9 (captions as a soft track) |
| `CRAFT-MOG-08` | MOG-08 | video-editing-architect | eye | judgement | `v-edit-video` | spatial contiguity: a label sits by its object |
| `CRAFT-MOG-09` | MOG-09 | video-editing-architect | code | existing | `explainer_engine/production/beats.py` | temporal contiguity: the visual lands on its word |
| `CRAFT-MOG-10` | MOG-10 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | segmenting: chapter cards cut the story into named parts |
| `CRAFT-MOG-11` | MOG-11 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | pre-training: names and sides are shown before the battle |
| `CRAFT-MOG-12` | MOG-12 | video-editing-architect | code | existing | `explainer_engine/production/beats.py` | modality: narration carries the words, on-screen text stays short |
| `CRAFT-MOG-13` | MOG-13 | video-editing-architect | code | existing | `explainer_engine/scripting/narration_lint.py` | personalisation: 'you' to one listener |
| `CRAFT-MOG-14` | MOG-14 | video-editing-architect | eye | judgement | `v-edit-video` | voice: a human-sounding narrator |
| `CRAFT-MOG-15` | MOG-15 | video-editing-architect | critic (planned P8) | judgement | `v-edit-video` | image: a host appears because it acts, not to decorate (the speaker's image need not help learning) |
| `CRAFT-PKG-01` | PKG-01 | shorts-for-video | manual | hypothesis | `creator or person does it; REVIEW only (no second source type yet)` | three title-and-thumbnail promises of different mechanism before the scenario |
| `CRAFT-PKG-02` | PKG-02 | shorts-for-video | critic (planned P8) | judgement | `v-viral-youtube-shorts` | the script's first seconds pay the chosen promise |
| `CRAFT-PKG-03` | PKG-03 | shorts-for-video | eye | judgement | `v-viral-youtube-shorts` | Studio's intro, top moments, spikes and dips mapped onto segment ids |
| `CRAFT-PKG-04` | PKG-04 | shorts-for-video | eye | judgement | `v-viral-youtube-shorts` | the midpoint retention gate (the intro gate is BP-48's) |
| `CRAFT-PKG-05` | PKG-05 | shorts-for-video | code (planned P9) | validator | `explainer_engine/validators/shorts.py` | a Short stays inside YouTube's length limit |
| `CRAFT-PKG-06` | PKG-06 | shorts-for-video | code | existing | `explainer_engine/production/shorts.py` | captions, labels and the face inside the Shorts safe zone |
| `CRAFT-PKG-07` | PKG-07 | shorts-for-video | code | existing | `explainer_engine/production/shorts.py` | the hook is spoken from the first second |
| `CRAFT-PKG-08` | PKG-08 | shorts-for-video | critic | judgement | `v-viral-youtube-shorts` | the thumbnail opens a gap the video closes, honestly |
| `CRAFT-PKG-09` | PKG-09 | shorts-for-video | manual | hypothesis | `creator or person does it; REVIEW only (no second source type yet)` | per-platform packs (TikTok, Instagram): limits not researched yet |
| `CRAFT-PKG-10` | PKG-10 | shorts-for-video | manual | hypothesis | `creator or person does it; REVIEW only (no second source type yet)` | nothing goes public without the creator's recorded approval |
| `CRAFT-SCR-01` | SCR-01 | narration-script | code | existing | `explainer_engine/scripting/register_lint.py` | no AI-register word over the density limit (delve, tapestry, testament to, ...) |
| `CRAFT-SCR-02` | SCR-02 | narration-script | critic (planned P8) | judgement | `v-hook-writing` | no structural AI tells: stacked triplets, sentence-initial 'Imagine', a rhetorical-question opener in every segment, em-dash chains, 'not just X but Y' |
| `CRAFT-SCR-03` | SCR-03 | narration-script | code (planned P3) | validator | `explainer_engine/validators/narration.py` | the twist sentence lands inside its estimated spoken length |
| `CRAFT-SCR-04` | SCR-04 | narration-script | code | existing | `explainer_engine/scripting/story_lint.py` | causal chain: THEREFORE / BUT joins, no AND-THEN chain |
| `CRAFT-SCR-05` | SCR-05 | narration-script | code | existing | `explainer_engine/scripting/scene_lint.py` | show, don't tell and full immersion (no trait statements, no meta disclaimers) |
| `CRAFT-SCR-06` | SCR-06 | narration-script | critic (planned P8) | judgement | `v-hook-writing` | no double exposition: the narration never describes what the picture already shows |
| `CRAFT-SCR-07` | SCR-07 | narration-script | code | existing | `explainer_engine/scripting/narration_lint.py` | sentences for the ear and spoken register |
| `CRAFT-SND-01` | SND-01 | editing-style | code | existing | `explainer_engine/audio/sound_director.py` | a continuous room-tone bed per scene inside the band; no cut falls to digital silence |
| `CRAFT-SND-02` | SND-02 | editing-style | code | existing | `explainer_engine/audio/sound_director.py` | J- or L-cut at every scene boundary inside its durations |
| `CRAFT-SND-03` | SND-03 | editing-style | code | existing | `explainer_engine/audio/sound_director.py` | music and ambience leave the voice's presence band while the narrator speaks (measured gap) |
| `CRAFT-SND-04` | SND-04 | editing-style | code | existing | `explainer_engine/audio/duck.py` | every duck is a dip inside BP-53's band |
| `CRAFT-SND-05` | SND-05 | editing-style | code | existing | `explainer_engine/audio/sound_director.py` | a major impact is a three-layer composite hit on the frame |
| `CRAFT-SND-06` | SND-06 | editing-style | code | existing | `explainer_engine/audio/sound_director.py` | an acoustic vacuum before each of the largest reveals, then the hit |
| `CRAFT-SND-07` | SND-07 | editing-style | code | existing | `explainer_engine/audio/layers.py` | at most two and a half sounds of one colour at once besides the voice (five when spread) |
| `CRAFT-SND-08` | SND-08 | editing-style | code | existing | `explainer_engine/production/assemble.py` | narration centred, music wide, a spot effect on its source's screen side within the pan range |
| `CRAFT-SND-09` | SND-09 | editing-style | critic (planned P8) | judgement | `v-design-sound` | encoded and embodied sound are balanced: never two encoded streams (narration over a hero line) at once |
| `CRAFT-SND-10` | SND-10 | editing-style | code | existing | `explainer_engine/audio/sound_director.py` | acoustic perspective follows the shot size; one impulse response per scene |
| `CRAFT-SND-11` | SND-11 | editing-style | critic (planned P8) | judgement | `v-design-sound` | one motif per faction, hero and channel; it returns when its owner acts |
| `CRAFT-SND-12` | SND-12 | editing-style | code | existing | `explainer_engine/audio/sound_director.py` | with music up, an action cut falls on the beat grid |
| `CRAFT-SND-13` | SND-13 | editing-style | code | existing | `explainer_engine/audio/layers.py` | music is spotted on scene or beat boundaries, with a planned no-music stretch |
| `CRAFT-SND-14` | SND-14 | editing-style | code | existing | `explainer_engine/qa/targets.py` | the delivered mix meets the loudness and true-peak gate |
| `CRAFT-VOX-01` | VOX-01 | elevenlabs-voice | code | existing | `explainer_engine/production/validate.py` | the heard pace sits in BP-01's band |
| `CRAFT-VOX-02` | VOX-02 | elevenlabs-voice | code | existing | `explainer_engine/audio/voice_audition.py` | every candidate voice has a measured profile from one test read |
| `CRAFT-VOX-03` | VOX-03 | elevenlabs-voice | code | existing | `explainer_engine/audio/voice_audition.py` | two cast voices differ by at least one measured margin |
| `CRAFT-VOX-04` | VOX-04 | elevenlabs-voice | manual | hypothesis | `creator or person does it; REVIEW only (no second source type yet)` | the creator picks the voice by ear from the top three |
| `CRAFT-VOX-05` | VOX-05 | elevenlabs-voice | critic (planned P8) | judgement | `v-elevenlabs-text-to-speech` | one stressed word per sentence; a tag only where the delivery changes |
| `CRAFT-VOX-06` | VOX-06 | elevenlabs-voice | code | existing | `explainer_engine/scripting/narration_lint.py` | no pause before a punch line; held pauses inside their limit |
| `CRAFT-VOX-07` | VOX-07 | elevenlabs-voice | manual | hypothesis | `creator or person does it; REVIEW only (no second source type yet)` | chunk size, carried context, pauses by tags and punctuation |
| `CRAFT-VOX-08` | VOX-08 | elevenlabs-voice | code | existing | `explainer_engine/audio/voice_check.py` | a new take matches the voice's baseline (no drift) |
| `CRAFT-VOX-09` | VOX-09 | elevenlabs-voice | critic (planned P8) | judgement | `v-elevenlabs-text-to-speech` | an animated shot's line carries delivery (pace, loudness, colour) and a face the lens sees |

## B. Other ids the archived skills cite (their canonical home is already a document; one row per id)

These ids are defined elsewhere (`docs/INDEX.md` lists the home). The archived skill only pointed at them, so the mapping is
the existing home; the last column names the archived skills that cite the id.

| Rule | Mapping | Home | Cited by |
|---|---|---|---|
| `AL-01` | existing | `docs/STORY_ENGINE.md` | video-editing-architect |
| `AV-01` | existing | `docs/EPISODE_FIRST.md` | editing-style |
| `AV-08` | existing | `docs/EPISODE_FIRST.md` | editing-style |
| `BP-04` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-07` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-12` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-20` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-21` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-22` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-23` | existing | `docs/SOURCED_RULES.md` | animation-principles, editing-style, video-editing-architect |
| `BP-24` | existing | `docs/SOURCED_RULES.md` | animation-principles, editing-style |
| `BP-25` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-26` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-27` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-28` | existing | `docs/SOURCED_RULES.md` | editing-style, shot-visuals, video-editing-architect |
| `BP-29` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-30` | existing | `docs/SOURCED_RULES.md` | editing-style, shot-visuals, video-editing-architect |
| `BP-31` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-34` | existing | `docs/SOURCED_RULES.md` | shot-visuals |
| `BP-35` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-38` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-40` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-41` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-50` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-52` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-53` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-54` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-56` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-59` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-60` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-61` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-62` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-66` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-84` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-85` | existing | `docs/SOURCED_RULES.md` | shot-visuals |
| `BP-90` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-91` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-92` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-93` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-94` | existing | `docs/SOURCED_RULES.md` | editing-style, video-editing-architect |
| `BP-100` | existing | `docs/SOURCED_RULES.md` | shot-visuals |
| `BP-103` | existing | `docs/SOURCED_RULES.md` | shot-visuals |
| `BP-107` | existing | `docs/SOURCED_RULES.md` | animation-principles |
| `BP-108` | existing | `docs/SOURCED_RULES.md` | animated-universe |
| `BP-109` | existing | `docs/SOURCED_RULES.md` | animation-principles |
| `BP-113` | existing | `docs/SOURCED_RULES.md` | animation-principles |
| `BP-116` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-117` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-118` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-119` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-120` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-121` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-122` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-123` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-126` | existing | `docs/SOURCED_RULES.md` | shot-visuals, video-editing-architect |
| `BP-127` | existing | `docs/SOURCED_RULES.md` | shot-visuals |
| `BP-128` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-129` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-130` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-131` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-132` | existing | `docs/SOURCED_RULES.md` | animation-principles |
| `BP-133` | existing | `docs/SOURCED_RULES.md` | animation-principles |
| `BP-134` | existing | `docs/SOURCED_RULES.md` | video-editing-architect |
| `BP-160` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-161` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-162` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-185` | existing | `docs/SOURCED_RULES.md` | shot-visuals |
| `BP-186` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-187` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `BP-188` | existing | `docs/SOURCED_RULES.md` | editing-style |
| `CS-01` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `CS-02` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `CS-05` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `CS-12` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `CT-06` | existing | `docs/SHOT_CONTINUITY.md` | shot-visuals |
| `ED-01` | existing | `docs/EDITING.md` | editing-style, video-editing-architect |
| `ED-02` | existing | `docs/EDITING.md` | editing-style, video-editing-architect |
| `ED-03` | existing | `docs/EDITING.md` | editing-style, video-editing-architect |
| `ED-04` | existing | `docs/EDITING.md` | video-editing-architect |
| `ED-06` | existing | `docs/EDITING.md` | editing-style |
| `ED-07` | existing | `docs/EDITING.md` | editing-style |
| `ED-08` | existing | `docs/EDITING.md` | video-editing-architect |
| `ED-09` | existing | `docs/EDITING.md` | editing-style, video-editing-architect |
| `ED-10` | existing | `docs/EDITING.md` | editing-style |
| `ED-11` | existing | `docs/EDITING.md` | editing-style |
| `ED-12` | existing | `docs/EDITING.md` | video-editing-architect |
| `ED-14` | existing | `docs/EDITING.md` | editing-style |
| `ED-15` | existing | `docs/EDITING.md` | video-editing-architect |
| `FS-05` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `GC-01` | existing | `docs/GEMINI_CONSISTENCY_RULES.md` | shot-visuals |
| `GC-17` | existing | `docs/GEMINI_CONSISTENCY_RULES.md` | shot-visuals |
| `ICW-02` | existing | `docs/CONTRACTS.md` | shot-visuals |
| `ICW-06` | existing | `docs/architecture/INK_CHRONICLE_OPUS_IMPLEMENTATION_ROADMAP_2026-11-04.md` | shot-visuals |
| `KP-01` | existing | `docs/SHOT_PROMPTS.md` | shot-visuals |
| `KP-12` | existing | `docs/SHOT_PROMPTS.md` | animation-principles |
| `KP-14` | existing | `docs/SHOT_PROMPTS.md` | shot-visuals |
| `KP-15` | existing | `docs/SHOT_PROMPTS.md` | shot-visuals |
| `KP-16` | existing | `docs/SHOT_PROMPTS.md` | animation-principles, video-editing-architect |
| `KP-29` | existing | `docs/SHOT_PROMPTS.md` | animation-principles, shot-visuals |
| `KP-33` | existing | `docs/SHOT_PROMPTS.md` | shot-visuals |
| `KP-34` | existing | `docs/SHOT_PROMPTS.md` | shot-visuals |
| `KP-43` | existing | `docs/SHOT_PROMPTS.md` | animation-principles |
| `LT-06` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-10` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-17` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-31` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-32` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-41` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-42` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-60` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `LT-79` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `MO-04` | existing | `docs/STORY_ENGINE.md` | editing-style |
| `OR-09` | existing | `docs/ORCHESTRATION.md` | editing-style |
| `OR-11` | existing | `docs/ORCHESTRATION.md` | animation-principles, editing-style, shot-visuals, video-editing-architect |
| `PV-04` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `PV-06` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `PV-07` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `PV-29` | existing | `docs/PRODUCTION_SCRIPT.md` | video-editing-architect |
| `PV-43` | existing | `docs/PRODUCTION_SCRIPT.md` | shot-visuals |
| `RN-05` | existing | `docs/EPISODE_FIRST.md` | editing-style |
| `RR-15` | existing | `docs/RIGHTS_AND_FAIR_USE.md` | shot-visuals |
| `RT-01` | existing | `docs/EPISODE_FIRST.md` | shot-visuals |
| `RT-04` | existing | `docs/EPISODE_FIRST.md` | editing-style |
| `RT-05` | existing | `docs/EPISODE_FIRST.md` | shot-visuals |
| `RT-06` | existing | `docs/EPISODE_FIRST.md` | shot-visuals |
| `RT-07` | existing | `docs/EPISODE_FIRST.md` | shot-visuals |
| `SD-01` | existing | `docs/AUDIO_SYSTEM.md` | editing-style |
| `SD-15` | existing | `docs/AUDIO_SYSTEM.md` | editing-style |
| `SP-02` | existing | `docs/EPISODE_FIRST.md` | editing-style |
| `UR-04` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-06` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-07` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-08` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-11` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-12` | existing | `docs/UNIVERSAL_RULE_BASE.md` | video-editing-architect |
| `UR-16` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-17` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-20` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-21` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-22` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-24` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-26` | existing | `docs/UNIVERSAL_RULE_BASE.md` | animated-universe |
| `UR-29` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-30` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `UR-31` | existing | `docs/UNIVERSAL_RULE_BASE.md` | shot-visuals |
| `VL-01` | existing | `docs/VIDEO_LANE.md` | editing-style, shot-visuals |
| `VL-13` | existing | `docs/VIDEO_LANE.md` | editing-style, shot-visuals |
| `VQ-01` | existing | `docs/LORA_TRAINING.md` | lora-training |
| `VQ-10` | existing | `docs/LORA_TRAINING.md` | animation-principles |
