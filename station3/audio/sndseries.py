# make sound clip as long as loudness is over a threshold
# apt install python3-pyaudio python3-soundfile
# mic and headphone card default set in /etc/asound.conf
# testmic.py found 44100 as rate accepted by my mic
# python pyaudio to highlevel for keeping up with alsa buffer after the 2nd wav, so not working -> lower level python (pyalsaaudio) or C solution
import pyaudio
import wave
import math

# Parameters
CHUNK = 4096            # larger chunk to avoid overflow
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
THRESHOLD = 500
SILENCE_LIMIT = 2.0

p = pyaudio.PyAudio()

# Choose input device
DEVICE_INDEX = None
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    if "USB" in dev['name']:
        DEVICE_INDEX = i
        break

if DEVICE_INDEX is None:
    raise RuntimeError("No USB mic found")

print(f"Using input device: {p.get_device_info_by_index(DEVICE_INDEX)['name']}")

def rms(data):
    count = len(data)//2
    format_data = [int.from_bytes(data[i*2:i*2+2], 'little', signed=True) for i in range(count)]
    sum_squares = sum(sample**2 for sample in format_data)
    return math.sqrt(sum_squares / count) if count else 0

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=DEVICE_INDEX,
                frames_per_buffer=CHUNK)

clip_count = 1
frames = []
silent_chunks = 0
silence_chunks_needed = int(SILENCE_LIMIT * RATE / CHUNK)

print("Listening for sound... Press Ctrl+C to exit.")

try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        level = rms(data)
        if level > THRESHOLD:
            frames.append(data)
            silent_chunks = 0
        else:
            if frames:
                silent_chunks += 1
                if silent_chunks >= silence_chunks_needed:
                    filename = f"{clip_count}.wav"
                    wf = wave.open(filename, 'wb')
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(p.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    print(f"Saved {filename}")
                    clip_count += 1
                    frames = []
                    silent_chunks = 0
except KeyboardInterrupt:
    if frames:
        filename = f"{clip_count}.wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"Saved {filename}")
    print("Exiting gracefully...")

stream.stop_stream()
stream.close()
p.terminate()