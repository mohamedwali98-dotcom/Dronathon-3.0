import json
import pytest
from comms.schema import make_msg, encode, decode, MAX_BYTES
from drone.state import DroneState, Casualty, Zone


def test_every_message_type_is_versioned_and_small():
    s = DroneState()
    s.casualties = [Casualty(i, (i * 10.0, 5.0), 7, 7, "alive") for i in range(6)]
    s.zones = [Zone((50.0, 50.0), 8.0, "mine") for _ in range(6)]
    payloads = {
        "telemetry": s.telemetry(),
        "detection": {"class": "weapon", "confidence": 0.91, "bbox": [10, 20, 60, 90], "pos": [12.5, 40.1]},
        "goal_update": {"goal": [100.0, 20.0]},
        "ack": {"seq": 41},
        "log": {"event": "phase", "from": "TRIAGE", "to": "NAVIGUER", "why": "casualty 3 score 0.81"},
    }
    for seq, (t, p) in enumerate(payloads.items(), 1):
        m = make_msg(t, p, seq=seq, ts=12.34)
        raw = encode(m)
        assert len(raw) < MAX_BYTES
        back = decode(raw)
        assert back["v"] == 1 and back["seq"] == seq and back["type"] == t


def test_oversized_message_is_rejected():
    with pytest.raises(ValueError):
        encode(make_msg("log", {"x": "a" * 2000}, seq=1, ts=0.0))


def test_unknown_type_is_rejected():
    with pytest.raises(ValueError):
        make_msg("selfie", {}, seq=1, ts=0.0)


def test_telemetry_of_busy_state_still_fits():
    s = DroneState()
    s.casualties = [Casualty(i, (i * 1.0, 2.0), 5, 5, "alive") for i in range(40)]
    assert len(encode(make_msg("telemetry", s.telemetry(), seq=1, ts=0.0))) < MAX_BYTES
