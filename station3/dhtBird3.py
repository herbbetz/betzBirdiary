# upload environnement data from DHT22 sensor to birdiary platform
from datetime import datetime
import time
import json
import requests
import math
import os
#
import lgpio as sbc
from lgpioBird.DHT22 import DHT22Sensor
# own modules:
from sharedBird import roundFlt # shared functions in shareBird.py
import msgBird as ms
from configBird3 import birdpath, serverUrl, boxId, dhtPin

def now():
    return datetime.now()

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

    env_data["date"] = env_data["date"].strftime("%Y:%m:%d:%H:%M")
    env_data["humid_abs"] = humid_abs(env_data["temperature"], env_data["humidity"])

    data.append(env_data)
    if len(data) > maxdata:
        data = data[-maxdata:]

    with open(datafile, "w") as outfile:
        json.dump(data, outfile, indent=2)

def write_env_webserv(env_data):
    # for local webserver:
    filename = f"{birdpath['ramdisk']}/env.json"
    env_data["date"] = str(env_data["date"]).split('.')[0] # remove terminal msecs part
    with open(filename, 'w') as wfile:
        json.dump(env_data, wfile)

def send_realtime_environment(envData):
    envData["date"] = str(envData["date"])
    try:
        r = requests.post(serverUrl + 'environment/' + boxId, json=envData, timeout=20)
        r.raise_for_status()  # raises exception for HTTP errors
        ms.log('environment data send: ' + str(envData)) # type(envData) -> dict
        ms.log('Corresponding environment_id: ' + r.text)
        ms.setEnvirEvt() # for web browser
    except (requests.ConnectionError, requests.Timeout) as exception: # only network errors
        ms.log('failed envir upload - ' + str(exception))
    except requests.HTTPError as e: # this for HTTP errors like 404
        ms.log(f'HTTP error: {e}')


def main():
    ms.init()
    ms.log(f"Start dhtBird3 {now()}")
    chip = sbc.gpiochip_open(0)  # open gpiochip 0
    sensor = DHT22Sensor(chip=chip, gpio=dhtPin)

    sleepTime = 3
    samples = 3
    tempSum, humSum = 0.0, 0.0
    tempMean, humMean = 0.0, 0.0
    successful_reads = 0
    try:
        for s in range(samples):
            time.sleep(sleepTime)
            try:
                _timestamp, temperature, humidity = sensor.read()
                # bad reads: 
                if (
                    not (-40 <= temperature <= 80) or
                    not (0 <= humidity <= 100) or
                    humidity == 0
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
        sbc.gpiochip_close(chip)

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

if __name__ == "__main__":
    main()
    ms.log(f"End dhtBird3 {now()}")