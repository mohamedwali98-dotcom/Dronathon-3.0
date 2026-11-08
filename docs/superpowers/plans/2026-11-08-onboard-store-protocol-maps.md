# Onboard Store, Compact Protocol v2 & Real-Map Detection UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The drone keeps every detection on board, sends it to the ground in a compact numeric JSON
protocol (each message < 1 KB), and the ground station draws the 4 detection maps (Armes · Blessés ·
Déchets marins · Mines) on a real geographic map.

**Architecture:** Drone side: detections are geolocated (pixel → ground metres), merged per object, and
stored in SQLite; a reporter turns new rows into packed v2 messages sent through the existing
`comms/link.py` (ring buffer + resync unchanged). Ground side: decodes v2, keeps its own SQLite, serves
`/api/view` (lat/lon) and one static page with 4 synced Leaflet maps. Positions travel as local metres
from the home base; one `hello` message carries the base's lat/lon so the ground converts to the real map.

**Tech Stack:** Python 3.12 stdlib (`sqlite3`, `json`, `http.server`, `math`), pytest; browser: Leaflet
1.9.4 + Leaflet.heat 0.2.0 (CDN), Esri World Imagery + OpenStreetMap tiles.

**Spec:** owner request of 2026-11-08 (this plan's "Protocol decisions" section records it and the
objective assessment), `MESSIONS_POINTS.md` (S-13, S-24, S-27, S-35..S-41), `docs/dashboard-design-prompt.md`
§"Page 4 — Rapport de mission".

## Protocol decisions (owner's idea, assessed)

| Owner proposal | Assessment | Decision |
|---|---|---|
| "Encrypt the data so it stays < 1 KB" | Encryption never makes data smaller: AES-GCM adds ~28 B (nonce+tag) and base64 adds +33 %. It also makes the JSON unreadable to the **jury's ground station** (S-13: their interface, our schema must stay adaptable). What shrinks the message is the *encoding* the owner describes next. | **No encryption.** Size is guaranteed by compact positional encoding + a packer that splits any report over several messages. (Optional later: an 8-byte HMAC tag for integrity, ~15 B, only if the jury asks.) |
| Booleans as 0/1 in a fixed order: gun, marine_litter, mines | Good: positional numeric arrays are ~5× smaller than named keys. | Adopted: `"h":[weapon, litter, mine]`, class ids **0 weapon · 1 litter · 2 mine** in that order. |
| Send a location with each one | Required (F3/F4 maps). One boolean per class loses *how many* and *where*. | Each object is sent **once** as a detection row `[class, x, y, conf%]`, merged on board (same class within 3 m = same object) so the radio is not flooded with the same mine 30×/s. Booleans are still sent. |
| Injured: 0/1 presence + priority 1–10 + location | Good, maps directly to the heat map. Missing: a possibly-deceased person has priority 1 and would look "low urgency" on the map. | `"i":[presence, [[x, y, priority, status], ...]]`, status **0 alive · 1 unresponsive · 2 possibly deceased** (drawn as a grey cross, not in the heat). |
| One JSON file < 1 KB | Fine as long as there is a hard guarantee. | Every message goes through `encode()` (raises ≥ 1024 B); the packer targets **≤ 1000 B**. |
| Coordinates | lat/lon at 6 decimals = 2×10 chars per point; local metres at 0.1 m = 2×5 chars. | Local metres (x east, y north, origin = home base) on the radio; `hello` carries `[lat, lon]` of the base once (re-sent on resync). |

## Algorithm choices

- **Geo conversion:** local tangent plane (equirectangular around the base): `lat = lat0 + y/R`,
  `lon = lon0 + x/(R·cos lat0)`, R = 6 378 137 m. Error < 1 cm over 1 km; no `pyproj` dependency.
- **Pixel → ground:** pinhole camera pointing straight down (nadir) at altitude h:
  ground footprint width = 2·h·tan(hfov/2); pixel offset from the image centre scaled to metres, rotated
  by drone yaw, added to drone (x, y). (Tilt/terrain via the depth camera = later, not in this plan.)
- **On-board de-duplication:** online greedy nearest-neighbour merge: a detection joins the closest stored
  object of the same class within 3 m (running-mean position, max confidence, `n_seen += 1`), else it is a
  new object. Cheaper than ground-side clustering and it is what keeps radio traffic low.
- **< 1 KB guarantee:** greedy packing by serialised size: append rows while `len(encode(msg)) ≤ 1000`,
  start a new message when full; one row never exceeds ~30 B so every row fits.
- **Storage:** SQLite (stdlib) file `runs/mission/drone.db`, WAL mode, survives a controller crash.
- **Heat map:** kernel density (Leaflet.heat), point weight = priority/10, gradient pale yellow → dark red,
  so higher priority = darker.

