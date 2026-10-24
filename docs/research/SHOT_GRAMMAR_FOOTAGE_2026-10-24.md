# Shot grammar of the creator's cartoons (2026-10-24)

Why: ვანო asked (2026-10-24, 15:50 Tbilisi) to study the shots of the cartoons he sent before writing the prompt rules
(docs/SHOT_PROMPTS.md, KP-19 and KP-26). Material: HF dataset `vano1919/tmr-artifacts`, `footage_2026-10-23/raw/`
(`rick_and_morty_s1_3_moments.mp4`, `solar_opposites_s5_moments.mp4`, `inside_job_part_retrospective.mp4`) and the shot list
`footage_2026-10-23/work/shots.json` (3517 shots; 3312 without duplicates; shots under 2 s were not cut out).

Method: per show, 4 random runs of 10 consecutive shots (seed 7), the middle frame of each shot on contact sheets; each frame
labelled by eye (Claude) for shot size, the number of people who read as characters (9 = a crowd), and over-the-shoulder
framing. `camera` and `static_share` (the share of near-still frames) come from shots.json. What this does not measure:
shots under 2 s, dialogue versus silence, angles other than eye level (nearly all frames were eye level; low angles appear
when the characters are small creatures, high angles in establishing shots).

## Results

| Measure | Value |
|---|---|
| shot size | MS 30 %, WS 20 %, MCU 18 %, MWS (full body) 17 %, insert 8 %, EWS (establishing) 4 %, CU 3 % |
| people in shot | 0: 8 %, 1: 38 %, 2: 40 %, 3 or more: 15 % (10 of the 18 are wides) |
| over-the-shoulder | 16 % |
| static camera (all 3312 shots, camera < 0.01) | 81 % |
| median shot length (all 3312) | 3.2 s |
| median length by size (sample) | MS 3.5 s, MCU 3.6 s, MWS 3.6 s, WS 3.3 s, insert 3.0 s, EWS 5.2 s |

Patterns seen on the sheets:

- A scene opens on a wide that shows where everyone is, then cuts in to singles and two-shots; reverses are
  over-the-shoulder with the listener's back or shoulder large in the foreground.
- Two characters talking face each other in profile or three-quarter on the left and right thirds; a punch line or a
  reaction is a frontal medium close-up or close-up.
- Groups of three to five stand in a row in a wide or full shot; nobody acts big in them, the acting is cut to a medium.
- Inserts carry information without a face: a phone screen, a prop, a TV, hands.
- The camera is still; the few moves are a pan across action, a push into a reveal, a shake on an impact.

## Labels

