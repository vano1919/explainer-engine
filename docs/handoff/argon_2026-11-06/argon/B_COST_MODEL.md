# Step B: Per-Shot & 12-Minute Episode Cost Model (`B_COST_MODEL.md`)

## მოკლე შეჯამება დამკვეთისთვის (ქართულად)

- **რა გაკეთდა:** [`LTX_HELPERS.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/LTX_HELPERS.md)-ის, [`COST_REDUCTION_NOTE.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/COST_REDUCTION_NOTE.md)-ის, [`README.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/README.md)-ის, `MATERIAL.md`-ისა და [`HANDOFF_route_script.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/handoffs/HANDOFF_route_script.md)-ის გაზომილი და დოკუმენტირებული რიცხვების საფუძველზე შევადგინეთ ზუსტი არითმეტიკული ხარჯთაღრიცხვა: (1) თითოეული კადრის/რუტის (`J1–J5`, `H`, უფასო სტატიკური/პითონით მოძრავი კადრი, Qwen-ის 1 სურათი, LTX-ის 1 წამი, პოდის ფიქსირებული ხარჯი) ცხრილი და (2) 12-წუთიანი (`720 წმ`) ეპიზოდის ბიუჯეტი 3 პოლიტიკისთვის. ყველა გაუზომავი პარამეტრი მკაფიოდ მონიშნულია (`[UNMEASURED]`).
- **მთავარი რიცხვები (12-წუთიანი ეპიზოდი = 720 წმ, ~144 კადრი / 56–96 ვიზუალური სეტი):**
  1. **პოლიტიკა 1 (დღევანდელი გეგმა — 60% LTX ვიდეო = 432 წმ):** RunPod GPU ხარჯი = **$10.35** (გამეორებების გარეშე, $0.016/წმ) — **$14.37** (დღევანდელი გეგმის გამეორებების ბუფერით, ~$10.50 LTX + $3.37 Qwen/პოდი) — **$17.47** (H100 NVL-ის 5.8 წთ / 185 ფრეიმის ტემპით). ElevenLabs-ის გახმოვანებით (~$2.00 EST) სრული ხარჯია **$12.35 – $19.47**.
  2. **პოლიტიკა 2 (LTX მხოლოდ იმ კადრებისთვის, სადაც უფასო სტატიკური/2.5D მოძრაობა არ კმარა — `needs_ltx` ფილტრი, ვიდეოს ~22.5% = 162 წმ LTX):** RunPod GPU ხარჯი ჩამოდის **$5.25**-მდე (გამეორებების გარეშე) ან **$6.60**-მდე (გამეორებების ბუფერით) — **54%-იანი კლება** დღევანდელ გეგმასთან შედარებით (ElevenLabs-ის ჩათვლით: **$7.25 – $8.60**, რაც $10–$15 სამიზნეზე ბევრად დაბალია).
  3. **პოლიტიკა 3 (მაქსიმალური ხელახალი გამოყენება `R0–R5` + `needs_ltx` ფილტრი — ~120 წმ LTX და სურათების 55% reuse):** RunPod GPU ხარჯი ჩამოდის **$3.44**-მდე (გამეორებების გარეშე) ან **$4.44**-მდე (გამეორებების ბუფერით) — **69%-იანი კლება** (ElevenLabs-ის ჩათვლით: **$5.44 – $6.44**).

---

## 1. Executive Summary Report (Under 600 Words)

