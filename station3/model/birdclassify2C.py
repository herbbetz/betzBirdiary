#!/usr/bin/env python3
"""
birdclassify2C.py

C-based version of birdclassify2.py using libbird_tflite.so.

Features
--------
• Uses TensorFlow Lite C API via ctypes
• Supports NCHW float32 input models
• Direct write into TFLite tensor memory
• Applies scaling, center crop, normalization, and softmax
"""

import sys
import os
import glob
import ctypes
import numpy as np
from PIL import Image

import msgBird as ms


# -------------------------------
# paths
# -------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMG_DIR = "/home/pi/station3/ramdisk"
MODEL_NAME = "model2"
MODEL_PATH = f"{BASE_DIR}/{MODEL_NAME}/birdiary_v5_mobilenetv3.tflite"
LABELS_PATH = f"{BASE_DIR}/{MODEL_NAME}/labels.txt"
LIB_PATH = f"{BASE_DIR}/libbird_tflite.so"


# -------------------------------
# helpers
# -------------------------------

def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]


def is_recognized(label: str) -> bool:
    label = label.strip().lower()
    return "none" not in label and "background" not in label


def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)


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
    right = left + target_width
    bottom = top + target_height
    image = image.crop((left, top, right, bottom))

    # 3. Normalize [0,1] -> mean/std
    arr = np.array(image, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std

    # 4. NCHW transpose
    arr = arr.transpose((2, 0, 1))

    # 5. Add batch dimension
    arr = np.expand_dims(arr, axis=0)
    return arr.astype(np.float32)


# -------------------------------
# main
# -------------------------------

def main():
    if len(sys.argv) < 2:
        ms.log("Usage: python birdclassify2C.py <filename_prefix>")
        sys.exit(1)

    prefix = sys.argv[1]
    if "/" in prefix:
        ms.log(f"must not contain '/': {prefix}")
        sys.exit(1)

    # --- find images ---
    image_files = sorted(glob.glob(os.path.join(IMG_DIR, f"{prefix}.*.jpg")))
    ms.log(f"AI classify {len(image_files)} images")
    if not image_files:
        ms.log(f"No matching JPG files found for {prefix}.")
        sys.exit(1)

    # --- labels ---
    labels = load_labels(LABELS_PATH)

    # --- load C library ---
    lib = ctypes.CDLL(LIB_PATH)

    # --- function signatures ---
    lib.bird_model_load.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.bird_model_load.restype = ctypes.c_void_p

    lib.bird_model_input_size.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int)
    ]

    lib.bird_model_output_size.argtypes = [ctypes.c_void_p]
    lib.bird_model_output_size.restype = ctypes.c_int

    lib.bird_model_input_buffer.argtypes = [ctypes.c_void_p]
    lib.bird_model_input_buffer.restype = ctypes.c_void_p

    lib.bird_model_infer.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.bird_model_infer.restype = ctypes.c_int

    lib.bird_model_free.argtypes = [ctypes.c_void_p]

    # --- load model ---
    model = lib.bird_model_load(MODEL_PATH.encode("utf-8"), 4)
    if not model:
        ms.log("model load failed")
        sys.exit(1)

    # --- input tensor ---
    w = ctypes.c_int()
    h = ctypes.c_int()
    c = ctypes.c_int()
    lib.bird_model_input_size(model, ctypes.byref(w), ctypes.byref(h), ctypes.byref(c))
    width, height, channels = w.value, h.value, c.value

    ptr = lib.bird_model_input_buffer(model)
    tensor_size = height * width * channels
    input_array = np.ctypeslib.as_array(
        (ctypes.c_float * tensor_size).from_address(ptr)
    ).reshape((1, channels, height, width))  # NCHW

    # --- output buffer ---
    num_classes = lib.bird_model_output_size(model)
    output = np.zeros(num_classes, dtype=np.float32)

    results = []

    # --- classify all images ---
    for image_path in image_files:
        img = preprocess_image(image_path, width, height)

        # NCHW memory write
        np.copyto(input_array, img)

        # inference
        lib.bird_model_infer(model, output.ctypes.data)

        # softmax
        probabilities = softmax(output)

        idx = int(np.argmax(probabilities))
        confidence = float(probabilities[idx]) * 100.0
        label = labels[idx] if idx < len(labels) else "unknown"

        results.append({
            "path": image_path,
            "label": label,
            "confidence": confidence,
        })

    # --- decision ---
    recognized = [r for r in results if is_recognized(r["label"]) and r["confidence"] >= 0]

    keep = sorted(recognized, key=lambda r: r["confidence"], reverse=True)[:2] if recognized else []

    # --- write CSV ---
    csv_path = os.path.join(IMG_DIR, f"{prefix}.csv")
    with open(csv_path, "a", encoding="utf-8") as f:
        if keep:
            for r in keep:
                fname = os.path.basename(r["path"])
                nameparts = fname.split(".")
                idx_part = nameparts[-2]
                f.write(f"{MODEL_NAME}, {idx_part}, {r['confidence']:.2f}, {r['label']}\n")
        else:
            f.write(f"{MODEL_NAME}, None\n")

    # --- cleanup ---
    lib.bird_model_free(model)


if __name__ == "__main__":
    main()