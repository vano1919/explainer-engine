import json
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
doc=json.load(open(A+'production_script.json'))
json.dump(doc,open(A+'scratch/before.json','w'),indent=1,ensure_ascii=False)
def T(at,text,why,pos=(0.5,0.2)): return {"at":at,"kind":"text","text":text,"why":why,"pos":list(pos)}
def LB(at,text,why,pos): return {"at":at,"kind":"label","text":text,"why":why,"pos":list(pos)}
def PR(at,thing,asset,why): return {"at":at,"kind":"prop","thing":thing,"asset":asset,"why":why}
def SY(at,sym,why,pos=(0.8,0.3)): return {"at":at,"kind":"symbol","symbol":sym,"why":why,"pos":list(pos)}
def HI(at,why,pos): return {"at":at,"kind":"highlight","why":why,"pos":list(pos)}
def AC(at,eff,why,st=0.5): return {"at":at,"kind":"accent","effect":eff,"strength":st,"why":why}
def EX(at,who,ex,why): return {"at":at,"kind":"expression","who":who,"expression":ex,"why":why}
def CH(at,v,unit,claim,why): return {"at":at,"kind":"chart","chart":"counter","values":[v],"unit":unit,"claim":claim,"why":why}
B={
'SH01':[[AC("fell","punch","the army fell: a punch on fell",0.4),T("1223","1223","an army fell into the year 1223")],
 [T("October 1812","OCT 1812","the date the army leaves Moscow"),PR("burning Moscow","burning Moscow","icon:flame","Moscow is burning around the army")],
 [PR("drums stop","the drums stop","icon:hand-stop","the drums stop"),SY("road is gone","cross","the road is gone",(0.8,0.35))],
 [HI("Riders on every ridge","rings the riders on every ridge",(0.55,0.32)),SY("No army","cross","no army to fight",(0.8,0.25))],
 [LB("Napoleon","NAPOLEON","names the man who wants one battle",(0.4,0.55)),T("one great battle","ONE BATTLE","he wants one great battle")],
 [SY("keep their distance","equals","the riders keep the same distance",(0.8,0.3)),PR("somebody is watching","somebody watching","icon:eye","somebody is watching")],
 [LB("Full video","FULL VIDEO","points to the full video",(0.5,0.8))]],
'SH02':[[LB("Genghis Khan","GENGHIS KHAN","names the khan the question is about",(0.7,0.4)),SY("want","question","what does he want",(0.5,0.25))],
 [PR("Watch","watch the khan","icon:eye","watch what the khan asks for")],
 [EX("Name your price","genghis","curious","the khan hears name your price and studies him")],
 [EX("Two guns stay","napoleon","angry","Napoleon hears two guns stay and the men who fire them")],
 [EX("French soldiers","genghis","deadpan","the khan gives nothing back at french soldiers are not for sale")],
 [EX("leads my right hand","napoleon","doubtful","Napoleon weighs the man who leads my right hand now")],
 [EX("Say yes","genghis","surprised","the khan hears the interpreter say yes on his own")],
 [EX("speaks when it counts","aslan","deadpan","Aslan takes the praise: a man who speaks when it counts")],
 [LB("full video","FULL VIDEO","points to the full video",(0.5,0.8))]],
'SH03':[[LB("guns","GUNS","names the guns the hook is about",(0.4,0.5)),SY("lose","question","why did the guns win and still lose",(0.5,0.25))],
 [CH("nine hundred metres",900,"m","C-05","counts the nine hundred metres the guns shoot")],
 [CH("four hundred",400,"m","C-09","counts the four hundred metres the arrows reach")],
 [SY("won the fight","check","the guns won the fight",(0.8,0.3)),SY("cheered","exclaim","the army cheered",(0.8,0.25))],
 [PR("wagons","the wagons","icon:truck-delivery","an army eats from its wagons")],
 [PR("burned","the burned wagons","icon:flame","the riders had just burned every wagon")],
 [LB("full video","FULL VIDEO","points to the full video",(0.5,0.8))]]}
for sh in doc['shorts']:
    bl=B[sh['id']]; assert len(bl)==len(sh['lines']),(sh['id'],len(bl),len(sh['lines']))
    for ln,b in zip(sh['lines'],bl): ln['visual_beats']=b
json.dump(doc,open(A+'production_script.json','w'),indent=1,ensure_ascii=False)
