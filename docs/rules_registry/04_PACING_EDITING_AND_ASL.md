# 04. მონტაჟის, ტემპისა და კადრის ხანგრძლივობის რეესტრი (Pacing, Editing & ASL)

წყაროები: [Piko MrBeast ASL Study](https://heypiko.co.uk/library/shows/mrbeast/parents-guide/mrbeast-vs-mrbeast-gaming), [Storyy 2025 YouTube Guide](https://storyy.com/insights/what-is-considered-long-form-content-on-youtube-a-2025-guide), [Optimal Shot Length for AI Motion](https://medium.com/@info_13818/optimal-shot-length-for-ai-generated-motion-based-on-viewer-retention-a7d86e8c8969), [Post-classical editing - Wikipedia](https://en.wikipedia.org/wiki/Post-classical_editing), [Match cut - Wikipedia](https://en.wikipedia.org/wiki/Match_cut).

## კატეგორია 1: ყოველთვის სავალდებულო კანონები (`TIER_1_INVARIANT_MANDATORY` — `FAIL`)
1. **`ED-T1-01` — უწყვეტი 24 FPS დროითი ბადე (`PV-21`):**
   - კადრებს შორის არ დაიშვება არცერთი ცარიელი ფრეიმი (Gap) ან უნებლიე გადაფარვა: `Shot[i].end_frame == Shot[i+1].start_frame`.
2. **`ED-T1-02` — აუდიო-ვიზუალური სინქრონიზაცია (`CF-AV-DURATION-SYNC`):**
   - თითოეული კადრის `target_duration_seconds` პირდაპირ უნდა შეესაბამებოდეს მასზე მიბმული `audio_line_ids`-ის ჯამურ ხანგრძლივობას (`±1.5s` დრამატული პაუზისა და J/L-Cut გადაფარვის ფარგლებში).
3. **`ED-T1-03` — ერთიანი ფილმის გადასვლები (`CF-COHESIVE-TRANSITIONS`):**
   - სეგმენტის შიგნით მოქმედებს მოქმედებაზე ჭრა (`hard_cut` on action) და ხმოვანი გადაფარვა (`j_cut` / `l_cut`), ხოლო სეგმენტებსა და ეპოქებს შორის გადასვლისას — აუდიო-ვიზუალური ხიდი (`j_cut`, `l_cut` ან `cross_dissolve_8f`), რაც გამორიცხავს კოლაჟის/სლაიდშოუს ეფექტს.

## კატეგორია 2: სცენარზე მორგებული კანონზომიერი საზღვრები (`TIER_2_STORY_BOUNDED_DYNAMIC` — `FAIL` საზღვრებს გარეთ)
1. **`ED-T2-01` — კადრის ხანგრძლივობა და აკორდეონის მონტაჟი (`PV-NO-METRONOME-DURATIONS`):**
   - **სცენარი მართავს:** კადრის ზუსტი წამი განისაზღვრება მხოლოდ სცენარით:
     - სწრაფი მოქმედება / პანიკა / დეპეშა: `1.5s – 2.8s`
     - ჩვეულებრივი ნარატიული ნაკადი: `3.0s – 4.8s`
     - მძიმე დრამატული პაუზა / ფართო პანორამა / რუკის აღქმა: `5.0s – 8.8s`
   - **კანონის საზღვრები:** თითოეული კადრი **`[1.2s .. 10.0s]`**; ეპიზოდის საშუალო ASL **`[3.2s .. 6.2s]`**; კადრების ხანგრძლივობის სტანდარტული გადახრა **`Stdev >= 0.65s`** (მეტრონომული თანაბარი კადრები იბლოკება `FAIL`-ით).

## კატეგორია 3: სარეკომენდაციო / თემატიკაზე მორგებული (`TIER_3_THEMATIC_ADVISORY` — `ADVISORY`)
1. **`ED-T3-01` — ჟანრობრივი ტემპის პროფილი:**
   - სამხედრო/საბრძოლო კულმინაციის სეგმენტებში რეკომენდებულია საშუალო ASL-ის ჩამოწევა `2.8s–3.8s`-მდე, ხოლო დიპლომატიურ/ფინანსურ სეგმენტებში — `4.2s–5.8s` დიაპაზონი.
