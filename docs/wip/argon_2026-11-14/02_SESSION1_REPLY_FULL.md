I've compiled your self-contained KNOWLEDGE_BASE.md, PLAN.md, and recipe_25d_and_qa_sketches.py in Canvas, along with the full audit and 8-step production plan below.

Knowledge Base
Export
Explainer Engine — External & Internal Production Knowledge Base (2026-11-14)

Self-contained technical reference compiled for the Explainer Engine pipeline (vano1919/explainer-engine, head 302c8dd / PR #188 + open PRs #184–#191). Built to hand directly to fresh engineering and review sessions (Argon / Gemini and Claude Opus) without requiring external re-discovery.

1. 2.5D / Parallax "Living Photo" Lane (30 % Runtime Share, <= 5.0 s per Shot)
1.1 Proven Open-Source Techniques & Papers

Layered Depth Image (LDI) & Context-Aware Disocclusion Inpainting: Shih et al. (CVPR 2020), 3D Photography using Context-aware Layered Depth Inpainting (vt-vl-lab/3d-photo-inpainting) (arXiv:2004.04727), proves that naive single-sheet depth warping either tears holes or rubber-stretches foreground edges across disocclusions, while diffusion/Telea smoothing blurs texture. The production fix is explicit depth discontinuity splitting + structural background inpainting behind foreground silhouettes before projecting camera motion.

3D Ken Burns with Semantic Depth Adjustment: Niklaus et al. (ACM TOG 2019), 3D Ken Burns Effect from a Single Image (sniklaus/3d-ken-burns) (Paper Summary), establishes two mandatory rules for human/character shots: (1) semantic instances (people, faces, rigid foreground props) must be assigned a flat, uniform depth plane so faces and bodies never warp internally, and (2) the virtual camera path must solve a boundary constraint so the crop frustum never crosses image borders or bisects heads/bodies.

Monocular Depth Estimation: Yang et al. (NeurIPS 2024), Depth Anything V2 (DepthAnything/Depth-Anything-V2) (NeurIPS 2024 Paper), trained on synthetic data for sharp boundary preservation and pseudo-labeled real images. For CPU production, onnx-community/depth-anything-v2-small at 1848x1036 (4x the repo's old 924x518 input) runs in ~9.7 s on 4 vCPU without GPU requirements. For surface normals + metric FOV when 2.5D relighting is needed, Microsoft MoGe (microsoft/MoGe) and Depth Anything 3 (ByteDance-Seed/Depth-Anything-3) are already wired in explainer_engine/production/understand.py:36-44.

Instance Segmentation & High-Resolution Edge Matting: Ravi et al., Segment Anything Model 2 (facebookresearch/sam2), provides point-prompted object masks (facebook/sam2.1-hiera-large), paired with BiRefNet (ZhengPeng7/BiRefNet) inside a narrow edge band (FINE_BAND = 0.006 in understand.py:52) for rifle barrels, spades, and coat rims.

Disocclusion Inpainting: Suvorov et al. (WACV 2022), LaMa: Resolution-robust Large Mask Inpainting with Fourier Convolutions (advimman/lama), uses Fast Fourier Convolutions (Carve/LaMa-ONNX 512 px tiles in understand.py:43, 50) to continue periodic background structures (trench planks, horizon lines, snowbanks) across disocclusion holes where OpenCV cv2.inpaint(..., cv2.INPAINT_TELEA) produces blurry streaks.

Shader vs. CPU Multiplane Rendering: DepthFlow (BrokenSource/DepthFlow) and ComfyUI-Depthflow-Nodes (akatz-ai/ComfyUI-Depthflow-Nodes) use ray-marched GLSL shaders for continuous depth parallax, DOF, and vignette, but require an active EGL/OpenGL GPU context (unavailable in headless CPU containers). In CPU-only containers, a 2-to-3 layer multiplane decomposition (continuous gently-smoothed background sheet + 1–2 rigid foreground RGBA cutouts with feathered alpha + depth-occluded particle/light layers) achieves the same parallax without ray-marching artifacts.

1.2 Why Our Repo's Two 2.5D Renderers Fail Today (Code Evidence)

Module & Lines

	

Defect Observed by Creator

	

Exact Root Cause in Code




explainer_engine/episode/run.py:554, 643

	

New P1 2.5D work never appears in episode runs

	

stage_clips imports layers25d as L25 and calls L25.render_clip(...). understand.py, direction.py, living_director.py, and directed25d.py are completely unwired from episode/run.py.




explainer_engine/production/depth.py:25-27

	

Soft edges, smeared silhouettes in layers25d.py

	

INPUT_SIZE = (924, 518), MAP_SIZE = (576, 324), SOFTEN = 3.0 downsamples and blurs the depth map before plane slicing.




explainer_engine/production/layers25d.py:82, 298-301, 692-697

	

"Just a zoom", stepping mist, Telea smears

	

PLANES = 4 slices k-means slabs regardless of objects; push/pull only scale around the frame center (src_w / 2); _tile_at uses integer int(round(ox * tw)) % tw with np.roll, stepping 7 px at a time.




explainer_engine/production/directed25d.py:74-82, 197-227

	

Wavy/scalloped outlines around people and hands at frame 0

	

_rest_background runs morphological opening (THIN_FILL_PX = 16.0) on SAM masks, cuts removed pieces out of the foreground layer, and dilates A by REST_ALPHA_GAIN = 6.0 and REST_GROW_PX = 3.0, exposing the LaMa plate along coat/hair boundaries even at rest.




explainer_engine/production/directed25d.py:590-604

	

Smeared/warped faces in crowds (S05_SH020, S06)

	

bg_maps warps the background per-pixel (cv2.remap over 3 iterations). Any person not isolated into self.objects (e.g. crowd figures with "layer": false) is stretched by the background depth gradient.




explainer_engine/production/living_director.py:45, 413

	

Clips stand static for 5–8 s before moving

	

When a shot has a late trigger word (targets), choose_camera sets the pre-word base move to RATE_MIN (0.5 %/s), which is imperceptible, and 12 of 24 Truce still_25d shots exceed the <= 5.0 s cap (BP-109).




explainer_engine/production/directed25d.py:62-64, 797-802

	

Weak effects in C4A, then blown-out white sky in C5

	

C4A used SHAFT_GAIN = 0.40; C5 multiplied by 2.5x with additive blending (rgb + colour*amount), clipping 10–13 % of pale skies to flat white (luma >= 245). Commit 302c8dd switched to LFX.screen (SHAFT_CEIL = 0.7, LIGHT_CEIL = 0.55).

2. LTX 60 % Video Lane & Hand-Over Continuity
2.1 Proven Workflow & Code State

Anchor-Plus-Chain Architecture (VL-14..VL-17): Only anchor keyframes are generated upfront in 2K (2752x1536) via Gemini (config/picture_route.json). Before writing any LTX prompt or continuation, the director inspects the actual start image (photo_visual_layer.json, DR-27 / VL-17) to record hand/prop occupancy (which hand holds the rifle/revolver, ground footing, gaze direction) and never uses negative prompt instructions ("does not step down" fails in LTX-2.5; always prompt the positive action).

Person-First Tail Frame Selection (BP-199): Implemented in explainer_engine/finish/frame_pick.py:16-55 using OpenCV YuNet (opencv/face_detection_yunet, MIT). Evaluates the last 1.5 s (36 frames at 24 fps, after speech_floor) and ranks frames by W_FACE (0.6) * (sharp - change - jitter) + W_BODY (0.3) * (-change) + W_FRAME (0.1) * (sharp - change). Gap to fix: training/pods/ltx/modal_ltx_jobs.py (handover_scores) still uses the old 0.75 s whole-frame score and must call finish/frame_pick.py.

Detail-Preserving CPU Upscale (BP-198): Implemented in explainer_engine/finish/superres.py:41-59 using Phips/4xNomos2_realplksr_dysample (RealPLKSR, CC-BY-4.0) with Phips/2xNomosUni_span_multijpg (SPAN) fallback and wavelet color fix, verified to retain 2K texture where Real-ESRGAN x2plus smoothed freckles and cloth grain.

3. Maps & 10 % Helper Visuals Lane
3.1 Proven Cartographic & Motion Graphics Standards

Programmatic Camera & Easing: Manim Community (ManimCommunity/manim) (Deep Dive Internals) and documentary map channels (Johnny Harris, Kings and Generals, Imperial) never cut between two static map crops of the same theater. They maintain a persistent camera state (lon, lat, span_km) across consecutive map beats, interpolating smoothly in log-scale span (math.exp(lerp(log(span_a), log(span_b), u))) while drawing progressive splines (Catmull-Rom splines) synchronized to spoken words.

Logical Helper Variety (MA-09, PR #190): Implemented in explainer_engine/episode/helper_fit.py (PR #190 diff). The 10 % lane must select its form from the spoken claim: map for geography/movement (route_arrow, front_line, marker_travel), progress bar / milestone for time spans ("over by Christmas", "almost four more years"), counter for headcount/casualty claims ("100,000 men", tied to claim_map.md), and bar_grow / split_compare for force ratios.

3.2 Why Our Maps Fail Today (Code Evidence)

Anachronistic Modern Borders (maps/plate.py:25): LAYERS = ("land", "lakes", "rivers", "borders") draws modern Natural Earth borders (ne50m.json.gz) on 1914 Europe. Fix: add borders: false default for historical eras in plate.py unless an era-verified border polygon is loaded.

Map-to-Map Hard Cut Jump (edit/cinematic_transitions.py:138-163 & maps/actions.py:167-182):

select_optimal_cinematic_transition handles map -> scene (line 138) and scene -> map (line 149), but omits is_a_infographic and is_b_infographic (map -> map), dropping into else: hard_cut_with_jl_bridge (0 transition frames)!

maps/actions.py:167 (_first_view) computes each map shot's starting camera independently from its own actions rather than inheriting prev_map_shot.end_view. Consecutive map shots (S02_SH001 -> S02_SH002 -> S02_SH003, S05_SH001 -> S05_SH002) jump violently in zoom and center.

Frozen Hold After 18 Frames (maps/actions.py:48-52, 223): ANIM_FRAMES = 18 finishes drawing an action in 0.75 s and freezes; DENSE_ACTIONS = 4 disables camera moves (push, route_pan, fly_to) whenever 4+ place actions exist.

Label Collisions & Cropped Chips (maps/actions.py:472-478): Labels draw at a fixed (cx + size*0.35, cy - size*0.35) with no bounding-box collision resolver and no safe-frame margin check (causing the S02_SH002 date chip to drift off the top edge).

4. Assembly, Color Matching, Pacing & Sound Design
4.1 Proven Techniques for Mixing AI Video + Animated Stills + Maps

Scene-Consistent Color Transfer (Reinhard LAB + Histogram Matching): Reinhard et al. (2001), Color Transfer between Images (chia56028/Color-Transfer-between-Images) (Theory & LAB Normalization), and scikit-image match_histograms unify disparate visual sources (LTX H100 video vs. Gemini 2K still vs. Python relief map) by matching CIE L
∗
a
∗
b
∗
 mean/std toward the scene's key anchor frame (blend <= 0.65), followed by a single unified film grain and vignette pass (vignette=PI/5,noise=alls=2:allf=t in FFmpeg Filters Documentation) after compositing all clips.

Documentary Pacing, Radio Edit & J/L Cuts: As documented in 10 Video Production Best Practices for Creators in 2026 (LesFM) and Stop AV Drift: Crossfade Editing with an FFmpeg Recipe (SoundBridge), top documentary/explainer channels (Kurzgesagt, Johnny Harris, Kings and Generals) build the radio edit (voice + word spine) first, cut visual beats on spoken nouns/verbs (-120 ms to +250 ms of word onset), and bridge every hard visual cut with a 250–450 ms J/L audio overlap (audio_j_cut_prelap_sec) plus continuous scene room tone/ambience so the ear never hears a splice.

Two-Pass EBU R128 Loudness Normalization: Per Two-pass loudness normalization with FFmpeg loudnorm and FFmpeg loudnorm Filter: EBU R128 Guide, single-pass loudnorm pumps background beds; two-pass linear loudnorm (-14.0 LUFS integrated for YouTube master, -1.0 dBTP true peak ceiling, dialogue anchor -16 LUFS, bed -36 dBFS RMS, music ducked via sidechain + 2.5 kHz presence-band dip) guarantees broadcast-clean clarity.

4.2 Critical Assembly Bugs in Our Code Today

Silent Voice Desync Fallback (explainer_engine/episode/run.py:821-838): In stage_sound, VV.compose splits the narration around LTX dialogue inserts only if not missing: (line 832). If even one LTX clip record is missing in a test worktree, stage_sound silently uses the unsplit narration_polished.wav (268.1 s) over the 379.8 s insert-expanded timeline—causing a 53.75 s voice desync in S05 and 83 s in S06 (INC-MAP-1).

Episode-First Assembler Bypasses Grading & Film Look (explainer_engine/production/assemble.py:1484-1582): While legacy iter_video_frames (lines 778–815) runs grade_mod.apply_transfer (finish/grade.py:98) and grade_mod.grade (finish/grade.py:17), the active v4.3 assemble_shot_clips (line 1546) only calls fr = _fit(raw, size)! It applies zero LAB color matching, zero era grade, and zero shared grain/vignette across LTX, 2.5D, and map clips.

Transition Continuity Reads Stale Text Instead of Rendered Motion (explainer_engine/edit/cinematic_transitions.py:64-72): compute_visual_continuity_alignment reads shot_a.get("camera_spec").get("camera_move") (Stage A text) instead of the actual camera track rendered in G7 (motion_imitation / shot_direction).

5. Perceptual QA That Matches the Human Eye
5.1 Proven Perceptual Video QA Metrics & References

Temporal Freeze, Black Frame & Boundary Jump Detection: Temporal and Spatial Features for Video Quality Assessment (TestDevLab), FFmpeg blackdetect Filter Guide, and Video Quality Assessment Survey (taco-group/Video-Quality-Assessment-A-Comprehensive-Survey) (arXiv:2412.04508).

Local Edge & Gradient Orientation Histograms: pcpmartins/video-quality-assessment measures local 4x4 grid edge orientation and Canny/Sobel gradient ratios to catch border stretching (BORDER_REPLICATE / BORDER_REFLECT smears), inpaint seams, and focus loss.

5.2 Why Old Gates Passed Bad Clips

REVIEW Rows Never Blocked Delivery: In explainer_engine/episode/run.py:45, 1086, GO_ON = (G.PASS, G.REVIEW). In qa/motion_intent.py:28-58, almost every new detector (fill_reveal, fill_at_rest, fill_invents, ghost_score, sharpness, blown_out, effect_seen_3s, intended_move) was set to level=G.REVIEW, so clips with visible defects passed G7 with 0 FAIL!

Whole-Frame Liveliness Masked Dead Regions: A single flickering brazier (0.5 % of the frame) satisfied alive_two_families (BP-185) while 99 % of the photo stood frozen for 8.8 s.

No Sliding-Window Dead-Second Check in layers25d.py: BP-174 only checked if frame-to-frame mean diff dropped below 0.15 for 12 frames; a microscopic 0.2 %/s zoom passed BP-174 while looking completely static to the human eye.

Plan
Export
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

Recipe 25d And Qa Sketches
Download
"""Reference Python implementation sketches for the Explainer Engine 2.5D recipe,
map collision/camera handoff, scene-key LAB color matching in assembly, and the 8
human-eye QA checks.
Designed to drop into:
- explainer_engine/production/directed25d.py
- explainer_engine/maps/actions.py
- explainer_engine/production/assemble.py
- explainer_engine/qa/motion_intent.py
- explainer_engine/videolane/master_qa.py
"""
from __future__ import annotations
import math
from typing import Any
import cv2
import numpy as np
# =============================================================================
# 1. 2.5D RECIPE FIXES (for explainer_engine/production/directed25d.py)
# =============================================================================
def prepare_clean_layers_and_bg_depth(
    src_rgb: np.ndarray,
    plate_rgb: np.ndarray,
    depth_01: np.ndarray,
    object_masks: dict[str, np.ndarray],
    person_boxes_norm: list[list[float]],
    thin_stroke_px: float = 16.0,
    thin_share_max: float = 0.35,
    feather_px: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Fix for directed25d.py:_rest_background (lines 174-227) and bg_maps (lines 590-604).
    1. NEVER bite morphological disc holes out of a kept foreground mask (which caused
       the C4A scalloped outlines at frame 0). Either keep the object mask whole with a
       soft inward-safe feather, or if it is mostly thin strokes (barbed wire, twigs),
       leave the entire object on the background sheet (layer=False).
    2. Flatten the background depth gradient inside every detected person/face box that
       remains on the background sheet (e.g. crowds in S05_SH020), so per-pixel background
       remap never rubber-stretches faces or heads.
1. ვერდიქტი და პირველი სამი ნაბიჯი (ქართულად)

მთავარი ვერდიქტი: არქიტექტურის ბირთვი (60% LTX / 30% 2.5D / 10% დამხმარე, სიტყვებზე მიბმული საათი timing.py და Scene Director) სწორია, მაგრამ კოდში ოთხი კრიტიკული წყვეტაა, რის გამოც ვიდეო ერთ ფილმად ვერ იკვრება.

რატომ ვერ ეწყობა ფილმი დღეს: (ა) episode/run.py:554, 643 ისევ ძველ layers25d.py-ს უშვებს და საერთოდ არ იძახებს PR #188-ის ახალ directed25d.py-ს; (ბ) directed25d.py:197-207 ნიღბებიდან მორფოლოგიური დისკით „თხელ ხაზებს“ ჭრის (რაც ადამიანების გარშემო ტალღოვან ნაკერებს ტოვებს), ხოლო ფონის დეფორმაცია (bg_maps, ხაზი 590) უნიღბო ხალხს სახეებს უწელავს; (გ) production/assemble.py:1546 (assemble_shot_clips) საერთოდ არ იძახებს finish/grade.py-ს, ამიტომ LTX, 2.5D და რუკები ფერის გასწორებისა და საერთო ფირის მარცვლის (grain) გარეშე ეწებება; (დ) episode/run.py:832 ერთი LTX კლიპის არარსებობისას ჩუმად გადადის დაუჭრელ ხმაზე (53.75 წმ აცდენა S05-ში), ხოლო cinematic_transitions.py:138-ს რუკიდან რუკაზე გადასვლის წესი საერთოდ არ აქვს.

ნაბიჯი 1 (უფასო, კოდი): გაასწორე ხმის ჩუმი fallback episode/run.py:831-838-ში (გაისროლოს ContractError ან ჩასვას ზუსტი სიჩუმე --rehearsal-ში), შეიტანე TD-342 სტერეო ფონის პატჩი audio/acoustics.py-ში და ჩართე directed25d.py პირდაპირ episode/run.py:stage_clips-ში.

ნაბიჯი 2 (უფასო, 2.5D და რუკები): ამოშალე მორფოლოგიური ამოჭრა directed25d.py:197-207-დან, გააბრტყელე ფონის სიღრმე (grad=0) ყველა აღმოჩენილი ადამიანის ჩარჩოში (bg_maps), გაყავი 5 წამზე გრძელი 2.5D კადრები (S02_SH008, S08_SH002, S05_SH020) წინადადების საზღვარზე, ხოლო რუკებში (maps/plate.py:25, maps/actions.py:167, 472) გამორთე თანამედროვე საზღვრები (borders=False), დაამატე წარწერების 8-პოზიციანი განლაგება და გადაეცი წინა რუკის კამერის (lon, lat, span_km) მომდევნო რუკას.

ნაბიჯი 3 (უფასო, მონტაჟი და QA): ჩასვი სცენის ღუზა-ფოტოზე Reinhard LAB ფერის გასწორება (finish/grade.py:108) და საერთო ფირის ეფექტი production/assemble.py:1546-ში, ხოლო qa/motion_intent.py-ის 8 დეტექტორი გადაიყვანე REVIEW-დან FAIL-ზე, რათა უძრავი ან ნაკერიანი კადრი გეიტმა ავტომატურად დაბლოკოს.

2. Verdict on the Current Approach (Judged Against the Code)

Your high-level architecture—an episode-first state machine (explainer_engine/episode/run.py:35), a fixed 60% LTX / 30% 2.5D / 10% helper runtime mix (D-93), a word-timed event spine (episode/timing.py + episode/events.py), and the Scene Director stack (production/understand.py, living_director.py, living.py, finish/frame_pick.py, finish/superres.py)—is fundamentally right. What is fundamentally broken is integration and boundary discipline in the code: episode/run.py:554, 643 still calls the legacy 4-slab Telea renderer (layers25d.py) and never invokes understand.py or directed25d.py. Inside PR #188's directed25d.py, morphological mask surgery (_rest_background, lines 197-207) bites scalloped holes out of character outlines, while per-pixel background warping (bg_maps, lines 590-604) stretches unlayered crowd faces whenever a mask is marked "layer": false. In assembly, production/assemble.py:1484-1582 (assemble_shot_clips) completely bypasses finish/grade.py (transfer_to_key and grade), edit/cinematic_transitions.py:138-163 has no map -> map transition branch, and episode/run.py:832 silently falls back to the unsplit narrator audio when an LTX insert clip is absent in a worktree (shifting S05 narration by 53.75 s). Finally, episode/run.py:45 (GO_ON = (G.PASS, G.REVIEW)) paired with level=G.REVIEW on almost every check in qa/motion_intent.py:28-58 guarantees that broken clips pass automated gates.

3. The 2.5D & Map Lanes: Concrete Technique, Code Root Causes, and Recipes
3.1 Proven 2.5D Stack & Why Ours Fails Today

Proven single-image 2.5D pipelines—3D Photography using Context-aware Layered Depth Inpainting (vt-vl-lab/3d-photo-inpainting) (arXiv:2004.04727) and 3D Ken Burns Effect (sniklaus/3d-ken-burns) (ACM TOG Paper)—establish three strict invariants: (1) high-resolution depth without pre-blurring (Depth Anything V2), (2) flat, constant depth inside every human/rigid foreground instance (SAM 2.1 + BiRefNet) so faces never warp internally, and (3) structural Fourier disocclusion inpainting (LaMa (advimman/lama)) behind whole, un-bitten alpha silhouettes. Shader tools like DepthFlow (BrokenSource/DepthFlow) and ComfyUI-Depthflow-Nodes require an OpenGL/EGL GPU context unavailable in your CPU container, making understand.py + directed25d.py the right CPU architecture once five code bugs are fixed:

Legacy Default Still Active (episode/run.py:554, 643 & production/depth.py:25-27): stage_clips runs L25.render_clip (layers25d.py), which uses MAP_SIZE = (576, 324) and SOFTEN = 3.0 (depth.py:26-27), slices 4 k-means slabs (PLANES = 4, layers25d.py:82), inpaints with cv2.INPAINT_TELEA, scales push/pull only around the frame center (src_w / 2, layers25d.py:324), and scrolls noise tiles by whole integers (int(round(ox * tw)) % tw, layers25d.py:695), causing 7-pixel stepping jitter.

Scalloped Seams at Frame 0 (production/directed25d.py:74-82, 197-227): _rest_background runs parts = hard & (1 - cv2.morphologyEx(hard, cv2.MORPH_OPEN, disc)) (line 197), cuts strokes from o["alpha"] (o["alpha"] = o["alpha"] * (1.0 - strip), line 206), and dilates A by REST_ALPHA_GAIN = 6.0 and REST_GROW_PX = 3.0 (line 212). That exposes a 3 px ring of LaMa plate around rough coat/hair outlines on frame 0. Fix: Never cut morphological pieces out of a kept foreground mask; if thin_share >= 0.35 (barbed wire, twigs), keep the entire object in the background (layer=False); otherwise keep the SAM+BiRefNet mask whole with a 3 px Gaussian feather.

Rubber-Sheet Face Smearing on Unlayered Crowds (production/directed25d.py:590-604): bg_maps warps the background sheet per-pixel (d = cv2.remap(self.bg_depth, mx, my, ...)). Any person not extracted as a separate layer (such as the 11 soldiers in S05_SH020 where crowd masks have "layer": false) gets warped by self.bg_depth gradients. Fix: Clamp self.bg_depth to its median value (grad = 0) inside every YuNet/SAM person bounding box (padded 1.25x) before bg_maps.

Dead Pre-Word Holds & Over-Length 2.5D Shots (production/living_director.py:45, 413): When a shot has a trigger word (targets), line 413 sets rate = RATE_MIN (0.5 %/s), leaving S02_SH008 and S05_SH020 visually static for 5–8 s, and 12 of 24 Truce still_25d shots exceed the <= 5.0 s rule (BP-109). Fix: Raise pre-accent floor to 1.8 %/s and split every still_25d shot > 5.0 s at its clause midpoint into two <= 5.0 s shots (Part A wide, Part B 1.35x focal crop on the named subject).

Clipped Highlights vs. Invisible Effects (production/directed25d.py:62-64, 797-802 & living_fx.py:40-45): Keep 302c8dd's LFX.screen (LIGHT_CEIL = 0.55, SHAFT_CEIL = 0.70, SHAFT_SHADE = 0.22, PEOPLE_SHIELD = 0.85).

3.2 Minimal Free CPU 2.5D Recipe per Shot Type (<= 5.0 s)
Shot Type	Depth & Layering (understand.py + directed25d.py)	Camera Trajectory (directed25d.py)	Living Effects (living_fx.py, 3–4 active)
Landscape (S01_SH001, S05_SH016)	Continuous DA-V2 1848x1036 background (BG_SMOOTH = 0.008); thin wire stays on BG (layer=False); max 1 rigid midground prop (spades) over LaMa plate.	Multi-plane crane up or truck (NEAR_TRAVEL = 0.05, far_share = 0.15, 2.0–3.0 %/s) easing into the spoken noun.	1) Two-bank sub-pixel mist (40/65 px/s), 2) screen-blended sun_shaft (SHAFT_GAIN = 0.85, +-6 deg sway), 3) cloud_drift light sweep (30 px/s), 4) grouped brazier glow/smoke.
Group of People (S05_SH020, S02_SH008, S06_SH001)	Max 2 primary foreground heroes as SAM 2.1 + BiRefNet RGBA layers; crowd stays on BG with bg_depth flattened per person box (grad=0).	Base push (1.8 %/s) on Speaker A -> word-timed truck (TRUCK_STRENGTH = 2.0, ease_out, 1.25 s) to Group B on trigger word + handheld (0.25).	1) Cold breath plumes from YuNet mouth coordinates (period_s = 3.6), 2) 3-layer depth-occluded snow or mist, 3) brazier/candle spill on faces, 4) embers/smoke.
Close Face	Hero cut out as 1 rigid RGBA layer (uniform median depth d_hero) over LaMa-inpainted background (HOLE_GROW = 0.006).	Targeted push (1.5–2.2 %/s) + subtle orbit (ox = 0.025) around focus_d = d_hero + rack_focus (RACK_SIGMA_PX = 5.0 on BG) + handheld (0.3).	1) subject_sway (0.25 deg rigid breath), 2) mouth breath plume, 3) warm fire spill on cheek, 4) far-layer snow/dust behind d_hero only (layers=[0]).
Object / Insert (S08_SH002)	Hands + object as 1 rigid RGBA layer (d_obj); trench background blurred (RACK_SIGMA_PX = 6.0).	handheld breathing (0.35) + targeted push (1.5 %/s) to named detail (button/photo) on word, keeping candle in soft keep_in_frame.	1) candle flame tip deformation (_deform_flame) + warm spill across hands, 2) candle-lit dust motes, 3) heat_haze above flame, 4) bottom-edge breath.
3.3 Rich, Readable Animated Maps & Map-to-Map Continuity

