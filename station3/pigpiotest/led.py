# https://www.elektronik-kompendium.de/sites/raspberry-pi/2611171.htm
import time
import pigpio
pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)

ledPin = 4
print('put long wire of LED on pin ' + str(ledPin) + ' and kathode on ground pin with resistor')

pi.set_mode(ledPin, pigpio.OUTPUT)
pi.write(ledPin, 1)
time.sleep(3)
pi.write(ledPin, 0)
askPin = 8
pi.set_mode(askPin, pigpio.INPUT)
print ("pin " + str(askPin) + " has status " + str(pi.read(askPin)))