from comms.geo import to_latlon, to_local, load_origin

O = (36.8, 10.3)


def test_100m_north_is_about_0_000899_deg():
    lat, lon = to_latlon(0.0, 100.0, O)
    assert abs(lat - O[0] - 0.000898) < 2e-6 and lon == O[1]


def test_round_trip_within_1cm_over_1km():
    for x, y in [(1000, 0), (-700, 650), (0, -1000)]:
        bx, by = to_local(*to_latlon(x, y, O), O)
        assert abs(bx - x) < 0.01 and abs(by - y) < 0.01


def test_origin_loads_from_config():
    lat, lon = load_origin()
    assert -90 <= lat <= 90 and -180 <= lon <= 180
