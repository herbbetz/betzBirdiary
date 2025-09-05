# call by http://192.168.178.210:8080
# send_from_directory() is more secure than send_file() against 'directory traversal attacks'
# DO NOT NAME THIS PROGRAM flask.py ! That's reserved for the module.
from flask import Flask, jsonify, request, send_from_directory, abort, Response
import json # for reading in json file
import subprocess
import os # for os.remove() and BASE_DIR
import time
import markdown
import msgBird as ms
from sharedBird import readPID, delFromGallery

app = Flask(__name__, static_folder='.')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # disable cacheing
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) # see @app.route('/<path:filename>')

@app.route('/')
def index():
   return send_from_directory(app.static_folder, 'vidshot.html')

@app.route('/reboot')
def reboot():
   cmd = "sudo shutdown -r +1"
   ret = subprocess.call(cmd, shell=True)
   print("exit code: " + str(ret), flush=True) # print to where? maybe call 'sys.stdout.flush()'
   return send_from_directory(app.static_folder, 'reboot.html')

@app.route('/shutdown')
def shutdown():
   # cmd = "sudo shutdown -h +1"
   cmd = "/home/pi/station2/tasmotaDown.sh orderedDown"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'shutdown.html')

@app.route('/upload') # no button for this, good for testing
def upload():
   cmd = "echo '0.0' >ramdisk/birdpipe"
   subprocess.call(cmd, shell=True)
   # see effect on shell using 'tail -f ramdisk/birdpipe' when no other reader active (like mainFoBird.py)
   # return cmStr # test this in browser incognito window without cache
   return send_from_directory(app.static_folder, 'snapshot.html') # flask needs to return a response

@app.route('/upmovement')
def upmovement():
   # cmd = ["python3", "/home/pi/station2/uploadBird.py", "&>>", "/home/pi/station2/logs/upload.log"] # no luck with cmd list, see flaskTest.py??
   cmd = "python3 /home/pi/station2/uploadBird.py &>> /home/pi/station2/logs/upload.log"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'upload.html')

@app.route('/keeplocal')
def keeplocal():
   cmd = "python3 /home/pi/station2/keepBird.py"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'keeplocal.html')

@app.route('/delrecord', methods=['POST'])
def delrecord():
   data = request.json['data']
   print(f"Received data: {data}")
   rec2del = data.get('rec') + 1
   mp4del = "keep/" + str(data.get('content')) + ".mp4"
   # print(rec2del)
   # print(mp4del)
   delFromGallery(rec2del)
   os.remove(mp4del)
   return jsonify({"received": data})

@app.route('/delmovement')
def delmovement():
   ms.emptyVidDateStr()
   cmd = "rm movements/*"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'delmovement.html')

@app.route('/chmain')
def chmain():
   prognames = ["mainFoBird2.py", "mainAckBird2.py"]
   mainPID = readPID(0) # see sharedBird
   if not mainPID: # empty string means False in python
      print("no PID to kill")
   else:
      cmd = "kill " + mainPID
      subprocess.call(cmd, shell=True)
      time.sleep(1)
      curMode = ms.getUpmode()
      if (curMode == 1): # mainFoBird2.py was active
         cmd = "python3 /home/pi/station2/" + prognames[1] + " &>> /home/pi/station2/logs/main.log &"
      else:
         cmd = "python3 /home/pi/station2/" + prognames[0] + " &>> /home/pi/station2/logs/main.log &"
      subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'changedmain.html')

@app.route('/standby')
def chstandby():
   ms.chStandby()
   return send_from_directory(app.static_folder, 'vidshot.html')

@app.route('/msgjson', methods = ['GET'])
# needed so vidshot.html will not read ramdisk/vidmsg.json without the lock
def msgJSON():
   if(request.method == 'GET'): 
      data = ms.readmsg()
      return jsonify(data)

@app.route('/hoursjson', methods = ['GET'])
# statistics of daytime of videos from birdiary web api, fetched by gethoursStats.py
def hoursJSON():
   try:
      with open('hour_counts.json', 'r') as file:
         data = json.load(file)
      return jsonify(data)
   except (FileNotFoundError, json.JSONDecodeError) as e:
      return jsonify({"error": str(e)}), 500
   
# this is needed for the files on ramdisk and movements:
@app.route('/<path:filename>')
# def send(filename):
#   return send_from_directory(app.static_folder, filename) 
def serve_file(filename):
    # converts .md and serves as html
    # Prevent path traversal attacks (github copilot)
    safe_path = os.path.normpath(filename)
    absolute_path = os.path.join(BASE_DIR, safe_path)
    if not absolute_path.startswith(BASE_DIR):
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
   app.run(host='0.0.0.0', port=8080, debug=debug_mode) # port 80 "Permission denied"
   print("flaskBird cleaning up")