# call by http://192.168.178.210:8080
# send_from_directory() is more secure than send_file() against 'directory traversal attacks'
# DO NOT NAME THIS PROGRAM flask.py ! That's reserved for the module.
from flask import Flask, jsonify, request, send_from_directory, abort, Response
import json # for reading in json file
import subprocess
import os # for os.remove() and BASE_DIR
import threading, time # for client inactivity monitoring
from datetime import datetime
import markdown
import msgBird as ms
from configBird3 import birdpath, update_config_json
from sharedBird import delFromGallery
# for camdata plotting:
import matplotlib.pyplot as plt
from collections import defaultdict
import io

PYTHON = "/home/pi/birdvenv/bin/python3"
### inactivity monitor for endpoint /msgjson
lock = threading.Lock()
timeout = 5  # seconds
last_activity = time.time()
client_active = 1

def monitor_inactivity():
   global last_activity, client_active
   while True:
      time.sleep(1)  # check every second
      with lock:
         # Check if the client has been inactive for too long
         if time.time() - last_activity > timeout:
            if client_active != 0:
               client_active = 0
               ms.setClientActive(0)

### for matplotlib in endpoint '/camdata':
mpl_lock = threading.Lock()
def _svg_error(msg):
    # Simple SVG with error message, always fits in <img> tag
    msg = str(msg).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="120">'
        f'<rect width="100%" height="100%" fill="#fffbe8"/><text x="50%" y="50%" '
        f'dominant-baseline="middle" text-anchor="middle" fill="#db3d00" font-size="22px" font-family="monospace">{msg}</text>'
        f'</svg>'
    )

app = Flask(__name__, static_folder='.')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # disable cacheing
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) # see @app.route('/<path:filename>')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.svg')

@app.route('/')
def index():
   return send_from_directory(app.static_folder, 'vidshot3.html')

@app.route('/reboot')
def reboot():
   cmd = "sudo shutdown -r now"
   ret = subprocess.call(cmd, shell=True)
   print("exit code: " + str(ret), flush=True) # print to where? maybe call 'sys.stdout.flush()'
   return send_from_directory(app.static_folder, 'reboot.html')

@app.route('/shutdown')
def shutdown():
   # cmd = "sudo shutdown -h +1"
   cmd = f"{birdpath['appdir']}/tasmotaDown.sh orderedDown"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'shutdown.html')

@app.route('/upload') # no button for this, good for testing
def upload():
   fifo_path = birdpath['fifo']
   try:
      fd = os.open(fifo_path, os.O_WRONLY | os.O_NONBLOCK)
      with os.fdopen(fd, 'w') as f:
         f.write('0.0\n')
   except BlockingIOError:
      # No reader is currently connected
      ms.log("Flask finds no fifo reader")
   except Exception as e:
      ms.log(f"Error writing to FIFO: {e}")

   # blocking might freeze flask server:
   # with open('ramdisk/birdpipe', 'w') as f:
   #   f.write('0.0\n')
   # cmd = "echo '0.0' >ramdisk/birdpipe"
   # subprocess.call(cmd, shell=True)
   # see effect on shell using 'tail -f ramdisk/birdpipe' when no other reader active (like mainFoBird.py)
   # return cmStr # test this in browser incognito window without cache
   return send_from_directory(app.static_folder, 'snapshot.html') # flask needs to return a response, but could also be a json like in /envupdate

@app.route('/standby')
def chstandby():
   ms.chStandby()
   return send_from_directory(app.static_folder, 'vidshot3.html')

@app.route('/envupdate')
def envupdate():
   cmd = f"{PYTHON} {birdpath['appdir']}/dhtBird3.py"
   subprocess.call(cmd, shell=True)
   return jsonify(success=True)

@app.route('/sysupdate')
def sysupdate():
   cmd = f"bash {birdpath['appdir']}/sysmon2.sh"
   subprocess.call(cmd, shell=True)
   return jsonify(success=True)

@app.route('/updatesettings', methods=['POST'])
def update_settings():
   """
   Handles the JSON POST request from settings.html to update settings.
   """
   # Check if the request contains JSON data
   if not request.is_json:
      return jsonify(status='error', message='Request must be JSON'), 400

   new_settings = request.json
   # Check if new_settings is a valid dictionary
   if not isinstance(new_settings, dict):
      return jsonify(status='error', message='Invalid JSON format'), 400
   try:
      update_config_json(new_settings)
      return jsonify(status='success', message='Settings updated successfully.')
   except Exception as e:
      # A catch-all for any unexpected errors during the process
      return jsonify(status='error', message=f"An error occurred during update: {str(e)}"), 500

@app.route('/msgjson', methods = ['GET'])
def msgJSON():
   # monitor client activity and set clientactive to 0 after timeout
   global last_activity, client_active
   with lock:
      last_activity = time.time()  # activity just occurred
      if client_active != 1:
         client_active = 1
         ms.setClientActive(1)

   # needed so vidshot.html will not read ramdisk/vidmsg.json without the lock:
   return jsonify(ms.readmsg())

