# G1: watch and listen to six raw LTX clips (Truce 1914)

**Purpose.** This is a capability check. We want to know how well native video and audio observation by a model can
serve as the "eyes and ears" of the pipeline. Your answers will be compared with independent measurements of the same
files (decoded frames, audio energy, frame sheets). Those measurements are not shown here on purpose.

**Run this in a fresh chat** that has not seen the repository, the review, the script or any word list for these clips.

## Files (this folder)

For each of the six shots `S03_SH003`, `S03_SH007`, `S04_SH014`, `S06_SH008`, `S07_SH005`, `S07_SH006`:

- `<shot>_clip.mp4`: the raw clip as the video model returned it, with its own sound.
- `<shot>_start.png` (or `.jpg`, see below): the picture the clip was generated from.

`SHA256.txt` lists the hash and size of every file.

`S03_SH003_start.jpg` and `S06_SH008_start.jpg` are JPEG copies (quality 92, same pixel size) of the original PNG start
pictures, which were too large for the upload. Their PNG hashes are in `SHA256.txt`.

## Rules

1. Watch every clip from the first frame to the last and listen to its sound.
2. Describe only what is in the file. Do not infer from the file name, from history, or from what such a scene "should" contain.
3. If you could not open a file, could not play it, or could not hear its audio, say so for that clip
   (`"opened": false` or `"audio_heard": false`). Never fill a gap with a guess.
4. Times are seconds from the start of the clip, to 0.1 s.
5. Every speech and sound row carries `confidence`: `high`, `medium` or `low`.
6. Write the words exactly as heard, in the language heard. If a voice is present but the words are unclear, write
   `"words": null` and say what it sounds like.

## Output

One file, `G1_OBSERVATIONS.json`, in this folder (or pasted in the chat if you cannot write to Drive):

```json
{
  "schema": "g1_observation/1",
  "observer": "<model name and mode exactly as your interface shows it>",
  "clips": [
    {
      "shot_id": "S03_SH003",
      "opened": true,
      "audio_heard": true,
      "duration_s": 0.0,
      "first_frame_vs_start_picture": {"same_composition": true, "differences": ["..."]},
      "visual_timeline": [{"t0": 0.0, "t1": 0.0, "what": "..."}],
      "people": [{"who": "short description", "mouth_moves": [{"t0": 0.0, "t1": 0.0}]}],
      "any_speech": true,
      "speech": [{"t0": 0.0, "t1": 0.0, "speaker": "who", "language": "...", "words": "...", "sung": false, "confidence": "high"}],
      "non_speech_sounds": [{"t0": 0.0, "t1": 0.0, "what": "...", "confidence": "high"}],
      "main_action": {"start_s": 0.0, "peak_s": 0.0, "end_s": 0.0, "what": "..."},
      "audio_matches_picture": {"verdict": "yes | partly | no", "why": "..."},
      "defects": [{"t": 0.0, "what": "..."}],
      "best_cut": {"in_s": 0.0, "out_s": 0.0, "why": "..."}
    }
  ]
}
```

After the JSON, add at most five lines on what you could not judge and why.
