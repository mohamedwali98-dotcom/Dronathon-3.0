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
- [x] T01 D3 marine litter downloaded + extracted (`DB/raw/marine_litter/Data/`, YOLO format, 7 classes,
      2946 train / 551 val / 179 test, CC BY 4.0, md5 verified)

- [x] T01 D2 mines downloaded (`DB/raw/mines/roboflow_mines_v3/`, YOLOv8, class `mine`, 1053/100/50)
- [x] T01 D2 cleaned: 119 boat/ship images removed (COCO boat detector + manual review)
      → 953/87/44 left; removed files kept in `DB/removed_boats_mines/`
- [x] T01 `data/` → `DB/` (raw · processed · augmented · removed_boats_mines), see `DB/README.md`
- [x] T01 `vision/prepare_db.py`: merge + remap + polygon→box + split 70/20/10 → `DB/processed/{main,people}`
      main = mine/weapon/litter (8499/2445/1224 imgs) · people = injured/healthy (1433/396/208)
- [x] T01 `vision/augment_db.py`: drone-style offline augmentation → `DB/augmented/` (train only)
- [x] T07 part: `vision/casualty.py` (thermal + depth + motion → alive / unresponsive / possibly deceased,
      injury level 1-10, priority) + `vision/realtime.py` (booleans + injured count/levels, JSON < 1 KB)
      — 21 tests in `tests/`
- [x] T03 `drone/state.py` + `comms/schema.py` (version/seq/ts/type, every message < 1 KB, tested)
- [x] T10 `comms/link.py`: ring buffer 512, store-and-forward, resync after 30 s cut, goal_update retry+ack
- [x] T08 `drone/planner.py`: energy model w/ wind, A* around inflated zones, triage score (0 if unreachable /
      battery short / deceased / served / no kit, every decision logged), lawn-mower coverage
- [x] T11 `drone/rth.py`: dynamic RTH threshold (path energy + wind, +20 % margin, landing, 10 % reserve)
- [x] T09 `drone/orchestrator.py`: LangGraph sense → interrupts → phase node, full FSM, no LLM;
      `sim/kinematic.py` 2D mission sim w/ oracle perception: full mission 0 human input, 3/3 kits,
      0 zone entries, link loss handled, decision p95 ≈ 21 ms — 43 tests green
- [x] T00 partial: `.venv` (Python 3.12, torch 2.6 cu124, ultralytics 8.4, CUDA OK on RTX 3050 6 GB)
- [x] T01 D4 injured downloaded (`DB/raw/injured/`):
      `injured_people_v11` (Injured/Uninjured, 678/113) + `goknil_v9` (Healthy/Injured, 1171/65/20)

## 🔄 In progress
- [ ] T00 install Webots R2025a (installer downloaded to `D:/tmp/webots/`, needs the owner to run it)
- [ ] T05/T06 train `vision/weights/main.pt` + `people.pt` (`vision/train.py`), then measure latency

- [x] T01 D1 guns: Roboflow `firearm-detection` v1 (public domain) → `DB/raw/guns/firearm_detection_v1/`,
      classes gun/rifle, 3153/367/94 (replaces the Kaggle link, which needs a token)
- [x] T01 weapons variety: `weapons_multi_v1` (sniper-rifle, automatic-rifle, SMG, shotgun, revolver, pistol;
      4253/1215/608) + `weapons_knife_v1` (knife 1060, rifle, pistol, grenade; 6519 train only;
      drop class `smoking` at merge) in `DB/raw/guns/`

## ⛔ Blocked
- (none)

## ⬜ Remaining (in order)
### P0 — mission must work
- [ ] T00 Setup: Webots + Python env + repo skeleton
- [ ] T02 Webots coastal scene (obstacles, moving obstacle, props, wind, radio shadows)
- [ ] T04 Reflex layer: PID, wind compensation, local avoidance (< 50 ms)
- [ ] T09 plug orchestrator into Webots (after T02/T04)
### P1 — scored features
- [ ] T12 Medical supply delivery
- [ ] T01 D4 download C2A + audit all datasets (`DB/README.md`)
- [ ] T05 Main vision (jury module or own YOLO on D1+D2+D3)
- [ ] T06 Secondary vision: C2A pretrain + sim-generated dataset
- [ ] T07 PerceptionAgent: fusion, 2D→3D, filtering, exclusion zones
- [ ] T13 Logs & metrics report
- [ ] T14 Docker/ROS2 packaging
### P0 — final
- [ ] T15 Docs, slides, 2 demo rehearsals
### P2 — bonus
- [ ] T16 Comms on Raspberry Pi (only if a Pi is available)
