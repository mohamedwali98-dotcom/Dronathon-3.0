"""Demo: fly a full mission in the 2D simulator (radio link on, radio shadow on the route), then serve
the ground station maps.   python -m ground.demo   ->  http://localhost:8000"""
import os

from drone.state import Casualty, Zone
from ground.server import serve
from sim.kinematic import World, run_mission

OUT = os.path.join(os.path.dirname(__file__), "..", "runs", "mission")
MINES = [(100.0, 110.0), (30.0, 185.0), (175.0, 95.0)]


def demo_world():
    return World(bounds=(0, 0, 200, 200), base=(5.0, 5.0), wind=(2.0, -1.0),
                 casualties=[Casualty(1, (60.0, 150.0), 8, 8, "alive"), Casualty(2, (150.0, 40.0), 9, 9, "alive_unresponsive"),
                             Casualty(3, (170.0, 170.0), 5, 5, "alive"), Casualty(4, (100.0, 60.0), 10, 1, "possibly_deceased"),
                             Casualty(5, (85.0, 175.0), 3, 3, "alive")],
                 zones=[Zone(MINES[0], 10.0, "mine"), Zone(MINES[1], 6.0, "mine"), Zone(MINES[2], 6.0, "mine"),
                        Zone((40.0, 80.0), 12.0, "hostile"), Zone((150.0, 120.0), 25.0, "radio_shadow")],
                 objects=[("mine", p) for p in MINES] + [("weapon", (45.0, 65.0)), ("weapon", (120.0, 20.0))]
                         + [("litter", (10.0 + 12 * k, 30.0 + (k % 3) * 50)) for k in range(15)])


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in ("drone.db", "ground.db"):
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(os.path.join(OUT, f + suffix)):
                os.remove(os.path.join(OUT, f + suffix))
    print("Flying the mission (about 1 min)...")
    s, st = run_mission(demo_world(), store_path=os.path.join(OUT, "drone.db"), link=True,
                        ground_path=os.path.join(OUT, "ground.db"))
    print(f"phase={s.phase}  drone store={st['store'].counts()}  max msg={max(st['channel'].sizes)} B")
    serve(st["ground"])


if __name__ == "__main__":
    main()
