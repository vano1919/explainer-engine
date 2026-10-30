from edit_rows import ROWS as R0
import copy
ROWS = copy.deepcopy(R0)

def drop(sid, pred):
    ROWS[sid] = [r for r in ROWS[sid] if not pred(r)]
def find(sid, line, sub=None):
    return next(r for r in ROWS[sid] if r[0] == line and r[1] == sub)
def nodiss(sid, line, sub=None):
    r = find(sid, line, sub); r[4].pop("tr", None); r[4].pop("cut", None)

# dissolves only at a period change (automatic), a scene/place change at a segment start; never inside a segment
nodiss("S01", 2); nodiss("S03", 0); nodiss("S03", 5); nodiss("S04", 0); nodiss("S12", 2); nodiss("S14", 2)
nodiss("S15", 2, "Then the fog closes")
find("S01", 2)[4]["pu"] = "the impossible arrival on the steppe (the fog crossing is carried by its sound)"

# S03: fewer, longer shots
drop("S03", lambda r: r[0] in (3, 7) and r[1] is None)
# S04
drop("S04", lambda r: r[0] in (14, 25, 35) and r[1] is None)
drop("S04", lambda r: r[0] == 17)
ROWS["S04"].append((14, None, "p_kerim_med", "P", {"pu": "the shout was in his grandfather's tongue"}))
r19 = find("S04", 19); ROWS["S04"][ROWS["S04"].index(r19)] = (19, None, "p_two_nk4", "P", {"pu": "his tongue lives everywhere; the rider asked about the horses"})
drop("S04", lambda r: r[0] == 20 and r[1] is None)
ROWS["S04"].append((35, "Napoleon's guns stay where", "p_guns_point", "P", {"pu": "the guns stay pointed at nothing"}))
# S06
for l in (14, 15, 18, 20, 21, 23, 24, 29, 31):
    drop("S06", lambda r, l=l: r[0] == l)
ROWS["S06"] += [
 (14, None, "p_kerim_close6", "P", {"pu": "Napoleon turns to Kerim for the truth"}),
 (17, None, "p_kerim_med6", "P", {"pu": "spare horses on a string and not one fire"}),
 (18, None, "p_n_close6", "P", {"pu": "did they ever light a fire"}),
 (20, None, "p_murat_close6", "L", {"pu": "Murat calls it tricks, Kerim says he ran fresh"}),
 (23, None, "p_n_close6", "L", {"pu": "why would a man run for six days"}),
 (24, None, "p_kerim_close6", "P", {"pu": "so that you follow him to wherever he chose"}),
 (29, None, "p_two_nm6", "P", {"pu": "the remounts go to the guns"}),
 (30, None, "p_n_close6", "H", {"pu": "the emperor holds his decision under the narrator's line"}),
 (31, "Then the quartermasters", "p_wagon_wide", "L", {"pu": "the count is bad"}),
]
ROWS["S06"].sort(key=lambda r: (r[0], 1 if r[1] else 0))
# S07
drop("S07", lambda r: r[2] == "p_pion")
# S08
drop("S08", lambda r: r[0] in (12, 25, 27))
ROWS["S08"] += [
 (25, None, "p_khan_med", "P", {"pu": "tell him the khan would like to see his guns"}),
 (27, None, "p_kerim_close8", "P", {"pu": "and if he says no"}),
]
ROWS["S08"].sort(key=lambda r: (r[0], 1 if r[1] else 0))
# S09
drop("S09", lambda r: r[0] == 2)
ROWS["S09"][0][4]["pu"] = "Kerim brings the message"
find("S09", 0, "The emperor hears the khan's")[4]["reveal"] = "the emperor receives the message in silence"
# S10
drop("S10", lambda r: r[0] == 1)
drop("S10", lambda r: r[0] in (23, 25, 49, 51))
ROWS["S10"][0][4]["pu"] = "the master: who stands where at the guns, and the riders opposite"
pass
ROWS["S10"] += [
 (23, None, "p_two_nm10", "P", {"pu": "half dies in the first charge, Murat"}),
 (25, None, "p_n_med10", "P", {"pu": "for the moment they come inside nine hundred"}),
 (49, None, "p_n_close10", "P", {"pu": "they wanted my bread: the whole battle in one line"}),
 (50, None, "p_kerim_close10", "P", {"pu": "and they knew exactly where my guns end: Kerim's secret"}),
]
ROWS["S10"] = [r for r in ROWS["S10"] if r[1] != "No square has broken" and r[1] != "Napoleon has one question"]
ROWS["S10"] += [
 (51, "No square has broken", "p_squares", "L", {"pu": "no square broke, the guns fired once"}),
 (51, "Napoleon has one question", "p_n_cold", "P", {"pu": "the one question left"}),
]
ROWS["S10"].sort(key=lambda r: (r[0], 1 if r[1] else 0))
# S13
drop("S13", lambda r: r[0] == 6)
# S15
drop("S15", lambda r: r[0] == 2 and r[1] is None)
ROWS["S15"] = [r for r in ROWS["S15"] if r[2] != "p_arrow_kept"]

