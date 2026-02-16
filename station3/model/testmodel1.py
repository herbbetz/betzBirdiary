#!/usr/bin/env python3
"""
Test float MobileNetV2 TFLite models with [1, N] output.

Usage:
  python testmodel_float.py image.jpg --model model.tflite --labels labels.txt
  python testmodel1.py test/2.jpg --model model1/bird_classifier.tflite --labels model1/labels.txt
"""

import argparse
import numpy as np
from PIL import Image
import tensorflow as tf


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def preprocess_image(image_path, width, height):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((width, height))

    # float32 normalization to [-1, 1]
    input_data = np.array(image, dtype=np.float32)
    input_data = (input_data - 127.5) / 127.5

    return np.expand_dims(input_data, axis=0)


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

    height = input_details[0]["shape"][1]
    width = input_details[0]["shape"][2]

    input_data = preprocess_image(args.image, width, height)

    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]["index"])[0]

    num_classes = output_data.shape[0]
    predicted_index = int(np.argmax(output_data))
    confidence = float(output_data[predicted_index]) * 100

    predicted_class = (
        labels[predicted_index]
        if predicted_index < len(labels)
        else f"Class {predicted_index}"
    )

    print(f"Number of classes: {num_classes}")
    print(f"Predicted class: {predicted_class} ({confidence:.2f}%)")


if __name__ == "__main__":
    main()
