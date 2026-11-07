# Dronathon 3.0 — Mission SKYFORGE : Task Breakdown

Source: `dronathon.pdf` (cahier des charges) + organisers' email (3 datasets).
Team: solo. Hardware: NVIDIA GPU PC. Event: 07–08 Nov 2026, ENSIT Tunis.

---

## 0. How priorities were set

Scoring (cahier §8): autonomy 20 % · decision intelligence 20 % · navigation 15 % ·
communication & resilience 15 % · adaptability 15 % · overall efficiency 15 % · F12 bonus.
Penalties: collision, entry into a danger zone, delivery off-target, impossible return.

| Priority | Meaning |
|---|---|
| **P0** | Without it the demo fails or gets penalised. Do first. |
| **P1** | Directly scored criterion. Do after P0 works end-to-end. |
| **P2** | Polish / bonus. Only if time remains. |

**Core strategy (solo):** build the full mission loop end-to-end first using
*oracle perception* (object positions read from the simulator), then swap in the real
vision models. A drone that flies the whole mission with fake perception scores far more
than perfect detectors on a drone that cannot fly.

---

## 1. Key decisions (my calls — change if you disagree)

| Topic | Decision | Why |
|---|---|---|
| Simulator | **Webots** (DJI Mavic 2 Pro model) | Easiest for a beginner, built-in drone + wind, runs on Windows, camera *Recognition* gives free bounding boxes for dataset generation |
| Language | Python 3.10+ controllers | Same language as LangGraph and YOLO |
| ROS2 | `webots_ros2` wrapper in Docker (WSL2/Ubuntu) **at packaging time** | Deliverable says Docker/ROS2; developing natively in Python first is faster |
| Detector | **YOLOv8n/YOLO11n** (Ultralytics) | Light, fast on GPU, exports to the required JSON easily |
| Orchestrator | LangGraph `StateGraph`, deterministic nodes, **no LLM call in the loop** | Cahier §3 forbids LLM in the real-time loop |
| Path planning | A* on a 2D occupancy grid (exclusion zones inflated) + local reactive avoidance | Simple, deterministic, fast (< 100 ms) |

---

## 2. Dependency graph

```
T00 Setup ──┬─> T02 Sim scene ──┬─> T04 Reflex layer ──┐
            │                   ├─> T06b Sim dataset ──┤
T01 Data ───┼─> T05 Main vision │                      │
            └─> T06 Sec. vision <┘                     │
T03 DroneState + JSON schema ──────────────────────────┼─> T09 Orchestrator + FSM
                                                       │      │
            T07 PerceptionAgent <── T05, T06, T03 ─────┘      ├─> T08 PlannerAgent ─> T11 RTH ─> T12 Delivery
            T10 Comms module   <── T03 ──────────────────────┘
T13 Logs & metrics <── T09 ; T14 Docker <── all ; T15 Docs/Demo <── all ; T16 Bonus Pi <── T10
```

**Critical path:** T00 → T02 → T03 → T04 → T09 (oracle perception) → T08 → T11 → T12 → T10 → T07 → T05/T06 → T14 → T15

---

## 3. Tasks

### T00 — Environment & repo setup · **P0**
- **Goal:** working dev environment and project skeleton.
- **Needs:** Webots R2025a+, Python 3.10+, `ultralytics`, `langgraph`, `numpy`, `opencv-python`, git, Docker Desktop + WSL2 (for T14).
- **Depends on:** nothing.
- **Done when:** Webots opens the Mavic sample world and a Python controller prints sensor values; repo has `sim/`, `drone/`, `vision/`, `comms/`, `tests/`, `docs/`.

### T01 — Dataset acquisition & audit · **P0**
- **Goal:** all datasets downloaded, converted to YOLO format, class lists and split sizes documented.
- **Datasets:**

| # | Content | Source | Access | Status |
|---|---|---|---|---|
| D1 | Guns / weapons | https://www.kaggle.com/datasets/ugorjiir/gun-detection | Kaggle token (not used) | ✅ replaced by https://universe.roboflow.com/enrique-ortiz/firearm-detection v1 → `DB/raw/guns/firearm_detection_v1/` — gun/rifle, 3153/367/94, public domain |
| D2 | Mines | https://universe.roboflow.com/mine-dyzns/detection-miwbi | Roboflow API key, export "YOLOv8" | ✅ v3 → `DB/raw/mines/roboflow_mines_v3/` — class `mine`, 1053/100/50 |
| D3 | Marine litter, 7 classes, Tunisian coast, drone images (TUN-MarineLitter) | https://zenodo.org/records/21965497 (`Data.rar` 297 MB, `Augmented data.rar` 906 MB) | public | ✅ `DB/raw/marine_litter/Data/` — YOLO, classes Cardboard/Fabrics/Glass/Metal/Other/Plastic/Wood, 2946/551/179 (≈80/15/5, re-split to 70/20/10) |
| D4a | Injured persons (chosen by team) | https://universe.roboflow.com/pcos-data-annotation/injured-people-detection (v11) | Roboflow key | ✅ `DB/raw/injured/injured_people_v11/` — Injured/Uninjured, 678/113 |
| D4b | Injured persons (chosen by team) | https://universe.roboflow.com/kaan-zcivan/goknil_detection_model (v9) | Roboflow key | ✅ `DB/raw/injured/goknil_v9/` — Healthy/Injured, 1171/65/20 |
| D4c | Injured persons, extra | **C2A** https://github.com/Ragib-Amin-Nihal/C2A (~10k UAV disaster images, 5 postures, YOLO+COCO) | public | ⬜ to download |
| D5 | Injured persons, backup | **SARD** https://ieee-dataport.org/documents/search-and-rescue-image-dataset-person-detection-sard (1,981 imgs, class *Lying*) | IEEE DataPort login | ⬜ optional |

