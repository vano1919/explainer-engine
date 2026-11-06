# English summary (added for the Argon handoff, 2026-11-06; the Georgian text below is the original and wins on any difference)

The creator's final high-level plan of 2026-11-06 11:00 Tbilisi (goal: maximum stability and quality; a 12-15 minute episode for about US$10-15).
Every unmeasured number in it is marked EST. Sections of the original: 1 principles, 2 tool roles, 3 route matrix, 4 rules in force,
5 gaps G1-G13, 6 phases 0-6, 7 questions, 8 the findings register F-01..F-40, 9 his answers.

1. **Principles.** Qwen-Image-2.1 + the xworld_v2 LoRA draws everything that is seen: scene assets (360 backdrops, heroes by angle, props)
   and the first frame of every shot; fixes by Qwen edit ("change nothing, fix this defect"). Blender builds space and time (scene,
   camera, depth, crowds, light) and animates some shots itself (2.5D cards, camera, mouth, crowds), or only supplies a drawing to LTX.
   LTX animates only where motion is really needed (battle, travel, duel, an emotional gesture, a discovery). A scene seen once: Qwen
   photo straight to LTX. A scene seen from several angles: Qwen assets, Blender assembly, angles. Dialogue: cut-out heroes on the
   same backdrop, mouth and expression by cheap Blender/Python; nobody watches one dialogue frame longer than 5 s. A pretty Blender NPR
   render is never the final picture (it failed three times: ICW-05b, ICW-05c, the night run).
2. **Routes** (D-116): J5 = Qwen assets + Blender 2.5D (no LTX, about $0); J2 = Blender clay layout, Qwen first frame, LTX
   Layout-To-Render; J4 = Blender full drawing (colour, depth, line), LTX restyle; H = Python helper graphics. Matrix by scene type:
   battle/siege V1 J4; duel V2 J2; dialogue V3 J5; council V4 J5; craft hands V5 J2 loop; travel V6 J4; discovery V7 J5; emotional
   gesture V8 J2; aftermath V9 J5; environment action V10 J5; stills S1-S7 J5; helpers H1-H6 H. The matrix is status T (a test must
   confirm), except stills and helpers.
3. **Budget (EST, before the later recount).** LTX is needed for V1, V2, V5, V6, V8 = 40-55 % of the 432 s of VIDEO, about 30-45 clips
   instead of about 90; the rest is J5 at $0 on the PC/Mac or under $1 on RunPod. LTX per clip EST $0.05-0.15 plus retries.
4. **Rules in force on every route:** speech 70 % narrator / 30 % dialogue (D-99, BP-105); dialogue at most 5 s, action 10-15 s,
   still at most 5 s, shot at least 2.5 s, 8k+1 frames on LTX (BP-108, BP-109, BP-84, BP-139); lanes 60/30/10 within 5 points (D-93,
   BP-109); format 2560x1440, 24 fps; Qwen-Image-2.1 + xworld_v2 ck3000 at 0.7 (D-80, D-83); continuity by cards and structure, never
   an img2img chain (D-75, D-78); assets from the library first (D-76, OR-18); money only per `config/spend_caps.json`, pods only via
   `cloud/runpod.py`, OR-23 plan + OR-34 audit + the creator's word for anything paid.
5. **Corrections the plan asked for (4a):** D-96 reworded to roles (Qwen look, Blender space/time, LTX motion where needed); lane mapping
   D-97; LTX rules back in force for J2/J4 only (D-105); identity carrier = Qwen hero sheet + Blender card/rig (D-101); BP-108 = scene
   length and BP-172 = one LTX clip (resolved in his answers: scene 10-15 s, LTX clip 3-6 s, limit 2-8 s).
6. **Gaps G1-G13** (rules PR, router recipes, J5 code, J4 pins, P12 pod, Mac route closed, speeds unmeasured, upscale, clip QA, a2v
   dialogue never run, identity across angles, 70/30 rewrite, unstarted WP-Q/ICW packages) and **phases 0-6** (answers, rules PR,
   free build incl. J5 dialogue and layouts, paid test of J2/J4/a2v, one-page verdict, roadmap rewrite, pilot = first two parts by D-67).
7. **His answers (11:14 Tbilisi):** D-96 corrected by roles: yes; V1/V2/V6 one LTX generation 3-6 s, longer scenes by cuts or chained clips;
   BP-108 and BP-172 stay at different levels; the Mac only for few-second tests, Blender = PC/Mac free, Qwen and LTX = RunPod; open: a
   cheap Qwen asset pod (about $0.3-0.5). The critique's five risks went into the plan: J5 "paper doll" (3 mouth states with a 2-frame
   cross-blend, angles with no visible mouth, flat-lit hero sheets with no cast shadows), J4 style loss on crowds (line only fore/mid),
   a free FFmpeg upscale chain in phase 3, 360 geometry (2-3 depth cards for wide moves).

