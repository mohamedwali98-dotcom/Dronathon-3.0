"""Hardware budget for the SKYFORGE real-drone build (F12 bonus).

Reproduces every number in HARDWARE_COMP.md:  python docs/hardware_calc.py
Method = the team deck's formulas (TWR, Wh / W, P = T * v) with v from momentum theory.
"""
import math

G, RHO = 9.81, 1.225               # gravity, sea-level air density (kg/m^3)
FM, ETA_MOTOR, ETA_ESC = 0.55, 0.80, 0.95   # prop figure of merit, motor, ESC (conservative)
USABLE = 0.80                      # use 80 % of the pack (deck rule; keeps the RTH reserve)
MISSION_FACTOR = 1.20              # mission power = 1.2 x hover (wind, climbs, manoeuvres)
TARGET_MIN = 30                    # owner requirement: >= 30 min of mission

# Pick C — light, long-endurance build. Mass in g, avionics power in W.
PARTS_C = [  # (group, item, qty, unit mass g, power W while flying)
    ("Frame", "550 mm carbon frame + landing gear", 1, 300, 0),
    ("Propulsion", "3508 ~700KV motor", 4, 85, None),          # power from hover model
    ("Propulsion", "13x4.4 carbon prop", 4, 15, 0),
    ("Propulsion", "4-in-1 ESC 45 A (current sensor)", 1, 25, 0),
    ("Flight", "Matek H743-SLIM FC (IMU + DPS310 baro)", 1, 8, 1.0),
    ("Flight", "M10 GPS + compass, mini (Matek M10Q-5883)", 1, 15, 0.5),
    ("Flight", "ELRS receiver", 1, 3, 0.3),
    ("Compute", "Raspberry Pi 5 8 GB (heatsink, no fan)", 1, 56, 8.0),
    ("Compute", "AI HAT+ Hailo-8L", 1, 20, 2.0),
    ("Sensors", "Camera Module 3 Wide + mount", 1, 10, 1.0),
    ("Sensors", "TFmini-S LiDAR (down + front)", 2, 5, 0.7),
    ("Comms", "XIAO ESP32-S3 + Wio-SX1262 LoRa", 1, 8, 0.8),
    ("Comms", "ATECC608B secure element", 1, 2, 0.0),
    ("Power", "5 V 5 A BEC", 1, 8, 0.0),
    ("Delivery", "SG90 servo + printed hook", 1, 12, 0.5),
    ("Misc", "wiring, XT60, dampers, straps, buzzer/LED", 1, 50, 0.5),
]
PROP_C_IN, THRUST_C_G = 13, 1300   # max thrust per motor, 4S, class value (verify!)

# Battery options: name, Ah, nominal V, mass g (Li-ion = Molicel P45B 21700, 70 g/cell + 30 g nickel/wires)
BATTERIES = [
    ("LiPo 4S 6000", 6.0, 14.8, 640),
    ("LiPo 4S 10000", 10.0, 14.8, 830),
    ("Li-ion 4S2P P45B", 9.0, 14.4, 8 * 70 + 30),
    ("Li-ion 4S3P P45B", 13.5, 14.4, 12 * 70 + 30),
]


def hover_power_w(mass_g, prop_in, avionics_w):
    """P = T * v per motor, v = sqrt(T / (2 rho A)), divided by efficiencies."""
    t = mass_g / 1000 * G / 4
    area = math.pi * (prop_in * 0.0254 / 2) ** 2
    v = math.sqrt(t / (2 * RHO * area))
    return 4 * t * v / (FM * ETA_MOTOR * ETA_ESC) + avionics_w


def times(auw_g, prop_in, avionics_w, ah, volt):
    p = hover_power_w(auw_g, prop_in, avionics_w)
    wh = ah * volt * USABLE
    return p, wh / p * 60, wh / (p * MISSION_FACTOR) * 60


dry = sum(q * m for _, _, q, m, _ in PARTS_C)
avionics = sum(q * w for _, _, q, _, w in PARTS_C if w)
print("== Pick C parts")
groups = {}
for g, item, q, m, w in PARTS_C:
    groups[g] = groups.get(g, 0) + q * m
    print(f"  {g:<10} {item:<45} {q} x {m:>3} g = {q*m:>4} g")
print("  per group:", groups)
print(f"  DRY (no battery, no payload) = {dry} g | avionics power = {avionics:.1f} W\n")

print(f"== Pick C, battery options (no payload) — need mission >= {TARGET_MIN} min")
for name, ah, v, mb in BATTERIES:
    auw = dry + mb
    p, hover, mission = times(auw, PROP_C_IN, avionics, ah, v)
    print(f"  {name:<17} {mb:>4} g  AUW {auw} g  TWR {4*THRUST_C_G/auw:.2f}  {ah*v:.0f} Wh  "
          f"hover {p:.0f} W ({p/v:.1f} A)  hover {hover:.1f} min  mission {mission:.1f} min "
          f"{'OK' if mission >= TARGET_MIN else 'too short'}")

name, ah, v, mb = BATTERIES[3]
print("\n== Payload effect on pick C (Li-ion 4S3P)")
for kit in (0, 100, 150):
    p, hover, mission = times(dry + mb + kit, PROP_C_IN, avionics, ah, v)
    print(f"  kit {kit:>3} g: hover {p:.0f} W  hover {hover:.1f} min  mission {mission:.1f} min")

print("\n== Old configs, same model, with LiPo 4S 6000 + 150 g kit (for comparison)")
for label, dry_old, prop, thrust in (("A deck 2212/8045", 1068, 8, 850), ("B v1 2216/1045", 1158, 10, 1100)):
    auw = dry_old + 640 + 150
    p, hover, mission = times(auw, prop, 21.0, 6.0, 14.8)
    print(f"  {label}: AUW {auw} g  TWR {4*thrust/auw:.2f}  hover {p:.0f} W  "
          f"hover {hover:.1f} min  mission {mission:.1f} min")

print("\n== Camera Module 3 Wide (HFOV 102 deg) at YOLO 640 px")
for h in (10, 15, 20):
    w = 2 * h * math.tan(math.radians(51))
    gsd = w / 640 * 100
    print(f"  alt {h} m: swath {w:.1f} m, {gsd:.1f} cm/px -> person {170/gsd:.0f} px, "
          f"mine {100/gsd:.0f} px, weapon {30/gsd:.0f} px")
