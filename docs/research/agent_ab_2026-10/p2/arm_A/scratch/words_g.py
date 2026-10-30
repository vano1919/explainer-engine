from helper import *
d = load()
s = next(x for x in d["segments"] if x["id"] == "S10")
s["lines"] = [l for l in s["lines"] if not l["text"].startswith("Sire, our bread. Our powder.")]
save(d)
repl("S10", "Then we stand here", ("murat", "napoleon", "press", "Then we stand here and watch it burn? Our bread, our powder, the wounded?"))
repl("S10", "Why have they stopped?", ("murat", "napoleon", "deflect", "Coincidence, sire."))
report()
