"""JSON message contract drone <-> ground station: version, seq, ts, type, payload; always < 1 KB."""
import json

VERSION = 2
MAX_BYTES = 1024
TYPES = {"telemetry", "detection", "goal_update", "ack", "log", "resync", "hello", "rep", "tel"}


def make_msg(type_, payload, seq, ts):
    if type_ not in TYPES:
        raise ValueError(f"unknown message type {type_!r}")
    return {"v": VERSION, "seq": seq, "ts": round(ts, 2), "type": type_, "p": payload}


def encode(msg):
    raw = json.dumps(msg, separators=(",", ":")).encode()
    if len(raw) >= MAX_BYTES:
        raise ValueError(f"message {msg.get('type')} seq {msg.get('seq')} is {len(raw)} B (limit {MAX_BYTES})")
    return raw


def decode(raw):
    return json.loads(raw)