---

# საბოლოო high-level გეგმა: Qwen ხატავს, Blender აწყობს და ზოგან აანიმაციებს, LTX ზოგან აანიმაციებს
**2026-11-06, 11:00 თბილისი. მიზანი: მაქსიმალური სტაბილურობა და ხარისხი; 12–15 წთ ეპიზოდი ≈ $10–15.**

წყაროები: ჩვენი საუბარი დღეს 09:40–10:56; Opus-ის LTX gap review და Qwen/LTX/Blender review (11-06); LoRA სრედის სტატუსი (11-06);
სამუშაო ბრენჩი `icw/05c-ink-round` (a3f1e1f): decision log D-40..D-115, `sourced_rules.json`, `visual/archetypes_ic.json`,
Opus-ის ბრიფი + direction + roadmap (11-04), craft report (11-04), legacy დოკუმენტები (SHOT_PROMPTS, SHOT_CONTINUITY,
KEYFRAME_GATE, LORA_TRAINING, SCRIPT_ENGINE, ASSET_COMPOSE). ყველა გაუზომავი ციფრი **EST**. ბოლოში ფაინდინგების რეესტრი (F-01..F-40):
თითოეულს აქვს ადგილი გეგმაში.

---

## 1. პრინციპი (შენი სიტყვები დღეს)

1. **Qwen-Image-2.1 + xworld_v2 ხატავს ყველაფერს, რაც ეკრანზე ჩანს:** სცენის ასეტები (360° ფონი, გმირები რაკურსით, რეკვიზიტი) და თითო შოთის პირველი კადრი. შესწორება Qwen-ის edit რეჟიმით: „არაფერი შეცვალო, ეს ხარვეზი გაასწორე“.
2. **Blender აწყობს სივრცესა და დროს:** სცენა, კამერა, რაკურსები, სიღრმე, ხალხი, განათება. ზოგან **თვითონვე აანიმაციებს** (2.5D ბარათები, კამერა, პირი, ხალხი), ზოგან მხოლოდ **ნახაზს** აძლევს LTX-ს.
3. **LTX აანიმაციებს მხოლოდ იქ, სადაც მოძრაობა მართლა სჭირდება:** ბატალია, მგზავრობა, დუელი, ემოციური ჟესტი, აღმოჩენა.
4. **სცენა, რომელიც ერთხელ ჩანს:** პირდაპირ Qwen ფოტო → LTX. **სცენა რამდენიმე რაკურსით:** Qwen ასეტები → Blender აწყობა → რაკურსები.
5. **დიალოგი:** ამოჭრილი გმირები + იგივე ფონი, პირი და მიმიკა იაფად Blender/Python-ით; LTX მხოლოდ თუ იაფი ვერ გამოვა. 5 წმ-ზე მეტს ერთ კადრს არავინ უყურებს.
6. Blender-ის „ლამაზი“ NPR რენდერი საბოლოო სურათი არსად არ არის (სამჯერ ჩავარდა: ICW-05b, 05c, ღამე).

## 2. ინსტრუმენტების როლები

| ინსტრუმენტი | რას აკეთებს | რას არ აკეთებს |
|---|---|---|
| Qwen-Image-2.1 + xworld_v2 ck3000 (0.7) | იერსახე: ასეტები, პირველი კადრები, შესწორებები (edit, რეფერენსი = გმირის sheet + clay კადრი) | მოძრაობას; უწყვეტობას სხვა შოთთან პრომპტით (D-75: უწყვეტობა ბარათებით და სტრუქტურით) |
| Blender 5.2.3 | სცენა, კამერის გრამატიკა, 360° ფონის პროექცია, 2.5D ბარათები, GN ხალხი, რიგი (Quaternius CC0), Rhubarb პირი, clay/depth/line-art pass, განათება, EEVEE რენდერი 2.5D შოთებისთვის | საბოლოო ფერწერულ იერსახეს შადერით |
| LTX-2.5 (პოდი) / LTX-2.3 q4 (Mac, გასაზომად) | Layout-To-Render (J2), restyle depth/canny (J4), a2v დიალოგი სადაც საჭიროა | ფონის/კომპოზიციის „გამოგონებას“: ყოველთვის ნახაზით ან ფოტოთი იმართება |
| Python / FFmpeg | HELPER გრაფიკა, assembly (`build_video_v2`), QA, cutout (BiRefNet), პირის ფორმების ჩანაცვლება ბარათზე | — |
| ElevenLabs | ნარატორი + გმირების ფიქსირებული ხმები (D-90), Scribe სიტყვების დრო | — |

