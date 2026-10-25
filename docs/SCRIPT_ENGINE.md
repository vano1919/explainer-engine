# Script engine v1 (2026-10-24)

**What it is.** The one path from a topic to every prompt of an animated episode, with nothing left to improvise: each
dimension of a prompt or a script is either set by a rule with a source or marked as a variant under test. ვანო asked for
it on 2026-10-24 ("zero improvisation; where a rule is missing, research it, then write it"). The first episode written
on it is [`examples/napoleon_vs_genghis/`](../examples/napoleon_vs_genghis/) (214 shots, 15:00, 0 FAIL, 0 REVIEW).
The evidence for the new numbers is [research/SCRIPT_ENGINE_V1_2026-10-24.md](research/SCRIPT_ENGINE_V1_2026-10-24.md).

## 1. The pipeline

| # | Stage | Input -> output | Rules | Tool / check | Who approves |
|---|---|---|---|---|---|
| 1 | Research | topic -> claim map (id, text, source, kind fact / estimate / invented) | invariant 5; ZI-02, ZI-04 | the `claims` block of the cards | - |
| 2 | Skeleton | claim map -> the 16 segments of template D with their clock | [STORY_ENGINE.md](STORY_ENGINE.md) template D, ST-14..ST-16 | `scripting/story_lint.py` | creator (scenario, OR-15) |
| 3 | Shot cards | skeleton -> `film_shots/1` cards: narration, dialogue, blocking, action, tier, claims | [SHOT_PROMPTS.md](SHOT_PROMPTS.md) KP-15..KP-43 | `python -m explainer_engine.scripting.film_shots check` | creator (script) |
| 4 | Script | cards -> the readable script and the narrator's lines; the shot list with every prompt under its shot | ZI-01 | `film_shots script --out script.md`, `film_shots shotlist --out shotlist.md` | - |
| 5 | Prompts | cards -> hero-sheet, keyframe, next-pose, cut, last-frame and video prompts, gate cards | ZI-01, ZI-05, KP-01..KP-14 | `film_shots compose --out prompts.json` | creator picks each new hero from its sheet (invariant 6) |
| 6 | Pictures | prompts -> sheets, masters (Qwen-Image-2512 + style LoRA), poses and cuts (Edit-2511 + scene LoRA) | ZI-06; the keyframe gate of PR #22 | gate cards in `prompts.json` | paint plan + provider (D-50) |
| 7 | Clips | first (and last) frame + video prompt -> clip with native audio | ZI-03, ZI-06; KP-36, KP-37 | video QA of PR #22 | paid run approved first |
| 8 | Narrator | `script.md` narrator lines -> ElevenLabs read + word timings | skill `elevenlabs-voice` | `audio/scribe_words.py` | - |
| 9 | Edit | clips + read -> 15-minute cut, 1440p release (test cuts at the base size, LT-18) | [EDITING.md](EDITING.md) | `production/assemble.py` | creator approval before upload |

## 2. The rules

