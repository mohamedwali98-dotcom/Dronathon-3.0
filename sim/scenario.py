"""The one demo scenario shared by the 2D simulator and the Webots world (same coordinates, metres).

skyforge_world() = ground.demo's mission (5 injured, 3 mines, hostile zone, radio shadow, weapons, litter)
plus physical obstacles: a building, 3 trees and 1 moving obstacle (cahier: fixed + >= 1 moving obstacle).
"""
from drone.state import Zone
from ground.demo import demo_world

ALT = 20.0              # cruise altitude (m)
MOVER_ID = 100


def skyforge_world():
    w = demo_world()
    w.zones += [Zone((125.0, 160.0), 6.0, "obstacle"),                        # building
                Zone((70.0, 30.0), 1.5, "obstacle"), Zone((160.0, 15.0), 1.5, "obstacle"),
                Zone((20.0, 130.0), 1.5, "obstacle"),                        # trees
                Zone((80.0, 130.0), 1.0, "obstacle", speed=1.5, id=MOVER_ID)]  # moving obstacle
    w.movers = {MOVER_ID: ((80.0, 130.0), (120.0, 130.0))}
    return w


def mover_center(world, zid, t):
    """Ping-pong position of a moving obstacle at time t (same law as sim/kinematic.py)."""
    a, b = world.movers[zid]
    speed = next(z.speed for z in world.zones if z.id == zid)
    L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
    u = (speed * t / L) % 2.0
    u = u if u <= 1 else 2 - u
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