## 3. მატრიცა: რომელი სცენისთვის რომელი მარშრუტი

მარშრუტები: **J5** = Qwen ასეტები + Blender 2.5D (LTX არა, ≈$0); **J2** = Blender clay layout → Qwen პირველი კადრი → LTX Layout-To-Render;
**J4** = Blender სრული ნახაზი (ფერი/depth/line) → LTX restyle; **H** = Python. „სტატუსი“: ✔ = უკვე დამტკიცებულ შედეგზე დგას,
T = ტესტმა უნდა დაადასტუროს.

| lane / ქვეკატეგორია (archetypes_ic) | მარშრუტი | ალტერნატივა | ხანგრძლივობა | identity-ს მატარებელი | სტატუსი |
|---|---|---|---|---|---|
| **VIDEO V1** ბატალია / ალყა / ფორმაცია | **J4** (ათასობით GN ხალხი, კამერა რელსზე) | J2 | სცენა ≤ 15 წმ (BP-108), LTX კლიპი 3–6 წმ (BP-172), მონტაჟით/ჯაჭვით | Blender სტრუქტურა + Qwen პირველი კადრი | T |
| V2 დუელი / მოქმედება | **J2** (LTX ამატებს ჟესტებს) | J4 | სცენა ≤ 15 წმ, LTX კლიპი 3–6 წმ, keypose 5 წმ | Qwen კადრი + layout | T |
| V3 დიალოგი (ხილული პირი) | **J5** (ამოჭრილი გმირი, Rhubarb პირი, 2–3 გამომეტყველება, სუნთქვა) | LTX a2v (D-90) | ≤ 5 წმ | Qwen sheet, ერთი ფოტო ყველა რაკურსზე | T (იაფი გზა) / ✔ (a2v კოდი არის, არ გაშვებულა) |
| V4 საბჭო / ჯგუფური დიალოგი | **J5** | — | ≤ 5 წმ | იგივე | T |
| V5 ხელობა (ხელები) | **J2** (ლუპი 2–5 წმ) | J5 ლუპი ბარათზე | ≤ 5 წმ | Qwen insert | T |
| V6 მგზავრობა | **J4** (dolly, parallax, ხალხი) | J5 (ბარათები + კამერა) | სცენა ≤ 15 წმ, LTX კლიპი 3–6 წმ | Blender | T |
| V7 აღმოჩენა (push-in, ნისლი) | **J5** (Blender კამერა + ნისლი ბარათებზე) | J4 | მოკლე | Blender | T |
| V8 ემოციური ჟესტი | **J2** | J5 (2–3 პოზა) | ჟესტის სიგრძე | Qwen კადრი | T |
| V9 შედეგი (კვამლი, ნელი ციკლები) | **J5** (Blender კვამლი + ბარათები) | J4 | ≤ 15 წმ | Blender | T |
| V10 გარემოს მოქმედება (ნისლი, მზე) | **J5** (Blender ნისლი/სინათლე 360° ფონზე) | — | ≤ 15 წმ | Blender | T |
| **STILL S1–S7** (establishing, ტაბლო, insert, aftermath, match, freeze) | **J5**: Qwen plate → Blender კამერა / parallax / BP-170 მრუდი | — | ≤ 5 წმ (BP-109) | Qwen 360°/plate | ✔ (+dpl 10-27, parallax კოდი არის) |
| **HELPER H1–H6** (რუკა, timeline, counter, cutaway, შედარება, callout) | **H** Python (D-87: 2D ვექტორი + 2.5D) | Blender ტერეინი მხოლოდ ბენჩმარკით (D-112) | ნარატორის წინადადება | — | ✔ |

**შედეგი ბიუჯეტზე (EST):** VIDEO-ს 432 წმ-დან LTX-ს სჭირდება V1, V2, V5, V6, V8 ≈ 40–55 %, ანუ ~30–45 კლიპი ეპიზოდში (ნაცვლად ~90-ისა);
დანარჩენი J5 Mac-ზე $0 ან RunPod-ზე < $1. LTX თითო კლიპი EST $0.05–0.15 + ცდები → ეპიზოდი $3–8 LTX + Qwen ასეტები $1–2 + ნარატორი.

