# როგორ კეთდება რუკები, 2.5D, ფოტოს პრომპტები, ხმა და მონტაჟი (მიმოხილვა, 2026-11-14)

მხოლოდ წაკითხვა: კოდი არ შეცვლილა, არაფერი დარენდერებულა, ფასიანი გამოძახება არ ყოფილა.

**რა წავიკითხე:** `systemic/next-video` (`8e29be8`), ასამბლეის ბრანჩი `claude/project-thread-ahjl5p` (`b004b7c`, აქ არის
Truce 1914-ის სკრიპტი A და ჰოთფიქსები HF-1..HF-7, ჯერ არ არის შერწყმული), რეპორტის ბრანჩი
`claude/project-thread-hqs08m` (`docs/handoffs/motion_audio_report_2026-11-14/REPORT.md`), დემოს ჟურნალები
(`/mnt/project-files/explainer-engine/demo_run_2026-11-13/`), ასამბლეის ბრიფი
(`/mnt/project-files/explainer-engine/demo_truce_1914/ASSEMBLY_BRIEF_v2_final.md`).
**მნიშვნელოვანი:** `episodes/ep_truce_1914` და ჰოთფიქსები `systemic/next-video`-ზე ჯერ არ არის; ქვემოთ "ახლა" ნიშნავს
`ahjl5p`-ის კოდს, თუ სხვა რამ არ წერია.

---

## 0. მთელი ჯაჭვი ერთ სურათად

1. **სკრიპტი** (`episodes/<id>/story/production_script.json`) წერს ყველაფერს: ყოველ კადრს აქვს `route`
   (`map_action` / `still_25d` / `video`, `episode/router.py`), სიგრძე, ტექსტის ხაზები, და მარშრუტის მიხედვით:
   რუკაზე `map_view` + `actions`, 2.5D-ზე `motion_profile` + `motion_imitation`, ვიდეოზე `edit_plan`. ამ ველებს წერს
   სრედის Claude სკრიპტის "editor" ეტაპზე (`.claude/agents/edit-planner.md`, `docs/STORY_ENGINE.md` ცხრილი, ხაზი 429).
2. **ერთი მოვლენების რეზოლვერი** `episode/events.py` (`visual_events`): ყოველ რუკის მოქმედებას და 2.5D მოძრაობას აძლევს id-ს,
   კადრების შუალედს (სიტყვაზე მიბმით) და ერთ ხმის გადაწყვეტილებას. რუკის რენდერერი, 2.5D რენდერერი, ხმის გეგმა და QA ერთსა
   და იმავე სიას კითხულობენ.
3. **რენდერი მარშრუტით** (G7): რუკა `maps/actions.py` + `production/map_clip.py`; 2.5D `production/layers25d.py`;
   ვიდეო `videolane/` (LTX, Modal).
4. **ხმა**: `episode/sound_plan.py` (G4) → `episode/cue_sheet.py` → `audio/stems.py` (G8).
5. **მონტაჟი**: `episode/timing.py` (G6, კადრების სიგრძე ხმოვანი წაკითხვიდან) → `edit/cinematic_transitions.py` →
   `production/assemble.assemble_shot_clips` (G9) → `episode/acceptance.py` (G10).

**რენდერერები არაფერს წყვეტენ თავისით:** რასაც სკრიპტი წერს, იმას აკეთებენ, სიტყვასიტყვით. ამიტომ "სუსტი ზუმი" სკრიპტის
ველებიდან მოდის, არა რენდერერიდან (იხ. ნაწილი 2).

---

## 1. რუკები (`map_action`)

**ვინ წყვეტს:** სკრიპტის editor ეტაპი (სრედის Claude). კოდი მხოლოდ ასრულებს და ამოწმებს.

**სკრიპტის ველები** (Truce, `S02_SH001`):
- `map_view`: `{lon, lat, span_km}` — საწყისი კადრი (ცენტრი და სიგანე კმ-ში).
- `actions[]`: `kind` (`route_arrow`, `front_line`, `spread`, `plume`, `pulse`, `highlight`, `label`, `counter`, `zoom`,
  `split_compare`, `marker_travel`, `supply_line`, `bar_grow`, `progress_bar`, `milestone` …), `at_word` / `until_word`
  (რომელ სიტყვაზე იწყება/მთავრდება), `from` / `to` / `via` (ადგილების id, კოორდინატები `episode.json`-ის `places`-ში),
  `label`, `value` + `unit` + `claim` (ციფრი მხოლოდ claim-ით), `camera` (არასავალდებულო), `event_id`, `audio`.
