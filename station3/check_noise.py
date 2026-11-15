"""
evaluates noise reduction by low-pass filter
check_noise.py: records idle HX711 noise and prints its spectrum (empty scale, no bird logic)  |  check_noise.py step [weight_g] (interactive on/off test with a known weight, default 20 g)
usage: python3 check_noise.py [duration_s] | python3 check_noise.py step [weight_g]   e.g. python3 check_noise.py step 32
step: press Enter right AFTER placing / removing the weight, then keep hands off during the 20 s countdown. Waiting at a prompt is ignored.
PSD is power spectral density: how much noise power (g²/Hz) sits at each frequency. A flat PSD means white noise, so averaging helps. A PSD rising toward 0 Hz means drift, so averaging does not help.
RMS root mean square is sigma
"""
import ctypes
import sys
import termios
import threading
import time
import numpy as np
from configBird3 import birdpath, hxDataPin, hxClckPin, hxPolScaleOff

ERR_BASE = -10000000
STEP_MODE = len(sys.argv) > 1 and sys.argv[1] == "step"
DURATION_S = float(sys.argv[1]) if len(sys.argv) > 1 and not STEP_MODE else 60.0
WEIGHT_G = float(sys.argv[2]) if STEP_MODE and len(sys.argv) > 2 else 20.0
FS = 10.0  # grid rate for the spectrum
SEG = 256  # Welch segment length: 25.6 s
BANDS = [(0.0, 0.1), (0.1, 0.3), (0.3, 1.0), (1.0, 3.0), (3.0, 5.0)]
CYCLES, HOLD_S, EDGE_S = 5, 20, 4  # HOLD_S: automatic hold after each Enter; EDGE_S: hand lag and settling skipped after Enter
POL = hxPolScaleOff[0]
scale = abs(hxPolScaleOff[1]) or 600

def open_driver():
    lib = ctypes.CDLL(f"{birdpath['appdir']}/c/libhx711.so")
    lib.hx711_init.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.hx711_read.restype = ctypes.c_int64
    if lib.hx711_init(hxDataPin, hxClckPin) != 0: sys.exit("HX711 init failed")
    return lib

def record(lib, stop, duration, data):
    # no sleep: hx711_read blocks until DOUT is ready, so the loop runs at the conversion rate
    t0 = time.monotonic()
    while not stop.is_set() and time.monotonic() - t0 < duration:
        value = lib.hx711_read()
        if value <= ERR_BASE: continue  # glitch or timeout: skip
        data["t"].append(time.monotonic())
        data["raw"].append(value)
        data["state"].append(data["cur"])

def countdown(seconds, text):
    # live countdown on one terminal line, then drop Enter presses typed meanwhile
    for left in range(seconds, 0, -1):
        print(f"\r  {text}: {left:2d} s ", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 40 + "\r", end="")
    termios.tcflush(sys.stdin, termios.TCIFLUSH)

def hold(marks, data, state, prompt, text):
    # Enter marks the physical action, the hold then runs automatically; state: 1 weight on, 0 empty, -1 waiting
    input(prompt)
    marks.append(time.monotonic())
    data["cur"] = state
    countdown(HOLD_S, text)
    data["cur"] = -1

def run_idle(worker, data):
    t0 = time.monotonic()
    print(f"recording {DURATION_S:.0f} s of idle noise, Ctrl-C stops early and saves")
    while worker.is_alive():
        worker.join(1.0)
        print(f"\r  {max(0.0, DURATION_S - (time.monotonic() - t0)):4.0f} s left, {len(data['t'])} samples ", end="", flush=True)
    print()
    return []

def run_step_test(data):
    # marks: 0 = start (empty), 2k-1 = weight on in cycle k, 2k = weight off in cycle k
    marks = []
    hold(marks, data, 0, "Scale empty and still? Press Enter to start the baseline: ", "empty, hands off")
    for k in range(CYCLES):
        hold(marks, data, 1, f"[{k + 1}/{CYCLES}] PUT {WEIGHT_G:g} g ON, then press Enter: ", "weight on, hands off")
        hold(marks, data, 0, f"[{k + 1}/{CYCLES}] TAKE {WEIGHT_G:g} g OFF, then press Enter: ", "empty, hands off")
    return marks

