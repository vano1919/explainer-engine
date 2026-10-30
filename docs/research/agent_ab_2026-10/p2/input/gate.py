"""Partial per-stage gates for P0c-2 (the same helper for both arms). Usage from the repo root:
    PYTHONPATH=. python3 jobs/ab_agents_2026-10/p2/input/gate.py <production_script.json> [story scene narr beats claims]
`production validate` stops at the schema check while root `voice` / segment `shots` are missing, so it cannot show
these before stages 4-5; this runs the individual lints on the segments that already have lines."""
import json, sys
from explainer_engine.scripting import story_lint, scene_lint, narration_lint, claims
from explainer_engine.production import beats as B
p = sys.argv[1]
doc = json.load(open(p))
doc2 = dict(doc); doc2['segments'] = [s for s in doc['segments'] if s.get('lines')]
def show(name, fs):
    f = [x for x in fs if x['severity'] == 'FAIL']; r = [x for x in fs if x['severity'] != 'FAIL']
    print(f"== {name}: {len(f)} FAIL, {len(r)} REVIEW")
    for x in fs: print("  ", x['severity'], x.get('rule'), x.get('where'), str(x.get('detail'))[:230])
only = sys.argv[2:]
if not only or 'story' in only: show('story_lint (full doc)', story_lint.lint(doc))
if not only or 'scene' in only: show('scene_lint', scene_lint.lint(doc2))
if not only or 'narr' in only: show('narration (PV-12)', narration_lint.doc_findings(doc2))
if not only or 'beats' in only: show('beats (PV-44 lint)', B.lint(doc2))
if not only or 'claims' in only:
    cm = claims.parse_map(open('jobs/ab_agents_2026-10/p2/input/claim_map.md').read())
    show('claims (PV-37)', claims.check(doc2, cm))
