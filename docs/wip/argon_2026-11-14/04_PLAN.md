Explainer Engine — End-to-End Production Plan (2026-11-14)

Self-contained engineering and film-production plan for Truce 1914 and repeatable future episodes (60 % LTX video / 30 % 2.5D living stills / 10 % helper visuals + ElevenLabs narration + 5-stem sound).

1. Verdict on the Current Approach (Judged Against the Code at 302c8dd)

What is fundamentally right: The episode-first stage contract (explainer_engine/episode/run.py:35, G1..G10 with SHA-256 input fingerprinting), the 60/30/10 visual mix (D-93), the word-spine clock (episode/timing.py + episode/events.py), the person-first LTX tail-frame selector and RealPLKSR upscaler (finish/frame_pick.py + finish/superres.py), and the Scene Director architecture (production/understand.py, direction.py, living_director.py, living.py) are architecturally sound.

What is fundamentally broken in code:

Split-brain codebase: episode/run.py:554, 643 still runs the legacy 4-plane Telea renderer (layers25d.py) and never invokes understand.py, living_director.py, or directed25d.py (PR #188).

Over-engineered, fragile 2.5D alpha surgery: directed25d.py:197-227 (_rest_background) uses morphological disc openings to cut "thin strokes" out of foreground masks and dilates holes by REST_ALPHA_GAIN = 6.0, creating scalloped seams at frame 0, while bg_maps (directed25d.py:590-604) warps unlayered crowd figures like rubber sheets.

Un-graded, un-bridged assembly: production/assemble.py:1484-1582 (assemble_shot_clips) skips finish/grade.py (transfer_to_key and grade) and LOOK (vignette + noise), concatenating raw LTX, 2.5D, and map clips with zero color matching or shared grain; edit/cinematic_transitions.py:138-163 has no map -> map transition rule; and episode/run.py:832 (stage_sound) silently falls back to unsplit narration when an LTX insert clip is absent, desyncing voice by 53.75 s.

Toothless QA: episode/run.py:45 sets GO_ON = (G.PASS, G.REVIEW) while qa/motion_intent.py:28-58 marks almost all perceptual defect detectors as REVIEW, allowing clips with seams, cropped people, blown skies, and 8-second static holds to pass automatically.

2. The 2.5D Lane (<= 5.0 s, Cut on Narrator Words)
2.1 Concrete Technique & Parameter Stack

Use the cached scene_layers/1 pipeline in explainer_engine/production/understand.py (free CPU, $0), simplified to eliminate mask-cutting seams and rubber-sheet face warping:

Depth: onnx-community/depth-anything-v2-small at 1848x1036 (understand.py:47, 16-bit PNG, no 3 px blur).

Segmentation: facebook/sam2.1-hiera-large (understand.py:41) from director/YuNet points, refined by ZhengPeng7/BiRefNet (understand.py:42) only in a 0.006 * W boundary band (FINE_BAND), with 4 px Gaussian alpha feathering inward (never morphological hole-biting inside the silhouette).

Inpainting: Carve/LaMa-ONNX (understand.py:43, 512x512 context tiles around HOLE_GROW = 0.006 * W dilated foreground masks).

Compositing Rule (Fixing directed25d.py:174-227 and 590-604):

Delete morphological stroke-biting (_rest_background lines 197–207). If an object has thin_share >= 0.35 (barbed wire, rifle sling) or is a crowd ("layer": false), keep it 100 % in the background plate (layer=False); otherwise keep the SAM+BiRefNet mask whole with a 3 px feathered alpha edge so frame 0 is bit-identical to the source photo (rest_seam == 0.0).

Flatten depth inside every detected face/body box on the background sheet: Before running bg_maps (directed25d.py:590), clamp self.bg_depth inside every detected person/face bounding box (padded by 1.5x width) to its median depth (grad(bg_depth) == 0 inside people), so unlayered crowd figures in S05_SH020 translate rigidly and never smear.

Continuous Camera Motion (BP-21 + BP-197): Never hold below 1.8 %/s before a word accent. Every still_25d shot > 5.0 s (S02_SH008 10.96 s, S08_SH002 9.75 s, S05_SH020 7.83 s) must be split on the midpoint sentence/clause boundary into two <= 5.0 s shots (using a 1.35x focal crop or second angle for part B) or routed to LTX.

Screen-Blended Atmosphere: Keep LFX.screen (living_fx.py:40, LIGHT_CEIL = 0.55, SHAFT_CEIL = 0.70, PEOPLE_SHIELD = 0.85) and sub-pixel tile scrolling (_tile_smooth, directed25d.py:876).

2.2 Minimal Free CPU Recipe per Shot Type

Shot Type

	

Layering (understand.py)

	

Camera Move (directed25d.py)

	

Living Effects (living_fx.py, 3–4 active)

	

Guardrails




1. Landscape (S01_SH001, S05_SH016)

	

Continuous depth-warped background (BG_SMOOTH = 0.008); thin wire stays in BG (layer=False); max 1 rigid midground prop (spades).

	

Multi-plane crane up or truck (NEAR_TRAVEL = 0.05, far_share = 0.15, 2.0–3.0 %/s), easing into key noun.

	

1) Two-bank sub-pixel mist (40/65 px/s), 2) sun_shaft (SHAFT_GAIN = 0.85, +-6 deg sway, screen blend), 3) cloud_drift light sweep (30 px/s), 4) grouped brazier glow / smoke.

	

