# picture catalog (stage 4): id -> (type, framing, heroes, cut_away, subject)
NAP = "Napoleon, the short stocky man in the grey-green coat and black bicorne hat"
MUR = "Murat, the tall flamboyant rider in the red-and-gold uniform and plumed hat"
KER = "Kerim, the lean Mameluke with the dark moustache and green turban"
KHN = "Genghis Khan, the broad weathered khan with long braids and a fur-rimmed felt cap"
PICS = {
 # S01-S03
 "p_arrow": ("C", "insert", ["napoleon"], False, "extreme close on a single arrow standing upright in wet green mud between two black cavalry boots, the hem of a grey-green coat at the top of the frame, thin fog"),
 "p_moscow_out": ("A", "wide", [], False, "a long column of exhausted French soldiers and heavy wagons trudging out of a burning Moscow, black smoke over onion domes, orange glow on a muddy road"),
 "p_steppe_fog": ("A", "wide", [], False, "the same column halted on an endless green steppe at dawn, thin fog tearing away, the soldiers staring at spring grass under a huge pale sky"),
 "p_n_look": ("B", "medium", ["napoleon"], False, f"{NAP} stares at an empty horizon, jaw set, a pocket spyglass hanging at his side, hungry for one decisive battle"),
 "p_riders_ridge": ("A", "wide", [], True, "an enemy that waits: a long ridge crowded with horse archers in felt caps sitting motionless on shaggy horses, bows across their knees, a pale sky behind"),
 "p_gun_empty": ("B", "medium", [], False, "a single bronze French cannon on a wet green rise, its muzzle pointing at an empty horizon, a tired gunner leaning on the wheel"),
 "p_map": ("A", "wide", [], False, "a hand-drawn map on old paper: Moscow in red flames at the right, a long road running west, small marching columns drawn as ink dots"),
 "p_neman": ("A", "wide", [], False, "the army crossing a river on pontoon bridges at dawn, endless columns of men and horse teams under flags"),
 "p_moscow_gate": ("A", "wide", [], False, "French troops marching through the gates of Moscow under onion domes, drums and flags, a city that looks empty"),
 "p_wagon_mud": ("C", "insert", [], False, "close on a heavy wooden supply wagon wheel sunk to the axle in thick mud, a sack of bread torn open on the tailgate"),
 "p_village_road": ("A", "wide", [], False, "a village beside a muddy road, French foragers carrying sacks and chickens out of the cottages"),
 "p_steppe_empty": ("A", "wide", [], False, "an endless green steppe with no road and no village to the horizon, a lone line of wheel tracks that ends in the grass"),
 "p_khan_ridge": ("A", "wide", ["genghis"], True, f"{KHN} on a shaggy horse at the top of a ridge against the sunrise, behind him two huge silent ranks of horsemen"),
 # S04 (scene 1)
 "p_rise_wide": ("A", "wide", ["napoleon", "murat", "kerim"], False, f"on a wet green rise above the halted column {NAP} stands at the crest, {MUR} sits his horse on the left and {KER} holds a second horse on the right, fog tearing off the far ridge"),
 "p_n_spyglass": ("B", "medium", ["napoleon"], False, f"{NAP} raises a spyglass to his eye toward the far ridge, one hand tucked in his coat, rigid with waiting"),
 "p_murat_med": ("B", "medium", ["murat"], False, f"{MUR} straining at the reins of his tall horse, whip in his fist, itching to charge"),
 "p_kerim_med": ("B", "medium", ["kerim"], False, f"{KER} holding the reins of two horses and watching the ridge with narrowed, wary eyes"),
 "p_ridge_far": ("A", "wide", [], True, "the far ridge in thinning fog with one tiny horseman on its crest, then nothing but wind in the grass"),
 "p_two_nm": ("B", "two_shot", ["napoleon", "murat"], False, f"{NAP} and {MUR} side by side on the crest, the marshal leaning toward the emperor, the emperor staring straight ahead"),
 "p_murat_close": ("B", "close", ["murat"], False, f"close on the face of {MUR}, eager and impatient, sweat on his curled hair"),
 "p_n_close": ("B", "close", ["napoleon"], False, f"close on the face of {NAP}, pale and controlled, grey eyes narrowed, lips tight"),
 "p_kerim_close": ("B", "close", ["kerim"], False, f"close on the face of {KER}, listening hard, a flicker of worry in his quick eyes"),
 "p_guns_up": ("C", "insert", [], True, "French artillerymen hauling a long bronze gun up a wet slope with ropes, wheels slipping in the mud"),
 "p_herd": ("C", "insert", [], True, "the French herd of spare horses behind the column, steaming in the cold, a few lifting their heads toward the ridge"),
 "p_ridge_empty": ("A", "wide", [], True, "the same far ridge now completely empty, grass bending in the wind, not a hoofprint"),
 "p_guns_point": ("C", "insert", [], True, "French guns pointed at an empty ridge while a cloud of cavalry dust drifts away over the crest"),
 # S05
 "p_murat_gallop": ("A", "wide", ["murat"], False, f"{MUR} at the head of a huge cavalry charge streaming over a ridge at dawn, sabres out, thundering hooves"),
 "p_rider_away": ("A", "wide", [], False, "one lone horse archer turning on a distant ridge and riding away, a long cloud of dust behind him"),
 "p_horses_down": ("C", "insert", [], False, "cavalry horses with lathered flanks stumbling in tall grass, one going down on its knees"),
 "p_stragglers": ("B", "medium", [], False, "three bound horse archers sitting in the grass among French troopers, perfectly calm, watching the soldiers' tired horses"),
 # S06 (scene 2)
 "p_wagon_wide": ("A", "wide", ["napoleon", "murat", "kerim"], False, f"at the edge of the wagon park at dusk {NAP} stands by a wagon, {MUR} rides in on a lathered horse on the left and {KER} waits on foot on the right, horses lying between the wheels"),
 "p_horses_lying": ("C", "insert", [], True, "dead and dying horses lying between wagon wheels in the last red light, one still lifting its head"),
 "p_murat_med6": ("B", "medium", ["murat"], False, f"{MUR} on a lathered horse, grinning triumphantly, mud on his gold braid"),
 "p_n_close6": ("B", "close", ["napoleon"], False, f"close on {NAP}, cold and still, watching the marshal's horse breathe"),
 "p_kerim_close6": ("B", "close", ["kerim"], False, f"close on {KER}, choosing his words, eyes on the ground and then up"),
 "p_two_nm6": ("B", "two_shot", ["napoleon", "murat"], False, f"{NAP} and {MUR} face to face between two wagons, the emperor on foot looking up at the marshal in the saddle"),
 "p_murat_close6": ("B", "close", ["murat"], False, f"close on {MUR}, his grin cracking, defensive"),
 "p_spare_string": ("C", "insert", [], True, "a rider on a shaggy horse leading a string of spare horses on a long rope across the steppe"),
 "p_valley_plan": ("A", "wide", [], True, "a long valley with a single mouth between two green slopes, empty in the evening light, a perfect place for guns"),
 # S07
 "p_wagons_line": ("A", "wide", [], False, "a long line of heavy wagons crawling over the grass, wheels cutting black ruts, thin horses leaning into their harness"),
 "p_hungry": ("B", "medium", [], False, "gaunt French soldiers sitting round an empty pot, one splitting the last loaf in half"),
 "p_kerim_alone": ("A", "wide", ["kerim"], False, f"{KER} riding alone into the tall grass toward a distant ridge at dusk, small against the enormous steppe"),
 # S08 (scene 3)
 "p_tent_out": ("A", "wide", [], True, "a felt tent behind a river cut at night, firelight glowing through the felt, riders in fur-rimmed caps standing guard"),
 "p_tent_wide": ("A", "wide", ["genghis", "kerim"], False, f"inside the felt tent {KHN} sits cross-legged by a dung and sagebrush fire on the left, {KER} kneels with bound hands on the right"),
 "p_khan_close": ("B", "close", ["genghis"], False, f"close on the face of {KHN}, firelight on his cheekbones, calm and unreadable"),
 "p_kerim_close8": ("B", "close", ["kerim"], False, f"close on {KER}, sweat on his brow, trying to look unafraid"),
 "p_herder": ("C", "insert", [], False, "a herder in a sheepskin coat in the corner of the felt tent, listening and murmuring translations"),
 "p_khan_med": ("B", "medium", ["genghis"], False, f"{KHN} leaning forward by the fire, one hand open as if weighing something"),
 "p_kerim_med8": ("B", "medium", ["kerim"], False, f"{KER} kneeling, bound hands clenched, chin up, proud and afraid"),
 "p_ash_range": ("C", "insert", [], True, "a finger drawing a long line in the ash beside the fire, then a short line beside it"),
 "p_kerim_leaves": ("A", "wide", ["kerim"], True, f"{KER} riding out of the camp at dawn between two silent riders, behind him the khan beckoning his generals"),
 # S09
 "p_kerim_ride": ("A", "wide", ["kerim"], True, f"{KER} riding hard across the grass toward the French camp in the grey light before sunrise"),
 "p_n_message": ("B", "medium", ["napoleon"], False, f"{NAP} listening to a message in silence, jaw clenched, at the door of his tent in the grey dawn"),
 "p_guns_slope": ("A", "wide", [], False, "the French battle line at dawn: long guns in a row on the high slope, squares of men behind them, the wagons at the back, the valley below"),
 "p_musket_arrow": ("C", "insert", [], False, "a musket ball and an arrow lying side by side on a drumhead, the arrow clearly longer"),
 "p_bow_loft": ("A", "wide", [], True, "a horse archer lofting an arrow in a high arc across a wide valley, the arc ending far beyond a line of muskets"),
 # S10 (central scene)
 "p_slope_wide": ("A", "wide", ["napoleon", "murat", "kerim"], False, f"on the slope at the valley mouth {NAP} stands beside the long guns in battery at the centre, {MUR} sits a wagon horse on the left and {KER} stands at the emperor's elbow on the right, squares behind, the ridge opposite"),
 "p_n_close10": ("B", "close", ["napoleon"], False, f"close on {NAP}, spyglass to his eye, measuring"),
 "p_murat_close10": ("B", "close", ["murat"], False, f"close on {MUR}, wild-eyed and straining, wanting to ride"),
 "p_kerim_close10": ("B", "close", ["kerim"], False, f"close on {KER}, very still, eyes sliding away from the emperor"),
 "p_two_nm10": ("B", "two_shot", ["napoleon", "murat"], False, f"{NAP} and {MUR} shoulder to shoulder on the slope, the marshal pleading, the emperor immovable"),
 "p_n_med10": ("B", "medium", ["napoleon"], False, f"{NAP} standing very straight beside a gun, watching the ridge with the spyglass lowered"),
 "p_gun_fire": ("C", "insert", [], True, "a long bronze gun firing, white smoke rolling out, the round skipping across the grass and dying short"),
 "p_riders_halt": ("A", "wide", [], True, "a perfect line of horsemen halted all at once on the grass exactly on an invisible line, not one horse out of place"),
 "p_riders_flank": ("A", "wide", [], True, "a column of riders galloping round the end of the ridge toward the rear of the French position"),
 "p_wagons_burn": ("A", "wide", [], True, "the wagon line burning, black smoke columns climbing into the dawn sky, flaming arrows arcing in from the grass"),
 "p_squares": ("A", "wide", [], True, "French infantry squares standing tight with bayonets up in the middle of the plain, arrows dropping around them, none breaking"),
 "p_gun_crew": ("C", "insert", [], False, "fifteen men crowded round one long gun, rammers and ropes, no room to turn the heavy carriage"),
 "p_fire_arrows": ("C", "insert", [], True, "a flaming arrow arcing through the smoke toward a canvas wagon cover"),
 "p_kerim_plea": ("B", "medium", ["kerim"], False, f"{KER} on the slope, reaching for the emperor's sleeve, desperate to ride to the wagons"),
 "p_n_cold": ("B", "close", ["napoleon"], False, f"close on {NAP}, his eyes turning slowly toward the Mameluke"),
 # S11
 "p_smoke_wide": ("A", "wide", ["napoleon", "kerim"], False, f"behind the burnt wagon line smoke lifts off black axles; {NAP} stands on the left facing {KER} on the right"),
 "p_n_close11": ("B", "close", ["napoleon"], False, f"close on {NAP}, his face hardening, ash on his coat"),
 "p_kerim_close11": ("B", "close", ["kerim"], False, f"close on {KER}, ashamed and defiant"),
 "p_white_cloth": ("C", "insert", [], True, "a white cloth being tied to the tip of a curved sabre"),
 "p_kerim_rides": ("A", "wide", ["kerim"], True, f"{KER} riding out across the plain with a white cloth on his sabre toward the silent ridge"),
 # S12
 "p_riders_calm": ("A", "wide", [], False, "the horse archers resting calmly on the ridge, not one wounded, horses grazing"),
 "p_kalka": ("A", "wide", [], True, "a river valley with scattered princes' tents and fallen banners, Mongol riders sweeping across the water"),
 "p_empty_sack": ("C", "insert", [], False, "an empty bread sack hanging from a burnt wagon axle in the smoke"),
 "p_fog_ridge": ("A", "wide", [], False, "a ridge with the grey fog lying thick behind it and the khan's riders silhouetted along the top"),
 # S13 (scene 4)
 "p_carpet_wide": ("A", "wide", ["napoleon", "genghis", "kerim"], False, f"on a felt carpet on open grass {NAP} sits on the left, {KHN} sits on the right and {KER} kneels between them, two armies far off on either side"),
 "p_n_close13": ("B", "close", ["napoleon"], False, f"close on {NAP}, unreadable, watching the khan"),
 "p_khan_close13": ("B", "close", ["genghis"], False, f"close on {KHN}, still as a rock, only his eyes moving"),
 "p_kerim_close13": ("B", "close", ["kerim"], False, f"close on {KER}, translating, careful, steady"),
 "p_two_nk": ("B", "two_shot", ["napoleon", "kerim"], False, f"{NAP} leaning to speak and {KER} kneeling to receive the words, the khan a blur at the edge"),
 "p_squares_far": ("A", "wide", [], True, "the French squares standing tight in the far distance, small and unbroken"),
 "p_riders_far": ("A", "wide", [], True, "the riders of the khan filling the far ridge, small and endless"),
 "p_guns_left": ("C", "insert", [], True, "two bronze guns standing alone on the open grass, ropes lying slack beside them"),
 "p_platform": ("C", "insert", [], True, "a great timber platform on a river bank at dusk, banners hanging, no one on it"),
 # S14-S16
 "p_army_leaves": ("A", "wide", [], False, "the army marching in a tight column toward thickening fog at dawn, the wagons gone, the horses thin"),
 "p_moscow_wait": ("B", "medium", ["napoleon"], True, f"{NAP} alone in a burnt Moscow hall beside an empty table, waiting, a clock on the wall"),
 "p_fog_edge": ("A", "wide", ["napoleon"], False, f"{NAP} standing at the very edge of the fog while the last soldier steps into it, grass and arrows at his boots"),
 "p_moscow_road": ("A", "wide", [], False, "the army on the road out of Moscow again, in cold grey October rain, smoke rising behind the domes"),
 "p_channel": ("A", "wide", [], False, "a drifting panorama through fog: a Stone Age fire, Roman columns, a far-future city, all drawn in the one hand-inked style"),
}

