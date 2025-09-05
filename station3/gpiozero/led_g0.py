from gpiozero import LED, Button
from time import sleep

# Pin definitions
ledPin = 4
askPin = 8

try:
    # Set up the LED pin as an output
    # gpiozero's LED class automatically handles setting the pin as output
    # and provides simple methods for control.
    print('Put long wire of LED on pin ' + str(ledPin) + ' and cathode on ground pin with resistor')
    led = LED(ledPin)
    print(f"LED pin {ledPin} ready.")

    # Turn the LED on
    led.on()
    print(f"LED on pin {ledPin} is ON.")
    sleep(3)

    # Turn the LED off
    led.off()
    print(f"LED on pin {ledPin} is OFF.")

    # Set up the askPin as an input
    # gpiozero's Button class is a convenient way to represent input pins,
    # automatically handling pull-ups/downs (defaults to pull_up=False,
    # meaning no internal pull-up and a floating input if not externally pulled).
    # If you need an internal pull-up for a button, you would use Button(askPin, pull_up=True)
    ask_button = Button(askPin)
    print(f"Ask pin {askPin} ready as input.")

    # Read the status of the askPin
    # The .is_pressed property returns True if the button is pressed (input is low)
    # or False if not pressed (input is high). This assumes a common button wiring
    # where pressing connects to ground.
    # If you just want the raw digital value (high/low), you can use .value
    # which returns 1 for high and 0 for low.
    pin_status = ask_button.value # Returns 0 or 1 directly
    print(f"Pin {askPin} has status: {pin_status}")

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure you have the necessary permissions. You might need to run this script with 'sudo'.")
finally:
    # gpiozero objects automatically clean up resources when the script ends,
    # or when they go out of scope. There's no explicit 'close' method like with lgpio.
    # However, if you're writing a long-running application and want to explicitly
    # release resources for a specific pin, you can use the .close() method
    # on the individual gpiozero objects (e.g., led.close(), ask_button.close()).
    # For this simple script, it's not strictly necessary in the finally block.
    print("Script finished. GPIO resources will be released.")