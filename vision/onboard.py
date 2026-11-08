"""Onboard vision for the simulator: camera frame -> YOLO (main + people) -> ground positions.

    v = OnboardVision()                              # loads both models once (GPU if available)
    dets = v.detect(bgr, drone_xyz, yaw, hfov_deg)   # [Detection(cls, conf, box, xy)]

Classes: main model -> mine / weapon / litter, people model -> injured / healthy.
Positions come from vision/geolocate.py (nadir pinhole camera).
"""
import os, sys, time
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # realtime.py imports its siblings flat
from geolocate import pixel_to_ground  # noqa: E402
from realtime import yolo_detector  # noqa: E402

ROOT = os.path.dirname(HERE)
MAIN_W = os.path.join(ROOT, "runs", "main", "weights", "best.pt")
PEOPLE_W = os.path.join(HERE, "weights", "people.pt")
MAIN_NAMES, PEOPLE_NAMES = ("mine", "weapon", "litter"), ("injured", "healthy")


@dataclass
class Detection:
    cls: str
    conf: float
    box: tuple          # x1, y1, x2, y2 in pixels
    xy: tuple           # ground position (m)


class OnboardVision:
    def __init__(self, conf=0.25, imgsz=640):
        self.models = [(yolo_detector(w, conf=conf, imgsz=imgsz), names)
                       for w, names in ((MAIN_W, MAIN_NAMES), (PEOPLE_W, PEOPLE_NAMES)) if os.path.exists(w)]
        self.last_ms = 0.0

    def detect(self, bgr, drone_xyz, yaw, hfov_deg):
        t0 = time.perf_counter()
        h, w = bgr.shape[:2]
        out = []
        for det, names in self.models:
            for c, p, x1, y1, x2, y2 in det(bgr):
                xy = pixel_to_ground((x1 + x2) / 2, (y1 + y2) / 2, w, h, hfov_deg, drone_xyz, yaw)
                out.append(Detection(names[c], p, (x1, y1, x2, y2), xy))
        self.last_ms = (time.perf_counter() - t0) * 1000
        return out
