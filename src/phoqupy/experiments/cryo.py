"""Cryogenic PL mapping — Piezoconcept C3200 + Andor spectrometer."""
import numpy as np
from ..devices.base import resolve_simulate
from ..devices.piezoconcept import PiezoconceptStage
from ..devices.spectrometer import AndorSpectrometer
from .._sim import SimSample, N_PIXELS
from ..core import PLMap


class CryoScan:
    def __init__(self, y_range=(90, 110), z_range=(90, 110), step=0.5, port="COM5",
                 simulate=None, seed=1, **andor_kwargs):
        self.y_range, self.z_range, self.step, self.port = y_range, z_range, step, port
        self.simulate = resolve_simulate(simulate, "Piezoconcept_C3200", "pylablib")
        self.seed = seed
        self.andor_kwargs = andor_kwargs

    def run(self):
        ys = np.arange(self.y_range[0], self.y_range[1] + self.step / 2, self.step)
        zs = np.arange(self.z_range[0], self.z_range[1] + self.step / 2, self.step)
        res = len(ys)
        center = self.y_range[0] + (self.y_range[1] - self.y_range[0]) / 2
        sample = SimSample(self.y_range, self.z_range, seed=self.seed)
        stage = PiezoconceptStage(self.port, simulate=self.simulate)
        stage.recenter(center)
        andor = AndorSpectrometer(simulate=self.simulate, sample=sample, **self.andor_kwargs)

        matrix = np.zeros((res * len(zs) + 1, N_PIXELS))
        matrix[0] = andor.setup_spectrograph()
        andor.wait_for_stabilization()
        i = 1
        for z in zs:
            for y in ys:
                stage.move_xyz(x_val=center, y_val=float(y), z_val=float(z), unit="u")
                matrix[i] = andor.acquire_spectrum(position=(y, z))
                i += 1
        stage.close()
        if not self.simulate:
            andor.shutdown()
        return PLMap(matrix, res, self.y_range, self.z_range)

    def plot_map(self, pl_map, **kw):
        return pl_map.plot_map(**kw)
