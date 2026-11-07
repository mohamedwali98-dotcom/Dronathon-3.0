# DB — datasets (only this README is committed; images stay local)

```
DB/
├── raw/                    downloaded as-is (never edited by scripts)
│   ├── guns/               firearm_detection_v1, weapons_multi_v1, weapons_knife_v1
│   ├── mines/              roboflow_mines_v3  (boat/ship images already removed)
│   ├── marine_litter/      Data  (Zenodo, polygon labels)
│   └── injured/            injured_people_v11, goknil_v9
├── removed_boats_mines/    119 boat/ship images taken out of the mines set (kept for undo)
├── processed/              vision/prepare_db.py → merged, remapped, resized ≤640 px, split 70/20/10
│   ├── main/               0 mine · 1 weapon · 2 litter      (+ data.yaml)
│   ├── people/             0 injured · 1 healthy             (+ data.yaml)
│   └── SUMMARY.md          image / box counts per split
└── augmented/              vision/augment_db.py → train = originals + augmented copies
    ├── main/               valid/test copied unchanged (never evaluate on augmented images)
    └── people/
```

Every `<set>/<split>/` has `images/*.jpg` + `labels/*.txt` (YOLO: `class cx cy w h`, normalised).

## Rebuild from scratch
```
.venv/Scripts/python vision/prepare_db.py    # raw → processed   (~1 min)
.venv/Scripts/python vision/augment_db.py    # processed → augmented (~15 min)
.venv/Scripts/python vision/train.py main    # → vision/weights/main.pt
.venv/Scripts/python vision/train.py people  # → vision/weights/people.pt
```

## Choices
- All gun / rifle / pistol / knife / grenade / explosive classes → one class `weapon` (the drone only
  needs "weapon present: yes/no"). Class `smoking` dropped. Each weapon source capped at 2000 photos
  so weapons do not drown out mines.
- All 7 litter materials → one class `litter`.
- Polygon labels (litter, injured) converted to bounding boxes.
- Roboflow copies of the same photo stay in the same split (no train/test leakage).
- Augmentation imitates drone conditions: altitude (scale), top-down rotation/flip, motion blur,
  sea haze, sun glare, sensor noise, video compression.
