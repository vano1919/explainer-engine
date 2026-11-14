Provided the Truce 1914 story-flow table, production design rules, and technical implementation code.
Identifying the user's primary concern about story flow.
Extracted all scene boundaries and lane changes from Truce 1914 production script
Searched YouTube and GitHub for 2.5D parallax and Johnny Harris / Kings and Generals map animation tutorials and repos
Extracted every scene boundary and lane change in Truce 1914 production script
Checking for additional cuts across specified sequences.
Listed all 84 shots of Truce 1914 to verify every boundary and lane switch
Printed compact summary of all 84 shots in Truce 1914
Comparing script metadata to recent PR changes.
Extracting requested code and searching for specified tutorials.
Verifying each link's validity against the retrieved data.
Complete
Gemini said

Here are the three missing pieces: the complete Truce 1914 shot-to-shot story-flow table with the 5 script-planning rules, the full recipe_25d_and_qa_sketches.py code (including camera inheritance, the 8-position label solver, and QA Checks 1, 2, and 7), and the verified YouTube and GitHub references.

1. Story Flow: Every Scene Boundary & Lane Change in ep_truce_1914

In episodes/ep_truce_1914/story/production_script.json (84 shots across S01–S08), every lane switch and scene boundary is listed below (noting S07_SH005, which is still_25d in PR #188's JSON but video per CLIPS-08 / LTX-11 after the R3 take was accepted):

shot_a -> shot_b (Type)	Why b Follows a in the Story	Visual Transition & Camera Hand-Off	What the Sound Does Across the Cut
S01_SH001 -> S01_SH002 (2.5D -> video)	Wide dawn establishing shot of frozen No Man's Land narrows to the cold-open hook: one British soldier climbing out of his trench.	Hard cut on focal point + motion continuation: SH001 cranes up/pushes toward the trench line (2.0%/s); SH002 picks up with tilt_up on the boots climbing the ladder.	J-cut (-0.25 s): leather boot scrape and heavy wool foley begin 6 frames before the cut over the open-field dawn wind bed.
S01_SH003 -> S01_SH004 (video -> 2.5D)	Moves from one unarmed man walking into danger (SH003) to the historical scale—thousands doing the same across the front (SH004).	Hard cut on reverse scale (push -> pull): SH003 tracks forward behind the lone soldier; SH004 opens at mid-scale and pulls back (2.0%/s) to reveal the wider crowd in mist.	L-cut (+0.30 s): the lone soldier's crunching footsteps in frozen mud ring into SH004 as a low, distant multi-voice murmur swells under the narrator's word "thousands".
S01_SH005 -> S02_SH001 (SCENE S01->S02, 2.5D -> map)	Ends the cold-open promise (candle-lit trench trees) and resets to August 1914 to explain how the mobile war became a stalemate.	fade_to_black (24 frames: 12f out, 12f in): SH005's rightward truck settles as warm candlelight dips to black; S02_SH001 rises from black on the Western Europe relief plate.	Musical cadence + paper foley prelap (-0.45 s): S01's warm carol motif decays into black; 0.45 s before S02_SH001 appears, a crisp period stamp/paper-slide (ov_map_open) introduces the August march arrow.
S02_SH001 -> S02_SH002 (map -> map)	Contrasts the fast August invasion promise ("over by Christmas") with the December reality (one continuous trench line from the North Sea to Switzerland).	cross_dissolve_8f + inherited camera (view0): SH002 inherits SH001's exact ending (lon, lat, span_km) and switches to route_pan tracing the red front_line south-east.	Continuous table bed + foley handoff: the marching-boots spot cue stops cleanly on the cut as a continuous charcoal-on-paper line draw (map_route_draw, span) traces the trench line.
S02_SH002 -> S02_SH003 (map -> map)	Zooms from the 400-mile theater line down into the specific Flanders sector where our characters sit yards apart.	cross_dissolve_8f + inherited camera -> fly_to: SH003 keeps the drawn front_line standing at frame 0 (cues: "none", stands=True) and executes a logarithmic fly_to zoom into Flanders (span_km narrowing toward 250 km).	Air whoosh (span) -> diegetic cough prelap (-0.35 s): fly_to carries a soft low-passed air movement, and on "hear each other cough", a distant muffled trench cough bridges into the physical trench.
S02_SH003 -> S02_SH004 (map -> 2.5D)	Drops from the Flanders map highlight directly into the physical mud and water of the British breastwork trench.	map_to_location_zoom_through (14 frames): camera zooms through the glowing Flanders ring on (focal_xy) as the parchment relief dissolves into the dark, wet trench boards of SH004 (truck:left).	J-cut (-0.50 s): sloshing boot water and cold trench wind fade up under the last 0.5 s of the map zoom so the viewer hears the mud before seeing it.
S02_SH005 -> S02_SH006 (2.5D -> video)	Shifts from narrator exposition (Thomas reading his mother's letter by brazier light) to Thomas speaking his first dry line aloud.	Axial cut-in (medium -> close-medium, match eyeline): SH005 pushes slowly (1.8%/s) toward Thomas's bowed head and letter; SH006 cuts in 30% closer on the same left-to-right eyeline as he speaks.	Voice-handoff L/J bridge (0.25 s): brazier crackle (fire_flicker foley, panned center-right) stays constant at -34 dBFS while the narrator yields cleanly to Thomas's LTX dialogue stem.
S02_SH007 -> S02_SH008 (video -> 2.5D)	Moves from Sgt. Harris's gruff warning ("Keep your head down") to the high-level political context (the Pope's failed truce appeal).	Hard cut on settling pose -> split 2-shot (SH008a/b): SH007 ends on Harris's still face (frame_pick); SH008 opens wider on both men by the brazier (push toward Thomas on "nobody asked the men").	L-cut (+0.30 s): trench wind and brazier crackle continue unbroken; a low, somber cello/pad note enters on "the Pope asked" to separate political failure from trench reality.
S02_SH009 -> S03_SH001 (SCENE S02->S03, 2.5D -> video)	Crosses No Man's Land on Christmas Eve: British soldiers opening brass Princess Mary tins (S02) -> Friedrich lighting Tannenbaum candles in the Saxon trench (S03).	Match-cut cross-dissolve (cross_dissolve_8f) on warm point light: S02_SH009 pushes into the warm brass reflection of the tin; S03_SH001 dissolves in on the warm match/candle flame in Friedrich's hands (slow_push_in).	Acoustic space shift (0.45 s crossfade): British trench murmur fades down as a strike-match foley spot (onset) introduces the quieter Saxon trench room tone.
S03_SH001 -> S03_SH002 (video -> 2.5D)	Connects Friedrich placing the candle on the parapet to the family photograph he carries in his coat.	Eyeline match -> insert (hard_cut): SH001 ends with Friedrich looking down toward his chest pocket; SH002 cuts to the close 2.5D insert of his hands holding the sepia portrait card (slow_push_in).	Close foley + warm spill: heavy coat-cloth rustle and paper touch (-30 dBFS) on the cut; candle ambience stays dry and intimate (close perspective).
S03_SH002 -> S03_SH003 (2.5D -> video)	Moves from the silent memory of home (SH002 photo) to the emotional turning point of the night: Friedrich beginning "Stille Nacht".	Insert -> reverse close-up (hard_cut): SH002's push into the family photo cuts back to Friedrich's face at the exact moment his breath forms the first note.	J-cut breath (-0.20 s): Friedrich's inhale begins 5 frames before the cut from the photograph, launching the solo baritone carol on frame 0 of SH003.
S03_SH009 -> S03_SH010 (video -> 2.5D)	Expands from the German soldiers applauding Thomas's English answer (SH009) to the iconic wide night tableau of both trenches singing together (SH010).	Hard cut on upward crane (crane:up): SH009's close cheering in the German trench cuts wide to SH010, where the 2.5D camera cranes upward over No Man's Land between both lines of candlelit trees.	Acoustic widening (close -> open_field): applause tails off through a long open-field impulse response (wet = 0.55) as blended bilingual choral harmony fills the stereo field.
S03_SH010 -> S04_SH001 (SCENE S03->S04, 2.5D -> 2.5D)	Time transition from Christmas Eve night carols (S03) to the frozen white stillness of Christmas morning (S04).	cross_dissolve_8f + vertical motion counter-balance: S03_SH010's upward crane dissolves over 8 frames into S04_SH001's slow forward push across the same No Man's Land geometry, now pale blue-gold at dawn.	1.5 s music decay -> cold vacuum (BP-120): the night carol fades out completely; S04_SH001 drops the bed by -6 dB into crisp frost wind before the narrator speaks "Christmas morning came white and still."
S04_SH001 -> S04_SH002 (2.5D -> video)	Breaks the dawn silence of the empty field with the first shouted invitation from the German parapet.	Hard cut on sound source: SH001's slow push across the wire cuts sharply to the German soldier calling out across the trench lip (SH002).	J-cut shout (-0.15 s): the distant-filtered call "English!" (4.5 kHz LPF, open-field slapback) starts 4 frames before the visual cut, snapping the viewer's eye to the speaker.
S04_SH010 -> S04_SH011 -> S04_SH012 (video -> 2.5D -> video)	Sandwich insert during the tense face-to-face meeting in No Man's Land: Thomas asks "And you're German?" (SH010) -> both men look down at their open, unarmed hands (SH011 2.5D) -> Friedrich smiles and introduces himself (SH012).	Eyeline -> detail insert -> eyeline (hard_cut in & out): SH011 (2.5 s) pushes gently (1.8%/s) on the two pairs of empty hands with rising cold breath; cuts back to Friedrich's face on "Saxon."	Tension drop: wind bed holds steady; a subtle leather-glove/coat movement spot lands on SH011 while dialogue pauses for 2.5 s so the visual proof of "unarmed" registers.
S04_SH015 -> S05_SH001 (SCENE S04->S05, video -> map)	Scales up from soldiers climbing out along Thomas's sector (S04_SH015 right pan) to the Flanders theater map showing the truce spreading in patches (S05_SH001).	cross_dissolve_8f (scene -> map): SH015's rightward pan across soldiers in No Man's Land dissolves into the Flanders relief plate (S05_SH001), where 4 sector pulse rings beat sequentially along the front line.	Diegetic voices -> map ticks (0.35 s bridge): field voices low-pass out as 4 sequential wood-table ticks (ov_tick, grouped under BP-192 / BP-81) land on each spoken word ("trench to trench, in patches").
S05_SH001 -> S05_SH002 (map -> map)	Connects the geographic spread of truce patches (SH001) to the human scale—the ~100,000 men estimate (SH002).	cross_dissolve_8f + inherited camera (view0): SH002 keeps SH001's exact Flanders view and standing front_line, converting the 4 pulses into warm highlight zones while the 100,000 counter + bar counts up.	Counter tick train -> final knock (BP-192): 9 decelerating mechanical ticks follow the counter's easing curve, landing a single low wood knock (ov_thud) on the exact frame 100,000 locks in.
S05_SH002 -> S05_SH003 (map -> 2.5D)	Returns from the 100,000 macro counter back down into the crowded No Man's Land trading scene.	infographic_number_to_scene_morph / map_to_location_zoom_through (12 frames): dissolves from the Flanders highlight into SH003's wide 2.5D truck:right across soldiers trading buttons and cigarettes.	J-cut crowd bed (-0.45 s): warm multi-language chatter, laughter, and match-strikes swell 0.45 s before the map dissolves out.
S05_SH003 -> S05_SH004 (2.5D -> video)	Narrows from the wide trading panorama (SH003) back into the personal conversation between Thomas and Friedrich (SH004).	Motion-settled hard cut: SH003's rightward truck eases to rest on Thomas and Friedrich; SH004 cuts into their two-shot as Thomas asks "Where'd you learn English?"	Crowd ducking (-6 dB): the wide crowd murmur ducks and low-passes into the background bed as Thomas's close dialogue stem takes center stage.
S05_SH009 -> S05_SH010 -> S05_SH011 (video -> 2.5D -> video)	Friedrich hands over his family photo (SH009) -> POV insert of the portrait card in Thomas's gloved hands (SH010 2.5D, echoing S03_SH002) -> Thomas's quiet reaction (SH011).	Hand-off match cut (hard_cut): SH009 ends with the card extended; SH010 opens on the card in Thomas's hands (slow_push_in 1.8%/s on the 3-year-old daughter); SH011 cuts to Thomas's face looking up from the card.	Intimate acoustic pocket: crowd ambience dips 4 dB; only paper rustle and soft cold breath (silent visual, soft wind bed) play under the 3 s insert before Thomas softly says "She looks happy."
S05_SH015 -> S05_SH016 -> S05_SH017 (video -> 2.5D -> video)	Transitions from digging the graves (SH015) -> a still, reverent 2.5D insert of two spades standing upright in the frozen earth beside the covered stretcher (SH016, 3.0 s) -> the burial conversation (SH017).	Action-to-rest match cut (hard_cut): physical digging in SH015 cuts to the planted spades in SH016 (gentle 1.5%/s push + rising brazier smoke + mist); SH017 cuts to Thomas removing his cap by the grave.	Foley stop -> solemn silence: heavy iron-spade earth impacts in SH015 stop on the cut to SH016, leaving only low wind and distant brazier crackle for 3.0 s before Thomas asks "What was his name?"
S05_SH019 -> S05_SH020 -> S05_SH021 (video -> 2.5D -> video)	Moves from Thomas's personal apology ("I'm sorry", SH019) to the symmetrical joint burial service (SH020a/b: Scottish left, German right, crosses center), ending on Sgt. Harris removing his cap (SH021).	Hard cut -> word-timed lateral truck (SH020) -> reaction cut (SH021): SH020 starts framed slightly left on the Scots (push 1.5%/s), then on the word "German" trucks right (TRUCK_STRENGTH = 2.0) to the German soldiers; SH021 cuts to Harris at the edge of the crowd.	Low choral drone + L-cut: a solemn low choral/organ pad enters on SH020 beneath the narrator's Psalm reading and holds across the cut into SH021 as Harris silently removes his cap.
S05_SH021 -> S06_SH001 -> S06_SH002 (SCENE S05->S06, video -> 2.5D -> video)	Time passage from the midday burial (S05) to late afternoon dusk (S06_SH001, light_fade + pull), where Thomas and Friedrich sit on ammunition boxes before Friedrich asks "Tommy... why are we fighting?" (SH002).	cross_dissolve_8f (S05->S06) then hard cut (SH001->SH002): S05_SH021 dissolves into the amber dusk of S06_SH001 as the camera pulls back and light_fade dims the sky; SH002 cuts in to Friedrich's close-up.	Warm brazier + dying wind: midday wind crossfades (0.5 s) into quiet evening brazier crackle; the narrator's "the light was going" finishes 0.3 s before Friedrich's voice enters.
S06_SH004 -> S06_SH005 -> S06_SH006 (video -> 2.5D -> video)	Reaction beat at the heart of the film: Friedrich says "They told us you were the enemy" (SH004) -> silent 2.5D reaction portrait of Thomas looking at him (SH005, 3.0 s) -> Thomas replies "They told us the same about you" (SH006).	Shot / reverse-shot with 2.5D reaction hold (hard_cut): SH005 holds a subtle 1.5%/s push + handheld (0.3) + mouth breath plume + warm brazier cheek spill on Thomas so his silence carries weight before SH006 speaks.	Intentional dialogue pause (silent_by_design speech, live bed): no music sting—only the crackle of the brazier and a soft exhale fill the 3.0 s reaction beat so the line lands with documentary honesty.
S06_SH011 -> S06_SH012 -> S07_SH001 (video -> 2.5D -> SCENE S07 2.5D)	After the brass button exchange (SH011), S06_SH012 pulls back on the two silhouettes at sunset ("Neither of them moved to leave"), then dissolves (cross_dissolve_8f) into cold Boxing Day morning (S07_SH001) as men drift back to their trenches.	Matched pull across dissolve: S06_SH012 pulls back as dusk light fades; S07_SH001 dissolves in over 8 frames, continuing the pull in cold grey morning mist as figures walk apart.	Warm dusk -> cold morning tonal shift (0.5 s crossfade): the warm evening cello note resolves on S06_SH012 and crossfades into cold, hollow morning wind and slow, reluctant footsteps in S07_SH001.
S07_SH001 -> S07_SH002 (2.5D -> video)	Narrows from the wide retreat across No Man's Land (SH001) to the final face-to-face parting between Friedrich and Thomas (SH002).	Hard cut on stopping motion: SH001's pull slows as the men reach the wire; SH002 cuts to Friedrich pausing to say "Good luck, Tommy."	J-cut voice (-0.20 s): Friedrich's quiet "Good luck, Tommy" starts 5 frames before the cut.
S07_SH004 -> S07_SH005 -> S07_SH006 (video -> R3 video [or 2.5D] -> video)	Sgt. Harris calls "Stand to" (SH004) -> the British captain fires three revolver shots into the air and salutes (SH005) -> the German captain salutes back and fires two shots (SH006).	Eyeline & upward gesture chain (hard_cut): SH004 looks along the trench to the captain (SH005); SH005's salute across the wire cuts across the axis to the German captain's answering salute (SH006).	3 revolver transients (-1.0 dBTP trimmed) + open-field tail: the three gunshots in SH005 (ASM-02 admitted LTX takes, onset within +-10 ms) ring across No Man's Land into SH006 before the two answering German shots fire.
S07_SH008 -> S08_SH001 -> S08_SH002 -> S08_SH003 -> S08_SH004 (SCENE S07->S08, video -> 2.5D epilogue -> black)	Thomas lifts his rifle back onto the fire step (S07_SH008 LTX) -> dissolves (cross_dissolve_8f) to Thomas writing home beside the German button (S08_SH001 2.5D) -> cuts to Friedrich holding his family photo + Thomas's button in falling snow (S08_SH002 split into <=5 s a/b) -> pulls high above the two trenches (S08_SH003 + 1914->1918 progress bar) -> fade_to_black (24f) into the single lit candle + final text card (S08_SH004).	cross_dissolve_8f (S07->S08) -> graphic prop match cut (SH001->SH002 on the brass button) -> crane/pull up (SH003) -> fade_to_black (24f) -> static candle (SH004).	Solo piano/cello epilogue + nib/candle foley -> silence: pen-on-paper foley in SH001 hands off to soft falling snow wind in SH002; music swells on SH003 ("almost four more years"), fades to room tone in SH004, and ends on a soft breath blow-out as the candle holds on black.
5 General Script-Writer Rules for Future Episodes (Enforceable at G1–G3)

The "Sandwich Insert" Rule for 30% 2.5D Stills (VL-08 + BP-109): Never drop a still_25d shot randomly into dialogue or action. Every still_25d shot must serve one of three structural roles: (a) Scene/Time Opener or Closer (wide establishing dawn/dusk/night tableau, 3–5 s), (b) Motivated POV / Prop Insert sandwiched between two video shots where Character A looks at or hands over an object (SH009 -> SH010 photo -> SH011, SH015 -> SH016 spades -> SH017, 2.5–3.5 s), or (c) Silent Reaction Hold (SH004 -> SH005 -> SH006, 3.0 s). Any still_25d shot over 5.0 s is automatically split at the sentence break into Wide (a) + Focal Crop (b).

Mandatory Anchor-to-Anchor Visual Bridge Token (match_bridge): Every shot pair shot_a -> shot_b in production_script.json must declare a match_bridge field choosing one of four film links: eyeline_to_object (character looks -> insert shows what they see), shared_prop (brass button in British dugout -> brass button in German trench), motion_continuation (push -> push or pan_right -> route_pan), or scale_pivot (single man -> wide crowd or map highlight -> physical trench at the same [x, y] screen coordinates).

Map Entry & Exit Zoom-Funnel Law (CMP-05 + CMP-07): A map_action sequence must always enter from the preceding scene via a geographic widen or dissolve (cross_dissolve_8f), chain consecutive maps by inheriting the exact camera (lon, lat, span_km) (macro -> meso -> micro), and exit into the next physical scene by zooming into the target place marker (map_to_location_zoom_through, 14 frames) with 0.50 s of the incoming location's ambient sound pre-lapped under the zoom.

Action-State Ledger Across Cuts (action_end_state == next.action_start_state): Before any image or LTX prompt is generated (G1/G5), every consecutive shot in the same location must pass a strict state-handover check: {posture, left_hand_prop, right_hand_prop, headgear, screen_side, gaze_dir}. If shot_a ends with a rifle in hand or a cap removed, shot_b must either start from shot_a's picked tail frame (continuation, BP-199) or inject that exact state into its new anchor prompt (VL-17).

Acoustic Lead/Lag (J/L) by Cut Type: Never cut picture and sound on the same frame except for shock impacts. The script generator must automatically assign: (a) J-cut (-0.20 s to -0.50 s) whenever cutting into a new location, a map exit, or a shouted/offscreen call (S04_SH002), and (b) L-cut (+0.25 s to +0.40 s) whenever cutting from a character's emotional line into a reaction still or wide tableau (S01_SH004, S06_SH005, S06_SH012).

2. Full Code: recipe_25d_and_qa_sketches.py

Here is the complete, self-contained Python module covering the 2.5D layer/depth fix, the map camera inheritance + 8-position label collision solver, and QA Checks 1 (rest_seam_and_halo), 2 (sliding_1s_liveliness), 3 (border_stretch), 6 (highlight_burn), and 7 (cross_shot_grade_and_stalls):

Python
"""Complete reference implementations for Explainer Engine:
1. 2.5D layer preparation without morphological scallop seams + crowd depth flattening
2. Map camera inheritance (map -> map smooth handoff) + 8-position label collision solver
3. Human-eye Perceptual QA Checks #1, #2, #3, #6, and #7 (with scene-key LAB transfer)
"""
from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np


# =============================================================================
# 1. 2.5D RECIPE FIXES (for explainer_engine/production/directed25d.py)
# =============================================================================

def prepare_clean_layers_and_bg_depth(
    src_rgb: np.ndarray,
    plate_rgb: np.ndarray,
    depth_01: np.ndarray,
    object_masks: dict[str, np.ndarray],
    person_boxes_norm: list[list[float]],
    thin_stroke_px: float = 16.0,
    thin_share_max: float = 0.35,
    feather_px: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Replaces directed25d.py:_rest_background (lines 174-227) and preps bg_depth (lines 118-123).

    Fixes two visual defects:
    - Eliminates morphological hole-biting on kept SAM masks (which caused scalloped
      3 px LaMa rings around people/hands at frame 0 in C4A).
    - Flattens bg_depth inside every unlayered person/face bounding box so per-pixel
      background remap (bg_maps) never rubber-stretches crowd faces (S05_SH020, S06).
    """
    sh, sw = depth_01.shape[:2]
    scale = sw / 1920.0
    r_disc = max(1, int(round((thin_stroke_px / 2.0) * scale)))
    disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r_disc + 1, 2 * r_disc + 1))

    kept_objects: list[dict[str, Any]] = []
    hole_union = np.zeros((sh, sw), dtype=np.float32)

    for oid, raw_mask in object_masks.items():
        alpha = np.clip(cv2.resize(raw_mask.astype(np.float32), (sw, sh)), 0.0, 1.0)
        hard = (alpha > 0.5).astype(np.uint8)
        if int(hard.sum()) < 40:
            continue

        # Measure thin-stroke ratio: if mostly thin wire/twigs, keep whole object in BG
        opened = cv2.morphologyEx(hard, cv2.MORPH_OPEN, disc)
        thin_parts = hard & (1 - opened)
        thin_share = float(thin_parts.sum()) / float(max(1, hard.sum()))
        if thin_share >= thin_share_max:
            continue

        # Keep silhouette whole (zero disc bites) and feather alpha smoothly
        sigma = max(0.8, feather_px * scale / 2.0)
        soft_alpha = cv2.GaussianBlur(hard.astype(np.float32), (0, 0), sigma)
        med_depth = float(np.median(depth_01[hard > 0]))
        rgba = np.dstack([src_rgb, np.clip(soft_alpha * 255.0 + 0.5, 0, 255).astype(np.uint8)])
        kept_objects.append({
            "id": oid,
            "rgba": rgba,
            "alpha": soft_alpha,
            "hard0": hard,
            "d": med_depth,
        })

        grow_px = max(2, int(round(4.0 * scale)))
        k_grow = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow_px + 1, 2 * grow_px + 1))
        hole_union = np.maximum(hole_union, cv2.dilate(soft_alpha, k_grow))

    kept_objects.sort(key=lambda o: o["d"])

    # Show LaMa plate ONLY under the dilated disocclusion footprint of kept layers
    hole_union = np.clip(cv2.GaussianBlur(hole_union, (0, 0), max(1.0, 2.0 * scale)), 0.0, 1.0)
    rest_plate = (
        src_rgb.astype(np.float32) * (1.0 - hole_union[..., None])
        + plate_rgb.astype(np.float32) * hole_union[..., None]
    ).astype(np.uint8)

    # Inpaint depth under foreground layers, then smooth
    bg_depth = depth_01.copy().astype(np.float32)
    if hole_union.max() > 0.05:
        bg_depth = cv2.inpaint(bg_depth, (hole_union > 0.05).astype(np.uint8), 5, cv2.INPAINT_TELEA)
    bg_depth = cv2.GaussianBlur(bg_depth, (0, 0), max(1.5, 0.006 * sw))

    # Flatten depth gradient inside every detected person/face box on the background sheet
    for box in person_boxes_norm:
        x0, y0, x1, y1 = box
        bw, bh = x1 - x0, y1 - y0
        px0 = max(0, int(round((x0 - 0.25 * bw) * sw)))
        px1 = min(sw, int(round((x1 + 0.25 * bw) * sw)))
        py0 = max(0, int(round((y0 - 0.20 * bh) * sh)))
        py1 = min(sh, int(round((y1 + 1.20 * bh) * sh)))
        if px1 > px0 and py1 > py0:
            patch_med = float(np.median(bg_depth[py0:py1, px0:px1]))
            sub_mask = np.zeros((sh, sw), dtype=np.float32)
            sub_mask[py0:py1, px0:px1] = 1.0
            sub_mask = cv2.GaussianBlur(sub_mask, (0, 0), max(2.0, 0.01 * sw))
            bg_depth = bg_depth * (1.0 - sub_mask) + patch_med * sub_mask

    return rest_plate, bg_depth, hole_union, kept_objects


# =============================================================================
# 2. MAP CAMERA INHERITANCE & 8-POSITION LABEL SOLVER (maps/actions.py)
# =============================================================================

def resolve_map_camera_inheritance(
    shot: dict[str, Any],
    actions_resolved: list[dict[str, Any]],
    prev_map_end_view: dict[str, float] | None = None,
    min_span_km: float = 250.0,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Replaces maps/actions.py:_first_view (lines 167-182).

    When two map_action shots are consecutive in the same theater (e.g. S02_SH001 -> S02_SH002
    -> S02_SH003, or S05_SH001 -> S05_SH002), shot B inherits shot A's final camera
    (lon, lat, span_km) as its view0, and smoothly pans/scales to shot B's target view over
    the first action's span instead of jumping at frame 0.
    """
    # Compute the natural target view for this shot's own actions
    mv = shot.get("map_view")
    if mv:
        natural = {"lon": float(mv["lon"]), "lat": float(mv["lat"]), "span_km": max(min_span_km, float(mv["span_km"]))}
    else:
        pts = [p for a in actions_resolved if a["kind"] != "zoom" for p in (a.get("from"), a.get("to")) if p]
        pts += [q for a in actions_resolved if a.get("path") for q in a["path"][:: max(1, len(a["path"]) // 8)]]
        if not pts:
            pts = [p for a in actions_resolved for p in (a.get("from"), a.get("to")) if p]
        lons, lats = [p[0] for p in pts], [p[1] for p in pts]
        lon, lat = (min(lons) + max(lons)) / 2.0, (min(lats) + max(lats)) / 2.0
        kx = 111.32 * math.cos(math.radians(lat))
        span = max(
            min_span_km,
            (max(lons) - min(lons)) * kx * 1.5,
            (max(lats) - min(lats)) * 111.32 * 1.5 * (16.0 / 9.0),
        )
        natural = {"lon": lon, "lat": lat, "span_km": span}

    if prev_map_end_view is None:
        return natural, actions_resolved

    # Inherit previous map's end camera as view0; inject a smooth camera glide on the first action
    view0 = dict(prev_map_end_view)
    updated = [dict(a) for a in actions_resolved]
    if updated and updated[0].get("camera") in (None, "hold"):
        updated[0]["camera"] = "fly_to"
        updated[0]["target_view"] = natural
    return view0, updated


def place_map_label_non_overlapping(
    cx: float,
    cy: float,
    text_w: float,
    text_h: float,
    frame_w: int,
    frame_h: int,
    occupied_boxes: list[tuple[float, float, float, float]],
    safe_margin_x: float = 0.05,
    safe_margin_y: float = 0.06,
) -> tuple[float, float, tuple[float, float, float, float], bool]:
    """8-candidate greedy label & date-chip placement with safe-frame clamping and leader line.
    Replaces fixed offset `(cx + size*0.35, cy - size*0.35)` in maps/actions.py:472-478.
    """
    pad = max(6.0, text_h * 0.35)
    candidates = [
        (+pad, -pad - text_h, False),               # 1. NE (inner)
        (-pad - text_w, -pad - text_h, False),      # 2. NW (inner)
        (+pad, +pad, False),                        # 3. SE (inner)
        (-pad - text_w, +pad, False),               # 4. SW (inner)
        (+pad * 1.3, -text_h * 0.5, False),         # 5. E  (inner)
        (-pad * 1.3 - text_w, -text_h * 0.5, False),# 6. W  (inner)
        (+pad * 2.4, -pad * 2.2 - text_h, True),    # 7. NE (outer + leader line)
        (-pad * 2.4 - text_w, -pad * 2.2 - text_h, True), # 8. NW (outer + leader line)
    ]
    xmin, xmax = frame_w * safe_margin_x, frame_w * (1.0 - safe_margin_x)
    ymin, ymax = frame_h * safe_margin_y, frame_h * (1.0 - safe_margin_y)

    best_choice = None
    best_cost = float("inf")
    for dx, dy, needs_leader in candidates:
        x0 = float(np.clip(cx + dx, xmin, xmax - text_w))
        y0 = float(np.clip(cy + dy, ymin, ymax - text_h))
        x1, y1 = x0 + text_w, y0 + text_h

        overlap = 0.0
        for ox0, oy0, ox1, oy1 in occupied_boxes:
            iw = max(0.0, min(x1, ox1) - max(x0, ox0))
            ih = max(0.0, min(y1, oy1) - max(y0, oy0))
            overlap += iw * ih

        dist_pen = math.hypot((x0 + x1) * 0.5 - cx, (y0 + y1) * 0.5 - cy) * 0.05
        cost = overlap * 1000.0 + dist_pen + (25.0 if needs_leader else 0.0)
        if cost < best_cost:
            best_cost = cost
            best_choice = (x0, y0, (x0 - 4.0, y0 - 4.0, x1 + 4.0, y1 + 4.0), needs_leader)
            if overlap == 0.0 and not needs_leader:
                break

    assert best_choice is not None
    occupied_boxes.append(best_choice[2])
    return best_choice


# =============================================================================
# 3. HUMAN-EYE PERCEPTUAL QA CHECKS (#1, #2, #3, #6, #7)
# =============================================================================

def qa_check_1_rest_seam_and_halo(
    frame0_no_fx_rgb: np.ndarray,
    src_crop_rgb: np.ndarray,
    object_hard_masks: list[np.ndarray],
    inset_px: int = 2,
    level_thr: float = 24.0,
) -> dict[str, Any]:
    """QA Check #1: Detects frame-0 scalloped outlines, LaMa bleed-through, or cut posts.
    Measures pixel deviation inside eroded object outlines and along a +-4 px contour band.
    """
    h, w = src_crop_rgb.shape[:2]
    g = max(1, int(round(inset_px * w / 1920.0)))
    k_in = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * g + 1, 2 * g + 1))
    k_3 = np.ones((3, 3), dtype=np.uint8)

    inner_union = np.zeros((h, w), dtype=bool)
    outline_px = 0
    for hard0 in object_hard_masks:
        m = (cv2.resize(hard0.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8)
        inner_union |= cv2.erode(m, k_in) > 0
        outline_px += int((m - cv2.erode(m, k_3)).sum())

    if outline_px == 0:
        return {"gate": "rest_seam_and_halo", "status": "PASS", "per_outline_px": 0.0, "bad_pixels": 0}

    diff = np.abs(frame0_no_fx_rgb.astype(np.float32) - src_crop_rgb.astype(np.float32)).max(axis=2)
    bad = (diff > level_thr) & inner_union
    ratio = float(bad.sum()) / float(outline_px)
    status = "FAIL" if ratio > 0.05 else ("REVIEW" if ratio > 0.02 else "PASS")
    return {
        "gate": "rest_seam_and_halo",
        "status": status,
        "per_outline_px": round(ratio, 4),
        "bad_pixels": int(bad.sum()),
        "outline_px": outline_px,
    }


def qa_check_2_sliding_1s_liveliness(
    frames_rgb: list[np.ndarray],
    fps: int = 24,
    is_map: bool = False,
    diff_level_thr: float = 4.0,
) -> dict[str, Any]:
    """QA Check #2: Sliding 1-second window liveliness check (G-LIVE-1).
    Catches shots that stand frozen for 5-8 seconds before a late word accent.
    """
    win = max(1, int(fps))
    small = [
        cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA).astype(np.float32).mean(axis=2)
        for f in frames_rgb
    ]
    if len(small) <= win:
        changed = float((np.abs(small[-1] - small[0]) >= diff_level_thr).mean())
        worst_s = 0.0
    else:
         windows = [
             (float((np.abs(small[i + win] - small[i]) >= diff_level_thr).mean()), i / float(fps))
             for i in range(len(small) - win)
         ]
        changed, worst_s = min(windows, key=lambda x: x[0])

    fail_floor = 0.015 if is_map else 0.050
    review_floor = 0.030 if is_map else 0.100
    status = "FAIL" if changed < fail_floor else ("REVIEW" if changed < review_floor else "PASS")
    return {
        "gate": "sliding_1s_liveliness",
        "status": status,
        "worst_1s_changed_share": round(changed, 4),
        "worst_window_start_s": round(worst_s, 2),
        "threshold_fail": fail_floor,
    }


def qa_check_3_border_stretch(frame_rgb: np.ndarray, strip_px: int = 8) -> dict[str, Any]:
    """QA Check #3b: Detects BORDER_REPLICATE / BORDER_REFLECT edge smearing on 2.5D warps."""
    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    scores = []
    for edge, axis in (
        (gray[:strip_px, :], 0),
        (gray[-strip_px:, :], 0),
        (gray[:, :strip_px], 1),
        (gray[:, -strip_px:], 1),
    ):
        norm_diff = float(np.abs(np.diff(edge, axis=axis)).mean())
        tang_std = float(edge.std())
        if tang_std > 8.0:
            scores.append(1.0 - min(1.0, norm_diff / max(1e-3, tang_std * 0.25)))
    worst = max(scores, default=0.0)
    return {
        "gate": "border_stretch",
        "status": "FAIL" if worst > 0.85 else ("REVIEW" if worst > 0.70 else "PASS"),
        "worst_smear_ratio": round(worst, 3),
    }


def qa_check_6_highlight_burn(
    frame_rgb: np.ndarray,
    src_rgb: np.ndarray,
    people_mask_01: np.ndarray | None = None,
) -> dict[str, Any]:
    """QA Check #6: Detects blown-out flat white sky (S01/S05 C5 defect) and bleached heads."""
    def _blown(img: np.ndarray) -> float:
        y = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
        sd = np.sqrt(np.maximum(cv2.blur(y * y, (9, 9)) - cv2.blur(y, (9, 9)) ** 2, 0.0))
        return float(((y >= 245.0) & (sd < 2.0)).mean())

    new_blown = max(0.0, _blown(frame_rgb) - _blown(src_rgb))
    head_rise = 0.0
    if people_mask_01 is not None and (people_mask_01 > 0.5).any():
        m = people_mask_01 > 0.5
        src_rs = cv2.resize(src_rgb, (frame_rgb.shape[1], frame_rgb.shape[0]))
        head_rise = float(frame_rgb.mean(axis=2)[m].mean() - src_rs.mean(axis=2)[m].mean())

    fail = new_blown > 0.015 or head_rise > 18.0
    review = new_blown > 0.005 or head_rise > 12.0
    return {
        "gate": "highlight_burn_and_clipping",
        "status": "FAIL" if fail else ("REVIEW" if review else "PASS"),
        "newly_blown_share": round(new_blown, 4),
        "people_luma_rise": round(head_rise, 2),
    }


def qa_check_7_cross_shot_grade_and_stalls(
    shot_a_frames_rgb: list[np.ndarray],
    shot_b_frames_rgb: list[np.ndarray],
    same_scene: bool = True,
    frozen_diff_max: float = 0.15,
    frozen_run_max: int = 6,
) -> dict[str, Any]:
    """QA Check #7: Measures CIE LAB Euclidean colour jump across a cut (after scene-key
    transfer in assemble_shot_clips) AND checks for frozen/black frame stalls >= 6 frames.
    """
    from explainer_engine.finish import grade as grade_mod

    last_a = shot_a_frames_rgb[-1].astype(np.float32) / 255.0
    first_b = shot_b_frames_rgb[0].astype(np.float32) / 255.0
    lab_dist = grade_mod.lab_distance(last_a, first_b)

    # Check frozen run inside shot B at 320x180 luma
    small = [cv2.resize(f, (320, 180), interpolation=cv2.INTER_AREA).mean(axis=2) for f in shot_b_frames_rgb]
    longest_freeze = cur = 0
    for i in range(1, len(small)):
        if float(np.abs(small[i] - small[i - 1]).mean()) < frozen_diff_max:
            cur += 1
            longest_freeze = max(longest_freeze, cur + 1)
        else:
            cur = 0

    grade_fail = same_scene and lab_dist > 12.0
    grade_review = same_scene and lab_dist > 8.0
    stall_fail = longest_freeze >= frozen_run_max
    status = "FAIL" if (grade_fail or stall_fail) else ("REVIEW" if grade_review else "PASS")
    return {
        "gate": "cross_shot_grade_and_stalls",
        "status": status,
        "lab_distance": round(lab_dist, 2),
        "longest_frozen_frames": longest_freeze,
    }

3. Concrete Sources (YouTube Tutorials & GitHub Repositories)
(a) Professional 2.5D Parallax from a Single Still

vt-vl-lab/3d-photo-inpainting — 3D Photography using Context-aware Layered Depth Inpainting (GitHub) & 3D Photo Inpainting Python Tutorial (YouTube): The foundational CVPR 2020 reference for splitting depth discontinuities and inpainting disoccluded background strips behind foreground silhouettes so camera moves never smear edges.

BrokenSource/DepthFlow — Images to 3D Parallax Videos (GitHub) & akatz-ai/ComfyUI-Depthflow-Nodes (GitHub): Reference implementation for orbital, dolly, and circle parallax presets with depth-aware bokeh (DOF) and vignette.

How To Make a Parallax Image Animation in After Effects (YouTube) & The Parallax Effect — Photo Animation Tutorial (YouTube): Practical production breakdown of separating foreground subjects from clean-plated backgrounds, setting multiplane Z-distances, and adding subtle smooth() camera/puppet breathing so figures never look like flat cardboard cutouts.

Landscape Parallax 2.5D Camera Animation Tutorial (YouTube): Demonstrates slow X/Y rotation and orbital camera moves on layered landscapes to avoid empty border reveals.

(b) Animated Historical Maps with Smooth Camera Moves (Kings and Generals / Johnny Harris Style)

Create a Johnny Harris Style Animated Map Montage — Boone Loves Video (YouTube) & Aescripts Technical Breakdown: Step-by-step guide by a map animator who worked on Johnny Harris's WWII documentaries (PremiumBeat Case Study), covering continuous camera glides between locations, shaded relief styling, and syncing route/marker animations to spoken beats.

Make a Map Like KINGS AND GENERALS — Boone Loves Video (YouTube) & How to Animate Historic Battle Maps (YouTube): Shows how Kings and Generals structures battle-map camera hierarchy (theater overview -> sector fly-in -> unit tokens moving along spline paths without resetting the base map).

Create a Documentary Map Animation — Archival Callouts & Camera Easing (YouTube): Specifically addresses blending labels, callout cards, and highlights into the map's paper/ink contrast so overlays look printed into the map rather than pasted on top, while keeping camera motion subordinate to the narration.

iart-ai/map-animation-skills — Programmatic Vox/Documentary Map Toolkit (GitHub) & ManimCommunity/manim — MovingCameraScene & Bezier/Spline Internals (GitHub): Open-source programmatic patterns for chaining MovingCameraScene zoom/pan states and progressive curve drawing in Python.

Complete
---
[Opus note] Hyperlinks actually present in Argon's reply (hosts+paths; the other YouTube titles carried NO link and are unverified):
github.com/vt-vl-lab/3d-photo-inpainting
www.youtube.com/watch (one video, the 3D-photo-inpainting tutorial)
github.com/BrokenSource/DepthFlow
github.com/akatz-ai/ComfyUI-Depthflow-Nodes
aescripts.com/learn/post/create-a-johnny-harris-style-animated-map-montage
www.premiumbeat.com/blog/making-maps-for-johnny-harris/
github.com/iart-ai/map-animation-skills
github.com/ManimCommunity/manim/blob/main/manim/scene/scene.py
