"""Drone-side reporter: perception -> on-board store -> compact v2 messages over the radio link.
Only new / changed objects are sent (the store remembers what went out). Each report is acked by the
ground; a report pushed out of the ring buffer before its ack (radio cut longer than the buffer) is
marked unsent again and re-packed. Positions are sent relative to the home base (protocol origin)."""
from comms.compact import STATUS, hello_payload, pack_reports, tel_payload

HELLO_PERIOD_S = 10.0


class Reporter:
    def __init__(self, store, link, origin, tel_period=1.0, base_xy=(0.0, 0.0)):
        self.store, self.link, self.origin, self.tel_period = store, link, origin, tel_period
        self.bx, self.by = base_xy
        self.inflight = {}                    # rep seq -> (det_ids, cas_ids) awaiting ground ack
        self._last_tel = self._last_hello = -1e9

    def observe(self, objects, casualties, t):
        """objects: [(cls, (x, y), conf)]; casualties: [drone.state.Casualty] — world coordinates."""
        for cls, (x, y), conf in objects:
            self.store.upsert_detection(cls, x - self.bx, y - self.by, conf, t)
        for c in casualties:
            self.store.upsert_casualty(c.id, c.pos[0] - self.bx, c.pos[1] - self.by, c.priority, STATUS[c.status], t)

    def on_messages(self, msgs):
        for m in msgs:
            if m["type"] == "ack":
                self.inflight.pop(m["p"]["seq"], None)

    def tick(self, state, t):
        if t - self._last_hello >= HELLO_PERIOD_S:
            self.link.send("hello", hello_payload(self.origin), t)
            self._last_hello = t
        if t - self._last_tel >= self.tel_period:
            tel = tel_payload(state)
            tel["d"][0], tel["d"][1] = round(tel["d"][0] - self.bx, 1), round(tel["d"][1] - self.by, 1)
            self.link.send("tel", tel, t)
            self._last_tel = t
        oldest = self.link.buffer.items[0][0] if self.link.buffer.items else 0
        for seq in [q for q in self.inflight if q < oldest]:          # evicted before the ground got it
            self.store.mark_unsent(*self.inflight.pop(seq))
        un = self.store.unsent()
        if un["det"] or un["cas"]:
            counts = self.store.counts()
            flags = tuple(int(counts[c] > 0) for c in ("weapon", "litter", "mine"))
            for m in pack_reports(flags, int(counts["casualties"] > 0), un["det"], un["cas"], self.link.seq + 1, t):
                seq = self.link.send("rep", m["p"], t)
                self.inflight[seq] = ([d[0] for d in m["p"]["d"]], [c[0] for c in m["p"]["i"][1]])
            self.store.mark_sent([r[0] for r in un["det"]], [r[0] for r in un["cas"]])
