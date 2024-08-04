# test functions of msgBird.py
import msgBird as ms
from datetime import datetime
import time

ms.init()
# ms.writemsg()
ms.setImgCnt(123)
ms.setVidDateStr(str(datetime.now()))
# ms.emptyVidDateStr()
ms.setConfirm()
ms.log("neuer fehler")
ms.setEnvirEvt()
ms.setSysmonEvt()
print(ms.getVidDateStr())
print(ms.getLogCnt())
# print("sleeping 5")
# time.sleep(5)
# ms.emptyVidDateStr()