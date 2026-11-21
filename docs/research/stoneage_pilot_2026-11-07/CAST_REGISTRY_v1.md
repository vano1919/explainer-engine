# Stone-age pilot: cast registry v1 (2026-11-07)

For [VISUAL_SCRIPT_v3](VISUAL_SCRIPT_v3.md) under [SCENE_REUSE_RULES](../../SCENE_REUSE_RULES.md) (ID-01..06, RF-02). Every prompt copies the **appearance text** below word for word (ID-01, CT-02); a shot never rewrites it, it only adds the scene part (ID-04). Colours are plain words, sizes in metres (ID-02); heroes have a face sentence (ID-05). The base texts of Marcus, Ura, the hunters and the mammoths are the ones that held across 9 pictures on 2026-11-07 (v5/v6); this file only puts a name label in front and appends a short face sentence (for the mammoths, the noun phrase in front). Nothing here has been generated yet.

Style line (opens every prompt, UR-22): `xworld style, hand-drawn 2D cartoon with bold black ink outlines and flat bright colours.`

Prompt order: style line, (reference sentence when refs are used), scene part, then the appearance blocks of only who/what is in the shot (SO-14), in the order they are named (RF-04).

## 1. People and animals

| ID | Role | Appearance text (verbatim) | Distinct mark (ID-03) | Reference sheet (RF-02) | Used in |
|---|---|---|---|---|---|
| MARCUS | hero | Marcus: a young man of 25, 1.75 m, short dark-brown hair, light skin, a medium-grey hoodie with the hood down, dark-blue jeans and plain white sneakers. Face: oval, clean-shaven, straight nose, thick dark brows. | grey hoodie + plain white sneakers; the only modern clothes in the film | SH-MARCUS (4 views), MS-MARCUS (mouth: rest, mid, wide + 3 visemes) | PM-01..08, M-STREET, M-TUNDRA, M-HALL, M-WALL, M-CAMP, M-GATE, I-01, I-02, I-05, I-06, I-08, I-10 |
| URA | hero | Ura: an old shaman, 1.80 m, his face hidden by a bone-white deer-skull mask with two tall branching brown antlers, a long dark-brown fur cloak to the ankles over a dark-blue tunic, brown leather boots. A long grey beard hangs below the mask. | deer-skull mask with two tall antlers (no one else wears headgear); mouth never visible -> DL-03 mouth-hidden fallback on every Ura line | SH-URA (4 views); no mouth sheet | PU-01..05, M-HALL, M-WALL, M-GATE, I-03 (hand), I-04, I-07 (hand) |
| HUNTERS | extras x3 (H-GREY, H-BROWN, H-SPOT) | Hunters: adult men, 1.70 m, dark-brown shoulder-length hair, bare arms, knee-length fur tunics: one grey fur, one brown fur, one cream fur with dark spots. Faces: broad and bearded (grey), thin (brown), round with a moustache (spotted). | fur colour per man: grey / brown / cream with dark spots; always shown as the three together | SH-HUNTERS (the three side by side, front + back in one picture) | PH-01, PH-02, M-HALL, M-CAMP, M-GATE; blurred near in S03-03, S09-04 |
| CHILD | extra (speaks 2 lines) | The child: a small girl of 6, 1.10 m, black hair in two short braids tied with red cord, light-brown skin, a knee-length white rabbit-fur tunic with one red ochre stripe across the chest, soft brown fur boots. Face: round, small upturned nose, big dark eyes, a gap in her front teeth. | white rabbit-fur tunic with one red stripe, two braids with red cord, the only child | SH-CHILD (4 views), MS-CHILD (rest, mid, wide) | PC-01, M-CAMP |
| MAMMOTHS | animals x3 | Mammoths: three woolly mammoths with dark reddish-brown shaggy fur and long curved cream tusks; the big one 3.5 m, the middle one 3 m, the small one 2 m. | three sizes 3.5 / 3 / 2 m, walk big-first | SH-MAMMOTHS (the three side by side, side view) | M-TUNDRA (c2) |

