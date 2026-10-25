# What If Napoleon Marched Into Genghis Khan? The prompt package

**ქართულად, მოკლედ.** ეს არის ერთი სრული 15-წუთიანი ეპიზოდის პრომპტი, დაწერილი სკრიპტის ენჯინ v1-ზე: ჩონჩხი,
სცენარი (მთხრობელი + დიალოგი), 214 შოტის ბარათი, ყველა სურათის, პოზის, კადრის და ვიდეოს პრომპტი, წყაროები და
გამოგონილის სია. ყველაფერი, რასაც მაყურებელი ხედავს ან ისმენს, ინგლისურადაა. შეფასებისთვის ეს ფაილი თავისთავად
საკმარისია; ყველა პრომპტი შოტების მიხედვით `shotlist.md`-შია.

## 0. How to judge this package

- Everything here is generated from one file of shot cards (`film_shots.json`, built by `build_cards.py` from
  `episode.py`) by the engine's composer; no prompt was typed by hand (rule ZI-01 of `docs/SCRIPT_ENGINE.md`).
- `python -m explainer_engine.scripting.film_shots check film_shots.json` -> **214 shots, 0 FAIL, 0 REVIEW** under
  the card rules KP-15..KP-43, the prompt lint KP-01..KP-14 and the engine rules ZI-02/ZI-03.
- Files: `film_shots.json` (the cards), `prompts.json` (9 hero sheets, 444 prompts, 230 gate
  cards for the keyframe check), `script.md` (the readable script with claim ids), `shotlist.md` (the script with every picture and video prompt under its shot), this package.

## 1. The story

**Premise.** September 1812: the Grande Armee marches into a fog outside Moscow and comes out on the steppe of 1223,
where Genghis Khan's army is waiting. **Central question:** can the man who conquered Europe beat the man who conquered
Asia? **Answer (mixed):** on a battlefield yes, in a campaign no. Napoleon wins the one battle the khan gives him and
loses his food; he buys the way home with two guns and a gunner, and comes out in 1812 to a Moscow burned by its own
side: the khan's lesson again.

**The two commanders, from the sources.** Napoleon: trained as an artillery officer, always on the offensive, wants
one decisive battle that destroys the enemy army, rages when a plan stalls (C04); he lays a gun himself, refuses to
serve anyone, and in the end pays a price to save the army. Genghis Khan: promotes by merit and loyalty, generous to
his own, ruthless to enemies, keeps the enemy archer who shot his horse and told him so, and collects skilled men from
the defeated (C11): he rewards the scout who lost his horse and admits it, wants the guns whole and a gunner to teach
his men, and offers Napoleon a tumen (C20).

**The two armies, from the sources.**

| | Grande Armee (1812) | Mongol army (1220s) |
|---|---|---|
| Reach | 12-pounder: about 900 m round shot, 600 m canister (C05); musket about 100 yd / 90 m, 2-3 shots a minute (C06) | composite bow: aimed 150-175 m, ballistic to about 400 m, 60 arrows a quiver (C09) |
| Defence | the infantry square: held its volley until the cavalry was close, rarely broken by cavalry alone (C07) | never stands where the guns land; feigned retreat (Kalka, about nine days, C10) |
| Mobility | heavy wagons, foraging along the road (C16); Murat spends horses (C13) | three or four horses a man, fresh mounts on the march (C08) |
| What it needs | a decisive battle, bread from wagons and farms | grass for the herds |

**Invented, and said so (ZI-04).** The fog and the jump (I01); Genghis Khan himself in the west in 1223, when in fact he
was back in Central Asia (C19) (I02); the skirmish, the valley battle, the burning of the wagons and every number in
them (I03); the parley and the two guns (I04); every line of dialogue; Kemal, Bars, Bayan, Brun and Petit. Kemal
can understand Bars because Crimean Tatar and the steppe's Kipchak are both Kipchak Turkic (C15) and the Guard's
mameluke company had Crimean men in 1812 (C14); real-life understanding would be partial, the story simplifies it.

## 2. The skeleton (template D, 16 segments)

