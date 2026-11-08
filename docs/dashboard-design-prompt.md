# Design brief — SKYFORGE Ground Station (drone mission dashboard)

## Context
SKYFORGE is an autonomous recon & medical-support drone (fully simulated in Webots) built for the
IEEE AESS/RAS ENSIT Dronathon 3.0. It flies alone over a coastal zone, maps it, detects
**weapons, sea mines, marine litter and injured people**, ranks the injured by medical urgency,
avoids hostile units (zones to avoid — never targets), drops simulated medical supplies, keeps
talking to a ground station (and keeps working when the radio drops), then returns home.
The audience is a **jury watching a live demo** and the operator during development.
No weapons, no targeting, nothing aggressive: hostile units are drawn as no-go zones only.

Build an **interactive web dashboard** (not static images): one app, 4 pages, left sidebar nav,
driven by a **mock data simulator** that replays a full mission (INIT → POSÉ) at adjustable speed,
with a clean adapter so it can later read live JSON from a WebSocket.

## Visual direction
- Mission-control / tactical-ops look: dark theme by default (light theme toggle), high contrast,
  dense but calm. Monospace numerals for telemetry. Subtle grid, no gimmicky glow.
- Fixed semantic colors used everywhere:
  - Injured = red→amber→yellow by urgency · Mines = orange · Weapons = purple ·
    Marine litter = teal · Hostile/danger zones = hatched red · Radio shadow = grey hatched ·
    Obstacles = slate (moving obstacle animated) · Drone = white/cyan · Home base = green.
- Status chips: OK (green) / Warning (amber) / Critical (red), with icons, never color alone.
- UI language French by default, EN toggle. Units SI (m, m/s, %, ms).
- Responsive down to a laptop at 1366px; the live page must also look good full-screen on a projector.

## Shared data model (DroneState — every page reads this)
```json
{
  "version": "1.0", "seq": 1842, "t": 312.4,
  "phase": "NAVIGUER",
  "mode": "AUTONOMOUS",
  "position": {"x": 42.1, "y": -17.8, "z": 12.0}, "heading_deg": 87,
  "velocity": {"vx": 3.1, "vy": 0.4, "vz": 0.0},
  "battery": {"pct": 61, "rth_threshold_pct": 34, "est_range_m": 820},
  "link": {"connected": true, "rssi_dbm": -71, "latency_ms": 38, "buffered_msgs": 0, "buffer_capacity": 256},
  "weather": {"wind_speed": 6.2, "wind_dir_deg": 240, "visibility_m": 900},
  "threats": [{"id": "H1", "type": "hostile", "x": 80.0, "y": 20.0, "radius": 15, "moving": false}],
  "injured": [{"id": "V3", "x": 60.0, "y": -30.0, "urgency": 0.9, "proximity": 0.6, "score": 0.82,
               "reachable": true, "status": "en_route"}],
  "detections": [{"id": "D17", "class": "mine", "conf": 0.93, "x": 12.5, "y": 40.2, "t": 205.1}],
  "current_goal": {"type": "deliver", "target": "V3"},
  "waypoints": [{"x": 50.0, "y": -20.0}, {"x": 60.0, "y": -30.0}],
  "latency": {"reflex_ms": 21, "decision_ms": 64, "total_ms": 97},
  "logs": [{"t": 310.2, "level": "decision", "msg": "Triage: V3 score 0.82 > V1 0.55"}]
}
```
Allowed values:
- `phase`: INIT | EXPLORER | DÉTECTER | TRIAGE | NAVIGUER | LIVRER | RETOUR_BASE | POSÉ
- `mode`: NOMINAL | AUTONOMOUS (autonomous = radio link lost)
- `threats[].type`: hostile | mine | obstacle
- `injured[].status`: pending | en_route | delivered
- `detections[].class`: weapon | mine | litter | injured | hostile
- `logs[].level`: info | warn | decision

Show the live message size (bytes) and flag it if ≥ 1 KB (spec: messages < 1 KB with version + seq).

## Page 1 — Carte (live mission map) ← the hero page
Large 2D top-down map of the coastal zone (land/sea boundary, local metres, scale bar, north arrow).

Layers (toggleable in a layer panel):
- Drone icon rotated to heading, fading trail, planned path + numbered waypoints, home base.
- Explored-coverage grid (cells fill in as the zone gets covered, with a % covered counter).
- Danger zones (hostile units, mine exclusion radius) hatched; obstacles, the moving one animated.
- Radio shadow zones; wind vector arrow; visibility indicator.
- Detections as class icons; injured as numbered markers = their triage rank.
- RTH "return circle": ring showing how far the drone can still go and get home.

