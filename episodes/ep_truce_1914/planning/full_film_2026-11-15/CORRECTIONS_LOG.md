# Truce 1914 full film — corrections log (2026-11-15)

Rule (ვანო 2026-11-15 16:46 UTC): every correction is written down with its story moment, prompt, photo, result, what was wrong and what changed.

Part A lists the specific defects and their fixes. Part B lists every shot's director brief before and after the rewrite (all 84). Pipeline code was not changed (the Argon loop owns it); code causes are in docs/wip/argon_2026-11-14/INCIDENT_JOURNAL_argon_loop.md.

## A. Specific corrections

### S06_SH008
- **Story moment:** The line of the film: But not today — "Maybe. But not today."
- **Prompt (as rendered):** Thomas says 'Maybe', pauses, then turns and says the rest, holding Friedrich's look.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S06_SH008_start_fix2.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH008_seed7303.mp4
- **What was wrong:** LTX clip says 'Maybe' twice (Whisper: 'Maybe.' 0.0-0.6 s, 'Maybe.' 1.72-1.92 s, 'But not today.' 2.9-3.54 s); the key line of the film is spoiled
- **What changed:** clip starts at 1.45 s (edit_points.json)

### S03_SH007
- **Story moment:** Thomas does not answer: the silence is the answer (VL-08 reaction) — "(Thomas does not answer; he looks at the candles)"
- **Prompt (as rendered):** Thomas stays still and breathes out; his breath clouds in the cold.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e9df2d1b39748533c7a03595.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH007_seed7105.mp4
- **What was wrong:** silent beat, but the clip noise transcribes as 'Oh my God'; a white fog bloom grows over the candles from ~2 s
- **What changed:** clip audio muted, out at 3.75 s (1.9 s if the bloom is visible on the eye check)

### S03_SH003
- **Story moment:** The song begins: men in the enemy trench sing, the turn of the night — "Stille Nacht, heilige Nacht..."
- **Prompt (as rendered):** The soldiers sing together softly, swaying slightly, breath rising in the candlelight.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S03_SH003_start_fix2.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/dd951163fc4b_fc6ae61bf410/S03_SH003/S03_SH003_seed7200.mp4
- **What was wrong:** the old assembly cut cut the last word 'Nacht' (journal 183)
- **What changed:** play the raw clip to its end, 4.71 s

### S04_SH014
- **Story moment:** The handshake: the centre of the film in one gesture — "(they shake hands)"
- **Prompt (as rendered):** They step together and shake hands firmly, both smiling.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S04_SH014_start_n1.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH014_seed7105.mp4
- **What was wrong:** silent beat 'they shake hands': at the end of the clip they let go and step apart
- **What changed:** out at 2.6 s, ends on the clasp

### S07_SH005
- **Story moment:** The signal: a British captain fires three shots into the air, raises a flag and salutes the German line (after Capt. Stockwell, Houplines, 26 December 1914) — "At Houplines, on Boxing Day morning, a British captain ended it politely: shots into the air."
- **Prompt (as rendered):** A slow push toward the captain as he fires three shots into the air; the brazier flickers and its steam and the muzzle smoke drift.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/064e7631e9b16acc8c24f40f.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S07_SH005_seed7111.mp4
- **What was wrong:** the two revolver bangs (0.5 s, 1.6 s of the clip) come long before the narrator says 'shots into the air'
- **What changed:** 1.0 s J-cut: the narration starts under the end of S07_SH004; narrator ducks 4 dB under each bang

### S07_SH006
- **Story moment:** The answer: the German captain salutes back and gets down into his trench, then fires two shots into the air — "(the German captain salutes back, gets down into his trench, then fires two shots into the air)"
- **Prompt (as rendered):** The captain salutes, steps down out of sight behind the parapet, then his arm rises above it and fires a pistol twice into the air.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/ab948b9d23ecd7a1affa1b5c.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH006_seed7104.mp4
- **What was wrong:** the script says two shots; the clip has one (7.9 s)
- **What changed:** second bang reused from S07_SH005 at 7.0 s, -4 dB, panned right

### S08_SH003
- **Story moment:** Pull up and away: two trench lines, a narrow strip between, and the years still to come — "The war went on for almost four more years."
- **Prompt (as rendered):** The camera rises slowly and the lines grow small.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/ae380e00e9c9f5cf5946a1e4.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH003.mp4
- **What was wrong:** 'The war went on for almost four more years' over a picture of men still fraternising in the field
- **What changed:** picture replaced by S01_SH001_start (the empty field of the opening, a bookend); picture_overrides.json

### S02_SH008
- **Story moment:** Raise the stakes from above: the people in charge said no; the men were never asked — "In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed. Nobody asked the men in the trenches."
- **Prompt (as rendered):** A slow push toward Thomas's face as the narrator says nobody asked the men.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/fb9c67af38a3f9aea8dba213.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/2p5d_after_s6_fixes/S02_SH008_new.mp4
- **What was wrong:** 2.5D slice render: steam and breath decided but invisible; boots and brazier legs cut at the end of the push (V4, V5)
- **What changed:** brief: steam strength 1.6, visible breath, keep boots (bottom edge >= .97); renderer defect logged

### S05_SH020
- **Story moment:** The joint service: one psalm in two languages — "At one burial, a Scottish chaplain read the Twenty-Third Psalm. A German student read it after him, in German."
- **Prompt (as rendered):** A slow push toward the chaplain and the young German.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/0961d9551910c9b0cd967e5e.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/after_s10/S05_SH020_new.mp4
- **What was wrong:** 2.5D slice render: pan to the German group imperceptible; breath invisible (V6)
- **What changed:** brief: pan must move >= 12 % of the frame width on 'German'; visible breath

### S08_SH002
- **Story moment:** Friedrich with the portrait card and the brass button: the other side of the same night — "Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale."
- **Prompt (as rendered):** A slow push toward the button and the portrait card.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/89645231dc29774437adbc26.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH002.mp4
- **What was wrong:** 2.5D slice render: 'pretty, cute snow' (creator), snow on frame 0, snow over the hands and photo (V1-V3)
- **What changed:** brief: snow only behind in the open trench, wind-driven, depth layers, candle bends in the draft, frame 0 = picture

### S02_SH009
- **Story moment:** Christmas Eve arrives as parcels: British soldiers open Princess Mary's brass tins (bodies at work, narrated) — "At Christmas, parcels came up the line. British soldiers opened brass tins from Princess Mary: cigarettes, tobacco, a Christmas card."
- **Prompt (as rendered):** A slow push toward the men as the narrator names the tins.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/ceec8c01a785c839081978bc.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH009.mp4
- **What was wrong:** old 2.5D render: grey blurred blobs in the sky band
- **What changed:** brief: no sky effects, a tin glint on 'brass'

### S05_SH003
- **Story moment:** The trading, wide: what men did with one free day — "They traded cigarettes, food, buttons. In a few places, accounts describe men kicking a ball around."
- **Prompt (as rendered):** A slow lateral drift across the groups.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/9a45b4c1a2ea6f25ccf7f783.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH003.mp4
- **What was wrong:** old 2.5D render: grey blurred blobs at the top
- **What changed:** brief: no sky mist, pushes to the trade then to the football on the words

### S06_SH005
- **Story moment:** Thomas's reaction: he looks at the 'enemy' beside him (VL-08) — "(Thomas looks at Friedrich)"
- **Prompt (as rendered):** The shadows lengthen very slowly.
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/fdfc498552fff49255c364e1.png
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S06_SH005.mp4
- **What was wrong:** old 2.5D render: grey blur patch at the top centre
- **What changed:** brief: no sky mist; smoke and lamps live

### S05_SH001
- **Story moment:** Show the truce was not one field but patches along the British line in Flanders — "Along the British line in Flanders, it spread from trench to trench, in patches."
- **Prompt (as rendered):** Patches pulse along the line one after another.
- **Photo:** (map, no photo)
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S05_SH001_new.mp4
- **What was wrong:** map label 'La Bassee' lost its accent
- **What changed:** episode.json name 'La Bassée'

### S05_SH002
- **Story moment:** How many men: the estimate on the map, the number tied to its claim — "Nobody counted them. The usual estimate is that about a hundred thousand men took part."
- **Prompt (as rendered):** The counter rises over the glowing line.
- **Photo:** (map, no photo)
- **Result (current clip):** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S05_SH002_new.mp4
- **What was wrong:** map label 'La Bassee' lost its accent
- **What changed:** episode.json name 'La Bassée'

