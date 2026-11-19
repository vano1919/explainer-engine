Gemini said

დღევანდელი living_director.py კარგად მართავს მხოლოდ ერთი კადრის შიგნით 2.5D ბუნებრივ ეფექტებს, ამინდის ჭერსა და ხმის მანძილს, მაგრამ ბრმაა მთლიანი ფილმის რეჟისურის მიმართ.
ის ვერ წყვეტს კადრის ზომას, ვერ არჩევს კამერის მოძრაობას სურათის გეომეტრიული უსაფრთხოების მიხედვით და თითქმის ყველა კადრს ერთნაირ push-ს ანიჭებს.
გვერდითი პარალაქსის (orbit / ძლიერი truck) დროს კი, როცა ფიგურები კიდეებთან ან მრავალშრიან სიღრმეშია, ადამიანები კადრიდან იჭრებიან ან დეფორმირდებიან.
ჩვენ გვჭირდება ერთიანი სცენის რეჟისორი (scene_director.py), რომელიც ტექსტის განზრახვას, სურათის გეომეტრიას (understand.py) და მეზობელ კადრებს ერთდროულად აანალიზებს.
ქვემოთ მოცემულია დღევანდელი კოდის ზუსტი აუდიტი, ახალი რეჟისორის არქიტექტურა, ცოდნის ბაზა (director_knowledge_base.json) 16 რეალური კადრის მაგალითით (ep_truce_1914) და 6-ნაბიჯიანი უფასო CPU გეგმა.
ყველა გადაწყვეტილება მოწმდება როგორც ავტომატური კონტრაქტით, ისე ვიზუალური კონტაქტ-ფურცლის (contact_sheet.png) ტესტით.

Research Grounding: How Virtual Cinematography, Documentary Editing & LLM Directors Solve Text + Picture -> Shot
Domain	Key Systems & Papers	Core Mechanism We Adopt
Virtual Cinematography & Editing Rules	The Director's Lens / Toric Space (Lino & Christie, 2015); Thinking Like a Director (Wu et al., 2018); Automatic Cinematography & Editing (Galvane et al., 2015); Intelligent Camera Control Using Behavior Trees (Markowitz et al.)	Encode shots as camera idioms (establishing, two-shot, reaction, insert) solved via screen-space geometric constraints (lead room, safe margins, never cutting joints at neck/knees/ankles) and Markov transition matrices enforcing the 180° axis of action and 30°/scale-step rule across cuts.
Editorial Priority & Eye-Trace	Walter Murch's Rule of Six (In the Blink of an Eye); StudioBinder Eye-Trace Analysis; Walter Murch — Dense Clarity, Clear Density	Prioritize Emotion (51%) > Story (23%) > Rhythm (10%) > Eye-Trace (7%) > 2D Plane (5%) > 3D Space (4%). Track focal_xy across cuts so the viewer's eye lands near the outgoing focus point, and prevent audio "logjams" by capping concurrent foreground stems.
Transcript-Driven Documentary Editing	QuickCut (Truong et al., UIST 2016); B-Script (Huber et al., CHI 2019); RoughCut Dialogue Idioms (Leake et al., 2017)	Align B-roll, cut-ins, and helper graphics directly to spoken word onsets and clause boundaries via dynamic programming over the timed transcript spine rather than arbitrary fixed timers.
LLM Director Agents (2024–2026)	FilmAgent (SIGGRAPH Asia 2024 / arXiv:2501.12909); MovieAgent (arXiv:2503.07314); CamPilot (arXiv:2609.10943); LAMP (CVPR 2026); Auto-Director (arXiv:2610.28346); Hybrid Cinematography (arXiv:2610.12455); Awesome-Video-Agents	Decouple Directorial CoT Planning (intent 
→ shot size, angle, motion primitive from a discrete operator library) from Previs/Critic Verification (checking 2D/3D proxy bounds before rendering so hallucinated or clipping trajectories are rejected upfront).
2.5D Parallax, Map Grammar & Visual Foley	3D Photo Inpainting (Shih et al., CVPR 2020); DepthFlow; Map Animation Skills; Manim MovingCameraScene; FoleyCrafter (arXiv:2407.01494); MMAudio (CVPR 2025); Diff-Foley	Bound 2.5D camera translation by disocclusion hole width and foreground edge proximity; chain map camera states (theater overview -> sector fly-in -> tactical card); synthesize foley strictly from visible on-screen kinematics and semantic negative prompts (blocking modern/anachronistic tags).
1. VERDICT: Audit of Our Director's Knowledge Today

