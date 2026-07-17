import serial
import json
import sys
import threading

UART_PORT=sys.argv[1]
BAUDRATE=115200
CHAMBER_ID=sys.argv[2]
SEND_PERIOD_S=1

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
    "ID": CHAMBER_ID,
    "RQ": "con"
}

class Emulator():
    def __init__(self):
        self.sm=serial.Serial()
        self.sm.dtr=False
        self.sm.rts=False
        self.sm.timeout=1

        self.sm.port=UART_PORT
        self.sm.baudrate=BAUDRATE
        self.status="unc" #to bridge not uart itself

        self.sender_stop=threading.Event()
        self.mutex=threading.Lock()

    def connect(self):
        self.sm.open()
        self.sm.reset_input_buffer()
        self.sm.reset_output_buffer()


    def disconect(self):
        self.sm.reset_input_buffer()
        self.sm.reset_output_buffer()
        self.sm.close()

    def answer_handhake(self, rq_payload):
        if "RQ" in rq_payload:
            handshake["RQ"]=rq_payload["RQ"]

            self.status=handshake["RQ"]
            payload=json.dumps(handshake)+"\n"
            self.sm.write(payload.encode("utf-8"))
            self.sm.flush()
        
    def sender_loop(self):
        while not self.sender_stop.wait(SEND_PERIOD_S) and not self.sender_stop.is_set():
            with self.mutex:
                if self.status=="con":
                    payload=json.dumps(readings)+"\n"
                    self.sm.write(payload.encode("utf-8"))
                    self.sm.flush()

    def run(self):
        try:
            self.connect()
            self.answer_handhake(handshake) #anouncement at boot
            self.sender=threading.Thread(target=self.sender_loop)
            self.sender.start()

            while self.sm and self.sm.is_open:
                line=self.sm.readline()
                if not line:
                    continue

                decoded=line.decode("utf-8", errors='ignore').strip()
                if not decoded:
                    continue

                try:
                    payload=json.loads(decoded)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"parse error: {e} | Raw: {line}")
                    continue

                if "JT" in payload:
                    if payload["JT"]=="hsk":
                        with self.mutex:
                            self.answer_handhake(rq_payload=payload)

        except KeyboardInterrupt:
            print("Shutting from terminal")

        except Exception as e:
            print(f"Encountered exception: {e}")
    
        finally:
            self.sender_stop.set()

            if hasattr(self, "sender"):
                self.sender.join(timeout=1)

            self.disconect()


if __name__=="__main__":
    try:
        emulator=Emulator()
        emulator.run()

    except Exception as e:
        print(f"Encountered exception: {e}")
        

