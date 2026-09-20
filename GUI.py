import customtkinter as ctk
import bridge as bc
from serial.tools import list_ports
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
COM_exclude_VID=[None, 0x303a]


from pathlib import Path
import sys
if getattr(sys, "frozen", False):
    app_base_path=Path(sys._MEIPASS) # compiled .exe
else:
    app_base_path=Path(__file__).resolve().parent # stanalone .pyw

app_icon_path_ico=str(app_base_path/"icons"/"app.ico")
adv_icon_path_ico=str(app_base_path/"icons"/"info.ico")
FONTS={}

def set_window_icon(window, icon_path):
    import os
    if not os.path.exists(icon_path):
        return

    try:
            window.wm_iconbitmap(icon_path)
    except Exception:
        pass

    
class App_main:
    def __init__(self):
        ctk.set_appearance_mode("system")
        
        '''Main window'''
        self.win=ctk.CTk()
        self.win.resizable(False, False)    
        self.win.title("LCS Bridge")     
        self.win.protocol("WM_DELETE_WINDOW", self.handle_win_close)

        set_window_icon(self.win, app_icon_path_ico)
    
        self.win.grid_columnconfigure(0, weight=1, uniform="panels")
        self.win.grid_columnconfigure(1, weight=1, uniform="panels")
        self.win.grid_rowconfigure(0, weight=0)#debug
        self.win.grid_rowconfigure(1, weight=0)#labels
        self.win.grid_rowconfigure(2, weight=1)#panel body

        '''Advanced window'''
        self.adv_win=ctk.CTkToplevel(self.win)
        self.adv_win.withdraw()
        self.adv_win.resizable(True, False)    
        self.adv_win.title("Advanced Info")
        self.adv_win.protocol("WM_DELETE_WINDOW", self.__handle_adv_win_close)

        set_window_icon(self.adv_win, adv_icon_path_ico)

        self.adv_win.grid_columnconfigure(0, weight=1, uniform="panels")
        self.adv_win.grid_columnconfigure(1, weight=1, uniform="panels")
        self.adv_win.grid_rowconfigure(0, weight=0)#labels
        self.adv_win.grid_rowconfigure(1, weight=1)#panel body

        self.__setup_fonts()

        '''Pannels'''
        self.panel=[
            Ctrl_panel(app=self, win=self.win, adv_win=self.adv_win, bridge=bc.Bridge(channel_id=0), panel_id=0),
            Ctrl_panel(app=self, win=self.win, adv_win=self.adv_win, bridge=bc.Bridge(channel_id=1), panel_id=1)
        ]
        self.__adv_set_enabled(False)

        self.__refresh_COM_event_cb()
        self.refresh_COM_btn=ctk.CTkButton(self.win, 
            text="Refresh COM", 
            font=FONTS["Small"], 
            command=self.__refresh_COM_event_cb, 
            width=40, 
            fg_color=color_tilein, 
            hover_color=color_select)
        self.refresh_COM_btn.grid(row=0, column=1, sticky="ne", padx=10, pady=(10, 0))

        self.adv_checkbox_var=ctk.BooleanVar(value=False)
        self.adv_checkbox=ctk.CTkCheckBox(self.win, 
            text="Advanced view",font=FONTS["Small"], 
            variable=self.adv_checkbox_var, 
            command=self.__adv_checkbox_event_cb, 
            hover_color=color_select,
            border_color=color_tilein)
        self.adv_checkbox.grid(row=0, column=0, sticky="nw", padx=10, pady=(10, 0))

    def __refresh_COM_event_cb(self):
        global COM_port_list 
        COM_port_list=[DEFAULT_COM_MSG]
        for port in list_ports.comports():
            if port.vid in COM_exclude_VID:
                continue #skip virtual ports, direct JTAG, motherboard channels etc.
            COM_port_list.append(port.device)
            
        self.panel[0].COM_dropdown.configure(values=COM_port_list)
        self.panel[1].COM_dropdown.configure(values=COM_port_list)


    def __adv_checkbox_event_cb(self):
        self.__adv_set_enabled(self.adv_checkbox_var.get()==True)
        
    def __adv_set_enabled(self, enabled=False):
        self.adv_enabled=enabled
        self.panel[0].set_adv_enabled(self.adv_enabled)
        self.panel[1].set_adv_enabled(self.adv_enabled)
        
        if self.adv_win.winfo_exists():
            if enabled:
                self.adv_win.deiconify()
                self.adv_win.lift()
                self.adv_win.attributes('-topmost', True)
                self.adv_win.after(100, lambda: self.adv_win.attributes('-topmost', False))
                self.adv_win.focus_force()
            else:
                self.adv_win.withdraw()

        self.win.update_idletasks()

    def __setup_fonts(self):
        FONTS["Heading"]=ctk.CTkFont(family="Tahoma", size=24, weight="bold")
        FONTS["Small"]=ctk.CTkFont(family="Tahoma", size=12)
        FONTS["Small_bold"]=ctk.CTkFont(family="Tahoma", size=12, weight="bold")
        FONTS["tiny"]=self.font_button=ctk.CTkFont(family="Tahoma", size=8)
        
    
    def handle_win_close(self):
        for panel in self.panel:
            panel.bridge.cmd_stop()
        self.adv_win.destroy()
        self.win.destroy()

    def __handle_adv_win_close(self):
        self.adv_checkbox_var.set(False)
        self.__adv_set_enabled(False)

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
    def __init__(self, app, win, adv_win, bridge: bc.Bridge, panel_id: int):
        self.app=app
        self.win=win
        self.adv_win=adv_win
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
        self.__poll_event_queue()

    def set_adv_enabled(self, adv_enabled: bool=False):
        self.bridge.cmd_set_adv(adv=adv_enabled)

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

        self.adv_label=ctk.CTkLabel(self.adv_win, text=f"Chamber {self.chamber_id}", font=FONTS["Heading"], text_color=color_text, height=34)
        self.adv_label.grid(row=0, column=self.panel_id, padx=15, pady=(10, 0), sticky="w")

        self.adv_section=ctk.CTkFrame(self.adv_win, fg_color=color_tile)
        self.adv_section.grid(row=1, column=self.panel_id, sticky="new", padx=10, pady=10)
        self.adv_section.grid_columnconfigure(0, weight=1)

        #from chamber
        self.labels.traffic_from_chamber_text=ctk.CTkLabel(self.adv_section, text="Traffic from chamber", font=FONTS["Small_bold"], text_color=color_text)
        self.labels.traffic_from_chamber_text.grid(row=0, column=0, sticky="nw", padx=10, pady=(5, 0))

        self.traffic_from_chamber_terminal=ctk.CTkTextbox(self.adv_section, font=FONTS["tiny"], height=150, width=400, text_color=color_text)
        self.traffic_from_chamber_terminal.grid(row=1, column=0, sticky="new", padx=10, pady=(0, 10))
        self.traffic_from_chamber_terminal.configure(state="disabled")

        #from server
        self.labels.traffic_from_server_text=ctk.CTkLabel(self.adv_section, text=f"Traffic from server ({MQTT_BROKER_HEADER})", font=FONTS["Small_bold"], text_color=color_text)
        self.labels.traffic_from_server_text.grid(row=2, column=0, sticky="nw", padx=10, pady=(5, 0))

        self.traffic_from_server_terminal=ctk.CTkTextbox(self.adv_section, font=FONTS["tiny"], height=150, width=400, text_color=color_text)
        self.traffic_from_server_terminal.grid(row=3, column=0, sticky="new", padx=10, pady=(0, 10))
        self.traffic_from_server_terminal.configure(state="disabled")

    def write_terminal_server(self, text: str, timestamp: str):
        if text==None:
            return
        self.traffic_from_server_terminal.configure(state="normal")
        self.traffic_from_server_terminal.insert("end", f"[{timestamp}] {text}\n")

        content=self.traffic_from_server_terminal.get("1.0", "end-1c")
        line_count=len(content.splitlines())
        while line_count>30:
            self.traffic_from_server_terminal.delete("1.0", "2.0")
            line_count-=1
        
        _, bottom=self.traffic_from_server_terminal.yview()
        was_at_bottom=bottom>=0.9

        if was_at_bottom:
            self.traffic_from_server_terminal.see("end")
        self.traffic_from_server_terminal.configure(state="disabled")

    def write_terminal_chamber(self, text: str, timestamp: str):
        if text==None:
            return
        self.traffic_from_chamber_terminal.configure(state="normal")
        self.traffic_from_chamber_terminal.insert("end", f"[{timestamp}] {text}\n")

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

    def __COM_change_cb(self, choice):
        if self.bridge_state==bc.Bridge_UART_state.connected:
            self.bridge.cmd_disconnect_chamber()
        if choice==DEFAULT_COM_MSG:
            self.btn_connect.configure(state="disabled")
        else:
            self.btn_connect.configure(state="normal")
        self.selected_COM=choice

    def __connect_btn_event_callback(self):
        self.connect_abort_timer=None
        match self.bridge_state:
            case bc.Bridge_UART_state.connected:
                self.bridge.cmd_disconnect_chamber()

            case bc.Bridge_UART_state.not_connected:
                self.__attempt_connect()

            case bc.Bridge_UART_state.connecting:
                self.__abort_connect()
                
    def __abort_connect_timer_cb(self):
        self.__abort_connect()
        result=custom_Messagebox.show(self.win, "Connection Timeout", "E", 
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

    def __abort_connect(self, send_disconect_cmd=True):
        self.bridge_state=bc.Bridge_UART_state.not_connected
        self.btn_connect.configure(text="Connect")
        self.labels.status.configure(text=self.bridge_state.value)
        self.labels.status.configure(text_color=color_nconnected)
        self.__cancel_abort_timer()
        if send_disconect_cmd:
            self.bridge.cmd_disconnect_chamber()

    def __cancel_abort_timer(self):
        if self.connect_abort_timer is not None:
            self.win.after_cancel(self.connect_abort_timer)
            self.connect_abort_timer=None

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
                    self.adv_label.configure(text=f"Chamber {self.chamber_id}")
                    self.MQTT_topic=f"/chambers/{self.chamber_id}/..."
                    self.labels.MQTT_topic.configure(text=self.MQTT_topic)
                case bc.Bridge_EVs.UART_CON_STATUS:
                    self.bridge_state=value
                    self.labels.status.configure(text=self.bridge_state.value)

                    match self.bridge_state:
                        case bc.Bridge_UART_state.connected:
                            self.__cancel_abort_timer()
                            self.btn_connect.configure(text="Disconect")
                            self.labels.status.configure(text_color=color_connected)
                        case bc.Bridge_UART_state.not_connected:
                            self.btn_connect.configure(text="Connect")
                            self.labels.status.configure(text_color=color_nconnected)
                        case bc.Bridge_UART_state.connecting:
                            pass #attemp, connect handles it

                case bc.Bridge_EVs.UART_TRAFFIC_RECEIVE:
                    self.last_UART_receive=datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    self.labels.UART_rec_time.configure(text=self.last_UART_receive)
                    if self.app.adv_enabled:
                        self.write_terminal_chamber(value, timestamp=self.last_UART_receive)

                case bc.Bridge_EVs.MQTT_TRAFFIC_RECEIVE:
                    self.last_MQTT_receive=datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    if self.app.adv_enabled:
                        self.write_terminal_server(value, timestamp=self.last_UART_receive)

                case bc.Bridge_EVs.ERROR:
                    self.__cancel_abort_timer()
                    self.__abort_connect()
                    custom_Messagebox.show(parent=self.win, title=f"Bridge{self.panel_id} error", type='E', message=value, buttons=("OK",))

            self.bridge.event_queue.task_done()

        self.win.after(100, self.__poll_event_queue)