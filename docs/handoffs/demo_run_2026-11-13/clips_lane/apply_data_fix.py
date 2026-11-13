"""Data fix package for script A of ep_truce_1914 (clips lane, 2026-11-13): BP-185 families on the 2.5D stills, the two map date
labels, FL-023 handles. Editor-owned fields only (shots[*].motion_imitation, actions, edit_plan). No word, picture or story change.
usage: apply_data_fix.py IN.json OUT.json [--endcard black|candle] [--s02sh009 video|still]
"""
import hashlib, json, sys

# shot -> [(effect, why)]; each effect is a second family beside the one the shot already has (atmosphere, light, surface, subject)
ADD = {
    "S01_SH001": [("fire_flicker", "the lamps at the trench edges flicker; the fire's crackle is the bed's")],
    "S01_SH004": [("mist", "ground fog drifts over the field; mist is heard in the bed")],
    "S01_SH005": [("mist", "night frost-fog lies on the field; mist is heard in the bed")],
    "S02_SH004": [("fire_flicker", "the brazier's flame flickers; the fire's crackle is the bed's")],
    "S02_SH005": [("embers", "sparks lift from the brazier below the letter; embers are the fire's bed")],
    "S02_SH008": [("fire_flicker", "the brazier's flame flickers; the fire's crackle is the bed's")],
    "S03_SH002": [("dust", "motes drift in the candle's light; the cold night bed carries it")],
    "S03_SH010": [("mist", "cold ground mist over the frozen field; mist is heard in the bed")],
    "S04_SH001": [("sun_shaft_drift", "the low sun's light drifts through the fog; the dawn bed carries it")],
    "S04_SH011": [("sun_shaft_drift", "the low sun's light drifts behind the hands; the dawn bed carries it"),
                  ("mist", "a thin frost mist over the field; mist is heard in the bed")],
    "S05_SH003": [("smoke_drift", "breath and brazier smoke rise between the men; the bed carries it")],
    "S05_SH010": [("sun_shaft_drift", "the low sun's light drifts behind the hands; the dawn bed carries it"),
                  ("mist", "a thin frost mist over the field; mist is heard in the bed")],
    "S05_SH016": [("smoke_drift", "smoke rises from the braziers behind the stretcher; the bed carries it"),
                  ("fire_flicker", "the braziers flicker; the fire's crackle is the bed's")],
    "S05_SH020": [("sun_shaft_drift", "the low sun's light drifts over the graves; the dawn bed carries it")],
    "S06_SH001": [("smoke_drift", "brazier smoke rises beside the German; the bed carries it")],
    "S06_SH005": [("smoke_drift", "smoke rises from the two trench lines; the bed carries it"),
                  ("sun_shaft_drift", "the low sun's light drifts over the ice; the dawn bed carries it")],
    "S06_SH012": [("smoke_drift", "smoke rises from the trench; the bed carries it")],
    "S07_SH001": [("sun_shaft_drift", "the low sun's light drifts through the mist; the dawn bed carries it")],
    "S08_SH001": [("dust", "motes drift in the candle's light; the cold night bed carries it")],
    "S08_SH002": [("fire_flicker", "the candle's flame flickers; its sound is the bed's"),
                  ("dust", "motes drift in the candle's light; the cold night bed carries it")],
    "S08_SH003": [("smoke_drift", "smoke rises from the trench braziers; the bed carries it"),
                  ("sun_shaft_drift", "the last low sun's light drifts over the field; the bed carries it")],
}
# the map date labels need a place (maps/actions.PLACE_KINDS): the place the shot's line is about
LABEL_FROM = {"S02_SH001": "aachen", "S02_SH002": "nieuport"}
# the map frames cut the routes off (found by rendering): S02_SH001 has Aachen/Liege/Brussels above the frame, S02_SH002's front runs
# from Nieuport (y -170) to the Swiss border (y 1320), S02_SH003 starts on "the whole front line", S05_SH001's line from Ypres
# (y -366) to La Bassee (y 1138). Frames computed so that every place of the shot lies inside with a 14 % margin.
MAP_VIEW = {"S02_SH001": {"lon": 4.84, "lat": 49.9, "span_km": 530},
            "S02_SH002": {"lon": 4.95, "lat": 49.31, "span_km": 1000},
            "S02_SH003": {"lon": 4.95, "lat": 49.31, "span_km": 1000},
            "S05_SH001": {"lon": 2.871, "lat": 50.692, "span_km": 90},
            "S05_SH002": {"lon": 2.871, "lat": 50.692, "span_km": 90}}
