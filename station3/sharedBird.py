# shared functions
import os, sys, subprocess

app_dir = '/home/pi/station3/'
PIDfile = ["mainPID.txt", "hxFiPID.txt"] # PIDfile ids for programms
PIDdir = app_dir + 'ramdisk/'
 # path to main app directory
keep_dir = app_dir + 'keep/'

def roundFlt(flt):
     # round float down to 0 decimal
     # return (math.floor(flt * 100)/100.0)
    return (round(flt, 0))

def fifoExists(pipefile):
# os.path.exists() only working on regular files
    try:
        # Try to open the named pipe for reading
        fd = os.open(pipefile, os.O_RDONLY | os.O_NONBLOCK) # nonblock -> otherwise reader would wait for writer
        os.close(fd)
        return True
    except FileNotFoundError:
        return False

def readPID(id):
    """Returns the PID as an integer, or -1 on any error (missing file, permission error)."""
    fname = os.path.join(PIDdir, PIDfile[id])
    try:
        with open(fname, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, PermissionError, ValueError) as e:
        # Silently return -1 or log if necessary
        return -1
    except Exception as e:
        print(f"Unexpected error reading PID file {fname}: {e}", file=sys.stderr)
        return -1

def writePID(id):
    """Returns True if successful, False on failure."""
    thepid = os.getpid()
    fname = os.path.join(PIDdir, PIDfile[id])
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, 'w') as f:
            f.write(str(thepid))
        return True
    except PermissionError:
        print(f"Permission denied writing PID to {fname}. Try sudo", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error writing PID to {fname}: {e}", file=sys.stderr)
        return False

def clearPID(id):
    """Safely removes the PID file. Returns True if removed, False otherwise."""
    fname = os.path.join(PIDdir, PIDfile[id])
    try:
        if os.path.exists(fname):
            os.remove(fname)
        return True
    except PermissionError:
        print(f"Permission denied removing PID file {fname}. Try sudo", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error removing PID file {fname}: {e}", file=sys.stderr)
        return False

def chg_punct(oldstr):
    # change punctuation in string according to following dict:
    replacements = {' ': '_', ':': '-', '.': '-'} # https://www.geeksforgeeks.org/python-replace-multiple-characters-at-once/
    replaced_chars = [replacements.get(char, char) for char in oldstr]
    return ''.join(replaced_chars)

def write_binVideo(movestart, binVideo):
    newfname = chg_punct(movestart)
    fname = keep_dir + newfname + '.h264'
    with open(fname, 'wb') as vfile:
        vfile.write(binVideo)

    mp4video = keep_dir + newfname + '.mp4'
    cmd = f'ffmpeg -y -framerate 24 -i "{fname}" -c copy "{mp4video}"'
    ffproc = subprocess.Popen(cmd, shell=True)
    ret = ffproc.wait() # await cmd completion
    if ret == 0: os.remove(fname)

def write_gallery(mov_data):
    # write new record to start of gallery.js
    # gallery.js already contains 'records = new Array(\n)'
    fname = keep_dir + 'gallery.js'
    with open(fname, 'r') as oldfile:
        content = oldfile.read()
    fstlinelen = content.find('\n') + 1

    dataline = '"' + chg_punct(mov_data['start_date']) + '|' + str(mov_data['weight']) + '",\n'
    newcontent = content[:fstlinelen] + dataline + content[fstlinelen:]
    with open(fname, 'w') as newfile:
        newfile.write(newcontent)

def delFromGallery(recnum):
    # delete line recnum
    fname = keep_dir + 'gallery.js'
    with open(fname, 'r') as oldfile:
        lines = oldfile.readlines()
    line2delete = recnum # as lines[0] reads 'records = new Array(\n'
    with open(fname, 'w') as newfile:
        for i in range(len(lines)):
            if i != line2delete: newfile.write(lines[i])

# videoking & delete_movs calculation:
def prev_month(month_str): # e.g. month_str = '2026-04'
    # Split and convert to integers
    year, month = map(int, month_str.split('-'))
    # Calculate previous month
    if month > 1:
        month -= 1
    else:
        year -= 1
        month = 12
    # Return formatted string with zero-padding (:02d)
    return f"{year}-{month:02d}"

''' for the old /acknowledge version:
def copy2mp4(movesaved):
    h264name = app_dir + 'movements/' + movesaved + '.h264'
    newfname = chg_punct(movesaved)
    mp4video = keep_dir + newfname + '.mp4'
    cmd = 'ffmpeg -framerate 24 -i ' + h264name + ' -c copy ' + mp4video
    ffproc = subprocess.Popen(cmd, shell=True)
    ret = ffproc.wait() # await cmd completion
    if ret == 0: os.remove(h264name)
'''