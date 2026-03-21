from snAPI.Main import *
from HBT.utils import *
import time 
import argparse
import json

class MultiHarpWrapper():
    def __init__(self, silent=False, debug=False, log_api=False, log_config=False, log_device=False, log_datafile=False, log_manipulators=False, settings_config="settings.json", measurement_config="measurement.json", irf_path=f"{'/'.join(__file__.split('/')[:-1])}/data/irf.ptu", output_path=f"{'/'.join(__file__.split('/')[:-1])}/data/default.ptu"):
        # internal config init
        self.silent = silent
        self.debug = debug
        self.irf_path = irf_path
        self.output_path = output_path
        self.is_measuring = False # not used right now, will be useful for non-blocking measurements later on, such as for live updating plots
        self.connected = False
        self.settings_config = settings_config
        self.measurement_config = measurement_config

        # snAPI config init
        self.sn = snAPI()
        self.sn.setLogLevel(LogLevel.Api, (not silent) and log_api)
        self.sn.setLogLevel(LogLevel.Config, (not silent) and log_config)
        self.sn.setLogLevel(LogLevel.Device, (not silent) and log_device)
        self.sn.setLogLevel(LogLevel.DataFile, (not silent) and log_datafile)
        self.sn.setLogLevel(LogLevel.Manipulators, (not silent) and log_manipulators)
        self.sn.setPTUFilePath(self.output_path)
        self.channels = [] # initialise in connect() call
        self.update_config()

    def debug_print(self, msg):
        if (not self.silent and self.debug): self.sn.logPrint(msg)

    def is_available(self):
        if (self.is_measuring):
            self.debug_print("Measurement in progress. Wait until finish.")
            return False
        return True

    # ------------------------- REAL DEVICE METHODS ------------------------------------
    def connect(self, measMode=MeasMode.T3, refSrc=None): # ignore refSrc
        if (self.connected):
            raise RuntimeError("Can only connect to one device at once.")            
        
        result = bool(self.sn.getDevice())
        self.debug_print(f"Get Device Status {result}")
        if (self.sn.deviceConfig["DeviceType"] != -1):
            self.connected = True
            result = bool(self.sn.initDevice(measMode)) # Always default T3 unless you're doing something funky that needs channel 1 w.r.t channel 2
            self.debug_print(f"Init Device Status: {result}")
            result = bool(self.sn.loadIniConfig("config/MH.ini"))
            self.debug_print(f"Load INI Config Status: {result}")
            self.channels = list(range(self.sn.getNumAllChannels())) # includes sync, input & manipulators
        else :
            self.connected = False
        return self.connected
    
    # Config
    def set_settings(self): # pass from a config.json file
        all = True
        for method, kwargs in self.settingsDict.items():
            resolved_kwargs = resolve_kwargs(kwargs, self.debug)
            result = bool(getattr(self.sn.device, method)(**resolved_kwargs)) # calls Device.method(keyword_arguments)
            self.debug_print(f"Set {method} with {resolved_kwargs}. Status: {result}")
            if (not result): all = False
        return all

    def get_count_rates(self, loopback=False): # this is a 100ms blocking call
        if (loopback):
            try:
                while (True):
                    countRates = self.sn.getCountRates()
                    self.sn.logPrint("Count Rates: " + ", ".join(f"{r:.2f}" for r in countRates), end="\r", flush=True)
            except KeyboardInterrupt:
                pass
        return self.sn.getCountRates()
    
    def get_sync_period(self): # returns 0.0 if measurement not running
        return self.sn.getSyncPeriod()
    
    def get_sync_rate(self): # returns 0 if measurement not running
        return self.sn.measDescription['AveSyncRate']

    # ------------------------- FILE DEVICE METHODS ------------------------------------
    def connectFile(self, filename):
        if (self.connected):
            raise RuntimeError("Can only connect to one device at once.")
                    
        result = bool(self.sn.getFileDevice(filename))
        self.debug_print(f"Get File Device Status: {result}")
        if (self.sn.deviceConfig["DeviceType"] != -1): 
            self.connected = True
            self.channels = list(range(self.sn.getNumAllChannels())) # includes sync, input & manipulators
        return self.connected
    
    def closeDevice(self):
        self.sn.closeDevice()
        self.connected = False
    
    # ------------------------- COMMON METHODS -----------------------------------------
    # Measurements: Currently only supports blocking measurements
    def _configure_measurements(self, measType="all"):
        all = True
        print(self.measurementDict)
        for type in self.measurementDict:
            print(type)
            if (measType not in ["all", type]): continue
            for method, kwargs in self.measurementDict[type]["settings"].items():
                resolved_kwargs = resolve_kwargs(kwargs, self.debug)
                type_obj = getattr(self.sn, type) # self.sn.measType
                result = bool(getattr(type_obj, method)(**resolved_kwargs))
                self.debug_print(f"Set {method} for {type} with {resolved_kwargs}. Status: {result}")
                if (not result and result is not None): all = False
        return all
    
    def update_config(self):
        with open(self.settings_config, 'r') as f:
            self.settingsDict = json.load(f)
        with open(self.measurement_config, 'r') as f:
            self.measurementDict = json.load(f)
        result = self._configure_measurements()
        return result

    def measure_irf(self, acqTime=1000, waitFinished=True, savePTU=True):
        # Assumes we are connected to a real device. DO NOT use with a file device.
        if (not self.is_available()):
            return False
        self.sn.setPTUFilePath(self.irf_path)
        result = bool(self.sn.histogram.measure(acqTime=acqTime, waitFinished=waitFinished, savePTU=savePTU))
        self.sn.setPTUFilePath(self.output_path)
        self.debug_print(f"IRF Measurement Status: {result}.")
        self.sn.logPrint(f"Retrieve IRF with histogram.getData(), or read from {self.irf_path}")
        return result # if true, get irf with histogram.getData()
    
    def measure(self, measType="unfold", acqTime=1000, size=134217728, waitFinished=True, savePTU=False):
        if (not self.is_available()):
            return False
        measure_func = getattr(self.sn, measType).measure
        kwargs = dict(acqTime=acqTime, waitFinished=waitFinished, savePTU=savePTU)
        if measType == "unfold": kwargs["size"] = size
        result = bool(measure_func(**kwargs))
        self.debug_print(f"{measType.capitalize()} Measurement Status: {result}.")
        return result # if true, get data with measType.getData()
    
    def clear(self, measType):
        try: getattr(getattr(self.sn, measType), "clearMeasure")
        except AttributeError: self.debug_print(f"{measType.capitalize()} does not have an attached 'clear' method.") 
    
    def get_data(self, measType="unfold"):
        getdata_obj = getattr(self.sn, measType) # self.sn.measType
        getdata_func = getattr(getdata_obj, self.measurementDict[measType]["getDataFunc"]) # self.sn.measType.getData
        arr1, arr2 = getdata_func()
        data = (np.array(arr1), np.array(arr2))
        self.debug_print(f"Retrieved {measType.capitalize()} Data.")
        return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--silent", action="store_true", help="Minimises output.")
    parser.add_argument("--debug", action="store_true", help="Enables MultiHarpWrapper logging.")
    parser.add_argument("--log_api", action="store_true", help="Enables API logging.")
    parser.add_argument("--log_config", action="store_true", help="Enables configuration logging.")
    parser.add_argument("--log_device", action="store_true", help="Enables device logging.")
    parser.add_argument("--log_datafile", action="store_true", help="Enables datafile logging.")
    parser.add_argument("--log_manipulators", action="store_true", help="Enables manipulators logging.")
    parser.add_argument("--settings_config", type=str, default="settings.json", help="Path to settings config JSON file. Default: ./settings.json")
    parser.add_argument("--measurement_config", type=str, default="measurement.json", help="Path to measurement config JSON file. Default: ./measurement.json")
    parser.add_argument("--irf_path", type=str, default=f"{'/'.join(__file__.split('/')[:-1])}/data/irf.ptu", help="Path to IRF PTU file. Default: ./data/irf.ptu")
    parser.add_argument("--output_path", "-o", type=str, default=f"{'/'.join(__file__.split('/')[:-1])}/data/default.ptu", help="Path to output PTU file. Default: ./data/default.ptu")

    mh = MultiHarpWrapper(**vars(parser.parse_args()))
    print(mh.connect())