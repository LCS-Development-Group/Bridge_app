import customtkinter as ctk
from tkinter import PhotoImage, messagebox
from bridge_class import Bridge, Bridge_CMDs, Bridge_EVs, Bridge_UART_state
from serial.tools import list_ports
from types import SimpleNamespace
import queue

DEFAULT_COM_MSG="Select COM"

app_icon_path="./Icon48x48.png"
color_black="#000000"
color_bg="#333333"
color_text="#E1E1E1"
color_tile="#313131"
color_select="#8B0000"
color_green="#32cd32"
color_tilein="#4D4D4D"

color_nconnected="#d10000"
color_connected="#32cd32"

COM_port_list=[DEFAULT_COM_MSG]
app_icon_path_ico="./icons/app.ico"

FONTS={}

class App_main:
    def __init__(self):
        ctk.set_appearance_mode("system")
        self.win=ctk.CTk()

        self.win.geometry("600x400")
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
            Ctrl_panel(app=self, win=self.win, bridge=Bridge(channel_id=0), panel_id=0),
            Ctrl_panel(app=self, win=self.win, bridge=Bridge(channel_id=1), panel_id=1)
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

    def __refresh_COM_event_cb(self):
        global COM_port_list 
        COM_port_list=[DEFAULT_COM_MSG]
        for port in list_ports.comports():
            COM_port_list.append(port.device)
            
        self.panel[0].COM_dropdown.configure(values=COM_port_list)
        self.panel[1].COM_dropdown.configure(values=COM_port_list)


    def __adv_checkbox_event_cb(self):
        if self.adv_checkbox_var.get()=='1':
            print("adv enabled")
        else:
            print("adv disabled")

    def __setup_fonts(self):
        FONTS["Heading"]=ctk.CTkFont(family="Tahoma", size=24, weight="bold")
        FONTS["Small"]=ctk.CTkFont(family="Tahoma", size=12)
        FONTS["Small_bold"]=ctk.CTkFont(family="Tahoma", size=12, weight="bold")

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

class Btns:
    connected: ctk.CTkButton

class Ctrl_panel:
    def __init__(self, app, win, bridge: Bridge, panel_id: int):
        self.app=app
        self.win=win
        self.bridge=bridge

        self.bridge_state=Bridge_UART_state.not_connected
        self.chamber_id="N/A"
        self.selected_COM=DEFAULT_COM_MSG

        self.panel_id=panel_id
        self.labels=Labels()
        self.btns=Btns()
        
        self.__setup_widgets()

    def __setup_widgets(self):

        self.labels.chamber=ctk.CTkLabel(self.win, text=f"Chamber {self.chamber_id}", font=FONTS["Heading"], text_color=color_text, height=34)
        self.labels.chamber.grid(row=1, column=self.panel_id, padx=15, pady=(10, 0), sticky="w")

        self.body=ctk.CTkFrame(self.win, fg_color=color_tile)
        self.body.grid(row=2, column=self.panel_id, sticky="nsew", padx=10, pady=10)

        self.body.grid_rowconfigure(0, weight=0)#status
        self.body.grid_columnconfigure(0, weight=1)

        self.labels.status=ctk.CTkLabel(self.body, text=self.bridge_state.value, font=FONTS["Small_bold"], text_color=color_nconnected)
        self.labels.status.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")

        self.body.grid_rowconfigure(1, weight=0)#COM port
        self.btns.connected=ctk.CTkButton(self.body, 
            text="Connect", 
            font=FONTS["Small"], 
            command=self.__connect_btn_event_callback,
            fg_color=color_tilein, 
            hover_color=color_select,
            state="disabled")
        self.btns.connected.grid(row=1, column=0, pady=5, padx=5, sticky="ew")

        self.COM_dropdown=ctk.CTkComboBox(self.body,
            values=COM_port_list,
            command=self.__COM_change_cb,
            state="readonly")
        self.COM_dropdown.set(DEFAULT_COM_MSG)
        self.COM_dropdown.grid(row=1, column=1, pady=5, padx=5, sticky="ew")

        self.__poll_event_queue()
        
    def __COM_change_cb(self, choice):
        if self.bridge_state==Bridge_UART_state.connected:
            self.bridge.cmd_disconnect_chamber()
        if choice==DEFAULT_COM_MSG:
            self.btns.connected.configure(state="disabled")
        else:
            self.btns.connected.configure(state="normal")
        self.selected_COM=choice

    def __connect_btn_event_callback(self):

        match self.bridge_state:
            case Bridge_UART_state.connected:
                self.bridge.cmd_disconnect_chamber()
            case Bridge_UART_state.not_connected:
                self.bridge.cmd_connect_chamber(self.selected_COM)
            case Bridge_UART_state.connecting:
                pass #not sure if anything beyond nothing

    def __poll_event_queue(self):
        while True:
            try:
                event, value=self.bridge.event_queue.get_nowait()
            except queue.Empty:
                break

            match event:
                case Bridge_EVs.UART_CON_ID:
                    self.chamber_id=value
                    self.labels.chamber.configure(text=f"Chamber {self.chamber_id}")
                case Bridge_EVs.UART_CON_STATUS:
                    self.bridge_state=value
                    self.labels.status.configure(text=self.bridge_state.value)
                    match self.bridge_state:
                        case Bridge_UART_state.connected:
                            self.btns.connected.configure(text="Disconect")
                            self.labels.status.configure(text_color=color_connected)
                        case Bridge_UART_state.not_connected:
                            self.btns.connected.configure(text="Connect")
                            self.labels.status.configure(text_color=color_nconnected)
                        case Bridge_UART_state.connecting:
                            self.btns.connected.configure(text="Connect")
                            self.labels.status.configure(text_color=color_text)

                case Bridge_EVs.ERROR:
                    #print(f"[bridge{self.panel_id}] {value}")
                    messagebox.showerror(f"Bridge{self.panel_id} error", value)

            self.bridge.event_queue.task_done()

        self.win.after(100, self.__poll_event_queue)