import serial
import json
import sys
import threading
import time

BAUDRATE=115200
SEND_PERIOD_S=1

from bridge_class import Handshake_codes, make_handshake_json

readings={
    "JT":"sen",
    "HI":0.0,
    "TI":0.0,
    "HE":0.0,
    "TE":0.0,
    "MC":0.0,
    "MV":0.0,
    "MP":0.0,
}

handshake={
    "JT":"hsk",
    "ID": "",
    "RQ": Handshake_codes.CON_REQ.value
}

ping={
    "JT":"hsk",
    "ID": "",
    "RQ": Handshake_codes.PING.value
}

regulator_settings={
    "JT": "reg",
    "SP": 25.0,
    "HI": 5.0,
    "EN": "OFF",
    "ME": "OFF"
}
starter_settings={
    "JT": "sta",
    "SS": "OFF",
    "LS": "OFF"
}


PING_COUNTER_MAX=5

class Emulator():
    def __init__(self, uart_port: str, chamber_id: int):
        self.sm=serial.Serial()
        self.sm.dtr=False
        self.sm.rts=False
        self.sm.timeout=1

        self.sm.port=uart_port
        self.sm.baudrate=BAUDRATE
        handshake["ID"]=chamber_id
        ping["ID"]=chamber_id
        self.connected=False

        self.sender_stop=threading.Event()
        self.mutex=threading.Lock()

        self.ping_counter=0

        #uart connect
        self.sm.open()

    def __readings_loop(self):
        #periodic send of readings
        while not self.sender_stop.wait(SEND_PERIOD_S) and not self.sender_stop.is_set():
            if not self.connected:
                continue

            self.__write(readings)
            self.ping_counter+=1
            if self.ping_counter>=PING_COUNTER_MAX:
                self.ping_counter=0
                ping["RQ"]=Handshake_codes.PING.value
                self.__write(ping)

    def __main_loop(self):
        #reading and responses
        while self.sm.is_open:
            line=self.sm.readline()

            if not line:
                continue
            
            print(line)

            try:
                payload:dict=json.loads(line.decode("utf-8", errors="ignore").strip())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            match payload.get("JT"):
                case "hsk":
                    match payload.get("RQ"):
                        case Handshake_codes.CON_REQ.value:
                            self.connected=True
                            handshake["RQ"]=Handshake_codes.CON_REQ.value
                            self.__write(handshake)

                        case Handshake_codes.DIS_REQ.value:
                            self.connected=False

                        case Handshake_codes.PONG.value:
                            pass # answer to ping, real chamber will have a watchdog on that

                case "sta":
                    starter_settings.update(payload)
                    self.__write(starter_settings)
                    print(f"[starter] {starter_settings}\n")

                case "reg":
                    regulator_settings.update(payload)
                    self.__write(regulator_settings)
                    print(f"[regulator] {regulator_settings}\n")


    def __write(self, payload:dict):
        data=(json.dumps(payload)+"\n").encode("utf-8")
        with self.mutex:
            if self.sm.is_open:
                self.sm.write(data)
                self.sm.flush()

    def run(self):
        threading.Thread(target=self.__readings_loop, daemon=True).start()
        try:
            self.__main_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.sender_stop.set()
            time.sleep(2)
            self.sm.close()
    


if __name__=="__main__":
    try:
        if len(sys.argv)!=3:
            print(f"Usage: py ./chamber_emulator.py <Uart_port> <Chamber_ID>")
        else:
            emulator=Emulator(sys.argv[1], int(sys.argv[2]))
            emulator.run()

    except Exception as e:
        print(f"Encountered exception: {e}")
        

