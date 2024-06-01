# shared functions
import os

def roundFlt(flt):
     # round float down to 2 decimal
     # return (math.floor(flt * 100)/100.0)
    return (round(flt, 2))

def fifoExists(pipefile):
# os.path.exists() only working on regular files
    try:
        # Try to open the named pipe for reading
        fd = os.open(pipefile, os.O_RDONLY | os.O_NONBLOCK) # nonblock -> otherwise reader would wait for writer
        os.close(fd)
        return True
    except FileNotFoundError:
        return False
