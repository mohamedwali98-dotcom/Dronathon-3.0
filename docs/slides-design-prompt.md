# Design brief — SKYFORGE jury presentation (interactive slide deck)

## Attach these files to Claude Design first
1. `UI UX/SKYFORGE Ground Station.html`: the dashboard. Copy the interaction model of its **Documentation** page.
2. `[drone-render.png]`: render of `Hardware/Assem2.SLDASM`, exported from SolidWorks on a transparent background.
3. `[webots-mission.png]`: clean screenshot of the 3D mission in Webots.
4. `[dashboard-maps.png]`: screenshot of the 4 detection maps.

If a file is missing, leave a clearly labelled drop zone. Do not generate a fake drone or fake screenshots.

## Context
SKYFORGE is an autonomous recon and medical-support drone, fully simulated in 3D (Webots), built for the
IEEE AESS/RAS ENSIT Dronathon 3.0 in Tunis. With zero human input it explores a coastal zone, maps mines,
weapons, marine litter and injured people, ranks the injured by medical urgency, drops simulated medical kits,
survives radio cuts and returns home.
No weapons on board. Hostile units are zones to avoid, never targets.

**Audience:** a technical jury in a room, on a projector, followed by questions.
**Goal:** they should remember that every engineering choice has a reason and a number behind it.

## Deliverable
One self-contained, offline-capable HTML deck, 16:9, designed at 1920×1080 and scaled to fit any screen.
17 slides in 5 acts. Language: English. Mission phase names stay in French, as in the spec
(INIT, EXPLORER, DÉTECTER, TRIAGE, NAVIGUER, LIVRER, RETOUR BASE, POSÉ).

**Accuracy rule:** use only the numbers in this brief. Never invent or round up a metric. Values in `[brackets]`
are placeholders: keep them visibly editable, in one `DATA` object at the top of the file, so a number can be
changed in one place. Keep the status labels exactly as written (calculated, simulated, interim, planned).

## Visual system: strictly 2 colors
| Role | Value | Use |
|---|---|---|
| Color 1: Ink | `#0B0F14` | Background, and text on cyan fills |
| Color 2: Signal cyan | `#62D6E8` | Text, lines, data, highlights, active state |
| White | `#FFFFFF` | **Last resort only**, when something is unreadable otherwise, such as a label over the 3D render |

- Tints and opacities of these two colors are allowed. No third hue anywhere: no green, red, amber, purple or gradient to another hue.
- The dashboard's colored status coding does **not** apply here. Show status through shape and fill:
  filled = reached or active, outlined = planned or pending, hatched = danger or no-go zone,
  dashed = predicted or not yet measured. Always add a text label, never rely on the mark alone.
- Render the 3D model and screenshots as an ink/cyan duotone so images obey the palette.
- Charts use cyan only, with opacity steps and patterns to separate series.
- Type, same as the dashboard: **Barlow Semi Condensed** for headings, **Barlow** for body, **JetBrains Mono** for
  numbers and equations. Embed the fonts or provide offline fallbacks.
- Mission-control feel: faint grid, thin lines, calm and precise, lots of empty space. No glow and no decorative icons.
- One idea per slide. Headlines state the takeaway, not the topic. Max about 40 words of visible body text,
  excluding labels and data. Details go in click-to-open panels, like the Documentation page.
- Minimum text size 24 px at 1920×1080, so it reads on a projector.

## Interaction and navigation (same model as the dashboard's Documentation page)
- Collapsible left **Sommaire** rail listing acts and slides, with the current slide highlighted. A progress line
  runs along the bottom.
- `←` `→` `Space`, click, swipe and number keys to navigate. `O` overview grid, `F` fullscreen, `N` presenter notes,
  `/` search across slides. Each slide has its own URL hash.
- Clickable blocks open a side panel with role, inputs and outputs, limits. Sliders and steppers run on real formulas.
- Every widget has a sensible default that already makes the point, so nothing needs clicking to be understood.
- A **Reset** on each widget. Everything works with the mouse and the keyboard.
- Include print-to-PDF styles showing each slide's default state.

