# dhtBirdCt.py
# -------------------------------
# Upload environmental data from a DHT22 sensor to the Birdiary platform
# Uses ctypes wrapper for the stable polling C driver libdht22.so
# Automatically retries on timeouts/checksum errors until valid readings are obtained
# -------------------------------

from datetime import datetime
import time
import json
import requests
import ctypes
import os
import math

# Own modules
from sharedBird import roundFlt        # utility function for rounding floats
import msgBird as ms                    # logging and event functions
from configBird3 import birdpath, serverUrl, boxId, dhtPin  # configuration

# -------------------------------
# Class wrapper for libdht22.so
# -------------------------------
class DHT22_CT:
    """
    DHT22 sensor interface using the C polling driver libdht22.so via ctypes.
    Provides init, read, and cleanup methods similar to previous Python driver.
    """

    def __init__(self, gpio_pin):
        """
        Initialize the sensor library and claim the GPIO pin.
        :param gpio_pin: BCM GPIO number where DHT22 data pin is connected
        """
        self.gpio_pin = gpio_pin
        libpath = f"{birdpath['appdir']}/c/libdht22.so"
        self.lib = ctypes.CDLL(libpath)

        # Define argument and return types for library functions
        self.lib.dht22_init.argtypes = [ctypes.c_int]
        self.lib.dht22_init.restype = ctypes.c_int

        self.lib.dht22_read.argtypes = [ctypes.POINTER(ctypes.c_double),
                                        ctypes.POINTER(ctypes.c_double)]
        self.lib.dht22_read.restype = ctypes.c_int

        self.lib.dht22_close.restype = None

        # Initialize the sensor
        if self.lib.dht22_init(self.gpio_pin) != 0:
            raise RuntimeError(f"DHT22 initialization failed on GPIO {self.gpio_pin}")

    def read(self):
        """
        Perform a single reading from the DHT22 sensor.
        Retries internally until a valid reading is obtained.
        :return: tuple(timestamp, temperature, humidity)
        :raises RuntimeError: if a read attempt fails (timeout or checksum error)
        """
        temp = ctypes.c_double()
        hum  = ctypes.c_double()
        ret = self.lib.dht22_read(ctypes.byref(temp), ctypes.byref(hum))

        if ret == 0:
            # Successful read, capture timestamp
            ts = time.time()
            return ts, temp.value, hum.value
        elif ret == -2:
            # Checksum error
            raise RuntimeError("Checksum error during DHT22 read")
        else:
            # Timeout
            raise RuntimeError("DHT22 read timeout")

    def cancel(self):
        """
        Cleanup the library and release resources.
        """
        self.lib.dht22_close()

# -------------------------------
# Helper functions
# -------------------------------
def humid_abs(temperature, humidity_rel):
    """
    Calculate absolute humidity (g/m³) from temperature (°C) and relative humidity (%).
    AH = 6.112 * e^(17.67*T/(T+243.5)) * RH * 2.1674 / (273.15 + T)
    """
    if temperature < -40 or temperature > 80:  # DHT22 operating range
        return 0.0
    if humidity_rel < 0 or humidity_rel > 100:
        return 0.0

    svp = 6.112 * math.exp(17.67 * temperature / (temperature + 243.5))
    ah = svp * humidity_rel * 2.1674 / (273.15 + temperature)
    return roundFlt(ah)

def tempProtocol(env_data):
    """
    Append environment data to local tempdata.json (limited to maxdata entries).
    """
    datafile = f"{birdpath['appdir']}/tempdata/tempdata.json"
    data = []
    maxdata = 160
    if os.path.exists(datafile):
        with open(datafile, "r") as infile:
            try:
                data = json.load(infile)
            except json.JSONDecodeError:
                ms.log(f"Error decoding JSON from {datafile}")

    env_data["date"] = datetime.fromtimestamp(env_data["timestamp"]).strftime("%Y:%m:%d:%H:%M")
    env_data["humid_abs"] = humid_abs(env_data["temperature"], env_data["humidity"])

    data.append(env_data)
    if len(data) > maxdata:
        data = data[-maxdata:]

    with open(datafile, "w") as outfile:
        json.dump(data, outfile, indent=2)

def write_env_webserv(env_data):
    """
    Write environment data to a local JSON file on the ramdisk.
    """
    filename = f"{birdpath['ramdisk']}/env.json"
    env_data["date"] = str(datetime.fromtimestamp(env_data["timestamp"]))  # convert to human-readable
    with open(filename, 'w') as wfile:
        json.dump(env_data, wfile)

def send_realtime_environment(envData):
    """
    Upload environment data to Birdiary platform via REST API.
    Skips upload if humidity reading is zero.
    """
    if envData['humidity'] == 0:
        ms.log('humidity=0% -> possible sensor disconnect?')
        return

    envData['date'] = str(datetime.fromtimestamp(envData['timestamp']))
    try:
        r = requests.post(serverUrl + 'environment/' + boxId, json=envData, timeout=20)
        ms.log('Environment data sent: ' + str(envData))
        ms.log('Corresponding environment_id: ' + r.text)
        ms.setEnvirEvt()  # notify web browser event
    except (requests.ConnectionError, requests.Timeout) as exception:
        ms.log('Failed environment upload - ' + str(exception))

# -------------------------------
# Main function
# -------------------------------
def main():
    ms.init()
    ms.log(f"Start dhtBirdCt {datetime.now()}")

    sleepTime = 3      # seconds between reads (DHT22 limit ~2 s)
    samples = 3        # number of reads to average
    tempSum, humSum = 0.0, 0.0
    successful_reads = 0
    max_retries = 10
    sensor = None

    try:
        sensor = DHT22_CT(gpio_pin=dhtPin)

        for s in range(samples):
            reads = 0
            while reads < max_retries:
                reads += 1
                try:
                    ts, temperature, humidity = sensor.read()
                    if humidity > 0:
                        tempSum += temperature
                        humSum  += humidity
                        successful_reads += 1
                        break
                    else:
                        ms.log("humidity=0% -> retrying...")
                except RuntimeError as e:
                    ms.log(f"Sample {s+1} read error: {e}")
                time.sleep(sleepTime)
            if reads == max_retries:
                ms.log(f"Sample {s+1} failed after {max_retries} attempts")

        tempMean = roundFlt(tempSum / successful_reads) if successful_reads else 0.0
        humMean  = roundFlt(humSum  / successful_reads) if successful_reads else 0.0

    except Exception as e:
        ms.log(f"Unexpected error during sampling: {e}")

    finally:
        if sensor:
            sensor.cancel()

    if successful_reads > 0:
        environment = {
            "timestamp": time.time(),
            "temperature": tempMean,
            "humidity": humMean
        }
        write_env_webserv(environment.copy())
        tempProtocol(environment.copy())
        send_realtime_environment(environment.copy())
    else:
        ms.log("No valid sensor data collected; nothing uploaded.")

# -------------------------------
# Entry point
# -------------------------------
if __name__ == "__main__":
    main()
    ms.log(f"End dhtBirdCt {datetime.now()}")