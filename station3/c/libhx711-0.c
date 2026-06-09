/*
 * libhx711.c — Robust HX711 driver with discard, median5 and resync
 *
 * Build:
 *   gcc -std=c17 -Wall -Wextra -O2 -shared -fPIC libhx711.c -llgpio -o libhx711.so
 *
 * This library can be loaded in Python via ctypes.
 */

#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <limits.h>
#include <lgpio.h>

static int chip = -1;
static int dout_pin = -1;
static int sck_pin = -1;

/* ---------- timing ---------- */

static void sleep_us(long us)
{
    struct timespec ts;
    ts.tv_sec  = us / 1000000;
    ts.tv_nsec = (us % 1000000) * 1000;
    nanosleep(&ts, NULL);
}

static double monotonic_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

/* ---------- median-of-5 helper ---------- */
static long median5(long a, long b, long c, long d, long e)
{
    long arr[5] = {a,b,c,d,e};
    for (int i=0;i<5;i++)
        for (int j=i+1;j<5;j++)
            if (arr[j] < arr[i])
            {
                long t = arr[i];
                arr[i] = arr[j];
                arr[j] = t;
            }
    return arr[2];
}

/* ---------- HX711 low-level read ---------- */
static int wait_ready(double timeout_s)
{
    double start = monotonic_seconds();
    while (lgGpioRead(chip, dout_pin) != 0)
    {
        if (monotonic_seconds() - start > timeout_s)
            return -1;
        sleep_us(1000);
    }
    return 0;
}

static long read_raw_once(void)
{
    if (wait_ready(1.0) < 0)
        return LONG_MIN;

    long value = 0;
    for (int i=0; i<24; i++)
    {
        lgGpioWrite(chip, sck_pin, 1);
        value = (value << 1) | lgGpioRead(chip, dout_pin);
        lgGpioWrite(chip, sck_pin, 0);
    }

    for (int i=0; i<3; i++) // gain=64
    {
        lgGpioWrite(chip, sck_pin, 1);
        lgGpioWrite(chip, sck_pin, 0);
    }

    if (value & 0x800000)
        value -= 1 << 24;

    return value;
}

/* ---------- Exported API ---------- */

/* initialize GPIO and discard first readings */
int hx711_init(int data_pin, int clock_pin)
{
    dout_pin = data_pin;
    sck_pin  = clock_pin;

    chip = lgGpiochipOpen(0);
    if (chip < 0)
        return -1;

    if (lgGpioClaimInput(chip, 0, dout_pin) < 0)
        return -2;
    if (lgGpioClaimOutput(chip, 0, sck_pin, 0) < 0)
        return -3;

    // discard first 5 readings
    for (int i=0;i<20;i++)
        read_raw_once();

    return 0;
}

/* read median-of-5 to reduce spikes 
and exclude jumps > 150000 */
long hx711_read(void)
{
    static long last = 0;

    long v = median5(
        read_raw_once(),
        read_raw_once(),
        read_raw_once(),
        read_raw_once(),
        read_raw_once()
    );

    if (last && labs(v - last) > 150000) v = last;
    last = v;

    return v;
}

/* software resync if HX711 glitches */
int hx711_resync(void)
{
    if (chip >= 0)
    {
        lgGpiochipClose(chip);
        chip = -1;
    }

    if (dout_pin < 0 || sck_pin < 0)
        return -1;

    return hx711_init(dout_pin, sck_pin);
}

/* cleanup */
void hx711_close(void)
{
    if (chip >= 0)
        lgGpiochipClose(chip);
    chip = -1;
}