"""Dynamic Return-To-Home (F11): threshold recomputed every cycle from distance to base, wind,
a safety margin and a fixed energy reserve. Battery at or under it -> forced RETOUR BASE."""
from drone.planner import RESERVE_WH, astar, energy_wh, hover_wh

MARGIN = 0.20        # +20 % on the trip home (model error, gusts)
LANDING_S = 30.0     # descent + landing


def rth_threshold(state, grid, base):
    path = astar(grid, state.pos, base) or [state.pos[:2], base]
    return energy_wh(path, state.weather.wind) * (1 + MARGIN) + hover_wh(LANDING_S) + RESERVE_WH


def should_rth(state, grid, base):
    return state.battery_wh <= rth_threshold(state, grid, base)
