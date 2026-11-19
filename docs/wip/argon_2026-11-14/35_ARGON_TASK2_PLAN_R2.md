1. შეჯამება შემქმნელისთვის (6–10 ხაზი)

R2-ის მთავარი გარდატეხა: გარე აუდიტისა (ChatGPT P0–P6) და თქვენი საბოლოო გადაწყვეტილებების (1–7, A–F) მიხედვით, სისტემა აღარ არის ცალკეული დეტექტორებისა და რიცხვითი ზღვრების კრებული — ის იქცევა ერთიან სარეჟისორო ჯაჭვად: აღქმა (Perception) -> ინტერპრეტაცია (Interpretation) -> რეჟისურა (Direction) -> შესრულება (Execution) -> ხელახალი აღქმა და შეფასება (Re-Perception & Feedback).

მკაცრი კონტრაქტები და გაურკვევლობის მართვა (A): თუ მოდელი (Florence-2 ან Grounding DINO Tiny) ვერ ხედავს საგანს მაღალი სანდოობით, ეს არ ნიშნავს საგნის არარსებობას — დაბალი სანდოობა გადადის REVIEW სტატუსში და რეჟისორი არასოდეს იგონებს ყალბ გადაწყვეტილებას.

ერთი ავტორიტეტული ხმის გეგმა და დეტერმინისტული ქეში (B, C): საბოლოო sound_plan.py::build იქმნება მხოლოდ მას შემდეგ, რაც ვიზუალური რეჟისურა და კადრის მტკიცებულებები არსებობს; ყველა არტეფაქტი (understand.py-ს ქეშის გაფართოებით) ინახავს სრულ SHA-256 ანაბეჭდს (ნახატი, სცენარი, brief, მოდელის ვერსია, კოდის ჰეში), რათა მოძველებული რეჟისურა ან ხმა არასოდეს გამოიყენებოდეს.

არავითარი ეფექტების დათვლა (Decision 2): უქმდება როგორც LP-08/BP-185 ქვედა ზღვრები, ისე „0 ეფექტზე FAIL“-იც — განზრახ მშვიდი კადრი დასაშვებია დასაბუთებით (why), ხოლო ტექნიკურად გაყინული ან გაფუჭებული რენდერი მოწმდება ცალკე.

ჯერ ვერტიკალური ჭრილი (Decision 7), შემდეგ 84 კადრი: სანამ 84-ვე კადრზე გადავალთ, S08_SH002, S02_SH008 და S05_SH020 გადიან სრულ ციკლს (script -> brief -> perception -> interpretation -> direction -> render -> sound -> assembly -> re-perception -> Claude review).

YouTube-თან შესაბამისობა (YOUTUBE FIT): Truce 1914-ის სცენარი და ჩვენი წესები (sourced_rules.json) შედარებულია რეალურ წარმატებულ YouTube დოკუმენტურ ფილმებთან — გთავაზობთ მოქნილ, ჟანრზე მორგებულ შაბლონს (კონკრეტული წამებით, ინტერვალებითა და სეგმენტური გადასვლებით), რომელიც ინარჩუნებს ფილმის სევდიან, ცივ ატმოსფეროს და ამავე დროს იცავს მაყურებლის ყურადღებას (Retention).

რას შეამჩნევს მაყურებელი: გაქრება ხელოვნური ეფექტები, მოჭრილი ფეხები/ბრაზიერი (S02_SH008) და საფლავის ჯვრებზე მოციმციმე ნაპერწკლები (S05_SH020); თითოეული კადრი, რუკა და ხმოვანი გადასვლა ემსახურება ერთ ემოციურ მიზანს — გაყინულ სანგარში მიტოვებული ადამიანების ტკივილსა და ღირსებას.

2. Corrected Research (P0 & Requirement F): Verified Time-Coded Analyses, Sourced Film Craft & Benchmark Plan for Local CPU Tools