- `camera_spec.camera_move` (მაგ. `parallax_dolly`) რუკის რენდერერს **არ** იკითხება.

**როგორ იხატება** (`maps/actions.py`):
- ფონი: ასოების გარეშე "ფირფიტა", Natural Earth-ის რელიეფი, ეპიზოდის `map_look` პალიტრა, შრიფტი Inter.
- დრო: `at_word` იხსნება სიტყვების ხერხემალზე (G6-ის შემდეგ გაზომილი, მანამდე შეფასებული). ყოველი მოქმედება
  `ANIM_FRAMES = 18` კადრში (0.75 წმ) "ჩამოდის"; მარშრუტი მარშის ტემპით (ნელა იწყებს, ჩერდება); `via` → Catmull-Rom
  მრუდი (`maps/paths.py`).
- **კამერა:** საწყისი ხედი = `map_view`; მთელ კადრზე ხედი ვიწროვდება `DRIFT = 4 %`-ით; ყოველ მოქმედებას შეუძლია
  სთხოვოს `hold` (ნაგულისხმევი), `push` (ხედი 0.7-მდე), `pull`, `route_pan`, `fly_to`, `scale`, ან `zoom` მოქმედება;
  4 ან მეტი ადგილის მოქმედებაზე ("მკვრივი" რუკა) კამერა მხოლოდ zoom-ზე მოძრაობს.
- **წარწერები:** ადგილის სახელი ჩნდება **მხოლოდ** `label` მოქმედებით (ტექსტი = `label` ან ადგილის სახელი), ფიქსირებული
  წანაცვლებით წერტილის ზემოთ-მარჯვნივ. მარშრუტის ბოლოებს სახელი თავისით არ ეწერება.

**ხმა:** ყოველ მოქმედებას აქვს `audio.decision` (`sfx`, `ui_cue`, `silent_by_design`, …) და კლასი; თუ სკრიპტი არ წერს,
`events.DEFAULTS` აძლევს (მაგ. `route_arrow` → `map_route_draw`, ხანგრძლივობით). Truce: `label` → `map_arrive_click`
(დაწყებაზე), `route_arrow` / `front_line` → `map_route_draw` (მთელ შუალედზე) + ჩამოსვლის კლიკი, `counter` →
`data_rise_texture`. ქვეშ ადგილის ფონი (`loc_western_front_map`: ქარი) და სეგმენტის მუსიკა.

**Truce-ში:** 5 რუკა, 32 წმ 367-დან (8.7 %); კამერის მოძრაობა მხოლოდ ერთში (`S02_SH003`, `fly_to`), დანარჩენი 4 დგას
(4 %-იანი დრიფტი).

**სუსტი წერტილები:**
- კამერა თითქმის ყოველთვის `hold` + 4 % დრიფტი: გაზომილი 0.2-0.5 %/წმ, Gemini-ს ნიმუშზე 1.5-5.1 %/წმ (რეალიზმის აუდიტი 11-12).
- `camera_spec.camera_move` (`parallax_dolly`) რუკაზე არაფერს აკეთებს: ორი ველი, რომლებიც ერთმანეთს არ იცნობენ.
- სახელები მხოლოდ ხელით დაწერილი `label`-ით ჩნდება; წარწერებს შორის გადაფარვის შემოწმება კოდში ვერ ვიპოვე.
- რუკის 8 კანონი (`maps/laws.py`, CMP-01..08, სკილი `cartography`) ამ გზაზე არ ეშვება (მხოლოდ `edit/visual_compensator.py` იძახებს).
- ყოველი მოქმედება ერთნაირად 18 კადრია, რაც არ უნდა იყოს (ისარი, წარწერა, მრიცხველი).
- `map_pin_set`, `map_line_strain`, `map_line_snap` კლასებს ბიბლიოთეკაში ჩანაწერი არ აქვს (KN-03).

---

## 2. 2.5D ფოტოს მოძრაობა (`still_25d`)

**ვინ წყვეტს, რომელ ფოტოს რა მოძრაობა და ეფექტი ერგება:** სრედის Claude სკრიპტის editor ეტაპზე წერს `motion_profile`-ს
და `motion_imitation`-ს, **ფოტოს დახატვამდე**, კადრის ტექსტიდან. შემდეგ Truce-ში clips lane-მა ფოტოების ნახვის შემდეგ
ეფექტები დაამატა და რეგიონები გაზომა (`docs/handoffs/demo_run_2026-11-13/clips_lane/DATA_FIX_PACKAGE.md`,
`apply_data_fix.py`): 24-დან 21 ფოტო BP-185-ზე ვარდებოდა. **რენდერერი არაფერს ირჩევს**: არც მოძრაობას, არც ძალას.

