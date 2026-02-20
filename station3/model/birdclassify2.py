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
# Use tflite_runtime as in your Raspberry Pi setup
from tflite_runtime.interpreter import Interpreter

import msgBird as ms

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMG_DIR = "/home/pi/station3/ramdisk"
MODEL_NAME = "model2"
MODEL_PATH = f"{BASE_DIR}/{MODEL_NAME}/birdiary_v5_mobilenetv3.tflite"
LABELS_PATH = f"{BASE_DIR}/{MODEL_NAME}/labels.txt"

def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]

def softmax(x):
    """Compute softmax values for each set of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)

def is_recognized(label: str) -> bool:
    label = label.strip().lower()
    return "none" not in label

def preprocess_image(image_path, target_width, target_height):
    image = Image.open(image_path).convert("RGB")
    
    # 1. Scaling (Maintain aspect ratio)
    src_w, src_h = image.size
    scale = max(target_width / src_w, target_height / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 2. Center crop
    left = (new_w - target_width) // 2
    top = (new_h - target_height) // 2
    image = image.crop((left, top, right := left + target_width, bottom := top + target_height))

    # 3. Normalization (H, W, C)
    input_data = np.array(image, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    input_data = (input_data - mean) / std

    # 4. Transpose to NCHW [C, H, W]
    input_data = input_data.transpose((2, 0, 1))

    # 5. Add Batch Dimension [1, 3, 224, 224]
    input_data = np.expand_dims(input_data, axis=0)
    return input_data.astype(np.float32)

def main():
    if len(sys.argv) < 2:
        ms.log("Usage: python birdclassify.py <filename_prefix>")
        sys.exit(1)

    prefix = sys.argv[1]
    if "/" in prefix:
        ms.log(f"must not contain '/': {prefix}")
        sys.exit(1)

    image_files = sorted(glob.glob(os.path.join(IMG_DIR, f"{prefix}.*.jpg")))
    
    if not image_files:
        ms.log(f"No matching JPG files found for {prefix}.")
        sys.exit(1)

    ms.log(f"AI classify {len(image_files)} images")
    labels = load_labels(LABELS_PATH)

    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # NCHW indexing: 2 is Height, 3 is Width
    height = input_details[0]["shape"][2]
    width = input_details[0]["shape"][3]

    results = []

    # --- classify all images ---
    for image_path in image_files:
        input_data = preprocess_image(image_path, width, height)
        interpreter.set_tensor(input_details[0]["index"], input_data)
        interpreter.invoke()

        # Get raw logits and convert to probabilities
        output_data = interpreter.get_tensor(output_details[0]["index"])[0]
        probabilities = softmax(output_data)

        idx = int(np.argmax(probabilities))
        confidence = float(probabilities[idx]) * 100.0
        label = labels[idx] if idx < len(labels) else "unknown"

        results.append({
            "path": image_path,
            "label": label,
            "confidence": confidence,
        })

    # --- decision phase (filter out "none") ---
    recognized = [r for r in results if is_recognized(r["label"]) and 'background' not in r["label"].lower()]

    keep = []
    if recognized:
        keep = sorted(
            recognized,
            key=lambda r: r["confidence"],
            reverse=True
        )[:2]

    # --- write CSV ---
    csv_path = os.path.join(IMG_DIR, f"{prefix}.csv")
    with open(csv_path, "a", encoding="utf-8") as f:
        if keep:
            for r in keep:
                fname = os.path.basename(r["path"])
                nameparts = fname.split(".")
                # Assumes filename format: prefix.index.jpg
                idx_part = nameparts[-2] # Gets 'X' from 'prefix.X.jpg'
                f.write(f"{MODEL_NAME}, {idx_part}, {r['confidence']:.2f}, {r['label']}\n")
        else:
            f.write(f"{MODEL_NAME}, None\n")

if __name__ == "__main__":
    main()