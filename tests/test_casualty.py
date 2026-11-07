import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vision"))
from casualty import PersonObs, assess, thermal_stats, height_above_ground, motion_score

BOX = (40, 40, 80, 80)  # x1, y1, x2, y2 in pixels


def obs(**kw):
    base = dict(injured_conf=0.0, body_temp_c=33.0, hotspot_delta_c=0.0, ambient_c=22.0,
                height_m=1.7, motion=0.5, observed_s=15.0)
    base.update(kw)
    return PersonObs(**base)


# ---------- assess(): alive / dead / injury level ----------
def test_healthy_standing_moving_person_is_alive_level_1():
    r = assess(obs())
    assert r["status"] == "alive" and r["severity"] == 1 and r["injured"] is False


def test_visible_injury_raises_severity():
    assert assess(obs(injured_conf=0.9))["severity"] > assess(obs())["severity"]
    assert assess(obs(injured_conf=0.9))["injured"] is True


def test_hot_spot_on_body_counts_as_possible_bleeding():
    r = assess(obs(injured_conf=0.9, hotspot_delta_c=2.5))
    assert r["severity"] > assess(obs(injured_conf=0.9))["severity"]
    assert "hot_spot" in r["reasons"]


def test_warm_still_lying_injured_person_is_alive_unconscious_and_most_urgent():
    r = assess(obs(injured_conf=0.9, hotspot_delta_c=2.5, height_m=0.3, motion=0.0))
    assert r["status"] == "alive_unresponsive"
    assert r["severity"] == 10 and r["priority"] == 10


def test_cold_still_body_is_possibly_deceased_with_lowest_aid_priority():
    r = assess(obs(injured_conf=0.9, body_temp_c=23.0, ambient_c=22.0, height_m=0.3, motion=0.0))
    assert r["status"] == "possibly_deceased"
    assert r["priority"] == 1          # supplies cannot help; still reported to rescue teams


def test_short_observation_never_declares_death():
    r = assess(obs(body_temp_c=23.0, ambient_c=22.0, height_m=0.3, motion=0.0, observed_s=2.0))
    assert r["status"] != "possibly_deceased"


def test_no_thermal_never_declares_death():
    r = assess(obs(body_temp_c=None, ambient_c=None, height_m=0.3, motion=0.0))
    assert r["status"] == "alive_unresponsive"


def test_severity_and_priority_are_always_between_1_and_10():
    for inj in (0, 0.3, 0.9):
        for hot in (0, 3):
            for h in (0.2, 1.7, None):
                for m in (0, 0.5):
                    r = assess(obs(injured_conf=inj, hotspot_delta_c=hot, height_m=h, motion=m))
                    assert 1 <= r["severity"] <= 10 and 1 <= r["priority"] <= 10


# ---------- sensor feature extraction ----------
def test_thermal_stats_finds_body_temperature_and_hot_spot():
    t = np.full((120, 120), 20.0)             # ground at 20 C
    t[45:75, 45:75] = 33.0                    # body at 33 C
    t[55:58, 55:58] = 36.5                    # wound at 36.5 C
    body, hot, amb = thermal_stats(t, BOX)
    assert abs(body - 33.0) < 0.5 and abs(amb - 20.0) < 0.5 and hot > 2.5


def test_height_above_ground_from_top_down_depth():
    d = np.full((120, 120), 30.0)             # ground 30 m below drone
    d[45:75, 45:75] = 29.7                    # body top 0.3 m above ground
    assert abs(height_above_ground(d, BOX) - 0.3) < 0.05


def test_motion_score_ignores_global_camera_motion():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 255, (120, 120)).astype(np.uint8)
    still = motion_score(a, a.copy(), BOX)
    b = a.copy(); b[45:75, 45:75] = 255 - b[45:75, 45:75]       # only the person changes
    moving = motion_score(a, b, BOX)
    c = np.roll(a, 1, axis=1)                                    # whole image shifts (drone drift)
    drift = motion_score(a, c, BOX)
    assert still == 0 and moving > 0.3 and drift < 0.1
