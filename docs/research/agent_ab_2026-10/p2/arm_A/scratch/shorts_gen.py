import json
from helper import T, LB, HL, SY, AC, PR, CH, EX
A = "/home/user/explainer-engine/jobs/ab_agents_2026-10/p2/arm_A/"
d = json.load(open(A + "s05_caster.json"))
def L(text, claims=None, beats=None, **kw):
    x = {"text": text}
    if claims: x["claims"] = claims
    if beats: x["visual_beats"] = beats
    x.update(kw); return x
S1 = {"id": "SH01", "style": "cold_open_cliffhanger", "ending": "cliffhanger", "source_period": "1223",
 "hook": "Where does Napoleon's army go when the fog drops?",
 "lines": [
  L("Where does Napoleon's army go when the fog drops?", ["C-91"], [
    T("Napoleon's army", "NAPOLEON'S ARMY", [0.5, 0.2], "names the army in the fog"),
    SY("the fog", "question", [0.85, 0.25], "the fog is the open question")], tags=["curious"]),
  L("Wait, an arrow stands in the mud between Napoleon's boots.", ["C-93"], [
    HL("an arrow", [0.5, 0.78], "rings the arrow in the mud"),
    LB("Napoleon's boots", "HIS BOOTS", [0.5, 0.9], "the boots beside the arrow")]),
  L("A minute ago, his army was marching out of burning Moscow.", ["C-12"], [
    PR("army", "marching column", "the army marching"),
    T("burning Moscow", "MOSCOW, 1812", [0.5, 0.2], "burning Moscow is the place he left")]),
  L("But now the grass is green.", ["C-93"], [
    SY("green", "exclaim", [0.85, 0.25], "the grass is green and wrong")]),
  L("Nobody speaks. Nobody moves. Something is watching from the ridge.", ["C-93"], [
    T("watching", "WATCHING", [0.5, 0.2], "something is watching"),
    HL("the ridge", [0.6, 0.35], "rings the ridge")]),
  L("The year is 1223, and the riders are Genghis Khan's.", ["C-91", "C-92"], [
    T("1223", "1223", [0.5, 0.2], "the year the fog gives back"),
    HL("Genghis Khan's", [0.5, 0.5], "rings the riders of Genghis Khan")], emphasis=["1223"]),
 ],
 "shots": [
  {"at": "Where does Napoleon's", "picture": "p_n_look", "crop_x": 0.5, "zoom": 1.0},
  {"at": "when the fog drops", "picture": "p_steppe_fog", "crop_x": 0.5, "zoom": 1.0},
  {"at": "Wait, an arrow", "picture": "p_arrow", "crop_x": 0.5, "zoom": 1.1},
  {"at": "A minute ago", "picture": "p_moscow_out", "crop_x": 0.5, "zoom": 1.0},
  {"at": "But now the grass", "picture": "p_steppe_empty", "crop_x": 0.5, "zoom": 1.0},
  {"at": "Nobody speaks", "picture": "p_riders_ridge", "crop_x": 0.5, "zoom": 1.1},
  {"at": "The year is 1223", "picture": "p_khan_ridge", "crop_x": 0.5, "zoom": 1.15}]}