| Segment | Clock | Function | Shots | What happens |
|---|---|---|---|---|
| S01 | 0:00-0:12 | hook | 5 | A drum stops in the fog; three 2 s teasers cut from the battle (canister into riders, lances against the square, torches on the wagons, KP-41); Mongol archers raise their bows on a ridge. |
| S02 | 0:12-0:36 | information gap | 6 | 1812 -> 1223; the khan is waiting; Napoleon will win the only battle and it will be his worst victory; the central question. |
| S03 | 0:36-1:15 | orientation | 10 | Two war machines: the artilleryman's guns and muskets against remounts, long-range bows and promotion by merit. |
| S04 | 1:15-2:51 | scene 1, inciting | 21 | An envoy at Napoleon's tents. A Crimean mameluke can understand him. The khan's terms; the Kalka warning; riders watch from the ridge; Napoleon wants battle. |
| S05 | 2:51-3:13 | bridge | 5 | The army is fed from wagons and farms; the steppe has only grass; Napoleon needs his battle fast. |
| S06 | 3:13-4:57 | scene 2, escalation | 27 | Plan 1 fails: the camp is empty, arrows from 400 m outrange the muskets, Murat's charge dies on tired horses. Napoleon lays a 12-pounder himself: first hit at 900 m; the riders form again out of range. |
| S07 | 4:57-5:46 | new complication | 12 | Horses and hunger: Murat spends horses, every Mongol has three more; the last biscuit; foragers vanish; no battle. |
| S08 | 5:46-7:29 | scene 3, the other side acts | 22 | The khan's yurt, cross-cut with the plan carried out (KP-42): an honest scout is rewarded; scouts count the French wagons; the French column pulls away from its wagons; 'a small one, let him win, take his wagons' while riders slip out at night; bring the guns whole. |
| S09 | 7:29-8:23 | preparation | 13 | The chase wears the French down; Napoleon sets a trap in a valley and takes every fighting man out of camp. A Mongol scout watches the guns being hidden; riders walk a dry gully toward the wagons. The khan waited for that. |
| S10 | 8:23-10:51 | central scene | 38 | The battle Napoleon wanted: arrow storm, the square holds, the lance charge breaks on a volley, hidden canister at 600 m; he refuses the chase. Cross-cut with the camp (KP-42): the drummer hears hooves, the guards fire one ragged volley, torches land the moment Napoleon smiles, the drummer beats the alarm. The khan: 'He is winning the wrong thing.' |
| S11 | 10:51-11:26 | turning point | 8 | The winner on his field. 'We won.' A burnt loaf. Murat: 'They never wanted the field.' |
| S12 | 11:26-12:06 | fallout | 9 | Who won and lost: Mongol riders lost, no horse that can't be replaced; the French food is gone; they eat their horses. An invitation. |
| S13 | 12:06-13:47 | scene 4, the final choice | 21 | The parley. The khan offers a tumen; Napoleon will not serve. The price of the way home: two guns and a gunner. Outside, the men eat grass; he pays it, and two guns are dragged off. |
| S14 | 13:47-14:34 | the answer | 11 | On a battlefield, yes; in a campaign, no. The fog returns; Moscow on 14 September 1812, almost empty and burning; the tsar refuses; the retreat; the count is uncertain. |
| S15 | 14:34-14:46 | callback | 3 | The drumstick stops again, before Moscow's fire. He had seen this fire 589 years earlier. |
| S16 | 14:46-15:00 | channel pointer | 3 | The Stone Age on the channel, the Ice Age next, worlds to the future; subscribe so as not to miss them. The khan tosses a French cannonball. |

Runtime 15:00; 214 shots = 14.3 a minute (BP-107 band 11-17), median shot
4 s; narrator 500 words, dialogue 613 words: the narrator has
45% of the words (BP-105, 25-45 %); the longest narration block stays under 90 s (BP-104).

## 3. Which variants this package uses (ZI-05)

| Dimension | Variant used here | What can replace it |
|---|---|---|
| Picture prompts | composed sentences: trigger, size and angle, place and light, each person by tag with side, gaze, first-frame pose, support and height in words, relations, free space (KP-31..KP-34) | numbers for the height (`height_pct`), if test T1 says numbers hold better |
| Keyframes and hero sheets | Qwen-Image-2512 + `wldnk style` LoRA, bf16, 1280x720, 24 steps, true CFG 4 | 1664x928, 50 steps |
| Poses, cuts, last frames | Qwen-Image-Edit-2511 + scene LoRA v1 only, from the scene's master or the shot's own first frame | - |
| Video | LTX-2.5 with native audio; full tier 160 shots (688 s) on dev, light 44 shots (171 s) on distilled, hold 10 shots (41 s) as keyframe + camera move | the cheaper model on full shots after the 1-minute film; 12 fps or twos |
| Clip length | at most 10 s; shots over 5 s with an action draw a last frame | longer clips with a video LoRA |
| Frames | 24 fps, 8k+1 frames per clip (21667 frames in all) | 12 fps |
| Size | test film 1280x704, no upscale (LT-18); release upscaled to 2560x1440 | 1920x1088 before the upscale |
| Camera | static on 204 of 214 shots, one move on 10 (BP-110: at most 20 %) | - |
| Voices | dialogue from LTX, the voice in words on each cast card; narrator ElevenLabs | one voice take per hero for audio-to-video |

## 4. The cast (one tag per hero, the same words in every prompt; names never enter a prompt, KP-15, KP-22)

| Name | Tag | Voice |
|---|---|---|
| Napoleon | the short general in a grey greatcoat and a black bicorne hat | a quick, clipped, slightly hoarse man's voice with a French accent |
| Murat | the tall marshal with long black curls and a white-plumed fur hat | a loud, bright, boastful man's voice with a southern French accent |
| Kemal | the mameluke rider in a white turban and a red embroidered vest | a soft, careful young man's voice with a Crimean Tatar accent |
| Brun | the grey-moustached grenadier in a tall black bearskin cap | a gravelly, tired old soldier's voice with a French accent |
| (group) | the ranks of French infantry in dark blue coats with white crossbelts | - |
| (group) | the French gun crew in dark blue jackets beside a bronze cannon | - |
| Genghis | the tall khan with a long grey beard and a blue fur-trimmed robe | a deep, slow, quiet man's voice with a Mongolian accent |
| Subutai | the stocky general with a shaved head and bronze scale armour | a flat, dry, practical man's voice with a Mongolian accent |
| Bars | the young interpreter with a braided forelock and a green felt cap | a quick, high young man's voice with a Turkic accent |
| Bayan | the young scout with a scar on his cheek and a fox-fur hat | a breathless young man's voice with a Mongolian accent |
| (group) | the line of Mongol horse archers in brown felt coats on short shaggy horses | - |
| (group) | the French cuirassiers in steel breastplates and brass helmets on big horses | - |
| Petit | the young drummer in a white shako with a red plume | a thin, hungry teenage voice with a French accent |
| (group) | the two Mongol scouts in brown felt coats with bows on their backs | - |
| (group) | the handful of French camp guards in grey greatcoats with long muskets | - |
| (group) | the crowd of modern people in bright jackets around a Stone Age campfire | - |
| (group) | the group of stranded travellers in winter coats on the Ice Age snow | - |

