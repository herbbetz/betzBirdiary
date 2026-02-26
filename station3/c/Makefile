# Makefile for hx711d C daemon

CC = gcc
CFLAGS = -O2 -Wall
LDFLAGS = -llgpio
TARGET = hx711d
SRC = hx711d.c
PID_FILE = /home/pi/station3/ramdisk/hx711d.pid

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC) $(LDFLAGS)

clean:
	rm -f $(TARGET)
	@if [ -f $(PID_FILE) ]; then \
	    echo "Removing stale PID file $(PID_FILE)"; \
	    rm -f $(PID_FILE); \
	fi