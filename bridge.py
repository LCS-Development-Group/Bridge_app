import serial
import threading
import json
import queue
from enum import Enum
import paho.mqtt.client as mqtt
import time
import secrets

WATCHDOG_TIME=10.0
BAUDRATE=115200

MQTT_BROKER_IP="LCSRP5.local"
# MQTT_BROKER_IP="LCSRP5.remote"
MQTT_BROKER_PORT=1883

class Bridge_UART_state(Enum):
    connected="Connected"
    not_connected="Not connected"
    connecting="Connecting..."

class Bridge_CMDs(Enum):
    CONNECT_UART="con"
    DISCONNECT_UART="dis"
    STOP="stp"
    SEND_UART="snd"
    SET_ADV="adv"

class Bridge_EVs(Enum):
    ERROR="ERR"
    UART_CON_STATUS="UCS"
    UART_CON_ID="UCI"
    UART_TRAFFIC_RECEIVE="UTR"
    MQTT_TRAFFIC_RECEIVE="MTR"

class Handshake_codes(Enum):
    CON_REQ="con"
    DIS_REQ="dis"
    PING="png"
    PONG="alv"
    ACK="ack"
def make_handshake_json(code:Handshake_codes) -> dict:
    return {"JT":"hsk", "RQ":code.value}

chamber_default_readings={"HI": None, "TI": None, "HE": None, "TE": None, "MC": 0.0, "MV": 0.0, "MP": 0.0}
chamber_default_regulator={"SP": 0.0, "HI": 0.0, "EN": None}

CONN_STAT_PAYLOAD={
    "ON":{"CS":"Online"},
    "OFF":{"CS":"Offline"}
}

class MQTT_topics:
    def __init__(self):
        '''this script listens to set, and answears to get'''
        self.regulator_get=""
        self.regulator_set=""
        self.starter_get=""
        self.starter_set=""
        self.readings=""
        self.conn_status=""

    def generate_topics(self, chamber_id:int):
        self.regulator_get=f"chambers/{chamber_id}/regulator/get"
        self.regulator_set=f"chambers/{chamber_id}/regulator/set"
        self.starter_get=f"chambers/{chamber_id}/starter/get"
        self.starter_set=f"chambers/{chamber_id}/starter/set"
        self.readings=f"chambers/{chamber_id}/readings"
        self.RHT_graph=f"chambers/{chamber_id}/RHT_graph"
        self.conn_status=f"chambers/{chamber_id}/misc/conn_stat"

class MQTT_CLient:
    def __init__(self, brige_inst:"Bridge"):
        self.client=mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=f"LCS_bridge_{secrets.token_hex(8)}")
        self.topics=MQTT_topics()
        self.bridge=brige_inst

    def connect_mqtt(self, chamber_id:int)->bool:
        if self.client.is_connected():
            self.disconnect_mqtt()

        try:
            self.topics.generate_topics(chamber_id=chamber_id)

            self.client.message_callback_add(self.topics.regulator_set, self.__regulator_from_server_cb)
            self.client.message_callback_add(self.topics.starter_set, self.__starter_from_server_cb)

            #status LWT
            self.client.will_set(topic=self.topics.conn_status, payload=json.dumps(CONN_STAT_PAYLOAD["OFF"]), qos=1, retain=True)
            self.client.connect(host=MQTT_BROKER_IP, port=MQTT_BROKER_PORT, keepalive=60)
            self.client.loop_start()

            self.client.publish(topic=self.topics.conn_status, payload=json.dumps(CONN_STAT_PAYLOAD["ON"]), retain=True)
            self.client.subscribe([(self.topics.regulator_set,0), (self.topics.starter_set,0)])

        except Exception:
            return False
        return True

    def disconnect_mqtt(self):
        try:
            wait=self.client.publish(topic=self.topics.conn_status, payload=json.dumps(CONN_STAT_PAYLOAD["OFF"]), retain=True)
            wait.wait_for_publish(timeout=0.5)

            wait=self.client.publish(topic=self.topics.readings, payload=json.dumps(chamber_default_readings), retain=False)
            wait.wait_for_publish(timeout=0.5)

            wait=self.client.publish(topic=self.topics.RHT_graph, payload=json.dumps(chamber_default_readings), retain=False)
            wait.wait_for_publish(timeout=0.5)

            wait=self.client.publish(topic=self.topics.regulator_get, payload=json.dumps(chamber_default_regulator), retain=False)
            wait.wait_for_publish(timeout=0.5)

            if self.client.is_connected():
                self.client.disconnect()

            self.client.loop_stop()
        except Exception:
            pass

    

        for topic in (self.topics.regulator_set, self.topics.starter_set):
            if topic:
                try:  
                    self.client.message_callback_remove(topic)
                except KeyError:
                    pass
            
        

    def __regulator_from_server_cb(self, client, userdata, msg):
        try:
            payload=json.loads(msg.payload.decode())
            payload={"JT":"reg", **payload}#json type injection
            
            #just forward to esp
            self.bridge.cmd_send_uart(payload)
            if self.bridge.adv==True:
                self.bridge.event_queue.put((Bridge_EVs.MQTT_TRAFFIC_RECEIVE, json.dumps(payload)))

        except Exception as e:
            print(f"json parse err: {e}")

    def __starter_from_server_cb(self, client, userdata, msg):
        try:
            payload=json.loads(msg.payload.decode())
            payload={"JT":"sta", **payload}#json type injection
            
            #WIP - no forward for now
            #self.bridge.cmd_send_uart(payload)
            if self.bridge.adv==True:
                self.bridge.event_queue.put((Bridge_EVs.MQTT_TRAFFIC_RECEIVE, json.dumps(payload)))

        except Exception as e:
            print(f"json parse err: {e}")

    def publish(self, topic:str, payload:dict|str, retain:bool=True):
        if not topic or not payload:
            return
        data=json.dumps(payload) if isinstance(payload, dict) else payload
        self.client.publish(topic, data, retain=retain)
    

