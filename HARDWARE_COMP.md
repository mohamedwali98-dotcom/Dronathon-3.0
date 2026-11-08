# HARDWARE_COMP — SKYFORGE real-drone build (F12 bonus)

Hardware selection for a physical version of the SKYFORGE drone.
The competition itself is **fully simulated** (S-01). Real hardware only counts for the **F12 bonus**
(comms module on a real board, S-34).

- Source: team deck `altaadhdyh-alwtnyh-llawatlyh-bdar-aqbh.pdf` (hardware slides 8–17), recomputed.
- Owner requirements (v2): **lighter sensors**, **≥ 30 min mission flight time**, totals in the report,
  and a second look at whether the payload is worth carrying.
- Every number comes from `python docs/hardware_calc.py`. Change a mass there, re-run, update here.
- ⚠ Masses, currents and thrust are **typical datasheet/class values, not verified for a specific seller**.
  Check the exact product page and the motor's thrust table before buying (§9).

---

## 1. Result (pick C — light, long-endurance)

| | Value |
|---|---|
| Frame (support) | **300 g** (550 mm carbon frame + landing gear) |
| Dry drone (no battery, no payload) | **927 g** |
| Battery | **Li-ion 4S3P, Molicel P45B 21700** (13.5 Ah, 194 Wh), 870 g |
| **All-up weight (AUW)** | **1797 g** without a kit · 1897 g with a 100 g kit |
| Thrust-to-weight | **2.89** (target > 2 ✔) |
| Hover power | **≈ 209 W** (≈ 14.5 A) |
| **Hover time** | **≈ 45 min** |
| **Mission time** (hover × 1.2 for wind/climbs/turns) | **≈ 37 min ✔ (≥ 30 min)** · ≈ 34.5 min with a 100 g kit |

