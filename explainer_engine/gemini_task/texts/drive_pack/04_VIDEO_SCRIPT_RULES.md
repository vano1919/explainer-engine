# Rules for the video script (the shot list)

Sources: `docs/EPISODE_FIRST.md` (RT-01..RT-06, RN-03); `docs/GEMINI_CONSISTENCY_RULES.md` (GC rules);
`docs/SOURCED_RULES.md` (BP-185); `05_STYLE.md` and `06_PICTURE_RULES.md` of this pack.

The video script turns the approved script into a list of shots. For every shot it says what the viewer sees, how the
shot is made, how long it lasts, which reference pictures it uses and the exact prompt for its picture. After your
check it is saved on Drive as `shot_queue.json` and you make the pictures from it, so a mistake here is repeated in
every picture that follows.

## Each shot must have

| Field | Rule |
|---|---|
| `shot_id` | unique, in viewing order |
| the line it covers | every spoken line of the approved script is covered by at least one shot, in order; no shot covers words the script does not have |
| `route` and a reason | one of `map_action`, `still_25d`, `wan` (RT-01) |
| `duration_s` | from the timed read, not from a guess (RN-03) |
| `shot_type` | one of the shot types of the style pack table in `05_STYLE.md`: it picks the style anchor |
| `cast` | the heroes in the picture, by id; each has an approved reference before its first shot |
| `place` | one place id; it has an approved reference before its first shot |
| `references` | in this order: the style anchor of the shot type, the heroes in `cast` order, the place (GC-02) |
| `prompt` | follows every rule of the section "The prompt" below |
| `target` | the file name the picture is saved under |

## Routes

- `wan` (a video clip from the picture) only where a body does something a still cannot fake: running, fighting,
  throwing, handling an object, a fall; and for the speaker of a played scene (RT-02).
- `still_25d` (the picture moved in layers) for camera moves, weather, fire, water, distant crowds, establishing
  views and objects at rest (RT-02). Such a shot names at least {{bp:BP-185.families_min}} kinds of movement beyond
  the camera, for example embers and a flickering light (RT-06, BP-185).
- `map_action` for geography and numbers. Python draws these; you make no picture for them (RT-03).
- The mix is measured by seconds, not by shot counts. The creator's guide is about 10 % map, 30 % still, 60 % video;
  report the measured shares and do not force them (RT-04).

## The prompt

Check every prompt against these. Quote the shot id and the words for each miss.

1. It opens with the style sentence of `05_STYLE.md`, word for word, and carries the style-reference clause (GC-01,
   GC-03).
2. A prompt with people carries the face sentence, word for word (GC-11).
3. Each hero is written with exactly the words of the cast table, the same in every prompt (GC-04).
4. One moment: who does what, where, in which light. No second action, no list of tags, no chain of camera jargon
   (GC-06).
5. No text of any kind is asked for: no signs, labels, letters, numbers, plaques, written maps (GC-07).
6. None of the forbidden words of `05_STYLE.md` appears outside a "never" phrase (GC-18).
7. The light source is named and fits the era (a hearth, a torch, a clay oil lamp, the low sun). Every object fits
   the era, and the prompt carries the episode's era line word for word.
8. A scene prompt says to keep the faces, hair, costumes and props of the reference pictures after image 1 (image 1
   is the style anchor and gives the look only).
9. An end frame of a `wan` shot attaches the style anchor of its shot type first and its own start frame second (GC-09, GC-21).

## The list as a whole

- References first: the list starts with the reference pictures of every hero and every place; no scene shot comes
  before the references it needs.
- A batch is six pictures; it stays inside one scene or one place where it can (GC-08), so that the same references
  serve the whole batch.
- The pictures tell the story without the sound: looking only at the shot descriptions in order, can you follow who
  wants what and what changes? Name the stretches where you cannot.
- Variety: flag a run of shots that would look the same (same size, same angle, same two faces).
- Stakes and named heroes are in the frame. Flag pretty scenery with nobody in it where the script has a hero acting.

## What is not yours to change

The routes, the durations and the wording of a prompt are Claude's. You report the finding and propose the fix; you do
not edit `shot_queue.json` yourself, and you never improve a prompt while making its picture
(`06_PICTURE_RULES.md`, rule 2).
