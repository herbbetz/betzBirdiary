import ctypes
import time

lib = ctypes.CDLL("./libdht22.so")

lib.dht22_init.argtypes = [ctypes.c_int]
lib.dht22_init.restype = ctypes.c_int

lib.dht22_read.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double)
]
lib.dht22_read.restype = ctypes.c_int

lib.dht22_close.restype = None


GPIO = 16

if lib.dht22_init(GPIO) != 0:
    raise RuntimeError("DHT22 init failed")

temp = ctypes.c_double()
hum  = ctypes.c_double()

try:

    while True:

        ret = lib.dht22_read(ctypes.byref(temp), ctypes.byref(hum))

        if ret == 0:
            print(f"T={temp.value:.1f}°C  H={hum.value:.1f}%")
        elif ret == -2:
            print("Checksum error")
        else:
            print("Timeout")

        time.sleep(3) # DHT22 cannot be polled faster than about 2 seconds.

except KeyboardInterrupt:
    pass

finally:
    lib.dht22_close()