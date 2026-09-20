import serial
import json
import time
import threading
import paho.mqtt.client as mqtt

from bridge import Bridge
from GUI import App_main

import sys
if sys.platform=="win32":
    windows_app_id="LCS_Bridge_E06E523D"
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(windows_app_id)


def setup():
    pass

if __name__=="__main__":
    setup()
    try:
        app=App_main()
        app.start()

    except Exception as e:
        print(f"Encountered exception: {e}")
