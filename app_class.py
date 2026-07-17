import customtkinter as ctk
from tkinter import PhotoImage
import bridge_class as bc
from serial.tools import list_ports
from types import SimpleNamespace
import queue
from datetime import datetime
import custom_Messagebox

DEFAULT_COM_MSG="Select COM"
MQTT_BROKER_HEADER=f"{bc.MQTT_BROKER_IP}:{bc.MQTT_BROKER_PORT}"

color_black="#000000"
color_bg="#333333"
color_text="#E1E1E1"
color_tile="#313131"
color_select="#8B0000"
color_green="#32cd32"
color_amber="#FFBF00"
color_tilein="#4D4D4D"

color_nconnected="#d10000"
color_connected="#32cd32"

COM_port_list=[DEFAULT_COM_MSG]

from pathlib import Path
app_base_path=Path(__file__).resolve().parent
app_icon_path_ico=f"{app_base_path}/icons/app.ico"

FONTS={}

class App_main:
    def __init__(self):
        ctk.set_appearance_mode("system")
        self.win=ctk.CTk()

        #self.win.geometry("600x400")
        self.win.resizable(False, False)   
        self.win.title("LCS Bridge")     
        self.win.protocol("WM_DELETE_WINDOW", self.handle_win_close)
        self.__set_app_icon()
        self.__setup_fonts()
        self.win.grid_columnconfigure(0, weight=1, uniform="panels")
        self.win.grid_columnconfigure(1, weight=1, uniform="panels")
        self.win.grid_rowconfigure(0, weight=0)#debug
        self.win.grid_rowconfigure(1, weight=0)#labels
        self.win.grid_rowconfigure(2, weight=1)#panel body
        self.panel=[
            Ctrl_panel(app=self, win=self.win, bridge=bc.Bridge(channel_id=0), panel_id=0),
            Ctrl_panel(app=self, win=self.win, bridge=bc.Bridge(channel_id=1), panel_id=1)
        ]
        self.__refresh_COM_event_cb()

        self.refresh_COM_btn=ctk.CTkButton(self.win, 
            text="Refresh COM", 
            font=FONTS["Small"], 
            command=self.__refresh_COM_event_cb, 
            width=40, 
            fg_color=color_tilein, 
            hover_color=color_select)
        self.refresh_COM_btn.grid(row=0, column=1, sticky="ne", padx=10, pady=(10, 0))

        self.adv_checkbox_var=ctk.StringVar(value='0')
        self.adv_checkbox=ctk.CTkCheckBox(self.win, 
            text="Advanced view",font=FONTS["Small"], 
            variable=self.adv_checkbox_var, 
            command=self.__adv_checkbox_event_cb, 
            hover_color=color_select,
            border_color=color_tilein)
        self.adv_checkbox.grid(row=0, column=0, sticky="nw", padx=10, pady=(10, 0))
        self.adv=True

    def __refresh_COM_event_cb(self):
        global COM_port_list 
        COM_port_list=[DEFAULT_COM_MSG]
        for port in list_ports.comports():
            COM_port_list.append(port.device)
            
        self.panel[0].COM_dropdown.configure(values=COM_port_list)
        self.panel[1].COM_dropdown.configure(values=COM_port_list)


    def __adv_checkbox_event_cb(self):
        self.adv=(self.adv_checkbox_var.get()=='1')
            
        self.panel[0].bridge.cmd_set_adv(self.adv)
        self.panel[1].bridge.cmd_set_adv(self.adv)
        self.panel[0].set_adv_visible(self.adv)
        self.panel[1].set_adv_visible(self.adv)
        self.win.update_idletasks()

    def __setup_fonts(self):
        FONTS["Heading"]=ctk.CTkFont(family="Tahoma", size=24, weight="bold")
        FONTS["Small"]=ctk.CTkFont(family="Tahoma", size=12)
        FONTS["Small_bold"]=ctk.CTkFont(family="Tahoma", size=12, weight="bold")
        FONTS["tiny"]=self.font_button=ctk.CTkFont(family="Tahoma", size=8)

    def __set_app_icon(self):
        try:
            self.win.wm_iconbitmap(app_icon_path_ico)

        except Exception as e:
            print(f"Exeption in icon setting: {e}")
    
    def handle_win_close(self):
        for panel in self.panel:
            panel.bridge.cmd_stop()
        self.win.destroy()

    def start(self):
        try:
            for panel in self.panel:
                panel.bridge.start()
            self.win.mainloop()
        except KeyboardInterrupt:
            print("Shutting from terminal")
            self.handle_win_close()

