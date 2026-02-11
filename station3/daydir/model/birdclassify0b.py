"""
classifies all images of name format 'yyyy-mm-dd_hhMMss.msecs.X.jpg (X = 0–9)',
e.g. '2026-02-02_083949.283901.0.jpg'

common <filename_prefix> is yyyy-mm-dd_hhMMss.msecs
Usage: python birdclassify.py <filename_prefix>

export TF_ENABLE_ONEDNN_OPTS=0 (in .bashrc, control by 'env | grep TF_')
"""

import sys
import os
import glob
import numpy as np
from PIL import Image
import tensorflow as tf

# ---- CONFIG ----
MODEL_PATH = "./model/classify.tflite"
LABELS_PATH = "./model/bird_labels_de_latin.txt"
CONFIDENCE_THRESHOLD = 30.0
# ----------------


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def preprocess_image(image_path, width, height, floating_model):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((width, height))
    input_data = np.expand_dims(np.array(image), axis=0)

    if floating_model:
        input_data = (np.float32(input_data) - 127.5) / 127.5

    return input_data


def main():
    if len(sys.argv) < 2:
        print("Usage: python birdclassify.py <filename_prefix>")
        sys.exit(1)

    prefix = sys.argv[1]
    image_files = sorted(glob.glob(f"{prefix}.*.jpg"))

    if not image_files:
        print("No matching JPG files found.")
        sys.exit(1)

    labels = load_labels(LABELS_PATH)

    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    height = input_details[0]["shape"][1]
    width = input_details[0]["shape"][2]
    floating_model = input_details[0]["dtype"] == np.float32

    confident_results = []
    rejected_images = []

    for image_path in image_files:
        input_data = preprocess_image(image_path, width, height, floating_model)
        interpreter.set_tensor(input_details[0]["index"], input_data)
        interpreter.invoke()

        output_data = interpreter.get_tensor(output_details[0]["index"])[0]

        if output_data.dtype != np.float32:
            output_data = output_data / 255.0

        predicted_index = int(np.argmax(output_data))
        confidence = float(output_data[predicted_index]) * 100.0

        if confidence >= CONFIDENCE_THRESHOLD:
            predicted_class = (
                labels[predicted_index]
                if predicted_index < len(labels)
                else f"Class {predicted_index}"
            )

            filename = os.path.basename(image_path)
            parts = filename.split(".")
            shortname = f"{parts[2]}.jpg" if len(parts) >= 3 else filename

            confident_results.append(
                (shortname, predicted_class, confidence)
            )
        else:
            rejected_images.append(image_path)

    # ---- WRITE CSV ----
    csv_path = f"{prefix}.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        if confident_results:
            for sname, species, conf in confident_results:
                f.write(f"{sname},{species},{conf:.2f}\n")
        else:
            f.write(f"No results above confidence {CONFIDENCE_THRESHOLD}%\n")

        rejectcnt = len(rejected_images)
        if rejectcnt > 0:
            f.write(f"Removed {rejectcnt} low-confidence images.\n")
            for img in rejected_images:
                os.remove(img)


if __name__ == "__main__":
    main()
