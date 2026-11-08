"""Train the two YOLO models on DB/augmented and copy the best weights to vision/weights/.

  python vision/train.py main      -> vision/weights/main.pt    (mine / weapon / litter)
  python vision/train.py people    -> vision/weights/people.pt  (injured / healthy)
Online augmentation in Ultralytics stays on (mosaic etc.); offline copies come from augment_db.py.
"""
import os, shutil, sys

from ultralytics import YOLO

HERE = os.path.dirname(os.path.abspath(__file__))
EPOCHS = {"main": 40, "people": 60}

def main():
    name = sys.argv[1]
    data = os.path.join(HERE, "..", "DB", "augmented", name, "data.yaml")
    if "resume" in sys.argv[2:]:               # python vision/train.py main resume  (fewer workers = less RAM)
        model = YOLO(os.path.join(HERE, "..", "runs", name, "weights", "last.pt"))
        model.train(resume=True, workers=2)
    else:
        model = YOLO("yolo11n.pt")             # n-size: fast enough for the < 100 ms decision budget
        model.train(data=data, epochs=EPOCHS[name], imgsz=640, batch=16, device=0, workers=4,
                    patience=15, project=os.path.join(HERE, "..", "runs"), name=name, exist_ok=True,
                    flipud=0.2, degrees=10)
    os.makedirs(os.path.join(HERE, "weights"), exist_ok=True)
    shutil.copy(os.path.join(model.trainer.save_dir, "weights", "best.pt"), os.path.join(HERE, "weights", f"{name}.pt"))
    metrics = YOLO(os.path.join(HERE, "weights", f"{name}.pt")).val(data=data, split="test", device=0)
    print(f"{name} TEST mAP50={metrics.box.map50:.3f} mAP50-95={metrics.box.map:.3f}")


if __name__ == "__main__":      # required on Windows: dataloader workers re-import this file
    main()
