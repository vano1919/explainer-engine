# J5 dialogue, montage and animation: review request for Argon (2026-11-06)

> **Route-scoped since D-116 (2026-11-06):** this page belongs to route J5 (Qwen assets + Blender 2.5D, no LTX); the route decision is in the [decision log](DECISIONS_AND_OPEN_QUESTIONS.md).

For Gemini "Argon". Free work only: no pod, no paid call. Branch with everything: see "Where the code is". The creator's goal for this strand: the 30 % still / collage lane and the dialogue lane of a 12-15 minute Ink Chronicle episode
(Qwen-Image-2.1 + xworld_v2 draws, Blender builds space and time, FFmpeg assembles, LTX only where motion is needed, D-96 as amended / D-116), all with pictures that exist already, tested on a one-minute, five-scene film.

## Where the code is
- Repository `vano1919/explainer-engine` (private), branch **`claude/project-thread-4nebmi`**, draft PR #151 (base `icw/05c-ink-round`), head = the latest commit of the branch (546f2a6 or newer). The same commits are merged into `argon/handoff-2026-11-06` (PR #153) when its builder refreshes it.
- Files to read, in order: `docs/J5_DIALOGUE_COLLAGE.md` (sections 7d-7j, the whole record), `explainer_engine/blender/j5_cuts.py` (cut lint, BP-176..178), `j5_montage.py` (montage lint, BP-179..181), `j5_minute.py` (the plan of the film), `j5_face.py` + `j5_variant_sheet.py`
  (mouth swap from one variant sheet per hero, D-119), `j5_background.py` (the dialogue shots), `j5_minute_anim.py` / `j5_minute_depth.py` / `j5_minute_depthcam.py` / `j5_minute_post.py` / `j5_minute_ambience.py` (v2 of the minute), `explainer_engine/standards/sourced_rules.json` (BP-176..181).
- Outputs (Hugging Face dataset `vano1919/tmr-artifacts`, private): `route_test_2026-11/j5_dialogue/step4f/` (the 12.5 s dialogue), `route_test_2026-11/j5_minute/v1/` and `v2/` (the minute, `minute_j5_v2.mp4`, `contact_v2.png`), `route_test_2026-11/j5_dialogue/mouth_variants_input/`.

## What was built and what the creator said about it
1. Dialogue (H1 commander, H2 scout, Blender 2.5D cards, painted mouths from Rhubarb cues, a young scout voice). Creator: straight film cuts, no black dip; the jaw must not slide; a cut needs a reason, never "the same man, only closer".
   Rules BP-176 (30-degree rule + size step, axial cut-in declared), BP-177 (plan check before any picture: first picture is the wide two-shot, sides and eyelines fixed), BP-178 (punch-in and reuse of a picture, hypothesis).
