# P12 shot prompts (WP-1b, hand-written)

The eight LTX-2.5 `video` prompts of pod P12b (stages L1, L3, L2 and AV in
[`p12b.json`](../../explainer_engine/training/pods/p12/p12b.json)). They are written by hand from the keyframe
descriptions in `jobs/kf/descriptions.md` (looked at by the session, 2026-11-01) and follow
[SHOT_PROMPTS](../SHOT_PROMPTS.md) KP-01..KP-14 (plus the parts of KP-15..KP-25 that apply to a video prompt). The machine
copy is [`p12b_prompts.json`](../../explainer_engine/training/pods/p12/p12b_prompts.json)
(`"prompt_source": "hand, docs/pods/P12_PROMPTS.md"`); the session merges it into `p12b.json`, this work package does not
edit `p12b.json`.

## Fixed parts (the same in every prompt)

- **Style sentence (KP-10, KP-24)**, first in all eight prompts, word for word:
  `Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours.` (the sentence of the worked
  `disco_val` prompt; it asks for no smooth, fluid or natural motion).
- **Identity tags (KP-01, KP-15, KP-22)**: no story names. The emperor is "the short man in the black gold-edged bicorne
  and dark-blue coat with a white vest and gold epaulettes"; the general is "the grey-haired man with a grey moustache in
  the red-plumed bicorne" (with "gold-embroidered blue coat" where the face is not seen); the ship's man is "the old
  bearded sea captain in the black tricorn with a scar". "man in" / "man with" passes the bare-role check of
  `shot_prompt_lint` (KP-01). A shortened tag is used where the keyframe hides the coat (tent_s1, tent_s2, tent_s3,
  tent_s4's background figure, av1). A person the actor looks at is named by tag too, never as "the man in front of
  him" (tent_s1).
- **Camera (KP-04, KP-38)**: `Static camera.` in every prompt, the only camera sentence.
- **In frame (KP-03)**: every prompt says the heroes stay in frame; no prompt sets `exit`.
- **Nobody speaks (KP-20)**: the six silent shots say `Nobody speaks.` so LTX does not fill the track with chatter.
- **Length (KP-06)**: the render is 121 frames at 24 fps (`ltx.render` in p12b.json), about 5 s, under the 8 s REVIEW line.
- **Negative (KP-09)**, the same for all eight, `film_shots.NEG_VIDEO` word for word; it names none of our own style:
  `text, watermark, logo, subtitles, extra people, duplicated character, morphing face, melting body, deformed hands, extra fingers, flicker, still image`.
  Note: L1, L2 and L3 run the distilled transformer at `cfg: 1.0` (p12b.json `ltx.render`), where the negative is
  ignored (KP-09 scope); the prompts therefore write the end state they want. AV loads the dev transformer
  (`ltx.av_files`), where the negative can act if the AV stage runs CFG > 1.
  # UNVERIFIED: whether p12c_ltx.py passes this negative to the pipeline; the session wires it when it merges.

## The prompts

| Shot | Stage | Prompt | KP rules used | `neg` (KP-09) |
|---|---|---|---|---|
| tent_s0 | L1, L2 | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The short man in the black gold-edged bicorne and dark-blue coat with a white vest and gold epaulettes, on the left, leans forward over the map table, slams one hand flat on the map, then straightens up and clasps his hands behind his back; the grey-haired man with a grey moustache in the red-plumed bicorne, on the right, only lifts his chin. Both men stay in frame. Static camera. Nobody speaks. Sounds: a hand slapping the table, canvas creaking in the wind, crickets outside. | KP-01, KP-02 (the left man acts, the right man reacts small), KP-03, KP-04, KP-06, KP-09, KP-10, KP-11 (3 sounds), KP-12 (lean, slam, straighten), KP-15, KP-20, KP-22; KP-13 risk: both men are small in this wide, so the acting may freeze (a measured outcome, KP-14) | NEG_VIDEO |
| tent_s1 | L3 | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The grey-haired man with a grey moustache in the red-plumed bicorne, in the centre, jabs his right forefinger down onto the map twice, then raises his eyes and stern brows to the short man in the black gold-edged bicorne, then pulls his hand back to his chest; the short man in the black gold-edged bicorne, seen from behind on the left, only tilts his head toward the map. Both men stay in frame. Static camera. Nobody speaks. Sounds: a finger tapping on paper, the lantern creaking on its pole, crickets outside. | KP-01 (the man he looks at is named by tag, not by role), KP-02 (the general acts; his pose already points, so the action goes to the figure posed for it), KP-03, KP-04, KP-06, KP-09, KP-10, KP-11, KP-12 (jab, raise, pull back), KP-15, KP-16 (starts from the pointing pose), KP-17 (brows, eyes), KP-19 (two faces at most), KP-20 | NEG_VIDEO |
| tent_s2 | L3, image of av1 | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The short man in the black gold-edged bicorne and dark-blue coat with gold epaulettes, facing the camera, lowers his brows into a deeper frown, then jerks his chin up as his eyes widen and his jaw sets hard, then settles into a still, narrow-eyed stare with his mouth closed. He stays in frame. Static camera. Nobody speaks. Sounds: the lantern hissing, canvas flapping softly in the wind. | KP-01, KP-02 (one actor), KP-03, KP-04, KP-06, KP-09, KP-10, KP-11 (2 sounds), KP-12 (frown, jerk, settle), KP-13 (close-up), KP-17 (brows, eyes, jaw, mouth; no feeling word), KP-20 | NEG_VIDEO |
| tent_s3 | L1, L2 | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The grey-haired man in the red-plumed bicorne and gold-embroidered blue coat, seen from behind, strides toward the tent door at the back, grabs the canvas flap with one hand and stops, then turns his head back over his shoulder toward the map table. He stays in frame at the door. Static camera. Nobody speaks. Sounds: boots thudding on the carpet, the canvas flap rustling, crickets outside. | KP-01, KP-02, KP-03 (the keyframe walks him to the door; the prompt stops him at the flap and keeps him in frame, no exit verb, no `exit`), KP-04, KP-06, KP-09, KP-10, KP-11, KP-12 (stride, grab, turn), KP-15, KP-16 (starts mid-walk), KP-20 | NEG_VIDEO |
| tent_s4 | L1, L2 | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The short man in the black gold-edged bicorne and dark-blue coat with a white vest and gold epaulettes, front right, grips the sword hilt at his side, squares his shoulders and lifts his chin, still looking to the left, then lets his hand rest on the hilt; the grey-haired man in the red-plumed bicorne, small by the pole in the background, only turns his head toward him. Both men stay in frame. Static camera. Nobody speaks. Sounds: the sword hilt clinking, the lantern creaking, wind on the canvas. | KP-01, KP-02 (the large foreground man acts, the small background man reacts), KP-03, KP-04, KP-06, KP-09, KP-10, KP-11, KP-12 (grip, square, lift, rest), KP-13 (the actor is the large figure), KP-15, KP-20 | NEG_VIDEO |
| ship_s2 | L3 | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The old bearded sea captain in the black tricorn with a scar draws in a breath, then throws his head forward and roars a wordless cry with his mouth wide open while he yanks the ship's wheel hard with one hand, then closes his mouth and grips the wheel, his chest heaving. He stays in frame. Static camera. Sounds: his wordless roar, waves crashing on the hull, the wheel creaking. | KP-01, KP-02, KP-03, KP-04, KP-06, KP-09, KP-10, KP-11 (the roar, the loudest, named once), KP-12 (breath, roar and yank, settle), KP-16 (the keyframe is already at the peak: the prompt adds a breath before it so the clip has a start), KP-17, KP-18 (a wordless roar, no quoted words, no speech verb); no `Nobody speaks.` because he roars | NEG_VIDEO |
| av1 | AV (image: keyframe tent_s2) | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The short man in the black gold-edged bicorne and dark-blue coat with gold epaulettes, facing the camera, starts with a frown and his mouth closed, then opens his mouth and talks straight into the camera, his lips moving with every word, raises his brows and nods his head once firmly on the strongest word, then closes his mouth and settles back into the frown. He stays in frame. Static camera. Sounds: his voice only, a faint lantern hiss. | KP-01, KP-02, KP-03, KP-04, KP-06, KP-09, KP-10, KP-11, KP-12 (open, raises his brows and nods, settle), KP-13 (close-up), KP-17, KP-18 (one speaker in a close shot, a settle at each end; the words come from the ElevenLabs take, so no quoted text, per the work package), KP-19 (one face) | NEG_VIDEO |
| av2 | AV (image: q1 napoleon, front-right quarter view, 0.8) | Hand-drawn 2D cartoon animation with bold black outlines and bright flat colours. The short man in the black gold-edged bicorne and dark-blue coat with a white vest and gold epaulettes, turned a quarter to the right, starts with his mouth closed, then turns his eyes to the camera, opens his mouth and talks to the camera, his lips moving with every word, raises one hand to his chest on the strongest word, then lowers the hand and closes his mouth. He stays in frame. Static camera. Sounds: his voice only. | KP-01, KP-02, KP-03, KP-04, KP-06, KP-09, KP-10, KP-11, KP-12 (turn, talk, raises one hand, lower), KP-17, KP-18 (as av1: words from the audio take, no quotes), KP-19, KP-25 (no place: the image is a full figure on plain white) | NEG_VIDEO |

## Notes for the session

- **No story content added** beyond the descriptions: the actions are acting beats (start, peak, settle, KP-12) on the
  poses the keyframes already show; no prompt adds a person, a prop or a place.
- **av1/av2**: no dialogue text and no speech verb from the lint's list; "talks to the camera" and "lips moving with every
  word" describe a person speaking to camera. The voice comes from the ElevenLabs takes in `ltx.av.takes`, still
  placeholders. `shot_prompt_lint` may still REVIEW KP-18 on the AV shots if it counts "talks" as speech; that REVIEW
  is expected here because the line is in the audio, not in the text.
- **Expected lint result**: 0 FAIL. KP-12: every prompt has a verb from the lint's `STRONG` list (av1 "raises his
  brows", av2 "raises one hand", which replaced "his brows rising" / "one hand rising" so that av1 and av2 no longer get a
  KP-12 REVIEW). KP-25: BP-102 `video_words` is [30, 130] and all eight prompts sit inside it, so no word-count REVIEW.
  Remaining possible REVIEWs: KP-13 on tent_s0 (editorial, the keyframe is a wide) and KP-18 on av1/av2 (see above).
  Run `python -m explainer_engine.scripting.shot_prompt_lint` on a `{"shots": [...]}` file built from the table (kind
  `video`, seconds 5, `neg` = NEG_VIDEO) before the pod starts.