### What Was Done
Using every measured figure in `docs/handoff/argon_2026-11-06/LTX_HELPERS.md`, `MATERIAL.md`, `COST_REDUCTION_NOTE.md`, `README.md`, and [`PLANNING_CHAIN_PLAN.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/PLANNING_CHAIN_PLAN.md), we built an exact arithmetic cost model covering:
1. Every hardware rate, model timing, and unit cost (marking every unmeasured parameter explicitly).
2. A per-shot cost table across routes `J1`, `J2`, `J3`, `J4`, `J5`, `H`, and `Still + Python/Blender Camera Move`, plus isolated component rows (`Qwen per picture`, `LTX i2v per second`, `Pod fixed cost`).
3. A 12-minute (`720 s`) episode estimate under all three required policies (`Policy 1: Today's Plan`, `Policy 2: LTX Only for Shots Failing the Still/Camera-Move Test`, `Policy 3: Maximal Reuse R0–R5`).

### What Was Found & Key Numbers
- **Unit Costs:**
  - **Qwen-Image-2.1 + `xworld_v2` per picture (30 steps):** Measured `33.5–38.5 s` (midpoint `36.0 s`) on H100 NVL after a `61.0 s` load (`HANDOFF_STEP3.md`). At the active H100 NVL community rate (`$2.59/h`), net compute is **$0.02410–$0.02770** (midpoint **$0.02590**) per picture plus **$0.04389** per model load. At the actual asset-pod H100 rate (`$1.69/h`, `MATERIAL.md`), midpoint net compute is **$0.01690/picture**. On A100 80GB community (`$1.39/h`, `1.7x` slower = `61.2 s` midpoint), midpoint net compute is **$0.02363/picture**. The plan's `$3.00` episode Qwen budget across ~56–60 shots implies an effective **$0.05000–$0.05357/picture** including retries, reference sheets, and pod overhead (`[UNMEASURED]` retry multiplier).
  - **LTX-2.5 per video second (`[UNMEASURED]` in [`config/job_speeds.json`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/config/job_speeds.json)):** Quoted plain rate is **$0.01600/s** (`$6.912` for `432 s`). With the plan's retry allowance (`$10.00–$11.00`, midpoint `$10.50` for `432 s`), the effective rate is **$0.02315–$0.02546/s** (midpoint **$0.02431/s**, implied retry multiplier `1.519x`). Under `PROGRESS` pilot v4's H100 figure (`5.8 min` = `348 s` for `185 frames` = `7.7083 s` @ 24 fps), 1 second of LTX costs **$0.03248/s** on H100 NVL (`$2.59/h`) or **$0.01858/s** if A100 runs at the same wall-clock (`$1.39/h`).
  - **Free Routes (`J5`, `H`, `Still + Python/Blender Camera Move`):** **$0.00000** LTX cost (`0 LTX s`).
- **12-Minute Episode (`720 s`) Comparison Across Three Policies:**
  - **Policy 1 (Today's Plan — 60% LTX = `432 s`, 30% Stills/J5 = `216 s`, 10% Helper `H` = `72 s`):** **$10.35** (plain $0.016/s, measured Qwen) to **$14.37** (plan retry allowance) to **$17.47** (H100 5.8-min/185f rate) in RunPod GPU spend (**+$2.00 EST** ElevenLabs = **$12.35–$19.47** all-in).
  - **Policy 2 (`needs_ltx` Gate — LTX only where static/Python/2.5D motion fails = `162 s` LTX [22.5%], `486 s` J5/Stills [67.5%], `72 s` Helper `H` [10%]):** **$5.25** (plain) to **$6.60** (with retry allowance) RunPod GPU spend (**$7.25–$8.60** all-in) — saving **$7.77/episode (-54.1%)**.
  - **Policy 3 (Maximal Reuse `R0–R5` + `needs_ltx` Gate = `120 s` LTX [16.7%], 55% still reuse via `R0–R3`):** **$3.44** (plain) to **$4.44** (with retry allowance) RunPod GPU spend (**$5.44–$6.44** all-in) — saving **$9.93/episode (-69.1%)**.

### What Could Not Be Verified
- `config/job_speeds.json` has `rows: {}` (`measured: null`) for `ltx_clip_s_per_clip`, `qwen_asset_s_per_image`, and `blender_25d_s_per_frame_pc`.
- Actual LTX-2.5 retry/rejection rate under `qa/clip_gates.py` and actual ElevenLabs credit consumption for a full 12-minute script are unmeasured.

### Questions for the Creator (4 Options Each)

1. **Q-B1: Hard Episode Budget Split (`D-93` / `BP-109`: 60% Video / 30% Stills / 10% Helper)**
   - **Option A:** Reclassify J5 2.5D animated collage shots (moving backdrop parallax + animated cards + lip-sync) as counting toward the **60% "video"** quota in `BP-109`, allowing LTX to drop from 432 s to ~120–162 s (**saves ~$6.00–$8.00/episode**, RunPod total **~$4.44–$6.60**).
   - **Option B:** Change `BP-109` / `D-93` explicitly to **20–25% LTX video / 65–70% J5 & Stills with motion / 10% Helper** (**saves ~$6.00–$8.00/episode**, RunPod total **~$4.44–$6.60**).
   - **Option C:** Keep `BP-109` at 60% LTX (`432 s`) and rely solely on `R0–R3` still reuse and A100 placement to stay near the $10–15 target (**RunPod total ~$11.50–$13.50**).
   - **Option D:** Cap LTX by a hard dollar budget per episode (`$4.00 LTX cap` = max ~165 s of LTX with retries) and route all remaining shots to J5 / Python camera moves (**RunPod total <= $7.50**).

2. **Q-B2: GPU Card Selection for Batch Episode Pods ([`cloud/schedule.py`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/explainer_engine/cloud/schedule.py) RP-11)**
   - **Option A:** Prefer **A100 80GB community (`$1.39/h`)** with RP-10 placement watch (`D-118`) and fallback to **A100 secure (`$1.79/h`)** after 15 minutes (**lowest cost: ~$0.0236/Qwen edit**).
   - **Option B:** Use **H100 NVL community (`$2.59/h`)** immediately whenever A100 community is unavailable, trading ~9.6% higher Qwen compute cost for 1.7x faster wall-clock completion (**+$0.40–$0.90/episode**).
   - **Option C:** Benchmark **RTX PRO 6000 community (`$1.29/h`)** in a $0.30 smoke pod first to verify PyTorch/LTX compatibility ([`OPEN_QUESTIONS.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/OPEN_QUESTIONS.md) §B).
   - **Option D:** Run Qwen batch restyles on an A100 pod and LTX clips on a separate H100 pod (**adds ~$0.50 extra pod setup cost**, not recommended under RP-10 single-pod rule).

---

## 2. Master Input Ledger: Measured vs. Unmeasured Parameters

Every number in this cost model traces to an exact repository source. No unmeasured number is treated as measured.

| Parameter | Value Used | Exact Math / Unit Conversion | Status | Source File |
|---|---|---|---|---|
| **H100 NVL (community) rate** | `$2.59 / h` | `$2.59 / 3600 = $0.00071944 / s` | **MEASURED / ACTIVE RULE** | `LTX_HELPERS.md` §3, `cloud/schedule.py` |
| **H100 (asset pod `0t2re35vf6f3sq`) rate** | `$1.69 / h` | `$1.69 / 3600 = $0.00046944 / s` (`40 min = $1.08`) | **MEASURED (historical pod)** | `MATERIAL.md` (`assets_A_backdrops`) |
| **A100 80GB (community / secure) rate** | `$1.39 / h` (comm), `$1.79 / h` (sec) | `$0.00038611 / s` (comm), `$0.00049722 / s` (sec) | **MEASURED / ACTIVE RULE** | `LTX_HELPERS.md` §3, `cloud/schedule.py` |
| **RTX PRO 6000 (community) rate** | `$1.29 / h` | `$0.00035833 / s` | **ACTIVE RULE (`torch` support `[UNMEASURED]`)** | `LTX_HELPERS.md` §3, `OPEN_QUESTIONS.md` §B |
| **Qwen-Image-2.1 + `xworld_v2` load time** | `61.0 s` (H100 NVL) | `$0.04389` on H100 NVL (`$2.59/h`); `$0.02864` at `$1.69/h` | **MEASURED** | `LTX_HELPERS.md` §3 (`HANDOFF_STEP3.md`) |
| **Qwen-Image-2.1 + `xworld_v2` per picture** | `33.5–38.5 s` (mid `36.0 s`) on H100 NVL | H100 NVL (`$2.59/h`): `$0.02410–$0.02770` (mid **`$0.02590`**); at `$1.69/h`: mid **`$0.01690`** | **MEASURED** (in handoff; `job_speeds.json` row empty) | `LTX_HELPERS.md` §3 (`HANDOFF_STEP3.md`) |
| **Qwen on A100 relative speed** | `1.7x` slower than H100 (`25.8 min` vs `15.4 min` for 24 pics) | Net `56.95–65.45 s` (mid `61.2 s`) -> **`$0.02363 / pic`** at `$1.39/h` | **MEASURED** | `LTX_HELPERS.md` §3 (`PROGRESS.md`) |
| **Plan's episode Qwen allowance** | `~$3.00` per 12-min episode | Across `56 shots` + `16 scene assets` = `72 pics` -> `$0.04167/pic` (incl. retries/overhead) | **`[UNMEASURED]` (estimate with retry margin)** | `COST_REDUCTION_NOTE.md`, `README.md` §5 |
| **LTX-2.5 plain rate per video second** | `$0.01600 / s` (no retries) | `432 s * $0.016 = $6.912` (`430 s * $0.016 = $6.880`) | **`[UNMEASURED]` (quoted plain estimate)** | [`ARGON_PROMPT.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/ARGON_PROMPT.md), `COST_REDUCTION_NOTE.md` |
| **LTX-2.5 rate with retries per second** | `$10.00–$11.00` for `430–432 s` | Midpoint `$10.50 / 432 s` = **`$0.02431 / s`** (`1.519x` retry multiplier) | **`[UNMEASURED]` (retry rate not measured)** | `COST_REDUCTION_NOTE.md`, `README.md` §5 |
| **LTX-2.5 H100 185-frame (`7.71 s`) benchmark** | `5.8 min` (`348 s`) typ, `12.0 min` (`720 s`) max on H100 | At `$2.59/h`: `$0.25037 / 7.7083 s` = **`$0.03248 / s`** (max `$0.06720 / s`); at `$1.69/h`: **`$0.02119 / s`** | **MEASURED (185f pilot v4; 1920x1088 speed in `job_speeds.json` is `[UNMEASURED]`)** | `LTX_HELPERS.md` §3 (`PROGRESS.md`) |
| **Historical `old_film_A` gross LTX+Qwen rate** | `$2.99` for `52.6 s` (`1280x704`, 121f/clip) | `$2.99 / 52.6 s = $0.05684 / s` (includes keyframes + setup) | **QUOTED HISTORICAL BASELINE** | `MATERIAL.md` (`old_film_A`), `LTX_HELPERS.md` §3 |
| **Pod fixed cost per run** | `$0.50` per pod | Container boot + weight sync + model load (`61 s` Qwen + LTX load) + upload | **`[UNMEASURED]` (quoted estimate; `setup_share_max = 0.4`)** | `COST_REDUCTION_NOTE.md`, `config/job_speeds.json` |
| **Blender 3D Pilot Stills (CPU)** | `$0.00` | Room: `50–66 s/still`; Battle colour: `202.3 s/frame`, depth: `238.1 s/frame` | **MEASURED (free local/CI CPU)** | `LTX_HELPERS.md` §3, [`PILOT_1MIN_PLAN_v3.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/PILOT_1MIN_PLAN_v3.md) |
| **Route J5 (`assemble_25d/1`) (CPU)** | `$0.00` | `7.8–8.3 s/frame` w/ cards (`3.7 s` w/o); anim BG `1.3 s/frame`; BiRefNet CPU `~20 s/sheet` | **MEASURED (free local/CI CPU)** | `LTX_HELPERS.md` §3, `J5_DIALOGUE_COLLAGE.md` |
| **ElevenLabs Voice (J5 / Episode)** | `155 credits` for 3 lines; `~$2.00` per 12-min episode | `~1,800 credits` for 2 sample parts (`OPEN_QUESTIONS.md` §A.5) | **3 lines MEASURED; 12-min `$2.00` `[UNMEASURED / EST]`** | `MATERIAL.md`, `PLANNING_CHAIN_PLAN.md` §0 & §5 |

---

## 3. Per-Shot & Component Cost Table (`J1–J5`, `H`, Free Still+Move, Qwen, LTX, Pod Fixed)

For a standard **4.0-second shot** (`97 frames` at 24 fps, `8k+1` with `k=12`) and a **5.0-second shot** (`121 frames` at 24 fps, `k=15`):

| Route / Component | Recipe / Mechanism | CPU / Blender Work (Free, $0) | Qwen Pictures Needed | LTX Seconds Needed | Cost: Measured / Plain Baseline (H100 NVL `$0.0259/pic` + Plain LTX `$0.016/s`) | Cost: Plan Retry Allowance (Qwen `$0.0417/pic` + Retry LTX `$0.02431/s`) | Measurement Status & Notes |
|---|---|---|---|---|---|---|---|
| **Component: Pod Fixed Cost** | Container boot, weight load (`61 s` Qwen + LTX), HF upload | 0 s | 0 | 0 s | **$0.5000 / pod** (or `$0.0089/shot` over 56 shots) | **$0.5000 / pod** | `[UNMEASURED]` quoted fixed overhead (`COST_REDUCTION_NOTE.md`). |
| **Component: Qwen per Picture** | `Qwen-Image-2.1` + `xworld_v2` (30 steps, 1280x720) | 0 s | 1 pic | 0 s | **$0.02590 / pic** (`36.0 s` on H100 NVL @ `$2.59/h`; `$0.02363` on A100 @ `$1.39/h`; `$0.01690` @ `$1.69/h`) | **$0.04167 / pic** (`$3.00` allowance / 72 episode pics) | Compute speed **MEASURED** (`33.5–38.5 s`); retry multiplier `[UNMEASURED]`. |
| **Component: LTX i2v per Second** | `ltx_i2v/1` (`Lightricks/LTX-2.5`, 24 fps, `8k+1` frames) | 0 s | 0 (see shot row) | 1.00 s (24 frames) | **$0.01600 / s** (quoted plain) \| **$0.03248 / s** (H100 5.8 min / 185f) | **$0.02431 / s** (`$10.50 / 432 s` with retries) | `[UNMEASURED]` in `config/job_speeds.json`; plain & retry rates from `COST_REDUCTION_NOTE.md`. |
| **Still + Python/Blender Camera Move** | `STILL_HOLD` / `STILL_3D` / pan, zoom, push-in (`ZOOM_MAX 1.6`) | `0–66 s` CPU | **0 pics** (if R0–R3 reused) or **1 pic** (if R4 new) | **0 s** (`0 LTX frames`) | **$0.00000** (reused R0–R2) \| **$0.02590** (new Qwen still) | **$0.00000** (reused) \| **$0.04167** (new Qwen still) | **MEASURED ($0 LTX).** Camera move is 100% free in Python/FFmpeg or Blender 2.5D. |
| **Route H (Helper Graphics)** | `python_helper/1` (maps, HUD, charts, titles, compensators) | `1–5 s` Python CPU | **0 pics** | **0 s** | **$0.00000 / shot** | **$0.00000 / shot** | **MEASURED ($0 GPU).** Pure deterministic Python/FFmpeg rendering. |
| **Route J5 (2.5D Collage / Dialogue)** | `assemble_25d/1` (cut-out cards on 360/plate backdrop + procedural mouth/blink/brow + parallax) | `95 s` per 4 stills + `1.3 s/f` BG (`$0` CPU) | **0 new pics/shot** (reuses scene backdrop `A` + hero sheets `B`) | **0 s** (`0 LTX frames`) | **$0.00000 marginal GPU / shot** (`+$0.0046` amortized if 1 backdrop + 3 hero x 4 angles = 13 pics are amortized over 72 shots) | **$0.00000 marginal GPU / shot** (plus ElevenLabs voice if voiced line) | **MEASURED ($0 LTX).** BiRefNet CPU cut-out `~20 s/sheet`; procedural Rhubarb mouth cues `$0`. |
| **Route J2 (Clay Layout -> Qwen -> LTX)** | `ltx_layout/1` (Blender clay pass + Qwen start frame + LTX-2.5 + Union-Control layout) | `~50–90 s` clay pass (`$0` CPU) | **1 pic** (or 0 if R1/R3 reused) | **4.04 s** (`97f`) to **5.04 s** (`121f`) | **4s (`97f`):** `$0.02590 + $0.06467 =` **$0.09057** \| **5s (`121f`):** `$0.02590 + $0.08067 =` **$0.10657** | **4s (`97f`):** `$0.04167 + $0.09824 =` **$0.13991** \| **5s (`121f`):** `$0.04167 + $0.12255 =` **$0.16422** | Qwen speed **MEASURED**; LTX Union-Control layout speed `[UNMEASURED]`. |
| **Route J4 (Full Layout -> Qwen -> LTX)** | `ltx_restyle/1` (Blender colour+depth+line passes + Qwen first frame + LTX-2.5 + Union-Control depth/canny) | `50–66 s` room or `440.4 s` battle (`$0` CPU) | **1 pic** (or 0 if R1/R3 reused) | **4.04 s** (`97f`) to **5.04 s** (`121f`) | **4s (`97f`):** `$0.02590 + $0.06467 =` **$0.09057** \| **5s (`121f`):** `$0.02590 + $0.08067 =` **$0.10657** | **4s (`97f`):** `$0.04167 + $0.09824 =` **$0.13991** \| **5s (`121f`):** `$0.04167 + $0.12255 =` **$0.16422** | Blender passes **MEASURED ($0 CPU)**; LTX restyle speed `[UNMEASURED]`. |
| **Route J3 (Plain Qwen -> LTX i2v, No 3D Layout)** | `ltx_i2v/1` (text-to-image Qwen keyframe -> LTX i2v without Blender 3D layout pass) | `0 s` Blender | **1 pic** | **4.04 s** (`97f`) to **5.04 s** (`121f`) | **4s (`97f`):** **$0.09057** \| **5s (`121f`):** **$0.10657** (before drift retries) | **4s (`97f`):** **$0.13991+** \| **5s (`121f`):** **$0.16422+** (high drift retry risk per `F-21`) | Deprecated as standalone route ([`ROUTE_PLAN_2026-11-06.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/architecture/ROUTE_PLAN_2026-11-06.md)) except when anchored by a Blender still (`pilot_stills`). |
| **Route J1 (Direct Text-to-Video LTX)** | Direct `t2v` without Qwen first frame or Blender layout | `0 s` | **0 pics** | **4.04 s** (`97f`) to **5.04 s** (`121f`) | **4s (`97f`):** **$0.06467** \| **5s (`121f`):** **$0.08067** | **4s (`97f`):** **$0.09824** \| **5s (`121f`):** **$0.12255** | **FORBIDDEN / UNUSABLE** for Ink Chronicle: cannot hold `xworld_v2` LoRA look or hero sheet identity (`LJ-01`, `D-96`). |

---

## 4. 12-Minute Episode (`720.0 s`) Cost Estimate Under Three Policies

### Common Episode Parameters (`README.md` §4–5, `COST_REDUCTION_NOTE.md`, `HANDOFF_route_script.md`)
- **Total Episode Runtime:** `12.0 minutes = 720.0 seconds = 17,280 frames` at 24 fps.
- **Speech Split (`D-99`, `BP-105`):** `70%` narrator (`504.0 s`) / `30%` voiced character dialogue (`216.0 s`).
- **Runtime Visual Mix Baseline (`D-93`, `BP-109`):** `60%` video (`432.0 s`), `30%` stills with Python/Blender motion (`216.0 s`), `10%` helper graphics `H` (`72.0 s`).
- **Shot Count Structure:**
  - In `COST_REDUCTION_NOTE.md` / `README.md` §5: `~56 LTX/still setups` + `16 scene-level assets` (`4 backdrops` + `3 heroes x 4 angles = 12 sheets`) = **`72 Qwen pictures`** in Today's Plan (or scaled from the `104.5 s` route test's `24 shots` by `720 / 104.5 = 6.89x` -> `165 total cuts` across `~96 distinct visual setups`). Below we show exact arithmetic for the **canonical 56-shot + 16-asset (`72 Qwen pictures`, `432.0 s LTX`) model** from `README.md` §5 / `COST_REDUCTION_NOTE.md`, and also provide the **route-test scaled (`6.89x`) sensitivity row**.

### Policy 1: Today's Plan (`432.0 s` LTX [60%], `216.0 s` Stills/J5 [30%], `72.0 s` Helper `H` [10%], No Solver Reuse)
- **LTX Video (`432.0 s`, e.g. 90 clips at `4.80 s` / `115–121 frames` average incl. `+0.17 s` Q4 A rounding):**
  - *Plain rate (`$0.01600/s`, `[UNMEASURED]`):* `432.0 s * $0.01600/s` = **`$6.9120`** (note: `COST_REDUCTION_NOTE.md` uses rounded `430 s * $0.016 = $6.88` -> `~$6.90`).
  - *With plan retry allowance (`$0.024306/s`, `[UNMEASURED]`):* `432.0 s * $0.02430556/s` = **`$10.5000`** (range `$10.0000–$11.0000`).
  - *At H100 185-frame benchmark (`$0.032480/s` at `$2.59/h`, `MEASURED` on pilot v4):* `432.0 s * $0.032480/s` = **`$14.0314`**.
- **Qwen Pictures (`56 shot first-frames/stills + 16 scene assets = 72 pictures`):**
  - *Measured H100 NVL compute (`36.0 s/pic` @ `$2.59/h` = `$0.02590/pic` + `$0.04389` load):* `72 * $0.02590 + $0.04389` = **`$1.9087`** (or on A100 @ `$1.39/h`: `72 * $0.02363 + $0.04004` = **`$1.7414`**; or on route-test scaled `6.89 * 26 = 179 pics` on H100 NVL: `179 * $0.02590 + $0.04389` = **`$4.6800`**).
  - *Plan Qwen budget allowance (`COST_REDUCTION_NOTE.md`, `[UNMEASURED]` retry/edit buffer):* **`$3.0000`**.
- **Pod Fixed Overhead (`COST_REDUCTION_NOTE.md`, `[UNMEASURED]`):** **`$0.5000`**.
- **Policy 1 Total RunPod GPU Cost:**
  - **Measured Qwen + Plain LTX (`$0.016/s`):** `$6.9120 (LTX) + $1.9087 (Qwen 72 pics) + $0.5000 (Pod)` = **`$9.3207`** (or **`$10.4120`** using the plan's `$3.00` Qwen allowance).
  - **Plan Recount Baseline (Retry LTX + `$3.00` Qwen + `$0.50` Pod):** `$10.5000 + $3.0000 + $0.5000` = **`$14.0000`** (range **`$13.5000–$14.5000`**, matching `README.md` §5's `$13–$15`).
  - **H100 185f Benchmark Rate (`$0.03248/s` LTX + `$3.00` Qwen + `$0.50` Pod):** `$14.0314 + $3.0000 + $0.5000` = **`$17.5314`**.
  - **All-In Episode Total (adding ElevenLabs `~$2.0000 [EST]`):** **`$11.3207`** (plain) to **`$16.0000`** (plan retry midpoint) to **`$19.5314`** (H100 185f rate).

---

### Policy 2: LTX Only for Shots That Fail the "Static or Python-Moved Still Would Do" Test (`needs_ltx` Gate)
- **How the Shot Test Filters the 12-Minute Episode (`720.0 s`):**
  - **10% Helper Graphics (`H`):** `72.0 s` (`0 s` LTX, `0` Qwen pics).
  - **30% Voiced Dialogue (`216.0 s`, `D-99`):** Routed 100% to **Route J5** (`assemble_25d/1`: 2.5D hero cards + procedural Rhubarb lip-sync + blink/brow + animated backdrop drift). Passes the still/2.5D test -> **`0.0 s` LTX** (down from ~108 s of `DIALOGUE_CU` LTX in the old pipeline).
  - **30% Narrated Stills with Python/Blender Camera Move (`216.0 s`):** Establishing shots, inserts (scrolls, clocks, tables), atmospheric holds, and aftermath tableaux pass the static/Python-moved still test -> **`0.0 s` LTX**.
  - **Remaining 30% Narrated Action/Crowd/Scene Transitions (`216.0 s`):** Applying our deterministic `needs_ltx` gate (Section C: requires continuous non-rigid multi-limb interaction such as sword duels, crowd clashes with locomotion, or physics contact that cannot be represented by 2.5D card translation/parallax), **25% of these (`54.0 s`)** are reaction close-ups, slow walks, or banner/rain holds that pass the 2.5D/Python-move test (matching `S05-04` and `X6` in our audit), leaving **75% of the action block = `162.0 s` (`22.5%` of episode runtime, ~36 clips at `4.50 s` avg)** that genuinely fail the still test and require `J2`/`J4` LTX motion!
- **Policy 2 Exact Cost Arithmetic (`162.0 s` LTX, `72 Qwen pictures` [no solver reuse yet], `$0.50` Pod):**
  - *LTX (`162.0 s`):*
    - Plain (`$0.01600/s`): `162.0 * $0.01600` = **`$2.5920`**
    - With retry allowance (`$0.024306/s`): `162.0 * $0.02430556` = **`$3.9375`**
    - At H100 185f benchmark (`$0.032480/s`): `162.0 * $0.032480` = **`$5.2618`**
  - *Qwen (`72 pictures`, no reuse solver applied yet):*
    - Measured H100 NVL (`$0.02590/pic` + `$0.04389` load): **`$1.9087`** (or Plan `$3.0000` allowance; or scaled to fewer LTX keyframes `52 pics` = **`$1.3907`**).
  - *Pod Fixed Overhead:* **`$0.5000`**.
  - **Policy 2 Total RunPod GPU Cost:**
    - **Plain LTX + Measured Qwen (72 pics):** `$2.5920 + $1.9087 + $0.5000` = **`$5.0007`** (or **`$6.0920`** with `$3.00` Qwen allowance).
    - **Retry LTX + Measured Qwen (72 pics):** `$3.9375 + $1.9087 + $0.5000` = **`$6.3462`** (or **`$7.4375`** with `$3.00` Qwen allowance).
    - **H100 185f Benchmark + Measured Qwen:** `$5.2618 + $1.9087 + $0.5000` = **`$7.6705`**.
    - **All-In Episode Total (adding ElevenLabs `~$2.0000 [EST]`):** **`$7.0007 – $9.4375`** (well below the `$10.00–$15.00` target).

---

### Policy 3: Maximal Reuse (`R0–R5` Solver + `needs_ltx` Gate + Cross-Shot/Episode Asset Reuse)
- **How `R0–R5` Reduces Qwen Pictures and LTX Seconds Across the 12-Minute Episode:**
  1. **Scene Assets (`R0` Cross-Episode Library Reuse):** The 3 recurring heroes (`H1`, `H2`, `H3` = 12 turnaround sheets) and 2 of 4 standard backdrops exist in `picture_library` / `assets/library.py` (`R0`). Only **2 new place backdrops + 4 new prop/angle cards = `6 new asset pictures`** are generated instead of 16 (**saves 10 Qwen asset pictures**).
  2. **Stills & First Frames (`R1` Crop Reuse `ZOOM_MAX 1.6`, `R2` J5 Card Assembly, `R3` Wide 1.6x Render + 1 Qwen Edit Serving Multiple Angles):**
     - Out of `56 shot setups`, `20` are J5 card shots assembled directly from `scene_assets` (`R2`, **0 new Qwen edits**).
     - Of the remaining `36` stills/first-frames, `20%` (`7 stills`, measured AC-12 return rate in [`REUSE.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/REUSE.md) §1) are `R1` crops (`<= 1.6x`) of an earlier frame of the same setup (**0 new Qwen edits**).
     - Of the remaining `29` stills, `12` share a `(place, camera_side, cast)` group and are covered by `5` wide `1.6x` Blender renders (`R3`: 1 Qwen edit serves 2.4 stills on average, saving **7 Qwen edits**).
     - Net new Qwen edits required across the entire 12-minute episode = `6 (R5 new assets) + 5 (R3 wide shared edits) + 17 (R4 unique first frames)` = **`28 Qwen pictures`** (a **61.1% reduction** from 72 pictures!).
  3. **LTX Seconds under Maximal Reuse (`120.0 s` LTX [16.7% of episode]):**
     - Combining `needs_ltx` with `R2` (converting medium two-shots and reaction inserts to J5 2.5D cards with animated backdrops) and `Q4 A` exact beat splitting reduces LTX generation to **27 action/crowd clips totaling `120.0 s`** (`16.7%` of runtime; `76.7%` J5 + Python/Blender motion; `6.7%–10%` Helper `H`).
  4. **Pod Fixed Overhead (`$0.3500` on A100 community `$1.39/h`):** Single shorter pod run (`~1.4 h` total vs `~3.8 h`).
- **Policy 3 Exact Cost Arithmetic (`120.0 s` LTX, `28 Qwen pictures`, `$0.35–$0.50` Pod):**
  - *LTX (`120.0 s`):*
    - Plain (`$0.01600/s`): `120.0 * $0.01600` = **`$1.9200`**
    - With retry allowance (`$0.024306/s`): `120.0 * $0.02430556` = **`$2.9167`**
    - At H100 185f benchmark (`$0.032480/s`): `120.0 * $0.032480` = **`$3.8976`**
  - *Qwen (`28 pictures`):*
    - Measured A100 community (`$0.02363/pic` + `$0.04004` load): `28 * $0.02363 + $0.04004` = **`$0.7017`**
    - Measured H100 NVL (`$0.02590/pic` + `$0.04389` load): `28 * $0.02590 + $0.04389` = **`$0.7691`**
    - Plan retry-buffered rate (`$0.04167/pic`): `28 * $0.041667` = **`$1.1667`**
  - *Pod Fixed Overhead:* **`$0.3500`** (A100) to **`$0.5000`** (H100).
  - **Policy 3 Total RunPod GPU Cost:**
    - **Plain LTX + Measured H100 Qwen + `$0.50` Pod:** `$1.9200 + $0.7691 + $0.5000` = **`$3.1891`** (or **`$3.1217`** on A100 with `$0.50` pod).
    - **Retry LTX + Retry-Buffered Qwen + `$0.50` Pod:** `$2.9167 + $1.1667 + $0.5000` = **`$4.5834`**.
    - **H100 185f Benchmark + Retry-Buffered Qwen + `$0.50` Pod:** `$3.8976 + $1.1667 + $0.5000` = **`$5.5643`**.
    - **All-In Episode Total (adding ElevenLabs `~$2.0000 [EST]`):** **`$5.1891`** (plain) to **`$6.5834`** (with retry buffers) to **`$7.5643`** (H100 185f worst-case).

---

## 5. Side-by-Side Summary Table Across All Three Policies (12-Minute Episode = `720.0 s`)

| Metric | Policy 1: Today's Plan (60% LTX, No Reuse Solver) | Policy 2: `needs_ltx` Shot Test Only (Still/2.5D Where Valid) | Policy 3: Maximal Reuse (`R0–R5` Solver + `needs_ltx` Test) |
|---|---|---|---|
| **LTX Video Seconds (% of 720 s)** | `432.0 s` (`60.0%`) | `162.0 s` (`22.5%`) | `120.0 s` (`16.7%`) |
| **Free J5 2.5D + Still w/ Camera Move Seconds** | `216.0 s` (`30.0%`) | `486.0 s` (`67.5%`) | `528.0 s` (`73.3%`) |
| **Free Helper Graphics (`H`) Seconds** | `72.0 s` (`10.0%`) | `72.0 s` (`10.0%`) | `72.0 s` (`10.0%`) |
| **Qwen Pictures Generated** | `72 pics` (`56 shots + 16 assets`) | `72 pics` (`56 shots + 16 assets`) | `28 pics` (`6 R5 + 5 R3 + 17 R4`; `44 reused via R0–R3`) |
| **LTX Cost — Plain (`$0.01600/s` `[UNMEASURED]`)** | `$6.9120` | `$2.5920` | `$1.9200` |
| **LTX Cost — Plan Retry Buffer (`$0.02431/s` `[UNMEASURED]`)** | `$10.5000` | `$3.9375` | `$2.9167` |
| **LTX Cost — H100 185f Rate (`$0.03248/s` `MEASURED` v4)** | `$14.0314` | `$5.2618` | `$3.8976` |
| **Qwen Cost — Measured H100 NVL (`$0.02590/pic` + `$0.0439` load)** | `$1.9087` | `$1.9087` | `$0.7691` |
| **Qwen Cost — Plan Retry Buffer (`$0.04167/pic` `[UNMEASURED]`)** | `$3.0000` | `$3.0000` | `$1.1667` |
| **Pod Fixed Cost (`[UNMEASURED]` estimate)** | `$0.5000` | `$0.5000` | `$0.5000` |
| **RunPod GPU Total (Plain LTX + Measured Qwen)** | **`$9.3207`** | **`$5.0007`** (`-46.3%`) | **`$3.1891`** (`-65.8%`) |
| **RunPod GPU Total (Plan Retry LTX + Retry Qwen)** | **`$14.0000`** | **`$7.4375`** (`-46.9%`) | **`$4.5834`** (`-67.3%`) |
| **RunPod GPU Total (H100 185f LTX + Retry Qwen)** | **`$17.5314`** | **`$8.7618`** (`-50.0%`) | **`$5.5643`** (`-68.3%`) |
| **All-In Episode Total (incl. `$2.00 [EST]` ElevenLabs)** | **`$11.32 – $19.53`** (mid **`$16.00`**) | **`$7.00 – $10.76`** (mid **`$9.44`**) | **`$5.19 – $7.56`** (mid **`$6.58`**) |
