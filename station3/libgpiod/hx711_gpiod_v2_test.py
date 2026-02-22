"""
HX711 minimal test using libgpiod v2 API (Debian Trixie compatible)
Verified against gpioinfo output

BEWARE: 'gpioinfo | grep GPIO17' must not show a consumer!

DATA  -> gpiochip0 line 17
CLOCK -> gpiochip0 line 23

Purpose:
- Verify GPIO access independent of lgpio
- Confirm HX711 timing & data read
- Provide verbose debug output

Pins are BCM numbering.
"""
import gpiod
import time

# =========================
# CONFIG
# =========================
CHIP_PATH = "/dev/gpiochip0"
DOUT = 17   # HX711 DT
SCK  = 23   # HX711 SCK

print(f"[INFO] Opening {CHIP_PATH}")
chip = gpiod.Chip(CHIP_PATH)

# ---- Request lines (v1-style API used in Debian build)
dout_line = chip.get_line(DOUT)
sck_line  = chip.get_line(SCK)

dout_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_IN)
sck_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])

print("[INFO] Lines requested")

# =========================
# HX711 read function
# =========================
def read_raw():
    # wait until ready (DOUT LOW)
    while dout_line.get_value() == 1:
        time.sleep(0.001)

    count = 0

    for _ in range(24):
        sck_line.set_value(1)
        count = (count << 1) | dout_line.get_value()
        sck_line.set_value(0)

    # 25th pulse → gain 128
    sck_line.set_value(1)
    sck_line.set_value(0)

    # 2's complement conversion
    if count & 0x800000:
        count -= 0x1000000

    return count


print("[INFO] Waiting for HX711 ready…")
val = read_raw()
print(f"[RESULT] Raw HX711 value: {val}")

chip.close()