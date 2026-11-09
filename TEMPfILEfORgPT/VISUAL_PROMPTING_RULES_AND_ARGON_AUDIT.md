# ვიზუალური პრომპტინგი: წესები, არგონის აუდიტის პრომპტი, Qwen-ის გასათვალისწინებელი (2026-11-07)
შედგენილია კოდიდან და დოკუმენტებიდან (ბრენჩი `icw/20-pilot-envs`): `qa/style_prompt.py`, `blender/pilot_stills.py`, `scripting/shot_prompt_lint.py`, `docs/SHOT_PROMPTS.md`, `docs/UNIVERSAL_RULE_BASE.md`. კოდის შემოწმება ვთქვი "კოდი" ან "მხოლოდ დოკუმენტი"; რასაც არ ვამოწმებ, ისე წერია.

## 1. რომელი წესები ზღუდავს ვიზუალურ პრომპტინგს

ჩვენი მარშრუტი: **Blender სურათი (სივრცე) → Qwen-Image-2.1 + xworld_v2 LoRA (სახე, edit რეჟიმი) → LTX (მოძრაობა)**. პრომპტი **გროვდება შოტის ბარათიდან** (`pilot_stills.prompts`), ხელით არ იწერება.

### A. Qwen-ის პრომპტი (6 სატესტო ფოტო)
| წესი | რას ითხოვს | შემოწმება |
|---|---|---|
| A1 / LT-65 | იწყება trigger-ით `xworld style`, ერთხელ | კოდი (FAIL) |
| A2 | Qwen-Image-2.1, LoRA xworld_v2 checkpoint 3000, წონა 0.7, bf16, 30 ნაბიჯი, true_cfg 4, 1280×720 | კონფიგი (`INFERENCE`) |
| A3 | უარყოფითი პრომპტი ზუსტად: `text, lettering, letters, words, watermark, signature, photo, 3d render` | კონფიგი |
| A4 | 40-150 სიტყვა (შენი ზოლი, 11-06 12:27); პილოტის სურათი ≤90 (QWEN_MAX_WORDS, Fable 11-06); ბრბოს სცენა >90 = REVIEW | კოდი |
| A5 | caption tail (STYLE_TAIL) არ არის | კოდი (REVIEW) |
| A6 | კამერა, კადრის ზომა, პოზიცია, ზომა/რიცხვი სიტყვებში არ არის, განლაგებას Image 1 (Blender) ატარებს | კოდი (REVIEW) |
| A7 | ყოველი ფიგურის სრული ტეგი ერთხელ, მერე მოკლე არსებითი სახელი | კოდი (`pilot_stills`, ContractError) |
| A8 / LT-66 | სხვა მედიუმი/სტილი არ არის (photo, 3d, anime, watercolour, cinematic...) | კოდი (FAIL) |
| A9 | ეპიზოდის სტილი ამატებს მხოლოდ ფერს/სინათლეს, A1-A8-ს ვერ ცვლის | მხოლოდ დოკუმენტი |
| A10 / KG-22 | ყოველი სურათი ადარდება დამტკიცებულ eras ფურცელს | შეჩერებულია (D-80) |
| DULL | "flat/overcast/dull/grey light", "empty white" ფერს რეცხავს | კოდი (REVIEW) |
| ბარათი | პრომპტში მხოლოდ `in_shot` სახელები; ბარათში უცხო სახელი, ტეგის გარეშე სახელი, ორჯერ ნახსენები ტეგი = შეცდომა; პრეფიქსი "Image 1 is the scene: keep every place, size and pose." | კოდი |
| KP-15/01 | თითო გმირს ერთი ხილული ტეგი, ≥2 ნიშანი, ყველა პრომპტში სიტყვასიტყვით; შიშველი როლი ("the man") არა | ნაწილობრივ კოდი |
| KP-02, 13, 32 | ერთი მთავარი მოქმედი პირველად, დანარჩენები პატარა რეაქცია; მოქმედი გმირი კადრში დიდია (≈1/3 სიმაღლე) | კოდი (shot_prompt_lint) / დოკუმენტი |
| KP-22, 23, 46 | ისტორიის სახელები არა, ხარისხის სიტყვები და წაკითხვადი ტექსტი არა, AI-რეგისტრი არა | KP-22/23 კოდი, KP-46 დოკუმენტი |
| KP-31, 33, 34, 44, 45 | ყველა რაღაცაზე დგას; მიმართება ერთი მხრიდან; თავისუფალი სივრცე მოქმედებისთვის; **არასოდეს ვასახელებთ, რაც არ უნდა იყოს**; ყველა მომენტში, ვიღაც რეაგირებს | მხოლოდ დოკუმენტი |
| KP-09, 10, 14 | უარყოფითი არ ასახელებს ჩვენს სტილს; სტილს ატარებს trigger და ერთი ფიქსირებული წინადადება; სატესტო პრომპტი მოდელს ამოწმებს, არა პრომპტს | KP-09/10/14 კოდი |

