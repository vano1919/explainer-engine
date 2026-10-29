import json,sys,subprocess,shutil
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
mode,sid=sys.argv[1],sys.argv[2]
doc=json.load(open(A+'production_script.json'))
json.dump(doc,open(A+'scratch/before.json','w'),indent=1,ensure_ascii=False)
seg=next(s for s in doc['segments'] if s['id']==sid)
if mode=='lines':
    seg['lines']=json.load(open(A+f'scratch/lines_{sid}.json'))
    stage='writer'
elif mode=='beats':
    bl=json.load(open(A+f'scratch/beats_{sid}.json'))
    assert len(bl)==len(seg['lines']),(len(bl),len(seg['lines']))
    for ln,b in zip(seg['lines'],bl):
        if b: ln['visual_beats']=b
        else: ln.pop('visual_beats',None)
    stage='beats'
json.dump(doc,open(A+'production_script.json','w'),indent=1,ensure_ascii=False)
R='/home/user/explainer-engine'
print(subprocess.run(['python3','-m','explainer_engine.scripting.stage_guard',stage,A+'scratch/before.json',A+'production_script.json'],cwd=R,capture_output=True,text=True).stdout)
