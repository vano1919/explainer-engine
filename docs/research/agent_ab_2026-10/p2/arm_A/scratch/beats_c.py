from helper import *
set_beats("S07", {
 0: [PR("the wagons", "a line of heavy wagons", "the wagons that the guns cannot fix", asset="icon:truck-delivery")],
 1: [T("built for roads", "BUILT FOR ROADS", [0.5, 0.2], "the wagons were built for roads")],
 2: [LB("Colonel Pion", "COLONEL PION", [0.3, 0.3], "names the colonel who put it bluntly"),
     T("live by the sword", "LIVE BY THE SWORD", [0.5, 0.2], "his blunt rule for how the army eats")],
 3: [SY("no villages", "cross", [0.8, 0.3], "the steppe has no villages")],
 4: [SY("eat the ground", "question", [0.85, 0.2], "an army that cannot eat the ground: the open question")],
 5: [CH("seventh day", "counter", [7], "C-93", "the seventh day counted up", unit="days"),
     SY("doesn't come back", "cross", [0.85, 0.25], "Kerim doesn't come back")],
})
set_beats("S08", {
 0: [PR("A felt tent", "a felt tent with a dung fire", "the khan's felt tent and its fire"),
     LB("Genghis Khan", "GENGHIS KHAN", [0.55, 0.3], "names the silent man by the fire")],
 1: [PR("a Mameluke's sabre", "a Mameluke's curved sabre", "the sabre that marks him as a Mameluke"),
     LB("Kerim", "KERIM", [0.4, 0.3], "names the captured man")],
 2: [T("Kipchak Turkic", "KIPCHAK", [0.5, 0.2], "the shared family of both tongues"),
     SY("the words cross", "equals", [0.85, 0.25], "the two tongues are cousins: an equals sign")],
 6: [EX("Yes", "genghis", "deadpan", "the khan's face does not move at the yes")],
 7: [EX("I kept him", "kerim", "surprised", "Kerim did not expect the khan to keep a man who shot at him")],
 14: [EX("nine hundred metres", "genghis", "curious", "the khan takes the number in")],
 16: [EX("Six hundred", "kerim", "worried", "Kerim hears himself give away six hundred, the second number")],
 19: [EX("see his guns", "kerim", "worried", "Kerim senses what the khan wants with his guns")],
 22: [LB("his generals", "HIS GENERALS", [0.5, 0.3], "names the men the khan sends for")],
})
set_beats("S09", {
 0: [LB("French lines", "FRENCH LINES", [0.3, 0.3], "names where Kerim arrives")],
 1: [T("see his guns", "SEE HIS GUNS", [0.5, 0.2], "the khan's message in three words")],
 2: [LB("the valley", "THE VALLEY", [0.5, 0.3], "names the valley he chose")],
 3: [LB("The long guns", "GUNS", [0.25, 0.25], "marks where the long guns go"),
     LB("The squares", "SQUARES", [0.5, 0.45], "marks the squares behind them"),
     LB("the wagons", "WAGONS", [0.75, 0.65], "marks the wagons at the back")],
 4: [CH("ninety metres", "counter", [90], "C-06", "the musket's reach", unit="m")],
 5: [CH("four hundred metres", "bars", [90, 400], "C-09", "a bow outreaches a musket", labels=["MUSKET", "BOW"])],
 6: [HL("the riders begin to gather", [0.75, 0.2], "rings the riders gathering on the ridge",
        cue=("rise", "build", "the riders gather: anticipation before the central scene"))],
})
