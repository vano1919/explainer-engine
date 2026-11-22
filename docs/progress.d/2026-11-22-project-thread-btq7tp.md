## 2026-11-22 — Test Film v4: three separate shots (map, 2.5D, LTX video), rendered and uploaded
- Three shots, each made once, no new pictures and no new narration: S1 map (`build_episode --only S02_SH001`, MapLibre lane, `zoom_in`), S2 2.5D photo
  (`S02_SH005`, fire and smoke, `zoom_in`), S3 LTX-2.5 video on Modal (Truce photo `S02_SH004` cropped to 1280x704, 5 s, no speech, slow push-in).
  S1 and S2 passed `qa/delivery_gate` (`tf4_s1_s2.delivery_gate.json`), 1280x720, 24 fps. S3: 121 frames, 1280x704, sha256 92637f64…; start, middle and
  last frame show the same three faces, a push-in and no melting. The bridge words of the map were not added (open question, not settled); the map shows
  one date chip only, so the "rich map, big text" rule is NOT exercised by S1.
- Modal: one L4 launch (ladder L0-L3 of the same launch/worker shas), reservation $0.97, settled $0.1196 for 84.5 s on the ledger
  (`/mnt/project-files/test_film_v4/ledger_s3.json`; the ledger counts only the `.remote()` wall clock and runs about 60 % under the account's bill,
  so the true cost is estimated at about $0.2). App `ap-LwTNI4OuYmNM7SQrj0HUWD` stopped, nothing left running. Under the $2 line and the night's $20.
- Files: `training/pods/ltx/scenes/test_film_v4_s3.json`, `tests/unit/test_test_film_v4_scene.py`. Media on HF `explainer-engine/test_film_v4/`.
- Not done: the Fable full-repo audit (OR-34) was not run for this $0.12 test; run on the coordinator's word; no technical-gate numbers for S3 yet.
