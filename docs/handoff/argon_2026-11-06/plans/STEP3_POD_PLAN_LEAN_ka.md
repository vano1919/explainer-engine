# English summary (added for the Argon handoff; the Georgian text below is the original)

The step-3 pod plan (OR-23, 2026-11-06 17:05 Tbilisi), after the creator's rule (16:59): "tests are tests; neither the whole scale nor all
combinations; every run must answer: what will this give me?" Every item has a question and what is learned.

Facts it stands on: identity holds across environments with a reference (CLIP .78-.82, measured on the asset pod); 90 words keep the
look but give clones in crowds; 150 words not yet tried; LTX speed at 1920x1088 not measured (`job_speeds` empty); Union-Control exists
only on LTX-2.3, Layout-To-Render only on LTX-2.5 (two bases = two tools).

Runs: A Blender layout passes on the pod CPU (battle 2 clips x 145 frames: colour, depth, line fore/mid; duel 121 frames clay);
B line drawing -> Qwen edit (does Qwen keep Blender's proportions and layout?); C a 150-word prompt on D4_rain and D2_duel (does style
hold, do crowd clones vanish?); D BiRefNet cut-outs 3 heroes x 4 angles (are alpha edges clean enough for 2.5D cards?); E1 J4 battle on
LTX-2.5 Layout-To-Render with colour pass; E2 on LTX-2.3 Union-Control canny + depth; E3 same with clean line; E4 clip 2 continued from
clip 1 (8 shared frames); E5 J2 duel LTX-2.5 clay; F speed measurement. 5 LTX clips, 4 Qwen pictures, 12 cut-outs. Upscale not on
the pod (free FFmpeg on the PC). Estimate $4-7 on a Blackwell 96 GB card, proposed caps $7 / 3 h. Deleted as not answering a question:
second seed, c2 on both bases, upscale on all clips, repeating the identity test, 4 line scenes instead of 2.
What happened (from `handoffs/` and `stages.txt` of pod 1, 14:27-14:43 UTC): A.duel ok; A.frame0 failed; B skipped (it needs A.frame0);
qwen1, C and X6.still ok (see `images/step3_qwen_150.jpg`); A.battle was started and its log has no result line; D (cut-outs) failed
(a dtype error, `cutout_report.json`); no E (LTX) line exists. Not verified: why the log stops there.

---

# ნაბიჯი 3: ერთი მოკლე ტესტ-პოდი (OR-23 გეგმა, პროექტი) — 2026-11-06 17:05 თბილისი

ვანოს წესი (16:59): „ტესტები ტესტებია; არც აფსკეილი ყველაფერს, არც ყველა კომბინაცია; ყველა რანზე კითხვა: ეს რას მომცემს?“
ამიტომ ყოველ პუნქტს აქვს **კითხვა** და **რას ვიგებთ**. რასაც კითხვა არ აქვს, წაშლილია (ბოლო ცხრილი).

## 0. ფაქტები, რაზეც გეგმა დგას
- იდენტობა რეფერენსით გარემოს ცვლისას ინარჩუნებს (დღევანდელი პოდი, CLIP .78–.82). ხელახლა არ ვტესტავთ.
- 90 სიტყვა სტილს ინარჩუნებს, ბრბოში კლონებს აძლევს. 150 ჯერ არავის უცდია.
- LTX-ის სიჩქარე 1920x1088-ზე **გაზომილი არ არის** (job_speeds ცარიელია): ეს თავად ერთი შედეგია.
- Union-Control მხოლოდ LTX-2.3-ზეა; Layout-To-Render მხოლოდ LTX-2.5-ზე. ორი ბაზა = ორი სხვადასხვა ხელსაწყო, არა „კომბინაცია“.

## 1. რას ვუშვებთ (თანმიმდევრობით; ყოველი შედეგი ჩაწერისთანავე იტვირთება HF-ზე, OR-33)