Following programmatic cartography standards (Manim Community Internals):

Historical Plate (maps/plate.py:25): Omit "borders" from LAYERS whenever historical_period.start_year < 1945 (map_look.borders = False) so modern borders never appear on 1914 Flanders; enforce MIN_SPAN_KM = 250.0 (maps/actions.py:55) so ne50m shaded relief stays sharp.

Map-to-Map Camera Handoff (maps/actions.py:167 & edit/cinematic_transitions.py:138): In maps/actions.py:_first_view, if the previous shot was a same-theater map_action, inherit its final camera (lon, lat, span_km) as view0 instead of recomputing an independent bounding box, and add elif is_a_infographic and is_b_infographic: in cinematic_transitions.py:138 using cross_dissolve_8f (8 frames).

Continuous Action & 8-Position Label Solver (maps/actions.py:48-52, 472-478): Stretch discrete action drawing across the spoken word span (ev["end_frame"] - ev["start_frame"], min 36 frames) instead of freezing after ANIM_FRAMES = 18; allow route_pan/scale when DENSE_ACTIONS >= 4; and replace the fixed (cx + 0.35*size, cy - 0.35*size) label offset with the 8-candidate greedy bounding-box solver in recipe_25d_and_qa_sketches.py.

4. End-to-End Assembly Recipe & Module Disposition
4.1 End-to-End Assembly Recipe (Order, Grade, Transitions, Cut Rules, Sound, Loudness)

