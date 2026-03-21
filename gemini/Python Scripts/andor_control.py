# andor_control.py

import time
from pylablib.devices import Andor

class AndorSystem:
    def __init__(self, temp_setpoint=-80, exposure=0.5, grating=1, filter_slot=5,center_wavelength=600E-9, acquisition_mode="single", num_of_accum=1, accum_time=1 ):
        self.cam = Andor.AndorSDK2.AndorSDK2Camera()
        self.spec = Andor.Shamrock.ShamrockSpectrograph()
        self.temp_setpoint = temp_setpoint
        self.center_wavelength= center_wavelength
        self.cam.set_temperature(temp_setpoint)
        self.cam.set_exposure(exposure/2)
        self.cam.set_acquisition_mode(acquisition_mode)
        if acquisition_mode == "accum":
            self.cam.setup_accum_mode(num_of_accum, accum_time)
        self.cam.set_fan_mode("full")

        self.spec.set_grating(grating)
        self.spec.set_filter(filter_slot)

        print("Andor initialized")
        print("Setpoint:", self.cam.get_temperature_setpoint())
        print("Status:", self.cam.get_temperature_status())

    def wait_for_stabilization(self):
        while self.cam.get_temperature_status() != 'stabilized':
            if self.cam.get_temperature_status() == 'drifted':
                print("Temperature drifted. Shutting down.")
                self.shutdown()
                exit()
            print(self.cam.get_temperature(), self.cam.get_temperature_status())
            time.sleep(3)

    def setup_spectrograph(self):
        self.spec.set_wavelength(float(self.center_wavelength))
        self.spec.setup_pixels_from_camera(self.cam)
        self.cam.set_read_mode("fvb")
        return self.spec.get_calibration()

    def acquire_spectrum(self):
        print(self.cam.get_temperature())
        acq1 = self.cam.snap()[0]
        acq2 = self.cam.snap()[0]
        acq = [0] * len(acq1)
        for i in range(len(acq1)):
            if abs(acq1[i] - acq2[i]) > 10:
                if acq1[i] > acq2[i]:
                    acq1[i] = acq2[i]
                else:
                    acq2[i] = acq1[i]
            acq[i] = acq1[i] + acq2[i]
        return acq

    def check_overexposure(self, spectrum, threshold=10000):
        if max(spectrum) > threshold:
            return "over"

    def shutdown(self):
        self.cam.set_cooler(False)
        while(self.cam.get_temperature()) < -20:
            print(self.cam.get_temperature())
            time.sleep(0.5)
        print(self.cam.get_temperature())
        self.cam.close()
        self.spec.close()
        print("Andor system shut down.")