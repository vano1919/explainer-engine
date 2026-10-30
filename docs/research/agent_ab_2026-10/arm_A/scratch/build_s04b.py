import json
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
doc=json.load(open(A+'scratch/s04_shots_only.json'))
S={s['id']:s for s in doc['segments']}
# staging
S['S02']['staging']={"scene_id":"road_ridge","location":"a grass rise on the Moscow road at the edge of the lifted fog","layout":"the rise in the centre foreground, the wagon train behind on the left, the ridges with riders across the right and back","fixed":["knee-high grass","riders sitting still on the ridges","the stalled wagons on the left"],"roster":["napoleon","aslan"],"positions":{"napoleon":"left of centre on the rise","aslan":"right of centre, one step back"},"master":"s02_master"}
S['S04']['staging']={"scene_id":"khan_tent","location":"inside the khan's felt tent on the ridge","layout":"a low fire in the middle, the khan seated at the back, the prisoner standing at the left, the archer standing behind the khan on the right","fixed":["felt walls","low fire","open smoke hole","a bow rack at the back"],"roster":["genghis","aslan","jebe"],"positions":{"aslan":"left, before the fire","genghis":"centre, seated behind the fire","jebe":"right, standing behind the khan"},"master":"s04_master"}
S['S06']['staging']={"scene_id":"burnt_wagons","location":"among the burnt wagon wrecks at the rear of the army at night","layout":"the three stand in a ring of smouldering wagon wrecks, the dark steppe beyond","fixed":["smouldering wagon wrecks","embers drifting","night"],"roster":["napoleon","aslan","murat"],"positions":{"murat":"left","napoleon":"centre","aslan":"right"},"master":"s06_master"}
S['S07']['staging']={"scene_id":"parley_ground","location":"open grass between the two armies, a felt carpet with two stools","layout":"the khan seated on the right stool, the emperor standing at the left, the interpreter a step back between them, the two armies far behind each","fixed":["felt carpet","two stools","wind in the grass","the two armies far behind"],"roster":["napoleon","genghis","aslan"],"positions":{"napoleon":"left, standing","aslan":"centre, a step back","genghis":"right, seated"},"master":"s07_master"}
# audio: library ids exist in the manifest; the media is not in git (PV-05 environmental, like the shipped example)
def bed(at,sound,db,purpose): return {"at":at,"sound":sound,"gain_db":db,"purpose":purpose,"yields_to":["voice"]}
def fx(at,sound,db,purpose,off=None):
    e={"at":at,"sound":sound,"gain_db":db,"purpose":purpose,"yields_to":["voice"]}
    if off is not None: e["offset_s"]=off
    return e
WIND="amb_steppe_wind__v1"
S['S01']['audio']={"beds":[bed("The drums stop first",WIND,-30,"place: the cold road, then the open steppe")],
 "sfx":[fx("fog","landing_thud__v1",-20,"the fog drops: the accent's impact")]}
S['S02']['audio']={"beds":[],"sfx":[fx("sinking to the axle","cloth_rustle__v1",-28,"the wagons straining in the mud"),fx("He sends for Murat","footstep_grass__v1",-26,"Murat's horse arriving")]}
S['S03']['audio']={"beds":[],"sfx":[fx("turn and go","swish__v1",-26,"the riders wheel away"),fx("falls","landing_thud__v1",-20,"the horse falls: the accent's impact")]}
S['S04']['audio']={"beds":[bed("Two riders took him","amb_tent_fire__v1",-30,"place: inside the khan's tent, a low fire")],
 "sfx":[fx("felt tent","cloth_rustle__v1",-28,"the tent flap")]}
S['S05']['audio']={"beds":[bed("Napoleon trained",WIND,-30,"place: the valley rim, the steppe wind returns")],
 "sfx":[fx("tears lanes","landing_thud__v1",-20,"the round shot hits: the accent's impact")]}
S['S06']['audio']={"beds":[bed("The cheering stops","amb_ash_night__v1",-30,"place: the burning wagon train and its ash at night")],
 "sfx":[fx("rides back to the ashes","footstep_dirt__v1",-27,"horses walking into the ash")]}
S['S07']['audio']={"beds":[bed("Open ground",WIND,-31,"place: the open parley ground, the steppe wind again")],
 "sfx":[fx("And the men who fire them","reveal_sting__v1",-24,"the sting that breaks the planned music dropout before the biggest reveal")]}
S['S08']['audio']={"beds":[bed("At dawn the fog comes back",WIND,-30,"place: dawn on the steppe, then the Russian road")],
 "sfx":[fx("fog comes back","swish__v1",-24,"the fog closes: the accent's impact"),fx("A clerk counts","tick__v1",-30,"the clerk's pencil ticking off guns")]}
for k in ('S01','S04','S06'): pass
# music: one track per chapter, a planned 1.5 s dropout before the biggest reveal (S07 'Two guns stay'), broken by reveal_sting
doc['music']=[
 {"track":"fog_drone_loop__v1","from":"<start>","to":"Aslan was the last man","gain_db":-30,"fade_s":2.0},
 {"track":"tent_low_strings__v1","from":"Aslan was the last man","to":"Napoleon trained","gain_db":-31,"fade_s":2.0},
 {"track":"valley_drums__v1","from":"Napoleon trained","to":"And the men who fire them","gain_db":-27,"fade_s":2.0},
 {"track":"fog_drone_loop__v1","from":"Sire, a gun takes fifteen","to":None,"gain_db":-30,"fade_s":2.0}]
doc['counter']=[]
doc['world']={"topic":"an army of 1812 falls through a fog into the steppe of 1223 and meets Genghis Khan","host":{"era":"medieval_europe","place":"the open steppe of 1223: knee-high grass, felt tents, ridges full of horsemen","when":"summer 1223"},"visitors":[],"light_owner":"host","day_arc":[{"beat":1,"light":"overcast"},{"beat":2,"light":"overcast"},{"beat":3,"light":"overcast"},{"beat":4,"light":"candle_night"},{"beat":5,"light":"overcast"},{"beat":6,"light":"candle_night"},{"beat":7,"light":"overcast"},{"beat":8,"light":"overcast"}]}
json.dump(doc,open(A+'production_script.json','w'),indent=1,ensure_ascii=False)