**სტაბილურობის წესები მატრიცისთვის (უკვე არსებული):** ერთი 360° ფონი თითო ადგილზე (+dpl); გმირი ერთი sheet-იდან, რაკურსი ამოჭრით და
Qwen edit-ით, არასდროს ხელახალი ხატვა ნულიდან (ინვარიანტი 6, D-101-ის პრინციპი); შოთის ხელახალი გამოყენება zoom/crop-ით, როცა სკრიპტი
იმავე რაკურსს უბრუნდება (შენი 10-25-ის წესი); გენერირებული შოთი არასდროს ხდება მომდევნოს ბაზა (D-78); ზედიზედ 3 VIDEO = REVIEW (KP-48).

## 4. წესები, რომლებიც ძალაშია (ყველა მარშრუტზე)

| ღერძი | წესი | წყარო |
|---|---|---|
| ხმა | 70 % ნარატორი / 30 % დიალოგი, REVIEW 65–75 %; ნარატორი საათია; გმირის ხმა ფიქსირებული, ჯერ იკითხება, მერე კონდიციონირებს კლიპს | D-99/BP-105, D-88, D-90 |
| ხანგრძლივობა | დიალოგი ≤ 5 წმ; მოქმედება 10–15 წმ, არ იჭრება ხელოვნურად; still ≤ 5 წმ; შოთი ≥ 2.5 წმ; 8k+1 კადრი LTX-ზე | BP-108, BP-109, BP-84, BP-139 |
| lane-ები | 60/30/10 ±5 პპ, იზომება წამებით, სიტყვებისგან დამოუკიდებლად | D-93/BP-109, D-98 |
| რიტმი | MrBeast 5 ზონა, ერთი ნარატორი ტემპოს ცვლილებით; hyped ზონაში მოკლე კლიპები | D-94, BP-169, BP-171, BP-172 |
| ფორმატი | 2560×1440, 24 fps, 12 წთ, 5 Shorts | BP-167, D-85, D-104 |
| მოდელი | Qwen-Image-2.1 + xworld_v2 ck3000 0.7; wldnk_* და 2512 აკრძალული; ლიცენზია არ ბლოკავს | D-80, D-83 |
| უწყვეტობა | მხოლოდ სტილი ისწავლება; უწყვეტობა ბარათებით + სტრუქტურით; edit რეფერენსებით კი, img2img ჯაჭვი არა | D-75, D-78, CT- ბარათები |
| ასეტები | ბიბლიოთეკა ჯერ, ახალი მხოლოდ საჭიროებისას; ლიცენზია ყოველ ასეტზე ჩაწერილი, არ ბლოკავს | D-76, D-110, D-83 |
| ფული | caps მხოლოდ `spend_caps.json`; პოდი მხოლოდ `cloud.runpod`; OR-23 გეგმა + OR-34 აუდიტი + შენი სიტყვა ფასიანზე; Mac და CI უფასოდ ავტომატურად; watchdog ყოველ ფასიან რანზე; ნაბიჯ-ნაბიჯ შენახვა | D-56, D-111, D-113, D-114, OR-33 |
| პროცესი | სინთეზი არსებული კოდიდან, ნულიდან არაფერი; Opus გეგმავს, Sonnet აკეთებს; ვერდიქტი შენი კლიპებზე, არა სურათებზე | D-115, OR-26, შენი 11-05 |

### 4a. წესები, რომლებიც ICW-01-მა Blender-ზე გადაწერა და ახლა უნდა შესწორდეს (ერთი PR, უფასო)
- **D-96:** „Blender = საბოლოო პიქსელები“ → „Qwen იერსახე, Blender სივრცე/დრო, LTX მოძრაობა სადაც საჭიროა; მარშრუტი სცენის ტიპით (ნაწილი 3)“. **შენი სიტყვით.**
- **D-97 lane mapping:** VIDEO_3D → VIDEO (J2/J4/J5 მარშრუტით), STILL_3D → STILL (J5), HELPER იგივე.
- **D-105:** LTX-ის წესები (BP-100/101/102/110/139/164/165/172) „legacy“-დან ისევ აქტიურში J2/J4 შოთებზე; J5 შოთებზე არა.
- **D-101:** identity-ს მატარებელი = Qwen გმირის sheet + Blender ბარათი/რიგი (ორივე).
- **BP-108/BP-109 ტექსტი:** რენდერერ-ნეიტრალური; ციფრები იგივე.
- **ბანერები** 5 დოკუმენტზე: „legacy“ → „ტესტის ქვეშ, J2/J4/J5-ის მიხედვით“.
- **`style_prompt.INFERENCE["lora"]`** None → xworld_v2 0.7 (D-83-ის შესაბამისად).

