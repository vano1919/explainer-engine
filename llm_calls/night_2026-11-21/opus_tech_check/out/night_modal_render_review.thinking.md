I'm checking the mask handling in living.py, since output_size_frame resizes s.m_all with LANCZOS4. If it's a float32 mask in 0..1, the overshoot from the resize gets clipped afterward, so that's fine. I'm also wondering whether cv2.resize accepts float64 and whether a boolean mask would make it fail.

I'm also checking whether the other writers are a concern: the alpha and person_zone PNGs are only diagnostics, and the metrics are measured on the working-space frame, so those are fine. The 1920 gate is met by upscaling the 1280x720 frame, which passes the check without adding real resolution, and I'll note that as a provisional point.

I'm checking whether freezedetect reports a freeze that runs to the end of the clip. I recall it may not emit freeze_end at EOF in older ffmpeg versions, unlike blackdetect, so a static clip could be undercounted and pass with a frozen ratio of zero. I'm flagging that as a real concern.

I'm flagging a should-fix: if a freeze runs to the end of the clip, freezedetect may emit freeze_start without a matching duration, so the frozen ratio could be undercounted. I'll mark that as depending on the ffmpeg version. The blackdetect and freezedetect thresholds are hardcoded and not in the JSON, so I'll name them as provisional in section 4.

I'm checking whether a duration of "N/A" from ffprobe would raise a ValueError instead of the RuntimeError the code expects, and whether a zero duration would hit a division by zero. Both are minor, but worth a should-fix. I'm also weighing whether the 0.00219 sharpness floor is meaningful, since the samples may have been measured at a different resolution than the 1920 output.

I'm checking whether near-black frames would read as sharp: with a mean near zero, the normalization blows up even small encoder noise, so a dark frame could pass the sharpness gate, which undercuts the "catches blank output" claim.

I'm checking the sharpness gate against near-black frames: with a mean close to zero, the normalisation inflates even small encoder noise, so a dark blank video could read as sharp and pass. That would undercut the claim that the gate catches blank output. I'm also noting that the scale-invariance test holds, and that the CAP_PROP_POS_FRAMES seek may be slightly inaccurate, which is minor.

I'm checking whether existing tests mock subprocess.run for measure_video, since it now always calls ffmpeg and cv2 and could break a test expecting a single call or a None black ratio.

I'm checking whether the existing video measurement tests mock subprocess.run in a way the new ffmpeg and cv2 calls would break, since I can't see that test in the diff. I'm also noting that the json now changes min_sharpness to 0.002 for both video and photo, but only the video section carries the guess marker, so the photo floor needs the same flag.

I'm checking the render payload in render.py: the bridges default to an empty list, so nothing changes when they're absent. I'm also wondering whether the fps fallback of 24 matches the clock's actual frame rate, since the render may already set its own.

I'm looking at the bridge test, where frame 48 sits at the very end of a 48-frame clip, so it falls outside the valid range. The bridge window of 1.0 to 3.0 seconds at 24 fps covers frames 24 to 72, so I'd move the check to frame 24 or 36 to stay safely inside the clip.

I'm checking whether the boundary frames are tested, since the current test only covers one frame inside and one outside the bridge window, which wouldn't catch a swapped onset and hold_end. I'm also confirming that the bridges_from_words test expects the right hold_end, and that it raises a ValueError when the text is missing.

I'm checking the bridge rendering code in render.py next. The new bridge_render, bridge_sync, and render_presets imports need to exist on the branch, and I'm watching for a possible circular import if bridge_render pulls in maps.render. I'm also confirming that the colour handling and the canvas-height-based sizing look right.

