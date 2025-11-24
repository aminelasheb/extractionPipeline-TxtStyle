from pathlib import Path
import cv2
import json

# Paths
files_dir = Path(r"C:\Users\lasheb\PycharmProjects\extractionPipeline-TS\files")  # Original images
detnum_folder = Path("output/detImages/predict")  # JSON folder
crop_folder = detnum_folder / "crops"
crop_folder.mkdir(exist_ok=True, parents=True)

# Get all JSON files
json_files = list(detnum_folder.glob("*.json"))

for json_file in json_files:
    # Always map JSON -> .png from original files
    image_name_png = json_file.stem + ".png"
    image_path = files_dir / image_name_png

    if not image_path.exists():
        print(f"[ERR] Image not found for {json_file.name}")
        continue

    # Load original image
    img = cv2.imread(str(image_path))
    h, w = img.shape[:2]

    # Extract page number
    stem = json_file.stem
    page_num = stem.split("_")[-1]

    # Read JSON
    with open(json_file, "r", encoding="utf-8") as jf:
        data = json.load(jf)
        for shape in data["shapes"]:
            (x_min, y_min), (x_max, y_max) = shape["points"]

            # Clamp to image bounds
            x_min = max(int(x_min), 0)
            y_min = max(int(y_min), 0)
            x_max = min(int(x_max), w - 1)
            y_max = min(int(y_max), h - 1)

            roi = img[y_min:y_max, x_min:x_max]

            # Use JSON shape id
            shape_id = shape["id"]

            # Naming: p{page_num}c{id}.png
            crop_name = f"p{page_num}c{shape_id}.png"
            cv2.imwrite(str(crop_folder / crop_name), roi)
            print(f"[OK] Saved crop: {crop_name}")
