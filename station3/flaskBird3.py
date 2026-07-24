# call by http://192.168.178.210:8080
# send_from_directory() is more secure than send_file() against 'directory traversal attacks'
# DO NOT NAME THIS PROGRAM flask.py ! That's reserved for the module.
from flask import Flask, jsonify, request, send_from_directory, abort, Response
import logging # Werkzeug logger handles Flask's server output
import json # for reading in json file
import psutil # for detecting ssh/sftp/scp on port 22
import subprocess
import os # for os.remove() and BASE_DIR
import threading, time # for client inactivity monitoring
from datetime import datetime
import markdown
import msgBird as ms
from configBird3 import birdpath, update_config_json
from sharedBird import delFromGallery, prev_month
# Import the entire module so you can use the module prefix
import stations.rarebrds4srvpag as rb
# for camdata plotting:
import matplotlib.pyplot as plt
from collections import defaultdict
import io

# PYTHON = "/home/pi/birdvenv/bin/python3"
PYTHON = "/usr/bin/python3"
VK_SCRIPT_RUNNING = False # flag OUTSIDE the function context to keep track of state across multiple browser refreshes.

# for timeseries_svg():
LABELS = {
"temperature": "Temperature (°C)",
"humidity": "Relative Humidity (%)",
"humid_abs": "Absolute Humidity (g/m³)",
"metaLux": "Lux",
"exposure": "Exposure",
"gain": "Gain"
}

### inactivity monitor for endpoint /msgjson
lock = threading.Lock()
timeout = 5  # seconds
last_activity = time.time()
client_active = 1

def has_active_session():
    """Checks for established TCP connections on SSH (22) or VNC_0 (5900) ports."""
    MONITORED_PORTS = {22, 5900}
    for conn in psutil.net_connections(kind='tcp'):
        if conn.status == psutil.CONN_ESTABLISHED:
            # Check if either local or remote port matches our monitored ports
            if conn.laddr.port in MONITORED_PORTS or (conn.raddr and conn.raddr.port in MONITORED_PORTS):
                return True
    return False

def monitor_inactivity():
   global last_activity, client_active
   while True:
      time.sleep(1)  # check every second
      with lock:
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

def timeseries_svg(json_file, key_param):
    # deploy svg graph for /camdata and /tempdata, for both timestamp has key "date":
    time_field="date"
    # Load data
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        return Response(_svg_error(f"Data load error: {e}"), mimetype="image/svg+xml")

    # Check if key exists
    if not data or all(key_param not in entry for entry in data):
        return Response(_svg_error(f"No data for {key_param}"), mimetype="image/svg+xml")

    # Parse data into day-wise curves
    curves = defaultdict(list)

    for entry in data:
        if key_param not in entry:
            continue # skip entries missing this field

        timestamp = entry[time_field]
        year, month, day, hour, minute = map(int, timestamp.split(':'))

        dt = datetime(year, month, day, hour, minute)
        day_key = (year, month, day)

        curves[day_key].append((dt, entry[key_param]))
        # example: curves[(2025, 7, 28)] = [(datetime(2025,7,28,6,12), 90), ...]

    for day_key in curves:
        curves[day_key].sort(key=lambda x: x[0])

    with mpl_lock:
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red']

        for idx, (day_key, points) in enumerate(curves.items()):
            x_vals = [dt.hour * 60 + dt.minute for dt, _ in points]
            values = [v for _, v in points]

            label = f"{day_key[1]:02d}-{day_key[2]:02d}"

            ax.plot(
                x_vals,
                values,
                label=label,
                color=colors[idx % len(colors)],
                marker='o'
            )

        ax.set_xticks([i * 60 for i in range(0, 24, 2)])
        ax.set_xticklabels([f"{i:02d}:00" for i in range(0, 24, 2)])
        ax.set_xlim(0, 1439)

        ax.set_xlabel("Time of Day")
        ylabel = LABELS.get(key_param, key_param) # get label if there is, else key_param
        ax.set_ylabel(ylabel)
        ax.set_title(f"{ylabel} – Daily Curves")
        ax.legend(title="Date")
        ax.grid(True)

        plt.tight_layout()

        buf = io.StringIO()
        plt.savefig(buf, format="svg")
        plt.close(fig)

        svg = buf.getvalue()
        buf.close()

        return Response(svg, mimetype="image/svg+xml")
    