blown_share <= 0.005; unfold max slope <= 0.5 px/px.




2. Group of People (S05_SH020, S02_SH008, S06_SH001)

	

Max 2 primary foreground heroes as SAM+BiRefNet RGBA layers; crowd stays on BG with depth flattened per person box (grad=0).

	

Base push (1.8 %/s) toward Speaker A -> word-timed truck (TRUCK_STRENGTH = 2.0, ease_out, 1.25 s) to Group B on trigger word + handheld (0.25).

	

1) Cold breath plumes from YuNet mouth coordinates (period_s = 3.6), 2) 3-layer depth-occluded snow or mist, 3) fire/candle warm spill on faces, 4) embers / smoke.

	

people_in_frame safe margin 2 %; split shot if duration > 5.0 s.




3. Close Face / Portrait

	

Hero as 1 rigid RGBA layer (uniform median depth d_hero) over LaMa-inpainted background plate (HOLE_GROW = 0.006).

	

Slow targeted push (1.5–2.2 %/s) + subtle orbit (ox = 0.025) around focus_d = d_hero + rack_focus (RACK_SIGMA_PX = 5.0 on BG) + handheld (0.3).

	

1) subject_sway (0.25 deg rigid breath), 2) mouth breath plume, 3) warm rim/fire spill on cheek, 4) far-layer snow/dust behind d_hero only (layers=[0]).

	

face_likeness >= 0.92; zero particles in front of face (layers=[0]).




4. Object / Insert (S08_SH002 hands+photo+candle)

	

Foreground hands/object as 1 rigid RGBA layer (d_obj); background trench blurred (RACK_SIGMA_PX = 6.0).

	

handheld breathing (0.35) + slow targeted push (1.5 %/s) to named detail (button / photo) on spoken word, keeping secondary light in soft safe-zone.

	

1) candle flame tip deformation (_deform_flame) + warm spill across hands/photo, 2) dust motes lit by candle, 3) heat_haze above flame, 4) breath entering from bottom edge.

	

keep_in_frame keeps object 100 % inside frame and candle >= 95 % inside.

3. Maps (10 % Helper Lane) & Scene-Level Alignment
3.1 Rich, Readable Animated Maps & Smooth Map-to-Map Transitions

Historical Base Plate (maps/plate.py:25): Default layers=("land", "lakes", "rivers") when historical_period.start_year < 1945 (map_look.borders = False), eliminating modern 2026 borders on 1914 Flanders while keeping shaded_relief=True (Natural Earth SR_HR) + paper grain (grain = 0.03). Enforce MIN_SPAN_KM = 250.0 so ne50m relief never blurs (upsample <= 2.5), or draw a styled tactical trench card when span_km < 150.

Continuous Map Camera & Map-to-Map Handoff (maps/actions.py:167, 215 & edit/cinematic_transitions.py:138):

Camera inheritance: When shot k and shot k-1 are both map_action in the same theater, set shot[k].view0 = camera(plan[k-1], frames[k-1] - 1) so S02_SH002 starts at the exact (lon, lat, span_km) where S02_SH001 ended, then pans/zooms (route_pan, fly_to, or scale) to the new action.

Transition rule: In edit/cinematic_transitions.py:138, add an explicit branch elif is_a_infographic and is_b_infographic: that selects cross_dissolve_8f (8 frames) if both are same-theater maps with inherited camera, or 12 frames with a paper-slide foley bridge if switching between a map and a data card.

