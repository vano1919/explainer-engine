Gemini said

I've audited all five map clips and your map pipeline code, and rendered a unified 18.875-second (453 frames at 24 fps, 1920x1080) continuous S02 map sequence with its keyframe contact sheet and standalone Python generator script (s02_continuous_map_generator.py, open in Canvas):

S02 Continuous Map Generator
Download
#!/usr/bin/env python3
"""Standalone Documentary Map Engine: Continuous S02 Sequence (S02_SH001 -> S02_SH002 -> S02_SH003).
Re-creates the three disconnected S02 map clips of "Truce 1914" as ONE continuous 18.875-second
(453 frames @ 24 fps, 1920x1080) documentary camera move in the Kings and Generals / Johnny Harris
cartographic style:
  1. Historically accurate August-December 1914 borders (German Empire including Alsace-Lorraine /
     Elsass-Lothringen & Eupen-Malmedy, Belgium, Luxembourg, France, Netherlands, Switzerland, UK)
     with zero post-1918 or modern borders, rendered as scale-invariant screen-space vectors.
  2. Multi-scale Natural Earth SR_HR shaded relief + parchment grain + bathymetric sea shelf +
     micro-relief detail enhancement so the 8x zoom into Flanders never blurs.
  3. Three historical German Schlieffen right-wing invasion axes (1st, 2nd, 3rd/4th Armies) timed
     to the spoken words "Everyone said it would be over by Christmas" (frames 76..118).
  4. Seamless camera pull-out and pan (no cut at frame 133) as the August advance ghosts to 22%
     opacity and the 760 km (475 mi) Western Front trench line draws from Nieuwpoort (North Sea)
     to Pfetterhouse (Swiss border) on "one line of trenches, from the North Sea to Switzerland"
     (frames 231..308), accompanied by a non-jittering live kilometer/mile counter.
  5. Seamless logarithmic zoom (span_km 960 -> 105 km, no cut at frame 321) into the Flanders
     sector on "Here, in Flanders" (frames 334..395), keeping the trench line standing at frame 321
     and lighting the Frelinghien-Ploegsteert sector highlight on "close enough to hear each other
     cough" (frames 409..452) with a 0.50 s trench-wind/cough J-cut prelap into S02_SH004.
  6. 8-position greedy bounding-box label solver with safe-frame clamping and altitude-tier fading
     so labels never collide with each other, the trench line, HUD cards, or frame edges.
"""
from __future__ import annotations
import math
import os
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
# =============================================================================
# 1. CONSTANTS, GEOMETRY & 1914 HISTORICAL GIS DATA
# =============================================================================
WIDTH = 1920
S02_continuous_map_sample
 MP4 

ხუთივე რუკის კლიპს ერთი და იგივე ძირეული პრობლემა აქვს: თითოეული კადრი ნულიდან იწყებს კამერას (actions.py:_first_view), სიტყვების დროებს ხაზოვნად ითვლის პაუზების გარეშე (actions.py:word_frames), ხოლო თარიღებსა და წარწერებს გეოგრაფიულ კოორდინატებზე აბამს შეჯახების შემოწმების გარეშე.
ამის გამო კადრებს შორის კამერა უხეშად ხტება, სანგრების ხაზი კადრის დასაწყისში ქრება (f < a["start"]), ფლანდრიის ზუმი კი საერთოდ არ სრულდება (fly_to უგულებელყოფს value=60 კმ-ს).
ქვემოთ მოცემულია ხუთივე კლიპის კადრ-კადრ გარჩევა ზუსტი ტაიმკოდებით და კოდის ფუნქციების მითითებით, სადაც თითოეული ხარვეზი იბადება.
ასევე დავარენდერე S02-ის უწყვეტი 18.875-წამიანი (1920x1080, 24 fps) ახალი ვერსია 1914 წლის ისტორიული საზღვრებით (ელზას-ლოთარინგია გერმანიის იმპერიაში), შლიფენის სამი მიმართულებით, 760 კმ-იანი ორმაგი ფრონტის ხაზითა და ფლანდრიის უწყვეტი ზუმით.
ბოლო ნაწილში გაწერილია მათემატიკური მოდელი და ზუსტი ცვლილებები თქვენს კოდში (actions.py, plate.py, map_clip.py, cinematic_transitions.py) შესაბამისი pytest შემოწმებებით.