Today's director logic is split across six disconnected modules (living_director.py, router.py, maps/actions.py, shot_split.py, cinematic_transitions.py, sound_plan.py). It excels at intra-shot 2.5D atmospheric scoring and diegetic audio filtering, but is blind to sequence-level cinematography, picture-safe camera geometry, and helper variety:

Decision Area	What It Decides Well Today (file:function)	What It Decides Blindly or Not at All (file:function)
1. Lane Choice (60/30/10)	episode/router.py:route_shot (L71–90) & talking_check (L127–146) deterministically route speaking heroes (Q7) and regex BODY_ACTION verbs (L29–40) to video, and MAP_WORDS (L45–46) to map_action. living.py:plan (L161–162) flags ROUTE LP-10 when people_mid_or_close exceeds LONG_PEOPLE_S.	Regex-blind to duration & mix: router.py:route_script (L92–106) routes shot-by-shot without checking the 60/30/10 duration target (mix_report, L109) or LP-10 notes—leaving S02_SH008 (10.0s), S05_SH020 (7.75s), and S08_SH002 (8.75s) as unsplit 2.5D stills in production_script.json.
2. Shot Type & Size	episode/sound_plan.py:distance_of (L217–225) reads camera_spec.shot_size and composition planes (foreground/midground/background) to set audio distance (close/medium/distant). shot_split.py:split_long_still (L308–309) applies a 1.35x cut-in crop on part B.	Zero shot-size validation against picture: living_director.py:direct (L494–563) never inspects or overrides shot_size. It computes face["share"] in live_faces (L172) solely to suppress near-lens snow (FACE_CLOSE = 0.02, L329), never checking if a scripted medium_close_up is actually a wide group photo.
3. Camera Move & Picture Safety	living_director.py:choose_camera (L368–437) anchors word accents to named seen.objects (_words_to_camera, direction.py:308), enforces PRE_ACCENT_RATE (L414), and adds handheld (0.3) so the camera never freezes (L435). keep_in_frame (L440–453) lists live faces and active lights.	Monotonous push & unsafe lateral moves: In choose_camera (L396–407), almost every shot defaults to push (in ep_truce_1914, 16 of 22 still_25d shots push in). Worse, L424 triggers truck (TRUCK_STRENGTH = 2.0) whenever abs(c[0] - prev[0]) > 0.2 without checking if outer figures sit near x < 0.12 or x > 0.88 or span large depth steps (understand.py:edge_alignment, L184)—cutting off peripheral people or stretching background sheets. pull, pan (pure 2D crop-pan without parallax angle change), tilt, and rack_focus are never chosen automatically (rack_focus is only parsed in direction.py:428).
4. Living Effects & Weather	living_director.py:candidates (L205–284), decide_weather (L300–341), and living.py:plan (L111–170) score VARIANTS by LP-04, enforce the 5-step weather ceiling (open_sky -> light -> picture -> words -> neighbours), auto-inject cold breath on YuNet mouths (L276), and skip thin wire (L241) or on_body cloth (L243).	Blind to cross-shot effect fatigue: living.py:plan picks the same top-scoring mist + sun_shaft + fire_flicker combination on every trench shot without checking if the previous 3 shots already used sun_shaft.
5. Transitions	edit/cinematic_transitions.py:select_optimal_cinematic_transition (L107–181) enforces ED-04 (hard cuts inside a scene, map_to_location_zoom_through for map$\rightarrow
scene,‘cross
d
	​

issolve
8
	​

f‘forscene\rightarrow$map and segment boundaries).	Disconnected from actual director tracks & map chains: direction.py (L26–29 of S02_SH008.direction.json) leaves transition_out untouched ("unchanged from the script"). compute_visual_continuity_alignment (L59–104) reads static camera_spec.camera_move strings instead of living_director.py's actual tracks, and select_optimal_cinematic_transition (L138–160) has no is_a_infographic and is_b_infographic branch, dropping consecutive maps (S02_SH001->002->003, S05_SH001->002) into abrupt hard_cut_with_jl_bridge.
6. Sound Design	living_director.py:choose_sound (L678–788) and episode/events.py:visual_events (L213–345) enforce AV-07/BP-192: only visible elements sound, words step distance one level closer (L733), cold scenes block insects/birds (COLD_FORBIDS, L588), and counters get eased ov_tick trains + ov_thud (L662–674).	No stereo pan from object X and blind to LTX dialogue/foley: living_director.py never runs on video shots (sound_plan.py:shot_events L329 leaves spoken/action words as unplaced candidates unless manually authored in sound_events), and cue_sheet.py (L314) pans SFX by a cyclic modulo ((n_ev % 5) - 2) * 0.15 instead of the visual element's where[0] coordinate.
7. Pacing & Rhythm	shot_split.py:split_long_still (L183–311) splits still_25d shots 
>5.0 s at punctuation boundaries in memory. living_director.py enforces ACCENT_LEAD_S = 1.0 (L49) and HOLD_MAX_S (direction.py:345).	Flat velocity across emotional arcs: choose_camera uses one fixed BASE_RATE = 0.015 (L46) whether the scene is a tense sniper warning (S02_SH004) or a hushed burial psalm (S05_SH020), and maps/actions.py freezes instant map actions at ANIM_FRAMES = 18 (0.75s, L52).
8. Helper Style Variety	maps/actions.py (L41–46, L538–545) supports 17 action kinds on geo plates or gradient card_base (counter, bar_grow, progress_bar, split_compare).	Only 1 helper archetype used in practice: In ep_truce_1914, all 5 helper shots (S02_SH001..003, S05_SH001..002) are top_down_map. The director has no dispatch rules for archival documents, letters, newspaper clippings, telegrams, tactical trench diagrams, or timeline cards—even when S02_SH008 narrates the Pope's appeal and S08_SH001 narrates "In January, British newspapers printed their letters."
9. Shot-to-Shot Continuity	living_director.py:weather_jumps (L344–360) checks CT-08 weather continuity, and choose_sound (L762–765) continues prev_beds in the same location.	Zero camera/eye-trace/map-view memory: choose_camera (L368) does not even accept prev or next_shot as parameters! It can pick the exact same camera move (push -> push -> push in S08_SH001..004), violate the 30°/scale-step rule, jump focal_xy across the screen, and reset maps/actions.py:_first_view (L167) between consecutive maps.
2. THE DIRECTOR WE NEED: Compact End-to-End Decision Architecture

