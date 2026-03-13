# testdhtctype_ready.py
# -------------------------------
# Test script for the interrupt-driven DHT22 C driver (libdht22.so)
# Waits for the first valid reading before printing
# -------------------------------

import ctypes
import time

GPIO = 16  # BCM pin

lib = ctypes.CDLL("./libdht22.so")

# Function signatures
lib.dht22_init.argtypes = [ctypes.c_int]
lib.dht22_init.restype = ctypes.c_int

lib.dht22_read.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_long)
]
lib.dht22_read.restype = ctypes.c_int

lib.dht22_close.restype = None

# Initialize sensor
if lib.dht22_init(GPIO) != 0:
    raise RuntimeError("DHT22 init failed")

# Give background thread time to collect first sample
time.sleep(3)

temp = ctypes.c_double()
hum  = ctypes.c_double()
ts   = ctypes.c_long()

# Wait for first valid reading
for _ in range(20):
    ret = lib.dht22_read(ctypes.byref(temp), ctypes.byref(hum), ctypes.byref(ts))
    if temp.value != 0.0 or hum.value != 0.0:
        break
    time.sleep(0.5)

if temp.value == 0.0 and hum.value == 0.0:
    print("No valid DHT22 reading received. Check sensor wiring and pull-up.")
else:
    print(f"First reading: T={temp.value:.1f}°C  H={hum.value:.1f}%  ts={ts.value}")

try:
    while True:
        ret = lib.dht22_read(ctypes.byref(temp), ctypes.byref(hum), ctypes.byref(ts))
        print(f"T={temp.value:.1f}°C  H={hum.value:.1f}%  ts={ts.value}")
        time.sleep(3)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    lib.dht22_close()