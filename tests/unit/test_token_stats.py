from explainer_engine.llm import token_stats as ts


def _rows():
    return [
        {"ev": "start", "uid": "a", "job": "j", "id": "R1", "model": "claude-fable-5-1"},
        {"ev": "done", "uid": "a", "model": "claude-fable-5-1", "effort": "xhigh", "stop": "max_tokens", "usage": {"output": 48000}},
        {"ev": "start", "uid": "b", "job": "j", "id": "R2", "model": "claude-opus-5-5"},
        {"ev": "done", "uid": "b", "model": "claude-opus-5-5", "effort": "high", "stop": "end_turn", "usage": {"output": 14000}},
        {"ev": "void", "uid": "c"},
    ]


def test_measured_counts_thinking_and_flags_capped_calls():
    m = ts.measured(_rows())
    assert m[("claude-fable-5-1", "xhigh", "j", "R1")] == {"calls": 1, "max_out": 48000, "capped": 1}
    assert len(m) == 2


def test_suggest_uses_floor_measured_headroom_and_answer_size():
    rows = _rows()
    assert ts.suggest("high", 2000, rows) == 32000                   # floor wins over 14000 x 1.5
    assert ts.suggest("high", 20000, rows) == 60000                  # answer x 3
    assert ts.suggest("xhigh", 1000, rows) == 96000                  # capped call: 48000 x 2
    assert ts.suggest("high", 1000, []) == 32000


def test_missing_ledger_is_empty(tmp_path):
    assert ts.load(tmp_path / "none.jsonl") == []
