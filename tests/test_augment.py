import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vision"))
from augment_db import augment_one

def test_augmented_boxes_stay_valid_and_keep_classes():
    img = np.random.randint(0, 255, (480, 640, 3), np.uint8)
    boxes = [[0.5, 0.5, 0.3, 0.2], [0.95, 0.9, 0.1, 0.2]]
    for seed in range(30):
        out_img, out_boxes, out_cls = augment_one(img, boxes, [0, 2], seed)
        assert out_img.ndim == 3 and out_img.dtype == np.uint8
        assert set(out_cls) <= {0, 2}
        for x, y, w, h in out_boxes:
            assert 0 <= x - w / 2 + 1e-6 and x + w / 2 <= 1 + 1e-6
            assert 0 <= y - h / 2 + 1e-6 and y + h / 2 <= 1 + 1e-6
            assert w > 0 and h > 0

def test_read_labels_drops_zero_size_boxes(tmp_path):
    from augment_db import read_labels
    f = tmp_path / "l.txt"
    f.write_text("0 0.4 0.9 0 0\n1 0.5 0.5 0.2 0.2\n")
    assert read_labels(str(f)) == ([[0.5, 0.5, 0.2, 0.2]], [1])
