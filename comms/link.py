"""Resilient drone <-> ground link (F9/F10).

* every outgoing message gets a seq and is kept in a ring buffer (declared capacity, default 512 =
  > 100 s of 5 Hz telemetry), whether or not the radio is up (store-and-forward);
* the ground station spots seq gaps and asks for a `resync {from, to}`; the drone re-sends from the buffer;
* `goal_update` from the ground is re-sent every second until the drone `ack`s it; the drone applies
  each goal once (duplicates ignored).
`Channel` is the radio: messages sent while `up` is False are lost, like in a radio shadow.
"""
from collections import deque

from comms.schema import decode, encode, make_msg


class Channel:
    def __init__(self):
        self.up, self.to_ground, self.to_drone, self.sizes = True, deque(), deque(), []

    def send(self, queue, raw):
        self.sizes.append(len(raw))
        if self.up:
            queue.append(raw)


class RingBuffer:
    def __init__(self, capacity):
        self.items, self.dropped = deque(maxlen=capacity), 0

    def append(self, seq, raw):
        full = len(self.items) == self.items.maxlen
        self.dropped += full
        self.items.append((seq, raw))
        return full

    def range(self, lo, hi):
        return [raw for seq, raw in self.items if lo <= seq <= hi]


class DroneLink:
    def __init__(self, channel, capacity=512):
        self.ch, self.buffer, self.seq, self.logs, self._seen = channel, RingBuffer(capacity), 0, [], set()

    def send(self, type_, payload, t):
        self.seq += 1
        raw = encode(make_msg(type_, payload, self.seq, t))
        if self.buffer.append(self.seq, raw) and self.buffer.dropped % 100 == 1:
            self.logs.append({"t": t, "event": "buffer_overflow", "dropped": self.buffer.dropped})
        self.ch.send(self.ch.to_ground, raw)
        return self.seq

    def poll(self, t):
        """Handle inbound messages; returns the ones the orchestrator must act on (e.g. goal_update)."""
        out = []
        while self.ch.to_drone:
            m = decode(self.ch.to_drone.popleft())
            if m["type"] == "resync":
                for raw in self.buffer.range(m["p"]["from"], m["p"]["to"]):
                    self.ch.send(self.ch.to_ground, raw)
                continue
            self.send("ack", {"seq": m["seq"]}, t)
            if m["seq"] not in self._seen:
                self._seen.add(m["seq"])
                out.append(m)
        return out


class GroundStation:
    """Mock of the jury ground station (until the real one is available)."""

    def __init__(self, channel):
        self.ch, self.got, self.seq, self.pending, self._last_req = channel, set(), 0, {}, -1e9

    def send_goal(self, goal, t):
        self.seq += 1
        self.pending[self.seq] = make_msg("goal_update", {"goal": list(goal)}, self.seq, t)
        self.ch.send(self.ch.to_drone, encode(self.pending[self.seq]))
        self.pending[self.seq]["_sent"] = t

    def step(self, t):
        while self.ch.to_ground:
            m = decode(self.ch.to_ground.popleft())
            self.got.add(m["seq"])
            if m["type"] == "ack":
                self.pending.pop(m["p"]["seq"], None)
        for msg in self.pending.values():                       # retry unacknowledged goals
            if t - msg["_sent"] >= 1.0:
                msg["_sent"] = t
                self.ch.send(self.ch.to_drone, encode({k: v for k, v in msg.items() if k != "_sent"}))
        missing = self.missing()
        if missing and t - self._last_req >= 1.0:
            self._last_req = t
            self.seq += 1
            self.ch.send(self.ch.to_drone, encode(make_msg("resync", {"from": missing[0], "to": missing[-1]}, self.seq, t)))

    def missing(self):
        return [s for s in range(1, max(self.got, default=0)) if s not in self.got]

    def received_seqs(self):
        return sorted(self.got)
