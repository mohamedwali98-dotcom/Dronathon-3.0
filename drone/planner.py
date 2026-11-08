"""PlannerAgent pieces (F1/F2/F6/F8): energy model, A* around exclusion zones, triage score, coverage pattern."""
import heapq, math

import numpy as np

from drone.state import BATTERY_WH

SPEED = 8.0          # cruise ground speed m/s
P_HOVER = 100.0      # W, Mavic-class average
K_DRAG = 0.5         # W per (m/s)^2 of airspeed
DROP_S = 20.0        # hover time to deliver a kit
RESERVE_WH = 0.10 * BATTERY_WH
SAFETY_M = 5.0       # extra distance kept from danger zones (mine / weapon / hostile)
CLEARANCE_M = 1.0    # minimum gap between the drone body and a physical obstacle (owner requirement)
DRONE_RADIUS_M = 0.3 # Mavic 2 half-span incl. propellers
T_PREDICT_S = 1.0    # moving obstacles are inflated by the distance they cover in this time
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


def keep_out(z):
    """Distance from a zone centre that the drone centre must stay beyond."""
    if z.kind == "obstacle":
        return z.radius + DRONE_RADIUS_M + CLEARANCE_M + z.speed * T_PREDICT_S
    return z.radius + SAFETY_M


def _seg_dist(a, b, c):
    ax, ay = a[0], a[1]; bx, by = b[0], b[1]
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((c[0] - ax) * (bx - ax) + (c[1] - ay) * (by - ay)) / L2))
    return math.dist((ax + u * (bx - ax), ay + u * (by - ay)), c)


def path_length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


class Grid:
    """Occupancy grid; every zone except radio shadows is blocked out to keep_out(z). Grid cells are padded by
    half a cell diagonal so straight moves between free cell centres also respect keep_out exactly."""

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
            self.blocked |= np.hypot(X - z.center[0], Y - z.center[1]) <= keep_out(z) + res * 0.7072

    def cell(self, p):
        return (min(self.nx - 1, max(0, round((p[0] - self.x0) / self.res))),
                min(self.ny - 1, max(0, round((p[1] - self.y0) / self.res))))

    def center(self, c):
        return (self.x0 + c[0] * self.res, self.y0 + c[1] * self.res)

    def blocked_at(self, p):
        return any(math.dist(p[:2], z.center) <= keep_out(z) for z in self.zones)

    def free_segment(self, a, b):
        """Exact: the whole segment stays beyond keep_out of every zone."""
        return all(_seg_dist(a, b, z.center) > keep_out(z) for z in self.zones)


def astar(grid, start, goal):
    """Shortest safe polyline start -> goal, or None if the goal cannot be reached safely."""
    if grid.blocked_at(goal) or grid.blocked_at(start[:2]):
        return None
    s, g = grid.cell(start), grid.cell(goal)
    if s == g:
        return [tuple(start[:2]), tuple(goal)] if grid.free_segment(start[:2], goal) else None
    openq, came, cost = [(0.0, s)], {s: None}, {s: 0.0}
    while openq:
        _, c = heapq.heappop(openq)
        if c == g:
            break
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (c[0] + dx, c[1] + dy)
                if not ((dx or dy) and 0 <= n[0] < grid.nx and 0 <= n[1] < grid.ny):
                    continue
                # padded cells next to the true start / goal are allowed when the real segment is clear
                ok = not grid.blocked[n]
                if c == s:
                    ok = grid.free_segment(start[:2], grid.center(n)) and (ok or not grid.blocked_at(grid.center(n)))
                if n == g:
                    ok = grid.free_segment(start[:2] if c == s else grid.center(c), goal)
                if ok:
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
