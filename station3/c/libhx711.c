/*
 * libhx711.c — Robust HX711 driver with fast timeout and single-read throughput.
 * Build:
 * gcc -std=c17 -Wall -Wextra -O2 -shared -fPIC libhx711.c -llgpio -o libhx711.so
 * header is /usr/include/lgpio.h
 * make -f hx_Makefile, make -f hx_Makefile debug (or both), make -f hx_Makefile clean
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <limits.h>
#include <stdint.h>
#include <lgpio.h>

/* Negative error band base: well below raw 24-bit ADC min (-8,388,608) */
#define ERR_BASE            (-10000000LL)
#define ERR_WAIT_TIMEOUT    (ERR_BASE - 1LL) /* -10000001: DOUT stayed HIGH */
#define ERR_FRAME_PREEMPT   (ERR_BASE - 2LL) /* -10000002: Frame took > 2.5ms due to OS stall */

static int chip = -1;
static int dout_pin = -1;
static int sck_pin = -1;

/* Fast sub-microsecond delay */
static inline void delay_ns(void) {
    for (volatile int i = 0; i < 20; i++) {
        __asm__ __volatile__("");
    }
}

#ifdef HX711_DEBUG
#include <stdarg.h>

static void debug_log(const char *fmt, ...) {
    struct timespec ts;
    struct tm tm;
    va_list args;

    clock_gettime(CLOCK_REALTIME, &ts);
    localtime_r(&ts.tv_sec, &tm);

    fprintf(stderr,
        "[%04d-%02d-%02d %02d:%02d:%02d.%06ld] ",
        tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
        tm.tm_hour, tm.tm_min, tm.tm_sec,
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

static double monotonic_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static int wait_ready(double timeout_s) {
    double start = monotonic_seconds();
    while (lgGpioRead(chip, dout_pin) != 0) {
        if (monotonic_seconds() - start > timeout_s) {
            DEBUG_LOG("HX711_FAIL: DOUT timeout (DOUT stuck HIGH for %.2fs)\n", timeout_s);
            return -1;
        }
        /* Sleep 100us instead of 1000us for faster responsiveness */
        struct timespec ts = {0, 100000L};
        nanosleep(&ts, NULL);
    }
    return 0;
}

static int64_t read_raw_once(void) {
    if (wait_ready(1.0) < 0) {
        return ERR_WAIT_TIMEOUT;
    }

    uint32_t raw = 0;
    struct timespec ts_start, ts_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);

    /* 24-Bit Read Loop */
    for (int i = 0; i < 24; i++) {
        lgGpioWrite(chip, sck_pin, 1);
        delay_ns();
        int bit = lgGpioRead(chip, dout_pin);
        lgGpioWrite(chip, sck_pin, 0); /* Bring clock LOW immediately */
        raw = (raw << 1) | (uint32_t)bit;
        delay_ns();
    }

    /* Gain pulses (Channel A, Gain 64) */
    for (int i = 0; i < 3; i++) {
        lgGpioWrite(chip, sck_pin, 1);
        delay_ns();
        lgGpioWrite(chip, sck_pin, 0);
        delay_ns();
    }

    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long total_frame_ns = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000L + 
                          (ts_end.tv_nsec - ts_start.tv_nsec);

    /* Expanded threshold to 2.5ms to avoid dropping valid frames during minor OS scheduling jitter */
    if (total_frame_ns > 2500000L) {
        DEBUG_LOG("HX711_FAIL: OS Preemption discard (frame time: %ld ns)\n", total_frame_ns);
        return ERR_FRAME_PREEMPT;
    }

    int32_t value = (int32_t)raw;
    if (value & 0x800000) {
        value |= 0xFF000000;
    }

    return (int64_t)value;
}

int hx711_init(int data_pin, int clock_pin) {
    dout_pin = data_pin;
    sck_pin  = clock_pin;

    chip = lgGpiochipOpen(0);
    if (chip < 0) return -1;

    if (lgGpioClaimInput(chip, 0, dout_pin) < 0) return -2;
    if (lgGpioClaimOutput(chip, 0, sck_pin, 0) < 0) return -3;

    lgGpioWrite(chip, sck_pin, 0);

    for (int i = 0; i < 5; i++) {
        read_raw_once();
    }
    return 0;
}

int64_t hx711_read(void) {
    return read_raw_once();
}

int hx711_resync(void) {
    if (chip >= 0) {
        lgGpiochipClose(chip);
        chip = -1;
    }
    if (dout_pin < 0 || sck_pin < 0) return -1;
    return hx711_init(dout_pin, sck_pin);
}

void hx711_close(void) {
    if (chip >= 0) {
        lgGpiochipClose(chip);
    }
    chip = -1;
}