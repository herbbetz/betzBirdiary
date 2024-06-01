# upload environnement data from DHT22 sensor to birdiary platform
from datetime import datetime
import time
import json
import requests
# DHT sensor
import pigpio
import pigpioBird.DHT as DHT # ./pigpioBird/DHT.py
# own local modules:
from sharedBird import roundFlt # shared functions in shareBird.py
import msgBird as ms
from configBird import dev_mode, serverUrl, boxId, dhtPin # import variables from ./configBird.py

# these directories should exist within ./station2 and are no longer tested for by module os:
#   pigpioBird environments logs ramdisk

pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)

basedir = '/home/pi/station2/' # crontab needs absolute path

def write_env_webserv(environment_data):
    # for local webserver:
    filename = basedir + 'ramdisk/env.json'
    with open(filename, 'w') as wfile:
        json.dump(environment_data, wfile)

def write_environment(environment_data):
    # for dev_mode
    filename = basedir + 'environments/' + environment_data['date'] + '.json'
    with open(filename, 'w') as wfile:
        json.dump(environment_data, wfile)

def send_realtime_environment(envData):
    global dev_mode, serverUrl, boxId

    if dev_mode: 
        write_environment(envData)
        return

    if (envData['humidity'] == 0):
        ms.log('humid 0% ? sensor disconnect?')
        return

    try:
        r = requests.post(serverUrl + 'environment/' + boxId, json=envData, timeout=20)
        ms.log('Following environment data send: ' + str(envData)) # type(envData) -> dict
        ms.log('Corresponding environment_id: ' + r.text)
        ms.setEnvirEvt() # for web browser
    except (requests.ConnectionError, requests.Timeout) as exception:
        ms.log('failed envir upload - ' + str(exception))


def readDHT22():
    data = dhtsensor.read()
    temp = data[3]
    humidity  = data[4]
    return (temp, humidity)

#### main:
ms.init()
# Setup the sensor
dhtsensor = DHT.sensor(pi, dhtPin) # use the actual GPIO pin name
# DHT22 should only be read every 3 secs:
sleepTime = 3

samples = 3
tempSum, humSum = 0.0, 0.0
tempMean, humMean = 0.0, 0.0
for s in range(samples):
    time.sleep(sleepTime)
    temp, humid = readDHT22()
    tempSum += temp
    humSum += humid

tempMean = roundFlt(tempSum/samples) # float/integer -> float
humMean = roundFlt(humSum/samples)

environment = {}
environment["date"] = str(datetime.now())
environment["temperature"] = tempMean
environment["humidity"] = humMean

write_env_webserv(environment) # for local webserver

send_realtime_environment(environment)

# clean up:
dhtsensor.cancel()
pi.stop()