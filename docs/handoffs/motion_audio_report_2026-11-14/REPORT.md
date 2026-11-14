# მოძრაობისა და ხმის რეპორტი: 6 ფოტო + 4 რუკა (Truce 1914, სკრიპტი A db99ec7d)

რას წერს სკრიპტი მოძრაობაზე და ხმაზე და რას აკეთებს რენდერერი. მონაცემები: `episodes/ep_truce_1914/story/production_script.json` (ციტატა სიტყვასიტყვით), `audio/sound_plan.json`, გაზომვა: 1080p რენდერი. დრო: 2026-11-14.

## S01_SH001  (ფოტო 2.5D, 2.0 წმ სკრიპტში)
**ამბავი:** Open on the empty frozen field at dawn so the first second says place, cold and danger
**კამერა სკრიპტში:** {"shot_size": "wide", "vertical_angle": "eye_level_0", "horizontal_azimuth_deg": 0, "camera_move": "slow_push_in", "multiangle_token": null}
ფოტო: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w2/S01_SH001_start_r2.png  
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_five_test_shots/S01_SH001.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "motion_profile": "landscape",
 "motion_imitation": [
  {
   "effect": "push",
   "event_id": "S01_SH001.M1",
   "audio": {
    "decision": "silent_by_design",
    "why": "a slow camera move under the voice; its sound is the place's bed (BP-81 budget)"
   },
   "strength": 0.6
  },
  {
   "effect": "mist",
   "event_id": "S01_SH001.M2",
   "audio": {
    "decision": "ambience_only",
    "why": "the fog drift is carried by the wind bed"
   }
  },
  {
   "effect": "sun_shaft_drift",
   "event_id": "S01_SH001.M3",
   "audio": {
    "decision": "ambience_only",
    "why": "the low sun's light drifts through the fog; the place's bed carries it"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- სკრიპტიდან რენდერერმა გაითვალა: კამერის მოძრაობა `push` ძალით 0.6, ეფექტები: mist, sun_shaft_drift; ცოცხალი ოჯახები: atmosphere, light; სიღრმის პლანები: 4
- გაზომილი ზუმი ბოლო კადარზე: შორი პლანი ×1.036, ახლო პლანი ×1.0609; გვერდითი წანაცვლება 0 (orbit/truck არ არის)
- სურათის ცვლილება: ~6.81% წამში (კადრიდან კადრამდე 0.414%); გეიტები: PASS

**ხმა:**
- ადგილი: loc_no_mans_land (outdoor), ამინდი: freezing_wind_and_snow
- ფონი (bed): BED_01_loc_no_mans_land ['wind']
- მუსიკა სეგმენტზე S01: განწყობა mysterious, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: არცერთი (ყველა მოძრაობა silent_by_design / ambience_only, მხოლოდ ფონი)

## S08_SH002  (ფოტო 2.5D, 8.75 წმ სკრიპტში)
**ამბავი:** Friedrich with the portrait card and the brass button: the other side of the same night
**კამერა სკრიპტში:** {"shot_size": "medium_close_up", "vertical_angle": "high_angle_30", "horizontal_azimuth_deg": 0, "camera_move": "slow_push_in", "multiangle_token": null}
ფოტო: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/S08_SH002_start.png  
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_five_test_shots/S08_SH002.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "motion_profile": "object",
 "motion_imitation": [
  {
   "effect": "push",
   "event_id": "S08_SH002.M1",
   "audio": {
    "decision": "silent_by_design",
    "why": "a slow camera move under the voice; its sound is the place's bed (BP-81 budget)"
   },
   "strength": 0.5
  },
  {
   "effect": "fire_flicker",
   "event_id": "S08_SH002.M2",
   "audio": {
    "decision": "silent_by_design",
    "why": "a candle makes no sound"
   },
   "region": [
    0.78,
    0.3,
    0.92,
    0.62
   ]
  },
  {
   "effect": "dust",
   "event_id": "S08_SH002.M3",
   "audio": {
    "decision": "silent_by_design",
    "why": "the place's bed carries it"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- სკრიპტიდან რენდერერმა გაითვალა: კამერის მოძრაობა `push` ძალით 0.5, ეფექტები: fire_flicker, dust; ცოცხალი ოჯახები: atmosphere, light; სიღრმის პლანები: 3
- გაზომილი ზუმი ბოლო კადარზე: შორი პლანი ×1.03, ახლო პლანი ×1.0506; გვერდითი წანაცვლება 0 (orbit/truck არ არის)
- სურათის ცვლილება: ~1.62% წამში (კადრიდან კადრამდე 0.271%); გეიტები: REVIEW

**ხმა:**
- ადგილი: loc_german_trench (outdoor), ამინდი: high_altitude_wind
- ფონი (bed): BED_21_loc_german_trench ['wind', 'crowd_murmur']
- მუსიკა სეგმენტზე S08: განწყობა reflective, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: არცერთი (ყველა მოძრაობა silent_by_design / ambience_only, მხოლოდ ფონი)

## S06_SH001  (ფოტო 2.5D, 3.25 წმ სკრიპტში)
**ამბავი:** Time cut to dusk: two men sitting in the open where nobody could sit yesterday
**კამერა სკრიპტში:** {"shot_size": "wide", "vertical_angle": "eye_level_0", "horizontal_azimuth_deg": 90, "camera_move": "slow_pull_back", "multiangle_token": null}
ფოტო: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/S06_SH001_start.png  
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_five_test_shots/S06_SH001.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "motion_profile": "landscape",
 "motion_imitation": [
  {
   "effect": "pull",
   "event_id": "S06_SH001.M1",
   "audio": {
    "decision": "silent_by_design",
    "why": "a slow camera move under the voice; its sound is the place's bed (BP-81 budget)"
   },
   "strength": 0.5
  },
  {
   "effect": "sun_shaft_drift",
   "event_id": "S06_SH001.M2",
   "audio": {
    "decision": "silent_by_design",
    "why": "light only"
   },
   "region": [
    0.5,
    0.2,
    1.0,
    0.6
   ]
  },
  {
   "effect": "smoke_drift",
   "event_id": "S06_SH001.M3",
   "audio": {
    "decision": "silent_by_design",
    "why": "the place's bed carries it"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- სკრიპტიდან რენდერერმა გაითვალა: კამერის მოძრაობა `pull` ძალით 0.5, ეფექტები: sun_shaft_drift, smoke_drift; ცოცხალი ოჯახები: atmosphere, light; სიღრმის პლანები: 4
- გაზომილი ზუმი ბოლო კადარზე: შორი პლანი ×1.0, ახლო პლანი ×1.0; გვერდითი წანაცვლება 0 (orbit/truck არ არის)
- სურათის ცვლილება: ~6.51% წამში (კადრიდან კადრამდე 0.355%); გეიტები: REVIEW

**ხმა:**
- ადგილი: loc_no_mans_land (outdoor), ამინდი: freezing_wind_and_snow
- ფონი (bed): BED_17_loc_no_mans_land ['wind']
- მუსიკა სეგმენტზე S06: განწყობა reflective, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: არცერთი (ყველა მოძრაობა silent_by_design / ambience_only, მხოლოდ ფონი)

## S05_SH020  (ფოტო 2.5D, 7.75 წმ სკრიპტში)
**ამბავი:** The joint service: one psalm in two languages
**კამერა სკრიპტში:** {"shot_size": "wide", "vertical_angle": "eye_level_0", "horizontal_azimuth_deg": 90, "camera_move": "slow_push_in", "multiangle_token": null}
ფოტო: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/S05_SH020_start.png  
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_five_test_shots/S05_SH020.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "motion_profile": "battle",
 "motion_imitation": [
  {
   "effect": "push",
   "event_id": "S05_SH020.M1",
   "audio": {
    "decision": "silent_by_design",
    "why": "a slow camera move under the voice; its sound is the place's bed (BP-81 budget)"
   },
   "strength": 0.4
  },
  {
   "effect": "cloud_drift",
   "event_id": "S05_SH020.M2",
   "audio": {
    "decision": "silent_by_design",
    "why": "a slow sky; silence suits the service"
   },
   "region": [
    0.0,
    0.0,
    1.0,
    0.25
   ]
  },
  {
   "effect": "sun_shaft_drift",
   "event_id": "S05_SH020.M3",
   "audio": {
    "decision": "ambience_only",
    "why": "the low sun's light drifts over the graves; the place's bed carries it"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- სკრიპტიდან რენდერერმა გაითვალა: კამერის მოძრაობა `push` ძალით 0.4, ეფექტები: cloud_drift, sun_shaft_drift; ცოცხალი ოჯახები: atmosphere, light; სიღრმის პლანები: 3
- გაზომილი ზუმი ბოლო კადარზე: შორი პლანი ×1.024, ახლო პლანი ×1.0404; გვერდითი წანაცვლება 0 (orbit/truck არ არის)
- სურათის ცვლილება: ~3.6% წამში (კადრიდან კადრამდე 0.18%); გეიტები: REVIEW

**ხმა:**
- ადგილი: loc_no_mans_land (outdoor), ამინდი: high_altitude_wind
- ფონი (bed): BED_17_loc_no_mans_land ['wind']
- მუსიკა სეგმენტზე S05: განწყობა tragic, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: არცერთი (ყველა მოძრაობა silent_by_design / ambience_only, მხოლოდ ფონი)

## S02_SH008  (ფოტო 2.5D, 10.0 წმ სკრიპტში)
**ამბავი:** Raise the stakes from above: the people in charge said no; the men were never asked
**კამერა სკრიპტში:** {"shot_size": "wide", "vertical_angle": "eye_level_0", "horizontal_azimuth_deg": 135, "camera_move": "slow_push_in", "multiangle_token": null}
ფოტო: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/S02_SH008_start.png  
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_five_test_shots/S02_SH008.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "motion_profile": "portrait",
 "motion_imitation": [
  {
   "effect": "push",
   "event_id": "S02_SH008.M1",
   "audio": {
    "decision": "silent_by_design",
    "why": "a slow camera move under the voice; its sound is the place's bed (BP-81 budget)"
   },
   "strength": 0.5
  },
  {
   "effect": "cloud_drift",
   "event_id": "S02_SH008.M2",
   "audio": {
    "decision": "silent_by_design",
    "why": "the place's bed carries it"
   },
   "region": [
    0.0,
    0.0,
    1.0,
    0.35
   ]
  },
  {
   "effect": "fire_flicker",
   "event_id": "S02_SH008.M3",
   "audio": {
    "decision": "silent_by_design",
    "why": "the place's bed carries it"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- სკრიპტიდან რენდერერმა გაითვალა: კამერის მოძრაობა `push` ძალით 0.5, ეფექტები: cloud_drift, fire_flicker; ცოცხალი ოჯახები: atmosphere, light; სიღრმის პლანები: 4
- გაზომილი ზუმი ბოლო კადარზე: შორი პლანი ×1.03, ახლო პლანი ×1.0506; გვერდითი წანაცვლება 0 (orbit/truck არ არის)
- სურათის ცვლილება: ~1.91% წამში (კადრიდან კადრამდე 0.307%); გეიტები: REVIEW

**ხმა:**
- ადგილი: loc_british_trench (outdoor), ამინდი: high_altitude_wind
- ფონი (bed): BED_06_loc_british_trench ['wind', 'fire']
- მუსიკა სეგმენტზე S02: განწყობა dark, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: არცერთი (ყველა მოძრაობა silent_by_design / ambience_only, მხოლოდ ფონი)

## S05_SH016  (ფოტო 2.5D, 3.0 წმ სკრიპტში)
**ამბავი:** Insert: two spades in the frozen earth by the open grave; the work done together (VL-08 breath)
**კამერა სკრიპტში:** {"shot_size": "medium_close_up", "vertical_angle": "eye_level_0", "horizontal_azimuth_deg": 45, "camera_move": "static", "multiangle_token": null}
ფოტო: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/pictures/S3_scenes_w1/S05_SH016_start.png  
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_five_test_shots/S05_SH016.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "motion_profile": "object",
 "motion_imitation": [
  {
   "effect": "push",
   "event_id": "S05_SH016.M1",
   "audio": {
    "decision": "silent_by_design",
    "why": "the silence of the beat; no cue (BP-81)"
   },
   "strength": 0.3
  },
  {
   "effect": "smoke_drift",
   "event_id": "S05_SH016.M2",
   "audio": {
    "decision": "silent_by_design",
    "why": "the place's bed carries it"
   }
  },
  {
   "effect": "sun_shaft_drift",
   "event_id": "S05_SH016.M3",
   "audio": {
    "decision": "ambience_only",
    "why": "the low sun's light drifts over the spades and the stretcher; the place's bed carries it"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- სკრიპტიდან რენდერერმა გაითვალა: კამერის მოძრაობა `push` ძალით 0.3, ეფექტები: smoke_drift, sun_shaft_drift; ცოცხალი ოჯახები: atmosphere, light; სიღრმის პლანები: 4
- გაზომილი ზუმი ბოლო კადარზე: შორი პლანი ×1.018, ახლო პლანი ×1.0302; გვერდითი წანაცვლება 0 (orbit/truck არ არის)
- სურათის ცვლილება: ~4.76% წამში (კადრიდან კადრამდე 0.228%); გეიტები: PASS

**ხმა:**
- ადგილი: loc_no_mans_land (outdoor), ამინდი: freezing_wind_and_snow
- ფონი (bed): BED_17_loc_no_mans_land ['wind']
- მუსიკა სეგმენტზე S05: განწყობა tragic, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: არცერთი (ყველა მოძრაობა silent_by_design / ambience_only, მხოლოდ ფონი)

## S02_SH001  (რუკა, 6.0 წმ სკრიპტში)
**ამბავი:** August 1914: the war starts as a fast march, the promise of a short war
**კამერა სკრიპტში:** {"shot_size": "top_down_map", "vertical_angle": "bird_eye_60", "horizontal_azimuth_deg": 0, "camera_move": "parallax_dolly", "multiangle_token": null}
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH001.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "map_view": {
  "lon": 4.84,
  "lat": 49.9,
  "span_km": 530
 },
 "actions": [
  {
   "kind": "label",
   "at_word": "August",
   "label": "August 1914",
   "event_id": "S02_SH001.A1",
   "audio": {
    "decision": "ui_cue",
    "class": "map_arrive_click",
    "sync": "onset",
    "purpose": "clarify"
   },
   "from": "chip_aug"
  },
  {
   "kind": "route_arrow",
   "at_word": "Everyone",
   "until_word": "Christmas",
   "from": "aachen",
   "to": "marne",
   "via": [
    "liege",
    "brussels"
   ],
   "event_id": "S02_SH001.A2",
   "audio": {
    "decision": "sfx",
    "class": "map_route_draw",
    "sync": "span",
    "purpose": "clarify"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- რენდერერმა დახატა 137 კადრი (5.7083 წმ), სტატუსი REVIEW
- რუკის მოძრაობა (მარშრუტი, ხაზი, წარწერა, zoom, მონიშვნა, მრიცხველი) ხდება მხოლოდ actions-ის სიტყვაზე; დანარჩენ დროს რუკა დგას (გეიტი BP-164 REVIEW)

**ხმა:**
- ადგილი: loc_western_front_map (outdoor), ამინდი: high_altitude_wind
- ფონი (bed): BED_05_loc_western_front_map ['wind']
- მუსიკა სეგმენტზე S02: განწყობა dark, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: map_arrive_click @2.125 წმ (ui_cue, label); map_route_draw @2.458 წმ (sfx, route_arrow); map_arrive_click @5.208 წმ (ui_cue, route_arrow:arrive)

## S02_SH002  (რუკა, 7.75 წმ სკრიპტში)
**ამბავი:** December: the march has frozen into one trench line from the sea to Switzerland
**კამერა სკრიპტში:** {"shot_size": "top_down_map", "vertical_angle": "bird_eye_60", "horizontal_azimuth_deg": 0, "camera_move": "parallax_dolly", "multiangle_token": null}
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH002.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "map_view": {
  "lon": 4.95,
  "lat": 49.31,
  "span_km": 1000
 },
 "actions": [
  {
   "kind": "label",
   "at_word": "December",
   "label": "December 1914",
   "event_id": "S02_SH002.A1",
   "audio": {
    "decision": "ui_cue",
    "class": "map_arrive_click",
    "sync": "onset",
    "purpose": "clarify"
   },
   "from": "chip_dec"
  },
  {
   "kind": "front_line",
   "at_word": "trenches",
   "until_word": "Switzerland",
   "from": "nieuport",
   "to": "swiss_border",
   "via": [
    "ypres",
    "armentieres",
    "la_bassee",
    "arras",
    "noyon",
    "soissons",
    "reims",
    "verdun",
    "st_mihiel",
    "pont_a_mousson"
   ],
   "event_id": "S02_SH002.A2",
   "audio": {
    "decision": "sfx",
    "class": "map_route_draw",
    "sync": "span",
    "purpose": "clarify"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- რენდერერმა დახატა 191 კადრი (7.9583 წმ), სტატუსი REVIEW
- რუკის მოძრაობა (მარშრუტი, ხაზი, წარწერა, zoom, მონიშვნა, მრიცხველი) ხდება მხოლოდ actions-ის სიტყვაზე; დანარჩენ დროს რუკა დგას (გეიტი BP-164 REVIEW)

**ხმა:**
- ადგილი: loc_western_front_map (outdoor), ამინდი: high_altitude_wind
- ფონი (bed): BED_05_loc_western_front_map ['wind']
- მუსიკა სეგმენტზე S02: განწყობა dark, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: map_arrive_click @0.792 წმ (ui_cue, label); map_route_draw @4.458 წმ (sfx, front_line)

## S02_SH003  (რუკა, 6.0 წმ სკრიპტში)
**ამბავი:** Fly to Flanders: the sector of our story, where the lines nearly touch
**კამერა სკრიპტში:** {"shot_size": "top_down_map", "vertical_angle": "bird_eye_60", "horizontal_azimuth_deg": 0, "camera_move": "parallax_dolly", "multiangle_token": null}
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S02_SH003.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "map_view": {
  "lon": 4.95,
  "lat": 49.31,
  "span_km": 1000
 },
 "actions": [
  {
   "kind": "front_line",
   "at_word": "Here",
   "from": "nieuport",
   "to": "swiss_border",
   "via": [
    "ypres",
    "armentieres",
    "la_bassee",
    "arras",
    "noyon",
    "soissons",
    "reims",
    "verdun",
    "st_mihiel",
    "pont_a_mousson"
   ],
   "cues": "none",
   "event_id": "S02_SH003.A0",
   "audio": {
    "decision": "silent_by_design",
    "why": "the line is already known from the shot before; it stands at once, no draw (BP-81)"
   }
  },
  {
   "kind": "zoom",
   "at_word": "Here",
   "to": "flanders",
   "value": 60,
   "camera": "fly_to",
   "event_id": "S02_SH003.A1",
   "audio": {
    "decision": "silent_by_design",
    "why": "a camera move under the voice; the draw sound has just ended (BP-81)"
   }
  },
  {
   "kind": "highlight",
   "at_word": "close",
   "from": "frelinghien",
   "value": 8,
   "event_id": "S02_SH003.A2",
   "audio": {
    "decision": "ui_cue",
    "class": "map_arrive_click",
    "sync": "onset",
    "purpose": "clarify"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- რენდერერმა დახატა 132 კადრი (5.5 წმ), სტატუსი REVIEW
- რუკის მოძრაობა (მარშრუტი, ხაზი, წარწერა, zoom, მონიშვნა, მრიცხველი) ხდება მხოლოდ actions-ის სიტყვაზე; დანარჩენ დროს რუკა დგას (გეიტი BP-164 REVIEW)

**ხმა:**
- ადგილი: loc_western_front_map (outdoor), ამინდი: high_altitude_wind
- ფონი (bed): BED_05_loc_western_front_map ['wind']
- მუსიკა სეგმენტზე S02: განწყობა dark, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: map_arrive_click @2.833 წმ (ui_cue, highlight)

## S05_SH002  (რუკა, 6.25 წმ სკრიპტში)
**ამბავი:** How many men: the estimate on the map, the number tied to its claim
**კამერა სკრიპტში:** {"shot_size": "top_down_map", "vertical_angle": "bird_eye_60", "horizontal_azimuth_deg": 0, "camera_move": "parallax_dolly", "multiangle_token": null}
კლიპი: https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal/S05_SH002.mp4

**სკრიპტი მოძრაობაზე (სიტყვასიტყვით):**
```json
{
 "map_view": {
  "lon": 2.871,
  "lat": 50.692,
  "span_km": 90
 },
 "actions": [
  {
   "kind": "front_line",
   "at_word": "Nobody",
   "from": "ypres",
   "to": "la_bassee",
   "via": [
    "wulverghem",
    "ploegsteert",
    "frelinghien",
    "armentieres",
    "fleurbaix"
   ],
   "cues": "none",
   "event_id": "S05_SH002.A0",
   "audio": {
    "decision": "silent_by_design",
    "why": "the line is already known from the shot before; it stands at once, no draw (BP-81)"
   }
  },
  {
   "kind": "highlight",
   "at_word": "Nobody",
   "from": "wulverghem",
   "value": 3,
   "event_id": "S05_SH002.A2",
   "audio": {
    "decision": "silent_by_design",
    "why": "the glow of the patches the shot before pulsed; the counter's sound is the cue (BP-81)"
   }
  },
  {
   "kind": "highlight",
   "at_word": "Nobody",
   "from": "ploegsteert",
   "value": 3,
   "event_id": "S05_SH002.A3",
   "audio": {
    "decision": "silent_by_design",
    "why": "the glow of the patches the shot before pulsed; the counter's sound is the cue (BP-81)"
   }
  },
  {
   "kind": "highlight",
   "at_word": "Nobody",
   "from": "frelinghien",
   "value": 3,
   "event_id": "S05_SH002.A4",
   "audio": {
    "decision": "silent_by_design",
    "why": "the glow of the patches the shot before pulsed; the counter's sound is the cue (BP-81)"
   }
  },
  {
   "kind": "highlight",
   "at_word": "Nobody",
   "from": "fleurbaix",
   "value": 3,
   "event_id": "S05_SH002.A5",
   "audio": {
    "decision": "silent_by_design",
    "why": "the glow of the patches the shot before pulsed; the counter's sound is the cue (BP-81)"
   }
  },
  {
   "kind": "counter",
   "at_word": "hundred",
   "until_word": "part",
   "value": 100000,
   "unit": "men (estimate)",
   "claim": "C-03",
   "event_id": "S05_SH002.A1",
   "audio": {
    "decision": "sfx",
    "class": "data_rise_texture",
    "sync": "span",
    "purpose": "clarify"
   }
  }
 ]
}
```
**რა გააკეთა რენდერერმა:**
- რენდერერმა დახატა 163 კადრი (6.7917 წმ), სტატუსი REVIEW
- რუკის მოძრაობა (მარშრუტი, ხაზი, წარწერა, zoom, მონიშვნა, მრიცხველი) ხდება მხოლოდ actions-ის სიტყვაზე; დანარჩენ დროს რუკა დგას (გეიტი BP-164 REVIEW)

**ხმა:**
- ადგილი: loc_western_front_map (outdoor), ამინდი: high_altitude_wind
- ფონი (bed): BED_16_loc_western_front_map ['wind']
- მუსიკა სეგმენტზე S05: განწყობა tragic, მუსიკა: True
- ხმოვანი ჩანაწერები კადარში: data_rise_texture @3.792 წმ (sfx, counter)

## დასკვნა
- სკრიპტი ყველა ამ ფოტოზე წერს ერთ ნაზ ზუმს (push/pull strength 0.4-0.6), 2 ეფექტს ნაგულისხმევი ძალით; orbit და truck არსად წერია. რენდერერი ამ ძალაზე იძლევა ზუმს მხოლოდ ×1.018-×1.061.
- რენდერერს მეტი შეუძლია: კამერის ძალა 1.0-1.5-მდე და ახლო პლანის წანაცვლება სიგანის 8%-მდე (ზღვარი BP-182).
- ხმა ფოტოებზე ძირითადად ფონია (wind და ა.შ.), ეფექტებს ხმა თითქმის არ აქვთ (silent_by_design / ambience_only): ეს ვანოს გადაწყვეტილებაა 11-13 (BP-81 ბიუჯეტი).
