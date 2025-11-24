from ultralytics import YOLO
from pathlib import Path
import cv2
import json
import shutil

# Delete "files" directory if it exists (optional)
files_dir = Path(r"C:\Users\lasheb\PycharmProjects\extractionPipeline-TS\files")

# Classes per model
classes_dict = {
    "detImages": ["image"],
}

# Directories
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

# Get all PNG files from "files"
images = list(files_dir.glob("*.png"))

# Model paths
model_paths = {
    "detImages": r"C:\Users\lasheb\PycharmProjects\MALIN-extraction-with-images\models\detImages.pt",
}

run_folders = []

# Step 1: Detection
for model_name, model_path in model_paths.items():
    print(f"\n=== Loading model {model_name} ===")
    model = YOLO(str(model_path))

    # Output directory for this model
    model_output_dir = output_dir / model_name
    model_output_dir.mkdir(exist_ok=True, parents=True)

    for image_path in images:
        print(f"Processing {image_path.name} with {model_name}...")
        _ = model.predict(
            source=str(image_path),
            save=True,
            save_txt=True,
            project=str(model_output_dir),
            name="predict",
            exist_ok=True
        )

    run_folders.append((model_name, model_output_dir))
    print(f"==> {model_name} finished\n")

# Step 2: Transform TXT -> JSON (LabelMe format)
for model_name, run_folder in run_folders:
    labels_dir = run_folder / "predict" / "labels"
    images_dir = run_folder / "predict"

    if not labels_dir.exists():
        print(f"No labels found for {model_name}")
        continue

    print(f"Transforming labels to JSON for {model_name}")

    for txt_file in labels_dir.glob("*.txt"):
        image_name_jpg = txt_file.stem + ".jpg"
        image_name_png = txt_file.stem + ".png"

        image_path = images_dir / image_name_jpg
        if not image_path.exists():
            image_path = images_dir / image_name_png
        if not image_path.exists():
            continue

        img = cv2.imread(str(image_path))
        if img is None:
            print(f"[WARN] Could not read image: {image_path}")
            continue

        h, w = img.shape[:2]

        shapes = []
        with open(txt_file, "r") as f:
            for idx, line in enumerate(f.readlines()):  # idx = id for each shape
                cls, x_c, y_c, bw, bh = map(float, line.strip().split())
                cls = int(cls)

                # For detNum, keep only class 2
                if model_name == "detNum" and cls != 2:
                    continue

                x_center = x_c * w
                y_center = y_c * h
                width = bw * w
                height = bh * h

                x_min = x_center - width / 2
                y_min = y_center - height / 2
                x_max = x_center + width / 2
                y_max = y_center + height / 2

                shape = {
                    "id": idx,  # starts at 0 and increments for each line
                    "label": classes_dict.get(model_name, [str(cls)])[cls],
                    "points": [
                        [x_min, y_min],
                        [x_max, y_max]
                    ]
                }
                shapes.append(shape)

        json_dict = {
            "shapes": shapes,
            "imageHeight": h,
            "imageWidth": w
        }

        json_path = images_dir / f"{txt_file.stem}.json"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(json_dict, jf, ensure_ascii=False, indent=2)

        print(f"  [OK] Saved JSON: {json_path}")
