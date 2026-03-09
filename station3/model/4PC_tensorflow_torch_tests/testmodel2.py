'''
Analyse image using tflite (which was built from pytorch) model:
Usage: python testmodel2.py ./test/2.jpg --model ./model2/birdiary_v5_mobilenetv3.tflite --labels ./model2/labels.txt
'''
import os
import argparse
import numpy as np
from PIL import Image
import tensorflow as tf
import sys

def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]

def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)

def preprocess_image(image_path, target_width, target_height):
    image = Image.open(image_path).convert("RGB")
    
    # 1. Scaling (Maintain aspect ratio)
    src_w, src_h = image.size
    scale = max(target_width / src_w, target_height / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 2. Center crop
    left = (new_w - target_width) // 2
    top = (new_h - target_height) // 2
    image = image.crop((left, top, left + target_width, top + target_height))

    # 3. Normalization (H, W, C)
    input_data = np.array(image, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    input_data = (input_data - mean) / std

    # 4. Transpose to NCHW [C, H, W] for PyTorch-converted models
    input_data = input_data.transpose((2, 0, 1))

    # 5. Add Batch Dimension [1, 3, 224, 224]
    input_data = np.expand_dims(input_data, axis=0)

    return input_data.astype(np.float32)

def main():
    parser = argparse.ArgumentParser(description="Birdiary TFLite Classifier")
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("--model", required=True, help="Path to .tflite model")
    parser.add_argument("--labels", required=True, help="Path to labels.txt")
    args = parser.parse_args()

    if not os.path.exists(args.labels):
        print(f"Error: Labels file not found at {args.labels}")
        sys.exit(1)

    labels = load_labels(args.labels)

    try:
        interpreter = tf.lite.Interpreter(model_path=args.model)
        interpreter.allocate_tensors()
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Get dimensions (Index 2 and 3 because of NCHW format)
    height = input_details[0]["shape"][2]
    width = input_details[0]["shape"][3]

    # Preprocess and Run
    input_data = preprocess_image(args.image, width, height)
    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    # Get Results
    output_data = interpreter.get_tensor(output_details[0]["index"])[0]
    probabilities = softmax(output_data)

    predicted_index = np.argmax(probabilities)
    confidence = probabilities[predicted_index] * 100
    predicted_class = labels[predicted_index] if predicted_index < len(labels) else f"ID {predicted_index}"

    # Final Output
    print(f"\nResult: {predicted_class} ({confidence:.2f}%)")

if __name__ == "__main__":
    main()