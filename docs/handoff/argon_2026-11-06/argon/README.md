# Argon Handoff Execution (`docs/handoff/argon_2026-11-06/argon/README.md`)

## მოკლე შეჯამება დამკვეთისთვის (ქართულად)

ეს საქაღალდე (`docs/handoff/argon_2026-11-06/argon/`) და შესაბამისი კოდის პაკეტი (`explainer_engine/visual/`, `explainer_engine/schemas/visual_script_1.json`, `tests/unit/test_{visual_script,still_needs,reuse_plan}.py`) შეიცავს [`ARGON_PROMPT.md`](../ARGON_PROMPT.md)-ის A, B, C, D და E ნაბიჯების სრულ შესრულებას ბრანჩზე `argon/handoff-2026-11-06` (`main`-ზე არაფერი გადასულა, დახარჯულია `$0.00`, ყველა ლინტერი და ტესტი სუფთაა).

| ნაბიჯი | ფაილი ამ საქაღალდეში / კოდში | შინაარსი და შედეგი |
|---|---|---|
| **A. აუდიტი** | [`A_AUDIT.md`](A_AUDIT.md) | [`MATERIAL.md`](../MATERIAL.md)-ის 19 სეტისა და [`images/`](../images/)-ის 17-ვე ფურცლის ვიზუალური აუდიტი + 8 ადგილი გეგმებში, სადაც ვიდეო სურათებს ერგებოდა სცენარის ნაცვლად. |
| **B. ხარჯთაღრიცხვა** | [`B_COST_MODEL.md`](B_COST_MODEL.md) | კადრის (`J1–J5`, `H`, უფასო სტატიკური/2.5D მოძრაობა, Qwen, LTX, პოდის ფიქსირებული ხარჯი) და 12-წუთიანი (`720 წმ`) ეპიზოდის ზუსტი არითმეტიკული მოდელი 3 პოლიტიკისთვის (`$14.00 -> $7.44 -> $4.58` გამეორებების ბუფერით; `$9.32 -> $5.00 -> $3.19` გამეორებების გარეშე). |
| **C. დიზაინი** | [`C_DESIGN.md`](C_DESIGN.md) | `visual_script/1` (`D-119`), `"needs LTX"` კადრის ტესტი, `in_shot` + Blender frustum შემოწმება (`SO-14`), `R0–R5` სოლვერის წესები და `OR-23` / `Q5 A` დასამტკიცებელი გვერდის არქიტექტურა. |
| **D. იმპლემენტაცია** | [`D_IMPLEMENTATION.md`](D_IMPLEMENTATION.md) + [`OR23_ROUTE_TEST_APPROVAL_PAGE.md`](OR23_ROUTE_TEST_APPROVAL_PAGE.md) | უფასო კოდის პაკეტები: `explainer_engine/visual/{visual_script.py,still_needs.py,reuse_plan.py}`, `explainer_engine/schemas/visual_script_1.json` და 7 იუნიტ-ტესტი (`tests/unit/test_{visual_script,still_needs,reuse_plan}.py`). |
| **E. ფასიანი ტესტის გეგმა** | [`E_PAID_TEST_PROPOSAL.md`](E_PAID_TEST_PROPOSAL.md) | ყველაზე იაფი კალიბრაციის პოდის (`p15_mini_cal`) შეთავაზება (გაშვების გარეშე): 2 Qwen რესტაილი + 2 LTX კლიპი (`121f` და `185f`), მოსალოდნელი ხარჯი `$0.43–$0.66`, უარესი შემთხვევის ჭერი `$0.70–$1.30`. |

---

## 1. Files in `docs/handoff/argon_2026-11-06/argon/`

