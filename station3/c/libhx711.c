/*
 * libhx711.c — Robust HX711 driver with fast timeout and single-read throughput.
 * similar to https://github.com/endail/hx711/blob/master/src/HX711.cpp
 * Build:
 * gcc -std=c17 -Wall -Wextra -O2 -shared -fPIC libhx711.c -llgpio -o libhx711.so
 * header is /usr/include/lgpio.h
 * make -f hx_Makefile, make -f hx_Makefile debug, make -f hx_Makefile clean
 * This library can be loaded in Python via ctypes.
 */

#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <limits.h>
#include <stdint.h>
#include <lgpio.h>

#ifdef HX711_DEBUG
#include <stdarg.h>

static long debug_last_value = LONG_MIN;
static uint32_t debug_last_raw = 0;
static unsigned long debug_sample_count = 0;

static void debug_log(const char *fmt, ...)
{
    struct timespec ts;
    struct tm tm;
    va_list args;

    clock_gettime(CLOCK_REALTIME, &ts);
    localtime_r(&ts.tv_sec, &tm);

    fprintf(stderr,
        "[%04d-%02d-%02d %02d:%02d:%02d.%06ld] ",
        tm.tm_year + 1900,
        tm.tm_mon + 1,
        tm.tm_mday,
        tm.tm_hour,
        tm.tm_min,
        tm.tm_sec,
        ts.tv_nsec / 1000);

    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fflush(stderr);
}

#define DEBUG_LOG(...) debug_log(__VA_ARGS__)
#else
#define DEBUG_LOG(...)
#endif

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

    uint32_t raw = 0;

#ifdef HX711_DEBUG
    char bits[25];
#endif

    for (int i = 0; i < 24; i++)
    {
        struct timespec t0, t1;

        clock_gettime(CLOCK_MONOTONIC, &t0);

        /*
         * Robertson style:
         * clock HIGH
         * wait for DOUT settling
         * clock LOW
         * read bit
         */

        lgGpioWrite(chip, sck_pin, 1);

        /*
         * HX711 timing:
         * T3 minimum clock high time = 0.2us
         *
         * Give lgpio and Linux plenty of margin.
         */
        sleep_us(1);

        lgGpioWrite(chip, sck_pin, 0);

        clock_gettime(CLOCK_MONOTONIC, &t1);

        long pulse_us =
            (t1.tv_sec - t0.tv_sec) * 1000000L +
            (t1.tv_nsec - t0.tv_nsec) / 1000L;

        /*
         * HX711 enters power-down if SCK stays HIGH > 60us.
         */
        if (pulse_us >= 60)
        {
            DEBUG_LOG("HX711 timing violation: %ld us\n",
                      pulse_us);
            return LONG_MIN;
        }

        /*
         * Robertson reads after falling edge.
         */
        sleep_us(1);

        int bit = lgGpioRead(chip, dout_pin);

#ifdef HX711_DEBUG
        bits[i] = bit ? '1' : '0';
#endif

        raw = (raw << 1) | (uint32_t)bit;

        /*
         * Robertson T4 minimum.
         */
        sleep_us(1);
    }

#ifdef HX711_DEBUG
    bits[24] = '\0';
#endif


    /*
     * Channel A, gain 128:
     * total pulses = 25
     * already sent 24,
     * send one extra pulse.
     */
    lgGpioWrite(chip, sck_pin, 1);
    sleep_us(1);
    lgGpioWrite(chip, sck_pin, 0);


    long value = raw;

    if (value & 0x800000)
        value |= ~0xFFFFFF;


#ifdef HX711_DEBUG

    debug_sample_count++;

    if (debug_last_value != LONG_MIN)
    {
        long delta = value - debug_last_value;

        if (labs(delta) > 2000)
        {
            DEBUG_LOG(
                "RAW_JUMP "
                "n=%lu "
                "bits=%s "
                "prev=%ld(0x%06X) "
                "curr=%ld(0x%06X) "
                "delta=%+ld\n",

                debug_sample_count,

                bits,

                debug_last_value,
                debug_last_raw,

                value,
                raw,

                delta
            );
        }
    }

    debug_last_value = value;
    debug_last_raw = raw;

#endif

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

    // Fast-discard startup readings to stabilize the internal capacitor
    for (int i=0; i<20; i++)
    {
        if (read_raw_once() == LONG_MIN)
            return -4;
    }

    return 0;
}

/* Clean, optimized, but lightning-fast single-read driver */
long hx711_read(void)
{
    // Aborts in 1 second if disconnected, otherwise returns instantly
    return read_raw_once(); 
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