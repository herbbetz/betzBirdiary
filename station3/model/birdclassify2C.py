#!/usr/bin/env python3
"""
birdclassify2C.py

C-based version of birdclassify2.py using libbird_tflite.so.

Features
--------
• Uses TensorFlow Lite C API via ctypes
• Supports NCHW float32 input models
• Direct write into TFLite tensor memory
• Scaling + center crop + PyTorch normalization
• Uses argmax instead of softmax for speed
"""

import sys
import os
import glob
import ctypes
import datetime
import json
import numpy as np
from PIL import Image

import msgBird as ms


# --------------------------------------------------
# paths
# --------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMG_DIR = "/home/pi/station3/ramdisk"

MODEL_NAME = "model2"
MODEL_PATH = f"{BASE_DIR}/{MODEL_NAME}/birdiary_v5_mobilenetv3.tflite"
LABELS_PATH = f"{BASE_DIR}/{MODEL_NAME}/labels.txt"

LIB_PATH = f"{BASE_DIR}/libbird_tflite.so"


# --------------------------------------------------
# helpers
# --------------------------------------------------

def load_labels(path):

    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]


def softmax(x: np.ndarray) -> np.ndarray:

    # Stable softmax for converting logits to probabilities.
    x = x - np.max(x)
    e = np.exp(x)
    return e / np.sum(e)


def is_recognized(label: str) -> bool:

    label = label.strip().lower()

    return "none" not in label and "background" not in label


def preprocess_image(image_path, target_width, target_height):
    """
    PyTorch-style preprocessing
    """

    image = Image.open(image_path).convert("RGB")

    # ---- scale with preserved aspect ratio ----

    src_w, src_h = image.size

    scale = max(
        target_width / src_w,
        target_height / src_h
    )

    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    image = image.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS
    )

    # ---- center crop ----

    left = (new_w - target_width) // 2
    top = (new_h - target_height) // 2

    image = image.crop((
        left,
        top,
        left + target_width,
        top + target_height
    ))

    # ---- convert to float ----

    arr = np.array(image, dtype=np.float32) / 255.0

    # ---- PyTorch normalization ----

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    arr = (arr - mean) / std

    # ---- convert to NCHW ----

    arr = arr.transpose((2, 0, 1))

    return arr.astype(np.float32)


# --------------------------------------------------
# main
# --------------------------------------------------

