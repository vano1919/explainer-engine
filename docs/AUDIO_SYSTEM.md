# Audio system

Python mixes all audio; the renderer produces silent video (RENDERING_ARCHITECTURE, D-11). Targets: P-90 to P-97
(D-08). Louder is not better: levels are validated against measurements of the rendered file.

## Chain
narration script -> `speakable()` text (pronunciations) -> Kokoro clips (cached per text + full delivery) with phoneme
timings -> `audio.words.json` (word ids, start/end, estimated flag) -> timeline reflow (scenes follow real durations)
-> mix: voice shaping (low-cut, de-ess, soft limit; copied from TMR `mix.shape_voice`), music bed with ducking, SFX
bus -> loudness measurement (ebur128) -> gate -> final audio muxed once into the video.
Narration: 24 kHz mono from Kokoro, resampled to 48 kHz; stereo output with centred voice; mixes stream in blocks (no
full-length float buffers; 16 GB RAM).

## Music, ambience, silence
One music state per scene group, ducked to at least 10 dB under speech (attack 50 ms, release 400 ms); procedural
(TMR `music_synth` approach, new energetic palettes) or CC0/licensed beds with per-file records; no commercial tracks and
no AI-music-as-the-main-focus (disclosure trigger, V-02). Planned silence (a held beat) is declared in the storyboard;
unintended silence over 1.5 s (0.8 s Shorts) fails.

## Audio event contract (v1; schema in Phase 3)
```json
{"schema": "explainer.audio_events", "version": 1,
 "events": [{"id": "sfx.knife_chop@w_0143", "kind": "sfx|music|ambience", "asset": "sfx.knife_chop",
   "at": {"word": "w_0143", "offset_ms": 0}, "duration_ms": 420, "gain_db": -9, "pan": 0.0,
   "fade_in_ms": 5, "fade_out_ms": 40, "priority": 2, "duck_music_db": 0, "overlap": "mix|replace|skip",
   "purpose": "clarify|humour|transition|sync", "license_id": "L-0004", "if_missing": "fail"}]}
```
Rules: SFX only where they clarify an action, reinforce a joke or aid comprehension; at most about one per 6 s on average
(REVIEW above); every asset has a licence record; `if_missing` is `fail` for narration-critical sounds and `skip` only for
decorative ones, and a skip is logged in the QA report. Sync check: rendered SFX start within one frame of the
anchor word.

## Checks run on every mix
Peak and true peak; integrated loudness; clipping; silence map; voice-to-music gap while speaking; click detection at
clip joins; speech does not overlap itself; measured pace against the target; ASR word error where available; level
jumps between scenes. Reports go to the review bundle ([QA_SPECIFICATION](QA_SPECIFICATION.md)).
