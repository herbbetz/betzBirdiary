# test functions of msgBird.py
import msgBird as ms
from datetime import datetime
import time
import sys

print('give one arg for reading or two for writing to ' + ms.filename + ' via msgBird')
if len(sys.argv) < 2 or len(sys.argv) > 3:
    print("only 2 args allowed")
    exit(0)

ms.init()
dictkey = sys.argv[1]
msg = ms.message
print("scheme: " + str(msg))

print("before: " + str(ms.readmsg()))

# test read:
if len(sys.argv) == 2:
    if not dictkey in msg.keys():
        print("key not known:" + dictkey)
        exit(0)
    else:
        print(str(dictkey) + " is " + str(ms.readmsgProp(dictkey)))


# test update:
if len(sys.argv) == 3:
    if isinstance(msg[dictkey], int): # only int argument is checked for
        if not sys.argv[2].isnumeric():
            print(str(dictkey) + " requires integer")
            exit(0)
    dictval = sys.argv[2]
    ms.setmsgprop(dictkey, dictval)
    # ms.setmsgProps({'lastvid':'hello',})
    # ms.setmsgProps({'imgid': 99, 'lastvid':'bumms'})


print("after: " + str(ms.readmsg()))