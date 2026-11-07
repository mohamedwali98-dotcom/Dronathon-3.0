import math
import numpy as np
from drone.state import Casualty, Zone
from drone.planner import RESERVE_WH
from sim.kinematic import World, run_mission

ORDER = {"INIT": {"EXPLORER"}, "EXPLORER": {"DETECTER", "TRIAGE", "RETOUR_BASE", "NAVIGUER"},
         "DETECTER": {"TRIAGE", "RETOUR_BASE"}, "TRIAGE": {"NAVIGUER", "EXPLORER", "RETOUR_BASE"},
         "NAVIGUER": {"LIVRER", "EXPLORER", "RETOUR_BASE", "TRIAGE", "NAVIGUER"},
         "LIVRER": {"TRIAGE", "RETOUR_BASE"}, "RETOUR_BASE": {"POSE", "NAVIGUER"}, "POSE": set()}


def world(**kw):
    w = World(bounds=(0, 0, 200, 200), base=(5.0, 5.0), wind=(2.0, -1.0),
              casualties=[Casualty(1, (60.0, 150.0), 8, 8, "alive"),
                          Casualty(2, (150.0, 40.0), 9, 9, "alive_unresponsive"),
                          Casualty(3, (170.0, 170.0), 5, 5, "alive"),
                          Casualty(4, (100.0, 60.0), 10, 1, "possibly_deceased")],
              zones=[Zone((100.0, 110.0), 10.0, "mine"), Zone((40.0, 80.0), 12.0, "hostile"),
                     Zone((150.0, 120.0), 25.0, "radio_shadow")])
    for k, v in kw.items():
        setattr(w, k, v)
    return w


def transitions(state):
    return [(l["from"], l["to"]) for l in state.mission_logs if l["event"] == "phase"]


def test_full_mission_with_zero_human_input():
    w = world()
    s, stats = run_mission(w)
    assert s.phase == "POSE" and math.dist(s.pos[:2], w.base) < 1.5
    assert sorted(c.id for c in s.casualties if c.served) == [1, 2, 3]
    assert stats["min_zone_clearance"] > 0              # never entered a mine / hostile zone
    assert s.battery_wh > RESERVE_WH
    for a, b in transitions(s):
        assert b in ORDER[a], f"illegal transition {a}->{b}"
    assert any(l["event"] == "link_lost" for l in s.mission_logs)      # flew through the radio shadow


def test_decision_cycle_p95_under_100ms():
    _, stats = run_mission(world())
    assert np.percentile(stats["cycle_ms"], 95) <= 100


def test_low_battery_forces_return_and_safe_landing():
    s, _ = run_mission(world(), battery_wh=14.0)
    assert s.phase == "POSE"
    assert any(l["event"] == "low_battery_rth" for l in s.mission_logs)
    assert s.battery_wh > RESERVE_WH


def test_goal_update_reroutes_the_drone():
    s, stats = run_mission(world(), goal_updates={30.0: (190.0, 10.0)})
    assert any(l["event"] == "reroute" for l in s.mission_logs)
    assert stats["closest_to"][(190.0, 10.0)] < 2.0
    assert s.phase == "POSE"


def test_exploration_continues_after_last_kit_to_map_all_hazards():
    s, _ = run_mission(world())
    assert {z.kind for z in s.zones} >= {"mine", "hostile"}
    explorer_after_kits = [l for l in s.mission_logs if l["event"] == "phase" and l["to"] == "EXPLORER"
                           and l["t"] > max(x["t"] for x in s.mission_logs if x["event"] == "delivered")]
    assert explorer_after_kits, "drone went home with coverage left"
