"""Andor Kymera + Newton spectrometer (pylablib) — real + simulated."""
import numpy as np
from .base import try_import, DeviceError
from .._sim import SimSample


class AndorSpectrometer:
    driver = "pylablib"

    def __init__(self, simulate=False, sample=None, temp_setpoint=-80, exposure=0.5,
                 grating=1, filter_slot=5, center_wavelength=600e-9,
                 acquisition_mode="single", num_of_accum=10, accum_time=0.5):
        self.simulate = simulate
        self.cfg = dict(temp_setpoint=temp_setpoint, exposure=exposure, grating=grating,
                        filter_slot=filter_slot, center_wavelength=center_wavelength,
                        acquisition_mode=acquisition_mode, num_of_accum=num_of_accum,
                        accum_time=accum_time)
        self._sample = sample or SimSample()
        self.cam = self.spec = None
        if not simulate:
            pl = try_import(self.driver)
            if pl is None:
                raise DeviceError(
                    "pylablib not installed. `pip install phoqupy[spectrometer]` or simulate=True.")
            from pylablib.devices import Andor
            self.cam = Andor.AndorSDK2.AndorSDK2Camera()
            self.spec = Andor.Shamrock.ShamrockSpectrograph()
            self.cam.set_temperature(temp_setpoint)
            self.cam.set_exposure(exposure / 2)
            self.cam.set_acquisition_mode(acquisition_mode)
            self.spec.set_grating(grating)
            self.spec.set_filter(filter_slot)

    def setup_spectrograph(self):
        if self.simulate:
            return self._sample.wl.copy()
        self.spec.set_wavelength(float(self.cfg["center_wavelength"]))
        self.spec.setup_pixels_from_camera(self.cam)
        self.cam.set_read_mode("fvb")
        return self.spec.get_calibration()

    def wait_for_stabilization(self):
        if self.simulate:
            return
        import time
        while self.cam.get_temperature_status() != "stabilized":
            time.sleep(1)

    def acquire_spectrum(self, position=None):
        """Double-acquisition read (cosmic-ray suppression) on real hardware."""
        if self.simulate:
            x, y = position or (0, 0)
            return self._sample.spectrum(x, y)
        a1 = self.cam.snap()[0]
        a2 = self.cam.snap()[0]
        out = [0] * len(a1)
        for i in range(len(a1)):
            if abs(a1[i] - a2[i]) > 10:      # cosmic-ray artifact -> keep the lower
                lo = min(a1[i], a2[i]); a1[i] = a2[i] = lo
            out[i] = a1[i] + a2[i]
        return np.asarray(out)

    def shutdown(self):
        if self.cam:
            self.cam.close(); self.spec.close()
