#!/usr/bin/env python3
"""
Example usage (Raspberry Pi / Linux, after building libsndclass.so):

    gcc -O3 -fPIC -shared sndclass.c -o libsndclass.so -Wl,--no-as-needed -ltensorflow-lite -ltensorflowlite_flex -lm

    python3 sndclassify.py testsnd/great-tit.wav sndmodel/BirdNET_6K_GLOBAL_MODEL.tflite sndmodel/labels.txt

Loads waveform into the TFLite input tensor via C (snd_wav_fill_model_input), runs inference, prints top prediction.
Output scores are treated as logits for softmax display; if the model already emits probabilities, ranking is unchanged.
"""

import ctypes
import os
import sys

import numpy as np


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f]


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x)
    e = np.exp(x)
    return e / np.sum(e)


def libsndclass_path():
    """libsndclass.so next to this script (Raspberry Pi / Trixie)."""
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "libsndclass.so")


def main():
    if len(sys.argv) != 4:
        print("Usage:")
        print("  sndclassify.py <wav> <model.tflite> <labels.txt>")
        sys.exit(1)

    wav_path = sys.argv[1]
    model_path = sys.argv[2]
    labels_path = sys.argv[3]

    if not os.path.isfile(wav_path):
        print(f"WAV not found: {wav_path}")
        sys.exit(1)
    if not os.path.isfile(model_path):
        print(f"Model not found: {model_path}")
        sys.exit(1)

    labels = load_labels(labels_path)

    lib_path = libsndclass_path()
    try:
        lib = ctypes.CDLL(lib_path)
    except OSError as e:
        print(f"Could not load {lib_path}: {e}")
        sys.exit(1)

    lib.snd_model_load.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.snd_model_load.restype = ctypes.c_void_p

    lib.snd_model_input_samples.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.snd_model_input_samples.restype = None

    lib.snd_model_input_elements.argtypes = [ctypes.c_void_p]
    lib.snd_model_input_elements.restype = ctypes.c_int

    lib.snd_model_output_size.argtypes = [ctypes.c_void_p]
    lib.snd_model_output_size.restype = ctypes.c_int

    lib.snd_model_input_buffer.argtypes = [ctypes.c_void_p]
    lib.snd_model_input_buffer.restype = ctypes.c_void_p

    lib.snd_model_infer.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.snd_model_infer.restype = ctypes.c_int

    lib.snd_wav_fill_model_input.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.snd_wav_fill_model_input.restype = ctypes.c_int

    lib.snd_model_free.argtypes = [ctypes.c_void_p]
    lib.snd_model_free.restype = None

    model = lib.snd_model_load(model_path.encode("utf-8"), 2)
    if not model:
        print("model load failed (wrong input shape/dtype, or TFLite error)")
        sys.exit(1)

    b = ctypes.c_int()
    h = ctypes.c_int()
    lib.snd_model_input_samples(model, ctypes.byref(b), ctypes.byref(h))
    num_classes = lib.snd_model_output_size(model)
    n_in = lib.snd_model_input_elements(model)

    print()
    print("MODEL INPUT")
    print("-----------")
    print("batch:", b.value, "samples:", h.value, "flat elements:", n_in)
    print("num classes:", num_classes)

    if lib.snd_wav_fill_model_input(model, wav_path.encode("utf-8")) != 0:
        print("snd_wav_fill_model_input failed (see stderr from C library)")
        lib.snd_model_free(model)
        sys.exit(1)

    output = np.zeros(num_classes, dtype=np.float32)
    if lib.snd_model_infer(model, output.ctypes.data) != 0:
        print("inference failed")
        lib.snd_model_free(model)
        sys.exit(1)

    lib.snd_model_free(model)

    probs = softmax(output)
    idx = int(np.argmax(output))
    idx_p = int(np.argmax(probs))

    label = labels[idx] if idx < len(labels) else f"class {idx}"
    conf_raw = float(output[idx]) * 100.0
    conf_soft = float(probs[idx_p]) * 100.0

    print()
    print("Prediction")
    print("----------")
    print(label)
    print(f"argmax raw score ×100 (for logits, not a true %): {conf_raw:.4f}")
    print(f"softmax confidence: {conf_soft:.2f}%")

    top_k = min(5, num_classes)
    order = np.argsort(-probs)[:top_k]
    print()
    print(f"Top {top_k} (softmax):")
    for rank, i in enumerate(order, 1):
        name = labels[int(i)] if int(i) < len(labels) else f"class {int(i)}"
        print(f"  {rank}. {probs[int(i)] * 100:.2f}%  {name}")


if __name__ == "__main__":
    main()
