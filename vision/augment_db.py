"""Offline data augmentation: DB/processed/<set> -> DB/augmented/<set>.

Train split = originals + N augmented copies (drone-like conditions: altitude/scale, top-down rotation,
motion blur, haze/fog, sun glare, sensor noise, lighting). Valid/test are copied unchanged
(never evaluate on augmented images).
Usage: python vision/augment_db.py
"""
import glob, os, shutil

import albumentations as A
import cv2
import yaml

ROOT = os.path.join(os.path.dirname(__file__), "..", "DB")
SRC, DST = os.path.join(ROOT, "processed"), os.path.join(ROOT, "augmented")
COPIES = {"main": 1, "people": 3}           # people set is small -> more copies

PIPE = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.2),                  # top-down drone view has no fixed "up"
    A.RandomRotate90(p=0.3),
    A.Affine(scale=(0.5, 1.1), translate_percent=(-0.1, 0.1), rotate=(-15, 15), p=0.7),  # altitude change
    A.OneOf([A.MotionBlur(blur_limit=7), A.GaussianBlur(blur_limit=(3, 5))], p=0.3),    # drone motion
    A.RandomFog(fog_coef_range=(0.1, 0.3), p=0.1),                                      # sea haze
    A.RandomSunFlare(src_radius=80, p=0.05),                                            # glare on water
    A.RandomBrightnessContrast(0.3, 0.3, p=0.6),
    A.HueSaturationValue(10, 20, 15, p=0.4),
    A.GaussNoise(std_range=(0.02, 0.06), p=0.2),                                        # sensor noise
    A.ImageCompression(quality_range=(50, 95), p=0.3),                                  # video link
], bbox_params=A.BboxParams(format="yolo", label_fields=["cls"], min_visibility=0.3, clip=True))


def augment_one(img, boxes, classes, seed):
    """Return (image, yolo_boxes, classes) for one random augmentation (deterministic for a seed)."""
    PIPE.set_random_seed(seed)
    r = PIPE(image=img, bboxes=boxes, cls=classes)
    keep = [(b, c) for b, c in zip(r["bboxes"], r["cls"]) if b[2] > 1e-3 and b[3] > 1e-3]
    return r["image"], [list(map(float, b)) for b, _ in keep], [int(c) for _, c in keep]


def read_labels(path):
    rows = [l.split() for l in open(path).read().splitlines() if l.strip()]
    rows = [r for r in rows if float(r[3]) > 1e-3 and float(r[4]) > 1e-3]   # drop degenerate boxes
    return [list(map(float, r[1:5])) for r in rows], [int(r[0]) for r in rows]


def write(img, boxes, classes, out_dir, stem):
    cv2.imwrite(os.path.join(out_dir, "images", stem + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    open(os.path.join(out_dir, "labels", stem + ".txt"), "w").write(
        "".join(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for (x, y, w, h), c in zip(boxes, classes)))


def build(name, copies):
    src, dst = os.path.join(SRC, name), os.path.join(DST, name)
    shutil.rmtree(dst, ignore_errors=True)
    for split in ("valid", "test"):
        shutil.copytree(os.path.join(src, split), os.path.join(dst, split))
    out = os.path.join(dst, "train")
    for sub in ("images", "labels"):
        os.makedirs(os.path.join(out, sub))
    n_orig = n_aug = 0
    for i, img_path in enumerate(sorted(glob.glob(os.path.join(src, "train", "images", "*.jpg")))):
        stem = os.path.splitext(os.path.basename(img_path))[0]
        img = cv2.imread(img_path)
        boxes, classes = read_labels(os.path.join(src, "train", "labels", stem + ".txt"))
        write(img, boxes, classes, out, stem)
        n_orig += 1
        for k in range(copies):
            a_img, a_boxes, a_cls = augment_one(img, boxes, classes, seed=i * 10 + k)
            if a_boxes:                       # skip copies where every object was cropped out
                write(a_img, a_boxes, a_cls, out, f"{stem}_aug{k}")
                n_aug += 1
    cfg = yaml.safe_load(open(os.path.join(src, "data.yaml")))
    cfg["path"] = os.path.abspath(dst)
    yaml.safe_dump(cfg, open(os.path.join(dst, "data.yaml"), "w"), sort_keys=False)
    print(f"{name}: train {n_orig} originals + {n_aug} augmented = {n_orig + n_aug}")


if __name__ == "__main__":
    for name, copies in COPIES.items():
        build(name, copies)
