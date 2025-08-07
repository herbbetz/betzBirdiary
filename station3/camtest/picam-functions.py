from picamera2 import Picamera2

picam2 = Picamera2()

# List all methods and attributes
print(dir(picam2))

# Or get detailed info on one method
help(picam2.start_encoder)
