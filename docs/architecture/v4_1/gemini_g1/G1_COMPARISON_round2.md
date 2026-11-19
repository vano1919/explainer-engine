# G1 round 2: Gemini's blind observation vs measured audio (2026-11-19, plan owner)

Source: Gemini (fresh chat 45ee009762be670d, model "Neon"), six clips uploaded directly from ვანო's Mac, 14:36 Georgia time.
All six clips `opened: true`, `audio_heard: true`. Start pictures could not be opened, so `first_frame_vs_start_picture`
is null everywhere (NOT_RUN, not a pass). Gemini sampled frames at 2 fps, so its times are about ±0.3 s.
Raw answer: `G1_round2_raw_gemini_answer.txt` ('?', '&', '=' were replaced by spaces when copying). JSON:
`g1_observation_gemini_round2.json`.

Measured here: ffmpeg `silencedetect n=-35dB d=0.25` on the same files (sha256 in `../G1_SHA256.txt`). It measures
loudness, not voicing, so it can confirm *when* sound is present, not *what* it is.

| Clip | Gemini hears | Measured (sound above -35 dB) | Agreement |
|---|---|---|---|
| S03_SH003 | German chorus sung, "Stille Nacht" 1.0-2.5, "heilige Nacht" 2.5-4.5; first second a cut-off "Aah" | continuous, one gap 2.62-2.91 | agrees (phrase break ≈2.6-2.9) |
| S03_SH007 | **no speech**; inhale 0.5-1.8, sigh 2.0-3.2 | only 2.47-2.81 loud; rest below -35 dB | no speech agrees; the inhale is quieter than -35 dB, sigh onset ≈2.5 not 2.0. **Contested: short listen** |
| S04_SH014 | **no speech**; string underscore throughout | continuous sound, no silence | agrees |
| S06_SH008 | three English lines: "Maybe." 0.0-0.8, "Maybe." 1.1-1.9, "But not today." 2.5-3.7 | 0.00-0.63, 1.64-2.15, 2.99-3.66 | three utterances agree; Gemini's times run 0.3-0.5 s early → use measured edges |
| S07_SH005 | **no speech**; gunshots 0.3-1.0 and 1.3-2.2; footsteps 3.0-5.5; cloth 5.5-7.5 | 0.48-2.86 loud; then quiet except a blip at 5.0 and 6.48-6.56 | gunshots agree (onset ≈0.48); footsteps/cloth below -35 dB |
| S07_SH006 | **no speech**; footsteps 1.0-6.5; gunshot 7.2-8.3 | short blips at ≈1.97, 2.81, 3.44, 3.83, 4.37, 5.24, 6.04 (rhythmic); loud from 7.85 | footsteps agree; gunshot onset measured 7.85 (Gemini 7.2) |

## What this settles for slice 1.2

- The recorded Whisper words in S03_SH007, S04_SH014 and S07_SH006 are hallucinations: Gemini hears no speech in any of
  them, and the measured sound there is breath, strings or footsteps. S07_SH005 also has no speech (gunshots). These four
  are the adversarial real cases the voicing check must reject.
- S06_SH008 has three real spoken lines; S03_SH003 is sung German (speech present, sung=true).
- Proposed expected verdicts for the six-clip test (still open until ვანო's short listen, per amendment 1.2):
  S03_SH003 speech (sung), S03_SH007 none, S04_SH014 none, S06_SH008 speech ×3, S07_SH005 none, S07_SH006 none.
- Word edges come from the measured voiced spans, never from Gemini's or Whisper's raw times.

## Picture defects Gemini found (for route / re-make decisions, not 1.2)

- S03_SH003 at 1.2 and 2.5 s: centre soldier's mouth closed while the chorus sings (lip-sync).
- S04_SH014 at 3.8 s: both soldiers turn to the camera and smile; best cut 0.0-3.4.
- S07_SH005 at 5.0 s: the revolver vanishes from his hand before the salute.
- S07_SH006 at 2.5 s: a spire/tent silhouette morphs into view on the horizon.
- S03_SH007, S06_SH008: none.

Best cuts (Gemini): S03_SH003 1.0-4.5, S03_SH007 0.5-4.0, S04_SH014 0.0-3.4, S06_SH008 0.0-4.0, S07_SH005 0.0-7.8,
S07_SH006 0.0-8.5. These are proposals; the cut contract (VL cuts) decides.
