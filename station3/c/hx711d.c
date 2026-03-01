/*
 * hx711d.c — HX711 daemon using lgpio (gain = 64)
 * ------------------------------------------------
 * - Reads HX711 continuously
 * - Uses CLOCK_MONOTONIC for timeout
 * - Writes raw values to FIFO
 * - Handles missing reader gracefully
 * - PID file support
 *
 * Build:
 *   gcc -std=c17 -Wall -Wextra -O2 hx711d.c -llgpio -o hx711d
 *
 * Usage:
 *   ./hx711d DATA_PIN SCK_PIN
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <time.h>
#include <lgpio.h>

#define FIFO_PATH "/home/pi/station3/ramdisk/hxfifo"
#define PID_FILE  "/home/pi/station3/ramdisk/hx711d.pid"

static volatile int keep_running = 1;

/* ---------- timing helpers ---------- */

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

/* ---------- signal handling ---------- */

static void handle_signal(int sig)
{
    (void)sig;
    keep_running = 0;
}

/* ---------- PID file ---------- */

static void write_pid(void)
{
    FILE *f = fopen(PID_FILE, "w");
    if (f) {
        fprintf(f, "%d\n", getpid());
        fclose(f);
    } else {
        perror("write_pid");
    }
}

static void remove_pid(void)
{
    unlink(PID_FILE);
}

/* ---------- HX711 helpers ---------- */

static int wait_ready(int chip, int dout, double timeout_s)
{
    double start = monotonic_seconds();

    while (keep_running && lgGpioRead(chip, dout) != 0) {
        if (monotonic_seconds() - start > timeout_s)
            return -1;
        sleep_us(1000);
    }
    return 0;
}

/* gain = 64 (channel A) → 3 extra pulses */
static long read_hx711(int chip, int dout, int sck)
{
    if (wait_ready(chip, dout, 1.0) < 0)
        return 0;  /* timeout */

    long value = 0;

    for (int i = 0; i < 24; i++) {
        lgGpioWrite(chip, sck, 1);
        value = (value << 1) | lgGpioRead(chip, dout);
        lgGpioWrite(chip, sck, 0);
    }

    for (int i = 0; i < 3; i++) {
        lgGpioWrite(chip, sck, 1);
        lgGpioWrite(chip, sck, 0);
    }

    /* sign extend 24-bit */
    if (value & 0x800000)
        value -= 1 << 24;

    return value;
}

/* ---------- main ---------- */

int main(int argc, char *argv[])
{
    if (argc != 3) {
        fprintf(stderr, "Usage: %s DATA_PIN SCK_PIN\n", argv[0]);
        return EXIT_FAILURE;
    }

    int dout_pin = atoi(argv[1]);
    int sck_pin  = atoi(argv[2]);

    signal(SIGINT,  handle_signal);
    signal(SIGTERM, handle_signal);

    write_pid();

    int chip = lgGpiochipOpen(0);
    if (chip < 0) {
        perror("lgGpiochipOpen");
        remove_pid();
        return EXIT_FAILURE;
    }

    if (lgGpioClaimInput(chip, 0, dout_pin) < 0 ||
        lgGpioClaimOutput(chip, 0, sck_pin, 0) < 0) {
        perror("lgGpioClaim");
        lgGpiochipClose(chip);
        remove_pid();
        return EXIT_FAILURE;
    }

    /* ensure FIFO exists */
    if (mkfifo(FIFO_PATH, 0666) < 0 && errno != EEXIST) {
        perror("mkfifo");
        lgGpiochipClose(chip);
        remove_pid();
        return EXIT_FAILURE;
    }

    while (keep_running) {
        long raw = read_hx711(chip, dout_pin, sck_pin);

        int fd = open(FIFO_PATH, O_WRONLY | O_NONBLOCK);
        if (fd < 0) {
            if (errno == ENXIO) {
                fprintf(stderr, "No FIFO reader — retrying in 1s\n");
                sleep(1);
                continue;
            } else {
                perror("open FIFO");
                break;
            }
        }

        char buf[32];
        int len = snprintf(buf, sizeof(buf), "%ld\n", raw);
        write(fd, buf, len);
        close(fd);

        sleep_us(50000); /* ~20 Hz */
    }

    lgGpiochipClose(chip);
    remove_pid();
    return EXIT_SUCCESS;
}