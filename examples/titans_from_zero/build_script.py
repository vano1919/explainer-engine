"""Builds the story layer (writers' room stages 1-2) of 'Titans from Zero' as production_script/3, plus a readable
screenplay. Run: python3 build_script.py  (writes production_script.json and script_v3.md next to this file)."""
import json
from pathlib import Path

HERE = Path(__file__).parent

N = None  # narrator


def L(text, who=None, to=None, intent=None, claims=None):
    d = {"text": text}
    if who:
        d["speaker"] = who
        d["to"] = to
        if intent:
            d["intent"] = intent
    if claims:
        d["claims"] = claims
    return d


cast = {
    "musk": {"names": ["Elon Musk", "Musk"], "card": "Elon Musk as our caricature: tall, broad shoulders, short dark hair, "
             "tired eyes, black T-shirt, grease on his hands", "props": ["soldering iron", "rebuilt scooter"]},
    "belfort": {"names": ["Jordan Belfort", "Belfort"], "card": "Jordan Belfort as our caricature: compact, slicked hair, wide "
                "grin, a sharp suit that has seen better days", "props": ["phone with no contacts"]},
    "oleary": {"names": ["Kevin O'Leary", "O'Leary"], "card": "Kevin O'Leary as our caricature: bald, round glasses, dark suit, "
               "a calm half-smile", "props": ["stack of white envelopes", "briefcase"]},
    "trump": {"names": ["Donald Trump", "Trump"], "card": "Donald Trump as our caricature: swept blond hair, long red tie, "
              "navy suit, a phone held at arm's length", "props": ["phone on a selfie stick"]},
    "kiyosaki": {"names": ["Robert Kiyosaki", "Kiyosaki"], "card": "Robert Kiyosaki as our caricature: grey hair, tanned, "
                 "open-collar shirt, a pointing finger", "props": ["napkin with a drawn deal", "old Toyota"]},
    "cuban": {"names": ["Mark Cuban", "Cuban"], "card": "Mark Cuban as our caricature: dark hair, T-shirt and jeans, arms crossed, "
              "a warehouse office with no chairs", "props": ["clipboard"]},
    "cardone": {"names": ["Grant Cardone", "Cardone"], "card": "Grant Cardone as our caricature: bald, trim beard, tight suit, "
                "a phone pressed to his ear", "props": ["call list"]},
    "hormozi": {"names": ["Alex Hormozi", "Hormozi"], "card": "Alex Hormozi as our caricature: very muscular, shaved head, "
                "beard, a tight black T-shirt", "props": ["gym clipboard"]},
    "zuckerberg": {"names": ["Mark Zuckerberg", "Zuckerberg"], "card": "Mark Zuckerberg as our caricature: short curly hair, "
                   "grey T-shirt, a laptop in a public library", "props": ["laptop"]},
    "bezos": {"names": ["Jeff Bezos", "Bezos"], "card": "Jeff Bezos as our caricature: bald, bright smile, a quilted vest, "
              "reading a report", "props": ["thick fire report"]},
    "vance": {"names": ["Vance"], "card": "Vance, an invented buyer of failing companies: grey suit, grey tie, grey smile",
              "props": ["business card"]},
}

segments = []


def seg(sid, beat, lines, drama, scene=None, period=None):
    s = {"id": sid, "beat": beat, "light_beat": len(segments) + 1, "lines": lines, "shots": [], "drama": drama}
    if scene:
        s["scene"] = scene
    if period:
        s["period"] = period
    segments.append(s)


seg("S01", "the bench", [
    L("Monday, nine in the morning. A courthouse hallway in New York, and one long wooden bench."),
    L("Ten men sit on it, shoulder to shoulder, and none of them looks at the others."),
    L("Donald Trump fixes his tie in the black screen of his phone. Robert Kiyosaki is telling the guard that debt is a gift."),
    L("On Friday they owned towers, rockets, studios and stores. By lunch, a clerk will turn all of it into paperwork."),
    L("But nobody will lend them a dollar after today. Not a bank, not a friend, not the man beside them."),
    L("They walk out with one thing: whatever is inside their heads."),
    L("You'd think that's enough to start again. Five years will show if it was ever skill."),
    L("And the best deal of those five years is about to be made on this bench, for forty dollars."),
], {"function": "cold_open", "turn": "start", "stakes": "ten fortunes and the proof of who earned them",
    "shift": "rich -> nothing", "need": "curiosity", "opens": ["L01", "L02"], "claim_share": "invented"}, period="day0")

