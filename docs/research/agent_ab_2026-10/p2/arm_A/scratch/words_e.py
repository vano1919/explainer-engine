from helper import *
# S04 (+ conflict, the horse thread)
ins("S04", "Then where is it?", [
 ("murat", "napoleon", "press", "A ridge is a ridge, sire. Cavalry takes ridges."),
 ("napoleon", "murat", "deflect", "Cavalry takes a ridge and finds nothing on it. I want the army behind it."),
])
ins("S04", "Whose horses are those", [
 ("napoleon", "kerim", "press", "Whose? Ours, or his?"),
 ("kerim", "napoleon", "concede", "Ours, sir. He was looking at the herd behind us."),
])
ins("S04", "You will not move.", [
 ("murat", "napoleon", "press", "Sire, I beg you. Not for glory. For the men sitting here with nothing to hit."),
 ("napoleon", "murat", "deflect", "Your glory is the only thing in this army that has never run short."),
 ("murat", "napoleon", "banter", "Then spend it, sire!"),
])
# S06
ins("S06", "Guns! They've nothing", [
 ("napoleon", "murat", "press", "A week. With what horses?"),
 ("murat", "napoleon", "deflect", "With theirs! We take their horses and they walk."),
 ("napoleon", "murat", "press", "How many horses did eleven men cost you?"),
 ("murat", "napoleon", "deflect", "Nobody counts horses in a charge, sire.", ["C-13"]),
])
ins("S06", "Spare horses, sir.", [
 ("napoleon", "kerim", "press", "And in six days, did they ever light a fire?"),
 ("kerim", "napoleon", "concede", "Not one, sir. Not one fire in six days.", ["C-93"]),
])
# S08
ins("S08", "Where did you learn", [])  # placeholder keeps order checks simple
ins("S08", "Am I meant to thank you?", [
 ("genghis", "kerim", "press", "Your emperor sent you ahead alone. Is he afraid, or only careless?"),
 ("kerim", "genghis", "deflect", "Neither, Khan. He's waiting for you to come to his guns."),
 ("genghis", "kerim", "deflect", "Everyone waits for me to come to something."),
])
ins("S08", "A bull is not slow", [
 ("genghis", "kerim", "press", "My riders say the tubes are loud and cannot hit what runs."),
])
repl("S08", "Your arrows fall short, Khan.", ("kerim", "genghis", "reveal", "Cannot hit what runs? Your arrows fall short. The long gun reaches nine hundred metres.", ["C-05"]))
ins("S08", "Six hundred. Then", [
 ("genghis", "kerim", "press", "You are generous with your emperor's secrets."),
 ("kerim", "genghis", "deflect", "You asked about the guns."),
 ("genghis", "kerim", "deflect", "I asked whether they were slow."),
])