What changed from v1 (F450, 2216 motors, LiPo 4S 6000, ≈ 12 min mission):
1. **Li-ion instead of LiPo.** Li-ion stores ≈ 220 Wh/kg against ≈ 140 Wh/kg for LiPo. That alone is the 30-min enabler.
2. **Bigger, slower props (13").** Moving more air slowly needs less power (P = T·v, and v drops when the disk is larger).
3. **Lighter avionics:** 486 g → 227 g (§3).

---

## 2. Component list (on the drone)

| # | Component | Pick / reference | Why this one | Qty | Mass (g) | Power (W) |
|---|---|---|---|---|---|---|
| 1 | **Frame (support)** | 550 mm carbon quad frame + landing gear | Carbon is stiffer and lighter than the F450 nylon/PCB frame (332 g). 13" props fit (389 mm between motors vs 330 mm prop) | 1 | 300 | — |
| 2 | **Motors** | 3508 ~700KV, 4S (e.g. T-Motor MN3508 KV700, store.tmotor.com) | Made for 12–14" props, efficient at low throttle (≈ 9 g/W at hover). ≈ 1.3 kg max thrust each on 4S | 4 | 4 × 85 | hover ≈ 48 each |
| 3 | **Propellers** | 13 × 4.4 carbon, 2 CW + 2 CCW, + spares | Large disk = low hover power | 4 (+4) | 4 × 15 | — |
| 4 | **ESC** | 4-in-1 45 A, BLHeli_32 / AM32, built-in current sensor | One board replaces 4 ESCs + the PDB (104 g → 25 g). Current sensor replaces the power module | 1 | 25 | ≈ 95 % eff. |
| 5 | **Flight controller** | **Matek H743-SLIM** + ArduPilot (mateksys.com, ardupilot.org) | Has the **IMU and a DPS310 barometer on board**: no separate barometer, accelerometer or pressure board. 8 g instead of ≈ 60 g for a Pixhawk 6C | 1 | 8 | 1.0 |
| 6 | **GPS + compass** | Matek M10Q-5883 (u-blox M10 + QMC5883 compass) | Same function as a Holybro M10 GPS, 15 g instead of 40 g | 1 | 15 | 0.5 |
| 7 | **RC receiver** | ExpressLRS 2.4 GHz nano receiver (expresslrs.org) | Manual override + failsafe. **Never fly without it** | 1 | 3 | 0.3 |
| 8 | **Companion computer** | Raspberry Pi 5 **8 GB**, aluminium heatsink, no fan (raspberrypi.com) | Runs the LangGraph orchestrator + agents. The prop wash cools it, so the fan is dropped | 1 | 56 | 8.0 |
| 9 | **AI accelerator** | Raspberry Pi AI HAT+ 13 TOPS (Hailo-8L) | Real-time YOLO. The Pi's CPU alone gives only a few FPS | 1 | 20 | 2.0 |
| 10 | **Camera** | Raspberry Pi Camera Module 3 **Wide** (102° HFOV) + mount | Wide strip of ground for coverage (§7), victim detection, VIO | 1 | 10 | 1.0 |
| 11 | **LiDAR** | Benewake TFmini-S (benewake.com): **1 down + 1 front** | Down: exact altitude (the barometer drifts), landing, delivery height. Front: obstacles in the flight direction | 2 | 2 × 5 | 0.7 each |
| 12 | **Comms module (ESP32)** | Seeed XIAO ESP32-S3 + Wio-SX1262 LoRa (seeedstudio.com) | Same role as v1's Heltec board (JSON < 1 KB, ring buffer, resync = F12), ≈ 8 g instead of 20 g | 1 | 8 | 0.8 |
| 13 | **Secure element** | Microchip ATECC608B breakout | The deck's "HSM": ECDSA P-256 keys stored in hardware | 1 | 2 | ≈ 0 |
| 14 | **5 V regulator (BEC)** | 5 V / 5 A BEC | Clean power for the Pi 5. A weak supply makes it reboot mid-flight | 1 | 8 | (in losses) |
| 15 | **Payload release** | SG90 servo + 3D-printed hook | Lets the drone drop a kit (F7). Kit itself is optional (§6) | 1 | 12 | 0.5 |
| 16 | **Wiring & mounting** | XT60, silicone wire, IMU dampers, straps, buzzer, LEDs | Dampers keep the IMU clean on a light frame | — | 50 | 0.5 |
| 17 | **Battery** | Li-ion 4S3P, 12 × Molicel P45B 21700 (4.5 Ah, 45 A each), spot-welded | Best energy per gram (§5). Max draw ≈ 70 A → 23 A per cell, well under 45 A | 1 | 870 | 194 Wh (155 Wh usable) |

---

## 3. Totals

### Mass
| Group | Items | Mass (g) |
|---|---|---|
| Frame (support) | 1 | **300** |
| Propulsion (motors, props, ESC) | 2–4 | **425** |
| Flight control (FC with IMU + baro, GPS, RX) | 5–7 | **26** |
| Compute (Pi 5 + AI HAT+) | 8–9 | **76** |
| Sensors (camera, 2 LiDAR) | 10–11 | **20** |
| Comms (ESP32 LoRa, secure element) | 12–13 | **10** |
| Power (BEC) | 14 | **8** |
| Delivery (servo + hook) | 15 | **12** |
| Wiring & mounting | 16 | **50** |
| **Dry drone** | | **927** |
| Battery Li-ion 4S3P | 17 | 870 |
| **AUW, no kit** | | **1797** |
| Optional kit | | +100 → **1897** |

### Power (flying, no kit)
| Consumer | Power |
|---|---|
| 4 motors at hover | ≈ 193 W (≈ 48 W each) |
| Avionics (Pi 5 + Hailo 10 W, FC + GPS + RX 1.8 W, camera 1 W, LiDAR 1.4 W, ESP32 0.8 W, servo + misc 1 W) | **16 W** |
| **Total hover** | **≈ 209 W ≈ 14.5 A at 14.4 V** |
| Mission average (× 1.2) | ≈ 251 W |
| Peak (full throttle) | ≈ 4 × 17 A + 1 A ≈ **70 A** (≈ 1 kW) |

### Savings v1 → v2
| Part | v1 | v2 | Saved |
|---|---|---|---|
| Flight controller (with baro + IMU) | Pixhawk 6C 60 g + PM02 20 g | Matek H743-SLIM 8 g (current sensor in ESC) | **72 g** |
| ESC + distribution | 4 × 30 A = 104 g | 4-in-1 45 A = 25 g | **79 g** |
| GPS | 40 g | 15 g | 25 g |
| LiDAR | 4 × TFmini-S = 20 g | 2 × TFmini-S = 10 g | 10 g |
| ESP32 comms | 20 g | 8 g | 12 g |
| Pi 5 cooling | active fan 70 g total | heatsink 56 g total | 14 g |
| Wiring/plates | 80 g | 50 g | 30 g |
| Frame | 332 g | 300 g | 32 g |
| Small parts (RX, servo, camera mount, BEC) | 50 g | 33 g | 17 g |
| **Everything except motors, props, battery** | **818 g** | **527 g** | **291 g** |

The motors and props got heavier (340 → 400 g) on purpose: bigger props are what make 30+ min possible.

---

## 4. Lighter sensors: the barometer question

**The lightest barometer is the one that's already on the flight controller.**
The Matek H743-SLIM carries a DPS310 barometer and the IMU (accelerometer + gyro) on an 8 g board. A separate
barometer breakout (BMP390/DPS310, ≈ 1 g) would only duplicate it.

| Option | Mass | Notes |
|---|---|---|
| Pixhawk 6C (v1) | ≈ 60 g + 20 g power module | Redundant IMUs, metal case, isolated IMU. Heavy |
| **Matek H743-SLIM (v2)** | **≈ 8 g** | IMU + baro on board, ArduPilot supported. Needs soft-mounting (dampers) |
| ESP32 as flight controller | ≈ 8 g + sensor breakouts | ✘ No proven firmware or failsafes. Not recommended |

**Trade-offs of going light (honest list):**
- The Matek board has less vibration isolation than a Pixhawk. **Mitigation:** soft-mount it on dampers (in item 16).
- Dropping the side LiDARs leaves the drone blind to the sides. **Mitigation:** in survey flight the drone moves forward, so the front LiDAR + camera + planned map cover it. Add 2 more TFmini-S (+10 g, ≈ −0.3 min) if you fly near walls or trees.
- A Pi 5 without a fan can slow itself down when hot. **Mitigation:** mount the heatsink in the prop wash, watch `vcgencmd measure_temp`, and add a 5 g fan if it throttles on the bench.

---

## 5. Battery choice (pick C, no kit)

Mission time = usable energy (80 %) / (hover power × 1.2).

| Battery | Mass | AUW | TWR | Energy | Hover power | Hover time | **Mission time** |
|---|---|---|---|---|---|---|---|
| LiPo 4S 6000 | 640 g | 1567 g | 3.32 | 89 Wh | 173 W | 24.6 min | 20.5 min ✘ |
| LiPo 4S 10000 | 830 g | 1757 g | 2.96 | 148 Wh | 203 W | 35.0 min | 29.2 min ✘ |
| Li-ion 4S2P P45B | 590 g | 1517 g | 3.43 | 130 Wh | 166 W | 37.5 min | 31.2 min (no margin) |
| **Li-ion 4S3P P45B** | **870 g** | **1797 g** | **2.89** | **194 Wh** | **209 W** | **44.6 min** | **37.2 min ✔** |

- **Li-ion 4S3P** is the pick. It's the only option that stays above 30 min with a margin, even with a kit or some extra sensors.
- 4S2P only just passes. Any extra weight or wind pushes it under 30 min.
- **Li-ion care:** it delivers less burst power than LiPo, so the drone is less punchy. That's fine for a survey drone: 23 A per cell at full throttle is half the P45B's 45 A rating. Land at 3.2 V per cell.

---

## 6. The payload: keep it or remove it? (objective view)

**What it is for:** F7 "deliver supplies" (S-30) is a scored requirement. Off-target delivery is a penalty, and
the mission is a *recon & support* drone. The delivery is half of the "support" part.

**What it costs (computed, Li-ion 4S3P):**
| Kit mass | Mission time | Cost |
|---|---|---|
| 0 g | 37.2 min | — |
| 100 g | 34.5 min | −2.7 min |
| 150 g | 33.2 min | −4.0 min |

And the cost only applies **until the drop**. After delivery the drone flies at 0-g kit weight.

**My view:**
- **You're right for the real build.** F7 is judged in the **simulation**. The real drone is only judged on F12 (the comms board), so a heavy kit buys no points there.
- **I'd keep the 12 g servo + hook.** It's cheap, and it lets you show a real drop in the demo video, which is a strong visual for the jury.
- **I'd remove the kit from the design weight** (done: the reference AUW is now 1797 g without a kit). Carry a light kit (≤ 100 g: compression bandage + emergency blanket) only for delivery demos.
- **In the simulation the kit stays.** It costs nothing there and F7 is scored.

---

## 7. Camera footprint and survey altitude (for the coverage planner)

Camera Module 3 Wide, 102° horizontal FOV, YOLO input 640 px wide:

| Altitude | Ground swath | cm / px | Person 1.7 m | Sea mine 1 m | Weapon 0.3 m |
|---|---|---|---|---|---|
| 10 m | 24.7 m | 3.9 | 44 px | 26 px | 8 px |
| **15 m** | **37.0 m** | **5.8** | **29 px** | **17 px** | 5 px ✘ |
| 20 m | 49.4 m | 7.7 | 22 px | 13 px | 4 px ✘ |

- YOLO needs about ≥ 15 px per object. **15 m** works for people and mines, with lanes ≈ 30 m apart (20 % overlap).
- **Weapons are too small at that height.** Use tiled inference (1280 px → 2 × 640), or descend to 6–8 m over spots flagged in the first pass.
- Coverage per battery: ≈ 30 min of survey at 5 m/s ≈ 9 km of path × 30 m lanes ≈ **27 ha**.

---

## 8. Calculations (deck formulas)

**Thrust-to-weight (slide 10):**
```
TWR = total thrust / total weight = 4 × 1.3 kg / 1.797 kg = 2.89   (target > 2)
```

**ESC rating (slide 15):**
```
motor max ≈ 17 A × 1.25 = 21 A  →  45 A 4-in-1 (smallest common size with a current sensor)
```

**Hover power (slides 12–13, P = T × v):**
```
T per motor = 1.797 × 9.81 / 4          = 4.41 N
A (13" disk) = π × 0.165²                = 0.0856 m²
v            = √(T / (2 ρ A))            = √(4.41 / (2 × 1.225 × 0.0856)) = 4.58 m/s
P ideal      = T × v                     = 20.2 W per motor
P electrical = 20.2 / (FM 0.55 × motor 0.80 × ESC 0.95) ≈ 48 W per motor
Total        = 4 × 48 + 16 W avionics    ≈ 209 W
```
FM 0.55 is a conservative propeller efficiency. Real hobby setups usually do a bit better.

**Flight time (slide 11):**
```
Energy        = 13.5 Ah × 14.4 V = 194 Wh  →  80 % usable = 155.5 Wh
Hover time    = 155.5 / 209 × 60      ≈ 44.6 min
Mission time  = 155.5 / (209 × 1.2) × 60 ≈ 37.2 min
```

**Old configs under the same model** (LiPo 4S 6000 + 150 g kit): deck A (2212/8045) TWR 1.83, mission 10.1 min ·
v1 B (2216/1045) TWR 2.26, mission 11.7 min. Neither can reach 30 min.

**Deck errors (kept for the record):**
- Slide 10 mixes 2 kg and 1.3 kg, and 1.2 kg and 0.85 kg per motor (3.4 / 1.3 = 2.62, not 2.46).
- Slide 11 mixes 220 W and 175.84 W. With 220 W the answer is 24.2 min × 80 % = 19.4 min.

---

## 9. Ground equipment (not on the drone)
| Item | Pick | Why |
|---|---|---|
| RC transmitter | RadioMaster Pocket / Boxer, ExpressLRS | Safety pilot override |
| Ground comms node | 2nd XIAO ESP32-S3 + Wio-SX1262 → laptop (USB) | Ground end of the LoRa link |
| Ground station | Laptop: dashboard + Mission Planner / QGroundControl | Telemetry, mission view |
| Charger | Balance charger 4S, ≥ 100 W, with a Li-ion mode (e.g. ISDT 608AC) | Li-ion charges to 4.2 V/cell like LiPo, but needs its own current limit |
| Safety | Battery bag, voltage checker, spare props, sand bucket | Battery fire risk |

## 10. Checks before buying
- [ ] Motor thrust table for the exact 3508 ~700KV on 4S with 13 × 4.4 props: max ≥ 1.3 kg, ≤ 17 A, ≈ 9 g/W near 450 g.
- [ ] Get the Li-ion pack spot-welded, not soldered. Weigh it, then re-run `docs/hardware_calc.py`.
- [ ] Bench-test the Pi 5 + Hailo for 30 min with the heatsink only. Check temperature and throttling.
- [ ] Confirm the Matek H743-SLIM ↔ Pi 5 UART link (3.3 V, MAVLink) and that the frame fits 13" props.
- [ ] Check local drone rules (registration, max altitude, flight zones) before flying outside.
