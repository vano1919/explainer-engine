# Truce 1914 — full film, shot-by-shot plan (2026-11-15)

Every shot was looked at (photo + clip start/middle/end) and every LTX clip was transcribed. Time = the measured narration clock (24 fps). Coordinates are picture fractions (x, y).

## Rules for the whole film

- **Cold:** Cold is felt through breath, wind and grade, not decorative snow. Falling snow only where the sky is overcast or night (S01_SH005, S03_SH010, S08_SH001-003): wind-driven diagonal, 3 depth layers (far: tiny, slow, sharp, 60 % of flakes; mid; near: large, soft, motion-blurred, fast, rare), gusts every 3-5 s, never a crisp dot on a face, hand, photo or letter, alpha 0 on frame 0 and fades in over 0.5 s. Clear golden dawn/dusk shots get NO falling snow: ground spindrift (low blowing snow at the ground, bottom 25 % only), drifting frost haze, smoke bent by the wind, breath on every visible face.
- **Breath:** Breath on every visible face in an exterior or open-trench shot: a puff every 2.8-3.6 s (desynchronised per person), rising 0.6-0.8 s, peak opacity 0.30-0.40, clearly visible on a phone screen; never on a face seen from behind, never inside a dugout with a fire close by.
- **Motion:** Only the element moves, never its support: flame not candle/brazier, steam not mug, smoke not chimney, cloth edge not pole.
- **Voice:** Narrator: the ElevenLabs reads of 2026-11-13 (Odom, 33 lines, text identical to the current script, measured clock in demo_truce_1914/clock). Dialogue: the LTX clips' own voices (the creator's choice of 11-13), every line checked by Whisper on 11-15; fixes: S06_SH008 start at 1.45 s (double 'Maybe'), S03_SH003 play to its end (cut word), S03_SH007 muted (false words in noise). ElevenLabs character reads stay as the fallback for any clip whose voice fails the ear check. No paid voice step.
- **Clip sound:** Video shots with a line: the clip's own audio is the dialogue. Narrated or silent video shots: the clip's own sound at -12 dB (switch Q2, creator 11-13) ducked under the narrator, except where the shot says otherwise.
- **Sound staging:** Every spot sound is panned to its source's x in the picture (pan = 2x-1) and set by distance (close 0 dB, mid -6, far -12); during a push its level rises up to +3 dB as the camera closes; beds change with the place (open field: wind; trench: wind low + crackle; dugout: wind low-passed). The old one-bed-everywhere (fire + calm wind) is replaced.
- **Library gaps:** Not in the free library: rifle crack (S02_SH004 sniper), scissors (S05_SH006), coin/button touch (S08_SH002), distant real artillery (amb_low_rumble stands in). Plan: leave those silent (no paid step); the gunshots of S07 come from the LTX clips. Optional later: ElevenLabs SFX ~4 takes, about 0.10 USD, only on the creator's word.

### Music

- S01: mus_echoes_of_time__v1 (mysterious), low, enters at 0.5 s
- S02: mus_dark_times__v1 (dark), low under narration; out at the dip to black
- S03: NO score: the carol is the music (Stille Nacht / Silent Night from the clips, carried far under S03_SH004-SH010)
- S04: mus_lord_of_the_land__v1 (tense, very low) from S04_SH002 to S04_SH011; it resolves to silence on the empty hands; no score under the handshake
- S05a: S05_SH003-SH013: mus_village_consort__v1 (peaceful/joyful), low; fades out under 'So does mine'
- S05b: S05_SH014-SH021: NO score (restraint at the burial); wind only
- S06: mus_despair_and_triumph__v1 (reflective), very low, from S06_SH001; out on the dip to black
- S07: S07_SH001-SH004 none (footsteps, farewells); after the shots: mus_dark_times__v1 low from S07_SH007
- S08: mus_ancient_rite__v1 (reflective), low; resolves on the end card

### Renderer defects to log (incident journal)

- V1-V3 snow look / frame 0 / snow over subject (S08_SH002)
- V4 decided steam/breath invisible (S02_SH008, S05_SH020, S06_SH001)
- V5 boots cut at the end of a push (S02_SH008)
- V6 pan imperceptible (S05_SH020)
- grey blur blobs in the sky band from mist/cloud effects without a sky mask (S02_SH009, S05_SH003, S06_SH005, S08_SH003 old renders)
- LTX S03_SH007 white bloom (bad take)
- S08_SH003 picture contradicts its line (data)

## S01

### S01_SH001 · still_25d · 0.0 s (+3.0 s) · breathless dawn dread; an empty killing ground on Christmas morning
- *narrator:* "Christmas morning, 1914."
- **Picture:** empty frozen no man's land at sunrise: wire on X-stakes across the middle (y .45-.65), shell hole bottom-left (.1-.3, .7-.8), sandbagged parapets both sides, fir trees on the far German parapet (.05-.3, .2-.35 and .85-.95, .2-.35), small lamps on the far parapets, sun at (.5, .27) in fog
- **Camera:** slow push in toward the sun gap over the wire (target (.5, .45)), 3.0 s, lands on '1914'; no handheld
- **Living:** ground fog drifting left->right across y .35-.6 (strength 1.3, visible movement); sun shafts in the fog; far parapet lamps flicker; ground spindrift at the bottom 20 %
- **Cold:** breathless still cold: frost haze, spindrift; no falling snow (clear sunrise)
- **Never moves:** wire, stakes, sandbags, trees
- **Keep in frame:** the shell hole and both parapets
- **Sound:** bed: open-land wind, low and thin (amb_wind_open_land); single far crow-less silence; one distant muffled rumble at 0.6 s far left (amb_low_rumble, -30 dB) = the war is still there
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/1cdedccd304005bdb602b72a.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S01_SH001.mp4

### S01_SH002 · video · 3.0 s (+4.9167 s) · hook: the man who will walk
- *narrator:* "In a few seconds, this man will walk toward the German guns."
- LTX clip heard: "You"
- **Clip:** LTX narrated (Thomas leans on the ladder, then climbs out): clip own sound -12 dB, use 0.0-4.9 s (slot), the climb starts inside the slot
- **Sound:** bed: trench wind; ladder creak and boots on rungs from the clip; brazier crackle right
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w3/cache/7bd3b95964074b9cdee9cb0e.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/35cc6a85cd8e_fc6ae61bf410/S01_SH002/S01_SH002_seed7100.mp4

### S01_SH003 · video · 7.92 s (+6.625 s) · the walk, unarmed
- *narrator:* "Unarmed. Across the ground where men had been dying for a few yards of mud."
- LTX clip heard: "You"
- **Clip:** LTX narrated (Thomas walks away from camera between the wire): clip own sound -12 dB, footsteps in snow added in sync (footstep_snow, centre, close -> mid), use 0.0-6.6 s
- **Sound:** bed: open-land wind; footsteps; one far muffled rumble on 'dying' (amb_low_rumble, -30 dB)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e9a173240a9ccdfcc4f83157.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/35cc6a85cd8e_fc6ae61bf410/S01_SH002/S01_SH003_seed7101.mp4

