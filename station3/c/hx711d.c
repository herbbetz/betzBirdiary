/*
 * hx711d.c - HX711 daemon for Raspberry Pi using lgpio C API
 *
 * Reads the HX711 in a loop and writes raw values to FIFO.
 * Handles missing FIFO readers gracefully.
 * Writes PID to /home/pi/station3/ramdisk/hx711d.pid
 *
 * Usage:
 *   ./hx711d 17 23
 *   where 17 = DOUT pin, 23 = SCK pin
 */

/*
 * hx711d.c — HX711 daemon for Raspberry Pi using lgpio C API
 * ----------------------------------------------------------
 * - Continuously reads HX711 (gain=64)
 * - Writes raw float values to /home/pi/station3/ramdisk/hxfifo
 * - If no reader, prints warning and retries every 1 second
 * - Handles PID file: /home/pi/station3/ramdisk/hx711d.pid
 * - Cleans up on exit
 *
 * Usage: ./hx711d DATA_PIN SCK_PIN
 */

/*
 * hx711d.c — HX711 daemon using lgpio C API
 * -----------------------------------------
 * - Reads HX711 (gain=64) via lgpio
 * - Writes raw values to /home/pi/station3/ramdisk/hxfifo
 * - PID file: /home/pi/station3/ramdisk/hx711d.pid
 * - If no reader, waits 1 s and retries
 * - Usage: ./hx711d DATA_PIN SCK_PIN
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <lgpio.h>

#define FIFO_PATH "/home/pi/station3/ramdisk/hxfifo"
#define PID_FILE  "/home/pi/station3/ramdisk/hx711d.pid"

volatile int keep_running = 1;

void handle_signal(int sig) {
    keep_running = 0;
}

void write_pid() {
    FILE *f = fopen(PID_FILE, "w");
    if (f) {
        fprintf(f, "%d\n", getpid());
        fclose(f);
    }
}

void remove_pid() {
    unlink(PID_FILE);
}

// Wait until DATA goes low or timeout (seconds)
int wait_ready(int chip, int dout, float timeout_s) {
    float start = time(NULL);
    while (keep_running && lgGpioRead(chip, dout) != 0) {
        if (time(NULL) - start > timeout_s) return -1;
        usleep(1000); // 1 ms
    }
    return 0;
}

// Read one 24-bit HX711 value (gain=64)
long read_hx711(int chip, int dout, int sck) {
    if (wait_ready(chip, dout, 1.0) < 0) {
        return 0; // timeout
    }

    long value = 0;
    for (int i = 0; i < 24; i++) {
        lgGpioWrite(chip, sck, 1);
        value = (value << 1) | lgGpioRead(chip, dout);
        lgGpioWrite(chip, sck, 0);
    }

    // 3 extra pulses for gain=64
    for (int i = 0; i < 3; i++) {
        lgGpioWrite(chip, sck, 1);
        lgGpioWrite(chip, sck, 0);
    }

    if (value & 0x800000) value -= 1 << 24;

    return value;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s DATA_PIN SCK_PIN\n", argv[0]);
        return 1;
    }

    int dout_pin = atoi(argv[1]);
    int sck_pin  = atoi(argv[2]);

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    write_pid();

    int chip_fd = lgGpiochipOpen(0);
    if (chip_fd < 0) {
        perror("lgGpiochipOpen");
        remove_pid();
        return 1;
    }

    if (lgGpioClaimInput(chip_fd, 0, dout_pin) < 0 ||
        lgGpioClaimOutput(chip_fd, 0, sck_pin, 0) < 0) {
        perror("lgGpioClaim");
        lgGpiochipClose(chip_fd);
        remove_pid();
        return 1;
    }

    while (keep_running) {
        long raw = read_hx711(chip_fd, dout_pin, sck_pin);

        int fd = open(FIFO_PATH, O_WRONLY | O_NONBLOCK);
        if (fd < 0) {
            if (errno == ENXIO) {
                fprintf(stderr, "No reader on %s, retrying in 1s...\n", FIFO_PATH);
                sleep(1);
                continue;
            } else {
                perror("open fifo");
                break;
            }
        }

        char buf[32];
        snprintf(buf, sizeof(buf), "%ld\n", raw);
        write(fd, buf, strlen(buf));
        close(fd);

        usleep(50000); // 50 ms between reads (~20 Hz)
    }

    lgGpiochipClose(chip_fd);
    remove_pid();
    return 0;
}