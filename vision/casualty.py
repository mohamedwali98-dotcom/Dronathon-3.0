"""Casualty assessment: RGB detector + thermal camera + depth camera + motion -> status and injury level 1-10.

Medical logic (simple, START-triage inspired, every rule leaves a reason string for mission_logs):
  * visible injury (RGB "injured" class)             -> +3   (+1 if weak detection)
  * thermal hot spot on the body (>= 1.5 C above the
    body's median: fresh blood is at core temperature
    ~37 C while skin is ~31-34 C, so active bleeding
    or inflamed wounds look warmer)                  -> +2
  * lying on the ground (depth: < 0.6 m tall)       -> +1
  * not moving but warm (unresponsive / unconscious) -> +3
  * cold skin (< 31 C) while alive (hypothermia)     -> +1
Death is only *suspected*, never asserted: still for >= 10 s AND body within 3 C of the ground
(a dead body cools toward ambient) or below 25 C. Without thermal data or with a short
observation we assume alive (never deprioritise someone who might be saved).
priority = severity for the living; a possibly-deceased person gets priority 1 for supplies
(supplies cannot help) but is still reported to the rescue team.
"""
from dataclasses import dataclass

import numpy as np

STILL = 0.05          # motion score below this = not moving
MIN_OBSERVE_S = 10.0  # seconds of stillness before death can be suspected


@dataclass
class PersonObs:
    injured_conf: float            # 0..1 from the RGB detector ("injured" class), 0 if "healthy"
    body_temp_c: float | None      # median body surface temperature (thermal)
    hotspot_delta_c: float | None  # hottest body spot minus body median (thermal)
    ambient_c: float | None        # ground temperature around the person (thermal)
    height_m: float | None         # top of body above the ground (depth)
    motion: float                  # 0..1 motion score accumulated over the track
    observed_s: float              # how long this person has been tracked


def assess(o: PersonObs) -> dict:
    reasons = []
    still = o.motion < STILL
    thermal = o.body_temp_c is not None and o.ambient_c is not None
    if not still:
        status = "alive"
    elif o.observed_s >= MIN_OBSERVE_S and thermal and (o.body_temp_c - o.ambient_c < 3 or o.body_temp_c < 25):
        status = "possibly_deceased"
        reasons.append("still_and_cold")
    else:
        status = "alive_unresponsive"

    sev = 1
    if o.injured_conf >= 0.5:
        sev += 3; reasons.append("visible_injury")
    elif o.injured_conf >= 0.25:
        sev += 1; reasons.append("possible_injury")
    if o.hotspot_delta_c is not None and o.hotspot_delta_c >= 1.5:
        sev += 2; reasons.append("hot_spot")
    if o.height_m is not None and o.height_m < 0.6:
        sev += 1; reasons.append("lying")
    if status == "alive_unresponsive":
        sev += 3; reasons.append("not_moving")
    if status != "possibly_deceased" and o.body_temp_c is not None and o.body_temp_c < 31:
        sev += 1; reasons.append("cold_skin")
    if status == "possibly_deceased":
        sev = 10
    sev = max(1, min(10, sev))

    injured = o.injured_conf >= 0.5 or "hot_spot" in reasons or status != "alive"
    priority = 1 if status == "possibly_deceased" else sev
    return {"status": status, "injured": injured, "severity": sev, "priority": priority, "reasons": reasons}


# ---------------- sensor feature extraction (pixel box = x1, y1, x2, y2) ----------------
def _masks(shape, box):
    x1, y1, x2, y2 = map(int, box)
    mx, my = (x2 - x1) // 2, (y2 - y1) // 2
    inner = np.zeros(shape, bool); inner[y1:y2, x1:x2] = True
    outer = np.zeros(shape, bool)
    outer[max(0, y1 - my):min(shape[0], y2 + my), max(0, x1 - mx):min(shape[1], x2 + mx)] = True
    return inner, outer & ~inner


def thermal_stats(thermal_c, box):
    """-> (body median C, hottest-spot minus body C, ambient C); None when no warm body is visible."""
    inner, ring = _masks(thermal_c.shape, box)
    ambient = float(np.median(thermal_c[ring])) if ring.any() else None
    vals = thermal_c[inner]
    body_px = vals[vals > ambient + 2] if ambient is not None else vals
    if body_px.size == 0:
        return None, None, ambient
    body = float(np.median(body_px))
    return body, float(np.percentile(body_px, 99.5)) - body, ambient


def height_above_ground(depth_m, box):
    """Top-down depth camera: ground distance (around the box) minus closest body point."""
    inner, ring = _masks(depth_m.shape, box)
    return float(np.median(depth_m[ring]) - np.percentile(depth_m[inner], 5))


def motion_score(prev_gray, gray, box, thresh=25):
    """Fraction of changed pixels inside the box minus the same around it (cancels drone drift)."""
    inner, ring = _masks(gray.shape, box)
    changed = np.abs(gray.astype(np.int16) - prev_gray.astype(np.int16)) > thresh
    return max(0.0, float(changed[inner].mean()) - (float(changed[ring].mean()) if ring.any() else 0.0))
