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