### 4b. შიდა წინააღმდეგობა, შენი გადასაწყვეტი
BP-172 (11-01): LTX კლიპი hyped ზონაში 2–4 წმ, შუაში 4–8 წმ. BP-108 (11-04): მოქმედება 10–15 წმ. ჩემი წაკითხვა: BP-108 ახალია და
იმარჯვებს (D-77); 12-წამიანი ბატალია შუა ზონაში კი, hyped ზონაში კლიპები მოკლე. **დაადასტურე ან შეცვალე.**

## 5. რა გვაკლია (Opus-ის სია + დღევანდელი)

| # | ნაკლი | რომელ მარშრუტს ეხება | ვინ ავსებს |
|---|---|---|---|
| G1 | D-96-ის შესწორება და lane mapping (4a) | ყველა | შენი სიტყვა → Sonnet PR |
| G2 | router film_shots/3 → `ltx_i2v` რეცეპტი და ახალი `assemble_25d` რეცეპტი | J2/J4, J5 | ICW-07 |
| G3 | J5 კოდი: Qwen ასეტების სია თითო სცენაზე (ფონი 360°, გმირები რაკურსით, რეკვიზიტი), BiRefNet cutout, Blender პროექცია + ბარათები, Rhubarb პირი ბარათზე, გამომეტყველების sheet; ASSET_COMPOSE-ის ძველი კოდი საძირკვლად | J5 | ახალი პაკეტი (ICW-11) |
| G4 | J4 pin-ები: LTX-2.3 Union-Control / Wan VACE, sha, smoke; depth/canny/line pass Blender-იდან | J4 | ICW-07 |
| G5 | P12 პოდი: 3 sha ხაზი, HF code upload, DRY gate | J2 | WP-1e |
| G6 | Mac მარშრუტი კოდში არ არის (MLX, LTX-2.3 q4, Qwen-2.1 MLX შეუმოწმებელი) | გასაზომად | Mac სრედი, შენი OK ~30 GB |
| G7 | სიჩქარე/ფასი: `job_speeds` ცარიელი; M4 Pro არ გაზომილა; LTX თითო კლიპი უცნობი | ყველა | ტესტი |
| G8 | upscale 2560×1440-მდე LTX კლიპებისთვის; ინსტრუმენტი არ არის არჩეული (roadmap 8.2 DEFER) | J2/J4 | ბენჩმარკი |
| G9 | QA LTX კლიპებზე: identity, flicker, LT-32 jitter არ გაშვებულა; RenderValidator Blender-ზეა | J2/J4 | ICW-08b |
| G10 | a2v დიალოგი (D-90) არასდროს გაშვებულა; ხმის თანმიმდევრობა კლიპებს შორის ღიაა | V3 fallback | ტესტი |
| G11 | Qwen identity რაკურსებს შორის: 10-25-ის cutout გზა მუშაობდა, 10-27-ის +dpl ფონი მუშაობდა, paintover დაუდასტურებელი; ჩაკრული ჩრდილები → Blender განათებით გადასაჭრელი | J5 | ტესტი |
| G12 | craft report-ის blueprint 75/25-ზეა, 70/30-ზე გადასაწერი; archetypes_ic-ის 12 ატრიბუტი HYP, კამერის/გადასვლის არჩევანი ვიწრო (შენი 10:25-ის კითხვა) | გეგმარება | Opus გეგმა |
| G13 | WP-Q2/Q3/Q5/Q6/Q9/Q10 და ICW-06/07/09/10 არ დაწყებულა; Blender-ის ნაწილები (კამერა, ხალხი, სამყარო, shading) J5/J2/J4-ის საძირკვლად რჩება | — | roadmap-ის გადაწერა |

## 6. ფაზები