Silhouette check (ID-03): hair dark-brown short (Marcus) vs dark-brown shoulder-length (hunters) vs grey beard under a mask (Ura) vs black braids (child); garments grey cotton / dark-brown fur + dark-blue / grey, brown, spotted cream fur / white fur + red stripe; only Ura has headgear. Heights 1.80 > 1.75 > 1.70 > 1.10 m are kept by DL-02 on every cut-out.

## 2. Recurring props

| ID | Appearance text (verbatim) | Distinct mark | Reference sheet | Used in |
|---|---|---|---|---|
| PHONE | The phone: a black smartphone, 15 cm, in a plain black case, one cracked corner on the screen glass at the top right. | cracked top-right corner; screen states are graphics laid on the screen (14 %, 9 % red, flash, black) | PR-MODERN | M-STREET, M-HALL, M-CAMP, I-05, I-06, PC-01 |
| KEY | The bike key: a small silver bike-lock key on a short red fabric strap. | red strap | PR-MODERN | I-05 |
| DRUM | The drum: a round flat hand drum, 0.5 m across, pale cream stretched hide on a dark-brown wooden rim, struck with a short white bone beater. | pale hide + white bone beater; Ura's only prop | PR-STONE | PU-01, PU-04, M-HALL, M-WALL, I-03 |
| SPEAR | The spears: 2 m wooden spears with grey flint points bound with brown sinew. | flint point + brown sinew | PR-STONE | M-GATE, PH-02, c4, spear tips in S03-01 / S09-04 |
| TORCH | The torches: 0.6 m wooden sticks wrapped in dark hide, burning with a yellow-orange flame. | dark hide wrap | PR-STONE | M-WALL, M-GATE |
| STICKS | The fire sticks: two straight pale wooden sticks, 0.4 m and 0.3 m long. | two lengths | PR-STONE | PM-04, PM-05 |
| BOWL | The ochre bowl: a small grey stone bowl, 15 cm across, full of wet bright-red ochre paste. | grey stone + wet red | PR-STONE | I-08 |
| BONE | The tally bone: a pale cream bone, 0.3 m long, with a row of short cut notches, cut with a grey flint blade. | row of notches | PR-STONE | I-07 |
| PRINTS | The handprints: positive prints (a palm pressed in paint, not a stencil). Ura's fresh print is a large bright-red palm with five fingers at shoulder height; beside it, clean grey-brown rock of the same size (the empty space); Marcus's later print is a smaller red palm in that space. Old prints around them are faded brown-red. | Ura's big fresh print + the empty space; later Marcus's smaller print in it | the masters M-WALL + inserts I-04, I-08, I-09, I-11 (no sheet: they are drawn in place) | M-WALL, I-04, I-08, I-09, I-11 |

## 3. Location masters (one sharp view each, SR-01/02)

The landmark text goes verbatim into the master's prompt; after approval the **master picture is the reference** of that place (RF-02/03): Image 1 only for its own crops (done in code, AC-12/13: ≤1.6x), a palette donor for its inserts, and the blurred plate of its D shots (DL-01). Masters are generated at 1280×720 and upscaled 2x before any crop past 1.4x.