## Global Constraints

- Every radio message: JSON with `v` (version) and `seq`, **< 1024 bytes** (S-35); compact = positional arrays.
- Protocol version for these messages: `v = 2` (`comms/schema.py` `VERSION` becomes 2).
- Class order on the radio: `0 weapon, 1 litter, 2 mine` — the vision model's order (`mine, weapon, litter`)
  must be mapped **by name**, never by index.
- Priority is an integer 1–10; status codes 0/1/2 as above.
- No LLM, no network call in the drone loop; the drone never needs internet (map tiles are ground-side only).
- No new Python dependencies.
- Author of every commit: `mohamedwali98-dotcom`; no Claude attribution (repo hooks enforce it).

## Review Focus

1. Same physical object seen in hundreds of frames → stored and sent **once** (Task 3 test `test_repeated_sightings_merge`).
2. A report bigger than 1 KB (e.g. 150 litter items after a beach pass) → split into several messages, every item
   received exactly once (Task 4 test `test_large_report_is_split_and_lossless`).
3. Class index confusion between vision model and radio order → a mine must never be drawn as a weapon
   (Task 4 test `test_class_mapping_is_by_name`).
4. Radio cut while reporting → after resync the ground has every detection and the `hello` origin
   (Task 5 test `test_ground_gets_everything_after_radio_cut`).
5. Ground PC offline at the demo (no tile server) → maps still show markers on a plain grid background
   (Task 6 step: tile `error` fallback to a blank layer + local-metres grid).

---

### Task 1: Geo anchor & coordinate conversion

**Files:**
- Create: `config/mission.json`, `comms/geo.py`
- Test: `tests/test_geo.py`

**Interfaces:**
- Produces: `comms.geo.to_latlon(x: float, y: float, origin: tuple[float, float]) -> tuple[float, float]`,
  `comms.geo.to_local(lat: float, lon: float, origin) -> tuple[float, float]`,
  `comms.geo.load_origin(path="config/mission.json") -> tuple[float, float]`.

- [ ] **Step 1: Write the failing tests**

```python
from comms.geo import to_latlon, to_local, load_origin
O = (36.8, 10.3)
def test_100m_north_is_about_0_000899_deg():
    lat, lon = to_latlon(0.0, 100.0, O)
    assert abs(lat - O[0] - 0.000898) < 2e-6 and lon == O[1]
def test_round_trip_within_1cm_over_1km():
    for x, y in [(1000, 0), (-700, 650), (0, -1000)]:
        bx, by = to_local(*to_latlon(x, y, O), O)
        assert abs(bx - x) < 0.01 and abs(by - y) < 0.01
def test_origin_loads_from_config():
    lat, lon = load_origin()
    assert -90 <= lat <= 90 and -180 <= lon <= 180
```

- [ ] **Step 2:** `.venv/Scripts/python -m pytest tests/test_geo.py -q` → Expected: FAIL (module missing).
- [ ] **Step 3:** Implement with the equirectangular formula above; `config/mission.json` =
  `{"origin_latlon": [<lat>, <lon>], "name": "<place>"}` — **origin = the owner's chosen coastal spot**
  (default until confirmed: a beach near ENSIT/Tunis, value supplied by the owner).
- [ ] **Step 4:** same command → Expected: 3 passed.
- [ ] **Step 5:** commit `feat(comms): geo anchor and local<->lat/lon conversion`.

### Task 2: Pixel → ground geolocation

**Files:**
- Create: `vision/geolocate.py`
- Test: `tests/test_geolocate.py`

**Interfaces:**
- Produces: `vision.geolocate.pixel_to_ground(u: float, v: float, img_w: int, img_h: int, hfov_deg: float,
  drone_xyz: tuple, yaw_rad: float) -> tuple[float, float]` (x east, y north; image "up" = drone forward).

- [ ] **Step 1: Write the failing tests**

```python
import math
from vision.geolocate import pixel_to_ground
def test_image_centre_is_under_the_drone():
    assert pixel_to_ground(320, 240, 640, 480, 90, (10, 20, 30), 0.0) == (10.0, 20.0)
def test_right_edge_at_90deg_fov_is_altitude_away():
    x, y = pixel_to_ground(640, 240, 640, 480, 90, (0, 0, 30), 0.0)   # yaw 0 = facing north
    assert abs(x - 30) < 1e-6 and abs(y) < 1e-6
def test_yaw_rotates_offsets():
    x, y = pixel_to_ground(320, 0, 640, 480, 90, (0, 0, 30), math.pi / 2)  # top of image, facing west
    assert x < -1 and abs(y) < 1e-6
```

