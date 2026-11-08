"""SKYFORGE Webots controller: Mavic 2 Pro flown by our decision stack, zero human input.

Layers (cahier §4):
  reflex   (every 8 ms step)  : attitude + altitude PID (Mavic sample gains) + velocity loop toward the
                                current waypoint; it absorbs the wind force -> wind compensation.
  decision (every 100 ms)     : drone/orchestrator.py LangGraph Mission.cycle() -> sets state.goal.
Perception = oracle (supervisor knows the scene), same as sim/kinematic.py.
The supervisor also moves the moving obstacle, applies wind, and drops the medical kits.
At the end: runs/webots/mission_logs.jsonl + latency p95 printed.
"""
import json, math, os, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(line_buffering=True)      # show progress live in the Webots console
OUT = os.path.join(ROOT, "runs", "webots")
os.makedirs(OUT, exist_ok=True)
_LOG = open(os.path.join(OUT, "progress.log"), "w", encoding="utf-8")


def say(msg):
    print(msg)
    _LOG.write(msg + "\n")
    _LOG.flush()


from controller import Supervisor  # noqa: E402

from drone.orchestrator import Mission  # noqa: E402
from drone.planner import K_DRAG, P_HOVER  # noqa: E402
from drone.state import BATTERY_WH, DroneState  # noqa: E402
from sim.kinematic import oracle  # noqa: E402
from sim.scenario import ALT, MOVER_ID, mover_center, skyforge_world  # noqa: E402

DECISION_DT = 0.1        # s
VMAX = 6.0               # m/s horizontal speed limit
K_POS = 0.6              # position error (m) -> desired speed (m/s)
K_VEL = 0.05             # speed error (m/s) -> tilt angle (rad)
MAX_TILT = 0.10          # rad (~6 deg) -> ~5 m/s with the world linear damping 0.2
TILT_SMOOTH = 0.015      # low-pass on the tilt command per 8 ms step
WIND_N_PER_MS = 0.04     # wind force on the airframe (N per m/s)
T_MAX = float(os.environ.get("SKYFORGE_TMAX", "900"))   # safety cap on simulated time (s)
VISION_DT = 0.5          # s between YOLO frames
MATCH_M = 6.0            # a detection confirms a scene object within this distance
PERCEPTION = os.environ.get("SKYFORGE_PERCEPTION", "yolo")   # yolo: injured must be seen by YOLO | oracle
BOX_RGB = {"injured": 0xFF2020, "healthy": 0x20FF20, "mine": 0xFF8000, "weapon": 0xB040FF, "litter": 0x00E0E0}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Pilot:
    """Reflex layer: Mavic sample attitude PID + altitude PD + horizontal velocity loop (wind rejection)."""
    K_VERTICAL_THRUST, K_VERTICAL_OFFSET, K_VERTICAL_P, K_VERTICAL_D = 68.5, 0.6, 3.0, 2.0
    K_ROLL_P, K_PITCH_P, K_YAW_RATE, K_RATE = 50.0, 30.0, 0.5, 3.0

    def __init__(self, robot, ts):
        dev = robot.getDevice
        self.imu, self.gps, self.gyro = dev("inertial unit"), dev("gps"), dev("gyro")
        for d in (self.imu, self.gps, self.gyro):
            d.enable(ts)
        dev("camera").enable(ts * 8)
        dev("camera pitch").setPosition(1.57)                # look straight down (survey)
        self.motors = [dev(n) for n in ("front left propeller", "front right propeller",
                                        "rear left propeller", "rear right propeller")]
        for m in self.motors:
            m.setPosition(float("inf"))
            m.setVelocity(1.0)
        self.cruising = False                                # latched once cruise altitude is reached
        self.tilt_f = self.tilt_l = 0.0                      # smoothed tilt commands (rad)

    def read(self):
        roll, pitch, yaw = self.imu.getRollPitchYaw()
        x, y, z = self.gps.getValues()
        vx, vy, vz = self.gps.getSpeedVector()
        return (x, y, z), (vx, vy, vz), (roll, pitch, yaw), self.gyro.getValues()

    def stop(self):
        for m in self.motors:
            m.setVelocity(0.0)

    def control(self, goal_xy, alt, pos, vel, att, rates):
        roll, pitch, yaw = att
        self.cruising = self.cruising or pos[2] > alt - 1.0
        want_f = want_l = 0.0
        if goal_xy is not None and self.cruising:
            dx, dy = goal_xy[0] - pos[0], goal_xy[1] - pos[1]
            d = math.hypot(dx, dy)
            sp = min(VMAX, K_POS * d)
            vdx, vdy = (dx / d * sp, dy / d * sp) if d > 1e-6 else (0.0, 0.0)
            c, s = math.cos(yaw), math.sin(yaw)
            ef = (vdx - vel[0]) * c + (vdy - vel[1]) * s        # forward (body x) speed error
            el = -(vdx - vel[0]) * s + (vdy - vel[1]) * c       # left (body y) speed error
            want_f = clamp(K_VEL * ef, -MAX_TILT, MAX_TILT)
            want_l = clamp(K_VEL * el, -MAX_TILT, MAX_TILT)
        self.tilt_f += (want_f - self.tilt_f) * TILT_SMOOTH
        self.tilt_l += (want_l - self.tilt_l) * TILT_SMOOTH
        pitch_d = -self.K_PITCH_P * self.tilt_f                 # negative pitch disturbance = forward
        roll_d = self.K_ROLL_P * self.tilt_l                    # positive roll disturbance = left
        yaw_d = clamp(-self.K_YAW_RATE * rates[2], -1.0, 1.0)   # damp spinning, heading itself is free
        roll_in = self.K_ROLL_P * clamp(roll, -1, 1) + self.K_RATE * rates[0] + roll_d
        pitch_in = self.K_PITCH_P * clamp(pitch, -1, 1) + self.K_RATE * rates[1] + pitch_d
        vert = (self.K_VERTICAL_P * clamp(alt - pos[2] + self.K_VERTICAL_OFFSET, -1, 1) ** 3
                - self.K_VERTICAL_D * clamp(vel[2], -2, 2))
        base = self.K_VERTICAL_THRUST + vert
        fl = base - yaw_d + pitch_in - roll_in
        fr = base + yaw_d + pitch_in + roll_in
        rl = base + yaw_d - pitch_in - roll_in
        rr = base - yaw_d - pitch_in + roll_in
        for m, v in zip(self.motors, (fl, -fr, -rl, rr)):
            m.setVelocity(v)


