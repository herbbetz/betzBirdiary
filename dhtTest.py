# start the daemon with the command 'sudo pigpiod' before running this script.
# from example code at the end of pigpioBird/DHT.py
import pigpio
import pigpioBird.DHT as DHT
import time
# from sharedBird import roundFlt # shared functions in shareBird.py
# from configBird2 import dhtPin # import variables from ./configBird.py

# BCM GPIO Pins attached to sensors:
dhtPin = 16

def roundFlt(flt):
# round float down to 2 decimal
    return (round(flt, 2))

def readDHT22(sensor):
    # Get a new reading
    data = sensor.read()
    # Save our values
    temp = roundFlt(data[3])
    humidity  = roundFlt(data[4])
    return (humidity, temp)

#### main:
if __name__ == "__main__":

    pi = pigpio.pi()
    if not pi.connected:
        print('no pigpio')
        exit(0)
    # Setup the sensor
    dhtsensor = DHT.sensor(pi, dhtPin) # use the actual GPIO pin name
    # DHT22 should only be read every 3 secs
    sleepTime = 3

    while True:
        try: 
            humidity, temperature = readDHT22(dhtsensor)
            print("Humidity is: " + str(humidity) + "%")
            print("Temperature is: " + str(temperature) + "C")
            time.sleep(sleepTime)
        except KeyboardInterrupt:
            break

    dhtsensor.cancel()
    pi.stop()
