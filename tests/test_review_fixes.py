import os, re
from comms.link import Channel, DroneLink, GroundStation
from drone.reporter import Reporter
from drone.state import DroneState
from drone.store import MissionStore
from ground.receiver import GroundView

ORIGIN = (36.9324355, 10.2695094)
WEB = os.path.join(os.path.dirname(__file__), "..", "ground", "web")


def rig(tmp_path, capacity=512, base=(0.0, 0.0)):
    ch, view = Channel(), GroundView()
    ground, dl = GroundStation(ch, on_message=view.ingest, capacity=capacity), DroneLink(ch, capacity)
    rep = Reporter(MissionStore(str(tmp_path / "d.db")), dl, ORIGIN, base_xy=base)
    return ch, view, ground, dl, rep


def step(ch, ground, dl, rep, s, t, up):
    ch.up = up
    rep.tick(s, t)
    ground.step(t)
    rep.on_messages(dl.poll(t))


def test_page_works_offline_no_cdn():
    html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
    srcs = re.findall(r'(?:src|href)="([^"]+)"', html)
    assert srcs and not [s for s in srcs if s.startswith("http")]
    for s in srcs:
        assert os.path.exists(os.path.join(WEB, s)), s


def test_detections_survive_a_cut_longer_than_the_ring_buffer(tmp_path):
    ch, view, ground, dl, rep = rig(tmp_path, capacity=30)
    s = DroneState()
    step(ch, ground, dl, rep, s, 0.0, True)                       # hello delivered
    rep.observe([("mine", (10.0 * i, 5.0), 0.9) for i in range(20)], [], 1.0)
    t = 1.0
    while t < 120:                                                # 2 min shadow, ring holds 30 msgs
        step(ch, ground, dl, rep, s, t, False); t += 0.5
    while t < 160:
        step(ch, ground, dl, rep, s, t, True); t += 0.5
    assert len(view.view()["mine"]) == 20
    sizes_before = len(ch.sizes)
    while t < 170:
        ch.up = True; ground.step(t); dl.poll(t); t += 0.5       # no telemetry: ground must stop asking
    assert len(ch.sizes) - sizes_before <= 2


def test_replayed_old_report_does_not_overwrite_newer_casualty():
    v = GroundView()
    v.ingest({"type": "hello", "seq": 1, "p": {"o": list(ORIGIN)}})
    v.ingest({"type": "rep", "seq": 9, "p": {"h": [0, 0, 0], "d": [], "i": [1, [[2, 1.0, 1.0, 10, 1]]]}})
    v.ingest({"type": "rep", "seq": 4, "p": {"h": [0, 0, 0], "d": [], "i": [1, [[2, 1.0, 1.0, 9, 0]]]}})
    assert v.view()["injured"][0]["priority"] == 10


def test_positions_are_relative_to_home_base(tmp_path):
    ch, view, ground, dl, rep = rig(tmp_path, base=(5.0, 5.0))
    s = DroneState(pos=(5.0, 5.0, 20.0))
    rep.observe([("weapon", (15.0, 5.0), 0.9)], [], 0.0)
    for k in range(5):
        step(ch, ground, dl, rep, s, k * 0.5, True)
    v = view.view()
    assert abs(v["drone"][0] - ORIGIN[0]) < 1e-9 and abs(v["drone"][1] - ORIGIN[1]) < 1e-9
    from comms.geo import to_local
    x, y = to_local(v["weapon"][0]["lat"], v["weapon"][0]["lon"], ORIGIN)
    assert abs(x - 10.0) < 0.05 and abs(y) < 0.05