**სკრიპტის ველები:**
- `motion_profile`: `portrait`, `landscape`, `battle`, `architecture`, `document`, `object` — რა მოძრაობები შეიძლება,
  ძალის ჭერი (1.0-1.5), რამდენად მიჰყვება შორი პლანი ახლოს (`layers25d.PROFILES`).
- `motion_imitation[]`: ერთი კამერის მოძრაობა (`push`, `pull`, `truck`, `crane`, `orbit_small`; მაქს. ორი სეგმენტი
  `from_frame`/`to_frame` ან სიტყვებით), `handheld`, `rack_focus`, და ეფექტები ოჯახებით: სინათლე (`fire_flicker`,
  `lightning`, `sun_shaft_drift`), ატმოსფერო (`mist`, `smoke_drift`, `dust`, `embers`, `rain`, `ash_fall`, `cloud_drift`),
  ზედაპირი (`water_shimmer`, `heat_haze`, `foliage_sway`, `cloth_flap`, რეგიონით), სუბიექტი (`subject_sway`), დარტყმა
  (`shake`, მხოლოდ ავტორის მოვლენაზე). თითოეულს: `strength` (0-1.5), `direction`, `easing`, `region`, `event_id`, `audio`.
- `camera_spec.camera_move` (`slow_push_in`, `static`, …) 2.5D რენდერერს **არ** იკითხება.

**როგორ მუშაობს** (`production/layers25d.py`):
- სიღრმე: Depth-Anything V2 Small (`production/depth.py`, უფასო, CPU) → 4 სიღრმის პლანი (k-means) → ახლო პლანის ქვეშ
  ხვრელი ივსება OpenCV Telea-თი (რადიუსი BP-182) → სახე ერთ პლანშია (YuNet; კონტეინერში `tools/yunet` არ არის, ამიტომ
  სახეები არ იზომება).
- **ზუმის რიცხვები:** `push` ძალით 1 = კადრის ზრდა 6 % (`PUSH_SCALE = 0.06`) + ახლო პლანს დამატებით 4 % (`DEPTH_PUSH`).
  ანუ ძალით 0.5 → შორი ×1.03, ახლო ×1.05; ზუსტად ეს გაიზომა რეპორტში.
- `orbit_small`: ახლო პლანი ფოკუსის მიმართ გვერდზე მიდის `5 % × ძალა`-ით, შორი საპირისპიროდ, + 2 % ზუმი; გეიტი
  `near_plane_travel` ზოლი 4-6 % (REVIEW), BP-182 ჭერი 8 %.
- ეფექტები 2D-ია: ხმაურის ფილები და ნიღბები (არა ნამდვილი ნაწილაკები); 2.1 ვერსიიდან ნისლი/კვამლი ცას არ ეკარება (FL-319).
- გეიტები: ≥2 "ცოცხალი" ოჯახი (BP-185, FAIL), ≥3 პლანი, დაფარვა, ნაპრალები, გაყინული მონაკვეთი, ციმციმი, ახლო პლანის სვლა.

**ხმა:** კამერის მოძრაობა ნაგულისხმევად `silent_by_design`; ეფექტის ატმოსფერო ფონს უერთდება
(`sound_plan.AMBIENCE_OF_EFFECT`); `shake`/`lightning` მხოლოდ ავტორის ხმის მოვლენიდან.

**Truce-ში (24 ფოტო, 129.5 წმ, 35 %):** კამერა: `push` 15, `pull` 4, `truck` 3, `crane` 2, **`orbit_small` 0**; ყველა
ერთი სეგმენტით, `handheld` და `rack_focus` არცერთში. ძალა: 0.5 ×13, 0.6 ×4, 0.3 ×4, 0.4 ×2, 0.05 ×1 (ჭერი 1.0-1.5).
`camera_spec` და `motion_imitation` ერთმანეთს არ ემთხვევა: 6 კადრი `static`, მაგრამ `push`; 2 `slow_pull_back`, მაგრამ `crane`.
ეფექტები: `sun_shaft_drift` 11, `fire_flicker` 11, `mist` 9, `smoke_drift` 9, `dust` 3, დანარჩენი 1-2.