| # | show | run | start s | length s | camera | still share | size | people | OTS |
|---|---|---|---|---|---|---|---|---|---|
| 0 | rick | 0 | 4181.4 | 2.2 | 0.001 | 0.00 | MS | 2 |  |
| 1 | rick | 0 | 4183.6 | 5.5 | 0.001 | 0.20 | MS | 2 | yes |
| 2 | rick | 0 | 4190.5 | 4.8 | 0.001 | 0.33 | WS | 2 |  |
| 3 | rick | 0 | 4195.4 | 16.9 | 0.224 | 0.09 | WS | 2 |  |
| 4 | rick | 0 | 4212.2 | 3.2 | 0.159 | 0.00 | MWS | 2 |  |
| 5 | rick | 0 | 4215.4 | 9.1 | 0.002 | 0.06 | WS | 1 |  |
| 6 | rick | 0 | 4224.5 | 16.3 | 0.001 | 0.44 | INS | 0 |  |
| 7 | rick | 0 | 4240.8 | 2.3 | 0.354 | 0.00 | WS | 1 |  |
| 8 | rick | 0 | 4243.2 | 2.7 | 0.010 | 0.00 | MS | 1 |  |
| 9 | rick | 0 | 4245.8 | 4.8 | 0.001 | 0.33 | WS | 9+ | yes |
| 10 | rick | 1 | 1960.6 | 9.9 | 0.003 | 0.58 | MCU | 1 |  |
| 11 | rick | 1 | 1970.6 | 4.4 | 0.000 | 0.50 | MCU | 1 |  |
| 12 | rick | 1 | 1975.0 | 2.3 | 0.056 | 0.50 | MCU | 1 |  |
| 13 | rick | 1 | 1977.3 | 2.6 | 0.001 | 0.50 | MS | 2 | yes |
| 14 | rick | 1 | 1979.9 | 3.5 | 0.000 | 1.00 | WS | 2 | yes |
| 15 | rick | 1 | 1983.4 | 3.6 | 0.002 | 0.50 | MS | 2 | yes |
| 16 | rick | 1 | 1991.3 | 2.4 | 0.000 | 1.00 | MS | 2 | yes |
| 17 | rick | 1 | 1996.0 | 2.3 | 0.000 | 0.75 | WS | 2 |  |
| 18 | rick | 1 | 1999.0 | 3.5 | 0.000 | 0.67 | MWS | 1 |  |
| 19 | rick | 1 | 2003.4 | 5.5 | 0.000 | 0.30 | WS | 2 |  |
| 20 | rick | 2 | 5105.8 | 4.6 | 0.057 | 0.38 | MWS | 4 |  |
| 21 | rick | 2 | 5110.4 | 2.0 | 0.001 | 0.00 | INS | 0 |  |
| 22 | rick | 2 | 5114.2 | 2.3 | 0.179 | 0.00 | MS | 1 |  |
| 23 | rick | 2 | 5126.7 | 2.5 | 0.000 | 0.75 | WS | 3 |  |
| 24 | rick | 2 | 5130.0 | 5.3 | 0.001 | 0.60 | MS | 2 |  |
| 25 | rick | 2 | 5136.0 | 3.7 | 0.002 | 0.14 | MCU | 1 |  |
| 26 | rick | 2 | 5139.7 | 2.8 | 0.000 | 0.80 | WS | 3 |  |
| 27 | rick | 2 | 5142.5 | 2.0 | 0.000 | 0.67 | MS | 1 |  |
| 28 | rick | 2 | 5144.5 | 3.3 | 0.000 | 1.00 | WS | 4 |  |
| 29 | rick | 2 | 5147.9 | 6.6 | 0.000 | 0.92 | MS | 2 | yes |
| 30 | rick | 3 | 599.3 | 2.2 | 0.225 | 0.00 | CU | 1 |  |
| 31 | rick | 3 | 602.8 | 3.3 | 0.035 | 0.00 | MS | 2 |  |
| 32 | rick | 3 | 606.1 | 8.4 | 0.001 | 0.38 | MWS | 1 |  |
| 33 | rick | 3 | 614.5 | 2.1 | 0.298 | 0.00 | MWS | 1 |  |
| 34 | rick | 3 | 616.6 | 5.2 | 0.001 | 0.80 | MS | 5 |  |
| 35 | rick | 3 | 621.8 | 11.6 | 0.001 | 0.32 | MWS | 1 |  |
| 36 | rick | 3 | 645.9 | 3.0 | 0.000 | 0.40 | EWS | 1 |  |
| 37 | rick | 3 | 648.9 | 12.8 | 0.006 | 0.36 | MWS | 3 |  |
| 38 | rick | 3 | 662.9 | 7.0 | 0.001 | 0.23 | MS | 2 | yes |
| 39 | rick | 3 | 671.3 | 3.5 | 0.000 | 0.50 | WS | 3 |  |
| 40 | solar | 0 | 219.4 | 9.2 | 0.036 | 0.44 | MWS | 2 |  |
| 41 | solar | 0 | 228.6 | 7.1 | 0.002 | 0.31 | MCU | 2 |  |
| 42 | solar | 0 | 235.7 | 8.3 | 0.003 | 0.38 | MCU | 2 |  |
| 43 | solar | 0 | 244.0 | 4.7 | 0.002 | 0.00 | MS | 2 |  |
| 44 | solar | 0 | 249.9 | 2.5 | 0.027 | 0.25 | MCU | 2 |  |
| 45 | solar | 0 | 252.3 | 2.3 | 0.005 | 0.00 | WS | 2 |  |
| 46 | solar | 0 | 256.6 | 3.7 | 0.002 | 0.86 | MWS | 1 |  |
| 47 | solar | 0 | 260.3 | 3.6 | 0.008 | 0.33 | MCU | 1 |  |
| 48 | solar | 0 | 263.9 | 5.2 | 0.002 | 1.00 | EWS | 9+ |  |
| 49 | solar | 0 | 269.1 | 5.6 | 0.008 | 0.50 | CU | 1 |  |
| 50 | solar | 1 | 1522.4 | 7.0 | 0.061 | 0.31 | EWS | 0 |  |
| 51 | solar | 1 | 1529.4 | 2.3 | 0.019 | 0.00 | WS | 0 |  |
| 52 | solar | 1 | 1531.7 | 2.3 | 0.002 | 0.00 | INS | 0 |  |
| 53 | solar | 1 | 1534.0 | 3.2 | 0.000 | 0.50 | WS | 1 |  |
| 54 | solar | 1 | 1537.2 | 2.8 | 0.000 | 1.00 | EWS | 0 |  |
| 55 | solar | 1 | 1540.0 | 15.3 | 0.001 | 0.87 | MCU | 1 |  |
| 56 | solar | 1 | 1555.2 | 2.2 | 0.134 | 0.00 | WS | 2 |  |
| 57 | solar | 1 | 1561.4 | 4.2 | 0.001 | 0.25 | MWS | 2 |  |
| 58 | solar | 1 | 1565.6 | 3.5 | 0.000 | 0.50 | WS | 4 |  |
| 59 | solar | 1 | 1569.1 | 5.3 | 0.001 | 0.40 | MS | 1 |  |
| 60 | solar | 2 | 1022.1 | 2.1 | 0.136 | 0.00 | MS | 2 |  |
| 61 | solar | 2 | 1024.2 | 5.6 | 0.154 | 0.10 | INS | 1 |  |
| 62 | solar | 2 | 1033.0 | 3.5 | 0.154 | 0.67 | INS | 1 |  |
| 63 | solar | 2 | 1036.5 | 4.1 | 0.175 | 0.00 | MS | 2 |  |
| 64 | solar | 2 | 1040.6 | 3.7 | 0.001 | 0.57 | MS | 1 |  |
| 65 | solar | 2 | 1045.9 | 2.4 | 0.001 | 0.00 | MWS | 2 |  |
| 66 | solar | 2 | 1048.3 | 2.3 | 0.001 | 0.25 | MS | 1 |  |
| 67 | solar | 2 | 1050.7 | 2.1 | 0.001 | 0.00 | MWS | 2 |  |
| 68 | solar | 2 | 1052.8 | 2.5 | 0.001 | 0.25 | MWS | 2 |  |
| 69 | solar | 2 | 1056.5 | 7.0 | 0.000 | 0.69 | INS | 3 |  |
| 70 | solar | 3 | 256.6 | 3.7 | 0.002 | 0.86 | MWS | 1 |  |
| 71 | solar | 3 | 260.3 | 3.6 | 0.008 | 0.33 | MCU | 1 |  |
| 72 | solar | 3 | 263.9 | 5.2 | 0.002 | 1.00 | EWS | 9+ |  |
| 73 | solar | 3 | 269.1 | 5.6 | 0.008 | 0.50 | CU | 1 |  |
| 74 | solar | 3 | 279.2 | 5.9 | 0.004 | 0.36 | MS | 1 |  |
| 75 | solar | 3 | 285.8 | 5.1 | 0.000 | 0.89 | MWS | 2 | yes |
| 76 | solar | 3 | 290.9 | 3.8 | 0.000 | 1.00 | MWS | 2 | yes |
| 77 | solar | 3 | 294.7 | 4.5 | 0.053 | 0.12 | MCU | 1 |  |
| 78 | solar | 3 | 299.1 | 2.1 | 0.002 | 0.00 | MCU | 1 |  |
| 79 | solar | 3 | 306.6 | 2.0 | 0.001 | 0.67 | MCU | 1 |  |
| 80 | inside | 0 | 3956.4 | 3.2 | 0.001 | 0.17 | MS | 2 |  |
| 81 | inside | 0 | 3959.6 | 2.2 | 0.001 | 0.75 | WS | 3 |  |
| 82 | inside | 0 | 3963.4 | 3.0 | 0.001 | 0.60 | MCU | 2 | yes |
| 83 | inside | 0 | 3971.6 | 2.2 | 0.004 | 0.00 | CU | 1 |  |
| 84 | inside | 0 | 3976.1 | 3.5 | 0.001 | 0.67 | MS | 2 | yes |
| 85 | inside | 0 | 3982.8 | 3.0 | 0.069 | 0.00 | MS | 3 |  |
| 86 | inside | 0 | 3992.1 | 2.0 | 0.001 | 0.33 | MCU | 1 |  |
| 87 | inside | 0 | 3994.1 | 3.1 | 0.000 | 0.80 | MWS | 2 |  |
| 88 | inside | 0 | 3997.2 | 4.0 | 0.001 | 0.00 | MCU | 1 |  |
| 89 | inside | 0 | 4002.7 | 3.2 | 0.001 | 0.67 | MS | 2 | yes |
| 90 | inside | 1 | 768.0 | 3.6 | 0.000 | 1.00 | WS | 2 |  |
| 91 | inside | 1 | 772.2 | 4.0 | 0.001 | 0.71 | WS | 2 |  |
| 92 | inside | 1 | 776.3 | 4.3 | 0.002 | 0.50 | MCU | 1 |  |
| 93 | inside | 1 | 780.6 | 2.5 | 0.001 | 0.25 | MCU | 1 |  |
| 94 | inside | 1 | 786.4 | 3.1 | 0.000 | 0.20 | MWS | 2 |  |
| 95 | inside | 1 | 789.5 | 2.3 | 0.003 | 0.00 | WS | 1 |  |
| 96 | inside | 1 | 793.4 | 2.4 | 0.005 | 0.00 | MS | 2 | yes |
| 97 | inside | 1 | 795.7 | 3.5 | 0.005 | 0.83 | MS | 2 |  |
| 98 | inside | 1 | 800.8 | 2.4 | 0.000 | 0.75 | MS | 1 |  |
| 99 | inside | 1 | 803.2 | 7.7 | 0.001 | 0.73 | MS | 1 |  |
| 100 | inside | 2 | 5411.0 | 3.3 | 0.001 | 0.33 | MS | 2 |  |
| 101 | inside | 2 | 5414.3 | 4.8 | 0.001 | 0.67 | WS | 3 |  |
| 102 | inside | 2 | 5419.1 | 2.9 | 0.114 | 0.40 | MCU | 1 | yes |
| 103 | inside | 2 | 5422.9 | 3.7 | 0.001 | 0.43 | MS | 2 | yes |
| 104 | inside | 2 | 5426.6 | 4.3 | 0.000 | 0.50 | MCU | 1 |  |
| 105 | inside | 2 | 5431.0 | 5.1 | 0.005 | 0.11 | MS | 2 |  |
| 106 | inside | 2 | 5436.1 | 2.1 | 0.000 | 0.67 | INS | 0 |  |
| 107 | inside | 2 | 5448.7 | 2.2 | 0.000 | 1.00 | MWS | 2 |  |
| 108 | inside | 2 | 5450.8 | 2.0 | 0.001 | 0.00 | INS | 1 |  |
| 109 | inside | 2 | 5460.0 | 5.1 | 0.004 | 0.00 | MS | 2 | yes |
| 110 | inside | 3 | 2424.3 | 2.4 | 0.000 | 0.00 | INS | 0 |  |
| 111 | inside | 3 | 2428.0 | 2.7 | 0.000 | 0.40 | MS | 2 | yes |
| 112 | inside | 3 | 2432.4 | 4.8 | 0.001 | 0.44 | MS | 2 |  |
| 113 | inside | 3 | 2438.6 | 3.7 | 0.000 | 0.57 | MS | 2 |  |
| 114 | inside | 3 | 2443.7 | 3.0 | 0.000 | 1.00 | WS | 3 |  |
| 115 | inside | 3 | 2447.3 | 2.8 | 0.001 | 0.00 | MCU | 1 |  |
| 116 | inside | 3 | 2450.1 | 3.0 | 0.001 | 0.40 | WS | 4 | yes |
| 117 | inside | 3 | 2454.8 | 2.6 | 0.003 | 0.00 | MWS | 3 |  |
| 118 | inside | 3 | 2458.0 | 2.6 | 0.000 | 0.25 | MS | 1 |  |
| 119 | inside | 3 | 2460.6 | 6.5 | 0.003 | 0.42 | INS | 0 |  |
