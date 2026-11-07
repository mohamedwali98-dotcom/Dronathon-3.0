# TODO — Dronathon 3.0 (Mission SKYFORGE)

Detailed tasks, needs and dependencies: [docs/TASKS.md](docs/TASKS.md)

## 🎯 Target
A simulated drone (Webots) that completes the whole mission **with zero human input**:
explore the coastal zone, detect mines/weapons/waste/injured/hostiles, triage casualties,
deliver supplies, survive radio cuts, and return home safely —
**0 collisions, 0 danger-zone entries, 0 off-target deliveries**, latency ≤ 150 ms p95,
packaged in Docker/ROS2 with docs + live demo.

## ✅ Done
- [x] Read cahier des charges, split into prioritised tasks (docs/TASKS.md)
- [x] Found injured-person dataset candidates: C2A (main), SARD (backup)
- [x] Project CLAUDE.md + TODO.md created
- [x] T01 D3 marine litter downloaded + extracted (`data/raw/marine_litter/Data/`, YOLO format, 7 classes,
      2946 train / 551 val / 179 test, CC BY 4.0, md5 verified)

- [x] T01 D2 mines downloaded (`data/raw/mines/roboflow_mines_v3/`, YOLOv8, class `mine`, 1053/100/50)
- [x] T01 D4 injured downloaded (`data/raw/injured/`):
      `injured_people_v11` (Injured/Uninjured, 678/113) + `goknil_v9` (Healthy/Injured, 1171/65/20)

## 🔄 In progress
- (nothing)

- [x] T01 D1 guns: Roboflow `firearm-detection` v1 (public domain) → `data/raw/guns/firearm_detection_v1/`,
      classes gun/rifle, 3153/367/94 (replaces the Kaggle link, which needs a token)
- [x] T01 weapons variety: `weapons_multi_v1` (sniper-rifle, automatic-rifle, SMG, shotgun, revolver, pistol;
      4253/1215/608) + `weapons_knife_v1` (knife 1060, rifle, pistol, grenade; 6519 train only;
      drop class `smoking` at merge) in `data/raw/guns/`

## ⛔ Blocked
- (none)

## ⬜ Remaining (in order)
### P0 — mission must work
- [ ] T00 Setup: Webots + Python env + repo skeleton
- [ ] T02 Webots coastal scene (obstacles, moving obstacle, props, wind, radio shadows)
- [ ] T03 DroneState + JSON schema (< 1 KB test)
- [ ] T04 Reflex layer: PID, wind compensation, local avoidance (< 50 ms)
- [ ] T09 LangGraph orchestrator + state machine with oracle perception
- [ ] T08 PlannerAgent: triage score, A*, exploration pattern
- [ ] T11 Dynamic RTH threshold
### P1 — scored features
- [ ] T12 Medical supply delivery
- [ ] T10 Comms: ring buffer, resync, goal_update, mock ground station
- [ ] T01 D4 download C2A + audit all datasets (`data/README.md`)
- [ ] T05 Main vision (jury module or own YOLO on D1+D2+D3)
- [ ] T06 Secondary vision: C2A pretrain + sim-generated dataset
- [ ] T07 PerceptionAgent: fusion, 2D→3D, filtering, exclusion zones
- [ ] T13 Logs & metrics report
- [ ] T14 Docker/ROS2 packaging
### P0 — final
- [ ] T15 Docs, slides, 2 demo rehearsals
### P2 — bonus
- [ ] T16 Comms on Raspberry Pi (only if a Pi is available)
