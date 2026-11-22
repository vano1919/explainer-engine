
## 2026-11-22 (Haiku helper, thread 3j9l41, coordinator instruction 06:39 UTC)

- **Sharpness unit (decided by the Haiku helper, coordinator delegated the technical choice):** sharpness = variance of the Laplacian of the grayscale frame (0..1) divided by the variance of the frame itself (0..1); frames with std below 2/255 score 0. Why: the previous unit divided by mean squared, which inflated dark blurred frames (Opus review, item 2). The new unit is brightness- and contrast-scale invariant. Floor: 0.02, GUESS, rounded down from the lowest of 24 project samples (0.0241; median 0.0338; max 0.602), measured 2026-11-22. Owner sets the real floor on approved samples.
- **Upscale note (fact, not a decision):** the 2.5D renderer's 1920x1080 output is upscaled from the 1280x720 working space; no new detail. The gate's size check passes on upscaled frames, so a 1080p label does not mean 1080p detail. The sharpness floor was not measured on upscaled output.
- **Filter parameters:** blackdetect d=0.1 pix_th=0.10 and freezedetect n=0.003 d=0.5 live in technical_gate.json under "filters", marked PROVISIONAL (house values, no source).
