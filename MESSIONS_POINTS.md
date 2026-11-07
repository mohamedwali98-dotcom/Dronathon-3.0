# MESSIONS_POINTS — Dronathon 3.0 / Mission SKYFORGE (spec digest)

Plain-language, complete digest of `dronathon.pdf`. **Read this instead of the PDF.**
Every rule of the PDF has an ID (`S-xx`). Tasks that implement it → `docs/TASKS.md` (T-ids).
Event: IEEE AESS/RAS ENSIT, Tunis, 07–08 Nov 2026. Priority: **P0** must-have · **P1** scored · **P2** bonus.

---

## 1. The mission in one paragraph
A drone, fully simulated in 3D, flies **alone** (zero human input) over a **coastal zone**.
It explores and maps the area, spots **sea mines, weapons and marine waste**, finds **injured
people** and ranks them by medical urgency, stays away from **hostile units** and obstacles,
drops **simulated medical supplies** on the right injured person, keeps talking to a
**ground station** (and keeps working when the radio cuts), then **returns home safely**.
Brain = **LangGraph orchestrator** + 2 AI agents (**Perception**, **Planner**).

---

## 2. Rules that can never be broken
| ID | Rule | Prio | Tasks |
|---|---|---|---|
| S-01 | Full 3D simulation: Gazebo, Webots, AirSim or Unity, via ROS2/Python (we use Webots) | P0 | T00, T02 |
| S-02 | Scenario, weather and obstacles are **defined by the jury** → our code must accept theirs | P0 | T02, T03 |
| S-03 | **No weapon, no dangerous payload** on the drone | P0 | T12 |
| S-04 | Triage only by **medical urgency** | P0 | T08 |
| S-05 | Hostile units = **zones to avoid, never targets** | P0 | T07, T08 |
| S-06 | Reflex layer **< 50 ms** | P0 | T04, T13 |
| S-07 | Decision **≤ 100 ms** | P0 | T09, T13 |
| S-08 | Total loop **≤ 150 ms** (measured at 95th percentile) | P0 | T13 |
| S-09 | **No LLM call** inside the real-time loop (LangGraph nodes are deterministic code) | P0 | T09 |
| S-10 | Zero human intervention during the demo | P0 | T09, T15 |

## 3. Who provides what
| ID | Provided by the **jury** | Notes |
|---|---|---|
| S-11 | Main vision module (waste, mines, weapons) | if not usable → train our own (T05 fallback) |
| S-12 | 3 datasets, split **70 % train / 20 % val / 10 % test** | guns (Kaggle), mines (Roboflow), marine litter (Zenodo) |
| S-13 | Scenario, weather, ground station | interface unknown → keep our schema adaptable |

| ID | Built by **us** | Prio | Tasks |
|---|---|---|---|
| S-14 | Secondary vision module: **injured + hostile units**, dataset **generated in the simulator** | P1 | T06 |
| S-15 | Orchestrator + agents | P0 | T07–T09 |
| S-16 | Obstacles (in the scene) | P0 | T02 |
| S-17 | JSON communication protocol | P1 | T03, T10 |

---

## 4. Architecture (what each block must do)
| ID | Block | Must do | Limit | Prio | Tasks |
|---|---|---|---|---|---|
| S-18 | **Reflex layer** (classic controllers, e.g. PID) | local obstacle avoidance · return to base · wind compensation | < 50 ms | P0 | T04 |
| S-19 | **Deliberative layer** = LangGraph orchestrator | deterministic nodes, no LLM | ≤ 100 ms | P0 | T09 |
| S-20 | **PerceptionAgent** | merge both vision modules · convert 2D detections → 3D positions · filter false detections · mark exclusion zones | — | P1 | T07 |
| S-21 | **PlannerAgent** | rank injured · compute avoidance paths with wind correction · manage objectives · trigger return-to-base | — | P0 | T08, T11 |
| S-22 | **Communication module** (NOT an agent) | JSON messages · ring buffer · resync after cut · can run on Raspberry Pi (bonus) | — | P1 | T10, T16 |
| S-23 | **DroneState** shared by all agents | position, velocity, battery, radio link, weather, threats, injured, current goal, waypoints, logs, mission phase | — | P0 | T03 |

## 5. Vision modules
| ID | Module | Classes | Output | Metric | Prio | Tasks |
|---|---|---|---|---|---|---|
| S-24 | Jury module | waste, mines, weapons | JSON `{class, confidence, bbox}` | **accuracy > 90 %**, recall + mAP per class, **recall first for mines & weapons** | P1 | T05 |
| S-25 | Our module (F5) | injured, hostile unit | same JSON format | recall on injured; light pipeline; trained on sim-generated data | P1 | T06 |

Notes: "mine" = **naval sea mine** (spiked sphere), not boats. Mine dataset = stock side-view photos →
add top-down sim images. Injured data: Roboflow `injured_people_v11` + `goknil_v9` (class ids differ — remap).

