"""Real-time drone vision: one call per camera frame -> one JSON-ready message (< 1 KB).

    v = DroneVision(yolo_detector("vision/weights/main.pt"), yolo_detector("vision/weights/people.pt"))
    msg = v.step(rgb, thermal_c=thermal, depth_m=depth, t=sim_time)

Output:
  weapon / mine / litter : bool  (True once seen in >= `persist` of the last `window` frames)
  injured: present (bool), count (injured people), people (all people),
           persons: most urgent first -> id, status, severity 1-10, priority 1-10, box
thermal_c (deg C per pixel) and depth_m (metres per pixel) are optional and must cover the same
view as the RGB camera; boxes are rescaled if their resolution differs.

CLI demo:  python vision/realtime.py --source 0           (webcam, RGB only)
           python vision/realtime.py --source video.mp4
"""
import argparse, json, time
from collections import deque

import cv2
import numpy as np

from casualty import PersonObs, assess, height_above_ground, motion_score, thermal_stats

HAZARDS = ("mine", "weapon", "litter")      # main model class order
INJURED, HEALTHY = 0, 1                     # people model class order
MAX_PERSONS = 6                             # keeps the message < 1 KB
MOTION_WINDOW_S = 3.0


def yolo_detector(weights, conf=0.4, imgsz=640):
    from ultralytics import YOLO
    model = YOLO(weights)

    def detect(img):
        r = model.predict(img, conf=conf, imgsz=imgsz, verbose=False)[0]
        return [(int(c), float(p), *map(float, b))
                for b, c, p in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]
    return detect


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def _scale(box, src_shape, dst_shape):
    sx, sy = dst_shape[1] / src_shape[1], dst_shape[0] / src_shape[0]
    return (box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy)


class DroneVision:
    def __init__(self, main_detector, people_detector, persist=3, window=5):
        self.main, self.people = main_detector, people_detector
        self.persist = persist
        self.history = deque(maxlen=window)
        self.tracks, self.next_id, self.seq, self.prev_gray = {}, 1, 0, None

    def step(self, rgb, thermal_c=None, depth_m=None, t=None):
        t0 = time.perf_counter()
        t = time.monotonic() if t is None else t
        gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)

        self.history.append({int(d[0]) for d in self.main(rgb)})
        hazards = {name: sum(i in seen for seen in self.history) >= self.persist for i, name in enumerate(HAZARDS)}

        persons = [self._update_track(d, rgb, gray, thermal_c, depth_m, t) for d in self.people(rgb)]
        self.tracks = {k: v for k, v in self.tracks.items() if t - v["last_t"] <= 1.0}
        self.prev_gray = gray
        persons.sort(key=lambda p: -p["priority"])

        self.seq += 1
        return {"version": 1, "seq": self.seq, "t": round(t, 2), **hazards,
                "injured": {"present": any(p["injured"] for p in persons),
                            "count": sum(p["injured"] for p in persons),
                            "people": len(persons),
                            "persons": [{k: p[k] for k in ("id", "status", "severity", "priority", "box")}
                                        for p in persons[:MAX_PERSONS]]},
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}

    def _update_track(self, det, rgb, gray, thermal_c, depth_m, t):
        cls, conf, box = det[0], det[1], tuple(det[2:6])
        tid = max(self.tracks, key=lambda k: _iou(self.tracks[k]["box"], box), default=None)
        if tid is None or _iou(self.tracks[tid]["box"], box) < 0.3 or self.tracks[tid]["last_t"] == t:
            tid, self.next_id = self.next_id, self.next_id + 1
            self.tracks[tid] = {"first_t": t, "motion": deque(), "inj": None}
        tr = self.tracks[tid]
        tr.update(box=box, last_t=t)

        p_inj = conf if cls == INJURED else 1 - conf
        tr["inj"] = p_inj if tr["inj"] is None else 0.7 * tr["inj"] + 0.3 * p_inj
        if self.prev_gray is not None and self.prev_gray.shape == gray.shape:
            tr["motion"].append((t, motion_score(self.prev_gray, gray, box)))
        while tr["motion"] and t - tr["motion"][0][0] > MOTION_WINDOW_S:
            tr["motion"].popleft()
        # until we have ~1 s of history, assume the person may be moving (unknown != still)
        enough = tr["motion"] and t - tr["first_t"] >= 1.0
        motion = max(m for _, m in tr["motion"]) if enough else 1.0

        body = hot = amb = height = None
        if thermal_c is not None:
            body, hot, amb = thermal_stats(thermal_c, _scale(box, rgb.shape, thermal_c.shape))
        if depth_m is not None:
            height = height_above_ground(depth_m, _scale(box, rgb.shape, depth_m.shape))

        r = assess(PersonObs(tr["inj"], body, hot, amb, height, motion, t - tr["first_t"]))
        return {"id": tid, **r, "box": [int(v) for v in box]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--main", default="vision/weights/main.pt")
    ap.add_argument("--people", default="vision/weights/people.pt")
    ap.add_argument("--no-show", action="store_true")
    a = ap.parse_args()
    cap = cv2.VideoCapture(int(a.source) if a.source.isdigit() else a.source)
    v = DroneVision(yolo_detector(a.main), yolo_detector(a.people))
    lat = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        msg = v.step(frame)
        lat.append(msg["latency_ms"])
        print(json.dumps(msg, separators=(",", ":")))
        if not a.no_show:
            for p in msg["injured"]["persons"]:
                x1, y1, x2, y2 = p["box"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255) if p["severity"] > 3 else (0, 200, 0), 2)
                cv2.putText(frame, f"#{p['id']} {p['status']} L{p['severity']}", (x1, y1 - 5), 0, 0.5, (0, 255, 255), 1)
            flags = " ".join(f"{h.upper()}" for h in HAZARDS if msg[h])
            cv2.putText(frame, flags or "clear", (10, 25), 0, 0.8, (0, 0, 255) if flags else (0, 200, 0), 2)
            cv2.imshow("SKYFORGE vision", frame)
            if cv2.waitKey(1) == 27:
                break
    if lat:
        print(f"frames={len(lat)} latency p50={np.percentile(lat, 50):.1f} ms p95={np.percentile(lat, 95):.1f} ms")


if __name__ == "__main__":
    main()