Each named hero gets one collage of four variants first (`prompts.json` -> `sheets`); the creator picks one, and that
sheet is what every keyframe, pose and clip is checked against (invariant 6).

## 5. Prompt samples (one of each kind; all 444 are in `prompts.json`)

**Hero sheet (Qwen-Image-2512 + style LoRA)** `{"id": "sheet.napoleon", "kind": "keyframe", "lora": "style"}`

> wldnk style, four variants of the short general in a grey greatcoat and a black bicorne hat, thin-limbed and bulging-eyed, side by side, neutral faces, warm studio light, each a little different in face and build

**Master keyframe (Qwen-Image-2512 + style LoRA)** `{"id": "S04-01.first", "kind": "keyframe", "lora": "style"}`

> wldnk style, a French army camp on the open steppe, the young interpreter pulls his horse up hard, the short general raises one eyebrow, the mameluke rider leans in to listen, the tall marshal, warm late afternoon light

**Cut, new size of the master (Edit-2511 + scene LoRA)** `{"id": "S04-07.first", "kind": "cut", "lora": "scene", "master": "S04-01"}`

> The same place, light and characters as in the first image, now an over-the-shoulder shot at eye level, past the shoulder of the mameluke rider in a white turban and a red embroidered vest. The mameluke rider in a white turban and a red embroidered vest, in the foreground on the left, looking at the young interpreter with a braided forelock and a green felt cap, holds his horse by the bridle, standing in the dry steppe grass, filling about half of the frame height. The young interpreter with a braided forelock and a green felt cap, in the center, looking at the mameluke rider in a white turban and a red embroidered vest, sits straight on his horse, sitting astride a short shaggy horse, filling most of the frame height. Empty space at the top of the frame, where his fist rises. Every character looks exactly as on their character sheet.

**Next pose of the master (Edit-2511 + scene LoRA)** `{"id": "S06-08.first", "kind": "nextpose", "lora": "scene", "master": "S06-07"}`

> nextpose, a later frame of the same continuous animated shot, same camera: the mameluke rider in a white turban and a red embroidered vest, on the left, shades his eyes with one hand. Same characters, same camera; nobody new appears and nobody disappears.

**Last frame of a long acted shot (Edit-2511 + scene LoRA)** `{"id": "S13-17.last", "kind": "nextpose", "lora": "scene", "master": "S13-17"}`

> nextpose, a later frame of the same continuous animated shot, same camera: the short general in a grey greatcoat and a black bicorne hat, in the center, stands with the bare hand open. Same characters, same camera; nobody new appears and nobody disappears.

**Video, full tier, a spoken line (LTX-2.5 dev, native audio)** `{"id": "S13-17.video", "kind": "video", "tier": "full", "model": "ltx-2.5-dev", "seconds": 6, "fps": 24, "frames": 145}`

> Hand-drawn 2D cartoon animation with bold black ink outlines, big bulging eyes and bright colours; snappy cartoon timing, poses hold between quick moves. The short general in a grey greatcoat and a black bicorne hat, in the center, pulls off one glove, then slaps the glove down on the carpet, and stands with the bare hand open. After a short pause, the short general in a grey greatcoat and a black bicorne hat says in English, slow, each word paid for, in a quick, clipped, slightly hoarse man's voice with a French accent: "Two guns. Not one more." Everyone stays in frame. Static camera. We hear a fire crackling, wind against felt and leather on carpet.

**Video, light tier (LTX-2.5 distilled)** `{"id": "S02-03.video", "kind": "video", "tier": "light", "model": "ltx-2.5-distilled", "seconds": 4, "fps": 24, "frames": 97}`

> Hand-drawn 2D cartoon animation with bold black ink outlines, big bulging eyes and bright colours; snappy cartoon timing, poses hold between quick moves. The tall khan with a long grey beard and a blue fur-trimmed robe, in the center, sits his horse on the ridge, perfectly still, then lifts his chin slowly toward the fog, and narrows his eyes and holds them there. His mouth stays flat, his eyes do not blink. Nobody speaks. Everyone stays in frame. Static camera. We hear wind over the ridge.

**Video, hold tier (no video model: keyframe + our camera move)** `{"id": "S03-05.video", "kind": "video", "tier": "hold", "model": "camera", "seconds": 4, "fps": 24, "frames": 97}`

> Hand-drawn 2D cartoon animation with bold black ink outlines, big bulging eyes and bright colours; snappy cartoon timing, poses hold between quick moves. Nobody speaks. Everyone stays in frame. The camera pans right, ending on the herd stretching to the horizon. We hear horses grazing, a far-off horn and many hooves on turf.

## 6. Claim map (every number the narrator says carries one of these ids, ZI-02)