- [ ] **Step 2:** run `tests/test_geolocate.py` → Expected: FAIL.
- [ ] **Step 3:** Implement the nadir pinhole model from "Algorithm choices" (square pixels; vfov derived from aspect).
  Yaw convention: 0 = north, +π/2 = west (counter-clockwise, Webots ENU).
- [ ] **Step 4:** → Expected: 3 passed.
- [ ] **Step 5:** commit `feat(vision): pixel to ground geolocation (nadir camera)`.

### Task 3: On-board mission store (SQLite)

**Files:**
- Create: `drone/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Produces: `class MissionStore(path: str)` with
  `upsert_detection(cls: str, x: float, y: float, conf: float, t: float, merge_m: float = 3.0) -> tuple[int, bool]` (id, is_new),
  `upsert_casualty(id: int, x: float, y: float, priority: int, status: int, t: float) -> bool` (changed),
  `unsent() -> dict` (`{"det": [(id, cls, x, y, conf)], "cas": [(id, x, y, priority, status)]}`),
  `mark_sent(det_ids: list[int], cas_ids: list[int]) -> None`, `log(t: float, event: str, data: dict) -> None`,
  `counts() -> dict[str, int]`. `cls` ∈ {"weapon", "litter", "mine"}.

- [ ] **Step 1: Write the failing tests** — `test_repeated_sightings_merge` (100 sightings jittered ±1 m of the
  same mine → 1 row, `n_seen == 100`, `is_new` True only the first time); `test_different_class_same_spot_not_merged`;
  `test_objects_4m_apart_are_two_objects`; `test_unsent_then_mark_sent` (unsent shrinks to empty);
  `test_casualty_priority_change_marks_it_unsent_again`; `test_data_survives_reopen` (close, reopen same file
  → `counts()` unchanged). Use `tmp_path` for the db file.
- [ ] **Step 2:** run `tests/test_store.py` → Expected: FAIL.
- [ ] **Step 3:** Implement: tables `detections(id, cls, x, y, conf, n_seen, first_t, last_t, sent)`,
  `casualties(id PK, x, y, priority, status, t, sent)`, `logs(t, event, json)`; `PRAGMA journal_mode=WAL`;
  merge = nearest same-class row within `merge_m` (running mean of x, y; conf = max).
- [ ] **Step 4:** → Expected: 6 passed.
- [ ] **Step 5:** commit `feat(drone): on-board SQLite mission store with object merge`.

### Task 4: Compact protocol v2 + packer

**Files:**
- Create: `comms/compact.py`
- Modify: `comms/schema.py` (`VERSION = 2`; add types `"hello"`, `"rep"`, `"tel"` to `TYPES`)
- Modify: `tests/test_schema.py` (expect `v == 2`)
- Test: `tests/test_compact.py`

**Interfaces:**
- Consumes: `comms.schema.make_msg/encode/decode`, `MissionStore.unsent()` row shapes (Task 3).
- Produces: `CLASS_ORDER = ("weapon", "litter", "mine")`, `STATUS = {"alive": 0, "alive_unresponsive": 1, "possibly_deceased": 2}`,
  `hello_payload(origin) -> dict` (`{"o": [lat, lon]}`),
  `tel_payload(state) -> dict` (`{"d": [x, y, z, bat_pct, phase_id, link01]}`),
  `pack_reports(flags: tuple[int, int, int], det_rows: list, cas_rows: list, seq0: int, t: float) -> list[dict]`
  (messages `{"v":2,"seq",...,"type":"rep","p":{"h":[w,l,m],"d":[[c,x,y,conf%],...],"i":[presence,[[x,y,prio,status],...]]}}`),
  `unpack_report(msg) -> dict` (`{"flags": {...}, "detections": [...], "injured": [...]}`).

- [ ] **Step 1: Write the failing tests** — `test_flags_order_is_weapon_litter_mine`;
  `test_class_mapping_is_by_name` (row with cls "mine" → `c == 2`; unpack gives "mine");
  `test_typical_report_is_one_message_under_1kb` (3 mines, 2 weapons, 15 litter, 5 injured);
  `test_large_report_is_split_and_lossless` (150 litter + 40 injured → ≥ 2 messages, each `len(encode(m)) < 1024`,
  consecutive `seq`, union of unpacked rows == input, no duplicates); `test_priority_out_of_range_rejected`
  (0 or 11 → ValueError); `test_deceased_status_code_is_2`.
- [ ] **Step 2:** run `tests/test_compact.py` → Expected: FAIL.
- [ ] **Step 3:** Implement; numbers rounded: x, y 1 decimal, conf integer %, flags 0/1. Packer = greedy by
  `len(encode(msg)) <= 1000`.
- [ ] **Step 4:** `.venv/Scripts/python -m pytest tests -q -k "not mission"` → Expected: all pass.
- [ ] **Step 5:** commit `feat(comms): compact numeric protocol v2 with <1 KB packer`.

### Task 5: Drone reporter + ground receiver, end-to-end in the kinematic sim

**Files:**
- Create: `drone/reporter.py`, `ground/__init__.py`, `ground/receiver.py`
- Modify: `sim/kinematic.py` (World gets `objects: list[tuple[str, tuple]]` for weapon/litter/mine props;
  `run_mission(..., store_path=None, link=False)` wires reporter + `Channel`/`DroneLink`/`GroundStation`)
- Test: `tests/test_reporting.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 4; `comms.link.Channel/DroneLink/GroundStation` (unchanged).
- Produces: `Reporter(store: MissionStore, link: DroneLink, origin)` with `observe(objects, casualties, t)` and
  `tick(state, t)` (sends `hello` at start and on every resync, `tel` at 1 Hz, `rep` when unsent rows exist);
  `GroundView(path)` with `ingest(raw_msg_dict)` and `view() -> dict`
  (`{"origin":[lat,lon], "drone":[lat,lon], "weapon":[...], "litter":[...], "mine":[...], "injured":[{"lat","lon","priority","status"}]}`).
  `GroundStation` gets an optional `on_message` callback (one-line change) so the view sees every decoded message.

