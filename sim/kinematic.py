"""Lightweight 2D mission simulator with oracle perception (no Webots needed).

Used to test the whole decision stack end to end before the Webots world exists.
The drone is a point at fixed altitude moving at cruise speed toward `state.goal`
(the reflex layer is assumed to compensate the wind); battery drains with the planner's energy model.
Oracle perception = every object within SENSOR_M of the drone is reported (stands in for vision/).
"""
import math, time
from dataclasses import dataclass, field

from comms.geo import load_origin
from comms.link import Channel, DroneLink, GroundStation
from drone.orchestrator import Mission
from drone.reporter import Reporter
from drone.store import MissionStore
from ground.receiver import GroundView
from drone.planner import K_DRAG, P_HOVER, SPEED
from drone.state import BATTERY_WH, Casualty, DroneState

SENSOR_M = 25.0        # camera ground footprint radius at 20 m altitude


@dataclass
class World:
    bounds: tuple
    base: tuple
    wind: tuple = (0.0, 0.0)
    casualties: list = field(default_factory=list)
    zones: list = field(default_factory=list)
    objects: list = field(default_factory=list)   # [(cls, (x, y))] weapon / litter / mine props


def oracle(world):
    def perceive(s):
        p = s.pos[:2]
        zones = [z for z in world.zones if z.kind != "radio_shadow" and math.dist(p, z.center) - z.radius <= SENSOR_M]
        cas = [Casualty(c.id, c.pos, c.severity, c.priority, c.status) for c in world.casualties
               if math.dist(p, c.pos) <= SENSOR_M]
        return zones, cas
    return perceive


def run_mission(world, battery_wh=BATTERY_WH, goal_updates=None, dt=0.1, t_max=3000.0,
                store_path=None, link=False, ground_path=":memory:"):
    s = DroneState(pos=(world.base[0], world.base[1], 20.0), battery_wh=battery_wh)
    s.weather.wind = world.wind
    m = Mission(s, world.bounds, world.base, oracle(world))
    goal_updates = dict(goal_updates or {})
    stats = {"cycle_ms": [], "min_zone_clearance": math.inf, "closest_to": {g: math.inf for g in goal_updates.values()}}
    rep = None
    if store_path:
        ch = Channel()
        view = GroundView(ground_path)
        ground, dlink = GroundStation(ch, on_message=view.ingest), DroneLink(ch)
        rep = Reporter(MissionStore(store_path), dlink, load_origin(), base_xy=world.base)
        stats.update(channel=ch, ground=view, store=rep.store)

    def comms(t):
        ch.up = s.link_ok if link else True
        p = s.pos[:2]
        rep.observe([(c, xy, 0.9) for c, xy in world.objects if math.dist(p, xy) <= SENSOR_M],
                    [c for c in world.casualties if math.dist(p, c.pos) <= SENSOR_M], t)
        rep.tick(s, t)
        ground.step(t)
        rep.on_messages(dlink.poll(t))
    while s.phase != "POSE" and s.t < t_max:
        s.t = round(s.t + dt, 3)
        for tg in [k for k in goal_updates if k <= s.t]:
            m.inbox.append(goal_updates.pop(tg))
        s.link_ok = not any(z.kind == "radio_shadow" and math.dist(s.pos[:2], z.center) <= z.radius for z in world.zones)

        t0 = time.perf_counter()
        m.cycle(dt)
        stats["cycle_ms"].append((time.perf_counter() - t0) * 1000)

        x, y, z = s.pos
        if s.goal is not None:
            d = math.dist((x, y), s.goal)
            step = min(SPEED * dt, d)
            ux, uy = ((s.goal[0] - x) / d, (s.goal[1] - y) / d) if d > 1e-9 else (0.0, 0.0)
            s.pos, s.vel = (x + ux * step, y + uy * step, z), (ux * SPEED, uy * SPEED, 0.0)
            air = math.hypot(SPEED * ux - world.wind[0], SPEED * uy - world.wind[1])
            power = P_HOVER + K_DRAG * air ** 2
        else:
            s.vel = (0.0, 0.0, 0.0)
            power = P_HOVER + K_DRAG * math.hypot(*world.wind) ** 2
        s.battery_wh -= power * dt / 3600

        for zn in world.zones:
            if zn.kind != "radio_shadow":
                stats["min_zone_clearance"] = min(stats["min_zone_clearance"], math.dist(s.pos[:2], zn.center) - zn.radius)
        for g in stats["closest_to"]:
            stats["closest_to"][g] = min(stats["closest_to"][g], math.dist(s.pos[:2], g))
        if rep:
            comms(s.t)
    if rep:                                  # keep the radio alive after landing until the ground is in sync
        t_end = s.t + 10.0
        while s.t < t_end:
            s.t = round(s.t + dt, 3)
            comms(s.t)
    return s, stats