## Transitions (the signature of the deck)
- **One continuous camera, no slide-flip effects.** A persistent thread, the drone's flight path, is drawn across the
  whole deck and moves forward with each slide.
- Use shared-element morphs: an element in the next slide grows out of the one in the current slide. Examples: the motor
  hotspot on slide 2 becomes the thrust term on slide 3, and the LiDAR hotspot on slide 5 becomes the 1 m ring on slide 12.
- 500–700 ms with soft easing. Inside a slide, elements build in sequence with a short stagger.
- Must stay smooth at 60 fps: animate transform and opacity only, with no layout shift.
- A fast double-press never breaks the state. `prefers-reduced-motion` switches to a short fade.

---

# Slides

## Act 0 — Mission
**1. Title.** "SKYFORGE: an autonomous drone that finds, ranks and helps." Thin flight path drawing itself over a
faint coastline. Dronathon 3.0, IEEE AESS/RAS ENSIT, 07–08 Nov 2026.
Team: `[Mohamed Anwer Guemri, Mohamed Wali, Ahmed Smida: confirm]`.

## Act 1 — Hardware: one 40-second story
Slides 2–5 tell one story: **"We needed 30 minutes in the air. Each part exists because of that."**
Add an **"Auto-story" mode** that plays them in 40 s (about 10 s each) with a thin timeline at the top,
reading *Shape → Balance → Parts → Senses*. Any key or click pauses it. Also fully steppable by hand.
Label this slide group: **"Real-drone design, calculated. The competition mission itself is simulated."**

**2. Shape: the 3D model.** The image fills about 80 % of the slide; this slide is mostly the picture.
Slow turntable or parallax if possible. 3 big numbers only: **1.80 kg** all-up weight · **TWR 2.89** · **≈ 37 min** mission.
Hotspots on the model open small cards: frame, motor, propeller, battery, camera, LiDAR.
Do not print dimensions on the model image.

**3. Balance: stability equations.** Headline: "It hovers with 65 % of its thrust in reserve." Four equations in mono;
clicking one highlights the matching forces on a simple drone outline.
```
Hover:            4T = mg              ->  T = 1.797 × 9.81 / 4 = 4.41 N per motor (450 g)
Thrust margin:    TWR = ΣTmax / W      ->  4 × 1.3 kg / 1.797 kg = 2.89   (target > 2)
Centre of gravity: x_cg = Σ(mᵢ·xᵢ) / Σmᵢ   ->  CG = [x, y, z from SolidWorks Mass Properties on Assem2]
Moment balance:   ΣM = 0   ->  CG over the centre of thrust, so the 4 motors share the load equally
```
Motor max thrust = 12.75 N, so the reserve is 1 − 4.41 / 12.75 = 65 %.
Why it matters, in 3 short tags: wind, battery sag, payload drop.
Footer: "Control: PD attitude and velocity loops correct what remains."

**4. Parts: every reference has a reason.** Horizontal timeline of decisions; each node opens on click, with the
active one expanded by default.
| Step | Choice | Why this one | Mass |
|---|---|---|---|
| Frame | 550 mm carbon quad | Stiffer and lighter than the F450 (332 g); fits 13" props (389 mm motor spacing, 330 mm prop) | 300 g |
| Motors | 3508 ~700 KV on 4S (e.g. T-Motor MN3508 KV700) | Made for 12–14" props, efficient at low throttle (≈ 9 g/W), ≈ 1.3 kg max thrust each | 4 × 85 g |
| Propellers | 13 × 4.4 carbon | Large disk moves more air slowly: P = T·v, and v drops as the disk grows. 48 W per motor at hover | 4 × 15 g |
| ESC | 4-in-1 45 A, BLHeli_32/AM32 | Replaces 4 ESCs + the PDB (104 g → 25 g); built-in current sensor; 17 A × 1.25 = 21 A | 25 g |
| Battery | **Li-ion 4S3P**, Molicel P45B 21700, 13.5 Ah, 194 Wh | ≈ 220 Wh/kg vs ≈ 140 Wh/kg for LiPo. Max draw 23 A per cell, rated 45 A | 870 g |
| Brain | Matek H743-SLIM + ArduPilot; Raspberry Pi 5 8 GB + Hailo-8L 13 TOPS | FC carries IMU + baro in 8 g instead of ≈ 60 g; Hailo runs YOLO in real time | 8 + 76 g |

