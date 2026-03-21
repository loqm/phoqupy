# nanomax_stage.py

import time
import numpy as np
from mdt69x import Controller

class NanoMaxStage:
    def __init__(self, port="COM4"):
        self.con = Controller(port)
        print(f"Connected to: {self.con.get_id()}")
        print(f"Voltage limit: {self.con.get_switch_limit():.4f} V")

    def center_stage(self, start, end):
        center = (end - start) / 2
        self.con.set_xyz_voltage(center, center, 0.0)

    def move_to(self, x=None, y=None, z=None):
        if x is not None:
            self.con.set_x_voltage(x)
        if y is not None:
            self.con.set_y_voltage(y)
        if z is not None:
            self.con.set_z_voltage(z)

    def shutdown(self):
        x = self.con.get_x_voltage()
        y = self.con.get_y_voltage()
        x_pos = np.linspace(start=x,stop=0,num=10)
        y_pos = np.linspace(start=y,stop=0,num=10)
        for i in x_pos:
            self.con.set_x_voltage(i)
            time.sleep(0.5)
        for i in y_pos:
            self.con.set_y_voltage(i)
            time.sleep(0.5)    
        self.con.set_xyz_voltage(0.0, 0.0, 0.0)
        self.con.close()
    
    def close(self):
        self.con.set_xyz_voltage(0.0, 0.0, 0.0)
        self.con.close()
        print("NanoMAX Stage shut down.")