seg("S02", "forty dollars", [
    L("At the far end, Kevin O'Leary reads the others one by one, the way a man reads price tags."),
    L("Then he slides along the bench to Elon Musk."),
    L("You can still build things?", "oleary", "musk", "question"),
    L("I can build anything. That isn't the problem.", "musk", "oleary", "deflect"),
    L("So what is?", "oleary", "musk", "press"),
    L("Nobody pays for the parts before the thing exists.", "musk", "oleary", "reveal"),
    L("Then I will. Forty dollars.", "oleary", "musk", "press"),
    L("Forty dollars buys one wheel.", "musk", "oleary", "deflect"),
    L("And ten percent of everything you ever build. Forever.", "oleary", "musk", "reveal"),
    L("Ten percent for forty? I've sold air for more.", "trump", "room", "banter"),
    L("Then sell me some. I've got an envelope for you too.", "oleary", "trump", "press"),
    L("Why would I sign that?", "musk", "oleary", "question"),
    L("Because forty is more than anyone else in this building is offering.", "oleary", "musk", "decide"),
    L("Musk signs. O'Leary moves one seat along and holds out the next envelope to Jordan Belfort."),
    L("Forever is a long word in a contract.", "belfort", "oleary", "deflect"),
    L("It's a short one in a bankruptcy.", "oleary", "belfort", "press"),
    L("Belfort reads it to the last line, folds it, and hands it back. O'Leary stands, a thick stack of white envelopes under his arm."),
], {"function": "inciting", "turn": "therefore", "stakes": "Musk sells a piece of his whole future for one wheel",
    "shift": "free -> owned", "need": "surprise", "claim_share": "invented", "opens": ["L03"]},
    scene={"place": "the bankruptcy court hallway, the long bench", "time": "Monday morning", "present": ["oleary", "musk", "trump", "belfort"],
           "why_now": "the clerk has just taken their fortunes; nobody will lend them again",
           "pov": "musk", "want": "money for parts without giving away control",
           "obstacle_want": "a slice of everything Musk will ever build", "value": "control",
           "open_charge": "+", "close_charge": "-", "turn": "Musk signs away ten percent of his future for one wheel",
           "exit": "succeed_complication", "surface_topic": "forty dollars", "real_subject": "who owns the next five years",
           "mode": "asymmetric"}, period="day0")

seg("S03", "the street", [
    L("By noon the ten are back on the street, and the city teaches them its first lesson."),
    L("Grant Cardone asks a bank for a small loan. The banker types his name, reads the screen, and slides the form back."),
    L("Robert Kiyosaki asks for a credit card. Same screen. Same slide."),
    L("Donald Trump taps his card at a coffee cart, and the machine beeps twice."),
    L("Here's what you learn fast on that street. A loan was only ever a stranger's trust with interest on top. And nobody trusts them for a cent."),
    L("So the only money they can touch is money they make today, with their hands or with their mouths."),
    L("Musk has forty dollars and a parts list. Jordan Belfort has a phone with no numbers in it."),
], {"function": "setup", "turn": "but", "stakes": "without credit, every plan must pay on the first day",
    "shift": "hopeful -> shut out", "need": "stakes", "claim_share": "reasoned", "closes": ["L03"], "opens": ["L04"]},
    period="day1")

seg("S04", "the parking lot", [
    L("A week later, a supermarket parking lot. Musk has built one good scooter out of three broken ones."),
    L("For six hours he has explained its battery to everyone who walks by. Nobody stops."),
    L("Belfort watches from the curb with a hot dog. Then he takes the handlebars without asking."),
    L("He never mentions the battery. He lets a delivery rider take one free lap of the lot, then names three times Musk's price."),
    L("The rider pays cash."),
    L("You were selling a battery. I sold him an hour of his evening.", "belfort", "musk", "reveal"),
    L("It's the same scooter.", "musk", "belfort", "deflect"),
    L("Not to him. He rode it before he paid.", "belfort", "musk", "press"),
    L("So you gave it away first.", "musk", "belfort", "question"),
    L("Give a little first. People hate owing you.", "belfort", "musk", "reveal"),
    L("What do you want?", "musk", "belfort", "question"),
    L("Half. You build, I sell.", "belfort", "musk", "press"),
    L("Ten percent already belongs to a man with envelopes.", "musk", "belfort", "concede"),
    L("Then forty-five each. I won't even ask.", "belfort", "musk", "concede"),
    L("One rule. You never promise what I haven't built.", "musk", "belfort", "press"),
    L("Me? Never.", "belfort", "musk", "deflect"),
    L("They shake hands. Neither of them lets go first."),
], {"function": "escalation", "turn": "therefore", "stakes": "Musk's skill is worth nothing until somebody pays for it",
    "shift": "alone -> partners", "need": "competence", "claim_share": "reasoned", "opens": ["L05"]},
    scene={"place": "a supermarket parking lot, late afternoon", "time": "a week after the bench", "present": ["musk", "belfort"],
           "why_now": "Belfort has just sold in thirty seconds what Musk could not sell in six hours",
           "pov": "musk", "want": "a seller who never lies about his machines",
           "obstacle_want": "half the business and the freedom to sell his own way", "value": "trust",
           "open_charge": "-", "close_charge": "+", "turn": "the free lap sells the scooter and Musk has to take a partner",
           "exit": "succeed_complication", "surface_topic": "the price of a scooter", "real_subject": "whether a liar can be trusted",
           "mode": "balanced"}, period="week1")