### S01_SH004 · still_25d · 14.54 s (+5.125 s) · wonder spreading: many men climbing out
- *narrator:* "That Christmas, thousands of soldiers on both sides did the same."
- **Picture:** ruined farm at (.3, .25), sun (.5, .27); British soldiers climbing out of the trench left-centre (.35-.45, .4-.55), men already walking in the field right (.6-.9, .3-.45), wire foreground, lamps in the trench right
- **Camera:** slow lateral pan_crop_2d left->right from the climbing men (.38, .5) to the walking men (.72, .4) on 'both sides'; gentle, 4 % frame width per second
- **Living:** fog drift; lamps flicker (.52, .52) (.95, .78); breath of the near climbers; spindrift low
- **Cold:** frost haze, breath
- **Never moves:** wire, farm, sandbags
- **Keep in frame:** the climbing men and the walking group
- **Sound:** bed: open-land wind; mid-distance footsteps in snow (footstep_snow) panned right as the pan arrives; faint murmur of voices far right (Battle Crowd murmuring, -28 dB, high-cut)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/136c47a2d212e626ee7837ca.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S01_SH004.mp4

### S01_SH005 · still_25d · 19.67 s (+9.3333 s) · title promise, night before; solemn and mysterious
- *narrator:* "This is the day the war stopped, along parts of the Western Front. How it began, with a song. And how it ended."
- **Picture:** moonlit night, clouds, dead trees on the horizon left; a winding trench with lit Christmas trees on the parapet (.3-.8, .35-.55); men with lamps inside the trench (.48, .65) (.62, .68), braziers (.66, .7)
- **Camera:** slow crane-like push down the trench line toward the lit trees (target (.55, .5)), 9.3 s split by the runner into two parts: part 1 holds wide on 'the day the war stopped', part 2 pushes on 'with a song'
- **Living:** tree candles twinkle (every tree, small radius); braziers flicker; moonlit clouds drift; light wind-driven snow, far layer only, diagonal
- **Cold:** night frost, light falling snow (overcast night sky = allowed), blue grade with the warm candle points
- **Never moves:** trees, trench walls
- **Keep in frame:** the winding trench and the lit trees
- **Sound:** bed: night wind low; very faint distant men singing far right (no library take: leave silent and let the music carry it); brazier crackle soft centre
- **Out:** dip to black 0.5 s into the map chapter (chapter change)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/8b77b881e734b3d58179831d.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S01_SH005.mp4


## S02

### S02_SH001 · map_action · 29.0 s (+5.7083 s) · history lesson that turns grim
- *narrator:* "The war had begun in August. Everyone said it would be over by Christmas."
- **Picture:** S10 map: August 1914 arrow from Aachen through Belgium to the Marne
- **Camera:** map renderer as S10
- **Living:** the arrow draws on 'August'; date chip 'August 1914'
- **Sound:** map sounds as SOUND_EVENTS v2 (pen line, chip tick); no bed
- **Out:** cut
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S02_SH001_new.mp4

### S02_SH002 · map_action · 34.71 s (+7.9583 s) · the war digs in
- *narrator:* "By December it had dug itself into the ground: one line of trenches, from the North Sea to Switzerland."
- **Picture:** S10 map: December 1914, front line Nieuport-Ypres-Verdun-Swiss border
- **Camera:** map renderer as S10
- **Living:** line draws on 'one line of trenches', ends at the Swiss border on 'Switzerland'
- **Sound:** map: pen line + soft dig thud when the line settles; no bed
- **Out:** cut
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S02_SH002_new.mp4

### S02_SH003 · map_action · 42.67 s (+5.5 s) · zoom into Flanders, closeness
- *narrator:* "Here, in Flanders, the two sides sat close enough to hear each other cough."
- **Picture:** S10 map: close Flanders view, dual lines, Frelinghien highlight
- **Camera:** map zoom as S10
- **Living:** highlight on Frelinghien on 'cough'
- **Sound:** map: one human cough (cough__v1) on the word 'cough', far left, low; no bed
- **Out:** cut
- **Journal:** La Bassee label lacks the accent (La Bassée) in S05 maps: data fix in episode.json key_coordinates
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S02_SH003_new.mp4

### S02_SH004 · still_25d · 48.17 s (+7.7917 s) · MISERY: mud, water, fear of the sniper
- *narrator:* "Mud to the knee. Water in every boot. A sniper waiting for one careless head."
- **Picture:** wet trench at dusk: two men standing left-centre (.25-.4, .3-.95), group by the brazier right (.55-.75), a man hunched on a bench right (.85, .65), water on the duckboards, brazier (.62, .73), candle in the dugout (.18, .62)
- **Camera:** hold 1.5 s, then slow push in toward the hunched man and the water (target (.62, .75)) on 'Water in every boot'; on 'sniper' a slight tilt up to the parapet wire (.75, .15), no snap
- **Living:** brazier flame + embers; water reflections ripple on the duckboards (y .8-1.0) (strength 1.4: must be seen); candle flicker; breath on the five faces; smoke from the brazier bent left by wind
- **Cold:** wet cold: breath, wind-bent smoke; no falling snow
- **Never moves:** men, brazier cage, ladder, sandbags
- **Keep in frame:** all five men whole, boots in frame
- **Sound:** bed: trench wind + dripping water; brazier crackle centre-right; squelch of a boot in mud on 'Mud' (footstep_dirt, slowed); distant single rifle crack far right on 'sniper' (NOT IN LIBRARY: leave silent, see library gaps)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/6b51ff920adfc201e0136cf9.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH004.mp4

### S02_SH005 · still_25d · 55.96 s (+5.2917 s) · private longing; the letter
- *narrator:* "Private Thomas Hale had read the same line every night for a week."
- **Picture:** POV: gloved hands hold a worn letter (.3-.65, .1-.75) in front of the brazier (.6, .8); sunset sky top-left, candle in the dugout (.17, .6)
- **Camera:** very slow push into the letter (target (.48, .4)), keep both hands in frame; no move on frame 0
- **Living:** brazier flame + rising embers past the letter's lower edge; candle; a faint tremble of the letter edge from the wind (edge only, the hands do not move)
- **Cold:** breath of the reader rises into frame bottom once (from below the frame, POV)
- **Never moves:** hands, letter body
- **Keep in frame:** both hands and the letter
- **Sound:** bed: trench wind low; paper rustle (paper_move) on 'read'; brazier crackle close bottom-centre
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/2bbae2bafe8a0b07d0bb1825.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH005.mp4

### S02_SH006 · video · 61.25 s (+4.25 s) · wry, sad
- *thomas_hale:* "Home by Christmas, she says. Didn't say which one."
- LTX clip heard: "Home by Christmas, she says. Didn't say which one."
- **Clip:** LTX voice; trim end to 4.5 s (last frame stillest); clip audio is the line
- **Sound:** clip voice; bed trench wind; brazier crackle
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/17d614227c2f28788e9600fe.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/752d93fd5ca1_fc6ae61bf410/S02_SH006/S02_SH006_seed7100.mp4

### S02_SH007 · video · 65.5 s (+4.25 s) · grim humour
- *sgt_harris:* "Keep your head down, and you might see one."
- LTX clip heard: "Keep your head down and you might see one."
- **Clip:** LTX voice, full 4.04 s
- **Sound:** clip voice; bed
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/ac7c952748cd4b48030b5e81.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/752d93fd5ca1_fc6ae61bf410/S02_SH006/S02_SH007_seed7101.mp4

