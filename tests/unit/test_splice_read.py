"""splice_read: the voiced read is cut at the bubble runs and every take lands in its run's place (D-63)."""
import numpy as np

from explainer_engine.production import splice_read as SR


def test_cut_keeps_every_sample_in_order_and_fades_only_inner_edges():
    sr = 1000
    pcm = np.ones(3000)
    parts = SR.cut(pcm, sr, [1.0, 2.0])
    assert [len(p) for p in parts] == [1000, 1000, 1000]
    assert parts[0][0] == 1.0 and parts[-1][-1] == 1.0       # the read's own start and end are untouched
    assert parts[0][-1] == 0.0 and parts[1][0] == 0.0         # every cut is faded, so no click
    assert parts[1][500] == 1.0


def test_one_take_per_run_or_refuse(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        SR.pieces([{"at": 1.0}, {"at": 2.0}], tmp_path, [tmp_path / "a.mp3"], tmp_path / "out")


def test_the_schema_marks_a_new_narrator_line_and_only_with_a_boolean():
    import json
    from pathlib import Path
    from explainer_engine.production import script as S
    doc = json.loads(Path("examples/titans_from_zero/production_script.json").read_text(encoding="utf-8"))
    line = next(ln for seg in doc["segments"] for ln in seg["lines"] if ln.get("new_read"))
    assert not [e for e in S.schema_errors(doc) if "new_read" in e]
    line["new_read"] = "yes"
    assert any("new_read" in e or "yes" in e for e in S.schema_errors(doc))
