Inputs and outputs of the stand-in validation quoted in `AGENT_AB_P0C2_2026-10.md`. Both finals are the arms' `production_script.json` with only the `world` block replaced by B2's
(host era `medieval_europe`, no visitors, no day arc), because `production validate` crashes on A2's eras (`steppe_1223`, `france_1812`) and day-arc lights that are not in the codex.
The B2 copy also has the one line with `intent` "command" changed to "decide" (the only change besides `world`); the real B2 file keeps its PV-01 FAIL. `claim_map.md` of `../input/` sat next to the file when run.
Run: `PYTHONPATH=. python -m explainer_engine.production validate <file>`. Totals: A2 `119 FAIL, 148 REVIEW`, B2 `153 FAIL, 177 REVIEW`.
