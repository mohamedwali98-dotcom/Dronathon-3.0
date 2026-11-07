import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vision"))
from realtime import DroneVision

RGB = np.zeros((120, 160, 3), np.uint8)


def fake(dets):
    """Detector stub: always returns the same list of (class_id, conf, x1, y1, x2, y2)."""
    return lambda img: dets


def test_hazard_booleans_need_several_frames_to_switch_on():
    v = DroneVision(fake([(0, 0.9, 10, 10, 30, 30)]), fake([]), persist=3, window=5)
    outs = [v.step(RGB, t=i * 0.1) for i in range(3)]
    assert [o["mine"] for o in outs] == [False, False, True]
    assert outs[-1]["weapon"] is False and outs[-1]["litter"] is False


def test_single_false_alarm_frame_is_ignored():
    dets = iter([[(1, 0.9, 0, 0, 5, 5)]] + [[]] * 9)
    v = DroneVision(lambda img: next(dets), fake([]), persist=3, window=5)
    assert not any(v.step(RGB, t=i * 0.1)["weapon"] for i in range(10))


def test_counts_injured_people_and_reports_level():
    people = fake([(0, 0.9, 10, 10, 40, 40), (1, 0.9, 80, 10, 110, 40), (0, 0.8, 50, 60, 80, 100)])
    out = DroneVision(fake([]), people).step(RGB, t=0.0)
    inj = out["injured"]
    assert inj["present"] is True and inj["count"] == 2 and inj["people"] == 3
    assert all(1 <= p["severity"] <= 10 for p in inj["persons"])
    assert inj["persons"][0]["priority"] >= inj["persons"][-1]["priority"]   # sorted most urgent first


def test_tracks_keep_their_id_across_frames():
    v = DroneVision(fake([]), fake([(0, 0.9, 10, 10, 40, 40)]))
    a = v.step(RGB, t=0.0)["injured"]["persons"][0]["id"]
    b = v.step(RGB, t=0.1)["injured"]["persons"][0]["id"]
    assert a == b


def test_message_is_versioned_and_under_1kb_even_with_many_people():
    people = fake([(0, 0.9, i * 5, 0, i * 5 + 4, 4) for i in range(30)])
    v = DroneVision(fake([]), people)
    m1, m2 = v.step(RGB, t=0.0), v.step(RGB, t=0.1)
    assert m1["version"] == 1 and m2["seq"] == m1["seq"] + 1
    assert len(json.dumps(m2, separators=(",", ":")).encode()) < 1024
