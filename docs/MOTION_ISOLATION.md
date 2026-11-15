# Motion isolation: mover vs. rigid holder separation and leak gate

Machine-readable source of truth: `explainer_engine/standards/motion_isolation.json`, enforced by `explainer_engine/production/motion_isolation.py` and `explainer_engine/qa/look_and_listen.py`. See also [SOURCED_RULES](SOURCED_RULES.md) (D-59).

## 1. Physical relationships

Every animated phenomenon in `production/directed25d.py` and `production/living_fx.py` separates the moving element (`mover_mask`) from its rigid holder and background (`anchor_mask`):

- **Flame in open grate (`S02_SH008` brazier):** Bar-preserving luminance and warmth gate animates glowing coals and upper flame plumes while clamping dark iron grating bars and basket legs to zero geometric displacement.
- **Flame on candle wick (`S08_SH002` candle in tin holder):** Wick-apex plume split animates only the teardrop flame above the wick while keeping the wax body, tin holder rim, and crate rigid (`0.0` displacement, radial light spill only).
- **Steam over held vessel (`S02_SH008` tin mug):** Translucent screen-blended wisp originating above the mug's top rim, masked off the mug body and gloved fingers.
- **Breath from mouth (`S02_SH008`, `S05_SH020`):** Directional puff originating at the mouth anchor, masked off the face and collar.
- **Sky and ground weather (`S02_SH008` stars, `S05_SH020` frost/sun):** Sky effects are multiplied by `sky_mask * (1 - dilated_fg_mask)` even when a box is supplied; frost glints are restricted to `snow_ground_mask * (1 - dilated_fg_mask)` and suppressed on solemn burial shots.
- **Cloth on rigid support (`S07_SH005` flag, coats):** Proximal attachment seam next to the pole or torso is pinned at zero displacement with a smooth ramp toward the free edge.

## 2. Multi-component leak gate

`evaluate_motion_isolation` compensates for camera crop and parallax motion before measuring: (1) intended element motion (`element_motion_p95`), (2) rigid holder leak (`holder_leak_p95`), (3) background camera residual (`camera_residual_error`), (4) mask boundary halo error (`boundary_halo_error`), and (5) forbidden-region particle leak (`forbidden_region_particle_leak`).