| # | რანი | კითხვა | რას ვიგებთ | რაოდენობა |
|---|---|---|---|---|
| A | Blender პასები პოდის CPU-ზე: ბრძოლა S02-02 2 კლიპი×145 კადრი (ფერი, სიღრმე, ხაზი fore/mid), დუელი S03-02 121 კადრი (clay) | — (ეს ტესტი არ არის, LTX-ის შემავალია; ამ მანქანაზე მეხსიერება არ ეყო) | პასები HF-ზე, drift-ის გარეშე | 1 |
| B | ხაზოვანი კადრი → Qwen-2.1 edit (შენი იდეა): დუელის და ბრძოლის layout-ის 1-ლი კადრი, გმირის ფურცლით | **ინარჩუნებს თუ არა Qwen Blender-ის პროპორციებს/განლაგებას, როცა ხაზოვან ნახატს აძლევ?** | კი/არა + რამდენად (ხაზის დამთხვევა %) | 2 სურათი |
| C | 150-სიტყვიანი პრომპტი: D4_rain (ერთი ფიგურა) და D2_duel (ბრბო) | **150-ზე სტილი რჩება? ბრბოში კლონები 150-ზე ქრება თუ რჩება?** | ზოლის ზედა ზღვარი ფაქტით | 2 სურათი |
| D | Cutout (BiRefNet) 3 გმირი × 4 რაკურსი | **ალფა-კიდეები საკმარისად სუფთაა 2.5D ბარათებისთვის?** (PC-ზე J5-ს სჭირდება) | 12 PNG + კიდის ზომა | 12 |
| E1 | J4 ბრძოლა c1, LTX-2.5 + Layout-To-Render, ფერის პასი, seed 42 | **2.5-ის Layout LoRA ინარჩუნებს ბრბოსა და სტილს ფერადი პასიდან?** | 1 კლიპი 6 წმ | 1 |
| E2 | J4 ბრძოლა c1, LTX-2.3 + Union-Control, canny(ფერი)+სიღრმე, seed 42 | **2.3-ის Union canny-თ ინარჩუნებს?** (E1-თან შედარება = ბაზის არჩევა) | 1 კლიპი | 1 |
| E3 | J4 ბრძოლა c1, LTX-2.3 + Union-Control, ხაზი fore/mid + სიღრმე, seed 42 | **სუფთა ხაზი (ფონის ბრბოს გარეშე) უკეთესია canny-ზე?** (E2-თან) | 1 კლიპი | 1 |
| E4 | J4 ბრძოლა c2 გაგრძელება c1-დან (8 საერთო კადრი), იმავე ბაზაზე, რომელიც E1/E2-ში უკეთესია — გადაწყვეტა პოდის შიგნით ვერ მოხდება, ამიტომ **E1-ის ბაზაზე** (2.5) | **ორი კლიპი ერთ სცენად იკვრება? (BP-108 15 წმ სცენა)** | კი/არა, ნაკერის ხილვადობა | 1 |
| E5 | J2 დუელი S03-02, LTX-2.5 + Layout-To-Render, clay, seed 42 | **J2 მუშაობს ერთ-ორფიგურიან სცენაზე?** | 1 კლიპი 5 წმ | 1 |
| F | სიჩქარის გაზომვა (ავტომატური) | **რა ღირს 1 LTX კლიპი წამებში/დოლარში?** | job_speeds ltx_clip_s_per_clip | 0 |

LTX სულ **5 კლიპი** (იყო 10). Qwen სულ 4 სურათი + 12 cutout.

