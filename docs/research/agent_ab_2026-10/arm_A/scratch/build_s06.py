import json,copy
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
doc=json.load(open(A+'s05_caster.json'))
json.dump(doc,open(A+'scratch/before.json','w'),indent=1,ensure_ascii=False)
TITLE="What If Napoleon's Army Walked Into Genghis Khan?"
def N(t,claims=None,tags=None,emph=None,pause=None):
    l={"text":t}
    if claims: l["claims"]=claims
    if tags: l["tags"]=tags
    if emph: l["emphasis"]=[emph]
    if pause: l["pause_after"]=pause
    return l
def H(sp,to,t,intent,claims=None,tags=None,emph=None):
    l={"text":t,"speaker":sp,"to":to,"intent":intent}
    if claims: l["claims"]=claims
    if tags: l["tags"]=tags
    if emph: l["emphasis"]=[emph]
    return l
sh=[]
sh.append({"id":"SH01","style":"cold_open_cliffhanger","ending":"cliffhanger","source_period":"S01-S02",
 "hook":"What if an army fell into 1223?",
 "lines":[N("What if an army fell into 1223?",["C-91"],["curious"],"1223"),
  N("October 1812. Napoleon's army is leaving a burning Moscow.",["C-12"],None,"Moscow"),
  N("But then the drums stop, and the road is gone.",["C-91"],["suspenseful"],"gone"),
  N("Cold grass. Riders on every ridge. No army to fight.",["C-91"],None,"fight"),
  N("Napoleon wants one great battle.",["C-04"],None,"battle"),
  N("The riders just keep their distance. And somebody is watching.",["C-91"],["suspenseful"],"watching"),
  N("Full video: "+TITLE,None,["matter of fact"],"Khan")],
 "shots":[{"at":"What if an army","picture":"s01_fog","crop_x":0.5,"zoom":1.0},
  {"at":"fell into 1223","picture":"s01_steppe","crop_x":0.5,"zoom":1.1},
  {"at":"October 1812","picture":"s01_road","crop_x":0.5,"zoom":1.15},
  {"at":"But then the drums stop","picture":"s01_fog","crop_x":0.4,"zoom":1.2},
  {"at":"Cold grass","picture":"s01_ridge","crop_x":0.5,"zoom":1.1},
  {"at":"Napoleon wants one great battle","picture":"s01_nap","crop_x":0.45,"zoom":1.3},
  {"at":"The riders just keep","picture":"s02_ridge" if False else "s02_master","crop_x":0.7,"zoom":1.2},
  {"at":"Full video","picture":"s08_fog","crop_x":0.5,"zoom":1.0}]})
sh.append({"id":"SH02","style":"dialogue_clash","ending":"pointer","source_period":"S07",
 "hook":"What does Genghis Khan want from Napoleon?",
 "lines":[N("What does Genghis Khan want from Napoleon?",None,["curious"],"Napoleon"),
  N("Watch what the khan asks for.",None,["suspenseful"],"asks"),
  H("napoleon","genghis","Name your price. My army is leaving.","press",None,["matter of fact"],"price"),
  H("genghis","napoleon","Two guns stay on this grass. And the men who fire them.","reveal",["C-94"],["slowly"],"fire"),
  H("napoleon","genghis","The guns, yes. French soldiers are not for sale.","decide",["C-94"],["matter of fact"],"sale"),
  H("genghis","napoleon","A man shot my horse once. He said so. He leads my right hand now.","deflect",["C-11"],["slowly"],"now"),
  H("aslan","genghis","Great khan, the guns stay. The men go home. Say yes.","decide",["C-94"],["cautiously"],"yes"),
  H("genghis","aslan","Good. A man who speaks when it counts.","concede",None,["softly"],"counts"),
  N("Watch the full video: "+TITLE,None,["matter of fact"],"Khan")],
 "shots":[{"at":"What does Genghis Khan","picture":"s07_master","crop_x":0.5,"zoom":1.0},
  {"at":"Khan want from Napoleon","picture":"s07_gen_close","crop_x":0.5,"zoom":1.0},
  {"at":"Name your price","picture":"s07_nap_os","crop_x":0.58,"zoom":1.1},
  {"at":"Two guns stay","picture":"s07_nap_close","crop_x":0.5,"zoom":1.1},
  {"at":"The guns, yes","picture":"s07_nap_os","crop_x":0.58,"zoom":1.25},
  {"at":"A man shot my horse","picture":"s07_gen_os","crop_x":0.42,"zoom":1.15},
  {"at":"Great khan, the guns stay","picture":"s07_aslan_close","crop_x":0.5,"zoom":1.1},
  {"at":"Good. A man who speaks","picture":"s07_gen_close","crop_x":0.5,"zoom":1.2},
  {"at":"Watch the full video","picture":"s07_guns","crop_x":0.5,"zoom":1.0}]})
sh.append({"id":"SH03","style":"fact_bomb","ending":"pointer","source_period":"S05-S06",
 "hook":"Why did Napoleon's guns win and still lose?",
 "lines":[N("Why did Napoleon's guns win and still lose?",None,["curious"],"lose"),
  N("His guns shot nine hundred metres.",["C-05"],None,"nine"),
  N("But the khan's arrows reached four hundred.",["C-09"],None,"four"),
  N("So the guns won the fight, and the army cheered.",["C-93"],None,"cheered"),
  N("An army eats from its wagons.",["C-16"],None,"wagons"),
  N("And the riders had just burned every one.",["C-93"],["suspenseful"],"burned"),
  N("Watch the full video: "+TITLE,None,["matter of fact"],"Khan")],
 "shots":[{"at":"Why did Napoleon's guns","picture":"s05_rim","crop_x":0.3,"zoom":1.0},
  {"at":"win and still lose","picture":"s05_guns","crop_x":0.5,"zoom":1.1},
  {"at":"His guns shot","picture":"s05_guns","crop_x":0.5,"zoom":1.25},
  {"at":"But the khan's arrows","picture":"s05_charge","crop_x":0.5,"zoom":1.1},
  {"at":"So the guns won","picture":"s05_cheer","crop_x":0.3,"zoom":1.2},
  {"at":"An army eats","picture":"s03_wagons","crop_x":0.5,"zoom":1.1},
  {"at":"And the riders had just burned","picture":"s06_ashes","crop_x":0.5,"zoom":1.15},
  {"at":"Watch the full video","picture":"s05_rim","crop_x":0.3,"zoom":1.0}]})
doc['shorts']=sh
json.dump(doc,open(A+'production_script.json','w'),indent=1,ensure_ascii=False)
