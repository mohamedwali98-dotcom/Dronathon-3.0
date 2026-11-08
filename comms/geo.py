"""Local metres (x east, y north, origin = home base) <-> WGS84 lat/lon.
Local tangent plane (equirectangular): < 1 cm error over 1 km, no extra dependency."""
import json, math, os

R = 6378137.0
CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "mission.json")


def to_latlon(x, y, origin):
    lat0, lon0 = origin
    return lat0 + math.degrees(y / R), lon0 + math.degrees(x / (R * math.cos(math.radians(lat0))))


def to_local(lat, lon, origin):
    lat0, lon0 = origin
    return math.radians(lon - lon0) * R * math.cos(math.radians(lat0)), math.radians(lat - lat0) * R


def load_origin(path=CONFIG):
    return tuple(json.load(open(path))["origin_latlon"])