## B. Director brief rewrites (all 84 shots)

"Before" is the brief on argon/plan-steps-1-2 @ 09232ca (about 80 were template output). "After" is PR #193.

### S01_SH001 · still_25d
- **Story moment:** Open on the empty frozen field at dawn so the first second says place, cold and danger — "Christmas morning, 1914."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/1cdedccd304005bdb602b72a.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S01_SH001.mp4
- **Before — mood:** breathless nocturnal dread (S01_SH001) · **focus:** frost_white_barbed_wire_on_wooden_stakes [0.18, 0.2, 0.82, 0.86] · **word:** 1914
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost-white barbed wire on wooden stakes uncropped inside the safe frame.
- **After — mood:** breathless dawn dread; an empty killing ground on Christmas morning · **box:** [0.35, 0.25, 0.65, 0.65] · **word:** 1914
- **After — camera:** slow push in toward the sun gap over the wire (target (.5, .45)), 3.0 s, lands on '1914'; no handheld
- **After — restraint:** Never moves: wire, stakes, sandbags, trees. Cold: breathless still cold: frost haze, spindrift; no falling snow (clear sunrise). Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: open-land wind, low and thin (amb_wind_open_land); single far crow-less silence; one distant muffled rumble at 0.6 s far left (amb_low_rumble, -30 dB) = the war is still there

### S01_SH002 · video
- **Story moment:** Hook: a soldier climbs out of his trench toward the enemy; the image the whole video pays off — "In a few seconds, this man will walk toward the German guns."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w3/cache/7bd3b95964074b9cdee9cb0e.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/35cc6a85cd8e_fc6ae61bf410/S01_SH002/S01_SH002_seed7100.mp4
- **Before — mood:** startled frostbound wonder (S01_SH002) · **focus:** frosted_sandbags_of_the_parapet [0.18, 0.2, 0.82, 0.86] · **word:** this
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frosted sandbags of the parapet uncropped inside the safe frame.
- **After — mood:** hook: the man who will walk · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** this
- **After — camera:** subtle_push_in
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: trench wind; ladder creak and boots on rungs from the clip; brazier crackle right

### S01_SH003 · video
- **Story moment:** Hook: the walk across the open ground, seen from behind; the danger made physical — "Unarmed. Across the ground where men had been dying for a few yards of mud."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e9a173240a9ccdfcc4f83157.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/35cc6a85cd8e_fc6ae61bf410/S01_SH002/S01_SH003_seed7101.mp4
- **Before — mood:** razor-edge sentry vigilance (S01_SH003) · **focus:** a_broken_wire_stake_and_frozen_mud [0.18, 0.2, 0.82, 0.86] · **word:** the
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a broken wire stake and frozen mud uncropped inside the safe frame.
- **After — mood:** the walk, unarmed · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** the
- **After — camera:** taut_stillness
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: open-land wind; footsteps; one far muffled rumble on 'dying' (amb_low_rumble, -30 dB)

### S01_SH004 · still_25d
- **Story moment:** Widen from one man to many so the viewer knows it is history, not one story — "That Christmas, thousands of soldiers on both sides did the same."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/136c47a2d212e626ee7837ca.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S01_SH004.mp4
- **Before — mood:** uncanny acoustic awe (S01_SH004) · **focus:** frozen_tussocks [0.18, 0.2, 0.82, 0.86] · **word:** thousands
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frozen tussocks uncropped inside the safe frame.
- **After — mood:** wonder spreading: many men climbing out · **box:** [0.23, 0.3, 0.53, 0.7] · **word:** both
- **After — camera:** slow lateral pan_crop_2d left->right from the climbing men (.38, .5) to the walking men (.72, .4) on 'both sides'; gentle, 4 % frame width per second
- **After — restraint:** Never moves: wire, farm, sandbags. Cold: frost haze, breath. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: open-land wind; mid-distance footsteps in snow (footstep_snow) panned right as the pan arrives; faint murmur of voices far right (Battle Crowd murmuring, -28 dB, high-cut)

### S01_SH005 · still_25d
- **Story moment:** The promise of the video over its most magical picture: the candle trees in the dark — "This is the day the war stopped, along parts of the Western Front. How it began, with a song. And how it ended."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/8b77b881e734b3d58179831d.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S01_SH005.mp4
- **Before — mood:** haunted historical gravity (S01_SH005) · **focus:** british_sandbags_in_silhouette_frost_on_ [0.18, 0.2, 0.82, 0.86] · **word:** day
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep British sandbags in silhouette, frost on them uncropped inside the safe frame.
- **After — mood:** title promise, night before; solemn and mysterious · **box:** [0.4, 0.3, 0.7, 0.7] · **word:** the
- **After — camera:** slow crane-like push down the trench line toward the lit trees (target (.55, .5)), 9.3 s split by the runner into two parts: part 1 holds wide on 'the day the war stopped', part 2 pushes on 'with a song'
- **After — restraint:** Never moves: trees, trench walls. Cold: night frost, light falling snow (overcast night sky = allowed), blue grade with the warm candle points. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: night wind low; very faint distant men singing far right (no library take: leave silent and let the music carry it); brazier crackle soft centre

### S02_SH001 · map_action
- **Story moment:** August 1914: the war starts as a fast march, the promise of a short war — "The war had begun in August. Everyone said it would be over by Christmas."
- **Photo:** (map)
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S02_SH001_new.mp4
- **Before — mood:** detached strategic hubris (S02_SH001) · **focus:** route_arrow_belgium_to_marne [0.22, 0.2, 0.78, 0.78] · **word:** Christmas
- **Before — restraint:** Tactile map cues only (map_arrive_click on August, map_route_draw across the sweep); camera move is silent_by_design with no mandatory wind bed (Decision 3).
- **After — mood:** history lesson that turns grim · **box:** [0.22, 0.2, 0.78, 0.78] · **word:** Christmas
- **After — camera:** map renderer as S10
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** map sounds as SOUND_EVENTS v2 (pen line, chip tick); no bed

### S02_SH002 · map_action
- **Story moment:** December: the march has frozen into one trench line from the sea to Switzerland — "By December it had dug itself into the ground: one line of trenches, from the North Sea to Switzerland."
- **Photo:** (map)
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S02_SH002_new.mp4
- **Before — mood:** relentless geographic encirclement (S02_SH002) · **focus:** the_map_s_frame [0.18, 0.2, 0.82, 0.86] · **word:** dug
- **Before — restraint:** Tactile map cues synced to action keyframes only; camera move is silent_by_design with no mandatory geography wind bed (Decision 3); scene-matched plate grade for S02.
- **After — mood:** the war digs in · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** dug
- **After — camera:** map renderer as S10
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** map: pen line + soft dig thud when the line settles; no bed

### S02_SH003 · map_action
- **Story moment:** Fly to Flanders: the sector of our story, where the lines nearly touch — "Here, in Flanders, the two sides sat close enough to hear each other cough."
- **Photo:** (map)
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S02_SH003_new.mp4
- **Before — mood:** descending operational claustrophobia (S02_SH003) · **focus:** frelinghien_sector_highlight [0.35, 0.35, 0.65, 0.65] · **word:** cough
- **Before — restraint:** Front-line stand and fly_to zoom stay silent under narration; only the highlight click on close and the J-cut cough/wind bridge over the last 1.5 s speak (YF-Q2).
- **After — mood:** zoom into Flanders, closeness · **box:** [0.35, 0.35, 0.65, 0.65] · **word:** cough
- **After — camera:** map zoom as S10
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** map: one human cough (cough__v1) on the word 'cough', far left, low; no bed

### S02_SH004 · still_25d
- **Story moment:** Make the cold and the danger physical before we meet the hero — "Mud to the knee. Water in every boot. A sniper waiting for one careless head."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/6b51ff920adfc201e0136cf9.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH004.mp4
- **Before — mood:** bone-deep freezing misery (S02_SH004) · **focus:** huddled_soldiers_fire_step [0.22, 0.28, 0.76, 0.86] · **word:** head
- **Before — restraint:** Slow drift and faint water shimmer only; the trench wind bed completing the J-cut from S02_SH003 carries the space without melodramatic gunfire.
- **After — mood:** MISERY: mud, water, fear of the sniper · **box:** [0.47, 0.55, 0.77, 0.95] · **word:** Water
- **After — camera:** hold 1.5 s, then slow push in toward the hunched man and the water (target (.62, .75)) on 'Water in every boot'; on 'sniper' a slight tilt up to the parapet wire (.75, .15), no snap
- **After — restraint:** Never moves: men, brazier cage, ladder, sandbags. Cold: wet cold: breath, wind-bent smoke; no falling snow. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: trench wind + dripping water; brazier crackle centre-right; squelch of a boot in mud on 'Mud' (footstep_dirt, slowed); distant single rifle crack far right on 'sniper' (NOT IN LIBRARY: leave silent, see library gaps)

