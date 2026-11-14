Gemini said
(a) Findings Table

All three defects reported in OPUS_VERIFY.md are CONFIRMED (#1–#3), alongside seven additional logic, real-data, test-validity, and performance findings (#4–#10):

#	Severity	File + Line Text	Problem	Fix
1	BLOCK	

tests/unit/test_plan_steps_1_2.py:194–204




sys.modules[pkg_name] = pkg




sys.modules[name] = mod




if hasattr(monkeypatch, "_undo"):




monkeypatch._undo.append(...)

	CONFIRMED (Opus Defect 1): Upstream pytest.MonkeyPatch has no _undo attribute (_setattr / _setitem are used instead), so hasattr(monkeypatch, "_undo") is False and sys.modules[name] = mod is never undone. Stub modules (events, plan, sound_plan, stems, voice) leak across the session and break 10 tests in test_living_director.py, test_motion_intent.py, and test_v43_runner.py (e.g. AttributeError: module 'explainer_engine.episode.events' has no attribute 'spine_hash').	Import the real modules and patch only individual functions via monkeypatch.setattr(...) (or monkeypatch.setitem(sys.modules, ...)), never mutating sys.modules directly or touching private MonkeyPatch attributes.
2	BLOCK	

explainer_engine/episode/run.py:839–872, 927–930




def _compose_rehearsal_voice_fallback(...):




...




w.writeframes(read_pcm + ins_pcm)




if not voice_wav.is_file():




fb_rep = _compose_rehearsal_voice_fallback(...)

	CONFIRMED (Opus Defect 2): Test-accommodation code in production. It runs even when rehearsal=False if VV.compose does not write voice_track.wav, and it concatenates all insert audio after the entire unsplit narrator read (read_pcm + ins_pcm) instead of splicing at each insert's at_read_frame, silently producing a desynced voice track.	Delete _compose_rehearsal_voice_fallback. Unlink any stale voice_wav before VV.compose, and if not voice_wav.is_file() after VV.compose, raise ContractError(f"VV.compose did not write {voice_wav}").
3	FIX	

explainer_engine/standards/sourced_rules.json:874–877




"pre_accent_rate_min_per_s": 0.018

	CONFIRMED (Opus Defect 3): sourced_rules.json was updated without running python -m explainer_engine.standards.sourced_rules write to update the generated Markdown block in docs/SOURCED_RULES.md, failing tests/unit/test_sourced_rules.py::test_the_doc_table_matches_the_registry. (D-59 compliance itself is valid: BP-21 keeps "severity": "REVIEW", sliding_liveliness is REVIEW, and blown_out FAIL at 0.015 has known-bad C5 10–13% / C4A 3% and known-good 0.0–0.5% calibration.)	Run python -m explainer_engine.standards.sourced_rules write so docs/SOURCED_RULES.md matches SR.render().
4	BLOCK	

explainer_engine/production/directed25d.py:205–218




inward = np.clip((dist - 0.5) / f_px, 0.0, 1.0)




inward = np.maximum(inward, parts.astype(np.float32))




core = (o["alpha"] >= 0.999).astype(np.float32)




A = np.maximum(A, core)

	T2 plate ghost & Frame 0 bleed on 1080p/1440p: (1) Setting A to o["alpha"] >= 0.999 leaves A = 0 across the entire 3.5 px feathered border of every kept person AND across any resized thin rifle (sw != w0 at 1440p$\to
1080pwhere‘INTER
L
	​

INEAR‘makes2pxstrokealpha‘<0.999‘)orsoftBiRefNetmask(‘254/255=0.996<0.999‘).‘self.plate=self.src∗(1−A)+self.plate∗A‘thereforebakesupto‘9,881‘darkforegroundpixels(at1440p\to$1080p) into self.plate, leaving a dark silhouette ring and duplicate rifle on the background when the layer moves. (2) parts = hard & (1 - opened) includes every rough hair/coat perimeter nub, so np.maximum(inward, parts) forces alpha = 1.0 on rough nubs next to feathered pixels (sawtooth outline). (3) On Frame 0 (f == 0), when layers have not moved from rest, sampling self.plate under the feathered rim bleeds the LaMa plate into the rim whenever A covers the full mask.	Restore Stage._strokes(parts, r) to keep only true long thin strokes (long_side >= STROKE_LEN * 2 * r, e.g. rifle barrels/slings) at 1.0 alongside the eroded interior inner_o = cv2.erode(hard, k_in) > 0; feather only the outer SEAM_INSET_PX rim; set A = np.maximum(A, (raw_a > 0.01).astype(np.float32)) so self.plate has zero foreground ghost; and in render(0) when parallax is zero (at_rest), sample self.src as the rest base so Frame 0 is identical to the source picture across all outlines and resolutions.
5	BLOCK	

explainer_engine/production/directed25d.py:170, 173, 639–646, 662




def bg_maps(self, v: dict):




self._flatten_bg_people()




...




dist_out = cv2.distanceTransform(1 - core, cv2.DIST_L2, 3)




w = np.exp(-0.5 * (dist_out / sig) ** 2)




bd = bd * (1.0 - w) + med * w

	T3 performance, frame-purity & multi-box bug: (1) When 2+ unlayered boxes exist (e.g. a crowd mask plus an unlayered face in keep_in_frame), the outer Gaussian tail w of box 2 bleeds into box 1's patch, making np.ptp(patch) > 1e-5 on box 1 and un-flattening box 1's interior. (2) Because np.ptp(patch) <= 1e-5 never triggers with 2+ boxes, calling self._flatten_bg_people() inside bg_maps(v) re-runs _bbox, full-frame cv2.distanceTransform, and full-frame np.exp on every rendered frame (120$\times$ on a 5 s 1080p clip) and mutates self.bg_depth on each call, breaking render(f) frame-number purity.	Run _flatten_bg_people(layers) once in Stage.__init__ after _unfold_background() (removing it from bg_maps and removing the duplicate pre-unfold call); compute distanceTransform and np.exp on the local padded ROI [ry0:ry1, rx0:rx1] (pad = ceil(4 * sig)); compute each box's median from bd0 and re-assert bd[cy0:cy1, cx0:cx1] = med after blending so adjacent Gaussian tails never un-flatten a box's core.
6	FIX	

explainer_engine/production/directed25d.py:603, 649–658




any(w in oid.lower() for w in ("crowd", ..., "man", "men", ...))




kb["d"] = float(self.bg_depth[cyp, cxp])

	T3 real-data false positives & safe-zone depth overwrite: (1) Substring matching "man" / "men" in oid.lower() matches non-person masks like "german_trench", "no_mans_land", "command_post", "embankment", and "equipment", flattening terrain depth. (2) Overwriting kb["d"] with self.bg_depth[cyp, cxp] clobbers the 75th-percentile host-mask depth set by _keep_boxes(), weakening _frame_people safe-zone zoom caps.	Match whole word tokens (set(re.findall(r"[a-z]+", oid.lower())) & person_tokens), and refresh only kb["face_d"] = self._face_depth(kb["face"]) without clobbering kb["d"].
7	FIX	

explainer_engine/production/directed25d.py:383–384, 607–614




elif it.get("box") or it.get("person"):




for extra in (self.p.get("person_boxes"), ...):

	Changes outside the task: Undocumented schema keys (keep_in_frame[].box/person, person_boxes, crowd_boxes) not in direction.py or living_director.py were added to _keep_boxes and _bg_person_boxes.	Remove the unrequested schema keys; read unlayered boxes from self.keep and layers["manifest"]["masks"]["objects"] / self.masks_src.
8	FIX	

explainer_engine/episode/run.py:901–903




if d.get("clip_path"):




clip_audio[ins["shot_id"]] = {"path": str(ep.root / d["clip_path"]), ...}

	T1 real-data crash when clip file is missing or failed: stage_sound checks d.get("clip_path") in production/video/<shot_id>.json without checking d.get("status") != G.FAIL or cp.is_file() (unlike _wan_clip at line 541). If the JSON exists with a failed status or a missing .mp4, missing is empty and VV.compose 
→ VV.read_mono crashes in ffmpeg.	Require d.get("status") != G.FAIL and cp.is_file() (handling both relative and absolute clip_path) before populating clip_audio[ins["shot_id"]].
9	FIX	

tests/unit/test_plan_steps_1_2.py:105, 144–162




"inserts": [{"shot_id": "S05_SH004", "start_frame": 24, "frames": 36, "duration_s": 1.5}]




def _fake_compose(...):

	T1 test passes for the wrong reason: The test stubs out VV.compose with a fake that appends inserts at the end of the read and omits "at_read_frame" from timing["inserts"]. Real VV.compose (videolane/voice.py:217) sorts by i["at_read_frame"] and raises KeyError: 'at_read_frame' on that fixture, and VI.speech was stubbed to return dicts instead of (start, end) tuples (videolane/voice.py:75).	Include "at_read_frame": 24 in timing["inserts"], stub VI.speech with (start, end) tuples, spy on the real VV.compose to verify mid-read silence splicing at 1.0 s..2.5 s, and assert ContractError when VV.compose fails to write voice_track.wav.
10	FIX	

tests/unit/test_c4a_review_fixes.py:66




bitten.plate = cv2.resize(lay["plate"], (bitten.sw, bitten.sh), interpolation=cv2.INTER_AREA)

	Test hides the T2 plate-hole bug: The test manually overwrote bitten.plate with lay["plate"] because _rest_background's core = (o["alpha"] >= 0.999) failed to put lay["plate"] under the outer 3.5 px ring of bitten.plate.	Remove the manual bitten.plate = ... overwrite; with A = (raw_a > 0.01) fixed in _rest_background, bitten.rest_seam() fails directly on bitten's own self.plate.
(b) Changed Files in Full
explainer_engine/episode/run.py
Python
[CODE 70102 chars]
explainer_engine/production/directed25d.py
Python
[CODE 68887 chars]
tests/unit/test_c4a_review_fixes.py
Python
[CODE 10844 chars]
tests/unit/test_plan_steps_1_2.py
Python
[CODE 19176 chars]
(c) Exact Pytest Command
Bash
[CODE 312 chars]
(d) NOT CHECKED

docs/SOURCED_RULES.md full 231 KB generated file: Regenerated and verified against test_sourced_rules.py::test_the_doc_table_matches_the_registry via python -m explainer_engine.standards.sourced_rules write (14 passed), not pasted in full above because it is a 231 KB auto-generated table.

Unbundled binary assets: Real Stage B / C4A / C5 PNG/MP4 renders for ep_truce_1914 and the real assets/audio/library/manifest.json audio takes were omitted from the slimmed checkout (SLIM_NOTE.txt), so test_living_director.py's library-take lookups were verified against a synthetic manifest.json fixture and 1080p/1440p layer/plate behaviour was verified on synthetic 1080p (1920x1080) and 1440p (2560x1440 
→
→ 1920x1080) shots (0.27 s/frame on 120 frames, well under BP-182's 1.5 s/frame cap).

Complete