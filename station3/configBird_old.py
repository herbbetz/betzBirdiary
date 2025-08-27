'''
serverUrl = "https://wiediversistmeingarten.org/api/"
boxId = "87bab185-7630-461c-85e6-c04cf5bab180"
upmaxcnt = 10 # max. videos in direct upload
# picamera2:
videodurate = 10 # without CircularOutput
hflip_val, vflip_val =  1, 1
vidsize = (1280, 960)
losize = (320, 240)
# balance:
weightlimit = 300 # plausible weight, artificially around 45 in case of strain gauge disconnect
weightThreshold = 5 # weight which is the threshold to recognize a movement 
# hxOffset =  -75498 # minus of weight reading when balance is empty
# hang 100 g waterbottle on balance and get the factor weight_increase/100 => hxScale means reading units per gram :
hxScale = 546
hxOffset = -168307
# BCM GPIO Pins attached to sensors:
dhtPin = 16
hxDataPin, hxClckPin = 17, 23
'''
import json
import os
# from configBird3 import * works in all *.py scripts, because configBird3.py is not only read, but also executed on import !
# 'import msgBird as ms' is an error: circular import as msgBird.py also imports configBird3.py

# Path to config.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

# Load config.json safely
try:
    with open(CONFIG_PATH) as f:
        _config = json.load(f)
except FileNotFoundError:
    raise RuntimeError(f"Config file not found: {CONFIG_PATH}")
except json.JSONDecodeError as e:
    raise RuntimeError(f"Invalid config.json: {e}")

# Validate and assign required keys
try:
    serverUrl        = _config['serverUrl']
    boxId            = _config['boxId']
    upmaxcnt         = _config['upmaxcnt']
    videodurate      = _config['videodurate']
    hflip_val        = _config['hflip_val']
    vflip_val        = _config['vflip_val']
    vidsize          = tuple(_config['vidsize']) # Convert json array to tuple
    losize           = tuple(_config['losize'])
    luxThreshold     = _config['luxThreshold']
    luxLimit         = _config['luxLimit']
    weightlimit      = _config['weightlimit']
    weightThreshold  = _config['weightThreshold']
    hxScale          = _config['hxScale']
    hxOffset         = _config['hxOffset']
    dhtPin           = _config['dhtPin']
    hxDataPin        = _config['hxDataPin']
    hxClckPin        = _config['hxClckPin']
    mdroid_key       = _config['mdroid_key']
    wapp_key         = _config['wapp_key']
    wapp_phone       = _config['wapp_phone']
    tasmota_ip       = _config['tasmota_ip']
except KeyError as e:
    # ms.log(f"Missing config key: {e}")
    raise RuntimeError(f"Missing key in config.json: {e}")

#
appdir = "/home/pi/station3"
birdpath = {
    'appdir': appdir,
    'ramdisk': f"{appdir}/ramdisk",
    'fifo': f"{appdir}/ramdisk/birdpipe"
}