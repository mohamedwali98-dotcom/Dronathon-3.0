"""Ground-side view: decodes compact v2 messages into its own SQLite and exposes lat/lon for the maps."""
import sqlite3

from comms.compact import CLASS_ORDER, unpack_report
from comms.geo import to_latlon


class GroundView:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS det(id INTEGER PRIMARY KEY, cls TEXT, x REAL, y REAL, conf REAL, seq INTEGER);
            CREATE TABLE IF NOT EXISTS cas(id INTEGER PRIMARY KEY, x REAL, y REAL, priority INTEGER, status TEXT, seq INTEGER);
            CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, a REAL, b REAL);""")

    def ingest(self, m):
        if m["type"] == "hello":
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('origin',?,?)", m["p"]["o"])
        elif m["type"] == "tel":
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('drone',?,?)", m["p"]["d"][:2])
        elif m["type"] == "rep":
            r, seq = unpack_report(m), m.get("seq", 0)      # a replayed older report never overwrites newer data
            self.db.executemany("INSERT INTO det VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET cls=excluded.cls, "
                                "x=excluded.x, y=excluded.y, conf=excluded.conf, seq=excluded.seq WHERE excluded.seq >= det.seq",
                                [(d["id"], d["cls"], d["x"], d["y"], d["conf"], seq) for d in r["detections"]])
            self.db.executemany("INSERT INTO cas VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET x=excluded.x, "
                                "y=excluded.y, priority=excluded.priority, status=excluded.status, seq=excluded.seq "
                                "WHERE excluded.seq >= cas.seq",
                                [(c["id"], c["x"], c["y"], c["priority"], c["status"], seq) for c in r["injured"]])
        self.db.commit()

    def view(self):
        meta = {k: (a, b) for k, a, b in self.db.execute("SELECT k, a, b FROM meta")}
        out = {"origin": None, "drone": None, **{c: [] for c in CLASS_ORDER}, "injured": []}
        if "origin" not in meta:
            return out
        o = meta["origin"]
        out["origin"] = list(o)
        if "drone" in meta:
            out["drone"] = list(to_latlon(*meta["drone"], o))
        for i, cls, x, y, conf in self.db.execute("SELECT id, cls, x, y, conf FROM det ORDER BY id"):
            lat, lon = to_latlon(x, y, o)
            out[cls].append({"id": i, "lat": lat, "lon": lon, "conf": conf})
        for i, x, y, pr, st in self.db.execute("SELECT id, x, y, priority, status FROM cas ORDER BY id"):
            lat, lon = to_latlon(x, y, o)
            out["injured"].append({"id": i, "lat": lat, "lon": lon, "priority": pr, "status": st})
        return out