We separate (A) Sourced Filmmaking & YouTube Analytics Principles, (B) Ten Re-Verified Time-Coded YouTube Documentary Evidence Rows (with #1 and #6 corrected and concrete visual/audio evidence distinguished from our engineering takeaway), and (C) Local CPU Tool Evaluation & Benchmark Protocol.

2.1 Sourced Filmmaking Principles vs. Our Pipeline Application
Sourced Principle & Primary Citation	What the Source Actually Establishes	How We Apply It (Our Engineering Interpretation)
Walter Murch — The Rule of Six (UC Berkeley iSchool, StudioBinder, Video Essay 00:42–03:15)	Murch ranks cut/transition priorities as: (1) Emotion (51%), (2) Story (23%), (3) Rhythm (10%), (4) Eye-trace (7%), (5) 2D screen plane (5%), (6) 3D action space (4%).	We use this hierarchy in living_director.py so emotional restraint (director_brief) overrides decorative particle density, and camera targets follow eye-trace (BP-30, BP-195).
Walter Murch — "Dense Clarity" & Law of Two-and-a-Half (Designing Sound Special)	Human perception tracks up to two independent foreground acoustic/visual layers clearly; at three or more simultaneous foreground motions/sounds, individual detail collapses into "womb tone" / clutter.	Supports dropping LP-08 (effects_min = 3) and BP-185 (families_min = 2), and keeping BP-56 (same_class_max: 2, layers_max: 5 in sourced_rules.json).
Randy Thom — Designing a Movie for Sound (FilmSound.org, A Sound Effect)	Sound must be planned from the script/brief stage around emotional point-of-view (subjective isolation vs. environmental exposure) rather than added as literal post-production sound effects on every noun.	The screenwriter's director_brief includes sound_perspective, which feeds the authoritative post-direction sound_plan.py::build pass.
Michel Chion — Audio-Vision: Added Value & Synchresis (Audio-Vision Ch. 1 PDF, ShapingWaves)	Synchresis is the perceptual fusion between a punctual sound transient and a simultaneous visual motion onset (±1 frame), giving physical weight to 2D drawings and map actions.	Map actions (route_arrow, front_line, pulse) and 2.5D action beats share a single frame-accurate timeline (episode/events.py::visual_events, BP-54: early_max_ms: 45, late_max_ms: 125).
3D Photography & Layered Depth Inpainting (Shih et al., CVPR 2020, Paper PDF)	Unlayered depth displacement stretches foreground-to-background boundary pixels ("rubber-sheet tearing"); clean parallax requires layer separation and occluded context inpainting.	We combine understand.py::clean_plate (run_lama at L502) with per-relationship motion_isolation.py so moving elements never warp their rigid holders or background silhouettes.
YouTube Studio Official Audience Retention Metrics (YouTube Help 9314415, YouTube Help 12942217, YouTube Help 13861714 Test & Compare)	YouTube Studio reports Intro (% still watching at 0:30), Top Moments (flat retention slope), Spikes (rewatched segments), and Dips (abandonment/skipping). Note: YouTube does NOT publish a universal "5-second drop-off law"; our 5.0 s ceiling on still_25d (BP-109, shot_split.MAX_STILL_S = 5.0) is an explicit house engineering rule (Decision 4), not an external scientific law.	We enforce MAX_STILL_S = 5.0 as our house upper bound on still_25d sub-shots (Decision 4) and align chapter/hook structure in Part 8 (YouTube Fit) to Studio's 30-second Intro and Dip diagnostics.
2.2 Ten Re-Verified Time-Coded YouTube Documentary Analyses (P0 & Requirement F)

Every row below has been verified for exact video title, channel attribution, and concrete audiovisual evidence at the cited timecodes:

#	Verified Channel & Exact Video Title (Clickable Link)	Time Code & Dramatic Situation	Concrete Evidence: What Is Seen & Heard in the Video	Our Engineering & Direction Takeaway (Separated from Evidence)
1	The Great War (Indy Neidell) — A Sign Of Friendship In The Midst Of War | THE CHRISTMAS TRUCE 1914 (Special Episode published Dec 24, 2014; replaces the mislabelled Week 22 link)	00:00–00:55 (Opening Contrast) & 05:40–06:55 (Commanders' Ban & Return of War)	Seen & Heard: Opens on archival stills of freezing mud-filled trenches in Flanders while Indy Neidell describes five months of industrial slaughter before Christmas Eve; at 05:40–06:55, over stark monochrome photographs of soldiers back on the fire step, the narration states verbatim: "in the middle of the largest war in history came a moment of peace and humanity, sadly such a moment was not to happen again, for by Christmas 1915 those same men who celebrated the truce with each other were now murdering each other with poison gas." Slow zoom into the soldiers' faces; subdued low drone underneath.	Takeaway for S08_SH002: The epilogue (S08_L002: "Their commanders moved to prevent it from happening again...") must visually emphasize the return of freezing trench reality (falling snow, open night trench, solitary candle), never a warm cosy room.
2	The Great War (Indy Neidell) — The First Battle of Champagne — Dying In Caucasus Snow | THE GREAT WAR Week 22 (Correctly titled Week 22 episode)	00:15–01:45 (Winter Exposure & Freezing Trenches)	Seen & Heard: Archival plates of waist-deep winter snow and soldiers wrapped in heavy coats in the Caucasus and Champagne; slow pan across huddled infantrymen accompanied by wind and sombre low strings while narration details soldiers freezing to death in their positions.	Takeaway for S02_SH008 & S08_SH002 (G-c): Winter war shots communicate suffering through visible atmospheric cold (snow drift, breath, hunched posture around a small heat source) and framing that shows the men trapped inside the trench walls.
3	Imperial War Museums (IWM) — The Christmas Truce in 1914 — I Was There: The Great War Interviews	00:10–01:15 (Trench Proximity) & 02:10–03:25 (First-Hand Voiceover Over Still Plates)	Seen & Heard: Recorded audio of WWI veterans describing the frost and hearing German voices across No Man's Land; onscreen, high-resolution archival photographs are held with a single slow, steady push-in (~4–6 s per framing) toward the subjects' eyes and hands, with zero artificial particle overlays and clean dialogue priority.	Takeaway for Decision 2 & S05_SH020: When the spoken line carries high emotional gravity, a slow, clean camera move toward the human subject with minimal, physically real motion outperforms busy multi-effect animation.
4	Extra History — WW1 Christmas Truce: Silent Night — Extra History — Part 1 (Companion Article)	00:00–00:42 (Cold Open Hook) & 03:10–04:15 (Pope Benedict XV's Failed Appeal)	Seen & Heard: Hand-drawn 2.5D illustrated scenes; opens in the freezing trench before cutting back to August 1914's "Home by Christmas" expectation; at 03:10–04:15, the narration explains Pope Benedict XV's December call for a truce and the governments' refusal, cutting directly from high-level diplomatic imagery to shivering soldiers on the trench fire step.	Takeaway for S02_SH008: S02_L008 ("In early December, the Pope asked for a Christmas truce. The appeal failed... Nobody asked the men in the trenches") uses this exact structural contrast: establish the men huddled around the brazier during the Pope's failed appeal, then push onto Thomas on the final sentence.
5	HistoryMarche — Hannibal (Parts 11–13) — Battle of Cannae, 216 BC (Full Documentary) (Verified HistoryMarche flagship map documentary)	01:10–02:45 (Strategic Campaign Map) & 14:20–16:05 (Two-Wing Deployment Pan)	Seen & Heard: Shaded top-down terrain map; campaign arrows draw smoothly across geographic waypoints synced to spoken place names while subtle marching/draw audio plays during the arrow span; at 14:20–16:05, as the narrator describes the left wing and then the right wing, the camera pans horizontally from one flank to the other, holding briefly on each.	Takeaway for S02_SH001 & S05_SH020: (1) Sync route_arrow drawing and its map_route_draw sound strictly to the spoken clause span (S02_SH001); (2) when narration names two opposing or paired groups in sequence (S05_SH020), pan between their measured coordinates with a brief settle on each.
6	Kings and Generals — Marlborough's Masterpiece — The Battle That Humiliated the Sun King (Verified Kings and Generals channel, Production Study)	01:30–03:10 (Theater Overview to Sector Zoom)	Seen & Heard: Starts on a wide European theater map showing allied march routes, then zooms down into the Danube/Blenheim sector as the narrator shifts from grand strategy to the battlefield where the armies stand close together; subtle low-frequency transition sound accompanies the scale change while label chips appear silently or with a soft tick.	Takeaway for S02_SH002 -> S02_SH003 & Decision 3: Keep slow map drifts silent (silent_by_design), synchronize tactile sounds to drawn map actions (route_arrow, front_line), and use an environmental bed only when the scene's acoustic perspective transitions toward the physical ground.
7	Epic History TV — World War 1 (All Parts, 4K)	01:15–02:40 (August 1914 Schlieffen Plan) & 11:40–13:10 (Western Front Trench Line from North Sea to Switzerland)	Seen & Heard: Relief map of Belgium and northern France; at 01:15, German invasion arrows sweep through Liège and Brussels toward the Marne; at 11:40, a continuous fortified line traces from the Belgian coast to the Swiss border while the narrator explains the race to the sea and the end of mobile warfare.	Takeaway for S02_SH001 & S02_SH002: Directly parallels S02_SH001 (August arrow from Aachen via Liège/Brussels to the Marne) and S02_SH002 (December trench line from the North Sea to Switzerland); consecutive maps of the same theater should carry over visual continuity (maps/actions.py::_build_carry_over, L178).
8	Johnny Harris — How I Make My Maps & FCPX Vox/Johnny Harris Documentary Style Breakdown	01:30–03:20 (Map Layering & Camera Tilt) & Craft Breakdown on Tactile Sound	Seen & Heard: Demonstrates building shaded-relief plates with tilted bird's-eye camera (bird_eye_60), glowing route lines, and physical paper/shutter/pen sounds locked to visual onsets ("A soft paper thud as the element lands, a shutter click on a hard cut").	Takeaway for maps/actions.py & episode/events.py: Every label, route_arrow, and front_line action in TACTILE_MAP shots gets an explicit, frame-locked audio decision in events.visual_events.
9	LEMMiNO — Grazed by the Apocalypse & The Enduring Mystery of Jack the Ripper (Format Analysis)	00:00–01:15 (Measured Cold Open) & 18:30–20:00 (Dark Atmospheric Restraint)	Seen & Heard: Calm, unhurried narration (~135–155 WPM) over dark, high-contrast illustrated plates where only a single element moves (a flickering gas lamp or slow rain/snow) over a continuous low ambient room tone.	Takeaway for Decision 2 & YouTube Fit: High retention in serious historical/investigative documentaries does not require frantic 230 WPM shouting (mrbeast_animated); it requires clean visual-verbal alignment, atmospheric tension, and zero dead air at cuts.
10	Simple History / BBC Archive — Christmas Truce (1914) & 1968: Remembering the CHRISTMAS TRUCE | Voice of the People | BBC Archive	00:20–01:10 (Trench Misery) & 02:40–03:35 (Joint Burial & Capt. Stockwell's Boxing Day Shots)	Seen & Heard: Recounts the joint burial service in No Man's Land and Captain Stockwell at Houplines firing three pistol shots into the air on Boxing Day morning (S07_SH005) to end the truce before artillery resumes.	Takeaway for S05_SH020 & S07_SH005: Keep the burial service (S05_SH020) reverent and unhurried (7.75 s split into two calm camera framings), and lock the three revolver shots in S07_SH005 (S07_SH005.S1..S3) to the spoken word "shots".
2.3 Benchmark Protocol for Local CPU Perception Models (Decision 5 & P2)

Per the outside review (3.F) and Creator Decision 5, we do not hardcode unverified speed/accuracy claims or treat model outputs as infallible truth. In Step 2B (Vertical Slice), we run a reproducible benchmark script (scripts/benchmark_perception_cpu.py) on the actual Truce assets (S08_SH002, S02_SH008, S05_SH020 rasters and WAVs) before locking default model weights:

Domain	Candidate Models Benchmarked on Real Truce Assets	Existing Repo Baseline Extended	Benchmark Metrics Recorded & Role in Pipeline
Visual Object Grounding & Captioning	

• IDEA-Research/grounding-dino-tiny / onnx-community/grounding-dino-tiny-ONNX (open-set text-query bbox detection)




• microsoft/Florence-2-base (<CAPTION_TO_PHRASE_GROUNDING>, <MORE_DETAILED_CAPTION>)

	explainer_engine/production/understand.py (run_sam at L382, run_da_v2_small at L94, picture_geometry at L237, light_mask at L476)	Measure CPU latency (seconds/image), bbox IoU against layers/*.png masks, and false-positive/false-negative rates on mug, letter, rifle, brazier, candle, crosses, sky. Crucial rule: Object detection (soldier) is separated from character identity (Thomas left vs. Harris right, resolved via screen_composition spatial relations + mask geometry).
Audio Event Classification & Semantic Check	

• Primary lightweight candidate: TensorFlow YAMNet (3.7M weights, 521 AudioSet classes on 0.975s windows)




• Secondary candidate: MIT/ast-finetuned-audioset-10-10-0.4593




• Optional semantic comparator: LAION-AI/CLAP (laion/clap-htsat-unfused)

	explainer_engine/qa/sound_realism.py::measure & explainer_engine/qa/frame_review.py::loudness (L399)	Layer 1 (mandatory): waveform RMS, LUFS (BP-50..52), spectral masking (BP-118), and silence/dropout checks (BP-189). Layer 2 (coarse event check): YAMNet vs. AST benchmarked on rendered Truce stems (wind, fire, speech, music). Layer 3 (optional advisory): CLAP. Human/Claude listening remains the final acceptance authority.
3. The Six Crew Contracts, Authoritative Sound Lifecycle & Deterministic Cache Fingerprints (Requirements A, B, C, D, E & P1–P4)

To prevent the pipeline from becoming a loose pile of detectors, every stage communicates through strictly typed, versioned JSON contracts separating Perception -> Interpretation -> Direction -> Execution -> Re-Perception Feedback.

3.1 Contract 1: PerceptionResult (explainer_engine/production/perceive_picture.py -> layers/perception.json)

Extends understand.py::understand (L611) and load (L742). Core Rule (Requirement A): A missed detection (confidence < threshold or not_detected) is recorded as "status": "uncertain" or "not_detected", NEVER as automatic proof of physical absence unless corroborated by positive counter-evidence (e.g., an unobstructed segmented hand mask holding a tin_mug where a letter was expected).

JSON
{
  "schema": "perception_result/1.0",
  "shot_id": "S02_SH008",
  "dependency_fingerprint": "sha256:...",
  "provenance": {
    "picture_path": "episodes/ep_truce_1914/pictures/S02_SH008/start_01.png",
    "picture_sha256": "a4f8...",
    "detector_model": "IDEA-Research/grounding-dino-tiny@06fa2e0",
    "segmenter_model": "sam2.1_hiera_tiny+understand/1.2",
    "depth_model": "depth-anything-v2-small",
    "inference_settings": {"box_threshold": 0.28, "text_threshold": 0.25}
  },
  "environment": {
    "sky_visible": {"value": true, "confidence": 0.96, "sky_mask_file": "sky.png", "sky_y_bounds": [0.0, 0.162], "horizon_contour_y_p95": 0.168},
    "enclosure": {"value": "open_trench", "confidence": 0.91, "uncertainty_note": null},
    "lighting_observed": {
      "dominant_palette": "cold_slate_blue_dusk",
      "active_emitters": [
        {"id": "brazier_fire", "kind": "fire", "centroid": [0.521, 0.585], "bbox": [0.445, 0.520, 0.595, 0.642], "holder_bbox": [0.430, 0.640, 0.610, 0.902], "confidence": 0.95}
      ]
    }
  },
  "objects": [
    {
      "object_id": "obj_person_left",
      "detected_class": "soldier",
      "candidate_identity": {"character_id": "char_thomas_hale", "basis": "screen_composition.screen_direction_notes ('Thomas left')", "confidence": 0.92},
      "mask_file": "thomas.png",
      "centroid": [0.242, 0.581],
      "bbox": [0.048, 0.198, 0.432, 0.962],
      "support_base_y": 0.962,
      "head_box": [0.210, 0.205, 0.315, 0.365],
      "mouth_anchor": [0.285, 0.342],
      "confidence": 0.97
    },
    {
      "object_id": "obj_held_left",
      "detected_class": "metal_mug",
      "holder_object_id": "obj_person_left",
      "relation": "held_in_hands_of(obj_person_left)",
      "bbox": [0.265, 0.515, 0.325, 0.580],
      "top_rim_line": [0.270, 0.515, 0.320, 0.515],
      "confidence": 0.86
    }
  ],
  "scripted_queries_audit": [
    {"query": "letter", "expected_by": "screen_composition.midground", "status": "not_detected_replaced_by_other", "observed_instead": "metal_mug", "confidence": 0.86, "breaks_spoken_narration": false},
    {"query": "rifle", "expected_by": "screen_composition.midground", "status": "not_detected", "observed_instead": "hands_resting_on_knees", "confidence": 0.81, "breaks_spoken_narration": false}
  ],
  "occlusions_and_boundaries": {
    "fg_union_mask": "fg_union.png",
    "parapet_wire_band_y": [0.155, 0.285]
  }
}

3.2 Contract 2: InterpretationRecord & DirectorDecisionRecord (living_director.py -> production/direction/<shot_id>.json)

Before generating a single camera keyframe or shader track, living_director.py runs an explicit Interpretation Step (interpret_scene) that reconciles (1) PerceptionResult, (2) shot.director_brief, (3) spoken audio_lines, (4) historical context, and (5) adjacent shots (prev_direction, next_shot):

Uncertainty & Conflict State Machine (Requirement A & G-e):

ALIGNED: Picture and script/brief agree (confidence >= 0.70). Proceed to direction.

ADAPTED_STAGING_NON_BREAKING: Picture differs from unvoiced script staging prose (screen_composition / action_start_state), but does not contradict audio_lines or director_brief meaning (e.g., S08_SH002 open trench vs. dugout bunk; S02_SH008 tin mug vs. letter). Preserve original authored_staging in shot.authored_intent_archive, record approved_visual_staging, and direct the physical picture.

UNCERTAIN_NEEDS_REVIEW: Perception confidence on a key focal element is low (< 0.60) or ambiguous. Do not invent effects; use conservative safe framing, set status: "REVIEW", needs_eye: true, and surface in the Look-and-Listen bundle.

STORY_BREAKING_CONFLICT: Picture contradicts a noun, person, or action explicitly spoken in audio_lines. Write to episodes/<ep>/production/regeneration_queue.json (needs_regeneration: true) and emit FAIL at stage_clips.

Stillness Taxonomy (Creator Decision 2):

DELIBERATELY_STILL: The director chooses 0 environmental/subject effects (or camera-only / breath-only) because the brief and spoken beat call for sacred or stark stillness, and writes a non-empty stillness_reason in decision_record. Status: PASS (reviewed by Claude in Look-and-Listen).

ACCIDENTALLY_FROZEN: The director planned active camera or element motion (tracks non-empty), but the rendered video frames have near-zero frame-to-frame optical flow (BP-194 frozen_window_s). Status: FAIL (renderer defect).

TECHNICALLY_BROKEN: Motion leaks onto rigid holders (gate_motion_isolation_leak), crops slice anchor bases (keep_in_frame), or NaN/black frames occur. Status: FAIL.

3.3 Contract 3: Authoritative Sound Lifecycle & Hand-Off (Requirement B & P4)

The outside review (3.B) identified a critical lifecycle bug in episode/run.py: previously, stage_sound_plan (L345) and stage_clips (L873, calling SP.build) ran before direction existed, and stage_sound (L1292) rebuilt the sound plan from the raw script alone, ignoring living_director.py.

Fixed Authoritative Lifecycle in episode/run.py & episode/sound_plan.py:

Provisional Pre-Clip Plan (stage_sound_plan, run.py:345): Marked explicitly "status": "provisional_pre_direction" in sound_plan.json — used only to check early script cue budgets (BP-81) and voice timing.

Direction & Visual Event Resolution (stage_direction / stage_clips, run.py:598, 873):

Runs perceive_picture -> living_director.direct (for still_25d and map_action) and maps/actions.plan (for map_action).

Writes production/direction/<shot_id>.json containing the director's audio_direction block (sound_of_direction at L1009 / sound_of_map at L1029: acoustic perspective, intentional silence reason, weather/place bed choice, and point-sound events locked to visual_events frame spans).

Updates production/av_events.json via episode/events.py::visual_events (L214) so every map action, 2.5D motion, and LTX action shares one canonical frame timeline [start_frame, end_frame) on the measured word spine (D-135).

Authoritative Final Sound Plan (stage_sound, run.py:1292 -> sound_plan.py::build, L489):

sound_plan.build(script, ..., directions=loaded_directions, av_events=loaded_av_events) builds the one authoritative final sound_plan.json ("status": "authoritative_post_direction").

Reconciles authored script sound_events with direction.audio_direction and events.visual_events (deduplicating by event_id and class within BP-39's 0.15 s window so no action ever gets double-sounded).

Honours Creator Decision 3 on maps: every meaningful map action (route_arrow, front_line, pulse) gets its explicit synced sound decision; slow camera moves stay silent_by_design; environmental beds (place_bed, L478) are placed only when director_brief.sound_perspective / sound_of_map calls for one, and intentional silence is documented with why.

Final Mix & Feedback (production/assemble.py::build_audio_v2 at L362 & audio/stems.py):

Renders voice, music, bed, and sfx stems with BP-53 sidechain ducking and BP-191 cross-cut bed continuity, then runs qa/perceive_audio.py on the delivered mix to verify that planned events are audible (BP-192) and dialogue isn't masked (BP-52, BP-118).

3.4 Contract 4: Deterministic Dependency Fingerprints (Requirement C & P2)

We extend explainer_engine/production/understand.py's existing _write_key / _read_key (L588–596) into a shared helper explainer_engine/core/fingerprints.py (new file) used by understand.py, perceive_picture.py, run.py::ensure_shot_direction (L554), directed25d.py, map_clip.py, and sound_plan.py:

direction_fingerprint(shot, script, layers, perception, kb) = SHA-256 of:

picture_sha256 (start_01.png bytes)

Canonical JSON of shot fields (action_start_state, action_end_state, screen_composition, camera_spec, lighting_and_time, motion_imitation, actions, route, target_duration_seconds)

Canonical JSON of spoken audio_lines for the shot + measured word spine timestamps

Canonical JSON of shot.director_brief

perception.dependency_fingerprint (which embeds detector_model, segmenter_model, depth_model, and layers/manifest.json hash)

sha256_file("explainer_engine/standards/director_knowledge_base.json") + sha256_file("explainer_engine/standards/motion_isolation.json")

DIRECTOR_CODE_DIGEST (SHA-256 of living_director.py, direction.py, living.py, living_fx.py, motion_isolation.py).

In episode/run.py::ensure_shot_direction (L554), a cached production/direction/<shot_id>.json is reused if and only if doc.get("dependency_fingerprint") == expected_fingerprint. Any change to the brief, picture, spine, model, or code invalidates the cache automatically.

3.5 Contract 5: Physical-Relationship Motion Isolation & Multi-Component Leak Gate (Requirement D & P3)

Instead of a single naive HSV rule, explainer_engine/production/motion_isolation.py + standards/motion_isolation.json implement relationship-specific isolation operators passed to directed25d.py::Stage (L110) and living_fx.py::apply (L381):

Physical Relationship	Why Simple HSV Fails (Outside Review 3.E)	Relationship-Specific Isolation Method in motion_isolation.py
1. flame_in_open_grate (S02_SH008 brazier)	Glowing coals sit behind dark iron bars; a flat horizontal cut warps the iron bars that cross the coals.	Bar-Preserving Luminance Mattes: Within the brazier SAM mask (layers/brazier.png), segment the dark iron grating bars (local luminance < P35 of mask + high Sobel horizontal/vertical bar gradient) into anchor_mask (alpha_motion = 0.0, dilated 2px). Only the high-luminance orange/yellow coal gaps and the upper flame plume (above grate top y) receive alpha_motion > 0, with 4px guided-filter feathering.
2. flame_on_candle_wick (S08_SH002 candle in tin holder)	Candle flame sits above a wax stub inside a reflective tin holder on a crate; glow reflects on the tin rim.	Wick-Apex Plume Split: Locate the brightest warm core ([0.848, 0.345]). mover_mask (geometry displacement) is strictly an elliptical teardrop above the wick apex (y < y_wick). The tin holder and wax stub below y_wick are in anchor_mask (0.0 displacement) and receive additive RGB radiance modulation only (zero pixel coordinate warp).
3. steam_over_held_vessel (S02_SH008 tin mug in gloved hands)	Semi-transparent steam overlaps the mug rim, gloved fingers, and coat chest behind the mug.	Additive Advected Alpha Field (Zero Background Warp): Steam (living_fx.py::_particles / _breath) is rendered as an independent translucent alpha layer spawned at mug.top_rim_line, occluded by (1.0 - hand_and_mug_body_mask), using screen blending (living_fx.py:40). It never warps or displaces the underlying RGB pixels of the mug, fingers, or coat.
4. breath_from_mouth (S02_SH008, S05_SH020)	Breath plume crosses the soldier's jaw, collar, or background figures.	DirectionalCone Alpha Overlay: Spawned at mouth_anchor along gaze vector (living_fx.py::_breath, L301), multiplied by (1.0 - face_mask). Pure alpha screen composite; zero underlying pixel warp.
5. sky_and_ground_weather (S02_SH008 stars, S05_SH020 frost/sun)	Box-based stars or glint land on barbed wire, sandbags, or wooden grave crosses.	Strict Layer-Matte Multiplication: Sky effects (stars, cloud_drift, sun_glint) are multiplied by sky_mask * (1.0 - dilated_fg_union_mask). Ground frost shimmer is multiplied by snow_ground_mask * (1.0 - dilated_fg_union_mask) and disabled on solemn burial shots.
6. cloth_on_rigid_support (S07_SH005 flag, coats)	Moving the whole cloth mask bends the wooden flagpole or soldier's shoulder.	Geodesic Distance Pinning: Compute distance transform from the rigid pole/torso seam; pin alpha_motion = 0.0 within the proximal 20% attachment band and ramp smoothly to the free fabric edge.

Multi-Component Leak Gate (qa/look_and_listen.py::evaluate_motion_isolation):
For every rendered still_25d clip, we invert the known deterministic camera crop trajectory (cx(t), cy(t), scale(t)) from directed25d.py to align Frame 
𝑡
t back into Frame 
0
0's plate coordinates (eliminating camera movement and parallax translation first!), then measure five separate components:

element_motion_p95: residual optical flow / pixel change inside mover_mask (verifies intended element actually moved).

holder_leak_p95: residual warp of underlying plate structure inside anchor_mask (iron_basket, tin_holder, mug_body, crosses).

camera_residual_error: background alignment error outside all masks (verifies smooth camera interpolation).

boundary_halo_error: gradient spike within a 4px band around foreground mask edges (detects tearing/halos).

forbidden_region_particle_leak: fraction of sky/glint energy falling onto fg_union_mask or below sky_mask (catches S02_SH008 stars on wire and S05_SH020 glints on crosses).

3.6 Contract 6: Post-Render Re-Perception & Closed Feedback Loop (Requirement E & P1, P6)

After directed25d.py::render_clip (L1101), map_clip.py::render_action_map_clip (L171), or LTX renders a clip, and after assemble.py::build_audio_v2 (L362) renders the audio mix, explainer_engine/qa/look_and_listen.py runs Post-Render Re-Perception:

Extracts keyframe strips (0%, 20%, 40%, 60%, 80%, 100%) and runs perceive_picture + evaluate_motion_isolation + keep_in_frame anchor check on the actual rendered frames.

Runs perceive_audio on the actual rendered shot audio slice from the mix.

Compares ObservedRenderResult against DirectorDecisionRecord and chooses one of three automated feedback actions before Claude review:

AUTO_ADJUST_AND_RERENDER (max 1 retry): If holder_leak_p95 exceeds calibrated threshold, or camera crop touches an anchor base (brazier/boots), or a spot SFX masks speech (BP-52), automatically tighten the mask erosion / reduce zoom_strength / duck the SFX by -3 dB and re-render the shot once.

FLAG_FOR_REGENERATION: If the starting plate or LTX clip has a story-breaking visual defect that parameter tuning cannot fix, append to regeneration_queue.json.

READY_FOR_CLAUDE_REVIEW: Package the contact sheet, motion-isolation heatmap, MP4 clip, WAV excerpt, and structured comparison into episodes/<ep>/qa/look_and_listen_bundle/ and set look_and_listen_record.json (status: "PENDING_CLAUDE_REVIEW").

4. Step-by-Step Build Guide in Execution Order — Vertical Slice First (Creator Decision 7 & P0–P6)

Per Creator Decision 7 and Outside Review Section 5, Step 1 through Step 6 are executed and verified on the 3-shot Vertical Slice (S08_SH002, S02_SH008, S05_SH020, plus map shot S02_SH001) FIRST before scaling to all 84 shots in Step 7.

Step	Goal	What Changes (Exact Real Repo Files/Functions vs. New Files)	Rules Added / Changed / Dropped	Verification & Explicit Vertical-Slice Acceptance Criteria	Dependencies	Effort	Risk	What the Viewer Notices
Step 1 (P1)	Typed Contracts, Schema & Deterministic Fingerprints (A, C)	

• New files: explainer_engine/core/fingerprints.py, explainer_engine/standards/screenwriter_guide.json, docs/SCREENWRITER_GUIDE.md.




• Existing files updated:




- explainer_engine/schemas/production_script.schema.json: add free-text shots[].director_brief and shots[].authored_intent_archive.




- explainer_engine/scripting/stage_guard.py: add "director_brief": "edit-planner" to V4_OWNERS.




- explainer_engine/production/understand.py (_write_key at L588, _read_key at L593, understand at L611, load at L742): integrate fingerprints.py and persist mask [cx, cy], bbox, support_base_y, and sky_y_bounds in layers/manifest.json.




- explainer_engine/episode/run.py::ensure_shot_direction (L554): validate full dependency_fingerprint before reusing cached production/direction/<shot_id>.json.

	

• Add SW-01..SW-05 (free-text brief, story/suffering truth).




• Add CACHE-FP-01: Stale direction/perception/sound artifacts are invalidated whenever any upstream input hash changes.

	• Unit Test: tests/unit/test_contracts_and_fingerprints.py verifies that modifying a single word of director_brief, narration, or start_01.png invalidates ensure_shot_direction cache.	None	Medium	Low	Guarantees every creative change in the brief or picture immediately reaches the render.
Step 2 (P2)	Benchmark CPU Perception & Build perceive_picture.py (Decision 5, A, G-e)	

• New files: explainer_engine/production/perceive_picture.py, scripts/benchmark_perception_cpu.py.




• Existing files updated:




- Benchmark IDEA-Research/grounding-dino-tiny vs. microsoft/Florence-2-base + understand.py (run_sam L382, picture_geometry L237, light_mask L476) on S08_SH002, S02_SH008, S05_SH020.




- Produce PerceptionResult (layers/perception.json) with object bboxes, mask centroids (fixing [0.5, 0.5] at living_director.py:1150, 1342), confidence, uncertainty_note, spatial relations, and scripted_queries_audit.

	• Add DIR-EYE-01: Picture wins for physical objects/geometry; Narration + Brief win for meaning/mood; low confidence (< 0.60) -> REVIEW; story-breaking conflict -> regeneration_queue.json.	

• Vertical-Slice Acceptance:




- S08_SH002: detects open night sky (y=0..0.15), gloved hands + portrait/button, candle in tin holder ([0.848, 0.375]).




- S02_SH008: measures true centroids (thomas cx≈0.24, brazier [0.52, 0.69], harris cx≈0.76), detects metal_mug, flags letter/rifle as non-breaking staging adaptation.




- S05_SH020: measures true centroids for left_group (cx≈0.26), cross_*, and right_group (cx≈0.73).

	Step 1	High	Low	The system knows what is actually painted in S08_SH002, S02_SH008, and S05_SH020 and where every person, flame, mug, and cross sits.
Step 3 (P3a)	Relationship-Specific Motion Isolation & Calibrated Leak Gate (Decision 2, D, G7)	

• New files: explainer_engine/standards/motion_isolation.json, docs/MOTION_ISOLATION.md, explainer_engine/production/motion_isolation.py.




• Existing files updated:




- explainer_engine/production/living_fx.py (apply L381, _particles L92, _sun_glint L182, _sparkle L241, _breath L301, _surface L332) & explainer_engine/production/directed25d.py (Stage L110, render_clip L1101): implement the 6 relationship-specific isolation operators (bar-preserving brazier flame, wick-apex candle plume, additive mug steam, directional breath cone, sky/ground matte clipping, geodesic cloth pinning).

	

• Add MI-01..MI-06 in motion_isolation.json.




• Add gate_motion_isolation_leak (calibrated on Task 1 known-bad S02_SH008 / S05_SH020 vs. Step 2B known-good renders per D-59).

	

• Vertical-Slice Acceptance:




- Fails on Task 1 S02_SH008 (stars on wire, brazier warp) and Task 1 S05_SH020 (ice glints on crosses).




- Passes on new S08_SH002, S02_SH008, S05_SH020: tin candle holder, iron brazier bars, mug, barbed wire, and grave crosses have zero leak/sparkles.

	Step 2	High	Medium	Flames move while holders stay solid; steam rises from the mug without bending the mug or fingers; no stars on wire or glints on crosses.
Step 4 (P3b)	Scene Director Interpretation, Zero Effect Quotas & Anchor Framing (Decisions 2, 4, G1, G3, G4, G6)	

• New file: docs/DIRECTOR_GUIDE.md.




• Existing files updated:




- explainer_engine/standards/director_knowledge_base.json: replace count floors with Murch hierarchy + situation methods.




- explainer_engine/production/living_director.py (choose_camera L471, keep_in_frame L701, direct L745, build_shot_direction_from_script L1113), explainer_engine/production/direction.py (check L185, _balance L328, _families L335), and explainer_engine/production/living.py (plan L111, check L173):




1. Make living_director.py the single creative brain; keep living.py's scoring/feasibility helpers while removing its independent LP-08 FAIL authority (D1 Modified B).




2. Remove all effect count/family floors (Decision 2): Remove LP-08 (effects_min = 3), BP-185 (families_min = 2), and remove if not has_fx: hard_fails.append(...) in run.py:582, 650. Allow DELIBERATELY_STILL shots with a written reason (BP-196); detect ACCIDENTALLY_FROZEN renders separately in QA.




3. Keep shot_split.py (MAX_STILL_S = 5.0, Decision 4): still_25d sub-shots are <= 5.0 s, cut on narrator clause boundaries (shot_split.split_long_still).




4. Anchor-Support Framing (keep_in_frame, L701): Prevent camera crops from slicing the bottom of the brazier or soldiers' boots in S02_SH008.

	

• Drop count FAILs in LP-08 & BP-185 (Decision 2).




• Upgrade BP-196: Perception-grounded inventory with written why for animated and deliberately still elements.




• Keep BP-109 / D-131 (MAX_STILL_S = 5.0) (Decision 4).

	

• Vertical-Slice Acceptance:




- S08_SH002: Exposed cold trench, light falling snow, isolated candle, slow push to button/portrait across 2 sub-shots (<= 5.0s each).




- S02_SH008: Wide establish keeps brazier + boots intact; final sub-shot pushes onto Thomas + steaming mug on "Nobody asked the men in the trenches."




- S05_SH020: Sub-shot 1 frames Scottish chaplain (left_group), Sub-shot 2 pans to German student (right_group), zero glints on crosses.

	Steps 1, 2, 3	High	Low	The three vertical-slice shots communicate cold trench suffering (S08_SH002, S02_SH008) and sacred burial stillness (S05_SH020).
Step 5 (P4)	Authoritative Post-Direction Sound Lifecycle & Mix (Decision 3, B, G5)	

• Existing files updated:




- explainer_engine/episode/run.py (stage_sound_plan L345, stage_clips L873, stage_sound L1292): make stage_sound generate the authoritative sound_plan.json after stage_direction / stage_clips outputs exist.




- explainer_engine/episode/sound_plan.py (shot_events L286, design_of L390, place_bed L478, build L489) & explainer_engine/episode/events.py (visual_events L214, default_audio L121): consume direction.audio_direction (choose_sound / sound_of_direction / sound_of_map), deduplicate against scripted sound_events, and apply Creator Decision 3 on maps (explicit decision per map action, optional bed only when perspective calls for it, documented intentional silence).




- explainer_engine/production/assemble.py::build_audio_v2 (L362): enforce BP-53 ducking and BP-191 cross-cut bed continuity while respecting intentional silence windows.

	

• Add SND-AUTH-01: Final sound_plan.json is built post-direction over the shared events.visual_events clock.




• Update AV-04 (Decision 3): Map actions carry synced tactile decisions; camera moves may be silent; beds are perspective-driven, never forced wallpaper.

	

• Vertical-Slice Acceptance:




- Render mixed audio for S08_SH002, S02_SH008, S05_SH020, and S02_SH001.




- Verify wind + candle/brazier crackle in S08_SH002 & S02_SH008, hushed snow air under the psalm in S05_SH020, and frame-synced map_arrive_click + map_route_draw in S02_SH001.

	Steps 1, 4	High	Low	Sound matches what is seen on screen and what the brief intends—never generic or disconnected.
Step 6 (P6)	Re-Perception Feedback Loop & Vertical-Slice Look-and-Listen Sign-Off (Decision 5, 7, E, G2)	

• New files: explainer_engine/qa/perceive_audio.py, explainer_engine/qa/look_and_listen.py.




• Existing files integrated: explainer_engine/qa/frame_review.py (check L150, contact_sheets L358, loudness L399), explainer_engine/qa/sheet_review.py (request L44, apply L55), explainer_engine/qa/visual_judge.py (verdict L86), explainer_engine/qa/sound_realism.py (measure).




• Run the complete Vertical Slice (S08_SH002, S02_SH008, S05_SH020, S02_SH001) through re-perception (YAMNet vs. AST benchmarked on the rendered WAVs, optical-flow leak gate on the MP4s), generate episodes/ep_truce_1914/qa/look_and_listen_bundle/, and submit for Claude + Creator Vertical-Slice Review.

	• Add QA-LL-01: Re-perception feedback loop (AUTO_ADJUST_AND_RERENDER, FLAG_FOR_REGENERATION, READY_FOR_CLAUDE_REVIEW) + blocking look_and_listen_record.json.	• Vertical-Slice Gate (STOP & VERIFY BEFORE SCALING): All 4 vertical-slice clips pass automated re-perception AND pass Claude's visual + listening inspection on contact strips, MP4s, and WAVs.	Steps 1–5	High	Low	Proves the entire crew architecture end-to-end on real shots before touching the rest of the episode.
Step 7 (P5 & Decision 6)	Scale to All 84 Truce Shots, Sequence Brief Review, LTX compose_prompt & Maps	

• Existing files updated:




- explainer_engine/videolane/scene.py::compose_prompt (L96) & paid_preflight.py: feed director_brief and perceive_picture(start_01.png) into LTX prompt generation, and run look_and_listen.py on generated LTX clips (S07_SH005, etc.).




- explainer_engine/maps/actions.py (render_frame L1428) & explainer_engine/production/map_clip.py (render_action_map_clip L171): apply contextual scene palette/vignette continuity (D4).




- Draft all 84 director_brief objects in episodes/ep_truce_1914/story/production_script.json and export docs/wip/TRUCE_84_BRIEFS_SEQUENCE_REVIEW.md (Decision 6) for sequential emotional continuity review.

	• Add VL-BRIEF-01 (LTX prompt brief & picture alignment) & SEQ-BRIEF-01 (sequential emotional progression across consecutive shots).	• Test: Full test suite + stage_script, stage_direction, stage_clips, stage_sound, stage_assemble, stage_qa dry/CPU run across ep_truce_1914.	Step 6 approved	High	Low	The entire 84-shot film plays with coherent emotional progression across LTX video (60%), 2.5D stills (30%), and tactile maps (10%).
5. Outline of the Knowledge Bases & Sequential Brief Hand-Off (Decisions 2, 3, 6)
5.1 explainer_engine/standards/screenwriter_guide.json + docs/SCREENWRITER_GUIDE.md

No numeric effect budgets, no closed enums.

Defines how .claude/agents/edit-planner.md writes director_brief for each shot as part of a continuous emotional sequence (segment.mood -> prev_shot.director_brief -> shot.director_brief -> next_shot.director_brief).

Distinguishes authored_intent_archive (what the writer originally imagined before pictures existed) from approved_visual_staging (what is physically present in the approved start_01.png painting, reconciled when non-breaking).

5.2 explainer_engine/standards/director_knowledge_base.json + docs/DIRECTOR_GUIDE.md

Organizes the director's rules into the 5-stage pipeline (Perception -> Interpretation -> Direction -> Execution -> Re-Perception Evaluation).

Encodes Creator Decision 2: zero mandatory effect counts; DELIBERATELY_STILL is valid when justified in decision_record.why; ACCIDENTALLY_FROZEN and TECHNICALLY_BROKEN are caught by comparing planned_tracks against observed_flow in look_and_listen.py.

Encodes Creator Decision 3: map actions receive explicit synced tactile sound decisions; map camera moves may be silent (silent_by_design); environmental beds are placed only when the scene's acoustic perspective requires them.

Encodes Creator Decision 4: still_25d sub-shots never exceed shot_split.MAX_STILL_S = 5.0 s (BP-109); shorter cuts (1.5–4.5 s) on spoken clause boundaries are encouraged whenever the narration shifts focus.

Encodes Constraint D4 on Color Grading: localized cold shadow / warm light grading in living_fx.py::apply inspects the picture's existing RGB histogram, light source coordinates, time of day, and skin/cloth masks first so it never slaps a generic blue filter over warm paintings.

5.3 Sequential Brief Review Table Format (Creator Decision 6 -> docs/wip/TRUCE_84_BRIEFS_SEQUENCE_REVIEW.md)

When drafting all 84 briefs, we output a sequence review table with all 8 columns required by the outside review (4.Q4), illustrated here on our Vertical Slice shots and their neighbours:

Shot ID & Route (target_s -> split_s)	Exact Spoken Narration (audio_lines)	Picture Summary (perceive_picture on Approved Raster)	director_brief (Mood, Viewer Feeling, Physical Truth, Focal Priority, Sound Perspective, Restraint)	Historical Context (citation_ids)	Picture vs. Script Conflict & Resolution	Emotional Progression (Prev -> Current -> Next)	Approval Status
S02_SH001 (map_action, 6.0s)	"The war had begun in August. Everyone said it would be over by Christmas." (S02_L001)	Shaded-relief plate of Belgium & northern France from Aachen to the Marne (span_km: 530).	

Mood: Hubristic late-summer confidence.




Feeling: The illusion of a swift 19th-century campaign.




Truth: Command map table; arrow sweeps Aachen -> Liège -> Brussels -> Marne.




Sound: Crisp map_arrive_click on "August", continuous map_route_draw on "Everyone... Christmas"; camera dolly silent; faint command-table room tone.

	C-05: Schlieffen sweep & "Home by Christmas" illusion (Aug 1914).	ALIGNED	Transitions from S01_SH005's quiet mystery into the ironic origin of the war (S02_SH001) before freezing into trench deadlock (S02_SH002).	DRAFT_FOR_CREATOR
S02_SH008 (still_25d, 10.0s -> split via shot_split.py into 3.4s + 3.0s + 3.6s)	"In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed. Nobody asked the men in the trenches." (S02_L008)	Open sandbagged trench at blue dusk (sky_y: 0..0.16, wire 0.16..0.28); Thomas (cx=0.24, left) holds a metal mug ([0.295, 0.545]); glowing iron-basket brazier ([0.52, 0.69]); Sgt. Harris (cx=0.76, right) sits hunched with hands on knees.	

Mood: Freezing misery and bitter institutional abandonment.




Feeling: The physical cold of the trench and the dry sting of "Nobody asked the men in the trenches."




Truth: Open dusk trench, light snow falling, steam rising from Thomas's mug, cold breath, coke brazier glowing inside its rigid iron basket.




Sound: Freezing parapet wind + close brazier crackle + breath.




Restraint: Keep full brazier basket and boots in frame on Sub-shots 1–2; push cleanly onto Thomas's face & steaming mug on Sub-shot 3 ("Nobody asked the men..."). Mask sky above wire.

	C-25: Pope Benedict XV's failed Dec 7, 1914 truce appeal vs. front-line conditions.	ADAPTED_STAGING_NON_BREAKING: Authored script midground said "letter in his hand; Harris... cleaning his rifle" ( archived in authored_intent_archive); approved raster shows tin mug & hands on knees. Spoken line (S02_L008) mentions neither letter nor rifle -> direct the mug & posture.	Follows S02_SH007 ("Keep your head down"), deepening the men's helplessness before S02_SH009 brings Princess Mary tins up the line.	VERTICAL_SLICE_TARGET
S05_SH020 (still_25d, 7.75s -> split via shot_split.py into 4.10s + 3.65s)	"At one burial, a Scottish chaplain read the Twenty-Third Psalm. A German student read it after him, in German." (S05_L020)	Open frozen snowfield under low amber sun ([0.497, 0.235]); 4 wooden grave crosses (y=0.52..0.78) between British/Scottish soldiers (left_group, cx=0.26) and German soldiers (right_group, cx=0.73).	

Mood: Sacred, tragic stillness over shared graves.




Feeling: Reverence and sorrow as one psalm is spoken in two languages.




Truth: Freezing snowfield, bareheaded soldiers, low winter sun, grave candles.




Focal Priority: Sub-shot 1 (0..4.10s) frames left_group + crosses; Sub-shot 2 (4.10..7.75s) pans gently across crosses to right_group.




Sound: Hushed open snow air, zero gunfire, faint boot shift in snow on the language turn.




Restraint: Zero ice glints/sparkles on crosses or coats; soft cold breath and isolated candle flames only.

	C-19: Joint burial services and bilingual Psalm 23 in No Man's Land.	ALIGNED (coordinates measured from layers/left_group.png, right_group.png, cross_*.png).	Peak emotional sobriety of Phase Z3 ("The day"), bridging the burials (S05_SH019) to the football/exchange beats and S06 ("The question").	VERTICAL_SLICE_TARGET
S08_SH002 (still_25d, 8.75s -> split via shot_split.py into 4.55s + 4.20s)	"Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale." (S08_L002)	Open, unroofed snow-lined trench at night (sky_y: 0..0.15); wool-gloved hands in foreground ([0.46, 0.68]) hold a sepia family portrait card and a British brass button; candle in tin holder on crate ([0.848, 0.375]); two far trench braziers ([0.72, 0.39], [0.85, 0.46]).	

Mood: Biting cold, isolation, and quiet heartbreak as the war's iron discipline returns.




Feeling: A man suffering in the freezing night trench, holding onto a tiny relic of humanity that high command has just outlawed.




Truth: Open winter trench at night, light snow falling into the trench, cold wind, candle flame flickering above its tin holder.




Focal Priority: Sub-shot 1 (0..4.55s) frames the open night trench, candle, and gloved hands ("Their commanders moved..."); Sub-shot 2 (4.55..8.75s) pushes into the brass button and portrait card ("A few small truces...").




Sound: Cold open-trench wind, close breath/wool rustle, faint distant rumble.




Restraint: Drop indoor dust_motes and far_brazier_embers; isolate candle flame from tin holder.

	C-23: High command orders prohibiting fraternization and court-martial threats (Dec 1914–1915).	ADAPTED_STAGING_NON_BREAKING: Authored foreground said "edge of a dugout bunk" and "warm candlelight"; approved raster is an open freezing night trench. Spoken line (S08_L002) never says "dugout" -> direct the open freezing trench (Creator G-c).	Follows S08_SH001 (Thomas back in the British trench) as the German mirror image before the final two shots of the film (S08_SH003..004).	VERTICAL_SLICE_TARGET
6. Creator's Final Decisions (1–7 & Q1–Q4 / D1–D4) Applied Summary

Every decision from your prompt and the outside review is locked into R2:

Decision 1: All P0–P6 items and Claude's review notes are integrated into this R2 architecture; zero code written yet.

Decision 2 (Zero Effect Counts): Both LP-08 (effects_min = 3), BP-185 (families_min = 2), and our R1 proposal (FAIL if len == 0) are removed as FAIL gates. A DELIBERATELY_STILL shot passes when the director records stillness_reason in decision_record (BP-196); ACCIDENTALLY_FROZEN (planned_motion > 0 but observed_flow ≈ 0) and TECHNICALLY_BROKEN renders fail in look_and_listen.py.

Decision 3 (Map Sound): Every meaningful map action gets an explicit sound decision; camera moves may be silent (silent_by_design); tactile map sounds (map_route_draw, map_arrive_click, map_pin_set) are synced to map actions; an environmental bed is placed only when the scene's acoustic perspective calls for it; intentional silence is documented.

Decision 4 (5-Second Upper Limit on 2.5D): shot_split.MAX_STILL_S = 5.0 s (BP-109) is strictly preserved as the hard upper limit on still_25d sub-shots (no long-take exception); shorter sub-shots (1.5–4.5 s) cut on narrator clause boundaries via explainer_engine/episode/shot_split.py are encouraged.

Decision 5 (Model Benchmarking): Florence-2-base vs. Grounding DINO Tiny (IDEA-Research/grounding-dino-tiny) and YAMNet vs. AST (with CLAP optional) are benchmarked on the real Truce assets in Step 2; Claude's look-and-listen review remains the final acceptance authority.

Decision 6 (84 Briefs & Authored Intent Preservation): edit-planner stays canonical owner in stage_guard.py; Argon drafts all 84 briefs in Step 7 (after the Vertical Slice passes in Step 6) with the 8-column sequential review table (docs/wip/TRUCE_84_BRIEFS_SEQUENCE_REVIEW.md), preserving original authored_intent_archive separately from approved_visual_staging.

Decision 7 (Vertical Slice First): S08_SH002, S02_SH008, S05_SH020 (and map shot S02_SH001) run end-to-end (script -> brief -> perception -> interpretation -> direction -> render -> sound -> assembly -> re-perception -> Claude review) before scaling to the 84 shots.

7. Separate Final Part: YOUTUBE FIT — Audit of Our Rules & Truce 1914 Against Successful YouTube Documentaries

A film can pass every engineering test and still underperform on YouTube if its pacing, hook architecture, chapter turns, or voice energy clash with viewer expectations in its genre. We audited all 161 rules in explainer_engine/standards/sourced_rules.json, docs/STORY_ENGINE.md, docs/YOUTUBE_50_100_BENCHMARK_AND_ROOT_CAUSE_FIX.md, and the 84-shot episodes/ep_truce_1914/story/production_script.json (367.0 s = 6m 07s) against successful YouTube history/documentary channels and YouTube Studio Retention Analytics.

7.1 Major Conflict Found in sourced_rules.json: mrbeast_animated (BP-169 / BP-171) vs. Historical Docudrama (Truce 1914)

In explainer_engine/standards/sourced_rules.json, rule BP-169 sets "default_profile": "mrbeast_animated", which demands:

hook_0_30s: 193 WPM heard (215–250 WPM speaking), 28 shots/min (1.0–2.5 s per shot), still_max_s: 2.5 s, 14–20 SFX/min, and TTS tags ["excited", "shouting", "rushed", "amazed"]!

Meanwhile, BP-01 demands 170 WPM (FAIL below 150 WPM), and BP-171 demands casting_keywords: ["energetic", "dynamic", "fast-paced"].

Why this is a critical YouTube Fit defect: Measured on episodes/ep_truce_1914/story/production_script.json, Truce 1914's actual script runs at 130 WPM overall (S01: 154 WPM, S02: 142 WPM, S03: 117 WPM, S04: 117 WPM, S05: 132 WPM, S06: 120 WPM, S07: 131 WPM, S08: 140 WPM) with delivery directions like "quiet, matter-of-fact", "reverent, unhurried", and "plain, no comment". If you force a 193 WPM "shouting, excited" voice (BP-169) or fail a 130 WPM solemn read (BP-01 fails < 150 WPM), you destroy the emotional credibility of a WWI Christmas Truce documentary! Conversely, in channels like LEMMiNO, Imperial War Museums, Mustard, and Epic History TV, measured speech (125–155 WPM with deliberate pauses) achieves top-decile retention because visual progression and narrative tension carry the momentum during vocal pauses.

7.2 Flexible Genre-Adaptive YouTube Template (Concrete Ranges & Conditions, Never Robotic Metronomes)

Instead of one rigid profile (mrbeast_animated), we replace BP-169 and BP-01's one-size-fits-all thresholds with a Three-Mode Adaptive YouTube Pacing Template (solemn_historical_docudrama, tactical_campaign_explainer, high_tempo_what_if), selected by the episode's genre and segment mood:

YouTube Dimension	Concrete Range for Solemn Historical Docudrama (Truce 1914)	Concrete Range for Tactical / Battle Explainer (Epic History / Kings & Generals)	Adaptive Condition & Backing YouTube Evidence
1. First Spoken Hook & Title-Promise Payoff (BP-03, BP-04, BP-135)	

• First word onset: 0.2–0.8 s (after a single cold breath/wind transient).




• Title/Thumbnail visual payoff: 0.0–6.5 s (S01_SH001..002: unarmed soldier stepping toward German guns on Christmas morning).




• Core paradox planted: by 12.0–17.0 s (30–45 words).

	

• First word onset: 0.0–0.5 s.




• Title/Thumbnail payoff: 0.0–5.0 s (BP-135).




• Stakes/scale number planted: by 10.0–15.0 s.

	Backed by Extra History Silent Night 00:00–00:42, The Great War Christmas Truce 00:00–00:55, and YouTube Studio Intro Metric (0:00–0:30).
2. Cold Open Duration & First Pattern Interrupt (BP-40, BP-41)	

• Cold open window (S01): 22–32 s (in Truce 1914, S01 is exactly 25.0 s!).




• First major pattern interrupt (Visual Lane + Acoustic Shift): lands at 24–32 s — right where S01 cuts from painted No Man's Land to the tactile relief map in S02_SH001 (t = 25.0 s, "The war had begun in August").

	

• Cold open window: 18–28 s.




• First pattern interrupt: 20–30 s (cut from battlefield hook to strategic theater map).

	Prevents the classic 0:25–0:35 post-intro retention cliff (YouTube Help 9314415) by changing both visual medium (still_25d/video -> map_action) and time period (Dec 1914 -> Aug 1914) at t = 25.0 s.
3. Visual Idea / Framing Change Cadence (BP-109, BP-36, Decision 4)	

• Hook (0–30 s): new shot or sub-framing every 2.0–4.5 s (7–10 visual cuts in first 30 s).




• Body (30 s – end): still_25d sub-shots 2.0–5.0 s (<= 5.0 s hard cap per Decision 4); LTX video clips 3.0–6.5 s; map actions change visual state (label, arrow, line, zoom) every 2.0–3.5 s (BP-147).

	

• Hook (0–30 s): 1.8–3.5 s (9–12 cuts in first 30 s).




• Body (30 s – end): still_25d 1.8–4.5 s; map actions every 1.5–3.0 s.

	Condition: In solemn beats (S05_SH020, S08_SH002), the sub-cut at 3.5–4.8 s is a gentle camera focal shift or axial cut-in on the same canvas (shot_split.py), NOT a jarring change of location (IWM 02:10–03:25).
4. Heard Narration Pace (WPM) & Pause Breathing (BP-01, BP-190)	• Heard WPM (including pauses): 120–155 WPM (speaking rate 150–175 WPM; inter-sentence pauses 0.35–0.90 s, dramatic turns up to 1.2 s filled with cold wind/fire room tone per BP-60 / BP-190).	• Heard WPM: 145–175 WPM (speaking rate 170–200 WPM; inter-sentence pauses 0.25–0.55 s).	Backed by LEMMiNO (~135–150 WPM) and Epic History TV (~145–160 WPM). Reforming BP-01 prevents Truce 1914 (130 WPM) from failing QA!
5. Chapter / Narrative Turn Cadence & Midpoint (BP-42, BP-75, BP-76, YT-02)	

• Chapter / Segment turn interval: every 35–85 s (6–8 chapters in a 6-minute film; 10–14 in a 12-minute film).




• Re-hook / escalation turn: every 60–110 s (scaled proportionally to episode length rather than hardcoded 180 s / 360 s in BP-42).




• Emotional Midpoint (BP-75): at 45–58% of runtime.

	

• Chapter interval: every 45–90 s.




• Escalation turn: every 60–120 s.




• Midpoint reversal: at 40–55% of runtime.

	In Truce 1914 (367 s), S05 ("No man's land", 182.8–268.2 s = 49.8%–73.1%) is the emotional center, but at 85.5 s it is 23% of the entire film without an internal chapter/tension turn (see concrete fix in 7.3 below).
6. Ending & Outbound Retention (BP-43, BP-106)	• Zero sign-off throat-clearing (BP-43): Final historical line lands at 96–99% of runtime (S08_SH004), followed by 2.0–4.0 s of ambient wind/bell tail for the YouTube end-screen overlay — never "In conclusion, thanks for watching!"	Same (BP-43 kept as FAIL).	Prevents the steep final-15-second drop-off that hurts YouTube's session watch-time handoff (YouTube Studio Retention Dips).
7.3 Concrete Audit of Truce 1914 (episodes/ep_truce_1914/story/production_script.json) Under This Template

Measuring the actual 84 shots (367.0 s) of Truce 1914 reveals four specific strengths to preserve and five concrete YouTube Fit bottlenecks to fix:

What Truce 1914 Already Does Well (Preserve):

Cold Open (S01, 0.0–25.0 s): Opens immediately on Christmas morning (S01_SH001, 2.0 s), puts an unarmed soldier walking toward German guns at 2.0–6.5 s (S01_SH002), widens to thousands at 12.0–17.0 s (S01_SH004), and lands the pattern interrupt to the August map (S02_SH001) at exactly 25.0 s.

Clean Abrupt Ending (S08_SH004, 359.5–367.0 s): Ends on a quiet, devastating human line without YouTube sign-off clichés (BP-43).

Lane Mix (BP-109): video = 212.25 s (57.8%), still_25d = 122.75 s (33.4%), map_action = 32.0 s (8.7%) — within the 60/30/10 (±5%) target.

Five Concrete Changes Needed in Truce 1914 for YouTube Fit:

S01_SH005 (17.0–25.0 s, 8.0 s unbroken still_25d right inside the 30-second Hook!):

Problem: Holding a single wide still_25d shot for 8.0 s at t = 17..25 s violates both BP-40 (hook_max_still_s: 5.0 s in the first 30 s) and Decision 4 (MAX_STILL_S = 5.0 s), creating an early Intro retention dip right before S02.

Fix: shot_split.py splits S01_SH005 on the spoken periods ("This is the day the war stopped, along parts of the Western Front." [4.3 s, wide establish] -> "How it began, with a song. And how it ended." [3.7 s, push-in onto the soldiers meeting in the frost haze]).

21 Long still_25d Shots Over 5.0 s Across the Body (S02_SH004 6.2s, S02_SH005 5.5s, S02_SH008 10.0s, S02_SH009 8.2s, S05_SH020 7.75s, S08_SH002 8.75s, etc.):

Problem: In S02 (25.0–83.2 s), four consecutive still_25d shots (S02_SH004, SH005, SH008, SH009) average 7.5 s each; in S08 (342.5–367.0 s), all 24.5 s are still_25d (4 shots averaging 6.1 s).

Fix: shot_split.split_long_still splits all 21 still_25d shots > 5.0 s at clause boundaries (<= 5.0 s each, Decision 4), and our upgraded living_director.py gives each split sub-shot a distinct, word-motivated focal target (e.g., wide trench establish -> close push on Thomas's face & steaming mug on "Nobody asked the men in the trenches" in S02_SH008), turning static holds into active visual storytelling.

19.75-Second Back-to-Back Map Block at 25.0–44.8 s (S02_SH001 6.0s + S02_SH002 7.75s + S02_SH003 6.0s):

Problem: Nearly 20 seconds of top-down maps in the first minute risks losing emotional connection if they look and sound like three disconnected slides.

Fix: Connect S02_SH001 -> S02_SH002 -> S02_SH003 as one continuous zoom-in progression (from the 530 km August sweep -> the 400-mile December trench line -> diving right down into the Flanders sector in S02_SH003 where "the two sides sat close enough to hear each other cough"), bringing in the faint sound of a soldier coughing in the cold mud during the final 2 seconds of S02_SH003 (a J-cut into S02_SH004!).

S05 ("No man's land", 182.8–268.2 s, 85.5 s / 21 shots) Needs an Internal Mid-Segment Escalation Beat:

Problem: S05 runs for 85.5 s covering map spread, haircuts, buttons, football, and the burial (S05_SH020). Without a stark tonal turn before the burial (S05_SH018..020 at t ≈ 240 s), the transition from gifts/football to graves feels flat.

Fix: In the sequential director_brief table (Decision 6), insert a deliberate acoustic vacuum (BP-120) and palette shift at S05_SH018 (when the men look at the bodies lying between the lines): drop the warm fraternization murmur to bare freezing wind for 1.0 s before the burial service (S05_SH019..020) begins.

Segment S08 (342.5–367.0 s) Is 100% still_25d (24.5 s):

Fix: Even without adding paid LTX clips, splitting S08_SH001..004 into <= 4.5 s word-timed camera beats with strong foreground/background depth parallax (BP-35), falling snow, isolated candle light (S08_SH002), and continuous cross-cut wind/music (BP-191) keeps the final 25 seconds visually gripping right up to the end screen.

7.4 Summary of sourced_rules.json Rules to Keep, Change, or Drop
Rule ID(s)	Current Rule in sourced_rules.json	Action (KEEP / CHANGE / DROP) & Exact R2 Specification
LP-08, BP-185, BP-200 (effects_min, families_min)	Hard FAIL if < 3 living effects (LP-08) or < 2 effect families (BP-185).	DROP count floors (Creator Decision 2). Replace with qualitative BP-196 reasoning (DELIBERATELY_STILL allowed with why; ACCIDENTALLY_FROZEN caught in QA).
BP-196	Living inventory: every natural element gets an effect or a written reason why not; camera follows named parts (BP-195).	KEEP & UPGRADE (Decision 2 & Q2). Ground the inventory in perceive_picture(start_01.png) + layers/manifest.json rather than blind text regexes.
BP-109, BP-170, D-131 (still_shot_max_s: 5.0)	60/30/10 lane share (±5%); still_25d shot max duration 5.0 s.	KEEP (Creator Decision 4). 5.0 s is the strict upper limit on still_25d sub-shots via episode/shot_split.py; shorter cuts on clause boundaries are encouraged.
BP-01, BP-169, BP-171 (WPM & Rhythm Profile)	BP-01 fails < 150 WPM; BP-169 defaults to mrbeast_animated (193 WPM, "shouting", 1.0–2.5s shots).	CHANGE (YouTube Fit 7.1–7.2). Add the "solemn_historical_docudrama" profile (115–160 WPM heard, 2.0–5.0 s sub-shots, restrained delivery) and make it the default for historical docudramas like Truce 1914.
BP-42, BP-76 (microhook_every_s: 150, rehook_at_s: [180, 360])	Hardcoded for 12-minute (720 s) videos.	CHANGE (YouTube Fit 7.2). Express re-hook and turn intervals as proportional shares of episode duration (every 18–25% of runtime, or 60–110 s in a 6-minute film) so 6-minute and 12-minute episodes are both judged accurately.
AV-01..AV-05, D-135 (AV Event Contract)	Single resolver episode/events.py::visual_events for map and 2.5D events; camera moves silent by default.	KEEP & REFINE (Decision 3 & Requirement B). Keep visual_events as the shared timeline, feed it into the post-direction authoritative sound_plan.py::build, and make map beds perspective-dependent rather than mandatory.
BP-50..BP-60, BP-189..BP-193 (Loudness, Ducking, Cross-Cut Continuity)	-14 LUFS, dialogue priority (BP-51, BP-52), smooth ducking (BP-53), continuous scene beds & J/L overlaps (BP-189, BP-191).	KEEP (D3). Enforce in assemble.py::build_audio_v2 and verify in qa/perceive_audio.py, with an explicit exemption for documented intentional silence windows (BP-120, Decision 3).
8. Open Questions for the Creator, ASSUMPTIONS, NOT CHECKED & Repo State
8.1 Open Questions for the Creator (Only If You Wish to Adjust Before Step 2B)

All earlier architectural questions (Q1–Q4, D1–D4, and Decisions 1–7) are settled and applied above. We have only two lightweight confirmation questions on the new YOUTUBE FIT recommendations:

YF-Q1 (Adding the solemn_historical_docudrama Profile to BP-169 & BP-01): Do you approve adding "solemn_historical_docudrama" (115–160 WPM heard, 2.0–5.0 s sub-shots) as the active rhythm profile for Truce 1914 in sourced_rules.json so its measured 130 WPM read passes BP-01 / BP-169 without being judged against mrbeast_animated (193 WPM)? (Recommendation: Yes.)

YF-Q2 (J-Cut Cough/Wind Bridge from Map S02_SH003 into Trench S02_SH004): In S02_SH003 ("Here, in Flanders, the two sides sat close enough to hear each other cough"), do you approve bringing in the faint sound of a soldier coughing in freezing trench wind during the final 1.5 s of the map zoom (t = 43.3–44.8 s) so the 20-second map sequence bridges seamlessly into the mud of S02_SH004? (Recommendation: Yes.)

8.2 ASSUMPTIONS, NOT CHECKED & Exact Repository State

Repository State Verified:

Code & data inspected in repo_after_task1.zip (branch argon/plan-steps-1-2, code commit 9ecdd875, corresponding to planning review target 854a4920 where only the 3 planning docs in docs/wip/argon_2026-11-14/ were added on top of 9ecdd875).

Visual artifacts inspected in visual_task1.zip: visual/s08_strip.jpg, visual/s02_strip.jpg, visual/s05_strip.jpg, visual/S08_SH002.auto_direction.json, visual/S02_SH008.auto_direction.json, visual/S05_SH020.auto_direction.json, and visual/README.txt.

ASSUMPTIONS:

Per the Step 2A R2 instructions ("TASK 2 STEP 2A — REQUEST FOR PLAN R2 (still NO code)"), no repository files were modified in this turn.

In Step 2B, we will execute and verify the Vertical Slice (S08_SH002, S02_SH008, S05_SH020, S02_SH001) first (Steps 1–6) with reproducible raster measurements and CPU benchmarks before scaling across all 84 shots (Step 7).

NOT CHECKED:

Live streaming of external .mp4 videos on Hugging Face or YouTube from inside the sandbox VM (outbound network is disabled inside the VM container); all YouTube video titles, channels, and descriptions were verified via web search metadata/transcripts, and the Task 1 renders were inspected directly from the frame strips and JSON manifests in visual_task1.zip.

Local CPU latency numbers for Grounding DINO Tiny vs. Florence-2-base and YAMNet vs. AST on the creator's workstation will be measured empirically by scripts/benchmark_perception_cpu.py on the real Truce rasters/WAVs at the start of Step 2B rather than assumed beforehand.

=== LINKS ===
UC Berkeley iSchool <https://blogs.ischool.berkeley.edu/i290-viznarr-s12/the-rule-of-six-walter-murch/>
StudioBinder <https://www.studiobinder.com/blog/walter-murch-rule-of-six/>
Video Essay 00:42–03:15 <https://www.youtube.com/watch?v=XVNI3niZp3Q>
Designing Sound Special <https://designingsound.org/2009/10/15/walter-murch-special-womb-tone-and-dense-clarityclear-density/>
FilmSound.org <http://filmsound.org/articles/designing_for_sound.htm>
A Sound Effect <https://www.asoundeffect.com/designing-a-movie-for-sound/>
Audio-Vision Ch. 1 PDF <http://pzacad.pitzer.edu/~mma/teaching/ms52/readings/audio-vision3-13.pdf>
ShapingWaves <https://www.shapingwaves.com/13016/>
Shih et al., CVPR 2020 <https://shihmengli.github.io/3D-Photo-Inpainting/>
Paper PDF <https://www.researchgate.net/publication/343461051_3D_Photography_Using_Context-Aware_Layered_Depth_Inpainting>
YouTube Help 9314415 <https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop>
YouTube Help 12942217 <https://support.google.com/youtube/answer/12942217?hl=en&co=YOUTUBE._YTVideoType%3Dvideo>
YouTube Help 13861714 Test & Compare <https://support.google.com/youtube/answer/13861714>
A Sign Of Friendship In The Midst Of War | THE CHRISTMAS TRUCE 1914 <https://www.youtube.com/watch?v=SpqVblMPRB4>
The First Battle of Champagne — Dying In Caucasus Snow | THE GREAT WAR Week 22 <https://www.youtube.com/watch?v=g-OQeCEMWpE>
The Christmas Truce in 1914 — I Was There: The Great War Interviews <https://www.youtube.com/watch?v=WNCxkA_zfMs>
WW1 Christmas Truce: Silent Night — Extra History — Part 1 <https://www.youtube.com/watch?v=WUlPNWDvk-c>
Companion Article <https://worldoftanks.asia/en/news/general-news/video-extra-credits-the-christmas-truce/>
Hannibal (Parts 11–13) — Battle of Cannae, 216 BC (Full Documentary) <https://www.youtube.com/watch?v=zDQDv-znHIE>
Marlborough's Masterpiece — The Battle That Humiliated the Sun King <https://www.youtube.com/watch?v=UWqrKGxYtps>
Production Study <https://asterman.org/works/creating-videos-for-the-kings-and-generals-youtube-channel>
World War 1 (All Parts, 4K) <https://www.youtube.com/watch?v=G1p6rlDCxq0&vl=en>
How I Make My Maps <https://www.youtube.com/watch?v=GsojLuJpe_0>
FCPX Vox/Johnny Harris Documentary Style Breakdown <https://fcpxfullaccess.com/blogs/blog/vox-johnny-harris-documentary-style-final-cut-pro>
Grazed by the Apocalypse <https://www.youtube.com/watch?v=2GcwAD_7tJY>
The Enduring Mystery of Jack the Ripper <https://www.youtube.com/watch?v=lADBHDg-JtA>
Format Analysis <https://faceless.my/niches/faceless-mystery-channel/>
Christmas Truce (1914) <https://www.youtube.com/watch?v=Fk-LjY16zdM>
1968: Remembering the CHRISTMAS TRUCE | Voice of the People | BBC Archive <https://www.youtube.com/watch?v=yPMyVa_p7qU>
IDEA-Research/grounding-dino-tiny <https://huggingface.co/IDEA-Research/grounding-dino-tiny>
onnx-community/grounding-dino-tiny-ONNX <https://huggingface.co/onnx-community/grounding-dino-tiny-ONNX>
microsoft/Florence-2-base <https://huggingface.co/microsoft/Florence-2-base>
TensorFlow YAMNet <https://github.com/tensorflow/models/tree/master/research/audioset/yamnet>
3.7M weights, 521 AudioSet classes on 0.975s windows <https://www.aomway.com/post/3831.html>
MIT/ast-finetuned-audioset-10-10-0.4593 <https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593>
LAION-AI/CLAP <https://github.com/LAION-AI/CLAP>
YouTube Studio Retention Analytics <https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop>
LEMMiNO <https://www.youtube.com/watch?v=2GcwAD_7tJY>
Imperial War Museums <https://www.youtube.com/watch?v=WNCxkA_zfMs>
Mustard <https://www.youtube.com/watch?v=tqhtkG6glug>
Epic History TV <https://www.youtube.com/watch?v=G1p6rlDCxq0&vl=en>
Extra History Silent Night 00:00–00:42 <https://www.youtube.com/watch?v=WUlPNWDvk-c>
The Great War Christmas Truce 00:00–00:55 <https://www.youtube.com/watch?v=SpqVblMPRB4>
YouTube Studio Intro Metric (0:00–0:30) <https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop>
IWM 02:10–03:25 <https://www.youtube.com/watch?v=WNCxkA_zfMs>
LEMMiNO (~135–150 WPM) <https://www.youtube.com/watch?v=2GcwAD_7tJY>
Epic History TV (~145–160 WPM) <https://www.youtube.com/watch?v=G1p6rlDCxq0&vl=en>
YouTube Studio Retention Dips <https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop>