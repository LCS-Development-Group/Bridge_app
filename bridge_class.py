import random
import serial
import threading
import json
import queue
from enum import Enum

BAUDRATE=115200

class Bridge_UART_state(Enum):
    connected="Connected"
    not_connected="Not connected"
    connecting="Connecting..."

class Bridge_CMDs(Enum):
    CONNECT_UART="con"
    DISCONNECT_UART="dis"
    STOP="stp"
    SEND_UART="snd"

class Bridge_EVs(Enum):
    ERROR="ERR"
    UART_CON_STATUS="UCS"
    UART_CON_ID="UCI"

handshake_rq={
    "JT":"hsk",
    "RQ":"con"
}

handshake_goodbye={
    "JT":"hsk",
    "RQ":"unc"
}


class Bridge:
    def __init__(self, channel_id):
        self.channel_id=channel_id

        self.command_queue=queue.Queue()
        self.event_queue=queue.Queue()

        self.stop_event=threading.Event()
        self.uart_open_event=threading.Event()

        self.cmd_thread=threading.Thread(target=self.__cmd_loop, daemon=True, name=f"bridge{self.channel_id}_cmd_thread")
        self.uart_thread=threading.Thread(target=self.__uart_loop, daemon=True, name=f"bridge{self.channel_id}_uart_thread")
        self.sm=serial.Serial(baudrate=BAUDRATE, timeout=0.1)
        self.sm.dtr=False
        self.sm.rts=False 

        self.mqtt_connected=False
        self.cham_connected=False
        self.chamber_id=None

    def start(self):
        self.cmd_thread.start()
        self.uart_thread.start()

    def __cmd_loop(self):
        while not self.stop_event.is_set():
            cmd, value=self.command_queue.get()
            try:
                match cmd:
                    case Bridge_CMDs.CONNECT_UART:
                        self.__open_uart(value)
                    case Bridge_CMDs.DISCONNECT_UART:
                        self.__close_uart(send_goodbye=True)
                    case Bridge_CMDs.SEND_UART:
                        self.__write_uart(value)
                    case Bridge_CMDs.STOP:
                        self.stop_event.set()
                        self.uart_open_event.set()
            finally:
                self.command_queue.task_done()   
        self.__close_uart()

    def __uart_loop(self):
        while not self.stop_event.is_set():
            self.uart_open_event.wait()
            if self.stop_event.is_set():
                return
            self.__read_uart()

    def __read_uart(self):
        line=self.sm.readline()
        if not line:
            return
        
        decoded=line.decode("utf-8", errors="ignore").strip()
        if not decoded:
            return

        try:
            payload=json.loads(decoded)
            self.__process_json_from_uart(payload)
        except json.JSONDecodeError as e:
            self.event_queue.put((Bridge_EVs.ERROR,f"JSON (from uart) parse: {e}"))
            return

    
    def __write_uart(self, payload):
        try:
            if not self.sm.is_open:
                self.event_queue.put((Bridge_EVs.ERROR, "UART write: port is closed"))
                return
            json_line=json.dumps(payload)+"\n"
            self.sm.write(json_line.encode("utf-8"))
            self.sm.flush()

        except (TypeError, ValueError, serial.SerialException) as e:
            self.event_queue.put((Bridge_EVs.ERROR, f"UART write: {e}"))

    def __process_handshake(self, payload):
        if "RQ" in payload:
            request=payload["RQ"]
            match request:
                case "con":
                    if "ID" in payload:
                        self.chamber_id=payload["ID"]
                        self.event_queue.put((Bridge_EVs.UART_CON_STATUS, Bridge_UART_state.connected))
                        self.event_queue.put((Bridge_EVs.UART_CON_ID, self.chamber_id))
                        self.cham_connected=True
                    else:
                        self.event_queue.put((Bridge_EVs.ERROR, f"handshake response: no ID"))
                case "unc":
                    self.command_queue.put((Bridge_CMDs.DISCONNECT_UART, None))

    def __process_json_from_uart(self, payload):
        json_type=payload.pop("JT", None)
        
        match json_type:
            case "hsk":
                self.__process_handshake(payload)

    def __open_uart(self, port):  
        try:
            if self.sm.is_open:
                return
            
            self.sm.port=port
            self.sm.open()

            self.sm.reset_input_buffer()
            self.sm.reset_output_buffer()

            self.uart_open_event.set()

            self.__write_uart(handshake_rq)
            self.event_queue.put((Bridge_EVs.UART_CON_STATUS, Bridge_UART_state.connecting))


        except serial.SerialException as e:
            self.event_queue.put((Bridge_EVs.ERROR, f"UART open: {e}"))
    
    def __close_uart(self, send_goodbye=False):
        try:
            self.uart_open_event.clear()
            if self.sm.is_open:
                if send_goodbye and self.cham_connected:
                    self.__write_uart(handshake_goodbye)
                    
                self.sm.reset_input_buffer()
                self.sm.reset_output_buffer()
                self.sm.close()

        except serial.SerialException as e:
            self.event_queue.put((Bridge_EVs.ERROR, f"UART close: {e}"))

        finally:
            self.cham_connected=False
            self.chamber_id=None
            self.event_queue.put((Bridge_EVs.UART_CON_STATUS, Bridge_UART_state.not_connected))
    


    '''interface (non blocking functions)'''
    def cmd_connect_chamber(self, port):
        self.command_queue.put((Bridge_CMDs.CONNECT_UART, port))
    def cmd_disconnect_chamber(self):
        self.command_queue.put((Bridge_CMDs.DISCONNECT_UART, None))
    def cmd_send_uart(self, payload):
        self.command_queue.put((Bridge_CMDs.SEND_UART, payload))
    def cmd_stop(self):
        self.command_queue.put((Bridge_CMDs.STOP, None))