def noise_spectrum(t, raw, scale, fs=FS, seg=SEG):
    # resample to a uniform grid by linear interpolation
    grid = np.arange(t[0], t[-1], 1 / fs)
    x = np.interp(grid, t, raw) / scale
    # Welch's method: Hann-windowed 50% overlapping segments, averaged periodogram
    win = np.hanning(seg)
    segs = [x[i:i + seg] - x[i:i + seg].mean() for i in range(0, len(x) - seg + 1, seg // 2)]
    psd = np.mean([np.abs(np.fft.rfft(s * win)) ** 2 for s in segs], axis=0) / (fs * (win ** 2).sum())
    psd[1:-1] *= 2  # one-sided PSD: fold in the negative frequencies (DC and Nyquist bins stay)
    return np.fft.rfftfreq(seg, 1 / fs), psd  # g^2/Hz

def report(freq, psd):
    df = freq[1] - freq[0]
    for lo, hi in BANDS:
        m = (freq >= lo) & (freq < hi)
        print(f"{lo:4.1f}-{hi:4.1f} Hz  rms {np.sqrt(psd[m].sum() * df):6.2f} g  psd {psd[m].mean():9.3f} g^2/Hz")

def window(t, marks, i):
    # samples EDGE_S .. HOLD_S seconds after mark i
    return (t >= marks[i] + EDGE_S) & (t < marks[i] + HOLD_S)

def report_steps(t, raw, marks):
    # weight = POL * raw difference / scale, signed like production; the empty level under the weight is the mean of the empty holds before and after
    for k in range(1, CYCLES + 1):
        on, before, after = window(t, marks, 2 * k - 1), window(t, marks, 2 * k - 2), window(t, marks, 2 * k)
        if min(on.sum(), before.sum(), after.sum()) < 20: print(f"cycle {k}: windows too short"); continue
        base = (raw[before].mean() + raw[after].mean()) / 2  # cancels linear drift
        drift = POL * (raw[after].mean() - raw[before].mean()) / scale
        print(f"cycle {k}: step {POL * (raw[on].mean() - base) / scale:+7.2f} g (expected {WEIGHT_G:+g})  empty drift {drift:+6.2f} g  on std {raw[on].std() / scale:5.2f} g")

if __name__ == "__main__":
    lib = open_driver()
    time.sleep(2.0)  # settle
    data = {"t": [], "raw": [], "state": [], "cur": -1}
    stop = threading.Event()
    worker = threading.Thread(target=record, args=(lib, stop, 1e9 if STEP_MODE else DURATION_S, data))
    worker.start()  # recording runs while the main thread talks to you
    try:
        marks = run_step_test(data) if STEP_MODE else run_idle(worker, data)
    except KeyboardInterrupt:
        print("\ninterrupted, saving what was recorded")
        marks = []
    stop.set()
    worker.join()
    lib.hx711_close()
    t, raw, state = np.array(data["t"]), np.array(data["raw"], dtype=float), np.array(data["state"])
    np.savetxt("ramdisk/check_step_raw.csv" if STEP_MODE else "ramdisk/check_noise_raw.csv", np.column_stack([t, raw, state]), fmt="%.3f,%d,%d", header=f"mono_t,raw,state (1 weight on, 0 empty, -1 waiting) | weight_g={WEIGHT_G:g} pol={POL} scale={scale}")
    print(f"{len(t)} samples, {(len(t) - 1) / (t[-1] - t[0]):.2f} Hz, std {raw.std() / scale:.2f} g")
    if not STEP_MODE: report(*noise_spectrum(t, raw, scale))
    elif len(marks) == 2 * CYCLES + 1: report_steps(t, raw, marks)
    else: print("step test incomplete, no report")
