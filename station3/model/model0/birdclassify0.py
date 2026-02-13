'''
simplest app, working only for classify.tflite and it's simple [1,N] output.
Usage: python birdclassify.py image.jpg
'''
import sys
import numpy as np
from PIL import Image
import tensorflow as tf

# ---- CONFIG ----
MODEL_PATH = "./model/classify.tflite"
LABELS_PATH = "./model/bird_labels_de_latin.txt"
# ----------------


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def preprocess_image(image_path, width, height, floating_model):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((width, height))
    input_data = np.expand_dims(np.array(image), axis=0)

    if floating_model:
        input_data = (np.float32(input_data) - 127.5) / 127.5

    return input_data


def main():
    if len(sys.argv) < 2:
        print("Usage: python birdclassify.py image.jpg")
        sys.exit(1)

    image_path = sys.argv[1]

    # Load labels
    labels = load_labels(LABELS_PATH)

    # Load model
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    height = input_details[0]["shape"][1]
    width = input_details[0]["shape"][2]
    floating_model = input_details[0]["dtype"] == np.float32

    # Preprocess and run inference
    input_data = preprocess_image(image_path, width, height, floating_model)
    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    # Get output [1, N]
    output_data = interpreter.get_tensor(output_details[0]["index"])[0]

    # Handle uint8 output models
    if output_data.dtype != np.float32:
        output_data = output_data / 255.0

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
