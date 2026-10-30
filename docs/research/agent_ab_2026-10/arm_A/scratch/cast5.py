import json,sys
sys.path.insert(0,'/home/user/explainer-engine')
from explainer_engine.audio import casting
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
doc=json.load(open(A+'s04_editor.json'))
U="UNVERIFIED: taken from the voice ids earlier sessions recorded in examples/*/production_script.json; not checked against the live ElevenLabs library (no connector call in this test), age and accent unknown; the creator picks after the one-chunk test read (EL-02)"
V={
 "napoleon":{"style":"a middle-aged man's clipped, dry, imperious voice that speaks in short orders and thins to a hard quiet when pressed; medium energy, a faint French cast to the English, never loud",
  "traits":{"gender":"male","age":"middle_aged","temperament":["serious","confident","crisp"],"energy":"medium","origin":"corsican-born, French-speaking; English with a French accent","role":"hero","real_person":True,"living":False,
   "documented":["https://en.wikipedia.org/wiki/Napoleon (born 1769, so 43 in 1812; birth year recalled, page not re-fetched)","C-04 (preferred the offensive, aimed to destroy the enemy's army in battle: short, forceful orders)"]},
  "cand":[("Dg1lUQiSAGVHkoQMG3QX","Jerry B. - Premium Luxury Commercial","polished, understated, quiet authority; courteous and cold (recorded in titans_from_zero) - fits a dry, imperious register; no French accent known"),
          ("AyuyomQLIrhdNOsoDN2N","Christopher J Kelly - British","measured senior finance executive (recorded in titans_from_zero) - measured and crisp; British, not French"),
          ("WzVKtqQpTUUQ2JNx8YxI","Silas - Weathered Villain","low, precise, quietly threatening (recorded in titans_from_zero) - the hard quiet; may sound too villainous for the lead")]},
 "genghis":{"style":"an old man's low, slow, quiet voice with long pauses and almost no hurry, kind-sounding and level, that asks a question where another would boast; low energy, a steppe-born accent in the English",
  "traits":{"gender":"male","age":"old","temperament":["calm","serious","wise"],"energy":"low","origin":"mongolian, steppe-born","ethnicity":"mongolian","role":"rival","real_person":True,"living":False,
   "documented":["https://en.wikipedia.org/wiki/Genghis_Khan (born about 1162, so about 61 in 1223; steppe-born)","C-11 (promoted by merit and loyalty, kept the archer who admitted shooting his horse: a patient tester of men)"]},
  "cand":[("8wePOEVMsHVU2qfSJbtC","Lawrence","deep, subtly emotional, warm (recorded in stone_age) - low and level"),
          ("xkDz8dF9GIt1kG06c9Of","Ron 2","deep and soothing (recorded in stone_age) - slow and calm"),
          ("NOpBlnGInO9m6vDvFkFC","Grandpa Spuds Oxley","an old man's voice (recorded in syndicate_wars_ep1) - old, but was a narrator of episode 1")]},
 "aslan":{"style":"a young man's careful, formal voice, courteous and exact, that thins and quickens under fear and softens on a word of his grandmother's tongue; medium energy, a soft coastal accent in the English",
  "traits":{"gender":"male","age":"young","temperament":["formal","calm","soft"],"energy":"medium","origin":"crimean tatar from the black sea coast; English learned late and careful","ethnicity":"crimean tatar","role":"everyman"}  ,
  "cand":[("n9RJRb8CoeRtSYSpKZRH","Robert - Calm Confident British","calm and confident, British (recorded in syndicate_wars_ep1) - formal and exact; British, not Crimean"),
          ("HSBWXljo3oivWhybh3YX","Mr Wellington","a formal gentleman's voice (recorded in syndicate_wars_ep1) - formal; age unknown"),
          ("vrZ1gMhrsD9LI0gRKrLh","Chris - Warm, Thoughtful","middle-aged American, understated humour (recorded in titans_from_zero) - warm and careful; too old, last resort")]}}
doc['voice']={"provider":"elevenlabs","model":"eleven_v4","voice_id":None,"name":None,
 "style":"a warm, steady, slightly wry storyteller, low and unhurried on the strange parts and quicker on action, who talks to one listener",
 "pace_wpm":[160,185],
 "candidates":[{"voice_id":"l3OCvamakRoSUNIIz75n","name":"Brad - Warm, Trusted Storyteller","why":U+". A warm, quick-enough middle-aged American storyteller."},
  {"voice_id":"Ovio1nb5Thj5cZeW3MPS","name":"Alec","why":U+". Calm, warm, cinematic documentary."},
  {"voice_id":"oJUpLOe3yEYTEIjO6ddh","name":"Leo Ashcraft - Late-Night Radio Host","why":U+". Deep, warm, dry humour."}]}
queries={}
for h,v in V.items():
    c=doc['cast'][h]; c['voice']={"style":v["style"],"traits":v["traits"],"voice_id":None,"name":None,
        "candidates":[{"voice_id":i,"name":n,"why":U+". "+w} for i,n,w in v["cand"]]}
    assert not casting.problems(c),(h,casting.problems(c))
    queries[h]=casting.query(c); queries[h]["_relaxed"]=casting.relaxed(queries[h])
    queries[h]["_design_description_if_nothing_fits (paid, creator approves)"]=casting.design_description(c)
print(casting.distinct(doc['cast']))
json.dump(doc,open(A+'production_script.json','w'),indent=1,ensure_ascii=False)
json.dump(queries,open(A+'scratch/casting_queries.json','w'),indent=1)
print(json.dumps({h:{k:v for k,v in q.items() if not k.startswith('_')} for h,q in queries.items()},indent=0))
