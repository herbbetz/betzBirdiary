import time
import lgpio # Import the lgpio library

# Define the GPIO chip (usually 0 for /dev/gpiochip0)
# This is equivalent to pigpio.pi(), establishing a connection to the GPIO chip.
GPIO_CHIP = 0

# Pin definitions
ledPin = 4
askPin = 8

# Variable to hold the GPIO chip handle
h = -1 # Initialize with an invalid handle

try:
    # Open the GPIO chip
    # This obtains a handle to the GPIO chip, similar to pi = pigpio.pi()
    # Corrected: Changed 'chip_open' to 'gpiochip_open'
    h = lgpio.gpiochip_open(GPIO_CHIP)
    print(f"Successfully opened GPIO chip {GPIO_CHIP}")

    # Set up the LED pin as an output
    # lgpio.gpio_claim_output(handle, gpio_pin) claims the pin for output
    print('Put long wire of LED on pin ' + str(ledPin) + ' and cathode on ground pin with resistor')
    lgpio.gpio_claim_output(h, ledPin)
    print(f"LED pin {ledPin} set as output.")

    # Turn the LED on (write 1 to the pin)
    lgpio.gpio_write(h, ledPin, 1)
    print(f"LED on pin {ledPin} is ON.")
    time.sleep(3)

    # Turn the LED off (write 0 to the pin)
    lgpio.gpio_write(h, ledPin, 0)
    print(f"LED on pin {ledPin} is OFF.")

    # Set up the askPin as an input
    # lgpio.gpio_claim_input(handle, gpio_pin) claims the pin for input
    lgpio.gpio_claim_input(h, askPin)
    print(f"Ask pin {askPin} set as input.")

    # Read the status of the askPin
    # lgpio.gpio_read(handle, gpio_pin) reads the current value of the pin
    pin_status = lgpio.gpio_read(h, askPin)
    print(f"Pin {askPin} has status: {pin_status}")

# Corrected: Removed specific lgpio.LGPError as it might not be directly exposed.
# Standard exceptions like OSError might be raised by lgpio functions on failure.
except Exception as e:
    # Catch any errors, including those from lgpio operations (e.g., OSError)
    print(f"An error occurred: {e}")
    print("Please ensure you have the necessary permissions. You might need to run this script with 'sudo'.")
finally:
    # Always close the GPIO chip when done to release resources
    # This is crucial for proper cleanup, similar to pi.stop() in pigpio
    if h != -1:
        lgpio.gpiochip_close(h) # Corrected: Changed 'chip_close' to 'gpiochip_close'
        print(f"GPIO chip {GPIO_CHIP} closed.")