**რატომ ჩანს "უბრალო ზუმად" (მიზეზების ჯაჭვი):**
1. სკრიპტი თითქმის ყველგან `push`/`pull`-ს წერს, ძალით 0.3-0.6 → 2-5 % ზუმი (ნიმუში: 7-10 % + 5-8 % პანი).
2. editor ეტაპის გვერდზე (`edit-planner.md`) და სკილებში წესი არ არის, რომელი მოძრაობა, რა ძალით, რამდენი სეგმენტი.
3. მოძრაობა იწერება ფოტოს ნახვამდე; ფოტოს ნახვის შემდეგ დაემატა მხოლოდ ეფექტები, კამერა არავის შეუცვლია.
4. BP-181-ის ზღვარი (`still_move_min` 1.04) კოდში არის (`MOVE_MIN`), მაგრამ არცერთი გეიტი არ იყენებს: 3 %-იანი ზუმი გადის.
5. გვერდითი სვლის გეიტი მხოლოდ truck/crane/orbit-ზე ეშვება; push-ზე სიღრმის ეფექტს (პარალაქსს) არავინ ზომავს.

**სუსტი წერტილები (ერთ ხაზად):**
- რენდერერს ნაგულისხმევი "კარგი" მოძრაობა არ აქვს: ცუდი ველი = ცუდი კადრი, და ეს არსად ჩანს გეიტებში.
- `camera_spec.camera_move` და `motion_imitation` ორი სხვადასხვა ველია ერთსა და იმავეზე, შემოწმების გარეშე.
- ორი სეგმენტის, `handheld`-ის და `orbit_small`-ის შესაძლებლობა არსებობს, მაგრამ სკრიპტი არ იყენებს.
- სახეები არ იზომება (YuNet არ არის), ანუ orbit-ზე სახის დამახინჯებას არავინ დაიჭერს.
- ეფექტები BP-185-ის გასავლელად დაემატა, არა ამბისთვის; მათი სიძლიერე ნაგულისხმევ 1.0-ზეა.

---

## 3. ფოტოს პრომპტები

**ვინ წერს:** სრედის Claude (წესი 15; არა Claude API). ხატავს Gemini.

**ჯაჭვი:**
1. სკრიპტი: `shots[].image_prompt` (`start_frame_prompt`, `negative_prompt`), `camera_spec` (ზომა, კუთხე, აზიმუტი),
   `screen_composition`, `lighting_and_time`, `character_ids`, `location_id`.
2. continuity ბარათები (`shot-continuity-writer`, CT-01..14): `episodes/ep_truce_1914/planning/continuity/<shot>.json` და
   აწყობილი პრომპტი `<shot>.prompts.json`: "Image 1 is the place … Image 2 is the young British private: copy the face, body
   and costume only …", ყოველი ადამიანის ადგილი, მიმართულება, მზერა, კოსტიუმი.
3. ბილდერი (`docs/handoffs/demo_run_2026-11-13/builder/build_api_scene_waves.py`) აწყობს Gemini-ს შეტყობინებას:
   სტილის ბლოკი ("Painterly cinematic storybook illustration …"), რეფერენსები რიგით (სტილი, ადგილი, გმირები), სამყაროს
   ბლოკი (1914-ის სინათლის წყაროები და მასალები), "No text" (`planning/gemini_task/messages/*.md`).
4. პროვაიდერი `config/picture_route.json`: 1) Gemini ჩატი (უფასო), 2) Gemini API `gemini-3.1-flash-image` (1K/2K),
   3) BFL Klein. Truce-ში API-თ გაკეთდა (DV-003).
5. მიღების გეიტები GC-01..17 (`imagegen/turn_pack`), Opus medium-ის სურათების რევიუ, G5.

**სუსტი წერტილები:**
- პრომპტი არ იცის, რომ ფოტო 2.5D-ში იმოძრავებს: იმ პრომპტებში, რაც გავხსენი, არ ითხოვს მკაფიო წინა/შუა/უკანა პლანს ან ჭრისთვის ზედმეტ კიდეს.
- სტილის და სამყაროს გრძელი ბლოკი ყოველ პრომპტში მეორდება; კადრის საკუთარი აზრი ბოლოშია და მოკლეა.
- `camera_spec.camera_move` პრომპტში კამერის აღწერად შედის, მოძრაობა კი სხვა ველიდან მოდის.
- სახის ერთგვაროვნება არ იზომება (KN-10); იდენტური ორკაციანი კადრები განმეორდა (S04_SH009/010/012/014, S05_SH007/009).

