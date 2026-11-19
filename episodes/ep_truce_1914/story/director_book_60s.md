# Director's Book: ep_truce_1914, the 60 s slice (S01_SH001..S02_SH005), new style

Method: `wuwangzhang1216/DirectorSKILL` skill `cinematic-director` v2.1.0, MIT, commit `c65ae0d14457` (2026-08-31).
Read for this book: `SKILL.md` in full (hard rules 1-11, 13-step pipeline), `assets/director-book-template.md`,
`assets/shot-plan-template.md`, `assets/keyframe-prompt-template.md`, `references/failure-modes.md` (triage tree, F1-F19 index).
Not opened: the other `references/` files and `director_styles/` (no director lens is used; none is named by the creator).
SK-1 verdict for this skill is in the plan (S4: vendor, W1); this book only cites it.

Inputs (all opened in this session): `story/production_script.json` (shots, lines, claims), the HF clock
`demo_truce_1914/clock/timing.json`, the creator's style note (11-19, "realism with stylised faces"), the picture task
`plan_v5_2026-11-19/pictures_B/PICTURE_TASK_60S_NEW_STYLE.md` and the three new-style references. Words are frozen (OR-17).
Routes are frozen as measured: 5 `still_25d`, 3 `map_action`, 2 `video`. No route was changed.

## Frame
- Format: documentary-drama cold open + rewind, 16:9, 24 fps, master 2560x1440. Target 61.25 s on the clock, 10 shots,
  average shot length 6.1 s (range 3.0-9.3 s).
- Tool class: Gemini chat stills as first frames (reference binding); LTX-2.5 distilled clips for the two `video` shots
  (first frame only, no last-frame slot used: CT-1); Python layered 2.5D for `still_25d`; Python map route for `map_action`.
- Style lens: none. Genre default: restrained period drama, observational, no shot imitating a film.

## Story
- Logline: A private who has read "home by Christmas" all week climbs out of a flooded trench and walks, unarmed, toward the
  guns that have been killing his side; thousands do the same.
- Dramatic core: this slice is a cold open that promises an act (the walk), widens it to thousands, then rewinds to the
  trench where hope ("over by Christmas") has turned to mud. Charge: calm, threat, courage, scale, promise, then hope falling.
- Subtext: nobody says "peace"; the picture shows empty hands.
- Visual thesis: **empty hands and an empty field**. Every frame of S01 keeps the space between the lines open and bright;
  every frame of S02 closes it in (mud, sandbags, a brazier) until a pencilled letter is the only bright thing.

## Delivery
- Platform: YouTube 16:9. Captions: burned in later by the subtitle stage, not in the picture. Nothing readable is
  generated into a picture except one line on the letter (S02_SH005), and that one is checked and, if wrong, set in post.
- Hook frame: 0:00, the frozen field in golden fog (an event in the frame is a hypothesis: see the SK-1 trial; no change made).
- Never: text or signs in pictures, logos, a title card over the hook.

## Lens and framing policy (world words, full-frame equivalent)
- Kit: 24 mm (establishing, fields), 35 mm (trench, group), 50 mm (the hero, the letter). Heights in cm.
- Camera height: eye 160 cm by default; exceptions: low worm's-eye 40 cm (S01_SH002), high 6 m (S01_SH004, S02_SH005 over the shoulder at 180 cm, looking down).
- Headroom: hero never touches the top edge; S01_SH002 keeps 30 % of the frame above him for the tilt.
- Never: lens wider than 24 mm, any Dutch angle, handheld shake.

## Camera grammar
- Allowed moves: slow push-in, slow pull-back, one tilt up, one track behind, one pan right, parallax dolly (2.5D), map parallax dolly.
- Budget: every shot has exactly one move; no shot has two. Motivation: the move shows the next piece of information
  (fog thins, German parapet, the gap, the candle) rather than decorating.
- Never: whip, orbit, zoom.

## Axis and screen direction (coverage)
- **The axis is the line between the two trenches.** British side is **screen left**, German side **screen right**, in every
  wide shot of S01 (SH001, SH003, SH004, SH005) and in the maps (S02_SH001..003: west left, east right).
