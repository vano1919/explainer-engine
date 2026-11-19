# Opus visual check of the six shots rendered from the NEW director's direction files (S7, 2026-11-15)
Renders: https://huggingface.co/datasets/vano1919/tmr-artifacts/tree/main/explainer-engine/argon_loop_2026-11-15/2p5d_new_director_s7
- S01, S05_SH016, S06, S08, S02: no isolated one-frame jumps; QA rows PASS except REVIEW fill_invents on S05_SH016.
- S05_SH020: the director chose right (push to left_group on "scottish", pan_crop_2d to right_group on "student", no orbit/truck),
  but the RENDERER executes pan_crop_2d wrongly: the view moves LEFT (toward the Scots) instead of right, a soldier is cut at the left
  edge (frame 150), and at the end of the 30-frame accent window the view whips back in 3 frames (frames 148-151, 29-32 per frame).
  Strip: .../2p5d_new_director_s7/S05_SH020_s7_frames.jpg. To fix in directed25d Stage.view (pan_crop_2d sign, hold after the
  accent instead of returning, keep_in_frame for the pan window).