- **Split rule:** 70 % train / 20 % val / 10 % test (cahier §3) — re-split if a dataset differs.
- **Depends on:** T00.
- **Done when:** `DB/README.md` lists per dataset: classes, image count per split, format, licence.

### T02 — 3D simulation scene (coastal zone) · **P0**
- **Goal:** Webots world that reproduces the mission.
- **Contents:** coast/sea + beach terrain, home base pad, Mavic 2 Pro, fixed obstacles (buildings, poles, trees), **≥ 1 moving obstacle**, props: mines, weapons, waste, injured persons (lying/sitting), hostile units (vehicles/people with a distinct marker), radio-shadow zones (regions), wind field, fog/visibility.
- **Needs:** Webots PROTO assets; SolidWorks models can be exported to STL → imported as `Mesh`.
- **Depends on:** T00.
- **Done when:** world loads, every object type is present, a supervisor script can list ground-truth positions of all objects (needed for oracle perception & auto-labelling).

### T03 — DroneState & JSON message contract · **P0**
- **Goal:** single shared data model used by every module (cahier §3).
- **DroneState fields:** position, velocity, battery, radio_link, weather (wind, visibility), threats/exclusion_zones, casualties (id, pos, urgency, status), current_goal, waypoints, mission_logs, phase.
- **JSON messages:** `version`, `seq`, `ts`, `type` (`telemetry`, `detection`, `goal_update`, `ack`, `log`), payload — **< 1 KB** each, compact keys.
- **Detection JSON:** `{class, confidence, bbox}` (same as jury module).
- **Depends on:** nothing (design task).
- **Done when:** `drone/state.py` (dataclass/TypedDict) + `comms/schema.py` with a test asserting every message serialises < 1024 bytes.

### T04 — Reflex layer (< 50 ms) · **P0**
- **Goal:** classical controllers that keep the drone safe regardless of the deliberative layer.
- **Includes:** attitude/altitude/position PID, waypoint following, **wind compensation** (feed-forward from wind estimate + integral term), **local obstacle avoidance** (distance sensors / lidar → repulsive vector), emergency RTH hook.
- **Depends on:** T02, T03.
- **Done when:** drone flies a square of waypoints in wind without collision; loop time measured < 50 ms p95.

### T05 — Main vision module (waste, mines, weapons) · **P1**
- **Goal:** integrate the jury's module; if it is not delivered in usable form, train our own YOLO on D1+D2+D3 as fallback.
- **Metrics:** accuracy > 90 %, recall & mAP per class; **recall prioritised for mines & weapons** (lower confidence threshold for those classes).
- **Output:** JSON `{class, confidence, bbox}`.
- **Domain gap:** mine dataset = naval sea mines in stock side-view photos → add top-down mine images
  generated in Webots (same auto-labelling as T06b) and fine-tune.
- **Depends on:** T01 (datasets).
- **Done when:** evaluation report on test split (10 %) with per-class recall/mAP; inference < 30 ms/frame on GPU.

### T06 — Secondary vision module F5 (injured + hostile units) · **P1**
- **Goal:** light detector, classes `injured`, `hostile_unit`, same JSON format.
- **T06a:** pretrain on C2A (D4) for the *injured* class.
- **T06b:** generate a simulator dataset (required by the cahier): Webots camera Recognition gives bounding boxes automatically → script flies random poses and saves images + YOLO labels; fine-tune on it.
- **Depends on:** T01, T02.
- **Done when:** recall on injured (sim test set) reported; JSON conforms to schema.

### T07 — PerceptionAgent · **P1**
- **Goal:** fuse both vision modules → world-frame objects.
- **Includes:** 2D→3D projection (camera intrinsics + drone pose + ground plane / altitude), temporal confirmation (object seen in N of M frames) to filter false positives, de-duplication by distance, exclusion zones (circle around mines/weapons/hostiles, inflated by margin).
- **Depends on:** T03, T05, T06 (can run first on oracle detections from T02).
- **Done when:** projected positions within X m of ground truth; exclusion zones written to DroneState.

