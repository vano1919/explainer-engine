"""Regression tests for Truce 1914 Rebuild Implementation (Steps 1-7 + Creator Corrections C1-C4).

Every test here verifies a general pipeline fix and fails on the pre-fix Pass-1 code.
Compatible with both ``pytest`` and ``python3 -m unittest``.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from explainer_engine.audio import duck
from explainer_engine.episode import shot_split as SS
from explainer_engine.episode import sound_plan as SPL
from explainer_engine.episode import timing as ETM
from explainer_engine.finish import frame_pick as FP
from explainer_engine.finish import superres as SR
from explainer_engine.maps import actions as MA
from explainer_engine.maps import tactile_renderer as TR
from explainer_engine.production import directed25d as D25
from explainer_engine.production import living_fx as LFX
from explainer_engine.production import visual_bridge as VB
from explainer_engine.videolane import ingest as VI
from explainer_engine.videolane import plan as VP

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestTruceRebuildImplementation(unittest.TestCase):
    def test_step1_whisper_edit_points_and_clock_retime(self):
        """Step 1: spoken clips are trimmed to [first_word - 0.40s, last_word + >=0.50s] and timing.json shifts to match."""
        script = json.loads((REPO_ROOT / "episodes/ep_truce_1914/story/production_script.json").read_text(encoding="utf-8"))
        whisper_sample = {
            "clips": {
                "S03_SH004": {
                    "duration": 3.00,
                    "words": [{"word": "Listen.", "start": 1.92, "end": 2.84}],
                },
                "S03_SH005": {
                    "duration": 4.70,
                    "words": [
                        {"word": "Wait...", "start": 0.10, "end": 1.40},
                        {"word": "that's", "start": 2.10, "end": 3.10},
                        {"word": "German.", "start": 3.10, "end": 4.12},
                    ],
                },
                "S02_SH004": {
                    "duration": 3.00,
                    "words": [{"word": "You", "start": 1.38, "end": 1.88}],
                },
            }
        }
        ep = VI.whisper_edit_points(whisper_sample, script)
        self.assertAlmostEqual(ep["clips"]["S03_SH004"]["in"], 1.52, places=1)
        self.assertAlmostEqual(ep["clips"]["S03_SH004"]["out"], 3.00, places=2)
        self.assertGreaterEqual(ep["clips"]["S03_SH005"]["out"], 4.62)
        self.assertLessEqual(ep["clips"]["S02_SH004"]["mute_tail_from_s"], 1.38)

        dummy_timing = {
            "fps": 24,
            "total_frames": 132,
            "inserts": [{"shot_id": "S03_SH005", "at_read_frame": 0, "frames": 78}],
            "shots": {
                "S03_SH005": {"start_frame": 0, "end_frame": 78, "frames": 78, "seconds": 3.25},
                "S08_SH004": {"start_frame": 78, "end_frame": 132, "frames": 54, "seconds": 2.25},
            },
            "spines": {"S08_SH004": [{"word": "human", "start_frame": 90}]},
        }
        retimed = ETM.retime_with_edit_points(dummy_timing, script, ep)
        self.assertEqual(retimed["shots"]["S03_SH005"]["frames"], int(round(ep["clips"]["S03_SH005"]["out"] * 24)))
        self.assertEqual(retimed["shots"]["S08_SH004"]["start_frame"], retimed["shots"]["S03_SH005"]["frames"])
        self.assertIn("S08_SH004", retimed["on_screen_texts"])
        self.assertEqual(
            retimed["on_screen_texts"]["S08_SH004"][0]["text"],
            "For one day, they remembered they were human.",
        )

    def test_step2_continuous_25d_no_cutin_crop_and_frame0_parity(self):
        """Step 2: CUTIN_CROP is 1.0 (no 1.35x sub-shot zoom jump), continuous waypoints cover 0..N, and snow at f=0 has alpha=0."""
        self.assertEqual(SS.CUTIN_CROP, 1.0)
        shot = {
            "shot_id": "S02_SH008",
            "route": "still_25d",
            "target_duration_seconds": 9.8,
            "camera_spec": {"camera_move": "push_in"},
            "director_brief": {"focal_anchor": {"id": "harris", "box_hint": [0.35, 0.18, 0.72, 0.99], "keep_in_frame": True}},
        }
        wps = SS.build_continuous_camera_waypoints(shot, fps=24)
        self.assertEqual(len(wps), 1)
        self.assertEqual(wps[0]["start"], 0)
        self.assertEqual(wps[0]["end"], int(round(9.8 * 24)))

        class DummyStage:
            import cv2
            W, H = 320, 180
            sw, sh = 320, 180
            fps = 24
            n = 96
            seed = 42
            p = {"shot_id": "S02_SH008", "wind": [0.08, 0.0]}
            sky = np.zeros((180, 320), np.float32)

            def _coef(self, v, d):
                return 160.0, 90.0

            def matrix(self, v, d):
                return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)

            def cover_k(self, v, d):
                return 1.0

            def people_field(self, v):
                m = np.zeros((self.H, self.W), np.float32)
                m[40:140, 100:220] = 1.0
                return m

        st = DummyStage()
        src_rgb = np.full((180, 320, 3), 120.0, dtype=np.float32)
        depth = np.full((180, 320), 0.2, dtype=np.float32)
        v = {"z0": 1.05, "s": 1.0, "dp": 0.0, "cx": 0.5, "cy": 0.5, "tx": 0.0, "ty": 0.0, "ox": 0.0, "rot": 0.0, "far": 0.2}
        out_f0 = LFX._particles(st, src_rgb, depth, {"op": "snow", "strength": 1.0, "params": {"count": 180}}, t=0.0, v=v, op="snow")
        self.assertEqual(float(np.abs(out_f0 - src_rgb).max()), 0.0)

        out_f24 = LFX._particles(st, src_rgb, depth, {"op": "snow", "strength": 1.0, "params": {"count": 180}}, t=1.0, v=v, op="snow")
        bg_diff = float(np.abs(out_f24[:35, :80] - src_rgb[:35, :80]).mean())
        fg_diff = float(np.abs(out_f24[60:120, 120:200] - src_rgb[60:120, 120:200]).mean())
        self.assertGreater(bg_diff, fg_diff * 3.0)

    def test_step3_epilogue_on_screen_text_and_visual_bridge(self):
        """Step 3 & Step 6: S08_SH004 renders 'For one day, they remembered they were human.' on screen and avoids faces."""
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        shot = {
            "shot_id": "S08_SH004",
            "on_screen_text": "For one day, they remembered they were human.",
            "frames": 120,
        }
        rendered = VB.render_on_frame(frame, shot, f=48, fps=24, total_frames=120)
        self.assertGreater(float(rendered.mean()), float(frame.mean()) + 0.5)

        box = VB.safe_overlay_box((0.06, 0.78, 0.46, 0.88), keep_boxes=[{"face": [0.05, 0.70, 0.40, 0.92]}])
        self.assertNotEqual(box, (0.06, 0.78, 0.46, 0.88))

    def test_step4_map_counter_exact_landing_and_frame_locked_audio(self):
        """Step 4: counter reaches 1.0 (100,000 men) at least 18 frames before end_frame (never 99,998),
        and drawing audio emits only while progress increases."""
        act = {"kind": "counter", "start": 10, "end": 120, "value": 100000, "unit": "men (estimate)"}
        for f in range(102, 120):
            u = MA._u_counter(act, f)
            self.assertEqual(u, 1.0)
            self.assertEqual(MA._fmt(100000 * u, 100000), "100,000")

        plan_doc = {
            "shot_id": "S02_SH002",
            "frames": 192,
            "fps": 24,
            "actions": [
                {
                    "kind": "front_line",
                    "event_id": "S02_SH002.A1",
                    "start": 6,
                    "end": 78,
                    "stands": False,
                    "path": [(2.8, 51.0), (7.5, 47.5)],
                }
            ],
        }
        emitter = TR.AudioEventEmitter(plan_doc)
        spans = emitter.drawing_spans_s()
        self.assertEqual(len(spans), 1)
        s0, s1 = spans[0]
        self.assertGreaterEqual(s0, 0.20)
        self.assertLessEqual(s1, 3.30)

    def test_step5_and_c1_presence_band_ducking_and_no_numeric_quotas(self):
        """Step 5 & Creator C1: presence-band ducking preserves high-frequency wind hiss (>3600 Hz) > 2x better than -9 dB crush,
        and sound_plan advisory_density_hint never blocks intentional silence."""
        sr = 48000
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        mid_tone = 0.2 * np.sin(2 * np.pi * 1000.0 * t)
        high_wind = 0.2 * np.sin(2 * np.pi * 6000.0 * t)
        bed = np.stack([mid_tone + high_wind, mid_tone + high_wind], axis=0).astype(np.float32)
        voice = (0.35 * np.sin(2 * np.pi * 400.0 * t)).astype(np.float32)

        ducked = duck.duck_presence_band(bed, voice, sr=sr, presence_cut_db=6.0, outer_cut_db=1.5)
        from scipy import signal
        sos_hi = signal.butter(2, 4500.0, btype="high", fs=sr, output="sos")
        hi_new = float(np.sqrt(np.mean(signal.sosfilt(sos_hi, ducked[0]) ** 2)))
        hi_old = float(np.sqrt(np.mean(signal.sosfilt(sos_hi, bed[0] * (10 ** (-9.0 / 20.0))) ** 2)))
        self.assertGreater(hi_new, hi_old * 2.0)

        hint = SPL.advisory_density_hint({
            "shot_id": "S08_SH004",
            "dur_s": 5.0,
            "events": [],
            "design": {"state": "INTENTIONAL_SILENCE", "silence_reason": "solemn epilogue silence"},
        })
        self.assertEqual(hint["status"], "PASS")
        self.assertFalse(hint["blocking"])

    def test_step7_and_c2_c3_ltx_natural_fit_and_pluggable_upscaler(self):
        """Step 7, C2 & C3: unnatural talking close-ups/handshakes/small props re-route away from raw LTX,
        and finish/superres supports pluggable per-lane backends ('none', 'lanczos', 'temporal_video') + grain restore."""
        script = json.loads((REPO_ROOT / "episodes/ep_truce_1914/story/production_script.json").read_text(encoding="utf-8"))
        res = VP.reroute_unnatural_ltx_shots(script)
        self.assertFalse(res["evaluations"]["S06_SH002"]["natural_for_ltx"])
        self.assertEqual(res["evaluations"]["S06_SH002"]["recommended_route"], "still_25d")
        self.assertFalse(res["evaluations"]["S05_SH011"]["natural_for_ltx"])
        self.assertGreaterEqual(len(res["kept_ltx_natural"]), 14)
        self.assertGreaterEqual(len(res["rerouted_to_25d"]), 30)

        import cv2
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            src_img = np.full((120, 160, 3), 128, dtype=np.uint8)
            src_p = tmp_path / "in.png"
            out_none = tmp_path / "out_none.png"
            out_temp = tmp_path / "out_temp.png"
            cv2.imwrite(str(src_p), src_img)

            rep_none = SR.upscale_with_backend(src_p, out_none, lane="still_25d", backend="none", restore_grain=False)
            self.assertEqual(rep_none["status"], "PASS")
            self.assertEqual(rep_none["backend"], "none")
            rep_temp = SR.upscale_with_backend(
                src_p, out_temp, lane="video", backend="temporal_video", size=(320, 240), restore_grain=True
            )
            self.assertEqual(rep_temp["status"], "PASS")
            self.assertEqual(rep_temp["output_size"], [320, 240])


if __name__ == "__main__":
    unittest.main()