S2 = {"id": "SH02", "style": "fact_bomb", "ending": "question", "source_period": "1223",
 "hook": "Why did arrows outrange Napoleon's muskets?",
 "lines": [
  L("Why did arrows outrange Napoleon's muskets?", ["C-06", "C-09"], [
    T("arrows", "ARROWS", [0.5, 0.2], "arrows are the subject"),
    HL("muskets", [0.4, 0.55], "rings the muskets")], tags=["curious"]),
  L("But a musket reaches ninety metres, and an arrow four hundred.", ["C-06", "C-09"], [
    CH("ninety metres", "bars", [90, 400], "C-06", "a musket against an arrow, in metres", unit="m", labels=["MUSKET", "ARROW"]),
    HL("four hundred", [0.5, 0.5], "rings the four hundred bar")]),
  L("Napoleon's long guns still throw iron nine hundred metres.", ["C-05"], [
    CH("nine hundred metres", "bars", [400, 900], "C-05", "the gun against the arrow, in metres", unit="m", labels=["ARROW", "GUN"])]),
  L("At six hundred metres the iron breaks into hail.", ["C-05"], [
    T("hail", "IRON HAIL", [0.5, 0.2], "the iron breaks into hail")]),
  L("But the riders will not stand where the iron falls.", ["C-93"], [
    SY("will not stand", "cross", [0.85, 0.25], "the riders will not stand there")]),
  L("They burn the wagons from beyond the guns' reach.", ["C-93", "C-09"], [
    PR("wagons", "burning wagon", "the wagons burn"),
    HL("beyond", [0.6, 0.4], "rings the gap beyond the reach")]),
  L("They never came into range. Full story on the channel.", ["C-93"], [
    LB("Full story", "FULL STORY", [0.5, 0.82], "points to the full story")]),
 ],
 "shots": [
  {"at": "Why did arrows", "picture": "p_bow_loft", "crop_x": 0.5, "zoom": 1.0},
  {"at": "Napoleon's muskets", "picture": "p_musket_arrow", "crop_x": 0.5, "zoom": 1.0},
  {"at": "But a musket reaches", "picture": "p_guns_slope", "crop_x": 0.4, "zoom": 1.1},
  {"at": "Napoleon's long guns", "picture": "p_gun_fire", "crop_x": 0.5, "zoom": 1.0},
  {"at": "At six hundred", "picture": "p_gun_crew", "crop_x": 0.5, "zoom": 1.0},
  {"at": "But the riders", "picture": "p_riders_halt", "crop_x": 0.5, "zoom": 1.1},
  {"at": "They burn the wagons", "picture": "p_wagons_burn", "crop_x": 0.5, "zoom": 1.0},
  {"at": "They never came", "picture": "p_n_close10", "crop_x": 0.5, "zoom": 1.2}]}
S3 = {"id": "SH03", "style": "dialogue_clash", "ending": "cliffhanger", "source_period": "1223",
 "hook": "Take two guns, and the men stay with me.",
 "lines": [
  L("Take two guns, and the men stay with me.", ["C-94"], speaker="napoleon", to="genghis", intent="decide", beats=[
    T("two guns", "TWO GUNS", [0.5, 0.2], "two guns is the price")]),
  L("A tube without a man who knows it is only a pot.", ["C-11"], speaker="genghis", to="napoleon", intent="press", beats=[
    PR("a pot", "iron pot", "the gun is only a pot")]),
  L("But where I come from, a man belongs to himself.", speaker="napoleon", to="genghis", intent="press", beats=[
    SY("belongs to himself", "equals", [0.15, 0.25], "a man belongs to himself")]),
  L("Then your guns will be lonely.", speaker="genghis", to="napoleon", intent="deflect", beats=[
    HL("lonely", [0.7, 0.4], "rings the lonely guns")]),
  L("Learn the rest yourself.", speaker="napoleon", to="genghis", intent="decide", beats=[
    HL("yourself", [0.3, 0.4], "rings the word yourself")]),
  L("Kerim translates. The khan says nothing for a long while.", ["C-94"], beats=[
    LB("Kerim", "KERIM", [0.5, 0.82], "the translator in the middle"),
    T("nothing", "SILENCE", [0.5, 0.2], "the khan says nothing")]),
  L("Two. The fog is yours at dawn.", speaker="genghis", to="napoleon", intent="concede", beats=[
    T("at dawn", "AT DAWN", [0.5, 0.2], "the fog opens at dawn")]),
 ],
 "shots": [
  {"at": "Take two guns", "picture": "p_carpet_wide", "crop_x": 0.25, "zoom": 1.0},
  {"at": "and the men stay", "picture": "p_n_close13", "crop_x": 0.5, "zoom": 1.1},
  {"at": "A tube without", "picture": "p_khan_close13", "crop_x": 0.5, "zoom": 1.1},
  {"at": "But where I come", "picture": "p_two_nk", "crop_x": 0.3, "zoom": 1.0},
  {"at": "Then your guns", "picture": "p_guns_left", "crop_x": 0.5, "zoom": 1.0},
  {"at": "Learn the rest", "picture": "p_n_close13", "crop_x": 0.5, "zoom": 1.2},
  {"at": "Kerim translates", "picture": "p_kerim_close13", "crop_x": 0.5, "zoom": 1.0},
  {"at": "Two. The fog", "picture": "p_khan_close13", "crop_x": 0.5, "zoom": 1.15}]}
d["shorts"] = [S1, S2, S3]
json.dump(d, open(A + "production_script.json", "w"), indent=1, ensure_ascii=False)
