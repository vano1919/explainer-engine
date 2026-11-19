# Step E: Proposal for One Cheapest Paid Calibration Test (`E_PAID_TEST_PROPOSAL.md`)

## მოკლე შეჯამება დამკვეთისთვის (ქართულად)

- **რა გაკეთდა:** შევადგინეთ (გაშვების გარეშე, `OR-23` / `RP-07` წესების სრული დაცვით) **ერთი ყველაზე იაფი ფასიანი ტესტის (`p15_mini_cal`)** გეგმა, რომელიც ერთდროულად ხსნის აუდიტისა და ხარჯთაღრიცხვის დროს აღმოჩენილ **უდიდეს გაუზომავ კითხვებს** და ჯდება არსებულ `p15` გეგმაზე (`$3.40–$3.50`) **5-ჯერ იაფი**:
  - **მოსალოდნელი ხარჯი:** **$0.43** (`A100 80GB community @ $1.39/სთ`, `~18.7 წთ`) ან **$0.66** (`H100 NVL @ $2.59/სთ`, `~13.4 წთ`).
  - **უარესი შემთხვევის (Worst-Case) ჭერი:** **$0.70** (`A100 community`, 30 წთ ტაიმაუტი) / **$1.30** (`H100 NVL`, მკაცრი `--max-usd 1.30 --max-hours 0.50` ლიმიტი), რაც ხელუხლებელს ტოვებს RunPod-ის `$7.99` ბალანსის მინიმუმ `$6.69`-ს (`min_balance_left_usd = $1.00`).
- **რა კითხვებს პასუხობს ეს ერთი ტესტი:**
  1. **LTX-2.5-ის რეალური სიჩქარე და ფასი `1920x1088`-ზე (`config/job_speeds.json`-ის შესავსებად):** რამდენი წამი და ცენტი სჭირდება LTX-2.5 distilled i2v-ს სტანდარტულ `121 ფრეიმზე (5.04 წმ)` და მაქსიმალურ `185 ფრეიმზე (7.71 წმ)`?
  2. **Qwen-ის რესტაილი Blender-ის კადრებზე + `R3` (1.46x კროპის) ვარგისიანობა:** ინარჩუნებს თუ არა `Qwen-Image-2.1 + xworld_v2` ოთახის გეომეტრიასა და გმირების (`B_H1`, `B_H2`) იდენტობას 2 კუთხიდან (`room_two_shot` `30mm` vs `room_close_host` `50mm`), და უჭირავს თუ არა `room_two_shot`-ის `1.46x` კროპს (`R3` reuse) იგივე ხარისხი, რაც ცალკე დარენდერებულ `room_close_host`-ს?
  3. **უჭირავს თუ არა LTX-ს `7.71 წმ (185 ფრეიმი)` ერთ კადრად დრეიფის გარეშე**, თუ `visual_script/1`-მა კლიპები `<= 5.04 წმ (121 ფრეიმი)`-ზე უნდა გაყოს?

---

## 1. Executive Summary Report (Under 600 Words)

### What Was Done
Following Step E of [`ARGON_PROMPT.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/ARGON_PROMPT.md) and `OR-23` / `RP-07` in [`README.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/README.md), we designed—and **did not run**—the single cheapest paid test (**`p15_mini_cal`**) that settles the biggest operational and cost unknowns uncovered in Steps A–D.

### What Was Found & Key Numbers
- **Why `p15` (`$3.40–$3.50` cap) Was Over-Sized for Answering the Core Unknowns:**
  - In [`OPEN_QUESTIONS.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/OPEN_QUESTIONS.md) §A.1 & §B and [`HANDOFF_P1.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/HANDOFF_P1.md), the entire pipeline is blocked on two unmeasured facts: (1) nobody has seen a Qwen restyle of a pilot Blender still, and (2) [`config/job_speeds.json`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/config/job_speeds.json) has `rows: {}` (`measured: null`) for `ltx_clip_s_per_clip`, forcing RP-11 (`cloud/schedule.py`) to apply `margin_unmeasured = 2.0` and refuse `p16` (`$4.98 / 3.6 h` worst-case).
  - Instead of running 8 Qwen edits + two 185-frame LTX clips (`p15`), **`p15_mini_cal` runs exactly 2 Qwen restyles + 2 LTX clips (`121f` and `185f`)** on inputs already uploaded and sha256-verified on HuggingFace (`route_test_2026-11/pilot/blender/` and `route_test_2026-11/assets/B/`).
- **Exact Cost Numbers (`p15_mini_cal`):**
  - **Expected Cost:** **$0.43** on `A100 80GB community ($1.39/h, 18.7 min)` | **$0.56** on `A100 80GB secure ($1.79/h, 18.7 min)` | **$0.66** on `H100 NVL community ($2.59/h, 13.4 min)`.
  - **Worst-Case Cost (hard `30.0 min` timeout):** **$0.70** (`A100 community`) | **$0.90** (`A100 secure`) | **$1.30** (`H100 NVL`, enforced by `--max-usd 1.30 --max-hours 0.50`).
  - **Early-Exit Gate Cost:** If the 2 Qwen restyles fail the keyframe gate (identity drift or prop distortion), the pod stops **before loading LTX**, spending only **$0.18** (`A100`) to **$0.23** (`H100 NVL`)!