def p95(xs):
    xs = sorted(xs)
    return xs[int(0.95 * (len(xs) - 1))] if xs else 0.0


class Eyes:
    """PerceptionAgent in the sim: camera -> YOLO -> ground position -> confirm scene objects.
    Mode yolo: an injured person enters the mission only once YOLO has seen it (oracle gives severity).
    Danger zones and obstacles always come from the oracle (safety: never fly into an unseen mine)."""

    def __init__(self, robot, world, perceive):
        import numpy as np
        from vision.onboard import OnboardVision
        self.np, self.world, self.base_perceive = np, world, perceive
        self.cam, self.disp = robot.getDevice("camera"), robot.getDevice("yolo")
        self.w, self.h = self.cam.getWidth(), self.cam.getHeight()
        self.hfov = math.degrees(self.cam.getFov())
        if self.disp:
            self.disp.attachCamera(self.cam)
        self.v = OnboardVision()
        self.confirmed, self.obj_seen = set(), set()
        self.ms, self.counts, self.false_pos, self.saved = [], {}, 0, {}
        os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
        self.log = open(os.path.join(OUT, "detections.jsonl"), "w", encoding="utf-8")

    def _match(self, d):
        if d.cls in ("injured", "healthy"):
            cands = [(math.dist(d.xy, c.pos), ("cas", c.id)) for c in self.world.casualties]
        else:
            cands = [(math.dist(d.xy, xy), ("obj", i)) for i, (cls, xy) in enumerate(self.world.objects) if cls == d.cls]
        best = min(cands, default=(math.inf, None))
        return best[1] if best[0] <= MATCH_M else None

    def look(self, pos, yaw, t):
        img = self.np.frombuffer(self.cam.getImage(), self.np.uint8).reshape(self.h, self.w, 4)[:, :, :3].copy()
        dets = self.v.detect(img, pos, yaw - math.pi / 2, self.hfov)    # geolocate: yaw 0 = north
        self.ms.append(self.v.last_ms)
        if self.disp:
            self.disp.setAlpha(0.0)
            self.disp.fillRectangle(0, 0, self.w, self.h)
            self.disp.setAlpha(1.0)
        for d in dets:
            self.counts[d.cls] = self.counts.get(d.cls, 0) + 1
            m = self._match(d)
            if m is None:
                self.false_pos += 1
            elif m[0] == "cas" and m[1] not in self.confirmed:
                self.confirmed.add(m[1])
                say(f"[SKYFORGE] t={t:6.1f}s  YOLO confirmed injured #{m[1]} ({d.cls} {d.conf:.2f}) "
                    f"at ({d.xy[0]:.1f}, {d.xy[1]:.1f})")
            elif m[0] == "obj":
                self.obj_seen.add(m[1])
            self.log.write(json.dumps({"t": round(t, 2), "cls": d.cls, "conf": round(d.conf, 2),
                                       "xy": [round(d.xy[0], 1), round(d.xy[1], 1)], "match": m}) + "\n")
            x1, y1, x2, y2 = map(int, d.box)
            if self.disp:
                self.disp.setColor(BOX_RGB.get(d.cls, 0xFFFFFF))
                self.disp.drawRectangle(x1, y1, x2 - x1, y2 - y1)
                self.disp.drawText(f"{d.cls} {d.conf:.2f}", x1, max(0, y1 - 10))
        if dets and min(self.saved.get(d.cls, 0) for d in dets) < 3:      # keep a few example frames
            import cv2
            for d in dets:
                x1, y1, x2, y2 = map(int, d.box)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(img, f"{d.cls} {d.conf:.2f}", (x1, max(12, y1 - 4)), 0, 0.5, (0, 0, 255), 1)
                self.saved[d.cls] = self.saved.get(d.cls, 0) + 1
            cv2.imwrite(os.path.join(OUT, "frames", f"t{t:06.1f}_{dets[0].cls}.jpg"), img)

    def perceive(self, s):
        zones, cas = self.base_perceive(s)
        if PERCEPTION == "yolo":
            cas = [c for c in cas if c.id in self.confirmed]
        return zones, cas

    def stats(self):
        return {"perception": PERCEPTION, "frames": len(self.ms), "vision_p95_ms": round(p95(self.ms), 1),
                "detections": self.counts, "false_positives": self.false_pos,
                "injured_confirmed": f"{len(self.confirmed)}/{len(self.world.casualties)}",
                "objects_confirmed": f"{len(self.obj_seen)}/{len(self.world.objects)}"}