| ფაზა | რა | ფასი | კარიბჭე |
|---|---|---|---|
| **0** | შენი პასუხები (ნაწილი 7) | — | — |
| **1 წესები** | 4a-ს ერთი PR ბრენჩზე + D-116 („მარშრუტი სცენის ტიპით“) + ნაწილი 3-ის მატრიცა `archetypes_ic.json`-ში `route` ველად + ტესტი | უფასო | Fable აუდიტი |
| **2 უფასო აგება** | (ა) J5 დიალოგი: 2 გმირი ამოჭრა, 360° ფონი, Blender ბარათები, Rhubarb პირი, 5 წმ reverse angle, Mac; (ბ) Blender clay/depth/line layout-ები ბატალიისთვის (12 წმ) და დუელისთვის (8 წმ); (გ) Mac-ზე Qwen-2.1 MLX შემოწმება | $0 (Qwen ასეტები: თუ Mac-ზე არ მუშაობს, ერთი იაფი პოდი ≈ $0.3–0.5, OR-23) | შენ უყურებ J5 კლიპს |
| **3 ფასიანი ტესტი** | პოდი: J2 (დუელი, ჟესტი) და J4 (ბატალია 12 წმ, მგზავრობა) × 2 seed; a2v ერთ დიალოგზე; LTX თითო კლიპის დრო/ფასი იზომება | EST $3–6 | OR-23 → Opus → OR-34 → შენი სიტყვა; watchdog |
| **4 ვერდიქტი** | ერთი გვერდი: J5 / J2 / J4 / ღამის J3 გვერდიგვერდ, რიცხვები (identity, პალიტრა, hold, flicker, ფასი); ნაწილი 3-ის T → ✔ ან ✘ | უფასო | შენი არჩევანი |
| **5 roadmap** | D-96 საბოლოო, ICW-07/08b/09/10/11 გადაწერა მატრიცით, ფასის მოდელი გაზომილი ციფრებით, upscale არჩევა | უფასო (Opus გეგმა) | Fable |
| **6 პილოტი** | პირველი ორი ნაწილი (D-67), ყველა მარშრუტით, შენ უყურებ, მერე დანარჩენი | OR-23 | შენი სიტყვა |

**რაც არ იცვლება:** main-ში არაფერი; ბრენჩები არ იშლება; ფასიანი ნაბიჯი სამი კარიბჭის გარეშე არა; RunPod ბალანსი 11-05: $10.17.

## 7. შენი გადასაწყვეტი

1. D-96-ის შესწორება ნაწილი 1-ის პრინციპით: კი / არა.
2. ნაწილი 3-ის მატრიცა default-ად (T სტატუსით, ტესტი ადასტურებს): კი / შეცვალე რომელიმე სტრიქონი.
3. BP-108 vs BP-172 (4b).
4. Mac-ზე ~30 GB გადმოწერა (Qwen-2.1 MLX + LTX-2.3 q4) გასაზომად: კი / არა / მერე.
5. ფაზა 2-ის Qwen ასეტებისთვის იაფი პოდი (≈$0.3–0.5), თუ Mac-ზე ვერ გავა: კი / ჯერ Mac.

## 9. შენი პასუხები და კრიტიკის ინტეგრაცია (11:14 თბილისი)

**გადაწყვეტილებები (შენი 7.1–7.4):**
- **7.1 კი:** D-96 სწორდება როლებით: Qwen იერსახე, Blender სივრცე, LTX მოძრაობა; კოდსა და წესებში დაუყოვნებლივ (ფაზა 1).
- **7.2:** V1, V2, V6: ერთი LTX გენერაცია **3–6 წმ**; გრძელი სცენა მონტაჟით ან კლიპების ჯაჭვით (J4-ში Blender-ის უწყვეტი სტრუქტურა ნაკერებს ამარტივებს: გადაფარვადი კადრები + იგივე depth; J2-ში first+last / continuation, ჯერ გაუშვებელი, F-20). მატრიცა შესწორებულია.
- **7.3:** ორივე წესი რჩება სხვადასხვა დონეზე: **BP-108 = სცენის ხანგრძლივობა (10–15 წმ)**, **BP-172 = ერთი LTX კლიპის ლიმიტი (2–8 წმ, სამიზნე 3–6)**. 4b დახურულია; ფაზა 1-ის PR ორივე ტექსტს ასე გადაწერს (`film_shots.py`: scene_max vs clip_max).
- **7.4:** Mac მხოლოდ რამდენიმეწამიანი ტესტებისთვის (სამსახურის კომპიუტერია). ჩემი შეფასება RX 5700 16 GB-ზე: Blender EEVEE **კი** (2.5D აწყობა, clay/depth/line pass-ები, J5 რენდერი, უფასოდ; D-113-ში უკვე EEVEE fallback-ად წერია); Qwen-Image-2.1 (20B) და LTX **არა** (CUDA/ROCm არ აქვს, tmr-ზე SDXL-ს 6–7 წთ უნდებოდა სურათზე). ანუ: **Blender = PC/Mac უფასოდ, Qwen და LTX = RunPod.** G6 (Mac MLX მარშრუტი) იხურება.
- **7.5 ღია:** Qwen ასეტებისთვის იაფი პოდი ≈ $0.3–0.5 (ფაზა 2): კი / არა.

