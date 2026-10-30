from helper import *
set_beats("S01", {
 0: [HL("An arrow", [0.52, 0.78], "rings the arrow standing in the mud"),
     LB("Napoleon's boots", "NAPOLEON", [0.5, 0.3], "names whose boots stand by the arrow")],
 1: [SY("A minute ago", "clock", [0.85, 0.2], "a minute ago: the time that just jumped"),
     T("burning Moscow", "MOSCOW, OCTOBER 1812", [0.5, 0.2], "shows where and when the army marched")],
 2: [T("the year is 1223", "1223", [0.5, 0.2], "the year the fog dropped them into",
       cue=("chime", "reveal", "the year lands on the turn of the hook"))],
})
set_beats("S02", {
 0: [T("single big battle", "ONE BIG BATTLE", [0.5, 0.2], "the one thing he needs from an enemy")],
 1: [AC("run away first", "punch", 0.5, "the joke lands: the enemy runs first")],
 2: [SY("nobody will come", "question", [0.85, 0.2], "nobody will come: the open question")],
})
set_beats("S03", {
 0: [LB("Moscow", "MOSCOW", [0.3, 0.3], "names the city on the map"),
     SY("refused to talk", "cross", [0.85, 0.25], "the tsar refused to talk: a cross")],
 1: [CH("Five weeks", "counter", [5], "C-12", "five weeks in Moscow counted up", unit="weeks")],
 2: [CH("Four hundred and fifty thousand", "counter", [450000], "C-01", "the size of the army at the Neman", unit="men")],
 3: [CH("a hundred thousand", "bars", [450000, 100000], "C-02", "the army shrinks from the Neman to Moscow", labels=["NEMAN", "MOSCOW"])],
 4: [PR("heavy wagons", "the heavy supply wagons that carry the bread", "the wagons that carry the army's bread", asset="icon:truck-delivery")],
 5: [SY("no road", "cross", [0.8, 0.3], "no road and no villages on the steppe")],
 6: [LB("Genghis Khan", "GENGHIS KHAN", [0.5, 0.3], "names the khan on the steppe",
        cue=("thud", "reveal", "the khan enters the story"))],
 7: [CH("ten thousand", "counter", [10000], "C-20", "the size of one tumen", unit="riders")],
})
