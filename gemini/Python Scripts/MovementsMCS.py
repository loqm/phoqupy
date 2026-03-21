import ctypes
from ctypes import *


lib = ctypes.CDLL('MCSControl.dll')     #load C library

def initialization():
    
    #serial_number = b"usb:id:1839779165"    #substitute this with the serial number on the smaract controller
    #system_locator = ctypes.c_char_p(serial_number)

    inizializing_option = b"sync"
    options = ctypes.c_char_p(inizializing_option)

    system_index = ctypes.c_uint(0)



    channel_index = ctypes.c_uint(0)

    direction = ctypes.c_uint(0)
    hold_time = ctypes.c_uint(0)
    auto_zero = ctypes.c_uint(0)

    known = ctypes.c_uint(11)

    #lib.SA_OpenSystem.argtypes = [POINTER(ctypes.c_uint), c_char_p, c_char_p]
    #result = lib.SA_OpenSystem(system_index, system_locator, options)


    lib.SA_InitSystems.argtypes = [ctypes.c_uint]
    result = lib.SA_InitSystems(ctypes.c_uint(0))




    if result!=0:
        print('Can not connect to the GEMINI, please power cycle and try again! Error code: ', result)
        return 0,0,1

    

    lib.SA_GetPhysicalPositionKnown_S.argtypes=[ctypes.c_uint, ctypes.c_uint, POINTER(ctypes.c_uint)]
    result = lib.SA_GetPhysicalPositionKnown_S(system_index, channel_index, known)
    if result != 0:
        print('Can not GetPhysicalPositionKnown! Error code: ', result)
        return 0,0,1


    if known.value==0 :
        lib.SA_FindReferenceMark_S.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
        result = lib.SA_FindReferenceMark_S(system_index, channel_index, direction, hold_time, auto_zero)

    if result != 0:
        print('Can not FindReferenceMark! Error code: ', result)
        return 0,0,1

            

        
    

    


    while True:
        status = ctypes.c_int()
        lib.SA_GetStatus_S.argtypes = [ctypes.c_uint, ctypes.c_uint, POINTER(ctypes.c_int)]
        result = lib.SA_GetStatus_S(system_index, channel_index, status)
        if result != 0:
            print('Can not GetStatus! Error code: ', result)
            return 0,0,1
       
        if status.value != 7:
            break


    lib.SA_GotoPositionAbsolute_S.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
    result = lib.SA_GotoPositionAbsolute_S(system_index, channel_index, 0, 0)

    if result != 0:
        print('Can not GotoPositionAbsolute! Error code: ', result)
        return 0,0,1
 

    return system_index, channel_index,0



def move_absolute(system_index, channel_index, movement):

    position = ctypes.c_int(int(movement*1000000))

    lib.SA_GotoPositionAbsolute_S.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_int, ctypes.c_uint]    #C function call
    result = lib.SA_GotoPositionAbsolute_S(system_index, channel_index, position, 60000)
    #print(result)
    return result


def move_relative(system_index, channel_index, movement):

    position = ctypes.c_int(int(movement*1000000))

    lib.SA_GotoPositionRelative_S.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
    result = lib.SA_GotoPositionRelative_S(system_index, channel_index, position, 0)
    #print(result)
    return result


def get_position(system_index, channel_index):
    position = ctypes.c_int()

    lib.SA_GetPosition_S.argtypes = [ctypes.c_uint, ctypes.c_uint, POINTER(ctypes.c_int)]
    result = lib.SA_GetPosition_S(system_index, channel_index, position)
    #print(position.value)
    return position.value/1000000

def identify():
    positioner_type='MCS'
    return positioner_type


def get_status(system_index, channel_index):
    status = ctypes.c_int()
    lib.SA_GetStatus_S.argtypes = [ctypes.c_uint, ctypes.c_uint, POINTER(ctypes.c_int)]
    result = lib.SA_GetStatus_S(system_index, channel_index, status)
    #print(status.value)
    return status


#def get_scale(system_index, channel_index):
    scale = ctypes.c_int()
    inverted = ctypes.c_uint()

    lib.SA_GetPosition_S.argtypes = [ctypes.c_uint, ctypes.c_uint, POINTER(ctypes.c_int), POINTER(ctypes.c_uint)]
    result = lib.SA_GetPosition_S(system_index, channel_index, scale, inverted)
    # print(position.value)
    return scale.value


def close_system():

   
    result = lib.SA_ReleaseSystems()  
    return result