| ID | Scenes | Landmark text (verbatim) | Staging (scene part of the master prompt) | Two landmarks a viewer remembers |
|---|---|---|---|---|
| M-STREET | S01, S16 | a Manhattan crosswalk at night in the rain: wide white crosswalk stripes on wet black asphalt, a round puddle at the kerb reflecting red and yellow lights, one street lamp, a bicycle chained to the lamp post, tall buildings with small lit windows far behind. | Marcus at the kerb, head bowed to the phone, left third; bike on the lamp post; crosswalk to the right | the crosswalk stripes + the round puddle |
| M-TUNDRA | S01 end, S02, S03 | a snowy open valley at dusk: flat white snow, a low dark ridge far behind, a pale orange and violet sky, a few bare dark shrubs. | low wide view; mammoths cross mid-distance left->right; Marcus small, from behind, near lower-left | the dark ridge + the herd |
| M-HALL | S04, S05, S06, S09 | a large cave hall lit by a low dying fire: a ring of stones in the middle with red embers and two small flames; on the back wall a golden-yellow painting of tall towers like a city skyline; grey-brown rock. | Ura left, near, facing right, lowering the drum; Marcus kneels right of the fire facing left, phone in his lap; three hunters sit back right in shadow. Fire LOW all through (S04-S09) | the golden skyline painting + the dying stone-ring fire |
| M-WALL | S10, S11, S13, S14, S15 | a deep, narrow cave chamber: a curved grey-brown rock wall covered from knee height to above the head with hundreds of faded brown-red handprints, one fresh bright-red large print at shoulder height in the middle with clean empty rock beside it; a burning torch stuck in a crack on the left; a small ring of stones with glowing embers at the foot of the wall. | eye level from behind: Ura left, Marcus right, both facing the wall, middle distance; the fresh print + empty space between them; torch left; ember ring at the wall's foot (the fire that returns in S14) | hundreds of red palms + the empty space |
| M-CAMP | S07, S08 | a winter camp at night: a ring of round huts covered in brown hides, a big campfire in the middle, a fallen log by the fire, trodden snow, a dark pine forest and stars behind. | Marcus on the log right of the fire facing left, grey fur on his shoulders, phone lit; the child left of him leaning to the phone; the three hunters kneel in a row at the left offering a fur and meat on a flat stone | ring of hide huts + campfire |
| M-GATE | S12 | the camp's gate in a snowstorm at night: a tall arch of two crossed mammoth tusks and big pale bones set in a fence of wooden stakes, heavy blowing snow, dark blue-grey light. | hunters in a row before the gate facing us, torch in one hand, spear raised forward in the other; Marcus (left) and Ura (right) near, large, backs to us, dark against the torchlight | tusk arch + stake fence + blowing snow |

## 4. Reference sheets to make (RF-02, RF-05: each approved by the creator before use)

| Sheet | Content | Size | Needed by |
|---|---|---|---|
| SH-MARCUS | Marcus, 4 views (front, 3/4, side, back), plain light-grey | 1280×720 | PM-01..08, every picture with Marcus |
| SH-URA | Ura, 4 views | 1280×720 | PU-01..05, M-HALL, M-WALL, M-GATE |
| SH-HUNTERS | the three hunters side by side, front and back | 1280×720 | PH-01, PH-02, M-HALL, M-CAMP, M-GATE |
| SH-CHILD | the child, 4 views | 1280×720 | PC-01, M-CAMP |
| SH-MAMMOTHS | the three mammoths, side view, in size order | 1280×720 | M-TUNDRA (if the text-only master drifts) |
| MS-MARCUS | Marcus's head, front and 3/4, mouth rest / mid / wide (+ 3 visemes if they hold) | 1280×720 | DL-03 on 8 Marcus D shots |
| MS-CHILD | the child's head, mouth rest / mid / wide | 1280×720 | DL-03 on S07-02 |
| PR-MODERN | phone (front, back, side; screen dark) + bike key | 1280×720 | I-05, I-06, PC-01 |
| PR-STONE | drum + beater, spear, torch, fire sticks, ochre bowl, tally bone | 1280×720 | I-03, I-07, I-08, PM-04/05, spear tips |

Ura has no mouth sheet: the mask hides the mouth, so every Ura line uses DL-03's mouth-hidden fallback (head nod / tilt on stressed words, beard sway, drum hand), with DL-04 breathing and blinks replaced by antler sway and a slow push. **Open question:** v2 planned a mask over the upper face with the mouth visible; the tested text hides the face. Keep the tested text unless the creator wants a lip-synced Ura.