### S02_SH008 · still_25d · 69.75 s (+10.9583 s) · forsaken; dry bitterness turning personal
- *narrator:* "In early December, the Pope asked for a Christmas truce. The appeal failed. No official truce was agreed. Nobody asked the men in the trenches."
- **Picture:** hand-made direction exists (s7_regenerated_directions/S02_SH008.direction.json): Thomas left with mug (.33, .45), Harris right (.69, .45), brazier (.52, .79), candle (.18, .62)
- **Camera:** as the hand-made direction: hold on the official story, push to Thomas on 'Nobody'; FIX V5: the end of the push must keep the brazier legs and both men's boots (bottom edge at y >= .97 of the picture)
- **Living:** brazier, embers, candle, smoke, VISIBLE mug steam (strength 1.6), visible breath both men, first stars
- **Cold:** dusk frost, breath
- **Never moves:** men, brazier cage
- **Keep in frame:** both men whole including boots, the brazier
- **Sound:** bed: trench wind; brazier crackle centre; the narrator alone on 'Nobody asked the men' (bed dips 3 dB under that sentence)
- **Out:** cut
- **Journal:** V4 (steam/breath decided but invisible) and V5 (boots cut at the end of the push) are renderer defects: journal
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/fb9c67af38a3f9aea8dba213.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/2p5d_after_s6_fixes/S02_SH008_new.mp4

### S02_SH009 · still_25d · 80.71 s (+10.4583 s) · small comfort: parcels
- *narrator:* "At Christmas, parcels came up the line. British soldiers opened brass tins from Princess Mary: cigarettes, tobacco, a Christmas card."
- **Picture:** dusk trench: men opening brass Princess Mary tins: two left (.2-.3, .35-.9), one centre seated (.45, .6), one right (.75, .65), group at the back by the brazier (.62, .45), brazier (.62, .72), candle (.17, .62)
- **Camera:** part 1: slow push toward the brass tin of the centre man (.45, .62) on 'brass tins'; part 2 (runner split): gentle pan to the right man's tin (.75, .67) on 'a Christmas card'
- **Living:** brazier flame+embers, candle, breath on visible faces, brass glint on the tins (one soft glint each, on the word 'brass')
- **Cold:** breath; NO sky effects (the sky is a thin strip, no mist blobs: the old render had grey blur blobs at the top = defect)
- **Never moves:** men, tins
- **Keep in frame:** all four front men
- **Sound:** bed: trench wind low, murmur of men; tin lid click (buckle_click, low) on 'opened'; paper rustle on 'card'
- **Out:** dip to black 0.4 s (day -> night, cross to the German side)
- **Journal:** old 2.5D render had blurry grey blobs in the sky band (mist/cloud effect without a sky mask): journal
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/ceec8c01a785c839081978bc.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH009.mp4


## S03

### S03_SH001 · video · 91.17 s (+8.9167 s) · quiet homesickness, the enemy as a man
- *narrator:* "On the German side, little Christmas trees had come up the line. As night fell, they went up on the parapets, candles and all."
- LTX clip heard: "You"
- **Clip:** LTX, narrated; clip own sound at -12 dB under the narrator (Whisper heard a false 'You' = noise, fine); full 9.7 s
- **Sound:** bed: night wind; candle flicker silent; soft cloth rustle from the clip
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/99f8c4769cbc757f217bcba3.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH001_seed7100.mp4

### S03_SH002 · still_25d · 100.08 s (+4.3333 s) · tender: the photograph
- *narrator:* "Gefreiter Friedrich Brandt had carried this photograph since August."
- **Picture:** gloved hand (.68-.9, .4-.85) holds a photograph of a woman (.65-.78, .3-.55); a tall candle left (.25, .5-.75), lantern in the dugout right (.85, .35), brazier (.38, .72) behind
- **Camera:** slow push into the photograph (target (.72, .42)) landing on 'photograph'
- **Living:** candle flame (.25, .5) flicker + warm spill on the photo edge; lantern flicker; brazier glow behind; frost sparkle none
- **Cold:** night blue grade, breath not visible (no face)
- **Never moves:** hand, photo, candle body
- **Keep in frame:** hand and photograph whole
- **Sound:** bed: night wind very low; candle silent; far German voices murmur (-30 dB) from the right = the trench beyond
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/1ce703b5e381affc86aaa892.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S03_SH002.mp4

### S03_SH003 · video · 104.42 s (+4.75 s) · carol: Stille Nacht
- *friedrich_brandt:* "Stille Nacht, heilige Nacht..."
- LTX clip heard: "Stilenacht, Heiligenacht"
- **Clip:** LTX voice (Friedrich sings). FIX: the old cut clipped 'Nacht'; play the raw clip to its natural end 4.71 s, do not trim
- **Sound:** clip voice; no bed under the singing except a breath of wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S03_SH003_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/dd951163fc4b_fc6ae61bf410/S03_SH003/S03_SH003_seed7200.mp4

### S03_SH004 · video · 109.17 s (+2.25 s) · curious
- *sgt_harris:* "What are they singing?"
- LTX clip heard: "What are they singing?"
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice; the German singing continues far away under it (reuse S03_SH003 clip audio, -18 dB, high-cut, panned right)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/9c5546268537f154272d13be.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH004_seed7102.mp4

### S03_SH005 · video · 111.42 s (+3.25 s) · recognition
- *thomas_hale:* "Silent Night. Same tune as ours."
- LTX clip heard: "Silent night, same tune as ours."
- **Clip:** LTX voice, full 4.71 s
- **Sound:** clip voice; far singing continues (-20 dB)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/30944f63efba78420f46b07c.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/4e31028adebf_fc6ae61bf410/S03_SH005/S03_SH005_seed7103.mp4

