import json,copy
A='/home/user/explainer-engine/jobs/ab_agents_2026-10/arm_A/'
doc=json.load(open(A+'s03_performer.json'))
NAP="the short man in the grey greatcoat and black bicorne hat"
ASL="the lean rider in the red turban and Crimean cloak"
GEN="the broad weathered man in the fur-trimmed felt hat and quilted blue coat"
MUR="the tall rider in the huge plumed hat and gold-braided red jacket"
JEB="the lean scarred archer in the plain leather coat"
FR="French army of 1812: blue coats, white cross-belts, shakos, grey greatcoats, Mameluke riders in red turbans and baggy trousers"
MG="Mongol riders of 1223: felt hats, quilted coats, leather boots, horn bows"
def P(id,subject,heroes=(),speakers=None,framing=None,costume=None,visible=None,partial=None,change=None,cut_away=False,props=None,tier=None):
    p={"id":id,"engine":"gemini","subject":subject+", clear empty upper third"}
    if heroes: p["heroes"]=list(heroes)
    if speakers: p["speakers"]=speakers
    if costume: p["costume"]=costume
    if framing: p["framing"]=framing
    if visible: p["visible"]=visible
    if partial: p["partial"]=partial
    if cut_away: p["cut_away"]=True
    return p
def sh(at,typ,pic,motion,purpose,why,accents=None,**kw):
    s={"at":at,"type":typ,"picture":pic,"motion":motion,"purpose":purpose,"cut":{"why":why}}
    if accents: s["accents"]=accents
    s.update(kw)
    return s
def M(kind,z0,z1,dx=None,par=None):
    m={"kind":kind,"z0":z0,"z1":z1}
    if dx is not None: m["dx"]=dx
    if par is not None: m["parallax"]=par
    return m
