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