### S03_SH006 · video · 114.67 s (+2.75 s) · gruff caution
- *sgt_harris:* "Let 'em sing. Heads down."
- LTX clip heard: "Let him sing. Heads down."
- **Clip:** LTX voice ('Let him sing' heard for 'Let 'em sing': accept), full 4.04 s
- **Sound:** clip voice; far singing
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/4da9a0b8a639c9bd818a97f1.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/4e31028adebf_fc6ae61bf410/S03_SH005/S03_SH006_seed7104.mp4

### S03_SH007 · video · 117.42 s (+3.75 s) · silent beat: Thomas looks at the candles
- *none:* "(Thomas does not answer; he looks at the candles)"
- LTX clip heard: "Oh, my God."
- **Clip:** LTX, NO voice: mute the clip audio (Whisper hears 'Oh my God' in its noise); trim to 3.75 s before the white bloom grows (a white glow covers the candles from ~2.0 s = defect: cut out at 1.9 s if visible on the eye check, else hold)
- **Sound:** far singing continues (-16 dB, the only sound), candle silent
- **Out:** cut
- **Journal:** LTX clip S03_SH007 grows a white fog bloom over the candles mid-clip (frame at 2.2 s): bad take
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e9df2d1b39748533c7a03595.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH007_seed7105.mp4

### S03_SH008 · video · 121.17 s (+4.75 s) · Thomas answers with the song
- *thomas_hale:* "Silent night... holy night..."
- LTX clip heard: "Silent night, holy night"
- **Clip:** LTX voice, full 5.04 s (two soldiers walk into the back at the end: acceptable, they come to listen)
- **Sound:** clip voice; far German singing under it
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/aa004b10a4c4740cc8529847.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH008_seed7106.mp4

### S03_SH009 · video · 125.92 s (+2.0 s) · delight
- *friedrich_brandt:* "Good, English! More!"
- LTX clip heard: "Good English! More!"
- **Clip:** LTX voice, full 4.04 s
- **Sound:** clip voice; brazier
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/5181df4f6a1a2f87fce4c48a.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH009_seed7107.mp4

### S03_SH010 · still_25d · 127.92 s (+5.8333 s) · awe: the silence that is not gunfire
- *narrator:* "And for the first time in months, the sound crossing no man's land was not gunfire."
- **Picture:** moonlit no man's land: moon (.5, .08) in cloud, frozen pools, wire, the German parapet far right lined with lit trees and candles (.55-.95, .3-.55), a lit trench right-front with lanterns (.75, .55-.8)
- **Camera:** slow push across no man's land toward the candle line (target (.7, .4)), arrives on 'not gunfire'
- **Living:** tree candles twinkle; lanterns flicker; moonlit clouds drift slowly; moon reflection shimmer in the pools (.45, .6); light falling snow far layer (night, overcast)
- **Cold:** night frost, light snow, blue grade
- **Never moves:** trees, wire, stakes
- **Keep in frame:** the candle line
- **Sound:** bed: night wind very low; far voices singing faintly from the right (reuse S03_SH008 clip audio, -24 dB, reverb, panned right); NO rumble
- **Out:** dip to black 0.6 s (night -> Christmas morning)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/042e791830efe7ef6b667d84.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S03_SH010.mp4


## S04

### S04_SH001 · still_25d · 133.75 s (+3.0833 s) · white stillness, held breath
- *narrator:* "Christmas morning came white and still."
- **Picture:** empty no man's land at sunrise, ruined farm right (.75, .3), wire foreground, trenches either side, fog
- **Camera:** very slow push (target (.5, .45)), 3.0 s
- **Living:** fog drift (visible), spindrift, sun shafts
- **Cold:** frost haze, no falling snow (clear dawn)
- **Never moves:** wire, farm
- **Keep in frame:** both trench lines
- **Sound:** bed: almost silent open-land wind, -6 dB lower than S01 (the stillness); one far crow-like silence; nothing else
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/b681716d06f3cfbf7f1ccacc.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S04_SH001.mp4

### S04_SH002 · video · 136.83 s (+2.0 s) · startling friendliness
- *friedrich_brandt:* "English! Merry Christmas!"
- LTX clip heard: "English! Merry Christmas!"
- **Clip:** LTX voice (raw clip has 'Merry'), full 4.04 s
- **Sound:** clip voice; far, from the German side
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/e69dee53372e986211c98a4f.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH002_seed7100.mp4

### S04_SH003 · video · 138.83 s (+2.75 s) · suspicion
- *sgt_harris:* "It's a trick. Nobody move."
- LTX clip heard: "It's a trick. Nobody move."
- **Clip:** LTX voice, full 4.04 s
- **Sound:** clip voice; trench close
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/9c6d322aa73deabfeaad5784.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH003_seed7101.mp4

### S04_SH004 · video · 141.58 s (+2.25 s) · arms wide
- *friedrich_brandt:* "No shooting! Merry Christmas!"
- LTX clip heard: "No shooting! Merry Christmas!"
- **Clip:** LTX voice, full 4.38 s
- **Sound:** clip voice far; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/758dbead47c7f025c1d2124a.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH004_seed7102.mp4

### S04_SH005 · video · 143.83 s (+5.75 s) · decision: Thomas climbs out
- *none:* "(Thomas leans his rifle on the sandbags and climbs the ladder)"
- LTX clip heard: "(nothing)"
- **Clip:** LTX, no line: clip own sound at -12 dB (rifle lean, ladder creak), full 6.38 s
- **Sound:** clip foley; footstep on ladder; bed wind rises as he reaches the top
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/089a194403bb504678b96fae.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH005_seed7103.mp4

### S04_SH006 · video · 149.58 s (+2.25 s) · alarm
- *sgt_harris:* "Thomas! Get back down!"
- LTX clip heard: "Thomas! Get back down!"
- **Clip:** LTX voice, full 4.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/0ebbd5b964742af1d27108f0.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH006_seed7104.mp4

### S04_SH007 · video · 151.83 s (+4.0 s) · calm certainty
- *thomas_hale:* "If they wanted us dead, we'd be dead."
- LTX clip heard: "If they wanted us dead, we'd be dead."
- **Clip:** LTX voice, full 4.38 s
- **Sound:** clip voice; wind louder (he is on the parapet)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/f687326ded501c8e7f9eeaab.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c77ad9cdd010_fc6ae61bf410/S04_SH002/S04_SH007_seed7105.mp4

### S04_SH008 · video · 155.83 s (+10.0 s) · the walk across fifty yards
- *narrator:* "In places, the lines were only fifty yards apart. Fifty yards of frozen mud, wire, and the men who never made it back."
- LTX clip heard: "(nothing)"
- **Clip:** LTX, narrated: clip own sound -12 dB, footsteps in snow added in sync with Thomas's steps (footstep_snow, centre, close -> mid as he walks away), full 10.04 s
- **Sound:** bed: open-land wind; footsteps; bed dips on 'the men who never made it back'
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/1f4b1178ccfce58026247da2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH008_seed7100.mp4

### S04_SH009 · video · 165.83 s (+2.0 s) · first words
- *friedrich_brandt:* "You are English?"
- LTX clip heard: "You are English?"
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S04_SH009_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH009_seed7101.mp4

### S04_SH010 · video · 167.83 s (+2.0 s) · a smile
- *thomas_hale:* "And you're German?"
- LTX clip heard: "And you're German?"
- **Clip:** LTX voice, full 3.38 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S04_SH010_start_n1.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH010_seed7102.mp4

### S04_SH011 · still_25d · 169.83 s (+3.5417 s) · silent beat: empty hands, trust
- *none:* "(their empty hands)"
- **Picture:** two pairs of hands reaching toward each other over the frozen field (left hands .2-.45, .3-.7; right hands .55-.75, .3-.7), sunrise (.5, .2), willows right
- **Camera:** slow push to the gap between the hands (target (.5, .5)), 3.5 s; nothing else moves in the hands
- **Living:** breath vapour drifting across the gap from both sides (two soft puffs, at 0.8 s and 2.2 s); sun shimmer; spindrift low
- **Cold:** breath, frost
- **Never moves:** ALL FOUR HANDS and the sleeves (never animate a hand)
- **Keep in frame:** all hands
- **Sound:** silence of the field: wind very low; one cloth rustle (cloth_move) as the push lands
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/6abdb2918f268ec74e346250.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S04_SH011.mp4

### S04_SH012 · video · 173.38 s (+4.0 s) · warm introduction
- *friedrich_brandt:* "Saxon. Fritz, to my friends. Merry Christmas, Tommy."
- LTX clip heard: "Saxon. Fritz to my friends. Merry Christmas, Tommy."
- **Clip:** LTX voice, full 6.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S04_SH012_start_n1.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH012_seed7103.mp4

### S04_SH013 · video · 177.38 s (+4.25 s) · joke, warmth
- *thomas_hale:* "We're all Tommies to you. It's really my name."
- LTX clip heard: "We're all Tommies to you. It's really my name."
- **Clip:** LTX voice, full 5.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S04_SH013_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH013_seed7104.mp4

### S04_SH014 · video · 181.62 s (+3.5833 s) · the handshake
- *none:* "(they shake hands)"
- LTX clip heard: "You"
- **Clip:** LTX, no line; trim to 0.0-2.6 s so it ENDS on the clasped hands (the raw clip lets go and steps apart); clip own sound -12 dB
- **Sound:** glove clasp (cloth_move) on the clasp; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S04_SH014_start_n1.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH014_seed7105.mp4

### S04_SH015 · video · 185.21 s (+6.0833 s) · it spreads
- *narrator:* "Up and down this part of the line, the same thing was happening. Nobody had ordered it."
- LTX clip heard: "you"
- **Clip:** LTX narrated, clip own sound -12 dB (crowd murmur), full 7.04 s
- **Sound:** bed: open land; murmur of many men rising (Battle Crowd murmuring, -24 dB, high-cut so it is friendly not battle)
- **Out:** dip to black 0.4 s (chapter: the truce spreads, maps)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/5eb300f0c039c4bd10c802e2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH015_seed7106.mp4


## S05

### S05_SH001 · map_action · 191.29 s (+6.3333 s) · spreading
- *narrator:* "Along the British line in Flanders, it spread from trench to trench, in patches."
- **Picture:** S10 close map: British line in Flanders, ripples at Wulverghem, Ploegsteert, Frelinghien, Fleurbaix
- **Camera:** map renderer as S10
- **Living:** ripples pop one by one on 'trench to trench'
- **Sound:** map: soft tick per ripple; no bed
- **Out:** cut
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S05_SH001_new.mp4

### S05_SH002 · map_action · 197.62 s (+6.7917 s) · scale
- *narrator:* "Nobody counted them. The usual estimate is that about a hundred thousand men took part."
- **Picture:** S10 map: '100,000 men (estimate)' counter
- **Camera:** as S10
- **Living:** counter lands on 'hundred thousand'
- **Sound:** map: counter ticks + soft knock when the number lands (BP-192)
- **Out:** cut
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/maps_our_code_after_s8/S05_SH002_new.mp4

### S05_SH003 · still_25d · 204.42 s (+8.0417 s) · joy: trading and football
- *narrator:* "They traded cigarettes, food, buttons. In a few places, accounts describe men kicking a ball around."
- **Picture:** mixed British and German soldiers trading in the middle (.15-.95, .4-.85), a football game far behind (.35-.6, .35-.42), ruined farm (.75, .25), brazier (.92, .78), smoke rising (.6, .25)
- **Camera:** part 1: slow push toward the hand-to-hand trade in the middle (.55, .55) on 'buttons'; part 2: tilt/push up to the football players (.47, .38) on 'kicking a ball around'
- **Living:** brazier flame; chimney/brazier smoke rising and bending; breath on the visible faces; sun shimmer; NO sky mist blobs (old render had blurred grey blobs at the top = defect)
- **Cold:** breath, frost; no falling snow (clear)
- **Never moves:** men, wire
- **Keep in frame:** every man in the front group
- **Sound:** bed: open land; friendly murmur and one warm laugh (laugh_warm, mid-left); far shouts of the football game panned to the ball (Battle Crowd murmuring, -26 dB)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/9a45b4c1a2ea6f25ccf7f783.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH003.mp4

### S05_SH004 · video · 212.46 s (+2.25 s) · curiosity
- *thomas_hale:* "Where'd you learn English?"
- LTX clip heard: "Where do you learn English?"
- **Clip:** LTX voice ('Where do you learn': accept), full 3.04 s
- **Sound:** clip voice; murmur bed
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/1be456d64b6827f0cf9889ef.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH004_seed7100.mp4

### S05_SH005 · video · 214.71 s (+3.5 s) · London memory
- *friedrich_brandt:* "London. I was a waiter. Four years."
- LTX clip heard: "London. I was a waiter. Four years."
- **Clip:** LTX voice, full 4.71 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH005_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH005_seed7101.mp4

### S05_SH006 · video · 218.21 s (+7.875 s) · human comedy: the barber
- *narrator:* "Many Germans had worked in Britain before the war. One Briton found his old barber among them, and sat down for a haircut."
- LTX clip heard: "LAUGHTER"
- **Clip:** LTX narrated, clip own sound -12 dB: KEEP its laughter (2.3-3.7 s, fits the barber), 8.71 s
- **Sound:** murmur bed; scissors not in library
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/4027aba2635cd8e7e7071f05.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH006_seed7102.mp4

### S05_SH007 · video · 226.08 s (+2.25 s) · gentle question
- *friedrich_brandt:* "You have a family?"
- LTX clip heard: "You have a family."
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH007_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH007_seed7103.mp4

### S05_SH008 · video · 228.33 s (+3.25 s) · family
- *thomas_hale:* "My mum. And a little sister."
- LTX clip heard: "My mum, and a little sister."
- **Clip:** LTX voice, full 4.04 s (check the last frame: pouches near 3.3 s)
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH008_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S05_SH008_seed7300.mp4

### S05_SH009 · video · 231.58 s (+3.5 s) · his daughter
- *friedrich_brandt:* "My wife. My daughter. She is three."
- LTX clip heard: "My wife. My daughter. She is three."
- **Clip:** LTX voice, full 5.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed/S05_SH009_start_n1_card.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH009_seed7105.mp4

### S05_SH010 · still_25d · 235.08 s (+3.375 s) · silent beat: the photograph passes
- *none:* "(Thomas looks at the photograph)"
- **Picture:** close: British gloved hands (left, .25-.45, .35-.7) take a photograph (.42-.55, .42-.55) from German hands (right, .5-.7, .35-.65)
- **Camera:** slow push into the photograph (target (.48, .5)), 3.4 s
- **Living:** breath drifting through the top of the frame once; sun flare shimmer top; spindrift bottom
- **Cold:** breath, frost on the gloves
- **Never moves:** ALL hands and the photograph
- **Keep in frame:** the photograph and the four hands
- **Sound:** near silence: wind low; paper touch (paper_move, very soft) at 0.3 s
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH010_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH010.mp4

### S05_SH011 · video · 238.46 s (+2.0 s) · kind
- *thomas_hale:* "She looks happy."
- LTX clip heard: "She looks happy."
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S05_SH011_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S05_SH011_seed7302.mp4

### S05_SH012 · video · 240.46 s (+3.5 s) · ache
- *friedrich_brandt:* "She thinks I am home for Christmas."
- LTX clip heard: "She thinks I am home for Christmas."
- **Clip:** LTX voice, full 4.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S05_SH012_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/671e136e4bdc_fc6ae61bf410/S05_SH004/S05_SH012_seed7107.mp4

### S05_SH013 · video · 243.96 s (+2.0 s) · shared ache
- *thomas_hale:* "So does mine."
- LTX clip heard: "So does mine."
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice; murmur bed fades out under 'So does mine'
- **Out:** cut (hold 0.5 s of silence before the narration turns)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH013_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S05_SH013_seed7301.mp4

### S05_SH014 · video · 245.96 s (+6.0833 s) · SOLEMN turn: bringing in the dead
- *narrator:* "But the day was not only for trading. Both sides went out to bring in their dead."
- LTX clip heard: "You"
- **Clip:** LTX narrated, clip own sound -14 dB, full 7.04 s
- **Sound:** bed changes: murmur gone, cold wind only; slow footsteps in snow; restraint
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/57a4ea9bd4270fd9064a409d.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH014_seed7100.mp4

### S05_SH015 · video · 252.04 s (+2.5 s) · grief
- *narrator:* "Some had lain out there for weeks."
- LTX clip heard: "(nothing)"
- **Clip:** LTX narrated, full 3.04 s, clip own sound -14 dB (spade in frozen earth)
- **Sound:** wind; spade scrape from the clip
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e2490163ec3a5422222edeca.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH015_seed7101.mp4

### S05_SH016 · still_25d · 254.54 s (+3.5 s) · silent beat: two spades by the grave
- *none:* "(two spades stand in the earth by the grave)"
- **Picture:** a British spade (.3, .1-.75) and a German shovel (.6, .15-.75) planted in a mound of frozen earth, a body under a blanket on a stretcher behind (.3-.6, .45-.55), lamps far left (.12, .4) and right
- **Camera:** slow push to the space between the two spades (target (.45, .45)), 3.5 s
- **Living:** lamps flicker far left and right; ground spindrift drifting across the mound bottom (strength 1.3); a wisp of smoke far left (.12, .3)
- **Cold:** spindrift, frost, cold grade
- **Never moves:** spades, blanket, mound
- **Keep in frame:** both spades whole
- **Sound:** wind alone, slightly stronger gust at 1.5 s; nothing else (restraint)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/45bb0e8ecc8c760ab0be75af.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH016.mp4

### S05_SH017 · video · 258.04 s (+2.25 s) · respect
- *thomas_hale:* "What was his name?"
- LTX clip heard: "What was his name?"
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/e3fa664985bac13da28cd720.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH017_seed7102.mp4

### S05_SH018 · video · 260.29 s (+2.75 s) · grief
- *friedrich_brandt:* "Karl. He sang the loudest."
- LTX clip heard: "Carl, he sang the loudest."
- **Clip:** LTX voice, full 4.38 s
- **Sound:** clip voice; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S05_SH018_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cde4357602e2_fc6ae61bf410/S05_SH018/S05_SH018_seed7400.mp4

### S05_SH019 · video · 263.04 s (+2.0 s) · apology
- *thomas_hale:* "I'm sorry."
- LTX clip heard: "I'm sorry"
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice; wind
- **Out:** cut
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH019_seed7104.mp4

### S05_SH020 · still_25d · 265.04 s (+7.8333 s) · solemn, restrained: the joint burial
- *narrator:* "At one burial, a Scottish chaplain read the Twenty-Third Psalm. A German student read it after him, in German."
- **Picture:** hand-made direction exists (s7_regenerated_directions/S05_SH020.direction.json): Scottish group left (.15-.45, .35-.85), German group right (.55-.85, .35-.85), crosses (.3-.55, .45-.85), braziers (.12, .5) (.9, .5)
- **Camera:** hold on the whole burial during 'a Scottish chaplain read the Twenty-Third Psalm', then a VISIBLE but gentle pan_crop_2d from the Scottish group (.3, .55) to the German group (.7, .55) on 'German' (FIX V6: the move must shift the framing at least 12 % of the frame width)
- **Living:** braziers flicker; sun rays; VISIBLE breath on the bare-headed soldiers; no glints on the crosses
- **Cold:** breath, frost; no falling snow
- **Never moves:** every man, crosses
- **Keep in frame:** both groups whole
- **Sound:** bed: wind very low; no music swell; a single soft bell-less silence; the narrator carries it
- **Out:** cut
- **Journal:** V6: planned pan imperceptible; breath invisible: renderer defects
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/0961d9551910c9b0cd967e5e.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/after_s10/S05_SH020_new.mp4

### S05_SH021 · video · 272.88 s (+4.2917 s) · silent beat: Harris takes off his cap
- *none:* "(Harris takes off his cap at the edge of the graves)"
- LTX clip heard: "You"
- **Clip:** LTX, no line: clip audio -18 dB (wind only, its noise has a false 'You'), full 5.04 s; ends on the lifted cap
- **Sound:** wind; cloth rustle when the cap comes off
- **Out:** dip to black 0.5 s (chapter: dusk)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/c030b4def7eef27edcc0292d.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/cb3c1d2e63b8_fc6ae61bf410/S05_SH014/S05_SH021_seed7105.mp4


## S06

### S06_SH001 · still_25d · 277.17 s (+3.0 s) · the light going
- *narrator:* "By late afternoon, the light was going."
- **Picture:** hand-made direction exists: Thomas left seated on a crate (.3-.45, .25-.85), Friedrich right with mug (.55-.7, .25-.9), brazier right (.95, .8), ruin and willows right
- **Camera:** as the hand-made direction (slow push on the two men), 3.0 s
- **Living:** brazier flame, mug steam VISIBLE, breath both men, sun sinking shimmer
- **Cold:** breath, dusk frost
- **Never moves:** men, crates
- **Keep in frame:** both men and their boots
- **Sound:** bed: dusk wind low; brazier crackle right
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/0beb5fddd6f4426807a55589.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/argon_loop_2026-11-15/2p5d_after_s6_fixes/S06_SH001_new.mp4

### S06_SH002 · video · 280.17 s (+2.75 s) · the question
- *friedrich_brandt:* "Tommy... why are we fighting?"
- LTX clip heard: "Tommy, why are we fighting?"
- **Clip:** LTX voice, full 4.04 s
- **Sound:** clip voice; brazier
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S06_SH002_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH002_seed7100.mp4

### S06_SH003 · video · 282.92 s (+2.0 s) · honest
- *thomas_hale:* "I don't know."
- LTX clip heard: "I don't know."
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S06_SH003_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH003_seed7304.mp4

### S06_SH004 · video · 284.92 s (+3.5 s) · bitter truth
- *friedrich_brandt:* "They told us you were the enemy."
- LTX clip heard: "They told us you were the enemy."
- **Clip:** LTX voice, full 4.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/fc29ca07f635138501dffed1.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH004_seed7102.mp4

### S06_SH005 · still_25d · 288.42 s (+2.0417 s) · silent beat: two shadows side by side
- *none:* "(Thomas looks at Friedrich)"
- **Picture:** two long shadows of the seated men cast across the frozen field toward the sun (.3-.6, .45-.9), trenches with lamps both sides (.15, .45) (.85, .45), smoke rising from two dugouts (.22, .1-.3) (.82, .1-.3)
- **Camera:** very slow push along the shadows toward the sun (target (.5, .4)), 2.0 s
- **Living:** lamps flicker; dugout smoke rises and bends (visible); sun shimmer on the ice; spindrift low; NO sky mist blobs (old render had a grey blur patch at the top centre = defect)
- **Cold:** frost, spindrift
- **Never moves:** shadows (they belong to still men), wire
- **Keep in frame:** both shadows whole
- **Sound:** wind low; brazier crackle off-screen behind camera (centre, close)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/fdfc498552fff49255c364e1.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S06_SH005.mp4

### S06_SH006 · video · 290.46 s (+3.5 s) · mirror
- *thomas_hale:* "They told us the same about you."
- LTX clip heard: "They told us the same about you."
- **Clip:** LTX voice, full 3.71 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/d1484fa3a280046b2ea5de16.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH006_seed7306.mp4

### S06_SH007 · video · 293.96 s (+3.25 s) · fatal maybe
- *friedrich_brandt:* "Tomorrow, maybe, we are enemies again."
- LTX clip heard: "Tomorrow, maybe, we are enemies again."
- **Clip:** LTX voice, full 5.04 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S06_SH007_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH007_seed7104.mp4

### S06_SH008 · video · 297.21 s (+2.25 s) · THE line: 'Maybe. But not today.'
- *thomas_hale:* "Maybe. But not today."
- LTX clip heard: "Maybe. Maybe. But not today."
- **Clip:** LTX voice; FIX: the raw clip says 'Maybe' twice (0.0-0.6 s and 1.72-1.92 s). Start the clip at 1.45 s and play to 4.04 s (2.6 s): 'Maybe. But not today.'
- **Sound:** clip voice; brazier; nothing else
- **Out:** cut (0.4 s of held silence after 'today' before the next shot)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S06_SH008_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH008_seed7303.mp4

### S06_SH009 · video · 299.46 s (+5.6667 s) · silent beat: the button
- *none:* "(Thomas cuts a brass button off his tunic with a penknife)"
- LTX clip heard: "(nothing)"
- **Clip:** LTX R3 take (accepted 11-14), no line: clip own sound -12 dB, full 6.38 s; knife click and cloth snip audible
- **Sound:** small cloth snip; wind low
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/459180abd24b5054b68873f1.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S06_SH009_seed7110.mp4

### S06_SH010 · video · 305.12 s (+2.75 s) · gift
- *thomas_hale:* "Something to remember me by."
- LTX clip heard: "Something to remember me by."
- **Clip:** LTX voice, full 3.71 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S06_SH010_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH010_seed7305.mp4

### S06_SH011 · video · 307.88 s (+2.75 s) · gift returned
- *friedrich_brandt:* "Then take one of mine."
- LTX clip heard: "Then, take one of mine."
- **Clip:** LTX voice, full 3.38 s
- **Sound:** clip voice
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S06_SH011_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/df474a1fd412_fc6ae61bf410/S06_SH002/S06_SH011_seed7108.mp4

### S06_SH012 · still_25d · 310.62 s (+5.4583 s) · the sun goes down; they stay
- *narrator:* "The sun went down on Christmas Day. Neither of them moved to leave."
- **Picture:** two men seen from behind sitting together in no man's land (.42-.55, .4-.6), sunset behind the ruined farm (.65, .25), trench with lamps right-front (.8-.95, .5-.8), brazier left (.15, .63), smoke from the dugout (.15, .2-.4)
- **Camera:** slow pull back (reverse push) from the two men (.5, .5) to the wide, 5.5 s (runner split: hold then pull), the men stay centred
- **Living:** sunset dims: light going down over 5 s (grade toward blue, -15 % exposure at the end); lamps and brazier get relatively brighter; smoke bends; no breath (seen from behind)
- **Cold:** dusk cold grade, frost
- **Never moves:** the two men
- **Keep in frame:** the two men centred and whole
- **Sound:** bed: dusk wind, brazier crackle left; everything thins as the light goes
- **Out:** dip to black 0.8 s (night -> next morning)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/d6dd993ef61f64d9b6129ebc.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S06_SH012.mp4


## S07

### S07_SH001 · still_25d · 316.08 s (+4.25 s) · drifting back, melancholy
- *narrator:* "The next morning, the men drifted back to their own trenches."
- **Picture:** fog at sunrise, a long open field between two parapets; groups of men walking away in both directions (.1-.75, .3-.85), lamps in the trenches
- **Camera:** slow push down the field (target (.5, .35)), 4.25 s
- **Living:** fog drift (visible), sun shafts; lamps flicker; breath none (backs)
- **Cold:** frost haze, no falling snow
- **Never moves:** men, wire
- **Keep in frame:** the walking groups
- **Sound:** bed: morning wind; many slow footsteps in snow (footstep_snow, layered, panned both ways)
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/82ece8ecbcfa5da9123fe8cd.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S07_SH001.mp4

### S07_SH002 · video · 320.33 s (+2.0 s) · farewell offered: Friedrich wishes him luck
- *friedrich_brandt:* "Good luck, Tommy."
- LTX clip heard: "Good luck, Tommy."
- **Clip:** LTX voice, full 3.04 s
- **Sound:** clip voice; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/mirrored/S07_SH002_start_mirror.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH002_seed7100.mp4

### S07_SH003 · video · 322.33 s (+2.0 s) · farewell returned; Thomas turns back to his line
- *thomas_hale:* "You too, Fritz."
- LTX clip heard: "You too, Fritz."
- **Clip:** LTX voice, full 3.04 s (Thomas turns away = good)
- **Sound:** clip voice; footsteps
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/fixed2/S07_SH003_start_fix2.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH003_seed7101.mp4

### S07_SH004 · video · 324.33 s (+2.0 s) · back to war
- *sgt_harris:* "Stand to."
- LTX clip heard: "stan 2"
- **Clip:** LTX voice, full 3.04 s; the narration of S07_SH005 starts under its last 1.0 s (J-cut) so the revolver shots land near 'ended it politely'
- **Sound:** clip voice; trench wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/060bfd79498d4a66871d9528.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH004_seed7102.mp4

### S07_SH005 · video · 326.33 s (+7.25 s) · polite end: two shots into the air, salute
- *narrator:* "At Houplines, on Boxing Day morning, a British captain ended it politely: shots into the air."
- LTX clip heard: "BANG! BANG!"
- **Clip:** LTX R3 take, narrated; KEEP its two gunshots (0.5 s and 1.6 s of the clip, loud) at full effect level; the narrator ducks 4 dB under each bang; full 8.04 s; level trim -0.5 dB (CLIP-06 -0.1 dBTP)
- **Sound:** gunshots from the clip, echo across no man's land (reverb tail 1.2 s); bed trench wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/cache/064e7631e9b16acc8c24f40f.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S07_SH005_seed7111.mp4

### S07_SH006 · video · 333.58 s (+7.9583 s) · the German answer
- *none:* "(the German captain salutes back, gets down into his trench, then fires two shots into the air)"
- LTX clip heard: "I'll see you next time."
- **Clip:** LTX, no line: clip audio has ONE shot at 7.9 s; add a second shot 0.9 s earlier by reusing the S07_SH005 clip's second bang (-4 dB, far, panned right); full 8.71 s
- **Sound:** two far shots from the German trench (right), long echo; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/ab948b9d23ecd7a1affa1b5c.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH006_seed7104.mp4

### S07_SH007 · video · 341.54 s (+2.8333 s) · Thomas hears it end
- *none:* "(Thomas looks up at the shots)"
- LTX clip heard: "You"
- **Clip:** LTX, no line: clip audio -18 dB, full 3.71 s
- **Sound:** the echo of the second shot dies over this shot; wind
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/button_fix/S07_SH007_start.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH007_seed7105.mp4

### S07_SH008 · video · 344.38 s (+8.375 s) · history's verdict, war resumes
- *narrator:* "There had been no treaty. In some places the truce lasted hours. In others, it held until the New Year."
- LTX clip heard: "You"
- **Clip:** LTX R3 take narrated, clip own sound -14 dB, full 9.04 s
- **Sound:** trench wind; one distant rumble at the end (amb_low_rumble, far, -28 dB) = the guns are back
- **Out:** dip to black 0.6 s (night: the letter)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/button_fix/S07_SH008_start.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S07_SH008_seed7112.mp4


## S08

### S08_SH001 · still_25d · 352.75 s (+7.8333 s) · writing home, intimate
- *narrator:* "Thomas wrote home that night. So did many others. In January, British newspapers printed their letters."
- **Picture:** dugout at night: a candle in a holder left (.22, .25-.45), Thomas's hand writing with a pencil (.45-.6, .4-.6) on a letter, a brass button on the table (.5, .72), an old letter right (.75, .75), the open trench at night right with moon (.88, .07) and a brazier (.9, .45)
- **Camera:** slow push to the writing hand and the button (target (.52, .62)), 7.8 s (runner split: part 2 settles on the button on 'printed their letters')
- **Living:** candle flame + spill on the paper (strength 1.2); brazier far right; light falling snow in the open trench ONLY (right third, x > .7, far layer, never inside the dugout)
- **Cold:** warm interior vs blue cold outside
- **Never moves:** the writing hand (do not animate the pencil), candle body
- **Keep in frame:** hand, letter, button
- **Sound:** bed: night wind outside, muffled (low-pass) because we are inside; pencil scratching (pencil_scribble, close, centre); candle silent
- **Out:** cut
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/03bcf8817982220b0b2b0ef6.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH001.mp4

### S08_SH002 · still_25d · 360.58 s (+9.75 s) · the commanders forbid it; the keepsake
- *narrator:* "Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale."
- **Picture:** hand-made direction exists: hands hold the photograph with the brass button (.4-.6, .25-.65), candle right (.83, .25-.6), open trench behind at dusk
- **Camera:** as the hand-made direction (push lands on the button on 'prevent'), 8.75 s split by the runner
- **Living:** candle flame bending and guttering in the draft (the cold is felt); FIX V1: snow ONLY behind in the open trench, wind-driven diagonal, depth layers, never over the hands or the photo; FIX V2: frame 0 = the picture, effects fade in
- **Cold:** draft-bent candle, blue grade in the shadows against the small warm light
- **Never moves:** hands, photo, button, candle body
- **Keep in frame:** hands, photo, button
- **Sound:** bed: night wind with gusts that match the candle bending; a soft metallic touch when the button is first seen (coin-like, not in library: leave silent)
- **Out:** cut
- **Journal:** V1 'pretty cute snow', V2 snow on frame 0, V3 snow over the close subject: renderer defects
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/89645231dc29774437adbc26.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH002.mp4

### S08_SH003 · still_25d · 370.33 s (+3.5833 s) · the war goes on (no comfort)
- *narrator:* "The war went on for almost four more years."
- **Picture:** NEW CHOICE: reuse the picture of S01_SH001 (the empty frozen field of the opening) instead of the current S08_SH003 picture, which shows men still fraternising in the field and so contradicts 'The war went on'. Bookend: the film ends where it began, the field empty again
- **Camera:** slow pull back (the field recedes), 3.6 s
- **Living:** fog drift; cold blue-grey grade over the golden picture if the renderer can (else none); spindrift
- **Cold:** cold, empty
- **Never moves:** wire, stakes
- **Keep in frame:** the field
- **Sound:** bed: open-land wind; two distant artillery rumbles far left and far right (amb_low_rumble, -26 dB, 1.2 s apart)
- **Out:** dip to black 0.6 s
- **Journal:** S08_SH003 picture contradicts its line (men in the field during 'The war went on for almost four more years'): data change to reuse S01_SH001_start
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/cache/ae380e00e9c9f5cf5946a1e4.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH003.mp4

### S08_SH004 · still_25d · 373.92 s (+5.9167 s) · end card: memory
- *none:* "(on screen: For one day, they remembered they were human.)"
- **Picture:** black frame with one candle (.8, .55-.8)
- **Camera:** locked (no push), 5.9 s
- **Living:** the candle flame breathes; the end text 'For one day, they remembered they were human.' fades in at 0.8 s, centred left of the candle, serif, warm white, holds, fades out at 5.2 s
- **Cold:** none
- **Never moves:** candle body
- **Keep in frame:** candle and text
- **Sound:** silence except a very low wind; the candle is silent; music (if any) resolves here
- **Out:** fade to black 1.0 s (end)
- photo: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/clips_lane_newangles/S08_SH004_start_candle.png
- current clip: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S08_SH004.mp4

## Music accents (added 2026-11-15 17:00 UTC, the creator's question on dramatic moments)
All tracks are Kevin MacLeod / incompetech, CC BY 4.0, already in the library (attribution line in the video description, text in catalog.sqlite).
The score sits under the narrator: ducked 8-10 dB while a voice speaks, it rises to its own level only in the gaps listed below.
| moment | time (clock) | cue |
|---|---|---|
| S01_SH005 "the day the war stopped" | 19.7-29.0 s | Echoes of Time swells +4 dB on "stopped", falls to nothing under the dip to black |
| S02_SH004 misery, "sniper" | 48.2-56.0 s | Dark Times low string pulse; a 1 s silence before "sniper" |
| S03 night | 91-133 s | no score: the carol is the music |
| S04_SH005-SH008 Thomas climbs out and walks | 143.8-165.8 s | Lightless Dawn tension pad rises slowly from the climb to the walk; cuts to silence on "the men who never made it back" |
| S04_SH011 empty hands | 169.8 s | silence (the release) |
| S05_SH003 trading | 204.4-246 s | Village Consort, light, low; out under "So does mine" |
| S05_SH014-SH021 the dead | 246-277 s | no score (restraint) |
| S06_SH008 "Maybe. But not today." | 297.2 s | Despair and Triumph enters softly right AFTER "today" (not under the line) and carries S06_SH009-SH012 to the dip |
| S07_SH005-SH006 shots | 326-341 s | silence; after the second echo Thunder Dreams low drone enters (the war is back) |
| S08 letter -> end card | 352.8-380 s | Ancient Rite low; resolves on the end card, last note fades with the candle |
Gap: no free instrumental "Silent Night" recording in the library. The melody (Gruber, 1818) is public domain, but every recording has its own licence. Optional: one solo instrumental recording from YouTube Audio Library (free, check the attribution flag per track) or Musopen (public-domain or CC recordings), for the end card only. Nothing is downloaded without the creator's word.
