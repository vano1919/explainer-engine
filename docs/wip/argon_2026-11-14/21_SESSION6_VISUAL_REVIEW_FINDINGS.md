Gemini said

ექვსივე კადრის შედარებითი ფურცლები (*_C5_vs_new.jpg), results.json და S05_SH020-ის ორივე ვიდეო სრულად შევამოწმე კოდის დონეზე.
ახალმა კოდმა (PR #192) გაასწორა საწყისი კადრის ნაკერები (rest_seam = 0.0 ყველა კადრში) და fill_at_rest ხუთ კადრში, მაგრამ S05_SH020-ში კამერის მოძრაობა დააზიანა.S05_SH020-ში კამერის სტატიკურობა და 73-ე/143-ე კადრებზე ერთკადრიანი ნახტომები გამოწვეულია Stage._frame_people-ში soft: true ნათურების (brazier_left=0.11, brazier_right=0.91) მიერ ხედის ცენტრში ჩაკეტვით, direction.resolve/segment_u-ის საზღვრის b - 1 წანაცვლებით, Stage.view-ში შეუზღუდავი goal-ის ინტერპოლაციით და living_director-ის ფიქსირებული end.frame=74-ით.
ერთ ფოტოზე გვერდითი კუთხის ცვლილება (orbit / პარალაქსური truck) ჭრის ადამიანებს ჩარჩოს კიდეზე და ხსნის 84.3 px შევსების ზოლს (post_right), ამიტომ ადამიანებიან კადრებში რეჟისორმა უნდა გამოიყენოს push ან ჰორიზონტალური pan კუთხის შეცვლის გარეშე.
გარდა ამისა, S06_SH001-ის pull პირველ კადრზევე წევს პარალაქსს (dp = +0.03, fill_at_rest = 21.9 px), ხოლო T6/T7 (run.py + shot_split.py) გრძელ კადრებს ჭრის ისე, რომ direction.resolve ისვრის ValueError-ს და კარგავს კამერას, ეფექტებსა და 1.35x cut-in ჩარჩოს.

(a) Per-Shot Visual & Telemetry Table (NEW vs C5)
Shot	Verdict (NEW vs C5)	What a Viewer Sees (renders/*_C5_vs_new.jpg & Videos)	renders/results.json vs c5_inputs/render_results_*.json


S01_SH001




(3.0 s, 72f, crane up)

	Better at Frame 0 & fill reveal; Same weak secondary effects	

Frame 0: C5's 19 px vertical cut on the near-right post is gone (no_effects=0.0).




Motion/seams: Stronger upward crane (+3.60% vs +2.31%); horizon Telea/LaMa smear narrows (45.8 px vs 76.4 px, still visible at 33–66%).




Ghosts/light: sandbags_near ghost gone, thin wire_right_near stroke leaves 0.207 double-edge at f=28; screen-mix sun_shaft avoids white burn; sun_glint (8.61) and fire (5.79) stay imperceptible.

	

base_zoom: 1.2279 (both)




rest_seam: 0.0388 (602 px) 
→ 0.0




fill_at_rest: 1.63% / 18.6 px (REVIEW) 
→ 0.0% / 0.0 px (PASS)




fill_reveal: 2.22% / 76.4 px 
→ 1.92% / 45.8 px (f=33, REVIEW)




double_edge: 0.331 
→ 0.207 (wire_right_near f=28, shift 5.4 px, REVIEW)




global_motion: shift_y +2.31% 
→ +3.60%




effects_seen: sun_glint=8.61, fire=5.79 (< 10 REVIEW)




S02_SH008




(10.96 s, 263f, push to Thomas on "nobody")

	Better at Frame 0; Same 8.75 s slow crawl & star stamp	

Frame 0: C5's 15.3 px rest fill band around Thomas/brazier is gone (0.0 px).




Motion: Cached direction file still uses pre-T4 strength=0.733 (0.5%/s crawl for 8.75 s) before the accent push (210->241).




Effects: Fire/smoke/breath read well; fx_first_stars (box=[0.27,0.02,0.33,0.08], STAR_GAIN=2.2) stamps up to 60 bright 4-point crosses into a 
6%×6% sky patch.

	

base_zoom: 1.0099 (both)




rest_seam: 0.0193 (245 px) 
→ 0.0




fill_at_rest: 1.45% / 15.3 px 
→ 0.0% / 0.0 px (PASS)




fill_reveal: 1.66% / 18.6 px 
→ 0.96% / 18.6 px (PASS)




double_edge: 0.0 
→ 0.046 (PASS); face_intact: 0.977 
→ 0.966 (PASS)




global_motion: scale 1.1271 -> 1.1427, shift_x +5.59% -> +5.56%




effects_seen: stars=222.03




S05_SH016




(3.5 s, 84f, push to spade_left)

	Better at Frame 0; Same motion; Worse false fill_invents	

Frame 0: C5's 7.6 px rest fill ring around the spades is gone (0.0 px).




Motion/life: Clean push (scale=1.0722) with mist, snow, and glint.




False QA flag: fill_invents rises to 1.87 (REVIEW at f=8) because self.hole = (raw_a > 0.01) marks the stationary 3 px inward-feathered spade rim as newly revealed fill after Frame 0 (fill=0).

	

base_zoom: 1.0079 (both)




rest_seam: 0.0052 (57 px) 
→ 0.0




fill_at_rest: 1.25% / 7.6 px 
→ 0.0% / 0.0 px (PASS)




fill_reveal: 1.46% / 18.6 px 
→ 1.04% / 21.9 px (PASS)




double_edge: 0.092 
→ 0.091 (PASS)




fill_invents: 1.29 (PASS) 
→ 1.87 (f=8, 5778 px, REVIEW)




S05_SH020




(7.83 s, 188f, burial: push on "scottish", side move on "student")

	Worse (Static/centred camera, 1-frame jumps at f=73 & f=143, 84.3 px fill band; crowd rigidity better)	

Motion (S05_SH020_C5.mp4 vs S05_SH020_new.mp4):




1. Wider Frame 0: base_zoom drops 1.1235 -> 1.0245.




2. Lost push to Scots (x=0.30): NEW zooms +7.72% into dead centre (pan_x = -0.20% vs C5 +4.36%).




3. 1-frame jumps at f=73 & f=143: At f=72->73, L1 frame diff spikes to 32.74 (C5 also spiked to 31.03 at f=72->73!) while f=71->72 (0.29) and f=73->74 (0.60) stand still. At f=142->143, the crowd is frozen for f=136..142 (dx=0), snaps -32 px (L1 diff = 30.31) in 1 frame at f=143, and freezes again for f=144..162 (dx=0).




4. Lost lateral move & 84.3 px tear: Lateral move shrinks from -7.46% to -1.45%, while parallax on post_right (d=0.826, shift 18.8 px) opens an 84.3 px blurry fill band at f=142.

	

base_zoom: 1.1235 
→ 1.0245




rest_seam: 0.0044 
→ 0.0; fill_at_rest: 7.6 px 
→ 0.0 px




fill_reveal: 1.56% / 45.8 px 
→ 1.63% / 84.3 px (f=142, REVIEW)




fill_invents: 1.59 
→ 2.33 (f=24, REVIEW)




double_edge: 0.259 (REVIEW) 
→ 0.160 (post_right f=152, shift 18.8 px)




camera_segments push 72->74: C5 zoom +6.98%, pan_x +4.36% 
→ NEW zoom +7.72%, pan_x -0.20%




camera_segments truck 136->162: C5 pan_x -7.46% 
→ NEW pan_x -1.45%




face_intact: NOT_RUN (faces=0, kept_faces=11)




S06_SH001




(3.0 s, 72f, pull out)

	Same motion & rays; Better rest_seam; Still failing Frame-0 rest purity	

Frame 0: rest_seam is 0.0, but fill_at_rest is still 21.9 px (REVIEW) and frame0_purity["no_effects"] = 4.027 because Stage.view sets dp = +DEPTH_PUSH * st * (1 - u) = +0.03 on Frame 0 (u=0), making at_rest = False and shifting post_left (d=1.0) 22 px off its hole on Frame 0.




Effects: Geometric 3/5/8-lobed radial cosine sun_shaft pattern remains visible around the sun in both.

	

base_zoom: 1.0106 (both)




rest_seam: 0.0264 (452 px) 
→ 0.0




fill_at_rest: 1.88% / 26.2 px 
→ 0.94% / 21.9 px (REVIEW)




fill_reveal: 1.50% / 22.9 px 
→ 0.73% / 16.4 px (PASS)




face_intact: 0.990 (PASS); global_motion: scale 0.9438




frame0_purity: no_effects = 4.027




S08_SH002




(9.75 s, 234f, push to photo on "truces")

	Better at Frame 0; Same fill_invents REVIEW & 5.0 s slow crawl	

Frame 0: C5's 11.0 px rest fill band around the hands/photo is gone (0.0 px).




Motion: Cached direction file still crawls at 0.5%/s (strength=0.417) for 5.0 s (0->120) before pushing into photo (120->150, scale=1.1029, shift_x=+4.64%).




Seams: hands double-edge is 0.134 (PASS); fill_invents=1.76 at f=8 is the same feathered-rim false positive as S05_SH016.

	

base_zoom: 1.0095 (both)




rest_seam: 0.0; fill_at_rest: 1.49% / 11.0 px 
→ 0.0% / 0.0 px




fill_reveal: 1.52% / 22.9 px 
→ 1.60% / 21.9 px (PASS)




double_edge: 0.065 
→ 0.134 (hands f=152, shift 5.4 px, PASS)




fill_invents: 1.77 
→ 1.76 (f=8, REVIEW)




target_sharpness: 0.738 (PASS)

Verdict on S05_SH020 Camera Regression: It is a combination of real code bugs in directed25d.py, direction.py, and living_director.py triggered by render_driver/render_shot.py's inputs:

directed25d.py:Stage._frame_people (line 450): if s_max < 1.0 and i + 1 < len(groups): continue only drops i=0 (self.keep, which includes "soft": true lights brazier_left=0.11 and brazier_right=0.91, span 0.862) when s_max < 1.0. Under NEW's da_v2_small depth (d=0.62, par=0.696 vs C5 d=0.38, par=0.504), i=0 clamps wx = cx + tx * par to hi = 0.532 during the truck (nx = 0.463), which pulls the foreground right corner inside [0, 1] at z0 = 1.0245 (vs C5 1.1235). At z0 = 1.0245, s_max for i=0 stays >= 1.0 on all 188 frames, so i=0 never yields: it clamps cx to [0.488, 0.532], erasing the horizontal push to left_group (-0.20% vs +4.36%) and 75% of the lateral move to right_group (-1.45% vs -7.46%).

Why both C5 and NEW jumped for 1 frame at f=73, and NEW jumped for 1 frame at f=143:

Frame 73 in C5 (|f73 - f72| = 31.03): In C5 (from=44, to=74, z0=1.1235), s_max for i=0 sat just above 1.0 (1.014 .. 1.00002) for 29 frames (f=44..72), holding the view wide at scale=1.000, shift_x=0.0%. At f=73, dp pushed s_max to 0.99988 < 1.0, so _frame_people switched from i=0 to i=1 in one frame (72->73), dumping the entire +7.94% zoom and +3.76% shift into frame 73.

Frame 73 in NEW (|f73 - f72| = 32.74): C5's camera_moves recorded that f=72..74 jump as 3.0 s -> 3.08 s; render_driver estimated "scottish": 72, while S05_SH020.direction.json had baked end: {"frame": 74} from living_director.choose_camera. Plus, layers25d.segment_u divides by b - 1 - a, so track 0 (0->72) reached u=1.0 at f=71, froze at f=71->72 (du=0), and track 1 (72->74, b-1-a=1) jumped from u=0 (f=72) to u=1 (f=73) in 1 frame.

Frame 143 in NEW (|f143 - f142| = 30.31, -32 px): Stage.view interpolated goal_x in unclipped coordinates (0.30 -> 0.717) and clipped RECENTRE * (goal_x - 0.5) to [-half_x, +half_x] ([-0.0398, +0.0398]) after the loop, while _frame_people (i=0) clipped wx to [lo, hi] = [0.506, 0.523]. For f=136..141, goal_x stayed saturated below -half_x (wx < lo, crowd dx = 0); at f=142->143, goal_x crossed 0.50, jumping wx from < lo to > hi (-32 px) in 1 frame at f=143, then saturated at hi (crowd dx = 0) for f=144..162.

(b) Findings Table & Automatic QA Checks
#	Level	File + Line	Problem	Smallest Fix & Automatic Check
1	BLOCK	

explainer_engine/production/directed25d.py




Stage._frame_people




line 450:




if s_max < 1.0 and i + 1 < len(groups): continue

	i=0 (self.keep including "soft": true edge lights brazier_left=0.11, brazier_right=0.91) only yields when s_max < 1.0. When s > s_max >= 1.0 or when i=0's [lo, hi] clamps wx/wy, i=0 stays active: it drops z0 to 1.0245, cancels the push to left_group, cancels 75% of the lateral move to right_group, and in C5 caused the 1-frame snap at f=73 when s_max crossed 1.0.	

Yield i=0 (continue when i + 1 < len(groups)) whenever s > s_max or not (lo_x <= wx <= hi_x and lo_y <= wy <= hi_y).




QA check: motion_intent.segment_rows now checks horizontal recentre (want_sign * dx >= 1.0%, hypothesis per D-59) on off-centre push (`


2	BLOCK	

explainer_engine/production/direction.py




resolve (lines 446–485) &




explainer_engine/production/directed25d.py




Stage.view (lines 341–355)

	

Creator-spotted defect (1) — 1-frame jumps at frame 73 and frame 143 on S05_SH020:




1. layers25d.segment_u uses (f - a) / max(1, b - 1 - a), so at a shared boundary prev.to == next.from (72), prev finishes at f = 71 (u=1) and freezes for 1 frame (71->72), while baked end.frame = 74 with start = 72 (b - 1 - a = 1) jumps 0 -> 1 in 1 frame (72->73).




2. Stage.view blends unclipped goal (0.30 -> 0.717) before clipping to [-half_x, +half_x], saturating cx for f=136..141 and jumping -32 px in 1 frame at f=142->143.

	

1. In direction.resolve: extend word-anchored accents with baked end.frame where b - a < 12 to b = min(frames, a + 30), and when c_prev["to"] == c_next["from"], set c_prev["to"] = c_next["from"] + 1.




2. In Stage.view: clip each segment's target shift (tx_i, ty_i) to [-half_x, +half_x] before blending across pulls.




QA check: Add max frame-to-frame camera step check `max(


3	BLOCK	

explainer_engine/production/living_director.py




choose_camera (lines 423–427) &




explainer_engine/production/direction.py




check (line 171)

	Creator-spotted defect (2) — Lateral angle change (orbit / parallax side move) on one photo with people: Changing viewing angle laterally on a single 2D photo with people shears depth planes, cutting people off at the frame edge and tearing open an 84.3 px fill band beside foreground objects (S05_SH020 post_right). Also line 423 bakes static end = {"frame": ...} instead of {"word": word, "offset": ...}.	

1. In living_director.choose_camera: set end = {"word": word, "offset": int(round(ACCENT_S * fps))} and when faces or people_mid_or_close is true, emit horizontal "pan" (no angle change) instead of "truck" (and in Stage.view, append "pan" to pulls so targeted pans recentre smoothly).




2. In direction.check: flag orbit on shots with keep_in_frame faces as REVIEW.


4	BLOCK	

explainer_engine/production/directed25d.py




Stage.view




lines 320–323:




elif seg["op"] == "pull":




dp += DEPTH_PUSH * st * (1 - u)

	On Frame 0 (u = 0), pull sets dp = +DEPTH_PUSH * st (+0.03 on S06_SH001), making at_rest (abs(v["dp"]) < 1e-7) False on Frame 0! That renders self.plate on Frame 0 and shifts post_left (d=1.0) outward by 22 px, causing fill_at_rest = 21.9 px (REVIEW) and frame0_purity["no_effects"] = 4.027.	

Anchor pull at dp = 0.0 on Frame 0 (u = 0): s *= (1 + PUSH_SCALE * st * (1 - u)) * (1 + DEPTH_PUSH * st) and dp -= DEPTH_PUSH * st * u / (1 + DEPTH_PUSH * st).




QA check: Gate frame0_no_effects (max_abs_diff <= 0.5 levels, invariant FAIL).


5	FIX	

explainer_engine/production/directed25d.py




Stage._rest_background




lines 222, 225:




self.hole = A_plate

	Setting self.hole = (raw_a > 0.01) marks the stationary 3 px inward-feathered rim (0 < o["alpha"] < 1) as hole = 1.0, while Frame 0 forces fill = 0. At f=8 (S05_SH016, S08_SH002) and f=24 (S05_SH020), (fill > 0.5) & ~base flags that stationary rim (ratio = 1.87..2.33) as false fill_invents REVIEWs.	Keep A_plate = np.maximum(A_plate, (raw_a > 0.01)) for self.plate, and set self.hole = np.maximum(A_hole, o["alpha"]) so fill * (1 - a) = a * (1 - a) <= 0.25 < 0.5 at rest.
6	BLOCK	

explainer_engine/production/direction.py




resolve (lines 403–432) &




explainer_engine/production/directed25d.py




Stage.view, _keep_boxes, _fit_zoom

	

T6 (run.py) + T7 (shot_split.py) split-shot defects:




1. When T7 splits still_25d shots 
>5 s (S02_SH008, S05_SH020, S08_SH002) into <a>/<b>, part["spine"] only has that part's words. D.resolve raises ValueError: word not spoken in this shot, and run.py:_resolve_direction_plan's fallback D.resolve(..., spine=None) raises ValueError again — dropping all cameras, handheld, and living effects!




2. directed25d.Stage ignored plan["framing"] = {"crop": 1.35, "focus": [fx, fy]} on Part B.

	

1. Store _part_start_frame, _part_end_frame, _parent_frames, _parent_spine on part["spine"][0] in split_long_still, and slice parent camera/rack tracks into the part's frame window in direction.resolve.




2. Honor plan["framing"] (crop floor in _fit_zoom, initial cx, cy in view, and soft = True for faces outside the 1.35x crop window in _keep_boxes).


7	FIX	

explainer_engine/episode/shot_split.py




punctuate_spine (line 48), _centre (line 59), _resolve_focus (line 87), split_long_still (line 260)

	

1. punctuate_spine bails out if any(is_clause_end(w) for w in out) (e.g. final period), failing to recover internal clause punctuation.




2. _resolve_focus calls d.get("living").get("parts"), crashing with AttributeError when seen["living"] is a list (all real direction files).




3. _centre misses points/parts/where.




4. bounds_f does not clamp to w_next["start_frame"] (risking cutting into the next word) and forgets to shift w["frame"].

	

1. Use all(is_clause_end(w) for w in out) in punctuate_spine.




2. Handle seen["living"] as list or dict, and support where, points, parts in _centre.




3. Clamp raw_f = min(raw_f, int(nxt_f)) and set nw["frame"] = nw["start_frame"].


8	NOTE	

explainer_engine/production/directed25d.py




FACE_MIN_PX = 55.0 (line 57) &




living_fx.py STAR_GAIN = 2.2

	

1. S05_SH020 face_intact is NOT_RUN (faces: 0, kept_faces: 11) because all 11 faces are 28..42 px < 55 px.




2. S02_SH008 fx_first_stars packs up to 60 bright 4-point crosses into a 
6%×6% box (222.03 levels).

	QA checks: (1) Add crowd head-and-shoulders patch NCC fallback when kept_faces > 0 and faces == 0 (ncc >= 0.85, hypothesis / REVIEW per D-59); (2) cap star density per 
1% box area (<= 2.0, hypothesis / REVIEW per D-59).
(c) Changed Files (In Full)
explainer_engine/production/directed25d.py
Python
[CODE 0]
explainer_engine/production/direction.py
Python
[CODE 1]
explainer_engine/production/living_director.py
Python
[CODE 2]
explainer_engine/episode/shot_split.py
Python
[CODE 3]
explainer_engine/qa/motion_intent.py
Python
[CODE 4]
tests/unit/test_s6_review_fixes.py
Python
[CODE 5]
(d) pytest Command
Bash
[CODE 6]

(Result: 65 passed, 0 failed).

(e) NOT CHECKED

Full MP4 video playback for the other five shots (S01_SH001, S02_SH008, S05_SH016, S06_SH001, S08_SH002): Only their 4-row comparison contact sheets (renders/<SHOT>_C5_vs_new.jpg, 0/33/66/100%) and full telemetry (renders/results.json, c5_inputs/render_results_<SHOT>.json) were included in s6_review.zip; only S05_SH020 had full MP4 videos attached.

Real episodes/ep_truce_1914/clock/timing.json: Not included in s6_review.zip (render_driver/render_shot.py noted no clock/timing.json is published).

Live GPU re-extraction via SAM 2.1 / BiRefNet / Depth Anything v2 / LaMa: Not run inside the CPU sandbox; verified via synthetic and reconstructed Stage / understand fixtures in pytest.

Audio muxing and loudness gates (stage_sound / stage_assemble): Out of scope of the visual 2.5D render package.