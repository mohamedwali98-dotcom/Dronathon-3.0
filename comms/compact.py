"""Compact numeric protocol v2 (owner's design, see docs/superpowers/plans/2026-11-08-...md).

rep  p = {"h": [weapon, litter, mine],                       flags 0/1, fixed order
          "d": [[id, class, x, y, conf%], ...],               class 0 weapon, 1 litter, 2 mine
          "i": [presence, [[id, x, y, priority, status], ...]]} priority 1-10, status 0 alive,
                                                                1 unresponsive, 2 possibly deceased
tel  p = {"d": [x, y, z, battery%, phase_id, link]}
hello p = {"o": [lat, lon]}                                   home base = origin of x (east) / y (north)
Positions are metres from the home base (0.1 m). Every message is < 1 KB: rows are packed greedily
until the encoded size reaches PACK_BYTES, then a new message starts.
"""
from comms.schema import encode, make_msg

CLASS_ORDER = ("weapon", "litter", "mine")
STATUS = {"alive": 0, "alive_unresponsive": 1, "possibly_deceased": 2}
STATUS_NAME = {v: k for k, v in STATUS.items()}
PACK_BYTES = 1000


def hello_payload(origin):
    return {"o": [float(origin[0]), float(origin[1])]}


def tel_payload(state):
    from drone.orchestrator import PHASES
    from drone.state import BATTERY_WH
    x, y, z = state.pos
    return {"d": [round(x, 1), round(y, 1), round(z, 1), round(100 * state.battery_wh / BATTERY_WH),
                  PHASES.index(state.phase), int(state.link_ok)]}


def _det_row(r):
    i, cls, x, y, conf = r
    return [i, CLASS_ORDER.index(cls), round(x, 1), round(y, 1), round(conf * 100)]


def _cas_row(r):
    i, x, y, prio, status = r
    if not (isinstance(prio, int) and 1 <= prio <= 10):
        raise ValueError(f"priority must be an integer 1-10, got {prio!r}")
    if status not in STATUS_NAME:
        raise ValueError(f"status must be 0, 1 or 2, got {status!r}")
    return [i, round(x, 1), round(y, 1), prio, status]


def pack_reports(flags, injured_present, det_rows, cas_rows, seq0, t):
    items = [("d", _det_row(r)) for r in det_rows] + [("i", _cas_row(r)) for r in cas_rows]
    msgs, seq = [], seq0

    def new():
        nonlocal seq
        m = make_msg("rep", {"h": [int(bool(f)) for f in flags], "d": [], "i": [int(bool(injured_present)), []]}, seq, t)
        seq += 1
        msgs.append(m)
        return m

    m = new()
    for kind, row in items:
        target = m["p"]["d"] if kind == "d" else m["p"]["i"][1]
        target.append(row)
        if len(encode(m)) > PACK_BYTES:
            target.pop()
            m = new()
            (m["p"]["d"] if kind == "d" else m["p"]["i"][1]).append(row)
    return msgs


def unpack_report(msg):
    p = msg["p"]
    return {"flags": dict(zip(CLASS_ORDER, p["h"])),
            "injured_present": p["i"][0],
            "detections": [{"id": i, "cls": CLASS_ORDER[c], "x": x, "y": y, "conf": conf / 100} for i, c, x, y, conf in p["d"]],
            "injured": [{"id": i, "x": x, "y": y, "priority": pr, "status": STATUS_NAME[st]} for i, x, y, pr, st in p["i"][1]]}