Story beat, the turning point: **"LiPo gave ≈ 12 min. Li-ion + big props + lighter avionics gave ≈ 37 min."**
Avionics and structure dropped by 291 g (818 → 527 g).

**Widget: battery switcher** (table values, not recalculated). Changing the battery visibly fails or passes a 30-minute line:
| Battery | Mass | AUW | TWR | Energy | Mission |
|---|---|---|---|---|---|
| LiPo 4S 6000 | 640 g | 1567 g | 3.32 | 89 Wh | 20.5 min — fails |
| LiPo 4S 10000 | 830 g | 1757 g | 2.96 | 148 Wh | 29.2 min — fails |
| Li-ion 4S2P | 590 g | 1517 g | 3.43 | 130 Wh | 31.2 min — no margin |
| **Li-ion 4S3P** | 870 g | 1797 g | 2.89 | 194 Wh | **37.2 min — chosen** |

Kit toggle: 0 g = 37.2 min · 100 g = 34.5 min · 150 g = 33.2 min.
Formula: mission = 80 % usable energy / (hover power × 1.2) = 155.5 Wh / (209 W × 1.2).

**5. Senses: what the drone perceives.** Drone outline with the sensors lighting up one at a time; total mass only 20 g
for camera + LiDARs.
| Sensor | Reference | Gives | Mass |
|---|---|---|---|
| Camera | Pi Camera Module 3 Wide, 102° | Detection, ground coverage | 10 g |
| LiDAR ×2 | Benewake TFmini-S, 1 front + 1 down | Front: obstacles. Down: exact altitude, landing, delivery height | 2 × 5 g |
| IMU + barometer | On the flight controller (DPS310) | Attitude; backup altitude, since baro drifts | in FC |
| GPS + compass | Matek M10Q-5883 | Position, heading | 15 g |
| Current sensor | In the ESC | Energy used, feeds the return decision | in ESC |

**Widget: altitude stepper** (10 / 15 / 20 m) showing the camera footprint and pixels on target (YOLO needs ≈ 15 px):
| Altitude | Swath | cm/px | Person | Mine | Weapon |
|---|---|---|---|---|---|
| 10 m | 24.7 m | 3.9 | 44 px | 26 px | 8 px |
| **15 m** | 37.0 m | 5.8 | 29 px | 17 px | 5 px — too small |
| 20 m | 49.4 m | 7.7 | 22 px | 13 px | 4 px — too small |

## Act 2 — Software
**6. Layers.** Headline: "Fast reflexes, deterministic decisions, no LLM in the loop." Clickable stack; each block opens a panel:
- **Reflex**: PD attitude + velocity loop, wind compensation. Budget **< 50 ms**.
- **Deliberative**: LangGraph orchestrator, deterministic nodes (sense → interrupts → phase). Budget **≤ 100 ms**.
- **Agents**: Perception (2 YOLO models, 2D → ground position, filtering) · Planner (A*, triage, coverage, RTH).
- **Shared DroneState**: position, velocity, battery, link, weather, threats, injured, goal, waypoints, logs, phase.
- **Communication module**, deliberately not an agent: compact JSON, ring buffer, resync.
- **Ground station**: dashboard and maps.
Total loop budget **≤ 150 ms at p95**.

**7. System design: follow one detection.** Animated dataflow with a single token travelling along it:
Camera → YOLO main + people → geolocate → on-board SQLite store (objects merged within 3 m) → DroneState → LangGraph →
Planner → Reflex → motors. Branch: Reporter → compact protocol v2 → ring buffer → radio → ground receiver → dashboard.
Stack chips: Webots R2025a · Python 3.12 · LangGraph · Ultralytics YOLO11n · SQLite · Docker (`docker compose up`).
ROS2 packaging is **planned**: draw it outlined.
Quality line: **76 automated tests passing.**

