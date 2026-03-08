'''
test tflite models like classify.tflite and it's simple [1,N] output.
Usage:
python test0runtime.py test/8.jpg --model model0/classify.tflite --labels model0/bird_labels_de_latin.txt
needs python 3.11 environment: source /home/pi/.pyenv/versions/birdvenv/bin/activate
'''

import argparse
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def preprocess_image(image_path, width, height):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((width, height), Image.BILINEAR)

    img = np.array(image).astype(np.uint8)
    return np.expand_dims(img, axis=0)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    image_path = args.image

    # --- load labels ---
    labels = load_labels(args.labels)

    # --- load model ---
    interpreter = Interpreter(
        model_path=args.model,
        num_threads=args.threads
    )
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    height = input_details[0]["shape"][1]
    width = input_details[0]["shape"][2]

    # --- preprocess ---
    input_data = preprocess_image(image_path, width, height)

    # --- inference ---
    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    # --- read output ---
    output_data = interpreter.get_tensor(output_details[0]["index"])[0]

    # handle quantized models
    if output_data.dtype != np.float32:
        output_data = output_data / 255.0

    num_classes = output_data.shape[0]
    predicted_index = int(np.argmax(output_data))
    confidence = float(output_data[predicted_index]) * 100.0

    predicted_class = (
        labels[predicted_index]
        if predicted_index < len(labels)
        else f"Class {predicted_index}"
    )

    print(f"Number of classes: {num_classes}")
    print(f"Predicted class: {predicted_class} ({confidence:.2f}%)")


if __name__ == "__main__":
    main()