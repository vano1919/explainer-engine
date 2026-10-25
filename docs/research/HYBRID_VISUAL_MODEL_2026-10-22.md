# The hybrid visual model: AI for the world, classic rigs for the characters (2026-10-22)

The creator's question (2026-10-22 17:48): should AI only paint and move the environment (backgrounds, clouds, water,
trees), while the characters, especially hard ones (wounded, a specific pose), are drawn and rigged with classic tools that
AI controls? Research only, nothing paid, no architecture change. Context: the Wild Ink style is chosen; the cut-out rig
`production/rig.py` and the 10-second ice-age test live in draft PR #20; the test's audit (project files,
`animation_universe_2026-10-22/ice_test/AUDIT_ice_shot_ka.md`) found that the image models do not give a character in
parts, so the legs read as separate pieces and the joints are rough (items 5 and 8). Sources were read on 2026-10-22; a
claim the sources did not confirm is marked "not verified".

## მოკლედ (ქართულად)

**დიახ, ჰიბრიდი სწორი გზაა, ერთი შესწორებით:** ზღვარი არ გადის "ფონი AI / პერსონაჟი კლასიკური"-ზე, არამედ
"რა უნდა იყოს ზუსტი და განმეორებადი"-ზე. AI-ს ვანდობთ იმას, სადაც შემთხვევითობა არ გვაზიანებს (ფონის ნახატი,
ერთჯერადი ატმოსფერული კადრი, პერსონაჟის **დიზაინის** პირველი ესკიზი); კოდს და კლასიკურ რიგს ვანდობთ იმას, რაც ყოველ
ჯერზე ერთნაირი უნდა იყოს (პერსონაჟის სხეული, სახსრები, ნაბიჯი, ჭრილობა, ფიზიკა, ხმასთან სინქრონი). ყინულის ტესტის
ფეხების პრობლემა რენდერერის ბრალი არ არის: ერთი დახატული პოზიდან ნაწილები ამოიჭრა, მუხლის და დაფარული ნაწილების ნახატი
არ არსებობდა. გამოსავალი: პერსონაჟი **თავიდანვე ნაწილებად** უნდა შეიქმნას (ნაწილების ფურცელი, დაფარული კიდეებით და
მოხრის ზონებით) და სახსრები უნდა **იღუნებოდეს** (mesh deformation), არა მხოლოდ ბრუნავდეს. ღრუბლები, წყალი, ხეები
ძირითადად უფასოდ და დეტერმინისტულად მოძრაობს კოდით (ფენები, ნიღბები, ქარის რხევა); ფასიანი image-to-video მხოლოდ
იშვიათი ატმოსფერული კადრისთვის. გარე პროგრამებიდან (Synfig, Blender Grease Pencil, Godot, Rive, Spine, Live2D, Moho)
არცერთი არ სჯობს ჩვენს რიგს ღრუბელში, უთავო რენდერში და ტესტებში; Blender Grease Pencil ინახება სარეზერვოდ, თუ 3/4
შემობრუნება და რთული დეფორმაცია დაგვჭირდება. შემდეგი უფასო ნაბიჯი (შენი თანხმობით): ერთი გმირის PoC, კოდით დახატული
SVG ნაწილები Wild Ink-ის ხაზით + მოხრადი ფეხები + ტესტ-ფურცელი (სიარული, სირბილი, ხტომა, დაცემა, დაჭრილის კოჭლობა).

## 1. The verdict

Yes, with one correction. The useful line is not "background = AI, character = classic"; it is **"what must be exact and
repeatable" vs "what may vary"**:

