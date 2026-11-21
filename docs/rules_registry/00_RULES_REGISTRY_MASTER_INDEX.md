# YouTube Historical Docudrama — ერთიანი შეკრული ფილმის (Cohesive Film) 3-დონიანი წესების მასტერ-რეესტრი (`v4.1 / D-126`)

წინამდებარე სისტემა უზრუნველყოფს, რომ AI ვიდეო წარმოებამ შექმნას **არა დაქუცმაცებული „ვიდეო-კოლაჟი“ (სლაიდშოუ)**, არამედ **ერთი მთლიანი, ორგანულად შეკრული კინემატოგრაფიული დოკუდრამა (Cohesive Film)**.

ამისათვის 12-ვე კომპონენტის ყველა წესი დახარისხებულია **3 მკაცრ კატეგორიად** და იმპლემენტირებულია ოთხივე დონეზე (**ტექსტი / სცენარი**, **აუდიო**, **ვიდეო / გამოსახულება**, **მონტაჟი / გადაბმა**):

## წესების 3-დონიანი კლასიფიკაციის კანონი (3-Tier Rule Taxonomy)

| კატეგორია (Tier) | სტატუსი და ვალიდატორის რეაქცია | არსი და დანიშნულება |
| :--- | :--- | :--- |
| **კატეგორია 1: ყოველთვის სავალდებულო / უცვლელი კანონები (`TIER_1_INVARIANT_MANDATORY`)** | **100% სავალდებულო (`FAIL` დარღვევისას)** | წესები, რომლებიც **არასდროს იცვლება** არცერთ სცენაში და კრავს კადრებს ერთ მთლიან ფილმად: მიზეზ-შედეგობრივი ჯაჭვი (`Z1..Z5`), 180°-იანი ღერძის დაცვა, 30°-იანი/მასშტაბის ცვლილება Jump-Cut-ის წინააღმდეგ (`CF-NO-JUMP-CUT`), J-Cut/L-Cut ხმოვანი გადაბმები (`CF-AUDIO-BRIDGE`), უწყვეტი ემბიენსის ფონი (`-24 dB`), 1 ფიზიკური მოქმედება AI ვიდეო კადრში, `WAN-CHAIN-MINUS-5` უწყვეტი გადაბმა `>5.0s` ვიდეო კადრებზე, ერთიანი ქიაროსკუროს სტილი და 35mm Film Grain. |
| **კატეგორია 2: სცენარზე მორგებული კანონზომიერი საზღვრები (`TIER_2_STORY_BOUNDED_DYNAMIC`)** | **სცენარი წყვეტს ზუსტ რიცხვს, კანონი იცავს `[Min, Max, Min_Stdev]` საზღვრებს (`FAIL` საზღვრის ან დისპერსიის დარღვევისას)** | აქ **მთავარი მბრძანებელი არის სცენარი**: კადრის წამების რაოდენობა არ არის ფიქსირებული 5 ან 6 წამი, არამედ ზუსტად იმდენია, რამდენსაც ითხოვს ფრაზა და ემოცია, თუმცა ვალდებულია ჩაჯდეს კინემატოგრაფიულ საზღვრებში (`[1.2s .. 10.0s]`, საშუალო `3.2s..6.2s`, დისპერსია `Stdev >= 0.65s`). იგივე ეხება წინადადების სიგრძეს (`[2..28] სიტყვა`, `Stdev >= 2.8`), სეგმენტის ხანგრძლივობას (`[20s..160s]`, `Stdev >= 3.0s`), ეპიზოდის აუდიო ბალანსს (`65–85%` ნარატორი / `15–35%` დიალოგი) და ვიზუალურ მიქსს (`50–70%` ვიდეო, `20–40%` კოლაჟი, `5–20%` რუკა). |
| **კატეგორია 3: სარეკომენდაციო / თემატიკაზე და სტილისტიკაზე მორგებული (`TIER_3_THEMATIC_ADVISORY`)** | **ადაპტური / სარეკომენდაციო (`ADVISORY / REVIEW`)** | წესები, რომლებიც თავისუფლად ვარირებს ეპიზოდის ეპოქის, თემატიკისა და სცენის ჟანრის მიხედვით: კამერის ვერტიკალური კუთხის არჩევა (`worm_eye_-30` იმპერიული დომინაციისთვის vs `high_angle_30` განადგურებისთვის), განათების დრო (`dawn` ნისლი vs `candlelit` კაბინეტი), მუსიკალური ინსტრუმენტაცია (ჩელო vs სპილენძის ჩასაბერი), `WAN_CONTROL` მოდალობა (`depth` vs `openpose`) და შერჩევითი `WAN_S2V_LIPSYNC` (`>= 8.0s` მონოლოგებზე). |

