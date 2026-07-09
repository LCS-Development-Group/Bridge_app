import random
default_COM_msg="Select COM"
conn_state="Connected"
nconn_state="Not connected"

class Bridge:
    def __init__(self):
        self.chamber_id="N/A"
        self.status=nconn_state
        
        self.selected_COM=default_COM_msg

    def connect(self):
        self.status=conn_state
        print("connect")
        self.chamber_id=random.randrange(0, 5, 1)
        
    def disconnect(self):
        self.chamber_id="N/A"
        print("disconnect")
        self.status=nconn_state
        self.selected_COM=default_COM_msg

        