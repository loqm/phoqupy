# -*- coding: utf-8 -*-
"""
Created on Thu Oct 01 11:52:44 2015

@author: hera
"""
from __future__ import print_function
from builtins import str
import serial
import time
import matplotlib.pyplot as plt


import nplab.instrument.serial_instrument as si

class Piezoconcept(si.SerialInstrument):
    '''A simple class for the Piezo concept FOC100 nanopositioning system'''
    
    def __init__(self, port=None):
        self.termination_character = '\n'
        self.port_settings = {
                    'baudrate':115200,
                    'bytesize':serial.EIGHTBITS,
                    'parity':serial.PARITY_NONE,
                    'stopbits':serial.STOPBITS_ONE,
                    'timeout':1, #wait at most one second for a response
          #          'writeTimeout':1, #similarly, fail if writing takes >1s
           #         'xonxoff':False, 'rtscts':False, 'dsrdtr':False,
                    }
        si.SerialInstrument.__init__(self,port=port)
        self.recenter()
        
    def move_rel_x(self,value,unit="n"):
        '''A command for relative movement, where the default units is nm'''
        if unit == "n":
            multiplier=1
        if unit == "u":
            multiplier=1E3
            
        if (value*multiplier+self.positionx) > 2E5 or (value*multiplier+self.positionx) < 0:
            print("The value is out of range! 0-100 um (0-1E8 nm) (Z)")
        elif (value*multiplier+self.positionx) < 2E5 and (value*multiplier+self.positionx) >= 0:
            self.write("MOVRX "+str(value)+unit)
            self.positionx=self.query("GET_X",multiline=True,termination_line= "\n \n \n \n",timeout=.1)

    def move_rel_y(self,value,unit="n"):
        '''A command for relative movement, where the default units is nm'''
        if unit == "n":
            multiplier=1
        if unit == "u":
            multiplier=1E3
            
        if (value*multiplier+self.positiony) > 2E5 or (value*multiplier+self.positiony) < 0:
            print("The value is out of range! 0-100 um (0-1E8 nm) (Z)")
        elif (value*multiplier+self.positiony) < 2E5 and (value*multiplier+self.positiony) >= 0:
            self.write("MOVRY "+str(value)+unit)
            self.positiony=self.query("GET_Y",multiline=True,termination_line= "\n \n \n \n",timeout=.1)
    
    def move_rel_z(self,value,unit="n"):
        '''A command for relative movement, where the default units is nm'''
        if unit == "n":
            multiplier=1
        if unit == "u":
            multiplier=1E3
            
        if (value*multiplier+self.positionz) > 2E5 or (value*multiplier+self.positionz) < 0:
            print("The value is out of range! 0-100 um (0-1E8 nm) (Z)")
        elif (value*multiplier+self.positionz) < 2E5 and (value*multiplier+self.positionz) >= 0:
            self.write("MOVRZ "+str(value)+unit)
            self.positionz=self.query("GET_Z",multiline=True,termination_line= "\n \n \n \n",timeout=.1)
    
    def movex(self,value,unit="n"):
        '''An absolute movement command, will print an error to the console 
        if you moveoutside of the range(100um) default unit is nm'''
        if unit == "n":
            multiplier=1
        if unit == "u":
            multiplier=1E3
            
        if value*multiplier >2E5 or value*multiplier <0:
            print("The value is out of range! 0-100 um (0-1E8 nm) (Z)")
            
        elif value*multiplier < 2E5 and value*multiplier >=0: 
            self.write("MOVEX "+str(value)+unit)
            self.positionx = self.query("GET_X",multiline=True,termination_line= "\n \n \n \n",timeout=.1)

    def movey(self,value,unit="n"):
        '''An absolute movement command, will print an error to the console 
        if you moveoutside of the range(100um) default unit is nm'''
        if unit == "n":
            multiplier=1
        if unit == "u":
            multiplier=1E3
            
        if value*multiplier >2E5 or value*multiplier <0:
            print("The value is out of range! 0-100 um (0-1E8 nm) (Z)")
            
        elif value*multiplier < 2E5 and value*multiplier >=0: 
            self.write("MOVEY "+str(value)+unit)
            self.positiony = self.query("GET_Y",multiline=True,termination_line= "\n \n \n \n",timeout=.1)
    
    def movez(self,value,unit="n"):
        '''An absolute movement command, will print an error to the console 
        if you moveoutside of the range(100um) default unit is nm'''
        if unit == "n":
            multiplier=1
        if unit == "u":
            multiplier=1E3
            
        if value*multiplier >2E5 or value*multiplier <0:
            print("The value is out of range! 0-100 um (0-1E8 nm) (Z)")
            
        elif value*multiplier < 2E5 and value*multiplier >=0: 
            self.write("MOVEZ "+str(value)+unit)
            self.positionz = self.query("GET_Z",multiline=True,termination_line= "\n \n \n \n",timeout=.1)

    def move_xyz(self,x_val=0,y_val=0,z_val=0, unit="u"):
        self.movex(x_val, unit)
        self.movey(y_val, unit)
        self.movez(z_val, unit)

    def move_step(self,direction):
        self.move_rel(direction*self.stepsize)
        
    def recenter(self,center=100):
        ''' Moves the stage to the center position'''
        self.move_xyz(center,center,center,unit = "u")
        self.positionx = self.query("GET_X",multiline=True,termination_line= "\n \n \n \n",timeout=.1)
        self.positiony = self.query("GET_Y",multiline=True,termination_line= "\n \n \n \n",timeout=.1)
        self.positionz = self.query("GET_Z",multiline=True,termination_line= "\n \n \n \n",timeout=.1)
        
    def INFO(self):
        return self.query("INFOS",multiline=True,termination_line= "\n \n \n \n",timeout=.1,)
    
        
if __name__ == "__main__":
    '''Basic test, should open the Z stage and print its info before closing. 
    Obvisouly the comport has to be correct!'''
    Z = Piezoconcept(port = "COM10")
    print(Z.INFO())
    Z.move_xyz(0,0,0,unit="u")
    print(Z.positionx,Z.positiony,Z.positionz)
    # for i in range(100):
    #     print(Z.positionx,Z.positiony,Z.positionz)
    #     time.sleep(1)
    Z.close()