# CLAUDE.md — Dronathon 3.0 (Mission SKYFORGE)

Autonomous recon & support drone, fully simulated in 3D, for IEEE AESS/RAS ENSIT Dronathon 3.0
(07–08 Nov 2026). **Spec digest: `MESSIONS_POINTS.md` (read this, not the PDF; rules have S-ids).**
Original spec: `dronathon.pdf`. Task plan: `docs/TASKS.md` (T-ids). Progress: `TODO.md`.

## Working rules
- Update `TODO.md` (Done / In progress / Remaining) whenever a task changes state.
- Solo developer, beginner in simulation (knows SolidWorks) → explain sim/ROS steps simply.
- Build end-to-end with oracle perception first, real vision second.
- Keep this file under 200 lines.

## Git (owner rule — MUST)
- Repo: github.com/mohamedwali98-dotcom/Dronathon-3.0 (public). Push after each completed F-requirement.
- Author is ONLY `mohamedwali98-dotcom`. Never add Co-Authored-By Claude, "Generated with Claude Code"
  or any Claude/Anthropic credit. Enforced by `.claude/settings.json` (attribution off + PreToolUse hook)
  and `.githooks/` (commit-msg strips, pre-push blocks). Never commit `data/raw/`, weights, PDFs, API keys.

## Hard constraints from the spec (never break)
- No weapons / dangerous payload. Triage by medical urgency. Hostile units = zones to avoid, never targets.
- Reflex layer < 50 ms, decision ≤ 100 ms, total ≤ 150 ms (p95).
- LangGraph orchestrator with deterministic nodes — **no LLM call in the real-time loop**.
- JSON messages < 1 KB, with `version` and `seq`; ring buffer + resync after link loss.
- Triage score: urgency (main) + proximity; **0 if battery can't go + return**. Log every decision in `mission_logs`.
- RTH threshold recomputed every cycle (wind, distance to base, margin, energy reserve).
- State machine: INIT → EXPLORER → DÉTECTER → TRIAGE → NAVIGUER → LIVRER → (TRIAGE | RETOUR BASE) → POSÉ.
  Interrupts: low battery → RTH, link lost → autonomous, goal_update → reroute.
- Penalties: collision, danger-zone entry, off-target delivery, failed return.

## Stack (decided)
- Webots (Mavic 2 Pro) + Python controllers; ROS2 via `webots_ros2` in Docker at packaging time.
- Ultralytics YOLO (n-size) for both vision modules; LangGraph for the orchestrator.

## Layout (planned)
- `sim/` Webots worlds, PROTOs, supervisor
- `drone/` state, reflex controllers, agents (perception, planner), orchestrator
- `vision/` training/eval scripts, weights
- `comms/` JSON schema, ring buffer, ground-station mock
- `data/raw/` downloaded datasets (not committed) · `tests/` · `docs/`

## Datasets
- D1 guns: kaggle.com/datasets/ugorjiir/gun-detection (needs Kaggle token)
- D2 mines: universe.roboflow.com/mine-dyzns/detection-miwbi (needs Roboflow key)
- D3 marine litter: zenodo.org/records/21965497 (public)
- D4 injured: C2A github.com/Ragib-Amin-Nihal/C2A · backup SARD (IEEE DataPort)
- Split 70/20/10 train/val/test.