class Labels:
    chamber: ctk.CTkLabel
    status: ctk.CTkLabel
    MQTT_text: ctk.CTkLabel
    MQTT_topic: ctk.CTkLabel
    rec_time_header: ctk.CTkLabel
    MQTT_rec_time_text: ctk.CTkLabel
    MQTT_rec_time: ctk.CTkLabel
    UART_rec_time_text: ctk.CTkLabel
    UART_rec_time: ctk.CTkLabel
    traffic_from_chamber_text: ctk.CTkLabel
    traffic_from_server_text: ctk.CTkLabel


class Ctrl_panel:
    def __init__(self, app, win, bridge: bc.Bridge, panel_id: int):
        self.app=app
        self.win=win
        self.bridge=bridge

        self.bridge_state=bc.Bridge_UART_state.not_connected
        self.chamber_id="N/A"
        self.selected_COM=DEFAULT_COM_MSG
        self.MQTT_topic="N/A"
        
        self.last_UART_receive="N/A"
        self.last_MQTT_receive="N/A"

        self.panel_id=panel_id
        self.labels=Labels()

        self.connect_abort_timer=None

        self.labels.chamber=ctk.CTkLabel(self.win, text=f"Chamber {self.chamber_id}", font=FONTS["Heading"], text_color=color_text, height=34)
        self.labels.chamber.grid(row=1, column=self.panel_id, padx=15, pady=(10, 0), sticky="w")

        self.__setup_widgets()
        self.__setup_adv_widgets()
        self.set_adv_visible(False)
        self.__poll_event_queue()

    def __setup_widgets(self):
        self.body=ctk.CTkFrame(self.win, fg_color=color_tile)
        self.body.grid(row=2, column=self.panel_id, sticky="new", padx=10, pady=10)

        self.body.grid_rowconfigure(0, weight=0)#status
        self.body.grid_columnconfigure(0, weight=1)

        self.labels.status=ctk.CTkLabel(self.body, text=self.bridge_state.value, font=FONTS["Small_bold"], text_color=color_nconnected)
        self.labels.status.grid(row=0, column=0, columnspan=2, pady=5, padx=5, sticky="ew")

        self.body.grid_rowconfigure(1, weight=0)#COM port
        self.btn_connect=ctk.CTkButton(self.body, 
            text="Connect", 
            font=FONTS["Small"], 
            command=self.__connect_btn_event_callback,
            fg_color=color_tilein, 
            hover_color=color_select,
            state="disabled")
        self.btn_connect.grid(row=1, column=0, pady=5, padx=5, sticky="ew")

        self.COM_dropdown=ctk.CTkComboBox(self.body,
            values=COM_port_list,
            command=self.__COM_change_cb,
            state="readonly")
        self.COM_dropdown.set(DEFAULT_COM_MSG)
        self.COM_dropdown.grid(row=1, column=1, pady=5, padx=5, sticky="ew")

        #MQTT topic labels
        self.labels.MQTT_text=ctk.CTkLabel(self.body, text="MQTT topic:", font=FONTS["Small_bold"], text_color=color_text)
        self.labels.MQTT_text.grid(row=2, column=0, padx=10, pady=5, sticky="nw")

        self.labels.MQTT_topic=ctk.CTkLabel(self.body, text=f"{self.MQTT_topic}", font=FONTS["Small"], text_color=color_text)
        self.labels.MQTT_topic.grid(row=2, column=1, padx=10, pady=5, sticky="nw")

        #receive times
        self.body.grid_columnconfigure(0, weight=1)
        self.labels.rec_time_header=ctk.CTkLabel(self.body, text="Last traffic received", font=FONTS["Small_bold"], text_color=color_text)
        self.labels.rec_time_header.grid(row=3, column=0, padx=10, pady=(20,0), columnspan=2, sticky="new")
        

        self.labels.UART_rec_time_text=ctk.CTkLabel(self.body, text="from chamber:", font=FONTS["Small"], text_color=color_text)
        self.labels.UART_rec_time_text.grid(row=4, column=0, padx=10, pady=0, sticky="nw")
        self.labels.UART_rec_time=ctk.CTkLabel(self.body, text=self.last_UART_receive, font=FONTS["Small"], text_color=color_text)
        self.labels.UART_rec_time.grid(row=4, column=1, padx=10, pady=0, sticky="nw")

        self.labels.MQTT_rec_time_text=ctk.CTkLabel(self.body, text="from server:", font=FONTS["Small"], text_color=color_text)
        self.labels.MQTT_rec_time_text.grid(row=5, column=0, padx=10, pady=(0, 5), sticky="nw")
        self.labels.MQTT_rec_time=ctk.CTkLabel(self.body, text=self.last_MQTT_receive, font=FONTS["Small"], text_color=color_text)
        self.labels.MQTT_rec_time.grid(row=5, column=1, padx=10, pady=(0, 5), sticky="nw")
        
    def __setup_adv_widgets(self):
        self.adv_section=ctk.CTkFrame(self.win, fg_color=color_tile)
        self.adv_section.grid(row=3, column=self.panel_id, sticky="new", padx=10, pady=(0, 10))
        self.adv_section.grid_columnconfigure(0, weight=1)

        #from chamber
        self.labels.traffic_from_chamber_text=ctk.CTkLabel(self.adv_section, text="Traffic from chamber", font=FONTS["Small_bold"], text_color=color_text)
        self.labels.traffic_from_chamber_text.grid(row=0, column=0, sticky="nw", padx=10, pady=(5, 0))

        self.traffic_from_chamber_terminal=ctk.CTkTextbox(self.adv_section, font=FONTS["tiny"], height=100, text_color=color_text)
        self.traffic_from_chamber_terminal.grid(row=1, column=0, sticky="new", padx=10, pady=(0, 10))
        self.traffic_from_chamber_terminal.configure(state="disabled")

        #from server
        self.labels.traffic_from_server_text=ctk.CTkLabel(self.adv_section, text=f"Traffic from server ({MQTT_BROKER_HEADER})", font=FONTS["Small_bold"], text_color=color_text)
        self.labels.traffic_from_server_text.grid(row=2, column=0, sticky="nw", padx=10, pady=(5, 0))

        self.traffic_from_server_terminal=ctk.CTkTextbox(self.adv_section, font=FONTS["tiny"], height=100, text_color=color_text)
        self.traffic_from_server_terminal.grid(row=3, column=0, sticky="new", padx=10, pady=(0, 10))
        self.traffic_from_server_terminal.configure(state="disabled")

        

    def write_terminal_server(self, text: str):
        if text==None:
            return
        self.traffic_from_server_terminal.configure(state="normal")
        self.traffic_from_server_terminal.insert("end", f"MQTT) {text}\n")
        self.traffic_from_server_terminal.see("end")
        self.traffic_from_server_terminal.configure(state="disabled")

    def write_terminal_chamber(self, text: str, timestamp: str):
        if text==None:
            return
        self.traffic_from_chamber_terminal.configure(state="normal")
        self.traffic_from_chamber_terminal.insert("end", f"[{timestamp}]  {text}\n")

        content=self.traffic_from_chamber_terminal.get("1.0", "end-1c")
        line_count=len(content.splitlines())
        while line_count>30:
            self.traffic_from_chamber_terminal.delete("1.0", "2.0")
            line_count-=1
        
        _, bottom=self.traffic_from_chamber_terminal.yview()
        was_at_bottom=bottom>=0.9

        if was_at_bottom:
            self.traffic_from_chamber_terminal.see("end")
        self.traffic_from_chamber_terminal.configure(state="disabled")


    def set_adv_visible(self, visible=True):
        if visible:
            self.adv_section.grid()
        else:
            self.adv_section.grid_remove()

    def __COM_change_cb(self, choice):
        if self.bridge_state==bc.Bridge_UART_state.connected:
            self.bridge.cmd_disconnect_chamber()
        if choice==DEFAULT_COM_MSG:
            self.btn_connect.configure(state="disabled")
        else:
            self.btn_connect.configure(state="normal")
        self.selected_COM=choice

    def __connect_btn_event_callback(self):
        match self.bridge_state:
            case bc.Bridge_UART_state.connected:
                self.bridge.cmd_disconnect_chamber()

            case bc.Bridge_UART_state.not_connected:
                self.__attempt_connect()

            case bc.Bridge_UART_state.connecting:
                self.__abort_connect()
                
    def __abort_connect_timer_cb(self):
        self.__abort_connect()
        result=custom_Messagebox.show(self.win, "Connection Timeout", "I", 
            f"Connecting to {self.selected_COM} timed out", ("Retry", "Ok",))
        if result=="Ok":
            return
        elif result=="Retry":
            self.__attempt_connect()

    def __attempt_connect(self):
        self.bridge_state=bc.Bridge_UART_state.connecting
        self.btn_connect.configure(text="Abort")
        self.labels.status.configure(text=self.bridge_state.value)
        self.labels.status.configure(text_color=color_amber)
        self.bridge.cmd_connect_chamber(self.selected_COM)
        self.connect_abort_timer=self.win.after(2000, self.__abort_connect_timer_cb)

    def __abort_connect(self):
        self.bridge_state=bc.Bridge_UART_state.not_connected
        self.btn_connect.configure(text="Connect")
        self.labels.status.configure(text=self.bridge_state.value)
        self.labels.status.configure(text_color=color_nconnected)
        self.bridge.cmd_disconnect_chamber()

    def __poll_event_queue(self):
        while True:
            try:
                event, value=self.bridge.event_queue.get_nowait()
            except queue.Empty:
                break

            match event:
                case bc.Bridge_EVs.UART_CON_ID:
                    self.chamber_id=value
                    self.labels.chamber.configure(text=f"Chamber {self.chamber_id}")
                    self.MQTT_topic=f"/chambers/{self.chamber_id}/..."
                    self.labels.MQTT_topic.configure(text=self.MQTT_topic)
                case bc.Bridge_EVs.UART_CON_STATUS:
                    self.bridge_state=value
                    self.labels.status.configure(text=self.bridge_state.value)
                    self.win.after_cancel(self.connect_abort_timer)
                    match self.bridge_state:
                        case bc.Bridge_UART_state.connected:
                            self.btn_connect.configure(text="Disconect")
                            self.labels.status.configure(text_color=color_connected)
                        case bc.Bridge_UART_state.not_connected:
                            self.btn_connect.configure(text="Connect")
                            self.labels.status.configure(text_color=color_nconnected)
                        case bc.Bridge_UART_state.connecting:
                            self.btn_connect.configure(text="Connecting")
                            self.labels.status.configure(text_color=color_text)

                case bc.Bridge_EVs.UART_TRAFFIC_RECEIVE:
                    self.last_UART_receive=datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    self.labels.UART_rec_time.configure(text=self.last_UART_receive)
                    if self.app.adv:
                        self.write_terminal_chamber(value, timestamp=self.last_UART_receive)

                case bc.Bridge_EVs.MQTT_TRAFFIC_RECEIVE:
                    self.last_MQTT_receive=datetime.now().strftime("%H:%M:%S.%f")[:-3]

                case bc.Bridge_EVs.ERROR:
                    custom_Messagebox.show(parent=self.win, title=f"Bridge{self.panel_id} error", type='E', message=value, buttons=("OK",))

            self.bridge.event_queue.task_done()

        self.win.after(100, self.__poll_event_queue)