- Hero travel: Thomas moves away from camera and slightly screen-right in S01_SH003 (toward the German line); S01_SH004 repeats
  British from the left and Germans from the right. S01_SH005 is shot from the British parapet and pans right, toward the Germans.
- S01_SH002 is the one reverse of function, not of axis: the camera is at the foot of the British ladder looking up at the parapet
  (the German line is beyond it, to the right of the frame edge when he looks up).
- Axis cross: none inside S01. S02 is a time cut (rewind), so a new setup is legal (`hook_up`: time_cut).
- Coverage: S01 follows establish (SH001) - relation (SH002) - action (SH003) - scale reveal (SH004) - promise/insert (SH005)
  from the nine shot functions; S02 is map ladder (SH001-003) - tableau (SH004) - insert (SH005).

## Lighting roles (one key, world space)
- **Key:** the low winter sun just above the German parapet, golden, hard through fog (east, Christmas morning, behind the far line, so
  it faces the camera in S01 wide shots): schema `key_light_dir: back`. Height 8-12 degrees. **Fill:** none; fog is the
  fill (soft scatter). **Rim:** the sun rims Thomas's cap and shoulders in S01_SH003 (seen from behind).
- S02_SH004: low gold winter afternoon light from screen left (the sun, now west, over the British side), fog thinner.
- S02_SH005: key is the coke brazier, low and warm, from the front and below; ambient dusk blue behind. Ratio 3:1 lit to shadow side of the hands.
- Planes held under: the near wire and sandbags are silhouetted a stop under in the push-in shots.
- Palette: frost white, mud brown, khaki, field grey, golden sun; forbidden: saturated red, neon, teal-orange grading.

## Continuity bible (strings are pasted verbatim into every prompt; do not improve them)
- `STYLE_BLOCK`: "Photoreal live-action cinematic film still, shot on 35 mm film, natural low winter sun, ground haze and breath vapour,
  muted earthy palette of frost white, mud brown, khaki and field grey, fine film grain, shallow depth of field. Faces are photoreal but
  slightly stylised by ONE shared rule for every person: firmer planar brow, cheek and jaw facets, the same handwriting on every face,
  no single face deformed differently. 16:9." (from the picture task; the creator's style note 11-19)
- `ID_THOMAS`: "Private Thomas Hale, a lean 20-year-old English infantry private with a pale freckled face, short sandy-brown hair, light grey
  eyes, a soft khaki 1914 winter trench cap with a floppy crown, no stiff wire, a short soft peak and ear flaps tied up over the top, a
  khaki 1902 service-dress tunic with brass buttons, 1908 webbing, muddy puttees, a long khaki greatcoat open over the tunic, bare cold
  chapped hands with no gloves". **Open conflict, reported:** the world bible still says "khaki peaked service cap"; the picture task and the
  11-13 note say soft cap. This book follows the soft cap. The Round 0 collage pick (four variants) is still the reference image; until
  the creator picks one, `refs` names the folder, not a file.
- `LOCK_NML`: "a frozen field between two trench lines in Flanders, frost-white barbed wire on wooden stakes, an ice-skinned shell
  hole, a broken willow, the low German parapet with small fir trees standing on it, thick ground fog".
- `LOCK_TRENCH`: "a British front-line trench in winter, waist-high frosted sandbag breastwork, duckboards over brown floodwater, a wooden
  trench ladder, timber props, a small coke brazier".
- `NEG_BASE` (named instances, selected per shot): steel helmets, Brodie helmet, Stahlhelm, gas masks, tanks, glass or hurricane lamps,
  torches or flaming baskets, horses, dogs, oxen, sheep, eagles, plumed or crested helmets, armour, yurts, wooden watchtowers, bows,
  rendered text or signage, watermark, gloves on Thomas, extra people, a changed face or costume.
- Reference order for Gemini (CT-05: at most 4 people-refs, at most 14 refs; we use at most 4): style reference(s) first for look only, then the
  Thomas reference. Style refs are used "for look, light, grain and the face rule only; copy none of their objects".

