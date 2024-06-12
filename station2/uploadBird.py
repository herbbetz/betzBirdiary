# upload last file saved in ./movements
import json
import os
import requests
# own local modules:
import msgBird as ms
from configBird import serverUrl, boxId # import all variables from ./configBird.py

def readMovement(mstartdate):
    filename = 'movements/' + mstartdate + '.json'
    if not os.path.isfile(filename):
        ms.log('error: no ' + filename)
        exit(1) # end upload script
    with open(filename) as json_file:
        data = json.load(json_file)
    return data

#### main:
ms.init()
movementStartDate = ms.getVidDateStr()
if movementStartDate == "":
    ms.log("no movementStartDate from msgBird")
    exit(1)
movementData = readMovement(movementStartDate)
saveformat = movementData['start_date'] # 2024-05-12_21:20:31.955550
# reverse replace(' ', '_') in mainAckBird.py:
startdate = saveformat.replace('_', ' ') # '2024-05-12 21:20:31.955550'
movementData['start_date'] = startdate

files = {}
files["json"] = (None, json.dumps(movementData), 'application/json')
# files['json'] is tuple like:
# (None, '{"audio": "audioKey", "video": "videoKey", "weight": 99, "environment": {}}', 'application/json')

audio_filename = startdate + '.wav'
video_filename = startdate + '.h264'
audio_saved = saveformat + '.wav'
video_saved = saveformat + '.h264'
files['audioKey'] = (audio_filename, open('movements/' + audio_saved, 'rb'))
files['videoKey'] = (video_filename, open('movements/' + video_saved, 'rb'))

try:
    ms.log('sending to ' + serverUrl + 'movement/' + boxId)
    r = requests.post(serverUrl + 'movement/' + boxId, files=files, timeout=60)
    ms.log('Movement data sent: ' + files['json'][1]) # files['json'][1] is string inside tuple files['json'], files is dictionary of files to send, str(dict)
    ms.log('Corresponding movement_id: ' + r.text) # type(r.content) -> bytes
    ms.emptyVidDateStr()
    os.system("rm movements/*")
except (requests.ConnectionError, requests.Timeout) as exception:
    ms.log('failed movement upload - ' + str(exception))