def main():

    if len(sys.argv) < 2:

        ms.log("Usage: python birdclassify2C.py <filename_prefix>")
        sys.exit(1)


    prefix = sys.argv[1]

    if "/" in prefix:

        ms.log(f"must not contain '/': {prefix}")
        sys.exit(1)


    # --------------------------------------------------
    # find images
    # --------------------------------------------------

    image_files = sorted(
        glob.glob(
            os.path.join(IMG_DIR, f"{prefix}.*.jpg")
        )
    )

    ms.log(f"AI classify {len(image_files)} images")

    if not image_files:

        ms.log(f"No matching JPG files found for {prefix}.")
        sys.exit(1)


    # --------------------------------------------------
    # labels
    # --------------------------------------------------

    labels = load_labels(LABELS_PATH)


    # --------------------------------------------------
    # load C library
    # --------------------------------------------------

    lib = ctypes.CDLL(LIB_PATH)


    # --------------------------------------------------
    # C function signatures
    # --------------------------------------------------

    lib.bird_model_load.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int
    ]
    lib.bird_model_load.restype = ctypes.c_void_p


    lib.bird_model_input_info.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int)
    ]


    lib.bird_model_input_buffer.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_input_buffer.restype = ctypes.c_void_p


    lib.bird_model_output_size.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_output_size.restype = ctypes.c_int


    lib.bird_model_infer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p
    ]


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
    # query tensor info
    # --------------------------------------------------

    w = ctypes.c_int()
    h = ctypes.c_int()
    c = ctypes.c_int()
    layout = ctypes.c_int()
    dtype  = ctypes.c_int()

    lib.bird_model_input_info(
        model,
        ctypes.byref(w),
        ctypes.byref(h),
        ctypes.byref(c),
        ctypes.byref(layout),
        ctypes.byref(dtype)
    )

    width  = w.value
    height = h.value
    channels = c.value


    # ---- safety checks ----

    if layout.value != 1:

        ms.log("ERROR: model2 requires NCHW layout")
        sys.exit(1)

    if dtype.value != 1:

        ms.log("ERROR: model2 requires float32 input")
        sys.exit(1)


    # --------------------------------------------------
    # tensor memory pointer
    # --------------------------------------------------

    ptr = lib.bird_model_input_buffer(model)

    tensor_size = width * height * channels

    input_array = np.ctypeslib.as_array(
        (ctypes.c_float * tensor_size).from_address(ptr)
    ).reshape((channels, height, width))


    # --------------------------------------------------
    # output buffer
    # --------------------------------------------------

    num_classes = lib.bird_model_output_size(model)

    output = np.zeros(
        num_classes,
        dtype=np.float32
    )


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

        np.copyto(
            input_array,
            img
        )

        # inference

        lib.bird_model_infer(
            model,
            output.ctypes.data
        )

        probs = softmax(output)

        idx = int(np.argmax(probs))
        confidence = float(probs[idx]) * 100.0

        label = labels[idx] if idx < len(labels) else "unknown"


        results.append({
            "path": image_path,
            "label_idx": idx,
            "confidence": confidence
        })


    # --------------------------------------------------
    # decision phase
    # --------------------------------------------------
    recognized = [
        r for r in results
        if is_recognized(labels[r["label_idx"]])  # Look up string for the check
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
                idx_part = nameparts[-2]

                f.write(
                    f"{MODEL_NAME}, {idx_part}, "
                    f"{r['confidence']:.2f}, "
                    f"{labels[r['label_idx']]}\n"
                )

        else:

            f.write(f"{MODEL_NAME}, None\n")


    # --------------------------------------------------
    # write ramdisk/model2.json for bird statistics
    # --------------------------------------------------

    top_label_idx = keep[0]["label_idx"] if len(keep) > 0 and keep[0]["confidence"] > 60 else None

    if top_label_idx is not None:
        date_str = datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        new_entry = [date_str, top_label_idx]

        # Keep file as one valid JSON array: [[date, idx], ...]
        statfname = os.path.join(IMG_DIR, f"{MODEL_NAME}.json")
        stats = []
        if os.path.exists(statfname):
            try:
                with open(statfname, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except json.JSONDecodeError:
                stats = [] # Handle corrupted/empty files
 
        stats.append(new_entry)

        # Keep only the last 1000 entries to prevent ramdisk bloat
        if len(stats) > 1000:
            stats = stats[-1000:]

        with open(statfname, "w", encoding="utf-8") as f:
            json.dump(stats, f)    

        # count absolute counts to a dictionary counts = {label_idx0: count0, ...}
        counts = {}
        for entry in stats:
            idx = entry[1]
            if idx in counts: counts[idx] += 1 
            else: counts[idx] = 1  # same as: 'counts[idx] = counts.get(idx, 0) + 1'

        # counts.items() gives [(idx, count), (idx, count), ...]
        sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)

        # html output (iframe):
        html = "<!doctype html>\n<html>\n<head><meta http-equiv='refresh' content='60'></head>\n<body>\n" # refresh every 60 secs to avoid iframe browser cacheing
        html += f"<h2>Statistics of {MODEL_NAME}</h2>\n<table style='display: block; margin: 0 auto; border-collapse: collapse; width: 60%;'>\n"
        for idx, count in sorted_counts:
            bird_name = labels[idx][:15] # 15 leftmost chars
            relcnt = round(count/len(stats) * 100)
            html += f"<tr style='border-bottom: 1px solid #ddd;'><td style='padding: 4px;'>{bird_name}</td><td>{count}</td><td>{relcnt} %</td></tr>\n"
        html += "</table></body></html>"

        html_path = os.path.join(IMG_DIR,f"{MODEL_NAME}.html")
        # overwrite:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)       
    # --------------------------------------------------
    # cleanup
    # --------------------------------------------------

    lib.bird_model_free(model)



if __name__ == "__main__":
    main()