| ID | Rule | Why | Check |
|---|---|---|---|
| ZI-01 | **Every prompt is composed from a card**: hero sheets, keyframes, next poses, cuts, last frames and video prompts come only from `film_shots compose`; a prompt typed by hand is not used, and a gap in the composer is fixed in the composer (with a test), never patched in one prompt | one card, every model's grammar the same (KP-30) | [code] `compose` |
| ZI-02 | **A number needs a claim.** A narrator line with a number (a digit, a year, "hundred", "half", "nine") lists claim ids, and every listed id is in the claim map with a source; a fact the story invents is a claim of kind `invented` | invariant 5: no unsupported claims | [code] FAIL |
| ZI-03 | **Every shot has an animation tier** (`hold`, `light`, `full`, KP-37) under `"engine": "script_engine/1"`; the tier picks the model (section 3) | the critic's plan and the measured cartoons disagreed; the card has to say which budget it spends | [code] FAIL |
| ZI-04 | **Inventions are listed.** Everything the story makes up that a viewer could take for history (the premise, a person's presence, a battle and its numbers, every line of dialogue) has an `invented` claim, and the description of the video says the story is fiction | invariant 5; YouTube's disclosure is decided per video (CLAUDE.md) | the claim map; editorial |
| ZI-05 | **A variant under test is named, not guessed.** Where a test is still running (sizes in words or numbers, 24 or 12 fps, the tier shares), the cards use the variant in section 3 and the package names it; the winner of the test replaces it in section 3 and nowhere else | the creator 2026-10-24: "use the one that looks ideal in theory, say which" | section 3 |
| ZI-06 | **A LoRA runs only on its own base**: the style LoRA on Qwen-Image-2512 (sheets and masters), the scene LoRA on Edit-2511 (next poses, cuts, last frames), never both in one call; each shot is made once and redrawn only when its check fails | the style-weight test 2026-10-24 (identity swaps with the style LoRA inside Edit); LT-18 | [code] `lora` field of every prompt |

## 3. Variants in use (replace a row when its test reports)

| Dimension | In use now | Alternative under test | Where it is set |
|---|---|---|---|
| Story structure | template D, 16 segments, 900 s | - | [STORY_ENGINE.md](STORY_ENGINE.md) |
| Figure size in a picture prompt | words ("a third", "most of the frame height"); decided by test v2 2026-10-24 (numbers were drawn as rulers and sized no better) | - | KP-32 |
| A hero's tag in one prompt | the full tag every time the hero is named | the full tag once, then a short name ("the old man"): one figure came out twice in 4 of 4 pictures where a tag repeated three times (test v2, a hypothesis) | `film_shots._people` |
| Keyframe | Qwen-Image-2512 + `wldnk style` LoRA, bf16, 1280x720, 24 steps, true CFG 4 (the settings the frozen LoRA was judged at) | 1664x928 at 50 steps (the base model's own 16:9 default) | the LoRA thread's params file |
| Keyframe and sheet words | `wldnk style, <the moment>`, at most 40 words, no tail, no camera, size or position (LT-65): the place's head, the lead (tag, or its head phrase when words run out) with the caricature body words (`style.body`) and the action at its peak, one reaction, the light, then every other figure (KP-45: everyone by the tag's head, their reactions, then costume traits; each tag once, LY-09); sizes, sides, heights, supports, free space and counts are the gate card's layout for the composition of assets (ASSET_COMPOSE), whose first frame keeps the start pose (KP-16) | the long composed layout sentences (v1: up to 337 words) and the v5 caption tail (90 words), retired by PR #22 c032f76 | `film_shots.keyframe_prompt`, `MOMENT_WORDS_MAX` |
| Gate cards | one card for every drawn frame: each first frame (keyframe, next pose, cut; `master` names the picture it was edited from, KG-13) and each guided last frame (`<id>.last`, a lead who exits left out); besides people, relations and free space, a card carries `things` (exact counts from `frame.things` {name: count}, KG-01: one bus is one bus) and `absent` (the world's top-level `absent` plus `frame.absent`, KG-21) | cards for keyframes and cuts only, with no object counts or absent things (the Qwen-Image-2.1 style LoRA drew a second bus and a city, 2026-10-25) | `film_shots.gate_card`, `gate_cards` |
| Episode look and absolutes | every style-LoRA prompt ends with the episode's colour-and-light phrase (`style.look`: a look file or its phrase and `lights`; a shot names a variant with `frame.look`), added by `episode_look.apply`, never by hand (AC-16..AC-17); the moment shrinks so the whole prompt keeps 40 words; the negative is exactly `style_prompt.NEGATIVE` and the inference settings `style_prompt.INFERENCE` (LT-66) | colour words written per prompt, a negative per episode | `film_shots._look`, `style_check` |
| Next pose, cut, last frame | Qwen-Image-Edit-2511 + scene LoRA v1 (checkpoint 500-750), the training caption's prefix | - | KP-07, KP-08, KP-27 |
| Video model by tier | `full` -> LTX-2.5 dev (acting, every line, every peak); `light` -> LTX-2.5 distilled (breath, glance, a turn of the head); `hold` -> no video model: the keyframe with our camera move | the cheaper model on `full` shots, after the 1-minute film | `film_shots.MODEL` |
| Clip length | at most 10 s; a longer acted shot draws its last frame | 12-15 s with a video LoRA | BP-108 |
| Frame rate and frames | 24 fps, 8k + 1 frames covering the shot | 12 fps or 24 fps drawn on twos (the creator's three-variant test film) | `film_shots.frames`, LT-07 |
| Clip size | test films 1280x704 (LTX sizes are multiples of 32), never upscaled; release clips upscaled to 2560x1440 | release clips rendered at 1920x1088 before the upscale | LT-18 |
| Video prompt | one present-tense paragraph: the style sentence, the action start -> peak -> settle, the face, the reactions, the line in quotes with its voice, who stays in frame, one camera sentence, the sounds | - | KP-10..KP-12, KP-18, BP-102 |
| Acting fallback (KP-43) | a line whose take fails the acting check twice: over the speaker's shoulder onto the listener (the line plays on the reaction), or the speaker's hands for a line said to the room | redraw the same shot a third time | `film_shots._acting` |
| Dialogue audio | LTX native audio, the voice described in words on the cast card (`voice`) | audio-to-video conditioning on one voice take per hero | the cast cards |
| Narrator | ElevenLabs, the script's narrator lines, first take | - | skill `elevenlabs-voice` |
| Tier shares | hold at most 10 %, light about a sixth, full the rest | the critic's 40 / 35 / 25 % on the test film | BP-109 |

## 4. The master prompt (what the writer is given)

The writer of an episode (a person, the `story-architect` and `scene-writer` agents, or a chat) gets this brief, filled in.
Every line points at a rule; nothing in it is new.

1. **Topic and premise.** One sentence of what if, one dramatic question answered at the end (ST-01), and the mixed
   outcome (the channel tells stories, the ending is not a clean win).
2. **Research first.** Write the claim map before a line of story: each historical fact with its source, each invention
   marked `invented` (ZI-02, ZI-04). The heroes' characters come from the sources (how they decided, what they wanted,
   what they feared), the armies' or systems' abilities from numbers with sources.
3. **Skeleton.** Fill template D's 16 segments with what happens in each, in the clock template D gives.
4. **Cards.** Write the shots in `film_shots/1`: a beat for each, the frame (size, place, light, camera), the blocking
   (who stands where, on what, how large), one action with its start, peak and settle, the reactions, the line or the
   narrator's words, the sound, the tier and the claims. A spoken line fits its shot (BP-100); a scene opens wide (KP-26);
   the narrator never describes the picture (KP-20); a scene changes the situation (SC-02).
   **Action, reaction, consequence**: judge a scene by that chain, not by its shot count. A plan is shown while it is
   told (KP-42: the scouts at the wagons while the khan asks what the French eat), the other side's move runs in
   parallel with the hero's win (cross-cutting: the camp burns while Napoleon smiles), the cost lands on screen (spent
   horses, men eating grass), and the cold open shows pieces of the fight to come (KP-41). Talk never rests on AI faces
   alone (KP-43).
5. **Check.** `film_shots check` until 0 FAIL; every REVIEW left is answered in the package.
6. **Compose.** `film_shots compose` and `film_shots script`; the package for the creator holds the skeleton, the script,
   the prompts, the variants in use (section 3) and the claim map.

## 5. Commands

```powershell
.venv\Scripts\python examples\napoleon_vs_genghis\build_cards.py          # the shot list -> film_shots.json
.venv\Scripts\python -m explainer_engine.scripting.film_shots check   examples\napoleon_vs_genghis\film_shots.json
.venv\Scripts\python -m explainer_engine.scripting.film_shots compose examples\napoleon_vs_genghis\film_shots.json --out prompts.json
.venv\Scripts\python -m explainer_engine.scripting.film_shots script  examples\napoleon_vs_genghis\film_shots.json --out script.md
.venv\Scripts\python -m explainer_engine.scripting.film_shots shotlist examples\napoleon_vs_genghis\film_shots.json --out shotlist.md
```