seg("S05", "the motel", [
    L("Across the river, a motel by the highway rents rooms by the week. Two men split the cheapest one."),
    L("Debt is how the rich get richer. Write that down.", "kiyosaki", "trump", "press"),
    L("Fantastic. Lend me some.", "trump", "kiyosaki", "banter"),
    L("I don't have any.", "kiyosaki", "trump", "concede"),
    L("Then you don't own the thing you're selling.", "trump", "kiyosaki", "reveal"),
    L("Banks forget. In a year they'll beg to lend us.", "kiyosaki", "trump", "deflect"),
    L("My companies went to bankruptcy court six times. The banks never came back first.", "trump", "kiyosaki", "reveal",
      ["C-03"]),
    L("So who did?", "kiyosaki", "trump", "question"),
    L("The cameras.", "trump", "kiyosaki", "reveal"),
    L("Cameras don't pay rent.", "kiyosaki", "trump", "deflect"),
    L("Watch.", "trump", "kiyosaki", "decide"),
    L("Trump props his phone on a plastic chair by the empty pool and goes live."),
    L("Eleven strangers watch him eat a vending machine sandwich with a knife and fork, like a state dinner."),
    L("By midnight, eleven is four thousand. Kiyosaki calls the bank again and gets the voicemail."),
], {"function": "escalation", "turn": "but", "stakes": "two men whose money always came from others now have no others",
    "shift": "stuck -> watched", "need": "humour", "claim_share": "fact", "opens": ["L06"]},
    scene={"place": "a cheap highway motel room, then the empty pool", "time": "the first week", "present": ["kiyosaki", "trump"],
           "why_now": "the motel wants the week's rent tomorrow",
           "pov": "kiyosaki", "want": "a lender who believes in his plan",
           "obstacle_want": "an audience, not a lender", "value": "hope",
           "open_charge": "-", "close_charge": "+", "turn": "Trump stops asking for money and starts asking for attention",
           "exit": "fail_new_goal", "surface_topic": "debt", "real_subject": "whose skill still works without a bank",
           "mode": "comic"}, period="day1")

seg("S06", "six months", [
    L("Six months later, the garage behind the motel smells of solder."),
    L("Musk sleeps on a folding cot beside the workbench and rebuilds thirty scooters a month. Every one leaves with Belfort."),
    L("Belfort never says lithium. If you deliver food for a living, he sells you one more delivery an hour."),
    L("Across town, Alex Hormozi walks into dying gyms and offers to fill them. He gets paid only from new members, cash first."),
    L("Mark Zuckerberg sits in a public library writing code that finds broken shop websites. Then he fixes them for a fee."),
    L("Mark Cuban rents one bicycle to a kid who delivers lunch. Then two bicycles. Then twenty."),
    L("Jeff Bezos sells used books off a folding table and writes down every title that sells twice."),
    L("But Grant Cardone, making a hundred calls a day, gets a hundred hang-ups."),
    L("His plan pools other people's money into a building. And the one thing his name can't raise anymore is their trust."),
], {"function": "escalation", "turn": "therefore", "stakes": "the skills that need trust stall while the others earn",
    "shift": "even -> split", "need": "competence", "claim_share": "reasoned", "closes": ["L04"], "opens": ["L07"]},
    period="month6")

