import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from bridge_class import Bridge, default_COM_msg
from serial.tools import list_ports

app_icon_path="./Icon48x48.png"
color_black="#000000"
color_bg="#333333"
color_text="#E1E1E1"
color_tile="#333333"
color_select="#8B0000"
color_green="#32cd32"
color_tilein="#4D4D4D"

COM_port_list=[default_COM_msg]


class App_main:
    def __init__(self, bridges: list[Bridge]):
        self.win=tk.Tk()

        self.setup_styles()
        self.win.geometry("600x200")
        self.win.resizable(False, False)   
        self.win.title("LCS Bridge")     
        self.set_app_icon()
        self.win.protocol("WM_DELETE_WINDOW", self.handle_win_close)

        self.win.grid_columnconfigure(0, weight=1, uniform="panels")
        self.win.grid_columnconfigure(1, weight=1, uniform="panels")
        self.win.grid_rowconfigure(0, weight=1)
        self.panel=[
            Ctrl_panel(app=self, win=self.win, bridge=bridges[0], panel_id=0),
            Ctrl_panel(app=self, win=self.win, bridge=bridges[1], panel_id=1)
        ]


    def setup_styles(self):
        combobox_style=ttk.Style()
        combobox_style.theme_use("vista")
        combobox_style.configure(
            "Dark.TCombobox",
            foreground=color_black,
            font=("Tahoma", 12))

    def set_app_icon(self):
        try:
            self.app_icon_img=tk.PhotoImage(file=app_icon_path)
            self.win.iconphoto(True, self.app_icon_img)

        except Exception as e:
            print(f"Exeption in icon setting: {e}")
    
    def handle_win_close(self):
        self.win.destroy()

    def start(self):
        self.win.mainloop()


class Ctrl_panel:
    def __init__(self, app, win, bridge, panel_id):
        self.app=app
        self.win=win
        self.bridge=bridge
        self.panel_id=panel_id
        

        self.body=tk.Frame(
            self.win,
            bg=color_bg,
            padx=10,
            pady=0,
        )
        self.body.grid(row=0, column=panel_id, sticky="nsew", padx=0, pady=0)

        self.chamber_label=tk.Label(
            self.body,
            text=f"Chamber {self.bridge.chamber_id}",
            font=("Tahoma", 24, "bold"),
            bg=color_bg,
            fg=color_text,
            relief="flat",
            width=11,
            pady=10,
        )
        self.chamber_label.pack()

        self.connect_btn=tk.Button(
            self.body,
            text="Connect",
            font=("Tahoma", 12, "bold"),
            bg=color_tilein,
            fg=color_text,
            activebackground=color_tilein,
            activeforeground=color_text,
            width=10,
            command=self.handle_connect_button
        )
        self.connect_btn.pack()
        self.selected_COM_stringvar=tk.StringVar(value=self.bridge.selected_COM)
        self.COMlist=ttk.Combobox(
            self.body, 
            values=COM_port_list,
            textvariable=self.selected_COM_stringvar,
            font=("Tahoma", 12),
            width=11,
            style="Dark.TCombobox"
        )
        self.COMlist.pack()
        self.COMlist.bind("<<ComboboxSelected>>", self.handle_COM_change)

        self.COM_refresh_btn=tk.Button(
            self.body,
            text="Refresh COM ports",
            font=("Tahoma", 8),
            bg=color_tilein,
            fg=color_text,
            activebackground=color_tilein,
            activeforeground=color_text,
            width=15,
            command=self.refresh_com_list
        )
        self.COM_refresh_btn.pack()

    def handle_COM_change(self, *args):
        if self.bridge.is_connected==True:
            self.handle_connect_button()
        self.bridge.selected_COM=self.selected_COM_stringvar.get()

    def refresh_com_list(self):
        global COM_port_list
        COM_port_list=[default_COM_msg]

        for port in list_ports.comports():
            if "CH343" in port.description:
                COM_port_list.append(port.device)

        self.app.panel[0].refresh_dropdown()
        self.app.panel[1].refresh_dropdown()

    def refresh_dropdown(self):
        self.COMlist.configure(values=COM_port_list)

    def handle_connect_button(self):
        if self.bridge.is_connected==False:
            self.bridge.connect()
            if self.bridge.is_connected==True:
                self.connect_btn.configure(text="Disconnect")
        else:
            self.bridge.disconnect()
            if self.bridge.is_connected==False:
                self.connect_btn.configure(text="Connect")

        self.chamber_label.configure(text=f"Chamber {self.bridge.chamber_id}")