Remove the 18-frame freeze (maps/actions.py:48-52): Replace fixed ANIM_FRAMES = 18 with word-span duration (ev["end_frame"] - ev["start_frame"], minimum 36 frames / 1.5 s), and allow route_pan / scale even when DENSE_ACTIONS >= 4.

8-Position Label & Chip Collision Solver (maps/actions.py:472-478):

Replace the fixed (cx + 0.35*size, cy - 0.35*size) offset with an 8-candidate greedy bounding-box placement (NE, NW, SE, SW, E, W, N, S at radii 0.45*size and 0.90*size), penalizing overlap with existing labels, drawn routes/front-lines, and a 5 % frame-edge safe zone (0.05*W .. 0.95*W, 0.06*H .. 0.94*H). Draw a thin leader line when using the outer ring.

3.2 Per-Scene Alignment of Narration, Text on Screen, Sound & Theme

Every shot is governed by one unified av_events/2 timeline (episode/events.py + production/living_director.py) anchored to the measured ElevenLabs Scribe word spine (audio/timing.json):

Word -> Visual Beat (BP-195): Camera accents (push/truck/fly_to), map action starts (at_word), and on-screen text/counters trigger within [-0.15 s, +0.25 s] (-4 to +6 frames at 24 fps) of the spoken word's start_frame.

Visual Beat -> Sound Event (BP-54, BP-192, VL-18): Every visible motion on a map, counter, or 2.5D shot gets a period-authentic foley/spot cue from living_director.choose_sound:

route_arrow / front_line (when cues != "none") -> map_route_draw (charcoal/pencil on paper, span).

front_line with cues: "none" -> drawn at frame 0 (stands=True), silent (0 draw sound).

label / date chip -> period stamp / typewriter / ov_slide (onset, foley layer so BP-81 UI-cue budget is untouched).

counter -> tick train decelerating with the easing curve + final low ov_thud knock on the exact frame the number lands (timed_script frame, never untimed).

marker_travel (army token) -> distant army_march (span, panned to token x).

4. End-to-End Assembly Recipe & Module Disposition
4.1 Assembly Order & Technical Recipe

Stage 1 — Voice & Word Spine (G6, episode/run.py:stage_voice): Polish narrator read via audio/narrator_polish.py (POLISHED_REL, verifying |len_after - len_before| <= 1/30 s), align Scribe word timestamps (TM.align_read), and splice LTX character dialogue inserts (VV.compose). Hard Rule: In episode/run.py:831, if missing LTX insert clips exist, raise ContractError (unless --rehearsal, where silent padding of exact insert duration is inserted)—never fall back to the unsplit read.

Stage 2 — Understand & Direct (G6.5, new stage direction in episode/run.py): Run understand.build on all 24 still_25d photos (cached in <pic>.layers/), then run living_director.direct on all still_25d and map_action shots to produce production/direction/<shot_id>.json and merge into production/av_events.json.

Stage 3 — Clip Rendering & Ingest (G7, episode/run.py:stage_clips):

60 % LTX (video): Ingest QA'd 1280x704 clips via videolane/ingest.py (VI.recut from raw clip with handles, HF-4 true-peak limiter at -1.0 dBTP, muting clip audio on non-speaking shots where Whisper detected stray hallucinations like "You" in S07_SH008).

30 % 2.5D (still_25d): Render at 1920x1080 24 fps via directed25d.render_clip (called from layers25d.render_clip when direction/<sid>.json exists).

10 % Helpers (map_action): Render at 1920x1080 24 fps via map_clip.render_action_map_clip with camera inheritance and label collision avoidance.

Stage 4 — Scene-Key Color Matching & Unified Film Finish (G9, production/assemble.py:1535-1550):

Group shots by segment_id / scene. Designate each scene's first anchor photo (<sid>_start) as key_master_frame.

Inside assemble_shot_clips, compute params = grade_mod.transfer_params(boundary_frames, key_master_frame) once per shot (preventing intra-shot flicker) and apply Reinhard LAB color transfer (grade_mod.apply_transfer(x, params, blend=0.50) for LTX and 2.5D shots; blend=0.20 for maps), followed by the episode's era LUT (grade_mod.grade(x, look, seed=global_frame_idx)) and FFmpeg's subtle film finish (vignette=PI/6,noise=alls=1.5:allf=t).

