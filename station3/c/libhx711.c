/* for ctype python binding 
gcc -std=c17 -Wall -Wextra -O2 -shared -fPIC libhx711.c -llgpio -o libhx711.so
*/
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <lgpio.h>

static int chip = -1;
static int dout_pin = -1;
static int sck_pin = -1;

/* ---------- timing ---------- */

static double monotonic_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void sleep_us(long us)
{
    struct timespec ts;
    ts.tv_sec  = us / 1000000;
    ts.tv_nsec = (us % 1000000) * 1000;
    nanosleep(&ts, NULL);
}

/* ---------- wait until HX711 ready ---------- */

static int wait_ready(double timeout_s)
{
    double start = monotonic_seconds();

    while (lgGpioRead(chip, dout_pin) != 0) {
        if (monotonic_seconds() - start > timeout_s)
            return -1;
        sleep_us(1000);
    }
    return 0;
}

/* ---------- read one sample (gain=64) ---------- */

static long read_raw(void)
{
    if (wait_ready(1.0) < 0)
        return 0;

    long value = 0;

    for (int i = 0; i < 24; i++) {
        lgGpioWrite(chip, sck_pin, 1);
        value = (value << 1) | lgGpioRead(chip, dout_pin);
        lgGpioWrite(chip, sck_pin, 0);
    }

    /* gain=64 → 3 pulses */
    for (int i = 0; i < 3; i++) {
        lgGpioWrite(chip, sck_pin, 1);
        lgGpioWrite(chip, sck_pin, 0);
    }

    if (value & 0x800000)
        value -= 1 << 24;

    return value;
}

/* ========================================================= */
/* ============== EXPORTED FUNCTIONS ======================= */
/* ========================================================= */

/* must be called once before reading */
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

    return 0;
}

/* read one raw value */
long hx711_read(void)
{
    if (chip < 0)
        return 0;

    return read_raw();
}

/* cleanup */
void hx711_close(void)
{
    if (chip >= 0)
        lgGpiochipClose(chip);

    chip = -1;
}