### What Could Not Be Verified
- Live RunPod GPU availability for `A100 80GB community` vs. `H100 NVL community` at the moment the creator approves the test (`OPEN_QUESTIONS.md` §A.1 noted `icw/19-pilot-pod` was retrying placement on A100 community).

### Questions for the Creator (4 Options Each)

1. **Q-E1: Approving the Paid Calibration Test Scope**
   - **Option A (Recommended — `p15_mini_cal`):** Run **2 Qwen restyles** (`room_two_shot` `30mm` + `room_close_host` `50mm`) + **2 LTX i2v clips** (`room_two_shot` at `121 frames [5.04 s]` and `185 frames [7.71 s]`) (**Expected: $0.43–$0.66 | Worst-case cap: $1.30**).
   - **Option B (`p15_qwen_only_mini`):** Run **only the 2 Qwen restyles** (`room_two_shot` + `room_close_host`) + free local `R3` crop test first, and stop before LTX (**Expected: $0.18–$0.23 | Worst-case cap: $0.40**).
   - **Option C (`p15_plus_battle`):** Add 1 battle restyle (`battle_f000_colour.png`) + 1 battle LTX clip (`121 frames`) to `p15_mini_cal` (= 3 Qwen edits + 3 LTX clips) to test J4 crowd restyling in the same pod (**Expected: $0.62–$0.95 | Worst-case cap: $1.80**).
   - **Option D (Full `p15` as originally drafted in PR #149):** Run all 8 Qwen edits + 2 LTX clips (`185 frames` each) (**Expected: $1.20–$1.85 | Worst-case cap: $3.50**).

2. **Q-E2: GPU Placement Policy for the Calibration Pod**
   - **Option A:** Try `A100 80GB community ($1.39/h)` for 10 minutes via `RP-10` placement watch (`D-118`), then automatically fall back to `A100 80GB secure ($1.79/h)` or `H100 NVL ($2.59/h)` (**Expected: $0.43–$0.66**).
   - **Option B:** Place immediately on `H100 NVL community ($2.59/h)` so the test finishes in **~13.4 minutes** without placement-queue waiting (**Expected: $0.66 | Worst-case: $1.30**).
   - **Option C:** Place only on `A100 80GB community ($1.39/h)` and wait indefinitely until an instance opens (**Expected: $0.43 | Risk: multi-hour queue delay**).
   - **Option D:** Do not launch any pod until `p15` placement watch finishes on branch `icw/19-pilot-pod` (**$0.00**).

---

## 2. Complete Specification of the Proposed Paid Test (`p15_mini_cal`)

### 2.1 The Exact Question(s) It Answers
1. **LTX-2.5 Speed & Cost Calibration (`config/job_speeds.json` `ltx_clip_s_per_clip`):** What is the exact measured `s/frame` and `$/second` of `Lightricks/LTX-2.5` distilled i2v at `1920x1088` on a standard `121-frame (5.04 s)` clip vs. a max-length `185-frame (7.71 s)` clip?
2. **Clip Length Stability (`121f` vs. `185f`):** Does an `8 s` (`185-frame`) single-scene LTX i2v clip hold character identity and room geometry, or does quality degrade after `~5 s` (`121 frames`)?
3. **Blender-to-Qwen Multi-Angle Consistency & `R3` Crop Validation:**
   - Do props and character identity hold across two camera angles of the same Blender room (`room_two_shot` `30mm` vs. `room_close_host` `50mm`)?
   - Does a `1.46x` crop from the restyled `room_two_shot` (`30mm`, upscaled via the free FFmpeg `lanczos + cas 0.4` chain to `2560x1440`) match the visual quality of the dedicated `room_close_host` (`50mm`) Qwen restyle—validating `R3` shared-render reuse in `explainer_engine/visual/reuse_plan.py`?

---

### 2.2 Exact Inputs (All Existing & SHA256-Pinned on HuggingFace — Zero New Setup Work)

| Input # | HF Path (`vano1919/tmr-artifacts`) | Role in `p15_mini_cal` | Source Reference |
|---|---|---|---|
| **1** | `route_test_2026-11/pilot/blender/room_two_shot.png` | Image 1 for Qwen Edit 1 (`30mm` two-shot of host `H1` + guest `H2` at table) | [`PILOT_1MIN_PLAN_v3.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/PILOT_1MIN_PLAN_v3.md) |
| **2** | `route_test_2026-11/pilot/blender/room_close_host.png` | Image 1 for Qwen Edit 2 (`50mm` close shot of host `H1` at table) | [`PILOT_1MIN_PLAN_v3.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/PILOT_1MIN_PLAN_v3.md) |
| **3** | `route_test_2026-11/assets/B/B_H1_front.png` | Hero identity reference (`H1` commander) for Edit 1 and Edit 2 | [`MATERIAL.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/MATERIAL.md) (`assets_B_hero_sheets`) |
| **4** | `route_test_2026-11/assets/B/B_H2_front.png` | Hero identity reference (`H2` scout) for Edit 1 | [`MATERIAL.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/MATERIAL.md) (`assets_B_hero_sheets`) |
| **5** | `Qwen-Image-2.1` + `xworld_v2` ck3000 (`sha256: f5c420a1...`, `w=0.7`) | `true_cfg=2.5`, `30 steps`, `seed=11`, `1280x720` cover-cropped to `1920x1088` | [`LTX_HELPERS.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/LTX_HELPERS.md) §2 |
| **6** | `Lightricks/LTX-2.5` @ `49b093a3` (`ltx_pipelines.distilled` @ `e98f6d9`) | Clip 1: `121 frames (5.04 s)`; Clip 2: `185 frames (7.71 s)`; `1920x1088`, `24 fps`, `seed=42` | [`PILOT_1MIN_PLAN_v3.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/PILOT_1MIN_PLAN_v3.md) §Stage 3 |

---

### 2.3 GPU Selection, Exact Expected Cost, and Worst-Case Cost Table

| Stage / Metric | `A100 80GB Community` (`$1.39 / h`) | `A100 80GB Secure` (`$1.79 / h`) | `H100 NVL Community` (`$2.59 / h`) |
|---|---:|---:|---:|
| **1. Container Boot & Weight Load** | `240.0 s` (`$0.0927`) | `240.0 s` (`$0.1193`) | `180.0 s` (`$0.1295`) |
| **2. Qwen Model Load + 2 Restyle Edits** | `103.7 s + 2 * 61.2 s = 226.1 s` (`$0.0873`) | `226.1 s` (`$0.1124`) | `61.0 s + 2 * 36.0 s = 133.0 s` (`$0.0957`) |
| **3. Early-Exit Cost (if Qwen Gate Fails)** | **`$0.1800` (`7.77 min`)** | **`$0.2317` (`7.77 min`)** | **`$0.2252` (`5.22 min`)** |
| **4. LTX Clip 1 (`121 frames = 5.04 s` @ `1920x1088`)** | `242.0 s` (`$0.0934`) | `242.0 s` (`$0.1203`) | `227.6 s` (`$0.1637`) |
| **5. LTX Clip 2 (`185 frames = 7.71 s` @ `1920x1088`)** | `370.0 s` (`$0.1429`) | `370.0 s` (`$0.1840`) | `348.0 s` (`$0.2504`) |
| **6. Sidecar & Artifact Upload (`speeds.json`, MP4s)** | `45.0 s` (`$0.0174`) | `45.0 s` (`$0.0224`) | `30.0 s` (`$0.0216`) |
| **Expected Total Wall-Clock & USD** | **`18.72 min` -> `$0.4337`** | **`18.72 min` -> `$0.5585`** | **`15.31 min` -> `$0.6609`** |
| **Worst-Case Cap (`--max-hours 0.50`, `30.0 min` hard kill)** | **`30.00 min` -> `$0.6950`** | **`30.00 min` -> `$0.8950`** | **`30.00 min` -> `$1.2950`** |
| **Remaining RunPod Balance (from `$7.99` current)** | `$7.56` expected / `$7.29` worst | `$7.43` expected / `$7.09` worst | `$7.33` expected / `$6.69` worst |

---

### 2.4 Explicit Stop Conditions (`CLOUD_RUNBOOK.md` Three-Path Enforcement)

1. **Gate 1 — Post-Qwen Keyframe Gate (at `~5–8 min`, `$0.18–$0.23` spent):**
   - Immediately after generating `room_two_shot_qwen.png` and `room_close_host_qwen.png`, upload both PNGs to HF and run `qa/keyframe_gate.py` + CLIP cosine check against `B_H1_front.png`.
   - **Stop Condition:** If either PNG fails to write, has CLIP cosine `< 0.75`, or exhibits severe distortion, upload `stages.json` (`status: "STOPPED_AT_QWEN_GATE"`) and **terminate the pod immediately without loading LTX**.
2. **Gate 2 — Post-Clip-1 Speed & Timeout Gate (at `~10–12 min`, `$0.29–$0.41` spent):**
   - Run Clip 1 (`121 frames`) with a per-command timeout of `600 s` (`10 min`). Write its exact wall-clock seconds to `speeds.json` and upload `room_two_shot_121f.mp4` + `speeds.json` to HF immediately.
   - **Stop Condition:** If Clip 1 takes `> 600 s` or raises a CUDA OOM / runtime error, skip Clip 2 (`185 frames`) and terminate the pod immediately—preserving the `121-frame` speed measurement and both Qwen PNGs.
3. **Gate 3 — Hard Pod Wrapper & External Watchdog (`30.0 min` / `$1.30` ceiling):**
   - In-pod `pod_wrapper.sh` enforces `timeout 1800` (`30 min`) with `trap 'runpodctl remove pod $RUNPOD_POD_ID' EXIT`.
   - External `cloud/watchdog.py` polls every 60 seconds and kills the pod if elapsed time reaches `30.0 min` or accrued cost reaches `$1.30`.