Order of Operations:

Step A (G6 Voice & Word Spine): Polish narration (audio/narrator_polish.py), align Scribe words (episode/timing.py), and splice LTX character dialogue (videolane/voice.py). In episode/run.py:831-838, remove the silent fallback to unsplit narration: if any insert clip is missing, raise ContractError (or insert exact-duration silence in --rehearsal).

Step B (G6.5 Understand & Direct): Run understand.build (scene_layers/1) and living_director.direct (shot_direction/1) across all photos and maps; resolve av_events/2 (episode/events.py) so camera moves, map actions, text overlays, and foley share one frame clock.

Step C (G7 Render & Ingest): Render map_action (map_clip.py), render still_25d (directed25d.py), and ingest video (videolane/ingest.py with HF-4 -1.0 dBTP true-peak trim and muting of non-speaking LTX tails where Whisper hears hallucinations like "You" in S07_SH008).

Step D (G8 5-Stem Audio Mix): Render narration, spot, foley, music, and ambience (audio/stems.py), then normalize via two-pass EBU R128 loudnorm (qa/targets.py, Two-Pass FFmpeg loudnorm Guide).

Step E (G9 Grade-Matched Chunk Assembly): Stream shot clips through production/assemble.py:assemble_shot_clips with scene-key color transfer, transition blending, era LUT, and film grain/vignette (FFmpeg Filters).

