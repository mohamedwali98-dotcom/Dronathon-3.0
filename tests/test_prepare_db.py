import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vision"))
from prepare_db import remap

NAMES = ["a", "b"]

def test_box_row_is_remapped():
    assert remap(["1 0.5 0.5 0.2 0.2"], NAMES, {"b": 7}) == ["7 0.5 0.5 0.2 0.2"]

def test_polygon_row_becomes_bounding_box():
    out = remap(["0 0.1 0.2 0.3 0.2 0.3 0.6 0.1 0.6"], NAMES, {"*": 2})
    c, x, y, w, h = out[0].split()
    assert c == "2" and [round(float(v), 4) for v in (x, y, w, h)] == [0.2, 0.4, 0.2, 0.4]

def test_dropped_class_is_removed():
    assert remap(["0 0.5 0.5 0.1 0.1"], NAMES, {"a": None, "*": 1}) == []