### B. Blender სურათი (Image 1)
- **SO-14** (შენი, 11-06 15:53): სურათში მხოლოდ ის, რაც მისი კლიპის მოქმედებას ან ადგილს სჭირდება (`in_shot`), კედელი/იატაკი/ცა ყოველთვის. კოდი (`world_kits.dress`).
- **D-96 შესწორებული** (შენი, 11-06): Qwen = სახე, Blender = სივრცე/გეომეტრია, LTX = მოძრაობა. გმირის ფურცლები "flat ambient lighting, no cast shadows".
- ერთი და იგივე ნაკრები, საგნები და cast ყოველ კადრში; იცვლება მხოლოდ კამერა (ეს ტესტში ზუსტად დაცულია: ორ მიდგომას შორის განსხვავებაა მხოლოდ ადგილის აწყობა).
- ახალი პერსონაჟი/გარემო = ჯერ ვარიანტების კოლაჟი შენთვის (invariant 6).

### C. LTX-ის პრომპტი (ამ ტესტში არ გამოიყენება, ბარათი მას მაინც აგენერირებს)
- KP-04 ერთი კამერის წინადადება ("Static camera."); KP-10/24 ერთი ფიქსირებული სტილის წინადადება, "smooth/fluid/natural motion" აკრძალულია; KP-11 ≤3 ხმა; KP-12 / KP-16 დასაწყისი, პიკი, დასასრული სხეულის ნაწილებით, პირველი კადრი = დასაწყისი; KP-25 მხოლოდ ცვლილება; KP-03 გმირი კადრში რჩება (+ "everyone stays in frame"); KP-21 ქულა/მუსიკა არა; KP-47 ცხელ ზონაში სწრაფი მოქმედება; KP-49 / BP-172 კლიპი 3-6 წმ; BP-139 8k+1 კადრი; BP-184 LTX ≤15 %. შემოწმება: `shot_prompt_lint` (KP-00..12, 14, 17, 18, 21-25, 47, 49).

### D. ძველი მარშრუტი (სტატიკური სურათების ეპიზოდები, D-43), ჩვენზე არ ვრცელდება
UR-16..UR-29 (stakes, ერთი სამყარო UR-22, სამყაროს სიზუსტე UR-23, ბრტყელი ადგილი UR-20, ერთი სინათლის გასაღები UR-26...) `docs/UNIVERSAL_RULE_BASE.md`-შია და ანიმირებულ ეპიზოდს არ ეხება (UR-22/UR-25-ში ეს ცალსახად წერია).

### რეალური შემოწმება ამ ტესტზე
6 სატესტო Qwen პრომპტი (81, 81, 78, 78, 85, 85 სიტყვა) `pilot_stills.prompts`-მა და `qa/style_prompt.check`-მა გაიარა FAIL/REVIEW-ის გარეშე. `shot_prompt_lint`-მა დამატებით სამ **LTX** პრომპტზე იპოვა: "walking out" მამონტებზე (KP-03 FAIL) და "everyone stays in frame"-ის უქონლობა (3 REVIEW). ბარათის settle ტექსტი გავასწორე.

## 2. არგონის აუდიტის პრომპტი (ჩასაკოპირებლად, ინგლისურად)