seg("S07", "the live show", [
    L("By month nine, a hundred thousand people tune in every night to watch Trump eat cereal from a crystal glass."),
    L("One night, Kiyosaki steps into the frame."),
    L("Mind if I teach them something useful?", "kiyosaki", "trump", "question"),
    L("Two minutes. They come for me, not homework.", "trump", "kiyosaki", "press"),
    L("Lesson one. Your house is not an asset.", "kiyosaki", "room", "reveal"),
    L("You're losing them. Nine hundred gone. Two thousand.", "trump", "kiyosaki", "press"),
    L("They need to hear this.", "kiyosaki", "trump", "deflect"),
    L("They need to hear me.", "trump", "kiyosaki", "decide"),
    L("Trump turns the phone. Kiyosaki is out of the picture, and the count climbs back in seconds."),
], {"function": "reversal", "turn": "but", "stakes": "Kiyosaki loses the one stage he still has",
    "shift": "partners -> rivals", "need": "humour", "claim_share": "invented", "closes": ["L06"], "opens": ["L08"]},
    scene={"place": "the motel pool at night, on a live video", "time": "month nine", "present": ["kiyosaki", "trump"],
           "why_now": "Trump's audience has grown past anything Kiyosaki can reach alone",
           "pov": "kiyosaki", "want": "the audience for his lesson",
           "obstacle_want": "keep every viewer on himself", "value": "attention",
           "open_charge": "+", "close_charge": "-", "turn": "the count falls while Kiyosaki teaches and Trump takes the phone back",
           "exit": "fail_new_goal", "surface_topic": "a lesson about houses", "real_subject": "who the crowd actually came for",
           "mode": "comic"}, period="month9")

seg("S08", "five hundred", [
    L("Year one. Mark Cuban runs two hundred delivery riders out of a warehouse office with no chairs."),
    L("He has heard about the scooters that never break down."),
    L("How many can you make by Christmas?", "cuban", "musk", "question"),
    L("Fifty. Fifty good ones.", "musk", "cuban", "concede"),
    L("Five hundred.", "belfort", "cuban", "press"),
    L("We have parts for fifty.", "musk", "belfort", "press"),
    L("He's modest. It's a condition.", "belfort", "cuban", "deflect"),
    L("Five hundred by the twentieth of December, or you never walk in here again.", "cuban", "belfort", "press"),
    L("Can you?", "cuban", "musk", "question"),
    L("Yes.", "musk", "cuban", "concede"),
    L("Cuban signs. It is the biggest order either of them has seen in a year."),
], {"function": "midpoint", "turn": "therefore", "stakes": "the order that saves them leaves no room for a single mistake",
    "shift": "safe -> exposed", "need": "stakes", "claim_share": "invented", "closes": ["L05"], "opens": ["L09"]},
    scene={"place": "Cuban's warehouse office, no chairs", "time": "year one, autumn", "present": ["cuban", "musk", "belfort"],
           "why_now": "Cuban needs scooters before the holiday rush",
           "pov": "musk", "want": "an order he can build without cutting corners",
           "obstacle_want": "the biggest order Cuban will sign today", "value": "safety",
           "open_charge": "+", "close_charge": "-", "turn": "Musk says yes to a number he knows he cannot build safely",
           "exit": "succeed_complication", "surface_topic": "how many scooters by Christmas", "real_subject": "who decides what is true about the machines",
           "mode": "asymmetric"}, period="year1")

seg("S09", "the van", [
    L("In the parking lot, Musk doesn't start the van."),
    L("You promised what I haven't built.", "musk", "belfort", "press"),
    L("You said yes. I heard you.", "belfort", "musk", "deflect"),
    L("Because you'd already said it.", "musk", "belfort", "press"),
    L("That's how big orders work. Promise, then build.", "belfort", "musk", "reveal"),
    L("That's how fires work.", "musk", "belfort", "reveal"),
    L("Belfort laughs. Then he sees Musk isn't laughing, and stops."),
    L("For eleven weeks the garage lights never go off."),
    L("The good cells won't arrive before Christmas, so Musk orders cheap ones from a seller he has never met."),
    L("A heat test takes a day per batch. He skips it on the last two hundred."),
    L("On the nineteenth of December, five hundred scooters roll into Cuban's warehouse. One day early."),
    L("Cuban pays. Belfort frames the receipt. Three hundred cheap cells are left over on a garage shelf."),
], {"function": "escalation", "turn": "therefore", "stakes": "two hundred riders now carry an untested battery",
    "shift": "careful -> rushed", "need": "fear", "claim_share": "reasoned", "opens": ["L10"]},
    scene={"place": "the van in Cuban's parking lot", "time": "minutes after the order", "present": ["musk", "belfort"],
           "why_now": "Musk has just promised five hundred because Belfort already had",
           "pov": "musk", "want": "Belfort to admit the promise was a lie",
           "obstacle_want": "keep the order and the money", "value": "honesty",
           "open_charge": "+", "close_charge": "-", "turn": "Musk names the danger and then builds the five hundred anyway",
           "exit": "succeed_complication", "surface_topic": "who said yes first", "real_subject": "the safety margin they just gave away",
           "mode": "balanced"}, period="year1")