Stage 5 — Cut & Transition Execution (edit/cinematic_transitions.py + production/assemble.py):

Compute compute_visual_continuity_alignment from the actual rendered camera vector (record["camera"]), not stale camera_spec text.

Same scene / location (video <-> 2.5D): Hard cut (0 blend frames) on the spoken word onset ([-4, +6] frames), bridged by a 0.25–0.35 s J/L audio overlap. If both shots have aligned camera motion (dot > 0.5), ease outgoing speed to match incoming speed over the last 8 frames.

Scene <-> Map: cross_dissolve_8f (scene -> map) and map_to_location_zoom_through (14 frames, map -> scene) with 0.35–0.50 s audio prelap.

Map <-> Map: cross_dissolve_8f with inherited camera state (lon, lat, span_km).

Segment change: cross_dissolve_8f (0.45 s audio bridge); End card (S08_SH004): fade_to_black (24 frames).

Stage 6 — 5-Stem Audio Mix & Loudness Normalization (G8, episode/cue_sheet.py + audio/stems.py + qa/targets.py):

5 Stems: narration (Priority 1, mono centered, high-passed at 80 Hz, -16 LUFS speech anchor), spot / foley (Priority 2/3, -26 / -30 dBFS RMS, panned from mask x via pan = (cx - 0.5) * 1.2, distance LPF 9 kHz medium / 4.5 kHz distant), music (Priority 4, -32 dBFS, 2.0 s equal-power crossfades, ducked under voice + 2.5 kHz presence dip), ambience + room_tone (Priority 5, -36 dBFS bed / -54 dBFS room floor, widened stereo with corr in [0.05, 0.65] from TD-342, 0.5 s equal-power crossfade across scene cuts so bed jumps stay <= 3.0 dB).

Master Target (BP-50): Two-pass ffmpeg loudnorm via qa/targets.normalise_file to -14.0 LUFS integrated (pass band -15.0 .. -13.0 LUFS), -1.0 dBTP true peak ceiling, 48 kHz stereo AAC-LC 192 kbps.

4.2 Existing Modules: Keep, Fix, or Drop

Action

	

Modules

	

Exact Reason




KEEP

	

