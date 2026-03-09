'''
python3 bird_tflite_example.py test/8.jpg model0/classify.tflite model0/bird_labels_de_latin.txt
'''
#!/usr/bin/env python3

import ctypes
import sys
import numpy as np
from PIL import Image


def load_labels(path):

    with open(path,"r",encoding="utf-8") as f:
        return [line.strip() for line in f]


def main():

    if len(sys.argv) != 4:
        print("Usage:")
        print("bird_tflite_example.py image model.tflite labels.txt")
        sys.exit(1)

    image_path = sys.argv[1]
    model_path = sys.argv[2]
    labels_path = sys.argv[3]

    labels = load_labels(labels_path)

    lib = ctypes.CDLL("./libbird_tflite.so")

    # --------------------------------------------------
    # function signatures
    # --------------------------------------------------

    lib.bird_model_load.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int
    ]
    lib.bird_model_load.restype = ctypes.c_void_p


    lib.bird_model_input_size.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int)
    ]


    lib.bird_model_output_size.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_output_size.restype = ctypes.c_int


    lib.bird_model_input_buffer.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_input_buffer.restype = ctypes.c_void_p


    lib.bird_model_infer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p
    ]
    lib.bird_model_infer.restype = ctypes.c_int


    lib.bird_model_free.argtypes = [
        ctypes.c_void_p
    ]


    # --------------------------------------------------
    # load model
    # --------------------------------------------------

    model = lib.bird_model_load(
        model_path.encode("utf-8"),
        2
    )

    if not model:
        print("model load failed")
        sys.exit(1)


    # --------------------------------------------------
    # query input shape
    # --------------------------------------------------

    w = ctypes.c_int()
    h = ctypes.c_int()
    c = ctypes.c_int()

    lib.bird_model_input_size(
        model,
        ctypes.byref(w),
        ctypes.byref(h),
        ctypes.byref(c)
    )

    width  = w.value
    height = h.value
    channels = c.value


    # --------------------------------------------------
    # get tensor memory pointer
    # --------------------------------------------------

    ptr = lib.bird_model_input_buffer(model)

    size = width * height * channels

    input_array = np.ctypeslib.as_array(
        (ctypes.c_uint8 * size).from_address(ptr)
    )

    input_array = input_array.reshape(
        (height, width, channels)
    )


    # --------------------------------------------------
    # load image directly into tensor
    # --------------------------------------------------

    img = Image.open(image_path).convert("RGB")
    img = img.resize((width,height))

    np.copyto(
        input_array,
        np.array(img,dtype=np.uint8)
    )


    # --------------------------------------------------
    # allocate output buffer
    # --------------------------------------------------

    num_classes = lib.bird_model_output_size(model)

    output = np.zeros(num_classes,dtype=np.float32)


    # --------------------------------------------------
    # run inference
    # --------------------------------------------------

    lib.bird_model_infer(
        model,
        output.ctypes.data
    )


    # --------------------------------------------------
    # prediction
    # --------------------------------------------------

    idx = int(np.argmax(output))
    conf = float(output[idx])*100

    label = labels[idx] if idx < len(labels) else f"class {idx}"

    print()
    print("Number of classes:",num_classes)
    print("Prediction")
    print("----------")
    print(label)
    print(f"{conf:.2f}%")


    lib.bird_model_free(model)


if __name__ == "__main__":
    main()