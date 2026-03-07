# dhtBirdCt.py
# -------------------------------
# Upload environmental data from a DHT22 sensor to the Birdiary platform
# This version uses a ctypes wrapper for the C driver libdht22.so
# Automatically retries on timeouts/checksum errors until valid readings are obtained
# -------------------------------

from datetime import datetime
import time
import json
import requests
import ctypes

# Own modules
from sharedBird import roundFlt  # shared utility function for rounding floats
import msgBird as ms              # logging and event functions
from configBird3 import birdpath, serverUrl, boxId, dhtPin  # configuration

# -------------------------------
# Class wrapper for libdht22.so
# -------------------------------
class DHT22_CT:
    """
    DHT22 sensor interface using the C driver libdht22.so via ctypes.
    Provides init, read, and cleanup methods similar to previous Python driver.
    """

    def __init__(self, gpio_pin):
        """
        Initialize the sensor library and claim the GPIO pin.
        :param gpio_pin: BCM GPIO number where DHT22 data pin is connected
        """
        self.gpio_pin = gpio_pin

        # Load the shared library from station3/c/
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
        :return: tuple(temperature, humidity)
        :raises RuntimeError: if a read attempt fails (timeout or checksum error)
        """
        temp = ctypes.c_double()
        hum  = ctypes.c_double()

        ret = self.lib.dht22_read(ctypes.byref(temp), ctypes.byref(hum))

        if ret == 0:
            # Successful read
            return temp.value, hum.value
        elif ret == -2:
            # Checksum error, transient, caller may retry
            raise RuntimeError("Checksum error during DHT22 read")
        else:
            # Timeout, transient, caller may retry
            raise RuntimeError("DHT22 read timeout")

    def cancel(self):
        """
        Cleanup the library and release resources.
        """
        self.lib.dht22_close()

# -------------------------------
# Helper functions
# -------------------------------
def write_env_webserv(env_data):
    """
    Write environment data to a local JSON file on the ramdisk.
    Removes milliseconds from timestamp for consistency.
    """
    filename = f"{birdpath['ramdisk']}/env.json"
    env_data["date"] = env_data["date"].split('.')[0]  # remove milliseconds
    with open(filename, 'w') as wfile:
        json.dump(env_data, wfile)

def send_realtime_environment(envData):
    """
    Upload environment data to Birdiary platform via REST API.
    Skips upload if humidity reading is zero (possible sensor disconnect).
    Logs success or failure.
    """
    if envData['humidity'] == 0:
        ms.log('humidity=0% -> possible sensor disconnect?')
        return

    try:
        r = requests.post(serverUrl + 'environment/' + boxId, json=envData, timeout=20)
        ms.log('Environment data sent: ' + str(envData))
        ms.log('Corresponding environment_id: ' + r.text)
        ms.setEnvirEvt()  # Notify web browser event
    except (requests.ConnectionError, requests.Timeout) as exception:
        ms.log('Failed environment upload - ' + str(exception))

# -------------------------------
# Main function
# -------------------------------
def main():
    ms.init()
    ms.log(f"Start dhtBirdCt {datetime.now()}")

    sensor = DHT22_CT(gpio_pin=dhtPin)

    sleepTime = 3      # seconds between each read (DHT22 limit ~2 sec)
    samples = 3        # number of reads to average
    tempSum, humSum = 0.0, 0.0
    successful_reads = 0

    try:
        for s in range(samples):
            while True:
                # Keep trying until a valid reading is obtained
                try:
                    temperature, humidity = sensor.read()
                    if humidity > 0:
                        # Valid reading, add to sums
                        tempSum += temperature
                        humSum  += humidity
                        successful_reads += 1
                        break
                    else:
                        ms.log("humidity=0% -> retrying...")
                except RuntimeError as e:
                    ms.log(f"Sample {s+1} read error: {e}")
                time.sleep(sleepTime)

        # Compute mean values
        tempMean = roundFlt(tempSum / successful_reads) if successful_reads else 0.0
        humMean  = roundFlt(humSum  / successful_reads) if successful_reads else 0.0

    except Exception as e:
        ms.log(f"Unexpected error during sampling: {e}")

    finally:
        # Cleanup sensor resources
        sensor.cancel()

    # If we got valid data, upload and save locally
    if successful_reads > 0:
        environment = {
            "date": str(datetime.now()),
            "temperature": tempMean,
            "humidity": humMean
        }
        write_env_webserv(environment)
        send_realtime_environment(environment)
    else:
        ms.log("No valid sensor data collected; nothing uploaded.")

# -------------------------------
# Entry point
# -------------------------------
if __name__ == "__main__":
    main()
    ms.log(f"End dhtBirdCt {datetime.now()}")