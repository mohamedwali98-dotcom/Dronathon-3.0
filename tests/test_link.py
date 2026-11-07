from comms.link import Channel, DroneLink, GroundStation
from comms.schema import MAX_BYTES


def run(seconds, cut=(None, None), capacity=512, hz=5, goal_at=None):
    ch = Channel()
    drone, ground = DroneLink(ch, capacity), GroundStation(ch)
    goals = []
    for k in range(int(seconds * hz)):
        t = k / hz
        ch.up = not (cut[0] is not None and cut[0] <= t < cut[1])
        if goal_at is not None and abs(t - goal_at) < 1e-9:
            ground.send_goal((120.0, 40.0), t)
        drone.send("telemetry", {"k": k}, t)
        ground.step(t)
        goals += [m["p"]["goal"] for m in drone.poll(t) if m["type"] == "goal_update"]
    return drone, ground, ch, goals


def test_30s_radio_cut_is_fully_resynchronised():
    drone, ground, ch, _ = run(90, cut=(20, 50))
    assert ground.received_seqs() == list(range(1, drone.seq + 1))
    assert max(ch.sizes) < MAX_BYTES


def test_messages_are_lost_without_resync_only_when_buffer_overflows():
    drone, ground, _, _ = run(90, cut=(20, 50), capacity=50)
    lost = drone.seq - len(ground.received_seqs())      # 150 msgs during the cut, only 50 fit the buffer
    assert 95 <= lost <= 101
    assert any(l["event"] == "buffer_overflow" for l in drone.logs)


def test_goal_update_sent_during_outage_arrives_after_reconnection_exactly_once():
    _, _, _, goals = run(90, cut=(20, 50), goal_at=30.0)
    assert goals == [[120.0, 40.0]]
