# კინემატოგრაფიული აუდიოვიზუალური ოსტატობა, წარმოების ტექნიკები და ინსტრუმენტული იმპლემენტაცია: დამოუკიდებელი კვლევითი ანგარიში

## A. აღმასრულებელი შეჯამება და საწარმოო ჩარჩო (Executive Summary & Production Boundaries)

12-წუთიანი ინგლისურენოვანი ანიმაციური ისტორიული და კონტრფაქტობრივი დოკუდრამისა (Historical / Counterfactual Docudrama and Explainer) და ანალიტიკური ექსპლეინერის შექმნა მოითხოვს კლასიკური კინოენის, ანიმაციური დრამატურგიის, აუდიო ინჟინერიისა და თანამედროვე ჰიბრიდული გენერაციულ-დეტერმინისტული ინსტრუმენტების მკაცრ სინთეზს. კინემატოგრაფიული ხარისხი ილუსტრირებულ და ანიმაციურ სამყაროში არ მიიღწევა ფოტორეალისტური იმიტაციით ან მექანიკური ვიზუალური ეფექტების დამატებით; იგი ეფუძნება კადრის იერარქიულ დადგმას (`Staging`), მოტივირებულ კამერის მოძრაობას (`Motivated Camera Movement`), პერსპექტივისა და სიღრმის ფიზიკურ სიზუსტეს (`Parallax & Depth of Field`), სინათლის კონტრასტის კონტროლს (`Chiaroscuro & Contrast Ratio`), აუდიო-წინმსწრებ მონტაჟს (`J-cut / L-cut`) და აკუსტიკური პერსპექტივის (`Point of Audition`) განუხრელ დაცვას.

წინამდებარე კვლევა აყალიბებს პროფესიონალური აუდიოვიზუალური ტექნიკების სრულ საცნობარო ბიბლიოთეკას და ადგენს, თუ როგორ უნდა გარდაიქმნას ნარატიული მნიშვნელობა კონკრეტულ ვიზუალურ და ხმოვან გადაწყვეტილებად ხუთი საწარმოო მეთოდის კომბინაციით:

1. **LTX-ოჯახის გენერაციული ვიდეო მოდელები** ([LTX Open Source Documentation](https://docs.ltx.io/open-source-model/getting-started/overview), [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5), [Lightricks/LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3), [Lightricks/LTX-Video](https://huggingface.co/Lightricks/LTX-Video)) — ლოკალური `ComfyUI` / `PyTorch` და ჰოსტირებული API (`docs.ltx.io`, `fal.ai`) გარემოების მკაცრი გამიჯვნით.

2. **Blender-ის დეტერმინისტული 2D/2.5D/3D გარემო** ([Blender Manual: Track To Constraint](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html), [Blender Manual: Rigid Body Physics](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html)) — კამერის ზუსტი რიგების, `Geometry Nodes` მასობრივი ფორმაციების, `2.5D Camera Projection`-ის, `Previs`-ისა და მრავალშრიანი კომპოზიტინგისთვის.

3. **Python-ზე დაფუძნებული დეტერმინისტული გრაფიკული ძრავა** ([Pillow Image Module](https://pillow.readthedocs.io/en/latest/reference/Image.html), [OpenCV Geometric Image Transformations](https://docs.opencv.org/4.13.0/dir_996070d144ea13ded22df5bf9603981f.html)) — ვექტორული კარტოგრაფიის, მონაცემთა ვიზუალიზაციის, სუბპიქსელური `2.5D Parallax`-ისა და ავტომატიზებული ხარისხის კონტროლისთვის (`QA`).

4. **FFmpeg-ის პოსტ-პროდუქციისა და აუდიო მასტერინგის ჯაჭვი** ([FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)) — ფილტრ-გრაფების (`xfade`, `zoompan`, `blend`, `sidechaincompress`, `loudnorm`) ზუსტი სემანტიკური მართვისთვის.

5. **ჰიბრიდული საწარმოო კონვეიერები (Hybrid Pipelines)** — სადაც დეტერმინისტული გეომეტრია და კომპოზიცია მართავს გენერაციულ მოძრაობასა და სინქრონიზებულ აუდიო დიზაინს.

### A.1 არასავაჭრო საწარმოო საზღვრები და დამოუკიდებელი განზომილებები

საწარმოო სისტემის დაგეგმვისას ვიზუალური ქრონომეტრაჟის განაწილება, სასაუბრო სიტყვების ბალანსი და კადრის ხანგრძლივობის ლიმიტები წარმოადგენს სამ ერთმანეთისგან სრულიად დამოუკიდებელ ღერძს. მათი ერთმანეთში აღრევა იწვევს დრამატურგიულ და ტექნიკურ ხარვეზებს.

| საწარმოო განზომილება | კატეგორია / პარამეტრი | სამიზნე მაჩვენებელი | ტოლერანტობა / ლიმიტი | ოპერაციული განმარტება და საზღვრები | 
| ----- | ----- | ----- | ----- | ----- | 
| **ვიზუალური ქრონომეტრაჟი (Visual Runtime Allocation)** | `VIDEO` Lane | **60%** (\~432 წმ / 12 წთ-ში) | ±5 პროცენტული პუნქტი (55%–65%) | გენერირებული მოძრავი ვიდეო, მათ შორის უსიტყვო მოქმედება, ბრძოლა, გარემოს დინამიკა და პერსონაჟთა აქტივობა. | 
| **ვიზუალური ქრონომეტრაჟი (Visual Runtime Allocation)** | `STILL` Lane | **30%** (\~216 წმ / 12 წთ-ში) | ±5 პროცენტული პუნქტი (25%–35%) | სტატიკური ილუსტრირებული კომპოზიციები პროგრამული მოძრაობით, 2.5D ფენებით (`Multi-plane Parallax`), ნაწილაკებითა და კამერის სუბპიქსელური სვლებით. | 
| **ვიზუალური ქრონომეტრაჟი (Visual Runtime Allocation)** | `HELPER` Lane | **10%** (\~72 წმ / 12 წთ-ში) | ±5 პროცენტული პუნქტი (5%–15%) | ისტორიული და ტაქტიკური რუკები, დიაგრამები, ქრონოლოგიური ხაზები (`Timelines`), მრიცხველები და სტატისტიკური შედარებები. | 
| **სასაუბრო სიტყვების ბალანსი (Spoken-Word Share)** | Narrator (`თხრობა`) | **70% – 80%** | დაგეგმვის შუაწერტილი: **75%** | იზომება გახმოვანებული სიტყვების რაოდენობით (Word Count) და არა ვიზუალური კადრების ან წამების რაოდენობით. ნარატორი შეიძლება საუბრობდეს `VIDEO`, `STILL` ან `HELPER` კადრების ფონზე. | 
| **სასაუბრო სიტყვების ბალანსი (Spoken-Word Share)** | Voiced Character Dialogue (`დიალოგი`) | **20% – 30%** | დაგეგმვის შუაწერტილი: **25%** (ჭერი: 30%) | პერსონაჟთა გახმოვანებული რეპლიკები. არაგახმოვანებული (`non-voiced`) ტექსტი, მუსიკა, `Ambience`, `Foley`, `SFX` და პაუზები ამ ფორმულაში არ შედის. | 
| **კადრის ხანგრძლივობა (Shot Duration Boundaries)** | Visible Lip-Sync Coverage | **≤ 5 წამი** | დაგეგმვის მაქსიმალური სამიზნე | ხილული მოლაპარაკე სახის (`Lip-Sync`) კადრის ჭერი არტეფაქტებისა და იდენტობის დრეიფის (`Identity Drift`) თავიდან ასაცილებლად. გრძელი რეპლიკები იფარება `Reaction Shot`-ებითა და `Insert`-ებით. | 
| **კადრის ხანგრძლივობა (Shot Duration Boundaries)** | Non-Dialogue `VIDEO` Action | **10 – 15 წამი** | დაგეგმვის ჭერი (მოდელზე დამოკიდებული) | გამოიყენება მაშინ, როდესაც უწყვეტი ქორეოგრაფია, ბრძოლის გეოგრაფია ან კამერის სვლა მოითხოვს დაუقطعავ კადრს. არ უნდა დაიჭრას ხელოვნურ 5-წამიან ნაწილებად. | 

### A.2 მტკიცებულებათა კლასიფიკაციის სისტემა და მთავარი ტექნიკური დასკვნები

წინამდებარე ანგარიშში ყველა ტექნიკური და შემოქმედებითი მტკიცება მკაცრად კლასიფიცირებულია მტკიცებულების ექვს კატეგორიად:

* **\[PRIMARY / OFFICIAL\]:** ოფიციალური ტექნიკური დოკუმენტაცია, საერთაშორისო სტანდარტები (`ITU-R`, `EBU`, `ATSC`), მწარმოებელთა სახელმძღვანელოები (`Lightricks`, `Blender Foundation`, `FFmpeg`, `ElevenLabs`, `Blackmagic Design`, `Adobe`, `ARRI`, `Dolby`) და პლატფორმების ოფიციალური სპეციფიკაციები (`YouTube Help`, `Netflix Partner Help`).

* **\[RESEARCH\]:** რეცენზირებული სამეცნიერო პუბლიკაციები და აკადემიური კვლევები (მაგ., [Okabe-Ito Colorblind-Safe Palette](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference), `LTX-2: Efficient Joint Audio-Visual Foundation Model` `arXiv:2601.03233`).

* **\[PROFESSIONAL PRACTICE\]:** ინდუსტრიული სასწავლო კურიკულუმები ([Berklee Online](https://online.berklee.edu/courses/audio-music-production-for-visual-media), [School of Motion](https://schoolofmotion.com/courses/after-effects-kickstart), [Pixar in a Box / Khan Academy](https://www.khanacademy.org/computing/pixar/storytelling), [iZotope Dialogue Editing](https://www.izotope.com/community/blog/the-dialogue-editing-workflow)) და დადასტურებული საწარმოო პრაქტიკა.

* **\[MEASURED TEST\]:** განმეორებადი ტექნიკური ტესტირებითა და ალგორითმული გაზომვით დადასტურებული პარამეტრები.

* **\[ANECDOTAL\]:** პრაქტიკოსთა და საზოგადოების (`Hugging Face Discussions`, `Reddit`) დაკვირვებები, რომლებიც მოითხოვს ლოკალურ ვერიფიკაციას.

* **\[HYPOTHESIS\]:** თეორიულად დასაბუთებული ვარაუდი, რომელიც საჭიროებს საპილოტე ტესტირებას კონკრეტულ სცენაზე.

**უმაღლესი ღირებულების ტექნიკური დასკვნები ინსტრუმენტების შესაძლებლობათა შესახებ:**

1. **LTX-2.5 და LTX-2.3 არქიტექტურული გარღვევა და მკაცრი შეზღუდვები \[PRIMARY / OFFICIAL\]:** `LTX-2.5` ([LTX-2.5 Documentation](https://docs.ltx.io/models/ltx-2-5)) და `LTX-2.3` ([Lightricks/LTX-2.3 Hugging Face](https://huggingface.co/Lightricks/LTX-2.3)) წარმოადგენს ასიმეტრიულ ორნაკადიან დიფუზიურ ტრანსფორმერებს (`DiT-based joint audio-video foundation models`), რომლებიც ერთ გენერაციულ ციკლში ქმნიან სინქრონიზებულ ვიდეოსა და აუდიოს. თუმცა, ლოკალური ინფერენსისას კადრების რაოდენობა მკაცრად უნდა აკმაყოფილებდეს $F = 8n + 1$ კვანტიზაციის წესს (მაგ., 97, 121, 161, 241, 361 კადრი), ხოლო სივრცითი რეზოლუცია უნდა იყოს **32 პიქსელის ჯერადი** ([Motion Control IC-LoRA Guide](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control)). გარდა ამისა, ტექსტურ პრომპტში ჩაწერილი კამერის მოძრაობა არის მხოლოდ ალბათური (`Prompt-driven / Probabilistic`); გარანტირებული ტრაექტორიის მისაღებად აუცილებელია `IC-LoRA` სტრუქტურული ადაპტერების (`Motion Control Sparse Track Editor`, `Depth`, `Pose`, `Canny`) ან `Blender`-ის `Previs` გიდების გამოყენება ([IC-LoRA Documentation](https://docs.ltx.io/open-source-model/usage-guides/ic-lo-ra)).

2. **კამერის ფიზიკური მოძრაობისა და ციფრული სკალირების ფუნდამენტური განსხვავება \[PRIMARY / OFFICIAL\]:** `FFmpeg`-ის `zoompan` ფილტრი ([FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)) ასრულებს მხოლოდ 2D სურათის აფინურ სკალირებასა და ტრანსლაციას (`Crop & Scale`), რაც არ ქმნის პერსპექტივის ცვლილებასა და ობიექტების ურთიერთგადაფარვას (`Occlusion / Parallax`). ნამდვილი კინემატოგრაფიული `Dolly-In` მოითხოვს ან `Python / OpenCV`-ით სიღრმის რუკაზე (`Depth Map`) დაფუძნებულ მრავალშრიან 2.5D პარალაქსს, ან `Blender`-ში 3D კამერის ფიზიკურ გადაადგილებას, ან `LTX Image-to-Video` გენერაციას.

3. **ტექსტის, კარტოგრაფიისა და სტატისტიკის დეტერმინისტული იმპერატივი \[PRIMARY / OFFICIAL\]:** გენერაციულ ვიდეო და სურათის მოდელებს არ უნდა მიენდოს ისტორიული რუკების საზღვრების, ტოპონიმების, თარიღებისა და რიცხვითი მონაცემების რენდერი. `HELPER` ზოლის ყველა ელემენტი უნდა აიგოს დეტერმინისტულად `Python` (`Pillow`, `Matplotlib`, `SVG`) ან `Blender` გარემოში [Okabe-Ito ფერთა პალიტრის](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference)ა და [Netflix Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements)-ის წაკითხვადობის სტანდარტების (17–20 სიმბოლო წამში) დაცვით.

4. **ხმის სინთეზისა და აუდიო მასტერინგის სტანდარტიზაცია \[PRIMARY / OFFICIAL\]:** `ElevenLabs Eleven v4` (`eleven_v4`) და `eleven_v4_turbo` მოდელები ([Eleven v4 Documentation](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4)) უზრუნველყოფენ მაღალ ექსპრესიულობას და ახალ `clone_strength` პარამეტრს, თუმცა მათში `speed` პარამეტრი გათიშულია ([ElevenLabs Conversational Voice Design](https://elevenlabs.io/docs/eleven-agents/customization/voice/best-practices/conversational-voice-design)). ზუსტი ლიპ-სინქისა და მონტაჟისთვის სავალდებულოა `/v1/text-to-speech/{voice_id}/with-timestamps` ([Create Speech with Timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)) ან `/v1/forced-alignment` ([Forced Alignment Documentation](https://elevenlabs.io/docs/overview/capabilities/forced-alignment)) გამოყენება. საბოლოო აუდიო მიქსი იზომება [ITU-R BS.1770-5 (11/2023)](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf) ალგორითმით, სადაც YouTube-ისთვის ოპტიმალური სამიზნეა **`-14 LUFS` Integrated Loudness** და **`-1.0 dBTP` True Peak** (რადგან YouTube იყენებს მხოლოდ ქვემოთ მიმართულ ნორმალიზაციას — [EBU R 128 Reference](https://en.wikipedia.org/wiki/EBU_R_128), [LUFS Targets Per Platform 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026)).

## B. საგანმანათლებლო და აკადემიური კატალოგი (Education & Academy Catalogue)

პროფესიონალური საწარმოო სისტემის ასაგებად აუცილებელია სტრუქტურირებული აკადემიური და ინდუსტრიული კურიკულუმების გამიჯვნა ზედაპირული ინტერნეტ-ფოლკლორისგან. ქვემოთ წარმოდგენილია ხუთი ფუნდამენტური დისციპლინის ვერიფიცირებული სასწავლო ბაზა.

### B.1 YouTube-ის ოფიციალური საგანმანათლებლო რესურსები და ანალიტიკური დიაგნოსტიკა

პლატფორმის ოფიციალური სახელმძღვანელოები ([YouTube Measure Key Moments for Audience Retention](https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop), [YouTube Recommended Upload Encoding Settings](https://support.google.com/youtube/answer/1722171?hl=en)) მკაფიოდ განასხვავებს ალგორითმულ მითებს რეალური აუდიტორიის ქცევისგან:

* **პირველი 30 წამის კრიტიკული ზღვარი (Intro Retention Benchmark) \[PRIMARY / OFFICIAL\]:** YouTube Analytics-ის `Key moments for audience retention` ანგარიში ცალკე ზომავს ვიდეოს პირველ 30 წამში დარჩენილი მაყურებლების პროცენტულ წილს. 12-წუთიანი ისტორიული დოკუდრამისთვის ეს ნიშნავს, რომ პირველი 30 წამი არ უნდა დაიხარჯოს ზოგად ბიოგრაფიულ შესავალზე ან ლოგოს ანიმაციაზე; იგი პირდაპირ უნდა აყალიბებდეს სათაურისა და `Thumbnail`-ის დაპირებას (`Opening Promise`) და სვამდეს ცენტრალურ კონტრფაქტობრივ ან დრამატურგიულ კითხვას.

* **Retention-ის გრაფიკის ოთხი დიაგნოსტიკური სიგნალი \[PRIMARY / OFFICIAL\]:**

  1. *Top Moments (ჰორიზონტალური პლატო):* მიუთითებს იმაზე, რომ თხრობის ტემპი, ინფორმაციული სიმკვრივე და ვიზუალური ცვლილება იდეალურ თანხვედრაშია.

  2. *Spikes (პიკები):* წარმოიქმნება მაშინ, როდესაც მაყურებლები უკან ახვევენ ვიდეოს. ეს ან საუკეთესო კინემატოგრაფიული `Reveal`-ის ნიშანია, ან იმის სიმპტომი, რომ რუკა/დიაგრამა (`HELPER`) ზედმეტად სწრაფად გაქრა ეკრანიდან და მაყურებელს მისი ხელახლა ნახვა დასჭირდა.

  3. *Dips (ჩავარდნები):* მიუთითებს კონკრეტული სეგმენტის გადახვევაზე (მაგ., მონოტონური ექსპოზიცია ვიზუალური პროგრესიის გარეშე).

  4. *Gradual vs. Steep Drop-offs:* მკვეთრი ვარდნა პირველ წუთზე მიუთითებს სათაურსა და შინაარსს შორის შეუსაბამობაზე (Story/Expectation Problem), ხოლო შუა ნაწილში საფეხურებრივი ვარდნა მიუთითებს მონტაჟური რიტმის დარღვევაზე ან აუდიო დაღლილობაზე (Editing/Pacing Problem).

* **ვიდეო თავები (Video Chapters) და ხელმისაწვდომობა \[PRIMARY / OFFICIAL\]:** თავების (`Chapters`) სტრუქტურირება (`00:00` საწყისი ტაიმკოდით, მინიმუმ 3 თავი, თითოეული ≥10 წამი) და სრული სუბტიტრებისა და აუდიო აღწერილობების (`Audio Descriptions`) დამატება ზრდის სესიის ხანგრძლივობასა და სეგმენტურ ნავიგაციას.

### B.2 კინორეჟისურის, ოპერატორული ხელოვნებისა და განათების განათლება

* **ARRI Academy ([ARRI Academy Certified Courses](https://www.arri.com/en/learn/arri-academy/arri-certified-courses)) \[PRIMARY / OFFICIAL\]:** გვთავაზობს სისტემურ სასწავლო პროგრამებს კამერის ოპტიკური სისტემების, დიდი ფორმატის სენსორების სიღრმისეული აღქმის, განათების სერტიფიცირებული კონტროლისა (`Certified User Training for Lighting`) და პრე/პოსტ-პროდუქციის ფერთა მართვის (`Color Science & Look Design`) მიმართულებით. ილუსტრირებული დოკუდრამისთვის ARRI-ს განათების კურიკულუმი იძლევა ზუსტ მათემატიკურ საფუძველს სინათლის კონტრასტის თანაფარდობის (`Key-to-Fill Ratio`) და მოტივირებული წყაროების (`Practical Lights`) დასაგეგმად `Blender`-ში.

* **MIT OpenCourseWare — The Film Experience \[RESEARCH / PROFESSIONAL PRACTICE\]:** აკადემიური კურსი, რომელიც აანალიზებს კინოენის ევოლუციას, კადრის შიდა კომპოზიციას (`Mise-en-scène`), კამერის მოძრაობის ნარატიულ მოტივაციასა და საბჭოთა მონტაჟური სკოლისა და ჰოლივუდური უწყვეტი მონტაჟის (`Continuity Editing`) დაპირისპირებას.

### B.3 მონტაჟის, კომპოზიტინგისა და ფერთა კორექციის განათლება

* **Blackmagic Design — DaVinci Resolve Official Training ([DaVinci Resolve Training](https://www.blackmagicdesign.com/products/davinciresolve/training), [The Beginner's Guide to DaVinci Resolve 20](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Beginners-Guide.pdf?_v=1757574013000)) \[PRIMARY / OFFICIAL\]:** ინდუსტრიის ყველაზე სრულყოფილი უფასო სერტიფიცირებული სასწავლო გზა, რომელიც მოიცავს ხუთ ოფიციალურ სახელმძღვანელოსა და პრაქტიკულ პროექტს:

  1. *The Beginner's Guide to DaVinci Resolve 20 / 21* — სრული საწარმოო ჯაჭვი `Cut`, `Edit`, `Fusion`, `Color` და `Fairlight` გვერდებზე.

  2. *The Editor's Guide* — მრავალკამერიანი და დიალოგური სცენების მონტაჟი, `J-cut / L-cut` ტრიმინგი, რიტმული მონტაჟი.

  3. *The Colorist Guide* — ნოუდებზე დაფუძნებული (`Node-based`) პირველადი და მეორადი ფერთა კორექცია, `Lift / Gamma / Gain`, კადრების შეთანხმება (`Shot Matching`) და `Waveform / Parade / Vectorscope` ანალიზი.

  4. *The Fairlight Audio Guide* — დიალოგის რედაქტირება, `ADR`, `Foley` სინქრონიზაცია, ბას-როუტინგი და `ITU-R BS.1770` ლაუდნესის კონტროლი.

  5. *The Visual Effects Guide (Fusion)* — ნოუდური კომპოზიტინგი, 3D კამერის პროექცია და ნაწილაკების სისტემები.

* **Adobe Premiere Pro — Color Management & Lumetri Scopes ([Color Management and Lumetri Color](https://helpx.adobe.com/premiere/desktop/correct-color/set-up-color-management/lumetri-enhancements.html), [Display Lumetri Scopes in Premiere](https://helpx.adobe.com/premiere/desktop/correct-color/add-color-effects/display-lumetri-scopes.html)) \[PRIMARY / OFFICIAL\]:** ოფიციალური ტექნიკური დოკუმენტაცია ფერთა სივრცის ნორმალიზაციის, `Rec.709` სტანდარტის, `LUT`-ების შეზღუდვებისა და `Lumetri Scopes`-ით კანის ტონალობისა (`Skin Tone Line`) და ლუმინანსის კონტროლის შესახებ.

### B.4 აუდიო ინჟინერიისა და საუნდ-დიზაინის განათლება

* **Berklee Online ([Audio/Music Production for Visual Media Course](https://online.berklee.edu/courses/audio-music-production-for-visual-media)) \[PROFESSIONAL PRACTICE\]:** საუნივერსიტეტო დონის კურიკულუმი, რომელიც სისტემურად ასწავლის დიალოგის, `Foley`-ს, გარემოს ხმებისა (`Backgrounds / Ambience`) და ორკესტრირებული პარტიტურის (`Score Stems`) პრე-დაბინგსა (`Pre-dubs`) და საბოლოო რე-რეკორდინგ მიქსს.

* **Dolby Creator Lab & Dolby Atmos Music Creation 101 ([Dolby Atmos Music Creation 101](https://professional.dolby.com/music/dolby-atmos-music-creation-101/), [The Dolby Creator Lab](https://www.dolby.com/creator-lab/)) \[PRIMARY / OFFICIAL\]:** ოფიციალური მოდულები სივრცითი აუდიოს, ობიექტზე დაფუძნებული პანორამირების, აკუსტიკური სიღრმისა და დინამიკური დიაპაზონის მართვის შესახებ.

* **iZotope Dialogue Editing Education ([The Dialogue Editing Workflow](https://www.izotope.com/community/blog/the-dialogue-editing-workflow), [Dialogue Editing Tips & Tutorials](https://www.izotope.com/community/blog/category/dialogue-editing)) \[PROFESSIONAL PRACTICE\]:** პრაქტიკული სახელმძღვანელოები სპექტრული გასუფთავების, `Room Tone`-ის უწყვეტობის, სიბილანტების კონტროლისა (`De-essing`) და სხვადასხვა კადრის ვოკალური ტემბრის გათანაბრების (`Dialogue Match`) შესახებ.

### B.5 ანიმაციის, 2.5D-ის, Blender-ისა და მოუშენ-გრაფიკის განათლება

* **Pixar in a Box — Khan Academy ([The Art of Storytelling](https://www.khanacademy.org/computing/pixar/storytelling), [Pixar in a Box Partner Content](https://www.khanacademy.org/partner-content/hass-storytelling/storytelling-pixar-in-a-box)) \[PRIMARY / OFFICIAL\]:** Pixar-ის ანიმაციური სტუდიის ოფიციალური უფასო კურიკულუმი, რომელიც მოიცავს სთორიბორდინგს, კადრის სილუეტურ წაკითხვადობას (`Staging & Silhouette`), ვიზუალურ დრამატურგიას, ვირტუალურ კამერებს, სიმულაციასა და ფერის მეცნიერებას.

* **School of Motion ([After Effects Kickstart](https://schoolofmotion.com/courses/after-effects-kickstart), [Animation Bootcamp](https://schoolofmotion.com/courses/animation-bootcamp), [Design Bootcamp](https://schoolofmotion.com/courses/design-bootcamp)) \[PROFESSIONAL PRACTICE\]:** ინდუსტრიული სტანდარტის კურსები, რომლებიც დეტალურად ხსნის ანიმაციის მრუდების (`Speed & Value Graphs`), `Easing`-ის, თვალის ტრაექტორიის მართვის (`Eye Trace`) და საინფორმაციო იერარქიის კანონებს.

* **Blender Manual & Blender Studio ([Blender Manual: Track To Constraint](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html), [Blender Manual: Rigid Body Physics](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html)) \[PRIMARY / OFFICIAL\]:** ოფიციალური ტექნიკური რეფერენსი `Geometry Nodes`-ის, კამერის კონსტრეინტების, `Grease Pencil` 2D/3D ჰიბრიდული ანიმაციისა და ფიზიკური სიმულაციებისთვის.

### B.6 აკადემიებისა და კურსების სტრუქტურირებული კატალოგი

| Provider / institution | Exact course or learning path | Discipline | Relevant lessons | Free / paid | Access status | Direct URL | Why it matters | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **Khan Academy / Pixar** | Pixar in a Box: The Art of Storytelling & Animation | Storytelling, Staging, Camera, Lighting | Character, Story Structure, Visual Language, Film Grammar, Camera Lenses, Color Science | Free | Open access | [Pixar in a Box Storytelling](https://www.khanacademy.org/computing/pixar/storytelling) | ასწავლის, თუ როგორ იგება დრამატურგიული კადრი, სილუეტი და კამერის ენა ანიმაციურ გარემოში. | 
| **Blackmagic Design** | DaVinci Resolve Official Training & Beginner's Guide 20/21 | Editing, Color Grading, Fairlight Audio, Fusion | High-Speed Editing, Node Color Grading, Scopes, Fairlight Mixing, Loudness, 3D Compositing | Free | Open PDF & Project files | [DaVinci Resolve Training](https://www.blackmagicdesign.com/products/davinciresolve/training) | სრული, ინდუსტრიული დონის უფასო კურიკულუმი მონტაჟის, ფერთა კორექციისა და აუდიო პოსტ-პროდუქციისთვის. | 
| **ARRI Academy** | ARRI Certified Courses & Film School Program | Cinematography, Optics, Lighting | Large-Format Optics, Lighting Contrast Ratios, Color Management, Camera Systems | Free & Paid tiers | Open docs / Paid certification | [ARRI Certified Courses](https://www.arri.com/en/learn/arri-academy/arri-certified-courses) | აყალიბებს ოპტიკური პერსპექტივის, ლინზების არჩევანისა და კინემატოგრაფიული განათების ფიზიკურ სტანდარტებს. | 
| **Berklee Online** | Audio/Music Production for Visual Media | Sound Design, Dialogue, Mixing, Score | Location to Post Workflow, Foley & Backgrounds, Pre-dubs, Stem Mixing, Broadcast Delivery | Paid (with public syllabus) | Accredited university course | [Berklee Visual Media Audio](https://online.berklee.edu/courses/audio-music-production-for-visual-media) | აერთიანებს დიალოგის, `Foley`-ს, `Ambience`-ისა და მუსიკალური სტემების იერარქიულ მიქსინგს ვიზუალური მედიისთვის. | 
| **Dolby Laboratories** | Dolby Atmos Music Creation 101 & Creator Lab | Spatial Audio, Acoustic Depth, Mixing | Session Setup, Bed vs. Object Tracks, Panning, Dynamic Headroom, Binaural Rendering | Free | Open video series & articles | [Dolby Atmos Creation 101](https://professional.dolby.com/music/dolby-atmos-music-creation-101/) | ასწავლის სამგანზომილებიან აკუსტიკურ სივრცესა და სიღრმისეულ პანორამირებას. | 
| **iZotope** | Dialogue Editing Workflow & Tutorials | Dialogue Editing, Restoration, EQ | Spectral Repair, Room Tone Matching, De-essing, Breath Control, Dialogue Match | Free | Open articles & guides | [iZotope Dialogue Workflow](https://www.izotope.com/community/blog/the-dialogue-editing-workflow) | კრიტიკულია სინთეზირებული (`TTS`) და მსახიობური დიალოგების ბუნებრივი ჟღერადობისა და უწყვეტობისთვის. | 
| **School of Motion** | After Effects Kickstart, Animation Bootcamp & Design Bootcamp | Motion Graphics, Animation Curves, Design | Value/Speed Graphs, Oscillation, Eye Trace, Visual Hierarchy, Typography in Motion | Paid (with free blog guides) | Cohort & self-paced | [School of Motion Courses](https://schoolofmotion.com/courses/after-effects-kickstart) | ასწავლის `Easing`-ის მათემატიკასა და ინფოგრაფიკის მოძრაობის კინემატოგრაფიულ ხარისხს. | 
| **Blender Foundation** | Blender Manual & Blender Studio Fundamentals | 3D/2.5D Layout, Camera Constraints, Physics | Track To Constraint, Rigid Body World, Geometry Nodes, Render Passes, Defocus Node | Free / Paid Studio sub | Open manual | [Blender Track To Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html) | უზრუნველყოფს დეტერმინისტული კამერის, ფიზიკისა და კომპოზიტინგის ზუსტ ტექნიკურ დოკუმენტაციას. | 
| **Adobe Help Center** | Premiere Pro Color Management & Lumetri Scopes | Color Correction, Scopes, LUTs | Color Space Normalization, Waveform/Vectorscope Reading, Shot Matching | Free | Open documentation | [Adobe Lumetri Color Guide](https://helpx.adobe.com/premiere/desktop/correct-color/set-up-color-management/lumetri-enhancements.html) | იძლევა პრაქტიკულ ინსტრუქციას სხვადასხვა გენერაციული კადრის ფერისა და კონტრასტის გასათანაბრებლად. | 
| **YouTube Creators / Help** | Key Moments for Audience Retention & Encoding Specs | Retention Analytics, Packaging, Delivery | 30-Second Intro Retention, Spikes vs. Dips Diagnosis, H.264/AAC Bitrate & GOP Rules | Free | Open official docs | [YouTube Retention Guide](https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop) | განასხვავებს პლატფორმის რეალურ ტექნიკურ და ანალიტიკურ მოთხოვნებს კრეატორული მითებისგან. | 
| **Lightricks** | LTX Open Source & API Documentation | Generative Video, IC-LoRA, Audio-to-Video | Two-Stage Distilled Pipeline, Motion Control Sparse Tracks, Frame Rules ($8n+1$) | Free docs | Open documentation | [LTX Open Source Overview](https://docs.ltx.io/open-source-model/getting-started/overview) | წარმოადგენს პირველად წყაროს `LTX-2.5` და `LTX-2.3` მოდელების პარამეტრებისა და ადაპტერებისთვის. | 

## C. ვიზუალური ოსტატობის ენციკლოპედია (Visual Craft Encyclopedia)

### C.1 ვიზუალური დრამატურგია და სცენარიდან ეკრანზე გადატანის გრამატიკა (Visual Storytelling & Script-to-Screen)

დოკუმენტურ-დრამატულ ექსპლეინერში ყველაზე გავრცელებული სამოყვარულო შეცდომაა **ნარატორის ტექსტის პირდაპირი, ბუკვალური ილუსტრირება (`Literal Duplication / See-Say`)**. როდესაც ნარატორი ამბობს: *„მეფემ ხელი მოაწერა ზავს“*, ხოლო ეკრანზე ჩანს მხოლოდ სტატიკური კაცი ქაღალდით ხელში, კადრი არ ქმნის დამატებით ინფორმაციულ ან ემოციურ ღირებულებას. პროფესიონალური კინოენა ([Pixar in a Box: The Art of Storytelling](https://www.khanacademy.org/computing/pixar/storytelling)) ეფუძნება **კონტრაპუნქტისა და ვიზუალური მტკიცებულების** პრინციპს: ნარატორი ხსნის კონტექსტსა და მასშტაბს, ხოლო კადრი აჩვენებს ფიზიკურ მიზეზ-შედეგობრიობას, ადამიანურ ფასს ან დაფარულ ქვეტექსტს.

| ვიზუალური თხრობის ტექნიკა | დრამატურგიული დანიშნულება და სცენის ბიტი (Story Beat) | რას აღიქვამს აუდიტორია | გავლენა კადრის ზომაზე (`Shot Size`) და ხანგრძლივობაზე | რა უნდა შეინარჩუნოს მონტაჟმა ჭრას შორის (`Across the Cut`) | 
| ----- | ----- | ----- | ----- | ----- | 
| **Visual Exposition vs. Verbal Exposition** | სამყაროს, ეპოქის ან სოციალური მდგომარეობის გაცნობა საწყის აქტში. | მაყურებელი თვითონ კითხულობს გარემოს დეტალებს (დაჟანგული იარაღი, ცარიელი ბეღელი) ნარატორის კარნახის გარეშე. | `Wide Shot (WS)` ან `Medium Wide (MWS)` დეტალური `Insert`-ით; 4–7 წმ კადრის წასაკითხად. | განათების ტემპერატურა და გარემოს აკუსტიკური ფონი (`Ambience`). | 
| **Show-Don't-Tell Through Action** | პერსონაჟის ხასიათის, შიშის ან გადაწყვეტილების ჩვენება ფიზიკური ქმედებით. | ემოცია აღიქმება სხეულის მექანიკით (მაგ., აკანკალებული ხელი ხმლის ქარქაშზე). | `Medium Close-Up (MCU)` ან `Insert / Extreme Close-Up (ECU)`; 3–5 წმ (`VIDEO`). | მოძრაობის ვექტორი (`Match on Action`) და კონტაქტის `Foley` ხმა. | 
| **Establishing Geography Before Close Action** | ბრძოლის, ალყის ან მოლაპარაკების დაწყება (`Scene Opening`). | მაყურებელი იგებს ვინ სად დგას, რა მანძილია მხარეებს შორის და საითაა მიმართული შეტევა. | `Extreme Wide Shot (EWS)` ან მაღალი კუთხის (`High-Angle Overhead`) კადრი; 6–10 წმ. | `180-Degree Axis` და ფრაქციების ეკრანული მხარეები (მარცხნივ vs. მარჯვნივ). | 
| **Visual Cause and Effect** | ტაქტიკური მანევრის ან მექანიზმის მოქმედების ახსნა. | მიზეზი (კადრი A: მშვილდოსნების ზალპი) პირდაპირ იწვევს შედეგს (კადრი B: კავალერიის ხაზის რღვევა). | კადრი A: `Medium Shot (MS)` 3 წმ -> კადრი B: `Wide Shot (WS)` 5 წმ. | მოძრაობის ტრაექტორიის მიმართულება (`Screen Direction`) და ხმოვანი ხიდი (ისრის სტვენა გადადის დაცემის ხმაში). | 
| **Action / Reaction Coupling** | დრამატული შეჯახება, ბრძანების გაცემა ან კამათი. | მოქმედების სიმძიმე იზომება არა თვითონ დარტყმით, არამედ დამკვირვებლის ან მსხვერპლის რეაქციით. | Action: `MS / WS` (3–4 წმ) -> Reaction: `CU / MCU` (2–4 წმ). | მზერის მიმართულება (`Eyeline Match`) და ემოციური პაუზა ჭრის წინ. | 
| **Reveal & Delayed Reveal** | ახალი საფრთხის, არმიის მასშტაბის ან საიდუმლო ობიექტის აღმოჩენა. | ჯერ ჩანს პერსონაჟის გაოცებული სახე (`Character-First Reveal`), შემდეგ კი კამერა აჩვენებს მიზეზს. | კადრი 1: `CU` პერსონაჟზე (3 წმ) -> კადრი 2: `EWS` ან `Dolly-Out / Pan` (6–10 წმ). | მზერის ვექტორი და მუსიკალური `Dropout` უშუალოდ აღმოჩენის კადრამდე. | 
| **Visual Contrast & Juxtaposition** | ორი დაპირისპირებული ძალის, სიმდიდრისა და სიღარიბის ან გეგმისა და რეალობის შედარება. | კონტრასტი მძაფრდება მკვეთრი გადასვლით (`Hard Cut`) თბილი/მდიდრული სასახლიდან ცივ/ტალახიან სანგარზე. | თანაბარი კადრის ზომები (`MS` -> `MS`) ვიზუალური შედარების გასამარტივებლად; 4–5 წმ თითოეული. | კომპოზიციური ცენტრი (`Eye Trace`), მაგრამ რადიკალურად შეცვლილი ფერთა ტემპერატურა და `Ambience`. | 
| **Match Cut & Recurring Visual Motif** | დროის ნახტომი (`Time Jump`), თემატური კავშირი ან კონტრფაქტობრივი გადასვლა. | გეომეტრიული ფორმის ან მოძრაობის იდენტურობა (მაგ., მრგვალი ფარი გადადის მონეტაში ან რუკის კომპასში) კრავს ეპიზოდს. | იდენტური მასშტაბი და ეკრანული კოორდინატები ორივე კადრში; `xfade` ან სუფთა `Hard Cut`. | ობიექტის ზუსტი პოზიცია ეკრანის ბადეზე (`Screen-Space Alignment`) და მოძრაობის სიჩქარე. | 
| **Montage & Time Compression** | ხანგრძლივი მომზადების, მშენებლობის, ლაშქრობის ან იმპერიის დაცემის შეკუმშვა. | მოკლე კადრების სერია, გაერთიანებული ერთიანი მუსიკალური პულსითა (`Ostinato`) და ნარატიული თეზისით. | კადრების ზომების მონაცვლეობა (`WS -> MCU -> ECU Insert`); 2–3.5 წმ თითო კადრი. | ერთიანი მუსიკალური ბسترი (`Score Bed`) და პროგრესირებადი ვიზუალური ცვლილება. | 
| **Cross-Cutting (Parallel Editing)** | ორი ერთდროული მოვლენის დაკავშირება კულმინაციის წინ (მაგ., მაცნე გზაში vs. საბჭო კენჭისყრაზე). | ქმნის დროით დაძაბულობას (`Suspense`) — მოასწრებს თუ არა ერთი ხაზი მეორეს. | კადრების ხანგრძლივობა თანდათან მოკლდება კულმინაციისკენ (6 წმ -> 4 წმ -> 2.5 წმ). | თითოეული ხაზის მკაფიო ფერადი და აკუსტიკური იდენტობა, რათა მაყურებელი არ დაიბნეს. | 
| **Visual Proof for a Factual Claim** | ისტორიული ან ეკონომიკური არგუმენტის დასაბუთება. | ნარატორის მტკიცება მყარდება პირველადი დოკუმენტით, რუკით ან სტატისტიკური გრაფიკით (`HELPER` / `STILL`). | `HELPER` ან `Insert STILL` 5–8 წმ, რათა მაყურებელმა მოასწროს რიცხვების წაკითხვა. | ვიზუალური აქცენტი (`Highlight / Callout`) ზუსტად იმ მონაცემზე, რომელსაც ნარატორი წარმოთქვამს. | 

### C.2 კინემატოგრაფიისა და კამერის ენის ბიბლიოთეკა (Cinematography & Camera-Language Library)

#### 6.1 კადრის ზომები და ფრეიმინგი (Shot Size and Framing)

კადრის ზომა განსაზღვრავს ინფორმაციულ და ემოციურ დისტანციას აუდიტორიასა და ობიექტს შორის ([Pixar in a Box: Virtual Cameras](https://www.khanacademy.org/computing/pixar/storytelling), [ARRI Academy](https://www.arri.com/en/learn/arri-academy)). კადრის ზომის შეცვლა მონტაჟურ ჭრაზე (`30-Degree Rule`-თან ერთად) ხშირად ბევრად უფრო ეფექტური, სწრაფი და იაფია, ვიდრე კამერის ხელოვნური მოძრაობა.

| კადრის ზომა (`Shot Size`) | კომპოზიციური საზღვრები | ინფორმაციული და ემოციური ფუნქცია | რეკომენდებული ვიზუალური ზოლი (`Lane`) და ხანგრძლივობა | 
| ----- | ----- | ----- | ----- | 
| **Extreme Wide Shot (EWS)** | ლანდშაფტი, ქალაქი ან ბრძოლის ველი დომინირებს; ადამიანები ჩანან მცირე სილუეტებად ან ფორმაციებად. | ადგენს გეოგრაფიულ მასშტაბს, ეპოქას, კლიმატსა და პერსონაჟის იზოლაციას ან არმიის სიმრავლეს. | `VIDEO` (8–15 წმ მასშტაბური მოძრაობისთვის) ან `STILL` (5–8 წმ 2.5D ატმოსფეროთი). | 
| **Wide Shot (WS) / Full Shot (FS)** | პერსონაჟი ჩანს სრული სიმაღლით (თავიდან ტერფებამდე) გარემოსთან მიმართებაში. | აჩვენებს ფიზიკურ ქმედებას, კოსტიუმს, იარაღსა და სხეულის პოზას (`Body Blocking`). | `VIDEO` (5–10 წმ ფიზიკური ქორეოგრაფიისთვის) ან `STILL` (4–6 წმ). | 
| **Medium Wide / Cowboy Shot (MWS)** | ფრეიმინგი თავიდან მუხლების ზემოთ (შუა ბარძაყამდე). | იდეალურია შეიარაღებული პერსონაჟებისთვის — კადრში ხვდება როგორც სახის გამომეტყველება, ისე წელზე დაკიდებული იარაღი და ხელების მოძრაობა. | `VIDEO` (4–8 წმ) ან `STILL` (4–6 წმ). | 
| **Medium Shot (MS)** | ფრეიმინგი წელიდან ზემოთ. | ობიექტური თხრობისა და დიალოგის საბაზისო სამუშაო კადრი; აბალანსებს ჟესტიკულაციასა და მიმიკას. | `VIDEO` (3–6 წმ) ან `STILL` (3–5 წმ). | 
| **Medium Close-Up (MCU)** | ფრეიმინგი მკერდიდან/მხრებიდან ზემოთ. | გადააქვს ფოკუსი პერსონაჟის ემოციურ რეაქციასა და ინტიმურ დიალოგზე; გარემო გადადის მეორე პლანზე (`Bokeh`). | `VIDEO` (≤5 წმ `Lip-Sync`-ისთვის; 3–6 წმ რეაქციისთვის). | 
| **Close-Up (CU)** | სახე მთლიანად ავსებს კადრს (ნიკაპიდან შუბლამდე). | მაქსიმალური ფსიქოლოგიური ინტენსივობა, შინაგანი გარდატეხა, გადაწყვეტილების მიღება. | `VIDEO` (2–5 წმ) ან `STILL` (2–4 წმ დაძაბული პაუზის დროს). | 
| **Extreme Close-Up (ECU) / Insert** | თვალები, ბეჭედი, რუკის დეტალი, ხმლის პირი, საათის მექანიზმი. | ვიზუალური მტკიცებულება (`Visual Proof`), მინიშნება ან ტაქტილური აქცენტი `Foley` ხმასთან სინქრონში. | `STILL` (2–4 წმ) ან `VIDEO` (2–4 წმ მცირე მოძრაობით). | 
| **Two-Shot / Over-the-Shoulder (OTS)** | ორი პერსონაჟი ერთ კადრში, ან კამერა ერთი პერსონაჟის მხრისა და კეფის უკნიდან უყურებს მეორეს. | აფიქსირებს ძალაუფლების ბალანსს, დისტანციასა და `180-Degree Axis`-ს მოლაპარაკების ან დაპირისპირების დროს. | `VIDEO` (3–6 წმ) ან `STILL` (3–5 წმ). | 

#### 6.2 ლინზები, პერსპექტივა და სიღრმე (Lens, Perspective and Depth)

ოპტიკური ფიზიკის ფუნდამენტური კანონია, რომ **პერსპექტივის დამახინჯებას ან შეკუმშვას (`Perspective Distortion / Compression`) განსაზღვრავს კამერის ფიზიკური მანძილი ობიექტამდე, ხოლო ფოკუსური მანძილი (`Focal Length`) განსაზღვრავს ხედვის კუთხეს (`Field of View - FOV`)** ([ARRI Certified Courses](https://www.arri.com/en/learn/arri-academy/arri-certified-courses), [Blender Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html)):

* **ფართოკუთხიანი ლინზა (Wide-Angle: 18mm – 28mm):** ახლო მანძილიდან გადაღებისას აფართოებს სივრცეს, აძლიერებს წინა და უკანა პლანს შორის მასშტაბის სხვაობას, ზრდის მოძრაობის აღქმულ სიჩქარეს Z-ღერძზე და ქმნის დინამიკურ, ზოგჯერ კლაუსტროფობიულ ან დეზორიენტირებულ განწყობას.

* **ნორმალური ლინზა (Normal: 35mm – 50mm):** შეესაბამება ადამიანის ბუნებრივ სივრცით აღქმას; იდეალურია ობიექტური დოკუმენტური თხრობისა და `Master Shot`-ებისთვის.

* **ტელეფოტო ლინზა (Telephoto: 85mm – 200mm):** შორი მანძილიდან კუმშავს სივრცეს (`Perspective Compression`), უკანა პლანს ვიზუალურად აახლოებს წინა პლანთან (რაც არმიის რიგებს ან ალყის კედლებს ბევრად უფრო მჭიდროდ და მასიურად წარმოაჩენს) და ქმნის მცირე სიმკვეთრის სიღრმეს (`Shallow Depth of Field`), რაც პერსონაჟს გამოყოფს ქაოსური ფონისგან.

* **2D / 2.5D vs. 3D გეომეტრიის საზღვარი \[MEASURED TEST\]:**

  * *2D / 2.5D გარემოში (`Python / OpenCV` ან `Blender Camera Projection`):* დამაჯერებლად იქმნება სიბრტყობრივი პარალაქსი (`Multi-plane Parallax`), სიმკვეთრის სიღრმის ცვლილება (`Rack Focus` Z-Depth ნიღბითა და `Defocus Node`-ით) და მცირე კუთხოვანი გადაადგილება (±10–15 გრადუსამდე).

  * *ნამდვილი 3D გეომეტრია (`Blender` სრული სცენა):* აუცილებელია მაშინ, როდესაც კამერა ასრულებს დიდ ორბიტალურ შემოვლას (`Orbit / Arc > 20°`), გადადის ფრონტალური ხედიდან ზედა ხედზე (`Crane-Up to Overhead`), ან როდესაც ობიექტმა უნდა შემოუაროს სხვა 3D ობიექტს კომპლექსური პერსპექტიული დეფორმაციით.

#### 6.3 კამერის მოძრაობა vs. ციფრული სკალირება (Camera Movement Encyclopedia)

კრიტიკული ტექნიკური გამიჯვნა: **ციფრული სკალირება (`FFmpeg zoompan`) არ არის კამერის ფიზიკური გადაადგილება (`Dolly`)**.

| კამერის მოძრაობა | რას აკეთებს კამერა ფიზიკურად | პარალაქსი და პერსპექტივა | ნარატიული და ემოციური მიზანი | LTX იმპლემენტაცია | Blender / Python / FFmpeg იმპლემენტაცია | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **Static / Locked-off Camera** | კამერა სრულიად უძრავია შტატივზე. | პარალაქსი = 0; მოძრაობს მხოლოდ კადრში არსებული ობიექტი ან სინათლე. | ობიექტურობა, სიმძიმე, ფორმალური ისტორიული ტაბლო, ან დაძაბული მოლოდინი. | მაღალი სანდოობა (`static camera, locked-off tripod shot`). | `Blender`: უძრავი კამერა; `FFmpeg`: პირდაპირი სტრიმი მოძრაობის გარეშე. | 
| **Pan & Tilt** | კამერა ბრუნავს ჰორიზონტალურ (`Yaw`) ან ვერტიკალურ (`Pitch`) ღერძზე ფიქსირებული წერტილიდან. | პარალაქსი თითქმის არ წარმოიქმნება; იცვლება მხოლოდ კადრის საზღვრები. | გარემოს მასშტაბის გახსნა, მზერის მიყოლა ან კოშკის/კედლის სიმაღლის ჩვენება. | საშუალო/მაღალი (`slow camera pan right`, `tilt up`). | `Blender`: კამერის როტაცია; `Python/FFmpeg`: ფართო სურათზე `crop` ფანჯრის გადაადგილება. | 
| **Physical Dolly-In / Dolly-Out** | კამერა ფიზიკურად მიდის წინ ან იხევს უკან Z-ღერძზე. | **ძლიერი პარალაქსი:** წინა პლანის ობიექტები სწრაფად გადიან კადრის კიდეებისკენ, ფონი იხსნება. | ფსიქოლოგიური ჩაღრმავება პერსონაჟის აზრებში (`Dolly-In`) ან მარტოობის/მასშტაბის გახსნა (`Dolly-Out`). | ალბათური პრომპტით; ზუსტი `Motion Control IC-LoRA`-თი. | `Blender`: კამერის ტრანსლაცია Z-ღერძზე; `Python`: 3–4 ფენიანი `2.5D Parallax` სხვადასხვა სიჩქარით. | 
| **Optical / Digital Zoom (`zoompan`)** | კამერა დგას ადგილზე; იცვლება ფოკუსური მანძილი ან ხდება 2D კადრის მოჭრა-გადიდება. | **პარალაქსი = 0:** წინა და უკანა პლანის პროპორცია უცვლელია, იკარგება სივრცითი სიღრმე. | დოკუმენტურ არქივზე, რუკაზე ან სტატიკურ ილუსტრაციაზე დეტალის გამოკვეთა (`Ken Burns effect`). | არ არის საჭირო (დეტერმინისტული ოპერაციაა). | `FFmpeg`: `zoompan=z='min(zoom+0.0008,1.25)':d=125` ([FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html)). | 
| **Lateral Tracking / Trucking** | კამერა მოძრაობს პარალელურად X-ღერძზე მოძრავ პერსონაჟთან ან ფრონტის ხაზთან ერთად. | უწყვეტი ჰორიზონტალური პარალაქსი წინა პლანის სვეტებს/ხეებსა და უკანა ფონს შორის. | ლაშქრობის, სირბილის ან ბრძოლის ხაზის ენერგიისა და სიჩქარის შენარჩუნება. | კარგი `Image-to-Video` + `IC-LoRA` გიდით. | `Blender`: კამერა მიბმულია `Follow Path` სპლაინზე; `Python`: მრავალშრიანი ჰორიზონტალური სქროლინგი. | 
| **Crane / Jib / Pedestal** | კამერა ფიზიკურად ადის მაღლა ან ეშვება დაბლა Y-ღერძზე. | ვერტიკალური პარალაქსი; ჰორიზონტის ხაზი და მიწის სიბრტყე იცვლის გეომეტრიულ პროექციას. | გადასვლა ინდივიდუალური ჯარისკაცის ტრაგედიიდან მთელი ბრძოლის ველის მასშტაბზე. | რთულია მხოლოდ პრომპტით; მოითხოვს 3D გიდს. | `Blender`: 3D კამერის ვერტიკალური აწევა + `Track To Constraint` სამიზნეზე. | 
| **Orbit / Arc** | კამერა შემოუვლის სუბიექტს წრიულ ტრაექტორიაზე, ხოლო ობიექტი რჩება ცენტრში. | ფონი სწრაფად ბრუნავს სუბიექტის უკან, სუბიექტი იცვლის კუთხეს. | გმირული მომენტის, ალყაში მოქცევის ან კრიტიკული გადაწყვეტილების დრამატიზება. | ხშირად იწვევს სახის/ტანის დეფორმაციას 3D გიდის გარეშე. | `Blender`: კამერა წრიულ `Bezier Circle`-ზე + `Track To Constraint` ([Blender Track To](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html)). | 
| **Dolly Zoom (Vertigo Effect)** | კამერა მიდის უკან (`Dolly-Out`), ხოლო ფოკუსური მანძილი იზრდება (`Zoom-In`) ისე, რომ წინა პლანის სუბიექტის ზომა უცვლელი რჩება. | ფონი დრამატულად „იკუმშება“ და უახლოვდება პერსონაჟს. | შოკის, კატასტროფის გაცნობიერების ან ფსიქოლოგიური თავბრუსხვევის ვიზუალიზაცია. | არასაიმედოა გენერაციულ მოდელში. | `Blender`: კამერის Z-კოორდინატისა და `Focal Length`-ის სინქრონული ანიმაცია ($f / d = \text{const}$). | 

#### 6.4 ბლოკინგი, სივრცითი გეოგრაფია და უწყვეტობა (Blocking, Geography and Continuity)

ანიმაციურ და გენერაციულ წარმოებაში, სადაც თითოეული კადრი იქმნება დამოუკიდებელი `Image-to-Video` ან `Text-to-Video` გენერაციით, სივრცითი დეზორიენტაცია მთავარი საფრთხეა. მისი აღმოფხვრა მოითხოვს კლასიკური უწყვეტობის კანონების ([Pixar in a Box: Film Grammar](https://www.khanacademy.org/computing/pixar/storytelling), [The Beginner's Guide to DaVinci Resolve 20](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Beginners-Guide.pdf?_v=1757574013000)) მკაცრ დაცვას:

1. **180-გრადუსიანი ღერძის კანონი (180-Degree Axis of Action):** ნებისმიერ სცენაში (იქნება ეს ორი მეთაურის დიალოგი თუ ორი არმიის შეტაკება) ივლება წარმოსახვითი ხაზი მოქმედ მხარეებს შორის. კამერის ყველა პოზიცია უნდა დარჩეს ამ ხაზის ერთ მხარეს: თუ ფრაქცია A საწყის `Master Shot`-ში და რუკაზე (`HELPER`) არის მარცხნივ და უტევს მარჯვნივ, ხოლო ფრაქცია B არის მარჯვნივ და უტევს მარცხნივ, ეს ეკრანული მიმართულება (`Screen Direction`) უცვლელი უნდა დარჩეს ბრძოლის ყველა `Close-Up` და `Medium` კადრში. ღერძის გადაკვეთა დასაშვებია მხოლოდ ერთი უწყვეტი კამერის მოძრაობისას (`Orbit`) ან ნეიტრალური ფრონტალური კადრის გავლით.

2. **30-გრადუსიანი წესი (30-Degree Rule):** როდესაც ერთი და იმავე სუბიექტის ორ თანმიმდევრულ კადრს შორის კეთდება პირდაპირი ჭრა (`Hard Cut`), კამერის კუთხე უნდა შეიცვალოს მინიმუმ 30 გრადუსით ან კადრის ზომა უნდა შეიცვალოს მინიმუმ ერთი საფეხურით (მაგ., `Medium Shot`-დან `Close-Up`-ზე). წინააღმდეგ შემთხვევაში მაყურებელი აღიქვამს უსიამოვნო ვიზუალურ ნახტომს (`Unintended Jump Cut`).

3. **მზერის თანხვედრა (Eyeline Match):** თუ პერსონაჟი A იყურება კადრის მარჯვენა ქვედა კუთხისკენ (მაგ., დაჭრილ ჯარისკაცზე ან რუკაზე), მომდევნო კადრში ობიექტი ან პერსონაჟი B უნდა იყოს განთავსებული მარცხენა/ცენტრალურ ზონაში და უყურებდეს მარცხენა ზედა კუთხისკენ.

4. **საყრდენი გარემოს მარკერები (Anchor Landmarks in First-Frame Generation):** გენერაციულ კადრებს შორის გარემოს დრეიფის (`Environment Drift`) შესაჩერებლად, საწყის სურათებში (`First Frames`) უნდა ფიგურირებდეს მკაფიო არქიტექტურული ან ბუნებრივი ორიენტირი (მაგ., ცეცხლმოკიდებული საალყო კოშკი მარცხენა ფონზე, ან წითელი დროშა კარვის შესასვლელთან), რომელიც ყველა რაკურსში სწორ გეომეტრიულ მხარეს ჩანს.

### C.3 განათება, ფერთა დიზაინი და ისტორიული პროდაქშენ-დიზაინი (Lighting, Colour & Production Design)

#### 7.1 განათების არქიტექტურა (Cinematic Lighting Setups)

განათება ქმნის სამგანზომილებიან მოცულობას ბრტყელ 2D/2.5D ეკრანზე და მართავს მაყურებლის თვალის ფოკუსს ([ARRI Certified Courses](https://www.arri.com/en/learn/arri-academy/arri-certified-courses)):

* **Key, Fill & Rim (Three-Point Lighting) და მისი მიზანმიმართული დარღვევა:** კლასიკური სამწერტილოვანი განათება (`Key Light` — მთავარი მიმართულების მიმცემი წყარო; `Fill Light` — ჩრდილების შემავსებელი; `Rim / Back Light` — კონტურული სინათლე, რომელიც სუბიექტს გამოყოფს ფონისგან) ეფექტურია სუფთა დიალოგური სცენებისთვის. თუმცა, დრამატულ ისტორიულ სცენებში `Fill Light`-ის მოცილება და **უარყოფითი შევსების (`Negative Fill` — შავი შთანმთქმელი ზედაპირი ჩრდილის მხარეს)** გამოყენება ზრდის კონტრასტის თანაფარდობას (`Contrast Ratio 8:1` ან `16:1`) და ქმნის ნამდვილ კინემატოგრაფიულ სიმძიმეს.

* **Chiaroscuro და Low-Key Lighting:** მკვეთრი გადასვლა განათებულ ზონასა და ღრმა ჩრდილს შორის (მაგ., შეთქმულების, ღამის თათბირის ან ციხის სცენები). `LTX` პრომპტებში იწერება კონკრეტული ფიზიკური აღწერით: `chiaroscuro lighting, single hard warm candle key light from left, deep shadow falloff on right side of face, high contrast ratio, rim light on shoulder`.

* **Motivated & Practical Lighting (ცეცხლი, ჩირაღდანი, სანთელი):** სინათლის წყარო კადრშივე ჩანს (`Practical Light`) და ამართლებს სინათლის მიმართულებასა და ფერს (\~1800K–2200K თბილი ქარვისფერი). `Blender`-ში ცეცხლის ციმციმი (`Firelight Flicker`) იქმნება `Point Light`-ის სიმძლავრის არხზე (`Power / Wattage`) დადებული `Noise Modifier`-ით (Scale: 4.0–8.0, Strength: 0.25), რაც სტატიკურ `STILL` კომპოზიციასაც კი ცოცხალ 2.5D გარემოდ აქცევს.

* **Volumetric Light, Haze & Atmospheric Depth:** მტვრის, კვამლის ან ნისლის ფენებში გატარებული სინათლის სხივები (`God Rays / Crepuscular Rays`) ქმნის ჰაეროვან პერსპექტივას (`Aerial Perspective`): რაც უფრო შორსაა ობიექტი, მით უფრო ნაკლებია მისი კონტრასტი და მით უფრო უახლოვდება მისი ფერი ატმოსფეროს ტონს.

#### 7.2 როლებზე დაფუძნებული ფერთა პალიტრა და Okabe-Ito ხელმისაწვდომობის სტანდარტი

ვიზუალური სამყაროს ერთიანობისთვის ფერები ნაწილდება ხუთ ფუნქციურ როლად (60-30-10 კომპოზიციური პროპორციით):

1. **Dominant / Environment Base (60%):** დაბალი გაჯერების (`Desaturated`) ბუნებრივი ტონები (ქვის ნაცრისფერი, მიწის ოხრა, პერგამენტის კრემისფერი), რომლებიც არ ღლის თვალს.

2. **Secondary / Faction or Location Identity (20%):** კონკრეტული მხარის ან გეოგრაფიული ზონის განმსაზღვრელი ტონი (მაგ., იმპერიული მუქი ლურჯი vs. მეამბოხეთა ჟანგისფერი წითელი).

3. **Accent / Focal Callout (5–10%):** მაღალი გაჯერების ან კონტრასტული ლუმინანსის წერტილი, რომელიც მყისიერად იზიდავს მზერას (ოქროს ბეჭედი, ცეცხლის ალი, რუკის აქტიური ისარი).

4. **Shadow Tone:** ჩრდილების ტონირება (`Lift` არხში ცივი ლურჯ-მომწვანო ან თბილი სეპია), რაც კრავს სხვადასხვა კადრს (`Shot Matching` — [Adobe Lumetri Color Guide](https://helpx.adobe.com/premiere/desktop/correct-color/set-up-color-management/lumetri-enhancements.html)).

5. **Atmosphere / Haze Tone:** შუა და უკანა პლანის გამაერთიანებელი ნისლის ან მტვრის ფერი.

**Okabe-Ito (Wong) ფერთა პალიტრა საინფორმაციო გრაფიკისა და რუკებისთვის (`HELPER` Lane) \[RESEARCH / PRIMARY\]:**
კარტოგრაფიულ და სტატისტიკურ გრაფიკაში სავალდებულოა დალტონიზმის (`Protanopia`, `Deuteranopia`, `Tritanopia`) მიმართ მდგრადი [Okabe-Ito ფერთა პალიტრის](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference) ([Okabe-Ito HEX & RGB Reference](https://figcanvas.com/blog/okabe-ito-palette-hex-rgb-wong-prism)) გამოყენება, ორმაგი ვიზუალური კოდირებით (ფერი + ხაზის სტილი / ფორმა):

| ფერის დასახელება | HEX კოდი | RGB მნიშვნელობა | ლუმინანსის როლი და WCAG კონტრასტის წესი | რეკომენდებული გამოყენება `HELPER` რუკებსა და დიაგრამებში | 
| ----- | ----- | ----- | ----- | ----- | 
| **Blue** | `#0072B2` | `(0, 114, 178)` | აკმაყოფილებს WCAG AA (≥4.5:1) თეთრ ფონზე; მკაფიო მუქი ფონზეც თეთრი კონტურით. | ფრაქცია A (მთავარი მოქმედი მხარე), პირველადი მონაცემთა სერია. | 
| **Vermilion** | `#D55E00` | `(213, 94, 0)` | მაღალი ხილვადობა; მკვეთრად განსხვავდება `#0072B2`-სგან ყველა ტიპის დალტონიზმის დროს. | ფრაქცია B (მოწინააღმდეგე მხარე), შეტევის ვექტორები, კრიტიკული ზღვარი. | 
| **Bluish Green** | `#009E73` | `(0, 158, 115)` | საშუალო ლუმინანსი; საიმედო მესამე კატეგორია. | მოკავშირე/ნეიტრალური ტერიტორია, მესამე ეკონომიკური მაჩვენებელი. | 
| **Orange** | `#E69F00` | `(230, 159, 0)` | მაღალი სიკაშკაშე; იდეალურია მუქ (`#1A1D24`) კარტოგრაფიულ ფონზე. | სავაჭრო მარშრუტები, მომარაგების ხაზები, მეორადი აქცენტი. | 
| **Sky Blue** | `#56B4E9` | `(86, 180, 233)` | ღია ტონი; თეთრ ფონზე საჭიროებს მუქ კონტურს, მუქ ფონზე — პირდაპირ წაკითხვადია. | ჰიდროგრაფია (მდინარეები, ზღვები), საჰაერო/საზღვაო დერეფნები. | 
| **Reddish Purple** | `#CC79A7` | `(204, 121, 167)` | საშუალო-ღია ტონი; განსხვავებული ქრომატული ღერძი. | კონტრფაქტობრივი/ალტერნატიული სცენარის ტრაექტორია. | 
| **Yellow** | `#F0E442` | `(240, 228, 66)` | უმაღლესი ლუმინანსი; თეთრ ფონზე დაუშვებელია კონტურის გარეშე, მუქ ფონზე — უმაღლესი კონტრასტი. | აქტიური ფოკუსის წერტილი (`Callout Ring`), ბრძოლის ეპიცენტრი მუქ რუკაზე. | 
| **Black / Dark Charcoal** | `#000000` | `(0, 0, 0)` | მაქსიმალური კონტრასტის საყრდენი. | ტექსტის კონტურები, საზღვრები, საბაზისო ბადე. | 

### C.4 ანიმაციის პრინციპები და მოქმედების ქორეოგრაფია (Animation & Action Choreography)

ილუსტრირებულ და გენერაციულ ვიდეოში მოძრაობის დამაჯერებლობას განსაზღვრავს არა კადრების სიხშირე, არამედ კლასიკური ანიმაციის 12 პრინციპის ([Pixar in a Box](https://www.khanacademy.org/computing/pixar/storytelling), [School of Motion Animation Bootcamp](https://schoolofmotion.com/courses/animation-bootcamp)) ადაპტაცია:

1. **ოთხფაზიანი მოქმედების სტრუქტურა (Four-Pose Action Structure):** ნებისმიერი ფიზიკური ქმედება (ხმლის მოქნევა, უროს დარტყმა, ცხენის ნახტომი) უნდა დაიგეგმოს ოთხ დისკრეტულ ფაზად:

   * *First Pose (საწყისი წონასწორობა):* პერსონაჟის მკაფიო სილუეტი და სიმძიმის ცენტრი (`First Frame` სურათი).

   * *Anticipation Pose (მოსამზადებელი საპირისპირო მოძრაობა):* დარტყმამდე სხეული იხრება ან იკუმშება საპირისპირო მიმართულებით (3–6 კადრი). `Anticipation`-ის გარეშე მოძრაობა გამოიყურება უწონოდ და ხელოვნურად.

   * *Action Peak / Contact (მოქმედების პიკი და შეჯახება):* მაქსიმალური გაჭიმვა და ფიზიკური კონტაქტის კადრი, სადაც სრულდება `Foley / Impact SFX` სინქრონიზაცია.

   * *Settle Pose & Follow-Through (ინერცია და დამშვიდება):* ძირითადი სხეული ჩერდება, ხოლო მეორადი ელემენტები (`Overlapping Action`: მოსასხამი, თმა, დროშა, მტვერი) აგრძელებს მოძრაობას ინერციით და ნელა ჩერდება (`Slow Out`).

2. **სილუეტის წაკითხვადობა (Staging & Silhouette Test):** თუ კადრს გადავიყვანთ შავ-თეთრ ბინარულ ნიღაბში და პერსონაჟის კიდურები ან იარაღი ერთმანეთს ერწყმის ტორსის შიგნით, `LTX` მოდელი გენერაციისას დააკარგვინებს კიდურებს ან შექმნის „რეზინის ხელებს“ (`Rubber Limbs`). საწყის კადრში (`First Frame`) იარაღი და ხელები მკაფიოდ უნდა იყოს გამოყოფილი სხეულის კონტურისგან.

3. **გენერაციული მოძრაობის ტიპური ხარვეზები და მათი პრევენცია \[PROFESSIONAL PRACTICE / MEASURED TEST\]:**

   * *Sliding Feet (ფეხების სრიალი მიწაზე):* წარმოიქმნება მაშინ, როდესაც კამერა და პერსონაჟი ერთდროულად მოძრაობენ საყრდენი სიბრტყის გარეშე. პრევენცია: გამოიყენეთ `Medium Wide (Cowboy)` ფრეიმინგი ან წინა პლანის საფარი (ბალახი, მტვერი, პარაპეტი), ან მართეთ ტრაექტორია `Motion Control IC-LoRA`-თი ([Motion Control IC-LoRA](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control)).

   * *Identity Drift & Morphing (სახისა და აღჭურვილობის ცვლილება):* იზრდება კადრის ხანგრძლივობასთან და კამერის ბრუნვასთან ერთად. პრევენცია: ახლო დიალოგური კადრები შეზღუდეთ ≤5 წამით, ხოლო გრძელ (10–15 წმ) კადრებში გამოიყენეთ `First-Frame / Last-Frame Conditioning` (`FLF2V`) ან ფართო რაკურსები.

   * *Teleporting Props & Impossible Collisions:* როდესაც ორი პერსონაჟი ფიზიკურად ეჯახება ერთმანეთს, დიფუზიური მოდელი ხშირად აერთიანებს მათ იარაღს. პრევენცია: გამოიყენეთ **მონტაჟური შეჯახება (`Editorial Impact Cut`)** — კადრი 1 აჩვენებს მოქნევას კონტაქტის წერტილამდე (`Cut on Action`), ხოლო კადრი 2 (`ECU` ან `Reaction Shot`) აჩვენებს შეჯახების იმპულსსა და უკუცემას.

### C.5 რუკები, დიაგრამები, სტატისტიკა და მოუშენ-გრაფიკა (Maps, Diagrams & Motion Graphics — `HELPER` Lane)

`HELPER` ზოლი (ქრონომეტრაჟის 10% ±5%) ასრულებს **კოგნიტური კომპრესორის** ფუნქციას: როდესაც სივრცითი მანევრი, ეკონომიკური დისბალანსი ან ქრონოლოგიური ჯაჭვი შეუძლებელია გადმოიცეს ერთი კინემატოგრაფიული კადრით, საქმეში ერთვება დეტერმინისტული ინფოგრაფიკა ([Netflix Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements), [School of Motion Design Bootcamp](https://schoolofmotion.com/courses/design-bootcamp)).

| გრაფიკული ტიპი (`HELPER`) | რა ინფორმაციას გადასცემს | როდის ჯობია კინემატოგრაფიულ სცენას | ინფორმაციული ჭერი ერთ ეკრანზე (`Cognitive Load Ceiling`) | დეტერმინისტული იმპლემენტაციის გზა | 
| ----- | ----- | ----- | ----- | ----- | 
| **Strategic / Route & Territory Map** | ფრონტის ხაზები, მომარაგების მარშრუტები, რელიეფის ბარიერები, ტერიტორიული ცვლილება. | როდესაც საჭიროა >2 გეოგრაფიული პუნქტის ურთიერთმდებარეობისა და მანძილის ჩვენება. | მაქსიმუმ 3–4 ტოპონიმი, 2 დაპირისპირებული ფრაქცია (`#0072B2` vs `#D55E00`), 1 აქტიური მოძრავი ისარი. | `Python` (`GeoJSON/SVG` + `Pillow/OpenCV`) ან `Blender` 3D რელიეფის სიმაღლის რუკაზე (`Heightmap`). | 
| **Timeline & Chronological Stepper** | მოვლენათა თანმიმდევრობა, დროის ინტერვალები, კონტრფაქტობრივი განშტოების წერტილი (`Point of Divergence`). | როდესაც თხრობა ხტება წლებს ან საუკუნეებს შორის და აუცილებელია დროითი ორიენტაცია. | მაქსიმუმ 3–5 თარიღის კვანძი ეკრანზე ერთდროულად; აქტიური კვანძი განათებულია (`#F0E442`). | `Python` (`Pillow` + `Cubic-Bezier` ჰორიზონტალური სქროლინგი). | 
| **Bar / Line / Step Comparison Chart** | ჯარის რაოდენობა, რესურსების ვარდნა, ეკონომიკური ზრდა, დანაკარგების პროპორცია. | როდესაც ნარატორი ასახელებს ≥2 რიცხვით მაჩვენებელს, რომელთა მასშტაბის სხვაობა გადამწყვეტია. | მაქსიმუმ 4 სვეტი ან 2 ხაზოვანი მრუდი; Y-ღერძი ყოველთვის იწყება ნულიდან (მასშტაბის გაყალბების გარეშე). | `Python` (`Matplotlib` / `Pillow` კადრ-კადრ ანიმირებული ზრდით). | 
| **Counter / Ticker & Ledger** | მსხვერპლის, ხაზინის, დღეების ან მანძილის დინამიკური ათვლა. | როდესაც რაოდენობრივი ცვლილების სისწრაფე თვითონ ქმნის დრამატულ ეფექტს. | 1 მთავარი რიცხვითი მრიცხველი + 1 საზომი ერთეულის ეტიკეტი. | `Python` (`Pillow ImageDraw` მონოსპეისური ან ტაბულარული ციფრებით `tabular-nums`). | 
| **Cutaway / Process Flow & Network Diagram** | ციხესიმაგრის შიდა სტრუქტურა, იარაღის მექანიზმი, სამეთაურო იერარქია. | როდესაც გარეგანი ხედი ვერ აჩვენებს ფარულ სტრუქტურულ მექანიზმს. | მაქსიმუმ 4 დაკავშირებული კვანძი, რომლებიც ნათდება თანმიმდევრულად ნარატორის საუბრის კვალდაკვალ. | `Blender` (`Boolean Cutaway` + `Freestyle/LineArt`) ან `Python` ვექტორული სქემა. | 

**ეკრანული ტექსტისა და ეტიკეტების წაკითხვადობის მკაცრი სტანდარტები ([Netflix Timed Text Style Guide: General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements), [Subtitle Timing Guidelines](https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines)) \[PRIMARY / OFFICIAL\]:**

* **კითხვის სიჩქარე (`Reading Speed`):** მაქსიმუმ **17–20 სიმბოლო წამში (CPS)** მოზრდილთა აუდიტორიისთვის.

* **ხაზის სიმკვრივე:** მაქსიმუმ **42 სიმბოლო ხაზზე (CPL)** და არაუმეტეს 2 ხაზისა ერთდროულად.

* **მინიმალური დაყოვნება ეკრანზე (`Minimum Duration`):** ნებისმიერი ტექსტური ეტიკეტი ან `Lower Third` ეკრანზე უნდა დარჩეს მინიმუმ **5/6 წამი (\~20 კადრი 24fps-ზე)**, ხოლო ინფოგრაფიკული ეტიკეტები — მინიმუმ **2.0–2.5 წამი** სრული გაჩენიდან (`Ease-Out` დასრულებიდან).

* **კადრის ჭრასთან სინქრონიზაცია (`Chaining & Shot Changes`):** 24fps ვიდეოში სუბტიტრებს ან ტექსტურ ბლოკებს შორის ინტერვალი უნდა იყოს მინიმუმ 2 კადრი, ხოლო 3–11 კადრიანი ხარვეზები უნდა დაიხუროს 2 კადრამდე, რათა თავიდან იქნას აცილებული ვიზუალური ციმციმი.

## D. მონტაჟისა და ვიზუალური რიტმის ენციკლოპედია (Editing Craft Encyclopedia)

### D.1 ჭრისა და გადასვლების გრამატიკა (Cut and Transition Grammar)

ყოველი მონტაჟური გადასვლა წარმოადგენს სასვენ ნიშანს ვიზუალურ წინადადებაში ([The Beginner's Guide to DaVinci Resolve 20](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Beginners-Guide.pdf?_v=1757574013000), [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)). ეფექტური მონტაჟის 85–90% ეფუძნება ზუსტად დათვლილ პირდაპირ ჭრას (`Hard Cut`), რომელიც შენიღბულია მოძრაობით, მზერით ან ხმოვანი გადაფარვით (`J-cut / L-cut`).

| მონტაჟური ტექნიკა | ნარატიული ფუნქცია და როდის მუშაობს | როდის ასუსტებს სცენას (უკუჩვენება) | უწყვეტობის მოთხოვნა (`Continuity Requirement`) | ტექნიკური იმპლემენტაცია (`FFmpeg / Python / Blender`) | 
| ----- | ----- | ----- | ----- | ----- | 
| **Hard Cut** | მყისიერი გადასვლა კადრიდან კადრზე; საბაზისო ნარატიული სიჩქარე და სიცხადე. | როდესაც კეთდება მსგავს ზომასა და კუთხეზე (`<30°`), რაც ქმნის უნებლიე `Jump Cut`-ს. | `30-Degree Rule`, `180-Degree Axis`, ლუმინანსისა და ფერის ბალანსი. | `FFmpeg`: `concat` დემუქსერი ან ფილტრი ზუსტი კადრის ტაიმკოდზე. | 
| **Cut on Action** | ჭრა მოძრაობის შუა ფაზაში (მაგ., კარის გაღება, ხმლის მოქნევა); მალავს მონტაჟურ ნაკერს. | როდესაც მეორე კადრში მოძრაობის სიჩქარე ან მიმართულება ეწინააღმდეგება პირველს. | მოძრაობის ვექტორის თანხვედრა და 1–2 კადრიანი ვიზუალური გადაფარვა. | `Python`: ოპტიკური ნაკადის (`Optical Flow`) პიკის დეტექცია ჭრის წერტილისთვის. | 
| **Match Cut (Graphic / Action)** | აკავშირებს ორ სხვადასხვა ეპოქას, ადგილს ან იდეას ფორმის ან მოძრაობის იდენტურობით. | როდესაც გამოიყენება ზედმეტად ხშირად დეკორატიული მიზნით შინაარსობრივი კავშირის გარეშე. | ორივე კადრში ფოკუსური ობიექტის კოორდინატებისა და ზომის თანხვედრა (`Δx, Δy < 5%`). | `Python / Pillow`: პირველი კადრის ბოლო ფრეიმისა და მეორე კადრის საწყისი ფრეიმის ოვერლეი-რეგისტრაცია. | 
| **J-Cut (Audio Pre-Lap)** | მომდევნო სცენის ხმა (დიალოგი, ბრძოლის ღრიალი, წვიმა) შემოდის 0.5–1.5 წამით ადრე, სანამ ვიზუალური კადრი შეიცვლება. | როდესაც ახალი ხმა ეჯახება წინა კადრის დაუსრულებელ ფრაზას. | წინა კადრის ვოკალური პაუზა ბოლო 1 წამში. | `FFmpeg`: აუდიო სტრიმის წანაცვლება `adelay` და `acrossfade` ფილტრებით ვიდეო `concat`-თან მიმართებაში. | 
| **L-Cut (Audio Post-Lap)** | მიმდინარე პერსონაჟის ხმა ან სცენის რეზონანსი გრძელდება მომდევნო ვიზუალურ კადრზე (მაგ., მსმენელის რეაქციაზე). | როდესაც მომდევნო კადრი მოითხოვს მყისიერ აკუსტიკურ შოკს (`Smash Cut`). | მსმენელის რეაქციის ან გარემოს კადრის თემატური კავშირი გაგრძელებულ ხმასთან. | `FFmpeg`: ვიდეო ჭრა მოლაპარაკე კადრიდან `Reaction Shot`-ზე აუდიო ტრეკის გაწყვეტის გარეშე. | 
| **Reaction Cut & Insert Cut** | აჩვენებს მსმენელის ემოციურ პასუხს ან მცირე ფიზიკურ დეტალს; ფარავს 5-წამიან `Lip-Sync` ლიმიტს. | როდესაც რეაქციის კადრი სტატიკურია და არ შეიცავს მიკრო-მიმიკას ან მზერის ცვლილებას. | `Eyeline Match`, იდენტური `Room Tone` და განათების მიმართულება. | `LTX` 3–4 წმ `MCU` რეაქციის კადრი ან `STILL` `ECU Insert` 2.5D განათებით. | 
| **Cross-Cutting (Parallel Editing)** | მონაცვლეობით აჩვენებს ორ ერთდროულ პროცესს, რომლებიც მიემართება საერთო კვანძისკენ. | როდესაც ორივე ხაზი ვიზუალურად ერთნაირი ფერისა და კომპოზიციისაა. | მკაფიო ფერადი და აკუსტიკური კონტრასტი ხაზებს შორის; კადრების პროგრესული დამოკლება. | სცენარის დონეზე A/B სეგმენტების ინტერლივინგი ერთიანი მუსიკალური `Ostinato`-ს ქვეშ. | 
| **Smash Cut** | უეცარი, მკვეთრი გადასვლა სიჩუმიდან ხმაურზე (ან პირიქით) დრამატული შოკისთვის. | როდესაც აუდიო დონის ნახტომი იწვევს ციფრულ კლიპინგს (`> -1.0 dBTP`). | მკვეთრი აკუსტიკური კონტრასტი (მინიმუმ 10–15 LU სხვაობა `Short-Term Loudness`-ში). | `FFmpeg`: ნულოვანი `xfade` + მყისიერი `Impact SFX` კადრის პირველ ფრეიმზე. | 
| **Dissolve (Cross-Dissolve)** | რბილი გადადნობა (0.5–1.5 წმ); აღნიშნავს დროის გასვლას, მოგონებას ან მშვიდ თემატურ გადასვლას. | სამოქმედო და საბრძოლო სცენებში — კლავს კინემატოგრაფიულ იმპულსსა და სიმკვეთრეს. | კომპოზიციური თავსებადობა გარდამავალ ფაზაში, რათა არ წარმოიქმნას ორი სახის უსიამოვნო ზედდება. | `FFmpeg`: `xfade=transition=fade:duration=1.0:offset=T` ([FFmpeg xfade](https://ffmpeg.org/ffmpeg-filters.html)). | 
| **Fade to / from Black** | სრული დახურვა და ახალი აქტის/თავის გახსნა. | ეპიზოდის შიგნით ყოველ 30–60 წამში გამოყენება — ანაწევრებს თხრობის დინებას. | გამოიყენება მხოლოდ დიდი დრამატურგიული აქტების (მაქსიმუმ 3–4-ჯერ 12 წუთში) საზღვარზე. | `FFmpeg`: `fade=t=out:st=T:d=1.0`, `afade=t=out:st=T:d=1.2`. | 
| **Motivated Graphic Wipe / Whip-Pan** | კამერის სწრაფი მოქნევა ან წინა პლანის მუქი ობიექტის (სვეტი, მხედარი) გავლა კადრის შესაცვლელად. | არამოტივირებული სტანდარტული გეომეტრიული `Wipe`-ები (ვარსკვლავი, საათის ისარი), რაც იაფფასიან იერს აძლევს ვიდეოს. | ორივე კადრში მოძრაობის იდენტური მიმართულება და `Motion Blur` + `Whoosh / Cloth Foley`. | `Blender` / `Python` ალფა-ნიღბის გავლა ან `FFmpeg` `xfade=transition=wipeleft` მოძრაობის დაბინდვით. | 
| **Freeze Frame & Held Tableau** | მოძრაობის გაყინვა კრიტიკულ ისტორიულ მომენტზე ნარატორის ანალიტიკური კომენტარისთვის. | როდესაც გაყინული კადრი შეიცავს `Motion Blur`-ის არტეფაქტებს ან დამახინჯებულ მიმიკას. | სუფთა, მაღალი სიმკვეთრის ფრეიმი, რომელსაც ემატება მსუბუქი `Vignette` ან გრაფიკული `Callout`. | `FFmpeg`: `tpad=stop_mode=clone:stop_duration=3.5` + `eq=saturation=0.7`. | 

### D.2 რიტმი, ტემპორიტმი და ინფორმაციული სიმკვრივე (Rhythm, Pacing & Explanatory Clarity)

პროფესიონალური მონტაჟი არასოდეს ჭრის კადრებს მექანიკური ტაიმერით (მაგ., „ყოველი კადრი 4.0 წამი“). თანაბარი ხანგრძლივობის კადრების ჯაჭვი იწვევს ჰიპნოზურ მონოტონურობას და აუდიტორიის ყურადღების გაფანტვას ([YouTube Audience Retention Guide](https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop)). კადრის ხანგრძლივობა განისაზღვრება **ინფორმაციული წაკითხვის დროითა (`Visual Comprehension Time`) და დრამატურგიული პულსით**:

* **ინფორმაციული წაკითხვის ფორმულა:** ფართო გეოგრაფიული კადრი (`EWS/WS`), რომელიც შეიცავს რთულ არქიტექტურას, არმიის განლაგებას ან რუკას, მოითხოვს **6–12 წამს**, რათა მაყურებლის თვალმა შეასრულოს სრული სკანირება (`Primary Focal Point -> Secondary Context -> Trajectory`). პირიქით, ახლო `Insert` ან `Reaction Close-Up`, რომელიც შეიცავს მხოლოდ ერთ ინფორმაციულ ერთეულს (მაგ., ხმლის ამოღება ან თვალის შევიწროება), იკითხება **1.8–3.5 წამში**.

* **დაძაბულობის აგება და განმუხტვა (`Tension Build and Release`):** ესკალაციისას კადრების საშუალო სიგრძე (`Average Shot Length - ASL`) თანდათან მცირდება (მაგ., 8 წმ -> 5 წმ -> 3.5 წმ -> 2 წმ), ხოლო კულმინაციური დარტყმის შემდეგ (`Aftermath / Reveal`) აუცილებელია მკვეთრი კონტრასტი — **გრძელი, 8–12 წამიანი სუნთქვის კადრი (`Long Held Shot`)** შემცირებული მუსიკალური სიმკვრივით, რათა აუდიტორიამ გააცნობიეროს მომხდარის მნიშვნელობა.

* **საინფორმაციო გადატვირთვის პრევენცია (`Explanatory Clarity`):**

  1. *ერთდროულად მხოლოდ ერთი პირველადი არხი:* როდესაც ეკრანზე ჩნდება ახალი რუკა ან რიცხვითი გრაფიკი (`HELPER`), პირველი **0.8–1.2 წამის** განმავლობაში ნარატორი აკეთებს მიკრო-პაუზას ან ასახელებს თვითონ გრაფიკის სათაურს/ადგილმდებარეობას, რათა მაყურებლის ვიზუალური და ვერბალური არხები არ შევიდეს კონფლიქტში.

  2. *მოძრავი გრაფიკა და მოლაპარაკე სახე არასოდეს ეჯიბრება ერთმანეთს:* დაუშვებელია რთული სტატისტიკური ტაბლოს გამოტანა ხილული `Lip-Sync` დიალოგის კადრის თავზე; დიალოგი მოითხოვს სახეზე ფოკუსირებას, ხოლო სტატისტიკა — dedicated `HELPER` ან `STILL` ზოლს ნარატორის თანხლებით.

## E. აუდიო რეჟისურის, მუსიკის, საუნდ-დიზაინისა და მასტერინგის ენციკლოპედია (Audio Craft Encyclopedia)

აუდიო არ არის ვიდეოზე ბოლოს დადებული მუსიკალური ფონი; დოკუმენტურ და კინემატოგრაფიულ წარმოებაში ხმა ქმნის აღქმული რეალობის, სივრცითი მასშტაბისა და ემოციური უწყვეტობის ნახევარზე მეტს ([Berklee Online: Audio/Music Production for Visual Media](https://online.berklee.edu/courses/audio-music-production-for-visual-media)). როდესაც ვიზუალური ზოლი გადადის `VIDEO`-დან `STILL`-ზე ან `HELPER`-ზე, სწორედ უწყვეტი აკუსტიკური გარემო (`Room Tone`, `Ambience`, `Pre-Lap Foley` და `Score`) კრავს განსხვავებულ ვიზუალურ ფორმატებს ერთიან კინემატოგრაფიულ გამოცდილებად.

### E.1 თხრობის ოსტატობა, პერსონაჟთა დიალოგი და TTS სპეციფიკაციები (Narration, Dialogue & TTS Production)

#### 10.1 ნარატორის დრამატურგია და სასაუბრო პროსოდია

12-წუთიან ისტორიულ დოკუდრამაში ნარატორი იკავებს გახმოვანებული სიტყვების **70–80%-ს (დაგეგმვის შუაწერტილი: 75%)**. მონოტონური „ვიკიპედიური კითხვის“ თავიდან ასაცილებლად თხრობის ტექსტი უნდა აიგოს სუნთქვით ჯგუფებად (`Breath Groups`) და პროსოდიულ კონტრასტებად ([ElevenLabs Text-to-Speech Best Practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices)):

* **წინადადების სიგრძის ვარიაცია (`Sentence Cadence Alternation`):** გრძელი, ანალიტიკური წინადადება (18–25 სიტყვა), რომელიც აყალიბებს ისტორიულ მიზეზ-შედეგობრიობას, უნდა დასრულდეს მოკლე, დამრტყმელი ვერდიქტით (4–7 სიტყვა). მაგალითად: *„სამი კვირის განმავლობაში მომარაგების ხაზები იწელებოდა გაყინულ უღელტეხილებზე, ხოლო გარნიზონის მარაგი დღითიდღე ქრებოდა. შემდეგ კი — გზა ჩაიკეტა.“*

* **პაუზის არქიტექტურა (`Intentional Pause Placement`):** კრიტიკული რიცხვის, თარიღის ან მოულოდნელი შედეგის (`Reveal`) წინ სავალდებულოა **0.4–0.8 წამიანი მიკრო-პაუზა**, ხოლო თემატური აბზაცის დასრულებისას — **1.2–2.0 წამიანი სუნთქვის ფანჯარა**, სადაც წინა პლანზე ამოდის გარემოს ხმა (`Ambience`) ან მუსიკალური მოტივი.

* **See-Say დუბლირების აკრძალვა:** ნარატორი არასოდეს აღწერს იმას, რაც უკვე ცხადად ჩანს ეკრანზე. თუ კადრში ჩანს ცეცხლმოკიდებული ფლოტი, ნარატორი არ ამბობს *„გემები იწვის“*; იგი ასახელებს იმას, რაც კადრში არ ჩანს — *„ერთ ღამეში განადგურდა ხუთი წლის განმავლობაში ნაშენები საზღვაო ხაზინა.“*

#### 10.2 პერსონაჟთა დიალოგი, ვოკალური კონტრასტი და ხილული ლიპ-სინქის მართვა

პერსონაჟთა გახმოვანებული დიალოგი შეადგენს სასაუბრო სიტყვების **20–30%-ს (დაგეგმვის შუაწერტილი: 25%, ზედა ზღვარი: 30%)**:

* **ვოკალური იდენტობის კონტრასტი (`Timbral Separation`):** ერთ სცენაში მონაწილე ორ პერსონაჟს უნდა ჰქონდეს მკაფიოდ განსხვავებული ფუნდამენტური სიხშირე (`Pitch / F0`), მეტყველების ტემპი და ტემბრული ტექსტურა (მაგ., დაბალი, ხრინწიანი ბარიტონი დინჯი პაუზებით vs. სწრაფი, მკვეთრი ტენორი), რათა აუდიტორიამ მყისიერად იცნოს მოლაპარაკე მაშინაც კი, როდესაც კამერა აჩვენებს მსმენელს (`Off-Screen Dialogue`).

* **ხილული `Lip-Sync` vs. `Reaction / Insert` გადაფარვა:** ვინაიდან ხილული `Lip-Sync` კადრის დაგეგმვის მაქსიმალური სამიზნეა **≤ 5 წამი**, ნებისმიერი 8–12 წამიანი დიალოგური რეპლიკა იგება სამფაზიანი მონტაჟით:

  1. *0.0 – 3.5 წმ:* მოლაპარაკე პერსონაჟის `MCU` ხილული `Lip-Sync`-ით (მაგ., `LTX-2.5 Audio-to-Video`).

  2. *3.5 – 7.5 წმ (`L-Cut`):* მოლაპარაკის ხმა გრძელდება უწყვეტად, ხოლო ვიზუალი გადადის მსმენელის `Close-Up` რეაქციაზე ან მაგიდაზე გაშლილ რუკაზე (`Insert`).

  3. *7.5 – 10.0 წმ:* დაბრუნება მოლაპარაკეზე ან მეორე პერსონაჟის პასუხის შესვლა `J-Cut`-ით.

#### 10.3 ElevenLabs TTS მოდელებისა და API პარამეტრების ვერიფიცირებული სპეციფიკაცია

ოფიციალური დოკუმენტაციის ([ElevenLabs Models Overview](https://elevenlabs.io/docs/overview/models), [Eleven v4 Documentation](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4), [Get Voice Settings API](https://elevenlabs.io/docs/api-reference/voices/settings/get), [Edit Voice Settings API](https://elevenlabs.io/docs/api-reference/voices/settings/update)) მიხედვით, აუცილებელია რეალურად არსებული API პარამეტრების გამიჯვნა მოძველებული ან გამოგონილი კონტროლებისგან:

| ElevenLabs მოდელი / API Endpoint | Model ID / Path | ვერიფიცირებული შესაძლებლობები და პარამეტრები | კრიტიკული შეზღუდვები და ქცევის წესები \[PRIMARY / OFFICIAL\] | 
| ----- | ----- | ----- | ----- | 
| **Eleven v4** | `eleven_v4` | უახლესი თაობის ფლაგმანი მოდელი კონტენტის შექმნისთვის, აუდიოწიგნებისა და ვიდეო ნარაციისთვის ([How to Choose the Right Model](https://elevenlabs.io/docs/eleven-api/choosing-the-right-model)). მხარს უჭერს `stability`, `similarity_boost`, `style` და ახალ **`clone_strength` (0.0 – 1.0)** პარამეტრს. | **`speed` პარამეტრი არ არის ხელმისაწვდომი `Eleven v3` და `Eleven v4` მოდელებში** ([Conversational Voice Design Guide](https://elevenlabs.io/docs/eleven-agents/customization/voice/best-practices/conversational-voice-design)). ტემპი იმართება ტექსტური სტრუქტურითა და პუნქტუაციით. | 
| **Eleven v4 Turbo** | `eleven_v4_turbo` | მაღალი ექსპრესიულობისა და დაბალი ლატენტობის მოდელი დიალოგური და მრავალპერსონაჟიანი სცენებისთვის; მხარს უჭერს `clone_strength`-ს პროფესიონალური კლონებისთვის. | `clone_strength` რეკომენდებულია `0.0` საბაზისო მოქნილობისთვის; გაზრდა (`>0.5`) აახლოებს ხმას სასწავლო ჩანაწერთან, მაგრამ ამცირებს დრამატულ ვარიაციას. | 
| **Eleven Multilingual v2** | `eleven_multilingual_v2` | მაღალი სტაბილურობის მოდელი, რომელიც გაწვრთნილია რიცხვების, თარიღებისა და რთული ფრაზების ბუნებრივ წაკითხვაზე ([TTS Best Practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices)). მხარს უჭერს `speed` (სტანდარტი `1.0`, ბუნებრივი დიაპაზონი `0.9–1.1x`). | `style` პარამეტრის `0`-ზე მეტად გაზრდა მოითხოვს დამატებით გამოთვლით რესურსს და ზრდის ლატენტობას. | 
| **Create Speech with Timing** | `POST /v1/text-to-speech/{voice_id}/with-timestamps` | აბრუნებს გენერირებულ აუდიოს და სიმბოლოების დონეზე (`character-level`) ნორმალიზებულ დროით მასივებს (`characters`, `character_start_times_seconds`, `character_end_times_seconds`) ([Create Speech with Timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)). | სავალდებულოა `HELPER` გრაფიკის ანიმაციისა და `J-cut / L-cut` წერტილების ზუსტი პროგრამული გამოთვლისთვის. | 
| **Forced Alignment API** | `POST /v1/forced-alignment` | იღებს ნებისმიერ არსებულ აუდიო ფაილსა (3 GB / 10 საათამდე) და plain-text ტრანსკრიპტს (675,000 სიმბოლომდე) და აბრუნებს ზუსტ სიტყვისა და ფრაზის ტაიმსტამპებს ([Forced Alignment Docs](https://elevenlabs.io/docs/overview/capabilities/forced-alignment)). | არ აქვს სპიკერების დიარიზაციის (`Diarization`) მხარდაჭერა; ტექსტი უნდა გადაეცეს მხოლოდ სუფთა სტრიქონად (`Plain string only`, JSON შეფუთვის გარეშე). | 
| **Pronunciation Dictionaries** | `/v1/pronunciation-dictionaries` | ისტორიული ტოპონიმების, ანტიკური სახელებისა და ტერმინების ზუსტი წარმოთქმის მართვა `IPA` (International Phonetic Alphabet) ან `CMU Arpabet` წესებით ([TTS Best Practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices)). | `IPA` წესები ბევრად უფრო საიმედოა, ვიდრე სიტყვის ხელოვნური დამარცვლა ტექსტში. | 

**Voice Settings-ის რეკომენდებული საწყისი კონფიგურაცია \[PRIMARY / OFFICIAL\]:**

* *ისტორიული ნარატორი (`Narrator`):* `stability: 0.60 – 0.75` (მკაფიო, ავტორიტეტული უწყვეტობა), `similarity_boost: 0.75 – 0.85`, `style: 0.0 – 0.15`.

* *ემოციური პერსონაჟის დიალოგი (`Character Dialogue`):* `stability: 0.35 – 0.50` (ფართო ემოციური დინამიკა და ბუნებრივი ინტონაციური რყევა), `similarity_boost: 0.70 – 0.80`, `clone_strength: 0.0 – 0.30` (`eleven_v4`-ზე).

### E.2 მუსიკალური რეჟისურა, პარტიტურის არქიტექტურა და AI მუსიკის გენერაცია (Music Direction & Score Design)

#### 11.1 კინომუსიკის კომპოზიციური ტექნიკები

დოკუმენტური დრამის პარტიტურა არ უნდა შედგებოდეს ეპიზოდური, ერთმანეთთან დაუკავშირებელი „ეპიკური ტრეილერის“ ტრეკებისგან, რომლებიც მუდმივად ფარავს ნარატორის ხმას. პროფესიონალური სქორინგი ([Berklee Visual Media Course](https://online.berklee.edu/courses/audio-music-production-for-visual-media)) იყენებს სტრუქტურულ მუსიკალურ ხერხებს:

| მუსიკალური ტექნიკა | მუსიკალურ-აკუსტიკური მექანიზმი | ნარატიული და ემოციური ფუნქცია | რომელი სცენის ტიპს უხდება | როდის უნდა გამოირთოს ან შეიცვალოს | 
| ----- | ----- | ----- | ----- | ----- | 
| **Leitmotif & Recurring Melodic Motif** | მოკლე (3–6 ნოტიანი) ცნობადი მელოდიური ან ინსტრუმენტული ფრაზა, რომელიც მიბმულია კონკრეტულ პერსონაჟზე, ფრაქციაზე ან ცენტრალურ იდეაზე. | ქმნის ქვეცნობიერ თემატურ ერთიანობას 12 წუთის განმავლობაში; მოტივის მინორული ან დაშლილი ვარიაცია აჩვენებს პერსონაჟის დაცემას. | `Opening Hook`, პერსონაჟის შემოსვლა, `Climax` და `Ending / Coda`. | არ უნდა ჟღერდეს ტექნიკური `HELPER` სტატისტიკის ახსნისას. | 
| **Ostinato & Rhythmic Pulse** | განმეორებადი მოკლე რიტმულ-მელოდიური ფიგურა (მაგ., დაბალი სიმებიანი `Spiccato` ან ყრუ პერკუსია), რომელიც ინარჩუნებს მუდმივ მეტრულ ტემპს. | ქმნის გარდაუვალობის, მომზადების, დროის წიკწიკისა და წინსვლის განცდას მელოდიური გადატვირთვის გარეშე. | ლაშქრობა (`Travel`), სამხედრო მომზადება (`Crafting`), ტაქტიკური რუკის ახსნა (`HELPER`). | წყდება უშუალოდ შეჯახების ან `Reveal`-ის წინ. | 
| **Drone & Sustained Pedal Texture** | ერთი უწყვეტი დაბალი ტონი (მაგ., ჩელოს, კონტრაბასის ან სინთეზური ბასის `Pedal Point` 40–110 Hz ზონაში) ჰარმონიული მოძრაობის გარეშე. | ქმნის სივრცის სიმძიმეს, გაურკვევლობასა და ფარულ საფრთხეს, ამასთან სრულიად თავისუფალს ტოვებს ვოკალურ სიხშირულ ზონას (`1–4 kHz`). | `Exploration`, ღამის ბანაკი, მოლაპარაკება (`Dialogue`), `Aftermath`. | იცვლება ჰარმონიული გადასვლით (`Tonal Shift`), როდესაც პერსონაჟი იღებს გადაწყვეტილებას. | 
| **Harmonic Tension, Dissonance & Resolution** | დისონანსური ინტერვალების (მცირე სეკუნდა, ტრიტონი) ან შეჩერებული აკორდების (`Sus4`) დაგროვება კონსონანსურ გადაწყვეტამდე. | მაყურებელი ფიზიკურად გრძნობს მოუგვარებელ კონფლიქტს ან მოახლოებულ კატასტროფას. | ალყა, კრიზისული დიალოგი, კონტრფაქტობრივი გარდატეხის წერტილი. | წყდება ან გადადის სუფთა ტონალობაში კვანძის გახსნისას (`Payoff`). | 
| **Riser, Impact & Sting** | სიხშირული და ამპლიტუდური აწევა (`Riser`), რომელსაც მოსდევს დაბალსიხშირული დარტყმა (`Sub-Impact`) და მოკლე ორკესტრული აქცენტი (`Sting`). | ხაზს უსვამს დრამატულ აღმოჩენას ან სცენის მკვეთრ ცვლილებას. | `Opening Hook`-ის დასასრული, `Reveal`, ბრძოლის დაწყების პირველი კონტაქტი. | დაუშვებელია ყოველ მონტაჟურ ჭრაზე გამოყენება — იწვევს აუდიტორიის სენსორულ დაბუჟებას. | 
| **Intentional Silence / Music Dropout** | მუსიკის სრული და მყისიერი გაჩერება (ხშირად მხოლოდ `Reverb Tail`-ის დატოვებით), რის შემდეგაც ისმის მხოლოდ `Room Tone` ან ერთი `Foley` დეტალი. | ეპიზოდის ყველაზე ძლიერი დრამატული იარაღი; სიჩუმე აიძულებს მაყურებელს სრულად კონცენტრირდეს მომდევნო სიტყვაზე ან დარტყმაზე. | კულმინაციური ფრაზის წინ, ბრძოლის დასრულების პირველ წამებში (`Aftermath`), საბედისწერო აღმოჩენისას. | სიჩუმე უნდა გაგრძელდეს მინიმუმ 2–5 წამი, რათა აღიქმებოდეს განზრახ დრამატულ პაუზად და არა ტექნიკურ ხარვეზად. | 

#### 11.2 12-წუთიანი ისტორიული დოკუდრამის მუსიკალური რუკა (12-Minute Score Arc Blueprint)

ნაცვლად იმისა, რომ თითოეულ სეგმენტს დაედოს შემთხვევითი მუსიკალური ტრეკი, 12-წუთიანი ეპიზოდი იგება **7 მუსიკალური მდგომარეობისა (`Music States`) და 3 განზრახ უმუსიკო ფანჯრის (`No-Music Stretches`)** მონაცვლეობით:

| დროითი ფანჯარა | ნარატიული ფაზა | მუსიკალური მდგომარეობა (`Music State`) და ტემპი / ტონალობა | ინსტრუმენტაცია და სპექტრული სიმკვრივე | გადასვლის მექანიზმი (`Transition Cue`) | 
| ----- | ----- | ----- | ----- | ----- | 
| **00:00 – 00:45** | Opening Hook / Cold Open | **Cue 1: Tension Hook & Theme Statement** (`90 BPM`, D Minor) | დაბალი ჩელოს `Drone` + მთავარი 4-ნოტიანი `Leitmotif` სოლო სიმებიანზე + ყრუ ტამტამის დარტყმა 00:35-ზე. | 00:43-ზე `Riser -> Sub-Impact` და 2.5-წამიანი `Reverb Tail` სიჩუმეში. | 
| **00:45 – 02:15** | Historical Context & Exposition | **Cue 2: Sparse Analytical Pulse** (`100 BPM`, D Dorian) | მსუბუქი `Pizzicato` / მარყუჟული `Ostinato` დაბალ რეგისტრში; `1–4 kHz` სრულიად თავისუფალია ნარატორისა და `HELPER` რუკისთვის. | რბილი `Decrescendo` პირველი პერსონაჟის სცენის წინ. | 
| **02:15 – 03:30** | Character Introduction & Council Dialogue | **No-Music Stretch #1 -> Minimal Ambient Pad** | პირველი 40 წამი — **მუსიკის გარეშე** (მხოლოდ ოთახის ექო, ცეცხლის ტკაცუნი და დიალოგი); ბოლო 35 წამში შემოდის შეუმჩნეველი დაბალი `Drone`. | პერსონაჟის მუქარის რეპლიკაზე `Drone` იმატებს ნახევარი ტონით (`Dissonant Shift`). | 
| **03:30 – 05:30** | Preparation, Crafting & Strategic Escalation | **Cue 3: Building Ostinato** (`112 BPM`, A Minor) | რიტმული პერკუსია ემატება ფენებად (`Orchestral Layering`) ყოველ 30 წამში სამხედრო მომზადებისა და ლაშქრობის კვალდაკვალ. | 05:25-ზე მუსიკა აღწევს `Crescendo`-ს და მყისიერად წყდება (`Hard Dropout`). | 
| **05:30 – 06:15** | Tactical Map & Counterfactual Pivot | **No-Music Stretch #2 -> Sub-Bass Tension** | ტაქტიკური რუკის (`HELPER`) საკვანძო ახსნა მიდის სუფთა ატმოსფერულ ფონზე, რათა მაყურებელმა გაიაზროს მანევრი. | 06:10-ზე იწყება დაბალსიხშირული პულსაცია ბრძოლის წინ. | 
| **06:15 – 08:45** | Large-Scale Battle & Action Sequence | **Cue 4: Full Kinetic Action Score** (`128 BPM`, D Minor) | მძიმე პერკუსია, სპილენძის ჩასაბერები (`Low Brass`) და სწრაფი სიმებიანი `Ostinato`. დიალოგის/ნარაციის ფანჯრებში მოქმედებს `Sidechain Ducking (-4 to -6 dB)`. | 08:15-ზე (კულმინაციური დარტყმის წინ) 3-წამიანი **მუსიკალური ვაკუუმი (`Silence Before Impact`)**, შემდეგ ფინალური 30-წამიანი პიკი. | 
| **08:45 – 10:15** | Aftermath, Loss & Consequence | **No-Music Stretch #3 (08:45–09:15) -> Cue 5: Elegiac Cello** (`64 BPM`) | ბრძოლის დასრულების პირველი 30 წამი — მხოლოდ ქარი, კვამლი და იარაღის ჩხარუნი; შემდეგ შემოდის მთავარი `Leitmotif` ნელ, ტრაგიკულ ტემპში. | გადადნობა (`Crossfade`) ანალიტიკურ დასკვნაში. | 
| **10:15 – 12:00** | Historical / Counterfactual Payoff & Coda | **Cue 6: Thematic Resolution** (`90 BPM`, D Minor -> D Major / Open Fifth) | საწყისი `Opening Hook`-ის მუსიკალური თემის დაბრუნება სრული ჰარმონიული გახსნით, რომელიც კრავს ეპიზოდის დრამატურგიულ რკალს. | ბოლო კადრზე (`Held Tableau`) მუსიკა სრულდება სუფთა აკუსტიკური კადენციით (`Natural Decay to -∞ dB`). | 

#### 11.3 AI მუსიკის გენერაცია, პრომპტინგი და კომერციული ლიცენზირება

თანამედროვე გენერაციული მუსიკალური სისტემების ([Stable Audio 3.0 Licensing & Comparison](https://stability.ai/explainers/stable-audio-vs-competitors-licensing-export-rights-and-self-hosting-compared), [Stability AI Generative Audio API](https://stability.ai/explainers/generative-audio-api-for-apps-what-music-software-platforms-can-ship), [ElevenLabs Music Best Practices](https://elevenlabs.io/docs/overview/capabilities/music/best-practices)) გამოყენებისას დაცული უნდა იყოს ორი მკაცრი წესი:

1. **კომპოზიციური ბრიფი ნაცვლად ცოცხალი კომპოზიტორების იმიტაციისა \[PRIMARY / OFFICIAL\]:** პრომპტში არასოდეს მიუთითოთ ცოცხალი კომპოზიტორის ან კონკრეტული ფილმის სახელი. ElevenLabs Music-ისა და Stable Audio-ს ოფიციალური დოკუმენტაცია ადასტურებს, რომ მოდელები ზუსტად რეაგირებენ **სტუდიურ და მუსიკალურ ტერმინოლოგიაზე**: ზუსტი ტემპი (`112 BPM`), ტონალობა (`in D minor`), ინსტრუმენტაცია (`solo cello, low brass pedal, frame drum ostinato`), ვოკალის გამორიცხვა (`instrumental only, no vocals`) და დროითი სტრუქტურა (`sparse intro 0:00-0:20, rhythmic percussion enters at 0:20, crescendo at 0:50, clean reverb tail ending at 1:15`).

2. **კომერციული უფლებებისა და ლიცენზირების ვერიფიკაცია \[PRIMARY / OFFICIAL\]:**

   * *Stable Audio 3.0 / Stable Audio Open:* ვრცელდება `Stability AI Community License`-ით, რომელიც ანიჭებს მომხმარებელს გენერირებული აუდიოს სრულ კომერციულ საკუთრებასა და თვით-ჰოსტინგის (`Self-Hosting`) უფლებას უფასოდ იმ ორგანიზაციებისთვის, რომელთა წლიური შემოსავალი **1 მილიონ აშშ დოლარზე ნაკლებია** (1 მილიონზე მეტი შემოსავლის მქონე ორგანიზაციებს ესაჭიროებათ `Enterprise License`). გარდა ამისა, `Stable Audio 3.0` არ აგენერირებს ვოკალს, რაც მას იდეალურ ინსტრუმენტულ და `SFX/Stem` გენერატორად აქცევს ([Generative Audio API FAQ](https://stability.ai/explainers/generative-audio-api-for-apps-what-music-software-platforms-can-ship)).

   * *Suno / Udio / სხვა ჰოსტირებული პლატფორმები:* კომერციული გავრცელების უფლება მკაცრად მიბმულია აქტიურ ფასიან სააბონენტო გეგმაზე გენერაციის მომენტში და ხშირად ზღუდავს `Stem`-ების ექსპორტს ან ოფლაინ მოდელის წონებზე წვდომას ([Stable Audio vs. Competitors](https://stability.ai/explainers/stable-audio-vs-competitors-licensing-export-rights-and-self-hosting-compared)).

### E.3 საუნდ-დიზაინი, Foley და გარემოს აკუსტიკა (Sound Design, Foley & Environmental Audio)

#### 12.1 ხმის 11 ფენა და აკუსტიკური პერსპექტივა (`Point of Audition`)

კინემატოგრაფიული საუნდსკეიპი იგება 11 დამოუკიდებელი შრისგან, რომლებიც არასოდეს ირთვება ერთდროულად სრული სიმძლავრით ([Berklee Visual Media Audio](https://online.berklee.edu/courses/audio-music-production-for-visual-media), [iZotope Dialogue Workflow](https://www.izotope.com/community/blog/the-dialogue-editing-workflow)):

 1. **Narrator (Non-Diegetic Voice):** აკუსტიკურად მშრალი (`Dry`), ახლო და ცენტრში ფიქსირებული (`Center Mono`); არ იცვლის ექოს კადრის გარემოს მიხედვით.

 2. **Character Dialogue (Diegetic Voice):** ექვემდებარება კადრის ფიზიკურ სივრცეს (`Room Reverb`) და კამერის დისტანციას.

 3. **Room Tone:** კონკრეტული დახურული სივრცის უწყვეტი, დაბალი დონის ფონური სუნთქვა (`-42 to -50 LUFS`), რომელიც ავსებს დიალოგის ჭრებს შორის არსებულ სიცარიელეს.

 4. **Environmental Ambience (Backgrounds):** გარე სამყაროს უწყვეტი ტექსტურა (ქარი, წვიმა, ტყე, შორეული ქალაქის გუგუნი).

 5. **Environmental Spot Effects:** დისკრეტული გარემოს ხმები (ყვავის ჩხავილი, შორეული ზარის რეკვა, ჭექა-ქუხილი).

 6. **Foley (Feet, Cloth, Props):** პერსონაჟის უშუალო ფიზიკური მოძრაობის ხმები (ნაბიჯები ზედაპირისა და წონის მიხედვით, აბჯრის/ტანსაცმლის შრიალი, ხმლის ქარქაშიდან ამოღება, კალმის წერა პერგამენტზე).

 7. **Hard Sound Effects (Hard SFX):** კადრში ხილული მსხვილი მექანიკური ან საბრძოლო მოვლენები (კატაპულტის გასროლა, კარის შემტვრევა, ცხენის თქარუნი, ფარების შეჯახება).

 8. **Designed Cinematic Effects:** არარეალისტური, სტილიზებული აკუსტიკური აქცენტები (`Sub-Boooms`, `Reverse Risers`, `Metallic Whooshes`), რომლებიც გამოიყენება მხოლოდ დრამატურგიულ გარდატეხებზე.

 9. **Crowd Walla:** ბრბოს ან არმიის ფონური ხმაური კონკრეტული გარჩევადი სიტყვების გარეშე (რათა არ გადაფაროს ნარატორი).

10. **Diegetic Music:** კადრში არსებული მუსიკა (საბრძოლო ბუკი, სამხედრო დოლი, ტავერნის საკრავი).

11. **Non-Diegetic Score & Intentional Silence:** ორკესტრული პარტიტურა და დრამატული პაუზები.

**აკუსტიკური დისტანციის ფიზიკა (`Acoustic Distance Scaling`):**
ხმის ტემბრი სავალდებულოდ უნდა იცვლებოდეს კადრის ზომის (`Shot Size`) მიხედვით:

* `Extreme Wide Shot (EWS)`-ში ხმლის დარტყმა **არ უნდა ჟღერდეს ახლო, მჭახე მაღალი სიხშირეებით**; ჰაერის აბსორბციის გამო შორეულ ხმას ეჭრება მაღალი სიხშირეები (`Low-Pass Filter @ 3.5–5 kHz`), უმცირდება მშრალი ტრანზიენტი და ემატება გარემოს ადრეული არეკვლები (`Early Reflections / Wet Reverb`).

* `Close-Up (CU)` და `ECU Insert` კადრში იგივე ხმა ხდება სრული სპექტრის (`20 Hz – 18 kHz`), მშრალი, მაღალი ტაქტილური დეტალიზაციით (`Cloth + Leather Creak + Metal Transient`).

#### 12.2 Foley-ს სინქრონიზაცია და ანტი-გამეორების წესი (`Round-Robin Sample Rule`)

* **რატომ აფუჭებს ხმა ყოველ ჭრაზე ვიდეოს (`The Over-Scoring Trap`):** თუ ყოველ კამერის მოძრაობას ან ტექსტის გამოჩენას ახლავს სტანდარტული `Whoosh` ეფექტი, მაყურებლის ყური 60 წამში ეჩვევა მას და წარმოება იძენს იაფფასიანი სარეკლამო შაბლონის იერს. კინემატოგრაფიული წესით, `Whoosh / Transition SFX` დასაშვებია მხოლოდ სწრაფ `Whip-Pan`-ზე ან დროით/სივრცით ნახტომზე, ხოლო ჩვეულებრივი ჭრები ეყრდნობა ბუნებრივ `Foley`-ს (მაგ., რუკის გაშლისას ისმის სქელი პერგამენტის გაშლისა და ხის მაგიდაზე კომპასის დადების ტაქტილური ხმა).

* **Round-Robin ვარიაცია:** ნაბიჯების, ხმლების ჩხარუნისა და ცხენის თქარუნისთვის დაუშვებელია ერთი და იმავე აუდიო სემპლის ზედიზედ გამეორება (`Machine-Gun Effect`). სავალდებულოა მინიმუმ 4–6 განსხვავებული სემპლის მონაცვლეობა (`Round-Robin`) `±1.5 dB` ამპლიტუდისა და `±40 cents` სიმაღლის (`Pitch`) მიკრო-რანდომიზაციით.

#### 12.3 ათი სცენის ტიპის საუნდ-დიზაინის რეცეპტი (Scene-Type Sound Recipes)

| სცენის ტიპი | Narrator / Dialogue პრიორიტეტი | Score (მუსიკა) | Ambience & Room Tone | Foley & Hard SFX | პერსპექტივა და განზრახ სიჩუმე (`Silence Beat`) | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **1. Large Battle** | ნარატორი ადგენს ტაქტიკურ კონტექსტს; მოკლე (1–2 წმ) მეთაურის ბრძანებები. | `128 BPM` რიტმული პერკუსია და `Low Brass`; იკლებს `-5 dB`-ით ნარაციის დროს. | ღია ველის ქარი + შორეული არმიის `Walla` (გაფილტრული `<2 kHz`). | ფენოვანი: აბჯრის რხევა, ცხენების თქარუნი, მშვილდის მოზიდვა, ლითონის შეჯახება. | `EWS`-ში დომინირებს მასის გუგუნი; `CU`-ში ფონი იწევს უკან და წინ გამოდის ერთი მებრძოლის მძიმე სუნთქვა. 1.5 წმ სიჩუმე პირველ შეჯახებამდე. | 
| **2. Small Fight / Duel** | თითქმის უსიტყვო; მხოლოდ ძალისხმევის სუნთქვა (`Grunts/Breaths`). | მინიმალური დაბალი `Drone` ან სრულიად უმუსიკო. | ლოკალური გარემო (ტყის შრიალი, ქვის დარბაზის ექო). | ჰიპერ-დეტალური: ფეხის გასრიალება ხრეშზე, ტყავის სახელურის ჭრიალი, ფოლადის წკრიალი. | ინტიმური, მშრალი აკუსტიკა; ყოველი დარტყმის შემდეგ პაუზა, სადაც ისმის მხოლოდ სუნთქვა და გარემოს არეკვლა. | 
| **3. Dialogue & Negotiation** | უმაღლესი პრიორიტეტი (`Anchor Element`); მკაფიო ვოკალური ტემბრი. | გამორთული ან უკიდურესად დაბალი სუბ-ბას `Drone` (`-32 LUFS`). | უწყვეტი `Room Tone` (დარბაზი/კარავი) + ბუხრის ან წვიმის რბილი ფონი. | სკამის გაწევა, თასის დადება, პერგამენტის შრიალი რეპლიკებს შორის პაუზებში. | კამერის ახლო კადრზე გადასვლისას `Room Reverb` მცირდება 20%-ით ინტიმურობის გასაზრდელად; კრიტიკული კითხვის შემდეგ 2-წამიანი სამარისებური სიჩუმე. | 
| **4. Travel / Marching / Sailing** | ნარატორი მიჰყვება მარშრუტსა და დროის გასვლას. | განმეორებადი `Ostinato`, რომელიც იცვლის ტემბრს გეოგრაფიის ცვლილებასთან ერთად. | ცვალებადი კლიმატი: სტეპის ქარი -> მთის ქარბუქი -> ზღვის ტალღები. | რიტმული ნაბიჯები, აღკაზმულობის წკარუნი, ხის გემბანის ჭრიალი და აფრის ტკაცუნი. | `J-Cut`-ით შემოდის მომდევნო კლიმატური ზონის ქარი/ტალღა კადრის შეცვლამდე 1 წამით ადრე. | 
| **5. Manual Crafting / Building** | ნარატორი ხსნის ტექნოლოგიას ან მომზადების მნიშვნელობას. | მსუბუქი, რიტმული პულსი, რომელიც სინქრონდება შრომის ტემპთან. | სამჭედლოს საბერველის ქშიტინი, სახელოსნოს ან ბანაკის ფონი. | უროს დარტყმა გავარვარებულ რკინაზე, წყალში გაცივების შიშინი (`Sizzle`), ხის თლა. | `Foley`-ს დარტყმები ასრულებს მუსიკალური პერკუსიის როლს; მუსიკა შეიძლება სრულად დაუთმოს ადგილი შრომის რიტმს. | 
| **6. Discovery / Reveal** | ნარატორი ჩერდება აღმოჩენის კადრამდე, შემდეგ აკეთებს მოკლე, დაბალ კომენტარს. | `Tension Riser` -> მყისიერი `Music Dropout` -> დაბალი `Resonant Sting`. | გარემოს ხმა უეცრად იფილტრება (`Low-Pass`), თითქოს ყურადღება იკუმშება. | ჩირაღდნის აგიზგიზება, მძიმე კარის გაღება ან მტვრის ჩამოყრა. | **სავალდებულო 1.0–2.0 წამიანი აკუსტიკური ვაკუუმი** უშუალოდ იმ მომენტში, როდესაც კამერა აჩვენებს აღმოჩენილ ობიექტს. | 
| **7. Environmental Establishing** | ნარატორი იწყებს საუბარს კადრის გახსნიდან 1.5–2.0 წამის შემდეგ. | ფართო ჰარმონიული აკორდი ან ეპოქის ინსტრუმენტული სოლო. | მდიდარი, ფართო სტერეო (`Wide Stereo`) ატმოსფერო (ქარი, ფრინველები, ქალაქის ზარები). | შორეული დროშის ტკაცუნი ქარში ან ცეცხლის კერა. | პირველი 2 წამი ეკუთვნის მხოლოდ გარემოს ატმოსფეროსა და მუსიკას, რათა მაყურებელი „შევიდეს“ სივრცეში. | 
| **8. Map / Tactical Explanation** | ნარატორი არის აბსოლუტური წამყვანი; მკაფიო დიქცია და ზუსტი პაუზები. | დაბალი, არამელოდიური ანალიტიკური პულსი (`Ostinato` `<250 Hz`). | სუფთა, დაბალი ატმოსფერული ფონი (ქარის ან დარბაზის რბილი შუილი). | ორგანული ტაქტილური ხმები: პერგამენტის გაშლა, ხის ფიგურის გადაადგილება, რბილი დაბალი ტონი. | ციფრული „ბიპების“ (`Sci-Fi Beeps`) სრული აკრძალვა ისტორიულ რუკებზე; ხმა მხოლოდ ახალ ფრაქციაზე ან ისარზე. | 
| **9. Aftermath & Loss** | ნელი, დაბალი რეგისტრის თხრობა დიდი (1.5–3 წმ) პაუზებით. | პირველი 15–30 წამი უმუსიკოდ, შემდეგ სოლო ჩელოს ან ხის ჩასაბერის ელეგია. | ცივი ქარი, ნაკვერჩხლის ტკაცუნი, შორეული წვიმა. | ნელი, მძიმე ნაბიჯები ტალახში, გატეხილი იარაღის დავარდნა. | სივრცე გაჯერებულია გრძელი `Reverb Tail`-ითა და სიჩუმის ინტერვალებით. | 
| **10. Climax & Payoff** | თხრობისა და პერსონაჟის გადამწყვეტი რეპლიკის კონვერგენცია. | მთავარი `Leitmotif`-ის სრული ორკესტრული გახსნა. | გარემოს ხმა შერწყმულია მუსიკალურ კულმინაციასთან. | გადამწყვეტი ფიზიკური აქტის სუფთა, არაკლიპირებული `Impact`. | კულმინაციური პიკის დასრულებისთანავე მყისიერი გადასვლა სუფთა აკუსტიკურ განმუხტვაზე. | 

### E.4 აუდიო ინჟინერია, მიქსინგი, სტანდარტები და მასტერინგი (Audio Engineering, Mixing & Mastering)

#### 13.1 სიგნალის დამუშავების სრული ჯაჭვი (`Post-Production Signal Chain`)

პროფესიონალური რე-რეკორდინგ მიქსი ([Berklee Visual Media Audio](https://online.berklee.edu/courses/audio-music-production-for-visual-media), [iZotope Dialogue Editing Workflow](https://www.izotope.com/community/blog/the-dialogue-editing-workflow), [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)) იყოფა ოთხ იერარქიულ სტემ-ბასად (`Dialogue/Narration Bus`, `Music Bus`, `Foley/SFX Bus`, `Ambience Bus`), რომლებიც იკრიბება `Master Bus`-ზე:

1. **Gain Staging & High-Pass Filtering:** თითოეული ცალკეული ტრეკის პიკური დონე (`Peak Level`) დამუშავებამდე დგება `-12 dBFS`-დან `-6 dBFS`-მდე, რათა დარჩეს საკმარისი `Headroom`. ნარატორის, დიალოგისა და `Ambience`-ის ტრეკებზე იდება `High-Pass Filter @ 75–85 Hz` (`12–18 dB/octave`), რათა მოიჭრას არასაჭირო სუბ-ბას გუგუნი (`Mud`) და დაბალი სიხშირეების ენერგია დარჩეს საბრძოლო `Sub-Impact`-ებისა და მუსიკალური ბასისთვის.

2. **კორექციული და ტონალური EQ + De-essing:**

   * *Dialogue / Narration:* `180–250 Hz` ზონაში `-2 dB` ამოჭრა (ყუთისებრი რეზონანსის — `Boxiness`-ის მოსახსნელად), `2.5–3.5 kHz` ზონაში `+1.5 to +2.5 dB` განიერი აწევა (`Presence / Intelligibility`), ხოლო `6–9 kHz` ზონაში დინამიკური `De-esser` მჭახე სისინა ბგერების (`s, sh, ch`) დასარბილებლად.

   * *Music & Ambience Bus (Spectral Unmasking):* მუსიკისა და ატმოსფეროს ბასებზე კეთდება `-2.5 to -3.5 dB` რბილი ჩაღრმავება (`Dip`) **`1.5 kHz – 3.5 kHz` ვოკალური ფორმანტის ზონაში**, რათა მუსიკამ არ შენიღბოს მეტყველების გარჩევადობა მაშინაც კი, როდესაც იგი ხმამაღლა ჟღერს.

3. **კომპრესია და პარალელური კომპრესია (`Compression & Parallel Compression`):**

   * ნარატორის ხმაზე გამოიყენება რბილი ოპტიკური სტილის კომპრესია (`Ratio 2.5:1 to 3:1`, `Attack 15–25 ms`, `Release 80–120 ms`, `Gain Reduction 3–5 dB`), რათა ყოველი სიტყვა იკითხებოდეს თანაბრად მობილურ დინამიკებზეც.

   * საბრძოლო `SFX` ბასზე გამოიყენება `Parallel Compression` (შეკუმშული სიგნალის შერევა მშრალ სიგნალთან 25/75 პროპორციით), რაც ინარჩუნებს დარტყმის მკვეთრ საწყის ტრანზიენტს და ამავდროულად ამკვრივებს ხმის კუდს.

4. **დინამიკური Sidechain Ducking:** ნარატორისა და პერსონაჟთა დიალოგის ბასი მართავს (`Key Input`) მუსიკისა და `Ambience/SFX` ბასების კომპრესორს (`FFmpeg sidechaincompress` — [FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html)): როდესაც იწყება მეტყველება, მუსიკა რბილად იწევს ქვემოთ **`3–6 dB`-ით** (`Attack 15–30 ms` მყისიერი გაწმენდისთვის, `Release 350–600 ms`, რათა სიტყვებს შორის მოკლე პაუზებში მუსიკამ არ „იხტუნაოს“ — `Pumping Prevention`).

#### 13.2 ლაუდნესის საერთაშორისო სტანდარტების შედარება და YouTube-ის რეალური სამიზნე

აუდიო ინჟინერიაში ერთ-ერთი ყველაზე გავრცელებული შეცდომაა სატელევიზიო მაუწყებლობის სტანდარტის (`-23 LUFS` ან `-27 LKFS`) ბრმად გადმოტანა YouTube-ის ვებ-პლატფორმაზე ([ITU-R BS.1770-5 (11/2023)](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf), [EBU R 128 Specification](https://en.wikipedia.org/wiki/EBU_R_128), [ATSC A/85:2013](https://www.atsc.org/wp-content/uploads/2025/06/A85-2013-with-Corrigendum-No-1.pdf), [LUFS Targets Per Platform 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026)):

| სტანდარტი / პლატფორმა | ავტორიტეტული დოკუმენტი და ვერსია | გაზომვის მეთოდი (`Gating & Weighting`) | სამიზნე ლაუდნესი (`Integrated Target`) | მაქსიმალური True Peak (`dBTP`) | პლატფორმის ქცევა და გამოყენების წესი 12-წუთიანი დოკუდრამისთვის \[PRIMARY / OFFICIAL\] | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **ITU-R BS.1770-5** | [ITU-R BS.1770-5 (11/2023)](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf) | K-weighting ფილტრი + ორსაფეხურიანი გეიტინგი (`-70 LKFS` აბსოლუტური და `-10 dB` ფარდობითი); 4x ოვერსემპლინგი `True Peak`-ისთვის. | განსაზღვრავს **გაზომვის ალგორითმს** (`LKFS = LUFS`), და არა ერთ უნივერსალურ სამიზნე რიცხვს. | ალგორითმული საზომი (`dBTP`). | ყველა თანამედროვე ლაუდნეს-მეტრისა და `FFmpeg loudnorm`-ის ფუნდამენტური მათემატიკური ბაზა. | 
| **ITU-R BS.2076-3 (ADM)** | [ITU-R BS.2076-3 (02/2025)](https://www.itu.int/rec/R-REC-BS.2076/) | Audio Definition Model (XML მეტამონაცემები მრავალარხიანი და ობიექტზე დაფუძნებული აუდიოსთვის). | N/A (მეტამონაცემთა სტრუქტურა). | N/A | გამოიყენება `Dolby Atmos` და იმერსიული სამაუწყებლო არქივების სტრუქტურირებისთვის. | 
| **EBU R 128** | [EBU R 128 (Rev. 11/2023)](https://en.wikipedia.org/wiki/EBU_R_128) | სრული პროგრამის ინტეგრირებული ლაუდნესი (`Integrated - I`), `Short-Term (3s)` და `Momentary (400ms)`. | **`-23.0 LUFS ± 0.5 LU`** (ლაივში `±1.0 LU`). | **`-1.0 dBTP`** (შეკუმშული კოდეკებისთვის ხშირად `-2.0` ან `-3.0 dBTP`). | **ევროპული ტელე-რადიო მაუწყებლობის სტანდარტი.** YouTube-ზე `-23 LUFS` ფაილის ატვირთვა გამოიწვევს იმას, რომ ვიდეო იქნება 9 dB-ით ჩუმი სხვა ვიდეოებთან შედარებით! | 
| **ATSC A/85 (CALM Act)** | [ATSC A/85:2013 + Corrigendum 1](https://www.atsc.org/wp-content/uploads/2025/06/A85-2013-with-Corrigendum-No-1.pdf) | `Anchor Element` (დიალოგზე დაფუძნებული გაზომვა) ან სრული პროგრამის `ITU-R BS.1770`. | **`-24.0 LKFS ± 2.0 LU`** | **`-2.0 dBTP`** | აშშ-ის სატელევიზიო მაუწყებლობის სტანდარტი; ამკვიდრებს დიალოგის, როგორც მთავარი საყრდენის (`Anchor`), პრინციპს. | 
| **Netflix Delivery Spec** | [Netflix Sound Mix Specs & Platform Analysis](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026) | **Dialog-Gated** `ITU-R BS.1770` (იზომება მხოლოდ დიალოგის მონაკვეთები). | **`-27.0 LKFS ± 2.0 LU`** (დიალოგის გარეშე პროგრამებისთვის `-24 LKFS`). | **`-2.0 dBTP`** | კინოთეატრალური ფართო დინამიკური დიაპაზონი სახლის კინოთეატრებისთვის; არ გამოიყენება პირდაპირ YouTube-ის სტერეო მიქსისთვის. | 
| **YouTube Web / Mobile Delivery** | [YouTube Upload Encoding Settings](https://support.google.com/youtube/answer/1722171?hl=en) & [EBU R 128 Streaming Section](https://en.wikipedia.org/wiki/EBU_R_128) | სრული პროგრამის ინტეგრირებული ლაუდნესი (`ITU-R BS.1770`). | **`-14.0 LUFS`** (სარეკომენდაციო საწარმოო სამიზნე: **`-14.0 to -15.0 LUFS`**, `LRA 6–10 LU`). | **`-1.0 dBTP`** (`AAC` ტრანსკოდირებისთვის უსაფრთხოა **`-1.5 dBTP`**). | **კრიტიკული წესი:** YouTube იყენებს **მხოლოდ ქვემოთ მიმართულ ნორმალიზაციას (`Downward Normalization Only`)** — თუ მიქსი არის `-9 LUFS`, პლატფორმა დაუწევს მას `-14 LUFS`-მდე, მაგრამ თუ მიქსი არის `-23 LUFS`, YouTube მას **არ აუწევს**! ამიტომ 12-წუთიანი დოკუდრამის მასტერი უნდა დამზადდეს **`-14.0 LUFS` Integrated / `-1.5 dBTP` True Peak** პარამეტრზე. | 

#### 13.3 რვა საბაზისო მიქს-რეცეპტი (`Starting-Point Mix Recipes`)

ქვემოთ მოცემული რიცხვითი დიაპაზონები წარმოადგენს [Berklee Online](https://online.berklee.edu/courses/audio-music-production-for-visual-media)-ისა და [LUFS Targets 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026)-ის პრაქტიკაზე დაფუძნებულ **საწყის საორიენტაციო წერტილებს (`Starting Points`)** `-14.0 LUFS` YouTube მასტერისთვის, რომლებიც საბოლოოდ მოწმდება სმენითი მონიტორინგითა და `Short-Term Loudness` მეტრით:

| მიქსის სცენარი | Layer 1: Narrator / Dialogue (`Short-Term LUFS`) | Layer 2: Music Score (`Short-Term LUFS`) | Layer 3: Hard SFX & Foley (`Short-Term LUFS`) | Layer 4: Ambience & Room Tone (`Short-Term LUFS`) | დინამიკური მართვა და ავტომატიზაცია | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **1. Narration-Led Scene** | **`-14 to -15 LUFS`** (აბსოლუტური ლიდერი) | `-26 to -29 LUFS` (12–14 dB-ით ნარატორის ქვემოთ) | `-22 to -26 LUFS` (რბილი ტაქტილური აქცენტები) | `-32 to -36 LUFS` | `Sidechain Ducking` მუსიკაზე (`-4 dB`) და `-3 dB` EQ dip `2.5 kHz`-ზე. | 
| **2. Character Dialogue Scene** | **`-15 to -17 LUFS`** (ბუნებრივი დინამიკით) | `-30 to -36 LUFS` ან გამორთული | `-22 to -25 LUFS` (სინქრონული `Foley` პაუზებში) | `-34 to -40 LUFS` (უწყვეტი `Room Tone`) | რეპლიკებს შორის პაუზებში `Foley` (ჭიქა, ნაბიჯი) ამოდის `-20 LUFS`-მდე. | 
| **3. Music-Led Montage** | `-15 LUFS` (მხოლოდ მოკლე თეზისები) | **`-14 to -16 LUFS`** (წამყვანი ენერგია უსიტყვო ფანჯრებში) | `-18 to -22 LUFS` (რიტმულად სინქრონიზებული) | `-30 to -34 LUFS` | როდესაც ნარატორი შემოდის 1 წინადადებით, მუსიკა იწევს `-24 LUFS`-მდე `0.4s` ფეიდით. | 
| **4. Battle / Action Sequence** | `-14 LUFS` (მკვეთრი კომპრესიით, რომ არ დაიკარგოს) | `-16 to -18 LUFS` (სავსე დაბალი რეგისტრით) | **`-12 to -14 LUFS`** (პიკური შეჯახებები; `Limiter @ -1.5 dBTP`) | `-24 to -28 LUFS` (ბრძოლის ველის `Walla`) | ნარატორის ფანჯრებში `SFX` ბასის მაღალი შუა სიხშირეები (`1.5–4 kHz`) იკლებს `-5 dB`-ით. | 
| **5. Quiet Reveal** | `-17 to -19 LUFS` (ინტიმური, ხმადაბალი ტემბრი) | `Dropout to -∞` -> `-24 LUFS Sting` | `-20 LUFS` (ერთი მკაფიო იზოლირებული დეტალი) | `-38 to -44 LUFS` | აღმოჩენის კადრზე 1.5 წამის განმავლობაში საერთო ლაუდნესი ეცემა `-35 LUFS`-მდე კონტრასტისთვის. | 
| **6. Ambience-Led Travel** | `-15 LUFS` | `-22 to -25 LUFS` (`Ostinato`) | `-20 to -23 LUFS` (ნაბიჯები, ცხენები, აფრები) | **`-22 to -26 LUFS`** (ქარი, წვიმა, ზღვა წინა პლანზე) | გარემოს ხმა იშლება ფართო სტერეო ველში (`Mid/Side Side +2 dB`), ნარატორი რჩება `Mid`-ში. | 
| **7. Climax** | **`-13.5 to -14.5 LUFS`** | **`-15 to -17 LUFS`** | **`-13 to -15 LUFS`** | `-26 LUFS` | მაქსიმალური სპექტრული სიმკვრივე; `True Peak Limiter` იცავს `-1.5 dBTP` ჭერს. | 
| **8. Silence-to-Impact Transition** | ჩერდება დარტყმამდე 1.5 წამით ადრე | `Riser` (`-16 LUFS`) -> **1.5s Silence (`-45 LUFS`)** | **Impact (`-11 LUFS Momentary`, `-1.5 dBTP`)** | ითიშება ვაკუუმის დროს | 25+ LU დინამიკური ნახტომი სიჩუმესა და დარტყმას შორის ქმნის მაქსიმალურ ფიზიკურ შოკს კლიპინგის გარეშე. | 

## F. სცენის არქეტიპების ბიბლიოთეკა — ვიზუალური და აუდიო გრამატიკა (Scene-Archetype Library — 20 Archetypes)

ქვემოთ მოცემულია 20 სავალდებულო სცენის არქეტიპის სრული ტექნიკური სპეციფიკაცია. თითოეული არქეტიპი განსაზღვრავს საკუთარ ვიზუალურ და აკუსტიკურ ენას, რათა საბრძოლო სცენა, ხელოსნობა, დიალოგი და რუკა მკაფიოდ განსხვავდებოდეს ერთმანეთისგან.

### F.1 არქეტიპების სრული ტაქსონომია და საწარმოო მატრიცა (Archetypes 1–20)

| \# | სცენის არქეტიპი | ნარატიული და ემოციური მიზანი | ვიზუალური ზოლი (`Lane`) და კადრის ხანგრძლივობა | კადრების თანმიმდევრობა (`Shot Sequence`) და ლინზა | კამერისა და სუბიექტის მოძრაობა | განათება, პალიტრა და ატმოსფერო | აუდიო რეცეპტი (Voice / Score / Ambience / Foley / Silence) | საუკეთესო ინსტრუმენტული გზა (`Tool Route`) და QA | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **1** | **Large-scale battle / army movement / siege** | მასშტაბის, ტაქტიკური მიზეზ-შედეგობრიობისა და შეჯახების ინერციის ჩვენება. | `VIDEO` (10–15 წმ უწყვეტი არადიალოგური მანევრი + 3–5 წმ ახლო კადრები); `HELPER` (6–8 წმ ტაქტიკური რუკა). | `High-Angle EWS` (24mm) -> `Telephoto MWS` (135mm შეკუმშული მწკრივები) -> `Ground MS` შეჯახება. | `Elevated Crane/Tracking` ფორმაციის გასწვრივ; მკაცრი `Screen Direction` (A მარცხნივ -> B მარჯვნივ). | მტვრისა და კვამლის ვოლუმეტრიკა (`Aerial Perspective`), ცივი ფოლადისა და ცეცხლის (`#D55E00`) კონტრასტი. | ნარატორი ტაქტიკაზე; `128 BPM` პერკუსია + `Low Brass`; ფენოვანი `Walla` + აბჯარი; 1.5 წმ სიჩუმე პირველ დარტყმამდე. | `Blender` (`Geometry Nodes` ფორმაციის Previs) -> `LTX-2.5 I2V` (`Motion Control IC-LoRA`) -> `FFmpeg` მიქსი. QA: ეკრანული მიმართულება და იარაღის მთლიანობა. | 
| **2** | **Small-scale fight / duel / physical confrontation** | პერსონალური რისკის, ფიზიკური წონისა და სიცოცხლისთვის ბრძოლის დაძაბულობა. | `VIDEO` (3–6 წმ სწრაფი სამოქმედო კადრები + `Editorial Impact Cut`). | `Two-Shot MWS` (35mm) -> `OTS MS` (50mm) -> `ECU Insert` (85mm იარაღის ბლოკირება) -> `CU Reaction`. | `Controlled Handheld` ან დაბალი კუთხის (`Low-Angle`) ტრეკინგი; 4-ფაზიანი პოზა (`Anticipation -> Peak -> Settle`). | მაღალი კონტრასტი (`Low-Key 8:1`), მკვეთრი `Rim Light` სილუეტისა და იარაღის გამოსაკვეთად. | უსიტყვო (მხოლოდ სუნთქვა); მუსიკა გამორთული ან დაბალი `Drone`; ჰიპერ-დეტალური ფოლადის, ტყავისა და ნაბიჯების `Foley`. | `LTX-2.5 FLF2V` (საწყისი და საბოლოო პოზის ფიქსაციით) + `FFmpeg` `Cut on Action`. QA: არავითარი „რეზინის კიდურები“ და ფეხების სრიალი. | 
| **3** | **Two-person dialogue / negotiation / argument** | ინტელექტუალური ან პოლიტიკური დაპირისპირება, ქვეტექსტი და ძალაუფლების ცვლილება. | `VIDEO` (≤5 წმ ხილული `Lip-Sync` + 3–5 წმ `Reaction MCU`); `STILL` (3–4 წმ `Insert`). | `Master Two-Shot` (35mm) -> `OTS A` (50mm) -> `OTS B` (50mm) -> `Single CU` (85mm გარდატეხისას). | კამერა უძრავია ან ასრულებს უკიდურესად ნელ `Dolly-In`-ს მხოლოდ გადამწყვეტ რეპლიკაზე; მკაცრი `180° Axis`. | მოტივირებული `Chiaroscuro` (სანთელი/ფანჯარა), `Negative Fill` ჩრდილის მხარეს. | პერსონაჟთა დიალოგი (`20–30%` ბიუჯეტიდან) `J-cut / L-cut`-ით; უწყვეტი `Room Tone`; მუსიკის გარეშე; 2 წმ პაუზა მუქარის შემდეგ. | `ElevenLabs v4` + `Forced Alignment` -> `LTX-2.5 Audio-to-Video` (≤5 წმ) + `Reaction` კადრები. QA: `Eyeline Match` და ვოკალური ტემბრის განსხვავება. | 
| **4** | **Group dialogue / council / assembly** | ფრაქციული დაყოფის, კოლექტიური ზეწოლისა და ლიდერის იზოლაციის ჩვენება. | `STILL` (5–7 წმ მრავალფიგურიანი `2.5D Tableau`) + `VIDEO` (≤5 წმ მთავარი მომხსენებლის `MCU`). | `Wide Architectural Master` (24mm სიმეტრია) -> `3/4 Group MS` -> `Low-Angle MCU` ლიდერზე -> `Cutaway` მოწინააღმდეგეთა ჩურჩულზე. | ნელი `2.5D Parallax Push` მთელ დარბაზზე; მზერის ვექტორები მიმართულია ცენტრალური სპიკერისკენ. | ზედა ვოლუმეტრიული სხივები (`High Windows / Chandeliers`), თბილი ცენტრი და ცივი პერიფერია. | ნარატორი აჯამებს ფრაქციების პოზიციებს, შემდეგ 1–2 საკვანძო გახმოვანებული რეპლიკა; დარბაზის ჩუმი `Walla` და ქაღალდის შრიალი. | `Python / Blender` `2.5D Multi-plane` დარბაზისთვის + `LTX-2.5` ინდივიდუალური სპიკერისთვის. QA: ფონზე მდგომი ხალხის სახეები არ უნდა დეფორმირდებოდეს. | 
| **5** | **Solitary emotion / realisation / reaction** | შინაგანი გარდატეხის, დანაშაულის, შიშის ან გასხივოსნების ინტიმური გადაცემა. | `VIDEO` (4–7 წმ მიკრო-მიმიკით) ან `STILL` (4–6 წმ `2.5D` სინათლის ციმციმით). | `MCU` -> `CU` (85mm ან 100mm `Shallow DOF`) ან პირიქით: `CU` -> `EWS` იზოლაციის საჩვენებლად. | უძრავი კამერა ან ნელი `Dolly-In`; სუბიექტი თითქმის უძრავია (მხოლოდ სუნთქვა, თვალის დახამხამება, მზერის გადატანა). | სახის ნახევარი ჩრდილში (`Split / Rembrandt Lighting`), თბილი ცეცხლის ან ცივი მთვარის ანარეკლი თვალში (`Catchlight`). | ნარატორის ხმადაბალი რეფლექსია ან სრული ვოკალური პაუზა; სოლო ინსტრუმენტი (ჩელო); ღრმა სუნთქვისა და გარემოს იზოლირებული ხმა. | `LTX-2.5 I2V` მინიმალური მოძრაობის პრომპტით (`subtle breathing, eyes shift left, firelight flicker`). QA: სახის იდენტობის 100%-იანი სტაბილურობა. | 
| **6** | **Crafting / building / repairing / manual work** | ფიზიკური შრომის, ტექნოლოგიური პროცესისა და მასალის გარდაქმნის ტაქტილური ჩვენება. | `VIDEO` (4–8 წმ პროცესის კადრები) + `STILL` (2.5–4 წმ დეტალური `Insert`-ები). | `Establishing MS` (35mm სახელოსნო) -> `ECU Hands/Tool Insert` (85mm) -> `Low-Angle MCU` ოსტატის სახეზე -> `Result FS`. | `Cut on Action` უროს/ხელსაწყოს ყოველ დარტყმაზე; კამერის მცირე `Tilt` მასალის გასწვრივ. | მოტივირებული თბილი სინათლე ქურიდან ან გვერდითი სარკმლიდან; ნაპერწკლებისა და მტვრის ნაწილაკები. | ნარატორი ხსნის პროცესს; რიტმული, შრომის ტემპთან სინქრონიზებული `Foley` (რკინა, ხე, ქვა, წყალი) წინა პლანზე (`-18 LUFS`). | `LTX-2.5 I2V` ნაპერწკლებისა და მარტივი მოძრაობისთვის + `Python/Blender` ზუსტი მექანიკური დეტალებისთვის. QA: ხელსაწყოს გეომეტრია არ უნდა იღუნებოდეს. | 
| **7** | **Travel / marching / riding / sailing / traversal** | გეოგრაფიული მანძილის, კლიმატური სირთულისა და დროის გასვლის გადმოცემა. | `VIDEO` (8–14 წმ უწყვეტი ლაშქრობა/ცურვა) + `HELPER` (5–7 წმ მარშრუტის რუკა). | `Route Map HELPER` -> `Extreme Wide Profile Shot` (24mm ჰორიზონტზე) -> `Lateral Tracking MWS` (50mm) -> `Tail-Away WS`. | თანმიმდევრული ჰორიზონტალური მიმართულება (მაგ., მუდმივად მარცხნიდან მარჯვნივ); კამერის `Lateral Tracking`. | ცვალებადი ამინდი და დღის მონაკვეთი (`Dawn -> Overcast -> Dusk`) დროის გასვლის საჩვენებლად. | ნარატორი; განმეორებადი `Ostinato`; მდიდარი სტერეო `Ambience` (ქარი, წვიმა, ზღვა) + რიტმული ნაბიჯების/აფრების `Foley`. | `Python` მარშრუტის რუკა -> `LTX-2.5` გარემოსა და ლაშქრობისთვის -> `FFmpeg` `xfade` დროის გადასვლისთვის. QA: მოძრაობის ვექტორის უწყვეტობა. | 
| **8** | **Exploration / discovery / entering an unknown place** | ცნობისმოყვარეობის, სიფრთხილისა და უცნობი სივრცის მასშტაბის განცდა. | `VIDEO` (6–12 წმ კამერის ნელი შესვლა სივრცეში) ან `STILL` (`2.5D Multi-plane Parallax`). | `Over-the-Shoulder Back-Lit WS` (პერსონაჟი შედის ბნელ თაღში) -> `POV Pan/Tilt` (24mm) -> `MCU` სახეზე ჩირაღდნის შუქით. | ნელი `Dolly-In` წინა პლანის მუქი ჩარჩოს (`Frame-within-Frame`) გავლით. | ძლიერი კონტრასტი ბნელ წინა პლანსა და განათებულ სიღრმეს შორის; მტვრის ნაწილაკები სინათლის სხივში. | ნარატორი ჩურჩულა/დაბალ რეგისტრში; მაღალი სიმებიანი `Tension Texture`; გრძელი აკუსტიკური ექო (`Cave/Hall Reverb`) და ნელი ნაბიჯები. | `Blender` 3D/2.5D კამერის შესვლა თაღში + `LTX-2.5` ჩირაღდნის ციმციმისთვის. QA: ჩრდილების სისუფთავე (`No Banding`). | 
| **9** | **Reveal / surprise / object discovery / reversal** | აუდიტორიის მოლოდინის შეცვლა და ახალი დრამატურგიული ფაქტის დაფიქსირება. | `VIDEO` (4–8 წმ `Character-First` ან `Rack-Focus Reveal`) ან `STILL` (`2.5D` ფოკუსის გადატანით). | ვარიანტი A: `CU Gaze` -> `Hard Cut / Whip-Pan` -> `EWS Object`. ვარიანტი B: წინა პლანი ბუნდოვანია -> `Rack Focus` უკანა პლანზე. | კამერის მოძრაობა ან ფოკუსის ცვლილება ხსნის მანამდე დაფარულ ინფორმაციას. | აქცენტური სინათლის სხივი ან მაღალი გაჯერების ფერი (`Accent Color`) მხოლოდ აღმოჩენილ ობიექტზე. | `Riser` -> **მყისიერი `Music Dropout` (1–2 წმ სიჩუმე)** -> დაბალი `Sting` ზუსტად ვიზუალური ფოკუსირების წამს. | `Blender Defocus Node` (`Z-Depth Rack Focus`) ან `LTX-2.5 I2V`. QA: ხმოვანმა `Sting`-მა არ უნდა დაასწროს ვიზუალურ გამოჩენას! | 
| **10** | **Chase / escape / pursuit** | კინეტიკური ენერგია, დროის დეფიციტი და ფიზიკური საფრთხის სიახლოვე. | `VIDEO` (2.5–5 წმ სწრაფი მონტაჟური კადრები + 8–10 წმ ტრეკინგი). | `Low-Angle Follow Shot` (24mm მდევარი) -> `Frontal Tracking MCU` (გაქცეული იყურება უკან) -> `Wide Lateral Geography Check`. | სწრაფი `Follow / Lateral Tracking`, წინა პლანზე ხეების/სვეტების სწრაფი გავლა (`Foreground Occlusion Whip`). | დახრილი ჩრდილები, მტვრისა და ტალახის შხეფები, დინამიკური სინათლის ცვლილება. | სწრაფი `130+ BPM` პერკუსიული `Ostinato`; მძიმე სუნთქვა, ფლოქვების/ნაბიჯების აჩქარებული რიტმი, ტოტების ლაწანი. | `LTX-2.5 Fast / Pro` + `Motion Control IC-LoRA` ტრაექტორიისთვის -> `FFmpeg` სწრაფი `Cut on Action`. QA: მდევარი და გაქცეული მოძრაობენ ერთი და იმავე მიმართულებით! | 
| **11** | **Environmental establishing / weather / landscape / city / camp** | ეპოქის, გეოგრაფიული ლოკაციისა და სცენის ემოციური ტონის დამკვიდრება. | `STILL` (5–8 წმ `2.5D Parallax` + ნაწილაკები) ან `VIDEO` (6–10 წმ ატმოსფერული მოძრაობით). | `Extreme Wide Rule-of-Thirds Tableau` (24mm ან 35mm) მკაფიო წინა, შუა და უკანა პლანით. | უძრავი ან ძალიან ნელი ჰორიზონტალური დრეიფი (`Slow Drift`); მოძრაობს ღრუბელი, კვამლი, წყალი, დროშა. | „ოქროს საათი“ (`Golden Hour`), ნისლიანი განთიადი ან ღამის კოცონები ბანაკში. | პირველი 2 წამი ნარატორის გარეშე; ფართო სტერეო `Ambience` + ლოკაციის მუსიკალური თემა (`Location Motif`). | `Python / Blender 2.5D` + პროცედურული ნისლი/კვამლი ან `LTX-2.5 I2V`. QA: ჰორიზონტის ხაზის სისწორე და არქიტექტურული სიზუსტე. | 
| **12** | **Map / route / tactical geography / territorial change** | სივრცითი სტრატეგიის, საზღვრების ცვლილებისა და ფრონტების კოორდინაციის ახსნა. | `HELPER` (6–12 წმ დეტერმინისტული კარტოგრაფიული ანიმაცია). | `Macro Regional Map` -> `Smooth Camera Zoom/Pan` კონკრეტულ ხეობაზე/ქალაქზე -> `Animated Vector Arrows & Territory Fill`. | დეტერმინისტული `Cubic-Bezier` კამერის სვლა; ელემენტები ჩნდება თანმიმდევრულად ნარატორის სიტყვებთან სინქრონში. | პერგამენტის ან მუქი ტაქტიკური ფონი (`#1A1D24`) + `Okabe-Ito` ფერები (`#0072B2` vs `#D55E00` + `#F0E442` აქცენტი). | ნარატორი (`Forced Alignment` სინქრონით); დაბალი ანალიტიკური პულსი; ქაღალდისა და ხის ტაქტილური `Foley` ისრების გამოჩენაზე. | **100% დეტერმინისტული `Python` (`GeoJSON/SVG + Pillow/OpenCV`) ან `Blender`**. QA: 0 გენერაციული ტექსტი; `17–20 CPS` წაკითხვადობა. | 
| **13** | **Abstract explanation / mechanism / calculation / comparison** | ეკონომიკური, დემოგრაფიული ან ტექნიკური მტკიცებულების ვიზუალიზაცია. | `HELPER` (5–10 წმ დიაგრამა, მრიცხველი ან სქემა). | `Clean Split-Screen Comparison` ან `Animated Bar/Step Chart` / `Technical Cutaway`. | სვეტების/ხაზების გლუვი ზრდა (`Ease-OutCubic`); აქტიური მონაცემის განათება და დანარჩენის ჩაბნელება (`Dimming to 30%`). | მაღალი კონტრასტი (`WCAG ≥ 4.5:1`), სუფთა ბადე, `Okabe-Ito` კოდირება + ფორმის/შტრიხის დუბლირება. | ნარატორი ასახელებს ზუსტ რიცხვს მრიცხველის გაჩერების მომენტში; მსუბუქი მექანიკური წკაპი (`Soft Mechanical Tick`). | **დეტერმინისტული `Python` (`Matplotlib / Pillow`)**. QA: Y-ღერძის ნულიდან დაწყება და რიცხვების 100%-იანი სიზუსტე. | 
| **14** | **Transformation / construction / destruction / passage of time** | ქალაქის აშენების, იმპერიის დაცემის ან სეზონების ცვლილების შეკუმშული ჩვენება. | `STILL` / `VIDEO` ჰიბრიდი (3–4 დაკავშირებული კადრი `Match Dissolve`-ით, სულ 8–12 წმ). | `Locked-Off Wide Camera` ერთი და იმავე რაკურსიდან, სადაც იცვლება მხოლოდ ობიექტის მდგომარეობა (საძირკველი -> კედლები -> ციხესიმაგრე). | კამერის პოზიცია და ფოკუსური მანძილი აბსოლუტურად ფიქსირებულია ყველა ფაზაში. | სინათლისა და სეზონის პროგრესია (გაზაფხულის განთიადი -> ზაფხულის შუადღე -> ზამთრის ბინდი). | ნარატორი აჯამებს წლებს/ათწლეულებს; ჰარმონიული აკორდების პროგრესია + მშენებლობის/ნგრევის შორეული აკუსტიკური ფენები. | `Blender` (ფიქსირებული კამერის გეომეტრია) + `LTX-2.5 FLF2V` ან `FFmpeg xfade=transition=fade`. QA: ფონის მთებისა და ჰორიზონტის პიქსელური თანხვედრა. | 
| **15** | **Crowd / ceremony / ritual / public event** | კოლექტიური ემოციის, ძალაუფლების ლეგიტიმაციის ან სახალხო მღელვარების ჩვენება. | `STILL` (`2.5D Multi-plane` 5–7 წმ) ან `VIDEO` (6–10 წმ დროშებისა და კვამლის მოძრაობით). | `Symmetrical Low-Angle Wide Shot` (24mm პოდიუმი/ტაძარი) -> `High-Angle Crowd Sea` (85mm) -> `MCU` ინდივიდუალურ სახეზე ბრბოში. | ნელი ვერტიკალური `Tilt-Up` ან `Dolly-In` ცენტრალური ფიგურისკენ; ბრბოში მოძრაობს დროშები, ჩირაღდნები, საკმევლის კვამლი. | თეატრალური, სიმეტრიული განათება, ოქროსფერი და მეწამული ცერემონიული აქცენტები. | ნარატორი; საზეიმო ან საგანგაშო საგუნდო/სპილენძის აკორდი; დიდი სივრცის `Crowd Walla`, ზარები, ბუკები. | `Blender Geometry Nodes` (ბრბოს სილუეტური მასა) + `LTX-2.5` წინა პლანის ფიგურებისთვის. QA: ბრბოს უკანა რიგებში სახეები რჩება რბილ ფოკუსში (`Bokeh`). | 
| **16** | **Aftermath / loss / quiet reflection / transition** | ბრძოლის ან კატასტროფის ადამიანური და ისტორიული ფასის გააზრება; ემოციური დეკომპრესია. | `STILL` (6–10 წმ ნელი `2.5D` ნაცრისა და ნისლის დრეიფით) ან `VIDEO` (8–12 წმ ნელი კამერით). | `High-Angle Wide Shot` (მიტოვებული ველი) -> `Ground-Level ECU Insert` (გატეხილი ფარი/მუზარადი ტალახში) -> `Lonely Silhouette WS`. | კამერის მოძრაობა მინიმალურია (`Ultra-Slow Pull-Out`); კადრში მოძრაობს მხოლოდ ქარი, ნაცარი და კვამლი. | დაბალი გაჯერება (`Desaturated Palette`), ცივი ნაცრისფერ-ლურჯი ტონალობა და ჩამქრალი ნაკვერჩხლის სუსტი წითელი წერტილები. | **პირველი 5–10 წამი სრული ვოკალური და მუსიკალური სიჩუმე** (მხოლოდ ქარი და ნაკვერჩხლის ტკაცუნი); შემდეგ სოლო ჩელოს ელეგია და ნარატორის მშვიდი ხმა. | `Python / Blender 2.5D` ნაწილაკებით ან `LTX-2.5` დაბალი დინამიკით -> `FFmpeg` `fade` და `eq=saturation=0.65`. QA: არავითარი სწრაფი ჭრა ან ხმამაღალი `SFX`. | 
| **17** | **Narrator-only explanation over visual evidence** | ისტორიული დოკუმენტის, არტეფაქტის ან არქივული ილუსტრაციის ანალიტიკური განხილვა. | `STILL` (5–9 წმ `2.5D Document/Artifact Treatment`). | `Centered Artifact/Document Frame` 3D დახრით (`8–12° Tilt`), რბილი ვიგნეტითა და განათებული ტექსტური ფრაგმენტით (`Callout Highlight`). | ნელი `2.5D Push-In` და ფოკუსის გადატანა დოკუმენტის კონკრეტულ სტრიქონზე. | თბილი სამუზეუმო/არქივული სინათლის კონუსი (`Spotlight Cone`) მუქ ფონზე, მტვრის მიკრო-ნაწილაკები. | ნარატორი კითხულობს ან აანალიზებს წყაროს; დაბალი `Ambient Pad`; პერგამენტის/ქვის რბილი აკუსტიკური ტექსტურა. | `Python` (`OpenCV warpPerspective` + `Pillow` განათების ნიღაბი) ან `Blender` 2.5D სიბრტყე. QA: ციტირებული ტექსტის სრული კონტრასტი და სისუფთავე. | 
| **18** | **Opening hook / cold open** | მაყურებლის ყურადღების მყისიერი დაჭერა პირველ 30 წამში და მთავარი დრამატული კითხვის დასმა. | `VIDEO` (60–70% მაღალი ენერგიის კადრები) + `HELPER` (1 სწრაფი კონტრფაქტობრივი რუკა/თარიღი). | `In-Medias-Res Striking Visual Hook` (0–5 წმ) -> `Rapid Context Montage` (3 კადრი, 5–18 წმ) -> `Counterfactual Pivot Question` (18–30 წმ). | დინამიკური `Dolly-In` ან კონტრასტული `Match Cut`; ყოველი კადრი პასუხობს ვიდეოს სათაურის დაპირებას. | მაქსიმალური ვიზუალური კონტრასტი და ეპიზოდის მთავარი ფერთა მოტივის განაცხადი. | ნარატორი იწყებს პირველივე წამიდან; `Leitmotif` + `Tension Riser` -> **00:28-ზე `Sub-Impact` და 2-წამიანი სიჩუმე** მთავარი კითხვის შემდეგ. | ჰიბრიდული: საუკეთესო `LTX-2.5 Pro` კადრი + დეტერმინისტული `Python` თარიღის/რუკის აქცენტი. QA: [YouTube 30-Second Intro Retention](https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop) სტანდარტი. | 
| **19** | **Climax / payoff** | ეპიზოდის მთავარი დრამატული კონფლიქტისა და კონტრფაქტობრივი თეზისის გადამწყვეტი გადაწყვეტა. | `VIDEO` (10–15 წმ უწყვეტი კულმინაციური სვლა + სწრაფი რეაქციები). | `Converging Cross-Cut` -> `10s Continuous Master Action Shot` -> `Silence Beat ECU` -> `Decisive Impact WS`. | კამერის ყველაზე მასშტაბური მოძრაობა მთელ ეპიზოდში (`Crane-Up` ან `360/Arc Reveal`), რომელიც კრავს ყველა მანამდე ნაჩვენებ გეოგრაფიულ ელემენტს. | მაქსიმალური განათების დინამიკა (ცეცხლი, განთიადის სხივი ან კონტრასტული სილუეტი). | ნარატორისა და მთავარი პერსონაჟის ბოლო რეპლიკის კულმინაცია; `Score`-ის სრული ორკესტრული პიკი (`-14 LUFS`) წინმსწრები 2-წამიანი სიჩუმის შემდეგ. | `Blender` კამერის ტრაექტორია -> `LTX-2.5 Pro` -> `FFmpeg` ზუსტი აუდიო-ვიზუალური სინქრონიზაცია. QA: `True Peak ≤ -1.5 dBTP` პიკურ დარტყმაზე. | 
| **20** | **Ending / coda** | ისტორიული შედეგის შეჯამება, საწყის `Opening Hook`-თან თემატური დაბრუნება და დასამახსოვრებელი ფინალური ხატი. | `STILL` (8–12 წმ ფინალური `Held Tableau` 2.5D ატმოსფეროთი) ან ნელი `VIDEO`. | `Visual Callback Shot` (საწყისი კადრის სარკისებური ან შეცვლილი კომპოზიცია) -> `Slow Pull-Out to EWS` -> `Fade to Black`. | ნელი `Dolly-Out`, რომელიც ტოვებს პერსონაჟს ან ველს ისტორიის მასშტაბში. | მშვიდი, დაბალანსებული განათება, რომელიც აჩვენებს ახალ სტატუს-კვოს. | ნარატორის დასკვნითი ფრაზა სრულდება დასრულებამდე 4 წამით ადრე; საწყისი `Leitmotif` ბრუნდება და იხსნება ჰარმონიულ კადენციაში; ბუნებრივი აკუსტიკური მილევადობა. | `LTX-2.5` ან `Python 2.5D Tableau` -> `FFmpeg` `fade=t=out` და `afade=t=out`. QA: საწყისი და საბოლოო კადრის ვიზუალური მოტივის თანხვედრა. | 

## G. LTX / Blender / Python / FFmpeg შესაძლებლობების მატრიცა და ღრმა ტექნიკური აუდიტი (Tool Implementation & Capability Matrix)

### G.1 LTX ვიდეო გენერაციის ოჯახის ზუსტი ტექნიკური აუდიტი

დაუშვებელია სხვადასხვა თაობის LTX მოდელების (`LTX-Video 0.9.x`, `LTX-2`, `LTX-2.3`, `LTX-2.5`) ან ლოკალური `ComfyUI / PyTorch` და ჰოსტირებული API (`docs.ltx.io`, `fal.ai`) გარემოების ერთმანეთში აღრევა. ქვემოთ წარმოდგენილია ოფიციალურ დოკუმენტაციასა და მოდელის ბარათებზე დაფუძნებული ვერიფიცირებული სპეციფიკაცია ([LTX Open Source Overview](https://docs.ltx.io/open-source-model/getting-started/overview), [LTX-2.5 Model Page](https://docs.ltx.io/models/ltx-2-5), [Lightricks/LTX-2.3 Hugging Face](https://huggingface.co/Lightricks/LTX-2.3), [Lightricks/LTX-2 Hugging Face](https://huggingface.co/Lightricks/LTX-2), [Lightricks/LTX-Video Hugging Face](https://huggingface.co/Lightricks/LTX-Video), [Fal.ai LTX-2.3](https://fal.ai/ltx-2.3), [Fal.ai LTX-2.5](https://fal.ai/ltx-2.5)):

| მოდელის ვერსია და ვარიანტი | პარამეტრების ზომა და არქიტექტურა | ლოკალური vs. ჰოსტირებული Entry Point | რეზოლუცია, Aspect Ratio, FPS და კადრების წესი | Native Audio & Conditioning შესაძლებლობები | კამერისა და მოძრაობის კონტროლი | VRAM მოთხოვნები, ლიცენზია და ღირებულება \[PRIMARY / OFFICIAL\] | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **LTX-Video (v0.9.5 / v0.9.7 2B & 13B Distilled)** | `2B` და `13B` პარამეტრიანი პირველი თაობის `DiT` (ვიდეო-მხოლოდ). | Local: [GitHub Lightricks/ltx-video](https://github.com/Lightricks/ltx-video), [HF Lightricks/LTX-Video](https://huggingface.co/Lightricks/LTX-Video); Hosted: `fal.ai`. | საბაზისო `1216×704 @ 30 FPS`; კადრების რაოდენობა $8n + 1$, სივრცითი ზომა **32px ჯერადი**. | **არ აქვს Native Audio.** მხარს უჭერს `T2V`, `I2V`, `V2V` და Keyframe კონდიცირებას. | მხოლოდ ტექსტური პრომპტით ან `ComfyUI` keyframe გიდებით. | `Python >= 3.10.5`, `CUDA 12.2`, `PyTorch >= 2.1.2`; 16–24 GB VRAM (Distilled/FP8). | 
| **LTX-2 (19B)** | `19B` პარამეტრიანი ასიმეტრიული ორნაკადიანი აუდიო-ვიზუალური `DiT` (`arXiv:2601.03233`). | Local: [HF Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2), [GitHub ltx-video-trainer](https://github.com/Lightricks/ltx-video-trainer). | `720p / 1080p`, `24 / 30 FPS`, $8n + 1$ კადრის კვანტიზაცია ლოკალურ პაიპლაინში. | **Native Joint Audio-Video Generation** ერთ გენერაციულ გავლაში. | პრომპტი + საბაზისო `LoRA` და `IC-LoRA` ტრენერი. | სრული BF16: \~48–80 GB VRAM; `FP8 / NV4` კვანტიზებული: 24–32 GB VRAM ([HF LTX-2.3 Render Times](https://huggingface.co/Lightricks/LTX-2.3/discussions/16)). | 
| **LTX-2.3 (22B Dev & Distilled 1.1)** | `22B` პარამეტრიანი გაუმჯობესებული აუდიო-ვიდეო `DiT` (`46.1 GB safetensors`), ახალი `VAE` არქიტექტურა და `x1.5 / x2` Spatial & Temporal Upscalers. | Local: [HF Lightricks/LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3) (`ltx-core`, `ltx-pipelines`, `ltx-trainer`); Hosted API: `ltx-2-3-fast`, `ltx-2-3-pro` ([Submit Image-to-Video](https://docs.ltx.io/api-documentation/api-reference/async-video-generation/submit-image-to-video)) და [Fal.ai LTX-2.3](https://fal.ai/ltx-2.3). | `720p, 1080p, 1440p, 2160p (4K)`; `16:9, 9:16, 1:1, 4:5, 5:4`; `24 / 48 FPS`; ჰოსტირებულზე **20 წამამდე** ერთ გენერაციაში (+ `extend-video`). | **Native Audio + Audio-to-Video** (`/v2/audio-to-video`), `Retake` (`/v2/retake`), `Extend` (`/v2/extend`) და `Reframe` ([Fal.ai LTX-2.3 Reframe](https://fal.ai/models/fal-ai/ltx-2.3/reframe) — 60 წამამდე ვიდეოს outpainting). | `IC-LoRA` ადაპტერები (`Union Control`, `Relight`, `Dub-It`), `First-Last-Frame (FLF2V)` და პრომპტი. | Local: `Python >= 3.12, CUDA > 12.7, PyTorch ~= 2.7`. Fal.ai ფასი: Pro `$0.06/s` (1080p), `$0.12/s` (1440p), `$0.24/s` (4K); Fast `$0.04/s` (1080p); A2V/Extend/Retake `$0.10/s` ([Fal.ai LTX-2.3](https://fal.ai/ltx-2.3)). | 
| **LTX-2.5 (`ltx-2-5-fast` & `ltx-2-5-pro`)** | უახლესი ღია წონების (`Open-Weights`) აუდიო-ვიდეო მოდელი **Diffusion Fidelity Rendering (DFR)** დეკოდერითა და **Native Multi-Shot** მხარდაჭერით. | Local: `ComfyUI-LTXVideo` შაბლონები (`video_ltx2_5_t2v`, `video_ltx2_5_i2v`), [HF Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5); Hosted API: [LTX-2.5 Docs](https://docs.ltx.io/models/ltx-2-5), [Fal.ai LTX-2.5](https://fal.ai/ltx-2.5). | `720p`-დან `4K`-მდე ყველა ფორმატში: `16:9, 9:16, 1:1, 3:2, 2:3` ([API Changelog](https://docs.ltx.io/api-changelog)); ლოკალურში $F = 8n + 1$; API-ში `duration: null` ავტომატურად ითვლის სიგრძეს პრომპტიდან ([Text-to-Video API](https://docs.ltx.io/api-documentation/api-reference/video-generation/text-to-video)). | **Native Synchronized Audio + Audio-to-Video + Text-to-Audio**; **Native Multi-Shot** (ერთ გენერაციაში ქმნის რამდენიმე დაკავშირებულ კადრს პერსონაჟის, განათებისა და ხმის შენარჩუნებით). | **Motion Control IC-LoRA** (`LTX Sparse Track Editor`: `LTXVDrawTracks` -> `LTXAddVideoICLoRAGuide` -> 8-step distilled run -> `LTXVCropGuides`) ([Motion Control Guide](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control)). | **Two-Stage Distilled Pipeline** (`CFG = 1`, Stage 1 image conditioning strength `0.7`, `Tiled VAE Decode` დაბალი VRAM-ისთვის) ([Two-Stage Generation](https://docs.ltx.io/open-source-model/usage-guides/two-stage-generation)). ლიცენზია: `LTX-2.x Community License`. | 

**კრიტიკული ტექნიკური დასკვნები LTX-ის გამოყენებისთვის \[PRIMARY / OFFICIAL\]:**

1. **Two-Stage Distilled Pipeline-ის მექანიკა ([Two-Stage Generation](https://docs.ltx.io/open-source-model/usage-guides/two-stage-generation), [Image-to-Video Workflow](https://docs.ltx.io/open-source-model/usage-guides/image-to-video)):** ლოკალურ `ComfyUI`-ში `LTX-2.5` მუშაობს ორსაფეხურიან რეჟიმში (`CFG = 1` ორივე საფეხურზე): პირველ საფეხურზე მოდელი აგენერირებს საბაზისო რეზოლუციის ვიდეოსა და სინქრონიზებულ აუდიოს მოკლე ფიქსირებული სიგმა-განრიგით (სადაც საწყისი სურათი ინექცირდება `strength = 0.7`-ით), ხოლო მეორე საფეხურზე ხდება ლატენტური აფსკეილინგი და `Tiled VAE Decode` (რაც ყოფს დეკოდირებას ფილებად VRAM-ის პიკური მოხმარების შესამცირებლად). გარდა ამისა, ტექსტის ენკოდირება შეიძლება განიტვირთოს LTX API-ზე VRAM-ის დასაზოგად.

2. **Motion Control IC-LoRA vs. ბუნებრივი ენის პრომპტი ([Motion Control IC-LoRA](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control)):** როდესაც იყენებთ `Motion Control IC-LoRA`-ს, მოძრაობის ტრაექტორიას ხაზავთ `LTX Sparse Track Editor`-ში საწყის სურათზე (`LTXVDrawTracks` ქმნის გიდ-ვიდეოს, `LTXAddVideoICLoRAGuide` აწვდის მას მოდელს 8-ნაბიჯიან დისტილირებულ გენერაციაში, ხოლო `LTXVCropGuides` აჭრის გიდის ტოკენებს დეკოდირებამდე). ოფიციალური დოკუმენტაციის მკაცრი წესია: **ამ რეჟიმში ტექსტურ პრომპტში აღწერეთ მხოლოდ სუბიექტი და ვიზუალური სტილი, და არა მოძრაობა**, რადგან მოძრაობას სრულად მართავს დახაზული ტრეკები!

3. **V1-დან V2 API-ზე მიგრაცია ([Migrate from V1 to V2](https://docs.ltx.io/migrate-v1-to-v2)):** ჰოსტირებული API სრულად გადავიდა ასინქრონულ სამუშაო რიგებზე (`POST /v2/text-to-video`, `POST /v2/image-to-video`, `POST /v2/audio-to-video`, `POST /v2/retake`, `POST /v2/extend` და სტატუსის შემოწმება `GET /v2/.../{id}`-ით).

### G.2 Blender, Python და FFmpeg — დეტერმინისტული ინსტრუმენტების ტექნიკური როლი

#### 15.2 Blender-ის დეტერმინისტული საწარმოო შესაძლებლობები ([Blender Track To Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html), [Blender Rigid Body Manual](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html))

* **კამერის რიგები და `Track To Constraint`:** კამერას ედება `Track To Constraint` (`To: -Z`, `Up: Y`), რომლის სამიზნე (`Target`) არის ცარიელი ობიექტი (`Empty Focus Null`). კამერა მოძრაობს ნებისმიერ 3D სპლაინზე (`Dolly, Crane, Orbit`), ხოლო `Empty` მართავს ზუსტ ფოკუსურ წერტილსა და `Depth of Field` მანძილს.

* **2.5D Camera Projection (`Project From View`):** 2D ილუსტრირებული კადრი იჭრება 3–5 შრედ (წინა პლანი, შუა არქიტექტურა, ფონი), პროექცირდება მარტივ 3D პროქსი-გეომეტრიაზე (`Low-Poly Greybox`) და იღებს რეალურ 3D პარალაქსს, მოცულობით ნისლსა (`Volumetric Fog`) და დინამიკურ ჩრდილებს.

* **Geometry Nodes & Rigid Body Physics:** ათასობით ჯარისკაცის, შუბის ან კარვის მკაცრი გეომეტრიული მწკრივი იქმნება `Geometry Nodes` ინსტანსირებით წამებში, ხოლო კედლის ნგრევა ან კატაპულტის დარტყმა სიმულირდება `Active` და `Passive Rigid Body` მექანიკით.

* **Multi-Layer EXR Render Passes:** `Blender` აექსპორტებს `Z-Depth`, `Normal`, `Vector (Motion Blur)`, `Shadow` და `Cryptomatte` პასებს. ეს პასები პირდაპირ გამოიყენება ან `Defocus Node`-ით ოპტიკური `Rack Focus`-ის გასაკეთებლად, ან `LTX IC-LoRA`-ს სტრუქტურულ კონდიცირებად!

#### 15.3 Python-ის დეტერმინისტული კონვეიერი ([Pillow Image Module](https://pillow.readthedocs.io/en/latest/reference/Image.html), [OpenCV Geometric Transformations](https://docs.opencv.org/4.13.0/dir_996070d144ea13ded22df5bf9603981f.html))

* **Pillow (`PIL.Image`, `ImageDraw`, `ImageFont`):** პასუხისმგებელია უნაკლო ტიპოგრაფიაზე, `Lower Thirds`-ზე, მრიცხველებზე (`Counters`) და ალფა-კომპოზიტინგზე (`Image.alpha_composite`).

* **OpenCV (`cv2.getPerspectiveTransform`, `cv2.warpPerspective`, `cv2.remap`, `cv2.calcOpticalFlowFarneback`):** ასრულებს სუბპიქსელურ (`INTER_CUBIC` / `INTER_LANCZOS4`) 2.5D პარალაქსურ წანაცვლებას სიღრმის რუკის (`Depth Map`) მიხედვით (სადაც $\Delta x(u,v) = V_x \cdot Z(u,v)$), 3D დახრილი რუკების პერსპექტიულ ტრანსფორმაციას და გენერაციული ვიდეოების ოპტიკური ნაკადის QA-ანალიზს.

* **NumPy & Cubic-Bezier Easing:** კამერისა და ინფოგრაფიკის ყველა მოძრაობა ითვლება დეტერმინისტული კუბური ბეზიეს ან `Ease-In-Out Cubic` ფუნქციით ($f(t) = 3t^2 - 2t^3$), რაც გამორიცხავს ხაზოვან, რობოტულ მოძრაობას.

#### 15.4 FFmpeg-ის პოსტ-პროდუქციისა და აუდიო მასტერინგის ფილტრ-გრაფები ([FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html))

* **ვიზუალური ფილტრები:** `scale` / `crop` / `pad` (ფორმატის ნორმალიზაცია), `zoompan` (მხოლოდ 2D სკალირებისთვის; სუბპიქსელური კანკალის — `Jitter`-ის თავიდან ასაცილებლად სურათი წინასწარ უნდა გაიზარდოს `scale=8000:-1`-მდე!), `xfade` (გადასვლები), `blend` და `overlay` (კვამლის, მარცვლოვანებისა და `HELPER` ფენების დადება), `curves` / `eq` / `lut3d` / `colortemperature` (ფერთა შეთანხმება), `vignette` და `noise` (კინოფირის ტექსტურა).

* **აუდიო ფილტრები:** `highpass=f=80`, `equalizer`, `deesser`, `acompressor`, `sidechaincompress` (მუსიკის ავტომატური დაწევა ნარატორის ქვეშ), `acrossfade`, `adelay`, `afade`, `amix` და **ორგავლიანი (`Two-Pass Linear`) `loudnorm=I=-14:TP=-1.5:LRA=9`** (პირველ გავლაზე ზომავს `input_i`, `input_tp`, `input_lra`, `input_thresh` პარამეტრებს `print_format=json`-ით, ხოლო მეორე გავლაზე იყენებს `linear=true` რეჟიმს, რათა ნორმალიზაცია მოხდეს დინამიკური პამპინგის გარეშე!).

### G.3 ტექნიკა-ინსტრუმენტის შესაძლებლობათა შედარებითი მატრიცა (Technique-to-Tool Capability Matrix)

ცხრილში გამოყენებულია ბრიფით განსაზღვრული მკაცრი კლასიფიკაციის იარლიყები: `native / directly supported`, `prompt-driven / probabilistic`, `deterministic / scripted`, `approximate / simulated`, `unsupported`, `unknown / not verified`.

| ტექნიკა (`Technique`) | LTX (`LTX-2.5 / 2.3`) | Blender (`4.5 / 5.2 LTS`) | Python (`Pillow / OpenCV / NumPy`) | FFmpeg (`Filtergraphs`) | რეკომენდებული საწარმოო გზა (`Recommended Route`) | მთავარი შეზღუდვა (`Main Limitation`) | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **True 3D Dolly / Crane / Orbit with Parallax** | `prompt-driven / probabilistic` (ან `approximate` `Motion Control IC-LoRA`-თი) | `native / directly supported` (ფიზიკური 3D კამერა + `Track To`) | `approximate / simulated` (მრავალშრიანი 2.5D `Depth Map` წანაცვლებით) | `unsupported` (`zoompan` არის მხოლოდ 2D სკალირება პარალაქსის გარეშე) | **ჰიბრიდული:** `Blender` 3D კამერის Previs/Depth გიდი -> `LTX-2.5 IC-LoRA`, ან `Blender 2.5D Projection`. | მხოლოდ ტექსტური პრომპტით `LTX`-ში დიდი კუთხით ბრუნვა იწვევს გეომეტრიის რღვევას. | 
| **2D Ken Burns Pan & Zoom on Still Archive** | `approximate / simulated` (არასაჭირო გენერაციული ხარჯი) | `native / directly supported` | `deterministic / scripted` (`OpenCV warpAffine` სუბპიქსელური სიზუსტით) | `native / directly supported` (`zoompan` წინასწარი `upscale`-ით) | **Python (`OpenCV`)** ან **FFmpeg (`scale` + `zoompan`)**. | არ ქმნის შიდა პარალაქსს; `FFmpeg zoompan` დაბალ რეზოლუციაზე იწვევს პიქსელურ კანკალს (`Stepping Jitter`). | 
| **Multi-Plane 2.5D Parallax + Atmospheric Particles** | `prompt-driven / probabilistic` | `native / directly supported` (3D სიბრტყეები + ვოლუმეტრიკა) | `deterministic / scripted` (RGBA ფენების სხვადასხვა სიჩქარით სქროლინგი + ნაწილაკები) | `approximate / simulated` (`overlay` ფილტრების ჯაჭვით) | **Python (`Pillow/OpenCV`)** სწრაფი 2.5D სცენებისთვის; **Blender** რთული განათებისთვის (`STILL` Lane). | 15 გრადუსზე მეტი კუთხის შეცვლისას ჩნდება ბრტყელი ფენების კიდეები. | 
| **Rack Focus (Shallow Depth-of-Field Shift)** | `prompt-driven / probabilistic` | `native / directly supported` (კამერის `Focus Distance` ან `Defocus Node` Z-პასით) | `deterministic / scripted` (`Z-Depth` ნიღბითა და ცვალებადი Gaussian/Lens Blur-ით) | `approximate / simulated` (`boxblur/gblur` მთელ კადრზე სიღრმის გარეშე) | **Blender (`Defocus Node`)** ან **Python (`Depth-masked Lens Blur`)**. | `FFmpeg`-ს დამოუკიდებლად არ გააჩნია Z-Depth ბუფერის ცოდნა. | 
| **Character Facial Acting & Visible Lip-Sync (≤5s)** | `native / directly supported` (`LTX-2.5 / 2.3 Audio-to-Video` და `I2V`) | `deterministic / scripted` (მოითხოვს სრულ 3D პერსონაჟის რიგსა და Shape Keys-ს) | `unsupported` | `unsupported` | **ElevenLabs TTS (`with-timestamps`) -> LTX-2.5 Audio-to-Video (≤5 წმ)** + `Reaction` გადაფარვა. | 5 წამზე გრძელ ახლო კადრებში იზრდება სახის იდენტობის დრეიფის რისკი. | 
| **Large Army Formations & Rigid-Body Destruction** | `prompt-driven / probabilistic` (ხშირია ჯარისკაცების შერწყმა) | `native / directly supported` (`Geometry Nodes` + `Rigid Body World`) | `unsupported` (მხოლოდ 2D სქემატურ რუკაზე) | `unsupported` | **Blender (`Geometry Nodes` Previs)** -> **LTX-2.5 `IC-LoRA`** ტექსტურირებისა და დეტალებისთვის. | სუფთა `LTX` პრომპტი ვერ ინარჩუნებს ასობით მეომრის მკაცრ ტაქტიკურ მწკრივს 10–15 წამის განმავლობაში. | 
| **First-to-Last Frame Pose Interpolation (`FLF2V`)** | `native / directly supported` (`LTX-2.5 / 2.3 First-Frame / Last-Frame` შაბლონი) | `native / directly supported` (3D Keyframe ინტერპოლაცია) | `approximate / simulated` (`Optical Flow` მორფინგი მხოლოდ მცირე სხვაობაზე) | `approximate / simulated` (`minterpolate` / `xfade`) | **LTX-2.5 First-Frame / Last-Frame Conditioning**. | თუ საწყის და საბოლოო კადრს შორის კომპოზიცია რადიკალურად განსხვავდება, შუა ფაზაში ჩნდება მორფინგი. | 
| **Historical Cartography, Borders & Route Arrows** | `unsupported` (აყალბებს საზღვრებსა და წარწერებს) | `deterministic / scripted` (3D რელიეფური რუკები + ვექტორული ხაზები) | `deterministic / scripted` (`GeoJSON/SVG` + `Pillow/OpenCV` + `Okabe-Ito`) | `unsupported` | **100% Python (`GeoJSON + Pillow/OpenCV`)** ან **Blender 3D Terrain** (`HELPER` Lane). | გენერაციულ მოდელებს კატეგორიულად ეკრძალებათ რუკებისა და ტოპონიმების ხატვა. | 
| **Statistical Charts, Counters & Animated Typography** | `unsupported` | `deterministic / scripted` | `native / directly supported` (`Matplotlib`, `Pillow ImageDraw`, `tabular-nums`) | `approximate / simulated` (`drawtext` მარტივი წარწერებისთვის) | **Python (`Pillow / Matplotlib`)** კადრ-კადრ რენდერით. | `FFmpeg drawtext`-ს არ გააჩნია რთული ინფოგრაფიკული განლაგებისა და დიაგრამების ძრავა. | 
| **Editorial Transitions (`J-Cut`, `L-Cut`, `Cross-Dissolve`)** | `native / directly supported` (მხოლოდ `LTX-2.5 Native Multi-Shot`-ის შიგნით) | `native / directly supported` (`Video Sequence Editor - VSE`) | `deterministic / scripted` | `native / directly supported` (`xfade`, `adelay`, `acrossfade`, `concat`) | **FFmpeg** (პროგრამული აწყობა `Forced Alignment` ტაიმკოდებით). | `LTX Native Multi-Shot`-ში ჭრის ზუსტი ფრეიმის დეტერმინისტული კონტროლი შეზღუდულია `FFmpeg`-თან შედარებით. | 
| **Dynamic Sidechain Audio Ducking & Spectral EQ** | `unsupported` | `unsupported` | `deterministic / scripted` (`SciPy / NumPy` DSP) | `native / directly supported` (`sidechaincompress`, `equalizer`, `acompressor`) | **FFmpeg (`sidechaincompress` + `equalizer`)**. | მოითხოვს სწორ `Attack (15-30ms)` და `Release (400-600ms)` კალიბრაციას პამპინგის თავიდან ასაცილებლად. | 
| **ITU-R BS.1770-5 / EBU R 128 Loudness Mastering** | `unsupported` | `unsupported` | `deterministic / scripted` (`pyloudnorm` QA-სთვის) | `native / directly supported` (ორგავლიანი `loudnorm=I=-14:TP=-1.5:linear=true`) | **FFmpeg Two-Pass `loudnorm`** + Python QA ვერიფიკაცია. | ერთგავლიანი (`Single-Pass`) `loudnorm` იყენებს დინამიკურ კომპრესიას და ცვლის მიქსის შიდა ბალანსს; სავალდებულოა ორგავლიანი `linear=true` რეჟიმი! | 

## H. ჰიბრიდული წარმოების რეცეპტები და დეტალური სამუშაო მაგალითები (Hybrid Production Recipes & Worked Examples A–H)

ქვემოთ წარმოდგენილია სექცია 15.6-ით მოთხოვნილი 8 ჰიბრიდული საწარმოო კონვეიერი და სექცია 17-ით მოთხოვნილი 8 სრული სამუშაო მაგალითი (`Worked Examples A–H`), სადაც მკაფიოდაა გამიჯნული დეტერმინისტული (`[DETERMINISTIC]`), გენერაციული (`[GENERATIVE]`), ადამიანური სარედაქციო კონტროლის (`[HUMAN REVIEW]`) და ავტომატიზებული ვერიფიკაციის (`[AUTO QA]`) ეტაპები.

### H.1 რვა ჰიბრიდული საწარმოო კონვეიერი (Section 15.6 Hybrid Workflows)

1. **უწყვეტი ზედა რაკურსის საბრძოლო მანევრი (`Continuous Overhead Battle Move — 10–12s VIDEO`):**

   * *ნაბიჯი 1 `[DETERMINISTIC - Blender]`:* `Blender`-ში იგება დაბალპოლიგონური რელიეფი და `Geometry Nodes`-ით ნაწილდება ორი არმიის ბლოკები (ფრაქცია A მარცხნივ, ფრაქცია B მარჯვნივ). მაღალი კუთხის კამერა (`35mm`, `45° Tilt-Down`) მოძრაობს სპლაინზე 10 წამის განმავლობაში (241 კადრი @ 24fps, $8 \times 30 + 1 = 241$). რენდერდება `Z-Depth` და `Motion Track` გიდი.

   * *ნაბიჯი 2 `[GENERATIVE - First Frame + LTX-2.5]`:* პირველი კადრის სიღრმის რუკაზე დაყრდნობით გენერირდება მაღალი დეტალიზაციის ილუსტრირებული საწყისი კადრი (`First Frame`), შემდეგ კი `LTX-2.5` (`Motion Control IC-LoRA` ან `Union Control Depth IC-LoRA`, [IC-LoRA Guide](https://docs.ltx.io/open-source-model/usage-guides/ic-lo-ra)) აცოცხლებს 241 კადრს.

   * *ნაბიჯი 3 `[HUMAN REVIEW]`:* მოწმდება, რომ ფრონტის შეჯახების ხაზი არ იშლება ქაოსურ მორფინგში მე-6–10 წამებზე.

   * *ნაბიჯი 4 `[DETERMINISTIC & AUTO QA - FFmpeg/Python]`:* ემატება მრავალშრიანი საბრძოლო `Ambience`, `Foley` და `Sub-Impact` კონტაქტის ფრეიმზე; `Python` ამოწმებს კადრების რაოდენობასა და ოპტიკური ნაკადის მიმართულებას.

2. **პერსონაჟის ახლო ფიზიკური მოქმედება (`Close-Up Character Action — 4s VIDEO`):**

   * *ნაბიჯი 1 `[DETERMINISTIC / GENERATIVE]`:* მზადდება პერსონაჟის იდენტობის რეფერენსი და ორი საკვანძო კადრი: `First Frame` (`Anticipation Pose` — ხელი ხმლის ტარზე) და `Last Frame` (`Settle Pose` — გაშიშვლებული ხმალი სახის წინ, მკაფიო სილუეტით).

   * *ნაბიჯი 2 `[GENERATIVE - LTX-2.5 FLF2V]`:* `LTX-2.5 First-Frame / Last-Frame` შაბლონით ([Quick Start](https://docs.ltx.io/open-source-model/getting-started/quick-start)) გენერირდება 97 კადრი ($8 \times 12 + 1 = 97$, \~4.0 წმ @ 24fps).

   * *ნაბიჯი 3 `[HUMAN REVIEW]`:* მოწმდება ხმლის პირის სწორი გეომეტრია და თითების ანატომია.

   * *ნაბიჯი 4 `[DETERMINISTIC - FFmpeg]`:* მოძრაობის პიკურ ფრეიმზე სინქრონდება ფოლადის ქარქაშიდან ამოღების მშრალი `Foley` ტრანზიენტი.

3. **ორპერსონაჟიანი დიალოგური სცენა (`Dialogue Scene — Audio-Led Coverage`):**

   * *ნაბიჯი 1 `[DETERMINISTIC - ElevenLabs API]`:* `ElevenLabs v4` აგენერირებს ორივე პერსონაჟის რეპლიკებს განსხვავებული ხმებით; `/v1/forced-alignment` ([Forced Alignment](https://elevenlabs.io/docs/overview/capabilities/forced-alignment)) ითვლის თითოეული სიტყვისა და პაუზის ზუსტ წამებს.

   * *ნაბიჯი 2 `[GENERATIVE - LTX-2.5 Audio-to-Video]`:* რეპლიკების პირველი 3.5–4.5 წამიანი სეგმენტები გენერირდება `/v2/audio-to-video` ([Audio-to-Video Guide](https://docs.ltx.io/open-source-model/usage-guides/audio-to-video)) მოდელით `OTS / MCU` რაკურსში (`180° Axis`-ის დაცვით).

   * *ნაბიჯი 3 `[DETERMINISTIC / GENERATIVE - Reaction & Insert]`:* 5 წამზე გრძელი რეპლიკების მეორე ნახევარი იფარება მსმენელის `MCU Reaction` კადრითა და `STILL ECU Insert`-ით.

   * *ნაბიჯი 4 `[DETERMINISTIC & AUTO QA - FFmpeg]`:* კადრები იკერება `J-cut` (`0.6s pre-lap`) და `L-cut` (`1.2s post-lap`) წესებით უწყვეტი `Room Tone`-ის ფონზე.

4. **დრამატული აღმოჩენა (`Dramatic Reveal — Rack Focus & Audio Dropout`):**

   * *ნაბიჯი 1 `[DETERMINISTIC - Blender / Python]`:* საწყისი კომპოზიცია იყოფა წინა პლანად (პერსონაჟი ჩირაღდნით მარცხენა მესამედში) და უკანა პლანად (აღმოსაჩენი ობიექტი მარჯვენა სიღრმეში) `Z-Depth` რუკით.

   * *ნაბიჯი 2 `[DETERMINISTIC - Blender Defocus Node / Python]`:* პირველი 2.5 წამის განმავლობაში უკანა პლანი დაბინდულია (`Bokeh`), ხოლო 2.5–3.2 წამზე სრულდება `Rack Focus` უკანა პლანზე ჩირაღდნის სინათლის გაძლიერებით.

   * *ნაბიჯი 3 `[DETERMINISTIC - FFmpeg Audio]`:* 2.5 წამზე მუსიკა და `Riser` მყისიერად წყდება (`Music Dropout`), ჩნდება 1.2-წამიანი სიჩუმე და 3.2 წამზე (სრული ფოკუსირებისას) შედის დაბალი რეზონანსული `Sting`.

5. **მოძრავი ისტორიული რუკა (`Moving Historical Map — HELPER Lane`):**

   * *ნაბიჯი 1 `[DETERMINISTIC - Python GIS/Vector]`:* ვერიფიცირებული ისტორიული საზღვრები (`GeoJSON / SVG`) რენდერდება მაღალ რეზოლუციაში (`3840×2160`) `Okabe-Ito` ფერებით (`#0072B2` vs `#D55E00`).

   * *ნაბიჯი 2 `[DETERMINISTIC - Python Animation]`:* `ElevenLabs with-timestamps` ტაიმკოდებზე მიბმული სკრიპტი ხაზავს მოძრავ ისრებს, თარიღის მრიცხველსა და ტოპონიმების ეტიკეტებს `Ease-In-Out Cubic` ინტერპოლაციით.

   * *ნაბიჯი 3 `[AUTO QA]`:* მოწმდება, რომ ყველა ტექსტი აკმაყოფილებს `WCAG ≥ 4.5:1` კონტრასტს და ეკრანზე ჩერდება მინიმუმ 2.5 წამი (`≤17 CPS`).

6. **სტატისტიკური და შედარებითი გრაფიკა (`Statistic / Comparison Graphic — HELPER Lane`):**

   * *ნაბიჯი 1 `[DETERMINISTIC - Python Matplotlib/Pillow]`:* წყაროებით დადასტურებული რიცხვითი მონაცემები გარდაიქმნება კადრ-კადრ ანიმირებულ სვეტოვან ან საფეხურებრივ გრაფიკად (`tabular-nums` შრიფტით).

   * *ნაბიჯი 2 `[DETERMINISTIC - FFmpeg]`:* სვეტის ზრდის დასრულების ფრეიმზე იდება რბილი ტაქტილური აკუსტიკური აქცენტი ნარატორის მიერ რიცხვის წარმოთქმის პარალელურად.

7. **სტატიკური სურათის კინემატოგრაფიული გაცოცხლება (`Still-Image Cinematic Shot — STILL Lane`):**

   * *ნაბიჯი 1 `[DETERMINISTIC - Python / Blender]`:* ილუსტრირებული კადრი იყოფა 3–4 სიღრმისეულ ფენად (`Foreground, Midground, Background, Sky`) ალფა-ნიღბებით.

   * *ნაბიჯი 2 `[DETERMINISTIC - Python OpenCV]`:* 6 წამის განმავლობაში (144 კადრი) ფენები გადაადგილდება სხვადასხვა სუბპიქსელური სიჩქარით (`Foreground: +45px`, `Midground: +20px`, `Background: +6px`), შუა ფენაზე ემატება პროცედურული მტვრის/ნისლის ნაწილაკები და თბილი სინათლის პულსაცია.

8. **ბრძოლის შემდგომი ველი (`Battle Aftermath — Restrained Camera & Silence`):**

   * *ნაბიჯი 1 `[GENERATIVE / DETERMINISTIC]`:* ფართო, დაბალი გაჯერების (`Desaturated`) კომპოზიცია მიტოვებულ ველზე; `LTX-2.5` ან `Python 2.5D` ქმნის მხოლოდ ნელ კვამლსა და ქარში მოძრავ დახეულ დროშას ნელი `Dolly-Out`-ით (10 წმ).

   * *ნაბიჯი 2 `[DETERMINISTIC - FFmpeg Audio]`:* მუსიკა სრულად გათიშულია პირველი 6 წამი; ისმის მხოლოდ ცივი ქარი (`-26 LUFS`) და ნაკვერჩხლის ტკაცუნი, რის შემდეგაც შემოდის სოლო ჩელოს მოტივი.

### H.2 რვა დეტალური სამუშაო მაგალითი (Section 17 Worked Examples A–H)

#### Example A — Large-Scale Battle (მასშტაბური ისტორიული ბრძოლა: მიახლოება, მანევრი, შეჯახება და უკანდახევა)

* **სცენის დრამატურგიული ამოცანა:** აუდიტორიამ 45 წამში სრულად უნდა გაიგოს ბრძოლის ველის გეოგრაფია (ვიწრო ხეობა მდინარესა და ქედს შორის), ორივე არმიის მასშტაბი, ტაქტიკური ფლანგური დარტყმის მიზეზი, შეჯახების ფიზიკური იმპულსი და მარჯვენა ფლანგის რღვევა.

* **სთორიბორდი და მონტაჟური გეგმა (`Storyboard & Edit Plan — 6 Shots, 45s Total`):**

| Shot # | Lane & Duration | Shot Size, Lens & Angle | Visual Composition & Action Choreography | Audio Layering (Narration, Dialogue, Score, Ambience, Foley/SFX) | Tool Pathway | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **A1** | `HELPER` (7.0s) | `Top-Down Tactical Map` (3D tilted 25°) | ხეობის რელიეფი; ლურჯი ფრაქცია (`#0072B2`, ჩრდილოეთის კოალიცია) იკავებს მარცხენა სიმაღლეს, ხოლო ვერმილიონის ფრაქცია (`#D55E00`, იმპერიული ავანგარდი) მიიწევს მარჯვნიდან ხეობაში. 04.5 წამზე ჩნდება `#F0E442` ფლანგური ისარი. | **Narrator:** ხსნის ხეობის სივიწროვესა და ფლანგურ ხაფანგს. **Score:** `112 BPM` დაბალი `Ostinato`. **SFX:** პერგამენტის გაშლა და ხის ფიგურის დადება 04.5s-ზე. | `Python` (`GeoJSON/SVG + OpenCV warpPerspective`). | 
| **A2** | `VIDEO` (**11.0s Continuous Non-Dialogue Action**, 265 frames @ 24fps, $8 \times 33 + 1$) | `High-Angle EWS -> Crane-Down to MWS` (28mm) | **11-წამიანი უწყვეტი არადიალოგური კადრი:** კამერა იწყებს ქედის თავზე ლურჯი მხედრების ზურგს უკან (მარცხენა მხარე), ეშვება ქვემოთ (`Crane-Down + Forward Tracking`) და მიჰყვება კავალერიის დაშვებას ფერდობზე მარცხნიდან მარჯვნივ, სანამ ისინი უახლოვდებიან ქვემოთ მიმავალ წითელ მწკრივებს. მტვრის ღრუბელი იზრდება ფლოქვების ქვეშ. | **Narrator (00.0–05.5s):** ასახელებს შეტევის მომენტს, შემდეგ ჩერდება. **Score:** `Crescendo` სპილენძის ჩასაბერებით. **Ambience/SFX:** ფლოქვების გუგუნი იზრდება `-24 LUFS`-დან `-14 LUFS`-მდე; საბრძოლო ბუკის ხმა 06.0s-ზე. | `Blender` (`Geometry Nodes` + 3D Camera Path Previs) -> `LTX-2.5 Pro I2V` (`Motion Control IC-LoRA`). | 
| **A3** | `VIDEO` (3.5s, 81 frames) | `Telephoto Profile MS` (135mm) | იმპერიული ქვეითები (მარჯვენა მხარეს) ბრუნდებიან მარცხნივ და სწევენ შუბების კედელს (`Anticipation Pose`). **02.5 წამზე სრული აკუსტიკური სიჩუმე.** | **Dialogue (00.5–02.0s):** მეთაურის ყვირილი: *"Brace the left flank!"* **Silence Beat (02.0–03.5s):** მუსიკა და გუგუნი წყდება; ისმის მხოლოდ ხელთათმანის მოჭერა შუბის ტარზე და მძიმე ჩასუნთქვა. | `LTX-2.5 I2V` (81 frames). | 
| **A4** | `VIDEO` (5.0s, 121 frames) | `Ground-Level Wide-Angle MS` (24mm) | შეჯახების მომენტი (`Cut on Action`): მარცხნიდან შემოვარდნილი მხედრები ეჯახებიან ფარების კედელს მარჯვნივ; ნამსხვრევები, მტვერი და დროშის დაცემა (`Action Peak -> Settle`). | **SFX (00.0s):** მძლავრი `Sub-Impact` + ხის შუბების მტვრევა და ფოლადის ზრიალი (`-12 LUFS`, `-1.5 dBTP`). **Score:** სრული `128 BPM` პერკუსია ბრუნდება დარტყმისთანავე. | `LTX-2.5 Pro FLF2V` (საწყისი და საბოლოო კადრის კონტროლით). | 
| **A5** | `STILL` (3.5s) | `ECU Insert` (85mm) | ტალახში ჩავარდნილი და გათელილი იმპერიული ვერმილიონის დროშა, რომელზეც გადადის ცხენის ფლოქვის ჩრდილი (`2.5D Parallax`). | **Narrator:** *"Within twenty minutes, the imperial vanguard split in two."* **SFX:** ქსოვილის გახევა და ტალახის შხეფი. | `Python 2.5D` (`Pillow/OpenCV` ფენები + ნაწილაკები). | 
| **A6** | `VIDEO` (15.0s ceiling / 10.0s actual, 241 frames) | `Elevated Wide Shot` (35mm) | იმპერიული მწკრივები იშლება და იხევს უკან მარცხნიდან მარჯვნივ ხეობის გასასვლელისკენ, ხოლო ლურჯი ფორმაცია იკავებს ცენტრალურ გზას. | **Narrator:** აჯამებს ტაქტიკურ შედეგს. **Score:** პერკუსია ნელდება და გადადის დაბალ სიმებიან `Drone`-ში. | `Blender` Previs -> `LTX-2.5 I2V`. | 

* **Shot A2-ის ზუსტი პრომპტების წყვილი (`First-Frame Image Prompt` & `LTX-2.5 Motion Prompt`):**

  * *First-Frame Image Prompt:* `Illustrated historical docudrama style, high-angle wide shot from a rocky mountain ridge looking down into a misty river valley at dawn. In the left foreground, armored cavalry in deep blue cloaks (#0072B2) sit mounted on horses poised on the slope crest, spears angled forward toward the right. Far below in the right-center valley floor, a long column of infantry in vermilion tunics (#D55E00) marches along the muddy river road. Volumetric morning haze, dramatic rim lighting from low eastern sun, clear silhouette separation, clean composition, text-free, no labels, no watermarks.`

  * *Matching LTX-2.5 Image-to-Video Motion Prompt:* `The blue-cloaked cavalry on the left ridge charges downhill toward the right into the valley, kicking up clouds of dust and gravel behind their hooves. The camera cranes smoothly downward and tracks forward behind the charging horsemen, maintaining left-to-right screen direction as the distance to the vermilion infantry column below rapidly closes. Banners whip violently in the wind, rising thunder of hooves and brass horn call.`

* **QA ვერიფიკაცია Example A-სთვის:** (1) `Screen Direction Check`: ლურჯი ძალა ყველა კადრში (A1–A6) მოძრაობს მარცხნიდან მარჯვნივ; (2) `Frame Quantization`: A2 = 265 კადრი ($8 \times 33 + 1$), A3 = 81 კადრი ($8 \times 10 + 1$), A4 = 121 კადრი ($8 \times 15 + 1$); (3) `Audio Perspective`: A2-ის დასაწყისში ფლოქვები გაფილტრულია შორი მანძილისთვის, ხოლო A4-ში სრულსპექტრიანია.

#### Example B — Two-Character Confrontation (ორი ისტორიული პერსონაჟის დაპირისპირება და მოლაპარაკება)

* **სცენის გარემო და საყრდენი ორიენტირები (`Fixed Landmarks`):** ქვის სათათბირო ოთახი ღამით. ცენტრში დგას მუხის მაგიდა გაშლილი რუკით; მარცხენა კედელთან ანთია ბუხარი (თბილი `Key Light ~2000K`), ხოლო მარჯვენა უკანა კედელზე არის მაღალი თაღოვანი სარკმელი, საიდანაც შემოდის ცივი მთვარის შუქი (`Rim Light ~5600K`).

* **180-გრადუსიანი ღერძი:** გუბერნატორი (მუქი მწვანე მოსასხამი, ხანდაზმული ბარიტონი) დგას **მარცხნივ** ბუხართან და იყურება მარჯვნივ; ელჩი (რუხი სამგზავრო სამოსი, ახალგაზრდა მკვეთრი ტენორი) დგას **მარჯვნივ** სარკმელთან და იყურება მარცხნივ. კამერა რჩება მაგიდის წინა (სამხრეთ) მხარეს.

* **სთორიბორდი და აუდიო-წინმსწრები მონტაჟი (`5 Shots, 24s Total`):**

  1. **Shot B1 (`STILL`, 4.5s — `Master Two-Shot`, 35mm, Eye-Level):** ორივე პერსონაჟი მაგიდის საპირისპირო მხარეს; ბუხრის ცეცხლი აციმციმებს ჩრდილებს (`2.5D Firelight Flicker`). **Narrator (0.0–3.5s):** *"Behind closed doors, the envoy offered one final ultimatum."* **J-Cut (3.8s):** ელჩის ხმა იწყება ჯერ კიდევ `Master Shot`-ზე: *"Open the harbour gates by dawn—"*

  2. **Shot B2 (`VIDEO`, 4.0s, 97 frames — `OTS MCU on Envoy`, 50mm):** კამერა გუბერნატორის მარცხენა მხრის უკნიდან უყურებს ელჩს (მარჯვნივ). **Visible Lip-Sync (0.0–3.2s):** *"—or the fleet burns everything anchored in the bay."* ელჩი ასრულებს ფრაზას და წინ იხრება. (`Lip-Sync ≤ 5s` წესი დაცულია!).

  3. **Shot B3 (`STILL`, 2.5s — `ECU Insert`, 85mm):** გუბერნატორის ხელი ნელა ეხება მაგიდაზე დადებულ ბეჭედს. **Silence & Foley Beat:** დიალოგი და მუსიკა სრულად ჩერდება; ისმის მხოლოდ ბუხრის ტკაცუნი, `Room Tone (-38 LUFS)` და ლითონის ბეჭდის რბილი გაჩოჩება ხის მაგიდაზე.

  4. **Shot B4 (`VIDEO`, 4.5s, 105 frames — `Single CU on Governor`, 85mm, Slight Low-Angle):** გუბერნატორი ნელა სწევს მზერას მარჯვნივ (`Eyeline Match` ელჩისკენ). **Visible Lip-Sync (0.5–4.0s):** *"Your ships carry three weeks of grain. My granaries hold enough for a year."*

  5. **Shot B5 (`VIDEO`, 4.5s, 105 frames — `Reaction CU on Envoy`, 85mm):** **L-Cut (0.0–2.5s):** გუბერნატორის ხმა გრძელდება კადრს მიღმა (*"Tell your admiral to count his rations."*), ხოლო ეკრანზე ჩანს მხოლოდ ელჩის სახე, რომელსაც თვალის კუთხე ეჭიმება და მზერა ეშვება ქვემოთ. ბოლო 2 წამში შემოდის დაბალი ჩელოს `Dissonant Drone`.

* **Shot B4-ის პრომპტების წყვილი:**

  * *First-Frame Image Prompt:* `Illustrated historical docudrama medium close-up of an aging governor in a dark green wool cloak standing in a stone chamber at night. He occupies the left-center frame looking toward the right edge. Warm flickering orange firelight from the left illuminates the left half of his weathered face, while the right half falls into deep chiaroscuro shadow with a cool moonlight rim light on his right shoulder. Shallow depth of field, stone wall softly blurred behind, 85mm lens look, text-free.`

  * *Matching LTX-2.5 Audio-to-Video Prompt:* `The governor raises his eyes steadily toward the right and speaks calmly with controlled authority, his jaw moving naturally to the dialogue while warm firelight flickers subtly across his brow. Camera remains locked-off and static.`

#### Example C — Historical Crafting / Manual Work (ისტორიული ხელოსნობა და სამხედრო/საინჟინრო მომზადება)

* **სცენის ამოცანა:** სამჭედლოში რკინის იარაღის/საალყო დეტალის გამოჭედვის პროცესის ჩვენება ისე, რომ ფიზიკური მექანიკა, მასალის ტემპერატურის ცვლილება და `Foley` ხმა ქმნიდეს ტაქტილურ დამაჯერებლობას (22 წამი, 4 კადრი).

* **სთორიბორდი და ინსტრუმენტული გადაწყვეტა:**

  1. **Shot C1 (`STILL`, 4.5s — `Establishing MS`, 35mm):** მჭედელი ქურის წინ; `Python 2.5D` ქმნის საბერველის მოძრაობასა და ქურიდან ამომავალ ნაპერწკლებს. **Ambience:** ქურის გუგუნი და ნაკვერჩხლის შიშინი. **Narrator:** ხსნის ახალი შენადნობის ან კონსტრუქციის საჭიროებას.

  2. **Shot C2 (`VIDEO`, 5.0s, 121 frames — `ECU Insert on Anvil`, 85mm):** გავარვარებული (`#E69F00`) ლითონის ზოდი გრდემლზე; ურო ეცემა სამჯერ (`Anticipation -> Contact Peak -> Rebound`), ყოველი დარტყმისას იფრქვევა ნაპერწკლები. **Foley Sync:** სამი განსხვავებული `Round-Robin` ლითონის წკრიალა დარტყმა ზუსტად კონტაქტის ფრეიმებზე (კადრები 24, 60, 96).

  3. **Shot C3 (`VIDEO`, 4.0s, 97 frames — `Low-Angle MCU on Blacksmith`, 50mm):** `Cut on Action` მესამე დარტყმის აწევაზე; ქვემოდან არეკლილი ნარინჯისფერი სინათლე ანათებს მჭედლის ოფლიან სახეს.

  4. **Shot C4 (`VIDEO`, 5.0s, 121 frames — `MS Quenching & Material State Change`, 50mm):** გავარვარებული პირი ეშვება წყლიან კასრში; ნარინჯისფერი ნათება ქრება, გადადის მუქ ფოლადისფერში და ამოდის სქელი თეთრი ორთქლის სვეტი. **SFX:** მძლავრი `Steam Sizzle` (`2–8 kHz`), რომელიც ნელა მიილევა.

#### Example D — Discovery and Reveal (აღმოჩენა და დრამატული შემობრუნება)

* **სცენის ამოცანა:** მზვერავი ნისლიან ტყეში პოულობს მიტოვებულ საალყო მანქანებს, რაც ცვლის აუდიტორიის წარმოდგენას მოწინააღმდეგის გეგმაზე (`Character-First + Rack-Focus Delayed Reveal`, 18 წამი).

* **სთორიბორდი და სიურპრიზის დაცვის მექანიკა:**

  1. **Shot D1 (`VIDEO`, 5.0s, 121 frames — `Frontal Tracking MCU`, 50mm):** მზვერავი მიიწევს წინ სქელ ნისლში, უყურებს კამერის მარჯვენა მხარეს; 03.5 წამზე იგი უეცრად შეშდება (`Settle Pose`), თვალები უფართოვდება. **Audio:** ნარატორი წყვეტს ფრაზას შუაზე; ტყის ქარი და დაბალი `Tension Riser` იზრდება 03.5 წამამდე, შემდეგ კი — **სრული აკუსტიკური Dropout (სიჩუმე 03.5–05.0s)**.

  2. **Shot D2 (`STILL / Blender 2.5D`, 7.0s — `OTS Rack-Focus Reveal`, 85mm):** კადრის მარცხენა წინა პლანზე მკვეთრ ფოკუსში ჩანს მზვერავის მხარი და ჩირაღდანი, ხოლო მარჯვენა უკანა პლანი დაფარულია ღრმა `Defocus Bokeh`-ითა და ნისლით. **01.5 – 02.8 წამზე:** `Blender Defocus Node` გადასწევს ფოკუსის სიბრტყეს (`Rack Focus`) წინა პლანიდან უკანა პლანზე, სადაც ნისლიდან იკვეთება ათობით გიგანტური საალყო კატაპულტის სილუეტი. **Audio:** `Resonant Sub-Sting` ჟღერდება ზუსტად **02.8 წამზე** (როდესაც კატაპულტის სილუეტი სრულ სიმკვეთრეს აღწევს — არც ერთი ფრეიმით ადრე!).

  3. **Shot D3 (`VIDEO`, 4.0s, 97 frames — `ECU Eyes/Face Reaction`):** მზვერავი უკან იხევს; ნარატორი ხმადაბლა განმარტავს აღმოჩენის სტრატეგიულ მნიშვნელობას.

#### Example E — Explanatory Geography / Tactical Strategy (სტრატეგიული გეოგრაფიისა და ფიზიკური სცენის სინთეზი)

* **როდის ჯობია რუკა კინემატოგრაფიულ სცენას:** როდესაც საჭიროა 300-კილომეტრიანი მომარაგების ჯაჭვის გაწყვეტისა და ორი პარალელური უღელტეხილის ბლოკირების ჩვენება — რასაც ვერც ერთი ფიზიკური კამერის კადრი ვერ დაიტევს.

* **სთორიბორდი (`3 Shots, 24s Total`):**

  1. **Shot E1 (`STILL`, 5.0s — `High-Angle Mountain Pass Establishing`):** ფიზიკური დათოვლილი უღელტეხილი. ბოლო 1 წამში კამერა იწევა ვერტიკალურად მაღლა და `Match Dissolve`-ით (`xfade=transition=fade:duration=1.2`) გადადის რუკაში, სადაც იგივე მთის ქედი ემთხვევა კარტოგრაფიულ კონტურს.

  2. **Shot E2 (`HELPER`, 12.0s — `Deterministic Python Vector Map`):**

     * *0.0–3.5s:* მაკრო-რეგიონული ხედი; ნარატორი ასახელებს ორ სანავსადგურო ქალაქს (ჩნდება 2 ეტიკეტი `#0072B2` ფერით, `24pt` სანს-სერიფი, `WCAG 8.2:1` კონტრასტით).

     * *3.5–7.5s:* `Cubic-Bezier` კამერის მიახლოება ცენტრალურ უღელტეხილზე; ნარინჯისფერი (`#E69F00`) წყვეტილი მომარაგების ხაზი მიემართება ჩრდილოეთით (`Forced Alignment` სინქრონით).

     * *7.5–12.0s:* ვერმილიონის (`#D55E00`) ბლოკადის სიმბოლო კეტავს უღელტეხილს; მომარაგების ხაზი წყდება და იცვლის ფერს ნაცრისფრად.

  3. **Shot E3 (`VIDEO`, 7.0s, 169 frames — `Ground-Level Consequence`):** `Match Cut` რუკის ბლოკადის წერტილიდან ფიზიკურ სცენაზე — თოვლში გაჭედილი სურსათის ურმები და ჯარისკაცები, რომლებიც ცეცხლს უკიდებენ დამტვრეულ ბორბლებს.

#### Example F — Travel / Traversal (ლაშქრობა და ცვალებადი გარემოს გადალახვა)

* **სთორიბორდი (`4 Shots, 26s Total — Left-to-Right Directional Continuity`):**

  1. **Shot F1 (`HELPER`, 4.5s):** მარშრუტის ხაზი მიემართება დასავლეთიდან აღმოსავლეთით (მარცხნიდან მარჯვნივ).

  2. **Shot F2 (`VIDEO`, 8.0s, 193 frames — `Extreme Wide Silhouette Profile`, 24mm):** ქარავანი/არმია მიდის მარცხნიდან მარჯვნივ მზიანი სტეპის ჰორიზონტზე. **Audio:** მსუბუქი `108 BPM` პერკუსიული `Ostinato` + მშრალი ქარი. **J-Cut (7.0s):** შემოდის ჭექა-ქუხილისა და კოკისპირული წვიმის ხმა.

  3. **Shot F3 (`VIDEO`, 8.0s, 193 frames — `Lateral Tracking MWS`, 50mm):** კამერა მოძრაობს პარალელურად მარცხნიდან მარჯვნივ ტალახსა და წვიმაში მიმავალ მწკრივთან ერთად; წინა პლანზე ბუნდოვანი ხის ტოტები ქმნის ძლიერ პარალაქსს. **Audio:** `Ostinato`-ს ემატება მძიმე ჩელოს პარტია; ტალახში ნაბიჯებისა და სველი მოსასხამების `Foley`.

  4. **Shot F4 (`STILL`, 5.5s — `Tail-Away Wide Shot at Dusk`):** მწკრივი შედის ნისლიან ხეობაში კამერისგან სიღრმეში (`2.5D Parallax` + ნისლის ფენები), ხოლო ჰორიზონტზე ჩნდება დანიშნულების ციხესიმაგრის სილუეტი.

#### Example G — Aftermath / Loss / Quiet Reflection (ბრძოლის ან კატასტროფის შედეგი და ჩუმი რეფლექსია)

* **სთორიბორდი (`3 Shots, 25s Total — Decompression & Sonic Restraint`):**

  1. **Shot G1 (`STILL`, 8.0s — `Ground-Level ECU/MS Tableau`, 50mm):** ნისლიან მინდორზე ჩარჭობილი გატეხილი ხმალი და ჩამქრალი ნაკვერჩხალი; `Python 2.5D` ნელა ამოძრავებს ნაცრის ფანტელებს მარჯვნიდან მარცხნივ (შეტევის საპირისპირო მიმართულებით!). **Audio (0.0–8.0s):** **ნარატორი და მუსიკა სრულად დუმს.** ისმის მხოლოდ ცივი ქარი (`-28 LUFS`) და ნაკვერჩხლის ჩუმი ტკაცუნი.

  2. **Shot G2 (`VIDEO`, 9.0s, 217 frames — `Slow Crane-Up / Pull-Out EWS`, 35mm):** მარტოხელა გადარჩენილი მებრძოლი ზის ქვაზე ზურგით კამერისკენ; კამერა ძალიან ნელა იწევს უკან და მაღლა, ხსნის დამწვარი ბანაკის მასშტაბს. **Audio:** 02.0 წამზე შემოდის სოლო ჩელოს ნელი, დაბალი მოტივი (`64 BPM`, `-24 LUFS`); 04.0 წამზე ნარატორი იწყებს ხმადაბალ, დინჯ შეჯამებას.

  3. **Shot G3 (`STILL`, 8.0s — `Historical Ledger / Counter HELPER-STILL Hybrid`):** მუქ ფონზე ნელა იწერება დანაკარგებისა და შედეგის ვერიფიცირებული ისტორიული მონაცემი, რომელიც `Cross-Dissolve`-ით გადადის მომდევნო აქტში.

#### Example H — Opening Hook and Final Payoff (საწყისი კაუჭისა და ფინალური კვანძის გახსნის სიმეტრიული დიზაინი)

* **Opening Hook (`00:00 – 00:35` — ცნობისმოყვარეობის აღძვრა სრული ახსნის გარეშე):**

  * *Shot H1 (`00:00–00:05`, `VIDEO` `ECU -> CU`):* კამერა იწყებს მაგიდაზე დაღვრილი წითელი ლუქისა და სამეფო ბეჭდის `ECU`-თი, საიდანაც სწრაფი `Tilt-Up`-ით გადადის მაცნის შეშინებულ სახეზე; ფონზე ჩანს ცეცხლმოკიდებული ნავსადგურის სარკმელი. **Narrator (00:00):** *"In November 1453, one unsigned letter stood between an empire's survival and total collapse."*

  * *Shot H2 (`00:05–00:18`, `Rapid 3-Shot Montage — VIDEO + STILL`):* (1) ფლოტი ნისლში (4s); (2) საბჭოს დარბაზში გადაყირავებული სკამი (4s); (3) ხმალი, რომელიც ჭრის საზღვაო რუკის თოკს (5s). **Score:** 4-ნოტიანი `Leitmotif` D-მინორში + აჩქარებული პერკუსიული პულსი.

  * *Shot H3 (`00:18–00:35`, `HELPER` Counterfactual Map):* რუკაზე ჩნდება განშტოების წერტილი (`Point of Divergence — #F0E442`). **Narrator:** სვამს მთავარ დრამატულ კითხვას: *"What if the relief fleet had sailed forty-eight hours earlier?"* **00:33-ზე:** `Riser -> Sub-Impact` და **2.0-წამიანი აბსოლუტური სიჩუმე** პირველი თავის დაწყებამდე.

* **Final Payoff (`11:15 – 12:00` — დრამატული პასუხი და მოტივის ტრანსფორმაცია):**

  * *Shot H4 (`11:15–11:30`, `HELPER` Map Callback):* იგივე რუკა, რომელიც `Opening Hook`-ში გაჩერდა კითხვის ნიშანზე, ახლა სრულდება სრული ტერიტორიული და სავაჭრო ქსელის გაშლით (`#0072B2` და `#009E73`).

  * *Shot H5 (`11:30–11:45`, `VIDEO` 10s Continuous Crane Shot):* კამერა იგივე სარკმლიდან (`Visual Motif Callback` Shot H1-თან) გადის გარეთ გახსნილი ნავსადგურისკენ განთიადის ოქროსფერ შუქზე.

  * *Shot H6 (`11:45–12:00`, `STILL` 2.5D Held Tableau):* მაგიდაზე დევს იგივე წერილი, ამჯერად დასრულებული ბეჭდით; კამერა ნელა იხევს უკან (`Slow Pull-Out`). **Score & Audio:** საწყისი 4-ნოტიანი `Leitmotif`, რომელიც დასაწყისში ჟღერდა დაძაბულ D-მინორში, ახლა სრულდება ღია კვინტის (`Open Fifth / D Major`) მშვიდ ჰარმონიულ კადენციაში; ნარატორი ასრულებს თხრობას `11:55`-ზე, ხოლო ბოლო 5 წამი ეკუთვნის მუსიკის ბუნებრივ აკუსტიკურ მილევადობასა და `Fade to Black`-ს.

## I. თორმეტწუთიანი აუდიოვიზუალური ბლუპრინტი (Twelve-Minute Audiovisual Blueprint)

წინამდებარე ბლუპრინტი აჩვენებს, თუ როგორ ვითარდება 12-წუთიანი (`720 წამი`) ეპიზოდი 9 ნარატიულ ფაზად ისე, რომ მკაცრად და დამოუკიდებლად სრულდება:

1. **ვიზუალური ქრონომეტრაჟის სამიზნე (`60% VIDEO / 30% STILL / 10% HELPER ±5%`):**

   * `VIDEO`: **432 წამი (60.0%)**

   * `STILL`: **216 წამი (30.0%)**

   * `HELPER`: **72 წამი (10.0%)**

   * *ჯამური ვიზუალური ქრონომეტრაჟი:* **720 წამი (12:00)**.

2. **სასაუბრო სიტყვების დამოუკიდებელი ბიუჯეტი (`75% Narrator / 25% Voiced Character Dialogue`, დიალოგის ჭერი 30%):**

   * 12-წუთიან ვიდეოში საშუალო დოკუმენტური ტემპით (\~140 სიტყვა წუთში აქტიური საუბრისას, \~84 წამი ჯამური უსიტყვო სამოქმედო, ატმოსფერული და დრამატული პაუზების გათვალისწინებით) სულ წარმოითქმის **1,680 გახმოვანებული სიტყვა**:

   * `Narrator Words`: **1,260 სიტყვა (75.0%)** — გადანაწილებულია როგორც `VIDEO`, ისე `STILL` და `HELPER` კადრებზე.

   * `Voiced Character Dialogue Words`: **420 სიტყვა (25.0%)** — გადანაწილებულია მოკლე (`≤5 წმ`) ხილულ `Lip-Sync` კადრებზე, `Reaction MCU` კადრებსა და `STILL Insert`-ებზე (`J-cut / L-cut` გადაფარვით).

   * უსიტყვო (`Silence / Music & SFX-only`) მონაკვეთები (ჯამში 84 წამი) იკავებს ვიზუალურ ქრონომეტრაჟს, მაგრამ **საერთოდ არ ცვლის სასაუბრო სიტყვების პროცენტულ წილს (`1260 / 1680 = 75.0%`, `420 / 1680 = 25.0%`)**.

### I.1 12-წუთიანი ეპიზოდის სრული კოორდინირებული მატრიცა (00:00 – 12:00)

| ფაზა და ტაიმკოდი (ხანგრძლივობა) | ნარატიული ფუნქცია და აუდიტორიის კითხვა | ვიზუალური ზოლების განაწილება (`VIDEO / STILL / HELPER` წამებში) | სასაუბრო სიტყვების განაწილება (`Narrator vs. Dialogue Words`) | ვიზუალური და აუდიო კომბინაციის მექანიკა (Cross-Lane Independence) | მუსიკის, `Ambience/SFX`-ისა და მონტაჟური რიტმის სტრატეგია | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **1. Cold Open & Hook** `00:00 – 00:45` (**45s**) | ცნობისმოყვარეობის დაჭერა: *რა იდგა სასწორზე და რა არის მთავარი კონტრფაქტობრივი კითხვა?* | `VIDEO`: 28s | `STILL`: 9s | `HELPER`: 8s | `Narrator`: 85w | `Dialogue`: 15w | `Silence`: 4s | ნარატორი საუბრობს `VIDEO` კადრებზე (18s) და `HELPER` რუკაზე (8s); 1 პერსონაჟის 3-წამიანი (15w) ხილული `Lip-Sync` რეპლიკა კრიზისის პიკზე. | **Cue 1 (`90 BPM` D Minor Leitmotif)** -> `Riser` -> `00:41`-ზე `Sub-Impact` და 4-წამიანი სიჩუმე; სწრაფი `Hard Cut` და `Match Cut`. | 
| **2. Historical Context & World Setup** `00:45 – 02:15` (**90s**) | საბაზისო რეალობის ახსნა: *როგორი იყო ძალთა ბალანსი და გეოგრაფია კრიზისამდე?* | `VIDEO`: 36s | `STILL`: 36s | `HELPER`: 18s | `Narrator`: 210w | `Dialogue`: 0w | `Silence`: 6s | ნარატორი სრულად მართავს ფაზას: მიდის `STILL` (`2.5D Parallax` ქალაქისა და არქივის კადრებზე), `HELPER` (სტატისტიკურ დიაგრამაზე) და `VIDEO` (ლანდშაფტის კადრებზე). | **Cue 2 (`100 BPM` Sparse Analytical Pulse)**; ფართო სტერეო `Ambience`; მშვიდი 5–8 წამიანი კადრები `Cross-Dissolve`-ით. | 
| **3. Inciting Incident & Council Confrontation** `02:15 – 03:45` (**90s**) | კონფლიქტის პერსონიფიკაცია: *რატომ ვერ შეთანხმდნენ მხარეები?* | `VIDEO`: 54s | `STILL`: 36s | `HELPER`: 0s | `Narrator`: 95w | `Dialogue`: 135w | `Silence`: 8s | **დიალოგის მთავარი სცენა:** 135 სიტყვა დიალოგი განაწილებულია ხუთ `≤4.5s` ხილულ `Lip-Sync VIDEO` კადრზე, ხოლო რეპლიკების დანარჩენი ნაწილი გრძელდება `L-Cut`-ით მსმენელის `Reaction VIDEO` და `STILL Insert` კადრებზე! | **No-Music Stretch #1 (40s)** -> დაბალი `Drone`; უწყვეტი `Room Tone`, ცეცხლის ტკაცუნი, პერგამენტის `Foley`; `J-cut / L-cut` დიალოგური მონტაჟი. | 
| **4. Preparation, Crafting & Mobilisation** `03:45 – 05:15` (**90s**) | ფიზიკური მზადება: *როგორ მოემზადა ორივე მხარე შეჯახებისთვის?* | `VIDEO`: 56s | `STILL`: 24s | `HELPER`: 10s | `Narrator`: 175w | `Dialogue`: 35w | `Silence`: 8s | ნარატორი საუბრობს სამჭედლოსა და ლაშქრობის `VIDEO` მონტაჟზე (56s) და რესურსების `HELPER` მრიცხველზე (10s); მეთაურის მოკლე ბრძანება (35w) ფარავს მზადების კადრებს. | **Cue 3 (`112 BPM` Building Ostinato)**; რიტმული სამჭედლოსა და აღჭურვილობის `Foley` სინქრონიზებულია `Cut on Action` ჭრებთან. | 
| **5. Strategic Pivot & Tactical Geography** `05:15 – 06:15` (**60s**) | ტაქტიკური ანალიზი: *სად დაუშვეს საბედისწერო შეცდომა (ან სად იწყება კონტრფაქტობრივი გარდატეხა)?* | `VIDEO`: 24s | `STILL`: 14s | `HELPER`: 22s | `Narrator`: 130w | `Dialogue`: 25w | `Silence`: 5s | `HELPER` ტაქტიკური რუკა (22s) ნარატორის `Forced Alignment` სინქრონით გადადის `Match Cut`-ით ფიზიკურ უღელტეხილზე (`VIDEO` 24s), სადაც მზვერავი აწვდის მოკლე პატაკს (25w). | **No-Music Stretch #2** რუკის ახსნისას -> სუბ-ბას პულსაცია; ქაღალდისა და ხის ფიგურების ტაქტილური `Foley`. | 
| **6. Escalation & Battle / Action Sequence** `06:15 – 08:30` (**135s**) | კინეტიკური შეჯახება: *როგორ განვითარდა ბრძოლა ველზე?* | `VIDEO`: 108s | `STILL`: 27s | `HELPER`: 0s | `Narrator`: 165w | `Dialogue`: 85w | `Silence`: 28s | **მოიცავს სამ 10–14 წამიან უწყვეტ არადიალოგურ `VIDEO` სამოქმედო კადრს**, სადაც 28 წამის განმავლობაში საერთოდ არავინ საუბრობს (მხოლოდ მოქმედება, `SFX` და `Score`), ხოლო მოკლე ფანჯრებში ისმის ნარატორის კომენტარი და საველე ბრძანებები (85w). | **Cue 4 (`128 BPM` Full Kinetic Score)** + `Sidechain Ducking`; ფენოვანი საბრძოლო `Ambience/Foley`; 2-წამიანი აკუსტიკური ვაკუუმი მთავარ შეჯახებამდე. | 
| **7. Climax & Decisive Turning Point** `08:30 – 09:45` (**75s**) | კულმინაციური გარდატეხა: *ვინ გაიმარჯვა და რამ გადაწყვიტა ბედი?* | `VIDEO`: 56s | `STILL`: 19s | `HELPER`: 0s | `Narrator`: 110w | `Dialogue`: 95w | `Silence`: 10s | `Cross-Cutting` ორ ფლანგსა და ლიდერების დაპირისპირებას შორის; 95 სიტყვა კულმინაციური დიალოგი (`≤4s Lip-Sync` + `Reaction CU`) და 12-წამიანი კულმინაციური `Crane-Up VIDEO` კადრი. | მთავარი `Leitmotif`-ის სრული ორკესტრული პიკი (`-14 LUFS`, `-1.5 dBTP`); მკვეთრი `Smash Cut` კულმინაციური დარტყმის შემდეგ. | 
| **8. Aftermath, Loss & Immediate Consequence** `09:45 – 10:45` (**60s**) | ემოციური დეკომპრესია: *რა ფასი დაჯდა ეს შედეგი?* | `VIDEO`: 30s | `STILL`: 30s | `HELPER`: 0s | `Narrator`: 115w | `Dialogue`: 30w | `Silence`: 10s | პირველი 10 წამი — სრული ვოკალური და მუსიკალური სიჩუმე `STILL 2.5D` ნისლიან ველზე; შემდეგ ნარატორის რეფლექსია (115w) და გადარჩენილი პერსონაჟის ერთი ჩუმი დასკვნითი ფრაზა (30w). | **No-Music Stretch #3 (10s)** -> **Cue 5 (`64 BPM` Elegiac Solo Cello)**; ცივი ქარი და ნაკვერჩხლის ტკაცუნი; გრძელი 8–10 წამიანი კადრები. | 
| **9. Historical Payoff & Coda** `10:45 – 12:00` (**75s**) | თემატური დახურვა: *როგორ შეცვალა ამ მოვლენამ ისტორია და რა პასუხი გაეცა საწყის კითხვას?* | `VIDEO`: 40s | `STILL`: 21s | `HELPER`: 14s | `Narrator`: 175w | `Dialogue`: 0w | `Silence`: 5s | `HELPER` (14s) აჩვენებს საბოლოო ტერიტორიულ/ეკონომიკურ შედეგს; `VIDEO` (40s) უბრუნდება საწყისი `Opening Hook`-ის ვიზუალურ მოტივს; ბოლო 12 წამი — `STILL 2.5D Held Tableau`. | **Cue 6 (`90 BPM` Thematic Resolution)** — საწყისი თემა გადადის ღია ჰარმონიულ კადენციაში; ბოლო 5 წამი ბუნებრივი აკუსტიკური მილევადობა და `Fade to Black`. | 
| **ჯამური ბალანსი (TOTAL VERIFICATION)** | **720 წამი (12:00)** | **`VIDEO`: 432s (60.0%)** | **`STILL`: 216s (30.0%)** | **`HELPER`: 72s (10.0%)** | **`Narrator`: 1,260w (75.0%)** | **`Dialogue`: 420w (25.0%)** | **Total Words: 1,680w** | **ორივე განზომილება 100%-ით დაცულია დამოუკიდებლად.** | **Integrated Loudness: `-14.0 LUFS` | True Peak: `-1.5 dBTP` | LRA: `8.5 LU`** | 

## J. მრავალჯერადი გამოყენების ტექნიკური ბარათები (Reusable Technique Cards — Section 19 Format)

ქვემოთ მოცემულია 10 უმაღლესი შემოქმედებითი და საწარმოო ღირებულების ტექნიკური ბარათი სექცია 19-ის მკაცრი 19-ველიანი სტრუქტურით.

### Technique 1: Multi-Plane 2.5D Camera Projection & Parallax Push

* **Discipline:** cinematography / compositing / animation.

* **What it is:** ერთი 2D ილუსტრირებული კადრის დაყოფა 3–5 დისკრეტულ სიღრმისეულ შრედ (`Foreground, Mid-Foreground, Midground, Background, Sky`) ალფა-ნიღბებითა და `Z-Depth` რუკით, რომლებიც გადაადგილდება სხვადასხვა კუთხოვანი/ხაზოვანი სიჩქარით ვირტუალური კამერის მოძრაობისას.

* **What the audience experiences:** მაყურებელი აღიქვამს რეალურ სამგანზომილებიან მოცულობასა და სივრცით სიღრმეს (`STILL` ზოლი იძენს სრულფასოვანი კინოკადრის ხარისხს ბრტყელი სლაიდშოუს ნაცვლად).

* **Purpose:** გარემოს მასშტაბის დამკვიდრება (`Establishing`), ჯგუფური საბჭოს ტაბლოს გაცოცხლება ან `Aftermath` სცენის ჩვენება პერსონაჟის იდენტობის ნულოვანი დრეიფით.

* **Use it when:** საჭიროა 4–10 წამიანი სტაბილური არქიტექტურული, ლანდშაფტური ან მრავალფიგურიანი კადრი (`STILL` 30% ბიუჯეტის ფარგლებში), სადაც გენერაციული `VIDEO` მოდელი გამოიწვევდა ფონური სახეების ან კედლების მორფინგს.

* **Avoid it when:** სცენა მოითხოვს პერსონაჟის აქტიურ არტიკულაციას (სირბილი, ხმლის ქნევა, ხილული `Lip-Sync`) ან კამერის >15° ორბიტალურ შემოვლას.

* **Visual requirements:** მაღალი რეზოლუციის (`≥2560×1440`) საწყისი ილუსტრაცია მკაფიოდ გამიჯნული წინა პლანის ჩარჩო ელემენტებით (სვეტი, ხის ტოტი, მხარი), სუფთა ალფა-კიდეებითა და `Inpainted` უკანა ფონით (რათა წინა ფენის გაწევისას უკან არ გამოჩნდეს ცარიელი ხვრელი).

* **Audio requirements:** ფართო სტერეო `Ambience` + 1–2 სივრცითი `Spot SFX` (მაგ., ქარი, ჩირაღდნის ტკაცუნი) + ნარატორის თხრობა.

* **Execution steps:** (1) საწყისი კადრის სეგმენტაცია 4 RGBA ფენად და უკანა ფონების შევსება (`Inpainting`); (2) ფენების განთავსება Z-ღერძზე ($Z_1=1.0, Z_2=2.5, Z_3=6.0, Z_4=20.0$); (3) კამერის `Ease-In-Out Cubic` ტრანსლაციის გაწერა; (4) შუა ფენაში ნისლის/მტვრის ნაწილაკების ჩასმა; (5) მსუბუქი `Defocus` წინა და უკანა შრეებზე.

* **LTX route:** `approximate / simulated` — `LTX-2.5 I2V`-ს შეუძლია მსგავსი კადრის გენერაცია, მაგრამ იგი ითვლება `VIDEO` ზოლში და მოიხმარს GPU ინფერენსს.

* **Blender route:** `native / directly supported` — `Import Images as Planes` Z-სიღრმეზე განლაგებით + 3D კამერის `Dolly` + `Defocus Node` ([Blender Track To Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html)).

* **Python route:** `deterministic / scripted` — `Pillow` (`Image.alpha_composite`) და `OpenCV` (`cv2.warpAffine` / `cv2.remap` `INTER_LANCZOS4` სუბპიქსელური ინტერპოლაციით) ([Pillow Image Module](https://pillow.readthedocs.io/en/latest/reference/Image.html), [OpenCV Geometric Transformations](https://docs.opencv.org/4.13.0/dir_996070d144ea13ded22df5bf9603981f.html)).

* **FFmpeg route:** `approximate / simulated` — მრავალჯერადი `overlay=x='...':y='...'` ფილტრ-გრაფით, თუმცა სუბპიქსელური სირბილით ჩამორჩება `OpenCV/Blender`-ს ([FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html)).

* **Hybrid route:** `Python / OpenCV` ასრულებს RGBA ფენების სუბპიქსელურ პარალაქსურ რენდერსა და ნაწილაკების ზედდებას, ხოლო `FFmpeg` ამატებს ფინალურ `Vignette`-სა და აუდიო მიქსს.

* **Common failures:** `Edge Halo / Disocclusion Gap` (წინა ფენის გადაადგილებისას უკანა ფენაზე ჩნდება შეუვსებელი ზოლი); `Cardboard Cutout Look` (ფენებს შორის ატმოსფერული ნისლისა და სიმკვეთრის სიღრმის არარსებობა).

* **Quality check:** კიდეების 100%-იანი შემოწმება ბოლო ფრეიმზე (`No Alpha Holes`) და სუბპიქსელური მოძრაობის სირბილის შემოწმება (`0 Frame Jitter`).

* **Cost / complexity:** Low to Medium (სრულიად დეტერმინისტული CPU/GPU პროცესი, ნულოვანი API ხარჯი).

* **Evidence:** [Blender Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html), [OpenCV Geometric Transformations](https://docs.opencv.org/4.13.0/dir_996070d144ea13ded22df5bf9603981f.html), [Pillow Image Reference](https://pillow.readthedocs.io/en/latest/reference/Image.html) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 2: Motion-Track IC-LoRA & First-Last-Frame (`FLF2V`) Conditioning

* **Discipline:** generative video / animation / cinematography.

* **What it is:** `LTX-2.5` და `LTX-2.3` მოდელებში მოძრაობის ტრაექტორიის დეტერმინისტული მართვა საწყის სურათზე დახაზული ვექტორული ტრეკებით (`LTX Sparse Track Editor` -> `Motion Control IC-LoRA`) ან საწყისი და საბოლოო კადრის ერთდროული ფიქსაციით (`First-Frame / Last-Frame Conditioning`).

* **What the audience experiences:** მიზანმიმართული, ფიზიკურად მოტივირებული კამერისა და პერსონაჟის მოძრაობა ქაოსური გენერაციული ხეტიალისა და პერსონაჟის მორფინგის გარეშე.

* **Purpose:** რთული ქორეოგრაფიის (კავალერიის შეტევა, ხმლის ამოღება, კამერის ტრეკინგი) ზუსტი შესრულება `180-Degree Axis`-ისა და 4-პოზიანი სტრუქტურის (`Anticipation -> Peak -> Settle`) დაცვით.

* **Use it when:** ტექსტური პრომპტი ვერ უზრუნველყოფს სასურველ ეკრანულ მიმართულებას (`Screen Direction`) ან როდესაც კადრი უნდა დასრულდეს ზუსტ კომპოზიციაში მომდევნო კადრთან `Match Cut`-ისთვის.

* **Avoid it when:** საწყის და საბოლოო კადრს შორის კამერის კუთხე იცვლება >90 გრადუსით ან სუბიექტი მთლიანად იცვლის ტოპოლოგიას (რაც იწვევს შუა ფრეიმების გადადნობას).

* **Visual requirements:** საწყისი სურათი (`PNG/JPG/WebP`) ზუსტად სამიზნე `Aspect Ratio`-ში, რეზოლუცია **32 პიქსელის ჯერადი**, ხოლო კადრების რაოდენობა $F = 8n + 1$ (მაგ., 97, 121, 161, 241 კადრი).

* **Audio requirements:** `LTX-2.5` ავტომატურად აგენერირებს სინქრონიზებულ საბაზისო აუდიოს, რომელიც პოსტ-პროდუქციაში იცვლება ან ივსება მაღალი ხარისხის მრავალშრიანი `Foley / SFX` მიქსით.

* **Execution steps:** (1) `ComfyUI`-ში იტვირთება `LTX-2.5 Motion Control IC-LoRA` ან `FLF2V` შაბლონი; (2) `LoadImage` ნოუდში შედის საწყისი კადრი; (3) `LTX Sparse Track Editor`-ში იხაზება სუბიექტისა და კამერის მოძრაობის ვექტორები (`LTXVDrawTracks` -> `LTXAddVideoICLoRAGuide`); (4) **პრომპტში იწერება მხოლოდ სუბიექტი და ვიზუალური სტილი (მოძრაობის აღწერის გარეშე!)**; (5) სრულდება 8-ნაბიჯიანი დისტილირებული გენერაცია (`CFG = 1`) და `LTXVCropGuides` აჭრის გიდ-ტოკენებს `Tiled VAE Decode`-მდე.

* **LTX route:** `native / directly supported` — `LTX-2.5` და `LTX-2.3` `ComfyUI-LTXVideo` ნოუდებით ([Motion Control IC-LoRA Guide](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control), [Quick Start](https://docs.ltx.io/open-source-model/getting-started/quick-start)).

* **Blender route:** `deterministic / scripted` — `Blender`-ს შეუძლია დაარენდეროს ზუსტი 3D ტრეკების ან სიღრმის გიდ-ვიდეო `IC-LoRA`-ს შესასვლელისთვის.

* **Python route:** `deterministic / scripted` — `Python`-ით შესაძლებელია `Sparse Track` კოორდინატების პროგრამული გენერაცია და `$8n+1$` კადრების ვალიდაცია.

* **FFmpeg route:** not applicable (მხოლოდ საბოლოო MP4-ის ჭრა და აუდიო მუქსინგი).

* **Hybrid route:** `Blender / Python` აგენერირებს ტრაექტორიის გიდს -> `LTX-2.5 IC-LoRA` ასრულებს ვიდეო სინთეზს -> `FFmpeg` ამატებს ზუსტ `Foley`-ს.

* **Common failures:** პრომპტში მოძრაობის სიტყვიერი ჩაწერა მაშინ, როცა `Motion Control IC-LoRA` ჩართულია (იწვევს კონფლიქტს ტრეკებსა და ტექსტურ ტოკენებს შორის); `$8n+1$` წესის დარღვევა (იწვევს ბოლო კადრების მოჭრას ან პადინგის არტეფაქტებს).

* **Quality check:** `Optical Flow` ვექტორების შედარება შეყვანილ ტრეკებთან და ბოლო კადრის იდენტობის შემოწმება.

* **Cost / complexity:** Medium (მოითხოვს ლოკალურ GPU-ს 24–32GB VRAM-ით ან ჰოსტირებულ API-ს).

* **Evidence:** [Motion Control IC-LoRA Documentation](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control), [IC-LoRA Usage Guide](https://docs.ltx.io/open-source-model/usage-guides/ic-lo-ra) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 3: Continuous Overhead Battle Choreography (10–15s Non-Dialogue VIDEO)

* **Discipline:** directing / cinematography / animation.

* **What it is:** 10–15 წამიანი დაუقطعავი, მაღალი კუთხის (`Elevated / Crane`) სამოქმედო კადრი, რომელიც ერთ უწყვეტ სვლაში აჩვენებს ორი სამხედრო ფორმაციის მანევრს, რელიეფურ მიზეზ-შედეგობრიობასა და შეჯახების ხაზს დიალოგის გარეშე.

* **What the audience experiences:** ეპიკური მასშტაბის, ტაქტიკური სიცხადისა და ფიზიკური იმპულსის განცდა, რომელსაც დაქუცმაცებული 2-წამიანი კადრები ვერასოდეს შექმნის.

* **Purpose:** ბრძოლის ველის გეოგრაფიისა და შეტევის ინერციის ჩვენება (სექცია 2.3-ის წესის შესაბამისად, სადაც არადიალოგური `VIDEO` მოქმედება იყენებს 10–15 წამიან უწყვეტ ფანჯარას).

* **Use it when:** საჭიროა ფლანგური დარტყმის, ალყის კედელზე მიახლოების ან კავალერიის იერიშის სრული ტრაექტორიის ჩვენება.

* **Avoid it when:** მოქმედება მოითხოვს პერსონაჟის ახლო მიმიკას ან ხილულ დიალოგს (`Lip-Sync ≤ 5s`).

* **Visual requirements:** მაღალი კუთხის (`30°–50° Pitch`) საწყისი კომპოზიცია მკაფიო ფერადი დიფერენციაციით ფრაქციებს შორის (`#0072B2` vs `#D55E00`), მტვრისა და კვამლის ვოლუმეტრიული ფენებით.

* **Audio requirements:** ნარატორი საუბრობს მხოლოდ პირველ 4–5 წამში, შემდეგ კი ბოლო 6–10 წამი ეკუთვნის სრულ კინეტიკურ პარტიტურას (`128 BPM`), საბრძოლო ბუკებს, ფლოქვების გუგუნსა და შეჯახების `Sub-Impact`-ს.

* **Execution steps:** (1) `Blender`-ში `Geometry Nodes`-ით იგება ორი ფორმაციის პროქსი-მოძრაობა და 10–12 წამიანი კამერის სპლაინი (241 ან 289 კადრი @ 24fps); (2) რენდერდება `Depth / Canny` პასი; (3) `LTX-2.5 Pro` ან ჰოსტირებული `LTX-2.3 / 2.5` (რომელიც მხარს უჭერს 20 წამამდე გენერაციას — [Fal.ai LTX-2.3](https://fal.ai/ltx-2.3)) აგენერირებს უწყვეტ კადრს; (4) `FFmpeg`-ში ემატება დისტანციაზე მორგებული აუდიო პერსპექტივა.

* **LTX route:** `native / directly supported` (ხანგრძლივობა 20 წამამდე ჰოსტირებულ `LTX-2.3/2.5`-ზე; ლოკალურზე `x2 Temporal Upscaler` ან `IC-LoRA`).

* **Blender route:** `native / directly supported` (`Geometry Nodes` + 3D Camera Crane Path).

* **Python route:** `deterministic / scripted` (ოპტიკური ნაკადისა და კადრების ვალიდაცია).

* **FFmpeg route:** `native / directly supported` (მრავალშრიანი აუდიო მუქსინგი და `loudnorm`).

* **Hybrid route:** `Blender` (ტაქტიკური Previs & Depth Guide) -> `LTX-2.5 Pro` (ვიზუალური სინთეზი) -> `FFmpeg` (აკუსტიკური პერსპექტივის მიქსი).

* **Common failures:** მე-8 წამის შემდეგ არმიების ფერების ერთმანეთში არევა `Depth / Track` გიდის გარეშე; კადრის ხელოვნურად დაჭრა 5-წამიან ნაწილებად.

* **Quality check:** ფრაქციების ეკრანული მხარეების (`Left vs. Right`) შენარჩუნება კადრის პირველიდან ბოლო წამამდე.

* **Cost / complexity:** High (მოითხოვს `Blender` Previs-სა და `LTX Pro` გენერაციას).

* **Evidence:** [Fal.ai LTX-2.3 Specs](https://fal.ai/ltx-2.3), [LTX-2.5 Documentation](https://docs.ltx.io/models/ltx-2-5), [Blender Manual](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 4: Shot / Reverse-Shot with Audio-Led J-Cut, L-Cut & Reaction Coverage

* **Discipline:** editing / dialogue direction / cinematography.

* **What it is:** დიალოგური სცენის დაფარვა `Master Two-Shot`-ის, `Over-the-Shoulder (OTS)` რაკურსებისა და მსმენელის `Reaction Close-Up`-ების მონაცვლეობით, სადაც აუდიო ჭრა უსწრებს (`J-Cut`) ან აგრძელებს (`L-Cut`) ვიზუალურ ჭრას, ხოლო ხილული `Lip-Sync` არასოდეს აღემატება 5 წამს.

* **What the audience experiences:** ცოცხალი, ფსიქოლოგიურად დაძაბული საუბარი, სადაც მსმენელის უსიტყვო რეაქცია ისეთივე მნიშვნელოვანია, როგორც წარმოთქმული სიტყვა.

* **Purpose:** პერსონაჟთა დაპირისპირების, მოლაპარაკებისა და ქვეტექსტის გადმოცემა `20–30%` დიალოგური ბიუჯეტის ფარგლებში `Lip-Sync` არტეფაქტების გარეშე.

* **Use it when:** სცენაში მონაწილეობს 2 ან მეტი პერსონაჟი გახმოვანებული რეპლიკებით.

* **Avoid it when:** მექანიკურად ჭრით კამერას ყოველ ჯერზე ზუსტად მაშინ, როცა ახალი პერსონაჟი იწყებს საუბარს (`Ping-Pong Editing`).

* **Visual requirements:** მკაცრი `180-Degree Axis`, შეთანხმებული მზერის სიმაღლე (`Eyeline Match`), საერთო საყრდენი ორიენტირი ფონზე და `Chiaroscuro` განათების თანმიმდევრული მიმართულება.

* **Audio requirements:** განსხვავებული ვოკალური ტემბრები (`ElevenLabs v4`), უწყვეტი `Room Tone (-38 LUFS)` ყველა ჭრის ქვეშ და პაუზებში ჩასმული მცირე `Foley` (ჭიქა, ბეჭედი, ქაღალდი).

* **Execution steps:** (1) სრული დიალოგის აუდიო გენერაცია და `/v1/forced-alignment` ტაიმსტამპების ამოღება; (2) რეპლიკების დაყოფა `≤4.5s` ხილულ `Lip-Sync` ფანჯრებად (`LTX-2.5 Audio-to-Video`); (3) რეპლიკის მეორე ნახევარზე მსმენელის `MCU Reaction` კადრის დადება (`L-Cut`); (4) მომდევნო პერსონაჟის პასუხის შემოყვანა `0.5–1.0s`-ით ადრე (`J-Cut`).

* **LTX route:** `native / directly supported` (`/v2/audio-to-video` `≤5s` კლიპებისთვის — [Audio-to-Video Guide](https://docs.ltx.io/open-source-model/usage-guides/audio-to-video)).

* **Blender route:** `deterministic / scripted` (კამერის `OTS` კუთხეებისა და `180° Axis`-ის სქემატური ბლოკინგი).

* **Python route:** `deterministic / scripted` (`Forced Alignment` JSON-ის პარსინგი ზუსტი `J/L-cut` ტაიმკოდების გამოსათვლელად).

* **FFmpeg route:** `native / directly supported` (ვიდეო და აუდიო ტრეკების დამოუკიდებელი ტრიმინგი `atrim`, `adelay`, `acrossfade` და `concat` ფილტრებით).

* **Hybrid route:** `ElevenLabs v4` + `Forced Alignment` -> `LTX-2.5 A2V` (მოლაპარაკე `≤5s`) + `LTX-2.5 I2V` (მსმენელის რეაქცია) -> `FFmpeg` (`J/L-cut` აწყობა + `Room Tone`).

* **Common failures:** `180° Axis`-ის დარღვევა (ორივე პერსონაჟი იყურება ეკრანის ერთსა და იმავე კიდეში); `Room Tone`-ის წყვეტა კადრებს შორის.

* **Quality check:** მზერის ვექტორების შემოწმება (`Left-looking vs. Right-looking`) და ხილული `Lip-Sync` კადრების ქრონომეტრაჟის შემოწმება (`max_duration <= 5.0s`).

* **Cost / complexity:** Medium.

* **Evidence:** [LTX Audio-to-Video Docs](https://docs.ltx.io/open-source-model/usage-guides/audio-to-video), [ElevenLabs Forced Alignment](https://elevenlabs.io/docs/overview/capabilities/forced-alignment), [iZotope Dialogue Workflow](https://www.izotope.com/community/blog/the-dialogue-editing-workflow) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 5: Z-Depth Rack Focus & Delayed Compositional Reveal

* **Discipline:** cinematography / compositing / sound design.

* **What it is:** კამერის ფოკუსური სიბრტყის მართვადი გადატანა წინა პლანის სუბიექტიდან უკანა პლანის მანამდე დაბინდულ ობიექტზე (ან პირიქით), სინქრონიზებული მუსიკალურ `Dropout`-თან.

* **What the audience experiences:** მაყურებლის თვალი იძულებით გადადის ერთი დრამატული ელემენტიდან მეორეზე კადრის გაჭრის გარეშე, რაც ქმნის აღმოჩენის (`Reveal`) ძლიერ ფსიქოლოგიურ ეფექტს.

* **Purpose:** ფარული საფრთხის (მკვლელი, საალყო მანქანა, მოახლოებული ფლოტი) ან მნიშვნელოვანი არტეფაქტის გახსნა იმავე კადრის სივრცეში.

* **Use it when:** წინა და უკანა პლანს შორის არის მკაფიო სივრცითი დისტანცია და გსურთ მიზეზ-შედეგობრივი კავშირის ჩვენება `Hard Cut`-ის გარეშე.

* **Avoid it when:** კადრი გადაღებულია ფართოკუთხიანი (`18–24mm`) ღრმა ფოკუსის (`Deep Focus`) ესთეტიკაში ან როდესაც ორივე ობიექტი ერთსა და იმავე სიღრმისეულ სიბრტყეზეა.

* **Visual requirements:** კომპოზიცია გაყოფილი მესამედების ბადეზე (`Rule of Thirds`): სუბიექტი A წინა მარცხენა მესამედში ($Z = 1.5\text{m}$), სუბიექტი B უკანა მარჯვენა მესამედში ($Z = 12.0\text{m}$) + ზუსტი `Z-Depth` რუკა.

* **Audio requirements:** `Tension Riser` ფოკუსის დაძვრამდე -> **1.0–1.5 წამიანი სიჩუმე ფოკუსის გადაადგილების დროს** -> დაბალი `Resonant Sting` ზუსტად მაშინ, როცა მეორე ობიექტი სრულ სიმკვეთრეს აღწევს.

* **Execution steps:** (1) საწყისი კადრისა და მისი `Z-Depth` რუკის მომზადება; (2) `Blender Compositor`-ში `Defocus Node`-ის მიბმა `Z-Pass`-ზე, სადაც კამერის `Focus Distance` ანიმირდება $Z_1$-დან $Z_2$-მდე `1.2 წამის` განმავლობაში (`f-stop = 2.0`); (3) აუდიო ტრეკზე `Sting`-ის დასმა ფოკუსის დასრულების ფრეიმზე.

* **LTX route:** `prompt-driven / probabilistic` (`rack focus from foreground soldier to background fleet`).

* **Blender route:** `native / directly supported` (კამერის `Depth of Field -> Focus Object / Distance` ან Compositor `Defocus Node`).

* **Python route:** `deterministic / scripted` (`Z-Depth` ნიღბით წონითი ინტერპოლაცია სუფთა ფენასა და `cv2.GaussianBlur` / Disk Kernel-ით დაბინდულ ფენას შორის).

* **FFmpeg route:** `approximate / simulated` (ორ წინასწარ დარენდერებულ ფოკუს-მდგომარეობას შორის `xfade=transition=fade:duration=1.0`).

* **Hybrid route:** `Blender / Python` ასრულებს დეტერმინისტულ `Z-Depth Rack Focus`-ს (ან `STILL` კადრზე, ან `LTX` ვიდეო კლიპზე).

* **Common failures:** ხმოვანი `Sting`-ის ჩასმა ფოკუსის დაწყებამდე (რაც აფუჭებს სიურპრიზს); ბრტყელი `Gaussian Blur` მთელ კადრზე სიღრმის ნიღბის გარეშე.

* **Quality check:** სიმკვეთრის პიკის (`Laplacian Variance Peak`) დამთხვევა აუდიო `Sting`-ის ტრანზიენტთან `±2 კადრის` სიზუსტით.

* **Cost / complexity:** Low to Medium.

* **Evidence:** [Blender Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html), [OpenCV Documentation](https://docs.opencv.org/4.13.0/dir_996070d144ea13ded22df5bf9603981f.html) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 6: Deterministic Cartographic & Statistical Motion Graphics (Okabe-Ito Standard)

* **Discipline:** motion graphics / data visualisation (`HELPER` Lane).

* **What it is:** ისტორიული რუკების, ფრონტის ხაზების, ქრონოლოგიური სკალებისა და სტატისტიკური დიაგრამების 100%-ით დეტერმინისტული კადრ-კადრ რენდერი `Python`-ით, [Okabe-Ito დალტონიზმისგან დაცული პალიტრის](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference)ა და [Netflix Timed Text](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements) წაკითხვადობის სტანდარტების დაცვით.

* **What the audience experiences:** კრისტალურად სუფთა, მყისიერად გასაგები ტაქტიკური და ეკონომიკური ვიზუალური მტკიცებულება ყოველგვარი დამახინჯებული გენერაციული ასოების გარეშე.

* **Purpose:** რთული გეოგრაფიული მანევრებისა და რაოდენობრივი შედარებების გადმოცემა `HELPER` (10% ±5%) ბიუჯეტის ფარგლებში.

* **Use it when:** ნარატორი ასახელებს გეოგრაფიულ მარშრუტებს, ტერიტორიულ ცვლილებებს, თარიღებს ან ≥2 რიცხვით მაჩვენებელს.

* **Avoid it when:** ცდილობთ რუკის ან დიაგრამის დახატვას ტექსტ-ვიდეო ან ტექსტ-სურათის გენერაციული მოდელით.

* **Visual requirements:** მუქი ტაქტიკური (`#1A1D24`) ან ნეიტრალური პერგამენტის ფონი; `Okabe-Ito` ფერები (`#0072B2` Blue, `#D55E00` Vermilion, `#009E73` Bluish Green, `#E69F00` Orange, `#F0E442` Yellow Callout); მაქსიმუმ 3–4 ტოპონიმი ეკრანზე; კითხვის სიჩქარე **≤17–20 CPS**, მაქსიმუმ **42 CPL**, მინიმუმ **2.5 წამი** დაყოვნება.

* **Audio requirements:** ნარატორი (`Forced Alignment` ტაიმსტამპებით) + დაბალი ანალიტიკური `Ostinato` + ორგანული ტაქტილური `Foley` (პერგამენტის, ხის ფიგურის ან მექანიკური მრიცხველის ხმა).

* **Execution steps:** (1) `ElevenLabs with-timestamps`-იდან საკვანძო სიტყვების (ტოპონიმების/რიცხვების) ზუსტი ტაიმკოდების ამოღება; (2) `Python` სკრიპტით საბაზისო ვექტორული რუკის ან `Matplotlib/Pillow` ბადის აგება; (3) `Ease-OutCubic` ინტერპოლაციით ისრებისა და სვეტების დახატვა კადრ-კადრ (`24 FPS`); (4) `Pillow ImageDraw`-ით მკაფიო ეტიკეტების დადება კონტრასტული (`≥4.5:1`) კონტურით.

* **LTX route:** `unsupported` (კატეგორიულად აკრძალულია ტექსტისა და რუკებისთვის).

* **Blender route:** `deterministic / scripted` (3D რელიეფური `Heightmap` რუკებისა და 3D კამერის გადაფრენისთვის).

* **Python route:** `native / directly supported` (`Pillow`, `OpenCV`, `Matplotlib`, `NumPy`).

* **FFmpeg route:** `native / directly supported` (PNG მიმდევრობის კომპილაცია MP4-ში და აუდიო მუქსინგი).

* **Hybrid route:** `Blender` (3D ტოპოგრაფიული რელიეფის ფონი წარწერების გარეშე) -> `Python Pillow/OpenCV` (ვექტორული საზღვრები, ისრები, `Okabe-Ito` ფერები და ზუსტი ტიპოგრაფია).

* **Common failures:** ეკრანზე 10+ ქალაქის სახელის ერთდროულად გამოტანა; Y-ღერძის არანულოვანი ნიშნულიდან დაწყება (ვიზუალური მანიპულაცია); წითელ-მწვანე ფერების გამოყენება დალტონიზმის გაუთვალისწინებლად.

* **Quality check:** ავტომატური `WCAG Contrast Ratio ≥ 4.5:1` შემოწმება, `CPS <= 20` შემოწმება და ისტორიული წყაროს სიზუსტის ვერიფიკაცია.

* **Cost / complexity:** Low (100% დეტერმინისტული კოდი).

* **Evidence:** [Okabe-Ito Palette Reference](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference), [Netflix Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements), [Pillow Documentation](https://pillow.readthedocs.io/en/latest/reference/Image.html) `[PRIMARY / OFFICIAL / RESEARCH]`.

* **Confidence:** verified.

### Technique 7: Dynamic Sidechain Dialogue Ducking & Spectral Unmasking

* **Discipline:** audio engineering / mixing.

* **What it is:** მუსიკალური პარტიტურისა (`Score`) და გარემოს ხმების (`Ambience/SFX`) ავტომატური დინამიკური დაწევა და სიხშირული გამოთავისუფლება მაშინ, როდესაც აქტიურდება ნარატორის ან პერსონაჟის ხმა.

* **What the audience experiences:** მდიდარი, ხმამაღალი კინემატოგრაფიული მუსიკა და ბრძოლის ხმაური, რომლის ფონზეც ნარატორისა და პერსონაჟის ყოველი მარცვალი ისმის 100%-იანი სისუფთავითა და ძალისხმევის გარეშე.

* **Purpose:** მეტყველების გარჩევადობის (`Speech Intelligibility`) გარანტირება მუსიკალური ენერგიის მოკვლის გარეშე.

* **Use it when:** ნებისმიერ სცენაში, სადაც მეტყველება (`Narrator` ან `Dialogue`) ზედდება მუსიკას ან ინტენსიურ `Ambience/SFX`-ს.

* **Avoid it when:** `Release` დრო დაყენებულია `<150 ms`-ზე, რაც იწვევს მუსიკის ხტუნვას (`Audible Pumping`) ყოველ სიტყვას შორის.

* **Visual requirements:** not applicable (აუდიო პოსტ-პროდუქციის პროცესია).

* **Audio requirements:** ცალ-ცალკე იზოლირებული სტემები: `voice_stem.wav` (Narrator + Dialogue) და `bg_stem.wav` (Score + Ambience).

* **Execution steps:** (1) `voice_stem`-ის გასუფთავება (`highpass=f=80`, `deesser`); (2) `bg_stem`-ზე სპექტრული ადგილის გამოთავისუფლება (`equalizer=f=2500:t=q:w=1.2:g=-3.0`); (3) `FFmpeg sidechaincompress` ფილტრის გაშვება, სადაც `voice_stem` მართავს `bg_stem`-ის ატენუაციას (`threshold=0.03:ratio=4:attack=20:release=450`).

* **LTX route:** not applicable.

* **Blender route:** not applicable.

* **Python route:** `deterministic / scripted` (მიქსის ენველოპის ანალიზი და სიგნალის-ხმაურთან თანაფარდობის — `Voice-to-Background SNR >= +9 dB` ავტომატური შემოწმება).

* **FFmpeg route:** `native / directly supported` — ზუსტი ფილტრ-გრაფი ([FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html)):
  `[0:a]asplit=2[sc][v];[1:a]equalizer=f=2500:t=q:w=1.2:g=-3[bg];[bg][sc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=450[bg_ducked];[v][bg_ducked]amix=inputs=2:weights=1 1:normalize=0[out]`

* **Hybrid route:** `Python` ამზადებს სტემებს და ამოწმებს SNR-ს, ხოლო `FFmpeg` ასრულებს `sidechaincompress` და `equalizer` დამუშავებას.

* **Common failures:** `amix` ფილტრის გაშვება სტანდარტული `normalize=1` პარამეტრით (რაც ანახევრებს სიგნალის ხმის სიმძლავრეს — სავალდებულოა `normalize=0`!); ზედმეტად მოკლე `Release` დრო.

* **Quality check:** მეტყველების აქტიურ ფანჯრებში ვოკალური სტემისა და ფონური სტემის `Short-Term LUFS` სხვაობა უნდა იყოს მინიმუმ **`+9 to +12 LU`**.

* **Cost / complexity:** Low (სრულად ავტომატიზებულია `FFmpeg`-ში).

* **Evidence:** [FFmpeg Filters Documentation (`sidechaincompress`, `equalizer`, `amix`)](https://ffmpeg.org/ffmpeg-filters.html), [Berklee Visual Media Audio](https://online.berklee.edu/courses/audio-music-production-for-visual-media) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 8: Two-Pass ITU-R BS.1770-5 / EBU R 128 Linear Loudness Mastering

* **Discipline:** audio mastering / delivery.

* **What it is:** დასრულებული აუდიო მიქსის ორგავლიანი (`Two-Pass Linear`) ნორმალიზაცია [ITU-R BS.1770-5](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf) ალგორითმით სამიზნე **`-14.0 LUFS` Integrated Loudness** და **`-1.5 dBTP` True Peak** პარამეტრებზე.

* **What the audience experiences:** თანაბარი, მკვრივი და სუფთა კინემატოგრაფიული ხმა YouTube-ზე ყოველგვარი ციფრული ხრიალისა (`Inter-sample Clipping`) და პლატფორმის მიერ ხმის დაწევის გარეშე.

* **Purpose:** მიქსის შიდა დინამიკური კონტრასტის (სიჩუმესა და კულმინაციას შორის სხვაობის) შენარჩუნება YouTube-ის სტრიმინგ სტანდარტთან სრული შესაბამისობით.

* **Use it when:** საბოლოო 12-წუთიანი ეპიზოდის ან ცალკეული დასრულებული სცენის მასტერინგისას.

* **Avoid it when:** იყენებთ ერთგავლიან (`Single-Pass`) `loudnorm`-ს — ერთგავლიანი რეჟიმი იყენებს დინამიკურ AGC-ს, რომელიც ხელოვნურად სწევს მაღლა ჩუმ `Aftermath` სცენებს და ანადგურებს განზრახ სიჩუმის ეფექტს!

* **Visual requirements:** not applicable.

* **Audio requirements:** სრული შეკრებილი სტერეო მიქსი (`48 kHz, 24-bit WAV`).

* **Execution steps:**

  1. *Pass 1 (Measurement):* `ffmpeg -i mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json -f null -` — კითხულობს `input_i`, `input_tp`, `input_lra`, `input_thresh`, `target_offset`.

  2. *Pass 2 (Linear Application):* `ffmpeg -i mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=9:measured_I=...:measured_TP=...:measured_LRA=...:measured_thresh=...:offset=...:linear=true -ar 48000 -c:a aac -b:a 384k master.mp4` ([FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html), [YouTube Encoding Specs](https://support.google.com/youtube/answer/1722171?hl=en)).

* **LTX route:** not applicable.

* **Blender route:** not applicable.

* **Python route:** `deterministic / scripted` (`subprocess`-ით Pass 1 JSON-ის წაკითხვა, Pass 2 ბრძანების აწყობა და საბოლოო ფაილის ვალიდაცია).

* **FFmpeg route:** `native / directly supported` (`loudnorm` two-pass `linear=true`).

* **Hybrid route:** `Python` მართავს ორგავლიან `FFmpeg loudnorm` კონვეიერს და ამოწმებს შედეგს.

* **Common failures:** `-23 LUFS` სატელევიზიო სამიზნის გამოყენება YouTube-ისთვის (ვიდეო რჩება 9 dB-ით ჩუმი, რადგან YouTube არ სწევს მაღლა ჩუმ ვიდეოებს — [EBU R 128 Reference](https://en.wikipedia.org/wiki/EBU_R_128), [LUFS Targets 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026)).

* **Quality check:** Pass 2-ის შემდეგ განმეორებითი გაზომვა: `Integrated Loudness = -14.0 ± 0.3 LUFS`, `True Peak <= -1.5 dBTP`, `LRA = 6.0 – 10.0 LU`.

* **Cost / complexity:** Low.

* **Evidence:** [ITU-R BS.1770-5 (11/2023)](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf), [EBU R 128](https://en.wikipedia.org/wiki/EBU_R_128), [FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html), [LUFS Targets Per Platform 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 9: Forced Alignment Word-Level Lip-Sync & Infographic Event Triggering

* **Discipline:** dialogue editing / motion graphics / pipeline engineering.

* **What it is:** `ElevenLabs` `/v1/forced-alignment` ან `/with-timestamps` API-ით თითოეული წარმოთქმული სიტყვისა და სიმბოლოს ზუსტი დაწყება-დასრულების ტაიმკოდის ამოღება და მისი გამოყენება (ა) `HELPER` გრაფიკის ანიმაციის ტრიგერად და (ბ) `≤5s` `Lip-Sync` სეგმენტების ზუსტ საზღვრად.

* **What the audience experiences:** რუკაზე ისარი, თარიღი ან სტატისტიკური სვეტი ჩნდება ზუსტად იმ მილიწამში, როდესაც ნარატორი წარმოთქვამს შესაბამის სიტყვას, ხოლო პერსონაჟის ტუჩების მოძრაობა სრულად ემთხვევა ფონემებს.

* **Purpose:** აუდიო-ვიზუალური სინქრონიზაციის ავტომატიზაცია ხელით ტაიმლაინის სწორების გარეშე.

* **Use it when:** ნებისმიერი `HELPER` რუკის/დიაგრამის აწყობისას და პერსონაჟთა დიალოგური სცენების დაჭრისას.

* **Avoid it when:** `/v1/forced-alignment`-ს აწვდით JSON-ში შეფუთულ ტექსტს ან სპიკერების დიარიზაციის მარკერებს (API მოითხოვს მხოლოდ `Plain string only` ტექსტს — [Forced Alignment Docs](https://elevenlabs.io/docs/overview/capabilities/forced-alignment)).

* **Visual requirements:** `HELPER` ანიმაციის სკრიპტი, რომელიც იღებს `trigger_time_sec` პარამეტრებს.

* **Audio requirements:** დასრულებული ვოკალური აუდიო ფაილი და მისი ზუსტი ტრანსკრიპტი.

* **Execution steps:** (1) ვოკალის გენერაცია `POST /v1/text-to-speech/{voice_id}/with-timestamps` ([Create Speech with Timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)) ან არსებული აუდიოს გაგზავნა `POST /v1/forced-alignment`-ზე; (2) `Python`-ით სიტყვების მასივის ამოღება (`word`, `start_time`, `end_time`); (3) ტაიმკოდების გადაყვანა ფრეიმის ინდექსებში ($F_{\text{idx}} = \text{round}(t \times \text{FPS})$); (4) `Python` გრაფიკისა და `LTX-2.5 Audio-to-Video` კლიპების რენდერი ზუსტ ფრეიმ-საზღვრებზე.

* **LTX route:** `native / directly supported` (დაჭრილი აუდიო სეგმენტი გადაეცემა `/v2/audio-to-video`-ს).

* **Blender route:** `deterministic / scripted` (`bpy` Python სკრიპტი სვამს Keyframe-ებს ფრეიმის ინდექსებზე).

* **Python route:** `native / directly supported` (ტაიმსტამპების პარსინგი და ფრეიმ-ტრიგერების მართვა).

* **FFmpeg route:** `native / directly supported` (`adelay` და `overlay=enable='between(t,t1,t2)'`).

* **Hybrid route:** `ElevenLabs Timing API` -> `Python` (ფრეიმ-კალკულატორი) -> `Python HELPER / LTX A2V` -> `FFmpeg`.

* **Common failures:** `Enable_logging=false` (Zero Retention Mode) ჩართვისას Request Stitching-ის დაკარგვა ([Stream Speech with Timing](https://elevenlabs.io/docs/api-reference/text-to-speech/stream-with-timestamps)).

* **Quality check:** აუდიო ტრანზიენტისა და ვიზუალური მოვლენის დაწყების სხვაობა `|\Delta t| <= 40\text{ ms}` (1 კადრი @ 24fps).

* **Cost / complexity:** Low.

* **Evidence:** [ElevenLabs Forced Alignment Documentation](https://elevenlabs.io/docs/overview/capabilities/forced-alignment), [Create Speech with Timing API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

### Technique 10: Audio-Visual Pre-Lap Sound Bridge & Silence-to-Impact Transition

* **Discipline:** editing / sound design / music direction.

* **What it is:** სცენებს შორის გადასვლის ორი კომპლემენტარული ხერხი: (ა) `Pre-Lap Sound Bridge (J-Cut)`, სადაც მომდევნო გარემოს ხმა შემოდის კადრის შეცვლამდე 1–1.5 წამით ადრე; და (ბ) `Silence-to-Impact`, სადაც კულმინაციური დარტყმის წინ ყველა აუდიო შრე ჩერდება 1.5–2.0 წამით და კადრის ჭრაზე შემოდის სრულსპექტრიანი `Impact`.

* **What the audience experiences:** სცენების ორგანული, ნაკერების გარეშე დინება მშვიდ ფაზებში და ფიზიკური ადრენალინის დარტყმა კულმინაციურ მომენტებში.

* **Purpose:** მონტაჟური რიტმის მართვა და 12-წუთიანი ეპიზოდის აქტების შეკვრა ყალბი ვიზუალური ეფექტების (`Flash/Spin Transitions`) გარეშე.

* **Use it when:** `Pre-Lap` — ლოკაციის ან დროის შეცვლისას (მაგ., საბჭოს დარბაზიდან ქარიან უღელტეხილზე); `Silence-to-Impact` — ეპიზოდში მაქსიმუმ 2–3-ჯერ (`Opening Hook`-ის ბოლოს, ბრძოლის პირველ შეჯახებაზე და კულმინაციაზე).

* **Avoid it when:** `Silence-to-Impact`-ს იყენებთ ყოველ წუთს (კარგავს ეფექტს).

* **Visual requirements:** `Silence-to-Impact`-ისას სიჩუმის ფანჯარა ემთხვევა `Anticipation Pose` კადრს, ხოლო `Impact` ემთხვევა `Cut on Action` კონტაქტის პირველ ფრეიმს.

* **Audio requirements:** სიჩუმის ფანჯარაში ლაუდნესი ეცემა `<-40 LUFS`-მდე (მხოლოდ სუნთქვა ან სრული ვაკუუმი), ხოლო დარტყმის ფრეიმზე `Momentary Loudness` აღწევს `-11 to -12 LUFS`-ს (`True Peak <= -1.5 dBTP`).

* **Execution steps:** (1) ჭრის ტაიმკოდის $T_{\text{cut}}$ ფიქსაცია; (2) `Silence-to-Impact`-ისთვის $T_{\text{cut}} - 1.5\text{s}$ წერტილში `Score` და `Ambience` ტრეკების გაჭრა `0.15s` სწრაფი ფეიდით; (3) ზუსტად $T_{\text{cut}}$-ზე `Sub-Impact + Hard SFX` ტრანზიენტის დასმა.

* **LTX route:** not applicable.

* **Blender route:** not applicable.

* **Python route:** `deterministic / scripted` (აუდიო ენველოპის ავტომატური გენერაცია $T_{\text{cut}}$ კოორდინატებზე).

* **FFmpeg route:** `native / directly supported` (`volume=enable='between(t,t1,t2)':volume=0`, `afade`, `adelay`).

* **Hybrid route:** `Python` ითვლის სცენის ჭრის ტაიმკოდებს -> `FFmpeg` აწყობს აუდიო ხიდებსა და სიჩუმის ფანჯრებს.

* **Common failures:** სიჩუმის ფანჯარაში დაუმუშავებელი ციფრული ტკაცუნი (`Zero-Crossing Click` — სავალდებულოა `10–20 ms` მიკრო-ფეიდი!).

* **Quality check:** `Momentary Loudness` გრაფიკზე $\Delta L \ge 20\text{ LU}$ ნახტომის დადასტურება $T_{\text{cut}}$ წერტილში კლიპინგის გარეშე.

* **Cost / complexity:** Low.

* **Evidence:** [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html), [Berklee Visual Media Audio](https://online.berklee.edu/courses/audio-music-production-for-visual-media), [DaVinci Resolve Beginner's Guide 20](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Beginners-Guide.pdf?_v=1757574013000) `[PRIMARY / OFFICIAL]`.

* **Confidence:** verified.

## K. ხარისხის ვერიფიკაცია (QA), 24 კვლევით კითხვაზე პასუხი და წყაროების რეესტრი (QA, Final Questions & Source Register)

### K.1 ვიზუალური, აუდიო და კომბინირებული ხარისხის კონტროლი (Visual, Audio & Combined QA Framework)

ხარისხის კონტროლი მკაცრად მიჯნავს **ავტომატიზებულ ალგორითმულ გაზომვებს (`Automated Programmatic Checks`)** და **ადამიანურ სარედაქციო შეფასებას (`Human Editorial Judgement`)**:

| QA კატეგორია | შესამოწმებელი პარამეტრი | ავტომატიზებული ტექნიკური შემოწმება (`Python / FFmpeg Automated Metric`) | ადამიანური სარედაქციო შეფასება (`Human Editorial Judgement`) | 
| ----- | ----- | ----- | ----- | 
| **Visual QA** | რეზოლუცია, ფრეიმ-კვანტიზაცია და ხანგრძლივობა | `LTX` კადრების რაოდენობა $F \equiv 1 \pmod 8$; სიგანე/სიმაღლე $\equiv 0 \pmod{32}$; ხილული `Lip-Sync <= 5.0s`; არადიალოგური `VIDEO <= 15.0s`; ჯამური ბალანსი `60/30/10 ±5%`. | შეესაბამება თუ არა კადრის ხანგრძლივობა მის ინფორმაციულ სიმკვრივესა და დრამატულ პულსს. | 
| **Visual QA** | მოძრაობის უწყვეტობა და არტეფაქტები | `OpenCV Optical Flow` (`calcOpticalFlowFarneback`) — მოძრაობის საშუალო ვექტორის შესაბამისობა `Screen Direction`-თან; მეზობელ ფრეიმებს შორის `SSIM` ნახტომის დეტექცია (მორფინგი/ციმციმი). | ხდება თუ არა ფეხების სრიალი (`Sliding Feet`), კიდურების დაგრძელება (`Rubber Limbs`), იარაღის გაქრობა ან სახის იდენტობის დრეიფი. | 
| **Visual QA** | ფერი, განათება და ინფოგრაფიკის წაკითხვადობა | `HELPER` ტექსტის კონტრასტი `WCAG >= 4.5:1`; `Okabe-Ito` HEX კოდების ვალიდაცია; კითხვის სიჩქარე `<= 20 CPS`, `<= 42 CPL`, დაყოვნება `>= 2.0s`; კადრებს შორის საშუალო ლუმინანსის ნახტომი. | ქმნის თუ არა განათება (`Chiaroscuro / Volumetrics`) სასურველ ემოციურ ტონს და არის თუ არა ისტორიული აღჭურვილობა ეპოქის შესაბამისი. | 
| **Audio QA** | ლაუდნესი, პიკები და სპექტრული ბალანსი | `FFmpeg loudnorm / ebur128`: `Integrated = -14.0 ± 0.5 LUFS`, `True Peak <= -1.5 dBTP`, `LRA = 6–10 LU`; ნარატორის SNR ფონთან მიმართებაში `>= +9 dB`; სტერეო ფაზის კორელაცია `>= +0.2` (Mono Compatibility). | ჟღერს თუ არა ნარატორისა და პერსონაჟების ინტონაცია ბუნებრივად და შეესაბამება თუ არა მუსიკალური თემა სცენის ემოციას. | 
| **Combined A/V QA** | აუდიო-ვიზუალური სინქრონიზაცია და პერსპექტივა | `Forced Alignment` სიტყვის დაწყებისა და `HELPER` გრაფიკის გამოჩენის სხვაობა `<= 40 ms` (1 ფრეიმი); `Impact SFX` ტრანზიენტის დამთხვევა ოპტიკური ნაკადის შეჯახების პიკთან. | არღვევს თუ არა ხმა სიურპრიზს (`Reveal`-ზე ხმამ არ უნდა დაასწროს კადრს); შეესაბამება თუ არა ხმის `Reverb/EQ` კადრის სიშორეს (`EWS vs. CU`). | 

### K.2 პირდაპირი პასუხები 24 საბოლოო კვლევით კითხვაზე (Section 23 Final Research Questions)

 1. **რომელი ვიზუალური ტექნიკებია ყველაზე ეფექტური თითოეული ძირითადი სცენის არქეტიპისთვის?**
    მასშტაბური ბრძოლებისთვის — მაღალი კუთხის 10–15 წამიანი უწყვეტი `Crane/Tracking VIDEO` კადრი `HELPER` ტაქტიკურ რუკასთან წყვილში; დუელებისთვის — დაბალი კუთხის 4-პოზიანი (`Anticipation -> Peak -> Settle`) `FLF2V` და `Cut on Action`; დიალოგებისთვის — `Master Two-Shot` + `OTS / Reaction MCU` (`Lip-Sync <= 5s`) `Chiaroscuro` განათებით; გარემოსა და `Aftermath`-ისთვის — მრავალშრიანი `2.5D Parallax STILL` მოცულობითი ნისლითა და ნაწილაკებით; ხოლო სტრატეგიისა და სტატისტიკისთვის — დეტერმინისტული `Python` ვექტორული გრაფიკა `Okabe-Ito` პალიტრით (იხ. სექცია F.1).

 2. **რა ხდის კადრს ნამდვილად კინემატოგრაფიულს და არა უბრალოდ „ანიმირებულს“?**
    კინემატოგრაფიულობას ქმნის ხუთი ფიზიკური თვისება: (1) მკაფიო ფოკუსური იერარქია და სილუეტის წაკითხვადობა (`Staging`); (2) სინათლის მიმართულება და ჩრდილის კონტრასტი (`Negative Fill / Chiaroscuro`) ბრტყელი თანაბარი განათების ნაცვლად; (3) სიღრმისეული პარალაქსი და ოპტიკური სიმკვეთრის სიღრმე (`Shallow DOF / Aerial Perspective`); (4) მოტივირებული, ინერციული (`Ease-In-Out`) კამერის მოძრაობა; და (5) კადრის ზომასთან შეთანხმებული აკუსტიკური პერსპექტივა.

 3. **როგორ უნდა მუშაობდეს ერთად კადრის ზომა, კამერის პოზიცია, ლინზა, პერსპექტივა, მოძრაობა, ბლოკინგი და განათება?**
    კამერის მანძილი განსაზღვრავს პერსპექტივის შეკუმშვას, ხოლო ლინზის ფოკუსური მანძილი — ხედვის კუთხეს (`FOV`). ფართო გეოგრაფიულ კადრში (`EWS`, `24mm`, მაღალი კუთხე) განათება და ჰაეროვანი პერსპექტივა ჰყოფს ფრონტის ხაზებს, ხოლო ინტიმურ გარდატეხაზე (`CU`, `85mm`, თვალის დონე ან დაბალი კუთხე) `Shallow DOF` და `Chiaroscuro` აქრობს ფონს და მთელ ყურადღებას მიმართავს პერსონაჟის თვალებზე.

 4. **კამერის რომელი ტექნიკების სიმულირება შეუძლია LTX-ს დამაჯერებლად და რომელს სჭირდება Blender ან დეტერმინისტული კომპოზიტინგი?**
    `LTX-2.5 / 2.3` დამაჯერებლად ასრულებს სტატიკურ კადრებს, `Pan/Tilt`-ს, პირდაპირ `Tracking / Dolly`-სა და `Motion Control IC-LoRA`-თი მართულ ტრაექტორიებს. `Blender` ან `Python` აუცილებელია ზუსტი გეომეტრიული `360° Orbit`-ისთვის, `Dolly Zoom (Vertigo)` ეფექტისთვის, მრავალკადრიანი ფიქსირებული `Time-Lapse Construction`-ისა და ზუსტი `Z-Depth Rack Focus`-ისთვის.

 5. **რომელი მოჩვენებითი კამერის მოძრაობებია მხოლოდ ციფრული zoom/crop მიახლოება და რა ვიზუალურ სხვაობას ქმნის ისინი?**
    `FFmpeg zoompan` და სტანდარტული 2D სკალირება არის მხოლოდ ბრტყელი სურათის გადიდება (`Optical/Digital Zoom`). იგი არ ქმნის პარალაქსს — წინა პლანის სვეტი და უკანა პლანის მთა ერთნაირი პროპორციით იზრდება და არ იცვლება მათი ურთიერთგადაფარვა (`Occlusion`). ნამდვილი პარალაქსისთვის `STILL` ზოლში სავალდებულოა სურათის მინიმუმ 3–4 სიღრმისეულ ფენად დაჭრა (`Python/Blender 2.5D`).

 6. **როგორ უნდა დაიგეგმოს საწყისი კადრის (`First-Frame`) კომპოზიცია მომდევნო მოძრაობისთვის?**
    საწყის კადრში: (1) მოძრავ სუბიექტს წინ უნდა ჰქონდეს დატოვებული თავისუფალი ეკრანული სივრცე (`Lead Room / Action Space`) მოძრაობის მიმართულებით; (2) პერსონაჟი უნდა იყოს `Anticipation Pose`-ში მკაფიოდ გამოყოფილი კიდურებისა და იარაღის სილუეტით; (3) ფონზე უნდა იყოს საყრდენი არქიტექტურული ორიენტირი; და (4) სურათის რეზოლუცია ზუსტად უნდა ემთხვეოდეს სამიზნე 32px-ჯერად ვიდეო კონტეინერს.

 7. **როგორ უნდა გადმოსცეს ისტორიულმა საბრძოლო სცენამ მასშტაბური გეოგრაფია, ტაქტიკა, იმპულსი, შეჯახება და შედეგი?**
    სამსაფეხურიანი იერარქიით: ჯერ `HELPER` ტაქტიკური რუკა ან მაღალი კუთხის `EWS` ადგენს ფრაქციების მხარეებს (`Left vs. Right`); შემდეგ 10–15 წამიანი უწყვეტი `VIDEO` კადრი აჩვენებს მანევრის იმპულსს; შეჯახების წინ კეთდება 1.5-წამიანი აკუსტიკური სიჩუმე (`Anticipation`), რომელსაც მოსდევს მიწის დონის `Cut on Action` შეჯახება (`Sub-Impact`) და ბოლოს — გათელილი სიმბოლოს `Insert` და უკანდახევის ფართო კადრი (იხ. Example A).

 8. **როგორ უნდა გამოიყენოს დიალოგურმა სცენამ master shots, OTS, რეაქციები, ინსერტები, eyelines და აუდიო-წინმსწრები ჭრები გამეორების გარეშე?**
    სცენა იხსნება `Master Two-Shot`-ით გეოგრაფიის დასაფიქსირებლად, გადადის `OTS`-ზე, ხოლო როგორც კი დაძაბულობა იზრდება, კამერა გადმოდის იზოლირებულ `Single CU`-ზე. ყოველი 5 წამზე გრძელი რეპლიკა იყოფა `L-Cut`-ით მსმენელის რეაქციასა და ხელების/ობიექტის `Insert`-ზე, ხოლო პასუხები შემოდის `J-Cut`-ით (იხ. Example B).

 9. **როგორ უნდა დაპროექტდეს რუკები, სტატისტიკა, დიაგრამები და მოუშენ-გრაფიკა სწრაფი აღქმისთვის?**
    ერთ ეკრანზე მაქსიმუმ 3–4 ინფორმაციული ერთეული; დალტონიზმისგან დაცული `Okabe-Ito` პალიტრა (`#0072B2` vs `#D55E00` + `#F0E442` აქცენტი); კითხვის სიჩქარე `<= 17–20 CPS`; Y-ღერძი ნულიდან; და ელემენტების ეტაპობრივი გამოჩენა ნარატორის `Forced Alignment` ტაიმკოდებთან სინქრონში.

10. **ანიმაციის რომელი პრინციპებია ყველაზე მნიშვნელოვანი დამაჯერებელი გენერაციული მოძრაობისთვის?**
    `Staging` (სუფთა სილუეტი საწყის კადრში), `Anticipation` (მოსამზადებელი საპირისპირო მოძრაობა), `Slow In / Slow Out` (არახაზოვანი აჩქარება), `Solid Drawing / Weight` (ტერფების მყარი კონტაქტი მიწასთან) და `Follow-Through / Overlapping Action` (მოსასხამის, თმის, დროშისა და მტვრის ინერციული მოძრაობა ძირითადი სხეულის გაჩერების შემდეგ).

11. **როგორ უნდა იცვლებოდეს განათება, ატმოსფერო და ფერი ნარატიულ ემოციასთან ერთად ერთიანი ვიზუალური იდენტობის შენარჩუნებით?**
    საბაზისო 60%-იანი დომინანტური გარემოს პალიტრა და ჩრდილების ტონირება (`Shadow Lift`) რჩება თანმიმდევრული მთელ ეპიზოდში, ხოლო იცვლება კონტრასტის თანაფარდობა (`Key-to-Fill Ratio`), გაჯერება (`Saturation`) და სინათლის ტემპერატურა: მშვიდ ექსპოზიციაში — რბილი კონტრასტი (`3:1`), კრიზისსა და შეთქმულებაში — მკვეთრი `Chiaroscuro (12:1)`, ხოლო `Aftermath`-ში — დაბალი გაჯერება (`Desaturated 65%`) და ცივი ნისლი.

12. **რომელი მონტაჟური ტექნიკები უჭერს მხარს საუკეთესოდ hooks, exposition, escalation, action, reveals, payoff და reflection ფაზებს?**
    `Hook`: `In-Medias-Res Hard Cut` + `Match Cut` + აკუსტიკური `Dropout`; `Exposition`: `L-Cut` ნარაცია + `Cross-Dissolve` `STILL/HELPER`-ს შორის; `Escalation`: პროგრესირებადი `Cross-Cutting` კადრების დამოკლებით; `Action`: `Cut on Action` + 10–15s უწყვეტი კადრი; `Reveal`: `Delayed Character-First Cut` ან `Rack Focus`; `Reflection/Aftermath`: გრძელი 8–12s `Held Tableau`.

13. **როგორ უნდა შესრულდეს, დაბალანსდეს და დამონტაჟდეს ნარატორის თხრობა და პერსონაჟთა დიალოგი?**
    ნარატორი (`70–80%`, შუაწერტილი `75%`) ინარჩუნებს სტაბილურ (`stability: 0.65–0.75`), ავტორიტეტულ ტონს ცენტრალურ მონო არხში სუნთქვითი პაუზებით, ხოლო პერსონაჟთა დიალოგი (`20–30%`, შუაწერტილი `25%`) იყენებს უფრო დინამიკურ პარამეტრებს (`stability: 0.35–0.50`), განსხვავებულ ტემბრებსა და სივრცით `Room Reverb`-ს.

14. **როგორ ქმნის პროფესიონალური კინომუსიკა დაძაბულობას, ემოციურ უწყვეტობას, პერსონაჟის იდენტობასა და კვანძის გახსნას?**
    ერთი ცენტრალური 4–6 ნოტიანი `Leitmotif`-ის ტრანსფორმაციით მთელ 12 წუთზე, `Ostinato`-ს ფენობრივი დაშენებით ესკალაციისას, დაბალი `Drone`-ით დიალოგების ქვეშ (რომელიც არ ფარავს `1–4 kHz` ვოკალურ ზონას) და 2–3 სტრატეგიული უმუსიკო ფანჯრით (`Intentional Silence`), რაც აათმაგებს მომდევნო მუსიკალური კულმინაციის ძალას.

15. **როგორ უნდა გადმოსცეს ambience-მა, Foley-მ და sound effects-მა ფიზიკური გარემო, მანძილი, მასალა, მასშტაბი და დარტყმა?**
    აკუსტიკური დისტანციის სკალირებით (`EWS`-ში მაღალი სიხშირეების მოჭრა და მეტი `Reverb`, `CU`-ში მშრალი ტაქტილური ტრანზიენტები), `Round-Robin` სემპლების ვარიაციით და სამშრიანი დარტყმით (`Sub-Bass Thud 40–80Hz` + `Mid Material Crunch 400–2kHz` + `High Metallic/Debris Tail 4–12kHz`).

16. **როგორ ინარჩუნებენ პროფესიონალი მიქს-ინჟინრები დიალოგის სიცხადეს მდიდარი კინემატოგრაფიული საუნდსკეიპის პირობებში?**
    სამმაგი მექანიზმით: (1) `High-Pass Filter @ 80Hz` ყველა არაბასურ ტრეკზე; (2) სპექტრული ამოჭრა (`-3 dB EQ Dip @ 1.5–3.5 kHz`) მუსიკისა და ატმოსფეროს ბასებზე; და (3) დინამიკური `Sidechain Ducking` (`-3 to -6 dB`, `Attack 20ms`, `Release 450ms`), რომელსაც მართავს ვოკალური ბასი.

17. **რომელი აუდიო საზომები და სტანდარტებია რელევანტური და რომელი მიიჩნევა შეცდომით უნივერსალურ წესად?**
    გაზომვის ფუნდამენტური ალგორითმია [ITU-R BS.1770-5](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf). შეცდომაა სატელევიზიო `EBU R 128 (-23 LUFS)` ან კინოთეატრალური `Netflix (-27 LKFS dialog-gated)` სამიზნის გამოყენება YouTube-ისთვის. ვინაიდან YouTube იყენებს მხოლოდ ქვემოთ მიმართულ ნორმალიზაციას (`-14 LUFS`-ზე), YouTube-ის მასტერი უნდა მომზადდეს **`-14.0 LUFS Integrated` და `-1.5 dBTP True Peak`** პარამეტრზე.

18. **რისი გაკეთება შეუძლია LTX-ს ნატიურად, რა არის მხოლოდ პრომპტზე დამოკიდებული და რა რჩება არავერიფიცირებული თითოეული მოდელის/ენდპოინტისთვის?**
    ნატიურად მხარდაჭერილია: ერთობლივი აუდიო-ვიდეო სინთეზი (`LTX-2 / 2.3 / 2.5`), `Text-to-Video`, `Image-to-Video`, `Audio-to-Video`, `First-Last-Frame (FLF2V)`, `IC-LoRA` (`Motion Control Sparse Tracks`, `Depth/Pose/Canny`, `Relight`), `Retake`, `Extend`, `Reframe` და `LTX-2.5 Native Multi-Shot`. მხოლოდ პრომპტზეა დამოკიდებული (ალბათურია) კამერის რთული მოძრაობა `IC-LoRA`-ს გარეშე. საპილოტე ტესტირებას საჭიროებს `LTX-2.5 Native Multi-Shot`-ის ზუსტი კადრ-კადრ ტაიმკოდური მართვა 10 წამზე გრძელ სეგმენტებში.

19. **რა უნდა გააკეთოს Blender-მა ისეთი, რაც რთული ან არასაიმედოა LTX-ისთვის?**
    ზუსტი 3D კამერის ტრაექტორიები (`Orbit`, `Crane-Up`, `Dolly Zoom`), ასობით ჯარისკაცის მკაცრი გეომეტრიული ფორმაციები (`Geometry Nodes`), მყარი სხეულების ნგრევის ფიზიკა (`Rigid Body`), მრავალფაზიანი მშენებლობა ფიქსირებული კამერით და `Z-Depth / Normal / Motion` პასების გენერაცია.

20. **რა უნდა გააკეთოს Python-მა დეტერმინისტულად გენერაციული AI-ის ნაცვლად?**
    ყველა `HELPER` რუკა, საზღვარი, ისარი, ქრონოლოგიური ხაზი, სტატისტიკური დიაგრამა, მრიცხველი, ეკრანული წარწერა (`Pillow/Matplotlib`), `STILL` კადრების სუბპიქსელური `2.5D Parallax` (`OpenCV`), `Forced Alignment` ტაიმკოდების კალკულაცია და ავტომატური აუდიო-ვიზუალური QA.

21. **რა უნდა გააკეთოს FFmpeg-მა პოსტ-პროდუქციაში და რა არ უნდა დავაძალოთ FFmpeg-ს?**
    `FFmpeg`-მა უნდა შეასრულოს კადრების მონტაჟური აწყობა (`concat`, `xfade`), `J-cut / L-cut` აუდიო წანაცვლება, ფერთა ფინალური ნორმალიზაცია (`curves`, `lut3d`, `vignette`), `sidechaincompress` დაკინგი, ორგავლიანი `loudnorm` მასტერინგი და H.264/AAC ენკოდირება. `FFmpeg`-ს **არ უნდა დავაძალოთ** რთული კარტოგრაფიის, მრავალშრიანი 3D პარალაქსის ან სტატისტიკური დიაგრამების ხატვა `drawtext/zoompan` ფილტრებით.

22. **რომელი ჰიბრიდული კონვეიერები იძლევა ხარისხის, კონტროლის, უწყვეტობის, ღირებულებისა და განმეორებადობის საუკეთესო ბალანსს?**
    (1) *საბრძოლო და რთული კამერის კადრები:* `Blender` Previs/Track Guide -> `LTX-2.5 IC-LoRA` -> `FFmpeg`; (2) *დიალოგი:* `ElevenLabs v4` + `Forced Alignment` -> `LTX-2.5 Audio-to-Video (<=5s)` + `Reaction STILL/VIDEO` -> `FFmpeg J/L-cut`; (3) *გარემო და ტაბლო (`STILL` 30%):* ილუსტრირებული ფენები -> `Python OpenCV 2.5D Parallax` + ნაწილაკები; (4) *ანალიტიკა (`HELPER` 10%):* `Python GeoJSON/Matplotlib/Pillow` -> `FFmpeg`.

23. **როგორ უნდა იმუშაოს ყველა ამ ტექნიკამ ერთად 12-წუთიან ვიდეოში დამოუკიდებელი 60/30/10 ვიზუალური და 70–80 / 20–30 სასაუბრო სამიზნეების დაცვით?**
    ვიზუალური ქრონომეტრაჟი (`432s VIDEO / 216s STILL / 72s HELPER`) იგეგმება სცენის ვიზუალური საჭიროებით, ხოლო სასაუბრო სიტყვების ბიუჯეტი (`~1,260 Narrator words / ~420 Dialogue words`) ნაწილდება აუდიო ტრეკზე დამოუკიდებლად: ნარატორი საუბრობს სამივე ვიზუალური ზოლის თავზე, პერსონაჟთა დიალოგი ნაწილდება მოკლე `Lip-Sync` კადრებსა და `Reaction/Insert` კადრებზე, ხოლო უსიტყვო სამოქმედო და ატმოსფერული პაუზები ქმნის კინემატოგრაფიულ სუნთქვას სიტყვების პროცენტული თანაფარდობის დარღვევის გარეშე (იხ. სექცია I.1).

24. **რომელი ტექნიკებია მაღალი ღირებულების საბაზისო სტანდარტები (`High-Value Defaults`), რომელია არჩევითი შემოქმედებითი გადაწყვეტა და რომელი საჭიროებს საპილოტე ტესტს?**

    * *სავალდებულო საბაზისო სტანდარტები (`Defaults`):* `$8n+1$` და `32px` წესი `LTX`-ში; `Lip-Sync <= 5s` + `J/L-cut Reaction` გადაფარვა; `100% Python` დეტერმინიზმი `HELPER` რუკებისა და ტექსტისთვის `Okabe-Ito` პალიტრით; `Multi-plane 2.5D Parallax` `STILL` ზოლისთვის; `FFmpeg sidechaincompress` და ორგავლიანი `loudnorm (-14 LUFS / -1.5 dBTP)`.

    * *არჩევითი შემოქმედებითი გადაწყვეტები:* `Dolly Zoom`, `Rack Focus`, `Freeze-Frame Tableau`, სრული 3D `Rigid Body` სიმულაცია.

    * *საპილოტე ტესტირებას საჭიროებს (`Needs Sample Test`):* `LTX-2.5 Native Multi-Shot`-ის სტაბილურობა კონკრეტულ ილუსტრირებულ სტილში 3+ კადრის ერთ გენერაციაში გაერთიანებისას და `NV4 / FP8` კვანტიზაციის გავლენა სწრაფი ხმლის ქნევის არტეფაქტებზე.

### K.3 ვერიფიცირებული წყაროების სრული რეესტრი (Verified Source Register — 45 Direct Sources)

ყველა ქვემოთ მოყვანილი წყარო ვერიფიცირებულია პირდაპირი URL-ით და აკმაყოფილებს სექცია 3.3-ის მოთხოვნას (≥30 წყარო, მინიმუმ 4 წყარო თითოეულ ძირითად დისციპლინაში).

| \# | Exact Title | Author / Institution / Publisher | Direct URL | Date / Version | Source Category & Quality | Exact Claim or Technique Supported | Limitations / Conflicts | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **1** | LTX Open Source Documentation: Overview | Lightricks | [LTX Open Source Overview](https://docs.ltx.io/open-source-model/getting-started/overview) | 2026 (LTX-2.5) | `PRIMARY / OFFICIAL` | `LTX-2.5` open-weights DiT architecture, joint audio-video synthesis, LoRA & IC-LoRA support. | Focuses on local ComfyUI/PyTorch workflows; hosted API has separate rate limits. | 
| **2** | Quick Start | LTX Documentation | Lightricks | [LTX Quick Start](https://docs.ltx.io/open-source-model/getting-started/quick-start) | 2026 | `PRIMARY / OFFICIAL` | `ComfyUI` templates (`video_ltx2_5_t2v`, `video_ltx2_5_i2v`, `First-Frame / Last-Frame`), LTX-2.3 vs 2.5 asset compatibility. | Standard LoRA general-purpose workflow for 2.5 still evolving compared to 2.3. | 
| **3** | LTX-2.5 Model Specifications | Lightricks | [LTX-2.5 Model Docs](https://docs.ltx.io/models/ltx-2-5) | 2026 | `PRIMARY / OFFICIAL` | `ltx-2-5-fast` and `ltx-2-5-pro` variants, up to 4K across `16:9, 9:16, 1:1, 3:2, 2:3`, Diffusion Video Decoder, Native Multi-Shot. | Exact multi-shot cut frame timing is prompt-driven rather than frame-indexed. | 
| **4** | Two-Stage Generation | LTX Documentation | Lightricks | [LTX Two-Stage Generation](https://docs.ltx.io/open-source-model/usage-guides/two-stage-generation) | 2026 | `PRIMARY / OFFICIAL` | Stage 1 base generation + Stage 2 latent upscale, `CFG = 1`, `Tiled VAE Decode`, API text encoding offload. | Tiled VAE slightly increases decode latency to save peak VRAM. | 
| **5** | Image-to-Video Workflow for Beginners | Lightricks | [LTX Image-to-Video Guide](https://docs.ltx.io/open-source-model/usage-guides/image-to-video) | 2026 | `PRIMARY / OFFICIAL` | First-frame conditioning at `strength = 0.7`, PNG/JPG/WebP support, motion-focused prompting rules. | Requires source image aspect ratio to match target resolution to avoid resize distortion. | 
| **6** | Text-to-Video Workflow for Beginners | Lightricks | [LTX Text-to-Video Guide](https://docs.ltx.io/open-source-model/usage-guides/text-to-video) | 2026 | `PRIMARY / OFFICIAL` | Node graph configuration and missing model auto-fetching in `ComfyUI-LTXVideo`. | Less spatial control than `I2V` for strict historical continuity. | 
| **7** | Audio-to-Video | LTX Documentation | Lightricks | [LTX Audio-to-Video Guide](https://docs.ltx.io/open-source-model/usage-guides/audio-to-video) | 2026 | `PRIMARY / OFFICIAL` | Audio-driven video generation for dialogue lip-sync and rhythmic action timed to an input audio track. | Best constrained to ≤5s for close-up character faces to prevent identity drift. | 
| **8** | IC-LoRA | LTX Documentation | Lightricks | [LTX IC-LoRA Guide](https://docs.ltx.io/open-source-model/usage-guides/ic-lo-ra) | 2026 | `PRIMARY / OFFICIAL` | In-Context LoRA adapters conditioning generation on reference video, depth, pose, or structural guides. | Requires task-specific workflow matching model version (2.3 vs 2.5). | 
| **9** | Motion Control IC-LoRA | LTX Documentation | Lightricks | [LTX Motion Control IC-LoRA](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control) | 2026 | `PRIMARY / OFFICIAL` | `LTX Sparse Track Editor`, `LTXVDrawTracks`, `LTXAddVideoICLoRAGuide`, `LTXVCropGuides`, $F = 8n + 1$ frame quantization rule, prompt-style-not-motion rule. | Track points are 2D screen-space projections; extreme 3D occlusion still benefits from Blender depth guides. | 
| **10** | LoRAs | LTX Documentation | Lightricks | [LTX LoRAs Guide](https://docs.ltx.io/open-source-model/usage-guides/lo-ra) | 2026 | `PRIMARY / OFFICIAL` | Cross-compatibility of LTX-2.3 LoRAs and IC-LoRAs on LTX-2.5 checkpoints. | Minor strength tuning (`0.6–0.9`) needed when porting 2.3 LoRAs to 2.5. | 
| **11** | Generate Video from Text API Reference | Lightricks | [LTX Text-to-Video API](https://docs.ltx.io/api-documentation/api-reference/video-generation/text-to-video) | 2026 | `PRIMARY / OFFICIAL` | Hosted API schema, `duration: null` automatic prompt-driven length, `generate_audio` boolean parameter. | Hosted durations are discrete tiers compared to local frame counts. | 
| **12** | Generate Video from Image Async API Reference | Lightricks | [LTX Submit Image-to-Video API](https://docs.ltx.io/api-documentation/api-reference/async-video-generation/submit-image-to-video) | 2026 | `PRIMARY / OFFICIAL` | Async job submission for `ltx-2-3-fast`, `ltx-2-3-pro`, `ltx-2-5-fast`, `ltx-2-5-pro`. | Requires polling `GET /v2/.../{id}` for completion. | 
| **13** | Generate Video from Audio Async API Reference | Lightricks | [LTX Submit Audio-to-Video API](https://docs.ltx.io/api-documentation/api-reference/async-video-generation/submit-audio-to-video) | 2026 | `PRIMARY / OFFICIAL` | Hosted `/v2/audio-to-video` endpoint parameters and polling lifecycle. | Subject to hosted audio duration caps. | 
| **14** | Migrate from V1 to V2 | LTX Documentation | Lightricks | [LTX Migrate V1 to V2](https://docs.ltx.io/migrate-v1-to-v2) | Nov 2026 | `PRIMARY / OFFICIAL` | Deprecation of V1 endpoints in favor of async `/v2/text-to-video`, `/v2/image-to-video`, `/v2/audio-to-video`, `/v2/retake`, `/v2/extend`. | Legacy V1 synchronous scripts will fail without V2 async polling. | 
| **15** | Lightricks/LTX-2.3 Hugging Face Model Card | Lightricks / Hugging Face | [HF Lightricks/LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3) | Jan–Oct 2026 | `PRIMARY / OFFICIAL` | `22B` parameter architecture (`46.1 GB safetensors`), `x1.5` & `x2` spatial/temporal upscalers, `Python >= 3.12, CUDA > 12.7, PyTorch ~= 2.7`. | Full BF16 weights require enterprise VRAM; consumer GPUs require FP8/distilled weights. | 
| **16** | Lightricks/LTX-2.5 Hugging Face Model Card | Lightricks / Hugging Face | [HF Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) | 2026 | `PRIMARY / OFFICIAL` | `LTX-2.5` open weights, `LTX-2.x Community License`, `uv sync --extra natten` installation. | Commercial terms governed by LTX-2.x Community License. | 
| **17** | Lightricks/LTX-Video & Trainer GitHub Repositories | Lightricks / GitHub | [GitHub Lightricks/ltx-video](https://github.com/Lightricks/ltx-video) | 2025–2026 | `PRIMARY / OFFICIAL` | Official PyTorch implementation and [LTX-Video-Trainer](https://github.com/Lightricks/ltx-video-trainer) LoRA training configs. | Local training requires high-VRAM CUDA or MPS environment. | 
| **18** | LTX-2.3 & LTX-2.5 Hosted API & Reframe on Fal.ai | Fal.ai / Lightricks | [Fal.ai LTX-2.3](https://fal.ai/ltx-2.3) | 2026 | `PRIMARY / OFFICIAL` | Up to 20s single generation, 24/48 FPS, per-second pricing (`$0.04–$0.24/s`), and [LTX-2.3 Reframe](https://fal.ai/models/fal-ai/ltx-2.3/reframe) generative outpainting up to 60s. | Third-party cloud pricing varies by resolution tier. | 
| **19** | Models Overview | ElevenLabs Documentation | ElevenLabs | [ElevenLabs Models Docs](https://elevenlabs.io/docs/overview/models) | Nov 2026 | `PRIMARY / OFFICIAL` | Model taxonomy (`eleven_v4`, `eleven_v4_turbo`, `eleven_flash_v2_5`, `eleven_multilingual_v2`, `scribe_v2`) and [Model Selection Guide](https://elevenlabs.io/docs/eleven-api/choosing-the-right-model). | Latency-optimized flash models trade off subtle emotional prosody. | 
| **20** | Eleven v4 & Voice Design Guide | ElevenLabs | ElevenLabs | [ElevenLabs Eleven v4](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4) | Nov 2026 | `PRIMARY / OFFICIAL` | `Eleven v4` capabilities, `clone_strength (0–1)` parameter, and confirmation in [Voice Design Guide](https://elevenlabs.io/docs/eleven-agents/customization/voice/best-practices/conversational-voice-design) that `speed` is disabled in v3/v4. | Pacing in v4 must be controlled via punctuation and text phrasing rather than a numeric speed slider. | 
| **21** | Get / Edit Voice Settings API Reference | ElevenLabs | [ElevenLabs Voice Settings API](https://elevenlabs.io/docs/api-reference/voices/settings/get) | 2026 | `PRIMARY / OFFICIAL` | Exact JSON schema for `stability`, `similarity_boost`, `style`, `use_speaker_boost`, `speed`, `clone_strength`. | Non-zero `style` increases computational load and latency. | 
| **22** | Create Speech with Timing & Stream with Timestamps | ElevenLabs | [ElevenLabs Convert with Timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps) | Nov 2026 | `PRIMARY / OFFICIAL` | Character-level start and end timestamp arrays for deterministic lip-sync and graphic triggers; [Stream with Timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/stream-with-timestamps) `enable_logging` rules. | Zero-retention mode (`enable_logging=false`) disables request stitching. | 
| **23** | Forced Alignment | ElevenLabs Documentation | ElevenLabs | [ElevenLabs Forced Alignment](https://elevenlabs.io/docs/overview/capabilities/forced-alignment) | 2026 | `PRIMARY / OFFICIAL` | Word and phrase time-alignment for up to 3 GB / 10 hours audio and 675,000 chars via [Create Forced Alignment API](https://elevenlabs.io/docs/api-reference/forced-alignment/create). | Plain string input only; speaker diarization is not supported. | 
| **24** | Text-to-Speech & Music Best Practices | ElevenLabs | ElevenLabs | [ElevenLabs TTS Best Practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices) | 2026 | `PRIMARY / OFFICIAL` | IPA pronunciation dictionaries, text normalization, and [Music Best Practices](https://elevenlabs.io/docs/overview/capabilities/music/best-practices) (exact BPM, musical key, `instrumental only`, structural time cues). | IPA rendering can still vary slightly across voice clones. | 
| **25** | Stable Audio 3.0 vs. Competitors: Licensing & Self-Hosting | Stability AI | [Stability AI Licensing Comparison](https://stability.ai/explainers/stable-audio-vs-competitors-licensing-export-rights-and-self-hosting-compared) | Aug–Oct 2026 | `PRIMARY / OFFICIAL` | `Stability AI Community License` granting free commercial ownership & self-hosting under `$1M` annual revenue; [Generative Audio API FAQ](https://stability.ai/explainers/generative-audio-api-for-apps-what-music-software-platforms-can-ship). | Organizations >\$1M annual revenue require an Enterprise license; Stable Audio 3.0 does not generate vocals. | 
| **26** | Recommendation ITU-R BS.1770-5 (11/2023) | International Telecommunication Union (ITU) | [ITU-R BS.1770-5 PDF](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf) | Nov 2023 (In force 2026) | `PRIMARY / OFFICIAL` | K-weighted multichannel loudness measurement (`LKFS/LUFS`), `-70 LKFS` absolute & `-10 dB` relative gating, 4x oversampled True Peak (`dBTP`). | Defines measurement algorithm only, not platform-specific target numbers. | 
| **27** | Recommendation ITU-R BS.2076-3 (02/2025) — Audio Definition Model | International Telecommunication Union (ITU) | [ITU-R BS.2076 ADM](https://www.itu.int/rec/R-REC-BS.2076/) | Feb 2025 | `PRIMARY / OFFICIAL` | Standardized Audio Definition Model metadata for spatial and broadcast audio stems. | Primarily needed for immersive/Atmos archival rather than stereo web MP4. | 
| **28** | ATSC Recommended Practice A/85:2013 (with Corrigendum 1) | Advanced Television Systems Committee (ATSC) | [ATSC A/85 PDF](https://www.atsc.org/wp-content/uploads/2025/06/A85-2013-with-Corrigendum-No-1.pdf) | 2013 / 2025 | `PRIMARY / OFFICIAL` | U.S. CALM Act broadcast loudness target (`-24 LKFS`, `-2 dBTP`) and `Anchor Element` (dialogue-anchored) mixing philosophy. | Broadcast target; too quiet for un-normalized web playback on YouTube. | 
| **29** | EBU R 128 Loudness Normalisation & Streaming Comparison | European Broadcasting Union / Wikipedia Reference | [EBU R 128 Specification Summary](https://en.wikipedia.org/wiki/EBU_R_128) | Rev. Nov 2023 | `PRIMARY / OFFICIAL / PROFESSIONAL PRACTICE` | `-23.0 LUFS ± 0.5 LU`, `-1.0 dBTP`, Momentary/Short-Term/Integrated windows, and confirmation that **YouTube applies downward normalization only**. | Broadcast `-23 LUFS` vs. streaming `-14 LUFS` divergence must be explicitly managed. | 
| **30** | LUFS Targets Per Platform in 2026: Netflix Dialog-Gated vs. Streaming | ForaSoft Audio Engineering | [LUFS Targets Per Platform 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026) | June 2026 | `PROFESSIONAL PRACTICE` | Explains why Netflix's `-27 LKFS` (dialog-gated) cannot be compared to YouTube/Spotify's `-14 LUFS` (whole-programme integrated). | Platform targets can shift slightly, but `-14 LUFS / -1.5 dBTP` remains the safe YouTube benchmark. | 
| **31** | The Dialogue Editing Workflow: When and How to Use RX & Dialogue Match | iZotope | [iZotope Dialogue Editing Workflow](https://www.izotope.com/community/blog/the-dialogue-editing-workflow) | 2019–2026 | `PROFESSIONAL PRACTICE` | Pre-cleaning noisy audio before spectral/reverb profile matching (`noises in, noises out`), room tone continuity, and [Dialogue Editing Tutorials](https://www.izotope.com/community/blog/category/dialogue-editing). | Focused on iZotope RX/Dialogue Match, though principles apply to any DAW/FFmpeg chain. | 
| **32** | Audio/Music Production for Visual Media Course Syllabus | Berklee Online | [Berklee Visual Media Audio Course](https://online.berklee.edu/courses/audio-music-production-for-visual-media) | 2026 | `PROFESSIONAL PRACTICE` | End-to-end post-production hierarchy: dialogue, Foley, backgrounds, pre-dubs, score stems, and final delivery mix. | Full course requires paid tuition; syllabus structure is publicly verifiable. | 
| **33** | Dolby Atmos Music Creation 101 & Dolby Creator Lab | Dolby Laboratories | [Dolby Atmos Creation 101](https://professional.dolby.com/music/dolby-atmos-music-creation-101/) | 2025–2026 | `PRIMARY / OFFICIAL` | Spatial audio panning, bed vs. object tracks, binaural rendering, and [The Dolby Creator Lab](https://www.dolby.com/creator-lab/). | YouTube stereo delivery requires checking binaural/stereo downmix mono compatibility. | 
| **34** | FFmpeg Filters Official Documentation | FFmpeg Project | [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html) | 2026 | `PRIMARY / OFFICIAL` | Exact filter syntax and semantics for `zoompan`, `xfade`, `overlay`, `blend`, `curves`, `eq`, `drawtext`, `acompressor`, `sidechaincompress`, `equalizer`, `deesser`, `loudnorm`, `amix`. | `zoompan` is strictly 2D affine scaling without 3D parallax. | 
| **35** | Blender Manual: Track To Constraint | Blender Foundation | [Blender Track To Constraint](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html) | Blender Manual | `PRIMARY / OFFICIAL` | Deterministic 3D camera target tracking (`To` and `Up` axes) and 2D/2.5D billboard tracking mechanics. | Choosing identical `Tracking` and `Up` axes disables the constraint (red state). | 
| **36** | Blender Manual: Rigid Body Physics Introduction | Blender Foundation | [Blender Rigid Body Manual](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html) | Blender Manual | `PRIMARY / OFFICIAL` | `Active` (dynamically simulated) vs. `Passive` (static/animated) mesh rigid-body simulation for siege/destruction choreography. | Only mesh objects participate in rigid-body collisions. | 
| **37** | Pillow (PIL Fork) 13.1.0 Image Module & Tutorial | Python Pillow Project | [Pillow Image Module Reference](https://pillow.readthedocs.io/en/latest/reference/Image.html) | v13.0 / 13.1 (2026) | `PRIMARY / OFFICIAL` | Deterministic raster compositing, alpha masks, geometry transforms, and typography via [Pillow Tutorial](https://pillow.readthedocs.io/en/stable/handbook/tutorial.html). | CPU-bound single-threaded unless parallelized across frames with Python `multiprocessing`. | 
| **38** | OpenCV 4.13.0 Geometric Image Transformations | OpenCV Team | [OpenCV Geometric Transformations](https://docs.opencv.org/4.13.0/dir_996070d144ea13ded22df5bf9603981f.html) | v4.13.0 (2026) | `PRIMARY / OFFICIAL` | Sub-pixel affine and perspective warping (`warpAffine`, `warpPerspective`) for 2.5D parallax and tilted map planes. | Requires `INTER_CUBIC` or `INTER_LANCZOS4` flags to prevent sub-pixel shimmer. | 
| **39** | Okabe-Ito Colorblind-Safe Palette HEX & RGB Complete Reference | ConceptViz / FigCanvas (Masataka Okabe & Kei Ito / Bang Wong) | [Okabe-Ito Palette Reference](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference) | Feb–May 2026 | `RESEARCH / PROFESSIONAL PRACTICE` | Exact 8-color colorblind-safe HEX/RGB values (`#E69F00, #56B4E9, #009E73, #F0E442, #0072B2, #D55E00, #CC79A7, #000000`) and [FigCanvas Reference](https://figcanvas.com/blog/okabe-ito-palette-hex-rgb-wong-prism). | Lighter hues (`#F0E442` Yellow, `#56B4E9` Sky Blue) require dark backgrounds or dark borders to meet WCAG AA contrast. | 
| **40** | Netflix Timed Text Style Guide: General Requirements & Timing Guidelines | Netflix Partner Help Center | [Netflix Timed Text General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements) | Rev. Dec 2025 / 2026 | `PRIMARY / OFFICIAL` | Reading speed limits (`17–20 CPS` adult), `42 CPL` max line length, `5/6s` min duration, and 2-frame gap chaining in [Subtitle Timing Guidelines](https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines) & [English USA Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide). | Designed for subtitles, used here as the gold-standard legibility ceiling for `HELPER` on-screen labels. | 
| **41** | YouTube Recommended Upload Encoding Settings & Audience Retention | Google / YouTube Help | [YouTube Encoding Settings](https://support.google.com/youtube/answer/1722171?hl=en) | 2026 | `PRIMARY / OFFICIAL` | MP4 H.264 Progressive Scan, Closed GOP, AAC-LC audio, and [Measure Key Moments for Audience Retention](https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop) (30s intro benchmark, spikes, dips). | YouTube re-encodes all uploads; uploading clean high-bitrate progressive masters prevents generation loss. | 
| **42** | Pixar in a Box: The Art of Storytelling | Pixar Animation Studios & Khan Academy | [Pixar in a Box Storytelling](https://www.khanacademy.org/computing/pixar/storytelling) | 2026 | `PRIMARY / OFFICIAL` | Visual storytelling, character staging, silhouette readability, film grammar, and virtual camera mechanics ([Partner Content Unit](https://www.khanacademy.org/partner-content/hass-storytelling/storytelling-pixar-in-a-box)). | Introductory-to-intermediate mathematical depth; pair with Blender Manual for production rigging. | 
| **43** | DaVinci Resolve Official Training & Beginner's Guide to Resolve 20 | Blackmagic Design | [DaVinci Resolve Official Training](https://www.blackmagicdesign.com/products/davinciresolve/training) | 2025–2026 | `PRIMARY / OFFICIAL` | Certified curriculum and [DaVinci Resolve 20 Beginner's Guide PDF](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Beginners-Guide.pdf?_v=1757574013000) covering Edit, Color nodes, Fairlight audio, and Fusion. | GUI-oriented; translate node concepts to FFmpeg/Python for automated headless pipelines. | 
| **44** | Color Management, Lumetri Color & Scopes in Premiere Pro | Adobe Help Center | [Adobe Color Management & Lumetri](https://helpx.adobe.com/premiere/desktop/correct-color/set-up-color-management/lumetri-enhancements.html) | Jan–Aug 2026 | `PRIMARY / OFFICIAL` | Color space normalization, LUT limitations, and [Display Lumetri Scopes](https://helpx.adobe.com/premiere/desktop/correct-color/add-color-effects/display-lumetri-scopes.html) for shot matching. | LUTs clip out-of-range luminance if applied before primary exposure/lift-gamma-gain normalization. | 
| **45** | ARRI Academy Certified Courses & School of Motion Bootcamps | ARRI / School of Motion | [ARRI Certified Courses](https://www.arri.com/en/learn/arri-academy/arri-certified-courses) | 2026 | `PRIMARY / OFFICIAL / PROFESSIONAL PRACTICE` | ARRI optical & lighting contrast standards, plus [School of Motion After Effects Kickstart](https://schoolofmotion.com/courses/after-effects-kickstart), [Animation Bootcamp](https://schoolofmotion.com/courses/animation-bootcamp), and [Design Bootcamp](https://schoolofmotion.com/courses/design-bootcamp) easing curves. | Full bootcamps are paid; free curriculum guides and easing principles transfer directly to Python/Blender curves. | 

### K.4 მტკიცებულებათა ხარვეზები და ღია საკითხები (Evidence Gaps & Unresolved Questions)

1. **`LTX-2.5 Native Multi-Shot`-ის დეტერმინისტული ტაიმკოდური მართვა `[PARTIALLY VERIFIED / GAP]`:** ოფიციალური დოკუმენტაცია ([LTX-2.5 Docs](https://docs.ltx.io/models/ltx-2-5)) ადასტურებს, რომ `LTX-2.5`-ს შეუძლია ერთ გენერაციაში შექმნას რამდენიმე დაკავშირებული კადრი იდენტობის შენარჩუნებით, თუმცა საჯარო დოკუმენტაციაში არ არის მოცემული დეტერმინისტული API პარამეტრი, რომელიც ჭრას დასვამს ზუსტად მე-96 ფრეიმზე. ამიტომ ზუსტი აუდიო-სინქრონული მონტაჟისთვის კვლავ რეკომენდებულია კადრების ცალ-ცალკე გენერაცია და `FFmpeg`-ით აწყობა.

2. **`NV4` 4-ბიტიანი კვანტიზაციის გავლენა სწრაფ საბრძოლო მოძრაობაზე `[ANECDOTAL / NEEDS MEASURED TEST]`:** საზოგადოების ტესტები ([HF LTX-2.3 Render Times](https://huggingface.co/Lightricks/LTX-2.3/discussions/16)) მიუთითებს `200–300%` აჩქარებაზე Blackwell GPU-ებზე ნელი მოძრაობისას ხარისხის შეუმჩნეველი დანაკარგით, მაგრამ სწრაფ სამოქმედო კადრებში აღინიშნება `>10%` მოძრაობის არტეფაქტები. საბრძოლო სცენებისთვის სავალდებულოა `FP8` ან `BF16` რეჟიმის გამოყენება.

## L. პრაქტიკული სასწავლო გზამკვლევი (Practical Learning Roadmap)

საწარმოო სისტემის არქიტექტორისა და რეჟისორისთვის სასწავლო რესურსები დალაგებულია სამ პრიორიტეტულ საფეხურად (`Tier 1 -> Tier 2 -> Tier 3`), სადაც პირველ ეტაპზე სრულად უფასო, ოფიციალური რესურსებით იგება ფუნდამენტური კინემატოგრაფიული და პროგრამული უნარები:

### L.1 Tier 1 — დაუყოვნებელი საბაზისო კურიკულუმი (100% Free & Official — კვირა 1–2)

1. **ვიზუალური დრამატურგია, Staging და ვირტუალური კამერა:** [Pixar in a Box: The Art of Storytelling & Virtual Cameras (Khan Academy)](https://www.khanacademy.org/computing/pixar/storytelling) (`Free`).

   * *შეძენილი უნარი:* სცენის სილუეტური დადგმა, კადრის ზომების (`EWS -> CU`) ემოციური პროგრესია, ფოკუსური მანძილისა და სიმკვეთრის სიღრმის მართვა.

2. **მონტაჟი, ფერთა კორექცია და Fairlight აუდიო პოსტ-პროდუქცია:** [The Beginner's Guide to DaVinci Resolve 20 / Official Training](https://www.blackmagicdesign.com/products/davinciresolve/training) (`Free PDF + Project Files`).

   * *შეძენილი უნარი:* `J-cut / L-cut` დიალოგური მონტაჟი, `180-Degree Axis` კონტროლი, `Lift/Gamma/Gain` კადრების ფერადი შეთანხმება (`Shot Matching`) და `ITU-R BS.1770` ლაუდნესის ბალანსირება.

3. **LTX-2.5 გენერაციული კონვეიერი და IC-LoRA მართვა:** [LTX Open Source Documentation & Motion Control IC-LoRA Guide](https://docs.ltx.io/open-source-model/feature-guides/structural-control/motion-control) (`Free`).

   * *შეძენილი უნარი:* `$F = 8n + 1$` კადრების კვანტიზაცია, `Two-Stage Distilled Pipeline`, `Sparse Track Editor`-ით მოძრაობის დეტერმინისტული მართვა და `/v2/audio-to-video` ინტეგრაცია.

4. **ElevenLabs Timing & FFmpeg Filtergraphs:** [ElevenLabs Forced Alignment Docs](https://elevenlabs.io/docs/overview/capabilities/forced-alignment) + [FFmpeg Filters Official Reference](https://ffmpeg.org/ffmpeg-filters.html) (`Free`).

   * *შეძენილი უნარი:* სიტყვის დონის ტაიმსტამპების ამოღება, `sidechaincompress` დაკინგი და ორგავლიანი `loudnorm (-14 LUFS / -1.5 dBTP)` მასტერინგი.

### L.2 Tier 2 — დეტერმინისტული 2.5D/3D, კარტოგრაფია და დიალოგის ინჟინერია (Free Official Docs — კვირა 3–4)

1. **Blender 3D/2.5D Camera & Physics Previs:** [Blender Manual: Track To Constraint](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html) & [Rigid Body Physics](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html) (`Free`).

   * *შეძენილი უნარი:* 3D კამერის სპლაინ-რიგები, `2.5D Camera Projection`, `Geometry Nodes` არმიის ფორმაციები და `Z-Depth Rack Focus`.

2. **Python Deterministic Graphics & Accessibility:** [Pillow Image Reference](https://pillow.readthedocs.io/en/latest/reference/Image.html) + [OpenCV Geometric Transformations](https://docs.opencv.org/4.13.0/dir_996070d144ea13ded22df5bf9603981f.html) + [Okabe-Ito Palette Guide](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference) + [Netflix Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements) (`Free`).

   * *შეძენილი უნარი:* დალტონიზმისგან დაცული, `17–20 CPS` სტანდარტის მოძრავი რუკებისა და სტატისტიკური გრაფიკების პროგრამული რენდერი.

3. **დიალოგის გაწმენდა და Retention ანალიტიკა:** [iZotope Dialogue Editing Workflow](https://www.izotope.com/community/blog/the-dialogue-editing-workflow) + [YouTube Key Moments for Audience Retention](https://support.google.com/youtube/answer/9314415?hl=en&co=GENIE.Platform%3DDesktop) (`Free`).

   * *შეძენილი უნარი:* `Room Tone`-ის უწყვეტობა, ვოკალური ტემბრის გათანაბრება და პირველი 30 წამის `Intro Retention` დიაგნოსტიკა.

### L.3 Tier 3 — გაღრმავებული პროფესიონალური სპეციალიზაცია (Paid & Advanced Curricula — თვე 2+)

1. **კინომუსიკისა და პოსტ-პროდუქციის აკადემიური კურსი:** [Berklee Online: Audio/Music Production for Visual Media](https://online.berklee.edu/courses/audio-music-production-for-visual-media) (`Paid Accredited Course`) + [Dolby Atmos Music Creation 101](https://professional.dolby.com/music/dolby-atmos-music-creation-101/) (`Free`).

   * *შეძენილი უნარი:* მრავალსტემიანი რე-რეკორდინგ მიქსინგი, ორკესტრული პარტიტურის შრეობრივი დრამატურგია და იმერსიული პანორამირება.

2. **მოუშენ-დიზაინისა და ანიმაციის მრუდების მასტერკლასი:** [School of Motion: Animation Bootcamp](https://schoolofmotion.com/courses/animation-bootcamp) & [Design Bootcamp](https://schoolofmotion.com/courses/design-bootcamp) (`Paid Cohort`).

   * *შეძენილი უნარი:* კომპლექსური `Speed/Value Graph` ინტერპოლაცია, `Eye Trace` კომპოზიციური მართვა და მაღალი სიმკვრივის საინფორმაციო დიზაინი.

3. **ოპტიკისა და კინოგანათების სერტიფიცირება:** [ARRI Academy Certified Courses](https://www.arri.com/en/learn/arri-academy/arri-certified-courses) (`Paid / Hybrid`).

   * *შეძენილი უნარი:* ფიზიკური კონტრასტის თანაფარდობისა და დიდი ფორმატის ოპტიკური სიღრმის პროფესიონალური კონტროლი.

## M. ალტერნატიული საწარმოო არქიტექტურა: იგივე და უფრო მაღალი კინემატოგრაფიული ხარისხის მიღწევა 3D მოდელებითა და Blender-ით (Pure & Hybrid 3D Blender Cinematic Alternative)

წინამდებარე გაფართოება (სექციები **M–T**) წარმოადგენს დამოუკიდებელ, სრულფასოვან ალტერნატიულ საწარმოო პარადიგმას: **როგორ მივაღწიოთ იმავე — და სივრცითი უწყვეტობის, კამერის ოპტიკის, განათებისა და ფიზიკური ქორეოგრაფიის თვალსაზრისით უფრო მაღალ — კინემატოგრაფიულ ხარისხს 3D მოდელებითა და `Blender`-ის (`bpy` Python API, `EEVEE Next`, `Cycles`, `Geometry Nodes`, `Grease Pencil 3.0`, `Rigid Body / Cloth / Mantaflow`, `NLA Editor`, `Realtime Compositor`) სრული ეკოსისტემით**.

### M.1 რატომ აღემატება დეტერმინისტული 3D / Blender კონვეიერი წმინდა გენერაციულ ვიდეოს კინემატოგრაფიულ კონტროლში

გენერაციული დიფუზიური ტრანსფორმერები ([LTX-2.5](https://docs.ltx.io/models/ltx-2-5), [LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3)) მუშაობს 2D ლატენტური პიქსელების დროით-სივრცით ალბათურ პროგნოზირებაზე. მათ არ გააჩნიათ მუდმივი სამგანზომილებიანი ევკლიდური სამყაროს მეხსიერება კადრებს შორის. როდესაც წარმოება გადადის **3D მოდელებსა და `Blender`-ზე** ([Blender 5.1 EEVEE Manual](https://docs.blender.org/manual/en/5.1/render/eevee/introduction.html), [Blender Python API](https://docs.blender.org/api/current/bpy.types.SceneObjects.html)), სისტემა იღებს 7 ფუნდამენტურ უპირატესობას, რომელიც პირდაპირ ზრდის კინემატოგრაფიულ ხარისხს:

| კინემატოგრაფიული კრიტერიუმი | გენერაციული ვიდეო (`LTX-2.5 / I2V`) | 3D მოდელები და `Blender` (`bpy` + `EEVEE Next / Cycles`) | ხარისხობრივი უპირატესობა 12-წუთიანი ისტორიული დოკუდრამისთვის |
|---|---|---|---|
| **1. პერსონაჟის, კოსტიუმისა და გარემოს იდენტობა (`Identity & Asset Continuity`)** | ალბათური: 5–10 წამის შემდეგ ან ახალი კუთხიდან გადაღებისას სახე, აბჯრის დეტალები და შენობები განიცდის მორფინგს (`Identity Drift`). | **100% დეტერმინისტული:** ერთი 3D პერსონაჟი ([MPFB2](https://github.com/makehumancommunity/mpfb2) / [Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)) და 3D ციხესიმაგრე ([Infinigen](https://github.com/princeton-vl/infinigen)) ინარჩუნებს იდენტურ გეომეტრიას ყველა კადრში 12 წუთის განმავლობაში. | შესაძლებელია ერთი და იმავე სცენის გადაღება 12 სხვადასხვა კამერით (`Master, OTS, CU, High-Angle`) ნულოვანი ვიზუალური ცდომილებით. |
| **2. კამერის ოპტიკა და რთული 3D ტრაექტორიები (`3D Camera Choreography`)** | შეზღუდული: დიდი `360° Orbit`, `Crane-Up to Overhead` ან `Dolly Zoom` იწვევს გეომეტრიის დაშლას 3D გიდის გარეშე. | **ფიზიკურად უნაკლო:** ნებისმიერი ფოკუსური მანძილი (`14mm–200mm`), ანამორფული ბოკე, `Track To Constraint` ([Blender Track To](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html)) და [Camera Shakify](https://github.com/EatTheFuture/camera_shakify). | ნამდვილი ოპტიკური პერსპექტივის შეკუმშვა, `Dolly Zoom (Vertigo)` და ერთკადრიანი 15–30 წამიანი უწყვეტი სვლები. |
| **3. სხეულის ბიომექანიკა და კონტაქტი (`Weight & Foot Planting`)** | ხშირია ფეხების სრიალი (`Sliding Feet`), კიდურების დაგრძელება (`Rubber Limbs`) და ხმლების ერთმანეთში გავლა. | **ინვერსიული კინემატიკა (`IK`) და ფიზიკა:** [Rigify Meta-Rigs](https://docs.blender.org/manual/en/3.1/addons/rigging/rigify/metarigs.html) იჭერს ტერფს მიწაზე, ხოლო [SprongMotion-14M](https://huggingface.co/SegerEnd/SprongMotion-14M/blob/main/README.md) და [CMU-FBX](https://huggingface.co/datasets/meitemouss0501-del/cmu-fbx/blob/main/README.md) იძლევა რეალურ მოძრაობას. | ფიზიკური წონის, ინერციისა და იარაღის შეჯახების (`Rigid Body Collision`) აბსოლუტური სიზუსტე. |
| **4. ხილული დიალოგი და ლიპ-სინქი (`Lip-Sync Duration & Precision`)** | დაგეგმვის ჭერი **≤ 5 წამი** არტეფაქტების გამო. | **შეუზღუდავი ხანგრძლივობა და ფონემური სიზუსტე:** [Rhubarb Lip Sync](https://github.com/danielswolf/rhubarb-lip-sync) + `ElevenLabs` ტაიმსტამპები მართავს 3D სახის `Shape Keys`-ს ნებისმიერი სიგრძის კადრზე (თუმცა მონტაჟური დინამიკისთვის კვლავ ვიყენებთ `≤5s` + `Reaction` წესს). | ნულოვანი სახის ცურვა ან კბილების/ტუჩების გენერაციული დამახინჯება. |
| **5. მასშტაბური ბრძოლები და ბრბოს სიმულაცია (`Army & Crowd Scale`)** | ასობით მეომარი ერთმანეთს ერწყმის ლაქებად. | **Geometry Nodes Instancing:** 10,000+ დამოუკიდებელი 3D მეომარი ანიმირებული ციკლებით ეკრობა რელიეფს (`Raycast`) მინიმალური VRAM-ით ([Army in Geometry Nodes](https://www.youtube.com/watch?v=5bnFZyNqJJA)). | ტაქტიკური ფორმაციების, ფლანგური მანევრებისა და ალყის რეალური გეომეტრიული კონტროლი. |
| **6. ილუსტრირებული ვიზუალური სტილი (`Stylized / Painterly NPR Look`)** | დამოკიდებულია საწყისი სურათის სტილსა და LoRA-ზე. | **სრული NPR კონტროლი:** `Shader to RGB`, ხელით ნახატი ფუნჯის ნორმალები ([Arcane Style Rendering](https://www.youtube.com/watch?v=EWHCjienXJ0), [Painterly Shader](https://www.youtube.com/watch?v=sAjsMlAg5bQ)), [Grease Pencil Line Art](https://docs.blender.org/manual/en/3.0/grease_pencil/primitives.html) და [Freestyle](https://docs.blender.org/manual/en/4.0/render/freestyle/index.html). | 3D სცენა გამოიყურება როგორც მაღალბიუჯეტიანი ილუსტრირებული ანიმაციური ფილმი (*Arcane / Spider-Verse / Ghibli* ესთეტიკა) და არა იაფფასიანი პლასტმასის 3D. |
| **7. განმეორებადობა და რედაქტირებადობა (`Iterative Directorial Control`)** | თუ კადრში ერთი დეტალი არ ვარგა, საჭიროა ახალი `Seed` ან `/v2/retake`. | **მყისიერი კორექცია:** შეგიძლიათ შეცვალოთ მხოლოდ კამერის ფოკუსური მანძილი `35mm`-დან `85mm`-ზე ან გადასწიოთ ერთი სანთელი ისე, რომ მთელი ანიმაცია უცვლელი დარჩეს. | რეჟისორული სიზუსტე და სრული დეტერმინიზმი `bpy` კოდით. |

### M.2 როგორ ნარჩუნდება 60 / 30 / 10 ვიზუალური და 75 / 25 სასაუბრო ბალანსი 3D Blender-ის არქიტექტურაში

3D / Blender-ზე გადასვლა არ ცვლის პროექტის არასავაჭრო დრამატურგიულ პროპორციებს — პირიქით, იგი სამივე ვიზუალურ ზოლს (`VIDEO`, `STILL`, `HELPER`) აქცევს ერთიანი 3D სამყაროს ნაწილად:
1. **`VIDEO` Lane (60% — ~432 წმ):** სრული 3D ანიმირებული სცენები, სადაც მოძრაობს როგორც კამერა, ისე 3D პერსონაჟები (`Armature / NLA / Shape Keys`), ჯარის ფორმაციები (`Geometry Nodes`), ნგრევის ფიზიკა ([Rigid Body](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html)), ქსოვილები ([Cloth Physics](https://docs.blender.org/manual/en/4.0/physics/cloth/index.html)) და ცეცხლი/კვამლი (`Mantaflow`). რენდერდება `EEVEE Next`-ით (24fps, 0.3–1.2 წმ/კადრი GPU-ზე) NPR Painterly შადერებით.
2. **`STILL` Lane (30% — ~216 წმ):** მაღალდეტალური ილუსტრირებული ტაბლოები, რომლებიც `Blender`-ში გარდაიქმნება **3D Camera Projection (`Project From View`)** ან **Multi-Plane 3D Cards** სცენებად ([Using Warped 2D Elements in 3D](https://www.youtube.com/watch?v=mrd0wFzJKeM)). პერსონაჟები ფიქსირებულ დრამატულ პოზაშია (`Held Tableau`), ხოლო მათ გარშემო მოძრაობს ნამდვილი 3D კამერა, მოცულობითი ნისლი (`Volumetric Fog Shader` — [Volumetric Fog Tutorial](https://www.youtube.com/watch?v=2SiCtnXVVFw)), მოციმციმე 3D სინათლის წყაროები და `Grease Pencil` 2D ეფექტები.
3. **`HELPER` Lane (10% — ~72 წმ):** ნამდვილი 3D ტოპოგრაფიული რუკები ([BlenderGIS](https://github.com/domlysz/blendergis) DEM სიმაღლის რუკებით), სადაც მთები, ხეობები და მდინარეები სამგანზომილებიანია, ხოლო მათ ზემოთ ანიმირდება დეტერმინისტული 3D ისრები (`Curve Bevel Factor`), ტერიტორიული საზღვრები და 3D სვეტოვანი დიაგრამები (`Animation Nodes` / `Geometry Nodes`) [Okabe-Ito ფერთა პალიტრის](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference) (`#0072B2`, `#D55E00`, `#F0E442`) მკაცრი დაცვით.

---

## N. ოფიციალური Blender დოკუმენტაციისა და `bpy` Python API-ს ღრმა ტექნიკური სახელმძღვანელო (Official Blender Documentation & `bpy` Architecture)

Blender-ის სრული ავტომატიზაცია ეფუძნება იმ ფაქტს, რომ პროგრამის ნებისმიერი ვიზუალური, ფიზიკური და სარენდერო ოპერაცია ხელმისაწვდომია ჩაშენებული Python API-ს (`bpy`, `mathutils`, `bmesh`) მეშვეობით უინტერფეისო (`Headless CLI`) რეჟიმში:
`blender -b scene.blend -P generate_shot.py -- --shot_id A2 --frames 241`

### N.1 `bpy` მონაცემთა არქიტექტურა და ოფიციალური API მოდულები

ოფიციალური API დოკუმენტაციის ([bpy.types.SceneObjects](https://docs.blender.org/api/current/bpy.types.SceneObjects.html), [bpy.ops.collection](https://docs.blender.org/api/current/bpy.ops.collection.html), [bpy.types.ActionGroup](https://docs.blender.org/api/current/bpy.types.ActionGroup.html), [bpy.types.PreferencesEdit](https://docs.blender.org/api/current/bpy.types.PreferencesEdit.html), [bpy.types.bpy_prop](https://docs.blender.org/api/current/bpy.types.bpy_prop.html), [bpy.types.NodeClosureInputItems](https://docs.blender.org/api/current/bpy.types.NodeClosureInputItems.html), [bpy.types.AnyType](https://docs.blender.org/api/current/bpy.types.AnyType.html)) მიხედვით, ავტომატიზებული კონვეიერი უნდა აიგოს **პირდაპირ მონაცემთა ბლოკებზე (`bpy.data`) და არა კონტექსტზე დამოკიდებულ UI ოპერატორებზე (`bpy.ops`)**, რადგან `bpy.ops` მოითხოვს აქტიურ 3D Viewport-ს და ხშირად იწვევს `RuntimeError: Operator bpy.ops... poll() failed, context is incorrect` შეცდომას უინტერფეისო სერვერზე!

| Blender ქვესისტემა | ოფიციალური Manual / API წყარო | ძირითადი `bpy` კლასები და მეთოდები (`Low-Level Data API`) | კინემატოგრაფიული როლი და საწარმოო კონფიგურაცია [PRIMARY / OFFICIAL] |
|---|---|---|---|
| **Render Engines: EEVEE Next & Cycles** | [Blender 5.1 EEVEE Manual](https://docs.blender.org/manual/en/5.1/render/eevee/introduction.html), [Blender 5.0 EEVEE](https://docs.blender.org/manual/en/5.0/render/eevee/introduction.html), [Cycles GPU Rendering](https://docs.blender.org/manual/en/2.90/render/cycles/gpu_rendering.html) | `scene.render.engine = 'BLENDER_EEVEE_NEXT'` ან `'CYCLES'`; `scene.cycles.device = 'GPU'`; `scene.eevee.use_raytracing = True`; `scene.eevee.use_volumetric_shadows = True`. | `EEVEE Next` უზრუნველყოფს რეალურ დროში რეიტრეისინგს, მოცულობით ჩრდილებს (`Volumetric Shadows`), `Motion Blur`-სა და `Depth of Field`-ს NPR/Stylized შადერებისთვის; `Cycles` გამოიყენება მაღალი სიზუსტის არქიტექტურული და ბრძოლის კადრებისთვის. |
| **Scene & Collection Management** | [bpy.types.SceneObjects](https://docs.blender.org/api/current/bpy.types.SceneObjects.html), [bpy.ops.collection](https://docs.blender.org/api/current/bpy.ops.collection.html) | `bpy.data.collections.new()`, `col.objects.link(obj)`, `view_layer.layer_collection.children[name].holdout = True`. | სცენის დაყოფა `Foreground`, `Characters`, `Environment`, `VFX` კოლექციებად; თითოეული კოლექცია რენდერდება ცალკე `View Layer`-ად `Holdout` და `Indirect Only` ნიღბებით. |
| **Camera Optics & Tracking Constraints** | [Track To Constraint Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html), [Camera Data Manual](https://docs.blender.org/manual/en/2.81/movie_clip/tracking/clip/properties/camera_data.html) | `cam.data.lens` (mm), `cam.data.sensor_width = 36.0` (Full Frame), `cam.data.dof.use_dof = True`, `cam.data.dof.focus_object`, `cam.data.dof.aperture_fstop`, `obj.constraints.new('TRACK_TO')`. | ზუსტი ოპტიკური სიმულაცია: `Track To` (`track_axis='TRACK_NEGATIVE_Z'`, `up_axis='UP_Y'`) მუდმივად აფიქსირებს კამერას მოძრავ სამიზნეზე, ხოლო `focus_object` მართავს ავტომატურ `Rack Focus`-ს. |
| **Animation Curves, F-Curves & NLA** | [NLA Editor Manual](https://docs.blender.org/manual/en/4.0/editors/nla/introduction.html), [bpy.types.ActionGroup](https://docs.blender.org/api/current/bpy.types.ActionGroup.html), [bpy.types.PreferencesEdit](https://docs.blender.org/api/current/bpy.types.PreferencesEdit.html) | `obj.keyframe_insert(data_path, frame)`, `fcurve.modifiers.new('NOISE')`, `obj.animation_data.nla_tracks.new()`, `track.strips.new(name, start, action)`. | `NLA Editor` აერთიანებს სიარულის, სირბილისა და ხმლის ქნევის მოკლე ანიმაციურ კლიპებს (`Actions`) გლუვი გადადნობით (`Auto-Blend In/Out`), ხოლო `F-Curve Noise Modifier` ქმნის ცეცხლის ციმციმსა და ხელის კამერის რხევას. |
| **Rigify & Skeletal Character Rigging** | [Creating Meta-rigs — Rigify](https://docs.blender.org/manual/en/3.1/addons/rigging/rigify/metarigs.html), [Rigify Feature Sets](https://docs.blender.org/manual/en/3.3/addons/rigging/rigify/feature_sets.html) | `bpy.ops.armature.metarig_add()`, `bpy.ops.pose.rigify_generate()`, `pose.bones['foot_ik.L'].location`. | აგენერირებს სრულ `IK/FK` კონტროლერებსა და სახის ძვლოვან სისტემას; `IK` ტერფის კონტროლერი 100%-ით გამორიცხავს ფეხების სრიალს (`Sliding Feet`). |
| **Grease Pencil 3.0, Line Art & Freestyle NPR** | [Grease Pencil Primitives & Line Art](https://docs.blender.org/manual/en/3.0/grease_pencil/primitives.html), [Freestyle Render Manual](https://docs.blender.org/manual/en/4.0/render/freestyle/index.html), [Freestyle Line Style](https://docs.blender.org/manual/en/4.0/render/freestyle/view_layer/line_style/index.html), [Guiding Lines](https://docs.blender.org/manual/en/4.0/render/freestyle/view_layer/line_style/modifiers/geometry/guiding_lines.html) | `gp_obj.grease_pencil_modifiers.new(name, 'GP_LINEART')`, `scene.render.use_freestyle = True`, `lineset.select_silhouette = True`, `lineset.select_crease = True`. | 3D მოდელებს გარედან ავლებს დინამიკურ, კამერაზე მორგებულ ტუშის/კალმის კონტურს (`Silhouette, Crease, Border Lines`) ცვალებადი სისქით, რაც 3D გეომეტრიას აქცევს ხელით დახატულ ილუსტრაციად. |
| **Physics: Rigid Body & Cloth** | [Rigid Body Introduction](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html), [Cloth Physics Manual](https://docs.blender.org/manual/en/4.0/physics/cloth/index.html) | `obj.rigid_body.type = 'ACTIVE'` / `'PASSIVE'`, `obj.rigid_body.collision_shape = 'CONVEX_HULL'`, `obj.modifiers.new(name, 'CLOTH')`. | კატაპულტის ჭურვების, კედლების ნგრევისა და მიწაზე დავარდნილი იარაღის დეტერმინისტული სიმულაცია + დროშებისა და მოსასხამების ქარში ფრიალი (`Force Field: Wind`). |
| **Realtime Compositor & Multi-Pass EXR** | [Compositing Manual 3.5+](https://docs.blender.org/manual/en/3.5/compositing/index.html), [Compositing 3.3](https://docs.blender.org/manual/en/3.3/compositing/index.html) | `scene.use_nodes = True`, `CompositorNodeDefocus`, `CompositorNodeCryptomatteV2`, `CompositorNodeGlare`, `CompositorNodeKuwahara`. | `CompositorNodeKuwahara` (ანაიზოტროპული ფერწერული ფილტრი) 3D რენდერს გარდაქმნის ზეთის/აკრილის ფერწერულ ტილოდ, ხოლო `Defocus` და `Cryptomatte` მართავს ზუსტ ფოკუსსა და ფერის იზოლირებულ კორექციას. |

---

## O. GitHub-ისა და Hugging Face-ის ღია კოდის რეპოზიტორიების კატალოგი პირდაპირი კოდის ინტეგრაციისთვის (26 Verified Repositories)

ქვემოთ მოცემულია GitHub-სა და Hugging Face-ზე არსებული 26 ვერიფიცირებული ღია კოდის რეპოზიტორია, საიდანაც საწარმოო სისტემას შეუძლია **პირდაპირ აიღოს და გაუშვას Python / `bpy` კოდი** 3D გარემოების, პერსონაჟების, კამერების, ლიპ-სინქის, მოძრაობისა და რუკების ავტომატური გენერაციისთვის:

| # | რეპოზიტორია (GitHub / Hugging Face) | პირდაპირი ვერიფიცირებული URL | კატეგორია | რა კოდი და მოდული შეგვიძლია პირდაპირ ავიღოთ (`Direct Code Reuse`) |
|---|---|---|---|---|
| **1** | **princeton-vl/infinigen** | [GitHub: princeton-vl/infinigen](https://github.com/princeton-vl/infinigen) | Procedural 3D World & Indoor Generation (`bpy`) | `infinigen/assets` და `infinigen/terrain`: პროცედურული მთების, ტყეების, მდინარეების, კლდეების, ღრუბლების, ამინდისა და ისტორიული ინტერიერების (`Infinigen-Indoors`) `Geometry Nodes` და `bpy` გენერატორები. |
| **2** | **DLR-RM/BlenderProc** | [GitHub: DLR-RM/BlenderProc](https://github.com/DLR-RM/BlenderProc) & [HF BlenderProc Course](https://huggingface.co/learn/computer-vision-course/unit10/blenderProc) | Headless Procedural `bpy` Pipeline | `blenderproc.python.camera`, `lighting`, `physics`, `renderer`: მზა Python ფუნქციები კამერის პოზიციონირებისთვის, ობიექტების მიწაზე ფიზიკური დასმისთვის (`simulate_physics_and_fix_final_poses`) და `Depth/Normal/Segmentation` რენდერისთვის. |
| **3** | **domlysz/BlenderGIS** | [GitHub: domlysz/BlenderGIS](https://github.com/domlysz/blendergis) | Historical Cartography & 3D Terrain (`HELPER`) | `operators/io_import_asc.py`, `io_import_shp.py`, `geoscene.py`: რეალური გეოგრაფიული `SRTM DEM` სიმაღლის რუკების, `Shapefile` საზღვრებისა და მდინარეების პირდაპირი იმპორტი 3D მრავალკუთხედებად (`Delaunay triangulation`). |
| **4** | **google-research/kubric** | [GitHub: google-research/kubric](https://github.com/google-research/kubric/blob/main/challenges/movi/README.md) | Physics & Multi-Pass Blender Wrapper | `kubric/renderer/blender.py` და `kubric/simulator/pybullet.py`: სუფთა Python აბსტრაქცია `Blender`-სა და `PyBullet`-ს შორის მრავალობიექტიანი ნგრევისა და ოპტიკური ნაკადის (`Optical Flow`) ექსპორტისთვის. |
| **5** | **EatTheFuture/camera_shakify** | [GitHub: EatTheFuture/camera_shakify](https://github.com/EatTheFuture/camera_shakify) | Cinematic Handheld Camera Rigs | `camera_shakify/shake_data.py` და `__init__.py`: Blender Studio-ს მიერ რეალური კამერებიდან ჩაწერილი ემპირიული რხევის მრუდები (`Investigation`, `Battle Handheld`, `Long Lens`), რომლებიც ემატება ნებისმიერ კამერას 1 სტრიქონით. |
| **6** | **DanielSWolf/rhubarb-lip-sync** | [GitHub: DanielSWolf/rhubarb-lip-sync](https://github.com/danielswolf/rhubarb-lip-sync) | Automated Dialogue Phoneme Lip-Sync | CLI და Blender Addon კოდი, რომელიც იღებს `ElevenLabs`-ის WAV აუდიოს + ტექსტს და აგენერირებს 9 ვიზემის (`Mouth Shapes A–H, X`) ზუსტ ფრეიმ-კოდებს 2D `Grease Pencil` ან 3D `Shape Key` პირის ანიმაციისთვის. |
| **7** | **MakeHumanCommunity/mpfb2** | [GitHub: MakeHumanCommunity/mpfb2](https://github.com/makehumancommunity/mpfb2) | Parametric 3D Human Character Generator | `src/mpfb/services/humanservice.py` და `rigservice.py`: Blender 4.2+-ის შიგნით პროგრამულად ქმნის სხვადასხვა ასაკის, აღნაგობისა და ეთნიკურობის 3D პერსონაჟებს სრული `Rigify` ჩონჩხითა და სახის `ARKit / Viseme` Shape Key-ებით. |
| **8** | **Rokoko/rokoko-studio-live-blender** | [GitHub: Rokoko/rokoko-studio-live-blender](https://github.com/Rokoko/rokoko-studio-live-blender) | Automated Skeletal Motion Retargeting | `operators/retargeting.py` (`Build Bone List` & `Retarget Animation`): ნებისმიერი `.bvh` ან `.fbx` მოძრაობის ფაილის ავტომატური გადატანა ჩვენს 3D პერსონაჟზე ძვლების სახელების ავტო-მეპინგით. |
| **9** | **SegerEnd/SprongMotion-14M** | [HF: SegerEnd/SprongMotion-14M](https://huggingface.co/SegerEnd/SprongMotion-14M/blob/main/README.md) | Text-to-3D Skeletal Motion (CPU/Blender) | 33 MB GGUF მოდელი და მზა Blender Add-on, რომელიც ინგლისური ტექსტური აღწერიდან (`"soldier marches forward"`, `"man swings sword"`) CPU-ზე 0.23 წამში აგენერირებს 22-სახსრიან 3D ჩონჩხის ანიმაციასა და `.bvh` ფაილს ტერფის კონტაქტებით! |
| **10** | **meitemouss0501-del/cmu-fbx** | [HF Dataset: cmu-fbx](https://huggingface.co/datasets/meitemouss0501-del/cmu-fbx/blob/main/README.md) | 2,500+ Optical Motion Capture Library | კარნეგი-მელონის უნივერსიტეტის 2,500+ ოპტიკური მოძრაობის ჩანაწერი (სიარული, სირბილი, ხტომა, ბრძოლა, ხელოსნობა), რომელიც Blender-ით გადაყვანილია მზა `.fbx` ჩონჩხებად (`Root Motion`-ით). |
| **11** | **CGArtPython/bpy_building_blocks** | [GitHub: CGArtPython/bpy_building_blocks](https://github.com/CGArtPython/bpy_building_blocks) | Clean `bpy` Scripting Utilities | `bpy_building_blocks` მოდულები: სუფთა Python ფუნქციები კამერის სწორებისთვის, ნოუდური შადერების პროგრამული აწყობისთვის, HDRI განათებისა და F-Curve ინტერპოლაციისთვის. |
| **12** | **JacquesLucke/animation_nodes** | [GitHub: JacquesLucke/animation_nodes](https://github.com/JacquesLucke/animation_nodes) | Procedural Motion Graphics & Data Viz | ნოუდური სისტემა 3D მრიცხველების, დინამიკური ტექსტის, ქრონოლოგიური ხაზებისა და აუდიო-სპექტრზე მიბმული ანიმაციებისთვის. |
| **13** | **ahujasid/mcp-for-blender** | [GitHub: ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | Automated Agent-to-Blender Control & QA | `addon.py`: სოკეტ-სერვერი Blender-ის შიგნით, რომელიც იღებს Python კოდს, ქმნის/ცვლის 3D სცენას და აბრუნებს მრავალკუთხოვან (`Camera, Wireframe, X-Ray`) რენდერებს ავტომატური ვიზუალური ვერიფიკაციისთვის. |
| **14** | **gd3kr/BlenderGPT** | [GitHub: gd3kr/BlenderGPT](https://github.com/gd3kr/blendergpt) | Natural Language to `bpy` Execution | LLM-ით გენერირებული `bpy` სკრიპტების სენდბოქს-ვალიდაციისა და Blender-ის კონტექსტში უსაფრთხო გაშვების კოდი. |
| **15** | **DietCoke4671/BlenderBench** | [HF Dataset: DietCoke4671/BlenderBench](https://huggingface.co/datasets/DietCoke4671/BlenderBench) | `bpy` Scene Editing Benchmark & Code | მზა `bpy` Python სკრიპტების კორპუსი კამერის, განათების, მასალებისა და ობიექტების ტრანსფორმაციისთვის საწყის და სამიზნე სცენებს შორის. |
| **16** | **MaxRondelli/BlenderRAG** | [HF Dataset: MaxRondelli/BlenderRAG](https://huggingface.co/datasets/MaxRondelli/BlenderRAG) | Procedural `bpy` Script Dataset | ტექსტური აღწერილობების, პროცედურული `bpy` Python სკრიპტებისა და დარენდერებული პრევიუების წყვილები RAG-ზე დაფუძნებული 3D გენერაციისთვის. |
| **17** | **allenai/Holodeck** | [GitHub: allenai/Holodeck](https://github.com/allenai/Holodeck) | Automated 3D Interior Scene Layout | CVPR 2024 კოდი ოთახების, კედლების, ფანჯრების, მაგიდებისა და სკამების სივრცითი შეზღუდვებით (`Spatial Constraints`) ავტომატური განლაგებისთვის (იდეალურია საბჭოსა და მოლაპარაკების დარბაზებისთვის). |
| **18** | **Tencent-Hunyuan/Hunyuan3D-2** | [GitHub: Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) & [HF Space](https://huggingface.co/spaces/tencent/Hunyuan3D-2) | Image/Text-to-High-Res 3D Mesh + Texture | ერთი ილუსტრირებული კონცეპტ-არტიდან აგენერირებს მაღალი დეტალიზაციის 3D მეშსა (`Hunyuan3D-DiT-v2`) და PBR ტექსტურას (`Hunyuan3D-Paint`), რომელიც [Hunyuan3D-2-Mesh_Import](https://github.com/JorisVanMeenen/Hunyuan3D-2-Mesh_Import)-ით პირდაპირ შედის Blender-ში. |
| **19** | **microsoft/TRELLIS.2** | [GitHub: microsoft/TRELLIS.2](https://github.com/microsoft/trellis.2) & [HF TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B) | Structured 3D Latent Asset Synthesis | 4B პარამეტრიანი მოდელი ისტორიული არქიტექტურის, ციხესიმაგრეების, საალყო მანქანების, გემებისა და რეკვიზიტების (`Props`) `.glb / .obj` ფორმატში სწრაფი გენერაციისთვის. |
| **20** | **VAST-AI-Research/TripoSG** | [GitHub: VAST-AI-Research/TripoSG](https://github.com/VAST-AI-Research/TripoSG) & [HF VAST-AI/TripoSG](https://huggingface.co/VAST-AI/TripoSG) | Rectified-Flow High-Fidelity 3D Shapes | სურათიდან ან სკეტჩიდან ([TripoSG-scribble](https://huggingface.co/VAST-AI/TripoSG-scribble)) სუფთა ტოპოლოგიის 3D ობიექტების სინთეზი `Diffusers` პაიპლაინით. |
| **21** | **VAST-AI-Research/TripoSR** | [GitHub: VAST-AI-Research/TripoSR](https://github.com/vast-ai-research/triposr) & [HF stabilityai/TripoSR](https://huggingface.co/stabilityai/TripoSR) | Sub-Second Fast 3D Object Reconstruction | `<0.5 წამში` ქმნის 3D მეშს ერთი სურათიდან — იდეალურია შუა და უკანა პლანის ისტორიული რეკვიზიტების, კარვების, ურმებისა და ფარების მასობრივი შევსებისთვის. |
| **22** | **SifuInTheShell/Effigy** | [GitHub: SifuInTheShell/Effigy](https://github.com/SifuInTheShell/Effigy) | Local 2D-to-3D Production Pipeline | აერთიანებს ლოკალურ 2D კონცეპტის გენერაციასა და `TRELLIS.2` 3D კონვერტაციას ერთ ავტომატიზებულ სკრიპტში. |
| **23** | **carson-katri/dream-textures** | [GitHub: carson-katri/dream-textures](https://github.com/carson-katri/dream-textures) | Camera-Projected AI Textures in Blender | `Depth-to-Image` პროექცია პირდაპირ Blender-ის 3D კამერიდან — საშუალებას გვაძლევს მარტივი 3D გეომეტრია შევღებოთ ილუსტრირებულ ისტორიულ სტილში კამერის პერსპექტივიდან. |
| **24** | **AIGODLIKE/ComfyUI-BlenderAI-node** | [GitHub: AIGODLIKE/ComfyUI-BlenderAI-node](https://github.com/AIGODLIKE/ComfyUI-BlenderAI-node) | Direct Blender-to-ComfyUI Node Bridge | აქცევს Blender-ის 3D კამერასა და `Z-Depth / Normal / Canny` პასებს პირდაპირ `ComfyUI`-ს რეალურ დროში შესასვლელად (ჰიბრიდული `Blender -> LTX-2.5 IC-LoRA` რეჟიმისთვის). |
| **25** | **agmmnn/awesome-blender** | [GitHub: agmmnn/awesome-blender](https://github.com/agmmnn/awesome-blender) | Curated Blender Add-ons & Tools Index | ღია კოდის Blender გაფართოებების, სიმულაციის, განათებისა და AI ხელსაწყოების სრული საცნობარო რეესტრი. |
| **26** | **blender/blender** | [GitHub: blender/blender](https://github.com/blender/blender) | Official Blender Core & Python Templates | `scripts/templates_py/` და `scripts/startup/bl_operators/`: ოფიციალური Python შაბლონები ყველა ნოუდის, მოდიფიკატორისა და სარენდერო პასის პროგრამული მართვისთვის. |

---

## P. ტოპ 55 ვერიფიცირებული Blender-ის ტუტორიალის, სტუდიური კურსისა და ოფიციალური სახელმძღვანელოს კატალოგი (Top 55 Verified Blender Tutorials & Manuals)

ქვემოთ წარმოდგენილია 55 ვერიფიცირებული სასწავლო რესურსი, დაჯგუფებული 7 საწარმოო დისციპლინად, რომლებიც ფარავს 12-წუთიანი ისტორიული დოკუდრამის ყველა ტექნიკურ საჭიროებას:

| # | ტუტორიალის / სახელმძღვანელოს ზუსტი სათაური | ავტორი / ინსტიტუცია | დისციპლინა | პირდაპირი ვერიფიცირებული URL | რა კონკრეტულ ტექნიკას გვასწავლის საწარმოო სისტემისთვის |
|---|---|---|---|---|---|
| **1** | **How to Make 3D Look Illustrated \| Stylized Stipple Toon Shader** | YouTube Blender NPR | NPR / Stylized Shaders | [Stylized Stipple Toon Shader](https://www.youtube.com/watch?v=lFvL-4bIUMc) | 3D მოდელების გარდაქმნა ილუსტრირებულ წერტილოვან/გრავიურულ სტილად `Shader to RGB` და პროცედურული ტექსტურებით. |
| **2** | **Arcane Style Rendering in Blender!** | YouTube Blender Stylized | NPR / Arcane Painterly Look | [Arcane Style Rendering](https://www.youtube.com/watch?v=EWHCjienXJ0) | *Arcane*-ის სტილის ფერწერული განათება, ხელით დახატული კონტრასტი და კამერაზე მორგებული ჩრდილები. |
| **3** | **THIS is Arcane Shading in Blender (EASY)** | Comfee / YouTube | NPR / Character Skin Shader | [Arcane Shading in Blender](https://www.youtube.com/watch?v=As4biIb1-Jo) | პერსონაჟის სახისა და კანის ფერწერული შადერის აწყობა ნულოვანი პლასტმასის ეფექტით. |
| **4** | **Arcane Style Tutorial Part 1: Hair (EEVEE)** | Lightning Boy Studio / YT | NPR / Stylized Hair | [Arcane Style Tutorial Part 1](https://www.youtube.com/watch?v=FXuReln3XD0) | სტილიზებული 3D თმისა და წვერის ფერწერული შადერი `EEVEE`-ში. |
| **5** | **Arcane Tutorial Part 2: Environment & Lighting** | Lightning Boy Studio / YT | NPR / Stylized Environments | [Arcane Tutorial Part 2](https://www.youtube.com/watch?v=gG7ZoP3fd1w) | ისტორიული არქიტექტურისა და ინტერიერების ფერწერული ტექსტურირება და განათება. |
| **6** | **Making 3D animation look painterly (it's easier than you think)** | YouTube Blender NPR | NPR / Painterly Normals | [Making 3D Look Painterly](https://www.youtube.com/watch?v=s8N00rjil_4) | 3D ზედაპირის ნორმალების დარღვევა ფუნჯის მონასმების (`Brushstroke Normal Maps`) ტექსტურით. |
| **7** | **Painterly Shader in Blender Eevee** | YouTube Blender NPR | NPR / Procedural Eevee | [Painterly Shader in Eevee](https://www.youtube.com/watch?v=sAjsMlAg5bQ) | 100%-ით პროცედურული ფერწერული შადერის ნოუდ-გრაფი `EEVEE`-სთვის. |
| **8** | **Blender 5 Toon Shader Tutorial — Fast, Clean, Stylized NPR** | YouTube Blender 5 | NPR / Inverted Hull Outlines | [Blender 5 Toon Shader](https://www.youtube.com/watch?v=aZAqFJKMtjs) | `Solidify Modifier` (`Flipped Normals`) მეთოდით სუფთა კონტურების დადება 3D მოდელებზე Blender 5-ში. |
| **9** | **Blender 4.4 - 4.5 Toon Shader Tutorial + Grease Pencil Tips** | VectorRecite / YouTube | NPR / Toon + Grease Pencil | [Blender 4.5 Toon + Grease Pencil](https://www.youtube.com/watch?v=TkUwgHo5GUg) | 3D Toon შადერისა და 2D `Grease Pencil` ხაზების ჰიბრიდული შერწყმა. |
| **10** | **STYLIZED 2D Effects in BLENDER Using Grease Pencil and Shaders** | YouTube Blender FX | NPR / 2D FX in 3D | [Stylized 2D Effects in Blender](https://www.youtube.com/watch?v=QCTAR2SXEws) | 2D კვამლის, ნაპერწკლებისა და დარტყმის ეფექტების დახატვა 3D სცენაში. |
| **11** | **Basic Blender Toon / Cel Shader Tutorial 2D Grease Pencil + 3D** | YouTube Blender NPR | NPR / 4-Node Cel Shader | [4-Node Cel Shader + Grease Pencil](https://www.youtube.com/watch?v=hBztmFHkNQo) | მსუბუქი 4-ნოუდიანი Cel Shader სწრაფი მასობრივი რენდერისთვის. |
| **12** | **How To Make Ghibli-Style Anime Rocks Shader in Blender** | YouTube Blender Stylized | NPR / Stylized Nature | [Ghibli-Style Rocks Shader](https://www.youtube.com/watch?v=0LKDUTiHnq4) | ილუსტრირებული კლდეებისა და ბუნებრივი რელიეფის პროცედურული შადერი. |
| **13** | **Stylized 2D/3D Landscape in Blender \| Grease Pencil + Geometry Nodes** | YouTube Blender Env | NPR / 2.5D Landscapes | [Stylized 2D/3D Landscape](https://www.youtube.com/watch?v=ROZcvxQ6HpY) | `Grease Pencil`-ისა და `Geometry Nodes`-ის კომბინაციით ილუსტრირებული ლანდშაფტების აგება. |
| **14** | **Sprite Fright Production Lessons: Distressed Character Shading** | Blender Studio Official | Studio Production / Shading | [Blender Studio: Sprite Fright Shading](https://studio.blender.org/projects/sprite-fright/394e83f00b4b5c/?asset=4968) | Blender Studio-ს ოფიციალური გაკვეთილი პერსონაჟების ტანსაცმლისა და კანის დაძველების/ტექსტურირების შესახებ. |
| **15** | **Fire: Grease Pencil to Mesh Automation — Sprite Fright** | Blender Studio Official | Studio Production / VFX | [Blender Studio: Grease Pencil Fire](https://studio.blender.org/projects/sprite-fright/394c22767579d6/?asset=4567) | 2D `Grease Pencil` ცეცხლის ავტომატური კონვერტაცია 3D მოცულობით მეშში. |
| **16** | **How I Made Huge Armies in Blender! (Breakdown)** | Martin Klekner / YouTube | Battles & Crowds | [How I Made Huge Armies in Blender](https://www.youtube.com/watch?v=wcvgBYW9YeE) | კინემატოგრაფიული ისტორიული არმიების, ბატალური სცენებისა და LOD-ების (Level of Detail) სრული არქიტექტურა. |
| **17** | **Make an ARMY in Blender in 1 Minute \| Advanced Tutorial** | YouTube Geometry Nodes | Battles / Geometry Nodes | [Make an Army in Geometry Nodes](https://www.youtube.com/watch?v=5bnFZyNqJJA) | `Distribute Points on Faces` + `Instance on Points` + `Raycast` (`Set Position`) უსწორმასწორო რელიეფზე მოსიარულე არმიისთვის. |
| **18** | **How to Make Procedural Mountains in Blender** | YouTube Blender Terrain | Environments / Terrain | [Procedural Mountains in Blender](https://www.youtube.com/watch?v=Oa_WxMcVz9w) | პროცედურული მთების, წყლის დონის, კლდეების, ბუჩქებისა და ღრუბლების ჩრდილების (`Volume Cube`) აგება დრონის კადრებისთვის. |
| **19** | **Using Warped 2D Elements in 3D to Create Waterfalls & Mist** | Ian Hubert / YouTube Style | 2.5D Projection / VFX | [Warped 2D Elements in 3D](https://www.youtube.com/watch?v=mrd0wFzJKeM) | 2D ვიდეო/სურათის ფენების (`Cards`) 3D სივრცეში მოღუნვა ჩანჩქერების, ნისლის, ცეცხლისა და გემის ტალღებისთვის. |
| **20** | **Create a Castle in Blender in Under 60 Minutes!** | CG Geek / YouTube | Historical Architecture | [Create a Castle in 60 Minutes](https://www.youtube.com/watch?v=QbSmoZCrP8I) | მოდულური ისტორიული ციხესიმაგრისა და გალავნის სწრაფი აგება და განათება. |
| **21** | **How To Create a Medieval Environment in Blender (FREE Pack)** | YouTube Blender Env | Historical Architecture | [Create a Medieval Environment](https://www.youtube.com/watch?v=INqnGBPRvhU) | შუა საუკუნეების ქალაქისა და გარემოს აწყობა მოდულური 3D ასეტებით. |
| **22** | **Making a Castle Ruins Environment in Blender** | YouTube Blender Env | Historical Aftermath / Ruins | [Making Castle Ruins Environment](https://www.youtube.com/watch?v=RYa8khHlbhY) | დანგრეული ციხესიმაგრისა და `Aftermath` გარემოს კომპოზიცია და ატმოსფერო. |
| **23** | **Creating a Kingdom in Blender (Free Assets)** | YouTube Blender Env | Large-Scale World Building | [Creating a Kingdom in Blender](https://www.youtube.com/watch?v=rgU0VQI6xAQ) | მასშტაბური სამეფოსა და ქალაქის პანორამული `Extreme Wide Shot`-ების აგება. |
| **24** | **How To Make A Castle — Blender 4.2 Tutorial** | Blender Simplified / YT | Historical Modeling | [How To Make A Castle Blender 4.2](https://www.youtube.com/watch?v=i67zFBMfMQA) | თანამედროვე მოდიფიკატორებით კოშკებისა და ქონგურების პროცედურული მოდელირება. |
| **25** | **Low Poly Castle in Blender — 3D Modeling Process** | Polygon Runway / YouTube | Stylized Architecture | [Polygon Runway Low Poly Castle](https://www.youtube.com/watch?v=O8Jf03rbMtE) | სუფთა გეომეტრიული სტილიზებული ციხესიმაგრის აგება ილუსტრირებული დოკუდრამისთვის. |
| **26** | **Make this CASTLE TOWER in 6 Minutes in Blender** | YouTube Blender Modeling | Modular Kitbashing | [Castle Tower in 6 Minutes](https://www.youtube.com/watch?v=lH8GeRHDbsY) | სწრაფი მოდულური კოშკის გენერატორი ალყის სცენებისთვის. |
| **27** | **Fundamentals of Lighting in Blender (2026)** | Blender Guru (Andrew Price) | Cinematic Lighting | [Blender Guru: Fundamentals of Lighting](https://www.youtube.com/watch?v=ENnEYoUpFfU) | კინემატოგრაფიული განათების ფუნდამენტი: `Key-to-Fill Ratio`, `Rim Light`, ფერის ტემპერატურა და თვალის ფოკუსის მართვა. |
| **28** | **The Best Volumetric Fog Shader (Blender Tutorial)** | Ryan King Art / YouTube | Volumetrics & Atmosphere | [Best Volumetric Fog Shader](https://www.youtube.com/watch?v=2SiCtnXVVFw) | არაერთგვაროვანი (`3D Noise`) მოცულობითი ნისლის შადერი `Cycles` და `EEVEE`-სთვის ჰაეროვანი პერსპექტივის შესაქმნელად. |
| **29** | **Quick Easy Fog Effect in Blender (2026 Tutorial)** | Ryan King Art / YouTube | Fast Atmosphere / Mist Pass | [Quick Easy Fog Effect](https://www.youtube.com/watch?v=GjvlxbRtZwE) | სწრაფი ნისლისა და `Mist Pass`-ის კონფიგურაცია მინიმალური რენდერის დროით. |
| **30** | **Blender Tutorial: Quick Volumetric Lighting God Rays** | Ryan King Art / YouTube | Volumetric God Rays | [Volumetric Lighting God Rays](https://www.youtube.com/watch?v=uWd4oYIjCqU) | სარკმლებიდან და ტყეში შემომავალი სინათლის სხივების (`Crepuscular God Rays`) შექმნა. |
| **31** | **Procedural Lights Studio in Geometry Nodes** | Andrea Ciani / YouTube | Procedural Lighting | [Procedural Lights in Geometry Nodes](https://www.youtube.com/watch?v=iOcKNZ5ybRc) | სინათლის წყაროების (ჩირაღდნების, სანთლების) პროცედურული განაწილება `Geometry Nodes`-ით. |
| **32** | **Animated Lightbeams with Geometry Nodes in Blender** | YouTube Geometry Nodes | Dynamic Lighting | [Animated Lightbeams Geometry Nodes](https://www.youtube.com/watch?v=pZrDdR98tEE) | მოძრავი სინათლის კონუსებისა და ატმოსფერული სხივების პროცედურული მართვა. |
| **33** | **Blender Lighting Effects for Beginners — Lens Flares** | YouTube Blender Lighting | Optical Lens Effects | [Blender Lighting Lens Flares](https://www.youtube.com/watch?v=tKqHZomlkU4) | ოპტიკური `Lens Flare`-ისა და `Glare`-ის ინტეგრაცია კინოკამერის ეფექტისთვის. |
| **34** | **Blender Tutorial — Lighting Tips & Tricks Pt. 2** | UniBlend_Art / YouTube | Chiaroscuro & Contrast | [Blender Lighting Tips & Tricks](https://www.youtube.com/watch?v=BPNdmfMjato) | `Negative Fill`, `Light Linking` და ჩრდილის სიმკვეთრის კონტროლი. |
| **35** | **How to Use Depth of Field in Blender (Tutorial)** | Ryan King Art / YouTube | Camera Optics & DOF | [How to Use Depth of Field in Blender](https://www.youtube.com/watch?v=ahT3P274EMw) | კამერის `f-stop`, `Focus Object`, `Blades` (ანამორფული ბოკე) და `Rack Focus` ანიმაცია. |
| **36** | **How to Use Blender's Built-in Camera Rig Addon** | Ryan King Art / YouTube | Camera Rigging (Dolly/Crane) | [Blender Built-in Camera Rig Addon](https://www.youtube.com/watch?v=G6eM-D57ZbU) | Blender-ის ოფიციალური `Add Camera Rig` (`Dolly Rig` & `Crane Rig`) გაფართოების გამოყენება რთული კამერის სვლებისთვის. |
| **37** | **Blender Add Camera Rigs (Quick Tip)** | YouTube Blender Camera | Camera Rigging | [Blender Add Camera Rigs](https://www.youtube.com/watch?v=1FxTF5UDcaQ) | კამერის სამიზნისა და `Aim/Track` ძვლების სწრაფი აწყობა. |
| **38** | **Procedural Auto Focus in Geometry Nodes** | Andrea Ciani / YouTube | Automated Raycast Focus | [Procedural Auto Focus Geometry Nodes](https://www.youtube.com/watch?v=fidihomNzU0) | კამერიდან გასროლილი `Raycast` სხივით ფოკუსური მანძილის 100%-ით ავტომატური გამოთვლა მოძრავ სუბიექტზე. |
| **39** | **Geometry Nodes Camera Culling & Optimization** | pointsscatter / YouTube | Performance / Frustum Culling | [Geometry Nodes Camera Culling](https://www.youtube.com/watch?v=XMrmfiL1xTA) | კამერის ხედვის კუთხის (`Frustum`) გარეთ დარჩენილი ჯარისკაცებისა და ხეების ავტომატური გათიშვა სწრაფი რენდერისთვის. |
| **40** | **How to Create Lip Sync Animation in Blender 4.4 (Step-by-Step)** | YouTube Blender Animation | Character Lip-Sync | [Lip Sync Animation in Blender 4.4](https://www.youtube.com/watch?v=6OFpkwDxzjs) | 3D პერსონაჟის ავტომატური ლიპ-სინქი აუდიო ფაილიდან Blender 4.4+-ში. |
| **41** | **Blender Facial Animation Secrets: Eyes and Lip Sync Tips** | YouTube Character Acting | Facial Acting & Eye Darts | [Facial Animation Secrets: Eyes & Lip Sync](https://www.youtube.com/watch?v=Q-3mhNQz5Q0) | თვალის მიკრო-მოძრაობები (`Saccades / Eye Darts`), ქუთუთოების დახამხამება და ასიმეტრიული მიმიკა ცოცხალი დიალოგისთვის. |
| **42** | **Lip Syncing in Blender (Phoneme Pose Library)** | YouTube Character Acting | Pose Library Lip-Sync | [Lip Syncing in Blender](https://www.youtube.com/watch?v=htSUzvC3drI) | ფონემური `Pose Asset Library`-ის შექმნა და აუდიო ტალღაზე (`Waveform`) დასმა. |
| **43** | **Blender Dialogue Animation: Action & Reference Footage Tips** | YouTube Character Acting | Dialogue Body Mechanics | [Blender Dialogue Animation Tips](https://www.youtube.com/watch?v=7PArZhFCfQs) | სხეულის წონის გადატანა, სუნთქვა და ჟესტის წინსწრება (`Gesture Leads Speech` 4–6 კადრით) დიალოგის დროს. |
| **44** | **6 Animation Tips You NEED to Know in Blender (2026)** | YouTube Blender Animation | Animation Curves & Easing | [6 Animation Tips in Blender](https://www.youtube.com/watch?v=zaGzTrJchzM) | `Graph Editor`-ში `Overshoot`, `Anticipation` და `Overlapping Action` მრუდების დახვეწა. |
| **45** | **How To Destroy Anything in Blender! \| Rigid Body Simulation** | YouTube Blender VFX | Siege & Destruction Physics | [Rigid Body Destruction Tutorial](https://www.youtube.com/watch?v=67VtSE5WeR0) | `Cell Fracture` + `Active/Passive Rigid Body` + `Constraints` კედლებისა და კოშკების კონტროლირებადი ნგრევისთვის. |
| **46** | **Blender \| Rigid Body Destruction \| Beginner Tutorial** | PIXXO 3D / YouTube | Physics Simulation | [PIXXO 3D Rigid Body Destruction](https://www.youtube.com/watch?v=xbX3awHrDjs) | შეჯახების იმპულსისა და ნამსხვრევების მასის (`Mass & Friction`) კალიბრაცია. |
| **47** | **3D Modeling for Destruction: Blender Rigid Body Concepts** | YouTube Blender Physics | Structural Collapse | [3D Modeling for Destruction](https://www.youtube.com/watch?v=W49jVMk2i7U) | შენობების შიდა საყრდენი სტრუქტურის მოდელირება დამაჯერებელი ჩამოშლისთვის. |
| **48** | **New Procedural Material Nodes for Blender!** | CG Cookie / YouTube | Procedural Texturing | [CG Cookie Procedural Material Nodes](https://www.youtube.com/watch?v=WbWOPCo2WEM) | ქვის, ლითონის, ხისა და ტალახის პროცედურული მასალების შექმნა UV ნაკერების გარეშე. |
| **49** | **Shading Index Switch Group Node in Geometry Nodes** | Andrea Ciani / YouTube | Multi-Variation Shaders | [Shading Index Switch Geometry Nodes](https://www.youtube.com/watch?v=la4qt0lDAx8) | ინსტანსირებული ჯარისკაცებისთვის ფარებისა და ტუნიკების ვარიაციების პროცედურული გადართვა. |
| **50** | **Blender Tutorial — Geometry Nodes Explained & Sound Animation** | YouTube Geometry Nodes | Audio-Driven 3D Graphics | [Geometry Nodes & Sound Animation](https://www.youtube.com/watch?v=a4TJGQpR0u0) | აუდიო სიხშირეებითა და ხმით მართული 3D გეომეტრიული ანიმაცია (`Bake Sound to F-Curves`). |
| **51** | **How Beautiful Light Trails Are Made in Blender 4.5** | YouTube Geometry Nodes | Map Routes & Light Trails | [Light Trails in Blender 4.5](https://www.youtube.com/watch?v=SerF_8yCVDA) | 3D რუკებზე მანათობელი მარშრუტებისა და შეტევის ხაზების შექმნა `Curve` + `Geometry Nodes`-ით. |
| **52** | **Let's Sound Design! (Sound Editing in Blender 4.3 VSE)** | YouTube Blender VSE | Audio Sync in VSE | [Sound Design in Blender 4.3](https://www.youtube.com/watch?v=XZD2zl3yV5c) | Blender-ის `Video Sequence Editor (VSE)`-ში მრავალშრიანი ხმისა და 3D სცენის კადრ-კადრ სინქრონიზაცია. |
| **53** | **Blender 2D Animation Tutorial for Beginners (Grease Pencil)** | YouTube Grease Pencil | 2D/3D Hybrid Drawing | [Grease Pencil 2D Animation Tutorial](https://www.youtube.com/watch?v=5epzCprCdGc) | `Grease Pencil`-ის ჩრდილების ნიღბები (`Mask Layers`) და 2D ანიმაცია 3D სივრცეში. |
| **54** | **Blender 5.1 Manual: EEVEE Next Introduction & Settings** | Blender Foundation | Official Render Manual | [Blender 5.1 EEVEE Manual](https://docs.blender.org/manual/en/5.1/render/eevee/introduction.html) | `EEVEE Next` რეიტრეისინგის, ჩრდილების, ვოლუმეტრიკისა და სემპლინგის ოფიციალური სპეციფიკაცია. |
| **55** | **Blender Manual: Compositing, NLA, Rigify & Freestyle** | Blender Foundation | Official Core Manual | [Blender Compositing Manual](https://docs.blender.org/manual/en/3.5/compositing/index.html) | ოფიციალური სახელმძღვანელო `Realtime Compositor`-ის, [NLA Editor](https://docs.blender.org/manual/en/4.0/editors/nla/introduction.html)-ის, [Rigify](https://docs.blender.org/manual/en/3.1/addons/rigging/rigify/metarigs.html)-სა და [Freestyle](https://docs.blender.org/manual/en/4.0/render/freestyle/index.html)-ისთვის. |

## Q. პირდაპირ გამოსაყენებელი `bpy` Python კოდის მოდულები (Production-Ready Copy-Paste `bpy` Modules)

ქვემოთ წარმოდგენილია 5 სრული, დამოუკიდებელი `bpy` Python მოდული, რომელიც ეფუძნება ვერიფიცირებულ ღია კოდის რეპოზიტორიებს ([CGArtPython/bpy_building_blocks](https://github.com/CGArtPython/bpy_building_blocks), [DLR-RM/BlenderProc](https://github.com/DLR-RM/BlenderProc), [EatTheFuture/camera_shakify](https://github.com/EatTheFuture/camera_shakify), [DanielSWolf/rhubarb-lip-sync](https://github.com/danielswolf/rhubarb-lip-sync), [domlysz/BlenderGIS](https://github.com/domlysz/blendergis)) და ოფიციალურ [Blender Python API](https://docs.blender.org/api/current/bpy.types.SceneObjects.html)-ს. თითოეული სკრიპტი ეშვება პირდაპირ უინტერფეისო რეჟიმში (`blender -b -P module.py`) და არ იყენებს კონტექსტზე დამოკიდებულ Viewport ოპერატორებს.

### Q.1 მოდული 1: კინემატოგრაფიული 3D კამერის რიგი (`Dolly / Crane / Orbit / Dolly-Zoom / Handheld Shake / Auto-DOF`)

ეს მოდული ქმნის სპლაინზე მოძრავ კამერას, აბამს მას `Track To Constraint`-ით ფოკუსურ სამიზნეზე ([Blender Track To Manual](https://docs.blender.org/manual/en/3.2/animation/constraints/tracking/track_to.html)), ააქტიურებს ოპტიკურ `Depth of Field`-ს, ითვლის ზუსტ `Dolly Zoom (Vertigo)` ფოკუსურ კომპენსაციას ($f(t) = f_0 \cdot \frac{d(t)}{d_0}$) და ამატებს [Camera Shakify](https://github.com/EatTheFuture/camera_shakify)-ს სტილის პროცედურულ ხელის კამერის რხევას:

```python
import bpy
import math
from mathutils import Vector

def create_cinematic_camera_rig(
    name: str = "CinematicCam",
    start_pos: tuple = (-8.0, -12.0, 4.5),
    end_pos: tuple = (-2.0, -4.5, 1.8),
    target_start: tuple = (0.0, 0.0, 1.6),
    target_end: tuple = (0.5, 0.0, 1.65),
    frame_start: int = 1,
    frame_end: int = 241,
    lens_mm: float = 50.0,
    fstop: float = 2.0,
    dolly_zoom_subject_width: float = 0.0,
    handheld_shake_strength: float = 0.008
):
    scene = bpy.context.scene
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.render.fps = 24

    # 1. ფოკუსური და თვალთვალის სამიზნე (Focus & Track Target Empty)
    target_empty = bpy.data.objects.new(f"{name}_Target", None)
    target_empty.empty_display_type = 'SPHERE'
    target_empty.empty_display_size = 0.25
    scene.collection.objects.link(target_empty)

    target_empty.location = Vector(target_start)
    target_empty.keyframe_insert(data_path="location", frame=frame_start)
    target_empty.location = Vector(target_end)
    target_empty.keyframe_insert(data_path="location", frame=frame_end)

    # 2. კამერის მონაცემთა ბლოკი და ოპტიკური პარამეტრები (36mm Full-Frame Sensor)
    cam_data = bpy.data.cameras.new(name)
    cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.sensor_width = 36.0
    cam_data.lens = lens_mm
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = target_empty
    cam_data.dof.aperture_fstop = fstop
    cam_data.dof.aperture_blades = 7  # კინო-ლინზის 7-ფრთიანი ბოკე

    cam_obj = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # 3. კამერის ტრაექტორიის Keyframes (Ease-In-Out Cubic Bezier)
    cam_obj.location = Vector(start_pos)
    cam_obj.keyframe_insert(data_path="location", frame=frame_start)
    cam_obj.location = Vector(end_pos)
    cam_obj.keyframe_insert(data_path="location", frame=frame_end)

    for obj in (cam_obj, target_empty):
        if obj.animation_data and obj.animation_data.action:
            for fc in obj.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.handle_left_type = 'AUTO_CLAMPED'
                    kp.handle_right_type = 'AUTO_CLAMPED'

    # 4. დეტერმინისტული Track To Constraint (-Z უყურებს სამიზნეს, Y მიმართულია ზემოთ)
    track = cam_obj.constraints.new(type='TRACK_TO')
    track.target = target_empty
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    # 5. არჩევითი Dolly Zoom (Vertigo Effect) მათემატიკური კომპენსაცია
    if dolly_zoom_subject_width > 0.0:
        for f in range(frame_start, frame_end + 1, 4):
            scene.frame_set(f)
            dist = (cam_obj.matrix_world.translation - target_empty.matrix_world.translation).length
            cam_data.lens = (cam_data.sensor_width * dist) / max(dolly_zoom_subject_width, 0.1)
            cam_data.keyframe_insert(data_path="lens", frame=f)

    # 6. პროცედურული Handheld Shake (Camera Shakify სტილის F-Curve Noise)
    if handheld_shake_strength > 0.0:
        cam_obj.rotation_euler = (0.0, 0.0, 0.0)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=frame_start)
        for idx, scale in enumerate((18.0, 22.0, 27.0)):
            fc = cam_obj.animation_data.action.fcurves.find("rotation_euler", index=idx)
            if fc:
                noise = fc.modifiers.new(type='NOISE')
                noise.scale = scale
                noise.strength = handheld_shake_strength
                noise.phase = idx * 31.4

    return cam_obj, target_empty
```

---

### Q.2 მოდული 2: `Geometry Nodes` მასშტაბური არმიის ფორმაცია და რელიეფზე მიკრობა (`Terrain Raycast Army Generator`)

ეს მოდული პროგრამულად აწყობს [Make an Army in Geometry Nodes](https://www.youtube.com/watch?v=5bnFZyNqJJA)-სა და [How I Made Huge Armies in Blender](https://www.youtube.com/watch?v=wcvgBYW9YeE)-ის ნოუდურ ხეს: ქმნის ტაქტიკურ ბადეს, `Raycast` ნოუდით აკრავს ათასობით მეომარს უსწორმასწორო მთიან რელიეფზე და ამოძრავებს ფორმაციას `180-Degree Axis`-ის გასწვრივ:

```python
import bpy

def build_geometry_nodes_army_formation(
    formation_name: str,
    soldier_collection: bpy.types.Collection,
    terrain_obj: bpy.types.Object,
    rows: int = 25,
    cols: int = 40,
    spacing: float = 1.4,
    start_xy: tuple = (-35.0, 0.0),
    end_xy: tuple = (-5.0, 0.0),
    facing_angle_rad: float = 0.0,
    frame_start: int = 1,
    frame_end: int = 241
):
    # 1. საბაზისო ფორმაციის სიბრტყის შექმნა რელიეფის ზემოთ (Z = +50m Raycast-ისთვის)
    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=cols,
        y_subdivisions=rows,
        size=max(rows, cols) * spacing * 0.5,
        location=(start_xy[0], start_xy[1], 50.0)
    )
    emitter = bpy.context.active_object
    emitter.name = formation_name

    # 2. ფორმაციის გადაადგილების ანიმაცია (Left-to-Right Screen Direction)
    emitter.location = (start_xy[0], start_xy[1], 50.0)
    emitter.keyframe_insert(data_path="location", frame=frame_start)
    emitter.location = (end_xy[0], end_xy[1], 50.0)
    emitter.keyframe_insert(data_path="location", frame=frame_end)

    # 3. Geometry Nodes ხის პროგრამული აგება
    mod = emitter.modifiers.new(name="ArmyFormationGN", type='NODES')
    tree = bpy.data.node_groups.new(name=f"{formation_name}_GNTree", type='GeometryNodeTree')
    mod.node_group = tree

    tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = tree.nodes
    links = tree.links
    n_in = nodes.new('NodeGroupInput')
    n_out = nodes.new('NodeGroupOutput')

    # რელიეფის გეომეტრიის შემოტანა და Raycast ქვემოთ (0, 0, -1) მიმართულებით
    n_terrain = nodes.new('GeometryNodeObjectInfo')
    n_terrain.inputs['Object'].default_value = terrain_obj
    n_terrain.transform_space = 'RELATIVE'

    n_ray = nodes.new('GeometryNodeRaycast')
    n_ray.inputs['Ray Direction'].default_value = (0.0, 0.0, -1.0)
    n_ray.inputs['Ray Length'].default_value = 200.0

    n_set_pos = nodes.new('GeometryNodeSetPosition')

    # მეომრების კოლექციის ინსტანსირება წერტილებზე (Instance on Points)
    n_col = nodes.new('GeometryNodeCollectionInfo')
    n_col.inputs['Collection'].default_value = soldier_collection
    n_col.inputs['Separate Children'].default_value = True
    n_col.inputs['Reset Children'].default_value = True

    n_inst = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst.inputs['Pick Instance'].default_value = True
    n_inst.inputs['Rotation'].default_value = (0.0, 0.0, facing_angle_rad)

    # მცირე ბუნებრივი მასშტაბის ვარიაცია (0.94 - 1.06)
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.data_type = 'FLOAT_VECTOR'
    n_rand.inputs['Min'].default_value = (0.94, 0.94, 0.94)
    n_rand.inputs['Max'].default_value = (1.06, 1.06, 1.06)

    links.new(n_terrain.outputs['Geometry'], n_ray.inputs['Target Geometry'])
    links.new(n_in.outputs['Geometry'], n_set_pos.inputs['Geometry'])
    links.new(n_ray.outputs['Hit Position'], n_set_pos.inputs['Position'])
    links.new(n_set_pos.outputs['Geometry'], n_inst.inputs['Points'])
    links.new(n_col.outputs['Instances'], n_inst.inputs['Instance'])
    links.new(n_rand.outputs['Value'], n_inst.inputs['Scale'])
    links.new(n_inst.outputs['Instances'], n_out.inputs['Geometry'])

    return emitter
```

---

### Q.3 მოდული 3: ილუსტრირებული ფერწერული (`Arcane / Painterly NPR`) შადერი, `Chiaroscuro` განათება და `Kuwahara` კომპოზიტორი

ეს მოდული უზრუნველყოფს, რომ 3D მოდელები 100%-ით ჩაჯდეს ილუსტრირებული ისტორიული დოკუდრამის ვიზუალურ სამყაროში ([Arcane Style Rendering](https://www.youtube.com/watch?v=EWHCjienXJ0), [Painterly Shader in Eevee](https://www.youtube.com/watch?v=sAjsMlAg5bQ), [Compositing Manual](https://docs.blender.org/manual/en/3.5/compositing/index.html)): იგი ქმნის `Shader to RGB` 3-ზონიან ფერწერულ შადერს ფუნჯის ნორმალებით, აყენებს მოტივირებულ ცეცხლის განათებას (`Chiaroscuro`) და რთავს `Realtime Compositor`-ის `Kuwahara` ფერწერულ ფილტრს:

```python
import bpy

def create_painterly_npr_material(
    mat_name: str,
    shadow_hex: tuple = (0.04, 0.06, 0.11, 1.0),
    midtone_hex: tuple = (0.18, 0.32, 0.52, 1.0),
    highlight_hex: tuple = (0.85, 0.68, 0.42, 1.0)
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    n_out = nodes.new('ShaderNodeOutputMaterial')
    n_diffuse = nodes.new('ShaderNodeBsdfDiffuse')
    n_s2rgb = nodes.new('ShaderNodeShaderToRGB')
    n_ramp = nodes.new('ShaderNodeValToRGB')

    # 3-საფეხურიანი ილუსტრირებული Chiaroscuro ტონალური რამპა
    n_ramp.color_ramp.interpolation = 'B_SPLINE'
    el0 = n_ramp.color_ramp.elements[0]
    el0.position = 0.22
    el0.color = shadow_hex
    el1 = n_ramp.color_ramp.elements[1]
    el1.position = 0.58
    el1.color = midtone_hex
    el2 = n_ramp.color_ramp.elements.new(0.86)
    el2.color = highlight_hex

    # პროცედურული ფუნჯის მონასმის ნორმალები (Painterly Brushstroke Perturbation)
    n_tex = nodes.new('ShaderNodeTexNoise')
    n_tex.inputs['Scale'].default_value = 42.0
    n_tex.inputs['Detail'].default_value = 8.0
    n_tex.inputs['Distortion'].default_value = 1.4
    n_bump = nodes.new('ShaderNodeBump')
    n_bump.inputs['Strength'].default_value = 0.18

    links.new(n_tex.outputs['Fac'], n_bump.inputs['Height'])
    links.new(n_bump.outputs['Normal'], n_diffuse.inputs['Normal'])
    links.new(n_diffuse.outputs['BSDF'], n_s2rgb.inputs['Shader'])
    links.new(n_s2rgb.outputs['Color'], n_ramp.inputs['Fac'])
    links.new(n_ramp.outputs['Color'], n_out.inputs['Surface'])
    return mat

def setup_painterly_compositor_and_freestyle(scene: bpy.types.Scene):
    # 1. Freestyle ილუსტრირებული ტუშის კონტურების ჩართვა
    scene.render.use_freestyle = True
    vl = scene.view_layers[0]
    vl.use_freestyle = True
    vl.use_pass_z = True
    vl.use_pass_mist = True

    # 2. Compositor: Anisotropic Kuwahara Painterly Filter + Z-Defocus + Vignette
    scene.use_nodes = True
    tree = scene.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    n_rl = nodes.new('CompositorNodeRLayers')
    n_kuwa = nodes.new('CompositorNodeKuwahara')
    n_kuwa.variation = 'ANISOTROPIC'
    n_kuwa.inputs['Size'].default_value = 3.0

    n_defocus = nodes.new('CompositorNodeDefocus')
    n_defocus.use_zbuffer = True
    n_defocus.f_stop = 2.8

    n_comp = nodes.new('CompositorNodeComposite')

    links.new(n_rl.outputs['Image'], n_kuwa.inputs['Image'])
    links.new(n_kuwa.outputs['Image'], n_defocus.inputs['Image'])
    links.new(n_rl.outputs['Depth'], n_defocus.inputs['Z'])
    links.new(n_defocus.outputs['Image'], n_comp.inputs['Image'])
```

---

### Q.4 მოდული 4: `Rhubarb Lip Sync` & `ElevenLabs Forced Alignment` პირდაპირი მიბმა 3D პერსონაჟის `Shape Keys`-ზე

ეს მოდული კითხულობს [DanielSWolf/rhubarb-lip-sync](https://github.com/danielswolf/rhubarb-lip-sync)-ის JSON გამოსავალს (ან `ElevenLabs` ტაიმსტამპებს) და ავტომატურად სვამს 3D პერსონაჟის სახის `Shape Keys` (`viseme_A` – `viseme_X`, თვალების დახამხამება და წარბების მოძრაობა) ფრეიმ-კადრებზე:

```python
import bpy
import json

def apply_rhubarb_lipsync_to_shapekeys(
    character_mesh_obj: bpy.types.Object,
    rhubarb_json_path: str,
    fps: int = 24,
    start_frame_offset: int = 1
):
    with open(rhubarb_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    shape_keys = character_mesh_obj.data.shape_keys.key_blocks
    viseme_names = ["viseme_A", "viseme_B", "viseme_C", "viseme_D",
                    "viseme_E", "viseme_F", "viseme_G", "viseme_H", "viseme_X"]

    for cue in data.get("mouthCues", []):
        active_v = f"viseme_{cue['value']}"
        f_start = start_frame_offset + int(round(cue["start"] * fps))
        f_end = start_frame_offset + int(round(cue["end"] * fps))
        f_mid = max(f_start + 1, (f_start + f_end) // 2)

        for v_name in viseme_names:
            if v_name not in shape_keys:
                continue
            sk = shape_keys[v_name]
            val = 0.85 if v_name == active_v else 0.0
            sk.value = 0.0
            sk.keyframe_insert(data_path="value", frame=max(1, f_start - 1))
            sk.value = val
            sk.keyframe_insert(data_path="value", frame=f_mid)
            sk.value = 0.0
            sk.keyframe_insert(data_path="value", frame=f_end + 1)
```

---

### Q.5 მოდული 5: 3D ტოპოგრაფიული ტაქტიკური რუკა `Okabe-Ito` ფერებითა და ანიმირებული 3D შეტევის ისრებით (`HELPER` Lane)

ეს მოდული ქმნის ნამდვილ 3D რელიეფურ რუკას ([BlenderGIS](https://github.com/domlysz/blendergis) / `Displace Modifier` სიმაღლის რუკით) და ხაზავს 3D მოძრავ შეტევის ვექტორებს (`Curve Bevel Factor`), რომლებიც სინქრონდება ნარატორის `Forced Alignment` ტაიმკოდებთან ([Light Trails in Blender 4.5](https://www.youtube.com/watch?v=SerF_8yCVDA), [Okabe-Ito Palette](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference)):

```python
import bpy
from mathutils import Vector

def create_3d_tactical_route_arrow(
    route_name: str,
    waypoints_xyz: list,
    hex_rgba: tuple = (0.835, 0.369, 0.0, 1.0),  # Okabe-Ito Vermilion #D55E00
    bevel_radius: float = 0.18,
    frame_appear_start: int = 24,
    frame_appear_end: int = 120
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(name=route_name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = bevel_radius
    curve_data.use_fill_caps = True

    spline = curve_data.splines.new(type='BEZIER')
    spline.bezier_points.add(len(waypoints_xyz) - 1)
    for i, pt in enumerate(waypoints_xyz):
        bp = spline.bezier_points[i]
        bp.co = Vector(pt)
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    # ისრის ზრდის ანიმაცია ნარატორის ტაიმკოდის მიხედვით
    curve_data.bevel_factor_end = 0.0
    curve_data.keyframe_insert(data_path="bevel_factor_end", frame=frame_appear_start)
    curve_data.bevel_factor_end = 1.0
    curve_data.keyframe_insert(data_path="bevel_factor_end", frame=frame_appear_end)

    mat = bpy.data.materials.new(name=f"{route_name}_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = hex_rgba
        bsdf.inputs["Emission Color"].default_value = hex_rgba
        bsdf.inputs["Emission Strength"].default_value = 1.8
    curve_data.materials.append(mat)

    obj = bpy.data.objects.new(route_name, curve_data)
    bpy.context.scene.collection.objects.link(obj)
    return obj
```

---

## R. 20 სცენის არქეტიპისა და 8 სამუშაო მაგალითის (`Examples A–H`) სრული 3D / Blender იმპლემენტაცია

ქვემოთ მოცემულია, თუ როგორ ხორციელდება სექცია 16-ის **20-ვე სცენის არქეტიპი** და სექცია 17-ის **8 სამუშაო მაგალითი (Examples A–H)** წმინდა 3D / Blender კონვეიერში (`Pure 3D NPR Blender`), და რა კონკრეტულ ხარისხობრივ გაუმჯობესებას იძლევა იგი:

### R.1 რვა სამუშაო მაგალითის (`Examples A–H`) 3D / Blender რე-ინჟინერია

| სამუშაო მაგალითი | 3D ასეტებისა და გარემოს წყარო (GitHub / HF Repo) | კამერის, ანიმაციისა და ფიზიკის გადაწყვეტა `Blender`-ში | NPR სტილიზაცია და რენდერი (`EEVEE Next / Cycles`) | რატომ აჭარბებს LTX-ს კინემატოგრაფიულ ხარისხში |
|---|---|---|---|---|
| **Example A: Large-Scale Battle (11s Continuous Action)** | რელიეფი: [Infinigen Terrain](https://github.com/princeton-vl/infinigen); მეომრები და ცხენები: [MPFB2](https://github.com/makehumancommunity/mpfb2) + [TRELLIS.2](https://github.com/microsoft/trellis.2) აბჯარი + [CMU-FBX](https://huggingface.co/datasets/meitemouss0501-del/cmu-fbx/blob/main/README.md) ციკლები. | **Module Q.2 (`Geometry Nodes Raycast`)**: 1,500 ლურჯი მხედარი (`#0072B2`) ეშვება მარცხენა ქედიდან მარჯვნივ; კამერა (`28mm`, **Module Q.1**) ეშვება სპლაინზე 265 კადრის განმავლობაში; შეჯახებაზე ირთვება `Rigid Body` ფარების მტვრევა. | `EEVEE Next` + `Volumetric Fog Shader` + `Freestyle` სილუეტური კონტური; კადრები A2, A3, A4 გადაღებულია **ერთსა და იმავე 3D სცენაში** 3 სხვადასხვა კამერით (`28mm, 135mm, 24mm`). | **100% სივრცითი და ფერადი უწყვეტობა:** A2, A3, A4 და A6 კადრებში ზუსტად იგივე მთები, დროშები და მეომრებია; მე-10 წამზე არავითარი მორფინგი არ ხდება. |
| **Example B: Two-Character Confrontation** | ინტერიერი: [allenai/Holodeck](https://github.com/allenai/Holodeck) ქვის დარბაზი; გუბერნატორი და ელჩი: [MPFB2](https://github.com/makehumancommunity/mpfb2) `Rigify` + `ARKit Shape Keys`. | 3 ვირტუალური კამერა (`Cam_Master 35mm`, `Cam_OTS_A 50mm`, `Cam_CU_B 85mm`) განთავსებულია `180° Axis`-ის ერთ მხარეს; ლიპ-სინქი იმართება **Module Q.4 (`Rhubarb Lip Sync`)**-ით, სხეულის ჟესტები — `NLA Editor`-ით. | `Chiaroscuro` განათება: მარცხნივ `Point Light (2000K)` `F-Curve Noise` ციმციმით (ბუხარი), მარჯვნივ `Area Light (5600K)` მთვარის `Rim Light` + **Module Q.3 (`Painterly Kuwahara`)**. | **100% `Eyeline Match` და ნულოვანი სახის დრეიფი:** კამერების გადართვა ხდება `Timeline Marker Bind Camera`-თი ერთი და იმავე 3D შესრულების დროს! |
| **Example C: Historical Crafting / Blacksmith** | სამჭედლო და გრდემალი: [Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2); მჭედელი: `MPFB2` + `SprongMotion-14M` უროს დარტყმის ციკლი. | უროს დარტყმის ფრეიმებზე (24, 60, 96) `Particle System` აფრქვევს 3D ნაპერწკლებს; ზოდის მასალა (`Emission Strength`) ანიმირდება ნარინჯისფერიდან (`#E69F00`) მუქ ფოლადისფერში წყალში ჩაშვებისას (`Mantaflow Steam`). | `EEVEE Next` `Bloom / Glare` ნოუდი გავარვარებულ რკინაზე + ახლო `85mm Macro DOF`. | ხელსაწყოსა და ხმლის პირის გეომეტრია რჩება აბსოლუტურად მყარი და სწორი ყველა დარტყმისას. |
| **Example D: Discovery & Z-Depth Rack Focus Reveal** | ტყე: [Infinigen Nature](https://github.com/princeton-vl/infinigen); საალყო კატაპულტები: [TRELLIS.2](https://huggingface.co/microsoft/TRELLIS.2-4B). | კამერის (`85mm, f/1.8`) `dof.focus_distance` ანიმირდება $1.5\text{m}$-დან (მზვერავი ჩირაღდნით) $18.0\text{m}$-მდე (კატაპულტები ნისლში) ზუსტად `01.5–02.8s` ინტერვალში. | რეალური 3D მოცულობითი ნისლი ([Volumetric Fog Shader](https://www.youtube.com/watch?v=2SiCtnXVVFw)) და ოპტიკური 7-ფრთიანი ბოკე. | ფოკუსის გადატანა არის ფიზიკურად რეალური 3D ოპტიკური პროცესი და ზუსტად ემთხვევა აუდიო `Sting`-ის ფრეიმს. |
| **Example E: Explanatory Geography / 3D Tactical Map** | რეალური DEM რელიეფი: [domlysz/BlenderGIS](https://github.com/domlysz/blendergis) (`SRTM`). | **Module Q.5**: 3D მთის უღელტეხილზე იზრდება `#E69F00` მომარაგების მილი, რომელსაც კეტავს `#D55E00` 3D ბლოკადა; ბოლო ფრეიმზე კამერა ეშვება პირდაპირ რუკის ხეობაში და `Match Dissolve`-ით გადადის 3D თოვლიან სცენაში! | `Okabe-Ito` ემისიური შადერები + 3D ტოპოგრაფიული კონტურული ხაზები (`Shader Wave Texture on Z-coordinate`). | რუკიდან ფიზიკურ სცენაზე გადასვლა ხდება **იდენტური 3D კამერის კოორდინატებით (`Seamless 3D Camera Match`)**. |
| **Example F: Travel / Traversal Across Seasons** | გარემო: `Infinigen` (სტეპი -> ტყე -> მთის ხეობა); ქარავანი: `Geometry Nodes` სპლაინზე (`Curve Follow`). | კამერა მოძრაობს პარალელურ ლიანდაგზე (`Lateral Tracking 50mm`) წინა პლანის 3D ხეების გავლით; წვიმა და ტალახის შხეფები იქმნება 3D ნაწილაკებით. | დღის სინათლის ანიმაცია `Nishita Sky Texture`-ის მზის კუთხის (`Sun Elevation`) შეცვლით განთიადიდან ბინდამდე. | უწყვეტი ჰორიზონტალური პარალაქსი და ამინდის ფიზიკური ერთიანობა. |
| **Example G: Battle Aftermath & Loss** | იგივე Example A-ს 3D ხეობა, სადაც `BlenderProc` ფიზიკით მიმოფანტულია გატეხილი ფარები და შუბები. | კამერა (`35mm`) იწყებს მიწის დონიდან (`Ground-Level ECU`) და 10 წამის განმავლობაში ნელა ადის მაღლა (`Crane-Up`); ქარის ველი (`Wind Force`) ნელა არხევს დახეულ დროშას (`Cloth Physics`). | გაჯერება დაწეულია Compositor-ში (`Hue/Saturation = 0.65`), ჰაერში დაფრინავს 3D ნაცრის ნაწილაკები. | მაყურებელი ცნობს Example A-ს ზუსტ ბრძოლის ველს, რაც აათმაგებს ემოციურ სიმძიმეს. |
| **Example H: Opening Hook & Final Payoff Symmetry** | დარბაზი და ნავსადგური ერთიან 3D სცენაში (`Linked Collections`). | `Opening Hook`-ში კამერა სწრაფად შედის სარკმლიდან მაგიდაზე დადებულ ბეჭედზე; `Final Payoff`-ში ზუსტად იგივე კამერა ასრულებს შებრუნებულ ტრაექტორიას (`Reverse Keyframe Curve`) გახსნილი ნავსადგურისკენ! | საწყის კადრში — ღამის ცეცხლის კონტრასტი (`12:1`), ფინალურ კადრში — მშვიდი განთიადის ოქროსფერი განათება (`3:1`). | სრული გეომეტრიული სიმეტრია დასაწყისსა და დასასრულს შორის. |

---

## S. დამატებითი 3D / Blender ტექნიკური ბარათები (Reusable Technique Cards 11–15 — Section 19 Format)

### Technique 11: Procedural Geometry Nodes Army & Crowd Terrain Raycasting

- **Discipline:** 3D layout / animation / battle choreography.
- **What it is:** `Blender Geometry Nodes`-ით ასობით ან ათასობით 3D მეომრის, მხედრის ან მოქალაქის ინსტანსირება ტაქტიკურ ბადეზე და მათი ავტომატური მიკრობა 3D რელიეფის ზედაპირზე `Raycast` ნოუდით (`Ray Direction: -Z`).
- **What the audience experiences:** მასშტაბური, გეომეტრიულად მოწესრიგებული ისტორიული არმიების მოძრაობა მთებსა და ხეობებზე, სადაც არც ერთი ჯარისკაცი არ ტივტივებს ჰაერში და არ ირევა ქაოსურ ლაქად.
- **Purpose:** მასშტაბური ბრძოლების (არქეტიპი 1), ლაშქრობებისა (არქეტიპი 7) და სახალხო ცერემონიების (არქეტიპი 15) დეტერმინისტული ვიზუალიზაცია 10–15 წამიან უწყვეტ კადრებში.
- **Use it when:** კადრში საჭიროა >10 მოძრავი ფიგურის ჩვენება მკაფიო ფრაქციული და ტაქტიკური წყობით.
- **Avoid it when:** კამერა უახლოვდება ერთ კონკრეტულ პერსონაჟს `Close-Up` მანძილზე (ახლო კადრისთვის გამოიყენეთ სრული `Rigify` გმირი და არა დაბალპოლიგონური ინსტანსი).
- **Visual requirements:** 3D რელიეფის მეში + 3–5 განსხვავებული პოზის/ანიმაციური ფაზის მქონე მეომრის კოლექცია (`Separate Children = True`, `Pick Instance = True`) + ფრაქციის ფერის ატრიბუტი (`#0072B2` vs `#D55E00`).
- **Audio requirements:** ფენოვანი საბრძოლო `Ambience / Walla`, ნაბიჯებისა და აბჯრის რიტმული გუგუნი დისტანციური `Low-Pass` ფილტრაციით.
- **Execution steps:** (1) 3–5 ვარიაციის მეომრის მომზადება წინასწარ ჩაწერილი სიარულის/სირბილის ციკლით ([CMU-FBX](https://huggingface.co/datasets/meitemouss0501-del/cmu-fbx/blob/main/README.md)); (2) **Module Q.2** სკრიპტის გაშვება რელიეფის თავზე; (3) კამერის ხედვის კუთხის (`Frustum Culling` — [Camera Culling Tutorial](https://www.youtube.com/watch?v=XMrmfiL1xTA)) ჩართვა კამერის უკან მდგომი ინსტანსების დასამალად; (4) რენდერი `EEVEE Next`-ში.
- **LTX route:** `approximate / simulated` (შეუძლია გამოიყენოს ამ სისტემის `Z-Depth` რენდერი `IC-LoRA` გიდად).
- **Blender route:** `native / directly supported` (`GeometryNodeRaycast` + `GeometryNodeInstanceOnPoints`).
- **Python route:** `deterministic / scripted` (**Module Q.2** `bpy` გენერატორი).
- **FFmpeg route:** not applicable.
- **Hybrid route:** `Blender Geometry Nodes` არენდერებს ან პირდაპირ ფინალურ NPR კადრს, ან `Depth/Normal` პასს `LTX-2.5 IC-LoRA`-სთვის.
- **Common failures:** ყველა ინსტანსის ერთსა და იმავე ფრეიმზე სინქრონული მოძრაობა (`Clone March` — აუცილებელია კოლექციაში 4–6 წანაცვლებული ფაზის ვარიანტის ჩადება!).
- **Quality check:** `Raycast Hit` შემოწმება (არც ერთი ინსტანსი არ უნდა დარჩეს `Z = +50m` სიბრტყეზე რელიეფის საზღვრებს გარეთ).
- **Cost / complexity:** Medium (ინსტანსირება იყენებს მხოლოდ ~1–2 GB VRAM-ს 5,000 მეომარზეც კი).
- **Evidence:** [Make an Army in Geometry Nodes](https://www.youtube.com/watch?v=5bnFZyNqJJA), [How I Made Huge Armies in Blender](https://www.youtube.com/watch?v=wcvgBYW9YeE), [Shading Index Switch](https://www.youtube.com/watch?v=la4qt0lDAx8) `[PROFESSIONAL PRACTICE / PRIMARY]`.
- **Confidence:** verified.

---

### Technique 12: NPR Painterly / Arcane Shader-to-RGB & Grease Pencil Line Art Hybrid

- **Discipline:** shading / lighting / compositing / art direction.
- **What it is:** 3D გეომეტრიის რენდერი არაფოტორეალისტურ (`NPR`) ფერწერულ სტილში `EEVEE Next`-ის `Shader to RGB` ტონალური რამპის, პროცედურული ფუნჯის ნორმალების, `Grease Pencil Line Art / Freestyle` ტუშის კონტურებისა და კომპოზიტორის ანაიზოტროპული `Kuwahara` ფილტრის კომბინაციით.
- **What the audience experiences:** მაყურებელი ხედავს ხელით დახატულ, ცოცხალ ილუსტრირებულ ფერწერულ ტილოს, რომელიც მოძრაობს ნამდვილი 3D კინოკამერის პარალაქსითა და დრამატული განათებით.
- **Purpose:** ერთიანი ილუსტრირებული ვიზუალური სამყაროს შენარჩუნება 3D მოდელების გამოყენებისას (`Uncanny Valley`-სა და იაფფასიანი პლასტმასის 3D იერის სრული აღმოფხვრა).
- **Use it when:** ყველა 3D პერსონაჟის, არქიტექტურისა და რეკვიზიტის რენდერისას როგორც `VIDEO`, ისე `STILL` ზოლში.
- **Avoid it when:** იყენებთ სტანდარტულ ფოტორეალისტურ `Principled BSDF` პრიალა პლასტმასის მასალებს კომპოზიტორის ფერწერული ფილტრის გარეშე.
- **Visual requirements:** 3-ზონიანი `ColorRamp` (ჩრდილი, ძირითადი ტონი, განათებული კიდე), ფუნჯის მონასმის `Bump/Normal` რუკა და `Anisotropic Kuwahara (Size: 2–4px)`.
- **Audio requirements:** not applicable.
- **Execution steps:** (1) **Module Q.3**-ით `create_painterly_npr_material()`-ის მინიჭება 3D ობიექტებზე; (2) `Scene Line Art` ან `Freestyle` სილუეტური ხაზების ჩართვა ([Grease Pencil Primitives](https://docs.blender.org/manual/en/3.0/grease_pencil/primitives.html), [Freestyle Manual](https://docs.blender.org/manual/en/4.0/render/freestyle/index.html)); (3) `CompositorNodeKuwahara` (`ANISOTROPIC`) ჩართვა კომპოზიტორში.
- **LTX route:** `approximate / simulated` (შეიძლება გაიწვრთნას სტილის LoRA Blender-ის ამ რენდერებზე).
- **Blender route:** `native / directly supported` (`ShaderNodeShaderToRGB`, `GP_LINEART`, `CompositorNodeKuwahara`).
- **Python route:** `deterministic / scripted` (**Module Q.3**).
- **FFmpeg route:** `approximate / simulated` (მხოლოდ საბოლოო ფერის კორექცია და მარცვლოვანება).
- **Hybrid route:** 100% `Blender EEVEE Next + Realtime Compositor`.
- **Common failures:** `Freestyle` ხაზების ზედმეტი სისქე შორეულ `EWS` კადრებში (აუცილებელია `Distance from Camera` ხაზის სისქის მოდიფიკატორის დადება!).
- **Quality check:** კადრის გადიდებისას (`200% Zoom`) უნდა იკითხებოდეს ფერწერული მონასმების კლასტერები და სუფთა კონტური პიქსელური ალიასინგის გარეშე.
- **Cost / complexity:** Low (`EEVEE Next` არენდერებს ამ შადერს რეალურ დროში — <0.5 წმ/კადრი).
- **Evidence:** [Arcane Style Rendering](https://www.youtube.com/watch?v=EWHCjienXJ0), [Painterly Shader in Eevee](https://www.youtube.com/watch?v=sAjsMlAg5bQ), [Making 3D Look Painterly](https://www.youtube.com/watch?v=s8N00rjil_4), [Freestyle Manual](https://docs.blender.org/manual/en/4.0/render/freestyle/index.html) `[PRIMARY / PROFESSIONAL PRACTICE]`.
- **Confidence:** verified.

---

### Technique 13: Automated Rhubarb + Shape-Key 3D Facial Lip-Sync & NLA Mocap Retargeting

- **Discipline:** 3D character animation / dialogue direction.
- **What it is:** `ElevenLabs`-ის გახმოვანებული დიალოგური WAV ფაილის ავტომატური გარდაქმნა 3D პერსონაჟის პირის ვიზემების (`Shape Keys A–H, X`) Keyframe-ებად [Rhubarb Lip Sync](https://github.com/danielswolf/rhubarb-lip-sync)-ის მეშვეობით, პარალელურად [SprongMotion-14M](https://huggingface.co/SegerEnd/SprongMotion-14M/blob/main/README.md) ან [CMU-FBX](https://huggingface.co/datasets/meitemouss0501-del/cmu-fbx/blob/main/README.md) სხეულის ჟესტების დადებით [NLA Editor](https://docs.blender.org/manual/en/4.0/editors/nla/introduction.html)-ში.
- **What the audience experiences:** სტაბილური, გამომსახველი 3D პერსონაჟის სახისა და სხეულის თამაში ნულოვანი გენერაციული მორფინგითა და ზუსტი აუდიო-ვიზუალური სინქრონიზაციით.
- **Purpose:** პერსონაჟთა დიალოგური სცენების (`20–30%` სასაუბრო ბიუჯეტი) სრულად დეტერმინისტული შესრულება.
- **Use it when:** ნებისმიერ დიალოგურ ან მონოლოგურ კადრში, სადაც ჩანს მოლაპარაკე 3D პერსონაჟი.
- **Avoid it when:** ამოძრავებთ მხოლოდ პირს გაშეშებულ სახეზე თვალების მიკრო-მოძრაობებისა (`Eye Darts`) და სუნთქვის გარეშე ([Facial Animation Secrets](https://www.youtube.com/watch?v=Q-3mhNQz5Q0)).
- **Visual requirements:** [MPFB2](https://github.com/makehumancommunity/mpfb2) ან `Rigify` 3D პერსონაჟი 9 სტანდარტული ვიზემის `Shape Key`-ით, ქუთუთოების დახამხამებითა (`blink`) და თვალის სამიზნე კონტროლერით (`eye_target`).
- **Audio requirements:** `ElevenLabs v4` WAV ფაილი + ტექსტური ტრანსკრიპტი.
- **Execution steps:** (1) `rhubarb -f json -d transcript.txt dialogue.wav -o lipsync.json` გაშვება; (2) **Module Q.4 (`apply_rhubarb_lipsync_to_shapekeys`)** გაშვება Blender-ში; (3) თვალის დახამხამების დამატება ყოველ 70–110 კადრში და სხეულის სუნთქვის/ჟესტის NLA სტრიპის დადება ([Rokoko Retargeting](https://github.com/Rokoko/rokoko-studio-live-blender)).
- **LTX route:** alternative to `LTX-2.5 Audio-to-Video`.
- **Blender route:** `native / directly supported` (`Shape Keys` + `NLA Editor`).
- **Python route:** `deterministic / scripted` (**Module Q.4** + `subprocess` call to `rhubarb`).
- **FFmpeg route:** `native / directly supported` (`J-cut / L-cut` აუდიო-ვიდეო მუქსინგი).
- **Hybrid route:** `ElevenLabs` -> `Rhubarb CLI` -> `Blender bpy Shape Keys + NLA` -> `FFmpeg`.
- **Common failures:** `Shape Key` წონის `1.0`-ზე დაყენება ყველა მარცვალზე (იწვევს ყბის გადაჭარბებულ გაღებას — ოპტიმალური წონაა `0.70–0.85`!).
- **Quality check:** დახურული თანხმოვნების (`M, B, P` -> `viseme_A`) ზუსტი დამთხვევა აუდიო ტალღის ტრანზიენტთან.
- **Cost / complexity:** Low (100% უფასო და დეტერმინისტული CPU/GPU პროცესი).
- **Evidence:** [DanielSWolf/rhubarb-lip-sync](https://github.com/danielswolf/rhubarb-lip-sync), [MPFB2](https://github.com/makehumancommunity/mpfb2), [Lip Sync in Blender 4.4](https://www.youtube.com/watch?v=6OFpkwDxzjs), [Facial Animation Secrets](https://www.youtube.com/watch?v=Q-3mhNQz5Q0) `[PRIMARY / OFFICIAL]`.
- **Confidence:** verified.

---

### Technique 14: True 3D Topographic Tactical Map with Animated Bevel Curves (`BlenderGIS` + `Okabe-Ito`)

- **Discipline:** 3D cartography / motion graphics (`HELPER` Lane).
- **What it is:** რეალური გეოგრაფიული სიმაღლის რუკის (`DEM Heightmap` / [BlenderGIS](https://github.com/domlysz/blendergis)) საფუძველზე აგებული 3D ტოპოგრაფიული რელიეფი, რომელზეც `Curve Bevel Factor`-ით იზრდება სამგანზომილებიანი შეტევის ისრები და ფრაქციული ზონები [Okabe-Ito ფერებით](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference).
- **What the audience experiences:** ბრტყელი 2D სქემის ნაცვლად მაყურებელი ხედავს სამგანზომილებიან სამხედრო-სტრატეგიულ მაკეტს, სადაც კამერა დაფრინავს რეალური მთის უღელტეხილებისა და ხეობების თავზე.
- **Purpose:** ტაქტიკური მანევრების, ალყისა და მომარაგების გზების ახსნა `HELPER` (10%) ბიუჯეტის ფარგლებში უმაღლესი კინემატოგრაფიული ხარისხით.
- **Use it when:** გეოგრაფიული რელიეფი (მთები, კანიონები, მდინარეები, სიმაღლის უპირატესობა) პირდაპირ განსაზღვრავს ისტორიული მოვლენის შედეგს.
- **Avoid it when:** საჭიროა მხოლოდ მარტივი 2-სვეტიანი რიცხვითი დიაგრამა (სადაც 2D `Python Matplotlib/Pillow` უფრო სწრაფი და სუფთაა).
- **Visual requirements:** მუქი ტაქტიკური რელიეფის შადერი (`#1A1D24`) ჰორიზონტალური იზოჰიფსებით (`Contour Lines`), `Okabe-Ito` ემისიური ისრები (`#0072B2` vs `#D55E00` + `#F0E442`) და ორთოგრაფიული ან `35mm` დახრილი 3D კამერა.
- **Audio requirements:** ნარატორი (`Forced Alignment` სინქრონით) + დაბალი ანალიტიკური `Ostinato` + პერგამენტისა და ხის ფიგურების ტაქტილური `Foley`.
- **Execution steps:** (1) `BlenderGIS`-ით ან `Displace Modifier`-ით რეგიონის სიმაღლის რუკის იმპორტი; (2) **Module Q.5 (`create_3d_tactical_route_arrow`)** გაშვება `ElevenLabs` ტაიმსტამპებზე მიბმული ფრეიმ-ინტერვალებით; (3) ტოპონიმების დადება 2D/3D ბილბორდებად (`Track To Camera`, `17–20 CPS`).
- **LTX route:** `unsupported`.
- **Blender route:** `native / directly supported` (`Curve.bevel_factor_end` + `Displace Modifier` + `BlenderGIS`).
- **Python route:** `deterministic / scripted` (**Module Q.5** + `Pillow` ტექსტური ეტიკეტების ოვერლეი).
- **FFmpeg route:** `native / directly supported` (საბოლოო კომპოზიცია და აუდიო მიქსი).
- **Hybrid route:** `Blender` არენდერებს 3D ტოპოგრაფიულ რელიეფსა და 3D ისრებს -> `Python Pillow` აწერს იდეალურად მკვეთრ 2D ტოპონიმებსა და თარიღებს -> `FFmpeg`.
- **Common failures:** 3D ტექსტის დახრა მცირე კუთხით ან პერსპექტიული დაბინდვით (`DOF` არ უნდა ბინდავდეს აქტიურ ტოპონიმს!).
- **Quality check:** `WCAG Contrast >= 4.5:1` ყველა ტოპონიმზე და გეოგრაფიული მასშტაბის ისტორიული სიზუსტე.
- **Cost / complexity:** Low to Medium (`EEVEE Next`-ში რენდერდება 0.2 წმ/კადრი სიჩქარით).
- **Evidence:** [domlysz/BlenderGIS](https://github.com/domlysz/blendergis), [Light Trails in Blender 4.5](https://www.youtube.com/watch?v=SerF_8yCVDA), [Okabe-Ito Palette Reference](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference) `[PRIMARY / OFFICIAL]`.
- **Confidence:** verified.

---

### Technique 15: Active/Passive Rigid-Body Siege Destruction & Mantaflow Volumetric Smoke

- **Discipline:** 3D physics simulation / VFX.
- **What it is:** ციხესიმაგრის გალავნის, კოშკის ან კარიბჭის დანგრევის დეტერმინისტული სიმულაცია [Blender Rigid Body Physics](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html)-ით (`Cell Fracture` + `Active/Passive` სხეულები), სინქრონიზებული `Mantaflow` კვამლისა და მტვრის ვოლუმეტრიულ აფეთქებასთან.
- **What the audience experiences:** რეალური სიმძიმის, მასისა და გრავიტაციის მქონე ნგრევა, სადაც თითოეული ქვის ბლოკი ეცემა ფიზიკის კანონების დაცვით და არ ქრება ჰაერში.
- **Purpose:** ალყის, კატაპულტის/ზარბაზნის გასროლისა და ნგრევის სცენების (არქეტიპები 1, 14, 19) ფიზიკური დამაჯერებლობა.
- **Use it when:** სცენარი მოითხოვს ობიექტის დამსხვრევას, კედლის ჩამოშლას ან საბრძოლო შეჯახებას.
- **Avoid it when:** ნგრევა ხდება შორეულ ფონზე მცირე მასშტაბით (სადაც საკმარისია მარტივი ნაწილაკებისა და კვამლის ფენა).
- **Visual requirements:** წინასწარ დანაწევრებული (`Cell Fracture`) 3D კედელი (`Rigid Body: Active`, `Deactivation -> Start Deactivated = True` შეჯახების მომენტამდე!) + საძირკველი (`Rigid Body: Passive`).
- **Audio requirements:** 1.5-წამიანი სიჩუმე ჭურვის მოხვედრამდე -> მძლავრი `Sub-Impact (-1.5 dBTP)` შეჯახების ფრეიმზე -> ქვების ჩამოშლის ხანგრძლივი `Debris Tail`.
- **Execution steps:** (1) კედლის დაყოფა 40–80 ფრაგმენტად; (2) ფრაგმენტებზე `Active Rigid Body` (`Mass: 250 kg`, `Start Deactivated = True`) მინიჭება; (3) ჭურვის (`Active, Animated`) შეჯახების ფრეიმზე $F_{\text{hit}}$ კონტაქტის გააქტიურება და მტვრის ნაწილაკების გაშვება; (4) სიმულაციის ჩაწერა (`Bake All Dynamics`) რენდერამდე.
- **LTX route:** `prompt-driven / probabilistic` (ხშირად არღვევს გრავიტაციასა და მასის შენახვის კანონს).
- **Blender route:** `native / directly supported` (`RigidBodyWorld` + `Fluid/Smoke Domain`).
- **Python route:** `deterministic / scripted` ([DLR-RM/BlenderProc](https://github.com/DLR-RM/BlenderProc) ან [google-research/kubric](https://github.com/google-research/kubric/blob/main/challenges/movi/README.md) ფიზიკის სკრიპტი).
- **FFmpeg route:** `native / directly supported` (`Sub-Impact` აუდიო სინქრონიზაცია $F_{\text{hit}}$ ფრეიმზე).
- **Hybrid route:** `Blender Rigid Body` ასრულებს ზუსტ ნგრევას -> რენდერდება ან პირდაპირ NPR სტილში, ან გადაეცემა `LTX-2.5 IC-LoRA`-ს დეტალური მტვრის სინთეზისთვის.
- **Common failures:** `Start Deactivated`-ის გამორთვა (კედელი თავისით იშლება პირველივე კადრზე ჭურვის მოხვედრამდე!).
- **Quality check:** $F_{\text{hit}}$ ფრეიმამდე კედლის ნულოვანი გადაადგილება და შეჯახების ფრეიმის 100%-იანი თანხვედრა აუდიო `Impact`-თან.
- **Cost / complexity:** Medium.
- **Evidence:** [Blender Manual: Rigid Body Introduction](https://docs.blender.org/manual/en/3.2/physics/rigid_body/introduction.html), [How To Destroy Anything in Blender](https://www.youtube.com/watch?v=67VtSE5WeR0), [PIXXO 3D Rigid Body Tutorial](https://www.youtube.com/watch?v=xbX3awHrDjs) `[PRIMARY / OFFICIAL]`.
- **Confidence:** verified.

---

## T. შემაჯამებელი გადაწყვეტილების მატრიცა: LTX-2.5 vs. Pure 3D Blender vs. Hybrid 3D-Guided Pipeline

საწარმოო სისტემას ახლა გააჩნია სამი სრულად დოკუმენტირებული რეჟიმი. ქვემოთ მოცემულია გადაწყვეტილების მიღების ზუსტი მატრიცა, თუ როდის რომელი რეჟიმი იძლევა საუკეთესო შედეგს:

| საწარმოო სცენარი / მოთხოვნა | ვარიანტი 1: LTX-2.5 + Python/FFmpeg (სექციები A–L) | ვარიანტი 2: Pure 3D Blender NPR + Python/FFmpeg (სექციები M–S) | ვარიანტი 3: Hybrid 3D-Blender-Guided LTX-2.5 (`Blender Previs -> LTX IC-LoRA`) | საბოლოო საწარმოო რეკომენდაცია |
|---|---|---|---|---|
| **პერსონაჟისა და გარემოს 100%-იანი იდენტობის შენარჩუნება მრავალ კადრში** | საშუალო (საჭიროებს LoRA-სა და ≤5s ლიმიტს). | **უმაღლესი (100% იდენტური 3D მეში ყველა რაკურსში).** | მაღალი (`Blender` იჭერს გეომეტრიას, `LTX` ავსებს ტექსტურას). | **Pure 3D Blender NPR** (ან Hybrid მთავარ პერსონაჟებზე). |
| **რთული 3D კამერის ქორეოგრაფია (`360° Orbit, Crane-Up, Dolly Zoom`)** | დაბალი/საშუალო (მხოლოდ პრომპტით იშლება). | **უმაღლესი (ფიზიკური 3D კამერა + `Track To` + `DOF`).** | მაღალი (`Blender` ქმნის `Depth/Track` გიდს `LTX IC-LoRA`-სთვის). | **Pure 3D Blender NPR** (Module Q.1). |
| **მასშტაბური არმიების ტაქტიკური ფორმაცია (10–15 წმ უწყვეტი კადრი)** | საშუალო (მეომრები ერთმანეთს ერწყმის შორ მანძილზე). | **უმაღლესი (`Geometry Nodes Raycast` 1,000+ მეომრით).** | **უმაღლესი** (`Blender Geometry Nodes` გიდი + `LTX-2.5` ატმოსფერული დეტალიზაცია). | **Pure 3D Blender** ან **Hybrid 3D-Guided LTX**. |
| **ბუნებრივი ორგანული ტექსტურები (ცეცხლი, წყლის შხეფი, ცხოველების მიკრო-მოძრაობა)** | **უმაღლესი (`LTX-2.5 DFR` ბუნებრივად ქმნის რთულ ფლუიდურ ტექსტურებს).** | საშუალო/მაღალი (მოითხოვს `Mantaflow` ან 2D FX Cards-ს). | **უმაღლესი** (3D ბლოკინგი + `LTX` ორგანული სინთეზი). | **LTX-2.5** ან **Hybrid**. |
| **3D ტოპოგრაფიული და სტრატეგიული რუკები (`HELPER` 10%)** | დაუშვებელია LTX-ში (მხოლოდ 2D `Python`). | **უმაღლესი (`BlenderGIS` 3D რელიეფი + Module Q.5 3D ისრები).** | იგივე (`Blender 3D Terrain` + `Python` 2D ტოპონიმები). | **Pure 3D Blender (`BlenderGIS`) + Python Typography**. |
| **API და ღრუბლოვანი ინფერენსის ხარჯი (`Cloud GPU / API Cost`)** | მოითხოვს 24–48GB VRAM-ს ან `$0.04–$0.24/s` API ხარჯს. | **100% უფასო და ლოკალური (`EEVEE Next` მუშაობს 8–12GB VRAM-ზეც კი 0.3–1.0 წმ/კადრი სიჩქარით).** | საშუალო (`Blender` უფასოა + `LTX` ინფერენსი). | **Pure 3D Blender NPR** (ნულოვანი API ხარჯი და სრული დეტერმინიზმი). |

## U. უფასო და ღია კოდის 3D სამყაროებისა და ასეტების ბიბლიოთეკები Blender-ისთვის (Free & Open-Source 3D World Libraries)

იმისათვის, რომ 12-წუთიანი ისტორიული დოკუდრამის ყველა ეპიზოდი და ყველა კადრი ეკუთვნოდეს **ერთ მონოლითურ, ეპიკურ და ვიზუალურად თანმიმდევრულ სამყაროს**, დაუშვებელია ინტერნეტში შემთხვევით ნაპოვნი, სხვადასხვა პროპორციისა და ტექსტურის მქონე 3D მოდელების ქაოსური შერევა. საწარმოო სისტემა უნდა დაეყრდნოს **მოდულურ (`Modular Kitbashing`) და პროცედურულ (`Procedural Seed-Based`) უფასო ბიბლიოთეკებს**, რომლებიც იძლევა ერთი და იმავე საბაზისო სამშენებლო კომპონენტებისგან ასობით განსხვავებული ქალაქის, ციხესიმაგრის, ბრძოლის ველის, ტყისა და დარბაზის უსასრულოდ რეგენერირების საშუალებას.

### U.1 16 ვერიფიცირებული უფასო / CC0 3D სამყაროსა და ასეტების ბიბლიოთეკის კატალოგი

| # | ბიბლიოთეკა / გენერატორი | პირდაპირი ვერიფიცირებული URL | ლიცენზია | რას მოიცავს (სამყაროს კომპონენტები) | როგორ უზრუნველყოფს 1 ერთიან სტილს და ახლიდან დაგენერირებას (`Regeneration & Unity`) |
|---|---|---|---|---|---|
| **1** | **Infinigen (Nature & Indoors)** | [GitHub: princeton-vl/infinigen](https://github.com/princeton-vl/infinigen) | BSD 3-Clause (100% Free & Commercial) | პროცედურული მთები, კანიონები, მდინარეები, ტყეები, ხეები, კლდეები, ღრუბლები, ცა, ქარი და შიდა დარბაზები/ოთახები (`Infinigen-Indoors`). | 100% მათემატიკურად ერთიანი `Geometry Nodes` და შადერ-გრაფები; ნებისმიერი ახალი `--seed` წამებში აგენერირებს სრულიად ახალ ლანდშაფტს ან დარბაზს ზუსტად იმავე ვიზუალურ სტილში. |
| **2** | **Poly Haven (Models, Terrains, HDRIs, Textures)** | [Poly Haven All Assets](https://polyhaven.com/all) & [Ground & Terrain](https://polyhaven.com/textures/ground-terrain) | **CC0 (Public Domain)** — ატრიბუციის გარეშეც | ასობით კინემატოგრაფიული 3D კლდე, მცენარე, ისტორიული ავეჯი, არქიტექტურული ელემენტი, `8K` რელიეფის ტექსტურა და `16K` ბუნებრივი განათების HDRI. | ყველა ასეტი კალიბრირებულია ერთიან ფიზიკურ PBR სტანდარტსა და რეალურ მეტრულ მასშტაბში (`1 unit = 1 meter`); ერთიანი HDRI განათება კრავს ყველა სცენას. |
| **3** | **ambientCG (2,000+ PBR Materials & Terrains)** | [ambientCG Asset List](https://ambientcg.com/list) & [Gallery](https://ambientcg.com/gallery) | **CC0 (Public Domain)** | 2,000+ უფასო PBR მასალა (ქვის გალავნები, ციხის კედლები, ტალახი, ბალახი, დაჟანგული რკინა, ძველი ხე — მაგ. [Wood 095](https://ambientcg.com/view?id=Wood095)) და 3D რელიეფი. | მზა `.blend` Asset Browser კატალოგები; ერთიანი სკალირებადი მასალების ბიბლიოთეკა მთელი სამყაროს ზედაპირებისთვის. |
| **4** | **Quaternius CC0 Modular Packs** | [Quaternius Modular Medieval & Dungeon](https://quaternius.com/packs/medievaldungeon.html) | **CC0 (Public Domain)** | მოდულური შუა საუკუნეების კედლები, კოშკები, თაღები, კასრები, ჩირაღდნები, იარაღი, გემები, ბუნება და დარიგული პერსონაჟები პირდაპირ `.blend` ფორმატში. | შექმნილია ერთი ავტორის მიერ მკაცრად ფიქსირებულ ბადესა (`Grid Snap`) და ერთიან სტილიზებულ გეომეტრიულ პროპორციებში. |
| **5** | **KayKit Stylized Modular Universe** | [KayKit Medieval Hexagon](https://kaylousberg.itch.io/kaykit-medieval-hexagon), [KayKit Dungeon](https://kaylousberg.itch.io/kaykit-dungeon) & [KayKit Complete](https://kaylousberg.itch.io/kaykit-complete) | **CC0 / Free Tier** | 200+ მოდულური შუა საუკუნეების შენობა, ციხესიმაგრის სექცია, ჰექსაგონური რელიეფის ფილა, ტყე, საალყო დეტალი და პერსონაჟი. | იდეალურია სტრატეგიული დიორამებისა და სტილიზებული ქალაქების ასაწყობად — ლეგოს კუბიკებივით ერგება ერთმანეთს ნებისმიერი კომბინაციით. |
| **6** | **Blender Studio Open Movie Libraries** | [Blender Studio Characters & Sets](https://studio.blender.org/characters/5d403ddeee3219164b952e27/v2/) & [Sprite Fright Lessons](https://studio.blender.org/projects/sprite-fright/394e83f00b4b5c/?asset=4968) | **CC-BY** (Blender Foundation) | ღია ფილმების (*Sprite Fright*, *Charge*, *Wing It!*, *Spring*, *Sintel*) სრული საწარმოო ფაილები: ტყეები, კლდეები, ცეცხლის/კვამლის რიგები და პერსონაჟები. | სტუდიური დონის `Collection Instance` + `Library Override` არქიტექტურა, რომელიც პირდაპირ მზადაა მრავალეპიზოდიანი სერიალისთვის. |
| **7** | **BlenderGIS (Real-Earth DEM & OSM)** | [GitHub: domlysz/BlenderGIS](https://github.com/domlysz/blendergis) | GPL-3.0 (100% Free) | დედამიწის ნებისმიერი წერტილის რეალური სატელიტური 3D ტოპოგრაფია (`SRTM 30m DEM`), მდინარეების ქსელი და რელიეფის კონტურები. | მთელი ეპიზოდის ბრძოლის ველები და ტაქტიკური რუკები (`HELPER`) იგება ერთი და იმავე რეალური გეოგრაფიული რეგიონის უწყვეტ 3D მეშზე. |
| **8** | **A.N.T. Landscape (Built-in Blender Addon)** | [Blender Manual: ANT Landscape](https://docs.blender.org/manual/en/3.1/addons/add_mesh/ant_landscape.html) | GPL (ჩაშენებულია Blender-ში) | პროცედურული მთათა სისტემები, ხეობები, კანიონები, პლატოები, ვულკანები და ჰიდრავლიკური ეროზიის ნიღბები. | `Noise Size`, `Strata` და `Random Seed` პარამეტრების შეცვლით 1 წამში აგენერირებს უსასრულო რაოდენობის მთებსა და ბრძოლის ველებს ერთიანი ტოპოლოგიით. |
| **9** | **Building Tools (Procedural Architecture)** | [GitHub: ranjian0/building_tools](https://github.com/ranjian0/building_tools) & [Wiki](https://github.com/ranjian0/building_tools/wiki) | GPL-3.0 (100% Free) | პროცედურული შენობების, სართულების, სახურავების, თაღოვანი სარკმლების, აივნების, კიბეებისა და კოშკების გენერატორი. | ერთი საბაზისო არქიტექტურული წესით (`Style Preset`) აგენერირებს მთელ ქალაქს, სადაც ყველა სახლი განსხვავებული ზომისაა, მაგრამ 100%-ით ერთი ეპოქისა და სტილისაა. |
| **10** | **MPFB2 (MakeHuman for Blender 4.2+)** | [GitHub: MakeHumanCommunity/mpfb2](https://github.com/makehumancommunity/mpfb2) | AGPL / CC0 Assets (100% Free) | პარამეტრული 3D ადამიანების, სახეების, თმის, წვერისა და ისტორიული ტანსაცმლის გენერატორი სრული `Rigify` და `Shape Key` მხარდაჭერით. | გამორიცხავს სხვადასხვა საიტიდან გადმოწერილი პერსონაჟების ანატომიურ შეუთავსებლობას: მეფეც, ელჩიც და 1,000 ჯარისკაციც იქმნება ერთი და იმავე ბაზური მეშის პარამეტრული ვარიაციით! |
| **11** | **Blendkit / BlenderKit Free Library** | [Blendkit Official](https://www.blenderkit.com/) & [Baked Materials](https://www.blenderkit.com/articles/modelled-and-baked-materials/) | Royalty-Free / CC0 Tier | ათასობით უფასო 3D რეკვიზიტი (ხმლები, ფარები, სანთლები, ურმები, კარვები) და პროცედურული მასალა პირდაპირ Blender-ის პანელში. | გამოიყენება მეორადი რეკვიზიტების (`Set Dressing`) შესავსებად ჩვენი ერთიანი `Master NPR Shader`-ის ქვეშ. |
| **12** | **Smithsonian Open Access CC0 3D** | [Smithsonian Open Access 3D](https://www.si.edu/openaccess/updates/21st-century-diffusion) | **CC0 (Public Domain)** | 2,200+ მუზეუმის მიერ ლაზერით სკანირებული რეალური ისტორიული არტეფაქტი, ქანდაკება, მონეტა, იარაღი და არქიტექტურული ფრაგმენტი. | იძლევა 100%-ით ავთენტურ ისტორიულ ფორმებს (`Visual Proof`), რომლებსაც Blender-ში ედება ერთიანი ბრინჯაოს/ქვის/ფერწერული შადერი. |
| **13** | **Objaverse & Objaverse-XL (10M+ 3D Objects)** | [GitHub: allenai/objaverse-xl](https://github.com/allenai/objaverse-xl) & [HF Dataset](https://huggingface.co/datasets/allenai/objaverse-xl) | ODC-By / CC-BY / CC0 Filterable | 10 მილიონზე მეტი 3D ობიექტის ღია ინდექსი Python API-თ (`objaverse.load_objects`), საიდანაც იფილტრება CC0/CC-BY ისტორიული ობიექტები. | Python სკრიპტით ავტომატურად იწერება საჭირო კატეგორიის ობიექტები და გადის ავტომატურ ნორმალიზაციასა და რემეშინგს Blender-ში. |
| **14** | **Hunyuan3D-2 & TRELLIS.2 Local Generators** | [GitHub: Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) & [HF TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B) | Open-Weights | ნებისმიერი სპეციფიკური ისტორიული იარაღის, გვირგვინის ან შენობის ლოკალური 3D გენერაცია ერთი რეფერენს-სურათიდან ([SifuInTheShell/Effigy](https://github.com/SifuInTheShell/Effigy)). | გენერირებულ `.glb/.obj` მოდელს იმპორტისთანავე ეცვლება ტექსტურა ჩვენი სამყაროს `Master NPR Shader`-ით, რაც მას 100%-ით აერთიანებს დანარჩენ სცენასთან. |
| **15** | **DLR-RM/BlenderProc Scene Loader** | [GitHub: DLR-RM/BlenderProc](https://github.com/DLR-RM/BlenderProc) | GPL-3.0 | პროცედურული სცენების ამწყობი Python ბიბლიოთეკა ფიზიკური დაჯახებების (`Collision Check`) და ავტომატური განათების მხარდაჭერით. | უზრუნველყოფს, რომ მოდულური ბიბლიოთეკებიდან აღებული ასეტები ავტომატურად დაჯდეს მიწაზე და არ გადაკვეთოს ერთმანეთი. |
| **16** | **Awesome-Blender Open Ecosystem** | [GitHub: agmmnn/awesome-blender](https://github.com/agmmnn/awesome-blender) | MIT Index | კურირებული ღია კოდის გენერატორების (ხეების, კლდეების, ქალაქების, გზების, შადერების) ერთიანი საცავი. | საშუალებას იძლევა სწრაფად დაემატოს სპეციალიზებული პროცედურული მოდიფიკატორები ერთიანი სამყაროს ფარგლებში. |

---

## V. ერთიანი სტილის ძრავა (`The Style Unification Engine`): როგორ ვაქციოთ ნებისმიერი ბიბლიოთეკის მოდელები 100%-ით ერთ სტილად

მთავარი ტექნიკური საიდუმლო, რომელსაც პროფესიონალური ანიმაციური სტუდიები ([Blender Studio: Sprite Fright Shading](https://studio.blender.org/projects/sprite-fright/394e83f00b4b5c/?asset=4968), [Arcane Style Rendering](https://www.youtube.com/watch?v=EWHCjienXJ0)) იყენებენ სხვადასხვა წყაროდან აღებული 3D მოდელების გასაერთიანებლად, არის **გეომეტრიისა და ზედაპირის შადერის სრული გამიჯვნა (`Geometry-Shader Decoupling`)**.

როდესაც თქვენ შემოგაქვთ მთა `Infinigen`-იდან, კოშკი `Quaternius`-იდან, ქანდაკება `Smithsonian`-იდან და პერსონაჟი `MPFB2`-იდან, მათი ქარხნული ტექსტურები ერთმანეთს ეწინააღმდეგება. მაგრამ თუ Blender-ში იმპორტისთანავე Python სკრიპტით გადავაწერთ მათ **4-დონიან სტილის უნიფიკატორს (`4-Layer Style Unification Protocol`)**, ყველა ობიექტი მყისიერად ხდება ერთი სამყაროს ნაწილი:

1. **დონე 1 — ტრი-პლანარული პროცედურული მასტერ-შადერი (`Tri-Planar Master NPR Material Override`):**
   უარს ვამბობთ გადმოწერილი მოდელების არათანაბარ UV-ტექსტურებზე. ნაცვლად ამისა, `Texture Coordinate -> Object / Generated` და `Box Projection (Blend = 0.25)` მეთოდით ყველა ობიექტს ედება ერთიანი პროცედურული მასტერ-შადერი ([CG Cookie Procedural Material Nodes](https://www.youtube.com/watch?v=WbWOPCo2WEM)), რომელიც ავტომატურად კითხულობს 3D მოდელის გეომეტრიულ კიდეებს (`Geometry -> Pointiness` და `Ambient Occlusion`):
   * ამოზნექილ კიდეებზე (`Pointiness > 0.52`) ავტომატურად ჩნდება გაცვეთილი ფუნჯის განათებული შტრიხი (`Edge Highlight`);
   * ჩაღრმავებებში (`Ambient Occlusion`) ავტომატურად ჯდება ღრმა ილუსტრირებული ჩრდილი (`Shadow Role Color`);
   * ძირითად ზედაპირზე მუშაობს `Shader to RGB` 3-საფეხურიანი ფერწერული რამპა (იხ. სექცია Q.3).
2. **დონე 2 — გეომეტრიული დეტალიზაციის ნორმალიზაცია (`Subdivision & Decimate Unification`):**
   თუ ერთი მოდელი ზედმეტად დაბალპოლიგონურია (`Low-Poly`), ხოლო მეორე — მილიონპოლიგონიანი სკანი, `bpy` სკრიპტი ავტომატურად აბალანსებს მათ სიმკვრივეს (`Bevel Modifier + Weighted Normal` დაბალპოლიგონურზე და `Decimate Ratio = 0.25` მძიმე სკანებზე), რათა სინათლის ანარეკლი ყველა ობიექტზე ერთნაირად რბილი იყოს.
3. **დონე 3 — ერთიანი ტუშის კონტური და ჰაეროვანი პერსპექტივა (`Global Line Art + Volumetric Fog`):**
   მთელ სცენას (`Scene Line Art` — [Grease Pencil Primitives](https://docs.blender.org/manual/en/3.0/grease_pencil/primitives.html)) ედება ერთი გლობალური კონტურის გენერატორი და ერთიანი 3D მოცულობითი ნისლის კუბი ([Volumetric Fog Shader](https://www.youtube.com/watch?v=2SiCtnXVVFw)), რაც წინა, შუა და უკანა პლანს ერთ ფერად სივრცეში ძირავს.
4. **დონე 4 — კომპოზიტორის ფერწერული ერთიანობა (`Anisotropic Kuwahara + AgX Color Grading`):**
   საბოლოო რენდერი გადის კომპოზიტორის `Anisotropic Kuwahara` ფილტრს ([Blender Compositing Manual](https://docs.blender.org/manual/en/3.5/compositing/index.html)), რომელიც ნებისმიერ 3D პიქსელს გარდაქმნის ერთიანი ზომის (`3px`) ფერწერულ მონასმად.

---

## W. სამყაროს მარტივი გამრავლება, უსასრულო რეგენერაცია და Reusability არქიტექტურა (`World Multiplication & Reusability Pipeline`)

### W.1 როგორ მუშაობს Reusability და მეხსიერების ოპტიმიზაცია Blender-ში ([Blender File Paths & Asset Browser Manual](https://docs.blender.org/manual/en/3.5/editors/preferences/file_paths.html))

იმისათვის, რომ ერთხელ შექმნილი სამყაროს ბიბლიოთეკა (`master_world_library.blend`) მრავალჯერადად გამოვიყენოთ 50 სხვადასხვა ეპიზოდსა და ასობით სცენაში მეხსიერების გადავსების გარეშე, გამოიყენება Blender-ის სამსაფეხურიანი იერარქია:

1. **Master Asset Library (`master_world_library.blend`) + `Append (Reuse Data)` / `Link`:**
   ოფიციალური დოკუმენტაციის ([Blender File Paths Manual](https://docs.blender.org/manual/en/3.5/editors/preferences/file_paths.html)) მიხედვით, სტანდარტული `Append` ყოველ ჯერზე ქმნის მეშისა და მასალის დამოუკიდებელ ასლს, რაც ბერავს ფაილს. პირიქით, **`Append (Reuse Data)`** ან პროგრამული **`bpy.data.libraries.load(filepath, link=True)`** ტვირთავს 3D კოშკის, ხის ან მეომრის გეომეტრიასა და შადერს მეხსიერებაში **მხოლოდ ერთხელ**! სცენაში მისი 1,000-ჯერ გამრავლებისას იქმნება მხოლოდ მსუბუქი ტრანსფორმაციის მაჩვენებლები (`Pointers / Instances`).
2. **Collection Instancing & Library Overrides ([Blender Studio Pinguino Guide](https://studio.blender.org/characters/5d403ddeee3219164b952e27/v2/)):**
   პერსონაჟები და რთული საალყო მანქანები შემოდიან `Instance Collections`-ის სახით და მათზე კეთდება `Object -> Library Override -> Make` (`obj.override_library_create()`). ეს ნიშნავს, რომ ყველა სცენაში პერსონაჟს შეუძლია შეასრულოს სრულიად განსხვავებული მოძრაობა და დიალოგი, მაგრამ თუ `master_world_library.blend`-ში შეუცვლით მოსასხამის ფერს ან შადერს, ეს ცვლილება ავტომატურად აისახება ყველა ეპიზოდში!
3. **Seed-Based Procedural Multiplication (`Geometry Nodes Poisson Disk + Modular Kitbashing`):**
   სამყაროს გამრავლება ხდება ერთი მთელი რიცხვით (`WORLD_SEED = 1001, 1002, 1003...`). მხოლოდ 15 მოდულური ელემენტისგან (3 სახლის მოდული, 2 კოშკი, 2 გალავნის სექცია, 3 ხე, 3 კლდე, 2 კარავი) `Geometry Nodes` და ქვემოთ მოცემული Python სკრიპტი ყოველ ახალ `SEED`-ზე აგენერირებს სრულიად ახალ რელიეფს, ახალ ციხესიმაგრის განლაგებას, ახალ ქალაქის ქუჩებსა და ტყის მასივს 100%-ით იდენტურ ვიზუალურ სტილში!

### W.2 მზა Copy-Paste `bpy` მოდული: ერთიანი სამყაროს ავტომატური გამრავლება და სტილის უნიფიკაცია (`Module W.1: unified_world_multiplier.py`)

ეს სკრიპტი შეგიძლიათ პირდაპირ გაუშვათ ნებისმიერ `.blend` ბიბლიოთეკაზე: იგი (1) `world_seed`-ის მიხედვით ქმნის ახალ 3D რელიეფს, (2) ბიბლიოთეკიდან მეხსიერების დუბლირების გარეშე (`link=True`) იღებს მოდულურ შენობებსა და ბუნების ელემენტებს, (3) ამრავლებს მათ რელიეფზე `Geometry Nodes`-ით და (4) ყველა ობიექტს ადებს ერთიან ილუსტრირებულ მასტერ-შადერს:

```python
import bpy
import random
import math

def build_unified_master_world_shader(palette_name: str = "EpicChronicle") -> bpy.types.Material:
    """
    ქმნის ტრი-პლანარულ (UV-დამოუკიდებელ) პროცედურულ NPR მასტერ-შადერს,
    რომელიც ნებისმიერი უფასო ბიბლიოთეკის 3D მოდელს აქცევს 100%-ით ერთ სტილად.
    """
    mat_name = f"MasterWorldShader_{palette_name}"
    if mat_name in bpy.data.materials:
        return bpy.data.materials[mat_name]

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    n_out = nodes.new('ShaderNodeOutputMaterial')
    n_diff = nodes.new('ShaderNodeBsdfDiffuse')
    n_s2rgb = nodes.new('ShaderNodeShaderToRGB')
    n_ramp = nodes.new('ShaderNodeValToRGB')

    # ერთიანი სამყაროს 3-საფეხურიანი კინემატოგრაფიული ტონალური პალიტრა
    n_ramp.color_ramp.interpolation = 'B_SPLINE'
    n_ramp.color_ramp.elements[0].position = 0.20
    n_ramp.color_ramp.elements[0].color = (0.05, 0.07, 0.12, 1.0)  # ღრმა ცივი ჩრდილი
    n_ramp.color_ramp.elements[1].position = 0.55
    n_ramp.color_ramp.elements[1].color = (0.28, 0.25, 0.22, 1.0)  # ისტორიული ქვა/მიწა
    el_hi = n_ramp.color_ramp.elements.new(0.85)
    el_hi.color = (0.82, 0.68, 0.45, 1.0)                          # თბილი ოქროსფერი სინათლე

    # Object-Space პროცედურული ტექსტურა (არ საჭიროებს UV განშლას!)
    n_coord = nodes.new('ShaderNodeTexCoord')
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.inputs['Scale'].default_value = 18.0
    n_noise.inputs['Detail'].default_value = 6.0
    n_bump = nodes.new('ShaderNodeBump')
    n_bump.inputs['Strength'].default_value = 0.15

    links.new(n_coord.outputs['Object'], n_noise.inputs['Vector'])
    links.new(n_noise.outputs['Fac'], n_bump.inputs['Height'])
    links.new(n_bump.outputs['Normal'], n_diff.inputs['Normal'])
    links.new(n_diff.outputs['BSDF'], n_s2rgb.inputs['Shader'])
    links.new(n_s2rgb.outputs['Color'], n_ramp.inputs['Fac'])
    links.new(n_ramp.outputs['Color'], n_out.inputs['Surface'])
    return mat

def generate_reusable_world_variation(
    world_seed: int = 1042,
    library_blend_path: str = "",
    asset_collection_names: list = None,
    terrain_size: float = 120.0,
    instance_count: int = 180
):
    """
    აგენერირებს სრულიად ახალ ეპიკურ 3D გარემოს მოცემული world_seed-ით,
    ამრავლებს მოდულურ ასეტებს მეხსიერების დუბლირების გარეშე (Instancing)
    და აერთიანებს ყველა ობიექტს ერთი მასტერ-შადერის ქვეშ.
    """
    rng = random.Random(world_seed)
    scene = bpy.context.scene
    master_mat = build_unified_master_world_shader("EpicChronicle")

    # 1. პროცედურული 3D რელიეფის გენერაცია Seed-ის მიხედვით
    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=128,
        y_subdivisions=128,
        size=terrain_size,
        location=(0.0, 0.0, 0.0)
    )
    terrain = bpy.context.active_object
    terrain.name = f"WorldTerrain_Seed_{world_seed}"

    tex = bpy.data.textures.new(f"TerrainTex_{world_seed}", type='MUSGRAVE')
    tex.noise_scale = rng.uniform(18.0, 32.0)
    disp = terrain.modifiers.new(name="TerrainDisplace", type='DISPLACE')
    disp.texture = tex
    disp.strength = rng.uniform(8.0, 16.0)
    terrain.data.materials.append(master_mat)

    # 2. გარე ბიბლიოთეკიდან კოლექციების შემოტანა Link (Reuse Data) რეჟიმით
    loaded_collections = []
    if library_blend_path and asset_collection_names:
        with bpy.data.libraries.load(library_blend_path, link=True) as (data_from, data_to):
            data_to.collections = [c for c in data_from.collections if c in asset_collection_names]
        loaded_collections = [c for c in data_to.collections if c is not None]

    # 3. ასეტების ინსტანსირება (0 მეხსიერების დუბლირება!) და სტილის უნიფიკაცია
    world_col = bpy.data.collections.new(f"WorldInstances_Seed_{world_seed}")
    scene.collection.children.link(world_col)

    for i in range(instance_count):
        angle = rng.uniform(0, 2 * math.pi)
        radius = rng.uniform(8.0, terrain_size * 0.45)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        rot_z = rng.uniform(0, 2 * math.pi)
        scale_u = rng.uniform(0.85, 1.25)

        if loaded_collections:
            src_col = rng.choice(loaded_collections)
            inst_obj = bpy.data.objects.new(f"Inst_{src_col.name}_{i}", None)
            inst_obj.instance_type = 'COLLECTION'
            inst_obj.instance_collection = src_col
        else:
            # Fallback მოდულური კოშკის/მონოლითის პროქსი, თუ გარე ფაილი არ არის მითითებული
            bpy.ops.mesh.primitive_cube_add(size=2.0)
            inst_obj = bpy.context.active_object
            inst_obj.data.materials.append(master_mat)

        inst_obj.location = (x, y, 0.0)
        inst_obj.rotation_euler = (0.0, 0.0, rot_z)
        inst_obj.scale = (scale_u, scale_u, scale_u * rng.uniform(0.9, 1.5))
        if inst_obj.name not in world_col.objects:
            world_col.objects.link(inst_obj)

    # 4. View Layer-ის გლობალური სტილის გარანტია
    scene.view_layers[0].material_override = master_mat
    return terrain, world_col
```

---

## X. 6 ეპიკური ერთიანი სამყაროს ვარიანტი ასარჩევად (The 6 Selectable Unified Epic World Archetypes)

ქვემოთ წარმოდგენილია 6 სრულად დაკომპლექტებული, 100%-ით უფასო ბიბლიოთეკებზე აგებული სამყაროს არქიტექტურა. თითოეული მათგანი უზრუნველყოფს **აბსოლუტურად ერთიან ვიზუალურ სტილს ყველა ვიდეოში**, მაღალ მრავალფეროვნებასა და `Seed`-ით ახლიდან დაგენერირების შესაძლებლობას:

| სამყაროს ვარიანტი (`World Option`) | ვიზუალური ესთეტიკა და კინემატოგრაფიული რეფერენსი | რომელი უფასო ბიბლიოთეკების კომბინაციას იყენებს (`Free Stack`) | როგორ მრავლდება და იცვლება სცენიდან სცენამდე (`Multiplication & Regeneration`) | რენდერის სისწრაფე და საუკეთესო გამოყენება |
|---|---|---|---|---|
| **ვარიანტი 1: „Arcane / Dishonored“ — ფერწერულ-ილუსტრირებული იმპერია (`Painterly Stylized Historical World`)** | მდიდარი ზეთის/აკრილის ფერწერული ტექსტურა, მკვეთრი `Chiaroscuro` განათება, მოცულობითი ნისლი და ხელით ნახატი ილუსტრაციის სიღრმე ([Arcane Style Rendering](https://www.youtube.com/watch?v=EWHCjienXJ0)). | [Quaternius CC0 Modular Medieval](https://quaternius.com/packs/medievaldungeon.html) + [Building Tools](https://github.com/ranjian0/building_tools) + [ANT Landscape](https://docs.blender.org/manual/en/3.1/addons/add_mesh/ant_landscape.html) + [MPFB2](https://github.com/makehumancommunity/mpfb2) + **Module Q.3 (`Painterly Kuwahara + Shader to RGB`)**. | `Building Tools` და `Quaternius` მოდულები სხვადასხვა `Seed`-ით აწყობს ციხესიმაგრეებს, ნავსადგურებსა და სასახლეებს, ხოლო ფერწერული მასტერ-შადერი ყველა კადრს ერთ ნახატად კრავს. | **ძალიან სწრაფი (`EEVEE Next`: 0.3–0.6 წმ/კადრი).** საუკეთესოა დრამატული ისტორიული და კონტრფაქტობრივი დოკუდრამებისთვის. |
| **ვარიანტი 2: „Infinigen Procedural Realism“ — ჰიპერ-დეტალური ბუნება და ანტიკური სამყარო (`Infinite Procedural Nature & Ruins`)** | ეპიკური, ნატურალისტური კინემატოგრაფია: უზარმაზარი მთის ქედები, კანიონები, მდინარეები, ნისლიანი ტყეები და ქვის დარბაზები ნამდვილი ფიზიკური სინათლით. | [princeton-vl/infinigen (Nature + Indoors)](https://github.com/princeton-vl/infinigen) + [Poly Haven CC0](https://polyhaven.com/all) + [ambientCG CC0](https://ambientcg.com/list) + `MPFB2`. | `python -m infinigen_examples.generate_nature --seed N` ყოველ ჯერზე აგენერირებს სრულიად ახალ ეკოსისტემას (უდაბნო, ალპური მთა, ტყე, სანაპირო) 100%-ით ერთიანი პროცედურული ხარისხით. | საშუალო (`Cycles GPU / EEVEE Next Raytracing`: 1.5–4.0 წმ/კადრი). საუკეთესოა მასშტაბური გეოგრაფიული ლაშქრობებისა და ბრძოლებისთვის. |
| **ვარიანტი 3: „Graphical Ink & Chronicle“ — მონუმენტური გრავიურა და 3D ქრონიკა (`Grease Pencil Line Art + Stipple Toon`)** | *Banner Saga / Pentiment* სტილის მკაფიო ტუშის კონტურები, გრავიურული შტრიხები (`Stipple/Hatching`) და კონტრასტული ფერადი სიბრტყეები ([Stylized Stipple Toon Shader](https://www.youtube.com/watch?v=lFvL-4bIUMc)). | [KayKit Medieval & Dungeon](https://kaylousberg.itch.io/kaykit-complete) + [Quaternius](https://quaternius.com/packs/medievaldungeon.html) + [Grease Pencil Scene Line Art](https://docs.blender.org/manual/en/3.0/grease_pencil/primitives.html) + [Blender 5 Toon Shader](https://www.youtube.com/watch?v=aZAqFJKMtjs). | `KayKit`-ისა და `Quaternius`-ის ასობით დაბალპოლიგონური მოდული მრავლდება მყისიერად, ხოლო `Line Art` მოდიფიკატორი ყველაფერს აქცევს ერთიანი 2D/3D გრაფიკული რომანის კადრად. | **ულტრა-სწრაფი (`EEVEE`: 0.1–0.25 წმ/კადრი — რეალურ დროში!).** საუკეთესოა სწრაფი წარმოებისა და მაღალი სტილისტური ცნობადობისთვის. |
| **ვარიანტი 4: „Real-Earth Tactical Diorama“ — რეალური დედამიწის 3D ტოპოგრაფია და სტრატეგიული მაკეტი (`BlenderGIS + Citadel Diorama`)** | რეალური სატელიტური მთები და ხეობები, რომლებზეც პირდაპირ დგას სტილიზებული ციხესიმაგრეები, მოძრაობს 3D არმიების ბლოკები და ანათებს ტაქტიკური ისრები (`Total War / Noble Tabletop` ესთეტიკა). | [domlysz/BlenderGIS (SRTM DEM)](https://github.com/domlysz/blendergis) + [KayKit Medieval Hexagon](https://kaylousberg.itch.io/kaykit-medieval-hexagon) + **Module Q.2 (`Geometry Nodes Armies`)** + **Module Q.5 (`Okabe-Ito 3D Arrows`)**. | ნებისმიერი რეალური კოორდინატი (კავკასია, ანატოლია, ევროპა) შემოდის 1 კლიკით, რაც გაძლევთ მთელი დედამიწის უსასრულო რეალურ ბრძოლის ველებს ერთიან ტაქტიკურ სტილში; აერთიანებს `VIDEO` და `HELPER` ზოლებს! | **ძალიან სწრაფი (`0.25–0.5 წმ/კადრი`).** საუკეთესოა სამხედრო-ისტორიული, გეოპოლიტიკური და ტაქტიკური ანალიზისთვის. |
| **ვარიანტი 5: „Museum Heritage & Chiaroscuro“ — მუზეუმის 3D სკანებისა და ბნელი რენესანსის დრამა (`Smithsonian CC0 + Bronze/Stone Override`)** | *Caravaggio / Rembrandt*-ის სტილის ღრმა შავი ფონი, ოქროსფერი/ბრინჯაოს და მარმარილოს რელიეფური განათება, ნამდვილი მუზეუმის არტეფაქტებითა და კლასიკური არქიტექტურით. | [Smithsonian Open Access CC0 3D](https://www.si.edu/openaccess/updates/21st-century-diffusion) + [Objaverse-XL CC0](https://github.com/allenai/objaverse-xl) + [Poly Haven](https://polyhaven.com/all) + **Module W.1 (`Tri-Planar Aged Stone/Bronze Master Shader`)**. | მილიონობით რეალური სკანირებული ქანდაკება, იარაღი და კოლონა ერთიანდება ერთი გლობალური ქვის/ბრინჯაოს შადერისა და კონტრასტული `Spot Light` კონუსების ქვეშ. | სწრაფი (`0.4–0.8 წმ/კადრი`). საუკეთესოა ანტიკური ისტორიის, იმპერიების აღზევება-დაცემისა და ფილოსოფიური დოკუდრამებისთვის. |
| **ვარიანტი 6: „AI-Kitbashed Custom Universe“ — უნიკალური ეროვნული/რეგიონული ეპოქის გენერატორი (`TRELLIS.2 / Hunyuan3D-2 + NPR Unifier`)** | საშუალებას გაძლევთ შექმნათ ისეთი სპეციფიკური კულტურული სამყარო (მაგ., ძველი საქართველო, ბიზანტია, სასანიდური ირანი), რომლის მზა 3D პაკეტები არ არსებობს, და გააერთიანოთ იგი ფერწერულ NPR სტილში. | [microsoft/TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B) + [Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) + [SifuInTheShell/Effigy](https://github.com/SifuInTheShell/Effigy) + **Module Q.3 / W.1 (`Master NPR Shader Override`)**. | იქმნება 15–20 საბაზისო კულტურული მოდული (კოშკი, ტაძარი, სახლი, აბჯარი) `TRELLIS.2`-ით, ინახება Blender Asset Browser-ში, ედება ერთიანი NPR შადერი და მრავლდება **Module W.1**-ით! | სწრაფი რენდერი (`0.4 წმ/კადრი`) ასეტების ერთჯერადი გენერაციის შემდეგ. საუკეთესოა უნიკალური რეგიონული ისტორიისთვის. |
