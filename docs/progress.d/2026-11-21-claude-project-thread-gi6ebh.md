## 2026-11-21 — DeepSeek ceiling recorded, PR 252/253 merged (P1)

Done: PR #253 (deepseek-worker skill + tool) and PR #252 (assembly line) merged to main after green CI. Added the `deepseek_api` line
($10 per week) to `config/spend_caps.json` on the creator's word (the "start execution" answer to the DeepSeek cost card, relayed by the
coordinator; recorded with `governance ok protected_config`, message cmsg_01Hnu5zB86sjUj5GtTgaUkPW2nA93UhHqTMgSF6w2H9s19).
Project rule 15 (scripts written by the thread's Claude) is replaced by: scripts are written by DeepSeek, Claude plans and checks.
Cost: none yet. Next: P2 fail-closed fixes through the DeepSeek tool.

### P2 — fail closed (DeepSeek Flash, $0.002)
`production/build_shot.validate_spec` now runs `build_map_shot.check_spec` for map shots (camera, film_file, arrows were checked only at render time).
Photo shots already require camera and film since #252; `living` has no silent drift path under `build_shot`. Test: `tests/unit/test_no_silent_fallbacks.py`.

### P3 — receipts and delivery gate (DeepSeek Pro, ~$0.29 in 3 attempts)
New `qa/delivery_gate.py`: reads the episode log and every shot's `.render_log.json` receipt; a missing receipt, key, clip, camera move outside the five,
film id, font, depth, a non-PASS plume check or `paid_calls != 0` is FAIL. `build_map_shot` receipts now carry camera, film_id and font;
`build_episode` runs the gate, writes `<out>.delivery_gate.json` and raises on FAIL. Tests: `tests/unit/test_delivery_gate.py` plus adapted fixtures.
Claude read the gate logic in full. Old cached map clips without the new receipt keys FAIL until rebuilt (intended).

### P4 — one render path for map shots (DeepSeek Flash, $0.005)
`edit/visual_compensator.render_item_frame` refuses the old PIL map renderer unless `allow_legacy_map=True` or `EXPLAINER_ALLOW_LEGACY_MAP=1` (the owner's permission);
map shots belong to `production/build_shot` kind "map" (maplibre lane). Tests: `test_no_silent_fallbacks.py`; the old-renderer tests set the flag explicitly.
