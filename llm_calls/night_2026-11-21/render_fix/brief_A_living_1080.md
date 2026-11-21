Task: make the 2.5D still-motion renderer output 1920x1080 instead of 1280x720. Repo: explainer-engine (Python 3.12).

File: explainer_engine/fx25d/living.py. Module constants: W, H, FPS = 1280, 720, 24 (line 14). Many coordinates in the file (OFFICER polygon, fires boxes, faces, mouths) are in the 1280x720 working space and must stay that way.

Required change (minimal, no change of motion logic):
1. Keep all internal processing in the 1280x720 working space exactly as now (the coordinates stay valid).
2. The OUTPUT frames and the output video must be 1920x1080 (W_OUT=1920, H_OUT=1080). Resize each finished working frame to 1920x1080 with cv2.INTER_LANCZOS4 just before it is written/encoded. Add module constants W_OUT, H_OUT and a function or constant used by the writer and ffmpeg size arguments so the encoded size is 1920x1080.
3. The picture input (--pic) is still resized to the working 1280x720 as today.
4. Do not change the depth, motion, particles or measurement code paths except where they write frames or set the encoder size.
5. Add a unit test file tests/unit/test_living_output_size.py that checks: the constants W_OUT == 1920 and H_OUT == 1080; a helper (name it output_size_frame or similar, add it to living.py) takes a 720x1280 BGR array and returns 1080x1920x3; the ffmpeg command built for encoding (if a function builds it) contains "1920x1080". If no function builds the command, test the helper only and say so in a comment. Do not run ffmpeg in the test.
6. Keep the existing tests in tests/unit passing that touch living.py (run: python -m pytest -q tests/unit -k "living or fx25d").

Output: the full changed living.py via the diff tooling of the worker; do not rename public functions; no new dependencies beyond cv2 and numpy which are already used.
