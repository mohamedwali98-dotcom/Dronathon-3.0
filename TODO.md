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
- [x] Onboard store + compact protocol v2 + real-map UI (plan `docs/superpowers/plans/2026-11-08-onboard-store-protocol-maps.md`):
      `drone/store.py` (SQLite, object merge 3 m) · `comms/compact.py` (numeric, flags weapon/litter/mine, < 1 KB packer)
      · `comms/geo.py` + `config/mission.json` (home base = Gammarth beach) · `vision/geolocate.py`
      · `drone/reporter.py` + `ground/receiver.py` · `ground/server.py` + `ground/web/index.html` (4 synced maps)
      — demo: `.venv/Scripts/python -m ground.demo` → http://localhost:8000
- [x] Obstacle avoidance: ≥ 1 m gap between drone body and any obstacle (static + moving, exact segment check,
      moving obstacle tracked/predicted 1 s, replan or evade); danger zones keep 5 m. Tests: min gap 1.01 m in full mission
- [x] T00 partial: `.venv` (Python 3.12, torch 2.6 cu124, ultralytics 8.4, CUDA OK on RTX 3050 6 GB)
- [x] T01 D4 injured downloaded (`DB/raw/injured/`):
      `injured_people_v11` (Injured/Uninjured, 678/113) + `goknil_v9` (Healthy/Injured, 1171/65/20)
- [x] T16 prep: `HARDWARE_COMP.md` v2 real-drone parts list (550 mm carbon, 3508-700KV + 13", Li-ion 4S3P P45B,
      Matek H743-SLIM, Pi 5 + Hailo, XIAO ESP32-S3 LoRa) — AUW 1.80 kg (no kit), TWR 2.89, ≈ 37 min mission;
      numbers from `docs/hardware_calc.py`
- [x] `docs/dashboard-design-prompt.md`: Claude Design brief for the ground-station dashboard
- [x] T15 part: `docs/slides-design-prompt.md`: Claude Design brief for the jury deck (slides not generated yet)

- [x] T00/T02/T04/T09 Webots R2025a (`D:/tmp/webots/Webots`): `sim/webots/` world generated from `sim/scenario.py`
      + Mavic controller `skyforge` (reflex PD/attitude + velocity loop vs wind, LangGraph decisions @10 Hz,
      oracle perception, moving obstacle, kit drop). Run: open `sim/webots/worlds/skyforge.wbt` (README there)
- [x] T07 part: YOLO in the Webots loop (`vision/onboard.py` + `Eyes` in the controller): camera 0.5 s -> main+people
      YOLO -> geolocate -> match; injured enter the mission only once seen. Full run: 4/5 injured seen, 3 kits, POSE,
      vision p95 75 ms. Limits: people detected as `healthy` (trained on real photos), mines not matched (box covers disc)
- [x] T14 Docker: `Dockerfile` + `docker-compose.yml` (decision stack + 2D mission + ground maps, verified)

## 🔄 In progress
- [x] T06 `vision/weights/people.pt` trained (60 ep): TEST mAP50 0.782 (injured 0.80, healthy 0.76)
- [ ] T05 `main.pt` training resumed 8 Nov 10:07 from epoch 5/40 with 2 workers (`vision/train.py main resume`),
      log `runs_main_resume.log`; on finish it copies `vision/weights/main.pt` and prints the test metrics
- [ ] T15 slides + 2 demo rehearsals (technical docs done: `docs/TECHNICAL.md`, `README.md`)

- [x] T01 D1 guns: Roboflow `firearm-detection` v1 (public domain) → `DB/raw/guns/firearm_detection_v1/`,
      classes gun/rifle, 3153/367/94 (replaces the Kaggle link, which needs a token)
- [x] T01 weapons variety: `weapons_multi_v1` (sniper-rifle, automatic-rifle, SMG, shotgun, revolver, pistol;
      4253/1215/608) + `weapons_knife_v1` (knife 1060, rifle, pistol, grenade; 6519 train only;
      drop class `smoking` at merge) in `DB/raw/guns/`

## ⛔ Blocked
- (none)

## ⬜ Remaining (in order)
### P0 — final
- [ ] T15 3 Webots runs (self-check in `MESSIONS_POINTS.md` §11), slides, 2 demo rehearsals
### P1 — scored features (gaps detailed in `docs/TECHNICAL.md` §9)
- [ ] T08 Kit allocation: a low-priority casualty found early takes a kit before higher-priority ones (F6)
- [ ] T06 Secondary vision: sim-generated dataset + `hostile_unit` class (F5)
- [ ] T07 PerceptionAgent in the 3D loop: mines not matched, 0/20 objects confirmed, zones still from the scene
- [ ] T10 `goal_update` + link + ground station in the Webots controller
- [ ] T04 Local sensor-based avoidance; variable wind + visibility
- [ ] T13 One-command metrics report (coverage, collisions, delivery accuracy, total loop p95)
- [ ] T14 ROS2 packaging (Docker done: `docker compose up` -> decision stack + maps on :8000)
### P2 — bonus
- [ ] Dashboard: draw the mission zone to start (proposed, not built)
- [ ] T16 Comms on Raspberry Pi (only if a Pi is available)