PICS.update({
 "p_two_nk4": ("B", "two_shot", ["napoleon", "kerim"], False, f"{NAP} and {KER} face to face on the crest, the emperor questioning, the Mameluke answering with a careful look at the herd behind them"),
 "p_pion": ("B", "medium", [], False, "an old French colonel in a blue coat tapping a ledger on a wagon tailgate, pointing at a village beyond, blunt and weary"),
 "p_ridge_dawn10": ("A", "wide", [], True, "the opposite ridge in the grey dawn with the first long line of horse archers coming into view against the sky"),
 "p_arrow_kept": ("C", "insert", ["napoleon"], False, f"a gloved hand of {NAP} drawing an arrow out of the grass and tucking it inside his coat"),
})
PICS["p_horses_lying"] = ("C", "insert", [], False, PICS["p_horses_lying"][4])
SPEAKERS = {
 "p_rise_wide": {"napoleon": [.5, .4], "murat": [.22, .45], "kerim": [.78, .45]},
 "p_two_nm": {"napoleon": [.35, .4], "murat": [.68, .4]},
 "p_two_nm6": {"napoleon": [.35, .4], "murat": [.68, .35]},
 "p_two_nm10": {"napoleon": [.35, .4], "murat": [.68, .4]},
 "p_two_nk4": {"napoleon": [.3, .4], "kerim": [.7, .4]},
 "p_wagon_wide": {"napoleon": [.5, .4], "murat": [.2, .4], "kerim": [.8, .45]},
 "p_tent_wide": {"genghis": [.25, .45], "kerim": [.75, .5]},
 "p_slope_wide": {"napoleon": [.5, .4], "murat": [.2, .4], "kerim": [.75, .42]},
 "p_smoke_wide": {"napoleon": [.25, .4], "kerim": [.75, .4]},
 "p_carpet_wide": {"napoleon": [.2, .45], "genghis": [.8, .45], "kerim": [.5, .5]},
 "p_two_nk": {"napoleon": [.3, .4], "kerim": [.7, .45]},
}

PICS["p_kerim_med6"] = ("B", "medium", ["kerim"], False, f"{KER} describing what he saw, one hand showing a short string of spare horses in the air, the wagon park dusk behind him")
PICS["p_mk_med4"] = ("B", "two_shot", ["murat", "kerim"], False, f"{MUR} sits his tall horse in front, straining at the reins, while {KER} stands behind him holding the emperor's second mount, both watching the far ridge")
SPEAKERS["p_mk_med4"] = {"murat": [.35, .35], "kerim": [.7, .45]}