seg("S10", "the limousine", [
    L("Year two. A black car waits outside the motel office."),
    L("A network wants a show. How to Lose a Billion. Season one.", "trump", "kiyosaki", "reveal"),
    L("And what will you own, exactly?", "kiyosaki", "trump", "press"),
    L("The audience. The rest is paperwork.", "trump", "kiyosaki", "deflect"),
    L("An audience isn't an asset.", "kiyosaki", "trump", "press"),
    L("It paid for this car.", "trump", "kiyosaki", "reveal"),
    L("A car is a liability.", "kiyosaki", "trump", "deflect"),
    L("Not when somebody else pays for it.", "trump", "kiyosaki", "reveal"),
    L("There's a seat in the back. Season one needs a man who lost everything.", "trump", "kiyosaki", "press"),
    L("I'm not a lesson. I teach them.", "kiyosaki", "trump", "decide"),
    L("Suit yourself.", "trump", "kiyosaki", "concede"),
    L("The car pulls away. Kiyosaki carries his bag to an old Toyota at the far end of the lot."),
    L("He slept in one once, a long time ago, with Kim. He still knows which seat folds flat.", claims=["C-01"]),
], {"function": "escalation", "turn": "but", "stakes": "Kiyosaki is back where he started forty years ago",
    "shift": "together -> alone", "need": "identity", "claim_share": "fact", "closes": ["L08"]},
    scene={"place": "the motel parking lot, beside a black car", "time": "year two", "present": ["trump", "kiyosaki"],
           "why_now": "the network's car has come for Trump",
           "pov": "kiyosaki", "want": "prove Trump's new money isn't real wealth",
           "obstacle_want": "leave with the car and the contract", "value": "pride",
           "open_charge": "+", "close_charge": "-", "turn": "Trump offers him a seat on the show and Kiyosaki turns it down",
           "exit": "interrupted", "surface_topic": "the car", "real_subject": "whose rule still works",
           "mode": "indirect"}, period="year2")

seg("S11", "the fire", [
    L("Year three. Two in the morning. The garage behind the motel is dark."),
    L("On the shelf, one of the three hundred leftover cells starts to hiss."),
    L("By the time the fire trucks arrive, the garage is a black box without a roof. Nobody is hurt. Everything else is gone."),
    L("Those cells came from the same box as Cuban's.", "musk", "belfort", "reveal"),
    L("Cuban's have run for two years. They're fine.", "belfort", "musk", "deflect"),
    L("Two hundred of them never had the heat test.", "musk", "belfort", "reveal"),
    L("You never told me that.", "belfort", "musk", "press"),
    L("I told you we had parts for fifty.", "musk", "belfort", "press"),
    L("You said it quietly.", "belfort", "musk", "deflect"),
    L("You never listen when it's quiet.", "musk", "belfort", "press"),
    L("If Cuban hears this, we're finished.", "belfort", "musk", "decide"),
    L("If a rider's scooter burns, we're worse than finished.", "musk", "belfort", "reveal"),
    L("Belfort looks at the black shelf for a long time. He doesn't answer."),
    L("Replacing two hundred batteries would cost more than they have left."),
], {"function": "crisis", "turn": "but", "stakes": "two hundred riders, and every dollar they have",
    "shift": "rich -> ruined", "need": "fear", "claim_share": "invented", "closes": ["L09"]},
    scene={"place": "the burnt-out garage at dawn, ash on everything", "time": "year three, the morning after", "present": ["musk", "belfort"],
           "why_now": "the leftover cheap cells just burned the garage down",
           "pov": "belfort", "want": "keep the fire away from Cuban",
           "obstacle_want": "tell Cuban and pull the untested batteries", "value": "safety",
           "open_charge": "+", "close_charge": "-", "turn": "Musk admits the two hundred were never tested",
           "exit": "fail_new_goal", "surface_topic": "the box the cells came from", "real_subject": "who broke the promise first",
           "mode": "balanced"}, period="year3")

