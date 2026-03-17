# dhtBirdCt.py
# Upload environmental data from DHT22 (ctypes driver) to Birdiary platform

from datetime import datetime
import time
import json
import requests
import ctypes
import os
import math

# own modules
from sharedBird import roundFlt
import msgBird as ms
from configBird3 import birdpath, serverUrl, boxId, dhtPin


# -------------------------------
# Helper
# -------------------------------
def now():
    return datetime.now()


# -------------------------------
# ctypes DHT22 wrapper
# -------------------------------
class DHT22_CT:

    def __init__(self, gpio_pin):
        self.gpio_pin = gpio_pin
        libpath = f"{birdpath['appdir']}/c/libdht22.so"
        self.lib = ctypes.CDLL(libpath)

        self.lib.dht22_init.argtypes = [ctypes.c_int]
        self.lib.dht22_init.restype = ctypes.c_int

        self.lib.dht22_read.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double)
        ]
        self.lib.dht22_read.restype = ctypes.c_int

        self.lib.dht22_close.restype = None

        if self.lib.dht22_init(self.gpio_pin) != 0:
            raise RuntimeError(f"DHT22 init failed on GPIO {self.gpio_pin}")

    def read(self):
        temp = ctypes.c_double()
        hum = ctypes.c_double()

        ret = self.lib.dht22_read(ctypes.byref(temp), ctypes.byref(hum))

        if ret == 0:
            return time.time(), temp.value, hum.value
        elif ret == -2:
            raise RuntimeError("Checksum error")
        else:
            raise RuntimeError("Timeout")

    def cancel(self):
        self.lib.dht22_close()


# -------------------------------
# Calculations
# -------------------------------
def humid_abs(temperature, humidity_rel):
    if temperature < -40 or temperature > 80:
        return 0.0
    if humidity_rel < 0 or humidity_rel > 100:
        return 0.0

    svp = 6.112 * math.exp(17.67 * temperature / (temperature + 243.5))
    ah = svp * humidity_rel * 2.1674 / (273.15 + temperature)
    return roundFlt(ah)


# -------------------------------
# Local storage
# -------------------------------
def tempProtocol(env_data):
    datafile = f"{birdpath['appdir']}/tempdata/tempdata.json"
    os.makedirs(os.path.dirname(datafile), exist_ok=True)

    data = []
    maxdata = 160

    if os.path.exists(datafile):
        with open(datafile, "r") as infile:
            try:
                data = json.load(infile)
            except json.JSONDecodeError:
                ms.log(f"Corrupt JSON, backing up {datafile}")
                os.rename(datafile, datafile + ".bak")
                data = []

    env_data["date"] = env_data["date"].strftime("%Y:%m:%d:%H:%M")
    env_data["humid_abs"] = humid_abs(env_data["temperature"], env_data["humidity"])

    data.append(env_data)
    if len(data) > maxdata:
        data = data[-maxdata:]

    with open(datafile, "w") as outfile:
        json.dump(data, outfile, indent=2)


def write_env_webserv(env_data):
    filename = f"{birdpath['ramdisk']}/env.json"
    env_data["date"] = str(env_data["date"]).split('.')[0]

    with open(filename, 'w') as wfile:
        json.dump(env_data, wfile)


# -------------------------------
# Upload
# -------------------------------
def send_realtime_environment(envData):
    envData["date"] = str(envData["date"])

    try:
        r = requests.post(serverUrl + 'environment/' + boxId, json=envData, timeout=20)
        r.raise_for_status()

        ms.log(f"environment data sent: {envData}")
        ms.log(f"Corresponding environment_id: {r.text}")
        ms.setEnvirEvt()

    except (requests.ConnectionError, requests.Timeout) as exception:
        ms.log('failed envir upload - ' + str(exception))

    except requests.HTTPError as e:
        response_text = getattr(e.response, "text", "no response")
        ms.log(f'HTTP error: {e} - {response_text}')


# -------------------------------
# Main
# -------------------------------
def main():
    ms.init()
    ms.log(f"Start dhtBirdCt {now()}")

    sleepTime = 3
    samples = 3

    tempSum, humSum = 0.0, 0.0
    tempMean, humMean = 0.0, 0.0
    successful_reads = 0

    sensor = None

    try:
        sensor = DHT22_CT(gpio_pin=dhtPin)

        for s in range(samples):
            time.sleep(sleepTime)
            try:
                _timestamp, temperature, humidity = sensor.read()

                # same filtering as dhtBird3
                if (
                    not (-40 <= temperature <= 80) or
                    not (0 <= humidity <= 100) or
                    humidity == 0   # optional but practical
                ):
                    continue

                tempSum += temperature
                humSum += humidity
                successful_reads += 1

            except RuntimeError as e:
                ms.log(f"Sample {s+1} failed: {e}")

        if successful_reads > 0:
            tempMean = roundFlt(tempSum / successful_reads)
            humMean = roundFlt(humSum / successful_reads)

    except Exception as e:
        ms.log(f"Unexpected error: {e}")

    finally:
        if sensor:
            sensor.cancel()

    if successful_reads > 0:
        environment = {
            "date": now(),
            "temperature": tempMean,
            "humidity": humMean
        }

        write_env_webserv(environment.copy())
        tempProtocol(environment.copy())
        send_realtime_environment(environment.copy())

    else:
        ms.log("No valid sensor data collected; nothing uploaded.")


# -------------------------------
# Entry
# -------------------------------
if __name__ == "__main__":
    main()
    ms.log(f"End dhtBirdCt {now()}")