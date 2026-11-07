# Scene reuse, references, identity and dialogue (SR- / RF- / ID- / DL-)

The creator's decision, 2026-11-07 18:08 UTC (cmsg_01Hnu5zB86sjUj5GtTgaUkPWWGFzRWxBehT3gJoao5ggGZ), after the day's Qwen-Image-2.1
tests (v1-v7, route_test_2026-11/sa_test/ on HF) and two research notes
([E0 audit](research/stoneage_pilot_2026-11-07/E0_AUDIT_2026-11-07.md),
[scene-reuse research](research/stoneage_pilot_2026-11-07/SCENE_REUSE_RESEARCH_2026-11-07.md)).

What the tests showed (measured, not assumed):
- Qwen-Image-2.1 edit keeps the composition of Image 1 and **cannot turn the camera** of a painted place (asset test: "left/right/back"
  views came back as copies of the front).
- A shaded Blender render as Image 1 pulls the picture toward 3D realism and weakens the xworld style (test 1, cave CC0: edge density
  7.55 % -> 4.22 %); the LoRA itself is healthy (E0: all 192 adapters non-zero, gate_up merge correct).
- A **fixed, verbatim appearance text** per person and thing kept Marcus, Ura, the hunters and the mammoths identical across 9
  independent pictures (v5/v6), and a **verbal scene description** (who is where, who sits/kneels/turns away) restored the layout (v6).
