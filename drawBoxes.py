import os
import json
import cv2
from pathlib import Path

# Base directory = where this script is located
base_dir = Path(__file__).parent.resolve()

# Paths relative to the script directory
images_path = r"C:\Users\lasheb\PycharmProjects\extractionPipeline-TS\files"
json_path = base_dir / "output" / "detImages" / "predict"
output_path = r"C:\Users\lasheb\PycharmProjects\extractionPipeline-TS\files-out"

# Create output folder if not exists
os.makedirs(output_path, exist_ok=True)

# Iterate over all json files
for json_file in os.listdir(json_path):
    if not json_file.endswith(".json"):
        continue

    json_file_path = os.path.join(json_path, json_file)

    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Assume JSON filename corresponds to the image name
    image_name = os.path.splitext(json_file)[0] + ".png"  # or jpg/jpeg
    image_file = os.path.join(images_path, image_name)

    if not os.path.exists(image_file):
        print(f"[WARN] Image not found for {json_file}")
        continue

    img = cv2.imread(image_file)
    if img is None:
        print(f"[WARN] Could not load {image_file}")
        continue

    # Extract page number
    page_num = ''.join([c for c in image_name if c.isdigit()]) or "0"

    for shape in data.get("shapes", []):
        pts = shape["points"]
        x1, y1 = map(int, pts[0])
        x2, y2 = map(int, pts[1])
        shape_id = shape["id"]

        # --- Thicker rectangle in RED ---
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 6)  # épaisseur augmentée ici

        # Label text
        label_text = f"p{page_num}c{shape_id}"

        font = cv2.FONT_HERSHEY_SIMPLEX

        # DOUBLE SIZE (text + thickness)
        scale = 2.8  # previously 1.4
        thickness = 8  # previously 3

        (text_w, text_h), baseline = cv2.getTextSize(label_text, font, scale, thickness)
        box_cx = (x1 + x2) // 2
        box_cy = (y1 + y2) // 2

        text_x = box_cx - text_w // 2
        text_y = box_cy + text_h // 2

        # DOUBLE THE PADDING
        padding = 20  # previously 10

        tx1 = text_x - padding
        ty1 = text_y - text_h - padding
        tx2 = text_x + text_w + padding
        ty2 = text_y + padding

        overlay = img.copy()
        cv2.rectangle(overlay, (tx1, ty1), (tx2, ty2), (0, 0, 0), -1)
        alpha = 0.85  # nicer contrast
        img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

        cv2.putText(img, label_text, (text_x, text_y), font,
                    scale, (255, 255, 255), thickness, cv2.LINE_AA)

    out_file = os.path.join(output_path, image_name)
    cv2.imwrite(out_file, img)
    print(f"[OK] Saved {out_file}")
