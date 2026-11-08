# SKYFORGE

Autonomous recon and medical-support drone, fully simulated in 3D (Webots), for IEEE AESS/RAS ENSIT Dronathon 3.0.
It explores a coastal zone, maps hazards, ranks injured people by urgency, drops simulated medical kits,
survives radio cuts and returns home with zero human input. No weapons on board; hostile units are zones to avoid.

**Full details, measured results and known limitations: [docs/TECHNICAL.md](docs/TECHNICAL.md)**

## Quick start

| Goal | Command |
|---|---|
| 3D mission | Open `sim/webots/worlds/skyforge.wbt` in Webots R2025a and press Run ([guide](sim/webots/README.md)) |
| 2D mission + maps | `.venv/Scripts/python -m ground.demo`, then open http://localhost:8000 |
| Dashboard + maps (Windows) | `run_all.bat` |
| Docker | `docker compose up`, then open http://localhost:8000 |
| Tests | `.venv/Scripts/python -m pytest tests -q` |

## Layout

| Folder | Contents |
|---|---|
| `drone/` | Shared state, LangGraph orchestrator, planner, return-to-home, onboard store |
| `vision/` | Training, data preparation, onboard detection, casualty assessment |
| `comms/` | JSON protocol, ring buffer, resync |
| `ground/`, `UI UX/` | Ground station, detection maps, dashboard |
| `sim/` | Shared scenario, 2D simulator, Webots world and controller |
| `Hardware/` | CAD files for the real-drone concept |
| `tests/` | Automated tests |

Datasets and weights are not committed. See [DB/README.md](DB/README.md) to rebuild them.