def render_csv_block(basedir, prefix):
    csv_path = f"{birdpath['appdir']}/{basedir}/{prefix}.csv" #os.path.join(basedir, f"{prefix}.csv")
    if not os.path.exists(csv_path):
      ms.log(f"not found: {csv_path}")
      return ""

    html = "<div class='csv-block'>"
    with open(csv_path, "r", encoding="utf-8") as f:
      # csv line: "{MODEL_NAME}, {img#}, {r['confidence']:.2f}, {r['label']}" or "{MODEL_NAME}, None"
      for line in f:
         elems = line.strip().split(",")
         if len(elems) < 4:
            continue
         html += f"<div class='csv-line'>{elems[0]}: {elems[3]} {elems[2]}%</div><br>\n"

    html += "</div>\n"
    return html

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
    if has_active_session():
        # Active SSH/SFTP/VNC_0 connection detected -> return warning page
        return send_from_directory(app.static_folder, 'shutdownNot.html')
    else:
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
   subprocess.Popen(cmd, shell=True) # asynchronous "fire and forget"
   return jsonify(success=True)

@app.route('/sysupdate')
def sysupdate():
   cmd = f"bash {birdpath['appdir']}/sysmon2.sh"
   subprocess.Popen(cmd, shell=True)
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
    # defaults to "brightness" if only "/camdata" is asked for, but request should be like "/camdata?target=brightness" or "http://server/camdata?target=metaLux"
    key_param = request.args.get("target", "metaLux")
    # example camdata.json: [{"date": "2025:07:28:06:12", "metaLux": 1400,..., "luxcategory": 3}, ...]
    return timeseries_svg(
        f"{birdpath['appdir']}/camdata/camdata.json",
        key_param
    )

@app.route("/tempdata")
def tempdata_svg():
    key_param = request.args.get("target", "temperature")
    # "tempdata?target=temperature" or "tempdata?target=humidity" or "http://server/tempdata?target=humid_abs", targets must correspond to keys in tempdata.json
    # example tempdata.json: [{"date": "2025:07:28:06:12", "temperature": 20, "humidity": 70, "humid_abs": 12}, ...]
    return timeseries_svg(
        f"{birdpath['appdir']}/tempdata/tempdata.json",
        key_param
    )

@app.route("/daywatch")
def daygallery():
    # for the images the path relative to flaskBird3.py and it s html must not contain {birdpath['appdir']}:
    dayimg_dir = "ramdisk"
    images = sorted([
        f for f in os.listdir(dayimg_dir)
        if f.lower().endswith(".jpg") and "_" in f # only .jpg filenames containing "_" (which monitor jpg have not)
    ]) # needs be sorted to compare common fst part of filename
    # start HTML:
    html_segments = ["""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Daywatch</title>
        <link rel="stylesheet" href="/bird.css">
    </head>
    <body>
        <h1>Daily Images</h1>
        <div class="indented">
        <div class="rowed"><a href="vidshot3.html" class="button">back</a> <a href="https://www.wiediversistmeingarten.org/view" class="button" target="_blank">Birdiary Karte</a></div>
        <div class='csv-line'>model0 = Birdiary, model2 = Anni's Model</div>
        <a href='./model/daywatch.md'>Erklärung</a>
        </div><hr>
    """]
    
    stat_frame = f"{dayimg_dir}/model2.html"
    if os.path.exists(stat_frame):
       html_segments.append(f"<div><iframe src='{stat_frame}' class='stats-iframe'></iframe></div><hr>\n")

    currentprefix = None
    current_comb_prefix = None  
    groupIdx = 0
    vidURL_prev = ""

    # Build the sequential body
    for img in images:
        namesplits = img.split(".")
        prefix = namesplits[0]  
        comb_prefix = f"{prefix}.{namesplits[1]}"  
        vidURL = f"https://wiediversistmeingarten.org/api/uploads/videos/{comb_prefix}.mp4"
        
        if prefix != currentprefix:
            # 1. End the PREVIOUS group's div/link (if it's not the first loop)
            if currentprefix is not None:
               html_segments.append("</div>")
               html_segments.append(render_csv_block(dayimg_dir, current_comb_prefix))
               html_segments.append(f'<div>{groupIdx} <a href="{vidURL_prev}" target="_blank">{currentprefix}</a></div><hr>')
               # html += f'lastDEBUG: groupIdx={groupIdx}: csv={current_comb_prefix}, video={vidURL_prev}, videolinktext={currentprefix}'

            # 2. Start the NEW group's row
            groupIdx += 1
            html_segments.append('<div class="rowed">')
            currentprefix = prefix
            current_comb_prefix = comb_prefix
            vidURL_prev = vidURL

        # 3. Add the image (this happens for every image, new row or not)    
        html_segments.append(f"""
        <div class="image-container">
            <img src="{dayimg_dir}/{img}" alt="{img}">
        </div>
        """)

    # Close the very last group
    if currentprefix is not None:
      html_segments.append("</div>")
      html_segments.append(render_csv_block(dayimg_dir, current_comb_prefix))
      html_segments.append(f'<div>{groupIdx} <a href="{vidURL_prev}" target="_blank">{currentprefix}</a></div><hr>')

    html_segments.append("</body></html>")
    
    # Join everything cleanly with newlines
    return "\n".join(html_segments)

