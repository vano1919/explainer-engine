1. შეჯამება შემქმნელისთვის (6–10 ხაზი)

დიაგნოზი (9ecdd875): Task 1-მა გაასწორა ლოგიკური ხარვეზები, მაგრამ S08_SH002, S02_SH008 და S05_SH020 რენდერების ვიზუალურმა შემოწმებამ აჩვენა მთავარი პრობლემა: რეჟისორი კვლავ „ბრმა“ და „ყრუა“ — ის კითხულობს მხოლოდ სცენარის ტექსტს (production_script.json), არ ამოწმებს რეალურ ნახატს (start_01.png) და ყველა ნიღბის კოორდინატს სვამს ცენტრში ([0.5, 0.5]).

რას ვცვლით არქიტექტურაში: ვქმნით ერთიან გადამღებ ჯგუფს (სცენარისტი -> აღქმა -> რეჟისორი -> ხმის რეჟისორი -> მემონტაჟე), სადაც სცენარისტი თავისუფალი, ცოცხალი ენით წერს კადრის მხატვრულ დავალებას (director_brief: განწყობა, რა უნდა იგრძნოს მაყურებელმა, გარემოს ფიზიკური სიმართლე), ხოლო რეჟისორი ჯერ უყურებს ნახატს (understand.py + perceive_picture.py) და მხოლოდ ამის შემდეგ იღებს გადაწყვეტილებას.

სურათისა და სცენარის შეთანხმება: ნახატი წყვეტს, რა არის ფიზიკურად კადრში (რათა არ გავაცოცხლოთ არარსებული საგანი ან დახურული ოთახის მტვერი ღია სანგარში, როგორც S08_SH002-ში), ხოლო მთხრობელის ტექსტი და სცენარისტის brief წყვეტს აზრსა და განწყობას (ომის სიცივე, ტანჯვა, მიტოვებულობა); თუ ნახატი ეწინააღმდეგება თავად მთხრობელის ამბავს, კადრი ხვდება თავიდან დასახატ სიაში (regeneration_queue.json) და არა ჩუმად გადაწერაში.

არავითარი მექანიკური რიცხვითი კვოტები: LP-08 („მინიმუმ 3 ეფექტი“), BP-185 და ეფექტების ხისტი რაოდენობრივი ლიმიტები იცვლება კონტექსტური, დასაბუთებული გადაწყვეტილებებით — ეფექტების არჩევანს განსაზღვრავს ისტორია, ნახატი და მთხრობელის სიტყვები.

მოძრაობის სრული იზოლაცია (motion_isolation.json): ცეცხლი ირხევა, მაგრამ რკინის ბრაზიერი და თუნუქის შანდალი უძრავია; ორთქლი ადის თომასის ჭიქიდან (S02_SH008), მაგრამ თავად ჭიქა და თითები არ იღუნება; ვარსკვლავები და ყინულის ბზინვარება აღარასოდეს დაედება მავთულხლართებს (S02_SH008) ან საფლავის ჯვრებს (S05_SH020).

ცოცხალი ხმა და რუკები: living_director.choose_sound და sound_of_map პირდაპირ უკავშირდება episode/sound_plan.py::build-სა და episode/events.py::visual_events-ს; რუკებსა (S02_SH001, S02_SH002) და სანგრის კადრებს ეძლევათ ნამდვილი აკუსტიკური სივრცე და სინქრონიზებული ხმოვანი აქცენტები.

რას შეამჩნევს მაყურებელი: S08_SH002-სა და S02_SH008-ში მაყურებელი იგრძნობს გაყინული ღია სანგრის ნამდვილ სიცივეს, მსუბუქ თოვას, ქარს, ცხელი ჭიქის ორთქლსა და მიტოვებული ჯარისკაცების სიმძიმეს (მოჭრილი ფეხებისა და ბრაზიერის გარეშე), ხოლო S05_SH020-ში — სამარისებურ სიმშვიდეს, როცა კამერა შოტლანდიელი კაპელანიდან გერმანელ სტუდენტზე გადადის.

2. Thematic Research Findings: Time-Coded Documentary Analyses, Retention Craft & Evaluated Open-Source Tools
2.1 Ten Time-Coded Analyses of Strong YouTube History & Documentary Films

We analyzed ten benchmark historical and documentary videos across diverse styles (archival WWI chronicles, tactical map documentaries, investigative explainers, and 2.5D animated history) to extract repeatable rules for seven core dramatic situations: (1) Opening Hook, (2) Political Decision / Irony from Above, (3) Strategic Map & Troop Movement, (4) Battle / Escalation, (5) Trench Suffering & Endurance, (6) Emotional / Sacred Moment, and (7) Outcome & Epilogue.