**8. Mission logic.** Step-through state machine:
INIT → EXPLORER → DÉTECTER → TRIAGE → NAVIGUER → LIVRER → (TRIAGE | RETOUR BASE) → POSÉ.
Three interrupt buttons animate an override: low battery → RETOUR BASE · link lost → autonomous mode · `goal_update` → reroute.

## Act 3 — Models and rules
**9. Data.** Two pipelines side by side. Split 70/20/10 with train-only augmentation imitating drone conditions: altitude,
top-down rotation, motion blur, haze, glare, noise.
- **Main** (mine, weapon, litter): 8499 / 2445 / 1224 images. Train boxes: mine 1076 · weapon 7394 · litter 5641.
  Show this imbalance plainly.
- **People** (injured, healthy): 1433 / 396 / 208 images.
- 119 boat and ship images removed from the mines set. Same-photo copies stay in the same split, so no train/test leakage.

**10. Model statistics.** Both models are YOLO11n at 640 px.
**People: final, test set, 60 epochs** (bar chart per class):
| Class | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| all | 0.832 | 0.656 | 0.782 | 0.504 |
| injured | 0.814 | 0.705 | 0.800 | 0.542 |
| healthy | 0.850 | 0.607 | 0.764 | 0.466 |
Inference 6.1 ms per image on an RTX 3050.

**Main: INTERIM, validation set, stopped at epoch 4 of 40, drawn dashed:**
best epoch so far P 0.624 · R 0.453 · mAP50 0.493 · mAP50-95 0.223. No per-class figures yet.
`[Replace with final test metrics per class after training finishes.]`
Show the spec target beside it: **accuracy > 90 %, recall first for mines and weapons.** Never present the interim
figure as a final result.

**11. Rules the drone can't break.** A grid of rule cards. Filled = measured in the last 3D run, dashed = target only.
| Rule | Limit | Latest result |
|---|---|---|
| Collisions | 0 | 0 — closest obstacle pass 3.11 m |
| Danger-zone entries | 0 | 0 — closest pass 3.05 m (planner aims for 5 m) |
| Reflex compute | < 50 ms | p95 0.047 ms |
| Decision | ≤ 100 ms | p95 29.01 ms |
| Total loop | ≤ 150 ms p95 | Not yet measured end to end (dashed) |
| Messages | < 1 KB, with version + seq | Enforced and tested |
| Human input | 0 | 0 |
| Payload | No weapon, no dangerous payload | Medical kits only |
| Triage | Medical urgency first | Every decision logged |
| Hostile units | Avoid, never target | Treated as no-go zones |

**12. The 1 m rule: how it works.** Headline: "Never closer than 1 m, and moving obstacles count for where they'll be."
Top-down view with a hatched keep-out ring. **Interactive sliders:** obstacle radius and obstacle speed.
```
keep_out = radius + 0.3 m (drone half-span) + 1.0 m (clearance) + speed × 1 s (prediction)
```
Default examples: radius 2 m, static → 3.3 m · moving at 2 m/s → 5.3 m. Danger zones: radius + 5 m.
Build 4 steps:
1. **Sense:** the front LiDAR reads range ahead on the real drone; the camera and planned map support it.
2. **Inflate:** each zone is blocked on a 2 m occupancy grid, out to its keep-out.
3. **Plan:** A* finds a path around blocked cells, with an exact segment-to-obstacle check.
4. **React:** if a moving obstacle enters the keep-out, replan or step straight away from it.

Numbers: minimum gap **1.01 m** across the full-mission test · 6 obstacle replans in the last 3D run.
Why prediction matters: at 8 m/s the drone travels 1.2 m during one 150 ms loop.

**Required honesty label on this slide:** "In the current simulation, obstacles come from the scene data. The LiDAR
is part of the real-drone design." Do not imply a LiDAR is flying in the simulation.
TFmini-S range `[confirm on the Benewake datasheet]`.