| ID | Kind | Claim | Source |
|---|---|---|---|
| C01 | fact | The first wave of the Grande Armee crossed the Neman on 24 June 1812: more than 450,000 men and over 150,000 horses. | https://en.wikipedia.org/wiki/French_invasion_of_Russia |
| C02 | fact | About 100,000 French troops entered Moscow on 14 September 1812. | https://en.wikipedia.org/wiki/French_invasion_of_Russia |
| C04 | fact | Napoleon trained as an artillery officer; he preferred the offensive and aimed to destroy the enemy's army in battle. | https://en.wikipedia.org/wiki/Napoleon |
| C05 | fact | The Gribeauval 12-pounder: effective range about 900 m with round shot and 600 m with canister; a crew of 15. | https://en.wikipedia.org/wiki/Canon_de_12_Gribeauval |
| C06 | fact | The Charleville musket was effective to about 100 yards (90 m), two or three shots a minute. | https://en.wikipedia.org/wiki/Charleville_model_1777_musket |
| C07 | fact | Infantry squares held their volley until cavalry was very close; a steady square was rarely broken by cavalry alone, artillery was its main danger. | https://en.wikipedia.org/wiki/Infantry_square |
| C08 | fact | Each Mongol soldier kept three or four horses and changed mounts on the march. | https://en.wikipedia.org/wiki/Mongol_military_tactics_and_organization |
| C09 | fact | Mongol composite bows: aimed shots at about 150-175 m, ballistic shots up to about 400 m; a quiver of 60 arrows. | https://en.wikipedia.org/wiki/Mongol_military_tactics_and_organization |
| C10 | fact | Kalka River, 31 May 1223: the Rus princes had killed the Mongol envoys; Jebe and Subutai drew them on in a feigned retreat of about nine days and destroyed them; captured princes were crushed under a victory platform. | https://en.wikipedia.org/wiki/Battle_of_the_Kalka_River |
| C11 | fact | Genghis Khan promoted by merit and loyalty, kept the enemy archer Jebe who had shot his horse and admitted it, and recruited skilled men from defeated enemies. | https://en.wikipedia.org/wiki/Genghis_Khan |
| C12 | fact | Moscow was abandoned by Kutuzov's army and burned (Governor Rostopchin); Alexander I refused to negotiate; the French left on 19 October after about five weeks. | https://en.wikipedia.org/wiki/French_invasion_of_Russia |
| C13 | fact | Murat was the best cavalry commander of the Grande Armee and showed a total lack of concern for the well-being of his horses. | https://en.wikipedia.org/wiki/Joachim_Murat |
| C14 | fact | The Mameluke company of the Imperial Guard served in Russia in 1812 (109 riders on 1 July); its men came from Crimea, Georgia, Circassia, Syria, Egypt and elsewhere. | https://en.wikipedia.org/wiki/Mamelukes_of_the_Imperial_Guard |
| C15 | fact | Crimean Tatar and Cuman (the Kipchak of the 13th-century steppe) are both Kipchak Turkic languages. | https://en.wikipedia.org/wiki/Kipchak_languages |
| C16 | fact | The army's supply rested on heavy wagons unfit for Russian tracks; foraging along the road fed the rest ('the Army must live by the sword', Colonel Pion). | https://en.wikipedia.org/wiki/French_invasion_of_Russia |
| C19 | fact | Genghis Khan stopped his Central Asian campaign in 1221 and was back in Mongolia by 1225; in 1223 he was not on the western steppe. | https://en.wikipedia.org/wiki/Genghis_Khan |
| C20 | fact | A tumen was a Mongol unit of 10,000 men. | https://en.wikipedia.org/wiki/Mongol_military_tactics_and_organization |
| C21 | fact | 1812 - 1223 = 589 years. | arithmetic |
| CH1 | fact | The channel's episodes: 100 geniuses in the Stone Age (on the channel); 100 people dropped into the Ice Age (coming next). | CrossWorld Chronicles, the creator's plan 2026-10-24 |
| I01 | invented | The fog that drops the army from 1812 into the steppe of 1223, and back. | the episode's premise |
| I02 | invented | Genghis Khan himself on the western steppe in 1223 with about two tumens. | the episode's premise (against C19) |
| I03 | invented | The skirmish, the valley battle, the burning of the wagons and their numbers. | the episode's story |
| I04 | invented | The parley and the two guns left to the khan. | the episode's story |

## 7. Open points for the creator

- **The outro's worlds.** It names the Stone Age ("a hundred geniuses", on the channel) and the Ice Age (next). Check
  the names against the published videos; the check (KP-40) reads them from the `channel` block.
- **Cost** has not been estimated for this script on its own: at the eras clips' rate (about $10-12 per 10 minutes at
  full quality, an estimate) the 15 minutes would be in the region of $15-18 before retakes, to be priced
  properly in the paint plan and the video plan before any paid run.
- **AI acting (KP-43).** 90 lines carry the acting check and a fallback that hides the
  mouth; the parley is the first candidate for the paid acting test in the 1-minute film.
- **What is not verified:** no picture or clip of this script has been drawn yet; the tier shares, the 24 fps and the
  word sizes are the variants above, not results.

## 8. The full script



### S01

- `0:00.0` S01-01 NARRATOR: In September 1812, Napoleon marched a hundred thousand men into a fog outside Moscow. [C02]
- `0:03.0` S01-02 (Teaser: a cannon blast breaks a mass of riders.)
- `0:05.0` S01-03 (Teaser: lances against a wall of bayonets.)
- `0:07.0` S01-04 (Teaser: torches on the wagons.)
- `0:09.0` S01-05 (Reveal: an army no European has seen in six centuries.)

### S02

- `0:12.0` S02-01 NARRATOR: They came out of it in the year 1223. [I01]
- `0:16.0` S02-02 NARRATOR: And the army waiting for them belonged to Genghis Khan. [I02]
- `0:20.0` S02-03 NARRATOR: Napoleon will win the only battle the khan gives him.
- `0:24.0` S02-04 NARRATOR: And it will be his worst victory.
- `0:28.0` S02-05 NARRATOR: So what happens when the man who conquered Europe meets the man who conquered Asia?
- `0:32.0` S02-06 (Title beat: the two armies, a valley apart.)

