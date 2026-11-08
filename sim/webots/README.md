# SKYFORGE — Webots 3D simulation

Mavic 2 Pro flown by our decision stack (LangGraph orchestrator + planner + RTH), **zero human input**.

## Run the demo
1. (Only after changing `sim/scenario.py`) regenerate the world:
   `.venv/Scripts/python sim/webots/make_world.py`
2. Open `sim/webots/worlds/skyforge.wbt` in Webots R2025a (File → Open World).
3. Press ▶ (Run real-time) or ⏩ (Fast). The drone takes off, sweeps the zone, finds the injured,
   drops kits on the 3 highest-priority reachable ones, avoids the building, trees and the moving
   (yellow) obstacle, flies through the radio shadow (grey dome), returns home and lands.
4. The Webots console shows each phase change, kit drop and the final summary.
   Results: `runs/webots/summary.json` and `runs/webots/mission_logs.jsonl`.

The controller uses the project venv through `controllers/skyforge/runtime.ini`. If the repo moves,
fix the path in that file.

Headless check (no window):
`SKYFORGE_QUIT=1 webots --mode=fast --no-rendering --stdout --batch --minimize sim/webots/worlds/skyforge.wbt`

## What is in the scene
| Colour | Object |
|---|---|
| Green disc | Home base |
| Lying people, red / yellow shirt | Injured (red = high priority) |
| Black spheres + orange disc | Sea mines + exclusion zone |
| Red disc + dark box | Hostile unit = zone to avoid (never a target) |
| Grey dome | Radio shadow (link lost → autonomous mode) |
| Grey block / green cylinders | Building / trees (25 m high, above flight altitude) |
| Yellow column | Moving obstacle |
| Small purple / cyan items | Weapons / marine litter |
| White box | Dropped medical kit |

## Perception: YOLO in the loop (default)
- Every 0.5 s the down-looking camera frame (640×480, 69° FOV) goes through **both YOLO models**:
  `runs/main/weights/best.pt` (mine / weapon / litter) and `vision/weights/people.pt` (injured / healthy).
- Each box centre is converted to a ground position (`vision/geolocate.py`) and matched to the scene (≤ 6 m).
- **An injured person enters the mission only after YOLO has seen it.** The severity still comes from the
  scenario: the thermal/depth casualty assessment is not simulated.
- **Danger zones and obstacles always come from the scene**, for safety: the drone never relies on a detection to avoid a mine.
- Sweep lanes are spaced to match the camera footprint (85 % of it), so the camera sees the whole zone.
- The **"yolo" display** (robot overlay in the 3D view) shows the camera with boxes. Example frames go to
  `runs/webots/frames/`, every detection to `runs/webots/detections.jsonl`, and the stats to `summary.json`.
- Oracle-only mode: set the environment variable `SKYFORGE_PERCEPTION=oracle` before starting Webots.
