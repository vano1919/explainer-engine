import numpy as np

from explainer_engine.qa import scorecard as S


def words(n=60, step=0.4):
    return [{"w": f"w{i}" + ("." if i % 6 == 5 else ""), "s": i * step, "e": i * step + 0.3} for i in range(n)]


def test_picture_stats_and_outliers():
    rng = np.random.default_rng(0)
    base = {f"p{i}": S.picture_stats(np.clip(0.4 + rng.normal(0, 0.02, (8, 8, 3)), 0, 1)) for i in range(9)}
    base["odd"] = S.picture_stats(np.ones((8, 8, 3)) * np.array([1.0, 0.1, 0.0]))
    assert S.outliers(base) == ["odd"]


def test_markdown_and_worst():
    rows = [S.row(1, "x", "PASS", ["a"]), S.row(2, "y", "FAIL", ["b"], human=True)]
    md = S.markdown(rows)
    assert "creator decides" in md and S.worst(["PASS", "FAIL", "REVIEW"]) == "FAIL"


def test_sound_event_on_a_word_fails():
    w = words()
    shots = [{"id": "s1", "type": "A", "start": 0.0, "end": 6.0, "transition": "cut", "emotion": "tension", "beat": "hook",
              "phase": "d", "sentences": [0], "motion": {"kind": "static", "z0": 1.0, "z1": 1.0}, "picture": "p", "palette": [],
              "face": "none", "stakes": "x y z w v u t"}]
    rows = S.score(shots, w, "Is it? yes.", {"cast": [], "style_suffix": ""}, sound_events=[{"id": "x", "at": w[3]["s"] + 0.1}])
    assert rows[1]["status"] == "FAIL"