The unified Scene Director (explainer_engine/production/scene_director.py) runs at Stage G6.5 (direction, after pictures + voice word-spine alignment, before clips). For every shot 
𝑖
i, it takes (shot[i], spine[i], seen[i], layers_manifest[i], decision[i-1], shot[i+1], episode_state) and executes a 5-stage pipeline:

(a) Shot Grammar & Idiom Table (Narration Intent -> Full Directing Spec)

The director classifies each shot's narration + dramatic beat into one of 12 canonical documentary idioms (inspired by Wu et al.'s editing patterns, QuickCut, and CamPilot):

Idiom ID	Narration Intent / Trigger Cues	Lane (route)	Shot Size	Primary Camera Technique (Safe Fallback)	Living Effects / Helper Layer	Transition Out (ED-04)	Sound Design Pattern
IDM_HOOK_ACTION	Cold-open physical jeopardy / kinetic action (0–4s, verbs of motion/danger)	video (LTX)	medium_wide 
→ wide	tilt_up or tracking_shot following body vector	Clip native motion + era grade	hard_cut (J-cut -0.25s foley lead)	Close foley (footsteps_dirt/cloth) + tense wind bed; zero music until beat turn
IDM_ESTAB_HORIZON	Time/place anchor ("Christmas morning, 1914", "By late afternoon...")	still_25d	extreme_wide / wide	crane_up (if sky_share >= 0.25) or pan_crop_2d (1.8%/s)	mist (2 banks) + sun_shaft / light_fade + cloud_drift	hard_cut (in-scene) or cross_dissolve_8f	Open-air bed (wind, distant) + room tone; camera silent
IDM_SCALE_REVEAL	Pivot from individual to mass scale ("thousands of soldiers", "neither moved")	still_25d	wide 
→ extreme_wide	pull_back (2.0%/s, ease_out from centre/hero)	mist + grouped glow/fire + breath	hard_cut or cross_dissolve_8f (segment end)	L-cut from prior foley into crowd_murmur (distant) + wind bed
IDM_TWO_GROUP_PIVOT	Contrast/transfer between two sides ("Scottish chaplain... German student")	still_25d (split 
≤5s if 
>5s)	wide / medium_wide	Hold/slow push (1.5%/s) on Group A 
→ word-timed pan_crop_2d or safe truck to Group B	breath on all faces + mist + candle/fire spill	hard_cut on clause boundary	Ambience bed (fire + wind); zero UI/spot clutter during solemn speech
IDM_INTIMATE_PORTRAIT	Internal thought, letter, memory ("Private Thomas Hale had read...")	still_25d	medium_close_up	push_in (1.6%/s) to face + rack_focus (sigma=5px on BG) + handheld (0.25)	breath + fire/candle cheek spill + layers=[0] far particles only	hard_cut (J-cut -0.20s into speaker)	Close hearth/candle bed (fire medium) + paper foley if letter visible
IDM_OBJECT_INSERT	Symbolic prop/evidence ("empty hands", "two spades", "photograph")	still_25d	close_up / medium_close_up	rack_focus (BG$\rightarrow$FG object) + gentle_push (1.4%/s) + handheld (0.3)	dust motes in light + candle/sun_glint + heat_haze	hard_cut (match eye-trace focal_xy)	Intentional quiet bed (ambience_only) so narrator words carry full weight
IDM_DIALOGUE_TURN	Spoken character line or active physical exchange (handshake, haircut, salute)	video (LTX)	medium / medium_wide	Locked tripod or subtle handheld (<= 3.5s per speaker, BP-108)	LTX performance clip (real voice splice at at_read_frame)	hard_cut (J/L bridge 0.20s, 180° axis preserved)	Character voice + Sync-panned foley (pan = (cx-0.5)*1.2) + ducked bed
IDM_MAP_THEATER	Macro campaign movement ("begun in August", "North Sea to Switzerland")	map_action	top_down_map (span >= 400km)	route_pan or scale following spline route_arrow / front_line	Shaded relief (borders=False pre-1945) + route_arrow + progress_bar	cross_dissolve_8f (to next map w/ inherited view0)	map_route_draw (charcoal span) + army_march (distant) + ov_slide date tag
IDM_MAP_SECTOR_FLYIN	Narrowing to specific battlefield ("Here, in Flanders...")	map_action	top_down_map (400km -> 250km)	Inherit prev.view_end 
→ logarithmic fly_to + highlight	Standing front_line (cues="none") + pulsing sector ring	map_to_location_zoom_through (14f into trench)	Low-passed air whoosh (span) + map_pin_set thud + pre-lapped trench foley
IDM_MAP_PATCH_COUNT	Distributed phenomenon + quantitative estimate ("in patches... 100,000 men")	map_action	top_down_map + corner counter	Inherit view0 + slow push (CAM_PUSH=0.75)	Staggered pulse/highlight along line + eased counter box	map_to_location_zoom_through or infographic_number_to_scene_morph	First pulse map_pin_set, rest map_arrive_click (BP-81); 9 eased ov_tick + 1 ov_thud
IDM_HELPER_DOCUMENT	Official decree, printed newspaper, letter text ("Pope asked", "newspapers printed")	map_action (card: true, doc_card)	insert_card	document_ken_burns (pan_crop_2d + 1.12x push onto highlighted quote)	Parchment/newsprint plate + callout highlight box + date stamp	cross_dissolve_8f	ov_slide paper handling + typewriter_key / date_stamp onset
IDM_EPILOGUE_STATEMENT	Final thematic synthesis & title card ("war went on", "remembered they were human")	still_25d	extreme_wide 
→ wide	crane_up into sky (SH003) 
→ still_by_design (handheld 0.25 on SH004)	light_fade + smoke_drift + fire_flicker	fade_to_black (24f: 12f out, 12f in)	Reflective music cadence + wind/fire bed tailing into room tone
(b) Picture-Aware Camera Feasibility Matrix (Why People Got Cut Off & How the Director Prevents It)

