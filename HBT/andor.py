import time
import yaml
from pylablib.devices import Andor

class AndorSystem():
    def __init__(self, config="config.yaml"):
        try:
            self.cam = Andor.AndorSDK2.AndorSDK2Camera()
            self.spec = Andor.Shamrock.ShamrockSpectrograph()
            self.update_config(config)
        except Exception as e:
            print(f"Error initializing Andor system: {e}")
            self.cam = None
            self.spec = None
            return

    def update_config(self, config=None):
        if (config):
            with open(config, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            if (not self.config):
                raise RuntimeError("Andor config path is not set!")
        self.temp_setpoint = self.config.get('temp_setpoint', self.temp_setpoint)
        self.center_wavelength = self.config.get('center_wavelength', self.center_wavelength)
        self.cam.set_temperature(self.temp_setpoint)
        self.cam.set_exposure(self.config.get('exposure', self.cam.get_exposure())/2)
        self.cam.set_acquisition_mode(self.config.get('acquisition_mode', "single"))
        if self.config.get('acquisition_mode', "single") == "accum":
            self.cam.setup_accum_mode(self.config.get('num_of_accum', 1), self.config.get('accum_time', 1))
        self.cam.set_fan_mode(self.config.get('fan_mode', "full"))
        self.spec.set_grating(self.config.get('grating', 1))
        self.spec.set_filter(self.config.get('filter_slot', 5))
        print("Configuration updated.")
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

    def is_overexposed(self, spectrum, threshold=10000):
        return (max(spectrum) > threshold)

    def shutdown(self):
        self.cam.set_cooler(False)
        while(self.cam.get_temperature()) < -20:
            print(self.cam.get_temperature())
            time.sleep(0.5)
        print(self.cam.get_temperature())
        self.cam.close()
        self.spec.close()
        print("Andor system shut down.")