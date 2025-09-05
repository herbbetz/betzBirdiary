# https://abyz.me.uk/rpi/pigpio/python.html#set_mode
# http://abyz.me.uk/rpi/pigpio/python.html#callback
import time
import pigpio
pi = pigpio.pi()
if not pi.connected:
    print('no pigpio')
    exit(0)

btnPin = 22
print('connect hardware btn/resistor to pin ' + str(btnPin) + ' and +3.3V')
pi.set_mode(btnPin, pigpio.INPUT)
pi.set_pull_up_down(btnPin, pigpio.PUD_DOWN)

debounce, debounceLim = 0, 10 # 3 units of sleepTime
sleepTime = 0.1
while True:
    try: 
        time.sleep(sleepTime)
        pressed = pi.read(btnPin) # not use together with pi.callback() !
        print(pressed)
        if (pressed):
            if (debounce == 0):
                print('***********debounced action')
                debounce = debounceLim
        else:
            if (debounce > 0): debounce -= 1
    except KeyboardInterrupt:
        break

pi.stop()