# round 2 fixes
drop("S04", lambda r: r[0] == 1)
ROWS["S04"].append((1, None, "p_mk_med4", "H", {"pu": "Murat itching to charge, Kerim holding the second horse"}))
drop("S04", lambda r: r[0] == 32 or (r[0] == 35))
ROWS["S04"] += [
 (32, None, "p_two_nm", "P", {"pu": "the order to find them"}),
 (34, None, "p_n_close", "P", {"pu": "the emperor's mood held under the narrator's conclusion"}),
 (35, "Napoleon's guns stay where", "p_guns_point", "P", {"pu": "the guns stay pointed at nothing"}),
]
drop("S06", lambda r: r[0] == 30 or r[0] == 31)
ROWS["S06"] += [
 (30, None, "p_n_close6", "H", {"pu": "the emperor decides: the remounts go to the guns"}),
 (31, None, "p_murat_close6", "P", {"pu": "Murat speaks to no one"}),
 (31, "Then the quartermasters", "p_wagon_wide", "L", {"pu": "the count is bad"}),
]
drop("S08", lambda r: r[0] == 5)
find("S09", 0, "The emperor hears the khan's")[4]["reveal"] = "Napoleon receives the message in silence"
ROWS["S10"] = [r for r in ROWS["S10"] if r[2] != "p_n_cold"]
drop("S11", lambda r: r[0] == 10 and r[1])
drop("S11", lambda r: r[0] == 10 and r[1] is None)
ROWS["S11"].append((10, None, "p_white_cloth", "P", {"pu": "the white cloth for the parley; Napoleon does not watch"}))
drop("S12", lambda r: r[0] == 3)
ROWS["S12"] += [
 (3, None, "p_n_look", "P", {"pu": "Napoleon wanted an army to break"}),
 (3, "This army found his dinner", "p_empty_sack", "P", {"pu": "the army found his dinner"}),
]

# round 3: HERO-1, S12 rhythm, event kinds per minute (reframes and pop_text)
drop("S04", lambda r: r[0] in (32, 34))
ROWS["S04"] += [
 (32, None, "p_murat_close", "P", {"pu": "the order to find them lands on Murat"}),
 (34, None, "p_two_nm", "L", {"pu": "bring me a battle; Murat is gone over the ridge"}),
]
drop("S08", lambda r: r[0] in (23, 25, 27))
ROWS["S08"] += [
 (23, None, "p_khan_med", "P", {"pu": "go back to your emperor"}),
 (25, None, "p_tent_wide", "P", {"pu": "tell him the khan would like to see his guns"}),
 (27, None, "p_kerim_close8", "P", {"pu": "and if he says no"}),
 (17, None, "p_tent_wide", "P", {"pu": "the khan's riders say the tubes cannot hit what runs"}),
]
drop("S12", lambda r: r[0] in (1, 3))
ROWS["S12"] += [(3, None, "p_empty_sack", "P", {"pu": "the army found his dinner"})]
find("S12", 0)[4]["pu"] = "the khan lost no one; no square broke"
ROWS["S04"] += [(22, None, "p_two_nk4", "P", {"pu": "ours or his: the herd behind them"})]
ROWS["S06"] += [(16, None, "p_kerim_close6", "P", {"pu": "the truth, Kerim"})]
ROWS["S10"] += [(7, None, "p_two_nm10", "P", {"pu": "men at a market are patient"}), (27, None, "p_n_med10", "P", {"pu": "hold the left of the squares"})]
ROWS["S13"] += [(7, None, "p_khan_close13", "P", {"pu": "then you will wait a long time"}), (11, None, "p_kerim_close13", "P", {"pu": "exactly, Khan"})]
def acc(sid, line, at, text, sub=None):
    find(sid, line, sub)[4]["acc"] = [{"kind": "pop_text", "at": at, "text": text, "strength": 0.6}]
acc("S04", 19, "Whose horses are those", "WHOSE HORSES?") if False else None
for _k in ROWS:
    ROWS[_k].sort(key=lambda r: r[0])
acc("S04", 19, "Whose horses are those", "WHOSE HORSES?")
acc("S06", 18, "Not one fire", "NO FIRES")
acc("S08", 15, "Slow to leave", "SLOW?")
acc("S10", 3, "nine hundred metres", "900 METRES")
acc("S10", 33, "The wagons, sire", "THE WAGONS!")
acc("S13", 9, "Exactly as he said it", "EXACTLY?")

# round 4: fewer shots, reframes where the lines are long enough
drop("S10", lambda r: r[0] == 7); drop("S13", lambda r: r[0] in (7, 11))
drop("S06", lambda r: r[0] in (16, 27, 30)); drop("S03", lambda r: r[0] == 1)
drop("S04", lambda r: r[0] == 22)
ROWS["S04"] += [(21, None, "p_two_nk4", "P", {"pu": "ours or his: the herd behind them"})]
ROWS["S06"] += [(15, None, "p_kerim_close6", "P", {"pu": "the truth, Kerim"})]
ROWS["S13"] += [(10, None, "p_kerim_close13", "P", {"pu": "exactly as he said it"})]
find("S04", 19)[4].pop("acc", None)
find("S13", 9)[4].pop("acc", None)
for _k in ROWS:
    ROWS[_k].sort(key=lambda r: r[0])
acc("S04", 21, "Whose horses are those", "WHOSE HORSES?")
acc("S13", 10, "Exactly as he said it", "EXACTLY?")

drop("S08", lambda r: r[0] == 23)
ROWS["S08"] += [(22, None, "p_khan_med", "P", {"pu": "go back to your emperor"})]
for _k in ROWS:
    ROWS[_k].sort(key=lambda r: r[0])
