'''
test tflite models like classify.tflite and it's simple [1,N] output.
Usage: 
python testmodel_embLabels.py test/2.jpg --model model1/bird_classifier_metadata.tflite

Smart TFLite classifier tester.
Tries multiple preprocessing modes to discover the correct pipeline.

> also for bird_classifier_metadata.tflite with embedded labels, but tflite_support.metadata does not work with python 3.11.2 within a venv in WSL Debian 12 (bookworm)
> so this can only show the class index and not see the labels
'''
import argparse
import numpy as np
from PIL import Image
import tensorflow as tf


# ---------- Helpers ----------

def load_labels(path):
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()]
    except Exception:
        return None


def load_image(image_path, width, height):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((width, height))
    return np.array(image)


def run_inference(interpreter, input_details, output_details, input_data):
    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()
    return interpreter.get_tensor(output_details[0]["index"])[0]


def dequantize_output(output_data, output_details):
    if output_details[0]["dtype"] != np.float32:
        scale, zero_point = output_details[0]["quantization"]
        if scale > 0:
            output_data = scale * (output_data - zero_point)
    return output_data


def preprocess(mode, image_np, input_dtype):
    data = np.expand_dims(image_np, axis=0)

    if mode == "raw_uint8":
        return data.astype(input_dtype)

    if input_dtype != np.float32:
        raise TypeError("Float preprocessing on non-float model")

    if mode == "float_0_1":
        return data.astype(np.float32) / 255.0

    if mode == "float_-1_1":
        return (data.astype(np.float32) - 127.5) / 127.5

    raise ValueError("Unknown mode")


def predict(mode, image_np, interpreter, input_details, output_details):
    try:
        input_dtype = input_details[0]["dtype"]
        data = preprocess(mode, image_np, input_dtype)
        output = run_inference(interpreter, input_details, output_details, data)
        output = dequantize_output(output, output_details)

        idx = int(np.argmax(output))
        conf = float(output[idx])
        return idx, conf, output

    except Exception as e:
        return None, str(e), None


def top_k(output, k=5):
    idxs = np.argsort(output)[::-1][:k]
    return [(int(i), float(output[i])) for i in idxs]


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", default=None)
    args = parser.parse_args()

    labels = load_labels(args.labels)

    print("\n=== Loading model ===")
    interpreter = tf.lite.Interpreter(model_path=args.model)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    input_shape = input_details[0]["shape"]
    input_dtype = input_details[0]["dtype"]
    output_shape = output_details[0]["shape"]
    output_dtype = output_details[0]["dtype"]

    print(f"Input shape : {input_shape}")
    print(f"Input dtype : {input_dtype}")
    print(f"Output shape: {output_shape}")
    print(f"Output dtype: {output_dtype}")

    _, height, width, _ = input_shape
    image_np = load_image(args.image, width, height)

    modes = ["raw_uint8", "float_0_1", "float_-1_1"]
    results = []

    print("\n=== Testing preprocessing modes ===\n")
    for mode in modes:
        idx, conf, output = predict(mode, image_np, interpreter, input_details, output_details)

        if idx is None:
            print(f"{mode:15} → failed ({conf})")
        else:
            label = labels[idx] if labels and idx < len(labels) else f"Class {idx}"
            print(f"{mode:15} → {label} ({conf*100:.2f}%)")
            results.append((mode, idx, conf, output))

    # ----- Authoritative mode selection -----

    if input_dtype == np.float32:
        authoritative_mode = "float_-1_1"
    else:
        authoritative_mode = "raw_uint8"

    print("\n=== AUTHORITATIVE RESULT ===")

    for mode, idx, conf, output in results:
        if mode == authoritative_mode:
            label = labels[idx] if labels and idx < len(labels) else f"Class {idx}"
            print(f"Mode : {mode}")
            print(f"Bird : {label}")
            print(f"Score: {conf*100:.2f}%")

            print("\nTop-5 predictions:")
            for i, score in top_k(output, 5):
                name = labels[i] if labels and i < len(labels) else f"Class {i}"
                print(f"  {name:25} {score*100:.2f}%")
            break

    print("\nDone.\n")


if __name__ == "__main__":
    main()
