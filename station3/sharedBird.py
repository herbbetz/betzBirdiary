# shared functions
import os, subprocess, json

PIDfile = ["mainPID.txt", "hxFiPID.txt"] # PIDfile ids for programms
app_dir = '/home/pi/station3/' # path to main app directory
keep_dir = app_dir + 'keep/'

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
    if not os.path.exists(fname): return -1
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

'''
def update_config_json(config_path, offset_val, scale_val):
    #Update or insert hxOffset and hxScale in config.json.
    data = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as jfile:
            try:
                data = json.load(jfile) # read
            except json.JSONDecodeError:
                print(f"{config_path} is invalid JSON.")
    else:
        return

    data['hxOffset'] = offset_val
    data['hxScale'] = scale_val

    with open(config_path, 'w') as jfile:
        json.dump(data, jfile, indent=4)

    print(f"    Updated {config_path} with:")
    print(f"    hxOffset = {offset_val}")
    print(f"    hxScale  = {scale_val}")
'''
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