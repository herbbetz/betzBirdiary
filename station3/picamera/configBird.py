dev_mode = False
serverUrl = "https://wiediversistmeingarten.org/api/"
boxId = "87bab185-7630-461c-85e6-c04cf5bab180"
# picamera1:
camera_rotation = 180
vidsize = (1280, 960)
losize = (320, 240)
# balance:
weightThreshold = 5 # weight which is the threshold to recognize a movement 
# hxOffset =  -75498 # minus of weight reading when balance is empty
# hang 100 g waterbottle on balance and get the factor weight_increase/100 => hxScale means reading units per gram :
hxScale = 788 # for CH_A_GAIN_64,  1580 for CH_A_GAIN_128
# BCM GPIO Pins attached to sensors:
dhtPin = 16
hxDataPin, hxClckPin = 17, 23

# calibrate hxOffset on startup
offsetFname = 'hxOffset.txt' # written by calibHxOffset.py on startup
def _readHxOffset():
    with open(offsetFname, 'r') as ofile:
        read = ofile.read()
    return float(read)

import os
if os.path.exists(offsetFname):
    hxOffset = round(_readHxOffset())