## Performance register
- Thomas: restrained; the performance lives in hands and breath. Largest gesture: hands lifted slightly out from the sides.
- Never: a hero's raised fist, a smile, looking at camera.

## Editing rhythm
- Clock average 6.1 s. Cut on the narrator's full stop (the clock's shot edges are the voiced edges). Hard cut everywhere; the S01 to S02
  rewind is the only time cut. No dissolve inside S01.

## Sound direction (for W6; recorded here as intent, no sound is made)
- One continuous bed: wind over frozen ground in S01; trench water and brazier crackle in S02. Silence: none planned in the 60 s.
  Effects only where a named event earns one (the ladder grip, the footfall on frost); minimum three effect kinds per scene is the creator's rule, to be placed by W6.

## Acting lane per shot (V2.1 section 17)
| Shot | Route | Lane | Why |
|---|---|---|---|
| S01_SH001 | still_25d | none | no person |
| S01_SH002 | video | P1 | silent under narration, one hand action |
| S01_SH003 | video | P1 | silent walk under narration |
| S01_SH004 | still_25d | P4 | crowd, small figures, no named face |
| S01_SH005 | still_25d | none | candle insert, no person |
| S02_SH001-003 | map_action | none | Python maps |
| S02_SH004 | still_25d | P4 | three soldiers as a group, one ducking |
| S02_SH005 | still_25d | P3 | the hero's hands and the letter, 2.5D |

## Failure watch-list (DirectorSKILL F1-F19, per shot; "n/a" = cannot occur on this route)
F1 identity drift, F2 no motion, F3 warping, F4 wrong action, F5 no end state, F6 camera chaos, F7 continuity break, F8 anachronism,
F9 extra people or objects, F10 anatomy, F11 text artifacts, F12 light drift, F13 speed, F14 physics, F15 lip-sync (n/a: no speech in the slice),
F16 style drift, F17 framing, F18 seam on extend, F19 object permanence.

| Shot | Watch | Why it is likely here |
|---|---|---|
| S01_SH001 | F8, F9, F16, F12 | an empty field invites a stray figure or a steel-helmet silhouette; the old ink look can leak; fog light must stay one golden source |
| S01_SH002 | F1, F8, F10, F5, F6 | soft cap vs peaked cap; bare hands on rails; clip must end with hands still on the rails and eyes on the parapet; only the tilt moves |
| S01_SH003 | F13, F14, F1, F9, F18 | walking speed and foot contact on frost; nobody else may enter the field; no extend, one 5.5 s take |
| S01_SH004 | F3, F9, F8, F17 | crowd warping and weapons appearing; helmets; the extreme wide must keep both groups inside the frame |
| S01_SH005 | F8, F19, F2 | a holder or glass around the candle stub; the stub must not vanish during the pan; the pan must be visible |
| S02_SH001 | F11, F17, F6 | map labels are our own type from Python, not generated; frame crop; parallax only |
| S02_SH002 | F11, F17, F6 | the continuous line must stay continuous; label legibility |
| S02_SH003 | F11, F17, F6 | the Flanders inset; label legibility |
| S02_SH004 | F9, F10, F8, F19 | exactly three soldiers; ducking head under the parapet; no steel helmets; the water level must stay |
| S02_SH005 | F11, F10, F19 | the only readable words ("home by Christmas") may come out garbled: set in post if needed; bare chapped hands, no gloves; the brazier must stay lit |

Repair path (the skill's cost ladder L1-L7, our P-5 limit: at most two generative retries): R1 deterministic fix, R2 prompt patch, R3 new
keyframe or reference, R4 fall back to 2.5D. A clip with two codes is re-planned, not re-prompted (skill skip rule b).

## Open items for the plan thread
1. World bible cap text is stale (peaked vs soft); the book follows the soft cap.
2. Thomas reference: the Round 0 collage pick is not recorded; cards cite the folder.
3. Maps: the schema needs a location for a map plate; cards use a nominal `EXT / day / clear` and `route: map_action`. Say if you want a `MAP` value instead.