Grade Matching Across LTX (60%), 2.5D (30%), and Maps (10%):

In production/assemble.py:1535-1550 (assemble_shot_clips), wire in finish/grade.py:89-110 (Reinhard LAB Color Transfer / scikit-image Histogram Matching): compute transfer_params once per shot from its boundary frames toward the scene's first 2K Gemini anchor photo (key_master_frame), apply apply_transfer(frame, params, blend=0.50) (0.20 on maps), then apply the era grade grade(frame, look, seed=frame_idx) and vignette=PI/6,noise=alls=1.5:allf=t so all three lanes share identical black levels, warmth, and grain.

Transitions & Cut Rules (Documentary Editing Best Practices & Crossfade AV Sync):

Cut on Words (BP-195): Every cut or camera accent lands within [-4, +6] frames (-150 ms to +250 ms) of the spoken noun/verb onset.

Within Scene (video <-> 2.5D): Hard cut (0 visual blend frames) with a 0.25–0.35 s J/L audio bridge (audio_j_cut_prelap_sec). Read actual rendered camera vectors from shot_records.json in cinematic_transitions.py:64.

Scene <-> Map & Map <-> Map: cross_dissolve_8f (8 frames, scene -> map and map -> map) and map_to_location_zoom_through (14 frames, map -> scene) with 0.35–0.50 s audio prelap.

