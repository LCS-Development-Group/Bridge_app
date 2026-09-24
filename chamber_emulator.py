import serial
import json
import sys
import threading
import time
import random
import traceback

BAUDRATE=115200
SEND_PERIOD_S=1

from bridge import Handshake_codes, make_handshake_json

readings={
    "JT":"sen",
    "HI":10.0,
    "TI":20.0,
    "HE":30.0,
    "TE":40.0,
    "MC":0.110,
    "MV":3.0,
    "MP":0.33,
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
}
starter_settings={
    "JT": "sta",
    "SS": "OFF",
    "LS": "OFF"
}


LEAK_MULT=0.015
MEMB_MULT=0.05
CURR_MULT=0.06
class Dynamics_simulator:
    def __init__(self, 
        start_RH_int:float=20, 
        start_T:float=20, 
        start_RH_ext:float=45,
        start_SP:float=25, 
        start_Hist:float=0.5,
        start_reg_en:bool=False):
        self.RH_int=start_RH_int
        self.T_int=start_T 
        self.RH_ext=start_RH_ext
        self.T_ext=start_T
        self.SP=start_SP
        self.Hist=start_Hist
        self.reg_en=start_reg_en
        self.memb_en=False

        self.memb_curr=0
        self.memb_pow=0
        self.memb_vol=0

        self.__T_max=start_T+2
        self.__T_min=start_T-2
        self.__RH_ext_max=start_RH_ext+10
        self.__RH_ext_min=start_RH_ext-10

        self.__delta_leak=(self.RH_ext-self.RH_int)*LEAK_MULT
        self.mutex=threading.Lock()

    def __update_ext(self):
        self.RH_ext+=round(random.random()*0.1-0.05, 3)
        if self.RH_ext>self.__RH_ext_max:
            self.RH_ext=self.__RH_ext_max
        elif self.RH_ext<self.__RH_ext_min:
            self.RH_ext=self.__RH_ext_min

        self.T_ext+=round(random.random()*0.1-0.05, 3)
        if self.T_ext>self.__T_max:
            self.T_ext=self.__T_max
        elif self.T_ext<self.__T_min:
            self.T_ext=self.__T_min
        self.T_int=self.T_ext

    def update(self):
        with self.mutex:
            self.__update_ext()
            self.__delta_leak=(self.RH_ext-self.RH_int)*LEAK_MULT

            delta=self.__delta_leak
            if self.memb_en:
                delta-=self.RH_int*MEMB_MULT
                self.memb_vol=3
                self.memb_curr=self.RH_int*CURR_MULT
                self.memb_pow=self.memb_vol*self.memb_curr
            else:
                self.memb_vol=0
                self.memb_curr=0
                self.memb_pow=self.memb_vol*self.memb_curr
                

            if self.reg_en:
                error=self.SP-self.RH_int
                if error>self.Hist/2:
                    self.memb_en=False
                    
                elif error<-self.Hist/2:
                    self.memb_en=True

            self.RH_int+=delta

    def get_readings_dict(self)->dict:
        with self.mutex:
            return {
                "JT":"sen",
                "HI":round(self.RH_int,3),
                "TI":round(self.T_int,3),
                "HE":round(self.RH_ext,3),
                "TE":round(self.T_ext,3),
                "MC":round(self.memb_curr,3),
                "MV":round(self.memb_vol,3),
                "MP":round(self.memb_pow, 3)
            }
    def get_reg_dict(self)->dict:
        with self.mutex:
            if self.reg_en:
                EN="ON"
            else:
                EN="OFF"

            return{
                "JT": "reg",
                "SP": round(self.SP,3),
                "HI": round(self.Hist,3),
                "EN": EN,
            }

    def set_reg(self, SP:float=None, Hist:float=None, enabled:bool=None):
        with self.mutex:
            if SP is not None:
                self.SP=SP
            if Hist is not None:
                self.Hist=Hist
            if enabled is not None:
                self.reg_en=enabled
                self.memb_en=False #to be sure


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
        self.dsim=Dynamics_simulator()

        #uart connect
        self.sm.open()

    def __readings_loop(self):
        #periodic send of readings
        while not self.sender_stop.wait(SEND_PERIOD_S) and not self.sender_stop.is_set():
            if not self.connected:
                continue

            self.dsim.update()
            self.__write(self.dsim.get_readings_dict())
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
            
            #print(line)

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
                            payload=self.dsim.get_reg_dict()
                            self.__write(payload=payload)

                        case Handshake_codes.DIS_REQ.value:
                            self.connected=False

                        case Handshake_codes.PONG.value:
                            pass # answer to ping, real chamber will have a watchdog on that

                case "sta":
                    starter_settings.update(payload)
                    self.__write(starter_settings)

                case "reg":
                    en_str=payload.get("EN")
                    en:bool=None
                    if en_str is not None:
                        if en_str=="ON":
                            en=True
                        elif en_str=="OFF":
                            en=False
                    
                    self.dsim.set_reg(SP=payload.get("SP"), Hist=payload.get("HI"), enabled=en)
                
                    payload=self.dsim.get_reg_dict()
                    self.__write(payload=payload)


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
    import argparse

    parser=argparse.ArgumentParser(description="LCS Chamber Emulator")
    parser.add_argument("port", type=str, help="Virtual Serial port (e.g., COM3 or /dev/ttyUSB0). Port must belong to a connected pair")
    parser.add_argument("chamber_id", type=int, help="Chamber ID number")
    args=parser.parse_args()

    try:

        emulator=Emulator(args.port, args.chamber_id)
        emulator.run()

    except Exception:
        traceback.print_exc()
        