When the renderer (directed25d.py) executes a 3D parallax camera move (orbit, truck, crane), foreground layers shift by 
Δ
𝑥
∝
strength
⋅
(
𝑑
layer
−
𝑑
focus
)
Δx∝strength⋅(d
layer
	​

−d
focus
	​

) while background pixels warp by bg_depth. This causes two visual failures the creator spotted:

Viewport Edge Clipping: Lateral angle changes (orbit, or truck with TRUCK_STRENGTH = 2.0) push characters whose bounding boxes sit near the left/right edges (x_min < 0.12 or x_max > 0.88) out of the frame.

Depth-Discontinuity Tearing & Crowd Rubber-Sheeting: When an unlayered group (layer: false, like the 11 soldiers in S05_SH020) or a high-disparity boundary (max_grad_depth > 0.35) is subjected to a 3D angle change (orbit or wide 3D truck), faces shear or LaMa inpainting holes (hole_share > 0.08) disocclude past their 512px tile margin.

The director computes a Geometric Feasibility Vector from understand.py + seen before choosing any camera op:

edge_margin_x = min(min(b[0] for b in person_boxes), min(1.0 - b[2] for b in person_boxes)) (minimum horizontal clearance of any person/face from frame edge).

edge_margin_y = min(min(b[1] for b in person_boxes), min(1.0 - b[3] for b in person_boxes)) (vertical clearance).

