# analog to uploadBird, but saving files in keep/ instead of uploading
import json
import os
# own local modules:
import msgBird as ms
from sharedBird import write_gallery, copy2mp4

def readMovement(mstartdate): # same as uploadBird
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
write_gallery(movementData)
copy2mp4(saveformat)
ms.emptyVidDateStr()
os.system("rm movements/*")