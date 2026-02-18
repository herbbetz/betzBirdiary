"""
classifies all images of name format 'yyyy-mm-dd_hhMMss.msecs.X.jpg (X = 0–9)',
e.g. '2026-02-02_083949.283901.0.jpg'

common <filename_prefix> is yyyy-mm-dd_hhMMss.msecs
Usage: python birdclassify.py <filename_prefix>

keeps the top 2 most confident classifications that are not "none"
"""
import sys
import os
import glob
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

import msgBird as ms

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMG_DIR = "/home/pi/station3/ramdisk"
MODEL_NAME = "model1"
MODEL_PATH = f"{BASE_DIR}/{MODEL_NAME}/bird_classifier.tflite"
LABELS_PATH = f"{BASE_DIR}/{MODEL_NAME}/labels.txt"


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]


def is_recognized(label: str) -> bool:
    label = label.strip().lower()
    return "none" not in label


def preprocess_image(image_path, width, height):
    image = Image.open(image_path).convert("RGB")
    # image = image.resize((width, height)) only distorts image
    # --- keep aspect ratio ---
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    image = image.resize((new_w, new_h), Image.BILINEAR)

    # --- center crop ---
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    right = left + width
    bottom = top + height
    image = image.crop((left, top, right, bottom))

    input_data = np.array(image, dtype=np.float32)
    input_data = (input_data - 127.5) / 127.5

    return np.expand_dims(input_data, axis=0)


def main():
    if len(sys.argv) < 2:
        ms.log("Usage: python birdclassify.py <filename_prefix>")
        sys.exit(1)

    prefix = sys.argv[1]
    if "/" in prefix:
        ms.log(f"must not contain '/': {prefix}")
        sys.exit(1)

    image_files = sorted(glob.glob(os.path.join(IMG_DIR, f"{prefix}.*.jpg")))
    ms.log(f"AI classify {len(image_files)} images")

    if not image_files:
        ms.log("No matching JPG files found.")
        sys.exit(1)

    labels = load_labels(LABELS_PATH)

    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    height = input_details[0]["shape"][1]
    width = input_details[0]["shape"][2]

    results = []

    # --- classify all images ---
    for image_path in image_files:
        input_data = preprocess_image(image_path, width, height)
        interpreter.set_tensor(input_details[0]["index"], input_data)
        interpreter.invoke()

        output_data = interpreter.get_tensor(output_details[0]["index"])[0]

        idx = int(np.argmax(output_data))
        confidence = float(output_data[idx]) * 100.0
        label = labels[idx] if idx < len(labels) else "unknown"

        results.append({
            "path": image_path,
            "label": label,
            "confidence": confidence,
        })

    # --- decision phase ---
    recognized = [r for r in results if is_recognized(r["label"])]

    keep = []
    if recognized:
        keep = sorted(
            recognized,
            key=lambda r: r["confidence"],
            reverse=True
        )[:2]

    # --- write CSV ---
    csv_path = os.path.join(IMG_DIR, f"{prefix}.csv")
    with open(csv_path, "a", encoding="utf-8") as f: # append
        if keep:
            for r in keep:
                fname = os.path.basename(r["path"])
                nameparts = fname.split(".")
                f.write(f"{MODEL_NAME}, {nameparts[2]}, {r['confidence']:.2f}, {r['label']}\n")
        else:
            f.write(f"{MODEL_NAME}, None\n")


if __name__ == "__main__":
    main()
