import json,copy
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
d=json.load(open(A+'s03_performer.json'))
b2=copy.deepcopy(d)
for s in b2['segments']:
    for l in s['lines']:
        for k in ('tags','emphasis','tone','emotion','pause_after'): l.pop(k,None)
w=copy.deepcopy(b2)
for s in w['segments']:
    for l in s['lines']: l.pop('visual_beats',None)
json.dump(w,open(A+'s02_writer.json','w'),indent=1,ensure_ascii=False)
json.dump(b2,open(A+'s02b_beats.json','w'),indent=1,ensure_ascii=False)