- [ ] **Step 1: Write the failing tests** — `test_ground_gets_everything_after_radio_cut` (world with 3 mines,
  2 weapons, 15 litter, the 4 test casualties, radio shadow on the route → ground `view()` has exactly those
  counts, positions within 0.5 m after lat/lon round-trip); `test_every_radio_message_under_1kb`
  (`max(channel.sizes) < 1024`); `test_drone_store_has_all_objects_on_landing`.
- [ ] **Step 2:** run `tests/test_reporting.py` → Expected: FAIL.
- [ ] **Step 3:** Implement. Oracle perception in the sim reports objects within `SENSOR_M` (stand-in for
  `vision/realtime.py` + `pixel_to_ground`); the reporter is the only component that touches the radio for reports.
- [ ] **Step 4:** full suite `.venv/Scripts/python -m pytest tests -q` → Expected: all pass (≈ 60).
- [ ] **Step 5:** commit `feat: on-board reporting over compact protocol, ground view`.

### Task 6: Ground server + 4 synced real-map views

**Files:**
- Create: `ground/server.py`, `ground/web/index.html`, `ground/demo.py`
- Test: `tests/test_ground_server.py`

**Interfaces:**
- Consumes: `GroundView.view()` (Task 5).
- Produces: `python -m ground.demo` (replays a full kinematic mission into `runs/mission/ground.db`, then serves
  `http://localhost:8000`); `GET /api/view` → `GroundView.view()` JSON.

- [ ] **Step 1: Write the failing test** — `test_api_view_serves_geojson_ready_data`: start `ground.server.serve(view, port=0)`
  in a thread, GET `/api/view`, assert keys `origin, drone, weapon, litter, mine, injured` and every point has
  `lat`, `lon`; GET `/` returns HTML containing `id="map-weapon"`, `map-injured`, `map-litter`, `map-mine`.
- [ ] **Step 2:** run → Expected: FAIL.
- [ ] **Step 3:** Implement `server.py` with stdlib `ThreadingHTTPServer`. `index.html`: 2×2 grid
  (Armes · Blessés · Déchets marins · Mines, FR labels, count + mean confidence per map), Leaflet 1.9.4 and
  leaflet.heat 0.2.0 from unpkg pinned versions; base layers Esri World Imagery (default) / OpenStreetMap;
  pan/zoom synced across the 4 maps (`move` event → `setView` on the others, guarded against loops);
  Blessés = heat layer (weight priority/10, gradient `{0.2:'#ffffb2',0.5:'#fd8d3c',0.8:'#e31a1c',1:'#67000d'}`) +
  numbered markers, deceased = grey ✕ outside the heat; other maps = colored circle markers (weapon purple,
  litter teal, mine orange — brief's colors) with tooltip class/conf/id; home base green, drone cyan.
  Poll `/api/view` every 1 s. Tile `tileerror` → switch to a blank layer + metre grid (Review Focus 5).
- [ ] **Step 4:** run test → Expected: PASS; then `python -m ground.demo`, open the page in the browser,
  screenshot: 4 maps on the real coastline, markers at the expected places, heat darker on priority 9–10.
- [ ] **Step 5:** commit `feat(ground): 4 synced detection maps on a real map`; update `TODO.md`; push (F3/F4/F9 done).

---

**Out of scope (later plans):** the other 3 dashboard pages; feeding real YOLO detections from Webots
(needs T02/T04 — then `vision/realtime.py` + `pixel_to_ground` replace the oracle in `Reporter.observe`);
optional HMAC integrity tag.