Interactions:
- Pan/zoom; hover a marker → tooltip (class, confidence, time); click an injured → side card with score breakdown.
- "Follow drone" toggle.
- Timeline scrubber at the bottom to replay the mission (play/pause, 1×/2×/5×/10×) with event ticks
  (detections, state changes, link loss).

Top bar: phase chip, mode chip, battery, link, mission clock, alert toasts
(link lost, RTH forced, goal_update received, danger-zone proximity).

## Page 2 — État (status / telemetry)
Card grid, all live:
- **Phase de mission**: interactive state-machine diagram
  INIT → EXPLORER → DÉTECTER → TRIAGE → NAVIGUER → LIVRER → (TRIAGE | RETOUR BASE) → POSÉ,
  current node highlighted; interrupt arrows (low battery → RTH, link lost → autonomous,
  goal_update → reroute) flash when triggered.
- **Altitude** (big number + sparkline), **Position** (x, y, z + mini-map), **Vitesse**
  (ground speed + vector, sparkline).
- **Batterie**: gauge with the *dynamic RTH threshold* drawn as a moving marker; chart of
  battery % vs threshold over time (the threshold changes with wind/distance — make that visible).
- **Lien radio**: connected/lost, RSSI, latency, ring-buffer fill bar (n / capacity), resync events.
- **Météo**: wind speed + direction compass, visibility.
- **Menaces**: list with type, distance, "inside zone?" (should always be no).
- **Blessés**: triage queue table sorted by score — rank, urgency, proximity, score, reachable
  (score 0 if battery can't go + return, shown greyed with the reason), status.
- **Objectif courant** + **Waypoints** list (current one highlighted, ETA).
- **Latence**: reflex / decision / total vs budgets 50 / 100 / 150 ms, with live p95.
- **Journaux** (mission_logs): streaming log console, filter by level (info/warn/decision),
  search, auto-scroll toggle, export JSON/CSV.

## Page 3 — Documentation (interactive, not a static text page)
A guided technical doc with live widgets:
- Clickable architecture diagram: Reflex layer (PID, < 50 ms) · LangGraph orchestrator
  (deterministic nodes, no LLM in the loop, ≤ 100 ms) · PerceptionAgent · PlannerAgent ·
  Communication module · DroneState. Click a block → panel with role, inputs/outputs, limits.
- Animated state machine you can step through (buttons to trigger each interrupt).
- **Triage calculator**: sliders for urgency, distance, battery → shows the score and when it drops to 0.
- **RTH threshold calculator**: sliders for wind, distance to base, margin, reserve → threshold.
- **JSON message playground**: editable message, live byte counter vs 1 KB, version/seq check.
- Ring buffer demo: simulate a link cut, watch messages buffer and resync.
- Vision section: classes, datasets, split 70/20/10, metrics table (recall, mAP per class;
  recall prioritised for mines & weapons).
- Requirements checklist F1–F12 with status chips. Sticky table of contents, search.

## Page 4 — Rapport de mission (post-mission detection maps)
Unlocks when the phase reaches POSÉ (also openable for any replayed mission).
- 2×2 grid of 4 maps: **Armes · Blessés · Déchets marins · Mines**, each with count + avg confidence.
- **Pan/zoom synced** across the 4 maps (toggle to unsync); click a map to expand it full width.
- Per-map **view selector** (segmented control):
  1. **Étiqueté**: markers with ID, class, confidence, timestamp; clustered when zoomed out.
  2. **Heatmap**: detection density (adjustable radius).
  3. **Priorité**: Blessés = colored by triage score with rescue-order lines;
     Mines/Armes = risk radius / exclusion zones; Déchets = density clusters for cleanup priority.
  4. **Hexbin**: counts per hex cell (cleaner than a heatmap for presentations).
- Global controls: confidence threshold slider, time-range filter, "apply view to all 4" button.
- **Ground-truth overlay** (if available): TP green / FP red / FN hollow → per-class recall and
  precision shown live.
- Summary strip: coverage %, flight time, energy used, deliveries (on target / off target),
  collisions (0), danger-zone entries (0), link-loss time, p95 latencies.
- Export: PNG per map, full PDF report, JSON/CSV of detections.

## Deliverable
A working interactive prototype with realistic mock data: one full mission scenario with
~5 injured, 3 mines, 2 weapons, ~15 litter items, 2 hostile zones, 1 moving obstacle,
1 radio shadow zone, 1 link-loss event and 1 mid-mission goal_update.
Also include empty, loading and link-lost states.
Keep the data layer separate (a single `useDroneState()` / store fed by the simulator) so
swapping in a live WebSocket is a one-line change.
