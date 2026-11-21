# Quality options for maps and bridges (night 2026-11-21)

## How to choose

Set `QUALITY_OPTION=strict|medium|light` for thresholds. The code reads this variable; the default is `medium`. Map preset and bridge style are chosen by name in `map_presets.json` and `bridge_styles.json`. Nothing is applied to renders yet. Owner approval changes numbers only.

## Thresholds

| Setting | strict | medium | light |
|---|---|---|---|
| Primary line % | 0.6 | 0.5 | 0.4 |
| Secondary line % | 0.3 | 0.25 | 0.2 |
| Label cap height % | 3.0 | 2.5 | 2.0 |
| Label contrast | 7.0 | 4.5 | 3.0 |
| Green hue range (deg) | 85–150 | 80–160 | 70–170 |
| Green saturation min % | 45 | 35 | 25 |
| Bridge onset tolerance (frames) | 1 | 1 | 2 |
| Bridge cap height % | 9.0 | 8.0 | 6.0 |
| Bridge hold (s) | 1.5 | 1.0 | 0.8 |
| Residual motion per frame % | 0.04 | 0.05 | 0.07 |
| Residual over shot % | 0.15 | 0.2 | 0.3 |

- **strict:** Crisp, high-contrast diagrams with large labels and wide lines; nothing subtle.
- **medium:** Balanced, readable diagrams with standard line weights and comfortable label contrast.
- **light:** Softer, lighter diagrams with thinner lines and lower minimum label contrast.

## Map presets

- **bold:** 1.0% primary, 0.5% secondary lines; 3.0% label cap; white fill, black halo. Heavy lines and big white labels with a black halo, like a bold infographic.
- **balanced:** 0.7% primary, 0.35% secondary; 2.8% cap; warm off-white fill (`#F4F1E8`), dark halo. Moderate weights with warm labels for a balanced look.
- **light:** 0.5% primary, 0.25% secondary; 2.5% cap; dark fill (`#1B1B1B`), white halo. Thin lines and dark labels for a light, airy diagram.

## Bridge styles

- **card:** 9.0% cap height, solid dark card.
- **outline:** 8.0% cap height, no background, outlined text.
- **lower_third:** 7.0% cap height, full-width bar.

## Recommendation

Start with **medium**; it equals the current provisional numbers. Choose **strict** if you want crisp diagrams, **light** if labels crowd the frame. These are my proposals, no source is cited, and none was tested on a rendered frame.

## Files

Configs are in `explainer_engine/maps/quality_options/` on branch `claude/project-thread-3j9l41-options`; copies are in this folder.