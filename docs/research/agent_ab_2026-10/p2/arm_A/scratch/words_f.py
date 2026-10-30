from helper import *
repl("S06", "Nobody counts horses", ("murat", "napoleon", "deflect", "Eleven men, sire! Count those, not horses.", ["C-13"]))
# S09 trimmed
set_lines("S09", [
 ("N", "Kerim rides into the French lines before sunrise. The emperor hears the khan's message in silence.", ["C-93"]),
 ("N", "The khan would like to see his guns. Napoleon takes that as an insult, and then as an invitation.", ["C-94"]),
 ("N", "Ahead lies the valley he chose: one mouth, long slopes, firm ground.", ["C-93"]),
 ("N", "The long guns go on the high slope, the squares behind them, the wagons at the back.", ["C-93"]),
 ("N", "A musket is good for ninety metres.", ["C-06"]),
 ("N", "A Mongol bow can loft an arrow nearly four hundred metres.", ["C-09"]),
 ("N", "On the ridge above, the riders begin to gather. Nobody has counted them.", ["C-93"]),
])
# S10: the central scene grows to three escalations
ins("S10", "Look at them. Sitting", [
 ("napoleon", "murat", "deflect", "Men at a market are patient, Murat. Learn from them."),
 ("murat", "napoleon", "deflect", "I'd rather learn from a horse that can still stand, sire."),
])
ins("S10", "Wait.", [
 ("napoleon", "murat", "decide", "Fire one round. Let them see what waits for them."),
 ("murat", "napoleon", "banter", "At nothing, sire? You'll frighten the grass."),
])
repl("S10", "Nine hundred and fifty.", ("napoleon", "room", "aside", "Fifty metres short. And not one of them flinched."))
ins("S10", "Fifty metres short.", [
 ("murat", "napoleon", "banter", "They're polite, sire. They let you finish."),
 ("napoleon", "murat", "reveal", "Look where they stopped. Nine hundred and fifty, to the pace."),
])
ins("S10", "Then send a square", [])
ins("S10", "Then we stand here", [
 ("murat", "napoleon", "press", "Sire, our bread. Our powder. The wounded are in those wagons."),
 ("napoleon", "murat", "deflect", "I know what is in those wagons."),
 ("murat", "napoleon", "press", "Then do something!"),
 ("napoleon", "murat", "decide", "I am. I am holding what I have."),
 ("kerim", "napoleon", "press", "Sir, let me take the Mamelukes to the wagons. Please."),
 ("napoleon", "kerim", "deflect", "Please? You have not asked me for anything in eight days."),
 ("kerim", "napoleon", "concede", "No, sir."),
 ("napoleon", "kerim", "decide", "Stay where I can see you."),
])
repl("S10", "By midmorning", ("N", "By midmorning the wagon line is a wall of black smoke. No square has broken. The guns have fired once, at nothing. Napoleon has one question left.", ["C-93"]))
# S11
ins("S11", "Sir, I spent a night", [])
ins("S11", "I did, sir.", [
 ("napoleon", "kerim", "press", "Why?"),
 ("kerim", "napoleon", "deflect", "Nobody listens to a Mameluke, sir. Until he has something to sell."),
])
repl("S11", "Then go back and tell", ("napoleon", "kerim", "decide", "I am listening now. Go back, and tell them what I want."))
# S13
ins("S13", "Yes. I watched them.", [
 ("genghis", "napoleon", "deflect", "You came for a battle. I have watched you wait for one for eight days."),
 ("napoleon", "genghis", "deflect", "I am still waiting."),
 ("genghis", "napoleon", "deflect", "Then you will wait a long time."),
])
ins("S13", "A tube without a man", [
 ("genghis", "napoleon", "press", "Where I come from, a man who knows a thing is worth ten who own it.", ["C-11"]),
 ("napoleon", "genghis", "deflect", "And where I come from, a man belongs to himself."),
 ("genghis", "napoleon", "banter", "Then your guns will be lonely."),
])
# S15 trimmed
set_lines("S15", [
 ("N", "The last man steps into the fog. Napoleon stops at its edge.", ["C-91"]),
 ("N", "An arrow stands in the grass at his boots, right where the first one stood.", ["C-93"]),
 ("N", "He pulls it out and keeps it. Then the fog closes, and it's October 1812 again.", ["C-12"]),
])
