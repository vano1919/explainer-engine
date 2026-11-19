"""Two causes found while running the first 60 s: a swallowed TypeError (Grounding-DINO) and a light the layers lack."""
import sys
import types

import numpy as np

from explainer_engine.production import living_director as LD
from explainer_engine.production import perceive_picture as PP


class _Enc(dict):
    input_ids = [1]


class _T(list):
    def tolist(self):
        return list(self)


def test_the_dino_call_uses_the_threshold_name_the_installed_transformers_takes(monkeypatch):
    seen_kw = {}

    class Proc:
        def __call__(self, images, text, return_tensors):
            enc = _Enc()
            return enc

        def post_process_grounded_object_detection(self, outputs, input_ids, threshold=0.4, text_threshold=0.3,
                                                   target_sizes=None):          # transformers 5: no box_threshold
            seen_kw.update(threshold=threshold)
            return [{"boxes": [_T([10.0, 10.0, 50.0, 30.0])], "scores": [0.9], "labels": ["hand"]}]

    class Model:
        def eval(self):
            return self

        def __call__(self, **kw):
            return None

    class _Ctx:
        def __enter__(self):
            return None

        def __exit__(self, *a):
            return False

    tr = types.ModuleType("transformers")
    tr.AutoProcessor = types.SimpleNamespace(from_pretrained=lambda m: Proc())
    tr.AutoModelForZeroShotObjectDetection = types.SimpleNamespace(from_pretrained=lambda m: Model())
    torch = types.ModuleType("torch")
    torch.inference_mode = lambda: _Ctx()
    monkeypatch.setitem(sys.modules, "transformers", tr)
    monkeypatch.setitem(sys.modules, "torch", torch)

    out = PP.run_grounding_dino_tiny(np.zeros((100, 200, 3), np.uint8), ["hand"], box_threshold=0.25)
    assert seen_kw == {"threshold": 0.25}
    assert len(out) == 1 and out[0]["bbox"] == [0.05, 0.1, 0.25, 0.3]


def test_a_light_track_carries_the_point_the_director_saw():
    d = {"seen": {"lights": [{"id": "sun", "kind": "sun", "point": [0.5, 0.22], "radius": 0.06}]}}
    r = {"id": "sun_rays", "effect": "sun_shaft", "tkind": "light", "track": "lighting", "lights": ["sun"], "area_pct": 1.0}
    tr = LD._track(r, d)
    assert tr["target"]["light"] == "sun" and tr["target"]["origin"] == [0.5, 0.22]
    r2 = dict(r, lights=["unknown"])
    assert "origin" not in LD._track(r2, d)["target"]