```
You are a technical reviewer of a solo creator's AI animation pipeline. Audit ONE part of it: how the visual prompts and
their rules are built and whether the system that enforces them actually works. Use the web and cite sources (title, URL, year,
type: official docs / paper / community report / my reasoning). Mark every claim you could not verify. Do not invent numbers.

PIPELINE (this part only)
1. A Blender scene (a layout of flat-toned primitives or CC0 models plus rigged low-poly characters) is rendered to ONE still per shot.
   The still holds only what the shot's clip needs (an "in_shot" list). It carries places, sizes and poses.
2. Qwen-Image-2.1 + a style LoRA ("xworld_v2", checkpoint 3000, weight 0.7, bf16, 30 steps, true_cfg 4, 1280x720, negative prompt
   "text, lettering, letters, words, watermark, signature, photo, 3d render") restyles the still in multi-image EDIT mode:
   Image 1 = the Blender still, optional Images 2.. = hero reference sheets. The prompt is composed by code from a "shot card".
3. The restyled picture is the first frame of an LTX-2.5 image-to-video clip (3-6 s, native audio).

PROMPT RULES WE ENFORCE (Qwen keyframe/edit prompt)
- Starts with the LoRA trigger "xworld style", once. 40-150 words allowed, pilot stills at most 90 words.
- No camera words, shot sizes, positions, measurements or numbers in the words (layout lives in Image 1).
- Every figure is described once by one fixed tag with at least two visible traits ("the old sorcerer in a deer-antler mask and a fur
  cloak"); later mentions use the short noun. Only objects that are in the shot are named.
- No other medium or style words (photo, 3d, anime, watercolour, cinematic), no quality words, no readable text, no story names,
  no colour-washing light words (flat, overcast, dull, grey light).
- Never name what must be absent. Name the light source once. Place and era once.
- Prefix: "Image 1 is the scene: keep every place, size and pose."
LTX rules: one fixed style sentence, one camera sentence ("Static camera."), a start-peak-settle action with body parts, "everyone
stays in frame", at most three sounds, no score music, never ask for smooth/fluid motion, clip 3-6 s, 8k+1 frames.

A SAMPLE OF THE GENERATED PROMPTS (cave scene, then ice scene)
QWEN: "xworld style, Image 1 is the scene: keep every place, size and pose. The old sorcerer in a deer-antler mask and a fur cloak
speaks by a hearth fire, the young courier in a grey hoodie and white sneakers stares at a wall painted with gold towers and red
handprints, the hunter in grey fur, the hunter in brown fur and the hunter in spotted fur kneel, in a dark ice-age cave, lit by the
orange glow of a hearth fire."
QWEN: "xworld style, Image 1 is the scene: keep every place, size and pose. The big woolly mammoth with long curved tusks on the left,
the woolly mammoth in the middle and the small woolly mammoth on the right walk across the snow while the young courier in a grey
hoodie and white sneakers stands with his back to us, in a wide snow plain at dusk in the ice age, lit by a low cold blue dusk glow."

OUR TEST (why we ask)
We build the same three scenes two ways and send both to Qwen with the SAME prompt, seed and settings, so only Image 1 differs:
(block) every place is flat-toned primitives; (cc0) the place is built from CC0 models (rock faces, boulders, a fire pit, trunks) on a
textured ground. Story props, cast and camera are identical. We want the way that gives Qwen the better start, then write it as a rule.

QUESTIONS
1. Edit-mode behaviour: how does Qwen-Image-2.1 / Qwen-Image-Edit-2509/2511-class models treat Image 1 when it is a flat, untextured
   blockout versus a textured render? Does "keep every place, size and pose" hold, or does the model redraw shapes? What do
   practitioners report about edit strength, structure preservation, and the role of the LoRA weight (0.7) here?
2. Prompt rules: which of our rules above are supported by evidence for Qwen-Image edit mode, which are folklore, which contradict
   the model's published guidance? In particular: "no camera or layout words" in EDIT mode, one tag per figure said once, never
   naming absent things, banning words like "overcast", and the 90-word cap.
3. Does a style LoRA at weight 0.7 interact badly with multi-image edit conditioning (identity, colour, lighting drift)?
4. Blockout input: known failure modes (the model copying primitive silhouettes, flat colours leaking into the result, clone
   figures in groups, lost kneeling or seated poses) and mitigations (depth/edge conditioning, noise or strength settings,
   prompt wording, lighting in the blockout, a cheap pre-pass).
5. LTX-2.5 image-to-video from a stylised first frame: is "everyone stays in frame", "Static camera", a fixed style sentence and a
   start-peak-settle action supported by the LTX documentation or community tests? Anything missing from our list?
6. Overall: list the five most likely ways this exact part of our system will silently produce bad pictures although every
   lint passes, and one cheap test for each.

OUTPUT: for each question (1) answer in at most 8 lines, (2) the evidence with source type, (3) verdict: supported / unsupported /
unknown, (4) one concrete change to our rules or code. End with a one-page checklist. Say which links you opened yourself.
```