## როგორ იქმნება „ერთი მთლიანი შეკრული ფილმი“ ნაცვლად „ვიდეო-კოლაჟისა“ (4-დონიანი სინქრონიზაცია)

1. **ტექსტის / სცენარის დონე (`explainer_engine/scripting/story_lint.py` & `cohesive_film_engine.py`):**
   - არცერთი კადრი არ არსებობს იზოლირებულად: ყოველი სეგმენტი ებმის წინას მიზეზ-შედეგობრივი ხიდით (`cause_from_segment_id -> effect_to_segment_id`), ხოლო ყოველი კადრის `action_start_state` აგრძელებს წინა კადრის სივრცით ან დრამატურგიულ იმპულსს.
2. **აუდიოს დონე (`explainer_engine/audio/layers.py` & `sfx_planner.py`):**
   - ვიდეო-კოლაჟში ხმა და კადრი ერთდროულად წყდება. შეკრულ ფილმში მოქმედებს **უწყვეტი ატმოსფერული ფონი (`Ambience Bed -24 dB`)**, რომელიც კადრების შეცვლისას არ წყდება, და **J-Cut / L-Cut ხმოვანი ხიდები (`0.25s–0.60s` გადაფარვა)**, სადაც მომდევნო სცენის ან რეპლიკის ხმა იწყება წინა კადრის დასრულებამდე.
3. **ვიდეოს / გამოსახულების დონე (`explainer_engine/imagegen/turn_pack.py` (v4.3 P3; ადრე gemini_image_engine.py) & `aivideo/wan_optimizer.py`):**
   - 10% რუკები, 30% კოლაჟები და 60% Wan 2.2 ვიდეოები ეყრდნობა ერთსა და იმავე `Reference_Library` ეტალონებს (`style_bible.json`), იცავს 180-გრადუსიან ღერძს და 30-გრადუსიან კონტრასტს მეზობელ კადრებს შორის.
4. **მონტაჟის დონე (`explainer_engine/production/chunked_edit.py` & `finish/grade.py`):**
   - მოქმედებაზე ჭრა (`Match on Action`), `WAN-CHAIN-MINUS-5` (`frame[-5]`) უწყვეტი გადაბმა გრძელ ვიდეო კადრებზე და ერთიანი ფერთა კორექცია + 35mm ფირის მარცვალი (`Film Grain`) კრავს სამივე ვიზუალურ რეჟიმს ერთ განუყოფელ კინოფირად.

## 12 მოდულური წესების რეესტრი:
1. [01_DRAMATURGY_AND_SCRIPTWRITING.md](01_DRAMATURGY_AND_SCRIPTWRITING.md)
2. [02_DIALOGUE_STAGING_AND_SPEECH.md](02_DIALOGUE_STAGING_AND_SPEECH.md)
3. [03_CINEMATOGRAPHY_AND_CAMERA_FRAMING.md](03_CINEMATOGRAPHY_AND_CAMERA_FRAMING.md)
4. [04_PACING_EDITING_AND_ASL.md](04_PACING_EDITING_AND_ASL.md)
5. [05_LIGHTING_AND_CHIAROSCURO_AESTHETICS.md](05_LIGHTING_AND_CHIAROSCURO_AESTHETICS.md)
6. [06_COLLAGE_AND_COMPOSING_STILLS.md](06_COLLAGE_AND_COMPOSING_STILLS.md)
7. [07_TACTILE_RELIEF_MAPS_AND_WAR_TABLES.md](07_TACTILE_RELIEF_MAPS_AND_WAR_TABLES.md)
8. [08_AI_VIDEO_GENERATION_AND_WAN22.md](08_AI_VIDEO_GENERATION_AND_WAN22.md)
9. [09_FOLEY_AND_SPOT_SOUND_EFFECTS.md](09_FOLEY_AND_SPOT_SOUND_EFFECTS.md)
10. [10_MUSIC_AND_AMBIENCE_HIERARCHY.md](10_MUSIC_AND_AMBIENCE_HIERARCHY.md)
11. [11_VOICE_ACTING_AND_LIPSYNC_SPINE.md](11_VOICE_ACTING_AND_LIPSYNC_SPINE.md)
12. [12_FINAL_ASSEMBLY_AND_PACKAGING.md](12_FINAL_ASSEMBLY_AND_PACKAGING.md)