---

## 4. ხმა

**მთხრობელი (ElevenLabs):** ერთი ფაილი `audio/narration.wav` (ხმა Odom), Scribe-ის სიტყვების დრო → `audio/timing.json`
(G6). გაწმენდა RC-004 = `audio/narrator_polish.CHAIN`: `volume=-0.6dB, highpass=60, afftdn=nr=8:nf=-50, bass=+12dB@150Hz,
equalizer 300Hz -2dB, alimiter=0.95`; `ahjl5p`-ზე G8 წერს ცალკე `narration_polished.wav` (HF-3), ნედლი რჩება.

**LTX დიალოგი:** კლიპი თვითონ ამბობს თავის ხაზს (VL-07). `videolane/ingest.py` ჭრის Whisper-ის მეტყველების შუალედებით +
BP-187-ის 0.5 წმ "კუდი" (TD-323, TD-327); პიკი -1 dBTP-ზე მაღლა → ჭრილი ჩუმდება (HF-4); `videolane/voice.py` (compose)
თითო კაცზე EQ-ს ათანაბრებს და სიმაღლეს ზომიერად სწევს (TD-320). RC-004-ის პერსონაჟების მსუბუქი ჯაჭვი ამ ფილმში
**არ** გამოიყენება (TD-304, შენი ბარათი ა). ხაზის არმქონე კლიპში შემთხვევითი სიტყვა -12 dB-ზე იდება (გადამრთველი Q2).

**ფონები (beds):** ადგილის მიხედვით: `world_bible.locations[].ambience_bed.classes`; ერთი ფონი ერთ ადგილზე ზედიზედ კადრებისთვის,
ადგილის ცვლაზე J/L ხიდი (`sound_plan.BRIDGE_S`). ეპიზოდის ბიბლიოთეკის ხედი თითო კლასზე ერთ ჩანაწერს ირჩევს (ბარათი ა, HF-7).

**SFX:** მხოლოდ ხილული მოვლენის `audio` გადაწყვეტილებიდან და ავტორის `sound_events`-დან; ნათქვამი სიტყვა მხოლოდ
"კანდიდატია", თავისით ხმას არ აჩენს. წყარო: ბიბლიოთეკა (`assets/audio/library`, HF `sound_library_2026-11-13`) → უფასო →
ElevenLabs (ფასით, შენი სიტყვით). წესები: სახელმძღვანელო `SOUND_INTEGRATION_GUIDE.md`.

**მუსიკა:** სეგმენტის `mood` → `cue_sheet.pick_music` (5 CC BY 4.0 ტრეკი).

**დონეები და ხმამაღლობა:** ერთი მოვლენის RMS `cue_sheet.LEVELS` (spot -26, foley -30, ambience -36, music -32 dBFS);
ხმის ქვეშ ჩაწევა BP-53 (9 dB); BP-52 (მუსიკა 10 LU, ფონი 15 LU ხმის ქვეშ); BP-65 ჭერები; BP-186 (მარშრუტებს შორის ≤3 dB).
საბოლოო: BP-50 = -14 LUFS (ზოლი -15..-13), true peak -1 dBTP. `ahjl5p`-ზე G8 წერს `mix_delivered.wav`, G9 მას აწყობს,
G10 მასტერს ზომავს (HF-2); `systemic/next-video`-ზე ეს ჯერ არ არის.

**სუსტი წერტილები:**
- არავის მოუსმენია (KN-05): ყველა PASS მანქანურია.
- 2.5D-ის თითქმის ყველა მოძრაობა `silent_by_design`: ფოტო-კადრებში მხოლოდ ხმა + ფონი + მუსიკაა.
- მთხრობელის ჯაჭვში +12 dB ბასი 150 Hz-ზე: დიდი მატებაა, ყურით შესამოწმებელი.
- გაწმენდილი მთხრობელის გვერდით LTX-ის ნედლი ხმები: ტემბრის სხვაობის რისკი.
- რუკის ფონი "ქარია" (ადგილის ფონი რუკაზეც მოქმედებს).
- BP-56 ისევ REVIEW (KN-09); ჰოთფიქსები (HF-2..HF-7) მთავარ ბრანჩზე ჯერ არ არის.

---

## 5. ჭრა და აწყობა

