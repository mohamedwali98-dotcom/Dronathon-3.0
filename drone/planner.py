"""PlannerAgent pieces (F1/F2/F6/F8): energy model, A* around exclusion zones, triage score, coverage pattern."""
import heapq, math

import numpy as np

from drone.state import BATTERY_WH

SPEED = 8.0          # cruise ground speed m/s
P_HOVER = 100.0      # W, Mavic-class average
K_DRAG = 0.5         # W per (m/s)^2 of airspeed
DROP_S = 20.0        # hover time to deliver a kit
RESERVE_WH = 0.10 * BATTERY_WH
SAFETY_M = 5.0       # extra distance kept from every exclusion zone
W_URGENCY, W_PROX, D_MAX = 0.8, 0.2, 300.0


def energy_wh(path, wind, speed=SPEED):
    """Energy to fly a polyline at constant ground speed while compensating the wind."""
    e = 0.0
    for a, b in zip(path, path[1:]):
        d = math.dist(a, b)
        if d < 1e-9:
            continue
        ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
        air = math.hypot(speed * ux - wind[0], speed * uy - wind[1])
        e += (P_HOVER + K_DRAG * air ** 2) * (d / speed) / 3600
    return e


def hover_wh(seconds):
    return P_HOVER * seconds / 3600


def path_length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


class Grid:
    """Occupancy grid; every zone except radio shadows is inflated by SAFETY_M and blocked."""

    def __init__(self, bounds, zones, res=2.0):
        self.x0, self.y0, x1, y1 = bounds
        self.res = res
        self.nx, self.ny = int((x1 - self.x0) / res) + 1, int((y1 - self.y0) / res) + 1
        self.zones = [z for z in zones if z.kind != "radio_shadow"]
        xs = self.x0 + np.arange(self.nx) * res
        ys = self.y0 + np.arange(self.ny) * res
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        self.blocked = np.zeros((self.nx, self.ny), bool)          # precomputed once per zone update
        for z in self.zones:
            self.blocked |= np.hypot(X - z.center[0], Y - z.center[1]) <= z.radius + SAFETY_M

    def cell(self, p):
        return (min(self.nx - 1, max(0, round((p[0] - self.x0) / self.res))),
                min(self.ny - 1, max(0, round((p[1] - self.y0) / self.res))))

    def center(self, c):
        return (self.x0 + c[0] * self.res, self.y0 + c[1] * self.res)

    def blocked_at(self, p):
        return any(math.dist(p, z.center) <= z.radius + SAFETY_M for z in self.zones)

    def free_segment(self, a, b):
        n = max(1, int(math.dist(a, b) / (self.res / 2)))
        return not any(self.blocked_at((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
                       for i in range(n + 1))


def astar(grid, start, goal):
    """Shortest safe polyline start -> goal, or None if the goal cannot be reached safely."""
    if grid.blocked_at(goal) or grid.blocked_at(start[:2]):
        return None
    s, g = grid.cell(start), grid.cell(goal)
    openq, came, cost = [(0.0, s)], {s: None}, {s: 0.0}
    while openq:
        _, c = heapq.heappop(openq)
        if c == g:
            break
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (c[0] + dx, c[1] + dy)
                if (dx or dy) and 0 <= n[0] < grid.nx and 0 <= n[1] < grid.ny and not grid.blocked[n]:
                    nc = cost[c] + math.hypot(dx, dy)
                    if nc < cost.get(n, math.inf):
                        cost[n], came[n] = nc, c
                        heapq.heappush(openq, (nc + math.dist(n, g), n))
    if g not in came:
        return None
    cells = []
    while g is not None:
        cells.append(grid.center(g)); g = came[g]
    pts = [tuple(start[:2])] + cells[::-1][1:-1] + [tuple(goal)]
    out = [pts[0]]                                   # string-pulling: drop waypoints we can skip safely
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not grid.free_segment(pts[i], pts[j]):
            j -= 1
        out.append(pts[j]); i = j
    return out


def triage(state, grid, base):
    """Rank casualties: score = 0.8*urgency + 0.2*proximity; 0 if no kit, unreachable, deceased,
    already served, or the battery cannot cover go + deliver + return + reserve. Every decision is logged."""
    ranked = []
    for c in state.casualties:
        path = None
        if c.served:
            score, why = 0.0, "already_served"
        elif c.status == "possibly_deceased":
            score, why = 0.0, "possibly_deceased"
        elif state.kits <= 0:
            score, why = 0.0, "no_kits"
        else:
            path, back = astar(grid, state.pos, c.pos), astar(grid, c.pos, base)
            if path is None or back is None:
                score, why, path = 0.0, "unreachable", None
            else:
                need = energy_wh(path, state.weather.wind) + hover_wh(DROP_S) + energy_wh(back, state.weather.wind) + RESERVE_WH
                if need > state.battery_wh:
                    score, why = 0.0, f"battery_short need={need:.1f}Wh have={state.battery_wh:.1f}Wh"
                else:
                    d = path_length(path)
                    score = W_URGENCY * c.priority / 10 + W_PROX * (1 - min(d, D_MAX) / D_MAX)
                    why = f"priority={c.priority} dist={d:.0f}m need={need:.1f}Wh"
        state.log("triage", id=c.id, score=round(score, 3), why=why)
        ranked.append((score, c, path))
    ranked.sort(key=lambda r: -r[0])
    return ranked


def lawnmower(bounds, swath):
    """Back-and-forth coverage lines `swath` metres apart (swath = camera ground footprint width)."""
    x0, y0, x1, y1 = bounds
    wps, x, up = [], x0 + swath / 2, True
    while x - swath / 2 < x1:
        xc = min(x, x1)
        wps += [(xc, y0), (xc, y1)] if up else [(xc, y1), (xc, y0)]
        x, up = x + swath, not up
    return wps
