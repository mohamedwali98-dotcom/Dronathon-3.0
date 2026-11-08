import pytest
from comms.compact import CLASS_ORDER, STATUS, pack_reports, unpack_report, hello_payload, tel_payload
from comms.schema import encode
from drone.state import DroneState


def test_flags_order_is_weapon_litter_mine():
    assert CLASS_ORDER == ("weapon", "litter", "mine")
    (m,) = pack_reports((1, 0, 1), 1, [], [], seq0=1, t=0.0)
    assert m["p"]["h"] == [1, 0, 1]
    assert unpack_report(m)["flags"] == {"weapon": 1, "litter": 0, "mine": 1}


def test_class_mapping_is_by_name():
    (m,) = pack_reports((0, 0, 1), 0, [(5, "mine", 10.0, 20.0, 0.93)], [], seq0=1, t=0.0)
    assert m["p"]["d"][0][1] == 2
    assert unpack_report(m)["detections"][0]["cls"] == "mine"


def test_typical_report_is_one_message_under_1kb():
    det = [(i, c, 123.4, -56.7, 0.91) for i, c in enumerate(["mine"] * 3 + ["weapon"] * 2 + ["litter"] * 15)]
    cas = [(i, 150.5, 40.2, 9, 0) for i in range(5)]
    msgs = pack_reports((1, 1, 1), 1, det, cas, seq0=7, t=312.4)
    assert len(msgs) == 1 and len(encode(msgs[0])) < 1024
    assert msgs[0]["v"] == 2 and msgs[0]["seq"] == 7 and msgs[0]["type"] == "rep"


def test_large_report_is_split_and_lossless():
    det = [(i, "litter", 100.0 + i, 199.9, 0.75) for i in range(150)]
    cas = [(i, 12.3, 45.6, 1 + i % 10, i % 3) for i in range(40)]
    msgs = pack_reports((0, 1, 0), 1, det, cas, seq0=100, t=1.0)
    assert len(msgs) >= 2
    assert all(len(encode(m)) < 1024 for m in msgs)
    assert [m["seq"] for m in msgs] == list(range(100, 100 + len(msgs)))
    got_d = [d["id"] for m in msgs for d in unpack_report(m)["detections"]]
    got_c = [c["id"] for m in msgs for c in unpack_report(m)["injured"]]
    assert sorted(got_d) == list(range(150)) and sorted(got_c) == list(range(40))


def test_priority_out_of_range_rejected():
    for bad in (0, 11):
        with pytest.raises(ValueError):
            pack_reports((0, 0, 0), 1, [], [(1, 0.0, 0.0, bad, 0)], seq0=1, t=0.0)


def test_deceased_status_code_is_2():
    assert STATUS["possibly_deceased"] == 2
    (m,) = pack_reports((0, 0, 0), 1, [], [(1, 0.0, 0.0, 1, 2)], seq0=1, t=0.0)
    assert unpack_report(m)["injured"][0]["status"] == "possibly_deceased"


def test_hello_and_tel_are_numeric_and_small():
    assert hello_payload((36.9324355, 10.2695094)) == {"o": [36.9324355, 10.2695094]}
    s = DroneState(pos=(12.34, 56.78, 20.0), phase="NAVIGUER")
    d = tel_payload(s)["d"]
    assert d[:3] == [12.3, 56.8, 20.0] and all(isinstance(v, (int, float)) for v in d)
