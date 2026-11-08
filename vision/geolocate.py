"""Pixel -> ground position for a camera looking straight down (nadir pinhole model).
Yaw: 0 = drone faces north, +pi/2 = faces west (counter-clockwise, Webots ENU). Image "up" = forward."""
import math


def pixel_to_ground(u, v, img_w, img_h, hfov_deg, drone_xyz, yaw_rad):
    x0, y0, alt = drone_xyz
    m_per_px = alt / ((img_w / 2) / math.tan(math.radians(hfov_deg) / 2))
    right, fwd = (u - img_w / 2) * m_per_px, (img_h / 2 - v) * m_per_px
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    return x0 + right * c - fwd * s, y0 + right * s + fwd * c