**კრიტიკის 5 რისკი და რა შევიდა გეგმაში:**
1. LTX ხანგრძლივობა → 7.2/7.3-ით მოხსნილია.
2. **J5 „ქაღალდის თოჯინა“:** პირი 3 მდგომარეობით (დახურული / ნახევრად / ღია) 2-კადრიანი cross-blend-ით, არა 8 ფორმა; დიალოგის ნაწილი რაკურსებზე, სადაც პირი არ ჩანს (ზურგიდან, რეაქცია, OTS მსმენელი, უკვე V3-ის დიზაინშია); გმირის sheet-ის პრომპტი: **flat ambient lighting, no cast shadows**, რომ Blender-ის განათება ორმაგ ჩრდილს არ მისცეს. ფაზა 2(ა)-ს კრიტერიუმი: შენ უყურებ და თუ „თოჯინაა“, V3 LTX a2v-ზე გადადის (ფასი იზრდება ~15–25 კლიპით).
3. **J4 სტილი მასობრივ სცენაზე:** canny/line-art მხოლოდ წინა და შუა პლანზე; უკანა პლანის GN ჯარი depth + სილუეტის ფერით, რომ მასა ლაქებად დაიხატოს; კონტროლი 0.5–0.7. ფაზა 3-ის ბატალიის შოთი ორ ვარიანტად (სრული canny vs გასუფთავებული).
4. **Upscale ფაზა 3-შივე:** უფასო FFmpeg ჯაჭვი (lanczos → cas/unsharp → მსუბუქი grain) LTX-ის გამოსავალზე 1440p-მდე, იზომება line share / პალიტრა; AI upscale მხოლოდ თუ ეს ჩავარდა. G8 ფაზა 3-ში გადადის.
5. **360° გეომეტრია:** qwen-360 LoRA 0.8-ზე (10-25) ნაკერი გაზომილად იკვრებოდა (edge diff 8.3 vs 7.3); ფაზა 2-ში პროექციაზე ჰორიზონტის/არქიტექტურის ხაზების შემოწმება ფართო პანზე; ფართო მოძრაობაზე ფონი 2–3 ბარათად სიღრმეში (parallax), არა ერთ სფეროდ.

## 8. ფაინდინგების რეესტრი (არაფერი გამოტოვებული)