### S02_SH005 · still_25d
- **Story moment:** Plant the letter motif: the line from home the story will answer at the end — "Private Thomas Hale had read the same line every night for a week."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/2bbae2bafe8a0b07d0bb1825.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH005.mp4
- **Before — mood:** predatory loophole tension (S02_SH005) · **focus:** two_cold_fingers_holding_the_paper [0.18, 0.2, 0.82, 0.86] · **word:** Hale
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep two cold fingers holding the paper uncropped inside the safe frame.
- **After — mood:** private longing; the letter · **box:** [0.33, 0.2, 0.63, 0.6] · **word:** Hale
- **After — camera:** very slow push into the letter (target (.48, .4)), keep both hands in frame; no move on frame 0
- **After — restraint:** Never moves: hands, letter body. Cold: breath of the reader rises into frame bottom once (from below the frame, POV). Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: trench wind low; paper rustle (paper_move) on 'read'; brazier crackle close bottom-centre

### S02_SH006 · video
- **Story moment:** Meet Thomas: one wry line shows who he is without the narrator telling us — "Home by Christmas, she says. Didn't say which one."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/17d614227c2f28788e9600fe.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/752d93fd5ca1_fc6ae61bf410/S02_SH006/S02_SH006_seed7100.mp4
- **Before — mood:** hollowed-out survivor grief (S02_SH006) · **focus:** the_brazier_s_glow_at_frame_edge [0.18, 0.2, 0.82, 0.86] · **word:** she
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the brazier's glow at frame edge uncropped inside the safe frame.
- **After — mood:** wry, sad · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** she
- **After — camera:** reverent_lateral_creep
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; bed trench wind; brazier crackle

### S02_SH007 · video
- **Story moment:** Harris answers: his whole philosophy in one line, and the rule Thomas will break — "Keep your head down, and you might see one."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/ac7c952748cd4b48030b5e81.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/752d93fd5ca1_fc6ae61bf410/S02_SH006/S02_SH007_seed7101.mp4
- **Before — mood:** bitter domestic irony (S02_SH007) · **focus:** the_brazier [0.18, 0.2, 0.82, 0.86] · **word:** head
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the brazier uncropped inside the safe frame.
- **After — mood:** grim humour · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** head
- **After — camera:** intimate_tabletop_drift
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; bed

### S02_SH008 · still_25d
- **Story moment:** Raise the stakes from above: the people in charge said no; the men were never asked — "In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed. Nobody asked the men in the trenches."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/fb9c67af38a3f9aea8dba213.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/2p5d_after_s6_fixes/S02_SH008_new.mp4
- **Before — mood:** forsaken front-line isolation (S02_SH008) · **focus:** thomas [0.06, 0.22, 0.42, 0.94] · **word:** Nobody
- **Before — restraint:** Keep brazier flame isolated to the grate core, star twinkle strictly in sky_mask * (1 - fg_union), and subtle steam rising from Thomas's mug; never crop Harris or the brazier.
- **After — mood:** forsaken; dry bitterness turning personal · **box:** [0.06, 0.22, 0.42, 0.94] · **word:** Nobody
- **After — camera:** as the hand-made direction: hold on the official story, push to Thomas on 'Nobody'; FIX V5: the end of the push must keep the brazier legs and both men's boots (bottom edge at y >= .97 of the picture)
- **After — restraint:** Never moves: men, brazier cage. Cold: dusk frost, breath. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: trench wind; brazier crackle centre; the narrator alone on 'Nobody asked the men' (bed dips 3 dB under that sentence)

### S02_SH009 · still_25d
- **Story moment:** Christmas Eve arrives as parcels: British soldiers open Princess Mary's brass tins (bodies at work, narrated) — "At Christmas, parcels came up the line. British soldiers opened brass tins from Princess Mary: cigarettes, tobacco, a Christmas card."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/ceec8c01a785c839081978bc.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH009.mp4
- **Before — mood:** fragile epistolary intimacy (S02_SH009) · **focus:** a_sandbag_with_frost [0.18, 0.2, 0.82, 0.86] · **word:** came
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a sandbag with frost uncropped inside the safe frame.
- **After — mood:** small comfort: parcels · **box:** [0.3, 0.42, 0.6, 0.82] · **word:** brass
- **After — camera:** part 1: slow push toward the brass tin of the centre man (.45, .62) on 'brass tins'; part 2 (runner split): gentle pan to the right man's tin (.75, .67) on 'a Christmas card'
- **After — restraint:** Never moves: men, tins. Cold: breath; NO sky effects (the sky is a thin strip, no mist blobs: the old render had grey blur blobs at the top = defect). Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: trench wind low, murmur of men; tin lid click (buckle_click, low) on 'opened'; paper rustle on 'card'

### S03_SH001 · video
- **Story moment:** Cross the wire to the other side: Friedrich lights a candle on the tree, the enemy shown as a man — "On the German side, little Christmas trees had come up the line. As night fell, they went up on the parapets, candles and all."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/99f8c4769cbc757f217bcba3.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH001_seed7100.mp4
- **Before — mood:** quiet Saxon homesickness (S03_SH001) · **focus:** timber_revetment_with_frost [0.18, 0.2, 0.82, 0.86] · **word:** side
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep timber revetment with frost uncropped inside the safe frame.
- **After — mood:** quiet homesickness, the enemy as a man · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** side
- **After — camera:** locked_watchful
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: night wind; candle flicker silent; soft cloth rustle from the clip

### S03_SH002 · still_25d
- **Story moment:** Plant the portrait card: who Friedrich is fighting for — "Gefreiter Friedrich Brandt had carried this photograph since August."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/1ce703b5e381affc86aaa892.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S03_SH002.mp4
- **Before — mood:** brittle pre-dawn frost (S03_SH002) · **focus:** a_woollen_glove [0.18, 0.2, 0.82, 0.86] · **word:** Brandt
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a woollen glove uncropped inside the safe frame.
- **After — mood:** tender: the photograph · **box:** [0.57, 0.22, 0.87, 0.62] · **word:** photograph
- **After — camera:** slow push into the photograph (target (.72, .42)) landing on 'photograph'
- **After — restraint:** Never moves: hand, photo, candle body. Cold: night blue grade, breath not visible (no face). Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: night wind very low; candle silent; far German voices murmur (-30 dB) from the right = the trench beyond

### S03_SH003 · video
- **Story moment:** The song begins: men in the enemy trench sing, the turn of the night — "Stille Nacht, heilige Nacht..."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S03_SH003_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/dd951163fc4b_fc6ae61bf410/S03_SH003/S03_SH003_seed7200.mp4
- **Before — mood:** curious logistical surprise (S03_SH003) · **focus:** the_dark_edge_of_the_trench_wall [0.18, 0.2, 0.82, 0.86] · **word:** heilige
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the dark edge of the trench wall uncropped inside the safe frame.
- **After — mood:** carol: Stille Nacht · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** heilige
- **After — camera:** taut_stillness
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; no bed under the singing except a breath of wind

### S03_SH004 · video
- **Story moment:** The British hear it: Harris's question opens the scene's argument — "What are they singing?"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/9c5546268537f154272d13be.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH004_seed7102.mp4
- **Before — mood:** tender candlelight reverence (S03_SH004) · **focus:** frosted_sandbags [0.18, 0.2, 0.82, 0.86] · **word:** they
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frosted sandbags uncropped inside the safe frame.
- **After — mood:** curious · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** they
- **After — camera:** slow_drift_across
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; the German singing continues far away under it (reuse S03_SH003 clip audio, -18 dB, high-cut, panned right)

### S03_SH005 · video
- **Story moment:** Thomas recognises the tune: the first bridge between the trenches — "Silent Night. Same tune as ours."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/30944f63efba78420f46b07c.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/4e31028adebf_fc6ae61bf410/S03_SH005/S03_SH005_seed7103.mp4
- **Before — mood:** hushed sacred anticipation (S03_SH005) · **focus:** harris_s_shoulder_out_of_focus_at_frame_ [0.18, 0.2, 0.82, 0.86] · **word:** Same
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Harris's shoulder out of focus at frame left uncropped inside the safe frame.
- **After — mood:** recognition · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Same
- **After — camera:** measured_pull_back
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; far singing continues (-20 dB)

