"""DroneState: the one shared data model every module reads and writes (cahier §3).
Units: metres, m/s, seconds, Wh. Ground plane = (x, y); altitude = z."""
from dataclasses import dataclass, field

BATTERY_WH = 59.3          # DJI Mavic 2 Pro: 3850 mAh x 15.4 V


@dataclass
class Casualty:
    id: int
    pos: tuple                 # (x, y)
    severity: int              # 1-10 from vision/casualty.py
    priority: int              # 1-10 (possibly deceased -> 1)
    status: str                # alive | alive_unresponsive | possibly_deceased
    served: bool = False


@dataclass
class Zone:
    center: tuple              # (x, y)
    radius: float
    kind: str                  # mine | weapon | hostile | radio_shadow


@dataclass
class Weather:
    wind: tuple = (0.0, 0.0)   # (wx, wy) m/s, direction the air moves to
    visibility: float = 1000.0


@dataclass
class DroneState:
    pos: tuple = (0.0, 0.0, 0.0)
    vel: tuple = (0.0, 0.0, 0.0)
    battery_wh: float = BATTERY_WH
    link_ok: bool = True
    weather: Weather = field(default_factory=Weather)
    zones: list = field(default_factory=list)
    casualties: list = field(default_factory=list)
    kits: int = 3              # medical kits on board
    goal: tuple | None = None
    waypoints: list = field(default_factory=list)
    phase: str = "INIT"
    t: float = 0.0
    mission_logs: list = field(default_factory=list)

    def log(self, event, **data):
        self.mission_logs.append({"t": round(self.t, 2), "event": event, **data})

    def telemetry(self):
        """Compact summary for the ground station (always < 1 KB)."""
        return {"p": [round(v, 1) for v in self.pos], "v": [round(v, 1) for v in self.vel],
                "bat": round(100 * self.battery_wh / BATTERY_WH, 1), "link": self.link_ok,
                "ph": self.phase, "goal": None if self.goal is None else [round(v, 1) for v in self.goal],
                "cas": len(self.casualties), "served": sum(c.served for c in self.casualties),
                "zones": len(self.zones), "kits": self.kits}