| F | ფაინდინგი | წყარო | ადგილი გეგმაში |
|---|---|---|---|
| F-01 | roadmap Blender-only, LTX legacy, გეგმა LTX-ზე არ არსებობს | Opus gap §0 | 4a, 6.5 |
| F-02 | ICW-00..05, 08, WP-Q0/1/4/7/8 DONE; 06 paused; 07/09/10, Q2/3/5/6/9/10 MISSING | Opus gap §1 | 5 G13 |
| F-03 | 70/30, BP-108, BP-167, lanes, validator რენდერერ-დამოუკიდებელია | Opus gap §2 | 4 |
| F-04 | router ltx_i2v მხოლოდ /2 | Opus gap §3 | 5 G2 |
| F-05 | pins LTX-2.5 + Layout LoRA sha null, legacy | Opus gap §3 | 5 G4/G5 |
| F-06 | clay_video + 3 კლიპი HF | Opus gap §3 | 6.2(ბ) |
| F-07 | P12 კოდი მზად, პოდი არ გაშვებულა, 3 sha | Opus gap §3 | 5 G5 |
| F-08 | AV take Raymond Verne არის | Opus gap §3 | 6.3 a2v |
| F-09 | job_speeds ცარიელი | Opus gap §3 | 5 G7 |
| F-10 | D-96-ის შესწორება შენი სიტყვით | Opus gap §4.1 | 7.1 |
| F-11 | ჯაჭვის არჩევა | Opus gap §4.2 | 3, 7.2 |
| F-12 | wldnk_* და 2512 აკრძალული (D-80); xworld_v2 ნებადართული; Mac 2512 4-bit მხოლოდ wldnk-ს ემთხვევა | Opus gap §4.4 | 4 მოდელი, G6 |
| F-13 | Mac მარშრუტი კოდში არა; 2.5 vs 2.3 | Opus gap §4.5 | G6 |
| F-14 | სიჩქარე M4 Max-ის, Pro გაზომილი არ არის; Qwen+LTX ერთად 24 GB-ში არ ეტევა | Opus gap §4.6 | G7 |
| F-15 | ეპიზოდი ≈ 90–140 LTX კლიპი Mac-ზე 5–9 სთ; upscale არ არის | Opus gap §4.7 | 3 ბიუჯეტი, G8 |
| F-16 | QA LTX-ზე არ გაშვებულა | Opus gap §4.8 | G9 |
| F-17 | a2v არ გაშვებულა, ხმის თანმიმდევრობა ღია | Opus gap §4.9 | G10 |
| F-18 | პოდის მზადყოფნა: sha, upload, DRY, OR-23, OR-34 | Opus gap §4.10 | G5, 6.3 |
| F-19 | Qwen: KG/KP წესები დახვეწილი; xworld_v2 სტილს იჭერს; 360° ფონი საუკეთესო; depth ControlNet და paintover სტილს კარგავს; identity რაკურსებს შორის გადაუწყვეტელი; 10-27-ის მერე ცდა არ ყოფილა | Opus Qwen review | 3, G11 |
| F-20 | LTX: 10 წმ მყარი, 15–20 ფუჭდება; შოთებს შორის მხოლოდ ფერის/ხაზის REVIEW; chain/multishot/first+last არ გაშვებულა | Opus review | 4 ხანგრძლივობა, G9 |
| F-21 | IC 10-24-ზე ჩავარდა მხოლოდ იმიტომ, რომ layout-ს მოძრაობა არ ჰქონდა; IC იმეორებს layout-ს | Opus review | 3 J2 |
| F-22 | 2.1-ზე edit-ით მიღებული შოთი ფონს აკოპირებს, კამერა არ მოძრაობს; grid პანელები ფონს იგონებენ → 3D layout საჭიროა | Opus review (2.1) | 1.2, 3 |
| F-23 | wldnk_qi21_v2 HF-ზეა, შედეგი არსად; D-80-ით აკრძალული | Opus + LoRA სრედი | 4 მოდელი |
| F-24 | LoRA ბრენჩი beg7xa main-შიც და icw/05c-შიც; xworld_v2 ck3000 0.7; რაუნდი 3b; 27 ოქტ.-ის მერე სამუშაო არა; `style_prompt` lora None vs D-83 | LoRA სრედი | 4a |
| F-25 | D-95/BP-108 LTX-ისთვის იყო დაწერილი: 5 წმ დიალოგი, 10–15 წმ მოქმედება, ბატალია/ჯარი ზემოდან მაგალითად | archive override | 4 |
| F-26 | BP-172 vs BP-108 წინააღმდეგობა | sourced_rules | 4b |
| F-27 | legacy ბანერები 5 დოკუმენტზე, შინაარსი ხელუხლებელი | ბრენჩი | 4a |
| F-28 | archetypes_ic: 23 ქვეკატეგორია × 12 ატრიბუტი; ხანგრძლივობები BP-108/109, დანარჩენი HYP; კამერა/გადასვლა ვიწრო; ზონები lane-ებს არ კვეთს | ბრენჩი + საუბარი | 3, G12 |
| F-29 | craft report: 20 არქეტიპი, 10 ტექნიკის ბარათი, 12-წთ blueprint 75/25-ზე | ბრენჩი | G12 |
| F-30 | წესები სამჯერ იკითხება: გეგმა → აღწერა/აგება → QA | საუბარი | 2 |
| F-31 | J1 ამოვარდა: ხალხი/identity/ცდები | საუბარი | 3 |
| F-32 | J3 ამოვარდა ცალკე გზად, საძირკვლად რჩება | საუბარი | 1.6, G13 |
| F-33 | J4 სტილის დაკარგვის რისკი: კონტროლი 0.5–0.7, canny line-art-იდან (ჰიპოთეზა) | საუბარი | 3 V1/V6, 6.3 |
| F-34 | J5 = 10-25 cutout ტესტი + 10-27 +dpl + ASSET_COMPOSE; ჩაკრული ჩრდილები → Blender განათება | საუბარი + მეხსიერება | 3, G3, G11 |
| F-35 | Blender რენდერი LTX-ზე 5–15-ჯერ იაფი; ბატალია 0.76 წმ/კადრი Mac-ზე | ღამე + საუბარი | 3 ბიუჯეტი |
| F-36 | შოთის ხელახალი გამოყენება zoom/crop-ით, 5 წმ წესი | შენი 10-25 | 3 სტაბილურობა |
| F-37 | ღამის Blender შედეგი: სტაბილური გმირები, უფასო სწრაფი რენდერი, მაგრამ იერსახე „90-იანების თამაში“ | ღამე | 1.6 |
| F-38 | Mac free runs, CI free; ფასიანი სამი კარიბჭით; watchdog; ნაბიჯ-ნაბიჯ შენახვა | D-113/114, OR-33 | 4 ფული |
| F-39 | main-ში Ink Chronicle არაფერია; ზოგადი წესების main-ში შერწყმა ღიაა | 05:55 | 6 „არ იცვლება“ |
| F-40 | D-75/D-78: უწყვეტობა ბარათებით, edit რეფერენსებით კი, img2img ჯაჭვი არა | decision log | 4 უწყვეტობა |