### S03_SH006 · video
- **Story moment:** Harris repeats his rule (heads down): the obstacle Thomas is about to defy — "Let 'em sing. Heads down."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/4da9a0b8a639c9bd818a97f1.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/4e31028adebf_fc6ae61bf410/S03_SH005/S03_SH006_seed7104.mp4
- **Before — mood:** disarmed sentry alertness (S03_SH006) · **focus:** thomas_s_shoulder_out_of_focus_at_frame_ [0.18, 0.2, 0.82, 0.86] · **word:** sing
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's shoulder out of focus at frame right uncropped inside the safe frame.
- **After — mood:** gruff caution · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** sing
- **After — camera:** measured_map_pan
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; far singing

### S03_SH007 · video
- **Story moment:** Thomas does not answer: the silence is the answer (VL-08 reaction) — "(Thomas does not answer; he looks at the candles)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e9df2d1b39748533c7a03595.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH007_seed7105.mp4
- **Before — mood:** audacious communal answer (S03_SH007) · **focus:** frosted_sandbag [0.18, 0.2, 0.82, 0.86] · **word:** not
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frosted sandbag uncropped inside the safe frame.
- **After — mood:** silent beat: Thomas looks at the candles · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** not
- **After — camera:** steady_creep_north
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** far singing continues (-16 dB, the only sound), candle silent

### S03_SH008 · video
- **Story moment:** Thomas sings back: the answer across no man's land — "Silent night... holy night..."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/aa004b10a4c4740cc8529847.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH008_seed7106.mp4
- **Before — mood:** electric bilingual harmony (S03_SH008) · **focus:** sandbags [0.18, 0.2, 0.82, 0.86] · **word:** holy
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep sandbags uncropped inside the safe frame.
- **After — mood:** Thomas answers with the song · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** holy
- **After — camera:** descending_focus
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; far German singing under it

### S03_SH009 · video
- **Story moment:** The Germans applaud the British carol: the first exchange between the trenches — "Good, English! More!"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/5181df4f6a1a2f87fce4c48a.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH009_seed7107.mp4
- **Before — mood:** exposed unarmed vulnerability (S03_SH009) · **focus:** the_edge_of_the_dugout_entrance [0.18, 0.2, 0.82, 0.86] · **word:** More
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the edge of the dugout entrance uncropped inside the safe frame.
- **After — mood:** delight · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** More
- **After — camera:** heavy_low_angle_hold
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; brazier

### S03_SH010 · still_25d
- **Story moment:** The two trench lines singing at once: the image of the night — "And for the first time in months, the sound crossing no man's land was not gunfire."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/042e791830efe7ef6b667d84.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S03_SH010.mp4
- **Before — mood:** nervous first-contact courage (S03_SH010) · **focus:** the_british_parapet_with_faint_figures_b [0.18, 0.2, 0.82, 0.86] · **word:** the
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the British parapet with faint figures, breat uncropped inside the safe frame.
- **After — mood:** awe: the silence that is not gunfire · **box:** [0.55, 0.2, 0.85, 0.6] · **word:** not
- **After — camera:** slow push across no man's land toward the candle line (target (.7, .4)), arrives on 'not gunfire'
- **After — restraint:** Never moves: trees, wire, stakes. Cold: night frost, light snow, blue grade. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: night wind very low; far voices singing faintly from the right (reuse S03_SH008 clip audio, -24 dB, reverb, panned right); NO rumble

### S04_SH001 · still_25d
- **Story moment:** Time cut to Christmas morning: the field white and silent — "Christmas morning came white and still."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/b681716d06f3cfbf7f1ccacc.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S04_SH001.mp4
- **Before — mood:** breath-held moral reckoning (S04_SH001) · **focus:** frost_on_the_british_sandbags [0.18, 0.2, 0.82, 0.86] · **word:** came
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost on the British sandbags uncropped inside the safe frame.
- **After — mood:** white stillness, held breath · **box:** [0.35, 0.25, 0.65, 0.65] · **word:** came
- **After — camera:** very slow push (target (.5, .45)), 3.0 s
- **After — restraint:** Never moves: wire, farm. Cold: frost haze, no falling snow (clear dawn). Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: almost silent open-land wind, -6 dB lower than S01 (the stillness); one far crow-like silence; nothing else

### S04_SH002 · video
- **Story moment:** A voice from the enemy trench: the invitation — "English! Merry Christmas!"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/e69dee53372e986211c98a4f.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH002_seed7100.mp4
- **Before — mood:** white-knuckle command friction (S04_SH002) · **focus:** frosted_sandbags_of_the_german_parapet [0.18, 0.2, 0.82, 0.86] · **word:** Christmas
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frosted sandbags of the German parapet uncropped inside the safe frame.
- **After — mood:** startling friendliness · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Christmas
- **After — camera:** intimate_tabletop_drift
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; far, from the German side

### S04_SH003 · video
- **Story moment:** Harris forbids it: the obstacle — "It's a trick. Nobody move."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/9c6d322aa73deabfeaad5784.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH003_seed7101.mp4
- **Before — mood:** defiant individual resolve (S04_SH003) · **focus:** sandbags_with_frost [0.18, 0.2, 0.82, 0.86] · **word:** Nobody
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep sandbags with frost uncropped inside the safe frame.
- **After — mood:** suspicion · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Nobody
- **After — camera:** weighty_contemplative_push
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; trench close

### S04_SH004 · video
- **Story moment:** Friedrich climbs out unarmed: the risk is taken by the enemy first — "No shooting! Merry Christmas!"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/758dbead47c7f025c1d2124a.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH004_seed7102.mp4
- **Before — mood:** reluctant officer complicity (S04_SH004) · **focus:** frosted_wire_stakes [0.18, 0.2, 0.82, 0.86] · **word:** Christmas
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frosted wire stakes uncropped inside the safe frame.
- **After — mood:** arms wide · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Christmas
- **After — camera:** intimate_over_shoulder
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice far; wind