@app.route("/videoking")
def monthlyking():
    global VK_SCRIPT_RUNNING # global lock
    
    today = datetime.today()
    CURRENT_MONTH = today.strftime("%Y-%m")
    TARGET_MONTH = prev_month(CURRENT_MONTH)
    OUTPUT_FILE = f"vk{TARGET_MONTH}.html"
    
    STATIONS_DIR = os.path.join(BASE_DIR, "stations")
    OUT_PATH = os.path.join(STATIONS_DIR, OUTPUT_FILE)
    
    # print(f"\n[FLASK DEBUG] Checking for VideoKing report...")
    # print(f"[FLASK DEBUG] Expected Path: {OUT_PATH}")
    # print(f"[FLASK DEBUG] File Exists Status: {os.path.exists(OUT_PATH)}")
    
    # If file exists, reset the lock and serve it!
    if os.path.exists(OUT_PATH):
        VK_SCRIPT_RUNNING = False  # Reset lock for next month
        # print(f"[FLASK DEBUG] Serving file directly.")
        return send_from_directory(STATIONS_DIR, OUTPUT_FILE)
        
    else:
        # print(f"[FLASK DEBUG] File not found yet. Lock status: {VK_SCRIPT_RUNNING}")
        if not VK_SCRIPT_RUNNING:
            VK_SCRIPT_RUNNING = True
            SCRIPT_PATH = os.path.join(STATIONS_DIR, "vk_lastmonth_pag.py")
            cmd = ["python", SCRIPT_PATH]
            # print(f"[FLASK DEBUG] Launching background process: {cmd}")
            subprocess.Popen(cmd) 

        return f"""
        <!doctype html>
        <html>
            <head>
                <meta http-equiv="refresh" content="15;url=/videoking">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Wait...</title>
                <link rel="icon" href="/favicon.svg" type="image/svg+xml">
                <link rel="stylesheet" href="/bird.css">
            </head>
            <body>
                <h3>Compiling VideoKing stats for {TARGET_MONTH}...</h3>
                <p>Expected target location:<br><code>{OUT_PATH}</code></p>
                <strong>This page updates automatically every 15 seconds. Please wait...</strong>
            </body>
        </html>
        """

@app.route("/api/report-data")
# selectstations.html submits to layouter '/rarebirds/rb_report.html' with GET parameters station_name and station_id
def api_rarebirds():
    station_name = request.args.get('station_name')
    station_id = request.args.get('station_id')
    # DEBUG PRINT: Watch this terminal output after starting flask from terminal!
    print(f"--- Flask Received: Name={station_name}, ID={station_id} ---")
    # module imported above as rb, so we can call rb.setStation() and rb.getHTML()
    rb.setStation(station_name, station_id)
    report_data = rb.getReport()
    return jsonify(report_data)

# remove mp4 and record from gallery.js, 'del' button in gallery3.html handled by it's sendDelRec(recId):
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
            html_body = markdown.markdown(md_content, extensions=["fenced_code", "tables"]) # md extensions for code window, tables
        base = os.path.splitext(os.path.basename(filename))[0]
        html_template = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{base}</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/birdmd.css">
</head>
<body>
<main>{html_body}</main>
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
   logging.getLogger('werkzeug').setLevel(logging.ERROR) # Werkzeug logger prints no info/warning
   # logging.getLogger('werkzeug').disabled = True
   app.run(host='0.0.0.0', port=8080, debug=debug_mode, threaded=True) # port 80 "Permission denied"
   ms.log(f"End flaskBird3 {datetime.now()}")