2. Mouths from ONE variant sheet per hero (8 variants in a grid, cut by Python, swapped on cue weights): written, tested on synthetic data, waiting for the real Qwen sheets (paid pod, creator's word).
3. The one-minute film. v1 was criticised by the creator: "illogical cuts and order of photos, nothing is animated". v2: story order by time and place, local animation of what the pictures show (a bob travelling down the marching column, flags, water, smoke, crowd sway, sword flashes, flames, fog, embers, rain),
   a Blender relief camera from Depth Anything V2 depth maps, ambience per place, the mix at -14.0 LUFS (BP-50). Weak points (honest): the elder is a flat card, the drummer cut-in is soft, the courtyard picture looks more 3D-render than the rest, the crowd bobs but does not walk or fight, masters are 1080p.
4. The creator's verdict on scope (21:56 UTC): worth it for dialogue and for the 30 % still lane (not plain photo collage but animated shots); action shots need LTX.

## Sources used (exact links)
Wikipedia (read in full, 2026-11-06): https://en.wikipedia.org/wiki/Film_editing, https://en.wikipedia.org/wiki/Cut_(filmmaking), https://en.wikipedia.org/wiki/Montage_(filmmaking), https://en.wikipedia.org/wiki/Match_cut, https://en.wikipedia.org/wiki/Continuity_editing,
https://en.wikipedia.org/wiki/Dissolve_(filmmaking), https://en.wikipedia.org/wiki/Fade_(filmmaking), https://en.wikipedia.org/wiki/Jump_cut, https://en.wikipedia.org/wiki/Cross-cutting, https://en.wikipedia.org/wiki/Ken_Burns_effect, https://en.wikipedia.org/wiki/Multiplane_camera,
https://en.wikipedia.org/wiki/Establishing_shot, https://en.wikipedia.org/wiki/Cutaway_(filmmaking), https://en.wikipedia.org/wiki/Rule_of_thirds, https://en.wikipedia.org/wiki/Headroom_(photographic_framing), https://en.wikipedia.org/wiki/Cutout_animation, https://en.wikipedia.org/wiki/Parallax_scrolling,
https://en.wikipedia.org/wiki/Limited_animation, https://en.wikipedia.org/wiki/Camera_coverage, https://en.wikipedia.org/wiki/30-degree_rule, https://en.wikipedia.org/wiki/Shot_reverse_shot, https://en.wikipedia.org/wiki/Kuleshov_effect, https://en.wikipedia.org/wiki/Animatic.
GitHub / papers: https://github.com/BrokenSource/DepthFlow (parallax shader), https://github.com/sniklaus/3d-ken-burns and https://arxiv.org/abs/1909.05483 (depth + inpainting, needs CUDA), https://github.com/facebookresearch/AnimatedDrawings (rig a drawn figure, retarget BVH motion; runs headless with Mesa and numpy 1.x; our hand-rigged robed elder collapsed),
https://github.com/DanielSWolf/rhubarb-lip-sync (mouth cues, used), https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf (depth, used).
Not verified: a UChicago study on dialogue cut points (PDF unreadable), the retention numbers of creator tutorials about punch-ins.

## What I ask Argon
Read the files above and the sources, then answer in a document with exact links:
1. Which better, existing editing rules or code exist for (a) dialogue cutting with a still-based 2.5D camera, (b) non-dialogue montage and transitions between still pictures, (c) animating a still picture locally (masks, flow, cut-out rigs) without a video model? Prefer sources the repository can use (licence is not a gate, the creator decided).
2. Where do BP-176..181 or the code in `j5_cuts.py` / `j5_montage.py` contradict a better source? Give the page and quote.
3. How would you animate the crowd and action shots cheaply (cut-out rigs with walking BVH, depth-aware inpainting, frame interpolation, LTX at the shortest useful clip) so that the LTX share stays minimal? Rank by cost and by how well the ink style survives.
4. A full rig for hero figures with visible legs (Animated Drawings or another free method): what is the minimum input (joint annotation, mask) and where does it fail on robes?

## Prompt (paste as is)
"You are Argon, reviewing a free-work branch of the repository vano1919/explainer-engine (branch claude/project-thread-4nebmi, PR #151, use the latest commit; file docs/J5_ARGON_REVIEW.md lists everything). The channel makes 12-15 minute animated explainers in an ink-painted style; Qwen draws, Blender builds space and time, LTX animates only what must move, FFmpeg assembles.
Read docs/J5_DIALOGUE_COLLAGE.md sections 7d-7j, explainer_engine/blender/j5_cuts.py, j5_montage.py, j5_minute.py and the rules BP-176..181 in explainer_engine/standards/sourced_rules.json. Then search Wikipedia, GitHub and the web for better editing and animation methods for (1) dialogue shot/reverse-shot from still-based cards, (2) transitions and pacing of non-dialogue stills, (3) local animation of a still picture without a video model, (4) rigging a drawn hero with visible legs. For every claim give the exact link and a quote; say what you verified and what you did not. Mark where our rules or code are wrong or weak, and rank your suggestions by cost and by how well they keep the ink style. Do not propose paid runs without a cost estimate; do not change the creator's decisions (D-96, D-116, D-119); free work only."
