# Workflow 02: Hybrid Render & Governed Modal H100 LTX-2.5 Loop

## Prerequisites
- Anchor-locked keyframes verified via Workflow 01.
- SQLite Spend Ledger (`explainer_engine/core/spend_ledger.py`) initialized with `$15.00` Modal H100 hard ceiling (`$12.00` 80% checkpoint).

## Steps
1. **Smart Hybrid Shot Routing (`DEF-07`, D-131):**
   - `ltx_video` (~40–50%): Human acting, spoken diegetic dialogue, fire ignition, active physical combat/movement. Hard-capped at **4.0–6.0s** (`97–145` frames @ 24fps, `8n+1`) with explicit prop end-state continuity clauses (`DEF-05`).
   - `still_25d` (~30–40%): Establishing environmental plates, atmospheric holds, dramatic tableaus via `cinema_25d.py` (Depth Anything V2 ONNX continuous zero-tear parallax, `$0.00`).
   - `map_action` (~15–20%): Geographic campaigns, routes, beacon/supply chains via `cinema_map.py` (Natural Earth 1:10m NE1+SR shaded relief + synced CC0 SFX, `$0.00`).
2. **Reserve Spend Before Modal Launch:**
   - Call `antigravity_runner.py` to atomically `reserve()` estimated Modal H100 spend in SQLite WAL BEFORE launching `modal_ltx_jobs.py::main`.
   - Settle actual USD immediately on completion; zero stuck `RESERVED` rows.
3. **Post-Render Cinema Polish:**
   - Run automatic **BP-187 Speech/Action End-Point Trimmer** (`explainer_engine/edit/trim.py`) to cut `0.35–0.50s` after final word/beat (`DEF-03`).
   - Apply unified 35mm cinema grade (`cinema_grade.py` / `.cube` LUT + grain + vignette) and 2K `2560x1440` Lanczos+CAS upscale (`DEF-08`).
