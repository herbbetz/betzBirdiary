'''
python3 bird_tflite_model2.py test/8.jpg model2/birdiary_v5_mobilenetv3.tflite model2/labels.txt
'''
import ctypes
import sys
import numpy as np
from PIL import Image



def load_labels(path):

    with open(path,"r",encoding="utf-8") as f:
        return [line.strip() for line in f]



def softmax(x):

    e = np.exp(x - np.max(x))
    return e / e.sum()



def main():

    if len(sys.argv) != 4:

        print("Usage:")
        print("bird_tflite_model2.py image model.tflite labels.txt")
        sys.exit(1)


    image_path  = sys.argv[1]
    model_path  = sys.argv[2]
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


    lib.bird_model_input_info.argtypes = [

        ctypes.c_void_p,

        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),

        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int)
    ]


    lib.bird_model_input_buffer.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_input_buffer.restype = ctypes.c_void_p


    lib.bird_model_output_size.argtypes = [
        ctypes.c_void_p
    ]
    lib.bird_model_output_size.restype = ctypes.c_int


    lib.bird_model_infer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p
    ]


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
    # query input info
    # --------------------------------------------------

    w = ctypes.c_int()
    h = ctypes.c_int()
    c = ctypes.c_int()
    layout = ctypes.c_int()
    dtype  = ctypes.c_int()

    lib.bird_model_input_info(

        model,

        ctypes.byref(w),
        ctypes.byref(h),
        ctypes.byref(c),

        ctypes.byref(layout),
        ctypes.byref(dtype)
    )

    width  = w.value
    height = h.value
    channels = c.value


    print()
    print("INPUT")
    print("-----")

    print("width:",width)
    print("height:",height)
    print("channels:",channels)

    print("layout:", "NCHW" if layout.value else "NHWC")
    print("dtype:",  "float32" if dtype.value else "uint8")



    # --------------------------------------------------
    # get tensor pointer
    # --------------------------------------------------

    ptr = lib.bird_model_input_buffer(model)

    size = width*height*channels

    input_array = np.ctypeslib.as_array(
        (ctypes.c_float * size).from_address(ptr)
    )



    # --------------------------------------------------
    # load image
    # --------------------------------------------------

    img = Image.open(image_path).convert("RGB")
    img = img.resize((width,height))

    arr = np.array(img,dtype=np.float32)/255.0


    # normalization (PyTorch)

    mean = np.array([0.485,0.456,0.406],dtype=np.float32)
    std  = np.array([0.229,0.224,0.225],dtype=np.float32)

    arr = (arr - mean) / std



    # --------------------------------------------------
    # layout conversion
    # --------------------------------------------------

    if layout.value == 1:

        # NCHW

        input_array = input_array.reshape(
            (channels,height,width)
        )

        arr = arr.transpose((2,0,1))

        np.copyto(input_array,arr)

    else:

        # NHWC

        input_array = input_array.reshape(
            (height,width,channels)
        )

        np.copyto(input_array,arr)



    # --------------------------------------------------
    # inference
    # --------------------------------------------------

    num_classes = lib.bird_model_output_size(model)

    output = np.zeros(num_classes,dtype=np.float32)

    lib.bird_model_infer(
        model,
        output.ctypes.data
    )



    probs = softmax(output)


    idx = np.argsort(probs)[-5:][::-1]


    print()
    print("TOP5")
    print("----")

    for i in idx:

        label = labels[i] if i < len(labels) else f"class {i}"

        print(
            f"{label:30s}",
            f"{probs[i]*100:6.2f}%"
        )


    lib.bird_model_free(model)



if __name__ == "__main__":
    main()