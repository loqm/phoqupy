"""Confocal PL mapping — NanoMax stage + Andor spectrometer (room temperature)."""
import numpy as np
from ..devices.base import resolve_simulate
from ..devices.nanomax import NanoMaxStage
from ..devices.spectrometer import AndorSpectrometer
from .._sim import SimSample, N_PIXELS
from ..core import PLMap


class ConfocalScan:
    def __init__(self, x_range=(0, 50), y_range=(0, 50), step=0.5, port="COM4",
                 simulate=None, seed=0, **andor_kwargs):
        self.x_range, self.y_range, self.step, self.port = x_range, y_range, step, port
        self.simulate = resolve_simulate(simulate, "mdt69x", "pylablib")
        self.seed = seed
        self.andor_kwargs = andor_kwargs

    def run(self, settle=0.0):
        import time
        xs = np.arange(self.x_range[0], self.x_range[1] + self.step / 2, self.step)
        ys = np.arange(self.y_range[0], self.y_range[1] + self.step / 2, self.step)
        res = len(xs)
        sample = SimSample(self.x_range, self.y_range, seed=self.seed)
        stage = NanoMaxStage(self.port, simulate=self.simulate)
        andor = AndorSpectrometer(simulate=self.simulate, sample=sample, **self.andor_kwargs)

        matrix = np.zeros((res * len(ys) + 1, N_PIXELS))
        matrix[0] = andor.setup_spectrograph()
        andor.wait_for_stabilization()
        i = 1
        for y in ys:
            for x in xs:
                stage.move_to(x=float(x), y=float(y))
                if settle:
                    time.sleep(settle)
                matrix[i] = andor.acquire_spectrum(position=(x, y))
                i += 1
        stage.close()
        if not self.simulate:
            andor.shutdown()
        return PLMap(matrix, res, self.x_range, self.y_range)

    def plot_map(self, pl_map, **kw):
        return pl_map.plot_map(**kw)