@app.route('/msgjson2', methods = ['GET'])
def msgJSON2():
   # other files like config3.html can get vidmsg.json without monitoring client activity for image recording
   # needed so vidshot.html will not read ramdisk/vidmsg.json without the lock:
   return jsonify(ms.readmsg())

# @app.route('/hoursjson', methods = ['GET']) ->  see acknowledge\flaskBird.py

@app.route("/camdata")
def camdata_svg():
   keyParam = request.args.get("target", "brightness") # defaults to "brightness" if only "/camdata" is asked for, but request should be like "/camdata?target=brightness" or "/camdata?target=metaLux"
   # Load data from file
   try:
      with open("camdata/camdata.json", "r") as f:
         data = json.load(f)
   except Exception as e:
      return Response(_svg_error(f"Data load error: {e}"), mimetype="image/svg+xml")
   # example data: [{"timestamp": "2025:07:28:06:12", "brightness": 90, "metaLux": 1400, "luxcategory": 3}, ...]
   # Check if keyParam exists in at least one entry
   if not data or all(keyParam not in entry for entry in data):
      return Response(_svg_error(f"No data for {keyParam}"), mimetype="image/svg+xml")

   # Parse data into day-wise curves
   curves = defaultdict(list)
   for entry in data:
      if keyParam not in entry:
         continue  # skip entries missing this field
      year, month, day, hour, minute = map(int, entry['timestamp'].split(':'))
      dt = datetime(year=year, month=month, day=day, hour=hour, minute=minute)
      day_key = (year, month, day)
      curves[day_key].append((dt, entry[keyParam]))
      # example: curves[(2025, 7, 28)] = [(datetime(2025,7,28,6,12), 90), ...]
   for day_key in curves:
      curves[day_key].sort(key=lambda x: x[0])

   with mpl_lock: # thread safety for multiple requests
      fig, ax = plt.subplots(figsize=(10, 5))
      colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red']
      for idx, (day_key, points) in enumerate(curves.items()):
         times = [dt.time() for dt, _ in points]
         brightness = [b for _, b in points]
         x_vals = [t.hour * 60 + t.minute for t in times]
         label = f"{day_key[1]:02d}-{day_key[2]:02d}"
         ax.plot(x_vals, brightness, label=label, color=colors[idx % len(colors)], marker='o')
      ax.set_xticks([i * 60 for i in range(0, 24, 2)])
      ax.set_xticklabels([f"{i:02d}:00" for i in range(0, 24, 2)])
      ax.set_xlim(0, 1439)
      ax.set_xlabel("Time of Day")
      ax.set_ylabel(keyParam)
      ax.set_title(f"{keyParam} Curves for Each Day")
      ax.legend(title="Date")
      ax.grid(True)
      plt.tight_layout()

      buf = io.StringIO()
      plt.savefig(buf, format="svg")
      plt.close(fig)
      svg = buf.getvalue()
      buf.close()

      return Response(svg, mimetype="image/svg+xml")

# remove mp4 and record from gallery.js, 'del' button in gallery3.html handled by it's sendDelRec(recId)
@app.route('/delrecord', methods=['POST'])
def delrecord():
   data = request.json['data']
   print(f"Received data: {data}")
   rec2del = data.get('rec') + 1
   mp4del = "keep/" + str(data.get('content')) + ".mp4"
   # print(rec2del)
   # print(mp4del)
   delFromGallery(rec2del) # see sharedBird.py
   os.remove(mp4del)
   return jsonify({"received": data})

# this is needed for the files on ramdisk and movements:
@app.route('/<path:filename>')
# def send(filename):
#   return send_from_directory(app.static_folder, filename) 
def serve_file(filename):
    # converts .md and serves as html
    # Prevent path traversal attacks (github copilot)
    safe_path = os.path.normpath(filename)
    absolute_path = os.path.join(BASE_DIR, safe_path)
    if os.path.commonpath([BASE_DIR, absolute_path]) != BASE_DIR:
        abort(403)
    if not os.path.isfile(absolute_path):
        abort(404)

    if filename.endswith('.md'):
        with open(absolute_path, encoding='utf-8') as f:
            md_content = f.read()
            html_body = markdown.markdown(md_content)
        base = os.path.splitext(os.path.basename(filename))[0]
        html_template = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{base}</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
</head>
<body>
{html_body}
</body>
</html>
"""
        return Response(html_template, mimetype='text/html')
        # the browsers view-source: does not show the <head>, as the file is still called an .md, not an .html,
        # but the browsers developer tools (F12) show the <head> in the Network-Response tab of the .md .
    else:
        return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
   debug_mode = False
   ms.init()
   ms.log(f"Start flaskBird3 {datetime.now()}")
   threading.Thread(target=monitor_inactivity, daemon=True).start() # daemon=True so it will not block the main thread or it's exit
   app.run(host='0.0.0.0', port=8080, debug=debug_mode) # port 80 "Permission denied"
   ms.log(f"End flaskBird3 {datetime.now()}")