---

## 6. Functional requirements (what the jury checks)
| ID | Req | What it means | Validated by | Prio | Tasks |
|---|---|---|---|---|---|
| S-26 | F1, F2 | Autonomous navigation, exploration, mapping | whole zone covered without help, wind compensated | P0 | T04, T08 |
| S-27 | F3, F4 | Detect waste, mines, weapons, danger zones | recall + mAP per class, exclusion zones recorded | P1 | T05, T07 |
| S-28 | F5 | Detect injured + hostile units | recall on injured, JSON conforms | P1 | T06, T07 |
| S-29 | F6 | Rank the injured | rescue order = score order | P0 | T08 |
| S-30 | F7 | Deliver supplies | delivery on the right target | P1 | T12 |
| S-31 | F8 | Avoid obstacles, re-plan | **0 collisions, 0 entries into danger zones** | P0 | T04, T08 |
| S-32 | F9, F10 | Communicate; keep going without radio | messages < 1 KB, logs resynced | P1 | T10, T09 |
| S-33 | F11 | Safe return to home (RTH) | return triggered by the dynamic threshold | P0 | T11 |
| S-34 | F12 | **Bonus**: comms module on a real board | memory, latency, sync measured | P2 | T16 |

### Triage score (F6) — S-35 · P0 · T08
- score = **medical urgency (main factor)** + **proximity**.
- score = **0** if the battery can't reach the injured **and** come back.
- **Every decision is written in `mission_logs`.**

### Return threshold (F11) — S-36 · P0 · T11
- Recomputed **every cycle** from: wind, distance to base, safety margin, energy reserve.
- Battery below threshold → state **RETOUR BASE forced**.

---

## 7. Environment & communication constraints
| ID | Constraint | Prio | Tasks |
|---|---|---|---|
| S-37 | Variable **wind** and **visibility** | P0 | T02, T04 |
| S-38 | **Fixed obstacles + at least 1 moving obstacle** | P0 | T02, T04 |
| S-39 | **Radio shadow zones** (link drops) | P1 | T02, T10 |
| S-40 | **Limited battery/autonomy** | P0 | T11 |
| S-41 | Any `goal_update` from the station is applied **immediately** | P1 | T09, T10 |
| S-42 | Messages: compact JSON **< 1 KB**, with **version** + **sequence number** | P1 | T03, T10 |
| S-43 | **Ring buffer capacity declared by us** (state the number in docs) | P1 | T10, T15 |

## 8. State machine — S-44 · P0 · T09
```
INIT → EXPLORER → DÉTECTER → TRIAGE → NAVIGUER → LIVRER ─┬─> TRIAGE (injured left)
                                                          └─> RETOUR BASE → POSÉ (none left)
```
Priority interrupts (checked every cycle, override the normal flow):
| Trigger | Go to |
|---|---|
| Battery under threshold | RETOUR BASE |
| Radio link lost | autonomous mode (keep mission going, buffer messages) |
| Goal changed (`goal_update`) | re-route |

---

## 9. Deliverables — S-45 · P0/P1 · T14, T15
- [ ] Source code + 3D scene, **deployable in Docker/ROS2**
- [ ] Technical documentation
- [ ] **Live demo with no human intervention**
- [ ] Oral presentation
- [ ] Bonus: demo on a real board (F12)

## 10. Scoring & penalties — S-46
| Criterion | Weight | Mainly from |
|---|---|---|
| Autonomy | 20 % | T09, T04, T11 |
| Decision intelligence | 20 % | T08, T07 |
| Navigation | 15 % | T04, T08 |
| Communication & resilience | 15 % | T10 |
| Adaptability (wind, goal_update, moving obstacle) | 15 % | T04, T09, T10 |
| Overall efficiency (time, energy, latency) | 15 % | T13 |
| Bonus F12 | extra | T16 |

**Penalties:** collision · entering a danger zone · delivery off-target · return impossible.

---

## 11. Self-check before the demo
- [ ] Mission runs start → POSÉ with zero input (S-10)
- [ ] 0 collisions, 0 danger-zone entries in 3 runs (S-31)
- [ ] p95 latencies: reflex < 50, decision ≤ 100, total ≤ 150 ms (S-06..08)
- [ ] Triage order matches score; unreachable injured = 0; all in mission_logs (S-35)
- [ ] RTH triggers earlier with headwind; lands with reserve (S-36)
- [ ] Radio cut → mission continues → logs resynced, all msgs < 1 KB (S-32, S-42)
- [ ] goal_update applied immediately (S-41)
- [ ] Recall/mAP per class reported, mines & weapons recall prioritised (S-24)
- [ ] Ring buffer capacity documented (S-43)
- [ ] `docker compose up` works on a clean machine (S-45)
