## 2026-11-22 — PY-01: black/freeze intervals and zero duration in the technical gate
- The open-interval rule already exists in `explainer_engine/qa/technical_gate.py` (`_parse_blackdetect` and `_parse_freezedetect` close a dangling start at the clip end; `measure_video` raises on zero duration). This change adds the two focused tests the PY-01 acceptance asks for: a zero-length clip raises `RuntimeError`, and `black_start 9.0` in a 10.0 s clip gives 1.0 s.
- Files: `tests/unit/test_technical_gate.py` (2 new tests; the existing 38 kept). The branch is the Test Film modal-render base (76b62b31) because the handbook's `qa/technical_gate.py` exists only there; PY-01's own spec file `qa/pixels.py` is not the target.
- Test: `tests/unit/test_technical_gate.py` 40 passed.