### S03

- `0:36.0` S03-01 NARRATOR: Napoleon had trained as an artillery officer. [C04]
- `0:40.0` S03-02 NARRATOR: His method: find the enemy army, force one big battle, destroy it. [C04]
- `0:44.0` S03-03 NARRATOR: His guns could hit a target nine hundred metres away. [C05]
- `0:47.0` S03-04 NARRATOR: His muskets reached about a hundred. [C06]
- `0:51.0` S03-05 NARRATOR: Genghis Khan built his army to move.
- `0:55.0` S03-06 NARRATOR: Every rider brought three or four horses. [C08]
- `0:59.0` S03-07 NARRATOR: His archers could drop an arrow four hundred metres away. [C09]
- `1:03.0` S03-08 NARRATOR: He promoted men for what they did, not for their fathers. [C11]
- `1:07.0` S03-09 (Two weapons side by side, two philosophies.)
- `1:11.0` S03-10 (The gap between the armies closes.)

### S04

- `1:15.0` S04-01 (A lone rider comes to the emperor's tents.)
- `1:19.0` S04-02 **MURAT**: "Sire. Let me knock that ghost off his pony."
- `1:24.0` S04-03 **NAPOLEON**: "Not yet. A man who rides in alone wants to talk."
- `1:30.0` S04-04 **KEMAL**: "Sire. He speaks the old Tatar tongue. My grandmother's."
- `1:35.0` S04-05 (Napoleon registers the impossible and moves on.)
- `1:39.0` S04-06 **NAPOLEON**: "Then tell me what he wants."
- `1:43.0` S04-07 **BARS**: "The khan of all who live in felt tents says: kneel."
- `1:49.0` S04-08 **BARS**: "Give him your horses and your guns, and you will live."
- `1:55.0` S04-09 (Murat finds it funny.)
- `1:59.0` S04-10 **NAPOLEON**: "Tell your khan I kneel to nobody. We meet in battle."
- `2:05.0` S04-11 **BARS**: "This spring, princes on the river killed the khan's envoys."
- `2:10.0` S04-12 **BARS**: "Now the princes are dead."
- `2:14.0` S04-13 (Murat goes for his pistol.)
- `2:18.0` S04-14 **NAPOLEON**: "Put it away. Nobody touches an envoy."
- `2:22.0` S04-15 **NAPOLEON**: "Where is your khan's army?"
- `2:26.0` S04-16 **BARS**: "Everywhere you are not."
- `2:30.0` S04-17 (On the far ridge, riders watch the camp.)
- `2:33.0` S04-18 (The envoy rides off into the empty steppe.)
- `2:37.0` S04-19 **NAPOLEON**: "Murat. Tomorrow you find me that army."
- `2:42.0` S04-20 **MURAT**: "Tomorrow, Sire. You'll have him by lunch."
- `2:46.0` S04-21 **BRUN**: "Wherever it is, I hope it has bread."

### S05

- `2:51.0` S05-01 NARRATOR: Napoleon's army ate from wagons, and from the farms along the road. [C16]
- `2:56.0` S05-02 NARRATOR: On this steppe, there were no farms.
- `3:00.0` S05-03 NARRATOR: Only grass. And grass feeds horses, not men.
- `3:04.0` S05-04 NARRATOR: So he needed his battle, and he needed it fast.
- `3:09.0` S05-05 (Murat's cavalry rides out at dawn.)

### S06

- `3:13.0` S06-01 (The camp Murat found is already gone.)
- `3:17.0` S06-02 **MURAT**: "Gone. And the ashes are warm."
- `3:21.0` S06-03 (An arrow from nowhere.)
- `3:24.0` S06-04 (They were watching all along, out of range.)
- `3:28.0` S06-05 **BRUN**: "Down! Get down!"
- `3:32.0` S06-06 (A pinned pack.)
- `3:35.0` S06-07 **NAPOLEON**: "How far are they?"
- `3:39.0` S06-08 **KEMAL**: "Four hundred metres, Sire. Maybe more."
- `3:43.0` S06-09 **KEMAL**: "They shoot high, Sire. The arrows drop on us."
- `3:48.0` S06-10 (They keep falling.)
- `3:51.0` S06-11 **NAPOLEON**: "Our muskets reach a hundred."
- `3:55.0` S06-12 **NAPOLEON**: "Murat! Drive them off that ridge!"
- `3:59.0` S06-13 **MURAT**: "With pleasure!"
- `4:03.0` S06-14 (The French charge.)
- `4:07.0` S06-15 (The Mongols turn away and shoot backwards.)
- `4:11.0` S06-16 (The French horses are spent.)
- `4:15.0` S06-17 (The Mongols' horses are not.)
- `4:19.0` S06-18 **MURAT**: "They change horses, Sire! Like shirts! We can't catch them."
- `4:24.0` S06-19 **NAPOLEON**: "Then stop chasing. Bring up the guns."
- `4:28.0` S06-20 (The guns come up.)
- `4:32.0` S06-21 **NAPOLEON**: "Up two degrees. Wait for my word."
- `4:36.0` S06-22 **NAPOLEON**: "Fire."
- `4:39.0` S06-23 (The gun fires.)
- `4:42.0` S06-24 (Nine hundred metres away, the ridge breaks.)
- `4:46.0` S06-25 **NAPOLEON**: "Nine hundred metres. Let him outrun that."
- `4:50.0` S06-26 **BRUN**: "First thing we've hit all week."
- `4:54.0` S06-27 (Out of range, they form again.)

### S07

- `4:57.0` S07-01 NARRATOR: Murat was the best cavalry commander in the army. [C13]
- `5:01.0` S07-02 NARRATOR: He spent horses the way other men spend coins. [C13]
- `5:05.0` S07-03 **MURAT**: "Come on, old girl. One more day."
- `5:09.0` S07-04 NARRATOR: Every dead French horse was gone for good.
- `5:13.0` S07-05 NARRATOR: Every Mongol rider had three more behind him. [C08]
- `5:17.0` S07-06 **BRUN**: "Last biscuit. Half each, and don't argue."
- `5:22.0` S07-07 **PETIT**: "Sergeant, what do they eat out there?"
- `5:26.0` S07-08 **BRUN**: "Us, if we're slow."
- `5:30.0` S07-09 **PETIT**: "Then you keep the half, Sergeant."
- `5:34.0` S07-10 NARRATOR: Each night, the French ate a little less.
- `5:38.0` S07-11 NARRATOR: Foragers who wandered off did not come back. [I03]
- `5:42.0` S07-12 NARRATOR: And Napoleon could not find his battle. [C04]

### S08

- `5:46.0` S08-01 (The scout who lost his horse.)
- `5:50.0` S08-02 **BAYAN**: "Great Khan. My horse is dead. An iron ball. I ran."
- `5:56.0` S08-03 **GENGHIS**: "You ran back to tell me the truth?"
- `6:01.0` S08-04 (Yes.)
- `6:04.0` S08-05 **GENGHIS**: "Then you are worth more than the horse. Give him two."
- `6:10.0` S08-06 (The scout cannot believe it.)
- `6:13.0` S08-07 **SUBUTAI**: "Their iron balls fly farther than our arrows."
- `6:18.0` S08-08 **GENGHIS**: "Then we don't stand where they land."
- `6:23.0` S08-09 **GENGHIS**: "What do they eat?"
- `6:27.0` S08-10 **BARS**: "Bread, Khan. From wagons. Many wagons, very few sheep."
- `6:33.0` S08-11 (Out in the grass, his scouts count the wagons.)
- `6:36.0` S08-12 **GENGHIS**: "Then the wagons are the army."
- `6:41.0` S08-13 (The French march: the fighting column ahead, the wagons falling behind.)
- `6:45.0` S08-14 **SUBUTAI**: "Like at the river this spring. Run nine days. Turn on the tenth."
- `6:52.0` S08-15 **GENGHIS**: "No. This one wants a battle. Give him one."
- `6:57.0` S08-16 (Subutai does not follow.)
- `7:01.0` S08-17 **GENGHIS**: "A small one. Let him win. While he wins, take his wagons."
- `7:07.0` S08-18 (That night, riders slip out of the camp.)
- `7:10.0` S08-19 **GENGHIS**: "And the iron tubes. Bring me those whole."
- `7:15.0` S08-20 **SUBUTAI**: "Whole?"
- `7:19.0` S08-21 **GENGHIS**: "Never break a thing you can learn from."
- `7:25.0` S08-22 (Subutai goes to do it.)

### S09

- `7:29.0` S09-01 NARRATOR: For days, the khan gave Napoleon nothing to hit.
- `7:33.0` S09-02 (Shoot and gone.)
- `7:37.0` S09-03 **BRUN**: "Shoot, run. Shoot, run. Like flies."
- `7:41.0` S09-04 NARRATOR: Every day took them further from the fog. [I01]
- `7:45.0` S09-05 (Napoleon decides.)
- `7:49.0` S09-06 **NAPOLEON**: "If he won't come to me, I'll give him a reason."
- `7:55.0` S09-07 NARRATOR: He set a trap.
- `7:59.0` S09-08 NARRATOR: One division as bait in an open valley. The guns hidden behind the hill.
- `8:04.0` S09-09 NARRATOR: To spring it, he took every fighting man out of camp.
- `8:09.0` S09-10 (Someone watches them hide the guns.)
- `8:12.0` S09-11 NARRATOR: The wagons stayed behind, with a handful of guards.
- `8:16.0` S09-12 (Far from the valley, riders walk their horses along a dry gully.)
- `8:19.0` S09-13 NARRATOR: The khan had been waiting for exactly that.

### S10

- `8:23.0` S10-01 (At last, the khan comes.)
- `8:27.0` S10-02 **NAPOLEON**: "Squares! Form squares!"
- `8:31.0` S10-03 (The square forms.)
- `8:35.0` S10-04 (At the wagons, the drummer hears hooves.)
- `8:38.0` S10-05 (The arrow storm.)
- `8:42.0` S10-06 (Inside the square.)
- `8:45.0` S10-07 **BRUN**: "Close up! Close the gap!"
- `8:49.0` S10-08 **BRUN**: "Steady, lads. They can't stay up there all day."
- `8:54.0` S10-09 (The camp guards fire one ragged volley.)
- `8:57.0` S10-10 (A drum keeps the square together.)
- `9:00.0` S10-11 (The heavy riders form for the charge.)
- `9:04.0` S10-12 **BRUN**: "Front rank, kneel! Second rank, present!"
- `9:08.0` S10-13 **BRUN**: "Hold your fire. Hold."
- `9:12.0` S10-14 (The front rank aims.)
- `9:15.0` S10-15 **BRUN**: "Fire!"
- `9:18.0` S10-16 (The volley at thirty metres.)
- `9:22.0` S10-17 (The charge splits around the square.)
- `9:26.0` S10-18 **BRUN**: "Ha! Like a rock!"
- `9:30.0` S10-19 **NAPOLEON**: "Now. Signal the guns."
- `9:34.0` S10-20 (The hidden guns roll over the crest.)
- `9:38.0` S10-21 **NAPOLEON**: "Canister. Six hundred. Now!"
- `9:42.0` S10-22 (Canister.)
- `9:45.0` S10-23 (Six hundred metres: the Mongol mass breaks.)
- `9:49.0` S10-24 **NAPOLEON**: "That is how Europe learned."
- `9:53.0` S10-25 (Behind the hills, other riders reach the wagons.)
- `9:57.0` S10-26 **PETIT**: "Alarm! Alarm!"
- `10:01.0` S10-27 **MURAT**: "Let me finish them, Sire! Now, while they run!"
- `10:06.0` S10-28 **NAPOLEON**: "No. They want you to chase."
- `10:10.0` S10-29 (Murat hates it.)
- `10:14.0` S10-30 (On the far ridge, the khan watches.)
- `10:18.0` S10-31 **SUBUTAI**: "He is winning, Khan."
- `10:22.0` S10-32 **GENGHIS**: "Let him. He is winning the wrong thing."
- `10:28.0` S10-33 (The khan looks behind the French.)
- `10:32.0` S10-34 **KEMAL**: "Sire. Smoke. Behind us."
- `10:36.0` S10-35 **NAPOLEON**: "What is that?"
- `10:39.0` S10-36 (Black smoke where the camp was.)
- `10:43.0` S10-37 **KEMAL**: "Sire. That is our camp. The wagons."
- `10:47.0` S10-38 (The emperor understands.)

### S11

- `10:51.0` S11-01 (One still frame: the winner on his field.)
- `10:56.0` S11-02 **NAPOLEON**: "We won."
- `11:01.0` S11-03 **BRUN**: "Sire. This is what's left of the bread."
- `11:06.0` S11-04 **NAPOLEON**: "How much is left?"
- `11:10.0` S11-05 **BRUN**: "That, Sire. And the horses."
- `11:14.0` S11-06 (The emperor looks down.)
- `11:18.0` S11-07 **MURAT**: "They never wanted the field, Sire."
- `11:22.0` S11-08 (The wagons, burned to their ribs.)

### S12

- `11:26.0` S12-01 NARRATOR: On paper, it was a victory.
- `11:30.0` S12-02 NARRATOR: The khan left hundreds of riders in that valley. [I03]
- `11:34.0` S12-03 NARRATOR: But he had not lost a single horse he could not replace. [I03]
- `11:39.0` S12-04 NARRATOR: The French had lost what no battle wins back: their food.
- `11:44.0` S12-05 NARRATOR: Within days, they were eating their horses. [I03]
- `11:48.0` S12-06 (The emperor, beaten by a won battle.)
- `11:52.0` S12-07 (An invitation arrives.)
- `11:56.0` S12-08 **MURAT**: "It's a trap, Sire. He'll cut your throat."
- `12:01.0` S12-09 **NAPOLEON**: "Everything here is a trap. I'm going."

### S13

- `12:06.0` S13-01 (The emperor enters the khan's tent.)
- `12:10.0` S13-02 **GENGHIS**: "Your men stand like rocks, and your iron tubes sing."
- `12:16.0` S13-03 **NAPOLEON**: "And still you burned my bread."
- `12:21.0` S13-04 **GENGHIS**: "You came to fight a battle. I came to win a war."
- `12:27.0` S13-05 (The hit lands.)
- `12:31.0` S13-06 **GENGHIS**: "Ride with me. I will give you a tumen. Ten thousand."
- `12:37.0` S13-07 **KEMAL**: "Sire, he means it. He gives armies to strangers."
- `12:42.0` S13-08 **NAPOLEON**: "I have given orders to kings. I do not take them."
- `12:48.0` S13-09 (The interpreter swallows.)
- `12:51.0` S13-10 **GENGHIS**: "Then go back into your fog."
- `12:56.0` S13-11 **GENGHIS**: "I will give you sheep to reach it."
- `13:01.0` S13-12 **NAPOLEON**: "And the price?"
- `13:05.0` S13-13 **GENGHIS**: "Two of your iron tubes. And a gunner to teach mine."
- `13:11.0` S13-14 (The longest silence of his life.)
- `13:15.0` S13-15 **KEMAL**: "Sire. The men are eating grass."
- `13:20.0` S13-16 (Outside, they are.)
- `13:23.0` S13-17 **NAPOLEON**: "Two guns. Not one more."
- `13:29.0` S13-18 (The khan's smile.)
- `13:33.0` S13-19 **GENGHIS**: "You lost nothing today but pride. Pride eats too much grass."
- `13:39.0` S13-20 (Napoleon takes his glove and goes.)
- `13:43.0` S13-21 (The price, paid: two guns go to the khan.)

### S14

- `13:47.0` S14-01 NARRATOR: So: can the man who conquered Europe beat the man who conquered Asia?
- `13:52.0` S14-02 NARRATOR: On a battlefield, yes. A square and a battery broke the charge. [C05, C07]
- `13:57.0` S14-03 NARRATOR: In a campaign, no. The khan never needed the battle. He needed the army's dinner.
- `14:02.0` S14-04 NARRATOR: Then the fog came back, and the army marched into it. [I01]
- `14:06.0` S14-05 NARRATOR: It came out on the road to Moscow, on the fourteenth of September, 1812. [C02]
- `14:10.0` S14-06 NARRATOR: The city was almost empty. The Russian army had pulled out, and Moscow burned. [C12]
- `14:14.0` S14-07 **KEMAL**: "Sire. They burned their own city."
- `14:18.0` S14-08 **NAPOLEON**: "Then they learned it from the khan."
- `14:22.0` S14-09 NARRATOR: The tsar refused to talk. [C12]
- `14:26.0` S14-10 NARRATOR: About five weeks later, Napoleon marched out, and the long retreat began. [C12]
- `14:30.0` S14-11 NARRATOR: How many came home is still argued over. The counts do not agree.

### S15

- `14:34.0` S15-01 (The drumstick stops, again.)
- `14:37.0` S15-02 NARRATOR: He had seen a fire like this before.
- `14:41.0` S15-03 NARRATOR: Five hundred and eighty-nine years earlier. [C21, I01]

### S16

- `14:46.0` S16-01 NARRATOR: On this channel, a hundred geniuses are already waiting for you in the Stone Age. [CH1]
- `14:51.0` S16-02 NARRATOR: Next: a hundred people dropped into the Ice Age. And worlds all the way to the future. [CH1]
- `14:56.0` S16-03 NARRATOR: Subscribe if you don't want to miss them.

Runtime 15:00.0, 214 shots.

### Claims

- **C01** (fact): The first wave of the Grande Armee crossed the Neman on 24 June 1812: more than 450,000 men and over 150,000 horses. Source: https://en.wikipedia.org/wiki/French_invasion_of_Russia
- **C02** (fact): About 100,000 French troops entered Moscow on 14 September 1812. Source: https://en.wikipedia.org/wiki/French_invasion_of_Russia
- **C04** (fact): Napoleon trained as an artillery officer; he preferred the offensive and aimed to destroy the enemy's army in battle. Source: https://en.wikipedia.org/wiki/Napoleon
- **C05** (fact): The Gribeauval 12-pounder: effective range about 900 m with round shot and 600 m with canister; a crew of 15. Source: https://en.wikipedia.org/wiki/Canon_de_12_Gribeauval
- **C06** (fact): The Charleville musket was effective to about 100 yards (90 m), two or three shots a minute. Source: https://en.wikipedia.org/wiki/Charleville_model_1777_musket
- **C07** (fact): Infantry squares held their volley until cavalry was very close; a steady square was rarely broken by cavalry alone, artillery was its main danger. Source: https://en.wikipedia.org/wiki/Infantry_square
- **C08** (fact): Each Mongol soldier kept three or four horses and changed mounts on the march. Source: https://en.wikipedia.org/wiki/Mongol_military_tactics_and_organization
- **C09** (fact): Mongol composite bows: aimed shots at about 150-175 m, ballistic shots up to about 400 m; a quiver of 60 arrows. Source: https://en.wikipedia.org/wiki/Mongol_military_tactics_and_organization
- **C10** (fact): Kalka River, 31 May 1223: the Rus princes had killed the Mongol envoys; Jebe and Subutai drew them on in a feigned retreat of about nine days and destroyed them; captured princes were crushed under a victory platform. Source: https://en.wikipedia.org/wiki/Battle_of_the_Kalka_River
- **C11** (fact): Genghis Khan promoted by merit and loyalty, kept the enemy archer Jebe who had shot his horse and admitted it, and recruited skilled men from defeated enemies. Source: https://en.wikipedia.org/wiki/Genghis_Khan
- **C12** (fact): Moscow was abandoned by Kutuzov's army and burned (Governor Rostopchin); Alexander I refused to negotiate; the French left on 19 October after about five weeks. Source: https://en.wikipedia.org/wiki/French_invasion_of_Russia
- **C13** (fact): Murat was the best cavalry commander of the Grande Armee and showed a total lack of concern for the well-being of his horses. Source: https://en.wikipedia.org/wiki/Joachim_Murat
- **C14** (fact): The Mameluke company of the Imperial Guard served in Russia in 1812 (109 riders on 1 July); its men came from Crimea, Georgia, Circassia, Syria, Egypt and elsewhere. Source: https://en.wikipedia.org/wiki/Mamelukes_of_the_Imperial_Guard
- **C15** (fact): Crimean Tatar and Cuman (the Kipchak of the 13th-century steppe) are both Kipchak Turkic languages. Source: https://en.wikipedia.org/wiki/Kipchak_languages
- **C16** (fact): The army's supply rested on heavy wagons unfit for Russian tracks; foraging along the road fed the rest ('the Army must live by the sword', Colonel Pion). Source: https://en.wikipedia.org/wiki/French_invasion_of_Russia
- **C19** (fact): Genghis Khan stopped his Central Asian campaign in 1221 and was back in Mongolia by 1225; in 1223 he was not on the western steppe. Source: https://en.wikipedia.org/wiki/Genghis_Khan
- **C20** (fact): A tumen was a Mongol unit of 10,000 men. Source: https://en.wikipedia.org/wiki/Mongol_military_tactics_and_organization
- **C21** (fact): 1812 - 1223 = 589 years. Source: arithmetic
- **CH1** (fact): The channel's episodes: 100 geniuses in the Stone Age (on the channel); 100 people dropped into the Ice Age (coming next). Source: CrossWorld Chronicles, the creator's plan 2026-10-24
- **I01** (invented): The fog that drops the army from 1812 into the steppe of 1223, and back. Source: the episode's premise
- **I02** (invented): Genghis Khan himself on the western steppe in 1223 with about two tumens. Source: the episode's premise (against C19)
- **I03** (invented): The skirmish, the valley battle, the burning of the wagons and their numbers. Source: the episode's story
- **I04** (invented): The parley and the two guns left to the khan. Source: the episode's story
