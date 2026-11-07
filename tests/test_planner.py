import math
from drone.state import DroneState, Casualty, Zone, Weather, BATTERY_WH
from drone.planner import Grid, astar, triage, lawnmower, energy_wh
from drone.rth import rth_threshold, should_rth

BOUNDS = (0, 0, 200, 200)
BASE = (5.0, 5.0)


def state(**kw):
    s = DroneState(pos=(5.0, 5.0, 20.0))
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def test_rescue_order_follows_urgency_then_proximity():
    s = state(casualties=[Casualty(1, (60, 60), 4, 4, "alive"),
                          Casualty(2, (150, 150), 9, 9, "alive"),
                          Casualty(3, (40, 40), 9, 9, "alive")])
    ranked = triage(s, Grid(BOUNDS, s.zones), BASE)
    assert [c.id for sc, c, _ in ranked if sc > 0] == [3, 2, 1]
    assert any(l["event"] == "triage" for l in s.mission_logs)


def test_casualty_inside_minefield_is_unreachable_and_scores_zero():
    s = state(zones=[Zone((100, 100), 10, "mine")], casualties=[Casualty(1, (102, 100), 9, 9, "alive")])
    (score, _, path), = triage(s, Grid(BOUNDS, s.zones), BASE)
    assert score == 0 and path is None


def test_casualty_beyond_battery_range_scores_zero():
    s = state(battery_wh=1.0, casualties=[Casualty(1, (190, 190), 9, 9, "alive")])
    assert triage(s, Grid(BOUNDS, s.zones), BASE)[0][0] == 0


def test_possibly_deceased_and_served_casualties_get_no_supplies():
    s = state(casualties=[Casualty(1, (40, 40), 10, 1, "possibly_deceased"),
                          Casualty(2, (50, 50), 9, 9, "alive", served=True)])
    assert all(sc == 0 for sc, _, _ in triage(s, Grid(BOUNDS, s.zones), BASE))


def test_path_never_enters_an_exclusion_zone():
    zones = [Zone((100, 100), 20, "mine"), Zone((60, 140), 15, "hostile")]
    g = Grid(BOUNDS, zones)
    path = astar(g, (10, 10), (190, 190))
    assert path and math.dist(path[-1], (190, 190)) < 3
    for a, b in zip(path, path[1:]):
        for i in range(11):
            p = (a[0] + (b[0] - a[0]) * i / 10, a[1] + (b[1] - a[1]) * i / 10)
            assert all(math.dist(p, z.center) > z.radius for z in zones)


def test_radio_shadow_is_not_an_obstacle():
    g = Grid(BOUNDS, [Zone((100, 100), 30, "radio_shadow")])
    assert not g.blocked_at((100, 100))


def test_lawnmower_covers_whole_area():
    wps = lawnmower(BOUNDS, swath=20)
    for x in range(0, 201, 10):
        for y in range(0, 201, 10):
            assert any(abs(a[0] - x) <= 10 and min(a[1], b[1]) <= y <= max(a[1], b[1])
                       for a, b in zip(wps, wps[1:]) if a[0] == b[0])


def test_headwind_costs_more_energy():
    path = [(0, 0), (100, 0)]
    assert energy_wh(path, (-6, 0)) > energy_wh(path, (0, 0)) > energy_wh(path, (6, 0))


def test_rth_threshold_rises_with_headwind_and_distance():
    far = state(pos=(180.0, 180.0, 20.0))
    g = Grid(BOUNDS, [])
    calm = rth_threshold(far, g, BASE)
    far.weather = Weather(wind=(6.0, 6.0))            # blowing away from base = headwind on the way home
    assert rth_threshold(far, g, BASE) > calm
    near = state(pos=(20.0, 20.0, 20.0))
    assert rth_threshold(near, g, BASE) < calm


def test_should_rth_when_battery_hits_threshold():
    s = state(pos=(180.0, 180.0, 20.0))
    g = Grid(BOUNDS, [])
    s.battery_wh = rth_threshold(s, g, BASE) + 0.5
    assert not should_rth(s, g, BASE)
    s.battery_wh -= 1.0
    assert should_rth(s, g, BASE)
