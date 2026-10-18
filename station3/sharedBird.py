# shared functions
import fcntl, json, os, signal, subprocess, sys, time # subprocess shell call needs sys

app_dir = '/home/pi/station3/'
PIDdir = app_dir + 'ramdisk/'
PIDjson = PIDdir + 'PID.json'  # {"hxFiBird.sh": 123, "hxFiBirdStateCt.py": 124}
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

def getTestmode():
    # return 'testmode' directly from lastdown.json (not from flask EP /testmode)
    jsonfile = f"{app_dir}/lastdown.json"
    if not os.path.exists(jsonfile):
        return {"error": "JSON file not found"}, 404
    try:
        with open(jsonfile, "r", encoding="utf-8") as file:
            data = json.load(file)
        # If the property is missing, treat testmode as disabled.
        return data.get("testmode", 0)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}, 500
    except OSError as error:
        return {"error": f"Could not read JSON file: {error}"}, 500

class pids:
    def __init__(self):
        self.pids = {}
        self.load_pids()
        
    def load_pids(self):
        if os.path.exists(PIDjson):
            with open(PIDjson, 'r') as f:
                fcntl.flock(f, fcntl.LOCK_EX) # will wait for other locks to close
                try:
                    self.pids = json.load(f)
                except (OSError, ValueError): 
                    self.pids = {}
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        else:
            self.pids = {}

    def save_pids(self):
        with open(PIDjson, 'a') as f:
            fcntl.flock(f, fcntl.LOCK_EX) # will wait for other locks to close
            f.truncate(0)  # clear file before writing
            try:
                json.dump(self.pids, f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def get_pid(self, process_name):
        if process_name in self.pids:
            return self.pids.get(process_name)
        return None

    def set_pid(self, process_name, pid):
        self.pids[process_name] = pid
        self.save_pids()

    def remove_pid(self, process_name):
        if process_name in self.pids:
            del self.pids[process_name]
            self.save_pids()

    @staticmethod
    def alive(name, pid):  # cmdline check guards against stale entries and PID reuse
        try:
            with open(f'/proc/{pid}/cmdline') as f: return name in f.read().replace('\0', ' ')
        except OSError: return False

    def kill_pid(self, name, timeout=5.0):  # SIGTERM, wait, SIGKILL; True if no longer running
        pid = self.get_pid(name)
        if pid is None: return True
        for sig in (signal.SIGTERM, signal.SIGKILL):
            if not self.alive(name, pid): break
            os.kill(pid, sig)
            t0 = time.time()
            while self.alive(name, pid) and time.time() - t0 < timeout: time.sleep(0.1)
        self.remove_pid(name)
        return not self.alive(name, pid)

    def kill_list(self, process_names):
        # kill .sh wrappers first, then .py scripts, so that .sh wrappers don't respawn the .py scripts
        sh_wrappers = [name for name in process_names if name.endswith('.sh')]
        py_scripts = [name for name in process_names if name.endswith('.py')]
        for process_name in sh_wrappers:
            self.kill_pid(process_name)
        for process_name in py_scripts:
            self.kill_pid(process_name)

    def kill_all(self):
        # kill .sh wrappers first, then .py scripts, so that .sh wrappers don't respawn the .py scripts
        sh_wrappers = [name for name in self.pids.keys() if name.endswith('.sh')]
        py_scripts = [name for name in self.pids.keys() if name.endswith('.py')]
        for process_name in sh_wrappers:
            self.kill_pid(process_name)
        for process_name in py_scripts:
            self.kill_pid(process_name)

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