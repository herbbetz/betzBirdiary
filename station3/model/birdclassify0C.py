#!/usr/bin/env python3
"""
birdclassify0C.py

C-based version of birdclassify0.py.

Uses the custom C inference library:

    libbird_tflite.so

instead of the Python TensorFlow Lite runtime.

Advantages
----------

• avoids Python tflite_runtime dependency
• works with modern Python versions
• faster inference on Raspberry Pi
• writes image directly into TFLite tensor memory
• uses universal tensor info API

Input images follow the naming format

    yyyy-mm-dd_hhMMss.msecs.X.jpg

example

    2026-02-02_083949.283901.0.jpg

The common prefix is

    yyyy-mm-dd_hhMMss.msecs

Usage

    python birdclassify0C.py <filename_prefix>

Example

    python birdclassify0C.py 2026-02-02_083949.283901

The script keeps the two most confident predictions
that are not labeled "none".
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

MODEL_NAME = "model0"

MODEL_PATH = f"{BASE_DIR}/{MODEL_NAME}/classify.tflite"

LABELS_PATH = f"{BASE_DIR}/{MODEL_NAME}/bird_labels_de_latin.txt"

LIB_PATH = f"{BASE_DIR}/libbird_tflite.so"


# --------------------------------------------------
# load labels
# --------------------------------------------------

def load_labels(path):

    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]


# --------------------------------------------------
# filter out "none"
# --------------------------------------------------

def is_recognized(label: str):

    label = label.strip().lower()

    return "none" not in label


# --------------------------------------------------
# main program
# --------------------------------------------------

def main():

    if len(sys.argv) < 2:

        ms.log("Usage: python birdclassify0C.py <filename_prefix>")
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
    # load C inference library
    # --------------------------------------------------

    lib = ctypes.CDLL(LIB_PATH)


    # --------------------------------------------------
    # function signatures (ctypes safety)
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
    # query input tensor information
    # --------------------------------------------------

    w = ctypes.c_int()
    h = ctypes.c_int()
    c = ctypes.c_int()
    layout = ctypes.c_int()
    dtype = ctypes.c_int()

    lib.bird_model_input_info(
        model,
        ctypes.byref(w),
        ctypes.byref(h),
        ctypes.byref(c),
        ctypes.byref(layout),
        ctypes.byref(dtype)
    )

    width = w.value
    height = h.value
    channels = c.value


    # --------------------------------------------------
    # verify tensor format
    # --------------------------------------------------

    if layout.value != 0:

        ms.log("ERROR: model0 expects NHWC layout")
        sys.exit(1)

    if dtype.value != 0:

        ms.log("ERROR: model0 expects uint8 input")
        sys.exit(1)


    # --------------------------------------------------
    # obtain pointer to tensor memory
    # --------------------------------------------------

    ptr = lib.bird_model_input_buffer(model)

    tensor_size = width * height * channels

    input_array = np.ctypeslib.as_array(
        (ctypes.c_uint8 * tensor_size).from_address(ptr)
    )

    input_array = input_array.reshape(
        (height, width, channels)
    )


    # --------------------------------------------------
    # output vector size
    # --------------------------------------------------

    num_classes = lib.bird_model_output_size(model)

    output = np.zeros(num_classes, dtype=np.float32)

    results = []


    # --------------------------------------------------
    # classify each image
    # --------------------------------------------------

    for image_path in image_files:

        # load image

        img = Image.open(image_path).convert("RGB")

        # resize to model input size

        img = img.resize((width, height), Image.BILINEAR)

        # convert to numpy uint8

        arr = np.array(img, dtype=np.uint8)

        # write directly into tensor memory

        np.copyto(input_array, arr)

        # run inference

        lib.bird_model_infer(
            model,
            output.ctypes.data
        )

        # compute prediction

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
    ]

    if recognized:

        keep = sorted(
            recognized,
            key=lambda r: r["confidence"],
            reverse=True
        )[:2]

    else:

        keep = []


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

                img_index = fname.rsplit(".", 2)[1]

                f.write(
                    f"{MODEL_NAME}, "
                    f"{img_index}, "
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