depth_spread = np.percentile(depth, 95) - np.percentile(depth, 5) and edge_align = understand.edge_alignment(depth, masks).

unlayered_people = any(not o.get("layer", True) for o in seen.objects if o in people).

Camera Technique	How It Moves the Picture	Picture Conditions Required (PASS)	Hard Veto (FORBIDDEN on That Photo)	Safe Automatic Fallback
push_in (2D/2.5D axial zoom toward target_xy)	Scales outward from target_xy; zero lateral angle change; zero disocclusion behind central subject	Any photo where keep_in_frame faces lie within 1 / zoom_end crop box around target_xy	Secondary kept person sits outside target_xy ± (0.48 / zoom_end) (would be cropped out by zoom)	Shift target_xy to midpoint of all kept faces, or cap strength <= 0.65
pan_crop_2d (Pure 2D horizontal pan inside a 1.12x overscan crop, zero 3D angle change)	Slides a rigid 2D window horizontally from x_start to x_end; zero depth warp, zero LaMa hole reveal, zero shearing	Wide group or document (S05_SH020, S01_SH005) where target_B.x - target_A.x >= 0.18 and kept faces fit inside 0.89 * W window	Kept faces simultaneously span 
>0.88∗W AND both must remain in frame at the end of the shot	Keep overscan = 1.06 and pan ±3% toward target while holding both groups inside keep_in_frame
truck_25d (Multi-plane lateral dolly with parallax shift)	Shifts FG masks relative to LaMa plate by (d - d_focus) * strength	edge_margin_x >= 0.14, edge_align >= 2.2, hole_share <= 0.06, and not unlayered_people (or bg_depth flattened inside crowd boxes)	edge_margin_x < 0.14 (cuts peripheral people!) OR unlayered_people without flat depth OR edge_align < 1.8	Downgrade truck_25d 
→ pan_crop_2d (horizontal pan without angle change)
orbit_small (3D yaw angle change around d_focus)	Rotates viewing ray across depth planes; highest disocclusion risk	Single isolated central hero (len(people) == 1), 0.28 <= cx <= 0.72, edge_align >= 2.8, sam_score >= 0.88, hole_share <= 0.04	Banned (FORBIDDEN) whenever len(people) >= 2, edge_margin_x < 0.22, unlayered_people == True, or thin FG objects exist	Downgrade orbit_small 
→ push_in + rack_focus
pull_back (Overscan 1.15x 
→ 1.00x reveal)	Starts cropped at 1.15x on focus_xy and eases out to full frame 1.00x (zero border pad needed)	Initial 1.15x crop does not slice through a face or neck joint (Markowitz et al.)	Start crop boundary intersects any face box in keep_in_frame	Adjust initial crop 1.12x..1.18x or shift focus_xy so all faces are either cleanly inside or revealed cleanly
crane_up / tilt_2d (Vertical rise toward sky/horizon)	Vertical crop-pan or 2.5D Y-parallax toward upper frame	sky_open == True, sky_area_pct >= 15%, bottom subjects have edge_margin_y >= 0.12	Indoor/dugout shot (sky_open == False) or bottom face y_max > 0.86 (would cut chin/chest)	Downgrade crane_up 
→ slow push_in toward horizon light
rack_focus (Depth-guided defocus transfer)	Shifts Gaussian/lens blur (sigma 0 -> 5.5px) between depth < 0.4 and depth > 0.6	Bimodal depth separation (`	d_fg - d_bg	>= 0.28, e.g.,S02_SH005,S08_SH002`)
(c) Variety & Rhythm Across the Film

