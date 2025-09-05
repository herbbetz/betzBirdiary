# https://abyz.me.uk/rpi/pigpio/python.html#set_mode
# http://abyz.me.uk/rpi/pigpio/python.html#callback
import time
import pigpio
pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)

def cbf(gpio, level, tick):
    global debounce, debounceLim 
    print(gpio, level, tick)
    print('event triggered')
    if (debounce == 0):
        print('**********************debounced action')
        debounce = debounceLim

btnPin = 22
print('connect hardware btn/resistor to pin ' + str(btnPin) + ' and +3.3V')
pi.set_mode(btnPin, pigpio.INPUT)
pi.set_pull_up_down(btnPin, pigpio.PUD_DOWN)

cb1 = pi.callback(btnPin, pigpio.EITHER_EDGE, cbf)

debounce, debounceLim = 0, 3 # 3 units of sleepTime
sleepTime = 1
while True:
    try: 
        time.sleep(sleepTime)
        if (debounce > 0):
            debounce -= 1
        # print(pi.read(btnPin)) # not use together with pi.callback() !
        print('tally: ' + str(cb1.tally())) # tally always 0?
    except KeyboardInterrupt:
        break

pi.stop()