seg("S12", "the man in grey", [
    L("Two days later, a man in a grey suit steps over the ashes. His name is Vance, and he buys companies before their bad week."),
    L("I'll buy the company today. You're both rich by Friday.", "vance", "belfort", "press"),
    L("What's the catch?", "belfort", "vance", "question"),
    L("The fire was old wiring in an old garage. Nothing to do with batteries.", "vance", "belfort", "press"),
    L("Two hundred riders are sitting on those batteries.", "musk", "vance", "press"),
    L("And they'll be fine. Probably.", "vance", "musk", "deflect"),
    L("You know how this kind of paper works.", "vance", "belfort", "press"),
    L("I signed paper like that once. I paid for it in a cell.", "belfort", "vance", "reveal", ["C-05"]),
    L("Then you know it works.", "vance", "belfort", "press"),
    L("That's why I'm not signing.", "belfort", "vance", "decide"),
    L("Vance leaves his card on the burnt workbench."),
    L("Belfort picks up his phone and does something he has never done in a sale. He calls the buyer to tell him what's wrong."),
], {"function": "climax", "turn": "therefore", "stakes": "a fortune by Friday against two hundred riders",
    "shift": "tempted -> honest", "need": "justice", "claim_share": "fact", "opens": ["L11"]},
    scene={"place": "the burnt garage, two days later", "time": "year three", "present": ["vance", "belfort", "musk"],
           "why_now": "they are broke, and a buyer has arrived with cash",
           "pov": "belfort", "want": "a way out that does not end in a cell",
           "obstacle_want": "buy the company before the truth gets out", "value": "honesty",
           "open_charge": "-", "close_charge": "+", "turn": "Belfort recognises the paper from his old life and refuses it",
           "exit": "succeed_complication", "surface_topic": "what caused the fire", "real_subject": "whether Belfort has changed",
           "mode": "asymmetric"}, period="year3")

seg("S13", "everything in", [
    L("The next morning, Cuban's warehouse. Two hundred scooters stand in rows."),
    L("Two hundred of your batteries skipped a test. We want them back.", "belfort", "cuban", "reveal"),
    L("Are they bad?", "cuban", "musk", "question"),
    L("Probably not. I don't sell probably.", "musk", "cuban", "reveal"),
    L("Who pays for two hundred new ones?", "cuban", "belfort", "press"),
    L("We do.", "musk", "cuban", "decide"),
    L("With what?", "belfort", "musk", "question"),
    L("With everything. I did it once before, on a Christmas Eve.", "musk", "belfort", "decide", ["C-02"]),
    L("Nobody has ever come in here to give me money back.", "cuban", "belfort", "reveal"),
    L("Belfort opens his mouth to make a pitch. For once, he closes it."),
    L("Fix them. Then bring me next year's number. A real one.", "cuban", "musk", "decide"),
    L("They spend every dollar on two hundred new batteries, and Musk tests each one twice, on camera."),
    L("For three months they eat from the motel vending machine. Belfort calls it the executive menu."),
], {"function": "resolution", "turn": "therefore", "stakes": "they give up all their cash to keep one customer's trust",
    "shift": "broke -> trusted", "need": "belonging", "claim_share": "fact", "closes": ["L10", "L11"]},
    scene={"place": "Cuban's warehouse, between rows of scooters", "time": "year three, the next morning", "present": ["belfort", "cuban", "musk"],
           "why_now": "Belfort called Cuban last night",
           "pov": "belfort", "want": "keep Cuban as a customer after the truth",
           "obstacle_want": "never be lied to by a supplier", "value": "trust",
           "open_charge": "-", "close_charge": "+", "turn": "the recall they pay for wins the next order",
           "exit": "succeed_complication", "surface_topic": "two hundred batteries", "real_subject": "what trust is worth in money",
           "mode": "balanced"}, period="year3")

