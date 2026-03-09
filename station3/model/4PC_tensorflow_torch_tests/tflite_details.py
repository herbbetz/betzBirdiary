#!/usr/bin/env python3
import sys
from collections import Counter
import tensorflow as tf


def infer_layer_type(name: str) -> str:
    name = name.lower()

    if "depthwise" in name:
        return "DepthwiseConv"
    if "conv" in name:
        return "Conv2D"
    if "matmul" in name or "logits" in name:
        return "Dense"
    if "avgpool" in name or "pool" in name:
        return "Pooling"
    if "add" in name:
        return "Add/Residual"
    if "relu" in name:
        return "Activation"
    return "Other"


def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_tflite.py model.tflite")
        sys.exit(1)

    model_path = sys.argv[1]

    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    tensor_details = interpreter.get_tensor_details()

    print(f"\nTotal tensors: {len(tensor_details)}\n")

    # -------- raw tensor dump --------
    for t in tensor_details:
        print("Name:   ", t.get("name"))
        print("Index:  ", t.get("index"))
        print("Shape:  ", t.get("shape"))
        print("Dtype:  ", t.get("dtype"))
        print("Quant.: ", t.get("quantization"))
        print("-" * 40)

    # -------- summary --------
    counter = Counter()
    for t in tensor_details:
        layer_type = infer_layer_type(t.get("name", ""))
        counter[layer_type] += 1

    print("\n=== Layer Summary (inferred) ===\n")
    print(f"{'Layer type':<20}Count")
    print("-" * 30)

    for layer, count in sorted(counter.items()):
        print(f"{layer:<20}{count}")

    print("\nNote: counts are inferred from tensor names, not exact op list.")


if __name__ == "__main__":
    main()