def main():
    robot = Supervisor()
    ts = int(robot.getBasicTimeStep())
    dt = ts / 1000.0
    pilot = Pilot(robot, ts)
    world = skyforge_world()
    me = robot.getSelf()
    mover = robot.getFromDef("MOVER")
    kids = robot.getRoot().getField("children")

    s = DroneState(pos=(world.base[0], world.base[1], 0.0), battery_wh=BATTERY_WH)
    s.weather.wind = world.wind
    eyes = Eyes(robot, world, oracle(world)) if PERCEPTION == "yolo" else None
    cam = robot.getDevice("camera")
    swath = 0.85 * 2 * ALT * math.tan(cam.getFov() / 2)          # lane spacing = camera footprint, 15 % overlap
    mission = Mission(s, world.bounds, world.base, eyes.perceive if eyes else oracle(world), swath=swath)
    say(f"[SKYFORGE] perception={PERCEPTION}  lane spacing={swath:.1f} m")
    reflex_ms, decision_ms = [], []
    next_decision, kits, hold, landed_at, next_status, next_look = 0.0, s.kits, None, None, 0.0, 0.0
    min_obst = min_zone = math.inf
    say("[SKYFORGE] mission start, zero human input")

    while robot.step(ts) != -1:
        t = robot.getTime()
        pos, vel, att, rates = pilot.read()
        s.t, s.pos, s.vel = t, pos, vel

        # world: moving obstacle, wind, radio shadow
        for z in world.zones:
            if z.id == MOVER_ID:
                z.center = mover_center(world, MOVER_ID, t)
                if mover:
                    mover.getField("translation").setSFVec3f([z.center[0], z.center[1], 15.0])
            if z.kind == "obstacle":
                min_obst = min(min_obst, math.dist(pos[:2], z.center) - z.radius - 0.3)
            elif z.kind != "radio_shadow":
                min_zone = min(min_zone, math.dist(pos[:2], z.center) - z.radius)
        me.addForce([WIND_N_PER_MS * world.wind[0], WIND_N_PER_MS * world.wind[1], 0.0], False)
        s.link_ok = not any(z.kind == "radio_shadow" and math.dist(pos[:2], z.center) <= z.radius
                            for z in world.zones)

        # battery (same energy model as the planner)
        air = math.hypot(vel[0] - world.wind[0], vel[1] - world.wind[1])
        s.battery_wh -= (P_HOVER + K_DRAG * air ** 2) * dt / 3600

        # perception: YOLO on the down-looking camera
        if eyes and pilot.cruising and s.phase not in ("INIT", "POSE") and t >= next_look:
            next_look = t + VISION_DT
            eyes.look(pos, att[2], t)

        # decision layer
        if t >= next_decision and (s.phase == "INIT" or pilot.cruising):
            next_decision = t + DECISION_DT
            phase0 = s.phase
            t0 = time.perf_counter()
            mission.cycle(DECISION_DT)
            decision_ms.append((time.perf_counter() - t0) * 1000)
            if s.phase != phase0:
                say(f"[SKYFORGE] t={t:6.1f}s  {phase0} -> {s.phase}  bat={100*s.battery_wh/BATTERY_WH:.0f}%"
                      f"  link={'ok' if s.link_ok else 'LOST'}")

        # medical kit release (F7): drop a box under the drone
        if s.kits < kits:
            kits = s.kits
            kids.importMFNodeFromString(-1, (
                f'Solid {{ translation {pos[0]} {pos[1]} {pos[2] - 0.5} name "kit {kits}" children [ Shape {{ '
                'appearance PBRAppearance { baseColor 1 1 1 roughness 1 metalness 0 } geometry Box { size 0.3 0.3 0.2 } } ] '
                'boundingObject Box { size 0.3 0.3 0.2 } physics Physics { mass 0.15 } }'))
            say(f"[SKYFORGE] t={t:6.1f}s  kit dropped at ({pos[0]:.1f}, {pos[1]:.1f}), {kits} left")

        # reflex layer
        if s.goal is not None:
            hold = None
            goal = s.goal
        else:
            hold = hold or pos[:2]
            goal = hold
        alt = ALT
        if s.phase == "POSE":
            goal, alt = world.base, 0.0
            if pos[2] < 0.3:
                landed_at = landed_at or t
        t0 = time.perf_counter()
        if landed_at:
            pilot.stop()
        else:
            pilot.control(goal, alt, pos, vel, att, rates)
        reflex_ms.append((time.perf_counter() - t0) * 1000)

        if t >= next_status:
            next_status = t + float(os.environ.get("SKYFORGE_STATUS_S", "10"))
            say(f"[SKYFORGE] t={t:6.1f}s {s.phase:<11} pos=({pos[0]:6.1f},{pos[1]:6.1f},{pos[2]:5.1f}) "
                  f"goal={None if s.goal is None else tuple(round(v, 1) for v in s.goal)} yaw={att[2]:.2f} rp=({att[0]:.2f},{att[1]:.2f}) "
                  f"v={math.hypot(vel[0], vel[1]):.1f}m/s")
        if (landed_at and t - landed_at > 2.0) or t > T_MAX:
            break

    served = sum(c.served for c in s.casualties)
    summary = {"phase": s.phase, "t_s": round(t, 1), "battery_pct": round(100 * s.battery_wh / BATTERY_WH, 1),
               "casualties_served": served, "kits_left": s.kits,
               "min_obstacle_clearance_m": round(min_obst, 2), "min_danger_zone_clearance_m": round(min_zone, 2),
               "reflex_p95_ms": round(p95(reflex_ms), 3), "decision_p95_ms": round(p95(decision_ms), 2)}
    if eyes:
        summary.update(eyes.stats())
    out = OUT
    with open(os.path.join(out, "mission_logs.jsonl"), "w", encoding="utf-8") as f:
        for e in s.mission_logs:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    say("[SKYFORGE] MISSION COMPLETE " + json.dumps(summary))
    if os.environ.get("SKYFORGE_QUIT") == "1":
        robot.simulationQuit(0)


main()
