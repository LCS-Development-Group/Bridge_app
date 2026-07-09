import customtkinter as ctk
from tkinter import PhotoImage
from bridge_class import Bridge, default_COM_msg, conn_state, nconn_state
from serial.tools import list_ports
from types import SimpleNamespace

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

COM_port_list=[default_COM_msg, "option 2"]
app_icon_path_ico="./Icon128.ico"

FONTS={}

class App_main:
    def __init__(self, bridges: list[Bridge]):
        ctk.set_appearance_mode("system")
        self.win=ctk.CTk()

        self.win.geometry("600x400")
        self.win.resizable(False, False)   
        self.win.title("LCS Bridge")     
        self.win.protocol("WM_DELETE_WINDOW", self.handle_win_close)
        self.set_app_icon()
        self.setup_fonts()

        self.win.grid_columnconfigure(0, weight=1, uniform="panels")
        self.win.grid_columnconfigure(1, weight=1, uniform="panels")
        self.win.grid_rowconfigure(0, weight=0)#debug
        self.win.grid_rowconfigure(1, weight=0)#labels
        self.win.grid_rowconfigure(2, weight=1)#panel body
        self.panel=[
            Ctrl_panel(app=self, win=self.win, bridge=bridges[0], panel_id=0),
            Ctrl_panel(app=self, win=self.win, bridge=bridges[1], panel_id=1)
        ]

        self.refresh_COM_btn=ctk.CTkButton(self.win, 
            text="Refresh COM", 
            font=FONTS["Small"], 
            command=self.refresh_COM_event_cb, 
            width=40, 
            fg_color=color_tilein, 
            hover_color=color_select)
        self.refresh_COM_btn.grid(row=0, column=1, sticky="ne", padx=10, pady=(10, 0))

        self.adv_checkbox_var=ctk.StringVar(value='0')
        self.adv_checkbox=ctk.CTkCheckBox(self.win, 
            text="Advanced view",font=FONTS["Small"], 
            variable=self.adv_checkbox_var, 
            command=self.adv_checkbox_event_cb, 
            hover_color=color_select,
            border_color=color_tilein)
        self.adv_checkbox.grid(row=0, column=0, sticky="nw", padx=10, pady=(10, 0))

    def refresh_COM_event_cb(self):
        print("com refreshed")

    def adv_checkbox_event_cb(self):
        if self.adv_checkbox_var.get()=='1':
            print("adv enabled")
        else:
            print("adv disabled")



    def setup_fonts(self):
        FONTS["Heading"]=ctk.CTkFont(family="Tahoma", size=24, weight="bold")
        FONTS["Small"]=ctk.CTkFont(family="Tahoma", size=12)
        FONTS["Small_bold"]=ctk.CTkFont(family="Tahoma", size=12, weight="bold")

    def set_app_icon(self):
        try:
            self.win.wm_iconbitmap(app_icon_path_ico)

        except Exception as e:
            print(f"Exeption in icon setting: {e}")
    
    def handle_win_close(self):
        self.win.destroy()

    def start(self):
        try:
            self.win.mainloop()
        except KeyboardInterrupt:
            print("Shutting from terminal")
            self.win.destroy()

class Labels:
    chamber: ctk.CTkLabel
    status: ctk.CTkLabel

class Btns:
    connected: ctk.CTkButton

class Ctrl_panel:
    def __init__(self, app, win, bridge, panel_id):
        self.app=app
        self.win=win
        self.bridge=bridge
        self.panel_id=panel_id
        self.labels=Labels()
        self.btns=Btns()
        
        self.setup_widgets()

    def setup_widgets(self):

        self.labels.chamber=ctk.CTkLabel(self.win, text=f"Chamber {self.bridge.chamber_id}", font=FONTS["Heading"], text_color=color_text, height=34)
        self.labels.chamber.grid(row=1, column=self.panel_id, padx=15, pady=(10, 0), sticky="w")

        self.body=ctk.CTkFrame(self.win, fg_color=color_tile)
        self.body.grid(row=2, column=self.panel_id, sticky="nsew", padx=10, pady=10)

        self.body.grid_rowconfigure(0, weight=0)#status
        self.body.grid_columnconfigure(0, weight=1)

        self.labels.status=ctk.CTkLabel(self.body, text=self.bridge.status, font=FONTS["Small_bold"], text_color=color_nconnected)
        self.labels.status.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")

        self.body.grid_rowconfigure(1, weight=0)#COM port
        self.btns.connected=ctk.CTkButton(self.body, 
            text="Connect", 
            font=FONTS["Small"], 
            command=self.connect_btn_event_callback,
            fg_color=color_tilein, 
            hover_color=color_select,
            state="disabled")
        self.btns.connected.grid(row=1, column=0, pady=5, padx=5, sticky="ew")

        self.COM_dropdown=ctk.CTkComboBox(self.body,
            values=COM_port_list,
            command=self.COM_change_cb,
            state="readonly")
        self.COM_dropdown.set(default_COM_msg)
        self.COM_dropdown.grid(row=1, column=1, pady=5, padx=5, sticky="ew")
        
    def COM_change_cb(self, choice):
        if self.bridge.status==conn_state:
            self.bridge.disconnect()
            if self.bridge.status==nconn_state:#confirming
                self.btns.connected.configure(text="Connect")
                self.labels.status.configure(text=self.bridge.status, text_color=color_nconnected)

        if choice==default_COM_msg:
            self.btns.connected.configure(state="disabled")
        else:
            self.btns.connected.configure(state="normal")
        self.bridge.selected_COM=choice

    def connect_btn_event_callback(self):

        if self.bridge.status==conn_state:
            self.bridge.disconnect()
        elif self.bridge.status==nconn_state:
            self.bridge.connect()
        else:
            print(f"unknown status: {self.bridge.status}")

        if self.bridge.status==conn_state:#confirming
            self.btns.connected.configure(text="Disconect")
            self.labels.status.configure(text=self.bridge.status, text_color=color_connected)
        elif self.bridge.status==nconn_state:#confirming
            self.btns.connected.configure(text="Connect")
            self.labels.status.configure(text=self.bridge.status, text_color=color_nconnected)
        else:
            print("connection in superposition")
            

