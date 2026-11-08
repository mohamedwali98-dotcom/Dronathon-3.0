import math
from drone.state import Casualty, Zone
from comms.geo import to_local
from sim.kinematic import World, run_mission

MINES = [(100.0, 110.0), (30.0, 185.0), (175.0, 95.0)]
WEAPONS = [(45.0, 65.0), (120.0, 20.0)]
LITTER = [(10.0 + 12 * k, 30.0 + (k % 3) * 50) for k in range(15)]


def world():
    return World(bounds=(0, 0, 200, 200), base=(5.0, 5.0), wind=(2.0, -1.0),
                 casualties=[Casualty(1, (60.0, 150.0), 8, 8, "alive"),
                             Casualty(2, (150.0, 40.0), 9, 9, "alive_unresponsive"),
                             Casualty(3, (170.0, 170.0), 5, 5, "alive"),
                             Casualty(4, (100.0, 60.0), 10, 1, "possibly_deceased")],
                 zones=[Zone(MINES[0], 10.0, "mine"), Zone(MINES[1], 6.0, "mine"), Zone(MINES[2], 6.0, "mine"),
                        Zone((40.0, 80.0), 12.0, "hostile"), Zone((150.0, 120.0), 25.0, "radio_shadow")],
                 objects=[("mine", p) for p in MINES] + [("weapon", p) for p in WEAPONS] + [("litter", p) for p in LITTER])


def run(tmp_path):
    return run_mission(world(), store_path=str(tmp_path / "drone.db"), link=True)


def test_ground_gets_everything_after_radio_cut(tmp_path):
    s, st = run(tmp_path)
    v = st["ground"].view()
    assert any(l["event"] == "link_lost" for l in s.mission_logs)
    assert (len(v["weapon"]), len(v["litter"]), len(v["mine"]), len(v["injured"])) == (2, 15, 3, 4)
    origin = tuple(v["origin"])
    for cls, truth in (("mine", MINES), ("weapon", WEAPONS), ("litter", LITTER)):
        for p in v[cls]:
            x, y = to_local(p["lat"], p["lon"], origin)
            assert min(math.dist((x + 5.0, y + 5.0), q) for q in truth) < 0.5   # radio frame = from home base (5, 5)
    dead = [p for p in v["injured"] if p["status"] == "possibly_deceased"]
    assert len(dead) == 1 and dead[0]["priority"] == 1


def test_every_radio_message_under_1kb(tmp_path):
    _, st = run(tmp_path)
    assert max(st["channel"].sizes) < 1024


def test_drone_store_has_all_objects_on_landing(tmp_path):
    s, st = run(tmp_path)
    assert s.phase == "POSE"
    c = st["store"].counts()
    assert (c["weapon"], c["litter"], c["mine"], c["casualties"]) == (2, 15, 3, 4)