1. Frame-by-Frame Critique of the Five Clips
Clip (Dur / Frames)	Timestamp (Frame)	Visual, Motion, or Audio-Sync Defect	Root Cause in Pipeline Code (File : Function)
S02_SH001 (5.54s / 133f)	00:00.00–00:01.92 (f0–f46)	Dead opening & missing 1914 borders: Blank beige relief with zero country borders or labels while narrator speaks "The war had begun in August."	maps/geo.py:dataset bundles modern Natural Earth 1:50m vectors; maps/plate.py:draw_base (line 133) draws faint modern borders (0.0016*h) with no 1914 sovereignty layer.
S02_SH001	00:01.96–00:05.50 (f47–f132)	Floating date text on water: "August 1914" spawns on the English Channel coast (f47, 0.46s after "August" at f36) and drifts diagonally across the water as the camera pans.	story/production_script.json authors "August 1914" as kind: "label" at from: "chip_aug" (1.584°E, 50.892°N); maps/actions.py:_draw_one (line 473) projects it via px(a["from"]) instead of screen-space HUD coordinates.
S02_SH001	00:02.46 vs 00:03.21 (f59 vs f77)	0.75 s audio-visual desync: map_route_draw foley starts at 00:02.46 (f59) during a 0.83s speech pause, while "Everyone" and the arrow actually start at 00:03.21 (f77).	maps/actions.py:word_frames (lines 80–81) spreads words uniformly across [0.06*N, 0.88*N], ignoring the 0.83s sentence pause after "August." (production/av_events.json records spine_basis: "estimated").
S02_SH001	00:03.21–00:05.08 (f77–f122)	Blue square & route flying off top edge: A blue unit box (marker) drags a red curve that shoots off the top edge (y < 0) at 00:04.50–00:05.50 with no arrowhead.	maps/actions.py:camera (line 233) route_pan locks the camera center to polyline_point(path, head) with min(1.0, 4*u), pushing Aachen/Brussels off the top of the frame.
S02_SH002 (7.83s / 188f)	00:00.00 (f0)	Jarring camera snap at cut: View jumps instantaneously from tight Marne framing (span_km≈260) to wide Western Europe (lon=4.95, lat=49.31, span_km=1000), and the August arrow vanishes on the cut.	maps/actions.py:_first_view (lines 167–170) resets view0 to shot["map_view"] per clip with zero camera state or layer inheritance from S02_SH001.
S02_SH002	00:00.79–00:04.88 (f19–f117)	3.4 s dead window & late trench draw: "December 1914" floats over Kent (f19), then nothing draws for 3.4s while narrator says "dug itself into the ground: one line of trenches"; trench draw starts at 00:04.92 (f118), 0.88s after "trenches" (f98–f108).	production_script.json anchors front_line to at_word: "trenches" (f107 estimated, f118 rendered) instead of "one" (f98), and maps/actions.py:camera only applies a 4% DRIFT.
S02_SH002	00:04.92–00:07.83 (f118–f187)	Segmented caterpillar line & label collisions: Single thick black-and-coral dashed line (29 px casing) splinters into jagged black comb artifacts at the Verdun/St-Mihiel bend; "North Sea" (00:05.00) and "Switzerland" (00:06.75) touch the line tips.	maps/draw.py:Canvas.line (lines 189–190) draws unjoined 2-point segments per dash run; maps/actions.py:_draw_one (line 477) uses fixed (cx + 0.35*size, cy - 0.35*size) offset with zero obstacle check.
S02_SH003 (5.50s / 132f)	00:00.00–00:00.38 (f0–f9)	Trench line vanishes for 9 frames at cut: Screen opens completely blank (f0–f9), then the full trench line pops back in at 00:00.42 (f10).	S02_SH003.A0 has at_word: "Here" (start=f9 from LEAD_IN=0.06); maps/actions.py:draw (line 303) skips if f < a["start"]: continue even when cues: "none" denotes a pre-existing line.
S02_SH003	00:00.42–00:02.83 (f10–f68)	Broken Flanders zoom (stays at 1000 km): Camera jerks slightly north-west (f12–f28) but never zooms into Flanders (value: 60 km), staying at continental scale showing all of England and France.	S02_SH003.A1 sets "kind": "zoom", "camera": "fly_to", "value": 60. In maps/actions.py:camera (lines 226–235), elif cam == "fly_to": interpolates with cur["span_km"] (1000 km), ignoring a["value"]!
S02_SH003	00:02.83 vs 00:03.75 (f68 vs f90)	0.92 s premature click & tiny highlight: map_arrive_click fires at 00:02.83 (f68), but the tiny yellow highlight dot (888 px area) only fades in at 00:03.75 (f90), and "Flanders" collides with the trench curve.	maps/actions.py:_draw_one (line 469) scales highlight radius at 1000 km macro view (8 km / 0.52 km/px = 15 px), while word_frames misplaces "close".
S05_SH001 (6.21s / 149f)	00:00.00–00:06.21 (f0–f148)	39.6x relief blur & 1.96 s frozen opening: Terrain is a blurry beige smudge (span_km=90 upsamples 1.85 km/px SR_HR by 39.6x); screen is frozen from 00:00.00–00:01.96 (f0–f46), then 4 pulses overlap into one muddy bullseye (00:03.54–00:06.21).	maps/relief.py:sample (line 87) bicubic-upsamples SR_HR (1/60°) far beyond the 3.0x ceiling in maps/actions.py:Plate.upsample (line 534); pulse (line 465) uses fixed screen-fraction radius (0.09*h = 97 px).
S05_SH002 (6.79s / 163f)	00:00.00–00:00.46 (f0–f11)	12-frame blank flash & coastline jump at cut: Trench line disappears for 0.46s (f0–f11), snaps back at f12 (00:00.50), and the yellow highlight pops at f28 (00:01.17) while the coastline jumps outward.	S05_SH002 resets view0 to span_km=90 (undoing S05_SH001's 4% DRIFT) and delays front_line/highlight until word 0 "Nobody" (start=f9..f12).
S05_SH002	00:04.17–00:06.46 (f100–f155)	"0 men (estimate)" & jittering counter box: Counter pops up reading "0 men (estimate)" at 00:04.17 (f100), and the orange box stretches and jitters horizontally every frame as digits change (825 -> 66,764 -> 100,000).	maps/actions.py:_draw_one (lines 484–489) only locks box width w to the final value if p.get("card"):, recomputing w = c.text_width(text, size) + size every frame when card == False.
2. How the Continuous S02 Sample Works

1914 Historical Borders & Front-Line Data Sources:

1914 Sovereign Boundaries: Sourced from the CShapes 2.0 Historical GIS Dataset (ETH Zürich ICR) and aourednik/historical-basemaps (world_1914.geojson) (cleaned pipeline in Uspectacle/historical-basemaps-cleaned). Unlike modern Natural Earth 1:10m Cultural Vectors, the 1914 Franco-German border follows the 1871–1918 Treaty of Frankfurt line along the Vosges crest (Ballon d'Alsace -> Col de la Schlucht -> Donon -> west of Metz and Thionville), placing Alsace-Lorraine (Reichsland Elsaß-Lothringen) and Eupen-Malmedy inside the German Empire.

Physical Relief & Hydrography: Uses Natural Earth 1:10m Shaded Relief (SR_HR) paired with Natural Earth 1:10m Physical Vectors (rivers Yser, Lys, Scarpe, Somme, Aisne, Marne, Meuse, Moselle, Rhine).

December 1914 Trench Line & Flanders Sector: Waypoints from Nieuwpoort (2.75°E, 51.13°N) through Ypres, Wulverghem, Ploegsteert Wood, Frelinghien-Houplines, Armentières, Fleurbaix, La Bassée, Arras, Noyon, Soissons, Reims, Verdun, and Saint-Mihiel to Pfetterhouse on the Swiss border (7.15°E, 47.50°N) are grounded in The Western Front Association TrenchMapper Portal, McMaster Libraries WWI Trench Maps Archive, and Historial de la Grande Guerre Front-Line Cartography.

Layers, Palette, Typography & Scale-Invariant Styling:

Base Plate (MasterCartographicPlate): Fuses the 1000 km and 530 km SR_HR relief plates at 3840x2160 using a cosine feather window (np.clip(np.sin(...), 0, 1)**0.45), injects multi-octave Sobel micro-hillshading (sigma=1.5 and 4.8 px) plus 1.4% parchment fiber grain over #F4ECDC paper, and grades the North Sea/Channel from #223444 deep water to #405C70 coastal shelf via Euclidean distance transform (cv2.distanceTransform).

Scale-Invariant Screen-Space Vectors: 1914 borders (7 px #1F2430 alpha-85 casing + 2 px dashed core) and rivers (3 px #4A7694) are projected per frame via view.to_px so they never pixelate during the 9.3x zoom into Flanders.

Dual-Opposed Trench Line: Computes unit normals 
𝑛
=
(
−
𝑑
𝑦
,
𝑑
𝑥
)
/
∥
Δ
𝑝
∥
n=(−dy,dx)/∥Δp∥ along the Catmull-Rom spline to offset an Entente steel-blue line (#2A6F9E, west) and Imperial German crimson-vermilion line (#D94E34, east) around a #1F2430 core with perpendicular traverse ticks every 26 px and a 14 px Gaussian combat glow.

Typography: Uses Inter / InterDisplay (Black 30 px HUD headers, Bold 24 px accent pills, SemiBold 21 px place pills), with fixed-width HUD cards (w - 465..w - 40) so counters never jitter.

Camera Path Maths, Label Solver & Word-Locked Audio Sync:

Log-Scale Zoom with Pan Coupling (lerp_view): Width interpolates logarithmically, 
𝑆
(
𝑢
)
=
exp
⁡
(
ln
⁡
𝑆
0
+
(
ln
⁡
𝑆
1
−
ln
⁡
𝑆
0
)
𝑒
(
𝑢
)
)
S(u)=exp(lnS
0
	​

+(lnS
1
	​

−lnS
0
	​

)e(u)) where 
𝑒
(
𝑢
)
e(u) is cubic ease-in-out. To prevent target overshoot during large scale changes (940 km -> 125 km), pan progress couples to scale progress: 
𝑢
pan
=
0.65
𝑆
(
𝑢
)
−
𝑆
0
𝑆
1
−
𝑆
0
+
0.35
𝑒
(
𝑢
)
u
pan
	​

=0.65
S
1
	​

−S
0
	​

S(u)−S
0
	​

	​

+0.35e(u).

8-Position Greedy Label Solver (place_label_8pos): Evaluates 8 candidate boxes around (cx, cy) (NE, NW, SE, SW, E, W, outer-NE, outer-NW), clamps to safe margins (x \in [54, 1866], y \in [40, 1014]), and minimizes intersection area 
∑
𝐴
overlap
×
1000
+
rank
×
8
∑A
overlap
	​

×1000+rank×8 against all HUD cards, active arrows, trench segments, and prior labels.

Frame-Exact Word & Sound Schedule (24 fps across 453 frames):

f036 (01.50s, word "August"): Top-left AUGUST 1914 HUD card stamps in + wood tick (195 Hz, 45 ms).

f076–f118 (03.17s–04.92s, "Everyone ... Christmas"): Three German Schlieffen arrows draw via march_ease + filtered charcoal draw loop (f076–f118) + arrival tick on the Marne (f118, 165 Hz).

f133 (05.54s, S02_SH001 -> S02_SH002 handover): Zero cut; camera smoothly widens (660 -> 950 km) as August arrows fade to 22% ghost traces (f145–f215).

f149 (06.21s, "December"): HUD card flips to DECEMBER 1914 + wood tick (190 Hz).

f231–f308 (09.62s–12.83s, "one line of trenches ... Switzerland"): Dual trench line draws 760 km with live counter + charcoal draw foley (f231–f308) + pin ticks on "North Sea" (f276) and "Switzerland" (f293).

f321 (13.38s, S02_SH002 -> S02_SH003 handover): Zero cut; trench line stands at u=1.0; log-scale fly_to zoom (940 -> 125 km, f334–f398) on "Here, in Flanders".

f409–f452 (17.04s–18.83s, "close ... cough"): Frelinghien–Ploegsteert amber glow + pulse rings + 30–50 YARDS APART card (f409 click) + 0.50s trench-wind J-cut prelap (f440–f452).

3. Concrete Changes to Your Pipeline Code & Verification Tests

explainer_engine/maps/actions.py — Fix fly_to zoom, standing lines, camera inheritance, fixed-width counters, and 8-position labels:

Change camera() (lines 226–235): Merge cam in ("zoom", "fly_to") so span = float(a["value"]) if a.get("value") else cur["span_km"] is passed to _lerp_view with log-scale pan coupling.

Change _progress() (lines 192–198) & draw() (line 303): When a.get("cues") == "none" or a.get("stands"), set a["start"] = 0 and return 1.0 in _progress() so inherited front lines stand from frame 0 without disappearing on f0..f9.

Change _first_view() (lines 167–182): Accept prev_map_end_view: dict | None; when the previous shot is map_action in the same location, set view0 = prev_map_end_view and attach a smooth fly_to move to the shot's natural map_view.

Change _draw_one() (lines 472–490): Route from: "chip_*" date actions to a screen-space HUD card ((0.04*w, 0.04*h)), lock counter box width w to the final formatted value unconditionally (remove if p.get("card"): guard on line 485), and replace the fixed (cx + 0.35*size, cy - 0.35*size) label offset with place_label_8pos().

Test: pytest tests/unit/test_maps.py -k "test_fly_to_honours_value_span and test_standing_front_line_frame0 and test_counter_box_width_constant and test_label_8pos_no_collision"

explainer_engine/maps/plate.py & explainer_engine/maps/geo.py — Add borders_1914 layer and multi-resolution DEM fallback:

Change geo.dataset() (line 26) & plate.draw_base() (lines 133–142): Load data/borders_1914.json.gz (extracted from CShapes 2.0 1914-08-01 polygons) when episode.historical_period.start_year == 1914, and add deterministic micro-hillshade synthesis in plate.relief_rgb() (lines 65–80) whenever view.span_km / view.width < 0.35 (upsample > 3.0x).

Test: pytest tests/unit/test_maps.py -k "test_1914_borders_alsace_lorraine and test_micro_relief_sharpness_under_100km"

explainer_engine/production/map_clip.py — Pass measured word spines and chain consecutive map cameras:

Change render_action_map_clip() (lines 112–128): Load the shot's measured Whisper/forced-alignment word spine from production/spines/<shot_id>.json when available, and persist end_camera = MA.camera(p, p["frames"] - 1) into cache_dir / f"{shot_id}_end_view.json" so the next consecutive map_action shot inherits it automatically.

Test: pytest tests/unit/test_plan_step_3.py -k "test_consecutive_map_clips_zero_camera_jump"

explainer_engine/edit/cinematic_transitions.py — Zero-dissolve seamless cut between camera-chained maps:

Change select_optimal_cinematic_transition() (lines 137–163): Add branch elif is_a_infographic and is_b_infographic and continuity["same_location"]: returning transition_type = "hard_cut_with_jl_bridge", transition_frames = 0, audio_j_cut_prelap_sec = 0.15 so camera-matched consecutive map shots join seamlessly on exact frame boundaries without double-exposure ghosting of HUD cards, while keeping map_to_location_zoom_through (14f, 0.50s J-cut) on S02_SH003 -> S02_SH004.

Test: pytest tests/unit/test_c4a_review_fixes.py -k "test_map_to_map_seamless_handover_and_map_to_scene_zoom"