episode/timing.py, episode/events.py, finish/frame_pick.py, finish/superres.py, finish/grade.py, audio/narrator_polish.py, audio/duck.py, qa/targets.py, videolane/ingest.py, episode/helper_fit.py (PR #190)

	

Proven, deterministic, tested modules that solve word timing, tail-frame selection, RealPLKSR upscaling, LAB grading, and EBU R128 loudness.




FIX

	

episode/run.py, production/directed25d.py, production/living_director.py, production/understand.py, production/assemble.py, edit/cinematic_transitions.py, maps/actions.py, maps/plate.py, episode/cue_sheet.py, audio/acoustics.py (TD-342), qa/motion_intent.py, videolane/master_qa.py

	

Wire understand + living_director + directed25d into run.py; fix alpha hole-biting & crowd depth warp in directed25d.py; wire LAB grading into assemble_shot_clips; fix silent voice fallback in run.py:832; add map-to-map transitions, label collision, and borders=False in maps/; promote critical QA rows from REVIEW to FAIL.




DROP / RETIRE

	

explainer_engine/blender/* (J5 era), production/parallax.py, production/cinematic_image_animator.py, edit/clay_video.py, finish/upscale.py (plain Lanczos), maps/render.py (legacy Toba/Waterloo path)

	

Superseded by directed25d.py, finish/superres.py, and maps/actions.py; keeping them active causes route confusion.

5. QA That Matches the Human Eye (8 Automated Checks)

Promote these 8 checks in qa/motion_intent.py, production/map_clip.py, and videolane/master_qa.py so any FAIL blocks G7/G8/G10 (no silent REVIEW pass-through on visual or sync defects):

#

	

Check Name & Target Defect

	

How It Is Measured (Deterministic Python / OpenCV / FFmpeg)

	

Starting Threshold (FAIL / REVIEW)




1

	

rest_seam_and_halo (Scalloped outlines / cut posts at frame 0)

	

On frame 0 of every still_25d clip (before effects), compute `max_c

	

frame0_no_fx - src_crop




2

	

sliding_1s_liveliness (Static / dead seconds inside 2.5D or map clips)

	

Decode clip at 960x540 gray. For every sliding 1.0 s window (24 frames), compute the fraction of pixels where `

	

I(t+24) - I(t)




3

	

border_stretch_and_reveal (Stretched edges, Telea/LaMa smears, invented wire loops)

	

Measure (a) distance transform of newly disoccluded fill pixels (qa/motion_intent.py:157), (b) Canny edge density ratio inside_fill / outer_ring (invented_detail, line 216), and (c) boundary gradient correlation along the outer 8 px border vs 16 px inward (catches BORDER_REPLICATE / BORDER_REFLECT smearing).

	

FAIL if share_wide > 3.5 % or band_px > 45 px or invent_ratio > 1.8 or border-stretch correlation > 0.85; REVIEW above 2.0 % / 30 px / 1.5 (hypothesis).




4

	

people_and_chips_safe_zone (Cropped soldiers, boots, candle dishes, map date chips)

	

For every live face/person box in keep_in_frame (directed25d.py:543) and every map text/chip bounding box (maps/actions.py), compute the fraction of the box outside [0.015*W, 0.985*W] x [0.015*H, 0.985*H] across all frames.

	

FAIL > 0.005 (0.5 % of any kept person or map label/chip cut by frame edge); REVIEW > 0.0 on soft light sources (binding owner rule).




5

	

face_rigidity_and_sharpness (Smeared faces in S06, blurred photo in S08)

	

Track each kept face/target across frames with camera affine removed (directed25d.py:534): measure (a) normalized cross-correlation TM_CCOEFF_NORMED against frame 0 (face_likeness), and (b) final-to-initial Laplacian variance ratio inside the focus target (target_sharpness).

	

FAIL if face_likeness < 0.88 or target_sharpness_ratio < 0.45; REVIEW < 0.92 or < 0.60 (calibrated on smeared S06 0.80 vs intact 0.96–0.99).




6

	

highlight_burn_and_clipping (Blown-out white sky in S01/S05, bleached heads)

	

Measure blown_share(frame) - blown_share(src_crop) where a pixel is blown if luma >= 245 and local 9x9 std < 2.0 (directed25d.py:508), plus mean luma rise on people_field.

	

FAIL if newly blown area > 0.015 (1.5 % of frame) or person-head luma rise > 18.0 levels; REVIEW > 0.005 (0.5 %) (calibrated on C5 burn 10–13 % vs fixed 0.0–0.3 %).




7

	

cross_shot_grade_and_cut_continuity (Jarring cuts between LTX, 2.5D, and maps)

	

Across every cut (shot_a, shot_b) within the same scene in videolane/master_qa.py, measure CIE LAB Euclidean mean distance lab_distance(last_frame_a, first_frame_b) (finish/grade.py:73) and optical-flow velocity jump at hard cuts.

	

FAIL if same-scene lab_distance > 12.0 (after scene-key transfer) or any black/frozen run >= 6 frames (BP-164); REVIEW if lab_distance > 8.0 (hypothesis).




8

	

per_shot_asr_and_onset_sync (Wrong narration under S05 maps, early counter knock, bed jumps)

	

Run Whisper (faster-whisper base/small) on each shot's slice of audio/stems/narration.wav (or mix_delivered.wav) and compute word overlap with shot["audio_line_ids"]; check SFX onset (cue_sheet.py:152) vs visual event frame (BP-54) and ambience step across cuts (BP-191).

	

FAIL if per-shot word recall < 0.80 (catches INC-MAP-1 54 s offset immediately), or SFX onset outside [-45 ms, +125 ms], or master outside [-15.0, -13.0] LUFS / > -1.0 dBTP; REVIEW if bed cut step > 3.0 dB.

6. Ordered Execution Plan (8 Steps)

Step

	

Goal

	

Files Touched

	

Cost (Free / Paid)

	

Done-When (Verification Criteria)




1

	

Unify branch state & fix stage_sound silent voice desync + TD-342 stereo bed anti-phase

	

explainer_engine/episode/run.py (stage_sound line 831), explainer_engine/audio/acoustics.py (widen_best), tests/unit/test_bed_stereo_and_loop_window.py, tests/unit/test_v43_runner.py

	

Free ($0, CPU)

	

stage_sound raises ContractError if an LTX insert clip is missing (or pads exact insert silence in --rehearsal); BED_16/BED_17 stereo correlation in [0.03, 0.61] with mono loss <= 2.9 dB; unit tests pass.




2

	

Fix directed25d.py seam & crowd-warp bugs and promote 2.5D perceptual QA to FAIL

	

explainer_engine/production/directed25d.py (_rest_background, bg_maps), explainer_engine/production/living_director.py (choose_camera), explainer_engine/qa/motion_intent.py

	

Free ($0, CPU)

	

Morphological hole-biting removed (rest_seam <= 0.02 on all 6 test photos); background depth flattened inside all detected person boxes (face_likeness >= 0.92 on S05_SH020 and S06); base camera rate >= 1.8 %/s; Checks 1–6 active as FAIL gates.




3

	

Split or re-route the > 5.0 s 2.5D shots (BP-109) and wire understand + living_director + directed25d into episode/run.py

	

episodes/ep_truce_1914/story/production_script.json (split long still_25d shots on clause boundaries into <= 5.0 s sub-shots with focal re-framing), explainer_engine/episode/run.py (stage_clips), explainer_engine/production/layers25d.py

	

Free ($0, CPU) (or ~$0.21 paid on Modal H100 ONLY if creator chooses LTX instead of splitting for 3 shots)

	

Every still_25d shot in ep_truce_1914 has target_duration_seconds <= 5.0; episode run --stage clips runs understand -> living_director -> directed25d and all 2.5D shots pass Checks 1–6 with 0 FAIL.




4

	

Upgrade the 10 % Map & Helper lane (no modern borders, label collision solver, continuous camera, map-to-map transitions)

	

explainer_engine/maps/plate.py, explainer_engine/maps/actions.py, explainer_engine/production/map_clip.py, explainer_engine/edit/cinematic_transitions.py, explainer_engine/episode/helper_fit.py (from PR #190)

	

Free ($0, CPU)

	

borders=False on 1914 plates; 0 label/chip collisions or edge cuts across all 5 Truce maps; S02_SH001->002->003 and S05_SH001->002 inherit camera (lon, lat, span_km) and use cross_dissolve_8f; S02_SH001 ("over by Christmas") includes timeline progress bar.




5

	

Align scene audio, map foley, and LTX tail-frame hand-over (VL-16..18)

	

explainer_engine/production/living_director.py (choose_sound, sound_of_map), explainer_engine/episode/cue_sheet.py (mask-based pan, 0.5 s bed crossfades), explainer_engine/finish/frame_pick.py -> training/pods/ltx/modal_ltx_jobs.py

	

Free ($0, CPU) with existing library + BP-57 pitch/gain jitter (optional ~$0.15 ElevenLabs SFX only if creator wants new stamp/typewriter/pin takes)

	

Counter ticks + final knock land within +-1 frame of visual counter completion on timed_script; cues: "none" lines draw at frame 0 silently; LTX silent-shot hallucinations (S07_SH008, S04_SH005) muted at G8; CLIP-06 true-peak trim applied to S07_SH005 and S02_SH006.




6

	

Wire Scene-Key LAB Color Matching, Era Grade, and Film Finish into assemble_shot_clips (G9)

	

explainer_engine/production/assemble.py (assemble_shot_clips, lines 1484–1582), explainer_engine/edit/cinematic_transitions.py (compute_visual_continuity_alignment), tests/unit/test_assemble_v2.py

	

Free ($0, CPU)

	

assemble_shot_clips applies per-shot Reinhard LAB transfer (finish/grade.py) toward each scene's anchor frame + era LUT + subtle film grain/vignette; cinematic_transitions.py reads rendered camera vectors from shot_records.json; cross-cut lab_distance <= 12.0.




7

	

Add Per-Shot ASR & Perceptual Master QA (G10) and Render Full ep_truce_1914 Master

	

explainer_engine/videolane/master_qa.py, explainer_engine/episode/acceptance.py, explainer_engine/episode/run.py (stage_qa)

	

Free ($0, CPU, ~35 min render)

	

python -m explainer_engine.episode run episodes/ep_truce_1914 --to qa completes with 0 FAIL across all 8 perceptual/sync checks; contact sheet and side-by-side diagnostic strip generated.




8

	

Lock Repeatable Episode Template for Next Videos

	

docs/EPISODE_FIRST.md, docs/MAIN_METHOD.md, explainer_engine/standards/sourced_rules.json, docs/PROGRESS.md

	

Free ($0)

	

python -m explainer_engine.docs_lint returns 0 findings; full pytest suite passes; next episode requires only episode.json + production_script.json + anchor photos + 1 LTX wave run.