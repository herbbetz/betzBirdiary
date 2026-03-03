# test_hx711d_fifo.py

FIFO_PATH = "/home/pi/station3/ramdisk/hxfifo"

def main():
    with open(FIFO_PATH, "r") as fifo:
        while True:
            line = fifo.readline()
            if not line:
                continue
            print(line.strip())

if __name__ == "__main__":
    main()