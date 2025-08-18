# upload environnement data from DHT22 sensor to birdiary platform
from datetime import datetime
import time
import json
import requests
#
import lgpio as sbc
from lgpioBird.DHT22 import DHT22Sensor
# own modules:
from sharedBird import roundFlt # shared functions in shareBird.py
import msgBird as ms
from configBird3 import birdpath, serverUrl, boxId, dhtPin

def write_env_webserv(env_data):
    # for local webserver:
    filename = f"{birdpath['ramdisk']}/env.json"
    env_data["date"] = env_data["date"].split('.')[0] # remove terminal msecs part
    with open(filename, 'w') as wfile:
        json.dump(env_data, wfile)

def send_realtime_environment(envData):
    if (envData['humidity'] == 0):
        ms.log('humid=0%->sensor_disconnect?')
        return

    try:
        r = requests.post(serverUrl + 'environment/' + boxId, json=envData, timeout=20)
        ms.log('environment data send: ' + str(envData)) # type(envData) -> dict
        ms.log('Corresponding environment_id: ' + r.text)
        ms.setEnvirEvt() # for web browser
    except (requests.ConnectionError, requests.Timeout) as exception:
        ms.log('failed envir upload - ' + str(exception))

def main():
    ms.init()
    ms.log(f"Start dhtBird3 {datetime.now()}")
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
        sensor.cancel()
        sbc.gpiochip_close(chip)

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

if __name__ == "__main__":
    main()
    ms.log(f"End dhtBird3 {datetime.now()}")