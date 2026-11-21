# Same-Topic Before/After Story & Scene Comparison (`ep_waterloo_12min` & `ep_toba_74000bce_12min`)

## 1. Cold Open Comparison (First 10 Seconds)

| Dimension | BEFORE (Disconnected v4.0 Script) | AFTER (Integrated v4.2 Dramatic-Scene & Future-Scene Cold Open) |
|---|---|---|
| **Visual Cold Open (`0–10s`)** | Generated standalone opening shots (`S01_SH001`, `S01_SH002`) with no formal link to later climax scenes. | `S01_SH001` and `S01_SH002` (Toba) / `S01_SH004` (Waterloo) declare `teaser_of` (`S05_SH001`, `S09_SH001` in Toba; `S04_SH004`, `S07_SH003` in Waterloo) and explicit `teaser_trim: [start_s, end_s]`, trimming directly from the later payoff clips with **zero new AI image or video generation**. |
| **Spoken Hook & Setup (`S01`)** | Interrupted by out-of-context character lines (`S01_L003` Gérard shouting at Wellington; `S01_L004`–`S01_L005` Sena speaking before the viewer knows where or when we are). | Pure `narration_led` cold open: intriguing narrator hook lines interpret the visual teaser, frame the paradoxical stakes (`8 billion people today vs. 2,000 survivors in 74,000 BCE`; `four hours of dry chalk at Waterloo`), and hand off into the chronological build-up without spoiling the payoff. |

## 2. Segment-by-Segment Dialogue vs. Narration Architecture

### A. `ep_waterloo_12min` (What If Napoleon Marched at Dawn?)
- **BEFORE (48 `scene_lint` + 3 `story_lint` failures)**:
  - Every segment `S01`–`S12` injected 2–3 isolated one-line character shouts at fixed slots (`S01_L003`, `S02_L002`, `S02_L006`, `S03_L001`, etc.) with no `scene` contract, no reply, physically impossible addressees (`char_rothschild_1815 -> char_napoleon_1815`), third-person self-reference (`char_wellington_1815` saying `"before Wellington reinforces the ridge!"`), and verbatim duplicate sentences repeated 4 times across segments.
- **AFTER (`0 FAIL, 0 REVIEW`)**:
  - **8 Narration-Led Segments (`S01`, `S02`, `S03`, `S05`, `S06`, `S08`, `S10`, `S12`)**: 100% narrator-voiced (`segment_mode: "narration_led"`) for strategic maps, artillery mechanics, Lasne bridge choke points, and Coalition diplomatic fallout.
  - **4 Genuine Played Dramatic Scenes (`S04`, `S07`, `S09`, `S11`)**:
    1. `S04` (**The Wavre Cannon-Thunder Clash**): Narrator setup (`S04_L001`–`S04_L003`) -> 4-turn unbroken confrontation between General Gérard and Marshal Grouchy (`S04_L004`–`S04_L007`, charge turns `- -> +` as Grouchy agrees to march to the sound of the guns) -> Narrator consequence (`S04_L008`–`S04_L009`).
    2. `S07` (**The La Belle Alliance Assault Decision**): Narrator setup (`S07_L001`–`S07_L005`) -> 4-turn unbroken exchange between Gérard and Napoleon (`S07_L006`–`S07_L009`, charge turns `- -> +` as Napoleon commits the unbroken Imperial Guard) -> Narrator consequence (`S07_L010`–`S07_L013`).
    3. `S09` (**Mont-Saint-Jean Dusk Retreat**): Narrator setup (`S09_L001`–`S09_L004`) -> 3-turn exchange (`S09_L005`–`S09_L007`, charge turns `+ -> -` as Wellington orders withdrawal toward Antwerp) -> Narrator consequence (`S09_L008`–`S09_L011`).
    4. `S11` (**Panic at the London Royal Exchange Pillar**): Narrator setup (`S11_L001`–`S11_L004`) -> 3-turn exchange (`S11_L005`–`S11_L007`, charge turns `+ -> -` as Nathan Rothschild liquidates Consols for gold bullion) -> Narrator consequence (`S11_L008`–`S11_L011`).

### B. `ep_toba_74000bce_12min` (The Toba Super-Eruption & Humanity's Survival)
- **BEFORE (20 `scene_lint` + 2 `story_lint` failures)**:
  - Isolated character lines interrupted scientific narration in `S01`, `S03`, `S04`, `S06` (a solitary line dropped inside Stanley Ambrose's 1998 mitochondrial DNA explanation), `S07`, `S10`, `S11`, and `S12`, while narrator lines split character exchanges mid-scene.
- **AFTER (`0 FAIL, 0 REVIEW`)**:
  - **9 Narration-Led Segments (`S01`, `S02`, `S03`, `S04`, `S06`, `S07`, `S10`, `S11`, `S12`)**: 100% narrator-voiced (`segment_mode: "narration_led"`) for VEI-8 magma chamber physics, stratospheric sulfate aerosols, genetic bottleneck data, and Blue Highway migration corridors.
  - **3 Genuine Played Dramatic Scenes (`S05`, `S08`, `S09`)**:
    1. `S05` (**The Basalt Cave Split**): Narrator setup (`S05_L001`) -> 5-turn unbroken clash between Kael and Sena (`S05_L002`–`S05_L006`, charge turns `- -> +` as Sena wins one final day at the river pools) -> Narrator consequence (`S05_L007`–`S05_L011`).
    2. `S08` (**The Heat-Treated Microlith & First Bow Test**): Narrator setup (`S08_L001`–`S08_L003`) -> 4-turn unbroken bow test scene between Sena and Kael (`S08_L004`–`S08_L007`, charge turns `- -> +` as the microlith arrow pierces the pool without scattering the fish) -> Narrator consequence (`S08_L008`–`S08_L014`).
    3. `S09` (**Strangers at the Ash River Standoff**): Narrator setup (`S09_L001`) -> 5-turn unbroken three-character standoff among Kael, Thar, and Sena (`S09_L002`–`S09_L006`, charge turns `- -> +` as Sena brokers the trade of microlith arrows for sealed ostrich-shell water flasks) -> Narrator consequence (`S09_L007`–`S09_L009`).