| Layer | Who makes it | Why |
|---|---|---|
| Background plates (places, skies, terrain) | AI image model, in the chosen style, from the World Bible | variation is welcome, nothing has to match frame to frame; already our flow (paint plan, provider per batch) |
| Ambient motion of nature (clouds, water, foliage, fire, snow, dust) | **code** on the plate: layers, masks, flow, wind, particles | free, loops exactly, deterministic, no style drift; the TMR engine's "living pictures" already do this for fire |
| One atmospheric hero shot per episode (a storm, a flood) | AI image-to-video, only when code cannot do it | paid, can drift and morph; judged per usable second |
| Character design (look, face, outfit) | AI, once, as a sheet in the style, chosen by the creator (invariant 6) | AI is good at appeal, bad at consistent anatomy over time |
| Character body, joints, cycles, acting, wounds, props, lip-sync | **classic rig driven by code** (Claude writes the data, not a prompt) | must be identical every time; physics and timing must be measurable (the ice test's foot-slide and pop-in checks) |

This is the direction PR #20 already started (`rig.py`: rule 4 of its research doc, "a prompt never asks a picture for
motion"); the hybrid makes it explicit and adds the missing piece: **how the character's parts are made**.

## 2. Why the ice test's legs failed (the real cause)

From the audit (items 5 and 8) and the code: the figures were whole Seedream stickers or pieces cut from one painted pose.
A cut-out rig needs, for every joint, (a) a pivot at the joint, (b) hidden artwork under the overlap so a rotation does not
open a hole, (c) a front/back layer order, and (d) either a drawn knee or a bend zone. A single painted pose has none of
these, and no image model gives them reliably: the creator's master brief says the same (C4: "do not let image
segmentation cut every hard pose automatically without a check"). So the cure is upstream (the parts) and in the joint
(bend, not only rotate), not a better renderer.

## 3. AI for backgrounds and dynamic elements

| Element | Free code method (recommended default) | AI video alternative | Risks of the AI route |
|---|---|---|---|
| Clouds, sky | 2-3 cloud layers cut from the plate (or painted on their own), slow parallax drift, wrap-around for a loop; depth from `production/depth.py` (PR #18) | Wan 2.2 first-last-frame (same frame twice for a loop; community workaround, not documented) ([RunComfy](https://www.runcomfy.com/comfyui-workflows/wan-2-2-flf2v-first-last-frame-video-generation), [ComfyUI wiki, Fun InP Apache-2.0](https://comfyui-wiki.com/en/tutorial/advanced/video/wan2.2/wan2-2-fun-inp)) | loop seam, style softening |
| Water | mask the water region, scrolling flow/ripple displacement + highlight sparkle; exact loop by period | same | "boiling" texture, flicker ([Eurographics 2021: flicker tires the viewer](https://diglib7.eg.org/bitstream/handle/10.1111/cgf14398/v40i7pp021-032.pdf)) |
| Trees, grass | foliage mask, per-region sine sway with wind gusts (low frequency + small high frequency), anchored at the trunk/root | same | trunks bend like rubber, leaves morph |
| Fire, smoke, snow, dust | particles + the TMR flame mask (`tmr_engine/render/motion.py`: fire = flames only; v1 swayed lit walls, so the mask matters) | same | flame shapes drift out of style |
| Whole establishing shot with camera move | 2.5D parallax (PR #18 `production/parallax.py`) + the above | Veo/Kling/Wan clip (TMR `videogen.py` makes an 8 s Veo loop with the same first and last frame) | cost per usable second, morphing; vendors themselves advise slow camera moves and simple backgrounds ([Magic Hour](https://magichour.ai/templates/details/cmonzc6ks02a82e0yy97ji1yt-background-morph)) |

Precedent: Netflix Japan's short *The Dog & the Boy* (2023) used an image model for the backgrounds while the characters
stayed hand-drawn, the same split; it drew a backlash from artists over credit ("AI + Human") and labour, and critics said
the backgrounds still looked poor ([Cartoon Brew](https://cartoonbrew.com/tech/netflix-japan-ai-dog-and-boy-225631.html),
[Wikipedia](https://en.wikipedia.org/wiki/The_Dog_%26_the_Boy)). Lesson for us: the split works technically; the plates
must be judged and fixed (our paint plan + review), and disclosure follows our per-video checklist.

## 4. Classic tools that AI can drive

What "AI controls a classic tool" means in practice: Claude writes the tool's file or script (XML, JSON, Python, Lua) and a
headless command renders it in the cloud. The tool must therefore have (1) a text format or API, (2) a headless render,
(3) frames that are a function of time (our chunked render, RULE-R1), (4) a licence that lets us publish the output.

| Tool | AI-drivable? | Headless cloud render | Bend / mesh deform | Licence / cost | Fit for us |
|---|---|---|---|---|---|
| **Our `production/rig.py`** (numpy + PIL) | yes: Python data | yes (already, 1.7x real time at 720p) | rotation only today; mesh bend is the gap | ours | **keep as the renderer**; add bend zones |
| **Synfig** | `.sif` is XML; Python plug-ins since 1.5 for import/export ([1.5.0 notes](https://synfig.readthedocs.io/en/latest/releases/development/1.5.0.html)) | yes, the `synfig` CLI renders without a display ([Wikipedia](https://en.wikipedia.org/wiki/Synfig)); exact flags not verified | yes, Skeleton Deformation layer ([docs](https://synfig.readthedocs.io/en/latest/tools/skeleton.html)) | GPL-3 CLI ([Arch package](https://archlinux.org/packages/extra-testing/x86_64/synfig/)); free | the strongest outside candidate for a deform PoC; a second render path to maintain |
| **Blender Grease Pencil** | yes: `bpy`; community MCP servers exist, including one that runs scripts in headless Blender ([Glama list](https://glama.ai/mcp/servers/@cwahlfeldt/blender-mcp/blob/35855a186923dbdfdebaff1edb1dfcc76b58ee0c/README.md)) | yes in principle; older Grease Pencil headless crashes were reported ([T85546](https://developer.blender.org/T85546)), v3 not verified | yes (armatures, real 3D turns, lighting) | GPL app, "what you create with Blender is your sole property" ([blender.org](https://www.blender.org/about/license/)); free | the backup when we need 3/4 turns, perspective, heavy deformation; heavy (GPU pod, big install) |
| **OpenToonz** | ToonzScript (QtScript) from the menu; command-line scripts only in the Morevna fork ([docs](https://opentoonz.readthedocs.io/ja/latest/toonzscript.html), [Morevna 1.3](https://morevnaproject.org/2019/03/23/opentoonz-morevna-edition-1-3-0-released)) | not verified | yes | open source; licence not verified in this pass | weak for automation |
| **Godot** | yes: scenes are text, GDScript | `--write-movie` + `--fixed-fps`, non-real-time ([docs](https://godot.readthedocs.io/en/4.0/tutorials/animation/creating_movies.html)); headless not verified | Skeleton2D + polygons; users call it "incomplete" in 4.4 ([forum](https://forum.godotengine.org/t/state-of-skeleton2d-in-godot-bone-2d-rigging-cutout-animations/65393)) | MIT | possible, no gain over our rig |
| **Rive** | runtime state machines; the editor is the authoring tool | no official headless video; Cloud Renderer is a paid editor feature; docs point to Remotion/Revideo ([Rive docs](https://rive.app/docs/runtimes/react/rendering-to-a-bitmap)) | yes | paid editor plans | no |
| **Spine** | JSON skeletons | through runtimes | yes, meshes + weights | using the runtimes needs a Spine Editor licence ([runtime licence](https://raw.github.com/EsotericSoftware/spine-runtimes/master/LICENSE)) | no (licence, GUI authoring) |
| **Live2D Cubism** | GUI editor; SDK | SDK render | yes, excellent face/body deform | small business under 10 M yen sales exempt; videos exported from the editor need no contract ([Live2D](https://live2d.com/en/?p=586)) | good for talking busts, but authoring is manual |
| **Moho** | Lua scripts; a community MohoMCP plug-in ([README](https://cdn.jsdelivr.net/gh/Kveto/MohoMCP@master/README.md)) | CLI render exists with limits ([forum](https://www.lostmarble.com/forum/viewtopic.php?p=213392)) | yes (smart bones) | paid, Windows/macOS | no for the cloud |
| **Lottie** (python-lottie + rlottie) | yes: JSON | frames via rlottie, then ffmpeg ([rlottie-python](https://pypi.org/project/rlottie-python/1.1.0)) | limited | licences not verified | only for UI-like graphics |

Toon Boom Harmony was not researched in this pass (paid, desktop).

Verdict: no outside tool beats our own rig on the things this project needs most (cloud, headless, chunked, tested, free).
The one capability we lack, **bending joints**, is a small addition to the rig (a two-bone limb drawn as one stroke or a
mesh warp of the limb piece), not a reason to adopt a second application. Synfig is the cheapest outside comparison if
the creator wants one; Blender Grease Pencil is the escalation for turns and perspective.

## 5. Making the character's parts (the missing step)

| Route | How | Quality | Risk |
|---|---|---|---|
| **A. Parts drawn by code (SVG)** | Claude writes each part as vector shapes with Wild Ink line weight, colours from `design/palette.json`, pivots and overlap built in; rendered through cairo/skia into the rig | crisp, perfectly consistent, bends cleanly (a limb is a stroke along two bones) | flatter than the painted plates; needs a shading pass (one shadow tone + rim light) to sit in the painterly world |
| **B. AI parts sheet** | the creator-approved character art is re-painted as a "parts sheet": every part separate on flat chroma, with hidden overlap areas and a knee/elbow drawn, then cleaned and (optionally) vectorised | painterly, matches the plates | needs repaints until parts line up; the model invents differences between parts |
| **C. Automatic decomposition** | Qwen-Image-Layered splits an image into RGBA layers (Apache-2.0, 20B, recommended 640 px bucket, 3-8 layers; hidden-region completion not stated) ([model card](https://huggingface.co/Qwen/Qwen-Image-Layered)); Bunraku (2026 preprint) turns one illustration into a Live2D rig with completed hidden regions, but code and weights are not stated as released ([alphaxiv](https://www.alphaxiv.org/abs/2607.27348)) | promising research | low resolution, layers are by object not by joint, needs a GPU pod; Bunraku not usable yet |
| **D. Joint finder** | Meta AnimatedDrawings' pose estimator finds joints on a drawn figure (MIT, archived) ([InfoQ](https://www.infoq.com/news/2023/04/meta-animated-drawings/)) | helps place pivots on B | archived, old Python |

Recommendation: **A for the body (limbs, torso, hands), B for the head and face set** (where the painterly appeal and
expressions matter most and parts are few), C watched, not adopted. This matches the master brief's C4 parts list (head,
torso, pelvis, upper/lower limbs, hands, feet, eyes, brows, mouths; hidden artwork under joints; pivots at the joints).

**Wounded or unusual characters** become data, not prompts: a wound is a decal layer on a part (bandage, torn sleeve,
bruise tone; kept cartoon, no gore), a limp is a cycle variant (shorter stance on one side, slower recovery), an arm in a
sling is a part swap with that arm's joints locked. Every variant is reusable for the next episode.

## 6. Quality, efficiency, risks

**Advantages**
- Identity is stable by construction (invariant 6): the same parts every frame, every episode.
- Physics and timing are measurable, so the ice test's checks (pop-in, foot slide, static drift, sound on contact) can
  gate every render; frame = function of its number fits the chunked render.
- Cost per usable second for character shots tends to zero after the one-off parts work; paid image-to-video is kept to
  the rare shot where its per-usable-second price is justified.
- Policy: YouTube's July 2025 update demonetises "mass-produced and repetitious" content while allowing AI that enhances
  original work ([CineD](https://cined.com/youtube-set-to-crack-down-on-ai-slop-with-monetization-policy-update),
  [Plagiarism Today](https://www.plagiarismtoday.com/2025/07/08/youtube-targets-inauthentic-content/)); an original rig and
  hand-authored acting is the stronger side of that line.

**Risks**
- **Style seam** (the biggest): a flat rigged figure on a painterly plate looks like a sticker. Mitigation: one palette for
  both, the plate's key light applied to the figure (shadow side + rim), contact shadows, matching line weight, a grade
  over the composite; judge it on the first PoC frame sheet before anything else.
- **Setup per character**: parts, pivots, bend zones and a test sheet (neutral, walk, run, reach, bend, jump, land, fall,
  turn, interaction, extreme face; master brief C4) take a few hours of Claude's work per new build; then reuse.
- **Limits of 2D cut-out**: turns, foreshortening, hands touching objects look artificial; plan shots around them (side
  and 3/4 views, cut on the turn, insert close-ups), escalate to Blender only if a story needs it.
- **AI-written animation can be wrong without anyone seeing it** (the ice test). Mitigation: automatic verification after
  every render; research shows the loop works: MoVer verified LLM-made SVG motion against predicates, 58.8 % right first
  time, 93.6 % with up to 50 correction rounds ([arXiv 2502.13372](https://arxiv.org/abs/2502.13372)); Apple's Keyframer
  found people describe motion best when decomposed per element ([arXiv 2402.06071](https://arxiv.org/abs/2402.06071v1)).
- **Ambient code motion can look mechanical**: sum two frequencies, add gusts, never animate everything at once (the
  limited-animation rule of PR #20's research doc).

**Efficiency (rough, to be measured in the PoC)**
- Code-made ambient motion and rigged acting: $0 per shot, CPU render (the rig PoC: 20 s clip in 12 s at 720p).
- AI plates: unchanged from today's paint plans.
- AI image-to-video: only per creator-approved shot with an estimate first (invariant 2).

## 7. Proposed next step (free, needs the creator's word)

One hero in Wild Ink, built by route A (+ the face from an existing approved picture if one fits): SVG parts with bend
zones, the rig extended with two-bone limbs, a test sheet clip (walk, run, jump, land, fall, turn by cut, a wounded limp,
point, talk) over one existing plate with code-made cloud and foliage motion, checked by the ice test's frame checks and a
neighbour-frame sheet. Output: a 15-20 s clip + frame sheet. Optional comparison: the same hero in Synfig with its
skeleton deformation. Nothing paid in either.

## 8. Result of the PoC (2026-10-22, the creator's "კი")

`explainer_engine/production/bend_rig.py` + `tests/unit/test_bend_rig.py` (10 tests). A 15-second shot, 1920x1080, 24 fps,
rendered on the CPU in about 2.5 minutes, nothing paid: one code-drawn hero (route A of section 5, Wild Ink line and
bulging eyes) walks in, stops, looks up, crouches, runs, jumps, trips on the landing, falls on his belly, scrapes the right
knee (a torn trouser and a red scrape appear at the impact frame), pushes up, kneels, stands, holds the knee, turns with a
squash-and-flip, and limps away. The plate is the ice test's own Seedream picture with the crowd painted out (reused, no
new spend); the snowfall and the trees bending in the wind are code.

- Bending: legs and arms are one ink shape over two bones (outlines first, fills after), so knees and elbows have no seam
  or hole at any angle; the wound is a decal on the part, the limp is the gait with a shorter, dipping, slower stance.
- Feet: the gait phase comes from the distance the hips travelled; planted feet hold one world position, knees come from
  inverse kinematics, the hips' bob from what the legs can reach; entering a gait, a foot the gait wants elsewhere steps
  there instead of sliding.
- Sound: footsteps, takeoff, landing and impact are read from the poses (stereo, -14.3 LUFS, peak -2.2 dBFS).
- `python -m explainer_engine.production.bend_rig check`: BR-1 foot slide, BR-2 under the snow, BR-3 planted foot reached,
  BR-4 bone lengths, BR-5 joint jumps, BR-6 in frame, BR-7 every footfall has its sound: 432 frames, 0 findings.
- Not solved here: the style seam (the hero is flat vector next to a painterly plate; a paper texture in screen space would
  "swim", so it needs a texture fixed to each part); one side view only (the turn is a flip); the hero is drawn by code,
  so his appeal is below the painted boards. Next: the same rig with the face and outfit taken from a creator-approved
  painted sheet (route B), and a texture per part.

Files: project files `explainer-engine/hybrid_model_2026-10-22/bend_poc/` and
https://huggingface.co/datasets/vano1919/tmr-artifacts/tree/main/explainer-engine/hybrid_model_2026-10-22/bend_poc
(`bend_poc.mp4`, `bend_poc_frames.jpg`, `bend_poc_check.json`, `ice_plate_clean.png`).

### 8.1 Version 2: a painted face on the rig's body (2026-10-22 18:47, the creator's call)

The creator: the body can be drawn by code, the face is hard, so let the image model paint the faces (one picture with
several variants) and let us build the body. Done free with faces already paid for: three expressions of one man cut
from the Wild Ink board (happy, scared, angry/pain; the fourth head on the board is another man), backgrounds removed,
`--heads <dir>` puts the matching picture on the rig by the expression timeline. Also from his notes: the turn is now
three drawings (side, front with the feet stepping round, the other side) instead of a squash-flip; the walk rolls
heel-sole-toes, the torso pitches with each step, the arms trail the legs and the head nods on a spring. `check`:
0 findings on 360 frames; 12 tests; -14.2 LUFS.

What a real face sheet needs (learned here): the board heads are about 100 px and front-facing, so they are soft at
1080p and look at the camera while the body walks in profile; grey paper stays between hair strands after the cut. A
production sheet should be one 2k picture of one face on a flat chroma background, side view and front view, 6-8
expressions plus 4-5 mouth shapes made by editing one approved head (so the face never drifts), no blink needed if the
eyes are drawn as separate layers.

Files: `bend_poc_v2.mp4`, `bend_poc_v2_frames.jpg`, `bend_poc_v2_check.json` and `heads/` next to the version 1 files.

### 8.2 Version 3: the body's paint from the picture too (2026-10-22 19:16, the creator's "უფასო ტესტი")

The creator sent a Wild Ink cave scene as the style reference for the world (environment, body and face shapes and
colours; not that scene) and asked whether this level is reachable and which tools are missing, 3/4 scenes included.
Answer given: in stills the level is already there (the picture is the model's); in motion every view (side, front, 3/4)
must be a painted sheet because a 2D rig cannot invent drawing (occlusion, perspective); free camera and perspective
turns stay out. Tools to add: textured parts in the rig (done below), per-view sheets from one character reference
(paid, 8-10 pictures per hero), a code mesh warp for 3/4 bodies (Live2D's principle, headless), a style-harmonising
grade, and pose-conditioned painting of rare key poses (the rig's skeleton drives the model; ControlNet-type on fal).

Done free, his choice: `Sheet` in `bend_rig.py`. `parts.json` names a painted picture and, per part, the painted bone
(`p0 -> p1`, source px) and its half-widths; the rig maps each part's paint onto its own bone by a similarity (mirrored
for the other facing), the capsule outline stays the rig's ink, a part narrower than the rig's (`rig_r`) is stretched
across. Einstein was cut from the reference with GrabCut (OpenCV) and his tunic, arm skin and head placed on the rig:
the paint follows the knee and elbow bends, the fall and the front turn. `check` 0 findings; 14 tests.

Learned: a figure painted in one 3/4 pose is a poor parts source (the arm crosses the tunic, the hair hangs over the
shoulder, the legs are cropped), so three bones had to be moved by hand and the torso is a stretched strip of fur. The
production sheet must paint every part straight, separate and complete, with the hidden overlap under each joint, on a
flat chroma, one view per sheet. Files: `bend_poc_v3*` and `einstein_parts/` next to the earlier versions.

### 8.3 The 30-second test cartoon: an Ice Age valley in 2.5D (2026-10-22 19:35-19:38, the creator's call)

The creator asked for a more spacious world, faces, clothes and expressions made by the image model in the reference's
style, and a 30 s cartoon with heroes; the body is still drawn by our rig. Klein was approved with a $1.5 ceiling and the
pictures were asked to be reusable for the next episode (a hundred people dropped into the Ice Age).

Paid: eleven Klein 2k pictures with the reference as the only style reference, $0.154 in the ledger
(`jobs/ice_cartoon/job-001_2026-10-22/run.json`): the valley in three layers (far sky and glaciers; the middle snowfield
on chroma; the near rock frame on chroma), a camp under a rock overhang, two original heroes as side/3-4/front turnarounds
(Dev, an office worker in a blanket cape; Marta, a hiker of 65), six expressions each in 3/4 and in profile, and a
suitcase sled. All on chroma green so they key cleanly and go to the asset library as they are.

Free, in code:
- `bend_rig.Sheet` mode `cut`: each part is the painting's own cut-out (alpha inside a polygon or capsule) carried whole
  by an affine map: along the bone it stretches to the rig's length, across it keeps the figure's scale, mirrored for
  the other facing. Feet are cut parts too. The outline is the painter's, not the rig's.
- The `three_quarter` view: the near hip and shoulder move back, the far ones forward and a little higher; the turnaround's
  3/4 drawing supplies the torso and the 3/4 face sheet the heads.
- `Build`: per-character bone lengths (Marta's legs are a third shorter than Dev's), swapped in while that hero is posed
  and drawn; gaits scale with the leg.
- `production/ice_short.py`: the 2.5D shot. Far layer at a fifth of the pan, middle layer with the camera, foreground
  rocks 1.35x faster; an object at depth d is drawn 1/d the size and nearer the horizon, so the sled shrinks away into
  the valley. Camera keys, soft shadows, snowfall, a snow burst at the fall, rope physics as a sagging curve, footstep,
  rope, hiss and impact sounds from the poses, -14 LUFS. `check` per hero: planted feet, reached feet, bone lengths,
  joint jumps, footfall sounds, heroes in frame.

Story (English on screen): Dev drags the sled he made from a suitcase, "Behold! The first sled of the Ice Age."; Marta:
"It's a suitcase."; he throws up his arms, lets go, the sled slides off; he chases it, trips into the snow; she walks
down, helps him up; "Great plan."

Learned: the turnaround's limbs come out cleanly when the painting shows them apart; the heads from a separate face
sheet are a slightly different drawing from the turnaround body (one sheet per hero with body and expressions together
is better); a near layer that is a full rock frame cannot be tiled, so foreground rocks must be painted as separate
props; the face sheets' hat colour differed from the turnaround's once (green vs grey), so a hero's colours must be
fixed in one reference first. Voice: lines are captions in this cut; the ElevenLabs take waits for the creator's word.

### 8.4 Physics and montage, version 2 (2026-10-22 20:32-21:50, the creator's option "0+1 + paid ≈$0.50")

The creator (20:32): ignore the visuals here; the physics and the editing are completely off from reality. The frame-by-frame
audit and the plan are in the Claude Doc "ფიზიკა და მონტაჟი: ანალიზი და გეგმა"; he chose stages 0+1 (free) plus the stage 2
paid test (one 5 s clip on fal).

Stage 0+1, free, in code (`production/physics2d.py`, `production/mocap.py`, `production/gaits.json`, `ice_short.py` rewritten):
- Bodies instead of eased keys (pymunk, MIT): the terrain is a profile of slopes along a lane that bends away from the camera;
  the sled is a box with mass and friction dragged on a rope (a slide joint) by the hand, the arm that holds it gives (a
  damped spring, ~400 N/m, so the gait's bob does not yank the sled every step); the sled coasts over the lip, slides down
  the 10-degree slope and taps Dev's heel (simulated contact, 10 px/s), is freed when the heel lifts, runs down with real
  gravity; Dev's trip is a ragdoll from the rig's skeleton (jointed bodies, angle limits, muscle tone fading in 0.35 s, a
  reach reflex of the shoulders), and the get-up starts from where the ragdoll came to rest. Every contact, takeoff and
  landing is an event; sounds come from the events and the simulated speeds.
- Gait from motion capture: `mocap.py` parses a BVH clip (CMU Graphics Lab Motion Capture Database, free for any use; the
  cgspeed BVH conversion), runs forward kinematics, projects onto the body's own sagittal plane, detects contacts by foot
  stillness and measures each cycle: stride, stance shares, swing arc, hip height and bob, lean, sway, arm swing, elbow,
  heel-strike and toe-off pitch, in leg lengths so they retarget to the rig's shorter cartoon legs. Measured on 07_01 (walk),
  07_12 (brisk walk), 09_01 (run), 02_03 (jog) -> `gaits.json`; `bend_rig.measured("walk")` and `("run")` drive Dev.
  The measured walk has a longer stride (0.78 vs the hand-made 0.62 body heights), a 58-degree toe-off, stance 0.58/0.55;
  the run stance 0.29 with a flight phase and a 13-degree lean.
- The camera as an operator: per shot a critically damped second-order follow with lead room from the subject's speed, a slow
  push-in, a fit zoom; ten shots with reaction shots on the lines and cuts on actions. Rule BR-10 now means "the camera
  stopped dead while its subjects moved".
- Checks: BR-3/4/5/7/8/9/10/11/12/13 and IS-1 (scoped to the shot's subjects): 0 findings on the full 30 s and on the clip.
  Tests: `test_physics2d.py` (terrain, flat vs slope, the taut rope and the giving arm, the heel bump, ragdoll bone lengths,
  the operator never dead-stops), `test_mocap.py` (BVH parse and FK, a synthetic walk's cycles, the rig's measured gaits
  never slide), `test_ice_short.py` (projection, inverse, lane, terrain); the whole suite 671 passed.

Stage 2, paid (fal, the card's ≈$0.50; ledger `jobs/ice_cartoon/job-002_2026-10-22/run.json`):
- Wan 2.2 Animate ("move", 480p, $0.04/s): the fall clip was refused by fal's content checker before generation ($0); the
  walk clip (0.5-5.5 s) generated for $0.20. Result: unusable. The model expects a person filling the frame; from a small
  2.5D cartoon figure it extracted no pose and painted a smeared portrait of the reference (file
  `hybrid_model_2026-10-22/ice_cartoon/v2/fal_wan_animate_walk.mp4` + sheet).
- Kling 2.6 Motion Control ($0.07/s): refused the reference image's aspect ratio (fixed by padding), then refused the fall
  clip ("no complete upper body detected in the video"); the third try on the close-up clip (8.6-13.6 s, Dev filling the
  frame for 2.8 s) generated for $0.35 (`v2/fal_kling_motion_control_close.mp4` + sheet, 1136x1824, 30 fps). Result: the
  hero stays ON MODEL (Dev's design, cape, tie, hair, the Wild Ink line, as drawn in the reference), the arms-out "Behold"
  and the wide pose are followed, the face acts (a grin). It paints the hero alone on the reference's plain background, in
  the reference's portrait orientation; after the cut to the wide shot (3.4 s) it kept a small figure walking on a blank
  snowfield, so one shot per call. The sound and the plate are ours to add.
- Verdict: motion-transfer models are built for full-frame humans. Wan 2.2 Animate gives nothing from a small 2.5D figure.
  Kling 2.6 Motion Control re-animates our hero from ONE reference picture when the hero fills the frame, and keeps the
  style: a real tool for close-up inserts (a reaction, a gesture, a face acting) driven by our rig's motion as the
  reference video, composited onto our plates (a chroma or plain reference background keys out). Cost $0.07/s, one shot per
  call, portrait or landscape by the reference. Wide and medium shots, physics, contacts and continuity stay with the rig.
