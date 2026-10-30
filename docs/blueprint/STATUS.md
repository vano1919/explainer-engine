# STATUS: the Blueprint rewrite (the one status table)

Moved into the repository by P0b (it was in the project files). The tables below are **generated** from `phases.json` and
`decision_queue.json`; edit those, then run `python -m explainer_engine.governance status --write` (a test refuses a stale
table). Plan: `blueprint_2026-10-29/BLUEPRINT_PLAN_v2_ka.md` in the project files; routing standard: `config/model_routing.json`
(D6/D7, [OR-29](../ORCHESTRATION.md)).

States: todo / doing / review / done / blocked. One phase = one thread = one draft PR; an S2+ PR is reviewed by another thread.
A phase in review/done needs its line in `routing_log.jsonl` (model, effort, level, result); `python -m explainer_engine.governance log`
appends it, and the Stop hook refuses to end the turn without it. Creator-owned cards are asked in one message and never
answered by Claude without his recorded delegation.

## Phases

<!-- generated:phases -->
| ID | Title | Depends on | Routing | Wave | Thread | PR | State | Waits for |
|---|---|---|---|---|---|---|---|---|
| P0a | რეპოს ჰიგიენა | — | S1 / Sonnet / medium | 1 | — | #32 merged | done | — (D2 კი) |
| P0b | Plane 1 საკეტები + governance + model_routing.json | — | S2 / Sonnet / high (hook-დიზაინი Opus high); გაშვებულია Opus high (კოორდინატორი) | 1 | cmsg_01Hnu5zB86sjUj5GtTgaUkPWYaBuVJnMoMV8ioZLDf9DXr | #30 merged | done | — |
| P0c | აგენტური სისტემის უფასო A/B (ნაპოლეონი 1–6) | — | S2 / Sonnet / medium; კრიტიკოსი Opus high | 2 | — | #35 merged | done | — |
| P1a | RunPod stop-გზების სისწორე | — | S3 Opus high (დიზაინი) → S2 Sonnet high; გაშვებულია Opus high | 1 | [P1a](#cmsg_01Hnu5zB86sjUj5GtTgaUkPW2PaTTJGAo9cuV2gtDJDzHp) | #29 merged | done | ვანო: Sonnet high-ზე გადართვის სიტყვა; GitHub secret HF_TOKEN (watchdog-ის heartbeat); D9 მოგვიანებით (არ ბლოკავს); RUNPOD_API_KEY secret არსებობს; დიზაინი მზადაა: docs/CLOUD_RUNBOOK.md, CR-01..16 |
| P1b | RunPod dryrun + cloud_pins | P1a | S2 / Sonnet / high | 2 | — | #46 merged, #49 merged | done | — |
| P1c | RunPod აღრიცხვა, job_speeds, ამომრჩევი, RP-01..10 | P1a | S2 / Sonnet / high | 2 | — | #48 merged | done | — |
| P2 | კონტრაქტები, state machine, shot cache, ledger, severity | — | S3 Opus high → S2 Sonnet high; გაშვებულია Opus high | 1 | [P2](#cmsg_01Hnu5zB86sjUj5GtTgaUkPWUKsq2ggmTdyfCuprDHMLhZ) | #31 merged | done | — |
| P3b | პროფესიული კურიკულუმი (სკილები, craft_checklists) | — | S2 Sonnet (კვლევა) → S3 Opus high (ტექსტი) | 3 | — | #36 merged | done | — |
| P4b | ხმის დირექტორი (ბატარეა, რეესტრი; კონექტორი, REST არა) | P2 | S2 / Sonnet / high | 3 | cmsg_01Hnu5zB86sjUj5GtTgaUkPWVCDmSdPHFKoz1Q5YLQxGKZ | #45 merged, #50 merged | done | cross-review (plan thread); D9 spend_caps casting_credits_max (the creator, before P12a) |
| P5 | კომპენსატორი, რუკები, HUD | P2, P3b | S2 / Sonnet / high | 3 | — | #47 merged | done | — |
| P3 | სცენარის ხერხემალი + variant_plan + register_lint | P2, P3b | S2 / Sonnet / high (ქულები Opus) | 4 | — | #40 merged | done | — (A5 = D-79) |
| P4 | აუდიო-ხერხემალი + sound director | P3, P2, P3b | S3 Opus high → S2 Sonnet high | 4 | — | #51 merged | done | cross-review (plan thread); the creator's admission word and blind A/B answer before any free generator is used (D8, BP-162); the free measurement run after the merge |
| P5b | წამყვანების სამყარო (უფასო ნაწილი) | P2, P5, P4b | S3 Opus high → S2 Sonnet high | 4 | — | — | todo | — |
| P6 | shot router, lane-ები, continuity (D-82) | P2, P5, P4, P3b | S3 Opus high → S2 Sonnet high | 5 | — | — | todo | — |
| P9 | Shorts პლატფორმისთვის + captions | P3, P7, P2 | S2 / Sonnet / medium–high | 5 | — | — | todo | — |
| P7 | სტეიჯინგი, ფინიშინგი, OTIO, safe_zones | P6, P4, P2 | S2 / Sonnet / high | 6 | — | — | todo | — |
| P8 | QA: editorial_review, identity, retry router | P7, P6, P4b, P3b | S3 Opus high → S2 Sonnet high | 6 | — | — | todo | — |
| P10 | დისტრიბუცია (unlisted, პაკეტები) | P9, P8, P2 | S1–S2 / Sonnet / medium | 6 | — | — | todo | — |
| P11 | ორკესტრატორი dry-run + აგენტები A5-ით | P8, P10, P0b, P0c | S3 Opus high → S2 Sonnet high | 7 | — | — | todo | P0c-ის ანგარიში |
| P12a | ცოცხალი smoke ≤ $0.50 | P1a | S3 Opus xhigh (გეგმა) → Sonnet high | 2 | — | — | blocked | ვანო: კონსოლის 1, 3; OR-23/24 |
| P12d | drills (უფასო, P12a-ს პოდზე) | P1a, P12a | S2 / Sonnet / high | 2 | — | #44 merged | done | P12a |
| P12b | ორი გაშვება ერთ პოდზე ≤ $2.50 | P12a, P5, P6, P1c | S3 Opus xhigh → Sonnet high | ფული | — | — | blocked | P12a; OR-23/24 |
| P12e | sheet-ები + turnaround + ფირფიტები ≤ $1 | P5b, P5, P12b | S3 Opus xhigh → Sonnet high | ფული | — | — | blocked | P12b; OR-24; კოლაჟი ვანოსთვის |
| P12c | პილოტი: ნაპოლეონი ხელახლა, ჭერებში | P11, P12b, P12e | S3 Opus xhigh (OR-23) → Sonnet high; სიუჟეტი Fable high ვანოს სიტყვით | ფული | — | — | blocked | ყველა ფაზა; OR-15/17/19/24 |
<!-- /generated:phases -->

## Decision cards (35)

<!-- generated:cards -->
| ID | Owner | Question | Answer |
|---|---|---|---|
| A1 | creator | ვიდეოებში მუდმივი წამყვანები (analyst/compass) გვინდა? | კი, 2.5D ფიგურა (ვანო) |
| A2 | claude | 3D blocking (Blender) და LivePortrait/MuseTalk გეგმაში შევიდეს? | არცერთი კოდში v2-ში (claude) |
| A3 | claude | პერსონაჟების ხმა როგორ იყოს? | ნარატორი+LTX (claude) |
| A4 | claude | რუკები და HUD რა სტილით დავხატოთ? | ორივე ფენით (claude) |
| A5 | creator | Blueprint-ის 7 დეპარტამენტი-აგენტი როგორ ავიღოთ? | D-79 (ერთი მთავარი აგენტი + ერთი read-only Opus კრიტიკოსი) (claude, delegated by ვანო) |
| B1 | claude | პოდის დასრულებისას default stop იყოს თუ terminate? | stop + ხარჯი (claude) |
| B2 | creator | ~50 გაჩერებულ პოდს რა ვუყოთ? | open |
| B3 | claude | პოდის Docker image როგორ ჩავკეტოთ? | digest pin (claude) |
| B4 | claude | $2.50-იანი ექსპერიმენტი (3 კადრი) რას შეამოწმებს? | ორი გაშვება ერთ პოდზე ≤ $2.50 ჯამში (claude) |
| B5 | creator | ფასიანი ფაზები (smoke test, ექსპერიმენტი, პილოტი) როდის? | ამ თვეში (ვანო) |
| C1 | creator | არხის rebrand @CrossWorldHistory გვინდა? | open |
| C2 | creator | GTA 6 ვიდეო დავმალოთ (unlisted)? | open |
| C3 | claude | Shorts-ის ხანგრძლივობა რამდენი იყოს? | პლატფორმაზე (claude) |
| C4 | claude | ეპიზოდის სტრუქტურის რომელი პროფილები ავაგოთ? | ოთხივე (claude) |
| C5 | claude | 16:9 ვიდეოში სუბტიტრების აკრძალვა (Mayer) შევიდეს? | REVIEW-დ (claude) |
| C6 | claude | TikTok-ზე ატვირთვის კოდი გვინდა? | არა ახლა (claude) |
| C7 | claude | Instagram Reels-ზე ატვირთვის კოდი გვინდა? | არა ახლა (claude) |
| C8 | creator | რა სიხშირით გამოვიდეს ვიდეოები? | open |
| C9 | claude | პილოტის თემა რა იყოს? | ნაპოლეონი ხელახლა დაწერილი (V4) (claude) |
| D1 | claude | კონტრაქტები jsonschema-ზე დარჩეს თუ Pydantic-ზე გადავიდეთ? | jsonschema (claude) |
| D2 | creator | .chatgpt/ საქაღალდეს რა ვუყოთ? | წაშლა (ვანო) |
| D3 | claude | OTIO ექსპორტი (მონტაჟის ფაილი) გვინდა? | ექსპორტად (claude) |
| D4 | claude | რამდენი კოდირების სრედი იმუშაოს ერთდროულად? | ≤3 (claude) |
| D5 | claude | ფაზებზე რომელი მოდელი იმუშაოს? | v2 სტანდარტით (S0–S4) (claude) |
| C10 | creator | არხის ნარატორის ხმა რჩება (Grandpa Spuds Oxley)? | open |
| C11 | creator | xworld_v2-ის ბაზა (Qwen-Image-2.1, research licence) რჩება? | რჩება, პერფორმანსისთვის (ვანო) |
| D6 | creator | MODEL_ROUTING v2: 14 კლასის ცხრილი + ინსტრუქციის მე-7 პუნქტი + „სიუჟეტური სტადიები Fable high მხოლოდ შენი სიტყვით“ — ვამტკიცებთ? | კი (ვანო) |
| D7 | claude | config/model_routing.json — ერთი სახლი მოდელი/effort წყვილებისთვის? | კი (claude) |
| D8 | creator | D-52-ის შესწორება: ნარატორი ElevenLabs REST-ით (იგივე hook/ledger) და ბიბლიოთეკის მუსიკა/SFX უფასო გენერატორებით (ACE-Step 1.5 MIT, Stable Audio Open) ElevenLabs-ის წინ? | პირობით: უფასო გენერატორი მხოლოდ გაზომილი ხარისხით; ნარატორი კონექტორით (ვანო) |
| D9 | creator | spend_caps.json-ში ორი ახალი ხაზი: casting_credits_max (ElevenLabs კრედიტები) და ბალანსის წესი (RunPod ბალანსი < X → create უარი)? | ჯერ უფასო ნაბიჯები; ფულის ხაზები და კონსოლი მოგვიანებით (ვანო) |
| V2 | claude | წამყვანები ნარატორის ხმით ლაპარაკობენ (ცალკე ხმები არა) | თანხმობა (დუმილი) (claude) |
| V3 | claude | ED-04-ის ერთი გამონაკლისი: wipe მხოლოდ უხილავი ჭრისთვის (ოკლუზია) | თანხმობა (დუმილი) (claude) |
| V4 | claude | პილოტი = ნაპოლეონი ხელახლა დაწერილი ახალი ხერხემლით | თანხმობა (დუმილი) (claude) |
| V5 | claude | ფასიანი ტესტი = OR-19-ის sample-ის პირველი ნაჭერი | თანხმობა (დუმილი) (claude) |
| V6 | claude | LT-69-ის მონაცემები რჩება; ხელახალი სწავლება არა | თანხმობა (დუმილი) (claude) |
<!-- /generated:cards -->

## Waves (at most 3 threads at once, D4)

1. P0a + P0b, P1a, P2
2. P0c, P1b, P1c (+ P12a after the P1a merge, OR-23/24; P12d with it)
3. P3b, P4b, P5
4. P3, P4, P5b
5. P6, P9
6. P7, P8, P10
7. P11
8. money, inside the caps: P12b, then P12e, then P12c

## Console list (the creator, before P12a)

RunPod spend limit $80/h to about $5/h; low-balance e-mail; restricted API key plus the GitHub secrets
`RUNPOD_API_KEY_RESTRICTED` and `HF_TOKEN`; the ElevenLabs key in the environment; a phone screenshot of one Short for the safe zone (BP-29).
