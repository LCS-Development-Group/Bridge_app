import random
default_COM_msg="Select COM"

class Bridge:
    def __init__(self):
        self.chamber_id="N/A"
        self.is_connected=False
        self.selected_COM=default_COM_msg

    def connect(self):
        self.is_connected=True
        self.chamber_id=random.randrange(0, 5, 1)
        
    def disconnect(self):
        self.chamber_id="N/A"
        self.is_connected=False
        self.selected_COM=default_COM_msg

        