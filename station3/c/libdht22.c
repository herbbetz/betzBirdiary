/*
 * libdht22.c  —  DHT22 driver for Raspberry Pi using lgpio
 * polling version, lgpio to old for interrupt edge detection
 * Build:
 * gcc -std=c17 -O2 -Wall -shared -fPIC libdht22.c -llgpio -o libdht22.so
 */

#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>      // for nanosleep
#include <lgpio.h>

static int chip = -1;
static int pin  = -1;

// ---------- timing helpers ----------
static inline long micros()
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec*1000000L + ts.tv_nsec/1000;
}

static int wait_level(int level, int timeout_us)
{
    long start = micros();
    while (lgGpioRead(chip, pin) != level)
    {
        if ((micros() - start) > timeout_us)
            return -1;
    }
    return 0;
}

static int measure_high()
{
    long start = micros();
    while (lgGpioRead(chip, pin) == 1)
    {
        if ((micros() - start) > 200) // 200 us max
            break;
    }
    return micros() - start;
}

// ---------- public API ----------
int dht22_init(int gpio)
{
    pin = gpio;
    chip = lgGpiochipOpen(0);
    if (chip < 0) return -1;
    return 0;
}

int dht22_read(double *temperature, double *humidity)
{
    uint8_t data[5] = {0};

    // start signal
    lgGpioClaimOutput(chip, 0, pin, 0);
    lgGpioWrite(chip, pin, 0);
    struct timespec ts = {0, 2000*1000}; // 2 ms
    nanosleep(&ts, NULL);

    lgGpioWrite(chip, pin, 1);
    lgGpioClaimInput(chip, 0, pin);

    // sensor response
    if (wait_level(0, 100) < 0) return -1;
    if (wait_level(1, 100) < 0) return -1;
    if (wait_level(0, 100) < 0) return -1;

    // read 40 bits
    for (int i = 0; i < 40; i++)
    {
        if (wait_level(1, 100) < 0) return -1;
        int width = measure_high();
        if (width > 50)
            data[i/8] |= (1 << (7 - (i % 8)));
        if (wait_level(0, 100) < 0) return -1;
    }

    // checksum
    uint8_t sum = data[0] + data[1] + data[2] + data[3];
    if ((sum & 0xFF) != data[4])
        return -2;

    int rh = (data[0] << 8) | data[1];
    int rt = (data[2] << 8) | data[3];

    *humidity = rh / 10.0;
    if (rt & 0x8000)
    {
        rt &= 0x7FFF;
        *temperature = -(rt / 10.0);
    }
    else
    {
        *temperature = rt / 10.0;
    }

    return 0;
}

void dht22_close(void)
{
    if (chip >= 0)
        lgGpiochipClose(chip);
    chip = -1;
}