- A second reference image in a different style confuses the model (the creator's observation, 17:03).

## 1. Scene reuse (SR-)

| ID | Rule | Severity |
|---|---|---|
| SR-01 | **One location is shown sharp from one view only.** A location may appear again only (a) with its background **blurred** (a close-up or medium-close dialogue/reaction shot, depth of field so the place reads as colour and light, not as walls and objects), or (b) **not in consecutive shots**, with at least one shot of another place or an insert between them, so the viewer cannot compare the two. | FAIL |
| SR-02 | A location's sharp view is its **master**. Every sharp shot of that location reuses the master's camera: a push-in, pan or crop of the same picture (AC-12/AC-13, ED-02), never a new angle of the same set. | FAIL |
| SR-03 | A change of story beat that needs a new look moves to a **new place** (another part of the location counts as a new place when it has its own landmarks, e.g. the cave's "fire hall" and "handprint wall"), not to a new angle of the same place. | REVIEW |
| SR-04 | An **insert** shows a thing, not a place: hand, phone, bone, footprint, painted palm, on a blurred or neutral ground with at most two landmark details. Inserts do not count as a view of the location. | REVIEW |
| SR-05 | Change inside one place is carried by **light, weather, smoke and the actors** (fire flares or dies, white flash, snow thickens), never by new geometry. | REVIEW |
| SR-06 | **LTX clips never show the same location from a different view** (one location = one LTX view, the creator 16:41). A clip of a location starts from that location's master or from a blurred-background close-up. | FAIL |
| SR-07 | **Angle register.** Every visual script ends with a table: location -> master id, the shots that reuse it sharp (same camera), the blurred shots, and the inserts. More than one sharp view per location fails the script before any paid step. | FAIL |

## 2. References (RF-)

| ID | Rule | Severity |
|---|---|---|
| RF-01 | **No rendered (Blender / 3D) picture is a reference.** Layout comes from the verbal scene description (ID-04), not from a render. Blender stays available for other uses only by the creator's word (depth/line control, a later test). | FAIL |
| RF-02 | **References are our own generated pictures**, in the house style: a character sheet (front, 3/4, side, back), a location master, a prop sheet. A reference in another style (photo, render, older look) is not used. | FAIL |
| RF-03 | **Which picture may serve which shot** (to be measured; the first 10 pictures test it): a character sheet -> every shot of that character (identity); a location master -> that location's blurred close-ups and inserts (palette, light), never a new sharp angle of it (SR-02); a prop sheet -> the prop's inserts. The master is Image 1 only for a crop/push-in of itself; otherwise it is a later image (palette donor). | REVIEW until measured |
| RF-04 | At most 3 reference images per picture (Qwen 1-3, CT-05). Order: the shot's own place reference first (if any), then the people in the order they are named. | FAIL |
| RF-05 | Every reference is approved by the creator before it is used (AC-02), and a generated shot is never the base image of the next (CT-09). | FAIL |

## 3. Identity control (ID-)

| ID | Rule | Severity |
|---|---|---|
| ID-01 | **Cast registry, verbatim.** Every person, animal and recurring prop has one appearance text (age, height, hair, skin, each garment with its colour, shoes, distinguishing marks; for animals size and colour). The prompt copies it word for word; no shot rewrites it (extends CT-02). | FAIL |
| ID-02 | **Registry text names colours by plain words** and fixes proportions in metres, so two shots can be compared (Marcus 1.75 m, Ura 1.80 m, hunters 1.70 m, mammoths 3.5 / 3 / 2 m). | REVIEW |
| ID-03 | **Distinct silhouettes.** No two cast members share hair colour, garment colour and headgear; every hero has one unmistakable mark (Ura's deer-skull mask with antlers, Marcus's grey hoodie and white sneakers, the hunters' grey / brown / spotted furs). | REVIEW |
| ID-04 | **Prompt in two parts** (the creator 17:04 and 17:30): the **scene** (camera size and height, who is where, who sits / kneels / stands / turns away, near is large and far is small, the landmarks and light) and the **appearance** block (ID-01, identical in every picture). The style line opens it (UR-22). | FAIL |
| ID-05 | **Faces.** Every hero's text names the face (shape, nose, brows, beard or none) so faces stop drifting; extras get one face word each. Faces are checked on the contact sheet (CT-14) and a hero who changes face is redrawn. | REVIEW |
| ID-06 | LoRA weight is one per episode and recorded. **Standard: xworld_v2 at 1.0** (the creator 2026-11-07 19:25 UTC: "0.7 -> 1"); the day's earlier tests used 0.7 (v1, v5, v6), v7-v10 used 1.0. 1.2 is untested. | REVIEW |

## 4. Dialogue shots (DL-) — extends ED-14, BP-113, AC-15

| ID | Rule | Severity |
|---|---|---|
| DL-01 | A dialogue shot is a close-up or medium close-up on a **blurred** version of the location (SR-01 a): the hero cut-out from the character sheet / picture over the master blurred and slightly shifted, same light colour. | FAIL |
| DL-02 | **Proportions are kept on every cut-out:** scale by the registry height and the shot size, never squash or stretch; the head stays the same size across a scene's shots of the same size; the frame edge cuts at a natural line (chest, waist), never at a joint (AC-15). | FAIL |
| DL-03 | **Mouth:** at least 3 mouth states (rest, mid, wide; six visemes where available, `audio/visemes.py`) switched on the line's phonemes; the mouth never moves on silence; a take whose mouth fails twice uses a mouth-hidden fallback (BP-113). | FAIL |
| DL-04 | **The body is never frozen:** a 3-5 s breathing cycle (1-2 % scale on the chest), a blink every 2-6 s, a head tilt or nod on stressed words, and a slow camera push (ED-08 at rest at the cut). | REVIEW |
| DL-05 | **Listener reactions** on every 2nd-4th line and always on news, an insult or a reveal (ED-14); at most 4 lines in a row before a silent reaction, insert or cutaway (BP-113). | REVIEW |
| DL-06 | Two-shots are the master (SR-02) or an over-the-shoulder with the near person blurred; never a new sharp angle of the place. | FAIL |

## 4a. LTX clips in the edit (LX-) — the creator 2026-11-07 19:17 UTC; extends KP-16, KP-36, BP-108, BP-164

| ID | Rule | Severity |
|---|---|---|
| LX-01 | **Handles:** every clip is generated about 0.5 s longer at the head and 0.5 s at the tail than its slot (frames rounded up to 8k+1), so the edit can choose its in and out points. | REVIEW |
| LX-02 | **The first frames are not used:** the head handle (the model's warm-up, where the picture can morph away from the first frame) is trimmed; the shot starts at the first frame after the warm-up that still matches the keyframe (BP-164 frame0 check on the kept first frame). | FAIL when the kept head morphs |
| LX-03 | **The last second lands in the cut:** the clip's settle (KP-16) sits on the out point; the cut is on the settle or on a motivated action beat, never mid-morph; a frozen tail (BP-164) is trimmed, not shown. | REVIEW |
| LX-04 | **Speed:** a clip may be retimed in the edit between 0.85x and 1.15x (frame blending / optical flow, pitch-free since clip audio is not used for speech) to fit its slot; outside that band it is regenerated with a length that fits. Never retime a shot with visible lip-sync. | REVIEW |
| LX-05 | **Joins:** a clip that follows or precedes a still of the same picture starts or ends on that picture's framing (ED-02), and the camera is at rest at the cut (ED-08). | REVIEW |

## 5. Conflicts with existing rules and how they are resolved

| Existing rule | Conflict | Resolution (pending the creator's yes on this file) |
|---|---|---|
| CT-03 "Image 1 of every shot except the master is the scene's master frame" | A sharp new angle drawn from the master is now forbidden (SR-01/02) and Qwen cannot re-angle a master | **Amend:** the master is Image 1 only for crops/push-ins of itself (handled in code, not redrawn) and is a palette donor for that place's blurred close-ups (RF-03) |
| CT-07 "consecutive shots of the same people change size by a step or angle by >=30°" | A >=30° re-angle of the same place is a second sharp view | **Amend:** inside one place the change is a size step on the master or a cut to a blurred close-up / insert; a >=30° change of angle only on blurred shots |
| CT-09 "a generated shot is never the base image of the next" | none; RF-05 keeps it | kept |
| CT-05 "every person has a sheet among the references" | none; sheets are RF-02 references | kept |
| ED-14 "a scene opens on an establishing or two-shot" | the establishing shot is the master; two-shots must not be new angles | **Amend:** establishing = master; two-shot = master crop or blurred OTS (DL-06) |
| AC-12 "same setup reuses the frame through a crop" | agrees with SR-02 | kept, now mandatory for a location's sharp shots |
| VISUAL_SCRIPT_v2 "16 Blender angles, Blender -> Qwen" | RF-01 forbids rendered references | **Replaced** by VISUAL_SCRIPT_v3 (masters + crops + blurred close-ups + inserts, no Blender references) |
| D-27 / D-28 green-kit cut-outs | agrees with DL-01/02 (cut-out heroes on plates) | kept |
| BP-40 / BP-107 shot rhythm | crops and inserts count as changes (BP-93); unchanged | kept |

## 6. Open risks (the creator, 18:08)

1. **Heroes must not change from shot to shot** (ID-01..05, RF-02 sheets; measured on the first 10 pictures: same face, clothes,
   proportions; a REVIEW names the shot).
2. **Dialogue rendering must get richer** (DL-01..06): mouth, breathing, blinks, cut-out proportions. The code for DL-03/04 exists
   only in part (`audio/visemes.py`, the J5 card); a free test on one dialogue shot comes before the episode render.
