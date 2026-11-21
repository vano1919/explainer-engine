"""The 2-minute overlay demo (OVERLAY_INTEGRATION_RULES section 10): twelve shots, their narration, and what each puts on screen.
Data are TEST DATA (no claim map; the demo is never uploaded). ``at`` is the spoken word an item lands on (words after the cursor)."""
from __future__ import annotations

LINES = [
    "Seventy-four thousand years ago, a family sat by a fire, and the sky was about to change.",
    "Far to the east, on the island of Sumatra, a mountain called Toba was waking. Everything within a hundred and fifty miles would be gone by morning.",
    "They never heard its name. Their home was the Shinfa valley, in what is now Ethiopia.",
    "How big was it? Mount St. Helens threw out one cubic kilometer of rock. Tambora, the worst in recorded history, a hundred and fifty. Toba: nearly three thousand.",
    "The fire still burned. The children still slept.",
    "But the ash was already traveling, four thousand miles of sky between the mountain and this valley.",
    "First it fell on India, burying the tools of the people at Jwalapuram under a gray blanket. Then the cloud kept going west.",
    "Morning came late.",
    "For six years, some scientists think, the summers stayed cold.",
    "The warmth dropped, year after year, and only slowly climbed back.",
    "Yet here, nobody vanished. They changed what they ate: fewer antelope, more fish.",
    "Seventy-four thousand years later, eight billion of us carry their story.",
]

PLACES = {"toba": (98.88, 2.68, "Toba"), "shinfa": (36.0, 12.8, "Shinfa-Metema"), "jwalapuram": (78.1, 15.3, "Jwalapuram")}

# photo ids: M1 (a pair in a canyon), M3 (a man by a drying river), C1 (ltx_scene_test/start_c1.png, the couple at sunset): see demo_assets.PHOTOS
SHOTS = [
    dict(no=1, dur=8, route="still_25d", photo="C1", push=(1.0, 1.05, 0.50, 0.55), items=[]),
    dict(no=2, dur=12, route="map_action", mode="full", surface="solid", bg="map", view=dict(lon=98.0, lat=3.0, span_km=2600.0), reason="date", items=[
        dict(kind="date_chip", at="far", text="74,000 years ago"),
        dict(kind="label", at="toba", place="toba"),
        dict(kind="pulse", at="waking", place="toba"),
        dict(kind="highlight", at="hundred", place="toba", miles=150),
        dict(kind="scale_bar"),
    ]),
    dict(no=3, dur=10, route="still_25d", mode="accent", surface="bare", photo="M1", push=(1.0, 1.06, 0.55, 0.50), reason="place", items=[
        dict(kind="label", at="shinfa", text="Shinfa-Metema · Ethiopia", size=64),
    ]),
    dict(no=4, dur=12, route="map_action", mode="full", surface="solid", bg="card", photo="M3", reason="number", items=[
        dict(kind="bar_chart", title="Eruption size, km³ (demo data)", unit="km³", series=[
            dict(label="Mount St. Helens", value=1, at="one", text="1"),
            dict(label="Tambora", value=150, at="hundred", text="150"),
            dict(label="Toba", value=2800, at="three", text="2,800", highlight=True)]),
    ]),
    dict(no=5, dur=8, route="still_25d", photo="M1", push=(1.0, 1.06, 0.72, 0.58), items=[]),
    dict(no=6, dur=10, route="still_25d", mode="accent", surface="glass", photo="M3", push=(1.0, 1.05, 0.50, 0.50), reason="number", items=[
        dict(kind="mini_map", pref="top_right", view=dict(lon=67.0, lat=9.0, span_km=9500.0), size=(864, 486)),
        dict(kind="route_arrow", at="traveling", a="toba", b="shinfa"),
        dict(kind="counter", at="four", value=4000, unit="miles"),
    ]),
    dict(no=7, dur=12, route="map_action", mode="full", surface="solid", bg="map", view=dict(lon=86.0, lat=9.5, span_km=5600.0), reason="place", items=[
        dict(kind="pulse", at="first", place="toba", frames=16),
        dict(kind="plume", at="fell", a="toba", b="jwalapuram", miles=430),
        dict(kind="label", at="jwalapuram", place="jwalapuram"),
        dict(kind="spread", at="gray", place="jwalapuram", miles=300),
        dict(kind="scale_bar"),
    ]),
    dict(no=8, dur=8, route="ltx", items=[]),
    dict(no=9, dur=10, route="still_25d", mode="accent", surface="bare", photo="M1", push=(1.0, 1.05, 0.40, 0.45), reason="number", items=[
        dict(kind="stat_callout", at="six", number="6", unit="years", caption="of cold summers", pref="top_left", size=(660, 420)),
    ]),
    dict(no=10, dur=12, route="map_action", mode="full", surface="solid", bg="card", photo="M1", reason="number", items=[
        dict(kind="line_chart", title="Summer change, °C (demo data)", unit="°C", series=[
            dict(at="warmth", value=0.0), dict(at="dropped", value=-0.7), dict(at="year", value=-1.4), dict(at="only", value=-1.1),
            dict(at="climbed", value=-0.5)]),
    ]),
    dict(no=11, dur=8, route="still_25d", mode="accent", surface="glass", photo="M3", push=(1.0, 1.05, 0.62, 0.55), reason="compare", items=[
        dict(kind="compare_pair", pref="bottom_right", size=(1100, 300),
             left=dict(at="antelope", label="Antelope", direction="down"), right=dict(at="fish", label="Fish", direction="up")),
    ]),
    dict(no=12, dur=10, route="map_action", mode="full", surface="solid", bg="card", photo="C1", reason="date", items=[
        dict(kind="timeline", at="seventy", marks=[(74000, "74,000 years ago"), (50000, "50,000"), (25000, "25,000"), (10000, "10,000"), (0, "Today")], move_at="thousand"),
        dict(kind="counter_big", at="eight", value=8_000_000_000, unit="people (demo data)"),
    ]),
]
FPS = 24