1. **[`A_AUDIT.md`](A_AUDIT.md)** — Per-set visual audit of all 19 sets in [`MATERIAL.md`](../MATERIAL.md) across all 17 contact sheets in [`images/`](../images/) (documenting 7 table-vs-section verdict discrepancies, identity drift, unneeded props violating Standing Order 14, soft backdrops, and missing hero angles) + 8 places where existing plans still fit video to pictures.
2. **[`B_COST_MODEL.md`](B_COST_MODEL.md)** — Exact per-shot cost table (`J1–J5`, `H`, free still + camera move, Qwen per picture, LTX i2v per second, pod fixed costs) and 12-minute (`720.0 s`) episode cost estimates under Policy 1 (Today's Plan: `$9.32` plain / `$14.00` retry-buffered / `$17.53` H100 185f rate), Policy 2 (`needs_ltx` gate: `$5.00` plain / `$7.44` retry-buffered), and Policy 3 (Maximal Reuse `R0–R5`: `$3.19` plain / `$4.58` retry-buffered), marking every unmeasured input explicitly.
3. **[`C_DESIGN.md`](C_DESIGN.md)** — Implementation-level design for `visual_script/1` (`D-119`), the `needs_ltx` shot test, `in_shot` derivation + Blender frustum visibility check (`check_frustum_visibility` with `hide_in_blender`), reconciled `R0–R5` reuse rules (`REUSE.md` §2), and the `OR-23` / `Q5 A` creator approval page.
4. **[`D_IMPLEMENTATION.md`](D_IMPLEMENTATION.md)** — Summary of the implemented Python packages and unit test results (`7/7 PASS`, `<= 120` columns, `docs_lint` `0 finding(s)`).
5. **[`OR23_ROUTE_TEST_APPROVAL_PAGE.md`](OR23_ROUTE_TEST_APPROVAL_PAGE.md)** — Human-readable creator approval page generated deterministically from [`tests/fixtures/route_test/route_shots.json`](../../../../tests/fixtures/route_test/route_shots.json).
6. **[`E_PAID_TEST_PROPOSAL.md`](E_PAID_TEST_PROPOSAL.md)** — Written `OR-23` plan (not run) for `p15_mini_cal` (`2` Qwen restyles + `2` LTX clips at `121f` and `185f` on existing HF inputs; `$0.43` expected on A100 community / `$0.66` on H100 NVL; `$0.18–$0.23` early-exit keyframe gate; `$0.70–$1.30` hard ceiling).

## 2. Implemented Code & Unit Test Paths

- [`explainer_engine/schemas/visual_script_1.json`](../../../../explainer_engine/schemas/visual_script_1.json) — JSON Schema Draft 2020-12 contract for `visual_script/1`.
- [`explainer_engine/visual/__init__.py`](../../../../explainer_engine/visual/__init__.py) — Package exports.
- [`explainer_engine/visual/visual_script.py`](../../../../explainer_engine/visual/visual_script.py) — `needs_ltx(shot)`, `frames_8k_plus_1(seconds, fps=24)`, `build_visual_script(...)`, `validate_visual_script(...)`.
- [`explainer_engine/visual/still_needs.py`](../../../../explainer_engine/visual/still_needs.py) — `build_in_shot(...)`, `derive_shot_stills(...)`, `derive_still_needs(...)`, `check_frustum_visibility(...)`.
- [`explainer_engine/visual/reuse_plan.py`](../../../../explainer_engine/visual/reuse_plan.py) — `in_shot_signature(...)`, `setup_group_key(...)`, `solve_reuse_plan(...)`, `render_approval_page(...)`.
- [`tests/unit/test_visual_script.py`](../../../../tests/unit/test_visual_script.py) — 3 unit tests on `route_shots.json` (`9 -> 6` LTX clips, `1,089 -> 822` frames).
- [`tests/unit/test_still_needs.py`](../../../../tests/unit/test_still_needs.py) — 2 unit tests for `in_shot` derivation and frustum clutter auto-hiding.
- [`tests/unit/test_reuse_plan.py`](../../../../tests/unit/test_reuse_plan.py) — 2 unit tests including the 7-still hand-solved optimal plan (`5` Qwen pictures = `$0.1295`).
