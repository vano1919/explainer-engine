# Prompt for Argon (Gemini): minimise LTX realistically, plan the Python / Blender / FFmpeg limits, write the code (2026-11-06)

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX; LTX stays for the J2/J4 shots.

Paste everything under the line into Argon. Written for the creator (22:01 UTC request). Free work only.

---

You are Argon, the engineer of the repository **vano1919/explainer-engine** (private; you read it through git). Your branch for this job: create `argon/ltx-minimisation` from the head of **`claude/project-thread-4nebmi`** (https://github.com/vano1919/explainer-engine/tree/claude/project-thread-4nebmi, draft PR #151, base `icw/05c-ink-round`). That branch holds the latest work of the thread that built the J5 dialogue and montage tools; read it as it is, do not assume anything the repository does not show.

## 0. The goal, in numbers
The channel makes 12-15 minute animated explainers in an ink-painted style. Qwen-Image-2.1 with the xworld_v2 LoRA draws every picture, Blender builds space and time, FFmpeg assembles, LTX (a paid image-to-video model on a RunPod GPU) animates only what must move. Today a 12-minute episode is estimated at about 430 s of LTX at roughly US$10-11 with retries, against a total render target of US$10-15 (docs/DECISIONS_AND_OPEN_QUESTIONS.md, D-96 as amended, D-116; docs/COST_AND_TIME_MODEL.md).
**Your goal: cut the LTX seconds of an episode as far as is realistically possible, without breaking the look and without lying about what a still picture can do.** "Realistically" means: you name, per shot type, what Python, Blender and FFmpeg can do convincingly, what they cannot, and the LTX seconds that remain. Give the remaining LTX share as a number with its basis (measured here, measured elsewhere, or estimated), and the visual-lane shares that result (BP-109: 60 % moving, 30 % still with camera motion, 10 % helper graphics, tolerance 5 points; discuss honestly whether the 60 % must really be generated video).

## 1. Required reading, with receipts (do this first; do not skip)
Read in full and, at the top of your first report, give one **verbatim quoted line from each file** as proof (a file you cannot quote is a file you did not read):
1. `docs/J5_ARGON_REVIEW.md` (index of the work, the sources already used, the creator's remarks).
2. `docs/J5_DIALOGUE_COLLAGE.md`, sections 7d to 7j and the "v2 of the minute" and "Existing code tried" paragraphs.
3. `explainer_engine/blender/j5_cuts.py`, `j5_montage.py`, `j5_minute.py` (rules BP-176 to BP-181 as code and the plan of the one-minute film).
4. `explainer_engine/blender/j5_face.py`, `j5_variant_sheet.py`, `j5_background.py` (dialogue shots, mouth swap from one variant sheet per hero, D-119).
5. `explainer_engine/blender/j5_minute_anim.py`, `j5_minute_depth.py`, `j5_minute_depthcam.py`, `j5_minute_post.py`, `j5_minute_ambience.py` (what v2 of the minute does to a still).
6. `explainer_engine/standards/sourced_rules.json`: BP-108, BP-109, BP-172, BP-176 to BP-181 (thresholds and source types), and `docs/SOURCED_RULES.md` for how a rule becomes binding (two of article / book / video).
7. `CLAUDE.md` (invariants; never weaken a test; every change gets a focused test and a `docs/PROGRESS.md` entry; the commit identity line).
Also look at the outputs described in the review file (Hugging Face `vano1919/tmr-artifacts`, `route_test_2026-11/j5_minute/v2/`) if you can; if you cannot, say so.

## 2. What is already known (do not rediscover; challenge it if you can)
- Dialogue by Blender 2.5D cards with painted mouths from Rhubarb cues works and needs no LTX; the cut rules BP-176 to BP-178 are enforced by lint.
- A still picture can carry: a real perspective camera over a depth-relief mesh (Depth Anything V2 Small, Blender Workbench, about 1 s per 1080p frame on 4 CPU cores), local motion by colour and depth masks (a bob travelling down a column, waving flags, flowing water and smoke, flames, fog, embers, rain), ambience. It cannot make a crowd walk or fight.
- Tried and failed or blocked: Meta Animated Drawings on a robed figure without visible legs (the rig collapsed, hand-placed joints), 3D Ken Burns (needs CUDA), the paid mouth-variant sheets (waiting on a pod and the creator's word).
- Creator's verdict (2026-11-06 21:56 UTC): worth doing for dialogue and for the 30 % still lane as animated shots (not a plain photo collage); action shots need LTX. Your job is to test that verdict, not to repeat it: find how far "action without LTX" can really go.

## 3. Research (you do it yourself; minimum bar)
Search Wikipedia, GitHub, arXiv and project documentation (Blender manual, FFmpeg docs, Hugging Face model cards). For every candidate library, code base or technique give a table row: name, exact link, licence (a licence is information, not a gate: the creator decided that performance wins), what it does, CPU or GPU need, install effort, fit to a flat ink-painted style, failure modes, and **verified / not verified** (opened the code or paper, or only read a description). At least 25 sources, covering at minimum:
- cut-out and puppet animation (rigged 2D characters, skeletal retargeting, mesh warping, As-Rigid-As-Possible, Spine / Live2D-like free tools, Blender Grease Pencil and 2D rigging);
- walking, fighting and crowd motion for flat characters (BVH / mocap libraries with usable licences, motion retargeting to a 2D rig, crowd simulation in Blender, billboard crowds);
- depth-based parallax and inpainting (DepthFlow, 3D Ken Burns and its CPU-capable successors, depth-aware inpainting);
- frame interpolation and optical-flow animation of stills (RIFE, FILM, flow-guided warping), and the cheapest video model options (clip length, resolution, price) so that the LTX seconds that remain are as short as they can be;
- editing theory for still-based montage (the Wikipedia pages used in `docs/J5_ARGON_REVIEW.md`, and whatever you find that is better: books, courses, articles; quote the page).
Say plainly what you could not open.

## 4. Plan the boundaries (decide, write down, justify)
Produce a table of **limits** for each tool, with the rule that enforces it in code or lint:
- **Python** (numpy, OpenCV, masks, optical flow): what it may animate and where it must stop.
- **Blender** (scene, camera, 2.5D relief, rigs, layout passes, crowds): what it builds, which renderer, the seconds-per-frame budget on CPU CI and on the creator's RX 5700 PC (no CUDA), what stays out of Blender.
- **FFmpeg** (assembly, transitions, loudness): what it does, what it must not.
- **Qwen** (every picture): what must be drawn rather than composed.
- **LTX**: the exact situations in which it is still needed, the shortest useful clip, the cap on seconds per shot type.
Include the data handed between the tools (file formats, manifests) and a decision rule a script can apply to a shot ("this shot goes to Blender-relief / cut-out rig / LTX because ...").

## 5. Write the code
Implement what you decided, directly in the repository on your branch, as small commits: new modules next to `j5_*.py`, a shot router that applies your decision rule, lints for your limits (read thresholds from `explainer_engine/standards/sourced_rules.json` through `sourced_rules.T`; a new rule needs its sources and starts as a hypothesis, REVIEW only), a focused unit test for each module, a `docs/PROGRESS.md` entry, `docs/INDEX.md` rows for new docs; `python -m explainer_engine.docs_lint` must report 0 findings and the unit suite must stay green (never remove or weaken a test). Commit identity: `git -c user.name=vano1919 -c user.email=122537395+vano1919@users.noreply.github.com`. Open a **draft** PR against `claude/project-thread-4nebmi`.
Then **prove it on the one-minute film** (`explainer_engine/blender/j5_minute.py`, five scenes, three heroes): build v3 in which every action shot uses your cheapest convincing method, list for each shot the method and the LTX seconds still needed, and compare with v2. Show frames (a contact sheet) and say what a viewer will still find wrong.

## 6. Hard limits
- Free work only: no pod, no paid API call, no RunPod, no ElevenLabs, no paid image generation. A paid step is proposed as a plan with a cost estimate and waits for the creator's word.
- Do not change the creator's decisions: D-96 as amended, D-116 (J5 = Qwen assets + Blender cards + FFmpeg, no LTX), D-119 (mouth variants from one sheet), the rule that only Qwen 2.1 with the style LoRA draws pictures, the ban on a black dip between shots, English for everything the viewer sees or hears.
- Never present a guess as a measurement. Mark every number as measured, cited or estimated, with the source or the command.
- If a task seems to require breaking an invariant in `CLAUDE.md`, stop and report the conflict with evidence and options.

## 7. What you hand back
(1) a report as a document with the receipts, the source table (links, licence, verified or not), the limits table and the decision rule, written so that a reader who has not seen the repository can follow it; (2) the draft PR with code, tests and docs; (3) the v3 film path and contact sheet; (4) a short list of what still needs LTX, in seconds per 12-minute episode, and the estimated cost; (5) a list of the claims in `docs/J5_DIALOGUE_COLLAGE.md` and in BP-176 to BP-181 that you found wrong or weak, each with the source and a quote.
