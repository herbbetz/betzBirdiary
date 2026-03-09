#!/usr/bin/env python3
"""
birdclassify1C.py

C-based version of birdclassify1.py using libbird_tflite.so.

Features
--------
• Uses TensorFlow Lite C API via ctypes
• No Python tflite_runtime dependency
• Direct write into TFLite tensor memory
• Supports float32 input models

Image naming format:

    yyyy-mm-dd_hhMMss.msecs.X.jpg

Example:

    2026-02-02_083949.283901.0.jpg

Common prefix:

    yyyy-mm-dd_hhMMss.msecs

Usage:

    python birdclassify1C.py <filename_prefix>

Keeps the two most confident predictions
with confidence ≥ 50%.
"""

import sys
import os
import glob
import ctypes
import numpy as np
from PIL import Image

import msgBird as ms


# --------------------------------------------------
# paths
# --------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

IMG_DIR = "/home/pi/station3/ramdisk"

MODEL_NAME = "model1"

MODEL_PATH = f"{BASE_DIR}/{MODEL_NAME}/bird_classifier.tflite"

LABELS_PATH = f"{BASE_DIR}/{MODEL_NAME}/labels.txt"

LIB_PATH = f"{BASE_DIR}/libbird_tflite.so"


# --------------------------------------------------
# load labels
# --------------------------------------------------

def load_labels(path):

    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]


# --------------------------------------------------
# filter recognized birds
# --------------------------------------------------

def is_recognized(label: str) -> bool:

    label = label.strip().lower()

    return "none" not in label


# --------------------------------------------------
# image preprocessing
# --------------------------------------------------

def preprocess_image(image_path, width, height):

    image = Image.open(image_path).convert("RGB")

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

    # convert to float32

    arr = np.array(image, dtype=np.float32)

    # normalization required by model

    arr = (arr - 127.5) / 127.5

    return arr


# --------------------------------------------------
# main
# --------------------------------------------------

def main():

    if len(sys.argv) < 2:
        ms.log("Usage: python birdclassify1C.py <filename_prefix>")
        sys.exit(1)

    prefix = sys.argv[1]

    if "/" in prefix:
        ms.log(f"must not contain '/': {prefix}")
        sys.exit(1)


    # --------------------------------------------------
    # find images
    # --------------------------------------------------

    image_files = sorted(
        glob.glob(os.path.join(IMG_DIR, f"{prefix}.*.jpg"))
    )

    ms.log(f"AI classify {len(image_files)} images")

    if not image_files:
        ms.log("No matching JPG files found.")
        sys.exit(1)


    # --------------------------------------------------
    # load labels
    # --------------------------------------------------

    labels = load_labels(LABELS_PATH)


    # --------------------------------------------------
    # load C library
    # --------------------------------------------------

    lib = ctypes.CDLL(LIB_PATH)


    # --------------------------------------------------
    # define ctypes signatures
    # --------------------------------------------------

    lib.bird_model_load.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int
    ]
    lib.bird_model_load.restype = ctypes.c_void_p


    lib.bird_model_input_size.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int)
    ]


    lib.bird_model_output_size.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_output_size.restype = ctypes.c_int


    lib.bird_model_input_buffer.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_input_buffer.restype = ctypes.c_void_p


    lib.bird_model_infer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p
    ]
    lib.bird_model_infer.restype = ctypes.c_int


    lib.bird_model_free.argtypes = [
        ctypes.c_void_p
    ]


    # --------------------------------------------------
    # load model
    # --------------------------------------------------

    model = lib.bird_model_load(
        MODEL_PATH.encode("utf-8"),
        4
    )

    if not model:
        ms.log("model load failed")
        sys.exit(1)


    # --------------------------------------------------
    # query input tensor shape
    # --------------------------------------------------

    w = ctypes.c_int()
    h = ctypes.c_int()
    c = ctypes.c_int()

    lib.bird_model_input_size(
        model,
        ctypes.byref(w),
        ctypes.byref(h),
        ctypes.byref(c)
    )

    width = w.value
    height = h.value
    channels = c.value


    # --------------------------------------------------
    # map tensor memory (float32)
    # --------------------------------------------------

    ptr = lib.bird_model_input_buffer(model)

    tensor_size = width * height * channels

    input_array = np.ctypeslib.as_array(
        (ctypes.c_float * tensor_size).from_address(ptr)
    )

    input_array = input_array.reshape(
        (height, width, channels)
    )


    # --------------------------------------------------
    # output buffer
    # --------------------------------------------------

    num_classes = lib.bird_model_output_size(model)

    output = np.zeros(num_classes, dtype=np.float32)

    results = []


    # --------------------------------------------------
    # classify images
    # --------------------------------------------------

    for image_path in image_files:

        img = preprocess_image(
            image_path,
            width,
            height
        )

        # write directly into tensor memory

        np.copyto(input_array, img)

        # run inference

        lib.bird_model_infer(
            model,
            output.ctypes.data
        )

        idx = int(np.argmax(output))

        confidence = float(output[idx]) * 100.0

        label = labels[idx] if idx < len(labels) else "unknown"

        results.append({
            "path": image_path,
            "label": label,
            "confidence": confidence,
        })


    # --------------------------------------------------
    # decision phase
    # --------------------------------------------------

    recognized = [

        r for r in results

        if is_recognized(r["label"])
        and r["confidence"] >= 50

    ]


    keep = []

    if recognized:

        keep = sorted(
            recognized,
            key=lambda r: r["confidence"],
            reverse=True
        )[:2]


    # --------------------------------------------------
    # write CSV
    # --------------------------------------------------

    csv_path = os.path.join(
        IMG_DIR,
        f"{prefix}.csv"
    )

    with open(csv_path, "a", encoding="utf-8") as f:

        if keep:

            for r in keep:

                fname = os.path.basename(r["path"])

                nameparts = fname.split(".")

                f.write(
                    f"{MODEL_NAME}, "
                    f"{nameparts[2]}, "
                    f"{r['confidence']:.2f}, "
                    f"{r['label']}\n"
                )

        else:

            f.write(f"{MODEL_NAME}, None\n")


    # --------------------------------------------------
    # cleanup
    # --------------------------------------------------

    lib.bird_model_free(model)


if __name__ == "__main__":
    main()