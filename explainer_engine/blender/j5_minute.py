"""The one-minute, five-scene J5 test film (the creator, 2026-11-06 20:17 UTC): "The commander's last night", made only of pictures that already exist on
Hugging Face (vano1919/tmr-artifacts, route_test_2026-11/assets) plus the cards, mouths and cuts of the dialogue test. Plan only: nothing here renders or
bills anything. ``python -m explainer_engine.blender.j5_minute`` prints the lint of the plan (docs/J5_MINUTE_PLAN.md is the step-by-step plan)."""
from __future__ import annotations

from explainer_engine.blender import j5_cuts, j5_montage

TARGET_S = 60.0
EYE = j5_cuts.EYE


def _s(name, scene, lane, seconds, subject, view, size, **kw):
    return dict(name=name, scene=scene, lane=lane, seconds=seconds, subject=subject, view=view, size=size, **kw)


# picture ids are the HF names under route_test_2026-11/assets: D4_rain_90, A3_field, B_H1_back, A1_tent, B_H1_left34, B_H2_right34, B_H3_front, D6_eyes_90, D1_ford_90, D2_duel_90, D5_after_90
PLAN = [
    _s("M0_map", "title", "HELPER", 3.0, "map", "front", "wide", picture="python map of the march route (no picture)", motion={"kind": "draw"}),
    _s("M1_column_wide", "march", "STILL_3D", 5.0, "column", "front", "wide", picture="D4_rain_90", motion={"kind": "push", "scale": 1.08}, establishing=True, motivation="the map becomes the road"),
    _s("M2_drummer", "march", "STILL_3D", 4.0, "column", "front", "close", picture="D4_rain_90", reuse_of="M1_column_wide", cut="axial", motion={"kind": "push", "scale": 1.10}, direction="right"),
    _s("M3_commander_leads", "march", "VIDEO_3D", 6.0, "H1", "back", "medium", picture="B_H1_back on A3_field", motion={"kind": "walk"}, motivation="the commander leads the column", direction="right"),
    _s("T1_tent_wide", "tent", "STILL_3D", 5.0, "tent", "front", "wide", picture="A1_tent", cut="dissolve", transition_s=1.0, establishing=True, motion={"kind": "parallax", "layers": 3}, luma=53),
    _s("T2_two_shot", "tent", "VIDEO_3D", 3.0, "H2", "right34", "wide", picture="A1_tent + B_H2_right34 + B_H1_left34", dialogue=True, sides=("H2", "H1"), eyeline=EYE, motivation="we meet the two men", luma=53),
    _s("T3_commander", "tent", "VIDEO_3D", 5.0, "H1", "left34", "medium", picture="B_H1_left34", dialogue=True, motivation="the commander speaks", sides=("H2", "H1"), eyeline=EYE, luma=52),
    _s("T4_scout", "tent", "VIDEO_3D", 3.0, "H2", "right34", "medium", picture="B_H2_right34", dialogue=True, motivation="the scout answers", sides=("H2", "H1"), eyeline=EYE, luma=52),
    _s("T5_elder", "tent", "VIDEO_3D", 5.0, "H3", "front", "medium", picture="B_H3_front", motivation="the elder listens (cutaway)", luma=52),
    _s("T6_eyes", "tent", "STILL_3D", 4.0, "H1", "front", "close", picture="D6_eyes_90", motivation="the commander decides", motion={"kind": "push", "scale": 1.12}, luma=50),
    _s("B1_ford", "ford", "STILL_3D", 5.0, "armies", "front", "wide", picture="D1_ford_90", establishing=True, motion={"kind": "parallax", "layers": 3}, motivation="his decision becomes the battle", direction="right"),
    _s("B2_duel", "ford", "STILL_3D", 5.0, "duel", "front", "medium", picture="D2_duel_90", motion={"kind": "push", "scale": 1.10}, motivation="the fight in the courtyard (cross-cut)", direction="right"),
    _s("A1_after", "after", "STILL_3D", 5.0, "soldier", "front", "wide", picture="D5_after_90", cut="dissolve", transition_s=1.5, establishing=True, motion={"kind": "pull", "scale": 1.08}),
    _s("A2_end_card", "title", "HELPER", 4.5, "title", "front", "wide", picture="python title card", cut="fade_black", transition_s=1.0, motion={"kind": "fade"}),
]
# stills at 5 s; three animated lines of the dialogue plus the walk and the elder are the only moving figures


def check() -> list[str]:
    dialogue = [s for s in PLAN if s.get("dialogue")]
    return j5_cuts.plan_check(dialogue) + j5_montage.lint_montage(PLAN, TARGET_S)


if __name__ == "__main__":
    print(f"runtime {j5_montage.runtime(PLAN):g} s, shares {({k: round(v, 2) for k, v in j5_montage.lane_shares(PLAN).items()})}")
    for p in check():
        print(p)