## 3. Qwen-ის 6 ფოტოს გენერაციისთვის გასათვალისწინებელი
1. **სამართლიანი ტესტი:** ერთი და იგივე პრომპტი, seed, LoRA, ნაბიჯები, ზომა; განსხვავება მხოლოდ Image 1-შია. ორივე მიდგომის პრომპტი სიტყვასიტყვით ერთია (შეამოწმე: `sa_prompts.json`).
2. **პარამეტრები A2-დან:** ზუსტად ის, რაც `p15.json`-ში ზის (წონა 0.7, 30 ნაბიჯი, true_cfg 4, 1280×720, უარყოფითი A3). ამის გარეთ ერთი ახალი პარამეტრიც ტესტს ამახინჯებს.
3. **გმირების ფურცლები არ არსებობს** (მარკუსი, ურა, მონადირე ახალი პერსონაჟებია, invariant 6: ჯერ კოლაჟი): ამ ტესტში Image 2+ არ იქნება, გმირს ტეგი და Blender-ის პოზა განსაზღვრავს. პირის იდენტობა ტესტით არ მოწმდება.
4. **ბლოკაუტის რისკი:** Qwen-მა შეიძლება პრიმიტივების სილუეტი (კუბური მამონტი, კონუსი-ცეცხლი) შეინარჩუნოს ან ბრტყელი ფერები გადაიტანოს; პირიქით, CC0 ქვები ზედმეტად ზუსტად აკოპიროს. სწორედ ამას ვადარებთ; ორივეს მოაქვს რისკი, ამიტომ ვუყურებთ ხელით და ვწერთ.
5. **ჯგუფის კლონები:** სამი მუხლმოდრეკილი მონადირე და სამი მამონტი ბრბოს რისკია (ბრბოს REVIEW ზღვარი 90 სიტყვაა, ჩვენი 78-85 ზღვარს ქვემოთაა). ტეგები სხვადასხვაა (ფერი, მხარე).
6. **სინათლის სიტყვები:** "overcast" და "grey light" აკრძალულია (ფერს რეცხავს); პრომპტში "cold blue dusk glow" წერია, მაგრამ Blender-ის სურათი warm-ია (preset `overcast_day`): Qwen ამ წინააღმდეგობას დაინახავს. თუ ცივი ფერი გვინდა, preset უნდა შეიცვალოს (ჩემი ვარაუდი, არ გამომიცდია).
7. **ფაქტობრივი ბაზა (SC-11 / invariant 5):** მამონტი, მღვიმე, ხელის კვალები ფიქციის ნაწილია; ტექსტში "wall painted with gold towers" ორიგინალური სიუჟეტია, რეალური ხელოვნების ასლი არა.
8. **ქლიშე-გაფრთხილება** (`shot-visuals` ცხრილი): "გამოქვაბული, მამონტი, ხელკეტი" ძველ ეპიზოდებში სტოკ ასოციაციად ჩაითვალა; ჩვენი ისტორია ზუსტად ამაზეა, ამიტომ ვუყურებთ, ხომ არ ხატავს მოდელი ხელკეტს/ბეწვის ბიკინს სტოკად.
9. **ფასი და მიღება:** 6 სურათი Qwen-ის ერთი ჩატვირთვა + 6 დახატვა ≈ 10-14 წთ A100 ≈ $0.5-0.7 (შეფასება, ჩემი გაანგარიშება: 26 სურათი/28 წთ + ჩატვირთვა; ზუსტი გაზომვა არ მაქვს). ფასიანია, ამიტომ ჯერ OR-23 გეგმა და შენი "კი"; `RUNPOD_API_KEY` ამ გარემოში არის, Modal-ის ტოკენი არა.
10. **შედეგის შეფასება წესად გადასაწერად:** ყოველ ფოტოს ვუყურებთ ერთმანეთის გვერდით (block / cc0): (ა) ინახავს თუ არა ადგილს და პოზებს, (ბ) ტექსტურის ხარისხი, (გ) სტილი, (დ) კლონები/დეფექტები, (ე) რომელი ახლოსაა ჩვენს სტილთან. შემდეგ წესი: რომელი მიდგომა რა ტიპის გარემოს, თუ ერთი მიდგომა ყველგან.
