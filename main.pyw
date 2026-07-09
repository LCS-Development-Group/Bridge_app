import serial
import json
import time
import threading
import paho.mqtt.client as mqtt

from bridge_class import Bridge
from app_class import App_main

import sys
if sys.platform=="win32":
    windows_app_id="lcs_dev_group.lcs_bridge.app_main"
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(windows_app_id)


def setup():
    pass

if __name__=="__main__":
    setup()
    try:
        app=App_main([Bridge(), Bridge()])
        app.start()

    #except KeyboardInterrupt:
        #print("Shutting from terminal")

    except Exception as e:
        print(f"Encountered exception: {e}")
