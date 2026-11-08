import math
import numpy as np
from drone.state import Casualty, Zone
from drone.planner import Grid, astar, CLEARANCE_M, DRONE_RADIUS_M
from sim.kinematic import World, run_mission

BOUNDS = (0, 0, 200, 200)


def seg_clearance(a, b, z):
    """Gap between the drone body and obstacle z along segment a-b."""
    ax, ay = a; bx, by = b; cx, cy = z.center
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    u = 0 if L2 == 0 else max(0, min(1, ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / L2))
    return math.dist((ax + u * (bx - ax), ay + u * (by - ay)), z.center) - z.radius - DRONE_RADIUS_M


def test_clearance_is_one_metre():
    assert CLEARANCE_M == 1.0


def test_path_passes_a_pole_with_at_least_1m_and_not_far_detour():
    pole = Zone((100.0, 100.0), 0.3, "obstacle")
    path = astar(Grid(BOUNDS, [pole]), (100.0, 60.0), (100.0, 140.0))
    gaps = [seg_clearance(a, b, pole) for a, b in zip(path, path[1:])]
    assert min(gaps) >= CLEARANCE_M - 1e-6
    assert sum(math.dist(a, b) for a, b in zip(path, path[1:])) < 84      # dodges tightly, no 5 m danger margin


def test_path_threads_between_building_and_trees():
    zs = [Zone((60.0, 100.0), 6.0, "obstacle"), Zone((75.0, 95.0), 1.5, "obstacle"), Zone((70.0, 110.0), 1.5, "obstacle")]
    path = astar(Grid(BOUNDS, zs), (40.0, 100.0), (110.0, 100.0))
    assert path is not None
    assert min(seg_clearance(a, b, z) for a, b in zip(path, path[1:]) for z in zs) >= CLEARANCE_M - 1e-6


def test_start_close_to_an_obstacle_still_plans():
    tree = Zone((50.0, 50.0), 1.5, "obstacle")
    start = (50.0 + 1.5 + DRONE_RADIUS_M + 1.2, 50.0)                    # 1.2 m gap: legal but tight
    assert astar(Grid(BOUNDS, [tree]), start, (150.0, 50.0)) is not None


def world():
    return World(bounds=BOUNDS, base=(5.0, 5.0), wind=(2.0, -1.0),
                 casualties=[Casualty(1, (60.0, 150.0), 8, 8, "alive"), Casualty(2, (150.0, 40.0), 9, 9, "alive_unresponsive"),
                             Casualty(3, (170.0, 170.0), 5, 5, "alive")],
                 zones=[Zone((100.0, 110.0), 10.0, "mine"),
                        Zone((60.0, 100.0), 4.0, "obstacle"), Zone((20.0, 120.0), 0.3, "obstacle"),
                        Zone((140.0, 60.0), 0.3, "obstacle"), Zone((100.0, 30.0), 1.5, "obstacle"),
                        Zone((180.0, 150.0), 1.5, "obstacle"),
                        Zone((20.0, 90.0), 2.0, "obstacle", speed=2.0, id=99)],
                 movers={99: ((20.0, 90.0), (180.0, 90.0))})


def test_full_mission_keeps_1m_from_every_obstacle_including_the_moving_one():
    s, st = run_mission(world())
    assert s.phase == "POSE" and sorted(c.id for c in s.casualties if c.served) == [1, 2, 3]
    assert st["min_obstacle_clearance"] >= CLEARANCE_M - 0.05
    assert st["min_zone_clearance"] > 0
    assert np.percentile(st["cycle_ms"], 95) <= 100


def test_moving_obstacle_crossing_the_route_is_dodged_with_1m():
    # first coverage leg flies north along x=20; the mover crosses x=20 at y=90 right when the drone gets there
    w = World(bounds=BOUNDS, base=(5.0, 5.0), casualties=[],
              zones=[Zone((40.0, 90.0), 2.0, "obstacle", speed=2.0, id=7)], movers={7: ((40.0, 90.0), (0.0, 90.0))})
    s, st = run_mission(w)
    assert any(l["event"] in ("replan_obstacle", "evade") for l in s.mission_logs)
    assert st["min_obstacle_clearance"] >= CLEARANCE_M - 0.05
    assert s.phase == "POSE"