**13. Triage and return home.** Two live calculators, like the dashboard's Documentation page.
- **Triage:** sliders for injury priority (1–10) and path distance.
  `score = 0.8 × priority/10 + 0.2 × (1 − min(d, 300)/300)`. Default: priority 9, 60 m → **0.88**.
  A battery toggle drops the score to **0**, with the reason shown, when go + deliver + return + reserve exceeds the
  battery. Other zero reasons: already served, unreachable, no kits, possibly deceased.
- **Return threshold**, recomputed every cycle:
  `threshold = E_home × 1.2 + E_landing(30 s) + 10 % reserve`, where
  `E_home = Σ (100 W + 0.5·v_air²) × d / 8 m/s`. Sliders: distance, headwind. Battery = 59.3 Wh (simulated Mavic 2 Pro).
  Default 150 m: no wind **7.59 Wh (12.8 %)** → 6 m/s headwind **8.00 Wh (13.5 %)**. Make the marker visibly move.

## Act 4 — Staying connected, and proof
**14. Comms under a radio cut.** Headline: "The radio can drop. The mission doesn't."
**Ring-buffer widget:** press "Cut link", see messages fill slots 1…512, press "Restore", see them resync in order.
Facts: compact numeric protocol v2, every message < 1 KB with `version` + `seq` · ring buffer of **512** messages ·
resync tested after a 30 s cut · `goal_update` with retry and ack · 4 cuts and 4 recoveries in the last 3D run.
Optional real-board bonus F12: XIAO ESP32-S3 + LoRa, **planned**.

**15. Ground Station.** Dashboard screenshot, or embedded live if feasible, with a real-map view at Gammarth beach, Tunis:
4 synced maps (weapons, injured, litter, mines), mission state, telemetry, Documentation page.
Headline: "The operator sees everything, and doesn't need to touch anything."

**16. The full mission: results.** Webots screenshot + a replay timeline.
Landed (POSÉ) after **756.5 s** · **3 / 3 kits delivered** · **61.6 % battery left** (simulated Mavic 2 Pro) ·
**0 collisions** · **0 danger-zone entries** · **4 radio cuts survived** · 6 obstacle replans · 20 logged triage decisions ·
decision p95 **29 ms** · vision p95 **50 ms** · 1413 frames processed.
Detection in the loop: **injured confirmed 4 / 5**. Other objects: `[update after the main model is retrained; last run 0 / 20
matched, 117 false positives]`. Timings were measured on the development PC, not on a Pi.

**17. What's next, and how this maps to the score.** Two columns.
Left, honest limits:
- Main model needs its full 40 epochs, plus top-down training images
- Sim-to-real gap for people (trained on real photos, simulated bodies are often read as "healthy")
- Severity comes from the scenario, since thermal and depth assessment are not simulated yet
- ROS2 packaging; real-board F12

Right, how the work maps to scoring: Autonomy 20 % · Decision intelligence 20 % · Navigation 15 % · Communication and
resilience 15 % · Adaptability 15 % · Overall efficiency 15 % · Bonus F12, each linked to its slide.
End on "Questions?" with the flight path closing its loop back at home base.

---

# Presenter notes
Add 1–3 sentences of speaker notes to every slide (shown with `N`). Write them in plain spoken English.
Include the expected tough question where there is one:
- Slide 2: "Is it built?" → No, the mission is simulated; these are calculated numbers using typical datasheet values.
- Slide 12: "Is there a LiDAR in the simulation?" → No; obstacles come from the scene, and LiDAR is in the real build.
- Slide 10: "Does main reach 90 %?" → Answer from the final numbers.
- Slide 13: "Why does 'possibly deceased' score 0?" → Kits go first to people the drone can still help; explain the medical reasoning and that the status comes from a simulated assessment.

# Done means
- All 17 slides work offline, with no console errors, at 1920×1080 and on a 1366 px laptop.
- A scan of the CSS finds only ink, cyan and last-resort white, including charts and images.
- Slides 2–5 auto-play in 40 s ± 5 s.
- Every widget's default values match this brief exactly: 0.88 · 7.59 Wh / 8.00 Wh · 3.3 m / 5.3 m · 37.2 min.
- Moving through all slides, forward and back, shows no flash, jump or broken state.
