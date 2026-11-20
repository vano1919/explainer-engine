# Judge rubrics for owner_requirements/1 (proposed home: docs/registry/judge_rubrics.md)

Each judge step gives a NUMBER. A judge never lets a render through the send gate by itself (spec section 6): the owner at MS-7 or the blind judge sees it.

## j-seen-defects
**Seen-record defects.** Open the asset. List every defect (artifact, wrong prop, text, face drift, continuity break).
- Number the judge must give: integer defect count per asset
- Pass rule: PASS: every listed defect resolved or accepted by the owner; zero unlisted defects found by a second look.

## j-ms2-list-complete
**MS-2 list covers the three families.** Count candidates run or priced per family: camera projection, image-to-3D, scene reconstruction.
- Number the judge must give: count per family
- Pass rule: PASS: >= 1 per family.

## j-body-motion
**Realistic body motion.** Watch each clip at full speed and at 0.25x. Count limb melt, foot slide, face drift.
- Number the judge must give: realism score 1-5; artifact count (integer)
- Pass rule: PASS: score >= 4 and 0 artifacts on every listed clip.

## j-map-vs-library
**Our map vs library maps.** Blind sheet with sealed labels, same data. Rank all maps 1..N.
- Number the judge must give: integer rank of ours
- Pass rule: PASS: rank <= 2; key sha256 written before the judging.

## j-style-unity
**Overlay and video style unity.** Show the overlay shot next to its neighbouring video frame; judge colour, line, grain, type.
- Number the judge must give: score 1-5
- Pass rule: PASS: >= 4.

## j-face-actor
**Faces read as live-action actors.** For each hero face crop: does it read as an actor in a live-action adventure film (GC-11) or as a round 3D cartoon?
- Number the judge must give: actor score 1-5 per face; count of cartoon faces
- Pass rule: PASS: every face >= 4 and 0 cartoon faces.

## j-25d-moves
**2.5D moves well.** Watch the clip; mark speed jumps, hard starts/stops, wrong easing. Camera moves must have a motivated ease.
- Number the judge must give: count of speed jumps (must be 0); easing score 1-5
- Pass rule: PASS: 0 jumps and easing >= 4.

## j-waxy
**No waxy faces after upscale.** On identical face crops of source and upscale, judge skin texture.
- Number the judge must give: texture score 1-5 per crop (1 = waxy); count of waxy faces
- Pass rule: PASS: >= 4 on every crop and 0 waxy faces.

## j-story-first
**Story first.** script-critic rubric: read as viewer and as editor; predict drop-off minute.
- Number the judge must give: story score 1-10; predicted drop-off minute
- Pass rule: PASS: >= 7 before any paid step; owner approves the finished script (OR-17).

## j-owner-eye
**Owner's eye at MS-7.** Owner looks at the candidate sheet.
- Number the judge must give: verdict counts: keep / reject / unsure
- Pass rule: PASS: owner keep. A reject is never overruled by a blind judge.
