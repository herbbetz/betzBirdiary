import pyaudio

p = pyaudio.PyAudio()
info = p.get_device_info_by_index(1)  # your USB mic index
print(info)
for rate in [8000, 11025, 16000, 22050, 32000, 44100, 48000]:
    try:
        stream = p.open(rate=rate,
                        format=pyaudio.paInt16,
                        channels=1,
                        input=True,
                        input_device_index=1)
        stream.close()
        print(f"Rate {rate} Hz: OK")
    except:
        print(f"Rate {rate} Hz: FAILED")
p.terminate()