seg("S14", "year five", [
    L("Year five. Cuban's riders run on five thousand of their batteries, and not one has burned."),
    L("Belfort's whole pitch is one sentence now. Ours burned once. That's why they don't."),
    L("Grant Cardone works their phones. Same calls as year one. Now people pick up, because the name on the box means something."),
    L("Hormozi runs sixty gyms on cash. Zuckerberg sold his little website robot and vanished into a bigger one."),
    L("Trump is filming season four of How to Lose a Billion. Last season he read their fire report on air, page by page."),
    L("He called it the only honest paper in America. Ratings doubled."),
    L("And Kiyosaki is in the motel lobby, explaining to the night clerk why debt is a gift. The clerk has heard it before."),
    L("One viewer read every page after him. Then he walked into their office."),
    L("I read your fire report. All of it.", "bezos", "belfort", "reveal"),
    L("Most buyers ask us to bury it.", "belfort", "bezos", "press"),
    L("That's why I'm offering double what they would.", "bezos", "belfort", "reveal"),
    L("Double.", "musk", "belfort", "aside"),
    L("Make it a partnership, and you can buy lunch.", "belfort", "bezos", "press"),
], {"function": "resolution", "turn": "therefore", "stakes": "five years of choices are priced at last",
    "shift": "survivors -> winners", "need": "competence", "claim_share": "invented", "closes": ["L07"], "opens": ["L12"]},
    scene={"place": "the new factory office, a framed receipt on the wall", "time": "year five", "present": ["bezos", "belfort", "musk"],
           "why_now": "the fire report is public and buyers are calling",
           "pov": "belfort", "want": "a partner, not a buyer",
           "obstacle_want": "own the company that told the truth", "value": "worth",
           "open_charge": "-", "close_charge": "+", "turn": "the report they could have buried doubles their price",
           "exit": "succeed_complication", "surface_topic": "the fire report", "real_subject": "honesty as the asset",
           "mode": "asymmetric"}, period="year5")

seg("S15", "the envelopes", [
    L("Five years after the bench, Musk and Belfort walk into the same courthouse to register the deal."),
    L("The bench is still there. So is Kevin O'Leary."),
    L("Ten percent. Remember?", "oleary", "musk", "press"),
    L("Of a burnt garage?", "musk", "oleary", "deflect"),
    L("Of everything. Fires included. Read the envelope.", "oleary", "musk", "reveal"),
    L("You got lucky with him.", "belfort", "oleary", "banter"),
    L("I didn't pick him.", "oleary", "belfort", "reveal"),
    L("Belfort's grin stays on a second too long."),
    L("He opens his briefcase. Eight signed envelopes. Trump. Kiyosaki. Cardone. Hormozi. Cuban. Bezos. Zuckerberg. Musk."),
    L("Eight?", "belfort", "oleary", "question"),
    L("Nine offered. One man read to the last line and said no.", "oleary", "belfort", "reveal"),
    L("I read contracts.", "belfort", "oleary", "banter"),
    L("Then you went into business with a man who doesn't.", "oleary", "belfort", "reveal"),
    L("Musk looks at the floor. Belfort looks at Musk."),
    L("Most of these paid back my forty. Three of them paid for everything.", "oleary", "musk", "reveal"),
    L("So it was luck.", "musk", "oleary", "press"),
    L("Luck chose the three. I made sure I owned all eight.", "oleary", "musk", "decide"),
], {"function": "twist", "turn": "but", "stakes": "who really won the five years",
    "shift": "winners -> owned", "need": "surprise", "claim_share": "invented", "closes": ["L01", "L12"]},
    scene={"place": "the courthouse hallway, the same bench", "time": "year five", "present": ["oleary", "musk", "belfort"],
           "why_now": "the deal must be registered in this building",
           "pov": "musk", "want": "walk past the bench owing nothing",
           "obstacle_want": "collect ten percent of the best company on the street", "value": "victory",
           "open_charge": "+", "close_charge": "-", "turn": "O'Leary opens the briefcase and every envelope is there",
           "exit": "succeed_complication", "surface_topic": "the envelope", "real_subject": "who really won",
           "mode": "asymmetric"}, period="year5")

seg("S16", "the verdict", [
    L("Ten men walked out of this building with nothing but what they knew."),
    L("The ones whose skill ran on other people's trust waited years for it. Some are still waiting."),
    L("The ones who could build or sell with their own hands were back within months."),
    L("And the one who never built or sold anything spread forty dollars across eight of them."),
    L("Luck decided which envelope paid. Skill decided who was still standing when it did."),
    L("So if you sat on that bench tomorrow, which envelope would be yours?"),
], {"function": "button", "turn": "therefore", "stakes": "the answer to skill or luck",
    "shift": "question -> answer", "need": "identity", "claim_share": "reasoned", "closes": ["L02"]},
    period="year5")