To prevent monotonous camera and helper choices, scene_director.py maintains a rolling Episode State Window across shots 
1
…
𝑁
1…N:

No Two Identical Camera Moves in a Row (CAM-VAR-01): For consecutive still_25d shots 
(
𝑖
−
1
,
𝑖
)
(i−1,i), primary_op[i] != primary_op[i-1]. If both shots map to push_in by default (e.g., S02_SH008 
→
→ S02_SH009, or S08_SH001 
→
→ S08_SH002), shot 
𝑖
i automatically selects the idiom's secondary safe move (pan_crop_2d, pull_back, rack_focus + handheld, or crane_up) and records the override reason.

Sliding-Window Cap on push_in (CAM-VAR-02): Within any 5 consecutive non-map shots, push_in may appear at most 2 times (
≤
40
%
≤40%).

Pacing Curve Tied to Segment Mood (PACE-01): Base camera speed and cut density scale with sound_plan.MOOD_INTENSITY:

reflective / peaceful / tragic (burial S05, epilogue S08): base_rate = 0.012/s, max_still_s = 5.0s, gentle ease (ACCENT_S = 1.6s).

tense / dark (sniper trench S02, Boxing Day S07): base_rate = 0.018/s, max_still_s = 4.2s, sharper word accents (ACCENT_S = 1.0s).

aggressive / hook (S01_SH001..003): rapid cuts (2.0–4.5s), base_rate = 0.022/s.

Helper Visual Diversity (HLP-VAR-01): The 10% helper lane (map_action) rotates across 4 distinct visual archetypes so the viewer never sees 5 identical relief maps:

tactical_relief_map (S02_SH001, S02_SH002): Natural Earth shaded relief (borders=False) + spline arrows/front-lines + corner timeline progress_bar.

sector_radar_zoom (S02_SH003, S05_SH001): Tight sector view (250km) + pulsing trench nodes + standing front-line (cues="none").

data_counter_overlay (S05_SH002): Map or card_base with large typography counter (100,000 men) + comparative bar_grow.