### T08 — PlannerAgent · **P0**
- **Goal:** decisions + trajectories.
- **Triage score (F6):** `score = w_u·urgency + w_p·proximity`, urgency dominant; **score = 0 if battery cannot cover go + deliver + return**. Every decision logged in `mission_logs` with its inputs.
- **Path:** A* on grid avoiding inflated exclusion zones & obstacles; wind correction on heading/energy; replanning on new obstacle or `goal_update`.
- **Exploration (F1/F2):** lawn-mower coverage pattern of the zone + coverage map.
- **Depends on:** T03, T04.
- **Done when:** unit tests: rescue order matches score; unreachable casualty gets 0; path never crosses an exclusion zone.

### T09 — LangGraph orchestrator & state machine · **P0**
- **Goal:** deterministic graph implementing §7.
- **States:** INIT → EXPLORER → DÉTECTER → TRIAGE → NAVIGUER → LIVRER → (TRIAGE if casualties left, else RETOUR BASE) → POSÉ.
- **Priority interrupts (checked every cycle):** battery below threshold → RETOUR BASE; link lost → autonomous mode; goal changed → reroute.
- **Constraint:** decision ≤ 100 ms, total ≤ 150 ms (p95); no LLM call.
- **Depends on:** T03, T04 (T07/T08 plugged in as nodes).
- **Done when:** full mission runs in sim with oracle perception, zero human input, logs show every transition.

### T10 — Communication module (no agent) F9/F10 · **P1**
- **Goal:** drone ↔ ground station link resilient to outages.
- **Includes:** compact JSON (< 1 KB, version, seq), **ring buffer** (declared capacity, e.g. 256 msgs), store-and-forward during radio shadow, resync on reconnection (send missing seq range), immediate handling of `goal_update`.
- **Ground station:** jury provides one — until then a mock (UDP/WebSocket) to test.
- **Depends on:** T03.
- **Done when:** test: cut link 30 s → logs fully resynchronised after reconnection, no message > 1 KB.

### T11 — Dynamic Return-To-Home F11 · **P0**
- **Goal:** threshold recomputed every cycle = energy(distance to base, headwind) + margin + reserve; under it → forced RETOUR BASE.
- **Depends on:** T08, T09.
- **Done when:** test with strong headwind triggers RTH earlier; drone always lands with battery > reserve.

### T12 — Medical supply delivery F7 · **P1**
- **Goal:** fly to chosen casualty, hover/descend, release simulated package on target (Webots object detach/spawn), confirm.
- **Depends on:** T08, T09.
- **Done when:** package lands within radius R of the right casualty; logged.

### T13 — Mission logs & metrics · **P1**
- **Goal:** prove performance to the jury.
- **Includes:** `mission_logs` (JSON lines), latency per layer (p95), coverage %, collisions (0), danger-zone entries (0), detection recall/mAP, delivery accuracy.
- **Depends on:** T09.
- **Done when:** one command prints a metrics summary after a run.

### T14 — Docker / ROS2 packaging · **P1**
- **Goal:** deliverable "deployable in Docker/ROS2".
- **Includes:** Dockerfile (Ubuntu + ROS2 Humble/Jazzy + Webots + webots_ros2 + Python deps), launch file, README run instructions.
- **Depends on:** everything functional.
- **Done when:** fresh machine: `docker compose up` runs the mission.

### T15 — Technical docs, presentation, demo rehearsal · **P0 (at the end)**
- **Includes:** architecture diagram, design choices, metrics, slides, 2 full rehearsals of the autonomous demo.
- **Depends on:** all.

### T16 — Bonus F12: comms module on Raspberry Pi · **P2**
- **Needs:** Raspberry Pi (not available now) → **skip unless a Pi is provided**; measure memory, latency, sync.
- **Depends on:** T10.

---

## 4. Requirement → task traceability

| Req | Tasks |
|---|---|
| F1, F2 navigation/exploration/mapping | T04, T08 |
| F3, F4 waste/mines/weapons + danger zones | T05, T07 |
| F5 injured + hostile detection | T06, T07 |
| F6, F7 triage + delivery | T08, T12 |
| F8 avoidance + replanning | T04, T08 |
| F9, F10 comms + operation without link | T10, T09 |
| F11 RTH | T11 |
| F12 bonus Pi | T16 |
| Real-time budget (50/100/150 ms) | T04, T09, T13 |

## 5. Open questions / risks
- Does the jury deliver the main vision module as code/weights, or only datasets? (fallback = T05 own training)
- Exact scenario/weather/ground-station interface from the jury — keep T03 schema easy to adapt.
- ROS2 on Windows is painful → develop natively, containerise at the end (T14).
- Solo time budget: if short, cut T16, then T06b size, never cut T09/T11/T08.
