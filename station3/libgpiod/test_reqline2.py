import gpiod

chip = gpiod.Chip("/dev/gpiochip0")

# Create line settings (direction as int)
sck_settings = gpiod.line_settings.LineSettings()
sck_settings.direction = 1  # OUTPUT

dout_settings = gpiod.line_settings.LineSettings()
dout_settings.direction = 0  # INPUT

# Map lines to settings
config = {23: sck_settings, 17: dout_settings}

# Set initial output value for SCK
output_vals = {23: 0}  # LOW

# Request the lines
lines = chip.request_lines(config, consumer="HX711", output_values=output_vals)

# Read the input
vals = lines.get_values()
print("Line values:", vals)

# Toggle clock (SCK)
vals[0] = 1  # HIGH
lines.set_values(vals)
print("Toggled SCK high")

lines.release()
chip.close()