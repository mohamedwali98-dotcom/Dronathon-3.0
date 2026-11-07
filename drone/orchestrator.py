"""Deterministic LangGraph orchestrator (§7). One `cycle()` per control tick, no LLM anywhere.

Graph per cycle:   START -> sense -> interrupts -> <current phase node> -> END
Phases: INIT -> EXPLORER -> DETECTER -> TRIAGE -> NAVIGUER -> LIVRER -> (TRIAGE | RETOUR_BASE) -> POSE
Interrupts (checked every cycle, in this priority order):
  1. battery under the dynamic RTH threshold -> RETOUR_BASE (overrides everything, even goal_update)
  2. radio link lost -> keep flying autonomously (logged; comms buffers messages)
  3. goal_update from the ground -> reroute (NAVIGUER to the goal, then resume exploring)
The orchestrator only sets `state.goal` (next waypoint); the reflex layer / simulator flies to it.
"""
import math
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from drone.planner import DROP_S, Grid, astar, lawnmower, triage
from drone.rth import should_rth

ARRIVE_M = 1.5
PHASES = ("INIT", "EXPLORER", "DETECTER", "TRIAGE", "NAVIGUER", "LIVRER", "RETOUR_BASE", "POSE")


class _G(TypedDict):
    m: Any


class Mission:
    def __init__(self, state, bounds, base, perceive, swath=40.0):
        self.s, self.bounds, self.base, self.perceive, self.swath = state, bounds, tuple(base), perceive, swath
        self.grid = Grid(bounds, state.zones)
        self.coverage, self.path, self.pending, self.inbox = [], [], [], []
        self.target, self.drop_left, self.dt, self._link = None, 0.0, 0.1, True
        self.graph = self._build()

    # ---------- helpers ----------
    def phase(self, to, why):
        self.s.log("phase", **{"from": self.s.phase, "to": to, "why": why})
        self.s.phase = to

    def plan_to(self, xy):
        p = astar(self.grid, self.s.pos, xy)
        self.path = p[1:] if p else []
        return p is not None

    def follow(self):
        while self.path and math.dist(self.s.pos[:2], self.path[0]) < ARRIVE_M:
            self.path.pop(0)
        self.s.goal = self.path[0] if self.path else None

    def near(self, xy):
        return math.dist(self.s.pos[:2], xy) < ARRIVE_M

    def cycle(self, dt):
        self.dt = dt
        self.graph.invoke({"m": self})

    # ---------- graph nodes ----------
    def _sense(self, g):
        if self.s.phase in ("INIT", "POSE"):
            return {}
        zones, casualties = self.perceive(self.s)
        new_z = [z for z in zones if all(z.center != k.center for k in self.s.zones)]
        if new_z:
            self.s.zones += new_z
            self.grid = Grid(self.bounds, self.s.zones)
            for z in new_z:
                self.s.log("zone", kind=z.kind, c=list(z.center), r=z.radius)
            if self.path:                                           # replan around the new hazard
                end = self.path[-1]
                if not self.plan_to(end) and self.s.phase == "EXPLORER":
                    self.coverage = [w for w in self.coverage if w != end]
        known = {c.id for c in self.s.casualties} | {c.id for c in self.pending}
        self.pending += [c for c in casualties if c.id not in known]
        return {}

    def _interrupts(self, g):
        s = self.s
        if s.link_ok != self._link:
            s.log("link_lost" if not s.link_ok else "link_restored")
            self._link = s.link_ok
        if s.phase in ("INIT", "RETOUR_BASE", "POSE"):
            if s.phase == "RETOUR_BASE" and self.inbox and not should_rth(s, self.grid, self.base):
                self._reroute(self.inbox.pop(0))
            return {}
        if should_rth(s, self.grid, self.base):
            s.log("low_battery_rth", battery_wh=round(s.battery_wh, 2))
            self.inbox.clear()
            self.path = []
            self.phase("RETOUR_BASE", "battery under dynamic RTH threshold")
        elif self.inbox:
            self._reroute(self.inbox.pop(0))
        return {}

    def _reroute(self, goal):
        self.s.log("reroute", goal=list(goal))
        self.target = ("goal", tuple(goal))
        self.plan_to(tuple(goal))
        self.phase("NAVIGUER", "goal_update from ground station")

    def _init(self, g):
        self.coverage = lawnmower(self.bounds, self.swath)
        self.phase("EXPLORER", f"{len(self.coverage)} coverage waypoints")
        return {}

    def _explorer(self, g):
        if self.pending:
            self.phase("DETECTER", f"{len(self.pending)} new casualty(ies)")
            return {}
        while self.coverage and (self.near(self.coverage[0]) or self.grid.blocked_at(self.coverage[0])):
            self.coverage.pop(0)
        while self.coverage and (not self.path or self.path[-1] != self.coverage[0]):
            if self.plan_to(self.coverage[0]):
                break
            self.coverage.pop(0)
        if not self.coverage:
            self.phase("TRIAGE", "coverage complete")
            return {}
        self.follow()
        return {}

    def _detecter(self, g):
        for c in self.pending:
            self.s.casualties.append(c)
            self.s.log("casualty", id=c.id, pos=[round(v, 1) for v in c.pos], status=c.status, severity=c.severity)
        self.pending = []
        self.phase("TRIAGE", "casualties registered")
        return {}

    def _triage(self, g):
        ranked = triage(self.s, self.grid, self.base)
        if ranked and ranked[0][0] > 0:
            score, c, path = ranked[0]
            self.target, self.path = ("casualty", c), path[1:]
            self.phase("NAVIGUER", f"casualty {c.id} score {score:.2f}")
        elif self.coverage:
            self.path = []
            self.phase("EXPLORER", "no deliverable casualty, resume coverage")
        else:
            self.path = []
            self.phase("RETOUR_BASE", "mission complete")
        return {}

    def _naviguer(self, g):
        kind, tgt = self.target
        xy = tgt.pos if kind == "casualty" else tgt
        if self.near(xy):
            if kind == "casualty":
                self.drop_left = DROP_S
                self.s.goal = None
                self.phase("LIVRER", f"over casualty {tgt.id}")
            else:
                self.s.log("goal_reached", goal=list(xy))
                self.path = []
                self.phase("EXPLORER" if self.coverage else "RETOUR_BASE", "goal reached")
            return {}
        if not self.path and not self.plan_to(xy):
            self.phase("TRIAGE", "target became unreachable")
            return {}
        self.follow()
        return {}

    def _livrer(self, g):
        self.s.goal = None                                          # hover over the casualty
        self.drop_left -= self.dt
        if self.drop_left <= 0:
            c = self.target[1]
            c.served, self.s.kits = True, self.s.kits - 1
            self.s.log("delivered", id=c.id, kits_left=self.s.kits)
            self.phase("TRIAGE", "kit dropped")      # TRIAGE resumes coverage or returns home
        return {}

    def _retour(self, g):
        if self.near(self.base):
            self.s.goal = None
            self.s.log("landed", battery_wh=round(self.s.battery_wh, 2))
            self.phase("POSE", "at base")
            return {}
        if not self.path or self.path[-1] != self.base:
            self.plan_to(self.base)
        self.follow()
        return {}

    def _pose(self, g):
        self.s.goal = None
        return {}

    def _build(self):
        b = StateGraph(_G)
        nodes = {"INIT": self._init, "EXPLORER": self._explorer, "DETECTER": self._detecter,
                 "TRIAGE": self._triage, "NAVIGUER": self._naviguer, "LIVRER": self._livrer,
                 "RETOUR_BASE": self._retour, "POSE": self._pose}
        b.add_node("sense", self._sense)
        b.add_node("interrupts", self._interrupts)
        for name, fn in nodes.items():
            b.add_node(name, fn)
            b.add_edge(name, END)
        b.add_edge(START, "sense")
        b.add_edge("sense", "interrupts")
        b.add_conditional_edges("interrupts", lambda g: g["m"].s.phase, {p: p for p in PHASES})
        return b.compile()
