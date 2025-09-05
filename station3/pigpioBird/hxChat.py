import pigpio
import time

# Initialize pigpio
pi = pigpio.pi()

# HX711 data pin
data_pin = 22
# HX711 clock pin
clock_pin = 27

# Set up the data pin as an input and clock pin as an input
pi.set_mode(data_pin, pigpio.INPUT)
pi.set_mode(clock_pin, pigpio.INPUT)

# Read data from HX711
def read_hx711():
    # Initialize moving average parameters
    num_samples = 10
    samples = [0] * num_samples
    index = 0
    average = 0
    tare_value = 0  # Initial tare value
    
    # Tare function
    def tare():
        nonlocal tare_value
        tare_value = average  # Set tare value to current average
    
    while True:
        # Pulse the clock pin to request data
        pi.write(clock_pin, pigpio.LOW)
        time.sleep(0.001)  # Wait 1 ms
        pi.write(clock_pin, pigpio.HIGH)
        time.sleep(0.001)  # Wait 1 ms
        
        # Wait for the data pin to go low
        while pi.read(data_pin):
            pass
        
        # Read 24 bits of data
        count = 0
        for i in range(24):
            pi.write(clock_pin, pigpio.LOW)
            time.sleep(0.001)  # Wait 1 ms
            count = (count << 1) | pi.read(data_pin)
            pi.write(clock_pin, pigpio.HIGH)
            time.sleep(0.001)  # Wait 1 ms
        
        # Convert two's complement to signed integer
        if count & 0x800000:
            count |= ~0xffffff
        
        # Update moving average
        samples[index] = count
        index = (index + 1) % num_samples
        average = sum(samples) / num_samples
        
        # Output the result
        print("Weight:", average - tare_value)  # Output net weight
        time.sleep(0.1)  # Adjust as needed for desired sampling rate

try:
    read_hx711()
except KeyboardInterrupt:
    pi.stop()
