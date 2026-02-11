'''
python birdclass-tflite.py 8.jpg --model ./detect.tflite --labels ./labelmap.txt
python birdclass-tflite.py 8.jpg --model ./classify.tflite --labels ./bird_labels_de_latin.txt
www.worldbirdnames.org
pip install tensorflow
'''
import argparse
import numpy as np
from PIL import Image
import tensorflow as tf

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
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", required=True)
    args = parser.parse_args()

    labels = load_labels(args.labels)

    # Load TFLite model
    interpreter = tf.lite.Interpreter(model_path=args.model)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    height = input_details[0]["shape"][1]
    width = input_details[0]["shape"][2]
    floating_model = input_details[0]["dtype"] == np.float32

    # Preprocess image
    input_data = preprocess_image(args.image, width, height, floating_model)
    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    # Detect output type by shape
    output_shapes = [tuple(interpreter.get_tensor(o["index"]).shape) for o in output_details]

    # Classifier (single tensor, shape [1, num_classes])
    if len(output_shapes) == 1 and len(output_shapes[0]) == 2:
        output_data = interpreter.get_tensor(output_details[0]["index"])[0]
        if not floating_model:
            output_data = output_data / 255.0
        predicted_index = int(np.argmax(output_data))
        confidence = float(output_data[predicted_index]) * 100
        predicted_class = labels[predicted_index] if predicted_index < len(labels) else f"Class {predicted_index}"
        print(f"Number of classes: {len(output_data)}")
        print(f"Predicted class: {predicted_class} ({confidence:.2f}%)")

    # Detection model (usually outputs: [1, num_boxes, 4], [1, num_boxes], [1, num_boxes], [1])
    else:
        tensors = [interpreter.get_tensor(o["index"])[0] for o in output_details]

        # Heuristic: find 1D tensor of length num_boxes -> scores
        scores = None
        classes_idx = None
        for t in tensors:
            if t.ndim == 1:
                num_boxes = t.shape[0]
                # if values <=1, probably scores
                if np.all((t >= 0) & (t <= 1)):
                    scores = t
                else:  # otherwise class indices
                    classes_idx = t.astype(int)

        if scores is None or classes_idx is None:
            # fallback: try 2D tensor shape [1, num_boxes]
            for t in tensors:
                if t.ndim == 2 and t.shape[0] == 1:
                    if np.all((t >= 0) & (t <= 1)):
                        scores = t[0]
                    else:
                        classes_idx = t[0].astype(int)

        if scores is None or classes_idx is None:
            raise RuntimeError("Could not determine scores/classes from detect model outputs.")

        top_idx = int(np.argmax(scores))
        confidence = float(scores[top_idx]) * 100
        class_index = int(classes_idx[top_idx])
        predicted_class = labels[class_index] if class_index < len(labels) else f"Class {class_index}"
        print(f"Number of classes: {len(labels)}")
        print(f"Predicted class: {predicted_class} ({confidence:.2f}%)")

if __name__ == "__main__":
    main()
