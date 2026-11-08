import math
from vision.geolocate import pixel_to_ground


def test_image_centre_is_under_the_drone():
    assert pixel_to_ground(320, 240, 640, 480, 90, (10, 20, 30), 0.0) == (10.0, 20.0)


def test_right_edge_at_90deg_fov_is_altitude_away():
    x, y = pixel_to_ground(640, 240, 640, 480, 90, (0, 0, 30), 0.0)   # yaw 0 = facing north
    assert abs(x - 30) < 1e-6 and abs(y) < 1e-6


def test_yaw_rotates_offsets():
    x, y = pixel_to_ground(320, 0, 640, 480, 90, (0, 0, 30), math.pi / 2)  # top of image, facing west
    assert x < -1 and abs(y) < 1e-6
