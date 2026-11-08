import random
from drone.store import MissionStore


def store(tmp_path):
    return MissionStore(str(tmp_path / "drone.db"))


def test_repeated_sightings_merge(tmp_path):
    s, rng = store(tmp_path), random.Random(0)
    news = [s.upsert_detection("mine", 50 + rng.uniform(-1, 1), 60 + rng.uniform(-1, 1), 0.8, t)[1] for t in range(100)]
    assert news[0] is True and not any(news[1:])
    rows = s.unsent()["det"]
    assert len(rows) == 1 and abs(rows[0][2] - 50) < 0.5 and abs(rows[0][3] - 60) < 0.5
    assert s.counts()["mine"] == 1 and s.seen(rows[0][0]) == 100


def test_different_class_same_spot_not_merged(tmp_path):
    s = store(tmp_path)
    s.upsert_detection("mine", 10, 10, 0.9, 0); s.upsert_detection("weapon", 10, 10, 0.9, 0)
    assert len(s.unsent()["det"]) == 2


def test_objects_4m_apart_are_two_objects(tmp_path):
    s = store(tmp_path)
    s.upsert_detection("litter", 0, 0, 0.7, 0); s.upsert_detection("litter", 4, 0, 0.7, 1)
    assert s.counts()["litter"] == 2


def test_unsent_then_mark_sent(tmp_path):
    s = store(tmp_path)
    i, _ = s.upsert_detection("mine", 0, 0, 0.9, 0)
    s.upsert_casualty(7, 5, 5, 8, 0, 0)
    s.mark_sent([i], [7])
    assert s.unsent() == {"det": [], "cas": []}


def test_casualty_priority_change_marks_it_unsent_again(tmp_path):
    s = store(tmp_path)
    s.upsert_casualty(7, 5, 5, 8, 0, 0); s.mark_sent([], [7])
    assert s.upsert_casualty(7, 5, 5, 8, 0, 1) is False and s.unsent()["cas"] == []
    assert s.upsert_casualty(7, 5, 5, 10, 1, 2) is True
    assert s.unsent()["cas"] == [(7, 5.0, 5.0, 10, 1)]


def test_data_survives_reopen(tmp_path):
    s = store(tmp_path)
    s.upsert_detection("mine", 0, 0, 0.9, 0); s.upsert_casualty(1, 2, 2, 5, 0, 0); s.log(0.0, "phase", {"to": "EXPLORER"})
    before = s.counts(); s.close()
    assert MissionStore(str(tmp_path / "drone.db")).counts() == before
