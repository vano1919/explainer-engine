# J5 dialogue test, step 1 handoff (2026-11-06, thread "Test J5 dialogue with existing photos")

Done (free, $0): four 2560x1440 frames of one dialogue (H2 scout left, H1 commander right, A1 tent camp at dusk), as Blender 2.5D cards.
- Code: explainer_engine/blender/j5_collage.py (PR #151, draft, base icw/05c-ink-round, branch claude/project-thread-4nebmi); `transparent` flag in bpy/assemble_25d.py; edit/cutout.py CPU dtype fix from icw/16-lean-pod.
- Run: PYTHONPATH=. python -m explainer_engine.blender.j5_collage render --inputs <dir with A1_tent.png + <sheet>.cut.png> --out O --bpy-python <python with bpy==5.2.3>. Needs libegl1 libegl-mesa0 libgl1-mesa-dri (apt) in a bare container. 95 s for all four frames on 4 CPU cores.
- Outputs: this folder and HF datasets/vano1919/tmr-artifacts route_test_2026-11/j5_dialogue/step1/ (frames, contact_sheet.png, report.json, cards/, compare/).
- Cut-outs were made with edit.cutout.birefnet_mask + finish on B_H1_{left34,back}, B_H2_{right34,back} (torch CPU wheel, transformers); the .cut.png files are not on HF (only the graded cards are).

## Step 2 entry (only after the creator's OK, voice only from an existing take)
- Needed first: mouth states (closed/half/open) and an eyes-closed patch for the speaking card (H1 left34 in S2/S4); none exist. Options: 2D edits of the face region from the sheet, or Qwen edits (paid pod, his call). Brow/eye emotion variants likewise.
- Background motion: plate is a flat card 40 m away (plate_card), so camera drift gives parallax for free; add fire flicker (the plate's flame region + bloom pulse) and a smoke layer (2D).
- Voice: an existing recorded take (project files voice/line_1.wav or ledger takes) with Scribe timings -> assemble_25d LipSync.plan cues; dialogue shot <= 5 s per BP-108/D-95, clip 10-15 s as several shots. No new ElevenLabs call without his separate yes (feedback 11-01).
- Open from step 1: H1 has no legs (no wide, no contact shadow); H2 left-facing card (E_B_H2_left34 in assets/E, untried); the reverse OTS uses H1's back sheet mirrored.

## Update 2026-11-06 ~17:50 UTC: step 2 (background animation) done
Creator asked in the thread (17:25, 17:26). Clip and stills v2 (face shadow): /mnt/project-files/explainer-engine/j5_dialogue_step2/ and HF route_test_2026-11/j5_dialogue/step2/. Code: blender/j5_background.py. Record for the future standard: docs/J5_DIALOGUE_COLLAGE.md. PR #151 @ 0e7f061. No voice, no mouth yet (variants do not exist).
