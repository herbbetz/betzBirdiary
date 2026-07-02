import ctypes
import time
import statistics

lib = ctypes.CDLL("./libhx711.so")

lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
lib.hx711_init.restype = ctypes.c_int

lib.hx711_read.restype = ctypes.c_long
lib.hx711_close.restype = None

if lib.hx711_init(17, 23) != 0:
    raise RuntimeError("HX711 init failed")

samples = []

try:
    while True:
        v = lib.hx711_read()
        samples.append(v)

        if len(samples) == 100:
            mean = statistics.mean(samples)
            stdev = statistics.stdev(samples)
            print(
                f"min={min(samples):8d} "
                f"max={max(samples):8d} "
                f"span={max(samples)-min(samples):5d} "
                f"mean={mean:10.1f} "
                f"std={stdev:7.2f}"
            )
            samples.clear()

        time.sleep(0.1)

except KeyboardInterrupt:
    pass

finally:
    lib.hx711_close()