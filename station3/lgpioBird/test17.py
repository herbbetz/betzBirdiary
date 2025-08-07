import lgpio, time

chip = lgpio.gpiochip_open(0)
TEST_PIN = 17

# Correct way to claim the pin as input with pull-up
lgpio.gpio_claim_input(chip, TEST_PIN, lgpio.SET_PULL_UP)

try:
    while True:
        print(lgpio.gpio_read(chip, TEST_PIN))
        time.sleep(0.2)
except KeyboardInterrupt:
    pass
finally:
    lgpio.gpiochip_close(chip)