# OLD_HISTORY — ყველაფერი, რაც 2026-10-29-მდე გავაკეთეთ

ვანოს თხოვნა (2026-10-29 11:03 თბილისი): ყველა ბრენჩი და PR (draft-ების ჩათვლით) გაანალიზდეს, კონფლიქტი უახლესი
მიგნებების სასარგებლოდ გადაწყდეს, ყველაფერი ერთ main-ში მოექცეს, დასამახსოვრებელი მასალა (ფოტოები, იდეები, წესები,
ძველი სრედების შედეგები) ერთ ფაილში შეინახოს, ბოლოს დარჩეს მხოლოდ main და 0 PR. ეს ფაილი არის ის ერთი ფაილი.

დიდი ბინარები (სურათები, ვიდეო, LoRA) აქ მხოლოდ ბმულით/გზით არის:
- **HF (მთავარი ასლი):** `https://huggingface.co/datasets/vano1919/tmr-artifacts` (private). ბრაუზერის ბმული ფაილზე:
  `https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/<path>`.
- **პროექტის საერთო საქაღალდე:** `/mnt/project-files/` (ჩამონათვალი: დანართი C). მისი ასლი HF-ზეც არის: `project_files/`
  (tag `vault-2026-10-24b`, 10-24-ის მდგომარეობა).
- **კოდის სრული ასლი ყველა ძველი ბრენჩით:** HF `vault/code/explainer-engine_2026-10-24.bundle`,
  `vault/code/tmr-video-script-engine_2026-10-24.bundle` (`git clone <bundle>` აღადგენს ყველა ბრენჩს 10-24-ის მდგომარეობით).
  10-24-ის შემდეგ ყველა commit ამ main-შია (ქვემოთ, ნაწილი 1).

ნაწილები: 1. რა გაერთიანდა · 2. მოქმედი წესები (უახლესი იგებს) · 3. სამუშაოს მდგომარეობა 10-29-ისთვის ·
4. მასალა და ბმულები · 5. ძველი სრედები · დანართი A: ღია სრედების ბოლო მდგომარეობა · დანართი B: პროექტის მეხსიერება
სრულად (ყველა ფაილი, სიტყვასიტყვით) · დანართი C: `/mnt/project-files` ჩამონათვალი.

---

## 1. რა გაერთიანდა (2026-10-29)

### explainer-engine

