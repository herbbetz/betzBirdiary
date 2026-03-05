import ctypes
import time

lib = ctypes.CDLL("./libhx711.so")

# define function signatures
lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
lib.hx711_init.restype = ctypes.c_int

lib.hx711_read.restype = ctypes.c_long
lib.hx711_close.restype = None

# init GPIO
ret = lib.hx711_init(17, 23)
if ret != 0:
    print("Init failed:", ret)
    exit(1)

try:
    while True:
        value = lib.hx711_read()
        print(value)
        time.sleep(0.5)

except KeyboardInterrupt:
    pass

finally:
    lib.hx711_close()