#	Video & Channel	Time Code & Situation	What Is on Screen & Heard at t	The Directorial Decision & Why It Works	Repeatable Method We Take into Explainer Engine
1	The Great War — Dying In Caucasus Snow / Christmas Truce 1914 (Week 22)	00:00–00:38 (Opening Hook) & 06:10–07:45 (Trench Suffering vs. Truce)	At 00:00–00:38, cold wind and low string tension play under freezing mountain/trench imagery before the title card; at 06:10–07:45, the host contrasts high command's relentless orders with frozen mud, wet wool, and spontaneous truce pockets.	Opens on visceral physical environment (freezing snow, mud, exposure) rather than diplomatic dates, anchoring the viewer's empathy in bodily survival before explaining politics.	Situation Method — Trench Suffering (S02_SH008, S08_SH002): Always establish physical exposure (falling snow, rising breath/steam, wind over the parapet) whenever narration contrasts high command or diplomacy with the men in the line.
2	Imperial War Museums (IWM) — The Christmas Truce in 1914 — I Was There: The Great War Interviews	00:12–01:05 (Trench Proximity) & 02:15–03:30 (No Man's Land Encounter)	Veteran voiceover recalls hearing German voices and coughs across a narrow strip of frozen earth; camera performs a slow, unhurried push into archival trench photographs with zero decorative effects, accompanied only by faint cold wind.	When the spoken testimony carries stark human truth, the camera uses a single slow push-in toward faces/hands and strips away visual clutter so the viewer searches the soldiers' eyes.	Situation Method — Intimate Testimony / Epilogue (S08_SH002): On plain, unvarnished historical lines ("Their commanders moved to prevent it..."), use a single slow push toward the human token (hands, portrait, button) with only physically real snow and candle flicker.
3	Extra History — WW1 Christmas Truce: Silent Night (Part 1) (Overview)	00:00–00:45 (Cold Open Paradox) & 03:10–04:20 (Political Irony: Pope Benedict XV's Appeal)	Opens in the dark trench on Christmas Eve before flashing back to August 1914's "Home by Christmas" optimism; at 03:10, Pope Benedict XV's December appeal is shown failing in grand halls while cutting immediately to soldiers shivering in mud.	Creates a sharp vertical irony cut between powerful institutions saying "No" and ordinary soldiers left in the freezing dark ("Nobody asked the men in the trenches").	Situation Method — Political Decision vs. Human Cost (S02_SH008): Start wide enough to show the soldiers' hunched bodies, boots, and brazier in the freezing trench during the diplomatic setup, then push onto the soldier's face on the dry final sentence.
4	Epic History TV — World War 1 (All Parts, 4K)	01:15–02:30 (August 1914 Schlieffen Sweep) & 11:40–13:05 (Race to the Sea & Trench Deadlock)	Shaded-relief map of Belgium and Northern France; as the narrator names August 1914 and the sweep toward the Marne, bold directional arrows draw continuously with a low friction/marching bed and crisp arrival accents on Liège, Brussels, and the Marne.	Every map movement is word-locked: the arrow's head leaves Aachen on the time-marker word ("August") and reaches its terminus on the clause end ("Christmas" / "Marne"), backed by a continuous friction draw sound plus a terrain bed.	Situation Method — Strategic Map Movement (S02_SH001, S02_SH002): Pair every route_arrow and front_line span with map_route_draw continuous foley + low theater ambience (place_bed), never dead silence.
5	Kings and Generals — How the Union Finally Won the War (Production Study)	02:05–03:40 (Frontline Stabilization) & 14:20–15:50 (Tactical Sector Zoom)	Top-down illustrated terrain map transitions from continental overview (500+ km) to sector close-up (20 km); unit tokens shift with soft leather/wooden table foley while distant battlefield wind and low brass persist underneath.	Separates map camera moves from map element actions: a gentle camera drift (parallax_dolly) over the map rides the environmental bed, while a fast zoom-in to a battle sector (S02_SH003 Flanders) gets a subtle low whoosh/paper shift.	Situation Method — Map Zoom to Sector (S02_SH003, Q3): Slow map camera drifts stay on the terrain bed (silent_by_design), whereas purposeful rapid zooms into a named sector (span_km dropping > 3x) carry a soft low-frequency air/paper transition cue.
6	HistoryMarche — Marlborough's Masterpiece	00:45–02:10 (Two-Sided Line Confrontation)	Two opposing lines face each other across a narrow field; as the narrator names the left commander and then the right commander, the camera pans horizontally from left to right with a brief hold on each side.	Honours spatial geography in the frame: when two groups share one wide composition and the narrator names Group A then Group B, the camera anchors on Group A during Sentence 1 and pans/cuts to Group B on Sentence 2.	Situation Method — Two-Sided Tableau (S05_SH020): Anchor camera segment 1 on left_group ("Scottish chaplain read the Twenty-Third Psalm") and pan smoothly across the central crosses to right_group ("A German student read it after him, in German").
7	Johnny Harris / Vox Style — How I Make My Maps & Documentary Editing Breakdown (FCPX Tactile Craft Breakdown)	01:30–03:15 (Tactile Map & Archival Cutouts) & 05:10–06:40 (Sound Selling the Visual)	Cutout figures and shaded relief plates move with deliberate easing; every label appearance (August 1914), border draw, or archival photo settle is married to a tactile physical sound (paper thud, charcoal stroke, mechanical click).	As documented in the craft breakdown: "Sell it with sound. A soft paper thud as the element lands, a shutter click on a hard cut. This is doing more work than you think." Tactile sound transforms flat 2D graphics into physical objects.	Situation Method — Helper & Data Graphics (S05_SH001, S05_SH002): Every label, route_arrow, front_line, and patch spread in maps/actions.py / episode/events.py locks its visual onset frame to a physical cartographic sound in sound_plan.py.
8	LEMMiNO — Grazed by the Apocalypse & The Enduring Mystery of Jack the Ripper (Pacing Analysis)	00:00–01:20 (Measured Hook) & 18:40–20:15 (Atmospheric Restraint)	Dark, high-contrast illustrated scenes with only 1 or 2 moving elements (falling rain/snow or a single flickering streetlamp) held under a calm, unhurried voiceover and deep sub-bass room tone.	Proves that restraint creates authority: in dark or tragic beats, animating 1–2 atmospheric layers with high contrast and clean isolation holds viewer attention far better than busy particle soup.	Situation Method — Dark / Tragic Restraint (G4, S05_SH020, S08_SH002): Drop mechanical effect-count floors (LP-08); in solemn/tragic shots, fewer, cleaner, physically isolated motions create higher retention and prestige look.
9	Mustard — The Soviet Airliner Designed To Crash & What Really Happened To Giant Flying Boats?	00:00–00:50 (Cold Open Tension) & 04:15–05:30 (Sound-Driven Scene Transition)	The sound of the next environment (wind, engine rumble, rain) creeps in 0.25–0.40 s before the hard visual cut (J-cut), and the previous shot's ambient tail decays 0.25 s after the cut (L-cut).	Eliminates the "slideshow wall" between shots (BP-191): continuous environmental beds and J/L overlaps make a sequence of rendered clips feel like one continuous film reel.	Situation Method — Scene & Shot Handover (assemble.py): Keep the scene's ambient bed continuous across intra-scene cuts and overlap point-sound tails across cut_window_s (BP-191).
10	Simple History / BBC Archive — Christmas Truce (1914) & 1968 BBC Archive: Remembering the Christmas Truce	00:20–01:10 (Trench Conditions) & 02:45–03:40 (Burial in No Man's Land & Captain Stockwell's Signal)	Contrasts the festive myth of the truce with the grim reality: burying frozen bodies between the lines (S05_SH020) and officers like Captain Stockwell firing three shots into the air on Boxing Day (S07_SH005) before the war resumes.	Keeps the truce grounded in war and mortality: even during the truce, the men are standing among graves and barbed wire in freezing mud, and the ending is poignant because the machinery of war immediately closes back in.	Situation Method — Action & Return to War (S07_SH005, S08_SH002): Never let the truce look cosy or indoor-warm; maintain cold winter fog, frost breath, and stark acoustic contrast (revolver shots echoing into cold fog in S07_SH005).
2.2 Official YouTube Studio Retention Guidance & Film Craft Principles

YouTube Studio "Key Moments for Audience Retention" (Official Google/YouTube Help 9314415, YouTube Content Tab Analytics Tips 12942217, Virvid 2026 Retention Graph Analysis, AIR Media-Tech Retention Guide):

YouTube Studio tracks four diagnostic curves: (1) Intro (first 30 seconds), (2) Top Moments (flat line = zero drop-off), (3) Spikes (rewatched/shared visual or emotional peaks), and (4) Dips (abandonment caused by visual stagnation, audio mismatch, or confusing jumps).

Why Dips happen in AI explainer pipelines: A viewer drops off when (a) a static or slow shot lingers > 5 s without a camera focal shift on the spoken clause (D-131), (b) a jarring visual defect pulls the eye out of the story (sliced feet/brazier in S02_SH008, sparkling crosses in S05_SH020), or (c) audio cuts dead at shot boundaries.

Walter Murch's Rule of Six (UC Berkeley iSchool, StudioBinder, Video Essay at 00:42–03:15) & Eye-Trace (Artlist Guide):

Emotion (51%) + Story (23%) + Rhythm (10%) + Eye-trace (7%) govern every cut and camera move.

Ken Burns Framing & Layered Depth Inpainting (PBS Civil War Study, Ken Burns Composition Guide, Shih et al. CVPR 2020 LDI Paper):

Never slice a subject's grounding support (boots on trench floorboards, base of a brazier basket) near the frame edge during a push-in; either preserve the full base inside a safe margin or re-center cleanly onto the upper body/face.

Randy Thom & Michel Chion Sound Design (Randy Thom — Designing a Movie for Sound, Michel Chion — Audio-Vision PDF, Walter Murch — Dense Clarity / Law of Two-and-a-Half):

Sound is conceived with the screenwriter's brief; synchresis welds simultaneous visual motion and sound onsets; Murch's "Law of Two-and-a-Half" warns that layering more than 2–3 simultaneous foreground acoustic/visual elements turns clarity into muddy noise.

2.3 Evaluated GitHub & Hugging Face Tools for Every New Capability (CPU-Only, $0)
Capability Needed	Candidates Evaluated (GitHub / Hugging Face)	Chosen Tool(s) for Explainer Engine	Why Chosen (Quality, CPU Speed & Fit with Existing Repo)
1. Picture Perception & Phrase-Grounded Object Detection (perceive_picture.py)	

• microsoft/Florence-2-base (0.23B) & microsoft/Florence-2-large (0.77B)




• vikhyatk/moondream2 (2B VLM)




• Qwen/Qwen2.5-VL-3B-Instruct-GGUF




• Ultralytics YOLO-World

	microsoft/Florence-2-base + existing understand.py (SAM / Depth-Anything-V2-Small) + OpenCV HSV/mask-geometry analyzer (with moondream2 optional for open-ended VQA)	understand.py already runs Depth-Anything-V2-Small (L94) and SAM (L382). Adding Florence-2-base gives open-vocabulary phrase grounding (<CAPTION_TO_PHRASE_GROUNDING> + <MORE_DETAILED_CAPTION>) in ~0.9s on CPU: it locates any noun in the script/brief ("tin mug", "letter", "brazier basket", "candle holder", "sky", "grave crosses") and proves whether a scripted prop is actually painted or missing.
2. Motion Isolation & Fractional Alpha Matting (motion_isolation.py)	

• pymatting/pymatting (estimate_alpha_lkm) + OpenCV Guided Filter (cv2.ximgproc.guidedFilter)




• ZhengPeng7/BiRefNet (already in understand.py:411)




• hustvl/VitMatte-small

	OpenCV Guided Filter / pymatting at native 1920×1080 + HSV/Luminance Plume Splitter on existing understand.py SAM/light masks	understand.py:427 (refine_fine_edges) already notes that full-frame BiRefNet resizes internally to 1024×1024. By splitting existing 1080p masks locally into mover_mask (bright warm flame plume above grate; rising steam above mug rim) and anchor_mask (rigid iron basket, tin holder, mug body clamped to 0.0 displacement) with guided-filter feathering, we get zero holder warp at full 1080p on CPU in < 80 ms.
3. Motion-Leak & Stillness Verification (qa/look_and_listen.py)	

• OpenCV Dense Optical Flow (cv2.calcOpticalFlowFarneback) (VeroMotion HF Benchmark, Sana Flow Eval)




• RAFT-Small CPU (torchvision.models.optical_flow.raft_small)

	Camera-Compensated Farneback Dense Optical Flow (cv2.calcOpticalFlowFarneback) + Pixel-Diff Mask Ratio	Subtracts the known camera homography/crop warp from frame 
t→t+1, then measures residual flow inside anchor_mask vs. mover_mask and checks sky/snow effect leakage outside sky_mask/snow_mask. Runs in < 0.3 s per clip on CPU with zero external weights.
4. Audio Perception & Acoustic Verification (qa/perceive_audio.py)	

• MIT/ast-finetuned-audioset-10-10-0.4593 (86.6M, 527 AudioSet classes)




• LAION-AI/CLAP (laion/clap-htsat-unfused)




• snakers4/silero-vad




• librosa / scipy.signal

	MIT/ast-finetuned-audioset-10-10-0.4593 + laion/clap-htsat-unfused + scipy/librosa spectral/RMS analyzer	AST verifies that planned diegetic sound classes (Wind, Fire, Crackling, Speech, Music) are genuinely audible in the rendered WAV (not drowned or silent), while CLAP scores text-audio alignment against the shot's director_brief.sound_perspective in < 0.5 s on CPU.
3. Diagnostic Root-Cause Matrix (9ecdd875) & Step-by-Step Build Guide
3.1 Exact Code Root Causes Verified in repo_after_task1.zip (9ecdd875)
Failure / Lead	What the Eye / Code Inspection Sees	Exact Root Cause (file:line in 9ecdd875)	General Fix in Step 2B
S08_SH002 (HF Render, s08_strip.jpg)	Real line: "Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale." Picture is an open, unroofed snow-lined trench at night (sky at y=0..0.15), gloved hands holding portrait + brass button, candle in tin holder on crate ([0.848, 0.375]), two far braziers. Auto-director set sky_open: false, suppressed snow/wind, added warm indoor dust_motes and fast orange far_brazier_embers, and failed LP-08 (only 2 living effects beyond the flames).	

1. living_director.py:1172–1239 (build_shot_direction_from_script) reads screen_composition.foreground: "the edge of a dugout bunk" and lighting_and_time: "warm candlelight at night" without inspecting start_01.png.




2. living.py:151 & living_director.py:1458 enforce LP-08 hard numeric floor (EFFECTS_MIN = 3 -> FAIL).

	

1. New perceive_picture.py + understand.py inspect start_01.png, detect open night sky (y=0..0.15), snow on parapets, and candle at [0.848, 0.375].




2. Driven by the real narration and the creator's cold/suffering intent, animate light snow falling into the open trench, cold wind/breath, and the isolated candle flame (tin holder pinned), dropping indoor dust_motes and far_brazier_embers.




3. Remove LP-08's hard numeric FAIL floor.


S02_SH008 (HF Render, s02_strip.jpg)	

Real line: "In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed. Nobody asked the men in the trenches."




1. Push (strength: 2.5 to [0.5, 0.45]) slices off the bottom of the iron brazier basket and both soldiers' boots (f180..262).




2. fx_seen_stars places twinkling stars across sandbags and barbed wire (y=0.062..0.378).




3. Picture shows Thomas holding a metal mug (not a letter!) and Harris sitting hunched with hands on knees (no rifle!). No snow falls, no steam rises from the mug, no breath from faces.

	

1. living_director.py:1138–1168 (_load_valid_layers) & L1342 assign "where": [0.5, 0.5] to every mask (thomas, harris, brazier) instead of reading _mask_bbox (understand.py:227)!




2. living_director.py:1101 seeds stars at [0.5, 0.15] with radius 15.0 (box: [0.342, 0.062, 0.658, 0.378]), leaking below the y=0.16 sky horizon.




3. episode/run.py:1060 calls direct() without passing picture or faces_px, so faces: [] and no breath/steam is emitted.

	

1. Populate real mask [cx, cy] and bbox from layers/*.png (thomas cx≈0.24, brazier [0.52, 0.69], harris cx≈0.76).




2. Clip sky effects strictly to sky_mask * (1 - fg_mask).




3. Enforce guard_crop_respects_anchors in living_director.py::keep_in_frame (L701): keep the full brazier basket and boots inside the frame during the diplomatic setup, then push cleanly toward Thomas's face & steaming mug on "Nobody asked the men in the trenches."




4. Add light falling snow, rising steam from the mug, cold breath, and isolated brazier fire.


S05_SH020 (HF Render, s05_strip.jpg)	

Real line: "At one burial, a Scottish chaplain read the Twenty-Third Psalm. A German student read it after him, in German."




1. fx_seen_ice (op: "glint", box: [0.342, 0.422, 0.658, 0.738]) scatters sparkle glints across the wooden grave crosses and coats!




2. Camera pushes to dead center [0.5, 0.45] because all 7 masks (left_group, right_group, cross_*) have "where": [0.5, 0.5].

	

1. living_director.py:1102 & L1389 place ice/frost_glint in an unmasked center box [0.342, 0.422, 0.658, 0.738].




2. Mask centroids are hardcoded to [0.5, 0.5], preventing choose_camera (L471) from targeting left_group (cx=0.26) then right_group (cx=0.73).

	

1. Ban unmasked box glint/stars; mask any ground frost shimmer to ground_snow_mask * (1 - fg_union_mask) and suppress decorative glints in tragic/burial shots.




2. Use real mask centroids so camera segment 1 frames left_group ("Scottish chaplain") and segment 2 pans gently across the crosses to right_group ("A German student"), with cold breath rising from both groups.


Leads a–i	Disconnected producers/consumers across living_director.py, directed25d.py, living.py, living_fx.py, direction.py, episode/sound_plan.py, episode/events.py, videolane/scene.py, and qa/*.py.	Exact functions verified in Section 3.2 below.	Wired end-to-end in Steps 1–8 below with zero duplicate pipelines.
3.2 Step-by-Step Build Guide (In Exact Implementation Order for Step 2B)
Step	Goal	What Changes (Exact Real Files & Functions)	Rules Added / Changed / Dropped	How It Is Verified (Tests + Look-and-Listen)	Dependencies	Effort	Risk	What the Viewer Notices
Step 1	Screenwriter Guide & Open-Language Director Brief (G1, G3, G-b)	

• New files: explainer_engine/standards/screenwriter_guide.json + docs/SCREENWRITER_GUIDE.md.




• Existing files updated:




- explainer_engine/schemas/production_script.schema.json: add shots[].director_brief with free descriptive strings (mood, viewer_feeling, physical_truth, focal_priority, sound_perspective, restraint_note, plus optional tags: list[str]) — no closed enums, no numeric effect budgets.




- explainer_engine/scripting/stage_guard.py: register "director_brief": "edit-planner" in V4_OWNERS.




- .claude/agents/edit-planner.md, scene-writer.md, beat-writer.md: update prompts to author director_brief from the spoken line and historical context.




- explainer_engine/episode/run.py::stage_script (L229): validate director_brief presence and non-boilerplate content.

	

• Add SW-01..SW-08 in screenwriter_guide.json & sourced_rules.json (narrative situations, emotional clarity, free-text brief, picture humility).




• Add G1-BRIEF: every shot carries a shot-specific director_brief serving its actual audio_lines text.

	

• Test: tests/unit/test_screenwriter_brief_handoff.py checks schema, stage_guard ownership, and rejects empty/copied briefs or technical shader commands.




• Look: Review director_brief on S08_SH002, S02_SH008, S05_SH020, S02_SH001 against their real narration lines.

	None	Medium	Low	Every shot is guided by a clear human directorial vision tied to the actual spoken words.
Step 2	Visual Perception Engine: The Director Looks at the Picture First (G2, G3, G6, G-e, Leads a, d, i)	

• New file: explainer_engine/production/perceive_picture.py.




• Existing files updated:




- explainer_engine/production/understand.py (picture_geometry at L237, light_mask at L476, understand at L611, load at L742): compute and persist real normalized centroid [cx, cy], bounding box [x0, y0, x1, y1], area share, and top/bottom support y-coordinates for every mask in layers/manifest.json, plus exact sky horizon y_sky_max.




- explainer_engine/production/living_director.py (_load_valid_layers / build_shot_direction_from_script at L1113, direct at L745) & explainer_engine/episode/run.py::stage_clips (L1060): pass picture (start_01.png), faces_px, and perceive_picture output into build_shot_direction_from_script and direct(). Fix the [0.5, 0.5] centroid bug at L1150, 1342, 1389.




- Script-vs-Picture Reconciliation (G-e): Classify mismatches into (a) environment/detail adaptation (e.g., S08_SH002 picture is an open trench, not a dugout bunk -> director adapts to the picture's open trench while keeping the brief's cold suffering mood) vs. (b) story-breaking prop/action conflict (e.g., if narration explicitly speaks about a prop that is contradicted by the painting) -> write to episodes/<ep>/production/regeneration_queue.json (needs_regeneration: true).

	

• Add DIR-EYE-01 (G-e rule): The picture wins for what is physically present in the frame; the narration and director_brief win for meaning and mood; story-breaking conflicts between picture and narration are flagged to regeneration_queue.json.




• Add DIR-EYE-02: Every object/light in seen uses its measured mask/detected [cx, cy] and bbox, never a hardcoded [0.5, 0.5] default.

	• Test: tests/unit/test_perceive_picture_grounding.py on S08_SH002, S02_SH008, S05_SH020 verifies: S08_SH002 detects sky_open=True + candle at [0.848, 0.375]; S02_SH008 computes real centroids for thomas (cx≈0.24), brazier ([0.52, 0.69]), harris (cx≈0.76) and detects mug; S05_SH020 separates left_group (cx≈0.26) and right_group (cx≈0.73).	Step 1	High	Low	The director sees the actual painting: open sky in S08_SH002, the mug and brazier position in S02_SH008, and the two groups of soldiers in S05_SH020.
Step 3	Motion Isolation Engine & Calibrated Leak Gate (G7, Lead b)	

• New files: explainer_engine/standards/motion_isolation.json + docs/MOTION_ISOLATION.md + explainer_engine/production/motion_isolation.py.




• Existing files updated:




- explainer_engine/production/living_fx.py (apply at L381, _particles at L92, _sun_glint at L182, _sparkle at L241, _breath at L301, _surface at L332) & explainer_engine/production/directed25d.py (Stage at L110, render_clip at L1101):




1. Split every light/emitter mask into mover_mask (flame plume above grate/wick; steam plume above mug rim; smoke above chimney) and anchor_mask (iron brazier basket, tin candle holder, mug body, hands/coats clamped to 0.0 displacement).




2. Multiply sky effects (stars, cloud_drift, sun_glint) by sky_mask * (1 - dilated_fg_mask) so stars in S02_SH008 never touch sandbags or barbed wire.




3. Multiply ground frost effects (glint) by snow_ground_mask * (1 - dilated_fg_mask) so fx_seen_ice never sparkles on wooden grave crosses or coats (S05_SH020).

	

• Add MI-01..MI-09 in motion_isolation.json & sourced_rules.json.




• Add gate_motion_isolation_leak (calibrated per D-59 on old vs. new S02_SH008 and S05_SH020): fails if camera-compensated optical flow / pixel diff in anchor_mask exceeds calibrated leak ratio or if sky/ground particles appear on foreground masks.

	

• Test: tests/unit/test_motion_isolation_guards.py fails on Task 1 S02_SH008 (stars on wire, brazier basket motion) and Task 1 S05_SH020 (ice glints on grave crosses) and passes on new renders.




• Look: Inspect zoomed crop strips of brazier, candle holder, mug, barbed wire, and grave crosses.

	Step 2	High	Medium	Flames flicker while the iron brazier and tin candle holder stay rock-solid; zero stars on barbed wire; zero sparkles on grave crosses.
Step 4	Mood-Driven Scene Director & Removal of Numeric Effect Quotas (G1, G3, G4, G6, G-a, G-c, Leads a, b, d)	

• New file: docs/DIRECTOR_GUIDE.md.




• Existing files updated:




- explainer_engine/standards/director_knowledge_base.json: replace count-based rules with Murch's priority hierarchy, situation playbooks, and physical-truth criteria.




- explainer_engine/production/living.py (plan at L111, check at L173) & explainer_engine/production/living_director.py (direct at L745, choose_camera at L471, keep_in_frame at L701, build_shot_direction_from_script at L1113) & explainer_engine/production/direction.py (check at L185, _balance at L328, _families at L335):




1. Remove numeric floors (LP-08, BP-185) from FAIL: The director selects every effect that serves the director_brief and is physically supported by perceive_picture, and records a written reason (why) for each picked and skipped element (BP-196).




2. Cold, War & Suffering Realization (G-c): In S08_SH002 and S02_SH008, animate light falling snow into the open trench, cold breath, rising steam from Thomas's mug (S02_SH008), wind-driven mist, and isolated candle/brazier flames.




3. Anchor-Support Framing Guard (keep_in_frame, L701): Prevent any camera crop from slicing through the bottom of an active brazier/light source or cutting off feet/ankles at the frame edge (S02_SH008), while allowing a clean push onto Thomas's face/mug on the final spoken beat ("Nobody asked the men in the trenches").

	

• Change LP-08 & BP-185: Demote numeric counts (effects_min = 3, families_min = 2) from FAIL to contextual hints; a shot with 1–2 physically isolated effects and a written directorial reason in why passes cleanly.




• Keep & refine BP-196: Keep the living-inventory audit (every visible natural element gets an effect or a written reason why not), grounded in perceive_picture rather than blind text regex.




• Add DIR-CAM-ANCHOR: Camera crop box must not bisect an active fire/light base or slice off boots at the bottom edge.

	

• Test: tests/unit/test_mood_director_and_framing.py verifies S08_SH002, S02_SH008, S05_SH020 direction manifests have written reasons, zero LP-08 failures, intact brazier/boots on S02_SH008 establish, and word-timed pan from left_group to right_group on S05_SH020.




• Look: Render new MP4s + 6-frame contact strips for all 3 shots.

	Steps 1, 2, 3	High	Low	S08_SH002 and S02_SH008 feel freezing, bleak, and human; S02_SH008 never slices the brazier or boots; S05_SH020 moves reverently from the Scottish chaplain to the German student.
Step 5	Video Lane (60%) Brief & Picture Alignment (G1, G3, Lead g)	

• Existing files updated:




- explainer_engine/videolane/scene.py::compose_prompt (L96): read shot.director_brief and perceive_picture(start_01.png) (when start_01.png exists) so LTX motion prompts carry the brief's emotional tempo, physical weather, and motion-isolation rules, and never ask LTX to animate a prop absent from the starting frame.




- explainer_engine/videolane/paid_preflight.py: verify compose_prompt output against perceive_picture(start_01.png) inventory before any paid run.

	• Add VL-BRIEF-01: videolane/scene.py::compose_prompt incorporates director_brief mood/tempo and reconciles starting state with perceive_picture(start_01.png).	• Test: tests/unit/test_videolane_brief_and_picture_sync.py tests compose_prompt on S07_SH005 and synthetic conflict shots.	Steps 1, 2	Medium	Low	LTX video clips stay faithful to the starting painting and the scene's emotional tone.
Step 6	Wire Director Sound into sound_plan.py & events.py Across All Lanes (G5, Leads c, e, f)	

• Existing files updated:




- explainer_engine/episode/sound_plan.py (build at L489, shot_events at L286, design_of at L390, place_bed at L478): wire living_director.sound_of_direction() (L1009), choose_sound() (L906), and sound_of_map() (L1029) directly into sound_plan.build() and shot_events() so the director's sound choices are actually placed into sound_plan.json and rendered by explainer_engine/audio/stems.py.




- explainer_engine/episode/events.py (visual_events at L214, default_audio at L121, episode_events at L414): read director_brief.sound_perspective and map camera velocity (maps/actions.py::camera at L646) so rapid purposeful map zooms (zoom_fast / sector dive like S02_SH003) get a subtle paper/air transition cue while gentle drifts stay silent_by_design (AV-04).

	

• Add SND-DIR-01: episode/sound_plan.py::build must consume living_director.sound_of_direction and sound_of_map (zero dead sound functions).




• Refine AV-04 (Q3): Slow camera moves remain silent_by_design; rapid purposeful map sector dives (span_km ratio > 3.0) may carry a soft low-frequency transition cue (map_sector_zoom).

	

• Test: tests/unit/test_director_sound_wiring.py proves sound_plan.build() invokes sound_of_direction and sound_of_map, and places cold wind, fire crackle, and map route draw stems on S08_SH002, S02_SH008, S05_SH020, and S02_SH001.




• Listen: Render WAV excerpts for those 4 shots.

	Steps 1, 2, 4	High	Low	The viewer hears the cold wind and fire crackle the director chose on 2.5D shots, and hears tactile paper/charcoal draw + front ambience on maps (S02_SH001, S02_SH002).
Step 7	Tactile Map & Helper Mood Integration (G5, 10% Lane)	

• Existing files updated:




- explainer_engine/maps/actions.py (plan at L461, camera at L646, draw at L982, render_frame at L1428) & explainer_engine/production/map_clip.py (render_episode_gis_map_clip at L15, render_action_map_clip at L171): read shot.director_brief and segment mood to apply subtle atmospheric grading/vignette matching the surrounding scenes (e.g., cold December mud-and-frost vignette as S02_SH001's August optimism turns into S02_SH002's December trench line), and emit exact action frame spans to episode/events.py::visual_events.




- explainer_engine/episode/router.py (infer_helper_form at L167, helper_fit_rows at L187): verify helper variety and mood fit against director_brief.

	• Add MAP-MOOD-01: maps/actions.py::render_frame and production/map_clip.py adapt vignette and atmospheric patina to the shot's director_brief and lock action spans to events.visual_events.	• Test: tests/unit/test_map_mood_and_synchresis.py verifies S02_SH001 and S02_SH002 action frame spans match events.visual_events to the exact frame and apply mood patina.	Step 6	Medium	Low	Map shots (S02_SH001..003, S05_SH001..002) look and sound like part of the same physical wartime world as the painted scenes.
Step 8	Audio Perception Engine & Mandatory Look-and-Listen Gate (G2, G7, Lead h)	

• New files: explainer_engine/qa/perceive_audio.py + explainer_engine/qa/look_and_listen.py.




• Existing files wired together:




- Unify explainer_engine/qa/frame_review.py (check at L150, contact_sheets at L358, loudness at L399, run at L413), explainer_engine/qa/sheet_review.py (request at L44, apply at L55), explainer_engine/qa/visual_judge.py (build_prompt at L58, verdict at L86), and explainer_engine/qa/sound_realism.py (measure) inside look_and_listen.py, invoked automatically at the end of episode/run.py::stage_clips (L873), stage_sound (L1292), stage_assemble (L1476), and stage_qa.




- Write episodes/<ep>/qa/look_and_listen_bundle/ (contact sheets, motion-leak heatmaps, MP4 clips, WAV excerpts, perceive_audio AST/CLAP report, and look_and_listen_record.json with status: "PENDING_CLAUDE_REVIEW"). Block ship in stage_qa until signed off.

	• Add QA-LL-01: Every visual/audio stage writes self-perception metrics (perceive_picture, gate_motion_isolation_leak, perceive_audio) plus a human/Claude review bundle; stage_qa blocks shipping if any shot fails self-perception or lacks sign-off in look_and_listen_record.json.	• Test: tests/unit/test_look_and_listen_gate.py verifies contact-sheet + audio-excerpt generation, catches a synthetic motion leak or missing audio bed, and blocks unsigned runs.	Steps 2, 3, 6	High	Low	The pipeline looks at every frame and listens to every stem itself before handing a structured review pack to Claude.
4. Outline of the Two Knowledge Bases & the Motion-Isolation File (Zero Numeric Effect Quotas)
4.1 explainer_engine/standards/screenwriter_guide.json + docs/SCREENWRITER_GUIDE.md

Designed around narrative situations and free-form expressive briefs (no numeric effect counts or closed enums):

JSON
{
  "version": "1.0.0",
  "core_principles": {
    "SW-01_story_and_suffering_truth": "Every historical war shot must honour the lived physical reality of the men in the line—cold, mud, exhaustion, and the contrast between distant rulers/commanders and the soldiers bearing the cost.",
    "SW-02_free_descriptive_brief": "Write each shot's director_brief in clear, natural prose—never closed enum codes or numeric effect quotas—stating what the viewer must feel, the physical truth of the place, where the eye should rest on each spoken clause, and what restraint is required.",
    "SW-03_brief_serves_actual_narration": "A brief is anchored directly to the shot's spoken audio_lines text and delivery_direction (e.g., a dry beat on 'Nobody asked the men in the trenches' demands that the camera end on the forgotten men in the cold).",
    "SW-04_picture_humility_and_conflict_flagging": "Describe the intended staging and props clearly, knowing the director will inspect start_01.png: if a painted prop differs without breaking the spoken line (a tin mug instead of a letter when the line never mentions a letter, as in S02_SH008), the director will animate the mug; if the painting contradicts the spoken line itself, it will be queued for regeneration.",
    "SW-05_sound_conceived_with_picture": "Describe the emotional and spatial sound perspective in natural language (e.g., 'raw freezing parapet wind over a close coke-brazier crackle, making the distant Vatican appeal feel a thousand miles away')."
  },
  "situation_methods": {
    "opening_hook": {
      "dramatic_goal": "Arrest the viewer inside a concrete physical anomaly or human moment before explaining the broader war.",
      "visual_strategy": "Start close on a human action or sensory detail in cold fog/light, then widen to reveal scale (as in S01_SH001 -> S01_SH004).",
      "sound_strategy": "Immediate tactile foley (boots in frozen mud, breath, wind) under a restrained voiceover; no wall-to-wall bombastic music."
    },
    "political_decision_vs_men_in_line": {
      "dramatic_goal": "Expose the gulf between emperors, popes, or generals issuing decrees and the soldiers freezing in the trenches (e.g., S02_SH008, S08_SH002).",
      "visual_strategy": "Establish the harsh physical environment (open snow-lined trench, brazier, huddled posture) during the institutional statement, then push toward the soldier's face or hands on the human turn of the sentence.",
      "sound_strategy": "Cold wind and close physical foley (fire hiss, shivering breath) dominate so the institutional words land against raw physical suffering."
    },
    "troop_movement_and_frontline_maps": {
      "dramatic_goal": "Make geographic scale and strategic deadlock physically felt rather than academic (e.g., S02_SH001, S02_SH002, S02_SH003).",
      "visual_strategy": "Lock route arrows, frontline trenches, and sector zooms to the exact spoken time and place markers ('August', 'Christmas', 'North Sea to Switzerland', 'Flanders').",
      "sound_strategy": "Layer a continuous terrain/weather bed beneath tactile cartographic drawing sounds synced to the arrow or frontline span."
    },
    "battle_and_signal_actions": {
      "dramatic_goal": "Convey physical danger and irreversible turning points (e.g., S07_SH005 Capt. Stockwell's three shots into the air).",
      "visual_strategy": "Frame the physical action clearly against the environment (worm's-eye or trench-step view into cold morning fog); lock muzzle smoke and recoil to the exact spoken word ('shots').",
      "sound_strategy": "Sharp close transient impacts cutting through cold fog ambience, followed by long exterior decay."
    },
    "sacred_or_emotional_tableau": {
      "dramatic_goal": "Honour shared grief or fragile humanity without sentimental clutter (e.g., S05_SH020 joint burial psalm).",
      "visual_strategy": "Guide the camera calmly between the groups named by the narrator ('Scottish chaplain' -> 'German student'), keeping memorials/crosses whole and forbidding decorative sparkles.",
      "sound_strategy": "Hushed open-air snow wind and faint cloth/footstep shifts; let the spoken words and silence carry the weight."
    }
  }
}

4.2 Upgraded explainer_engine/standards/director_knowledge_base.json + docs/DIRECTOR_GUIDE.md

Replaces numeric effect floors/caps (LP-08, BP-185) with perception-first, reason-backed decision rules:

JSON
{
  "version": "2.0.0",
  "decision_protocol": {
    "step_1_perceive_picture": "Call perceive_picture(start_01.png, layers_manifest) via production/understand.py and production/perceive_picture.py to obtain real mask centroids [cx, cy], bounding boxes [x0, y0, x1, y1], verified sky_mask, snow_ground_mask, active_lights, and held props.",
    "step_2_reconcile_with_brief_and_narration": "Read shot.director_brief and the shot's audio_lines text. Where picture and script prose differ on physical surroundings or unmentioned props (e.g., S08_SH002 is an open trench, not a dugout; S02_SH008 shows a tin mug, not a letter, and the narration line S02_L008 never mentions a letter), follow the picture for physical geometry and follow the brief + narration for mood (cold, war, suffering). If the picture contradicts a noun explicitly spoken in audio_lines, flag the shot to regeneration_queue.json.",
    "step_3_direct_camera_from_words_and_anchors": "Choose camera path from the spoken clauses (BP-195) and real object centroids. Enforce keep_in_frame anchor protection: never slice off the base of an active brazier/light source or soldiers' boots near the bottom frame edge.",
    "step_4_select_living_effects_by_truth_and_mood": "Inspect every natural element visible in perceived (fire, candle, mug, faces in cold air, open sky, snow, mist, cloth, water). Animate every element that serves the brief's mood and physical truth, isolating motion strictly to the moving part (MI-01..MI-09), and write a concrete reason ('why') for each chosen and each skipped element (BP-196). Never add an effect merely to satisfy a number.",
    "step_5_direct_sound_for_all_lanes": "Pass the directed visual events and perceived environment into choose_sound / sound_of_direction / sound_of_map so episode/sound_plan.py::build places matching beds and word/frame-synced point sounds."
  }
}

4.3 explainer_engine/standards/motion_isolation.json + docs/MOTION_ISOLATION.md

Defines all physical mover-vs-holder pairs and the calibrated leak gate (D-59):

Rule ID	Moving Element (mover_mask)	Rigid Holder / Background (anchor_mask, 0.0 warp)	Separation & Masking Method in motion_isolation.py + living_fx.py
MI-01	Flame plume (brazier_flame, candle_flame, campfire)	Iron brazier basket & legs (S02_SH008), tin candle holder & wax stub (S08_SH002), wooden crate	Split light/object mask by HSV luminance + warmth (V > 0.72, R - B > 0.18) above the holder's upper rim line; apply guided-filter feathering. Pin all iron bars, tin base, and crate wood below the rim to alpha_motion = 0.0.
MI-02	Rising smoke (smoke_drift, muzzle_smoke in S07_SH005)	Chimney, brazier grate, revolver barrel (S07_SH005), sandbags	Spawn and advect smoke strictly above the emitter tip/rim multiplied by (1.0 - solid_object_masks).
MI-03	Rising steam (steam from hot tin mug in S02_SH008)	Metal mug body, rim, and Thomas's gloved fingers (S02_SH008)	Place steam plume box immediately above the detected mug top edge ([x0+0.15w, y0-0.35h, x1-0.15w, y0-0.02h]) and multiply by (1.0 - mug_and_hand_mask).
MI-04	Water shimmer / puddle ripple (water_shimmer)	Muddy trench banks, duckboards, ice edges, boots	Erode water mask at solid boundaries and feather over 6px; zero displacement on banks or boots.
MI-05	Cloth free edge (cloth_flap, coat hem, prop_flag_merry_christmas in S07_SH005)	Flagstick/pole, wooden grave posts (S05_SH020), soldier's torso/shoulders	Pin the proximal attachment zone (alpha_motion = 0.0 at pole/body seam) with a smooth ramp toward the free cloth edge.
MI-06	Fire embers / sparks (embers)	Barbed wire, sandbags, distant trench walls (S08_SH002)	Additive particle layer only (zero background pixel warp); disable rising embers on distant background braziers (S08_SH002) where they read as fake indoor sparks.
MI-07	Sky & snow-ground effects (stars, cloud_drift, sun_glint, frost_glint)	Barbed wire & sandbags (S02_SH008), wooden grave crosses & soldiers' coats (S05_SH020)	Multiply sky effects (stars, cloud_drift, sun_glint) by verified sky_mask * (1 - dilated_fg_mask). Multiply ground frost glints by snow_ground_mask * (1 - dilated_fg_mask) and suppress glints completely when the brief calls for solemn/tragic stillness (S05_SH020).
MI-08	Cold breath plume (breath in S02_SH008, S05_SH020, S08_SH002)	Soldier's face, moustache, cap, and collar	Anchor soft translucent puff (living_fx.py::_breath, L301) just outside the mouth coordinates facing the gaze direction, masked off the face pixels (1.0 - face_mask).
5. End-to-End Brief Hand-Off Design & Worked Examples on Real Truce Shots
5.1 Schema, Ownership & Reconciliation Flow

Schema (explainer_engine/schemas/production_script.schema.json):

JSON
"director_brief": {
  "type": "object",
  "required": ["mood", "viewer_feeling", "physical_truth", "focal_priority", "sound_perspective", "restraint_note"],
  "properties": {
    "mood": {"type": "string", "minLength": 5, "description": "Free descriptive mood phrase (no closed enum)."},
    "viewer_feeling": {"type": "string", "minLength": 15, "description": "What the viewer must feel during this specific spoken line."},
    "physical_truth": {"type": "string", "minLength": 15, "description": "The concrete physical reality, weather, temperature, and light of the place."},
    "focal_priority": {"type": "array", "items": {"type": "string"}, "minItems": 1, "description": "Ordered visual focal targets tied to the spoken clauses."},
    "sound_perspective": {"type": "string", "minLength": 10, "description": "Free descriptive acoustic POV and texture."},
    "restraint_note": {"type": "string", "minLength": 10, "description": "What must NOT be over-animated or cropped."},
    "tags": {"type": "array", "items": {"type": "string"}}
  }
}


Ownership (explainer_engine/scripting/stage_guard.py): Added to V4_OWNERS under "edit-planner".

Two-Tier Script-vs-Picture Reconciliation (G-e):

Case 1 — Physical Adaptation (Picture wins for geometry/environment; Narration + Brief win for meaning and mood): When start_01.png differs from screen_composition or action_start_state on an environmental or unmentioned prop detail that does not contradict the spoken audio_lines text (e.g., in S08_SH002, S08_L002 says "Their commanders moved to prevent it from happening again..." and the picture shows an open snow-lined trench rather than a dugout bunk; in S02_SH008, S02_L008 says "In early December, the Pope asked for a Christmas truce... Nobody asked the men in the trenches" and the picture shows Thomas holding a tin mug rather than a letter), the director trusts perceive_picture(start_01.png) for what is physically in the frame, logs direction["adapted_from_picture"], and updates the stale non-spoken script description fields so script and picture are in sync.

Case 2 — Story-Breaking Conflict (Flagged to regeneration_queue.json): When perceive_picture(start_01.png) discovers that the painting contradicts an object, person, or action explicitly named in audio_lines or essential to the story beat (for example, if a narration line says "He held up a wooden football" and the painting shows an empty field or a rifle), the director never silently overrides the story: it marks the shot needs_regeneration: true in episodes/<ep>/production/regeneration_queue.json and emits a FAIL gate row at stage_pictures / stage_clips.

5.2 Complete Worked Examples (Brief + Perceived Picture + Direction + Sound) on the Four Real Shots
1. S08_SH002 (still_25d, target_duration_seconds: 8.75, Segment S08 "For one day")

Real Spoken Line (S08_L002, delivery_direction: "plain, no comment"):

"Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale."

Screenwriter's director_brief:

JSON
{
  "mood": "bleak winter cold and quiet heartbreak as high command crushes a fragile human memory",
  "viewer_feeling": "The viewer should feel the biting cold of the trench and the tragedy of a soldier clinging to a tiny souvenir of peace—a brass button and a family portrait—while the machinery of war closes back over him.",
  "physical_truth": "An open, unroofed snow-lined German trench at night under a freezing purple-black sky; rough wool-gloved hands in the foreground hold a sepia family portrait card and a British brass button beside a flickering candle stub in a tin holder on a wooden crate.",
  "focal_priority": [
    "open freezing trench and gloved hands holding the portrait card ('Their commanders moved to prevent it from happening again')",
    "the British brass button and family portrait lit by the candle ('A few small truces still occurred in 1915, but nothing on that scale')"
  ],
  "sound_perspective": "Cold open-trench night wind cutting across the sandbags, faint freezing breath and wool glove rustle up close, with a fragile close candle crackle and a low, distant, inescapable rumble of the returning war.",
  "restraint_note": "This is a freezing open trench, not a warm bedroom: let light snow fall into the trench and cold wind drift across the parapet. Isolate the candle flicker strictly to the flame above the tin holder, and never spawn indoor dust motes or party-like embers on the distant trench braziers."
}


What perceive_picture(start_01.png) + understand.py Measure:

sky_mask: Open night sky at y = 0.00..0.15 (sky_open = True, overriding stale screen_composition.foreground: "the edge of a dugout bunk").

objects: hands_with_portrait_and_button (cx = 0.46, cy = 0.68, bbox = [0.18, 0.42, 0.76, 0.98]), candle_in_tin_holder (cx = 0.848, cy = 0.375, flame plume at [0.848, 0.345], rigid tin holder at y = 0.36..0.45), far_braziers ([0.72, 0.39], [0.85, 0.46]).

Director's Realization (living_director.py + directed25d.py + sound_plan.py):

Camera (2 word-linked beats on the 8.75s shot):

Beat 1 ("Their commanders moved to prevent it from happening again."): Starts wider on [0.50, 0.54] so the viewer sees the open snow-lined trench receding into the cold night above the gloved hands.

Beat 2 ("A few small truces still occurred in 1915, but nothing on that scale."): Slow push-in settling onto [0.47, 0.63] (the brass button resting on the family portrait card), keeping the candle flame in the right third ([0.848, 0.345]).

Living Effects & Isolation:

snow: Light snow falling diagonally into the open trench (why: "open night trench in winter; physical cold and suffering under the commanders' ban").

mist / breath: Cold night air drifting across the trench parapet (why: "freezing night air in the open trench").

candle (MI-01): Flame flickers softly above the tin holder ([0.848, 0.345]) casting warm light on the portrait card; the tin candle holder and wooden crate are clamped to 0.0 displacement. Distant braziers receive only a faint static/slow glow (far_brazier_embers and dust_motes skipped with written reason: "open freezing trench; indoor dust and rising background sparks contradict the cold bleak mood").

Sound (choose_sound -> sound_plan.build): Cold open-air night trench wind bed + faint close wool/paper rustle + subtle low distant artillery rumble on "prevent it from happening again".

2. S02_SH008 (still_25d, target_duration_seconds: 10.0, Segment S02 "Home by Christmas")

Real Spoken Line (S02_L008, delivery_direction: "plain; a dry beat before the last sentence"):

"In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed. Nobody asked the men in the trenches."

Screenwriter's director_brief:

JSON
{
  "mood": "bitter irony and freezing endurance—the forgotten men shivering in the mud while distant popes and governments decide their fate",
  "viewer_feeling": "The viewer should feel the physical misery of the freezing trench and the sharp sting of the final sentence: 'Nobody asked the men in the trenches.'",
  "physical_truth": "An open sandbagged British trench at freezing blue dusk with barbed wire along the parapet; Thomas (left, warming a hot tin mug in his gloved hands) and Sgt. Harris (right, hunched in his goatskin jerkin with hands on his knees) sit on the fire step around a glowing iron-basket coke brazier.",
  "focal_priority": [
    "full trench tableau: both soldiers from boots to caps huddled around the iron brazier ('In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed.')",
    "push onto Thomas's cold face and steaming tin mug ('Nobody asked the men in the trenches.')"
  ],
  "sound_perspective": "Raw freezing wind across the barbed-wire parapet, close coke-brazier crackle and hiss between the two men, and heavy cold breathing—no grand diplomatic music.",
  "restraint_note": "On the wide establish, keep the entire iron brazier basket and both soldiers' boots inside the frame—never slice off their feet or the bottom of the fire basket. Let light snow fall from the dusk sky, steam rise from Thomas's mug, and cold breath from their mouths; mask dusk sky effects strictly above the sandbag/wire horizon."
}


What perceive_picture(start_01.png) + understand.py Measure:

sky_mask: y = 0.00..0.16 (purple dusk sky above the sandbags and barbed wire).

objects (real mask coordinates, replacing [0.5, 0.5]):

thomas: cx = 0.24, cy = 0.58, bbox = [0.05, 0.20, 0.43, 0.96], face at [0.27, 0.34], holding tin_mug at [0.295, 0.545].

brazier: cx = 0.52, cy = 0.69, bbox = [0.43, 0.52, 0.61, 0.90] (flame plume y = 0.52..0.64, rigid iron basket & legs y = 0.64..0.90).

harris: cx = 0.76, cy = 0.57, bbox = [0.58, 0.19, 0.95, 0.96], face at [0.71, 0.33].

reconciliation: S02_L008 never mentions a letter or a rifle; the stale prose in screen_composition.midground ("the letter in his hand; Harris on the right cleaning his rifle") is updated to match the approved painting (tin mug, hands on knees).

Director's Realization:

Camera (keep_in_frame anchor guard active):

Beat 1 (0.00–6.40 s, "In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed."): Wide framing ([0.50, 0.55], gentle drift) that keeps the full brazier basket (y_bottom = 0.90) and both soldiers' boots (y_bottom = 0.96) completely inside the frame.

Beat 2 (6.40–10.00 s, after the dry pause, on "Nobody asked the men in the trenches."): Deliberate push-in toward Thomas's face and steaming mug (cx = 0.32, cy = 0.42), re-centering cleanly onto his upper body/face so the cut at the bottom is a true medium close-up rather than an accidental ankle slice.

Living Effects & Isolation:

brazier_flame (MI-01): Flickers in y = 0.52..0.64 with warm glow on the men's knees/hands; the iron basket (y = 0.64..0.90) has 0.0 displacement.

steam (MI-03): Rises softly from the top rim of Thomas's mug ([0.295, 0.51]), while the mug and fingers stay rigid.

breath (MI-08): Cold breath puffs from Thomas ([0.29, 0.35]) and Harris ([0.69, 0.34]).

snow & wind: Light snow falling and wind drifting across the trench (sky_open = True).

stars (MI-07): Masked strictly to sky_mask (y < 0.16) — zero star points on the barbed wire or sandbags!

3. S05_SH020 (still_25d, target_duration_seconds: 7.75, Segment S05 "No man's land")

Real Spoken Line (S05_L020, delivery_direction: "reverent, unhurried"):

"At one burial, a Scottish chaplain read the Twenty-Third Psalm. A German student read it after him, in German."

Screenwriter's director_brief:

JSON
{
  "mood": "reverent, tragic stillness—two enemy armies united in prayer over fresh graves in the snow",
  "viewer_feeling": "Quiet awe and sorrow as the same psalm bridges two languages across open graves in No Man's Land.",
  "physical_truth": "A frozen snowfield in No Man's Land under a low amber late-afternoon sun; four plain wooden crosses stand in the snow between bareheaded British/Scottish soldiers on the left and German soldiers on the right.",
  "focal_priority": [
    "Scottish chaplain and bareheaded British soldiers on the left ('At one burial, a Scottish chaplain read the Twenty-Third Psalm.')",
    "wooden grave crosses in the center leading to the young German student and German soldiers on the right ('A German student read it after him, in German.')"
  ],
  "sound_perspective": "Hushed open snowfield wind, complete absence of gunfire, and a single soft boot-in-snow shift as the reading passes from English to German.",
  "restraint_note": "Zero ice glints or sparkles on the wooden crosses or soldiers' coats. Guide the camera gently from the left group to the right group on the second sentence, with only soft cold breath, low sun haze in the upper sky, and tiny grave-candle flicker."
}


Director's Realization:

Uses measured mask centroids (left_group at cx = 0.26, cy = 0.52, cross_centre at cx = 0.49, cy = 0.64, right_group at cx = 0.73, cy = 0.51) to frame the Scottish chaplain during Sentence 1 (0.00–4.10 s) and pan smoothly across the crosses to the German student on "A German student read it after him, in German" (4.10–7.75 s).

Drops fx_seen_ice (glint box [0.342, 0.422, 0.658, 0.738]) completely; animates cold breath from the bareheaded soldiers, isolated flame flicker on the grave candles/side braziers (MI-01), and upper-sky sun_shaft drift (y < 0.35).

4. Real Map Shot S02_SH001 (map_action, TACTILE_MAP, target_duration_seconds: 6.0, Segment S02 "Home by Christmas")

Real Spoken Line (S02_L001, delivery_direction: "light irony on 'Christmas'"):

"The war had begun in August. Everyone said it would be over by Christmas."

Real Shot Actions in production_script.json:

S02_SH001.A1: kind: "label", at_word: "August", label: "August 1914", audio: {"decision": "ui_cue", "class": "map_arrive_click", "sync": "onset", "purpose": "clarify"}.

S02_SH001.A2: kind: "route_arrow", at_word: "Everyone", until_word: "Christmas", from: "aachen", to: "marne", via: ["liege", "brussels"], audio: {"decision": "sfx", "class": "map_route_draw", "sync": "span", "purpose": "clarify"}.

Screenwriter's director_brief:

JSON
{
  "mood": "hubristic late-summer confidence about to hit the wall of industrial trench warfare",
  "viewer_feeling": "The viewer should feel the sweeping illusion of a fast 19th-century march ('over by Christmas') before the map freezes into the December trench line in S02_SH002.",
  "physical_truth": "A tactile shaded-relief command map of Belgium and northern France from Aachen to the Marne, lit like a headquarters planning table.",
  "focal_priority": [
    "August 1914 date stamp at the German border ('The war had begun in August.')",
    "the sweeping invasion arrow curving through Liège and Brussels toward the Marne ('Everyone said it would be over by Christmas.')"
  ],
  "sound_perspective": "Command-tent map table ambience over a low distant marching/rumble bed; a crisp stamp click as 'August 1914' lands, followed by a continuous charcoal-on-paper sweep as the arrow drives from Aachen toward the Marne.",
  "restraint_note": "Keep the parallax dolly smooth so the viewer reads the Aachen -> Liège -> Brussels -> Marne trajectory effortlessly; lock the arrow draw sound strictly to the span from 'Everyone' to 'Christmas'."
}

6. The Creator's Four Open Questions (Q1–Q4)
Q1. S08_SH002: Script says "dugout bunk, warm candlelight", picture looks like an open trench: rewrite the script/image prompt, or the director decides from the picture? (And what is the general rule?)

Options:

Option A (Rewrite script/image prompt and regenerate the picture): Change image_prompt to force a roofed dugout bunk and re-run image generation.

Option B (Director silently overrides the script from the picture): Leave production_script.json untouched and let living_director.py override it at runtime.

Option C (Two-Tier General Rule — Picture wins for physical reality; Narration + Brief win for meaning/mood; update stale non-spoken script metadata and queue only story-breaking conflicts for regeneration):

In S08_SH002, the spoken narration (S08_L002: "Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale.") never says the word "dugout". Moreover, the actual painting (s08_strip.jpg — an open, freezing, snow-lined trench at night where a soldier holds the portrait card and British brass button beside a candle on a crate) is stronger for the creator's mood of cold, war, and suffering than a cosy indoor bunk!

Under Option C, the director inspects start_01.png via perceive_picture, directs the open freezing trench that is actually painted (light snow falling, cold wind, isolated candle flame), AND we update S08_SH002.screen_composition.foreground and lighting_and_time in production_script.json to match the approved painting so script and picture no longer disagree.

The General Rule (DIR-EYE-01):

Physical Presence: The picture (perceive_picture(start_01.png)) is authoritative for what physically exists in the frame (sky openness, object coordinates, light positions, held props). The director never animates an effect for an object that is not in the picture (Walter Murch Rule of Six).

Meaning & Mood: The spoken audio_lines and the screenwriter's director_brief are authoritative for emotional intent, story beat, and camera focus (TAKE 85 Directorial Intent Benchmark).

Story-Breaking Conflict Guard: If perceive_picture finds that the painting contradicts a noun or action explicitly spoken in audio_lines (or essential to the plot beat), the director does not silently override it — it flags the shot into episodes/<ep>/production/regeneration_queue.json (needs_regeneration: true). If the mismatch is only in unvoiced staging prose (dugout bunk in S08_SH002 or letter/rifle in S02_SH008), we sync the script's staging field to the approved painting and direct the painting.

Recommendation: Option C. It preserves the strong existing paintings for S08_SH002 and S02_SH008, aligns them with your cold/suffering mood, eliminates stale metadata, and catches genuine story-breaking image errors automatically.

Q2. BP-185 (at least 2 effect families, FAIL) and BP-196 (FAIL) are the creator's earlier house rules: keep, soften to hints, or replace?

Options:

Option A: Keep both BP-185 (families_min: 2 -> FAIL) and BP-196 (FAIL) exactly as written, including LP-08 (effects_min: 3 -> FAIL).

Option B: Drop both rules completely.

Option C (Replace numeric count floors in BP-185 / LP-08 with Reason-Backed Context & Keep BP-196 as a Perception-Grounded Accountability Rule):

Why BP-185's numeric count (families_min: 2) and LP-08 (effects_min: 3) caused damage: When a shot has only one natural family visible or calls for stark stillness (S08_SH002, S05_SH020), forcing 2 families / 3 effects (FAIL) forced the code either to fabricate fake effects (fx_seen_ice sparkling on grave crosses in S05_SH020, far_brazier_embers in S08_SH002) or to crash with FAIL LP-08: only 2 living effects beyond the flames (S08_SH002.auto_direction.json).

How we reform BP-185 and LP-08: Replace the hard count (families_min = 2, effects_min = 3) with Qualitative Liveliness (BP-185-v2): a still_25d shot must never be a dead frozen JPEG with only a zoom (FAIL only if len(living_effects) == 0); beyond that, the number and families of effects are chosen by the director from the perceived picture and director_brief (soft hint to consider atmosphere + light/subject when the picture supports them, never a count FAIL).

How we keep and sharpen BP-196: BP-196's core mechanism — "every element of the picture that moves in nature carries an effect OR a written reason why not (why); weather is a ceiling, not a fill; every part of the picture the shot's words name gets a camera move on that word or a written reason" — is excellent film direction discipline, provided the inventory comes from perceive_picture(start_01.png) (what is actually in the painting) rather than blind regexes over stale script strings.

Recommendation: Option C. Soften BP-185 and LP-08 from numeric count FAILs into qualitative guidelines (failing only on 0 living motion), and keep BP-196 upgraded to use perceive_picture + director_brief reasons (Walter Murch — Law of Two-and-a-Half).

Q3. Map camera moves are silent by default (AV-03 / AV-04 / D-135): should map moves get sound?

Options:

Option A (Always silent): Keep all map camera moves (zoom, push, pull, truck, parallax_dolly) silent_by_design in episode/events.py::DEFAULTS (L88).

Option B (Always add whoosh/sfx to every map camera move): Give every map pan or dolly a sound effect.

Option C (Differentiate Continuous Drift vs. Rapid Tactical Sector Zoom, plus Always Require a Geography Bed via sound_of_map):

In professional map documentaries (Kings and Generals, Johnny Harris / Vox Map Craft, Michel Chion's Audio-Vision), a slow camera drift (parallax_dolly during S02_SH001 while the arrow draws) should not have its own whoosh because the arrow (map_route_draw) and the environmental bed (sound_of_map: wind/distant rumble) already carry the motion; adding a camera sound there creates clutter (BP-81).

However, when a map performs a rapid scale dive / sector zoom where the camera move is the primary visual event (e.g., zooming from the 530 km Western Front overview in S02_SH002 down into the tight Flanders trench sector in S02_SH003: "Here, in Flanders, the two sides sat close enough to hear each other cough"), leaving the zoom completely silent feels weightless. A subtle low-frequency paper/air transition (map_sector_zoom / map_tokens_shift) synced to the zoom span sells the physical dive into the trenches.

Recommendation: Option C. Keep slow map camera drifts (parallax_dolly, gentle push/pull) silent_by_design under the mandatory sound_of_map terrain bed, and give purposeful scale dives / fast sector zooms (when the camera move is the primary visual beat or changes span_km significantly) a tactile paper/air transition sound in episode/events.py and episode/sound_plan.py.

Q4. The 84 Truce director briefs: written by you directly, or by the screenwriter stage (edit-planner) with the creator's review?

Options:

Option A: Written directly by Argon in one pass inside production_script.json.

Option B: Generated only by .claude/agents/edit-planner.md in a separate future run.

Option C (Hybrid Crew Workflow — Upgrade edit-planner + screenwriter_guide.json AND Have Argon Draft All 84 Briefs in Step 2B Following Those Exact Rules, Plus Export a Readable docs/wip/TRUCE_84_BRIEFS_REVIEW.md Table for the Creator's Review):

To make the pipeline self-sustaining for future episodes, .claude/agents/edit-planner.md, explainer_engine/standards/screenwriter_guide.json, and stage_guard.py (V4_OWNERS) must own director_brief.

At the same time, for Truce 1914 right now in Step 2B, Argon has full visibility into all 84 shots of episodes/ep_truce_1914/story/production_script.json, their exact audio_lines, and their layer manifests. Having Argon author all 84 director_brief entries in Step 2B (strictly adhering to screenwriter_guide.json and stage_guard.py as edit-planner) AND generate a clean side-by-side review table (shot_id | spoken line | picture summary | director_brief | conflicts flagged) lets you and Claude review, tweak, and approve every single shot's brief immediately without waiting for an extra agent pass.

Recommendation: Option C. Wire edit-planner as the canonical owner in stage_guard.py and screenwriter_guide.json, and have Argon populate all 84 Truce 1914 briefs in Step 2B along with a human-readable review table for your sign-off.

7. Additional Engineering & Creative Decisions for the Creator
ID	Question	Options	Argon's Recommendation
D1	Unifying living.py and living_director.py (Lead b)	

A. Keep living.py and living_director.py as two separate planners with separate rules.




B. Make living_director.py the single brain that chooses effects by perception + brief, and reduce living.py to a thin compatibility helper called by living_director.py.

	Option B: Eliminates the split-brain bug where living_director.py and living.py disagree on LP-08 or effect caps.
D2	Sub-Cutting still_25d Shots > 5.0 s (D-131 vs. BP-184)	

A. Split every still_25d shot > 5.0 s on spoken sentence/clause boundaries (shot_split.py) into distinct camera framings (<= 5.0 s each) that follow the named subjects (BP-195).




B. Allow unbroken single camera moves up to 10.0 s.

	Option A: Honours D-131 (<= 5.0 s cut on narrator words) and prevents mid-shot retention dips (YouTube Studio Retention Guide).
D3	Ducking vs. Cut Continuity (BP-53 vs. BP-191)	

A. Enforce BP-53 smooth sidechain ducking under speech AND BP-191 continuous scene beds + point-sound tail overlaps across intra-scene cuts in assemble.py::build_audio_v2 (L362).




B. Hard-cut all audio stems at shot boundaries.

	Option A: Keeps dialogue intelligible (BP-53) while eliminating dead air at shot cuts (BP-191).
D4	Cold/Warm Atmospheric Grading in living_fx.py::apply (L381)	

A. Allow the director to apply a subtle cold winter shadow grade balanced by localized warm fire/candle falloff when the brief calls for freezing trench suffering (S08_SH002, S02_SH008).




B. Keep RGB values ungraded outside additive particles.

	Option A: Reinforces the visual contrast between freezing trench steel-blue and fragile brazier/candle warmth (They Shall Not Grow Old Craft).
8. ASSUMPTIONS, NOT CHECKED & Exact Repository State

Repository State Used:

repo_after_task1.zip: branch argon/plan-steps-1-2 at commit 9ecdd875 ("Argon Task 1 + correction round 1 + Claude's fixes", verified via ZIP_NOTE.txt).

visual_task1.zip: inspected visual/s08_strip.jpg, visual/s02_strip.jpg, visual/s05_strip.jpg, visual/S08_SH002.auto_direction.json, visual/S02_SH008.auto_direction.json, visual/S05_SH020.auto_direction.json, and visual/README.txt.

Every shot ID (S08_SH002, S02_SH008, S05_SH020, S01_SH004, S02_SH001, S02_SH002, S02_SH003, S05_SH001, S05_SH002, S07_SH005), audio line (S08_L002, S02_L008, S05_L020, S02_L001, S07_L005), rule ID (BP-185, BP-196, BP-53, BP-191, BP-184, BP-81, BP-195, AV-01..AV-05, D-131, D-135, LP-06..LP-08), file path, and function name in this plan was verified directly against repo_after_task1.zip.

ASSUMPTIONS:

Per the Step 2A instructions, no repository files were modified in this reply; implementation begins in Step 2B once you review Q1–Q4 and D1–D4.

In Step 2B, perceive_picture.py and perceive_audio.py will support cached local weights (microsoft/Florence-2-base, MIT/ast-finetuned-audioset-10-10-0.4593, laion/clap-htsat-unfused) alongside deterministic OpenCV/SciPy geometry, HSV, optical-flow, and spectral analyzers so tests run offline on CPU in $0 environments.

NOT CHECKED:

The remote .mp4 files on Hugging Face (S08_SH002_auto.mp4, S02_SH008_auto.mp4, S05_SH020_auto.mp4) were not streamed over the network because sandbox internet is disabled; their extracted frame strips (s08_strip.jpg, s02_strip.jpg, s05_strip.jpg) and .auto_direction.json files in visual_task1.zip were inspected directly.

Full-resolution start_01.png rasters for the remaining 81 shots of ep_truce_1914 are not bundled in repo_after_task1.zip or visual_task1.zip; their layer manifests and script entries in episodes/ep_truce_1914/ were checked.

=== LINKS ===
Dying In Caucasus Snow / Christmas Truce 1914 (Week 22) <https://www.youtube.com/watch?v=g-OQeCEMWpE>
The Christmas Truce in 1914 — I Was There: The Great War Interviews <https://www.youtube.com/watch?v=WNCxkA_zfMs>
WW1 Christmas Truce: Silent Night (Part 1) <https://www.youtube.com/watch?v=WUlPNWDvk-c>
Overview <https://worldoftanks.asia/en/news/general-news/video-extra-credits-the-christmas-truce/>
World War 1 (All Parts, 4K) <https://www.youtube.com/watch?v=G1p6rlDCxq0&vl=en>
How the Union Finally Won the War <https://www.youtube.com/watch?v=otJnVLgaq7k>
Production Study <https://asterman.org/works/creating-videos-for-the-kings-and-generals-youtube-channel>
Marlborough's Masterpiece <https://www.youtube.com/watch?v=UWqrKGxYtps>
How I Make My Maps <https://www.youtube.com/watch?v=GsojLuJpe_0>
Documentary Editing Breakdown <https://www.youtube.com/watch?v=eOJR4NUZXlI>
FCPX Tactile Craft Breakdown <https://fcpxfullaccess.com/blogs/blog/vox-johnny-harris-documentary-style-final-cut-pro>
Grazed by the Apocalypse <https://www.youtube.com/watch?v=2GcwAD_7tJY>
The Enduring Mystery of Jack the Ripper <https://www.youtube.com/watch?v=lADBHDg-JtA>
Pacing Analysis <https://faceless.my/niches/faceless-mystery-channel/>
The Soviet Airliner Designed To Crash <https://www.youtube.com/watch?v=tqhtkG6glug>
What Really Happened To Giant Flying Boats? <https://www.youtube.com/watch?v=-f906Sy79hA&vl=en>
Christmas Truce (1914) <https://www.youtube.com/watch?v=Fk-LjY16zdM>
1968 BBC Archive: Remembering the Christmas Truce <https://www.youtube.com/watch?v=yPMyVa_p7qU>
Official Google/YouTube Help 9314415 <https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop>
YouTube Content Tab Analytics Tips 12942217 <https://support.google.com/youtube/answer/12942217?hl=en&co=YOUTUBE._YTVideoType%3Dvideo>
Virvid 2026 Retention Graph Analysis <https://virvid.ai/blog/retention-graphs-how-to-read-youtube-analytics-2026>
AIR Media-Tech Retention Guide <https://air.io/en/youtube-hacks/how-to-read-youtube-retention-graph>
UC Berkeley iSchool <https://blogs.ischool.berkeley.edu/i290-viznarr-s12/the-rule-of-six-walter-murch/>
StudioBinder <https://www.studiobinder.com/blog/walter-murch-rule-of-six/>
Video Essay at 00:42–03:15 <https://www.youtube.com/watch?v=XVNI3niZp3Q>
Artlist Guide <https://artlist.io/blog/eye-trace-and-rule-of-six-editing/>
PBS Civil War Study <https://elearning.asc.edu.ag/civil-war-ken-burns>
Ken Burns Composition Guide <https://frameo.ai/blog/use-ken-burns-effect-images/>
Shih et al. CVPR 2020 LDI Paper <https://shihmengli.github.io/3D-Photo-Inpainting/>
Randy Thom — Designing a Movie for Sound <http://filmsound.org/articles/designing_for_sound.htm>
Michel Chion — Audio-Vision PDF <http://pzacad.pitzer.edu/~mma/teaching/ms52/readings/audio-vision3-13.pdf>
Walter Murch — Dense Clarity / Law of Two-and-a-Half <https://designingsound.org/2009/10/15/walter-murch-special-womb-tone-and-dense-clarityclear-density/>
microsoft/Florence-2-base <https://huggingface.co/microsoft/Florence-2-base>
microsoft/Florence-2-large <https://huggingface.co/microsoft/Florence-2-large>
vikhyatk/moondream2 <https://huggingface.co/vikhyatk/moondream2>
Qwen/Qwen2.5-VL-3B-Instruct-GGUF <https://huggingface.co/ggml-org/Qwen2.5-VL-3B-Instruct-GGUF>
Ultralytics YOLO-World <https://docs.ultralytics.com/models/yolo-world>
moondream2 <https://huggingface.co/vikhyatk/moondream2>
pymatting/pymatting <https://github.com/pymatting/pymatting>
ZhengPeng7/BiRefNet <https://github.com/zhengpeng7/birefnet>
hustvl/VitMatte-small <https://comfy.icu/node/SimpleSyrup-ViTMatteModelLoader>
pymatting <https://github.com/pymatting/pymatting>
VeroMotion HF Benchmark <https://huggingface.co/datasets/VeroLM/VeroMotion>
Sana Flow Eval <https://huggingface.co/JoshHughes/sana-video2-style-v2v-lora>
MIT/ast-finetuned-audioset-10-10-0.4593 <https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593>
LAION-AI/CLAP <https://github.com/LAION-AI/CLAP>
snakers4/silero-vad <https://github.com/snakers4/silero-vad>
librosa <https://github.com/librosa/librosa>
laion/clap-htsat-unfused <https://huggingface.co/docs/transformers/en/model_doc/clap>
HF Render <https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/task1_auto_director/S08_SH002_auto.mp4>
HF Render <https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/task1_auto_director/S02_SH008_auto.mp4>
HF Render <https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/task1_auto_director/S05_SH020_auto.mp4>
Walter Murch Rule of Six <https://www.studiobinder.com/blog/walter-murch-rule-of-six/>
TAKE 85 Directorial Intent Benchmark <https://www.researchgate.net/publication/413824842_TAKE_85_Testing_Audiovisual_filmmaKer's_intEnt_across_85_Hours_of_Film>
Walter Murch — Law of Two-and-a-Half <https://designingsound.org/2009/10/15/walter-murch-special-womb-tone-and-dense-clarityclear-density/>
Kings and Generals <https://www.youtube.com/watch?v=otJnVLgaq7k>
Johnny Harris / Vox Map Craft <https://fcpxfullaccess.com/blogs/blog/vox-johnny-harris-documentary-style-final-cut-pro>
Michel Chion's Audio-Vision <http://pzacad.pitzer.edu/~mma/teaching/ms52/readings/audio-vision3-13.pdf>
YouTube Studio Retention Guide <https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop>
They Shall Not Grow Old Craft <https://www.reddit.com/r/movies/comments/b208mo/they_shall_not_grow_old_is_easily_one_of_the_most/>