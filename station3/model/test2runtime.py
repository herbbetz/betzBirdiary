'''
Test model2 with tflite_runtime using birdclassify2-style preprocessing.
Usage:
python test2runtime.py test/8.jpg --model model2/birdiary_v5_mobilenetv3.tflite --labels model2/labels.txt
'''

import argparse
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter


def load_labels(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)


def preprocess_image(image_path, target_width, target_height):
    image = Image.open(image_path).convert("RGB")
    # direct resize (stretch):
    image = image.resize((target_width, target_height), Image.BILINEAR)

    '''
    # 1) Scale while preserving aspect ratio
    src_w, src_h = image.size
    scale = max(target_width / src_w, target_height / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 2) Center crop
    left = (new_w - target_width) // 2
    top = (new_h - target_height) // 2
    image = image.crop((left, top, left + target_width, top + target_height))
    '''

    # 3) Normalize (PyTorch ImageNet normalization)
    arr = np.array(image, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std

    # 4) HWC -> CHW and add batch dimension
    arr = arr.transpose((2, 0, 1))
    arr = np.expand_dims(arr, axis=0)

    return arr.astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    labels = load_labels(args.labels)

    interpreter = Interpreter(
        model_path=args.model,
        num_threads=args.threads
    )
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # model2 is NCHW: [1, C, H, W]
    height = input_details[0]["shape"][2]
    width = input_details[0]["shape"][3]

    input_data = preprocess_image(args.image, width, height)

    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    logits = interpreter.get_tensor(output_details[0]["index"])[0]
    probs = softmax(logits)

    top_idx = np.argsort(probs)[-5:][::-1]

    print(f"Number of classes: {probs.shape[0]}")
    print("Top 5 predictions:")
    for i in top_idx:
        label = labels[i] if i < len(labels) else f"Class {i}"
        print(f"  {label:30s} {probs[i] * 100:6.2f}%")


if __name__ == "__main__":
    main()