### S04_SH005 · video
- **Story moment:** Thomas decides: he leaves the rifle and climbs (the hook's first image) — "(Thomas leans his rifle on the sandbags and climbs the ladder)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/089a194403bb504678b96fae.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH005_seed7103.mp4
- **Before — mood:** precarious frozen-ground tension (S04_SH005) · **focus:** frosted_sandbags [0.18, 0.2, 0.82, 0.86] · **word:** his
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frosted sandbags uncropped inside the safe frame.
- **After — mood:** decision: Thomas climbs out · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** his
- **After — camera:** locked_watchful
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip foley; footstep on ladder; bed wind rises as he reaches the top

### S04_SH006 · video
- **Story moment:** Harris tries to stop him — "Thomas! Get back down!"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/0ebbd5b964742af1d27108f0.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH006_seed7104.mp4
- **Before — mood:** symmetrical fog convergence (S04_SH006) · **focus:** the_trench_wall_with_a_shovel_on_it [0.18, 0.2, 0.82, 0.86] · **word:** back
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the trench wall with a shovel on it uncropped inside the safe frame.
- **After — mood:** alarm · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** back
- **After — camera:** subtle_push_in
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S04_SH007 · video
- **Story moment:** Thomas answers from the parapet: his reason, practical, not heroic — "If they wanted us dead, we'd be dead."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/f687326ded501c8e7f9eeaab.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH007_seed7105.mp4
- **Before — mood:** heart-in-throat proximity (S04_SH007) · **focus:** sandbag_edge [0.18, 0.2, 0.82, 0.86] · **word:** dead
- **Before — restraint:** Solemn restraint: keep mourners and crosses whole in frame; zero decorative sparkles or ice glints on graves; subtle breath frost and cold air only.
- **After — mood:** calm certainty · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** dead
- **After — camera:** taut_stillness
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; wind louder (he is on the parapet)

### S04_SH008 · video
- **Story moment:** The walk across: fifty yards of frozen mud, wire and the dead (the hook paid off) — "In places, the lines were only fifty yards apart. Fifty yards of frozen mud, wire, and the men who never made it back."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/1f4b1178ccfce58026247da2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH008_seed7100.mp4
- **Before — mood:** disarming bare-handed recognition (S04_SH008) · **focus:** a_broken_wire_stake_and_frozen_mud [0.18, 0.2, 0.82, 0.86] · **word:** lines
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a broken wire stake and frozen mud uncropped inside the safe frame.
- **After — mood:** the walk across fifty yards · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** lines
- **After — camera:** slow_drift_across
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: open-land wind; footsteps; bed dips on 'the men who never made it back'

### S04_SH009 · video
- **Story moment:** Face to face: the first question — "You are English?"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S04_SH009_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH009_seed7101.mp4
- **Before — mood:** wry working-class warmth (S04_SH009) · **focus:** frost_on_the_ground [0.18, 0.2, 0.82, 0.86] · **word:** English
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost on the ground uncropped inside the safe frame.
- **After — mood:** first words · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** English
- **After — camera:** measured_pull_back
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; wind

### S04_SH010 · video
- **Story moment:** Thomas's answer turns it back on him — "And you're German?"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S04_SH010_start_n1.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH010_seed7102.mp4
- **Before — mood:** bittersweet family kinship (S04_SH010) · **focus:** friedrich_s_grey_shoulder_out_of_focus_a [0.18, 0.2, 0.82, 0.86] · **word:** German
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's grey shoulder out of focus at fra uncropped inside the safe frame.
- **After — mood:** a smile · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** German
- **After — camera:** measured_map_pan
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S04_SH011 · still_25d
- **Story moment:** Insert: two pairs of empty hands, held a little out; nobody is armed (VL-08 breath) — "(their empty hands)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/6abdb2918f268ec74e346250.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S04_SH011.mp4
- **Before — mood:** spontaneous sector-wide release (S04_SH011) · **focus:** frozen_tussocks [0.18, 0.2, 0.82, 0.86] · **word:** hands
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frozen tussocks uncropped inside the safe frame.
- **After — mood:** silent beat: empty hands, trust · **box:** [0.35, 0.3, 0.65, 0.7] · **word:** hands
- **After — camera:** slow push to the gap between the hands (target (.5, .5)), 3.5 s; nothing else moves in the hands
- **After — restraint:** Never moves: ALL FOUR HANDS and the sleeves (never animate a hand). Cold: breath, frost. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** silence of the field: wind very low; one cloth rustle (cloth_move) as the push lands

### S04_SH012 · video
- **Story moment:** Friedrich: Saxon, and 'Tommy', the joke the name will turn — "Saxon. Fritz, to my friends. Merry Christmas, Tommy."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S04_SH012_start_n1.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH012_seed7103.mp4
- **Before — mood:** sober documentary breadth (S04_SH012) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** friends
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** warm introduction · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** friends
- **After — camera:** descending_focus
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S04_SH013 · video
- **Story moment:** Thomas laughs: Tommy, the nickname for every British soldier, really is his name — "We're all Tommies to you. It's really my name."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S04_SH013_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH013_seed7104.mp4
- **Before — mood:** stark sector-to-sector contrast (S04_SH013) · **focus:** friedrich_s_offered_hand_at_frame_right [0.18, 0.2, 0.82, 0.86] · **word:** Tommies
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's offered hand at frame right uncropped inside the safe frame.
- **After — mood:** joke, warmth · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Tommies
- **After — camera:** heavy_low_angle_hold
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S04_SH014 · video
- **Story moment:** The handshake: the centre of the film in one gesture — "(they shake hands)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S04_SH014_start_n1.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH014_seed7105.mp4
- **Before — mood:** unflinching historical candor (S04_SH014) · **focus:** frost_on_the_ground [0.18, 0.2, 0.82, 0.86] · **word:** hands
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost on the ground uncropped inside the safe frame.
- **After — mood:** the handshake · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** hands
- **After — camera:** claustrophobic_lock
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** glove clasp (cloth_move) on the clasp; wind

### S04_SH015 · video
- **Story moment:** Others follow along the line: bodies climbing and walking, the truce spreading — "Up and down this part of the line, the same thing was happening. Nobody had ordered it."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/5eb300f0c039c4bd10c802e2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH015_seed7106.mp4
- **Before — mood:** unbuttoned ration-sharing warmth (S04_SH015) · **focus:** frozen_tussocks [0.18, 0.2, 0.82, 0.86] · **word:** this
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frozen tussocks uncropped inside the safe frame.
- **After — mood:** it spreads · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** this
- **After — camera:** reverent_lateral_creep
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: open land; murmur of many men rising (Battle Crowd murmuring, -24 dB, high-cut so it is friendly not battle)

### S05_SH001 · map_action
- **Story moment:** Show the truce was not one field but patches along the British line in Flanders — "Along the British line in Flanders, it spread from trench to trench, in patches."
- **Photo:** (map)
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S05_SH001_new.mp4
- **Before — mood:** playful tunic-button camaraderie (S05_SH001) · **focus:** the_map_s_frame [0.18, 0.2, 0.82, 0.86] · **word:** British
- **Before — restraint:** Tactile map cues synced to action keyframes only; camera move is silent_by_design with no mandatory geography wind bed (Decision 3); scene-matched plate grade for S05.
- **After — mood:** spreading · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** British
- **After — camera:** map renderer as S10
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** map: soft tick per ripple; no bed

### S05_SH002 · map_action
- **Story moment:** How many men: the estimate on the map, the number tied to its claim — "Nobody counted them. The usual estimate is that about a hundred thousand men took part."
- **Photo:** (map)
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S05_SH002_new.mp4
- **Before — mood:** surreal frozen-pitch joy (S05_SH002) · **focus:** the_map_s_frame [0.18, 0.2, 0.82, 0.86] · **word:** them
- **Before — restraint:** Tactile map cues synced to action keyframes only; camera move is silent_by_design with no mandatory geography wind bed (Decision 3); scene-matched plate grade for S05.
- **After — mood:** scale · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** them
- **After — camera:** as S10
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** map: counter ticks + soft knock when the number lands (BP-192)

### S05_SH003 · still_25d
- **Story moment:** The trading, wide: what men did with one free day — "They traded cigarettes, food, buttons. In a few places, accounts describe men kicking a ball around."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/9a45b4c1a2ea6f25ccf7f783.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH003.mp4
- **Before — mood:** lighthearted scoreline banter (S05_SH003) · **focus:** two_soldiers_exchanging_a_tin_and_a_ciga [0.18, 0.2, 0.82, 0.86] · **word:** cigarettes
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep two soldiers exchanging a tin and a cigarette uncropped inside the safe frame.
- **After — mood:** joy: trading and football · **box:** [0.4, 0.35, 0.7, 0.75] · **word:** buttons
- **After — camera:** part 1: slow push toward the hand-to-hand trade in the middle (.55, .55) on 'buttons'; part 2: tilt/push up to the football players (.47, .38) on 'kicking a ball around'
- **After — restraint:** Never moves: men, wire. Cold: breath, frost; no falling snow (clear). Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: open land; friendly murmur and one warm laugh (laugh_warm, mid-left); far shouts of the football game panned to the ball (Battle Crowd murmuring, -26 dB)

### S05_SH004 · video
- **Story moment:** Thomas asks how the enemy speaks his language — "Where'd you learn English?"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/1be456d64b6827f0cf9889ef.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH004_seed7100.mp4
- **Before — mood:** abrupt mortal chill (S05_SH004) · **focus:** friedrich_s_grey_shoulder_out_of_focus_a [0.18, 0.2, 0.82, 0.86] · **word:** learn
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's grey shoulder out of focus at fra uncropped inside the safe frame.
- **After — mood:** curiosity · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** learn
- **After — camera:** locked_watchful
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; murmur bed

### S05_SH005 · video
- **Story moment:** Friedrich: London, a waiter, four years; why so many Germans spoke English — "London. I was a waiter. Four years."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH005_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH005_seed7101.mp4
- **Before — mood:** shared graveside duty (S05_SH005) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** waiter
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** London memory · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** waiter
- **After — camera:** subtle_push_in
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S05_SH006 · video
- **Story moment:** A detail only a truce could make: a Briton sits down for a haircut from his pre-war German barber — "Many Germans had worked in Britain before the war. One Briton found his old barber among them, and sat down for a haircut."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/4027aba2635cd8e7e7071f05.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH006_seed7102.mp4
- **Before — mood:** back-breaking frozen-earth labor (S05_SH006) · **focus:** frozen_mud_and_a_scatter_of_cut_hair [0.18, 0.2, 0.82, 0.86] · **word:** had
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frozen mud and a scatter of cut hair uncropped inside the safe frame.
- **After — mood:** human comedy: the barber · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** had
- **After — camera:** taut_stillness
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** murmur bed; scissors not in library

### S05_SH007 · video
- **Story moment:** Friedrich asks the first real question — "You have a family?"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH007_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH007_seed7103.mp4
- **Before — mood:** wordless fraternal care (S05_SH007) · **focus:** frost [0.18, 0.2, 0.82, 0.86] · **word:** family
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost uncropped inside the safe frame.
- **After — mood:** gentle question · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** family
- **After — camera:** slow_drift_across
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S05_SH008 · video
- **Story moment:** Thomas: mother and sister, the people waiting at home — "My mum. And a little sister."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH008_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S05_SH008_seed7300.mp4
- **Before — mood:** intimate identity-disc sorrow (S05_SH008) · **focus:** friedrich_s_grey_shoulder_out_of_focus_a [0.18, 0.2, 0.82, 0.86] · **word:** little
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's grey shoulder out of focus at fra uncropped inside the safe frame.
- **After — mood:** family · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** little
- **After — camera:** measured_pull_back
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S05_SH009 · video
- **Story moment:** Friedrich shows the portrait card: his wife and daughter — "My wife. My daughter. She is three."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed/S05_SH009_start_n1_card.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH009_seed7105.mp4
- **Before — mood:** austere rifle-cross unity (S05_SH009) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** She
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** his daughter · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** She
- **After — camera:** measured_map_pan
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S05_SH010 · still_25d
- **Story moment:** The portrait card in Thomas's hands: the insert that lets the line land (VL-08) — "(Thomas looks at the photograph)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH010_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH010.mp4
- **Before — mood:** dignified officer salute (S05_SH010) · **focus:** a_khaki_sleeve_and_a_grey_sleeve [0.18, 0.2, 0.82, 0.86] · **word:** the
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a khaki sleeve and a grey sleeve uncropped inside the safe frame.
- **After — mood:** silent beat: the photograph passes · **box:** [0.33, 0.3, 0.63, 0.7] · **word:** the
- **After — camera:** slow push into the photograph (target (.48, .5)), 3.4 s
- **After — restraint:** Never moves: ALL hands and the photograph. Cold: breath, frost on the gloves. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** near silence: wind low; paper touch (paper_move, very soft) at 0.3 s

### S05_SH011 · video
- **Story moment:** Thomas: the kindness that costs him — "She looks happy."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S05_SH011_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S05_SH011_seed7302.mp4
- **Before — mood:** piercing childhood recognition (S05_SH011) · **focus:** friedrich_s_grey_shoulder_out_of_focus_a [0.18, 0.2, 0.82, 0.86] · **word:** happy
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's grey shoulder out of focus at fra uncropped inside the safe frame.
- **After — mood:** kind · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** happy
- **After — camera:** descending_focus
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S05_SH012 · video
- **Story moment:** Friedrich: the wish both men share, said as a fact — "She thinks I am home for Christmas."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S05_SH012_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH012_seed7107.mp4
- **Before — mood:** silent survivor solidarity (S05_SH012) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** home
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** ache · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** home
- **After — camera:** heavy_low_angle_hold
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S05_SH013 · video
- **Story moment:** Thomas: the echo of the letter — "So does mine."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH013_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S05_SH013_seed7301.mp4
- **Before — mood:** gentle graveside inquiry (S05_SH013) · **focus:** frost [0.18, 0.2, 0.82, 0.86] · **word:** mine
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost uncropped inside the safe frame.
- **After — mood:** shared ache · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** mine
- **After — camera:** claustrophobic_lock
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; murmur bed fades out under 'So does mine'

### S05_SH014 · video
- **Story moment:** The turn of the day: both sides bring in their dead — "But the day was not only for trading. Both sides went out to bring in their dead."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/57a4ea9bd4270fd9064a409d.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH014_seed7100.mp4
- **Before — mood:** hushed heartbroken stillness (S05_SH014) · **focus:** a_stretcher_handle_and_frozen_mud [0.18, 0.2, 0.82, 0.86] · **word:** day
- **Before — restraint:** Solemn restraint: keep mourners and crosses whole in frame; zero decorative sparkles or ice glints on graves; subtle breath frost and cold air only.
- **After — mood:** SOLEMN turn: bringing in the dead · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** day
- **After — camera:** reverent_lateral_creep
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed changes: murmur gone, cold wind only; slow footsteps in snow; restraint

### S05_SH015 · video
- **Story moment:** Thomas and Friedrich dig side by side: enemies doing the same work — "Some had lain out there for weeks."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e2490163ec3a5422222edeca.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH015_seed7101.mp4
- **Before — mood:** bareheaded liturgical preparation (S05_SH015) · **focus:** a_heap_of_frozen_earth [0.18, 0.2, 0.82, 0.86] · **word:** lain
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a heap of frozen earth uncropped inside the safe frame.
- **After — mood:** grief · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** lain
- **After — camera:** intimate_tabletop_drift
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** wind; spade scrape from the clip

### S05_SH016 · still_25d
- **Story moment:** Insert: two spades in the frozen earth by the open grave; the work done together (VL-08 breath) — "(two spades stand in the earth by the grave)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/45bb0e8ecc8c760ab0be75af.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH016.mp4
- **Before — mood:** solemn bilingual Psalm reverence (S05_SH016) · **focus:** frozen_clods [0.18, 0.2, 0.82, 0.86] · **word:** stand
- **Before — restraint:** Solemn restraint: keep mourners and crosses whole in frame; zero decorative sparkles or ice glints on graves; subtle breath frost and cold air only.
- **After — mood:** silent beat: two spades by the grave · **box:** [0.3, 0.25, 0.6, 0.65] · **word:** stand
- **After — camera:** slow push to the space between the two spades (target (.45, .45)), 3.5 s
- **After — restraint:** Never moves: spades, blanket, mound. Cold: spindrift, frost, cold grade. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** wind alone, slightly stronger gust at 1.5 s; nothing else (restraint)

### S05_SH017 · video
- **Story moment:** Thomas asks the name: the dead get a person — "What was his name?"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e3fa664985bac13da28cd720.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH017_seed7102.mp4
- **Before — mood:** cold bureaucratic wrath (S05_SH017) · **focus:** the_mound_of_earth [0.18, 0.2, 0.82, 0.86] · **word:** his
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the mound of earth uncropped inside the safe frame.
- **After — mood:** respect · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** his
- **After — camera:** intimate_over_shoulder
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; wind

### S05_SH018 · video
- **Story moment:** Friedrich: one name, Karl — "Karl. He sang the loudest."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH018_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cde4357602e2_fc6ae61bf410/S05_SH018/S05_SH018_seed7400.mp4
- **Before — mood:** institutional command panic (S05_SH018) · **focus:** the_mound_of_earth [0.18, 0.2, 0.82, 0.86] · **word:** the
- **Before — restraint:** Deliberately still and hushed: drop music and distant battle rumble so Friedrich's words ('Karl. He sang the loudest.') stand over bare winter wind before the burial Psalm.
- **After — mood:** grief · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** the
- **After — camera:** locked_watchful
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; wind

### S05_SH019 · video
- **Story moment:** Thomas: the apology no army could give — "I'm sorry."
- **Photo:** None
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH019_seed7104.mp4
- **Before — mood:** implacable court-martial decree (S05_SH019) · **focus:** the_mound [0.18, 0.2, 0.82, 0.86] · **word:** sorry
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep the mound uncropped inside the safe frame.
- **After — mood:** apology · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** sorry
- **After — camera:** subtle_push_in
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; wind

### S05_SH020 · still_25d
- **Story moment:** The joint service: one psalm in two languages — "At one burial, a Scottish chaplain read the Twenty-Third Psalm. A German student read it after him, in German."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/0961d9551910c9b0cd967e5e.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/after_s10/S05_SH020_new.mp4
- **Before — mood:** heavy front-line compliance (S05_SH020) · **focus:** left_group [0.04, 0.18, 0.48, 0.86] · **word:** German
- **Before — restraint:** Solemn stillness: gentle low-amber sun shafts, faint breath frost, and quiet wind; skip ice sparkle on the frozen earth so the burial remains reverent.
- **After — mood:** solemn, restrained: the joint burial · **box:** [0.15, 0.35, 0.45, 0.75] · **word:** German
- **After — camera:** hold on the whole burial during 'a Scottish chaplain read the Twenty-Third Psalm', then a VISIBLE but gentle pan_crop_2d from the Scottish group (.3, .55) to the German group (.7, .55) on 'German' (FIX V6: the move must shift the framing at least 12 % of the frame width)
- **After — restraint:** Never moves: every man, crosses. Cold: breath, frost; no falling snow. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: wind very low; no music swell; a single soft bell-less silence; the narrator carries it

### S05_SH021 · video
- **Story moment:** Harris comes out last and takes off his cap: the hard man changes — "(Harris takes off his cap at the edge of the graves)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/c030b4def7eef27edcc0292d.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH021_seed7105.mp4
- **Before — mood:** urgent twilight warning (S05_SH021) · **focus:** wire_stake [0.18, 0.2, 0.82, 0.86] · **word:** off
- **Before — restraint:** Solemn restraint: keep mourners and crosses whole in frame; zero decorative sparkles or ice glints on graves; subtle breath frost and cold air only.
- **After — mood:** silent beat: Harris takes off his cap · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** off
- **After — camera:** slow_drift_across
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** wind; cloth rustle when the cap comes off

### S06_SH001 · still_25d
- **Story moment:** Time cut to dusk: two men sitting in the open where nobody could sit yesterday — "By late afternoon, the light was going."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/0beb5fddd6f4426807a55589.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/2p5d_after_s6_fixes/S06_SH001_new.mp4
- **Before — mood:** protective fraternal candor (S06_SH001) · **focus:** wire_stakes_black_against_the_sky [0.18, 0.2, 0.82, 0.86] · **word:** the
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep wire stakes black against the sky uncropped inside the safe frame.
- **After — mood:** the light going · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** the
- **After — camera:** as the hand-made direction (slow push on the two men), 3.0 s
- **After — restraint:** Never moves: men, crates. Cold: breath, dusk frost. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: dusk wind low; brazier crackle right

### S06_SH002 · video
- **Story moment:** Friedrich asks the question of the film — "Tommy... why are we fighting?"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S06_SH002_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH002_seed7100.mp4
- **Before — mood:** reciprocal dawn warning (S06_SH002) · **focus:** frost_on_the_box [0.18, 0.2, 0.82, 0.86] · **word:** are
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost on the box uncropped inside the safe frame.
- **After — mood:** the question · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** are
- **After — camera:** measured_map_pan
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; brazier

### S06_SH003 · video
- **Story moment:** Thomas has no answer — "I don't know."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S06_SH003_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH003_seed7304.mp4
- **Before — mood:** tactile parting keepsake (S06_SH003) · **focus:** friedrich_s_grey_shoulder_out_of_focus_a [0.18, 0.2, 0.82, 0.86] · **word:** know
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's grey shoulder out of focus at fra uncropped inside the safe frame.
- **After — mood:** honest · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** know
- **After — camera:** steady_creep_north
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S06_SH004 · video
- **Story moment:** Friedrich: what they were told — "They told us you were the enemy."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/fc29ca07f635138501dffed1.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH004_seed7102.mp4
- **Before — mood:** reluctant backward separation (S06_SH004) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** you
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** bitter truth · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** you
- **After — camera:** descending_focus
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S06_SH005 · still_25d
- **Story moment:** Thomas's reaction: he looks at the 'enemy' beside him (VL-08) — "(Thomas looks at Friedrich)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/fdfc498552fff49255c364e1.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S06_SH005.mp4
- **Before — mood:** leaden artillery resumption (S06_SH005) · **focus:** frozen_ground [0.18, 0.2, 0.82, 0.86] · **word:** Friedrich
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frozen ground uncropped inside the safe frame.
- **After — mood:** silent beat: two shadows side by side · **box:** [0.35, 0.2, 0.65, 0.6] · **word:** Friedrich
- **After — camera:** very slow push along the shadows toward the sun (target (.5, .4)), 2.0 s
- **After — restraint:** Never moves: shadows (they belong to still men), wire. Cold: frost, spindrift. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** wind low; brazier crackle off-screen behind camera (centre, close)

### S06_SH006 · video
- **Story moment:** Thomas: the same lie on both sides — "They told us the same about you."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/d1484fa3a280046b2ea5de16.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH006_seed7306.mp4
- **Before — mood:** deliberate high-aimed defiance (S06_SH006) · **focus:** friedrich_s_grey_shoulder_out_of_focus_a [0.18, 0.2, 0.82, 0.86] · **word:** the
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's grey shoulder out of focus at fra uncropped inside the safe frame.
- **After — mood:** mirror · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** the
- **After — camera:** claustrophobic_lock
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S06_SH007 · video
- **Story moment:** Friedrich names tomorrow — "Tomorrow, maybe, we are enemies again."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S06_SH007_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH007_seed7104.mp4
- **Before — mood:** bleak regiment rotation (S06_SH007) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** are
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** fatal maybe · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** are
- **After — camera:** reverent_lateral_creep
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S06_SH008 · video
- **Story moment:** The line of the film: But not today — "Maybe. But not today."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S06_SH008_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH008_seed7303.mp4
- **Before — mood:** clinical war-diary censorship (S06_SH008) · **focus:** frost_on_the_box [0.18, 0.2, 0.82, 0.86] · **word:** not
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost on the box uncropped inside the safe frame.
- **After — mood:** THE line: 'Maybe. But not today.' · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** not
- **After — camera:** intimate_tabletop_drift
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; brazier; nothing else

### S06_SH009 · video
- **Story moment:** The button: Thomas cuts it off his own uniform, a small act against the army (silent insert) — "(Thomas cuts a brass button off his tunic with a penknife)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/459180abd24b5054b68873f1.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S06_SH009_seed7110.mp4
- **Before — mood:** hearthside epistolary truth (S06_SH009) · **focus:** a_penknife_blade [0.18, 0.2, 0.82, 0.86] · **word:** brass
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a penknife blade uncropped inside the safe frame.
- **After — mood:** silent beat: the button · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** brass
- **After — camera:** weighty_contemplative_push
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** small cloth snip; wind low

### S06_SH010 · video
- **Story moment:** The gift and its words: Thomas holds out the button; Friedrich gives one of his own back — "Something to remember me by."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S06_SH010_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH010_seed7305.mp4
- **Before — mood:** shocked newsprint revelation (S06_SH010) · **focus:** frost_on_the_box [0.18, 0.2, 0.82, 0.86] · **word:** remember
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frost on the box uncropped inside the safe frame.
- **After — mood:** gift · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** remember
- **After — camera:** intimate_over_shoulder
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S06_SH011 · video
- **Story moment:** Friedrich gives one of his own: the exchange is equal — "Then take one of mine."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S06_SH011_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH011_seed7108.mp4
- **Before — mood:** tender kitchen-table memory (S06_SH011) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** one
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** gift returned · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** one
- **After — camera:** locked_watchful
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice

### S06_SH012 · still_25d
- **Story moment:** The narrator closes the scene: the day ends and neither wants to go (BP-90) — "The sun went down on Christmas Day. Neither of them moved to leave."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/d6dd993ef61f64d9b6129ebc.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S06_SH012.mp4
- **Before — mood:** continental archival reach (S06_SH012) · **focus:** black_wire_stakes [0.18, 0.2, 0.82, 0.86] · **word:** went
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep black wire stakes uncropped inside the safe frame.
- **After — mood:** the sun goes down; they stay · **box:** [0.35, 0.3, 0.65, 0.7] · **word:** went
- **After — camera:** slow pull back (reverse push) from the two men (.5, .5) to the wide, 5.5 s (runner split: hold then pull), the men stay centred
- **After — restraint:** Never moves: the two men. Cold: dusk cold grade, frost. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: dusk wind, brazier crackle left; everything thins as the light goes

### S07_SH001 · still_25d
- **Story moment:** Time cut to the next morning: everyone walks back — "The next morning, the men drifted back to their own trenches."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/82ece8ecbcfa5da9123fe8cd.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S07_SH001.mp4
- **Before — mood:** balanced dual-diary testimony (S07_SH001) · **focus:** fog_over_frozen_mud [0.18, 0.2, 0.82, 0.86] · **word:** morning
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep fog over frozen mud uncropped inside the safe frame.
- **After — mood:** drifting back, melancholy · **box:** [0.35, 0.15, 0.65, 0.55] · **word:** morning
- **After — camera:** slow push down the field (target (.5, .35)), 4.25 s
- **After — restraint:** Never moves: men, wire. Cold: frost haze, no falling snow. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: morning wind; many slow footsteps in snow (footstep_snow, layered, panned both ways)

### S07_SH002 · video
- **Story moment:** Friedrich's farewell — "Good luck, Tommy."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S07_SH002_start_mirror.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH002_seed7100.mp4
- **Before — mood:** guarded tunic-pocket memory (S07_SH002) · **focus:** thomas_s_khaki_shoulder_out_of_focus_at_ [0.18, 0.2, 0.82, 0.86] · **word:** Tommy
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Thomas's khaki shoulder out of focus at frame uncropped inside the safe frame.
- **After — mood:** farewell offered: Friedrich wishes him luck · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Tommy
- **After — camera:** slow_drift_across
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; wind

### S07_SH003 · video
- **Story moment:** Thomas's farewell: Fritz, the nickname for every German, said as a friend's name — "You too, Fritz."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S07_SH003_start_fix2.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH003_seed7101.mp4
- **Before — mood:** gathering spring-offensive dread (S07_SH003) · **focus:** friedrich_s_grey_shoulder_out_of_focus_a [0.18, 0.2, 0.82, 0.86] · **word:** Fritz
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep Friedrich's grey shoulder out of focus at fra uncropped inside the safe frame.
- **After — mood:** farewell returned; Thomas turns back to his line · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Fritz
- **After — camera:** measured_pull_back
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; footsteps

### S07_SH004 · video
- **Story moment:** Harris gives the order: the war's voice is back — "Stand to."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/060bfd79498d4a66871d9528.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH004_seed7102.mp4
- **Before — mood:** exhausted January dispersal (S07_SH004) · **focus:** sandbags [0.18, 0.2, 0.82, 0.86] · **word:** Stand
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep sandbags uncropped inside the safe frame.
- **After — mood:** back to war · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Stand
- **After — camera:** measured_map_pan
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** clip voice; trench wind

### S07_SH005 · video
- **Story moment:** The signal: a British captain fires three shots into the air, raises a flag and salutes the German line (after Capt. Stockwell, Houplines, 26 December 1914) — "At Houplines, on Boxing Day morning, a British captain ended it politely: shots into the air."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/064e7631e9b16acc8c24f40f.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S07_SH005_seed7111.mp4
- **Before — mood:** grim institutional suppression (S07_SH005) · **focus:** sandbags [0.18, 0.2, 0.82, 0.86] · **word:** Day
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep sandbags uncropped inside the safe frame.
- **After — mood:** polite end: two shots into the air, salute · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** Day
- **After — camera:** steady_creep_north
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** gunshots from the clip, echo across no man's land (reverb tail 1.2 s); bed trench wind

### S07_SH006 · video
- **Story moment:** The answer: the German captain salutes back and gets down into his trench, then fires two shots into the air — "(the German captain salutes back, gets down into his trench, then fires two shots into the air)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/ab948b9d23ecd7a1affa1b5c.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH006_seed7104.mp4
- **Before — mood:** crushing four-year devastation (S07_SH006) · **focus:** frosted_wire_stakes [0.18, 0.2, 0.82, 0.86] · **word:** captain
- **Before — restraint:** Honour the physical cold and suffering of Saxon front-line trench opposite the British line: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep frosted wire stakes uncropped inside the safe frame.
- **After — mood:** the German answer · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** captain
- **After — camera:** descending_focus
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** two far shots from the German trench (right), long echo; wind

### S07_SH007 · video
- **Story moment:** Thomas at the sound, rifle in hand: the face that knows — "(Thomas looks up at the shots)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/button_fix/S07_SH007_start.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH007_seed7105.mp4
- **Before — mood:** enduring lifetime grace (S07_SH007) · **focus:** sandbags [0.18, 0.2, 0.82, 0.86] · **word:** the
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep sandbags uncropped inside the safe frame.
- **After — mood:** Thomas hears it end · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** the
- **After — camera:** heavy_low_angle_hold
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** the echo of the second shot dies over this shot; wind

### S07_SH008 · video
- **Story moment:** Thomas takes up his rifle again — "There had been no treaty. In some places the truce lasted hours. In others, it held until the New Year."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/button_fix/S07_SH008_start.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S07_SH008_seed7112.mp4
- **Before — mood:** quiet memorial resonance (S07_SH008) · **focus:** sandbags [0.18, 0.2, 0.82, 0.86] · **word:** been
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep sandbags uncropped inside the safe frame.
- **After — mood:** history's verdict, war resumes · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** been
- **After — camera:** claustrophobic_lock
- **After — restraint:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** trench wind; one distant rumble at the end (amb_low_rumble, far, -28 dB) = the guns are back

### S08_SH001 · still_25d
- **Story moment:** The letter answered: Thomas writes home with the German button on the paper — "Thomas wrote home that night. So did many others. In January, British newspapers printed their letters."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/03bcf8817982220b0b2b0ef6.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH001.mp4
- **Before — mood:** final historical stillness (S08_SH001) · **focus:** a_candle_stub [0.18, 0.2, 0.82, 0.86] · **word:** home
- **Before — restraint:** Honour the physical cold and suffering of British front-line breastwork trench opposite Frelinghien: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep a candle stub uncropped inside the safe frame.
- **After — mood:** writing home, intimate · **box:** [0.37, 0.42, 0.67, 0.82] · **word:** printed
- **After — camera:** slow push to the writing hand and the button (target (.52, .62)), 7.8 s (runner split: part 2 settles on the button on 'printed their letters')
- **After — restraint:** Never moves: the writing hand (do not animate the pencil), candle body. Cold: warm interior vs blue cold outside. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: night wind outside, muffled (low-pass) because we are inside; pencil scratching (pencil_scribble, close, centre); candle silent

### S08_SH002 · still_25d
- **Story moment:** Friedrich with the portrait card and the brass button: the other side of the same night — "Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/89645231dc29774437adbc26.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH002.mp4
- **Before — mood:** sacred archival witness (S08_SH002) · **focus:** button [0.43, 0.56, 0.54, 0.67] · **word:** prevent
- **Before — restraint:** Isolate candle deformation strictly to the flame wick tip on the right crate so the tin holder and wooden crate never warp; skip dust motes to keep focus on the portrait and button.
- **After — mood:** the commanders forbid it; the keepsake · **box:** [0.43, 0.56, 0.54, 0.67] · **word:** prevent
- **After — camera:** as the hand-made direction (push lands on the button on 'prevent'), 8.75 s split by the runner
- **After — restraint:** Never moves: hands, photo, button, candle body. Cold: draft-bent candle, blue grade in the shadows against the small warm light. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: night wind with gusts that match the candle bending; a soft metallic touch when the button is first seen (coin-like, not in library: leave silent)

### S08_SH003 · still_25d
- **Story moment:** Pull up and away: two trench lines, a narrow strip between, and the years still to come — "The war went on for almost four more years."
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/ae380e00e9c9f5cf5946a1e4.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH003.mp4
- **Before — mood:** unforgotten human spark (S08_SH003) · **focus:** snow [0.18, 0.2, 0.82, 0.86] · **word:** went
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep snow uncropped inside the safe frame.
- **After — mood:** the war goes on (no comfort) · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** went
- **After — camera:** slow pull back (the field recedes), 3.6 s
- **After — restraint:** Never moves: wire, stakes. Cold: cold, empty. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** bed: open-land wind; two distant artillery rumbles far left and far right (amb_low_rumble, -26 dB, 1.2 s apart)

### S08_SH004 · still_25d
- **Story moment:** The last line on black — "(on screen: For one day, they remembered they were human.)"
- **Photo:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S08_SH004_start_candle.png
- **Result before:** https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH004.mp4
- **Before — mood:** timeless elegiac hush (S08_SH004) · **focus:** one_small_candle_in_a_tin_holder_low_rig [0.18, 0.2, 0.82, 0.86] · **word:** one
- **Before — restraint:** Honour the physical cold and suffering of No man's land between the lines: isolate any flame strictly to its emitter core, mask sky effects to open sky only, and keep one small candle in a tin holder, low right uncropped inside the safe frame.
- **After — mood:** end card: memory · **box:** [0.18, 0.2, 0.82, 0.86] · **word:** one
- **After — camera:** locked (no push), 5.9 s
- **After — restraint:** Never moves: candle body. Cold: none. Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **After — sound:** silence except a very low wind; the candle is silent; music (if any) resolves here
