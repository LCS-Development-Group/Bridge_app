import customtkinter as ctk

'''
[USAGE]

    result=show(parent, title: str, type: char, message: str, buttons=(str, ...,))

(arguments)
    parent - parrent widget, ie. ctk windo
    title - text displayed on the top bar
    type - defines the icon, possible are 'Q' (question), 'E' (error), 'W' (warning), 'I' (Info), or None (default CTK icon)
    message - the main popup message
    buttons - tupple of string defining the button texts. Always end with trailing colon
    result - contains the text of the pressed button. Closing the window returns None
'''


color_text="#E1E1E1"
color_select="#8B0000"
color_tilein="#4D4D4D"

'''icons'''
from pathlib import Path
app_base_path=Path(__file__).resolve().parent
ICON_QUESTION=f"{app_base_path}/icons/question.ico"
ICON_WARNING=f"{app_base_path}/icons/warning.ico"
ICON_ERROR=f"{app_base_path}/icons/error.ico"
ICON_INFO=f"{app_base_path}/icons/info.ico"

'''credit
https://www.iconarchive.com/show/button-icons-by-hopstarter/Button-Help-icon.html
https://www.iconarchive.com/show/button-icons-by-hopstarter/Button-Info-icon.html
https://www.iconarchive.com/show/soft-scraps-icons-by-hopstarter/Button-Warning-icon.html
https://www.iconarchive.com/show/sleek-xp-software-icons-by-hopstarter/Windows-Close-Program-icon.html
'''

class Messagebox(ctk.CTkToplevel):
    def __init__(
        self,
        parent, 
        title="no title",
        type=None,
        message="no msg",
        buttons=("OK",),
        width=360,
        height=120
    ):
        super().__init__(parent)
        self.result=None
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.font_button=ctk.CTkFont(family="Tahoma", size=10, weight="bold")
        self.font_big=ctk.CTkFont(family="Tahoma", size=12)

        icon=None
        match type:
            case 'Q':
                icon=ICON_QUESTION
            case 'I':
                icon=ICON_INFO
            case 'E':
                icon=ICON_ERROR
            case 'W':
                icon=ICON_WARNING
        if icon:
            self.after(200, lambda: self.iconbitmap(icon))
        

        msg_label=ctk.CTkLabel(self, text=message, wraplength=width-40, justify="left", font=self.font_big, text_color=color_text)
        msg_label.grid(row=0, column=0, padx=10, pady=(5, 20), sticky="nw")
        btn_frame=ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="e")

        for column, button in enumerate(buttons):
            #btn_frame.columnconfigure(column, weight=1)
            btn=ctk.CTkButton(btn_frame, width=90, text=button, font=self.font_button, 
                fg_color=color_tilein, text_color=color_text, hover_color=color_select,
                command=lambda value=button: self.__close(value))
            btn.grid(row=0, column=column, padx=5, pady=(0,5))

        self.protocol("WM_DELETE_WINDOW", lambda: self.__close(None))    
        self.update_idletasks()
        self.grab_set()
        self.focus_force()
        self.bind("<Unmap>", self.__prevent_minimize)


    def __close(self, result):
        self.result=result
        self.grab_release()
        self.destroy()
        pass

    def __prevent_minimize(self, event=None):
        if self.state()=="iconic":
            self.deiconify()

def show(parent, 
        title="no title",
        type=None,
        message="no msg",
        buttons=("OK",)):
    popup=Messagebox(parent=parent, title=title, type=type, message=message, buttons=buttons)
    parent.wait_window(popup)
    return popup.result

if __name__=="__main__":
    try:
        print("Running this file as \"__main__\" is for testing only")
        ctk.set_appearance_mode("system")

        #print(f"Set theme to: \"{ctk.get_appearance_mode()}\"")
        window=ctk.CTk()

        result=show(parent=window, title="", type='Q', message="test msg", buttons=("OK", "Cancel",))
        print(f"result: {result}")

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"Encountered exception: {e}")

    finally:
        window.destroy()