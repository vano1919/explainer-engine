# 12. საბოლოო აწყობის, შეფუთვისა და YouTube ოპტიმიზაციის რეესტრი (Final Assembly & YouTube Packaging)

წყაროები: [Storyy 2025 Long-Form Guide](https://storyy.com/insights/what-is-considered-long-form-content-on-youtube-a-2025-guide), [OutlierKit YouTube Script & Packaging](https://outlierkit.com/resources/youtube-script-writing/).

## კატეგორია 1: ყოველთვის სავალდებულო კანონები (`TIER_1_INVARIANT_MANDATORY` — `FAIL`)
1. **`PK-T1-01` — 3-წუთიანი ჩანქირებული აწყობა (`G8`, `plan_3min_assembly_chunks`):**
   - 12-წუთიანი ეპიზოდი აუცილებლად იწყობა და მოწმდება ოთხ ~3-წუთიან ნაწილად (`Chunk 1: 0–3m`, `Chunk 2: 3–6m`, `Chunk 3: 6–9m`, `Chunk 4: 9–12m`).
2. **`PK-T1-02` — ერთიანი ვიზუალური და აუდიო შეკვრა (Anti-Collage Finishing Pass):**
   - საბოლოო რენდერზე (`assemble.py` + `finish/grade.py`) 10% რუკებს, 30% კოლაჟებსა და 60% Wan 2.2 ვიდეოებს ედება **ერთიანი ფერთა კორექცია (Chiaroscuro LUT)**, **ერთიანი 35mm ფირის მარცვალი (`8–12% Film Grain`)**, **უწყვეტი ემბიენსი** და **J/L-Cut აუდიო გადასვლები**, რათა სამივე რეჟიმი აღიქმებოდეს ერთ მთლიან ფილმად.
3. **`PK-T1-03` — 9-გეითიანი ვალიდაციის სრული გავლა (`run_all_gate_audits`):**
   - გამოქვეყნებამდე ეპიზოდმა უნდა გაიაროს `G0..G8` ვალიდაცია **`0 FAIL`** შედეგით.

## კატეგორია 2: სცენარზე მორგებული კანონზომიერი საზღვრები (`TIER_2_STORY_BOUNDED_DYNAMIC` — `FAIL` საზღვრებს გარეთ)
1. **`PK-T2-01` — ეპიზოდის მთლიანი ქრონომეტრაჟი და ჩანქების საზღვრები:**
   - **სცენარი მართავს:** თითოეული ჩანქი სრულდება ზუსტად სეგმენტის ბუნებრივ საზღვარზე (და არა წინადადების შუაში).
   - **კანონის საზღვრები:** თითოეული ჩანქი `135s–225s` (სამიზნე `~180s`), მთლიანი ეპიზოდი `660s–780s` (სამიზნე `720s / 12 წთ`).

## კატეგორია 3: სარეკომენდაციო / თემატიკაზე მორგებული (`TIER_3_THEMATIC_ADVISORY` — `ADVISORY`)
1. **`PK-T3-01` — YouTube Title & Thumbnail CTR შეფუთვა:**
   - რეკომენდებულია 3 სათაურის ვარიანტი (პარადოქსული კითხვა, „ხაფანგის/საიდუმლოს“ ფორმულა, კონტრფაქტობრივი შედეგი) და თამბნეილი მაქსიმუმ 3 ვიზუალური ელემენტითა და 3–4 სიტყვით.


### `PK-T1-04` (`PV-NO-FAKE-OFFLINE-RENDER` — Tier 1 Hard Invariant, D-129/D-130)
- მკაცრი Fail-Closed კონტროლი: მოწმდება როგორც რენდერირებული MP4 ფაილი (`>= 2,500 kbps` ვიდეო, `>= 128 kbps` სტერეო აუდიო), ისე `api_render_receipts.json`-ის შიგთავსი.

### `PK-T1-05` (`CF-ENV-CREDENTIAL-HYGIENE` — Tier 1 Hard Invariant, D-128/D-130)
- გასაღებები იტვირთება Google Drive-ის `env_config_v4.env`-დან `env_loader.py`-ის მეშვეობით, URL-ში `?key=`-ის გამოჩენის გარეშე (`x-goog-api-key` ჰედერით).
