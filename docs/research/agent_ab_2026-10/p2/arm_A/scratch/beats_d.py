from helper import *
set_beats("S09", {
 "Kerim rides into": [LB("French lines", "FRENCH LINES", [0.3, 0.3], "names where Kerim arrives")],
 "The khan would like": [T("see his guns", "SEE HIS GUNS", [0.5, 0.2], "the khan's message in three words")],
 "Ahead lies": [LB("the valley", "THE VALLEY", [0.5, 0.3], "names the valley he chose")],
 "The long guns go": [LB("The long guns", "GUNS", [0.25, 0.25], "marks where the long guns go"),
                      LB("the squares", "SQUARES", [0.5, 0.45], "marks the squares behind them"),
                      LB("the wagons", "WAGONS", [0.75, 0.65], "marks the wagons at the back")],
 "A musket": [CH("ninety metres", "counter", [90], "C-06", "the musket's reach", unit="m")],
 "A Mongol bow": [CH("four hundred metres", "bars", [90, 400], "C-09", "a bow outreaches a musket", labels=["MUSKET", "BOW"])],
 "On the ridge above": [HL("the riders begin to gather", [0.75, 0.2], "rings the riders gathering on the ridge",
        cue=("rise", "build", "the riders gather: anticipation before the central scene"))],
})
set_beats("S08", {
 "Cannot hit what runs?": [EX("nine hundred metres", "genghis", "curious", "the khan takes in nine hundred metres")],
 "I asked whether": [EX("whether they were slow", "kerim", "scared", "Kerim sees he was baited with the word slow")],
})
set_beats("S10", {
 "Dawn on the eighth": [T("eighth day", "DAY EIGHT", [0.5, 0.2], "the eighth day on the steppe"),
                        PR("his guns", "the long guns on the slope", "the guns beside which Napoleon stands")],
 "Murat sits a horse": [HL("a horse taken from a wagon team", [0.3, 0.6], "rings the borrowed wagon horse Murat sits")],
 "On the ridge opposite": [HL("the first line of riders", [0.75, 0.25], "rings the first line of riders on the ridge")],
 "I'd rather learn": [EX("a horse that can still stand", "napoleon", "deadpan", "the emperor takes the jab about the horses without a flicker")],
 "Sir. They're coming down.": [EX("coming down", "napoleon", "curious", "Napoleon raises the spyglass at the riders coming down")],
 "Fifty metres short.": [AC("Fifty metres short", "shake", 0.5, "the round lands short of the riders: a shake of impact",
        cue=("thud", "impact", "the round lands short of the riders"))],
 "Look where they stopped.": [EX("where they stopped", "kerim", "worried", "Kerim looks down: he knows where they stopped and why")],
 "On what?": [EX("Half your horses", "murat", "angry", "Murat bristles at the count of his horses")],
 "Sir. Behind us.": [SY("Behind us", "exclaim", [0.85, 0.2], "behind us: the alarm",
        cue=("fall", "reveal", "the smoke over the wagons: the scene turns"))],
 "The smoke, sir.": [HL("The smoke", [0.7, 0.35], "rings the smoke over the wagons")],
 "Fire arrows.": [PR("Fire arrows", "arrows trailing fire", "the fire arrows that burn the wagons", asset="icon:flame")],
 "Fifteen men to a gun": [CH("Fifteen men", "counter", [15], "C-05", "a gun's crew of fifteen", unit="men")],
 "They never wanted my guns.": [EX("my bread", "murat", "surprised", "Murat realises the riders wanted the bread, not the guns")],
 "And they knew exactly": [EX("they knew", "kerim", "scared", "Kerim goes still as the emperor says they knew",
        cue=("chime", "take", "Kerim's scared take as the emperor says they knew"))],
 "By midmorning": [HL("a wall of black smoke", [0.5, 0.4], "rings the wall of smoke where the wagons were"),
                   SY("one question", "question", [0.85, 0.2], "Napoleon has one question left")],
})
set_beats("S11", {
 "Behind the wagon line": [HL("black axles", [0.5, 0.65], "rings the black axles of the burnt wagons")],
 "I did, sir.": [EX("I did", "napoleon", "angry", "Napoleon's face hardens as Kerim admits telling about the guns",
        cue=("thud", "take", "Napoleon's angry take at the confession"))],
 "I am listening now.": [EX("listening now", "kerim", "surprised", "Kerim did not expect to be listened to")],
 "Kerim rides out": [PR("a white cloth", "a white cloth tied to a sabre", "the white cloth that asks for the parley")],
})
set_beats("S12", {
 "So, who won?": [T("lost no one", "KHAN LOST NO ONE", [0.5, 0.2], "the khan lost no one"),
                  SY("half his bread", "arrow_down", [0.85, 0.3], "the emperor's bread cut by half")],
 "No square broke.": [SY("No square broke", "check", [0.8, 0.3], "no square broke: the squares held")],
 "This same spring": [LB("Kalka River", "KALKA RIVER", [0.3, 0.3], "names the river of the other trap"),
                      CH("nine days", "counter", [9], "C-10", "the days of the feigned retreat", unit="days")],
 "Napoleon wanted to find": [AC("found his dinner", "punch", 0.5, "the joke lands on his dinner")],
 "And the fog still lies": [T("khan's leave", "THE KHAN'S LEAVE", [0.5, 0.2], "what Napoleon now needs to reach the fog")],
})
set_beats("S13", {
 "A felt carpet": [LB("A felt carpet", "THE CARPET", [0.5, 0.7], "names the felt carpet of the parley")],
 "Napoleon sits": [LB("Napoleon", "NAPOLEON", [0.2, 0.3], "names the emperor on his side"),
                   LB("Genghis Khan", "GENGHIS KHAN", [0.8, 0.3], "names the khan on his side")],
 "Your bread is smoke.": [EX("Your bread is smoke", "napoleon", "deadpan", "Napoleon takes the hit about the bread without a flicker")],
 "Then you will wait": [EX("a long time", "napoleon", "worried", "Napoleon hears how long the wait will be")],
 "Exactly as he said it?": [EX("Exactly as he said it", "kerim", "determined", "Kerim will translate exactly as he said it")],
 "Good. I keep men": [EX("I keep men", "napoleon", "curious", "Napoleon notes the khan will keep men who tell what was said")],
 "Those princes lie": [EX("lie under", "napoleon", "worried", "Napoleon hears where the princes lie under the platform"),
                       PR("the victory platform", "a victory platform over the fallen princes", "the victory platform the princes lie under")],
 "No. You sent him back.": [EX("You sent him back", "napoleon", "surprised", "Napoleon had not counted that he sent him back as leverage")],
 "Then your guns will be lonely.": [EX("lonely", "napoleon", "amused", "a dry smile crosses Napoleon's face at lonely guns")],
 "Take two guns.": [CH("two guns", "counter", [2], "C-94", "the price of the road home", unit="guns")],
 "Two guns are rolled": [PR("Two guns", "two guns left on the open grass", "the two guns left behind")],
})
set_beats("S14", {
 "So, can Napoleon": [SY("He can", "check", [0.85, 0.2], "he can: the army gets out")],
 "He never gets": [SY("never gets his battle", "cross", [0.8, 0.3], "he never gets his battle"),
                   CH("two guns", "counter", [2], "C-94", "the price paid: two guns", unit="guns")],
 "Remember Moscow?": [CH("five weeks", "counter", [5], "C-12", "the weeks he waited in Moscow", unit="weeks")],
 "The khan talked": [SY("an afternoon", "clock", [0.85, 0.2], "the khan talked in one afternoon")],
 "Maybe that's": [SY("needed nothing", "cross", [0.8, 0.3], "the tsar needed nothing from him"),
                  T("two guns", "TWO GUNS", [0.5, 0.2], "what the khan wanted")],
 "What the khan did": [SY("no Frenchman ever saw", "question", [0.85, 0.2], "no Frenchman ever saw what became of them")],
 "At dawn the fog": [PR("the fog", "the fog sweeping back over the army", "the fog that comes back at dawn",
        cue=("whiff", "transition", "the fog sweeps back over the army"))],
})
set_beats("S15", {
 "The last man steps": [HL("its edge", [0.8, 0.4], "rings the edge of the fog where Napoleon stops")],
 "An arrow stands": [HL("An arrow", [0.52, 0.78], "rings the arrow at his boots, as at the start",
        cue=("pluck", "reveal", "the opening arrow returns with a new meaning"))],
 "He pulls it out": [T("October 1812", "OCTOBER 1812", [0.5, 0.2], "the year the fog gives them back to")],
})
set_beats("S16", {
 "The Stone Age": [LB("The Stone Age", "ON THE CHANNEL", [0.3, 0.3], "a world already on the channel"),
                   LB("Rome and the far future", "COMING", [0.7, 0.3], "worlds that are coming")],
 "Which world": [SY("next", "question", [0.85, 0.2], "which world next: the question"),
                 T("Subscribe", "DON'T MISS ONE", [0.5, 0.7], "why to subscribe: not to miss the next one")],
})
