# shared functions
import os, subprocess

PIDfile = ["mainPID.txt", "hxFiPID.txt"] # PIDfile ids for programms
keep_dir = 'keep/'

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

def readPID(id):
    # read main program PID
    fname = PIDfile[id]
    if not os.path.exists(fname): return "" # empty string
    with open(fname, 'r') as f:
        thepid = f.read()
    return thepid

def writePID(id):
    # write main program PID
    thepid = os.getpid()
    with open(PIDfile[id], 'w') as f:
        f.write(str(thepid))

def clearPID(id):
    os.remove(PIDfile[id])

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
    cmd = 'ffmpeg -framerate 24 -i /home/pi/station2/' + fname + ' -c copy /home/pi/station2/' + mp4video
    ffproc = subprocess.Popen(cmd, shell=True)
    ret = ffproc.wait() # await cmd completion
    if ret == 0: os.remove(fname)

def copy2mp4(movesaved):
    h264name = 'movements/' + movesaved + '.h264'
    newfname = chg_punct(movesaved)
    mp4video = keep_dir + newfname + '.mp4'
    cmd = 'ffmpeg -framerate 24 -i /home/pi/station2/' + h264name + ' -c copy /home/pi/station2/' + mp4video
    ffproc = subprocess.Popen(cmd, shell=True)
    ret = ffproc.wait() # await cmd completion
    if ret == 0: os.remove(h264name)

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