Sound Layers & Loudness Target (BP-50..65, EBU R128 Standard):

5 Stems: narration (-16.0 LUFS anchor, 80 Hz HPF), spot (-26 dBFS RMS) & foley (-30 dBFS RMS, panned from visual mask center pan = (cx - 0.5) * 1.2, low-passed by distance 9 kHz / 4.5 kHz), music (-32 dBFS, 2.0 s crossfades, voice sidechain ducking + 2.5 kHz presence dip), and ambience + room_tone (-36 dBFS / -54 dBFS, TD-342 stereo widen corr in [0.05, 0.65], 0.5 s crossfades at cuts).

Master Target: -14.0 LUFS integrated (-15.0 .. -13.0 pass band), -1.0 dBTP true peak, 48 kHz stereo AAC-LC.

4.2 Existing Modules: Keep, Fix, or Drop

KEEP: episode/timing.py, episode/events.py, finish/frame_pick.py, finish/superres.py, finish/grade.py, audio/narrator_polish.py, audio/duck.py, qa/targets.py, videolane/ingest.py, episode/helper_fit.py (PR #190).

FIX: episode/run.py (wire understand + living_director + directed25d; remove silent voice fallback at line 832), production/directed25d.py (remove morphological hole-biting at lines 197-207; flatten bg_depth inside person boxes at line 590), production/living_director.py (raise pre-word camera rate floor to 1.8 %/s), production/assemble.py (call finish/grade.py inside assemble_shot_clips at line 1546), edit/cinematic_transitions.py (add map -> map branch at line 138; read rendered camera vectors at line 64), maps/plate.py (borders=False), maps/actions.py (camera inheritance, 8-position label solver, word-span action duration), audio/acoustics.py (commit TD-342), qa/motion_intent.py & videolane/master_qa.py (promote perceptual checks to FAIL).

DROP / RETIRE: explainer_engine/blender/* (retired J5 era), production/parallax.py, production/cinematic_image_animator.py, edit/clay_video.py, finish/upscale.py (plain Lanczos), maps/render.py (legacy Toba/Waterloo path).

5. QA That Matches the Human Eye (8 Checks)

Grounded in Temporal & Spatial VQA Features (TestDevLab), Local Edge Histogram VQA (pcpmartins/video-quality-assessment), VQA Survey (taco-group), and FFmpeg blackdetect. Promote all 8 to blocking FAIL gates:

#	Check Name	Measurement Method	Starting Threshold (FAIL / REVIEW)
1	rest_seam_and_halo	On frame 0 (directed25d.py:229), measure `max_c	rest_composite - src_rgb
2	sliding_1s_liveliness	Across every sliding 1.0 s (24-frame) window at 480x270 gray, fraction of pixels with `	I(t+24) - I(t)
3	border_stretch_and_reveal	Distance transform of newly revealed LaMa fill (qa/motion_intent.py:157), Canny edge ratio inside_fill / outer_ring (line 216), and normal-vs-tangential gradient smear ratio in the outer 8 px border (recipe_25d_and_qa_sketches.py).	FAIL if share_wide > 3.5 %, band_px > 45 px, invent_ratio > 1.8, or border smear > 0.85; REVIEW above 2.0 % / 30 px / 1.5 (hypothesis).
4	people_and_chips_safe_zone	Fraction of any non-soft keep_in_frame person box (directed25d.py:543) or map label/date-chip box (maps/actions.py) outside [0.015*W, 0.985*W] x [0.015*H, 0.985*H].	FAIL > 0.005 (0.5 % cut by frame edge); REVIEW > 0.0 on soft light boxes (binding owner rule).
5	face_rigidity_and_sharpness	Camera-compensated template match TM_CCOEFF_NORMED of each face (>= 55 px) against frame 0 (directed25d.py:534), plus last-vs-first Laplacian variance ratio inside the focus target (qa/motion_intent.py:36).	FAIL if face_likeness < 0.88 or target_sharpness_ratio < 0.45; REVIEW < 0.92 or < 0.60 (calibrated: smeared S06 0.80, intact 0.96–0.99).
6	highlight_burn_and_clipping	Newly flat-white share blown_share(frame) - blown_share(src) (luma >= 245, 9x9 std < 2.0, directed25d.py:508) and mean luma rise inside people_field.	FAIL if new white burn > 1.5 % or person luma rise > 18.0 levels; REVIEW > 0.5 % (calibrated: C5 burn 10–13 %, fixed 0.0–0.3 %).
7	cross_shot_grade_and_stalls	Same-scene cut CIE LAB Euclidean mean distance lab_distance(last_a, first_b) (finish/grade.py:73) and BP-164 black/frozen run detector (master_qa.py:72).	FAIL if same-scene lab_distance > 12.0 or black/frozen run >= 6 frames; REVIEW if lab_distance > 8.0 (hypothesis).
8	per_shot_asr_and_onset_sync	Per-shot Whisper ASR word recall on the sliced master audio vs shot["audio_line_ids"], SFX onset offset (BP-54), bed cut jump (BP-191), and master EBU R128 (BP-50).	FAIL if shot ASR word recall < 0.80 (catches INC-MAP-1 54 s offset), SFX onset outside [-45, +125] ms, or master outside [-15, -13] LUFS / > -1.0 dBTP; REVIEW if bed jump > 3.0 dB.
6. Ordered Plan (8 Steps)
#	Goal	Files Touched	Free or Paid	Done-When
1	Fix stage_sound silent voice desync & commit TD-342 stereo bed anti-phase fix	explainer_engine/episode/run.py, explainer_engine/audio/acoustics.py, tests/unit/test_bed_stereo_and_loop_window.py	Free ($0, CPU)	Missing LTX insert raises ContractError (or pads exact insert silence in --rehearsal); BED_16/17 corr in [0.03, 0.61]; tests pass.
2	Fix directed25d.py seam & crowd-warp bugs and promote Checks 1–6 to FAIL	explainer_engine/production/directed25d.py, explainer_engine/production/living_director.py, explainer_engine/qa/motion_intent.py	Free ($0, CPU)	Morphological hole-biting removed (rest_seam <= 0.02); bg_depth flattened inside person boxes (face_likeness >= 0.92); pre-word camera >= 1.8 %/s.
3	Split > 5.0 s 2.5D shots (BP-109) & wire understand + living_director + directed25d into run.py	episodes/ep_truce_1914/story/production_script.json, explainer_engine/episode/run.py, explainer_engine/production/layers25d.py	Free ($0, CPU) (or ~$0.21 LTX only if owner prefers LTX over splitting)	All still_25d shots <= 5.0 s; episode run --stage clips runs directed25d and all 2.5D clips pass Checks 1–6 with 0 FAIL.
4	Upgrade Map & Helper lane (borders=False, 8-pos label solver, camera handoff, map->map dissolve)	explainer_engine/maps/plate.py, explainer_engine/maps/actions.py, explainer_engine/production/map_clip.py, explainer_engine/edit/cinematic_transitions.py, explainer_engine/episode/helper_fit.py	Free ($0, CPU)	1914 maps have no modern borders, 0 label/chip collisions, smooth camera inheritance across S02 and S05 maps, and cross_dissolve_8f on map -> map.
5	Align scene audio, map foley, LTX tail-frame pick (BP-199), and CLIP-06 true-peak trim	explainer_engine/production/living_director.py, explainer_engine/episode/cue_sheet.py, explainer_engine/finish/frame_pick.py, training/pods/ltx/modal_ltx_jobs.py	Free ($0, CPU) (optional ~$0.15 ElevenLabs SFX only if adding new takes)	Counter ticks/knock land within +-1 frame on timed_script; silent LTX tails (S07_SH008, S04_SH005) muted at G8; S07_SH005/S02_SH006 trimmed <= -1.0 dBTP.
6	Wire Scene-Key LAB Color Matching, Era Grade & Film Finish into assemble_shot_clips (G9)	explainer_engine/production/assemble.py, explainer_engine/edit/cinematic_transitions.py, tests/unit/test_assemble_v2.py	Free ($0, CPU)	assemble_shot_clips applies Reinhard LAB transfer (finish/grade.py) toward each scene's anchor photo + era LUT + grain/vignette; lab_distance <= 12.0.
7	Add Per-Shot ASR & Perceptual Master QA (G10) and render full ep_truce_1914 master	explainer_engine/videolane/master_qa.py, explainer_engine/episode/acceptance.py, explainer_engine/episode/run.py	Free ($0, CPU, ~35 min)	episode run episodes/ep_truce_1914 --to qa passes with 0 FAIL on all 8 checks; master MP4 and contact sheet verified.
8	Lock repeatable episode template & sync rule registry	docs/EPISODE_FIRST.md, docs/MAIN_METHOD.md, explainer_engine/standards/sourced_rules.json, docs/PROGRESS.md	Free ($0)	docs_lint 0 findings; full pytest green; next episode needs only script + anchor photos + 1 LTX wave run.
7. Why Earlier Argon (Gemini) Work Rated Higher Than Claude's—and How to Brief Both

Whole-Tree Code Verification Before Planning: In history_argon/2026-11-01/ARGON_PROMPT.md and 2026-11-06/BRIEF.md, you gave me a single consolidated snapshot and forced an audit-first gate ("quote file and line, mark unverified as NOT CHECKED") before designing. Claude operated across 20 fragmented parallel threads (T01–T20), so one Claude thread wrote directed25d.py in PR #188 while episode/run.py still ran layers25d.py, and another thread researched tools (LaMa, HyperFrames) already in the repo (INCIDENT_JOURNAL 14:45 UTC).

Script-First Visual Derivation vs. Blind Prompting: In the earlier workflow (BRIEF.md), shots were derived scene-by-scene from the narrative script with explicit action_start_state -> action_end_state and in_shot inventories before rendering. In Truce, Claude threads wrote LTX prompts and 2.5D configs from text alone without inspecting the start photo (PB-09, LTX-09) and without checking how assemble_shot_clips actually joins them.

External Grounding vs. Uncalibrated Internal Heuristics: Earlier Argon sessions pulled established computer-vision and film-editing standards (Reinhard LAB transfer, 30-degree rule, LDI inpainting, EBU R128), whereas Claude threads invented ad-hoc morphological operations (_rest_background disc opening) and marked every failing threshold as REVIEW so CI stayed green.

How to Brief Us Going Forward:

One branch, one truth: Never run parallel Claude threads on separate branches touching the same episode; merge into one integration branch before briefing.

Enforce the 3-part brief: (a) attached repo zip + incident journal, (b) mandatory code-quote audit of what episode/run.py actually executes, and (c) zero REVIEW-only gates on visual/audio defects—every new detector must be calibrated on 1 known-bad and 1 known-good clip and set to FAIL.

8. NOT CHECKED (What Could Not Be Verified in This Session)

Actual MP4 Video Playback & Audio Listening: SLIM_NOTE.txt and README_PACKAGE.md omit .mp4/.wav binaries and private Hugging Face dataset files (vano1919/tmr-artifacts); defects in C3/C4A/C5, R2/R3, and map_counter_test_v2 were verified via your frame-measurement logs, incident journals, and the exact Python rendering code that produced them.

Removed Slim Files: docs/VAULT_MANIFEST.json, assets/audio/library/manifest.json (the 260 audio file entries), docs/PROGRESS.md, and examples/ were stripped for the upload limit (SLIM_NOTE.txt).

Local Windows PC Hardware Benchmarks (i5-8400 + RX 5700): Not executed here (local_bench/RUN_ALL.ps1 requires your local Windows machine).

Full Pytest Suite Execution with Heavy Model Weights: tools/models/ (DA-V2, SAM 2.1, BiRefNet, LaMa, RealPLKSR, YuNet) are gitignored and not bundled in the text zip.