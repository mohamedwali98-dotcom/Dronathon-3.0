"""On-board mission store (SQLite, survives a controller crash).

Detections are merged per physical object: a sighting joins the nearest stored object of the same
class within `merge_m` (running-mean position, max confidence), so one mine seen in 100 frames is
one row, sent once over the radio."""
import json, math, sqlite3

CLASSES = ("weapon", "litter", "mine")


class MissionStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS detections(id INTEGER PRIMARY KEY, cls TEXT, x REAL, y REAL, conf REAL,
                n_seen INTEGER, first_t REAL, last_t REAL, sent INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS casualties(id INTEGER PRIMARY KEY, x REAL, y REAL, priority INTEGER,
                status INTEGER, t REAL, sent INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS logs(t REAL, event TEXT, json TEXT);""")

    def upsert_detection(self, cls, x, y, conf, t, merge_m=3.0):
        if cls not in CLASSES:
            raise ValueError(f"unknown class {cls!r}")
        rows = self.db.execute("SELECT id, x, y, conf, n_seen FROM detections WHERE cls=?", (cls,)).fetchall()
        near = min(rows, key=lambda r: math.dist((r[1], r[2]), (x, y)), default=None)
        if near and math.dist((near[1], near[2]), (x, y)) <= merge_m:
            i, ox, oy, oc, n = near
            self.db.execute("UPDATE detections SET x=?, y=?, conf=?, n_seen=?, last_t=? WHERE id=?",
                            ((ox * n + x) / (n + 1), (oy * n + y) / (n + 1), max(oc, conf), n + 1, t, i))
            self.db.commit()
            return i, False
        cur = self.db.execute("INSERT INTO detections(cls, x, y, conf, n_seen, first_t, last_t) VALUES(?,?,?,?,1,?,?)",
                              (cls, x, y, conf, t, t))
        self.db.commit()
        return cur.lastrowid, True

    def upsert_casualty(self, id, x, y, priority, status, t):
        old = self.db.execute("SELECT priority, status FROM casualties WHERE id=?", (id,)).fetchone()
        if old == (priority, status):
            return False
        self.db.execute("INSERT OR REPLACE INTO casualties(id, x, y, priority, status, t, sent) VALUES(?,?,?,?,?,?,0)",
                        (id, float(x), float(y), priority, status, t))
        self.db.commit()
        return True

    def unsent(self):
        return {"det": self.db.execute("SELECT id, cls, x, y, conf FROM detections WHERE sent=0 ORDER BY id").fetchall(),
                "cas": self.db.execute("SELECT id, x, y, priority, status FROM casualties WHERE sent=0 ORDER BY id").fetchall()}

    def mark_sent(self, det_ids, cas_ids):
        self.db.executemany("UPDATE detections SET sent=1 WHERE id=?", [(i,) for i in det_ids])
        self.db.executemany("UPDATE casualties SET sent=1 WHERE id=?", [(i,) for i in cas_ids])
        self.db.commit()

    def mark_unsent(self, det_ids, cas_ids):
        self.db.executemany("UPDATE detections SET sent=0 WHERE id=?", [(i,) for i in det_ids])
        self.db.executemany("UPDATE casualties SET sent=0 WHERE id=?", [(i,) for i in cas_ids])
        self.db.commit()

    def seen(self, det_id):
        return self.db.execute("SELECT n_seen FROM detections WHERE id=?", (det_id,)).fetchone()[0]

    def log(self, t, event, data):
        self.db.execute("INSERT INTO logs VALUES(?,?,?)", (t, event, json.dumps(data)))
        self.db.commit()

    def counts(self):
        c = {k: 0 for k in CLASSES}
        c.update(dict(self.db.execute("SELECT cls, COUNT(*) FROM detections GROUP BY cls").fetchall()))
        c["casualties"] = self.db.execute("SELECT COUNT(*) FROM casualties").fetchone()[0]
        c["logs"] = self.db.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        return c

    def close(self):
        self.db.close()
