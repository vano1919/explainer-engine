"""Face points measured on the painted pictures (qa/face_points.py; QA 2026-10-20: the script's speaker points were template
guesses, bubble tails and rings landed on the wrong hero or a wall): matching, the FP-OFF check and --apply."""
from explainer_engine.qa import face_points as FP


def _face(x, y, score=0.92):
    return {"x": x, "y": y, "w": 0.06, "h": 0.1, "score": score}


def test_faces_are_matched_in_left_to_right_order_and_a_back_view_has_none():
    # s02_wide: four heroes on a bench, each declared a little left of his painted face
    speakers = {"oleary": [0.2, 0.46], "trump": [0.4, 0.45], "musk": [0.62, 0.46], "belfort": [0.76, 0.46]}
    faces = [_face(0.837, 0.41), _face(0.353, 0.42), _face(0.631, 0.39), _face(0.474, 0.41)]
    m = FP.match(speakers, faces)
    assert {h: f["x"] for h, f in m.items()} == {"oleary": 0.353, "trump": 0.474, "musk": 0.631, "belfort": 0.837}
    # over the shoulder: one face for two declared heroes; the one nearest it in order gets it, the back view none
    m = FP.match({"oleary": [0.45, 0.4], "musk": [0.9, 0.52]}, [_face(0.38, 0.47)])
    assert list(m) == ["oleary"]
    # a face farther than MATCH_MAX is another figure, not the hero
    assert FP.match({"trump": [0.1, 0.4]}, [_face(0.9, 0.4)]) == {}


def _measured():
    return {"pictures": {"s02_signing": {"file": "x.png", "uses": ["SH017"], "faces": [], "heroes": {
        "belfort": {"declared": [0.76, 0.42], "face": [0.833, 0.308], "score": 0.91, "distance": 0.096, "off": True,
                    "confident": True},
        "musk": {"declared": [0.46, 0.4], "face": [0.256, 0.395], "score": 0.9, "distance": 0.204, "off": True,
                 "confident": False},
        "oleary": {"declared": [0.6, 0.31], "face": [0.615, 0.311], "score": 0.9, "distance": 0.015, "off": False,
                   "confident": True}}}}}


def test_a_point_off_its_face_is_a_review_and_apply_rewrites_only_confident_ones():
    found = FP.check({}, [], _measured())
    assert {f["where"] for f in found} == {"s02_signing belfort", "s02_signing musk"}
    assert all(f["rule"] == "FP-OFF" and f["severity"] == "REVIEW" for f in found)
    pic = {"id": "s02_signing", "speakers": {"belfort": [0.76, 0.42], "musk": [0.46, 0.4], "oleary": [0.6, 0.31]}}
    doc = {"segments": [{"shots": [{"picture": pic}, {"picture": "s02_signing"}]}]}
    changed = FP.apply(doc, _measured())
    assert changed == [{"picture": "s02_signing", "who": "belfort", "old": [0.76, 0.42], "new": [0.833, 0.308]}]
    assert pic["speakers"]["musk"] == [0.46, 0.4] and pic["speakers"]["oleary"] == [0.6, 0.31]


def test_distance_is_in_shares_of_the_width():
    assert abs(FP._dist([0.5, 0.5], {"x": 0.5, "y": 0.5 + 16 / 9 * 0.1}) - 0.1) < 1e-9


def test_without_the_face_model_nothing_is_measured_and_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "missing.onnx"))
    m = FP.measure({"segments": []}, [tmp_path])
    assert m["skipped"] and m["pictures"] == {} and FP.check({}, [], m) == []