# two map shots whose own composition text names a line that no action draws (each shot is rendered alone): S02_SH003 "the whole
# front line on the plate", S05_SH002 "the patches glow along the line" (without a place it was drawn as a bare orange counter card)
FRONT = ["ypres", "armentieres", "la_bassee", "arras", "noyon", "soissons", "reims", "verdun", "st_mihiel", "pont_a_mousson"]
KNOWN = "the line is already known from the shot before; it stands at once, no draw (BP-81)"
EXTRA_ACTIONS = {
    "S02_SH003": [(0, {"kind": "front_line", "at_word": "Here", "from": "nieuport", "to": "swiss_border", "via": FRONT, "cues": "none",
                       "event_id": "S02_SH003.A0", "audio": {"decision": "silent_by_design", "why": KNOWN}})],
    "S05_SH002": [(0, {"kind": "front_line", "at_word": "Nobody", "from": "ypres", "to": "la_bassee",
                       "via": ["wulverghem", "ploegsteert", "frelinghien", "armentieres", "fleurbaix"], "cues": "none",
                       "event_id": "S05_SH002.A0", "audio": {"decision": "silent_by_design", "why": KNOWN}})]
                  + [(1 + i, {"kind": "highlight", "at_word": "Nobody", "from": pl, "value": 3, "event_id": f"S05_SH002.A{2 + i}",
                              "audio": {"decision": "silent_by_design", "why": "the glow of the patches the shot before pulsed; the counter's sound is the cue (BP-81)"}})
                     for i, pl in enumerate(["wulverghem", "ploegsteert", "frelinghien", "fleurbaix"])],
}
# FL-023: both shots hold one narrator line and the clip must hold line + handles inside LTX's 10.06 s; hard cut out, no dissolve
# on the real clock (clock/timing.json): S04_SH008 = 10.000 s (needs tail 0), S02_SH009 = 10.4583 s (needs more than any handle can give)
HANDLES = {"S04_SH008": {"head_handle_s": 0.0, "tail_handle_s": 0.0}, "S02_SH009": {"head_handle_s": 0.0, "tail_handle_s": 0.0}}


def to_still(e):    # FL-023 option ა: S02_SH009 as a 2.5D shot on its own start picture (no LTX clip)
    e["route"], e["generation_mode"], e["visual_type"], e["motion_profile"] = "still_25d", "STILL_25D", "composed_illustration", "battle"
    e["route_reason"] = "place, object or tableau with no line spoken in frame: the 2.5D renderer carries it (RT-02)"
    e["keyframe_plan"]["start_frame_source"] = "new_master_anchor"
    e["video_prompt"] = {"motion_prompt": "A slow push toward the men as the narrator names the tins.", "primary_action_count": 1,
                         "camera_move_count": 1, "parallax_preset": "dolly_in"}
    e["motion_imitation"] = [
        {"effect": "push", "event_id": "S02_SH009.M1", "audio": {"decision": "silent_by_design", "why": "a slow camera move under the voice (BP-81 budget)"}, "strength": 0.6},
        {"effect": "fire_flicker", "event_id": "S02_SH009.M2", "audio": {"decision": "ambience_only", "why": "the brazier's flame flickers; the fire's crackle is the bed's"}},
        {"effect": "smoke_drift", "event_id": "S02_SH009.M3", "audio": {"decision": "ambience_only", "why": "breath and brazier smoke rise; the bed carries it"}}]
    e.pop("edit_plan", None)


def fix(d, endcard, s02sh009="video"):
    S = {s["shot_id"]: s for s in d["shots"]}
    for sid, items in ADD.items():
        mi = S[sid]["motion_imitation"]
        n = len(mi)
        for effect, why in items:
            n += 1
            mi.append({"effect": effect, "event_id": f"{sid}.M{n}", "audio": {"decision": "ambience_only", "why": why}})
    for sid, place in LABEL_FROM.items():
        for a in S[sid]["actions"]:
            if a["kind"] == "label":
                a["from"] = place
    for sid, items in EXTRA_ACTIONS.items():
        for pos, a in items:
            S[sid]["actions"].insert(pos, a)
    if endcard == "candle":    # S08_SH004: the black end card gets one small candle (a local crop of S08_SH002's candle on black)
        e = S["S08_SH004"]
        e["motion_imitation"] += [
            {"effect": "fire_flicker", "event_id": "S08_SH004.M2", "audio": {"decision": "silent_by_design", "why": "the film ends in silence; the candle's flicker makes no sound"}},
            {"effect": "smoke_drift", "event_id": "S08_SH004.M3", "audio": {"decision": "silent_by_design", "why": "the film ends in silence; the thin smoke makes no sound"}}]
        e["image_prompt"]["start_frame_prompt"] = ("Flanders, Christmas 1914, a frozen winter world. A black frame with one small candle "
                                                  "flame in a tin holder low in the right corner, nothing else, no text.")
        e["action_start_state"] = "Black with one small candle flame low in the corner"
        e["action_end_state"] = "Black with one small candle flame and the line of text"
        e["screen_composition"].update(foreground="one small candle in a tin holder, low right", notes=None) if False else \
            e["screen_composition"].update(foreground="one small candle in a tin holder, low right")
    for sid, mv in MAP_VIEW.items():
        S[sid]["map_view"] = dict(mv)
    for sid, h in HANDLES.items():
        if sid == "S02_SH009" and s02sh009 == "still":
            to_still(S[sid])
        else:
            S[sid]["edit_plan"].update(h)
    return d


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    endcard = sys.argv[sys.argv.index("--endcard") + 1] if "--endcard" in sys.argv else "none"
    s02 = sys.argv[sys.argv.index("--s02sh009") + 1] if "--s02sh009" in sys.argv else "video"
    d = fix(json.load(open(src, encoding="utf-8")), endcard, s02)
    txt = json.dumps(d, indent=1, ensure_ascii=False) + "\n"
    open(dst, "w", encoding="utf-8").write(txt)
    print(hashlib.sha256(txt.encode("utf-8")).hexdigest())
