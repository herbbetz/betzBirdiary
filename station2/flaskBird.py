# call by http://192.168.178.210:8080
# send_from_directory() is more secure than send_file() against 'directory traversal attacks'
# DO NOT NAME THIS PROGRAM flask.py ! That's reserved for the module.
from flask import Flask, jsonify, request, send_from_directory
import subprocess
import msgBird as ms

app = Flask(__name__, static_folder='.')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # disable cacheing

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
   cmd = "sudo shutdown -h +1"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'shutdown.html')

@app.route('/upload') # no button for this, good for testing
def upload():
   cmd = "echo '0.0' >ramdisk/birdpipe"
   subprocess.call(cmd, shell=True)
   # see effect on shell using 'tail -f ramdisk/birdpipe' when no other reader active (like mainFoBird.py)
   # return cmStr # test this in browser incognito window without cache
   return send_from_directory(app.static_folder, 'upload.html') # flask needs to return a response

@app.route('/upmovement')
def upmovement():
   # cmd = ["python3", "/home/pi/station2/uploadBird.py", "&>>", "/home/pi/station2/logs/upload.log"] # no luck with cmd list, see flaskTest.py??
   cmd = "python3 /home/pi/station2/uploadBird.py &>> /home/pi/station2/logs/upload.log"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'upload.html')

@app.route('/delmovement')
def delmovement():
   ms.emptyVidDateStr()
   cmd = "rm movements/*"
   subprocess.call(cmd, shell=True)
   return send_from_directory(app.static_folder, 'delmovement.html')

@app.route('/msgjson', methods = ['GET'])
# needed so vidshot.html will not read ramdisk/vidmsg.json without the lock
def msgJSON():
   if(request.method == 'GET'): 
      data = ms.readmsg()
      return jsonify(data)

# this is needed for the files on ramdisk and movements:
@app.route('/<path:filename>')
def send(filename):
   return send_from_directory(app.static_folder, filename) 

if __name__ == '__main__':
   debug_mode = False
   ms.init()
   app.run(host='0.0.0.0', port=8080, debug=debug_mode) # port 80 "Permission denied"
   print("flaskBird cleaning up")