class Bridge:
    def __init__(self, channel_id):
        self.channel_id=channel_id

        self.command_queue=queue.Queue()
        self.event_queue=queue.Queue()

        self.stop_event=threading.Event()
        self.uart_open_event=threading.Event()

        self.cmd_thread=threading.Thread(target=self.__cmd_loop, daemon=True, name=f"bridge{self.channel_id}_cmd_thread")
        self.uart_thread=threading.Thread(target=self.__uart_loop, daemon=True, name=f"bridge{self.channel_id}_uart_thread")
        self.sm=serial.Serial(baudrate=BAUDRATE, timeout=0.25)

        self.sm.rts=False
        self.sm.dts=True

        self.cham_connected=False
        self.cham_disconnecting=False
        self.chamber_id=None
        self.adv=False
        self.sm_rx_timestamp=0.0

        self.mqtt=MQTT_CLient(brige_inst=self)

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
                    case Bridge_CMDs.SET_ADV:
                        self.adv=value
            finally:
                self.command_queue.task_done()   
        self.__close_uart()

    def __uart_loop(self):
        while not self.stop_event.is_set():
            self.uart_open_event.wait()
            if self.stop_event.is_set():
                return
            
            self.__read_uart()

            #watchdog
            if self.cham_connected and not self.cham_disconnecting and (time.monotonic()-self.sm_rx_timestamp>WATCHDOG_TIME):
                self.event_queue.put((Bridge_EVs.ERROR, f"LCS silent for >{WATCHDOG_TIME} -> autodisconnect"))
                self.cham_disconnecting=True
                self.cmd_disconnect_chamber()

    def __read_uart(self):
        try:
            line=self.sm.readline()
        except (serial.SerialException, OSError, TypeError):
            return #triggered when bridge thread closes the port while reader is stuck on it

        if not line:
            return
        
        decoded=line.decode("utf-8", errors="ignore").strip()
        if not decoded:
            return

        try:
            payload=json.loads(decoded)

            self.sm_rx_timestamp=time.monotonic()

            self.__process_json_from_uart(payload)
        except json.JSONDecodeError:
            pass
            #self.event_queue.put((Bridge_EVs.ERROR,f"JSON (from uart) parse: {e}"))
            #return

    
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

    def __process_handshake(self, payload:dict):
        if "RQ" in payload:
            request=payload.get("RQ")
            if not request:
                return


            '''
                CON_REQ="con"
                DIS_REQ="dis"
                PING="png"
                PONG="alv"
            '''
            match request:
                case Handshake_codes.PING.value:
                    if "ID" in payload:
                        temp_id=payload["ID"]
                        if self.chamber_id is not None and temp_id!=self.chamber_id:
                            self.event_queue.put((Bridge_EVs.ERROR, f"ping from LCS: chamber_id mismatch ({temp_id}vs{self.chamber_id}) -> autodisconnect"))
                            self.command_queue.put((Bridge_CMDs.DISCONNECT_UART, None))
                        else:
                            self.cmd_send_uart(make_handshake_json(Handshake_codes.PONG))
                    else:
                        self.event_queue.put((Bridge_EVs.ERROR, "ping: no ID"))


                case Handshake_codes.CON_REQ.value:
                    self.__write_uart(payload=make_handshake_json(Handshake_codes.ACK))
                    if "ID" in payload:
                        self.chamber_id=payload["ID"]
                        self.event_queue.put((Bridge_EVs.UART_CON_STATUS, Bridge_UART_state.connected))
                        self.event_queue.put((Bridge_EVs.UART_CON_ID, self.chamber_id))
                        self.cham_connected=True

                        if not self.mqtt.connect_mqtt(self.chamber_id):
                            self.event_queue.put((Bridge_EVs.ERROR, "MQTT connection error"))
                            self.cmd_disconnect_chamber()

                    else:
                        self.event_queue.put((Bridge_EVs.ERROR, "handshake: no ID"))

                case Handshake_codes.ACK.value:
                    if "ID" in payload:
                        self.chamber_id=payload["ID"]
                        self.event_queue.put((Bridge_EVs.UART_CON_STATUS, Bridge_UART_state.connected))
                        self.event_queue.put((Bridge_EVs.UART_CON_ID, self.chamber_id))
                        self.cham_connected=True

                        if not self.mqtt.connect_mqtt(self.chamber_id):
                            self.event_queue.put((Bridge_EVs.ERROR, "MQTT connection error"))
                            self.cmd_disconnect_chamber()

                    else:
                        self.event_queue.put((Bridge_EVs.ERROR, "handshake: no ID"))


                case Handshake_codes.DIS_REQ.value:
                    self.command_queue.put((Bridge_CMDs.DISCONNECT_UART, None))

                case Handshake_codes.PONG.value:
                    #technically this should never be received
                    pass

    def __process_json_from_uart(self, payload:dict):
        json_type=payload.get("JT")
        if not json_type:
            return

        mqtt_payload={key: value for key,value in payload.items() if key!="JT"} #strip json type
        
        match json_type:
            case "hsk":
                self.__process_handshake(payload) #no need to do so here
                #return
            case "sen":
                if self.cham_connected:
                    self.mqtt.publish(self.mqtt.topics.readings, mqtt_payload, retain=False)
            case "sta":
                if self.cham_connected:
                    self.mqtt.publish(self.mqtt.topics.starter_get, mqtt_payload)
            case "reg":
                if self.cham_connected:
                    self.mqtt.publish(self.mqtt.topics.regulator_get, mqtt_payload)
            case "dec":
                if self.cham_connected:
                    self.mqtt.publish(self.mqtt.topics.RHT_graph, mqtt_payload, retain=False)
            
        if self.adv:
            event_val=json.dumps(payload)
        else:
            event_val=None
        self.event_queue.put((Bridge_EVs.UART_TRAFFIC_RECEIVE, event_val))

    def __open_uart(self, port):  
        try:
            if self.sm.is_open:
                return
            
            self.sm.port=port
            self.sm.open()

            self.sm.reset_input_buffer()
            self.sm.reset_output_buffer()

            self.uart_open_event.set()

            self.__write_uart(make_handshake_json(Handshake_codes.CON_REQ))
            self.event_queue.put((Bridge_EVs.UART_CON_STATUS, Bridge_UART_state.connecting))


        except serial.SerialException as e:
            self.event_queue.put((Bridge_EVs.ERROR, f"UART open: {e}"))
    
    def __close_uart(self, send_goodbye=False):
        try:
            self.uart_open_event.clear()
            if self.sm.is_open:
                if send_goodbye and self.cham_connected:
                    self.__write_uart(make_handshake_json(Handshake_codes.DIS_REQ))
                    time.sleep(0.05)
                    
                self.sm.reset_input_buffer()
                self.sm.reset_output_buffer()
                self.sm.close()

        except serial.SerialException as e:
            self.event_queue.put((Bridge_EVs.ERROR, f"UART close: {e}"))

        finally:
            self.mqtt.disconnect_mqtt()
            self.cham_connected=False
            self.cham_disconnecting=False
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
    def cmd_set_adv(self, adv:bool=False):
        self.command_queue.put((Bridge_CMDs.SET_ADV, adv))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="LCS Chamber Bridge (single channel, CLI only). For GUI run the whole app.")
    parser.add_argument("port", type=str, help="Serial port (e.g., /dev/ttyUSB0 or COM3)")
    parser.add_argument("--adv", action="store_true", help="Log raw UART & MQTT JSON traffic to console")
    parser.add_argument("--silent", action="store_true", help="Disable all forms of messages except errors")
    args=parser.parse_args()

    bridge=Bridge(channel_id=0)
    if args.adv:
        bridge.cmd_set_adv(True)

    silent=False
    if args.silent:
        silent=True

    if not silent:
        print(f"[*] starting on {args.port} (Ctrl+C to stop)")

    bridge.start()
    bridge.cmd_connect_chamber(args.port)

    try:
        while True:
            try:
                ev_type, val=bridge.event_queue.get(timeout=0.5)

                if not silent:
                    match ev_type:
                        case Bridge_EVs.ERROR:
                            print(f"[ERROR] {val}")
                        case Bridge_EVs.UART_CON_STATUS:
                            status_str=val.value if isinstance(val, Bridge_UART_state) else str(val)
                            print(f"[STATUS] Connection: {status_str}")
                        case Bridge_EVs.UART_CON_ID:
                            print(f"[INFO] Chamber ID: {val}")
                        case Bridge_EVs.UART_TRAFFIC_RECEIVE:
                            if val:
                                print(f"[UART RX] {val}")
                        case Bridge_EVs.MQTT_TRAFFIC_RECEIVE:
                            if val:
                                print(f"[MQTT RX] {val}")

                bridge.event_queue.task_done()
            except queue.Empty:
                pass

    except KeyboardInterrupt:
        bridge.cmd_disconnect_chamber()
        bridge.cmd_stop()
        time.sleep(0.5)
        if not silent:
            print("[*] Stopped")
