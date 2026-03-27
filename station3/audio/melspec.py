# mel spectrogram example suitable for BirdNET KI
# 'sudo apt install python3-librosa' noch nicht für Trixie => 'pip install librosa' in birdvenv (python 3.11)
# usage: python script.py file.wav

# usage: python melspec_compare.py file.wav

import sys
import librosa
import numpy as np
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("Usage: python melspec_compare.py <audio.wav>")
    sys.exit(1)

FILE = sys.argv[1]

TARGET_SR = 48000
DURATION = 3.0

# --- load ---
y, sr = librosa.load(FILE, sr=TARGET_SR, mono=True)

# fix length to 3 sec
target_len = int(TARGET_SR * DURATION)
if len(y) < target_len:
    y = np.pad(y, (0, target_len - len(y)))
else:
    y = y[:target_len]

# --- STFT (Audacity-like) ---
D = librosa.stft(y, n_fft=2048, hop_length=512)
S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

# --- Mel (BirdNET-like) ---
mel = librosa.feature.melspectrogram(
    y=y,
    sr=TARGET_SR,
    n_fft=1024,
    hop_length=280,
    n_mels=96,
    fmin=0,
    fmax=15000
)
mel_db = librosa.power_to_db(mel, ref=np.max)

# --- plot side by side ---
plt.figure(figsize=(12, 5))

# left: STFT
plt.subplot(1, 2, 1)
plt.imshow(S_db, aspect='auto', origin='lower', cmap='inferno', vmin=-80, vmax=0)
plt.title("STFT (Audacity-like)")
plt.xlabel("Time")
plt.ylabel("Frequency bins")

# right: Mel
plt.subplot(1, 2, 2)
plt.imshow(mel_db, aspect='auto', origin='lower', cmap='inferno', vmin=-80, vmax=0)
plt.title("Mel (BirdNET-like)")
plt.xlabel("Time")
plt.ylabel("Mel bins")

plt.tight_layout()

# save instead of show (SSH-safe)
out = FILE + "_compare.svg"
plt.savefig(out)
plt.close()

print("Saved:", out)
'''
# sliding window, if clips are longer than 3 secs:
def split_windows(y, sr, win_sec=3, step_sec=1):
    win = int(win_sec * sr)
    step = int(step_sec * sr)
    return [y[i:i+win] for i in range(0, len(y)-win+1, step)]
'''