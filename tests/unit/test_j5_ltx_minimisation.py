"""Unit tests for J5 LTX minimisation: the shot router, its limits (BP-184), the v3 one-minute plan, the action rig frames."""

from __future__ import annotations

import unittest

import numpy as np

from explainer_engine.blender import j5_action_rig, j5_limits, j5_minute, j5_minute_v3


class TestJ5LimitsAndRouter(unittest.TestCase):
    """Test BP-182..184 deterministic shot router and limits."""

    def test_limits_lint_clean_on_v3_plan(self) -> None:
        v3 = j5_minute_v3.build_v3_plan()
        self.assertEqual(j5_limits.lint_limits(v3), [])

    def test_dialogue_and_reaction_never_invoke_ltx(self) -> None:
        res = j5_limits.route_action_shot(
            {"name": "T2_two_shot", "scene": "tent", "lane": "VIDEO_3D", "seconds": 3.5, "dialogue": True}
        )
        self.assertEqual(res["method"], "J5_DIALOGUE_CARD")
        self.assertEqual(res["ltx_seconds"], 0.0)
        self.assertEqual(res["ltx_frames"], 0)

    def test_crowd_march_routes_to_billboard_crowd(self) -> None:
        res = j5_limits.route_action_shot(
            {"name": "M1_column_wide", "scene": "march", "lane": "STILL_3D", "seconds": 5.0, "subject": "column"}
        )
        self.assertEqual(res["method"], "J5_BILLBOARD_CROWD")
        self.assertEqual(res["ltx_seconds"], 0.0)

    def test_hinged_action_stays_free(self) -> None:
        res = j5_limits.route_action_shot(
            {
                "name": "M3_commander_leads",
                "scene": "march",
                "lane": "VIDEO_3D",
                "seconds": 4.0,
                "action_kind": "commander_leads",
                "hinged_prop": "cloak_and_banner",
            }
        )
        self.assertEqual(res["method"], "J5_HINGED_RIG")
        self.assertEqual(res["ltx_seconds"], 0.0)

    def test_true_3d_impact_routes_to_capped_ltx_insert(self) -> None:
        res = j5_limits.route_action_shot(
            {
                "name": "B2_duel",
                "scene": "ford",
                "lane": "VIDEO_3D",
                "seconds": 5.0,
                "action_kind": "duel",
                "requires_contact": True,
            }
        )
        self.assertEqual(res["method"], "HYBRID_J5_HINGE_PLUS_LTX_IMPACT")
        self.assertAlmostEqual(res["ltx_seconds"], 3.04, places=2)
        self.assertEqual(res["ltx_frames"], 73)
        self.assertAlmostEqual(res["j5_seconds"], 1.96, places=2)


class TestJ5V3Plan(unittest.TestCase):
    def test_v3_cuts_ltx_from_the_v2_video_lane_to_one_capped_insert(self) -> None:
        cmp_res = j5_minute_v3.compare_v2_v3()
        self.assertAlmostEqual(cmp_res["v2_video_3d_seconds"], 21.0, places=2)
        self.assertAlmostEqual(cmp_res["v3_ltx_seconds"], 3.04, places=2)
        self.assertLessEqual(cmp_res["v3_ltx_share"], cmp_res["episode_ltx_share_max"])
        self.assertEqual(len(cmp_res["rows"]), len(j5_minute.PLAN))


class TestJ5ActionRig(unittest.TestCase):
    def test_j5_action_rig_renders_frames(self) -> None:
        rgb = np.full((64, 96, 3), 128, dtype=np.uint8)
        f1 = j5_action_rig.render_depth_relief_frame(rgb, yaw_deg=5.0, push_zoom=1.05)
        f2 = j5_action_rig.render_billboard_crowd_frame(rgb, t_sec=1.0, n_planes=4, rain=True, water_splash=True)
        f3 = j5_action_rig.render_hinged_action_frame(rgb, angle_deg=18.0, slash_smear=True, shake_px=3.0)
        for f in (f1, f2, f3):
            self.assertEqual(f.shape, (64, 96, 3))


if __name__ == "__main__":
    unittest.main()
