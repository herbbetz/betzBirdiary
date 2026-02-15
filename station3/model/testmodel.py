'''
test tflite models like classify.tflite and it's simple [1,N] output.
Usage: 
python testmodel.py test/8.jpg --model model0/classify.tflite --labels model0/bird_labels_de_latin.txt
python testmodel.py test/2.jpg --model model1/uas.tflite --labels model1/uas.txt

Smart TFLite classifier tester.
Tries multiple preprocessing modes to discover the correct pipeline.
'''
import argparse
import numpy as np
from PIL import Image
import tensorflow as tf


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


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


def predict_with_mode(mode, image_np, interpreter, input_details, output_details):
    """
    Run inference with a given preprocessing mode.
    Only realistic modes are included (raw_uint8, float_0_1, float_-1_1)
    """
    data = np.expand_dims(image_np, axis=0)
    input_dtype = input_details[0]["dtype"]

    try:
        if mode == "raw_uint8":
            data = data.astype(input_dtype)

        elif mode == "float_0_1":
            if input_dtype != np.float32:
                raise TypeError("Model expects UINT8, cannot use float_0_1")
            data = data.astype(np.float32) / 255.0

        elif mode == "float_-1_1":
            if input_dtype != np.float32:
                raise TypeError("Model expects UINT8, cannot use float_-1_1")
            data = (data.astype(np.float32) - 127.5) / 127.5

        output = run_inference(interpreter, input_details, output_details, data)
        output = dequantize_output(output, output_details)

        idx = int(np.argmax(output))
        conf = float(output[idx])
        return idx, conf

    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", required=True)
    args = parser.parse_args()

    labels = load_labels(args.labels)
    interpreter = tf.lite.Interpreter(model_path=args.model)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    _, height, width, _ = input_details[0]["shape"]

    image_np = load_image(args.image, width, height)

    modes = ["raw_uint8", "float_0_1", "float_-1_1"]

    print("\n=== Testing preprocessing modes ===\n")
    for mode in modes:
        idx, conf = predict_with_mode(mode, image_np, interpreter, input_details, output_details)
        if idx is None:
            print(f"{mode:15} → failed ({conf})")
        else:
            label = labels[idx] if idx < len(labels) else f"Class {idx}"
            print(f"{mode:15} → {label} ({conf*100:.2f}%)")


if __name__ == "__main__":
    main()