doc = {
    "schema": "production_script/3",
    "episode": {"id": "titans_from_zero", "title": "What If 10 Business Titans Went Broke? Five Years to Prove It Wasn't Luck",
                "fps": 30, "scenario": {"file": "scenario.md", "approved_by": "vano1919 (ვანო)", "approved_at": "2026-10-20", "sha256": "26b9d6eb966430c5e0f13a189dc431601351122e9bdf730f87a542364a68026d"}, "notes": "writers' room stages 1-2 (story, scenes, lines); beats, performance, edit, voices and "
                "Shorts follow on these frozen words after the creator's approval of the script"},
    "voice": {"provider": "elevenlabs", "model": "eleven_v4", "voice_id": None, "name": None,
              "style": "a warm, quick, slightly wry storyteller with a low voice, curious and never solemn", "pace_wpm": [155, 185]},
    "world": {"host": "a caricatured present-day New York: courthouse, highway motel, garages, warehouses"},
    "cast": cast,
    "drama": {
        "premise": "Ten famous business titans go bankrupt on one Monday, lose every lender, and keep only their skills.",
        "question": "Was their money ever skill, or was it luck?",
        "promise": "five years of their comeback, who rises, who stays down, and who quietly wins",
        "needs": ["curiosity", "stakes", "humour", "surprise", "competence", "fear", "justice", "identity", "belonging"],
        "arcs": {
            "musk": {"want": "build machines that never fail", "need": "trust someone to speak for him",
                     "flaw": "says the truth too quietly, then gives in", "change": "says 'probably not' out loud and pays for it"},
            "belfort": {"want": "get rich fast again", "need": "sell only what is real",
                        "flaw": "promises more than exists", "change": "refuses the cover-up and sells the truth"},
            "trump": {"want": "be on top again", "flaw": "needs to be watched", "change": "turns attention into money"},
            "kiyosaki": {"want": "a lender for his plan", "flaw": "keeps his theory when the world changes",
                         "change": "none: turns down the seat out of pride and keeps preaching in the lobby"},
            "oleary": {"want": "the best return on forty dollars", "flaw": "owns without building"},
            "cuban": {"want": "suppliers who never lie", "flaw": "orders more than is safe"},
            "vance": {"want": "buy before the bad news", "flaw": "sells risk to others"},
            "bezos": {"want": "buy the honest company", "flaw": "only buys what he has read"},
        },
        "loops": [
            {"id": "L01", "question": "who makes the best deal of the five years, for forty dollars?"},
            {"id": "L02", "question": "skill or luck?"},
            {"id": "L03", "question": "will Musk regret the envelope?"},
            {"id": "L04", "question": "how do you make money when nobody lends to you?"},
            {"id": "L05", "question": "will Belfort keep his promise not to promise?"},
            {"id": "L06", "question": "can attention pay the rent?"},
            {"id": "L07", "question": "will Cardone ever get a yes?"},
            {"id": "L08", "question": "what happens to Kiyosaki?"},
            {"id": "L09", "question": "can they build five hundred in time?"},
            {"id": "L10", "question": "what will the leftover cells do?"},
            {"id": "L11", "question": "what will Cuban do with the truth?"},
            {"id": "L12", "question": "who really owns the winners?"},
        ],
        "setups": [
            {"id": "P01", "what": "O'Leary's thick stack of white envelopes", "plant": "S02", "payoff": "S15"},
            {"id": "P02", "what": "'Me? Never.' Belfort promises not to promise", "plant": "S04", "payoff": "S08"},
            {"id": "P03", "what": "three hundred leftover cheap cells on the shelf", "plant": "S09", "payoff": "S11"},
            {"id": "P04", "what": "Belfort's framed receipt", "plant": "S09", "payoff": "S14"},
        ],
        "ending": {"kind": "twist", "note": "O'Leary owned a slice of eight of them; the verdict closes skill or luck"},
    },
    "segments": segments,
}

(HERE / "production_script.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

NAMES = {k: v["names"][-1].upper() for k, v in cast.items()}
md = ["# Titans from Zero: full script, words (v3, 2026-10-20)", "",
      f"**Title:** {doc['episode']['title']}", "",
      "NARRATOR lines are in plain text; dialogue is NAME (to whom): line.", ""]
words = 0
for s in segments:
    md.append(f"## {s['id']} {s['beat']} ({s.get('period', '')})")
    if s.get("scene"):
        sc = s["scene"]
        md.append(f"*Scene: {sc['place']}. {', '.join(NAMES[p] for p in sc['present'])}.*")
    md.append("")
    for ln in s["lines"]:
        words += len(ln["text"].split())
        if ln.get("speaker"):
            to = ln["to"]
            to = NAMES.get(to, to)
            md.append(f"- **{NAMES[ln['speaker']]}** ({to}): {ln['text']}")
        else:
            md.append(f"- {ln['text']}")
    md.append("")
md.insert(4, f"**Spoken words:** {words} (about {words / 165:.1f} minutes at the narrator's pace, plus the pauses of the scenes)")
(HERE / "script_v3.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(words, "words")