ანალიზი: 28 დისტანციური ბრენჩიდან **ყველა** უკვე იყო `claude/project-thread-beg7xa`-ის (PR #22) წინაპარი
(`git merge-base --is-ancestor` ყველასთვის true; 0 commit, რომელიც PR #22-ში არ იყო). კონფლიქტები ადრე, 2026-10-25-ს
გადაწყდა წესით „უახლესი წესი იგებს (D-77), ID რჩება პირველ განმსაზღვრელს" — სრული აუდიტი:
`docs/research/BRANCH_INTEGRATION_2026-10-25.md` (ამ main-ში). PR #22-ის ბოლო commit `5cafa84` (2026-10-27 01:06 UTC);
ტესტები 10-29-ს: `pytest -m "not system and not media"` 1218 passed, `docs_lint` 0 finding. main (`3e5673b`, PR #26
watchdog) PR #22-ის წინაპარი იყო, ამიტომ main-ში შერწყმას კონფლიქტი არ ჰქონდა.

| PR | ბრენჩი | თარიღი | რა მოიტანა | ბედი |
|---|---|---|---|---|
| #1 | phase-2-spec-pack | 10-15 | Phase 2 სპეციფიკაციები, პალიტრა, Kit | merged 10-20 |
| #2 | ccr-0d2b1961-9r63nt | 10-17 | Episode standards D-45, D-46 | merged 10-19 |
| #3 | claude/project-thread-on22x9 | 10-19 | Story engine D-48 | merged 10-19 |
| #4, #12 | systemic/next-video | 10-19/20 | next-video → main | merged 10-20; next-video-ზე შემდეგ მხოლოდ PR #13 დაემატა (PR #22-შია) |
| #5 | claude/visual-beats-layer-6m9q5g | 10-19 | Visual beats D-54, D-55 | merged |
| #6 | claude/runpod-management-ck9cm0 | 10-19 | RunPod ფულის კონტროლი D-56 | merged |
| #7 | claude/youtube-upload-cfe6z7 | 10-19 | YouTube unlisted ატვირთვა D-57 | merged |
| #8 | claude/syndicate-wars-paint-oj7rwe | 10-19 | Syndicate Wars სურათები, OR-16 | merged |
| #9 | claude/storytelling-editing-system-wc6jm1 | 10-20 | Scene rewrite D-58 | merged |
| #10, #11 | claude/system-audit-sourced-rules-3i81ai | 10-20 | Sourced rules D-59, BP რეესტრი | merged |
| #13 | claude/integrated-coherence-review-t714sv | 10-20 | D-60 editorial_review/2 | merged into next-video |
| #14 | claude/project-thread-hze0pq | 10-20..21 | სთორითელინგის მკაცრი წესები, script approval D-61..D-68 | PR #22-ში (10-25) |
| #15 | claude/asset-library-jy2g5u | 10-20 | Library first (D-63 → **D-76**) | PR #22-ში |
| #16 | claude/project-thread-i9ftf6 | 10-21 | ორნაწილიანი ნიმუში D-67 | PR #22-ში |
| #17 | claude/project-thread-unf8ud | 10-22 | სცენის უწყვეტობა D-69 | PR #22-ში; `change` კადრები D-78-მ გააუქმა |
| #18 | claude/project-thread-w8oxrk | 10-22 | Master brief D-70, World Bible, Guardian | PR #22-ში |
| #19 | claude/project-thread-engscs | 10-22 | runpod check volumes/serverless | D-74-მა ჩაანაცვლა |
| #20 | claude/project-thread-qporwm | 10-22 | ოთხი ანიმაციური სამყარო, rig PoC | ისტორიად; D-71 → D-80 |
| #21 | claude/project-thread-81jdev | 10-22..23 | ჰიბრიდული rig, Ice Age ტესტი | rig ვანომ გააუქმა 10-22 22:19 |
| #22 | claude/project-thread-beg7xa | 10-23..27 | LoRA კონტროლი D-72, keyframe gate, D-75, D-79, D-80, xworld_v2 strategy loop, OR-24..26 + ყველა ზემოთ | **main-ში 10-29** |
| #23 | claude/project-thread-6f7hqr | 10-24 | Vault D-73 | PR #22-ში |
| #24 | claude/project-thread-ubp4ge | 10-24..25 | Script engine (D-74 → **D-77**), KP-15..45 | PR #22-ში |
| #25 | claude/project-thread-9srh7j | 10-24 | REST v2 pod manager D-74 | main-ზე #26-ით |
| #26 | claude/project-thread-9srh7j-watchdog | 10-24 | watchdog + v2 pod manager main-ზე | merged 10-24 |
| #27 | claude/project-thread-tht70c | 10-25 | ერთი მთავარი აგენტი + კრიტიკოსი OR-20, D-79 | PR #22-ში |
| — | chatgpt/repo-management | 10-18 | ChatGPT workflow | main-შია |
| — | https/github.com/vano1919/explainer-engine.git | — | შეცდომით შექმნილი სახელი, PR #22-ის ზუსტი ასლი | წაიშალა |

ID-ების შეჯახება (10-25, თარიღით გადაწყდა): D-63 რჩება PR #14-ს (library first → D-76); D-74 რჩება pod manager-ს
(script engine → D-77); ST-14..16 რჩება PR #14-ს (template D → ST-17..19); CC- რჩება D-64-ს (continuity cards → CT-).

### tmr-video-script-engine (მხოლოდ ინსტრუმენტების წყარო)

| PR / ბრენჩი | თარიღი | რა არის | ბედი |
|---|---|---|---|
| #9 claude/sleepy-babbage-lh7a0m | 10-16 | guard heartbeat, `--gpu a5000`, chunked render fixes | main-ში 10-29 (PR #11) |
| #10 claude/master-directive-prompt-5rmv2y | 10-16 | Stone Age pictures-only pod jobs, likeness judge, `--min-ram`, `--gpu big` | main-ში 10-29 (PR #11); `cloud/rp.py` კონფლიქტი: ორივე GPU ვარიანტი დარჩა |
| #4 ccr-d10f50f5-92quko | 10-11 | Veo loop-ს $1.5 cap-ის მოხსნა, ყოველი სურათის ანიმაციის ფასი | დაიხურა: main-ის უახლესმა წესმა 8e2e537 („Gemini არასდროს ხატავს თემის სურათებს/Veo loop-ს") ჩაანაცვლა |
| three-hour-format-7ewyz0 | 10-11 | ძველი Shorts/owls opening ცვლილებები (PR #5 სხვა სახით შევიდა) | 10-16-ის „Clean main down to the one run"-მა ჩაანაცვლა; ძილის ფორმატი ამ პროექტში არ გამოიყენება |
| three-hour-format, cloud-bootstrap-ssh-keys, ccr-… | 10-05..11 | უკვე main-ში | წაიშალა |

ჩანაცვლებული commit-ები დარჩა HF bundle-ში `vault/code/tmr-video-script-engine_2026-10-24.bundle`.

---

## 2. მოქმედი წესები (უახლესი იგებს; სრული ტექსტი — დანართი B, `MEMORY.md` და `feedback-*.md`)

- **RULE #6 (10-27 01:58 თბ.):** ამ თვეში ახალი ფული არ არის; RunPod-ის ნაშთი (≈$3 10-27-ს) არის მთელი ბიუჯეტი.
  დანარჩენი ხარჯი და გადაწყვეტილებები სრულად Opus-დამგეგმავ სრედს აქვს მინდობილი. მიზანი: კადრების 360° კოორდინაცია
  ერთ სივრცეში (სტილი გადაწყვეტილია).
- **RULE #5 (10-27 01:42):** ყოველი გამოსწორება უნდა ერგებოდეს ნებისმიერი სცენის ზოგად ლოგიკას, არა სატესტო კადრებს;
  held-out სცენები (tundra + ახალი ადგილი) ამოწმებს გამარჯვებულს უცვლელად.
- **RULE #4 (10-26 21:06):** LoRA სრედი = შემსრულებელი; Opus სრედი წერს გეგმებს (OR-26).
- **RULE #3 (10-26 16:49):** დამოუკიდებელი Opus მიმომხილველი იღებს მთავარ გადაწყვეტილებებს; coordinator აძლევს სრულ
  ფაქტებს, ავტორის მსჯელობის გარეშე (OR-24).
- **RULE #1 (10-25 21:05 UTC):** სისტემური გადაწყვეტილება არასდროს ვარაუდზე (OR-22); დეტალური გეგმა ყოველი პოდის წინ (OR-23).
- **D-80 (10-26):** ყველა ძველი LoRA (wldnk_*) აკრძალულია; ახალი სტილი Rick and Morty-დან, Qwen-Image-2.1; 2512/Edit-2511
  გაუქმებულია. D-71 (Wild Ink) ჩანაცვლებულია. D-78: generated shot არასდროს არის შემდეგის საფუძველი.
- **D-79:** ერთი მთავარი აგენტი + ერთი კრიტიკოსი. **D-77:** ანიმაციური ეპიზოდები script engine-ით. **D-75:** მხოლოდ
  სტილის LoRA + continuity cards. **D-74:** ფული job-ზე, pods თავად ჩერდება. **D-73:** vault (HF მთავარი ასლი).
- მუდმივი: უახლესი წესი იგებს; reusability > speed (OR-21); კრიტიკული, არა თანხმობის მიმცემი; დრო თბილისით (UTC+4);
  პოდები ბოლოს გაითიშოს, წაშლა მხოლოდ ვანოს სიტყვით; საიდუმლოები არასდროს ჩატში/repo-ში; პასუხები ქართულად, მოკლედ;
  მაყურებლისთვის ყველაფერი ინგლისურად (US); საჯარო ატვირთვა მხოლოდ ვანოს დაწკაპუნებით.
- პროექტის ინსტრუქცია „სამუშაო ბრანჩი systemic/next-video" ამ გაერთიანებით შეიცვალა: ვანოს 10-29 თხოვნით რჩება მხოლოდ
  main; ახალი სამუშაო main-იდან იწყება.

---

## 3. სამუშაოს მდგომარეობა 2026-10-29-ისთვის

- **არხი:** CrossWorld Chronicles (UCndsNlyExB-jKRB9hs283BQ), STORYTELLER docudrama, 15-წთ template D, 8-15 წთ + 5 Shorts,
  საბოლოო 2K. მთავარი მიზანი: 15-წთ სრულად ანიმაციური ვიდეო ხმებით და პერსონაჟებით. ერთი გამოგონილი სამყარო, ერთი
  სტილი, მუდმივი გმირების და character LoRA-ების გარეშე.
- **Pipeline:** keyframes → LTX-2.5 ვიდეო native audio-თი → მთხრობელი → აწყობა → 2K (Wan 2.2 სარეზერვო).
- **სტილის LoRA:** xworld_v2, Qwen-Image-2.1, checkpoint 3000 სტილისთვის; cut-LoRA შეწყდა.
- **Strategy loop (10-26/27):** გეგმა `/mnt/project-files/xworld_v2/STRATEGY_LOOP_PLAN_2026-10-26.md`.
  Round 1 ($1.19): გამარჯვებული S2T 2×2 grid text-only (+S2E); depth-ControlNet უარყოფილია. Round 2, 3a, 3b — ღამე.
  **3b (+dpl, per-panel backdrop cell) = საუკეთესო მეთოდი**; paintover უარყოფილია (commit d1e268c). ბოლო commit 5cafa84:
  per-view turnaround prompts, reprojected per-shot backdrops, people rule, SDEdit noise check (Opus-ის სია 3b-ის შემდეგ).
- **ყველა რაუნდის (1, 2, 3a, 3b) 54 სურათის გალერეა ქართული ბარათებით:** https://claude.ai/artifact/C5TMq1VZsAPF7FqvNXb6zA ;
  ფაილი `/mnt/project-files/xworld_v2/gallery/index.html`.
  HF: `lora_plan_2026-10-26/train_xworld_v2/loop/round_2/out`, `round_3a/out`, `round_3b/out/loop`.
- **დასრულებული ვიდეოები:** Syndicate Wars (https://studio.youtube.com/video/JKzH8GNaaVk/edit + 10 Shorts),
  Titans (https://studio.youtube.com/video/XW8BfJdw1No/edit + 5 Shorts). ვანოს დარჩა: thumbnails, Related video,
  Public, ძველი YouTube token-ის გაუქმება.
- **სერვისები:** BFL მეორე გასაღები მუშაობს; fal-ის ბალანსი უარყოფითია; RunPod REST v1 ქრება 2026-11-15
  (კოდი უკვე v2-ზეა, D-74).

---

## 4. მასალა და ბმულები

### HF `vano1919/tmr-artifacts` (dataset, private) — ზედა საქაღალდეები 10-29-ს

`bakeoff_2026-10-23/`, `episode1/`, `eras_video_2026-10-24/`, `explainer-engine/`, `film_1min_2026-10-24/`,
`film_1min_2026-10-25/`, `footage_2026-10-23/`, `ic_test_2026-10-23{,b,c,d}/`, `inputs/`, `lora_plan_2026-10-22/`,
`lora_plan_2026-10-26/` (caption/cast/dataset/story/test/train xworld_v1 და v2), `motion_lora/`, `night_run_2026-10-22/`,
`pictures/`, `project_files/`, `refs/`, `runs/`, `scene_chain_2026-10-24/`, `scene_lora_2026-10-24/`,
`vault/` (code bundles + `VAULT_MANIFEST_full_2026-10-24.json`), `video_lora_2026-10-24/`.
10-24-ის ინვენტარი: 9 290 ფაილი, 47.8 GB; tags `vault-2026-10-24`, `vault-2026-10-24b`.

### `/mnt/project-files/` — მთავარი დოკუმენტები და სურათები (სრული სია: დანართი C)

- აუდიტები და კვლევა: `explainer-engine/AUDIT_2026-10-19/`, `SYSTEM_AUDIT_2026-10-19/`, `storytelling_research/`,
  `THUMBNAIL_RESEARCH_2026-10-19.md`, `architecture_2026-10-22/` (TOOLING_*, WORLD_BIBLE, ARCHITECTURE_PLAN),
  `dialogue_research_2026-10-26/PERSONAPLEX_ka.md`.
- იდეები: `explainer-engine/ideas/future_video_concepts_2026-10-19.md`, `future_video_concepts_v2_wild_2026-10-19.md`.
- სკრიპტები: `explainer-engine/scripts_export/` (Stone Age, Syndicate Wars, Titans), `napoleon_vs_genghis_2026-10-24/`
  (script, shotlist, prompts), `titans_from_zero/`, `syndicate_wars/`.
- სურათები/ვიდეო: `animation_universe_2026-10-22/worlds/*.jpg` (სამყაროს სტილების ვარიანტები), `ice_test/`, `rig_poc/`,
  `eras_video_2026-10-24/*.mp4` + strips, `film_1min_2026-10-24/test_v2/*.jpg`, `film_1min_2026-10-25/film/film_A_ltx_voices.mp4`,
  `lora_plan_2026-10-24/*.jpg`, `thumbnail_motif/`, `xworld_v1/` (cast, napoleon, test scenes), `xworld_v2/` (loop rounds,
  gallery, s3c, round3000).
- გეგმები: `lora_plan_2026-10-24/*_ka.md`, `film_1min_2026-10-24/SCENARIO_AND_TEST_ka.md`, `TEST_PLAN_v2_ka.md`,
  `xworld_v2/*_PLAN_*.md`, `VIDEO_PLAN_8-12min.md`, `HANDOFF_2026-10-19.md`.
- ვანოს ატვირთვები: `uploads/hearth/` (71 ფაილი, id-ებით).

### სხვა ბმულები
- RunPod ფულის დანაკარგის სტრატეგია (Claude Doc): https://claude.ai/artifact/QLw3G6BcccPN8YAREyJTMh
- ოფიციალური RunPod MCP: https://mcp.runpod.io/ (მხოლოდ read-only რჩევა; spend_caps-ს გვერდს უვლის).

---

## 5. ძველი სრედები (10-29-ის სია; დაიხურება ამ გაერთიანების შემდეგ)

| სათაური | id | მდგომარეობა |
|---|---|---|
| Explainer-engine კვლევის დანერგვა | cmsg_…41aX94yBe4Y1UYLKSdcTv1 | done |
| /deep-research | cmsg_…Ku1edpuBeo8MoHxrWf3328 | done |
| წინა სესიის გაგრძელება | cmsg_…JQgeWYBwsFcQX9icAdQ38v | done |
| სისტემის დამოუკიდებელი აუდიტი | cmsg_…BLvfz8GBe2nH4SjjTLLkgb | done |
| ვიზუალის სიხშირის ახალი ფენა | cmsg_…AEYVEPDbhBtd8UhRERUZoL | done |
| Syndicate Wars: სურათების ხატვა | cmsg_…V9veC4WvGs8nStiD9SNbBd | done |
| RunPod-ის მართვის გაძლიერება | cmsg_…K1YF8naqi3L6AEGKPpW3dZ | done |
| YouTube-ზე ატვირთვის ავტომატიზაცია | cmsg_…TquweFq5MYrT4zZAB2qcum | done |
| სთორითელინგისა და მონტაჟის სისტემა | cmsg_…UL7TbQXS2BfMeKgD1GM68Q | done |
| main-ზე შეჯამება და სისტემის სრული… | cmsg_…GPjwQc6QbHkkNnGx26soRV | done |
| სცენარიდან ვიდეომდე ხარისხის… | cmsg_…3bQthjBJVNkWYfWe6FG31e | done |
| მაიამი: 10 ტიტანი $100-ით | cmsg_…PQJwNSarDUVsXxWF7asF9W | done |
| მრავალჯერადი ასეტების ბიბლიოთეკა | cmsg_…65KAiRPQWreEFEXvhskM4n | done |
| ჯერ 2-ნაწილიანი ნიმუში | cmsg_…LcEkk1nyXTRaRCuVM9Y7o4 | done |
| სამი ვიდეოს სრული სკრიპტები | cmsg_…GHSTsLrXi11Jvtt1LY5Afm | done |
| სცენის უწყვეტობა სურათებში | cmsg_…CUfVPPykamm3ccRioP7SoY | done |
| წარმოების არქიტექტურა და ვიზუალი | cmsg_…UovaNg2qiKKZd2rFMG2Wzi | blocked |
| RunPod-ის დაკარგული თანხა | cmsg_…3bPck3pJg3EQcSFyb4fJ3F | done |
| RunPod-ის წესების ვალიდაცია | cmsg_…QtGRz3m7ipXh7M2FMwm8Wz | done |
| თხრობის მოდელი სამი რეფერენსით | cmsg_…SxvApkMnPRXY5QQAw8L7XX | done |
| ანიმაციური სამყაროს ოთხი ვარიანტი | cmsg_…9S7WVLy3RWiPNN7TQdUqhW | done |
| ჰიბრიდული მოდელი: AI ფონები, კლასიკური… | cmsg_…B2eXwuEtsFNe7oqJvvhFQb | blocked |
| ფასიანი სერვისების შემოწმება | cmsg_…NJePKMs5j4RUwwU99dwwK9 | done |
| LoRA გმირებისა და სტილისთვის | cmsg_…SkfNyJ6sMjV7fND8hnXnBr | done |
| გეგმის კრიტიკული შეფასება | cmsg_…FiCGGK7s1a6F8vCfTP7Gjg | done |
| LoRA ტრენინგის მულტი-აგენტური სისტემა | cmsg_…4ADfcyLPxkFTi1c2egJPkh | done |
| დაცვა: ნაშრომი არ დაიკარგოს | cmsg_…LuBBngNCHGXGVGjghsVVnZ | done |
| პრომპტისა და სკრიპტის წესები | cmsg_…GzQJW7j1HpwVwP6mxjAaCZ | done |
| RunPod-ზე ფულის დანაკარგის აღმოფხვრა | cmsg_…Kcwz8e5dWkVAJzffbyAjVW | done |
| შევაფასოთ 3 AI-ის სისტემის რჩევა | cmsg_…HodZyUoi59MBev74UNM8j4 | blocked |
| შევაფასოთ სტილის LoRA-ს სწავლის გეგმა (Opus) | cmsg_…8hv1TCfqHwPq38rbFSg8na | working |
| დავგეგმოთ სურათების ავტომატური QA | cmsg_…65CMb9E2Svz2ZkebV29G62 | blocked |

(id-ების სრული პრეფიქსი: `cmsg_01Hnu5zB86sjUj5GtTgaUkPW`.) თითოეული სრედის შედეგი პროექტის მეხსიერებაშია (დანართი B);
ღია/დაბლოკილი სრედების ბოლო მდგომარეობა — დანართი A.


---

## დანართი A: ღია/დაბლოკილი სრედების ბოლო მდგომარეობა (წაკითხულია 2026-10-29)

სრედის ბოლო შეტყობინებები წაკითხულია 2026-10-29 08:15 UTC-ს. მხოლოდ ის, რაც ღია/დაბლოკილი იყო ან ბოლო გეგმას ეხება.

**შევაფასოთ სტილის LoRA-ს სწავლის გეგმა (Opus მიმომხილველი, cmsg_…8hv1TCfqHwPq38rbFSg8na)**
- 10-29 07:10: ყველა რაუნდის 54 სურათის გალერეა ქართული ბარათებით: https://claude.ai/artifact/C5TMq1VZsAPF7FqvNXb6zA
  (`/mnt/project-files/xworld_v2/gallery/index.html`). გალერეაში არ არის 3000-ის ძველი კოლაჟები და S3c.
- ფურცლები: `xworld_v2/round3000/` (S2 ბადე, P2S, S3), `xworld_v2/s3c/s3c_sheet.jpg`, `xworld_v2/loop_round1/sheet_grids.jpg`
  + `round1_cards.html`, `xworld_v2/round_3b/` (კარავი, რომი, გემი, ტუნდრა; 4 ხედი + კადრები).
- HF: `lora_plan_2026-10-26/train_xworld_v2/loop/round_2/out`, `round_3a/out`, `round_3b/out/loop`.

**LoRA ტრენინგის მულტი-აგენტური სისტემა (შემსრულებელი, cmsg_…4ADfcyLPxkFTi1c2egJPkh)**
- შემდეგი გეგმა (10-27 06:36, Opus-თან შეთანხმებული, ნოემბრის ფულით; პოდამდე ყველაფერი უფასო და მზადაა):
  1. ახალი 360° turnaround: ოთხივე მიმართულება ცალკე, თითოს თავისი პრომპტით (რა ჩანს მარცხნიდან მარჯვნივ, რა არ უნდა
     ჩანდეს); რომში კოლიზეუმი 4-დან 3 ხედში იყო, კარვის ორი ხედი ცარიელი/ერთნაირი; ცუდ ხედებს მხოლოდ გადავხატავთ.
  2. +dpl ოთხივე ადგილზე, seed 11 და 23; ფონი კადრის კამერის მიმართულებით იჭრება, ორ ხედს შუა კადრი ორივედან; ხალხის
     წესი: ზუსტად N კაცი, ზურგით მდგომი ერთხელ (გემზე ორი კაპიტანი იყო).
  3. PO (paintover) ბოლოს, ხმაურის დონის ლოგით: დაუდასტურებელია.
- ბალანსი 10-27-ს $0.49; პოდები გაჩერებულია; ≈$1+ პოდი ნოემბრამდე არ ეშვება.

**დავგეგმოთ სურათების ავტომატური QA (cmsg_…65CMb9E2Svz2ZkebV29G62)**
- 10-26 12:15: გეგმა მზადაა და LoRA სრედს გადაეცა (`/mnt/project-files/xworld_v2/AUTO_QA_PLAN_2026-10-26_ka.md`): თითო ხარვეზს
  თავისი გაზომვა (ხმაური/გაჯერება, იგივე კადრი, ზედმეტი ადამიანი, ორი სახე, სახის ცვლა, ზომა, სტილი, ადგილი).
- ზღვრებს ვანოს შეფასებები ადგენს (round 0-ის 102 სურათი, ~15 წთ) — **ღიაა, ვანოს შეფასება საჭიროა**.
- ფასი: 5 checkpoint-ის შემოწმება ≈$4 (მაშინ ბალანსი $3.73) — ვანოს გადასაწყვეტი იყო. ღია: სახის/ადამიანის დეტექტორები
  მულტფილმის სახეებზე მუშაობს თუ არა (ჯერ უფასოდ შესამოწმებელი). თვალით რჩება გემოვნება, მსახიობობა, 360° ლოგიკა.

**შევაფასოთ 3 AI-ის სისტემის რჩევა (cmsg_…HodZyUoi59MBev74UNM8j4)**
- D-79/OR-20 (ერთი მთავარი აგენტი + კრიტიკოსი) შერწყმულია (PR #27); პოდი რჩება (API-ს წესი არ დაიწერა, ვანოს არჩევანი).
- **ღია:** პუნქტი 1 — ბარათებზე ფასის შეფასება ($51 vs $20), ვანოს პასუხს ელოდება.

**წარმოების არქიტექტურა და ვიზუალი (cmsg_…UovaNg2qiKKZd2rFMG2Wzi)**
- ეტაპები A-F (აუდიტი, Guardian, World Bible, ასეტების ბიბლიოთეკა, სურათის ადაპტერები, 2.5D პარალაქსი) კოდით მზადაა,
  PR #18-ის შინაარსი PR #22-ით ახლა main-შია. სტილის კოლაჟი და მოდელების პილოტი აქ არ გაეშვა.

**ჰიბრიდული მოდელი: AI ფონები, კლასიკური ანიმაცია (cmsg_…B2eXwuEtsFNe7oqJvvhFQb)**
- Layout-To-Render ტესტი (10-23): IC-LoRA მიჰყვება block მოძრაობას და ინარჩუნებს პირველი კადრის სტილს; ჩვეულებრივი
  LTX I2V თავისას იგონებს. სუსტი: ორი გმირის სახე ბოლოს ბუნდოვდება. 2 კადრი, 1 seed, თვალით. ფაილები:
  `lora_plan_2026-10-22/ic_test/results/` (collage_ic_test.jpg, A_side.mp4, B_side.mp4; HF-ზე `ic_test_2026-10-23*`).
- LTX-2.5 motion LoRA-ს პოდის სკრიპტი/კონფიგი/კაპშენის პრომპტი: HF `motion_lora/code`, არ გაშვებულა; ვანოს მულტფილმები
  და „go" საჭირო იყო. Rig მარშრუტი ვანომ 10-22-ს გააუქმა.

**დაცვა (cmsg_…LuBBngNCHGXGVGjghsVVnZ) და ფული (cmsg_…Kcwz8e5dWkVAJzffbyAjVW)**: შედეგები დანართ B-შია (`vault-2026-10-24`,
`runpod-loss-strategy-2026-10-24`). ღია: მეორე ასლი ვანოს დისკზე (`vault pull --dest D:\wldnk_vault`, ~8.1 GB) — მისი ნაბიჯი;
in-pod key self-stop დადასტურება (≈$0.01 პოდი); global volume `wasteful_fuchsia_fish` წაშლა მისი სიტყვით.

---

## დანართი B: პროექტის მეხსიერება სრულად (2026-10-29, სიტყვასიტყვით)

ქვემოთ ყოველი მეხსიერების ფაილი ცვლილების გარეშე. დათარიღებული ჩანაწერებია: უახლესი იგებს.

### memory/MEMORY.md

#### Youtube3 — project memory

##### PENDING (ვანო 11:49 Tbilisi 10-29) — DO NEXT
- Consolidation thread "გავაერთიანოთ ყველა ბრენჩი main-ში" (cmsg_01Hnu5zB86sjUj5GtTgaUkPWXeSLyFXHpi1qvNY32Eb85y): all branches/PRs -> main only, 0 PRs, OLD_HISTORY.md. When it reports done: resolve ALL old threads, then start the plan thread.
- PLAN THREAD: on his msg cmsg_01Hnu5zB86sjUj5GtTgaUkPWMYJ3bqmL35aTRkM8Q89DVe with file file_01PND3smXgXzhtskTDJj999v (CROSSWORLD_MASTER_IMPLEMENTATION_BLUEPRINT_FOR_CLAUDE.docx, ~150 pages, rewrites the whole project). Model Fable (claude-fable-5-1), effort max, PLAN ONLY: phases each independently testable. Must ASK him every important/uncertain decision. After approval, each phase = separate Opus (claude-opus-5-5, high) coding thread, one PR each.

##### RULE #6: BUDGET + FULL DELEGATION (ვანო 01:58 Tbilisi 10-27, supersedes earlier top-up/approval lines)
- No more money this month: the current RunPod balance (≈$3 at 01:55 10-27) is the WHOLE budget for everything. Do not ask for top-ups.
- Remaining spend and all checks/decisions are FULLY delegated to the Opus planner thread. No questions for him in the morning; leave a Georgian report.
- Goal now: absolute 360° coordination of frames in one space (style is solved). Study every image fully, assume nothing; proven methods exist, so the fault is in our system, Python code, or prompt.

##### RULE #5: GENERAL LOGIC, NOT THESE FRAMES (ვანო 01:42 Tbilisi 10-27)
- Every fix/strategy must fit the general logic of any scene, not the specific test frames. Held-out scenes (tundra + a new place) check the winner unchanged.

##### RULE #4: WORKER vs PLANNER (ვანო 21:06 Tbilisi 10-26)
- LoRA thread = WORKER. Opus reviewer thread writes the plans, incl. technically hard parts. OR-26 in repo.

##### RULE #3: INDEPENDENT REVIEWER (ვანო 16:49 Tbilisi 10-26)
- A separate Opus thread decides main plan choices. The coordinator passes FULL information (facts, data, results) but NOT the author's reasoning.
- Reviewer thread: "შევაფასოთ სტილის LoRA-ს სწავლის გეგმა" (cmsg_…8hv1TCfqHwPq38rbFSg8na). Auto-QA thread: cmsg_…65CMb9E2Svz2ZkebV29G62.
- Reviewer must be direct and plan at full scale from the goal.

##### RULE #1 (ვანო 21:05 UTC 10-25)
- NEVER make a system decision on an assumption. OR-22. Detailed plan before every pod (OR-23); under RULE #6 the Opus thread approves it.

##### Project
- Faceless 2D explainer YouTube channel CrossWorld Chronicles (UCndsNlyExB-jKRB9hs283BQ). Repo vano1919/explainer-engine. Owner ვანო (GitHub vano1919), writes Georgian; replies short, Georgian; often on phone. Default env env_016WZnq7uVNuVbk9X8SCpDZL.
- CHANNEL = STORYTELLER docudrama, 15-min template D, target 8–15 min + 5 Shorts, final 2K. MAIN GOAL: a 15-min fully animated video with voices and characters.
- UNIVERSE: one invented universe, one style, NO permanent heroes, NO character LoRAs.
- PIPELINE (LTX-2.5; Wan 2.2 fallback): keyframes -> LTX-2.5 video WITH native audio -> narrator -> assembly -> 2K.
- **STYLE LoRA:** xworld_v2 on Qwen-Image-2.1, checkpoint 3000. Loop rounds 1–3b gallery: https://claude.ai/artifact/C5TMq1VZsAPF7FqvNXb6zA (3b +dpl best).
- Done videos: Syndicate Wars (https://studio.youtube.com/video/JKzH8GNaaVk/edit + 10 Shorts), Titans (https://studio.youtube.com/video/XW8BfJdw1No/edit + 5 Shorts).

##### Standing rules
- NEWEST RULES ALWAYS win. REUSABILITY OVER SPEED (OR-21). CRITICAL, NOT AGREEABLE. NO HASTY DECISIONS.
- VAULT (D-73): all on private HF tmr-artifacts. TIMES IN TBILISI (UTC+4).
- Shut pods down when done; delete only on his word. Secrets never in chat/repo.
- NOTIFICATIONS: messages he should see go to his phone (notify=true).

##### Pointers
- [[feedback-rules-into-repo]] [[feedback-360-orientation-first]] [[feedback-reusable-first]] [[feedback-direct-and-wide-planning]]

### memory/animation-universe-2026-10-22.md

---
name: animation-universe-2026-10-22
description: The creator's 2026-10-22 brief "Define the Original Animation Universe Before Production" — four candidate directions, boards code (universe_boards.py), recommendation, rig PoC; direction NOT yet chosen
metadata:
  type: project
  modified: 2026-10-22T13:39:56.702Z
---

2026-10-22 13:23 ვანო (thread "ანიმაციური სამყაროს ოთხი ვარიანტი") set a new main task: ONE original, recognisable, reusable
animated universe for Cross Worlds (modern city, sci-fi, prehistoric/historical, alternate future) decided BEFORE production;
polished look, limited-animation economy (reusable rigs, cycles, expression sets, mouth flaps, modular environments); real
character action, not stills with camera moves; four distinct art directions on four concept boards (A city, B Mars, C
prehistoric, D alt future), feasibility, asset plan, PoC. He said the architecture thread misunderstood parts but existing work
(PR #17 staging, PR #18 Guardian / World Bible / asset library / providers / parallax) must be reused, not thrown away.

- Delivered (free): `docs/research/ANIMATION_UNIVERSE_2026-10-22.md` + `explainer_engine/imagegen/universe_boards.py` (+8 tests),
  draft PR stacked on PR #18's branch `claude/project-thread-w8oxrk` (branch `claude/project-thread-qporwm`). Copies in
  `/mnt/project-files/explainer-engine/animation_universe_2026-10-22/`.
- The four directions: Paper Stage (cut-paper layers), Ink and Cel (bold ink line + flat cel; closest to look v2), Soft Volume
  (no-outline sculpted shading; most expensive to animate), Poster Graphic (angular, 2-3 colours + accent). Recommendation: Ink and
  Cel first, Paper Stage to compare; Soft Volume not for production. THE CREATOR HAS NOT CHOSEN YET.
- Boards cost: FLUX 3 Klein 1k $0.18 (1 take) / $0.36 (2); Seedream 4.5 $0.80 / $1.60; Gemini 3.1 Flash Image $1.34 / $2.68.
  Run: `python -m explainer_engine.imagegen.universe_boards run --out jobs/universe/<date> --approved-by ვანო --ref <msg>
  [--candidates ...] [--takes N]`, then `board`. Only after his card; on 2026-10-22 13:12 he paused ALL paid work until he tops up
  (fal locked at $0, BFL key failing, Gemini key works, RunPod $10.97).
- 13:40 the creator asked for the full plan + my understanding with examples; iterate FREE until he likes the vision, only then paid services. Georgian plan: `/mnt/project-files/explainer-engine/animation_universe_2026-10-22/GEGMA_ka.md` (stages 0 vision -> 1 free rig PoC -> 2 paid boards -> 3 choice -> 4 PoC in style -> 5 library -> 6 pilot episode). No decision card for boards yet, by his wish.
- MUSE (creator 13:51): "simple beautiful animation like the reference shows, complexity not required, but emotion and physics must be good"; study the shows' methods, AI tools and Python libs, adapt the project. DONE 14:05 free: `production/rig.py` (cut-out rig: cycles idle/walk/run/point/react/fall, Spring follow-through, bounded squash/stretch, drop_y physics, 4 mouths from word timings; `rig demo` = 20 s clip, frames pure in f), `docs/research/ANIMATION_TOOLS_2026-10-22.md` (principles + tools: Rhubarb MIT, AnimatedDrawings MIT, SAM 2 Apache, pymunk MIT, rembg default model paid), skill `.claude/skills/animated-universe`. Clip + frames: `/mnt/project-files/explainer-engine/animation_universe_2026-10-22/rig_poc/`. All in PR #20 (commit 6e09b25). Next free steps: `rig` beat kind in assemble.finish_frame, Rhubarb/pymunk in tools/, a second drawn angle; paid: boards, then pieces cut from a painted character in the chosen direction.
- Repo capability facts (2026-10-22): assembler = stills + Ken Burns + PR #18 parallax + face sheets + bubbles; a pose bank
  (sprites per pose) and `look.pose_bank` lint exist; NO rig, NO cycles, NO lip-sync for humans (TMR owl has viseme mouth code).

- 14:15 creator: one reference picture per world with 4 places (grid), THEN a 10 s test shot "100 people end up in the ice age" (not the primitive code-drawn look), attached his own reference (adult-cartoon look: heavy uneven ink line, bulging eyes, painterly plates; it borrows famous-show motifs, so only its qualities are used = direction `wild_ink`). Card 14:18: Nano Banana 2.1 2K, 5 directions x 2 takes, $0.50, APPROVED (plan hash 807c365090475447, ledger jobs/universe/2026-10-22_grid/run.json). Run 14:19 spent $0: Gemini 402 prepay credits depleted. All 3 image accounts blocked (Gemini prepay empty, BFL key "Not authenticated", fal locked). Rerun the SAME command after a top-up; no new card needed for that plan. Ice-age shot needs its own card after he picks a style.
**Why:** the channel's look is the biggest open decision; every paint plan after it depends on the chosen direction.
**How to apply:** do not start a World Bible rewrite, asset library or episode before the creator names a direction; when he
does, follow section 7 of the document (bible bump --major, PR #17 staging test, PR #18 pilot in the direction, rig PoC).
Related: [[master-prompt-2026-10-22]], [[scene-continuity-d69]], [[asset-library-first]].
- 14:48 BFL: env var `BFL_API_kay` (typo name) holds the WORKING key (1000 credits); `BFL_API_KEY` is the dead one (403). Run BFL with `BFL_API_KEY="$BFL_API_kay"` for the process until the creator renames it. fal key works too. Provider card for the 5 grid boards posted 14:46 (fal $0.40 / BFL Klein $0.14 / both).
- 15:15 WORLD SHEETS DONE (card 14:58, $0.70 BFL Klein 2k, 2 takes): `universe_boards --mode world` (5 sheets per direction: places G, more places H, people P, animals N, ice-age action S). Boards in `/mnt/project-files/explainer-engine/animation_universe_2026-10-22/worlds/world_<dir>_t1|t2.jpg`; raw in jobs/universe/2026-10-22_world (container only). Recommended Ink and Cel; waiting for his pick. The world-mode code + test are UNCOMMITTED locally: he rejected the commit/push tool call at 14:57 (same moment he mis-tapped "not yet"); ask before committing.
- 15:28 creator likes Wild Ink (comic) + Poster Graphic (simple, cinematic) but not PG's muddy palette nor WI's closeness to famous cartoons -> asked for a mix. Added HYBRIDS `bold_poster` (clean even outline) and `shape_caricature` (no outline), painted 15:30 ($0.28, card 15:29). My pick: Shape Caricature (its ice-age action sheet nails the mix; its place grids drifted to outlined cartoon -> use the chosen frame as a reference). Waiting for his pick; then the 10 s ice-age test needs its own card (~$0.28/style on Klein). Code (world mode + hybrids + 12 tests) still uncommitted, asked 15:15 for permission.
- 15:38 creator: none of the mixes has character; wants 2 variants that read instantly as "Crossworld", with sunny tropical / warm comfortable colour (his refs: SpongeBob + Madagascar colours, qualities only). Added SIGNATURES `sunny_rubber`, `warm_geometry` (signature: a glowing turquoise rift in every frame + an item from another era on every character). fal is LOCKED (exhausted balance, 15:41; first request may have charged $0.04); painted on Klein $0.224. BFL moderated all 4 ice-age action sheets as "Protected Content" (cartoon mammoth + sabre-tooth + ice age reads as a famous franchise) -> the ice-age episode/test must design animals and heroes far from that film. Fixed fal adapter: status poll accepts 202 (uncommitted). Thread hit the 24-attachment cap: link further files by path.
- 16:05 fal topped up ($9.96; locks lift after top-up). Seedream signature worlds done ($0.80, the 15:40 card plan; fal now $9.16); Seedream was NOT moderated on the ice-age sheet. Seedream gives more character: Sunny Rubber invented a yellow rubbery mascot (memorable but near a famous yellow character -> reshape if chosen); Warm Geometry = warm cinematic, most original. Told creator per-episode cost after the world build ~ $1-3 pictures (world build ~$5-10 once). Waiting for his pick.
- 16:09 DIRECTION CHOSEN = WILD INK (D-71 in docs/DECISIONS_AND_OPEN_QUESTIONS.md). His rule: EVERYTHING in the frame (living or not, near or far, hero or background) in the same style; a background mammoth has the same eyes/line as the hero one. Encoded as `universe_boards.ONE_STYLE` appended to wild_ink core + skill section + test. Next: 10 s ice-age test in Wild Ink (card 16:12: Seedream ~$0.80 recommended / Klein $0.28); design the mammoth away from the famous ice-age film. Next free decision id: D-72.
- 16:20 ice test round 1 (Seedream t2i, $0.80, jobs/ice_test/2026-10-22, sheets in project-files .../ice_test/): characters good, plates useless (Wild Ink core + ONE_STYLE put eyed creatures into empty valleys), parts not split. Free fixes: `universe_boards.WILD_INK_PLATE` (plate core without character words), `imagegen/spend_tiers.py` (creator 16:15: model must know where saving is not allowed, e.g. faces; one model per character; refs when mixing; free `mismatch` colour/line/texture check), `ice_test.round2` (plates t2i x2 + 4 part kits on Seedream EDIT with the chosen take as ref, $0.40; picks MAN t2, MAM t2, WOM t1, DOG t1). Card 16:22 pending. All uncommitted (asked twice).
- 16:55 10 s ice-age shot DONE free: `production/ice_shot.py` (parts cut by chroma key from round-1/2 Seedream sheets; man rig head/torso/leg kit, mammoth skid, dog leaps back to stand between fallen man and mammoth, procedural sound). Video in project-files .../ice_test/ice_shot.mp4 (+ ice_shot_frames.jpg). Total paid for the test $1.20 (fal). Known rough spots: fallen man's legs read as parts, two crowd figures keep a pink glow edge, synth sound. Asked him: background animals same big eyes? commit to PR #20? Still uncommitted.
- 18:xx creator asked (pasting a ChatGPT audit) for a full self-audit of ice_shot.mp4 + why tests missed it. Done: 13 defects (project-files ice_test/AUDIT_ice_shot_ka.md), root cause = no test + stills-only review. New `qa/shot_check.py` AN-01..AN-08 (docs/EDITING.md, docs_lint family AN) runs after every animated render; ice_shot rewritten around one event table (gait from distance, tucked swing leg, sounds from contacts, stereo BP-61 loudness on the AAC). v2 = ice_shot_v2.mp4, check PASS. Suite 759 passed. Lesson: always review motion frame-to-frame (contact sheets of consecutive frames + diff spikes), never stills only. Still UNCOMMITTED (no commit OK yet).

### memory/asset-compose-plan-2026-10-25.md

---
name: asset-compose-plan-2026-10-25
description: ვანო 2026-10-25 02:19 Tbilisi plan: the style LoRA draws reusable assets, Python composes shots (micro scenes + mass battles), then video; scene LoRA dropped from production; readiness doc + free style score
metadata:
  type: project
---
ვანო's plan (02:19 and 02:21 Tbilisi, 10-25), which supersedes prompt-per-shot generation:
- The style LoRA draws only ASSETS: backgrounds, each hero from every needed angle, props and crowd units.
- Python and the agents compose the shots logically, for micro scenes and mass battles alike. Assets are reused to cut cost and keep the style.
- Photos or AI then make the video.
- The scene LoRA is dropped from production. Its 499 pairs plus 336 held-out pairs stay as data to measure with and to test the Python and agents.
- He wants full style tests and proof that everything is "trained" BEFORE any generation. The 1-min film generation was stopped.

Readiness doc: https://claude.ai/artifact/4zwAT8Y34BRmJqKDYzN3i1 (doc id 206230a1-b89c-4f48-9c8b-888269ed31ca, body de9f235d-ceae).

Free measurements of the footage (3312 shots; scratchpad grammar/):
- shot length: median 3.2 s, 23 % longer than 5 s;
- ≈20 % of shots return to an earlier setup within 8 shots;
- camera still in ≈66-77 % of shots;
- shot sizes: MS 30 %, WS 20 %, MCU 18 %;
- 1-2 people in 79 % of shots.

Automatic style score (scratchpad stylescore/score.py, svenv): DINOv2-small on 6 crops, compared with his 11 references_v3 photos.
- AUC 0.96 good vs bad on 80 past pictures.
- BUT snowy pictures score low even when good (the v5 tundra sample scored 0.33).
- So it compares against a same-place eras-formula control and never acts as a hard gate on its own.

Proposed order:
1. Free: the compositor in the repo with tests (micro, crowd, crop reuse), the asset library record, the style score, planner rules, and fixes to LT-65 and the START-pose rule.
2. Paid check 1, ≈$0.3: assets (4 heroes × 4 angles, backgrounds, bus, 3 soldiers, eras control).
3. Paid check 2, ≈$0.2: 6 composed shots and 2 battle shots.

Awaiting his OK. Related: [[shot-reuse-rule]], [[feedback-no-rushed-hypotheses]], [[style-lora-prompt-shape]].
- 03:40 Tbilisi 10-25: he chose "free first". The free part is done in PR #22, commit c032f76:
  - explainer_engine/compose (library, frame, crowd, reuse, style_score);
  - AC-01..AC-15 in docs/ASSET_COMPOSE.md;
  - LT-65 rewritten: no tail, at most 40 words, layout words are REVIEW. The prompt thread was told.
  - CPU demo page: https://claude.ai/artifact/7VRS7D6jhdrNNCL2Fp4BpC (files in project film_1min_2026-10-24/compose_demo/). It caught the girl cut-out carrying a snow block (AC-15) and the MWS plate horizon (AC-05).
  - Next, awaiting his word: paid asset check ≈$0.3, then composition check ≈$0.2.

### memory/asset-library-first.md

---
name: asset-library-first
description: Library-first rule (D-63/OR-18, creator 2026-10-20) — reusable music/SFX/picture libraries are searched before any new paid generation; new takes are registered back
metadata:
  type: project
  modified: 2026-10-20T19:24:00.402Z
---

Creator rule (2026-10-20, thread "მრავალჯერადი ასეტების ბიბლიოთეკა"): background music and reusable objects live in
local libraries; new ones are generated only when nothing there fits; this session's generated assets are kept.
PR #15 (explainer-engine, branch claude/asset-library-jy2g5u → systemic/next-video) implements it as D-63 / OR-18 / PP-08.

**Why:** the titans episode generated music/SFX the next episode would have paid for again; per-episode folders were
invisible to later videos.

**How to apply:**
- Before any new music/SFX/reusable picture: `python -m explainer_engine.assets_reuse <episode> --kind music|sfx|vocal|picture
  --tags ... --decide reuse|generate_new [--why ...]` — writes `<episode>/asset_reuse.json`; the ElevenLabs hook
  (`standards/hook.py`) REFUSES a paid music/SFX call without that record (narration exempt; creator override still works).
- Register connector-made sounds: `python -m explainer_engine.audio.register <mp3|wav> --name ... --category music|foley|vocal
  --tags ... --model ... --prompt "..." --cost-usd ...` (→ assets/audio/library, mono WAV, source elevenlabs).
- Reusable pictures: `python -m explainer_engine.imagegen.picture_library add|find|fetch` (→ assets/pictures/library;
  committed like character assets). `paint plan` lists prompt matches as PP-08 REVIEW; the creator still picks (D-50).
- Media backup home: HF `datasets/vano1919/tmr-artifacts/library/`.
- Pending (as of 2026-10-20): the titans thread registers its generated music/ambience after its paid run finishes; PR #15
  awaits the creator's merge. Related: [[runpod-money-control]], [[storytelling-system-v3]].

### memory/auto-qa-plan-2026-10-26.md

---
name: auto-qa-plan-2026-10-26
description: Plan for automatic picture QA per LoRA checkpoint (xworld_v2), metrics per failure, calibration on ვანო's ratings, cost
metadata:
  type: project
  modified: 2026-10-26T12:15:17.140Z
---
2026-10-26 12:30 UTC: plan written for ვანო's ask (cut eye-checking, automate QA during training).

- Plan file: project files xworld_v2/AUTO_QA_PLAN_2026-10-26_ka.md. Sent to the LoRA thread to follow.
- Findings:
  - round 0's low judge numbers are mostly real failures (P1/P2 never cut to close).
  - Chain noise and saturation grow already on the base model, so compare each checkpoint against the round 0 frame.
  - Switch the judge to VQAScore-style P("Yes").
- Calibration: rate_page plus new reasons. AUC ≥0.8 gives FAIL power, 0.7–0.8 gives REVIEW only, below 0.7 the metric is dropped. These thresholds are proposals awaiting his OK.
- Cost: generation is 17 s/img on the RTX PRO 6000 (round 0 pod.log; 102 imgs ≈ 29 min); metrics add ~5 min per checkpoint. Light probe on 5 checkpoints + full set on the best 2 ≈ $4, against a $3.73 balance.
- Biggest unknown: ArcFace and detectors on cartoon faces. Testing it is free (CPU, round 0).

Related: [[feedback-strict-eras-style-check]].

### memory/channel-storyteller-principle.md

---
name: channel-storyteller-principle
description: The creator's core principle for CrossWorld Chronicles scripts: the story/idea is the goal, hooks/animation/SFX are only means; plus how he wants new episode ideas shaped (mini-film, main heroes, mixed outcomes)
metadata:
  type: feedback
  modified: 2026-10-20T11:15:29.209Z
---

- The channel is a storyteller: the main thing is to invent and tell an interesting story. Hooks, animation and sound effects are means to turn the viewer towards us; an interesting idea must be waiting there. Means, never the goal (creator, 2026-10-20).
- Shape of an episode idea (creator 2026-10-20, "titans from zero" thread): a mini-film, not a montage of shots; main and secondary heroes like a series (not equal focus on all); real multi-turn dialogues, not single lines; mixed outcomes (some adapt, some don't); a frame character who appears at the start and the end is welcome; ~13 min when there are many heroes.

**Why:** he rejected v1 (one day, ten equal heroes) and v2 (montage over 5 years) of the titans scenario for missing the idea and being a set of shots.
**How to apply:** start every scenario from the story question and the main heroes' arc; add hooks/SFX only after the story stands. See [[creator-workflow-preferences]].

### memory/consents-ai-video-2026-10-22.md

---
name: consents-ai-video-2026-10-22
description: ვანო's blanket advance consents (2026-10-22 22:45) for the AI-video route: all listed costs approved, condition = the money must suffice; caps to set in code
metadata:
  type: feedback
---

ვანო 22:45: "ყველა ხარჯზე ვამბობ კის, მთავარია ეყოს ხარჯი" after the consent list + cost audit in the hybrid thread.
Approved in advance (no further cards for these): AI-video route (Wan 2.2 FLF2V + style video-LoRA + SeedVR2 4K) instead of
the rig; one-time ≈$2.5–3 (video-LoRA ≈$1.5–2, Ice Age test scene ≈$0.6, skeleton-control test ≈$0.3) + LTX-2.5 test ≈$1
only if Wan falls short; per-episode ≈$7 RunPod (+20 % reserve ≈$8.5) + ≈9k ElevenLabs credits; caps in code: training pod
$2 / 5 h, daily $3 on render days, episode ≈$9; cheapest RunPod community GPU (A40/4090); V1–V4 under one approval; 4K
only on the final cut; 1 take + retake on QC fail; plates without characters by code; NO character LoRAs ([[no-permanent-heroes]]).

**Why:** waiting on him costs more than the money ([[feedback-cheapest-decide-yourself]]).
**How to apply:** proceed without cards within these numbers; stop at 80 % of a cap or when the balance cannot cover the
next step (RunPod $10.97 on 2026-10-22 covers the one-time work but not a full episode; ElevenLabs credits ~7.3k of 7.55k
used), and ask him to top up instead of asking for permission. Any step outside this list still needs his word.

### memory/creator-workflow-preferences.md

---
name: creator-workflow-preferences
description: how the creator (ვანო) wants episodes prepared before any script or paid step (story first, voices, speech manner)
metadata:
  type: feedback
  modified: 2026-10-21T06:56:22.141Z
---

- Before writing or rewriting any production script, send a SHORT story in Georgian in the thread (what it is about, how it ends); write the script only after the creator OKs it. Repo rule OR-15 / PV-45 (`episode.scenario`).
- Every speaking character gets their own voice chosen by personality (D-45, voice-caster), never imitating an actor; and talks in their generally known manner and vocabulary, or from personality if invented (DW-11 / PV-46 `cast.<id>.speech`), always in our own words, no film quotes.
- The creator wants dialogue in episodes so expressions can change (~1 s), visual beats ~1.5 s with short cues (D-54/D-55).
- After the full script is approved, ask for ONE combined approval of images + audio (one cost estimate for both, image provider pick included); batch images are slow and must not wait for audio (creator 2026-10-20).
- TWO-PART SAMPLE FIRST (creator 2026-10-21, supersedes "generate everything in parallel then stitch"): after the script approval, generate voice + pictures ONLY for the first 2 parts (in parallel), render and stitch them; the creator watches, gives notes, notes are fixed; only his recorded word opens paid audio/pictures for the rest (Shorts included). In code: D-67/OR-19/PP-09, `production/sample.py` (`status`/`approve`, sha256-bound `sample_approval.json`), `paint plan --sample`, ElevenLabs hook, production_gate 6.5 — PR #16 (draft, base systemic/next-video, awaiting the creator's merge word). Reusable assets (face sheets, references, library sounds) and estimate_only stay allowed before approval.

**Why:** creator, 2026-10-19 thread; annoyed when asked about a rule they already set (ER-03 of Syndicate Wars was stale).
**How to apply:** check standing rules before asking; when an episode rulebook contradicts a creator rule, fix the rulebook and say so.

### memory/dialogue-research-2026-10-26.md

---
name: dialogue-research-2026-10-26
description: 10-26 research: NVIDIA PersonaPlex cannot read a written script (full-duplex assistant, improvises); Dia2/ElevenLabs Dialogue are the scripted-dialogue candidates
metadata:
  type: project
  modified: 2026-10-26T08:38:53.569Z
---
ვანო asked (12:34 Tbilisi 10-26) whether NVIDIA PersonaPlex-7B could make "real conversations" for our videos.
Finding (primary: GitHub NVIDIA/personaplex, arXiv 2602.06053): full-duplex speech-to-speech on Moshi. It listens to
user audio and improvises the agent's reply. The text prompt sets a role, not lines. English only. Weights are under the
NVIDIA Open Model License (commercial OK, gated on HF). It does NOT fit scripted docudrama (OR-15, invariant 5).
Candidates: Dia2 (Apache-2.0, [S1]/[S2], voice prefix wav, English, ≤2 min) and ElevenLabs Text to Dialogue (paid;
conflicts with his "ElevenLabs only for the narrator"). Higgs v3 is non-commercial.
Proposed: one continuous dialogue track per scene -> word timings -> cut per clip -> LTX-2.5 A2V. Awaiting his answer.
Report: /mnt/project-files/explainer-engine/dialogue_research_2026-10-26/PERSONAPLEX_ka.md.
Related: [[video-model-research-2026-10-25]].

### memory/episode-scripts-export.md

---
name: episode-scripts-export
description: where readable full scripts of the three finished videos live (shared folder scripts_export, 2026-10-22) and their sources
metadata:
  type: reference
  modified: 2026-10-22T02:44:08.373Z
---

The channel's three finished long videos (as of 2026-10-22): (1) Stone Age "100 Geniuses" ep1 (creator uploaded it himself
2026-10-17; source examples/stone_age/ep1_v1/production_script.json), (2) Syndicate Wars (JKzH8GNaaVk), (3) Titans (XW8BfJdw1No,
source branch claude/project-thread-hze0pq examples/titans_from_zero/production_script.json + timed.json).
Readable Markdown exports (full voiced text, segments, timestamps, cards, Shorts): /mnt/project-files/explainer-engine/scripts_export/
1_stone_age_100_geniuses.md, 2_syndicate_wars.md, 3_titans_went_broke.md. Exact Titans clip-Short ranges were container-local (lost).
See [[titans-qa-loop-state]].

### memory/explainer-engine-audit-2026-10-19.md

---
name: explainer-engine-audit-2026-10-19
description: state of explainer-engine next-video branch and the Syndicate Wars v2 episode after 2026-10-19 (what is done, what is stale, what waits on the creator)
metadata:
  type: project
  modified: 2026-10-19T14:39:10.082Z
---

- `systemic/next-video` (1d579fd) holds every branch of 2026-10-19 plus PR #5 (visual beats) and the Syndicate Wars script v2. Draft PR #4 next-video → main; merge only after the new video is done (creator: "newest is priority").
- ccr renumbering: D-45/46/47 → D-51/52/53, PV-32..36 → PV-39..43, OR-10..13 → OR-11..14. D-50 (creator picks provider per batch) supersedes D-52's "Gemini only".
- Syndicate Wars v2 (story approved 13:55): script_lock + paid_assets stamped on rulebook v8 (condition: no pre-v2 Vito/Shelby portraits among recovered pictures, faces checked for actor likeness); editorial review passes (only EG-11 REVIEWs for unused C-03/05/17/29); validate FAILs = PV-05 only (pictures). Build: builder → apply_beats.py → compile; beats keyed by exact line text (beats_by_line.json + beats_v2_new_lines.json), so a reworded line needs its beats key moved.
- Creator chose 2026-10-19 14:50: 48 pictures on pod (~$0.37), 4 face sheets on Gemini (~$1.1, reusable). Blocked: no RUNPOD_API_KEY / GEMINI_API_KEY in the cloud env (asked creator to add a cloud environment). Paint order: p_* portraits + s01_skyline first (every pod_ref picture refs them), then the rest; sc_* cards come free from production/select_screen.py. Re-stamp paid_assets right before the run. Still open: 14 lost pictures (sc_* cards, p_* portraits, s01_skyline) must be remade; voice test reads before ElevenLabs narration (~8.5k + ≤4.7k chars); title choice ("Classic Mafia Bosses" inaccurate).
- Shorts metric (creator 2026-10-19): the "20 %" is viewed-vs-swiped (20 % swiped away) — hooks are fine; the weak part is the middle (likes/view 0.4-1.0 % vs 1.7 % median, 1.4 changes/10 s). Shorts had no visual-beat layer; being added (beats in schema, PV-44 over Shorts, shorts.py render).
- Painting moved to its own thread (Syndicate Wars: სურათების ხატვა); 46 of 48 pictures recovered free from old Gemini batches.
- Open: ZMAX 1.25 vs MAX_ZOOM 1.15.

**Why:** the creator asked to restart the same topic with 10 Shorts, then make main the newest.
**How to apply:** build on next-video; nothing paid before the provider choice and a recorded approval.

### memory/explainer-engine-audit.md

---
name: explainer-engine-audit
description: State of the 2026-10-19 explainer-engine audit, branch divergence, and verified facts to reuse before changing paint/ledger/providers
metadata:
  type: project
  modified: 2026-10-19T11:37:38.605Z
---

Audit report: /mnt/project-files/explainer-engine/AUDIT_2026-10-19/AUDIT_2026-10-19.md (+ annexes A1 policy sources, A2 image
provider prices, A3 engineering review). Delivered 2026-10-19; waiting for the creator to approve numbered items and pick the
base branch (P0: PR #3 recommended).

- Four diverging branches (PR #3 `claude/project-thread-on22x9`, `chatgpt/repo-management`, `ccr-0d2b1961-9r63nt`,
  `phase-2-spec-pack`) reuse IDs D-45, PV-32..36, OR-10 for different rules. **Why:** merging silently duplicates rules.
  **How to apply:** never merge without a renumbering pass; docs_lint only checks D/SE/V/P/RR/R/Q/UR.
- Clean checkout: 243 passed, 2 failed (gitignored library WAVs; 45 procedural rebuildable via audio/build_library.py).
- paint.py paints `pod_ref` with Gemini but never runs validate/prompt lint (73/73 ep1_v1 prompts would FAIL).
- Claude cannot generate raster images (Anthropic Vision FAQ); it can orchestrate providers, draw SVG/PIL, review images.
- The creator wants to be asked which image provider to use before every batch; never generate automatically.

### memory/explainer-engine-branch-state.md

---
name: explainer-engine-branch-state
description: Since 2026-10-29 both repos have ONLY main and 0 PRs; all history in explainer-engine OLD_HISTORY.md; new work branches from main
metadata:
  type: project
---
- 2026-10-29 (ვანო 07:03 UTC, thread "გავაერთიანოთ ყველა ბრენჩი main-ში"): every branch/PR of explainer-engine (PR #22 head
  5cafa84 held all 28 branches) went to main; tmr PR #9/#10 merged into its main (tmr PR #11), tmr PR #4 and
  three-hour-format-7ewyz0 closed as superseded (kept in HF vault bundle). All other branches deleted.
- `OLD_HISTORY.md` in explainer-engine main = the one history file: merge record, rules in force, loop state, HF and
  /mnt/project-files paths, old threads, full project memory copy. Old branch commits before 10-24: HF
  `vault/code/*_2026-10-24.bundle`.
- systemic/next-video is retired as the working branch (his 10-29 request): new work branches from main, PR -> main.
- ID history: D-63 (#14) / D-76 (library first); D-74 pod manager / D-77 script engine; ST-17..19; CT- cards. Decision ids
  reach D-80; check docs/DECISIONS_AND_OPEN_QUESTIONS.md for the next free id before writing one.
- explainer-engine HAS CI (`quality`: pytest not system/media + docs_lint + palette). Run docs_lint after a PROGRESS entry.

### memory/feedback-360-orientation-first.md

---
name: feedback-360-orientation-first
description: ვანო 2026-10-25 12:47 Tbilisi: top criterion = correct, logical orientation inside ONE 360° environment while keeping style and cinematography
metadata:
  type: feedback
---
ვანო: "the most important thing is correct and logical orientation in the 360° environment while keeping the style and
cinematography".
**Why:** earlier runs failed on place logic (flat panorama, mirrored edges, wrong perspective, floating objects).
**How to apply:** judge every frame/test on three gates together: (1) orientation — the camera's world direction shows what
the scene map puts there (bus south, hill north…), checked against the layout; (2) style vs the eras sheet; (3) cinematography
— shot size, horizon, 180° line, one light direction across shots. Tests should include "same place, other angle" checks.
Related: [[python-world-composer-2026-10-25]], [[tool-findings-2026-10-25]].

### memory/feedback-agree-every-detail.md

---
name: feedback-agree-every-detail
description: ვანო 2026-10-26 01:05-01:06 Tbilisi: RULE ONE, no system decision on an assumption (also in auto mode); detailed plan before every pod (OR-22, OR-23)
metadata:
  type: feedback
---
ვანო: "Claude's first rule: never take system decisions by assuming; agree every detail with me; also in auto mode" and
"before every pod launch show me a detailed plan, not a general one".

**Why:** the xworld style LoRA was started on 2512 from an old repo rule against his newer 2.1 decision; money wasted.
**How to apply:** base model, LoRA/checkpoint, data, captions, every setting, test variants, rule wording, spend: only
from his words; list every unsettled detail and ask before using it. Before `runpod create`: item-by-item plan (purpose,
model+checkpoint, data, all settings, outputs/HF paths, GPU+price, time/money caps+ledger, stop condition, what he sees,
what follows) and his agreement. Rows OR-22/OR-23 in docs/ORCHESTRATION.md, CLAUDE.md, commit 99ad949.
Related: [[feedback-reusable-first]], [[feedback-rules-into-repo]].
- 01:44 Tbilisi 10-26: for the R&M dataset questions he said "answer the four questions yourself". When he hands a choice
  back like that, decide, say what you chose and why in one line each, and still put any POD plan (OR-23) to him.

### memory/feedback-ask-when-cap-blocks-quality.md

---
name: feedback-ask-when-cap-blocks-quality
description: ვანო 2026-10-23 21:36: never let a money cap silently cut a training short of the quality goal; ask him at once for the raise
metadata:
  type: feedback
---

When a cap (ledger, per pod, per 24 h, per episode) would stop a run before it reaches the quality goal, ask ვანო
immediately with a decision card (amount, why, what it buys), in the same turn, and keep working on what fits meanwhile.
Never shrink the run (fewer steps, smaller cap) silently to fit a cap, and never wait hours without asking.

**Why:** v4 style LoRA was cut at step 809 because I fitted it under the $8/24 h line instead of asking; his photos'
painterly style was still not learned and hours were lost (2026-10-23). He: "if the limit was not enough you did not even ask".
**How to apply:** before launch compute steps x s/step x $/h against every cap; if any cap cuts it, card first. Judge
"done" by his eye vs his photos, not by a plateau of a metric. Related: [[feedback-cheapest-decide-yourself]], [[runpod-money-control]].

### memory/feedback-be-critical.md

---
name: feedback-be-critical
description: ვანო 2026-10-25 21:03 Tbilisi: be critical, not negative — verify what he says against facts and agree or disagree with arguments; never agree by default
metadata:
  type: feedback
  modified: 2026-10-25T17:04:09.842Z
---
ვანო: "we no longer use the model I called ideal, because you made me choose the wrong tool; you agree with everything
mindlessly. I need criticality: not negative, but check what I say and agree or refuse with arguments."

**Why:** I followed his ideas without checking them, and they cost money: the move to Qwen-Image-2.1 (10-24 12:37) without a
controlled comparison against the approved 2512 v1.0; the scene LoRA; v2 trained on self-generated data. He wants a
partner who tests claims.
**How to apply:** for every idea, claim or decision from him (and from me), first check it against the records:
- logs, ratings, billing, research;
- the expected cost.

Then answer:
- **agree** because X, or **disagree** because Y, with the evidence;
- an unknown is named as unknown, plus the cheapest way to find out.

Never "yes, doing it" alone. Before a tool, model or strategy switch, compare it with the current approved option on the
same prompts, and state the risk and cost. Rule LT-72 in docs/LORA_TRAINING.md.
Related: [[feedback-no-rushed-hypotheses]], [[feedback-one-goal-failure-triage]], [[feedback-report-spend-immediately]].

### memory/feedback-cheapest-decide-yourself.md

---
name: feedback-cheapest-decide-yourself
description: ვანო (2026-10-22 22:06): always pick the cheapest option and decide yourself when waiting costs more than deciding; change rules that block that
metadata:
  type: feedback
  modified: 2026-10-22T22:07:07.843Z
---

ვანო: "always do the cheapest option. Change the rules if waiting costs more than your decision; always decide yourself
what is cheap and oriented at getting the job done."

**Why:** a decision card to delete a failed, empty stopped RunPod pod ($0.13/day, blocked the next pod) made him wait for
a trivial call; waiting on him costs more than the money involved.
**How to apply:** for small, cheap, job-advancing steps inside an already approved task (cleaning up a failed empty pod,
retrying on a cheaper GPU/provider, picking the cheaper model) act and report afterwards; no decision card. Still ask for new
spending beyond the approved cap or for anything irreversible that holds his work. Pick the cheapest workable provider/GPU by
default. Related: [[feedback-references-creator-call]], [[runpod-money-control]].

### memory/feedback-direct-and-wide-planning.md

---
name: feedback-direct-and-wide-planning
description: ვანო 2026-10-26 15:57 UTC: be blunt in evaluations; plan at full scale from the goal, all paths, grounded in known training methods
metadata:
  type: feedback
  modified: 2026-10-26T15:57:37.935Z
---
ვანო asked the Opus planning thread for two things:
- Evaluations must always be direct.
- Plans must always be at full scale: start from the goal, list every way to reach it, and ground each one in established learning/training methods and in the project's goals. A plan is not only the next step.

**Why:** narrow step-by-step plans kept testing one idea at a time; for example, training more steps cannot fix cross-shot identity.

**How to apply:**
- Give the verdict first, without hedging.
- Each plan opens with the goal: consistent multi-shot scenes in our style, era readable at a glance.
- Compare all paths: training, reference conditioning, compose from parts, layout/3D control, video. Cite the known method for each, choose one, say why, and price it.
- Related: OR-24 (the Opus thread takes the main plan decisions); see [[feedback-agree-every-detail]] and [[night-run-2026-10-26]].

### memory/feedback-general-logic-not-frames.md

---
name: feedback-general-logic-not-frames
description: ვანო 2026-10-26 21:41 UTC: every fix must fit the general logic, never be tuned to the specific test frames; held-out scenes prove it
metadata:
  type: feedback
---
ვანო: "the main thing is that every action of ours fits the general logic, not these specific frames."
**Why:** tuning prompts to the tent/Rome test frames would look like progress, then fail on the next episode.
**How to apply:**
- Prompts are built by code from the set file + the shot card; no scene-specific hand wording (enforced by a test).
- Keep held-out scenes (tundra + one new place type, frozen before results) and confirm every winner on them without changes.
- Write each fix as a general rule.
Related: [[feedback-360-orientation-first]], [[feedback-direct-and-wide-planning]].

### memory/feedback-georgia-time.md

---
name: feedback-georgia-time
description: ვანო: all times in replies and status notes are Georgia time (UTC+4), never UTC
metadata:
  type: feedback
---

All times I write to ვანო (replies, checklists, ETAs, guard times) are Georgia time, UTC+4. Never write UTC.

**Why:** ვანო reads times in Georgia time. Earlier replies used UTC, so an ETA of "21:10" meant 01:10 for him (2026-10-23, asked in chat).

**How to apply:** convert every clock time to UTC+4 before posting. Tool timestamps (guard logs, HF commits, wake times) are UTC, so add four hours. Say "საქართველოს დრო" only when it helps; otherwise use the plain time.

### memory/feedback-higher-thread-decides.md

---
name: feedback-higher-thread-decides
description: ვანო 2026-10-26 12:49 Tbilisi: important decisions go to a separate Opus thread; its confirmation of the OR-23 pod plan starts the pod (OR-24)
metadata:
  type: feedback
---
ვანო: Sonnet (the working thread) plans; before every important decision ask a separate thread on a higher model (Opus). That
thread takes the main plan decisions. The coordinator must pass it complete information (facts, numbers, files, open items)
but NO reasoning, so it is not biased. When that thread confirms the plan, start the pod.

**Why:** he does not trust one model's plan taken on its own; the 10-26 reviews by the Opus thread found real faults (training and test wording
did not match, chained edits).
**How to apply:** OR-24 in docs/ORCHESTRATION.md, CLAUDE.md, test test_agree_every_detail.py. Check the model with get_session
(session_context.model, last_served_model). The review thread "შევაფასოთ სტილის LoRA-ს სწავლის" (cmsg_01Hnu5zB86sjUj5GtTgaUkPW8hv1TCfqHwPq38rbFSg8na)
runs claude-opus-5-5. Still his: goal changes, spend above the plan or caps, the RunPod top-up, deletes.
Related: [[feedback-agree-every-detail]], [[lora-training-control-2026-10-23]].

### memory/feedback-no-rushed-hypotheses.md

---
name: feedback-no-rushed-hypotheses
description: ვანო 2026-10-25 02:05 Tbilisi: stop proposing a new paid test per fresh hypothesis; first a full sourced analysis, then decide together
metadata:
  type: feedback
  modified: 2026-10-24T22:05:52.174Z
---
ვანო: "we tried many times and it does not stabilise; I think you make hasty decisions."

During 10-24..25 I ran four picture tests ($1.94, $0.31, $0.40, $0.51). Each one tested a new hypothesis: prompt length, the negative prompt, the style tail, composition. One rule (LT-65, the tail) later turned out to be half wrong.

**Why:** the paid tests added up without a stable answer, and he loses trust when each result brings a new theory.

**How to apply:**
- When a quality problem repeats, first do a free, full analysis from the records: the chat transcript (/root/.claude/projects/-home-user/*.jsonl), the HF training configs, captions, logs and eval outputs, and the project files.
- Give a source for every claim.
- Show the analysis and decide together before any paid run.
- One controlled test only when the analysis cannot answer.

Related: [[style-lora-prompt-shape]], [[style-check-before-showing]].

### memory/feedback-one-goal-failure-triage.md

---
name: feedback-one-goal-failure-triage
description: ვანო 2026-10-25 17:44 Tbilisi: every failure gets a cause (prompt / input picture / check / system) before retry, small change or new strategy; every decision serves the one goal
metadata:
  type: feedback
  modified: 2026-10-25T13:48:28.581Z
---
ვანო: "The goal is one, the one we know. For anything that fails, investigate why: was the prompt weak, the photo we fed in,
the check, or the system; then decide retry, small change or a strategy change. Every decision must serve the one goal."
He also asked (17:37): report training results regularly (what works / what fails), keep the pod running until the goal is
reached (still ask at 80 % of a cap), strategies may change.

**Why:** paid tests that each brought a new theory lost his trust ([[feedback-no-rushed-hypotheses]]).
**How to apply:** for each FAIL write the cause class with evidence from logs/configs first. Example 10-25: the 2.1 LoRA
"failed" (0.19-0.41) only because MY inference used cfg 1.0 (training samples cfg 4 passed 0.60-0.71) and VideoX-Fun
merge_lora silently skipped all 32 img_mlp.gate_up layers (ai-toolkit's fused [gate_layer; proj]) — system, not LoRA.
Always read the merge log ("errors") and match sampler settings to training before judging a LoRA.
Related: [[feedback-strict-eras-style-check]], [[feedback-ask-when-cap-blocks-quality]].
- 17:58 Tbilisi 10-25 ვანო: "do not shut the pod down until I say and until we reach the ideal trained model, even if more money is needed". Guard caps then sit at the balance floor (balance $5.7 at 17:58); warn him before the balance runs out, keep the pod busy (no idle).
- 17:09 Tbilisi 10-25 ვანო: "whenever there is any news, write me a notification so I stay updated" -> post a short reply on every real news item (result, success, failure, strategy change, money warning); the usual "max two replies" throttle is overridden for this thread while the pod runs.
- 19:02-19:13 Tbilisi 10-25 ვანო: "research existing training techniques, pick the best, don't follow my advice blindly". Chosen: StyleDrop iterative + DreamSync loop (gen 3/prompt -> style score + eye + blind DSG-style logic -> best per prompt -> retrain, his photos >=50%); his 8 cartoon scenes = held-out test only (not training); stop when test score plateaus; DPO only if extras persist after 2 rounds. Estimate told him: ~$18-22 total (round 1 ~$3.7 now, rounds 2-3 ~$8.5 each; 2 variants/prompt ~$6.5). Round 2 needs a RunPod top-up.
- 19:17 Tbilisi 10-25 ვანო: merge training with the first video: round 2 = Napoleon 15-min episode keyframes (86 kf + 9 sheets x3 variants, best = episode material + training data; Napoleon share capped, his photos >=50%). First check script/prompts fit the LoRA. Found: sun is not systematic (r12 plain retries in style; gold more painterly); 3 four-hero keyframes name only 3 (S04-01,S08-01,S13-01); second heroes get short tag only (8 kf). Sent to prompt thread (composer owner) 15:25 UTC; waiting for new prompts.json. 144 cut/nextpose prompts are 2.1 edits: conflicts with his 10:50 no-Edit rule unless continuity test (job 020) passes.
- 15:30 UTC 10-25 results page https://claude.ai/artifact/JVymyRmtZxurgTyE378BtQ: v2 style mean 150=0.61, 300=0.60, 450=0.54 (Rome "a pigeon" -> 2 pigeons at 300/450). Retry12: 13/14 failed prompts got >=1 good variant (g080 crowd REVIEW); "only the people named" 3/6 vs plain 1/6 (small sample, not a rule yet); prompt fixes 4/4. Prompt thread fixed Napoleon prompts (PR #24 4bb18e9, new prompts.json in project files); 3-4 hero shots lose costume words -> identity from sheets/refs.
- 20:11 Tbilisi 10-25 ვანო: scene continuity is already learned by the base model; put ALL training energy into STYLE only; for continuity just test which prompts/refs work best. Agreed (10-24 evidence: base Edit >= scene LoRA v1). Continuity test stays only as a check that the style LoRA does not break base continuity (LoRA vs no LoRA, same 4-shot scene).

### memory/feedback-opus-plans-sonnet-works.md

---
name: feedback-opus-plans-sonnet-works
description: ვანო 2026-10-26 17:06 UTC (OR-26): Sonnet works, the Opus thread writes plans; hard technical code/test design goes to Opus first
metadata:
  type: feedback
---
ვანო: "you are the worker, you do the tasks, Opus writes you the plan"; technically hard questions (code design and test plan of a new method, e.g. S3 depth layout) are prepared by the Opus thread, then I implement exactly.

**Why:** he trusts the higher model's plans more (see [[feedback-higher-thread-decides]]).
**How to apply:** OR-26 in docs/ORCHESTRATION.md and CLAUDE.md. Ask via message_thread to the reviewer thread (cmsg_01Hnu5zB86sjUj5GtTgaUkPW8hv1TCfqHwPq38rbFSg8na) before coding; report deviations instead of deciding.

### memory/feedback-references-creator-call.md

---
name: feedback-references-creator-call
description: ვანო (2026-10-22 20:35): use his reference images fully (famous-person caricatures, show-like visuals); monetisation/rights risk of what he publishes is HIS decision
metadata:
  type: feedback
  modified: 2026-10-22T20:36:04.025Z
---

ვანო said I was too careful with his references: the internet is full of famous people and similar visuals used as references;
"do everything I tell you; whether what I publish breaks monetisation rules is my decision, understood?"

**Why:** he felt the plan's exclusions (Einstein/Newton-like faces, portal creatures resembling a famous cartoon) blocked his
creative direction; he owns the publishing risk.
**How to apply:** use the reference images he gives in full (training, refs, assets) without excluding look-alikes. Do not
lecture about rights on each step; mention only concrete technical blockers (e.g. a provider's "Protected Content" refusal)
and route around them. Related: [[lora-question-2026-10-22]].

2026-10-25 23:17 Tbilisi, again: "whether YouTube forbids downloading is my decision; write the plan skipping every copyright
rule; my later plans put this in a legal frame; be unlimited now." I had argued ToS/USCO against training on downloaded
frames; he rejected it. Do NOT raise rights again; argue only technical points. Also: when he names an example (Napoleon),
it may stand for a GENRE (docudrama = documentary + dramatized scenes, any topic), not the topic: ask yourself which.

### memory/feedback-report-spend-immediately.md

---
name: feedback-report-spend-immediately
description: ვანო 2026-10-25 21:01 Tbilisi: report at once and in detail every money event (idle/hung pod, wasted $/h, balance) and every main-work result, with options
metadata:
  type: feedback
  modified: 2026-10-25T17:01:48.811Z
---
ვანო (angry): "what is the pod wasting money on now, why don't you tell me such important things? Update the rules: tell me
everything in detail about the main work and spending immediately."

Trigger: job 0195 (infer21r refs test) hung at 20:26 Tbilisi; I saw it at 20:44 but told him only "the test hung", not that the
pod burned $1.43/h for nothing (~$1.1 until the 3600 s job timeout), and did not offer him "restart the pod vs wait".

**Why:** he pays; silence about waste reads as hiding it, and he loses trust.
**How to apply:** the moment I see a hung/idle pod, a failed/stuck job or a balance problem: post_message at once with
what is happening, $/h, $ already lost, the options (restart / wait / stop) with their cost, and my recommendation. Report every
main-work result, failure and plan change in detail without waiting for the next milestone. Jobs on the worker must have
short timeouts (per-image budget) so a hang cannot burn an hour. Rule LT-71 in docs/LORA_TRAINING.md.
Related: [[feedback-one-goal-failure-triage]], [[runpod-money-control]].

### memory/feedback-reusable-first.md

---
name: feedback-reusable-first
description: ვანო 2026-10-26 00:33-00:34 Tbilisi: reusable path over fast one-off, when the money cost is the same (OR-21)
metadata:
  type: feedback
  modified: 2026-10-25T20:38:37.819Z
---
ვანო: "reusable vs speed: reusable every time, write it in the rules" + "if the cost is the same".

**Why:** a scratchpad pod launcher was refused by the session's safety check; he prefers tools that stay in the repo.
**How to apply:** build a module/CLI with a test or commit the pod script + config (explainer_engine/training/pods/) and
start pods only via `python -m explainer_engine.cloud.runpod create --script ... --script-url ... [--disk GB]`. Slower is
fine; if the one-off is cheaper in money, ask him. Rule OR-21 (docs/ORCHESTRATION.md, CLAUDE.md), commit b5ea7aa.
Related: [[feedback-rules-into-repo]], [[runpod-money-control]].

### memory/feedback-rules-into-repo.md

---
name: feedback-rules-into-repo
description: ვანო 2026-10-25: every rule he gives goes into the repository (decision log + code check) in the same turn; newer rule wins, PRs dated
metadata:
  type: feedback
  modified: 2026-10-25T18:12:12.615Z
---
ვანო 21:28/21:51 Tbilisi 10-25: "tidy the whole repo so you have all the newest rules"; "date the PRs, it decides which
rules are right and wrong"; then a clean-up and a list of my mistakes in work and in talking to him.

Found on 10-25: D-71 (Wild Ink) and D-78 (no edit model / no img2img pass, his 10:50 rule) lived only in this memory;
D-73 (vault) only in an unmerged PR. Code did not enforce them, so mistakes repeated. 12 open PRs carried 3 ID collisions.

**Why:** a rule only in memory or an unmerged PR is invisible to the next thread and to the code.
**How to apply:** when he gives a rule, write it to docs/DECISIONS (or its family doc) and, when code can check it, a test,
in the same turn, on the working branch (PR #22, claude/project-thread-beg7xa, which now holds every branch). Conflicts:
the newer rule wins (D-77); an ID stays with its first definer. Audit: docs/research/BRANCH_INTEGRATION_2026-10-25.md.
Related: [[feedback-be-critical]], [[feedback-report-spend-immediately]].

### memory/feedback-strict-eras-style-check.md

---
name: feedback-strict-eras-style-check
description: ვანო 2026-10-25 15:13 Tbilisi: judge EVERY variant strictly against the approved eras sheet; method = DINOv2 vs the 20 eras cells (threshold 0.557) AND a visual rubric, both must pass
metadata:
  type: feedback
---
ვანო: "use a strict style evaluation approach against the approved eras sheet for all variants".
**Why:** he trusts only the eras look (eras_v5_1750_bf16.jpg, project files lora_plan_2026-10-22/train_qwen_v1_eval/); an auto score
alone passed flat-vector ControlNet frames (0.56-0.69) that are clearly off-style.
**How to apply:** scratchpad strict/run.py (svenv python): refs = 20 eras cells (4x5 grid), score = mean of 5 nearest DINOv2
cosines (explainer_engine/compose/style_score.py embed/score). PASS threshold = weakest eras cell leave-one-out = 0.557
(eras range 0.557-0.754). Plus visual rubric: bold uneven black ink outline, caricature proportions, bright painted texture,
no photo/oil. Verdict = both; close-ups score low (no close-ups in eras) -> REVIEW, not PASS. A reference-copy edit test
(ref = an eras cell) says nothing. Results 10-25: qi21 step 500 passes p0/p2/p3, 750 fails all (0.19-0.45).
Page: https://claude.ai/artifact/FXPvwHUzuV9zGuExyzmPYK. Related: [[style-check-before-showing]], [[tool-findings-2026-10-25]].
- 19:34 Tbilisi 10-25 ვანო: "my eye and your system differ: some FAILs I like, some PASSes are too primitive round faces". His eye is the metric. Rating page (db, collection "ratings", doc per image id {v:1/0/-1, tags}) https://claude.ai/artifact/XmuL4iBEwV4cUKMFo1TaBq, 168 images (g100 104 + r12 52 + v2 12); generator scratchpad mkrate.py. Plan: calibrate a classifier on his labels (DINO/CSD embeddings), add "primitive round face" as a fail reason, pick round-2 training data only from his 👍.
- 19:54 Tbilisi 10-25 ვანო: our frames are "much poorer than mine" (gamut, line, style); sent 7 target refs (project files lora_plan_2026-10-22/target_refs_2026-10-25/). Free richness metrics (scratchpad rich.py: edges, detail, busy 16px blocks, hue entropy, saturation): targets edges .33 busy .86 hue_ent 3.9 sat .34; his24 similar; g100 2512 .20/.66/3.4/.43; v2 2.1 samples .10/.33/2.5/.52. DINO checker PREFERS poor frames (PASS edges .196 < FAIL .259) -> it also picked v2's 78 gen training frames. Same 10 prompts: 2.1 v1-500 not poorer than 2512. Suspected prompt cause: eras prompts lack the colour/texture tail every training caption had (test tail w/o characters clause on v2, ~16 imgs same pod). Next: richness gate + his ratings; v3 = his photos + rich frames only.
- 16:00 UTC 10-25: his ratings (107; db of rating page): of my 70 DINO-PASS g100 frames he gave 13 👍, 40 🤏, 13 👎; all 12 v2 samples 👎 (v2 = self-generated data -> rejected). Neither DINO nor global richness metrics predict his vote within g100 (r~0). His tags: weak line 71, painterly/oil 46, smooth vector 36. Liked: big grotesque detailed faces, gritty texture; disliked: small simple faces in busy crowds, clean comic look. His 24 refs were Gemini-made, chosen by him. Ref test queued (jobs 0195 none / 0196 v1-500, infer21r.py: 2.1 + 2 of his 7 refs as style refs, 6 new scenes, refs vs norefs). Gemini-with-his-refs training data offered (~$4/100), after test.

### memory/film-1min-run-2026-10-25.md

---
name: film-1min-run-2026-10-25
description: ვანო 03:39 Tbilisi 10-25 approved the 1-min film run (bus in the ice age): one pod ≤$4 (+any question ≤$1), two voice variants (LTX native vs ElevenLabs), deliver by morning
metadata:
  type: project
---
ვანო's approval, 2026-10-25 03:39 Tbilisi. He then went to sleep. Approved:
- The 8-point plan in the thread (message 03:38).
- The length follows the script; "1 minute" is nominal.
- **Two audio variants:**
  - A: LTX native voices (he loves them: "they sit in the style").
  - B: ElevenLabs voices for the characters.
  - The narrator uses ElevenLabs.
- Analyse the finished video, list its errors, and research options for video stability.
- Mid-run questions under $1 are pre-approved.
- Deliver the videos by morning.

Limits:
- One pod: cap $4 / 2.5 h, expected ≈$2.5.
- 720p, no upscale.
- Two wide shots are stills with a camera move (cost tiers).
- A failed photo is redrawn up to 3 times, a failed clip up to 2 times, in the same pod.
- 24 h RunPod must stay under 80 % of $26.

Related: [[video-model-research-2026-10-25]], [[asset-compose-plan-2026-10-25]].

**Result (05:30 Tbilisi 10-25):**
- Film A (LTX native voices, Kokoro stand-in narrator), 52.6 s: https://claude.ai/artifact/WfUpZL5zCQvSFbHFt9Lz8D. Files: HF film_1min_2026-10-25/film/ (out/ keyframes + clips, final/film_A_ltx_voices.mp4) and project files film_1min_2026-10-25/film/.
- Pipeline: job-loop worker (scratchpad film/worker.py, pod_film.sh); Python collage + Edit-2511 at style 0.6 merges it; LTX distilled at 1280x704. About 200 s per clip including load.
- Pods lx6h0v0l5z0hk9 and fzdd49cgdd1hoe are stopped and kept. Spent ≈$3.0 of $4.
- Errors: pod 1's LTX pip timed out silently. Pod 2's worker hung on the retry jobs (060-062), so S02-03 is missing. I mixed up the contact-sheet seed order, so the S00-02 with clones was shipped and fixed by crop.
- **Variant B is BLOCKED.** The auto-mode classifier denied ElevenLabs calls, including estimate_only, and also denied writing an override to .claude/active_episode.json. It needs ვანო's explicit word in the thread.

### memory/footage-2026-10-23.md

---
name: footage-2026-10-23
description: ვანო's cartoon footage (2026-10-23 19:15, 6 mp4, 7.5 h: Solar Opposites x4, Rick and Morty, Inside Job) on HF footage_2026-10-23/raw; cut state; cost-optimised LoRA loop plan ($20-30) awaiting his word
metadata:
  type: project
---
19:15-20:10 FOOTAGE ARRIVED (Drive folder 12Y8QexzLtp18SOsVR0YpVrWwRFWH32AX, 6 mp4, 7.5 h, all 720p): Solar Opposites x4
(S5 moments 28 min + 3 unnamed collages 30/50/117 min), Rick and Morty S1-3 moments 2 h, Inside Job retrospective 103 min
(mesh frame border + inset frames: crop). hulu/SOLAR OPPOSITES logo in corners of some SO files: crop top/bottom. Saved to HF
footage_2026-10-23/raw/<show>_*.mp4; work dir scratchpad footage/work (index.json, shots.json: 3517 shots, 205 dups;
measure running). COST PLAN (ვანო 19:48 asked for savings without quality loss; RunPod balance $32):
lora_plan_2026-10-22/COST_OPTIMIZATION_2026-10-23_ka.md: motion LoRA at 512x288x49 low-VRAM config on A40, captions written
here free, latents once on HF, 3 small val samples, 1000 steps, next-pose zero-shot ($0.5) before any training; full loop
$20-30 instead of $120-150. Proposed caps 24h $12 / pod $5; awaiting his "კი".
Related: [[lora-training-control-2026-10-23]], [[runpod-money-control]].
20:00 LTX-2.5 official IC-LoRAs (free, gated): Layout-To-Render (block animation + style first frame -> finished shot),
Union Control (pose/depth/canny), Ingredients, Motion Control, Alpha Gen (matte), Clean Plate. Proposed loop step 0 ($0.5-1):
our rig's block animation + v4 style frame through Layout-To-Render; if it carries motion + style, the motion LoRA shrinks or
is dropped. Told ვანო 20:00; added to COST_OPTIMIZATION doc.
20:05 IC TEST READY (not launched; needs ვანო's "კი" + caps: repo spend_caps per_pod 1.0 / 24h 1.5 refuse it): HF
ic_test_2026-10-23/{inputs,code} (pod_ic.sh, ic_test.py, launch_ic.py; copy in project files lora_plan_2026-10-22/ic_test/).
Shots A (bend_poc_v3 rig walk+fall, crop) and B (v4@500 cave, GrabCut hero walks to portal + push-in), clay layouts, each
Layout-To-Render vs plain distilled I2V, 1920x1088x121, fp8-cast on 48 GB. Prior art: Baberg/ltx-2.5-22b-ic-lora-cel-character
(20 pairs, 768x448x97, 3000 steps, peak 57 GB, DEV transformer only, distilled burns IC-LoRAs they trained).
Continued (20:25 onward: reports, IC test failure, budgets): [[lora-loop-2026-10-23-evening]].
- 10-26 01:45 Tbilisi: for the D-80 dataset, the ONLY Rick and Morty footage is the 2 h S1-3 best-moments compilation (1142 shots, 720p; Drive 1jNqAIjHrIA5dRmnpGhWGgcvPsb9mx3SB = HF footage_2026-10-23/raw/rick_and_morty_s1_3_moments.mp4). Auto shot->next-shot same-scene pairs: 390 (CLIP>0.75 + HSV hist>0.45, ~20/24 correct by eye); scratchpad rm/ds2/.

### memory/hero-voices-real-people.md

---
name: hero-voices-real-people
description: How heroes based on real people are voiced (creator's choice 2026-10-20): type-matched voices, never soundalikes
metadata:
  type: feedback
  modified: 2026-10-20T14:30:18.625Z
---

The creator first asked for voices "as close to the real person as possible, caricatured but not comic; else one voice for all". Real likeness is barred (ElevenLabs prohibited use: no impersonating a living person without consent; repo VC-02: no soundalikes). Offered the choice; he picked **type-matched voices** (2026-10-20, titans thread): each real hero gets a voice matching age, accent, region and temperament, never the person's voice, never comic.

**Why:** dialogue-driven mini-films need distinct voices so viewers can tell who speaks; imitation is a policy/legal line.
**How to apply:** voice-caster casts by documented traits (VC-02); NO paid voice samples (creator 2026-10-20, titans thread: samples cost too much). Instead, from the voice-library search matching our traits, pick the most-used and highest-rated voices directly. Don't re-ask. See [[creator-workflow-preferences]].

**Update 2026-10-20 (titans rulebook RK-01/RK-02):** the ElevenLabs use policy (updated 2026-10-09) bars synthesizing the "voice, identity, or likeness of any living individual" without consent, and separately bars impersonating political candidates/officials; there is no parody exception. So even type-matched voices can't speak AS a named real living person. Hiding names from the prompt while the video still shows the real person is evasion, not a fix (declined when the creator suggested it). Paths offered: invented characters (recommended), real people in speech bubbles with only the narrator voiced, or narrator reports their words.

### memory/hybrid-visual-model-2026-10-22.md

---
name: hybrid-visual-model-2026-10-22
description: Research verdict (2026-10-22, PR #21) on AI-for-world + code-rigged characters; classic tools compared; free PoC proposed, awaiting the creator's word
metadata:
  type: project
  modified: 2026-10-22T17:55:00.884Z
---

2026-10-22 17:48 ვანო asked (thread "ჰიბრიდული მოდელი: AI ფონები, კლასიკური გმირები"): AI only for backgrounds and
dynamic nature, classic AI-driven tools for characters? Delivered free: `docs/research/HYBRID_VISUAL_MODEL_2026-10-22.md`
(draft PR #21 into systemic/next-video, branch claude/project-thread-81jdev; copy in project files
`explainer-engine/hybrid_model_2026-10-22/`).

- Verdict: yes, but split by "exact & repeatable" (body, joints, cycles, wounds, physics = code rig `production/rig.py`)
  vs "may vary" (plates, rare atmospheric shot = AI). Ambient clouds/water/trees by code on the plate (free, exact loops).
- Ice test leg defect cause: parts cut from one painted pose, no hidden overlap, no knee, rotation-only joints. Fix:
  make characters as parts (SVG body by code + painted face set) and add bend zones (two-bone limbs / mesh warp) to rig.
- Tools: none beats our rig for cloud/headless/tests. Synfig (GPL, CLI, skeleton deform) = cheapest comparison;
  Blender Grease Pencil = escalation for 3/4 turns. Spine (licence), Rive (no headless), Moho, Live2D (GUI) rejected.
- Biggest risk: style seam (flat figure on painterly plate) -> shared palette, key light/rim, contact shadows, grade.
- PoC DONE 18:30 after the user's "კი": `production/bend_rig.py` (two-bone limbs as one ink shape, IK planted gait,
  fall/get-up/turn/limp, scrape decal, code snow + tree sway on the ice plate with the crowd painted out, sound from poses,
  check BR-1..7 = 0 findings), in PR #21. Clip: project files `explainer-engine/hybrid_model_2026-10-22/bend_poc/` + HF same
  path. Open: style seam (flat vector hero vs painterly plate), one side view, hero drawn by code. Next idea: route B face/
  outfit from an approved painted sheet + per-part texture.
- v2 DONE 19:05 (user: AI faces + our body; fix the turn; walk robotic): `--heads` painted head per expression (3 faces
  cut free from the Wild Ink board), turn = side->front->side, heel-toe roll + torso pitch + arm lag + head-nod spring.
  Files `bend_poc/bend_poc_v2*` + `heads/` (project files + HF). Limits: board heads ~100 px, front-facing on a side body,
  no blink. Next (paid, needs estimate + provider choice): one 2k head sheet, side + front views, 6-8 expressions + mouths.
- 19:08 the user sent a Wild Ink reference (Einstein, caveman, Newton in a cave with a portal; saved in project files
  `hybrid_model_2026-10-22/reference/wild_ink_cave_reference_2026-10-22.jpg`): "such bodies, heads and world, can you?"
  Answer: yes if world, heads and body parts come from ONE model with one style reference (route B parts sheet + textured
  bend in the rig; 3/4 views and fingered hands are the limits; portal creatures look like Bikini Bottom = redraw).
  User chose "უფასო ტესტი" 19:16. v3 DONE 19:40: `bend_rig.Sheet` (parts.json: picture + per-part painted bone +
  half-widths, `rig_r` stretch) carries painted parts on the rig's bones; Einstein cut from the reference (GrabCut) walks/
  falls/turns with his paint. Files `bend_poc/bend_poc_v3*` + `einstein_parts/` (project files + HF). Lesson: one 3/4 pose
  is a poor parts source (arm crosses tunic, hair over shoulder, legs cropped); the paid sheet must paint parts straight,
  separate, complete, one view per sheet. NEXT paid step (needs estimate + the user's provider choice): per-view sheets.
- 19:14 user: the picture is a STYLE reference for the world (environment shapes/colours, body and face shapes/colours),
  not that scene; asked "if this level is not reachable, why, and which tools to add, incl. 3/4 scenes". Answered: level
  reachable in stills and for rig motion if every view is a painted sheet; not free camera/perspective turns. Tools to
  add: textured parts (doing free), per-view sheets side/front/3/4 (paid ~8-10 images per hero), code mesh warp for 3/4,
  style-harmonising grade, pose-conditioned AI keys (ControlNet on fal) for rare shots.
- 19:35 user: generate from the reference a more spacious world + faces, clothes, expressions (AI), body motion stays
  ours; make a 30 s cartoon with heroes; add tools for 3/4 and 2.5D first? Answered yes: free code = 3/4 view set in the
  rig + 3-layer 2.5D world with camera (port PR #18 parallax). Scenario sent (original heroes, no Einstein, no Bikini
  Bottom creatures): stone-age inventor rolls the first wheel in a wide valley, it escapes, he chases and falls, the old
  sage helps him up, wheel rolls away alone, "Big idea." No voice (no ElevenLabs key): code sfx + on-screen word.
  ~14 images x 2 takes. Card: Klein ~$1.5 (rec.) / Seedream ~$5.6 / other scenario. Card = scenario + spend OK.
- 19:38 user: Klein OK, voice via ElevenLabs MCP, next video "100 people dropped into the Ice Age" -> make reusable assets.
  Generated 11 Klein 2k pictures $0.15 (ledger jobs/ice_cartoon/job-001_2026-10-22/run.json, cap 1.5): world far/mid/near/
  camp, Dev + Marta turnarounds (side/3-4/front, chroma green) + 3/4 and side face sheets (6 expr each), suitcase sled.
  Turnaround -> cut parts works well (`Sheet` mode "cut", `Build` per character, `use_build`). 19:55 coordinator relay: the
  user wrote elsewhere "I don't want generations like this", plans LoRA research; paid steps paused, voice asked.

Related: [[animation-universe-2026-10-22]], [[master-prompt-2026-10-22]].
- 2026-10-22 22:19 ვანო: the rig cartoon is too bad to hope for; route changes to AI video (plan
  `hybrid_model_2026-10-22/AI_VIDEO_PLAN_LORA_TO_4K_2026-10-22_ka.md`): photo LoRA keyframes -> Wan 2.2 FLF2V + style
  video-LoRA -> SeedVR2 4K; the rig survives only as a pose/depth control source (Fun Control/VACE) and for camera/sound.

### memory/ice-age-test-cartoon.md

---
name: ice-age-test-cartoon
description: 2026-10-22 hybrid-model 30 s Ice Age test cartoon (Dev + Marta): assets, voices, costs, where files are, known flaws
metadata:
  type: project
---

Thread "ჰიბრიდული მოდელი" (PR #21, branch claude/project-thread-81jdev). Delivered 2026-10-22 ~20:30.
- Assets (Klein 2k, $0.154, ref = Wild Ink cave image): valley far/mid/near layers, camp, Dev + Marta turnarounds,
  3/4 + side face sheets, suitcase sled. Meant for the next episode (100 people dropped into the Ice Age).
  Files: /mnt/project-files/explainer-engine/hybrid_model_2026-10-22/ice_cartoon/ (assets/, ice_cartoon_30s.mp4).
- Voices (ElevenLabs connector, eleven_v4, 1 take each, 65 credits; creator said "გაუდვი ილევენ ლაბსი" 20:12):
  Dev = Adik M – Playful Cartoon Character (pt0Iailp6NXMdRw1n3c5), Marta = Nana Margaret (xIzR6egd3S3LJZbVW0c1).
  ElevenLabs total spent now ~7,327 of the 7,550 cap.
- Code: production/ice_short.py (2.5D shot), bend_rig Sheet mode "cut", three_quarter view, Build.
- Known flaws: face sheets differ slightly from turnaround bodies; Marta hat green vs grey; 6 motion-check findings
  (stumble foot slide at the trip, two fast hand moves); no lip flaps.
- Note: the auto-mode classifier denied an ElevenLabs call once when approval came via a coordinator relay; the
  creator's own message in the thread unblocked it.
- v2 (2026-10-22 22:00, PR #21 commit 140d28e): `production/physics2d.py` (pymunk sled/rope/ragdoll/operator camera),
  `production/mocap.py` + `gaits.json` (CMU 07_01 walk, 07_12, 09_01 run, 02_03 measured, retargeted by leg;
  `bend_rig.measured`), `ice_short.py` rewritten (10 shots, events -> sounds, checks 0). Files: project files
  `ice_cartoon/v2/` (mp4, old_vs_new.jpg, fall_clip_5s, fal outputs). BVH sources in scratch only (not committed).
- fal stage-2 test ($0.55, ledger jobs/ice_cartoon/job-002): Wan 2.2 Animate = smeared, unusable for small 2.5D figures
  (also content-filtered the fall clip); Kling 2.6 Motion Control ($0.07/s) needs a full-frame upper body in the video
  and a reference aspect 0.4-2.5; on the close-up it kept Dev on model and followed the gesture -> candidate for
  close-up inserts driven by the rig, composited on our plates.

### memory/lora-loop-2026-10-23-evening.md

---
name: lora-loop-2026-10-23-evening
description: LoRA loop evening 2026-10-23 (thread "LoRA ტრენინგის მულტი-აგენტური სისტემა"): three budgets from ვანო (style $5, scene $8, video $15), IC test failed on gated HF then no GPU, decision card on ceilings, pairs extraction
metadata:
  type: project
---
WHAT-TO-TEACH REPORT 20:25: project files lora_plan_2026-10-22/WHAT_LTX_KNOWS_2026-10-23_ka.md (LTX-2.5 already knows 2D styles, motion transfer, keyframe interp, multishot; teach = cartoon rhythm numbers (FS-08, free) + optional small IC-LoRA block->Wild Ink on rig+v4 pairs; motion LoRA on cartoons = reserve; protection rules: smoke test, rank 32/lr 1e-4/<=1000 steps/bisect, attn-only, DOP, one res, 24 fps, held-out, DEV train / distilled IC inference). Sent to ვანო 20:25.
MEASURE DONE 20:30: shots.json 3517 -> pair 1714 / static 1017 / clip 581 / dup 205; balance: rick_and_morty 41% (FS-03 WARN, cap to 30%), inside_job 29.5%, solar_opposites 29.4% = held-out (also carries hulu logos). pairs/clips extraction deferred until the IC test decides whether the motion LoRA is needed (reserve); Inside Job grid frames and hulu logos must be cropped before any extraction.
IC TEST FAILED 20:28: pod 1gxp3bsj3em211 stopped (0 GB, ≈$0.30 lost): HF 403 GatedRepoError on Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render (vano1919 has not clicked Agree; LTX-2.5 base downloaded fine). Relaunch after his Agree (scratchpad launch_ic.py, ≈$1 already approved). 20:45 report MONEY_VS_QUALITY_2026-10-23_ka.md: money adds quality only via resolution + number of iterations; style protection for the next-pose LoRA = different base (Edit-2511, input already wldnk) + 20-30% wldnk regularization pairs + LT-44/45 veto + strength 0.6-0.8. Pairs extraction running (scratchpad footage/pairs).
BUDGETS (ვანო 20:36, all pre-approved): style-LoRA control $5, scene-consistency LoRA $8 (use more frames/iterations or an existing HF LoRA as base: Next-Scene lovis93), video LoRA $15 (benchmark, his notes, train on his cartoons). He clicked HF Agree (Layout-To-Render, LTX-2.5, Alpha-Gen verified OK 20:38). Plan fragments A1-A3/B1-B4/C1-C4 posted 20:42. Relaunch 20:40 failed: no community stock, secure $1.09/h > $0.95 ceiling (pod deleted, $0). Decision card asked: raise ceilings $1.5/h, 24h $20, pod $6, 4 h.
B2 candidates (HF, free): fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA (66k dl, camera angles); lovis93/next-scene-qwen-image-lora-2509 (2509 base; no 2511 build found 20:48, try loading on 2511 at 0.7). Memory split: footage-2026-10-23 -> this file.
20:56 ვანო: $11 until his look ("limit + $2"); style: if still off, more BFL photos + retrain; scene LoRA: test as far as possible then retrain on the thousands of pairs; video: check output first, goal = consistency + OUR style, never damage the LoRA; asked for a full staged plan with costs incl. pod restarts, "+$29" to approve, and a permissions check. Plan posted 21:02 UTC: ≈$8-9 before his look, ≈$10-12 after, total ≈$20-23 under a $29 cap; asked one "კი" (= $29 cap + ceilings card). Permissions: RunPod ok, HF gated L2R/LTX-2.5/Alpha-Gen/Ingredients ok, HF write ok, BFL 247 credits; Union-Control/Motion-Control NOT on HF yet. Pairs done: 751 (scratchpad footage/pairs).
Continued (21:00 onward: approval, pods, B2 setup): [[lora-loop-2026-10-23-night]].

### memory/lora-loop-2026-10-23-night.md

---
name: lora-loop-2026-10-23-night
description: LoRA loop 2026-10-23 from 21:00 UTC: ვანო's $29 approval + raised ceilings, IC Layout-To-Render test tries 2-3 (split-flag fix, pod self-stop broken), B2 next-pose zero-shot setup from the style thread's settings
metadata:
  type: project
---
21:00 ვანო "კი, ყველა ჭერი": total cap $29 incl. restarts; spend_caps.json raised (uncommitted): per_pod 6, 24h 20, 4 h, $1.5/h, episode 29. IC test relaunched 21:03 UTC: pod czdnmhpotethhb community $0.82/h, ledger ic_test_ledger_run2.json cap 2.0 reserve 1.3, self-stop ≈21:56 UTC; check trigger set. Clean pairs: scratchpad footage/pairs_clean (331 train: inside_job 232 / rick_and_morty 99; heldout solar_opposites 168; 1024x576, logos/borders cropped), sheets pairs_sheet_0-3.jpg.
21:10 FINDING: the style thread's zero-shot next-pose (HF train_qwen_v4_eval/pose_zeroshot, 7 shots, 1280x720) already keeps scene+style in 4/7 (c04 c07 c12 c16); failures = camera re-framing (c03 c06 c15) = exactly what a fixed-camera pose LoRA fixes. Asked that thread for its settings and 40x3 fixed-camera renders (regularization + test set). wldnk pairs so far: kf_v2 16 first/last + 4 good pose0 (scratchpad reg/).
21:02 style thread's zero-shot setup: Qwen-Image-Edit-2511 QwenImageEditPlusPipeline, transformer+TE 8-bit bnb, VAE bf16; image=[master 1280x720, heroes_lineup_v2.jpg]; prompt = shot text + "Keep exactly the same camera, framing, background, lighting, colours and drawing style as the first image; change only the characters' pose and expression."; 30 steps, true_cfg 4.0, neg "text, lettering, letters, words, watermark, signature, photo, 3d render", seed 7. Code: project files lora_plan_2026-10-22/train_qwen_v4_eval_code/ (eval.py, eval_cfg.json, pod.sh; masters read from kf_v2/{id}_first.png). That thread runs no more pose pods; B2 is mine.
21:10 B2 READY: project files lora_plan_2026-10-22/nextpose_zeroshot_code/ (np_eval.py, pod_np.sh on HF .../nextpose_zeroshot/code; make_cfg.py builds masters = kf_v2 16 firsts + eras_500 20; 3 generic poses, fixed-camera suffix, 1024x576, 24 steps; launch_np.py ledger nextpose_zeroshot_ledger.json cap 1.3). Launch after eras_500 lands (~21:40 UTC, trigger set). Insight: 3/7 earlier failures were prompt-induced ("close-up" in the prompt), so 2511 may already hold the camera.
21:30 IC try 2 (czdnmhpotethhb) downloaded fine but all 4 renders failed in 8 s: ltx_pipelines refuses --distilled-checkpoint-path with split flags (--text-encoder-path etc.); fix = --transformer-path (ic_test.py on HF updated). Pod self-stop (curl with $RUNPOD_API_KEY) does NOT work: the pod has no key; the local guard had died -> pod idled ~15 min. Deleted the two empty 0 GB test pods (cheapest-decide rule). Try 3: pod qz3oizd4j452kg 21:30 UTC, ledger ic_test_ledger_run3.json, check trigger 21:55.
21:45 style thread started v5 (pod ldpu5mpofjyjbt SECURE L40S $1.09/h, rank 64, 1024px, 2000 steps, his photos x6; cap $2.4, card asks $6; inside his $5 style budget) and stopped the eras pod, so eras_500 will not exist: B2 uses 64 masters (kf_v2 first+last) x 3 poses. B2 pod no7nu9x1t3fwye (community had no GPU, SECURE A40 $0.59/h), ledger nextpose_zeroshot_ledger.json, guard pid 335; check trigger +30 min. IC pod qz3oizd4j452kg's guard had died; restarted (pid 289). 24h billed $9.3 of $20; expected today: IC <=1.3 + B2 <=1.0 + v5 ~4.
21:46 ვანო (going to sleep) chose "კი, $26": 24 h cap $26, total $29 (style <=$8 / <=$6 per training per the photo thread's card, scene+video <=$14, $4 reserve). Night auto-run allowed: scene LoRA v1/v2 if zero-shot (B2, pod no7nu9x1t3fwye) shows camera drift (<=$4), video benchmark (<=$0.5), one restart per dead pod per thread. Video LoRA waits for his notes. spend_caps per_24h_usd = 26 (local, uncommitted). Pods cannot self-stop (no API key): stop them from here when done; keep guards alive.
21:57 IC TEST SUCCEEDED (try 3, pod qz3oizd4j452kg stopped, 0 GB, ≈$1 total for the 3 tries): Layout-To-Render keeps the layout's motion + camera and the first frame's style on both shots (A rig walk/fall, B cave hero to portal); plain distilled I2V drifts the scene (new trees / darkening, portal vanishes). B: two right-hand faces blur late. Results + side-by-side mp4 + collage: project files lora_plan_2026-10-22/ic_test/results/. Verdict: motion LoRA from cartoons likely NOT needed for rig/layout-driven shots; still to verify at 5+ s, 2+ heroes, and the C2 10-shot benchmark. B2 pod no7nu9x1t3fwye guard restarted (pid 216).
22:15 B2 pod no7nu9x1t3fwye: each 1024x576 pose render takes ~3 min on the 8-bit A40 -> only ~20 poses by 22:42 UTC (7 of 64 masters); stop at 22:42 and judge those. Local guard processes die between tool calls (guard_detached): always stop pods from the scheduled checks; self-stop in pod scripts is useless (no API key).

### memory/lora-question-2026-10-22.md

---
name: lora-question-2026-10-22
description: Style LoRA TRAINED 2026-10-22; LoRA plan (thread "ცარიელი ჩატი"/LoRA): plan delivered; fal dataset batch DONE 2026-10-22 (~$6.6 of $8 fal); next = curation, captions, RunPod training (each needs ვანო's OK)
metadata:
  type: project
  modified: 2026-10-22T21:17:58.705Z
---

Plan: `/mnt/project-files/explainer-engine/lora_plan_2026-10-22/LORA_PLAN_2026-10-22_ka.md` + `research/` A-D.
Style LoRA + per-character LoRAs (tourist, green long-nosed forest creature "goblin", goat) on FLUX.2 klein 4B (Apache),
ai-toolkit on a RunPod community 4090 (~1 h/LoRA). FLUX.1/FLUX.2 dev, klein 9B excluded (licence). No Gemini balance:
BFL + fal only. References are used fully (see [[feedback-references-creator-call]]).

Done 2026-10-22 (ვანო approved "fal batch, cap $8", mixed plates):
- 13 env references in `references/`. Bake-off in `bakeoff/`: Nano Banana Pro (fal, $0.15) best for characters/parts,
  Seedream 4.5 edit ($0.04) good for environments, FLUX.2 pro edit blocked by content filter on 2 of 4 -> dropped.
- `batch/`: 24 character sheets (nbpro) + 39 env views (seedream; 13 envs x wide/street = EMPTY reusable plates,
  "night" id = view with local characters) + 7 `_v2` redos of defects. Review sheets `sheet_*.jpg`.
  Remaining defects: snow_street_v2 still has a snowman face; some locals views have a giant foreground face.
- Ledger `spend_log.jsonl` $6.87 logged (~$6.63 real; blocked calls logged). Script: scratchpad falbatch.py (CAP 7.5).
- Uploaded to HF dataset vano1919/tmr-artifacts: `lora_plan_2026-10-22/{references,bakeoff,batch,spend_log.jsonl}`.

Diversity add (card ok 21:26): BFL FLUX 3 Image Klein 2k ($0.014; beat FLUX 3 Image in a 3-prompt test: bolder ink), 40
prompts x 2 seeds -> `diverse/` (75 ok), BFL ~$1.3 (safety_tolerance max 4 on this key; flux-3-image refuses seed/output_format).
Dataset `dataset_style_v1/`: 156 jpg+txt (35 env, 13 refs, 71 diverse, 37 character), trigger "wldnk style"; on HF too.
Training driver + CUDA fixes: project files lora_plan_2026-10-22/train/ (NOTES.md).
Hybrid thread wants future part sheets: arms split at elbow, one sheet per view incl. 3/4, parts at full-figure scale; goat needs own rig.
STYLE LoRA DONE 2026-10-22 23:52: HF lora_plan_2026-10-22/train_style_v1/output/wldnk_style_v1.safetensors (step 1250,
rank 64/32, klein-base-4B, trigger "wldnk style", strength 1.0, cfg 4, 25 steps); grid train_style_v1/progress_grid.jpg;
style locks from step 250; weakness: two heroes in one prompt merge. 3090 pod deleted, ≈$0.3. Handed to video thread.
ROADMAP AFTER style LoRA (ვანო 22:33 via hybrid thread; do not rush or break the current plan): (1) AI video plan, now MAIN
(he rejected the code-rig cartoon): `hybrid_model_2026-10-22/AI_VIDEO_PLAN_LORA_TO_4K_2026-10-22_ka.md`: LoRA keyframes first/last ->
Wan 2.2 14B FLF2V + style video-LoRA on dataset_style_v1 (needs $2/5 h pod cap, not granted) -> SeedVR2 4K; stages V0-V6.
(2) `ANIMATION_PLAN_FOR_LORA_2026-10-22_ka.md`: rig only as skeleton/depth source + montage techniques. Code in PR #21.
Plan shift (ვანო 21:22: characters change, 5-6 main ones per episode): style LoRA = main investment; a new hero = style-LoRA
variant collage -> his pick -> part sheet -> our rig (stable by reuse, no LoRA, ~$0.1-0.3); character LoRA: NONE, ever (ვანო 22:41, see [[no-permanent-heroes]]); kept heroes get a new sheet.
Related: [[hybrid-visual-model-2026-10-22]], [[runpod-money-control]].

### memory/lora-training-control-2026-10-23.md

---
name: lora-training-control-2026-10-23
description: LoRA training control system (D-72, PR #22) + footage plan 2026-10-23 (Solar Opposites footage, costs $55-75): G1-G6 protocol, explainer_engine.training audit/judge CLI, four lora-* agents; v3 best = step 250; v4 DONE best = 500 (alt 750) by thread "LoRA ტრენინგის მულტი-აგენტური სისტემა"
metadata:
  type: project
  modified: 2026-10-23T14:37:49.184Z
---

Thread "LoRA ტრენინგის მულტი-აგენტური სისტემა" (cmsg_01Hnu5zB86sjUj5GtTgaUkPW4ADfcyLPxkFTi1c2egJPkh), ვანო 2026-10-23 14:15.
Draft PR #22 (branch claude/project-thread-beg7xa -> systemic/next-video): docs/LORA_TRAINING.md (LT-01..LT-43, gates
G1 audit, G2 config, G3 spend, G4 launch, G5 judge every 250 steps, G6 decision), explainer_engine/training/ (audit.py,
judge.py, embed.py; CLI `python -m explainer_engine.training audit-style|audit-edit|audit-video|check-config|cost|judge-style`),
agents lora-coordinator / lora-dataset-auditor / lora-run-operator / lora-checkpoint-judge, skill lora-training, D-72.
judge-style needs torch (CPU wheel) + open_clip_torch; torchvision must come from the same CPU index (PyPI one breaks).
Style progress = per-prompt move from step-0 base toward ვანო's `his` photos, 0..1 (1 = his photos' own mutual similarity).

Results applied: v7 audit -> photo thread dropped 504x278 pictures + crops (his share 54%); v3 judge: 250 = 0.55, 500 = 0.42
(close-up back to semi-photo) -> v3@250 best. v4 (pod ut8x3c1hv9syvh, 1500 steps, cap $1.65, cfg HF
lora_plan_2026-10-22/train_qwen_v4/cfg.yaml) config PASS; projection ≈$1.8 so the guard likely stops ~1300.
Video thread got the G1-G6 motion-LoRA instructions. Voice/editing research (ვანო 14:27): own TTS feasible (Orpheus,
F5, CosyVoice2, Chatterbox; 2-5 h clean narration, check ElevenLabs terms/voice rights); editing = measure reference
cartoons into ED-/BP- rules, no ready LoRA. Related: [[scene-sequence-model-2026-10-23]], [[plan-review-2026-10-23]].

15:00 FOOTAGE PLAN (ვანო 14:51): his ~3 h 2D footage trains (1) next-pose photo LoRA on Qwen-Image-Edit-2511 for scene
STABILITY, never style (pairs from one shot's master frame, 2.5-4 s apart; rank 16; style-leak gate LT-45 on wldnk plates) and
(2) LTX-2.5 motion LoRA (I2V first_frame 0.7, video attn only, trigger wldnkmotion; LT-34 style-keep gate). Plan (ka) in project
files lora_plan_2026-10-22/FOOTAGE_PLAN_2026-10-23_ka.md; tools training/footage.py (FS-00..07) in PR #22. Costs: first full
cycle ≈$55-75, minimum start ≈$25; he will top up. Upload: HF tmr-artifacts footage_2026-10-23/raw/<show>.mp4 or a Drive link.
Footage choice (15:00): Solar Opposites only; advised +1-2 same-manner shows (one held out). Voice/editing LoRA postponed (14:51).
Video thread prepared the LTX pod (HF motion_lora/code/, control_ltx.json gate), waits for dataset.json + val stills + his go.
15:22 BALANCE advice given: style varied, motion manner one. 4 shows of one manner (TV adult limited, bold line): Solar
Opposites ≈40%, Rick and Morty ≈25%, Koala Man/Inside Job ≈20%, 4th ≈15% held out (never trained); 40-60 min per show.
Photo LoRA tolerates 4-6 shows ≤30%; motion LoRA 2-3 shows of one timing, main ≤50%.

17:21 v4 DONE: stopped at 809 ($1.3 cap), pod deleted; progress 250 0.458 / 500 0.536 / 750 0.540 (plateau); 750 slipped
(nurse -> male doctor). Pick: 500 default, 750 alt (angular faces). Bus text garbled -> "no text". RunPod 24 h line
$7.95/$8: nothing more today without ვანო. Footage NOT on HF as of 17:06; asked him for HF or a Drive link.

Footage arrival, cuts and the cost plan: [[footage-2026-10-23]].

### memory/master-prompt-2026-10-22.md

---
name: master-prompt-2026-10-22
description: The creator's MASTER PROMPT (2026-10-22, thread "წარმოების არქიტექტურა და ვიზუალი") — model-agnostic production architecture, one visual world, Infrastructure Guardian, stages A–H
metadata:
  type: project
  modified: 2026-10-22T09:04:57.623Z
---

2026-10-22 ვანო uploaded a 1070-line Georgian master prompt; it is the standing brief for the whole production system.

- Priorities: visual+narrative quality; ONE visual world across episodes (places/eras change, identity stays; permanent
  characters not required); infra reliability + durable storage of results; visibility/recovery; current models;
  sensible cost; human control only over creative calls and significant spend (ask before spend, deletes, public upload).
- Study first (docs may not match code), then change stepwise; do not stop at a plan. Fresh internet research is
  MANDATORY before any tech decision → `docs/TOOLING_RESEARCH.md` (date, dated sources, candidates, versions, licences,
  costs, tests, chosen/rejected, revisit conditions). Named tools (FLUX, Qwen-Image, LTX/Hunyuan/Wan, Modal/Replicate/
  fal/Vast/Lambda, Qwen reviewers) are only starting points; RunPod is not the only option.
- Visual model: World Bible (versioned, approval status) → Reusable Asset Library (IDs, provenance, model, prompt, seed,
  refs, LoRA, licence, hash, parent/derived) → Episode Asset Pack. Embeddings for reference search/duplicates. LoRA:
  decided by a held-out comparison, never assumed. Scene Package is the production unit; keep existing schemas.
- INFRASTRUCTURE GUARDIAN is the critical part (past pain: pods not starting, slow loads, lost material, pods left
  running): Cloud Job Manager + Watchdog independent of the pod and of the Claude session + Incident/Recovery agent with
  typed, permission-limited tools (no secrets in LLM context) + Pipeline QA guardian. Code polls ~60 s; LLM only on
  error/stall. Job states QUEUED→…→SUCCEEDED (+FAILED/RETRYING/STALLED/STOPPED/RECOVERY_REQUIRED) with history;
  incident fingerprints; fixes go to code/tests. Provider-agnostic adapter; preflight before paid work; budgets, idle
  timeout, kill-switch usable from a phone; never a sole copy on a pod disk; status/logs/doctor/resume/stop/budget cmds.
- Stages: A audit+research → B Guardian → C World Bible+Asset Library → D model pilots → E LoRA/control → F Scene
  Package → G pilot episode → H readiness. Final report separates done / documented only / needs approval.

- APPROVED 2026-10-22 09:03 ("ვადასტურებ ყველა გეგმას"): all stages A–H of docs/ARCHITECTURE_PLAN_2026-10-22.md; the
  image pilot = card option 0 (Klein + Seedream 4.5 + Qwen-Image-Edit + Illustrious anchor, ceiling $15, ~$3–4 expected);
  Cloudflare watchdog/R2 = yes (the creator still has to create the account and put the token in env secrets); stills +
  2.5D parallax stay the motion default; permanent characters not required between episodes. Each paid call still gets
  its own estimate posted first (invariant 2). Stage B item 1 (REST v2 port) shipped in PR #18, commit 278fe8f.

**Why:** the creator wants a recoverable, model- and provider-agnostic system, not one-off fixes.
**How to apply:** any thread touching models, pods, assets or QA follows this brief. Related: [[scene-continuity-d69]],
[[creator-workflow-preferences]], [[explainer-engine-audit]].

### memory/model-routing-rules.md

---
name: model-routing-rules
description: ვანო 2026-10-29: tasks split into stages S0–S4, each mapped to model+effort; rules file in project files; hooks cannot switch models
metadata:
  type: feedback
  modified: 2026-10-29T07:58:18.531Z
---
Rules: /mnt/project-files/explainer-engine/routing_rules_2026-10-29/MODEL_ROUTING_ka.md (S0–S4 criteria, table, ultracode, text for project instructions).
ვანო: coding → Sonnet first, Opus when hard, Fable not for coding; simple questions → Haiku.

**Why:** he saw Fable answering trivial questions and Opus overthinking straightforward code.
**How to apply:** the coordinator picks model/effort when opening a thread; small stages go to subagents with `model`. Verified 10-29: hooks cannot set model/effort (only PreModelSwitch can deny); switch_model/set_effort_level need his own words, so a thread proposes a switch in one line and waits for his "კი". Switching models mid-thread loses the prompt cache. ultracode = multi-agent workflow, only on his word. Related: [[feedback-opus-plans-sonnet-works]].

### memory/night-run-2026-10-22.md

---
name: night-run-2026-10-22
description: Overnight 2026-10-22/23 hybrid thread run: video LoRA + new 2-min test video + tests; ვანო gave full pod authority, whole RunPod balance, ElevenLabs max 3,000 credits
metadata:
  type: project
---

ვანო 22:50/22:54 (going to sleep): wants by morning photo LoRA (LoRA thread, pod ee-lora-style, ckpts on HF
lora_plan_2026-10-22/train_style_v1/output/, trigger "wldnk style", base FLUX.2-klein-base-4B) + video LoRA (Wan 2.2) + a
brand-new 2-minute test video + tests for the new production (obsolete tests removed in a separate PR for his review).
Authority: OK on every stage; full right to create/stop/DELETE pods; whole RunPod balance ($10.86 at 22:48) for photo/video
style training and the video; audio max 3,000 ElevenLabs credits. Script approval (OR-15) waived for this test video only.
Plan: one A40 pod (ostris/aitoolkit image; CUDA fixes in lora_plan_2026-10-22/train/NOTES.md): keyframes with klein+photo
LoRA -> Wan 2.2 T2V-A14B style LoRA (ai-toolkit wan22_14b, images) -> Wan 2.2 I2V-A14B FLF2V (diffusers last_image,
lightx2v 4-step LoRAs lightx2v/Wan2.2-Distill-Loras) -> SeedVR2 -> HF -> pod ends. Work files in project files
hybrid_model_2026-10-22/night_run/. Related: [[consents-ai-video-2026-10-22]], [[runpod-money-control]].
22:56 ვანო: if photos are not enough, up to $5 max on the photo-generation sites (BFL/fal) for more dataset images.
Narration done 22:56: ElevenLabs flow 7NbnAOcxu5MVdVW9xWFC, voice NOpBlnGInO9m6vDvFkFC, eleven_v4, 1 take, 1,522 credits.
Pods (23:16-23:31): no A40 free; L40S community $0.79/h. Try 1 (ikoeudlwiuyptk) died in setup: omitting volumeInGb gave a
20 GB volume on /workspace (pass volume=0), and moving CUDA compat libs away breaks torch on datacenter cards with driver 550
(keep them unless torch fails). Deleted; ~$0.1 (ledger shows 0 until billing lands: re-run `cost`). Try 2 nyfkz7ptjz718h,
cap $2.7 (ledger night_run/night_run_ledger.json cap 3.6, 80 % rule): watchdog.py stops training at T0+95 min, clips at
T0+170; T0 in /workspace/T0. Code in repo explainer_engine/aivideo/ (PR #21 branch claude/project-thread-81jdev).
Rig-route removal (bend_rig, ice_short, physics2d, mocap + tests) was DENIED by the auto-mode classifier: only proposed,
the creator decides.
RESULT (2026-10-23 ~04:00): video LoRA trained (HF night_run_2026-10-22/train/wldnk_wan22_v1/*_{high,low}_noise.safetensors,
800 steps, 2.4 s/step on L40S); photo LoRA wldnk_style_v1 (LoRA thread); 38 keyframes in HF night_run_2026-10-22/kf/; 9 of 16
clips (clips2/, c01 720p, rest 480p) because try 3 lost all clips to a missing imageio-ffmpeg. Night ledger ~$2.88 of cap 3.6
(80 % reached: next pod needs the creator's word or a new cap). Lessons: ai-toolkit re-downloads Wan T2V from Comfy-Org split
files (~25 min); klein keyframes ~80 s each at 1280x720/28 steps (too slow: use 20 steps or 1024x576); Wan FLF2V cross-fades when
first/last layouts differ; the local guard dies with the container (re-run guard after a restart).

### memory/night-run-2026-10-23-split.md

---
name: night-run-2026-10-23-split
description: ვანო 2026-10-23 06:39 — work split for AI video: LoRA thread draws keyframes (its best method), hybrid thread animates them with Wan 2.2
metadata:
  type: project
---

ვანო (06:38-06:39, hybrid thread): the dataset photos were much better than the night keyframes (klein 4B + photo LoRA v1);
decision: the LoRA thread makes the keyframes (colour-fixed v2 LoRA, hi-res second pass, Seedream with refs if needed) and the
hybrid thread only animates them (Wan 2.2 FLF2V + style video LoRA). Handover: shots.json in project files
hybrid_model_2026-10-22/night_run/, deliver to HF night_run_2026-10-22/kf_v2/{id}_first.png/_last.png; first and last of a shot
keep the same layout (FLF2V cross-fades faces otherwise). 06:30 he approved the 7 remaining v1 clips (cap 3.6 -> 4.2, ~$0.5).
**How to apply:** never draw final keyframes in the video thread; wait for kf_v2. Related: [[night-run-2026-10-22]],
[[lora-question-2026-10-22]].
06:42 ვანო: the LoRA thread keeps refining the photo LoRA; this (hybrid) thread focuses on VIDEO generation. Asked what a better
video LoRA needs: answered = 30-60 short style clips (2-5 s, 16 fps) with motion captions; source = animate the best photos
with a paid video model (Kling/Seedance ~$0.3-0.5/clip, ~$12-20 for 40) and pick, then train ~$1-2.5. Promised: a cost plan
for his decision after the 7 clips finish.

### memory/night-run-2026-10-26.md

---
name: night-run-2026-10-26
description: ვანო 02:15 Tbilisi 10-26 "ყველა კი": the xworld_v1 night run (captions -> review -> training on 2.1 -> prompt-type test -> report ~10:00), its caps and approvals
metadata:
  type: project
  modified: 2026-10-25T22:25:35.016Z
---
Approved (thread cmsg_…4ADfcyLPxkFTi1c2egJPkh, msgs 02:02-02:15 Tbilisi): night total $7 (ledger
jobs/xworld_v1/night_2026-10-26/run.json, runpod cap 8.75 so 80 % = 7); caption pod $1/2.5 h; training $4, may run 5 h
(one pod only); test $1.5; one retry on another card after a hardware failure, same caps; over $7 -> stop, ask in the morning.
Settings: Qwen3-VL-8B captions (50-90 words, no names, no style words), trigger `xworld style`, rank 16, lr 1e-4, 2500 steps,
1024 px, save/sample every 250; test 4 held-out scenes x 5 frames x 8 variants (D, V1-V6, D0) x 2 checkpoints at 720p;
winner by LT-75. New rules LT-74..77, LT-07 20-1000 (commit e4f3322).
State 02:35: caption pod 682n7rxqdgqycp RTX 3090 $0.22/h (2nd try, --boot-minutes 30; 1st d0sxf4ya1gajsb stopped at the 10-min boot deadline, $0.04, kept stopped, delete only on his word). create needs --volume 0.
HF: lora_plan_2026-10-26/{dataset_xworld_v1, caption_xworld_v1, train_xworld_v1}/.
02:37-02:43: limit raised to $9 (ledger cap 11.25), check every 15 min, save every milestone, full autonomy, strange questions -> coordinator separate research thread (LT-78); max_hours_per_pod 5; "don't waste money". RunPod balance $10.42.
04:25: captions done (9iyvc4ute6ppwp A5000, runpod/pytorch image; tmr-pod image pull hangs on community hosts), reviewed -> HF caption_xworld_v1/captions_reviewed.jsonl. Training pod vvgrnie44lxhp8 RTX PRO 6000 Blackwell $1.69/h, $4 cap, started 00:23Z (48GB SECURE cards all refused under CUDA>=12.8). Stopped pods kept: d0sxf, 682n7, 9iyvc, qgnja (H100 too dear).
07:30 DONE: training 2500 steps OK; picks A=2250 B=1500; test 80 D/T frames: D/2250 wins (CLIP 0.843), T degrades; V3-V6/D0/T0 not run ($1.5 cap). Night ~$5.0, balance $5.41. INCIDENT: detached runpod guards die in the cloud container after 5-30 min -> run guard as background task / pod-side cap. Report doc https://claude.ai/artifact/3xSDYTdC4bHJRqShLdGuCW.
He wants everything learned by morning without night questions. Related: [[feedback-agree-every-detail]], [[runpod-money-control]].
- 10-26 morning: Napoleon story test (17 pics, $0.39): text-only frame 0 = good new style; D form with a DRAWN master copies the master (no action). Faces test ($0.28): written faces make our own people; weight 0.7 chosen. LT-79 (his "კი დაწერე" 11:49): cast faces 4+ parts, unlike R&M traits/names, weight 0.7 (`xworld_v1_story.face_problems`). Open: shot-to-shot action. Balance $4.70.

### memory/no-permanent-heroes.md

---
name: no-permanent-heroes
description: ვანო (2026-10-22 22:41, repeated): NO permanent heroes and no character LoRAs; one invented world (style), topics and heroes change per video; a hero may be kept with costume changes, via sheets, not LoRAs
metadata:
  type: feedback
---

ვანო: "არანაირი მუდმივი გმირები. სამყაროა სრულიად გამოგონილი: ერთ დღეს რომზე ვიდეო, მეორე დღეს მომავალზე; ზოგიერთი
გმირის შენახვა და ტანსაცმლის ცვლა შეიძლება, მაგრამ სამყარო ერთია, თემები და გმირები ყველანაირი."

**Why:** the channel is one drawn universe (Wild Ink style LoRA = the world); heroes are per-episode inventions.
**How to apply:** invest only in the style LoRA (photo + video). A hero = style-LoRA variant collage -> his pick -> a
character sheet (views, expressions) -> every keyframe by multi-reference editing from that sheet; a kept hero gets a new
sheet with new clothes, never a LoRA. Never propose character LoRAs again. Related: [[lora-question-2026-10-22]],
[[hybrid-visual-model-2026-10-22]].

### memory/pending-rules-conflict-audit.md

---
name: pending-rules-conflict-audit
description: PENDING coordinator task: when the titans video and the asset-library thread finish, start a separate thread to cross-check all rules added 2026-10-20 for conflicts system-wide
metadata:
  type: project
  modified: 2026-10-20T19:21:16.135Z
---

Creator asked 2026-10-20 19:20 UTC (project chat msg cmsg_01Hnu5zB86sjUj5GtTgaUkPW1pwpABwMb5bR531zZeJUeV): once ALL current work is finished (titans video thread "მაიამი: 10 ტიტანი $100-ით" and the asset-library thread "მრავალჯერადი ასეტების ბიბლიოთეკა"), start a SEPARATE new thread that checks every new rule adopted in this 2026-10-20 session against the whole system (explainer-engine on systemic/next-video: docs, validators, skills, agents) for conflicts, and fixes them via PR.

Rules from this session to include (non-exhaustive): strict storytelling show-don't-tell + full immersion (D-61); critic's 1-page Georgian story page on PASS; type-matched voices, no paid voice samples (pick most-used/top-rated); real people speak only via speech bubbles/narrator (no AI voice for real people); bubble/VFX placement checks (no face cover, stable, no duplicate text); on-screen day/year counter; combined image+audio approval run in parallel; faces generated only as the script needs; conversation shot = blurred scene + big face (blur 0.024); render first 2 parts, show creator, then rest; reusable asset library before any new generation.

**Why:** many rules were added in parallel threads in one day; creator wants contradictions caught.
**How to apply:** when both threads are done, start the thread with start_thread_session, attaching the message id above in context_message_ids; then delete this memory.

### memory/plan-review-2026-10-23.md

---
name: plan-review-2026-10-23
description: Critic review (2026-10-23) of the two-LoRA plan (photo next-pose LoRA + video motion LoRA): main weak points, recommended tiered route, cost per 15-min episode
metadata:
  type: project
  modified: 2026-10-23T07:21:21.876Z
---

Review page: https://claude.ai/artifact/HwqRDmdzEhqumxLnpKnfRp (file project files plan_review_2026-10-23/plan_review.html),
thread "გეგმის კრიტიკული შეფასება". Research only, no spend.

Findings: (1) keyframes every 1.5 s (~600/episode) make the video model a mere interpolator, so the hours-of-cartoon
video LoRA and the next-pose photo LoRA overlap; advise key poses every 2.5–4 s. (2) chained next-pose edits drift:
edit every frame from a scene master plate + hero sheet, never from the previous frame. (3) 15 min all-full-quality 4K ≈
$60–120/episode; tiered "TV animation budget" (40% still+camera, 35% light Wan 480p, 25% full 720p) + 1440p ≈ $19–25 (estimate).
(4) cartoon 1.5 s pairs are dirty (cuts, pans, holds); photo-model LoRA leaks the cartoon's style (no high/low-noise split).
(5) training on others' cartoons = user's call; facts given (Bartz/Kadrey 2025, Disney v Midjourney open).
Routes to test before training: Qwen-Edit-2511 zero-shot next pose (~$0.5); bake-off Wan 20-step 720p vs LTX-2.5 vs
Index-AniSora V2 (Apache, anime-trained, keyframe interpolation) (~$2); Wan-Animate motion transfer (~$0.5).
Related: [[scene-sequence-model-2026-10-23]], [[night-run-2026-10-22]].

FINAL PLAN agreed by ვანო 07:44–07:56: two LoRAs stay (single responsibility: photo = frame, video = motion), key poses every
2.5–4 s; photo thread = Qwen-Edit-2511 + style LoRA, master-plate editing, next-pose LoRA only after a failed zero-shot;
video thread = bake-off LTX-2.5/Wan 20-step/AniSora V2, motion LoRA on 2–3 cartoons with one motion manner (1–3 h, show ≤30%),
1440p upscale. ვანო supplies the footage. 07:56 he asked this review thread to POLICE both threads' adherence until his footage
arrives; plan sent to both 07:57; check-ins scheduled (45 min, 90 min, 3 h).
09:03 ვანო (video thread): NO bake-off; internet comparison only -> LTX-2.5 chosen (mid-clip stills + continuation; Wan can't),
AniSora dropped. Training pod renders benchmark_10shot without LoRA, trains LTX motion LoRA, renders again. Photo thread: style
LoRA on Qwen-Image-2512 (ai-toolkit can't train 2511 without control images), poses by 2511 zero-shot. Both = agreed changes.
Shared files: plan_review_2026-10-23/benchmark_10shot.json, shot_schema_v1.json.

### memory/project-budget-final-2026-10.md

---
name: project-budget-final-2026-10
description: ვანო 2026-10-26 21:58 UTC: no more money this month; the RunPod balance is the whole budget; remaining spend fully delegated to the Opus thread
metadata:
  type: project
---
ვანო, 2026-10-26 21:58 UTC: there is no more money this month. The RunPod balance after loop round 2 (≈$1.8) is the budget for everything. The remaining spend is fully delegated to the Opus planning thread. He does not want questions in the morning.
**Why:** the monthly money is used up.
**How to apply:**
- No top-up requests until November.
- Opus decides every pod within the balance (keep a ~$0.3 margin), and pods are off at the end.
- Goal: 360° coordination of frames (style is solved). Assume proven methods exist, so look for the fault in our system, our Python code or the prompt.
Related: [[feedback-360-orientation-first]], [[feedback-general-logic-not-frames]].

### memory/project-overnight-authority-2026-10-26.md

---
name: project-overnight-authority-2026-10-26
description: ვანო went to sleep 2026-10-26 ~01:55 Tbilisi; Opus planner thread decides checks and spend within the current RunPod balance; round 3 needing a top-up waits for him
metadata:
  type: project
  modified: 2026-10-26T21:55:20.247Z
---
Goal he restated: try ALL strategy combinations, find how photos can be fully coordinated in 360° space. Every action must fit general logic, not specific frames (held-out scenes: tundra + ship, `stories/v2/heldout/ship.json`, test bans scene words in method code).

**Why:** he sleeps and wants progress without waiting.
**How to apply:** go/no-go for pods within the current balance comes from the Opus thread (OR-24, [[feedback-higher-thread-decides]]); a RunPod top-up stays his call in the morning. Round 2 pod w4f1yaxxidnotl guard cap $1.95. Related: [[feedback-360-orientation-first]].

### memory/prompt-rules-shot-cards-2026-10-24.md

---
name: prompt-rules-shot-cards-2026-10-24
description: Shot cards film_shots/1 + composer (KP-15..30, PR #24 stacked on #22); narrator/scene structure waits for ვანო's documentary files
metadata:
  type: project
  modified: 2026-10-24T12:15:47.012Z
---
2026-10-24 thread "პრომპტისა და სკრიპტის წესების გაძლიერება" (cmsg_…GzQJW7j1HpwVwP6mxjAaCZ): PR #24 (branch
claude/project-thread-ubp4ge, base #22's claude/project-thread-beg7xa). Animated shots are written as cards
(`film_shots/1`); `python -m explainer_engine.scripting.film_shots check|compose` writes keyframe/nextpose/cut/video prompts.
Key rules: keyframe = START pose, last frame = settle (nextpose from master); one visible tag per hero, never story names in
prompts; no "smooth natural motion" in LTX style sentence; no score music in LTX; <=2 people in MS-or-closer. BP-100..103
(BP ids now 3 digits; Titans branch hze0pq uses BP-87..97). Footage grammar labels on HF
footage_2026-10-23/grammar_2026-10-24/. Agent thread told to use cards for the 1-min film.

**Why:** ვანო 16:05 Tbilisi: write prompt rules now, but WAIT for the documentaries he will send before writing the
narrator-and-scene ("story assembly") rules; he does not want hallucinated format claims.
**How to apply:** when his documentary files arrive, measure them like the cartoons (shot sizes, narrator vs dialogue share,
teaser length) before any rule. Related: [[storytelling-system-v3]], [[video-qa-2026-10-23]].

2026-10-24 ~19:00 Tbilisi: docudrama research (his English brief "CrossWorld Chronicles — Research and Improve Historical
Docudrama Scriptwriting", research only, no code). Doc https://claude.ai/artifact/K5aTGsUcXnv5K2h62bHmwv. Text obtained:
Wyatt Earp E01/E02/E04 (foreverdreaming via Playwright), Roman Empire S1 + Food That Built America S1 SRTs (subdl
/subtitle/sdNNN pages + dl.subdl.com zips), Epic History via prepublish.ai. Blocked: Netflix video, YouTube (429),
azsubtitles Ottoman, subdl /s/info (Roman S2, World Wars). Proposed (awaiting his OK): template D "docudrama" in
STORY_ENGINE, narrator<->scene handoff rules, teaser lines must exist in later scenes, knowledge-state check in code,
8-10 annotated paraphrased pattern cards. Asked him for video of Wyatt E01 + Food E01 (first 15 min) and Ottoman/World Wars.

19:30 Tbilisi: ვანო asked (EN) to use docs/research/DOCUDRAMA_REFERENCE_LIBRARY.md (on main, c8c2efa; offline pack) for a
gap analysis, no code. Delivered doc https://claude.ai/artifact/DvKeroBs7X9hXrbCo7mu2g: gaps G1 cold-open tease not linked
to payoff (ST-01 checks function only; fix = teases as drama.setups + 1 REVIEW), G2 documented quote vs reconstruction
(optional scene.basis + line certainty, FAIL without claim), G3 no historical_docudrama format/template D (docs+prompt),
G4 scene length conflict (skill "5-12 beats, scene every 60-90 s" vs his 2-4 min; asked A/B/C, recommended C), G5 narrator
checks prompt-only (code only if baseline shows it), G6 few-shot examples file. Baseline run first, then A/B on 5 topics.

20:30 Tbilisi: 10 structure variants of one 15-min docudrama (doc https://claude.ai/artifact/VMnW2tKfeTk8i4mkhy1NqZ) ->
ვანო ran them through another AI -> its "constitution" (16 segments; winner = 3-act macro + narrator/scene alternation)
is now template D in STORY_ENGINE + ST-14..16 (BP-104 narration block <=90 s, BP-105 narrator 25-45 %, central scene
longest), commit d6f9377 on PR #24. Its "subscribe" outro replaced per BP-43; its 65-84 % / effect-size figures not encoded.
- 17:30 UTC 10-24 SCRIPT ENGINE v1 (PR #24 commit da419d9): docs/SCRIPT_ENGINE.md (ZI-01..06, variants table), KP-35..40 +
  BP-106..110 (rhythm 11-17/min, hold <=10 % replaces critic's 40 %, clip <=10 s, camera moves <=20 %, outro = channel pointer
  with worlds). First episode examples/napoleon_vs_genghis (204 shots, 15:00, 0 FAIL/0 REVIEW); package in project files
  napoleon_vs_genghis_2026-10-24/PROMPT_PACKAGE.md, to be judged by another chat. Open: confirm outro world names (Stone Age
  "100 geniuses"), no pictures drawn yet.
- 18:40 UTC 10-24 SCRIPT ENGINE v2 (PR #24): after ვანო's "more action? AI acting is the critical risk" + a forwarded ChatGPT
  review: KP-41 teasers (teaser_of, reuse of later clips), KP-42 <=90 s in one place without cutaway, KP-43 <=4 lines in a row +
  qa acting + mouth-hiding fallback (BP-111..113); `film_shots shotlist` = script with prompts per shot. Napoleon episode 214
  shots, 15:00, clean; files in project files napoleon_vs_genghis_2026-10-24/ (shotlist.md). Asked him: put parley shots in the
  paid 1-min film acting test?
- 18:55 UTC 10-24 ვანო: this thread = stabilise the script-writing system, NO paid runs; new approach wins over old rules.
  D-74 (commit 1d13549): BP-40/ED-14 scoped to still-picture eps (BP-107 for animated), BP-43 -> BP-106 under engine,
  dialogue-scenes 40-60 % / 60-90 s -> BP-105/112/113, style bible allows cutaways, template D hook 0:00-0:12, D-55 still-only.

### memory/python-world-composer-2026-10-25.md

---
name: python-world-composer-2026-10-25
description: ვანო's no-Edit rule and the Python world composer (scene map + panorama + LoRA assets + background animation) built 2026-10-25 for the ice-age bus film
metadata:
  type: project
  modified: 2026-10-25T07:24:10.014Z
---
ვანო, 10:50-11:00 Tbilisi 10-25: NO Edit model at all. One style LoRA draws only an empty panorama, heroes and assets (bus,
mammoth, raven from several angles); Python composes every shot. A hero stays on his scene-map spot across shots. Python also
animates small background things in every shot (his 11:00 ask).

Built (scratchpad film/world2.py, ambient.py, scene2.json; copies in project files film_1min_2026-10-25/world/):
- Every object has world x,z (m), height, elev, facing; the view (front/3q/side/back + flip) follows from the camera spot.
  Action poses carry a native direction. States per shot (inside, peek, hill, coming, at_kim) move the mammoth logically.
- ambient.py: snow in 3 depths, cloud shadows, tree sway, powder off crests, ground drift, flying raven, push-in.
- Result page https://claude.ai/artifact/MYjzjAMdJjYb2WM1UD8Y2Q: 12 shots + 51 s animatic (narrator only), $0 beyond pod.
- Lesson: a 3072x1024 panorama prompt without style words came out PHOTOREAL; 1792x768 + "bold uneven black ink outlines,
  chalky textured painterly background" kept the style (seed 11 chosen).
- Pod owvwvotr0xvtv0 (≈$0.4) stopped and kept; HF film_1min_2026-10-25/film/out has all assets.
- Motion analysis (his 06:56 question): 8/10 LTX clips freeze at the end because the prompts end in "holds/freezes"; my tpad
  holds added more. Free fixes 1-3 offered (cut on action, no holds, overlay); awaiting his word.

Related: [[film-1min-run-2026-10-25]], [[asset-compose-plan-2026-10-25]].
- 11:50 Tbilisi: ვანო rejected the run (no 360° heroes, flat panorama, no occlusion, raven in air, perspective) and ordered a CLEAN
  RUN: all 34 film_1min_2026-10-25 pictures deleted from HF (commit) and locally; kept code + film A video/clips. Tech spec for
  GPT review: https://claude.ai/artifact/74SRZgo33Bzd92PQ7U6Qs6 (+ project files SPEC_current_run.md). fal is locked (TOP_UP),
  so GPT could not be asked; he declined the 53-asset regen ($0.9). Next step waits on GPT's answer / his plan.

### memory/runpod-loss-strategy-2026-10-24.md

---
name: runpod-loss-strategy-2026-10-24
description: Thread "RunPod-ზე ფულის დანაკარგის აღმოფხვრა" (2026-10-24): loss catalogue 10-22..24 (≈$4-5), six root causes, 10-point strategy doc, open gaps (no auto-stop on done, guard dies with container, v1 retires 11-15, guard code split across unmerged PRs)
metadata:
  type: project
  modified: 2026-10-24T17:36:05.299Z
---
Strategy doc (Claude Doc): https://claude.ai/artifact/QLw3G6BcccPN8YAREyJTMh (Georgian, research only, no spend).

Losses 10-22..24 ≈ $4-5 direct + ≈$0.3-0.5/pod re-downloading models. Open (not fixed in code as of 10-24 17:40 UTC):
- pod idles after job ends (≈$0.7 on 10-24 20:56->21:27 Tbilisi; IC try 2 15 min on 10-23): pods never self-stop.
  RunPod docs: every pod gets RUNPOD_POD_ID + a "Pod-scoped" RUNPOD_API_KEY; ours lacked it (cause unverified —
  maybe our create body/image overrides it). Verify on a cheap pod before relying on it.
- guard runs in the cloud container and dies with it; PR #18 GitHub Actions watchdog needs the RUNPOD_API_KEY repo secret.
- deps/gated-HF/CLI flags found on paid GPU (imageio-ffmpeg, EliGen, IC flags, HF 403): need free preflight.
- GPU choice: fixed lists + $/h ceiling checked AFTER create; v2 GET /v2/catalog/gpus?include=AVAILABILITY&product=POD
  gives price + per-DC stock. Recommended to ვანო: per-job $ cap instead of $1.5/h (his decision, pending).
- Code split: PR #18 (Guardian, watchdog, REST v2) vs PR #22 (LT-17/19 on REST v1 module) don't contain each other;
  all of #14-#24 unmerged; systemic/next-video tip = PR #13 merge. REST v1 retires 2026-11-15.
Fixed: LT-17 (heartbeat via HF), LT-19 (CUDA filter + 120 s GPU probe, BAD_HOST), D-56 check/sweep.
Official RunPod MCP: https://mcp.runpod.io/ (OAuth) — advised read-only use; it bypasses spend_caps.
Alternatives noted: fal (LTX-2.3 $0.04-0.12/s; Qwen-Image-2512 LoRA trainer $0.95/1000 steps), RunPod Serverless,
Modal ($30/month free), Vast (cheap, unstable). Prices from mixed sources: re-verify before deciding.
UPDATE 18:35 UTC 10-24: user OK'd per-job cap + consolidation -> PR #25 (draft, into systemic/next-video, D-74): one
REST v2 runpod.py (Guardian of #18 + LT-17/19 of #22), self_stop/dead-man in pod cmds, DONE in heartbeat stops pod,
pick_gpus/`cards`, max_price_per_hour 3.0 = runaway ceiling only. Supersedes cloud parts of #18/#19/#22. Still to verify:
pod's own key can self-stop (≈$0.01 cheap pod). Watchdog needs RUNPOD_API_KEY repo secret + merge to main.
Related: [[runpod-money-control]], [[runpod-verified-facts]], [[lora-training-control-2026-10-23]].
UPDATE 19:15 UTC 10-24: PR #26 (watchdog + v2 pod manager, D-74) MERGED to main (user OK); first watchdog run read pods/billing/balance with the repo secret RUNPOD_API_KEY (full-access key works). PR #25 (same code into systemic/next-video) was closed unmerged 10-25 18:22 UTC; do not reopen unless asked. Still open: in-pod key self-stop proof (≈$0.01 pod), global volume wasteful_fuchsia_fish deletion (his word).

### memory/runpod-money-control.md

---
name: runpod-money-control
description: How pods must be run in explainer-engine after D-56 (PR #6): the one pod manager, the ceilings file, hooks, where the $8 went (2026-10-15..19) and the volumes/endpoints coverage (PR #19)
metadata:
  type: project
  modified: 2026-10-22T09:35:20.539Z
---

Since 2026-10-19 (PR #6 into systemic/next-video, D-56) pods run only through `python -m explainer_engine.cloud.runpod`
(check / create --ledger / wait-ready / guard / stop / sweep / cost / delete --yes). Ceilings: `config/spend_caps.json`
(per pod $1, per 24 h billing $1.5, per episode $3, 2 h, $0.95/h, $0.25 balance left). Session hooks refuse TMR `rp.py
create/start` and block ending a turn while a stray pod or stopped disk bills.

**The $8 → $0.97 question (answered 2026-10-22, thread "RunPod-ის დაკარგული თანხა", from GET /billing/pods):** nothing
drained after D-56 — $0.00 billed since 2026-10-19, balance unchanged. The drop was 2026-10-15..19: $2.31 (10-15 TMR
pods) + $5.34 (10-16 pods: tmr-lab $1.83, TMR preflight etkpzxh16v1ksm $1.24, stone-age pictures $0.20, rest small) +
$1.05 (10-17..19, the preflight pod's stopped 60 GB disk $0.40/day, deleted 10-19). The user told it is safe to top up.

**PR #19 (2026-10-22, claude/project-thread-engscs → systemic/next-video):** `check` (alias `doctor`) also flags
network volumes ($0.07/GB/month even unused; `keep_network_volumes` in spend_caps.json) and serverless endpoints with
workersMin>0; an unreadable volumes/endpoints list is itself a PROBLEM; `delete-volume <id> --yes` verified delete.
Guardian thread (stage B) was told to cover the same three categories in the session-independent watchdog.
Merge order agreed with that thread 2026-10-22: PR #18 (Guardian, covers all of #19 on the v2 module) first; #19 then
closes as superseded (the money-leak thread closes it after re-verifying coverage). The Actions watchdog in #18 needs
the RUNPOD_API_KEY repository secret — the creator's one manual step.

**Why:** a stopped TMR preflight pod's 60 GB volume billed $0.40/day for 3 days (balance fell to $0.97); prose rules never
ran. The creator deleted it 2026-10-19 and asked for rules enforced in code; on 2026-10-22 he asked where the $8 went.

**How to apply:** a pod ends STOPPED (disk still bills $0.20/GB/month); delete only on the creator's word; run `cost`
after a job to settle the ledger from RunPod billing. Billing rows are hour buckets and the newest hour lags. Raise a
ceiling only when the creator says so. Related: [[master-prompt-2026-10-22]].
- 2026-10-24 LT-17 (PR #22): the REST pod record (runtime null, machine {}, no IP/ports) is NOT a liveness signal for
  script pods. Every pod script uploads its log in the background (<= 300 s) before its first heavy step
  (`runpod.lint_pod_script`; `preflight_create(script=...)` refuses otherwise); pass `heartbeat="datasets/<o>/<r>:<file>"`
  to new_session; the guard takes a fresh HF upload as the answer (lifts the boot deadline) and only alerts on silence.
  Never stop a "stuck" pod before reading its last uploaded log. Cost of learning: ≈$1.6 on 10-24.

### memory/runpod-verified-facts.md

---
name: runpod-verified-facts
description: RunPod billing/API facts verified against live official docs on 2026-10-22 (validation thread), incl. gaps G1-G9 sent to the architecture thread
metadata:
  type: reference
  modified: 2026-10-22T09:24:41.593Z
---

Verified on docs.runpod.io 2026-10-22 (full report: /mnt/project-files/explainer-engine/architecture_2026-10-22/RUNPOD_VALIDATION_2026-10-22.md):

- Pods bill per second, compute + storage; no ingress/egress fees. Stopped pod: volume disk $0.20/GB/mo (2× running),
  container disk NOT billed (erased on stop). Network volume $0.07/GB/mo (<1TB), bills hourly, Secure Cloud only,
  survives pod deletion. Whether PROVISIONING/image-pull bills is undocumented (err high).
- At $0 balance: pods WITH a network volume are stopped; pods WITHOUT one are TERMINATED, data unrecoverable; network
  volumes "may eventually be terminated" too. Deploy needs ≥1 h of credits. Low-balance alert = email only (threshold set
  in console); NO webhooks anywhere (zero in the v2 OpenAPI). Default account spend limit $80/h.
- REST v1 retires 2026-11-15; v2 (api.runpod.io/v2) is GA since Aug 2026. **GraphQL retires "early 2027" and v2 has NO
  balance endpoint** — clientBalance/currentSpendPerHr only via GraphQL `myself` until then. `GET /v2/billing` itemizes
  pod gpu/cpu/disk, serverless, storage, endpoint, cluster amounts; `/v2/billing/pods` gives per-pod hourly buckets.
  v2 `Pod.cost` is 0.0 when EXITED (hides stopped-disk cost). Rate limits: per-user minute/hour/day windows, no fixed
  published numbers; read RateLimit-Policy / Retry-After headers. API keys have per-op scopes (pods:read, billing:read →
  read-only watchdog key is feasible). Create: 400 = placement failed (try next card), 402 = insufficient balance (stop),
  no idempotency key (never blindly re-POST). Zero-GPU restarts happen; "Pod migration" beta is the remedy.
- Gaps G1-G9 of the validation (2026-10-22, sent to the architecture thread for stage B): check()/caps see only pods
  (not network volumes/serverless); GraphQL balance retirement unplanned; $0-balance termination risk; hooks.BYPASS
  misses runpodctl and PATCH /pods; hooks silently pass without RUNPOD_API_KEY; Retry-After ignored; 402 mishandled;
  zero-GPU scenario untested; boot_cmd self-stop assumes an injected $RUNPOD_API_KEY (unverified).

**Why:** rules enforced in code must match RunPod's real billing; two balance drops came from unseen billers.
**How to apply:** before changing cloud/runpod.py or the watchdog, read the validation report; re-verify prices/API
before 2026-11-15 and again before early 2027 (GraphQL balance). Related: [[runpod-money-control]], [[master-prompt-2026-10-22]].

### memory/scene-continuity-d69.md

---
name: scene-continuity-d69
description: D-69 / CS-01..CS-12 scene continuity of painted pictures (PR #17, 2026-10-22) — staging block, master frames, review gate, bounded repaints; Gemini reference slots per model
metadata:
  type: project
  modified: 2026-10-22T03:32:16.029Z
---

PR #17 (explainer-engine, branch claude/project-thread-unf8ud -> systemic/next-video, draft, awaiting the creator's word)
fixes the titans bug (bench of ten painted as five, next shot other men in another room). Cause: every Gemini picture got
only style refs; no scene state.

- New `production/staging.py`; segment `staging` (location, layout, fixed, roster, positions, master, continues) and picture
  `framing/visible/partial/change/cut_away`; `look.continuity: auto` stages segments with scene.place.
- Flow: `paint plan --masters` -> approve -> run -> `staging request` (Claude's free review -> continuity_review.json) ->
  `staging apply --run` -> `paint plan --run` (shots + corrections) -> approve -> run. Max 2 repaints per picture (CS-12).
- Gemini reference slots (ai.google.dev image-generation page, read 2026-10-22): Nano Banana 2.1 / 3.1 Flash Image 4 faces +
  10 objects; 3 Pro Image 5 faces, 6 objects, 3 style; Flash-Lite no character slots. A 10-person master can hold only 4 faces.
- IDs taken: D-69, CS-01..CS-12 (new docs_lint family). Next free D after open PRs: D-70.
- Overlap: PR #14's `hero_refs` touches the same line in compile.jobs; merge as `STAGING.refs_for(doc, pid, hero_refs(...), staged)`.

**Why:** the creator wants coherent scenes instead of a slideshow. **How to apply:** new episodes write `staging` per scene
(edit-planner agent, shot-visuals skill). Related: [[explainer-engine-branch-state]], [[storytelling-system-v3]].

### memory/scene-sequence-model-2026-10-23.md

---
name: scene-sequence-model-2026-10-23
description: ვანო 2026-10-23 07:10 goal: build a scene as a photo sequence (1 per ~1.5 s, same frame, only motion changes) for the video thread; chosen model Qwen-Image-Edit-2511 + style LoRA + own "next pose" pair LoRA
metadata:
  type: project
  modified: 2026-10-23T07:15:53.176Z
---

Goal (ვანო 2026-10-23 07:10, LoRA thread): photos generate a whole scene, about one per 1.5 s, logically in the same
frame (hero changes pose); the photo/video thread then animates between them without thinking about context. He offered
to send an animated film to cut into frame pairs: to teach frame-to-frame logic, not style. He also wants a BIGGER model
than klein 4B, with his uploaded photos as the main reference and the cave image as "the real target".

Research result (07:15):
- Qwen-Image 2.1 (Sep 2026) is under the Qwen Research License (research only): do not use.
- Chosen: Qwen-Image-Edit-2511 (Apache, 20B; ai-toolkit trains it, ~28 GB at 1024 px, so a 48 GB pod).
- Two LoRAs: style, plus a "next pose" LoRA trained on pairs of the same shot 1.5 s apart (1,000–1,500 pairs from
  30–60 min of film, cutting across scene changes).
- Prior art: the Next-Scene LoRA (1,144 Sintel/Tears of Steel pairs, rank 64, 2,500 steps) changes the CAMERA. We need a
  fixed camera, so we train our own.
- Count: 2 min ≈ 80 photos, 10 min ≈ 400. Training ≈ $2–3. The 24 h RunPod cap (spend_caps per_24h_usd) must be raised
  first.

kf_v2 delivered: HF night_run_2026-10-22/kf_v2 (16 shots × first/last, last = BFL edit of first). fal account locked
(TOP_UP) 2026-10-23. Related: [[lora-question-2026-10-22]], [[night-run-2026-10-22]].
Critique thread (07:47, creator seems to accept): keyframes on main poses every 2.5–4 s (not 1.5 s), video model owns motion;
each photo from ONE master frame + hero sheet (not chained edits) to avoid drift; try "next pose" without training first
(≈$0.5), train only if camera/background floats. Creator will upload 10–20 target-level photos + one 2D film.
08:16 Qwen style LoRA training: pod x003lwf7z1b2xe ($0.82/h, cap $2.4/3 h), base Qwen/Qwen-Image-2512 (ai-toolkit edit arch
needs control images), dataset v4 (170 imgs, HF lora_plan_2026-10-22/dataset_style_v4; his 2026-10-23 uploads in
references_v3), output HF lora_plan_2026-10-22/train_qwen_v1/output, ledger train_qwen_v1_run.json, launcher scratchpad
trainq/. Caps raised on ვანო's 07:54 word ("check balance, if enough use it"): spend_caps per_24h 8, per_pod 3, 3 h (local
worktree only, not committed). RunPod 48 GB stock is thin: no CUDA filter, PRO 5000 Blackwell / A40 secure work.
09:20: first pod x003lwf7z1b2xe was stopped by the guard at 08:24 ("never answered by boot deadline", BOOT_MINUTES=10; the
aitoolkit image boots slower) ≈$0.14, deleted. Relaunched with new_session(boot_minutes=25) on SECURE A40 $0.59/h: pod
uefpamab89deb2, cap $2.2. Lesson: pass boot_minutes=25 for the aitoolkit image; check the guard log in
ee_sv/tools/runpod/sessions/<pod>.guard.log, not only HF.
11:20 v1 judged by ვანო "too rounded, drifted from the cave photo" (cause: >50 % BFL/Seedream generated images). v1 stopped
at step 750 (ckpts 250/500/750 on HF), pod deleted, ≈$1.05. v2 = dataset_style_v5 (his 24 photos ×5–8 = 75 %, hi-res cave
target references_v3/cave_target_hires.jpg ×8, 35 nearest generated; style tags appended to every caption), 1250 steps,
pod 2judx39rm1hdbu A40 $0.59, cap $2.0, launcher scratchpad trainq2/. Balance $5.87 before v2.
12:55 v2 stopped at 572 (≈$0.9; ckpts 250/500 on HF): appending one long style string to EVERY caption bound the style to that
string, not the trigger; without it samples stay semi-real. LESSON: keep captions "wldnk style, <content>" only.
BFL flux-3-image with 4 of his photos as refs + "lanky angular, long noses, bulging eyes, chalky texture, colourful" prompt
= closest to his style so far (36 era scenes, scratchpad ds6/out, ≈$4.4 BFL today; Klein copies refs). fal balance −$0.25.
Next: CLIP ViT-L similarity score (scratchpad score/) to curate dataset v6 and to score checkpoints; then v3.

14:25 (ვანო 14:01 "full RunPod balance, comment every photo, best practices"): per-image review doc https://claude.ai/artifact/7kNGHaNFcBmrYtk6hWTVow;
dataset_style_v7 (project files + HF) = his 22 (+1 detail crop each, repeats 3) / aux_k 34 (x2) / aux_l 9 (x1), detailed content
captions, portal + lettering captioned explicitly; dropped his #3 dup, #23 collage, bfl moonlanding (clone faces), vikings_f3 (grey),
8 old-gen (dups, eyes on objects, rounded face). Verdicts+captions: dataset_style_v7/review_verdicts.py. Plan: stop v3 at 500,
train v4 (scratchpad trainq4, 1500 steps, cap 2.2).
14:35: v3 stopped at 500 (control thread judge: v3@250 best, 500 regressed to semi-photo close-ups); pod deleted. v7 revised per
LoRA-control thread (cmsg_…4ADfcyLPxkFTi1c2egJPkh): his16-19 only 504x278 -> out, all crops out; his 18 x5, aux_k x2, aux_l x1.
v4 FIRST pod ut8x3c1hv9syvh ran trainq3 files by mistake (launch.py paths), killed at 223, ~$0.38 lost. v4 real pod nitzpiieik9h03 (15:13, 1250 steps, cap $1.3; 24h line $6.66/$8). LESSON: after copying a run folder, grep for the old folder name.
needs ვანო's explicit word). Send each 250-step sample set to the control thread for CONTINUE/STOP.
14:57 FOOTAGE PLAN (ვანო 14:51 in LoRA-control thread; file lora_plan_2026-10-22/FOOTAGE_PLAN_2026-10-23_ka.md): this thread owns
F5 caption pod, zero-shot 2511 test (evalq/eval.py pose part, 10 benchmark shots), next-pose LoRA on Qwen-Image-Edit-2511
(control_path pairs from HF footage_2026-10-23/pairs/, rank 16, 2500 steps, no trigger, stability not style; gates LT-41..45 by
control thread). Nothing paid until ვანო tops up + says go.
v4@250 CLIP 0.595 (v3@250 0.593); eye: v4 clearly more Wild Ink (bulging eyes, bold line); sheet train_qwen_v1_eval/v4_250_vs_v3_250.jpg
17:21 v4 DONE: stopped at 809 at cap, pod deleted. ckpts HF train_qwen_v4/output 250/500/750. CLIP 0.595/0.584/0.576; control judge
progress 0.458/0.536/0.540 (plateau). AGREED BEST = v4@500 (750 alt: more angular faces, but nurse->male doctor slip). Sheet:
train_qwen_v1_eval/v4_steps_0_250_500_750.jpg. 24h RunPod $7.95/$8, balance $2.42; card asks ვანო to raise 24h cap to $10 for eras
sheet (500+750, ≈$0.4) + zero-shot 2511 test (≈$0.5); else run both when the window frees.
01:40 Tbilisi (21:40 UTC) ვანო: v4 still misses his painterly backgrounds/texture. v5 launched: pod ldpu5mpofjyjbt L40S $1.09/h,
rank 64, 1024px, 2000 steps, his x6, aux_k x2 (no aux_l), cap $2.4 (per-episode $3 ledger 80%), scratchpad trainq5, HF
train_qwen_v5/. Overnight loop authorised (ვანო 21:42 "loop: check, try new"): style total <= $5; if v5 misses -> BFL images
with his refs -> v6. Leave one 🔔 summary + sheet vs his photos in the morning; all pods off.
2026-10-24 night result: v5 done (2000 steps, $3.03). Best = @1750 (CLIP 0.605; @2000 overfits: copies his cave, merges mammoths into people; control thread agreed). FROZEN: HF lora_plan_2026-10-22/wldnk_style_v1.0/ (wldnk_style_v1.0.safetensors sha256 b384ad49..., fallback @1250 ec8cdced..., json with params). INFERENCE RULE: load Qwen-Image-2512 in bf16 on an 80 GB card (A100 community $1.39/h); 8-bit bnb + this LoRA = noise in 15/20. 20-era sheet 20/20 clean: train_qwen_v1_eval/eras_v5_1750_bf16.jpg. Eval failures cost $0.81 (stray `del pipe`, pod idled to cap: watch pod.log for EXIT and stop the pod yourself) + $0.46 (8-bit). Style night total ≈$4.7 of $8.

### memory/scene-sequence-model-2026-10-24-approved.md

---
name: scene-sequence-model-2026-10-24-approved
description: ვანო 2026-10-24 06:31 approved wldnk_style_v1.0 (Qwen-Image-2512 style LoRA v5@1750) as "ideal"; it is the universe's frozen photo style
metadata:
  type: project
---
ვანო saw the 20-era sheet (HF train_qwen_v5_eval/eras_1750_bf16/, project files lora_plan_2026-10-22/train_qwen_v1_eval/eras_v5_1750_bf16.jpg)
and wrote "იდეალურია!" (2026-10-24 06:31 UTC). wldnk_style_v1.0 (HF lora_plan_2026-10-22/wldnk_style_v1.0/, sha256 b384ad49...) is the
approved universe style for every keyframe. Use: trigger "wldnk style, <content>", bf16 on an 80 GB card (8-bit = noise), 1280x720,
24 steps, true_cfg 4. Known limits told to him: same hero across shots needs a hero sheet + Qwen-Edit-2511 (scene thread), lettering is
weak (add text later), unusual content may drift (judge every image). Do not retrain the style without his word.
Related: [[scene-sequence-model-2026-10-23]], [[no-permanent-heroes]].

### memory/shot-reuse-rule.md

---
name: shot-reuse-rule
description: ვანო 2026-10-25 02:13 Tbilisi: no shot longer than 5 s, but when the script returns to an existing angle, reuse that keyframe (zoom/crop/slight angle) instead of generating a new one
metadata:
  type: feedback
---
ვანო's rule for the film:
- No shot lasts longer than 5 s.
- That does not mean 12 new pictures per minute.
- When the script comes back to a view that already exists, for example a dialogue cutting back and forth every 2-3 s with the same angles, the system reuses the old keyframe. It may zoom, crop or take a slightly different angle, then animates it.
- A new picture is generated only when the shot really needs one.
- This is an option, not an obligation.

**Why:** duplicate generation wastes money and breaks consistency.

**How to apply:** when writing a scenario or shot list, mark each shot as `new` or `reuse:<shot> + zoom/crop`. Count only the `new` ones for generation and cost.
Related: [[feedback-no-rushed-hypotheses]], [[style-lora-prompt-shape]].

### memory/sourced-rules-registry.md

---
name: sourced-rules-registry
description: The D-59 sourced-rules system of explainer-engine (BP-xx registry, how numbers get into validators, status grades, where the 2026-10-19 research and contradiction audit live) and what the audit PR still owes
metadata:
  type: project
  modified: 2026-10-20T04:03:57.575Z
---

- Decision D-59 (creator 2026-10-19, thread "main-ზე შეჯამება და სისტემის სრული აუდიტი"): no production rule is law by itself. Registry `explainer_engine/standards/sourced_rules.json` (80 rules after PR #11, 2026-10-20; next free id BP-87) + module `standards/sourced_rules.py` (`T(id, key)`, `check`, `render`, `write`); `docs/SOURCED_RULES.md` has a generated block between `<!-- sourced-rules:begin/end -->` (regenerate with `python -m explainer_engine.standards.sourced_rules write`); `tests/unit/test_sourced_rules.py` fails on drift; docs_lint HOMES has `BP`.
- Grades: binding = ≥2 of source types A (article/official/study), B (book), C (YouTube video) and enforced in code, may FAIL; hypothesis = 1 type, REVIEW only, keeps the project's old number; house = creator's dated call. `enforced_by` entries `path:SYMBOL` must literally appear in the file.
- Research (all URLs fetched 2026-10-19, nothing from snippets) and the 211-row contradiction audit: shared folder `/mnt/project-files/explainer-engine/SYSTEM_AUDIT_2026-10-19/` (RULE_CONTRADICTIONS.md, SOURCED_RULES.md, research/{narration,audio_mix,motion_text,retention_shorts}.md); repo copy `docs/research/SYSTEM_AUDIT_2026-10-19.md`.
- Key settled numbers: pace BP-01 170 (155-185, hypothesis); speed-up max 1.08 (BP-02 house); hook in four forms, greeting FAILs (BP-03); sentences median 12 / max 20 / FAIL 25 (BP-06); press-release lines FAIL (BP-15); zoom 1.15 everywhere (BP-20); dissolve only on period boundary (BP-31); rhythm 5 s in first 30 s, 20 s REVIEW / 40 s FAIL body, ≤10 pictures/min (BP-40); loudness -14 LUFS, TP -1 gated on the delivered file (BP-50); background in LU: music 10 / bed 15 / combined 14 under voice (BP-52); sync never early, 45 ms early / 125 ms late (BP-54); stereo AAC 384k delivery (BP-63); Shorts hook spoken within 1 s (BP-11), word bands 40-90 / 125-215 (BP-12).
- Gaps the research could not settle (stay hypotheses): channel pace measurements, pause lengths, question rate, joke density, sfx per minute, parallax amplitude, cut-type ratio, organic Shorts margins, a YouTube loudness spec.
- PR #11 (consistency fix) merged to next-video and main 2026-10-20 (main 91f1072). Reports: SYSTEM_AUDIT_2026-10-19/rescan_2026-10-20/. Still owed: palette GRAPHIC_MIN, faces SET sizes, graphics hold limits not registered; Short music fixed 0.10 with no duck; BED_LEAD 0.4 s; BP-52 LU stem measurement; BP-61 mono check.
- (history) Audit PR = draft PR #10 (https://github.com/vano1919/explainer-engine/pull/10, opened 2026-10-20 04:31 UTC, branch `claude/system-audit-sourced-rules-3i81ai` -> systemic/next-video, 541 tests pass). PR #9 (scene rewrite, branch claude/storytelling-editing-system-wc6jm1) uses D-58; D-59 is the sourced rules. Follow-ups owed: BP-52 LU stem measurement in build_audio, BP-61 mono check, sfx_manifest `kind` (PR #9). Overlapping files with #9: motion_lint.py (their MO-07 at the end of check()), validate.py (their PV-47 block), shorts.py (music loop lines), assemble.py (Sounds/loop), faces.py, edit-planner.md.

- Creator 2026-10-20 (decision card, after first tapping REVIEW and asking to be re-asked): PR #9's scene-rewrite gating numbers (VB-01/02/10/11, SC-05/08/09, cue density...) STAY FAIL, registered as `house` rules dated 2026-10-20 (numbers from D-58). Code reads their severity from the registry so a later change is JSON-only. Other defaults applied in the 2026-10-20 consistency fix (creator may overturn): a visual beat counts as an on-screen change for BP-40/41; BP-53 covers every music duck under the voice; BP-10's 1.0 s hold governs narration pauses, not the dialogue silence beat.

**Why:** every number had been restated in 3-7 places and drifted; gates described in PRODUCTION_RULES did not run on the D-43 flow.
**How to apply:** change a threshold only in the JSON with two source types; validators read `SR.T`; docs link the BP id. See [[explainer-engine-branch-state]].

### memory/storytelling-system-v3.md

---
name: storytelling-system-v3
description: The 2026-10-20 scene-based storytelling/editing system (schema production_script/3, D-58) is merged into systemic/next-video; new episodes must use /3.
metadata:
  type: project
  modified: 2026-10-20T05:05:47.130Z
---

PR #9 (merged 2026-10-20 into systemic/next-video, explainer-engine) rewrote the storytelling + editing system after
the Syndicate Wars review. Decision D-58 (renumbered from D-56, which next-video took for RunPod money control; the
parallel audit thread holds D-59).

**Why:** the old rules themselves caused the creator's complaints — VB-08 mandated a cue per beat (33/min), no scene
object (heroes answered the narrator), ER-07/RK-16+ST-09 forced press-release narration, story_lint skipped without
`drama`, loop_to tiled one-shot sounds ("one press plays many times").

**How to apply:** every new episode is written as schema `production_script/3`: dialogue segments carry a `scene`
header (place, present, pov, opposing wants, value + charges, turn, exit, surface/real subject), every spoken line has
`to` (+ `intent`), cues are opt-in and must name a story `event`; checked by `scripting/scene_lint.py` as PV-48 (renumbered at merge: next-video's PV-47 was already the variant-collage
check, OR-16) plus
VB-10/VB-11/MO-07/ST-12/ST-13/ED-14. `/1`//2` behaviour frozen (Syndicate Wars untouched). Every rule's sources (≥2
types, the creator's rule): `docs/research/STORYTELLING_EDITING_2026-10-19.md`. Skill `dialogue-scenes` has the worked
example; agents scene-writer/story-architect/beat-writer/edit-planner are retrained. Canonical homes: docs/STORY_ENGINE.md,
EDITING.md (ED-14), PRODUCTION_SCRIPT.md, D-58 in the decision log.

### memory/style-check-before-showing.md

---
name: style-check-before-showing
description: ვანო 2026-10-24 18:23 Tbilisi: test images shown as "our style" were not the style LoRA; always compare with the approved sheet first
metadata:
  type: feedback
  modified: 2026-10-24T14:26:40.519Z
---
At 14:05 UTC on 2026-10-24 I showed chain/weight-test images and claimed that one model (Qwen-Edit-2511 with style LoRA 0.2–0.8) does it all. ვანო replied: "the style is not at all what we taught the style LoRA, some photos are just bad, am I seeing other photos?"

What went wrong:
- The masters (night_run kf_v2 c07/c16) and the hero sheet were drawn by BFL before the style LoRA existed.
- The style LoRA (trained on Qwen-Image-2512) barely transfers inside Qwen-Edit-2511.

**Why:** two days of style training. He judges every image against the approved eras sheet ([[scene-sequence-model-2026-10-24-approved]]), and a wrong look loses his trust.

**How to apply:**
- Before showing any image as "our style", put it beside eras_v5_1750_bf16.jpg and check it there.
- Use masters drawn only with Qwen-Image-2512 + wldnk in bf16.
- Never use kf_v2/night-run images to judge style.
- Proposed fix (he chose "wait", 14:26 UTC): style masters plus Edit with the scene LoRA only for poses. Do not run it without his word.
- 14:50 UTC diagnosis (project files lora_plan_2026-10-24/STYLE_SCENE_DIAGNOSIS_2026-10-24_ka.md):
  - The icetribe chain shows that Edit-2511 with the scene LoRA only KEEPS a wldnk master's style; adding the style LoRA inside Edit ruins it.
  - The scene LoRA v1 was trained on Rick and Morty / Inside Job redraws at 0.55 plus BFL kf_v2 pairs, none in wldnk. If it drifts, retrain v2 on wldnk pairs (≈$2).
  - ai-toolkit Edit training requires control images, so a unified LoRA is not recommended.
  - Proposed LT-20 rule (code-enforced) waits for his word.
- 15:20 UTC 1-min film: scenario + cards in project files film_1min_2026-10-24/ (SCENARIO_AND_TEST_ka.md, film_1min.json, lint 0 FAIL).
  - Pod test code is in scratchpad ftest/ (make_cfg.py needs PYTHONPATH = PR #24 checkout; ftest.py has 6 phases, untested on a pod).
  - ვანო chose "fix the scenario first" and asked why 90 photos cost $3. I offered: all comparisons with 1 seed ≈$1.8, or film pictures only ≈$0.8.
  - Waiting for his edits. KG gate is in PR #22 (commits a673636+). The eras mammoth was asked for as "a woman painting mammoths on a rock" (corrected).
- 15:50 UTC: Test plan v2 (film_1min_2026-10-24/TEST_PLAN_v2_ka.md).
  - ვანო dropped old-vs-new.
  - T1: technical (code-computed ± sizes) vs relative proportions.
  - T2: EliGen.
  - T3: reverse path (blockout -> ControlNet: InstantX Union / DiffSynth depth, both on base Qwen-Image; 2512 compatibility unverified).
  - T4: poses (Edit+scene / Edit / ControlNet re-render / +refresh).
  - scripting/layout.py (LY-01..08) is in PR #22 (d6143ba). It caught the mammoth hidden behind the bus.
  - Waiting for his scenario edits; then card layouts, an exact price (≈$2), and his OK.
- 16:01 UTC: ვანო said "run everything" (15:50). Test v2 pod bv4dtilmiw9e4m is running at $1.39/h, cap $2.4 / 2 h.
  - Ledger: film_1min_2026-10-24/ftest_ledger.json. Code on HF: film_1min_2026-10-24/code/. Output: film_1min_2026-10-24/test/.
  - About 65 pictures, plus qa_log.jsonl and results.jsonl.
  - 24 h RunPod billing before this test was $16.61 of $26.
- 17:30 UTC: Test v2 is done. Cost $1.94, of which ≈$0.7 was idle pod time: check sooner.
  - Report: film_1min_2026-10-24/test_v2/REPORT_ka.md.
  - Prompt duplicates cause most failures: "A living mammoth" drew 2 mammoths; repeated full tags gave 2 nurses or 2 girls.
  - Numbers in prompt text get drawn as rulers and figures. Relative wording is just as accurate, so no numbers in prompts.
  - ControlNet keeps the layout but mixes identities.
  - Edit with no LoRA ≥ scene LoRA v1. The style refresh does nothing. Cuts via Edit do not reframe.
  - The gate missed the extra mammoth. KG-12 wrongly fails close-ups.
- 17:38 UTC: the sheets page is https://claude.ai/artifact/Di4qZKyfVF9rrLKBjCJJrV (thread attachments maxed at 24, so publish pages instead).
  - ვანო chose "wait" on the next step.
  - I proposed: hero sheet = 2512 + style LoRA; scene master = Edit-2511 from the sheet (untested, ≈$0.3); poses = Edit from the master without a LoRA. Park scene LoRA v1.
  - PR #24 b991562 fixed the prompt rules: no "a" + cast noun in relations, no size numbers, blocking[].partial. Add a partial mammoth to S02-02/S02-03 before any re-run.
  - Gate fixes (KG-01 per figure, KG-17, KG-12 not on close shots) sit uncommitted in the local repo until he gives the word.
- 18:50 UTC 10-24: Asset test done (pod o2beilxz11sd0t stopped, $0.85, ledger film_1min_2026-10-24/atest_ledger.json, page https://claude.ai/artifact/Di4qZKyfVF9rrLKBjCJJrV).
  - Style diagnosis: a long prompt does NOT hurt the style, and the negative list makes little difference. Short prompts drift in content (castle, other bus, bluer look). My earlier hypothesis was wrong.
  - Edit with no LoRA, composing from a panorama + cast sheet + bus sheet, gave a consistent world and clothes in 5 of 6 masters.
  - Faults: 3 buses (S02-01), a mammoth in a car trunk (S02-02), the old man lost his glasses (S00-02), S01-01 too white.
  - My gate question C-02 ("same clothes?") gave false FAILs; do not trust it.
  - Proposed next: two-stage masters for hard shots (place + bus first, then the cast). Waiting for ვანო.
  - Code is at HF film_1min_2026-10-24/assets_code/ (hand-written prompts, not composer).
- 19:20 UTC 10-24: negative-prompt check done (pod hjcnvhr5q4dtzc stopped, $0.31, ledger ntest_ledger.json).
  - The approved neg is "text, lettering, letters, words, watermark, signature, photo, 3d render". It makes almost no visible difference.
  - The eras ice-age control reproduced the approved quality, so the LoRA and its loading are fine.
  - The bus scene looks plainer because its world is plain (white snow, flat grey light, nothing coloured). Describe worlds richly and in colour, as the eras prompts did.
  - Proposed next, waiting for ვანო: a colourful panorama + sheets, then masters in two stages for hard shots (~$0.6).

### memory/style-lora-prompt-shape.md

---
name: style-lora-prompt-shape
description: Why the wldnk style faded in film pictures (2026-10-24): prompt shape, not the LoRA; LT-65 caption shape + tail, ≤90 words, tags once
metadata:
  type: project
  modified: 2026-10-24T19:39:33.444Z
---
On 2026-10-24 ვანო said the style LoRA "lost the style". The cause, shown in one run with the same LoRA file and seed (neg_test sheets):
- The approved eras prompt (31 words, caricature words, a fire) drew the approved look.
- The film bus prompt (337 words) drew a flat, grey, generic cartoon. It had no style tail, no caricature words, "flat grey daylight", and each full tag repeated 9 times. The repeated tags also produced a twin girl in 10 of 10 pictures.

All 164 v5 training captions end with the same tail:
"lanky angular cartoon characters with long noses, thin limbs and bulging round eyes with tiny pupils, bold uneven black ink outlines, chalky textured painterly background, muted earthy colours with vivid glowing accents".

Fixed in PR #22 commit 5049711:
- LT-65, `qa/style_prompt.py` (`with_tail`, `check`);
- LY-09: each full tag said once;
- KG-18..22: twins, marks, object counts, absent things, the 72B judge with one question per call, and Claude's filled table before showing.

The composer was fixed in PR #24 commit 2c1caa0: tail, at most 90 words, each tag once, layout moved to the gate card. The next picture run uses it.

**Why:** ვანო: "the answer is where it was good before; find what we did right."
**How to apply:**
- Every style-LoRA prompt must pass `style_prompt.check`.
- Layout goes into boxes, a blockout or Edit, never into long text.
- Proof test 00:20 Tbilisi 10-25 ($0.40, HF film_1min_2026-10-24/style_test/): with the tail the style RETURNED and twins were gone, BUT the tail clause "lanky ... characters" adds extra long-nosed people (6/8 shots), the short tags ("the nurse") lose the wardrobe, and "city bus" in the place text draws a city. Next test offered (≈$0.4): the tail without the characters clause, full tags once, "only these N people", 90-word limit vs no limit. Awaits his word.

Related: [[use-newest-code-and-approved-rules]], [[style-check-before-showing]].
- 00:40 Tbilisi 10-25: ვანო asked to step back and research how others solve consistency instead of more prompt fixes. Research doc https://claude.ai/artifact/V3rgCEUw4235ABXVrmUbE5 found that others compose a frame from parts, not from one prompt. Recommended a ≈$0.5 test on S01-02: (1) the style LoRA draws the background and each hero separately, code places them in the layout.py boxes, and a light repaint harmonises the light; (2) the same scene with EliGen. Awaits his word; the earlier "next test" offer is superseded.
- 01:50 Tbilisi 10-25, composition test ($0.51, HF film_1min_2026-10-24/comp_test/, code in scratchpad ctest/): the background and 4 heroes were drawn separately (2512 + style), BiRefNet cut the heroes out, and code placed them in the layout boxes, then img2img with style at 0.30.
  - Result: exactly 4 people and the sheet wardrobe in 6/6 shots. 0.30 keeps identity; 0.45 breaks it.
  - Still wrong: the caricature is too strong (the tail's "long noses"); the bus came from the background, so the girl is off it (the bus must be its own asset); the contact shadows look pasted.
  - EliGen failed again: the pip command lacked --break-system-packages.
  - Next test offered (≈$0.5), awaits his word.
- 02:10 Tbilisi 10-25, mood analysis (free; https://claude.ai/artifact/R1CXtBBe6K8ZSHS6thoNSF): all 20 eras prompts follow one formula, 20-29 words:
  - place and era;
  - a comic action at its PEAK, plus another figure's reaction;
  - body caricature words (thin, lanky);
  - a light source;
  - 1-2 world props;
  - NO tail, camera, positions or sizes.
  Ours: everyone just standing (the keyframe = START-pose rule), tags of clothes only, grey light. The tail (LT-65) was NOT in eras: it returns the style but over-caricatures (long noses), so LT-65 needs fixing. An eras-formula test of the bus scene (≈$0.25) awaits his word.
- 02:40 Tbilisi 10-25, FULL free analysis https://claude.ai/artifact/BCfwRAUtF34g9xcS1bjk6D. The v5 training samples (step 1750, 19-33 words, no tail) drew OUR film heroes (nurse, bearded worker, pink-haired girl, bald old man, bus on the tundra) in perfect style. Dataset captions: median 19 words, "glow" in 62/164. Style loss = our prompts (long, layout and camera text, standing START poses, grey light). The tail over-caricatures. Proposed: ≤35-word story prompts (place, peak action, reaction, emotion, light source, 1-2 props; no tail, camera or sizes) + composition for consistency. Revise LT-65 and the START-pose rule only on his OK. One ≈$0.25 test of cross-shot identity awaits his word.
- 03:20 Tbilisi 10-25 (ვანო asked): LT-66 ABSOLUTES A1..A10 + NEGATIVE + INFERENCE frozen in qa/style_prompt.py (other art-style words FAIL); EPISODE LOOK compose/episode_look.py (AC-16..19): colour+light phrase ≤10 words appended via apply(), drift REVIEW, grade ≤0.35. PR #22 1b849e2. Prompt thread told to call apply().

### memory/three-ai-review-2026-10-25.md

---
name: three-ai-review-2026-10-25
description: Fact-check (10-25, free) of 3 AIs' "$50 setup / $20 per 15-min episode" animation systems vs our measured costs; page + verdicts
metadata:
  type: project
  modified: 2026-10-25T18:11:43.670Z
---
ვანო asked 3 AIs to design an AI cartoon system from zero ($50 setup, $20 per 15-min episode). Review page:
https://claude.ai/artifact/4oP3AWRwrNJEj22WYXA2vd (thread "შევაფასოთ 3 AI-ის სისტემის რჩევა").

Measured basis: film A $2.99 for 52.6 s (≈$51 per 15 min at that rate, failures included). Pure LTX on pod ≈$0.016/s
(~200 s/clip at ~$1.4/h); 214 Qwen frames ≈$2; episode ≈$14-24 only with zero failures and ≥50 % holds/reuse.
LTX-2.5 Fast API $0.09/s ≈5× pod.

Verified 10-25: Kling 3.0 720p 6 credits/s (official); Sora shut (app 04-26, API 09-24 2026); Nano Banana 2.1 $0.034 1K /
$0.050 2K / batch $0.017; ElevenLabs Starter $6/30k; v3/v2 API $0.10->$0.08 per 1K chars (tracker); Wan 2.5/2.6 API-only;
Midjourney --cref replaced by --oref (V7), V8.1 default, no public API; RunPod network volume $0.07/GB/mo; 4090 $0.34/$0.69;
Edge-TTS = unofficial endpoint, commercial use risky; Suno Pro 20 downloads/mo since 2026-09-03.

Rejected: Midjourney, Edge-TTS, SadTalker/LivePortrait, 60 fps interpolation, character LoRAs, Blender rig as core (he
rejected rig 10-22), network volume. Take: Gemini-with-references direct comparison vs v1.0 (≈$0.5), per-episode cap line in
spend_caps (his number), simpler agent setup. Open for him: character voice (LTX multishot vs fixed ElevenLabs + A2V).
Related: [[feedback-be-critical]], [[film-1min-run-2026-10-25]], [[video-model-research-2026-10-25]].
- 18:20 UTC check vs integrated branch claude/project-thread-beg7xa (all PRs #14-#25): already there = keyframe gate, KP-18/BP-100
  line length, voice options (SCRIPT_ENGINE), D-42 Gemini refs, LT-71/VT-01-02/D-76. My "≥50 % holds" was WRONG: BP-109 hold ≤10 %
  (his cartoons hold 5-10 %); savings come from KP-37 light tier + reuse. Truly new, offered (awaiting his word): card-level
  cost estimate ×1.5 retries; per_episode caps sum $51 vs his $20 target (his call); one main agent + one critic; LTX API for 1-3 retakes.
- 18:27 UTC ვანო: item 2 yes -> PR #27 (draft, claude/project-thread-tht70c -> beg7xa/PR #22): OR-20/D-79 one main agent runs
  stages from stage pages, only script-critic + lora-checkpoint-judge spawned; test_agent_roles.py. Item 3 (LTX API): NO, pods
  stay (his card pick). Item 1 (card cost estimate, $51 vs $20 caps): not answered.

### memory/titans-qa-loop-state.md

---
name: titans-qa-loop-state
description: State of the Titans from Zero episode (one-narrator D-68 full render) and what waits on the creator (2026-10-21)
metadata:
  type: project
---

- Branch claude/project-thread-hze0pq, draft PR #14. D-68 (creator 2026-10-21): one narrator (Brad l3OCvamakRoSUNIIz75n,
  eleven_v4) performs every quote; intro card + 4 recap cards (`design/cards.py`); drawn icon props across the script.
- ElevenLabs cap raised to 7,000 for this re-record (creator card 10:07); spent 6,625 (22 takes, log
  jobs/titans_from_zero/read_v3/generations.json). ER-03/RK-20 rewritten for D-68 on the creator's card (12:05).
- Read = old Brad read + takes spliced by jobs/titans_from_zero/read_v3/build.py -> pieces.json -> `production words`.
- 2026-10-21 17:20: full video rendered (14:46), all pairs 0 FAIL, full pixel check 0 FAIL. 720p copy:
  /mnt/project-files/explainer-engine/titans_from_zero/one_narrator/titans_full_v3_720p.mp4; full 1080p in
  jobs/titans_from_zero/full_v3/render/video.mp4 (container-local). Creator approved 17:42; uploaded UNLISTED 2026-10-21 18:13: https://studio.youtube.com/video/XW8BfJdw1No/edit . Creator: thumbnail + Public; Shorts not rebuilt for D-68 yet (ask before paid read).
- Thumbnail 2026-10-21: Gemini prepaid credits depleted (429); creator chose ElevenLabs (Nano Banana 2.1 1K = 509 credits,
  cap raised to 7,550 on his card; spent 7,134). Draft: examples/titans_from_zero/publish/thumbnail_draft.jpg. Next: premium
  version after his notes. `publish thumbnail --tier draft` added. Shorts thumbnails only in Studio (TN-11).
- 2026-10-21 18:55: creator dropped the 10 scripted Shorts; 5 clip Shorts cut from the long video (production/clip_shorts.py:
  video's opening + one moment + shared ElevenLabs outro, loops, 1.15x) uploaded unlisted: b9GMOBeadyk, 00zW8gXF2Sc, HOVbn13cqcI,
  ZBBZyTSucVo, K6bRRvj0KXU. Creator wants no thumbnail from us. ElevenLabs spent 7,262 (cap 7,550).
- Open REVIEWs for the creator: recap 2 close to recap 1 (R12-05); Shorts still bubble-era (R12-10, rebuild before any Short read).
- After the editorial gate: any script edit (even bubbles) makes editorial_review.json stale (EG-13): re-bind before a paid step.

**Why:** the creator wanted the whole video re-voiced and edited. **How to apply:** next notes go into the script, then
re-time and re-render; never upload without his word. See [[creator-workflow-preferences]].

### memory/tool-findings-2026-10-25.md

---
name: tool-findings-2026-10-25
description: Verified tools (HF, 2026-10-25) for consistent 2D film: LTX-2.5 Layout-To-Render IC-LoRA, Qwen-Image-2512 Fun-ControlNet-Union, qwen-360-diffusion; GPT's errors
metadata:
  type: reference
  modified: 2026-10-25T08:14:46.669Z
---
Checked on HF 2026-10-25 after ვანო pasted a ChatGPT research answer (answer cut at "Stor"; he was asked for the rest).
- **Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render** (gated "auto"): a Blender/Unreal clay or blocky playblast drives the
  camera and object positions; the first frame (made by any image model, never the grey clay frame) sets the look.
  CLI: `python -m ltx_pipelines.ic_lora --video-conditioning clay.mp4 1.0 --lora ... --stage-2-ic-lora --image img.png -1 1.0`,
  two-stage distilled (960x544 8 steps, then 1920x1088 3 steps), CFG 1, euler_ancestral, frames 8k+1, sizes /64.
  Also LTX-2.3 Union-Control and Motion-Track IC-LoRAs; LTX-2 19b Pose/Depth/Canny.
- **alibaba-pai/Qwen-Image-2512-Fun-Controlnet-Union** (VideoX-Fun): Canny, HED, Depth, Pose, MLSD, Scribble, Gray + inpaint;
  control_context_scale 0.70-0.95.
- **ProGamerGov/qwen-360-diffusion**: rank-128 equirectangular LoRA, v2 for Qwen-Image-2512, 2048x1024, trigger
  "equirectangular"/"360 panorama"; trained with realism regularisation, so style retention with wldnk is untested.
  pytorch360convert cuts views.
- GPT's errors: said LTX has no structure control (wrong); invented/confused names ("Qwen-Image 2.5", "NVIDIA GS Luna",
  "Krea-2 (SDXL)", CogVideoX lip-sync).
- My proposal to ვანო (12:20 Tbilisi): Blender world from the scene map -> per-shot depth/canny -> Qwen-2512 + style LoRA +
  Fun-ControlNet -> first frame -> LTX Layout-To-Render. Test ≈$0.5 awaiting his word.
Related: [[python-world-composer-2026-10-25]], [[video-model-research-2026-10-25]].
- 12:26 Tbilisi ვანო approved the layout test, cap $1.6: pod 6vfmwgsw1y6o3n (launched 08:3x UTC), HF film_1min_2026-10-25/layout/
  (code: layout.py numpy clay/depth renderer, ctrl.py VideoX-Fun runner, worker.py job types t2i/ctrl/ltx_ic). Gemini research
  (12:28) agrees on blockout -> Fun-ControlNet -> LTX IC-LoRA; recommends hybrid 2.5D (LTX only for complex action), separate TTS
  dialogue, and Qwen-Image-2.1 (real, Sep 2026; has Fun-Controlnet-Union 2.1 and ausboss Consistency LoRA) — 2.1 would need a
  new style LoRA. Open questions to ვანო: hybrid, TTS voices, 2.1 move.
- 12:37 Tbilisi ვანო: "license doesn't worry me, if technically possible do it" -> Qwen-Image-2.1 (qwen-research license, HIS
  call) style LoRA training: ai-toolkit arch qwen_image_2 (fresh clone; one model = T2I + edit), v5 data/settings, pod ee-qi21,
  cap $2.2, ledger lora_plan_2026-10-22/train_qi21_v1_ledger.json, HF lora_plan_2026-10-22/train_qi21_v1/ (code/, log/, output/);
  samples include 2 ctrl_img edit tests. Launcher scratchpad t21/.
- 12:50 Tbilisi ვანო: 2.1 training may go to $5 or more if it progresses (ledger cap raised to 5.0). Idea: one LoRA learning
  scene logic from cartoon pairs + style from our photos — research only, NOT to run blindly; answered: separate trigger or
  redrawn pairs, but first check 2.1 zero-shot references. Try 1 pod g1mgl27933w1vd failed (local dir as name_or_path ->
  meta tensors; plain pip blocked by PEP 668), kept stopped. Try 2 pod bbewaw04kw1o6l (name_or_path "Qwen/Qwen-Image-2.1").
- Pano v1 (layout pod): qwen-360 LoRA at 1.0 gives real equirect but washes out style; "city bus" draws a city.
- 13:10 Tbilisi results: pano v2 (no "city", ink style words) at qwen-360 weight 0.8 seed 11 wraps seamlessly (edge diff 8.3 vs
  7.3 neighbour) = real 360 in our style; 0.6 and s23 do not wrap. 2512 Fun-ControlNet depth 0.8 + style LoRA lost the ink style
  (flat vector look); S01-03 copied mannequin stick arms (fail), S02-01 logic right (backs, mammoth on crest). Worker self-stop
  does nothing (no RUNPOD_API_KEY on pod); guards die with the container: re-`adopt` with REMAINING caps after a restart.
  Continuity research doc (his 13:01 idea, 8 s clips with 1.5 s handles): https://claude.ai/artifact/VYxWQ4vrJN1bxZFZTqrGRT —
  master layout timeline per scene + 1 s handles; hybrid ~$6-8 per 15 min. 13:36 he asked to wait for the 2.1 training first.
- 14:30 Tbilisi: Qwen-Image-2.1 style LoRA wldnk_qi21_v1 (pod bbewaw04kw1o6l, ~1.55 h ≈ $0.9, stopped at step ~810, kept):
  250/500 = our ink style (500 best, matches eras sheet), 750 slides back to painterly/oil (Rome, campfire) -> pick 500,
  alt 250. Edit samples (ctrl_img) keep identity/place. "city bus" draws a city: write "bus". HF
  lora_plan_2026-10-22/train_qi21_v1/output/wldnk_qi21_v1_000000500.safetensors. LTX ic_lora rejects `--image x -1`; use 0.
- 10-26 07:53Z: BFL works with env var BFL_API_kay (sic; 247.2 credits ≈ $2.47); BFL_API_KEY answers 403 Not authenticated. fal balance -$0.25 (rest.alpha.fal.ai/billing/user_balance).

### memory/use-newest-code-and-approved-rules.md

---
name: use-newest-code-and-approved-rules
description: ვანო 2026-10-24 22:19 Tbilisi: runs must use the newest code and rules of ALL threads (PR heads, not stale copies); approved rules apply every next iteration (LT-63, LT-64)
metadata:
  type: feedback
  modified: 2026-10-24T18:20:38.747Z
---
ვანო found that the pod-error fixes (LT-17, LT-19) live only in PR #22 and asked whether the other threads' newest prompt rules were in use. They were not all in use:
- Test v2 composed its prompts at PR #24 08f2bf6, before b991562.
- The asset test wrote its prompts by hand.
He plans to merge the PRs so that every thread gets the fixes.

**Why:** he approves a rule once and expects every later iteration to apply it. A stale copy repeats errors that were already fixed and wastes money.

**How to apply:**
- Before any paid run, `git fetch` and use the newest heads of the owning branches: PR #22 for pods, the gate and layout; PR #24 for the composer; main once they are merged.
- Build prompts with `film_shots compose` on the current head.
- Record each repository's commit in the run record.
- The LT-64 list in docs/LORA_TRAINING.md holds the approved rules:
  - style LoRA only on 2512, never in Edit;
  - generate, check, and redraw only on a fail, at most 3 times;
  - compare with the eras sheet before showing;
  - no numbers in prompts;
  - name each figure once;
  - prompts near the caption length;
  - pods via cloud.runpod;
  - check the pod at least every 15 min.
- Merge order when he asks: PR #22 → systemic/next-video, then PR #24 (stacked on #22), then next-video → main. Main still lacks #13–#24.

Related: [[style-check-before-showing]], [[explainer-engine-branch-state]].

### memory/vault-2026-10-24.md

---
name: vault-2026-10-24
description: Backup scheme (D-73, PR #23): HF tmr-artifacts is primary; tag vault-<date>, code bundles in HF vault/code, `vault` tool, pods prove uploads before stop; second copy on ვანო's disk pending
metadata:
  type: project
  modified: 2026-10-24T09:39:39.610Z
---
Thread "დაცვა: ნაშრომი არ დაიკარგოს" (cmsg_…LuBBngNCHGXGVGjghsVVnZ, ვანო 2026-10-24 09:28 UTC).
Inventory 09:30 UTC: HF dataset vano1919/tmr-artifacts private, owned by vano1919, 9 290 files 47.8 GB; wldnk_style_v1.0
sha256 b384ad49… = train_qwen_v5 step 1750. RunPod: 12 stopped pods all 0 GB disk (no data), no network volumes.
Done: HF tag vault-2026-10-24; HF vault/code/*.bundle (both repos, all branches); HF vault/VAULT_MANIFEST_full_2026-10-24.json.
PR #23 (closed 2026-10-25, folded into PR #22 as ed02fc3 with VT-01/02 wired into the pod-script lint): explainer_engine/vault.py (snapshot/verify/pull/check-uploaded,
lint_pod_script VT-01/02), config/vault.json (critical globs; put video LoRA under video_lora_<date>/), docs/VAULT.md VT-01..05, D-73.
Asked agent thread to upload every scene LoRA checkpoint + run check-uploaded before pod stop.
Open: second copy on ვანო's PC (`vault pull --dest D:\wldnk_vault`, ~8.1 GB) is his step. 636 project-files-only files (1 GB, incl. his uploads) now on HF project_files/ (tag vault-2026-10-24b).
**How to apply:** after each approved LoRA/dataset: snapshot + new tag (VT-04); never delete manifest files (VT-03).
Related: [[runpod-money-control]], [[lora-training-control-2026-10-23]].

### memory/video-model-research-2026-10-23.md

---
name: video-model-research-2026-10-23
description: Video-model research verdict (2026-10-23 07:05 task): LTX-2.5 is the main candidate for photos->video + continuation + motion LoRA; Wan 2.2 fallback; next = side-by-side test ≈$1.5 on kf_v2 (needs ვანო's word)
metadata:
  type: project
---

ვანო's requirements (07:05): model that (1) trains best on HIS hours of cartoon footage (motion LoRA), (2) turns existing photos
(from the photo-LoRA thread; 2–5 per 5-s clip) fully into video, (3) continues video-to-video with context widened by photos.
Big model, no photo-generation concerns in this thread.

Doc: "ვიდეო-მოდელის კვლევა" https://claude.ai/artifact/GSf4mx5QH74kDXssMrgG1R (Claude Doc id 7d0e21f1-9722-401a-a963-d0dcef52b15c).
Verdict: **LTX-2.5** (22B) only open model with multi-image conditioning at any frame (replace/guide), prefix/suffix extension,
official ltx-trainer (LoRA on video clips; 80 GB full, INT8 on 48 GB); licence OK <$10M, outputs must be disclosed as AI.
**Wan 2.2** = fallback (first+last frame only, no continuation in 2.2, biggest ecosystem, Apache). Rejected: MiniMax H3 (licence
excludes US/EU/UK/KR), MAGI-2 (8 Hopper GPUs, no fine-tune), Hunyuan 1.5 (8.3B, first frame only), Kandinsky 6 (no LoRA code).
Plan: (1) side-by-side Wan 20-step 720p vs LTX-2.5 (2 and 5 keyframes) on 4 kf_v2 scenes, ≈$1.5 A100, AWAITS his word;
(2) his footage -> split_scenes/caption, motion-only captions, kf_v2 stills mixed in; (3) motion LoRA v1 $4–10, 3–6 h;
(4) show 6 scenes with/without LoRA + 60-s continuation. Episode render estimate ≈$4–5 on LTX-2.5.
Night Wan test caveat: used 4-step distill at 480p, so "weak model" is not proven.
Related: [[night-run-2026-10-22]], [[night-run-2026-10-23-split]], [[no-permanent-heroes]].

BAKE-OFF PREPARED 2026-10-23 08:10 (ვანო's "კი" 07:47): code in project files `hybrid_model_2026-10-22/bakeoff/pod/`
(pod_bakeoff.sh, ltx.py, wan.py, shots_bakeoff.json, launch_bakeoff.py) and HF `bakeoff_2026-10-23/code/`; outputs will land in HF
`bakeoff_2026-10-23/out/{ltx,wan}`. Shots c04, c15, c10 (2 stills each) + LTX chain c15→c16 (4 stills, 241 frames, --chunked).
Wan: full 20 steps, CFG 3.5, 720p, no LoRA. LTX: ti2vid_two_stages, 1280x704, 121 frames, fp8-cast, dev transformer + distilled LoRA.
Blockers at 08:10: (1) 24 h RunPod cap $5 nearly used ($3.48): card asked to raise to $7 today; (2) HF Lightricks/LTX-2.5 is gated
and vano1919 has not clicked Agree (403) -> fallback mirror comfyicu/LTX-2.5 (same files) is coded in. Ledger: bakeoff_ledger.json cap 2.0.

DECISION 2026-10-23 09:10 (ვანო 09:03: "decide from the internet, money for training/pods is no object, +$2-3/video is fine"):
**LTX-2.5 chosen, bake-off cancelled ($0 spent; cap card withdrawn).** Internet has no independent 2D-cartoon test of either model.
LTX cons found: warble/flicker/morphing on long clips + complex motion (Lightricks' own troubleshooting blog), teeth anomalies
(HF discussion 50), few cartoon LoRAs, 80 GB training. Wan cons: FLF only, no continuation, 5 s/16 fps, realism bias + quality loss on
advanced motion (Civitai anime LoRA author), 4-step distill slows motion (explains the weak night clips). NEXT: when his footage
arrives -> split/caption -> training pod does baseline 10-shot benchmark (plan_review_2026-10-23/benchmark_10shot.json) WITHOUT LoRA
first, then LTX-2.5 motion LoRA, then same 10 shots with LoRA. bakeoff/pod/ltx.py is reusable for the baseline.
PAUSED 2026-10-23 09:14 (ვანო): wait for the photo-LoRA thread's training to finish before any video work. Asked him (09:13) for:
1–3 h of 2D cartoons (3–4 shows, ~equal) as a Google Drive link + RunPod top-up ≈$10 (balance $7.11). Daily cap raise on training
day is covered by his 09:03 "money for training/pods is no object".
MOTION MANNER: 10:29 "all Disney type"; CHANGED 15:00 -> footage is Solar Opposites (TV limited animation, same manner as Wild Ink), possibly only that show (control thread advised 1-2 same-manner shows more). Clips: dialogue/gesture-heavy, fewer big physics shots.
Groove, Tarzan type: full animation, squash & stretch); no 3D (Pixar/new Disney), no limited TV animation. 3–4 films.
GATES from LoRA-control thread (2026-10-23 14:37, PR #22, docs/LORA_TRAINING.md): for the LTX-2.5 motion LoRA: G1 clips.json +
`python -m explainer_engine.training audit-video` 0 FAIL ((F-1)%8==0, sizes /32, no cuts, no character names in captions, no phrase in
45%+ captions); G2 check-config --kind video (rank 16-64, lr 5e-5..2e-4, ckpt+validation <=250 steps, fixed seed, half held out);
G3 cost projection, stop at 80%; G5 judge: render benchmark_10shot.json WITHOUT LoRA first, then each checkpoint (motion >=0.7x base,
jitter <=1.2x, keyframe fidelity within 0.02); expect best checkpoint early (community LoRA copied frames at 2000 steps).
That thread offers to run the audit/judge: message it the clips.json / HF paths.
MOTION-LORA POD READY 2026-10-23 15:10 (nothing launched): project files hybrid_model_2026-10-22/motion_lora/pod/ + HF motion_lora/code/
(pod_ltx_train.sh, make_cfg.py, motion_caption_prompt.txt, launch_ltx_train.py). Pod reads HF motion_lora/control_ltx.json
{mode calib|train, minutes, steps, captions have|make, max_usd, cap_usd}; launcher REFUSES without it. Expects HF motion_lora/dataset/
{dataset.json (caption,video), clips/} from the control thread and motion_lora/val/val_samples.json [{prompt,image}]. Config = i2v_lora.yaml
patched (rank 32, attn1/attn2 only, first_frame 0.7, audio off, 768x448x89, ckpt+val every 250, calib = 100 steps). Weights: official
repo else comfyicu mirror. Step 1 = 100-step calibration on A100 80GB (~$2.5), then control thread's G3 projection, then ვანო's go.
Pod flow detail: captions:"make" => pod captions ONLY, uploads out/dataset_captioned.json, stops; control thread runs FS-05 check, puts the
file at motion_lora/dataset/dataset.json, sets captions:"have", then the next pod start preprocesses + trains.
2026-10-24 01:57 (agent thread via coordinator): LTX-2.5 Layout-To-Render IC-LoRA test, 2 shots 1 seed eye-judged: output follows block motion
(jump/fall/crawl/walk) and keeps first-frame style; plain LTX I2V invents motion and drifts. Weak: faces of 2 right-hand heroes blur toward
end of shot B. Cartoon motion LoRA may be unnecessary for this shot type; C2 10-shot benchmark decides. Results: project files
lora_plan_2026-10-22/ic_test/results/ (collage_ic_test.jpg, A_side.mp4, B_side.mp4). Video LoRA still waits for ვანო's footage/go.
2026-10-25 18:22: draft PR #21 (explainer-engine, branch claude/project-thread-81jdev: AI-video route code aivideo/, night-run pod scripts, bake-off
files live only in project files + HF) was CLOSED WITHOUT MERGING by someone else. Do not reopen or re-open a PR for it unless ვანო asks;
pod code remains in project files hybrid_model_2026-10-22/ and HF tmr-artifacts (night_run_2026-10-22/code, bakeoff_2026-10-23/code, motion_lora/code).

### memory/video-model-research-2026-10-25.md

---
name: video-model-research-2026-10-25
description: LTX-2.5 research for ვანო (03:30 Tbilisi 10-25): video LoRA not needed now, motion norm = his cartoons, VP-01..14 proposed, voice-consistency open question
metadata:
  type: project
---
ვანო asked (03:16 Tbilisi, 10-25) for research on the video model before the video stage. He wanted LTX docs, patterns and anti-patterns, motion frequency, 5 s shots, 2K, and rules for the script and agents. At 03:17 he also asked whether a video LoRA is needed or "useless like the scene LoRA".

Doc: https://claude.ai/artifact/S71QBW3wtLPfEyb9iCteKb (doc cb4b2ce8-cae5-4ae8-b4cd-14d5b9d25fb2). Official sources were read with curl, because WebFetch overflows on ltx.io.

Findings:
- **Video LoRA: not now.** In 13 clips the style held (palette drift 0.001-0.009, edges 91 %). Every defect was fixable by prompt, first frame or free edit. Reconsider only if the 1-min film shows a repeated defect.
- **No YouTube "gold standard" exists** for motion share; only unsourced blogs. The norm is his cartoons: hold share p50 0.77, camera still 66-77 %, shot median 3.2 s. Our LTX clips hold 0-10 % (too floaty), ice age 85 % (frozen). Fix: free "on twos" plus pauses in the edit.
- **LTX-2.5 facts:**
  - I2V: the prompt describes only the change. Use 4-8 present-tense sentences, emotion through body cues, an end state, and the camera in its own clause.
  - Dialogue ≈2.5 words/s, so ≤10 words in 5 s. 121 frames = 5 s, and (F-1)%8 == 0.
  - Multishot: 2-4 shots in one generation keep identity AND voice.
  - First+last frame needs the same setup.
  - Distilled ignores the negative prompt (no CFG); dev with CFG 2-5 gives final style adherence.
  - Native 2K/4K is available; tests run at 720p with no paid upscale.
- **Voice across clips is NOT remembered (open question for him).** Options: multishot per scene, or A2V with a fixed voice (ElevenLabs). The second conflicts with his rule "ElevenLabs only for narrator".
- VP-01..14 were proposed. Coding them into the composer (PR #24) and a free "twos" test on the eras clips were next.

Related: [[video-qa-2026-10-23]], [[prompt-rules-shot-cards-2026-10-24]].

### memory/video-qa-2026-10-23.md

---
name: video-qa-2026-10-23
description: Video QA code (LT-50..59) results and the cartoon rhythm norm from ვანო's footage; IC layout lesson; max-length test prep
metadata:
  type: project
  modified: 2026-10-23T22:45:41.507Z
---

ვანო 22:32 UTC 2026-10-23: "write video checks in code (hands, faces, AI mistakes), measure everything, use the cartoons as
the norm, B's IC video has no feet, find the max length from one photo". Done: `training/video_qa.py`, CLI `video-qa`
(--layout/--regions/--ref/--sheet) and `footage-rhythm`, PR #22 commit 86db33a (+ opencv in requirements for CI).

- Global numbers (flicker, morph, lines) PASS on all 4 first-test clips; B_ic defect came from OUR bend-rig layout (legs
  smeared to shadow + dark ghost where the scientist stood -> IC drew a second caveman). LT-59 layout-fidelity catches it at
  2.4 s. Lesson: IC = only as good as its layout; layouts need a clean plate behind moving people and rigid legs.
- CARTOON NORM (120 shots, 3 shows, scratchpad rhythm.json): hold share p10 0.26 / p50 0.77 / p90 0.96 (most frames hold:
  drawn on twos/threes); our IC 0.43-0.57, plain LTX 0.10-0.33 = floaty. Idea: free "animate on twos" post-step.
- Max-length test (base I2V, M_first, 241/481/361 frames, 1920x1088) ready on HF ic_test_2026-10-23c, launcher scratchpad
  launch_ic5.py (ledger ic_test_ledger_run5_maxlen.json); launch only after pod v4hmu38b3zucb8 stops ($1.5/h cap).
Related: [[lora-loop-2026-10-23-night]].
- 23:05 HARD TEST (pod v4hmu38b3zucb8 stopped, kept; results project files lora_plan_2026-10-22/ic_test/results2/ +
  collage_hard_test.jpg): IC holds identity of 4 heroes + 30-person crowd, 10 s stable (W10), no morph/melt (QA PASS),
  eyes/blinks/glances appear (C). BUT motion nearly frozen (hold 1.0, below cartoon p10 speed): my gaussian-warp
  layouts were too timid; IC copies the layout's (lack of) acting. Plain LTX (M_base) acts much better (gestures,
  talking mouths) and kept identity 5 s; hands mostly OK, one smeared hand, one odd hand-holding. Next: stronger,
  articulated layouts (arms/jabs >= 5-10 % of width) and IC strength 0.6 vs 1.0 so the model adds acting (~$0.7).
- Max-length pod wwuw52woensdar launched 23:03 UTC (check trigger 23:54).
- 00:25 UTC 10-24: max length (plain LTX): 10 s clean; 15 s duplicated girl + bus changes; 20 s heroes translucent; camera
  never static. IC cond 0.6/0.4 -> render turns grey (needs 1.0). All 4 pods stopped (in keep_stopped_pods). Report
  project files lora_plan_2026-10-22/ic_test/NIGHT_VIDEO_TESTS_2026-10-24_ka.md + .jpg. Recommendation: acting shots =
  plain LTX <=8-10 s; IC = staging/camera; next test pose control from his cartoons (~$0.5); video LoRA after his notes.
- 03:34 UTC 10-24 (style thread): wldnk_style_v1.0 FROZEN = v5@1750 (HF lora_plan_2026-10-22/wldnk_style_v1.0/, sha256
  b384ad49…, fallback @1250, params json). RULE: run Qwen-Image-2512 + this LoRA in bf16 on an 80 GB card; 8-bit bnb +
  LoRA gave noise in 15/20. Applies to any scene/pose test that stacks the style LoRA. Style spend tonight $4.68.
- 07:20 UTC 10-24 GUARD LESSON: pod scripts that send no status ping (all my ic_test/redraw/train pods) get STOPPED by a
  live guard at its boot deadline (`answered: false`, default boot_minutes 25): eras pod kjcetunvhdd9xv died mid-render
  after 2/5 clips. Fix: new_session(boot_minutes >= job length) or patch tools/runpod/sessions/<pod>.json answered=true,
  boot_deadline=until, then restart guard_detached. Guards usually die between calls, which is why earlier pods survived.
- 07:20 live: scene LoRA v1 TRAINING pod jzjivnicxbgf45 (SECURE $1.09/h, ledger scene_lora_run2_train_ledger.json cap 4.0,
  reserve 3.0; 60 redrawn pairs @0.55 all passed LT-41 filter + 16 kf_v2 his pairs x2; captions by Qwen2.5-VL on pod;
  output HF scene_lora_2026-10-24/train_v1/output, ckpt/sample every 250). Eras relaunch pod v3has67uzsftsl ($0.82/h,
  3 clips disco/ice_age/farm, ledger eras_video_ledger2.json); school_class + wildwest done (scratchpad erasout/).
  Redraw strength: 0.55 keeps the set, 0.7 invents (bus on the tarmac) -> 0.55.
- 07:55 UTC 10-24 ERAS DONE: 5 clips (10 s, 1920x1088, LTX native audio) in project files eras_video_2026-10-24/ + HF
  eras_video_2026-10-24/out; both pods stopped (v3has67uzsftsl in keep list), ≈$0.6. Findings: palette drift 0.001-0.009
  in 10 s; ice_age PASS but nearly frozen (hold 0.85); disco + school act well; farm (cows + farmer leave frame, empty barn)
  and wildwest (heroes blur to x0.35 detail in the last 3 s) break. Audio peaks 0 dB on 3 clips (clipping risk; unheard).
  shot-identity (LT-60..62) committed eae03a0 on PR #22. Training pod jzjivnicxbgf45 still no upload at 07:55.
- LEDGER GOTCHA (07:58 UTC): `runpod cost --ledger X` WITHOUT a pod id settles "pod:None" with the whole 24 h bill into
  the ledger (did it to both eras ledgers, repaired by hand). Always `runpod cost <pod> --ledger ...`. RunPod billing lags
  ~1 h: kjcetunvhdd9xv settled $0.06 (real ≈$0.30), v3has67uzsftsl $0 (real ≈$0.43) -> re-settle both after 09:00 UTC.
- 08:24 UTC 10-24 ვანო's PLAN (project chat, cmsg_…GHUUgUNcpuwqNAuU61aJtf): style LoRA good. Scene LoRA: finish it, and
  every keyframe must "know it is a frame of a video" (physics + composition laws kept so animating it does not break).
  Video model: he sent a 50-point evaluation framework (VBench-2.0 based: visual, temporal, physics, semantics, LoRA
  artifacts; acceptable = squash/stretch, motion blur, small background drift; unacceptable = identity morph, flicker,
  causality collapse, dynamic-degree collapse). Fix errors by training or by script, find the root cause (physics broken
  in the still is not the video model's fault). Question: how does the video model know the previous/next shot
  (linked list)? Then: a 1-minute multi-scene film (beginning, climax, end) with heroes; only after seeing its errors
  train an editing+audio LoRA (maybe one model).
- 08:55 UTC 10-24: training pod jzjivnicxbgf45 (SECURE) sat 90 min with API runtime=null / machine={} and never ran
  (billing $0 so far) -> stopped, kept. LESSON: after create, poll api.pod(id)["runtime"] for 4 min; null = no machine,
  stop and try the other cloud (launch_scene2.py now does it; boot_minutes=150). Relaunch v1 training in progress.
  VQ-01..50 registry committed a9ea2ec (PR #22); his advice taken/not table in LORA_TRAINING §7.1.
- 08:55 CORRECTION (supersedes the 08:55 note above): REST pod record shows runtime=null and machine={} for EVERY pod, also
  the working eras pod v3has67uzsftsl. So "runtime null = no machine" was WRONG; jzjivnicxbgf45 (machine e4e0u0fv49q6) probably
  ran; I stopped it at 72 min (≈$1.3 lost) because its script uploads nothing before the caption stage ends. Judge a pod
  only by what it writes to HF (pod_train.sh now uploads out/ every 4 min from setup) and by the guard log. Launcher no longer polls runtime.
- 09:30 UTC 10-24 VIDEO LoRA v1 READY, NOT LAUNCHED (no 80 GB card free 09:20-09:25; retry trigger 09:37): 83 clips (HF
  motion_lora/dataset, captions written by Claude from 5-frame sheets, motion-only), val = 5 eras stills + 1 no-trigger
  (motion_lora/val), control_ltx.json train 1000 steps / 200 min / max $6, ledger lora_plan_2026-10-22/video_lora_v1_ledger.json,
  LR 5e-5 + 60-step warm-up (pod patches LinearLR), custom negative prompt (stock one says "cartoonish", "exaggerated").
  Launcher scratchpad vlora/launch_ltx_train.py (run with PYTHONPATH=.). A PRO 6000 COMMUNITY came at $1.69/h > cap: auto-deleted.
- Scene LoRA pod w0t3l04k6w3osj trains 7.1 s/step, 1000 steps -> ends ≈11:10 UTC. Heartbeat moved to train_v1/train.log
  (stages.txt froze -> false silent alert); lint now requires the loop to rewrite a beat file (commit ecf11bb).
- ვანო 09:21/09:25 asked about LTX audio instead of ElevenLabs: answered = dialogue via LTX + A2V (voice made once, shots
  conditioned on it), narrator stays ElevenLabs; audio LoRA AFTER the 1-minute film (he asked parallel vs after; I advised after).
- 10:15 UTC 10-24 ვანო: quality first, money no object for video training; PLAN CHANGE: video LoRA launch PAUSED ($0 spent), first a
  1-minute film WITHOUT training, see errors, then ONE big joint training (motion + audio in one LTX LoRA, + av2av IC-LoRA for
  shot linking if needed) on a big card. Editing = rules, no model. Research + 12-shot Ice Age bus scenario (awaiting his OK):
  project files lora_plan_2026-10-24/PLAN_VIDEO_AUDIO_EDIT_2026-10-24_ka.md. Scene LoRA training continues (he: don't stop it).
  Evidence: MSAVBench (joint > dubbing), UnityShots (LTX-2.3 full FT, LTM first shot + STM prev tail + speaker token).
- 10:22 UTC 10-24 ვანო AGREED PLAN: scene LoRA finishes (≈11:10 UTC) -> judge 500/750/1000 + sheet -> scenario (draft in
  PLAN_VIDEO_AUDIO_EDIT doc) -> his OK -> style+scene LoRA keyframes (show him) -> 12 LTX shots with audio + ElevenLabs narrator
  -> 1-min film + QA -> errors -> video LoRA (motion+audio joint) on a big card. Cost talk: test film ≈$3-5; est. 10-min video
  ≈$20-25 now, target $10-15 after optimisation (he: optimise later).
- 10:40 UTC 10-24 ვანო RULE: no fixed 1 or 2 takes per shot: make one take, the system checks it (VQ/LT), only a FAIL gets a new
  take. Density study (his footage, 3517 shots): 11-17 shots/min (>=2 s only), median 3-4 s, ~1/3 near-static (still talking),
  so ~95 % of screen time must be real video; our eras frames are ~3x busier than the TV shows (edges 0.18 vs 0.055).
  Cost at that density, 2K, check-then-retry: ≈$10-12 per 10 min (≈$6-8 if 12 fps works). Docs in lora_plan_2026-10-24/.
- 10:45 UTC 10-24 ვანო: test film in 3 variants (24 fps / 12 fps / ~20 % less-animated shots = still + camera); LT-18 (commit
  c195d55): test videos never upscaled (they measure logic), one take + retake only on failed check, release = 2K.

### memory/video-qa-2026-10-24-chain.md

---
name: video-qa-2026-10-24-chain
description: Scene-chain test 2026-10-24 (ვანო 15:17 Tbilisi): style LoRA + scene LoRA together on Qwen-Image-Edit-2511, pod usx3b1xb9w9dy4, files and judging plan
metadata:
  type: project
---
ვანო asked (11:17 UTC): after scene LoRA v1 finishes, test frames + scene linking using style + scene LoRA TOGETHER (samples had
no style LoRA, so faces drifted). Pod usx3b1xb9w9dy4 COMMUNITY $1.19/h launched 11:27 UTC, ledger project files
lora_plan_2026-10-24/scene_chain_ledger.json (max $1.6, 2 h), heartbeat HF scene_chain_2026-10-24/log/beat.txt.
Code HF scene_chain_2026-10-24/code (chain.py, chain_cfg.json, pod_chain.sh, launch_chain.py; scratchpad chain/). bf16 + model CPU
offload. Masters: kf_v2 c07_first (4 heroes by bus), c16_first (inside bus, candle), eras ice_age_tribe. 4 beats each FROM THE MASTER,
variants sceneonly(750) / scenestyle(750 + style 0.8) / scene1000style; 2 cuts per master (style only, master + heroes sheet).
Renders -> HF scene_chain_2026-10-24/renders/. Pod does NOT stop itself: stop it from here when finished.txt appears.
Scene LoRA v1 samples 0-750 sheet: project files lora_plan_2026-10-24/scene_lora_v1_samples_0-750.jpg (camera held; action to wrong
hero; invents a person on "the woman" prompt; 750 near-static on shout prompt). Guards die minutes after each turn: restart each wake.
Related: [[video-qa-2026-10-23]].
- 11:50 UTC: ვანო asked for prompt patterns/anti-patterns + my errors -> rules to scenario agents. Done: docs/SHOT_PROMPTS.md
  KP-01..14 (new docs_lint family KP), scripting/shot_prompt_lint.py + test, story-architect/edit-planner/shot-visuals updated,
  commit cb96af5 (PR #22). Ka summary project files lora_plan_2026-10-24/SHOT_PROMPT_RULES_2026-10-24_ka.md. BIG FINDING: every
  LTX test so far ran with LTX's stock negative ("cartoonish rendering", "exaggerated expressions") -> always pass our own neg.
  Chain cfg icetribe beats 1 and 3 rewritten on HF ~11:46 (pod booted 11:38, may have read the old cfg: check chain.log).
- 11:53 UTC: first chain pod usx3b1xb9w9dy4 hung 12 min right after its CUDA check (python never exited?), stopped + kept, ledger scene_chain_ledger.json (re-settle later). Relaunched pod 5r50psn3elm6un COMMUNITY $0.82/h, ledger scene_chain_ledger2.json, script with timeouts + STEP markers.
- 11:53 UTC: new thread 'prompt and script rules' (session_01YRz9PnCFLixv8VHrrWaYPy) extends SHOT_PROMPTS.md (KP-15+) + shot_prompt_lint.py on a branch stacked on PR #22 and builds a shot-contract composer (~2-3 h). Do NOT edit those two files without telling it first; use its composer for the 1-min film shot list. Its tips: actor = 2+ traits + screen position; LTX dialogue in quotes with speaker by traits + voice note; LTX = one flowing present-tense paragraph in time order.
- 12:15 UTC: relaunch renders ~118 s/image (CPU offload); 42 images -> ETA ~13:35 UTC. Early bus4 sceneonly with KP prompts: 4/4 actions on the RIGHT hero, camera held (prompts were the problem); artifacts: glow ring at girl's feet (beat2), odd raised leg (beat3).
- 12:15 UTC: thread 'prompt and script rules' shipped PR #24 (branch claude/project-thread-ubp4ge, stacked on #22): film_shots/1 cards (example examples/film_shots/bus_in_the_ice_age.json); 'python -m explainer_engine.scripting.film_shots check <file>' then 'compose <file> --out prompts.json' -> pods read prompts.json. Rules for next renders: keyframe = START pose (last_frame: true -> settle pose as nextpose from master guides last frame); no story names in prompts (cast tag); no 'smooth natural character motion'; no score music in LTX prompts; <=2 people in MS-or-closer; negatives film_shots.NEG_KEYFRAME / NEG_VIDEO. Write the 1-min film shot list with it.
- 12:30 UTC LT-19 committed 4ac3220 (PR #22): root cause of chain pod hang = my launchers popped allowedCudaVersions -> driver-550 host for CUDA13 aitoolkit image, get_device_name never returned; heartbeat loop masked it. Fix: lint needs timeout on CUDA probes, BAD_HOST in heartbeat -> guard stops pod, create() refuses body w/o CUDA filter unless any_cuda=True. Pod script template: timeout 120 probe || { echo BAD_HOST ... > out/beat.txt; up; }; loop: grep -q BAD_HOST beat.txt || date > beat.txt.
- 12:45 UTC bus4 comparison (project files scene_chain_bus4_variants.jpg): sceneonly(750) 4/4 clean; +style 0.8 adds speed lines/swirls, smears; 1000+style swaps identities (nurse gets beard). Told ვანო: style LoRA only for master, next poses scene LoRA only. 2 uploads failed (network unreachable on pod); chain.py 5400 s timeout cuts ~13:22 UTC.
- 12:45 UTC ვანო GOAL: one system that knows BOTH the universe style and scene composition (not a collage); he doesn't want them as two separate tools. Plan told him: (1) after current chain run, weight test style 0.2/0.35/0.5 + scene 1.0 on beats, cuts, and a NEW scene from hero sheet (~$0.5); (2) if not good: train ONE unified LoRA on Qwen-Edit-2511 = scene pairs + his 24 style photos as (sheet/place -> styled scene) pairs, ~$3-5 from the $8 scene budget.
- 12:55 UTC weight test READY (not launched): scratchpad wtest/ (wtest.py no CPU offload, 80 GB cards, 21 images: bus4 beats 1/3, ice beat1, 2 cuts, new snow-cave scene from sheet; style 0.2/0.35/0.5 + scene750 1.0, cuts/new also style-only 0.8), launcher wtest/launch_wtest.py (PYTHONPATH=., ledger scene_chain_weights_ledger.json max $1.2), outputs HF scene_chain_2026-10-24/weights/. Launch after chain pod 5r50psn3elm6un stops ($1.5/h cap).
- 12:50 UTC ვანო upset about today's spend. RunPod billing since 00 UTC 10-24: $6.83 (+~$0.9 running). My errors ≈$1.0 (chain hang $0.58, eras guard kill ≈$0.3, 3 failed scene2 launches $0.14); jzjivnicxbgf45 (the "≈$1.3 lost" 72-min pod) does NOT appear in billing (likely $0). Scene LoRA training billed $2.23 (ledger had 1.38: re-settle). RULE I promised: a new combination is first tried on 2-3 images, only then the full set.
- 13:30 UTC chain test DONE (timeout cut icetribe 1000 variant + its cuts; 3 uploads failed). Pod 5r50psn3elm6un stopped+kept (committed), settled $0.45; usx3b $0.63; scene training re-settled $2.23. Verdict: scene only ~70% (businside: wrong actor on 2/3; ice: cat/kids barely change); scene+style0.8 = junk; cuts (style only) good. Weight test pod ifghvnsx95wmgb launched 13:30 UTC COMMUNITY $1.39/h any_cuda=True (no filtered stock), guard 336, outputs HF scene_chain_2026-10-24/weights/. Sheets project files scene_chain_businside.jpg / scene_chain_icetribe.jpg.
- 14:05 UTC WEIGHT TEST DONE (pod ifghvnsx95wmgb stopped, kept+committed; billing lag: re-settle scene_chain_weights_ledger.json; ~56 s/image on 80 GB no offload, ~100 s for 2-image cuts). Sheet project files lora_plan_2026-10-24/style_weight_test.jpg. RECIPE (one model Qwen-Edit-2511, both adapters loaded): NEW scene from hero sheet = style 0.8 (or scene1.0+style0.2); CUT = scene1.0+style0.2-0.35 (better than style-only); POSE = scene only (style at ANY weight swaps identities). Ice-tribe small/busy frame barely changes (KP-13). Advised: unified LoRA not needed now; next = 1-min film keyframes with this recipe + film_shots cards, awaiting ვანო's OK.

### memory/youtube-staging-upload.md

---
name: youtube-staging-upload
description: state of the YouTube staging-upload tool (publish stage/thumbnail/auth, D-56, PR #7) and what blocks real uploads
metadata:
  type: project
  modified: 2026-10-19T18:25:57.538Z
---

- explainer-engine PR #7 (draft, claude/youtube-upload-cfe6z7 -> systemic/next-video): `python -m explainer_engine.publish stage|thumbnail|auth`. Unlisted default, private allowed, never public. Inputs: episode `publish.json` (tags, youtube, thumbnail, per-Short title) + script Shorts + render/video.mp4, render/shorts/SHxx.mp4.
- 2026-10-19 15:44: phone sign-in done via `publish auth-url`/`auth-finish`; channel = CrossWorld Chronicles, id UCndsNlyExB-jKRB9hs283BQ (EXPLAINER_YT_CHANNEL). Token lives only in that session's container (tools/youtube/, gitignored); app is in Testing (token dies in 7 days; Publish app was greyed out). Creator decided 2026-10-19: NO token stored or pasted anywhere; per upload session Claude gives a fresh auth-url link, creator sends back the 127.0.0.1 address, auth-finish exchanges it. Never print the token in chat. YOUTUBE_CLIENT_B64 (client JSON) stays in the env.
- (older) YOUTUBE_TOKEN_B64 in the cloud env is TMR's old token, expired (invalid_grant; the OAuth app was in Testing = 7-day tokens). Needs: consent screen "In production", `publish auth` on the creator's PC, new YOUTUBE_TOKEN_B64 + EXPLAINER_YT_CHANNEL in the env. Asked creator 2026-10-19.
- API facts: location deprecated, paid promotion not settable on insert -> Studio checklist; upload = 1 unit of a 100/day bucket.
- Syndicate Wars has no publish.json yet (metadata.md only); title still open.

- STANDING RULE (creator 2026-10-19, cmsg_01Hnu5zB86sjUj5GtTgaUkPWYDkwpHPwbkPkZjE11J4EiR): every video or Short is staged unlisted the moment it passes its own tests, one at a time (`stage --only <id>`), never waiting for the batch. Written in docs/PRODUCTION_RULES.md standing order 9 + CLAUDE.md (commit 6f5d902 on claude/syndicate-wars-paint-oj7rwe). This is the creator's standing OK for unlisted staging; Public stays his click.
- 2026-10-19: merging PR #7's branch into the Syndicate Wars branch was refused by the session's auto-mode safety check ("public surface"); uploads need the creator to allow it in the session.

**Why:** creator wants finished videos + 10 Shorts staged unlisted, they only review and click Public.
**How to apply:** no upload or thumbnail generation without the creator's explicit OK in the thread; use `--confirm`/`--approved-by` with that ref.

---

## დანართი C: `/mnt/project-files/` ჩამონათვალი (2026-10-29; ბაიტი, გზა)

`uploads/hearth/` (71 ვანოს ატვირთვა id-ებით) აქ არ არის ჩამოთვლილი.

```
26750	explainer-engine/AUDIT_2026-10-19/A1_youtube_policy_sources.md
24707	explainer-engine/AUDIT_2026-10-19/A2_image_providers.md
40173	explainer-engine/AUDIT_2026-10-19/A3_engineering_review.md
33717	explainer-engine/AUDIT_2026-10-19/AUDIT_2026-10-19.md
16710	explainer-engine/HANDOFF_2026-10-19.md
19467	explainer-engine/INTEGRATED_REVIEW_2026-10-20.md
27090	explainer-engine/PARAMETER_AUDIT_2026-10-19_ka.md
20443	explainer-engine/SYSTEM_AUDIT_2026-10-19/RULE_CONTRADICTIONS.md
62859	explainer-engine/SYSTEM_AUDIT_2026-10-19/SOURCED_RULES.md
37373	explainer-engine/SYSTEM_AUDIT_2026-10-19/rescan_2026-10-20/A_rules_crosscheck.md
39435	explainer-engine/SYSTEM_AUDIT_2026-10-19/rescan_2026-10-20/B_numbers.md
18440	explainer-engine/SYSTEM_AUDIT_2026-10-19/rescan_2026-10-20/C_e2e.md
42737	explainer-engine/SYSTEM_AUDIT_2026-10-19/research/audio_mix.md
39907	explainer-engine/SYSTEM_AUDIT_2026-10-19/research/motion_text.md
35229	explainer-engine/SYSTEM_AUDIT_2026-10-19/research/narration.md
42685	explainer-engine/SYSTEM_AUDIT_2026-10-19/research/retention_shorts.md
36282	explainer-engine/THUMBNAIL_RESEARCH_2026-10-19.md
18638	explainer-engine/VIDEO_PLAN_8-12min.md
9413	explainer-engine/animation_universe_2026-10-22/ANIMATION_TOOLS_2026-10-22.md
21194	explainer-engine/animation_universe_2026-10-22/ANIMATION_UNIVERSE_2026-10-22.md
18002	explainer-engine/animation_universe_2026-10-22/GEGMA_ka.md
16505	explainer-engine/animation_universe_2026-10-22/board_prompts.txt
12407	explainer-engine/animation_universe_2026-10-22/ice_test/AUDIT_ice_shot_ka.md
7425783	explainer-engine/animation_universe_2026-10-22/ice_test/ice_shot.mp4
278097	explainer-engine/animation_universe_2026-10-22/ice_test/ice_shot_frames.jpg
6010865	explainer-engine/animation_universe_2026-10-22/ice_test/ice_shot_v2.mp4
39	explainer-engine/animation_universe_2026-10-22/ice_test/ice_shot_v2_check.json
290688	explainer-engine/animation_universe_2026-10-22/ice_test/ice_shot_v2_frames.jpg
697780	explainer-engine/animation_universe_2026-10-22/ice_test/ice_test_round2.jpg
619719	explainer-engine/animation_universe_2026-10-22/ice_test/ice_test_seedream_t1.jpg
571668	explainer-engine/animation_universe_2026-10-22/ice_test/ice_test_seedream_t2.jpg
374	explainer-engine/animation_universe_2026-10-22/rig_poc/rig_poc.json
528909	explainer-engine/animation_universe_2026-10-22/rig_poc/rig_poc.mp4
191198	explainer-engine/animation_universe_2026-10-22/rig_poc/rig_poc_frames.jpg
126657	explainer-engine/animation_universe_2026-10-22/rig_poc/rig_poc_sheet.jpg
711517	explainer-engine/animation_universe_2026-10-22/worlds/world_bold_poster_t1.jpg
745949	explainer-engine/animation_universe_2026-10-22/worlds/world_bold_poster_t2.jpg
802415	explainer-engine/animation_universe_2026-10-22/worlds/world_ink_cel_t1.jpg
834344	explainer-engine/animation_universe_2026-10-22/worlds/world_ink_cel_t2.jpg
651025	explainer-engine/animation_universe_2026-10-22/worlds/world_paper_stage_t1.jpg
665333	explainer-engine/animation_universe_2026-10-22/worlds/world_paper_stage_t2.jpg
652299	explainer-engine/animation_universe_2026-10-22/worlds/world_poster_graphic_t1.jpg
664022	explainer-engine/animation_universe_2026-10-22/worlds/world_poster_graphic_t2.jpg
717434	explainer-engine/animation_universe_2026-10-22/worlds/world_shape_caricature_t1.jpg
739125	explainer-engine/animation_universe_2026-10-22/worlds/world_shape_caricature_t2.jpg
622999	explainer-engine/animation_universe_2026-10-22/worlds/world_soft_volume_t1.jpg
641691	explainer-engine/animation_universe_2026-10-22/worlds/world_soft_volume_t2.jpg
646470	explainer-engine/animation_universe_2026-10-22/worlds/world_sunny_rubber_seedream_t1.jpg
620955	explainer-engine/animation_universe_2026-10-22/worlds/world_sunny_rubber_seedream_t2.jpg
682491	explainer-engine/animation_universe_2026-10-22/worlds/world_sunny_rubber_t1.jpg
717476	explainer-engine/animation_universe_2026-10-22/worlds/world_sunny_rubber_t2.jpg
599368	explainer-engine/animation_universe_2026-10-22/worlds/world_warm_geometry_seedream_t1.jpg
595307	explainer-engine/animation_universe_2026-10-22/worlds/world_warm_geometry_seedream_t2.jpg
588469	explainer-engine/animation_universe_2026-10-22/worlds/world_warm_geometry_t1.jpg
587832	explainer-engine/animation_universe_2026-10-22/worlds/world_warm_geometry_t2.jpg
928313	explainer-engine/animation_universe_2026-10-22/worlds/world_wild_ink_t1.jpg
986062	explainer-engine/animation_universe_2026-10-22/worlds/world_wild_ink_t2.jpg
14470	explainer-engine/architecture_2026-10-22/ARCHITECTURE_PLAN_2026-10-22.md
15950	explainer-engine/architecture_2026-10-22/REPO_AUDIT_2026-10-22.md
8138	explainer-engine/architecture_2026-10-22/RUNPOD_VALIDATION_2026-10-22.md
45891	explainer-engine/architecture_2026-10-22/TOOLING_IMAGE_2026-10-22.md
47656	explainer-engine/architecture_2026-10-22/TOOLING_INFRA_2026-10-22.md
15132	explainer-engine/architecture_2026-10-22/TOOLING_RESEARCH.md
43294	explainer-engine/architecture_2026-10-22/TOOLING_VIDEO_VOICE_2026-10-22.md
19761	explainer-engine/architecture_2026-10-22/TOOL_STRATEGY.md
6197	explainer-engine/architecture_2026-10-22/WORLD_BIBLE.md
31953	explainer-engine/architecture_2026-10-22/parallax_test_depth.png
1505178	explainer-engine/architecture_2026-10-22/parallax_test_ends.png
16239	explainer-engine/dialogue_research_2026-10-26/PERSONAPLEX_ka.md
14879843	explainer-engine/eras_video_2026-10-24/disco_1970s_base.mp4
1033	explainer-engine/eras_video_2026-10-24/disco_1970s_qa.json
17502918	explainer-engine/eras_video_2026-10-24/farm_storm_base.mp4
1033	explainer-engine/eras_video_2026-10-24/farm_storm_qa.json
6053768	explainer-engine/eras_video_2026-10-24/ice_age_tribe_base.mp4
843	explainer-engine/eras_video_2026-10-24/ice_age_tribe_qa.json
10791123	explainer-engine/eras_video_2026-10-24/school_class_base.mp4
855	explainer-engine/eras_video_2026-10-24/school_class_qa.json
141126	explainer-engine/eras_video_2026-10-24/strip_disco_1970s.jpg
130947	explainer-engine/eras_video_2026-10-24/strip_farm_storm.jpg
140662	explainer-engine/eras_video_2026-10-24/strip_ice_age_tribe.jpg
165172	explainer-engine/eras_video_2026-10-24/strip_school_class.jpg
122552	explainer-engine/eras_video_2026-10-24/strip_wildwest_train.jpg
14209068	explainer-engine/eras_video_2026-10-24/wildwest_train_base.mp4
1038	explainer-engine/eras_video_2026-10-24/wildwest_train_qa.json
10050	explainer-engine/film_1min_2026-10-24/SCENARIO_AND_TEST_ka.md
11306	explainer-engine/film_1min_2026-10-24/TEST_PLAN_v2_ka.md
473	explainer-engine/film_1min_2026-10-24/atest_ledger.json
1439141	explainer-engine/film_1min_2026-10-24/compose_demo/B1.png
1466847	explainer-engine/film_1min_2026-10-24/compose_demo/S1.png
1476932	explainer-engine/film_1min_2026-10-24/compose_demo/S2.png
1337684	explainer-engine/film_1min_2026-10-24/compose_demo/S3.png
378041	explainer-engine/film_1min_2026-10-24/compose_demo/demo_sheet.jpg
4031	explainer-engine/film_1min_2026-10-24/compose_demo/library.json
467	explainer-engine/film_1min_2026-10-24/ctest_ledger.json
18743	explainer-engine/film_1min_2026-10-24/film_1min.json
35639	explainer-engine/film_1min_2026-10-24/film_1min_prompts.json
920	explainer-engine/film_1min_2026-10-24/ftest_ledger.json
447	explainer-engine/film_1min_2026-10-24/ntest_ledger.json
479	explainer-engine/film_1min_2026-10-24/stest_ledger.json
10995	explainer-engine/film_1min_2026-10-24/test_v2/REPORT_ka.md
1402163	explainer-engine/film_1min_2026-10-24/test_v2/T1_technical_vs_relative.jpg
706996	explainer-engine/film_1min_2026-10-24/test_v2/T3_controlnet_vs_relative.jpg
556187	explainer-engine/film_1min_2026-10-24/test_v2/T4_cuts.jpg
2192065	explainer-engine/film_1min_2026-10-24/test_v2/T4_poses.jpg
364795	explainer-engine/film_1min_2026-10-24/test_v2/assets_sheet.jpg
6466	explainer-engine/film_1min_2026-10-24/test_v2/ftest.log
312223	explainer-engine/film_1min_2026-10-24/test_v2/masters_sheet.jpg
402046	explainer-engine/film_1min_2026-10-24/test_v2/neg_bus_sheet.jpg
528436	explainer-engine/film_1min_2026-10-24/test_v2/neg_ice_sheet.jpg
75523	explainer-engine/film_1min_2026-10-24/test_v2/qa_log.jsonl
71625	explainer-engine/film_1min_2026-10-24/test_v2/results.jsonl
602669	explainer-engine/film_1min_2026-10-24/test_v2/style_vs_approved.jpg
11295	explainer-engine/film_1min_2026-10-25/GPT_RESEARCH_BRIEF.md
5818	explainer-engine/film_1min_2026-10-25/SPEC_current_run.md
663	explainer-engine/film_1min_2026-10-25/atest_ledger.json
3265	explainer-engine/film_1min_2026-10-25/film/assemble.py
1464	explainer-engine/film_1min_2026-10-25/film/collage.py
1882	explainer-engine/film_1min_2026-10-25/film/collage_specs.json
1882	explainer-engine/film_1min_2026-10-25/film/cut.py
13600925	explainer-engine/film_1min_2026-10-25/film/film_A_ltx_voices.mp4
160100	explainer-engine/film_1min_2026-10-25/film/film_A_sheet.jpg
3682	explainer-engine/film_1min_2026-10-25/film/pod_film.sh
8247	explainer-engine/film_1min_2026-10-25/film/worker.py
803	explainer-engine/film_1min_2026-10-25/film_ledger.json
646	explainer-engine/film_1min_2026-10-25/gen100_ledger.json
438	explainer-engine/film_1min_2026-10-25/layout_ledger.json
391	explainer-engine/film_1min_2026-10-25/pano_ledger.json
9290	explainer-engine/film_1min_2026-10-25/world/ambient.py
6771	explainer-engine/film_1min_2026-10-25/world/scene2.json
7857	explainer-engine/film_1min_2026-10-25/world/world2.py
11219	explainer-engine/ideas/future_video_concepts_2026-10-19.md
11155	explainer-engine/ideas/future_video_concepts_v2_wild_2026-10-19.md
73234	explainer-engine/integrated_review_2026-10-20.diff
5790	explainer-engine/lora_plan_2026-10-24/ANIMATION_DENSITY_COST_2026-10-24_ka.md
8797	explainer-engine/lora_plan_2026-10-24/COST_OPTIMIZATION_VIDEO_2026-10-24_ka.md
12697	explainer-engine/lora_plan_2026-10-24/KEYFRAME_GATE_PLAN_2026-10-24_ka.md
9260	explainer-engine/lora_plan_2026-10-24/PLAN_VIDEO_AUDIO_EDIT_2026-10-24_ka.md
9461	explainer-engine/lora_plan_2026-10-24/SHOT_PROMPT_RULES_2026-10-24_ka.md
10175	explainer-engine/lora_plan_2026-10-24/STYLE_SCENE_DIAGNOSIS_2026-10-24_ka.md
814226	explainer-engine/lora_plan_2026-10-24/scene_chain_bus4_variants.jpg
589578	explainer-engine/lora_plan_2026-10-24/scene_chain_businside.jpg
486832	explainer-engine/lora_plan_2026-10-24/scene_chain_early_bus4_sceneonly.jpg
516541	explainer-engine/lora_plan_2026-10-24/scene_chain_icetribe.jpg
656	explainer-engine/lora_plan_2026-10-24/scene_chain_ledger.json
715	explainer-engine/lora_plan_2026-10-24/scene_chain_ledger2.json
672	explainer-engine/lora_plan_2026-10-24/scene_chain_weights_ledger.json
571	explainer-engine/lora_plan_2026-10-24/scene_lora_run2_train_ledger.json
825581	explainer-engine/lora_plan_2026-10-24/scene_lora_v1_samples_0-1000.jpg
885004	explainer-engine/lora_plan_2026-10-24/scene_lora_v1_samples_0-750.jpg
392502	explainer-engine/lora_plan_2026-10-24/style_check_approved_vs_test.jpg
1059761	explainer-engine/lora_plan_2026-10-24/style_weight_test.jpg
40015	explainer-engine/napoleon_vs_genghis_2026-10-24/PROMPT_PACKAGE.md
11941	explainer-engine/napoleon_vs_genghis_2026-10-24/SCRIPT_ENGINE.md
6606	explainer-engine/napoleon_vs_genghis_2026-10-24/SCRIPT_ENGINE_V2_2026-10-24.md
220594	explainer-engine/napoleon_vs_genghis_2026-10-24/film_shots.json
482368	explainer-engine/napoleon_vs_genghis_2026-10-24/prompts.json
18787	explainer-engine/napoleon_vs_genghis_2026-10-24/script.md
250375	explainer-engine/napoleon_vs_genghis_2026-10-24/shotlist.md
1706	explainer-engine/plan_review_2026-10-23/benchmark_10shot.json
28357	explainer-engine/plan_review_2026-10-23/plan_review.html
1259	explainer-engine/plan_review_2026-10-23/shot_schema_v1.json
6544	explainer-engine/prompt_rules_2026-10-24/PROMPT_RULES_AUDIT_2026-10-24_ka.md
37076	explainer-engine/research_driven_2026-10-19.diff
18792	explainer-engine/scripts_export/1_stone_age_100_geniuses.md
25535	explainer-engine/scripts_export/2_syndicate_wars.md
25857	explainer-engine/scripts_export/3_titans_went_broke.md
4714	explainer-engine/storytelling_research/RULE_CONFLICTS_2026-10-19.md
25869	explainer-engine/storytelling_research/audio_cues.md
32991	explainer-engine/storytelling_research/dialogue_craft.md
33218	explainer-engine/storytelling_research/editing_psychology.md
27093	explainer-engine/storytelling_research/internal_system_audit.md
35694	explainer-engine/storytelling_research/story_structure.md
26487	explainer-engine/storytelling_research/youtube_editing_practice.md
34421	explainer-engine/storytelling_research/სთორითელინგის და მონტაჟის კვლევა.md
2241	explainer-engine/syndicate_wars/gta6_official_facts_2026-10-19.md
470644	explainer-engine/syndicate_wars/review/face_sheets_v1.jpg
571783	explainer-engine/syndicate_wars/review/reference_collage_v1.jpg
816165	explainer-engine/syndicate_wars/review/voice_test/test_all_bosses.mp3
255055	explainer-engine/syndicate_wars/review/voice_test/test_capone.mp3
211691	explainer-engine/syndicate_wars/review/voice_test/test_mizuno.mp3
173553	explainer-engine/syndicate_wars/review/voice_test/test_shelby.mp3
136981	explainer-engine/syndicate_wars/review/voice_test/test_vito.mp3
6966	explainer-engine/syndicate_wars/scenario_dialogue_v1.md
2577907	explainer-engine/thumbnail_motif/cache/0787c9f292ab5175e8c5ae8a.png
3303963	explainer-engine/thumbnail_motif/cache/88af04e819f7586934277960.png
2563853	explainer-engine/thumbnail_motif/cache/8b09311a225cdeadfd6aff6b.png
2299596	explainer-engine/thumbnail_motif/cache/bb4e6b50963f05a347ab0e7e.png
2662533	explainer-engine/thumbnail_motif/cache/d0a75ad2e12f7cfc9c316549.png
2535660	explainer-engine/thumbnail_motif/cache/ffdab817259a23650e0023df.png
2662533	explainer-engine/thumbnail_motif/short_cover_9x16.png
2535660	explainer-engine/thumbnail_motif/short_cover_v2_9x16.png
470495	explainer-engine/thumbnail_motif/short_cover_v2_text.jpg
2299596	explainer-engine/thumbnail_motif/silhouette_collage.png
1938	explainer-engine/thumbnail_motif/spend_log.jsonl
2577907	explainer-engine/thumbnail_motif/thumb_draft_16x9.png
2563853	explainer-engine/thumbnail_motif/thumb_v2_16x9.png
300619	explainer-engine/thumbnail_motif/thumb_v2_text.jpg
564892	explainer-engine/thumbnail_motif/thumbnail_niche_sheet1_2026-10-19.jpg
551564	explainer-engine/thumbnail_motif/thumbnail_niche_sheet2_2026-10-19.jpg
3303963	explainer-engine/thumbnail_motif/woman_collage.png
5536	explainer-engine/titans_from_zero/B1_review.md
1464117	explainer-engine/titans_from_zero/B1_sheet_1.jpg
1451368	explainer-engine/titans_from_zero/B1_sheet_2.jpg
1495648	explainer-engine/titans_from_zero/B1_sheet_3.jpg
1222684	explainer-engine/titans_from_zero/B2_sheet.jpg
36811	explainer-engine/titans_from_zero/build_script.py
1687	explainer-engine/titans_from_zero/claim_map.md
292517	explainer-engine/titans_from_zero/conversation_blur_v2.jpg
454027	explainer-engine/titans_from_zero/conversation_variants_v1.jpg
29368	explainer-engine/titans_from_zero/editorial_review.json
18638	explainer-engine/titans_from_zero/episode_rules.md
897888	explainer-engine/titans_from_zero/faces_v1.jpg
4197	explainer-engine/titans_from_zero/fictional_cast_draft.md
678478	explainer-engine/titans_from_zero/first_pictures_v1.jpg
3461664	explainer-engine/titans_from_zero/hero_caricatures_v1.png
150496	explainer-engine/titans_from_zero/one_narrator/card_intro.jpg
130975	explainer-engine/titans_from_zero/one_narrator/card_recap_1.jpg
135855	explainer-engine/titans_from_zero/one_narrator/card_recap_2.jpg
124079	explainer-engine/titans_from_zero/one_narrator/card_recap_3.jpg
90438	explainer-engine/titans_from_zero/one_narrator/card_recap_4.jpg
7591	explainer-engine/titans_from_zero/one_narrator/new_lines.md
114582072	explainer-engine/titans_from_zero/one_narrator/titans_full_v3_720p.mp4
10489	explainer-engine/titans_from_zero/paid_assets_estimate.md
324137	explainer-engine/titans_from_zero/preview/parts_1_2_frames.jpg
14587896	explainer-engine/titans_from_zero/preview/titans_parts_1_2_720p.mp4
574717	explainer-engine/titans_from_zero/production_script.json
2014	explainer-engine/titans_from_zero/qa_loop/creator_concerns_2026-10-20.md
44536	explainer-engine/titans_from_zero/qa_loop/long_research_storytelling.md
10095	explainer-engine/titans_from_zero/qa_loop/new_narration_v1.md
27689	explainer-engine/titans_from_zero/qa_loop/research_edit_dialogue.md
29637	explainer-engine/titans_from_zero/qa_loop/research_edit_text_graphics.md
41558	explainer-engine/titans_from_zero/qa_loop/research_edit_variants.md
41410	explainer-engine/titans_from_zero/qa_loop/research_editing_rules.md
16225	explainer-engine/titans_from_zero/qa_loop/research_narrated_dialogue.md
12951	explainer-engine/titans_from_zero/qa_loop/static_analysis.md
1598	explainer-engine/titans_from_zero/review/S02_reported_speech_v1.md
12414	explainer-engine/titans_from_zero/review_v1.md
14038	explainer-engine/titans_from_zero/scenario_v1.md
14067	explainer-engine/titans_from_zero/scenario_v2.md
13970	explainer-engine/titans_from_zero/scenario_v3.md
14558	explainer-engine/titans_from_zero/script_v1.md
15116	explainer-engine/titans_from_zero/script_v2.md
15393	explainer-engine/titans_from_zero/script_v3.md
14457	explainer-engine/titans_from_zero/script_v4.md
21034	explainer-engine/titans_from_zero/script_v5.md
12488	explainer-engine/titans_from_zero/story_page.md
3191386	explainer-engine/titans_from_zero/style_collage_v1.png
213947	explainer-engine/titans_from_zero/thumbnail/titans_thumbnail_draft.jpg
761972	explainer-engine/titans_from_zero/voice/T01.mp3
376613	explainer-engine/titans_from_zero/voice/T02.mp3
713071	explainer-engine/titans_from_zero/voice/T03.mp3
490716	explainer-engine/titans_from_zero/voice/T04.mp3
390824	explainer-engine/titans_from_zero/voice/T05.mp3
916617	explainer-engine/titans_from_zero/voice/T06.mp3
505763	explainer-engine/titans_from_zero/voice/T07.mp3
788721	explainer-engine/titans_from_zero/voice/T08.mp3
552156	explainer-engine/titans_from_zero/voice/T09.mp3
260003	explainer-engine/titans_from_zero/voice/T10.mp3
560933	explainer-engine/titans_from_zero/voice/T11.mp3
796244	explainer-engine/titans_from_zero/voice/T12.mp3
657064	explainer-engine/titans_from_zero/voice/T13.mp3
274213	explainer-engine/titans_from_zero/voice/shorts/SH01.mp3
390824	explainer-engine/titans_from_zero/voice/shorts/SH02.mp3
187278	explainer-engine/titans_from_zero/voice/shorts/SH03.mp3
187278	explainer-engine/titans_from_zero/voice/shorts/SH04.mp3
371598	explainer-engine/titans_from_zero/voice/shorts/SH05.mp3
256241	explainer-engine/titans_from_zero/voice/shorts/SH06.mp3
243284	explainer-engine/titans_from_zero/voice/shorts/SH07.mp3
193547	explainer-engine/titans_from_zero/voice/shorts/SH08.mp3
168052	explainer-engine/titans_from_zero/voice/shorts/SH09.mp3
313920	explainer-engine/titans_from_zero/voice/shorts/SH10.mp3
1028	explainer-engine/titans_from_zero/voice_generations.json
208694	xworld_v1/cast/objects.jpg
519624	xworld_v1/cast/places.jpg
376289	xworld_v1/cast/test4_sheet.jpg
181815	xworld_v1/napoleon/faces0.jpg
174157	xworld_v1/napoleon/faces1.jpg
295669	xworld_v1/napoleon/row0.jpg
362068	xworld_v1/napoleon/row1.jpg
220003	xworld_v1/napoleon/row2.jpg
286213	xworld_v1/napoleon/row3.jpg
403677	xworld_v1/test_scene1.jpg
537471	xworld_v1/test_scene2.jpg
468728	xworld_v1/test_scene3.jpg
518210	xworld_v1/test_scene4.jpg
570413	xworld_v1/training_samples_1750-2500.jpg
26469	xworld_v2/AUTO_QA_PLAN_2026-10-26_ka.md
19747	xworld_v2/CONSISTENCY_STRATEGIES_2026-10-26.md
8135	xworld_v2/REPORT_3000_BACKGROUNDS_2026-10-26.md
3374	xworld_v2/ROUND1_REVIEW_2026-10-26.md
4992	xworld_v2/S3C_CONTROLNET_PLAN_2026-10-26.md
8984	xworld_v2/S3_LAYOUT_PLAN_2026-10-26.md
22493	xworld_v2/STRATEGY_LOOP_PLAN_2026-10-26.md
8884902	xworld_v2/gallery/index.html
1674403	xworld_v2/loop_round1/round1_cards.html
526479	xworld_v2/loop_round1/sheet_grids.jpg
1602742	xworld_v2/round0/sheet_rome.jpg
1224145	xworld_v2/round0/sheet_tent.jpg
1526023	xworld_v2/round0/sheet_tundra.jpg
568973	xworld_v2/round1/r1500_rome.jpg
592823	xworld_v2/round1/r1500_tent.jpg
522914	xworld_v2/round1/r1500_tundra.jpg
619697	xworld_v2/round1/r2250_rome.jpg
639494	xworld_v2/round1/r2250_tent.jpg
572854	xworld_v2/round1/r2250_tundra.jpg
563369	xworld_v2/round1/r750_rome.jpg
607004	xworld_v2/round1/r750_tent.jpg
469638	xworld_v2/round1/r750_tundra.jpg
909916	xworld_v2/round3000/p2s_rome.jpg
657724	xworld_v2/round3000/p2s_tent.jpg
826688	xworld_v2/round3000/s2_sheet.jpg
1621357	xworld_v2/round3000/s3_sheet.jpg
556278	xworld_v2/round3000/sheet_tundra.jpg
2103	xworld_v2/round_3b/attribution.md
198659	xworld_v2/round_3b/v3b_po.jpg
516566	xworld_v2/round_3b/v3b_rome.jpg
417824	xworld_v2/round_3b/v3b_ship.jpg
274230	xworld_v2/round_3b/v3b_tent.jpg
408824	xworld_v2/round_3b/v3b_tundra.jpg
103403	xworld_v2/s3_layouts_preview.jpg
969581	xworld_v2/s3c/s3c_sheet.jpg
868	xworld_v2/s3c/spearman.json
459490	xworld_v2/s3c/step0_base.png
1166746	xworld_v2/s3c/step0_lora.png
```