W=lambda s=0.3:[{"kind":"wobble","strength":s}]
SH={}
# S01 hook
SH['S01']=[
 sh("The drums stop first","A",P("s01_road","a long grey column of tired soldiers on a muddy autumn road, drummer boys with sticks raised and frozen mid-beat, the smoke of a burned city low on the horizon",costume=FR),M("push",1.0,1.07),"cold open: the drums stop on the Moscow road","sound from the first frame, the drums are the hook",W(0.3)),
 sh("Then a fog drops","A",P("s01_fog","thick white fog swallowing a wagon train and the column on the road, soldiers fading to pale shapes, the road itself gone",costume=FR),M("push",1.0,1.08),"the fog drops and takes the road","hard cut on the fog: the world changes",None),
 sh("When the fog thins","A",P("s01_steppe","an endless cold steppe of knee-high grass to the horizon, a tiny wagon train and a thin dark column stranded in the middle, no road, no village",costume=FR),M("pan",1.04,1.04,dx=0.06),"the fog thins on a different world","reveal wide: the scale of being lost",W(0.3)),
 sh("Napoleon has an army","B",P("s01_nap","the short man in the grey greatcoat and black bicorne hat stands on a grass rise with a spyglass raised, hard pale stare, the stranded column below him",heroes=["napoleon"],speakers={"napoleon":[0.45,0.45]},framing="medium",costume=FR),M("push",1.0,1.09),"Napoleon and his one plan","cut to the man who has the plan",None),
 sh("But the people who live here","A",P("s01_ridge","the people who live here: a long far ridge above the road at dusk, lined with the dark silhouettes of horsemen with bows, still as fence posts, a bruised sky",costume=MG),M("pull",1.08,1.0),"the people who live here wait","the turn: but, the other side appears",W(0.3),reuse="unique"),
]
# S02
SH['S02']=[
 sh("By noon the fog is gone","A",P("s02_master","wide shot of a grass rise at noon: the short man in the grey greatcoat and black bicorne hat stands beside the lean rider in the red turban and Crimean cloak, riders sitting still on every far ridge, the stalled wagon train behind",heroes=["napoleon","aslan"],speakers={"napoleon":[0.34,0.5],"aslan":[0.66,0.52]},framing="wide",costume=FR),M("pull",1.07,1.0),"establish the scene: two men, ridges full of riders","open on the two-shot so the viewer knows who stands where",W(0.3)),
 sh("Where is their army","B",P("s02_nap_os","over the shoulder of the lean rider in the red turban, the short man in the grey greatcoat and black bicorne hat glares out at the ridges, face to camera",heroes=["napoleon","aslan"],partial=["aslan"],visible=["napoleon"],speakers={"napoleon":[0.62,0.42]},framing="over_shoulder",costume=FR),M("push",1.0,1.06),"Napoleon demands the army","A side of the exchange",None),
 sh("Riders. When I rode closer","B",P("s02_aslan_os","over the shoulder of the short man in the black bicorne hat, the lean rider in the red turban and Crimean cloak answers with a careful face to camera",heroes=["aslan","napoleon"],partial=["napoleon"],visible=["aslan"],speakers={"aslan":[0.4,0.45]},framing="over_shoulder",costume=FR),M("push",1.0,1.05),"Aslan reports riders only","B side: the reverse",None),
 sh("Then we ride faster","B","s02_nap_os",M("pull",1.06,1.02),"Napoleon dismisses it","back to Napoleon; L-cut: his voice arrives before the face",None),
 sh("The wagons are sinking","C",P("s02_wagons","a heavy supply wagon with its wheels buried to the axle in wet grass, a driver heaving at the wheel, nobody to help",costume=FR,framing="insert",cut_away=True),M("hold",1.03,1.03),"the wagons cannot follow","pattern break: an insert of the thing being said",W(0.4)),
 sh("Sire. I understand their shouts","B",P("s02_aslan_close","close on the lean rider in the red turban, eyes wide, listening to far shouting, the grass blowing behind him",heroes=["aslan"],speakers={"aslan":[0.5,0.45]},framing="close",visible=["aslan"],costume=FR),M("push",1.0,1.1),"Aslan's reveal: the language is his grandmother's","the reveal goes to the speaker's face, the listener comes next",None),
 sh("Dead","B",P("s02_nap_close","close on the short man in the black bicorne hat, his hard stare cracking for one second as the riders on the ridge shout, mouth half open",heroes=["napoleon"],speakers={"napoleon":[0.5,0.45]},framing="close",visible=["napoleon"],costume=FR),M("push",1.0,1.08),"Napoleon's certainty cracks","the listener's reaction on news",None),
 sh("Murat rides at first light","B",P("s02_murat","far on the road the tall rider in the huge plumed hat and gold-braided red jacket reins in a rearing horse and turns it toward the riders on the ridge",heroes=["murat"],speakers={"murat":[0.55,0.5]},framing="medium",costume=FR,cut_away=True),M("pan",1.03,1.03,dx=-0.05),"Murat is the name in the order","the order names Murat: his picture arrives with his name",None,reveal="Murat on the road"),
 sh("He doesn't ask what year","B","s02_murat",M("push",1.03,1.08),"he does not ask what year it is","reframe on Murat as the narrator closes: the cavalry is sent for",None),
 sh("But the riders on the ridge","A","s02_master",M("pull",1.1,1.03),"the riders are already waiting","back to the wide: the ridges, the next pressure",None),
]
# S03
SH['S03']=[
 sh("Murat takes the cavalry","B",P("s03_charge","the tall rider in the huge plumed hat and gold-braided red jacket leads a charge of cavalry over the grass at first light, sabres up, the horsemen on the ridge turning away ahead",heroes=["murat"],speakers={"murat":[0.45,0.45]},framing="medium",costume=FR),M("push",1.0,1.08),"Murat charges","a new scene, hard cut on action",None),
 sh("He chases","A","s03_charge",M("pan",1.1,1.1,dx=0.07),"they hold the distance and shoot","reframe wide-to-side: the same charge, the distance held",None),
 sh("Every rider has three","A",P("s03_remount","a Mongol rider swaps from one galloping horse to a spare without slowing, three more spare horses running beside him",costume=MG),M("push",1.02,1.07),"three or four horses each","detail: the answer to the chase",W(0.3)),
 sh("Murat has one","B",P("s03_horse","the tall rider in the huge plumed hat and gold-braided red jacket stands over his collapsed grey horse in the grass, riding crop in hand, already looking ahead",heroes=["murat"],speakers={"murat":[0.45,0.4]},framing="medium",costume=FR),M("push",1.0,1.06),"Murat rides his one horse to death","contrast with the previous picture",None),
 sh("By dusk the best cavalry","A",P("s03_walk","a long dusk line of cavalrymen walking home on foot leading thin tired horses, their helmets dull, the wagon line far behind",costume=FR),M("pull",1.07,1.0),"the cavalry walks home","the cost of the day, wide and slow",W(0.3)),
 sh("Now the heavy wagons","A",P("s03_wagons","a long line of heavy wagons stuck to the axle in the grass at dusk, drivers whipping the oxen, the first low wolves of darkness",costume=FR,cut_away=True),M("push",1.0,1.06),"the wagons fall behind","the next pressure",None),
]
# S04
SH['S04']=[
 sh("Aslan was the last man","A",P("s04_tent","the lean rider in the red turban walked up a dusk ridge between two mounted riders in felt hats toward a felt tent with smoke rising, Mongol horsemen camped all round",heroes=["aslan"],framing="wide",cut_away=True,costume=MG+"; the prisoner in red turban and Crimean cloak"),M("push",1.0,1.06),"Aslan is taken to the tent","new place: the khan's ridge, wide first",W(0.3)),
 sh("A man by the fire said","A",P("s04_master","inside a felt tent: the broad weathered man in the fur-trimmed felt hat sits by a low fire, the lean scarred archer in the plain leather coat stands behind him to the right, the lean rider in the red turban stands before the fire to the left",heroes=["genghis","jebe","aslan"],speakers={"genghis":[0.5,0.42],"jebe":[0.8,0.4],"aslan":[0.2,0.45]},framing="wide",costume=MG+"; the prisoner in red turban and Crimean cloak"),M("push",1.0,1.09),"the khan's silence","establishing two-shot of the whole tent: seats fixed",W(0.3),reveal="Genghis Khan by the fire, with Jebe behind him"),
 sh("How far do the long iron","B",P("s04_gen_os","over the shoulder of the lean rider in the red turban, the broad weathered man in the felt hat looks at the prisoner across the low fire, calm",heroes=["genghis","aslan"],partial=["aslan"],visible=["genghis"],speakers={"genghis":[0.6,0.4]},framing="over_shoulder",costume=MG+"; prisoner in red turban"),M("push",1.0,1.05),"the khan questions","A side of the exchange",None),
 sh("Far enough to trouble","B",P("s04_aslan_os","over the shoulder of the broad man in the felt hat, the lean rider in the red turban answers stiffly with chin raised",heroes=["aslan","genghis"],partial=["genghis"],visible=["aslan"],speakers={"aslan":[0.4,0.42]},framing="over_shoulder",costume=MG+"; prisoner in red turban"),M("push",1.0,1.05),"Aslan deflects","B side",None),
 sh("Your emperor hides","B","s04_gen_os",M("pull",1.05,1.01),"the khan's mild insult","J-cut: the khan's voice starts under Aslan's last word",None),
 sh("Nine hundred metres","B",P("s04_gen_close","close on the broad weathered man in the felt hat, a small satisfied stillness in his eyes by the firelight",heroes=["genghis"],speakers={"genghis":[0.5,0.42]},framing="close",visible=["genghis"],costume=MG),M("push",1.0,1.09),"the khan hears what he wanted","the listener on the reveal",None),
 sh("Good. That is all I asked","B",P("s04_aslan_close","close on the lean rider in the red turban, jaw clenched, understanding the trap",heroes=["aslan"],speakers={"aslan":[0.5,0.45]},framing="close",visible=["aslan"],costume="red turban and Crimean cloak"),M("push",1.0,1.08),"Aslan sees the trap","reaction to the khan's good",None),
 sh("Jebe shot my horse","B",P("s04_jebe","the lean scarred archer in the plain leather coat stands behind the fire with a horn bow across his back, unreadable, the khan's shoulder in the foreground",heroes=["jebe","genghis"],partial=["genghis"],visible=["jebe"],speakers={"jebe":[0.55,0.4]},framing="over_shoulder",costume=MG),M("hold",1.03,1.03),"Jebe is the proof of the story","pattern break: the man himself, silent",W(0.3)),
 sh("I kept him","B","s04_gen_os",M("push",1.05,1.1),"the khan keeps honest men","back to the khan over Aslan's shoulder",None),
 sh("At dawn they send","B","s04_aslan_os",M("push",1.05,1.09),"Aslan is sent back","hold on the interpreter as the narrator takes over",None),
 sh("The khan knows how far","A",P("s04_dawn","a lone rider in a red turban rides down a dawn ridge toward a faraway army camp, the broad man in the felt hat watching him go from the heights with his horsemen",heroes=["aslan","genghis"],framing="wide",cut_away=True,costume=MG+"; the rider in red turban"),M("pan",1.03,1.03,dx=-0.06),"Aslan is sent back","hold the hero's mood under the narrator's first sentence, then move to dawn",W(0.3)),
]
# S05
SH['S05']=[
 sh("Napoleon trained","A",P("s05_rim","a valley seen from its rim: heavy guns wheel to wheel along the rim, infantry squares bristling with bayonets in the valley below, the short man in the grey greatcoat small beside a gun with a spyglass",heroes=["napoleon"],speakers={"napoleon":[0.3,0.42]},framing="wide",costume=FR),M("pull",1.08,1.0),"the plan: guns on the rim, squares below","new place: the valley, wide",W(0.3)),
 sh("The riders come at a gallop","A",P("s05_charge","a great mass of Mongol horse archers pouring down the far slope at a gallop, bows raised, arrows already arcing against the sky",costume=MG),M("push",1.0,1.07),"the riders come","cut on action",None),
 sh("The guns answer","B",P("s05_guns","a gun crew in blue coats heaving a heavy gun back from its recoil in a cloud of smoke, far out on the grass horses and riders tumbling in the blast lanes",costume=FR),M("push",1.0,1.08),"the guns answer at nine hundred","hard cut on the blast",None),
 sh("The few that reach","A",P("s05_square","a tight infantry square with bayonets out, a few riders breaking against its edge and falling, the soldiers motionless in the smoke",costume=FR),M("pull",1.07,1.0),"the squares hold","wide: the formation holds still",W(0.3)),
 sh("The riders wheel away","A",P("s05_cheer","soldiers in the foreground throw shakos in the air and cheer, far behind them the horse archers wheel away calmly in good order",costume=FR),M("pan",1.03,1.03,dx=0.06),"false victory: the army cheers, the riders retire in order","wide contrast: cheering foreground, calm distance",W(0.3)),
]
# S06
SH['S06']=[
 sh("The cheering stops","A",P("s06_ashes","a night road where a whole wagon train burns in a long line of fire, one rider on foot staggering toward the camp, sparks drifting into the dark",cut_away=True,costume=FR),M("push",1.0,1.07),"the wagons burn","hard cut to night: the cheering stops",None),
 sh("Napoleon rides back","A",P("s06_master","wide night shot among burnt wagon wrecks still smoking: the short man in the grey greatcoat and black bicorne hat stands in the middle, the lean rider in the red turban at his right, the tall rider in the huge plumed hat at his left",heroes=["napoleon","aslan","murat"],speakers={"napoleon":[0.5,0.45],"aslan":[0.78,0.5],"murat":[0.22,0.48]},framing="wide",costume=FR),M("pull",1.07,1.0),"the three stand in the ash","establishing shot of the ashes, seats fixed",W(0.3)),
 sh("We march at dawn","B",P("s06_nap_os","over the shoulder of the lean rider in the red turban, the short man in the grey greatcoat and black bicorne hat speaks hard, burnt wagons glowing behind him",heroes=["napoleon","aslan"],partial=["aslan"],visible=["napoleon"],speakers={"napoleon":[0.6,0.42]},framing="over_shoulder",costume=FR),M("push",1.0,1.05),"Napoleon will march on","A side of the exchange",None),
 sh("Sire, the Cuman rider asks","B",P("s06_aslan_os","over the shoulder of the short man in the black bicorne hat, the lean rider in the red turban speaks low and careful, firelight on his face",heroes=["aslan","napoleon"],partial=["napoleon"],visible=["aslan"],speakers={"aslan":[0.42,0.42]},framing="over_shoulder",costume=FR),M("push",1.0,1.05),"Aslan brings the parley","B side",None),
 sh("A man who burns my wagons","B","s06_nap_os",M("pull",1.05,1.01),"Napoleon refuses","J-cut: Napoleon's voice starts over Aslan's last word",None),
 sh("Murat. How many rounds","B",P("s06_murat","close on the tall rider in the huge plumed hat, plume singed, eyes lowered, no answer","heroes"and["murat"],speakers={"murat":[0.5,0.45]},framing="close",visible=["murat"],costume=FR),M("hold",1.04,1.04),"Murat has no answer","silent reaction to the question",W(0.3)),
 sh("What does he want","B",P("s06_nap_close","close on the short man in the black bicorne hat with a sliver of the red turban at the frame edge, the stare thinner, asking a question he has never asked",heroes=["napoleon","aslan"],partial=["aslan"],speakers={"napoleon":[0.5,0.45]},framing="close",visible=["napoleon"],costume=FR),M("push",1.0,1.07),"the first question to an enemy","the turn of the scene, close",None),
 sh("He didn't say","B","s06_aslan_os",M("pull",1.05,1.0),"the hour: sunrise","L-cut: Aslan's answer over Napoleon's face first",None),
 sh("At sunrise he rides out","A",P("s06_ride","at sunrise the short man in the grey greatcoat and the lean rider in the red turban ride out alone over the grass toward a far line of horsemen, the army's tired guns trailing behind them",heroes=["napoleon","aslan"],framing="wide",cut_away=True,costume=FR),M("pan",1.03,1.03,dx=0.06),"he rides out to ask","hold the hero's mood under the narrator's first sentence, then move to the sunrise",W(0.3)),
]
# S07
SH['S07']=[
 sh("Open ground, a felt carpet","A",P("s07_master","wide shot of open grass between two armies: a felt carpet with two stools, the broad man in the felt hat seated at the right, the short man in the grey greatcoat standing at the left, the lean rider in the red turban a step back between them",heroes=["napoleon","genghis","aslan"],speakers={"napoleon":[0.25,0.5],"genghis":[0.75,0.5],"aslan":[0.5,0.55]},framing="wide",costume=FR+"; "+MG),M("pull",1.07,1.0),"establish the parley ground and seats","open on the wide master: the seats stay fixed",W(0.3)),
 sh("Name your price","B",P("s07_nap_os","over the shoulder of the lean rider in the red turban, the short man in the grey greatcoat and black bicorne hat stands stiff, speaking to the seated khan",heroes=["napoleon","aslan"],partial=["aslan"],visible=["napoleon"],speakers={"napoleon":[0.58,0.4]},framing="over_shoulder",costume=FR),M("push",1.0,1.05),"Napoleon asks for terms","A side",None),
 sh("You came without your wagons","B",P("s07_gen_os","over the shoulder of the lean rider in the red turban, the broad man in the felt hat sits on his stool, mild, watching the visitor",heroes=["genghis","aslan"],partial=["aslan"],visible=["genghis"],speakers={"genghis":[0.42,0.42]},framing="over_shoulder",costume=MG),M("push",1.0,1.05),"the khan toys with him","B side",None),
 sh("Longer than your patience","B","s07_nap_os",M("pull",1.05,1.01),"Napoleon holds himself in","back to A: continues the move",None),
 sh("Two guns stay","B",P("s07_nap_close","close on the short man in the black bicorne hat, jaw tightening as he hears the price",heroes=["napoleon"],speakers={"napoleon":[0.5,0.45]},framing="close",visible=["napoleon"],costume=FR),M("push",1.0,1.05),"Napoleon hears two guns stay and the men","J-cut: the khan's voice goes on under Napoleon's close-up; the listener on news",None),
 sh("And the men who fire them","B","s07_nap_close",M("push",1.03,1.1),"the second half of the price lands","reframe on the same face: the sting breaks the music here",None),
 sh("Sire, a gun takes fifteen","B",P("s07_aslan_close","close on the lean rider in the red turban, leaning to his emperor to price the guns in men, speaking low and quick",heroes=["aslan"],speakers={"aslan":[0.5,0.45]},framing="close",visible=["aslan"],costume=FR),M("push",1.0,1.07),"Aslan counts the price","the translator speaks for himself",None),
 sh("The guns, yes","B","s07_nap_os",M("push",1.05,1.1),"Napoleon refuses the men","back to A: fresh push",None),
 sh("A man shot my horse once","B",P("s07_gen_close","close on the broad weathered man in the felt hat, level eyes, telling a story as an offer",heroes=["genghis"],speakers={"genghis":[0.5,0.43]},framing="close",visible=["genghis"],costume=MG),M("push",1.0,1.08),"the khan offers the Jebe bargain","close on the speaker, quiet",None),
 sh("I have no archers","B","s07_nap_close",M("pull",1.09,1.02),"Napoleon deflects","the listener's face holds the refusal",None),
 sh("Great khan, the guns stay","B","s07_aslan_close",M("pull",1.07,1.0),"Aslan speaks first","the translator takes the scene: reframe",None),
 sh("Good. A man who speaks","B","s07_gen_close",M("pull",1.08,1.01),"the khan approves","the listener-speaker pays him",None),
 sh("What did you tell him","B","s07_nap_os",M("hold",1.06,1.06),"Napoleon asks, Aslan answers over his face","L-cut: Aslan's answer runs over Napoleon's face",None),
 sh("The khan nods once","B","s07_gen_close",M("push",1.05,1.1),"the khan's nod seals the price","the khan's face, a held mood under the narrator's conclusion",None),
 sh("Two guns are unhitched","B",P("s07_guns","two heavy guns unhitched and left on the grass beside the felt carpet, their limbers pulling away, the broad man in the felt hat seated and watching them, the short man in the grey greatcoat walking away without looking back",heroes=["napoleon","genghis"],framing="wide",costume=FR,cut_away=True),M("pan",1.03,1.03,dx=0.05),"two guns left to the khan","wide: the price paid, no faces",W(0.3)),
]
# S08
SH['S08']=[
 sh("At dawn the fog comes back","A",P("s08_fog","the army walks into a wall of white fog at dawn, the column vanishing rank by rank, the grass trampled behind them",costume=FR),M("push",1.0,1.08),"the fog takes the army back","mirror of the first fog",None),
 sh("Behind it, two guns","B",P("s08_guns","two heavy guns stand alone on the grass where the carpet was, the broad weathered man in the felt hat walks slowly round one and lays a hand on its barrel",heroes=["genghis"],speakers={"genghis":[0.55,0.45]},framing="medium",costume=MG),M("push",1.0,1.07),"the khan inspects the guns","cut to the other side of the fog",None),
 sh("On the far side the road","A",P("s08_clerk","a muddy Russian road at dusk, a clerk with a ledger and a lamp counting guns as they roll past, one gap in the line",costume=FR),M("pan",1.03,1.03,dx=0.05),"the clerk counts two missing","hard cut: back in 1812",None),
 sh("Napoleon never got","B",P("s08_nap","the short man in the grey greatcoat and black bicorne hat on a horse at the roadside, watching his army pass, tired, a long look back at the empty grass",heroes=["napoleon"],speakers={"napoleon":[0.5,0.42]},framing="medium",costume=FR),M("push",1.0,1.07),"he got his army out","the answer to the dramatic question",W(0.3)),
 sh("Then the drums start","A","s01_road",M("pull",1.07,1.02),"the drums start again: the opening mirrored","callback: the first picture again, new meaning",None),
]
for s in doc['segments']:
    s['shots']=copy.deepcopy(SH[s['id']])
json.dump(doc,open(A+'scratch/s04_shots_only.json','w'),indent=1,ensure_ascii=False)
