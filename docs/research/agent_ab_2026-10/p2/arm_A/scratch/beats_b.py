from helper import *
set_beats("S04", {
 0: [LB("the far ridge", "FAR RIDGE", [0.75, 0.3], "names the ridge Napoleon is watching"),
     PR("a spyglass", "Napoleon's spyglass", "the spyglass in his hand")],
 1: [LB("Murat", "MURAT", [0.25, 0.3], "names the marshal on the horse"),
     LB("Kerim", "KERIM", [0.55, 0.3], "names the Mameluke holding the second mount")],
 2: [HL("A single rider", [0.8, 0.38], "rings the single rider on the far ridge")],
 5: [EX("I want his army", "murat", "doubtful", "Murat doubts the emperor wants only an army")],
 11: [EX("is not an army", "murat", "confused", "Murat cannot follow the logic of not an army")],
 15: [EX("my grandfather's tongue", "napoleon", "curious", "Napoleon leans in at the strange word tongue")],
 19: [EX("Whose horses", "napoleon", "doubtful", "the emperor wonders why a rider asks about horses")],
 22: [EX("The ridge", "napoleon", "surprised", "Napoleon lowers the spyglass at the ridge that is empty"),
       SY("empty", "cross", [0.8, 0.3], "the ridge is empty: a cross where the riders were",
         cue=("fall", "reveal", "the ridge empties: the turn of the scene"))],
 25: [EX("Take your sabres", "murat", "joyful", "Murat lights up as the emperor lets him off the leash")],
 28: [HL("pointed at nothing", [0.4, 0.55], "rings the guns aimed at nothing")],
})
set_beats("S05", {
 0: [CH("six days", "counter", [6], "C-93", "six days of chase counted up", unit="days")],
 1: [PR("a rider", "a lone rider on a ridge", "the rider who shows himself, then withdraws")],
 2: [PR("his horses", "Murat's exhausted horses", "what the chase costs: the horses")],
 3: [SY("caught", "question", [0.85, 0.2], "what exactly was caught: the open question")],
})
set_beats("S06", {
 0: [T("the sixth day", "DAY SIX", [0.5, 0.2], "the sixth day of the chase"),
     LB("the wagon park", "WAGON PARK", [0.3, 0.3], "names the place")],
 1: [HL("horses lie down", [0.45, 0.7], "rings the horses lying between the wheels")],
 3: [EX("Eleven of them", "napoleon", "deadpan", "the emperor counts eleven against the cost")],
 5: [EX("Horses are for riding", "kerim", "sad", "Kerim winces at the marshal's words about horses")],
 13: [EX("Three or four each", "murat", "confused", "Murat hears the number of spare horses")],
 15: [EX("tired horses", "murat", "angry", "Murat flares at tired horses from the Mameluke")],
 18: [EX("To wherever he chose", "napoleon", "worried", "Napoleon sees the trap in wherever he chose")],
 22: [CH("nine hundred metres", "counter", [900], "C-05", "the long guns' reach on screen", unit="m")],
 25: [SY("the count is bad", "arrow_down", [0.85, 0.2], "the supply count is falling")],
})
