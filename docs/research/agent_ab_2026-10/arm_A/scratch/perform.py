import json
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
doc=json.load(open(A+'production_script.json'))
json.dump(doc,open(A+'scratch/before.json','w'),indent=1,ensure_ascii=False)
# (tags, emphasis, tone, emotion, pause_after)
P={
'S01':[(["suspenseful"],"first","low and flat, then silence","dread",0.4),
 ([],"burned","quick, matter of fact","ominous",None),
 (["cautiously"],"knee","hushed, the fog slows him","uneasy",None),
 ([],"back","hushed wonder","awe",0.4),
 (["matter of fact"],"day","driven, plain","resolve",None),
 (["intrigued"],"alive","rising question, the last word lands","tension",None)],
'S02':[([],"battle","quick, a story starting","tense curiosity",None),
 (["matter of fact"],"army","clipped, imperious","impatience",None),
 (["cautiously"],"back","formal, careful, a soldier reporting","wary",None),
 (["matter of fact"],"faster","clipped, dismissive","impatience",None),
 (["hesitant"],"axle","formal, a little too exact","worry",None),
 ([],"tonight","flat, waves the problem away","denial",None),
 (["softly"],"dead","quiet, a slip of his mother tongue","moved and afraid",0.5),
 ([],None,"one word thrown back, not loud, then silence","shaken",1.2),
 (["matter of fact"],"army","flat, doubling down","stubborn",None),
 (["deadpan"],"Murat","dry, quick","foreboding",None)],
'S03':[(["quickly"],"go","quick, a charge starting","momentum",None),
 ([],"metres","dry, factual","unease",None),
 (["deadpan"],"back","flat, no pity","grim",None),
 ([],"fought","flat, each sentence a door closing","hollow",0.4),
 (["suspenseful"],"sinking","low, slowing down","foreboding",None)],
'S04':[(["slowly"],"long","slow, one image at a time","unease",None),
 (["matter of fact"],"understands","plain, quick","tension",None),
 (["slowly"],"iron","quiet, unhurried, almost kind","calm",None),
 (["cautiously"],"trouble","stiff courtesy","wary",None),
 (["softly"],"move","mild insult, no heat","calm",None),
 (["angry"],"Further","pride, a little too fast","pride",0.5),
 (["softly"],"asked","deadpan, quiet","satisfied",None),
 (["hesitant"],"tricked","low, stunned","dawning shock",None),
 (["slowly"],"did","told flat, a long beat before 'I did'","reflective",None),
 ([],"killed","wary, quiet","dread",None),
 (["softly"],"rare","warm and level, an offer inside it","quiet warmth",0.6),
 (["deadpan"],"gift","dry, steady","dignity",None),
 (["suspenseful"],"watch","low, a promise","foreboding",None)],
'S05':[(["quickly"],"below","brisk, the plan is simple","confidence",None),
 ([],"squares","rising, the riders closing","tension",None),
 (["dramatically"],"answer","big, a hit lands","power",None),
 (["matter of fact"],"alone","plain, the facts stacking up","competence",None),
 (["suspenseful"],"easily","the cheer fades, one line of doubt","foreboding",None)],
'S06':[(["slowly"],"foraged","low, each sentence heavier","dread",None),
 ([],"raised","quiet, the night is still","tension",None),
 (["matter of fact"],"it","hard and final","stubborn",None),
 (["cautiously"],"parley","careful, he must say it","wary",None),
 (["sarcastic"],"talk","cold, dry","contempt",None),
 (["softly"],"followed","quiet, the point lands","pleading",None),
 ([],"left","sharp, quick, to Murat","pressure",1.5),
 (["thoughtful"],"want","lower, a question he has never asked","unsettled",None),
 (["softly"],"Sunrise","steady, clipped","relief",None),
 (["matter of fact"],"hear","flat, final","resolve",None),
 (["slowly"],"ask","slow, wry","foreboding",None)],
'S07':[(["slowly"],"grandmother's","slow, ceremonial, a place being set","tension",None),
 (["matter of fact"],"price","stiff, a man not used to asking","pride",None),
 (["softly"],"long","mild, almost amused","calm",None),
 ([],"patience","tight, held down","anger",None),
 (["slowly"],"fire","quiet, no threat in it","cool",0.6),
 (["hesitant"],"thirty","low and quick, for the emperor only","alarm",None),
 (["matter of fact"],"sale","firm, proud","pride",None),
 (["slowly"],"now","told flat, a long beat before 'He said so'","reflective",None),
 (["deadpan"],"soldiers","dry, proud","defiance",None),
 (["cautiously"],"yes","steady for the first time, quick, he speaks first","courage",None),
 (["softly"],"counts","level, a small approval","respect",None),
 (["curious"],"tell","sharp, suspicious","suspicion",None),
 (["deadpan"],"Exactly","dry, closed","dignity",None),
 (["slowly"],"around","slow, a held breath, then silence","gravity",0.5)],
'S08':[(["suspenseful"],"word","low, the fog closing","hush",None),
 (["softly"],"barrel","slow, almost tender","unease",None),
 (["matter of fact"],"missing","flat, the clerk's voice","wry",None),
 (["deadpan"],"guns","level, a ledger closing","wry",None),
 ([],"again","quiet, the opening mirrored","wonder",None)]}
for s in doc['segments']:
    ps=P[s['id']]; assert len(ps)==len(s['lines']),(s['id'],len(ps),len(s['lines']))
    for ln,(tags,emp,tone,emo,pause) in zip(s['lines'],ps):
        if tags: ln['tags']=tags
        if emp:
            assert emp.lower() in ln['text'].lower(),(s['id'],emp,ln['text'])
            ln['emphasis']=[emp]
        ln['tone']=tone; ln['emotion']=emo
        if pause: ln['pause_after']=pause
s6=next(s for s in doc['segments'] if s['id']=='S06')
assert s6['lines'][9]['text']=="Then we go and hear it."
s6['lines'][9]['text']="Right. Then we go and hear it."
json.dump(doc,open(A+'production_script.json','w'),indent=1,ensure_ascii=False)