**კადრის სიგრძე:** სკრიპტის `target_duration_seconds` გეგმაა; G6 (`episode/timing.py`) ხელახლა ზომავს წაკითხვიდან: ორ
ხაზიან კადრს შორის ჭრა პაუზის შუაშია; უხაზო კადრები პაუზას გეგმის პროპორციით იყოფენ; ხაზის შემდეგ 0.25 წმ ჰაერი
(`PAD_S`); კლიპით ნათქვამი კადრი კლიპის სიგრძით იზომება (VL-07). ვიდეოს შესვლა/გასვლა: `videolane/ingest.edit_points`.

**გადასვლები:** სკრიპტის `transition_out` (Truce: 79 `hard_cut`, 3 `cross_dissolve_8f`, 2 `fade_to_black`).
`systemic/next-video`-ზე კოდი მას **არ კითხულობს** (`edit/cinematic_transitions.py` კადრის ტიპით გეგმავს, FL-406:
7 dissolve, 2 რუკის zoom-through, fade to black საერთოდ არა). `ahjl5p`-ზე HF-1 სკრიპტს მისდევს (dissolve 8 კადრი, fade 24).

**სცენის შიგნით:** `videolane/cuts.py` (VL-11) ჭრას ამოწმებს `edit_plan.continuity_mode`-ით: `continuation`, `coverage`,
`insert`.

**აწყობა:** `production/assemble.assemble_shot_clips`: ნაწილებად (RULE-R1), მოკლე კლიპი უარყოფილია (არ იჭიმება), გრძელი
იჭრება; LTX 1280x704 → 1920x1080 ჭრით, არა შეკუმშვით (HF-6); მასტერი 1920x1080 (TD-313, BP-167-ის 2560x1440-დან გადახვევა).

**გეიტები (`episode/run.py`):**

| გეიტი | ეტაპი | რას ამოწმებს |
|---|---|---|
| G1-G3 | script | სქემა, მარშრუტები, claims, AV კონტრაქტი |
| G4 | sound_plan | ხმის გეგმა, მოვლენები, ფონები, მუსიკა |
| G5 | pictures | ფოტოების მიღება (GC გეიტები) |
| G6 | voice | წაკითხვა, Scribe, კადრების სიგრძე, ანკერები |
| G7 | clips | G7a რუკები, G7b 2.5D, G7c ვიდეო |
| G8 | sound | stems, cue sheet, მიქსის შემოწმება, (ahjl5p) delivered mix |
| G9 | assemble | ნაწილები, ჯოინი |
| G10 | qa | საბოლოო ანგარიში (`acceptance_report.json`) |

**სუსტი წერტილები:**
- `transition_out` მთავარ ბრანჩზე იგნორირებულია, სანამ HF-1 არ შეირწყმება.
- ჭრის რიტმს სკრიპტის გარდა არაფერი განსაზღვრავს; 79 მკვეთრი ჭრიდან არცერთი არ მოწმდება სურათის მოძრაობასთან.
- 2.5D კადრები 2-დან 10 წმ-მდეა, ერთი ნელი მოძრაობით: გრძელ კადრზე ზუმი კიდევ უფრო ნელი ჩანს.
- LTX-ის 1280x704 → 1080p გადიდება სიმკვეთრეს კარგავს.
- G10 შეცდომას ასწორების კლასით წერს, მაგრამ ასწორებს ადამიანი (KN-08).

---

## 6. მოკლედ: სად წყდება რა

| რა | ვინ წყვეტს | სად წერია | ვინ ასრულებს |
|---|---|---|---|
| რუკის ხედი, მოქმედებები, წარწერები | სრედის Claude (editor) | `map_view`, `actions` | `maps/actions.py` |
| 2.5D მოძრაობა, ძალა, ეფექტი | სრედის Claude (editor), შემდეგ clips lane | `motion_profile`, `motion_imitation` | `production/layers25d.py` |
| ფოტოს პრომპტი | სრედის Claude + continuity ბარათები | `image_prompt`, `planning/continuity/` | Gemini |
| ხმის მოვლენა | სრედის Claude (`audio` ყოველ მოვლენაზე) | `events.py` | `sound_plan.py` → `stems.py` |
| ფონი, მუსიკა | ადგილი და სეგმენტის mood | `world_bible`, `segments[].mood` | `cue_sheet.py` |
| კადრის სიგრძე | ხმოვანი წაკითხვა | `audio/timing.json` | `episode/timing.py` |
| გადასვლა | სკრიპტი (ahjl5p-ზე) / კოდი (მთავარზე) | `transition_out` | `cinematic_transitions.py` |
