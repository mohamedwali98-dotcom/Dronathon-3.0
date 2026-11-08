"""Drone-side reporter: perception -> on-board store -> compact v2 messages over the radio link.
Only new / changed objects are sent (the store remembers what went out); the link's ring buffer
and resync take care of radio cuts."""
from comms.compact import STATUS, hello_payload, pack_reports, tel_payload

HELLO_PERIOD_S = 10.0


class Reporter:
    def __init__(self, store, link, origin, tel_period=1.0):
        self.store, self.link, self.origin, self.tel_period = store, link, origin, tel_period
        self._last_tel = self._last_hello = -1e9

    def observe(self, objects, casualties, t):
        """objects: [(cls, (x, y), conf)]; casualties: [drone.state.Casualty]."""
        for cls, (x, y), conf in objects:
            self.store.upsert_detection(cls, x, y, conf, t)
        for c in casualties:
            self.store.upsert_casualty(c.id, c.pos[0], c.pos[1], c.priority, STATUS[c.status], t)

    def tick(self, state, t):
        if t - self._last_hello >= HELLO_PERIOD_S:
            self.link.send("hello", hello_payload(self.origin), t)
            self._last_hello = t
        if t - self._last_tel >= self.tel_period:
            self.link.send("tel", tel_payload(state), t)
            self._last_tel = t
        un = self.store.unsent()
        if un["det"] or un["cas"]:
            counts = self.store.counts()
            flags = tuple(int(counts[c] > 0) for c in ("weapon", "litter", "mine"))
            for m in pack_reports(flags, int(counts["casualties"] > 0), un["det"], un["cas"], self.link.seq + 1, t):
                self.link.send("rep", m["p"], t)
            self.store.mark_sent([r[0] for r in un["det"]], [r[0] for r in un["cas"]])
