"""
classifies all images of name format 'yyyy-mm-dd_hhMMss.msecs.X.jpg (X = 0–9)',
e.g. '2026-02-02_083949.283901.0.jpg'

common <filename_prefix> is yyyy-mm-dd_hhMMss.msecs
Usage: python birdclassify.py <filename_prefix>
beware that 'run_classify.sh' does not include a path within <filename_prefix>

keeps the top 2 most confident classifications that are not "none", or if all are "none" keeps prefix.0.jpg and prefix.2.jpg if they exist, and deletes the rest
"""
import sys
import os
import glob # search for filename wildcards like '<filename_prefix>.*.jpg'
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

import msgBird as ms # because PYTHONPATH = home/pi/station3 in startup.sh (called by bird-startup.service)

BASE_DIR = os.path.abspath(os.path.dirname(__file__)) # BASE_DIR of current script = /home/pi/station3/model
IMG_DIR = "/home/pi/station3/ramdisk"
MODEL_NAME = "model0"
MODEL_PATH = f"{BASE_DIR}/{MODEL_NAME}/classify.tflite"
LABELS_PATH = f"{BASE_DIR}/{MODEL_NAME}/bird_labels_de_latin.txt"


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]

def is_recognized(label: str) -> bool: # 'none' is not in label, could be enhanced by 'background' or 'unknown' or similar
    label = label.strip().lower()
    return "none" not in label

def preprocess_image(image_path, width, height, floating_model):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((width, height))
    input_data = np.expand_dims(np.array(image), axis=0)

    # not really needed as model0/classify.tflite was identified as 'raw_uint8', see preprocess_image() with 3 args in testmodel0.py:
    if floating_model:
        input_data = (np.float32(input_data) - 127.5) / 127.5

    return input_data


def main():
    if len(sys.argv) < 2:
        ms.log("Usage: python birdclassify.py <filename_prefix>")
        sys.exit(1)

    prefix = sys.argv[1] # should contain no path
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
    floating_model = input_details[0]["dtype"] == np.float32

    results = []

    # --- classify all images ---
    for image_path in image_files:
        input_data = preprocess_image(image_path, width, height, floating_model)
        interpreter.set_tensor(input_details[0]["index"], input_data)
        interpreter.invoke()

        output_data = interpreter.get_tensor(output_details[0]["index"])[0]

        if output_data.dtype != np.float32:
            output_data = output_data / 255.0

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
        # keep top 2 by confidence
        keep = sorted(
            recognized,
            key=lambda r: r["confidence"],
            reverse=True
        )[:2]
    '''
    # do this later in extra script after all models analyzed all the images:
    else:
        # fallback for 'none' with all images: keep prefix.0.jpg and prefix.2.jpg if present
        keep = [r for r in results
                if r["path"].endswith(".0.jpg") or r["path"].endswith(".2.jpg")
        ]

    # if not keep:
    #    print("WARNING: keep is empty — skipping deletion for safety")
    #    return

    # keep_assert = "\n".join(r["path"] for r in keep)
    # for debugging, should be empty if keep is empty

    keep_paths = {r["path"] for r in keep}


    # --- delete all others ---
    for r in results:
        if r["path"] not in keep_paths:
            os.remove(r["path"])
    '''

    # --- write CSV ---
    csv_path = os.path.join(IMG_DIR, f"{prefix}.csv")
    with open(csv_path, "a", encoding="utf-8") as f: # append
        # f.write("DEBUG keep paths:\n")
        # f.write(keep_assert + "\n\n")
        if keep:
            for r in keep:
                fname = os.path.basename(r["path"])
                nameparts = fname.split(".")
                f.write(f"{MODEL_NAME}, {nameparts[2]}, {r['label']}, {r['confidence']:.2f}%\n") # Img#{nameparts[2]}
                # f.write(f"{r['label']}, {r['confidence']:.2f}%\n")
        else:
            f.write(f"{MODEL_NAME}, None\n")

if __name__ == "__main__":
    main()
