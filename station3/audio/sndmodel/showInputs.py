try:
    import tflite_runtime.interpreter as tflite
    Interpreter = tflite.Interpreter
except ImportError:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter

model_path = "./BirdNET_6K_GLOBAL_MODEL.tflite"

itp = Interpreter(model_path=model_path)
itp.allocate_tensors()

inp = itp.get_input_details()[0]
out = itp.get_output_details()[0]

print("INPUT name:", inp.get("name"))
print("INPUT shape:", inp["shape"])
print("INPUT dtype:", inp["dtype"])
print("INPUT quant params:", inp.get("quantization_parameters", {}))

print("OUTPUT name:", out.get("name"))
print("OUTPUT shape:", out["shape"])
print("OUTPUT dtype:", out["dtype"])
print("OUTPUT quant params:", out.get("quantization_parameters", {}))