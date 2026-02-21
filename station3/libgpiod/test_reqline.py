import gpiod

chip = gpiod.Chip("/dev/gpiochip0")
print(chip.__doc__)
help(chip.request_lines)
print("========dir(chip):")
dir(chip)