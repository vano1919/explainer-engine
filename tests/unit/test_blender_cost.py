"""ICW-04 skeleton of the Blender cost model (roadmap 12.3; ICW-09 fills the rows): an estimate comes only from a measured
config/job_speeds.json row, never from the roadmap's HYP s/frame; a booked estimate stops at 80 % of the cap."""
import copy

import pytest

from explainer_engine.blender.cost import CostModel, CostUnknown
from explainer_engine.cloud import speeds
from explainer_engine.core.ledger import CapReached, Run


def test_no_measured_row_means_no_estimate():
    with pytest.raises(CostUnknown, match="no measured row"):
        CostModel().estimate(10368, "eevee_full", "RTX 4090", 0.89)
    with pytest.raises(CostUnknown, match="no job type"):
        CostModel().estimate(100, "eevee_full", "RTX 4090", 0.89, tier="480")


def test_an_estimate_from_a_measured_row_and_the_80_percent_stop(tmp_path):
    data = copy.deepcopy(speeds.load())
    data["jobs"]["blender_frame_eevee_full_1440"]["rows"]["RTX 4090"] = {"s_per_unit": 3.0, "setup_min": 12.0}
    line = CostModel(data).estimate(1200, "eevee_full", "RTX 4090", 0.89)
    assert line["work_h"] == 1.0 and line["setup_h"] == 0.2 and line["usd"] == pytest.approx(1.068) and line["basis"] == "measured"
    run = Run.open(tmp_path / "run.json", caps={"runpod_usd": 1.2})
    with pytest.raises(CapReached):
        CostModel.reserve(run, line, "s1")      # 1.068 > 80 % of 1.20
    small = CostModel(data).estimate(100, "eevee_full", "RTX 4090", 0.89)
    CostModel.reserve(run, small, "s2")
    assert run.spent("runpod_usd") == pytest.approx(small["usd"])