archival_document_card (S02_SH008a Papal decree / S08_SH001b January 1915 newspaper letter): Styled period newsprint/parchment card with highlighted quote callout and date_stamp foley.

(d) Continuity With Previous & Next Shot (prev & next_shot)

Every shot decision inspects prev (
𝑖
−
1
i−1) and next_shot (
𝑖
+
1
i+1) across five continuity locks:

Eye-Trace & Focal Hand-Off (Murch Rule #4): The incoming shot's initial crop center start_focus_xy is pulled toward prev.end_focus_xy (within focal_distance_norm <= 0.28 when composition allows), so the viewer's eye does not jump across the screen on a hard cut.

30-Degree / Scale-Step Rule (CT-07): When cutting between two shots of the same location/characters (same_location == True), the director enforces 
∣
scale
𝑖
−
scale
𝑖
−
1
∣
≥
0.30
∣scale
i
	​

−scale
i−1
	​

∣≥0.30 (e.g., wide 
→
→ medium_close_up, or shot_split.py's 1.35x cut-in).

180-Degree Axis & Motion Vector Alignment: In S04 (British on left facing right, Germans on right facing left), camera pans/trucks move rightward when introducing the German side (S05_SH020) and leftward when returning to the British side. When prev ends with a rightward pan/truck, next_shot never opens with an opposing leftward whip.

Map Camera Inheritance: When prev.route == "map_action" and shot.route == "map_action" in the same theater (S02_SH001 -> S02_SH002 -> S02_SH003, S05_SH001 -> S05_SH002), shot.view0 is locked to camera(prev_plan, prev_frames - 1) and transition_out is set to cross_dissolve_8f.

Weather & Sound Bed Continuity (CT-08 & J/L Bridges): decide_weather and choose_sound inherit prev weather and ambience beds inside the same location, and schedule a 0.25s (in-scene) or 0.45s (location change) J/L audio bridge before next_shot.

(e) Human-Auditable Decision Log (choice.audit)

Every direction/<shot_id>.json file writes a structured choice.audit block explaining what was chosen, what candidates were rejected, and which rule/picture measurement decided it:

JSON
[CODE block 0, 1151 chars]
3. KNOWLEDGE BASE TO ADD: Concrete Data Schema + 16 Filled Rows for ep_truce_1914

Store this data file at explainer_engine/standards/director_knowledge_base.json (loaded by scene_director.py and checked by direction.check). It contains the machine-readable rules (idiom_grammar, camera_feasibility_rules, variety_and_continuity_rules) and 16 concrete shot direction records for ep_truce_1914 spanning video, still_25d (including shot_split pairs), map_action, and archival_document_card helpers:

JSON
[CODE block 1, 27064 chars]
4. PLAN: 6 Ordered Steps to Build & Verify in Code (100% Free CPU)
Step	Files to Create / Modify	What Changes in Code	Automated + Visual Test That Proves the Director Chose Well (pytest + Visual Check)
1. Add Knowledge Base & Schema Validator	

New: explainer_engine/standards/director_knowledge_base.json




Edit: explainer_engine/production/direction.py (CAMERA_OPS, check)

	Add pan_crop_2d (pure 2D overscan crop-pan without 3D angle change) and archival_document_card to direction.py. Add _feasibility(d), _variety(directions), and _audit_present(d) checks so any orbit_small on 
≥2 people, any truck_25d with edge_margin_x < 0.14, or any missing choice.audit key returns FAIL.	pytest tests/unit/test_director_kb.py — loads director_knowledge_base.json, runs direction.check() across all 16 Truce rows, and asserts 0 FAIL on valid rows and deterministic FAIL when injecting an orbit_small into S05_SH020.
2. Upgrade Picture Understanding With Safe-Move Geometry	Edit: explainer_engine/production/understand.py (understand) & explainer_engine/production/directed25d.py (Stage.__init__, render_frame)	In understand.py, write geometry metrics into manifest.json: person_boxes, edge_margin_x, edge_margin_y, sky_area_pct, fg_bg_depth_delta, edge_alignment, and hole_share. In directed25d.py, implement op == "pan_crop_2d" (pure 2D bicubic window pan inside 1.10x overscan with z_parallax = 0.0) and flatten bg_depth inside every detected person box (grad(bg_depth) == 0).	Visual + Pixel Test (tests/unit/test_camera_safety_visual.py): Renders S02_SH008 and S05_SH020 at [0%, 25%, 50%, 75%, 100%] into a 5-column contact_sheet_safety.png, asserting: (a) 100% of keep_in_frame face boxes stay 
≥4% inside frame borders on every frame, (b) rest_seam <= 0.02, and (c) zero face-aspect distortion (`
3. Upgrade living_director.py to Full scene_director Pipeline	Edit: explainer_engine/production/living_director.py (choose_camera, direct) & explainer_engine/episode/shot_split.py	Pass prev_direction, next_shot, and episode_state into direct() and choose_camera(). Match narration + seen to idiom_grammar; auto-split still_25d shots 
>5.0s via shot_split.split_long_still; filter candidate camera moves through camera_feasibility_rules; enforce CAM-VAR-01/02 (no two identical moves in a row, 
≤2 pushes per 5 shots); write choice.audit.	pytest tests/unit/test_scene_director_choices.py — runs direct() over all 84 shots of ep_truce_1914 on CPU, asserting: (a) 0 consecutive still_25d shots share the same camera.op, (b) push_in share across still_25d drops from 
73% to 
≤40%, (c) all still_25d sub-shots are 
≤5.0s, and (d) every shot writes non-empty choice.audit.
4. Add Map Camera Inheritance, 8-Pos Label Solver & Document Card Helper	Edit: explainer_engine/maps/actions.py (_first_view, camera, _draw_one, card_base)	Lock view0 to prev_map.view_end when consecutive shots are same-theater maps (S02_SH001->002->003, S05_SH001->002); replace ANIM_FRAMES = 18 with word-span duration (
≥36f); add the 8-candidate greedy label/chip collision solver; add archival_document_card renderer on card_base (parchment/newsprint header, quote callout, stamp).	Visual Test (tests/unit/test_map_and_helper_visual.py): Renders S02_SH001..003, S05_SH001..002, and S08_SH001b keyframes into contact_sheet_helpers.png, asserting: (a) `
5. Wire Continuity Transitions & Object-X Stereo Audio Pan	Edit: explainer_engine/edit/cinematic_transitions.py (select_optimal_cinematic_transition) & explainer_engine/episode/cue_sheet.py (build)	In cinematic_transitions.py, read the director's actual chosen camera track and transition_out, add the is_a_infographic and is_b_infographic -> cross_dissolve_8f branch, and check focal_distance_norm <= 0.32. In cue_sheet.py, replace modulo panning with visual coordinate panning pan = clip((where_x - 0.5) * 1.2, -0.45, 0.45) and verify eased counter ticks land within 
±1 frame of counter completion.	pytest tests/unit/test_transitions_and_audio_sync.py — verifies all 83 cuts in ep_truce_1914 obey ED-04, map$\rightarrow$map transitions use cross_dissolve_8f, counter knock in S05_SH002 lands within 
±41.7 ms (BP-54), and BP-81 UI cue density has 
0 violations.
6. Wire Stage direction into episode/run.py & Gate G10 Visual Strip	Edit: explainer_engine/episode/run.py (stage_clips, stage_qa) & explainer_engine/qa/motion_intent.py	Wire living_director.direct + directed25d.render_clip into stage_clips; promote cropped-face, rest_seam > 0.04, blown_out > 0.015, and sliding_liveliness < 0.015 checks in motion_intent.py to gate G10; emit a full-episode diagnostic director_audit_strip.png (start/mid/end frame + camera vector arrow + safe-zone overlay per shot).	pytest tests/unit/test_episode_direction_e2e.py — runs stage_clips + stage_qa in --rehearsal CPU mode on synthetic + Truce fixtures, verifying 0 FAIL gates and generating director_audit_strip.png for human inspection in 
<10s.
Complete