## 2. მოდელი და პარამეტრები (ყველა დაპინული, #144)
- Qwen-Image-2.1 bf16 + xworld_v2 ck3000 @0.7, 30 ნაბიჯი, true_cfg 4; edit რეჟიმი რეფერენსებით (B, C).
- LTX-2.5 distilled + Layout-To-Render IC-LoRA 1.0 (sha 77567d81…); LTX-2.3 distilled 1.1 + Union-Control ref0.5 (sha a1b888a8…) + Gemma 3 (ლიცენზია მიღებული). კოდი Lightricks/LTX-2 @e98f6d9.
- 1920x1088, 24 fps, 145/121 კადრი (CN-08), control strength 0.7 (E2/E3), 1.0 (E1/E5), stage-2 IC ჩართული, seed 42.
- BiRefNet @e2bf8e44.
- **აფსკეილი პოდზე არ კეთდება** (უფასოა FFmpeg-ით, PC-ზე, მხოლოდ იმ კლიპზე, რომელსაც აირჩევ).

## 3. გამოსავალი
- HF `vano1919/tmr-artifacts` → `route_test_2026-11/layouts/`, `.../step3/{qwen,cutout,ltx}/`, თითო კლიპზე sidecar (ბრძანება, წამები, sha).
- ვერდიქტის გვერდი (`qa/verdict_page`) პოდის შემდეგ, უფასოდ: ყველა კლიპი/სურათი თავისი კითხვით და რიცხვებით.

## 4. GPU, ფასი, ლიმიტები
- Blackwell RTX PRO 6000 96 GB COMMUNITY (დღეს ჩაირთო), ~$2.8/სთ; 48 GB-ზე LTX 22B არ ეტევა.
- შეფასება: ჩამოტვირთვა ~130 GB (LTX-2.5 + 2.3 + Gemma 3 + Qwen) ≈ 20–30 წთ; Blender CPU პასები ≈ 20–40 წთ; Qwen 16 სურათი ≈ 15 წთ; LTX 5 კლიპი × **უცნობი** (ვარაუდი 5–15 წთ) ≈ 25–75 წთ. სულ ≈ 1.5–2.5 სთ → **$4–7**.
- წინადადება: max-usd **$7**, ledger cap **$8.75** (80 % წესი), max-hours **3**; dead-man პოდზე, guard + beat ლოკალურად, watchdog.yml, Haiku-ს ზედამხედველი. ბალანსი $9.09 → პოდის შემდეგ ≥ $2.
- გაჩერების პირობა: ყველა რანი დასრულდა, ან კაპი, ან 2 ზედიზედ LTX წარუმატებლობა (RP-10 ერთი retry).

## 5. რას ნახავ
ერთი გვერდი: 5 კლიპი + 4 სურათი + 12 cutout, თითოეულთან კითხვა და პასუხი (რიცხვებით), სიჩქარე და ფასი თითო კლიპზე. შენ იღებ 4 გადაწყვეტილებას: J4 ბაზა, ხაზი თუ canny, 150 სიტყვა, J2 გამოდგება თუ არა.

## 6. რა წავშალე და რატომ
| წაშლილი | რატომ |
|---|---|
| მეორე seed (1337) ყველგან (−5 კლიპი) | seed-ის ვარიაცია კითხვას არ პასუხობს; ერთი ცუდი კლიპი კი ჩანს |
| c2 გაგრძელება ორივე ბაზაზე (−1) | კვერა ერთხელ იტესტება |
| აფსკეილი ყველა კლიპზე | უფასოა, მერე, მხოლოდ არჩეულზე |
| ხელახლა იდენტობის ტესტი | უკვე ფაქტია |
| 4 ხაზოვანი სცენა (B) → 2 | 2 საკმარისია კი/არა-სთვის; 4 მერე, თუ „კი“ |

## 7. რაც შენი სიტყვით უნდა გადაწყდეს (OR-22)
1. ფორმა: ერთი პოდი (ეს გეგმა) თუ გაყოფა — ბარათი ჩატში.
2. კაპი $7 / 3 სთ — კი/არა.
3. E4-ის ბაზა 2.5 (ზემოთ) — კი, თუ 2.3.
4. 150-სიტყვიანი ტესტი C — დარჩეს თუ 90-ით დავკმაყოფილდეთ.
